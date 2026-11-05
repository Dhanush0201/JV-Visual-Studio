import bpy, sys, time
argv = sys.argv[sys.argv.index('--')+1:]
blend, cam, out, rx, ry = argv[0], argv[1], argv[2], int(argv[3]), int(argv[4])
t0=time.time()
bpy.ops.wm.open_mainfile(filepath=blend)
sc=bpy.context.scene
print('engines',[e.identifier for e in sc.render.bl_rna.properties['engine'].enum_items])
sc.render.engine='BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in sc.render.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
sc.camera=bpy.data.objects[cam]
sc.render.resolution_x=rx; sc.render.resolution_y=ry; sc.render.resolution_percentage=100
e=sc.eevee
for k in ['taa_render_samples','use_raytracing','ray_tracing_method','use_shadows','shadow_ray_count','shadow_step_count','use_gtao','fast_gi_method','use_fast_gi']:
    print(k, getattr(e,k,'NA'))
e.taa_render_samples=int(argv[5]) if len(argv)>5 else 32
try: e.use_raytracing=True
except Exception as ex: print(ex)
sc.render.filepath=out
print('load',time.time()-t0)
t=time.time(); bpy.ops.render.render(write_still=True); print('EEVEE render s',time.time()-t)
