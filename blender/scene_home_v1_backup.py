"""Scene C — Residential: Vastu-led 2BHK duplex, 30 x 40 ft east-facing plot (studio concept,
same envelope as project doc jv-vastu-duplex-30x40-concept). Brick modernism.
Origin = plot SW corner. +X east (road side), +Y north. Feet converted to metres.
Object-name prefixes b01..b10 drive the scroll 'plan -> building' sequence on the web."""
import sys, math, random
sys.path.insert(0, '/home/claude/jv5/blender')
import bpy
from mathutils import Vector
import kit
import os
FILM = os.environ.get('JV_FILM') == '1'
if FILM:
    import interior as I
from kit import box, plane, cyl, palm, tree, shrub, hedge, bollard, wall, window, jali, car

FT = 0.3048
def ft(f, i=0.0): return (f + i / 12.0) * FT

kit.reset()
if FILM: I.materials()
B = kit.collection('buildings'); G = kit.collection('ground'); V = kit.collection('vegetation')
F = kit.collection('far'); FX = kit.collection('fixtures'); C = kit.collection('context')

PX, PY = ft(40), ft(30)                   # plot 40 ft E–W x 30 ft N–S
X0, X1 = ft(2), ft(30)                    # west setback 2 ft, building 28 ft
Y0, Y1 = ft(2), ft(27)                    # south setback 2 ft, building 25 ft, north setback 3 ft
T = ft(0, 9)                              # 9" external walls
PL = ft(1, 6)                             # plinth 1'6"
FF = PL + ft(10)                          # floor to floor 10'0"
RF = FF + ft(10)
SL = 0.15                                 # slab

