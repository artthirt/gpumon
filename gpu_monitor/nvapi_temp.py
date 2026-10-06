"""GPU memory temperature via NVAPI (LibreHardwareMonitor's approach).

``nvidia-smi`` / NVML report ``[N/A]`` for the memory temperature on most
cards, while NVAPI's internal ``NvAPI_GPU_ThermalGetSensors`` (QueryInterface
ID ``0x65FE3AAD``) exposes raw per-sensor temperatures.  LHM reads the VRAM
value from a generation-dependent slot of that array (50xx: idx 2,
40xx: idx 7, older: idx 9), fixed-point with 8 fractional bits.

Bindings mirror ``LibreHardwareMonitorLib/Interop/NvApi.cs`` and
``Hardware/Gpu/NvidiaGpu.cs`` (QueryInterface IDs, struct layouts,
version constant, mask discovery loop, per-generation indices).

Usage::

    from gpu_monitor import nvapi_temp
    # names: {bus_id: gpu_name}, bus_id = PCI bus number (int)
    temps = nvapi_temp.memory_temps_by_bus_id({1: "... RTX 5080"})
    # {1: 41.0, ...}
"""

from __future__ import annotations

import ctypes
import sys
from typing import Dict, List, Optional

_OK = 0

# nvapi_QueryInterface IDs (LibreHardwareMonitor Interop/NvApi.cs)
_ID_INITIALIZE = 0x0150E828
_ID_ENUM_PHYS_GPUS = 0xE5AC921F
_ID_GET_THERMAL_SETTINGS = 0xE3640A56
_ID_GET_THERMAL_SENSORS = 0x65FE3AAD
_ID_GET_BUS_ID = 0x1BE0B8E5

MAX_SENSORS = 3                      # MAX_THERMAL_SENSORS_PER_GPU
TARGET_ALL = 15                      # NvThermalTarget.All
THERMAL_RESERVED_COUNT = 8           # THERMAL_SENSOR_RESERVED_COUNT
THERMAL_TEMPERATURE_COUNT = 32       # THERMAL_SENSOR_TEMPERATURE_COUNT


class _NvSensor(ctypes.Structure):
    _fields_ = [
        ("controller", ctypes.c_uint32),
        ("default_min", ctypes.c_uint32),
        ("default_max", ctypes.c_uint32),
        ("current", ctypes.c_uint32),
        ("target", ctypes.c_uint32),
    ]


class _NvThermalSettings(ctypes.Structure):
    _fields_ = [
        ("version", ctypes.c_uint32),
        ("count", ctypes.c_uint32),
        ("sensor", _NvSensor * MAX_SENSORS),
    ]


# MAKE_NVAPI_VERSION(NvThermalSettings, 2) = sizeof | (2 << 16)
_THERMAL_VERSION = ctypes.sizeof(_NvThermalSettings) | (2 << 16)


class _NvThermalSensors(ctypes.Structure):
    """Internal NvAPI_GPU_ThermalGetSensors result (Pack=8, all 4-byte
    fields — no alignment surprises on x64)."""
    _fields_ = [
        ("version", ctypes.c_uint32),
        ("mask", ctypes.c_uint32),
        ("reserved", ctypes.c_int32 * THERMAL_RESERVED_COUNT),
        ("temperatures", ctypes.c_int32 * THERMAL_TEMPERATURE_COUNT),
    ]


_THERMAL_SENSORS_VERSION = \
    ctypes.sizeof(_NvThermalSensors) | (2 << 16)


class _NvPhysicalGpuHandle(ctypes.Structure):
    _fields_ = [("ptr", ctypes.c_void_p)]


