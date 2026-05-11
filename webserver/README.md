# Webserver

Flask app for browsing generated parts from `parts/` and recording new manual entries into `working_manual.yaml`.

## Run

From the repo root:

```bash
python -m webserver.app
```

Then open `http://<host>:<port>/explore`.
The default host is `127.0.0.1`, and both host and port are configurable through `config_port.yaml`.
Part source directories are configurable through `config_part_source.yaml`.

## Main Behaviors

- `/` redirects to `/explore`
- explore view loads from an in-memory cache built at startup
- explore results are shown as dense horizontal rows for faster scanning
- explore now supports sort selection in addition to taxonomy and text filtering
- `Reload Fast` only refreshes new or changed part folders
- `Reload Fast` promotes itself to a full rebuild if `config_ui.yaml` changes
- `Reload All` rebuilds the cache from disk
- `Run Generation` launches `action_make_all.py` in a separate visible Windows `cmd` window
- `/add` records a new manual entry into `working_manual.yaml` at the repo root
- preview image selection is driven by `config_ui.yaml`
- image previews are served through a derived-image route when possible instead of always using full-size originals
- clicking preview images opens an in-page popup viewer with previous and next controls
- image viewer data is loaded on demand per part instead of being embedded for every explore result up front
- startup host and port are driven by `config_port.yaml`
- part source directories are driven by `config_part_source.yaml`
- part detail pages load full file inventory and image metadata on demand instead of storing it eagerly in the explore cache

## Styling Structure

- Design tokens live in `static/style.css` under `:root`
- Shared layout and component classes are defined in `style.css`
- Shared page chrome and toolbar controls live in `templates/base.html`
- Page-specific behaviors are in `static/explore.js` and `static/add_item.js`
- Popup viewer behavior lives in `static/image_viewer.js`

## Application Structure

- `app.py` creates the Flask app, initializes runtime config/cache state, and registers blueprints
- `routes/explore.py` owns the explore/index pages
- `routes/parts.py` owns part detail, file/image serving, and on-demand viewer data
- `routes/manual.py` owns the add-item flow
- `routes/actions.py` owns reload and generation actions
- `runtime.py` owns config reload and cache setup helpers
- `presentation.py` owns shared view-layer helpers such as sort/search normalization and URL helpers

## UI Config

- `config_ui.yaml` currently exposes `preview_priority`
- `config_ui.yaml` also exposes `image_serving`
- The list is evaluated from top to bottom
- Exact filenames are matched before wildcard fallbacks
- `Reload All` always applies config changes
- `Reload Fast` also applies config changes and will rebuild the cache if the UI config changed

## Image Serving

- raster images are resized and cached for explore thumbnails, file popovers, detail previews, and popup viewing
- the default machine-local cache path resolves under `%LOCALAPPDATA%\project_base\webserver_image_cache`
- an explicit absolute cache path can be set with `image_serving.cache_dir`
- SVG files currently fall back to the original asset instead of being rasterized
- the original full-size file remains available through the popup viewer's `Open Original` action

## Part Source Config

- `config_part_source.yaml` exposes an ordered `directories` list
- each entry may point either to a `parts` directory or to a parent directory that contains `parts`
- duplicate part ids use the first matching directory in the list
- `Reload Fast` and `Reload All` both pick up part source config changes
- full cache loads print a debug progress line with one `.` for every 100 loaded parts

## Form Config

- `config_form_base.yaml` is the default add-form config
- `config_form.yaml` overrides it whenever that file exists
- The default generic family exposes `taxonomy_1` through `taxonomy_15`
- The webserver now records raw validated form values and does not perform taxonomy mapping
