import sys; sys.path.insert(0,'/home/claude/jv5/blender')
import bpy, kit
a=sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
w=bpy.context.scene.world
bg=[n for n in w.node_tree.nodes if n.type=='BACKGROUND'][0]
bg.inputs['Strength'].default_value=float(a[1])
bpy.data.objects['Sun'].data.energy=float(a[2])
bpy.context.scene.view_settings.exposure=float(a[3])
sc=bpy.context.scene; sc.cycles.adaptive_threshold=0.1
kit.render(a[4], bpy.data.objects[a[5]], (480,270), 20)
