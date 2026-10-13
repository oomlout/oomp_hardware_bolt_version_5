"""Independent hardware mesh generators, millimetres, Z principal axis."""
import argparse
import copy
import json
import math
from pathlib import Path
import numpy as np
import trimesh

GENERATORS = {'iso_4014_hex_bolt': 'bolt', 'iso_4017_hex_screw': 'bolt',
              'supplier_nylon_hex_screw': 'bolt', 'iso_4032_hex_nut': 'nut',
              'supplier_hex_nut': 'nut', 'supplier_nylon_hex_nut': 'nut',
              'din_6923_flange_nut': 'nut', 'supplier_coupling_nut': 'nut',
              'din_125_a_washer': 'washer', 'din_9021_penny_washer': 'washer',
              'catalogue_nylon_washer': 'washer', 'supplier_nylon_insert_nut': 'nut',
              'supplier_cage_nut': 'nut', 'supplier_2020_t_nut': 'nut',
              'supplier_2020_ball_spring_nut': 'nut'}


def resolve_parameters(parameters):
    """Recalculate axial coordinates after an independent under-head length edit."""
    p = copy.deepcopy(parameters)
    if p['family'] == 'bolt':
        length, pitch, radius = p['length_mm'], p['pitch_mm'], p['underhead_fillet_mm']
        if p['thread_mode'] == 'partial':
            p['thread_length_reference_mm'] = p['thread_length_table_mm'][
                0 if length <= 125 else 1 if length <= 200 else 2]
            end = min(p['thread_length_reference_mm']+pitch, length-radius)
        else:
            end = length-radius
        p.update(thread_end_z_mm=end, thread_runout_mm=min(pitch, end/3),
                 overall_height_mm=length+p['head_height_mm'])
        p['thread_length_mm'] = end-p['thread_runout_mm']
        p['plain_shank_length_mm'] = length-end
    else:
        p['overall_height_mm'] = p['height_mm']
    if 'pitch_mm' in p:
        h = math.sqrt(3)/2*p['pitch_mm']
        p.update(thread_pitch_diameter_mm=p['nominal_diameter_mm']-3*h/4,
                 external_minor_diameter_mm=p['nominal_diameter_mm']-17*h/12,
                 internal_minor_diameter_mm=p['nominal_diameter_mm']-5*h/4)
    return p


def validate_parameters(p):
    family = p.get('family')
    if family not in {'bolt', 'nut', 'washer'}:
        raise ValueError('Unknown geometry family')
    for key, value in p.items():
        if key.endswith('_mm') and isinstance(value, (float, int)):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'{key} must be finite and nonnegative')
    for key in ['nominal_diameter_mm', 'characteristic_dimension_mm', 'overall_height_mm']:
        if p[key] <= 0:
            raise ValueError(f'{key} must be positive')
    if family in {'bolt', 'nut'}:
        if p['handedness'] != 'right' or p['thread_starts'] != 1 or p['pitch_mm'] <= 0:
            raise ValueError('Only positive-pitch right-handed single-start threads supported')
        if p['external_minor_diameter_mm'] <= 0 or p['across_flats_mm'] <= p['nominal_diameter_mm']:
            raise ValueError('Thread or hex dimensions are impossible')
        if not 15 <= p['outer_chamfer_angle_degrees'] <= 30:
            raise ValueError('Outer chamfer must be 15 to 30 degrees')
        if p['thread_flank_angle_degrees'] != 60:
            raise ValueError('ISO metric generator requires 60 degree thread flanks')
    if family == 'bolt':
        if p['thread_end_z_mm'] <= p['tip_chamfer_mm']+p['pitch_mm']:
            raise ValueError('Length too short for thread and tip')
        if not 0 < p['tip_chamfer_mm'] < p['nominal_diameter_mm']/2:
            raise ValueError('Tip chamfer must leave a positive end face')
        if p['bearing_height_mm']+p['head_chamfer_height_mm'] >= p['head_height_mm']:
            raise ValueError('Head bearing and chamfer exceed head height')
        if p['bearing_diameter_mm'] <= p['nominal_diameter_mm']+2*p['underhead_fillet_mm']:
            raise ValueError('Fillet cannot fit below bearing')
    elif family == 'nut':
        if p['mouth_diameter_mm'] >= p['across_flats_mm'] or p['height_mm'] <= 0:
            raise ValueError('Nut cavity breaks through hex')
        if p['hole_chamfer_mm']*2 >= p['height_mm']:
            raise ValueError('Nut mouth chamfers consume the nut')
        if p['mouth_diameter_mm'] < p['nominal_diameter_mm']:
            raise ValueError('Nut mouth must clear nominal thread diameter')
    else:
        if not 0 < p['hole_diameter_mm'] < p['outer_diameter_mm'] or p['height_mm'] <= 0:
            raise ValueError('Invalid washer opening or thickness')


