from __future__ import annotations

from PySide6.QtWidgets import QApplication

from code_manager.application.config_service import CodeManagerService
from code_manager.infrastructure.git_service import GitService
from code_manager.presentation.tray_manager import TrayManager
from code_manager.presentation.window_manager import WindowManager


class ApplicationController:
    def __init__(
        self,
        service: CodeManagerService | None = None,
        git_service: GitService | None = None,
    ) -> None:
        self.service = service or CodeManagerService()
        self.git_service = git_service or GitService()
        self.windows = WindowManager(self.service, self.git_service)
        self.tray = TrayManager(
            on_show_system_list=self.show_system_list,
            on_open_system_detail=self.open_system_detail,
            on_close_all_windows=self.close_all_windows,
            on_quit=self.quit,
            list_system_names=self._list_system_names,
        )

    @property
    def main_window(self):
        return self.windows.main_window

    @property
    def detail_windows(self):
        return self.windows.detail_windows

    def start(self, *, show_system_list: bool = False) -> None:
        self.service.sync_auto_start()
        self.tray.setup()
        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(not self.tray.is_available or self.tray.tray_icon is None)
        if show_system_list:
            self.show_system_list()

    def show_system_list(self) -> None:
        self.windows.show_system_list()

    def open_system_detail(self, system_name: str | None = None, parent=None) -> bool:
        return self.windows.open_system_detail(system_name, parent)

    def close_all_windows(self) -> None:
        self.windows.close_all()

    def quit(self) -> None:
        self.close_all_windows()
        self.tray.hide()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _list_system_names(self) -> list[str]:
        return [system.name for system in self.service.config.systems]
