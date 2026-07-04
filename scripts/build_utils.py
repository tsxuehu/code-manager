from __future__ import annotations

import shutil
from pathlib import Path


def clean_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def clean_build_artifacts(project_root: Path) -> None:
    clean_directory(project_root / "build")
    clean_directory(project_root / "dist")
