import oomp
import copy

def load_parts(**kwargs):
    print(f"  loading parts {__name__}")
    
    parts = []

    part_details = {}
    part_details["classification"] = "hardware"
    part_details["type"] = "screw_wood"
    part_details["size"] = ""
    part_details["color"] = ""
    part_details["description_main"] = ""
    part_details["description_extra"] = ""
    part_details["manufacturer"] = ""
    part_details["part_number"] = ""
    
    default_empty = copy.deepcopy(part_details)

    #screw_countersunk pozi drive
    if True:
        extras_sizes = {}
        extras_sizes["m2"] = [4,5,6,8,10,12,16]
        extras_sizes["m2_5"] = [5,6,8,10,12,16,20]
        extras_sizes["m3"] = [5,6,8,10,12,16,20,25]
        extras_sizes["m3_5"] = [8,10,12,16]
        extras_sizes["m4"] = [6,8,10,12,16,20,25,30,40,50,60]
        extras_sizes["m5"] = [8,10,12,14,16,20,25,30,35,40,50,60,70,80,100]
        extras_sizes["m6"] = [10,12,16,20,25,30,40,100,120]    
        
        for extra_size in extras_sizes:
            lengths = extras_sizes[extra_size]
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = "screw_countersunk"
            part_details["color"] = "bright_zinc_plated"            
            part_details["description_extra"] = "pozidrive_head"
            part_details["manufacturer"] = ""
            part_details["part_number"] = ""
            part_details["size"] = extra_size
            for length in lengths:
                part_details["description_main"] = f"{length}_mm_length"
                parts.append(part_details)    
    
    
    # screw_countersunk black hex head
    if True:
        extras_sizes = {}
        extras_sizes["m2"] = [3,5,6,8,10,12,14,16,20,22,25]
        extras_sizes["m3"] = [4,5,6,8,10,12,16,20,25,30,35]
        extras_sizes["m4"] = [6,8,10,12,16,20,25,30,35,40]    
        
        for extra_size in extras_sizes:
            lengths = extras_sizes[extra_size]
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = "screw_countersunk"
            part_details["color"] = "black"
            part_details["description_extra"] = "hex_head"
            part_details["manufacturer"] = ""
            part_details["part_number"] = ""            
            part_details["size"] = extra_size
            for length in lengths:
                part_details["description_main"] = f"{length}_mm_length"
                parts.append(part_details) 


    # screw_countersunk black phillips head
    if True:
        extras_sizes = {}        
        extras_sizes["m1_4"] = [3,4,5,6,8,10]
        extras_sizes["m1_5"] = [3,4,5,6,8,10]
        extras_sizes["m1_6"] = [3,4,5,6,8,10]
        extras_sizes["m2"] = [3,4,5,6,7,8,10,12,14,16,18,20,22,25,30]
        
        for size in extras_sizes:
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = ["screw_countersunk"]
            sizes = [size]
            part_details["size"] = []
            for size in sizes:
                part_details["size"].append(f"{size}")
            part_details["color"] = ["black"]
            lengths = extras_sizes[size]
            part_details["description_main"] = []
            for length in lengths:
                part_details["description_main"].append(f"{length}_mm_length")
            part_details["description_extra"] = "phillips_head"
            part_details["manufacturer"] = ""
            part_details["part_number"] = ""
            part_details["kicad_reference"] = ""
            parts.append(part_details)    
    
    # screw_flat_head black phillips
    if True:
        extras_sizes = {}
        extras_sizes["m2"] = [3,4,5,6,8,10,12,14,16,20,22,25]
        extras_sizes["m2_5"] = [3,4,5,6,8,10,12,14,16,20,22,25]
        extras_sizes["m3"] = [4,5,6,8,10,12,14,16,18,20,22,25,30]
        extras_sizes["m4"] = [5,6,8,10,12,14,16,18,20,22,25,30,35,40]
        extras_sizes["m5"] = [6,8,10,12,14,16,18,20,22,25,30,35,40]
        extras_sizes["m6"] = [6,8,10,12,14,16,18,20,22,25,30,35,40,45,50]
        
        heads = ["phillips_head"]

        for size in extras_sizes:
            for head in heads:
                part_details = {}
                part_details["classification"] = "hardware"
                part_details["type"] = ["screw_flat_head"]
                sizes = [size]
                part_details["size"] = []
                for size in sizes:
                    part_details["size"].append(f"{size}")
                part_details["color"] = ["black"]
                lengths = extras_sizes[size]
                part_details["description_main"] = []
                for length in lengths:
                    part_details["description_main"].append(f"{length}_mm_length")
                part_details["description_extra"] = head
                part_details["manufacturer"] = ""
                part_details["part_number"] = ""
                part_details["kicad_reference"] = ""
                parts.append(part_details)    
    
    # screw_button black phillips
    if True:
        extras_sizes = {}
        extras_sizes["m2"] = [3,4,5,6,8,10,12,14,16,20,22,25]
        extras_sizes["m2_5"] = [3,4,5,6,8,10,12,14,16,20,22,25]
        extras_sizes["m3"] = [4,5,6,8,10,12,14,16,18,20,22,25,30]
        extras_sizes["m4"] = [5,6,8,10,12,14,16,18,20,22,25,30,35,40]
        extras_sizes["m5"] = [6,8,10,12,14,16,18,20,22,25,30,35,40]
        extras_sizes["m6"] = [6,8,10,12,14,16,18,20,22,25,30,35,40,45,50]
        
        heads = ["hex_head"]

        for size in extras_sizes:
            for head in heads:
                part_details = {}
                part_details["classification"] = "hardware"
                part_details["type"] = "screw_button_head"
                sizes = [size]
                part_details["size"] = []
                for size in sizes:
                    part_details["size"].append(f"{size}")
                part_details["color"] = ["black"]
                lengths = extras_sizes[size]
                part_details["description_main"] = []
                for length in lengths:
                    part_details["description_main"].append(f"{length}_mm_length")
                part_details["description_extra"] = head
                part_details["manufacturer"] = ""
                part_details["part_number"] = ""
                part_details["kicad_reference"] = ""
                parts.append(part_details) 
        
    #screw_grub
    if True:
        colors = []
        colors.append("black")
        colors.append("stainless_steel")

        extras_sizes = {}
        extras_sizes["m1_6"] = [2,2.5,3,4,5,8]
        extras_sizes["m2"] = [2,2.5,3,4,5,6,8,10,12,14]
        extras_sizes["m2_5"] = [2,2.5,3,4,5,6,8,10,12,14]
        extras_sizes["m3"] = [2,2.5,3,4,5,6,8,10,12,14,16,18,20]
        extras_sizes["m4"] = [3,4,5,6,8,10,12,14,16,18,20]
        extras_sizes["m5"] = [3,4,5,6,8,10,12,14,16,18,20,25,30,35]
        extras_sizes["m6"] = [6,8,10,12,14,16,18,20,30,40]
        
        part_details = {}
        part_details["classification"] = "hardware"
        part_details["type"] = "screw_grub"
        part_details["size"] = ""
        part_details["color"] = ""
        part_details["description_main"] = ""
        part_details["description_extra"] = "hex_head"
        part_details["manufacturer"] = ""
        part_details["part_number"] = ""

        default_screw_grub = part_details

        

        for color in colors:
            for size in extras_sizes:
                part_details = copy.deepcopy(default_screw_grub)
                part_details["color"] = color
                part_details["size"] = size
                default_current = part_details                
                lengths = extras_sizes[size]
                for length in lengths:
                    part_details = copy.deepcopy(default_current)
                    length_string = str(length)
                    length_string = length_string.replace(".","_")                    
                    part_details["description_main"] = f"{length_string}_mm_length"
                    parts.append(part_details)
        
    #screw_machine_screw pozi drive
    if True:
        extras_sizes = {}
        extras_sizes["m2"] = [4,6,8,10,12]
        extras_sizes["m3"] = [4,5,6,8,10,12,16,20,25,30,35,40]
        extras_sizes["m3_5"] = [5,8,10,12,16,20,25]
        extras_sizes["m4"] = [5,6,8,10,12,16,20,25,30,35,40,45,50,60,70,80,90,100]
        extras_sizes["m5"] = [6,8,10,12,14,16,20,25,30,35,40,50,60,80,100]
        extras_sizes["m6"] = [8,10,12,16,20,25,30,35,40,100,120]    
        for size in extras_sizes:
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = ["screw_machine_screw"]
            sizes = [size]
            part_details["size"] = []
            for size in sizes:
                part_details["size"].append(f"{size}")
            part_details["color"] = [""]
            lengths = extras_sizes[size]
            part_details["description_main"] = []
            for length in lengths:
                part_details["description_main"].append(f"{length}_mm_length")
            part_details["description_extra"] = "pozidrive_head"
            part_details["manufacturer"] = ""
            part_details["part_number"] = ""
            part_details["kicad_reference"] = ""
            parts.append(part_details)    
    
    #screw_machine_screw phillips nylon_white
    if True:
        extras_sizes = {}
        extras_sizes["m3"] = [12,16,20,25]
        for size in extras_sizes:
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = ["screw_machine_screw"]
            sizes = [size]
            part_details["size"] = []
            for size in sizes:
                part_details["size"].append(f"{size}")
            part_details["color"] = ["nylon_white"]
            lengths = extras_sizes[size]
            part_details["description_main"] = []
            for length in lengths:
                part_details["description_main"].append(f"{length}_mm_length")
            part_details["description_extra"] = "phillips_head"
            part_details["manufacturer"] = ""
            part_details["part_number"] = ""
            part_details["kicad_reference"] = ""
            parts.append(part_details)    

    #screw_self_tapping_phillips
    if True:
        extras_sizes = {}
        extras_sizes["m1"] = [3,5]
        extras_sizes["m1_2"] = [3,5,8]
        extras_sizes["m1_4"] = [3,5,8,10]
        extras_sizes["m1_7"] = [5,8,10,12,16]
        extras_sizes["m2"] = [5,8,12,16,20]
        extras_sizes["m2_3"] = [5,6,8,10,12,16,20]
        
        for size in extras_sizes:
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = ["screw_self_tapping"]
            sizes = [size]
            part_details["size"] = []
            for size in sizes:
                part_details["size"].append(f"{size}")
            part_details["color"] = ["black"]
            lengths = extras_sizes[size]
            part_details["description_main"] = []
            for length in lengths:
                part_details["description_main"].append(f"{length}_mm_length")
            part_details["description_extra"] = "phillips_head"
            part_details["manufacturer"] = ""
            part_details["part_number"] = ""
            part_details["kicad_reference"] = ""
            parts.append(part_details)    
    

    #screw_socket_cap
    if True:
        types = ["screw_socket_cap", "screw_socket_cap_low_head","screw_socket_cap_low_head_ultra" ]
        for typ in types:
            extras_sizes = {}
            extras_sizes["m2"] = [3,4,5,6,8,10,12,14,16,18,20,25]
            extras_sizes["m2_5"] = [4,5,6,8,10,12,16,20,25]
            extras_sizes["m3"] = [5,6,8,10,12,18,16,20,25,30,35,40,45,50,60]
            extras_sizes["m4"] = [4,6,8,10,12,14,16,20,25,30,35,40,45,50,60,65,70,75]
            extras_sizes["m5"] = [6,8,10,12,14,16,20,25,30,35,40,45,50,60,65,70,75,80,90,100,110,120]
            extras_sizes["m6"] = [8,12,16,20,25,30,35,40,45,50,60,65,70,80,90,100]    
            for size in extras_sizes:
                part_details = {}
                part_details["classification"] = "hardware"
                part_details["type"] = typ
                sizes = [size]
                part_details["size"] = []
                for size in sizes:
                    part_details["size"].append(f"{size}")
                    part_details["color"] = ["black"]
                    lengths = extras_sizes[size]
                    part_details["description_main"] = []
                    for length in lengths:
                        part_details["description_main"].append(f"{length}_mm_length")
                        part_details["description_extra"] = "hex_head"
                        part_details["manufacturer"] = ""
                        part_details["part_number"] = ""
                        part_details["kicad_reference"] = ""
                        parts.append(part_details)    
        
    #screw_thread_forming_phillips
    if True:
        extras_sizes = {}
        extras_sizes["m2_3"] = [6]
        extras_sizes["m2_5"] = [6]
        extras_sizes["m2_6"] = [6]
        for size in extras_sizes:
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = ["screw_thread_forming"]
            sizes = [size]
            part_details["size"] = []
            for size in sizes:
                part_details["size"].append(f"{size}")
            part_details["color"] = ["black"]
            lengths = extras_sizes[size]
            part_details["description_main"] = []
            for length in lengths:
                part_details["description_main"].append(f"{length}_mm_length")
            part_details["description_extra"] = "phillips_head"
            part_details["manufacturer"] = ""
            part_details["part_number"] = ""
            part_details["kicad_reference"] = ""
            parts.append(part_details)    
    
    #add corefix
    if True:
        part_details = {}
        part_details["classification"] = "hardware"
        part_details["type"] = "screw_wood"
        part_details["size"] = [""]
        part_details["color"] = [""]
        part_details["description_main"] = "10_mm_diameter_100_mm_length"
        part_details["description_extra"] = "pozidrive_head"
        part_details["manufacturer"] = "corefix"
        part_details["part_number"] = ""
        part_details["short_name"] = ""        
        part_details["part_number_exact"] = ""    
        part_details["distributor_screwfix"] = "344hg"
        part_details["distributor_screwfix_link"] = f"https://www.screwfix.com/p/{part_details['distributor_screwfix']}"
        parts.append(part_details)


        part_details = {}
        part_details["classification"] = "hardware"
        part_details["type"] = "screw_wood"
        part_details["size"] = [""]
        part_details["color"] = [""]
        part_details["description_main"] = "10_mm_diameter_120_mm_length"
        part_details["description_extra"] = "pozidrive_head"
        part_details["manufacturer"] = "corefix"
        part_details["part_number"] = ""
        part_details["short_name"] = ""        
        part_details["part_number_exact"] = ""    
        part_details["distributor_screwfix"] = "401hg"
        part_details["distributor_screwfix_link"] = f"https://www.screwfix.com/p/{part_details['distributor_screwfix']}"
        parts.append(part_details)


    #add goldscrew
    if True:
        screw_sizes = []
        screw_sizes.append([6,140])

        for screw_size in screw_sizes:
            diameter = screw_size[0]
            length = screw_size[1]
            
            part_details = copy.deepcopy(default_empty)
            part_details["description_main"] = f"{diameter}_mm_diameter_{length}_mm_length"
            part_details["manufacturer"] = "goldscrew"
            parts.append(part_details)



    #add screwtite screws
    if True:

        screws = []
        screw ={}
        #personal faves
        
        screws.append({"diameter":3.5, "length":16, "part_number":"419FY", "pack_count":200})
        screws.append({"diameter":3.5, "length":20, "part_number":"710FY", "pack_count":200})
        screws.append({"diameter":3.5, "length":30, "part_number":"488FY", "pack_count":200})
        screws.append({"diameter":3.5, "length":50, "part_number":"726FY", "pack_count":200})
        screws.append({"diameter":5, "length":90, "part_number":"800FY", "pack_count":100})
        screws.append({"diameter":5, "length":100, "part_number":"486FY", "pack_count":100})
        

        #trade pack
        screws.append({"diameter":3.5, "length":25, "part_number":"310FY", "pack_count":200}  )
        screws.append({"diameter":4, "length":30, "part_number":"284FY", "pack_count":200} )     
        screws.append({"diameter":4, "length":40, "part_number":"330FY", "pack_count":200})
        screws.append({"diameter":4, "length":50, "part_number":"127FY", "pack_count":200})
        screws.append({"diameter":4, "length":60, "part_number":"258FY", "pack_count":100})
        screws.append({"diameter":4, "length":70, "part_number":"131FY", "pack_count":100})
        screws.append({"diameter":5, "length":80, "part_number":"426FY", "pack_count":100})
        #screws.append({"diameter":5, "length":100, "part_number":"486FY"})

        #trade case
        #screws.append({"diameter":3.5, "length":30, "part_number":"488FY"})
        #screws.append({"diameter":4, "length":40, "part_number":"330FY", "pack_count":200} )       
        #screws.append({"diameter":4, "length":50, "part_number":"127FY", "pack_count":200})
        #screws.append({"diameter":4, "length":60, "part_number":"258FY", "pack_count":100})
        #screws.append({"diameter":4, "length":70, "part_number":"131FY", "pack_count":100})
        screws.append({"diameter":5, "length":50, "part_number":"", "pack_count":200})
        screws.append({"diameter":5, "length":70, "part_number":"", "pack_count":200})
        #screws.append({"diameter":5, "length":80, "part_number":"426FY", "pack_count":100})
        #screws.append({"diameter":5, "length":100, "part_number":"486FY"})





        default_current = copy.deepcopy(default_empty)
        default_current["type"] = "screw_wood"
        default_current["descripion_extra"] = "pozidrive_head"
        default_current["manufacturer"] = "screw_tite_two"



        for screw in screws:
            description_extras = []
            description_extras.append("")
            pack_count = screw["pack_count"]
            description_extras.append(f"{pack_count}_pack")
            for description_extra in description_extras:
                diameter = str(screw["diameter"]).replace(".","_")
                length = screw["length"]
                part_number = screw["part_number"]
                part_details = copy.deepcopy(default_current)
                part_details["description_main"] = f"{diameter}_mm_diameter_{length}_mm_length_pozidrive_head"
                part_details["description_extra"] = description_extra
                part_details["part_number"] = part_number
                parts.append(part_details)

        #trade pack
        part_details = {}
        part_details["classification"] = "hardware"
        part_details["type"] = "screw_wood"
        part_details["size"] = [""]
        part_details["color"] = [""]
        part_details["description_main"] = "trade_pack_1200_pieces"
        part_details["description_extra"] = "pozidrive_head"
        part_details["manufacturer"] = "screw_tite_two"
        part_details["part_number"] = "547FY"
        part_details["short_name"] = ""
        parts.append(part_details)

        #trade case
        part_details = {}
        part_details["classification"] = "hardware"
        part_details["type"] = "screw_wood"
        part_details["size"] = [""]
        part_details["color"] = [""]
        part_details["description_main"] = "trade_case_1200_pieces"
        part_details["description_extra"] = "pozidrive_head"
        part_details["manufacturer"] = "screw_tite_two"
        part_details["part_number"] = "712KR"
        part_details["short_name"] = ""
        parts.append(part_details)

        old = False
        if False:
            part_details = {}
            part_details["classification"] = "hardware"
            part_details["type"] = "screw_wood"
            part_details["size"] = [""]
            part_details["color"] = [""]
            part_details["description_main"] = "3_5_mm_diameter_50_mm_length"
            part_details["description_extra"] = "pozidrive_head"
            part_details["manufacturer"] = "screw_tite_two"
            part_details["part_number"] = "726FY"
            part_details["short_name"] = ""
            parts.append(part_details)

            screwtire_base = copy.deepcopy(part_details)

            part_details = copy.deepcopy(screwtire_base)
            part_details["description_main"] = "3_5_mm_diameter_30_mm_length"
            part_details["part_number"] = "488FY"
            parts.append(part_details)

            #5mm x 100 mm
            part_details = copy.deepcopy(screwtire_base)
            part_details["description_main"] = "5_mm_diameter_100_mm_length"
            part_details["part_number"] = "486FY"
            parts.append(part_details)

            # 5 mm 90 mm
            part_details = copy.deepcopy(screwtire_base)
            part_details["description_main"] = "5_mm_diameter_90_mm_length"
            part_details["part_number"] = "800FY"
            parts.append(part_details)



    
    oomp.add_parts(parts, **kwargs)
    