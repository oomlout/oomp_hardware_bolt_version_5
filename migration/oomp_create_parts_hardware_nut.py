import oomp
import copy

def load_parts(**kwargs):
    print(f"  loading parts {__name__}")
    
    parts = []

    #2020
    # standard
    if True:
        part_details = {}
        part_details["classification"] = "hardware"
        part_details["type"] = "nut"    
        part_details["size"] = ""
        part_details["color"] = ""
        part_details["description_main"] = "2020"
        part_details["description_extra"] = ""
        part_details["manufacturer"] = ""
        part_details["part_number"] = ""
        
        part_default = copy.deepcopy(part_details)
        
        sizes = ["m3", "m4", "m5", "m6"]
        descs = ["t_nut", "ball_spring"]

        for size in sizes:
            for desc in descs:
                part_details = copy.deepcopy(part_default)
                part_details["size"] = size
                part_details["description_extra"] = desc
                parts.append(part_details)    

    # standard
    if True:
        part_details = {}
        part_details["classification"] = "hardware"
        part_details["type"] = ["nut"]    
        part_details["size"] = ["m1", "m1_4","m1_5", "m2","m2_5","m2_7","m3","m4","m5","m6","m8"]
        part_details["color"] = [""]    
        part_details["description_main"] = ["", "flanged", "locking", "coupling"]    
        part_details["description_extra"] = ""
        part_details["manufacturer"] = ""
        part_details["part_number"] = ""
        part_details["kicad_reference"] = ""
        parts.append(part_details)    

    # cage
    if True:
        part_details = {}
        part_details["classification"] = "hardware"
        part_details["type"] = ["nut"]    
        part_details["size"] = ["m5","m6","m8"]
        part_details["color"] = [""]    
        part_details["description_main"] = ["cage"]    
        part_details["description_extra"] = ""
        part_details["manufacturer"] = ""
        part_details["part_number"] = ""
        part_details["kicad_reference"] = ""
        parts.append(part_details)    

    # standard
    if True:
        part_details = {}
        part_details["classification"] = "hardware"
        part_details["type"] = ["nut"]    
        part_details["size"] = ["m3"]
        part_details["color"] = ["black"]    
        part_details["description_main"] = [""]    
        part_details["description_extra"] = ""
        part_details["manufacturer"] = ""
        part_details["part_number"] = ""
        part_details["kicad_reference"] = ""
        parts.append(part_details)    


    # nylon_white
    if True:
        part_details = {}
        part_details["classification"] = "hardware"
        part_details["type"] = ["nut"]    
        part_details["size"] = ["m3","m4","m5","m6","m8"]
        part_details["color"] = ["nylon_white"]    
        part_details["description_main"] = [""]    
        part_details["description_extra"] = ""
        part_details["manufacturer"] = ""
        part_details["part_number"] = ""
        part_details["kicad_reference"] = ""
        parts.append(part_details)    


    
    oomp.add_parts(parts, **kwargs)
    