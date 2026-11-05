"""Scene A — Boulder-hill resort with infinity pool and pool villas (studio concept).
Clubhouse faces south over an infinity pool; terrace drops to a valley of granite boulder hills.
Units: metres. +Y north, +X east. Sun: golden hour from WSW.
"""
import sys, math, random
sys.path.insert(0, '/home/claude/jv5/blender')
import bpy, bmesh
from mathutils import Vector, noise
import kit
import os
FILM = os.environ.get('JV_FILM') == '1'
os.environ['JV_SCENE'] = 'resort'
if FILM:
    import interior as I
from kit import box, plane, cyl, pool, palm, tree, shrub, hedge, boulder, lounger, umbrella, bollard

MODE = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'golden'

kit.reset()
if FILM: I.materials()
B = kit.collection('buildings')
G = kit.collection('ground')
V = kit.collection('vegetation')
F = kit.collection('far')
P = kit.collection('pools')
FX = kit.collection('fixtures')

# ───────── ground: upper terrace z=0 north of y=-14, lower terrace and valley to the south ─────────
def ground_z(x, y):
    if y > -14.0:
        return -0.03
    t = (-14.0 - y)
    z = -3.2 - 0.05 * t - 0.0009 * t * t
    z += 1.2 * noise.noise(Vector((x * 0.02, y * 0.02, 1.0)))
    return z

bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=90, y_segments=90, size=110)
for v in bm.verts:
    v.co.y -= 50
    v.co.z = ground_z(v.co.x, v.co.y)
gnd = kit._finish(bm, 'ground_main', 'meadow', G)
for pg in gnd.data.polygons: pg.use_smooth = True

# boulder hills all round (higher to the south / south-west, over the valley)
peaks = [(200, 1100, 380, 110), (232, 900, 300, 80), (165, 850, 260, 70), (125, 1400, 420, 150),
         (262, 1450, 450, 130), (188, 1700, 520, 170), (330, 1300, 380, 70), (20, 1500, 420, 80),
         (72, 1200, 340, 55), (298, 1050, 320, 45)]
hills, peaks = kit.hills_ring('far_hills', r0=140, r1=2600, z_base=-24, seed=9, coll=F, peaks=peaks)
rnd = random.Random(11)
for i, (az, pr, pw, ph) in enumerate(peaks[:6]):
    for k in range(8):
        a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0, pw * 0.45)
        px, py = math.sin(math.radians(az)) * pr, math.cos(math.radians(az)) * pr
        x, y = px + math.cos(a) * d, py + math.sin(a) * d
        sz = rnd.uniform(14, 30)
        top = -24 + ph * math.exp(-(d / pw) ** 2) - 0.45 * sz
        boulder(f'far_boulder_{i}_{k}', x, y, top, sz, sz * rnd.uniform(0.7, 1.1), sz * rnd.uniform(0.6, 0.9), seed=i * 20 + k, coll=F, subdiv=3)

# near boulders on the lower terrace (Karnataka granite)
for k, (x, y, s) in enumerate([(-34, -24, 3.2), (-29, -27, 2.2), (-38, -30, 4.0), (30, -26, 3.0), (36, -22, 2.4), (22, -34, 2.8), (-12, -36, 2.0)]):
    boulder(f'boulder_{k}', x, y, ground_z(x, y) - 0.6, s, s * 0.85, s * 0.7, seed=100 + k, coll=G)

# retaining wall under the infinity edge (dressed granite)
box('retaining_wall', -40, -14.6, -3.4, 40, -14.0, -0.02, 'stone_dark', B, 0.01)
box('catch_trough', -15.4, -14.0, -0.55, 15.4, -13.3, -0.05, 'stone_dark', B, 0.005)

