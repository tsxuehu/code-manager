import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QAbstractItemView, QDialog, QPushButton

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import SystemProfile
from code_manager.infrastructure.config_store import JsonConfigStore
from code_manager.presentation.main_window import MainWindow


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_refresh_table_shows_system_after_add(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            window = MainWindow(service=service)

            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window.refresh_table()

            self.assertEqual(window.system_table.rowCount(), 1)
            self.assertEqual(window.system_table.item(0, 0).text(), "aha")
            self.assertEqual(window.system_table.item(0, 1).text(), str(Path("D:/workspace/aha")))

    def test_add_system_refreshes_visible_table(self) -> None:
        class FakeSystemDialog:
            def exec(self) -> int:
                return QDialog.DialogCode.Accepted

            def system(self) -> SystemProfile:
                return SystemProfile(name="aha", code_root=Path("D:/workspace/aha"))

        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            window = MainWindow(service=service)

            with patch("code_manager.presentation.main_window.SystemDialog", FakeSystemDialog):
                window.add_system()

            self.assertEqual(window.system_table.rowCount(), 1)
            self.assertEqual(window.system_table.currentRow(), -1)
            self.assertEqual(window.system_table.item(0, 0).text(), "aha")

    def test_system_management_window_is_compact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            window = MainWindow(service=service)

            self.assertLessEqual(window.width(), 760)
            self.assertLessEqual(window.height(), 460)

    def test_operation_buttons_are_in_each_system_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)

            operation_widget = window.system_table.cellWidget(0, 2)
            buttons = operation_widget.findChildren(QPushButton)

            self.assertEqual(window.system_table.columnCount(), 3)
            self.assertEqual(window.system_table.horizontalHeaderItem(2).text(), "操作")
            self.assertEqual([button.text() for button in buttons], ["进入", "编辑", "删除"])

    def test_system_list_items_are_not_editable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)

            name_item = window.system_table.item(0, 0)
            path_item = window.system_table.item(0, 1)

            self.assertFalse(name_item.flags() & Qt.ItemIsEditable)
            self.assertFalse(path_item.flags() & Qt.ItemIsEditable)
            self.assertEqual(window.system_table.editTriggers(), QAbstractItemView.NoEditTriggers)
            self.assertEqual(window.system_table.selectionMode(), QAbstractItemView.NoSelection)
            self.assertEqual(window.system_table.focusPolicy(), Qt.NoFocus)
            self.assertEqual(window.system_table.currentRow(), -1)

    def test_same_system_detail_window_opens_only_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)

            window.open_system_detail("aha")
            first_detail_window = window.detail_windows["aha"]
            window.open_system_detail("aha")

            self.assertEqual(len(window.detail_windows), 1)
            self.assertIs(window.detail_windows["aha"], first_detail_window)
            first_detail_window.close()


if __name__ == "__main__":
    unittest.main()