def _cylinder(radius, z0, z1, n):
    mesh = trimesh.creation.cylinder(radius=radius, height=z1-z0, sections=n)
    mesh.apply_translation([0, 0, (z0+z1)/2])
    return mesh


def _hex_body(flats, z0, z1, n, angle, bottom_chamfer=False):
    """Hex prism trimmed by a lathed cone, preserving actual flats and corners."""
    corner = flats/math.sqrt(3)
    height = (corner-flats/2)*math.tan(math.radians(angle))
    hexagon = _cylinder(corner, z0, z1, 6)
    z = [z0, z1-height, z1]
    radii = [corner, corner, flats/2]
    if bottom_chamfer:
        z = [z0, z0+height, z1-height, z1]
        radii = [flats/2, corner, corner, flats/2]
    envelope = _ring_solid(z, np.asarray(radii)[:, None], n)
    return trimesh.boolean.intersection([hexagon, envelope], engine='manifold')


def _bolt(p, variant, q):
    n, pitch = q['angular_segments'], p['pitch_mm']
    rs, end = p['nominal_diameter_mm']/2, p['thread_end_z_mm']
    length, rf = p['length_mm'], p['underhead_fillet_mm']
    z = np.linspace(0, end, max(3, math.ceil(end/pitch*q['samples_per_pitch'])+1))
    z = np.sort(np.r_[z, p['tip_chamfer_mm'], end-p['thread_runout_mm']])
    z = z[np.r_[True, np.diff(z) > 1e-8]]
    theta = np.arange(n)*2*math.pi/n
    radii = np.full((len(z), n), rs)
    if variant == 'full':
        taper = np.clip((end-z)/p['thread_runout_mm'], 0, 1)
        radii -= thread_depth(z[:, None]/pitch-theta[None, :]/(2*math.pi), pitch)*taper[:, None]
    radii = np.minimum(radii, (rs-p['tip_chamfer_mm']+z)[:, None])
    a = np.linspace(math.pi, math.pi/2, q['fillet_segments']+1)
    extra_z = np.r_[length-rf+rf*np.sin(a), length+p['bearing_height_mm']*.5]
    extra_r = np.r_[rs+rf+rf*np.cos(a), rs+rf]
    keep = extra_z > z[-1]+1e-8
    shaft = _ring_solid(np.r_[z, extra_z[keep]],
        np.vstack((radii, np.repeat(extra_r[keep, None], n, axis=1))), n)
    bearing = _cylinder(p['bearing_diameter_mm']/2, length,
                        length+p['bearing_height_mm']+.01, n)
    head = _hex_body(p['across_flats_mm'], length+p['bearing_height_mm'],
                     length+p['head_height_mm'], n, p['outer_chamfer_angle_degrees'])
    return trimesh.boolean.union([shaft, bearing, head], engine='manifold')


