"""Shared helpers for the Poly Haven plant library (import, alpha fix, thinning, centring)."""
import bpy, bmesh, glob, os, random, math
from mathutils import Vector, Matrix

SRC = '/home/claude/jv5/plants/src'

def alpha_file(pid, diff_name):
    """Find the alpha/opacity/mask map that belongs to a diffuse image name."""
    tex = f'{SRC}/{pid}/textures'
    stem = diff_name.split('_diff')[0]
    cands = sorted(glob.glob(f'{tex}/*_alpha_1k.png')) + sorted(glob.glob(f'{tex}/*_opacity_1k.png')) + sorted(glob.glob(f'{tex}/*_mask_1k.png'))
    for c in cands:
        if os.path.basename(c).startswith(stem): return c
    return None

def import_asset(pid):
    """Import one glTF into a fresh collection, wire real alpha maps; returns (collection, mesh objects)."""
    before = set(bpy.data.objects)
    g = glob.glob(f'{SRC}/{pid}/*.gltf')[0]
    bpy.ops.import_scene.gltf(filepath=g)
    objs = [o for o in bpy.data.objects if o not in before]
    for o in objs:
        if o.parent and o.parent in objs:
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    meshes = [o for o in objs if o.type == 'MESH']
    for o in objs:
        if o.type != 'MESH': bpy.data.objects.remove(o, do_unlink=True)
    for o in meshes:
        for s in o.material_slots:
            m = s.material
            if not m or m.get('jv_alpha_fixed'): continue
            nt = m.node_tree; b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if not b: continue
            tex = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and 'diff' in n.image.name.lower()), None)
            if tex is not None:
                af = alpha_file(pid, os.path.basename(tex.image.name))
                if af:
                    an = nt.nodes.new('ShaderNodeTexImage'); an.image = bpy.data.images.load(af, check_existing=True)
                    an.image.colorspace_settings.name = 'Non-Color'
                    if tex.inputs['Vector'].is_linked: nt.links.new(tex.inputs['Vector'].links[0].from_socket, an.inputs['Vector'])
                    nt.links.new(an.outputs['Color'], b.inputs['Alpha'])
                    m['jv_alpha'] = af
            m['jv_alpha_fixed'] = 1
            try: m.blend_method = 'HASHED'
            except Exception: pass
    return meshes

def apply_all(o):
    bpy.context.view_layer.objects.active = o
    for x in bpy.context.selected_objects: x.select_set(False)
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

def ground_centre(o):
    """Move mesh so its footprint centre is at x=y=0 and its lowest point at z=0."""
    me = o.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    off = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    me.transform(Matrix.Translation(-off)); me.update()
    return max(zs) - min(zs), max(max(xs) - min(xs), max(ys) - min(ys))

def islands(bm, faces):
    """Connected face islands within a face subset."""
    fs = set(faces); seen = set(); out = []
    for f in faces:
        if f in seen: continue
        st = [f]; isl = []
        while st:
            g = st.pop()
            if g in seen: continue
            seen.add(g); isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h in fs and h not in seen: st.append(h)
        out.append(isl)
    return out

def thin_islands(o, mat_pred, keep, scale_area, seed=1, min_diag=0.0):
    """Keep `keep` random islands of faces whose material matches, scale each about its centre so the kept
    area is `scale_area` of the original; drop islands smaller than min_diag."""
    rnd = random.Random(seed)
    me = o.data; bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    sel = [f for f in bm.faces if mat_pred(mats[f.material_index])]
    isl = islands(bm, sel)
    n0 = len(isl)
    kept = isl if keep >= n0 else rnd.sample(isl, keep)
    keep_set = set(id(i) for i in kept)
    kill = [f for i in isl if id(i) not in keep_set for f in i]
    s = math.sqrt(scale_area * n0 / max(1, len(kept))) if kept else 1
    for i in kept:
        vs = {v for f in i for v in f.verts}
        c = sum((v.co for v in vs), Vector()) / len(vs)
        for v in vs: v.co = c + (v.co - c) * s
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(me); bm.free(); me.update()
    return n0, len(kept), s

def drop_small_islands(o, mat_pred, min_diag):
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    sel = [f for f in bm.faces if mat_pred(mats[f.material_index])]
    kill = []
    for i in islands(bm, sel):
        vs = [v.co for f in i for v in f.verts]
        mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
        mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        if (mx - mn).length < min_diag: kill += i
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(me); bm.free(); me.update()
    return len(kill)

def decimate_mat(o, mat_pred, ratio):
    """Collapse-decimate only the faces of matching materials (via a vertex group)."""
    if ratio >= 1: return
    me = o.data
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    vg = o.vertex_groups.new(name='dec')
    idx = sorted({v for p in me.polygons if mat_pred(mats[p.material_index]) for v in p.vertices})
    vg.add(idx, 1.0, 'REPLACE')
    # the modifier ratio is of the whole mesh; the vertex group only limits what may collapse
    tot = sum(len(p.vertices) - 2 for p in me.polygons)
    sub = sum(len(p.vertices) - 2 for p in me.polygons if mat_pred(mats[p.material_index]))
    md = o.modifiers.new('dec', 'DECIMATE'); md.ratio = (tot - sub + sub * ratio) / max(1, tot); md.vertex_group = 'dec'; md.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=md.name)
    g = o.vertex_groups.get('dec')
    if g: o.vertex_groups.remove(g)

def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

def dedupe_islands(o, mat_pred, tol=1e-3):
    """Remove duplicate islands (same face count and centroid) of matching materials."""
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    sel = [f for f in bm.faces if mat_pred(mats[f.material_index])]
    seen = {}; kill = []
    for i in islands(bm, sel):
        vs = {v for f in i for v in f.verts}
        c = sum((v.co for v in vs), Vector()) / len(vs)
        key = (len(i), round(c.x / tol), round(c.y / tol), round(c.z / tol))
        if key in seen: kill += i
        else: seen[key] = 1
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(me); bm.free(); me.update()
    return len(kill)
