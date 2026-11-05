// J V Visual Studio v5 — scroll-driven 3D spaces (three.js r170, baked Cycles lighting)
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { createSceneLoader, startSceneAssets } from './scene-loader.js';

const html = document.documentElement;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = t => t * t * (3 - 2 * t);
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
                set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };

/* ───────── language toggle ───────── */
function setLang(l) {
  html.dataset.lang = l; html.lang = l === 'kn' ? 'kn' : 'en';
  $$('[data-setlang]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.setlang === l)));
  $$('[data-ph-en]').forEach(i => { i.placeholder = l === 'kn' ? i.dataset.phKn : i.dataset.phEn; });
  store.set('jv-lang', l);
}
setLang(store.get('jv-lang') || ((navigator.language || '').toLowerCase().startsWith('kn') ? 'kn' : 'en'));
$$('[data-setlang]').forEach(b => b.addEventListener('click', () => { setLang(b.dataset.setlang); sound.click(); }));

/* ───────── sound (all synthesised with Web Audio — no audio files) ───────── */
const sound = (() => {
  let ctx = null, master, beds = {}, noiseBuf, on = false, birdT = 0, chimeT = 0, cricketT = 0, weights = {};
  function noise(sec = 3) {
    const b = ctx.createBuffer(1, ctx.sampleRate * sec, ctx.sampleRate), d = b.getChannelData(0);
    let last = 0;
    for (let i = 0; i < d.length; i++) { const w = Math.random() * 2 - 1; last = (last + 0.02 * w) / 1.02; d[i] = w * 0.5 + last * 3; }
    return b;
  }
  function src() { const s = ctx.createBufferSource(); s.buffer = noiseBuf; s.loop = true; s.start(ctx.currentTime + Math.random()); return s; }
  function lfo(freq, depth, target, offset) {
    const o = ctx.createOscillator(), g = ctx.createGain(); o.frequency.value = freq; g.gain.value = depth;
    o.connect(g); g.connect(target); if (offset !== undefined) target.value = offset; o.start(); return o;
  }
  function bed(name) { const g = ctx.createGain(); g.gain.value = 0; g.connect(master); beds[name] = g; return g; }
  function build() {
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    master = ctx.createGain(); master.gain.value = 0; master.connect(ctx.destination);
    noiseBuf = noise();
    // resort: pool water lapping + valley wind
    const r = bed('resort');
    const w1 = src(), lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 520;
    const wg = ctx.createGain(); wg.gain.value = 0.35; lfo(0.18, 0.22, wg.gain, 0.35);
    w1.connect(lp); lp.connect(wg); wg.connect(r);
    const w2 = src(), bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1300; bp.Q.value = 1.4;
    const lg = ctx.createGain(); lg.gain.value = 0.08; lfo(0.9, 0.07, lg.gain, 0.08);
    w2.connect(bp); bp.connect(lg); lg.connect(r);
    const wd = src(), wf = ctx.createBiquadFilter(); wf.type = 'bandpass'; wf.Q.value = 0.6; lfo(0.05, 180, wf.frequency, 380);
    const wdg = ctx.createGain(); wdg.gain.value = 0.18; wd.connect(wf); wf.connect(wdg); wdg.connect(r);
    // villa at dusk: warm pad + crickets + occasional chime
    const v = bed('villa');
    const pf = ctx.createBiquadFilter(); pf.type = 'lowpass'; pf.frequency.value = 700; pf.connect(v);
    [110, 164.81, 220, 277.18].forEach((f, i) => {
      const o = ctx.createOscillator(); o.type = 'triangle'; o.frequency.value = f; o.detune.value = (i - 1.5) * 6;
      const g = ctx.createGain(); g.gain.value = 0.045; lfo(0.07 + i * 0.03, 0.025, g.gain, 0.045);
      o.connect(g); g.connect(pf); o.start();
    });
    // home: morning street — soft distant hum, birds
    const h = bed('home');
    const hm = src(), hf = ctx.createBiquadFilter(); hf.type = 'lowpass'; hf.frequency.value = 180;
    const hg = ctx.createGain(); hg.gain.value = 0.22; hm.connect(hf); hf.connect(hg); hg.connect(h);
    bed('ui').gain.value = 1;
  }
  function blip(freq0, freq1, dur, vol, type = 'sine', dest) {
    if (!ctx || !on) return;
    const t = ctx.currentTime, o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type; o.frequency.setValueAtTime(freq0, t); o.frequency.exponentialRampToValueAtTime(freq1, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 0.012); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(dest || beds.ui); o.start(t); o.stop(t + dur + 0.05);
  }
  function bird(dest) { const f = 2600 + Math.random() * 1600, n = 2 + (Math.random() * 3 | 0);
    for (let i = 0; i < n; i++) setTimeout(() => blip(f, f * (1.25 + Math.random() * 0.3), 0.07 + Math.random() * 0.05, 0.05, 'sine', dest), i * 110); }
  function tick(dt) {
    if (!ctx || !on) return;
    birdT -= dt; chimeT -= dt; cricketT -= dt;
    const outdoor = (weights.resort || 0) + (weights.home || 0);
    if (birdT < 0) { birdT = 2.5 + Math.random() * 5; if (outdoor > 0.15) bird(weights.home > weights.resort ? beds.home : beds.resort); }
    if (chimeT < 0) { chimeT = 4 + Math.random() * 6; if ((weights.villa || 0) > 0.15) { const f = [880, 1174.7, 1318.5, 1760][Math.random() * 4 | 0]; blip(f, f * 0.998, 2.2, 0.035, 'sine', beds.villa); } }
    if (cricketT < 0) { cricketT = 0.9 + Math.random() * 1.6; if ((weights.villa || 0) > 0.15) for (let i = 0; i < 3; i++) setTimeout(() => blip(4600, 4500, 0.03, 0.012, 'square', beds.villa), i * 60); }
  }
  return {
    get on() { return on; },
    toggle() {
      if (!ctx) build();
      on = !on;
      ctx.resume && ctx.resume();
      master.gain.setTargetAtTime(on ? 0.7 : 0, ctx.currentTime, 0.25);
      if (on) this.mix(weights);
      return on;
    },
    mix(w) {
      weights = w;
      if (!ctx) return;
      for (const k of ['resort', 'villa', 'home']) beds[k].gain.setTargetAtTime((w[k] || 0) * 0.9, ctx.currentTime, 0.6);
    },
    click() { blip(1500, 900, 0.05, 0.05); },
    whoosh() {
      if (!ctx || !on) return;
      const t = ctx.currentTime, s = ctx.createBufferSource(); s.buffer = noiseBuf;
      const f = ctx.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = 1.2;
      f.frequency.setValueAtTime(260, t); f.frequency.exponentialRampToValueAtTime(2400, t + 0.7);
      const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.25, t + 0.2); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.8);
      s.connect(f); f.connect(g); g.connect(beds.ui); s.start(t); s.stop(t + 0.9);
    },
    tock() { blip(240, 120, 0.12, 0.12, 'sine'); blip(1900, 1200, 0.04, 0.04, 'triangle'); },
    tick
  };
})();
const soundBtn = $('#soundBtn');
soundBtn.addEventListener('click', () => {
  const on = sound.toggle(); soundBtn.setAttribute('aria-pressed', String(on)); if (on) sound.click();
});

