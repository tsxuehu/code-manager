from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QWidget
from shiboken6 import isValid

from code_manager.application.config_service import CodeManagerService
from code_manager.infrastructure.git_service import GitService
from code_manager.presentation.app_icon import app_icon_path
from code_manager.presentation.main_window import MainWindow
from code_manager.presentation.system_detail_window import SystemDetailWindow


class ApplicationController:
    def __init__(
        self,
        service: CodeManagerService | None = None,
        git_service: GitService | None = None,
    ) -> None:
        self.service = service or CodeManagerService()
        self.git_service = git_service or GitService()
        self.main_window: MainWindow | None = None
        self.detail_windows: dict[str, SystemDetailWindow] = {}
        self._tray_icon: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None

    def start(self, *, show_system_list: bool = False) -> None:
        app = QApplication.instance()
        self._setup_tray()
        if app is not None:
            app.setQuitOnLastWindowClosed(self._tray_icon is None)
        if show_system_list:
            self.show_system_list()

    def show_system_list(self) -> None:
        window = self.main_window
        if window is None or not isValid(window):
            window = MainWindow(self.service, self.git_service, controller=self)
            window.destroyed.connect(self._clear_main_window_reference)
            self.main_window = window
        self._activate_window(window)

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
            self._activate_window(existing_window)
            return True

        self.service.select_system(system.name)
        window = SystemDetailWindow(self.service, self.git_service, system.name)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        window.destroyed.connect(lambda _obj=None, name=system.name: self.detail_windows.pop(name, None))
        window.resize(1180, 720)
        window.show()
        self.detail_windows[system.name] = window
        return True

    def close_all_windows(self) -> None:
        for window in list(self.detail_windows.values()):
            if isValid(window):
                window.close()
        self.detail_windows.clear()

        window = self.main_window
        if window is not None and isValid(window):
            window.close()
        self.main_window = None

    def quit(self) -> None:
        self.close_all_windows()
        if self._tray_icon is not None:
            self._tray_icon.hide()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _setup_tray(self) -> None:
        app = QApplication.instance()
        if app is None or not QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon_path = app_icon_path()
        tray_icon = QSystemTrayIcon(QIcon(str(icon_path)) if icon_path is not None else QIcon(), app)
        tray_icon.setToolTip("代码管理器")

        menu = QMenu()
        menu.aboutToShow.connect(self._populate_tray_menu)
        tray_icon.setContextMenu(menu)
        tray_icon.activated.connect(self._handle_tray_activation)
        tray_icon.show()
        self._tray_icon = tray_icon
        self._tray_menu = menu
        self._populate_tray_menu()

    def _populate_tray_menu(self) -> None:
        menu = self._tray_menu
        if menu is None:
            return

        menu.clear()
        menu.addAction("系统列表", self.show_system_list)
        menu.addSeparator()

        systems = self.service.config.systems
        if systems:
            for system in systems:
                menu.addAction(
                    system.name,
                    lambda _checked=False, name=system.name: self.open_system_detail(name),
                )
        else:
            empty_action = menu.addAction("暂无系统")
            empty_action.setEnabled(False)

        menu.addSeparator()
        menu.addAction("关闭所有窗口", self.close_all_windows)
        menu.addSeparator()
        menu.addAction("退出", self.quit)

    def _tray_system_action_names(self) -> list[str]:
        menu = self._tray_menu
        if menu is None:
            return []
        fixed_actions = {"系统列表", "关闭所有窗口", "退出", "暂无系统"}
        names: list[str] = []
        for action in menu.actions():
            if action.isSeparator():
                continue
            text = action.text()
            if text in fixed_actions:
                continue
            names.append(text)
        return names

    def _handle_tray_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_system_list()

    def _clear_main_window_reference(self, _object: object | None = None) -> None:
        self.main_window = None

    def _selected_system_from_main_window(self):
        window = self.main_window
        if window is None or not isValid(window):
            return None
        return window._selected_system_or_none()

    def _activate_window(self, window: QWidget) -> None:
        if window.isMinimized():
            window.showNormal()
        else:
            window.show()
        window.raise_()
        window.activateWindow()
