from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from code_manager.domain.models import Application, Group, SystemProfile
from code_manager.domain.repo_parser import parse_repository_url
from code_manager.infrastructure.config_store import JsonConfigStore
from code_manager.infrastructure.system_yaml import dump_system_to_yaml, load_system_from_yaml


@dataclass(frozen=True)
class ImportResult:
    imported_count: int
    skipped_count: int
    errors: list[str]


class CodeManagerService:
    def __init__(self, config_store: JsonConfigStore | None = None) -> None:
        self.config_store = config_store or JsonConfigStore()
        self.config = self.config_store.load()

    def active_system(self) -> SystemProfile:
        return self.config.active_system()

    def upsert_system(self, system: SystemProfile) -> None:
        self.config.upsert_system(system)
        self.save()

    def export_system_to_yaml(self, system_name: str, yaml_file: Path) -> None:
        system = self.config.get_system(system_name)
        yaml_file.write_text(dump_system_to_yaml(system), encoding="utf-8")

    def import_system_from_yaml(self, yaml_file: Path) -> SystemProfile:
        system = load_system_from_yaml(yaml_file.read_text(encoding="utf-8"))
        self.upsert_system(system)
        return system

    def delete_system(self, name: str) -> None:
        self.config.delete_system(name)
        self.save()

    def select_system(self, name: str) -> None:
        self.config.select_system(name)
        self.save()

    def set_code_root(self, code_root: Path) -> None:
        self.active_system().code_root = code_root
        self.save()

    def save(self) -> None:
        self.config_store.save(self.config)

    def upsert_group(self, group: Group) -> None:
        self.config.upsert_group(group)
        self.save()

    def delete_group(self, english_name: str) -> None:
        self.config.delete_group(english_name)
        self.save()

    def upsert_application(self, application: Application) -> None:
        self.config.upsert_application(application)
        self.save()

    def delete_application(self, repository_url: str) -> None:
        self.config.delete_application(repository_url)
        self.save()

    def import_repositories(self, repository_text: str) -> ImportResult:
        imported_count = 0
        skipped_count = 0
        errors: list[str] = []
        system = self.active_system()
        existing_urls = {application.repository_url for application in system.applications}

        for index, repository_url in enumerate(_split_repository_urls(repository_text), start=1):
            if repository_url in existing_urls:
                skipped_count += 1
                continue

            try:
                parsed = parse_repository_url(repository_url)
                system.upsert_group(
                    Group(
                        chinese_name=parsed.group_english_name,
                        english_name=parsed.group_english_name,
                    )
                )
                system.upsert_application(
                    Application(
                        name=parsed.app_name,
                        repository_url=repository_url,
                        group_english_name=parsed.group_english_name,
                        local_dir_name=parsed.local_dir_name,
                    )
                )
                existing_urls.add(repository_url)
                imported_count += 1
            except ValueError as exc:
                errors.append(f"第 {index} 个仓库: {exc}")

        self.save()
        return ImportResult(
            imported_count=imported_count,
            skipped_count=skipped_count,
            errors=errors,
        )


def _split_repository_urls(repository_text: str) -> list[str]:
    return [value.strip() for value in repository_text.split() if value.strip()]
