"""Replace leaf-twig islands by single UV-faithful quads (real leaf texture, 2 triangles per twig)."""
import bmesh, random, math
import numpy as np
from mathutils import Vector
import plantkit as pk

def twigs_to_quads(o, mat_pred, keep, grow=1.0, seed=1, radial=0.45, centre=None):
    rnd = random.Random(seed)
    me = o.data; bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv.active
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    sel = [f for f in bm.faces if mat_pred(mats[f.material_index])]
    isl = pk.islands(bm, sel)
    n0 = len(isl)
    kept = isl if keep >= n0 else rnd.sample(isl, keep)
    mat_index = sel[0].material_index if sel else 0
    quads = []
    for i in kept:
        P = []; U = []
        for f in i:
            for l in f.loops:
                P.append(l.vert.co[:]); U.append(l[uvl].uv[:])
        P = np.array(P); U = np.array(U)
        A = np.c_[U, np.ones(len(U))]
        sol, *_ = np.linalg.lstsq(A, P, rcond=None)          # (3,3): [u v 1] -> xyz
        u0, v0 = U.min(0); u1, v1 = U.max(0)
        corners = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        pts = [np.array([u, v, 1.0]) @ sol for u, v in corners]
        c = sum(pts) / 4
        pts = [c + (p - c) * grow for p in pts]
        quads.append((pts, corners))
    bmesh.ops.delete(bm, geom=sel, context='FACES')
    for pts, corners in quads:
        vs = [bm.verts.new(Vector(p)) for p in pts]
        try: f = bm.faces.new(vs)
        except ValueError: continue
        f.material_index = mat_index
        for l, uv in zip(f.loops, corners): l[uvl].uv = uv
    bm.to_mesh(me); bm.free(); me.update()
    # soft canopy shading: blend face normals toward the radial direction from the crown centre
    if radial > 0:
        cen = Vector(centre) if centre else None
        if cen is None:
            lv = [v.co for p in me.polygons if mat_pred(mats[p.material_index]) for v in [me.vertices[k] for k in p.vertices]]
            cen = sum(lv, Vector()) / max(1, len(lv))
        me.calc_loop_triangles() if hasattr(me, 'calc_loop_triangles') else None
        nrm = []
        for l in me.loops:
            p = me.polygons[0]
        loop_face = [0] * len(me.loops)
        for p in me.polygons:
            for li in p.loop_indices: loop_face[li] = p.index
        for li, l in enumerate(me.loops):
            p = me.polygons[loop_face[li]]
            if mat_pred(mats[p.material_index]):
                r = (me.vertices[l.vertex_index].co - cen); r.z *= 0.6
                n = Vector(p.normal)
                if n.dot(r) < 0: n = -n
                nrm.append((n * (1 - radial) + r.normalized() * radial).normalized())
            else:
                nrm.append(Vector(l.normal) if hasattr(l, 'normal') else Vector(p.normal))
        try:
            me.normals_split_custom_set(nrm)
        except Exception as e:
            print('custom normals failed', e)
    return n0, len(kept)
