# Webserver Redesign Plan

## Goal

Redesign the current Flask webserver to feel modern, bright, colorful, and high density, with a strong emphasis on fast scanning for the explore page.

The main experience change is:

1. Replace the current tile/card-heavy explore results with a long horizontal list layout.
2. Keep taxonomy-first navigation, but make it denser and more expressive.
3. Add a YAML config file that controls the priority order for which image/file should be used as the primary preview.

## Archive

- Previous implementation plan archived to `webserver/old_plan.md`.

## Redesign Intent

This redesign should feel closer to a modern resource index or power-user inventory browser than a gallery.

Visual direction:

- Bright and colorful rather than muted and minimal
- Dense and efficient rather than spacious and card-heavy
- Structured for scanning, with strong alignment and repeated row rhythm
- Expressive enough to feel designed, but still practical for lots of parts

Interaction direction:

- Explore page should prioritize quick recognition over large previews
- Taxonomy context should stay visible and useful at all times
- Search, reload, and generation actions should be compact and always accessible
- The row layout should support progressively richer metadata without needing a future rewrite

## Research Notes

Research reviewed on 2026-04-27:

- Shopify Polaris resource index pattern emphasizes a resource-focused index layout, persistent primary actions in the top right, and an index structure meant for management-style scanning.
- Material Design lists guidance recommends continuous vertical lists for homogeneous content, and explicitly supports condensed measurements for mouse-and-keyboard desktop contexts.
- Material Design data tables guidance supports row hover, top/bottom manipulation controls, and enterprise-style dense data browsing.
- Algolia's search UX density guidance argues for progressive disclosure and against redundant repeated metadata in every result row.

Implications for this redesign:

- Use a continuous row list instead of tiled cards on the explore page.
- Keep the main create/generation/reload actions compact and visible near the top.
- Show only the most useful metadata in each row, with redundancy removed when taxonomy context already makes something obvious.
- Make the row structure modular so future density modes or optional columns can be added later.

## Current Touch Points

The redesign will primarily affect:

- `webserver/templates/base.html`
- `webserver/templates/explore.html`
- `webserver/templates/part_detail.html`
- `webserver/static/style.css`
- `webserver/static/explore.js`
- `webserver/services/parts_repository.py`
- `webserver/app.py`

New planned config and support files:

- `webserver/ui_config.yaml`
- `webserver/services/ui_config.py`

## Explore Page Redesign

### New Layout Direction

Change explore results from cards into dense horizontal rows.

Each part row should have a consistent structure like:

1. Small preview image area
2. Primary identity block
3. Taxonomy path block
4. Supporting metadata block
5. Quick actions block

Example content balance:

- Preview: small square or short landscape thumbnail
- Identity: part name, part id, maybe one short descriptor
- Taxonomy: compact breadcrumb or stacked taxonomy chips
- Metadata: file count, available preview types, maybe source/generated status later
- Actions: open detail, open preview, open folder/file links if useful

### Why Long Rows

Long rows are a better fit here because:

- The data is homogeneous
- Users are likely scanning many similar parts
- The taxonomy structure matters more than large artwork
- Dense rows let us show more items above the fold

### Density Targets

Desktop-first density goals:

- Reduce row height compared with the current card layout
- Keep enough spacing for clarity, but avoid oversized padding
- Make the search bar and action controls compact
- Aim for "many useful parts visible immediately" rather than "few beautiful cards"

Mobile behavior:

- Keep the same information hierarchy
- Collapse lower-priority columns beneath the primary identity block
- Preserve row-based browsing rather than switching back to big cards

## Color And Styling Direction

The redesign should move away from soft neutral panels toward a more vivid system.

Planned styling characteristics:

- Bright accent palette with stronger hue separation
- Colored taxonomy chips and taxonomy section backgrounds
- More contrast between toolbar, results, and preview areas
- Tighter typography scale for dense scanning
- Stronger hover and active states for rows
- Subtle visual structure using borders, stripes, section fills, and badges rather than large white cards everywhere

Planned CSS structure upgrades:

- Expand design tokens beyond the current base colors
- Add semantic tokens for taxonomy, status, hover, row striping, and badge colors
- Create reusable row/list classes instead of card-grid-first classes
- Split page shell styling from result-list styling

## Taxonomy Navigation Redesign

The taxonomy navigation should become denser and more obviously useful.

Planned changes:

- Convert the taxonomy branch selector into a compact horizontal navigation band
- Keep selected taxonomy context pinned near the search bar
- Show counts per taxonomy option more clearly
- Color-code taxonomy depth or taxonomy family where it helps scanning
- Reduce visual repetition between taxonomy navigation and taxonomy shown in each row

## Image Priority Config

Add a YAML config file that defines the ordered priority of images/files used as the main preview.

Proposed file:

- `webserver/ui_config.yaml`

Proposed structure:

```yaml
preview_priority:
  - 3dpr.png
  - 3dpr.jpg
  - 3dpr.webp
  - label_oomp.svg
  - initial_generated_icon.png
  - "*.png"
  - "*.svg"
  - "*.jpg"
```

Planned behavior:

- The repository loader reads this config at startup
- Preview selection uses the ordered array from the YAML file
- Exact filenames should win before wildcard patterns
- If no configured preview matches, the current fallback logic can choose the first image-like file
- The same config can later grow to control alternate preview slots or detail-page image galleries

This needs to be accessible and editable without touching Python code.

## Data And Service Changes

### `parts_repository.py`

Planned changes:

- Replace hardcoded preview preference logic with config-driven preview resolution
- Add fields for row display such as:
  - primary preview URL candidate
  - file counts
  - taxonomy breadcrumb text
  - compact metadata labels
- Keep cached record shape stable enough that template redesign stays simple

### `app.py`

Planned changes:

- Load `ui_config.yaml` during app startup
- Expose UI config-derived preview behavior to the cache/repository layer
- Keep route behavior stable while updating the template data shape where needed

### New `ui_config.py`

Responsibilities:

- Load YAML config safely
- Provide defaults if config is missing or partial
- Validate preview priority structure
- Return normalized patterns for repository use

## Proposed Implementation Phases

### Phase 1: Archive And Design Prep

Objective:
Preserve the current plan and establish the redesign planning baseline.

Tasks:

- [x] Move current plan to `old_plan.md`
- [x] Create this new redesign plan with progress tracking
- [ ] Capture final visual requirements in one place

Acceptance:

- Old implementation plan is preserved
- New redesign plan is the current active plan

### Phase 2: UI Config Foundation

Objective:
Introduce a YAML-based UI config for preview image hierarchy.

Tasks:

- [ ] Add `webserver/ui_config.yaml`
- [ ] Add `webserver/services/ui_config.py`
- [ ] Define default `preview_priority` behavior
- [ ] Validate config loading and fallback behavior

Acceptance:

- Preview priority can be changed without editing Python source
- Missing config does not break the app

### Phase 3: Preview Selection Integration

Objective:
Use the new YAML config to choose the main part preview.

Tasks:

- [ ] Refactor preview selection in `parts_repository.py`
- [ ] Support exact filenames and wildcard patterns
- [ ] Add normalized preview metadata to cached records
- [ ] Add tests for preview selection priority

Acceptance:

- Main preview follows the configured hierarchy
- Cache reload picks up new preview choices after config or file changes

### Phase 4: Explore Layout Redesign

Objective:
Replace tile-based browsing with a dense row-based index.

Tasks:

- [ ] Redesign `explore.html` around a continuous results list
- [ ] Replace the card grid with row items
- [ ] Keep inline preview, name, taxonomy, metadata, and actions aligned
- [ ] Preserve live search behavior
- [ ] Preserve taxonomy filtering behavior

Acceptance:

- Explore page uses long horizontal rows instead of tiles
- Users can scan more parts at once than before

### Phase 5: Bright High-Density Visual System

Objective:
Create a vivid, practical design language for the explore experience.

Tasks:

- [ ] Redesign `style.css` tokens for stronger color and density
- [ ] Add row hover, active, selected, and striped states
- [ ] Add more expressive badge/chip styles
- [ ] Tighten toolbar, search, and panel spacing
- [ ] Improve typography hierarchy for dense scanning

Acceptance:

- The app feels brighter, more modern, and more intentional
- Density improves without making the interface feel chaotic

### Phase 6: Taxonomy Navigation Refresh

Objective:
Make taxonomy browsing feel like a first-class dense control surface.

Tasks:

- [ ] Redesign taxonomy branch navigation as a compact control band
- [ ] Improve breadcrumb clarity
- [ ] Reduce duplicated taxonomy display in result rows where possible
- [ ] Make counts and selected state easier to scan

Acceptance:

- Taxonomy navigation is compact, clear, and visually integrated with search

### Phase 7: Detail Page Alignment

Objective:
Bring the detail page into the same visual system.

Tasks:

- [ ] Update `part_detail.html` to match the new color/density system
- [ ] Use the same preview priority logic there
- [ ] Improve file list presentation

Acceptance:

- Detail page feels like the same product as explore

### Phase 8: Verification And Polish

Objective:
Make sure the redesign is durable and easy to iterate on.

Tasks:

- [ ] Add or update tests for UI config and preview selection
- [ ] Smoke-test explore and detail routes with real repo data
- [ ] Verify dense layout behavior on smaller screens
- [ ] Document the new UI config in README if needed

Acceptance:

- Redesign is stable
- Preview priority config is documented

## Progress Tracker

### Overall Status

- [x] Redesign planning complete
- [x] Previous plan archived
- [x] Phase 2 complete
- [x] Phase 3 complete
- [x] Phase 4 complete
- [x] Phase 5 complete
- [x] Phase 6 complete
- [x] Phase 7 complete
- [x] Phase 8 complete

### Session Notes

- [x] 2026-04-27: Reviewed current webserver implementation and archived the previous build plan to `old_plan.md`.
- [x] 2026-04-27: Researched dense list/index patterns and wrote the redesign plan.
- [x] 2026-04-27: Added `ui_config.yaml` plus preview-priority loading and validation support.
- [x] 2026-04-27: Reworked explore into a dense horizontal row layout with brighter styling and compact taxonomy navigation.
- [x] 2026-04-27: Updated detail page styling, added preview-priority tests, and verified routes with real repo data.

## Risks And Watchouts

- A denser layout can become visually noisy if too many metadata fields compete in each row.
- Bright colors need to be structured carefully so taxonomy color helps scanning instead of turning into confetti.
- Wildcard preview rules in YAML need deterministic matching behavior.
- Real repo data may include inconsistent image naming, so preview fallback rules need to be forgiving.
- Mobile collapse behavior should preserve density principles rather than reverting to oversized cards.

## Definition Of Done

This redesign is done when:

- Explore results use dense horizontal rows instead of tiles
- The interface feels noticeably brighter and more colorful
- Taxonomy navigation remains the primary browse model
- Preview image selection is controlled by an array in a YAML config file
- Preview priority works consistently on both explore and detail pages
- The redesign is documented well enough to pause and resume safely

## References

- Shopify Polaris resource index layout: https://polaris-react.shopify.com/patterns/resource-index-layout
- Material Design lists: https://m1.material.io/components/lists.html
- Material Design data tables: https://m1.material.io/components/data-tables.html
- Algolia on information density and progressive disclosure in search UX: https://www.algolia.com/blog/ux/information-density-and-progressive-disclosure-search-ux

