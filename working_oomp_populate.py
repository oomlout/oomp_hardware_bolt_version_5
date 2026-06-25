import copy

from oomp_populate_helper import write_extras, build_oomp_id
from working_oomp_populate_bolt import generate as generate_bolt
from working_oomp_populate_set_screw import generate as generate_set_screw
from working_oomp_populate_nut import generate as generate_nut
from working_oomp_populate_washer import generate as generate_washer



def main(**kwargs):
    
    options = []
    options.extend(generate_bolt())
    options.extend(generate_set_screw())
    options.extend(generate_nut())
    options.extend(generate_washer())

    extras = []
    for option in options:
        import csv
        
        #load size details from csv
        if True:
             styles = {}
             #load styles data
             if True:
                #nut
                if True:
                    style = {}
                    name = "nut"
                    style["name"] = name
                    file_name_iso_4032_nut_dimensions = "source_file\\dimension\\iso_4032_nut_dimensions.csv"
                    style["file_name"] = file_name_iso_4032_nut_dimensions
                    #nominal_diameter,thread_pitch_mm,s_min_mm,s_max_mm,e_min_mm,m_min_mm,m_max_mm,dw_min_mm,da_min_mm,da_max_mm,c_min_mm,c_max_mm
                    specs_iso_4032_nut_dimensions = ["nominal_diameter", "thread_pitch_mm", "s_min_mm", "s_max_mm", "e_min_mm", "m_min_mm", "m_max_mm", "dw_min_mm", "da_min_mm", "da_max_mm", "c_min_mm", "c_max_mm"]
                    style["specs"] = specs_iso_4032_nut_dimensions
                    svg_name = style.get("name", None)
                    style["svg_name"] = svg_name
                    styles[name] = style
                #bolt
                if True:
                    style = {}
                    name = "bolt"
                    style["name"] = name
                    style["file_name"] = "source_file\\dimension\\iso_4014_bolt_dimensions.csv"
                    #nominal_diameter,thread_pitch_mm,s_min_mm,s_max_mm,e_min_mm,k_min_mm,k_max_mm,dw_min_mm,da_max_mm,c_min_mm,c_max_mm,b_l_le_125_mm,b_125_lt_l_le_200_mm,b_l_gt_200_mm
                    style["specs"] = ["nominal_diameter", "thread_pitch_mm", "s_min_mm", "s_max_mm", "e_min_mm", "k_min_mm", "k_max_mm", "dw_min_mm", "da_max_mm", "c_min_mm", "c_max_mm", "b_l_le_125_mm", "b_125_lt_l_le_200_mm", "b_l_gt_200_mm"]
                    style["svg_name"] = name
                    styles[name] = style
                #set_screw — ISO 4017 full-thread hex screw; same head geometry as ISO 4014
                if True:
                    style = {}
                    name = "set_screw"
                    style["name"] = name
                    style["file_name"] = "source_file\\dimension\\iso_4014_bolt_dimensions.csv"
                    style["specs"] = ["nominal_diameter", "thread_pitch_mm", "s_min_mm", "s_max_mm", "e_min_mm", "k_min_mm", "k_max_mm", "dw_min_mm", "da_max_mm", "c_min_mm", "c_max_mm", "b_l_le_125_mm", "b_125_lt_l_le_200_mm", "b_l_gt_200_mm"]
                    style["svg_name"] = name
                    styles[name] = style
                #part gate
                run = False
                part_style = option.get("taxonomy_2", None)
                nominal_diameter = ""
                if part_style == "nut":
                    nominal_diameter = option.get("taxonomy_3", None)
                    typ = option.get("taxonomy_4", None)
                    if typ == "" or typ == None:
                        run = True
                if part_style == "bolt":
                    nominal_diameter = option.get("taxonomy_3", None)
                    run = True
                if part_style == "set_screw":
                    nominal_diameter = option.get("taxonomy_3", None)
                    run = True
                if run:
                    style = styles[part_style]                    
                    file_name = style.get("file_name", None)
                    with open(file_name, 'r', encoding='utf-8') as file:
                        reader = csv.DictReader(file)
                        svg_details = {}
                        svg_name = style.get("svg_name", None)
                        if svg_name != None:
                                svg_details["svg_name"] = copy.deepcopy(svg_name)
                                option["svg_details"] = svg_details                            
                        for row in reader:
                            nominal_diameter_test = row.get("nominal_diameter", None)
                            if nominal_diameter_test == nominal_diameter.replace("_", ".").upper():
                                for spec in style.get("specs", []):
                                    option[f"spec_iso_{spec}"] = row.get(spec, None)
                                    if svg_name != None:
                                        svg_details[f"svg_{spec}"] = row.get(spec, None)
                                # mechanical drawing entry — same data source as csv
                                nom = row.get("nominal_diameter", "")
                                try:
                                    id_mm = float(nom.lstrip("Mm"))
                                except (ValueError, AttributeError):
                                    id_mm = 0.0
                                try:
                                    af_mm = float(row.get("s_max_mm", 0))
                                except (ValueError, TypeError):
                                    af_mm = 0.0

                                if part_style == "nut":
                                    try:
                                        height_mm = float(row.get("m_max_mm", 0))
                                    except (ValueError, TypeError):
                                        height_mm = 0.0
                                    mech = {
                                        "svg_name":      "oomp_mech_drawing_hardware",
                                        "filename":      "working_mechanical_drawing",
                                        "hardware_type": "nut",
                                        "part_title":    nom,
                                        "part_series":   "METRIC HEX NUT",
                                        "part_category": "HARDWARE / NUT",
                                        "id_mm":         id_mm,
                                        "af_mm":         af_mm,
                                        "height_mm":     height_mm,
                                        "part_code":     "ISO4032 / DIN934",
                                        "part_name":     option.get("id", ""),
                                    }

                                elif part_style == "bolt":
                                    try:
                                        head_height_mm = float(row.get("k_max_mm", 0))
                                    except (ValueError, TypeError):
                                        head_height_mm = 0.0
                                    length_str = option.get("taxonomy_4", "").replace("_mm_length", "")
                                    try:
                                        length_mm = float(length_str)
                                    except (ValueError, TypeError):
                                        length_mm = 0.0
                                    # Thread length depends on nominal bolt length (ISO 4014)
                                    try:
                                        if length_mm <= 125:
                                            thread_length_mm = float(row.get("b_l_le_125_mm") or 0)
                                        elif length_mm <= 200:
                                            thread_length_mm = float(row.get("b_125_lt_l_le_200_mm") or 0)
                                        else:
                                            thread_length_mm = float(row.get("b_l_gt_200_mm") or 0)
                                    except (ValueError, TypeError):
                                        thread_length_mm = length_mm
                                    mech = {
                                        "svg_name":          "oomp_mech_drawing_hardware",
                                        "filename":          "working_mechanical_drawing",
                                        "hardware_type":     "bolt",
                                        "part_title":        f"{nom}×{int(length_mm)}",
                                        "part_series":       "HEX HEAD BOLT",
                                        "part_category":     "HARDWARE / BOLT",
                                        "id_mm":             id_mm,
                                        "af_mm":             af_mm,
                                        "head_height_mm":    head_height_mm,
                                        "length_mm":         length_mm,
                                        "thread_length_mm":  thread_length_mm,
                                        "part_code":         "ISO4014 / DIN931",
                                        "part_name":         option.get("id", ""),
                                    }

                                elif part_style == "set_screw":
                                    try:
                                        head_height_mm = float(row.get("k_max_mm", 0))
                                    except (ValueError, TypeError):
                                        head_height_mm = 0.0
                                    length_str = option.get("taxonomy_7", "").replace("_mm_length", "")
                                    try:
                                        length_mm = float(length_str)
                                    except (ValueError, TypeError):
                                        length_mm = 0.0
                                    mech = {
                                        "svg_name":          "oomp_mech_drawing_hardware",
                                        "filename":          "working_mechanical_drawing",
                                        "hardware_type":     "set_screw",
                                        "part_title":        f"{nom}×{int(length_mm)}",
                                        "part_series":       "HEX HEAD FULL THREAD SCREW",
                                        "part_category":     "HARDWARE / SET SCREW",
                                        "id_mm":             id_mm,
                                        "af_mm":             af_mm,
                                        "head_height_mm":    head_height_mm,
                                        "length_mm":         length_mm,
                                        "thread_length_mm":  length_mm,  # ISO 4017 is fully threaded
                                        "part_code":         "ISO4017 / DIN933",
                                        "part_name":         option.get("id", ""),
                                    }

                                else:
                                    mech = None

                                if mech:
                                    option["svg_details"] = [svg_details, mech]
                                        
                                
                            
                
        extra = {}
        extra.update(option)
        extras.append(copy.deepcopy(extra))
        

    ######### add notes from an id string
    import working_oomp_populate_extra_detail
    working_oomp_populate_extra_detail.main(extras=extras)

    write_extras(extras)


# Call main automatically
if __name__ == "__main__":
    main()