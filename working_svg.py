import copy
import math
import opsvg
import yaml
import os
import svg_help
import svg_styles


def _mm(v):
    """Format a mm value without spurious rounding: '5.5' not '6', '10' not '10.0'."""
    return f"{float(v):.0f}" if float(v) == int(float(v)) else f"{float(v):.1f}"


def main(**kwargs):
    make_svg(**kwargs)

def make_svg(**kwargs):
    typ = svg_help.get_typ(**kwargs)
    oomp_mode = "project"
    #oomp_mode = "oobb"
    filt = ""
    build_variables = svg_help.get_build_variables(typ, filter=filt)
    if True:
        kwargs["filter"] = build_variables["filter"]
        kwargs["save_type"] = build_variables["save_type"]
        kwargs["navigation"] = build_variables["navigation"]
        kwargs["overwrite"] = build_variables["overwrite"]
        kwargs["oomp_mode"] = oomp_mode
    parts = get_parts(kwargs, oomp_mode)

    kwargs["parts"] = parts

    svg_help.make_parts(**kwargs)

    if kwargs["navigation"]:
        oobb_style = False
        sort = svg_help.get_navigation_sort(oobb_style=oobb_style)
        svg_help.generate_navigation(sort=sort)


def get_parts(kwargs, oomp_mode):
    parts = []

    #load parts from parts/folder/working.yaml
    parts_directory = os.path.join(os.path.dirname(__file__), "parts")
    if not os.path.isdir(parts_directory):
        return parts

    for folder in os.listdir(parts_directory):
        folder_path = os.path.join(parts_directory, folder)
        if not os.path.isdir(folder_path):
            continue

        working_yaml_path = os.path.join(folder_path, "working.yaml")
        if not os.path.isfile(working_yaml_path):
            continue

        with open(working_yaml_path, "r", encoding="utf-8") as infile:
            loaded_part = yaml.safe_load(infile)

        if not isinstance(loaded_part, dict):
            continue

        svg_details_raw = loaded_part.get("svg_details")
        # Accept either a single dict or a list of dicts.
        if isinstance(svg_details_raw, list):
            # Use the first entry to derive kwargs / oobb_name; the full list
            # is kept intact in part["svg_details"] for make_svg_generic.
            svg_details = svg_details_raw[0] if svg_details_raw else {}
        elif isinstance(svg_details_raw, dict):
            svg_details = svg_details_raw
        else:
            continue  # no recognisable svg_details — skip

        part = loaded_part

        part_kwargs = copy.deepcopy(kwargs)
        part_kwargs.update(copy.deepcopy(loaded_part.get("kwargs", {})))
        _SD_META = {"svg_name", "filename_extra", "width", "height", "depth", "styles",
                    "extra", "radius_name"}
        svg_details_safe = {k: v for k, v in svg_details.items()
                            if k not in _SD_META or (k in ("width", "height", "depth") and isinstance(v, (int, float)))}
        part_kwargs.update(copy.deepcopy(svg_details_safe))

        # stylesheet name override from yaml: svg_details.stylesheet: "jazzy"
        if "stylesheet" in svg_details:
            part_kwargs["stylesheet"] = svg_details["stylesheet"]

        # per-part style overrides from yaml: svg_details.styles: {plate: {color: "#FF0000"}}
        yaml_styles = svg_details.get("styles", {})
        if isinstance(yaml_styles, dict) and yaml_styles:
            existing = part_kwargs.get("part_styles", {})
            part_kwargs["part_styles"] = svg_styles.merge(
                svg_styles.get_stylesheet(part_kwargs.get("stylesheet", "default")),
                {**existing, **yaml_styles}
            ) if not existing else {**existing, **yaml_styles}

        part["kwargs"] = part_kwargs
        part["oobb_name"] = part.get("oobb_name", svg_details.get("svg_name", "default"))

        if oomp_mode == "oobb":
            part["kwargs"]["oomp_size"] = part["oobb_name"]

        parts.append(part)

    return parts


