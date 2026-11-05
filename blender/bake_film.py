"""Bake a scene's Cycles lighting into textures / vertex colours and export a web GLB.
FILM variant: full vegetation, modifiers applied (bevels, cushions), separate interior atlas
(+0.7 EV for precision), optional 'hero' atlas for a rectangle around the film shots.
usage: python3 bake_film.py -- <blend> <out_dir> <name> <config.json>
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
CFG = json.load(open(a[3]))
HOME = CFG.get('home', False)
VTX_SPP = CFG.get('vtx_spp', 24)
HERO = CFG.get('hero')            # [x0, y0, x1, y1] world rect or None
ATL = CFG['atlases']              # {name: [size, spp, exposure]}
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
        if m.type == 'PARTICLE_SYSTEM':
            o.modifiers.remove(m)
# diffuse-only lightmaps turn metals black: give metals a diffuse equivalent for the bake
for m in bpy.data.materials:
    if not m.node_tree: continue
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED' and n.inputs['Metallic'].default_value > 0.5 and not n.inputs['Metallic'].is_linked:
            n.inputs['Metallic'].default_value = 0.0
            c = n.inputs['Base Color'].default_value
            n.inputs['Base Color'].default_value = (c[0] * 0.7, c[1] * 0.7, c[2] * 0.7, 1)
dg = bpy.context.evaluated_depsgraph_get()
napplied = 0
for o in list(bpy.data.objects):
    if o.type == 'MESH' and len(o.modifiers):
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        o.modifiers.clear(); o.data = me; napplied += 1
log('modifiers applied on', napplied, 'objects')

def mats_of(o):
    return [s.material.name for s in o.material_slots if s.material]

def is_veg(o):
    n = o.name
    return any(k in n for k in ('_leaves', '_fronds', '_trunk', '_flowers')) or \
        (o.users_collection and o.users_collection[0].name == 'vegetation')

TERRAIN = {'ground_main', 'lawn', 'lawn_w', 'lawn_e', 'lawn_n'}

def prefix(o):
    n = o.name
    if n.startswith('int_'): return 'int'
    if HOME and n.startswith('ctx_'): return 'ctx'
    return ''

def centre(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(bb, Vector()) / 8

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
    if p == 'int': return 'int'
    if HOME:
        if o.name.startswith('ctx_blk_'): return 'far_city'
        return 'ctx' if p == 'ctx' else 'build'
    if o.name in TERRAIN: return 'terrain'
    if HERO:
        c = centre(o)
        if HERO[0] <= c.x <= HERO[2] and HERO[1] <= c.y <= HERO[3]: return 'hero'
    return 'build'

def atlas_of(g):
    if g in ('terrain', 'ctx'): return 'terrain'
    if g in ('water',) or g.startswith('far') or g.endswith('glass') or g.endswith('lamp') or g.endswith('veg'): return None
    if g in ('int', 'hero'): return g
    return 'build'

groups = {}
for o in bpy.data.objects:
    g = group_of(o)
    if g: groups.setdefault(g, []).append(o)
log('groups', {k: len(v) for k, v in groups.items()})

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
def build_lut(N=33, lo=-12.0, hi=5.0, ev=0.0):
    sc.view_settings.exposure = ev
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
    path = os.path.join(OUT, f'_lut{ev}.png')
    img.save_render(path, scene=sc)
    sc.view_settings.exposure = 0.0
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
LUTV2, LUT2 = build_lut(ev=ATL.get('int', [0, 0, 0.7])[2])
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

def bake_image(objs, size, label, spp, ev):
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
    sc.cycles.samples = spp
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
    sc.view_settings.exposure = ev
    img.save_render(path, scene=sc)
    sc.view_settings.exposure = 0.0
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
    disp = apply_lut(buf[:, :3], *(LUTV2, LUT2) if label.startswith('int') else (LUTV, LUT))                       # display-referred sRGB
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
    size, spp, ev = ATL[t]
    uv_unwrap(objs, 0.0012 if size >= 4096 else 0.002)
    log('unwrapped', t, size, spp, ev, [o.name for o in objs])
    paths[t] = bake_image(objs, size, t, spp, ev)
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
                          export_vertex_color='ACTIVE', export_image_format='WEBP', export_image_quality=90,
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
sc.render.resolution_x, sc.render.resolution_y = 4096, 2048
sc.cycles.samples = 24
sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
sc.render.filepath = os.path.join(OUT, f'{NAME}_sky.jpg')
bpy.ops.render.render(write_still=True)
log('sky', sc.render.filepath)
json.dump({'groups': {g: len(o.data.polygons) for g, o in joined.items() if o}, 'seconds': time.time() - T0},
          open(os.path.join(OUT, f'{NAME}_meta.json'), 'w'), indent=1)
log('DONE')
