import bpy, sys, math, time
sys.path.insert(0, '/home/claude/jv5/plants')
import plantkit as pk, twigquads as tq
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
KEEP, GROW, BR_MIN, BR_RATIO, TR_RATIO, OUT = int(args[0]), float(args[1]), float(args[2]), float(args[3]), float(args[4]), args[5]
bpy.ops.wm.read_factory_settings(use_empty=True)
t0 = time.time()
o = pk.import_asset('jacaranda_tree')[0]
o.scale = (9.0 / o.dimensions.z,) * 3; pk.apply_all(o); pk.ground_centre(o)
leaf = lambda n: 'leaves' in n
n0, k = tq.twigs_to_quads(o, leaf, KEEP, GROW, seed=3)
dropped = pk.drop_small_islands(o, lambda n: 'branches' in n, BR_MIN)
pk.decimate_mat(o, lambda n: 'branches' in n, BR_RATIO)
pk.decimate_mat(o, lambda n: 'trunk' in n, TR_RATIO)  # no dedupe: paired trunk islands are both needed
print('islands', n0, 'kept', k, 'dropped branch faces', dropped, 'tris', pk.tris(o), 'dims', tuple(round(d, 2) for d in o.dimensions), round(time.time() - t0, 1), 's', flush=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'CPU'
sc.render.resolution_x = 640; sc.render.resolution_y = 640
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.65, 0.8, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = 4.0; so = bpy.data.objects.new('sun', ld); sc.collection.objects.link(so)
so.rotation_euler = (math.radians(45), 0, math.radians(-150))
gp = bpy.data.meshes.new('g'); gp.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
go = bpy.data.objects.new('g', gp); sc.collection.objects.link(go)
cd = bpy.data.cameras.new('c'); cd.lens = 50; co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
co.location = (0, -24, 4.8); co.rotation_euler = (math.radians(86), 0, 0)
sc.view_settings.view_transform = 'AgX'
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True)
if len(args) > 6: bpy.ops.wm.save_as_mainfile(filepath=args[6])
print('rendered', round(time.time() - t0, 1), flush=True)
