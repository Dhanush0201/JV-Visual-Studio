"""Build the web plant library from Poly Haven CC0 models.
Outputs: plants_lib.blend (one collection per prototype, for the Blender scenes),
         web/plants_raw.glb (all prototypes, for post-processing), web/tex/*.webp, web/plants_lib.json."""
import bpy, sys, os, json, glob, math
sys.path.insert(0, '/home/claude/jv5/plants')
import plantkit as pk, twigquads as tq
from mathutils import Vector

OUT = '/home/claude/jv5/plants'
os.makedirs(f'{OUT}/web/tex', exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# short name, Poly Haven id, max variants
ASSETS = [('shrub02', 'shrub_02', 4), ('shrub03', 'shrub_03', 4), ('peri', 'periwinkle_plant', 6), ('nettle', 'nettle_plant', 6),
          ('fern', 'fern_02', 4), ('weed', 'weed_plant_02', 5), ('rooibos', 'wild_rooibos_bush', 5), ('calathea', 'calathea_orbifolia_01', 5),
          ('anthurium', 'anthurium_botany_01', 6), ('pachira', 'pachira_aquatica_01', 6), ('potted02', 'potted_plant_02', 1), ('potted04', 'potted_plant_04', 1)]
JAC = [('jac_near', dict(twigs=30000, grow=1.55, br_min=1.0, br=0.2, tr=0.04)),
       ('jac_far', dict(twigs=10000, grow=2.9, br_min=1.5, br=0.15, tr=0.02)),
       ('jac_dist', dict(twigs=3200, grow=5.2, br_min=2.5, br=0.12, tr=0.01))]

protos = {}
def finish(o, pid, src):
    o.name = pid; o.data.name = pid
    pk.apply_all(o)
    h, w = pk.ground_centre(o)
    col = bpy.data.collections.new(pid); sc.collection.children.link(col)
    for c in list(o.users_collection): c.objects.unlink(o)
    col.objects.link(o)
    protos[pid] = {'src': src, 'height': round(h, 3), 'width': round(w, 3), 'tris': pk.tris(o),
                   'materials': [s.material.name for s in o.material_slots if s.material]}
    print('proto', pid, protos[pid], flush=True)

def join(objs):
    for x in bpy.context.selected_objects: x.select_set(False)
    for x in objs: x.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    return objs[0]

# ── jacaranda LODs (9 m tree) ──
for pid, P in JAC:
    o = pk.import_asset('jacaranda_tree')[0]
    o.scale = (9.0 / o.dimensions.z,) * 3; pk.apply_all(o); pk.ground_centre(o)
    tq.twigs_to_quads(o, lambda n: 'leaves' in n, P['twigs'], P['grow'], seed=3)
    pk.drop_small_islands(o, lambda n: 'branches' in n, P['br_min'])
    pk.decimate_mat(o, lambda n: 'branches' in n, P['br'])
    pk.decimate_mat(o, lambda n: 'trunk' in n, P['tr'])
    finish(o, pid, 'jacaranda_tree')

# ── multi-variant assets: variants sit side by side, so group objects by footprint overlap ──
def bbox(o):
    ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(w.x for w in ws), min(w.y for w in ws), max(w.x for w in ws), max(w.y for w in ws)]
for short, src, nmax in ASSETS:
    objs = pk.import_asset(src)
    for o in objs: pk.apply_all(o)
    groups = []
    for o in sorted(objs, key=lambda o: bbox(o)[0]):
        b = bbox(o)
        for g in groups:
            gb = g['bb']
            if b[0] < gb[2] + 0.02 and b[2] > gb[0] - 0.02 and b[1] < gb[3] + 0.02 and b[3] > gb[1] - 0.02:
                g['objs'].append(o); g['bb'] = [min(gb[0], b[0]), min(gb[1], b[1]), max(gb[2], b[2]), max(gb[3], b[3])]; break
        else:
            groups.append({'objs': [o], 'bb': b})
    for k, g in enumerate(groups[:nmax]):
        for o in g['objs']:
            # heavy non-leaf parts (dirt, pebbles) are decimated hard; leaves stay
            t = pk.tris(o)
            alpha = any(s.material and s.material.get('jv_alpha') for s in o.material_slots)
            if t > 20000 and not alpha:
                pk.decimate_mat(o, lambda n: True, 3000 / t)
        o = join(g['objs'])
        finish(o, f'{short}_{k}', src)
    for g in groups[nmax:]:
        for o in g['objs']: bpy.data.objects.remove(o, do_unlink=True)

# ── web textures: per material RGBA colour (alpha from the real map), normal, roughness ──
from PIL import Image
import numpy as np
mats = {}
def img_path(im):
    p = bpy.path.abspath(im.filepath) if im.filepath else ''
    return p if p and os.path.exists(p) else None
for m in bpy.data.materials:
    if not m.node_tree or not any(m.name in p['materials'] for p in protos.values()): continue
    nodes = [n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
    def find(*keys):
        for n in nodes:
            nm = n.image.name.lower()
            if any(k in nm for k in keys) and img_path(n.image): return img_path(n.image)
        return None
    diff = find('diff'); nor = find('nor_gl', 'normal'); arm = find('arm'); rough = find('rough')
    alpha = m.get('jv_alpha')
    if not diff: print('no diffuse for', m.name); continue
    import re
    base = re.sub(r'\.\d+$', '', m.name)
    if base in mats: continue
    safe = base
    rec = {'alpha': bool(alpha)}
    d = Image.open(diff).convert('RGB')
    if alpha:
        a = Image.open(alpha).convert('L').resize(d.size)
        d = Image.merge('RGBA', (*d.split(), a))
    for sz, sfx in ((1024, ''), (512, '-m')):
        d.resize((sz, sz), Image.LANCZOS).save(f'{OUT}/web/tex/{safe}_c{sfx}.webp', quality=88, method=6)
    rec['c'] = f'{safe}_c'
    if nor:
        n = Image.open(nor).convert('RGB')
        for sz, sfx in ((512, ''), (256, '-m')): n.resize((sz, sz), Image.LANCZOS).save(f'{OUT}/web/tex/{safe}_n{sfx}.webp', quality=86, method=6)
        rec['n'] = f'{safe}_n'
    r = None
    if arm: r = Image.open(arm).convert('RGB').split()[1]
    elif rough: r = Image.open(rough).convert('L')
    if r is not None:
        for sz, sfx in ((512, ''), (256, '-m')): r.resize((sz, sz), Image.LANCZOS).save(f'{OUT}/web/tex/{safe}_r{sfx}.webp', quality=86, method=6)
        rec['r'] = f'{safe}_r'
    rec['mean'] = [round(float(x), 4) for x in (np.asarray(d.convert('RGB').resize((64, 64)), np.float32) / 255).reshape(-1, 3).mean(0)]
    mats[base] = rec
json.dump({'protos': protos, 'materials': mats, 'license': 'Poly Haven CC0', 'jacaranda_height_m': 9.0},
          open(f'{OUT}/web/plants_lib.json', 'w'), indent=1)

# ── save the Blender library and the raw web GLB ──
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/plants_lib.blend')
for x in bpy.context.selected_objects: x.select_set(False)
for c in sc.collection.children:
    for o in c.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=f'{OUT}/web/plants_raw.glb', export_format='GLB', use_selection=True, export_apply=True,
                          export_texcoords=True, export_normals=True, export_materials='EXPORT', export_image_format='JPEG',
                          export_cameras=False, export_lights=False, export_yup=True)
print('DONE', len(protos), 'protos', sum(p['tris'] for p in protos.values()), 'tris', flush=True)
