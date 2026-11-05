"""Interior set-dressing kit for the film shots: soft furniture, beds, lamps, plants, shelves,
art, swing, curtains. Everything is built from primitives in local coordinates and placed with
Place(x, y, z, rot). Object names start with 'int_' so the film bake gives interiors their own
lightmap atlas. Materials are bake-friendly (no metallic: the lightmap bake is diffuse only)."""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
import kit
from kit import box, cyl

# ───────────────────────── materials ─────────────────────────
def _simple(name, col, rough=0.8, sheen=0.0):
    m, nt, b = kit._new(name)
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    if sheen: b.inputs['Sheen Weight'].default_value = sheen
    kit._M[name] = m
    return m, nt, b

def _textured(name, stops, scale=4.0, detail=6.0, rough=0.8, wave=None, bump=0.0, stretch=None):
    m, nt, b = kit._new(name)
    L = nt.links
    if wave:
        w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = wave
        w.inputs['Scale'].default_value = scale; w.inputs['Distortion'].default_value = 1.5
        w.inputs['Detail'].default_value = detail
        L.new(kit._worldpos(nt), w.inputs['Vector'])
        fac = w.outputs['Fac']
    else:
        vec = kit._worldpos(nt)
        if stretch:
            mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch
            L.new(vec, mp.inputs['Vector']); vec = mp.outputs['Vector']
        fac = kit._noise(nt, vec=vec, scale=scale, detail=detail).outputs['Fac']
    L.new(kit._ramp(nt, fac, stops), b.inputs['Base Color'])
    if bump:
        n2 = kit._noise(nt, scale=scale * 20, detail=3)
        L.new(kit._bump(nt, n2.outputs['Fac'], bump, 0.005), b.inputs['Normal'])
    b.inputs['Roughness'].default_value = rough
    kit._M[name] = m
    return m

def materials():
    if 'linen_white' in kit._M: return
    _simple('linen_white', (0.80, 0.78, 0.73), 0.85, 0.5)
    _simple('linen_oat', (0.66, 0.60, 0.50), 0.88, 0.5)
    _simple('fabric_charcoal', (0.075, 0.072, 0.07), 0.9, 0.4)
    _simple('fabric_rust', (0.42, 0.15, 0.07), 0.9, 0.4)
    _simple('fabric_olive', (0.20, 0.21, 0.11), 0.9, 0.4)
    _simple('fabric_indigo', (0.05, 0.08, 0.17), 0.9, 0.4)
    _simple('fabric_mustard', (0.55, 0.37, 0.08), 0.9, 0.4)
    _simple('brass', (0.56, 0.38, 0.14), 0.35)
    _simple('ceramic_white', (0.82, 0.80, 0.75), 0.3)
    _simple('ceramic_black', (0.035, 0.033, 0.03), 0.35)
    _simple('terracotta', (0.46, 0.21, 0.11), 0.85)
    _simple('soil', (0.06, 0.04, 0.03), 1.0)
    _simple('shade_paper', (0.85, 0.80, 0.70), 0.9)
    _simple('mattress', (0.84, 0.82, 0.78), 0.8)
    _textured('walnut', [(0.3, (0.10, 0.055, 0.03)), (0.7, (0.16, 0.09, 0.05))], scale=3.0, stretch=(1, 1, 12), rough=0.5)
    _textured('marble', [(0.46, (0.86, 0.85, 0.82)), (0.5, (0.62, 0.61, 0.60)), (0.54, (0.86, 0.85, 0.82))], scale=2.2, detail=8, rough=0.2)
    _textured('rug_wool', [(0.3, (0.62, 0.55, 0.44)), (0.5, (0.70, 0.63, 0.52)), (0.7, (0.58, 0.50, 0.39))], scale=6, wave='X', detail=2, rough=1.0, bump=0.3)
    _textured('rug_dhurrie', [(0.2, (0.42, 0.18, 0.09)), (0.45, (0.70, 0.60, 0.46)), (0.7, (0.13, 0.13, 0.18)), (0.9, (0.70, 0.60, 0.46))], scale=5, wave='Y', detail=1, rough=1.0, bump=0.3)
    _textured('cane', [(0.4, (0.52, 0.38, 0.20)), (0.6, (0.66, 0.50, 0.29))], scale=80, detail=2, rough=0.7)
    _textured('art_earth', [(0.25, (0.62, 0.42, 0.26)), (0.45, (0.80, 0.70, 0.55)), (0.62, (0.36, 0.17, 0.09)), (0.8, (0.85, 0.80, 0.70))], scale=1.6, detail=3, rough=0.9)
    _textured('art_indigo', [(0.3, (0.07, 0.10, 0.20)), (0.5, (0.78, 0.74, 0.66)), (0.7, (0.18, 0.24, 0.36))], scale=1.2, detail=2, rough=0.9)
    _textured('art_ochre', [(0.35, (0.68, 0.46, 0.14)), (0.55, (0.88, 0.82, 0.70)), (0.75, (0.52, 0.30, 0.10))], scale=0.9, detail=4, rough=0.9)
    for i, c in enumerate([(0.42, 0.15, 0.07), (0.70, 0.64, 0.52), (0.10, 0.14, 0.22), (0.24, 0.26, 0.15), (0.55, 0.40, 0.12), (0.80, 0.77, 0.70), (0.05, 0.05, 0.05)]):
        _simple(f'book_{i}', c, 0.7)

