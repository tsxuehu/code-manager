from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build_utils import clean_build_artifacts, ensure_windows_exe_icon, icon_source_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建 Windows exe")
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="构建成目录模式，默认构建单文件 exe",
    )
    parser.add_argument(
        "--name",
        default="code-manager",
        help="exe 名称，默认 code-manager",
    )
    parser.add_argument(
        "--dist-dir",
        default="dist/windows",
        help="输出目录，默认 dist/windows",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="不清理 PyInstaller 临时构建缓存",
    )
    args = parser.parse_args(argv)

    if platform.system() != "Windows":
        print("这个脚本用于在 Windows 上构建 exe。", file=sys.stderr)
        return 1

    uv = shutil.which("uv")
    if not uv:
        print("未找到 uv，请先安装 uv。", file=sys.stderr)
        return 1

    project_root = Path(__file__).resolve().parents[1]
    src_dir = project_root / "src"
    entry_file = src_dir / "code_manager" / "__main__.py"
    dist_dir = project_root / args.dist_dir
    build_dir = project_root / "build" / "pyinstaller"

    clean_build_artifacts(project_root)

    icon_file = icon_source_path(project_root)
    exe_icon_file = ensure_windows_exe_icon(project_root, build_dir=build_dir)

    command = [
        uv,
        "run",
        "--with",
        "PyInstaller>=6.0",
        "pyinstaller",
        "--noconfirm",
        "--windowed",
        "--name",
        args.name,
        "--paths",
        "src",
        "--icon",
        str(exe_icon_file.resolve()),
        "--add-data",
        f"{icon_file.resolve()};.",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(build_dir),
    ]
    if not args.no_clean:
        command.append("--clean")
    command.append("--onedir" if args.onedir else "--onefile")
    command.append(str(entry_file.relative_to(project_root)).replace("\\", "/"))

    subprocess.run(command, cwd=project_root, check=True)
    output = dist_dir / (args.name if args.onedir else f"{args.name}.exe")
    print(f"构建完成: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
