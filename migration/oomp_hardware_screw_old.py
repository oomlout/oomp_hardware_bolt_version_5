import oomp

def load_parts(**kwargs):
    print(f"  loading parts {__name__}")
    
    parts = []

    #standard bzp bolts
    if True:
        extras_sizes = {}
        extras_sizes["m4"] = [40]
        extras_sizes["m5"] = [35,40,45,60,65,70]
        extras_sizes["m6"] = [25,30,35,40,45,50,60,65,70,75,80,90,100,110,120]
        extras_sizes["m8"] = [30,35,40,45,50,60,65,70,75,80,90,95,100,110,120,130,140,150]
        # bolt
        for size in extras_sizes:
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = ["bolt"]
            sizes = [size]
            part_details["size"] = []
            for size in sizes:
                part_details["size"].append(f"{size}")
            part_details["color"] = [""]
            lengths = extras_sizes[size]
            part_details["description_main"] = []
            for length in lengths:
                part_details["description_main"].append(f"{length}_mm_length")
            part_details["description_extra"] = ""
            part_details["manufacturer"] = ""
            part_details["part_number"] = ""
            part_details["kicad_reference"] = ""
            parts.append(part_details)    
    
    

    #standard bzp setscrew
    if True:
        extras_sizes = {}
        extras_sizes["m3"] = [8,10,12,16,20,25,30]
        extras_sizes["m4"] = [8,10,12,16,20,25,30,35,40,50]
        extras_sizes["m5"] = [8,10,12,14,16,20,22,25,30,35,40,45,50,60,65,70,80]
        extras_sizes["m6"] = [8,10,12,15,16,18,20,22,25,30,35,40,45,50,55,60,65,70,75,80,90,100]
        extras_sizes["m8"] = [10,12,16,20,25,30,35,40,45,50,55,60,65,70,75,80,90,100,110,120,130,140,150]
        # set_screw
        for size in extras_sizes:
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = ["set_screw"]
            sizes = [size]
            part_details["size"] = []
            for size in sizes:
                part_details["size"].append(f"{size}")
            part_details["color"] = [""]
            lengths = extras_sizes[size]
            part_details["description_main"] = []
            for length in lengths:
                part_details["description_main"].append(f"{length}_mm_length")
            part_details["description_extra"] = ""
            part_details["manufacturer"] = ""
            part_details["part_number"] = ""
            part_details["kicad_reference"] = ""
            parts.append(part_details)    

    #nylon white set_screw
    if True:
        extras_sizes = {}
        extras_sizes["m6"] = [12,15,20,25,30,50]
        # bolt
        for size in extras_sizes:
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = ["set_screw"]
            sizes = [size]
            part_details["size"] = []
            for size in sizes:
                part_details["size"].append(f"{size}")
            part_details["color"] = ["nylon_white"]
            lengths = extras_sizes[size]
            part_details["description_main"] = []
            for length in lengths:
                part_details["description_main"].append(f"{length}_mm_length")
            part_details["description_extra"] = ""
            part_details["manufacturer"] = ""
            part_details["part_number"] = ""
            part_details["kicad_reference"] = ""
            parts.append(part_details)



    oomp.add_parts(parts, **kwargs)
    