def get_base(thing, **kwargs):

    prepare_print = kwargs.get("prepare_print", False)
    width = kwargs.get("width", 1)
    height = kwargs.get("height", 1)
    depth = kwargs.get("depth", 3)
    rot = kwargs.get("rot", [0,0,0])
    pos = kwargs.get("pos", [0,0,0])
    extra = kwargs.get("extra", "")



    #add plate
    if True:
        p3 = copy.deepcopy(kwargs)
        p3["shape"] = f"oobb_plate"
        p3["depth"] = depth
        #p3["m"] = "#"
        pos1 = copy.deepcopy(pos)
        p3["pos"] = pos1
        opsvg.se(thing,**p3)

    #add holes
    if True:
        p3 = copy.deepcopy(kwargs)
        p3["shape"] = f"oobb_holes"
        p3["depth"] = depth
        p3["radius_name"] = "m6"
        #p3["m"] = "#"
        pos1 = copy.deepcopy(pos)
        p3["pos"] = pos1
        opsvg.se(thing,**p3)

    #add text
    if True:
        p3 = copy.deepcopy(kwargs)
        p3["shape"] = f"text"
        p3["text"] = "Base Plate"
        p3["size"] = 10.0
        p3["font"] = "sans-serif"
        p3["halign"] = "left"
        p3["valign"] = "center"
        p3["color"] = "#000000"
        #p3["m"] = "#"
        pos1 = copy.deepcopy(pos)
        p3["pos"] = pos1
        opsvg.se(thing,**p3)

    if prepare_print:
        svg_help.prepare_base_for_print(thing, pos, **kwargs)


def get_nut(thing, **kwargs):
    """Icon: top view (hex + bore) on the left, side view (rect) on the right."""
    import svg_styles
    if not kwargs.get("stylesheet"):
        thing["styles"] = svg_styles.get_stylesheet("project_bolt")

    pos   = kwargs.get("pos", [0, 0, 0])
    s_mm  = float(thing.get("spec_iso_s_max_mm",  kwargs.get("svg_s_max_mm",  10.0)))
    m_mm  = float(thing.get("spec_iso_m_max_mm",  kwargs.get("svg_m_max_mm",   s_mm * 0.5)))
    nom   = thing.get("spec_iso_nominal_diameter", kwargs.get("svg_nominal_diameter", "M?"))
    try:
        d_hole = float(str(nom).lstrip("Mm"))
    except (ValueError, AttributeError):
        d_hole = s_mm * 0.6

    R   = (s_mm / 2) / math.cos(math.radians(30))
    gap = 2.0

    hex_pts = [
        [R * math.cos(math.radians(30 + i * 60)),
         R * math.sin(math.radians(30 + i * 60))]
        for i in range(6)
    ]

    # TOP VIEW (left): hex with through bore
    p_top = copy.deepcopy(pos)
    p_top[0] -= R + gap / 2
    opsvg.se(thing, shape="polygon", style="outline", points=hex_pts, pos=p_top)
    opsvg.se(thing, shape="circle", style="hole.cut", r=d_hole / 2, pos=p_top)

    # SIDE VIEW (right): outer rect (across corners) + bore rect + flat-face lines
    p_side = copy.deepcopy(pos)
    p_side[0] += R + gap / 2
    opsvg.se(thing, shape="rect", style="outline", size=[2 * R, m_mm, 0], pos=p_side)
    opsvg.se(thing, shape="rect", style="hole.cut", size=[d_hole, m_mm, 0], pos=p_side)
    for x_off in (-s_mm / 2, s_mm / 2):
        opsvg.se(thing, shape="line",
                 p1=[x_off, -m_mm / 2], p2=[x_off, m_mm / 2],
                 color="#AAAAAA", stroke_width=0.3, pos=p_side)


