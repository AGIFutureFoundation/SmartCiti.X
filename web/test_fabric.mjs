/**
 * The spatial fabric's reference consumer, held to the registries it loads.
 *
 * `web/build_fabric.py` writes `web/trade_craft_fabric.html`: the page that
 * is handed `spatial/registry/fabric.json`, `geopose.json` and `som.json`
 * and does what a metaverse browser would do with them - resolves every
 * pose, plots it, walks every branch of the scene graph under its owner,
 * lists every service with its transport and its door. Every figure on it
 * is a claim about a registry, and every "placed" number is a claim about
 * what the page drew. This suite recomputes each claim from the registry
 * that owns it and holds the SHIPPED PAGE to the answer; with --browser it
 * opens the page in headless Chromium and counts what was actually PLACED.
 *
 * WHICH FILE EACH CHECK READS is in its message, always:
 *
 *   [registry]  the registries only - no page involved
 *   [shipped]   the built HTML, and the payload embedded in it
 *   [generator] web/build_fabric.py's own source, comments stripped
 *   [browser]   the rendered DOM in headless Chromium (--browser only)
 *
 * MATCH STRUCTURE, NEVER A SENTENCE. Every check reads an element, an id or
 * a data attribute: `data-fig`, `data-honesty`, `data-quote`, `data-tier`,
 * `data-pose`, `data-branch`, `data-node`, `data-door`, `data-transport`.
 * The honesty block is checked BY NAMED FIELD against fabric.json, not by
 * hunting a sentence: a check that searched the prose would match this
 * page's own explanation of what it is not.
 *
 * ONE QUANTITY PER FIGURE. The browser section prints one "placed N of M"
 * line per kind, and each counts a DIFFERENT thing, said in the line: poses
 * are circles on the map, branches are list items in the tree, nodes are
 * items under them, services are rows with a transport cell, links are
 * relative hrefs that answered 200 when fetched once. None stands in for
 * another; a pose count is not a branch count is not a link count.
 *
 * NO BROWSER BY DEFAULT. verify_all.sh opens no browser, so the default run
 * is static. `--browser` serves the bundle itself on 127.0.0.1:8866 (or
 * uses --origin / --url), opens the page in headless Chromium, counts the
 * DOM, fetches every relative link once, screenshots the page, and fails on
 * any page or console error.
 *
 *   node web/test_fabric.mjs
 *   node web/test_fabric.mjs --browser [--origin=http://127.0.0.1:8866] [--shot=/path.png]
 *   node web/test_fabric.mjs --page=/tmp/broken.html --root=/tmp/broken-root
 *
 * `--page` and `--root` exist for the mutation tests. FAIL is printed at
 * column zero on stderr; ok lines go to stdout.
 */
import { readFileSync, existsSync, statSync, createReadStream } from 'node:fs';
import { createServer } from 'node:http';
import { join, resolve, dirname, extname, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit === undefined ? null : hit.slice(name.length + 3);
};
const ROOT = resolve(arg('root') !== null ? arg('root') : join(HERE, '..'));
const PAGE = resolve(arg('page') !== null ? arg('page') : join(HERE, 'trade_craft_fabric.html'));
const GENERATOR = join(HERE, 'build_fabric.py');
const PORT = 8866;
const ORIGIN = arg('origin') !== null ? arg('origin') : `http://127.0.0.1:${PORT}`;
const PAGE_URL = arg('url') !== null ? arg('url') : `${ORIGIN}/web/${PAGE.split('/').pop()}`;
const SHOT = arg('shot') !== null ? arg('shot') : join(tmpdir(), 'trade_craft_fabric.png');
const WANT_BROWSER = args.includes('--browser');

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.error('FAIL  ' + m);
  for (const e of evidence) console.error('      ' + e);
};
/* a registry field this suite needs, or a failure naming the path - the
   suite reads the registries the way the generator does, with no default */
const must = (o, k, where) => {
  if (o === null || typeof o !== 'object') throw new Error(`${where}: expected an object to read ${k} from`);
  if (!(k in o)) throw new Error(`${where}: required field ${k} is missing`);
  return o[k];
};
const readJSON = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/* ------------------------------------------------------------ registries -- */
const FABRIC_PATH = 'spatial/registry/fabric.json';
const GEOPOSE_PATH = 'spatial/registry/geopose.json';
const SOM_PATH = 'spatial/registry/som.json';
const MANIFEST_PATH = 'pack/manifest.json';
const TIERS = new Set(['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED']);
const NAMED_HONESTY = ['geopose_claimed', 'no_heights_or_headings', 'ombi_not_claimed',
  'static_files_only_no_rmap', 'external_origins', 'not_loaded_in_any_browser'];

const fabricReg = readJSON(FABRIC_PATH);
const geoposeReg = readJSON(GEOPOSE_PATH);
const somReg = readJSON(SOM_PATH);
const manifest = readJSON(MANIFEST_PATH);
const FAB = must(fabricReg, 'fabric', FABRIC_PATH);
const PLACES = must(fabricReg, 'places', FABRIC_PATH);
const ANCHORED = must(fabricReg, 'anchored_content', FABRIC_PATH);
const SERVICES = must(fabricReg, 'services', FABRIC_PATH);
const EXTERNAL = must(fabricReg, 'external_origins', FABRIC_PATH);
const HONESTY = must(fabricReg, 'honesty', FABRIC_PATH);
const POSES = must(geoposeReg, 'poses', GEOPOSE_PATH);
const UNPOSED = must(geoposeReg, 'unposed', GEOPOSE_PATH);
const COUNTS = must(geoposeReg, 'counts', GEOPOSE_PATH);
const SOM_ROOT = must(somReg, 'root', SOM_PATH);
const BRANCHES = must(SOM_ROOT, 'branches', SOM_PATH + '#root');
const CHILDREN = BRANCHES.flatMap((b, bi) => must(b, 'children', `${SOM_PATH}#root.branches[${bi}]`)
  .map((c, ci) => [c, `${SOM_PATH}#root.branches[${bi}].children[${ci}]`]));

/* Everything the page claims, recomputed here from the registries - a second,
   independent count, written without looking at the generator's arithmetic. */
