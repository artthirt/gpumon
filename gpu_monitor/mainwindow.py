"""Main application window: top bar, GPU cards, process table, charts."""

from __future__ import annotations

import csv
import time
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QByteArray, QSettings, Qt, Slot, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QFileDialog, QFrame, QGridLayout, QGroupBox,
                               QHeaderView, QHBoxLayout, QLabel, QMainWindow,
                               QPushButton, QScrollArea, QSizePolicy, QSplitter,
                               QStatusBar, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)

from . import theme
from .cards import GpuCard, GpuPanel, fmt_mem
from .charts import TimeSeriesChart
from .collector import GpuSampler, PcieDmonSampler

GPU_COLORS = ["#38bdf8", "#fbbf24", "#a78bfa", "#34d399",
              "#f472b6", "#fb7185", "#f97316", "#22d3ee"]

INTERVALS_MS = [(500, "0.5 s"), (1000, "1 s"), (2000, "2 s"),
                (5000, "5 s"), (10000, "10 s")]
WINDOWS_S = [(60, "1 min"), (300, "5 min"), (900, "15 min"),
             (1800, "30 min"), (3600, "1 hour")]


def _lighten(color_hex: str, factor: float = 1.7) -> str:
    c = QColor(color_hex)
    h, s, l, a = c.getHsl()
    return QColor.fromHsl(h, s, min(255, int(l * factor)), a).name()