def get_bolt(thing, **kwargs):
    """Icon: end view (solid hex) on the left, side profile at 1:1 on the right.

    Side profile mirrors the mechanical drawing: head (full AF width) + grip
    (unthreaded shank) + threaded section, all at true mm dimensions.
    """
    import svg_styles
    if not kwargs.get("stylesheet"):
        thing["styles"] = svg_styles.get_stylesheet("project_bolt")

    _st = thing.get("styles", {})

    pos   = kwargs.get("pos", [0, 0, 0])
    s_mm  = float(thing.get("spec_iso_s_max_mm",  kwargs.get("svg_s_max_mm",  10.0)))
    k_mm  = float(thing.get("spec_iso_k_max_mm",  kwargs.get("svg_k_max_mm",   4.0)))
    nom   = thing.get("spec_iso_nominal_diameter", kwargs.get("svg_nominal_diameter", "M?"))
    try:
        d_hole = float(str(nom).lstrip("Mm"))
    except (ValueError, AttributeError):
        d_hole = s_mm * 0.6

    # Actual shank length from part id ("hardware_bolt_m6_25_mm_length" → 25.0)
    import re as _re
    _m = _re.search(r'_(\d+(?:\.\d+)?)_mm_length', str(thing.get("id", "")))
    shank_len = float(_m.group(1)) if _m else max(2.5 * k_mm, 0.8 * s_mm)

    # Thread length from spec data; fallback to full shank
    try:
        thread_len = float(kwargs.get("svg_b_l_le_125_mm") or
                           kwargs.get("svg_b_125_lt_l_le_200_mm") or
                           shank_len)
        thread_len = min(thread_len, shank_len)
    except (ValueError, TypeError):
        thread_len = shank_len
    grip_len = shank_len - thread_len

    R   = (s_mm / 2) / math.cos(math.radians(30))
    gap = 2.0

    hex_pts = [
        [R * math.cos(math.radians(30 + i * 60)),
         R * math.sin(math.radians(30 + i * 60))]
        for i in range(6)
    ]

    # END VIEW (left): solid hex — bolt head has no through bore
    p_end = copy.deepcopy(pos)
    p_end[0] -= R + gap / 2
    opsvg.se(thing, shape="polygon", style="outline", points=hex_pts, pos=p_end)

    # SIDE VIEW (right): head + grip + thread, total centred at pos[1]
    # With bolt head at top (positive Y-up) and shank hanging down.
    # Total height = k_mm + shank_len, centred at pos[1]:
    #   head centre  = pos[1] + shank_len/2
    #   grip centre  = pos[1] + shank_len/2 - k_mm - grip_len/2  (if grip_len > 0)
    #   thread centre = pos[1] - k_mm/2 - grip_len - thread_len/2
    p_side = copy.deepcopy(pos)
    p_side[0] += R + gap / 2

    # Head
    p_head = copy.deepcopy(p_side)
    p_head[1] += shank_len / 2
    opsvg.se(thing, shape="rect", style="outline", size=[2 * R, k_mm, 0], pos=p_head)
    for x_off in (-s_mm / 2, s_mm / 2):
        opsvg.se(thing, shape="line",
                 p1=[x_off, -k_mm / 2], p2=[x_off, k_mm / 2],
                 color="#AAAAAA", stroke_width=0.3, pos=p_head)

    # Grip (unthreaded shank)
    if grip_len > 0:
        grip_cy = shank_len / 2 - k_mm - grip_len / 2
        p_grip = copy.deepcopy(p_side)
        p_grip[1] += grip_cy
        opsvg.se(thing, shape="rect", style="outline", size=[d_hole, grip_len, 0], pos=p_grip)

    # Threaded section (lighter fill to match mech drawing)
    thread_cy = shank_len / 2 - k_mm - grip_len - thread_len / 2
    p_thread = copy.deepcopy(p_side)
    p_thread[1] += thread_cy
    plate_light = _st.get("plate.light", {}).get("color", "#F0F0F0")
    opsvg.se(thing, shape="rect",
             color=plate_light, stroke="#1A1A1A", stroke_width=0.5,
             size=[d_hole, thread_len, 0], pos=p_thread)


def get_set_screw(thing, **kwargs):
    get_bolt(thing, **kwargs)


def get_fill_in_the_blanks(thing, **kwargs):
    svg_help.get_fill_in_the_blanks(thing, **kwargs)


def get_a4_sheet(thing, **kwargs):
    svg_help.get_a4_sheet(thing, **kwargs)


def get_label_76x50(thing, **kwargs):
    svg_help.get_label_76x50(thing, **kwargs)


def _default_label_boxes():
    """Default 3 × 4 grid matching the Project Bolt tin insert photo.

    Top row is 0.5 units tall (narrow label strip);
    the three lower rows are each 1.0 units tall.
    Total: 3 wide × 3.5 high = 12 boxes.
    """
    boxes = []
    n = 1
    layout = [
        (0.0, 0.5),   # top narrow row
        (0.5, 1.0),
        (1.5, 1.0),
        (2.5, 1.0),
    ]
    for (row_y, row_h) in layout:
        for col in range(3):
            boxes.append({
                "x": float(col),
                "y": row_y,
                "w": 1.0,
                "h": row_h,
                "name": f"box_{n}",
            })
            n += 1
    return boxes


