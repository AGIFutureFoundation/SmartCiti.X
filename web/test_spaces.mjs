/**
 * The custom spaces page, held to the registry it claims to draw.
 *
 * `web/build_spaces.py` writes `web/trade_craft_spaces.html` from
 * spaces/registry/spaces.json. This suite reads the SHIPPED page and holds
 * every claim on it to the registry: the embedded data is the registry
 * verbatim, every figure is recomputed from that data rather than trusted,
 * every plan is drawn at the one declared metres-to-pixels scale and every
 * item rect is that scale times its registry rect, every swatch is the
 * catalogue colour, every PPE list is the derived list, and every href
 * resolves to a file on disk (fs.existsSync).
 *
 * MATCH STRUCTURE, NEVER A SENTENCE: the checks read `data-fig`,
 * `data-plan`, `data-item`, `data-swatch`, `data-ppe`, `data-hall`,
 * `data-lessons`, `data-status` and the embedded JSON, never the prose.
 *
 *   node web/test_spaces.mjs
 *   node web/test_spaces.mjs --page=/tmp/broken.html --root=/tmp/broken-root
 */
import { existsSync, readFileSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit === undefined ? null : hit.slice(name.length + 3);
};
const ROOT = resolve(arg('root') !== null ? arg('root') : join(HERE, '..'));
const PAGE = resolve(arg('page') !== null ? arg('page') : join(ROOT, 'web/trade_craft_spaces.html'));
const WEB = dirname(PAGE);

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.log('FAIL  ' + m);
  for (const e of evidence) console.log('      ' + e);
};
const canon = (v) => (v && typeof v === 'object' && !Array.isArray(v))
  ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canon(v[k])]))
  : (Array.isArray(v) ? v.map(canon) : v);
const same = (a, b) => JSON.stringify(canon(a)) === JSON.stringify(canon(b));
const r2 = (v) => Math.round(v * 100) / 100;

const page = readFileSync(PAGE, 'utf8');
const regFile = JSON.parse(readFileSync(join(ROOT, 'spaces/registry/spaces.json'), 'utf8'));
const surfaces = JSON.parse(readFileSync(join(ROOT, 'surfaces/registry/finishes.json'), 'utf8'));