class ControlsDialog(QDialog):
    """Non-modal dialog holding the sampler/timeline/pause/export controls
    and the per-row visibility checkboxes for compact mode."""

    # (key, caption) — keys match GpuPanel row keys
    ROW_ITEMS: Tuple[Tuple[str, str], ...] = (
        ("load", "GPU load"),
        ("power", "Power"),
        ("temp", "Temperature"),
        ("mem", "Video memory"),
        ("fan", "Fan"),
        ("temp_mem", "Mem temp"),
        ("clk_sm", "SM clock"),
        ("clk_mem", "Mem clock"),
        ("bus", "Bus (PCIe)"),
    )

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Controls")
        self.setModal(False)

        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 16)
        v.setSpacing(10)

        row = QHBoxLayout()
        lab = QLabel("Theme")
        lab.setObjectName("dlgLabel")
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItem("Dark", "dark")
        self.cmb_theme.addItem("Light", "light")
        self.cmb_theme.setToolTip(
            "Application color scheme (dark or light). Saved between runs.")
        row.addWidget(lab)
        row.addWidget(self.cmb_theme, 1)
        v.addLayout(row)

        row = QHBoxLayout()
        lab = QLabel("Refresh interval")
        lab.setObjectName("dlgLabel")
        self.cmb_interval = QComboBox()
        for ms, text in INTERVALS_MS:
            self.cmb_interval.addItem(text, ms)
        row.addWidget(lab)
        self.cmb_interval.setToolTip(
            "How often nvidia-smi is polled. Lower = smoother charts, "
            "slightly more CPU usage.")
        row.addWidget(self.cmb_interval, 1)
        v.addLayout(row)

        row = QHBoxLayout()
        lab = QLabel("Timeline window")
        lab.setObjectName("dlgLabel")
        self.cmb_window = QComboBox()
        for sec, text in WINDOWS_S:
            self.cmb_window.addItem(text, sec)
        row.addWidget(lab)
        self.cmb_window.setToolTip(
            "How much history the timeline charts and compact sparklines "
            "display (older data is dropped).")
        row.addWidget(self.cmb_window, 1)
        v.addLayout(row)

        row = QHBoxLayout()
        lab = QLabel("Chart style")
        lab.setObjectName("dlgLabel")
        self.cmb_chart_style = QComboBox()
        self.cmb_chart_style.addItem("Area (filled)", "area")
        self.cmb_chart_style.addItem("Line", "line")
        row.addWidget(lab)
        self.cmb_chart_style.setToolTip(
            "Draw the timeline charts and sparklines as filled areas or "
            "plain lines.")
        row.addWidget(self.cmb_chart_style, 1)
        v.addLayout(row)

        self.btn_pause = QPushButton("⏸  Pause")
        self.btn_pause.setCheckable(True)
        self.btn_pause.setToolTip(
            "Temporarily stop sampling. The window keeps its last values.")
        v.addWidget(self.btn_pause)

        self.btn_export = QPushButton("⭳  Export CSV")
        self.btn_export.setToolTip(
            "Save the full in-memory history of all charts to a CSV file.")
        v.addWidget(self.btn_export)

        # ---- compact mode row visibility --------------------------------
        self.row_group = QGroupBox("Compact mode rows")
        self.row_group.setToolTip(
            "Choose which metric rows appear in the compact-mode panels.")
        gv = QGridLayout(self.row_group)
        gv.setContentsMargins(12, 10, 12, 10)
        self.row_checks: Dict[str, QCheckBox] = {}
        for i, (key, caption) in enumerate(self.ROW_ITEMS):
            cb = QCheckBox(caption)
            cb.setChecked(True)
            self.row_checks[key] = cb
            gv.addWidget(cb, i // 2, i % 2)
        v.addWidget(self.row_group)

        self.setMinimumWidth(280)

    def row_visibility(self) -> Dict[str, bool]:
        """Current checkbox states: {row key: visible}."""
        return {k: cb.isChecked() for k, cb in self.row_checks.items()}

    def set_row_visibility(self, vis: Dict[str, bool]) -> None:
        for key, cb in self.row_checks.items():
            cb.setChecked(bool(vis.get(key, True)))


class MainWindow(QMainWindow):

    def __init__(self, smi_path: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("GPU Monitor — nvidia-smi")
        self.resize(1320, 840)

        self._cards: List[Optional[GpuCard]] = []
        self._rows: List[Optional[GpuPanel]] = []
        self._last_snaps: Dict[int, object] = {}
        self._uuid_index: Dict[str, int] = {}
        self._meta: Optional[dict] = None
        self._last_status = ""
        self._compact = False
        self._normal_geo = None

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 8)
        root.setSpacing(10)
        root.addWidget(self._build_topbar())

        self.splitter = QSplitter(Qt.Horizontal)
        splitter = self.splitter
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_charts())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 920])
        root.addWidget(splitter, 1)

        # compact-mode container: one GpuPanel per GPU, stacked in one column;
        # wrapped in a scroll area so it scrolls when rows don't fit
        self.compact_box = QWidget()
        self.compact_layout = QVBoxLayout(self.compact_box)
        self.compact_layout.setContentsMargins(2, 0, 2, 2)
        self.compact_layout.setSpacing(10)
        self.compact_layout.addStretch(1)
        self.compact_scroll = QScrollArea()
        self.compact_scroll.setWidgetResizable(True)
        self.compact_scroll.setFrameShape(QScrollArea.NoFrame)
        self.compact_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.compact_scroll.setWidget(self.compact_box)
        self.compact_scroll.hide()
        root.addWidget(self.compact_scroll, 0)

        self.setCentralWidget(central)

        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage("Starting sampler…")

        self.sampler = GpuSampler(smi_path=smi_path, interval_ms=1000)
        self.sampler.meta_ready.connect(self._on_meta)
        self.sampler.snapshot_ready.connect(self._on_snapshots)
        self.sampler.processes_ready.connect(self._on_processes)
        self.sampler.sampler_error.connect(
            lambda msg: self.statusBar().showMessage(f"⚠ {msg}"))
        self.sampler.start()

        self._restoring = False
        self.dlg = ControlsDialog(self)
        for cb in self.dlg.row_checks.values():
            cb.stateChanged.connect(self._on_row_toggle)
        self.dlg.cmb_interval.setCurrentIndex(1)
        self.dlg.cmb_window.setCurrentIndex(1)
        self.dlg.cmb_interval.currentIndexChanged.connect(self._on_interval)
        self.dlg.cmb_window.currentIndexChanged.connect(self._on_window)
        self.dlg.cmb_chart_style.currentIndexChanged.connect(
            self._on_chart_style)
        self.dlg.cmb_theme.currentIndexChanged.connect(self._on_theme)
        self.dlg.btn_pause.toggled.connect(self._on_pause)
        self.dlg.btn_export.clicked.connect(self._export_csv)

        # continuous PCIe Rx/Tx sampler (dmon has its own ~1 s cadence)
        self.pcie_dmon = PcieDmonSampler(self.sampler.smi_path,
                                          parent=self)
        self.pcie_dmon.pcie_update.connect(self._on_pcie)
        self.pcie_dmon.start()

        self._restore_state()

    # ---------------------------------------------------------------- builders
    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("panel")
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 10, 16, 10)
        h.setSpacing(12)

        self.lbl_title = QLabel("⚡ GPU Monitor")
        self.lbl_title.setObjectName("title")
        self.lbl_info = QLabel("connecting to nvidia-smi…")
        self.lbl_info.setObjectName("subtitle")
        self.lbl_info.setMinimumWidth(0)
        self.lbl_info.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.lbl_info.setToolTip(
            "Number of detected GPUs · current refresh interval · local "
            "time of the last sample.")
        h.addWidget(self.lbl_title)
        h.addWidget(self.lbl_info)
        h.addStretch(1)

        self.btn_controls = QPushButton("☰  Controls")
        self.btn_controls.setToolTip("Open controls (refresh, timeline, …)")
        self.btn_controls.clicked.connect(self._open_controls)
        h.addWidget(self.btn_controls)

        sep = QFrame()
        sep.setObjectName("sepV")
        sep.setFrameShape(QFrame.VLine)
        h.addSpacing(6)
        h.addWidget(sep)

        self.btn_compact = QPushButton("▭  Compact")
        self.btn_compact.setCheckable(True)
        self.btn_compact.setToolTip(
            "Compact mode: stacked per-GPU panels with inline sparklines")
        self.btn_compact.toggled.connect(self._on_compact)
        h.addWidget(self.btn_compact)

        self.btn_top = QPushButton("📌  Top")
        self.btn_top.setCheckable(True)
        self.btn_top.setToolTip("Keep this window always on top")
        self.btn_top.toggled.connect(self._on_top)
        h.addWidget(self.btn_top)
        return bar

    def _build_left(self) -> QWidget:
        outer = QWidget()
        v = QVBoxLayout(outer)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        box = QWidget()
        self.cards_layout = QVBoxLayout(box)
        self.cards_layout.setContentsMargins(2, 2, 8, 2)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch(1)
        scroll.setWidget(box)
        v.addWidget(scroll, 3)

        cap = QLabel("Processes on GPUs")
        cap.setObjectName("sectionTitle")
        v.addWidget(cap)

        self.proc_tree = QTreeWidget()
        self.proc_tree.setToolTip(
            "All processes holding a compute/graphics context on a GPU, "
            "from nvidia-smi --query-compute-apps.\n"
            "Columns: PID (process ID) · Process (name) · "
            "GPU (index it runs on) · VRAM (memory it holds; may be — on "
            "some drivers).")
        self.proc_tree.setHeaderLabels(["PID", "Process", "GPU", "VRAM"])
        self.proc_tree.setRootIsDecorated(False)
        self.proc_tree.setAlternatingRowColors(True)
        self.proc_tree.setUniformRowHeights(True)
        hh = self.proc_tree.header()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        v.addWidget(self.proc_tree, 2)
        return outer

    def _build_charts(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        g = QGridLayout(panel)
        g.setContentsMargins(12, 12, 12, 12)
        g.setSpacing(10)

        self.chart_util = TimeSeriesChart("GPU load", "%", y_max=100.0)
        self.chart_power = TimeSeriesChart("Power draw", "W")
        self.chart_temp = TimeSeriesChart("Temperature", "°C")
        self.chart_mem = TimeSeriesChart("Memory used", "MiB")
        self.chart_clock = TimeSeriesChart("Clocks", "MHz")
        for ch, tip in ((
            self.chart_util,
            "Share of each interval the GPU was executing work (0–100 %)."),
            (self.chart_power,
             "Instantaneous power draw in watts."),
            (self.chart_temp,
             "GPU core (die) temperature in °C."),
            (self.chart_mem,
             "VRAM in use in MiB; the dashed line marks total memory."),
            (self.chart_clock,
             "SM (graphics) and memory clocks in MHz.")):
            ch.setToolTip(
                tip + "\nClick a legend entry to show/hide a GPU; hover the "
                      "plot to read exact values.")

        g.addWidget(self.chart_util, 0, 0)
        g.addWidget(self.chart_power, 0, 1)
        g.addWidget(self.chart_temp, 1, 0)
        g.addWidget(self.chart_mem, 1, 1)
        g.addWidget(self.chart_clock, 2, 0, 1, 2)
        for r in range(3):
            g.setRowStretch(r, 1)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)

        self._charts = [self.chart_util, self.chart_power, self.chart_temp,
                        self.chart_mem, self.chart_clock]
        for ch in self._charts:
            ch.set_window(300.0)
        return panel

    # ----------------------------------------------------------------- events
    def _on_meta(self, meta: dict) -> None:
        self._meta = meta
        parts = [f"driver {meta['driver_version']}"]
        if meta.get("cuda_version"):
            parts.append(f"CUDA {meta['cuda_version']}")
        self.lbl_info.setText(" · ".join(parts))

    @Slot(list)
    def _on_snapshots(self, snaps: list) -> None:
        for s in snaps:
            i = s.index
            self._last_snaps[i] = s
            color = GPU_COLORS[i % len(GPU_COLORS)]
            while i >= len(self._cards):
                self._cards.append(None)
            if self._cards[i] is None:
                self._register_gpu(i, s, color)
            self._cards[i].set_sample(s)

            self.chart_util.push(s.timestamp, {f"u{i}": s.util_gpu})
            self.chart_power.push(s.timestamp, {f"p{i}": s.power_draw})
            self.chart_temp.push(s.timestamp, {f"t{i}": s.temp_gpu})
            self.chart_mem.push(s.timestamp, {f"m{i}": s.mem_used})
            self.chart_clock.push(s.timestamp, {
                f"c{i}g": s.clock_graphics, f"c{i}m": s.clock_mem})

            if self._compact:
                created = self._ensure_row(i, s)
                if not created:
                    self._rows[i].set_sample(s)

        self._last_status = (
            f"{len(snaps)} GPU" + ("s" if len(snaps) != 1 else "")
            + f" · refresh {self.dlg.cmb_interval.currentData() / 1000:.1f} s"
            + f" · {time.strftime('%H:%M:%S')}")
        self.statusBar().showMessage(self._last_status)

    def _register_gpu(self, i: int, s, color: str) -> None:
        card = GpuCard(color)
        card.set_sample(s)
        self.cards_layout.insertWidget(len(self._cards) - 1, card)
        self._cards[i] = card
        if s.uuid:
            self._uuid_index[s.uuid] = i

        self.chart_util.add_series(f"u{i}", f"GPU {i}", color)

        self.chart_power.add_series(f"p{i}", f"GPU {i}", color)
        if s.power_limit:
            self.chart_power.set_reference(
                f"p{i}", s.power_limit, f"limit {s.power_limit:.0f} W")

        self.chart_temp.add_series(f"t{i}", f"GPU {i}", color)

        self.chart_mem.add_series(f"m{i}", f"GPU {i}", color)
        if s.mem_total:
            self.chart_mem.set_reference(
                f"m{i}", s.mem_total, f"{s.mem_total / 1024:.1f} GiB")

        self.chart_clock.add_series(f"c{i}g", f"GPU {i} · SM", color)
        self.chart_clock.add_series(
            f"c{i}m", f"GPU {i} · MEM", _lighten(color))

    @Slot(list)
    def _on_processes(self, procs: list) -> None:
        self.proc_tree.setUpdatesEnabled(False)
        self.proc_tree.clear()
        for pr in procs:
            name = pr["name"]
            base = name.replace("/", "\\").rsplit("\\", 1)[-1]
            gpu = self._uuid_index.get(pr["uuid"], "?")
            vram = fmt_mem(pr["mem_mib"]) if pr["mem_mib"] is not None else "—"
            item = QTreeWidgetItem(
                [str(pr["pid"]), base, str(gpu), vram])
            self.proc_tree.addTopLevelItem(item)
        self.proc_tree.setUpdatesEnabled(True)

    # ---------------------------------------------------------------- compact
    def _chart_series(self, key: str):
        for ch in self._charts:
            s = ch.series(key)
            if s is not None:
                return s
        return None

    def _ensure_row(self, i: int, s) -> bool:
        """Create the compact row for GPU *i* (seeded with chart history).

        Returns True if the row was just created (it already applied *s*).
        """
        while i >= len(self._rows):
            self._rows.append(None)
        if self._rows[i] is not None:
            return False
        color = GPU_COLORS[i % len(GPU_COLORS)]
        row = GpuPanel(color)
        row.set_limits(s.power_limit, s.mem_total)
        # clock sparklines seed from the big Clocks chart (SM ≈ graphics
        # clock); fan / mem temp have no big-chart history
        for spark, key in ((row.spark_load, f"u{i}"),
                           (row.spark_power, f"p{i}"),
                           (row.spark_temp, f"t{i}"),
                           (row.spark_mem, f"m{i}"),
                           (row.spark_clk_sm, f"c{i}g"),
                           (row.spark_clk_mem, f"c{i}m")):
            src = self._chart_series(key)
            if src is not None:
                for t, v in src.points:
                    spark.push(t, v)
        row.set_spark_style(self.dlg.cmb_chart_style.currentData())
        row.apply_row_visibility(self.dlg.row_visibility())
        row.set_sample(s)
        self.compact_layout.insertWidget(len(self._rows) - 1, row)
        self._rows[i] = row
        return True

    def _on_compact(self, on: bool) -> None:
        self._compact = on
        if on:
            self._normal_geo = self.saveGeometry()
            self.splitter.hide()
            self.lbl_info.setVisible(False)
            # compact top bar: short title + icon-only buttons
            self.lbl_title.setText("⚡ GPU")
            self.btn_controls.setText("☰")
            self.btn_compact.setText("▭")
            self.btn_top.setText("📌")
            for i, s in sorted(self._last_snaps.items()):
                self._ensure_row(i, s)
            self.compact_scroll.show()
            self.updateGeometry()
            self._fit_compact()
        else:
            self.lbl_info.setVisible(True)
            self.lbl_title.setText("⚡ GPU Monitor")
            self.btn_controls.setText("☰  Controls")
            self.btn_compact.setText("▭  Compact")
            self.btn_top.setText("📌  Top")
            self.compact_scroll.hide()
            self.splitter.show()
            if self._normal_geo is not None:
                self.restoreGeometry(self._normal_geo)
        if not self._restoring:
            self._save_state()

    def _fit_compact(self) -> None:
        """Resize the window to fit the visible compact panels.

        Deferred so Qt recomputes the layout's minimum width first; a
        synchronous resize would be clamped to the stale minimum.
        """
        n = max(1, sum(1 for r in self._rows if r is not None))
        ph = max((r.sizeHint().height()
                  for r in self._rows if r is not None), default=300)
        target_h = n * (ph + 10) + 130
        # cap at the available screen height: taller content scrolls instead
        screen_h = self.screen().availableGeometry().height()
        target_h = min(target_h, max(300, screen_h - 40))
        target = (GpuPanel.WIDTH + 60, target_h)
        QTimer.singleShot(
            100, lambda: self._compact and self.resize(*target))

    def _on_top(self, on: bool) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.show()
        if not self._restoring:
            self._save_state()

    def _open_controls(self) -> None:
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()

    # ---------------------------------------------------------------- controls
    def _on_interval(self, _idx: int) -> None:
        self.sampler.set_interval(self.dlg.cmb_interval.currentData())

    def _on_window(self, _idx: int) -> None:
        sec = float(self.dlg.cmb_window.currentData())
        for ch in self._charts:
            ch.set_window(sec)
        for row in self._rows:
            if row is not None:
                row.set_window(sec)

    def _on_chart_style(self, _idx: int) -> None:
        """Applies to the big timeline charts and the compact sparklines."""
        style = self.dlg.cmb_chart_style.currentData()
        for ch in self._charts:
            ch.set_style(style)
        for row in self._rows:
            if row is not None:
                row.set_spark_style(style)

    def _on_theme(self, _idx: int) -> None:
        """Switch the application color scheme."""
        name = self.dlg.cmb_theme.currentData()
        theme.apply(name)
        QApplication.instance().setStyleSheet(theme.build_qss(name))
        for c in self._cards:
            if c is not None:
                c.restyle()
        for row in self._rows:
            if row is not None:
                row.restyle()
        for ch in self._charts:
            ch.update()
        if not self._restoring:
            self._save_state()

    @Slot(int)
    def _on_row_toggle(self, _state: int) -> None:
        """A compact-mode row checkbox changed — apply to all panels."""
        if self._restoring:
            return
        vis = self.dlg.row_visibility()
        for row in self._rows:
            if row is not None:
                row.apply_row_visibility(vis)
        if self._compact:
            self._fit_compact()
        self._save_state()

    def _on_pause(self, checked: bool) -> None:
        self.sampler.set_paused(checked)
        self.pcie_dmon.set_paused(checked)
        self.dlg.btn_pause.setText(
            "▶  Resume" if checked else "⏸  Pause")
        if checked:
            self.statusBar().showMessage("Sampling paused")

    # ------------------------------------------------------------------ export
    @Slot(int, float, float)
    def _on_pcie(self, idx: int, rx: float, tx: float) -> None:
        row = self._rows[idx] if idx < len(self._rows) else None
        if row is not None:
            row.set_bus(rx, tx)

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export history",
            f"gpu_history_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["chart", "series", "timestamp", "value"])
            for ch in self._charts:
                for label, t, v in ch.history():
                    w.writerow([
                        ch.title, label,
                        time.strftime("%Y-%m-%d %H:%M:%S",
                                      time.localtime(t)),
                        "" if v is None else v])
        self.statusBar().showMessage(f"Exported history → {path}")

    # ------------------------------------------------------------------- state
    @staticmethod
    def _ini() -> QSettings:
        return QSettings(QSettings.IniFormat, QSettings.UserScope,
                         "GPUMonitor", "GPUMonitor")

    def _restore_state(self) -> None:
        s = self._ini()
        # read everything first: applying one value may trigger handlers
        # that save state and overwrite values we haven't read yet
        geom = (s.value("window/geometry", type=QByteArray)
                if s.contains("window/geometry") else None)
        spl = (s.value("window/splitter", type=QByteArray)
               if s.contains("window/splitter") else None)
        interval = int(s.value("settings/interval", 1))
        window = int(s.value("settings/window", 1))
        chart_style = int(s.value("settings/chart_style", 0))
        theme_idx = int(s.value("settings/theme", 0))
        top = bool(s.value("settings/top", False))
        compact = bool(s.value("settings/compact", False))
        hidden = list(s.value("settings/compact_hidden", []) or [])

        if geom is not None:
            self.restoreGeometry(geom)
        if spl is not None:
            self.splitter.restoreState(spl)
        self.dlg.cmb_interval.setCurrentIndex(interval)
        self.dlg.cmb_window.setCurrentIndex(window)
        self.dlg.cmb_chart_style.setCurrentIndex(chart_style)
        self._restoring = True
        try:
            self.dlg.cmb_theme.setCurrentIndex(theme_idx)
            self.dlg.set_row_visibility(
                {k: k not in hidden for k in self.dlg.row_checks})
            if top:
                self.btn_top.setChecked(True)
            if compact:
                self.btn_compact.setChecked(True)
        finally:
            self._restoring = False

    def _save_state(self) -> None:
        s = self._ini()
        s.setValue("window/geometry", self.saveGeometry())
        s.setValue("window/splitter", self.splitter.saveState())
        s.setValue("settings/interval",
                   self.dlg.cmb_interval.currentIndex())
        s.setValue("settings/window", self.dlg.cmb_window.currentIndex())
        s.setValue("settings/chart_style",
                   self.dlg.cmb_chart_style.currentIndex())
        s.setValue("settings/theme", self.dlg.cmb_theme.currentIndex())
        s.setValue("settings/top", self.btn_top.isChecked())
        s.setValue("settings/compact", self._compact)
        s.setValue("settings/compact_hidden",
                   [k for k, v in self.dlg.row_visibility().items()
                    if not v])
        s.sync()

    # ------------------------------------------------------------------- close
    def closeEvent(self, ev) -> None:  # noqa: N802
        self._save_state()
        self.sampler.request_stop()
        self.sampler.wait(1500)
        self.pcie_dmon.request_stop()
        self.pcie_dmon.wait(1500)
        super().closeEvent(ev)
