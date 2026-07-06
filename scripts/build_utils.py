from __future__ import annotations

import os
import shutil
from pathlib import Path


def icon_source_path(project_root: Path) -> Path:
    icon_path = project_root / "packaging" / "icons" / "code-manager.svg"
    if not icon_path.is_file():
        raise RuntimeError(f"未找到图标文件: {icon_path}")
    return icon_path


def ensure_windows_exe_icon(project_root: Path, *, build_dir: Path | None = None) -> Path:
    svg_path = icon_source_path(project_root)
    if build_dir is not None:
        build_dir.mkdir(parents=True, exist_ok=True)
        ico_path = build_dir / "code-manager.ico"
    else:
        ico_path = svg_path.with_suffix(".ico")
    if ico_path.is_file() and ico_path.stat().st_mtime >= svg_path.stat().st_mtime:
        return ico_path

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    if QGuiApplication.instance() is None:
        QGuiApplication([])

    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise RuntimeError(f"无法加载 SVG 图标: {svg_path}")

    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    if not pixmap.save(str(ico_path), "ICO"):
        raise RuntimeError(f"无法写入 ICO 图标: {ico_path}")
    return ico_path


def clean_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def clean_build_artifacts(project_root: Path) -> None:
    clean_directory(project_root / "build")
    clean_directory(project_root / "dist")
