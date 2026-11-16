"""Validate local documentation coverage, links, metadata and preview provenance."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

from PIL import Image
from working_part_readme import START, END, PREVIEW_SIZE

ROOT = Path(__file__).resolve().parent


def main():
    links = previews = 0
    families = Counter()
    statuses = Counter()
    for source in sorted((ROOT / 'parts').glob('*/working.yaml')):
        folder = source.parent
        page = folder / 'README.md'
        body = page.read_text(encoding='utf-8')
        assert body.count(START) == body.count(END) == 1, page
        body = body.split(START, 1)[1].split(END, 1)[0]
        assert source.read_text(encoding='utf-8').rstrip() in body, f'Metadata changed: {page}'
        body = re.sub(r'(?ms)^(`{3,})[^\n]*\n.*?^\1[ \t]*$', '', body)
        assert re.findall(r'^## (.+)$', body, re.M) == ['Summary', 'Details', 'Parts', 'Assembly'], page
        assert f'`{folder.name}`' in body, page
        for target in re.findall(r'\]\(([^)]+)\)', body):
            if '://' in target:
                continue
            path, _, anchor = target.partition('#')
            destination = folder / unquote(path) if path else page
            assert destination.exists(), (page, target)
            if anchor:
                headings = re.findall(r'^##? (.+)$', destination.read_text(encoding='utf-8'), re.M)
                assert anchor in [heading.lower().replace(' ', '-') for heading in headings], (page, target)
            links += 1
        recipe = json.loads((folder / 'three_d_model/parameters.json').read_text())
        assert recipe['parameters']['identity'] == folder.name, folder
        statuses[recipe.get('dimension_status', 'unspecified')] += 1
        families[recipe['parameters']['family']] += 1
        manifest = json.loads((folder / 'three_d_model/readme_images.json').read_text())
        for filename, evidence in manifest.items():
            original = folder / 'three_d_model' / evidence['source']
            preview = folder / 'three_d_model' / filename
            assert evidence['source'] in ('render_high.png', 'render_product_high.png'), original
            assert hashlib.sha256(original.read_bytes()).hexdigest() == evidence['source_sha256'], original
            assert hashlib.sha256(preview.read_bytes()).hexdigest() == evidence['preview_sha256'], preview
            with Image.open(preview) as image:
                assert max(image.size) <= PREVIEW_SIZE, preview
            previews += 1
    report = {'part_pages': sum(statuses.values()), 'previews': previews, 'local_links': links,
              'model_dimension_status': dict(sorted(statuses.items())),
              'model_families': dict(sorted(families.items()))}
    (ROOT / 'presentation/part_readme_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
