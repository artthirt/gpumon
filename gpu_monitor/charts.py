"""Custom QPainter timeline chart (no external charting dependency).

Features:
  * multiple series with per-series color + optional dashed reference line
  * sliding time window, fixed or auto "nice" Y scale
  * clickable legend (toggle series visibility)
  * hover crosshair + tooltip with all series values at the sampled point
"""

from __future__ import annotations

import math
import time
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter,
                           QPainterPath, QPen)
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import theme

# how much history (seconds) to keep regardless of the visible window
RETENTION_S = 3700.0


class Series:
    """One named data series inside a chart."""

    __slots__ = ("key", "label", "color", "points", "visible",
                 "reference", "reference_label")

    def __init__(self, key: str, label: str, color: str):
        self.key = key
        self.label = label
        self.color = color
        self.points: Deque[Tuple[float, Optional[float]]] = deque()
        self.visible = True
        self.reference: Optional[float] = None
        self.reference_label = ""


def _nice_max(v: float) -> float:
    """Round *v* up to a 'nice' axis maximum (1/2/2.5/5 * 10^k)."""
    if v <= 0:
        return 1.0
    exp = math.floor(math.log10(v))
    base = 10.0 ** exp
    for m in (1.0, 2.0, 2.5, 5.0, 10.0):
        if m * base >= v:
            return m * base
    return 10.0 * base


def _tick_step(window_s: float) -> float:
    for step in (5.0, 10.0, 30.0, 60.0, 300.0, 900.0, 1800.0, 3600.0):
        if window_s / step <= 8:
            return step
    return 7200.0


def fmt_value(v: Optional[float], unit: str = "") -> str:
    if v is None:
        return "—"
    av = abs(v)
    if av >= 1_000_000:
        s = f"{v / 1_000_000:.1f}M"
    elif av >= 10_000:
        s = f"{v / 1000:.0f}k"
    elif av >= 1_000:
        s = f"{v / 1000:.1f}k"
    elif av >= 1:
        s = f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}"
    else:
        s = f"{v:.2f}"
    return f"{s} {unit}".strip()