# ───────────────────────── placement ─────────────────────────
class Place:
    """Build in local coords; on exit move every new top-level object by T(x,y,z)·Rz(rot)."""
    def __init__(self, x=0.0, y=0.0, z=0.0, rot=0.0):
        self.M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rot), 4, 'Z')
    def __enter__(self):
        self.before = set(bpy.data.objects); return self
    def __exit__(self, *a):
        for o in bpy.data.objects:
            if o not in self.before and o.parent is None:
                o.matrix_basis = self.M @ o.matrix_basis

def tilt(o, rx=0.0, ry=0.0, rz=0.0):
    """Rotate an object about its own bounding-box centre (degrees)."""
    vs = o.data.vertices
    c = Vector((sum(v.co.x for v in vs), sum(v.co.y for v in vs), sum(v.co.z for v in vs))) / len(vs)
    for v in vs: v.co -= c
    o.location = c
    o.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    return o

def soft(name, x0, y0, z0, x1, y1, z1, material, coll, r=0.04, levels=2):
    """Upholstered / pillowy box: bevel then subdivision."""
    o = box(name, x0, y0, z0, x1, y1, z1, material, coll, 0)
    md = o.modifiers.new('bev', 'BEVEL'); md.width = min(r, 0.45 * min(x1 - x0, y1 - y0, z1 - z0)); md.segments = 1
    sd = o.modifiers.new('sub', 'SUBSURF'); sd.levels = levels; sd.render_levels = levels
    for p in o.data.polygons: p.use_smooth = True
    return o

def hard(name, x0, y0, z0, x1, y1, z1, material, coll, r=0.006):
    o = box(name, x0, y0, z0, x1, y1, z1, material, coll, 0)
    if r > 0 and min(x1 - x0, y1 - y0, z1 - z0) > 2.5 * r:
        md = o.modifiers.new('bev', 'BEVEL'); md.width = r; md.segments = 2
    return o

def cone(name, x, y, z0, z1, r0, r1, material, coll, seg=32, caps=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=seg, radius1=r0, radius2=r1, depth=z1 - z0)
    for v in bm.verts: v.co += Vector((x, y, (z0 + z1) / 2))
    o = kit._finish(bm, name, material, coll)
    for p in o.data.polygons: p.use_smooth = True
    return o

def ccyl(name, x, y, z0, z1, r, material, coll, seg=32):
    o = cyl(name, x, y, z0, z1, r, material, coll, seg)
    if z1 - z0 > 0.02 and r > 0.02:
        md = o.modifiers.new('bev', 'BEVEL'); md.width = min(0.006, r * 0.2); md.segments = 2; md.limit_method = 'ANGLE'
    return o

