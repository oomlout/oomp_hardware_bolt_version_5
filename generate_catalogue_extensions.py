"""Build the 45 additional catalogue models, preserving existing renders by default."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

import yaml

from working_three_d_model import ROOT, _generate_one


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, default=1, choices=range(1, 9))
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    tasks = []
    for path in sorted((ROOT/'parts').glob('*/working.yaml')):
        recipe = yaml.safe_load(path.read_text(encoding='utf-8')).get('three_d_model_details', {})
        if recipe.get('source_table') == 'source_file/standards/catalogue_extensions.yaml':
            tasks.append((recipe, path.parent, args.force))
    failures = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(_generate_one, task):task[1].name for task in tasks}
        for future in as_completed(futures):
            try:
                name, changed = future.result()
                print(f'{"generated" if changed else "cached"}: {name}', flush=True)
            except Exception as exc:
                failures.append(futures[future])
                print(f'FAILED {futures[future]}: {exc}', flush=True)
    print(f'Extension builds: {len(tasks)-len(failures)}/{len(tasks)} complete', flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
