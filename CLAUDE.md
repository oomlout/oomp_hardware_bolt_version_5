# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A parts data generator for hardware (bolts, nuts, washers, screws). It produces per-part directories under `parts/` and `parts_source/`, each containing a `working.yaml` with structured metadata, plus generated SVG labels, SCAD files, and images. A Flask webserver exposes a browser UI over the generated data.

## Running the pipeline

```bash
# Full pipeline: populate parts_source → generate oomp files → generate SCAD → run label actions
python working.py

# Individual stages (comment/uncomment flags inside working.py):
python working_oomp_populate.py   # regenerate parts_source from generate() functions
python working_oomp.py            # load parts_source and render templates/labels
python working_scad.py            # generate OpenSCAD files
python working_action.py          # run roboclick AI + CorelDRAW label rendering
```

## Running the webserver

```bash
cd webserver
python app.py
# or from repo root:
python -m webserver.app
```

## Running tests

```bash
pytest tests/
pytest tests/test_generate_structure.py   # single file
```

## Architecture

### Part data pipeline

1. **`working_oomp_populate_*.py`** — each file exports a `generate()` function that returns a list of dicts. Each dict describes one part variant (size, length, type, taxonomy fields). `working_oomp_populate.py` orchestrates all generators and calls `write_extras()` to write `parts_source/<id>/working.yaml`.

2. **`working_oomp.py`** — reads `parts_source/` YAML files, resolves directory/URL via `oomlout_roboclick`, renders Jinja2 templates from `source_file/template_jinja/`, and writes output into `parts/<id>/`.

3. **`working_scad.py`** — reads `parts/*/working.yaml` and calls `scad_help` + `oobb`/`opsc` libraries to produce `.scad` files.

4. **`working_action.py`** — deletes stale generated files then re-runs `oomlout_roboclick` in `ai` mode (generates AI images) and `corel` mode (renders CDR label templates to PNG).

### Key taxonomy fields

Each part dict uses `taxonomy_3` through `taxonomy_7` to build folder names and IDs. `taxonomy_6` must end with `_diameter`; `taxonomy_7` must end with `_mm_length`. These are validated in `tests/test_generate_structure.py`.

### Webserver

`webserver/app.py` is a Flask app. Config is read from YAML files at repo root (`config_part_source.yaml`, `config_ui.yaml`, `config_form.yaml`, `config_port.yaml`). `webserver/services/parts_repository.py` loads parts from `parts/` directories. Routes are in `webserver/routes/`.

### Source templates

`source_file/template_jinja/` contains Jinja2 templates (`.svg.j2`, `.cdr`) and base SVG files used to render per-part labels. CorelDRAW `.cdr` files are the master label sources.

### Migration scripts

`migration/` contains one-off scripts and frozen YAML/JSON snapshots of legacy part data. These are not part of the active pipeline.

## External dependencies

The pipeline depends on `oomlout_roboclick`, `oomp`, `oomp_helper`, `oomp_populate_helper`, `opsc`, `oobb`, and `scad_help` — these are separate oomlout Python packages that must be installed in the environment.
