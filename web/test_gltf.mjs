/**
 * The .glb the 3D environment hands the learner, opened and checked.
 *
 * meta/registry/metaverse.json says the exports are "plain Khronos glTF of
 * this bundle's own original meshes", and web/trade_craft_3d.html writes
 * them through three.js's GLTFExporter as a binary .glb. Until this file,
 * nothing in the bundle had ever opened one of those files: the claim
 * rested on the exporter's reputation. This suite captures the bytes the
 * page actually produces and holds them to the glTF 2.0 container rules
 * and to referential integrity - the checks a consumer performs before it
 * reads a single vertex.
 *
 * WHAT THIS IS, AND IS NOT. It is a container-and-references check written
 * from the glTF 2.0 rules this file states in RULES below. It is NOT
 * Khronos conformance: the glTF 2.0 JSON schema and the official
 * gltf-validator were not reachable from the build that wrote this (the
 * network is blocked), so neither is applied, and nothing here validates
 * material or texture semantics, animation, skins or morph targets. The
 * registry (meta/registry/metaverse.json, structural_validation) records
 * that boundary from this file's own RULES table; the not-covered list is
 * read back from the registry and printed below so a green run carries
 * its omissions with it. The counts - bytes, accessors, nodes - are never
 * typed in the registry: they come from the capture and live only in this
 * run's output.
 *
 * TWO MODES.
 *   node web/test_gltf.mjs             static: the export path in the BUILT
 *       page, the registry's rule list against this file, and a self-test
 *       of the validator on a synthetic one-triangle .glb - every rule
 *       passes on it, then every mutation fails its named rule. Runs
 *       browser-free in verify_all.sh and says plainly that no export was
 *       captured.
 *   node web/test_gltf.mjs --browser   serves the bundle on 127.0.0.1 (port
 *       8877 unless --port=), opens the page in headless Chromium, drives
 *       it to a hall and to the locker, presses the page's own .glb
 *       button, captures the Blob at URL.createObjectURL and the download
 *       the browser received, validates every capture, and re-runs the
 *       mutation drills on the real bytes. The default hall is the first
 *       of the page's roster (D.halls[0]); one hall and the locker take
 *       under a minute here, the whole roster over half an hour.
 *       --hall=<slug>   that hall instead of the first
 *       --all           every hall of the roster, then the locker
 *       --save=<dir>    keep the first hall's and the avatar's .glb
 *   node web/test_gltf.mjs --glb=<file>   validate a .glb on disk (an
 *       artifact download, say) with the same rules, no browser.
 *
 * Operator note for this container: one Chromium at a time. Check
 * `pgrep -f chrome-linux/chrome` is empty before a --browser run.
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { spawn, execFileSync } from 'node:child_process';
import { connect } from 'node:net';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const args = process.argv.slice(2);
const arg = (k) => {
  const hit = args.find((a) => a.startsWith(`--${k}=`));
  return hit === undefined ? null : hit.slice(k.length + 3);
};
const WANT_BROWSER = args.includes('--browser');
const PORT = arg('port') === null ? 8877 : Number(arg('port'));
const ONE_HALL = arg('hall');
const ALL_HALLS = args.includes('--all');
if (ONE_HALL !== null && ALL_HALLS) { console.error('FAIL', '--hall= and --all exclude each other'); process.exit(1); }
const SAVE_DIR = arg('save');
const GLB_FILE = arg('glb');

let n = 0;
// whatever a FAIL leaves running is torn down first: under --browser this
// kills the Chromium this run launched (its own child, by pid, never
// another) and the loopback server. A FAIL that left a browser behind
// would block the next run's one-Chromium rule (see below).
let teardown = () => {};
const fail = (m, detail) => {
  console.error('FAIL', m);
  if (detail) for (const d of [].concat(detail)) console.error('      ', d);
  teardown();
  process.exit(1);
};
const ok = (m, c, detail) => {
  if (!c) fail(m, detail);
  n++; console.log('  ok ', m);
};
process.on('exit', () => teardown());
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => process.exit(130));
// a missing field is a failure that names its path - never a default
const need = (obj, path, where) => {
  let v = obj;
  for (const k of path.split('.')) {
    if (v === null || typeof v !== 'object' || !(k in v))
      throw new Error(`missing field ${path} in ${where}`);
    v = v[k];
  }
  return v;
};

/* ============================================================ the rules === */
/* ONE TRUTH: this table is the rule list. meta/build.py reads it out of
   this file into the registry and meta/test.mjs holds the two equal, so
   the registry can never claim a rule this file does not run. Keep each
   `what` free of apostrophes - the builder reads it with a plain regex. */
const RULES = [
  { id: 'glb-magic', what: 'the first four header bytes are the ASCII magic glTF (0x46546C67, little-endian)' },
  { id: 'glb-version', what: 'the header version field is 2' },
  { id: 'glb-total-length', what: 'the header length field equals the byte count of the file, and that count is a multiple of 4' },
  { id: 'chunk-tiling', what: 'every chunk declares a length that is a multiple of 4 and fits inside the file, and the chunks tile the file exactly from byte 12 to the end with nothing left over' },
  { id: 'chunk-order', what: 'the first chunk is JSON, the second is BIN, no other BIN chunk exists, and the JSON chunk is padded with spaces (0x20) only' },
  { id: 'json-asset', what: 'the JSON chunk decodes as UTF-8 to an object whose asset.version is the string 2.0' },
  { id: 'buffer-bin', what: 'exactly one buffer, with no uri; the BIN chunk is at least buffers[0].byteLength long and at most 3 bytes longer (the alignment padding the spec allows), and those padding bytes are zero' },
  { id: 'bufferview-bounds', what: 'every bufferView names a buffer that exists and lies inside it (byteOffset plus byteLength within the buffer byteLength); a byteStride, when present, is a multiple of 4 between 4 and 252' },
  { id: 'accessor-bounds', what: 'every accessor names a bufferView that exists, has a known componentType and type, a count of at least 1, its last element ends inside the bufferView, and its absolute byte offset is aligned to its component size' },
  { id: 'primitive-refs', what: 'every mesh primitive carries a POSITION attribute, every attribute and indices accessor it names exists, its material (when named) exists, and its mode (when present) is 0 to 6' },
  { id: 'index-range', what: 'for every indexed primitive, every index read from the BIN chunk is below the count of its POSITION accessor' },
  { id: 'node-refs', what: 'every node names a mesh that exists (when it has one) and children that exist and are not itself, and no node is the child of two parents' },
  { id: 'scene-refs', what: 'every scene names nodes that exist and that have no parent, and the default scene index (when present) exists' },
  { id: 'material-texture-refs', what: 'every texture reference in a material names a texture that exists, every texture names an image that exists, and every image names a bufferView that exists with a mimeType and carries no uri' },
  { id: 'no-required-extensions', what: 'extensionsRequired is absent or empty, so no consumer must reject the file for an extension it lacks; every extensionsUsed entry is a string' },
  { id: 'no-animations', what: 'no animations array is present - the registry claims a rest-pose export with no clip' },
];