# ───────── decks ─────────
kit.slab_with_hole('deck_main', -22, -13.3, 22, -2.0, -0.25, 0.0, (-15.2, -13.3, 15.2, -4.8), 'stone_pave', G)
kit.slab_with_hole('coping', -15.5, -13.3, 15.5, -4.5, -0.02, 0.02, (-15.0, -13.3, 15.0, -5.0), 'stone_dark', G)
box('deck_plinth', -17, -2.0, -0.25, 17, 13.0, 0.45, 'stone_pave', G, 0)
for i in range(3):
    box(f'step_{i}', -6, -2.0 - 0.9 + i * 0.3, -0.1, 6, -2.0 - 0.6 + i * 0.3 + 0.3, 0.15 * (i + 1), 'stone_pave', G, 0.004)

# ───────── infinity pool ─────────
pool('ipool', -15, -13.3, 15, -5.0, z_top=0.0, depth=1.4, coll=P, water_drop=0.01)
kit.lights_in_pool('ipool', -15, -5.0 - 0.2, 15, -5.0, -0.5, P, 6)

# ───────── clubhouse pavilion ─────────
# brick wings
box('club_wing_w', -16, 3.0, 0.45, -9.5, 12.0, 5.0, 'brick', B)
box('club_wing_e', 9.5, 3.0, 0.45, 16, 12.0, 5.0, 'brick', B)
box('club_backwall', -9.5, 11.6, 0.45, 9.5, 12.0, 5.0, 'brick', B)
# glazed lobby
box('club_glass_s', -9.5, 3.0, 0.45, 9.5, 3.04, 4.95, 'glass', B, 0)
for i, x in enumerate([-9.5 + k * 2.375 for k in range(9)]):
    box(f'club_mullion_{i}', x - 0.04, 2.98, 0.45, x + 0.04, 3.06, 4.95, 'metal_dark', B, 0)
box('club_floor_in', -9.5, 3.04, 0.45, 9.5, 11.6, 0.47, 'kota', B, 0)
box('club_ceiling_in', -9.5, 3.04, 4.9, 9.5, 11.6, 4.95, 'teak', B, 0)
# interior: warm wall wash, furniture blocks, pendant glows
box('club_inwall_glow', -9.4, 11.5, 0.5, 9.4, 11.58, 4.85, 'interior_wall', B, 0)
if FILM:
    for i, x in enumerate([-5.5, 5.5]):
        I.rug(f'int_club_rug{i}', x - 2.6, 4.4, x + 2.6, 9.6, 0.47, B, 'rug_wool', 'linen_oat')
        with I.Place(0, 0, 0.47, 0):
            I.sofa(f'int_club_sofa{i}', x, 7.6, 0, B, w=2.8, fab='linen_oat')
            I.armchair(f'int_club_ac{i}a', x - 1.3, 5.3, 160, B, fab='linen_white')
            I.armchair(f'int_club_ac{i}b', x + 1.3, 5.3, 200, B, fab='linen_white')
            I.coffee_table(f'int_club_ct{i}', x, 6.5, 0, B, w=1.5, d=0.8)
        for k, dx in enumerate((-1.2, 0.0, 1.2)):
            I.pendant(f'int_club_pd{i}{k}', x + dx, 6.6, 4.9, 3.1, FX, r=0.26)
    for k, x in enumerate((-9.0, 0.0, 9.0)):
        I.plant(f'int_club_plant{k}', x, 4.0 if k != 1 else 9.8, 0.47, B, pot_r=0.32, pot_h=0.55, h=2.0, crown=0.75, pot='terracotta', seed=30 + k)
    I.bookshelf('int_club_shelf', 'x', -3.4, 3.4, 11.5, 0.47, 3.4, B, depth=0.36, cols=5, rows=5, seed=8, wood='walnut', inward=-1)
    I.art('int_club_art_w', 'x', -9.0, -6.6, 11.5, 1.4, 3.4, B, mat='art_ochre', inward=-1)
    I.art('int_club_art_e', 'x', 6.6, 9.0, 11.5, 1.4, 3.4, B, mat='art_indigo', inward=-1)
else:
    for i, x in enumerate([-6, -2, 2, 6]):
        kit.sofa(f'club_sofa_{i}', x - 1.2, 7.5, x + 1.2, 8.4, 0.47, B, 'fabric_sand')
        box(f'club_pendant_{i}', x - 0.25, 6.0, 3.6, x + 0.25, 6.5, 3.75, 'lamp', FX, 0)
