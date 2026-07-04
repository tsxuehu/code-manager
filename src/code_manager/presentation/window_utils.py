from __future__ import annotations

from PySide6.QtWidgets import QWidget


def activate_window(window: QWidget) -> None:
    if window.isMinimized():
        window.showNormal()
    else:
        window.show()
    window.raise_()
    window.activateWindow()