def get_internal_label_sheet(thing, **kwargs):
    """Proportional grid label sheet for tin inserts.

    No dark background — boxes sit directly on the card, separated by the
    card's own fill showing through the gap.  Corner radii are computed per
    corner so junctions and card edges look geometrically correct:

      r_inner  = gap_mm / 2   — inner corners: arc exactly fills the gap void
      r_outer  = card_r - card_margin_mm  — outer corners: parallel to card edge

    Parameters
    ----------
    unit_mm        : float  — physical size of one grid unit in mm   (default 42.0)
    grid_w         : float  — grid width in units                    (default 3.0)
    grid_h         : float  — grid height in units                   (default 3.5)
    card_margin_mm : float  — card fill visible around the grid      (default 2.0)
                              unit_mm=42, grid_w=3, margin=2 → card_w=130 mm
    card_r         : float  — card corner radius in mm               (default 8.0)
    gap_frac       : float  — gap between boxes as fraction of unit_mm (default 0.07)
    boxes          : list   — list of box dicts.  Each dict may contain:
                               x, y        — top-left position in units (required)
                               w, h        — size in units              (required)
                               name        — identifier string          (default "box_N")
                               text        — display text               (defaults to name)
                               style       — box fill style             (default "plate.cell")
                               text_style      — text style             (default "label")
                               text_size       — font size override mm  (default from style)
                               halign          — text alignment         (default "center";
                                                 auto "left" when lined)
                               valign          — vertical alignment     (default "center";
                                                 auto "top" when lined)
                               lined           — fill box with ruled    (default False)
                                                 lines for handwriting
                               line_spacing_mm — spacing between lines  (default 6.0 mm)
                               (any extra keys are preserved and ignored)
    stylesheet     : str    — stylesheet name                        (default "project_bolt")
    """
    prepare_print  = kwargs.get("prepare_print", False)
    pos            = kwargs.get("pos", [0, 0, 0])
    unit_mm        = float(kwargs.get("unit_mm",         42.0))
    grid_w         = float(kwargs.get("grid_w",           3.0))
    grid_h         = float(kwargs.get("grid_h",           3.5))
    card_margin_mm = float(kwargs.get("card_margin_mm",   2.0))
    card_r         = float(kwargs.get("card_r",           8.0))
    gap_frac       = float(kwargs.get("gap_frac",         0.07))
    boxes          = kwargs.get("boxes", _default_label_boxes())

    # ── Derived dimensions ────────────────────────────────────────────────────
    sheet_w  = grid_w * unit_mm                       # 126.0 mm
    sheet_h  = grid_h * unit_mm                       # 147.0 mm
    card_w   = sheet_w + 2 * card_margin_mm           # 130.0 mm
    card_h   = sheet_h + 2 * card_margin_mm           # 151.0 mm
    gap_mm   = gap_frac * unit_mm                     #   2.94 mm

    # Corner radius rules:
    #   inner: arc radius = gap/2 → arc exactly reaches the gap centreline,
    #          filling the void where four box corners meet
    #   outer: parallel to the card's own rounded corner
    r_inner  = gap_mm / 2
    r_outer  = max(card_r - card_margin_mm, 0.0)

    _EPS = 1e-3   # tolerance for edge-touching checks

    def _radii(bx, by, bw, bh):
        """Return (r_tl, r_tr, r_br, r_bl) for a box at grid position (bx,by)."""
        at_left   = bx              < _EPS
        at_top    = by              < _EPS
        at_right  = (bx + bw - grid_w) > -_EPS
        at_bottom = (by + bh - grid_h) > -_EPS
        tl = r_outer if (at_left  and at_top)    else r_inner
        tr = r_outer if (at_right and at_top)    else r_inner
        br = r_outer if (at_right and at_bottom) else r_inner
        bl = r_outer if (at_left  and at_bottom) else r_inner
        return tl, tr, br, bl

    # ── Stylesheet ────────────────────────────────────────────────────────────
    if "styles" not in thing or not thing.get("styles"):
        sheet_name = kwargs.get("stylesheet", "project_bolt")
        thing["styles"] = svg_styles.get_stylesheet(sheet_name)

    # ── Card fill (drawn first — border comes last) ───────────────────────────
    pos1 = copy.deepcopy(pos)
    opsvg.se(thing, shape="rounded_rectangle", style="plate",
             size=[card_w, card_h, 0], r=card_r, pos=pos1,
             stroke="none", stroke_width=0)

    # ── Boxes ─────────────────────────────────────────────────────────────────
    # Box centre in Y-up coords (origin = card centre = sheet centre):
    #   cx = -sheet_w/2 + unit_mm*(bx + bw/2)
    #   cy =  sheet_h/2 - unit_mm*(by + bh/2)
    # gap_mm cancels in the centre calculation; only affects w_mm / h_mm.
    for i, box in enumerate(boxes):
        bx         = float(box.get("x", 0))
        by         = float(box.get("y", 0))
        bw         = float(box.get("w", 1))
        bh         = float(box.get("h", 1))
        name       = box.get("name",       f"box_{i + 1}")
        text       = box.get("text",       name)
        box_style  = box.get("style",      "plate.cell")
        txt_style  = box.get("text_style", "label")
        txt_size   = box.get("text_size",  None)
        lined      = bool(box.get("lined", False))
        line_spc   = float(box.get("line_spacing_mm", 6.0))

        # lined boxes default to top-left anchored text; explicit values win
        halign = box.get("halign", "left"   if lined else "center")
        valign = box.get("valign", "top"    if lined else "center")

        w_mm = bw * unit_mm - gap_mm
        h_mm = bh * unit_mm - gap_mm
        cx   = -sheet_w / 2 + unit_mm * (bx + bw / 2)
        cy   =  sheet_h / 2 - unit_mm * (by + bh / 2)

        tl, tr, br, bl = _radii(bx, by, bw, bh)

        pos1    = copy.deepcopy(pos)
        pos1[0] += cx
        pos1[1] += cy

        # 1. Box fill
        opsvg.se(thing, shape="rrect_corners", style=box_style,
                 size=[w_mm, h_mm, 0],
                 r_tl=tl, r_tr=tr, r_br=br, r_bl=bl,
                 pos=pos1)

        # 2. Ruled lines (drawn before text so text sits on top)
        if lined:
            pad_x      = gap_mm * 1.5          # horizontal inset
            pad_y      = gap_mm                # top / bottom inset
            rule_w     = w_mm - 2 * pad_x
            rule_thick = 0.35
            y_from_top = pad_y + line_spc * 0.65   # first line
            while y_from_top + rule_thick / 2 < h_mm - pad_y:
                # Y-up offset from box centre: positive = up
                line_dy = h_mm / 2 - y_from_top
                lpos    = copy.deepcopy(pos)
                lpos[0] += cx
                lpos[1] += cy + line_dy
                opsvg.se(thing, shape="rect", style="rule",
                         size=[rule_w, rule_thick, 0], pos=lpos)
                y_from_top += line_spc

        # 3. Text — anchor point offset so halign/valign align to box edge
        padding = gap_mm
        off_x = {"left":  -(w_mm / 2 - padding),
                 "right":  (w_mm / 2 - padding),
                 "center": 0.0}.get(halign, 0.0)
        off_y = {"top":    (h_mm / 2 - padding),    # Y-up: positive = up
                 "bottom": -(h_mm / 2 - padding),
                 "center": 0.0}.get(valign, 0.0)

        txt_pos    = copy.deepcopy(pos)
        txt_pos[0] += cx + off_x
        txt_pos[1] += cy + off_y

        txt_kwargs = dict(halign=halign, valign=valign)
        if txt_size is not None:
            txt_kwargs["size"] = txt_size
        opsvg.se(thing, shape="text", style=txt_style,
                 text=text, pos=txt_pos, **txt_kwargs)

    # ── Card border (drawn last — on top of everything) ───────────────────────
    pos1 = copy.deepcopy(pos)
    opsvg.se(thing, shape="rounded_rectangle", style="plate.outline",
             size=[card_w, card_h, 0], r=card_r, pos=pos1)

    if prepare_print:
        svg_help.prepare_base_for_print(thing, pos, **kwargs)