const MAGIC = 0x46546C67, TYPE_JSON = 0x4E4F534A, TYPE_BIN = 0x004E4942;
// the same four fields as the ASCII the spec spells them in - the fixture
// below is written from THESE, so a wrong constant above cannot agree with
// a fixture written from the same wrong constant (spec section 23.5)
const ASCII_U32 = (s) => new DataView(new TextEncoder().encode(s).buffer).getUint32(0, true);
const COMPONENT_BYTES = { 5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4 };
const TYPE_ITEMS = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT2: 4, MAT3: 9, MAT4: 16 };

/** Parse the container. Returns chunks and the JSON, or the reason it could not. */
function parseGlb(bytes) {
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const out = { bytes, magic: null, version: null, length: null, chunks: [], json: null, jsonText: null, jsonErr: null };
  if (bytes.length < 12) { out.jsonErr = `file is ${bytes.length} bytes, shorter than the 12-byte header`; return out; }
  out.magic = dv.getUint32(0, true);
  out.version = dv.getUint32(4, true);
  out.length = dv.getUint32(8, true);
  let off = 12;
  while (off + 8 <= bytes.length) {
    const len = dv.getUint32(off, true), type = dv.getUint32(off + 4, true);
    out.chunks.push({ off, len, type, dataOff: off + 8, fits: off + 8 + len <= bytes.length });
    if (off + 8 + len > bytes.length) break;
    off += 8 + len;
  }
  out.tail = bytes.length - off; // bytes after the last chunk that fit
  const jc = out.chunks.find((c) => c.type === TYPE_JSON);
  if (jc && jc.fits) {
    const raw = bytes.subarray(jc.dataOff, jc.dataOff + jc.len);
    let end = raw.length;
    while (end > 0 && raw[end - 1] === 0x20) end--;
    out.jsonPad = raw.length - end;
    try {
      out.jsonText = new TextDecoder('utf-8', { fatal: true }).decode(raw.subarray(0, end));
      out.json = JSON.parse(out.jsonText);
    } catch (e) { out.jsonErr = String(e.message); }
  } else out.jsonErr = 'no JSON chunk fits inside the file';
  const bc = out.chunks.find((c) => c.type === TYPE_BIN);
  out.bin = bc && bc.fits ? bytes.subarray(bc.dataOff, bc.dataOff + bc.len) : null;
  return out;
}

