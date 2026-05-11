import working_oomp_populate

def main(**kwargs):
    extras = kwargs.get("extras", [])
    extras_dict = {}
    for extra in extras:
        oomp_id =  working_oomp_populate.build_oomp_id(extra)
        extras_dict[oomp_id] = extra

    ######add colour bands to tray
    types = []
    current_band_1 = "red"
    styles = {}
    #countersunk
    if True:
        styles["nut"] = {}
        styles["nut"]["band_1"] = "blue"
        band_2 = {}
        band_2["m2"] = "brown"
        band_2["m2_5"] = "red"
        band_2["m2_7"] = "orange"
        band_2["m3"] = "yellow"
        band_2["m4"] = "green"
        band_2["m5"] = "blue"
        band_2["m6"] = "purple"
        band_2["m8"] = "grey"
        band_2["m10"] = "white"        
        styles["nut"]["band_2"] = band_2
        
    for option in styles:
        style = option
        band_1 = styles[option]["band_1"]
        for option2 in styles[option]["band_2"]:
            band_2 = styles[option]["band_2"][option2]
            if True:                
                oomp_id = f"hardware_{style}_{option2}"
                if oomp_id in extras_dict:
                    extras_dict[oomp_id]["color_band_project_bolt_1"] = band_1
                    extras_dict[oomp_id]["color_band_taxonomy_2"] = band_1
                    extras_dict[oomp_id]["color_band_project_bolt_2"] = band_2
                    extras_dict[oomp_id]["color_band_taxonomy_3"] = band_2                   
                    extras_dict[oomp_id]["color_band_string_project_bolt"] = f"colour_band_{band_1}_{band_2}"
    pass
                
        
    