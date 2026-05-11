from __future__ import annotations

import re
from typing import Any

from webserver.config_app import TAXONOMY_FIELD_COUNT, taxonomy_key


def slugify(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def format_value(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def build_taxonomy_payload() -> dict[str, str]:
    return {taxonomy_key(index): "" for index in range(1, TAXONOMY_FIELD_COUNT + 1)}


def build_part_id(payload: dict[str, Any]) -> str:
    parts = []
    for index in range(1, TAXONOMY_FIELD_COUNT + 1):
        value = payload.get(taxonomy_key(index), "")
        if value in (None, ""):
            continue
        slug = slugify(value)
        if slug:
            parts.append(slug)
    return "_".join(parts)
