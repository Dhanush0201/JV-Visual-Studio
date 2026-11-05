"""Bake a scene's Cycles lighting into textures / vertex colours and export a web GLB.
usage: python3 bake_export.py -- <blend> <out_dir> <name> <build_tex> <terrain_tex> <img_spp> <vtx_spp> [home]
Image groups get a lightmap atlas (AgX view transform applied, OIDN lightmap denoise).
Vegetation / far hills get per-vertex colours (same AgX look via a 3D LUT).
Water, glass and lamps are exported untextured for real-time materials in three.js."""
import sys, os, math, random, json, time
sys.path.insert(0, '/home/claude/jv5/blender')
import bpy, bmesh
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
BLEND, OUT, NAME = a[0], a[1], a[2]
BUILD_TEX, TERR_TEX, IMG_SPP, VTX_SPP = int(a[3]), int(a[4]), int(a[5]), int(a[6])
HOME = len(a) > 7 and a[7] == 'home'
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
def log(*m): print(f'[{time.time()-T0:7.1f}s]', *m, flush=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
vl = bpy.context.view_layer

# ── 1. strip stills-only content: grass, scrub scatter, particle systems, bevels ──
for o in list(bpy.data.objects):
    if o.name.startswith('grass') or o.name.endswith('_scrub'):
        bpy.data.objects.remove(o, do_unlink=True)
for o in bpy.data.objects:
    for m in list(o.modifiers):
        if m.type in ('PARTICLE_SYSTEM', 'BEVEL'):
            o.modifiers.remove(m)

def mats_of(o):
    return [s.material.name for s in o.material_slots if s.material]

def is_veg(o):
    n = o.name
    return any(k in n for k in ('_leaves', '_fronds', '_trunk', '_flowers')) or \
        (o.users_collection and o.users_collection[0].name == 'vegetation')

TERRAIN = {'ground_main', 'lawn', 'lawn_w', 'lawn_e', 'lawn_n'}

def prefix(o):
    n = o.name
    if HOME:
        if n[:1] == 'b' and n[1:3].isdigit() and n[3] == '_': return n[:3]
        if n.startswith('ctx_'): return 'ctx'
    return ''

def group_of(o):
    if o.type != 'MESH': return None
    if o.get('jv_water'): return 'water'
    ms = mats_of(o)
    p = prefix(o)
    pp = (p + '_') if p else ''
    if any(m in ('glass', 'glass_dark') for m in ms): return pp + 'glass'
    if any(m.startswith('lamp') for m in ms): return pp + 'lamp'
    if o.users_collection and o.users_collection[0].name == 'far': return 'far'
    if is_veg(o): return pp + 'veg'
    if HOME:
        if o.name.startswith('ctx_blk_'): return 'far_city'      # distant blocks: per-vertex light, keeps the atlas for the near street
        return 'ctx' if p == 'ctx' else (p or 'build')
    return 'terrain' if o.name in TERRAIN else 'build'

def atlas_of(g):
    if g in ('terrain', 'ctx'): return 'terrain'
    if g in ('water',) or g.startswith('far') or g.endswith('glass') or g.endswith('lamp') or g.endswith('veg'): return None
    return 'build'

groups = {}
for o in bpy.data.objects:
    g = group_of(o)
    if g: groups.setdefault(g, []).append(o)
log('groups', {k: len(v) for k, v in groups.items()})

# ── 2. thin vegetation for the web: keep ≤ ~28k leaf cards per group family, enlarge the rest ──
rnd = random.Random(3)
LEAF_BUDGET = 28000
for g, objs in groups.items():
    if not g.endswith('veg') and not g.startswith('far'): continue
    leafy = [o for o in objs if '_trunk' not in o.name and o.type == 'MESH' and len(o.data.polygons) > 60 and 'boulder' not in o.name and 'hills' not in o.name]
    total = sum(len(o.data.polygons) for o in leafy)
    if not total: continue
    keep = min(1.0, LEAF_BUDGET / total)
    grow = min(2.2, 1.0 / math.sqrt(keep)) if keep < 1 else 1.0
    log('thin', g, total, '-> keep', round(keep, 3), 'grow', round(grow, 2))
    for o in leafy:
        bm = bmesh.new(); bm.from_mesh(o.data)
        kill = set(f for f in bm.faces if rnd.random() > keep)
        for f in bm.faces:
            if f in kill: continue
            c = f.calc_center_median()
            for v in f.verts: v.co = c + (v.co - c) * grow
        bmesh.ops.delete(bm, geom=list(kill), context='FACES')
        bm.to_mesh(o.data); bm.free()

# ── 3. join each group into one object ──
def join(objs, name):
    objs = [o for o in objs if o.type == 'MESH']
    if not objs: return None
    for o in objs:
        if o.data.users > 1: o.data = o.data.copy()
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs, object=objs[0]):
        bpy.ops.object.join()
    ob = objs[0]; ob.name = name; ob.data.name = name
    return ob

joined = {}
for g, objs in groups.items():
    joined[g] = join(objs, 'JV_' + g)