/** Run every rule. Each result: { id, checked, failing, detail[] }. */
function validate(bytes) {
  const g = parseGlb(bytes);
  const res = [];
  const rule = (id, checked, fails) => res.push({ id, checked, failing: fails.length, detail: fails });
  const J = g.json;
  const list = (k) => (J && Array.isArray(J[k])) ? J[k] : [];

  rule('glb-magic', 1, g.magic === MAGIC ? [] : [`magic is 0x${(g.magic === null ? 0 : g.magic).toString(16)}, not 0x${MAGIC.toString(16)}`]);
  rule('glb-version', 1, g.version === 2 ? [] : [`version field is ${g.version}, not 2`]);
  rule('glb-total-length', 1, (() => {
    const f = [];
    if (g.length !== bytes.length) f.push(`header says ${g.length} bytes, the file is ${bytes.length}`);
    if (bytes.length % 4 !== 0) f.push(`file length ${bytes.length} is not a multiple of 4`);
    return f;
  })());
  rule('chunk-tiling', g.chunks.length, (() => {
    const f = [];
    g.chunks.forEach((c, i) => {
      if (c.len % 4 !== 0) f.push(`chunk ${i} length ${c.len} is not a multiple of 4`);
      if (!c.fits) f.push(`chunk ${i} declares ${c.len} bytes at offset ${c.dataOff} but the file ends at ${bytes.length}`);
    });
    if (g.tail !== 0 && g.chunks.every((c) => c.fits)) f.push(`${g.tail} bytes after the last chunk`);
    if (g.chunks.length === 0) f.push('no chunk at all');
    return f;
  })());
  rule('chunk-order', 1, (() => {
    const f = [];
    if (!g.chunks[0] || g.chunks[0].type !== TYPE_JSON) f.push('the first chunk is not JSON');
    if (!g.chunks[1] || g.chunks[1].type !== TYPE_BIN) f.push('the second chunk is not BIN');
    if (g.chunks.filter((c) => c.type === TYPE_BIN).length > 1) f.push('more than one BIN chunk');
    const jc = g.chunks.find((c) => c.type === TYPE_JSON);
    if (jc && jc.fits) {
      const raw = bytes.subarray(jc.dataOff, jc.dataOff + jc.len);
      // the JSON chunk is space-padded: after the closing brace only 0x20 may follow
      let end = raw.length;
      while (end > 0 && raw[end - 1] === 0x20) end--;
      if (end > 0 && raw[end - 1] !== 0x7D) f.push(`the JSON chunk ends in byte 0x${raw[end - 1].toString(16)} after its padding, not in a closing brace`);
    }
    return f;
  })());
  rule('json-asset', 1, (() => {
    if (g.jsonErr) return [`JSON chunk unreadable: ${g.jsonErr}`];
    if (!J || typeof J !== 'object') return ['JSON chunk is not an object'];
    if (!('asset' in J) || typeof J.asset !== 'object' || J.asset === null) return ['no asset object'];
    if (!('version' in J.asset)) return ['asset has no version'];
    return J.asset.version === '2.0' ? [] : [`asset.version is ${JSON.stringify(J.asset.version)}, not "2.0"`];
  })());
  if (!J) {
    // the reference rules need the JSON; without it each says so rather than
    // passing over nothing
    for (const id of ['buffer-bin', 'bufferview-bounds', 'accessor-bounds', 'primitive-refs',
      'index-range', 'node-refs', 'scene-refs', 'material-texture-refs',
      'no-required-extensions', 'no-animations'])
      rule(id, 0, ['not run: the JSON chunk could not be read']);
    return { g, res };
  }
  const buffers = list('buffers'), views = list('bufferViews'), accs = list('accessors');
  const meshes = list('meshes'), nodes = list('nodes'), scenes = list('scenes');
  const mats = list('materials'), texs = list('textures'), imgs = list('images');
  rule('buffer-bin', buffers.length, (() => {
    const f = [];
    if (buffers.length !== 1) f.push(`${buffers.length} buffers, a .glb carries exactly one`);
    const b = buffers[0];
    if (b && 'uri' in b) f.push('buffers[0] carries a uri; a .glb buffer is the BIN chunk');
    if (b && typeof b.byteLength !== 'number') f.push('buffers[0].byteLength missing');
    if (!g.bin) f.push('no BIN chunk fits inside the file');
    if (b && g.bin && typeof b.byteLength === 'number') {
      const pad = g.bin.length - b.byteLength;
      if (pad < 0) f.push(`BIN chunk is ${g.bin.length} bytes, shorter than buffers[0].byteLength ${b.byteLength}`);
      else if (pad > 3) f.push(`BIN chunk is ${g.bin.length} bytes, ${pad} more than buffers[0].byteLength ${b.byteLength}; at most 3 bytes of padding are allowed`);
      else for (let i = b.byteLength; i < g.bin.length; i++)
        if (g.bin[i] !== 0) { f.push(`BIN padding byte at ${i} is 0x${g.bin[i].toString(16)}, not zero`); break; }
    }
    return f;
  })());
  rule('bufferview-bounds', views.length, (() => {
    const f = [];
    views.forEach((v, i) => {
      if (typeof v.buffer !== 'number' || !buffers[v.buffer]) { f.push(`bufferViews[${i}] names buffer ${v.buffer}, which does not exist`); return; }
      const off = 'byteOffset' in v ? v.byteOffset : 0;
      if (typeof v.byteLength !== 'number') { f.push(`bufferViews[${i}] has no byteLength`); return; }
      if (off + v.byteLength > buffers[v.buffer].byteLength)
        f.push(`bufferViews[${i}] ends at ${off + v.byteLength}, past buffer ${v.buffer} byteLength ${buffers[v.buffer].byteLength}`);
      if ('byteStride' in v && (v.byteStride % 4 !== 0 || v.byteStride < 4 || v.byteStride > 252))
        f.push(`bufferViews[${i}] byteStride ${v.byteStride} is out of the 4..252 multiple-of-4 range`);
    });
    return f;
  })());
  rule('accessor-bounds', accs.length, (() => {
    const f = [];
    accs.forEach((a, i) => {
      if (!(a.componentType in COMPONENT_BYTES)) { f.push(`accessors[${i}] componentType ${a.componentType} unknown`); return; }
      if (!(a.type in TYPE_ITEMS)) { f.push(`accessors[${i}] type ${a.type} unknown`); return; }
      if (typeof a.count !== 'number' || a.count < 1) { f.push(`accessors[${i}] count ${a.count} is not at least 1`); return; }
      if (!('bufferView' in a)) { f.push(`accessors[${i}] has no bufferView (a zero-filled accessor; this exporter never writes one)`); return; }
      const v = views[a.bufferView];
      if (!v) { f.push(`accessors[${i}] names bufferView ${a.bufferView}, which does not exist`); return; }
      const cb = COMPONENT_BYTES[a.componentType], elem = cb * TYPE_ITEMS[a.type];
      const stride = 'byteStride' in v ? v.byteStride : elem;
      const off = 'byteOffset' in a ? a.byteOffset : 0;
      const end = off + stride * (a.count - 1) + elem;
      if (end > v.byteLength) f.push(`accessors[${i}] ends at byte ${end} of bufferView ${a.bufferView}, whose byteLength is ${v.byteLength}`);
      const voff = 'byteOffset' in v ? v.byteOffset : 0;
      if ((voff + off) % cb !== 0) f.push(`accessors[${i}] absolute offset ${voff + off} is not aligned to its ${cb}-byte component`);
    });
    return f;
  })());
  const prims = meshes.flatMap((m, mi) => (Array.isArray(m.primitives) ? m.primitives : []).map((p, pi) => ({ p, at: `meshes[${mi}].primitives[${pi}]` })));
  rule('primitive-refs', prims.length, (() => {
    const f = [];
    for (const { p, at } of prims) {
      if (!p.attributes || typeof p.attributes !== 'object') { f.push(`${at} has no attributes`); continue; }
      if (!('POSITION' in p.attributes)) f.push(`${at} has no POSITION attribute`);
      for (const [k, ai] of Object.entries(p.attributes))
        if (!accs[ai]) f.push(`${at} attribute ${k} names accessor ${ai}, which does not exist`);
      if ('indices' in p && !accs[p.indices]) f.push(`${at} indices names accessor ${p.indices}, which does not exist`);
      if ('material' in p && !mats[p.material]) f.push(`${at} names material ${p.material}, which does not exist`);
      if ('mode' in p && !(Number.isInteger(p.mode) && p.mode >= 0 && p.mode <= 6)) f.push(`${at} mode ${p.mode} is not 0..6`);
    }
    return f;
  })());
  const indexed = prims.filter(({ p }) => 'indices' in p);
  rule('index-range', indexed.length, (() => {
    const f = [];
    for (const { p, at } of indexed) {
      const ia = accs[p.indices], pa = p.attributes && accs[p.attributes.POSITION];
      if (!ia || !pa) { f.push(`${at}: indices or POSITION accessor missing (see primitive-refs)`); continue; }
      const v = views[ia.bufferView];
      if (!v || !g.bin || !(ia.componentType in COMPONENT_BYTES)) { f.push(`${at}: index bufferView unreadable`); continue; }
      const cb = COMPONENT_BYTES[ia.componentType];
      const base = ('byteOffset' in v ? v.byteOffset : 0) + ('byteOffset' in ia ? ia.byteOffset : 0);
      if (base + ia.count * cb > g.bin.length) { f.push(`${at}: index data runs past the BIN chunk`); continue; }
      const dv = new DataView(g.bin.buffer, g.bin.byteOffset + base, ia.count * cb);
      let worst = -1;
      for (let k = 0; k < ia.count; k++) {
        const x = cb === 1 ? dv.getUint8(k) : cb === 2 ? dv.getUint16(k * 2, true) : dv.getUint32(k * 4, true);
        if (x > worst) worst = x;
      }
      if (worst >= pa.count) f.push(`${at}: an index reads ${worst} but POSITION has ${pa.count} vertices`);
    }
    return f;
  })());
  const parentOf = new Map();
  rule('node-refs', nodes.length, (() => {
    const f = [];
    nodes.forEach((nd, i) => {
      if ('mesh' in nd && !meshes[nd.mesh]) f.push(`nodes[${i}] names mesh ${nd.mesh}, which does not exist`);
      if ('children' in nd) for (const c of nd.children) {
        if (!nodes[c]) f.push(`nodes[${i}] names child ${c}, which does not exist`);
        else if (c === i) f.push(`nodes[${i}] is its own child`);
        else if (parentOf.has(c)) f.push(`nodes[${c}] is the child of both nodes[${parentOf.get(c)}] and nodes[${i}]`);
        else parentOf.set(c, i);
      }
    });
    return f;
  })());
  rule('scene-refs', scenes.length, (() => {
    const f = [];
    scenes.forEach((s, i) => {
      if (!Array.isArray(s.nodes)) { f.push(`scenes[${i}] has no nodes array`); return; }
      for (const ni of s.nodes) {
        if (!nodes[ni]) f.push(`scenes[${i}] names node ${ni}, which does not exist`);
        else if (parentOf.has(ni)) f.push(`scenes[${i}] root node ${ni} is also a child of nodes[${parentOf.get(ni)}]`);
      }
    });
    if ('scene' in J && !scenes[J.scene]) f.push(`default scene ${J.scene} does not exist`);
    return f;
  })());
  rule('material-texture-refs', mats.length + texs.length + imgs.length, (() => {
    const f = [];
    const texRef = (obj, at) => {
      if (!obj || typeof obj !== 'object') return;
      if ('index' in obj && !texs[obj.index]) f.push(`${at} names texture ${obj.index}, which does not exist`);
    };
    mats.forEach((m, i) => {
      const pbr = 'pbrMetallicRoughness' in m ? m.pbrMetallicRoughness : {};
      texRef(pbr.baseColorTexture, `materials[${i}].pbrMetallicRoughness.baseColorTexture`);
      texRef(pbr.metallicRoughnessTexture, `materials[${i}].pbrMetallicRoughness.metallicRoughnessTexture`);
      texRef(m.normalTexture, `materials[${i}].normalTexture`);
      texRef(m.occlusionTexture, `materials[${i}].occlusionTexture`);
      texRef(m.emissiveTexture, `materials[${i}].emissiveTexture`);
    });
    texs.forEach((t, i) => {
      if (!('source' in t)) f.push(`textures[${i}] has no source`);
      else if (!imgs[t.source]) f.push(`textures[${i}] names image ${t.source}, which does not exist`);
      if ('sampler' in t && !list('samplers')[t.sampler]) f.push(`textures[${i}] names sampler ${t.sampler}, which does not exist`);
    });
    imgs.forEach((im, i) => {
      if ('uri' in im) f.push(`images[${i}] carries a uri; a .glb image lives in a bufferView`);
      if (!('bufferView' in im)) f.push(`images[${i}] has no bufferView`);
      else if (!views[im.bufferView]) f.push(`images[${i}] names bufferView ${im.bufferView}, which does not exist`);
      if (!('mimeType' in im)) f.push(`images[${i}] has no mimeType`);
    });
    return f;
  })());
  rule('no-required-extensions', 1, (() => {
    const f = [];
    if ('extensionsRequired' in J && J.extensionsRequired.length > 0) f.push(`extensionsRequired: ${J.extensionsRequired.join(', ')}`);
    if ('extensionsUsed' in J && !J.extensionsUsed.every((x) => typeof x === 'string')) f.push('extensionsUsed has a non-string entry');
    return f;
  })());
  rule('no-animations', 1, 'animations' in J ? [`animations array present with ${J.animations.length} entries`] : []);
  return { g, res };
}