kit.area_light('club_fill', 0, 7.5, 4.7, 18, 7, 260, coll=FX, rot=(0, 0, 0))
# cantilever roof with teak soffit
box('club_roof', -19, -5.5, 5.05, 19, 13.5, 5.45, 'plaster', B, 0.01)
box('club_soffit', -19, -5.5, 4.97, 19, 13.5, 5.05, 'teak', B, 0)
box('club_fascia_strip', -19, -5.55, 5.15, 19, -5.5, 5.35, 'metal_dark', B, 0)
for x in (-13, -6.5, 0, 6.5, 13):
    cyl(f'club_col_{x}', x, -3.4, 0.45, 4.97, 0.13, 'bronze', B, 16)
# roof edge planting
hedge('club_roof_hedge', -18.5, 13.0, 18.5, 13.0, 5.45, 0.5, V, 21, 120)
# soffit downlights
for x in range(-17, 18, 3):
    box(f'club_downlight_{x}', x - 0.08, -4.4, 4.95, x + 0.08, -4.24, 4.97, 'lamp_strong', FX, 0)

# ───────── pool villas (3 east, 3 west), each 9 x 7 m with plunge pool ─────────
def suite(n, F, C):
    """Pool-villa suite interior, villa-local coords (glass at y≈0.44, north wall inner face y≈6.68)."""
    I.rug(n + '_rug', -1.75, 3.15, 1.75, 6.2, F, B, 'rug_dhurrie', 'linen_oat')
    box(n + '_cove', -2.0, 6.52, C - 0.32, 2.0, 6.62, C - 0.27, 'lamp_soft', FX, 0)
    with I.Place(0, 0, F, 0):
        I.bed(n + '_bed', 0.0, 4.33, 0, B, w=1.9, l=2.1, head='teak', throw='fabric_rust')
        I.armchair(n + '_chair', 3.05, 1.65, 40, B, fab='linen_white', frame='teak')
        I.side_table(n + '_st', 2.3, 1.2, B, r=0.22, h=0.5, top='marble')
        I.table_lamp(n + '_stl', 2.3, 1.2, 0.5, FX, h=0.45)
        I.plant(n + '_plant', 3.65, 5.95, 0, B, pot_r=0.24, pot_h=0.46, h=1.6, crown=0.55, pot='ceramic_white', seed=11)
        I.plant(n + '_plant2', -3.7, 6.2, 0, B, pot_r=0.18, pot_h=0.36, h=0.8, crown=0.4, pot='terracotta', seed=12, kind='leafy')
        I.urli(n + '_urli', -2.6, 3.6, 0, B, r=0.3)
    I.curtain(n + '_cur_w', 'x', -4.13, -3.35, 0.62, F + 0.02, C - 0.08, B, folds=5, amp=0.045)
    I.curtain(n + '_cur_e', 'x', 3.35, 4.13, 0.62, F + 0.02, C - 0.08, B, folds=5, amp=0.045)
    box(n + '_track', -4.13, 0.56, C - 0.08, 4.13, 0.68, C - 0.04, 'black', B, 0)
    I.art(n + '_art', 'y', 3.2, 5.4, -4.15, F + 1.0, F + 2.35, B, mat='art_earth', inward=1)
    I.bookshelf(n + '_shelf', 'y', 1.6, 3.7, 4.15, F, F + 2.1, B, depth=0.32, cols=2, rows=5, seed=21, wood='walnut', inward=-1)

