import json
from pathlib import Path
from string import Template
import tempfile
import unittest

from PIL import Image
import working_part_readme as docs


class PartReadmeTests(unittest.TestCase):
    def test_length_taxonomy_is_not_repeated_as_a_style(self):
        title, _ = docs.identity({'taxonomy_2': 'bolt', 'taxonomy_4': '40_mm_length'},
                                 {'parameters': {'nominal_diameter_mm': 4, 'length_mm': 40}}, 'hardware_bolt_m4_40_mm_length')
        self.assertEqual('M4 × 40 mm hex bolt', title)

    def test_notes_and_manual_edits_survive(self):
        body = docs.START + '\nnew\n' + docs.END
        first = docs.combine('Original [notes](working.yaml).', body)
        second = docs.combine(first + '\nManual addition.', body)
        self.assertEqual(1, second.count('Original [notes]'))
        self.assertIn('Manual addition.', second)
        with self.assertRaises(ValueError):
            docs.combine(docs.START, body)

    def test_missing_files_are_not_linked_and_metadata_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'hardware_washer_m3'
            folder.mkdir()
            template = Template((docs.Path(__file__).resolve().parents[1] / 'presentation/PART.template.md').read_text())
            raw = 'notes: "``` and | brackets []"\n'
            recipe = {'parameters': {'nominal_diameter_mm': 3, 'hole_diameter_mm': 3.2,
                                    'outer_diameter_mm': 7, 'height_mm': 0.5},
                      'dimension_status': 'approximate_visual_model'}
            result = docs.render(folder, {'taxonomy_2': 'washer'}, recipe, template, raw, 'No image')
            self.assertNotIn('model_full.stl', result)
            self.assertNotIn('model_full.glb', result)
            self.assertIn('approximate visual model', result)
            self.assertIn(raw.rstrip(), result)
            self.assertIn('````yaml', result)
            self.assertIn('| Hole diameter | 3.2 |', result)

    def test_only_full_renders_are_used_and_cached_images_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            model = folder / 'three_d_model'
            model.mkdir()
            Image.new('RGB', (700, 350), 'red').save(model / 'render_high.png')
            original = (model / 'render_high.png').read_bytes()
            with self.assertRaises(ValueError):
                docs.previews(folder, {'renders': {'high': {'variant': 'display'}}})
            recipe = {'renders': {'high': {'variant': 'full'}}}
            docs.previews(folder, recipe)
            preview = model / 'readme_isometric.png'
            before = preview.read_bytes()
            docs.previews(folder, recipe)
            self.assertEqual(before, preview.read_bytes())
            with Image.open(preview) as image:
                self.assertEqual((512, 256), image.size)
            preview.write_bytes(b'damaged')
            docs.previews(folder, recipe)
            self.assertEqual(before, preview.read_bytes())
            self.assertEqual(original, (model / 'render_high.png').read_bytes())


if __name__ == '__main__':
    unittest.main()
