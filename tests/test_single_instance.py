import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from code_manager.presentation.single_instance import SingleInstanceGuard, single_instance_server_name


class SingleInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_server_name_is_stable_for_same_home(self) -> None:
        with patch("code_manager.presentation.single_instance.Path.home", return_value=Path("/tmp/user-a")):
            first = single_instance_server_name()
            second = single_instance_server_name()
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("code-manager-"))

    def test_second_acquire_notifies_first_instance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            server_name = f"code-manager-test-{Path(temp_dir).name}"
            activations: list[str] = []

            first = SingleInstanceGuard(lambda: activations.append("shown"), server_name=server_name)
            second = SingleInstanceGuard(lambda: activations.append("second"), server_name=server_name)

            self.assertTrue(first.try_acquire())
            self.assertFalse(second.try_acquire())
            QApplication.processEvents()

            self.assertEqual(activations, ["shown"])


if __name__ == "__main__":
    unittest.main()
