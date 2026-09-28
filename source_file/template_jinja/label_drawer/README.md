# Drawer label

`working.svg.j2` produces `parts/<part>/label_drawer.svg` at **38.1 × 25.4 mm**
(1.5 × 1 inch). The viewBox uses millimetres. Print at **100% / actual size**.

The label has a white hardware diagram on black at top left and a bold white
thread size on black below it. The right side has the bold type description at
the top, a large length with an explicit `mm` suffix beneath it, and secondary
details at the bottom.
There are no type abbreviations or TYPE / THREAD / LENGTH captions. Lengths
are in millimetres; nuts and washers omit the length. Diagrams are symbolic
SVG vectors, not dimensioned drawings. Bolt and set-screw diagrams distinguish
partial and full threads; screw diagrams reflect the head style. There are no
raster images, grey fills or gradients.

From either project, run `action_make_label_overwrite.bat` to regenerate every
drawer label in that project, update its roboclick action, and delete stale
`label*.png` renders under each part (including nested render folders).
Other PNG artwork and other SVG/PDF labels are preserved. The batch can be
launched from any working directory and returns a nonzero status on failure.

The batch uses Python with PyYAML, Jinja2 and Pillow, plus Arial (Windows) or
Liberation Sans for measuring text. It does not require the OOMP libraries,
CorelDRAW, Inkscape, AI calls or CAD generation.

`working_oomp.py` registers the same `text_jinja_template` roboclick action
through `working_label_drawer.add_action`. Its empty `file_test` ensures the
SVG is refreshed each run; PNG and PDF conversions are disabled. Re-run the
batch or `working_oomp.py` when taxonomy data changes to refresh layout data.

Both projects contain identical copies of the template, helper, batch and tests.
Apply future design changes to both copies. Text stays editable; SVG rendering
uses Arial with a Liberation Sans fallback. Long text is measured and wrapped
without stretching, clipping, ellipses or discarded words.