const poseRefs = POSES.map((p, i) => must(must(p, 'subject', `${GEOPOSE_PATH}#poses[${i}]`), 'ref', `${GEOPOSE_PATH}#poses[${i}].subject`));
const poseByRef = new Map(POSES.map((p, i) => [poseRefs[i], p]));
const isPlaceholder = (p) => {
  const q = p.geopose.position, o = p.geopose.orientation;
  return q.h === 0 && o.yaw === 0 && o.pitch === 0 && o.roll === 0;
};
const externalBranches = BRANCHES.filter((b, bi) => must(b, 'origin', `${SOM_PATH}#root.branches[${bi}]`) === 'external');
const fabricBranches = BRANCHES.filter((b) => b.origin === 'this fabric');
/* Every record that may carry a door, with the registry path the page keys
   it by. Presence is recomputed here, at test time: the suite assumes
   neither that doors exist nor that they do not. */
const DOOR_BEARERS = [
  ...BRANCHES.map((b, i) => [b, `${SOM_PATH}#root.branches[${i}]`]),
  ...CHILDREN,
  ...PLACES.map((r, i) => [r, `${FABRIC_PATH}#places[${i}]`]),
  ...SERVICES.map((r, i) => [r, `${FABRIC_PATH}#services[${i}]`]),
  ...ANCHORED.map((r, i) => [r, `${FABRIC_PATH}#anchored_content[${i}]`]),
];
/* a door's href, as the registry wrote it - string, or an object carrying one */
const doorHrefOf = (rec, where) => {
  const d = rec.door;
  if (typeof d === 'string') return d;
  if (d !== null && typeof d === 'object') return must(d, 'href', where + '.door');
  return null;
};
/* the same href re-based to web/, which is where the page lives */
const rebase = (href) => (/^https?:\/\//.test(href) ? href : href.replace(/^web\//, ''));
const DOORS = DOOR_BEARERS.filter(([r]) => 'door' in r && r.door !== null).map(([r, w]) => [w, doorHrefOf(r, w)]);
/* a null door is the registry refusing one; its why_no_door is read by name */
const REFUSED = DOOR_BEARERS.filter(([r]) => 'door' in r && r.door === null).map(([r, w]) => [w, must(r, 'why_no_door', w)]);
const UNDECLARED = DOOR_BEARERS.filter(([r]) => !('door' in r));

const R = {
  places: PLACES.length,
  'anchored-content': ANCHORED.length,
  services: SERVICES.length,
  'external-origins': EXTERNAL.length,
  poses: POSES.length,
  'poses-h-placeholder': POSES.filter(isPlaceholder).length,
  unposed: UNPOSED.length,
  branches: BRANCHES.length,
  'external-branches': externalBranches.length,
  'fabric-nodes': fabricBranches.reduce((a, b) => a + b.children.length, 0),
  'external-nodes': externalBranches.reduce((a, b) => a + b.children.length, 0),
  'nodes-posed': CHILDREN.filter(([c, w]) => must(c, 'geopose', w) !== null).length,
  'nodes-unposed': CHILDREN.filter(([c]) => c.geopose === null).length,
  'doors-declared': BRANCHES.filter((b) => 'door' in b).length,
  'doors-undeclared': BRANCHES.filter((b) => !('door' in b)).length,
  'doors-anywhere': DOORS.length,
  'doors-refused': REFUSED.length,
};

/* ------------------------------------------------------- the shipped page -- */
const html = readFileSync(PAGE, 'utf8');
function scriptsOf(text) {
  const out = [];
  const re = /<script\b[^>]*>/gi;
  let m;
  while ((m = re.exec(text)) !== null) {
    const close = text.indexOf('</script', m.index + m[0].length);
    out.push(text.slice(m.index + m[0].length, close < 0 ? text.length : close));
    re.lastIndex = close < 0 ? text.length : close;
  }
  return out;
}
const SCRIPTS = scriptsOf(html);
const RENDERER = (SCRIPTS.length > 1 ? SCRIPTS[1] : '')
  .replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');
function payloadOf() {
  const s = SCRIPTS.length ? SCRIPTS[0] : '';
  const i = s.indexOf('const DATA = ');
  if (i < 0) return null;
  const j = s.lastIndexOf(';');
  if (j < i) return null;
  try { return JSON.parse(s.slice(i + 'const DATA = '.length, j)); } catch { return null; }
}
const D = payloadOf();
const unescape = (s) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
  .replace(/&#x27;/g, "'").replace(/&amp;/g, '&');
function figs() {
  const out = new Map();
  const re = /<div class="fig" data-fig="([^"]+)"><b>([^<]*)<\/b>/g;
  let m;
  while ((m = re.exec(html)) !== null) out.set(m[1], Number(m[2].replace(/,/g, '')));
  return out;
}
function honestyItems() {
  const out = new Map();
  const re = /<li data-honesty="([^"]+)" data-honesty-shape="(sentence|json)"><b>[^<]*<\/b>([\s\S]*?)<\/li>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    if (out.has(m[1])) out.set(m[1], { dup: true });
    else if (m[2] === 'sentence') out.set(m[1], { value: unescape(m[3]) });
    else {
      const pre = /^<pre class="hj">([\s\S]*)<\/pre>$/.exec(m[3]);
      let value = null;
      try { value = pre ? JSON.parse(unescape(pre[1])) : null; } catch { value = null; }
      out.set(m[1], { value });
    }
  }
  return out;
}
const attrRows = (attr) => {
  const out = new Map();
  const re = new RegExp(`<tr ${attr}="([^"]+)"[^>]*>([\\s\\S]*?)<\\/tr>`, 'g');
  let m;
  while ((m = re.exec(html)) !== null) {
    out.set(m[1], [...m[2].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((c) => c[1]));
  }
  return out;
};
const quotes = () => {
  const out = new Map();
  const re = /<pre data-quote="([^"]+)"[^>]*>([\s\S]*?)<\/pre>/g;
  let m;
  while ((m = re.exec(html)) !== null) out.set(m[1], unescape(m[2]));
  return out;
};
const slotText = (id) => {
  const m = new RegExp(`<b id="${id}">([\\s\\S]*?)<\\/b>`).exec(html);
  return m === null ? null : m[1];
};

console.log(`fabric: page ${PAGE} (${html.length.toLocaleString('en-US')} bytes), registries under ${ROOT}`);

