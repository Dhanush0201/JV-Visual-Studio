import sys, time
sys.path.insert(0,'/home/claude/jv5/blender')
import bpy
a=sys.argv[sys.argv.index('--')+1:]
blend, cam, out, rx, ry, spp = a[0], a[1], a[2], int(a[3]), int(a[4]), int(a[5])
bpy.ops.wm.open_mainfile(filepath=blend)
sc=bpy.context.scene
sc.camera=bpy.data.objects[cam]
sc.render.resolution_x=rx; sc.render.resolution_y=ry; sc.render.resolution_percentage=100
sc.cycles.samples=spp
if len(a)>6: sc.cycles.adaptive_threshold=float(a[6])
sc.render.filepath=out
t=time.time(); bpy.ops.render.render(write_still=True); print('RENDERED',out,round(time.time()-t,1),'s')
