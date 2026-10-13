"""Independent hardware dimension, cavity, serialization and workflow checks."""
import copy
from contextlib import redirect_stdout
import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from unittest.mock import patch

import numpy as np
from PIL import Image
import pytest
import trimesh
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import working_three_d_model as models
from hardware_model_geometry import build_model, export_mesh, resolve_parameters, internal_thread_radius, thread_depth
from hardware_model_pose import product_pose
from hardware_model_render import upgrade_presentation
from hardware_model_views import camera_basis, svg_lines
from hardware_model_recipe import definition

ROOT = models.ROOT


def recipe(typ='set_screw', d='m3', variant='', length=8, material=''):
    value = dict(taxonomy_1='hardware', taxonomy_2=typ, taxonomy_3=d,
        taxonomy_4=f'{length}_mm_length' if typ == 'bolt' else variant,
        taxonomy_5=material, taxonomy_7=f'{length}_mm_length')
    result, reason = definition(value)
    assert result, reason
    return result


@pytest.mark.parametrize('r', [recipe('bolt', 'm4', length=40), recipe('bolt','m8',length=150),
    recipe(), recipe('set_screw','m8',length=150), recipe('set_screw','m6',length=15,material='nylon_white'), recipe('nut','m1'),
    recipe('nut','m8'), recipe('nut','m3','flanged'), recipe('nut','m8','flanged'),
    recipe('nut','m8','coupling'), recipe('nut','m6','nylon_white'),
    recipe('washer','m2'), recipe('washer','m8','penny'),
    recipe('washer','m6','nylon_white_12_mm_outer_diameter_1_5_mm_depth')])
def test_dimensions_cavities_and_detail_reduction(r):
    p = resolve_parameters(r['parameters'])
    full, display = [build_model(p, variant, r['variants'][variant]) for variant in ['full','display']]
    np.testing.assert_allclose(full.extents, display.extents, atol=2e-5)
    assert len(display.faces) < len(full.faces)/2
    for mesh in [full,display]:
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.body_count == 1
        assert mesh.volume > 0
        assert mesh.bounds[0,2] == pytest.approx(0, abs=1e-6)
        assert mesh.extents[2] == pytest.approx(p['overall_height_mm'], abs=2e-5)
        if p['family']=='bolt':
            # Across flats evaluated below the circular top chamfer, above bearing.
            section = mesh.section(plane_origin=[0,0,p['length_mm']+p['head_height_mm']/2], plane_normal=[0,0,1])
            assert np.ptp(section.discrete[0][:,1]) == pytest.approx(p['across_flats_mm'],abs=2e-5)
            if p['thread_mode']=='partial':
                section = mesh.section(plane_origin=[0,0,(p['thread_end_z_mm']+p['length_mm']-p['underhead_fillet_mm'])/2], plane_normal=[0,0,1])
                assert np.ptp(section.discrete[0][:,0]) == pytest.approx(p['nominal_diameter_mm'],abs=2e-5)
        else:
            section = mesh.section(plane_origin=[0,0,p['height_mm']/2], plane_normal=[0,0,1])
            assert len(section.discrete)==2  # Actual bore, not a surface marking.
            hole = min(section.discrete, key=lambda points: np.ptp(points[:,0]))
            radii = np.linalg.norm(hole[:,:2],axis=1)
            if p['family']=='washer':
                assert mesh.extents[0] == pytest.approx(p['outer_diameter_mm'],abs=2e-5)
                assert radii.max()*2 == pytest.approx(p['hole_diameter_mm'],abs=2e-5)
                expected_volume=math.pi/4*(p['outer_diameter_mm']**2-p['hole_diameter_mm']**2)*p['height_mm']
                assert mesh.volume == pytest.approx(expected_volume,rel=.013)
            else:
                assert radii.min()*2 >= p['internal_minor_diameter_mm']*.98
                assert radii.max()*2 <= p['nominal_diameter_mm']+2e-5
                if mesh is full:
                    assert np.ptp(radii) > p['pitch_mm']*.3
                else:
                    assert np.ptp(radii) < p['pitch_mm']*.025
    for mesh in [full, display]:
        transform, support = product_pose(mesh,r['studio']['poses']['product'])
        points = trimesh.transform_points(mesh.vertices,transform)
        assert points[:,2].min() == pytest.approx(0,abs=1e-6)
        assert support['centre_inside_support'] and support['stability_margin_mm'] >= 0
        if r['studio']['poses']['product']['resting_axis']=='side':
            assert abs(support['principal_axis_world'][2])<.3
        else:
            assert support['principal_axis_world'][2] == pytest.approx(1)