def villa(tag, cx, cy, rot_deg, z0=1.15):
    objs_before = set(bpy.data.objects)
    w, d, h = 9.0, 7.0, 3.6
    x0, y0 = -w / 2, 0.0
    kit.slab_with_hole(f'{tag}_plinth', -6.0, -6.5, 6.0, d + 0.6, -0.1, z0 + 0.3, (-4.2, -6.0, 2.7, -2.2), 'deck', G)
    for k in range(4):
        box(f'{tag}_step{k}', -1.2, -6.5 - 1.2 + k * 0.3, -0.1, 1.2, -6.5, (k + 1) * (z0 + 0.3) / 4, 'deck', G, 0)
    box(f'{tag}_wall_w', x0, y0, z0 + 0.3, x0 + 0.35, d, z0 + h, 'brick', B)
    box(f'{tag}_wall_e', -x0 - 0.35, y0, z0 + 0.3, -x0, d, z0 + h, 'brick', B)
    box(f'{tag}_wall_n', x0, d - 0.3, z0 + 0.3, -x0, d, z0 + h, 'plaster_warm', B)
    box(f'{tag}_glass', x0 + 0.35, y0 + 0.4, z0 + 0.3, -x0 - 0.35, y0 + 0.44, z0 + h - 0.1, 'glass', B, 0)
    for k in range(5):
        xx = x0 + 0.35 + k * (w - 0.7) / 4
        box(f'{tag}_mul{k}', xx - 0.03, y0 + 0.38, z0 + 0.3, xx + 0.03, y0 + 0.46, z0 + h - 0.1, 'metal_dark', B, 0)
    box(f'{tag}_floor_in', x0 + 0.35, y0 + 0.44, z0 + 0.3, -x0 - 0.35, d - 0.3, z0 + 0.32, 'kota', B, 0)
    rich = FILM and tag in ('villa_e1',)
    if rich:
        suite(f'int_{tag}', z0 + 0.32, z0 + h - 0.05)
    else:
        box(f'{tag}_bed', -1.4, 3.6, z0 + 0.32, 1.4, 6.4, z0 + 0.85, 'fabric_ivory', B, 0.03)
        box(f'{tag}_headboard', -1.8, 6.4, z0 + 0.32, 1.8, 6.65, z0 + 1.6, 'teak', B, 0.01)
        box(f'{tag}_lamp', -2.6, 6.0, z0 + 1.4, -2.2, 6.3, z0 + 1.8, 'lamp', FX, 0)
        box(f'{tag}_lamp2', 2.2, 6.0, z0 + 1.4, 2.6, 6.3, z0 + 1.8, 'lamp', FX, 0)
    box(f'{tag}_inwall', x0 + 0.4, d - 0.32, z0 + 0.35, -x0 - 0.4, d - 0.31, z0 + h - 0.15, 'interior_wall', B, 0)
    kit.area_light(f'{tag}_in', 0, 3.5, z0 + h - 0.3, 6, 4, 70, coll=FX)
    box(f'{tag}_roof', -5.5, -1.8, z0 + h, 5.5, d + 0.5, z0 + h + 0.35, 'plaster', B, 0.01)
    box(f'{tag}_soffit', -5.5, -1.8, z0 + h - 0.05, 5.5, d + 0.5, z0 + h, 'teak', B, 0)
    hedge(f'{tag}_roofgreen', -5.2, d + 0.2, 5.2, d + 0.2, z0 + h + 0.35, 0.45, V, sum(map(ord, tag)) % 97, 110)
    # teak slat privacy screen on the east side of the deck
    for k in range(16):
        yy = -6.2 + k * 0.38
        box(f'{tag}_slat{k}', 5.7, yy, z0 + 0.3, 5.82, yy + 0.08, z0 + 2.6, 'teak', B, 0.004)
    pool(f'{tag}_pool', -4.0, -5.8, 2.5, -2.4, z_top=z0 + 0.3, depth=1.1, coll=P, water_drop=0.03)
    lounger(f'{tag}_lng', 4.0, -3.8, z0 + 0.3, 0.0, B)
    bollard(f'{tag}_bol', -5.6, -6.2, z0 + 0.3, FX)
    new = [o for o in bpy.data.objects if o not in objs_before]
    for o in new:
        if o.parent is None:
            o.matrix_basis = (kit.Matrix.Translation((cx, cy, 0)) @ kit.Matrix.Rotation(math.radians(rot_deg), 4, 'Z')) @ o.matrix_basis

