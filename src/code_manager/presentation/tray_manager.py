from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from code_manager.presentation.app_icon import app_icon_path

TRAY_MENU_FIXED_ACTIONS = frozenset({"系统列表", "关闭所有窗口", "退出", "暂无系统"})


class TrayManager:
    def __init__(
        self,
        *,
        on_show_system_list: Callable[[], None],
        on_open_system_detail: Callable[[str], None],
        on_close_all_windows: Callable[[], None],
        on_quit: Callable[[], None],
        list_system_names: Callable[[], list[str]],
    ) -> None:
        self._on_show_system_list = on_show_system_list
        self._on_open_system_detail = on_open_system_detail
        self._on_close_all_windows = on_close_all_windows
        self._on_quit = on_quit
        self._list_system_names = list_system_names
        self._tray_icon: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None

    @property
    def is_available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    @property
    def tray_icon(self) -> QSystemTrayIcon | None:
        return self._tray_icon

    def setup(self) -> None:
        app = QApplication.instance()
        if app is None or not self.is_available:
            return

        icon_path = app_icon_path()
        tray_icon = QSystemTrayIcon(QIcon(str(icon_path)) if icon_path is not None else QIcon(), app)
        tray_icon.setToolTip("代码管理器")

        menu = QMenu()
        menu.aboutToShow.connect(self.populate_menu)
        tray_icon.setContextMenu(menu)
        tray_icon.activated.connect(self._handle_activation)
        tray_icon.show()

        self._tray_icon = tray_icon
        self._menu = menu
        self.populate_menu()

    def hide(self) -> None:
        if self._tray_icon is not None:
            self._tray_icon.hide()

    def populate_menu(self) -> None:
        menu = self._menu
        if menu is None:
            return

        menu.clear()
        menu.addAction("系统列表", self._on_show_system_list)
        menu.addSeparator()

        system_names = self._list_system_names()
        if system_names:
            for system_name in system_names:
                menu.addAction(
                    system_name,
                    lambda _checked=False, name=system_name: self._on_open_system_detail(name),
                )
        else:
            empty_action = menu.addAction("暂无系统")
            empty_action.setEnabled(False)

        menu.addSeparator()
        menu.addAction("关闭所有窗口", self._on_close_all_windows)
        menu.addSeparator()
        menu.addAction("退出", self._on_quit)

    def system_action_names(self) -> list[str]:
        menu = self._menu
        if menu is None:
            return []

        names: list[str] = []
        for action in menu.actions():
            if action.isSeparator():
                continue
            text = action.text()
            if text in TRAY_MENU_FIXED_ACTIONS:
                continue
            names.append(text)
        return names

    def _handle_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_show_system_list()
