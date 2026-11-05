"""Web bake for real-material rendering.
Lighting and colour are baked separately so the browser can show real tiling PBR textures:
  * lightmap atlas  = diffuse light only (direct + indirect, no surface colour), linear, encoded /k as sRGB 8-bit
  * albedo atlas    = surface colour only, for materials that keep their Blender colour (art, rugs, books…)
  * UV0 'mat'       = world-scale box projection in metres (texture tiling in three.js)
  * UV1 'lm'        = lightmap layout
  * vegetation / far hills: per-vertex colour (light × colour), linear /kv
World = Poly Haven HDRI (rotated so its sun sits at the design azimuth); the sun hotspot is clamped out of the
HDRI and replaced by a matching sun lamp for clean, sharp baked shadows.
usage: python3 bake_pbr.py -- <blend> <out_dir> <name> <config.json>"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/jv5/blender')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

a = sys.argv[sys.argv.index('--') + 1:]
BLEND, OUT, NAME = a[0], a[1], a[2]
CFG = json.load(open(a[3]))
HOME = CFG.get('home', False)
HERO = CFG.get('hero')
ATL = CFG['atlases']            # {atlas: [size, spp]}
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
def log(*m): print(f'[{time.time() - T0:7.1f}s]', *m, flush=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene; vl = bpy.context.view_layer
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'

# ── 1. world: HDRI with the sun clamped out + a matching sun lamp ──
H = CFG['hdri']
def load_hdr(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[..., :3]
    return im, px
_, px1 = load_hdr(H['file_1k'])
hh, ww = px1.shape[:2]
lum = px1 @ np.array([0.2126, 0.7152, 0.0722], np.float32)
vv, uu = np.unravel_index(np.argmax(lum), lum.shape)
# Blender pixel rows run bottom→top, so row index = v * h
u = (uu + 0.5) / ww; v = (vv + 0.5) / hh
phi = (u - 0.5) * 2 * math.pi; th = (v - 0.5) * math.pi
d_h = Vector((-math.cos(phi) * math.cos(th), math.sin(phi) * math.cos(th), math.sin(th)))
best = None
for k in range(720):
    al = math.radians(k * 0.5)
    d = Matrix.Rotation(-al, 3, 'Z') @ d_h
    az = math.degrees(math.atan2(d.x, d.y)) % 360
    err = abs((az - H['sun_az'] + 180) % 360 - 180)
    if best is None or err < best[0]: best = (err, al, d)
_, ALPHA, SUN_DIR = best
# solid angle per pixel and the energy above the clamp threshold
rows = (np.arange(hh) + 0.5) / hh
elev = (rows - 0.5) * math.pi
dw = (2 * math.pi / ww) * (math.pi / hh) * np.cos(elev)[:, None]
sky_ref = np.percentile(lum, 99.0)
CLAMP = float(max(sky_ref * H.get('clamp_x', 8.0), 1e-3))
over = np.clip(lum - CLAMP, 0, None)
use_sun = H.get('sun', True) and over.max() > 0 and SUN_DIR.z > -0.02
E_raw = float((over * dw).sum())
up = elev > 0
dw2 = np.broadcast_to(dw, lum.shape)          # per-pixel solid angle, full width
L_up = float((np.minimum(lum, CLAMP) * dw2)[up].sum() / dw2[up].sum())
if H.get('target_sun'):   H['strength'] = H['target_sun'] / max(E_raw, 1e-6)
elif H.get('target_sky'): H['strength'] = H['target_sky'] / max(L_up, 1e-6)
E_sun = E_raw * H.get('strength', 1.0)
log('hdri levels', 'E_raw', round(E_raw, 3), 'L_up', round(L_up, 4), 'strength', round(H.get('strength', 1.0), 4))
wgt = (over * dw)[..., None]
sun_col = (px1 * wgt).sum((0, 1)) / max(1e-9, wgt.sum())
sun_col = sun_col / max(sun_col)
log('hdri sun', 'uv', round(u, 4), round(v, 4), 'elev', round(math.degrees(th), 1), 'rot', round(math.degrees(ALPHA), 1),
    'clamp', round(CLAMP, 2), 'E_sun', round(E_sun, 3), 'col', np.round(sun_col, 3), 'use', use_sun)

for o in list(bpy.data.objects):
    if o.type == 'LIGHT' and o.data.type == 'SUN': bpy.data.objects.remove(o, do_unlink=True)
w = bpy.data.worlds.new('HDRI'); sc.world = w; nt = w.node_tree
for n in list(nt.nodes): nt.nodes.remove(n)
tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
mp.inputs['Rotation'].default_value = (0, 0, ALPHA)
env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(H['file'])
nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
col_out = env.outputs['Color']
if use_sun:
    mn = nt.nodes.new('ShaderNodeVectorMath'); mn.operation = 'MINIMUM'
    mn.inputs[1].default_value = (CLAMP, CLAMP, CLAMP)
    nt.links.new(env.outputs['Color'], mn.inputs[0]); col_out = mn.outputs['Vector']
bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = H.get('strength', 1.0)
wo = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(col_out, bg.inputs['Color']); nt.links.new(bg.outputs[0], wo.inputs[0])
if use_sun:
    ld = bpy.data.lights.new('SunHDRI', 'SUN'); ld.energy = E_sun; ld.angle = math.radians(H.get('sun_angle', 0.7))
    ld.color = tuple(float(c) for c in sun_col)
    so = bpy.data.objects.new('SunHDRI', ld); sc.collection.objects.link(so)
    so.rotation_euler = (-SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
for o in bpy.data.objects:     # scene area lights: optional scaling for the new sky level
    if o.type == 'LIGHT' and o.data.type in ('AREA', 'POINT'): o.data.energy *= CFG.get('light_k', 1.0)

# ── 2. strip stills-only content, apply modifiers, bake-friendly metals ──
for o in list(bpy.data.objects):
    if o.name.startswith('grass') or o.name.endswith('_scrub'):
        bpy.data.objects.remove(o, do_unlink=True)
for o in bpy.data.objects:
    for m in list(o.modifiers):
        if m.type == 'PARTICLE_SYSTEM': o.modifiers.remove(m)
for m in bpy.data.materials:
    if not m.node_tree: continue
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED' and n.inputs['Metallic'].default_value > 0.5 and not n.inputs['Metallic'].is_linked:
            n.inputs['Metallic'].default_value = 0.0
            c = n.inputs['Base Color'].default_value
            n.inputs['Base Color'].default_value = (c[0] * 0.7, c[1] * 0.7, c[2] * 0.7, 1)
dg = bpy.context.evaluated_depsgraph_get()
for o in list(bpy.data.objects):
    if o.type == 'MESH' and len(o.modifiers):
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        o.modifiers.clear(); o.data = me
log('modifiers applied')

def mats_of(o): return [s.material.name for s in o.material_slots if s.material]
def is_veg(o):
    n = o.name
    return any(k in n for k in ('_leaves', '_fronds', '_trunk', '_flowers', '_stems')) or \
        (o.users_collection and o.users_collection[0].name == 'vegetation')
TERRAIN = {'ground_main', 'lawn', 'lawn_w', 'lawn_e', 'lawn_n'}
def centre(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(bb, Vector()) / 8
def prefix(o):
    n = o.name
    if HOME:
        if n.startswith('int_'): return 'b11'
        if n[:1] == 'b' and n[1:3].isdigit() and n[3] == '_': return n[:3]
        if n.startswith('ctx_'): return 'ctx'
        return ''
    return 'int' if n.startswith('int_') else ''
def group_of(o):
    if o.type != 'MESH': return None
    if o.get('jv_water'): return 'water'
    ms = mats_of(o); p = prefix(o); pp = (p + '_') if p else ''
    if any(m in ('glass', 'glass_dark') for m in ms): return pp + 'glass'
    if any(m.startswith('lamp') for m in ms): return pp + 'lamp'
    if o.users_collection and o.users_collection[0].name == 'far': return 'far'
    if is_veg(o): return pp + 'veg'
    if HOME:
        if o.name.startswith('ctx_blk_'): return 'far_city'
        return p or 'build'
    if p == 'int': return 'int'
    if o.name in TERRAIN: return 'terrain'
    if HERO:
        c = centre(o)
        if HERO[0] <= c.x <= HERO[2] and HERO[1] <= c.y <= HERO[3]: return 'hero'
    return 'build'
def atlas_of(g):
    if g in ('terrain', 'ctx'): return 'terrain'
    if g in ('water',) or g.startswith('far') or g.endswith('glass') or g.endswith('lamp') or g.endswith('veg'): return None
    if g in ('int', 'b11'): return 'int'
    if g == 'hero': return 'hero'
    return 'build'

# ── 3. world-scale material UVs (metres), before joining ──
def mat_uv(o):
    me = o.data
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name='mat')
    bm = bmesh.new(); bm.from_mesh(me)
    uvl = bm.loops.layers.uv.verify()
    M = o.matrix_world; N = M.to_3x3().inverted().transposed()
    for f in bm.faces:
        n = (N @ f.normal).normalized()
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for lp in f.loops:
            p = M @ lp.vert.co
            if az >= ax and az >= ay: lp[uvl].uv = (p.x, p.y if n.z > 0 else -p.y)
            elif ax >= ay: lp[uvl].uv = (p.y if n.x > 0 else -p.y, p.z)
            else: lp[uvl].uv = (-p.x if n.y > 0 else p.x, p.z)
    bm.to_mesh(me); bm.free()

groups = {}
for o in bpy.data.objects:
    if o.name not in sc.objects: continue          # plant prototype meshes live outside the scene
    g = group_of(o)
    if g: groups.setdefault(g, []).append(o)
for g, objs in groups.items():
    if atlas_of(g):
        for o in objs:
            if o.data.users > 1: o.data = o.data.copy()
            mat_uv(o)
log('groups', {k: len(v) for k, v in groups.items()})
# thin far vegetation for the web: keep a leaf-card budget per group, enlarge the survivors
import random
rnd = random.Random(3)
for g, budget in CFG.get('thin', {}).items():
    leafy = [o for o in groups.get(g, []) if o.type == 'MESH' and '_trunk' not in o.name and len(o.data.polygons) > 60 and 'boulder' not in o.name]
    total = sum(len(o.data.polygons) for o in leafy)
    if not total or total <= budget: continue
    keep = budget / total; grow = min(2.0, 1.0 / math.sqrt(keep))
    for o in leafy:
        if o.data.users > 1: o.data = o.data.copy()
        bm = bmesh.new(); bm.from_mesh(o.data)
        kill = [f for f in bm.faces if rnd.random() > keep]
        ks = set(kill)
        for f in bm.faces:
            if f in ks: continue
            c = f.calc_center_median()
            for v in f.verts: v.co = c + (v.co - c) * grow
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        bm.to_mesh(o.data); bm.free()
    log('thin', g, total, '->', budget, 'grow', round(grow, 2))

def join(objs, name):
    objs = [o for o in objs if o.type == 'MESH']
    if not objs: return None
    for o in objs:
        if o.data.users > 1: o.data = o.data.copy()
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs, object=objs[0]):
        bpy.ops.object.join()
    ob = objs[0]; ob.name = name; ob.data.name = name
    return ob
joined = {g: join(objs, 'JV_' + g) for g, objs in groups.items()}
log('joined', {g: len(o.data.polygons) for g, o in joined.items() if o})

# ── real plants: instance list for the web (prototype, transform in glTF space, build group, sky visibility) ──
PLIB = json.load(open('/home/claude/jv5/plants/web/plants_lib.json'))['protos']
C = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))      # Blender z-up -> glTF y-up
Ci = C.inverted()
dg_p = bpy.context.evaluated_depsgraph_get()
rays = []
for i in range(32):                                  # cosine-weighted upper hemisphere
    u, v = (i + 0.5) / 32, (i * 0.618034) % 1.0
    r, ph = math.sqrt(u), 2 * math.pi * v
    rays.append(Vector((r * math.cos(ph), r * math.sin(ph), math.sqrt(max(0.0, 1 - u)))))
plants = []
for o in sc.objects:
    pid = o.get('jv_plant')
    if not pid: continue
    p = prefix(o); g = ((p + '_') if p else '') + 'veg'
    top = o.matrix_world.translation + Vector((0, 0, PLIB[pid]['height'] * o.scale.z * 1.02 + 0.05))
    hit = 0
    for d in rays:
        ok, *_ = sc.ray_cast(dg_p, top, d, distance=60.0)
        hit += ok
    sv = 1.0 - hit / len(rays)
    M = C @ o.matrix_world @ Ci
    plants.append({'p': pid, 'g': g, 'sv': round(sv, 3), 'm': [round(M[r][c], 5) for c in range(4) for r in range(4)]})
log('plants', len(plants), 'mean sky vis', round(sum(x['sv'] for x in plants) / max(1, len(plants)), 3))

# ── 4. bake helpers ──
sc.render.bake.margin = 6
def select_only(objs):
    for o in bpy.context.scene.objects: o.select_set(False)
    for o in objs: o.select_set(True)
    vl.objects.active = objs[0]
def lm_unwrap(objs, margin):
    for o in objs:
        me = o.data
        if 'lm' in me.uv_layers: me.uv_layers.remove(me.uv_layers['lm'])
        lm = me.uv_layers.new(name='lm'); me.uv_layers.active = lm
    select_only(objs)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        o.data.uv_layers.active = o.data.uv_layers['lm']
        o.data.uv_layers['mat'].active_render = True
def set_target(objs, img):
    for o in objs:
        for s in o.material_slots:
            m = s.material
            if not m: continue
            nt = m.node_tree
            node = nt.nodes.get('JV_BAKE') or nt.nodes.new('ShaderNodeTexImage')
            node.name = 'JV_BAKE'; node.image = img
            uvn = nt.nodes.get('JV_BAKE_UV') or nt.nodes.new('ShaderNodeUVMap')
            uvn.name = 'JV_BAKE_UV'; uvn.uv_map = 'lm'
            if not node.inputs['Vector'].is_linked: nt.links.new(uvn.outputs['UV'], node.inputs['Vector'])
            nt.nodes.active = node
def to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)
def save8(arr, path):
    from PIL import Image
    im = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)[::-1]   # Blender rows are bottom-up
    Image.fromarray(im, 'RGB').save(path)
def bake(objs, size, label, spp, kind):
    img = bpy.data.images.new(f'bk_{label}_{kind}', size, size, float_buffer=True, alpha=False)
    set_target(objs, img); select_only(objs)
    sc.cycles.samples = spp
    filt = {'DIRECT', 'INDIRECT'} if kind == 'light' else {'COLOR'}
    bpy.ops.object.bake(type='DIFFUSE', pass_filter=filt, margin=6, use_clear=True, target='IMAGE_TEXTURES')
    px = np.array(img.pixels[:], np.float32).reshape(size, size, 4)[..., :3]
    return px

# ── 5. bake the atlases ──
atl = {}
for g, o in joined.items():
    t = atlas_of(g)
    if t and o: atl.setdefault(t, []).append(o)
meta = {'atlases': {}, 'hdri': {'rot_deg': math.degrees(ALPHA), 'sun_dir': list(SUN_DIR), 'E_sun': E_sun if use_sun else 0, 'clamp': CLAMP}}
# JV_REUSE=1: keep the lightmap/albedo PNGs and k of the previous run (the unwrap is deterministic)
old_meta = None
if os.environ.get('JV_REUSE') and os.path.exists(f'{OUT}/{NAME}_meta.json'):
    old_meta = json.load(open(f'{OUT}/{NAME}_meta.json'))
for t, objs in atl.items():
    size, spp = ATL[t]
    lm_unwrap(objs, 0.002 if size >= 2048 else 0.003)
    log('unwrapped', t, size, [o.name for o in objs])
    if old_meta and t in old_meta.get('atlases', {}) and os.path.exists(f'{OUT}/{NAME}_lm_{t}.png') and os.path.exists(f'{OUT}/{NAME}_al_{t}.png'):
        meta['atlases'][t] = old_meta['atlases'][t]; log('reused', t, 'k', round(meta['atlases'][t]['k'], 4))
        continue
    light = bake(objs, size, t, spp, 'light')
    try:
        import pyoidn
        light = pyoidn.denoise(np.ascontiguousarray(light), filter_type='RTLightmap')
    except Exception as e:
        log('denoise failed', e)
    lv = light @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    k = float(np.percentile(lv[lv > 1e-4], 99.6)) / 0.9 if (lv > 1e-4).any() else 1.0
    save8(to_srgb(light / k), f'{OUT}/{NAME}_lm_{t}.png')
    alb = bake(objs, size, t, 4, 'albedo')
    save8(to_srgb(alb), f'{OUT}/{NAME}_al_{t}.png')
    meta['atlases'][t] = {'k': k, 'size': size}
    log('baked', t, 'k', round(k, 4))

# plant light probes: the baked light on the ground under each plant (lamps, sky, sun), read from the lightmaps.
# Used to light plants where there is no sun (dusk): irradiance = pi x the diffuse light pass.
from PIL import Image as _Img
_lmimg = {}
def _lm_sample(t, uv):
    if t not in _lmimg:
        a = np.asarray(_Img.open(f'{OUT}/{NAME}_lm_{t}.png').convert('RGB'), np.float32) / 255.0
        a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
        _lmimg[t] = a * meta['atlases'][t]['k']
    a = _lmimg[t]; hh, ww = a.shape[:2]
    x = min(ww - 1, max(0, int(uv[0] * ww))); y = min(hh - 1, max(0, int((1 - uv[1]) * hh)))
    return a[max(0, y - 2):y + 3, max(0, x - 2):x + 3].reshape(-1, 3).mean(0)
_tri_cache = {}
def _uv_at(ob, face, p):
    me = ob.data
    if ob.name not in _tri_cache:
        me.calc_loop_triangles(); d = {}
        for lt in me.loop_triangles: d.setdefault(lt.polygon_index, []).append(lt)
        _tri_cache[ob.name] = d
    uvl = me.uv_layers['lm'].data; lp = ob.matrix_world.inverted() @ p
    from mathutils.geometry import barycentric_transform
    best = None
    for lt in _tri_cache[ob.name].get(face, []):
        v = [me.vertices[i].co for i in lt.vertices]
        u = [Vector((*uvl[l].uv, 0)) for l in lt.loops]
        q = barycentric_transform(lp, v[0], v[1], v[2], u[0], u[1], u[2])
        if best is None or (-0.01 <= q.x <= 1.01 and -0.01 <= q.y <= 1.01): best = q
    return best
dg_q = bpy.context.evaluated_depsgraph_get()
nprobe = 0
for o, rec in zip([o for o in sc.objects if o.get('jv_plant')], plants):
    org = o.matrix_world.translation + Vector((0.0, 0.0, 0.4)); rec['pr'] = None
    for _ in range(6):
        ok, loc, nrm, face, ob, _m = sc.ray_cast(dg_q, org, Vector((0, 0, -1)), distance=30.0)
        if not ok: break
        if ob.name.startswith('JV_') and atlas_of(ob.name[3:]) and 'lm' in ob.data.uv_layers:
            uv = _uv_at(ob, face, loc)
            if uv is not None:
                rec['pr'] = [round(float(c) * math.pi, 4) for c in _lm_sample(atlas_of(ob.name[3:]), uv)]; nprobe += 1
            break
        org = loc + Vector((0, 0, -0.01))
log('plant probes', nprobe, 'of', len(plants))

# vertex colours (light × colour) for vegetation and far hills
kv_all = []
def bake_vertex(obj):
    me = obj.data
    # keep the leaf 'col' attribute while baking: the leaf shaders read it for their colour
    if 'bake' in me.color_attributes: me.color_attributes.remove(me.color_attributes['bake'])
    ca = me.color_attributes.new('bake', 'FLOAT_COLOR', 'CORNER'); me.color_attributes.active_color = ca
    select_only([obj]); sc.cycles.samples = CFG.get('vtx_spp', 24); sc.cycles.sample_clamp_indirect = 2.0
    bpy.ops.object.bake(type='COMBINED', pass_filter={'DIRECT', 'INDIRECT', 'DIFFUSE', 'TRANSMISSION', 'EMIT'}, target='VERTEX_COLORS')
    ca = me.color_attributes['bake']
    n = len(ca.data); buf = np.zeros(n * 4, np.float32); ca.data.foreach_get('color', buf)
    # single-corner fireflies: clip each corner to 1.5x its face median (leaf cards are quads)
    b4 = buf.reshape(n, 4); lum = b4[:, :3] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    ls = np.zeros(len(me.polygons), np.int64); me.polygons.foreach_get('loop_start', ls)
    lt = np.zeros(len(me.polygons), np.int64); me.polygons.foreach_get('loop_total', lt)
    face = np.repeat(np.arange(len(lt)), lt)
    order = np.argsort(face, kind='stable'); med = np.zeros(len(lt), np.float32)
    for k in np.unique(lt):
        sel = np.where(lt == k)[0]
        idx = ls[sel][:, None] + np.arange(k)[None, :]
        med[sel] = np.median(lum[idx], axis=1)
    cap = med[face] * 1.5 + 1e-4
    sc_ = np.minimum(1.0, cap / np.maximum(lum, 1e-6))
    b4[:, :3] *= sc_[:, None]; buf = b4.ravel()
    for c in list(me.color_attributes):
        if c.name != 'bake': me.color_attributes.remove(c)
    ca = me.color_attributes['bake']; me.color_attributes.active_color = ca
    return ca, buf.reshape(n, 4)
vtx = {}
for g, o in joined.items():
    if o and (g.endswith('veg') or g.startswith('far')):
        vtx[g] = bake_vertex(o)
        kv_all.append(np.percentile(vtx[g][1][:, :3].max(1), 99.5))
KV = float(max(kv_all) / 0.95) if kv_all else 1.0
for g, (ca, buf) in vtx.items():
    out = buf.copy(); out[:, :3] = np.clip(out[:, :3] / KV, 0, 1); out[:, 3] = 1
    ca.data.foreach_set('color', out.ravel())
meta['kv'] = KV
log('vertex baked', list(vtx), 'kv', round(KV, 4))

# ── 6. export: simple named materials, both UV layers, normals ──
keep = {}
_tag = []
def tag_img():
    # the glTF exporter only writes UV maps that some texture reads, so each PBR material gets two
    # tiny tag textures: base colour on 'mat' and emission on 'lm'. post_pbr.mjs maps them to
    # TEXCOORD_0 / TEXCOORD_1 and strips the tags.
    if not _tag:
        im = bpy.data.images.new('jv_uvtag', 4, 4); im.pixels = [1.0] * 64
        im.filepath_raw = f'{OUT}/jv_uvtag.png'; im.file_format = 'PNG'; im.save()
        _tag.append(im)
    return _tag[0]
def simple(name, color=(0.8, 0.8, 0.8, 1), vcol=False, uvs=False):
    if name in keep: return keep[name]
    m = bpy.data.materials.new('W_' + name); m.name = name if name not in bpy.data.materials else name
    b = m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value = color; b.inputs['Roughness'].default_value = 1.0
    if uvs:
        nt = m.node_tree
        for uvname, sock in (('mat', 'Base Color'), ('lm', 'Emission Color')):
            uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = uvname
            tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = tag_img()
            nt.links.new(uv.outputs['UV'], tx.inputs['Vector']); nt.links.new(tx.outputs['Color'], b.inputs[sock])
        b.inputs['Emission Strength'].default_value = 1.0
    if vcol:
        cn = m.node_tree.nodes.new('ShaderNodeVertexColor'); cn.layer_name = 'bake'
        m.node_tree.links.new(cn.outputs['Color'], b.inputs['Base Color'])
    keep[name] = m; return m
export = []
for g, o in joined.items():
    if not o: continue
    t = atlas_of(g); me = o.data
    if t:
        for i, s in enumerate(o.material_slots):
            nm = s.material.name if s.material else 'plaster'
            s.material = simple('pbr__' + nm, uvs=True)
        while len(me.uv_layers) > 2: me.uv_layers.remove(me.uv_layers[-1])
        for c in list(me.color_attributes): me.color_attributes.remove(c)
        o['jv_atlas'] = t
    elif g.endswith('veg') or g.startswith('far'):
        o.data.materials.clear(); o.data.materials.append(simple('vcol', vcol=True))
        while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    else:
        nm = 'water' if g == 'water' else ('glass' if g.endswith('glass') else 'lamp')
        if nm == 'lamp':
            ms = mats_of(o); nm = 'lamp_pool' if ms and all(m == 'lamp_pool' for m in ms) else 'lamp'
            col = (0.5, 0.95, 1.0, 1) if nm == 'lamp_pool' else (1.0, 0.78, 0.5, 1)
            o.data.materials.clear(); o.data.materials.append(simple(nm, col))
        else:
            o.data.materials.clear(); o.data.materials.append(simple(nm))
        while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
        for c in list(me.color_attributes): me.color_attributes.remove(c)
    export.append(o)
select_only(export)
glb = f'{OUT}/{NAME}.glb'
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True,
                          export_texcoords=True, export_normals=True, export_materials='EXPORT',
                          export_vertex_color='ACTIVE', export_extras=True, export_cameras=False, export_lights=False, export_yup=True)
log('exported', glb, os.path.getsize(glb) // 1024, 'KB')
meta['groups'] = {g: {'polys': len(o.data.polygons), 'atlas': atlas_of(g)} for g, o in joined.items() if o}
json.dump(meta, open(f'{OUT}/{NAME}_meta.json', 'w'), indent=1)

# ── 7. sky: 4k background (linear / kb, sRGB 8-bit) and 1k HDR for reflections ──
for o in list(bpy.context.scene.objects):
    if o.type in ('MESH', 'CURVE') or (o.type == 'EMPTY' and o.instance_type == 'COLLECTION'): o.hide_render = True
cd = bpy.data.cameras.new('pano'); cd.type = 'PANO'
try: cd.panorama_type = 'EQUIRECTANGULAR'
except Exception: cd.cycles.panorama_type = 'EQUIRECTANGULAR'
co = bpy.data.objects.new('pano', cd); sc.collection.objects.link(co)
co.location = (0, 0, 2); co.rotation_euler = (math.radians(90), 0, math.radians(-90)); co.hide_render = False
sc.camera = co
# sun-free environment for the real-time lit plants (the sun reaches them as a directional light)
sc.render.image_settings.file_format = 'HDR'
for lamp in [o for o in bpy.data.objects if o.type == 'LIGHT']: lamp.hide_render = True
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0
sc.cycles.samples = 8; sc.cycles.use_denoising = False
sc.render.resolution_x, sc.render.resolution_y = 512, 256; sc.render.resolution_percentage = 100
sc.render.filepath = f'{OUT}/{NAME}_envd.hdr'; bpy.ops.render.render(write_still=True)
# unclamped sky for the pictures: swap the clamped colour back to the raw HDRI
if use_sun: nt.links.new(env.outputs['Color'], bg.inputs['Color'])
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0
sc.cycles.samples = 8; sc.cycles.use_denoising = False
for lamp in [o for o in bpy.data.objects if o.type == 'LIGHT']: lamp.hide_render = True
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
sc.render.resolution_x, sc.render.resolution_y = 4096, 2048; sc.render.resolution_percentage = 100
sc.render.filepath = f'{OUT}/{NAME}_sky.exr'; bpy.ops.render.render(write_still=True)
sk = bpy.data.images.load(f'{OUT}/{NAME}_sky.exr')
spx = np.array(sk.pixels[:], np.float32).reshape(2048, 4096, 4)[..., :3]
kb = float(np.percentile(spx @ np.array([0.2126, 0.7152, 0.0722], np.float32), 99.0)) / 0.85
from PIL import Image
Image.fromarray((to_srgb(spx / kb) * 255 + 0.5).astype(np.uint8)[::-1], 'RGB').save(f'{OUT}/{NAME}_sky.jpg', quality=88)
sc.render.image_settings.file_format = 'HDR'
sc.render.resolution_x, sc.render.resolution_y = 1024, 512
sc.render.filepath = f'{OUT}/{NAME}_env.hdr'; bpy.ops.render.render(write_still=True)
meta['kb'] = kb
meta['hdri']['sun_col'] = [float(c) for c in sun_col] if use_sun else [1, 1, 1]
meta['hdri']['sun_dir_gltf'] = [SUN_DIR.x, SUN_DIR.z, -SUN_DIR.y]
meta['plants'] = len(plants)
json.dump(meta, open(f'{OUT}/{NAME}_meta.json', 'w'), indent=1)
json.dump({'instances': plants}, open(f'{OUT}/{NAME}_plants.json', 'w'))
os.remove(f'{OUT}/{NAME}_sky.exr')
log('sky', 'kb', round(kb, 4)); log('DONE')
