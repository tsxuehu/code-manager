from __future__ import annotations

import shutil
from pathlib import Path


def clean_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
