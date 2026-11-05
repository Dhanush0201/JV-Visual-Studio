"""Render only the world sky as an equirect panorama (light on memory).
usage: sky_pano.py -- blend out.jpg [w h spp]"""
import bpy, sys, math
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
sc = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
cd = bpy.data.cameras.new('pano'); cd.type = 'PANO'
try: cd.panorama_type = 'EQUIRECTANGULAR'
except Exception: cd.cycles.panorama_type = 'EQUIRECTANGULAR'
co = bpy.data.objects.new('pano', cd); sc.collection.objects.link(co)
co.location = (0, 0, 2); co.rotation_euler = (math.radians(90), 0, math.radians(-90))
sc.camera = co
w, h, spp = (int(a[2]), int(a[3]), int(a[4])) if len(a) > 4 else (4096, 2048, 24)
sc.render.resolution_x, sc.render.resolution_y = w, h; sc.render.resolution_percentage = 100
sc.cycles.samples = spp
sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
sc.render.filepath = a[1]
bpy.ops.render.render(write_still=True)
print('SKY', a[1])
