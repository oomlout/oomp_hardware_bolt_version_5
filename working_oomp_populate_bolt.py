import copy


def generate(**kwargs):
    options = []

    current_taxonomy_1 = "hardware"
    current_taxonomy_2 = "bolt"

    # m4
    if True:
        for length in [40]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = "m4"
            option["taxonomy_4"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    # m5
    if True:
        for length in [35, 40, 45, 60, 65, 70]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = "m5"
            option["taxonomy_4"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    # m6
    if True:
        for length in [25, 30, 35, 40, 45, 50, 60, 65, 70, 75, 80, 90, 100, 110, 120]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2            
            option["taxonomy_3"] = "m6"
            option["taxonomy_4"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    # m8
    if True:
        for length in [30, 35, 40, 45, 50, 60, 65, 70, 75, 80, 90, 95, 100, 110, 120, 130, 140, 150]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = "m8"
            option["taxonomy_4"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    return options


if __name__ == "__main__":
    for o in generate():
        print(o)
