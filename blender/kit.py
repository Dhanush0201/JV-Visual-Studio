import os
"""JV Visual v5 — shared Blender kit (procedural archviz, real-world metres).
Follows blender-skills archviz / realistic-style / lighting / rendering guidance:
1 BU = 1 m, AgX view, PBR-plausible values, sky + sun, small bevels on visible edges.
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler

# ───────────────────────── scene ─────────────────────────
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.04
    cy.use_denoising = True
    cy.denoiser = 'OPENIMAGEDENOISE'
    cy.max_bounces = 8
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 3
    cy.transmission_bounces = 8
    cy.transparent_max_bounces = 8
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.sample_clamp_indirect = 6.0
    cy.use_light_tree = True
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    return sc

def collection(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c

def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj

# ───────────────────────── materials ─────────────────────────
_M = {}

def _new(name):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    return m, nt, bsdf

def _worldpos(nt):
    g = nt.nodes.new('ShaderNodeNewGeometry')
    return g.outputs['Position']

def _wall_uv(nt, sx=1.0, sy=1.0):
    """(x+y, z) mapping — bricks read horizontally on axis-aligned walls."""
    pos = _worldpos(nt)
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(pos, sep.inputs[0])
    add = nt.nodes.new('ShaderNodeMath'); add.operation = 'ADD'
    nt.links.new(sep.outputs[0], add.inputs[0]); nt.links.new(sep.outputs[1], add.inputs[1])
    comb = nt.nodes.new('ShaderNodeCombineXYZ')
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MULTIPLY'; mx.inputs[1].default_value = sx
    my = nt.nodes.new('ShaderNodeMath'); my.operation = 'MULTIPLY'; my.inputs[1].default_value = sy
    nt.links.new(add.outputs[0], mx.inputs[0]); nt.links.new(sep.outputs[2], my.inputs[0])
    nt.links.new(mx.outputs[0], comb.inputs[0]); nt.links.new(my.outputs[0], comb.inputs[1])
    return comb.outputs[0]

def _noise(nt, vec=None, scale=5.0, detail=6.0, rough=0.55):
    n = nt.nodes.new('ShaderNodeTexNoise')
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough
    if vec is not None: nt.links.new(vec, n.inputs['Vector'])
    else: nt.links.new(_worldpos(nt), n.inputs['Vector'])
    return n

def _ramp(nt, fac, stops):
    r = nt.nodes.new('ShaderNodeValToRGB')
    els = r.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    els[1].position, els[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        e = els.new(p); e.color = (*c, 1)
    nt.links.new(fac, r.inputs[0])
    return r.outputs[0]

def _bump(nt, height, strength=0.2, dist=0.02, normal=None):
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = strength
    b.inputs['Distance'].default_value = dist
    nt.links.new(height, b.inputs['Height'])
    if normal is not None: nt.links.new(normal, b.inputs['Normal'])
    return b.outputs[0]

def mat(name):
    if name in _M: return _M[name]
    m, nt, b = _new(name)
    L = nt.links
    def setp(**kw):
        for k, v in kw.items():
            b.inputs[k.replace('_', ' ')].default_value = v

    if name == 'plaster':          # warm off-white lime plaster
        n = _noise(nt, scale=3.0)
        L.new(_ramp(nt, n.outputs['Fac'], [(0.35, (0.70, 0.67, 0.61)), (0.65, (0.77, 0.74, 0.68))]), b.inputs['Base Color'])
        n2 = _noise(nt, scale=60, detail=4)
        L.new(_bump(nt, n2.outputs['Fac'], 0.08), b.inputs['Normal'])
        setp(Roughness=0.88)
    elif name == 'plaster_warm':   # ochre limewash
        n = _noise(nt, scale=2.5)
        L.new(_ramp(nt, n.outputs['Fac'], [(0.35, (0.74, 0.58, 0.40)), (0.7, (0.80, 0.65, 0.47))]), b.inputs['Base Color'])
        n2 = _noise(nt, scale=50, detail=4)
        L.new(_bump(nt, n2.outputs['Fac'], 0.1), b.inputs['Normal'])
        setp(Roughness=0.9)
    elif name == 'concrete':       # board-marked fair-face concrete
        n = _noise(nt, scale=1.5)
        L.new(_ramp(nt, n.outputs['Fac'], [(0.3, (0.42, 0.41, 0.39)), (0.7, (0.55, 0.54, 0.51))]), b.inputs['Base Color'])
        w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'Z'
        w.inputs['Scale'].default_value = 1.2; w.inputs['Distortion'].default_value = 0.5
        L.new(_worldpos(nt), w.inputs['Vector'])
        n2 = _noise(nt, scale=40)
        mixh = nt.nodes.new('ShaderNodeMath'); mixh.operation = 'ADD'
        L.new(w.outputs['Fac'], mixh.inputs[0]); L.new(n2.outputs['Fac'], mixh.inputs[1])
        L.new(_bump(nt, mixh.outputs[0], 0.06), b.inputs['Normal'])
        setp(Roughness=0.82)
    elif name == 'brick':          # exposed wire-cut fired clay, Malur type
        vec = _wall_uv(nt)
        br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0.5; br.offset_frequency = 2
        br.inputs['Scale'].default_value = 1.0
        br.inputs['Brick Width'].default_value = 0.235
        br.inputs['Row Height'].default_value = 0.085
        br.inputs['Mortar Size'].default_value = 0.011
        br.inputs['Mortar Smooth'].default_value = 0.1
        br.inputs['Bias'].default_value = 0.0
        L.new(vec, br.inputs['Vector'])
        br.inputs['Color1'].default_value = (0.47, 0.20, 0.11, 1)
        br.inputs['Color2'].default_value = (0.58, 0.28, 0.15, 1)
        br.inputs['Mortar'].default_value = (0.62, 0.58, 0.52, 1)
        n = _noise(nt, scale=25, detail=8)
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 0.35
        L.new(br.outputs['Color'], mix.inputs['A'])
        L.new(_ramp(nt, n.outputs['Fac'], [(0.3, (0.75, 0.72, 0.7)), (0.7, (1, 1, 1))]), mix.inputs['B'])
        L.new(mix.outputs['Result'], b.inputs['Base Color'])
        inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
        L.new(br.outputs['Factor'], inv.inputs[1])
        L.new(_bump(nt, inv.outputs[0], 0.5, 0.01), b.inputs['Normal'])
        setp(Roughness=0.86)
    elif name == 'stone_pave':     # Sadarahalli granite paving, honed
        pos = _worldpos(nt)
        br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0.0
        br.inputs['Brick Width'].default_value = 0.9; br.inputs['Row Height'].default_value = 0.6
        br.inputs['Mortar Size'].default_value = 0.004
        L.new(pos, br.inputs['Vector'])
        n = _noise(nt, scale=90, detail=3)
        c = _ramp(nt, n.outputs['Fac'], [(0.35, (0.50, 0.47, 0.44)), (0.5, (0.64, 0.61, 0.57)), (0.62, (0.42, 0.39, 0.37))])
        br.inputs['Mortar'].default_value = (0.35, 0.33, 0.31, 1)
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        L.new(br.outputs['Factor'], mix.inputs['Factor']); L.new(c, mix.inputs['A'])
        mix.inputs['B'].default_value = (0.33, 0.31, 0.29, 1)
        L.new(mix.outputs['Result'], b.inputs['Base Color'])
        setp(Roughness=0.55)
    elif name == 'stone_dark':     # black granite coping
        n = _noise(nt, scale=120, detail=2)
        L.new(_ramp(nt, n.outputs['Fac'], [(0.4, (0.04, 0.04, 0.045)), (0.6, (0.09, 0.09, 0.095))]), b.inputs['Base Color'])
        setp(Roughness=0.25)
    elif name == 'kota':           # Kota stone floor
        n = _noise(nt, scale=8)
        L.new(_ramp(nt, n.outputs['Fac'], [(0.3, (0.36, 0.38, 0.33)), (0.7, (0.46, 0.47, 0.41))]), b.inputs['Base Color'])
        setp(Roughness=0.35)
    elif name == 'teak':           # teak slats / soffit
        pos = _worldpos(nt)
        w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'X'
        w.inputs['Scale'].default_value = 3.0; w.inputs['Distortion'].default_value = 6.0
        w.inputs['Detail'].default_value = 3.0
        L.new(pos, w.inputs['Vector'])
        L.new(_ramp(nt, w.outputs['Fac'], [(0.2, (0.20, 0.09, 0.035)), (0.6, (0.33, 0.16, 0.07)), (0.9, (0.27, 0.12, 0.05))]), b.inputs['Base Color'])
        setp(Roughness=0.5)
    elif name == 'deck':           # weathered hardwood deck
        pos = _worldpos(nt)
        br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0.37
        br.inputs['Brick Width'].default_value = 1.8; br.inputs['Row Height'].default_value = 0.14
        br.inputs['Mortar Size'].default_value = 0.006
        br.inputs['Color1'].default_value = (0.30, 0.17, 0.09, 1)
        br.inputs['Color2'].default_value = (0.38, 0.23, 0.12, 1)
        br.inputs['Mortar'].default_value = (0.05, 0.03, 0.02, 1)
        L.new(pos, br.inputs['Vector'])
        L.new(br.outputs['Color'], b.inputs['Base Color'])
        setp(Roughness=0.6)
    elif name == 'water':          # pool water
        setp(Base_Color=(0.72, 0.93, 0.95, 1), Roughness=0.015, IOR=1.333)
        b.inputs['Transmission Weight'].default_value = 1.0
        n = _noise(nt, scale=2.2, detail=3, rough=0.5)
        L.new(_bump(nt, n.outputs['Fac'], 0.12, 0.05), b.inputs['Normal'])
    elif name == 'pool_tile':      # aqua glass mosaic
        pos = _worldpos(nt)
        br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0.0
        br.inputs['Brick Width'].default_value = 0.05; br.inputs['Row Height'].default_value = 0.05
        br.inputs['Mortar Size'].default_value = 0.003
        br.inputs['Color1'].default_value = (0.30, 0.66, 0.70, 1)
        br.inputs['Color2'].default_value = (0.38, 0.74, 0.76, 1)
        br.inputs['Mortar'].default_value = (0.85, 0.88, 0.88, 1)
        L.new(pos, br.inputs['Vector'])
        L.new(br.outputs['Color'], b.inputs['Base Color'])
        setp(Roughness=0.2)
    elif name == 'glass':
        setp(Base_Color=(0.88, 0.93, 0.92, 1), Roughness=0.0, IOR=1.5)
        b.inputs['Transmission Weight'].default_value = 1.0
    elif name == 'glass_dark':     # tinted, reflective upper glazing
        setp(Base_Color=(0.35, 0.40, 0.42, 1), Roughness=0.02, IOR=1.5, Metallic=0.0)
        b.inputs['Transmission Weight'].default_value = 0.85
    elif name == 'metal_dark':     # powder-coated charcoal frames
        setp(Base_Color=(0.035, 0.035, 0.035, 1), Roughness=0.45, Metallic=0.6)
    elif name == 'bronze':
        setp(Base_Color=(0.36, 0.24, 0.13, 1), Roughness=0.35, Metallic=1.0)
    elif name == 'fabric_ivory':
        setp(Base_Color=(0.78, 0.74, 0.66, 1), Roughness=0.9)
        b.inputs['Sheen Weight'].default_value = 0.4
    elif name == 'fabric_sand':
        setp(Base_Color=(0.55, 0.45, 0.33, 1), Roughness=0.9)
        b.inputs['Sheen Weight'].default_value = 0.4
    elif name == 'lawn':
        n = _noise(nt, scale=0.6, detail=8)
        n2 = _noise(nt, scale=9, detail=4)
        mix = nt.nodes.new('ShaderNodeMath'); mix.operation = 'MULTIPLY_ADD'
        L.new(n.outputs['Fac'], mix.inputs[0]); mix.inputs[1].default_value = 0.6
        L.new(n2.outputs['Fac'], mix.inputs[2])
        L.new(_ramp(nt, mix.outputs[0], [(0.45, (0.055, 0.10, 0.025)), (0.75, (0.11, 0.17, 0.04)), (0.95, (0.16, 0.18, 0.07))]), b.inputs['Base Color'])
        n3 = _noise(nt, scale=300, detail=2)
        L.new(_bump(nt, n3.outputs['Fac'], 0.5, 0.01), b.inputs['Normal'])
        setp(Roughness=0.95)
    elif name == 'earth':          # red laterite soil / dry grass mix
        n = _noise(nt, scale=0.25, detail=8)
        n2 = _noise(nt, scale=6, detail=4)
        mix = nt.nodes.new('ShaderNodeMath'); mix.operation = 'MULTIPLY_ADD'
        L.new(n.outputs['Fac'], mix.inputs[0]); mix.inputs[1].default_value = 0.7
        L.new(n2.outputs['Fac'], mix.inputs[2])
        L.new(_ramp(nt, mix.outputs[0], [(0.5, (0.20, 0.17, 0.08)), (0.7, (0.30, 0.20, 0.10)), (0.9, (0.24, 0.22, 0.12))]), b.inputs['Base Color'])
        setp(Roughness=0.97)
    elif name in ('hill', 'granite_far'):   # distant scrub hills / boulders with aerial-perspective haze
        n = _noise(nt, scale=0.05 if name == 'hill' else 0.4, detail=6)
        if name == 'hill':
            n2 = _noise(nt, scale=0.6, detail=4)
            mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY_ADD'
            L.new(n2.outputs['Fac'], mm.inputs[0]); mm.inputs[1].default_value = 0.8; L.new(n.outputs['Fac'], mm.inputs[2])
            c = _ramp(nt, mm.outputs[0], [(0.55, (0.035, 0.05, 0.02)), (0.75, (0.09, 0.10, 0.045)), (0.95, (0.20, 0.16, 0.10))])
        else:
            c = _ramp(nt, n.outputs['Fac'], [(0.4, (0.30, 0.27, 0.25)), (0.6, (0.42, 0.38, 0.35))])
        L.new(c, b.inputs['Base Color'])
        setp(Roughness=1.0)
        cam = nt.nodes.new('ShaderNodeCameraData')
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = 150; mr.inputs['From Max'].default_value = 2200
        mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = 0.7
        L.new(cam.outputs['View Distance'], mr.inputs['Value'])
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (0.58, 0.64, 0.74, 1); em.inputs['Strength'].default_value = 0.5
        ms = nt.nodes.new('ShaderNodeMixShader')
        L.new(mr.outputs['Result'], ms.inputs[0]); L.new(b.outputs[0], ms.inputs[1]); L.new(em.outputs[0], ms.inputs[2])
        L.new(ms.outputs[0], nt.nodes.get('Material Output').inputs['Surface'])
    elif name == 'meadow':         # native grass meadow, dry and green patches
        n = _noise(nt, scale=0.08, detail=8)
        n2 = _noise(nt, scale=2.5, detail=6)
        mix = nt.nodes.new('ShaderNodeMath'); mix.operation = 'MULTIPLY_ADD'
        L.new(n.outputs['Fac'], mix.inputs[0]); mix.inputs[1].default_value = 0.7
        L.new(n2.outputs['Fac'], mix.inputs[2])
        L.new(_ramp(nt, mix.outputs[0], [(0.5, (0.05, 0.08, 0.025)), (0.68, (0.10, 0.13, 0.04)), (0.85, (0.17, 0.16, 0.07)), (0.95, (0.16, 0.11, 0.06))]), b.inputs['Base Color'])
        n3 = _noise(nt, scale=220, detail=2)
        L.new(_bump(nt, n3.outputs['Fac'], 0.6, 0.01), b.inputs['Normal'])
        setp(Roughness=0.97)
    elif name == 'granite_boulder':
        n = _noise(nt, scale=0.9, detail=8)
        n2 = _noise(nt, scale=40, detail=3)
        c = _ramp(nt, n.outputs['Fac'], [(0.35, (0.30, 0.27, 0.25)), (0.55, (0.46, 0.41, 0.37)), (0.7, (0.38, 0.34, 0.31))])
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 0.4
        L.new(c, mix.inputs['A'])
        L.new(_ramp(nt, n2.outputs['Fac'], [(0.4, (0.6, 0.6, 0.6)), (0.6, (1, 1, 1))]), mix.inputs['B'])
        L.new(mix.outputs['Result'], b.inputs['Base Color'])
        L.new(_bump(nt, n2.outputs['Fac'], 0.3, 0.02), b.inputs['Normal'])
        setp(Roughness=0.8)
    elif name in ('leaf', 'leaf_palm', 'leaf_dark', 'leaf_flower'):
        attr = nt.nodes.new('ShaderNodeAttribute'); attr.attribute_name = 'col'
        base = {'leaf': (0.07, 0.16, 0.035), 'leaf_palm': (0.09, 0.17, 0.04),
                'leaf_dark': (0.035, 0.08, 0.025), 'leaf_flower': (0.07, 0.15, 0.04)}[name]
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        mix.inputs['A'].default_value = (*[c * 2.0 for c in base], 1)
        L.new(attr.outputs['Color'], mix.inputs['B'])
        L.new(mix.outputs['Result'], b.inputs['Base Color'])
        b.inputs['Subsurface Weight'].default_value = 0.0
        setp(Roughness=0.55)
        # translucency mix for back-lit glow
        tr = nt.nodes.new('ShaderNodeBsdfTranslucent')
        L.new(mix.outputs['Result'], tr.inputs['Color'])
        ms = nt.nodes.new('ShaderNodeMixShader'); ms.inputs[0].default_value = 0.3
        out = nt.nodes.get('Material Output')
        L.new(b.outputs[0], ms.inputs[1]); L.new(tr.outputs[0], ms.inputs[2])
        L.new(ms.outputs[0], out.inputs['Surface'])
    elif name == 'grass':
        attr = nt.nodes.new('ShaderNodeAttribute'); attr.attribute_name = 'col'
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        mix.inputs['A'].default_value = (0.11, 0.19, 0.045, 1)
        L.new(attr.outputs['Color'], mix.inputs['B'])
        L.new(mix.outputs['Result'], b.inputs['Base Color'])
        setp(Roughness=0.6)
        tr = nt.nodes.new('ShaderNodeBsdfTranslucent'); L.new(mix.outputs['Result'], tr.inputs['Color'])
        ms = nt.nodes.new('ShaderNodeMixShader'); ms.inputs[0].default_value = 0.35
        L.new(b.outputs[0], ms.inputs[1]); L.new(tr.outputs[0], ms.inputs[2])
        L.new(ms.outputs[0], nt.nodes.get('Material Output').inputs['Surface'])
    elif name == 'bark':
        n = _noise(nt, scale=12, detail=6)
        L.new(_ramp(nt, n.outputs['Fac'], [(0.3, (0.09, 0.07, 0.05)), (0.7, (0.20, 0.17, 0.13))]), b.inputs['Base Color'])
        L.new(_bump(nt, n.outputs['Fac'], 0.6), b.inputs['Normal'])
        setp(Roughness=0.9)
    elif name == 'palm_trunk':
        pos = _worldpos(nt)
        w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'Z'
        w.inputs['Scale'].default_value = 9.0; w.inputs['Distortion'].default_value = 1.0
        L.new(pos, w.inputs['Vector'])
        L.new(_ramp(nt, w.outputs['Fac'], [(0.3, (0.22, 0.19, 0.15)), (0.8, (0.36, 0.32, 0.26))]), b.inputs['Base Color'])
        L.new(_bump(nt, w.outputs['Fac'], 0.5), b.inputs['Normal'])
        setp(Roughness=0.9)
    elif name == 'flower':
        setp(Base_Color=(0.85, 0.80, 0.70, 1), Roughness=0.6)
    elif name == 'bougainvillea':
        setp(Base_Color=(0.55, 0.05, 0.25, 1), Roughness=0.6)
    elif name == 'solar':
        pos = _worldpos(nt)
        br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0
        br.inputs['Brick Width'].default_value = 0.16; br.inputs['Row Height'].default_value = 0.16
        br.inputs['Mortar Size'].default_value = 0.006
        br.inputs['Color1'].default_value = (0.012, 0.018, 0.04, 1)
        br.inputs['Color2'].default_value = (0.015, 0.02, 0.045, 1)
        br.inputs['Mortar'].default_value = (0.25, 0.27, 0.3, 1)
        L.new(pos, br.inputs['Vector']); L.new(br.outputs['Color'], b.inputs['Base Color'])
        setp(Roughness=0.08)
    elif name == 'tile_roof':      # Mangalore clay tile (red)
        pos = _worldpos(nt)
        w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'X'
        w.inputs['Scale'].default_value = 4.0
        L.new(pos, w.inputs['Vector'])
        L.new(_ramp(nt, w.outputs['Fac'], [(0.2, (0.30, 0.09, 0.04)), (0.8, (0.46, 0.16, 0.07))]), b.inputs['Base Color'])
        L.new(_bump(nt, w.outputs['Fac'], 0.4, 0.03), b.inputs['Normal'])
        setp(Roughness=0.7)
    elif name == 'interior_wall':
        setp(Base_Color=(0.72, 0.66, 0.58, 1), Roughness=0.9)
    elif name == 'interior_floor':
        setp(Base_Color=(0.42, 0.36, 0.29, 1), Roughness=0.4)
    elif name.startswith('lamp'):  # warm practical light, 2700 K-ish
        strength = {'lamp': 12.0, 'lamp_soft': 4.0, 'lamp_strong': 30.0, 'lamp_pool': 6.0}.get(name, 10.0)
        col = (0.38, 0.85, 1.0, 1) if name == 'lamp_pool' else (1.0, 0.62, 0.32, 1)
        setp(Base_Color=col)
        b.inputs['Emission Color'].default_value = col
        b.inputs['Emission Strength'].default_value = strength
    elif name == 'asphalt':
        n = _noise(nt, scale=0.4, detail=6); n2 = _noise(nt, scale=80, detail=2)
        L.new(_ramp(nt, n.outputs['Fac'], [(0.4, (0.035, 0.035, 0.037)), (0.6, (0.06, 0.06, 0.062))]), b.inputs['Base Color'])
        L.new(_bump(nt, n2.outputs['Fac'], 0.3, 0.01), b.inputs['Normal'])
        setp(Roughness=0.85)
    elif name == 'curb':
        setp(Base_Color=(0.45, 0.44, 0.42, 1), Roughness=0.8)
    elif name in ('paint_a', 'paint_b', 'paint_c'):
        col = {'paint_a': (0.50, 0.37, 0.27), 'paint_b': (0.40, 0.43, 0.40), 'paint_c': (0.58, 0.50, 0.39)}[name]
        n = _noise(nt, scale=2)
        L.new(_ramp(nt, n.outputs['Fac'], [(0.3, tuple(c * 0.93 for c in col)), (0.7, col)]), b.inputs['Base Color'])
        setp(Roughness=0.85)
    elif name == 'tank':
        setp(Base_Color=(0.02, 0.02, 0.02, 1), Roughness=0.5)
    elif name == 'black':
        setp(Base_Color=(0.02, 0.02, 0.02, 1), Roughness=0.6)
    elif name == 'car_paint':
        setp(Base_Color=(0.55, 0.56, 0.57, 1), Roughness=0.2, Metallic=0.8)
        b.inputs['Coat Weight'].default_value = 1.0
    else:
        setp(Base_Color=(0.6, 0.6, 0.6, 1), Roughness=0.7)
    _M[name] = m
    return m

# ───────────────────────── geometry ─────────────────────────
def _finish(bm, name, material, coll, bevel=0.0):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    if material: me.materials.append(mat(material) if isinstance(material, str) else material)
    link(ob, coll)
    if bevel > 0:
        md = ob.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = 2
        md.limit_method = 'ANGLE'; md.harden_normals = False
    return ob

def box(name, x0, y0, z0, x1, y1, z1, material='plaster', coll=None, bevel=0.008):
    """Axis-aligned box from min corner to max corner (metres)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
        v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
        v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
    ob = _finish(bm, name, material, coll, bevel if min(x1-x0, y1-y0, z1-z0) > 0.03 else 0)
    if material in ('glass', 'glass_dark', 'water'):
        ob.visible_shadow = False   # archviz practice: let sun/sky light pass glazing (no caustics on CPU)
    return ob

