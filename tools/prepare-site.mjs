import { copyFile, mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = fileURLToPath(new URL('../', import.meta.url));
const dist = path.join(root, 'dist');
const errors = [], checked = new Set(), scriptQueue = [], importMap = {};
const external = /^(?:[a-z][\w+.-]*:|\/\/|#)/i;

// Keep the original offline Blender generator out of the deployment build.
await mkdir(path.join(dist, 'assets'), { recursive: true });
for (const name of ['app.js', 'scene-loader.js', 'site.css']) {
  await copyFile(path.join(root, 'site', 'assets', name), path.join(dist, 'assets', name));
}

async function check(url, base = dist) {
  if (!url || external.test(url)) return;
  const local = decodeURIComponent(url.split(/[?#]/)[0]);
  const file = path.resolve(local.startsWith('/') ? dist : base, local.replace(/^\//, ''));
  const relative = path.relative(dist, file);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    errors.push(`Reference outside dist: ${url}`); return;
  }
  if (checked.has(file)) return;
  checked.add(file);
  try {
    // Windows allows mismatched case; production Linux must use the exact name.
    let parent = dist;
    for (const segment of relative.split(path.sep)) {
      if (!(await readdir(parent)).includes(segment)) throw new Error('missing or incorrect filename case');
      parent = path.join(parent, segment);
    }
    if (!(await stat(file)).isFile()) throw new Error('not a file');
    if (file.endsWith('.js')) scriptQueue.push(file);
  } catch (error) { errors.push(`${relative}: ${error.message}`); }
}

function inlineData(html, name) {
  const match = html.match(new RegExp(`window\\.${name}\\s*=\\s*([\\s\\S]*?);(?=\\s*(?:window\\.|</script>))`));
  if (!match) throw new Error(`Missing inline data: ${name}`);
  return { text: match[1], data: JSON.parse(match[1]) };
}

for (const page of ['index.html', 'look-2.html']) {
  const file = path.join(dist, page);
  let html = await readFile(file, 'utf8');
  const config = inlineData(html, 'JV_SCENES');
  // These preview-only modules were never supplied. Normal hosting uses binary assets.
  for (const scene of Object.values(config.data)) {
    delete scene.modelJs;
    if (scene.pbr) {
      delete scene.pbr.envJs;
      if (scene.pbr.plants) {
        delete scene.pbr.plants.glbJs;
        delete scene.pbr.plants.envdJs;
      }
    }
  }
  html = html.replace(config.text, JSON.stringify(config.data));
  await writeFile(file, html);
  const map = html.match(/<script\s+type="importmap">([\s\S]*?)<\/script>/);
  if (!map) throw new Error(`${page}: missing import map`);
  Object.assign(importMap, JSON.parse(map[1]).imports);
  for (const [, url] of html.matchAll(/\b(?:src|href|poster|data-src)="([^"]+)"/g)) await check(url);
  for (const [, srcset] of html.matchAll(/\bsrcset="([^"]+)"/g)) {
    for (const src of srcset.split(',')) await check(src.trim().split(/\s+/)[0]);
  }
  for (const scene of Object.values(config.data)) {
    await check(scene.model);
    if (!scene.pbr) { errors.push(`${page}: missing PBR scene data`); continue; }
    const pbr = scene.pbr;
    await check(pbr.env); await check(pbr.sky);
    for (const atlas of Object.values(pbr.atlases)) {
      for (const kind of ['al', 'lm']) for (const suffix of ['', '-m']) await check(atlas[kind] + suffix + '.webp');
    }
    if (pbr.plants) {
      await check(pbr.plants.envd);
      for (const suffix of ['', '-m']) await check(pbr.plants.glb + suffix + '.glb');
    }
  }
  const library = inlineData(html, 'JV_LIB').data;
  for (const material of Object.values(library.materials)) {
    if (material.mode !== 'photo') continue;
    for (const kind of [material.grey ? 'gd' : 'd', 'n', 'arm']) {
      for (const suffix of ['', '-m']) await check(`pbr/tex/${material.tex}_${kind}${suffix}.webp`);
    }
  }
  for (const material of Object.values(inlineData(html, 'JV_PLANT_MATS').data)) {
    for (const kind of ['c', 'n', 'r']) if (material[kind]) {
      for (const suffix of ['', '-m']) await check(`plants/tex/${material[kind]}${suffix}.webp`);
    }
  }
}

for (const target of Object.values(importMap)) if (!target.endsWith('/')) await check(target);
for (let i = 0; i < scriptQueue.length; i++) {
  const file = scriptQueue[i], source = await readFile(file, 'utf8');
  const syntax = spawnSync(process.execPath, ['--check', file], { encoding: 'utf8' });
  if (syntax.status !== 0) errors.push(`${path.relative(dist, file)}: ${syntax.stderr}`);
  for (const [, specifier] of source.matchAll(/^\s*import\s+(?:[^;'"]*?\s+from\s*)?['"]([^'"]+)['"]/gm)) {
    if (specifier.startsWith('.')) await check(specifier, path.dirname(file));
    else if (importMap[specifier]) await check(importMap[specifier]);
    else {
      const prefix = Object.keys(importMap).filter(key => key.endsWith('/') && specifier.startsWith(key)).sort((a, b) => b.length - a.length)[0];
      if (prefix) await check(importMap[prefix] + specifier.slice(prefix.length));
      else if (!external.test(specifier)) errors.push(`Unmapped import in ${path.relative(dist, file)}: ${specifier}`);
    }
  }
}
const css = await readFile(path.join(dist, 'assets', 'site.css'), 'utf8');
for (const [, url] of css.matchAll(/url\(['"]?([^'"\s)]+)['"]?\)/g)) await check(url, path.join(dist, 'assets'));
if (errors.length) {
  console.error('Website validation failed:\n' + errors.map(error => `- ${error}`).join('\n'));
  process.exitCode = 1;
} else console.log(`Website ready: 2 pages, ${checked.size} local files validated (including desktop/mobile assets and module imports).`);