# ───────────────────────── furniture ─────────────────────────
def sofa(n, x, y, rot, coll, w=2.5, d=0.98, fab='linen_oat', accents=('fabric_rust', 'fabric_charcoal'), seats=3):
    """Low lounge sofa, back to +y. Origin = centre of the front edge line at floor."""
    with Place(x, y, 0, rot):
        hard(n + '_plinth', -w / 2 + 0.06, 0.06, 0.0, w / 2 - 0.06, d - 0.06, 0.09, 'walnut', coll, 0.004)
        soft(n + '_base', -w / 2, 0.0, 0.09, w / 2, d, 0.30, fab, coll, 0.03)
        soft(n + '_arm_l', -w / 2, 0.0, 0.30, -w / 2 + 0.2, d, 0.58, fab, coll, 0.05)
        soft(n + '_arm_r', w / 2 - 0.2, 0.0, 0.30, w / 2, d, 0.58, fab, coll, 0.05)
        soft(n + '_back', -w / 2 + 0.2, d - 0.2, 0.30, w / 2 - 0.2, d, 0.74, fab, coll, 0.05)
        sw = (w - 0.4) / seats
        for i in range(seats):
            a = -w / 2 + 0.2 + i * sw
            soft(f'{n}_seat{i}', a + 0.01, 0.02, 0.30, a + sw - 0.01, d - 0.2, 0.47, fab, coll, 0.06)
            bc = soft(f'{n}_bk{i}', a + 0.02, d - 0.42, 0.47, a + sw - 0.02, d - 0.22, 0.86, fab, coll, 0.07)
            tilt(bc, -9)
        for i, (px, mt) in enumerate([(-w / 2 + 0.42, accents[0]), (w / 2 - 0.42, accents[1]), (-w / 2 + 0.7, accents[1])][:3]):
            p = soft(f'{n}_pil{i}', px - 0.22, d - 0.52, 0.47, px + 0.22, d - 0.38, 0.90, mt, coll, 0.07)
            tilt(p, -14, 6 if i else -6)

def armchair(n, x, y, rot, coll, fab='linen_white', frame='teak'):
    with Place(x, y, 0, rot):
        for sx in (-0.34, 0.30):
            for sy in (0.04, 0.70):
                hard(f'{n}_leg{sx}{sy}', sx, sy, 0.0, sx + 0.04, sy + 0.04, 0.42, frame, coll, 0.004)
        hard(n + '_rail_l', -0.36, 0.0, 0.40, -0.30, 0.78, 0.60, frame, coll, 0.008)
        hard(n + '_rail_r', 0.30, 0.0, 0.40, 0.36, 0.78, 0.60, frame, coll, 0.008)
        soft(n + '_seat', -0.30, 0.02, 0.30, 0.30, 0.74, 0.44, fab, coll, 0.05)
        bk = soft(n + '_back', -0.30, 0.56, 0.42, 0.30, 0.72, 0.88, fab, coll, 0.06)
        tilt(bk, -12)

def coffee_table(n, x, y, rot, coll, w=1.3, d=0.75, h=0.36, top='marble', base='walnut'):
    with Place(x, y, 0, rot):
        hard(n + '_top', -w / 2, -d / 2, h - 0.04, w / 2, d / 2, h, top, coll, 0.008)
        hard(n + '_base', -w / 2 + 0.12, -d / 2 + 0.1, 0.0, w / 2 - 0.12, d / 2 - 0.1, h - 0.04, base, coll, 0.006)
        # styling: two books + a bowl
        hard(n + '_bk1', -0.38, -0.12, h, -0.08, 0.10, h + 0.035, 'book_1', coll, 0.002)
        hard(n + '_bk2', -0.36, -0.10, h + 0.035, -0.10, 0.08, h + 0.06, 'book_2', coll, 0.002)
        cone(n + '_bowl', 0.25, 0.02, h, h + 0.08, 0.06, 0.15, 'ceramic_black', coll, 32)

def side_table(n, x, y, coll, r=0.24, h=0.52, top='walnut'):
    ccyl(n + '_top', x, y, h - 0.03, h, r, top, coll, 40)
    cyl(n + '_stem', x, y, 0.02, h - 0.03, 0.035, 'black', coll, 12)
    ccyl(n + '_foot', x, y, 0.0, 0.02, r * 0.6, 'black', coll, 32)

