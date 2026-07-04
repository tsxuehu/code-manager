from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse


@dataclass(frozen=True)
class ParsedRepository:
    group_english_name: str
    local_dir_name: str
    app_name: str


def parse_repository_url(repository_url: str) -> ParsedRepository:
    url = repository_url.strip()
    if not url:
        raise ValueError("Repository URL cannot be empty.")

    path = _extract_repository_path(url)
    parts = [part for part in PurePosixPath(path).parts if part not in ("/", "")]
    if len(parts) < 2:
        raise ValueError(f"Repository URL must include group and repository name: {repository_url}")

    group_name = parts[-2]
    repo_name = _strip_git_suffix(parts[-1])
    if not group_name or not repo_name:
        raise ValueError(f"Repository URL must include group and repository name: {repository_url}")

    return ParsedRepository(
        group_english_name=group_name,
        local_dir_name=repo_name,
        app_name=repo_name,
    )


def _extract_repository_path(repository_url: str) -> str:
    if "://" in repository_url:
        parsed = urlparse(repository_url)
        return parsed.path

    if "@" in repository_url and ":" in repository_url:
        return repository_url.split(":", 1)[1]

    return repository_url


def _strip_git_suffix(repo_name: str) -> str:
    if repo_name.endswith(".git"):
        return repo_name[:-4]
    return repo_name
