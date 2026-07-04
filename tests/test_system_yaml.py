import tempfile
import unittest
from pathlib import Path

from code_manager.domain.models import Application, Group, SystemProfile
from code_manager.infrastructure.system_yaml import dump_system_to_yaml, load_system_from_yaml


class SystemYamlTests(unittest.TestCase):
    def test_dump_and_load_system_yaml_with_groups_and_applications(self) -> None:
        system = SystemProfile(
            name="axo",
            code_root=Path("D:/workspace-axo"),
            groups=[
                Group(chinese_name="服务端", english_name="server"),
                Group(chinese_name="前端", english_name="endpoint"),
            ],
            applications=[
                Application(
                    name="axo-manager",
                    repository_url="git@example.com:aha/server/axo-manager.git",
                    group_english_name="server",
                    local_dir_name="axo-manager",
                ),
                Application(
                    name="axo-app-fe",
                    repository_url="git@example.com:aha/endpoint/axo-app-fe.git",
                    group_english_name="endpoint",
                    local_dir_name="axo-app-fe",
                ),
            ],
        )

        yaml_text = dump_system_to_yaml(system)
        imported = load_system_from_yaml(yaml_text)

        self.assertIn('name: "axo"', yaml_text)
        self.assertNotIn("code_root", yaml_text)
        self.assertNotIn("D:/workspace-axo", yaml_text)
        self.assertIn('chinese_name: "服务端"', yaml_text)
        self.assertEqual(imported.name, "axo")
        self.assertEqual(imported.code_root, Path.home() / "code")
        self.assertEqual(imported.groups, system.groups)
        self.assertEqual(imported.applications, system.applications)

    def test_load_system_yaml_rejects_missing_system_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "系统名称不能为空"):
            load_system_from_yaml(
                """
system:
groups: []
applications: []
"""
            )

    def test_dumped_yaml_can_be_written_as_utf8_file(self) -> None:
        system = SystemProfile(name="测试系统", code_root=Path("D:/workspace"))

        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_file = Path(temp_dir) / "system.yaml"
            yaml_file.write_text(dump_system_to_yaml(system), encoding="utf-8")

            self.assertEqual(load_system_from_yaml(yaml_file.read_text(encoding="utf-8")).name, "测试系统")


if __name__ == "__main__":
    unittest.main()