/** The table: every number says what it counts. */
function table(bytes, g) {
  const J = g.json;
  const jc = g.chunks.find((c) => c.type === TYPE_JSON), bc = g.chunks.find((c) => c.type === TYPE_BIN);
  const cnt = (k) => (J && Array.isArray(J[k]) ? J[k].length : 0);
  const rows = [
    ['file bytes', bytes.length, 'the whole .glb, header and both chunks'],
    ['json chunk bytes', jc ? jc.len : 0, 'the JSON chunk length field: text plus 0x20 padding'],
    ['json text bytes', g.jsonText === null ? 0 : jc.len - g.jsonPad, 'the JSON text before its padding'],
    ['bin chunk bytes', bc ? bc.len : 0, 'the BIN chunk length field: buffer plus zero padding'],
    ['buffers[0].byteLength', J && J.buffers && J.buffers[0] ? J.buffers[0].byteLength : 0, 'the buffer length the JSON declares'],
    ['buffers', cnt('buffers'), 'entries in buffers[]'],
    ['bufferViews', cnt('bufferViews'), 'entries in bufferViews[]'],
    ['accessors', cnt('accessors'), 'entries in accessors[]'],
    ['meshes', cnt('meshes'), 'entries in meshes[]'],
    ['primitives', J ? (J.meshes ? J.meshes.reduce((s, m) => s + (Array.isArray(m.primitives) ? m.primitives.length : 0), 0) : 0) : 0, 'primitives summed over every mesh'],
    ['nodes', cnt('nodes'), 'entries in nodes[]'],
    ['materials', cnt('materials'), 'entries in materials[]'],
    ['textures', cnt('textures'), 'entries in textures[]'],
    ['images', cnt('images'), 'entries in images[]'],
    ['scenes', cnt('scenes'), 'entries in scenes[]'],
  ];
  for (const [k, v, what] of rows) console.log(`      ${k.padEnd(24)} ${String(v).padStart(9)}   ${what}`);
}