def plane(name, x0, y0, x1, y1, z=0.0, material='lawn', coll=None, subdiv=0):
    bm = bmesh.new()
    vs = [bm.verts.new((x0, y0, z)), bm.verts.new((x1, y0, z)), bm.verts.new((x1, y1, z)), bm.verts.new((x0, y1, z))]
    bm.faces.new(vs)
    if subdiv: bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=subdiv, use_grid_fill=True)
    return _finish(bm, name, material, coll)

def cyl(name, x, y, z0, z1, r, material='metal_dark', coll=None, seg=16):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=z1 - z0)
    for v in bm.verts: v.co += Vector((x, y, (z0 + z1) / 2))
    ob = _finish(bm, name, material, coll)
    for p in ob.data.polygons: p.use_smooth = True
    return ob

def pool(name, x0, y0, x1, y1, z_top=0.0, depth=1.4, coll=None, water_drop=0.05, coping=0.3):
    """Basin (tiles) + water surface + dark granite coping."""
    box(name + '_basin_floor', x0, y0, z_top - depth - 0.2, x1, y1, z_top - depth, 'pool_tile', coll, 0)
    t = 0.2
    box(name + '_wall_s', x0 - t, y0 - t, z_top - depth - 0.2, x1 + t, y0, z_top - 0.02, 'pool_tile', coll, 0)
    box(name + '_wall_n', x0 - t, y1, z_top - depth - 0.2, x1 + t, y1 + t, z_top - 0.02, 'pool_tile', coll, 0)
    box(name + '_wall_w', x0 - t, y0, z_top - depth - 0.2, x0, y1, z_top - 0.02, 'pool_tile', coll, 0)
    box(name + '_wall_e', x1, y0, z_top - depth - 0.2, x1 + t, y1, z_top - 0.02, 'pool_tile', coll, 0)
    w = plane(name + '_water', x0, y0, x1, y1, z_top - water_drop, 'water', coll)
    w['jv_water'] = 1
    w.visible_shadow = False
    return w