log('joined', {g: len(o.data.polygons) for g, o in joined.items()})

# ── 4. AgX 3D LUT (scene view transform) for vertex colours ──
def build_lut(N=33, lo=-12.0, hi=5.0):
    vals = np.concatenate([[0.0], 2.0 ** np.linspace(lo, hi, N - 1)]).astype(np.float32)
    W, H = N * N, N
    img = bpy.data.images.new('lut_in', W, H, float_buffer=True, alpha=True)
    px = np.zeros((H, W, 4), np.float32)
    for k in range(N):
        for j in range(N):
            px[k, j * N:(j + 1) * N, 0] = vals
            px[k, j * N:(j + 1) * N, 1] = vals[j]
            px[k, j * N:(j + 1) * N, 2] = vals[k]
    px[..., 3] = 1
    img.pixels = px.ravel()
    path = os.path.join(OUT, '_lut.png')
    img.save_render(path, scene=sc)
    l2 = bpy.data.images.load(path)
    out = np.array(l2.pixels[:], np.float32).reshape(H, W, 4)[..., :3]
    lut = np.zeros((N, N, N, 3), np.float32)   # [r, g, b]
    for k in range(N):
        for j in range(N):
            lut[:, j, k] = out[k, j * N:(j + 1) * N]
    return vals, lut

def apply_lut(c, vals, lut):
    N = len(vals)
    lv = np.log2(np.maximum(vals[1:], 1e-12)); lo, hi = lv[0], lv[-1]
    def idx(x):
        x = np.maximum(x, 0)
        small = x < vals[1]
        f = np.where(small, x / vals[1], 1 + (np.log2(np.maximum(x, 1e-12)) - lo) / (hi - lo) * (N - 2))
        return np.clip(f, 0, N - 1 - 1e-4)
    fr, fg, fb = idx(c[:, 0]), idx(c[:, 1]), idx(c[:, 2])
    r0, g0, b0 = fr.astype(int), fg.astype(int), fb.astype(int)
    dr, dg, db = (fr - r0)[:, None], (fg - g0)[:, None], (fb - b0)[:, None]
    def L(i, j, k): return lut[i, j, k]
    res = (L(r0, g0, b0) * (1 - dr) * (1 - dg) * (1 - db) + L(r0 + 1, g0, b0) * dr * (1 - dg) * (1 - db) +
           L(r0, g0 + 1, b0) * (1 - dr) * dg * (1 - db) + L(r0, g0, b0 + 1) * (1 - dr) * (1 - dg) * db +
           L(r0 + 1, g0 + 1, b0) * dr * dg * (1 - db) + L(r0 + 1, g0, b0 + 1) * dr * (1 - dg) * db +
           L(r0, g0 + 1, b0 + 1) * (1 - dr) * dg * db + L(r0 + 1, g0 + 1, b0 + 1) * dr * dg * db)
    return res

LUTV, LUT = build_lut()
log('lut built')

# ── 5. bake helpers ──
sc.cycles.device = 'CPU'
sc.render.bake.margin = 8
sc.render.bake.use_clear = True

def select_only(objs):
    for o in bpy.context.scene.objects: o.select_set(False)
    for o in objs: o.select_set(True)
    vl.objects.active = objs[0]

