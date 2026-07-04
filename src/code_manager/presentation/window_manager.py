from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QWidget
from shiboken6 import isValid

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import SystemProfile
from code_manager.infrastructure.git_service import GitService
from code_manager.presentation.main_window import MainWindow
from code_manager.presentation.system_detail_window import SystemDetailWindow
from code_manager.presentation.window_utils import activate_window


class WindowManager:
    def __init__(self, service: CodeManagerService, git_service: GitService) -> None:
        self.service = service
        self.git_service = git_service
        self.main_window: MainWindow | None = None
        self.detail_windows: dict[str, SystemDetailWindow] = {}

    def show_system_list(self) -> None:
        window = self.main_window
        if window is None or not isValid(window):
            window = MainWindow(self.service, self.git_service, window_manager=self)
            window.destroyed.connect(self._clear_main_window_reference)
            self.main_window = window
        activate_window(window)

    def open_system_detail(self, system_name: str | None = None, parent: QWidget | None = None) -> bool:
        system = (
            self.service.config.get_system(system_name)
            if system_name
            else self._selected_system_from_main_window()
        )
        if not system:
            if parent is not None:
                QMessageBox.information(parent, "请先选择系统", "请先选择一个系统。")
            return False

        existing_window = self.detail_windows.get(system.name)
        if existing_window is not None and isValid(existing_window):
            activate_window(existing_window)
            return True

        self.service.select_system(system.name)
        window = SystemDetailWindow(self.service, self.git_service, system.name)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        window.destroyed.connect(lambda _obj=None, name=system.name: self.detail_windows.pop(name, None))
        window.resize(1180, 720)
        window.show()
        self.detail_windows[system.name] = window
        return True

    def close_all(self) -> None:
        for window in list(self.detail_windows.values()):
            if isValid(window):
                window.close()
        self.detail_windows.clear()

        window = self.main_window
        if window is not None and isValid(window):
            window.close()
        self.main_window = None

    def _selected_system_from_main_window(self) -> SystemProfile | None:
        window = self.main_window
        if window is None or not isValid(window):
            return None
        return window.selected_system()

    def _clear_main_window_reference(self, _object: object | None = None) -> None:
        self.main_window = None
