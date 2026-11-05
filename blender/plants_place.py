"""Real plants for the scenes: Poly Haven CC0 prototypes (plants/plants_lib.blend) placed as collection instances.
kit.tree / kit.shrub / kit.hedge and interior.plant call into this module unless JV_REAL_PLANTS=0."""
import bpy, json, math, os, random

LIB_BLEND = '/home/claude/jv5/plants/plants_lib.blend'
LIB = json.load(open('/home/claude/jv5/plants/web/plants_lib.json'))
P = LIB['protos']
ENABLED = os.environ.get('JV_REAL_PLANTS', '1') != '0'
_cols = {}

def proto_col(pid):
    if pid in _cols: return _cols[pid]
    if pid not in bpy.data.collections:
        with bpy.data.libraries.load(LIB_BLEND, link=False) as (src, dst):
            dst.collections = [pid]
    col = bpy.data.collections[pid]
    col['jv_plant_proto'] = 1
    _cols[pid] = col
    return col

def place(name, pid, x, y, z, h=None, scale=None, rot=None, coll=None, seed=0, sxy=1.0):
    """One plant instance: base at (x, y, z), height h (m) or a direct scale."""
    rnd = random.Random(seed)
    s = scale if scale is not None else (h / P[pid]['height'])
    e = bpy.data.objects.new(name, None)
    e.instance_type = 'COLLECTION'; e.instance_collection = proto_col(pid)
    e.location = (x, y, z)
    e.rotation_euler = (0, 0, rot if rot is not None else rnd.uniform(0, 2 * math.pi))
    e.scale = (s * sxy, s * sxy, s)
    e['jv_plant'] = pid
    (coll or bpy.context.scene.collection).objects.link(e)
    return e

def _pick(rnd, ids, h=None, lo=0.6, hi=1.8):
    """Random variant; with a target height, only variants that reach it at a believable scale (keeps leaf size real)."""
    if h is None: return rnd.choice(ids)
    ok = [i for i in ids if lo <= h / P[i]['height'] <= hi]
    if ok: return rnd.choice(ok)
    return max(ids, key=lambda i: P[i]['height']) if h > max(P[i]['height'] for i in ids) else min(ids, key=lambda i: P[i]['height'])
def _h(pid, h, hi=1.8):
    """Height actually used: never scale a plant past `hi`, so leaves stay life-size."""
    return min(h, P[pid]['height'] * hi)

# ── trees: one Poly Haven jacaranda in three levels of detail, scaled to the requested height ──
def tree(name, x, y, z=0.0, h=6.0, crown=3.0, seed=2, coll=None, **_):
    rnd = random.Random(seed)
    if name.startswith(('ctx_blk', 'north_tree')): pid = 'jac_dist'
    elif name.startswith(('low_tree',)) or (name.startswith('tree_') and os.environ.get('JV_SCENE') == 'villa'): pid = 'jac_far'
    else: pid = 'jac_near'
    w = P[pid]['width'] * h / P[pid]['height']
    sxy = max(0.75, min(1.2, 2 * crown / w))
    return place(name, pid, x, y, z, h=h * rnd.uniform(0.95, 1.05), coll=coll, seed=seed, sxy=sxy)

SPECIES = {
    'scrub': ['rooibos_0'],
    'bed': ['peri_1', 'peri_2', 'peri_3'],
    'tulsi': ['nettle_0', 'nettle_1'],
    'terrace': ['calathea_2', 'calathea_4', 'fern_2', 'anthurium_4'],
    'garden': ['calathea_0', 'calathea_2', 'calathea_4', 'fern_0', 'fern_2', 'anthurium_0', 'anthurium_2', 'shrub03_0', 'shrub03_1', 'shrub02_1', 'shrub02_3'],
    'ne_garden': ['peri_2', 'peri_3', 'peri_4', 'shrub03_0', 'shrub03_1', 'fern_0'],
    'hedge': ['shrub02_0', 'shrub02_1', 'shrub02_3'],
    'roof': ['weed_0', 'weed_1', 'weed_2', 'peri_0', 'peri_1'],
}
def _kind(name):
    if name.startswith('low_shrub'): return 'scrub'
    if name.startswith('bed_'): return 'bed'
    if 'tulsi' in name: return 'tulsi'
    if name.startswith('b09_plant'): return 'terrace'
    if name.startswith('b10_shrub'): return 'ne_garden'
    return 'garden'