def test_source_scope_length_and_materials():
    bolt=recipe('bolt','m8',length=150)
    assert bolt['standard_limits']['product_grade']=='B'
    p=resolve_parameters(bolt['parameters'])
    assert p['thread_length_mm']==28
    assert p['overall_height_mm']==155.3
    assert recipe('bolt','m8',length=95)['length_status'].startswith('catalogue_length')
    assert recipe('nut','m3','flanged')['dimension_status']=='manufacturer_extension'
    assert recipe('nut','m8','flanged')['dimension_status']=='standard_dimensions'
    assert recipe('nut','m8','coupling')['standard'] is None
    assert recipe('nut','m6','nylon_white')['parameters']['height_mm']==5
    assert recipe('nut','m6')['parameters']['height_mm']==5.2
    assert recipe('nut','m6','nylon_white')['material']['metallic']==0
    assert recipe('nut','m3','black')['material']['base_colour_srgb']==[.205,.218,.235]
    for typ,d,variant in [('nut','m99','cage'),('nut','m99','locking'),('nut','m99',''),('washer','m99',''),('nut','m99','coupling')]:
        r,reason=definition(dict(taxonomy_2=typ,taxonomy_3=d,taxonomy_4=variant))
        assert r is None and reason


def test_right_handed_thread_profiles():
    pitch=.5
    assert float(thread_depth(.5,pitch))==pytest.approx(.613434661*pitch)
    p=recipe('nut','m3')['parameters']
    assert float(internal_thread_radius(0,p))*2==pytest.approx(3-1.0825317547*pitch)
    assert float(internal_thread_radius(.5,p))*2==pytest.approx(3)
    full=build_model(recipe()['parameters'])
    for point in [(1.5,0,2),(0,1.5,2.125)]:
        assert np.linalg.norm(full.vertices-point,axis=1).min()<.02


def test_stl_glb_units_axes_and_linear_colour(tmp_path):
    r=recipe('nut','m3','black');mesh=build_model(r['parameters'],'display')
    for suffix in ['stl','glb']:
        export_mesh(mesh,tmp_path/f'model.{suffix}',r['parameters'],r['material'])
    stl=trimesh.load(tmp_path/'model.stl')
    np.testing.assert_allclose(stl.extents,mesh.extents,atol=1e-5)
    glb=trimesh.load(tmp_path/'model.glb',force='scene')
    np.testing.assert_allclose(glb.extents,mesh.extents[[0,2,1]]*.001,atol=1e-8)
    data=(tmp_path/'model.glb').read_bytes();length=struct.unpack_from('<I',data,12)[0]
    tree=json.loads(data[20:20+length]);mat=tree['materials'][0]
    expected=[((v+.055)/1.055)**2.4 for v in r['material']['base_colour_srgb']]+[1]
    np.testing.assert_allclose(mat['pbrMetallicRoughness']['baseColorFactor'],expected)
    assert mat['pbrMetallicRoughness']['metallicFactor']==.8
    assert mat['pbrMetallicRoughness']['roughnessFactor']==.31
    assert 'KHR_materials_clearcoat' in tree['extensionsUsed']
    assert 'extensionsRequired' not in tree or 'KHR_materials_clearcoat' not in tree['extensionsRequired']


