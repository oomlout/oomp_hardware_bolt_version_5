"""Rod matrix, long-stock export policy, cache migration and standalone rebuilds."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hardware_model_recipe import definition
from working_oomp_populate_threaded_rod import generate
import working_three_d_model as models


def rod(size, length):
    recipe, reason = definition(dict(taxonomy_1='hardware', taxonomy_2='threaded_rod',
                                    taxonomy_3=size, taxonomy_7=f'{length}_mm_length'))
    assert recipe, reason
    return recipe


def test_requested_matrix_and_export_formats():
    options = generate()
    assert len(options) == 47
    actual = {(p['taxonomy_3'], p['taxonomy_7']) for p in options}
    requested = {(f'm{size}', f'{length}_mm_length') for size in [3,4,5,6,8]
                 for length in [50,100,150,300,1000]}
    assert requested <= actual and len(requested) == 25
    for size, token in requested:
        length = int(token.split('_')[0])
        recipe = rod(size, length)
        assert recipe['model_formats'] == (['glb'] if length >= 300 else ['stl','glb'])
        assert recipe['parameters']['length_mm'] == length
        assert recipe['parameters']['family'] == 'rod'


def test_long_build_cache_and_standalone_never_export_stl(tmp_path, monkeypatch):
    from hardware_model_geometry import export_mesh
    recipe = rod('m20', 300)
    folder = tmp_path/recipe['parameters']['identity']
    folder.mkdir()
    exported = []
    def checked_export(mesh, filename, *args):
        assert Path(filename).suffix != '.stl'
        exported.append(Path(filename).name)
        return export_mesh(mesh, filename, *args)
    def studio(meshes, parameters, recipe, output):
        for r in recipe['renders'].values():
            Image.new('RGB', (r['pixels'],r['pixels']), 'gray').save(output/r['file'])
        (output/'studio.blend').write_bytes(b'test scene')
        (output/'render_scene.json').write_text('{}')
    with patch('hardware_model_geometry.export_mesh', side_effect=checked_export), \
         patch('hardware_model_render.render_studio', side_effect=studio), \
         patch.object(models, '_fingerprint', return_value='test'):
        assert models.generate_assets(recipe, folder, force=True)
    assert sorted(exported) == ['model_display.glb','model_full.glb']
    output = folder/'three_d_model'
    before = {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in output.glob('render*.png')}
    # A complete old bundle can be migrated without touching its renders.
    for p in [folder/'3dpr.stl',output/'model_full.stl',output/'model_display.stl']:
        p.write_bytes(b'obsolete')
    old = copy.deepcopy(recipe)
    old['model_formats'] = ['stl','glb']
    with patch('hardware_model_geometry.export_mesh', side_effect=AssertionError('cached build')):
        assert not models.generate_assets(old, folder)
    assert not list(folder.rglob('*.stl'))
    assert before == {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in output.glob('render*.png')}
    manifest = json.loads((output/'manifest.json').read_text())
    for name, entry in manifest['artifacts'].items():
        assert not name.endswith('.stl')
        assert hashlib.sha256((output/name).read_bytes()).hexdigest() == entry['sha256']
    standalone = tmp_path/'standalone'
    subprocess.run([sys.executable,str(output/'model.py'),'--variant','display','--length','1000',
                    '--output',str(standalone)],check=True,capture_output=True)
    assert (standalone/'model_display.glb').is_file()
    assert not list(standalone.glob('*.stl'))
    import hardware_rod_scad
    monkeypatch.chdir(tmp_path)
    hardware_rod_scad.generate(dict(id=folder.name,three_d_model_details=old),generate_stl=True)
    assert (tmp_path/'parts'/folder.name/'3dpr.scad').is_file()
    assert not list((tmp_path/'parts').rglob('*.stl'))


def test_population_filter():
    import working_oomp_populate as population
    with patch.object(population, 'write_extras') as writer:
        population.main(filter='hardware_threaded_rod_m[34568]_*')
    parts = writer.call_args.args[0]
    assert len(parts) == 25
    assert all(p['oobb_details']['oobb_name'] == 'threaded_rod' for p in parts)
    assert all(len(p['svg_details']) == 2 for p in parts)
