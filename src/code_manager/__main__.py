from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from code_manager.infrastructure.autostart import AUTOSTART_ARG
from code_manager.presentation.app_controller import ApplicationController
from code_manager.presentation.app_icon import app_icon_path
from code_manager.presentation.single_instance import SingleInstanceGuard


def main() -> int:
    autostart = AUTOSTART_ARG in sys.argv
    app = QApplication(sys.argv)
    icon_path = app_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))
    controller = ApplicationController()
    guard = SingleInstanceGuard(controller.show_system_list)
    if not guard.try_acquire():
        return 0
    controller.start(autostart=autostart)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