function report(label, bytes, { full }) {
  const { g, res } = validate(bytes);
  if (full) { console.log(`      -- ${label}`); table(bytes, g); }
  const bad = res.filter((r) => r.failing > 0);
  if (full) for (const r of res) {
    const what = RULES.find((x) => x.id === r.id).what;
    ok(`[gltf] ${label} ${r.id}: ${what} - checked ${r.checked}, failing ${r.failing}`,
      r.failing === 0, r.detail);
  } else ok(`[gltf] ${label}: ${res.length} rules, checked ${res.reduce((s, r) => s + r.checked, 0)} items, failing ${bad.length}`,
    bad.length === 0, bad.flatMap((r) => [r.id, ...r.detail]));
  return { g, res };
}

/* ================================================= the mutation drills === */
/* Each drill changes the bytes in one named way and names the rule that
   must fail. A validator that has never been watched failing is a lint
   nobody runs (spec §23.3); these run on the synthetic fixture in static
   mode and on the captured bytes under --browser. */
function buildGlb(json, bin) {
  const enc = new TextEncoder().encode(JSON.stringify(json));
  const jpad = (4 - (enc.length % 4)) % 4, bpad = (4 - (bin.length % 4)) % 4;
  const total = 12 + 8 + enc.length + jpad + 8 + bin.length + bpad;
  const out = new Uint8Array(total), dv = new DataView(out.buffer);
  dv.setUint32(0, ASCII_U32('glTF'), true); dv.setUint32(4, 2, true); dv.setUint32(8, total, true);
  dv.setUint32(12, enc.length + jpad, true); dv.setUint32(16, ASCII_U32('JSON'), true);
  out.set(enc, 20); out.fill(0x20, 20 + enc.length, 20 + enc.length + jpad);
  const bo = 20 + enc.length + jpad;
  dv.setUint32(bo, bin.length + bpad, true); dv.setUint32(bo + 4, ASCII_U32('BIN\0'), true);
  out.set(bin, bo + 8);
  return out;
}
const bytesEqual = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
// a JSON-level mutation: parse, edit, re-pack around the same BIN bytes
const repack = (bytes, edit) => {
  const g = parseGlb(bytes);
  const j = JSON.parse(g.jsonText);
  const bl = j.buffers[0].byteLength;
  edit(j);
  return buildGlb(j, g.bin.subarray(0, bl));
};
const DRILLS = [
  { name: 'flip the first magic byte', expect: 'glb-magic',
    apply: (b) => { const m = b.slice(); m[0] = 0x00; return m; } },
  { name: 'set the header version to 3', expect: 'glb-version',
    apply: (b) => { const m = b.slice(); new DataView(m.buffer).setUint32(4, 3, true); return m; } },
  { name: 'add 4 to the header length field', expect: 'glb-total-length',
    apply: (b) => { const m = b.slice(); const dv = new DataView(m.buffer); dv.setUint32(8, dv.getUint32(8, true) + 4, true); return m; } },
  { name: 'cut the last 8 bytes off the BIN chunk, header length corrected, chunk length not', expect: 'chunk-tiling',
    apply: (b) => { const m = b.slice(0, b.length - 8); new DataView(m.buffer).setUint32(8, m.length, true); return m; } },
  { name: 'swap the JSON and BIN chunk type tags', expect: 'chunk-order',
    apply: (b) => {
      const m = b.slice(); const dv = new DataView(m.buffer); const g = parseGlb(b);
      dv.setUint32(g.chunks[0].off + 4, TYPE_BIN, true); dv.setUint32(g.chunks[1].off + 4, TYPE_JSON, true); return m;
    } },
  { name: 'overwrite the closing brace of the JSON text with a space', expect: 'json-asset',
    apply: (b) => { const g = parseGlb(b); const m = b.slice(); m[g.chunks[0].dataOff + g.chunks[0].len - g.jsonPad - 1] = 0x20; return m; } },
  { name: 'set asset.version to 1.0', expect: 'json-asset',
    apply: (b) => repack(b, (j) => { j.asset.version = '1.0'; }) },
  { name: 'cut 8 bytes off the BIN chunk with header and chunk length both corrected, buffers[0].byteLength not', expect: 'buffer-bin',
    apply: (b) => {
      const g = parseGlb(b); const m = b.slice(0, b.length - 8); const dv = new DataView(m.buffer);
      dv.setUint32(8, m.length, true); dv.setUint32(g.chunks[1].off, g.chunks[1].len - 8, true); return m;
    } },
  { name: 'give buffers[0] a uri', expect: 'buffer-bin',
    apply: (b) => repack(b, (j) => { j.buffers[0].uri = 'elsewhere.bin'; }) },
  { name: 'point bufferViews[0] at buffer 7', expect: 'bufferview-bounds',
    apply: (b) => repack(b, (j) => { j.bufferViews[0].buffer = 7; }) },
  { name: 'stretch bufferViews[0].byteLength past the buffer', expect: 'bufferview-bounds',
    apply: (b) => repack(b, (j) => { j.bufferViews[0].byteLength = j.buffers[0].byteLength + 4; }) },
  { name: 'point accessors[0] at a bufferView that does not exist', expect: 'accessor-bounds',
    apply: (b) => repack(b, (j) => { j.accessors[0].bufferView = j.bufferViews.length + 5; }) },
  { name: 'multiply accessors[0].count by 1000', expect: 'accessor-bounds',
    apply: (b) => repack(b, (j) => { j.accessors[0].count *= 1000; }) },
  { name: 'point the first primitive POSITION at accessor 9999', expect: 'primitive-refs',
    apply: (b) => repack(b, (j) => { j.meshes[0].primitives[0].attributes.POSITION = 9999; }) },
  { name: 'drop the first primitive POSITION attribute', expect: 'primitive-refs',
    apply: (b) => repack(b, (j) => { delete j.meshes[0].primitives[0].attributes.POSITION; }) },
  { name: 'halve the POSITION count of the first indexed primitive so its indices overrun it', expect: 'index-range',
    apply: (b) => repack(b, (j) => {
      const p = j.meshes.flatMap((m) => m.primitives).find((x) => 'indices' in x);
      j.accessors[p.attributes.POSITION].count = 1;
    }) },
  { name: 'give nodes[0] a child that does not exist', expect: 'node-refs',
    apply: (b) => repack(b, (j) => { j.nodes[0].children = [j.nodes.length + 1]; }) },
  { name: 'make nodes[0] its own child', expect: 'node-refs',
    apply: (b) => repack(b, (j) => { j.nodes[0].children = [0]; }) },
  { name: 'point scenes[0] at a node that does not exist', expect: 'scene-refs',
    apply: (b) => repack(b, (j) => { j.scenes[0].nodes = [j.nodes.length + 1]; }) },
  { name: 'point the first material baseColorTexture at texture 9999', expect: 'material-texture-refs',
    apply: (b) => repack(b, (j) => {
      if (!('pbrMetallicRoughness' in j.materials[0])) j.materials[0].pbrMetallicRoughness = {};
      j.materials[0].pbrMetallicRoughness.baseColorTexture = { index: 9999 };
    }) },
  { name: 'declare a required extension', expect: 'no-required-extensions',
    apply: (b) => repack(b, (j) => { j.extensionsRequired = ['KHR_nothing_of_the_kind']; }) },
  { name: 'add an animations array', expect: 'no-animations',
    apply: (b) => repack(b, (j) => { j.animations = [{ channels: [], samplers: [] }]; }) },
];
function drill(label, bytes) {
  for (const d of DRILLS) {
    const m = d.apply(bytes);
    if (!(m instanceof Uint8Array) || bytesEqual(m, bytes)) fail(`[mutate] ${label} ${d.name}: the mutation did not change the bytes`);
    const { res } = validate(m);
    const hit = res.find((r) => r.id === d.expect);
    ok(`[mutate] ${label} ${d.name} -> ${d.expect} fails by name (${hit.failing > 0 ? hit.detail[0] : 'did not fail'})`,
      hit.failing > 0);
  }
}

