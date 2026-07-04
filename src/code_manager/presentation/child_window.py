from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow

from code_manager.presentation.window_utils import activate_window


def show_or_raise_window(
    current_window: QMainWindow | None,
    create_window: Callable[[], QMainWindow],
    on_destroyed: Callable[[], None],
) -> QMainWindow:
    if current_window is not None:
        activate_window(current_window)
        return current_window

    window = create_window()
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    window.destroyed.connect(lambda _object=None: on_destroyed())
    window.show()
    return window
