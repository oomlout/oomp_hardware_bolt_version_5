"""Shared drawer-label layout/data and a label-only regeneration entry point.

The same file and Jinja template live in the bolt and screw repositories.
SVG coordinates are millimetres; no image or CAD automation is required.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from jinja2 import Environment, StrictUndefined
from PIL import ImageFont
import yaml

ROOT = Path(__file__).resolve().parent
TEMPLATE = Path("source_file/template_jinja/label_drawer/working.svg.j2")
START = "# BEGIN GENERATED LABEL_DRAWER\n"
END = "# END GENERATED LABEL_DRAWER\n"
LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


@lru_cache(maxsize=2)
def font(bold=True):
    filename = "arialbd.ttf" if bold else "arial.ttf"
    candidates = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / filename,
                  Path("/usr/share/fonts/truetype/msttcorefonts") / filename,
                  Path("/usr/share/fonts/truetype/liberation2") /
                  ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf")]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), 1000)
    raise RuntimeError("Install Arial or Liberation Sans to measure drawer-label text.")


def width(text, size, bold=True):
    return font(bold).getlength(text) / 1000 * size


def fit_size(text, maximum, available):
    return round(min(maximum, maximum * available / max(width(text, maximum), .01)), 3)


def wrap(text, size, available, bold=True):
    lines = []
    for word in text.split():
        if lines and width(lines[-1] + " " + word, size, bold) <= available:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def readable(value):
    text = str(value or "").replace("_", " ")
    text = re.sub(r"(?<=\d) (?=\d)", ".", text)
    return text


def diagram(kind, style=""):
    """Symbolic side profiles; nuts and washers use front views."""
    if kind == "washer":
        return '<circle cx="10" cy="7" r="5.5"/><circle cx="10" cy="7" r="2.5"/>'
    if kind == "nut":
        if style == "coupling":
            return '<path d="M2 3H18V11H2Z M2 5H18 M2 9H18"/>'
        return '<path d="M7 1.8H13L16 7L13 12.2H7L4 7Z"/><circle cx="10" cy="7" r="2.5"/>'
    pointed = style in {"wood", "self_tapping", "thread_forming"}
    if kind in {"bolt", "set_screw"}:
        head = '<path d="M2 3H5L6 4V10L5 11H2Z M4 3V11"/>'
        start = 11 if kind == "bolt" else 7
    elif style == "grub":
        head = '<path d="M2 5V9 M2 7H4"/>'
        start = 3
    elif style in {"countersunk", "flat_head"}:
        head = '<path d="M2 2.5L6 5V9L2 11.5Z M2 6H3.5V8H2"/>'
        start = 7
    elif style == "button_head":
        head = '<path d="M6 3Q2 3 2 7Q2 11 6 11Z M2 6H3.5V8H2"/>'
        start = 7
    else:
        left = {"socket_cap_low_head": 3.5, "socket_cap_low_head_ultra": 4.5}.get(style, 2)
        head = f'<path d="M{left} 3H6V11H{left}Z M{left} 6H{left + .8}V8H{left}"/>'
        start = 7
    shank_start = 2 if style == "grub" else 6
    if pointed:
        shank = f'<path d="M{shank_start} 5H15L19 7L15 9H{shank_start}"/>'
        end = 15
    else:
        shank = f'<path d="M{shank_start} 5H18V9H{shank_start}"/>'
        end = 18
    threads = " ".join(f"M{x} 5L{x-1} 9" for x in range(start, end, 2))
    return head + shank + f'<path d="{threads}"/>'


def layout(part):
    """Normalize both taxonomies without confusing a drive or material with size."""
    values = [str(part.get(f"taxonomy_{i}") or "") for i in range(1, 16)]
    kind = values[1]
    codes = {"bolt": "BO", "set_screw": "SS", "screw": "SC", "nut": "NU", "washer": "WA"}
    if kind not in codes:
        raise ValueError(f"Unsupported drawer-label hardware type: {kind!r}")
    thread = next((v for v in values if re.fullmatch(r"m\d+(?:_\d+)?(?:_diameter)?", v)), "")
    if not thread:
        raise ValueError(f"Missing thread/diameter: {values}")
    thread = thread.removesuffix("_diameter").replace("_", ".").upper()
    length_token = next((v for v in values if re.fullmatch(r"\d+(?:_\d+)?_mm_length", v)), "")
    length = length_token.removesuffix("_mm_length").replace("_", ".")
    if kind in {"bolt", "set_screw", "screw"} and not length:
        raise ValueError(f"Missing fastener length: {values}")

    names = {"socket_cap": "Socket cap screw", "socket_cap_low_head": "Low head socket cap screw",
             "socket_cap_low_head_ultra": "Ultra low head socket cap screw",
             "button_head": "Button head screw", "flat_head": "Flat head screw",
             "countersunk": "Countersunk screw", "grub": "Grub screw",
             "machine_screw": "Machine screw", "self_tapping": "Self-tapping screw",
             "thread_forming": "Thread-forming screw", "wood": "Wood screw"}
    details = []
    if kind == "screw":
        name = names.get(values[2], readable(values[2]).capitalize() + " screw")
        drive = {"hex_head": "Hex socket", "philips": "Phillips", "pozidriv": "Pozidriv"}.get(values[3], readable(values[3]))
        if drive:
            details.append(drive)
        if values[4]:
            details.append(readable(values[4]).capitalize())
    else:
        name = {"bolt": "Bolt", "set_screw": "Set screw", "nut": "Nut", "washer": "Washer"}[kind]
        extras = [v for v in values[3:] if v and v != length_token]
        if kind in {"nut", "washer"} and extras:
            variant = extras.pop(0)
            if "nylon_white_" in variant:
                name = "Nylon washer"
                variant = variant.replace("nylon_white_", "White_").replace("_outer_diameter", " OD").replace("_depth", " thick")
                details.append(readable(variant))
            else:
                name = readable(variant).capitalize() + " " + name.lower()
        if kind == "bolt":
            details.append("Hex head / Partial thread")
        elif kind == "set_screw":
            details.append("Hex head / Full thread")
        details.extend(readable(v).capitalize() for v in extras)

    available = 22.5
    name_size = 3.2
    name_lines = wrap(name, name_size, available)
    while (len(name_lines) > 2 or any(width(line, name_size) > available for line in name_lines)) and name_size > 2.6:
        name_size = round(name_size - .1, 2)
        name_lines = wrap(name, name_size, available)
    detail_text = " / ".join(details)
    detail_size = 2.05
    # Keep finish/drive phrases intact when possible (e.g. "Nylon white").
    detail_lines = []
    for detail in details:
        if detail_lines and width(detail_lines[-1] + " / " + detail, detail_size, False) <= available:
            detail_lines[-1] += " / " + detail
        else:
            detail_lines.extend(wrap(detail, detail_size, available, False))
    while len(detail_lines) > 3 and detail_size > 1.9:
        detail_size = round(detail_size - .05, 2)
        detail_lines = wrap(detail_text, detail_size, available, False)
    if len(name_lines) > 2 or len(detail_lines) > 3:
        raise ValueError(f"Label text needs a layout adjustment: {name!r}, {detail_text!r}")
    length_size = fit_size(length, 7.8, available - width("mm", 2.8) - .8)
    length_width = width(length, length_size) + .8 + width("mm", 2.8)
    return dict(code=codes[kind], thread=thread, length=length, name=name,
                diagram=diagram(kind, values[2] if kind == "screw" else values[3]),
                description=" / ".join([name, thread, length + " mm" if length else "", detail_text]).strip(" /"),
                name_lines=name_lines, name_size=name_size,
                detail_lines=detail_lines, detail_size=detail_size,
                detail_y=24.1 - max(0, len(detail_lines) - 1) * 2.2,
                thread_size=fit_size(thread, 6.5, 9.8),
                length_size=length_size, length_x=25.25 - length_width / 2)


def add_action(part, count=0, root=ROOT):
    """Attach a native roboclick text_jinja_template block; no GUI action needed."""
    part["label_drawer"] = layout(part)
    # Repeated calls update the existing action rather than adding duplicates.
    key = next((k for k, v in part.items() if k.startswith("oomlout_ai_roboclick_")
                and isinstance(v, dict) and any(a.get("file_output") == "label_drawer.svg"
                for a in v.get("actions", []))), None)
    if key is None:
        index = 1
        while f"oomlout_ai_roboclick_{index}" in part:
            index += 1
        key = f"oomlout_ai_roboclick_{index}"
    part[key] = {"actions": [{"command": "text_jinja_template", "description": "label_drawer",
                             "file_template": str((Path(root) / TEMPLATE).resolve()),
                             "file_output": "label_drawer.svg",
                             "dict_data": {"label_drawer": part["label_drawer"]},
                             "convert_to_pdf": False, "convert_to_png": False}],
                 "file_test": ""}
    return count + 1


def render(part, root=ROOT):
    template = Environment(undefined=StrictUndefined, autoescape=False).from_string(
        (Path(root) / TEMPLATE).read_text(encoding="utf-8"))
    svg = template.render(p={"label_drawer": layout(part)})
    ET.fromstring(svg)  # Fail before touching existing output if rendering is invalid.
    return svg


def clean_pngs(directory, parts_root):
    """Remove label PNG renders only, with resolved-path and symlink protection."""
    parts_root = parts_root.resolve()
    directory = directory.resolve()
    if directory == parts_root or not directory.is_relative_to(parts_root):
        raise ValueError(f"Refusing PNG cleanup outside a part directory: {directory}")
    deleted = 0
    for candidate in directory.rglob("*.png"):
        if candidate.name.lower().startswith("label") and not candidate.is_symlink():
            if not candidate.resolve().is_relative_to(directory):
                raise ValueError(f"PNG path escapes part directory: {candidate}")
            candidate.unlink()
            deleted += 1
    return deleted


def regenerate(root=ROOT):
    root = Path(root).resolve()
    parts_root = root / "parts"
    sources = {p.parent.name: p for p in parts_root.glob("*/working.yaml")}
    sources.update({p.parent.name: p for p in (root / "parts_source").glob("*/working.yaml")})
    if not sources:
        raise ValueError(f"No parts found in {root}")
    generated = deleted = 0
    for name, source in sorted(sources.items()):
        directory = parts_root / name
        if not directory.resolve().is_relative_to(parts_root.resolve()):
            raise ValueError(f"Part directory escapes parts root: {directory}")
        part = yaml.load(source.read_text(encoding="utf-8"), Loader=LOADER)
        output = render(part, root)
        metadata_path = directory / "working.yaml"
        original = metadata_path.read_text(encoding="utf-8") if metadata_path.exists() else yaml.safe_dump(part, sort_keys=False)
        # Preserve all pre-existing metadata and actions verbatim outside our block.
        base = re.sub(re.escape(START) + r".*?" + re.escape(END), "", original, flags=re.S)
        metadata = yaml.load(base, Loader=LOADER) or {}
        for key, value in part.items():
            if key.startswith("taxonomy_"):
                metadata[key] = value
        before = set(metadata)
        add_action(metadata, root=root)
        drawer_keys = [k for k in metadata if k not in before or k == "label_drawer"]
        # Normally the action is new; a pipeline-generated drawer action is updated in place.
        existing_action = next((k for k in before if k.startswith("oomlout_ai_roboclick_")
                                and any(a.get("file_output") == "label_drawer.svg"
                                        for a in metadata[k].get("actions", []))), None)
        if existing_action or "label_drawer" in (yaml.load(base, Loader=LOADER) or {}):
            saved = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
        else:
            block = {k: metadata[k] for k in drawer_keys}
            saved = base.rstrip() + "\n" + START + yaml.safe_dump(block, allow_unicode=True, sort_keys=False) + END
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "label_drawer.svg").write_text(output, encoding="utf-8")
        metadata_path.write_text(saved, encoding="utf-8")
        deleted += clean_pngs(directory, parts_root)
        generated += 1
    print(f"{root.name}: wrote {generated} label_drawer.svg labels (38.1 x 25.4 mm); deleted {deleted} label PNG renders.")
    return generated, deleted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    regenerate(args.root)
