from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

import yaml

from webserver.config_app import TAXONOMY_FIELD_COUNT, taxonomy_key
from webserver.services import file_actions, file_previews, image_derivatives

TRACKED_METADATA_FILES = {"working.yaml", "working_manual.yaml"}


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1000:
        return str(size_bytes)

    units = ("k", "M", "G", "T")
    size_value = float(size_bytes)
    for unit in units:
        size_value /= 1000.0
        if size_value < 1000 or unit == units[-1]:
            if size_value >= 100 or size_value.is_integer():
                return f"{int(size_value)}{unit}"
            return f"{size_value:.1f}{unit}"

    return str(size_bytes)


def _normalize_parts_dirs(parts_dirs: Path | str | list[Path | str] | tuple[Path | str, ...]) -> list[Path]:
    if isinstance(parts_dirs, (Path, str)):
        candidates = [parts_dirs]
    else:
        candidates = list(parts_dirs or [])

    normalized: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        path = Path(candidate).resolve(strict=False)
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(path)
    return normalized


def list_part_directories(
    parts_dirs: Path | str | list[Path | str] | tuple[Path | str, ...]
) -> dict[str, tuple[Path, Path]]:
    directories: dict[str, tuple[Path, Path]] = {}
    for parts_dir in _normalize_parts_dirs(parts_dirs):
        if not parts_dir.exists():
            continue
        for child in sorted(parts_dir.iterdir(), key=lambda item: item.name.lower()):
            if not child.is_dir() or child.name in directories:
                continue
            directories[child.name] = (child, parts_dir)
    return directories


def build_directory_signature(part_dir: Path) -> dict[str, Any]:
    return build_part_snapshot(part_dir)


