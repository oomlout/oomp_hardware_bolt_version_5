import copy

from oomp_populate_helper import write_extras, build_oomp_id
from working_oomp_populate_bolt import generate as generate_bolt
from working_oomp_populate_set_screw import generate as generate_set_screw
from working_oomp_populate_nut import generate as generate_nut



def main(**kwargs):
    
    options = []
    options.extend(generate_bolt())
    options.extend(generate_set_screw())
    options.extend(generate_nut())

    extras = []
    for option in options:
        extra = {}
        extra.update(option)
        extras.append(copy.deepcopy(extra))

    ######### add notes from an id string
    import working_oomp_populate_extra_detail
    working_oomp_populate_extra_detail.main(extras=extras)

    write_extras(extras)


# Call main automatically
if __name__ == "__main__":
    main()