def lights_in_pool(name, x0, y0, x1, y1, z, coll=None, n=4):
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        box(f'{name}_pl{i}', x - 0.12, y0 + 0.005, z - 0.08, x + 0.12, y0 + 0.02, z + 0.08, 'lamp_pool', coll, 0)

# ───────────────────────── vegetation ─────────────────────────
# Real Poly Haven plants (plants_place.py) replace the procedural trees, shrubs and hedges; palms stay procedural.
def _real_plants():
    return os.environ.get('JV_REAL_PLANTS', '1') != '0'
def _pp():
    import plants_place
    return plants_place
def _col_layer(bm):
    return bm.loops.layers.color.new('col')

def palm(name, x, y, z=0.0, h=7.5, lean=(0.6, 0.2), seed=1, coll=None):
    rnd = random.Random(seed)
    # trunk: curved tapered tube built from rings
    bm = bmesh.new()
    rings, seg = 14, 10
    pts = []
    for i in range(rings + 1):
        t = i / rings
        off = Vector((lean[0] * t * t, lean[1] * t * t, 0))
        pts.append(Vector((x, y, z + h * t)) + off)
    prev = None
    for i, p in enumerate(pts):
        r = 0.22 - 0.07 * (i / rings) + (0.06 if i == 0 else 0)
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            ring.append(bm.verts.new(p + Vector((math.cos(a) * r, math.sin(a) * r, 0))))
        if prev:
            for k in range(seg):
                bm.faces.new((prev[k], prev[(k + 1) % seg], ring[(k + 1) % seg], ring[k]))
        prev = ring
    tr = _finish(bm, name + '_trunk', 'palm_trunk', coll)
    for pgn in tr.data.polygons: pgn.use_smooth = True
    top = pts[-1]
    # fronds with geometric leaflets
    bm = bmesh.new(); cl = _col_layer(bm)
    nf = 16
    for f in range(nf):
        az = 2 * math.pi * f / nf + rnd.uniform(-0.2, 0.2)
        el = math.radians(rnd.uniform(-20, 45) if f % 2 else rnd.uniform(15, 55))
        L = rnd.uniform(2.6, 3.4)
        d = Vector((math.cos(az), math.sin(az), 0))
        side = Vector((-d.y, d.x, 0))
        tint = rnd.uniform(0.75, 1.15)
        n_l = 26
        for i in range(n_l):
            t = (i + 1) / (n_l + 1)
            # rachis point: launch angle then gravity droop
            s = L * t
            hz = math.sin(el) * s - 0.55 * s * s / L
            p = top + d * (math.cos(el) * s) + Vector((0, 0, hz + 0.1))
            ll = 0.75 * math.sin(math.pi * min(1, t * 1.1)) + 0.12
            for sgn in (-1, 1):
                tipdir = (side * sgn * 0.85 + d * 0.35 + Vector((0, 0, -0.45))).normalized()
                w = 0.035
                a = p; b2 = p + tipdir * ll
                nrm = (d.cross(tipdir)).normalized() * w
                v1 = bm.verts.new(a - nrm); v2 = bm.verts.new(a + nrm)
                v3 = bm.verts.new(b2 + nrm * 0.2); v4 = bm.verts.new(b2 - nrm * 0.2)
                fc = bm.faces.new((v1, v2, v3, v4))
                c = (tint * rnd.uniform(0.85, 1.1), tint * rnd.uniform(0.9, 1.1), tint * 0.9, 1)
                for lp in fc.loops: lp[cl] = c
    _finish(bm, name + '_fronds', 'leaf_palm', coll)
    return tr