class _NvApi:
    """Lazy loader of the NVAPI entry points we need."""

    def __init__(self) -> None:
        self.ok = False
        self.initialize = None
        self.enum_phys_gpus = None
        self.get_thermal_settings = None
        self.get_thermal_sensors = None
        self.get_bus_id = None

    def load(self) -> bool:
        if self.ok:
            return True
        if sys.platform != "win32":
            return False
        dll_name = "nvapi64.dll" if sys.maxsize > 2 ** 32 else "nvapi.dll"
        try:
            dll = ctypes.WinDLL(dll_name)
            qi_addr = ctypes.cast(
                getattr(dll, "nvapi_QueryInterface"),
                ctypes.c_void_p).value
        except (OSError, AttributeError):
            return False
        if not qi_addr:
            return False
        query = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_uint32)(qi_addr)

        def _get(fid: int, argtypes) -> Optional[ctypes.CFUNCTYPE]:
            addr = query(fid)
            if not addr:
                return None
            fn = ctypes.CFUNCTYPE(ctypes.c_int32, *argtypes)(addr)
            fn.argtypes = argtypes
            fn.restype = ctypes.c_int32
            return fn

        self.initialize = _get(_ID_INITIALIZE, [])
        # old-style signature: (handles, out count) — no apiVersion arg
        self.enum_phys_gpus = _get(
            _ID_ENUM_PHYS_GPUS,
            [ctypes.POINTER(_NvPhysicalGpuHandle),
             ctypes.POINTER(ctypes.c_uint32)])
        self.get_thermal_settings = _get(
            _ID_GET_THERMAL_SETTINGS,
            [_NvPhysicalGpuHandle, ctypes.c_int32,
             ctypes.POINTER(_NvThermalSettings)])
        # internal: (handle, ref struct) — the mask is a FIELD of the
        # struct, NOT a separate argument
        self.get_thermal_sensors = _get(
            _ID_GET_THERMAL_SENSORS,
            [_NvPhysicalGpuHandle, ctypes.POINTER(_NvThermalSensors)])
        self.get_bus_id = _get(
            _ID_GET_BUS_ID,
            [_NvPhysicalGpuHandle, ctypes.POINTER(ctypes.c_uint32)])
        self.ok = bool(self.initialize and self.enum_phys_gpus
                       and self.get_thermal_settings
                       and self.get_thermal_sensors and self.get_bus_id)
        return self.ok


_api = _NvApi()
_mask_cache: Dict[int, int] = {}


def _memory_index(gpu_name: str) -> int:
    """Slot of the VRAM temperature in the raw array (LHM's rules)."""
    n = gpu_name or ""
    if n.startswith("NVIDIA GeForce RTX 50"):
        return 2
    if n.startswith("NVIDIA GeForce RTX 40"):
        return 7
    return 9


def raw_thermal_temps_by_bus_id() -> Dict[int, List[int]]:
    """Raw fixed-point thermal sensor arrays per PCI bus number.

    Returns ``{bus_id: [32 raw temps]}`` (raw / 256.0 = degrees C).
    Empty dict on any failure (no driver, no sensor, ...).
    """
    if not _api.load() or _api.initialize(_OK) != _OK:
        return {}
    handles = (_NvPhysicalGpuHandle * 64)()
    count = ctypes.c_uint32(len(handles))
    if _api.enum_phys_gpus(handles, ctypes.byref(count)) != _OK:
        return {}

    result: Dict[int, List[int]] = {}
    for i in range(count.value):
        h = handles[i]
        if not h.ptr:
            continue
        bus = ctypes.c_uint32(0)
        if _api.get_bus_id(h, ctypes.byref(bus)) != _OK:
            continue

        # Mask discovery: probe bits 0..31, accumulate every supported
        # bit, stop at the first failure.  A single-bit mask only returns
        # that one slot; the accumulated mask returns the full array.
        # Cached per bus — the mask does not change at runtime.
        mask = _mask_cache.get(bus.value)
        if mask is None:
            mask = 0
            for bit in range(32):
                probe = _NvThermalSensors(
                    version=_THERMAL_SENSORS_VERSION, mask=1 << bit)
                if _api.get_thermal_sensors(h, ctypes.byref(probe)) == _OK:
                    mask |= 1 << bit
                    continue
                break
            if mask == 0:
                continue
            _mask_cache[bus.value] = mask

        ts = _NvThermalSensors(version=_THERMAL_SENSORS_VERSION, mask=mask)
        if _api.get_thermal_sensors(h, ctypes.byref(ts)) != _OK:
            continue
        result[bus.value] = list(ts.temperatures)
    return result


def memory_temps_by_bus_id(name_by_bus: Dict[int, str]) -> Dict[int, float]:
    """Memory (VRAM) temperatures keyed by PCI bus number (int).

    ``name_by_bus`` maps bus id -> GPU name; needed because the slot of
    the VRAM value in the raw sensor array depends on the card
    generation (see LHM).  GPUs without a usable value are omitted.
    """
    raws = raw_thermal_temps_by_bus_id()
    if not raws:
        return {}
    temps: Dict[int, float] = {}
    for bus, arr in raws.items():
        idx = _memory_index(name_by_bus.get(bus, ""))
        if idx >= THERMAL_TEMPERATURE_COUNT:
            continue
        raw = arr[idx]
        # 0 = no data, 0xFF = "not available" sentinel, >160 C = bogus
        # (raw is fixed-point: value_C = raw / 256)
        if 0 < raw < 0xA000 and raw != 0xFF:
            temps[bus] = raw / 256.0
    return temps
