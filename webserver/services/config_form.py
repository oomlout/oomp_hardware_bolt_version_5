from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from webserver.config_app import TAXONOMY_FIELD_COUNT, taxonomy_key


def _build_generic_fields() -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for index in range(1, TAXONOMY_FIELD_COUNT + 1):
        fields.append(
            {
                "name": taxonomy_key(index),
                "label": f"Taxonomy {index}",
                "input_type": "text",
                "required": index == 1,
                "default": "",
                "placeholder": f"taxonomy level {index}",
                "help_text": "Leave blank if not needed." if index > 1 else "Top-level taxonomy value.",
            }
        )
    return fields


DEFAULT_FORM_CONFIG: dict[str, Any] = {
    "default_family": "generic",
    "families": {
        "generic": {
            "label": "Generic taxonomy entry",
            "description": "Direct control over taxonomy_1 to taxonomy_15.",
            "defaults": {},
            "fields": _build_generic_fields(),
        }
    },
}


def _normalize_field(field: dict[str, Any]) -> dict[str, Any] | None:
    name = str(field.get("name", "")).strip()
    if not name:
        return None

    return {
        "name": name,
        "label": str(field.get("label", name.replace("_", " ").title())),
        "input_type": "number" if field.get("input_type") == "number" else "text",
        "required": bool(field.get("required", False)),
        "default": field.get("default", "" if field.get("input_type") != "number" else None),
        "placeholder": str(field.get("placeholder", "")),
        "help_text": str(field.get("help_text", "")),
    }


def _normalize_family(slug: str, family: dict[str, Any]) -> dict[str, Any] | None:
    defaults = family.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}

    raw_fields = family.get("fields", [])
    normalized_fields = []
    if isinstance(raw_fields, list):
        for field in raw_fields:
            if not isinstance(field, dict):
                continue
            normalized_field = _normalize_field(field)
            if normalized_field:
                normalized_fields.append(normalized_field)

    if not normalized_fields:
        return None

    return {
        "label": str(family.get("label", slug.replace("_", " ").title())),
        "description": str(family.get("description", "")),
        "defaults": {str(key): value for key, value in defaults.items()},
        "fields": normalized_fields,
    }


def _load_single_form_config(path: Path) -> dict[str, Any]:
    config = deepcopy(DEFAULT_FORM_CONFIG)
    if not path.exists():
        return config

    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        return config

    raw_families = loaded.get("families")
    if isinstance(raw_families, dict):
        normalized_families: dict[str, Any] = {}
        for slug, family in raw_families.items():
            if not isinstance(family, dict):
                continue
            normalized_family = _normalize_family(str(slug), family)
            if normalized_family:
                normalized_families[str(slug)] = normalized_family
        if normalized_families:
            config["families"] = normalized_families

    default_family = str(loaded.get("default_family", config["default_family"])).strip()
    if default_family in config["families"]:
        config["default_family"] = default_family
    else:
        config["default_family"] = next(iter(config["families"]))

    return config


def load_form_config(base_path: Path | str, override_path: Path | str | None = None) -> dict[str, Any]:
    base = Path(base_path)
    override = Path(override_path) if override_path is not None else None

    if override is not None and override.exists():
        return _load_single_form_config(override)
    return _load_single_form_config(base)
