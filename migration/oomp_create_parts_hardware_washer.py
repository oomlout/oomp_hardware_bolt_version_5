import oomp

def load_parts(**kwargs):
    print(f"  loading parts {__name__}")
    
    parts = []

    part_details = {}
    part_details["classification"] = "hardware"
    part_details["type"] = ["washer"]    
    part_details["size"] = ["m1", "m1_5", "m2","m2_5","m2_7","m3","m4","m5","m6","m8"]
    part_details["color"] = [""]
    part_details["description_main"] = ["", "penny"]    
    part_details["description_extra"] = ""
    part_details["manufacturer"] = ""
    part_details["part_number"] = ""
    part_details["kicad_reference"] = ""
    parts.append(part_details)    


    #nylon
    part_details = {}
    part_details["classification"] = "hardware"
    part_details["type"] = ["washer"]    
    part_details["size"] = "m6"
    part_details["color"] = ["nylon_white"]
    part_details["description_main"] = ["12_mm_outer_diameter_1_5_mm_depth"]    
    part_details["description_extra"] = ""
    part_details["manufacturer"] = ""
    part_details["part_number"] = ""
    part_details["kicad_reference"] = ""
    parts.append(part_details) 

    
    oomp.add_parts(parts, **kwargs)
    