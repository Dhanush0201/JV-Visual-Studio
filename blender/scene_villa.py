"""Scene B — Luxury private villa (studio concept): glass pavilion, cantilevered upper volume,
exposed-brick tower with jali, 22 m lap pool, lawn and garden. +Y north, +X east.
Modes: day | dusk (same cameras for a scroll cross-fade)."""
import sys, math, random
sys.path.insert(0, '/home/claude/jv5/blender')
import bpy, bmesh
from mathutils import Vector
import kit
import os
FILM = os.environ.get('JV_FILM') == '1'
os.environ['JV_SCENE'] = 'villa'
if FILM:
    import interior as I
from kit import box, plane, cyl, pool, palm, tree, shrub, hedge, boulder, lounger, umbrella, bollard, wall, window, jali

MODE = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'day'
kit.reset()
if FILM: I.materials()
B = kit.collection('buildings'); G = kit.collection('ground'); V = kit.collection('vegetation')
F = kit.collection('far'); P = kit.collection('pools'); FX = kit.collection('fixtures')
dusk = MODE == 'dusk'

# ground + context
gnd = kit.terrain('ground_main', size=520, res=110, z=-0.02, flat_r=60, hill_h=8, seed=3, coll=G, material='meadow')
peaks = [(150, 1300, 380, 90), (190, 1600, 460, 140), (220, 1100, 320, 70), (120, 1800, 500, 120),
         (250, 1500, 420, 100), (300, 1400, 380, 60), (40, 1600, 420, 70), (80, 1200, 300, 50)]
kit.hills_ring('far_hills', r0=200, r1=2600, z_base=-12, seed=21, coll=F, peaks=peaks)
box('lawn', -30, -32, -0.03, 30, 22, 0.0, 'lawn', G, 0)

PL = 0.6   # plinth level
# plinth + decks with pool opening
kit.slab_with_hole('plinth_deck', -16, -11.5, 18, 12, -0.3, PL, (-12.2, -9.2, 10.2, -5.3), 'deck', G)
pool('lap', -12, -9.0, 10, -5.5, z_top=PL, depth=1.4, coll=P, water_drop=0.02)
kit.slab_with_hole('lap_coping', -12.4, -9.4, 10.4, -5.1, PL - 0.02, PL + 0.02, (-12, -9.0, 10, -5.5), 'stone_dark', G)
kit.lights_in_pool('lap', -12, -5.5 - 0.2, 10, -5.5, PL - 0.5, P, 5)
for i in range(4):
    box(f'steps_{i}', -16 - 0.0, -11.5 - 1.2 + i * 0.3, -0.3, 18, -11.5 - 0.9 + i * 0.3, 0.15 * (i + 1), 'stone_pave', G, 0.004)

