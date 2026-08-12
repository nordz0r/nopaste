"""Resolve the display/app version from env or pyproject.toml."""

from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path

logger = logging.getLogger(__name__)

APP_VERSION_ENV_VAR = "APP_VERSION"


def load_version_from_pyproject(pyproject_path: Path) -> str | None:
    try:
        pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None

    version = pyproject_data.get("project", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        return None
    return version.strip()


def load_version_from_environment() -> str | None:
    version = os.getenv(APP_VERSION_ENV_VAR, "").strip()
    return version or None


def load_asset_version(candidate_paths: list[Path], *, fallback: str = "dev") -> str:
    env_version = load_version_from_environment()
    if env_version:
        return env_version

    seen_paths: set[Path] = set()
    for version_path in candidate_paths:
        if version_path in seen_paths:
            continue
        seen_paths.add(version_path)
        version = load_version_from_pyproject(version_path)
        if version:
            return version

    logger.warning(
        "Could not load app version from known paths: %s",
        ", ".join(str(path) for path in seen_paths),
    )
    return fallback
