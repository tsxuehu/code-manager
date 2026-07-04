import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHeaderView, QLineEdit, QPushButton

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

    def test_group_table_columns_are_user_resizable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            system = SystemProfile(name="aha", code_root=Path("D:/workspace/aha"))
            service.upsert_system(system)
            window = GroupConfigWindow(service, "aha")
            header = window.group_table.horizontalHeader()

            for column in range(window.group_table.columnCount()):
                self.assertEqual(header.sectionResizeMode(column), QHeaderView.Interactive)
            self.assertTrue(header.stretchLastSection())
            self.assertEqual(window.group_table.horizontalScrollBarPolicy(), Qt.ScrollBarAlwaysOff)

    def test_double_clicking_group_cell_edits_only_that_cell(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            system = SystemProfile(name="aha", code_root=Path("D:/workspace/aha"))
            system.upsert_group(Group(chinese_name="服务端", english_name="server"))
            service.upsert_system(system)
            window = GroupConfigWindow(service, "aha")

            window.group_table.cellDoubleClicked.emit(0, 0)

            editor = window.group_table.cellWidget(0, 0)
            english_widget = window.group_table.cellWidget(0, 1)
            operation_buttons = window.group_table.cellWidget(0, 2).findChildren(QPushButton)
            editor_input = editor.findChild(QLineEdit)
            editor_buttons = editor.findChildren(QPushButton)

            self.assertIsNotNone(editor_input)
            self.assertIsNone(english_widget)
            self.assertEqual(editor_input.text(), "服务端")
            self.assertEqual([button.text() for button in editor_buttons], ["×", "√"])
            self.assertEqual([button.text() for button in operation_buttons], ["编辑", "删除"])

    def test_confirm_group_cell_edit_applies_chinese_name_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            system = SystemProfile(name="aha", code_root=Path("D:/workspace/aha"))
            system.upsert_group(Group(chinese_name="服务端", english_name="server"))
            service.upsert_system(system)
            window = GroupConfigWindow(service, "aha")

            window.group_table.cellDoubleClicked.emit(0, 0)
            editor = window.group_table.cellWidget(0, 0)
            name_input = editor.findChild(QLineEdit)
            assert name_input is not None
            name_input.setText("后端")

            confirm_button = [button for button in editor.findChildren(QPushButton) if button.text() == "√"][0]
            confirm_button.click()

            self.assertEqual(service.config.get_system("aha").groups[0].chinese_name, "后端")
            self.assertEqual(service.config.get_system("aha").groups[0].english_name, "server")
            self.assertEqual(window.group_table.item(0, 0).text(), "后端")
            self.assertIsNone(window.group_table.cellWidget(0, 0))

    def test_confirm_group_cell_edit_applies_english_name_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            system = SystemProfile(name="aha", code_root=Path("D:/workspace/aha"))
            system.upsert_group(Group(chinese_name="服务端", english_name="server"))
            service.upsert_system(system)
            window = GroupConfigWindow(service, "aha")

            window.group_table.cellDoubleClicked.emit(0, 1)
            editor = window.group_table.cellWidget(0, 1)
            name_input = editor.findChild(QLineEdit)
            assert name_input is not None
            name_input.setText("backend")

            confirm_button = [button for button in editor.findChildren(QPushButton) if button.text() == "√"][0]
            confirm_button.click()

            self.assertEqual(service.config.get_system("aha").groups[0].chinese_name, "服务端")
            self.assertEqual(service.config.get_system("aha").groups[0].english_name, "backend")
            self.assertEqual(window.group_table.item(0, 1).text(), "backend")
            self.assertIsNone(window.group_table.cellWidget(0, 1))

    def test_group_cell_editor_keeps_row_height_and_operation_column(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            system = SystemProfile(name="aha", code_root=Path("D:/workspace/aha"))
            system.upsert_group(Group(chinese_name="服务端", english_name="server"))
            service.upsert_system(system)
            window = GroupConfigWindow(service, "aha")
            operation_width = window.group_table.columnWidth(2)

            window.group_table.cellDoubleClicked.emit(0, 1)

            self.assertEqual(window.group_table.rowHeight(0), 36)
            self.assertEqual(window.group_table.columnWidth(2), operation_width)


if __name__ == "__main__":
    unittest.main()
