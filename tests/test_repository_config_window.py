import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QHeaderView, QLineEdit, QPushButton

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import Application, Group, SystemProfile
from code_manager.infrastructure.config_store import JsonConfigStore
from code_manager.presentation.repository_config_window import RepositoryConfigWindow


class RepositoryConfigWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_application_operation_buttons_are_in_each_row(self) -> None:
        with self._window() as window:
            app_buttons = window.application_table.cellWidget(0, 5).findChildren(QPushButton)

            self.assertFalse(hasattr(window, "group_table"))
            self.assertEqual(window.application_table.horizontalHeaderItem(5).text(), "操作")
            self.assertEqual([button.text() for button in app_buttons], ["编辑", "删除"])

    def test_application_table_columns_are_user_resizable(self) -> None:
        with self._window() as window:
            header = window.application_table.horizontalHeader()

            for column in range(window.application_table.columnCount()):
                self.assertEqual(header.sectionResizeMode(column), QHeaderView.Interactive)
            self.assertTrue(header.stretchLastSection())
            self.assertEqual(window.application_table.horizontalScrollBarPolicy(), Qt.ScrollBarAlwaysOff)
            self.assertTrue(window.application_table.hasMouseTracking())

    def test_double_clicking_application_text_cell_edits_only_that_cell(self) -> None:
        with self._window() as window:
            window.application_table.cellDoubleClicked.emit(0, 0)

            editor = window.application_table.cellWidget(0, 0)
            group_widget = window.application_table.cellWidget(0, 1)
            operation_buttons = window.application_table.cellWidget(0, 5).findChildren(QPushButton)
            editor_input = editor.findChild(QLineEdit)
            editor_buttons = editor.findChildren(QPushButton)

            self.assertIsNotNone(editor_input)
            self.assertIsNone(group_widget)
            self.assertEqual(editor_input.text(), "axo-manager")
            self.assertEqual([button.text() for button in editor_buttons], ["×", "√"])
            self.assertEqual([button.text() for button in operation_buttons], ["编辑", "删除"])

    def test_confirm_application_text_cell_edit_applies_change(self) -> None:
        with self._window() as window:
            window.application_table.cellDoubleClicked.emit(0, 2)
            editor = window.application_table.cellWidget(0, 2)
            local_dir_input = editor.findChild(QLineEdit)
            assert local_dir_input is not None
            local_dir_input.setText("axo-manager-new")

            confirm_button = [button for button in editor.findChildren(QPushButton) if button.text() == "√"][0]
            confirm_button.click()

            application = window.service.config.get_system("aha").applications[0]
            self.assertEqual(application.local_dir_name, "axo-manager-new")
            self.assertEqual(window.application_table.item(0, 2).text(), "axo-manager-new")
            self.assertIsNone(window.application_table.cellWidget(0, 2))

    def test_confirm_application_name_cell_edit_applies_change(self) -> None:
        with self._window() as window:
            window.application_table.cellDoubleClicked.emit(0, 0)
            editor = window.application_table.cellWidget(0, 0)
            name_input = editor.findChild(QLineEdit)
            assert name_input is not None
            name_input.setText("axo-manager-new")

            confirm_button = [button for button in editor.findChildren(QPushButton) if button.text() == "√"][0]
            confirm_button.click()

            application = window.service.config.get_system("aha").applications[0]
            self.assertEqual(application.name, "axo-manager-new")
            self.assertEqual(window.application_table.item(0, 0).text(), "axo-manager-new")

    def test_confirm_repository_url_cell_edit_applies_change(self) -> None:
        with self._window() as window:
            window.application_table.cellDoubleClicked.emit(0, 3)
            editor = window.application_table.cellWidget(0, 3)
            url_input = editor.findChild(QLineEdit)
            assert url_input is not None
            url_input.setText("git@example.com:aha/server/axo-manager-new.git")

            confirm_button = [button for button in editor.findChildren(QPushButton) if button.text() == "√"][0]
            confirm_button.click()

            applications = window.service.config.get_system("aha").applications
            self.assertEqual(len(applications), 1)
            self.assertEqual(
                applications[0].repository_url,
                "git@example.com:aha/server/axo-manager-new.git",
            )
            self.assertEqual(
                window.application_table.item(0, 3).text(),
                "git@example.com:aha/server/axo-manager-new.git",
            )

    def test_double_clicking_group_cell_uses_combo_box(self) -> None:
        with self._window() as window:
            window.application_table.cellDoubleClicked.emit(0, 1)

            editor = window.application_table.cellWidget(0, 1)
            combo = editor.findChild(QComboBox)
            buttons = editor.findChildren(QPushButton)

            self.assertIsNotNone(combo)
            self.assertEqual([combo.itemText(index) for index in range(combo.count())], ["server", "endpoint"])
            self.assertEqual(combo.currentText(), "server")
            self.assertEqual([button.text() for button in buttons], ["×", "√"])

    def test_group_cell_editor_removes_underlying_item_to_avoid_ghosting(self) -> None:
        with self._window() as window:
            window.application_table.cellDoubleClicked.emit(0, 1)

            self.assertIsNone(window.application_table.item(0, 1))

    def test_text_cell_editor_removes_underlying_item_to_avoid_ghosting(self) -> None:
        with self._window() as window:
            window.application_table.cellDoubleClicked.emit(0, 0)

            self.assertIsNone(window.application_table.item(0, 0))

    def test_confirm_group_combo_edit_applies_change(self) -> None:
        with self._window() as window:
            window.application_table.cellDoubleClicked.emit(0, 1)
            editor = window.application_table.cellWidget(0, 1)
            combo = editor.findChild(QComboBox)
            assert combo is not None
            combo.setCurrentText("endpoint")

            confirm_button = [button for button in editor.findChildren(QPushButton) if button.text() == "√"][0]
            confirm_button.click()

            application = window.service.config.get_system("aha").applications[0]
            self.assertEqual(application.group_english_name, "endpoint")
            self.assertEqual(window.application_table.item(0, 1).text(), "endpoint")
            self.assertIsNone(window.application_table.cellWidget(0, 1))

    def test_local_path_column_is_not_inline_editable(self) -> None:
        with self._window() as window:
            window.application_table.cellDoubleClicked.emit(0, 4)

            self.assertIsNone(window.application_table.cellWidget(0, 4))

    def _window(self):
        return _RepositoryWindowContext()


class _RepositoryWindowContext:
    def __enter__(self) -> RepositoryConfigWindow:
        self.temp_dir = tempfile.TemporaryDirectory()
        service = CodeManagerService(JsonConfigStore(Path(self.temp_dir.name) / "config.json"))
        system = SystemProfile(name="aha", code_root=Path("D:/workspace/aha"))
        system.upsert_group(Group(chinese_name="服务端", english_name="server"))
        system.upsert_group(Group(chinese_name="终端", english_name="endpoint"))
        system.upsert_application(
            Application(
                name="axo-manager",
                repository_url="git@example.com:aha/server/axo-manager.git",
                group_english_name="server",
                local_dir_name="axo-manager",
            )
        )
        service.upsert_system(system)
        self.window = RepositoryConfigWindow(service, "aha")
        return self.window

    def __exit__(self, exc_type, exc, tb) -> None:
        self.window.close()
        self.temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
