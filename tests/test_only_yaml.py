"""Portable export contract and full-build integration, without CAD rebuilds."""

import importlib
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from working_only_yaml import export_catalogue


def make_part(project, name="example", image="three_d_model/render_product_low.png"):
    part = project / "parts" / name
    part.mkdir(parents=True)
    (part / "working.yaml").write_bytes(b"id: example\r\nname: 'Original YAML'\r\n")
    if image:
        path = part / image
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (600, 300), "red").save(path)
    (part / "large.stl").write_text("excluded")
    return part


def test_portable_export_exact_metadata_and_small_image(tmp_path, monkeypatch):
    project = tmp_path / "oomp_other_project"
    source = make_part(project)
    Image.new("RGB", (512, 512), "blue").save(source / "3dpr.png")
    monkeypatch.chdir(tmp_path)
    result = export_catalogue(project)
    output = tmp_path / "oomp_other_project_only_yaml"
    assert result["parts"] == 1
    assert Path(result["output"]) == output
    part = output / "parts" / "example"
    assert {p.name for p in part.iterdir()} == {"working.yaml", "image.png"}
    assert (part / "working.yaml").read_bytes() == (source / "working.yaml").read_bytes()
    with Image.open(part / "image.png") as image:
        assert image.size == (256, 128)
        assert image.getpixel((0, 0)) == (255, 0, 0)


def test_refresh_removes_retired_parts_and_preserves_repository_files(tmp_path):
    project = tmp_path / "project"
    source = make_part(project)
    output = tmp_path / "publish"
    export_catalogue(project, output)
    image = output / "parts" / "example" / "image.png"
    unchanged_mtime = image.stat().st_mtime_ns
    export_catalogue(project, output)
    assert image.stat().st_mtime_ns == unchanged_mtime
    (output / ".git").mkdir()
    (output / ".git" / "config").write_text("keep")
    (output / "README.md").write_text("keep")
    (source / "working.yaml").unlink()
    make_part(project, "replacement")
    export_catalogue(project, output)
    assert {p.name for p in (output / "parts").iterdir()} == {"replacement"}
    assert (output / ".git" / "config").read_text() == "keep"
    assert (output / "README.md").read_text() == "keep"


def test_missing_image_does_not_change_previous_export(tmp_path):
    project = tmp_path / "project"
    source = make_part(project)
    output = Path(export_catalogue(project)["output"])
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    (source / "working.yaml").write_text("id: changed")
    make_part(project, "missing", image=None)
    with pytest.raises(ValueError, match="No usable preview for missing"):
        export_catalogue(project)
    after = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert before == after


def test_corrupt_preferred_image_falls_back(tmp_path):
    project = tmp_path / "project"
    source = make_part(project, image="3dpr.png")
    (source / "three_d_model").mkdir()
    (source / "three_d_model" / "render_product_low.png").write_bytes(b"broken")
    assert export_catalogue(project)["parts"] == 1


@pytest.mark.parametrize("destination", [".", "parts", ".."])
def test_reject_overlapping_destination(tmp_path, destination):
    project = tmp_path / "project"
    make_part(project)
    with pytest.raises(ValueError, match="must not overlap"):
        export_catalogue(project, project / destination)


def test_reject_empty_source_and_unmanaged_output(tmp_path):
    project = tmp_path / "project"
    with pytest.raises(ValueError, match="No generated parts"):
        export_catalogue(project)
    make_part(project)
    output = Path(export_catalogue(project)["output"])
    extra = output / "parts" / "example" / "important.txt"
    extra.write_text("keep")
    with pytest.raises(ValueError, match="Unexpected file"):
        export_catalogue(project)
    assert extra.read_text() == "keep"


@pytest.mark.parametrize("entrypoint", ["action_make_all", "action_make_all_no_stl", "working"])
def test_export_is_last_in_full_build(tmp_path, monkeypatch, entrypoint):
    project = tmp_path / "project"
    make_part(project)
    calls = []
    for name in ("oomp_populate", "oomp", "svg", "three_d_model", "scad", "action"):
        monkeypatch.setitem(sys.modules, "working_" + name,
                            SimpleNamespace(main=lambda _name=name, **kw: calls.append(_name)))

    def publish(**kwargs):
        calls.append("only_yaml")
        return export_catalogue(project)

    monkeypatch.setitem(sys.modules, "working_only_yaml", SimpleNamespace(main=publish))
    module = importlib.import_module(entrypoint)
    module.main()
    assert calls[-1] == "only_yaml"
    assert calls.index("only_yaml") > calls.index("action")
    assert {"oomp_populate", "oomp", "scad"} <= set(calls)
    assert (tmp_path / "project_only_yaml" / "parts" / "example" / "image.png").is_file()


def test_failed_build_does_not_publish(tmp_path, monkeypatch):
    import working
    if hasattr(working, "RUN_ERROR_LOG"):
        monkeypatch.setattr(working, "RUN_ERROR_LOG", tmp_path / "errors.txt")

    def fail(**kwargs):
        raise RuntimeError("generation failed")

    def unexpected(**kwargs):
        pytest.fail("Export ran after generation failed")

    monkeypatch.setitem(sys.modules, "working_oomp_populate", SimpleNamespace(main=fail))
    monkeypatch.setitem(sys.modules, "working_only_yaml", SimpleNamespace(main=unexpected))
    with pytest.raises(RuntimeError, match="generation failed"):
        working.run(run_oomp_populate=True, run_only_yaml=True)


def test_electronics_preview_path(tmp_path):
    project = tmp_path / "electronics"
    make_part(project, image="data/working_svg_square_pins_300.png")
    result = export_catalogue(project)
    assert result["parts"] == 1
    assert result["placeholders"] == 0


def test_configured_placeholder_is_replaced_when_preview_arrives(tmp_path):
    project = tmp_path / "electronics"
    source = make_part(project, image=None)
    (project / "config_only_yaml.json").write_text('{"missing_image": "placeholder"}')
    result = export_catalogue(project)
    assert result["placeholders"] == 1
    image = Path(result["output"]) / "parts" / "example" / "image.png"
    before = image.read_bytes()
    with Image.open(image) as preview:
        assert preview.size == (256, 256)
    with pytest.raises(ValueError, match="No usable preview"):
        export_catalogue(project, missing_image="error")
    assert image.read_bytes() == before
    (source / "data").mkdir()
    Image.new("RGB", (300, 150), "blue").save(source / "data/working_svg_square_pins_300.png")
    assert export_catalogue(project)["placeholders"] == 0
    assert image.read_bytes() != before
