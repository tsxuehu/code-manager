import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import Application, Group, SystemProfile
from code_manager.infrastructure.config_store import JsonConfigStore
from code_manager.presentation.repository_config_window import RepositoryConfigWindow


class RepositoryConfigWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_application_operation_buttons_are_in_each_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            system = SystemProfile(name="aha", code_root=Path("D:/workspace/aha"))
            system.upsert_group(Group(chinese_name="服务端", english_name="server"))
            system.upsert_application(
                Application(
                    name="axo-manager",
                    repository_url="git@example.com:aha/server/axo-manager.git",
                    group_english_name="server",
                    local_dir_name="axo-manager",
                )
            )
            service.upsert_system(system)

            window = RepositoryConfigWindow(service, "aha")
            app_buttons = window.application_table.cellWidget(0, 5).findChildren(QPushButton)

            self.assertFalse(hasattr(window, "group_table"))
            self.assertEqual(window.application_table.horizontalHeaderItem(5).text(), "操作")
            self.assertEqual([button.text() for button in app_buttons], ["编辑", "删除"])


if __name__ == "__main__":
    unittest.main()