# ── ground floor glass pavilion (living + dining) ──
GF0, GF1 = PL, PL + 3.3
box('gf_floor', -12, 0, PL, 10, 9, PL + 0.02, 'kota', B, 0)
box('gf_backwall', -12, 8.7, PL, 10, 9.0, GF1, 'teak', B, 0)
window('gf_glass_s', 'x', -12, 10, 0.05, GF0, GF1, B, frame=0.06, mullions=5)
window('gf_glass_w', 'y', 0, 8.7, -11.95, GF0, GF1, B, frame=0.06, mullions=2)
box('gf_ceiling', -12, 0, GF1 - 0.05, 10, 9, GF1, 'teak', B, 0)
# interior furniture
if FILM:
    F = PL + 0.02
    I.rug('int_gf_rug', -9.2, 0.9, -2.8, 5.6, F, B, 'rug_wool', 'linen_oat')
    with I.Place(0, 0, F, 0):
        I.sofa('int_gf_sofa', -6.0, 3.95, 0, B, w=3.0, d=1.0, fab='linen_oat', accents=('fabric_rust', 'fabric_indigo'))
        I.armchair('int_gf_ac1', -7.6, 1.55, 165, B, fab='linen_white', frame='walnut')
        I.armchair('int_gf_ac2', -4.4, 1.55, 195, B, fab='linen_white', frame='walnut')
        I.coffee_table('int_gf_ct', -6.0, 2.75, 0, B, w=1.5, d=0.8, top='stone_dark')
        I.side_table('int_gf_st', -8.0, 4.45, B, r=0.24, h=0.52)
        I.table_lamp('int_gf_tl', -8.0, 4.45, 0.52, FX, h=0.55)
        I.floor_lamp('int_gf_fl', -3.85, 4.75, FX, h=1.6)
        I.dining_table('int_gf_dn', 3.5, 3.9, 0, B, w=2.6, d=1.0, chairs=8)
        I.plant('int_gf_plant1', -10.9, 1.0, 0, B, pot_r=0.3, pot_h=0.55, h=2.1, crown=0.75, pot='ceramic_black', seed=41)
        I.plant('int_gf_plant2', 9.2, 1.1, 0, B, pot_r=0.26, pot_h=0.5, h=1.8, crown=0.6, pot='terracotta', seed=42)
        I.plant('int_gf_plant3', -2.3, 8.2, 0, B, pot_r=0.2, pot_h=0.4, h=1.0, crown=0.45, pot='terracotta', seed=43, kind='leafy')
        # kitchen island at the east end
        I.hard('int_gf_island', 6.9, 5.4, 0.0, 9.3, 6.4, 0.86, 'walnut', B, 0.008)
        I.hard('int_gf_island_top', 6.85, 5.35, 0.86, 9.35, 6.45, 0.9, 'marble', B, 0.006)
        for k, x in enumerate((7.4, 8.1, 8.8)):
            I.ccyl(f'int_gf_stool{k}', x, 5.05, 0.62, 0.66, 0.19, 'cane', B, 32)
            kit.cyl(f'int_gf_stool_leg{k}', x, 5.05, 0.0, 0.62, 0.025, 'black', B, 10)
    I.bookshelf('int_gf_shelf', 'x', -11.6, -6.4, 8.7, F, F + 2.75, B, depth=0.36, cols=4, rows=6, seed=5, wood='walnut', inward=-1)
    I.art('int_gf_art', 'x', -4.6, -2.4, 8.7, F + 1.0, F + 2.4, B, mat='art_indigo', inward=-1)
    I.art('int_gf_art2', 'x', 1.6, 5.4, 8.7, F + 1.2, F + 2.2, B, mat='art_ochre', inward=-1)
    for i, x in enumerate([2.6, 3.5, 4.4]):
        I.pendant(f'int_gf_pd{i}', x, 3.9, GF1 - 0.05, F + 1.55, FX, r=0.24)
    I.curtain('int_gf_cur', 'x', -11.9, -10.9, 0.25, F, GF1 - 0.1, B, folds=6, amp=0.05)
    I.curtain('int_gf_cur2', 'y', 0.2, 1.3, -11.75, F, GF1 - 0.1, B, folds=6, amp=0.05)
else:
    kit.sofa('gf_sofa', -8.5, 4.0, -3.5, 5.0, PL, B, 'fabric_ivory')
    kit.sofa('gf_sofa2', -9.5, 1.6, -8.6, 4.0, PL, B, 'fabric_ivory')
    box('gf_rug', -9, 1.4, PL + 0.02, -3, 4.2, PL + 0.035, 'fabric_sand', B, 0)
    box('gf_coffee', -7.2, 2.3, PL, -4.8, 3.2, PL + 0.38, 'stone_dark', B, 0.01)
    box('gf_dining', 1.0, 3.2, PL + 0.72, 6.0, 4.6, PL + 0.77, 'teak', B, 0.005)
    for x in (1.4, 5.6):
        box(f'gf_dining_leg{x}', x - 0.05, 3.3, PL, x + 0.05, 4.5, PL + 0.72, 'metal_dark', B, 0)
    for i, x in enumerate([2.0, 3.5, 5.0]):
        box(f'gf_pendant{i}', x - 0.3, 3.7, PL + 2.2, x + 0.3, 4.1, PL + 2.35, 'lamp_strong' if dusk else 'lamp', FX, 0)
        box(f'gf_pendant_wire{i}', x - 0.005, 3.895, PL + 2.35, x + 0.005, 3.905, GF1 - 0.05, 'black', FX, 0)
    box('gf_art_wall', -11.5, 8.6, PL + 0.6, -6.0, 8.7, PL + 2.6, 'plaster_warm', B, 0)
