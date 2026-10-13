"""Small real Blender render checks; catalogue output folders are never touched."""
import copy
import json
from pathlib import Path

from PIL import Image
import yaml

from working_three_d_model import ROOT, generate_assets

PARTS = [
    'hardware_nut_m6_locking', 'hardware_nut_m6_cage',
    'hardware_nut_m3_2020_ball_spring', 'hardware_nut_m5_2020_t_nut',
    'hardware_nut_m2_7', 'hardware_nut_m1_5_flanged',
    'hardware_nut_m3_coupling', 'hardware_washer_m1', 'hardware_washer_m2_penny',
]


def main():
    output = ROOT/'tmp/catalogue_extension_smoke'
    for part in PARTS:
        recipe = copy.deepcopy(yaml.safe_load((ROOT/'parts'/part/'working.yaml').read_text(encoding='utf-8'))['three_d_model_details'])
        for render in recipe['renders'].values():
            render['pixels'] = 128
        recipe['studio'].update(low_samples=4, high_samples=4)
        folder = output/part
        generate_assets(recipe, folder, force=True)
        for render in recipe['renders'].values():
            with Image.open(folder/'three_d_model'/render['file']) as im:
                assert im.size == (128, 128)
                assert any(lo != hi for lo, hi in im.getextrema())
        scene = json.loads((folder/'three_d_model/render_scene.json').read_text())
        assert all(p['ground_clearance_mm'] >= -1e-6 for p in scene['poses'].values())
        print('PASS '+part, flush=True)
    print(f'{len(PARTS)} real Blender smoke tests passed (4 renders each).', flush=True)


if __name__ == '__main__':
    main()
