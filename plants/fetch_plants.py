"""Download Poly Haven CC0 plant models (glTF, 1k textures) into plants/src/<id>/."""
import json, os, subprocess, sys

IDS = ['jacaranda_tree', 'shrub_02', 'shrub_03', 'shrub_04', 'periwinkle_plant', 'nettle_plant', 'fern_02',
       'weed_plant_02', 'wild_rooibos_bush', 'calathea_orbifolia_01', 'anthurium_botany_01',
       'pachira_aquatica_01', 'potted_plant_01', 'potted_plant_02', 'potted_plant_04', 'shrub_sorrel_01']
ROOT = '/home/claude/jv5/plants/src'
UA = 'jv-texture-fetch/1.0'

def curl(url, out=None):
    cmd = ['curl', '-s', '-f', '-L', '-A', UA, '--retry', '3', url]
    if out: cmd += ['-o', out]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode: raise RuntimeError(f'{url} rc={r.returncode}')
    return r.stdout

for pid in (sys.argv[1:] or IDS):
    d = os.path.join(ROOT, pid); os.makedirs(os.path.join(d, 'textures'), exist_ok=True)
    files = json.loads(curl(f'https://api.polyhaven.com/files/{pid}'))
    g = files['gltf']['1k']['gltf']
    main = os.path.join(d, os.path.basename(g['url']))
    if not os.path.exists(main): curl(g['url'], main)
    for rel, info in g.get('include', {}).items():
        out = os.path.join(d, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if not os.path.exists(out): curl(info['url'], out)
    info = json.loads(curl(f'https://api.polyhaven.com/info/{pid}'))
    json.dump({'id': pid, 'name': info.get('name'), 'polycount': info.get('polycount'), 'dimensions': info.get('dimensions'),
               'authors': info.get('authors'), 'license': 'CC0'}, open(os.path.join(d, 'info.json'), 'w'), indent=1)
    print('ok', pid, info.get('polycount'), info.get('dimensions'), flush=True)
