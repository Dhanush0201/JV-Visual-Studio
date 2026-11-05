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
os.environ['JV_SCENE'] = 'home'
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
for i, y in enumerate([-12, -1.5, 22]):   # poles clear of the plot frontage (none in front of the house)
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

# ── plan grid (ft from the plot's SW corner), dimension chain of the concept plan ──
#   E–W: 0'9" + 10'3" + 0'4½" + 7'6" + 0'4½" + 8'0" + 0'9" = 28'0"
#   N–S: 0'9" + 11'3" + 0'4½" + 5'4½" + 0'4½" + 6'1½" + 0'9" = 25'0"
PT = ft(0, 4.5)                                    # 4½" partitions
XA, XB, XC = ft(2, 9), ft(13, 4.5), ft(21, 3)      # clear start of bands A (SW rooms), B (stair), C (kitchen / lounge)
XA1, XB1, XC1 = ft(13), ft(20, 10.5), ft(29, 3)    # clear end of each band
YR1, YR2, YR3 = ft(2, 9), ft(14, 4.5), ft(20, 1.5) # clear start of rows 1 (south), 2, 3 (north)
YR11, YR21, YR31 = ft(14), ft(19, 9), ft(26, 3)
YK = ft(12, 6)                                     # kitchen / stair box ends at 9'9"
XU = ft(8)                                         # utility / toilet band 5'3" wide
XF = ft(23, 10.5)                                  # foyer / pooja band 5'0" clear
IF = PL + 0.02                                     # finished ground floor
FFL = FF + 0.02                                    # finished first floor
gz0, gz1 = PL, FF - SL
fz0, fz1 = FF, RF - SL
VOID = (ft(13, 4.5), ft(21), ft(21, 6), YR31)      # double-height void 8'1½" × 5'3"
STAIR = (XB, YR1, XB1, YK)                         # dog-leg stair box 7'6" × 9'9"
SKY = (ft(14, 3), ft(21, 3), ft(20, 9), ft(24))    # skylight over the void