class TimeSeriesChart(QWidget):
    """Sliding-window multi-series line chart with legend + hover tooltip."""

    MARGIN_L = 52
    MARGIN_R = 12
    MARGIN_T = 46      # title row + legend row
    MARGIN_B = 24

    def __init__(self, title: str, unit: str = "",
                 y_max: Optional[float] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self._fixed_max = y_max
        self._series: List[Series] = []
        self._window = 300.0
        self._t_last: Optional[float] = None
        self._hover: Optional[Tuple[float, float]] = None
        self._legend_rects: List[Tuple[str, QRectF]] = []
        self._style = "area"  # "line" or "area"
        self.setMinimumSize(280, 180)

    # ------------------------------------------------------------------ data
    def add_series(self, key: str, label: str, color: str) -> Series:
        for s in self._series:
            if s.key == key:
                return s
        s = Series(key, label, color)
        self._series.append(s)
        return s

    def set_reference(self, key: str, value: float, label: str = "") -> None:
        for s in self._series:
            if s.key == key:
                s.reference = value
                s.reference_label = label

    def set_window(self, seconds: float) -> None:
        self._window = max(15.0, float(seconds))
        self.update()

    def set_style(self, style: str) -> None:
        """Render style: 'line' (stroke only) or 'area' (stroke + fill)."""
        if style not in ("line", "area") or style == self._style:
            return
        self._style = style
        self.update()

    def push(self, t: float, values: Dict[str, Optional[float]]) -> None:
        """Append one sample (epoch seconds) for every known series key."""
        self._t_last = t
        for s in self._series:
            if s.key in values:
                s.points.append((t, values[s.key]))
                while s.points and s.points[0][0] < t - RETENTION_S:
                    s.points.popleft()
        self.update()

    def history(self):
        """Yield (series_label, t, value) — used by CSV export."""
        for s in self._series:
            for t, v in s.points:
                yield s.label, t, v

    def series(self, key: str) -> Optional[Series]:
        for s in self._series:
            if s.key == key:
                return s
        return None

    # ---------------------------------------------------------------- paint
    def _plot(self) -> QRectF:
        return QRectF(self.MARGIN_L, self.MARGIN_T,
                      max(10.0, self.width() - self.MARGIN_L - self.MARGIN_R),
                      max(10.0, self.height() - self.MARGIN_T - self.MARGIN_B))

    def _t_range(self) -> Tuple[float, float]:
        t1 = self._t_last if self._t_last is not None else time.time()
        return t1 - self._window, t1

    def _y_range(self) -> Tuple[float, float]:
        if self._fixed_max is not None:
            return 0.0, float(self._fixed_max)
        t0, _ = self._t_range()
        vmax = 0.0
        for s in self._series:
            if s.reference is not None:
                vmax = max(vmax, s.reference)
            if s.visible:
                for t, v in s.points:
                    if t >= t0 and v is not None:
                        vmax = max(vmax, v)
        if vmax <= 0:
            return 0.0, 100.0
        return 0.0, _nice_max(vmax * 1.12)

    def paintEvent(self, _ev) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        plot = self._plot()
        if plot.width() < 40 or plot.height() < 30:
            p.end()
            return
        t0, t1 = self._t_range()
        y0, y1 = self._y_range()
        yspan = max(1e-9, y1 - y0)

        def X(t: float) -> float:
            return plot.left() + (t - t0) / (t1 - t0) * plot.width()

        def Y(v: float) -> float:
            return plot.bottom() - (v - y0) / yspan * plot.height()

        # --- title + unit
        f = self.font()
        fb = QFont(f)
        fb.setBold(True)
        p.setFont(fb)
        p.setPen(QColor(theme.color("title")))
        p.drawText(QRectF(plot.left(), 6, 300, 16),
                   Qt.AlignLeft | Qt.AlignVCenter, self.title)
        p.setFont(f)
        p.setPen(QColor(theme.color("muted3")))
        tx = plot.left() + p.fontMetrics().horizontalAdvance(self.title) + 10
        p.drawText(QRectF(tx, 6, 120, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   self.unit)

        # --- plot background
        p.setPen(QPen(QColor(theme.color("chart_border")), 1))
        p.setBrush(QColor(theme.color("chart_bg")))
        p.drawRoundedRect(plot.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        # --- horizontal grid + Y labels
        steps = 4
        for i in range(steps + 1):
            yv = y0 + (y1 - y0) * i / steps
            y = Y(yv)
            p.setPen(QPen(QColor(theme.color("grid")), 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(theme.color("muted3")))
            p.drawText(QRectF(plot.left() - 48, y - 8, 44, 16),
                       Qt.AlignRight | Qt.AlignVCenter, fmt_value(yv))

        # --- X ticks
        step = _tick_step(self._window)
        fmt = "%H:%M:%S" if self._window >= 120 else "%M:%S"
        tt = math.ceil(t0 / step) * step
        while tt <= t1:
            x = X(tt)
            p.setPen(QPen(QColor(theme.color("grid")), 1))
            p.drawLine(QPointF(x, plot.bottom()), QPointF(x, plot.bottom() + 4))
            p.setPen(QColor(theme.color("muted3")))
            p.drawText(QRectF(x - 32, plot.bottom() + 5, 64, 14),
                       Qt.AlignHCenter, time.strftime(fmt, time.localtime(tt)))
            tt += step

        # --- series lines + area fill
        for s in self._series:
            if not s.visible:
                continue
            pts = [(t, v) for t, v in s.points if t0 <= t <= t1 and v is not None]
            if not pts:
                continue
            color = QColor(s.color)
            path = QPainterPath()
            for i, (t, v) in enumerate(pts):
                pt = QPointF(X(t), Y(v))
                if i == 0:
                    path.moveTo(pt)
                else:
                    path.lineTo(pt)
            if len(pts) > 1 and self._style == "area":
                fill = QPainterPath(path)
                fill.lineTo(QPointF(X(pts[-1][0]), plot.bottom()))
                fill.lineTo(QPointF(X(pts[0][0]), plot.bottom()))
                fill.closeSubpath()
                grad = QLinearGradient(0, plot.top(), 0, plot.bottom())
                c_top = QColor(color)
                c_top.setAlpha(95)
                c_bot = QColor(color)
                c_bot.setAlpha(10)
                grad.setColorAt(0.0, c_top)
                grad.setColorAt(1.0, c_bot)
                p.setPen(Qt.NoPen)
                p.setBrush(grad)
                p.drawPath(fill)
            pen = QPen(color, 2.0)
            pen.setJoinStyle(Qt.RoundJoin)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
            # latest-value dot
            lt, lv = pts[-1]
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawEllipse(QPointF(X(lt), Y(lv)), 3.0, 3.0)
            # dashed reference line (power limit, VRAM total, ...)
            if s.reference is not None and y0 <= s.reference <= y1:
                ry = Y(s.reference)
                rpen = QPen(QColor(color), 1.0, Qt.DashLine)
                rpen.setCosmetic(True)
                p.setPen(rpen)
                p.drawLine(QPointF(plot.left(), ry), QPointF(plot.right(), ry))
                p.setPen(color)
                lab = s.reference_label or fmt_value(s.reference, self.unit)
                p.drawText(QRectF(plot.left() + 6, ry - 15, plot.width() - 12, 12),
                           Qt.AlignRight | Qt.AlignVCenter, lab)

        # --- hover crosshair + tooltip
        self._legend_rects = []
        if self._hover is not None and plot.left() <= self._hover[0] <= plot.right():
            self._draw_hover(p, plot, t0, t1, y0, y1)

        # --- legend (drawn last so it sits above everything)
        self._draw_legend(p, plot)
        p.end()

    def _draw_hover(self, p: QPainter, plot: QRectF,
                    t0: float, t1: float, y0: float, y1: float) -> None:
        hover_x, hover_y = self._hover
        hover_t = t0 + (hover_x - plot.left()) / plot.width() * (t1 - t0)
        visible = [s for s in self._series if s.visible]
        if not visible:
            return

        def nearest(s: Series) -> Optional[Tuple[float, float]]:
            best = None
            for t, v in s.points:
                if v is None or not (t0 <= t <= t1):
                    continue
                if best is None or abs(t - hover_t) < abs(best[0] - hover_t):
                    best = (t, v)
            return best

        rows: List[Tuple[Series, Optional[float]]] = []
        sample_t: Optional[float] = None
        for s in visible:
            pt = nearest(s)
            if pt is None:
                continue
            rows.append((s, pt[1]))
            if sample_t is None:
                sample_t = pt[0]
        if not rows or sample_t is None:
            return
        # snap the crosshair to the actual sampled timestamp
        x = plot.left() + (sample_t - t0) / (t1 - t0) * plot.width()

        yspan = max(1e-9, y1 - y0)

        def Y(v: float) -> float:
            return plot.bottom() - (v - y0) / yspan * plot.height()

        p.setPen(QPen(QColor(theme.color("crosshair")), 1.0, Qt.DashLine))
        p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
        for s, v in rows:
            if v is None:
                continue
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(s.color))
            p.drawEllipse(QPointF(x, Y(v)), 3.5, 3.5)

        # tooltip box
        fm = p.fontMetrics()
        lines = [time.strftime("%H:%M:%S", time.localtime(sample_t))] + [
            f"{s.label}: {fmt_value(v, self.unit)}" for s, v in rows]
        box_w = max(fm.horizontalAdvance(l) for l in lines) + 26
        box_h = 16 * len(lines) + 12
        bx = x + 12
        if bx + box_w > plot.right():
            bx = x - 12 - box_w
        by = hover_y + 14
        by = min(max(plot.top() + 6, by), plot.bottom() - box_h - 4)
        p.setPen(QPen(QColor(theme.color("tip_border")), 1))
        tip_bg = QColor(theme.color("tip_bg"))
        tip_bg.setAlpha(235)
        p.setBrush(tip_bg)
        p.drawRoundedRect(QRectF(bx, by, box_w, box_h), 7, 7)
        ty = by + 16
        p.setPen(QColor(theme.color("muted2")))
        p.drawText(QRectF(bx + 12, ty - 11, box_w - 24, 14), Qt.AlignLeft, lines[0])
        for (s, v), line in zip(rows, lines[1:]):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(s.color))
            p.drawRoundedRect(QRectF(bx + 12, ty - 3, 8, 8), 2, 2)
            p.setPen(QColor(theme.color("tip_text")))
            p.drawText(QRectF(bx + 26, ty - 11, box_w - 38, 14), Qt.AlignLeft, line)
            ty += 16

    def _draw_legend(self, p: QPainter, plot: QRectF) -> None:
        x = plot.left()
        y = self.MARGIN_T - 12
        fm = p.fontMetrics()
        for s in self._series:
            w = 16 + fm.horizontalAdvance(s.label) + 12
            if x + w > plot.right() + self.MARGIN_R:
                break
            self._legend_rects.append((s.key, QRectF(x, y - 8, w, 17)))
            swatch = QRectF(x, y - 4, 9, 8)
            if s.visible:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(s.color))
                p.drawRoundedRect(swatch, 2, 2)
                p.setPen(QColor(theme.color("legend_text")))
            else:
                p.setPen(QPen(QColor(theme.color("legend_off")), 1))
                p.setBrush(QColor(theme.color("legend_off_bg")))
                p.drawRoundedRect(swatch, 2, 2)
                p.setPen(QColor(theme.color("legend_off")))
            p.drawText(QRectF(x + 14, y - 8, w - 14, 17),
                       Qt.AlignLeft | Qt.AlignVCenter, s.label)
            x += w

    # ------------------------------------------------------------- mouse
    def mousePressEvent(self, ev) -> None:  # noqa: N802
        for key, r in self._legend_rects:
            if r.contains(ev.position()):
                for s in self._series:
                    if s.key == key:
                        s.visible = not s.visible
                        self.update()
                        break
        ev.accept()

    def mouseMoveEvent(self, ev) -> None:  # noqa: N802
        self._hover = (ev.position().x(), ev.position().y())
        self.update()

    def leaveEvent(self, ev) -> None:  # noqa: N802
        self._hover = None
        self.update()


class Sparkline(QWidget):
    """Tiny inline chart (no axes, no legend) for compact GPU rows.

    Draws a rounded track, gradient area fill, a 1.5 px line, the latest
    value dot and an optional dashed reference (power limit / VRAM total).
    """

    def __init__(self, color: str, y_max: Optional[float] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = QColor(color)
        self._y_max = y_max
        self._reference: Optional[float] = None
        self._window = 300.0
        self._t_last: Optional[float] = None
        self._pts: Deque[Tuple[float, float]] = deque()
        self._style = "area"  # "line" or "area"
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    # ------------------------------------------------------------------ data
    def set_window(self, seconds: float) -> None:
        self._window = max(15.0, float(seconds))
        self.update()

    def set_reference(self, value: Optional[float]) -> None:
        self._reference = value
        self.update()

    def set_style(self, style: str) -> None:
        """Render style: 'line' (stroke only) or 'area' (stroke + fill)."""
        if style not in ("line", "area") or style == self._style:
            return
        self._style = style
        self.update()

    def push(self, t: float, v: Optional[float]) -> None:
        if v is None:
            return
        self._t_last = t
        self._pts.append((t, v))
        while self._pts and self._pts[0][0] < t - RETENTION_S:
            self._pts.popleft()
        self.update()

    # ----------------------------------------------------------------- paint
    def paintEvent(self, _ev) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad = 3.0
        track = QRectF(0.5, 0.5, max(1.0, w - 1), max(1.0, h - 1))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.color("spark_track")))
        p.drawRoundedRect(track, 5, 5)
        if w < 24 or h < 12 or len(self._pts) < 2:
            p.end()
            return

        t1 = self._t_last if self._t_last is not None else time.time()
        t0 = t1 - self._window
        pts = [(t, v) for t, v in self._pts if t >= t0]
        if len(pts) < 2:
            p.end()
            return

        vmax = max(v for _, v in pts)
        if self._reference is not None:
            vmax = max(vmax, self._reference)
        y1 = self._y_max if self._y_max else _nice_max(max(vmax, 1e-6) * 1.25)
        y1 = max(y1, 1e-6)

        def X(t: float) -> float:
            return 2.0 + (t - t0) / (t1 - t0) * (w - 4.0)

        def Y(v: float) -> float:
            return (h - pad) - (v / y1) * (h - 2.0 * pad)

        # dashed reference line
        if self._reference is not None and 0 <= self._reference <= y1:
            ry = Y(self._reference)
            rpen = QPen(self._color, 1.0, Qt.DashLine)
            rpen.setCosmetic(True)
            p.setPen(rpen)
            p.drawLine(QPointF(3, ry), QPointF(w - 3, ry))

        # line (+ optional area fill)
        path = QPainterPath()
        for i, (t, v) in enumerate(pts):
            pt = QPointF(X(t), Y(v))
            if i == 0:
                path.moveTo(pt)
            else:
                path.lineTo(pt)
        if self._style == "area":
            fill = QPainterPath(path)
            fill.lineTo(QPointF(X(pts[-1][0]), h - 1))
            fill.lineTo(QPointF(X(pts[0][0]), h - 1))
            fill.closeSubpath()
            grad = QLinearGradient(0, 0, 0, h)
            c_top = QColor(self._color)
            c_top.setAlpha(110)
            c_bot = QColor(self._color)
            c_bot.setAlpha(15)
            grad.setColorAt(0.0, c_top)
            grad.setColorAt(1.0, c_bot)
            p.setPen(Qt.NoPen)
            p.setBrush(grad)
            p.drawPath(fill)
        pen = QPen(self._color, 1.5)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        # latest value dot
        lt, lv = pts[-1]
        p.setPen(Qt.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(QPointF(X(lt), Y(lv)), 2.2, 2.2)
        p.end()