def get_oomp_mech_drawing_hardware(thing, **kwargs):
    import svg_template

    hardware_type    = kwargs.get("hardware_type", "nut")
    id_mm            = float(kwargs.get("id_mm",            6.0))
    af_mm            = float(kwargs.get("af_mm",           10.0))
    height_mm        = float(kwargs.get("height_mm",        5.0))
    head_height_mm   = float(kwargs.get("head_height_mm",  height_mm))
    length_mm        = float(kwargs.get("length_mm",       height_mm))
    thread_length_mm = float(kwargs.get("thread_length_mm", length_mm))

    if hardware_type == "nut":
        summary_cols = [
            (f"M{id_mm:.0f}",           "THREAD"),
            (f"{_mm(af_mm)} mm",         "ACROSS FLATS"),
            (f"{height_mm:.1f} mm",     "NUT HEIGHT"),
        ]
    elif hardware_type in ("bolt", "set_screw"):
        summary_cols = [
            (f"M{id_mm:.0f}",               "THREAD"),
            (f"{_mm(af_mm)} mm",             "ACROSS FLATS"),
            (f"{head_height_mm:.1f} mm",    "HEAD HEIGHT"),
            (f"{length_mm:.0f} mm",         "SHANK LENGTH"),
            (f"{thread_length_mm:.0f} mm",  "THREAD LENGTH"),
        ]
    else:
        summary_cols = []

    svg_template.mech_drawing_page(thing, draw_fn=draw_item,
                                   summary_cols=summary_cols, **kwargs)