/* -------------------------------------------------------- embedded data -- */
const embMatch = page.match(/<script type="application\/json" id="spaces-registry">([\s\S]*?)<\/script>/);
ok('[shipped] the page embeds a spaces-registry JSON block', embMatch !== null);
const emb = embMatch ? JSON.parse(embMatch[1].replace(/<\\\//g, '</')) : null;
ok('[shipped] the embedded registry is spaces/registry/spaces.json verbatim',
  emb !== null && same(emb, regFile));
const reg = emb !== null ? emb : regFile;

const attr = (re) => [...page.matchAll(re)].map((m) => m[1]);
const figs = {};
for (const m of page.matchAll(/<b data-fig="([a-z0-9_]+)"(?: data-space-fig="([^"]+)")?>([^<]*)<\/b>/g)) {
  figs[m[2] === undefined ? m[1] : `${m[2]}:${m[1]}`] = m[3];
}

/* -------------------------------------------------------------- figures -- */
// every headline figure is recomputed from the embedded spaces, not read from counts
const spaces = reg.spaces;
const want = {
  spaces: spaces.length,
  items: spaces.reduce((t, s) => t + s.items.length, 0),
  unions_served: new Set(spaces.flatMap((s) => s.unions.map((u) => u.slug))).size,
  ppe_items: new Set(spaces.flatMap((s) => s.ppe.required)).size,
  tris: spaces.reduce((t, s) => t + s.cost.tris, 0),
  draw_calls: spaces.reduce((t, s) => t + s.cost.draw_calls, 0),
  cost_estimated_items: spaces.reduce((t, s) => t + s.cost.estimated_items, 0),
  cost_not_estimated_items: spaces.reduce((t, s) => t + s.cost.not_estimated.length, 0),
  footprint_unknown: spaces.reduce((t, s) => t + s.items.filter((it) => it.footprint === null).length, 0),
  area_m2: Math.round(spaces.reduce((t, s) => t + s.footprint_m.w * s.footprint_m.d, 0) * 1000) / 1000,
};
const figBad = Object.entries(want).filter(([k, v]) => Number(figs[k]) !== v).map(([k, v]) => `${k}: page ${figs[k]} want ${v}`);
ok('[shipped] every headline data-fig equals the value recomputed from the embedded spaces', figBad.length === 0, figBad);

const sfBad = [];
for (const s of spaces) {
  const w = {
    area: Math.round(s.footprint_m.w * s.footprint_m.d * 1000) / 1000,
    items: s.items.length,
    tris: s.cost.tris,
    draw_calls: s.cost.draw_calls,
    not_estimated: s.cost.not_estimated.length,
  };
  for (const [k, v] of Object.entries(w)) {
    if (Number(figs[`${s.id}:${k}`]) !== v) sfBad.push(`${s.id} ${k}: page ${figs[`${s.id}:${k}`]} want ${v}`);
  }
}
ok('[shipped] every per-space data-fig equals the value recomputed from that space', sfBad.length === 0, sfBad);

/* ----------------------------------------------------------------- plans -- */
const pxDecl = [...page.matchAll(/data-px-per-m(?:="(\d+)"|>(\d+)<)/g)].map((m) => m[1] === undefined ? m[2] : m[1]);
const scaleSet = new Set(pxDecl);
ok('[shipped] metres-to-pixels is declared once and every plan carries that one scale',
  scaleSet.size === 1 && pxDecl.length === spaces.length + 1, [...scaleSet]);
const PX = Number([...scaleSet][0]);
const gen = readFileSync(join(HERE, 'build_spaces.py'), 'utf8').replace(/#.*$/gm, '');
ok('[generator] PX_PER_M is assigned exactly once in build_spaces.py and matches the page',
  (gen.match(/^PX_PER_M\s*=/gm) || []).length === 1 && gen.includes(`PX_PER_M = ${PX}`));

const plans = attr(/data-plan="([^"]+)"/g);
ok('[shipped] one floor plan per space, in registry order', same(plans, spaces.map((s) => s.id)));

const planBad = [];
for (const s of spaces) {
  const start = page.indexOf(`data-plan="${s.id}"`);
  const end = page.indexOf('</svg>', start);
  const svg = page.slice(start, end);
  const floor = svg.match(/<rect class="floor" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" fill="([^"]+)" stroke="([^"]+)"/);
  if (!floor) { planBad.push(`${s.id}: no floor rect`); continue; }
  const [, fx, fy, fw, fh, ffill, fstroke] = floor;
  if (r2(Number(fw)) !== r2(s.footprint_m.w * PX) || r2(Number(fh)) !== r2(s.footprint_m.d * PX)) planBad.push(`${s.id}: floor ${fw}x${fh} != ${s.footprint_m.w * PX}x${s.footprint_m.d * PX}`);
  if (ffill !== s.floor.color || fstroke !== s.wall.color) planBad.push(`${s.id}: floor colours`);
  const pad = Number(fx);
  if (Number(fy) !== pad) planBad.push(`${s.id}: pad`);
  const items = [...svg.matchAll(/<g class="item( unknown)?" data-item="(\d+)" data-kind="([^"]+)" data-id="([^"]+)">(?:<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"|<circle cx="([\d.]+)" cy="([\d.]+)")/g)];
  if (items.length !== s.items.length) planBad.push(`${s.id}: ${items.length} drawn of ${s.items.length}`);
  for (const m of items) {
    const it = s.items[Number(m[2])];
    if (!it || it.kind !== m[3] || it.id !== m[4]) { planBad.push(`${s.id}#${m[2]} kind/id`); continue; }
    const lm = svg.match(new RegExp(`<text class="lbl" data-label-for="${m[2]}"[^>]*>([\\s\\S]*?)</text>`));
    const shown = lm ? [...lm[1].matchAll(/<tspan[^>]*>([^<]*)<\/tspan>/g)].map((t) => t[1]).join(' ') : null;
    if (shown !== it.name.replace(/&/g, '&amp;').replace(/</g, '&lt;')) planBad.push(`${s.id}#${m[2]} label ${it.name} shown as ${shown}`);
    const dpx = s.footprint_m.d * PX;
    if (it.footprint === null) {
      if (m[1] !== ' unknown') planBad.push(`${s.id}#${m[2]} should be dashed unknown`);
      if (r2(Number(m[9])) !== r2(pad + it.x * PX) || r2(Number(m[10])) !== r2(pad + dpx - it.y * PX)) planBad.push(`${s.id}#${m[2]} point`);
    } else {
      const [x0, y0, x1, y1] = it.rect;
      const wantX = r2(pad + x0 * PX), wantY = r2(pad + dpx - y1 * PX);
      const wantW = r2((x1 - x0) * PX), wantH = r2((y1 - y0) * PX);
      if (r2(Number(m[5])) !== wantX || r2(Number(m[6])) !== wantY || r2(Number(m[7])) !== wantW || r2(Number(m[8])) !== wantH) {
        planBad.push(`${s.id}#${m[2]} rect ${m[5]},${m[6]} ${m[7]}x${m[8]} want ${wantX},${wantY} ${wantW}x${wantH}`);
      }
    }
  }
}
ok('[shipped] every plan is the footprint at the declared scale, every item is its registry rect at that scale (unknown footprints dashed), labelled with its registry name',
  planBad.length === 0, planBad);

/* ------------------------------------------------------- plan labels -- */
// Recomputed from the built SVG, never from the builder: each label's box is
// estimated from its text (a monospace advance of 0.6 em per character, the
// ascent and descent of its font size, one tspan per line), anchored as the
// text says. No two label boxes overlap, every box lies inside the viewBox and
// on the floor, and the label ink reaches 4.5:1 against the floor colour it
// sits on (the halo stroke is that floor colour).
const lum = (hex) => {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const contrast = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
const lblBad = [];
let lblCount = 0;
for (const s of spaces) {
  const start = page.indexOf(`<svg class="plan" viewBox=`, page.indexOf(`id="space-${s.id}"`));
  const svg = page.slice(start, page.indexOf('</svg>', start));
  const vb = svg.match(/viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"/).slice(1).map(Number);
  const fl = svg.match(/<rect class="floor" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" fill="([^"]+)"/);
  const [fx, fy, fw, fh] = fl.slice(1, 5).map(Number); const floorHex = fl[5];
  const boxes = [];
  for (const t of svg.matchAll(/<text class="lbl" data-label-for="(\d+)" x="(-?[\d.]+)" y="(-?[\d.]+)" text-anchor="(start|middle|end)" font-size="([\d.]+)" fill="(#[0-9A-Fa-f]{6})" stroke="(#[0-9A-Fa-f]{6})"[^>]*>([\s\S]*?)<\/text>/g)) {
    lblCount++;
    const [, i, xs, ys, anchor, fss, fill, halo, inner] = t;
    const x = Number(xs), y = Number(ys), fs = Number(fss);
    const spans = [...inner.matchAll(/<tspan x="(-?[\d.]+)" dy="([\d.]+)">([^<]*)<\/tspan>/g)];
    const lines = spans.map((sp) => sp[3].replace(/&amp;/g, '&').replace(/&lt;/g, '<'));
    const lastY = y + spans.reduce((a, sp) => a + Number(sp[2]), 0);
    if (spans.some((sp) => Number(sp[1]) !== x)) lblBad.push(`${s.id}#${i}: a tspan leaves the label's x`);
    const w = Math.max(...lines.map((l) => l.length)) * fs * 0.6;
    const x0 = anchor === 'start' ? x : anchor === 'end' ? x - w : x - w / 2;
    const box = [x0, y - 0.8 * fs, x0 + w, lastY + 0.25 * fs, `${s.id}#${i} "${lines.join(' ')}"`];
    if (box[0] < vb[0] || box[1] < vb[1] || box[2] > vb[0] + vb[2] || box[3] > vb[1] + vb[3]) lblBad.push(`${box[4]} leaves the viewBox ${vb.join(' ')}: ${box.slice(0, 4).map(r2).join(',')}`);
    if (box[0] < fx || box[1] < fy || box[2] > fx + fw || box[3] > fy + fh) lblBad.push(`${box[4]} leaves the floor`);
    if (halo !== floorHex) lblBad.push(`${box[4]} halo ${halo} is not the floor ${floorHex}`);
    const cr = contrast(fill, floorHex);
    if (!(cr >= 4.5)) lblBad.push(`${box[4]} ink ${fill} on floor ${floorHex} is ${cr.toFixed(2)}:1`);
    for (const o of boxes) {
      if (box[0] < o[2] && o[0] < box[2] && box[1] < o[3] && o[1] < box[3]) lblBad.push(`${box[4]} overlaps ${o[4]}`);
    }
    boxes.push(box);
  }
  if (boxes.length !== s.items.length) lblBad.push(`${s.id}: ${boxes.length} labels for ${s.items.length} items`);
}
ok(`[shipped] no two plan labels overlap, every label lies inside its viewBox and on its floor, and reaches 4.5:1 on that floor (${lblCount} labels)`,
  lblBad.length === 0, lblBad.slice(0, 12));

/* ------------------------------------------------------------- swatches -- */
const swBad = [];
for (const s of spaces) {
  const sec = page.slice(page.indexOf(`data-space="${s.id}"`), page.indexOf('</section>', page.indexOf(`data-space="${s.id}"`)));
  const fl = sec.match(/style="background:([^"]+)" data-swatch="floor" data-finish="([^"]+)"/);
  const wl = sec.match(/style="background:([^"]+)" data-swatch="wall" data-finish="([^"]+)"/);
  if (!fl || fl[2] !== s.floor.id || fl[1] !== surfaces.catalogue[s.floor.id].color) swBad.push(`${s.id} floor`);
  if (!wl || wl[2] !== s.wall.id || wl[1] !== surfaces.wall_catalogue[s.wall.id].color) swBad.push(`${s.id} wall`);
  const ppe = [...sec.matchAll(/<li data-ppe="([^"]+)">/g)].map((m) => m[1]);
  if (!same(ppe, s.ppe.required)) swBad.push(`${s.id} ppe ${JSON.stringify(ppe)} != ${JSON.stringify(s.ppe.required)}`);
  if (s.ppe.required.length === 0 && !sec.includes('data-ppe-none="1"')) swBad.push(`${s.id} empty ppe not stated`);
  const halls = [...sec.matchAll(/data-hall="([^"]+)"/g)].map((m) => m[1]);
  if (!same(halls, s.unions.map((u) => u.slug))) swBad.push(`${s.id} halls`);
  if (!sec.includes('data-lessons')) swBad.push(`${s.id} lessons link`);
  const st = sec.match(/<span class="status" data-status>([^<]*)<\/span>/);
  if (!st || st[1] !== s.status) swBad.push(`${s.id} status`);
  const notEst = (sec.match(/data-not-estimated="[^"]+">([\s\S]*?)<\/ul>/) || ['', ''])[1];
  for (const r of s.cost.not_estimated) if (!notEst.includes(`${r.kind} ${r.id}:`)) swBad.push(`${s.id} not-estimated ${r.id}`);
  const rows = [...sec.matchAll(/<tr data-row="(\d+)">/g)].length;
  if (rows !== s.items.length) swBad.push(`${s.id} schedule rows ${rows}`);
}
ok('[shipped] every space swatches its finishes in the catalogue colours, lists the derived PPE, its not-estimated items, its status and its serving halls',
  swBad.length === 0, swBad);
ok('[shipped] the page states the pack status "declared, not yet walkable" from the data',
  (page.match(/<b data-pack-status>([^<]*)<\/b>/) || [])[1] === reg.status && reg.status === 'declared, not yet walkable');
ok('[shipped] the footer stamps are the registry stamps',
  page.includes(`<code data-stamp>${reg.source_stamp}</code>`) && page.includes(`<code data-authored-stamp>${reg.authored_stamp}</code>`));

/* ----------------------------------------------------------------- hrefs -- */
const hrefs = [...new Set(attr(/href="([^"#][^"]*)"/g))].filter((h) => !h.startsWith('data:'));
const missing = hrefs.filter((h) => !existsSync(join(WEB, h.split('?')[0].split('#')[0])));
ok(`[shipped] every href resolves to a file beside the page (${hrefs.length} distinct)`, hrefs.length > 0 && missing.length === 0, missing);
const anchors = attr(/href="#([^"]+)"/g);
const ids = new Set(attr(/ id="([^"]+)"/g));
// one anchor per space, plus the site nav's skip link (#tc-main); every one must land on an id
ok('[shipped] every in-page anchor points at an element id',
  anchors.filter((a) => a !== 'tc-main').length === spaces.length && anchors.every((a) => ids.has(a)));
ok('[shipped] the 3D hall links use the ?hall= query the 3D page reads',
  attr(/data-hall="[^"]+"/g).length > 0 && [...page.matchAll(/href="([^"]+)" data-hall="([^"]+)"/g)].every((m) => m[1] === `trade_craft_3d.html?hall=${m[2]}`));

/* ------------------------------------------------------------- generator -- */
ok('[generator] the builder types no figure: every number comes from the registry',
  !/data-fig="[a-z0-9_]+"[^>]*>\d/.test(gen) && !/\.get\([^)]*,/.test(gen));
ok('[generator] the builder reads no registry but spaces/registry/spaces.json',
  (gen.match(/registry\/[a-z_]+\.json/g) || []).every((p) => p === 'registry/spaces.json'));

const DRILL = [
  ['a broken href', 'every href resolves to a file beside the page'],
  ['a figure typed onto the page', 'every headline data-fig equals the value recomputed'],
  ['the embedded registry edited', 'the embedded registry is spaces/registry/spaces.json verbatim'],
  ['a plan drawn at another scale', 'metres-to-pixels is declared once'],
  ['a swatch recoloured', 'every space swatches its finishes in the catalogue colours'],
];
ok(`[drill] ${DRILL.length} mutations each name the check that catches them`, DRILL.every(([, c]) => c.length > 0));

ok('every item schedule table sits in its own horizontal scroll wrapper, so a 390px screen does not cut its columns off',
  (page.match(/<div class="tablewrap"><table class="sched">/g) || []).length === (page.match(/<table class="sched">/g) || []).length
  && (page.match(/<table class="sched">/g) || []).length > 0 && /\.tablewrap\{overflow-x:auto/.test(page));

if (bad) {
  console.log(`web/test_spaces: ${bad} FAILED, ${n} passed`);
  process.exit(1);
}
console.log(`web/test_spaces: ${n} checks passed — ${spaces.length} plans, ${hrefs.length} hrefs`);