def test_isometric_and_hidden_line_depth_buffer(tmp_path):
    np.testing.assert_allclose(np.linalg.norm(camera_basis('isometric')[:,:2],axis=1),math.sqrt(2/3))
    # An occluded recess on the far face must not be visible from below.
    box=trimesh.creation.box([10,10,3]);box.apply_translation([0,0,1.5])
    cutter=trimesh.creation.cylinder(radius=1.5,height=2,sections=24);cutter.apply_translation([0,0,3])
    mesh=trimesh.boolean.difference([box,cutter],engine='manifold')
    p=recipe('washer','m3')['parameters']
    svg_lines(mesh,p,'display','bottom',tmp_path/'bottom.svg',256)
    root=ET.parse(tmp_path/'bottom.svg').getroot();ns='{http://www.w3.org/2000/svg}'
    assert root.get('width').endswith('mm')
    assert 'DIN 7991' not in root.find(ns+'title').text
    import re
    xy=np.array([float(v) for v in re.findall(r'-?\d+\.\d+',root.find('.//'+ns+'path').get('d'))]).reshape(-1,2)
    assert np.abs(xy).max(axis=1).min()>4.9


def test_targeted_yaml_and_recursive_presentation_upgrade(tmp_path):
    path=tmp_path/'working.yaml'
    original='name: café\r\n# Keep original comment\r\ncustom: &ref\r\n  value: 7\r\ncopy: *ref\r\n\r\n'
    path.write_bytes(original.encode('utf-8'))
    r=recipe();models.write_recipe(path,r)
    assert path.read_bytes().startswith(original.encode('utf-8'))
    data=path.read_bytes();models.write_recipe(path,r);assert path.read_bytes()==data
    r['parameters']['length_mm']=9.25;r['material']['roughness']=.42
    del r['studio']['look'];del r['studio']['poses']['product'];del r['renders']['product_high']
    upgraded=upgrade_presentation(r)
    assert upgraded['parameters']==r['parameters']
    assert upgraded['material']['roughness']==.42
    assert upgraded['studio']['look']=='AgX - Medium High Contrast'
    assert upgraded['renders']['product_high']['pixels']==2048
    assert 'look' not in r['studio']


def test_cache_damage_and_standalone_from_folder_with_spaces(tmp_path):
    r=recipe('washer','m2');folder=tmp_path/'part with spaces';folder.mkdir()
    def fake_studio(meshes,p,r,out):
        for render in r['renders'].values():
            if (out/render['file']).is_file():
                continue
            Image.new('RGB',(render['pixels'],render['pixels']),color='white').save(out/render['file'])
        (out/'studio.blend').write_bytes(b'fixture')
        (out/'render_scene.json').write_text('{}',encoding='utf-8')
    with patch('hardware_model_render.render_studio',side_effect=fake_studio) as renderer:
        assert models.generate_assets(r,folder)
        output=folder/'three_d_model';manifest=json.loads((output/'manifest.json').read_text())
        assert len(manifest['artifacts'])==28
        assert 'model_notes.md' in manifest['artifacts']
        assert not models.generate_assets(r,folder)
        existing={path.name:(path.read_bytes(),path.stat().st_mtime_ns) for path in output.glob('render*.png')}
        changed_recipe=copy.deepcopy(r);changed_recipe['studio']['exposure']=1.
        with patch.object(models,'_fingerprint',side_effect=AssertionError('No Blender/cache probe expected')):
            assert not models.generate_assets(changed_recipe,folder)
        (output/'render_low.png').unlink()
        assert models.generate_assets(r,folder)
        for name,snapshot in existing.items():
            if name!='render_low.png':
                assert ((output/name).read_bytes(),(output/name).stat().st_mtime_ns)==snapshot
        assert renderer.call_count==2
        (output/'full/top.svg').unlink()
        assert models.generate_assets(r,folder)
        assert renderer.call_count==2
        (output/'render_low.png').write_bytes(b'corrupt')
        assert not models.generate_assets(r,folder)
        assert models.generate_assets(r,folder,force=True)
        assert renderer.call_count==3
        assert Image.open(output/'render_low.png').size==(512,512)
    subprocess.run([sys.executable,str(output/'model.py'),'--output',str(tmp_path/'standalone result')],
        cwd=tmp_path,check=True,capture_output=True)
    np.testing.assert_allclose(trimesh.load(tmp_path/'standalone result/model_full.stl').extents,[5,5,.3],atol=1e-6)
    assert not list(output.glob('.build-*'))


