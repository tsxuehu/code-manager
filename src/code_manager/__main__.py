from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from code_manager.presentation.app_controller import ApplicationController
from code_manager.presentation.app_icon import app_icon_path


def main() -> int:
    app = QApplication(sys.argv)
    icon_path = app_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))
    controller = ApplicationController()
    controller.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