def draw_item(thing, **kwargs):
    hardware_type = kwargs.get("hardware_type", "nut")
    if hardware_type == "bolt":
        draw_bolt(thing, **kwargs)
    elif hardware_type == "set_screw":
        draw_set_screw(thing, **kwargs)
    else:
        draw_nut(thing, **kwargs)


def draw_nut(thing, **kwargs):
    """Top view + side view + dimension annotations for a hex nut."""
    front_cx     = kwargs["front_cx"]
    side_cx      = kwargs["side_cx"]
    view_cy      = kwargs["view_cy"]
    view_label_y = kwargs["view_label_y"]
    r_c_d        = kwargs["r_c_d"]
    af_d         = kwargs["af_d"]
    bore_r_d     = kwargs["bore_r_d"]
    height_d     = kwargs["height_d"]
    upper_vert_y = kwargs["upper_vert_y"]
    af_mm        = float(kwargs.get("af_mm",     10.0))
    id_mm        = float(kwargs.get("id_mm",      6.0))
    height_mm    = float(kwargs.get("height_mm",  5.0))

    _plate_c  = kwargs["_plate_c"]
    _plate_sk = kwargs["_plate_sk"]
    _plate_sw = kwargs["_plate_sw"]
    _cut_c    = kwargs["_cut_c"]
    _cut_sk   = kwargs["_cut_sk"]
    _cut_sw   = kwargs["_cut_sw"]
    _light_sk = kwargs["_light_sk"]
    _light_sw = kwargs["_light_sw"]
    _abs_pos  = kwargs["abs_pos_fn"]
    _text_at  = kwargs["text_at_fn"]
    _dim      = kwargs["dim_fn"]
    _hex_pts  = kwargs["hex_pts_fn"]

    e_d = 2 * r_c_d

    # View labels
    _text_at(front_cx, view_label_y, "TOP VIEW",  size=3.2, bold=True, muted=True)
    _text_at(side_cx,  view_label_y, "SIDE VIEW", size=3.2, bold=True, muted=True)

    # Top view: hex face with through bore
    fpos = _abs_pos(front_cx, view_cy)
    opsvg.se(thing, shape="polygon", points=_hex_pts(r_c_d),
             color=_plate_c, stroke=_plate_sk, stroke_width=_plate_sw, pos=fpos)
    opsvg.se(thing, shape="circle", r=bore_r_d,
             color=_cut_c, stroke=_cut_sk, stroke_width=_cut_sw, pos=fpos)

    # Side view: outer rect (across corners) + bore rect + flat-face indicator lines
    spos = _abs_pos(side_cx, view_cy)
    opsvg.se(thing, shape="rect", size=[e_d, height_d, 0],
             color=_plate_c, stroke=_plate_sk, stroke_width=_plate_sw, pos=spos)
    opsvg.se(thing, shape="rect", size=[bore_r_d * 2, height_d, 0],
             color=_cut_c, stroke=_cut_sk, stroke_width=_cut_sw, pos=spos)
    for x_off in (-af_d / 2, af_d / 2):
        opsvg.se(thing, shape="line",
                 p1=[x_off, -height_d / 2], p2=[x_off, height_d / 2],
                 color=_light_sk, stroke_width=_light_sw, pos=spos)

    # Dimension annotations
    _dim(front_cx, view_cy,
         p1=[-af_d / 2, upper_vert_y], p2=[af_d / 2, upper_vert_y],
         offset=upper_vert_y + 8, text=f"ACROSS FLATS  {_mm(af_mm)} mm",
         direction="horizontal")
    _dim(front_cx, view_cy,
         p1=[-bore_r_d, 0], p2=[bore_r_d, 0],
         offset=-(r_c_d + 8), text=f"THREAD BORE  Ø{id_mm:.0f} mm",
         direction="horizontal")
    _dim(side_cx, view_cy,
         p1=[-af_d / 2, height_d / 2], p2=[af_d / 2, height_d / 2],
         offset=8, text=f"ACROSS FLATS  {_mm(af_mm)} mm",
         direction="horizontal")
    _dim(side_cx, view_cy,
         p1=[af_d / 2, -height_d / 2], p2=[af_d / 2, height_d / 2],
         offset=8, text=f"NUT HEIGHT  {height_mm:.1f} mm",
         direction="vertical")