def table_lamp(n, x, y, z, coll, h=0.55, shade_r=0.17):
    cone(n + '_base', x, y, z, z + h * 0.55, 0.07, 0.11, 'ceramic_white', coll, 32)
    cyl(n + '_neck', x, y, z + h * 0.55, z + h * 0.7, 0.012, 'brass', coll, 10)
    cone(n + '_shade', x, y, z + h * 0.62, z + h, shade_r * 1.1, shade_r * 0.85, 'shade_paper', coll, 40, caps=False)
    cone(n + '_glow', x, y, z + h * 0.64, z + h * 0.98, shade_r * 1.0, shade_r * 0.78, 'lamp_soft', coll, 40, caps=False)

def floor_lamp(n, x, y, coll, h=1.55, shade_r=0.24):
    ccyl(n + '_base', x, y, 0.0, 0.025, 0.16, 'black', coll, 32)
    cyl(n + '_pole', x, y, 0.025, h - 0.25, 0.012, 'brass', coll, 10)
    cone(n + '_shade', x, y, h - 0.32, h, shade_r, shade_r * 0.7, 'shade_paper', coll, 40, caps=False)
    cone(n + '_glow', x, y, h - 0.30, h - 0.02, shade_r * 0.92, shade_r * 0.64, 'lamp_soft', coll, 40, caps=False)

def pendant(n, x, y, z_ceil, z_bot, coll, r=0.22, style='dome'):
    cyl(n + '_wire', x, y, z_bot + 0.1, z_ceil, 0.004, 'black', coll, 6)
    if style == 'dome':
        cone(n + '_dome', x, y, z_bot + 0.02, z_bot + 0.2, r, r * 0.2, 'brass', coll, 40, caps=False)
        ccyl(n + '_disc', x, y, z_bot + 0.015, z_bot + 0.03, r * 0.92, 'lamp', coll, 40)
    else:   # paper lantern
        o = kit._finish(_sphere(x, y, z_bot + r, r), n + '_lantern', 'lamp_soft', coll)
        for p in o.data.polygons: p.use_smooth = True

def _sphere(x, y, z, r, seg=24):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    for v in bm.verts: v.co += Vector((x, y, z))
    return bm

def rug(n, x0, y0, x1, y1, z, coll, mat='rug_wool', border='linen_oat'):
    hard(n, x0, y0, z, x1, y1, z + 0.012, mat, coll, 0.003)
    b = 0.06
    for k, (a0, b0, a1, b1) in enumerate([(x0, y0, x1, y0 + b), (x0, y1 - b, x1, y1), (x0, y0 + b, x0 + b, y1 - b), (x1 - b, y0 + b, x1, y1 - b)]):
        box(f'{n}_b{k}', a0, b0, z + 0.0005, a1, b1, z + 0.0125, border, coll, 0)

