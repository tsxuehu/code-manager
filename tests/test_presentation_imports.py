import unittest


class PresentationImportTests(unittest.TestCase):
    def test_window_modules_import(self) -> None:
        from code_manager.presentation.group_config_window import GroupConfigWindow
        from code_manager.presentation.main_window import MainWindow
        from code_manager.presentation.repository_config_window import RepositoryConfigWindow
        from code_manager.presentation.system_detail_window import SystemDetailWindow

        self.assertEqual(MainWindow.__name__, "MainWindow")
        self.assertEqual(SystemDetailWindow.__name__, "SystemDetailWindow")
        self.assertEqual(RepositoryConfigWindow.__name__, "RepositoryConfigWindow")
        self.assertEqual(GroupConfigWindow.__name__, "GroupConfigWindow")


if __name__ == "__main__":
    unittest.main()
