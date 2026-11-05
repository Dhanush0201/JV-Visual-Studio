// Web post-process for the PBR GLBs:
//  · UV slots fixed: the material UV set ('mat', world metres) → TEXCOORD_0, the lightmap set ('lm') → TEXCOORD_1.
//    Bake export tags them with a base-colour texture on 'mat' and an emissive texture on 'lm'; tags are stripped here.
//  · no normals on per-vertex-coloured meshes; quantise positions/normals/colours; UVs stay float; dedup; meshopt.
import { NodeIO } from '@gltf-transform/core';
import { KHRONOS_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions';
import { MeshoptEncoder } from 'meshoptimizer';
import { quantize, dedup, prune, reorder } from '@gltf-transform/functions';
const [,, inp, out] = process.argv;
await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions([...KHRONOS_EXTENSIONS, EXTMeshoptCompression]).registerDependencies({ 'meshopt.encoder': MeshoptEncoder });
const doc = await io.read(inp);
let fixed = 0, missing = 0;
for (const mesh of doc.getRoot().listMeshes())
  for (const prim of mesh.listPrimitives()) {
    if (prim.getAttribute('COLOR_0')) prim.setAttribute('NORMAL', null);
    const mat = prim.getMaterial();
    if (!mat || !mat.getBaseColorTexture()) continue;
    const iMat = mat.getBaseColorTextureInfo().getTexCoord(), iLm = mat.getEmissiveTexture() ? mat.getEmissiveTextureInfo().getTexCoord() : -1;
    const a = prim.getAttribute(`TEXCOORD_${iMat}`), b = iLm >= 0 ? prim.getAttribute(`TEXCOORD_${iLm}`) : null;
    if (!a || !b) { missing++; continue; }
    for (const s of prim.listSemantics()) if (s.startsWith('TEXCOORD_')) prim.setAttribute(s, null);
    prim.setAttribute('TEXCOORD_0', a); prim.setAttribute('TEXCOORD_1', b); fixed++;
  }
for (const mat of doc.getRoot().listMaterials()) {
  mat.setBaseColorTexture(null); mat.setEmissiveTexture(null); mat.setEmissiveFactor([0, 0, 0]);
}
await doc.transform(prune({ keepAttributes: true }), dedup({ keepUniqueNames: true }), reorder({ encoder: MeshoptEncoder, target: 'size' }), quantize({ pattern: /^(POSITION|NORMAL|COLOR_0)$/, quantizePosition: 16, quantizeNormal: 10, quantizeColor: 8 }));
// EXT_meshopt_compression without filters: UVs stay float (world-metre material UVs need the range)
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE });
await io.write(out, doc);
console.log('wrote', out, 'uv-fixed', fixed, 'missing', missing);
