import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QAbstractItemView, QDialog, QHeaderView, QLineEdit, QPushButton

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import Application, Group, SystemProfile
from code_manager.infrastructure.config_store import JsonConfigStore
from code_manager.infrastructure.git_service import GitService
from code_manager.presentation.app_controller import ApplicationController
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
            self.assertEqual([button.text() for button in buttons], ["进入", "编辑", "删除", "导出"])

    def test_system_management_has_import_button(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            window = MainWindow(service=service)

            buttons = [button.text() for button in window.findChildren(QPushButton)]

            self.assertIn("导入系统", buttons)

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
            self.assertTrue(window.system_table.hasMouseTracking())

    def test_system_table_highlights_row_under_mouse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            window = MainWindow(service=service)

            window.system_table.cellEntered.emit(0, 0)

            self.assertEqual(window.system_table.property("hovered_row"), 0)
            self.assertEqual(window.system_table.item(0, 0).background().color().name(), "#eaf4ff")
            self.assertIn("#eaf4ff", window.system_table.cellWidget(0, 2).styleSheet())

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
            self.assertEqual([button.text() for button in operation_buttons], ["进入", "编辑", "删除", "导出"])

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
            self.assertEqual([button.text() for button in operation_buttons], ["进入", "编辑", "删除", "导出"])

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

    def test_export_button_writes_system_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            system = SystemProfile(
                name="aha",
                code_root=Path("D:/workspace/aha"),
                groups=[Group(chinese_name="服务端", english_name="server")],
                applications=[
                    Application(
                        name="order-service",
                        repository_url="git@example.com:aha/server/order-service.git",
                        group_english_name="server",
                        local_dir_name="order-service",
                    )
                ],
            )
            service.upsert_system(system)
            window = MainWindow(service=service)
            yaml_file = Path(temp_dir) / "aha.yaml"

            with patch(
                "code_manager.presentation.main_window.QFileDialog.getSaveFileName",
                return_value=(str(yaml_file), "YAML"),
            ):
                export_button = window.system_table.cellWidget(0, 2).findChildren(QPushButton)[3]
                export_button.click()

            yaml_text = yaml_file.read_text(encoding="utf-8")
            self.assertIn("name: aha", yaml_text)
            self.assertNotIn("code_root", yaml_text)
            self.assertNotIn("D:/workspace/aha", yaml_text)
            self.assertIn("english_name: server", yaml_text)
            self.assertIn("name: order-service", yaml_text)

    def test_import_button_loads_system_yaml(self) -> None:
        class FakeSystemDialog:
            created_with: SystemProfile | None = None

            def __init__(self, system: SystemProfile | None = None) -> None:
                self.__class__.created_with = system

            def exec(self) -> int:
                return QDialog.DialogCode.Accepted

            def system(self) -> SystemProfile:
                assert self.__class__.created_with is not None
                imported = self.__class__.created_with
                return SystemProfile(name=imported.name, code_root=Path("D:/workspace/imported"))

        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            window = MainWindow(service=service)
            yaml_file = Path(temp_dir) / "aha.yaml"
            yaml_file.write_text(
                """
system:
  name: "aha"
groups:
  - chinese_name: "服务端"
    english_name: "server"
applications:
  - name: "order-service"
    repository_url: "git@example.com:aha/server/order-service.git"
    group_english_name: "server"
    local_dir_name: "order-service"
""",
                encoding="utf-8",
            )

            with patch(
                "code_manager.presentation.main_window.QFileDialog.getOpenFileName",
                return_value=(str(yaml_file), "YAML"),
            ), patch("code_manager.presentation.main_window.SystemDialog", FakeSystemDialog):
                import_button = [
                    button for button in window.findChildren(QPushButton) if button.text() == "导入系统"
                ][0]
                import_button.click()

            self.assertEqual(window.system_table.rowCount(), 1)
            imported = service.config.get_system("aha")
            self.assertEqual(FakeSystemDialog.created_with.name, "aha")
            self.assertEqual(imported.code_root, Path("D:/workspace/imported"))
            self.assertEqual(imported.groups[0].english_name, "server")
            self.assertEqual(imported.applications[0].name, "order-service")

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

            controller = ApplicationController(service=service)
            self.assertEqual(controller.detail_windows, {})

    def test_same_system_detail_window_opens_only_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            controller = ApplicationController(service=service, git_service=GitService())
            controller.show_system_list()
            window = controller.main_window
            assert window is not None

            window.open_system_detail("aha")
            first_detail_window = controller.detail_windows["aha"]
            self.assertFalse(window.isVisible())

            controller.open_system_detail("aha")

            self.assertEqual(len(controller.detail_windows), 1)
            self.assertIs(controller.detail_windows["aha"], first_detail_window)
            first_detail_window.close()

    def test_open_system_detail_closes_main_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            controller = ApplicationController(service=service, git_service=GitService())
            controller.show_system_list()
            window = controller.main_window
            assert window is not None

            window.open_system_detail("aha")

            self.assertIn("aha", controller.detail_windows)
            self.assertTrue(controller.detail_windows["aha"].isVisible())
            self.assertFalse(window.isVisible())
            controller.detail_windows["aha"].close()


if __name__ == "__main__":
    unittest.main()