def bed(n, x, y, rot, coll, w=1.9, l=2.1, head='teak', throw='fabric_rust', hw=None):
    """Platform bed, head at +y. Origin = centre of the foot edge at floor."""
    with Place(x, y, 0, rot):
        hard(n + '_plinth', -w / 2 + 0.1, 0.1, 0.0, w / 2 - 0.1, l - 0.05, 0.14, 'walnut', coll, 0.004)
        hard(n + '_frame', -w / 2 - 0.05, -0.05, 0.14, w / 2 + 0.05, l, 0.32, head, coll, 0.01)
        soft(n + '_mattress', -w / 2, 0.0, 0.32, w / 2, l - 0.02, 0.56, 'mattress', coll, 0.05)
        soft(n + '_duvet', -w / 2 - 0.04, -0.03, 0.50, w / 2 + 0.04, l - 0.55, 0.63, 'linen_white', coll, 0.05)
        soft(n + '_fold', -w / 2 - 0.03, l - 0.75, 0.55, w / 2 + 0.03, l - 0.52, 0.66, 'linen_white', coll, 0.06)
        soft(n + '_throw', -w / 2 - 0.05, 0.12, 0.58, w / 2 + 0.05, 0.62, 0.66, throw, coll, 0.03)
        for i, px in enumerate((-w / 4, w / 4)):
            p = soft(f'{n}_pil{i}', px - 0.36, l - 0.34, 0.54, px + 0.36, l - 0.14, 0.98, 'linen_white', coll, 0.09)
            tilt(p, -18)
            q = soft(f'{n}_cush{i}', px - 0.26, l - 0.52, 0.56, px + 0.26, l - 0.36, 0.88, 'linen_oat' if i else 'fabric_charcoal', coll, 0.07)
            tilt(q, -12)
        # upholstered + teak headboard wall
        soft(n + '_head', -w / 2 - 0.15, l, 0.30, w / 2 + 0.15, l + 0.12, 1.25, 'linen_oat', coll, 0.04)
        hw = hw or (w + 2.1)
        hard(n + '_headwall', -hw / 2, l + 0.12, 0.0, hw / 2, l + 0.16, 2.45, head, coll, 0.004)
        # bedside tables + lamps
        for s in (-1, 1):
            cx = s * (w / 2 + 0.42)
            hard(f'{n}_bst{s}', cx - 0.26, l - 0.42, 0.0, cx + 0.26, l + 0.1, 0.48, 'walnut', coll, 0.006)
            table_lamp(f'{n}_lamp{s}', cx + 0.05, l - 0.18, 0.48, coll, 0.5, 0.15)
        # bench at the foot
        hard(n + '_bench', -0.75, -0.62, 0.0, 0.75, -0.2, 0.42, 'cane', coll, 0.01)
        soft(n + '_benchpad', -0.73, -0.60, 0.42, 0.73, -0.22, 0.48, 'linen_oat', coll, 0.02)

def plant(n, x, y, z, coll, pot_r=0.22, pot_h=0.42, h=1.6, crown=0.55, pot='terracotta', seed=1, kind='tree'):
    cone(n + '_pot', x, y, z, z + pot_h, pot_r * 0.78, pot_r, pot, coll, 32)
    cyl(n + '_soil', x, y, z + pot_h - 0.05, z + pot_h - 0.02, pot_r * 0.94, 'soil', coll, 24)
    indoor_plant(n, x, y, z + pot_h - 0.03, coll, h, crown, seed, big=(kind == 'tree'))

def indoor_plant(n, x, y, z, coll, h=1.5, crown=0.5, seed=1, big=True):
    """Stems + oval leaves (fiddle-leaf / rubber-plant character)."""
    if kit._real_plants(): return kit._pp().indoor(n, x, y, z, coll, h, seed, big)
    rnd = random.Random(seed)
    bm = bmesh.new()
    lm = bmesh.new(); cl = kit._col_layer(lm)
    stems = rnd.randint(3, 5) if big else rnd.randint(6, 9)
    for s_ in range(stems):
        az = rnd.uniform(0, 6.283); lean = rnd.uniform(0.05, 0.35) * crown
        top = Vector((x + math.cos(az) * lean, y + math.sin(az) * lean, z + h * rnd.uniform(0.6, 1.0)))
        base = Vector((x + rnd.uniform(-0.03, 0.03), y + rnd.uniform(-0.03, 0.03), z))
        seg = 6
        axis = top - base; q = axis.to_track_quat('Z', 'Y')
        r0 = 0.012 if big else 0.006
        rings = [[bm.verts.new(p + q @ Vector((math.cos(2 * math.pi * k / seg) * r, math.sin(2 * math.pi * k / seg) * r, 0))) for k in range(seg)]
                 for p, r in ((base, r0), (top, r0 * 0.5))]
        for k in range(seg):
            bm.faces.new((rings[0][k], rings[0][(k + 1) % seg], rings[1][(k + 1) % seg], rings[1][k]))
        nl = rnd.randint(9, 15) if big else rnd.randint(5, 8)
        for j in range(nl):
            f = 0.3 + 0.7 * (j / max(1, nl - 1)) ** 0.8
            p = base + axis * f
            d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.1, 0.6))).normalized()
            L = (rnd.uniform(0.14, 0.22) if big else rnd.uniform(0.18, 0.3)) * (0.7 + 0.3 * f)
            W = L * (0.55 if big else 0.22)
            c = p + d * L * 0.55
            side = d.cross(Vector((0, 0, 1)))
            if side.length < 1e-3: side = Vector((1, 0, 0))
            side.normalize()
            up = side.cross(d).normalized()
            droop = Vector((0, 0, -L * 0.18))
            pts = [p, c - d * L * 0.25 + side * W * 0.5 + up * W * 0.08, c + side * W * 0.42 + droop * 0.6,
                   p + d * L + droop, c - side * W * 0.42 + droop * 0.6, c - d * L * 0.25 - side * W * 0.5 + up * W * 0.08]
            fc = lm.faces.new([lm.verts.new(v) for v in pts])
            sh = rnd.uniform(0.75, 1.15)
            for lp in fc.loops: lp[cl] = (sh, sh, sh * 0.9, 1)
    o = kit._finish(bm, n + '_stems', 'bark', coll)
    for p_ in o.data.polygons: p_.use_smooth = True
    kit._finish(lm, n + '_leaves', 'leaf', coll)

