from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_PART_SOURCE_CONFIG = {
    "directories": ["parts"],
}


def _normalize_directory_entries(raw_directories: Any) -> list[str]:
    if isinstance(raw_directories, str):
        candidates = [raw_directories]
    elif isinstance(raw_directories, list):
        candidates = raw_directories
    else:
        candidates = DEFAULT_PART_SOURCE_CONFIG["directories"]

    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        value = str(candidate).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)

    if normalized:
        return normalized
    return list(DEFAULT_PART_SOURCE_CONFIG["directories"])


def _resolve_parts_directory(path: Path) -> Path:
    # Treat explicit parts paths as-is; otherwise point at the child parts folder.
    if path.name.lower() == "parts":
        return path
    return path / "parts"


def _resolve_directories(directories: list[str], base_dir: Path) -> list[Path]:
    resolved: list[Path] = []
    seen: set[str] = set()
    for directory in directories:
        path = Path(directory)
        if not path.is_absolute():
            path = base_dir / path
        normalized = _resolve_parts_directory(path).resolve(strict=False)
        key = str(normalized).lower()
        if key in seen:
            continue
        seen.add(key)
        resolved.append(normalized)
    return resolved


def load_part_source_config(
    config_path: Path | str,
    base_dir: Path | str | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    root_dir = Path(base_dir) if base_dir is not None else path.parent
    config = {
        "directories": list(DEFAULT_PART_SOURCE_CONFIG["directories"]),
    }

    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if isinstance(loaded, dict):
            config["directories"] = _normalize_directory_entries(
                loaded.get("directories", config["directories"])
            )

    config["resolved_directories"] = _resolve_directories(
        config["directories"],
        root_dir.resolve(strict=False),
    )
    return config
