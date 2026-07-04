import tempfile
import unittest
from pathlib import Path

from code_manager.domain.models import Application, CodeManagerConfig, Group, SystemProfile
from code_manager.infrastructure.config_store import JsonConfigStore


class JsonConfigStoreTests(unittest.TestCase):
    def test_load_returns_default_config_when_file_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonConfigStore(Path(temp_dir) / "config.json")

            config = store.load()

            self.assertEqual(config.code_root, Path.home() / "code")
            self.assertEqual(config.systems, [])

    def test_save_and_load_round_trips_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonConfigStore(Path(temp_dir) / "nested" / "config.json")
            expected = CodeManagerConfig(
                systems=[
                    SystemProfile(
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
                ],
                active_system_name="aha",
            )

            store.save(expected)
            actual = store.load()

            self.assertEqual(actual, expected)

    def test_load_migrates_legacy_single_system_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            config_file.write_text(
                """
                {
                  "code_root": "D:/workspace",
                  "groups": [{"chinese_name": "平台", "english_name": "platform"}],
                  "applications": [{
                    "name": "order-service",
                    "repository_url": "https://git.example.com/platform/order-service.git",
                    "group_english_name": "platform",
                    "local_dir_name": "order-service"
                  }]
                }
                """,
                encoding="utf-8",
            )
            store = JsonConfigStore(config_file)

            config = store.load()

            self.assertEqual(len(config.systems), 1)
            self.assertEqual(config.active_system_name, "默认系统")
            self.assertEqual(config.active_system().code_root, Path("D:/workspace"))
            self.assertEqual(config.active_system().groups[0].english_name, "platform")


if __name__ == "__main__":
    unittest.main()
