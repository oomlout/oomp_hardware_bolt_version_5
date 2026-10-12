"""Lightweight recipe population; dimensional inputs are loaded from sourced YAML."""
import copy
from functools import lru_cache
import math
from pathlib import Path
import re
import yaml
from hardware_model_render import presentation_defaults

ROOT = Path(__file__).resolve().parent
STANDARD_FILE = ROOT/'source_file/standards/catalogue_hardware.yaml'
GENERATOR_NAMES = dict(hex_bolt='iso_4014_hex_bolt', hex_screw='iso_4017_hex_screw',
    nylon_hex_screw='supplier_nylon_hex_screw', hex_nut='iso_4032_hex_nut',
    miniature_hex_nut='supplier_hex_nut', nylon_hex_nut='supplier_nylon_hex_nut',
    flange_nut='din_6923_flange_nut', coupling_nut='supplier_coupling_nut',
    plain_washer='din_125_a_washer', penny_washer='din_9021_penny_washer',
    nylon_washer='catalogue_nylon_washer')


@lru_cache(maxsize=1)
def standard():
    return yaml.safe_load(STANDARD_FILE.read_text(encoding='utf-8'))


def classify(part):
    typ, variant = part.get('taxonomy_2'), part.get('taxonomy_4', '') or ''
    if typ == 'bolt':
        return 'hex_bolt', ''
    if typ == 'set_screw':
        finish = part.get('taxonomy_5', '') or ''
        if finish not in {'', 'nylon_white'}:
            return None, f'Unsupported screw material: {finish}'
        return 'nylon_hex_screw' if finish == 'nylon_white' else 'hex_screw', ''
    if typ == 'nut':
        if variant in {'', 'black'}:
            token = part.get('taxonomy_3', '')
            return ('miniature_hex_nut' if token in {'m1', 'm1_4'} else 'hex_nut'), ''
        if variant in {'nylon_white', 'flanged', 'coupling'}:
            return {'nylon_white': 'nylon_hex_nut', 'flanged': 'flange_nut', 'coupling': 'coupling_nut'}[variant], ''
        return None, ('Locking mechanism and manufacturer dimensions are unspecified; cannot assume a nylon insert or all-metal lock nut.'
                      if variant == 'locking' else 'Extrusion/cage nut requires a supplier-specific drawing and assembly definition.')
    if typ == 'washer':
        if variant in {'', 'penny', 'nylon_white_12_mm_outer_diameter_1_5_mm_depth'}:
            return {'': 'plain_washer', 'penny': 'penny_washer',
                    'nylon_white_12_mm_outer_diameter_1_5_mm_depth': 'nylon_washer'}[variant], ''
    return None, 'No registered family for this catalogue identity.'


