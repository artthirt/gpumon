"""Dark, modern Qt style sheet for the whole application."""

QSS = """
* {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
}

QWidget {
    background-color: #0f1319;
    color: #dbe2ec;
}

QFrame#panel, QFrame#gpuCard {
    background-color: #151b24;
    border: 1px solid #222b38;
    border-radius: 12px;
}

QFrame#gpuPanel {
    background-color: #141a23;
    border: 1px solid #212a37;
    border-radius: 10px;
}

QLabel {
    background: transparent;
}
QLabel#title {
    font-size: 15pt;
    font-weight: 700;
    color: #f2f5fa;
}
QLabel#subtitle {
    color: #8b98ad;
    padding-left: 4px;
}
QLabel#sectionTitle {
    color: #aeb9cb;
    font-weight: 600;
}
QLabel#badge {
    color: #c6cfdd;
    background-color: #232c3a;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 9pt;
}

QComboBox {
    background-color: #1b222d;
    border: 1px solid #2a3444;
    border-radius: 8px;
    padding: 4px 10px;
    min-width: 64px;
}
QComboBox:hover { border-color: #3d516e; }
QComboBox::drop-down {
    border: 0;
    width: 22px;
}
QComboBox QAbstractItemView {
    background-color: #1b222d;
    border: 1px solid #2a3444;
    border-radius: 6px;
    selection-background-color: #24466e;
    selection-color: #ffffff;
    outline: 0;
    padding: 2px;
}

QPushButton {
    background-color: #1b222d;
    border: 1px solid #2a3444;
    border-radius: 8px;
    padding: 5px 12px;
    color: #dbe2ec;
}
QPushButton:hover {
    border-color: #38bdf8;
    color: #ffffff;
}
QPushButton:pressed { background-color: #182230; }
QPushButton:checked {
    background-color: #17324a;
    border-color: #38bdf8;
    color: #7dd3fc;
}
QPushButton:disabled { color: #55607a; }

QTreeWidget {
    background-color: #121821;
    border: 1px solid #222b38;
    border-radius: 10px;
    alternate-background-color: #161d28;
    gridline-color: transparent;
    outline: 0;
}
QTreeWidget::item { padding: 3px 6px; color: #c6cfdd; }
QTreeWidget::item:selected { background-color: #1f3a5f; color: #ffffff; }
QHeaderView::section {
    background-color: #171e29;
    color: #8b98ad;
    border: 0;
    border-bottom: 1px solid #222b38;
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
    background: #2a3444;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #3a4759; }
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #2a3444;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QToolTip {
    background-color: #1b222d;
    color: #dbe2ec;
    border: 1px solid #2a3444;
    padding: 4px 8px;
    border-radius: 6px;
}

QStatusBar {
    background: #0c0f14;
    color: #7d8aa0;
}

QSplitter::handle {
    background: #1a212c;
}
QSplitter::handle:horizontal { width: 3px; }
"""
