import oomp
import oomp_helper
import copy
import oomlout_roboclick

def main(**kwargs):
    load_parts(**kwargs)

def load_parts(**kwargs):
    make_files = kwargs.get("make_files", True)
    #print "loading parts" plus the module name get the module name from the filename using __name__
    print(f"  loading parts {__name__}")
    create_generic(**kwargs)

def create_generic(**kwargs):
    print(f"  loading parts from part_source")
    things = {}    
    
    #load parts from parts_source directory
    directory_source = "parts_source"
    import os
    if not os.path.exists(directory_source):
        print(f"      directory {directory_source} does not exist, creating it")
        #create it
        os.makedirs(directory_source)
    directories = os.listdir(directory_source)
    for directory  in directories:
        directory_full = f"{directory_source}/{directory}"
        filenames = os.listdir(f"{directory_full}")
        for filename in filenames:
            import yaml
            #go through directories and load working.yaml files
            # only load .yaml files
            if "working.yaml" in filename:
                file_path = os.path.join(directory_full, filename)
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    thing_details = {}
                    for deet in data:
                        thing_details[deet] = data[deet]
                    things[directory] = thing_details
    
    
    parts = []

    for thing in things:
        current = things[thing]                
        #name stuff        
        part = copy.deepcopy(current)
        
        part["name"] = thing
        part["name_space"] = thing.replace("_", " ")
        part["name_proper"] = part["name_space"].title()
        part["name_upper"] = part["name_space"].upper()
        
        folder = oomlout_roboclick.get_directory(part)   
        part["directory"] = folder  
        url_chat = oomlout_roboclick.get_url(part)   
        part["url_chat"] = url_chat
        files_to_trace = []
        count = 0

        #mode_ai_wait = "fast"
        mode_ai_wait = "slow"


        #icon
        if True:
            count += 1     
            icon_detail = "please include the thread size and length in the image as text, add extra icons in the back, one that ryhmes with the diameter and one or two that rhymes with the length, if the length is less than 14 just one if it is greater do two, one rhyming for each part of the number ie for twenty five one that rhymes with twenty and one that rhymes with five. Put some time into searching to find the rhymes"
            oomp_helper.add_icon(part=part, count=count, mode_ai_wait=mode_ai_wait, icon_detail=icon_detail)

        #folder_project = "helen_personal_chart_bribe_bank"
        #iomage)chibi
        test_image_chibi = False
        if test_image_chibi:
            content_string = part.get("content_string", "")    
            count += 1
            chibi_detail = "please include the thread size and length in the image as text, add extra icons in the back, one that ryhmes with the diameter and one or two that rhymes with the length, if the length is less than 14 just one if it is greater do two, one rhyming for each part of the number ie for twenty five one that rhymes with twenty and one that rhymes with five. Put some time into searching to find the rhymes"
            oomp_helper.add_image_chibi(part=part, count=count, mode_ai_wait=mode_ai_wait, chibi_detail=chibi_detail)       

        #jinja_template replace
        if True:
            templates = []
            templates.append({"template_folder": "default"})
            #templates.append({"template_folder": "source_file\\template_jinja\\template_label_15_mm_30_mm", "output_filename": "label_oomp_small.svg"})
            convert_to_pdf = False
            convert_to_png = False
            count = oomp_helper.add_jinja_template(part=part, templates=templates, mode_ai_wait=mode_ai_wait, count=count, convert_to_pdf=convert_to_pdf, convert_to_png=convert_to_png)
        #prompt bubble letter        
        if False:
            count = oomp_helper.add_image(
                part=part,
                folder_project=folder_project,
                files_to_trace=files_to_trace,
                mode_ai_wait=mode_ai_wait,
                count=count,
            )

        #prompt image theme
        if False:
            count = oomp_helper.add_prompt_image(
                part=part,
                folder_project=folder_project,
                prompt_folder="prompt_image_main_1",
                file_name="image_main_1.png",
                files_to_trace=files_to_trace,
                mode_ai_wait=mode_ai_wait,
                count=count,
            )
        #value
        if False:
            count = oomp_helper.add_value_images(
                part=part,
                folder_project=folder_project,
                files_to_trace=files_to_trace,
                mode_ai_wait=mode_ai_wait,
                count=count,
            )
            

        #cover_background
        #prompt image
        if False:
            count = oomp_helper.add_cover_background(
                part=part,
                folder_project=folder_project,
                files_to_trace=files_to_trace,
                mode_ai_wait=mode_ai_wait,
                count=count,
            )
       
        #internal border
        #prompt image
        if False:
            count = oomp_helper.add_prompt_image(
                part=part,
                folder_project=folder_project,
                prompt_folder="prompt_inside_border_1",
                file_name="image_inside_border.png",
                files_to_trace=files_to_trace,
                mode_ai_wait=mode_ai_wait,
                count=count,
            )

        #logo back
        #prompt image
        if False:
            count = oomp_helper.add_prompt_image(
                part=part,
                folder_project=folder_project,
                prompt_folder="prompt_logo_back_1",
                file_name="image_logo_back.png",
                files_to_trace=files_to_trace,
                mode_ai_wait=mode_ai_wait,
                count=count,
            )

        #trace
        if False:  
            count = oomp_helper.trace_files(
                part=part,
                files_to_trace=files_to_trace,
                mode_ai_wait=mode_ai_wait,
                count=count,
            )

        #make_card
        if False:
            count = oomp_helper.make_card(part=part, folder_project=folder_project, count=count)

        #research
        if False:
            count = oomp_helper.add_research(
                part=part,
                folder_project=folder_project,
                mode_ai_wait=mode_ai_wait,
                count=count,
            )


        parts.append(part)
    



    oomp.add_parts(parts, **kwargs)

    #dd file copy
    for part in parts:
        file_copies = part.get("file_copy", [])
        if file_copies != []:
            for file_copy in file_copies:
                directory = part.get("directory", "")
                if directory != "":
                    file_source = f'{file_copy["file_source"]}'
                    file_destination = f'{directory}\\{file_copy["file_destination"]}'
                    import shutil
                    print(f"      copying {file_source} to {file_destination}")
                    try:
                        shutil.copyfile(file_source, file_destination)
                    except Exception as e:
                        print(f"      error copying file: {e}") 

    import time
    time.sleep(2)



if __name__ == "__main__":
    # run the function
    load_parts()    
    