/* ───────── forms: enquiry opens WhatsApp with the message filled in ───────── */
(() => {
  const f = $('#enquiry'), a = $('#sendWa'); if (!f || !a) return;
  const upd = () => {
    const d = new FormData(f);
    const txt = `J V Visual Studio enquiry\nName: ${d.get('name') || ''}\nProject type: ${d.get('ptype') || ''}\n${d.get('details') || ''}`;
    a.href = 'https://wa.me/919353495972?text=' + encodeURIComponent(txt);
  };
  f.addEventListener('input', upd); f.addEventListener('submit', e => e.preventDefault()); upd();
})();

/* ───────── films: muted loops while in view, a larger player on tap ───────── */
(() => {
  const films = $$('.film'); if (!films.length) return;
  // if a host's media policy blocks the file URL, fetch the same file and play it from a blob: URL
  const blobs = {};
  const viaBlob = url => (blobs[url] = blobs[url] || fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.blob(); })
    .then(b => URL.createObjectURL(b.type ? b : new Blob([b], { type: 'video/mp4' }))));
  function setSrc(v, url) {
    v.dataset.want = url;
    v.addEventListener('error', () => {
      if (v.dataset.want !== url) return;
      viaBlob(url).then(u => { if (v.dataset.want === url) { v.src = u; if (v._wantPlay) v.play().catch(() => {}); } }).catch(() => {});
    }, { once: true });
    v.src = url;
  }
  function arm(v) { if (!v._armed) { v._armed = true; v.preload = 'metadata'; setSrc(v, v.dataset.src); } }
  const play = v => { if (reduceMotion) return; arm(v); v.preload = 'auto'; v._wantPlay = true; v.play().catch(() => {}); };
  const stop = v => { v._wantPlay = false; if (!v.paused) v.pause(); };
  const near = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting && !reduceMotion) arm($('video', e.target)); }), { rootMargin: '600px 0px' });
  const seen = new IntersectionObserver(es => es.forEach(e => {
    const v = $('video', e.target);
    if (e.intersectionRatio >= 0.55) play(v); else stop(v);
  }), { threshold: [0, 0.55] });
  films.forEach(f => { near.observe(f); seen.observe(f); });
  // larger player
  const lb = $('#lightbox'), lv = $('video', lb), lcap = $('.lb-cap', lb);
  let last = null;
  function open(f) {
    last = f; const v = $('video', f);
    setSrc(lv, v.dataset.src); lv._wantPlay = true; lv.play().catch(() => {});
    lcap.innerHTML = $('figcaption', f).innerHTML;
    lb.hidden = false; html.classList.add('lb-open'); $('.close', lb).focus(); sound.whoosh();
  }
  function close() {
    lb.hidden = true; html.classList.remove('lb-open'); lv.dataset.want = ''; lv._wantPlay = false; lv.pause(); lv.removeAttribute('src'); lv.load();
    if (last) $('.open', last).focus();
  }
  films.forEach(f => $('.open', f).addEventListener('click', () => open(f)));
  $('.close', lb).addEventListener('click', close);
  lb.addEventListener('click', e => { if (e.target === lb) close(); });
  addEventListener('keydown', e => { if (e.key === 'Escape' && !lb.hidden) close(); });
})();

/* ───────── compare slider + day→dusk fade ───────── */
$$('.cmp').forEach(c => { const i = $('input', c); const u = () => c.style.setProperty('--x', i.value + '%'); i.addEventListener('input', u); u(); });

/* ───────── 3D stage ───────── */
const CFG = window.JV_SCENES;
const stageEl = $('#stage');
let renderer = null;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
} catch (e) { html.classList.add('no3d'); }

