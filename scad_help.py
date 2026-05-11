import copy
import oobb
import yaml
import os
import re
import working_scad
###### utilities


def cleanup_raw_scad_artifacts(folder):
    if not folder or not os.path.isdir(folder):
        return

    hex_pattern = re.compile(r"^(?P<stem>.+)_[0-9a-f]{16}\.scad$")
    referenced_helpers = {}

    for entry in os.listdir(folder):
        if not entry.endswith(".scad"):
            continue

        scad_path = os.path.join(folder, entry)
        try:
            with open(scad_path, "r", encoding="utf-8") as handle:
                contents = handle.read()
        except OSError:
            continue

        for match in re.finditer(r"use <([^>]+/(?P<stem_abs>[^/>]+)_[0-9a-f]{16}\.scad|(?P<stem_rel>[^/>]+)_[0-9a-f]{16}\.scad)>", contents):
            stem = match.group("stem_abs") or match.group("stem_rel")
            hashed_name = os.path.basename(match.group(1))
            referenced_helpers[stem] = hashed_name

        updated = re.sub(
            r"use <([^>]+/)?(?P<stem>[^/>]+)_[0-9a-f]{16}\.scad>",
            lambda m: f"use <{m.group('stem')}.scad>",
            contents,
        )
        if updated != contents:
            with open(scad_path, "w", encoding="utf-8") as handle:
                handle.write(updated)

    for stem, hashed_name in referenced_helpers.items():
        friendly_path = os.path.join(folder, f"{stem}.scad")
        hashed_path = os.path.join(folder, hashed_name)
        if not os.path.exists(friendly_path) and os.path.exists(hashed_path):
            with open(hashed_path, "r", encoding="utf-8") as src:
                contents = src.read()
            with open(friendly_path, "w", encoding="utf-8") as dst:
                dst.write(contents)

    for entry in os.listdir(folder):
        match = hex_pattern.match(entry)
        if not match:
            continue

        friendly_name = f"{match.group('stem')}.scad"
        friendly_path = os.path.join(folder, friendly_name)
        hashed_path = os.path.join(folder, entry)

        if os.path.exists(friendly_path):
            try:
                os.remove(hashed_path)
            except OSError:
                pass

def get_typ(**kwargs):
    typ = kwargs.get("typ", "")

    if typ == "":
        #setup
        #typ = "all"
        typ = "fast"
        #typ = "manual"

    return typ


def get_build_variables(typ, filter=""):
    if typ == "all":
        return {
            "filter": "",
            "save_type": "all",
            "navigation": True,
            "overwrite": True,
            "modes": ["3dpr"],
            "oomp_run": True,
        }

    if typ == "fast":
        return {
            "filter": "",
            "save_type": "none",
            "navigation": True,
            "overwrite": True,
            "modes": ["3dpr"],
            "oomp_run": False,
        }

    if typ == "manual":
        return {
            "filter": "",
            #"filter": "test"
            "save_type": "none",
            #"save_type": "all"
            "navigation": True,
            #"navigation": False
            "overwrite": True,
            "modes": ["3dpr"],
            #"modes": ["3dpr", "laser", "true"]
            #"modes": ["laser"]
            "oomp_run": True,
            #"oomp_run": False
        }

    raise ValueError(f"Unknown typ: {typ}")


def get_navigation_sort(oobb_style=False):
    sort = []
    if oobb_style:
        #sort.append("extra")
        sort.append("oobb_name") 
        sort.append("width")
        sort.append("height")
        sort.append("thickness")
    else:
        for i in range(1, 10):
            sort.append(f"taxonomy_{i}")
    return sort


def prepare_base_for_print(thing, pos, **kwargs):
    #put into a rotation object
    components_second = copy.deepcopy(thing["components"])
    return_value_2 = {}
    return_value_2["type"]  = "rotation"
    return_value_2["typetype"]  = "p"
    pos1 = copy.deepcopy(pos)
    pos1[0] += 50
    return_value_2["pos"] = pos1
    return_value_2["rot"] = [180,0,0]
    return_value_2["objects"] = components_second

    thing["components"].append(return_value_2)

    #add slice # top
    p3 = copy.deepcopy(kwargs)
    p3["type"] = "n"
    p3["shape"] = f"oobb_slice"
    pos1 = copy.deepcopy(pos)
    pos1[0] += -500/2
    pos1[1] += 0
    pos1[2] += -500/2
    p3["pos"] = pos1
    #p3["m"] = "#"
    oobb.append_full(thing,**p3)

def make_parts(**kwargs):
    parts = kwargs.get("parts", [])
    filter = kwargs.get("filter", "")
    #make the parts
    if True:
        for part in parts:
            oobb_name = part.get("oobb_name", "default")            
            extra = part["kwargs"].get("extra", "")
            if filter in oobb_name or filter in extra:
                print(f"making {part['oobb_name']}")
                make_scad_generic(part)            
                
            else:
                print(f"skipping {part['oobb_name']}")
    