villa_spots = [('villa_w1', -31, 2, 18), ('villa_w2', -44, 9, 30), ('villa_w3', -55, 19, 42),
               ('villa_e1', 31, 2, -18), ('villa_e2', 44, 9, -30), ('villa_e3', 55, 19, -42)]
for tag, x, y, r in villa_spots:
    villa(tag, x, y, r)
    # lawn pad around each villa
    pass

# lawns and paths
box('lawn_w', -70, -13.9, -0.03, -22, 32, 0.0, 'lawn', G, 0)
box('lawn_e', 22, -13.9, -0.03, 70, 32, 0.0, 'lawn', G, 0)
box('lawn_n', -22, 13, -0.03, 22, 40, 0.0, 'lawn', G, 0)
box('path_w', -26, -1.5, 0.0, -17, 0.5, 0.02, 'stone_pave', G, 0)
box('path_e', 17, -1.5, 0.0, 26, 0.5, 0.02, 'stone_pave', G, 0)

# lower terrace: native garden below the infinity edge
rl = random.Random(77)
for i in range(16):
    x = rl.uniform(-60, 60); y = rl.uniform(-45, -17)
    if abs(x) < 18 and y > -24: continue
    tree(f'low_tree_{i}', x, y, ground_z(x, y), rl.uniform(5, 8), rl.uniform(2.6, 4.2), seed=300 + i, coll=V, leaves=1800)
for i in range(40):
    x = rl.uniform(-70, 70); y = rl.uniform(-55, -15)
    shrub(f'low_shrub_{i}', x, y, ground_z(x, y), rl.uniform(0.8, 1.8), rl.uniform(0.6, 1.4), seed=400 + i, coll=V, n=380)
# tree line to the north (backdrop for the arrival view)
for i in range(22):
    x = -90 + i * 8.5 + rl.uniform(-2, 2); y = rl.uniform(42, 60)
    tree(f'north_tree_{i}', x, y, 0.0, rl.uniform(8, 12), rl.uniform(4, 6), seed=500 + i, coll=V, leaves=1600)

# ───────── planting ─────────
rnd = random.Random(7)
palms = [(-21, -9), (-20.5, -4), (21, -9), (20.5, -4), (-25, 4), (25, 4), (-18, 15), (18, 15),
         (-37, -6), (37, -6), (-50, 2), (50, 2), (-61, 12), (61, 12), (-8, 18), (8, 18)]
for i, (x, y) in enumerate(palms):
    palm(f'palm_{i}', x, y, 0.0, rnd.uniform(6.5, 9.5), (rnd.uniform(-0.9, 0.9), rnd.uniform(-0.9, 0.9)), seed=i, coll=V)
trees = [(-28, 18, 7, 4.0), (28, 18, 7, 4.0), (-40, 26, 8, 4.6), (40, 26, 8, 4.6), (0, 30, 9, 5.0),
         (-14, 26, 6, 3.4), (14, 26, 6, 3.4)]
for i, (x, y, h, c) in enumerate(trees):
    tree(f'tree_{i}', x, y, 0.0, h, c, seed=50 + i, coll=V, leaves=2600)
for i in range(18):
    x = rnd.choice([-1, 1]) * rnd.uniform(17, 60); y = rnd.uniform(-12, 28)
    shrub(f'shrub_{i}', x, y, 0.0, rnd.uniform(0.6, 1.2), rnd.uniform(0.6, 1.1), seed=200 + i, coll=V, n=420)
hedge('hedge_s_w', -40, -13.6, -22.5, -13.6, 0.0, 0.8, V, 31, 200)
hedge('hedge_s_e', 22.5, -13.6, 40, -13.6, 0.0, 0.8, V, 32, 200)

# loungers + umbrellas on the west and east decks
for i, y in enumerate([-11.5, -8.5]):
    for j, x in enumerate([-20.2, -18.0]):
        lounger(f'lng_w{i}{j}', x, y, 0.0, math.radians(90), B)
        lounger(f'lng_e{i}{j}', -x, y, 0.0, math.radians(-90), B)
    umbrella(f'umb_w{i}', -19.1, y + 1.3, 0.0, B)
    umbrella(f'umb_e{i}', 19.1, y + 1.3, 0.0, B)
