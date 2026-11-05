"""Turn the downloaded Poly Haven sets into web maps and write the material library the site reads.
Outputs /home/claude/jv5/pbr/web/tex/<asset>_{d,n,arm}[-m].webp and /home/claude/jv5/pbr/web/library.json"""
import json, os
import numpy as np
from PIL import Image

SRC = '/home/claude/jv5/pbr/src'
OUT = '/home/claude/jv5/pbr/web/tex'
os.makedirs(OUT, exist_ok=True)
info = json.load(open('/home/claude/jv5/pbr/library_src.json'))

def lin(c):  # sRGB 0..1 → linear
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

# kit material → texture set, target mean albedo (linear, from the Blender materials), roughness/normal tweaks
L = {
 'brick':          dict(tex='red_brick',            target=(0.50, 0.25, 0.14), rough=1.0, nrm=1.0),
 'plaster':        dict(tex='painted_plaster_wall', target=(0.73, 0.70, 0.64), rough=1.0, nrm=0.8),
 'plaster_warm':   dict(tex='yellow_plaster',       target=(0.77, 0.61, 0.43), rough=1.0, nrm=0.8),
 'interior_wall':  dict(tex='painted_plaster_wall', target=(0.74, 0.69, 0.61), rough=1.0, nrm=0.5),
 'concrete':       dict(tex='concrete_slab_wall',   target=(0.48, 0.47, 0.45), rough=1.0, nrm=1.0),
 'stone_pave':     dict(tex='granite_tile',         target=(0.54, 0.51, 0.47), rough=0.9, nrm=1.0),
 'stone_dark':     dict(tex='granite_tile_04',      target=(0.06, 0.06, 0.065), rough=0.55, nrm=0.6),
 'kota':           dict(tex='grey_tiles',           target=(0.41, 0.42, 0.37), rough=0.45, nrm=0.6),
 'teak':           dict(tex='fine_grained_wood',    target=(0.28, 0.13, 0.055), rough=0.8, nrm=0.6),
 'walnut':         dict(tex='dark_wood',            target=(0.12, 0.065, 0.035), rough=0.7, nrm=0.6),
 'deck':           dict(tex='wood_floor_deck',      target=(0.34, 0.20, 0.10), rough=1.0, nrm=1.0),
 'lawn':           dict(tex='leafy_grass',          target=None, rough=1.0, nrm=1.0),
 'meadow':         dict(tex='aerial_grass_rock',    target=None, rough=1.0, nrm=1.0, scale=4.0),
 'earth':          dict(tex='red_laterite_soil_stones', target=None, rough=1.0, nrm=1.0),
 'granite_boulder': dict(tex='rock_boulder_dry',    target=(0.42, 0.39, 0.36), rough=1.0, nrm=1.0),
 'pool_tile':      dict(tex='blue_floor_tiles_01',  target=(0.30, 0.66, 0.70), rough=0.25, nrm=0.6, scale=0.8),
 'asphalt':        dict(tex='asphalt_02',           target=None, rough=1.0, nrm=1.0),
 'curb':           dict(tex='concrete_pavement',    target=(0.45, 0.44, 0.42), rough=1.0, nrm=1.0),
 'paint_a':        dict(tex='painted_plaster_wall', target=(0.48, 0.36, 0.26), rough=1.0, nrm=0.7),
 'paint_b':        dict(tex='painted_plaster_wall', target=(0.39, 0.42, 0.39), rough=1.0, nrm=0.7),
 'paint_c':        dict(tex='painted_plaster_wall', target=(0.56, 0.48, 0.38), rough=1.0, nrm=0.7),
 'marble':         dict(tex='marble_01',            target=(0.80, 0.79, 0.76), rough=0.35, nrm=0.4),
 'terracotta':     dict(tex='clay_plaster',         target=(0.46, 0.21, 0.11), rough=1.0, nrm=0.8, scale=0.7),
 'tile_roof':      dict(tex='clay_plaster',         target=(0.45, 0.16, 0.08), rough=1.0, nrm=1.0),
}
for nm, col in {'linen_white': (0.80, 0.78, 0.73), 'linen_oat': (0.66, 0.60, 0.50), 'fabric_charcoal': (0.075, 0.072, 0.07),
                'fabric_rust': (0.42, 0.15, 0.07), 'fabric_olive': (0.20, 0.21, 0.11), 'fabric_indigo': (0.05, 0.08, 0.17),
                'fabric_mustard': (0.55, 0.37, 0.08), 'fabric_ivory': (0.78, 0.74, 0.66), 'fabric_sand': (0.55, 0.45, 0.33),
                'mattress': (0.84, 0.82, 0.78), 'rug_wool': (0.62, 0.55, 0.44)}.items():
    L[nm] = dict(tex='rough_linen', target=col, rough=1.0, nrm=0.8, scale=0.35)