def slab_holes(name, x0, y0, x1, y1, z0, z1, holes, material='plaster', coll=None):
    """Slab with any number of rectangular holes, split on the holes' edge lines."""
    xs = sorted(set([x0, x1] + [h[0] for h in holes] + [h[2] for h in holes]))
    ys = sorted(set([y0, y1] + [h[1] for h in holes] + [h[3] for h in holes]))
    k = 0
    for j in range(len(ys) - 1):
        run = None
        for i in range(len(xs) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            hole = any(h[0] < cx < h[2] and h[1] < cy < h[3] for h in holes)
            if not hole: run = (run[0], xs[i + 1]) if run else (xs[i], xs[i + 1])
            if (hole or i == len(xs) - 2) and run:
                box(f'{name}_{k}', run[0], ys[j], z0, run[1], ys[j + 1], z1, material, coll, 0); k += 1; run = None

def stair(name, z0, z1, coll):
    """Clockwise dog-leg in STAIR: flight 1 down the east half from the north edge, landing at the south,
    flight 2 up the west half arriving at the north edge. 18 risers, 10" treads, 150 mm waist."""
    x0, y0, x1, y1 = STAIR; xm = (x0 + x1) / 2
    n = 18; r = (z1 - z0) / n; t = ft(0, 10); land = (y1 - y0) - 8 * t
    for k in range(1, 9):              # flight 1, steps 1–8, rising southwards
        ya, yb = y1 - k * t, y1 - (k - 1) * t
        box(f'{name}_a{k}', xm + 0.02, ya, z0 + k * r - r - 0.15, x1, yb, z0 + k * r, 'kota', coll, 0.004)
    box(f'{name}_land', x0, y0, z0 + 9 * r - 0.15, x1, y0 + land, z0 + 9 * r, 'kota', coll, 0.004)
    for k in range(10, 18):            # flight 2, steps 10–17, rising northwards
        ya = y0 + land + (k - 10) * t
        box(f'{name}_b{k}', x0, ya, z0 + k * r - r - 0.15, xm - 0.02, ya + t, z0 + k * r, 'kota', coll, 0.004)
    box(f'{name}_mid', xm - 0.02, y0 + land, z0, xm + 0.02, y1, z0 + 9 * r + 0.95, 'interior_wall', coll, 0.003)
    box(f'{name}_rail', xm - 0.03, y0 + land, z0 + 9 * r + 0.95, xm + 0.03, y1, z0 + 9 * r + 1.0, 'teak', coll, 0.003)

def balustrade(name, x0, y0, x1, y1, z, coll, posts=None):
    L = max(abs(x1 - x0), abs(y1 - y0)); n = posts or max(2, int(L / 0.12))
    for k in range(n + 1):
        f = k / n; px, py = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        box(f'{name}_p{k}', px - 0.018, py - 0.018, z, px + 0.018, py + 0.018, z + 0.95, 'teak', coll, 0.002)
    box(f'{name}_rail', min(x0, x1) - 0.03, min(y0, y1) - 0.03, z + 0.95, max(x0, x1) + 0.03, max(y0, y1) + 0.03, z + 1.0, 'brass', coll, 0.003)

# ── b01 plot + plinth ──
box('b01_plot', 0, 0, -0.02, PX, PY, 0.02, 'stone_pave', B, 0)
box('b01_plinth', X0, Y0, 0.0, X1, Y1, PL, 'stone_dark', B, 0.006)
box('b01_steps', X1, ft(15), 0.0, X1 + 0.9, ft(20), PL * 0.5, 'stone_dark', B, 0.004)
box('b01_steps2', X1, ft(15), PL * 0.5, X1 + 0.45, ft(20), PL, 'stone_dark', B, 0.004)

# ── b02 ground floor: 9" external walls, 4½" partitions, floor finish ──
wall('b02_s', 'x', X0, X1, Y0, Y0 + T, gz0, gz1, [(ft(4), ft(9), PL + 0.8, PL + 2.2), (ft(14), ft(16, 6), PL + 0.6, gz1 - 0.2), (ft(22), ft(26), PL + 1.0, PL + 2.2)], 'brick', B)
wall('b02_e', 'y', Y0, Y1, X1 - T, X1, gz0, gz1, [(ft(5), ft(10), PL + 1.0, PL + 2.2), (ft(15, 6), ft(19, 6), PL, PL + 2.25), (ft(23, 6), ft(25, 6), PL + 0.9, PL + 1.9)], 'brick', B)
wall('b02_n', 'x', X0, X1, Y1 - T, Y1, gz0, gz1, [(ft(13), ft(22), PL + 0.45, gz1 - 0.05), (ft(4), ft(6), PL + 1.8, PL + 2.3)], 'brick', B)
wall('b02_w', 'y', Y0, Y1, X0, X0 + T, gz0, gz1, [(ft(7), ft(11), PL + 0.8, PL + 2.2), (ft(16), ft(18, 6), PL + 1.5, PL + 2.2)], 'brick', B)
D = 2.1   # internal door height
wall('b02_p_bed_e', 'y', YR1, YR11, XA1, XA1 + PT, IF, gz1, [], 'interior_wall', B)                                  # bedroom | stair
wall('b02_p_bed_n', 'x', XA, XA1, YR11, YR11 + PT, IF, gz1, [(ft(9, 6), ft(12, 6), IF, IF + D)], 'interior_wall', B)  # bedroom | utility, living
wall('b02_p_util_e', 'y', YR2, YR31, XU, XU + PT, IF, gz1, [(ft(15, 6), ft(18), IF, IF + D)], 'interior_wall', B)       # utility, toilet | living
wall('b02_p_toilet_s', 'x', XA, XU, YR21, YR21 + PT, IF, gz1, [(ft(4, 6), ft(7), IF, IF + D)], 'interior_wall', B)    # utility | toilet
wall('b02_p_kit_w', 'y', YR1, YK, XB1, XB1 + PT, IF, gz1, [], 'interior_wall', B)                                    # stair | kitchen
wall('b02_p_kit_n', 'x', XC, XC1, YK, YK + PT, IF, gz1, [(ft(22, 3), ft(25, 3), IF, IF + D)], 'interior_wall', B)     # kitchen | foyer, dining
wall('b02_p_foy_w', 'y', YK + PT, YR31, XF, XF + PT, IF, gz1, [(ft(14, 9), ft(19, 3), IF, IF + 2.3), (ft(21, 9), ft(24, 3), IF, IF + D)], 'interior_wall', B)  # foyer, pooja | living
wall('b02_p_pooja_s', 'x', XF + PT, XC1, YR3, YR3 + PT, IF, gz1, [], 'interior_wall', B)                              # foyer | pooja
box('b02_floor', X0 + T, Y0 + T, PL, X1 - T, Y1 - T, IF, 'kota', B, 0)

# ── b03 first-floor slab (void + stair openings), stair GF→FF, chajjas, balcony, porch ──
slab_holes('b03_slab', X0 - 0.05, Y0 - 0.05, X1 + 0.05, Y1 + 0.05, FF - SL, FF, [VOID, STAIR], 'plaster', B)
stair('b03_stair', IF, FFL, B)
box('b03_balcony', X1, ft(15), FF - SL, X1 + ft(4), ft(26, 6), FF, 'plaster', B, 0.006)
box('b03_porch', X1, Y0, FF - SL, PX - 0.3, ft(14), FF, 'plaster', B, 0.006)     # car-porch canopy (SE)
for nm, a, b2 in [('s1', ft(3.5), ft(9.5)), ('s3', ft(21.5), ft(26.5))]:
    box(f'b03_chajja_{nm}', a, Y0 - 0.45, PL + 2.25, b2, Y0, PL + 2.33, 'plaster', B, 0.004)

# ── b04 first floor: external walls, partitions, gallery round the void, floor finish ──
wall('b04_s', 'x', X0, X1, Y0, Y0 + T, fz0, fz1, [(ft(4), ft(10), FF + 0.75, FF + 2.2), (ft(14), ft(16, 6), FF + 0.3, fz1 - 0.2), (ft(22), ft(26), FF + 0.75, FF + 2.2)], 'brick', B)
wall('b04_e', 'y', Y0, Y1, X1 - T, X1, fz0, fz1, [(ft(4), ft(11), FF + 0.75, FF + 2.2), (ft(15, 6), ft(26), FF, FF + 2.4)], 'brick', B)
wall('b04_n', 'x', X0, X1, Y1 - T, Y1, fz0, fz1, [(ft(13), ft(22), FF, fz1 - 0.1), (ft(4), ft(6), FF + 1.7, FF + 2.2)], 'brick', B)
wall('b04_w', 'y', Y0, Y1, X0, X0 + T, fz0, fz1, [(ft(6), ft(10), FF + 0.75, FF + 2.2), (ft(16), ft(18), FF + 1.7, FF + 2.2)], 'brick', B)
box('b04_band', X0 - 0.06, Y0 - 0.06, FF - SL - 0.05, X1 + 0.06, Y0 + 0.01, FF + 0.05, 'plaster', B, 0.004)
wall('b04_p_mbr_e', 'y', YR1, YR11, XA1, XA1 + PT, FFL, fz1, [], 'interior_wall', B)                                  # master | stair
wall('b04_p_mbr_n', 'x', XA, XA1, YR11, YR11 + PT, FFL, fz1, [(ft(4, 6), ft(7), FFL, FFL + D), (ft(9, 9), ft(12, 6), FFL, FFL + D)], 'interior_wall', B)  # master | attached toilet, gallery
wall('b04_p_toilet_e', 'y', YR2, YR31, XU, XU + PT, FFL, fz1, [(ft(21, 9), ft(24, 3), FFL, FFL + D)], 'interior_wall', B)  # toilets | gallery
wall('b04_p_toilet_s', 'x', XA, XU, YR21, YR21 + PT, FFL, fz1, [], 'interior_wall', B)                               # attached | common toilet
wall('b04_p_lng_w', 'y', YR1, YK, XB1, XB1 + PT, FFL, fz1, [], 'interior_wall', B)                                   # stair | family lounge
wall('b04_p_lng_n', 'x', XC, XC1, YK, YK + PT, FFL, fz1, [(ft(22, 3), ft(25, 3), FFL, FFL + D)], 'interior_wall', B)  # lounge | sit-out
slab_holes('b04_floor', X0 + T, Y0 + T, X1 - T, Y1 - T, FF, FFL, [VOID, STAIR], 'kota', B)
balustrade('b04_bal_void_s', VOID[0], VOID[1], VOID[2], VOID[1], FFL, B)
balustrade('b04_bal_void_w', VOID[0], VOID[1], VOID[0], VOID[3], FFL, B)
balustrade('b04_bal_void_e', VOID[2], VOID[1], VOID[2], VOID[3], FFL, B)

# ── b05 roof slab (skylight + stair openings), stair FF→terrace ──
MX0, MX1, MY0, MY1 = XA1, XB1 + PT, Y0, YK + PT     # mumty walls stand on the stair-box walls below
slab_holes('b05_roof', X0 - 0.3, Y0 - 0.3, X1 + 0.3, Y1 + 0.3, RF - SL, RF, [SKY, (XB, YR1, XB1, YK)], 'plaster', B)
stair('b05_stair', FFL, RF, B)
box('b05_roof_bal', X1 + 0.3, ft(15) - 0.3, RF - SL, X1 + ft(4) + 0.3, ft(26, 6) + 0.3, RF, 'plaster', B, 0.006)

# ── b06 parapet, mumty over the stair, tank stand ──
pz = RF + 0.95
box('b06_par_s', X0 - 0.3, Y0 - 0.3, RF, X1 + 0.3, Y0 - 0.18, pz, 'brick', B)
box('b06_par_n', X0 - 0.3, Y1 + 0.18, RF, X1 + 0.3, Y1 + 0.3, pz, 'brick', B)
box('b06_par_w', X0 - 0.3, Y0 - 0.3, RF, X0 - 0.18, Y1 + 0.3, pz, 'brick', B)
box('b06_par_e', X1 + 0.18, Y0 - 0.3, RF, X1 + 0.3, Y1 + 0.3, pz, 'brick', B)
for nm, (a0, b0, a1, b1) in {'s': (X0 - 0.32, Y0 - 0.32, X1 + 0.32, Y0 - 0.16), 'n': (X0 - 0.32, Y1 + 0.16, X1 + 0.32, Y1 + 0.32),
                             'w': (X0 - 0.32, Y0 - 0.32, X0 - 0.16, Y1 + 0.32), 'e': (X1 + 0.16, Y0 - 0.32, X1 + 0.32, Y1 + 0.32)}.items():
    box(f'b06_coping_{nm}', a0, b0, pz, a1, b1, pz + 0.06, 'plaster', B, 0.003)
box('b06_mumty_w', MX0, MY0, RF, MX0 + PT, MY1, RF + 2.55, 'brick', B)
box('b06_mumty_e', MX1 - PT, MY0, RF, MX1, MY1, RF + 2.55, 'brick', B)
box('b06_mumty_s', MX0, MY0, RF, MX1, MY0 + T, RF + 2.55, 'brick', B)
wall('b06_mumty_n', 'x', MX0, MX1, MY1 - PT, MY1, RF, RF + 2.55, [(XB + 0.05, (XB + XB1) / 2 - 0.05, RF, RF + 2.1)], 'brick', B)   # door where flight 2 arrives
box('b06_mumty_roof', MX0 - 0.3, MY0 - 0.3, RF + 2.55, MX1 + 0.3, MY1 + 0.3, RF + 2.7, 'plaster', B, 0.005)
box('b06_tank_stand', ft(3), ft(3), RF, ft(8), ft(8), RF + 1.0, 'concrete', B, 0.005)
cyl('b06_tank', ft(5, 6), ft(5, 6), RF + 1.0, RF + 2.25, 0.58, 'tank', B, 24)

# ── b07 full-height brick jali on the east balcony ──
jali('b07_jali', 'y', ft(15), ft(26, 6), X1 + ft(4) - 0.115, X1 + ft(4), FF, RF - SL, B)
box('b07_jali_cap', X1 + ft(4) - 0.13, ft(15), RF - SL - 0.04, X1 + ft(4) + 0.01, ft(26, 6), RF - SL, 'plaster', B, 0)
# 4½″ brick return walls close both ends of the balcony, slab to slab, so the sit-out is screened on three sides
box('b07_ret_n', X1, ft(26, 6) - PT, FF, X1 + ft(4) - 0.115, ft(26, 6), RF - SL, 'brick', B, 0)
box('b07_ret_s', X1, ft(15), FF, X1 + ft(4) - 0.115, ft(15) + PT, RF - SL, 'brick', B, 0)

# ── b08 glazing + doors (every external opening above has its window or door) ──
window('b08_gs_bed', 'x', ft(4), ft(9), Y0 + T * 0.5, PL + 0.8, PL + 2.2, B, mullions=1)
window('b08_gs_stair', 'x', ft(14), ft(16, 6), Y0 + T * 0.5, PL + 0.6, gz1 - 0.2, B, mullions=0)
window('b08_gs_kit', 'x', ft(22), ft(26), Y0 + T * 0.5, PL + 1.0, PL + 2.2, B, mullions=1)
window('b08_ge_kit', 'y', ft(5), ft(10), X1 - T * 0.5, PL + 1.0, PL + 2.2, B, mullions=1)
window('b08_ge_pooja', 'y', ft(23, 6), ft(25, 6), X1 - T * 0.5, PL + 0.9, PL + 1.9, B, mullions=0)
window('b08_gn_liv', 'x', ft(13), ft(22), Y1 - T * 0.5, PL + 0.45, gz1 - 0.05, B, mullions=3)
window('b08_gn_toilet', 'x', ft(4), ft(6), Y1 - T * 0.5, PL + 1.8, PL + 2.3, B, mullions=0, glass='glass_dark')
window('b08_gw_bed', 'y', ft(7), ft(11), X0 + T * 0.5, PL + 0.8, PL + 2.2, B, mullions=1)
window('b08_gw_util', 'y', ft(16), ft(18, 6), X0 + T * 0.5, PL + 1.5, PL + 2.2, B, mullions=0, glass='glass_dark')
window('b08_fs_m', 'x', ft(4), ft(10), Y0 + T * 0.5, FF + 0.75, FF + 2.2, B, mullions=2)
window('b08_fs_stair', 'x', ft(14), ft(16, 6), Y0 + T * 0.5, FF + 0.3, fz1 - 0.2, B, mullions=0)
window('b08_fs_l', 'x', ft(22), ft(26), Y0 + T * 0.5, FF + 0.75, FF + 2.2, B, mullions=1)
window('b08_fe_l', 'y', ft(4), ft(11), X1 - T * 0.5, FF + 0.75, FF + 2.2, B, mullions=2)
window('b08_fe_sit', 'y', ft(15, 6), ft(26), X1 - T * 0.5, FF, FF + 2.4, B, mullions=3)
window('b08_fn_void', 'x', ft(13), ft(22), Y1 - T * 0.5, FF, fz1 - 0.1, B, mullions=3)
window('b08_fn_toilet', 'x', ft(4), ft(6), Y1 - T * 0.5, FF + 1.7, FF + 2.2, B, mullions=0, glass='glass_dark')
window('b08_fw_m', 'y', ft(6), ft(10), X0 + T * 0.5, FF + 0.75, FF + 2.2, B, mullions=1)
window('b08_fw_toilet', 'y', ft(16), ft(18), X0 + T * 0.5, FF + 1.7, FF + 2.2, B, mullions=0, glass='glass_dark')
for k, (a0, b0, a1, b1) in enumerate([(SKY[0] - 0.1, SKY[1] - 0.1, SKY[2] + 0.1, SKY[1]), (SKY[0] - 0.1, SKY[3], SKY[2] + 0.1, SKY[3] + 0.1),
                                      (SKY[0] - 0.1, SKY[1], SKY[0], SKY[3]), (SKY[2], SKY[1], SKY[2] + 0.1, SKY[3])]):
    box(f'b08_sky_up{k}', a0, b0, RF, a1, b1, RF + 0.3, 'plaster', B, 0.004)
box('b08_skylight', SKY[0], SKY[1], RF + 0.28, SKY[2], SKY[3], RF + 0.3, 'glass', B, 0)
# panelled teak main door, 4'0" double leaf in the foyer (north half of the east wall)
DY0, DY1 = ft(15, 6), ft(19, 6); dx = X1 - T * 0.5 - 0.02
box('b08_door_fr', dx, DY0 - 0.08, PL, dx + 0.04, DY1 + 0.08, PL + 2.33, 'teak', B, 0.004)
for lf, (a, b) in enumerate([(DY0, (DY0 + DY1) / 2), ((DY0 + DY1) / 2, DY1)]):
    box(f'b08_door_lf{lf}', dx + 0.04, a + 0.01, PL + 0.01, dx + 0.08, b - 0.01, PL + 2.24, 'walnut', B, 0.004)
    for k in range(3):
        z0 = PL + 0.12 + k * 0.72
        box(f'b08_door_pn{lf}{k}', dx + 0.08, a + 0.1, z0, dx + 0.095, b - 0.1, z0 + 0.6, 'teak', B, 0.006)
    cyl(f'b08_door_hd{lf}', dx + 0.11, (b - 0.06) if lf == 0 else (a + 0.06), PL + 0.95, PL + 1.25, 0.012, 'brass', B, 12)
# sliding gate: black MS frame with horizontal teak slats and gaps
g0, g1 = Y0 + 0.2, ft(14)
for nm, (a0, a1, z0, z1) in {'l': (g0, g0 + 0.05, 0.05, 1.5), 'r': (g1 - 0.05, g1, 0.05, 1.5), 'b': (g0, g1, 0.05, 0.11), 't': (g0, g1, 1.45, 1.5)}.items():
    box(f'b08_gate_f{nm}', PX - 0.11, a0, z0, PX - 0.05, a1, z1, 'metal_dark', B, 0.002)
for k in range(11):
    z = 0.14 + k * 0.118
    box(f'b08_gate_s{k}', PX - 0.1, g0 + 0.05, z, PX - 0.06, g1 - 0.05, z + 0.092, 'teak', B, 0.003)
for k in range(3):
    cyl(f'b08_gate_w{k}', PX - 0.08, g0 + 0.35 + k * 1.3, 0.0, 0.05, 0.04, 'metal_dark', B, 10)
kit.area_light('b08_in_light', ft(17), ft(17), RF - SL - 0.2, 3, 3, 90, coll=FX)
kit.area_light('b08_in_light2', ft(8), ft(8), FF - SL - 0.2, 2.5, 2.5, 40, coll=FX)

# ── b09 terrace: solar array (north-west, clear of the skylight), planters ──
for r in range(2):
    for c in range(3):
        x0 = 0.8 + c * 1.05; y0 = ft(15) + r * 1.9
        sp = box(f'b09_solar_{r}{c}', x0, y0, 0, x0 + 1.0, y0 + 1.7, 0.04, 'solar', B, 0)
        sp.rotation_euler = (math.radians(-13), 0, 0); sp.location = (0, 0, RF + 0.9)
        cyl(f'b09_solar_leg{r}{c}a', x0 + 0.1, y0 + 0.2, RF, RF + 0.95, 0.025, 'metal_dark', B, 6)
        cyl(f'b09_solar_leg{r}{c}b', x0 + 0.9, y0 + 1.5, RF, RF + 1.3, 0.025, 'metal_dark', B, 6)
for i in range(4):
    y = ft(2) + 0.4 + i * 1.9
    box(f'b09_planter{i}', X1 - 0.8, y, RF, X1 - 0.15, y + 1.2, RF + 0.55, 'concrete', B, 0.01)
    shrub(f'b09_plant{i}', X1 - 0.48, y + 0.6, RF + 0.55, 0.45, 0.6, seed=900 + i, coll=V, n=160)

# ── b10 landscape: compound wall, entry path to the door, NE garden, parking SE ──
cw = 1.35
box('b10_cw_s', 0, 0, 0, PX, 0.15, cw, 'plaster_warm', B, 0.004)
box('b10_cw_n', 0, PY - 0.15, 0, PX, PY, cw, 'plaster_warm', B, 0.004)
box('b10_cw_w', 0, 0, 0, 0.15, PY, cw, 'plaster_warm', B, 0.004)
box('b10_cw_e1', PX - 0.15, ft(14), 0, PX, ft(15), cw, 'plaster_warm', B, 0.004)
box('b10_cw_e2', PX - 0.15, ft(21), 0, PX, PY, cw, 'plaster_warm', B, 0.004)
box('b10_cw_cap', PX - 0.18, ft(21), cw, PX + 0.03, PY, cw + 0.06, 'brick', B, 0)
box('b10_path', X1 + 0.9, ft(15, 6), 0.02, PX - 0.15, ft(19, 6), 0.05, 'stone_pave', B, 0.003)
box('b10_lawn_ne', X1 + 0.2, ft(20) + 0.1, 0.02, PX - 0.2, PY - 0.2, 0.05, 'lawn', B, 0)
for i, (x, y) in enumerate([(X1 + 2.2, ft(25)), (X1 + 2.9, ft(22, 6)), (X1 + 1.6, ft(27, 6))]):
    shrub(f'b10_shrub{i}', x, y, 0.05, 0.5, 0.6, seed=950 + i, coll=V, n=220)
box('b10_tulsi', X1 + 1.2, ft(23), 0.02, X1 + 1.7, ft(24, 6), 0.75, 'brick', B, 0.01)
shrub('b10_tulsi_plant', X1 + 1.45, ft(23, 9), 0.75, 0.28, 0.4, seed=990, coll=V, n=120)
car('b10_car', X1 + 1.55, ft(7), 0.02, 0.0, B)
hedge('b10_hedge_w', 0.4, 0.4, 0.4, PY - 0.4, 0.0, 1.1, V, 3, 120)

# ── interior: double-height living, pooja door, furniture (names int_h_* → interior lightmap) ──
if FILM:
    # pooja door: teak frame, brass bell strip, warm glow inside
    PD0, PD1 = ft(21, 9), ft(24, 3)
    I.hard('int_h_pd_l', XF - 0.04, PD0 - 0.1, IF, XF + PT + 0.02, PD0, IF + 2.2, 'teak', B, 0.004)
    I.hard('int_h_pd_r', XF - 0.04, PD1, IF, XF + PT + 0.02, PD1 + 0.1, IF + 2.2, 'teak', B, 0.004)
    I.hard('int_h_pd_t', XF - 0.04, PD0 - 0.1, IF + 2.1, XF + PT + 0.02, PD1 + 0.1, IF + 2.3, 'teak', B, 0.004)
    for k in range(9):
        yy = PD0 + 0.05 + k * (PD1 - PD0 - 0.1) / 8
        kit.cyl(f'int_h_bell{k}', XF - 0.02, yy, IF + 1.95, IF + 2.1, 0.012, 'brass', B, 8)
        I.cone(f'int_h_bellc{k}', XF - 0.02, yy, IF + 1.9, IF + 1.96, 0.025, 0.008, 'brass', B, 12)
    box('int_h_pooja_glow', X1 - T - 0.03, YR3 + PT + 0.05, IF + 0.4, X1 - T - 0.01, ft(23, 3), IF + 2.2, 'lamp_soft', FX, 0)
    I.hard('int_h_pooja_shelf', ft(26), ft(21, 6), IF, X1 - T - 0.05, ft(25, 6), IF + 0.75, 'teak', B, 0.006)
    I.samai('int_h_samai_l', ft(23, 3), ft(21, 3), IF, B, h=0.95)
    I.urli('int_h_urli', ft(22), ft(22, 9), IF, B, r=0.34)
    # living: sofa on the west partition, swing in the void, armchair by the foyer
    I.rug('int_h_rug', ft(10, 6), ft(16), ft(20, 6), ft(23, 6), IF, B, 'rug_dhurrie', 'linen_oat')
    with I.Place(0, 0, IF, 0):
        I.sofa('int_h_sofa', XU + PT + 1.02, ft(20, 3), 90, B, w=2.35, d=0.98, fab='linen_oat', accents=('fabric_rust', 'fabric_indigo'))
        I.coffee_table('int_h_ct', ft(13, 3), ft(20, 3), 90, B, w=1.2, d=0.65, top='marble')
        I.side_table('int_h_st', ft(9, 3), ft(24), B, r=0.22, h=0.5)
        I.table_lamp('int_h_tl', ft(9, 3), ft(24), 0.5, FX, h=0.52)
        I.floor_lamp('int_h_fl', ft(9, 3), ft(16, 3), FX, h=1.55)
        I.plant('int_h_plant', ft(22, 6), ft(25, 3), 0, B, pot_r=0.28, pot_h=0.5, h=2.3, crown=0.7, pot='terracotta', seed=61)
        I.plant('int_h_plant2', ft(13, 9), ft(25, 6), 0, B, pot_r=0.2, pot_h=0.38, h=0.9, crown=0.4, pot='ceramic_white', seed=62, kind='leafy')
        I.dining_table('int_h_dn', ft(17, 3), ft(17, 6), 0, B, w=1.6, d=0.85, chairs=4)
        # kitchen: L-counter on the east and south walls (platform 2'-10" high, 2' deep)
        I.hard('int_h_kc_e', XC1 - ft(2), YR1, 0, XC1, YK - 0.3, ft(2, 10), 'walnut', B, 0.004)
        I.hard('int_h_kc_s', XC, YR1, 0, XC1 - ft(2), YR1 + ft(2), ft(2, 10), 'walnut', B, 0.004)
        I.hard('int_h_kc_top', XC, YR1, ft(2, 10), XC1, YR1 + ft(2), ft(2, 10) + 0.03, 'stone_dark', B, 0.003)
        I.hard('int_h_kc_top2', XC1 - ft(2), YR1 + ft(2), ft(2, 10), XC1, YK - 0.3, ft(2, 10) + 0.03, 'stone_dark', B, 0.003)
        # bedrooms: beds against the solid walls
        I.bed('int_h_bed_gf', XA1 - 2.2, 2.4, -90, B, w=1.6, l=2.0, head='teak', throw='fabric_mustard', hw=2.9)
    with I.Place(0, 0, FFL, 0):
        I.bed('int_h_bed_ff', XA1 - 2.2, 2.4, -90, B, w=1.6, l=2.0, head='walnut', throw='fabric_rust', hw=2.9)
        I.sofa('int_h_lounge_sofa', (XC + XC1) / 2, YR1 + 0.95, 180, B, w=2.0, d=0.9, fab='linen_white', accents=('fabric_indigo', 'fabric_mustard'), seats=2)
    I.swing('int_h_swing', ft(17, 6), ft(25, 2), IF + 0.5, RF - SL, 0, B)
    I.pendant('int_h_lantern', ft(17, 6), ft(22, 6), RF + 0.28, FF + 0.5, FX, r=0.25, style='lantern')
    I.art('int_h_art', 'y', ft(18), ft(22, 6), XU + PT, IF + 1.25, IF + 2.35, B, mat='art_earth', inward=1)
    I.curtain('int_h_cur_w', 'x', ft(13), ft(14, 3), Y1 - T - 0.12, IF, RF - SL - 0.1, B, folds=5, amp=0.04)
    I.curtain('int_h_cur_e', 'x', ft(20, 9), ft(22), Y1 - T - 0.12, IF, RF - SL - 0.1, B, folds=5, amp=0.04)
    kit.area_light('int_h_fill', ft(15), ft(18, 6), FF - SL - 0.05, 2.4, 1.6, 45, coll=FX)
    kit.area_light('int_h_fill2', ft(17, 6), ft(23, 6), RF - SL - 0.25, 2.2, 1.6, 40, coll=FX)

# light — morning sun on the east (road) facade
kit.sky(sun_elev=27.0, sun_az=112, strength=0.2, sun_strength=4.2, sun_angle=0.9)

kit.level_camera(kit.camera('CAM_street', (PX + 8.4, ft(6), 1.6), (X1, ft(17), 3.6), lens=22, shift_y=0.2), (X1, ft(17), 1.6))
kit.camera('CAM_aerial', (PX + 10, PY + 8, 12.5), (ft(18), ft(13), 3.0), lens=26)
kit.camera('CAM_jali', (PX - 0.4, ft(10), FF + 1.4), (X1 + ft(4), ft(22), FF + 1.6), lens=24)
bpy.ops.wm.save_as_mainfile(filepath=f'/home/claude/jv5/blender/home_morning{"_film" if FILM else ""}.blend')
print('SAVED home', len(bpy.data.objects))
