import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import SystemProfile
from code_manager.infrastructure.config_store import JsonConfigStore
from code_manager.infrastructure.git_service import GitService
from code_manager.presentation.app_controller import ApplicationController


class ApplicationControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_show_system_list_reuses_existing_main_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            controller = ApplicationController(service=service, git_service=GitService())

            controller.show_system_list()
            first_window = controller.main_window
            controller.show_system_list()

            self.assertIs(controller.main_window, first_window)
            self.assertTrue(first_window.isVisible())

    def test_open_system_detail_tracks_one_window_per_system(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            controller = ApplicationController(service=service, git_service=GitService())

            controller.open_system_detail("aha")
            first_detail_window = controller.detail_windows["aha"]
            controller.open_system_detail("aha")

            self.assertEqual(len(controller.detail_windows), 1)
            self.assertIs(controller.detail_windows["aha"], first_detail_window)
            first_detail_window.close()

    def test_open_system_detail_closes_main_window_when_opened_from_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            controller = ApplicationController(service=service, git_service=GitService())
            controller.show_system_list()
            main_window = controller.main_window
            assert main_window is not None

            main_window.open_system_detail("aha")

            self.assertFalse(main_window.isVisible())
            self.assertIn("aha", controller.detail_windows)
            controller.detail_windows["aha"].close()

    def test_close_all_windows_closes_main_and_detail_windows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/workspace/aha")))
            controller = ApplicationController(service=service, git_service=GitService())
            controller.show_system_list()
            controller.open_system_detail("aha")
            detail_window = controller.detail_windows["aha"]

            controller.close_all_windows()

            self.assertFalse(detail_window.isVisible())
            self.assertIsNone(controller.main_window)
            self.assertEqual(controller.detail_windows, {})

    def test_tray_menu_contains_required_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            controller = ApplicationController(service=service, git_service=GitService())

            with patch(
                "code_manager.presentation.tray_manager.QSystemTrayIcon.isSystemTrayAvailable",
                return_value=True,
            ):
                controller.tray.setup()

            controller.tray.populate_menu()
            menu = controller.tray._menu
            self.assertIsNotNone(menu)
            action_texts = [action.text() for action in menu.actions()]
            self.assertEqual(action_texts, ["系统列表", "", "暂无系统", "", "关闭所有窗口", "", "退出"])

    def test_tray_menu_lists_configured_systems(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="axo", code_root=Path("/tmp/axo")))
            service.upsert_system(SystemProfile(name="demo", code_root=Path("/tmp/demo")))
            controller = ApplicationController(service=service, git_service=GitService())

            with patch(
                "code_manager.presentation.tray_manager.QSystemTrayIcon.isSystemTrayAvailable",
                return_value=True,
            ):
                controller.tray.setup()

            controller.tray.populate_menu()
            self.assertEqual(controller.tray.system_action_names(), ["axo", "demo"])


if __name__ == "__main__":
    unittest.main()