box('gf_cove', -12, 8.55, GF1 - 0.25, 10, 8.68, GF1 - 0.18, 'lamp_strong' if dusk else 'lamp_soft', FX, 0)
kit.area_light('gf_in_light', -1, 4.5, GF1 - 0.2, 20, 7, 900 if dusk else 250, coll=FX)

# ── exposed brick tower (east), two storeys, with jali on the south face ──
TW0, TW1 = 10, 16
box('tw_e', 15.65, -2, PL, 16, 12, 7.8, 'brick', B)
box('tw_n', 10, 11.65, PL, 16, 12, 7.8, 'brick', B)
box('tw_w', 10, 9.0, PL, 10.35, 12, 7.8, 'brick', B)
wall('tw_s_low', 'x', 10, 16, -2, -1.65, PL, 4.0, [(11.0, 14.6, PL, PL + 2.6)], 'brick', B)
window('tw_s_door', 'x', 11.0, 14.6, -1.8, PL, PL + 2.6, B, mullions=1)
box('tw_s_up_l', 10, -2, 4.0, 10.7, -1.65, 7.8, 'brick', B)
box('tw_s_up_r', 15.3, -2, 4.0, 16, -1.65, 7.8, 'brick', B)
jali('tw_jali', 'x', 10.7, 15.3, -1.95, -1.70, 4.0, 7.75, B)
box('tw_roof', 9.8, -2.2, 7.8, 16.2, 12.2, 8.0, 'concrete', B, 0.006)
box('tw_in_glow', 10.4, -0.8, 4.0, 15.6, -0.7, 7.6, 'lamp_soft' if dusk else 'interior_wall', FX, 0)
box('tw_floor1', 10.35, -1.65, 3.85, 15.65, 11.65, 4.0, 'concrete', B, 0)

# ── cantilevered upper volume (bedrooms), white plaster, overhangs the pavilion ──
UV0, UV1 = 3.9, 7.4
box('up_slab', -13, -3.5, UV0, 10, 10.5, UV0 + 0.35, 'plaster', B, 0.01)
box('up_roof', -13, -3.5, UV1, 10, 10.5, UV1 + 0.4, 'plaster', B, 0.01)
wall('up_s', 'x', -13, 10, -3.5, -3.2, UV0 + 0.35, UV1, [(-11.5, 6.5, UV0 + 0.9, UV1 - 0.4)], 'plaster', B)
window('up_win_s', 'x', -11.5, 6.5, -3.3, UV0 + 0.9, UV1 - 0.4, B, mullions=5, glass='glass_dark')
for i in range(26):
    xx = -11.4 + i * 0.7
    box(f'up_fin{i}', xx, -3.75, UV0 + 0.7, xx + 0.09, -3.55, UV1 - 0.2, 'teak', B, 0.004)
box('up_w', -13, -3.2, UV0 + 0.35, -12.7, 10.5, UV1, 'plaster', B)
box('up_n', -13, 10.2, UV0 + 0.35, 10, 10.5, UV1, 'plaster', B)
box('up_e', 9.7, -3.2, UV0 + 0.35, 10, 10.2, UV1, 'plaster', B)
box('up_inwall', -11.5, 8.0, UV0 + 0.4, 6.5, 8.1, UV1 - 0.1, 'lamp_soft' if dusk else 'interior_wall', FX, 0)
kit.area_light('up_in_light', -2.5, 3.0, UV1 - 0.3, 18, 8, 500 if dusk else 120, coll=FX)
hedge('up_roof_green', -12.6, 10.0, 9.6, 10.0, UV1 + 0.4, 0.5, V, 5, 120)
for i in range(5):
    box(f'up_soffit_light{i}', -11 + i * 4.2, -3.1, UV0 - 0.02, -10.6 + i * 4.2, -2.9, UV0, 'lamp_strong', FX, 0)