def draw_bolt(thing, **kwargs):
    """End view + tip view (left panel) + side view (right panel) for a hex bolt.

    Left panel stacks two views vertically:
      END VIEW  — looking at the bolt head from above (solid hex, no bore)
      TIP VIEW  — looking at the shank tip (circle = shank OD)
    Right panel:
      SIDE VIEW — full profile: head + grip + threaded shank
    """
    front_cx         = kwargs["front_cx"]
    side_cx          = kwargs["side_cx"]
    view_cy          = kwargs["view_cy"]
    view_label_y     = kwargs["view_label_y"]
    view_area_top    = kwargs["view_area_top"]
    view_area_bot    = kwargs["view_area_bot"]
    r_c_d            = kwargs["r_c_d"]
    af_d             = kwargs["af_d"]
    bore_r_d         = kwargs["bore_r_d"]
    upper_vert_y     = kwargs["upper_vert_y"]
    view_scale       = kwargs["view_scale"]
    ann_ts           = kwargs["ann_ts"]
    af_mm            = float(kwargs.get("af_mm",             10.0))
    id_mm            = float(kwargs.get("id_mm",              6.0))
    head_height_mm   = float(kwargs.get("head_height_mm",     4.0))
    length_mm        = float(kwargs.get("length_mm",         16.0))
    thread_length_mm = float(kwargs.get("thread_length_mm", length_mm))

    _plate_c  = kwargs["_plate_c"]
    _plate_sk = kwargs["_plate_sk"]
    _plate_sw = kwargs["_plate_sw"]
    _dim_sk   = kwargs["_dim_sk"]
    _dim_sw   = kwargs["_dim_sw"]
    _light_sk = kwargs["_light_sk"]
    _light_sw = kwargs["_light_sw"]
    _abs_pos  = kwargs["abs_pos_fn"]
    _text_at  = kwargs["text_at_fn"]
    _dim      = kwargs["dim_fn"]
    _hex_pts  = kwargs["hex_pts_fn"]

    _st = thing.get("styles", {})
    _plate_light = _st.get("plate.light", {}).get("color", "#F0F0F0")

    e_d = 2 * r_c_d

    # ── View labels ───────────────────────────────────────────────────────────
    _text_at(front_cx, view_label_y, "END VIEW",  size=3.2, bold=True, muted=True)
    _text_at(side_cx,  view_label_y, "SIDE VIEW", size=3.2, bold=True, muted=True)

    # ── Left panel layout: stack END VIEW and TIP VIEW ────────────────────────
    above_end = upper_vert_y + 8 + ann_ts + 3   # space from end_cy to top of end dim
    below_end = r_c_d + 8 + ann_ts + 3          # space from end_cy to bottom of end dim
    above_tip = bore_r_d + 5                    # space from tip_cy to tip label
    below_tip = bore_r_d + ann_ts + 8           # space from tip_cy to bottom of tip dim
    gap       = 8.0                             # gap between end dim bottom and tip label

    total_h   = above_end + below_end + gap + above_tip + below_tip
    block_top = (view_area_top + view_area_bot) / 2 + total_h / 2
    end_cy    = block_top - above_end
    tip_cy    = end_cy - below_end - gap - above_tip

    # END VIEW: hex head only — bolt head is solid, no through bore
    fpos = _abs_pos(front_cx, end_cy)
    opsvg.se(thing, shape="polygon", points=_hex_pts(r_c_d),
             color=_plate_c, stroke=_plate_sk, stroke_width=_plate_sw, pos=fpos)
    _dim(front_cx, end_cy,
         p1=[-af_d / 2, upper_vert_y], p2=[af_d / 2, upper_vert_y],
         offset=upper_vert_y + 8, text=f"ACROSS FLATS  {_mm(af_mm)} mm",
         direction="horizontal")

    # TIP VIEW label (sits in the gap between the two views)
    tip_label_y = end_cy - below_end - 3
    _text_at(front_cx, tip_label_y, "TIP VIEW", size=3.2, bold=True, muted=True)

    # TIP VIEW: shank cross-section — solid circle = shank OD
    tpos = _abs_pos(front_cx, tip_cy)
    opsvg.se(thing, shape="circle", r=bore_r_d,
             color=_plate_c, stroke=_plate_sk, stroke_width=_plate_sw, pos=tpos)
    _dim(front_cx, tip_cy,
         p1=[-bore_r_d, 0], p2=[bore_r_d, 0],
         offset=-(bore_r_d + 6), text=f"Ø{id_mm:.0f} mm",
         direction="horizontal")

    # ── Right panel: SIDE VIEW ────────────────────────────────────────────────
    head_d    = head_height_mm * view_scale
    shank_d   = length_mm * view_scale
    total_d   = head_d + shank_d
    top_y     = view_cy + total_d / 2
    bear_y    = top_y - head_d
    bot_y     = top_y - total_d
    thread_d  = thread_length_mm * view_scale
    grip_d    = shank_d - thread_d
    grip_cy   = bear_y - grip_d / 2
    thread_cy = bot_y + thread_d / 2
    origin    = _abs_pos(side_cx, 0)

    # Head
    opsvg.se(thing, shape="rect", size=[e_d, head_d, 0],
             color=_plate_c, stroke=_plate_sk, stroke_width=_plate_sw,
             pos=_abs_pos(side_cx, (top_y + bear_y) / 2))
    for x_off in (-af_d / 2, af_d / 2):
        opsvg.se(thing, shape="line",
                 p1=[x_off, bear_y], p2=[x_off, top_y],
                 color=_light_sk, stroke_width=_light_sw, pos=origin)
    # Grip (unthreaded shank)
    if grip_d > 0:
        opsvg.se(thing, shape="rect", size=[bore_r_d * 2, grip_d, 0],
                 color=_plate_c, stroke=_plate_sk, stroke_width=_plate_sw,
                 pos=_abs_pos(side_cx, grip_cy))
    # Threaded section
    opsvg.se(thing, shape="rect", size=[bore_r_d * 2, thread_d, 0],
             color=_plate_light, stroke=_plate_sk, stroke_width=_plate_sw,
             pos=_abs_pos(side_cx, thread_cy))

    # Side view dimension annotations
    _dim(side_cx, 0,
         p1=[-af_d / 2, top_y], p2=[af_d / 2, top_y],
         offset=8, text=f"ACROSS FLATS  {_mm(af_mm)} mm",
         direction="horizontal")

    # HEAD HEIGHT: manual bracket so label stays horizontal
    _gap2 = 1.5;  _ovr = 1.5;  _tick = 1.5
    _bx   = side_cx - r_c_d - 8
    _dpos = _abs_pos(0, 0)
    for _ey in (bear_y, top_y):
        opsvg.se(thing, shape="line",
                 p1=[side_cx - r_c_d - _gap2, _ey], p2=[_bx - _ovr, _ey],
                 color=_dim_sk, stroke_width=_dim_sw, pos=_dpos)
        opsvg.se(thing, shape="line",
                 p1=[_bx - _tick, _ey], p2=[_bx + _tick, _ey],
                 color=_dim_sk, stroke_width=_dim_sw, pos=_dpos)
    opsvg.se(thing, shape="line",
             p1=[_bx, bear_y], p2=[_bx, top_y],
             color=_dim_sk, stroke_width=_dim_sw, pos=_dpos)
    _text_at(_bx - _tick - 2, (top_y + bear_y) / 2,
             f"HEAD HEIGHT  {head_height_mm:.1f} mm",
             size=ann_ts, halign="right")

    _dim(side_cx, 0,
         p1=[r_c_d, bot_y], p2=[r_c_d, bear_y],
         offset=8, text=f"SHANK LENGTH  {length_mm:.0f} mm",
         direction="vertical")
    _dim(side_cx, 0,
         p1=[-bore_r_d, bot_y], p2=[-bore_r_d, bot_y + thread_d],
         offset=-(r_c_d - bore_r_d + 8), text=f"THREAD LENGTH  {thread_length_mm:.0f} mm",
         direction="vertical")


def draw_set_screw(thing, **kwargs):
    draw_bolt(thing, **kwargs)


if __name__ == '__main__':
    kwargs = {}
    main(**kwargs)
