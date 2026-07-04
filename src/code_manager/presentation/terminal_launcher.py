from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path


def open_terminal_at(local_path: Path) -> bool:
    local_path.mkdir(parents=True, exist_ok=True)
    system_name = platform.system()
    if system_name == "Windows":
        creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen(["powershell.exe", "-NoExit"], cwd=local_path, creationflags=creation_flags)
        return True
    if system_name == "Darwin":
        return _open_terminal_on_macos(local_path)
    return _open_terminal_on_linux(local_path)


def _open_terminal_on_linux(local_path: Path) -> bool:
    candidates = [
        os.environ.get("TERMINAL"),
        "x-terminal-emulator",
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "xterm",
    ]
    for candidate in candidates:
        if candidate and shutil.which(candidate):
            subprocess.Popen([candidate], cwd=local_path)
            return True
    return False


def _open_terminal_on_macos(local_path: Path) -> bool:
    if Path("/Applications/iTerm.app").exists() and shutil.which("osascript"):
        quoted_path = shlex.quote(str(local_path))
        script = (
            'tell application "iTerm"\n'
            "  create window with default profile\n"
            "  tell current session of current window\n"
            f'    write text "cd {quoted_path}"\n'
            "  end tell\n"
            "end tell"
        )
        subprocess.Popen(["osascript", "-e", script])
        return True
    if shutil.which("open"):
        subprocess.Popen(["open", "-a", "Terminal", str(local_path)])
        return True
    return False
