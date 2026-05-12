import copy


def generate(**kwargs):
    options = []

    current_taxonomy_1 = "hardware"
    current_taxonomy_2 = "washer"

    # standard washers (no variant) - m1, m1_5, m2, m2_5, m2_7, m3, m4, m5, m6, m8
    if True:
        for size in ["m1", "m1_5", "m2", "m2_5", "m2_7", "m3", "m4", "m5", "m6", "m8"]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = size
            option["taxonomy_4"] = ""
            options.append(copy.deepcopy(option))

    # penny washers - m1, m1_5, m2, m2_5, m2_7, m3, m4, m5, m6, m8
    if True:
        for size in ["m1", "m1_5", "m2", "m2_5", "m2_7", "m3", "m4", "m5", "m6", "m8"]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = size
            option["taxonomy_4"] = "penny"
            options.append(copy.deepcopy(option))

    # nylon white washer - m6 12mm outer diameter 1.5mm depth
    if True:
        option = {}
        option["taxonomy_1"] = current_taxonomy_1
        option["taxonomy_2"] = current_taxonomy_2
        option["taxonomy_3"] = "m6"
        option["taxonomy_4"] = "nylon_white_12_mm_outer_diameter_1_5_mm_depth"
        options.append(copy.deepcopy(option))

    return options


if __name__ == "__main__":
    for o in generate():
        print(o)