# atlas materials keep the baked Blender colour (albedo atlas) with physical surface values
ATLAS = {'art_earth': (0.9, 0), 'art_indigo': (0.9, 0), 'art_ochre': (0.9, 0), 'rug_dhurrie': (1.0, 0), 'cane': (0.7, 0),
         'book_0': (0.7, 0), 'book_1': (0.7, 0), 'book_2': (0.7, 0), 'book_3': (0.7, 0), 'book_4': (0.7, 0), 'book_5': (0.7, 0), 'book_6': (0.7, 0),
         'ceramic_white': (0.25, 0), 'ceramic_black': (0.3, 0), 'shade_paper': (0.9, 0), 'soil': (1.0, 0), 'flower': (0.8, 0),
         'grass': (1.0, 0), 'solar': (0.15, 0.3), 'tank': (0.5, 0), 'black': (0.6, 0), 'metal_dark': (0.4, 0.75), 'bronze': (0.35, 0.9),
         'brass': (0.3, 0.9), 'car_paint': (0.2, 0.6), 'fabric_leather': (0.6, 0), 'water': (0.1, 0), 'bark': (1.0, 0), 'palm_trunk': (1.0, 0)}

lib = {'materials': {}, 'textures': {}}
used = sorted({v['tex'] for v in L.values()})
for asset in used:
    maps = info[asset]['maps']; dims = info[asset]['dimensions_mm'] or [2000, 2000]
    d = Image.open(maps['diff']).convert('RGB')
    arr = np.asarray(d.resize((256, 256), Image.BOX), np.float64) / 255
    mean = lin(arr).reshape(-1, 3).mean(0)
    for key, src, sizes, q in (('d', maps['diff'], (1024, 512), 82), ('n', maps['nor'], (1024, 512), 88), ('arm', maps['arm'], (512, 256), 85)):
        im = Image.open(src).convert('RGB')
        for i, sz in enumerate(sizes):
            im.resize((sz, sz), Image.LANCZOS).save(f'{OUT}/{asset}_{key}{"-m" if i else ""}.webp', 'WEBP', quality=q, method=6)
    lib['textures'][asset] = {'size_m': dims[0] / 1000.0, 'mean': [round(x, 4) for x in mean]}
    print(asset, dims, np.round(mean, 3))
grey_done = set()
for nm, v in L.items():
    t = lib['textures'][v['tex']]; grey = False
    if v['target'] is None:
        tint = [1, 1, 1]
    else:
        r = [v['target'][i] / max(1e-4, t['mean'][i]) for i in range(3)]
        grey = bool(max(r) / min(r) > 1.6)
        if grey:   # strongly coloured photo → use its luminance and tint to the design colour
            ml = 0.2126 * t['mean'][0] + 0.7152 * t['mean'][1] + 0.0722 * t['mean'][2]
            tint = [round(float(min(6.0, v['target'][i] / max(1e-4, ml))), 4) for i in range(3)]
            if v['tex'] not in grey_done:
                im = Image.open(info[v['tex']]['maps']['diff']).convert('L').convert('RGB')
                for i, sz in enumerate((1024, 512)):
                    im.resize((sz, sz), Image.LANCZOS).save(f'{OUT}/{v["tex"]}_gd{"-m" if i else ""}.webp', 'WEBP', quality=82, method=6)
                grey_done.add(v['tex'])
        else:
            tint = [round(float(min(6.0, max(0.15, x))), 4) for x in r]
    lib['materials'][nm] = {'mode': 'photo', 'tex': v['tex'], 'grey': grey, 'tint': tint, 'size_m': v.get('scale', t['size_m']), 'rough': v['rough'], 'nrm': v['nrm']}
for nm, (r, m) in ATLAS.items():
    lib['materials'][nm] = {'mode': 'atlas', 'rough': r, 'metal': m}
json.dump(lib, open('/home/claude/jv5/pbr/web/library.json', 'w'), indent=1)
os.system(f'du -sh {OUT}')