# ── context: street, footpath, neighbours ──
box('ctx_ground', -40, -40, -0.25, 60, 50, -0.02, 'meadow', C, 0)
box('ctx_road', PX + 1.8, -40, -0.05, PX + 9.1, 50, 0.0, 'asphalt', C, 0)
box('ctx_foot_w', PX, -40, -0.05, PX + 1.8, 50, 0.15, 'stone_pave', C, 0)
box('ctx_foot_e', PX + 9.1, -40, -0.05, PX + 10.9, 50, 0.15, 'stone_pave', C, 0)
box('ctx_drain', PX + 1.6, -40, 0.0, PX + 1.8, 50, 0.18, 'curb', C, 0)
for i, (y0, y1, h, m) in enumerate([(PY + 0.0, PY + 9.14, 7.2, 'paint_a'), (-9.14, -0.0, 9.8, 'paint_b'),
                                    (PY + 9.14, PY + 18.3, 6.6, 'paint_c'), (-18.3, -9.14, 7.0, 'paint_a')]):
    box(f'ctx_nb{i}', 0.6, y0 + 0.6, 0.0, 9.0, y1 - 0.9, h, m, C, 0.01)
    box(f'ctx_nb{i}_roofp', 0.6, y0 + 0.6, h, 9.0, y1 - 0.9, h + 0.9, m, C, 0.01)
    for fl in range(int(h // 3.1)):
        box(f'ctx_nb{i}_win{fl}', 9.0, y0 + 2.0, 1.2 + fl * 3.1, 9.05, y1 - 2.4, 2.4 + fl * 3.1, 'glass_dark', C, 0)
        box(f'ctx_nb{i}_ch{fl}', 9.0, y0 + 1.8, 2.5 + fl * 3.1, 9.5, y1 - 2.2, 2.6 + fl * 3.1, 'plaster', C, 0)
        for (yy, sg) in ((y0 + 0.6, -1), (y1 - 0.9, 1)):
            box(f'ctx_nb{i}_sw{fl}_{sg}', 2.5, yy - 0.03 if sg < 0 else yy, 1.3 + fl * 3.1, 4.2, yy if sg < 0 else yy + 0.03, 2.4 + fl * 3.1, 'glass_dark', C, 0)
            box(f'ctx_nb{i}_sw2{fl}_{sg}', 6.0, yy - 0.03 if sg < 0 else yy, 1.3 + fl * 3.1, 7.2, yy if sg < 0 else yy + 0.03, 2.4 + fl * 3.1, 'glass_dark', C, 0)
for i, (y0, y1, h, m) in enumerate([(-6, 3, 7.0, 'paint_c'), (4, 13, 9.6, 'paint_a'), (14, 24, 6.6, 'paint_b'), (-16, -7, 6.8, 'paint_b')]):
    box(f'ctx_opp{i}', PX + 12.5, y0, 0.0, PX + 22, y1, h, m, C, 0.01)
    for fl in range(int(h // 3.1)):
        box(f'ctx_opp{i}_w{fl}', PX + 12.45, y0 + 1.5, 1.2 + fl * 3.1, PX + 12.5, y1 - 1.5, 2.4 + fl * 3.1, 'glass_dark', C, 0)
rnd = random.Random(12)
for i, y in enumerate([-16, -28, 34, 46]):
    tree(f'ctx_streettree_{i}', PX + 10.2, y, 0.15, rnd.uniform(7, 9), rnd.uniform(3.5, 4.5), seed=700 + i, coll=C, leaves=2000)
for i, y in enumerate([-8, 6, 20]):
    cyl(f'ctx_pole{i}', PX + 1.2, y, 0.15, 7.5, 0.07, 'metal_dark', C, 10)
peaks = [(250, 1400, 400, 90), (300, 1600, 420, 110), (210, 1500, 380, 70), (340, 1200, 320, 60), (30, 1800, 500, 80)]
kit.hills_ring('far_hills', r0=420, r1=2600, z_base=-6, seed=33, coll=F, peaks=peaks)
# surrounding layout: blocks of G+1 / G+2 homes along a street grid, with avenue trees
rb = random.Random(5)
mats = ['paint_a', 'paint_b', 'paint_c']
for bx in range(-6, 7):
    for by in range(-7, 8):
        cx = bx * 32.0 + 5; cy = by * 22.0
        if -1 <= bx <= 1 and -2 <= by <= 2: continue        # keep the street around the site clear
        if math.hypot(cx, cy) > 230: continue
        for k in range(3):
            w = rb.uniform(8, 11); d = rb.uniform(8, 10); h = rb.choice([6.4, 7.2, 9.8, 10.2])
            x0 = cx + k * 10 - 14; y0 = cy - d / 2
            box(f'ctx_blk_{bx}_{by}_{k}', x0, y0, 0.0, x0 + w - 0.8, y0 + d, h, rb.choice(mats), C, 0)
        if rb.random() < 0.6:
            tree(f'ctx_blk_tree_{bx}_{by}', cx + 16, cy + 9, 0.0, rb.uniform(7, 10), rb.uniform(3.5, 5), seed=bx * 31 + by, coll=C, leaves=900)

# ── b01 plot + plinth ──
box('b01_plot', 0, 0, -0.02, PX, PY, 0.02, 'stone_pave', B, 0)
box('b01_plinth', X0, Y0, 0.0, X1, Y1, PL, 'stone_dark', B, 0.006)
box('b01_steps', X1, ft(17), 0.0, X1 + 0.9, ft(23), PL * 0.5, 'stone_dark', B, 0.004)
box('b01_steps2', X1, ft(17), PL * 0.5, X1 + 0.45, ft(23), PL, 'stone_dark', B, 0.004)

# ── b02 ground-floor walls with openings ──
gz0, gz1 = PL, FF - SL
wall('b02_s', 'x', X0, X1, Y0, Y0 + T, gz0, gz1, [(ft(4), ft(9), PL + 0.8, PL + 2.2), (ft(13), ft(15), PL + 0.6, gz1 - 0.2), (ft(22), ft(26), PL + 1.0, PL + 2.2)], 'brick', B)
wall('b02_e', 'y', Y0, Y1, X1 - T, X1, gz0, gz1, [(ft(5), ft(10), PL + 1.0, PL + 2.2), (ft(18), ft(22), PL, PL + 2.25), (ft(23, 6), ft(25, 6), PL + 0.9, PL + 1.9)], 'brick', B)
wall('b02_n', 'x', X0, X1, Y1 - T, Y1, gz0, gz1, [(ft(13), ft(22), PL + 0.45, gz1 - 0.05), (ft(4), ft(6), PL + 1.8, PL + 2.3)], 'brick', B)
wall('b02_w', 'y', Y0, Y1, X0, X0 + T, gz0, gz1, [(ft(14), ft(18), PL + 0.9, PL + 2.1)], 'brick', B)

# ── b03 first-floor slab + chajjas + balcony slab ──
VOID = (ft(13), ft(19, 9), ft(22), Y1 - T)          # double-height void over the living
if FILM:
    kit.slab_with_hole('b03_slab', X0 - 0.05, Y0 - 0.05, X1 + 0.05, Y1 + 0.05, FF - SL, FF, VOID, 'plaster', B)
else:
    box('b03_slab', X0 - 0.05, Y0 - 0.05, FF - SL, X1 + 0.05, Y1 + 0.05, FF, 'plaster', B, 0.006)
box('b03_balcony', X1, ft(15), FF - SL, X1 + ft(4), ft(26, 6), FF, 'plaster', B, 0.006)
box('b03_porch', X1, Y0, FF - SL, PX - 0.3, ft(14), FF, 'plaster', B, 0.006)     # car-porch canopy (SE)
for nm, a, b2 in [('s1', ft(3.5), ft(9.5)), ('s3', ft(21.5), ft(26.5))]:
    box(f'b03_chajja_{nm}', a, Y0 - 0.45, PL + 2.25, b2, Y0, PL + 2.33, 'plaster', B, 0.004)

# ── b04 first-floor walls ──
fz0, fz1 = FF, RF - SL
wall('b04_s', 'x', X0, X1, Y0, Y0 + T, fz0, fz1, [(ft(4), ft(10), FF + 0.75, FF + 2.2), (ft(13), ft(15), FF, fz1 - 0.2), (ft(21), ft(26), FF + 0.75, FF + 2.2)], 'brick', B)
wall('b04_e', 'y', Y0, Y1, X1 - T, X1, fz0, fz1, [(ft(4), ft(11), FF + 0.75, FF + 2.2), (ft(15, 6), ft(26), FF, FF + 2.4)], 'brick', B)
wall('b04_n', 'x', X0, X1, Y1 - T, Y1, fz0, fz1, [(ft(13), ft(22), FF, fz1 - 0.1), (ft(4), ft(6), FF + 1.7, FF + 2.2)], 'brick', B)
wall('b04_w', 'y', Y0, Y1, X0, X0 + T, fz0, fz1, [(ft(16), ft(18), FF + 1.7, FF + 2.2)], 'brick', B)
box('b04_band', X0 - 0.06, Y0 - 0.06, FF - SL - 0.05, X1 + 0.06, Y0 + 0.01, FF + 0.05, 'plaster', B, 0.004)

# ── b05 roof slab ──
SKY = (ft(14, 3), ft(20, 3), ft(20, 9), ft(23, 3))
if FILM:
    kit.slab_with_hole('b05_roof', X0 - 0.3, Y0 - 0.3, X1 + 0.3, Y1 + 0.3, RF - SL, RF, SKY, 'plaster', B)
else:
    box('b05_roof', X0 - 0.3, Y0 - 0.3, RF - SL, X1 + 0.3, Y1 + 0.3, RF, 'plaster', B, 0.006)
box('b05_roof_bal', X1 + 0.3, ft(15) - 0.3, RF - SL, X1 + ft(4) + 0.3, ft(26, 6) + 0.3, RF, 'plaster', B, 0.006)

# ── b06 parapet, mumty, tank stand ──
pz = RF + 0.95
box('b06_par_s', X0 - 0.3, Y0 - 0.3, RF, X1 + 0.3, Y0 - 0.18, pz, 'brick', B)
box('b06_par_n', X0 - 0.3, Y1 + 0.18, RF, X1 + 0.3, Y1 + 0.3, pz, 'brick', B)
box('b06_par_w', X0 - 0.3, Y0 - 0.3, RF, X0 - 0.18, Y1 + 0.3, pz, 'brick', B)
box('b06_par_e', X1 + 0.18, Y0 - 0.3, RF, X1 + 0.3, Y1 + 0.3, pz, 'brick', B)
for nm, (a0, b0, a1, b1) in {'s': (X0 - 0.32, Y0 - 0.32, X1 + 0.32, Y0 - 0.16), 'n': (X0 - 0.32, Y1 + 0.16, X1 + 0.32, Y1 + 0.32),
                             'w': (X0 - 0.32, Y0 - 0.32, X0 - 0.16, Y1 + 0.32), 'e': (X1 + 0.16, Y0 - 0.32, X1 + 0.32, Y1 + 0.32)}.items():
    box(f'b06_coping_{nm}', a0, b0, pz, a1, b1, pz + 0.06, 'plaster', B, 0.003)
MX0, MX1, MY0, MY1 = ft(12, 6), ft(21, 3), Y0, ft(12)
wall('b06_mumty_e', 'y', MY0, MY1, MX1 - T, MX1, RF, RF + 2.55, [(ft(6), ft(9), RF, RF + 2.1)], 'brick', B)
box('b06_mumty_w', MX0, MY0, RF, MX0 + T, MY1, RF + 2.55, 'brick', B)
box('b06_mumty_s', MX0, MY0, RF, MX1, MY0 + T, RF + 2.55, 'brick', B)
box('b06_mumty_n', MX0, MY1 - T, RF, MX1, MY1, RF + 2.55, 'brick', B)
box('b06_mumty_roof', MX0 - 0.3, MY0 - 0.3, RF + 2.55, MX1 + 0.3, MY1 + 0.3, RF + 2.7, 'plaster', B, 0.005)
box('b06_tank_stand', ft(3), ft(3), RF, ft(8), ft(8), RF + 1.0, 'concrete', B, 0.005)
cyl('b06_tank', ft(5, 6), ft(5, 6), RF + 1.0, RF + 2.25, 0.58, 'tank', B, 24)

# ── b07 full-height brick jali on the east balcony ──
jali('b07_jali', 'y', ft(15), ft(26, 6), X1 + ft(4) - 0.115, X1 + ft(4), FF, RF - SL, B)
box('b07_jali_cap', X1 + ft(4) - 0.13, ft(15), RF - SL - 0.04, X1 + ft(4) + 0.01, ft(26, 6), RF - SL, 'plaster', B, 0)

# ── b08 glazing + doors ──
window('b08_gs_bed', 'x', ft(4), ft(9), Y0 + T * 0.5, PL + 0.8, PL + 2.2, B, mullions=1)
window('b08_gs_stair', 'x', ft(13), ft(15), Y0 + T * 0.5, PL + 0.6, gz1 - 0.2, B, mullions=0)
window('b08_gs_kit', 'x', ft(22), ft(26), Y0 + T * 0.5, PL + 1.0, PL + 2.2, B, mullions=1)
window('b08_ge_kit', 'y', ft(5), ft(10), X1 - T * 0.5, PL + 1.0, PL + 2.2, B, mullions=1)
box('b08_ge_door', X1 - T * 0.5 - 0.03, ft(18), PL, X1 - T * 0.5 + 0.03, ft(22), PL + 2.25, 'teak', B, 0.004)
window('b08_ge_pooja', 'y', ft(23, 6), ft(25, 6), X1 - T * 0.5, PL + 0.9, PL + 1.9, B, mullions=0)
window('b08_gn_liv', 'x', ft(13), ft(22), Y1 - T * 0.5, PL + 0.45, gz1 - 0.05, B, mullions=3)
window('b08_fs_m', 'x', ft(4), ft(10), Y0 + T * 0.5, FF + 0.75, FF + 2.2, B, mullions=2)
window('b08_fs_stair', 'x', ft(13), ft(15), Y0 + T * 0.5, FF, fz1 - 0.2, B, mullions=0)
window('b08_fs_l', 'x', ft(21), ft(26), Y0 + T * 0.5, FF + 0.75, FF + 2.2, B, mullions=1)
window('b08_fe_l', 'y', ft(4), ft(11), X1 - T * 0.5, FF + 0.75, FF + 2.2, B, mullions=2)
window('b08_fe_sit', 'y', ft(15, 6), ft(26), X1 - T * 0.5, FF, FF + 2.4, B, mullions=3)
window('b08_fn_void', 'x', ft(13), ft(22), Y1 - T * 0.5, FF, fz1 - 0.1, B, mullions=3)
if FILM:
    for k, (a0, b0, a1, b1) in enumerate([(SKY[0] - 0.1, SKY[1] - 0.1, SKY[2] + 0.1, SKY[1]), (SKY[0] - 0.1, SKY[3], SKY[2] + 0.1, SKY[3] + 0.1),
                                          (SKY[0] - 0.1, SKY[1], SKY[0], SKY[3]), (SKY[2], SKY[1], SKY[2] + 0.1, SKY[3])]):
        box(f'b08_sky_up{k}', a0, b0, RF, a1, b1, RF + 0.3, 'plaster', B, 0.004)
    box('b08_skylight', SKY[0], SKY[1], RF + 0.28, SKY[2], SKY[3], RF + 0.3, 'glass', B, 0)
else:
    box('b08_skylight', ft(14), ft(19), RF, ft(21), ft(25), RF + 0.35, 'glass', B, 0)
if FILM:
    # sliding gate: black MS frame with horizontal teak slats and gaps
    g0, g1 = Y0 + 0.2, ft(14)
    for nm, (a0, a1, z0, z1) in {'l': (g0, g0 + 0.05, 0.05, 1.5), 'r': (g1 - 0.05, g1, 0.05, 1.5), 'b': (g0, g1, 0.05, 0.11), 't': (g0, g1, 1.45, 1.5)}.items():
        box(f'b08_gate_f{nm}', PX - 0.11, a0, z0, PX - 0.05, a1, z1, 'metal_dark', B, 0.002)
    for k in range(11):
        z = 0.14 + k * 0.118
        box(f'b08_gate_s{k}', PX - 0.1, g0 + 0.05, z, PX - 0.06, g1 - 0.05, z + 0.092, 'teak', B, 0.003)
    for k in range(3):
        cyl(f'b08_gate_w{k}', PX - 0.08, g0 + 0.35 + k * 1.3, 0.0, 0.05, 0.04, 'metal_dark', B, 10)
else:
    box('b08_gate', PX - 0.12, Y0 + 0.2, 0.0, PX - 0.04, ft(14), 1.5, 'metal_dark', B, 0.004)
# interior glow seen through glass
if not FILM:
    box('b08_in_liv', ft(13), Y1 - T - 0.6, PL, ft(22), Y1 - T - 0.55, RF - SL - 0.1, 'interior_wall', FX, 0)
kit.area_light('b08_in_light', ft(17), ft(18), RF - SL - 0.2, 3, 3, 90, coll=FX)
kit.area_light('b08_in_light2', ft(8), ft(6), FF - SL - 0.2, 2.5, 2.5, 40, coll=FX)

# ── b09 terrace: solar array, planters ──
for r in range(2):
    for c in range(3 if FILM else 4):
        # film: array moved to the north-west of the terrace so it no longer shades the skylight
        x0 = (0.8 + c * 1.05) if FILM else ft(13, 6) + c * 1.05; y0 = ft(15) + r * 1.9
        sp = box(f'b09_solar_{r}{c}', x0, y0, 0, x0 + 1.0, y0 + 1.7, 0.04, 'solar', B, 0)
        sp.rotation_euler = (math.radians(-13), 0, 0); sp.location = (0, 0, RF + 0.9 + (0 if r == 0 else 0.0))
        cyl(f'b09_solar_leg{r}{c}a', x0 + 0.1, y0 + 0.2, RF, RF + 0.95, 0.025, 'metal_dark', B, 6)
        cyl(f'b09_solar_leg{r}{c}b', x0 + 0.9, y0 + 1.5, RF, RF + 1.3, 0.025, 'metal_dark', B, 6)
for i in range(4):
    y = ft(2) + 0.4 + i * 1.9
    box(f'b09_planter{i}', X1 - 0.8, y, RF, X1 - 0.15, y + 1.2, RF + 0.55, 'concrete', B, 0.01)
    shrub(f'b09_plant{i}', X1 - 0.48, y + 0.6, RF + 0.55, 0.45, 0.6, seed=900 + i, coll=V, n=160)

# ── b10 landscape: compound wall, NE garden, parking, car ──
cw = 1.35
box('b10_cw_s', 0, 0, 0, PX, 0.15, cw, 'plaster_warm', B, 0.004)
box('b10_cw_n', 0, PY - 0.15, 0, PX, PY, cw, 'plaster_warm', B, 0.004)
box('b10_cw_w', 0, 0, 0, 0.15, PY, cw, 'plaster_warm', B, 0.004)
box('b10_cw_e1', PX - 0.15, ft(14), 0, PX, ft(17), cw, 'plaster_warm', B, 0.004)
box('b10_cw_e2', PX - 0.15, ft(23), 0, PX, PY, cw, 'plaster_warm', B, 0.004)
box('b10_cw_cap', PX - 0.18, ft(23), cw, PX + 0.03, PY, cw + 0.06, 'brick', B, 0)
box('b10_lawn_ne', X1 + 0.2, ft(17) + 0.3, 0.02, PX - 0.2, PY - 0.2, 0.05, 'lawn', B, 0)
for i, (x, y) in enumerate([(X1 + 2.2, ft(24)), (X1 + 2.8, ft(21)), (X1 + 1.6, ft(27))]):
    shrub(f'b10_shrub{i}', x, y, 0.05, 0.5, 0.6, seed=950 + i, coll=V, n=220)
box('b10_tulsi', X1 + 1.4, ft(19, 6), 0.02, X1 + 1.9, ft(21), 0.75, 'brick', B, 0.01)
shrub('b10_tulsi_plant', X1 + 1.65, ft(20, 3), 0.75, 0.28, 0.4, seed=990, coll=V, n=120)
car('b10_car', X1 + 1.55, ft(7), 0.02, 0.0, B)
hedge('b10_hedge_w', 0.4, 0.4, 0.4, PY - 0.4, 0.0, 1.1, V, 3, 120)

# ── film interior: double-height living, pooja door, partitions, gallery ──
if FILM:
    IF = PL + 0.02
    box('int_h_floor', X0 + T, Y0 + T, PL, X1 - T, Y1 - T, IF, 'kota', B, 0)
    box('int_h_floor1', X0 + T, Y0 + T, FF, X1 - T, VOID[1], FF + 0.02, 'kota', B, 0)
    PT = ft(0, 4.5); gz = FF - SL
    kit.wall('int_h_pw', 'y', ft(14, 4.5), Y1 - T, ft(8), ft(8) + PT, IF, gz, [], 'interior_wall', B)
    kit.wall('int_h_bedn', 'x', X0 + T, ft(13), ft(14), ft(14) + PT, IF, gz, [(ft(9), ft(12), IF, IF + 2.1)], 'interior_wall', B)
    kit.wall('int_h_stairw', 'y', Y0 + T, ft(14), ft(13), ft(13) + PT, IF, gz, [], 'interior_wall', B)
    kit.wall('int_h_kitn', 'x', ft(21, 3), X1 - T, ft(12, 6), ft(12, 6) + PT, IF, gz, [(ft(22), ft(25), IF, IF + 2.1)], 'interior_wall', B)
    kit.wall('int_h_foyw', 'y', ft(14, 4.5), Y1 - T, ft(24, 3), ft(24, 3) + PT, IF, gz, [(ft(15), ft(19, 6), IF, IF + 2.3), (ft(21, 6), ft(24), IF, IF + 2.1)], 'interior_wall', B)
    kit.wall('int_h_poojas', 'x', ft(24, 3) + PT, X1 - T, ft(20, 1.5), ft(20, 1.5) + PT, IF, gz, [], 'interior_wall', B)
    # first-floor walls flanking the void
    kit.wall('int_h_ffw', 'y', VOID[1], VOID[3], VOID[0] - PT, VOID[0], FF, RF - SL, [], 'brick', B)
    kit.wall('int_h_ffe', 'y', VOID[1], VOID[3], VOID[2], VOID[2] + PT, FF, RF - SL, [], 'brick', B)
    # gallery balustrade: teak posts + brass rail along the void's south edge
    for k in range(13):
        xx = VOID[0] + 0.05 + k * (VOID[2] - VOID[0] - 0.1) / 12
        I.hard(f'int_h_bal{k}', xx - 0.02, VOID[1] - 0.06, FF, xx + 0.02, VOID[1] - 0.02, FF + 0.95, 'teak', B, 0.003)
    I.hard('int_h_rail', VOID[0], VOID[1] - 0.07, FF + 0.95, VOID[2], VOID[1] - 0.01, FF + 1.0, 'brass', B, 0.004)
    I.hard('int_h_edge', VOID[0], VOID[1] - 0.02, FF - SL - 0.02, VOID[2], VOID[1], FF + 0.02, 'teak', B, 0.003)
    # pooja door: teak frame, brass bell strip, warm glow inside
    I.hard('int_h_pd_l', ft(24, 3) - 0.04, ft(21, 6) - 0.1, IF, ft(24, 3) + PT + 0.02, ft(21, 6), IF + 2.2, 'teak', B, 0.004)
    I.hard('int_h_pd_r', ft(24, 3) - 0.04, ft(24), IF, ft(24, 3) + PT + 0.02, ft(24) + 0.1, IF + 2.2, 'teak', B, 0.004)
    I.hard('int_h_pd_t', ft(24, 3) - 0.04, ft(21, 6) - 0.1, IF + 2.1, ft(24, 3) + PT + 0.02, ft(24) + 0.1, IF + 2.3, 'teak', B, 0.004)
    for k in range(9):
        yy = ft(21, 6) + 0.05 + k * (ft(24) - ft(21, 6) - 0.1) / 8
        kit.cyl(f'int_h_bell{k}', ft(24, 3) - 0.02, yy, IF + 1.95, IF + 2.1, 0.012, 'brass', B, 8)
        I.cone(f'int_h_bellc{k}', ft(24, 3) - 0.02, yy, IF + 1.9, IF + 1.96, 0.025, 0.008, 'brass', B, 12)
    box('int_h_pooja_glow', X1 - T - 0.03, ft(20, 6), IF + 0.4, X1 - T - 0.01, ft(23, 3), IF + 2.2, 'lamp_soft', FX, 0)
    I.hard('int_h_pooja_shelf', ft(26), ft(21, 6), IF, X1 - T - 0.05, ft(25, 6), IF + 0.75, 'teak', B, 0.006)
    I.samai('int_h_samai_l', ft(23, 6), ft(21), IF, B, h=0.95)
    I.urli('int_h_urli', ft(22, 3), ft(22, 9), IF, B, r=0.34)
    # living: sofa on the west wall, swing in the void, armchair by the foyer
    I.rug('int_h_rug', ft(10, 6), ft(16), ft(20, 6), ft(23, 6), IF, B, 'rug_dhurrie', 'linen_oat')
    with I.Place(0, 0, IF, 0):
        I.sofa('int_h_sofa', ft(8) + PT + 1.02, ft(19, 6), 90, B, w=2.35, d=0.98, fab='linen_oat', accents=('fabric_rust', 'fabric_indigo'))
        I.coffee_table('int_h_ct', ft(13, 3), ft(19, 6), 90, B, w=1.2, d=0.65, top='marble')
        I.armchair('int_h_ac', ft(20, 9), ft(18), -110, B, fab='linen_white', frame='teak')
        I.side_table('int_h_st', ft(9, 3), ft(23, 3), B, r=0.22, h=0.5)
        I.table_lamp('int_h_tl', ft(9, 3), ft(23, 3), 0.5, FX, h=0.52)
        I.floor_lamp('int_h_fl', ft(9, 3), ft(15, 9), FX, h=1.55)
        I.plant('int_h_plant', ft(22, 9), ft(24, 9), 0, B, pot_r=0.28, pot_h=0.5, h=2.3, crown=0.7, pot='terracotta', seed=61)
        I.plant('int_h_plant2', ft(13, 9), ft(25, 6), 0, B, pot_r=0.2, pot_h=0.38, h=0.9, crown=0.4, pot='ceramic_white', seed=62, kind='leafy')
    # panelled teak main door (outer face)
    dx = X1 - T * 0.5 + 0.03
    I.hard('int_h_door_fr', dx, ft(18) - 0.08, PL, dx + 0.04, ft(22) + 0.08, PL + 2.33, 'teak', B, 0.004)
    for lf, (a, b) in enumerate([(ft(18), ft(20)), (ft(20), ft(22))]):
        I.hard(f'int_h_door_lf{lf}', dx + 0.04, a + 0.01, PL + 0.01, dx + 0.07, b - 0.01, PL + 2.24, 'walnut', B, 0.004)
        for k in range(3):
            z0 = PL + 0.12 + k * 0.72
            I.hard(f'int_h_door_pn{lf}{k}', dx + 0.07, a + 0.1, z0, dx + 0.085, b - 0.1, z0 + 0.6, 'teak', B, 0.006)
        I.ccyl(f'int_h_door_hd{lf}', dx + 0.1, (b - 0.06) if lf == 0 else (a + 0.06), PL + 0.95, PL + 1.25, 0.012, 'brass', B, 12)
    I.swing('int_h_swing', ft(17, 6), ft(25), IF + 0.5, RF - SL, 0, B)
    I.pendant('int_h_lantern', ft(17, 6), ft(21, 9), RF + 0.28, FF + 0.5, FX, r=0.25, style='lantern')
    I.art('int_h_art', 'y', ft(17, 6), ft(22), ft(8) + PT, IF + 1.25, IF + 2.35, B, mat='art_earth', inward=1)
    I.curtain('int_h_cur_w', 'x', ft(13), ft(14, 3), Y1 - T - 0.12, IF, RF - SL - 0.1, B, folds=5, amp=0.04)
    I.curtain('int_h_cur_e', 'x', ft(20, 9), ft(22), Y1 - T - 0.12, IF, RF - SL - 0.1, B, folds=5, amp=0.04)
    kit.area_light('int_h_fill', ft(15), ft(17, 6), FF - SL - 0.05, 2.4, 1.6, 45, coll=FX)
    kit.area_light('int_h_fill2', ft(17, 6), ft(22, 6), RF - SL - 0.25, 2.2, 1.6, 40, coll=FX)

# light — morning sun on the east (road) facade
kit.sky(sun_elev=27.0, sun_az=112, strength=0.2, sun_strength=4.2, sun_angle=0.9)

kit.level_camera(kit.camera('CAM_street', (PX + 8.4, ft(6), 1.6), (X1, ft(17), 3.6), lens=22, shift_y=0.2), (X1, ft(17), 1.6))
kit.camera('CAM_aerial', (PX + 10, PY + 8, 12.5), (ft(18), ft(13), 3.0), lens=26)
kit.camera('CAM_jali', (PX - 0.4, ft(10), FF + 1.4), (X1 + ft(4), ft(22), FF + 1.6), lens=24)
bpy.ops.wm.save_as_mainfile(filepath=f'/home/claude/jv5/blender/home_morning{"_film" if FILM else ""}.blend')
print('SAVED home', len(bpy.data.objects))
