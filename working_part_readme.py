"""Generate canonical hardware part pages without changing engineering inputs."""
import hashlib
from html import escape
import io
import json
from pathlib import Path
import re
from string import Template
from urllib.parse import quote, urlsplit

from PIL import Image

START = '<!-- hardware-part:start -->'
END = '<!-- hardware-part:end -->'
PREVIEW_SIZE = 512
DIMENSIONS = (
    ('nominal_diameter_mm', 'Nominal size'), ('pitch_mm', 'Thread pitch'),
    ('length_mm', 'Length'), ('across_flats_mm', 'Across flats'),
    ('head_height_mm', 'Head height'), ('height_mm', 'Height / thickness'),
    ('outer_diameter_mm', 'Outside diameter'), ('hole_diameter_mm', 'Hole diameter'),
    ('flange_diameter_mm', 'Flange diameter'), ('flange_thickness_mm', 'Flange thickness'),
    ('body_length_mm', 'Body length'), ('body_width_mm', 'Body width'),
    ('thread_length_mm', 'Modelled thread length'),
)
FAMILY_ANCHORS = {'bolt': 'bolts', 'set_screw': 'set-screws', 'nut': 'nuts',
                  'washer': 'washers', 'threaded_rod': 'threaded-rod'}


def text(value):
    return escape(str(value)).replace('|', '&#124;').replace('\n', ' ').replace('[', '&#91;').replace(']', '&#93;').replace('`', '&#96;')


def number(value):
    return f'{value:.6g}' if isinstance(value, (int, float)) else str(value)


def fenced(value, language):
    fence = '`' * max(3, max((len(m[0]) + 1 for m in re.finditer(r'`+', value)), default=3))
    return f'{fence}{language}\n{value.rstrip()}\n{fence}'


def write_changed(path, content):
    encoded = (content.rstrip() + '\n').encode('utf-8') if isinstance(content, str) else content
    if path.exists() and path.read_bytes() == encoded:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def combine(old, body):
    if START in old or END in old:
        if old.count(START) != 1 or old.count(END) != 1 or old.index(START) > old.index(END):
            raise ValueError('Malformed hardware-part generation markers')
        return old[:old.index(START)] + body.rstrip() + old[old.index(END)+len(END):]
    if old.strip():
        return body.rstrip() + '\n\n<details>\n<summary>Existing technical notes</summary>\n\n' + old.rstrip() + '\n\n</details>\n'
    return body


def identity(data, recipe, part_id):
    p = recipe.get('parameters', {})
    family = data.get('taxonomy_2', '')
    size = 'M' + number(p['nominal_diameter_mm']) if 'nominal_diameter_mm' in p else str(data.get('taxonomy_3', '')).upper()
    length = number(p.get('length_mm', ''))
    style = ' '.join(str(data.get(f'taxonomy_{i}') or '').replace('_', ' ') for i in (4, 5)
                     if not str(data.get(f'taxonomy_{i}') or '').endswith(('_mm_length', '_diameter'))).strip()
    if family in ('bolt', 'set_screw'):
        noun = 'hex bolt' if family == 'bolt' else 'hex-head set screw'
        title = f'{size} × {length} mm {noun}'
        summary = 'A partially threaded hex-head fastener for bolted joints.' if family == 'bolt' else 'A fully threaded hex-head fastener for bolted joints.'
        if style:
            title += f' — {style}'
    elif family == 'threaded_rod':
        title = f'{size} × {length} mm threaded rod'
        summary = 'A headless threaded rod, recorded at the stated overall end-to-end length.'
    elif family == 'nut':
        title = f'{size} {style or "hex"} nut'
        summaries = {
            'locking': 'A nylon-insert locking nut, modelled with separate body and insert components.',
            'cage': 'A captive nut and spring cage, represented as separate components in the saved model.',
            'coupling': 'An extended nut for joining threaded components.',
            'flanged': 'A threaded nut with an integral flange around its bearing face.',
            '2020_ball_spring': 'A ball-spring nut catalogue model for 2020 profiles. The model includes the body and ball; the hidden spring is omitted.',
            '2020_t_nut': 'A T-slot nut catalogue model for 2020 profiles; see the source notes for dimensional adaptations.',
        }
        summary = summaries.get(str(data.get('taxonomy_4')), 'A metric nut with a modelled internal thread. The dimensions below identify the exact catalogue variant.')
    elif family == 'washer':
        title = f'{size} {style or "flat"} washer'
        summary = 'A large-diameter washer with its bore, outside diameter and thickness shown below.' if data.get('taxonomy_4') == 'penny' else 'A flat washer with its bore, outside diameter and thickness shown below.'
    else:
        title = data.get('name_proper') or part_id.replace('_', ' ')
        summary = 'A hardware catalogue record with saved dimensions and available assets.'
    return title, summary