def internal_thread_radius(phase, p):
    """ISO basic internal profile: D1=D-5H/4, P/4 flat crest, P/8 root."""
    distance = np.abs((np.asarray(phase)+.5) % 1-.5)
    h = math.sqrt(3)/2*p['pitch_mm']
    depth = np.clip((distance-1/8)*p['pitch_mm']*math.sqrt(3), 0, 5*h/8)
    return p['internal_minor_diameter_mm']/2+depth


def _nut(p, variant, q):
    if p.get('nut_style'):
        return _special_nut(p, variant, q)
    n, height = q['angular_segments'], p['height_mm']
    z0 = p.get('flange_thickness_mm', 0)
    body = _hex_body(p['across_flats_mm'], z0, height, n,
                     p['outer_chamfer_angle_degrees'], bottom_chamfer=not z0)
    if z0:
        outer = p['flange_diameter_mm']/2
        edge = p['flange_edge_round_mm']
        # Rounded flange rim and sloping upper transition, parameterized in recipe.
        a = np.linspace(-math.pi/2, 0, q['fillet_segments']+1)
        b = np.linspace(0, math.pi/2, q['fillet_segments']+1)[1:]
        flange_z = np.r_[edge+edge*np.sin(a), z0-edge+edge*np.sin(b), z0+.02]
        flange_r = np.r_[outer-edge+edge*np.cos(a), outer-edge+edge*np.cos(b), p['across_flats_mm']/2]
        flange = _ring_solid(flange_z, flange_r[:, None], n)
        body = trimesh.boolean.union([body, flange], engine='manifold')
    return _bore(body, p, variant, q, height)


def _bore(body, p, variant, q, height, offset=0):
    n = q['angular_segments']
    pitch = p['pitch_mm']
    z = np.linspace(-.05, height+.05, max(4, math.ceil(height/pitch*q['samples_per_pitch'])+1))
    z = np.unique(np.r_[z, 0, p['hole_chamfer_mm'], height-p['hole_chamfer_mm'], height])
    z = z[np.r_[True, np.diff(z) > 1e-8]]
    theta = np.arange(n)*2*math.pi/n
    if variant == 'full':
        radii = internal_thread_radius(z[:, None]/pitch-theta[None, :]/(2*math.pi), p)
    else:
        radii = np.full((len(z), n), p['internal_minor_diameter_mm']/2)
    mouth = p['mouth_diameter_mm']/2
    chamfer_r = mouth-np.minimum(np.maximum(z, 0), np.maximum(height-z, 0))*p['hole_chamfer_slope']
    radii = np.maximum(radii, chamfer_r[:, None])
    cutter = _ring_solid(z, radii, n)
    cutter.apply_translation([0, 0, offset])
    return trimesh.boolean.difference([body, cutter], engine='manifold')


def _box(x, y, z0, z1, cx=0, cy=0):
    mesh = trimesh.creation.box([x, y, z1-z0])
    mesh.apply_translation([cx, cy, (z0+z1)/2])
    return mesh


def _assembly(components):
    """Preserve face ranges for material assignment without merging contacting parts."""
    components = [(name, _clean_for_stl(mesh)) for name, mesh in components]
    result = trimesh.util.concatenate([mesh for _, mesh in components])
    result.metadata['components'] = [dict(name=name, faces=len(mesh.faces)) for name, mesh in components]
    return result


def _clean_for_stl(mesh):
    """Remove coincident boolean slivers before STL's default vertex merge."""
    mesh.merge_vertices(digits_vertex=8)
    ordered = np.sort(mesh.faces, axis=1)
    mesh.update_faces(np.all(np.diff(ordered, axis=1) != 0, axis=1))
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    return mesh


