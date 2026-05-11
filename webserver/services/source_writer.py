from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ValidationError(ValueError):
    pass


def _parse_number(value: str) -> int | float:
    numeric = float(value)
    if numeric.is_integer():
        return int(numeric)
    return numeric


def _parse_value(raw_value: str, input_type: str) -> Any:
    value = raw_value.strip()
    if value == "":
        return ""
    if input_type == "number":
        return _parse_number(value)
    return value


def build_form_response(form_data: dict[str, str], family_config: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = dict(family_config.get("defaults", {}))

    for field in family_config.get("fields", []):
        field_name = field["name"]
        raw_value = form_data.get(field_name, "")
        parsed_value = _parse_value(raw_value, field.get("input_type", "text"))

        if field.get("required") and parsed_value in ("", None):
            raise ValidationError(f"{field['label']} is required.")

        values[field_name] = parsed_value

    return values


def _normalize_manual_option(entry: Any) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None

    values = entry.get("values")
    if isinstance(values, dict):
        entry = values

    normalized = dict(entry)
    if "type_name" not in normalized and "item_type" in normalized:
        normalized["type_name"] = normalized.pop("item_type")
    return normalized


def _load_manual_document(manual_path: Path) -> dict[str, Any]:
    if not manual_path.exists():
        return {"options": []}

    with manual_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if isinstance(loaded, list):
        return {
            "options": [
                option
                for option in (_normalize_manual_option(entry) for entry in loaded)
                if option is not None
            ]
        }
    if isinstance(loaded, dict):
        options = loaded.get("options")
        if isinstance(options, list):
            normalized_options = [
                option
                for option in (_normalize_manual_option(entry) for entry in options)
                if option is not None
            ]
            entries = loaded.get("entries")
            if isinstance(entries, list):
                normalized_options.extend(
                    option
                    for option in (_normalize_manual_option(entry) for entry in entries)
                    if option is not None
                )
                loaded = {
                    key: value
                    for key, value in loaded.items()
                    if key != "entries"
                }
            loaded["options"] = normalized_options
            return loaded

        entries = loaded.get("entries")
        if isinstance(entries, list):
            migrated = {
                key: value
                for key, value in loaded.items()
                if key != "entries"
            }
            migrated["options"] = [
                option
                for option in (_normalize_manual_option(entry) for entry in entries)
                if option is not None
            ]
            return migrated

        loaded["options"] = []
        return loaded

    raise ValidationError(f"{manual_path} is not a valid manual entry file.")


def _canonical_manual_document(document: dict[str, Any]) -> dict[str, Any]:
    options = document.get("options", [])
    if not isinstance(options, list):
        options = []
    return {"options": options}


def load_yaml_mapping(document_path: Path) -> dict[str, Any]:
    path = Path(document_path)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        raise ValidationError(f"{path} must contain a YAML mapping.")

    return dict(loaded)


def build_multiline_field_values(
    document: dict[str, Any],
    field_names: list[str],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for field_name in field_names:
        raw_value = document.get(field_name, "")
        lines: list[str] = []
        if isinstance(raw_value, list):
            lines = [str(item).strip() for item in raw_value if str(item).strip()]
        elif raw_value not in (None, ""):
            text = str(raw_value).strip()
            if text:
                lines = [text]
        values[field_name] = "\n".join(lines)
    return values


def write_part_manual_fields(
    document_path: Path,
    form_data: dict[str, str],
    field_names: list[str],
) -> dict[str, Any]:
    path = Path(document_path)
    document = load_yaml_mapping(path)
    saved_values: dict[str, list[str]] = {}

    for field_name in field_names:
        raw_value = form_data.get(field_name, "")
        lines = [line.strip() for line in raw_value.splitlines() if line.strip()]
        saved_values[field_name] = lines
        if lines:
            document[field_name] = lines
        else:
            document.pop(field_name, None)

    file_exists = bool(document)
    if file_exists:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(document, handle, allow_unicode=False, sort_keys=False)
    elif path.exists():
        path.unlink()

    return {
        "target_file": path,
        "document": document,
        "saved_values": saved_values,
        "file_exists": file_exists,
    }


def write_manual_entry(
    manual_path: Path,
    form_data: dict[str, str],
    family_config: dict[str, Any],
) -> dict[str, Any]:
    values = build_form_response(form_data, family_config)
    document = _canonical_manual_document(_load_manual_document(Path(manual_path)))
    options = document.setdefault("options", [])
    options.append(values)

    manual_path = Path(manual_path)
    manual_path.parent.mkdir(parents=True, exist_ok=True)
    with manual_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(document, handle, allow_unicode=False, sort_keys=False)

    return {
        "target_file": manual_path,
        "entry": values,
        "entry_count": len(options),
    }
