"""Generate only seven finite representative proofs, never the entire catalogue."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import yaml
from working_three_d_model import ROOT, generate_assets

PROOFS = ['hardware_nut_m1', 'hardware_set_screw_m3_8_mm_length',
    'hardware_bolt_m8_150_mm_length', 'hardware_nut_m3_flanged',
    'hardware_nut_m8_coupling', 'hardware_set_screw_m6_nylon_white_15_mm_length',
    'hardware_washer_m8_penny']


def generate_proof(identity):
    folder = ROOT/'parts'/identity
    recipe = yaml.safe_load((folder/'working.yaml').read_text(encoding='utf-8'))['three_d_model_details']
    changed = generate_assets(recipe, folder)
    print(f'Proof {"generated" if changed else "cached"}: {identity}', flush=True)
    return identity


def preview_sheet():
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('arial.ttf', 15)
    except OSError:
        font = ImageFont.load_default(size=15)
    tile, label = 384, 44
    sheet = Image.new('RGB', (tile*4, (tile+label)*4), 'white')
    draw = ImageDraw.Draw(sheet)
    for i, identity in enumerate(PROOFS):
        for j, (file, view) in enumerate([('render_low.png', 'Isometric'), ('render_product_low.png', 'Product')]):
            index = i*2+j
            x, y = index % 4*tile, index//4*(tile+label)
            image = Image.open(ROOT/'parts'/identity/'three_d_model'/file).convert('RGB')
            image.thumbnail((tile, tile))
            sheet.paste(image, (x, y))
            title = identity.removeprefix('hardware_').replace('_mm_length', ' mm').replace('_', ' ')
            draw.text((x+9, y+tile+5), title, fill='#222222', font=font)
            draw.text((x+9, y+tile+23), view, fill='#555555', font=font)
    sheet.save(ROOT/'three_d_model_proofs.jpg', quality=92)


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(generate_proof, identity) for identity in PROOFS]):
            future.result()
    preview_sheet()