def _special_nut(p, variant, q):
    n, h = q['angular_segments'], p['height_mm']
    style = p['nut_style']
    if style == 'locking_nut':
        m, s, d = p['hex_height_mm'], p['across_flats_mm'], p['nominal_diameter_mm']
        outer, seat = s*.48, (d+s)*.25
        gap = .002
        lower = _hex_body(s, 0, m, n, 30, bottom_chamfer=True)
        # Rounded steel crown with an open counterbore for the separate polymer ring.
        z = np.linspace(m-.01, h, q['fillet_segments']+2)
        radii = outer-(outer-seat-.08*d)*np.clip((z-m)/(h-m), 0, 1)**2
        crown = _ring_solid(z, radii[:, None], n)
        steel = trimesh.boolean.union([lower, crown], engine='manifold')
        steel = _bore(steel, p, variant, q, m)
        steel = trimesh.boolean.difference([steel, _cylinder(seat, m, h+.05, n)], engine='manifold')
        insert = trimesh.boolean.difference([
            _cylinder(seat-gap, m+gap, h-.08*(h-m), n),
            _cylinder(p['internal_minor_diameter_mm']/2, m, h+.05, n)], engine='manifold')
        return _assembly([('steel', steel), ('nylon_insert', insert)])
    if style == 'cage_nut':
        w, length, t = p['body_width_mm'], p['body_length_mm'], p['sheet_thickness_mm']
        body_h = p['body_height_mm']
        # Open U-shaped sheet cage with opposing hooked spring ears.
        pieces = [_box(length, w, 0, t)]
        for sign in [-1, 1]:
            pieces.append(_box(length*.78, t, t*.5, body_h, cy=sign*(w-t)/2))
            ledge_depth = (w-p['across_flats_mm'])/2+.25
            pieces.append(_box(length*.55, ledge_depth,
                               body_h-t, body_h, cy=sign*(w/2-ledge_depth/2)))
            ear_y = sign*(p['across_flats_mm']/2+.2)
            # N is tab width across X, not outward hook projection.
            pieces.append(_box(p['foot_width_mm'], t, body_h-t, h, cy=ear_y))
            hook_depth = w/2-abs(ear_y)+t/2
            pieces.append(_box(p['foot_width_mm'], hook_depth, h-t, h,
                               cy=sign*(w/2-hook_depth/2)))
        cage = trimesh.boolean.union(pieces, engine='manifold')
        cage = trimesh.boolean.difference([cage, _cylinder(p['nominal_diameter_mm']*.6, -.05, t+.05, n)], engine='manifold')
        nut_z = t+.025
        nut = _box(p['across_flats_mm'], p['across_flats_mm'], nut_z, nut_z+p['nut_height_mm'])
        nut = _bore(nut, p, variant, q, p['nut_height_mm'], nut_z)
        return _assembly([('steel', cage), ('steel_nut', nut)])
    length, width = p['body_length_mm'], p['body_width_mm']
    if style == 't_nut':
        shoulder = h-p['neck_height_mm']
        # Convex clipped rectangle models the twist-in hammer head.
        cut = min(width*.2, 1.)
        xy = np.array([[-length/2+cut,-width/2],[length/2,-width/2],
                       [length/2,width/2-cut],[length/2-cut,width/2],
                       [-length/2,width/2],[-length/2,-width/2+cut]])
        points = np.vstack([np.column_stack([xy, np.full(6,z)]) for z in [0,shoulder]])
        head = trimesh.convex.convex_hull(points)
        neck = _cylinder(p['neck_width_mm']/2, shoulder-.01, h, n)
        body = trimesh.boolean.union([head,neck],engine='manifold')
        return _bore(body,p,variant,q,h)
    if style == 'ball_spring_nut':
        bh, r, projection = p['body_height_mm'], p['ball_radius_mm'], p['ball_projection_mm']
        # Extruded arched back and flat bearing face, aligned along X.
        theta = np.linspace(0, math.pi, n//2+1)
        section = np.column_stack([width/2*np.cos(theta), projection+bh*np.sin(theta)])
        points = np.vstack([np.column_stack([np.full(len(section),x),section]) for x in [-length/2,length/2]])
        body = trimesh.convex.convex_hull(points)
        # Bearing face on top so the bore and retaining ball can both be inspected.
        body.vertices[:,2] = h+projection-body.vertices[:,2]
        body.invert()
        body = _bore(body,p,variant,q,h)
        ball_center = [length/2-r-.4,0,r]
        pocket = trimesh.creation.icosphere(subdivisions=3 if variant=='full' else 2,radius=r+.025)
        pocket.apply_translation(ball_center)
        body = trimesh.boolean.difference([body,pocket],engine='manifold')
        ball = trimesh.creation.icosphere(subdivisions=3 if variant=='full' else 2,radius=r)
        ball.apply_translation(ball_center)
        return _assembly([('steel',body),('steel_ball',ball)])
    raise ValueError('Unknown special nut style')


def _washer(p, variant, q):
    n = q['angular_segments']
    # Form A is unchamfered. Avoid inventing a bevel to make reflections prettier.
    outer = _cylinder(p['outer_diameter_mm']/2, 0, p['height_mm'], n)
    hole = _cylinder(p['hole_diameter_mm']/2, -.05, p['height_mm']+.05, n)
    return trimesh.boolean.difference([outer, hole], engine='manifold')


def build_model(parameters, variant='full', quality=None):
    if variant not in {'full', 'display'}:
        raise ValueError(f'Unknown variant {variant}')
    p = resolve_parameters(parameters)
    validate_parameters(p)
    q = quality or dict(angular_segments=96 if variant == 'full' else 24,
        samples_per_pitch=32 if variant == 'full' else 1,
        fillet_segments=12 if variant == 'full' else 3)
    if q['angular_segments'] < 24 or q['angular_segments'] % 12 or q['samples_per_pitch'] < 1 or q['fillet_segments'] < 2:
        raise ValueError('Tessellation requires angular segments multiple of 12 >=24 and positive samples')
    mesh = {'bolt': _bolt, 'nut': _nut, 'washer': _washer}[p['family']](p, variant, q)
    if p.get('nut_style') or p['specification'].startswith('APPROXIMATE VISUAL MODEL:'):
        if not mesh.metadata.get('components'):
            mesh = _clean_for_stl(mesh)
    if mesh is None or not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0 or mesh.body_count != p['expected_components']:
        raise ValueError('Generator did not produce the intended closed solids')
    if not np.isclose(mesh.extents[2], p['overall_height_mm'], atol=2e-5):
        raise ValueError('Axial dimension mismatch')
    mesh.metadata.update(units='mm', variant=variant, parameters=p)
    return mesh
def thread_depth(phase, pitch):
    """Radial depth at distance from a crest, with C1 tangent rounded root."""
    q = np.abs((np.asarray(phase)+.5) % 1-.5)
    h = math.sqrt(3)/2*pitch
    radius = h/6
    linear = np.maximum(0, (q-1/16)*pitch*math.sqrt(3))
    rounded = 17*h/24-radius+np.sqrt(np.maximum(0, radius**2-((.5-q)*pitch)**2))
    return np.where(q <= 3/8, linear, rounded)

def _ring_solid(z, radii, segments):
    angles = np.arange(segments)*2*math.pi/segments
    radii = np.broadcast_to(radii, (len(z), segments))
    vertices = np.stack((radii*np.cos(angles), radii*np.sin(angles),
                         np.broadcast_to(np.asarray(z)[:, None], radii.shape)), axis=-1).reshape(-1, 3)
    first = np.arange((len(z)-1)*segments).reshape(-1, segments)
    nxt = np.roll(first, -1, axis=1)
    faces = np.concatenate((np.stack((first, nxt, nxt+segments), axis=-1).reshape(-1, 3),
                            np.stack((first, nxt+segments, first+segments), axis=-1).reshape(-1, 3)))
    bottom, top = len(vertices), len(vertices)+1
    vertices = np.vstack((vertices, [0, 0, z[0]], [0, 0, z[-1]]))
    idx = np.arange(segments)
    caps = np.vstack((np.column_stack((np.full(segments, bottom), (idx+1) % segments, idx)),
                      np.column_stack((np.full(segments, top), idx+(len(z)-1)*segments,
                                       (idx+1) % segments+(len(z)-1)*segments))))
    return trimesh.Trimesh(vertices, np.vstack((faces, caps)), process=True)

def apply_gltf_material(tree, material):
    """glTF factors are linear; preserve exact colours rather than 8-bit rounding."""
    for entry in tree.get('materials', []):
        selected = material.get('insert_material') if entry.get('name') == 'Blue nylon insert' else material
        selected = selected or material
        colour = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4
                  for v in selected['base_colour_srgb']]+[1.]
        entry['pbrMetallicRoughness']['baseColorFactor'] = colour
        if selected.get('coat_weight', 0) > 0:
            entry.setdefault('extensions', {})['KHR_materials_clearcoat'] = dict(
                clearcoatFactor=selected['coat_weight'],
                clearcoatRoughnessFactor=selected['coat_roughness'])
            used = tree.setdefault('extensionsUsed', [])
            if 'KHR_materials_clearcoat' not in used:
                used.append('KHR_materials_clearcoat')