def previews(folder, recipe):
    manifest_path = folder / 'three_d_model/readme_images.json'
    old = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    records = {}
    images = []
    for key, label, source_name, output_name in (
        ('high', 'Isometric', 'render_high.png', 'readme_isometric.png'),
        ('product_high', 'Product view', 'render_product_high.png', 'readme_product.png'),
    ):
        source = folder / 'three_d_model' / source_name
        if not source.exists():
            continue
        if recipe.get('renders', {}).get(key, {}).get('variant') != 'full':
            raise ValueError(f'Preview source is not identified as full detail: {source}')
        output = source.with_name(output_name)
        source_bytes = source.read_bytes()
        digest = hashlib.sha256(source_bytes).hexdigest()
        cached = old.get(output_name, {})
        if (cached.get('source_sha256') == digest and cached.get('preview_size') == PREVIEW_SIZE
                and output.exists() and cached.get('preview_sha256') == hashlib.sha256(output.read_bytes()).hexdigest()):
            records[output_name] = cached
        else:
            with Image.open(io.BytesIO(source_bytes)) as original:
                image = original.convert('RGB')
                image.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                image.save(buffer, format='PNG', optimize=True)
            encoded = buffer.getvalue()
            write_changed(output, encoded)
            records[output_name] = {'source': source_name, 'source_sha256': digest,
                                    'preview_size': PREVIEW_SIZE, 'preview_sha256': hashlib.sha256(encoded).hexdigest()}
        images.append((label, f'[![Full-detail {label.lower()} render](three_d_model/{output_name})](three_d_model/{source_name})'))
    write_changed(manifest_path, json.dumps(records, indent=2))
    if not images:
        return 'A full-detail preview is not available for this record.'
    return ('| ' + ' | '.join(label for label, _ in images) + ' |\n| ' + ' | '.join('---' for _ in images)
            + ' |\n| ' + ' | '.join(image for _, image in images)
            + ' |\n\nFull-detail catalogue renders. Click either image to open the original resolution.')


def render(folder, data, recipe, template, raw_yaml, images):
    part_id = folder.name
    title, summary = identity(data, recipe, part_id)
    p = recipe.get('parameters', {})
    dimensions = ['| Model dimension | mm |', '| --- | ---: |']
    for key, label in DIMENSIONS:
        if p.get(key) is not None:
            dimensions.append(f'| {label} | {text(number(p[key]))} |')
    if p.get('length_convention'):
        dimensions += ['', 'Length convention: ' + text(p['length_convention']) + '.']
    identifiers = []
    if data.get('md5_6_alpha'):
        identifiers.append('**Short code:** `' + text(data['md5_6_alpha']) + '`')
    if data.get('bip_39_3_word_space'):
        identifiers.append('**Three-word label:** ' + text(data['bip_39_3_word_space']))

    provenance = ['<details>', '<summary>Model provenance and assumptions</summary>', '']
    for label, value in [('Recorded dimensional reference', recipe.get('dimensional_specification')),
                         ('Source checked', recipe.get('checked_on')),
                         ('Length status', str(recipe['length_status']).replace('_', ' ') if recipe.get('length_status') not in (None, 'not_applicable') else None),
                         ('Visual finish', recipe.get('material', {}).get('name')),
                         ('Finish assumption', recipe.get('material', {}).get('note')),
                         ('Family notes', recipe.get('modelling_choices', {}).get('family_note'))]:
        if value:
            provenance += [f'**{label}:** {text(value)}', '']
    provenance += ['These are saved catalogue references and modelling choices, not a claim of manufacturing certification.', '']
    for source in recipe.get('sources', []):
        url = str(source.get('url', ''))
        if urlsplit(url).scheme in ('https', 'http'):
            provenance.append(f'- [{text(source.get("title") or url)}]({quote(url, safe=":/?=&%#._-~")})')
    if (folder / 'three_d_model/model_notes.md').exists():
        provenance += ['', '[Detailed model notes](three_d_model/model_notes.md)']
    provenance += ['', '[Complete model recipe](three_d_model/parameters.json)', '', '</details>']
    metadata = ('<details>\n<summary>Complete part metadata</summary>\n\n'
                '[Source working.yaml](working.yaml)\n\n' + fenced(raw_yaml, 'yaml') + '\n\n</details>')
    downloads = []
    for path, label in [('three_d_model/model_full.glb', 'Full-detail 3D model (GLB)'),
                        ('three_d_model/model_full.stl', 'Full-detail mesh (STL)'),
                        ('working_mechanical_drawing_a4.pdf', 'Dimensioned drawing (PDF)'),
                        ('three_d_model/full/', 'Full-detail view drawings'),
                        ('label_drawer.svg', 'Drawer label (SVG)')]:
        if (folder / path).exists():
            downloads.append(f'[{label}]({path})')
    count = p.get('expected_components')
    assembly = 'This page documents a component rather than a complete project assembly. No installation sequence or tightening torque is specified by this record.'
    if isinstance(count, int) and count > 1:
        assembly += f' The saved model contains {count} separate solids; consult the model notes for their interpretation.'
    return template.substitute(title=text(title), summary=summary, family_anchor=FAMILY_ANCHORS.get(data.get('taxonomy_2'), 'hardware-catalogue'),
                               images=images, part_id=part_id, identifiers=' · '.join(identifiers),
                               dimensions='\n'.join(dimensions), dimension_status=text(str(recipe.get('dimension_status', 'unspecified')).replace('_', ' ')),
                               provenance='\n'.join(provenance), metadata=metadata,
                               downloads=' · '.join(downloads) or 'Open the part folder for the available files.', assembly=assembly)


def generate(root, records):
    template = Template((root / 'presentation/PART.template.md').read_text(encoding='utf-8'))
    prepared = []
    for folder, data, raw_yaml in records:
        page = folder / 'README.md'
        old = page.read_text(encoding='utf-8') if page.exists() else ''
        combine(old, '')  # Validate every existing marker before generating any assets.
        recipe = json.loads((folder / 'three_d_model/parameters.json').read_text(encoding='utf-8'))
        if recipe.get('parameters', {}).get('identity') != folder.name:
            raise ValueError(f'Model identity does not match part folder: {folder}')
        prepared.append((folder, data, raw_yaml, recipe, old))
    for folder, data, raw_yaml, recipe, old in prepared:
        body = render(folder, data, recipe, template, raw_yaml, previews(folder, recipe))
        write_changed(folder / 'README.md', combine(old, body))
    return len(prepared)
