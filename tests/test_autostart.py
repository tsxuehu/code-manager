import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_autostart_module():
    return importlib.import_module("code_manager.infrastructure.autostart")


class AutostartServiceTests(unittest.TestCase):
    def test_launch_command_uses_frozen_executable(self) -> None:
        autostart = _load_autostart_module()

        with patch.object(autostart.sys, "frozen", True, create=True), patch.object(
            autostart.shutil,
            "which",
            return_value=None,
        ), patch.object(
            autostart.sys,
            "executable",
            "/opt/code-manager/code-manager",
        ):
            self.assertEqual(
                autostart.launch_command(),
                [str(Path("/opt/code-manager/code-manager").resolve())],
            )

    def test_launch_command_prefers_frozen_executable_over_installed_binary(self) -> None:
        autostart = _load_autostart_module()

        with patch.object(autostart.sys, "frozen", True, create=True), patch.object(
            autostart.shutil,
            "which",
            return_value="/usr/bin/code-manager",
        ), patch.object(
            autostart.sys,
            "executable",
            r"C:\Program Files\code-manager\code-manager.exe",
        ):
            self.assertEqual(
                autostart.launch_command(),
                [str(Path(r"C:\Program Files\code-manager\code-manager.exe").resolve())],
            )

    def test_launch_command_resolves_installed_binary_to_absolute_path(self) -> None:
        autostart = _load_autostart_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            exe_path = Path(temp_dir) / "code-manager.exe"
            exe_path.write_text("", encoding="utf-8")

            with patch.object(autostart.sys, "frozen", False, create=True), patch.object(
                autostart.shutil,
                "which",
                return_value=str(exe_path),
            ):
                self.assertEqual(
                    autostart.launch_command(),
                    [str(exe_path.resolve())],
                )

    def test_launch_command_falls_back_to_python_module(self) -> None:
        autostart = _load_autostart_module()

        with patch.object(autostart.sys, "frozen", False, create=True), patch.object(
            autostart.shutil,
            "which",
            return_value=None,
        ), patch.object(autostart.sys, "executable", "/usr/bin/python3"):
            self.assertEqual(
                autostart.launch_command(),
                [str(Path("/usr/bin/python3").resolve()), "-m", "code_manager"],
            )

    def test_linux_enable_and_disable(self) -> None:
        autostart = _load_autostart_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            desktop_path = home / ".config" / "autostart" / autostart.AUTOSTART_DESKTOP_NAME

            with patch.object(autostart.sys, "platform", "linux"), patch.object(
                autostart.Path,
                "home",
                return_value=home,
            ), patch.object(
                autostart,
                "launch_command",
                return_value=["/usr/bin/code-manager"],
            ):
                service = autostart.AutostartService()
                self.assertFalse(service.is_enabled())

                service.enable()
                self.assertTrue(desktop_path.is_file())
                desktop_text = desktop_path.read_text(encoding="utf-8")
                self.assertIn("Exec=/usr/bin/code-manager --autostart", desktop_text)
                self.assertIn("X-GNOME-Autostart-Delay=5", desktop_text)
                self.assertIn("StartupNotify=false", desktop_text)
                self.assertTrue(service.is_enabled())

                service.disable()
                self.assertFalse(desktop_path.exists())
                self.assertFalse(service.is_enabled())

    def test_macos_enable_and_disable(self) -> None:
        autostart = _load_autostart_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            plist_path = home / "Library" / "LaunchAgents" / autostart.AUTOSTART_PLIST_NAME

            with patch.object(autostart.sys, "platform", "darwin"), patch.object(
                autostart.Path,
                "home",
                return_value=home,
            ), patch.object(
                autostart,
                "launch_command",
                return_value=["/Applications/code-manager.app/Contents/MacOS/code-manager"],
            ):
                service = autostart.AutostartService()
                service.enable()
                self.assertTrue(plist_path.is_file())
                self.assertTrue(service.is_enabled())

                service.disable()
                self.assertFalse(plist_path.exists())
                self.assertFalse(service.is_enabled())

    def test_windows_enable_and_disable(self) -> None:
        autostart = _load_autostart_module()
        enabled = False

        def fake_enable(command: list[str]) -> None:
            nonlocal enabled
            enabled = True
            self.assertEqual(
                command,
                [r"C:\Program Files\code-manager\code-manager.exe", autostart.AUTOSTART_ARG],
            )

        def fake_disable() -> None:
            nonlocal enabled
            enabled = False

        with patch.object(autostart.sys, "platform", "win32"), patch.object(
            autostart,
            "_windows_enable",
            side_effect=fake_enable,
        ), patch.object(
            autostart,
            "_windows_disable",
            side_effect=fake_disable,
        ), patch.object(
            autostart,
            "_windows_is_enabled",
            side_effect=lambda: enabled,
        ), patch.object(
            autostart,
            "launch_command",
            return_value=[r"C:\Program Files\code-manager\code-manager.exe"],
        ):
            service = autostart.AutostartService()
            self.assertFalse(service.is_enabled())

            service.enable()
            self.assertTrue(service.is_enabled())

            service.disable()
            self.assertFalse(service.is_enabled())


if __name__ == "__main__":
    unittest.main()