def tree(name, x, y, z=0.0, h=6.0, crown=3.0, seed=2, coll=None, leaf_mat='leaf', leaves=3500, flowers=0):
    """Broadleaf tree (rain tree / neem character): trunk + branches + leaf-card clusters."""
    if _real_plants(): return _pp().tree(name, x, y, z, h, crown, seed, coll)
    rnd = random.Random(seed)
    bm = bmesh.new()
    def limb(p0, p1, r0, r1, seg=8):
        axis = (p1 - p0)
        q = axis.to_track_quat('Z', 'Y')
        rings = []
        for j, (p, r) in enumerate(((p0, r0), (p1, r1))):
            ring = [bm.verts.new(p + q @ Vector((math.cos(2*math.pi*k/seg)*r, math.sin(2*math.pi*k/seg)*r, 0))) for k in range(seg)]
            rings.append(ring)
        for k in range(seg):
            bm.faces.new((rings[0][k], rings[0][(k+1)%seg], rings[1][(k+1)%seg], rings[1][k]))
    base = Vector((x, y, z)); fork = Vector((x + rnd.uniform(-.2, .2), y + rnd.uniform(-.2, .2), z + h * 0.42))
    limb(base, fork, 0.22 * h / 6, 0.16 * h / 6)
    tips = []
    for i in range(5):
        az = 2 * math.pi * i / 5 + rnd.uniform(-0.3, 0.3)
        tip = fork + Vector((math.cos(az) * crown * 0.6, math.sin(az) * crown * 0.6, h * rnd.uniform(0.3, 0.45)))
        limb(fork, tip, 0.12 * h / 6, 0.04)
        tips.append(tip)
    trk = _finish(bm, name + '_trunk', 'bark', coll)
    for pg in trk.data.polygons: pg.use_smooth = True
    bm = bmesh.new(); cl = _col_layer(bm)
    centers = tips + [fork + Vector((0, 0, h * 0.5))]
    for i in range(leaves):
        c = rnd.choice(centers)
        u = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.6))).normalized() * (crown * 0.55) * (rnd.random() ** 0.4)
        p = c + u
        n = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.2, 1))).normalized()
        t1 = n.orthogonal().normalized(); t2 = n.cross(t1)
        s = rnd.uniform(0.16, 0.30)
        vs = [bm.verts.new(p + t1 * s), bm.verts.new(p + t2 * s * 0.55), bm.verts.new(p - t1 * s), bm.verts.new(p - t2 * s * 0.5)]
        fc = bm.faces.new(vs)
        # self-shadow tint: darker inside the crown
        shade = 0.6 + 0.5 * min(1, u.length / (crown * 0.55))
        col = (shade * rnd.uniform(0.85, 1.1), shade * rnd.uniform(0.9, 1.1), shade * 0.85, 1)
        for lp in fc.loops: lp[cl] = col
    _finish(bm, name + '_leaves', leaf_mat, coll)
    if flowers:
        bm = bmesh.new()
        for i in range(flowers):
            c = rnd.choice(centers)
            u = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.5))).normalized() * crown * 0.55
            p = c + u
            bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.05, matrix=Matrix.Translation(p))
        _finish(bm, name + '_flowers', 'flower', coll)
    return trk

