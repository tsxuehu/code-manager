from __future__ import annotations

import plistlib
import shlex
import shutil
import sys
from pathlib import Path

AUTOSTART_DESKTOP_NAME = "code-manager.desktop"
AUTOSTART_PLIST_NAME = "com.code-manager.app.plist"
WINDOWS_RUN_VALUE_NAME = "CodeManager"
AUTOSTART_ARG = "--autostart"
LINUX_AUTOSTART_DELAY_SECONDS = 5


def launch_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve())]

    installed = shutil.which("code-manager")
    if installed:
        return [str(Path(installed).resolve())]

    return [str(Path(sys.executable).resolve()), "-m", "code_manager"]


def autostart_exec_command() -> list[str]:
    return [*launch_command(), AUTOSTART_ARG]


class AutostartService:
    def is_enabled(self) -> bool:
        if sys.platform == "win32":
            return _windows_is_enabled()
        if sys.platform == "darwin":
            return _macos_plist_path().is_file()
        return _linux_desktop_path().is_file()

    def enable(self) -> None:
        command = autostart_exec_command()
        if sys.platform == "win32":
            _windows_enable(command)
            return
        if sys.platform == "darwin":
            _macos_enable(command)
            return
        _linux_enable(command)

    def disable(self) -> None:
        if sys.platform == "win32":
            _windows_disable()
            return
        if sys.platform == "darwin":
            _macos_disable()
            return
        _linux_disable()


def _linux_desktop_path() -> Path:
    return Path.home() / ".config" / "autostart" / AUTOSTART_DESKTOP_NAME


def _macos_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / AUTOSTART_PLIST_NAME


def _linux_enable(command: list[str]) -> None:
    desktop_path = _linux_desktop_path()
    desktop_path.parent.mkdir(parents=True, exist_ok=True)
    exec_line = " ".join(shlex.quote(part) for part in command)
    desktop_path.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Version=1.0",
                "Name=代码管理器",
                "Comment=代码仓库管理",
                f"Exec={exec_line}",
                "Terminal=false",
                "StartupNotify=false",
                "Hidden=false",
                "X-GNOME-Autostart-enabled=true",
                f"X-GNOME-Autostart-Delay={LINUX_AUTOSTART_DELAY_SECONDS}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _linux_disable() -> None:
    desktop_path = _linux_desktop_path()
    if desktop_path.exists():
        desktop_path.unlink()


def _macos_enable(command: list[str]) -> None:
    plist_path = _macos_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    with plist_path.open("wb") as file:
        plistlib.dump(
            {
                "Label": "com.code-manager.app",
                "ProgramArguments": command,
                "RunAtLoad": True,
            },
            file,
        )


def _macos_disable() -> None:
    plist_path = _macos_plist_path()
    if plist_path.exists():
        plist_path.unlink()


def _windows_enable(command: list[str]) -> None:
    import subprocess

    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(
            key,
            WINDOWS_RUN_VALUE_NAME,
            0,
            winreg.REG_SZ,
            subprocess.list2cmdline(command),
        )


def _windows_disable() -> None:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, WINDOWS_RUN_VALUE_NAME)
    except FileNotFoundError:
        return


def _windows_is_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        ) as key:
            winreg.QueryValueEx(key, WINDOWS_RUN_VALUE_NAME)
        return True
    except FileNotFoundError:
        return False
