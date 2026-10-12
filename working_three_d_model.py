"""Populate and generate sourced hardware solids and studio presentation assets."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

import yaml

from hardware_model_render import upgrade_presentation

ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = 1
from hardware_model_recipe import add_definition, definition, GENERATOR_NAMES


def write_recipe(path, recipe):
    """Replace just the top-level recipe, preserving all existing YAML blocks."""
    path = Path(path)
    with path.open(encoding='utf-8', newline='') as stream:
        original = stream.read()
    block = yaml.safe_dump({'three_d_model_details': recipe}, sort_keys=False, allow_unicode=True)
    if '\r\n' in original:
        block = block.replace('\n', '\r\n')
    pattern = r'^three_d_model_details:.*?(?=^\S|\Z)'
    text = re.sub(pattern, lambda _: block, original, flags=re.MULTILINE | re.DOTALL) if re.search(
        pattern, original, flags=re.MULTILINE | re.DOTALL) else original+('' if original.endswith('\n') else '\n')+block
    if text != original:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         suffix='.tmp', delete=False, newline='') as f:
            f.write(text)
            temp_path = Path(f.name)
        temp_path.replace(path)


def _fingerprint(recipe):
    digest = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode())
    for name in ['working_three_d_model.py', 'hardware_model_recipe.py', 'hardware_model_pose.py', 'source_file/standards/catalogue_hardware.yaml', 'hardware_model_geometry.py', 'hardware_model_views.py',
                 'hardware_model_render.py', 'hardware_model_blender.py', 'requirements-three-d-model.txt']:
        digest.update((ROOT/name).read_bytes())
    from hardware_model_render import renderer_identity
    digest.update(json.dumps(renderer_identity(), sort_keys=True).encode())
    from importlib.metadata import version
    for dependency in ['numpy', 'scipy', 'trimesh', 'manifold3d', 'Pillow', 'numba', 'PyYAML']:
        digest.update(f'{dependency}={version(dependency)}'.encode())
    return digest.hexdigest()


def generate_assets(recipe, folder, force=False):
    """Generate atomically; cache only a complete, verified artifact set."""
    recipe = upgrade_presentation(recipe)
    if recipe.get('schema_version') != SCHEMA_VERSION or recipe.get('generator') not in GENERATOR_NAMES.values():
        raise ValueError('Unsupported model recipe schema or generator')
    if recipe.get('output_folder') != 'three_d_model' or recipe.get('model_formats') != ['stl', 'glb']:
        raise ValueError('Unsupported output folder or model formats')
    if set(recipe['variants']) != {'full', 'display'}:
        raise ValueError('Both full and display variants are required')
    from hardware_model_geometry import build_model, export_mesh, resolve_parameters, GENERATORS
    from hardware_model_views import export_views, VIEWS
    from hardware_model_render import render_studio
    if recipe['views'] != list(VIEWS):
        raise ValueError('Unsupported view set')
    if GENERATORS[recipe['generator']] != recipe['parameters']['family']:
        raise ValueError('Generator and family disagree')
    render_files = [render['file'] for render in recipe['renders'].values()]
    if len(set(render_files)) != len(render_files) or any(
            Path(name).name != name or not name.lower().endswith('.png') for name in render_files):
        raise ValueError('Render filenames must be distinct PNG basenames')
    for render in recipe['renders'].values():
        if render['variant'] not in {'full', 'display'} or render['view'] not in {'isometric', 'product'}:
            raise ValueError('Unsupported render variant or camera')
        if not isinstance(render['pixels'], int) or render['pixels'] < 32:
            raise ValueError('Render pixels must be an integer >=32')
    output = Path(folder)/'three_d_model'
    output.mkdir(parents=True, exist_ok=True)
    fingerprint = _fingerprint(recipe)
    manifest_path = output/'manifest.json'
    if not force and manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            expected = {'model.py', 'parameters.json', 'requirements.txt', 'studio.blend', 'render_scene.json'}
            expected.update(f'model_{variant}.{suffix}' for variant in recipe['variants'] for suffix in recipe['model_formats'])
            expected.update(f'{variant}/{view}.svg' for variant in recipe['variants'] for view in recipe['views'])
            expected.update(render['file'] for render in recipe['renders'].values())
            if manifest['fingerprint'] == fingerprint and set(manifest['artifacts']) == expected and all(
                (output/name).is_file() and hashlib.sha256((output/name).read_bytes()).hexdigest() == info['sha256']
                and (output/name).stat().st_size == info['bytes']
                for name, info in manifest['artifacts'].items()):
                return False
        except (KeyError, ValueError, OSError):
            pass
    with tempfile.TemporaryDirectory(prefix='.build-', dir=output) as directory:
        stage = Path(directory)
        (stage/'parameters.json').write_text(json.dumps(recipe, indent=2, sort_keys=True)+'\n', encoding='utf-8')
        shutil.copyfile(ROOT/'hardware_model_geometry.py', stage/'model.py')
        shutil.copyfile(ROOT/'requirements-three-d-model.txt', stage/'requirements.txt')
        measurements = {}
        meshes = {}
        p = resolve_parameters(recipe['parameters'])
        for variant, quality in recipe['variants'].items():
            mesh = build_model(p, variant, quality)
            meshes[variant] = mesh
            measurements[variant] = dict(triangles=len(mesh.faces), vertices=len(mesh.vertices),
                watertight=bool(mesh.is_watertight), connected_solids=mesh.body_count,
                volume_mm3=float(mesh.volume), bounds_mm=mesh.bounds.tolist(), dimensions_mm=mesh.extents.tolist(),
                winding_consistent=bool(mesh.is_winding_consistent))
            for suffix in recipe['model_formats']:
                export_mesh(mesh, stage/f'model_{variant}.{suffix}', p, recipe['material'])
            # Verify serialized unit/axis conversion rather than trusting export code.
            import numpy as np
            import trimesh
            stl = trimesh.load(stage/f'model_{variant}.stl')
            glb = trimesh.load(stage/f'model_{variant}.glb', force='scene')
            if not stl.is_watertight or not np.allclose(stl.extents, mesh.extents, atol=2e-5):
                raise ValueError('STL lost closed topology or millimetre dimensions')
            if not np.allclose(glb.extents, mesh.extents[[0, 2, 1]]*.001, atol=2e-8):
                raise ValueError('GLB metre/Y-up dimensions mismatch')
            export_views(mesh, p, variant, stage)
        if not len(meshes['display'].faces) < len(meshes['full'].faces)/2:
            raise ValueError('Display model does not sufficiently reduce triangle count')
        if not np.allclose(meshes['display'].extents, meshes['full'].extents, atol=2e-5):
            raise ValueError('Full and display dimensions differ')
        render_studio(meshes, p, recipe, stage)
        artifacts = {str(path.relative_to(stage)).replace('\\', '/'): dict(bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in sorted(stage.rglob('*')) if path.is_file()}
        manifest = dict(schema_version=SCHEMA_VERSION, fingerprint=fingerprint, standard=recipe['standard'],
            dimension_status=recipe['dimension_status'], length_status=recipe['length_status'],
            generator=recipe['generator'], sources=recipe['sources'],
            source_fingerprint=hashlib.sha256((ROOT/recipe['source_table']).read_bytes()).hexdigest(),
            recipe_fingerprint=hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest(),
            coordinate_system=recipe['coordinate_system'], models=measurements, artifacts=artifacts)
        # Publish manifest last: an interrupted build never passes a cache check.
        for name in artifacts:
            destination = output/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            (stage/name).replace(destination)
        temp_manifest = stage/'manifest.json'
        temp_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n', encoding='utf-8')
        temp_manifest.replace(manifest_path)
    return True


def main(**kwargs):
    root = Path(kwargs.get('root', ROOT))
    pattern = kwargs.get('filter') or '*'
    update = kwargs.get('update_metadata', False)
    update_presentation = kwargs.get('update_presentation', False)
    count = dict(updated=0, generated=0, cached=0, supported=0, unsupported=0)
    unsupported = []
    families = {}
    jobs = kwargs.get('model_jobs', 1)
    if not isinstance(jobs, int) or not 1 <= jobs <= 8:
        raise ValueError('model_jobs must be an integer between 1 and 8')
    # Migrate both stores independently; preserve hand-edited/action metadata.
    if update or update_presentation:
        for store in ['parts_source', 'parts']:
            for path in sorted((root/store).glob('*/working.yaml')):
                if not fnmatch.fnmatchcase(path.parent.name, pattern):
                    continue
                part = yaml.safe_load(path.read_text(encoding='utf-8'))
                if update and add_definition(part):
                    write_recipe(path, part['three_d_model_details'])
                    count['updated'] += 1
                elif update_presentation and part.get('three_d_model_details'):
                    recipe = upgrade_presentation(part['three_d_model_details'])
                    if recipe != part['three_d_model_details']:
                        write_recipe(path, recipe)
                        count['updated'] += 1
    tasks = []
    for path in sorted((root/'parts').glob('*/working.yaml')):
        if not fnmatch.fnmatchcase(path.parent.name, pattern):
            continue
        part = yaml.safe_load(path.read_text(encoding='utf-8'))
        recipe = part.get('three_d_model_details')
        if not recipe:
            _, reason = definition(part)
            unsupported.append(dict(part_id=path.parent.name, reason=reason or 'Supported part has no saved recipe; use --update-metadata.'))
            count['unsupported'] += 1
            continue
        count['supported'] += 1
        families[recipe['generator']] = families.get(recipe['generator'], 0)+1
        if kwargs.get('metadata_only', False):
            continue
        tasks.append((recipe, path.parent, kwargs.get('force', False)))
    if jobs == 1:
        for task in tasks:
            name, changed = _generate_one(task)
            count['generated' if changed else 'cached'] += 1
            print(f'  3D {"generated" if changed else "cached"}: {name}', flush=True)
    elif tasks:
        # Each worker owns a different part directory and publishes atomically.
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = [pool.submit(_generate_one, task) for task in tasks]
            for future in as_completed(futures):
                name, changed = future.result()
                count['generated' if changed else 'cached'] += 1
                print(f'  3D {"generated" if changed else "cached"}: {name}', flush=True)
    if kwargs.get('metadata_only', False) and update:
        (root/'three_d_model_coverage.json').write_text(json.dumps(dict(checked_on='2026-10-11',
            supported=count['supported'], families=families, unsupported=unsupported), indent=2)+'\n', encoding='utf-8')
    print(f'3D models: {count}; supported generators: {families}', flush=True)
    return count


def _generate_one(task):
    recipe, folder, force = task
    return folder.name, generate_assets(recipe, folder, force)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='*')
    parser.add_argument('--update-metadata', action='store_true')
    parser.add_argument('--update-presentation', action='store_true',
                        help='Add studio materials and product views, preserving saved geometry and custom settings')
    parser.add_argument('--metadata-only', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--jobs', dest='model_jobs', type=int, default=1,
                        help='Independent model worker processes, 1–8 (default 1)')
    main(**vars(parser.parse_args()))