def _humanize_slug(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _normalize_search_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _search_query_tokens(query: str) -> list[str]:
    normalized = _normalize_search_text(query)
    return [token for token in normalized.split(" ") if token]


def _build_taxonomy_breadcrumb(taxonomy_pairs: list[dict[str, Any]]) -> str:
    return " / ".join(pair["label"] for pair in taxonomy_pairs)


def _taxonomy_pairs(data: dict[str, Any]) -> list[dict[str, Any]]:
    pairs = []
    for index in range(1, TAXONOMY_FIELD_COUNT + 1):
        key = taxonomy_key(index)
        value = data.get(key, "")
        if value in (None, ""):
            continue
        pairs.append(
            {
                "key": key,
                "index": index,
                "value": str(value),
                "label": _humanize_slug(str(value)),
            }
        )
    return pairs


def _build_search_text(record: dict[str, Any]) -> str:
    values = [
        record.get("id", ""),
        record.get("name", ""),
        record.get("name_space", ""),
        record.get("name_proper", ""),
    ]
    values.extend(pair["value"] for pair in record["taxonomy_pairs"])
    values.extend(pair["label"] for pair in record["taxonomy_pairs"])
    for field_name, field_value in record.get("data", {}).items():
        if field_name.startswith("taxonomy_"):
            continue
        if isinstance(field_value, list):
            values.extend(str(item) for item in field_value if item not in (None, ""))
        elif field_value not in (None, ""):
            values.append(str(field_value))
    return " ".join(str(value) for value in values if value).lower()


def _search_field_text(field_name: str, record: dict[str, Any]) -> str:
    values: list[str] = []
    if field_name == "id":
        values.append(record.get("id", ""))
    elif field_name == "name":
        values.extend(
            [
                record.get("name", ""),
                record.get("name_space", ""),
            ]
        )
    elif field_name == "name_proper":
        values.append(record.get("name_proper", ""))
    elif field_name == "taxonomy":
        combined_taxonomy = record.get("data", {}).get("taxonomy", "")
        if isinstance(combined_taxonomy, list):
            values.extend(str(item) for item in combined_taxonomy if item not in (None, ""))
        elif combined_taxonomy not in (None, ""):
            values.append(str(combined_taxonomy))
        values.extend(pair["value"] for pair in record.get("taxonomy_pairs", []))
        values.extend(pair["label"] for pair in record.get("taxonomy_pairs", []))
        values.append(record.get("taxonomy_breadcrumb", ""))
    elif field_name == "working_manual":
        for manual_value in record.get("working_manual", {}).values():
            if isinstance(manual_value, list):
                values.extend(str(item) for item in manual_value if item not in (None, ""))
            elif manual_value not in (None, ""):
                values.append(str(manual_value))
    else:
        combined_value = record.get("data", {}).get(field_name, "")
        if isinstance(combined_value, list):
            values.extend(str(item) for item in combined_value if item not in (None, ""))
        elif combined_value not in (None, ""):
            values.append(str(combined_value))

    return " ".join(str(value) for value in values if value).lower()


def _build_search_index(record: dict[str, Any], search_field_names: list[str]) -> dict[str, str]:
    return {
        field_name: _search_field_text(field_name, record)
        for field_name in search_field_names
    }


def _list_part_files(part_dir: Path) -> list[dict[str, Any]]:
    files = []
    for file_path in sorted(part_dir.rglob("*")):
        if not file_path.is_file():
            continue
        relative_path = file_path.relative_to(part_dir).as_posix()
        is_image = _is_image_file(relative_path)
        width = None
        height = None
        if is_image:
            width, height = image_derivatives.read_image_dimensions(file_path)
        text_preview = file_previews.build_hover_preview(file_path)
        files.append(
            {
                "name": file_path.name,
                "relative_path": relative_path,
                "suffix": file_path.suffix.lower(),
                "size": file_path.stat().st_size,
                "size_label": format_file_size(file_path.stat().st_size),
                "is_image": is_image,
                "is_text_previewable": bool(text_preview),
                "text_language": text_preview["language"] if text_preview else "",
                "text_language_label": text_preview["language_label"] if text_preview else "",
                "text_hover_preview": text_preview["hover_text"] if text_preview else "",
                "text_hover_truncated": bool(text_preview and text_preview["hover_truncated"]),
                "width": width,
                "height": height,
            }
        )
    return files


def build_part_snapshot(part_dir: Path) -> dict[str, Any]:
    file_count = 0
    image_relative_paths: list[str] = []
    tracked_signatures: dict[str, tuple[int, int]] = {}

    for file_path in sorted(part_dir.rglob("*")):
        if not file_path.is_file():
            continue
        relative_path = file_path.relative_to(part_dir).as_posix()
        file_count += 1
        if _is_image_file(relative_path):
            image_relative_paths.append(relative_path)
        if relative_path in TRACKED_METADATA_FILES:
            stat = file_path.stat()
            tracked_signatures[relative_path] = (int(stat.st_mtime_ns), int(stat.st_size))

    return {
        "file_count": file_count,
        "image_relative_paths": tuple(image_relative_paths),
        "tracked_signatures": tracked_signatures,
    }


def _is_image_file(relative_path: str) -> bool:
    suffix = Path(relative_path).suffix.lower()
    return suffix in {".png", ".svg", ".jpg", ".jpeg", ".webp", ".gif"}


def _pick_preview_file(
    files: list[dict[str, Any]],
    preview_priority: list[str] | None,
) -> str | None:
    if not files:
        return None

    image_files = [file for file in files if file["is_image"]]
    if not image_files:
        return None

    patterns = [pattern.strip() for pattern in (preview_priority or []) if str(pattern).strip()]
    for pattern in patterns:
        wildcard = any(char in pattern for char in "*?[]")
        for file in image_files:
            candidates = [file["relative_path"], file["name"]]
            if wildcard:
                if any(fnmatch.fnmatch(candidate.lower(), pattern.lower()) for candidate in candidates):
                    return file["relative_path"]
            else:
                if any(candidate.lower() == pattern.lower() for candidate in candidates):
                    return file["relative_path"]

    return image_files[0]["relative_path"]


def _is_previewable_file(file: dict[str, Any]) -> bool:
    return bool(file.get("is_image") or file.get("is_text_previewable"))


def _build_preview_items(
    files: list[dict[str, Any]],
    preview_file: str | None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    preview_candidates = [file for file in files if _is_previewable_file(file)]
    if not preview_candidates:
        return [], {}

    ordered_candidates = list(preview_candidates)
    if preview_file:
        preview_match = next(
            (file for file in preview_candidates if file["relative_path"] == preview_file),
            None,
        )
        if preview_match is not None:
            ordered_candidates = [preview_match]
            ordered_candidates.extend(
                file
                for file in preview_candidates
                if file["relative_path"] != preview_file
            )

    items = []
    index_by_relative_path: dict[str, int] = {}
    for index, file in enumerate(ordered_candidates):
        item = {
            "kind": "image" if file["is_image"] else "text",
            "name": file["name"],
            "relative_path": file["relative_path"],
        }
        if file["is_image"]:
            item["width"] = file.get("width")
            item["height"] = file.get("height")
        else:
            item["language"] = file.get("text_language", "plaintext")
            item["language_label"] = file.get("text_language_label", "Text")
        items.append(item)
        index_by_relative_path[file["relative_path"]] = index
    return items, index_by_relative_path


def load_part_record(
    part_dir: Path,
    parts_dir: Path,
    preview_priority: list[str] | None = None,
    search_field_names: list[str] | None = None,
) -> dict[str, Any] | None:
    part_dir = Path(part_dir).resolve(strict=False)
    parts_dir = Path(parts_dir).resolve(strict=False)
    working_yaml = Path(part_dir) / "working.yaml"
    if not working_yaml.exists():
        return None
    with working_yaml.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        return None

    working_manual_path = Path(part_dir) / "working_manual.yaml"
    working_manual: dict[str, Any] = {}
    working_manual_error: str | None = None
    if working_manual_path.exists():
        try:
            with working_manual_path.open("r", encoding="utf-8") as handle:
                loaded_manual = yaml.safe_load(handle) or {}
        except Exception as exc:
            working_manual_error = str(exc)
        else:
            if isinstance(loaded_manual, dict):
                working_manual = loaded_manual
            else:
                working_manual_error = "working_manual.yaml must contain a YAML mapping."

    combined_data = dict(data)
    combined_data.update(working_manual)

    part_id = part_dir.name
    taxonomy_pairs = _taxonomy_pairs(combined_data)
    snapshot = build_part_snapshot(part_dir)
    image_relative_paths = list(snapshot["image_relative_paths"])
    preview_file = _pick_preview_file(
        [{"relative_path": relative_path, "name": Path(relative_path).name, "is_image": True} for relative_path in image_relative_paths],
        preview_priority,
    )
    image_index_by_relative_path = {
        relative_path: index
        for index, relative_path in enumerate(image_relative_paths)
    }
    source_label = parts_dir.parent.name or parts_dir.name
    record = {
        "id": part_id,
        "name": combined_data.get("name_proper") or combined_data.get("name") or _humanize_slug(part_id),
        "name_space": combined_data.get("name_space") or part_id.replace("_", " "),
        "name_proper": combined_data.get("name_proper") or _humanize_slug(part_id),
        "directory": combined_data.get("directory") or part_dir.relative_to(parts_dir.parent).as_posix(),
        "source_base_dir": str(parts_dir.parent),
        "source_parts_dir": str(parts_dir),
        "source_label": source_label,
        "part_dir": str(part_dir),
        "relative_dir": part_dir.relative_to(parts_dir).as_posix(),
        "data": combined_data,
        "taxonomy_pairs": taxonomy_pairs,
        "taxonomy_values": {pair["key"]: pair["value"] for pair in taxonomy_pairs},
        "taxonomy_breadcrumb": _build_taxonomy_breadcrumb(taxonomy_pairs),
        "preview_file": preview_file,
        "preview_file_index": 0 if preview_file else 0,
        "image_relative_paths": image_relative_paths,
        "image_index_by_relative_path": image_index_by_relative_path,
        "file_count": snapshot["file_count"],
        "image_count": len(image_relative_paths),
        "working_yaml": data,
        "working_manual": working_manual,
        "working_manual_exists": working_manual_path.exists(),
        "working_manual_error": working_manual_error,
        "reload_signature": snapshot,
    }
    record["search_index_by_field"] = _build_search_index(record, list(search_field_names or ["id"]))
    record["search_text"] = _build_search_text(record)
    return record


def populate_part_assets(
    record: dict[str, Any],
    preview_priority: list[str] | None = None,
) -> dict[str, Any]:
    part = dict(record)
    part_dir = Path(part["part_dir"]).resolve(strict=False)
    files = []
    for file in _list_part_files(part_dir):
        file_record = dict(file)
        source_path = part_dir / str(file_record["relative_path"])
        file_record["actions"] = file_actions.describe_file_actions(source_path, part_dir)
        files.append(file_record)
    image_files = [file for file in files if file["is_image"]]
    image_index_by_relative_path = {
        file["relative_path"]: index
        for index, file in enumerate(image_files)
    }
    preview_file = _pick_preview_file(files, preview_priority)
    preview_items, preview_index_by_relative_path = _build_preview_items(files, preview_file)
    part.update(
        {
            "files": files,
            "image_files": image_files,
            "image_relative_paths": [file["relative_path"] for file in image_files],
            "image_index_by_relative_path": image_index_by_relative_path,
            "preview_items": preview_items,
            "preview_index_by_relative_path": preview_index_by_relative_path,
            "preview_file": preview_file,
            "preview_file_index": preview_index_by_relative_path.get(preview_file or "", 0),
            "file_count": len(files),
            "image_count": len(image_files),
        }
    )
    return part


def scan_parts(
    parts_dirs: Path | str | list[Path | str] | tuple[Path | str, ...],
    preview_priority: list[str] | None = None,
    search_field_names: list[str] | None = None,
    progress_interval: int | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, tuple[int, int, int]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    signatures: dict[str, tuple[int, int, int]] = {}
    errors: list[str] = []
    loaded_count = 0
    for part_id, (part_dir, source_parts_dir) in list_part_directories(parts_dirs).items():
        try:
            record = load_part_record(
                part_dir,
                source_parts_dir,
                preview_priority,
                search_field_names,
            )
        except Exception as exc:
            errors.append(f"{part_id}: {exc}")
            continue
        if record is None:
            continue
        records[part_id] = record
        signatures[part_id] = record["reload_signature"]
        loaded_count += 1
        if progress_interval and loaded_count % progress_interval == 0:
            print(".", end="", flush=True)
    return records, signatures, errors


def filter_parts(
    parts: list[dict[str, Any]],
    taxonomy_filters: dict[str, str],
    query: str = "",
    selected_search_fields: list[str] | None = None,
    sort_name: str = "name",
) -> list[dict[str, Any]]:
    query_tokens = _search_query_tokens(query)
    active_fields = list(selected_search_fields or [])
    filtered = []
    for part in parts:
        include = True
        for key, value in taxonomy_filters.items():
            if not value:
                continue
            if part["taxonomy_values"].get(key) != value:
                include = False
                break
        if not include:
            continue
        if query_tokens:
            if active_fields:
                haystack = " ".join(
                    part.get("search_index_by_field", {}).get(field_name, "")
                    for field_name in active_fields
                )
            else:
                haystack = part.get("search_text", "")
            normalized_haystack = _normalize_search_text(haystack)
            if not all(token in normalized_haystack for token in query_tokens):
                continue
        filtered.append(part)
    return sort_parts(filtered, sort_name)


def sort_parts(parts: list[dict[str, Any]], sort_name: str = "name") -> list[dict[str, Any]]:
    if sort_name == "id":
        return sorted(parts, key=lambda item: str(item["id"]).lower())
    if sort_name == "images_desc":
        return sorted(parts, key=lambda item: (-int(item.get("image_count", 0)), str(item["name"]).lower()))
    if sort_name == "files_desc":
        return sorted(parts, key=lambda item: (-int(item.get("file_count", 0)), str(item["name"]).lower()))
    return sorted(parts, key=lambda item: str(item["name"]).lower())


def build_taxonomy_navigation(
    parts: list[dict[str, Any]],
    active_filters: dict[str, str],
) -> dict[str, Any]:
    selected_pairs = []
    for index in range(1, TAXONOMY_FIELD_COUNT + 1):
        key = taxonomy_key(index)
        value = active_filters.get(key, "")
        if not value:
            break
        selected_pairs.append(
            {"key": key, "index": index, "value": value, "label": _humanize_slug(value)}
        )

    parent_filters = {pair["key"]: pair["value"] for pair in selected_pairs}
    next_index = len(selected_pairs) + 1
    options = []
    if next_index <= TAXONOMY_FIELD_COUNT:
        counts: dict[str, int] = {}
        for part in parts:
            matches_parent = True
            for key, value in parent_filters.items():
                if part["taxonomy_values"].get(key) != value:
                    matches_parent = False
                    break
            if not matches_parent:
                continue
            next_value = part["taxonomy_values"].get(taxonomy_key(next_index), "")
            if not next_value:
                continue
            counts[next_value] = counts.get(next_value, 0) + 1
        options = [
            {
                "key": taxonomy_key(next_index),
                "value": value,
                "label": _humanize_slug(value),
                "count": count,
            }
            for value, count in sorted(counts.items(), key=lambda item: (item[0].lower(), item[1]))
        ]

    return {
        "selected": selected_pairs,
        "next_key": taxonomy_key(next_index) if next_index <= TAXONOMY_FIELD_COUNT else None,
        "next_index": next_index if next_index <= TAXONOMY_FIELD_COUNT else None,
        "options": options,
    }
