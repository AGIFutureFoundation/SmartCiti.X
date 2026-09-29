/* cognitionx/test.mjs - the Cognition.X K-12 pack, checked. Browser-free, network-free.
 *
 * Recompute, never re-read: the pin, the verbatim text of every block used, the attribution, the band of
 * every block, the place mapping (re-derived here from the SmartCiti registries with an independent
 * implementation of the stated rule), the Louisiana links and every count. When the local Cognition.X
 * checkout is present its HEAD and file hashes are checked against the pin and every vendored row is
 * found verbatim in the upstream blocks.csv; without it the vendored pins stand in (said so, by name).
 */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
const UP = process.env.COGX_UPSTREAM || '/home/user/cognition.x';
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const buf = (p) => readFileSync(join(ROOT, p));
const J = (p) => JSON.parse(buf(p).toString('utf8'));
const sha = (b) => createHash('sha256').update(b).digest('hex');
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function parseCSV(text) {        // RFC 4180: quotes, doubled quotes, embedded commas/newlines
  const rows = []; let row = [], f = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; }
      else f += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(f); f = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(f); rows.push(row); row = []; f = '';
    } else f += c;
  }
  if (f !== '' || row.length) { row.push(f); rows.push(row); }
  const [h, ...body] = rows;
  return { header: h, rows: body.map((r) => Object.fromEntries(h.map((k, i) => [k, r[i]]))) };
}

console.log('cognitionx/test.mjs');
const R = J('cognitionx/registry/cognitionx.json');
const SRC = buf('cognitionx/build.py').toString('utf8');
const COLS = ['block_id', 'pack', 'track', 'code', 'grade', 'level', 'credential', 'theme', 'description', 'transfer_check'];

/* ---- provenance and the pin ------------------------------------------ */
ok(R.pack === 'cognitionx', 'the registry names its own pack');
ok(sha(SRC).slice(0, 16) === R.source_stamp, 'the registry was built from the current builder (stamp check)');
const srcOk = Object.entries(R.sources).every(([p, s]) => existsSync(join(ROOT, p)) && sha(buf(p)).slice(0, 16) === s);
ok(srcOk && Object.keys(R.sources).length === 7, 'every SmartCiti registry the build read is unchanged since (sources stamps)');
const pinCommit = (SRC.match(/PIN_COMMIT = '([0-9a-f]{40})'/) || [])[1];
ok(pinCommit && R.upstream.commit === pinCommit && R.attribution.commit === pinCommit,
   'the pinned upstream commit is the one the builder pins (registry, attribution)');
