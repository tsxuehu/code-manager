import os
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QApplication, QHeaderView, QPushButton

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import Application, SystemProfile
from code_manager.infrastructure.config_store import JsonConfigStore
from code_manager.infrastructure.git_service import GitOperationResult, GitService, RepositoryStatus
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

    def test_local_changes_column_shows_not_cloned_when_repository_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            application = Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )
            service.upsert_system(
                SystemProfile(
                    name="aha",
                    code_root=Path("D:/workspace/aha"),
                    applications=(application,),
                )
            )
            window = SystemDetailWindow(service, GitService(), "aha")
            window.status_by_url[application.repository_url] = RepositoryStatus(
                application=application,
                local_path=application.resolve_local_path(Path("D:/workspace/aha")),
                exists=False,
                branch="-",
                has_local_changes=False,
                has_remote_updates=False,
                message="本地仓库不存在",
            )

            window.refresh_table()

            self.assertEqual(window.repository_table.item(0, 4).text(), "未clone")

    def test_repository_table_shows_group_first_and_sorts_by_group_then_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(
                SystemProfile(
                    name="aha",
                    code_root=Path("D:/workspace/aha"),
                    applications=(
                        Application(
                            name="z-api",
                            repository_url="https://git.example.com/server/z-api.git",
                            group_english_name="server",
                            local_dir_name="z-api",
                        ),
                        Application(
                            name="a-web",
                            repository_url="https://git.example.com/endpoint/a-web.git",
                            group_english_name="endpoint",
                            local_dir_name="a-web",
                        ),
                        Application(
                            name="a-api",
                            repository_url="https://git.example.com/server/a-api.git",
                            group_english_name="server",
                            local_dir_name="a-api",
                        ),
                    ),
                )
            )

            window = SystemDetailWindow(service, GitService(), "aha")

            self.assertEqual(window.repository_table.horizontalHeaderItem(0).text(), "分组")
            self.assertEqual(window.repository_table.horizontalHeaderItem(1).text(), "应用名")
            self.assertEqual(window.repository_table.horizontalHeaderItem(2).text(), "本地路径")
            self.assertEqual(window.repository_table.horizontalHeaderItem(3).text(), "分支")
            self.assertEqual(window.repository_table.horizontalHeaderItem(4).text(), "本地改动")
            self.assertEqual(window.repository_table.horizontalHeaderItem(5).text(), "远端新代码")
            self.assertEqual(window.repository_table.horizontalHeaderItem(6).text(), "操作")
            self.assertEqual(window.repository_table.item(0, 0).text(), "endpoint")
            self.assertEqual(window.repository_table.item(0, 1).text(), "a-web")
            self.assertEqual(window.repository_table.item(1, 0).text(), "server")
            self.assertEqual(window.repository_table.item(1, 1).text(), "a-api")
            self.assertEqual(window.repository_table.item(2, 0).text(), "server")
            self.assertEqual(window.repository_table.item(2, 1).text(), "z-api")

    def test_repository_table_has_open_local_directory_button_per_row(self) -> None:
        opened_paths: list[Path] = []
        terminal_paths: list[Path] = []

        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            application = Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )
            service.upsert_system(
                SystemProfile(
                    name="aha",
                    code_root=Path("D:/workspace/aha"),
                    applications=(application,),
                )
            )
            window = SystemDetailWindow(
                service,
                GitService(),
                "aha",
                open_local_path=opened_paths.append,
                open_terminal_path=terminal_paths.append,
            )

            operation_widget = window.repository_table.cellWidget(0, 6)
            self.assertIsNotNone(operation_widget)
            buttons = operation_widget.findChildren(QPushButton)

            self.assertEqual([button.text() for button in buttons], ["打本目录", "在终端中打开"])

            buttons[0].click()
            buttons[1].click()

            self.assertEqual(opened_paths, [application.resolve_local_path(Path("D:/workspace/aha"))])
            self.assertEqual(terminal_paths, [application.resolve_local_path(Path("D:/workspace/aha"))])

    def test_repository_table_cells_are_not_selectable_and_do_not_take_focus(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(
                SystemProfile(
                    name="aha",
                    code_root=Path("D:/workspace/aha"),
                    applications=(
                        Application(
                            name="order-service",
                            repository_url="https://git.example.com/platform/order-service.git",
                            group_english_name="platform",
                            local_dir_name="order-service",
                        ),
                    ),
                )
            )

            window = SystemDetailWindow(service, GitService(), "aha")

            self.assertEqual(window.repository_table.selectionMode(), QAbstractItemView.NoSelection)
            self.assertEqual(window.repository_table.focusPolicy(), Qt.NoFocus)
            for column in range(window.repository_table.columnCount() - 1):
                item = window.repository_table.item(0, column)
                self.assertFalse(item.flags() & Qt.ItemIsSelectable)

    def test_repository_table_uses_compact_fixed_widths_for_short_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))

            window = SystemDetailWindow(service, GitService(), "aha")
            header = window.repository_table.horizontalHeader()

            self.assertEqual(header.sectionResizeMode(0), QHeaderView.Fixed)
            self.assertEqual(header.sectionResizeMode(1), QHeaderView.Fixed)
            self.assertEqual(header.sectionResizeMode(2), QHeaderView.Stretch)
            self.assertEqual(header.sectionResizeMode(3), QHeaderView.Fixed)
            self.assertEqual(header.sectionResizeMode(4), QHeaderView.Fixed)
            self.assertEqual(header.sectionResizeMode(5), QHeaderView.Fixed)
            self.assertEqual(header.sectionResizeMode(6), QHeaderView.Fixed)
            self.assertLessEqual(window.repository_table.columnWidth(3), 120)
            self.assertLessEqual(window.repository_table.columnWidth(4), 120)
            self.assertLessEqual(window.repository_table.columnWidth(5), 130)

    def test_clone_and_update_respect_submodule_checkbox(self) -> None:
        class RecordingGitService(GitService):
            def __init__(self) -> None:
                self.clone_flags: list[bool] = []
                self.update_flags: list[bool] = []

            def clone(
                self,
                application: Application,
                code_root: Path,
                include_submodules: bool = False,
            ) -> GitOperationResult:
                self.clone_flags.append(include_submodules)
                return GitOperationResult(application, True, "clone 完成")

            def update(
                self,
                application: Application,
                code_root: Path,
                include_submodules: bool = False,
            ) -> GitOperationResult:
                self.update_flags.append(include_submodules)
                return GitOperationResult(application, True, "更新完成")

        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            application = Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )
            service.upsert_system(
                SystemProfile(
                    name="aha",
                    code_root=Path("D:/workspace/aha"),
                    applications=(application,),
                )
            )
            git_service = RecordingGitService()
            window = SystemDetailWindow(service, git_service, "aha")
            captured_operations: list[Callable[[Application], object]] = []

            def capture_run_batch(
                name: str,
                system: SystemProfile,
                operation: Callable[[Application], object],
            ) -> None:
                captured_operations.append(operation)

            window._run_batch = capture_run_batch

            self.assertFalse(window.include_submodules_checkbox.isChecked())
            window.clone_all()
            captured_operations.pop()(application)

            window.include_submodules_checkbox.setChecked(True)
            window.clone_all()
            captured_operations.pop()(application)
            window.update_all()
            captured_operations.pop()(application)

            self.assertEqual(git_service.clone_flags, [False, True])
            self.assertEqual(git_service.update_flags, [True])


if __name__ == "__main__":
    unittest.main()
