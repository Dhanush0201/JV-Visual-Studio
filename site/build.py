"""Assemble the JV Visual Studio v5 site (Look 1 and Look 2) into /home/claude/jv5/dist."""
import json, os, shutil, sys, math
from PIL import Image

ROOT = '/home/claude/jv5'
DIST = f'{ROOT}/dist'
SITE = f'{ROOT}/site'
REN = f'{ROOT}/renders'
WEB = f'{ROOT}/web'
os.makedirs(DIST, exist_ok=True)
for d in ('assets', 'lib/addons/loaders', 'lib/addons/utils', 'lib/addons/libs', 'models', 'img', 'sky'):
    os.makedirs(f'{DIST}/{d}', exist_ok=True)

# libraries
T = f'{ROOT}/tools/node_modules/three'
shutil.copy(f'{T}/build/three.module.min.js', f'{DIST}/lib/three.module.min.js')
shutil.copy(f'{T}/examples/jsm/loaders/GLTFLoader.js', f'{DIST}/lib/addons/loaders/GLTFLoader.js')
shutil.copy(f'{T}/examples/jsm/utils/BufferGeometryUtils.js', f'{DIST}/lib/addons/utils/BufferGeometryUtils.js')
shutil.copy(f'{SITE}/assets/site.css', f'{DIST}/assets/site.css')
shutil.copy(f'{SITE}/assets/app.js', f'{DIST}/assets/app.js')

# stills → webp (large + small)
STILLS = ['resort_hero', 'resort_edge', 'resort_villa', 'resort_hero_dusk', 'resort_villa_dusk', 'villa_front_day',
          'villa_front_dusk', 'villa_pool', 'villa_aerial_dusk', 'home_street', 'home_aerial', 'home_jali']
have = set()
for s in STILLS:
    p = f'{REN}/{s}.png'
    if not os.path.exists(p): continue
    im = Image.open(p).convert('RGB')
    im.resize((1600, 900), Image.LANCZOS).save(f'{DIST}/img/{s}.webp', 'WEBP', quality=82, method=6)
    im.resize((880, 495), Image.LANCZOS).save(f'{DIST}/img/{s}-s.webp', 'WEBP', quality=78, method=6)
    have.add(s)

