"""Per-GPU status card widgets."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QSizePolicy, QVBoxLayout, QWidget)

from . import theme
from .charts import Sparkline


def fmt_mem(mib: Optional[float]) -> str:
    if mib is None:
        return "—"
    if mib >= 1024:
        return f"{mib / 1024:.1f} GiB"
    return f"{mib:.0f} MiB"


def fmt_opt(v: Optional[float], unit: str = "", digits: int = 0) -> str:
    if v is None:
        return "—"
    return f"{v:.{digits}f} {unit}".strip()


def fmt_mem_short(mib: Optional[float]) -> str:
    """Compact VRAM value for narrow rows: '18.8G' / '512M'."""
    if mib is None:
        return "—"
    if mib >= 1024:
        return f"{mib / 1024:.1f}G"
    return f"{mib:.0f}M"


class Bar(QWidget):
    """Slim rounded progress bar with a per-instance accent color."""

    def __init__(self, color: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._frac: Optional[float] = 0.0
        self._color = QColor(color)
        self.setFixedHeight(6)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_fraction(self, frac: Optional[float]) -> None:
        self._frac = None if frac is None else max(0.0, min(1.0, frac))
        self.update()

    def paintEvent(self, _ev) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        h = self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.color("track")))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, h - 1), h / 2, h / 2)
        if self._frac:
            w = max(float(h), self._frac * (self.width() - 1))
            p.setBrush(self._color)
            p.drawRoundedRect(QRectF(0.5, 0.5, w, h - 1), h / 2, h / 2)
        p.end()


class GpuCard(QFrame):
    """Compact live status card for one GPU."""

    def __init__(self, accent: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("gpuCard")
        self.accent = accent

        g = QGridLayout(self)
        g.setContentsMargins(16, 12, 16, 14)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(5)

        # ---- header -------------------------------------------------------
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 2)
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background-color:{accent}; border-radius:5px;")
        self.lbl_name = QLabel("GPU …")
        self.lbl_name.setStyleSheet(
            f"font-weight:600; font-size:12pt; color:{theme.color('card_name')};"
            " background:transparent;")
        self.lbl_pstate = QLabel("—")
        self.lbl_pstate.setObjectName("badge")
        self.lbl_pstate.setToolTip(
            "Performance state — P0 is maximum performance, P15 minimum "
            "(lower number = higher clocks).")
        header.addWidget(dot)
        header.addWidget(self.lbl_name)
        header.addStretch(1)
        header.addWidget(self.lbl_pstate)
        g.addLayout(header, 0, 0, 1, 3)

        # label registries for restyle() (theme switching)
        self._caps: List[QLabel] = []
        self._vals: List[QLabel] = []
        self._stat_caps: List[QLabel] = []
        self._stat_vals: List[QLabel] = []
        self._footers: List[QLabel] = []

        # ---- metric rows (caption + value, then a bar) --------------------
        self.lbl_util_val = self._metric(
            g, 1, "GPU load",
            "Share of the last sampling interval the GPU was busy executing "
            "work (0–100 %).")
        self.bar_util = self._bar(g, 2, accent, self.lbl_util_val.toolTip())
        self.lbl_mem_val = self._metric(
            g, 3, "Video memory",
            "VRAM currently in use, out of the total.")
        self.bar_mem = self._bar(g, 4, "#a78bfa", self.lbl_mem_val.toolTip())
        self.lbl_pow_val = self._metric(
            g, 5, "Power",
            "Current power draw in watts, against the active power limit.")
        self.bar_pow = self._bar(g, 6, "#fbbf24", self.lbl_pow_val.toolTip())

        # ---- small stats trio ----------------------------------------------
        g.addWidget(self._stat_caption("Temperature",
            "GPU core (die) temperature in °C."), 7, 0)
        g.addWidget(self._stat_caption("Fan",
            "Fan speed as a percentage of maximum RPM."), 7, 1)
        g.addWidget(self._stat_caption("Enc / Dec",
            "Hardware encoder / decoder engine utilisation in %."), 7, 2)
        self.lbl_temp = self._stat_value(8, 0, "—",
            "GPU core (die) temperature in °C.")
        self.lbl_fan = self._stat_value(8, 1, "—",
            "Fan speed as a percentage of maximum RPM.")
        self.lbl_encdec = self._stat_value(8, 2, "—",
            "Hardware encoder / decoder engine utilisation in %.")

        # ---- footer lines ---------------------------------------------------
        self.lbl_clocks = self._footer(
            g, 9,
            "Current clocks: SM (graphics core), MEM (memory) and VID "
            "(video/encoder) in MHz.")
        self.lbl_pcie = self._footer(
            g, 10,
            "Active PCIe link generation × width, VBIOS version and PCI bus "
            "ID.")
        self.lbl_throttle = QLabel("● —")
        self.lbl_throttle.setStyleSheet("background:transparent;")
        self.lbl_throttle.setToolTip("Clock throttle status")
        self._throttle_reasons: Optional[list] = None  # None = not throttled
        g.addWidget(self.lbl_throttle, 11, 0, 1, 3)

    def restyle(self) -> None:
        """Re-apply inline label styles from the active theme."""
        t = theme.color
        self.lbl_name.setStyleSheet(
            f"font-weight:600; font-size:12pt; color:{t('card_name')};"
            " background:transparent;")
        for w in self._caps:
            w.setStyleSheet(f"color:{t('muted2')}; background:transparent;")
        for w in self._vals:
            w.setStyleSheet(
                f"font-size:11pt; font-weight:600; color:{t('value_text')};"
                " background:transparent;")
        for w in self._stat_caps + self._footers:
            w.setStyleSheet(f"color:{t('muted3')}; font-size:9pt; background:transparent;")
        for w in self._stat_vals:
            w.setStyleSheet(
                f"font-size:10pt; font-weight:600; color:{t('text')};"
                " background:transparent;")
        self._apply_throttle()
        for bar in (self.bar_util, self.bar_mem, self.bar_pow):
            bar.update()

    # -- builders ------------------------------------------------------------
    def _metric(self, g: QGridLayout, row: int, caption: str,
                tip: str = "") -> QLabel:
        hb = QHBoxLayout()
        hb.setContentsMargins(0, 0, 0, 0)
        cap = QLabel(caption)
        cap.setStyleSheet(
            f"color:{theme.color('muted2')}; background:transparent;")
        cap.setFixedWidth(96)
        val = QLabel("—")
        val.setStyleSheet(
            f"font-size:11pt; font-weight:600; color:{theme.color('value_text')};"
            " background:transparent;")
        if tip:
            cap.setToolTip(tip)
            val.setToolTip(tip)
        self._caps.append(cap)
        self._vals.append(val)
        hb.addWidget(cap)
        hb.addWidget(val, 1)
        g.addLayout(hb, row, 0, 1, 3)
        return val

    def _bar(self, g: QGridLayout, row: int, color: str, tip: str = "") -> Bar:
        bar = Bar(color)
        if tip:
            bar.setToolTip(tip)
        g.addWidget(bar, row, 0, 1, 3)
        return bar

    def _stat_caption(self, text: str, tip: str = "") -> QLabel:
        lab = QLabel(text)
        lab.setStyleSheet(
            f"color:{theme.color('muted3')}; font-size:9pt; background:transparent;")
        self._stat_caps.append(lab)
        if tip:
            lab.setToolTip(tip)
        return lab

    def _stat_value(self, row: int, col: int, text: str, tip: str = "") -> QLabel:
        lab = QLabel(text)
        lab.setStyleSheet(
            f"font-size:10pt; font-weight:600; color:{theme.color('text')};"
            " background:transparent;")
        self._stat_vals.append(lab)
        if tip:
            lab.setToolTip(tip)
        return lab

    def _footer(self, g: QGridLayout, row: int, tip: str = "") -> QLabel:
        lab = QLabel("—")
        lab.setStyleSheet(
            f"color:{theme.color('muted3')}; font-size:9pt; background:transparent;")
        self._footers.append(lab)
        if tip:
            lab.setToolTip(tip)
        g.addWidget(lab, row, 0, 1, 3)
        return lab

    # -- updates ---------------------------------------------------------------
    def set_sample(self, s) -> None:  # s: GpuSnapshot
        self.lbl_name.setText(f"GPU {s.index} · {s.name.replace('NVIDIA ', '')}")
        self.lbl_name.setToolTip(
            f"{s.name}\nUUID {s.uuid or '—'}"
            + (f"\n{s.bus_id}" if s.bus_id else ""))
        self.lbl_pstate.setText(s.perf_state or "—")

        self.lbl_util_val.setText(fmt_opt(s.util_gpu, "%"))
        self.bar_util.set_fraction(
            None if s.util_gpu is None else s.util_gpu / 100.0)
        self.bar_util._color = QColor(self.accent)

        if s.mem_used is not None and s.mem_total:
            self.lbl_mem_val.setText(
                f"{fmt_mem(s.mem_used)} / {fmt_mem(s.mem_total)}")
            self.bar_mem.set_fraction(s.mem_used_frac)
        else:
            self.lbl_mem_val.setText("—")
            self.bar_mem.set_fraction(None)

        if s.power_draw is not None and s.power_limit:
            self.lbl_pow_val.setText(
                f"{s.power_draw:.1f} / {s.power_limit:.0f} W")
            self.bar_pow.set_fraction(s.power_frac)
        elif s.power_draw is not None:
            self.lbl_pow_val.setText(f"{s.power_draw:.1f} W")
            self.bar_pow.set_fraction(None)
        else:
            self.lbl_pow_val.setText("—")
            self.bar_pow.set_fraction(None)

        self.lbl_temp.setText(fmt_opt(s.temp_gpu, "°C"))
        self.lbl_fan.setText(fmt_opt(s.fan_speed, "%"))
        self.lbl_encdec.setText(
            f"{fmt_opt(s.util_enc)} / {fmt_opt(s.util_dec)}")

        self.lbl_clocks.setText(
            "SM " + fmt_opt(s.clock_graphics, "MHz")
            + "   ·   MEM " + fmt_opt(s.clock_mem, "MHz")
            + "   ·   VID " + fmt_opt(s.clock_video, "MHz"))
        if s.pcie_gen_current is not None and s.pcie_width_current is not None:
            self.lbl_pcie.setText(
                f"PCIe Gen {s.pcie_gen_current:.0f} ×{s.pcie_width_current:.0f}"
                f"   ·   VBIOS {s.vbios_version or '—'}"
                + (f"   ·   {s.bus_id}" if s.bus_id else ""))
        else:
            self.lbl_pcie.setText("—")

        self._throttle_reasons = (
            [r for r in s.throttle_reasons if r != "GPU Idle"]
            if s.is_throttled else None)
        self._apply_throttle()

    def _apply_throttle(self) -> None:
        t = theme.color
        if self._throttle_reasons is None:
            self.lbl_throttle.setText("● No throttling")
            self.lbl_throttle.setStyleSheet(
                f"color:{t('ok')}; font-weight:600; background:transparent;")
            self.lbl_throttle.setToolTip("No clock throttling active")
        else:
            reasons = self._throttle_reasons or ["throttled"]
            self.lbl_throttle.setText("⚠ " + ", ".join(reasons))
            self.lbl_throttle.setStyleSheet(
                f"color:{t('warn')}; font-weight:600; background:transparent;")
            self.lbl_throttle.setToolTip(
                "Clocks are being limited: " + ", ".join(reasons))


class GpuPanel(QFrame):
    """Vertical per-GPU panel for compact mode.

    Header: [dot] name [P-state] [throttle]
    Then each metric stacked below the previous one:
        LOAD  12 %
        [sparkline]
        PWR   45.2 W
        [sparkline]
        ...
    """

    WIDTH = 320

    def __init__(self, accent: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("gpuPanel")
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(4)

        # ---- header ---------------------------------------------------------
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 2)
        header.setSpacing(6)
        dot = QLabel()
        dot.setFixedSize(9, 9)
        dot.setStyleSheet(f"background-color:{accent}; border-radius:4px;")
        self.lbl_name = QLabel("GPU …")
        self.lbl_name.setStyleSheet(
            f"font-weight:600; font-size:10pt; color:{theme.color('card_name')};"
            " background:transparent;")
        self.lbl_pstate = QLabel("—")
        self.lbl_pstate.setObjectName("badge")
        self.lbl_pstate.setToolTip(
            "Performance state — P0 is maximum performance, P15 minimum "
            "(lower number = higher clocks).")
        self.lbl_throttle = QLabel("●")
        self.lbl_throttle.setStyleSheet(
            f"color:{theme.color('ok')}; font-weight:600; background:transparent;")
        self.lbl_throttle.setToolTip("Clock throttle status")
        self._throttle_reasons: Optional[list] = None
        # label registries for restyle() (theme switching)
        self._caps: List[QLabel] = []
        self._vals: List[QLabel] = []
        header.addWidget(dot)
        header.addWidget(self.lbl_name, 1)
        header.addWidget(self.lbl_pstate)
        header.addWidget(self.lbl_throttle)
        v.addLayout(header)

        # ---- metric blocks (single row: caption · sparkline · value) --------
        # key -> container widget, so rows can be toggled in compact mode
        self._row_widgets: Dict[str, QWidget] = {}

        self.spark_load = Sparkline(accent, y_max=100.0)
        self.spark_power = Sparkline("#fbbf24")
        self.spark_temp = Sparkline("#fb7185")
        self.spark_mem = Sparkline("#a78bfa")

        self.lbl_load = self._metric(v, "GPU load", self.spark_load,
            "GPU load — share of the last sampling interval the GPU was "
            "busy executing work (0–100 %).", key="load")
        self.lbl_power = self._metric(v, "Power", self.spark_power,
            "Instantaneous power draw in watts; the dashed line marks the "
            "active power limit.", key="power")
        self.lbl_temp = self._metric(v, "Temperature", self.spark_temp,
            "GPU core (die) temperature in °C.", key="temp")
        self.lbl_mem = self._metric(v, "Video memory", self.spark_mem,
            "VRAM currently in use; the dashed line marks the total "
            "memory.", key="mem")

        self.spark_fan = Sparkline("#34d399", y_max=100.0)
        self.spark_temp_mem = Sparkline("#f97316")
        self.spark_clk_sm = Sparkline("#22d3ee")
        self.spark_clk_mem = Sparkline("#e879f9")

        self.lbl_fan = self._metric(v, "Fan", self.spark_fan,
            "Fan speed as a percentage of maximum RPM. May be — if the "
            "card reports no fan sensor.", key="fan")
        self.lbl_temp_mem = self._metric(v, "Mem temp", self.spark_temp_mem,
            "Memory (VRAM) temperature in °C. Not reported by all "
            "drivers/cards.", key="temp_mem")
        self.lbl_clk_sm = self._metric(v, "SM clock", self.spark_clk_sm,
            "Current SM / graphics core clock in MHz.", key="clk_sm")
        self.lbl_clk_mem = self._metric(v, "Mem clock", self.spark_clk_mem,
            "Current memory (GDDR/HBM) clock in MHz.", key="clk_mem")

        self.spark_bus = Sparkline("#94a3b8")
        self.lbl_bus = self._metric(v, "Bus (PCIe)", self.spark_bus,
            "PCIe link throughput (Rx + Tx) in MB/s, sampled every second "
            "by `nvidia-smi dmon`. Near 0 while the GPU is idle.",
            key="bus")
        self._bus_link = ""

        # stretch to fill the window (single-column compact layout),
        # but never shrink below WIDTH
        self.setMinimumWidth(self.WIDTH)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _metric(self, v: QVBoxLayout, caption: str, spark: Sparkline,
                tip: str = "", key: str = "") -> QLabel:
        # single row: [caption] [sparkline] [value], in its own container
        # so the whole row can be hidden from the settings dialog
        row = QWidget()
        row.setStyleSheet("background:transparent;")
        hb = QHBoxLayout(row)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(6)
        cap = QLabel(caption)
        cap.setFixedWidth(72)
        cap.setStyleSheet(
            f"color:{theme.color('muted3')}; font-size:8.5pt; background:transparent;")
        val = QLabel("—")
        val.setFixedWidth(76)
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val.setStyleSheet(
            f"font-weight:600; font-size:9.5pt; color:{theme.color('value_text')};"
            " background:transparent;")
        self._caps.append(cap)
        self._vals.append(val)
        if tip:
            for w in (cap, val, spark):
                w.setToolTip(tip)
        hb.addWidget(cap)
        hb.addWidget(spark, 1)
        hb.addWidget(val)
        if key:
            self._row_widgets[key] = row
        v.addWidget(row)
        v.addSpacing(3)
        return val

    def restyle(self) -> None:
        """Re-apply inline label styles from the active theme."""
        t = theme.color
        self.lbl_name.setStyleSheet(
            f"font-weight:600; font-size:10pt; color:{t('card_name')};"
            " background:transparent;")
        for w in self._caps:
            w.setStyleSheet(
                f"color:{t('muted3')}; font-size:8.5pt; background:transparent;")
        for w in self._vals:
            w.setStyleSheet(
                f"font-weight:600; font-size:9.5pt; color:{t('value_text')};"
                " background:transparent;")
        self._apply_throttle()
        for sp in self._all_sparks:
            sp.update()

    def _apply_throttle(self) -> None:
        t = theme.color
        if self._throttle_reasons is None:
            self.lbl_throttle.setText("●")
            self.lbl_throttle.setStyleSheet(
                f"color:{t('ok')}; background:transparent;")
            self.lbl_throttle.setToolTip("No clock throttling")
        else:
            self.lbl_throttle.setText("⚠")
            self.lbl_throttle.setStyleSheet(
                f"color:{t('warn')}; background:transparent;")
            self.lbl_throttle.setToolTip(
                ", ".join(self._throttle_reasons or []) or "throttled")

    def set_row_visible(self, key: str, visible: bool) -> None:
        """Show/hide one metric row (key: load, power, temp, mem, fan,
        temp_mem, clk_sm, clk_mem, bus)."""
        w = self._row_widgets.get(key)
        if w is not None:
            w.setVisible(visible)

    def set_limits(self, power_limit: Optional[float],
                   mem_total: Optional[float]) -> None:
        self.spark_power.set_reference(power_limit)
        self.spark_mem.set_reference(mem_total)

    @property
    def _all_sparks(self) -> tuple:
        return (self.spark_load, self.spark_power, self.spark_temp,
                self.spark_mem, self.spark_fan, self.spark_temp_mem,
                self.spark_clk_sm, self.spark_clk_mem, self.spark_bus)

    def set_bus(self, rx: float, tx: float) -> None:
        """Update the PCIe throughput row (MB/s, from nvidia-smi dmon)."""
        total = rx + tx
        self.lbl_bus.setText(f"{total:.0f} MB/s")
        tip = f"PCIe Rx {rx:.0f} MB/s · Tx {tx:.0f} MB/s"
        if self._bus_link:
            tip += f" · {self._bus_link}"
        self.lbl_bus.setToolTip(tip)
        self.spark_bus.push(time.time(), total)

    def apply_row_visibility(self, vis: Dict[str, bool]) -> None:
        for key, w in self._row_widgets.items():
            w.setVisible(bool(vis.get(key, True)))

    def set_window(self, seconds: float) -> None:
        for sp in self._all_sparks:
            sp.set_window(seconds)

    def set_spark_style(self, style: str) -> None:
        """'line' or 'area' — applied to all sparklines."""
        for sp in self._all_sparks:
            sp.set_style(style)

    def set_sample(self, s) -> None:  # s: GpuSnapshot
        name = f"GPU {s.index} · {s.name.replace('NVIDIA ', '')}"
        self.lbl_name.setText(name)
        self.lbl_name.setToolTip(
            f"{s.name}\nUUID {s.uuid or '—'}"
            + (f"\n{s.bus_id}" if s.bus_id else ""))
        self.setToolTip(f"GPU {s.index} live metrics — one row per metric, "
                        f"sparklines follow the timeline window.")
        self.lbl_pstate.setText(s.perf_state or "—")
        self.lbl_load.setText(fmt_opt(s.util_gpu, "%"))
        self.lbl_power.setText(fmt_opt(s.power_draw, "W"))
        self.lbl_temp.setText(fmt_opt(s.temp_gpu, "°C"))
        self.lbl_mem.setText(fmt_mem_short(s.mem_used))
        self.lbl_fan.setText(fmt_opt(s.fan_speed, "%"))
        self.lbl_temp_mem.setText(fmt_opt(s.temp_mem, "°C"))
        self.lbl_clk_sm.setText(fmt_opt(s.clock_sm, "MHz"))
        self.lbl_clk_mem.setText(fmt_opt(s.clock_mem, "MHz"))
        t = s.timestamp
        self.spark_load.push(t, s.util_gpu)
        self.spark_power.push(t, s.power_draw)
        self.spark_temp.push(t, s.temp_gpu)
        self.spark_mem.push(t, s.mem_used)
        self.spark_fan.push(t, s.fan_speed)
        self.spark_temp_mem.push(t, s.temp_mem)
        self.spark_clk_sm.push(t, s.clock_sm)
        self.spark_clk_mem.push(t, s.clock_mem)
        if s.pcie_gen_current and s.pcie_width_current:
            self._bus_link = (
                f"Gen {int(s.pcie_gen_current)} x{int(s.pcie_width_current)}")
        self._throttle_reasons = (
            [r for r in s.throttle_reasons if r != "GPU Idle"]
            if s.is_throttled else None)
        self._apply_throttle()
