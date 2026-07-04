import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox

from code_manager.domain.models import Application
from code_manager.presentation.dialogs import ApplicationDialog


class DialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_application_dialog_uses_group_combo_box(self) -> None:
        dialog = ApplicationDialog(
            Application(
                name="axo-insight",
                repository_url="git@example.com:aha/server/axo-insight.git",
                group_english_name="server",
                local_dir_name="axo-insight",
            ),
            group_options=["server", "endpoint"],
        )

        self.assertIsInstance(dialog.group_input, QComboBox)
        self.assertEqual(
            [dialog.group_input.itemText(index) for index in range(dialog.group_input.count())],
            ["server", "endpoint"],
        )
        self.assertEqual(dialog.group_input.currentText(), "server")

        dialog.group_input.setCurrentText("endpoint")

        self.assertEqual(dialog.application().group_english_name, "endpoint")


if __name__ == "__main__":
    unittest.main()