# real-material (PBR) models: light-only lightmaps + albedo atlases, Poly Haven texture library, HDRI skies
PB = f'{ROOT}/pbr'
LIBJS = json.load(open(f'{PB}/web/library.json'))
os.makedirs(f'{DIST}/pbr/tex', exist_ok=True)
T = f'{ROOT}/tools/node_modules/three'
shutil.copy(f'{T}/examples/jsm/loaders/RGBELoader.js', f'{DIST}/lib/addons/loaders/RGBELoader.js')
shutil.copy(f'{T}/examples/jsm/libs/meshopt_decoder.module.js', f'{DIST}/lib/addons/libs/meshopt_decoder.module.js')
PBR = {}
used_tex = set()
import subprocess, re, base64
PLIB = json.load(open(f'{ROOT}/plants/web/plants_lib.json'))
used_pmat = set()
for k in ('resort', 'villa', 'home'):
    meta_p = f'{PB}/bake/{k}_meta.json'
    if not os.path.exists(meta_p): continue
    meta = json.load(open(meta_p))
    atl = {}
    for a, am in meta['atlases'].items():
        for kind in ('lm', 'al'):
            src = Image.open(f'{PB}/bake/{k}_{kind}_{a}.png').convert('RGB')
            src.save(f'{DIST}/pbr/{k}_{kind}_{a}.webp', 'WEBP', quality=90 if kind == 'lm' else 86, method=6)
            src.resize((src.width // 2, src.height // 2), Image.LANCZOS).save(f'{DIST}/pbr/{k}_{kind}_{a}-m.webp', 'WEBP', quality=86, method=6)
        atl[a] = {'lm': f'pbr/{k}_lm_{a}', 'al': f'pbr/{k}_al_{a}', 'k': am['k']}
    shutil.copy(f'{PB}/bake/{k}_sky.jpg', f'{DIST}/pbr/{k}_sky.jpg')
    shutil.copy(f'{PB}/bake/{k}_env.hdr', f'{DIST}/pbr/{k}_env.hdr')
    # the claude.ai preview host serves no .hdr, so the environment also ships as a base64 ES module
    import base64
    open(f'{DIST}/pbr/{k}_env.hdr.js', 'w').write('export default "' + base64.b64encode(open(f'{PB}/bake/{k}_env.hdr', 'rb').read()).decode() + '";\n')
    g = f'{PB}/bake/{k}_q.glb'
    shutil.copy(g, f'{DIST}/models/{k}.glb')
    import base64
    open(f'{DIST}/models/{k}.glb.js', 'w').write('export default "' + base64.b64encode(open(g, 'rb').read()).decode() + '";\n')
    sun = max(a['k'] for a in meta['atlases'].values()) * math.pi * 0.5
    PBR[k] = {'atlases': atl, 'sky': f'pbr/{k}_sky.jpg', 'kb': meta['kb'], 'env': f'pbr/{k}_env.hdr', 'envJs': f'../pbr/{k}_env.hdr.js', 'kv': meta['kv'], 'sunLevel': sun,
              'atlasOf': {'JV_' + gname: gm['atlas'] for gname, gm in meta['groups'].items() if gm['atlas']}}
    # real plants: instance list, sun-free environment, per-scene prototype GLBs (desktop + lighter phone set)
    pj = f'{PB}/bake/{k}_plants.json'
    if os.path.exists(pj) and os.path.exists(f'{PB}/bake/{k}_envd.hdr'):
        inst = json.load(open(pj))['instances']
        used = sorted({i['p'] for i in inst})
        down = {'jac_near': 'jac_far', 'jac_far': 'jac_dist'}
        used_m = sorted({down.get(p, p) for p in used})
        os.makedirs(f'{DIST}/plants', exist_ok=True)
        for tag, lst in (('', used), ('-m', used_m)):
            out = f'{DIST}/plants/{k}{tag}.glb'
            subprocess.run(['node', 'post_plants.mjs', f'{ROOT}/plants/web/plants_raw.glb', out, ','.join(lst)], cwd=f'{ROOT}/tools', check=True, capture_output=True)
            open(out + '.js', 'w').write('export default "' + base64.b64encode(open(out, 'rb').read()).decode() + '";\n')
        shutil.copy(f'{PB}/bake/{k}_envd.hdr', f'{DIST}/pbr/{k}_envd.hdr')
        open(f'{DIST}/pbr/{k}_envd.hdr.js', 'w').write('export default "' + base64.b64encode(open(f'{PB}/bake/{k}_envd.hdr', 'rb').read()).decode() + '";\n')
        H = meta['hdri']
        PBR[k]['plants'] = {'glb': f'plants/{k}', 'glbJs': f'../plants/{k}', 'inst': inst, 'down': down,
                            'envd': f'pbr/{k}_envd.hdr', 'envdJs': f'../pbr/{k}_envd.hdr.js',
                            'sun': ({'dir': H['sun_dir_gltf'], 'E': H['E_sun'], 'col': H['sun_col']} if H.get('E_sun') else None),
                            # dusk: no sun, so plants are lit by the baked light under them
                            'probeMix': 0 if H.get('E_sun') else 0.75, 'probeGain': 1.0 if H.get('E_sun') else 4.0, 'plantEnv': 1.0}
        for p_ in set(used) | set(used_m):
            for mname in PLIB['protos'][p_]['materials']:
                used_pmat.add(re.sub(r'\.\d+$', '', mname))
# plant textures (colour+alpha, normal, roughness), only the sets the scenes use
os.makedirs(f'{DIST}/plants/tex', exist_ok=True)
PLANT_MATS = {}
for mname in sorted(used_pmat):
    rec = PLIB['materials'].get(mname)
    if not rec: continue
    PLANT_MATS[mname] = {kk: rec[kk] for kk in ('c', 'n', 'r', 'alpha') if kk in rec}
    for kk in ('c', 'n', 'r'):
        if kk in rec:
            for suf in ('', '-m'): shutil.copy(f'{ROOT}/plants/web/tex/{rec[kk]}{suf}.webp', f'{DIST}/plants/tex/')
for name, mt in LIBJS['materials'].items():
    if mt['mode'] == 'photo': used_tex.add((mt['tex'], mt.get('grey', False)))
for tex, grey in used_tex:
    for key in (('gd' if grey else 'd'), 'n', 'arm'):
        for suf in ('', '-m'):
            src = f'{PB}/web/tex/{tex}_{key}{suf}.webp'
            if os.path.exists(src): shutil.copy(src, f'{DIST}/pbr/tex/')

# models + skies
fog = {}
for k in ('resort', 'villa', 'home'):
    g = f'{WEB}/{k}_opt.glb'
    if os.path.exists(g) and k not in PBR:
        shutil.copy(g, f'{DIST}/models/{k}.glb')            # for normal hosting (Vercel)
        import base64
        open(f'{DIST}/models/{k}.glb.js', 'w').write('export default "' + base64.b64encode(open(g, 'rb').read()).decode() + '";\n')
    sky = f'{WEB}/{k}_sky.jpg'
    if os.path.exists(sky):
        im = Image.open(sky).convert('RGB')
        im.save(f'{DIST}/sky/{k}.jpg', 'JPEG', quality=86)
        w, h = im.size
        row = im.crop((0, int(h * 0.49), w, int(h * 0.51))).resize((1, 1), Image.BOX).getpixel((0, 0))
        fog[k] = '#%02x%02x%02x' % row

def img(s, alt_en, alt_kn, spec):
    if s not in have: return ''
    return f'''<figure><img src="img/{s}.webp" srcset="img/{s}-s.webp 880w, img/{s}.webp 1600w" sizes="(max-width:640px) 86vw, 920px" alt="{alt_en}" loading="lazy" width="1600" height="900">
<figcaption><span><span lang="en">{alt_en}</span><span lang="kn">{alt_kn}</span></span><span class="spec">{spec}</span></figcaption></figure>'''

def bi(en, kn, tag='span', cls=''):
    c = f' class="{cls}"' if cls else ''
    return f'<{tag} lang="en"{c}>{en}</{tag}><{tag} lang="kn"{c}>{kn}</{tag}>'

SPEC = 'CYCLES · 64 SPP · AgX · 1920×1080'
CONCEPT = bi('STUDIO CONCEPT · DESIGN VISUALISATION', 'ಸ್ಟುಡಿಯೋ ಪರಿಕಲ್ಪನೆ · ವಿನ್ಯಾಸ ದೃಶ್ಯೀಕರಣ')
DRAFT = '<span class="draft" title="New copy — awaiting approval">DRAFT</span>'

FILMS = json.load(open(f'{ROOT}/film/films_meta.json')) if os.path.exists(f'{ROOT}/film/films_meta.json') else {}
os.makedirs(f'{DIST}/films', exist_ok=True)
for fid, fm in FILMS.items():
    for ext in ('mp4', 'webp'):
        src = f'{ROOT}/film/web/{fid}.{ext}'
        if os.path.exists(src): shutil.copy(src, f'{DIST}/films/{fid}.{ext}')

def films(scene, h_en, h_kn):
    items = [(fid, fm) for fid, fm in FILMS.items() if fm['scene'] == scene]
    if not items: return ''
    cards = []
    for fid, fm in items:
        cards.append(f'''<figure class="film" data-film="{fid}">
  <div class="fr"><video muted playsinline loop preload="none" poster="films/{fid}.webp" data-src="films/{fid}.mp4" aria-label="{fm['title_en']}"></video>
  <span class="tag">{bi(fm['kind_en'], fm['kind_kn'])}<span class="dur">0:11</span></span>
  <button type="button" class="open" aria-label="Play larger / ದೊಡ್ಡದಾಗಿ ನೋಡಿ"><span class="pl" aria-hidden="true"></span></button></div>
  <figcaption><span>{bi(fm['title_en'], fm['title_kn'])}</span><span class="spec">{fm['spec']}</span></figcaption>
</figure>''')
    return f'''<section class="films" id="films-{scene}">
  <div class="fh"><div><div class="eyebrow"><span lang="en">FILMS FROM THE MODEL</span><span lang="kn">ಮಾದರಿಯಿಂದ ಚಿತ್ರೀಕರಣ</span></div>
    <h3>{bi(h_en, h_kn)}</h3></div>
    <p>{bi('Drone, gimbal and interior moves through the same 3D model. 11 seconds each.', 'ಅದೇ 3D ಮಾದರಿಯೊಳಗೆ ಡ್ರೋನ್, ಗಿಂಬಲ್ ಮತ್ತು ಒಳಾಂಗಣ ಚಲನೆ. ತಲಾ 11 ಸೆಕೆಂಡು.')}</p></div>
  <div class="reel">
    {"".join(cards)}
  </div>
</section>'''

def card(k_en, k_kn, h_en, h_kn, p_en, p_kn, cam, side=''):
    return f'''<div class="step{(' ' + side) if side else ''}"><article class="card">
<div class="k"><span lang="en">{k_en}</span><span lang="kn">{k_kn}</span></div>
<h3 class="hud-stage">{bi(h_en, h_kn)}</h3>
<p lang="en">{p_en}</p><p lang="kn">{p_kn}</p>
<div class="cam">{cam}</div></article></div>'''

def page(look):
    planColor = '#B03A2E' if look == 1 else '#D4AF37'
    scenes = {
        'resort': {'model': 'models/resort.glb', 'modelJs': '../models/resort.glb.js', 'sky': 'sky/resort.jpg', 'fog': fog.get('resort', '#cfc9c0'), 'fogNear': 260, 'fogFar': 2600,
                   'ground': 0.0, 'sunLabel': 'SUN 11° WSW', 'waterColor': 0x1b5c60, 'lampBoost': 1.0,
                   'path': [
                       {'p': 0.00, 'pos': [8, -110, 9], 'tgt': [0, 0, 3], 'fov': 36},
                       {'p': 0.16, 'pos': [22, -46, 8], 'tgt': [-2, -6, 1.5], 'fov': 40},
                       {'p': 0.33, 'pos': [12, -17.5, 1.9], 'tgt': [-16, -9, 1.2], 'fov': 46},
                       {'p': 0.50, 'pos': [-13, -11, 2.6], 'tgt': [4, 5, 3], 'fov': 44},
                       {'p': 0.66, 'pos': [-30, -30, 15], 'tgt': [2, 3, 2], 'fov': 40},
                       {'p': 0.83, 'pos': [19, -17, 4.6], 'tgt': [31, 1, 2.2], 'fov': 42},
                       {'p': 1.00, 'pos': [40, -40, 22], 'tgt': [0, 4, 0], 'fov': 38}]},
        'villa': {'model': 'models/villa.glb', 'modelJs': '../models/villa.glb.js', 'sky': 'sky/villa.jpg', 'fog': fog.get('villa', '#3b3644'), 'fogNear': 220, 'fogFar': 2400,
                  'ground': 0.0, 'sunLabel': 'SUN −2° · DUSK', 'waterColor': 0x0f4248, 'lampBoost': 1.2, 'glassOpacity': 0.28,
                  'path': [
                      {'p': 0.00, 'pos': [0, -70, 4], 'tgt': [0, 2, 3.5], 'fov': 34},
                      {'p': 0.20, 'pos': [6, -32, 2.0], 'tgt': [0, 2, 3.2], 'fov': 40},
                      {'p': 0.40, 'pos': [-9, -15, 1.7], 'tgt': [0, 4, 2.2], 'fov': 46},
                      {'p': 0.60, 'pos': [15.5, -16.5, 5.0], 'tgt': [13, -1.8, 5.6], 'fov': 44},
                      {'p': 0.80, 'pos': [-17, -11.5, 1.6], 'tgt': [12, -6, 1.0], 'fov': 48},
                      {'p': 1.00, 'pos': [34, -40, 20], 'tgt': [0, 2, 2], 'fov': 38}]},
        'home': {'model': 'models/home.glb', 'modelJs': '../models/home.glb.js', 'sky': 'sky/home.jpg', 'fog': fog.get('home', '#c9d3dd'), 'fogNear': 160, 'fogFar': 2000,
                 'ground': 0.0, 'sunLabel': 'SUN 27° ESE', 'waterColor': 0x1b5c60,
                 'path': [
                     {'p': 0.00, 'pos': [8.5, 4.6, 27], 'tgt': [6.0, 4.6, 0], 'fov': 40},
                     {'p': 0.12, 'pos': [22, 2.5, 18], 'tgt': [5.5, 4.6, 1], 'fov': 42},
                     {'p': 0.35, 'pos': [24, 0.5, 12], 'tgt': [5.5, 4.6, 2.5], 'fov': 40},
                     {'p': 0.60, 'pos': [23, 8.5, 9], 'tgt': [5.5, 4.6, 3.5], 'fov': 40},
                     {'p': 0.86, 'pos': [20.6, 1.8, 1.7], 'tgt': [9.1, 5.2, 3.4], 'fov': 50},
                     {'p': 1.00, 'pos': [19.8, 6.5, 1.7], 'tgt': [9.1, 4.6, 3.6], 'fov': 50}],
                 'build': {'planEnd': 0.10, 'planZ': 0.03, 'planColor': planColor, 'sheetColor': '#F4F1EB' if look == 1 else '#15130f',
                           'planLabel': bi('00 — PLAN', '00 — ನಕ್ಷೆ'),
                           'stages': [
                               {'a': .10, 'b': .17, 'groups': ['b01'], 'label': bi('01 — PLINTH 1′6″', '01 — ಪ್ಲಿಂತ್ 1′6″')},
                               {'a': .17, 'b': .29, 'groups': ['b02'], 'label': bi('02 — GROUND-FLOOR WALLS · 9″ OUTER, 4½″ INNER', '02 — ನೆಲ ಅಂತಸ್ತಿನ ಗೋಡೆಗಳು · 9″ ಹೊರಗೋಡೆ, 4½″ ಒಳಗೋಡೆ')},
                               {'a': .29, 'b': .35, 'groups': ['b03'], 'label': bi('03 — FIRST-FLOOR SLAB · STAIR · VOID', '03 — ಮೊದಲ ಅಂತಸ್ತಿನ ಸ್ಲ್ಯಾಬ್ · ಮೆಟ್ಟಿಲು · ತೆರೆದ ಜಾಗ')},
                               {'a': .35, 'b': .46, 'groups': ['b04'], 'label': bi('04 — FIRST-FLOOR WALLS · GALLERY', '04 — ಮೊದಲ ಅಂತಸ್ತಿನ ಗೋಡೆಗಳು · ಗ್ಯಾಲರಿ')},
                               {'a': .46, 'b': .52, 'groups': ['b05'], 'label': bi('05 — ROOF SLAB · STAIR TO TERRACE', '05 — ಛಾವಣಿ ಸ್ಲ್ಯಾಬ್ · ತಾರಸಿಗೆ ಮೆಟ್ಟಿಲು')},
                               {'a': .52, 'b': .60, 'groups': ['b06'], 'label': bi('06 — PARAPET · MUMTY · TANK SW', '06 — ಪ್ಯಾರಪೆಟ್ · ಮಮ್ಟಿ · ನೈಋತ್ಯದಲ್ಲಿ ಟ್ಯಾಂಕ್')},
                               {'a': .60, 'b': .68, 'groups': ['b07'], 'label': bi('07 — BRICK JALI, EAST BALCONY', '07 — ಇಟ್ಟಿಗೆ ಜಾಲಿ, ಪೂರ್ವ ಬಾಲ್ಕನಿ')},
                               {'a': .68, 'b': .76, 'groups': ['b08', 'b08_glass', 'b11', 'b11_veg', 'b11_lamp'], 'label': bi('08 — WINDOWS, DOORS, INTERIORS', '08 — ಕಿಟಕಿ, ಬಾಗಿಲು, ಒಳಾಂಗಣ')},
                               {'a': .76, 'b': .83, 'groups': ['b09', 'b09_veg'], 'label': bi('09 — SOLAR AND TERRACE GARDEN', '09 — ಸೌರ ಫಲಕ ಮತ್ತು ತಾರಸಿ ತೋಟ')},
                               {'a': .83, 'b': .90, 'groups': ['b10', 'b10_glass', 'b10_veg'], 'label': bi('10 — COMPOUND, NE GARDEN, PARKING SE', '10 — ಕಾಂಪೌಂಡ್, ಈಶಾನ್ಯ ತೋಟ, ಆಗ್ನೇಯ ವಾಹನ ನಿಲುಗಡೆ')}]}},
    }
    PLAN = json.load(open(f'{ROOT}/pbr/plan_gf.json'))
    for k, sc_ in scenes.items():
        sc_['pbr'] = PBR.get(k)
        sc_['exposure'] = {'resort': 1.0, 'villa': 1.0, 'home': 1.0}[k]
        sc_['skyGain'] = {'resort': 0.42, 'villa': 1.0, 'home': 0.7}[k]   # sky picture level against the baked exposure
    scenes['home']['build']['planRects'] = PLAN
    hero_img = 'img/resort_edge.webp' if 'resort_edge' in have else ''
    other = 'look-2.html' if look == 1 else 'index.html'
    return f'''<!DOCTYPE html>
<html lang="en" data-lang="en" data-look="{look}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>J V Visual Studio — Spaces in 3D</title>
<meta name="description" content="3D visualisation studio in Karnataka. Scroll to watch the plan become the building.">
<meta name="theme-color" content="#F4F1EB">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%23F4F1EB'/%3E%3Cpath d='M10 40 L32 16 L54 40' fill='none' stroke='%231A1009' stroke-width='4' stroke-linejoin='round'/%3E%3Cpath d='M18 40v10h28V40' fill='none' stroke='%23B03A2E' stroke-width='4' stroke-linejoin='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Manrope:wght@400;500;600&family=Noto+Sans+Kannada:wght@400;500;600&family=Noto+Serif+Kannada:wght@500;600&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/site.css">
<script type="importmap">{{"imports":{{"three":"./lib/three.module.min.js","three/addons/":"./lib/addons/"}}}}</script>
<script>window.JV_SCENES = {json.dumps(scenes, ensure_ascii=False)}; window.JV_LIB = {json.dumps(LIBJS)}; window.JV_PLANT_MATS = {json.dumps(PLANT_MATS)};</script>
</head>
<body>
<div id="stage" aria-hidden="true"></div>

<header class="topbar">
  <a class="brand" href="#top" aria-label="J V Visual Studio, back to top">
    <svg width="28" height="28" viewBox="0 0 64 64" aria-hidden="true"><path d="M10 40 L32 16 L54 40" fill="none" stroke="#1A1009" stroke-width="5" stroke-linejoin="round"/><path d="M18 40v10h28V40" fill="none" stroke="#B03A2E" stroke-width="5" stroke-linejoin="round"/></svg>
    <b>J V VISUAL STUDIO</b><small>{bi('3D SPACES', '3D ಸ್ಥಳಗಳು')}</small>
  </a>
  <div class="seg" role="group" aria-label="Language / ಭಾಷೆ">
    <button type="button" data-setlang="en" lang="en" aria-pressed="true">EN</button>
    <button type="button" data-setlang="kn" lang="kn" aria-pressed="false">ಕನ್ನಡ</button>
  </div>
  <button type="button" class="sound" id="soundBtn" aria-pressed="false" aria-label="Sound on or off / ಧ್ವನಿ">
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor"/><path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
    <span class="bars" aria-hidden="true"><i></i><i></i><i></i></span><span class="lbl">{bi('SOUND', 'ಧ್ವನಿ')}</span>
  </button>
</header>
<div class="progress" aria-hidden="true"></div>

<div class="hud" id="hud" aria-hidden="true">
  <div class="l"><span id="hudChapter"></span><span class="stage-label" id="hudStage"></span><span class="bar" id="hudBar"><i></i></span></div>
  <div class="r" style="text-align:right;display:grid;gap:4px"><span id="hudCam"></span><span class="loader" id="hudLoad" hidden></span></div>
</div>
<div class="hud-tools" id="tools"><button type="button" class="tool" id="orbitBtn" aria-pressed="false">⟳ {bi('EXPLORE IN 3D', '3D ಯಲ್ಲಿ ಅನ್ವೇಷಿಸಿ')}</button></div>

<nav class="lookswitch" aria-label="Preview looks">
  <a href="index.html"{' aria-current="page"' if look == 1 else ''}>LOOK 1 · LIGHT</a>
  <a href="look-2.html"{' aria-current="page"' if look == 2 else ''}>LOOK 2 · DARK 3D</a>
</nav>

<main id="top">
<section class="hero" style="background-image:url('{hero_img}')">
  <div class="meta">{bi('INFINITY EDGE · BOULDER-HILL RESORT', 'ಇನ್ಫಿನಿಟಿ ಅಂಚು · ಬಂಡೆಬೆಟ್ಟದ ರೆಸಾರ್ಟ್')}<br>{SPEC}<br>{CONCEPT}</div>
  <div class="wrap" style="width:100%">
    <div class="eyebrow"><span lang="en">CHINTAMANI · BENGALURU · BHARAT</span><span lang="kn">ಚಿಂತಾಮಣಿ · ಬೆಂಗಳೂರು · ಭಾರತ</span></div>
    <h1>{bi('Before the foundation,<br><span class="ac">comes the vision.</span>', 'ಅಡಿಪಾಯಕ್ಕೂ ಮೊದಲು,<br><span class="ac">ಕಲ್ಪನೆಯ ದರ್ಶನ.</span>')}</h1>
    <p class="lead" lang="en">Three-dimensional visualisation rooted in Vastu, sacred geometry, and the timeless design principles of Bharat.</p>
    <p class="lead" lang="kn">ವಾಸ್ತು, ಪವಿತ್ರ ಜ್ಯಾಮಿತಿ ಮತ್ತು ಭಾರತದ ಶಾಶ್ವತ ವಿನ್ಯಾಸ ತತ್ವಗಳಲ್ಲಿ ಬೇರೂರಿದ ತ್ರಿ-ಆಯಾಮದ (3D) ದೃಶ್ಯೀಕರಣ.</p>
    <div class="hero-row">
      <a class="btn solid" href="#ch-resort">{bi('Scroll the spaces ↓', 'ಸ್ಥಳಗಳನ್ನು ಸ್ಕ್ರಾಲ್ ಮಾಡಿ ↓')}</a>
      <a class="btn" href="#contact">{bi('Begin your project', 'ನಿಮ್ಮ ಯೋಜನೆ ಆರಂಭಿಸಿ')}</a>
    </div>
  </div>
</section>

<section class="paper" id="concepts">
  <div class="wrap concepts-head">
    <div class="eyebrow"><span lang="en">PORTFOLIO · STUDIO CONCEPTS</span><span lang="kn">ಪೋರ್ಟ್‌ಫೋಲಿಯೋ · ಸ್ಟುಡಿಯೋ ಪರಿಕಲ್ಪನೆಗಳು</span>{DRAFT}</div>
    <h2>{bi('Three spaces, built in 3D<br><span class="ac">before a single brick.</span>', 'ಒಂದು ಇಟ್ಟಿಗೆ ಇಡುವ ಮೊದಲೇ<br><span class="ac">3D ಯಲ್ಲಿ ಕಟ್ಟಿದ ಮೂರು ಸ್ಥಳಗಳು.</span>')}</h2>
    <p class="lead" lang="en">A resort, a private villa and a 30 × 40 home. Each one is a real-scale 3D model: scroll and the camera moves through it; tap Explore in 3D to look around yourself.</p>
    <p class="lead" lang="kn">ಒಂದು ರೆಸಾರ್ಟ್, ಒಂದು ಖಾಸಗಿ ವಿಲ್ಲಾ ಮತ್ತು ಒಂದು 30 × 40 ಮನೆ. ಪ್ರತಿಯೊಂದೂ ನಿಜ ಅಳತೆಯ 3D ಮಾದರಿ: ಸ್ಕ್ರಾಲ್ ಮಾಡಿದರೆ ಕ್ಯಾಮೆರಾ ಅದರೊಳಗೆ ಸಾಗುತ್ತದೆ; ನೀವೇ ಸುತ್ತಲೂ ನೋಡಲು ‘3D ಯಲ್ಲಿ ಅನ್ವೇಷಿಸಿ’ ಒತ್ತಿ.</p>
    <p class="note" lang="en">Concept designs made by the studio to show the process. They are not client projects. Enquire for full portfolio.</p>
    <p class="note" lang="kn">ಪ್ರಕ್ರಿಯೆಯನ್ನು ತೋರಿಸಲು ಸ್ಟುಡಿಯೋ ಮಾಡಿದ ಪರಿಕಲ್ಪನಾ ವಿನ್ಯಾಸಗಳು. ಇವು ಗ್ರಾಹಕರ ಯೋಜನೆಗಳಲ್ಲ. ಪೂರ್ಣ ಪೋರ್ಟ್‌ಫೋಲಿಯೋಗಾಗಿ ವಿಚಾರಿಸಿ.</p>
    <div class="chips">
      <a class="chip" href="#ch-resort"><b>01</b>{bi('Resort + pool villas', 'ರೆಸಾರ್ಟ್ + ಪೂಲ್ ವಿಲ್ಲಾಗಳು')}</a>
      <a class="chip" href="#ch-villa"><b>02</b>{bi('Luxury private villa', 'ಐಷಾರಾಮಿ ಖಾಸಗಿ ವಿಲ್ಲಾ')}</a>
      <a class="chip" href="#ch-home"><b>03</b>{bi('Residential duplex', 'ವಸತಿ ಡ್ಯೂಪ್ಲೆಕ್ಸ್')}</a>
    </div>
  </div>
</section>

<!-- 01 RESORT -->
<section class="chapter" id="ch-resort">
  <span class="hud-title" hidden>01 · {bi('BOULDER-HILL RESORT', 'ಬಂಡೆಬೆಟ್ಟದ ರೆಸಾರ್ಟ್')}</span>
  <div class="ch-head"><div class="wrap ch-head-grid">
    <div class="ch-num" aria-hidden="true">01</div>
    <div>
      <div class="eyebrow"><span lang="en">RESORT + POOL VILLAS</span><span lang="kn">ರೆಸಾರ್ಟ್ + ಪೂಲ್ ವಿಲ್ಲಾಗಳು</span>{DRAFT}</div>
      <h2>{bi('Boulder-Hill <span class="ac">Resort</span>', 'ಬಂಡೆಬೆಟ್ಟದ <span class="ac">ರೆಸಾರ್ಟ್</span>')}</h2>
      <p class="lead" lang="en">A clubhouse, a 30 m infinity pool and six pool villas on a granite ridge, modelled on the scrub hills of the Kolar plateau.</p>
      <p class="lead" lang="kn">ಕೋಲಾರ ಪ್ರಸ್ಥಭೂಮಿಯ ಪೊದೆ ಬೆಟ್ಟಗಳ ಮಾದರಿಯಲ್ಲಿ, ಗ್ರಾನೈಟ್ ಬೆಟ್ಟದ ಅಂಚಿನಲ್ಲಿ ಕ್ಲಬ್‌ಹೌಸ್, 30 ಮೀ ಇನ್ಫಿನಿಟಿ ಈಜುಕೊಳ ಮತ್ತು ಆರು ಪೂಲ್ ವಿಲ್ಲಾಗಳು.</p>
      <div class="concept-tag">{CONCEPT}</div>
      <div class="facts"><span>{bi('Clubhouse roof 38 × 19 m', 'ಕ್ಲಬ್‌ಹೌಸ್ ಛಾವಣಿ 38 × 19 ಮೀ')}</span><span>{bi('Pool 30 × 8.3 m', 'ಈಜುಕೊಳ 30 × 8.3 ಮೀ')}</span><span>{bi('6 villas · 9 × 7 m', '6 ವಿಲ್ಲಾಗಳು · 9 × 7 ಮೀ')}</span><span>{bi('Terrace drop 3.2 m', 'ಮೆಟ್ಟಿಲು ಇಳಿಜಾರು 3.2 ಮೀ')}</span></div>
    </div>
  </div></div>
  <div class="track" data-track="resort">
    {card('01 / 04', '01 / 04', 'Arrival over the valley', 'ಕಣಿವೆಯ ಮೇಲಿಂದ ಆಗಮನ',
          'The site steps down to a lower garden, so the pool edge meets the hills.',
          'ನಿವೇಶನ ಕೆಳಗಿನ ತೋಟಕ್ಕೆ ಮೆಟ್ಟಿಲಾಗಿ ಇಳಿಯುತ್ತದೆ; ಹಾಗಾಗಿ ಈಜುಕೊಳದ ಅಂಚು ಬೆಟ್ಟಗಳನ್ನು ಸೇರುತ್ತದೆ.', 'LOWER TERRACE −3.2 m · HILLS 0.9–1.7 km')}
    {card('02 / 04', '02 / 04', '30 m infinity pool', '30 ಮೀ ಇನ್ಫಿನಿಟಿ ಈಜುಕೊಳ',
          'Water held to the brim on the valley side, with a granite catch trough below.',
          'ಕಣಿವೆಯ ಬದಿಯಲ್ಲಿ ಅಂಚಿನವರೆಗೂ ತುಂಬಿದ ನೀರು; ಕೆಳಗೆ ಗ್ರಾನೈಟ್ ಹಿಡಿಕೆ ತೊಟ್ಟಿ.', 'POOL 30.0 × 8.3 m · DEPTH 1.4 m', 'r')}
    {card('03 / 04', '03 / 04', 'Clubhouse pavilion', 'ಕ್ಲಬ್‌ಹೌಸ್ ಮಂಟಪ',
          'A 38 m cantilevered roof on bronze columns, exposed brick wings and a teak soffit.',
          'ಕಂಚಿನ ಕಂಬಗಳ ಮೇಲೆ 38 ಮೀ ಚಾಚಿದ ಛಾವಣಿ, ತೆರೆದ ಇಟ್ಟಿಗೆಯ ಪಾರ್ಶ್ವಗಳು ಮತ್ತು ತೇಗದ ಒಳಛಾವಣಿ.', 'ROOF +5.45 m · COLUMNS Ø 260 mm @ 6.5 m')}
    {card('04 / 04', '04 / 04', 'Pool villas', 'ಪೂಲ್ ವಿಲ್ಲಾಗಳು',
          'Six 9 × 7 m villas, each with a plunge pool, deck and teak privacy screen.',
          'ಆರು 9 × 7 ಮೀ ವಿಲ್ಲಾಗಳು — ಪ್ರತಿಯೊಂದಕ್ಕೂ ಪುಟ್ಟ ಈಜುಕೊಳ, ಡೆಕ್ ಮತ್ತು ತೇಗದ ಮರೆಪರದೆ.', 'PLUNGE POOL 6.5 × 3.4 m · SCREEN 16 SLATS', 'r')}
    <div class="step"></div>
  </div>
</section>
{films('resort', 'Resort, golden hour', 'ರೆಸಾರ್ಟ್, ಸಂಜೆಯ ಹೊಂಬೆಳಕು')}
<section class="gallery">
  <div class="gh"><div><div class="eyebrow"><span lang="en">RENDERS</span><span lang="kn">ರೆಂಡರ್‌ಗಳು</span></div>
    <h3 style="margin-top:10px">{bi('Golden hour to dusk — drag the line', 'ಹೊಂಬೆಳಕಿನಿಂದ ಮುಸ್ಸಂಜೆಗೆ — ಗೆರೆಯನ್ನು ಎಳೆಯಿರಿ')}</h3></div><p>{SPEC}</p></div>
  <div class="compare"><div class="cmp">
    <img src="img/resort_hero.webp" alt="Resort clubhouse and infinity pool at golden hour" width="1600" height="900">
    <img class="top" src="img/resort_hero_dusk.webp" alt="The same view at dusk with the lights on" width="1600" height="900">
    <span class="handle" aria-hidden="true"></span>
    <span class="lab a">{bi('GOLDEN HOUR', 'ಹೊಂಬೆಳಕು')}</span><span class="lab b">{bi('DUSK', 'ಮುಸ್ಸಂಜೆ')}</span>
    <input type="range" min="0" max="100" value="50" id="cmpResort" aria-label="Compare golden hour and dusk">
  </div></div>
  <div class="strip">
    {img('resort_edge', 'Infinity edge over the valley', 'ಕಣಿವೆಯ ಮೇಲೆ ಇನ್ಫಿನಿಟಿ ಅಂಚು', 'CAM 24 mm · EYE 1.55 m')}
    {img('resort_villa', 'Pool villa, golden hour', 'ಪೂಲ್ ವಿಲ್ಲಾ, ಹೊಂಬೆಳಕು', 'CAM 26 mm · EYE 3.2 m')}
    {img('resort_villa_dusk', 'Pool villa, dusk', 'ಪೂಲ್ ವಿಲ್ಲಾ, ಮುಸ್ಸಂಜೆ', 'CAM 26 mm · EYE 3.2 m')}
  </div>
</section>

<!-- 02 VILLA -->
<section class="chapter" id="ch-villa">
  <span class="hud-title" hidden>02 · {bi('THE CANTILEVER VILLA', 'ಕ್ಯಾಂಟಿಲಿವರ್ ವಿಲ್ಲಾ')}</span>
  <div class="ch-head"><div class="wrap ch-head-grid">
    <div class="ch-num" aria-hidden="true">02</div>
    <div>
      <div class="eyebrow"><span lang="en">LUXURY PRIVATE VILLA</span><span lang="kn">ಐಷಾರಾಮಿ ಖಾಸಗಿ ವಿಲ್ಲಾ</span>{DRAFT}</div>
      <h2>{bi('The Cantilever <span class="ac">Villa</span>', 'ಕ್ಯಾಂಟಿಲಿವರ್ <span class="ac">ವಿಲ್ಲಾ</span>')}</h2>
      <p class="lead" lang="en">A private villa with a glass living pavilion, a floating upper floor and a 22 m lap pool. Shown at dusk with the house lit from inside.</p>
      <p class="lead" lang="kn">ಗಾಜಿನ ವಾಸದ ಮಂಟಪ, ತೇಲುವಂತಿರುವ ಮೇಲಂತಸ್ತು ಮತ್ತು 22 ಮೀ ಲ್ಯಾಪ್ ಈಜುಕೊಳ ಇರುವ ಖಾಸಗಿ ವಿಲ್ಲಾ. ಒಳಗಿನ ದೀಪಗಳು ಬೆಳಗಿದ ಮುಸ್ಸಂಜೆಯ ನೋಟ.</p>
      <div class="concept-tag">{CONCEPT}</div>
      <div class="facts"><span>{bi('G+1 · plinth 0.6 m', 'G+1 · ಪ್ಲಿಂತ್ 0.6 ಮೀ')}</span><span>{bi('Cantilever 3.5 m', 'ಚಾಚು 3.5 ಮೀ')}</span><span>{bi('Lap pool 22 × 3.5 m', 'ಲ್ಯಾಪ್ ಈಜುಕೊಳ 22 × 3.5 ಮೀ')}</span><span>{bi('Brick tower 7.8 m', 'ಇಟ್ಟಿಗೆ ಗೋಪುರ 7.8 ಮೀ')}</span></div>
    </div>
  </div></div>
  <div class="track" data-track="villa">
    {card('01 / 04', '01 / 04', 'Glass living pavilion', 'ಗಾಜಿನ ವಾಸದ ಮಂಟಪ',
          'Living and dining open fully to the deck along a 22 m wall of glass.',
          'ವಾಸ ಮತ್ತು ಊಟದ ಸ್ಥಳ 22 ಮೀ ಉದ್ದದ ಗಾಜಿನ ಗೋಡೆಯುದ್ದಕ್ಕೂ ಡೆಕ್‌ಗೆ ಸಂಪೂರ್ಣ ತೆರೆದುಕೊಳ್ಳುತ್ತದೆ.', 'GLAZING 22.0 × 3.3 m · 6 BAYS')}
    {card('02 / 04', '02 / 04', '3.5 m cantilever', '3.5 ಮೀ ಚಾಚು',
          'The bedroom floor reaches past the glass and shades it from high sun, with teak fins on the window.',
          'ಮಲಗುವ ಕೋಣೆಗಳ ಅಂತಸ್ತು ಗಾಜಿನ ಆಚೆಗೂ ಚಾಚಿಕೊಂಡು ನೆತ್ತಿಯ ಬಿಸಿಲಿನಿಂದ ನೆರಳು ನೀಡುತ್ತದೆ; ಕಿಟಕಿಗೆ ತೇಗದ ಪಟ್ಟಿಗಳು.', 'UPPER FLOOR 23 × 14 m · 26 TEAK FINS', 'r')}
    {card('03 / 04', '03 / 04', 'Brick tower with jali', 'ಜಾಲಿಯಿರುವ ಇಟ್ಟಿಗೆ ಗೋಪುರ',
          'Two storeys of exposed brick. The jali lets light and air through, and glows at night.',
          'ಎರಡು ಅಂತಸ್ತಿನ ತೆರೆದ ಇಟ್ಟಿಗೆ. ಜಾಲಿ ಬೆಳಕು ಮತ್ತು ಗಾಳಿಯನ್ನು ಒಳಬಿಡುತ್ತದೆ, ರಾತ್ರಿ ಹೊಳೆಯುತ್ತದೆ.', 'JALI 4.6 × 3.75 m · 230 × 75 mm BRICK')}
    {card('04 / 04', '04 / 04', '22 m lap pool', '22 ಮೀ ಲ್ಯಾಪ್ ಈಜುಕೊಳ',
          'Set at plinth level along the full facade, with a teak deck and a fire bowl.',
          'ಪೂರ್ತಿ ಮುಂಭಾಗದುದ್ದಕ್ಕೂ ಪ್ಲಿಂತ್ ಮಟ್ಟದಲ್ಲಿ, ತೇಗದ ಡೆಕ್ ಮತ್ತು ಅಗ್ನಿಕುಂಡದೊಂದಿಗೆ.', 'POOL 22.0 × 3.5 m · DEPTH 1.4 m', 'r')}
    <div class="step"></div>
  </div>
</section>
{films('villa', 'Villa, dusk', 'ವಿಲ್ಲಾ, ಮುಸ್ಸಂಜೆ')}
<section class="fade">
  <div class="pin">
    <div class="cap"><span class="eyebrow" style="color:var(--ch-accent)"><span lang="en">DAY TO DUSK — KEEP SCROLLING</span><span lang="kn">ಹಗಲಿನಿಂದ ಮುಸ್ಸಂಜೆಗೆ — ಸ್ಕ್ರಾಲ್ ಮುಂದುವರಿಸಿ</span></span><span class="clock">SUN 38°</span></div>
    <div class="frame">
      <img src="img/villa_front_day.webp" alt="The villa in afternoon sun" width="1600" height="900">
      <img class="dusk" src="img/villa_front_dusk.webp" alt="The same view at dusk" width="1600" height="900">
    </div>
    <div class="cap"><span>{bi('Same camera, two skies: sun 38° in the south-west, then 2° below the horizon.', 'ಒಂದೇ ಕ್ಯಾಮೆರಾ, ಎರಡು ಆಕಾಶ: ನೈಋತ್ಯದಲ್ಲಿ 38° ಸೂರ್ಯ, ನಂತರ ದಿಗಂತದ 2° ಕೆಳಗೆ.')}</span><span class="spec" style="font-family:var(--mono);font-size:10px">{SPEC}</span></div>
  </div>
</section>
<section class="gallery">
  <div class="strip">
    {img('villa_pool', 'Along the lap pool', 'ಲ್ಯಾಪ್ ಈಜುಕೊಳದುದ್ದಕ್ಕೂ', 'CAM 22 mm · EYE 1.55 m')}
    {img('villa_aerial_dusk', 'Aerial view at dusk', 'ಮುಸ್ಸಂಜೆಯ ವೈಮಾನಿಕ ನೋಟ', 'CAM 30 mm · EYE 20 m')}
  </div>
</section>

<!-- 03 HOME -->
<section class="chapter" id="ch-home">
  <span class="hud-title" hidden>03 · {bi('VASTU-LED DUPLEX 30 × 40', 'ವಾಸ್ತು ಆಧಾರಿತ ಡ್ಯೂಪ್ಲೆಕ್ಸ್ 30 × 40')}</span>
  <div class="ch-head"><div class="wrap ch-head-grid">
    <div class="ch-num" aria-hidden="true">03</div>
    <div>
      <div class="eyebrow"><span lang="en">RESIDENTIAL</span><span lang="kn">ವಸತಿ</span>{DRAFT}</div>
      <h2>{bi('Vastu-led duplex, <span class="ac">30 × 40 ft</span>', 'ವಾಸ್ತು ಆಧಾರಿತ ಡ್ಯೂಪ್ಲೆಕ್ಸ್, <span class="ac">30 × 40 ಅಡಿ</span>')}</h2>
      <p class="lead" lang="en">An east-facing 2BHK in exposed brick. Scroll to watch the plan become the building.</p>
      <p class="lead" lang="kn">ತೆರೆದ ಇಟ್ಟಿಗೆಯ ಪೂರ್ವಾಭಿಮುಖ 2BHK. ನಕ್ಷೆ ಕಟ್ಟಡವಾಗುವುದನ್ನು ಸ್ಕ್ರಾಲ್ ಮಾಡಿ ನೋಡಿ.</p>
      <div class="concept-tag">{CONCEPT}</div>
      <div class="facts"><span>{bi('Plot 30 × 40 ft · road east', 'ನಿವೇಶನ 30 × 40 ಅಡಿ · ಪೂರ್ವಕ್ಕೆ ರಸ್ತೆ')}</span><span>{bi('Building 28 × 25 ft · G+1', 'ಕಟ್ಟಡ 28 × 25 ಅಡಿ · G+1')}</span><span>{bi('Floor to floor 10′0″', 'ಅಂತಸ್ತಿನ ಎತ್ತರ 10′0″')}</span><span>{bi('Kitchen SE · pooja NE · bedroom SW', 'ಅಡುಗೆ ಮನೆ ಆಗ್ನೇಯ · ದೇವರ ಕೋಣೆ ಈಶಾನ್ಯ · ಮಲಗುವ ಕೋಣೆ ನೈಋತ್ಯ')}</span></div>
    </div>
  </div></div>
  <div class="track" data-track="home">
    {card('PLAN', 'ನಕ್ಷೆ', 'From the plan', 'ನಕ್ಷೆಯಿಂದ',
          'The ground-floor dimension chain closes at 28′0″ by 25′0″ inside 2 ft, 2 ft, 3 ft and 10 ft setbacks.',
          'ನೆಲ ಅಂತಸ್ತಿನ ಅಳತೆ ಸರಪಳಿ 2, 2, 3 ಮತ್ತು 10 ಅಡಿ ಸೆಟ್‌ಬ್ಯಾಕ್‌ಗಳ ಒಳಗೆ 28′0″ × 25′0″ ಕ್ಕೆ ಸರಿಯಾಗಿ ಮುಚ್ಚುತ್ತದೆ.', "0′9″ + 10′3″ + 0′4½″ + 7′6″ + 0′4½″ + 8′0″ + 0′9″ = 28′0″")}
    {card('STRUCTURE', 'ರಚನೆ', 'Walls and slabs', 'ಗೋಡೆಗಳು ಮತ್ತು ಸ್ಲ್ಯಾಬ್‌ಗಳು',
          'Nine-inch brick walls rise in two storeys, with a 1′6″ plinth and 10′0″ floor to floor.',
          'ಒಂಬತ್ತು ಇಂಚಿನ ಇಟ್ಟಿಗೆ ಗೋಡೆಗಳು ಎರಡು ಅಂತಸ್ತುಗಳಲ್ಲಿ ಏರುತ್ತವೆ; 1′6″ ಪ್ಲಿಂತ್, 10′0″ ಅಂತಸ್ತಿನ ಎತ್ತರ.', 'WALLS 9″ / 4½″ · SLAB 150 mm (INDICATIVE)', 'r')}
    {card('SKIN', 'ಹೊದಿಕೆ', 'Jali, openings, terrace', 'ಜಾಲಿ, ಕಿಟಕಿ-ಬಾಗಿಲು, ತಾರಸಿ',
          'A full-height brick jali screens the east balcony. The terrace carries the mumty, the tank in the south-west and a solar array.',
          'ಪೂರ್ವ ಬಾಲ್ಕನಿಗೆ ಪೂರ್ಣ ಎತ್ತರದ ಇಟ್ಟಿಗೆ ಜಾಲಿಯ ಪರದೆ. ತಾರಸಿಯಲ್ಲಿ ಮಮ್ಟಿ, ನೈಋತ್ಯದಲ್ಲಿ ಟ್ಯಾಂಕ್ ಮತ್ತು ಸೌರ ಫಲಕಗಳು.', 'SOLAR 6 PANELS, NW · TILT 13° SOUTH')}
    {card('STREET', 'ರಸ್ತೆ', 'Seen from the road', 'ರಸ್ತೆಯಿಂದ ಕಂಡಂತೆ',
          'Parking in the south-east setback, a small garden kept open in the north-east, and the main door in the north half of the east wall.',
          'ಆಗ್ನೇಯ ಸೆಟ್‌ಬ್ಯಾಕ್‌ನಲ್ಲಿ ವಾಹನ ನಿಲುಗಡೆ, ಈಶಾನ್ಯದಲ್ಲಿ ತೆರೆದಿಟ್ಟ ಪುಟ್ಟ ತೋಟ, ಪೂರ್ವ ಗೋಡೆಯ ಉತ್ತರಾರ್ಧದಲ್ಲಿ ಮುಖ್ಯ ದ್ವಾರ.', 'EYE 1.7 m · ACROSS THE ROAD', 'r')}
    <div class="step"></div>
  </div>
</section>
{films('home', 'Duplex, morning', 'ಡ್ಯೂಪ್ಲೆಕ್ಸ್, ಬೆಳಗಿನ ಹೊತ್ತು')}
<section class="gallery">
  <div class="gh"><div><div class="eyebrow"><span lang="en">RENDERS</span><span lang="kn">ರೆಂಡರ್‌ಗಳು</span></div></div><p>{SPEC}</p></div>
  <div class="strip">
    {img('home_street', 'East elevation from across the road', 'ರಸ್ತೆಯ ಆಚೆಯಿಂದ ಪೂರ್ವ ಮುಂಭಾಗ', 'CAM 22 mm · EYE 1.6 m')}
    {img('home_aerial', 'Terrace, mumty and solar from the north-east', 'ಈಶಾನ್ಯದಿಂದ ತಾರಸಿ, ಮಮ್ಟಿ ಮತ್ತು ಸೌರ ಫಲಕ', 'CAM 26 mm · EYE 12.5 m')}
    {img('home_jali', 'Brick jali on the east balcony', 'ಪೂರ್ವ ಬಾಲ್ಕನಿಯ ಇಟ್ಟಿಗೆ ಜಾಲಿ', 'CAM 24 mm · EYE 4.9 m')}
  </div>
</section>

<section class="paper alt" id="philosophy">
  <div class="wrap">
    <div class="eyebrow"><span lang="en">OUR DESIGN PHILOSOPHY</span><span lang="kn">ನಮ್ಮ ವಿನ್ಯಾಸ ತತ್ವ</span></div>
    <blockquote lang="en">"We design and document buildings rooted in Bharat's timeless temple principles — blending Vastu, sacred geometry, and modern living."</blockquote>
    <blockquote lang="kn">"ಭಾರತದ ಶಾಶ್ವತ ದೇವಾಲಯ ತತ್ವಗಳಲ್ಲಿ ಬೇರೂರಿದ ಕಟ್ಟಡಗಳನ್ನು ನಾವು ವಿನ್ಯಾಸಗೊಳಿಸಿ ದಾಖಲಿಸುತ್ತೇವೆ — ವಾಸ್ತು, ಪವಿತ್ರ ಜ್ಯಾಮಿತಿ ಮತ್ತು ಆಧುನಿಕ ಜೀವನವನ್ನು ಬೆಸೆಯುತ್ತಾ."</blockquote>
    <p class="lead" lang="en" style="margin-top:40px">At JV, we honour the sacred building wisdom of ancient Bharat while embracing contemporary innovation. Every structure we visualise harmonises cosmic energy with functional elegance. Every render we produce is not merely an image — it is a commitment to building with intention, informed by the Shilpa Shastras and Vastu Vidya that have shaped Bharatiya built heritage for over seven thousand years.</p>
    <p class="lead" lang="kn" style="margin-top:40px">ಜೆ ವಿ ಯಲ್ಲಿ ನಾವು ಪ್ರಾಚೀನ ಭಾರತದ ಪವಿತ್ರ ನಿರ್ಮಾಣ ಜ್ಞಾನವನ್ನು ಗೌರವಿಸುತ್ತಲೇ ಸಮಕಾಲೀನ ಹೊಸತನವನ್ನು ಅಳವಡಿಸಿಕೊಳ್ಳುತ್ತೇವೆ. ನಾವು ದೃಶ್ಯೀಕರಿಸುವ ಪ್ರತಿಯೊಂದು ಕಟ್ಟಡವೂ ವಿಶ್ವಶಕ್ತಿಯನ್ನು ಉಪಯುಕ್ತ ಸೊಬಗಿನೊಂದಿಗೆ ಸಮನ್ವಯಗೊಳಿಸುತ್ತದೆ. ನಾವು ತಯಾರಿಸುವ ಪ್ರತಿಯೊಂದು ರೆಂಡರ್ ಕೇವಲ ಚಿತ್ರವಲ್ಲ — ಏಳು ಸಾವಿರ ವರ್ಷಗಳಿಗೂ ಹೆಚ್ಚು ಕಾಲ ಭಾರತೀಯ ನಿರ್ಮಿತ ಪರಂಪರೆಯನ್ನು ರೂಪಿಸಿದ ಶಿಲ್ಪಶಾಸ್ತ್ರ ಮತ್ತು ವಾಸ್ತುವಿದ್ಯೆಯ ಮಾರ್ಗದರ್ಶನದಲ್ಲಿ, ಉದ್ದೇಶಪೂರ್ವಕವಾಗಿ ಕಟ್ಟುವ ಬದ್ಧತೆ ಅದು.</p>
  </div>
</section>

<section class="paper" id="services">
  <div class="wrap">
    <div class="eyebrow"><span lang="en">01 · WHAT WE DO</span><span lang="kn">01 · ನಮ್ಮ ಸೇವೆಗಳು</span></div>
    <h2>{bi('What we bring<br>to your project', 'ನಿಮ್ಮ ಯೋಜನೆಗೆ<br>ನಾವು ತರುವುದು')}</h2>
    <div class="grid3">
      <div class="svc"><span class="n">01</span><h3>{bi('3D Exterior Renders', '3D ಹೊರಾಂಗಣ ರೆಂಡರ್‌ಗಳು')}</h3><p lang="en">Photorealistic day and evening renders showing materials, light, landscape, and scale exactly as it will exist once built.</p><p lang="kn">ಕಟ್ಟಿದ ನಂತರ ಹೇಗೆ ಕಾಣುತ್ತದೋ ಹಾಗೆಯೇ — ಸಾಮಗ್ರಿ, ಬೆಳಕು, ಭೂದೃಶ್ಯ ಮತ್ತು ಅಳತೆಯನ್ನು ತೋರಿಸುವ ಹಗಲು ಮತ್ತು ಸಂಜೆಯ ಫೋಟೋರಿಯಲಿಸ್ಟಿಕ್ ರೆಂಡರ್‌ಗಳು.</p></div>
      <div class="svc"><span class="n">02</span><h3>{bi('Interior Visualisation', 'ಒಳಾಂಗಣ ದೃಶ್ಯೀಕರಣ')}</h3><p lang="en">Room-by-room renders with material palettes, furniture placement, and lighting — decisions made with clarity before construction begins.</p><p lang="kn">ಸಾಮಗ್ರಿ ಬಣ್ಣಗಳು, ಪೀಠೋಪಕರಣಗಳ ಜೋಡಣೆ ಮತ್ತು ಬೆಳಕಿನೊಂದಿಗೆ ಕೋಣೆ-ಕೋಣೆಯ ರೆಂಡರ್‌ಗಳು — ನಿರ್ಮಾಣ ಆರಂಭವಾಗುವ ಮೊದಲೇ ಸ್ಪಷ್ಟ ನಿರ್ಧಾರಗಳು.</p></div>
      <div class="svc"><span class="n">03</span><h3>{bi('Walkthrough Videos', 'ವಾಕ್‌ಥ್ರೂ ವೀಡಿಯೊಗಳು')}</h3><p lang="en">Cinematic fly-through animations that move through your building as if it already stands — presenting your project with complete conviction.</p><p lang="kn">ನಿಮ್ಮ ಕಟ್ಟಡ ಈಗಾಗಲೇ ನಿಂತಿದೆಯೇನೋ ಎಂಬಂತೆ ಅದರೊಳಗೆ ಸಾಗುವ ಸಿನಿಮೀಯ ಫ್ಲೈ-ಥ್ರೂ ಅನಿಮೇಷನ್‌ಗಳು — ನಿಮ್ಮ ಯೋಜನೆಯನ್ನು ಸಂಪೂರ್ಣ ವಿಶ್ವಾಸದಿಂದ ಪ್ರಸ್ತುತಪಡಿಸಲು.</p></div>
      <div class="svc"><span class="n">04</span><h3>{bi('Elevations &amp; Sections', 'ಎಲಿವೇಷನ್ ಮತ್ತು ಸೆಕ್ಷನ್‌ಗಳು')}</h3><p lang="en">Precision technical drawings produced to professional documentation standards, ready for contractor coordination.</p><p lang="kn">ವೃತ್ತಿಪರ ದಾಖಲಾತಿ ಮಾನದಂಡಗಳಿಗೆ ಅನುಗುಣವಾಗಿ ತಯಾರಿಸಿದ ನಿಖರ ತಾಂತ್ರಿಕ ನಕ್ಷೆಗಳು, ಗುತ್ತಿಗೆದಾರರೊಂದಿಗೆ ಸಮನ್ವಯಕ್ಕೆ ಸಿದ್ಧ.</p></div>
      <div class="svc"><span class="n">05</span><h3>{bi('AR Visualisation', 'AR ದೃಶ್ಯೀಕರಣ')}</h3><p lang="en">See your building placed on its actual plot, on your phone — experiencing scale and position before a foundation is dug.</p><p lang="kn">ನಿಮ್ಮ ಕಟ್ಟಡವನ್ನು ಅದರ ನಿಜವಾದ ನಿವೇಶನದ ಮೇಲೆ, ನಿಮ್ಮ ಫೋನಿನಲ್ಲೇ ನೋಡಿ — ಅಡಿಪಾಯ ತೋಡುವ ಮೊದಲೇ ಅಳತೆ ಮತ್ತು ಸ್ಥಾನದ ಅನುಭವ.</p></div>
      <div class="svc"><span class="n">06</span><h3>{bi('Solar &amp; Terrace Garden', 'ಸೌರ ಶಕ್ತಿ ಮತ್ತು ತಾರಸಿ ತೋಟ')}</h3><p lang="en">PM Surya Ghar Muft Bijili Yojana integration and terrace garden visualisation — net-zero power and living green spaces.</p><p lang="kn">ಪಿಎಂ ಸೂರ್ಯ ಘರ್ ಮುಫ್ತ್ ಬಿಜ್ಲಿ ಯೋಜನೆಯ ಅಳವಡಿಕೆ ಮತ್ತು ತಾರಸಿ ತೋಟದ ದೃಶ್ಯೀಕರಣ — ನಿವ್ವಳ-ಶೂನ್ಯ ವಿದ್ಯುತ್ ಮತ್ತು ಜೀವಂತ ಹಸಿರು ಸ್ಥಳಗಳು.</p></div>
    </div>
  </div>
</section>

<div class="ticker" aria-hidden="true"><div class="t">
  {''.join(f'<span lang="en">{w}</span><span lang="kn">{k}</span><span class="sep">·</span>' for w, k in [('Vastu Vidya', 'ವಾಸ್ತುವಿದ್ಯೆ'), ('Shilpa Shastra', 'ಶಿಲ್ಪಶಾಸ್ತ್ರ'), ('Sacred Geometry', 'ಪವಿತ್ರ ಜ್ಯಾಮಿತಿ'), ('Cosmic Proportion', 'ವಿಶ್ವ ಅನುಪಾತ'), ('Modern Precision', 'ಆಧುನಿಕ ನಿಖರತೆ')] * 2)}
</div></div>

<section class="paper alt" id="process">
  <div class="wrap">
    <div class="eyebrow"><span lang="en">02 · PROCESS</span><span lang="kn">02 · ಪ್ರಕ್ರಿಯೆ</span></div>
    <h2>{bi('From your drawing<br><span class="ac">to your vision</span>', 'ನಿಮ್ಮ ನಕ್ಷೆಯಿಂದ<br><span class="ac">ನಿಮ್ಮ ಕಲ್ಪನೆಯವರೆಗೆ</span>')}</h2>
    <div class="steps">
      <div class="stp"><span class="n">01</span><div><h4>{bi('Brief', 'ವಿವರ (ಬ್ರೀಫ್)')}</h4><p lang="en">Send your floor plans, elevation sketches, and material preferences. Hand-drawn plans work — a clear photo is enough. <em>Day 1.</em></p><p lang="kn">ನಿಮ್ಮ ನೆಲ ನಕ್ಷೆಗಳು, ಎಲಿವೇಷನ್ ರೇಖಾಚಿತ್ರಗಳು ಮತ್ತು ಸಾಮಗ್ರಿ ಆಯ್ಕೆಗಳನ್ನು ಕಳುಹಿಸಿ. ಕೈಯಲ್ಲಿ ಬರೆದ ನಕ್ಷೆಯೂ ಆಗುತ್ತದೆ — ಸ್ಪಷ್ಟವಾದ ಒಂದು ಫೋಟೋ ಸಾಕು. <em>ದಿನ 1.</em></p></div></div>
      <div class="stp"><span class="n">02</span><div><h4>{bi('Model', 'ಮಾದರಿ')}</h4><p lang="en">We build your home in 3D — walls, openings, materials, landscape. You get a base preview to confirm before rendering. <em>Days 2–3.</em></p><p lang="kn">ನಿಮ್ಮ ಮನೆಯನ್ನು 3D ಯಲ್ಲಿ ಕಟ್ಟುತ್ತೇವೆ — ಗೋಡೆಗಳು, ಕಿಟಕಿ-ಬಾಗಿಲುಗಳು, ಸಾಮಗ್ರಿಗಳು, ಭೂದೃಶ್ಯ. ರೆಂಡರ್ ಮಾಡುವ ಮೊದಲು ಖಚಿತಪಡಿಸಲು ಮೂಲ ಪೂರ್ವದರ್ಶನ ಸಿಗುತ್ತದೆ. <em>ದಿನ 2–3.</em></p></div></div>
      <div class="stp"><span class="n">03</span><div><h4>{bi('Render', 'ರೆಂಡರ್')}</h4><p lang="en">High-resolution renders at agreed light conditions. Two revision rounds included; further rounds quoted on request. <em>Days 3–5.</em></p><p lang="kn">ಒಪ್ಪಿದ ಬೆಳಕಿನ ಸ್ಥಿತಿಯಲ್ಲಿ ಹೈ-ರೆಸಲ್ಯೂಷನ್ ರೆಂಡರ್‌ಗಳು. ಎರಡು ತಿದ್ದುಪಡಿ ಸುತ್ತುಗಳು ಸೇರಿವೆ; ಹೆಚ್ಚಿನ ಸುತ್ತುಗಳಿಗೆ ಕೇಳಿದಾಗ ದರ ತಿಳಿಸಲಾಗುತ್ತದೆ. <em>ದಿನ 3–5.</em></p></div></div>
      <div class="stp"><span class="n">04</span><div><h4>{bi('Deliver', 'ಹಸ್ತಾಂತರ')}</h4><p lang="en">Full-resolution files via Google Drive or WhatsApp — print-ready TIFF and web JPEG. Commercial usage rights included. <em>Day 5–7.</em></p><p lang="kn">ಗೂಗಲ್ ಡ್ರೈವ್ ಅಥವಾ ವಾಟ್ಸಾಪ್ ಮೂಲಕ ಪೂರ್ಣ-ರೆಸಲ್ಯೂಷನ್ ಫೈಲ್‌ಗಳು — ಮುದ್ರಣಕ್ಕೆ ಸಿದ್ಧ TIFF ಮತ್ತು ವೆಬ್ JPEG. ವಾಣಿಜ್ಯ ಬಳಕೆಯ ಹಕ್ಕುಗಳು ಸೇರಿವೆ. <em>ದಿನ 5–7.</em></p></div></div>
    </div>
  </div>
</section>

<section class="paper" id="contact">
  <div class="wrap">
    <div class="eyebrow"><span lang="en">03 · CONTACT</span><span lang="kn">03 · ಸಂಪರ್ಕಿಸಿ</span></div>
    <h2>{bi('Begin your project<br>with <span class="ac">a conversation.</span>', 'ಒಂದು ಮಾತುಕತೆಯೊಂದಿಗೆ<br><span class="ac">ನಿಮ್ಮ ಯೋಜನೆ ಆರಂಭಿಸಿ.</span>')}</h2>
    <div class="contact">
      <div class="ci">
        <div>{bi('Location', 'ಸ್ಥಳ', 'div', 'lbl')}<span class="val">{bi('Chintamani, Karnataka — 563125', 'ಚಿಂತಾಮಣಿ, ಕರ್ನಾಟಕ — 563125')}</span></div>
        <div>{bi('Phone &amp; WhatsApp', 'ಫೋನ್ ಮತ್ತು ವಾಟ್ಸಾಪ್', 'div', 'lbl')}<a class="val" href="tel:+919353495972">+91 93534 95972</a><a class="val" href="https://wa.me/919353495972" target="_blank" rel="noopener">{bi('Message on WhatsApp', 'ವಾಟ್ಸಾಪ್‌ನಲ್ಲಿ ಸಂದೇಶ ಕಳುಹಿಸಿ')}</a></div>
        <div>{bi('Instagram', 'ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್', 'div', 'lbl')}<span class="val">@jvvisualstudio</span></div>
        <div>{bi('Parent Company', 'ಮಾತೃ ಸಂಸ್ಥೆ', 'div', 'lbl')}<span class="val">{bi('JV Studios · Chintamani', 'ಜೆ ವಿ ಸ್ಟುಡಿಯೋಸ್ · ಚಿಂತಾಮಣಿ')}</span></div>
      </div>
      <form id="enquiry" novalidate>
        <label for="f-name">{bi('Your Name', 'ನಿಮ್ಮ ಹೆಸರು')}<input id="f-name" name="name" type="text" autocomplete="name" placeholder="How shall we address you?" data-ph-en="How shall we address you?" data-ph-kn="ನಿಮ್ಮನ್ನು ಹೇಗೆ ಸಂಬೋಧಿಸಲಿ?"></label>
        <label for="f-type">{bi('Project Type', 'ಯೋಜನೆಯ ಪ್ರಕಾರ')}<input id="f-type" name="ptype" type="text" placeholder="Residential / Commercial / Other" data-ph-en="Residential / Commercial / Other" data-ph-kn="ವಸತಿ / ವಾಣಿಜ್ಯ / ಇತರೆ"></label>
        <label for="f-msg">{bi('Tell us about your project', 'ನಿಮ್ಮ ಯೋಜನೆಯ ಬಗ್ಗೆ ತಿಳಿಸಿ')}<textarea id="f-msg" name="details" placeholder="Location, scale, vision — anything helps us understand…" data-ph-en="Location, scale, vision — anything helps us understand…" data-ph-kn="ಸ್ಥಳ, ಗಾತ್ರ, ಕಲ್ಪನೆ — ಏನೇ ಇದ್ದರೂ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ಸಹಾಯವಾಗುತ್ತದೆ…"></textarea></label>
        <a class="btn solid" id="sendWa" href="https://wa.me/919353495972" target="_blank" rel="noopener" style="justify-self:start">{bi('Send Enquiry', 'ವಿಚಾರಣೆ ಕಳುಹಿಸಿ')}</a>
        <p class="formnote">{bi('Opens WhatsApp with your message filled in.', 'ನಿಮ್ಮ ಸಂದೇಶ ತುಂಬಿದ ವಾಟ್ಸಾಪ್ ತೆರೆಯುತ್ತದೆ.')}{DRAFT}</p>
      </form>
    </div>
  </div>
</section>
</main>
<div class="lightbox" id="lightbox" hidden role="dialog" aria-modal="true" aria-label="Film / ಚಿತ್ರ">
  <div class="lb-in"><video controls playsinline loop muted></video><div class="lb-cap"></div></div>
  <button type="button" class="close" aria-label="Close / ಮುಚ್ಚಿ">✕</button>
</div>

<footer>
  <div>JV VISUAL STUDIO</div>
  <div>{bi('A sub-brand of JV Studios · Chintamani, Karnataka', 'ಜೆ ವಿ ಸ್ಟುಡಿಯೋಸ್‌ನ ಉಪ-ಬ್ರ್ಯಾಂಡ್ · ಚಿಂತಾಮಣಿ, ಕರ್ನಾಟಕ')}</div>
  <nav><a href="https://wa.me/919353495972" target="_blank" rel="noopener">WhatsApp</a></nav>
</footer>
<script type="module" src="assets/app.js"></script>
</body>
</html>'''

open(f'{DIST}/index.html', 'w', encoding='utf-8').write(page(1))
open(f'{DIST}/look-2.html', 'w', encoding='utf-8').write(page(2))
print('built', sorted(have), fog)
