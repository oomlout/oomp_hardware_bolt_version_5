from __future__ import annotations

APP_TITLE = "Parts Explorer"
TAXONOMY_FIELD_COUNT = 15


def taxonomy_key(index: int) -> str:
    return f"taxonomy_{index}"