/* ================================================================ static === */
ok('the magic and chunk-type constants the validator reads are the ASCII the glTF 2.0 spec spells them in: glTF, JSON, BIN followed by a zero byte, each read little-endian',
  MAGIC === ASCII_U32('glTF') && TYPE_JSON === ASCII_U32('JSON') && TYPE_BIN === ASCII_U32('BIN\0'));
const reg = JSON.parse(readFileSync(join(ROOT, 'meta/registry/metaverse.json'), 'utf8'));
const sv = need(reg, 'structural_validation', 'meta/registry/metaverse.json');
ok('the registry records this suite as the structural validator, and its rule list is this file\'s RULES table in order (one truth: this file; the registry a built copy)',
  need(sv, 'suite', 'structural_validation') === 'web/test_gltf.mjs'
  && JSON.stringify(need(sv, 'rules', 'structural_validation').map((r) => need(r, 'id', 'structural_validation.rules[]')))
    === JSON.stringify(RULES.map((r) => r.id))
  && sv.rules.every((r, i) => need(r, 'what', 'structural_validation.rules[]') === RULES[i].what));
ok('the registry says what this is - a container-and-references check - and what it is not: no schema, no conformance, no material or texture semantics, no animation',
  /container-and-references/.test(need(sv, 'scope', 'structural_validation'))
  && /not Khronos conformance/.test(sv.scope)
  && ['schema', 'gltf-validator', 'material', 'animation'].every((w) =>
    need(sv, 'not_covered', 'structural_validation').some((x) => x.toLowerCase().includes(w))));
console.log('      NOT VALIDATED (from the registry):');
for (const x of sv.not_covered) console.log('        - ' + x);
ok('the registry types no counts for the export: every number lives in this run\'s output',
  (function noNumbers(v) {
    if (typeof v === 'number') return false;
    if (Array.isArray(v)) return v.every(noNumbers);
    if (v && typeof v === 'object') return Object.values(v).every(noNumbers);
    return true;
  })(sv));

// the BUILT page, not the builder: the export path this suite drives
const page = readFileSync(join(ROOT, 'web/trade_craft_3d.html'), 'utf8');
const fnBody = (sig) => { const i = page.indexOf(sig); if (i < 0) return ''; return page.slice(i, page.indexOf('\n}\n', i)); };
const exportFn = fnBody('async function exportGlb(root, name) {');
ok('the built page exports through GLTFExporter with { binary: true } - the .glb container this suite parses',
  /new GLTFExporter\(\)\.parse\(exportable\(root\), res, rej, \{ binary: true \}\)/.test(exportFn));
ok('where no host mediates saves, the built page hands the bytes to URL.createObjectURL as a model/gltf-binary Blob and clicks a download anchor - the door this suite captures at',
  /a\.href = URL\.createObjectURL\(new Blob\(\[bin\], \{ type: 'model\/gltf-binary' \}\)\);/.test(exportFn)
  && /a\.download = name;\s*a\.click\(\);/.test(exportFn));
ok('the .glb button exports the locker avatar as tc-avatar.glb and a hall as tc-hall-<slug>.glb, by view',
  /if \(view === 'avatar' && avatarMesh\) exportGlb\(avatarMesh, 'tc-avatar\.glb'\);/.test(page)
  && /else if \(view === 'hall' && hallGroup\)\s*exportGlb\(hallGroup, 'tc-hall-' \+ slug \+ '\.glb'\);/.test(page)
  && /id="glbBtn"/.test(page));
ok('the built page exposes the hooks this suite drives: __tc3dDo("view", "hall:<slug>"), __tc3d().hallSlugs, and the locker button',
  /window\.__tc3dDo = \(fn, arg\) =>/.test(page)
  && page.includes("else if (what === 'hall') showHall(which")
  && /hallSlugs: D\.halls\.map\(\(h\) => h\.slug\)/.test(page)
  && /getElementById\('avaBtn'\)\.addEventListener\('click', showAvatar\)/.test(page));

// the validator itself, on a synthetic one-triangle file: passes whole, fails on every drill
const synth = (() => {
  const pos = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]);
  const idx = new Uint16Array([0, 1, 2, 0]); // 4th index pads the view to 8 bytes
  const bin = new Uint8Array(36 + 8); bin.set(new Uint8Array(pos.buffer), 0); bin.set(new Uint8Array(idx.buffer), 36);
  return buildGlb({
    asset: { version: '2.0', generator: 'web/test_gltf.mjs self-test' },
    scene: 0, scenes: [{ nodes: [0] }],
    nodes: [{ name: 'root', children: [1] }, { name: 'tri', mesh: 0 }],
    meshes: [{ primitives: [{ attributes: { POSITION: 0 }, indices: 1, material: 0, mode: 4 }] }],
    materials: [{ pbrMetallicRoughness: { baseColorFactor: [1, 1, 1, 1] } }],
    accessors: [
      { bufferView: 0, componentType: 5126, count: 3, type: 'VEC3', min: [0, 0, 0], max: [1, 1, 0] },
      { bufferView: 1, componentType: 5123, count: 3, type: 'SCALAR' }],
    bufferViews: [{ buffer: 0, byteOffset: 0, byteLength: 36 }, { buffer: 0, byteOffset: 36, byteLength: 8 }],
    buffers: [{ byteLength: 44 }],
  }, bin);
})();
report('self-test (synthetic one-triangle .glb)', synth, { full: true });
drill('self-test', synth);