def bookshelf(n, axis, u0, u1, t_wall, z0, z1, coll, depth=0.34, cols=4, rows=5, seed=3, wood='teak', inward=1):
    """Open shelving against a wall. axis 'x': runs along x at y=t_wall, shelves extend to y + inward*depth."""
    rnd = random.Random(seed)
    def B(nm, a0, b0, c0, a1, b1, c1, m):
        t0, t1 = sorted((t_wall + inward * b0, t_wall + inward * b1))
        if axis == 'x':
            return hard(nm, a0, t0, c0, a1, t1, c1, m, coll, 0.003)
        return hard(nm, t0, a0, c0, t1, a1, c1, m, coll, 0.003)
    W = u1 - u0; cw = W / cols; rh = (z1 - z0) / rows
    for c in range(cols + 1):
        u = u0 + c * cw
        B(f'{n}_v{c}', u - 0.02, 0.0, z0, u + 0.02, depth, z1, wood)
    for r in range(rows + 1):
        z = z0 + r * rh
        B(f'{n}_h{r}', u0, 0.0, z - 0.02, u1, depth, z + 0.02, wood)
    k = 0
    for c in range(cols):
        for r in range(rows):
            zb = z0 + r * rh + 0.02
            a = u0 + c * cw + 0.04; e = u0 + (c + 1) * cw - 0.04
            mode = rnd.random()
            if mode < 0.62:   # run of books, sometimes leaning
                u = a + rnd.uniform(0, 0.12)
                stop = e - rnd.uniform(0.0, 0.25)
                while u < stop:
                    bw = rnd.uniform(0.025, 0.05); bh = rnd.uniform(0.6, 0.92) * (rh - 0.06)
                    B(f'{n}_b{k}', u, 0.04, zb, u + bw, depth - rnd.uniform(0.04, 0.1), zb + bh, f'book_{rnd.randrange(7)}')
                    u += bw + 0.003; k += 1
            elif mode < 0.82:  # vase
                uc = (a + e) / 2 + rnd.uniform(-0.1, 0.1)
                hh = rnd.uniform(0.18, 0.32) * (rh / 0.42)
                p = (uc, t_wall + inward * depth / 2) if axis == 'x' else (t_wall + inward * depth / 2, uc)
                cone(f'{n}_vase{k}', p[0], p[1], zb, zb + min(hh, rh - 0.06), rnd.uniform(0.05, 0.08), rnd.uniform(0.03, 0.06),
                     rnd.choice(['ceramic_white', 'ceramic_black', 'terracotta']), coll, 24); k += 1
            else:              # stacked books + object
                u = a + 0.05
                for s in range(rnd.randint(2, 4)):
                    B(f'{n}_s{k}', u, 0.05, zb + s * 0.035, u + rnd.uniform(0.18, 0.24), depth - 0.06, zb + (s + 1) * 0.035, f'book_{rnd.randrange(7)}'); k += 1

