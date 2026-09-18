"""Application themes: named color palettes + a QSS template (string.Template).

`theme.current` is the active theme ("dark" or "light"); `theme.apply(name)`
switches it and rebuilds the style sheet. Widgets with painted (QPainter)
content read `theme.color(key)` directly at paint time, so they follow the
active theme automatically after `update()`.
"""

# ---------------------------------------------------------------------------
# palettes
# ---------------------------------------------------------------------------

_DARK = {
    "window":        "#0f1319",
    "text":          "#dbe2ec",
    "title":         "#f2f5fa",
    "muted":         "#aeb9cb",
    "muted2":        "#8b98ad",
    "muted3":        "#7d8aa0",
    "panel":         "#151b24",
    "panel_border":  "#222b38",
    "panel2":        "#141a23",
    "panel2_border": "#212a37",
    "badge_bg":      "#232c3a",
    "badge_text":    "#c6cfdd",
    "control":       "#1b222d",
    "control_border": "#2a3444",
    "control_hover": "#3d516e",
    "selection_bg":  "#24466e",
    "selection_text": "#ffffff",
    "pressed":       "#182230",
    "checked_bg":    "#17324a",
    "checked_text":  "#7dd3fc",
    "btn_hover_text": "#ffffff",
    "disabled":      "#55607a",
    "accent":        "#38bdf8",
    "tree":          "#121821",
    "tree_alt":      "#161d28",
    "tree_text":     "#c6cfdd",
    "tree_sel":      "#1f3a5f",
    "header_bg":     "#171e29",
    "scroll":        "#2a3444",
    "scroll_hover":  "#3a4759",
    "tooltip_bg":    "#1b222d",
    "tooltip_text":  "#dbe2ec",
    "tooltip_border": "#2a3444",
    "statusbar":     "#0c0f14",
    "splitter":      "#1a212c",
    "card_name":     "#eef2f8",
    "value_text":    "#f2f5fa",
    "track":         "#212a38",
    "warn":          "#fbbf24",
    "ok":            "#34d399",
    # --- painted chart colors (not in QSS) ---
    "chart_bg":      "#0b0f15",
    "chart_border":  "#232c3a",
    "grid":          "#1e2735",
    "legend_text":   "#c6cfdd",
    "legend_off":    "#5b6678",
    "legend_off_bg": "#2a3342",
    "crosshair":     "#93a1b8",
    "tip_bg":        "#11161e",
    "tip_border":    "#2c3648",
    "tip_text":      "#dbe2ec",
    "spark_track":   "#10151d",
}

_LIGHT = {
    "window":        "#f4f6f9",
    "text":          "#232a35",
    "title":         "#10151d",
    "muted":         "#46536a",
    "muted2":        "#55617a",
    "muted3":        "#67718a",
    "panel":         "#ffffff",
    "panel_border":  "#d5dbe4",
    "panel2":        "#f7f9fc",
    "panel2_border": "#dfe4ec",
    "badge_bg":      "#e8edf4",
    "badge_text":    "#3c4657",
    "control":       "#ffffff",
    "control_border": "#c4ccd8",
    "control_hover": "#93a8c4",
    "selection_bg":  "#dbe7f6",
    "selection_text": "#15315a",
    "pressed":       "#eef1f6",
    "checked_bg":    "#e0edfb",
    "checked_text":  "#1d4ed8",
    "btn_hover_text": "#10151d",
    "disabled":      "#9aa4b5",
    "accent":        "#2563eb",
    "tree":          "#ffffff",
    "tree_alt":      "#f5f7fa",
    "tree_text":     "#2b3444",
    "tree_sel":      "#cfe1f8",
    "header_bg":     "#eef1f6",
    "scroll":        "#c2cad6",
    "scroll_hover":  "#a6b1c1",
    "tooltip_bg":    "#ffffff",
    "tooltip_text":  "#232a35",
    "tooltip_border": "#b9c2d0",
    "statusbar":     "#eef1f5",
    "splitter":      "#e3e8ef",
    "card_name":     "#10151d",
    "value_text":    "#10151d",
    "track":         "#e1e6ee",
    "warn":          "#b45309",
    "ok":            "#047857",
    # --- painted chart colors (not in QSS) ---
    "chart_bg":      "#ffffff",
    "chart_border":  "#d5dbe4",
    "grid":          "#e5e9f0",
    "legend_text":   "#39434f",
    "legend_off":    "#98a2b3",
    "legend_off_bg": "#dde2ea",
    "crosshair":     "#7c8aa0",
    "tip_bg":        "#ffffff",
    "tip_border":    "#b9c2d0",
    "tip_text":      "#232a35",
    "spark_track":   "#e8ecf2",
}

