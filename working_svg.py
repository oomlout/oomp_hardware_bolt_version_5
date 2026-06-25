import copy
import math
import opsvg
import yaml
import os
import svg_help
import svg_styles


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
    # Spec fields live as top-level keys in `thing` (written by working_oomp.py):
    #   spec_iso_s_max_mm          — width across flats (wrench size)
    #   spec_iso_dw_min_mm         — bearing-surface diameter
    #   spec_iso_nominal_diameter  — e.g. "M6"
    # svg_* kwargs are the legacy fallback (from parts_source svg_details).
    import math
    import svg_styles

    prepare_print = kwargs.get("prepare_print", False)
    pos = kwargs.get("pos", [0, 0, 0])

    # ── Stylesheet ────────────────────────────────────────────────────────────
    if not kwargs.get("stylesheet"):
        thing["styles"] = svg_styles.get_stylesheet("project_bolt")

    # ── Specs ─────────────────────────────────────────────────────────────────
    s_mm  = float(thing.get("spec_iso_s_max_mm",  kwargs.get("svg_s_max_mm",  10.0)))
    dw_mm = float(thing.get("spec_iso_dw_min_mm", kwargs.get("svg_dw_min_mm",  8.9)))
    nom   = thing.get("spec_iso_nominal_diameter", kwargs.get("svg_nominal_diameter", "M?"))
    try:
        d_hole = float(str(nom).lstrip("Mm"))          # thread diameter in mm
    except (ValueError, AttributeError):
        d_hole = s_mm * 0.6

    # ── Derived geometry ──────────────────────────────────────────────────────
    # Circumradius: R = (s/2) / cos(30°)
    R = (s_mm / 2) / math.cos(math.radians(30))

    # Flat-top hex: first vertex at 30° so flat edges run left-right
    hex_pts = [
        [R * math.cos(math.radians(30 + i * 60)),
         R * math.sin(math.radians(30 + i * 60))]
        for i in range(6)
    ]

    # ── Page background ───────────────────────────────────────────────────────
    # page = max(40.0, R * 9.0)

    # opsvg.se(thing, shape="rect",
    #          color="#FFFFFF", stroke="none", stroke_width=0,
    #          size=[page, page, 0], pos=copy.deepcopy(pos))

    # ── Hex nut body ──────────────────────────────────────────────────────────
    opsvg.se(thing, shape="polygon", style="outline",
             points=hex_pts, pos=copy.deepcopy(pos))

    # ── Bearing-surface circle (outline only) ─────────────────────────────────
    #opsvg.se(thing, shape="circle", style="outline",
    #         r=dw_mm / 2, pos=copy.deepcopy(pos))

    # ── Thread through-hole ───────────────────────────────────────────────────
    opsvg.se(thing, shape="circle", style="hole.cut",
             r=d_hole / 2, pos=copy.deepcopy(pos))

    # ── Nominal diameter label ────────────────────────────────────────────────
    # label_pos = copy.deepcopy(pos)
    # label_pos[1] -= (page / 2 - 5)
    # opsvg.se(thing, shape="text", style="label.title",
    #          text=nom, size=5.0,
    #          halign="center", valign="center", pos=label_pos)
    # if prepare_print:
    #     svg_help.prepare_base_for_print(thing, pos, **kwargs)


def get_bolt(thing, **kwargs):
    import svg_styles
    if not kwargs.get("stylesheet"):
        thing["styles"] = svg_styles.get_stylesheet("project_bolt")
    s_mm  = float(thing.get("spec_iso_s_max_mm",  kwargs.get("svg_s_max_mm",  10.0)))
    k_mm  = float(thing.get("spec_iso_k_max_mm",  kwargs.get("svg_k_max_mm",   4.0)))
    nom   = thing.get("spec_iso_nominal_diameter", kwargs.get("svg_nominal_diameter", "M?"))
    try:
        d_hole = float(str(nom).lstrip("Mm"))
    except (ValueError, AttributeError):
        d_hole = s_mm * 0.6
    R = (s_mm / 2) / math.cos(math.radians(30))
    hex_pts = [
        [R * math.cos(math.radians(30 + i * 60)),
         R * math.sin(math.radians(30 + i * 60))]
        for i in range(6)
    ]
    pos = kwargs.get("pos", [0, 0, 0])
    opsvg.se(thing, shape="polygon", style="outline",
             points=hex_pts, pos=copy.deepcopy(pos))
    opsvg.se(thing, shape="circle", style="hole.cut",
             r=d_hole / 2, pos=copy.deepcopy(pos))


