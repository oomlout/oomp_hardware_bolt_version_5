# Webserver Plan

## Goal

Build a Flask-based webserver that makes the generated `parts/` directory easy to explore and makes it easy to add new entries into `parts_source/` through a configurable form.

The first two user-facing features are:

1. An explore page for browsing parts with a search box that narrows results while typing.
2. An add-item page that writes a new `parts_source/<part_id>/working.yaml` entry using a single configuration point for form inputs and taxonomy mapping.

## Current Repo Understanding

- `parts_source/*/working.yaml` is the editable source of truth for part definitions.
- `working_oomp.py` loads `parts_source/` entries and produces/generated data under `parts/`.
- `working_oomp_populate.py` currently hardcodes source entries and is the best reference for the field shapes we need to create from the web form.
- `parts/*/working.yaml` contains rich generated metadata that will be useful for explore/search results.
- `webserver/` exists already and is currently empty, which makes it a good home for the new app.

## Guiding Decisions

- Keep the Flask app self-contained under `webserver/`.
- Use server-rendered templates first; add lightweight client-side JavaScript only for live filtering and form UX.
- Treat `parts_source/` as the write target and `parts/` as the browse target.
- Centralize add-form configuration in one Python structure so new part families can be added by editing one file.
- Prefer a small service layer over putting file/YAML logic directly in Flask routes.
- Keep the initial styling intentionally basic, but build the HTML/CSS structure so a fuller visual design can be layered on later without rewriting templates.
- Make the add flow generic from day one by leaning on `taxonomy_1`, `taxonomy_2`, and so on as the core navigation and identity model.
- Redirect `/` to `/explore` in the first version.
- Creating a part from the web UI should only write the source YAML entry.
- Generation should be available separately from the UI by launching `action_make_all.py`.
- Generation should launch in a separate background process using a visible Windows `cmd` popup window.
- The web app should not wait for generation to finish and should not track generation progress.
- Browse pages should directly serve and preview part files where useful.
- Load parts into an application cache at startup, and support incremental reload of only new or changed parts.

## Proposed Structure

```text
webserver/
  PLAN.md
  app.py
  config.py
  cache.py
  services/
    __init__.py
    parts_repository.py
    source_writer.py
    taxonomy_builder.py
    generation_runner.py
  templates/
    base.html
    explore.html
    add_item.html
    part_detail.html
  static/
    style.css
    explore.js
    add_item.js
```

## Styling Foundation

The first version should look simple and clean, but it should be easy to style out later.

Set up these foundations from the start:

- CSS custom properties for colors, spacing, radius, shadows, and type scale
- A predictable page structure with reusable wrappers like `site-header`, `page-shell`, `panel`, `toolbar`, `card-grid`, and `form-row`
- Consistent button, input, label, message, and card classes
- Template blocks in `base.html` for page title, head extras, and page-level scripts
- A small set of state classes for success, error, empty, selected, and loading UI
- Data attributes or semantic classes on search results and form fields so richer interactions can be added later without changing markup

This should let us start plain while keeping future redesign work mostly in CSS and templates rather than route logic.

## Caching And Reload Strategy

The app should avoid re-reading every part on every request.

Initial strategy:

- Load all parts into memory during app startup
- Track source file metadata such as path and last modified time
- Keep a normalized in-memory index for explore, detail pages, and navigation
- Support a fast reload that only reloads entries whose backing files are new or changed
- Support a full reload that rebuilds the entire cache from disk
- Expose reload actions in the web UI

Suggested implementation shape:

- `cache.py` owns the current in-memory snapshot
- `parts_repository.py` knows how to scan files and turn them into normalized part records
- A reload service compares timestamps or file signatures to decide what needs refreshing

This gives us fast browsing while keeping the data refreshable from the page itself.

## Single Configuration Point For Add Form

Create one config object in `webserver/config.py` that defines:

- Which form fields exist
- How each field is displayed
- Validation rules
- Whether the field is required
- How the field maps to output YAML
- How the field contributes to taxonomy labels
- Any default values

Example shape:

