"""Download CC0 Poly Haven texture sets + HDRIs used by the JV material library."""
import json, os, subprocess, sys
def api(path):
    return json.loads(subprocess.run(['curl', '-s', '--max-time', '60', '-A', 'jv-texture-fetch/1.0', 'https://api.polyhaven.com/' + path], capture_output=True, check=True).stdout)
OUT = '/home/claude/jv5/pbr'
TEX = {
 'red_brick': '2k', 'painted_plaster_wall': '2k', 'yellow_plaster': '1k', 'concrete_slab_wall': '2k',
 'granite_tile': '2k', 'grey_tiles': '2k', 'fine_grained_wood': '2k', 'dark_wood': '1k', 'wood_floor_deck': '2k',
 'leafy_grass': '2k', 'aerial_grass_rock': '2k', 'red_laterite_soil_stones': '2k', 'rock_boulder_dry': '1k',
 'asphalt_02': '2k', 'concrete_pavement': '1k', 'blue_floor_tiles_01': '1k', 'marble_01': '1k', 'clay_plaster': '1k',
 'rough_linen': '1k', 'granite_tile_04': '1k',
}
HDRI = {'qwantani_sunset_puresky': '4k', 'qwantani_dusk_2_puresky': '4k', 'rustig_koppie_puresky': '4k'}
def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000: return
    subprocess.run(['curl', '-s', '--max-time', '300', '-o', path, url], check=True)
info = {}
for a, res in TEX.items():
    files = api(f'files/{a}')
    meta = api(f'info/{a}')
    d = {}
    for key, mp in (('Diffuse', 'diff'), ('nor_gl', 'nor'), ('arm', 'arm')):
        if key not in files: print('no', key, a); continue
        r = res if res in files[key] else sorted(files[key])[0]
        url = files[key][r]['jpg']['url']
        p = f'{OUT}/src/{a}_{mp}.jpg'; get(url, p); d[mp] = p
    info[a] = {'dimensions_mm': meta.get('dimensions'), 'maps': d}
    print('tex', a, meta.get('dimensions'), flush=True)
for a, res in HDRI.items():
    files = api(f'files/{a}')
    url = files['hdri'][res]['hdr']['url']; get(url, f'{OUT}/hdri/{a}_{res}.hdr')
    url1 = files['hdri']['1k']['hdr']['url']; get(url1, f'{OUT}/hdri/{a}_1k.hdr')
    print('hdri', a, flush=True)
json.dump(info, open(f'{OUT}/library_src.json', 'w'), indent=1)
print('DONE')