const b2t = a => new THREE.Vector3(a[0], a[2], -a[1]);   // Blender Z-up → three Y-up
const isMobile = matchMedia('(max-width: 640px)').matches;
const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.3, 6000);
let scenes, loadScene;
let lastShadowScene = null;
const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);   // models are EXT_meshopt_compression
const texLoader = new THREE.TextureLoader();
let pmrem = null;
const waterNormal = (() => {
  const s = 256, c = document.createElement('canvas'); c.width = c.height = s; const g = c.getContext('2d');
  const img = g.createImageData(s, s);
  const h = (x, y) => Math.sin(x * 0.11 + Math.sin(y * 0.07) * 2) * 0.5 + Math.sin(y * 0.13 + x * 0.05) * 0.35 + Math.sin((x + y) * 0.31) * 0.15;
  for (let y = 0; y < s; y++) for (let x = 0; x < s; x++) {
    const dx = h(x + 1, y) - h(x - 1, y), dy = h(x, y + 1) - h(x, y - 1);
    const n = new THREE.Vector3(-dx * 0.9, -dy * 0.9, 1).normalize(), i = (y * s + x) * 4;
    img.data[i] = (n.x * 0.5 + 0.5) * 255; img.data[i + 1] = (n.y * 0.5 + 0.5) * 255; img.data[i + 2] = (n.z * 0.5 + 0.5) * 255; img.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(6, 6); return t;
})();

function setupRenderer() {
  renderer.setPixelRatio(Math.min(devicePixelRatio, isMobile ? 1.5 : 1.75));
  renderer.setSize(innerWidth, innerHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.AgXToneMapping;  // baked light is linear; textures and sky are real; AgX like Blender
  renderer.localClippingEnabled = true;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; renderer.shadowMap.autoUpdate = false;
  stageEl.appendChild(renderer.domElement);
  pmrem = new THREE.PMREMGenerator(renderer);
}
if (renderer) setupRenderer();

/* ───────── real materials: Poly Haven PBR sets × baked light-only lightmaps ───────── */
const LIB = window.JV_LIB;
const texCache = {}, texClones = {}, textureTasks = {};
const sfx = isMobile ? '-m' : '';
function texture(url, srgb, repeat = 0, channel = 0, flip = true) {
  const key = url + '|' + srgb;
  if (!texCache[key]) {
    const clones = [];
    let resolve, reject;
    textureTasks[key] = new Promise((ok, bad) => { resolve = ok; reject = bad; });
    textureTasks[key].catch(() => {}); // The owning scene awaits and reports failures.
    const t = texLoader.load(url, () => {
      clones.forEach(c => { c.needsUpdate = true; }); resolve();
    }, undefined, error => { delete texCache[key]; reject(error); });
    t.userData.jvTextureKey = key;
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.flipY = flip; t.anisotropy = isMobile ? 4 : 8;
    texClones[key] = clones;
    texCache[key] = t;
  }
  const base = texCache[key];
  if (!repeat) { base.channel = channel; return base; }
  // clones share the image; they are flagged for upload once it has arrived
  const t = base.clone();
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat, repeat); t.channel = channel;
  if (base.image && base.image.width) t.needsUpdate = true; else texClones[key].push(t);
  return t;
}
async function waitForTextures(root) {
  const pending = new Set();
  root.traverse(o => {
    if (!o.isMesh) return;
    for (const material of (Array.isArray(o.material) ? o.material : [o.material])) {
      for (const value of Object.values(material)) {
        const task = value?.isTexture && textureTasks[value.userData.jvTextureKey];
        if (task) pending.add(task);
      }
    }
  });
  await Promise.all(pending);
}
// lightmap = irradiance only: drop three's own IBL diffuse (the sky is already in the bake) and
// darken reflections where the bake is in shadow (cheap specular occlusion)
function patchLightmap(m, sunLevel) {
  m.onBeforeCompile = sh => {
    sh.uniforms.soK = { value: 1 / sunLevel };
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float soK;')
      // the IBL line lives inside an #include, so expand that chunk first, then drop the line
      .replace('#include <lights_fragment_maps>', THREE.ShaderChunk.lights_fragment_maps.replace('iblIrradiance += getIBLIrradiance( geometryNormal );', ''))
      .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
        #ifdef USE_LIGHTMAP
          reflectedLight.indirectSpecular *= clamp( dot( lightMapIrradiance, vec3( 0.2126, 0.7152, 0.0722 ) ) * soK, 0.08, 1.0 );
        #endif
        // the sun is already in the bake; the scene's sun light is only there for the real-time lit plants
        reflectedLight.directDiffuse = vec3( 0.0 ); reflectedLight.directSpecular = vec3( 0.0 );`);
  };
  m.customProgramCacheKey = () => 'jvlm' + sunLevel.toFixed(3);
}
function pbrMaterial(name, atl, env, sunLevel) {
  const L = LIB.materials[name] || { mode: 'atlas', rough: 0.85, metal: 0 };
  const m = new THREE.MeshStandardMaterial({ envMap: env, envMapIntensity: 1.0, name });
  m.lightMap = atl.lm; m.lightMapIntensity = atl.k * Math.PI;
  if (L.mode === 'photo') {
    const rep = 1 / L.size_m, base = `pbr/tex/${L.tex}`;
    m.map = texture(`${base}_${L.grey ? 'gd' : 'd'}${sfx}.webp`, true, rep, 0);
    m.normalMap = texture(`${base}_n${sfx}.webp`, false, rep, 0);
    m.normalScale.set(L.nrm, -L.nrm);
    const arm = texture(`${base}_arm${sfx}.webp`, false, rep, 0);
    m.aoMap = arm; m.aoMapIntensity = 0.75; m.roughnessMap = arm;   // every photo set is a dielectric
    m.roughness = L.rough; m.metalness = 0.0;
    m.color.setRGB(L.tint[0], L.tint[1], L.tint[2]);
  } else {
    m.map = atl.al; m.roughness = L.rough; m.metalness = L.metal;
  }
  patchLightmap(m, sunLevel);
  return m;
}

/* ───────── real plants: Poly Haven CC0 models, instanced, lit by the same sky (without its sun) + the sun as a light ───────── */
const PLANT_MATS = window.JV_PLANT_MATS || {};
const plantMats = {};
function patchPlant(m, leaf) {
  m.onBeforeCompile = sh => {
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute float skyVis;\nattribute vec3 probe;\nvarying float vSkyVis;\nvarying vec3 vProbe;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvSkyVis = skyVis; vProbe = probe;');
    sh.uniforms.probeMix = { value: m.userData.probeMix || 0 };
    let phys = THREE.ShaderChunk.lights_physical_pars_fragment;
    // leaves pass light through: the far side of a sunlit leaf gets a share of the sun
    // (diffuse only: the specular term is undefined from the back side and flares white)
    if (leaf) phys = phys.replace('reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );\n}\nvoid RE_IndirectDiffuse_Physical',
      'reflectedLight.directDiffuse += ( irradiance + max( - dot( geometryNormal, directLight.direction ), 0.0 ) * 0.45 * directLight.color ) * BRDF_Lambert( material.diffuseColor );\n}\nvoid RE_IndirectDiffuse_Physical');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying float vSkyVis;\nvarying vec3 vProbe;\nuniform float probeMix;')
      .replace('#include <lights_physical_pars_fragment>', phys)
      // sky light reaching each plant (baked per instance: 0 under a roof, 1 in the open)
      // where there is no sun (dusk) plants take the baked light of the ground they stand on (lamps, sky)
      .replace('#include <lights_fragment_end>', 'iblIrradiance = mix( iblIrradiance * vSkyVis, vProbe, probeMix ); radiance *= vSkyVis;\n#include <lights_fragment_end>');
  };
  m.customProgramCacheKey = () => (leaf ? 'jvleaf' : 'jvbark') + (m.userData.probeMix || 0);
}
function plantMaterial(name, envd, probeMix = 0, envGain = 1) {
  const base = name.replace(/\.\d+$/, '');
  const key = base + '|' + envd.uuid;
  if (plantMats[key]) return plantMats[key];
  const R = PLANT_MATS[base] || {};
  const tex = (f, srgb) => texture(`plants/tex/${f}${sfx}.webp`, srgb, 0, 0, false);
  const m = new THREE.MeshStandardMaterial({ name: base, roughness: 1, metalness: 0, envMap: envd, envMapIntensity: envGain, side: THREE.DoubleSide });
  if (R.c) m.map = tex(R.c, true); else m.color.set(0x556b3a);
  if (R.n) { m.normalMap = tex(R.n, false); m.normalScale.set(1, -1); }
  // leaves stay matte: a glossy leaf card turns white against a low sun
  if (R.r && !R.alpha) m.roughnessMap = tex(R.r, false);
  if (R.alpha) { m.alphaTest = 0.35; m.alphaToCoverage = true; m.roughness = 0.92; }   // coverage keeps distant canopies full
  m.userData.probeMix = probeMix;
  patchPlant(m, !!R.alpha);
  return plantMats[key] = m;
}
function loadHdrTex(url) {
  return new RGBELoader().loadAsync(url);
}
function loadGlb(url, onProgress) {
  return loader.loadAsync(url, onProgress);
}
const SMALL_PLANT = /^(peri|weed|shrub03|fern|nettle|calathea|jac_dist)/;
async function loadPlantAssets(P) {
  const [hdr, gltf] = await Promise.all([loadHdrTex(P.envd), loadGlb(P.glb + sfx + '.glb')]);
  return { hdr, gltf };
}
async function addPlants(s, P, assets) {
  const { hdr, gltf } = assets;
  hdr.mapping = THREE.EquirectangularReflectionMapping;
  s.plantEnvTarget = pmrem.fromEquirectangular(hdr);
  const envd = s.plantEnvTarget.texture; hdr.dispose();
  const protos = {};
  gltf.scene.updateMatrixWorld(true);
  for (const node of gltf.scene.children) {
    const parts = [];
    // positions are quantised (normalised int16 + a node scale), so keep the node matrix instead of baking it in
    node.traverse(o => { if (o.isMesh) parts.push({ g: o.geometry, mat: o.material.name, mw: o.matrixWorld.clone() }); });
    protos[node.name] = parts;
  }
  // group instances by prototype and build group (the build stages reveal plants with their stage)
  const sets = {};
  P.inst.forEach((it, i) => {
    let p = it.p;
    if (isMobile) { p = P.down[p] || p; if (SMALL_PLANT.test(p) && i % 2) return; }
    if (!protos[p]) return;
    const k = p + '|' + it.g; (sets[k] = sets[k] || { p, g: it.g, list: [] }).list.push(it);
  });
  const m4 = new THREE.Matrix4(), box = new THREE.Box3(), v = new THREE.Vector3();
  for (const { p, g, list } of Object.values(sets)) {
    for (const part of protos[p]) {
      const geo = new THREE.BufferGeometry();
      for (const [n, a] of Object.entries(part.g.attributes)) geo.setAttribute(n, a);
      if (part.g.index) geo.setIndex(part.g.index);
      geo.setAttribute('skyVis', new THREE.InstancedBufferAttribute(new Float32Array(list.map(it => Math.max(0.12, it.sv))), 1));
      geo.setAttribute('probe', new THREE.InstancedBufferAttribute(new Float32Array(list.flatMap(it => (it.pr || [0, 0, 0]).map(c => c * (P.probeGain || 1)))), 3));
      const mesh = new THREE.InstancedMesh(geo, plantMaterial(part.mat, envd, P.probeMix || 0, P.plantEnv || 1), list.length);
      list.forEach((it, i) => { m4.fromArray(it.m); box.expandByPoint(v.setFromMatrixPosition(m4)); m4.multiply(part.mw); mesh.setMatrixAt(i, m4); });
      mesh.instanceMatrix.needsUpdate = true; mesh.computeBoundingSphere();
      mesh.castShadow = true; mesh.receiveShadow = true;
      s.scene.add(mesh);
      (s.groups['JV_' + g] = s.groups['JV_' + g] || []).push(mesh);
    }
  }
  // the sun as a light, with one static shadow map over the planted area
  if (P.sun && P.sun.E > 0) {
    const L = new THREE.DirectionalLight(new THREE.Color(...P.sun.col), P.sun.E);
    const c = box.getCenter(new THREE.Vector3()), r = Math.min(170, box.getSize(new THREE.Vector3()).length() * 0.5 + 12);
    const d = new THREE.Vector3(...P.sun.dir).normalize();
    L.position.copy(c).addScaledVector(d, r + 60); L.target.position.copy(c);
    L.castShadow = true;
    const sc = L.shadow.camera; sc.left = sc.bottom = -r; sc.right = sc.top = r; sc.near = 1; sc.far = 2 * r + 140; sc.updateProjectionMatrix();
    L.shadow.mapSize.set(isMobile ? 1024 : 2048, isMobile ? 1024 : 2048);
    L.shadow.bias = -0.0004; L.shadow.normalBias = 0.05; L.shadow.radius = 2;
    s.scene.add(L, L.target);
    s.sun = L;
  }
  s.shadowDirty = true;
}
const jvGroup = o => { let p = o; while (p && !(p.name && p.name.startsWith('JV_'))) p = p.parent; return p ? p.name.replace(/_\d+$/, '') : ''; };

function disposeScene(s) {
  const materials = new Set(), geometries = new Set();
  s.scene.traverse(o => {
    if (!o.isMesh) return;
    geometries.add(o.geometry);
    for (const m of (Array.isArray(o.material) ? o.material : [o.material])) materials.add(m);
  });
  materials.forEach(m => m.dispose());
  geometries.forEach(g => g.dispose());
  s.scene.background?.dispose();
  s.envTarget?.dispose();
  s.plantEnvTarget?.dispose();
}
async function prepareScene(s) {
  const cfg = s.cfg, P = cfg.pbr;
  if (!P) throw new Error('No baked materials configured for ' + s.key);
  s.scene.fog = new THREE.Fog(cfg.fog, cfg.fogNear, cfg.fogFar);
  s.phase = 'assets';
  const atl = {};
  for (const [name, a] of Object.entries(P.atlases)) {
    atl[name] = { k: a.k, lm: texture(a.lm + sfx + '.webp', true, 0, 1, false), al: texture(a.al + sfx + '.webp', true, 0, 1, false) };
  }
  const assets = startSceneAssets({
    environment: () => loadHdrTex(P.env),
    sky: () => texLoader.loadAsync(P.sky),
    model: () => loadGlb(cfg.model, ev => { s.progress = ev.total ? ev.loaded / ev.total : 0; }),
    plants: P.plants ? () => loadPlantAssets(P.plants) : null
  });
  const [hdr, sky, gltf] = await assets.base;
  try { s.envTarget = pmrem.fromEquirectangular(hdr); s.env = s.envTarget.texture; }
  finally { hdr.dispose(); }
  sky.mapping = THREE.EquirectangularReflectionMapping; sky.colorSpace = THREE.SRGBColorSpace;
  s.scene.background = sky; s.scene.backgroundIntensity = P.kb * (cfg.skyGain || 1);
  s.progress = 1;
  const sunLevel = P.sunLevel || 3.0, root = gltf.scene;
  root.traverse(o => {
    if (!o.isMesh) return;
    const g = jvGroup(o), n = g.toLowerCase(), m = o.material, mn = (m && m.name) || '';
    let nm;
    if (n.includes('water')) {
      nm = new THREE.MeshStandardMaterial({ color: cfg.waterColor || 0x1d5a61, roughness: 0.04, metalness: 0.0, envMap: s.env, envMapIntensity: 1.1,
        transparent: true, opacity: 0.88, normalMap: waterNormal, normalScale: new THREE.Vector2(0.22, 0.22) });
      s.water.push(nm);
    } else if (n.includes('glass')) {
      // reflections added on top, the view through attenuated: premultiplied-style blend
      nm = new THREE.MeshStandardMaterial({ color: 0x000000, roughness: 0.02, metalness: 0.0, envMap: s.env, envMapIntensity: 1.1,
        transparent: true, opacity: cfg.glassOpacity || 0.3, depthWrite: false, side: THREE.DoubleSide,
        blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor });
    } else if (n.includes('lamp')) {
      nm = new THREE.MeshBasicMaterial({ color: (m.color || new THREE.Color(1, .8, .5)).clone().multiplyScalar(cfg.lampBoost || 1.0), toneMapped: false });
    } else if (n.includes('veg') || n.includes('far')) {
      nm = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, color: new THREE.Color(P.kv, P.kv, P.kv) });
    } else {
      const a = atl[(o.parent && o.parent.userData.jv_atlas) || o.userData.jv_atlas || P.atlasOf[g] || 'build'] || Object.values(atl)[0];
      nm = pbrMaterial(mn.replace(/^pbr__/, '').replace(/\.\d+$/, ''), a, s.env, sunLevel);
    }
    nm.fog = !n.includes('lamp');
    o.material = nm;
    (s.groups[g] = s.groups[g] || []).push(o);
  });
  s.scene.add(root);
  root.traverse(o => { if (o.isMesh && !/glass|water|lamp/i.test(jvGroup(o))) o.castShadow = true; });
  s.phase = 'textures';
  await waitForTextures(root);
  if (P.plants) {
    s.phase = 'plants';
    const plants = await assets.plants;
    try {
      if (plants.error) throw plants.error;
      await addPlants(s, P.plants, plants.value);
      await waitForTextures(s.scene);
    } catch (e) { console.warn('plants failed', e); }
  }
  if (cfg.build) setupBuild(s);
  s.phase = 'shaders';
  // Compile while the poster is visible, instead of blocking the first live frame.
  await renderer.compileAsync(s.scene, camera);
}
({ scenes, loadScene } = createSceneLoader({
  create: key => ({ key, cfg: CFG[key], scene: new THREE.Scene(), ready: false, failed: false, groups: {}, water: [], progress: 0 }),
  prepare: prepareScene,
  dispose: disposeScene,
  onReady: s => { if (s.key === 'resort' || active?.key === s.key) warmNextScene(s.key); },
  onError: (s, err) => console.warn('scene failed', s.key, err)
}));

/* ───────── camera paths (Blender coordinates from the scene files) ───────── */
const tmpA = new THREE.Vector3(), tmpB = new THREE.Vector3();
function pathAt(keys, p) {
  // keys: [{p, pos:[...], tgt:[...], fov}]; Catmull-Rom between keys, eased
  let i = 0; while (i < keys.length - 2 && p > keys[i + 1].p) i++;
  const k0 = keys[Math.max(0, i - 1)], k1 = keys[i], k2 = keys[i + 1], k3 = keys[Math.min(keys.length - 1, i + 2)];
  const t = smooth(clamp((p - k1.p) / Math.max(1e-6, k2.p - k1.p)));
  const cr = (a, b, c, d) => {
    const A = b2t(a), B = b2t(b), C = b2t(c), D = b2t(d);
    return new THREE.Vector3(
      0.5 * ((2 * B.x) + (-A.x + C.x) * t + (2 * A.x - 5 * B.x + 4 * C.x - D.x) * t * t + (-A.x + 3 * B.x - 3 * C.x + D.x) * t * t * t),
      0.5 * ((2 * B.y) + (-A.y + C.y) * t + (2 * A.y - 5 * B.y + 4 * C.y - D.y) * t * t + (-A.y + 3 * B.y - 3 * C.y + D.y) * t * t * t),
      0.5 * ((2 * B.z) + (-A.z + C.z) * t + (2 * A.z - 5 * B.z + 4 * C.z - D.z) * t * t + (-A.z + 3 * B.z - 3 * C.z + D.z) * t * t * t));
  };
  return { pos: cr(k0.pos, k1.pos, k2.pos, k3.pos), tgt: cr(k0.tgt, k1.tgt, k2.tgt, k3.tgt), fov: k1.fov + (k2.fov - k1.fov) * t };
}

/* ───────── residential build sequence ───────── */
function setupBuild(s) {
  const B = s.cfg.build;
  s.build = [];
  for (const st of B.stages) {
    const meshes = st.groups.flatMap(g => s.groups['JV_' + g] || []);
    const box = new THREE.Box3(); meshes.forEach(m => box.expandByObject(m));
    const plane = new THREE.Plane(new THREE.Vector3(0, -1, 0), box.min.y - 0.01);
    // clones keep the shader patches (Material.clone drops onBeforeCompile)
    meshes.forEach(m => { const o = m.material, c = o.clone(); c.onBeforeCompile = o.onBeforeCompile; c.customProgramCacheKey = o.customProgramCacheKey; c.clippingPlanes = [plane]; m.material = c; });
    s.build.push({ ...st, meshes, plane, y0: box.min.y - 0.01, y1: box.max.y + 0.02 });
  }
  // plan lines: the outline of every ground-floor wall as modelled (door and window gaps show as breaks)
  const ft = (f, i = 0) => (f + i / 12) * 0.3048;
  const pts = [];
  const L = (a, b) => { pts.push(b2t([a[0], a[1], B.planZ]), b2t([b[0], b[1], B.planZ])); };
  const P = [ft(40), ft(30)];
  L([0, 0], [P[0], 0]); L([P[0], 0], [P[0], P[1]]); L([P[0], P[1]], [0, P[1]]); L([0, P[1]], [0, 0]);
  (B.planRects || []).forEach(([x0, y0, x1, y1]) => { L([x0, y0], [x1, y0]); L([x1, y0], [x1, y1]); L([x1, y1], [x0, y1]); L([x0, y1], [x0, y0]); });
  // draw each plan line as a flat 7 cm ribbon so it reads at any zoom
  const pos = [], half = 0.018;
  for (let i = 0; i < pts.length; i += 2) {
    const a = pts[i], b = pts[i + 1], d = b.clone().sub(a).normalize(), n = new THREE.Vector3(-d.z, 0, d.x).multiplyScalar(half);
    const A = a.clone().sub(d.clone().multiplyScalar(half));
    const Bp = b.clone().add(d.clone().multiplyScalar(half));
    const q = [A.clone().add(n), A.clone().sub(n), Bp.clone().sub(n), Bp.clone().add(n)];
    [0, 1, 2, 0, 2, 3].forEach(k => pos.push(q[k].x, q[k].y, q[k].z));
  }
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  s.planMat = new THREE.MeshBasicMaterial({ color: B.planColor, transparent: true, opacity: 1, toneMapped: false, side: THREE.DoubleSide,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2, fog: false });
  s.plan = new THREE.Mesh(geo, s.planMat); s.plan.renderOrder = 10; s.scene.add(s.plan);
  // drawing sheet laid over the plot while the plan draws
  const sh = new THREE.PlaneGeometry(P[0] + 0.6, P[1] + 0.6); sh.rotateX(-Math.PI / 2);
  s.sheetMat = new THREE.MeshBasicMaterial({ color: B.sheetColor, transparent: true, opacity: 0.96, toneMapped: false, fog: false,
    polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
  s.sheet = new THREE.Mesh(sh, s.sheetMat); s.sheet.position.copy(b2t([P[0] / 2, P[1] / 2, B.planZ - 0.004])); s.sheet.renderOrder = 9; s.scene.add(s.sheet);
  s.lastStage = -1;
}
function updateBuild(s, p) {
  if (s.buildProgress === p) return s.lastStage;
  s.buildProgress = p;
  let cur = -1;
  s.build.forEach((st, i) => {
    const k = clamp((p - st.a) / (st.b - st.a));
    const vis = k > 0;
    st.meshes.forEach(m => { m.visible = vis; });
    st.plane.constant = st.y0 + (st.y1 - st.y0) * smooth(k);
    if (k > 0) cur = i;
  });
  const n = s.plan.geometry.attributes.position.count;
  s.plan.geometry.setDrawRange(0, Math.max(6, Math.floor(n * clamp(p / s.cfg.build.planEnd) / 6) * 6));
  s.planMat.opacity = 1 - clamp((p - s.build[1].a) / 0.08) * 0.85;
  s.sheetMat.opacity = 0.96 * (1 - clamp((p - s.build[0].a) / 0.06));
  s.sheet.visible = s.sheetMat.opacity > 0.01;
  if (cur !== s.lastStage) { if (cur > s.lastStage && cur >= 0) sound.tock(); s.lastStage = cur; s.shadowDirty = true; }
  return cur;
}

/* ───────── scroll → active chapter ───────── */
const tracks = $$('.track').map(el => ({ el, key: el.dataset.track, steps: $$('.step', el), title: $('.hud-title', el.closest('.chapter')).innerHTML }));
const fades = $$('.fade');
const scenePosters = { resort: 'img/resort_edge', villa: 'img/villa_front_dusk', home: 'img/home_street' };
const posterImages = Object.fromEntries(Object.entries(scenePosters).map(([key, src]) => {
  const image = new Image(); image.src = src + (isMobile ? '-s' : '') + '.webp'; return [key, image];
}));
let posterKey = null;
function showPoster(key) {
  if (key === posterKey) return;
  posterKey = key;
  stageEl.style.backgroundImage = key ? `url("${posterImages[key].src}")` : '';
}
const deferredPreloads = new Set();
function warmNextScene(key) {
  const next = tracks[tracks.findIndex(t => t.key === key) + 1]?.key;
  if (!next || scenes[next] || deferredPreloads.has(next) || navigator.connection?.saveData || /(^|-)2g$/.test(navigator.connection?.effectiveType || '')) return;
  deferredPreloads.add(next);
  const run = () => { if (!scenes[next]) loadScene(next); };
  if ('requestIdleCallback' in window) requestIdleCallback(run, { timeout: 2500 });
  else setTimeout(run, 250);
}
const htmlValues = new WeakMap();
function updateHTML(element, value) {
  if (htmlValues.get(element) !== value) { element.innerHTML = value; htmlValues.set(element, value); }
}
const hud = $('#hud'), hudChapter = $('#hudChapter'), hudStage = $('#hudStage'), hudBar = $('#hudBar i'), hudCam = $('#hudCam'), hudLoad = $('#hudLoad');
const tools = $('#tools'), orbitBtn = $('#orbitBtn'), progressEl = $('.progress');
const retryBtn = document.createElement('button');
retryBtn.type = 'button'; retryBtn.id = 'retryScene'; retryBtn.className = 'retry-scene'; retryBtn.hidden = true;
retryBtn.innerHTML = '<span lang="en">RETRY 3D</span><span lang="kn">ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ</span>';
hudLoad.after(retryBtn);
hudLoad.setAttribute('role', 'status');
retryBtn.addEventListener('click', () => {
  if (!active?.failed) return;
  loadScene(active.key, { retry: true });
  active = scenes[active.key];
  retryBtn.hidden = true;
});
let active = null, lastActiveKey = null, orbit = null;

function trackState() {
  const vh = innerHeight;
  let best = null;
  for (const t of tracks) {
    const r = t.el.getBoundingClientRect();
    const span = r.height - vh;
    const p = clamp(-r.top / Math.max(1, span));
    const visible = r.top < vh && r.bottom > 0;
    // cover = how much of the viewport the transparent track occupies (drives sound mix + render)
    const cover = clamp((Math.min(r.bottom, vh) - Math.max(r.top, 0)) / vh);
    t.p = p; t.visible = visible; t.cover = cover;
    if (visible && cover > 0.02 && (!best || cover > best.cover)) best = t;
  }
  return best;
}

orbitBtn && orbitBtn.addEventListener('click', () => {
  if (orbit) { orbit = null; stageEl.classList.remove('orbit'); orbitBtn.setAttribute('aria-pressed', 'false'); sound.click(); return; }
  if (!active || !active.ready) return;
  const tgt = active.lastTgt ? active.lastTgt.clone() : new THREE.Vector3();
  const off = camera.position.clone().sub(tgt);
  orbit = { tgt, r: off.length(), th: Math.atan2(off.x, off.z), ph: Math.acos(clamp(off.y / off.length(), -1, 1)), dth: 0, dph: 0, scene: active.key, sy: scrollY };
  stageEl.classList.add('orbit'); orbitBtn.setAttribute('aria-pressed', 'true'); sound.click();
});
(() => {
  let drag = null, pinch = 0;
  stageEl.addEventListener('pointerdown', e => { if (!orbit) return; drag = { x: e.clientX, y: e.clientY }; stageEl.setPointerCapture(e.pointerId); });
  stageEl.addEventListener('pointermove', e => {
    if (!orbit || !drag) return;
    orbit.dth -= (e.clientX - drag.x) * 0.005; orbit.dph -= (e.clientY - drag.y) * 0.005; drag = { x: e.clientX, y: e.clientY };
  });
  stageEl.addEventListener('pointerup', () => { drag = null; });
  stageEl.addEventListener('wheel', e => { if (!orbit) return; e.preventDefault(); orbit.r = clamp(orbit.r * Math.pow(1.0015, e.deltaY), 4, 400); }, { passive: false });
  stageEl.addEventListener('touchmove', e => {
    if (!orbit || e.touches.length !== 2) return;
    const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
    if (pinch) orbit.r = clamp(orbit.r * pinch / d, 4, 400); pinch = d;
  }, { passive: true });
  stageEl.addEventListener('touchend', () => { pinch = 0; });
  addEventListener('keydown', e => { if (e.key === 'Escape' && orbit) orbitBtn.click(); });
})();

function stepIndex(t) {
  const vh = innerHeight; let idx = 0;
  t.steps.forEach((s, i) => { const c = s.querySelector('.card'); if (c && c.getBoundingClientRect().top < vh * 0.78) idx = i; });
  return idx;
}

let layoutDirty = true, cachedTrack = null;
const invalidateLayout = () => { layoutDirty = true; };
addEventListener('scroll', invalidateLayout, { passive: true });
addEventListener('resize', invalidateLayout);
new ResizeObserver(invalidateLayout).observe(document.body);
let lastT = performance.now();
function frame(now) {
  try { frameInner(now); } catch (e) { console.error(e); }
  requestAnimationFrame(frame);
}
function frameInner(now) {
  const dt = Math.min(0.1, (now - lastT) / 1000); lastT = now;
  if (layoutDirty) {
    layoutDirty = false;
    const doc = document.documentElement;
    progressEl.style.width = (100 * scrollY / Math.max(1, doc.scrollHeight - innerHeight)).toFixed(2) + '%';
    // fade sections
    fades.forEach(f => {
      const r = f.getBoundingClientRect(); const t = clamp(-r.top / Math.max(1, r.height - innerHeight));
      f.style.setProperty('--t', smooth(clamp((t - 0.15) / 0.7)).toFixed(3));
      const c = $('.clock', f); if (c) { const e = 38 + (-2 - 38) * smooth(clamp((t - 0.15) / 0.7)); c.textContent = `SUN ${e.toFixed(0)}°`; }
    });
    cachedTrack = trackState();
    tracks.forEach(t => { t.step = stepIndex(t); });
    const weights = {}; tracks.forEach(t => { weights[t.key] = Math.max(weights[t.key] || 0, t.visible ? t.cover : 0); });
    sound.mix(weights);
  }
  const best = cachedTrack;
  // leave orbit mode as soon as the page moves on, so the stage never blocks the page
  if (orbit && (!best || best.key !== orbit.scene || Math.abs(scrollY - orbit.sy) > 80)) orbitBtn.click();
  sound.tick(dt);
  if (best && renderer) {
    if (!scenes[best.key]) loadScene(best.key);
    const s = scenes[best.key];
    if (best.key !== lastActiveKey) {
      lastActiveKey = best.key; sound.whoosh();
      if (orbit && orbit.scene !== best.key) orbitBtn.click();
      if (s.ready) warmNextScene(best.key);
    }
    active = s || null;
    const showHud = best.cover > 0.55;
    hud.classList.toggle('on', showHud); tools.classList.toggle('on', showHud && !!(s && s.ready));
    const sIdx = best.step || 0;
    const step = best.steps[sIdx];
    updateHTML(hudChapter, best.title);
    if (s && s.ready) {
      renderer.domElement.hidden = false;
      hudLoad.textContent = ''; delete hudLoad.dataset.message; hudLoad.hidden = true; retryBtn.hidden = true;
      let cam;
      if (orbit) {
        orbit.th += orbit.dth * 0.12; orbit.ph = clamp(orbit.ph + orbit.dph * 0.12, 0.12, Math.PI / 2 - 0.02); orbit.dth *= 0.88; orbit.dph *= 0.88;
        const pos = new THREE.Vector3(Math.sin(orbit.ph) * Math.sin(orbit.th), Math.cos(orbit.ph), Math.sin(orbit.ph) * Math.cos(orbit.th)).multiplyScalar(orbit.r).add(orbit.tgt);
        cam = { pos, tgt: orbit.tgt, fov: camera.fov };
      } else {
        cam = pathAt(s.cfg.path, best.p);
        if (!reduceMotion) { const tt = now / 1000; cam.pos.x += Math.sin(tt * 0.21) * 0.25; cam.pos.y += Math.sin(tt * 0.17) * 0.12; }
      }
      camera.position.copy(cam.pos); camera.lookAt(cam.tgt); s.lastTgt = cam.tgt;
      camera.aspect = innerWidth / innerHeight;
      camera.fov = camera.aspect < 1 ? Math.min(78, cam.fov * (1 + 0.55 * (1 - camera.aspect))) : cam.fov;
      camera.updateProjectionMatrix();
      const lab = step && ($('.hud-stage', step) || $('h3', step));
      let label = lab ? lab.innerHTML : (best.lastLabel || '');
      best.lastLabel = label;
      if (s.build) { const cur = updateBuild(s, best.p); if (cur >= 0) label = s.cfg.build.stages[cur].label; else label = s.cfg.build.planLabel; }
      updateHTML(hudStage, label);
      hudBar.style.width = (best.p * 100).toFixed(1) + '%';
      hudCam.textContent = `CAM ${(24 / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2))).toFixed(0)} mm · EYE ${(cam.pos.y - s.cfg.ground).toFixed(1)} m · ${s.cfg.sunLabel}`;
      s.water.forEach(m => { m.normalMap.offset.x += dt * 0.012; m.normalMap.offset.y += dt * 0.007; });
      renderer.toneMappingExposure = s.cfg.exposure || 1;
      if (s.shadowDirty || s !== lastShadowScene) { renderer.shadowMap.needsUpdate = true; s.shadowDirty = false; lastShadowScene = s; }
      renderer.render(s.scene, camera);
    } else {
      if (!renderer.domElement.hidden) { renderer.clear(); renderer.domElement.hidden = true; }
      showPoster(best.key);
      updateHTML(hudStage, ''); hudCam.textContent = ''; hudBar.style.width = '0%';
      retryBtn.hidden = !s?.failed;
      hudLoad.hidden = false;
      const labels = {
        assets: s?.progress > 0 ? [`LOADING MODEL ${Math.round(s.progress * 100)}%`, `ಮಾದರಿ ಲೋಡ್ ಆಗುತ್ತಿದೆ ${Math.round(s.progress * 100)}%`] : ['LOADING 3D', '3D ಲೋಡ್ ಆಗುತ್ತಿದೆ'],
        textures: ['LOADING MATERIALS', 'ಸಾಮಗ್ರಿಗಳು ಲೋಡ್ ಆಗುತ್ತಿವೆ'],
        plants: ['ADDING LANDSCAPE', 'ಭೂದೃಶ್ಯ ಲೋಡ್ ಆಗುತ್ತಿದೆ'],
        shaders: ['PREPARING 3D', '3D ಸಿದ್ಧವಾಗುತ್ತಿದೆ']
      };
      const message = s?.failed ? ['3D UNAVAILABLE — RETRY OR KEEP SCROLLING', '3D ಲಭ್ಯವಿಲ್ಲ — ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಮುಂದೆ ನೋಡಿ'] : (labels[s?.phase] || labels.assets);
      if (hudLoad.dataset.message !== message.join('|')) {
        hudLoad.replaceChildren(...message.map((text, i) => { const span = document.createElement('span'); span.lang = i ? 'kn' : 'en'; span.textContent = text; return span; }));
        hudLoad.dataset.message = message.join('|');
      }
    }
  } else {
    hud.classList.remove('on'); tools.classList.remove('on'); retryBtn.hidden = true;
    showPoster(null);
    if (renderer && !renderer.domElement.hidden) { renderer.clear(); renderer.domElement.hidden = true; }
  }
}
addEventListener('resize', () => { if (renderer) { renderer.setSize(innerWidth, innerHeight); } });
if (renderer) {
  // Direct chapter links should not download the resort before the requested scene.
  const initial = tracks.find(t => '#' + t.el.closest('.chapter').id === location.hash)?.key || 'resort';
  loadScene(initial);
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) loadScene($('.track', e.target).dataset.track); }), { rootMargin: '200% 0px' });
  tracks.forEach(t => io.observe(t.el.closest('.chapter')));
}
requestAnimationFrame(frame);
