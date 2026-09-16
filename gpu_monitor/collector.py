"""Background nvidia-smi sampler.

Spawns ``nvidia-smi --query-gpu=... --format=csv,noheader,nounits`` on a
``QThread`` and emits parsed :class:`~gpu_monitor.model.GpuSnapshot`
objects.  Read-only: no admin rights, no management commands.
"""

from __future__ import annotations

import csv
import io
import re
import shutil
import subprocess
import sys
import time
from typing import List, Optional

from PySide6.QtCore import QThread, Signal

from .model import GpuSnapshot, decode_throttle

# (GpuSnapshot attribute, nvidia-smi query field)
QUERY_FIELDS: List[tuple[str, str]] = [
    ("index", "index"),
    ("name", "name"),
    ("uuid", "uuid"),
    ("driver_version", "driver_version"),
    ("vbios_version", "vbios_version"),
    ("serial", "serial"),
    ("bus_id", "pci.bus_id"),
    ("util_gpu", "utilization.gpu"),
    ("util_mem", "utilization.memory"),
    ("util_enc", "utilization.encoder"),
    ("util_dec", "utilization.decoder"),
    ("temp_gpu", "temperature.gpu"),
    ("temp_mem", "temperature.memory"),
    ("mem_total", "memory.total"),
    ("mem_used", "memory.used"),
    ("mem_free", "memory.free"),
    ("power_draw", "power.draw"),
    ("power_limit", "power.limit"),
    ("power_max_limit", "power.max_limit"),
    ("power_default_limit", "power.default_limit"),
    ("clock_graphics", "clocks.gr"),
    ("clock_sm", "clocks.sm"),
    ("clock_mem", "clocks.mem"),
    ("clock_video", "clocks.video"),
    ("fan_speed", "fan.speed"),
    ("perf_state", "pstate"),
    ("throttle_bits", "clocks_throttle_reasons.active"),
    ("pcie_gen_current", "pcie.link.gen.current"),
    ("pcie_width_current", "pcie.link.width.current"),
]

INT_ATTRS = {"index", "throttle_bits"}
STR_ATTRS = {
    "name", "uuid", "driver_version", "vbios_version", "serial",
    "bus_id", "perf_state",
}

PROC_FIELDS = "pid,process_name,used_memory,gpu_uuid"

_RE_SMI = re.compile(r"NVIDIA-SMI\s+(?P<smi>[\d.]+)")
# Old drivers: "Driver Version: 535.104.05". Newer NVIDIA-SMI (>= ~570) prints
# "KMD Version: 616.92" instead — accept either.
_RE_DRIVER = re.compile(r"(?:Driver|KMD) Version:\s*(?P<drv>[\d.]+)")
# Newer NVIDIA-SMI prints "CUDA UMD Version"; older ones "CUDA Version".
_RE_CUDA = re.compile(r"CUDA(?:\s+UMD)?\s+Version:\s*(?P<cuda>[\d.]+)")


def find_nvidia_smi() -> Optional[str]:
    """Locate the nvidia-smi executable."""
    found = shutil.which("nvidia-smi")
    if found:
        return found
    if sys.platform == "win32":
        import os
        for env in ("SystemRoot", "windir"):
            base = os.environ.get(env)
            if base:
                cand = os.path.join(base, "System32", "nvidia-smi.exe")
                if os.path.isfile(cand):
                    return cand
    return None


def _run_smi(smi_path: str, args: List[str], timeout: float = 15.0) -> Optional[str]:
    """Run nvidia-smi; return stdout or None on failure."""
    kwargs = dict(capture_output=True, text=True, timeout=timeout)
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.run([smi_path, *args], **kwargs)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def read_meta(smi_path: str) -> Optional[dict]:
    """Parse driver / CUDA versions from the plain ``nvidia-smi`` header."""
    out = _run_smi(smi_path, [])
    if not out:
        return None
    m = _RE_SMI.search(out)
    if not m:
        return None
    md = _RE_DRIVER.search(out)
    mc = _RE_CUDA.search(out)
    return {
        "smi_version": m.group("smi"),
        "driver_version": md.group("drv") if md else "",
        "cuda_version": mc.group("cuda") if mc else "",
    }


def _parse_throttle(text: str) -> Optional[int]:
    t = text.strip()
    if not t or t.upper().startswith("[N/A]"):
        return None
    try:
        return int(t, 16)
    except ValueError:
        return None


def query_gpus(smi_path: str) -> List[GpuSnapshot]:
    """One blocking poll: returns a list of snapshots (one per GPU)."""
    fields = ",".join(f for _, f in QUERY_FIELDS)
    out = _run_smi(smi_path, [f"--query-gpu={fields}", "--format=csv,noheader,nounits"])
    if out is None:
        return []
    now = time.time()
    snaps: List[GpuSnapshot] = []
    for row in csv.reader(io.StringIO(out)):
        if len(row) != len(QUERY_FIELDS):
            continue
        snap = GpuSnapshot(timestamp=now)
        for (attr, _qf), raw in zip(QUERY_FIELDS, row):
            raw = raw.strip()
            if attr in INT_ATTRS and attr == "index":
                try:
                    setattr(snap, attr, int(float(raw)))
                except ValueError:
                    pass
            elif attr == "throttle_bits":
                setattr(snap, attr, _parse_throttle(raw))
            elif attr in STR_ATTRS:
                setattr(snap, attr, raw)
            else:
                setattr(snap, attr, _num_or_none(raw))
        snap.throttle_reasons = decode_throttle(snap.throttle_bits)
        snaps.append(snap)
    return snaps


