from __future__ import annotations

import hashlib
import logging
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

DERIVATIVE_VERSION = "1"
SVG_NAMESPACE_SUFFIX = "svg"
RASTER_SOURCE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
IMAGE_SOURCE_SUFFIXES = RASTER_SOURCE_SUFFIXES | {".gif", ".svg"}
DEFAULT_PROJECT_CACHE_DIRNAME = "project_base"
DEFAULT_IMAGE_CACHE_DIRNAME = "webserver_image_cache"
DEFAULT_FIT = "contain"
DEFAULT_QUALITY = 82
DEFAULT_MAX_REQUEST_DIMENSION = 4096

logger = logging.getLogger(__name__)


def is_image_path(path: Path | str) -> bool:
    return Path(path).suffix.lower() in IMAGE_SOURCE_SUFFIXES


def is_resizable_raster_path(path: Path | str) -> bool:
    return Path(path).suffix.lower() in RASTER_SOURCE_SUFFIXES


def read_image_dimensions(path: Path | str) -> tuple[int | None, int | None]:
    image_path = Path(path)
    suffix = image_path.suffix.lower()
    if suffix in RASTER_SOURCE_SUFFIXES:
        try:
            with Image.open(image_path) as image:
                return int(image.width), int(image.height)
        except Exception:
            return None, None
    if suffix == ".svg":
        return _read_svg_dimensions(image_path)
    return None, None


def resolve_image_cache_dir(image_serving_config: dict[str, Any]) -> Path:
    configured = str(image_serving_config.get("cache_dir", "auto")).strip()
    if configured and configured.lower() != "auto":
        configured_path = Path(configured)
        if configured_path.is_absolute():
            return configured_path.resolve(strict=False)

    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data).resolve(strict=False) / DEFAULT_PROJECT_CACHE_DIRNAME / DEFAULT_IMAGE_CACHE_DIRNAME

    return Path(tempfile.gettempdir()).resolve(strict=False) / DEFAULT_PROJECT_CACHE_DIRNAME / DEFAULT_IMAGE_CACHE_DIRNAME


def resolve_preset(image_serving_config: dict[str, Any], preset_name: str | None) -> dict[str, Any]:
    presets = image_serving_config.get("presets", {})
    if not preset_name:
        return {}
    if not isinstance(presets, dict):
        return {}
    preset = presets.get(str(preset_name).strip())
    if not isinstance(preset, dict):
        return {}
    return dict(preset)


def build_derivative_settings(
    image_serving_config: dict[str, Any],
    preset_name: str | None = None,
    width: int | None = None,
    height: int | None = None,
    fit: str | None = None,
    quality: int | None = None,
) -> dict[str, Any]:
    preset = resolve_preset(image_serving_config, preset_name)
    max_dimension = _normalize_dimension_limit(
        image_serving_config.get("max_request_dimension", DEFAULT_MAX_REQUEST_DIMENSION)
    )
    resolved_width = _coerce_optional_int(width if width is not None else preset.get("width"))
    resolved_height = _coerce_optional_int(height if height is not None else preset.get("height"))
    if resolved_width:
        resolved_width = min(resolved_width, max_dimension)
    if resolved_height:
        resolved_height = min(resolved_height, max_dimension)
    resolved_fit = _normalize_fit(fit if fit is not None else preset.get("fit", DEFAULT_FIT))
    resolved_quality = _normalize_quality(
        quality if quality is not None else preset.get("quality", image_serving_config.get("quality_webp", DEFAULT_QUALITY))
    )
    return {
        "width": resolved_width,
        "height": resolved_height,
        "fit": resolved_fit,
        "quality": resolved_quality,
        "preset_name": str(preset_name).strip() if preset_name else "",
    }


def get_served_image_path(
    source_path: Path | str,
    image_serving_config: dict[str, Any],
    preset_name: str | None = None,
    width: int | None = None,
    height: int | None = None,
    fit: str | None = None,
    quality: int | None = None,
) -> Path:
    original_path = Path(source_path).resolve(strict=False)
    if not image_serving_config.get("enabled", True):
        return original_path
    if not is_resizable_raster_path(original_path):
        return original_path

    settings = build_derivative_settings(
        image_serving_config,
        preset_name=preset_name,
        width=width,
        height=height,
        fit=fit,
        quality=quality,
    )
    if settings["width"] is None and settings["height"] is None:
        return original_path

    if _derivative_would_not_help(original_path, settings):
        return original_path

    derivative_path = _build_derivative_path(original_path, image_serving_config, settings)
    if derivative_path.exists():
        logger.debug("Image derivative cache hit: %s", derivative_path)
        return derivative_path

    derivative_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Generating image derivative: %s", derivative_path)
    try:
        _write_derivative(original_path, derivative_path, image_serving_config, settings)
    except Exception as exc:
        logger.warning("Image derivative generation failed for %s: %s", original_path, exc)
        return original_path
    return derivative_path


