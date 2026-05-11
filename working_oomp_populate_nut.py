import copy


def generate(**kwargs):
    options = []

    current_taxonomy_1 = "hardware"
    current_taxonomy_2 = "nut"

    # 2020 t-nut and ball-spring - m3, m4, m5, m6
    if True:
        for size in ["m3", "m4", "m5", "m6"]:
            for variant in ["2020_t_nut", "2020_ball_spring"]:
                option = {}
                option["taxonomy_1"] = current_taxonomy_1
                option["taxonomy_2"] = current_taxonomy_2
                option["taxonomy_3"] = size
                option["taxonomy_4"] = variant
                options.append(copy.deepcopy(option))

    # standard nuts (no colour) - m1, m1_4, m1_5, m2, m2_5, m2_7, m3, m4, m5, m6, m8
    # variants: plain, flanged, locking, coupling
    if True:
        for size in ["m1", "m1_4", "m1_5", "m2", "m2_5", "m2_7", "m3", "m4", "m5", "m6", "m8"]:
            for variant in ["", "flanged", "locking", "coupling"]:
                option = {}
                option["taxonomy_1"] = current_taxonomy_1
                option["taxonomy_2"] = current_taxonomy_2
                option["taxonomy_3"] = size
                option["taxonomy_4"] = variant
                options.append(copy.deepcopy(option))

    # cage nuts - m5, m6, m8
    if True:
        for size in ["m5", "m6", "m8"]:
            option = {}

            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = size
            option["taxonomy_4"] = "cage"
            options.append(copy.deepcopy(option))

    # black nuts - m3
    if True:
        for size in ["m3"]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = size
            option["taxonomy_4"] = "black"
            options.append(copy.deepcopy(option))

    # nylon white nuts - m3, m4, m5, m6, m8
    if True:
        for size in ["m3", "m4", "m5", "m6", "m8"]:
            option = {}
            option["taxonomy_1"] = current_taxonomy_1
            option["taxonomy_2"] = current_taxonomy_2
            option["taxonomy_3"] = size
            option["taxonomy_4"] = "nylon_white"
            options.append(copy.deepcopy(option))

    return options


if __name__ == "__main__":
    for o in generate():
        print(o)
