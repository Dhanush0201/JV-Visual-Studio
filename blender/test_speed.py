import bpy, time
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.render.engine='CYCLES'
cy=sc.cycles
cy.device='CPU'; cy.samples=64; cy.use_denoising=True
try: cy.denoiser='OPENIMAGEDENOISE'
except Exception as e: print('den',e)
sc.render.resolution_x=960; sc.render.resolution_y=540
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True
nt=w.node_tree; sky=nt.nodes.new('ShaderNodeTexSky')
print('sky types', [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items])
print('sky props', [p.identifier for p in sky.bl_rna.properties])
nt.links.new(sky.outputs[0], nt.nodes['Background'].inputs[0] if 'Background' in nt.nodes else nt.nodes.new('ShaderNodeBackground').inputs[0])
bg=[n for n in nt.nodes if n.type=='BACKGROUND'][0]
out=[n for n in nt.nodes if n.type=='OUTPUT_WORLD']
if not out:
    o=nt.nodes.new('ShaderNodeOutputWorld'); nt.links.new(bg.outputs[0],o.inputs[0])
bpy.ops.mesh.primitive_plane_add(size=40)
bpy.ops.mesh.primitive_cube_add(size=4,location=(0,0,2))
bpy.ops.object.light_add(type='SUN'); bpy.context.object.data.energy=3
cam=bpy.data.objects.new('C',bpy.data.cameras.new('C')); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(10,-10,5);
import mathutils
d=mathutils.Vector((0,0,1.5))-cam.location; cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
sc.render.filepath='/home/claude/jv5/out/test.png'
print('view transforms',[i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items])
t=time.time(); bpy.ops.render.render(write_still=True); print('render s',time.time()-t)
print('threads', sc.render.threads)
