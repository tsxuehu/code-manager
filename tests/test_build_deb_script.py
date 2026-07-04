import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_build_script():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build-deb.py"
    spec = importlib.util.spec_from_file_location("build_deb", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_project_icon(project_root: Path) -> None:
    icon_dir = project_root / "packaging" / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    (icon_dir / "code-manager.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"></svg>',
        encoding="utf-8",
    )


class BuildDebScriptTests(unittest.TestCase):
    def test_build_script_invokes_pyinstaller_and_dpkg_deb(self) -> None:
        build_deb = _load_build_script()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "pyproject.toml").write_text('version = "0.1.0"\n', encoding="utf-8")
            _write_project_icon(project_root)
            bundle_dir = project_root / "dist" / "linux" / "code-manager"
            bundle_dir.mkdir(parents=True)
            (bundle_dir / "code-manager").write_text("", encoding="utf-8")

            with patch.object(build_deb, "__file__", str(project_root / "scripts" / "build-deb.py")), patch.object(
                build_deb.platform,
                "system",
                return_value="Linux",
            ), patch.object(
                build_deb.shutil,
                "which",
                side_effect=lambda name: {"uv": "uv", "dpkg-deb": "dpkg-deb"}.get(name),
            ), patch.object(
                build_deb,
                "build_pyinstaller_bundle",
                return_value=bundle_dir,
            ) as build_bundle, patch.object(
                build_deb,
                "clean_directory",
            ) as clean_directory, patch.object(
                build_deb.subprocess,
                "run",
            ) as run:
                result = build_deb.main([])

            self.assertEqual(result, 0)
            self.assertEqual(clean_directory.call_count, 2)
            build_bundle.assert_called_once()
            command = run.call_args.args[0]
            self.assertEqual(command[0], "dpkg-deb")
            self.assertIn("--root-owner-group", command)
            self.assertTrue(str(command[-1]).endswith("code-manager_0.1.0_amd64.deb"))

    def test_build_script_rejects_non_linux(self) -> None:
        build_deb = _load_build_script()

        with patch.object(build_deb.platform, "system", return_value="Windows"):
            result = build_deb.main([])

        self.assertEqual(result, 1)

    def test_assemble_deb_tree_creates_launcher_and_desktop_file(self) -> None:
        build_deb = _load_build_script()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            _write_project_icon(project_root)
            bundle_dir = project_root / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "code-manager").write_text("binary", encoding="utf-8")

            staging_root = build_deb.assemble_deb_tree(
                project_root,
                bundle_dir=bundle_dir,
                version="0.1.0",
                architecture="amd64",
            )

            launcher = staging_root / "usr" / "bin" / "code-manager"
            desktop = staging_root / "usr" / "share" / "applications" / "code-manager.desktop"
            control = staging_root / "DEBIAN" / "control"
            icon = staging_root / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps" / "code-manager.svg"
            postinst = staging_root / "DEBIAN" / "postinst"

            self.assertTrue(launcher.is_file())
            self.assertIn("/usr/lib/code-manager/code-manager", launcher.read_text(encoding="utf-8"))
            self.assertTrue(desktop.is_file())
            self.assertIn("Name=代码管理器", desktop.read_text(encoding="utf-8"))
            self.assertIn("Icon=code-manager", desktop.read_text(encoding="utf-8"))
            self.assertTrue(icon.is_file())
            self.assertTrue(postinst.is_file())
            self.assertTrue(control.is_file())
            self.assertIn("Architecture: amd64", control.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