PALETTES = {"dark": _DARK, "light": _LIGHT}

# ---------------------------------------------------------------------------
# QSS template (same structure as the original dark sheet, colors named)
# ---------------------------------------------------------------------------

_QSS_TEMPLATE = """
* {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
}

QWidget {
    background-color: $window;
    color: $text;
}

QFrame#panel, QFrame#gpuCard {
    background-color: $panel;
    border: 1px solid $panel_border;
    border-radius: 12px;
}

QFrame#gpuPanel {
    background-color: $panel2;
    border: 1px solid $panel2_border;
    border-radius: 10px;
}

QLabel {
    background: transparent;
}
QLabel#title {
    font-size: 15pt;
    font-weight: 700;
    color: $title;
}
QLabel#subtitle {
    color: $muted2;
    padding-left: 4px;
}
QLabel#sectionTitle {
    color: $muted;
    font-weight: 600;
}
QLabel#dlgLabel {
    color: $muted2;
}

QFrame#sepV {
    background: $control_border;
    max-width: 1px;
    min-width: 1px;
}
QLabel#badge {
    color: $badge_text;
    background-color: $badge_bg;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 9pt;
}

QComboBox {
    background-color: $control;
    border: 1px solid $control_border;
    border-radius: 8px;
    padding: 4px 10px;
    min-width: 64px;
}
QComboBox:hover { border-color: $control_hover; }
QComboBox::drop-down {
    border: 0;
    width: 22px;
}
QComboBox QAbstractItemView {
    background-color: $control;
    border: 1px solid $control_border;
    border-radius: 6px;
    selection-background-color: $selection_bg;
    selection-color: $selection_text;
    outline: 0;
    padding: 2px;
}

QPushButton {
    background-color: $control;
    border: 1px solid $control_border;
    border-radius: 8px;
    padding: 5px 12px;
    color: $text;
}
QPushButton:hover {
    border-color: $accent;
    color: $btn_hover_text;
}
QPushButton:pressed { background-color: $pressed; }
QPushButton:checked {
    background-color: $checked_bg;
    border-color: $accent;
    color: $checked_text;
}
QPushButton:disabled { color: $disabled; }

QTreeWidget {
    background-color: $tree;
    border: 1px solid $panel_border;
    border-radius: 10px;
    alternate-background-color: $tree_alt;
    gridline-color: transparent;
    outline: 0;
}
QTreeWidget::item { padding: 3px 6px; color: $tree_text; }
QTreeWidget::item:selected { background-color: $tree_sel; color: $selection_text; }
QHeaderView::section {
    background-color: $header_bg;
    color: $muted2;
    border: 0;
    border-bottom: 1px solid $panel_border;
    padding: 5px 8px;
    font-weight: 600;
}

QScrollArea {
    border: 0;
    background: transparent;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: $scroll;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: $scroll_hover; }
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: $scroll;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QToolTip {
    background-color: $tooltip_bg;
    color: $tooltip_text;
    border: 1px solid $tooltip_border;
    padding: 4px 8px;
    border-radius: 6px;
}

QStatusBar {
    background: $statusbar;
    color: $muted3;
}

QSplitter::handle {
    background: $splitter;
}
QSplitter::handle:horizontal { width: 3px; }
"""


class Theme:
    """Active theme state + QSS builder."""

    def __init__(self):
        self.current = "dark"

    def color(self, key: str) -> str:
        return PALETTES[self.current][key]

    def build_qss(self, name: str) -> str:
        from string import Template
        return Template(_QSS_TEMPLATE).substitute(PALETTES[name])

    def apply(self, name: str) -> None:
        if name not in PALETTES or name == self.current:
            return
        self.current = name


_active = Theme()


def current() -> str:
    """Active theme name ("dark" or "light")."""
    return _active.current


def color(key: str) -> str:
    """Color value for *key* in the active theme."""
    return _active.color(key)


def build_qss(name: str) -> str:
    """Full application style sheet for *name*."""
    return _active.build_qss(name)


def apply(name: str) -> None:
    """Switch the active theme (does NOT re-apply the QSS to the app)."""
    _active.apply(name)


# default style sheet (dark) for app startup
QSS = build_qss("dark")