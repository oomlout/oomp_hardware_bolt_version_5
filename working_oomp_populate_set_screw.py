import copy


def generate(**kwargs):
    options = []

    current_taxonomy_1 = "hardware"
    current_taxonomy_2 = "set_screw"

    # standard bzp set screws - m3
    if True:
        for length in [8, 10, 12, 16, 20, 25, 30]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = "m3"
            option["taxonomy_5"] = ""
            option["taxonomy_7"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    # standard bzp set screws - m4
    if True:
        for length in [8, 10, 12, 16, 20, 25, 30, 35, 40, 50]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2   
            option["taxonomy_3"] = "m4"
            option["taxonomy_5"] = ""
            option["taxonomy_7"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    # standard bzp set screws - m5
    if True:
        for length in [8, 10, 12, 14, 16, 20, 22, 25, 30, 35, 40, 45, 50, 60, 65, 70, 80]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = "m5"
            option["taxonomy_5"] = ""
            option["taxonomy_7"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    # standard bzp set screws - m6
    if True:
        for length in [8, 10, 12, 15, 16, 18, 20, 22, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = "m6"
            option["taxonomy_5"] = ""
            option["taxonomy_7"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    # standard bzp set screws - m8
    if True:
        for length in [10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100, 110, 120, 130, 140, 150]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = "m8"
            option["taxonomy_5"] = ""
            option["taxonomy_7"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    # nylon white set screws - m6
    if True:
        for length in [12, 15, 20, 25, 30, 50]:            
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = "m6"
            option["taxonomy_5"] = "nylon_white"
            option["taxonomy_7"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    return options


if __name__ == "__main__":
    for o in generate():
        print(o)
