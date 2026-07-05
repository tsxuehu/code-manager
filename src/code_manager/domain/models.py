from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Group:
    chinese_name: str
    english_name: str

    def __post_init__(self) -> None:
        if not self.english_name.strip():
            raise ValueError("Group english name cannot be empty.")
        if not self.chinese_name.strip():
            raise ValueError("Group chinese name cannot be empty.")


@dataclass(frozen=True)
class Application:
    name: str
    repository_url: str
    group_english_name: str
    local_dir_name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Application name cannot be empty.")
        if not self.repository_url.strip():
            raise ValueError("Repository URL cannot be empty.")
        if not self.local_dir_name.strip():
            raise ValueError("Application local directory name cannot be empty.")

    def resolve_local_path(self, code_root: Path) -> Path:
        return Path(code_root).expanduser() / self.group_english_name / self.local_dir_name


@dataclass
class SystemProfile:
    name: str
    code_root: Path = field(default_factory=lambda: Path.home() / "code")
    groups: list[Group] = field(default_factory=list)
    applications: list[Application] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("System name cannot be empty.")

    def upsert_group(self, group: Group) -> None:
        self.groups = [
            current
            for current in self.groups
            if current.english_name.lower() != group.english_name.lower()
        ]
        self.groups.append(group)

    def delete_group(self, english_name: str) -> None:
        normalized = english_name.lower()
        self.groups = [
            current for current in self.groups if current.english_name.lower() != normalized
        ]
        self.applications = [
            Application(
                name=current.name,
                repository_url=current.repository_url,
                group_english_name="",
                local_dir_name=current.local_dir_name,
            )
            if current.group_english_name.lower() == normalized
            else current
            for current in self.applications
        ]

    def upsert_application(self, application: Application) -> None:
        self.applications = [
            current
            for current in self.applications
            if current.repository_url != application.repository_url
        ]
        self.applications.append(application)

    def delete_application(self, repository_url: str) -> None:
        self.applications = [
            current
            for current in self.applications
            if current.repository_url != repository_url
        ]


@dataclass
class CodeManagerConfig:
    systems: list[SystemProfile] = field(default_factory=list)
    active_system_name: str | None = None
    auto_start: bool = False

    @property
    def code_root(self) -> Path:
        return self.active_system().code_root if self.systems else Path.home() / "code"

    def upsert_system(self, system: SystemProfile) -> None:
        self.systems = [
            current
            for current in self.systems
            if current.name.lower() != system.name.lower()
        ]
        self.systems.append(system)
        self.active_system_name = system.name

    def delete_system(self, name: str) -> None:
        normalized = name.lower()
        self.systems = [current for current in self.systems if current.name.lower() != normalized]
        if self.active_system_name and self.active_system_name.lower() == normalized:
            self.active_system_name = self.systems[0].name if self.systems else None

    def select_system(self, name: str) -> None:
        self.active_system_name = self.get_system(name).name

    def get_system(self, name: str) -> SystemProfile:
        normalized = name.lower()
        for system in self.systems:
            if system.name.lower() == normalized:
                return system
        raise ValueError(f"System does not exist: {name}")

    def active_system(self) -> SystemProfile:
        if not self.systems:
            raise ValueError("No system selected.")
        if self.active_system_name:
            try:
                return self.get_system(self.active_system_name)
            except ValueError:
                pass
        self.active_system_name = self.systems[0].name
        return self.systems[0]

    def upsert_group(self, group: Group) -> None:
        self.active_system().upsert_group(group)

    def delete_group(self, english_name: str) -> None:
        self.active_system().delete_group(english_name)

    def upsert_application(self, application: Application) -> None:
        self.active_system().upsert_application(application)

    def delete_application(self, repository_url: str) -> None:
        self.active_system().delete_application(repository_url)
