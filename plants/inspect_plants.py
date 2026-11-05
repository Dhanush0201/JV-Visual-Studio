import bpy, os, glob, json
ROOT = '/home/claude/jv5/plants/src'
out = {}
for d in sorted(glob.glob(f'{ROOT}/*/')):
    pid = os.path.basename(d.rstrip('/'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    g = glob.glob(f'{d}/*.gltf')[0]
    bpy.ops.import_scene.gltf(filepath=g)
    objs = [o for o in bpy.data.objects if o.type == 'MESH']
    dg = bpy.context.evaluated_depsgraph_get()
    mn = [1e9] * 3; mx = [-1e9] * 3; tris = 0
    parts = []
    for o in objs:
        for v in o.bound_box:
            w = o.matrix_world @ __import__('mathutils').Vector(v)
            for i in range(3): mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
        t = sum(len(p.vertices) - 2 for p in o.data.polygons); tris += t
        mats = [s.material.name for s in o.material_slots if s.material]
        parts.append((o.name, t, mats))
    imgs = sorted({i.name for i in bpy.data.images})
    alpha = []
    for m in bpy.data.materials:
        if not m.node_tree: continue
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED' and n.inputs['Alpha'].is_linked: alpha.append(m.name)
    out[pid] = {'size_m': [round(mx[i] - mn[i], 2) for i in range(3)], 'zmin': round(mn[2], 3), 'tris': tris, 'parts': parts, 'alpha_mats': alpha, 'images': imgs}
    print(pid, out[pid]['size_m'], tris, [(p[0], p[1], p[2]) for p in parts][:6], 'alpha', alpha, flush=True)
json.dump(out, open('/home/claude/jv5/plants/inspect.json', 'w'), indent=1)
