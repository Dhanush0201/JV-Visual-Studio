"""Top-down section renders of the duplex (roof and upper floor hidden) for the wall check.
usage: plan_views.py -- blend out_prefix"""
import bpy, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
sc = bpy.context.scene
FT = 0.3048
PL = 1.5 * FT; FF = PL + 10 * FT
def show(level):
    cut = (PL + 1.35) if level == 'gf' else (FF + 1.35)
    for o in bpy.data.objects:
        if o.type not in ('MESH', 'LIGHT'): continue
        if o.type == 'LIGHT': continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        zmin = min(v.z for v in bb)
        o.hide_render = zmin > cut or o.name.startswith('ctx_') or o.name.startswith('grass')
        # clip walls: hide everything that starts above the cut; walls that cross it stay
    # section: a big bisect would be ideal; instead, hide slabs/roof above and keep walls as boxes
cd = bpy.data.cameras.new('plan'); cd.type = 'ORTHO'; cd.ortho_scale = 10.5
co = bpy.data.objects.new('plan', cd); sc.collection.objects.link(co)
co.location = (15 * FT, 14.5 * FT, 30); co.rotation_euler = (0, 0, 0)
sc.camera = co
sc.render.resolution_x, sc.render.resolution_y = 1400, 1250
sc.cycles.samples = 24
for lv in ('gf', 'ff'):
    show(lv)
    sc.render.filepath = f'{a[1]}_{lv}.png'
    bpy.ops.render.render(write_still=True)
    print('PLAN', lv)
