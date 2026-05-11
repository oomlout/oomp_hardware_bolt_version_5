from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from PIL import Image

from webserver.app import create_app
from webserver.services import config_form, config_part_source, config_port, config_ui
from webserver.services.parts_repository import format_file_size, load_part_record, populate_part_assets
from webserver.services.source_writer import build_form_response, write_manual_entry


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, allow_unicode=False, sort_keys=True)


def write_image(path: Path, size: tuple[int, int] = (320, 240), color: tuple[int, int, int] = (10, 120, 180)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", size, color)
    image.save(path, format="PNG")


class WebserverAppTests(unittest.TestCase):
    def test_format_file_size_uses_compact_labels(self) -> None:
        self.assertEqual(format_file_size(980), "980")
        self.assertEqual(format_file_size(1200), "1.2k")
        self.assertEqual(format_file_size(15500), "15.5k")
        self.assertEqual(format_file_size(2400000), "2.4M")

    def test_load_part_record_includes_working_manual_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )
            write_yaml(
                part_dir / "working_manual.yaml",
                {
                    "content": ["ribbon"],
                    "taxonomy": ["craft/ribbon"],
                },
            )

            record = load_part_record(part_dir, parts_dir)

            self.assertEqual(record["working_manual"]["content"], ["ribbon"])
            self.assertEqual(record["working_manual"]["taxonomy"], ["craft/ribbon"])
            self.assertEqual(record["data"]["content"], ["ribbon"])
            self.assertEqual(record["data"]["taxonomy"], ["craft/ribbon"])
            self.assertTrue(record["working_manual_exists"])
            self.assertIsNone(record["working_manual_error"])

    def test_populate_part_assets_includes_file_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )
            (part_dir / "shape.scad").write_text("cube([1,1,1]);", encoding="utf-8")
            (part_dir / "label.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
            (part_dir / "notes.txt").write_text("hello", encoding="utf-8")

            record = load_part_record(part_dir, parts_dir)
            part = populate_part_assets(record)
            files_by_name = {file["name"]: file for file in part["files"]}

            self.assertEqual(files_by_name["shape.scad"]["actions"][0]["label"], "Generate STL")
            self.assertEqual(files_by_name["shape.scad"]["actions"][1]["id"], "delete-file")
            self.assertTrue(files_by_name["shape.scad"]["is_text_previewable"])
            self.assertEqual(files_by_name["shape.scad"]["text_language_label"], "OpenSCAD")
            self.assertEqual(files_by_name["label.svg"]["actions"][0]["label"], "Convert to PDF")
            self.assertEqual(files_by_name["label.svg"]["actions"][1]["id"], "delete-file")
            self.assertEqual(files_by_name["notes.txt"]["actions"][0]["id"], "delete-file")
            self.assertTrue(files_by_name["notes.txt"]["is_text_previewable"])
            self.assertEqual(files_by_name["notes.txt"]["text_language_label"], "Text")
            self.assertEqual(part["preview_items"][0]["relative_path"], "label.svg")
            self.assertEqual(part["preview_items"][1]["relative_path"], "notes.txt")
            self.assertEqual(part["preview_items"][2]["relative_path"], "shape.scad")

    def test_add_route_records_manual_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            manual_path = root / "working_manual.yaml"
            parts_dir.mkdir()
            source_dir.mkdir()

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "MANUAL_QUEUE_PATH": manual_path,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.post(
                "/add",
                data={
                    "family": "generic",
                    "diameter": "40",
                    "depth": "30",
                    "hole_top_diameter": "20",
                },
                follow_redirects=True,
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(manual_path.exists())
            with manual_path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
            self.assertEqual(list(loaded.keys()), ["options"])
            self.assertEqual(loaded["options"][0]["type_name"], "hole_cover")
            self.assertEqual(loaded["options"][0]["diameter"], 40)
            self.assertEqual(loaded["options"][0]["depth"], 30)
            self.assertEqual(loaded["options"][0]["hole_top_diameter"], 20)

    def test_explore_route_renders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "organizing_electrical_wire_clip"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Wire Clip",
                    "taxonomy_1": "organizing",
                    "taxonomy_2": "electrical",
                    "taxonomy_3": "wire",
                    "taxonomy_4": "clip",
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/explore")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Wire Clip", response.data)
            self.assertIn(b"Taxonomy", response.data)
            self.assertIn(b'name="search_fields"', response.data)
            self.assertIn(b'value="id"', response.data)

    def test_explore_search_defaults_to_id_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "organizing_electrical_wire_clip"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Fancy Search Name",
                    "taxonomy_1": "organizing",
                    "taxonomy_2": "electrical",
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/explore?q=fancy")

            self.assertEqual(response.status_code, 200)
            self.assertNotIn(b"Fancy Search Name", response.data)
            self.assertIn(b'No parts match the current taxonomy path and search query.', response.data)

    def test_explore_search_can_include_name_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            config_path = root / "config_ui.yaml"
            part_dir = parts_dir / "organizing_electrical_wire_clip"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Fancy Search Name",
                    "taxonomy_1": "organizing",
                    "taxonomy_2": "electrical",
                },
            )
            write_yaml(
                config_path,
                {
                    "search_fields": {
                        "available": [
                            {"name": "id", "label": "ID"},
                            {"name": "name", "label": "Name"},
                        ],
                        "default_selected": ["id"],
                    }
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "CONFIG_UI_PATH": config_path,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/explore?q=fancy&search_fields=id&search_fields=name")

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Fancy Search Name", response.data)
            self.assertIn(b'value="name"', response.data)

    def test_explore_search_treats_spaces_as_and_across_underscores(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            matching_part_dir = parts_dir / "tool_is_a_set"
            non_matching_part_dir = parts_dir / "tool_only_box"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                matching_part_dir / "working.yaml",
                {
                    "name_proper": "Tool Is A Set",
                    "taxonomy_1": "organizing",
                },
            )
            write_yaml(
                non_matching_part_dir / "working.yaml",
                {
                    "name_proper": "Tool Only Box",
                    "taxonomy_1": "organizing",
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/explore?q=tool%20set")

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Tool Is A Set", response.data)
            self.assertNotIn(b"Tool Only Box", response.data)

    def test_explore_search_treats_dash_like_space_separator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            matching_part_dir = parts_dir / "tool_is_a_set"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                matching_part_dir / "working.yaml",
                {
                    "name_proper": "Tool Is A Set",
                    "taxonomy_1": "organizing",
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/explore?q=tool-set")

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Tool Is A Set", response.data)

    def test_explore_search_can_include_taxonomy_from_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            config_path = root / "config_ui.yaml"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                },
            )
            write_yaml(
                part_dir / "working_manual.yaml",
                {
                    "taxonomy": ["craft/ribbon"],
                },
            )
            write_yaml(
                config_path,
                {
                    "search_fields": {
                        "available": [
                            {"name": "id", "label": "ID"},
                            {"name": "taxonomy", "label": "Taxonomy"},
                        ],
                        "default_selected": ["id"],
                    }
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "CONFIG_UI_PATH": config_path,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/explore?q=craft%2Fribbon&search_fields=taxonomy")

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Warehouse Storage Tote Stackable Fullsize Size 210 Count", response.data)

    def test_part_detail_renders_manual_editor_with_default_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )
            (part_dir / "preview.png").write_bytes(b"preview")
            (part_dir / "notes.txt").write_text("hello", encoding="utf-8")

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/parts/warehouse_storage_tote_stackable_fullsize_size_210_count")

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Manual Attributes", response.data)
            self.assertIn(b'name="content"', response.data)
            self.assertIn(b'name="taxonomy"', response.data)
            self.assertIn(b"Save Manual Details", response.data)
            self.assertIn(b"Reload Details", response.data)
            self.assertIn(b'rows="3"', response.data)
            self.assertIn(b'details class="collapsible-panel"', response.data)
            self.assertIn(b'target="download-frame"', response.data)
            self.assertIn(b"file-preview-popover", response.data)

    def test_part_detail_renders_file_actions_and_compact_sizes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )
            (part_dir / "shape.scad").write_text("cube([1,1,1]);\n" * 100, encoding="utf-8")
            (part_dir / "label.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/parts/warehouse_storage_tote_stackable_fullsize_size_210_count")

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Generate STL", response.data)
            self.assertIn(b"Convert to PDF", response.data)
            self.assertIn(b"actions/delete-file", response.data)
            self.assertIn(b'aria-label="Download"', response.data)
            self.assertIn(b"file-action-icon--download", response.data)
            self.assertIn(b'data-image-viewer-trigger="true"', response.data)
            self.assertIn(b"OpenSCAD", response.data)
            self.assertIn(b'id="image-viewer-code"', response.data)
            self.assertNotIn(b'/static/text_file_viewer.js', response.data)
            self.assertIn(b'data-confirm-message="Delete shape.scad? This cannot be undone."', response.data)
            self.assertIn(b'aria-label="Delete"', response.data)
            self.assertIn(b'/static/file_actions.js', response.data)
            self.assertIn(b">1.6k<", response.data)
            self.assertNotIn(b"bytes", response.data)

    def test_part_image_viewer_data_includes_text_and_image_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )
            (part_dir / "preview.png").write_bytes(b"preview")
            (part_dir / "notes.txt").write_text("hello\npreview", encoding="utf-8")

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get(
                "/parts/warehouse_storage_tote_stackable_fullsize_size_210_count/viewer-data"
            )

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["items"][0]["kind"], "image")
            self.assertEqual(payload["items"][0]["relativePath"], "preview.png")
            self.assertEqual(payload["items"][1]["kind"], "text")
            self.assertEqual(payload["items"][1]["relativePath"], "notes.txt")
            self.assertEqual(payload["items"][1]["language"], "plaintext")
            self.assertEqual(payload["items"][1]["languageLabel"], "Text")
            self.assertIn("hello", payload["items"][1]["content"])
            self.assertFalse(payload["items"][1]["truncated"])

    def test_part_file_action_route_launches_detached_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )
            source_file = part_dir / "shape.scad"
            source_file.write_text("cube([1,1,1]);", encoding="utf-8")

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()

            with patch("webserver.routes.parts.generation_runner.launch_detached_command") as launch_mock:
                response = client.post(
                    "/parts/warehouse_storage_tote_stackable_fullsize_size_210_count/files/shape.scad/actions/generate-stl",
                    follow_redirects=True,
                )

            self.assertEqual(response.status_code, 200)
            launch_mock.assert_called_once()
            command = launch_mock.call_args.args[0]
            cwd = launch_mock.call_args.kwargs["cwd"]
            self.assertEqual(command[0], "openscad")
            self.assertEqual(command[1], "-o")
            self.assertTrue(str(command[2]).endswith("shape.stl"))
            self.assertTrue(str(command[3]).endswith("shape.scad"))
            self.assertEqual(Path(cwd), part_dir)
            self.assertIn(b"Launched Generate STL", response.data)

    def test_part_file_action_route_rejects_invalid_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )
            (part_dir / "notes.txt").write_text("hello", encoding="utf-8")

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.post(
                "/parts/warehouse_storage_tote_stackable_fullsize_size_210_count/files/notes.txt/actions/generate-stl"
            )

            self.assertEqual(response.status_code, 404)

    def test_part_file_action_route_deletes_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )
            doomed_file = part_dir / "notes.txt"
            doomed_file.write_text("hello", encoding="utf-8")

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.post(
                "/parts/warehouse_storage_tote_stackable_fullsize_size_210_count/files/notes.txt/actions/delete-file",
                follow_redirects=True,
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(doomed_file.exists())
            self.assertIn(b"Deleted notes.txt.", response.data)

    def test_part_manual_update_route_writes_working_manual_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )
            write_yaml(
                part_dir / "working_manual.yaml",
                {
                    "content": ["old ribbon"],
                    "taxonomy": ["craft/old_ribbon"],
                    "notes": ["keep me"],
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.post(
                "/parts/warehouse_storage_tote_stackable_fullsize_size_210_count/manual",
                data={
                    "content": "ribbon\nelastic",
                    "taxonomy": "craft/ribbon\ncraft/elastic",
                },
                follow_redirects=True,
            )

            self.assertEqual(response.status_code, 200)
            with (part_dir / "working_manual.yaml").open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
            self.assertEqual(loaded["content"], ["ribbon", "elastic"])
            self.assertEqual(loaded["taxonomy"], ["craft/ribbon", "craft/elastic"])
            self.assertEqual(loaded["notes"], ["keep me"])
            self.assertIn(b"Saved working_manual.yaml", response.data)

    def test_part_manual_update_route_creates_manual_file_from_non_empty_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.post(
                "/parts/warehouse_storage_tote_stackable_fullsize_size_210_count/manual",
                data={
                    "content": "",
                    "taxonomy": "craft/ribbon",
                },
                follow_redirects=True,
            )

            self.assertEqual(response.status_code, 200)
            with (part_dir / "working_manual.yaml").open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
            self.assertEqual(loaded, {"taxonomy": ["craft/ribbon"]})
            self.assertIn(b"Saved working_manual.yaml", response.data)

    def test_part_reload_route_refreshes_detail_from_disk(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()

            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Updated",
                    "taxonomy_1": "warehouse",
                    "taxonomy_2": "storage",
                },
            )
            response = client.post(
                "/parts/warehouse_storage_tote_stackable_fullsize_size_210_count/reload",
                follow_redirects=True,
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Warehouse Storage Tote Updated", response.data)
            self.assertIn(b"Reloaded part details", response.data)

    def test_fast_reload_updates_changed_part(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "organizing_electrical_wire_clip"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Wire Clip",
                    "taxonomy_1": "organizing",
                    "taxonomy_2": "electrical",
                    "taxonomy_3": "wire",
                    "taxonomy_4": "clip",
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            cache = app.config["PARTS_CACHE"]
            first_name = cache.get_part("organizing_electrical_wire_clip")["name"]
            self.assertEqual(first_name, "Wire Clip")

            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Wire Clip Updated",
                    "taxonomy_1": "organizing",
                    "taxonomy_2": "electrical",
                    "taxonomy_3": "wire",
                    "taxonomy_4": "clip",
                },
            )

            summary = cache.reload_changed()
            updated_name = cache.get_part("organizing_electrical_wire_clip")["name"]
            self.assertGreaterEqual(summary.changed, 1)
            self.assertEqual(updated_name, "Wire Clip Updated")

    def test_preview_priority_prefers_yaml_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "organizing_electrical_wire_clip"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Wire Clip",
                    "taxonomy_1": "organizing",
                    "taxonomy_2": "electrical",
                    "taxonomy_3": "wire",
                    "taxonomy_4": "clip",
                },
            )
            (part_dir / "initial_generated_icon.png").write_bytes(b"icon")
            (part_dir / "3dpr.png").write_bytes(b"preview")
            config_path = root / "config_ui.yaml"
            write_yaml(config_path, {"preview_priority": ["initial_generated_icon.png", "3dpr.png", "*.png"]})

            loaded = config_ui.load_ui_config(config_path)
            record = load_part_record(part_dir, parts_dir, loaded["preview_priority"])

            self.assertEqual(record["preview_file"], "initial_generated_icon.png")

    def test_fast_reload_promotes_to_full_reload_when_ui_config_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            config_path = root / "config_ui.yaml"
            part_dir = parts_dir / "organizing_electrical_wire_clip"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Wire Clip",
                    "taxonomy_1": "organizing",
                    "taxonomy_2": "electrical",
                    "taxonomy_3": "wire",
                    "taxonomy_4": "clip",
                },
            )
            (part_dir / "3dpr.png").write_bytes(b"preview")
            (part_dir / "initial_generated_icon.png").write_bytes(b"icon")
            write_yaml(config_path, {"preview_priority": ["3dpr.png", "initial_generated_icon.png"]})

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "CONFIG_UI_PATH": config_path,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            self.assertEqual(app.config["PARTS_CACHE"].get_part("organizing_electrical_wire_clip")["preview_file"], "3dpr.png")

            write_yaml(config_path, {"preview_priority": ["initial_generated_icon.png", "3dpr.png"]})
            response = client.post("/reload/fast", follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"promoted itself to a full cache rebuild", response.data)
            self.assertEqual(
                app.config["PARTS_CACHE"].get_part("organizing_electrical_wire_clip")["preview_file"],
                "initial_generated_icon.png",
            )

    def test_form_response_preserves_generic_values_without_mapping(self) -> None:
        values = build_form_response(
            {
                "taxonomy_1": "Organizing",
                "taxonomy_2": "Electrical",
                "taxonomy_3": "Wire",
                "taxonomy_4": "Clip",
            },
            config_form.DEFAULT_FORM_CONFIG["families"]["generic"],
        )

        self.assertEqual(values["taxonomy_1"], "Organizing")
        self.assertEqual(values["taxonomy_4"], "Clip")

    def test_manual_writer_appends_entry_to_yaml_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manual_path = Path(temp_dir) / "working_manual.yaml"
            result = write_manual_entry(
                manual_path,
                {
                    "taxonomy_1": "organizing",
                    "taxonomy_2": "electrical",
                    "taxonomy_3": "wire",
                    "taxonomy_4": "clip",
                },
                config_form.DEFAULT_FORM_CONFIG["families"]["generic"],
            )

            self.assertEqual(result["entry_count"], 1)
            with manual_path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
            self.assertEqual(list(loaded.keys()), ["options"])
            self.assertEqual(loaded["options"][0]["taxonomy_3"], "wire")

    def test_manual_writer_migrates_legacy_entries_to_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manual_path = Path(temp_dir) / "working_manual.yaml"
            write_yaml(
                manual_path,
                {
                    "entries": [
                        {
                            "family": "generic",
                            "values": {
                                "item_type": "hole_cover",
                                "diameter": 35,
                                "depth": 10,
                                "hole_top_diameter": 15,
                            },
                        }
                    ]
                },
            )

            result = write_manual_entry(
                manual_path,
                {
                    "diameter": "40",
                    "depth": "30",
                    "hole_top_diameter": "20",
                },
                {
                    "defaults": {},
                    "fields": [
                        {"name": "diameter", "label": "Diameter", "input_type": "number", "required": True},
                        {"name": "depth", "label": "Depth", "input_type": "number", "required": True},
                        {
                            "name": "hole_top_diameter",
                            "label": "Hole Top Diameter",
                            "input_type": "number",
                            "required": True,
                        },
                    ],
                },
            )

            self.assertEqual(result["entry_count"], 2)
            with manual_path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
            self.assertEqual(list(loaded.keys()), ["options"])
            self.assertEqual(loaded["options"][0]["type_name"], "hole_cover")
            self.assertEqual(loaded["options"][0]["diameter"], 35)
            self.assertEqual(loaded["options"][1]["hole_top_diameter"], 20)

    def test_manual_writer_normalizes_item_type_to_type_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manual_path = Path(temp_dir) / "working_manual.yaml"
            write_yaml(
                manual_path,
                {
                    "options": [
                        {
                            "item_type": "hole_cover",
                            "diameter": 35,
                            "depth": 10,
                            "hole_top_diameter": 15,
                        }
                    ]
                },
            )

            result = write_manual_entry(
                manual_path,
                {
                    "diameter": "40",
                    "depth": "30",
                    "hole_top_diameter": "20",
                },
                {
                    "defaults": {"type_name": "hole_cover"},
                    "fields": [
                        {"name": "diameter", "label": "Diameter", "input_type": "number", "required": True},
                        {"name": "depth", "label": "Depth", "input_type": "number", "required": True},
                        {
                            "name": "hole_top_diameter",
                            "label": "Hole Top Diameter",
                            "input_type": "number",
                            "required": True,
                        },
                    ],
                },
            )

            self.assertEqual(result["entry_count"], 2)
            with manual_path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
            self.assertEqual(list(loaded.keys()), ["options"])
            self.assertNotIn("item_type", loaded["options"][0])
            self.assertEqual(loaded["options"][0]["type_name"], "hole_cover")
            self.assertEqual(loaded["options"][1]["type_name"], "hole_cover")

    def test_manual_writer_merges_legacy_entries_when_options_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manual_path = Path(temp_dir) / "working_manual.yaml"
            write_yaml(
                manual_path,
                {
                    "options": [
                        {
                            "type_name": "hole_cover",
                            "diameter": 40,
                            "depth": 30,
                            "hole_top_diameter": 20,
                        }
                    ],
                    "entries": [
                        {
                            "family": "generic",
                            "values": {
                                "item_type": "hole_cover",
                                "diameter": 35,
                                "depth": 10,
                                "hole_top_diameter": 15,
                            },
                        }
                    ],
                },
            )

            result = write_manual_entry(
                manual_path,
                {
                    "diameter": "50",
                    "depth": "25",
                    "hole_top_diameter": "18",
                },
                {
                    "defaults": {"type_name": "hole_cover"},
                    "fields": [
                        {"name": "diameter", "label": "Diameter", "input_type": "number", "required": True},
                        {"name": "depth", "label": "Depth", "input_type": "number", "required": True},
                        {
                            "name": "hole_top_diameter",
                            "label": "Hole Top Diameter",
                            "input_type": "number",
                            "required": True,
                        },
                    ],
                },
            )

            self.assertEqual(result["entry_count"], 3)
            with manual_path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
            self.assertEqual(list(loaded.keys()), ["options"])
            self.assertEqual(loaded["options"][1]["type_name"], "hole_cover")
            self.assertEqual(loaded["options"][2]["diameter"], 50)

    def test_form_config_prefers_override_path_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = root / "config_form_base.yaml"
            override_path = root / "config_form.yaml"
            write_yaml(
                base_path,
                {
                    "default_family": "generic",
                    "families": {
                        "generic": {
                            "label": "Base Generic",
                            "fields": [{"name": "taxonomy_1", "required": True}],
                        }
                    },
                },
            )
            write_yaml(
                override_path,
                {
                    "default_family": "generic",
                    "families": {
                        "generic": {
                            "label": "Override Generic",
                            "fields": [{"name": "taxonomy_1", "required": True}],
                        }
                    },
                },
            )

            loaded = config_form.load_form_config(base_path, override_path)
            self.assertEqual(loaded["families"]["generic"]["label"], "Override Generic")

    def test_form_config_uses_base_path_when_override_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = root / "config_form_base.yaml"
            missing_override = root / "config_form.yaml"
            write_yaml(
                base_path,
                {
                    "default_family": "generic",
                    "families": {
                        "generic": {
                            "label": "Base Generic",
                            "fields": [{"name": "taxonomy_1", "required": True}],
                        }
                    },
                },
            )

            loaded = config_form.load_form_config(base_path, missing_override)
            self.assertEqual(loaded["families"]["generic"]["label"], "Base Generic")

    def test_ui_config_loads_search_field_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config_ui.yaml"
            write_yaml(
                config_path,
                {
                    "search_fields": {
                        "available": [
                            {"name": "id", "label": "ID"},
                            {"name": "name", "label": "Name"},
                        ],
                        "default_selected": ["id"],
                    }
                },
            )

            loaded = config_ui.load_ui_config(config_path)

            self.assertEqual(
                [field["name"] for field in loaded["search_fields"]["available"]],
                ["id", "name"],
            )
            self.assertEqual(loaded["search_fields"]["default_selected"], ["id"])

    def test_ui_config_loads_image_serving_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config_ui.yaml"
            write_yaml(
                config_path,
                {
                    "image_serving": {
                        "cache_dir": "auto",
                        "presets": {
                            "modal": {
                                "width": 1600,
                                "height": 1200,
                                "fit": "contain",
                                "quality": 90,
                            }
                        },
                    }
                },
            )

            loaded = config_ui.load_ui_config(config_path)

            self.assertTrue(loaded["image_serving"]["enabled"])
            self.assertEqual(loaded["image_serving"]["presets"]["modal"]["width"], 1600)
            self.assertEqual(loaded["image_serving"]["presets"]["modal"]["quality"], 90)

    def test_part_source_config_defaults_to_relative_parts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config_part_source.yaml"

            loaded = config_part_source.load_part_source_config(config_path, root)

            self.assertEqual(loaded["directories"], ["parts"])
            self.assertEqual(loaded["resolved_directories"], [root.joinpath("parts").resolve(strict=False)])

    def test_part_source_config_absolute_parent_directory_resolves_to_child_parts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config_part_source.yaml"
            external_root = root / "external_source"
            write_yaml(
                config_path,
                {
                    "directories": [str(external_root.resolve(strict=False))],
                },
            )

            loaded = config_part_source.load_part_source_config(config_path, root)

            self.assertEqual(
                loaded["resolved_directories"],
                [external_root.joinpath("parts").resolve(strict=False)],
            )

    def test_port_config_loads_custom_port(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config_port.yaml"
            write_yaml(config_path, {"port": 5055})

            loaded = config_port.load_port_config(config_path)

            self.assertEqual(loaded["port"], 5055)

    def test_port_config_loads_custom_host(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config_port.yaml"
            write_yaml(config_path, {"host": "0.0.0.0", "port": 5055})

            loaded = config_port.load_port_config(config_path)

            self.assertEqual(loaded["host"], "0.0.0.0")

    def test_create_app_uses_configured_port(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            config_port_path = root / "config_port.yaml"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(config_port_path, {"port": 5057})

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "CONFIG_PORT_PATH": config_port_path,
                    "SECRET_KEY": "test",
                }
            )

            self.assertEqual(app.config["PORT"], 5057)
            self.assertEqual(app.config["HOST"], "127.0.0.1")

    def test_create_app_uses_configured_host(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            config_port_path = root / "config_port.yaml"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(config_port_path, {"host": "0.0.0.0", "port": 5057})

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "CONFIG_PORT_PATH": config_port_path,
                    "SECRET_KEY": "test",
                }
            )

            self.assertEqual(app.config["HOST"], "0.0.0.0")
            self.assertEqual(app.config["PORT"], 5057)

    def test_create_app_prefers_repo_root_config_over_webserver_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            webserver_dir = root / "webserver"
            parts_dir.mkdir()
            source_dir.mkdir()
            webserver_dir.mkdir()
            write_yaml(root / "config_port.yaml", {"port": 5059})
            write_yaml(webserver_dir / "config_port.yaml", {"port": 5061})

            app = create_app(
                {
                    "TESTING": True,
                    "REPO_ROOT": root,
                    "SECRET_KEY": "test",
                }
            )

            self.assertEqual(app.config["CONFIG_PORT_PATH"], root / "config_port.yaml")
            self.assertEqual(app.config["PORT"], 5059)

    def test_create_app_loads_parts_from_multiple_directories_and_prefers_first_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "parts_source"
            first_root_dir = root / "source_one"
            second_root_dir = root / "source_two"
            first_parts_dir = first_root_dir / "parts"
            second_parts_dir = second_root_dir / "parts"
            config_path = root / "config_part_source.yaml"
            first_shared = first_parts_dir / "shared_part"
            second_shared = second_parts_dir / "shared_part"
            second_unique = second_parts_dir / "second_only_part"
            source_dir.mkdir()
            first_parts_dir.mkdir(parents=True)
            second_parts_dir.mkdir(parents=True)
            write_yaml(
                first_shared / "working.yaml",
                {
                    "name_proper": "Shared Part From First Source",
                    "taxonomy_1": "shared",
                },
            )
            write_yaml(
                second_shared / "working.yaml",
                {
                    "name_proper": "Shared Part From Second Source",
                    "taxonomy_1": "shared",
                },
            )
            write_yaml(
                second_unique / "working.yaml",
                {
                    "name_proper": "Second Source Only Part",
                    "taxonomy_1": "unique",
                },
            )
            write_yaml(
                config_path,
                {
                    "directories": ["source_one", "source_two"],
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "REPO_ROOT": root,
                    "PARTS_SOURCE_DIR": source_dir,
                    "CONFIG_PART_SOURCE_PATH": config_path,
                    "SECRET_KEY": "test",
                }
            )

            shared = app.config["PARTS_CACHE"].get_part("shared_part")
            second_only = app.config["PARTS_CACHE"].get_part("second_only_part")

            self.assertEqual(shared["name"], "Shared Part From First Source")
            self.assertEqual(second_only["name"], "Second Source Only Part")
            self.assertEqual(app.config["PARTS_DIRS"], [first_parts_dir.resolve(strict=False), second_parts_dir.resolve(strict=False)])

    def test_fast_reload_promotes_to_full_reload_when_part_source_config_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "parts_source"
            first_root_dir = root / "source_one"
            second_root_dir = root / "source_two"
            first_parts_dir = first_root_dir / "parts"
            second_parts_dir = second_root_dir / "parts"
            config_path = root / "config_part_source.yaml"
            source_dir.mkdir()
            first_parts_dir.mkdir(parents=True)
            second_parts_dir.mkdir(parents=True)
            write_yaml(
                (first_parts_dir / "first_part" / "working.yaml"),
                {
                    "name_proper": "First Part",
                    "taxonomy_1": "first",
                },
            )
            write_yaml(
                (second_parts_dir / "second_part" / "working.yaml"),
                {
                    "name_proper": "Second Part",
                    "taxonomy_1": "second",
                },
            )
            write_yaml(config_path, {"directories": ["source_one"]})

            app = create_app(
                {
                    "TESTING": True,
                    "REPO_ROOT": root,
                    "PARTS_SOURCE_DIR": source_dir,
                    "CONFIG_PART_SOURCE_PATH": config_path,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()

            self.assertIsNotNone(app.config["PARTS_CACHE"].get_part("first_part"))
            self.assertIsNone(app.config["PARTS_CACHE"].get_part("second_part"))

            write_yaml(config_path, {"directories": ["source_one", "source_two"]})
            response = client.post("/reload/fast", follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"promoted itself to a full cache rebuild", response.data)
            self.assertIsNotNone(app.config["PARTS_CACHE"].get_part("second_part"))

    def test_explore_route_renders_popup_viewer_markup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "organizing_electrical_wire_clip"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Wire Clip",
                    "taxonomy_1": "organizing",
                },
            )
            write_image(part_dir / "preview.png", size=(400, 240))

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/explore")

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'id="image-viewer"', response.data)
            self.assertIn(b'data-image-viewer-trigger="true"', response.data)
            self.assertIn(b"image_viewer.js", response.data)

    def test_part_image_route_returns_resized_derivative_and_reuses_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            cache_dir = root / "machine_cache"
            config_path = root / "config_ui.yaml"
            part_dir = parts_dir / "organizing_electrical_wire_clip"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Wire Clip",
                    "taxonomy_1": "organizing",
                },
            )
            write_image(part_dir / "preview.png", size=(400, 200))
            write_yaml(
                config_path,
                {
                    "image_serving": {
                        "cache_dir": str(cache_dir.resolve(strict=False)),
                    }
                },
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "CONFIG_UI_PATH": config_path,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()

            response = client.get("/parts/organizing_electrical_wire_clip/image/preview.png?w=100")
            self.assertEqual(response.status_code, 200)
            _ = response.data
            response.close()
            self.assertTrue(cache_dir.exists())
            cached_files_after_first = sorted(path for path in cache_dir.rglob("*") if path.is_file())
            self.assertTrue(cached_files_after_first)
            with Image.open(part_dir / "preview.png") as original_image:
                self.assertEqual(original_image.size, (400, 200))
            derivative_path = cached_files_after_first[0]
            with Image.open(derivative_path) as derivative_image:
                self.assertEqual(derivative_image.size, (100, 50))

            response = client.get("/parts/organizing_electrical_wire_clip/image/preview.png?w=100")
            self.assertEqual(response.status_code, 200)
            _ = response.data
            response.close()
            cached_files_after_second = sorted(path for path in cache_dir.rglob("*") if path.is_file())
            self.assertEqual(cached_files_after_second, cached_files_after_first)

    def test_part_image_route_falls_back_to_original_for_svg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "organizing_electrical_wire_clip"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Wire Clip",
                },
            )
            svg_path = part_dir / "preview.svg"
            svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="120" height="80" fill="red"/></svg>',
                encoding="utf-8",
            )

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/parts/organizing_electrical_wire_clip/image/preview.svg?preset=modal")

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"<svg", response.data)
            response.close()

    def test_part_detail_renders_popup_image_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                },
            )
            write_image(part_dir / "preview.png", size=(640, 480))
            write_image(part_dir / "detail.png", size=(800, 600), color=(120, 20, 120))

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/parts/warehouse_storage_tote_stackable_fullsize_size_210_count")

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"View Image", response.data)
            self.assertIn(b"Open Original", response.data)
            self.assertIn(b'data-image-viewer-trigger="true"', response.data)

    def test_cache_records_omit_eager_file_inventory_until_detail_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "organizing_electrical_wire_clip"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Wire Clip",
                    "taxonomy_1": "organizing",
                },
            )
            write_image(part_dir / "preview.png", size=(400, 240))
            (part_dir / "notes.txt").write_text("hello", encoding="utf-8")

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )

            cached_part = app.config["PARTS_CACHE"].get_part("organizing_electrical_wire_clip")

            self.assertEqual(cached_part["file_count"], 3)
            self.assertEqual(cached_part["image_count"], 1)
            self.assertNotIn("files", cached_part)
            self.assertNotIn("image_files", cached_part)

    def test_part_viewer_data_route_returns_images_on_demand(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            part_dir = parts_dir / "warehouse_storage_tote_stackable_fullsize_size_210_count"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                part_dir / "working.yaml",
                {
                    "name_proper": "Warehouse Storage Tote Stackable Fullsize Size 210 Count",
                    "taxonomy_1": "warehouse",
                },
            )
            write_image(part_dir / "preview.png", size=(640, 480))
            write_image(part_dir / "detail.png", size=(800, 600), color=(120, 20, 120))

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/parts/warehouse_storage_tote_stackable_fullsize_size_210_count/viewer-data")

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["partId"], "warehouse_storage_tote_stackable_fullsize_size_210_count")
            self.assertEqual(len(payload["items"]), 3)
            self.assertEqual(payload["items"][0]["kind"], "image")
            self.assertTrue(payload["items"][0]["relativePath"].endswith(".png"))
            self.assertEqual(payload["items"][1]["kind"], "image")
            self.assertEqual(payload["items"][2]["kind"], "text")
            self.assertEqual(payload["items"][2]["relativePath"], "working.yaml")

    def test_explore_route_can_sort_by_image_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parts_dir = root / "parts"
            source_dir = root / "parts_source"
            first_part_dir = parts_dir / "organizing_electrical_wire_clip"
            second_part_dir = parts_dir / "organizing_electrical_wire_bundle"
            parts_dir.mkdir()
            source_dir.mkdir()
            write_yaml(
                first_part_dir / "working.yaml",
                {
                    "name_proper": "Wire Clip",
                    "taxonomy_1": "organizing",
                },
            )
            write_yaml(
                second_part_dir / "working.yaml",
                {
                    "name_proper": "Wire Bundle",
                    "taxonomy_1": "organizing",
                },
            )
            write_image(first_part_dir / "preview.png", size=(400, 240))
            write_image(second_part_dir / "preview.png", size=(400, 240))
            write_image(second_part_dir / "detail.png", size=(400, 240), color=(220, 40, 90))

            app = create_app(
                {
                    "TESTING": True,
                    "PARTS_DIR": parts_dir,
                    "PARTS_SOURCE_DIR": source_dir,
                    "SECRET_KEY": "test",
                }
            )
            client = app.test_client()
            response = client.get("/explore?sort=images_desc")

            self.assertEqual(response.status_code, 200)
            html = response.data.decode("utf-8")
            self.assertLess(html.index("Wire Bundle"), html.index("Wire Clip"))


if __name__ == "__main__":
    unittest.main()
