

def main(**kwargs):
    filters_to_run = kwargs.get("filters_to_run", [])
    filters_within_directory = kwargs.get("filters_within_directory", {})
    filter_part_name = kwargs.get("filter_part_name", "")
    directory_base = "parts"


    #if filters to run is a string make it an array
    if filters_to_run and isinstance(filters_to_run, str):
        filters_to_run = [filters_to_run]
    if "all" in filters_to_run:
        #get all the names from filters_within_directory
        filters_to_run = list(filters_within_directory.keys())
        
    files_to_delete = []
    for filters_name in filters_to_run:
        filters = filters_within_directory.get(filters_name, [])
        #if filters isn't an array make it one
        if filters and isinstance(filters, str):
            filters = [filters]
        for filter in filters:
            filter_items = filter
            #if filter_items isn't an array make it one
            if filter_items and isinstance(filter_items, str):
                filter_items = [filter_items]
            #add part name to only include them
            if filter_part_name != "":
                filter_items.append(filter_part_name)
            import os            
            folders = os.listdir(directory_base)
            for folder in folders:
                directory = os.path.join(directory_base, folder)
                if os.path.isdir(directory):
                    files = os.listdir(directory)
                    for file in files:
                        flename_full = os.path.join(directory, file)
                        #if all elements in filters are in the filename full
                        if all(elem in flename_full for elem in filter_items):
                            print(f"    deleting {flename_full}")
                            files_to_delete.append(flename_full)
    #if files to delete are there
    if len(files_to_delete) > 0:
        #check if it's oklay to delete    
        result = input(f"are you sure you want to delete these {len(files_to_delete)} files? (y/n)")
        if result.lower() == "y":
            for file in files_to_delete:
                os.remove(file)
                print(f"    deleted {file}")
    else:
        print("no files to delete")
