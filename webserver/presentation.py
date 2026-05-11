from __future__ import annotations

from typing import Any

from flask import url_for

from webserver.services import source_writer

SORT_OPTIONS = [
    {"name": "name", "label": "Name"},
    {"name": "id", "label": "ID"},
    {"name": "images_desc", "label": "Most Images"},
    {"name": "files_desc", "label": "Most Files"},
]
DEFAULT_SORT = SORT_OPTIONS[0]["name"]


def select_family(config: dict[str, Any], family_slug: str | None) -> tuple[str, dict[str, Any]]:
    families = config["families"]
    selected_slug = family_slug or config["default_family"]
    family_config = families.get(selected_slug)
    if family_config is None:
        selected_slug = config["default_family"]
        family_config = families[selected_slug]
    return selected_slug, family_config


def build_form_values(family_config: dict[str, Any], submitted: dict[str, str] | None = None) -> dict[str, str]:
    values = dict(family_config.get("defaults", {}))
    for field in family_config.get("fields", []):
        values.setdefault(field["name"], field.get("default", ""))
    if submitted:
        values.update(submitted)
    return values


def build_manual_form_values(
    working_manual: dict[str, Any],
    manual_fields: list[dict[str, str]],
) -> dict[str, str]:
    return source_writer.build_multiline_field_values(
        working_manual,
        [field["name"] for field in manual_fields],
    )


def selected_search_fields(config: dict[str, Any], submitted: list[str] | None = None) -> list[str]:
    available_names = [field["name"] for field in config["search_fields"]["available"]]
    requested = submitted if submitted is not None else config["search_fields"]["default_selected"]
    normalized: list[str] = []
    for field_name in requested:
        name = str(field_name).strip()
        if name and name in available_names and name not in normalized:
            normalized.append(name)
    if normalized:
        return normalized
    return list(config["search_fields"]["default_selected"])


def selected_sort(raw_value: str | None) -> str:
    requested = str(raw_value or "").strip()
    for option in SORT_OPTIONS:
        if option["name"] == requested:
            return requested
    return DEFAULT_SORT


def positive_int_arg(raw_value: str | None) -> int | None:
    if raw_value in (None, ""):
        return None
    try:
        number = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def part_image_url(
    part_id: str,
    relative_path: str,
    preset: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> str:
    params: dict[str, Any] = {}
    if preset:
        params["preset"] = preset
    if width:
        params["w"] = width
    if height:
        params["h"] = height
    return url_for("parts.part_image", part_id=part_id, relative_path=relative_path, **params)
