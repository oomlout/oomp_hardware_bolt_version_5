"""Persisted studio settings and a headless Blender/Cycles render bridge."""
import copy
from functools import lru_cache
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def presentation_defaults(finish='satin', family='bolt', elongated=False):
    black = finish == 'black'
    defaults = dict(
        material=dict(name='Black oxide steel' if black else 'Satin steel',
            base_colour_srgb=[.205, .218, .235] if black else [.62, .65, .69],
            metallic=.8 if black else 1., roughness=.31 if black else .26,
            roughness_variation=.045, coat_weight=.08 if black else .02,
            coat_roughness=.28, microtexture_spacing_mm=.025,
            microtexture_height_um=.8, note='Visual finish approximation; catalogue specifies colour only.'),
        studio=dict(engine='cycles', device='auto', seed=7991,
            low_samples=48, high_samples=160, adaptive_threshold=.015,
            denoise=True, view_transform='AgX', look='AgX - Medium High Contrast', exposure=0.,
            world_colour=[.78, .82, .9], world_strength=.35,
            floor_colour_srgb=[.93, .935, .94], floor_roughness=.55,
            framing_margin=.13,
            lights=[dict(name='Key softbox', position=[-3, -4, 6],
                         power=650., width=4., height=5., colour=[1., .96, .9]),
                    dict(name='Fill softbox', position=[4, -1, 3],
                         power=330., width=3., height=4., colour=[.9, .95, 1.]),
                    dict(name='Rim strip', position=[1, 4, 4],
                         power=850., width=1.2, height=5., colour=[1., 1., 1.])],
            poses=dict(isometric=dict(camera_eye=[1, -1, 1], projection='orthographic',
                                      orientation='tip down, head up'),
                       product=dict(camera_eye=[-6, -10, 6], projection='orthographic',
                                    orientation='lying on side, head to left', yaw_degrees=-12.,
                                    support='Stable convex-hull support using actual mesh centre of mass.'))),
        renders=dict(low=dict(file='render_low.png', variant='display', pixels=512, view='isometric'),
                     high=dict(file='render_high.png', variant='full', pixels=2048, view='isometric'),
                     product_low=dict(file='render_product_low.png', variant='display', pixels=512, view='product'),
                     product_high=dict(file='render_product_high.png', variant='full', pixels=2048, view='product')))
    defaults['studio']['poses']['isometric']['orientation'] = 'principal axis Z up'
    defaults['studio']['poses']['product'].update(
        resting_axis='side' if family == 'bolt' or elongated else 'face',
        orientation='lying on side, axial end to left' if family == 'bolt' or elongated else 'resting on lower face, bore visible')
    if finish == 'nylon_white':
        defaults['material'].update(name='Natural white nylon', base_colour_srgb=[.86, .85, .81],
            metallic=0., roughness=.38, roughness_variation=.025, coat_weight=.025,
            microtexture_height_um=.4, note='Visual natural nylon approximation; exact polymer grade and mould surface not supplied by catalogue.')
    return defaults


def upgrade_presentation(recipe):
    """Add presentation fields without resetting saved geometry or user settings."""
    result = copy.deepcopy(recipe)
    p = recipe['parameters']
    defaults = presentation_defaults(p['finish'], p['family'], recipe['generator'] == 'supplier_coupling_nut')
    def fill(existing, source):
        for key, value in source.items():
            if key not in existing:
                existing[key] = copy.deepcopy(value)
            elif isinstance(existing[key], dict) and isinstance(value, dict):
                fill(existing[key], value)
    fill(result, defaults)
    return result


@lru_cache(maxsize=1)
def blender_executable():
    configured = os.environ.get('OOMP_BLENDER_EXE')
    if configured:
        path = Path(configured)
        if not path.is_file():
            raise FileNotFoundError(f'OOMP_BLENDER_EXE not found: {configured}')
        return path
    available = shutil.which('blender')
    if available:
        return Path(available)
    candidates = list((Path(os.environ.get('ProgramFiles', 'C:/Program Files'))/
                       'Blender Foundation').glob('Blender */blender.exe'))
    candidates += [Path('/Applications/Blender.app/Contents/MacOS/Blender')]
    existing = sorted((p for p in candidates if p.is_file()), reverse=True)
    if existing:
        import re
        return max(existing, key=lambda p: tuple(int(v) for v in re.findall(r'\d+', str(p.parent.name))))
    raise FileNotFoundError('Studio rendering requires Blender 4.5 or newer. Install Blender, '
                            'add it to PATH, or set OOMP_BLENDER_EXE to its executable.')


def renderer_identity():
    path = blender_executable()
    stat = path.stat()
    result = subprocess.run([str(path), '--version'], capture_output=True, text=True, encoding='utf-8')
    import re
    match = re.search(r'Blender (\d+)\.(\d+)', result.stdout)
    if result.returncode or not match or tuple(map(int, match.groups())) < (4, 5):
        raise RuntimeError('Studio rendering requires Blender 4.5 or newer')
    return dict(executable=str(path), size=stat.st_size, modified_ns=stat.st_mtime_ns,
                version=result.stdout.splitlines()[0])


def render_studio(meshes, p, recipe, output):
    """Transfer mesh geometry with sharp-edge normals; render all poses in one process."""
    import math
    import numpy as np
    import trimesh
    from hardware_model_pose import product_pose
    output = Path(output)
    transfer = output/'_render_meshes.npz'
    arrays = {}
    for variant, mesh in meshes.items():
        shaded = trimesh.graph.smooth_shade(mesh, angle=math.pi/5)
        arrays[f'{variant}_vertices'] = shaded.vertices
        arrays[f'{variant}_faces'] = shaded.faces
        arrays[f'{variant}_normals'] = shaded.vertex_normals
    np.savez(transfer, **arrays)
    job = output/'_render_job.json'
    product_transforms, product_supports = {}, {}
    for variant, mesh in meshes.items():
        transform, support = product_pose(mesh, recipe['studio']['poses']['product'])
        product_transforms[variant] = transform.tolist()
        product_supports[variant] = support
    job.write_text(json.dumps(dict(parameters=p, material=recipe['material'],
        studio=recipe['studio'], renders=recipe['renders'], output=str(output.resolve()),
        product_transforms=product_transforms, product_supports=product_supports,
        meshes=str(transfer.resolve())), indent=2), encoding='utf-8')
    command = [str(blender_executable()), '--background', '--factory-startup',
               '--python-exit-code', '1', '--python', str(ROOT/'hardware_model_blender.py'),
               '--', str(job.resolve())]
    # Captured output keeps catalogue logs readable; failures retain useful diagnostics.
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(f'Blender studio rendering failed ({result.returncode}):\n'
                           f'{(result.stdout + result.stderr)[-12000:]}')
    missing = [r['file'] for r in recipe['renders'].values() if not (output/r['file']).is_file()]
    if missing or not (output/'studio.blend').is_file() or not (output/'render_scene.json').is_file():
        raise RuntimeError(f'Blender did not produce the complete studio asset set: {missing}')
    transfer.unlink()
    job.unlink()
