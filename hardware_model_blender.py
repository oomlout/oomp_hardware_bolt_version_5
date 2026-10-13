"""Run with Blender --background --python hardware_model_blender.py -- job.json."""
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Matrix, Vector
import numpy as np


def linear(srgb):
    return [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in srgb]


def point_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def material(settings, normalized_unit_mm):
    mat = bpy.data.materials.new(settings['name'])
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*linear(settings['base_colour_srgb']), 1.)
    bsdf.inputs['Metallic'].default_value = settings['metallic']
    bsdf.inputs['Roughness'].default_value = settings['roughness']
    bsdf.inputs['Coat Weight'].default_value = settings['coat_weight']
    bsdf.inputs['Coat Roughness'].default_value = settings['coat_roughness']
    tex = nodes.new('ShaderNodeTexCoord')
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = normalized_unit_mm/settings['microtexture_spacing_mm']
    noise.inputs['Detail'].default_value = 2.
    noise.inputs['Roughness'].default_value = .65
    links.new(tex.outputs['Object'], noise.inputs['Vector'])
    rough = nodes.new('ShaderNodeMapRange')
    rough.inputs['To Min'].default_value = settings['roughness']-settings['roughness_variation']
    rough.inputs['To Max'].default_value = settings['roughness']+settings['roughness_variation']
    links.new(noise.outputs['Fac'], rough.inputs['Value'])
    links.new(rough.outputs['Result'], bsdf.inputs['Roughness'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .2
    bump.inputs['Distance'].default_value = settings['microtexture_height_um']*.001/normalized_unit_mm
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def device(settings):
    if settings['device'] == 'cpu':
        return 'CPU'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for backend in ['OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI']:
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            gpu = [d for d in prefs.devices if d.type == backend]
            if gpu:
                for d in prefs.devices:
                    d.use = d.type == backend
                return 'GPU'
        except (TypeError, RuntimeError):
            continue
    return 'CPU'


def setup_scene(name, pose, meshes, p, settings, steel, render_device, job):
    scene = bpy.data.scenes.new(name)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = render_device
    scene.cycles.use_denoising = settings['denoise']
    backend = bpy.context.preferences.addons['cycles'].preferences.compute_device_type
    scene.cycles.denoiser = 'OPTIX' if render_device == 'GPU' and backend == 'OPTIX' else 'OPENIMAGEDENOISE'
    if render_device == 'GPU':
        # Bound CPU preparation work when multiple parts share one GPU.
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = 4
    scene.cycles.adaptive_threshold = settings['adaptive_threshold']
    scene.cycles.seed = settings['seed']
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 4
    scene.view_settings.view_transform = settings['view_transform']
    scene.view_settings.look = settings['look']
    scene.view_settings.exposure = settings['exposure']
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = p['characteristic_dimension_mm']*.001
    scene.world = bpy.data.worlds.new(name+' environment')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (*settings['world_colour'], 1.)
    background.inputs['Strength'].default_value = settings['world_strength']
    objects, world_vertices = {}, {}
    for variant, data in meshes.items():
        rotation = Matrix(job['product_transforms'][variant]) if name == 'product' else Matrix.Identity(4)
        rotation.translation = Vector((0, 0, 0))
        obj = bpy.data.objects.new(name+' '+variant, data)
        scene.collection.objects.link(obj)
        points = np.array([v.co[:] for v in data.vertices]) @ np.array(rotation)[:3, :3].T
        transform = rotation.copy()
        transform.translation.z = -points[:, 2].min()
        obj.matrix_world = transform
        points[:, 2] += transform.translation.z
        world_vertices[variant] = points
        objects[variant] = obj
    points = world_vertices['full']
    target = (points.min(axis=0)+points.max(axis=0))/2
    extent = max(np.ptp(points, axis=0).max(), 1.5)
    camera_data = bpy.data.cameras.new(name+' camera')
    camera = bpy.data.objects.new(name+' camera', camera_data)
    scene.collection.objects.link(camera)
    eye = np.array(pose['camera_eye'], dtype=float)
    eye /= np.linalg.norm(eye)
    camera.location = target+eye*extent*8
    point_at(camera, target)
    camera_data.type = 'ORTHO'
    camera_data.lens = 85.
    camera_data.clip_end = extent*300
    scene.camera = camera
    # Fit projected bounds, keeping the original true isometric camera direction.
    basis = np.array(camera.rotation_euler.to_matrix())
    projected = points @ basis
    span = np.ptp(projected[:, :2], axis=0).max()
    camera_data.ortho_scale = span/(1-2*settings['framing_margin'])
    midpoint = (projected[:, :2].min(axis=0)+projected[:, :2].max(axis=0))/2
    shift = midpoint-target @ basis[:, :2]
    camera.location += Vector(basis[:, :2] @ shift)
    camera.location -= Vector(basis[:, 1]*camera_data.ortho_scale*.025)
    framing = {}
    for variant, vertices in world_vertices.items():
        relative = (vertices-np.asarray(camera.location)) @ basis
        fraction = float(np.abs(relative[:, :2]).max()/(camera_data.ortho_scale/2))
        if fraction >= 1 or relative[:, 2].max() >= -camera_data.clip_start:
            raise ValueError(f'{name} {variant} camera clips model')
        framing[variant] = dict(max_frame_fraction=fraction,
                               bounds_normalized=[vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()])
    # White seamless sweep: a large plane has no visible edge or horizon.
    floor_data = bpy.data.meshes.new(name+' seamless floor')
    half = extent*200
    floor_data.from_pydata([(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)], [], [(0, 1, 2, 3)])
    floor = bpy.data.objects.new(name+' seamless floor', floor_data)
    scene.collection.objects.link(floor)
    floor_material = bpy.data.materials.new(name+' matte white')
    floor_material.use_nodes = True
    floor_bsdf = floor_material.node_tree.nodes.get('Principled BSDF')
    floor_bsdf.inputs['Base Color'].default_value = (*linear(settings['floor_colour_srgb']), 1.)
    floor_bsdf.inputs['Roughness'].default_value = settings['floor_roughness']
    floor.data.materials.append(floor_material)
    rig_scale = max(extent*.6, 1.5)
    for light in settings['lights']:
        data = bpy.data.lights.new(name+' '+light['name'], 'AREA')
        data.shape = 'RECTANGLE'
        data.energy = light['power']*rig_scale**2
        data.color = light['colour']
        data.size = light['width']*rig_scale
        data.size_y = light['height']*rig_scale
        obj = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(obj)
        obj.location = target+np.asarray(light['position'])*rig_scale
        point_at(obj, target)
    support = points[:, 2]
    description = dict(camera_eye=pose['camera_eye'], projection='orthographic',
        floor_z=0., normalized_unit_mm=p['characteristic_dimension_mm'],
        normalization_basis=p['characteristic_dimension_basis'], rig_scale=float(rig_scale),
        orthographic_scale=float(camera_data.ortho_scale), projected_span=float(span),
        framing_margin=settings['framing_margin'],
        framing=framing,
        object_matrix=list(map(list, objects['full'].matrix_world)),
        variant_object_matrices={key:list(map(list, obj.matrix_world)) for key,obj in objects.items()},
        variant_ground_clearance_mm={k:float(v[:,2].min()*p['characteristic_dimension_mm']) for k,v in world_vertices.items()},
        ground_clearance_mm=float(support.min()*p['characteristic_dimension_mm']))
    if name == 'product':
        description.update(job['product_supports']['full'])
        description['variant_supports'] = job['product_supports']
    return scene, objects, description


def main(job_path):
    job = json.loads(Path(job_path).read_text(encoding='utf-8'))
    output = Path(job['output'])
    p, settings = job['parameters'], job['studio']
    if bpy.app.version < (4, 5, 0):
        raise RuntimeError('Blender 4.5 or newer required')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    steel = material(job['material'], p['characteristic_dimension_mm'])
    nylon = material(job['insert_material'], p['characteristic_dimension_mm']) if job.get('insert_material') else None
    arrays = np.load(job['meshes'])
    meshes = {}
    for variant in ['full', 'display']:
        data = bpy.data.meshes.new(variant+' hardware')
        data.from_pydata((arrays[f'{variant}_vertices']/p['characteristic_dimension_mm']).tolist(), [],
                         arrays[f'{variant}_faces'].tolist())
        data.update()
        for poly in data.polygons:
            poly.use_smooth = True
        data.normals_split_custom_set_from_vertices(arrays[f'{variant}_normals'].tolist())
        data.materials.append(steel)
        if nylon:
            data.materials.append(nylon)
            for poly, index in zip(data.polygons, arrays[f'{variant}_materials']):
                poly.material_index = int(index)
        meshes[variant] = data
    selected_device = device(settings)
    scenes, metadata = {}, {}
    for name, pose in settings['poses'].items():
        scenes[name] = setup_scene(name, pose, meshes, p, settings, steel, selected_device, job)
        metadata[name] = scenes[name][2]
    timings = {}
    for name, render in job['renders'].items():
        if (output/render['file']).is_file():
            continue
        scene, objects, _ = scenes[render.get('view', 'isometric')]
        bpy.context.window.scene = scene
        for variant, obj in objects.items():
            obj.hide_render = variant != render['variant']
            obj.hide_viewport = variant != render['variant']
        scene.render.resolution_x = scene.render.resolution_y = render['pixels']
        scene.render.resolution_percentage = 100
        scene.cycles.samples = settings['low_samples' if render['pixels'] <= 512 else 'high_samples']
        scene.render.filepath = str(output/render['file'])
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        timings[name] = dict(seconds=round(time.perf_counter()-started, 3),
                             denoiser=scene.cycles.denoiser, samples=scene.cycles.samples)
    bpy.context.window.scene = scenes['product'][0]
    # Relative render destinations keep the saved studio portable.
    for scene, _, _ in scenes.values():
        scene.render.filepath = '//'+Path(scene.render.filepath).name
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'studio.blend'), compress=True)
    (output/'render_scene.json').write_text(json.dumps(dict(engine='Cycles',
        blender_version=bpy.app.version_string, device=selected_device,
        material=job['material'], studio=settings, poses=metadata, renders=job['renders'],
        render_statistics=timings), indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--')+1])
