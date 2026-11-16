"""Threaded rod catalogue: overall lengths, with metre stock from M3 upwards."""
from hardware_model_recipe import standard


def generate(**kwargs):
    options = []
    for size, row in standard()['families']['threaded_rod']['sizes'].items():
        diameter = float(size)
        for length in [50, 100, 150, 300] + ([1000] if diameter >= 3 else []):
            dimensions = dict(diameter_mm=diameter, length_mm=length, pitch_mm=row['pitch_mm'])
            options.append(dict(
                taxonomy_1='hardware', taxonomy_2='threaded_rod',
                taxonomy_3='m'+size.replace('.', '_'), taxonomy_7=f'{length}_mm_length',
                oobb_details=dict(oobb_name='threaded_rod', **dimensions),
                svg_details=[dict(svg_name='threaded_rod', **dimensions),
                    dict(svg_name='threaded_rod_drawing', filename='working_mechanical_drawing', **dimensions)]))
    return options
