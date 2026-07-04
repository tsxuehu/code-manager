import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import SystemProfile
from code_manager.infrastructure.config_store import JsonConfigStore
from code_manager.infrastructure.git_service import GitService
from code_manager.presentation.system_detail_window import SystemDetailWindow


class SystemDetailWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_reuses_one_repository_and_one_group_config_window_per_system(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = SystemDetailWindow(service, GitService(), "aha")

            window.open_repository_config()
            first_repository_window = window.repository_config_window
            window.open_repository_config()

            window.open_group_config()
            first_group_window = window.group_config_window
            window.open_group_config()

            self.assertIs(window.repository_config_window, first_repository_window)
            self.assertIs(window.group_config_window, first_group_window)


if __name__ == "__main__":
    unittest.main()