def shrub(name, x, y, z=0.0, r=0.8, hgt=0.9, seed=3, coll=None, **_):
    """A planted clump: 1–4 real plants inside radius r, topping out near hgt."""
    rnd = random.Random(seed)
    kind = _kind(name); ids = SPECIES[kind]
    out = []
    if kind == 'scrub' and hgt > 0.85: ids = SPECIES['hedge']        # big hill bushes: the sapling shrubs
    # planted beds are dense: as many plants as their footprints need to fill the clump (max 8)
    p0 = _pick(rnd, ids, hgt); f0 = P[p0]['width'] * _h(p0, hgt) / P[p0]['height']
    n = 1 if kind in ('scrub',) else max(1, min(8 if kind != 'tulsi' else 3, int(round(0.7 * (2 * r) ** 2 / max(0.02, f0 * f0)))))
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        hh = hgt * rnd.uniform(0.8, 1.0) * (1.0 if i == 0 else rnd.uniform(0.7, 0.95))
        pid = p0 if i == 0 else _pick(rnd, ids, hh); hh = _h(pid, hh)
        a = i * ga + rnd.uniform(-0.3, 0.3); d = 0 if i == 0 else 0.8 * r * math.sqrt(i / n) * rnd.uniform(0.85, 1.1)
        if kind == 'scrub':     # spread to the clump radius
            s = hh / P[pid]['height']; sxy = max(0.7, min(1.6, (2 * r) / (P[pid]['width'] * s)))
            out.append(place(f'{name}_p{i}', pid, x, y, z, h=hh, coll=coll, seed=seed * 7 + i, sxy=sxy))
        else:
            out.append(place(f'{name}_p{i}', pid, x + math.cos(a) * d, y + math.sin(a) * d, z, h=hh, coll=coll, seed=seed * 7 + i))
    return out[0]

def hedge(name, x0, y0, x1, y1, z=0.0, h=1.0, coll=None, seed=4, **_):
    """A planted row: shrubs on the ground, low ground cover in roof planters."""
    rnd = random.Random(seed)
    roof = z > 1.0
    ids = SPECIES['roof' if roof else 'hedge']
    L = math.hypot(x1 - x0, y1 - y0); step = 0.8 if roof else 1.05
    n = max(1, int(L / step))
    out = []
    for i in range(n):
        t = (i + 0.5) / n
        hh = (h * rnd.uniform(0.85, 1.05)) if not roof else rnd.uniform(0.12, 0.3)
        pid = _pick(rnd, ids, None if roof else hh)
        if roof and pid.startswith('weed'): hh = rnd.uniform(0.06, 0.1)
        hh = _h(pid, hh)
        out.append(place(f'{name}_p{i}', pid, x0 + (x1 - x0) * t + rnd.uniform(-0.08, 0.08), y0 + (y1 - y0) * t + rnd.uniform(-0.08, 0.08),
                         z, h=hh, coll=coll, seed=seed * 131 + i))
    return out[0] if out else None

def indoor(name, x, y, z, coll, h=1.5, seed=1, big=True):
    rnd = random.Random(seed)
    ids = ['pachira_3', 'pachira_0', 'pachira_2', 'pachira_1'] if big else ['calathea_0', 'anthurium_2', 'anthurium_0', 'fern_0', 'potted02_0']
    pid = _pick(rnd, ids, h)
    return place(name + '_plant', pid, x, y, z, h=_h(pid, h), coll=coll, seed=seed)