if (GLB_FILE) {
  const bytes = new Uint8Array(readFileSync(GLB_FILE));
  report(`file ${GLB_FILE}`, bytes, { full: true });
}

/* =============================================================== browser === */
if (!WANT_BROWSER) {
  console.log('  --  [browser] the export was NOT captured: no browser ran, so nothing above says anything '
    + 'about the bytes the page produces. Pass --browser to serve the bundle, drive the page and validate '
    + 'a hall export and the locker export (--all for every hall).');
} else {
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  // ONE Chromium at a time in this container: other harnesses need it too.
  // Wait while another one runs; never kill it. pgrep exits 1 for "none";
  // any other failure (no pgrep at all) is an error, not an empty list -
  // a guard that cannot look must not report clear (spec section 23.1).
  // anchored to the executable: a shell whose command line merely mentions
  // the path (an operator's own pgrep, say) is not a browser
  const CHROMIUM_CMD = '^/opt/pw-browsers/chromium-[0-9]+/chrome-linux/chrome';
  const chromiumPids = () => {
    try { return execFileSync('pgrep', ['-f', CHROMIUM_CMD], { encoding: 'utf8' }).trim().split('\n').filter(Boolean); }
    catch (e) { if (e.status === 1) return []; throw e; }
  };
  const WAIT_MAX_MS = 15 * 60_000, WAIT_STEP_MS = 5_000;
  for (let waited = 0; chromiumPids().length > 0; waited += WAIT_STEP_MS) {
    if (waited >= WAIT_MAX_MS) fail(`[browser] another Chromium (pids ${chromiumPids().join(', ')}) was still running after ${WAIT_MAX_MS / 60_000} minutes; not launching a second one, and not killing it`);
    if (waited % 30_000 === 0) console.log(`      waiting: another Chromium is running (pids ${chromiumPids().join(', ')}); ${(WAIT_MAX_MS - waited) / 60_000} min left before giving up`);
    await new Promise((r) => setTimeout(r, WAIT_STEP_MS));
  }
  // serve the bundle ourselves on a loopback port nobody else uses
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1', '--directory', ROOT],
    { stdio: ['ignore', 'ignore', 'ignore'] });
  const waitPort = () => new Promise((res, rej) => {
    let tries = 0;
    const go = () => {
      const s = connect({ host: '127.0.0.1', port: PORT }, () => { s.destroy(); res(); });
      s.on('error', () => { s.destroy(); if (++tries > 100) rej(new Error(`port ${PORT} never opened`)); else setTimeout(go, 100); });
    };
    go();
  });
  const stop = () => { try { server.kill('SIGTERM'); } catch { /* already gone */ } };
  teardown = stop;
  await waitPort();
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
  });
  // from here a FAIL kills this run's own browser (the Chromium that is a
  // direct child of THIS process - never another run's) and the server,
  // synchronously, before exit
  const ownChromium = () => {
    try { return execFileSync('pgrep', ['-P', String(process.pid), '-f', CHROMIUM_CMD], { encoding: 'utf8' }).trim().split('\n').filter(Boolean); }
    catch (e) { if (e.status === 1) return []; throw e; }
  };
  const chromePids = ownChromium();
  if (chromePids.length !== 1) fail(`[browser] expected exactly one Chromium child of this process after launch, found ${chromePids.length}`);
  teardown = () => { for (const pid of chromePids) { try { process.kill(Number(pid), 'SIGKILL'); } catch { /* already gone */ } } stop(); };
  try {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, acceptDownloads: true });
    const pg = await ctx.newPage();
    const pageErrors = [];
    pg.on('pageerror', (e) => pageErrors.push(String(e)));
    // capture at the door: every Blob the page hands to URL.createObjectURL,
    // and the download name the anchor carried
    await pg.addInitScript(() => {
      const orig = URL.createObjectURL.bind(URL);
      window.__glbCaptured = [];
      URL.createObjectURL = (obj) => {
        const url = orig(obj);
        if (obj instanceof Blob) window.__glbCaptured.push({ blob: obj, type: obj.type, size: obj.size, url, download: null });
        return url;
      };
      const click = HTMLAnchorElement.prototype.click;
      HTMLAnchorElement.prototype.click = function () {
        const hit = window.__glbCaptured.find((c) => c.url === this.href);
        if (hit) hit.download = this.download;
        return click.call(this);
      };
    });
    await pg.goto(`http://127.0.0.1:${PORT}/web/trade_craft_3d.html`, { waitUntil: 'load' });
    await pg.waitForFunction(() => window.__tc3d, null, { timeout: 90_000 });
    await pg.waitForTimeout(2000);
    const slugs = await pg.evaluate(() => window.__tc3d().hallSlugs);
    ok(`[browser] the page booted and lists ${slugs.length} halls (D.halls, every slug)`, slugs.length > 0);

    const capture = async (label, drive, expectName) => {
      const before = await pg.evaluate(() => window.__glbCaptured.length);
      await drive();
      await pg.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
      const dlPromise = pg.waitForEvent('download', { timeout: 60_000 }).catch(() => null);
      await pg.click('#glbBtn');
      // the page catches its own export errors and writes them to the HUD
      // line; a Blob that never arrives is reported with that line, by name
      try { await pg.waitForFunction((k) => window.__glbCaptured.length > k, before, { timeout: 60_000 }); }
      catch (e) {
        fail(`[browser] ${label}: no Blob reached URL.createObjectURL within 60 s of pressing #glbBtn`,
          [`hint: ${await pg.evaluate(() => document.getElementById('hint').textContent)}`, String(e.message).split('\n')[0], ...pageErrors]);
      }
      const meta = await pg.evaluate((k) => {
        const c = window.__glbCaptured[k];
        return { type: c.type, size: c.size, download: c.download, hint: document.getElementById('hint').textContent };
      }, before);
      const b64 = await pg.evaluate(async (k) => {
        const u8 = new Uint8Array(await window.__glbCaptured[k].blob.arrayBuffer());
        let s = '';
        for (let j = 0; j < u8.length; j += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(j, j + 0x8000));
        return btoa(s);
      }, before);
      const bytes = new Uint8Array(Buffer.from(b64, 'base64'));
      const dl = await dlPromise;
      let dlBytes = null;
      if (dl) { const p = await dl.path(); if (p) dlBytes = new Uint8Array(readFileSync(p)); }
      return { label, bytes, meta, dlBytes, expectName };
    };
    const hallList = ALL_HALLS ? slugs : [ONE_HALL === null ? slugs[0] : ONE_HALL];
    if (ONE_HALL && !slugs.includes(ONE_HALL)) fail(`[browser] no such hall: ${ONE_HALL}`, [`the page lists: ${slugs.join(' ')}`]);
    const caps = [];
    for (const s of hallList)
      caps.push(await capture(`hall ${s}`, () => pg.evaluate((x) => window.__tc3dDo('view', 'hall:' + x), s), `tc-hall-${s}.glb`));
    caps.push(await capture('avatar (locker)', () => pg.click('#avaBtn'), 'tc-avatar.glb'));

    ok(`[browser] ${caps.length} exports captured (${hallList.length} halls and the locker avatar), each a model/gltf-binary Blob whose size is the byte count captured`,
      caps.every((c) => c.meta.type === 'model/gltf-binary' && c.meta.size === c.bytes.length),
      caps.filter((c) => !(c.meta.type === 'model/gltf-binary' && c.meta.size === c.bytes.length)).map((c) => `${c.label}: type=${c.meta.type} size=${c.meta.size} captured=${c.bytes.length}`));
    ok('[browser] every download anchor carried the file name the registry declares for that view (tc-hall-<slug>.glb, tc-avatar.glb)',
      caps.every((c) => c.meta.download === c.expectName),
      caps.filter((c) => c.meta.download !== c.expectName).map((c) => `${c.label}: anchor download=${c.meta.download} expected=${c.expectName}`));
    ok('[browser] the HUD line after each export names the file and the same KB the captured byte count gives ((bytes/1024).toFixed(0), as the page computes it)',
      caps.every((c) => c.meta.hint.startsWith(`${c.expectName} · ${(c.bytes.length / 1024).toFixed(0)} KB`)),
      caps.filter((c) => !c.meta.hint.startsWith(`${c.expectName} · ${(c.bytes.length / 1024).toFixed(0)} KB`)).map((c) => `${c.label}: hint="${c.meta.hint}"`));
    const withDl = caps.filter((c) => c.dlBytes !== null);
    ok(`[browser] the file the browser received as a download is byte-identical to the Blob the page built (${withDl.length} of ${caps.length} downloads reached the browser)`,
      withDl.length === caps.length && withDl.every((c) => bytesEqual(c.dlBytes, c.bytes)),
      caps.filter((c) => c.dlBytes === null || !bytesEqual(c.dlBytes, c.bytes)).map((c) => `${c.label}: download ${c.dlBytes === null ? 'not received' : 'differs'}`));
    ok('[browser] no page error was thrown while driving the views and exporting', pageErrors.length === 0, pageErrors);

    // full table and per-rule lines for the first hall and the avatar; one line per other hall
    const first = caps[0], avatar = caps[caps.length - 1];
    const results = new Map();
    results.set(first.label, report(first.label, first.bytes, { full: true }));
    for (const c of caps.slice(1, -1)) results.set(c.label, report(c.label, c.bytes, { full: false }));
    results.set(avatar.label, report(avatar.label, avatar.bytes, { full: true }));
    const totalChecked = [...results.values()].reduce((s, r) => s + r.res.reduce((t, x) => t + x.checked, 0), 0);
    console.log(`      ${caps.length} captures x ${RULES.length} rules, ${totalChecked} items checked in all (sum of every rule's checked count over every capture; ${hallList.length} of the page's ${slugs.length} halls${ALL_HALLS ? ', the whole roster' : ', pass --all for the whole roster'})`);

    // what the registry claims about the content, held to the captured JSON
    const rootNames = (r) => r.g.json.scenes[r.g.json.scene].nodes.map((i) => r.g.json.nodes[i].name);
    ok(`[browser] each hall export has one scene whose root node is tc-hall-<slug> (registry conventions.scene_naming)`,
      caps.slice(0, -1).every((c) => { const r = results.get(c.label); return r.g.json.scenes.length === 1 && rootNames(r).length === 1 && rootNames(r)[0] === `tc-hall-${c.label.slice(5)}`; }),
      caps.slice(0, -1).map((c) => `${c.label}: roots ${JSON.stringify(rootNames(results.get(c.label)))}`).slice(0, 5));
    const avNames = new Set(results.get(avatar.label).g.json.nodes.map((nd) => nd.name));
    ok(`[browser] the avatar export names every node the registry lists as the rig (${reg.conventions.avatar_rig.length} names: tc-avatar, the VRM bones, headwear)`,
      reg.conventions.avatar_rig.every((b) => avNames.has(b)),
      reg.conventions.avatar_rig.filter((b) => !avNames.has(b)).map((b) => `missing node ${b}`));
    ok('[browser] every capture is an indexed-triangle file with at least one image in a bufferView (the canvas textures the registry says the meshes carry) and no external uri anywhere',
      caps.every((c) => { const J = results.get(c.label).g.json; return J.meshes.length > 0 && J.images.length > 0 && J.images.every((im) => 'bufferView' in im && !('uri' in im)); }),
      caps.map((c) => { const J = results.get(c.label).g.json; return `${c.label}: meshes=${J.meshes.length} images=${J.images ? J.images.length : 0}`; }).slice(0, 5));

    // the drills again, on the real bytes
    drill(first.label, first.bytes);
    drill(avatar.label, avatar.bytes);

    if (SAVE_DIR) {
      mkdirSync(SAVE_DIR, { recursive: true });
      writeFileSync(join(SAVE_DIR, first.expectName), first.bytes);
      writeFileSync(join(SAVE_DIR, avatar.expectName), avatar.bytes);
      console.log(`      saved ${first.expectName} and ${avatar.expectName} under ${SAVE_DIR}`);
    }
    await ctx.close();
  } finally {
    await browser.close();
    stop();
  }
}

console.log(`web/test_gltf: ${n} checks passed${WANT_BROWSER ? '' : ' (static; the export was not captured)'}`);
