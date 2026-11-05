"""Quick Cycles previews of film camera keys. usage: preview_cams.py -- blend out_prefix json"""
import bpy, sys, json, math, time
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
sc = bpy.context.scene
cams = json.loads(open(a[2]).read())
rx, ry, spp = 640, 360, 16
if len(a) > 3: rx, ry, spp = int(a[3]), int(a[4]), int(a[5])
sc.render.resolution_x, sc.render.resolution_y = rx, ry
sc.cycles.samples = spp
for o in bpy.data.objects:
    if o.name.startswith('grass'): o.hide_render = True
for name, c in cams.items():
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
    cd.lens = 12 / math.tan(math.radians(c['fov']) / 2)
    cd.clip_start = 0.1; cd.clip_end = 3000
    co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co)
    co.location = c['pos']
    co.rotation_euler = (Vector(c['tgt']) - Vector(c['pos'])).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co
    sc.render.filepath = f"{a[1]}_{name}.png"
    t = time.time(); bpy.ops.render.render(write_still=True); print('PREVIEW', name, round(time.time() - t, 1))