def uv_unwrap(objs, margin):
    for o in objs:
        while o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers[0])
        o.data.uv_layers.new(name='bake')
    select_only(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')

def bake_image(objs, size, label):
    img = bpy.data.images.new('bk_' + label, size, size, float_buffer=True, alpha=False)
    for o in objs:
        for s in o.material_slots:
            m = s.material
            if not m: continue
            nt = m.node_tree
            node = nt.nodes.get('JV_BAKE') or nt.nodes.new('ShaderNodeTexImage')
            node.name = 'JV_BAKE'; node.image = img
            nt.nodes.active = node
    select_only(objs)
    sc.cycles.samples = IMG_SPP
    bpy.ops.object.bake(type='COMBINED', pass_filter={'DIRECT', 'INDIRECT', 'DIFFUSE', 'TRANSMISSION', 'EMIT'},
                        margin=8, use_clear=True, target='IMAGE_TEXTURES')
    px = np.array(img.pixels[:], np.float32).reshape(size, size, 4)
    try:
        import pyoidn
        den = pyoidn.denoise(np.ascontiguousarray(px[..., :3]), filter_type='RTLightmap')
        px[..., :3] = den
    except Exception as e:
        log('denoise failed', e)
    img.pixels = px.ravel()
    path = os.path.join(OUT, f'{NAME}_{label}.png')
    img.save_render(path, scene=sc)
    return path

def bake_vertex(obj, label):
    me = obj.data
    if 'bake' in me.color_attributes: me.color_attributes.remove(me.color_attributes['bake'])
    ca = me.color_attributes.new('bake', 'FLOAT_COLOR', 'CORNER')
    me.color_attributes.active_color = ca
    select_only([obj])
    sc.cycles.samples = VTX_SPP
    bpy.ops.object.bake(type='COMBINED', pass_filter={'DIRECT', 'INDIRECT', 'DIFFUSE', 'TRANSMISSION', 'EMIT'},
                        target='VERTEX_COLORS')
    n = len(ca.data)
    buf = np.zeros(n * 4, np.float32); ca.data.foreach_get('color', buf); buf = buf.reshape(n, 4)
    disp = apply_lut(buf[:, :3], LUTV, LUT)                       # display-referred sRGB
    lin = np.where(disp <= 0.04045, disp / 12.92, ((disp + 0.055) / 1.055) ** 2.4)   # store linear for glTF
    out = np.concatenate([lin, np.ones((n, 1), np.float32)], 1).astype(np.float32)
    ca.data.foreach_set('color', out.ravel())
    for c in list(me.color_attributes):
        if c.name != 'bake': me.color_attributes.remove(c)
    me.color_attributes.active_color = me.color_attributes['bake']

# ── 6. bake ──
atl = {}
for g, o in joined.items():
    t = atlas_of(g)
    if t and o: atl.setdefault(t, []).append(o)
paths = {}
for t, objs in atl.items():
    size = BUILD_TEX if t == 'build' else TERR_TEX
    uv_unwrap(objs, 0.0015 if t == 'build' else 0.003)
    log('unwrapped', t, size, [o.name for o in objs])
    paths[t] = bake_image(objs, size, t)
    log('baked image', t, paths[t])
for g, o in joined.items():
    if o and (g.endswith('veg') or g.startswith('far')):
        bake_vertex(o, g)
        log('baked vertex', g, len(o.data.vertices))

# ── 7. export materials ──
def basic_mat(name, color=(1, 1, 1, 1), image=None, vcol=False):
    m = bpy.data.materials.new(name); nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = color
    b.inputs['Roughness'].default_value = 1.0
    if image:
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = image
        nt.links.new(tn.outputs['Color'], b.inputs['Base Color'])
    if vcol:
        cn = nt.nodes.new('ShaderNodeVertexColor'); cn.layer_name = 'bake'
        nt.links.new(cn.outputs['Color'], b.inputs['Base Color'])
    return m

loaded = {t: bpy.data.images.load(p) for t, p in paths.items()}
for t, im in loaded.items(): im.colorspace_settings.name = 'sRGB'
MAT = {t: basic_mat('M_' + t, image=im) for t, im in loaded.items()}
MAT['vcol'] = basic_mat('M_vcol', vcol=True)
MAT['water'] = basic_mat('M_water', (0.06, 0.32, 0.36, 1))
MAT['glass'] = basic_mat('M_glass', (0.05, 0.07, 0.08, 1))
MAT['lamp'] = basic_mat('M_lamp', (1.0, 0.78, 0.5, 1))
MAT['lamp_pool'] = basic_mat('M_lamp_pool', (0.5, 0.95, 1.0, 1))

export = []
for g, o in joined.items():
    if not o: continue
    t = atlas_of(g)
    if t: key = t
    elif g.endswith('veg') or g.startswith('far'): key = 'vcol'
    elif g == 'water': key = 'water'
    elif g.endswith('glass'): key = 'glass'
    elif g.endswith('lamp'):
        key = 'lamp_pool' if any(m == 'lamp_pool' for m in mats_of(o)) and all(m == 'lamp_pool' for m in mats_of(o)) else 'lamp'
    else: key = 'lamp'
    o.data.materials.clear(); o.data.materials.append(MAT[key])
    if key not in ('vcol',):
        for c in list(o.data.color_attributes): o.data.color_attributes.remove(c)
    if not t:
        while o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers[0])
    export.append(o)

select_only(export)
glb = os.path.join(OUT, f'{NAME}.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True,
                          export_texcoords=True, export_normals=False, export_materials='EXPORT',
                          export_vertex_color='ACTIVE', export_image_format='WEBP', export_image_quality=82,
                          export_cameras=False, export_lights=False, export_yup=True)
log('exported', glb, os.path.getsize(glb) // 1024, 'KB')

# ── 8. sky panorama for the web background / reflections ──
for o in bpy.context.scene.objects:
    o.hide_render = True
cd = bpy.data.cameras.new('pano'); cd.type = 'PANO'
try: cd.panorama_type = 'EQUIRECTANGULAR'
except Exception: cd.cycles.panorama_type = 'EQUIRECTANGULAR'
co = bpy.data.objects.new('pano', cd); sc.collection.objects.link(co)
co.location = (0, 0, 2); co.rotation_euler = (math.radians(90), 0, math.radians(-90))
co.hide_render = False
sc.camera = co
sc.render.resolution_x, sc.render.resolution_y = 2048, 1024
sc.cycles.samples = 16
sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
sc.render.filepath = os.path.join(OUT, f'{NAME}_sky.jpg')
bpy.ops.render.render(write_still=True)
log('sky', sc.render.filepath)
json.dump({'groups': {g: len(o.data.polygons) for g, o in joined.items() if o}, 'seconds': time.time() - T0},
          open(os.path.join(OUT, f'{NAME}_meta.json'), 'w'), indent=1)
log('DONE')
