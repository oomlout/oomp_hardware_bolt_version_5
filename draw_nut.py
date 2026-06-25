"""
draw_nut.py  —  dimension-accurate M6 nut (top view) on a 50×50 mm page.

ISO 4032 M6 dimensions used:
  s      = 10.0 mm   width across flats (wrench size)
  e_min  = 11.05 mm  width across corners (circumradius × 2)
  d      = 6.0 mm    nominal thread / through-hole diameter
  dw_min = 8.9 mm    bearing-surface circle diameter

Output: draw_nut_output.svg
"""

import math
import opsvg
import svg_styles

# ── Page ──────────────────────────────────────────────────────────────────────
PAGE = 50.0  # mm square

# ── M6 nut  ISO 4032 ──────────────────────────────────────────────────────────
s       = 10.0   # across-flats (wrench size)
d_hole  = 6.0    # nominal thread diameter
dw_min  = 8.9    # bearing-surface diameter (min)

# Circumradius: R = (s/2) / cos(30°) = s / sqrt(3)
R = (s / 2) / math.cos(math.radians(30))

# Hexagon vertices — flat-top orientation (horizontal flats at top/bottom)
# Starting vertex at 30° so flat edges run left-right at the top and bottom.
hex_pts = [
    [R * math.cos(math.radians(30 + i * 60)),
     R * math.sin(math.radians(30 + i * 60))]
    for i in range(6)
]

# ── Build SVG ─────────────────────────────────────────────────────────────────
styles = svg_styles.get_stylesheet("project_bolt")

thing = {
    "svg_components": [],
    "styles": styles,
}

# 1. Page background — white fill, no border
opsvg.se(thing, shape="rect",
         color="#FFFFFF", stroke="none", stroke_width=0,
         size=[PAGE, PAGE, 0], pos=[0, 0, 0])

# 2. Hex nut body — plate fill + thick border
opsvg.se(thing, shape="polygon", style="plate",
         points=hex_pts, pos=[0, 0, 0])

# 3. Bearing-surface circle — outline only (dw_min)
opsvg.se(thing, shape="circle", style="outline",
         r=dw_min / 2, pos=[0, 0, 0])

# 4. Thread through-hole — white fill, thin dark border
opsvg.se(thing, shape="circle", style="hole.cut",
         r=d_hole / 2, pos=[0, 0, 0])

# 5. Title label — bottom of page
opsvg.se(thing, shape="text", style="label.title",
         text="M6 NUT", size=5.0,
         halign="center", valign="center",
         pos=[0, -(PAGE / 2 - 5), 0])

# ── Save ──────────────────────────────────────────────────────────────────────
opsvg.opsvg_make_object("draw_nut_output.svg", thing["svg_components"], padding=0)
