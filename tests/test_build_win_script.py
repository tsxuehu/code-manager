import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_build_script():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build-win.py"
    spec = importlib.util.spec_from_file_location("build_win", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildWinScriptTests(unittest.TestCase):
    def test_build_script_invokes_pyinstaller_for_windows_exe(self) -> None:
        build_win = _load_build_script()

        with patch.object(build_win.platform, "system", return_value="Windows"), patch.object(
            build_win.shutil,
            "which",
            return_value="uv",
        ), patch.object(build_win.subprocess, "run") as run:
            result = build_win.main([])

        self.assertEqual(result, 0)
        command = run.call_args.args[0]
        self.assertEqual(command[:5], ["uv", "run", "--with", "PyInstaller>=6.0", "pyinstaller"])
        self.assertIn("--onefile", command)
        self.assertIn("--windowed", command)
        self.assertIn("--name", command)
        self.assertIn("code-manager", command)
        self.assertIn("--paths", command)
        self.assertIn("src", command)
        self.assertTrue(any(value.endswith("src/code_manager/__main__.py") for value in command))

    def test_build_script_can_build_onedir(self) -> None:
        build_win = _load_build_script()

        with patch.object(build_win.platform, "system", return_value="Windows"), patch.object(
            build_win.shutil,
            "which",
            return_value="uv",
        ), patch.object(build_win.subprocess, "run") as run:
            build_win.main(["--onedir"])

        command = run.call_args.args[0]
        self.assertIn("--onedir", command)
        self.assertNotIn("--onefile", command)


if __name__ == "__main__":
    unittest.main()