/* ================================================== 1. the registries alone */
{
  const stampsOff = [];
  for (const [p, reg] of [[FABRIC_PATH, fabricReg], [GEOPOSE_PATH, geoposeReg], [SOM_PATH, somReg]]) {
    if (must(reg, 'pack_version', p) !== must(manifest, 'pack_version', MANIFEST_PATH)) stampsOff.push(`${p} pack_version ${reg.pack_version}`);
    for (const k of ['built', 'source_stamp', 'pack', 'product']) {
      if (must(reg, k, p) !== must(fabricReg, k, FABRIC_PATH)) stampsOff.push(`${p} ${k} differs from ${FABRIC_PATH}`);
    }
    if (!same(must(reg, 'honesty', p), HONESTY)) stampsOff.push(`${p} honesty block differs from ${FABRIC_PATH}`);
  }
  ok(`[registry] the three registries carry ${MANIFEST_PATH}'s pack_version, one built date, one source `
    + 'stamp and one identical honesty block', stampsOff.length === 0, stampsOff);
}
{
  const kinds = {};
  for (const p of POSES) kinds[p.subject.kind] = (p.subject.kind in kinds ? kinds[p.subject.kind] : 0) + 1;
  const off = [];
  const want = { total: POSES.length, unposed: UNPOSED.length, campuses: kinds.campus, anchors: kinds.anchor,
    restoration_sites: kinds['restoration-site'] };
  for (const k of Object.keys(want)) if (must(COUNTS, k, GEOPOSE_PATH + '#counts') !== want[k]) off.push(`counts.${k}=${COUNTS[k]} records=${want[k]}`);
  ok(`[registry] ${GEOPOSE_PATH} counts equal its records: ${want.total} poses (${want.campuses} campuses, `
    + `${want.anchors} anchors, ${want.restoration_sites} restoration sites), ${want.unposed} unposed, `
    + 'and every subject ref is unique', off.length === 0 && poseByRef.size === POSES.length, off);
}
{
  const off = [];
  POSES.forEach((p, i) => {
    const w = `${GEOPOSE_PATH}#poses[${i}]`;
    const q = must(must(p, 'geopose', w), 'position', w), o = must(p.geopose, 'orientation', w);
    if (same(Object.keys(q).sort(), ['h', 'lat', 'lon']) === false || same(Object.keys(o).sort(), ['pitch', 'roll', 'yaw']) === false) off.push(`${w}: not Basic-YPR`);
    if (!isPlaceholder(p)) off.push(`${w}: h=${q.h} yaw/pitch/roll=${o.yaw}/${o.pitch}/${o.roll}`);
    if (!TIERS.has(must(must(p, 'provenance', w), 'position_horizontal', w))) off.push(`${w}: tier ${p.provenance.position_horizontal}`);
    for (const k of ['h_provenance', 'orientation_provenance', 'source']) must(p.provenance, k, w + '.provenance');
  });
  ok(`[registry] every one of the ${POSES.length} poses is Basic-YPR, carries h = 0 and yaw = pitch = roll = 0 `
    + 'with both UNKNOWN sidecars present, and a position tier of this bundle - so the '
    + `no_heights_or_headings field of ${FABRIC_PATH}#honesty is true of every record`,
    off.length === 0 && 'no_heights_or_headings' in HONESTY, off.slice(0, 4));
}
{
  const dangling = [];
  const chk = (ref, w) => { if (!poseByRef.has(ref)) dangling.push(`${w} -> ${ref}`); };
  PLACES.forEach((r, i) => chk(must(r, 'geopose', `${FABRIC_PATH}#places[${i}]`), `${FABRIC_PATH}#places[${i}]`));
  SERVICES.forEach((r, i) => {
    chk(must(r, 'anchored_at', `${FABRIC_PATH}#services[${i}]`), `${FABRIC_PATH}#services[${i}]`);
    if ('also_at' in r) for (const a of r.also_at) chk(a, `${FABRIC_PATH}#services[${i}].also_at`);
  });
  ANCHORED.forEach((r, i) => { const a = must(r, 'anchored_at', `${FABRIC_PATH}#anchored_content[${i}]`); if (a !== null) chk(a, `${FABRIC_PATH}#anchored_content[${i}]`); });
  EXTERNAL.forEach((r, i) => { for (const g of must(r, 'geoposes', `${FABRIC_PATH}#external_origins[${i}]`)) chk(g, `${FABRIC_PATH}#external_origins[${i}]`); });
  for (const [c, w] of CHILDREN) if (c.geopose !== null) chk(c.geopose, w);
  ok(`[registry] every geopose ref in ${FABRIC_PATH} and ${SOM_PATH} resolves to a pose in ${GEOPOSE_PATH} `
    + `(${R['nodes-posed']} posed nodes, ${R['nodes-unposed']} with no pose)`, dangling.length === 0, dangling.slice(0, 4));
}
{
  const off = [];
  const ic = must(must(somReg, 'invariants', SOM_PATH), 'counts', SOM_PATH + '#invariants');
  for (const [k, v] of [['branches', R.branches], ['external_branches', R['external-branches']], ['fabric_nodes', R['fabric-nodes']]]) {
    if (must(ic, k, SOM_PATH + '#invariants.counts') !== v) off.push(`invariants.counts.${k}=${ic[k]} walked=${v}`);
  }
  BRANCHES.forEach((b, bi) => {
    const w = `${SOM_PATH}#root.branches[${bi}]`;
    const served = must(b, 'served_by_this_fabric', w);
    if (b.origin === 'external' && served !== false) off.push(`${w}: external but served`);
    if (b.origin === 'this fabric' && served !== true) off.push(`${w}: this fabric but not served`);
    if (b.origin !== 'external' && b.origin !== 'this fabric') off.push(`${w}: origin ${b.origin}`);
    for (const t of must(b, 'provenance_tiers', w)) if (!TIERS.has(t)) off.push(`${w}: tier ${t}`);
    b.children.forEach((c, ci) => {
      if (c.served_by_this_fabric !== served) off.push(`${w}.children[${ci}]: served disagrees with branch`);
      if (b.origin === 'external' && ['place', 'content', 'service'].includes(c.kind)) off.push(`${w}.children[${ci}]: ${c.kind} under an external branch`);
      if (!TIERS.has(c.provenance)) off.push(`${w}.children[${ci}]: tier ${c.provenance}`);
    });
  });
  EXTERNAL.forEach((e, i) => { if (must(e, 'served_by_this_fabric', `${FABRIC_PATH}#external_origins[${i}]`) !== false) off.push(`external_origins[${i}] served`); });
  ok(`[registry] the scene graph walks to its own invariants: ${R.branches} branches, ${R['external-branches']} external `
    + `(none served, none holding a place, content or service), ${fabricBranches.length} of this fabric (served), `
    + `${R['fabric-nodes']} + ${R['external-nodes']} nodes; every external origin unserved`, off.length === 0, off.slice(0, 5));
}
{
  const off = [];
  for (const [w, href] of DOORS) {
    if (href === null || typeof href !== 'string' || !href) { off.push(`${w}.door is not a string href or an object carrying one`); continue; }
    if (/^https?:\/\//.test(href)) continue;
    const file = href.split(/[?#]/)[0];
    if (!file.startsWith('web/') || !existsSync(join(ROOT, file))) off.push(`${w}.door ${href} lands on no file under web/`);
  }
  for (const [w, why] of REFUSED) if (typeof why !== 'string' || !why) off.push(`${w}.why_no_door is not a sentence`);
  ok(`[registry] across ${DOOR_BEARERS.length} door-bearing records (branches, nodes, places, services, content): `
    + `${DOORS.length} declare a door that lands on a file under web/, ${REFUSED.length} refuse one with a why_no_door, `
    + `${UNDECLARED.length} declare none - all three recomputed here, none assumed`,
    off.length === 0 && DOORS.length + REFUSED.length + UNDECLARED.length === DOOR_BEARERS.length, off.slice(0, 4));
}

/* ============================================ 2. the page against those facts */
ok('[shipped] the page carries an embedded registry payload that parses', D !== null, ['the payload did not parse']);
if (D !== null) {
  const off = [];
  const pairs = [
    ['geopose.poses', D.geopose && D.geopose.poses, POSES], ['geopose.unposed', D.geopose && D.geopose.unposed, UNPOSED],
    ['geopose.counts', D.geopose && D.geopose.counts, COUNTS], ['som.root', D.som && D.som.root, SOM_ROOT],
    ['honesty', D.honesty, HONESTY], ['places', D.places, PLACES], ['services', D.services, SERVICES],
    ['externalOrigins', D.externalOrigins, EXTERNAL], ['anchored', D.anchored, ANCHORED], ['fabric', D.fabric, FAB],
    ['stamp', D.stamp, { pack: fabricReg.pack, pack_version: fabricReg.pack_version, built: fabricReg.built, source_stamp: fabricReg.source_stamp }],
  ];
  for (const [k, got, want] of pairs) if (!same(got, want)) off.push(`payload.${k} differs from the registry file`);
  ok(`[shipped] the embedded copy of ${GEOPOSE_PATH} (poses, unposed, counts), ${SOM_PATH} (root) and ${FABRIC_PATH} `
    + '(places, services, external origins, content, honesty, stamp) equals the files, record for record',
    off.length === 0, off);
  const paths = D.paths;
  ok('[shipped] the payload names the three registry paths it was built from',
    paths !== undefined && paths.fabric === FABRIC_PATH && paths.geopose === GEOPOSE_PATH && paths.som === SOM_PATH,
    [JSON.stringify(paths)]);
  /* doors in the payload: exactly the records that declare one, re-based to web/ */
  const dh = D.doorHref;
  const doorOff = [];
  if (dh === undefined || dh === null || typeof dh !== 'object') doorOff.push('payload.doorHref missing');
  else {
    for (const [w, href] of DOORS) {
      if (!(w in dh)) doorOff.push(`payload.doorHref lacks ${w}`);
      else if (dh[w] !== rebase(href)) doorOff.push(`${w}: page ${dh[w]} vs registry ${href} re-based`);
    }
    for (const w of Object.keys(dh)) if (!DOORS.some(([x]) => x === w)) doorOff.push(`payload.doorHref carries ${w}, which declares no door`);
  }
  const dr = D.doorRefused;
  if (dr === undefined || dr === null || typeof dr !== 'object') doorOff.push('payload.doorRefused missing');
  else {
    for (const [w, why] of REFUSED) if (dr[w] !== why) doorOff.push(`payload.doorRefused[${w}] is not the registry's why_no_door`);
    for (const w of Object.keys(dr)) if (!REFUSED.some(([x]) => x === w)) doorOff.push(`payload.doorRefused carries ${w}, whose door is not null`);
  }
  ok(`[shipped] the payload's door maps hold exactly the ${DOORS.length} declared door(s), each the registry's own href `
    + `re-based from web/ to the page's location, and exactly the ${REFUSED.length} refused one(s) with the registry's own `
    + 'why_no_door - none invented, none dropped', doorOff.length === 0, doorOff.slice(0, 4));
}

/* ------------------------------------- the keyed figures, element by element */
{
  const f = figs();
  const wrong = [];
  for (const [k, v] of Object.entries(R)) {
    if (!f.has(k)) { wrong.push(`no <div class="fig" data-fig="${k}"> on the page`); continue; }
    if (f.get(k) !== v) wrong.push(`data-fig="${k}": page ${f.get(k)}, registry ${v}`);
  }
  for (const k of f.keys()) if (!(k in R)) wrong.push(`data-fig="${k}" on the page is a figure this suite does not recompute`);
  ok(`[shipped] every one of the ${Object.keys(R).length} keyed figures equals the number recomputed from the registry `
    + 'that owns it, and the page carries no keyed figure this suite does not recompute', wrong.length === 0, wrong.slice(0, 6));
}

/* ---------------------------------------- the honesty block, by named field */
{
  const items = honestyItems();
  const off = [];
  for (const k of Object.keys(HONESTY)) {
    if (!items.has(k)) { off.push(`no <li data-honesty="${k}">`); continue; }
    if (items.get(k).dup) { off.push(`data-honesty="${k}" appears twice`); continue; }
    if (!same(items.get(k).value, HONESTY[k])) off.push(`data-honesty="${k}" is not the registry's text, verbatim`);
  }
  for (const k of items.keys()) if (!(k in HONESTY)) off.push(`data-honesty="${k}" is not a field of ${FABRIC_PATH}#honesty`);
  const namedMissing = NAMED_HONESTY.filter((k) => !(k in HONESTY));
  ok(`[shipped] all ${Object.keys(HONESTY).length} fields of ${FABRIC_PATH}#honesty are on the page, each in its own `
    + `<li data-honesty="field"> with the registry's value verbatim (sentence or JSON), no extra field, and the named fields `
    + `${NAMED_HONESTY.join(', ')} exist in the registry`, off.length === 0 && namedMissing.length === 0,
    [...off.slice(0, 4), ...namedMissing.map((k) => `${FABRIC_PATH}#honesty.${k} is missing`)]);
}
{
  const lead = html.indexOf('<section class="lead" id="limits">');
  const firstHonesty = html.indexOf('<li data-honesty="');
  const figsAt = html.indexOf('<section class="figs">');
  const mapAt = html.indexOf('<svg id="map"');
  const somAt = html.indexOf('<ul class="som" id="som">');
  ok('[shipped] the honesty block is where a visitor reads first: inside #limits, above the figures, above the map, '
    + 'above the scene graph', lead >= 0 && firstHonesty > lead && figsAt > firstHonesty && mapAt > figsAt && somAt > mapAt,
    [`limits=${lead} honesty=${firstHonesty} figs=${figsAt} map=${mapAt} som=${somAt}`]);
  const consumer = /<p class="consumer" id="consumer" data-consumer="([^"]*)" data-not-loaded-in="([^"]*)"\s+data-measured-by="([^"]*)">/.exec(html);
  ok('[shipped] the consumer element names itself as web/trade_craft_fabric.html, names Sneeze and Artemis as browsers it '
    + 'has NOT been loaded in, and names this suite as what measures it - as attributes, not prose',
    consumer !== null && consumer[1] === 'web/trade_craft_fabric.html' && consumer[2].split(/,\s*/).includes('Sneeze')
    && consumer[2].split(/,\s*/).includes('Artemis') && consumer[3] === 'web/test_fabric.mjs',
    [consumer === null ? 'no #consumer element with the three attributes' : consumer[0]]);
}
{
  const q = quotes();
  ok(`[shipped] the shape sentence quoted on the page is ${SOM_PATH}#shape, which is ${FABRIC_PATH}#fabric.shape, verbatim; `
    + `the composition sentence is ${SOM_PATH}#root.composition, verbatim`,
    q.get('shape') === must(somReg, 'shape', SOM_PATH) && somReg.shape === must(FAB, 'shape', FABRIC_PATH + '#fabric')
    && q.get('composition') === must(SOM_ROOT, 'composition', SOM_PATH + '#root'),
    [`shape: ${q.get('shape')}`, `composition: ${q.get('composition')}`]);
}

/* ------------------------------------------------------------- provenance */
{
  const tiers = [...html.matchAll(/data-tier="([^"]*)"/g)].map((m) => m[1]);
  const outside = tiers.filter((t) => !TIERS.has(t));
  ok(`[shipped] every provenance tier on the page (${tiers.length} data-tier attributes) is one of `
    + `${[...TIERS].join(' / ')}, and none is AI-SYNTHESIZED`, tiers.length > 0 && outside.length === 0,
    outside.length ? outside.slice(0, 4).map((t) => `data-tier="${t}"`) : ['the page declares no data-tier at all']);
}

/* ----------------------------------------------- the placed slots ship EMPTY */
{
  const want = ['placed-poses', 'placed-inset-poses', 'placed-branches', 'placed-nodes', 'placed-node-poses'];
  const filled = want.filter((k) => slotText(k) === null || slotText(k).trim() !== '');
  ok(`[shipped] all ${want.length} "placed" slots ship EMPTY - the page types no placed count, the renderer fills each from `
    + 'the elements it drew', filled.length === 0, filled.map((k) => `#${k} holds ${JSON.stringify(slotText(k))}`));
}
ok('[shipped] the renderer fills #placed-poses by counting [data-pose] marks in #map and #placed-branches by counting '
  + '[data-branch] items in #som - from the DOM, never from a number of its own',
  /getElementById\('placed-poses'\)\.textContent\s*=\s*map\.querySelectorAll\('\[data-pose\]'\)\.length/.test(RENDERER)
  && /getElementById\('placed-branches'\)\.textContent\s*=\s*som\.querySelectorAll\('\[data-branch\]'\)\.length/.test(RENDERER),
  ['the renderer, comments stripped, does not derive the placed slots from the DOM']);
ok('[shipped] the renderer fails closed by name: an unresolvable geopose ref throws naming the registry path, a node with '
  + 'no pose and no registry reason throws, a door that is not a string or an object with href throws; no `??` anywhere in it',
  /function pose\(ref, where\) \{\s*if \(!byRef\.has\(ref\)\) throw new Error\(where \+ ': geopose ref '/.test(RENDERER)
  && /must\(must\(D, 'unplacedWhy', 'payload'\), name, cw \+ ' \(no geopose\)'\)/.test(RENDERER)
  && /function doorText\(d, where\) \{[\s\S]{0,400}?throw new Error\(where \+ '\.door: a door is a string href/.test(RENDERER)
  && !/\?\?/.test(RENDERER),
  ['a fail-closed throw is missing from the renderer, or a ?? survives in it']);

/* --------------------------------------------- the static tables, row by row */
{
  const rows = attrRows('data-pose-row');
  const off = [];
  for (const [ref, p] of poseByRef) {
    if (!rows.has(ref)) { off.push(`no <tr data-pose-row="${ref}">`); continue; }
    const cells = rows.get(ref);
    const lat = /<td class="num" data-lat>([^<]*)<\/td>/.exec(`<td class="num" data-lat>${cells[3]}</td>`);
    if (Number(cells[3]) !== p.geopose.position.lat || Number(cells[4]) !== p.geopose.position.lon) off.push(`${ref}: lat/lon cells ${cells[3]}, ${cells[4]}`);
    if (lat === null) off.push(`${ref}: no data-lat cell`);
  }
  ok(`[shipped] the pose table carries one <tr data-pose-row> per pose (${rows.size} of ${POSES.length}) with the `
    + "registry's own lat and lon", off.length === 0 && rows.size === POSES.length, off.slice(0, 4));
}
{
  const rows = attrRows('data-service');
  const off = [];
  SERVICES.forEach((sv, i) => {
    const id = must(sv, 'id', `${FABRIC_PATH}#services[${i}]`);
    if (!rows.has(id)) { off.push(`no <tr data-service="${id}">`); return; }
    const t = /<td data-transport>([^<]*)<\/td>/.exec(html.slice(html.indexOf(`<tr data-service="${id}"`)));
    if (t === null || unescape(t[1]) !== must(sv, 'transport', `${FABRIC_PATH}#services[${i}]`)) off.push(`${id}: transport cell`);
  });
  ok(`[shipped] every service row (${rows.size} of ${SERVICES.length}) carries the registry's own transport in its `
    + '<td data-transport> cell', off.length === 0 && rows.size === SERVICES.length, off.slice(0, 4));
}
{
  /* the static door markup: a link for exactly the fabric.json records that declare one, the statement for the rest */
  const links = new Map([...html.matchAll(/<a data-door="([^"]+)" href="([^"]*)">/g)].map((m) => [m[1], unescape(m[2])]));
  const undeclared = new Set([...html.matchAll(/data-door-undeclared="([^"]+)"/g)].map((m) => m[1]));
  const refused = new Set([...html.matchAll(/data-door-refused="([^"]+)"/g)].map((m) => m[1]));
  const off = [];
  const staticBearers = DOOR_BEARERS.filter(([, w]) => w.startsWith(FABRIC_PATH));
  for (const [r, w] of staticBearers) {
    if ('door' in r && r.door === null) {
      if (!refused.has(w)) off.push(`${w} refuses a door and the page does not say so`);
      if (links.has(w) || undeclared.has(w)) off.push(`${w} refuses a door and the page links or says undeclared`);
    } else if ('door' in r) {
      if (!links.has(w)) off.push(`${w} declares a door and the page shows no link for it`);
      else if (links.get(w) !== rebase(doorHrefOf(r, w))) off.push(`${w}: link ${links.get(w)} vs door ${doorHrefOf(r, w)}`);
      if (undeclared.has(w)) off.push(`${w} declares a door and the page also says none is declared`);
    } else {
      if (!undeclared.has(w)) off.push(`${w} declares no door and the page does not say so`);
      if (links.has(w)) off.push(`${w} declares no door and the page links one`);
    }
  }
  for (const w of links.keys()) if (!staticBearers.some(([, x]) => x === w)) off.push(`link data-door="${w}" is for no fabric.json record`);
  const declared = staticBearers.filter(([r]) => 'door' in r && r.door !== null).length;
  const refusedN = staticBearers.filter(([r]) => 'door' in r && r.door === null).length;
  ok(`[shipped] of the ${staticBearers.length} place, service and content records, the ${declared} that declare a door are `
    + `linked with the registry's href, the ${refusedN} that refuse one carry the registry's reason, and the `
    + `${staticBearers.length - declared - refusedN} that declare none carry "no door declared" - never an invented link`,
    off.length === 0, off.slice(0, 4));
}
{
  const rows = attrRows('data-external');
  const served = [...html.matchAll(/<tr data-external="\d+" data-served="([^"]+)">/g)].map((m) => m[1]);
  ok(`[shipped] the external origins table has one row per origin (${rows.size} of ${EXTERNAL.length}) and every row is `
    + 'marked data-served="false"', rows.size === EXTERNAL.length && served.length === EXTERNAL.length && served.every((s) => s === 'false'),
    [`rows=${rows.size} served=[${[...new Set(served)]}]`]);
}
{
  const entry = /<a id="entry" data-entry href="([^"]*)">/.exec(html);
  const want = must(FAB, 'entry', FABRIC_PATH + '#fabric');
  ok(`[shipped] the fabric's declared entry ${want} is linked re-based to the page's location, and the file exists`,
    entry !== null && entry[1] === rebase(want) && existsSync(join(ROOT, want)), [entry === null ? 'no #entry link' : entry[1]]);
}

/* --------------------------------------------------------------- generator -- */
{
  const src = readFileSync(GENERATOR, 'utf8');
  const code = src.replace(/"""[\s\S]*?"""/g, ' ').replace(/^\s*#[^\n]*$/gm, ' ')
    .replace(/\/\*[\s\S]*?\*\//g, ' ');
  ok('[generator] no default-valued lookup over registry data: no `.get(k, default)` and no bare `??` - a missing '
    + 'field fails closed through need() instead',
    !/\.get\([^)]*,[^)]*\)/.test(code) && !/\?\?/.test(code), ['a defaulted lookup survives in the generator']);
  const named = [FABRIC_PATH, GEOPOSE_PATH, SOM_PATH, MANIFEST_PATH];
  const missing = named.filter((p) => !src.includes(p));
  ok(`[generator] the generator names all ${named.length} registry paths it reads, so a scan for readers of a registry `
    + 'finds it', missing.length === 0, missing);
}

/* ---------------------------------------------------------------- browser -- */
if (!WANT_BROWSER) {
  console.log('  --  [browser] the DOM checks were not run: pass --browser to serve the bundle, drive the page in '
    + 'headless Chromium, count what was placed, fetch every relative link once and screenshot it');
} else {
  /* a static server over ROOT, so the page and every relative link it carries are served from one origin */
  const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript',
    '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml',
    '.woff2': 'font/woff2', '.woff': 'font/woff', '.glb': 'model/gltf-binary', '.webp': 'image/webp', '.ico': 'image/x-icon' };
  let server = null;
  if (arg('origin') === null && arg('url') === null) {
    server = createServer((req, res) => {
      const path = normalize(decodeURIComponent(req.url.split('?')[0].split('#')[0]));
      const file = join(ROOT, path);
      if (!file.startsWith(ROOT) || !existsSync(file) || !statSync(file).isFile()) { res.writeHead(404); res.end('not found'); return; }
      const ext = extname(file);
      res.writeHead(200, { 'content-type': ext in TYPES ? TYPES[ext] : 'application/octet-stream' });
      createReadStream(file).pipe(res);
    });
    await new Promise((res, rej) => { server.once('error', rej); server.listen(PORT, '127.0.0.1', res); })
      .catch((e) => { ok(`[browser] a server for ${ROOT} listens on 127.0.0.1:${PORT}`, false, [String(e)]); server = null; });
    if (server !== null) ok(`[browser] serving ${ROOT} on 127.0.0.1:${PORT}`, true);
  }
  let browser = null;
  try {
    const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
    browser = await chromium.launch({
      executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
      args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
    });
  } catch (e) { ok('[browser] playwright and Chromium are launchable', false, [String(e)]); }
  if (browser !== null) {
    const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
    const pageErrors = [], consoleErrors = [];
    page.on('pageerror', (e) => pageErrors.push(String(e)));
    page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
    const resp = await page.goto(PAGE_URL, { waitUntil: 'load' });
    ok(`[browser] ${PAGE_URL} answers ${resp === null ? 'nothing' : resp.status()}`, resp !== null && resp.ok());
    const dom = await page.evaluate(() => {
      const t = (id) => document.getElementById(id).textContent;
      const mapTop = document.getElementById('map').getBoundingClientRect().top + window.scrollY;
      return {
        mapPoses: [...document.querySelectorAll('#map [data-pose]')].map((e) => e.getAttribute('data-pose')),
        mapTiers: [...document.querySelectorAll('#map [data-pose]')].map((e) => e.getAttribute('data-tier')),
        insetPoses: [...document.querySelectorAll('#insets [data-inset]')].map((s) => [s.getAttribute('data-inset'),
          [...s.querySelectorAll('[data-pose]')].map((e) => e.getAttribute('data-pose'))]),
        branches: [...document.querySelectorAll('#som > li[data-branch]')].map((li) => [li.getAttribute('data-branch'),
          li.getAttribute('data-served'), li.getAttribute('data-origin'), li.querySelectorAll('[data-node]').length,
          li.querySelector('.doorline [data-door]') !== null, li.querySelector('.doorline [data-door-undeclared]') !== null,
          li.querySelector('.doorline [data-door-refused]') !== null]),
        nodes: document.querySelectorAll('#som [data-node]').length,
        nodeDoors: [...document.querySelectorAll('#som [data-node]')].map((e) => [
          e.querySelector('a[data-door]') === null ? null : e.querySelector('a[data-door]').getAttribute('data-door'),
          e.getAttribute('data-door-refused'), e.getAttribute('data-door-undeclared')]),
        nodePoses: [...document.querySelectorAll('#som [data-node-pose]')].map((e) => e.getAttribute('data-node-pose')),
        unplaced: [...document.querySelectorAll('#som [data-unplaced-why]')].map((e) => e.getAttribute('data-unplaced-why')),
        services: [...document.querySelectorAll('tr[data-service]')].map((tr) => [tr.getAttribute('data-service'),
          (tr.querySelector('[data-transport]') === null ? '' : tr.querySelector('[data-transport]').textContent)]),
        doorLinks: [...document.querySelectorAll('a[data-door]')].map((a) => [a.getAttribute('data-door'), a.getAttribute('href')]),
        hrefs: [...document.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')),
        honesty: [...document.querySelectorAll('[data-honesty]')].map((e) => [e.getAttribute('data-honesty'),
          e.offsetHeight > 0, e.getBoundingClientRect().top + window.scrollY < mapTop]),
        slots: { poses: t('placed-poses'), inset: t('placed-inset-poses'), branches: t('placed-branches'),
          nodes: t('placed-nodes'), nodePoses: t('placed-node-poses') },
      };
    });
    const placed = (got, of, what) => console.log(`placed ${got} of ${of} ${what}`);

    /* poses: circles on the continental map, one per pose in geopose.json */
    placed(dom.mapPoses.length, POSES.length, 'poses - <circle data-pose> marks in #map, of the poses in geopose.json');
    ok(`[browser] the continental map draws ${POSES.length} pose marks and they are exactly the registry's subject refs; `
      + 'the placed-poses slot shows that count; every mark carries a tier of this bundle',
      same([...dom.mapPoses].sort(), [...poseRefs].sort()) && dom.slots.poses === `${dom.mapPoses.length} of ${POSES.length}`
      && dom.mapTiers.every((t) => TIERS.has(t)),
      [`dom=${dom.mapPoses.length} registry=${POSES.length} slot=${dom.slots.poses}`]);

    /* insets: one per place, each holding the poses whose subject belongs to that campus */
    const insetTotal = dom.insetPoses.reduce((a, [, ps]) => a + ps.length, 0);
    placed(insetTotal, POSES.length, 'poses across the campus insets - <circle data-pose> marks in #insets, of the poses in geopose.json (each pose belongs to one campus)');
    {
      const off = [];
      const slugs = PLACES.map((pl, i) => must(poseByRef.get(pl.geopose).subject, 'campus', `${FABRIC_PATH}#places[${i}]`));
      if (!same(dom.insetPoses.map(([s]) => s), slugs)) off.push(`insets=[${dom.insetPoses.map(([s]) => s)}]`);
      for (const [slug, ps] of dom.insetPoses) {
        const want = POSES.filter((p) => p.subject.campus === slug).map((p) => p.subject.ref).sort();
        if (!same([...ps].sort(), want)) off.push(`${slug}: dom ${ps.length} vs registry ${want.length}`);
      }
      ok(`[browser] one inset per place (${PLACES.length}), each drawing exactly the poses whose subject belongs to that campus; `
        + 'the inset slot shows the total', off.length === 0 && dom.slots.inset === `${insetTotal} of ${POSES.length}`, off.slice(0, 4));
    }

    /* branches: list items in the tree, one per branch in som.json */
    placed(dom.branches.length, BRANCHES.length, 'branches - <li data-branch> items in #som, of the branches in som.json');
    {
      const off = [];
      BRANCHES.forEach((b, bi) => {
        const row = dom.branches.find(([id]) => id === b.id);
        if (!row) { off.push(`${b.id} not rendered`); return; }
        if (row[1] !== String(b.served_by_this_fabric) || row[2] !== b.origin) off.push(`${b.id}: served/origin ${row[1]}/${row[2]}`);
        if (row[3] !== b.children.length) off.push(`${b.id}: ${row[3]} nodes rendered of ${b.children.length}`);
        const state = !('door' in b) ? 'undeclared' : b.door === null ? 'refused' : 'declared';
        const shown = row[4] ? 'declared' : row[6] ? 'refused' : row[5] ? 'undeclared' : 'nothing';
        if (state !== shown || [row[4], row[5], row[6]].filter(Boolean).length !== 1) off.push(`${b.id}: door ${state} but rendered ${shown}`);
      });
      ok(`[browser] every branch is rendered with its registry id, origin and served flag, all of its nodes under it, and `
        + `a door link or a "no door declared" line as som.json has it (${R['doors-declared']} declared, ${R['doors-undeclared']} not); `
        + 'the branches slot shows the count', off.length === 0 && dom.branches.length === BRANCHES.length
        && dom.slots.branches === `${dom.branches.length} of ${BRANCHES.length}`, off.slice(0, 4));
    }

    /* nodes: items under those branches, one per child in som.json */
    placed(dom.nodes, CHILDREN.length, 'nodes - <li data-node> items under the branches, of the children in som.json');
    {
      const off = [];
      const wantStates = CHILDREN.map(([c, w]) => [w, !('door' in c) ? 'undeclared' : c.door === null ? 'refused' : 'declared']);
      const gotStates = dom.nodeDoors.map(([link, refused, undeclared]) => link !== null ? ['declared', link] : refused !== null ? ['refused', refused] : undeclared !== null ? ['undeclared', undeclared] : ['nothing', null]);
      if (gotStates.length !== wantStates.length) off.push(`dom nodes ${gotStates.length} vs registry ${wantStates.length}`);
      wantStates.forEach(([w, st], i) => {
        if (i >= gotStates.length) return;
        if (gotStates[i][0] !== st || gotStates[i][1] !== w) off.push(`${w}: door ${st} but rendered ${gotStates[i][0]} for ${gotStates[i][1]}`);
      });
      placed(gotStates.filter(([s]) => s === 'declared').length, wantStates.filter(([, s]) => s === 'declared').length,
        'node doors - <a data-door> links on nodes, of the nodes whose door in som.json is followable');
      placed(gotStates.filter(([s]) => s === 'refused').length, wantStates.filter(([, s]) => s === 'refused').length,
        'node door refusals - [data-door-refused] on nodes, of the nodes whose door in som.json is null with a why_no_door');
      ok('[browser] every node shows its door state as som.json has it - link, refusal with the registry\'s reason, or '
        + '"no door declared" - keyed by its own registry path, in registry order', off.length === 0, off.slice(0, 4));
    }
    placed(dom.nodePoses.length, dom.nodes, 'rendered nodes whose geopose ref resolved to a pose - [data-node-pose], of the nodes rendered');
    ok(`[browser] ${CHILDREN.length} nodes rendered; ${R['nodes-posed']} carry a resolved pose ref (every one a registry ref) and `
      + `${R['nodes-unposed']} carry the registry's own reason instead; the two node slots show those counts`,
      dom.nodes === CHILDREN.length && dom.nodePoses.length === R['nodes-posed'] && dom.nodePoses.every((r) => poseByRef.has(r))
      && dom.unplaced.length === R['nodes-unposed'] && dom.unplaced.every((w) => w.length > 0)
      && dom.slots.nodes === `${dom.nodes} of ${CHILDREN.length}` && dom.slots.nodePoses === `${dom.nodePoses.length} of ${dom.nodes}`,
      [`nodes=${dom.nodes} posed=${dom.nodePoses.length} unplaced=${dom.unplaced.length}`, JSON.stringify(dom.slots)]);

    /* services: rows with a transport cell, one per service in fabric.json */
    const withTransport = dom.services.filter(([, t]) => t.trim() !== '');
    placed(withTransport.length, SERVICES.length, 'services - <tr data-service> rows with a non-empty transport cell, of the services in fabric.json');
    ok('[browser] every service row shows the transport fabric.json declares for it',
      same(dom.services.map(([id]) => id), SERVICES.map((s) => s.id)) && dom.services.every(([id, t]) => t === SERVICES.find((s) => s.id === id).transport),
      [`rows=${dom.services.length}`]);

    /* doors: links on the page, one per declared door across every record kind */
    placed(dom.doorLinks.length, DOORS.length, 'doors - <a data-door> links, of the doors declared on any record in fabric.json and som.json');
    ok('[browser] every rendered door link is a declared door with its re-based href, and every declared door is rendered',
      same(dom.doorLinks.map(([w]) => w).sort(), DOORS.map(([w]) => w).sort())
      && dom.doorLinks.every(([w, h]) => h === rebase(DOORS.find(([x]) => x === w)[1])),
      [`dom=${dom.doorLinks.length} registry=${DOORS.length}`]);

    /* links: every distinct relative href, fetched once, expected 200 */
    const rel = [...new Set(dom.hrefs.filter((h) => !/^(https?:|data:|#|mailto:)/.test(h)))];
    const answers = [];
    for (const h of rel) {
      const target = new URL(h, PAGE_URL).href;
      try { const r = await page.request.get(target); answers.push([h, r.status()]); } catch (e) { answers.push([h, String(e)]); }
    }
    const good = answers.filter(([, s]) => s === 200);
    placed(good.length, rel.length, 'links - distinct relative hrefs on the page (entry, doors, footer) that answered 200 when fetched once from the served bundle');
    ok(`[browser] every one of the ${rel.length} distinct relative link(s) resolves to a served file (${dom.hrefs.filter((h) => /^https?:/.test(h)).length} `
      + 'external hrefs cited, not fetched)', good.length === rel.length && rel.length > 0,
      answers.filter(([, s]) => s !== 200).slice(0, 6).map(([h, s]) => `${h} -> ${s}`));

    /* the honesty block, visible and first */
    const hv = dom.honesty.filter(([, vis, above]) => vis && above);
    placed(hv.length, Object.keys(HONESTY).length, 'honesty fields - [data-honesty] items visible and laid out above the map, of the fields in fabric.json#honesty');
    ok(`[browser] every field of the honesty block is visible on the rendered page and sits above the map`,
      same(dom.honesty.map(([k]) => k), Object.keys(HONESTY)) && hv.length === Object.keys(HONESTY).length,
      [JSON.stringify(dom.honesty)]);

    await page.screenshot({ path: SHOT, fullPage: true });
    console.log(`  screenshot: ${SHOT}`);
    ok('[browser] the page raised no uncaught error and logged no console error while it rendered and its links were fetched',
      pageErrors.length === 0 && consoleErrors.length === 0, [...pageErrors.slice(0, 3), ...consoleErrors.slice(0, 3)]);
    await browser.close();
  }
  if (server !== null) server.close();
}

console.log(`\nfabric: ${n} checks, ${bad} failure${bad === 1 ? '' : 's'}`);
process.exit(bad ? 1 : 0);
