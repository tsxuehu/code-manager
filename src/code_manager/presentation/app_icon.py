from __future__ import annotations

import sys
from pathlib import Path


def icon_candidates() -> list[Path]:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "code-manager.svg")
        executable_dir = Path(sys.executable).resolve().parent
        candidates.append(executable_dir / "code-manager.svg")

    module_root = Path(__file__).resolve().parents[3]
    candidates.extend(
        [
            module_root / "packaging" / "icons" / "code-manager.svg",
            Path("/usr/share/icons/hicolor/scalable/apps/code-manager.svg"),
            Path("/usr/lib/code-manager/code-manager.svg"),
        ]
    )
    return candidates


def app_icon_path() -> Path | None:
    for path in icon_candidates():
        if path.is_file():
            return path
    return None