def art(n, axis, u0, u1, t, z0, z1, coll, mat='art_earth', inward=1, frame='walnut'):
    """Framed canvas on a wall plane at t (axis 'x' → wall runs along x at y=t)."""
    f = 0.025
    if axis == 'x':
        ya, yb = sorted((t, t + inward * 0.04))
        hard(n + '_frame', u0, ya, z0, u1, yb, z1, frame, coll, 0.003)
        ya2, yb2 = sorted((t + inward * 0.04, t + inward * 0.045))
        box(n + '_canvas', u0 + f, ya2, z0 + f, u1 - f, yb2, z1 - f, mat, coll, 0)
    else:
        xa, xb = sorted((t, t + inward * 0.04))
        hard(n + '_frame', xa, u0, z0, xb, u1, z1, frame, coll, 0.003)
        xa2, xb2 = sorted((t + inward * 0.04, t + inward * 0.045))
        box(n + '_canvas', xa2, u0 + f, z0 + f, xb2, u1 - f, z1 - f, mat, coll, 0)

def dining_chair(n, x, y, rot, coll, wood='teak', seat='cane'):
    with Place(x, y, 0, rot):
        for sx in (-0.21, 0.18):
            for sy in (-0.21, 0.18):
                hard(f'{n}_leg{sx}{sy}', sx, sy, 0.0, sx + 0.03, sy + 0.03, 0.45 if sy < 0 else 0.82, wood, coll, 0.003)
        hard(n + '_seat', -0.22, -0.22, 0.43, 0.22, 0.22, 0.47, seat, coll, 0.006)
        hard(n + '_back', -0.21, 0.17, 0.62, 0.21, 0.21, 0.80, wood, coll, 0.006)

def dining_table(n, x, y, rot, coll, w=2.1, d=0.95, top='walnut', chairs=6):
    with Place(x, y, 0, rot):
        hard(n + '_top', -w / 2, -d / 2, 0.72, w / 2, d / 2, 0.76, top, coll, 0.006)
        for s in (-1, 1):
            hard(f'{n}_leg{s}', s * (w / 2 - 0.3) - 0.04, -d / 2 + 0.12, 0.0, s * (w / 2 - 0.3) + 0.04, d / 2 - 0.12, 0.72, top, coll, 0.004)
        per = chairs // 2
        for i in range(per):
            cx = -w / 2 + (i + 0.5) * w / per
            dining_chair(f'{n}_ch_s{i}', cx, -d / 2 - 0.12, 180, coll)
            dining_chair(f'{n}_ch_n{i}', cx, d / 2 + 0.12, 0, coll)
        cone(n + '_vase', 0.0, 0.0, 0.76, 1.02, 0.07, 0.045, 'ceramic_white', coll, 32)
        kit.shrub(n + '_stems', 0.0, 0.0, 1.0, 0.18, 0.3, seed=77, coll=coll, n=60, material='leaf')
        cone(n + '_bowl', 0.55, 0.05, 0.76, 0.84, 0.07, 0.17, 'brass', coll, 32)

def swing(n, x, y, z_seat, z_top, rot, coll):
    """Traditional teak plank swing (uyyale) on four brass rods."""
    with Place(x, y, 0, rot):
        hard(n + '_plank', -0.75, -0.3, z_seat - 0.06, 0.75, 0.3, z_seat, 'teak', coll, 0.01)
        hard(n + '_rail', -0.75, 0.24, z_seat, 0.75, 0.3, z_seat + 0.12, 'teak', coll, 0.006)
        soft(n + '_cush', -0.70, -0.26, z_seat, 0.70, 0.22, z_seat + 0.07, 'fabric_indigo', coll, 0.03)
        p = soft(n + '_bol', -0.68, 0.06, z_seat + 0.07, -0.30, 0.22, z_seat + 0.24, 'fabric_mustard', coll, 0.06)
        for sx in (-0.7, 0.7):
            for sy in (-0.25, 0.25):
                cyl(f'{n}_rod{sx}{sy}', sx, sy, z_seat, z_top, 0.009, 'brass', coll, 8)
        hard(n + '_beam', -0.85, -0.32, z_top - 0.12, 0.85, 0.32, z_top, 'teak', coll, 0.006)

