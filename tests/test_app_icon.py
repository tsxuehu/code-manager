import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from code_manager.presentation.app_icon import app_icon_path


class AppIconTests(unittest.TestCase):
    def test_app_icon_path_finds_project_icon(self) -> None:
        icon_path = app_icon_path()

        self.assertIsNotNone(icon_path)
        assert icon_path is not None
        self.assertTrue(icon_path.is_file())
        self.assertEqual(icon_path.name, "code-manager.svg")
        self.assertEqual(icon_path.parent, Path(__file__).resolve().parents[1] / "packaging" / "icons")


if __name__ == "__main__":
    unittest.main()
