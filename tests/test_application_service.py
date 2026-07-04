import tempfile
import unittest
from pathlib import Path

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import SystemProfile
from code_manager.infrastructure.config_store import JsonConfigStore


class CodeManagerServiceTests(unittest.TestCase):
    def test_import_repositories_creates_groups_and_applications(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/aha")))

            result = service.import_repositories(
                """
                https://git.example.com/platform/order-service.git
                git@git.example.com:business/payment-api.git
                """
            )

            self.assertEqual(result.imported_count, 2)
            self.assertEqual(result.skipped_count, 0)
            self.assertEqual(
                [group.english_name for group in service.active_system().groups],
                ["platform", "business"],
            )
            self.assertEqual(
                [application.local_dir_name for application in service.active_system().applications],
                ["order-service", "payment-api"],
            )

    def test_import_repositories_skips_duplicate_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/aha")))

            result = service.import_repositories(
                """
                https://git.example.com/platform/order-service.git
                https://git.example.com/platform/order-service.git
                """
            )

            self.assertEqual(result.imported_count, 1)
            self.assertEqual(result.skipped_count, 1)
            self.assertEqual(len(service.active_system().applications), 1)

    def test_import_repositories_accepts_whitespace_separated_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))
            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/aha")))

            result = service.import_repositories(
                "git@codeup.aliyun.com:62cf7f0b487c500c27f70f94/aha/server/axo-worker-bridge.git "
                "git@codeup.aliyun.com:62cf7f0b487c500c27f70f94/aha/server/axo-robot.git "
                "git@codeup.aliyun.com:62cf7f0b487c500c27f70f94/aha/endpoint/soia-web.git"
            )

            self.assertEqual(result.imported_count, 3)
            self.assertEqual(result.skipped_count, 0)
            self.assertEqual(result.errors, [])
            self.assertEqual(
                [application.name for application in service.active_system().applications],
                ["axo-worker-bridge", "axo-robot", "soia-web"],
            )
            self.assertEqual(
                [application.group_english_name for application in service.active_system().applications],
                ["server", "server", "endpoint"],
            )

    def test_system_operations_select_active_system(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CodeManagerService(JsonConfigStore(Path(temp_dir) / "config.json"))

            service.upsert_system(SystemProfile(name="aha", code_root=Path("D:/aha")))
            service.upsert_system(SystemProfile(name="ops", code_root=Path("D:/ops")))
            service.select_system("ops")

            self.assertEqual(service.active_system().name, "ops")
            self.assertEqual(service.active_system().code_root, Path("D:/ops"))


if __name__ == "__main__":
    unittest.main()