const pinBlock = (name) => Object.fromEntries([...SRC.split(name + ' = {')[1].split('}')[0]
  .matchAll(/'([^']+)': '([0-9a-f]{64})'/g)].map((m) => [m[1], m[2]]));
const PF = pinBlock('PIN_FILES'), PV = pinBlock('PIN_VENDOR');
ok(Object.keys(PF).length === 4 && eq(PF, R.upstream.files_sha256), 'the registry records the sha256 of every upstream file read (4, as pinned)');
ok(Object.keys(PV).length === 4 && eq(PV, R.upstream.vendored_sha256), 'the registry records the sha256 of every vendored file (4, as pinned)');
ok(Object.entries(PV).every(([p, h]) => sha(buf('cognitionx/' + p)) === h), 'every vendored file matches its pinned sha256');
ok(PV['vendor/LICENSE-CONTENT'] === PF['LICENSE-CONTENT'], 'the vendored LICENSE-CONTENT is byte-identical to the upstream one');
const HAVE_UP = existsSync(join(UP, '.git'));
if (HAVE_UP) {
  const head = execFileSync('git', ['-C', UP, 'rev-parse', 'HEAD']).toString().trim();
  ok(head === pinCommit, `the local Cognition.X checkout is at the pinned commit (${head.slice(0, 7)})`);
  ok(Object.entries(PF).every(([p, h]) => sha(readFileSync(join(UP, p))) === h), 'every upstream file read still matches its pinned sha256');
} else {
  ok(true, `no Cognition.X checkout at ${UP}: the vendored pins stand in for the upstream ones`);
}

/* ---- attribution + licence ------------------------------------------- */
const A = R.attribution;
ok(A.text === 'Cognition.X by AGI Future Foundation' && A.license === 'CC-BY-4.0'
   && A.license_url === 'https://creativecommons.org/licenses/by/4.0/'
   && A.repo === 'https://github.com/AGIFutureFoundation/cognition.x', 'attribution: CC-BY-4.0, "Cognition.X by AGI Future Foundation", repo link');
const LIC = buf('cognitionx/vendor/LICENSE-CONTENT').toString('utf8');
ok(A.license_file === 'cognitionx/vendor/LICENSE-CONTENT' && LIC.startsWith('Creative Commons Attribution 4.0 International'),
   'the CC BY 4.0 licence text travels with the vendored content');
const NOTICE = existsSync(join(HERE, 'vendor/NOTICE')) ? readFileSync(join(HERE, 'vendor/NOTICE'), 'utf8') : '';
ok(NOTICE.startsWith(A.text + ' - ' + A.repo) && NOTICE.includes(pinCommit) && NOTICE.includes('CC BY 4.0'),
   'vendor/NOTICE carries the attribution, repo link, pinned commit and licence');
ok(/verbatim/.test(A.changes) && /derived/.test(A.changes), 'attribution states the changes (selection verbatim, band derived)');
const H = R.honesty;
ok(/not accredited/.test(H.blocks) && /not verified/.test(H.blocks) && /transfer checks/.test(H.blocks), 'honesty: blocks are statements with transfer checks, not accredited, not verified');
ok(/keyword overlap, not a pedagogical alignment/.test(H.mapping) && /unmapped/.test(H.mapping), 'honesty: mapping is keyword overlap, not alignment; unmapped counted');
ok(/PROPOSED/.test(H.districts) && /No student data leaves the browser/.test(H.privacy), 'honesty: districts PROPOSED; no student data leaves the browser');

/* ---- verbatim round trip --------------------------------------------- */
const V = parseCSV(buf('cognitionx/vendor/blocks_subset.csv').toString('utf8'));
ok(eq(V.header, COLS), 'the vendored CSV keeps the upstream header');
const vById = new Map(V.rows.map((r) => [r.block_id, r]));
const B = R.blocks;
ok(B.every((b) => vById.has(b.block_id) && COLS.every((k) => b[k] === vById.get(b.block_id)[k])),
   `every block used (${B.length}) round-trips all 10 columns verbatim against the vendored rows`);
if (HAVE_UP) {
  const U = parseCSV(readFileSync(join(UP, 'data/blocks.csv'), 'utf8'));
  const uById = new Map(U.rows.map((r) => [r.block_id, r]));
  ok(V.rows.every((r) => uById.has(r.block_id) && COLS.every((k) => r[k] === uById.get(r.block_id)[k])),
     `every vendored row (${V.rows.length}) is verbatim in the upstream blocks.csv`);
  const packs = new Set(V.rows.map((r) => r.pack));
  ok(U.rows.filter((r) => packs.has(r.pack)).length === V.rows.length, 'the vendor subset holds every upstream row of the selected packs (none dropped)');
} else {
  ok(true, 'upstream round trip skipped with the checkout absent (the vendored sha256 pins stand in)');
}
const SINGLE = { K: 'K–2', 1: 'K–2', 2: 'K–2', 3: '3–5', 4: '3–5', 5: '3–5', 6: '6–8', 7: '6–8', 8: '6–8', 9: '9–10', 10: '9–10', 11: '11–12', 12: '11–12' };
const bandOf = (g) => (R.bands.includes(g) ? g : SINGLE[g] || null);
const kept = V.rows.filter((r) => bandOf(r.grade));
ok(kept.length === B.length && R.counts.excluded_unbanded === V.rows.length - kept.length, 'every K-12 vendored row is in the registry; unbanded rows are counted as excluded');
ok(eq(R.bands, ['K–2', '3–5', '6–8', '9–10', '11–12']) && B.every((b) => b.band === bandOf(b.grade)),
   'every block band is the data/schema.md level mapping of its grade');
// schools/build.py claims its bands are "aligned with the Cognition.X band vocabulary": prove it from the blocks' own level column
const SCB = J('schools/registry/schools.json').bands;
const schoolsBand = (bd) => (bd === 'K–2' || bd === '3–5' ? 'K-5' : bd.replace('–', '-'));
ok(SCB.length === 4 && B.every((b) => { const s = SCB.find((x) => x.band === schoolsBand(b.band)); return s && s.level === b.level; }),
   'every block\'s upstream level equals the schools/ band level (the schools pack\'s Cognition.X vocabulary claim holds)');
ok(B.every((b) => b.statement_field === (b.description ? 'description' : 'theme') && b[b.statement_field]),
   'every block names a non-empty statement field (description, else theme)');
ok(B.every((b) => typeof b.transfer_check === 'string' && b.transfer_check.length > 0), 'every block carries its transfer check');
const MS = J('cognitionx/vendor/manifest_subset.json');
const slugOf = Object.fromEntries(MS.packs.map((p) => [p.name, p.slug]));
const SEL = R.selection.packs.map((p) => p.slug);
ok(eq([...new Set(B.map((b) => b.pack_slug))].sort(), [...SEL].sort()) && B.every((b) => slugOf[b.pack] === b.pack_slug),
   `the blocks come from exactly the ${SEL.length} selected packs, slugs from the upstream manifest`);
ok(MS.packs.every((p) => V.rows.filter((r) => r.pack === p.name).length === p.blocks), 'the vendored rows per pack equal the upstream manifest block counts');

/* ---- the mapping rule, re-implemented -------------------------------- */
const MR = R.mapping_rule;
const STOP = new Set(MR.stop);
const buildStop = [...SRC.split('STOP = sorted({')[1].split('})')[0].matchAll(/'([a-z]+)'/g)].map((m) => m[1]);
ok(eq([...new Set(buildStop)].sort(), MR.stop) && MR.min_shared === 2, 'the published stop list and threshold are the builder\'s');
function toks(t) {
  const out = new Set();
  for (let w of t.toLowerCase().match(/[a-z]+/g) || []) {
    if (w.length < 4 || STOP.has(w)) continue;
    if (w.endsWith('ies')) w = w.slice(0, -3) + 'y';
    else if (w.endsWith('s') && !w.endsWith('ss')) w = w.slice(0, -1);
    if (w.length < 4 || STOP.has(w)) continue;
    out.add(w);
  }
  return out;
}
const blockText = (b) => b.theme + ' ' + b.description.replace(/\s+— at [^—]*$/, '');
// candidate places, derived here from the SmartCiti registries
const cand = new Map();
const add = (id, world, title) => { if (cand.has(id)) throw new Error('dup ' + id); cand.set(id, { world, title }); };
const LY = J('layers/registry/layers.json'), PA = J('layers/registry/paths.json'), WI = J('wilds/registry/wilds.json');
const SI = J('sims/registry/sims.json'), LE = J('lessons/registry/lessons.json'), SC = J('schools/registry/schools.json');
for (const p of LY.parishes) for (const st of p.stations) add(`parish:${p.fips}/${st.id}`, 'parishes', st.title);
for (const p of PA.parishes) for (const path of p.paths) path.steps.forEach((s, i) => {
  if (path.id === 'k12') add(`k12:${p.fips}/${i + 1}`, 'parishes', s.title);
  else if (s.kind === 'quote') add(`path:${p.fips}/${s.id}`, 'parishes', s.title);
});
for (const w of WI.worlds) for (const s of w.sites) add(`wilds:${w.id}/${s.id}`, 'wilds', s.title);
const hallName = {};
for (const lid of Object.keys(LE.lessons).sort()) hallName[LE.lessons[lid].hall] = LE.lessons[lid].hall_name;
for (const h of Object.keys(hallName).sort()) add(`campus:${h}`, 'campus', hallName[h]);
for (const [h, bs] of Object.entries(SI.hall_bindings)) if (hallName[h])
  for (const sim of [...new Set(bs.map((b) => b.sim))]) add(`campus:${h}/${sim}`, 'campus', `${hallName[h]}: ${SI.sims[sim].name}`);
const unitHalls = new Set(SC.units.map((u) => u.hall));
for (const h of unitHalls) add(`module:mod-${h}`, 'classroom', hallName[h]);
ok(cand.size === R.counts.places_total, `the candidate place set re-derives to ${cand.size} places from 6 SmartCiti registries`);
ok(R.places.every((p) => cand.has(p.id) && cand.get(p.id).title === p.title && cand.get(p.id).world === p.world),
   'every published place resolves to a real registry id with the same title and world');
const ctok = [...cand].map(([id, p]) => [id, toks(p.title)]);
let mapMismatch = [];
for (const b of B) {
  const bt = toks(blockText(b)), tt = toks(b.theme);
  const hits = ctok.filter(([, t]) => [...t].filter((x) => bt.has(x)).length >= 2 && [...t].some((x) => tt.has(x))).map(([id]) => id).sort();
  if (!eq(hits, b.places)) mapMismatch.push(b.block_id);
}
ok(mapMismatch.length === 0, `the mapping rule reproduces every block's places independently (${mapMismatch.slice(0, 3).join(', ') || 'no mismatch'})`);
const used = [...new Set(B.flatMap((b) => b.places))].sort();
ok(eq(used, R.places.map((p) => p.id)), 'the published places are exactly the places some block maps to, sorted');
ok(B.every((b) => eq(b.classroom_modules, [...new Set(b.places.filter((p) => /^(campus|module):/.test(p))
  .map((p) => p.replace(/^module:mod-/, 'campus:').split(':')[1].split('/')[0]))].filter((h) => unitHalls.has(h)).map((h) => `mod-${h}`).sort())),
   'every block\'s classroom modules re-derive from its campus/module places and the schools units');
const CL = existsSync(join(ROOT, 'classroom/registry/classroom.json')) ? J('classroom/registry/classroom.json') : null;
if (CL) {
  const clIds = new Set(CL.places.map((p) => p.id)), clMods = new Set(CL.modules.map((m) => m.id));
  const theirs = CL.places.filter((p) => /^(parish|k12|wilds|campus):/.test(p.id));
  const both = R.places.filter((p) => clIds.has(p.id)).length;
  ok(theirs.length > 0 && theirs.every((p) => cand.has(p.id) && cand.get(p.id).world === p.world)
     && B.every((b) => b.classroom_modules.every((m) => clMods.has(m))),
     `place ids share the classroom grammar: all ${theirs.length} classroom.json parish/k12/wilds/campus ids are COGX candidates (${both} published places in both); every classroom module id resolves`);
} else ok(false, 'classroom/registry/classroom.json is missing (the place-id grammar cross-check needs it)');

/* ---- Cognition.X modules --------------------------------------------- */
const M = R.modules;
const inMods = M.flatMap((m) => m.blocks);
ok(new Set(M.map((m) => m.id)).size === M.length && inMods.length === B.length && new Set(inMods).size === B.length,
   `every block sits in exactly one of ${M.length} Cognition.X modules (unique ids)`);
const bById = new Map(B.map((b) => [b.block_id, b]));
ok(M.every((m) => m.blocks.every((id) => { const b = bById.get(id); return b.module === m.id && b.pack_slug === m.pack_slug
  && (m.group === 'track' ? b.track === m.name : b.band === m.name); })),
   'modules group the upstream structure: track name verbatim (or the K12 band), one pack each');
ok(M.every((m) => m.mapped_blocks === m.blocks.filter((id) => bById.get(id).places.length).length
  && eq(m.bands, R.bands.filter((bd) => m.blocks.some((id) => bById.get(id).band === bd)))), 'module mapped counts and bands recompute');

/* ---- Louisiana dashboards -------------------------------------------- */
const LA = J('cognitionx/vendor/louisiana_parishes.json').parishes;
const PR = J('parishes/registry/parishes.json').parishes;
const slug = (n) => n.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
const L = R.louisiana.links;
ok(L.length === Object.keys(PR).length && eq(L.map((l) => l.fips), Object.keys(PR).sort()), `every SmartCiti parish (${L.length}) has one Louisiana dashboard link`);
ok(L.every((l) => { const la = LA.find((x) => x.name === PR[l.fips].name); const d = l.dashboard;
  return la && d.name === PR[l.fips].name && l.smartciti_name === PR[l.fips].full_name && d.slug === slug(d.name)
    && d.route === '#/parish/' + d.slug && d.seat === la.seat && d.region === la.region && d.world === la.world
    && d.districts === la.districts && d.url === `${A.repo}/blob/${pinCommit}/apps/louisiana/index.html`; }),
   'each link: same Census name, the app\'s own slug/route rule, fields verbatim from the app data');
ok(LA.length === 64 && R.counts.louisiana_dashboards === 64 && R.counts.louisiana_linked === L.length, 'the app has 64 parish dashboards; the linked count recomputes');

/* ---- counts ---------------------------------------------------------- */
const C = R.counts;
const cnt = (f) => B.filter(f).length;
ok(C.blocks === B.length && eq(C.by_band, Object.fromEntries(R.bands.map((bd) => [bd, cnt((b) => b.band === bd)])))
   && eq(C.by_pack, Object.fromEntries([...new Set(B.map((b) => b.pack_slug))].sort().map((s) => [s, cnt((b) => b.pack_slug === s)]))),
   `counts by band and by pack recompute (${B.length} blocks)`);
const mapped = cnt((b) => b.places.length);
ok(C.mapped === mapped && C.unmapped === B.length - mapped && C.links === B.reduce((n, b) => n + b.places.length, 0)
   && eq(C.mapped_by_pack, Object.fromEntries(SEL.map((s) => [s, cnt((b) => b.pack_slug === s && b.places.length)])))
   && eq(C.mapped_by_band, Object.fromEntries(R.bands.map((bd) => [bd, cnt((b) => b.band === bd && b.places.length)]))),
   `mapped ${mapped} / unmapped ${B.length - mapped} recompute, by pack and band`);
ok(C.places_used === used.length && C.modules === M.length
   && eq(C.places_used_by_world, Object.fromEntries([...new Set([...cand.values()].map((p) => p.world))].sort()
     .map((w) => [w, used.filter((id) => cand.get(id).world === w).length]))), 'place and module counts recompute');

/* ---- fail closed ----------------------------------------------------- */
ok(!/\.get\([^)]*,/.test(SRC) && !SRC.includes('??'), 'the builder uses no defaulted lookups (fail closed)');
ok(/raise CogxError\(f'cognitionx: Cognition.X checkout is at/.test(SRC) && /differs from pinned/.test(SRC),
   'the builder refuses a checkout or file that differs from the pin');

console.log(`\n${pass} ok, ${fail} FAIL`);
process.exit(fail ? 1 : 0);
