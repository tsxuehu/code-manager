import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import Group, SystemProfile
from code_manager.infrastructure.config_store import JsonConfigStore
from code_manager.presentation.group_config_window import GroupConfigWindow


class GroupConfigWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_group_operation_buttons_are_in_each_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            system = SystemProfile(name="aha", code_root=Path("D:/workspace/aha"))
            system.upsert_group(Group(chinese_name="服务端", english_name="server"))
            service.upsert_system(system)

            window = GroupConfigWindow(service, "aha")
            buttons = window.group_table.cellWidget(0, 2).findChildren(QPushButton)

            self.assertEqual(window.group_table.horizontalHeaderItem(2).text(), "操作")
            self.assertEqual([button.text() for button in buttons], ["编辑", "删除"])


if __name__ == "__main__":
    unittest.main()