# stone feature wall (west) + boundary wall
box('stone_fin_w', -15.6, -4, PL, -15.0, 11, 4.6, 'granite_boulder', B, 0.01)
box('boundary_s', -32, -33, 0, 32, -32.7, 1.8, 'plaster_warm', B, 0.01)
box('boundary_w', -32, -33, 0, -31.7, 22, 1.8, 'plaster_warm', B, 0.01)
box('boundary_e', 31.7, -33, 0, 32, 22, 1.8, 'plaster_warm', B, 0.01)

# deck furniture
for i, x in enumerate([-10.5, -8.6, -6.7]):
    lounger(f'lng_{i}', x, -10.4, PL, math.radians(180), B)
umbrella('umb_0', -4.8, -10.2, PL, B)
kit.sofa('out_sofa', 12.0, -10.5, 16.0, -9.6, PL, B, 'fabric_sand')
box('fire_bowl', 13.4, -8.6, PL, 14.6, -7.6, PL + 0.45, 'stone_dark', B, 0.02)
if dusk:
    box('fire_glow', 13.6, -8.4, PL + 0.45, 14.4, -7.8, PL + 0.5, 'lamp_strong', FX, 0)
    kit.point_light('fire_pt', 14.0, -8.1, PL + 0.8, 120, coll=FX)

# planting
rnd = random.Random(4)
for i, (x, y) in enumerate([(-20, -14), (-23, -6), (-21, 4), (22, -14), (24, -5), (21, 6), (-26, 15), (26, 15)]):
    palm(f'palm_{i}', x, y, 0.0, rnd.uniform(7, 10), (rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8)), seed=60 + i, coll=V)
tree('frangipani', 18.5, -9.5, PL, 4.2, 2.6, seed=7, coll=V, leaves=1600, flowers=260)
for i, (x, y) in enumerate([(-28, -26), (-22, -29), (24, -29), (28, -24), (-28, 18), (0, 19), (28, 18), (-12, 20), (13, 20)]):
    tree(f'tree_{i}', x, y, 0.0, rnd.uniform(6, 9), rnd.uniform(3, 4.5), seed=80 + i, coll=V, leaves=2200)
hedge('hedge_s', -30, -31.8, 30, -31.8, 0.0, 1.2, V, 9, 160)
for i in range(16):
    x = rnd.uniform(-29, 29); y = rnd.uniform(-30, -14)
    shrub(f'shrub_{i}', x, y, 0.0, rnd.uniform(0.5, 1.0), rnd.uniform(0.5, 0.9), seed=120 + i, coll=V, n=300)
for i, x in enumerate(range(-14, 19, 4)):
    shrub(f'bed_{i}', x, -12.6, 0.0, 0.7, 0.5, seed=140 + i, coll=V, n=260)
for x in range(-28, 29, 7):
    bollard(f'bol_{x}', x, -15.0, 0.0, FX)

# light
if dusk:
    for mn in ('hill', 'granite_far'):
        for n in kit.mat(mn).node_tree.nodes:
            if n.type == 'EMISSION': n.inputs['Color'].default_value = (0.42, 0.36, 0.42, 1); n.inputs['Strength'].default_value = 0.05
    kit.sky(sun_elev=-2.0, sun_az=255, strength=0.32, sun_strength=0.0, sun_angle=3.0)
else:
    kit.sky(sun_elev=38.0, sun_az=215, strength=0.2, sun_strength=4.5, sun_angle=0.8, warm=False)

kit.level_camera(kit.camera('CAM_front', (6, -36, 2.4), (0, 2, 4.0), lens=26, shift_y=0.12), (0, 2, 2.4))
kit.camera('CAM_aerial', (34, -38, 20), (0, 1, 2), lens=30)
kit.level_camera(kit.camera('CAM_pool', (-13.6, -10.6, 1.55), (10, -5, 1.55), lens=22, shift_y=0.05), (10, -5, 1.55))
bpy.ops.wm.save_as_mainfile(filepath=f'/home/claude/jv5/blender/villa_{MODE}{"_film" if FILM else ""}.blend')
print('SAVED villa', MODE, len(bpy.data.objects))
