"""Data model for a single GPU snapshot.

A :class:`GpuSnapshot` is one row of ``nvidia-smi --query-gpu`` output,
parsed into typed, unit-aware fields.  Fields that the driver cannot
report (common on consumer GeForce parts or on some OS/driver combos)
are ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# nvidia-smi reports these as the literal string "[N/A]" (or similar)
# when a property is unsupported.  We normalise all of them to None.
_NA_TOKENS = {
    "",
    "[N/A]",
    "[n/a]",
    "N/A",
    "n/a",
    "Not Supported",
    "[Not Supported]",
    "Not Available",
    "Unknown",
    "[Unknown]",
}


def _opt_float(text: str) -> Optional[float]:
    """Parse a numeric CSV cell, mapping nvidia-smi 'N/A' to ``None``."""
    if text is None:
        return None
    t = text.strip()
    if t in _NA_TOKENS:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _opt_int(text: str) -> Optional[int]:
    v = _opt_float(text)
    return None if v is None else int(v)


def _opt_str(text: str) -> Optional[str]:
    if text is None:
        return None
    t = text.strip()
    return None if t in _NA_TOKENS else t


@dataclass
class GpuSnapshot:
    """One point-in-time reading for a single GPU."""

    # identity / static
    index: int = 0
    name: str = ""
    uuid: str = ""
    driver_version: str = ""
    vbios_version: str = ""
    serial: str = ""
    bus_id: str = ""

    # utilization (percent 0..100)
    util_gpu: Optional[float] = None
    util_mem: Optional[float] = None
    util_enc: Optional[float] = None
    util_dec: Optional[float] = None

    # temperature (C)
    temp_gpu: Optional[float] = None
    temp_mem: Optional[float] = None

    # memory (MiB)
    mem_total: Optional[float] = None
    mem_used: Optional[float] = None
    mem_free: Optional[float] = None

    # power (W)
    power_draw: Optional[float] = None
    power_limit: Optional[float] = None
    power_max_limit: Optional[float] = None
    power_default_limit: Optional[float] = None

    # clocks (MHz)
    clock_graphics: Optional[float] = None
    clock_sm: Optional[float] = None
    clock_mem: Optional[float] = None
    clock_video: Optional[float] = None

    # fan / thermal
    fan_speed: Optional[float] = None
    perf_state: str = ""            # e.g. "P0" .. "P15"

    # throttle (bitmask as int) + decoded reason names
    throttle_bits: Optional[int] = None
    throttle_reasons: list[str] = field(default_factory=list)

    # pci-e
    pcie_gen_current: Optional[float] = None
    pcie_width_current: Optional[float] = None

    # convenience: a monotonic-ish wall-clock timestamp (epoch seconds)
    timestamp: float = 0.0

    # ---- derived helpers ---------------------------------------------------

    @property
    def mem_used_frac(self) -> Optional[float]:
        if self.mem_used is None or not self.mem_total:
            return None
        return max(0.0, min(1.0, self.mem_used / self.mem_total))

    @property
    def power_frac(self) -> Optional[float]:
        if self.power_draw is None or not self.power_limit:
            return None
        return max(0.0, min(1.0, self.power_draw / self.power_limit))

    @property
    def is_throttled(self) -> bool:
        # bit 0 (GPU Idle) is a normal, benign condition.
        return bool(self.throttle_bits and (self.throttle_bits & ~0x1))


# Bitmask -> human readable throttle reasons (NVML clocks throttle bits).
THROTTLE_BITS = {
    0: "GPU Idle",
    1: "Applications Clocks Setting",
    2: "SW Power Cap",
    3: "HW Slow Brake",
    4: "SW Thermal Cap",
    5: "HW Thermal Shutdown",
    6: "SW Power Brake",
    7: "HW Power Brake",
    8: "SW Thermal Slowdown",
    9: "HW Thermal Slowdown",
    10: "HW FL (Fan) Slowdown",
    11: "SW FL (Fan) Slowdown",
    12: "Reliability",
    13: "SW Thermal Slowdown (Memory)",
    14: "HW Thermal Slowdown (Memory)",
    15: "HW Thermal Interposer Slowdown",
    16: "Power Floor Reduction",
}


def decode_throttle(bits: Optional[int]) -> list[str]:
    """Return a list of human readable throttle reason names."""
    if not bits:
        return []
    return [name for i, name in sorted(THROTTLE_BITS.items()) if bits & (1 << i)]
