import unittest
from pathlib import Path

from code_manager.domain.models import Application, CodeManagerConfig, Group, SystemProfile


class ModelTests(unittest.TestCase):
    def test_application_resolves_repository_path(self) -> None:
        system = SystemProfile(
            name="aha",
            code_root=Path("D:/workspace"),
            groups=[Group(chinese_name="平台", english_name="platform")],
            applications=[
                Application(
                    name="order-service",
                    repository_url="https://git.example.com/platform/order-service.git",
                    group_english_name="platform",
                    local_dir_name="order-service",
                )
            ],
        )

        self.assertEqual(
            system.applications[0].resolve_local_path(system.code_root),
            Path("D:/workspace") / "platform" / "order-service",
        )

    def test_config_upserts_group_by_english_name(self) -> None:
        system = SystemProfile(name="aha")

        system.upsert_group(Group(chinese_name="平台", english_name="platform"))
        system.upsert_group(Group(chinese_name="基础平台", english_name="platform"))

        self.assertEqual(len(system.groups), 1)
        self.assertEqual(system.groups[0].chinese_name, "基础平台")

    def test_config_upserts_application_by_repository_url(self) -> None:
        system = SystemProfile(name="aha")

        system.upsert_application(
            Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )
        )
        system.upsert_application(
            Application(
                name="orders",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="orders",
            )
        )

        self.assertEqual(len(system.applications), 1)
        self.assertEqual(system.applications[0].name, "orders")
        self.assertEqual(system.applications[0].local_dir_name, "orders")

    def test_delete_group_keeps_applications_and_clears_their_group(self) -> None:
        system = SystemProfile(name="aha")
        system.upsert_group(Group(chinese_name="服务端", english_name="server"))
        system.upsert_application(
            Application(
                name="axo-manager",
                repository_url="git@example.com:aha/server/axo-manager.git",
                group_english_name="server",
                local_dir_name="axo-manager",
            )
        )

        system.delete_group("server")

        self.assertEqual(system.groups, [])
        self.assertEqual(len(system.applications), 1)
        self.assertEqual(system.applications[0].group_english_name, "")

    def test_application_can_have_empty_group(self) -> None:
        application = Application(
            name="axo-manager",
            repository_url="git@example.com:aha/server/axo-manager.git",
            group_english_name="",
            local_dir_name="axo-manager",
        )

        self.assertEqual(application.resolve_local_path(Path("D:/workspace")), Path("D:/workspace") / "axo-manager")

    def test_config_manages_multiple_systems(self) -> None:
        config = CodeManagerConfig()

        config.upsert_system(SystemProfile(name="aha", code_root=Path("D:/aha")))
        config.upsert_system(SystemProfile(name="ops", code_root=Path("D:/ops")))
        config.select_system("ops")

        self.assertEqual([system.name for system in config.systems], ["aha", "ops"])
        self.assertEqual(config.active_system_name, "ops")
        self.assertEqual(config.active_system().code_root, Path("D:/ops"))

    def test_config_updates_system_by_name(self) -> None:
        config = CodeManagerConfig()

        config.upsert_system(SystemProfile(name="aha", code_root=Path("D:/old")))
        config.upsert_system(SystemProfile(name="aha", code_root=Path("D:/new")))

        self.assertEqual(len(config.systems), 1)
        self.assertEqual(config.active_system().code_root, Path("D:/new"))


if __name__ == "__main__":
    unittest.main()