def shrub(name, x, y, z=0.0, r=0.8, hgt=0.9, seed=3, coll=None, n=500, material='leaf_dark', sx=1.0, sy=1.0):
    if _real_plants(): return _pp().shrub(name, x, y, z, r, hgt, seed, coll)
    rnd = random.Random(seed)
    bm = bmesh.new(); cl = _col_layer(bm)
    for i in range(n):
        u = Vector((rnd.gauss(0, 1) * sx, rnd.gauss(0, 1) * sy, abs(rnd.gauss(0, 1)))).normalized()
        k = rnd.random() ** 0.35
        p = Vector((x + u.x * r * k, y + u.y * r * k, z + u.z * hgt * k))
        nn = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, 1))).normalized()
        t1 = nn.orthogonal().normalized(); t2 = nn.cross(t1)
        s = rnd.uniform(0.07, 0.12)
        fc = bm.faces.new([bm.verts.new(p + t1 * s), bm.verts.new(p + t2 * s * .5), bm.verts.new(p - t1 * s), bm.verts.new(p - t2 * s * .5)])
        sh = 0.55 + 0.55 * k
        for lp in fc.loops: lp[cl] = (sh, sh * rnd.uniform(.9, 1.1), sh * .85, 1)
    return _finish(bm, name, material, coll)

