from __future__ import annotations

from pathlib import Path


TEXT_PREVIEW_CONFIG = {
    ".af": {"language": "plaintext", "label": "AF"},
    ".bat": {"language": "batch", "label": "Batch"},
    ".c": {"language": "c", "label": "C"},
    ".cfg": {"language": "ini", "label": "Config"},
    ".cpp": {"language": "cpp", "label": "C++"},
    ".css": {"language": "css", "label": "CSS"},
    ".csv": {"language": "plaintext", "label": "CSV"},
    ".html": {"language": "html", "label": "HTML"},
    ".ini": {"language": "ini", "label": "INI"},
    ".js": {"language": "javascript", "label": "JavaScript"},
    ".json": {"language": "json", "label": "JSON"},
    ".log": {"language": "plaintext", "label": "Log"},
    ".md": {"language": "markdown", "label": "Markdown"},
    ".py": {"language": "python", "label": "Python"},
    ".scad": {"language": "openscad", "label": "OpenSCAD"},
    ".sh": {"language": "shell", "label": "Shell"},
    ".sql": {"language": "sql", "label": "SQL"},
    ".toml": {"language": "toml", "label": "TOML"},
    ".txt": {"language": "plaintext", "label": "Text"},
    ".xml": {"language": "xml", "label": "XML"},
    ".yaml": {"language": "yaml", "label": "YAML"},
    ".yml": {"language": "yaml", "label": "YAML"},
}

MAX_PREVIEW_FILE_SIZE = 256_000
HOVER_PREVIEW_CHAR_LIMIT = 420
HOVER_PREVIEW_LINE_LIMIT = 12
MODAL_PREVIEW_CHAR_LIMIT = 64_000


def is_text_previewable(file_path: Path | str) -> bool:
    suffix = Path(file_path).suffix.lower()
    return suffix in TEXT_PREVIEW_CONFIG


def describe_text_preview(file_path: Path | str) -> dict[str, str | bool] | None:
    path = Path(file_path)
    preview_config = TEXT_PREVIEW_CONFIG.get(path.suffix.lower())
    if preview_config is None:
        return None

    if path.exists() and path.stat().st_size > MAX_PREVIEW_FILE_SIZE:
        return None

    return {
        "language": preview_config["language"],
        "language_label": preview_config["label"],
        "is_text_previewable": True,
    }


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _trim_text(value: str, char_limit: int, line_limit: int | None = None) -> tuple[str, bool]:
    lines = value.splitlines()
    truncated = False
    if line_limit is not None and len(lines) > line_limit:
        lines = lines[:line_limit]
        truncated = True

    text = "\n".join(lines)
    if len(text) > char_limit:
        text = text[:char_limit].rstrip()
        truncated = True

    if truncated:
        return f"{text}\n...", True
    return text, False


def build_hover_preview(file_path: Path | str) -> dict[str, str | bool] | None:
    path = Path(file_path)
    preview = describe_text_preview(path)
    if preview is None or not path.exists():
        return None

    text = _read_text_file(path)
    snippet, truncated = _trim_text(
        text,
        char_limit=HOVER_PREVIEW_CHAR_LIMIT,
        line_limit=HOVER_PREVIEW_LINE_LIMIT,
    )
    preview.update(
        {
            "hover_text": snippet,
            "hover_truncated": truncated,
        }
    )
    return preview


def build_modal_preview(file_path: Path | str, relative_path: str) -> dict[str, str | bool]:
    path = Path(file_path)
    preview = describe_text_preview(path)
    if preview is None:
        raise ValueError(f"File is not text-previewable: {relative_path}")

    text = _read_text_file(path)
    content, truncated = _trim_text(text, char_limit=MODAL_PREVIEW_CHAR_LIMIT)
    preview.update(
        {
            "relative_path": relative_path,
            "content": content,
            "truncated": truncated,
        }
    )
    return preview