def make_scad_generic(part):
    
    # fetching variables
    oobb_name = part.get("oobb_name", "default")
    project_name = part.get("project_name", "default")
    
    kwargs = part.get("kwargs", {})    
    
    modes = kwargs.get("modes", ["3dpr", "laser", "true"])
    save_type = kwargs.get("save_type", "all")
    overwrite = kwargs.get("overwrite", True)

    kwargs["type"] = f"{project_name}_{oobb_name}"

    thing = oobb.get_default_thing(**kwargs)
    thing.update(part)
    kwargs.pop("size","")

    #get the part from the function get_{oobb_name}"
    try:
        func = getattr(working_scad, f"get_{oobb_name}")
    except AttributeError:
        func = None
    # test if func exists
    if callable(func):            
        func(thing, **kwargs)        
    else:            
        working_scad.get_base(thing, **kwargs)   

    oomp_mode = kwargs.get("oomp_mode", "project")
    
    if oomp_mode == "project":
        descmain = ""
        current_description_main = thing.get("description_main", "default")
        current_size = thing.get("size", "default")
        new_size = current_size.replace(f"{project_name}_", "")
        descmain = f"{new_size}_{current_description_main}"
        kwargs["oomp_description_main"] = f"{descmain}"
        descextra = ""
        current_description_extra = thing.get("description_extra", "")
        descextra = f"{current_description_extra}"
        kwargs["oomp_description_extra"] = f"{descextra}"
    elif oomp_mode == "oobb":
        current_description_main = thing.get("description_main", "default")   
        descmain = f"{current_description_main}" 

        descextra = thing.get("extra", "")    
        if descextra != "":
            descextra = f"{descextra}_extra"
        kwargs["oomp_description_main"] = f"{current_description_main}"
        kwargs["oomp_description_extra"] = f"{descextra}"
        kwargs["oomp_size"] = f"{part['oobb_name']}"

    #id = thing.get("oobb_id", "default")    
    

    #kwargs["description_main"] = id

    oomp_keys = ["classification", "type", "size", "color", "description_main", "description_extra", "manufacturer", "part_number"]
    oomp_id = part.get("id", "")
    if oomp_id == "":
        for key in oomp_keys:
            deet = part.get(key, "")
            deet = deet.replace(".","_")
            if deet != "":
                oomp_id += f"{deet}_"
        oomp_id = oomp_id[:-1]
    part["id"] = oomp_id
    folder = f"parts/{oomp_id}"

    for mode in modes:
        depth = thing.get(
            "depth_mm", thing.get("thickness_mm", 3))
        height = thing.get("height_mm", 100)
        layers = depth / 3
        tilediff = height + 10
        start = 1.5
        if layers != 1:
            start = 1.5 - (layers / 2)*3
        if "bunting" in thing:
            start = 0.5
        

        oobb.opsc_make_object(f'{folder}/{mode}.scad', thing["components"], mode=mode, save_type=save_type, overwrite=overwrite, layers=layers, tilediff=tilediff, start=start)
        cleanup_raw_scad_artifacts(folder)
        


    yaml_file = f"{folder}/working.yaml"
    #partial dump
    with open(yaml_file, 'w') as file:
        part_new = copy.deepcopy(part)
        kwargs_new = part_new.get("kwargs", {})
        kwargs_new.pop("save_type","")
        part_new["kwargs"] = kwargs_new
        import os
        cwd = os.getcwd()
        part_new["project_name"] = cwd
        part_new["id_oobb"] = thing["id"]
        #part_new["thing"] = thing
        part_new.pop("thing", "")
        yaml.dump(part_new, file)
    
    #full dump
    yaml_file = f"{folder}/thing.yaml"
    with open(yaml_file, 'w') as file:
        part_new = copy.deepcopy(part)
        kwargs_new = part_new.get("kwargs", {})
        kwargs_new.pop("save_type","")
        part_new["kwargs"] = kwargs_new
        import os
        cwd = os.getcwd()
        part_new["project_name"] = cwd
        part_new["id_oobb"] = thing["id"]
        part_new["thing"] = thing
        yaml.dump(part_new, file)


    print(f"done {oomp_id}")

def generate_navigation(folder="parts", sort=["width", "height", "thickness"]):
    #crawl though all directories in scad_output and load all the working.yaml files
    parts = {}
    for root, dirs, files in os.walk(folder):
        if 'working.yaml' in files:
            yaml_file = os.path.join(root, 'working.yaml')
            #if working.yaml isn't in the root directory, then do it
            if root != folder:
                with open(yaml_file, 'r') as file:
                    part = yaml.safe_load(file)
                    # Process the loaded YAML content as needed
                    part["folder"] = root
                    part_name = root.replace(f"{folder}","")
                    
                    #remove all slashes
                    part_name = part_name.replace("/","").replace("\\","")
                    parts[part_name] = part

                    print(f"Loaded {yaml_file}")

    pass
    
    for part_id in parts:
        if part_id != "":
            part = parts[part_id]

            if "kwargs" in part:
                kwarg_copy = copy.deepcopy(part["kwargs"])
                folder_navigation = "navigation_oobb"
                folder_source = part["folder"]
                folder_extra = ""
                for s in sort:
                    if s == "oobb_name":
                        ex = part.get("oobb_name", "default")
                    else:                        
                        ex = kwarg_copy.get(s, "default")
                        if ex == "default":
                            ex = part.get(s, "default")
                        #if ex is a list
                        if isinstance(ex, list):
                            ex_string = ""
                            for e in ex:
                                ex_string += f"{e}_"
                            ex = ex_string[:-1]
                            ex = ex.replace(".","d")                            
                    if ex != "default" and ex != "":
                        if "taxonomy_" in s:
                            folder_extra += f"{ex}/"
                        else:
                            folder_extra += f"{s}_{ex}/"

                #replace "." with d
                folder_extra = folder_extra.replace(".","d")            
                folder_destination = f"{folder_navigation}/{folder_extra}"
                if not os.path.exists(folder_destination):
                    os.makedirs(folder_destination)
                if os.name == 'nt':
                    #copy a full directory auto overwrite
                    command = f'xcopy "{folder_source}" "{folder_destination}" /E /I /Y'
                    print(command)
                    os.system(command)
                else:
                    os.system(f"cp {folder_source} {folder_destination}")
                cleanup_raw_scad_artifacts(folder_destination)

