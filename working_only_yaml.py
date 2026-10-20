"""Publish a small, portable OOMP catalogue using only pathlib and Pillow.

Copy this file to another OOMP project's root and call main() after generation,
or run it with --project PATH. No screw/bolt-specific code or paths are needed.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
import textwrap

from PIL import Image, ImageDraw, ImageOps


IMAGE_CANDIDATES = (
    "three_d_model/render_product_low.png",
    "three_d_model/render_low.png",
    "3dpr.png",
    "image.png",
    "image.jpg",
    "image.webp",
    "three_d_model/render_product_high.png",
    "three_d_model/render_high.png",
    "initial_generated_icon.png",
    "data/working_svg_square_pins_300.png",
    "data/working_svg_top_300.png",
    "data/generated_data/src/board_pins_300.png",
    "images/pcb_3d_populated.png",
    "data/working_svg_square_pins.png",
    "data/working_svg_top.png",
    "data/working_svg_contact_sheet.png",
)
OUTPUT_FILES = {"working.yaml", "image.png"}


def _is_link(path: Path) -> bool:
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def _check_output(parts: Path) -> None:
    """Only manage our two-file-per-part tree; never follow output links."""
    if _is_link(parts):
        raise ValueError(f"Export parts directory must not be a link: {parts}")
    if not parts.exists():
        return
    if not parts.is_dir():
        raise ValueError(f"Export parts path is not a directory: {parts}")
    for directory in parts.iterdir():
        if _is_link(directory) or not directory.is_dir():
            raise ValueError(f"Unexpected entry in export parts: {directory}")
        for path in directory.iterdir():
            if path.is_symlink() or not path.is_file() or path.name not in OUTPUT_FILES:
                raise ValueError(f"Unexpected file in export; refusing to replace it: {path}")


def _thumbnail(part: Path, destination: Path, size: int, candidates: tuple[str, ...], missing_image: str) -> bool:
    errors = []
    for name in candidates:
        source = part / name
        if not source.is_file():
            continue
        try:
            with Image.open(source) as original:
                image = ImageOps.exif_transpose(original).convert("RGBA")
                image.thumbnail((size, size), Image.Resampling.LANCZOS)
                # A white background is useful in catalogue browsers and printouts.
                background = Image.new("RGBA", image.size, "white")
                background.alpha_composite(image)
                background.convert("RGB").save(destination, "PNG", optimize=True)
            return True
        except (OSError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
    if missing_image == "placeholder":
        # Explicitly show the absence of a preview; never invent component geometry.
        image = Image.new("RGB", (256, 256), "#f4f4f4")
        draw = ImageDraw.Draw(image)
        draw.text((16, 16), "Preview unavailable", fill="#333333")
        label = "\n".join(textwrap.wrap(part.name.replace("_", " "), width=32))
        draw.multiline_text((16, 48), label, fill="#555555", spacing=4)
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        image.save(destination, "PNG", optimize=True)
        return False
    detail = "; ".join(errors) or "none of the configured image files exist"
    raise ValueError(f"No usable preview for {part.name}: {detail}")


def export_catalogue(
    project: str | Path | None = None,
    output: str | Path | None = None,
    size: int = 256,
    image_candidates: tuple[str, ...] | None = None,
    missing_image: str | None = None,
) -> dict:
    """Export every generated part, preserving YAML bytes and removing retired parts.

    Build all thumbnails before touching an existing export. Root files (such as
    a publishing repository's .git or README) are preserved; parts/ is managed.
    """
    project = Path(project or Path(__file__).parent).resolve()
    config_path = project / "config_only_yaml.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    if not isinstance(config, dict):
        raise ValueError("config_only_yaml.json must contain an object")
    image_candidates = image_candidates if image_candidates is not None else config.get("image_candidates", IMAGE_CANDIDATES)
    if not isinstance(image_candidates, (tuple, list)) or not all(isinstance(name, str) for name in image_candidates):
        raise ValueError("image_candidates must be a list of relative image paths")
    missing_image = missing_image if missing_image is not None else config.get("missing_image", "error")
    if missing_image not in {"error", "placeholder"}:
        raise ValueError("missing_image must be 'error' or 'placeholder'")
    output = Path(output).resolve() if output else project.with_name(project.name + "_only_yaml")
    if output == project or output.is_relative_to(project) or project.is_relative_to(output):
        raise ValueError("Export and source project directories must not overlap")
    if not isinstance(size, int) or size < 1:
        raise ValueError("Thumbnail size must be a positive integer")
    for name in image_candidates:
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("Image candidates must be paths within each part directory")
    yamls = sorted((project / "parts").glob("*/working.yaml"))
    if not yamls:
        raise ValueError(f"No generated parts found in {project / 'parts'}")
    target = output / "parts"
    _check_output(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    placeholders = 0
    # Stage outside the publish folder, so it contains only the small catalogue.
    with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as temporary:
        staging = Path(temporary)
        for yaml in yamls:
            part = staging / yaml.parent.name
            part.mkdir()
            shutil.copyfile(yaml, part / "working.yaml")
            if not _thumbnail(yaml.parent, part / "image.png", size, image_candidates, missing_image):
                placeholders += 1

        _check_output(target)
        target.mkdir(parents=True, exist_ok=True)
        current_ids = {yaml.parent.name for yaml in yamls}
        for part in staging.iterdir():
            destination = target / part.name
            destination.mkdir(exist_ok=True)
            for source in part.iterdir():
                final = destination / source.name
                # Keep unchanged files' timestamps stable on repeated builds.
                if not final.exists() or final.read_bytes() != source.read_bytes():
                    os.replace(source, final)
        for retired in target.iterdir():
            if retired.name not in current_ids:
                # Entries were validated above; only delete the two managed files.
                for path in retired.iterdir():
                    path.unlink()
                retired.rmdir()
    total_bytes = sum(path.stat().st_size for path in target.glob("*/*"))
    result = {"output": str(output), "parts": len(yamls), "bytes": total_bytes, "placeholders": placeholders}
    print(f"YAML-only export: {len(yamls)} parts, {total_bytes / 1024 / 1024:.2f} MiB -> {output}")
    if placeholders:
        print(f"  {placeholders} parts have labelled 'Preview unavailable' thumbnails.")
    return result


def main(**kwargs):
    # Ignore upstream part filters: this is always a complete catalogue snapshot.
    return export_catalogue(
        project=kwargs.get("only_yaml_project"),
        output=kwargs.get("only_yaml_output"),
        size=kwargs.get("only_yaml_image_size", 256),
        missing_image=kwargs.get("only_yaml_missing_image"),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, help="Default: sibling <project>_only_yaml folder")
    parser.add_argument("--size", type=int, default=256, help="Maximum image width/height (default: 256)")
    parser.add_argument("--image", action="append", help="Preferred relative image path; repeat for fallbacks")
    parser.add_argument("--missing-image", choices=("error", "placeholder"), help="Override the project's missing-preview policy (default: error)")
    args = parser.parse_args()
    export_catalogue(args.project, args.output, args.size, tuple(args.image) if args.image else None, args.missing_image)
