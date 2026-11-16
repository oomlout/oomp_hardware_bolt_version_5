import argparse

def main(**kwargs):
    kwargs.setdefault("run_only_yaml", True)
    kwargs["run_oomp_populate"] = True

    kwargs["run_oomp"] = True

    kwargs.setdefault("run_action", True)
    #kwargs["run_action"] = False

    kwargs["run_scad"] = True
    kwargs['run_svg'] = True

    kwargs["generate_stl"] = True

    import working
    working.run(**kwargs)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Regenerate definitions, OOMP, SCAD/STL, SVG/PDF and studio renders.')
    parser.add_argument('--filter', default='*', help='Part ID glob, e.g. hardware_threaded_rod_*')
    parser.add_argument('--jobs', dest='model_jobs', type=int, default=1, choices=range(1, 9))
    parser.add_argument('--skip-actions', dest='run_action', action='store_false', help='Skip interactive legacy Corel/roboclick actions')
    parser.add_argument('--skip-only-yaml', dest='run_only_yaml', action='store_false')
    parser.add_argument('--force', action='store_true', help='Refresh existing model outputs and studio renders')
    main(**vars(parser.parse_args()))
