from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from code_manager.domain.models import Application, CodeManagerConfig, Group, SystemProfile


class JsonConfigStore:
    def __init__(self, config_file: Path | None = None) -> None:
        self.config_file = config_file or Path.home() / ".code-manager" / "config.json"

    def load(self) -> CodeManagerConfig:
        if not self.config_file.exists():
            return CodeManagerConfig()

        data = json.loads(self.config_file.read_text(encoding="utf-8"))
        if "systems" not in data:
            return self._load_legacy_config(data)

        return CodeManagerConfig(
            systems=[
                SystemProfile(
                    name=item["name"],
                    code_root=Path(item.get("code_root", str(Path.home() / "code"))),
                    groups=self._load_groups(item.get("groups", [])),
                    applications=self._load_applications(item.get("applications", [])),
                )
                for item in data.get("systems", [])
            ],
            active_system_name=data.get("active_system_name"),
            auto_start=bool(data.get("auto_start", False)),
        )

    def save(self, config: CodeManagerConfig) -> None:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(
            json.dumps(self._to_json(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _to_json(self, config: CodeManagerConfig) -> dict[str, Any]:
        return {
            "systems": [
                {
                    "name": system.name,
                    "code_root": str(system.code_root),
                    "groups": [asdict(group) for group in system.groups],
                    "applications": [asdict(application) for application in system.applications],
                }
                for system in config.systems
            ],
            "active_system_name": config.active_system_name,
            "auto_start": config.auto_start,
        }

    def _load_legacy_config(self, data: dict[str, Any]) -> CodeManagerConfig:
        system = SystemProfile(
            name="默认系统",
            code_root=Path(data.get("code_root", str(Path.home() / "code"))),
            groups=self._load_groups(data.get("groups", [])),
            applications=self._load_applications(data.get("applications", [])),
        )
        return CodeManagerConfig(systems=[system], active_system_name=system.name)

    def _load_groups(self, items: list[dict[str, Any]]) -> list[Group]:
        return [
            Group(
                chinese_name=item["chinese_name"],
                english_name=item["english_name"],
            )
            for item in items
        ]

    def _load_applications(self, items: list[dict[str, Any]]) -> list[Application]:
        return [
            Application(
                name=item["name"],
                repository_url=item["repository_url"],
                group_english_name=item["group_english_name"],
                local_dir_name=item["local_dir_name"],
            )
            for item in items
        ]
