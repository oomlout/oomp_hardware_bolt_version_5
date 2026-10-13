"""New catalogue rows retain nominal identity, closed components and insert materials."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import trimesh
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hardware_model_recipe import definition
from hardware_model_geometry import build_model, export_mesh
from hardware_model_pose import product_pose

ROOT = Path(__file__).resolve().parents[1]
ROWS = []
for family, table in yaml.safe_load((ROOT/'source_file/standards/catalogue_extensions.yaml').read_text())['families'].items():
    for size in table['sizes']:
        kind = 'washer' if 'washer' in family else 'nut'
        variant = {'hex_nut':'', 'plain_washer':'', 'penny_washer':'penny', 'coupling_nut':'coupling',
                   'flange_nut':'flanged', 'locking_nut':'locking', 'cage_nut':'cage',
                   't_nut':'2020_t_nut', 'ball_spring_nut':'2020_ball_spring'}[family]
        ROWS.append((kind, size, variant))


@pytest.mark.parametrize('kind,size,variant', ROWS)
def test_extension_solids_and_support(kind, size, variant, tmp_path):
    r, reason = definition(dict(taxonomy_2=kind, taxonomy_3='m'+size.replace('.', '_'), taxonomy_4=variant))
    assert r, reason
    p = r['parameters']
    assert p['nominal_diameter_mm'] == float(size)
    meshes = [build_model(p, v, r['variants'][v]) for v in ['full', 'display']]
    np.testing.assert_allclose(meshes[0].extents, meshes[1].extents, atol=2e-5)
    assert len(meshes[1].faces) < len(meshes[0].faces)/2
    for mesh in meshes:
        assert mesh.is_volume and mesh.body_count == p['expected_components']
        export_mesh(mesh, tmp_path/'roundtrip.stl', p)
        reloaded = trimesh.load(tmp_path/'roundtrip.stl')
        assert reloaded.is_watertight
        np.testing.assert_allclose(reloaded.extents, mesh.extents, atol=2e-5)
        if p.get('nut_style') == 'cage_nut':
            assert mesh.extents[1] == pytest.approx(p['body_width_mm'], abs=2e-5)
        # Separate assembly components must not intersect one another.
        pieces = mesh.split()
        for i, piece in enumerate(pieces):
            for other in pieces[i+1:]:
                overlap = trimesh.boolean.intersection([piece, other], engine='manifold')
                assert not len(overlap.faces) or overlap.volume < 1e-7
        _, support = product_pose(mesh, r['studio']['poses']['product'])
        assert support['centre_inside_support']
    if r['dimension_status'] == 'approximate_visual_model':
        assert r['standard'] is None
        assert p['specification'].startswith('APPROXIMATE VISUAL MODEL:')
        assert r['modelling_choices']['family_note']


def test_nylon_insert_glb_material_and_bore(tmp_path):
    r, _ = definition(dict(taxonomy_2='nut', taxonomy_3='m6', taxonomy_4='locking'))
    mesh = build_model(r['parameters'], 'display')
    export_mesh(mesh, tmp_path/'nut.glb', r['parameters'], r['material'])
    scene = trimesh.load(tmp_path/'nut.glb', force='scene')
    assert len(scene.geometry) == 2
    materials = {g.visual.material.name:g.visual.material for g in scene.geometry.values()}
    assert materials['Blue nylon insert'].metallicFactor == 0
    np.testing.assert_allclose(scene.extents, mesh.extents[[0,2,1]]*.001, atol=2e-8)
    for piece in mesh.split():
        section = piece.section(plane_origin=[0,0,piece.bounds[:,2].mean()], plane_normal=[0,0,1])
        assert len(section.discrete) == 2