def get_set_screw(thing, **kwargs):
    # Full-thread hex head screw — same head geometry as bolt
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
    """A4 mechanical drawing sheet for hardware fasteners (nuts, bolts, washers).

    All views are rendered at view_scale : 1.  Dimension annotations call out
    the true mm values.  Designed as a template — hardware_type selects the
    correct front/side view geometry.

    kwargs (set via svg_details in working.yaml)
    --------------------------------------------
    hardware_type  : 'nut' | 'bolt' | 'washer'   (default 'nut')
    part_title     : str   large identifier, e.g. 'M6'
    part_series    : str   series/spec,      e.g. 'METRIC HEX NUT'
    part_category  : str   header category,  e.g. 'HARDWARE / NUT'
    id_mm          : float inner diameter (thread bore), mm   (default 6.0)
    af_mm          : float across-flats width, mm             (default 10.0)
    height_mm      : float thickness / height, mm             (default 5.0)
    part_code      : str   standard code, e.g. 'ISO4032 / DIN934'
    part_name      : str   full part identifier string
    view_scale     : float drawing scale (auto if None → targets ~46 mm AF span)
    """
    pos             = kwargs.get("pos",             [0, 0, 0])
    hardware_type   = kwargs.get("hardware_type",   "nut")
    part_title      = str(kwargs.get("part_title",      "M6"))
    part_id = thing.get("id", "")
    part_series     = str(kwargs.get("part_series",     "METRIC HEX NUT"))
    part_category   = str(kwargs.get("part_category",   "HARDWARE / NUT"))
    id_mm           = float(kwargs.get("id_mm",       6.0))
    af_mm           = float(kwargs.get("af_mm",      10.0))
    height_mm       = float(kwargs.get("height_mm",   5.0))
    head_height_mm   = float(kwargs.get("head_height_mm",  height_mm))
    length_mm        = float(kwargs.get("length_mm",      height_mm))
    thread_length_mm = float(kwargs.get("thread_length_mm", length_mm))
    part_code       = str(kwargs.get("part_code",      ""))
    part_name       = str(kwargs.get("part_name",      ""))
    view_scale      = kwargs.get("view_scale", None)

    W, H = 210.0, 297.0

    brand_y      =  H / 2 - 14.0
    title_y      =  H / 2 - 40.0 + 3
    part_name_y  =  H / 2 - 57.0 + 8
    series_y     =  H / 2 - 67.0
    rule1_y      =  H / 2 - 76.0
    dim_head_y   =  H / 2 - 83.0
    view_label_y =  H / 2 - 97.0
    rule2_y      = -H / 2 + 72.0

    # Auto-scale: fit views between view_label_y and rule2_y, whole number.
    # Front view vertical height = label_gap(10) + dim_above(r_c_d/2+15) +
    #                              hex_height(2*r_c_d) + bore_dim(r_c_d+12) = 37 + 3.5*r_c_d
    # Side view for bolt = AF_dim_above(15) + total_bolt_height(scale*(L+k)) + margin(10)
    # Width: front hex must fit in left half-page.
    if view_scale is None:
        r_c   = af_mm / math.sqrt(3)
        avail = view_label_y - rule2_y          # available height for views
        # Front-view overhead: label_gap(10) + dim_above(r_c/2+15) + hex(2r_c) + bore_dim(r_c+12)
        scale_front = (avail - 37.0) / (3.5 * r_c)
        if hardware_type == "nut":
            scale_side = scale_front
        else:
            # Bolt side overhead: AF dim above(15) + total bolt(L+k) + length dim below(15)
            total_mm = length_mm + head_height_mm
            scale_side = (avail - 30.0) / total_mm
        scale_w = (W / 4.0 - 10.0) / r_c
        s_raw = min(scale_front, scale_side, scale_w)
        view_scale = max(1, int(s_raw)) if s_raw >= 1.0 else 0.5

    r_c_d    = (af_mm / math.sqrt(3)) * view_scale
    af_d     = af_mm * view_scale
    bore_r_d = (id_mm / 2.0) * view_scale
    height_d = height_mm * view_scale
    upper_vert_y = r_c_d / 2
    ann_ts = 3.8   # dimension text size (mm) — used in centring calc below

    # Centre the view block vertically between view_label_y and rule2_y.
    # Height above view_cy: dim_above + hex/bolt-top
    # Height below view_cy: hex/bolt-bottom + dim_below
    if hardware_type == "nut":
        above_vc = upper_vert_y + 8 + ann_ts + 3   # AF dim + gap
        below_vc = r_c_d + 8 + ann_ts + 3          # bore dim below hex
    else:
        total_d_raw = (length_mm + head_height_mm) * view_scale
        above_vc = total_d_raw / 2 + 15            # top of bolt + AF dim above
        below_vc = total_d_raw / 2 + 15            # bottom of bolt + length dim below

    content_top = view_label_y - 8   # just below the view label text
    content_bot = rule2_y
    content_mid = (content_top + content_bot) / 2
    view_cy = content_mid + (below_vc - above_vc) / 2

    front_cx = -W / 4
    side_cx  =  W / 4

    # ── Stylesheet ────────────────────────────────────────────────────────────
    import svg_styles as _ss
    thing["styles"] = _ss.get_stylesheet("project_bolt")
    #thing["styles"] = _ss.get_stylesheet("jazzy")
    _st = thing["styles"]

    # Pull key colours directly from the resolved stylesheet
    _plate_c  = _st.get("plate",         {}).get("color",        "#FAFAFA")
    _plate_sk = _st.get("plate.outline", {}).get("stroke",       "#1A1A1A")
    _plate_sw = _st.get("plate.outline", {}).get("stroke_width", 0.8)
    _cut_c    = _st.get("hole.cut",{}).get("color",        "#FFFFFF")
    _cut_sk   = _st.get("hole.cut",{}).get("stroke",       "#444444")
    _cut_sw   = _st.get("hole.cut",{}).get("stroke_width", 0.3)
    _dim_sk   = _st.get("outline", {}).get("stroke",       "#1A1A1A")
    _dim_sw   = _st.get("outline", {}).get("stroke_width", 0.5)
    _lbl_c    = _st.get("label",   {}).get("color",        "#1A1A1A")
    _mut_c    = _st.get("label.muted", {}).get("color",    "#888888")
    _tit_c    = _st.get("label.title", {}).get("color",    "#111111")
    _hdr_c    = _st.get("header",  {}).get("color",        "#1C1C1C")


    def _abs_pos(x_off, y_off):
        p = copy.deepcopy(pos)
        p[0] += x_off
        p[1] += y_off
        return p

    def _hline(y_coord, x1=-W / 2 + 10, x2=W / 2 - 10, sw=None):
        lpos = _abs_pos(0, y_coord)
        opsvg.se(thing, shape="line",
                 p1=[x1, 0], p2=[x2, 0],
                 color=_dim_sk, stroke_width=(sw if sw is not None else _dim_sw),
                 pos=lpos)

    def _text_at(x_off, y_off, text, size=4.0, halign="center",
                 color=None, bold=False, muted=False):
        tpos = _abs_pos(x_off, y_off)
        col  = _mut_c if muted else (color or _lbl_c)
        fw   = "bold" if bold else ""
        opsvg.se(thing, shape="text",
                 text=text, size=size, halign=halign, valign="center",
                 color=col, font_weight=fw, pos=tpos)

    def _dim(cx_off, cy_off, p1, p2, offset, text, direction="auto"):
        dpos = _abs_pos(cx_off, cy_off)
        opsvg.se(thing, shape="dimension_line",
                 p1=p1, p2=p2, offset=offset, direction=direction,
                 text=text, text_size=ann_ts,
                 color=_dim_sk, stroke_width=_dim_sw, pos=dpos)

    def _hex_pts(r):
        return [[r * math.cos(math.radians(90 + 60 * i)),
                 r * math.sin(math.radians(90 + 60 * i))]
                for i in range(6)]

    # ── Background + border ───────────────────────────────────────────────────
    opsvg.se(thing, shape="rect", color="#ffffff",
             size=[W, H, 0], pos=_abs_pos(0, 0))
    opsvg.se(thing, shape="rounded_rectangle",
             color="none", stroke=_plate_sk, stroke_width=_plate_sw,
             size=[W - 8, H - 8, 0], r=3.5, pos=_abs_pos(0, 0))

    # ── Header ────────────────────────────────────────────────────────────────
    _text_at(-W / 2 + 14, brand_y, part_id,
             size=3.2, halign="left", muted=True)
    _text_at(-W / 2 + 14, title_y, part_title,
             size=18.0, halign="left", bold=True, color=_hdr_c)
    _text_at(-W / 2 + 14, part_name_y, f"{part_category}",
             size=4.5, halign="left", muted=True)
    _text_at(-W / 2 + 14, series_y, part_series,
             size=4.0, halign="left", muted=True)
    _hline(rule1_y)
    _text_at(-W / 2 + 14, dim_head_y, "DIMENSIONS",
             size=5.2, halign="left", bold=True, color=_tit_c)
    if view_scale >= 1:
        scale_label = f"{int(view_scale)}:1"
    else:
        scale_label = f"1:{int(round(1 / view_scale))}"
    _text_at(W / 2 - 14, dim_head_y, f"{scale_label} RATIO  —  PRINT AT 100%",
             size=3.2, halign="right", muted=True)

    # ── View labels ───────────────────────────────────────────────────────────
    _text_at(front_cx, view_label_y, "FRONT VIEW", size=3.2, bold=True, muted=True)
    _text_at(side_cx,  view_label_y, "SIDE VIEW",  size=3.2, bold=True, muted=True)

    # ── Front view (hex + bore) ───────────────────────────────────────────────
    fpos = _abs_pos(front_cx, view_cy)
    opsvg.se(thing, shape="polygon",
             points=_hex_pts(r_c_d),
             color=_plate_c, stroke=_plate_sk, stroke_width=_plate_sw, pos=fpos)
    opsvg.se(thing, shape="circle",
             r=bore_r_d,
             color=_cut_c, stroke=_cut_sk, stroke_width=_cut_sw, pos=fpos)

    # ── Side view ─────────────────────────────────────────────────────────────
    spos = _abs_pos(side_cx, view_cy)

    # Corner side view: outer width = e_mm (across corners = 2*r_c_d).
    # Chamfer creates a peaked top (and bottom for nut) — the hex corner
    # sits higher than the flat faces in this view.
    e_d       = 2 * r_c_d
    chamfer_h = max(r_c_d - af_d / 2, 2.0)   # geometric peak height, min 2 mm

    origin = _abs_pos(side_cx, 0)   # anchor at side centre, Y=0

    _light_sk = _st.get("outline.light", {}).get("stroke", "#AAAAAA")
    _light_sw = _st.get("outline.light", {}).get("stroke_width", 0.3)

    if hardware_type == "nut":
        opsvg.se(thing, shape="rect",
                 size=[e_d, height_d, 0],
                 color=_plate_c, stroke=_plate_sk, stroke_width=_plate_sw, pos=spos)
        opsvg.se(thing, shape="rect",
                 size=[bore_r_d * 2, height_d, 0],
                 color=_cut_c, stroke=_cut_sk, stroke_width=_cut_sw, pos=spos)
        for x_off in (-af_d / 2, af_d / 2):
            opsvg.se(thing, shape="line",
                     p1=[x_off, -height_d / 2], p2=[x_off, height_d / 2],
                     color=_light_sk, stroke_width=_light_sw, pos=spos)
    else:
        head_d   = head_height_mm * view_scale
        shank_d  = length_mm * view_scale
        total_d  = head_d + shank_d
        top_y    = view_cy + total_d / 2
        bear_y   = top_y - head_d
        bot_y    = top_y - total_d

        thread_d  = thread_length_mm * view_scale
        grip_d    = shank_d - thread_d
        grip_cy   = bear_y - grip_d / 2
        thread_cy = bot_y + thread_d / 2

        opsvg.se(thing, shape="rect",
                 size=[e_d, head_d, 0],
                 color=_plate_c, stroke=_plate_sk, stroke_width=_plate_sw,
                 pos=_abs_pos(side_cx, (top_y + bear_y) / 2))
        for x_off in (-af_d / 2, af_d / 2):
            opsvg.se(thing, shape="line",
                     p1=[x_off, bear_y], p2=[x_off, top_y],
                     color=_light_sk, stroke_width=_light_sw, pos=origin)
        # Grip (unthreaded shank)
        if grip_d > 0:
            opsvg.se(thing, shape="rect",
                     size=[bore_r_d * 2, grip_d, 0],
                     color=_plate_c, stroke=_plate_sk, stroke_width=_plate_sw,
                     pos=_abs_pos(side_cx, grip_cy))
        # Threaded portion
        opsvg.se(thing, shape="rect",
                 size=[bore_r_d * 2, thread_d, 0],
                 color=_st.get("plate.light", {}).get("color", "#F0F0F0"),
                 stroke=_plate_sk, stroke_width=_plate_sw,
                 pos=_abs_pos(side_cx, thread_cy))

    # ── Dimension annotations ─────────────────────────────────────────────────
    _dim(front_cx, view_cy,
         p1=[-af_d / 2, upper_vert_y], p2=[af_d / 2, upper_vert_y],
         offset=upper_vert_y + 8, text=f"ACROSS FLATS  {af_mm:.0f} mm",
         direction="horizontal")
    _dim(front_cx, view_cy,
         p1=[-bore_r_d, 0], p2=[bore_r_d, 0],
         offset=-(r_c_d + 8), text=f"THREAD BORE  Ø{id_mm:.0f} mm",
         direction="horizontal")

    if hardware_type == "nut":
        _dim(side_cx, view_cy,
             p1=[-af_d / 2, height_d / 2], p2=[af_d / 2, height_d / 2],
             offset=8, text=f"ACROSS FLATS  {af_mm:.0f} mm",
             direction="horizontal")
        _dim(side_cx, view_cy,
             p1=[af_d / 2, -height_d / 2], p2=[af_d / 2, height_d / 2],
             offset=8, text=f"NUT HEIGHT  {height_mm:.1f} mm",
             direction="vertical")
    else:
        head_d  = head_height_mm * view_scale
        shank_d = length_mm * view_scale
        total_d = head_d + shank_d
        top_y   = view_cy + total_d / 2
        bear_y  = top_y - head_d
        bot_y   = top_y - total_d
        # ACROSS FLATS spans the inner lines (±af_d/2), annotated above head top
        _dim(side_cx, 0,
             p1=[-af_d / 2, top_y], p2=[af_d / 2, top_y],
             offset=8, text=f"ACROSS FLATS  {af_mm:.0f} mm",
             direction="horizontal")
        # HEAD HEIGHT: manual bracket so text stays flat (horizontal).
        _gap  = 1.5;  _ovr = 1.5;  _tick = 1.5;  _off = 8
        _bx   = side_cx - r_c_d - _off   # bar x in part coords
        _dpos = _abs_pos(0, 0)
        for _ey in (bear_y, top_y):
            opsvg.se(thing, shape="line",
                     p1=[side_cx - r_c_d - _gap, _ey],
                     p2=[_bx - _ovr, _ey],
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
        # Thread length on the left side of the shank
        _dim(side_cx, 0,
             p1=[-bore_r_d, bot_y], p2=[-bore_r_d, bot_y + thread_d],
             offset=-(r_c_d - bore_r_d + 8), text=f"THREAD LENGTH  {thread_length_mm:.0f} mm",
             direction="vertical")

    # ── Summary ───────────────────────────────────────────────────────────────
    rule2_y  = -H / 2 + 72.0
    val_y    = -H / 2 + 61.0   # value row (large bold)
    lbl_y    = -H / 2 + 53.5   # label row (small muted)
    rule3_y  = -H / 2 + 46.0
    code_y   = -H / 2 + 38.0
    name_y   = -H / 2 + 29.0
    rule4_y  = -H / 2 + 20.0
    foot_y   = -H / 2 + 12.0

    _hline(rule2_y)

    margin = -W / 2 + 14
    content_w = W - 28        # 182 mm

    if hardware_type == "nut":
        cols = [
            (f"M{id_mm:.0f}",          "THREAD"),
            (f"{af_mm:.0f} mm",         "ACROSS FLATS"),
            (f"{height_mm:.1f} mm",     "NUT HEIGHT"),
        ]
    else:
        cols = [
            (f"M{id_mm:.0f}",            "THREAD"),
            (f"{af_mm:.0f} mm",           "ACROSS FLATS"),
            (f"{length_mm:.0f} mm",       "SHANK LENGTH"),
            (f"{thread_length_mm:.0f} mm","THREAD LENGTH"),
        ]

    step = content_w / len(cols)
    for i, (val, lbl) in enumerate(cols):
        x = margin + i * step
        _text_at(x, val_y, val, size=5.5, halign="left", bold=True, color=_tit_c)
        _text_at(x, lbl_y, lbl, size=3.0, halign="left", muted=True)

    _hline(rule3_y, sw=0.3)
    if part_code:
        _text_at(margin, code_y, part_code, size=3.2, halign="left", muted=True)
    _text_at(margin, name_y,
             part_name if part_name else part_title,
             size=3.0, halign="left", color="#aaaaaa")
    _hline(rule4_y, sw=0.3)
    md5_6     = thing.get("md5_6", "")
    foot_url  = f"oom.lt/{md5_6}" if md5_6 else "oomlout.com"
    _text_at(margin,      foot_y, "OOMLOUT",  size=2.8, halign="left",  muted=True)
    _text_at(W / 2 - 14, foot_y, foot_url,   size=2.8, halign="right", muted=True)


if __name__ == '__main__':
    kwargs = {}
    main(**kwargs)
