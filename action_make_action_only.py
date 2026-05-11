import copy
import working_scad

def main(**kwargs):
    kwargs["run_oomp_populate"] = True

    kwargs["run_oomp"] = True

    kwargs["run_action"] = True
    #kwargs["run_action"] = False

    kwargs["run_scad"] = False

    kwargs["generate_stl"] = False

    import working
    working.run(**kwargs)

if __name__ == '__main__':
    kwargs = {}
    main(**kwargs)