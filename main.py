"""GPU Monitor — entry point.

Run:  python main.py
"""

from __future__ import annotations

import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from gpu_monitor import theme
from gpu_monitor.collector import find_nvidia_smi
from gpu_monitor.mainwindow import MainWindow


def icon_path() -> str | None:
    """Locate icon.ico — in dev it sits next to this file; in a Nuitka
    onefile build, both this module and included data files are extracted
    to the same temp folder, so the same lookup works."""
    for base in (os.path.dirname(os.path.abspath(__file__)),
                 os.path.dirname(sys.executable)):
        cand = os.path.join(base, "icon.ico")
        if os.path.isfile(cand):
            return cand
    return None


def main() -> int:
    if find_nvidia_smi() is None:
        print("WARNING: nvidia-smi not found on PATH or in System32.\n"
              "Install the NVIDIA driver to use this tool.", file=sys.stderr)

    app = QApplication(sys.argv)
    app.setApplicationName("GPU Monitor")
    app.setStyle("Fusion")
    app.setStyleSheet(theme.QSS)

    win = MainWindow()
    ic = icon_path()
    if ic:
        win.setWindowIcon(QIcon(ic))
        app.setWindowIcon(QIcon(ic))
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
