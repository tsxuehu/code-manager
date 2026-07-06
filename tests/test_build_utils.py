import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


def _load_build_utils():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_utils.py"
    spec = importlib.util.spec_from_file_location("build_utils", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildUtilsTests(unittest.TestCase):
    def test_icon_source_path_raises_when_icon_missing(self) -> None:
        build_utils = _load_build_utils()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            with self.assertRaisesRegex(RuntimeError, "未找到图标文件"):
                build_utils.icon_source_path(project_root)

    def test_ensure_windows_exe_icon_generates_ico_from_svg(self) -> None:
        build_utils = _load_build_utils()
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            icon_dir = project_root / "packaging" / "icons"
            icon_dir.mkdir(parents=True)
            svg_path = icon_dir / "code-manager.svg"
            svg_path.write_text(
                Path(__file__).resolve().parents[1]
                .joinpath("packaging", "icons", "code-manager.svg")
                .read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            build_dir = project_root / "build" / "pyinstaller"

            ico_path = build_utils.ensure_windows_exe_icon(project_root, build_dir=build_dir)

            self.assertEqual(ico_path, build_dir / "code-manager.ico")
            self.assertTrue(ico_path.is_file())
            self.assertGreater(ico_path.stat().st_size, 0)

            first_mtime = ico_path.stat().st_mtime
            cached_path = build_utils.ensure_windows_exe_icon(project_root, build_dir=build_dir)
            self.assertEqual(cached_path, ico_path)
            self.assertEqual(ico_path.stat().st_mtime, first_mtime)


if __name__ == "__main__":
    unittest.main()
