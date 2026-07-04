from __future__ import annotations

import argparse
import platform
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path


def read_project_version(project_root: Path) -> str:
    pyproject = project_root / "pyproject.toml"
    match = re.search(
        r'^version\s*=\s*"([^"]+)"',
        pyproject.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        raise RuntimeError("无法从 pyproject.toml 读取版本号")
    return match.group(1)


def deb_architecture() -> str:
    machine = platform.machine().lower()
    mapping = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "armhf",
    }
    if machine in mapping:
        return mapping[machine]

    dpkg = shutil.which("dpkg")
    if dpkg:
        completed = subprocess.run(
            [dpkg, "--print-architecture"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    raise RuntimeError(f"无法识别当前架构: {machine}")


def build_pyinstaller_bundle(
    project_root: Path,
    *,
    name: str,
    dist_dir: Path,
    build_dir: Path,
    clean: bool,
) -> Path:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("未找到 uv，请先安装 uv。")

    entry_file = project_root / "src" / "code_manager" / "__main__.py"
    icon_file = icon_source_path(project_root)
    command = [
        uv,
        "run",
        "--with",
        "PyInstaller>=6.0",
        "pyinstaller",
        "--noconfirm",
        "--windowed",
        "--onedir",
        "--name",
        name,
        "--paths",
        "src",
        "--add-data",
        f"{icon_file.resolve().as_posix()}:.",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(build_dir),
    ]
    if clean:
        command.append("--clean")
    command.append(str(entry_file.relative_to(project_root)).replace("\\", "/"))

    subprocess.run(command, cwd=project_root, check=True)
    bundle_dir = dist_dir / name
    if not bundle_dir.is_dir():
        raise RuntimeError(f"PyInstaller 输出目录不存在: {bundle_dir}")
    return bundle_dir


def write_desktop_file(path: Path) -> None:
    path.write_text(
        textwrap.dedent(
            """\
            [Desktop Entry]
            Type=Application
            Name=代码管理器
            GenericName=代码仓库管理
            Comment=管理多个系统的代码仓库
            Exec=code-manager
            Icon=code-manager
            Terminal=false
            Categories=Development;Utility;
            StartupWMClass=code-manager
            """
        ),
        encoding="utf-8",
    )


def icon_source_path(project_root: Path) -> Path:
    icon_path = project_root / "packaging" / "icons" / "code-manager.svg"
    if not icon_path.is_file():
        raise RuntimeError(f"未找到图标文件: {icon_path}")
    return icon_path


def install_icons(staging_root: Path, project_root: Path, install_root: Path) -> None:
    source_svg = icon_source_path(project_root)
    icon_theme_root = staging_root / "usr" / "share" / "icons" / "hicolor"
    scalable_dir = icon_theme_root / "scalable" / "apps"
    scalable_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_svg, scalable_dir / "code-manager.svg")
    shutil.copy2(source_svg, install_root / "code-manager.svg")

    rsvg_convert = shutil.which("rsvg-convert")
    for size in (48, 128, 256):
        target_dir = icon_theme_root / f"{size}x{size}" / "apps"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / "code-manager.png"
        if rsvg_convert:
            subprocess.run(
                [
                    rsvg_convert,
                    "-w",
                    str(size),
                    "-h",
                    str(size),
                    str(source_svg),
                    "-o",
                    str(target_path),
                ],
                check=True,
            )


def write_postinst_file(path: Path) -> None:
    path.write_text(
        textwrap.dedent(
            """\
            #!/bin/sh
            set -e
            if command -v gtk-update-icon-cache >/dev/null 2>&1; then
              gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
            fi
            """
        ),
        encoding="utf-8",
    )
    path.chmod(0o755)


def write_control_file(
    path: Path,
    *,
    version: str,
    architecture: str,
    installed_size_kb: int,
) -> None:
    path.write_text(
        textwrap.dedent(
            f"""\
            Package: code-manager
            Version: {version}
            Section: utils
            Priority: optional
            Architecture: {architecture}
            Depends: git, libxcb-cursor0, libxkbcommon-x11-0
            Maintainer: code-manager <code-manager@localhost>
            Description: Desktop application for managing application source repositories.
             代码管理器是一个桌面应用，用于统一管理一个系统下所有应用的代码仓库。
            Installed-Size: {installed_size_kb}
            """
        ),
        encoding="utf-8",
    )


def assemble_deb_tree(
    project_root: Path,
    *,
    bundle_dir: Path,
    version: str,
    architecture: str,
) -> Path:
    staging_root = project_root / "build" / "deb" / f"code-manager_{version}_{architecture}"
    if staging_root.exists():
        shutil.rmtree(staging_root)

    install_root = staging_root / "usr" / "lib" / "code-manager"
    install_root.parents[1].joinpath("bin").mkdir(parents=True, exist_ok=True)
    install_root.parents[1].joinpath("share", "applications").mkdir(parents=True, exist_ok=True)
    staging_root.joinpath("DEBIAN").mkdir(parents=True, exist_ok=True)

    shutil.copytree(bundle_dir, install_root)

    launcher = staging_root / "usr" / "bin" / "code-manager"
    launcher.write_text(
        textwrap.dedent(
            """\
            #!/bin/sh
            exec /usr/lib/code-manager/code-manager "$@"
            """
        ),
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    install_icons(staging_root, project_root, install_root)
    write_desktop_file(staging_root / "usr" / "share" / "applications" / "code-manager.desktop")
    write_postinst_file(staging_root / "DEBIAN" / "postinst")

    installed_size_kb = max(1, sum(path.stat().st_size for path in staging_root.rglob("*") if path.is_file()) // 1024)
    write_control_file(
        staging_root / "DEBIAN" / "control",
        version=version,
        architecture=architecture,
        installed_size_kb=installed_size_kb,
    )
    return staging_root


def build_deb_package(staging_root: Path, output_path: Path) -> None:
    dpkg_deb = shutil.which("dpkg-deb")
    if not dpkg_deb:
        raise RuntimeError("未找到 dpkg-deb，请在 Debian/Ubuntu 环境中运行。")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    subprocess.run(
        [dpkg_deb, "--root-owner-group", "--build", str(staging_root), str(output_path)],
        check=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建 Linux deb 包")
    parser.add_argument(
        "--name",
        default="code-manager",
        help="应用名称，默认 code-manager",
    )
    parser.add_argument(
        "--dist-dir",
        default="dist/linux",
        help="PyInstaller 输出目录，默认 dist/linux",
    )
    parser.add_argument(
        "--output-dir",
        default="dist/debian",
        help="deb 输出目录，默认 dist/debian",
    )
    parser.add_argument(
        "--architecture",
        default=None,
        help="deb 架构，默认自动识别",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="不清理 PyInstaller 临时构建缓存",
    )
    args = parser.parse_args(argv)

    if platform.system() != "Linux":
        print("这个脚本用于在 Linux 上构建 deb 包。", file=sys.stderr)
        return 1

    project_root = Path(__file__).resolve().parents[1]
    version = read_project_version(project_root)
    architecture = args.architecture or deb_architecture()
    dist_dir = project_root / args.dist_dir
    build_dir = project_root / "build" / "pyinstaller"
    output_path = project_root / args.output_dir / f"code-manager_{version}_{architecture}.deb"

    try:
        bundle_dir = build_pyinstaller_bundle(
            project_root,
            name=args.name,
            dist_dir=dist_dir,
            build_dir=build_dir,
            clean=not args.no_clean,
        )
        staging_root = assemble_deb_tree(
            project_root,
            bundle_dir=bundle_dir,
            version=version,
            architecture=architecture,
        )
        build_deb_package(staging_root, output_path)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"构建完成: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