def _num_or_none(text: str):
    t = text.strip()
    if not t or t.upper().startswith("[N/A]"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def query_processes(smi_path: str) -> List[dict]:
    """Active compute / graphics processes holding a context on a GPU."""
    out = _run_smi(smi_path, [f"--query-compute-apps={PROC_FIELDS}",
                              "--format=csv,noheader,nounits"])
    if out is None:
        return []
    procs: List[dict] = []
    for row in csv.reader(io.StringIO(out)):
        if len(row) < 4:
            continue
        mem = _num_or_none(row[2])
        pid = int(float(row[0])) if _num_or_none(row[0]) is not None else 0
        procs.append({"pid": pid, "name": row[1].strip(), "mem_mib": mem,
                      "uuid": row[3].strip()})
    return procs


class GpuSampler(QThread):
    """Polls nvidia-smi on a timer and emits Qt signals.

    Signals
    -------
    meta_ready(dict)          driver/CUDA versions (once, at start)
    snapshot_ready(list)      list of GpuSnapshot, one per poll
    processes_ready(list)     list of process dicts, one per poll
    sampler_error(str)        human-readable error message
    """

    meta_ready = Signal(dict)
    snapshot_ready = Signal(list)
    processes_ready = Signal(list)
    sampler_error = Signal(str)

    def __init__(self, smi_path: Optional[str] = None, interval_ms: int = 1000,
                 parent=None):
        super().__init__(parent)
        self.smi_path = smi_path or find_nvidia_smi()
        self.interval_ms = max(250, int(interval_ms))
        self._paused = False
        self._stop = False

    # -- control ------------------------------------------------------------
    def set_interval(self, ms: int) -> None:
        self.interval_ms = max(250, int(ms))

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def request_stop(self) -> None:
        self._stop = True

    # -- thread body ----------------------------------------------------------
    def run(self) -> None:  # noqa: D102
        if not self.smi_path:
            self.sampler_error.emit(
                "nvidia-smi was not found on PATH or in System32.")
            return
        meta = read_meta(self.smi_path)
        if meta:
            self.meta_ready.emit(meta)

        while not self._stop:
            if not self._paused:
                t0 = time.perf_counter()
                try:
                    snaps = query_gpus(self.smi_path)
                    if snaps:
                        self.snapshot_ready.emit(snaps)
                        self.processes_ready.emit(query_processes(self.smi_path))
                    else:
                        self.sampler_error.emit(
                            "nvidia-smi query failed (driver not responding?)")
                except Exception as exc:  # keep the thread alive
                    self.sampler_error.emit(f"collector error: {exc}")
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                self._sleep_ms(max(50, self.interval_ms - int(elapsed_ms)))
            else:
                self._sleep_ms(250)

    def _sleep_ms(self, ms: int) -> None:
        """Interruptible sleep so request_stop() stays responsive."""
        deadline = time.perf_counter() + ms / 1000.0
        while not self._stop and time.perf_counter() < deadline:
            self.msleep(50)


class PcieDmonSampler(QThread):
    """Continuous ``nvidia-smi dmon -s t`` loop → PCIe Rx/Tx throughput.

    This driver has no queryable ``pcie_throughput`` field, so we run the
    dmon monitor instead (one sample per second, per GPU).

    Signal
    ------
    pcie_update(int, float, float)   (gpu index, rx MB/s, tx MB/s)
    """

    pcie_update = Signal(int, float, float)

    def __init__(self, smi_path: Optional[str] = None, delay_s: int = 1,
                 parent=None):
        super().__init__(parent)
        self.smi_path = smi_path or find_nvidia_smi()
        self.delay_s = max(1, int(delay_s))
        self._stop = False
        self._paused = False

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def request_stop(self) -> None:
        self._stop = True

    def _handle_line(self, line: str) -> None:
        parts = line.split()
        if len(parts) < 3:
            return
        try:
            idx = int(float(parts[0]))
        except ValueError:
            return  # header / comment line
        rx = _num_or_none(parts[1])
        tx = _num_or_none(parts[2])
        if rx is None and tx is None:
            return
        self.pcie_update.emit(idx, rx or 0.0, tx or 0.0)

    def run(self) -> None:
        if not self.smi_path:
            return
        backoff_s = 1.0
        while not self._stop:
            if self._paused:
                self._sleep_ms(250)
                continue
            try:
                kwargs = dict(stdout=subprocess.PIPE, text=True,
                              stderr=subprocess.DEVNULL)
                if sys.platform == "win32":
                    kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
                with subprocess.Popen(
                        [self.smi_path, "dmon", "-s", "t",
                         "-d", str(self.delay_s)], **kwargs) as proc:
                    for line in proc.stdout:
                        if self._stop:
                            proc.kill()
                            break
                        self._handle_line(line)
                backoff_s = 1.0
            except (OSError, subprocess.SubprocessError):
                pass
            self._sleep_ms(int(backoff_s * 1000))
            backoff_s = min(backoff_s * 2, 15.0)  # restart with backoff

    def _sleep_ms(self, ms: int) -> None:
        deadline = time.perf_counter() + ms / 1000.0
        while not self._stop and time.perf_counter() < deadline:
            self.msleep(50)
