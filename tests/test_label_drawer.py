"""Regressions for drawer-label typography, taxonomy and overwrite safety."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("drawer_under_test", ROOT / "working_label_drawer.py")
drawer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drawer)


def bolt():
    return dict(taxonomy_1="hardware", taxonomy_2="bolt", taxonomy_3="m2_5", taxonomy_4="100_mm_length")


def test_real_catalogue_fits_and_is_monochrome():
    for source in (ROOT / "parts_source").glob("*/working.yaml"):
        part = yaml.load(source.read_text(encoding="utf-8"), Loader=drawer.LOADER)
        d = drawer.layout(part)
        assert drawer.width(d["thread"], d["thread_size"]) <= 9.81
        assert drawer.width(d["length"], d["length_size"]) + .8 + drawer.width("mm", 2.8) <= 22.51
        for line in d["name_lines"]:
            assert drawer.width(line, d["name_size"]) <= 22.51, source
        for line in d["detail_lines"]:
            assert drawer.width(line, d["detail_size"], False) <= 22.51, source
        svg = ET.fromstring(drawer.render(part))
        assert (svg.get("width"), svg.get("height"), svg.get("viewBox")) == ("38.1mm", "25.4mm", "0 0 38.1 25.4")
        for node in svg.iter():
            assert not node.tag.endswith("image")
            for attribute in ("fill", "stroke"):
                if attribute in node.attrib:
                    assert node.get(attribute) in {"#000000", "#ffffff", "none"}
        texts = [node.text for node in svg.iter() if node.tag.endswith("text")]
        assert not {"TYPE", "THREAD", "LENGTH mm", "BO", "SS", "SC", "WA", "NU"}.intersection(texts)
        assert svg.find(".//*[@id='hardware-diagram']") is not None
        thread = svg.find(".//*[@id='thread']")
        assert (thread.get("x"), thread.get("y"), thread.get("fill")) == ("6.7", "19.5", "#ffffff")
        assert float(svg.find(".//*[@id='name-1']").get("y")) < 5
        if d["length"]:
            length = svg.find(".//*[@id='length']")
            assert "".join(length.itertext()) == d["length"] + "mm"
            assert float(length.get("x")) >= 14


def test_decimal_threads_and_nonstandard_length_location():
    part = bolt()
    assert drawer.layout(part)["thread"] == "M2.5"
    part.update(taxonomy_2="set_screw", taxonomy_4="", taxonomy_5="nylon_white", taxonomy_7="15_mm_length")
    d = drawer.layout(part)
    assert (d["code"], d["length"]) == ("SS", "15")
    assert "Nylon white" in d["detail_lines"]


def test_diagrams_distinguish_threading_and_head_styles():
    assert drawer.diagram("bolt") != drawer.diagram("set_screw")
    styles = ["socket_cap", "socket_cap_low_head", "socket_cap_low_head_ultra",
              "button_head", "countersunk", "grub"]
    assert len({drawer.diagram("screw", style) for style in styles}) == len(styles)


def test_roboclick_action_updates_without_duplicates():
    part = bolt()
    part["oomlout_ai_roboclick_1"] = {"actions": [{"command": "existing_action"}]}
    drawer.add_action(part)
    drawer.add_action(part)
    assert "oomlout_ai_roboclick_3" not in part
    block = part["oomlout_ai_roboclick_2"]
    assert block["file_test"] == ""
    action = block["actions"][0]
    assert action["command"] == "text_jinja_template"
    assert action["file_output"] == "label_drawer.svg"
    assert not action["convert_to_png"]
    # Render exactly the payload handed to roboclick.
    template = drawer.Environment(undefined=drawer.StrictUndefined).from_string(Path(action["file_template"]).read_text(encoding="utf-8"))
    ET.fromstring(template.render(p=action["dict_data"]))


def test_overwrite_and_cleanup_preserve_unrelated_files(tmp_path):
    template = tmp_path / drawer.TEMPLATE
    template.parent.mkdir(parents=True)
    template.write_bytes((ROOT / drawer.TEMPLATE).read_bytes())
    source = tmp_path / "parts_source" / "example" / "working.yaml"
    source.parent.mkdir(parents=True)
    source.write_text(yaml.safe_dump(bolt()), encoding="utf-8")
    part_dir = tmp_path / "parts" / "example"
    part_dir.mkdir(parents=True)
    original = "# User metadata\ncustom: untouched\noomlout_ai_roboclick_1:\n  actions:\n  - command: existing_action\n"
    (part_dir / "working.yaml").write_text(original, encoding="utf-8")
    for filename in ["label_drawer.png", "label_bolt_image.png", "initial_generated_icon.png", "working.png"]:
        (part_dir / filename).write_bytes(b"test")
    (part_dir / "label_drawer.svg").write_text("old label", encoding="utf-8")
    assert drawer.regenerate(tmp_path) == (1, 2)
    first = (part_dir / "working.yaml").read_bytes()
    assert (part_dir / "working.yaml").read_text(encoding="utf-8").startswith(original)
    assert (part_dir / "initial_generated_icon.png").exists()
    assert (part_dir / "working.png").exists()
    assert drawer.regenerate(tmp_path) == (1, 0)
    assert (part_dir / "working.yaml").read_bytes() == first
    saved = yaml.safe_load(first)
    assert saved["label_drawer"]["thread"] == "M2.5"
    assert saved["oomlout_ai_roboclick_2"]["actions"][0]["file_output"] == "label_drawer.svg"
    with pytest.raises(ValueError):
        drawer.clean_pngs(tmp_path, tmp_path / "parts")


def test_missing_length_fails_before_replacing_a_label():
    part = bolt()
    part["taxonomy_4"] = ""
    with pytest.raises(ValueError, match="Missing fastener length"):
        drawer.render(part)