def _build_derivative_path(
    source_path: Path,
    image_serving_config: dict[str, Any],
    settings: dict[str, Any],
) -> Path:
    cache_root = resolve_image_cache_dir(image_serving_config)
    stat = source_path.stat()
    source_key = hashlib.sha256(str(source_path).lower().encode("utf-8")).hexdigest()
    format_name = _pick_output_format(source_path)
    width = settings.get("width") or 0
    height = settings.get("height") or 0
    fit = settings.get("fit", DEFAULT_FIT)
    quality = settings.get("quality", DEFAULT_QUALITY)
    file_name = f"w{width}-h{height}-{fit}-q{quality}.{format_name}"
    return (
        cache_root
        / source_key[:2]
        / source_key[2:4]
        / source_key
        / f"{stat.st_mtime_ns}-{stat.st_size}-{DERIVATIVE_VERSION}"
        / file_name
    )


def _write_derivative(
    source_path: Path,
    derivative_path: Path,
    image_serving_config: dict[str, Any],
    settings: dict[str, Any],
) -> None:
    max_source_pixels = int(image_serving_config.get("max_source_pixels", 40_000_000))
    width = settings["width"]
    height = settings["height"]
    fit = settings["fit"]
    quality = settings["quality"]
    output_format = derivative_path.suffix.lstrip(".").upper()

    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image)
        source_pixels = int(image.width) * int(image.height)
        if source_pixels > max_source_pixels:
            ratio = (max_source_pixels / float(source_pixels)) ** 0.5
            reduced_size = (
                max(1, int(image.width * ratio)),
                max(1, int(image.height * ratio)),
            )
            image = image.resize(reduced_size, Image.Resampling.LANCZOS)

        target_size = _resolve_target_size(image.size, width, height)
        if fit == "cover" and width and height:
            image = ImageOps.fit(image, target_size, Image.Resampling.LANCZOS)
        elif target_size != image.size:
            image = ImageOps.contain(image, target_size, Image.Resampling.LANCZOS)

        save_kwargs: dict[str, Any] = {}
        if output_format == "PNG":
            image = image.convert("RGBA") if _has_alpha(image) else image.convert("RGB")
            save_kwargs["optimize"] = True
        elif output_format == "WEBP":
            image = image.convert("RGBA") if _has_alpha(image) else image.convert("RGB")
            save_kwargs["quality"] = quality
            save_kwargs["method"] = 6
        else:
            image = image.convert("RGB")
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True

        image.save(derivative_path, format=output_format, **save_kwargs)


def _derivative_would_not_help(source_path: Path, settings: dict[str, Any]) -> bool:
    source_width, source_height = read_image_dimensions(source_path)
    if not source_width or not source_height:
        return False
    requested_width = settings.get("width")
    requested_height = settings.get("height")
    fit = settings.get("fit", DEFAULT_FIT)
    if fit == "cover" and requested_width and requested_height:
        return False
    if requested_width and requested_height:
        return requested_width >= source_width and requested_height >= source_height
    if requested_width:
        return requested_width >= source_width
    if requested_height:
        return requested_height >= source_height
    return False


def _pick_output_format(source_path: Path) -> str:
    suffix = source_path.suffix.lower()
    if suffix == ".png":
        width, height = read_image_dimensions(source_path)
        if width is None or height is None:
            return "png"
    try:
        with Image.open(source_path) as image:
            if _has_alpha(image):
                return "png"
    except Exception:
        return "png"
    return "webp"


def _has_alpha(image: Image.Image) -> bool:
    if image.mode in {"RGBA", "LA"}:
        return True
    return "transparency" in image.info


def _resolve_target_size(
    source_size: tuple[int, int],
    width: int | None,
    height: int | None,
) -> tuple[int, int]:
    source_width, source_height = source_size
    if width and height:
        return int(width), int(height)
    if width:
        scale = width / float(source_width)
        return int(width), max(1, int(round(source_height * scale)))
    if height:
        scale = height / float(source_height)
        return max(1, int(round(source_width * scale))), int(height)
    return source_size


def _read_svg_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None, None

    width = _parse_svg_length(root.attrib.get("width"))
    height = _parse_svg_length(root.attrib.get("height"))
    if width and height:
        return width, height

    view_box = root.attrib.get("viewBox", "")
    parts = [part for part in re.split(r"[\s,]+", str(view_box).strip()) if part]
    if len(parts) == 4:
        try:
            return max(1, int(float(parts[2]))), max(1, int(float(parts[3])))
        except ValueError:
            return None, None
    return None, None


def _parse_svg_length(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)", text)
    if not match:
        return None
    try:
        return max(1, int(float(match.group(1))))
    except ValueError:
        return None


def _coerce_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def _normalize_fit(value: Any) -> str:
    text = str(value or DEFAULT_FIT).strip().lower()
    if text in {"contain", "cover"}:
        return text
    return DEFAULT_FIT


def _normalize_quality(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULT_QUALITY
    return max(30, min(95, number))


def _normalize_dimension_limit(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_REQUEST_DIMENSION
    return max(256, min(8192, number))
