// Web post-process for the plant library GLB: drop embedded images (the site loads its own webp sets),
// keep UVs and normals, quantise positions/normals, meshopt-compress.
import { NodeIO } from '@gltf-transform/core';
import { KHRONOS_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions';
import { MeshoptEncoder } from 'meshoptimizer';
import { quantize, dedup, prune, reorder } from '@gltf-transform/functions';
const [,, inp, out, keepList] = process.argv;
const keep = keepList ? new Set(keepList.split(',')) : null;
await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions([...KHRONOS_EXTENSIONS, EXTMeshoptCompression]).registerDependencies({ 'meshopt.encoder': MeshoptEncoder });
const doc = await io.read(inp);
for (const m of doc.getRoot().listMaterials()) {
  m.setBaseColorTexture(null); m.setNormalTexture(null); m.setMetallicRoughnessTexture(null);
  m.setOcclusionTexture(null); m.setEmissiveTexture(null);
}
for (const t of doc.getRoot().listTextures()) t.dispose();
// only the prototypes this scene places (plus their lighter levels of detail)
if (keep) for (const n of doc.getRoot().listNodes()) if (!keep.has(n.getName())) { const m = n.getMesh(); n.dispose(); if (m && !m.listParents().some(x => x.propertyType === 'Node')) m.dispose(); }
await doc.transform(prune({ keepAttributes: true }), dedup({ keepUniqueNames: true }), reorder({ encoder: MeshoptEncoder, target: 'size' }),
  quantize({ pattern: /^(POSITION|NORMAL)$/, quantizePosition: 14, quantizeNormal: 8 }));
// UVs inside [0,1] go to normalised 16-bit (no texture transform needed); others stay float
let q16 = 0, kept = 0;
for (const mesh of doc.getRoot().listMeshes()) for (const prim of mesh.listPrimitives()) {
  const uv = prim.getAttribute('TEXCOORD_0'); if (!uv || uv.getComponentType() !== 5126) continue;
  const a = uv.getArray(); let lo = Infinity, hi = -Infinity;
  for (let i = 0; i < a.length; i++) { if (a[i] < lo) lo = a[i]; if (a[i] > hi) hi = a[i]; }
  if (lo < 0 || hi > 1) { kept++; continue; }
  const b = new Uint16Array(a.length); for (let i = 0; i < a.length; i++) b[i] = Math.round(a[i] * 65535);
  uv.setArray(b).setNormalized(true); q16++;
}
console.log('uv16', q16, 'uv float', kept);
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE });
await io.write(out, doc);
const names = doc.getRoot().listNodes().map(n => n.getName());
console.log('wrote', out, names.length, 'nodes');
