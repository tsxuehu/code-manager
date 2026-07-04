import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QAbstractItemView, QDialog, QHeaderView, QLineEdit, QPushButton

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

    def test_system_name_column_is_wider_and_rows_have_fixed_height(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            service.upsert_system(SystemProfile(name="ops", code_root=Path("D:/workspace/ops")))
            window = MainWindow(service=service)

            self.assertGreaterEqual(window.system_table.columnWidth(0), 160)
            self.assertEqual(window.system_table.rowHeight(0), 36)
            self.assertEqual(window.system_table.rowHeight(1), 36)

    def test_system_table_columns_are_user_resizable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            window = MainWindow(service=service)
            header = window.system_table.horizontalHeader()

            for column in range(window.system_table.columnCount()):
                self.assertEqual(header.sectionResizeMode(column), QHeaderView.Interactive)
            self.assertTrue(header.stretchLastSection())
            self.assertEqual(window.system_table.horizontalScrollBarPolicy(), Qt.ScrollBarAlwaysOff)

    def test_cell_editor_keeps_row_height_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)

            window.system_table.cellDoubleClicked.emit(0, 1)

            self.assertEqual(window.system_table.rowHeight(0), 36)

    def test_double_clicking_system_name_cell_edits_only_that_cell(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)

            window.system_table.cellDoubleClicked.emit(0, 0)

            editor = window.system_table.cellWidget(0, 0)
            path_widget = window.system_table.cellWidget(0, 1)
            operation_buttons = window.system_table.cellWidget(0, 2).findChildren(QPushButton)
            editor_input = editor.findChild(QLineEdit)
            editor_buttons = editor.findChildren(QPushButton)

            self.assertIsNotNone(editor_input)
            self.assertIsNone(path_widget)
            self.assertEqual(editor_input.text(), "aha")
            self.assertEqual([button.text() for button in editor_buttons], ["×", "√"])
            self.assertEqual([button.text() for button in operation_buttons], ["进入", "编辑", "删除"])

    def test_cell_editor_does_not_resize_operation_column(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)
            operation_width = window.system_table.columnWidth(2)

            window.system_table.cellDoubleClicked.emit(0, 1)

            operation_buttons = window.system_table.cellWidget(0, 2).findChildren(QPushButton)
            self.assertEqual(window.system_table.columnWidth(2), operation_width)
            self.assertGreaterEqual(operation_width, 240)
            self.assertEqual([button.text() for button in operation_buttons], ["进入", "编辑", "删除"])

    def test_clicking_edit_button_opens_system_dialog(self) -> None:
        class FakeSystemDialog:
            created_with: SystemProfile | None = None

            def __init__(self, system: SystemProfile | None = None) -> None:
                self.__class__.created_with = system

            def exec(self) -> int:
                return QDialog.DialogCode.Accepted

            def system(self) -> SystemProfile:
                return SystemProfile(name="axo", code_root=Path("D:/workspace-axo"))

        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)

            with patch("code_manager.presentation.main_window.SystemDialog", FakeSystemDialog):
                edit_button = window.system_table.cellWidget(0, 2).findChildren(QPushButton)[1]
                edit_button.click()

            self.assertEqual(FakeSystemDialog.created_with.name, "aha")
            self.assertEqual(service.config.systems[0].name, "axo")
            self.assertEqual(service.config.systems[0].code_root, Path("D:/workspace-axo"))
            self.assertEqual(window.system_table.item(0, 0).text(), "axo")
            self.assertIsNone(window.system_table.cellWidget(0, 0))
            self.assertIsNone(window.system_table.cellWidget(0, 1))

    def test_confirm_cell_edit_applies_system_name_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)

            window.system_table.cellDoubleClicked.emit(0, 0)
            editor = window.system_table.cellWidget(0, 0)
            name_input = editor.findChild(QLineEdit)
            assert name_input is not None
            name_input.setText("axo")

            confirm_button = [button for button in editor.findChildren(QPushButton) if button.text() == "√"][0]
            confirm_button.click()

            self.assertEqual(service.config.systems[0].name, "axo")
            self.assertEqual(service.config.systems[0].code_root, Path("D:/workspace/aha"))
            self.assertEqual(window.system_table.item(0, 0).text(), "axo")
            self.assertIsNone(window.system_table.cellWidget(0, 0))

    def test_confirm_cell_edit_applies_code_root_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)

            window.system_table.cellDoubleClicked.emit(0, 1)
            editor = window.system_table.cellWidget(0, 1)
            path_input = editor.findChild(QLineEdit)
            assert path_input is not None
            path_input.setText("D:/workspace-axo")

            confirm_button = [button for button in editor.findChildren(QPushButton) if button.text() == "√"][0]
            confirm_button.click()

            self.assertEqual(service.config.systems[0].name, "aha")
            self.assertEqual(service.config.systems[0].code_root, Path("D:/workspace-axo"))
            self.assertEqual(window.system_table.item(0, 1).text(), str(Path("D:/workspace-axo")))
            self.assertIsNone(window.system_table.cellWidget(0, 1))

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

    def test_double_clicking_system_cell_does_not_open_detail_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)
            window.system_table.setCurrentCell(0, 0)

            window.system_table.cellDoubleClicked.emit(0, 0)

            self.assertEqual(window.detail_windows, {})

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