for x in range(-36, 37, 6):
    if abs(x) > 18: bollard(f'bol_{x}', x, -13.0, 0.0, FX)

# ───────── grass (instanced clumps, stills only — the web build bakes the ground) ─────────
GR = kit.collection('grass')
clump = kit.grass_clump('grass_clump', seed=1); clump_dry = kit.grass_clump('grass_clump_dry', h=0.32, seed=2, dry=0.6)
for o in (clump, clump_dry):
    bpy.context.scene.collection.objects.unlink(o); GR.objects.link(o)
for nm, (x0, y0, x1, y1) in {'w': (-70, -13.9, -22, 32), 'e': (22, -13.9, 70, 32), 'n': (-22, 13, 22, 40)}.items():
    em = plane(f'grass_em_{nm}', x0, y0, x1, y1, 0.0, 'lawn', GR)
    kit.scatter(em, clump, (x1 - x0) * (y1 - y0) * 9, seed=ord(nm), size=1.0)
# lower terrace meadow patch following the slope
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=60, y_segments=24, size=1)
for v in bm.verts:
    x = v.co.x * 75; y = -36.5 + v.co.y * 22.5
    v.co = Vector((x, y, ground_z(x, y) + 0.005))
em = kit._finish(bm, 'grass_em_low', 'meadow', GR)
kit.scatter(em, clump_dry, 150 * 45 * 5, seed=5, size=1.3)

# ───────── sink the ground under every pool so water never shows meadow through it ─────────
bpy.context.view_layer.update()
foot = []
for o in bpy.data.objects:
    if o.get('jv_water'):
        ws = [o.matrix_world @ v.co for v in o.data.vertices]
        foot.append((min(v.x for v in ws) - 3, min(v.y for v in ws) - 3, max(v.x for v in ws) + 3, max(v.y for v in ws) + 3))
for v in gnd.data.vertices:
    for (a0, b0, a1, b1) in foot:
        if a0 <= v.co.x <= a1 and b0 <= v.co.y <= b1:
            v.co.z = -2.2
gnd.data.update()

# ───────── light ─────────
if MODE == 'dusk':
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and o.data.type == 'AREA': o.data.energy *= 3.0
    kit.mat('lamp_pool').node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 14.0
    for mn in ('hill', 'granite_far'):
        for n in kit.mat(mn).node_tree.nodes:
            if n.type == 'EMISSION': n.inputs['Color'].default_value = (0.42, 0.36, 0.42, 1); n.inputs['Strength'].default_value = 0.05
    kit.sky(sun_elev=-1.0, sun_az=250, strength=0.35, sun_strength=0.0, sun_angle=2.5)
else:
    kit.sky(sun_elev=11.0, sun_az=248, strength=0.22, sun_strength=4.0, sun_angle=1.0)

# ───────── cameras ─────────
cams = {}
cams['hero'] = kit.camera('CAM_hero', (27, -31, 9.5), (-5, -2, 2.0), lens=26)
cams['edge'] = kit.level_camera(kit.camera('CAM_edge', (9.0, -3.2, 1.55), (-22, -60, 1.55), lens=24), (-22, -60, 1.55))
cams['pool'] = kit.level_camera(kit.camera('CAM_pool', (-21.5, -12.2, 1.45), (4, -3, 2.2), lens=22), (4, -3, 1.45))
cams['villa'] = kit.camera('CAM_villa', (24.0, -8.5, 3.2), (33.5, 0.5, 1.5), lens=26)
cams['wide'] = kit.camera('CAM_wide', (0, -78, 26), (0, 4, 1), lens=35)

bpy.ops.wm.save_as_mainfile(filepath=f'/home/claude/jv5/blender/resort_{MODE}{"_film" if FILM else ""}.blend')
print('SAVED resort', MODE, len(bpy.data.objects), 'objects')