def hedge(name, x0, y0, x1, y1, z=0.0, h=1.0, coll=None, seed=4, density=260, material='leaf_dark'):
    """Hedge run along a line — leaf cards in a rounded box volume."""
    if _real_plants(): return _pp().hedge(name, x0, y0, x1, y1, z, h, coll, seed)
    rnd = random.Random(seed)
    bm = bmesh.new(); cl = _col_layer(bm)
    a = Vector((x0, y0, z)); b2 = Vector((x1, y1, z)); L = (b2 - a).length
    d = (b2 - a).normalized(); sd = Vector((-d.y, d.x, 0))
    n = int(L * density)
    for i in range(n):
        t = rnd.random(); w = rnd.uniform(-0.35, 0.35); zz = rnd.uniform(0, h)
        p = a + d * (t * L) + sd * w + Vector((0, 0, zz))
        nn = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.2, 1))).normalized()
        t1 = nn.orthogonal().normalized(); t2 = nn.cross(t1); s = rnd.uniform(0.06, 0.1)
        fc = bm.faces.new([bm.verts.new(p + t1 * s), bm.verts.new(p + t2 * s * .5), bm.verts.new(p - t1 * s), bm.verts.new(p - t2 * s * .5)])
        sh = 0.6 + 0.4 * (zz / h) + 0.3 * abs(w) / 0.35
        for lp in fc.loops: lp[cl] = (sh, sh * rnd.uniform(.9, 1.1), sh * .85, 1)
    return _finish(bm, name, material, coll)

def boulder(name, x, y, z, sx, sy, sz, seed=5, coll=None, subdiv=4):
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    ox, oy, oz = rnd.uniform(0, 100), rnd.uniform(0, 100), rnd.uniform(0, 100)
    from mathutils import noise
    for v in bm.verts:
        p = v.co.copy()
        dsp = 0.18 * noise.noise(p * 1.3 + Vector((ox, oy, oz))) + 0.06 * noise.noise(p * 4 + Vector((oy, oz, ox)))
        v.co = p * (1 + dsp)
        v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
        if v.co.z < -sz * 0.35: v.co.z = -sz * 0.35   # sit on ground
        v.co += Vector((x, y, z + sz * 0.35))
    ob = _finish(bm, name, 'granite_far' if subdiv <= 3 else 'granite_boulder', coll)
    for pg in ob.data.polygons: pg.use_smooth = True
    return ob

def terrain(name, size=600, res=120, z=0.0, flat_r=70, hill_h=26, seed=6, coll=None, material='earth', center=(0, 0)):
    """Ground that stays flat near the site and rolls into scrub hills further out."""
    from mathutils import noise
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=res, y_segments=res, size=size / 2)
    cx, cy = center
    for v in bm.verts:
        v.co.x += cx; v.co.y += cy
        d = math.hypot(v.co.x - cx, v.co.y - cy)
        k = max(0.0, min(1.0, (d - flat_r) / (size * 0.35)))
        n = noise.noise(Vector((v.co.x * 0.008, v.co.y * 0.008, seed))) * 0.5 + 0.5
        n2 = noise.noise(Vector((v.co.x * 0.03, v.co.y * 0.03, seed + 3)))
        v.co.z = z + (k ** 1.6) * (hill_h * n + 4 * n2) - (0.0 if d > flat_r else 0)
    ob = _finish(bm, name, material, coll)
    for pg in ob.data.polygons: pg.use_smooth = True
    return ob

# ───────────────────────── furniture ─────────────────────────
def lounger(name, x, y, z=0.0, rot=0.0, coll=None):
    objs = []
    objs.append(box(name + '_frame', -0.35, -1.0, 0.0, 0.35, 1.0, 0.28, 'teak', coll, 0.01))
    objs.append(box(name + '_pad', -0.33, -0.98, 0.28, 0.33, 0.45, 0.36, 'fabric_ivory', coll, 0.02))
    back = box(name + '_back', -0.33, 0.0, 0.0, 0.33, 0.75, 0.08, 'fabric_ivory', coll, 0.02)
    back.rotation_euler = (math.radians(-35), 0, 0); back.location = (0, 0.45, 0.32)
    objs.append(back)
    for o in objs:
        o.location = Vector(o.location) if o is back else o.location
        o.matrix_basis = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z") @ o.matrix_basis
    return objs

def umbrella(name, x, y, z=0.0, coll=None):
    cyl(name + '_pole', x, y, z, z + 2.4, 0.025, 'teak', coll, 8)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=1.4, radius2=0.02, depth=0.5)
    for v in bm.verts: v.co += Vector((x, y, z + 2.45))
    return _finish(bm, name + '_canopy', 'fabric_sand', coll)

def sofa(name, x0, y0, x1, y1, z=0.0, coll=None, material='fabric_ivory'):
    box(name + '_base', x0, y0, z, x1, y1, z + 0.42, material, coll, 0.03)
    box(name + '_back', x0, y1 - 0.2, z, x1, y1, z + 0.8, material, coll, 0.03)

def bollard(name, x, y, z=0.0, coll=None):
    box(name, x - 0.06, y - 0.06, z, x + 0.06, y + 0.06, z + 0.6, 'metal_dark', coll, 0.005)
    box(name + '_glow', x - 0.05, y - 0.065, z + 0.42, x + 0.05, y + 0.065, z + 0.5, 'lamp', coll, 0)

