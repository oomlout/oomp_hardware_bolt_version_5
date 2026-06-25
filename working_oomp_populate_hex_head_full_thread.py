import copy


def generate(**kwargs):
    options = []

    current_taxonomy_1 = "hardware"
    current_taxonomy_2 = "screw"
    current_taxonomy_3 = "hex_head"
    current_taxonomy_4 = "full_thread"

    sizes = {
        "m3":  [6, 8, 10, 12, 16, 20, 25, 30],
        "m4":  [6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 50],
        "m5":  [8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50],
        "m6":  [10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80],
        "m8":  [12, 16, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80],
        "m10": [20, 25, 30, 35, 40, 50, 60, 70, 80],
        "m12": [25, 30, 35, 40, 50, 60, 70, 80],
    }

    for size, lengths in sizes.items():
        for length in lengths:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = current_taxonomy_3
            option["taxonomy_4"] = current_taxonomy_4
            option["taxonomy_5"] = ""
            option["taxonomy_6"] = f"{size}_diameter"
            option["taxonomy_7"] = f"{length}_mm_length"
            options.append(copy.deepcopy(option))

    return options


if __name__ == "__main__":
    for o in generate():
        print(o)