def urli(n, x, y, z, coll, r=0.36):
    cone(n + '_bowl', x, y, z, z + 0.14, r * 0.55, r, 'brass', coll, 48)
    ccyl(n + '_water', x, y, z + 0.09, z + 0.10, r * 0.9, 'water', coll, 48)
    rnd = random.Random(int(x * 100) % 997)
    for i in range(14):
        a = rnd.uniform(0, 6.283); rr = rnd.uniform(0, r * 0.75)
        o = kit._finish(_sphere(x + math.cos(a) * rr, y + math.sin(a) * rr, z + 0.105, 0.03, 10), f'{n}_petal{i}',
                        rnd.choice(['flower', 'fabric_mustard', 'fabric_rust']), coll)
        o.scale = (1, 1, 0.35)

def samai(n, x, y, z, coll, h=0.9):
    """Brass oil-lamp stand with a lit wick."""
    ccyl(n + '_foot', x, y, z, z + 0.04, 0.15, 'brass', coll, 40)
    cone(n + '_dome', x, y, z + 0.04, z + 0.14, 0.13, 0.04, 'brass', coll, 40)
    cyl(n + '_stem', x, y, z + 0.14, z + h - 0.06, 0.02, 'brass', coll, 16)
    for k in range(3):
        ccyl(f'{n}_ring{k}', x, y, z + 0.3 + k * 0.17, z + 0.33 + k * 0.17, 0.035, 'brass', coll, 24)
    cone(n + '_plate', x, y, z + h - 0.06, z + h, 0.06, 0.12, 'brass', coll, 40)
    for k in range(5):
        a = k * 6.283 / 5
        o = kit._finish(_sphere(x + math.cos(a) * 0.09, y + math.sin(a) * 0.09, z + h + 0.025, 0.014, 10), f'{n}_flame{k}', 'lamp_strong', coll)
        o.scale = (1, 1, 1.9)

def curtain(n, axis, u0, u1, t, z0, z1, coll, folds=10, amp=0.05, mat='linen_white'):
    """Gathered linen curtain panel (wavy surface), hung along a wall line."""
    bm = bmesh.new()
    nu, nz = folds * 6, 6
    rows = []
    for j in range(nz + 1):
        z = z0 + (z1 - z0) * j / nz
        row = []
        for i in range(nu + 1):
            u = u0 + (u1 - u0) * i / nu
            off = amp * math.sin(i / 6 * 2 * math.pi)
            row.append(bm.verts.new((u, t + off, z) if axis == 'x' else (t + off, u, z)))
        rows.append(row)
    for j in range(nz):
        for i in range(nu):
            bm.faces.new([rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]])
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.006)
    o = kit._finish(bm, n, mat, coll)
    for p in o.data.polygons: p.use_smooth = True
    return o

def slat_wall(n, axis, u0, u1, t, z0, z1, coll, pitch=0.09, w=0.045, d=0.04, inward=1, wood='teak'):
    """Vertical timber battens over a dark backing."""
    if axis == 'x':
        ya, yb = sorted((t, t + inward * 0.01))
        box(n + '_back', u0, ya, z0, u1, yb, z1, 'walnut', coll, 0)
        k = 0; u = u0 + 0.02
        while u + w < u1:
            y0, y1 = sorted((t + inward * 0.01, t + inward * (0.01 + d)))
            hard(f'{n}_s{k}', u, y0, z0, u + w, y1, z1, wood, coll, 0.004); u += pitch; k += 1
    else:
        xa, xb = sorted((t, t + inward * 0.01))
        box(n + '_back', xa, u0, z0, xb, u1, z1, 'walnut', coll, 0)
        k = 0; u = u0 + 0.02
        while u + w < u1:
            x0, x1 = sorted((t + inward * 0.01, t + inward * (0.01 + d)))
            hard(f'{n}_s{k}', x0, u, z0, x1, u + w, z1, wood, coll, 0.004); u += pitch; k += 1