def car(name, x, y, z=0.0, rot=0.0, coll=None):
    """Simple hatchback massing — reads as a parked car at distance."""
    parts = [box(name + '_body', -0.85, -1.95, 0.25, 0.85, 1.95, 0.85, 'car_paint', coll, 0.06),
             box(name + '_cabin', -0.78, -1.1, 0.85, 0.78, 1.0, 1.45, 'glass_dark', coll, 0.05)]
    for wx in (-0.8, 0.8):
        for wy in (-1.3, 1.3):
            w = cyl(name + f'_w{wx}{wy}', 0, 0, -0.1, 0.1, 0.32, 'black', coll, 16)
            w.rotation_euler = (0, math.radians(90), 0); w.location = (wx, wy, 0.32)
            parts.append(w)
    for o in parts:
        o.matrix_basis = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z") @ o.matrix_basis
    return parts

# ───────────────────────── light / camera / render ─────────────────────────
def sky(sun_elev=12.0, sun_az=230.0, strength=1.0, sun_strength=4.0, sun_angle=1.2, warm=True):
    """Physical sky (multiple scattering) + matching sun lamp. Angles in degrees.
    sun_az: compass azimuth of the sun measured from +Y (north) clockwise towards +X (east)."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new('Sky'); sc.world = w
    nt = w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    s = nt.nodes.new('ShaderNodeTexSky'); s.sky_type = 'MULTIPLE_SCATTERING'
    s.sun_disc = False
    s.sun_elevation = math.radians(sun_elev)
    # Blender sky: rotation 0 => sun towards -Y?; we verify by matching lamp to sky in test renders
    s.sun_rotation = math.radians(sun_az)
    s.altitude = 900.0
    s.air_density = 1.0; s.aerosol_density = 1.6
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(s.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    ld = bpy.data.lights.new('Sun', 'SUN'); ld.energy = sun_strength
    ld.angle = math.radians(sun_angle)
    ld.color = (1.0, 0.78, 0.56) if warm else (1.0, 0.95, 0.88)
    so = bpy.data.objects.new('Sun', ld); link(so)
    az = math.radians(sun_az); el = math.radians(sun_elev)
    d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))  # towards sun
    so.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    return s, so

def area_light(name, x, y, z, sx, sy, energy, color=(1.0, 0.65, 0.38), coll=None, rot=(0, 0, 0)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'; ld.size = sx; ld.size_y = sy
    ld.energy = energy; ld.color = color
    o = bpy.data.objects.new(name, ld); o.location = (x, y, z); o.rotation_euler = rot
    link(o, coll); return o

def point_light(name, x, y, z, energy, color=(1.0, 0.62, 0.34), radius=0.05, coll=None):
    ld = bpy.data.lights.new(name, 'POINT'); ld.energy = energy; ld.color = color; ld.shadow_soft_size = radius
    o = bpy.data.objects.new(name, ld); o.location = (x, y, z); link(o, coll); return o

def camera(name, loc, target, lens=28, shift_y=0.0, sensor=36):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = sensor; cd.shift_y = shift_y
    cd.clip_end = 3000
    co = bpy.data.objects.new(name, cd); link(co)
    co.location = loc
    d = Vector(target) - Vector(loc)
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return co

def level_camera(co, target):
    """Two-point perspective: keep camera level, use shift to frame (straight verticals)."""
    d = Vector(target) - co.location
    flat = Vector((d.x, d.y, 0))
    co.rotation_euler = flat.to_track_quat('-Z', 'Y').to_euler()
    return co

def render(path, cam, res=(1600, 900), samples=128):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

def slab_with_hole(name, x0, y0, x1, y1, z0, z1, hole, material='stone_pave', coll=None):
    """Rectangular slab with one rectangular opening (for pools set into decks)."""
    hx0, hy0, hx1, hy1 = hole
    parts = []
    if hy0 > y0: parts.append(box(name + '_s', x0, y0, z0, x1, hy0, z1, material, coll, 0))
    if hy1 < y1: parts.append(box(name + '_n', x0, hy1, z0, x1, y1, z1, material, coll, 0))
    if hx0 > x0: parts.append(box(name + '_w', x0, max(y0, hy0), z0, hx0, min(y1, hy1), z1, material, coll, 0))
    if hx1 < x1: parts.append(box(name + '_e', hx1, max(y0, hy0), z0, x1, min(y1, hy1), z1, material, coll, 0))
    return parts

def hills_ring(name, r0=260, r1=900, z_base=-20, seed=9, coll=None, peaks=None, mat_name='hill', seg_a=160, seg_r=30, low_dirs=None):
    """Ring of rolling scrub hills around the site. peaks: list of (azimuth_deg, radius, width, height)."""
    from mathutils import noise
    rnd = random.Random(seed)
    if peaks is None:
        peaks = [(rnd.uniform(0, 360), rnd.uniform(r0 + 80, r1 - 150), rnd.uniform(90, 220), rnd.uniform(40, 130)) for _ in range(14)]
    bm = bmesh.new()
    grid = []
    for i in range(seg_r + 1):
        r = r0 + (r1 - r0) * (i / seg_r) ** 1.3
        row = []
        for j in range(seg_a):
            a = 2 * math.pi * j / seg_a
            x, y = math.sin(a) * r, math.cos(a) * r
            h = 0.0
            for (az, pr, pw, ph) in peaks:
                px, py = math.sin(math.radians(az)) * pr, math.cos(math.radians(az)) * pr
                d = math.hypot(x - px, y - py)
                h = max(h, ph * math.exp(-(d / pw) ** 2))
            h += 10 * (noise.noise(Vector((x * 0.006, y * 0.006, seed))) * 0.5 + 0.5) * min(1, (r - r0) / 120)
            row.append(bm.verts.new((x, y, z_base + h)))
        grid.append(row)
    for i in range(seg_r):
        for j in range(seg_a):
            a, b2 = grid[i][j], grid[i][(j + 1) % seg_a]
            c, d = grid[i + 1][(j + 1) % seg_a], grid[i + 1][j]
            bm.faces.new((a, b2, c, d))
    ob = _finish(bm, name, mat_name, coll)
    for pg in ob.data.polygons: pg.use_smooth = True
    # scrub-tree scatter (stills): density by distance, fading out far away
    vg = ob.vertex_groups.new(name='dens')
    for v in ob.data.vertices:
        r = math.hypot(v.co.x, v.co.y)
        w = 1.0 if r < 700 else max(0.0, 1 - (r - 700) / 900)
        vg.add([v.index], w, 'REPLACE')
    sb = bmesh.new(); cl = _col_layer(sb)
    for k in range(3):
        bmesh.ops.create_icosphere(sb, subdivisions=1, radius=1.0,
                                   matrix=Matrix.Translation((rnd.uniform(-1.2, 1.2), rnd.uniform(-1.2, 1.2), rnd.uniform(0.6, 1.4))) @ Matrix.Scale(rnd.uniform(1.0, 1.6), 4))
    for f in sb.faces:
        sh = rnd.uniform(0.5, 1.0)
        for lp in f.loops: lp[cl] = (sh, sh, sh * 0.9, 1)
    scrub = _finish(sb, name + '_scrub', 'leaf_dark', None); scrub.location = (0, 0, -80)
    ps = scatter(ob, scrub, 42000, seed=seed, size=1.15, size_rand=0.7)
    ps.vertex_group_density = 'dens'
    ps.settings.rotation_mode = 'NONE'
    return ob, peaks

def wall(name, axis, a0, a1, t0, t1, z0, z1, openings=(), material='brick', coll=None, bevel=0.006):
    """Wall slab with rectangular openings.
    axis='x': wall runs along X from a0..a1, thickness across Y t0..t1.
    axis='y': wall runs along Y from a0..a1, thickness across X t0..t1.
    openings: list of (u0, u1, v0, v1) in wall-run coordinate u and height v (absolute z)."""
    us = sorted(set([a0, a1] + [max(a0, min(a1, o[0])) for o in openings] + [max(a0, min(a1, o[1])) for o in openings]))
    vs = sorted(set([z0, z1] + [max(z0, min(z1, o[2])) for o in openings] + [max(z0, min(z1, o[3])) for o in openings]))
    parts = []
    k = 0
    for j in range(len(vs) - 1):
        run = None
        for i in range(len(us) - 1):
            cu = (us[i] + us[i + 1]) / 2; cv = (vs[j] + vs[j + 1]) / 2
            hole = any(o[0] < cu < o[1] and o[2] < cv < o[3] for o in openings)
            if not hole:
                run = (run[0], us[i + 1]) if run else (us[i], us[i + 1])
            if (hole or i == len(us) - 2) and run:
                u0, u1 = run
                if axis == 'x': parts.append(box(f'{name}_{k}', u0, t0, vs[j], u1, t1, vs[j + 1], material, coll, bevel))
                else: parts.append(box(f'{name}_{k}', t0, u0, vs[j], t1, u1, vs[j + 1], material, coll, bevel))
                k += 1; run = None
    return parts

def window(name, axis, u0, u1, t, v0, v1, coll=None, frame=0.05, mullions=1, glass='glass', depth=0.06):
    """Glazed opening: frame + glass at wall position t (centre plane)."""
    objs = []
    def b(n, a, bb, c, d, m):
        if axis == 'x': objs.append(box(n, a, t - depth / 2, c, bb, t + depth / 2, d, m, coll, 0))
        else: objs.append(box(n, t - depth / 2, a, c, t + depth / 2, bb, d, m, coll, 0))
    b(name + '_fb', u0, u1, v0, v0 + frame, 'metal_dark')
    b(name + '_ft', u0, u1, v1 - frame, v1, 'metal_dark')
    b(name + '_fl', u0, u0 + frame, v0, v1, 'metal_dark')
    b(name + '_fr', u1 - frame, u1, v0, v1, 'metal_dark')
    for m in range(1, mullions + 1):
        uu = u0 + (u1 - u0) * m / (mullions + 1)
        b(name + f'_m{m}', uu - frame / 2, uu + frame / 2, v0, v1, 'metal_dark')
    if axis == 'x': objs.append(box(name + '_gl', u0, t - 0.006, v0, u1, t + 0.006, v1, glass, coll, 0))
    else: objs.append(box(name + '_gl', t - 0.006, u0, v0, t + 0.006, u1, v1, glass, coll, 0))
    return objs

def jali(name, axis, u0, u1, t0, t1, z0, z1, coll=None, material='brick', bw=0.23, bh=0.075, gap=0.11):
    """Honeycomb brick jali: alternating courses of bricks with open gaps (real geometry)."""
    objs = []
    rows = int((z1 - z0) / bh)
    for r in range(rows):
        zz = z0 + r * bh
        if r % 2 == 0:
            if axis == 'x': objs.append(box(f'{name}_c{r}', u0, t0, zz, u1, t1, zz + bh * 0.92, material, coll, 0))
            else: objs.append(box(f'{name}_c{r}', t0, u0, zz, t1, u1, zz + bh * 0.92, material, coll, 0))
        else:
            off = (r // 2 % 2) * (bw + gap) / 2
            u = u0 + off
            while u < u1:
                ue = min(u1, u + bw)
                if axis == 'x': objs.append(box(f'{name}_b{r}_{int(u*100)}', u, t0, zz, ue, t1, zz + bh * 0.92, material, coll, 0))
                else: objs.append(box(f'{name}_b{r}_{int(u*100)}', t0, u, zz, t1, ue, zz + bh * 0.92, material, coll, 0))
                u += bw + gap
    return objs

def grass_clump(name, blades=24, h=0.22, spread=0.12, seed=1, material='grass', dry=0.0):
    """One clump of curved grass blades (instanced by particles)."""
    rnd = random.Random(seed)
    bm = bmesh.new(); cl = _col_layer(bm)
    for i in range(blades):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0, spread)
        base = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        lean = Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(0.02, 0.09)
        hh = h * rnd.uniform(0.6, 1.25); w = rnd.uniform(0.004, 0.008)
        side = Vector((-math.sin(a + 1.2), math.cos(a + 1.2), 0)) * w
        segs = 3; prev = None
        for s in range(segs + 1):
            t = s / segs
            p = base + lean * (t * t) * 3 + Vector((0, 0, hh * t))
            ww = 1 - t * 0.9
            pair = (bm.verts.new(p - side * ww), bm.verts.new(p + side * ww))
            if prev:
                f = bm.faces.new((prev[0], prev[1], pair[1], pair[0]))
                c = 0.55 + 0.6 * t
                tint = (c * (1 + dry * 1.2), c * (1 + dry * 0.6), c * 0.8, 1)
                for lp in f.loops: lp[cl] = tint
            prev = pair
    ob = _finish(bm, name, material, None)
    ob.location = (0, 0, -60)
    return ob

def scatter(emitter, inst, count, seed=0, size=1.0, size_rand=0.5):
    ps = emitter.modifiers.new('grass', 'PARTICLE_SYSTEM').particle_system
    st = ps.settings
    st.type = 'HAIR'; st.use_advanced_hair = True
    st.count = int(count); st.hair_length = 1.0
    st.render_type = 'OBJECT'; st.instance_object = inst
    st.particle_size = size; st.size_random = size_rand
    st.use_rotations = True; st.rotation_mode = 'NOR'; st.phase_factor_random = 2.0
    st.rotation_factor_random = 0.15
    st.emit_from = 'FACE'; st.use_emit_random = True; st.distribution = 'RAND'
    ps.seed = seed
    return ps