def export_mesh(mesh, filename, p, material=None):
    """STL stays in millimetres; glTF uses metres and Y-up per glTF 2.0."""
    path = Path(filename)
    if path.suffix.lower() == '.glb':
        web = mesh.copy()
        web.apply_transform(np.array([[.001, 0, 0, 0], [0, 0, .001, 0],
                                       [0, -.001, 0, 0], [0, 0, 0, 1]]))
        web.metadata.update(units='metres', source_units='mm', up_axis='Y')
        colour = ([round(c*255) for c in material['base_colour_srgb']]+[255] if material else
                  [52, 56, 60, 255] if p['finish'] == 'black' else [158, 166, 176, 255])
        web.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            name=material['name'] if material else p['finish'], baseColorFactor=colour,
            metallicFactor=material['metallic'] if material else .8,
            roughnessFactor=material['roughness'] if material else .31))
        scene = trimesh.Scene()
        offset = 0
        for component in mesh.metadata.get('components', [dict(name='steel', faces=len(mesh.faces))]):
            count = component['faces']
            piece = web.submesh([np.arange(offset, offset+count)], append=True)
            selected = material.get('insert_material', material) if material and component['name']=='nylon_insert' else material
            if selected:
                piece.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
                    name=selected['name'], baseColorFactor=[round(c*255) for c in selected['base_colour_srgb']]+[255],
                    metallicFactor=selected['metallic'], roughnessFactor=selected['roughness']))
            scene.add_geometry(piece, node_name=component['name'], geom_name=component['name'])
            offset += count
        scene.metadata.update(units='metres', source_units='mm', up_axis='Y', specification=p['specification'])
        path.write_bytes(trimesh.exchange.gltf.export_glb(scene,
            tree_postprocessor=(lambda tree: apply_gltf_material(tree, material)) if material else None))
    else:
        mesh.export(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, default=Path(__file__).with_name('parameters.json'))
    parser.add_argument('--length', type=float, help='Under-head length for headed axial fasteners only')
    parser.add_argument('--variant', choices=['full', 'display', 'both'], default='both')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    recipe = json.loads(args.parameters.read_text(encoding='utf-8'))
    if recipe['generator'] not in GENERATORS or GENERATORS[recipe['generator']] != recipe['parameters']['family']:
        raise ValueError('Unsupported generator or inconsistent family')
    p = recipe['parameters']
    if args.length is not None:
        if p['family'] != 'bolt':
            parser.error('--length applies only to bolts and headed screws')
        p['length_mm'] = args.length
    args.output.mkdir(parents=True, exist_ok=True)
    for variant in ['full', 'display'] if args.variant == 'both' else [args.variant]:
        mesh = build_model(p, variant, recipe['variants'][variant])
        for suffix in ['stl', 'glb']:
            export_mesh(mesh, args.output/f'model_{variant}.{suffix}', p, recipe['material'])
        print(f'{variant}: {len(mesh.faces)} triangles, {mesh.volume:.3f} mm3')
