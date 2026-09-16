"""GPU Monitor — entry point.

Run:  python main.py
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from gpu_monitor import theme
from gpu_monitor.collector import find_nvidia_smi
from gpu_monitor.mainwindow import MainWindow


def main() -> int:
    if find_nvidia_smi() is None:
        print("WARNING: nvidia-smi not found on PATH or in System32.\n"
              "Install the NVIDIA driver to use this tool.", file=sys.stderr)

    app = QApplication(sys.argv)
    app.setApplicationName("GPU Monitor")
    app.setStyle("Fusion")
    app.setStyleSheet(theme.QSS)

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
