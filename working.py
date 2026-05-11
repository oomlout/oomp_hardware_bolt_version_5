import copy

def main(**kwargs):
    run_oomp_populate = kwargs.get("run_oomp_populate", True)
    #run_oomp_populate = False
    kwargs["run_oomp_populate"] = run_oomp_populate

    run_oomp = kwargs.get("run_oomp", True)
    #run_oomp = False
    kwargs["run_oomp"] = run_oomp

    run_scad = kwargs.get("run_scad", True)
    #run_scad = False
    kwargs["run_scad"] = run_scad

    run_action = kwargs.get("run_action", True)
    #run_action = False
    kwargs["run_action"] = run_action

    generate_stl = kwargs.get("generate_stl", False)
    #generate_stl = True
    kwargs["generate_stl"] = generate_stl

    run(**kwargs)

def run(**kwargs):

    if kwargs.get("run_oomp_populate", True):
        import working_oomp_populate
        working_oomp_populate.main(**kwargs)

    if kwargs.get("run_oomp", True):
        import working_oomp
        working_oomp.main(**kwargs)

    if kwargs.get("run_scad", True):        
        kwargs2 = copy.deepcopy(kwargs)
        if kwargs.get("generate_stl", False):
            kwargs2["typ"] = "all"
        import working_scad
        working_scad.main(**kwargs2)

    if kwargs.get("run_action", True):
        import working_action
        working_action.main(**kwargs)    




if __name__ == '__main__':
    kwargs = {}
    main(**kwargs)