def test_population_and_every_saved_display_recipe():
    import working_oomp_populate as population
    with patch.object(population,'write_extras') as writer:
        population.main()
    assert sum('three_d_model_details' in p for p in writer.call_args.args[0])==207
    supported=0
    for path in (ROOT/'parts').glob('*/working.yaml'):
        part=yaml.safe_load(path.read_text(encoding='utf-8'))
        r=part.get('three_d_model_details')
        source=yaml.safe_load((ROOT/'parts_source'/path.parent.name/'working.yaml').read_text(encoding='utf-8'))
        assert source.get('three_d_model_details')==r
        if r:
            supported+=1
            mesh=build_model(r['parameters'],'display',r['variants']['display'])
            assert mesh.body_count==r['parameters']['expected_components'] and mesh.is_watertight
            assert all('url' in s or 'path' in s for s in r['sources'])
    assert supported==207


@pytest.mark.skipif(os.name!='nt',reason='Windows shortcut checks')
def test_windows_batch_external_cwd_spaces_exit_code_and_disposable_delete(tmp_path):
    fixture=tmp_path/'repository with spaces';fixture.mkdir()
    for name in ['action_make_three_d_model.bat','action_delete_three_d_model.bat','action_delete_three_d_model.ps1']:
        shutil.copyfile(ROOT/name,fixture/name)
    stub="import json,sys\nfrom pathlib import Path\nPath(__file__).with_name('argv.json').write_text(json.dumps(sys.argv[1:]))\nsys.exit(23)\n"
    (fixture/'working_three_d_model.py').write_text(stub,encoding='utf-8')
    result=subprocess.run(['cmd.exe','/d','/c',str(fixture/'action_make_three_d_model.bat'),'--metadata-only','--filter','no_matching_parts'],cwd=tmp_path,capture_output=True)
    assert result.returncode==23
    argv=json.loads((fixture/'argv.json').read_text());assert argv[:5]==['--filter','*','--jobs','3','--update-presentation'];assert '--force' not in argv
    assert argv[-3:]==['--metadata-only','--filter','no_matching_parts']
    part=fixture/'parts/product';output=part/'three_d_model';output.mkdir(parents=True)
    (part/'working.yaml').write_text('name: keep\n',encoding='utf-8');(part/'legacy.stl').write_bytes(b'keep')
    (output/'model.stl').write_bytes(b'remove')
    result=subprocess.run(['powershell.exe','-NoProfile','-File',str(fixture/'action_delete_three_d_model.ps1'),'-WhatIf'],cwd=tmp_path,capture_output=True)
    assert result.returncode==0 and output.exists()
    result=subprocess.run(['powershell.exe','-NoProfile','-File',str(fixture/'action_delete_three_d_model.ps1')],cwd=tmp_path,capture_output=True)
    assert result.returncode==0 and not output.exists()
    assert (part/'working.yaml').read_text()=='name: keep\n' and (part/'legacy.stl').read_bytes()==b'keep'


def test_bad_geometry_fails():
    p=recipe()['parameters'];p['length_mm']=.2
    with pytest.raises(ValueError):
        build_model(p)
    p=recipe('washer','m3')['parameters'];p['hole_diameter_mm']=100
    with pytest.raises(ValueError):
        build_model(p)


def test_metadata_is_lightweight_and_pipeline_stage_can_be_disabled():
    subprocess.run([sys.executable,'-c',
        "import sys,working_three_d_model;assert not {'numpy','trimesh','manifold3d','numba'} & set(sys.modules)"],
        cwd=ROOT,check=True,capture_output=True)
    import working
    with patch('working_three_d_model.main') as stage:
        working.run(run_oomp_populate=False,run_oomp=False,run_scad=False,run_svg=False,run_action=False,
                    run_three_d_model=False)
        stage.assert_not_called()
        working.run(run_oomp_populate=False,run_oomp=False,run_scad=False,run_svg=False,run_action=False,
                    run_three_d_model=True,model_jobs=3)
        assert stage.call_args.kwargs['model_jobs']==3