```python
PART_FORM_CONFIG = {
    "defaults": {
        "taxonomy_1": "organizing",
        "taxonomy_2": "electrical",
        "taxonomy_3": "wire",
    },
    "fields": [
        {
            "name": "part_type",
            "label": "Part Type",
            "input_type": "text",
            "required": True,
            "maps_to": "taxonomy_4",
            "transform": "slug",
        },
        {
            "name": "diameter",
            "label": "Diameter (mm)",
            "input_type": "number",
            "required": False,
            "maps_to": "taxonomy_5",
            "format": "{value}_mm_diameter",
            "also_store_raw": True,
        },
    ],
}
```

This config should drive both:

- The rendered HTML form
- The YAML payload written into `parts_source/`

## Phase Plan

### Phase 1: App Skeleton

Objective:
Create a runnable Flask app with a base layout and placeholder routes.

Tasks:

- [ ] Create `webserver/app.py`
- [ ] Add Flask app factory or simple app bootstrap
- [ ] Add routes for `/`, `/explore`, `/add`, `/parts/<part_id>`, `/reload/fast`, `/reload/all`, and generation controls
- [ ] Add template and static folder structure
- [ ] Add a minimal stylesheet so pages are usable immediately
- [ ] Add base template blocks and reusable layout/component classes for future styling expansion
- [ ] Define CSS variables and a basic design token section in `style.css`

Acceptance:

- Running the app starts a local Flask server
- `/` redirects to `/explore`
- `/explore` and `/add` render without errors
- Styling is still basic, but the structure supports later visual upgrades without template rewrites

### Phase 2: Read Model For Explore

Objective:
Load part data from `parts/` into a normalized structure for templates, search, and cached navigation.

Tasks:

- [ ] Build `parts_repository.py`
- [ ] Recursively or directly load `parts/*/working.yaml`
- [ ] Normalize values like `id`, `name`, `taxonomy_*`, preview image path, and directory path
- [ ] Gracefully skip malformed or partial entries
- [ ] Sort results consistently
- [ ] Build startup cache loading
- [ ] Track file modification metadata for incremental reload
- [ ] Build taxonomy-driven navigation structures from `taxonomy_*` values

Acceptance:

- Explore page can render a list of current parts
- Missing optional files like `3dpr.png` do not crash the page
- The initial cache is populated on startup
- A changed part can be identified for targeted reload

### Phase 3: Explore UI

Objective:
Make parts easy to browse and narrow down with live typing.

Tasks:

- [ ] Build explore template with search box and result cards/table
- [ ] Expose searchable text from name, id, taxonomy labels, and key metadata
- [ ] Add client-side filtering with JavaScript for instant narrowing
- [ ] Add basic empty-state messaging
- [ ] Add taxonomy-first navigation using `taxonomy_1`, `taxonomy_2`, and onward
- [ ] Add visible controls for `reload fast`, `reload all`, and `run generation`

Acceptance:

- Typing into the search box narrows visible results without a page reload
- Users can identify a part quickly from the listing
- Users can navigate by taxonomy structure as well as search

### Phase 4: Part Detail Page

Objective:
Allow drilling into one part from the explore view.

Tasks:

- [ ] Add `/parts/<part_id>` route
- [ ] Show key metadata from `parts/<part_id>/working.yaml`
- [ ] Show links/paths to generated files when present
- [ ] Show preview image if available
- [ ] Serve previewable files directly from Flask routes where appropriate

Acceptance:

- Clicking a part from explore opens a useful detail page
- Previewable assets can be viewed directly in the browser

### Phase 5: Config-Driven Add Form

Objective:
Replace hardcoded part-entry creation with a form generated from a single config.

Tasks:

- [ ] Create `config.py` for defaults and field definitions
- [ ] Render the add form from config rather than hardcoded HTML
- [ ] Support field types such as text, number, select, and checkbox if needed
- [ ] Validate required inputs server-side
- [ ] Keep config readable enough to extend later
- [ ] Design the config around generic taxonomy entry instead of one fixed part family

Acceptance:

- Adding or changing a field usually requires editing only the config
- The rendered form stays in sync with the output mapping
- The form can support multiple part families without route rewrites

### Phase 6: YAML Generation And Write Flow

Objective:
Submit the add form and write a correct new source entry under `parts_source/`.

Tasks:

- [ ] Build `taxonomy_builder.py` to convert form values into taxonomy labels
- [ ] Build `source_writer.py` to compose YAML payloads and folder names
- [ ] Generate the part id/folder name from taxonomy values
- [ ] Preserve blank taxonomy slots as needed for compatibility
- [ ] Write `working.yaml` into a new `parts_source/<part_id>/` directory
- [ ] Detect collisions and show a clear error if the entry already exists

Acceptance:

- Submitting the form creates a valid `parts_source/.../working.yaml`
- The output format matches current repo conventions closely enough for `working_oomp.py`

### Phase 7: Post-Create Workflow

Objective:
Support regeneration and data refresh from the UI without mixing it into source creation.

Tasks:

- [ ] Add a generation action that launches `action_make_all.py`
- [ ] Launch generation in a separate visible `cmd` window and return immediately
- [ ] Keep create-item submission separate from generation action
- [ ] Add a fast reload action that refreshes only changed or new parts in cache
- [ ] Add a full reload action that rebuilds the cache from disk
- [ ] Add user-facing success/error messaging around these actions

Acceptance:

- The user can create source YAML without triggering generation automatically
- The user can launch generation intentionally from the UI
- Launching generation opens a separate visible `cmd` window and does not block the web request
- The user can refresh cached browse data with fast or full reload controls

### Phase 8: Validation, Testing, And Polish

Objective:
Make the app durable enough for daily use.

Tasks:

- [ ] Add smoke tests for repository loading and source writing
- [ ] Add validation tests for taxonomy/id generation
- [ ] Add tests for cache refresh behavior
- [ ] Verify Windows path handling carefully
- [ ] Verify generation launching is safe and does not block or corrupt the UI flow
- [ ] Improve labels, help text, and error messages
- [ ] Document the styling structure so future UI work knows where tokens, layout classes, and component classes live
- [ ] Document how to run the app

Acceptance:

- Main flows work on this repo without manual patching
- The app is understandable to resume later

## Progress Tracker

Use this section as the live interruption-safe checklist during implementation.

### Overall Status

- [x] Planning complete
- [x] Phase 1 complete
- [x] Phase 2 complete
- [x] Phase 3 complete
- [x] Phase 4 complete
- [x] Phase 5 complete
- [x] Phase 6 complete
- [x] Phase 7 complete
- [x] Phase 8 complete

### Session Notes

- [x] 2026-04-27: Repo structure reviewed and initial plan created.
- [x] 2026-04-27: Flask app, cache layer, taxonomy navigation, add form, reload actions, file serving, and generation launcher implemented.
- [x] 2026-04-27: Added smoke tests plus real-repo route verification for explore, add, detail, and file serving paths.

## Risks And Watchouts

- `working_oomp_populate.py` shows patterns but may rely on helpers outside this repo, so the webserver should not depend on importing it directly for writes.
- `parts/` and `parts_source/` may temporarily diverge; the UI should make clear which side is being edited and which side is being browsed.
- Generated YAML in `parts/` contains much richer data than source YAML; we should avoid trying to write that larger structure back.
- Existing working tree changes mean we should keep webserver work isolated from current part-generation edits.

## Open Decisions To Confirm During Build

These are not blockers for starting implementation, but we should settle them as we go:

- Whether search should remain purely client-side or also gain server-side filtering once the dataset grows
- Whether fast reload should use file timestamps only or a stronger file-content signature

## Recommended Build Order

1. Phase 1: get Flask running
2. Phase 2: load parts, cache them, and build taxonomy navigation data
3. Phase 3: add live search and taxonomy browsing
4. Phase 5: add config-driven form rendering
5. Phase 6: add YAML writing
6. Phase 4: add part detail page and direct file preview
7. Phase 7 and 8: generation controls, reload controls, tests, and polish

## Definition Of Done

This project is done when:

- A Flask app runs locally from this repo
- `/explore` shows current parts from `parts/`
- `/` redirects to `/explore`
- Typing in the search box narrows results live
- Taxonomy navigation is driven by `taxonomy_*` fields
- `/add` renders from a single configuration point
- Submitting `/add` creates a valid `parts_source/<part_id>/working.yaml`
- The app caches loaded parts at startup
- The page exposes `reload fast`, `reload all`, and `run generation`
- Previewable generated files can be served directly
- The workflow is documented enough to pause and resume without re-discovery