def definition(part):
    family, reason = classify(part)
    if family is None:
        return None, reason
    token = part.get('taxonomy_3', '')
    if not re.fullmatch(r'm\d+(?:_\d+)?', token):
        return None, f'Unrecognized metric size: {token}'
    d = float(token[1:].replace('_', '.'))
    table = standard()['families'][family]
    row = copy.deepcopy(table['sizes'].get(f'{d:g}'))
    if row is None:
        return None, f'{family}: M{d:g} has no verified dimensional row; not extrapolated.'
    if 'inherit_bolt_size' in row:
        row = copy.deepcopy(standard()['families']['hex_bolt']['sizes'][row['inherit_bolt_size']])
        if family != 'hex_bolt':
            row.pop('b_mm', None)
    shape = 'bolt' if family.endswith('screw') or family == 'hex_bolt' else 'washer' if 'washer' in family else 'nut'
    finish = ('nylon_white' if 'nylon' in family else
              'black' if part.get('taxonomy_4') == 'black' else 'satin')
    identity = part.get('id') or '_'.join(str(part.get(f'taxonomy_{i}', '')) for i in range(1, 8) if part.get(f'taxonomy_{i}'))
    specification = table.get('specification', table['standard'])
    p = dict(family=shape, nominal_diameter_mm=d, finish=finish,
             identity=identity, specification=specification, expected_components=1,
             handedness='right', thread_starts=1, thread_flank_angle_degrees=60.)
    limits = {}
    status = row.get('dimension_status', 'standard_dimensions' if table['standard'] else 'manufacturer_dimensions')
    length_status = 'not_applicable'
    if shape == 'bolt':
        length_token = part.get('taxonomy_4') if family == 'hex_bolt' else part.get('taxonomy_7')
        if not re.fullmatch(r'\d+(?:_\d+)?_mm_length', length_token or ''):
            raise ValueError(f'Invalid under-head length {length_token}')
        length = float(length_token.removesuffix('_mm_length').replace('_', '.'))
        grade = 'A' if length <= min(10*d, 150) else 'B'
        p.update({key: row[key] for key in ['pitch_mm', 'across_flats_mm', 'head_height_mm',
            'bearing_diameter_mm', 'bearing_height_mm', 'underhead_fillet_mm']})
        p.update(length_mm=length, length_convention='under-head bearing plane to tip',
            thread_mode='partial' if family == 'hex_bolt' else 'full',
            thread_length_table_mm=row.get('b_mm'), tip_chamfer_mm=p['pitch_mm']/2,
            outer_chamfer_angle_degrees=30., characteristic_dimension_mm=d,
            characteristic_dimension_basis='nominal axial thread diameter')
        p['head_chamfer_height_mm'] = (p['across_flats_mm']/math.sqrt(3)-p['across_flats_mm']/2)*math.tan(math.pi/6)
        end = min(row['b_mm'][0 if length <= 125 else 1 if length <= 200 else 2]+p['pitch_mm'], length-p['underhead_fillet_mm']) if family == 'hex_bolt' else length-p['underhead_fillet_mm']
        p.update(thread_end_z_mm=end, thread_runout_mm=min(p['pitch_mm'], end/3),
                 overall_height_mm=length+p['head_height_mm'])
        p['thread_length_mm'] = end-p['thread_runout_mm']
        p['plain_shank_length_mm'] = length-end
        if family == 'hex_bolt':
            p['thread_length_reference_mm'] = row['b_mm'][0 if length <= 125 else 1 if length <= 200 else 2]
        limits = dict(product_grade=grade, head_height_mm=row[f'k_limits_{grade}'],
                      across_flats_mm=row[f's_limits_{grade}'],
                      across_corners_min_mm=row[f'e_min_{grade}'], bearing_diameter_min_mm=row[f'dw_min_{grade}'],
                      underhead_fillet_min_mm=p['underhead_fillet_mm'],
                      outer_chamfer_angle_degrees=[15, 30], incomplete_thread_max_mm=2*p['pitch_mm'])
        length_status = 'standard_length' if length in table.get('standard_lengths_mm', []) else 'catalogue_length_not_verified_in_source_length_table'
    elif shape == 'nut':
        p.update({key: row[key] for key in ['pitch_mm', 'across_flats_mm', 'height_mm']})
        mouth_limits = row.get('hole_mouth_limits', [d, d+p['pitch_mm']/2])
        mouth = sum(mouth_limits)/2
        minor = d-5/4*math.sqrt(3)/2*p['pitch_mm']
        slope = math.tan(math.pi/3)  # included angle 120 degrees
        p.update(outer_chamfer_angle_degrees=30., mouth_diameter_mm=mouth,
            hole_chamfer_mm=(mouth-minor)/2/slope, hole_chamfer_slope=slope,
            height_convention='total axial nut height', overall_height_mm=p['height_mm'],
            characteristic_dimension_mm=p['across_flats_mm'], characteristic_dimension_basis='hexagon across flats')
        if family == 'flange_nut':
            p.update(flange_diameter_mm=row['flange_diameter_mm'], flange_thickness_mm=row['flange_thickness_mm'],
                     flange_edge_round_mm=min(row.get('flange_radius_max_mm', .15), row['flange_thickness_mm']/4))
        for key, target in [('height_limits', 'height_mm'), ('flats_limits', 'across_flats_mm'), ('hole_mouth_limits', 'mouth_diameter_mm')]:
            if key in row:
                limits[target] = row[key]
        if 'e_min' in row:
            limits['across_corners_min_mm'] = row['e_min']
    else:
        p.update({key: row[key] for key in ['hole_diameter_mm', 'outer_diameter_mm', 'height_mm']})
        p.update(overall_height_mm=p['height_mm'], characteristic_dimension_mm=p['outer_diameter_mm'],
                 characteristic_dimension_basis='outer washer diameter', height_convention='axial thickness')
        for key, target in [('height_limits', 'height_mm'), ('hole_limits', 'hole_diameter_mm'), ('outer_limits', 'outer_diameter_mm')]:
            if key in row:
                limits[target] = row[key]
    if 'pitch_mm' in p:
        h = math.sqrt(3)/2*p['pitch_mm']
        p.update(thread_pitch_diameter_mm=d-3*h/4, external_minor_diameter_mm=d-17*h/12,
                 internal_minor_diameter_mm=d-5*h/4)
    recipe = dict(schema_version=1, generator=GENERATOR_NAMES[family], output_folder='three_d_model', units='mm',
        standard=table['standard'], dimensional_specification=specification, dimension_status=status,
        length_status=length_status, sources=copy.deepcopy(table['sources']), checked_on=standard()['checked_on'],
        source_table='source_file/standards/catalogue_hardware.yaml', standard_limits=limits,
        standard_lengths_mm=table.get('standard_lengths_mm', []), parameters=p,
        modelling_choices=dict(dimension_selection='Nominal bolt head height, max flats/nut height, nominal washer sizes; selected dimensions stored in parameters.',
            thread='Nominal ISO basic metric profile, no ISO 965 tolerance offsets. External rounded root H/6, internal P/4 crest and P/8 root flats.',
            runout='External one-pitch fade to plain shank; full thread ends at underhead fillet.',
            chamfer='30 degree outer hex chamfer. Nut mouth included angle 120 degrees. Bolt tip 45 degrees, P/2.',
            bearing='Bolt bearing circle and c selected within limits; k includes bearing thickness; fillet tangent to shaft and bearing.',
            cavity='Nut through-bore has a helical internal surface; display keeps minor-diameter bore and mouth chamfers.',
            display='Smooth nominal external-thread envelope or smooth minor-diameter internal bore; lower angular and fillet tessellation.',
            components='One closed solid for supported products. Unspecified lock/cage assemblies are not substituted with plain hex nuts.',
            markings='Supplier and property-class markings omitted because catalogue does not identify them.',
            unspecified_geometry='Nut mouth for supplier rows without limits and flange M3/M4 thickness/rim blends are explicit visual model selections.',
            family_note=table.get('note', 'Catalogue family mapped to the cited dimensional pattern; exact supplier unspecified.'),
            certification='Nominal visual catalogue model, not manufacturing tolerance certification.'),
        coordinate_system=dict(origin='tip centre' if shape == 'bolt' else 'lower face centre', axis='+Z towards head' if shape == 'bolt' else '+Z along bore',
            stl_units='mm', glb_units='metres', glb_up_axis='Y', glb_conversion='(x,y,z) mm -> (x,z,-y)/1000 metres'),
        variants=dict(full=dict(angular_segments=96, samples_per_pitch=32, fillet_segments=12),
                      display=dict(angular_segments=24, samples_per_pitch=1, fillet_segments=3)),
        views=['isometric', 'front', 'back', 'left', 'right', 'top', 'bottom'], model_formats=['stl', 'glb'])
    if shape != 'washer':
        recipe['sources'].append(copy.deepcopy(standard()['thread_source']))
    recipe.update(presentation_defaults(finish, shape, family == 'coupling_nut'))
    return recipe, ''


def add_definition(part):
    recipe, reason = definition(part)
    if recipe is None:
        return False
    part['three_d_model_details'] = recipe
    return True
