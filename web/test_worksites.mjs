/**
 * The work sites page, held to the registry it claims to draw.
 *
 * `web/build_worksites.py` writes `web/trade_craft_worksites.html` from
 * worksites/registry/worksites.json. This suite reads the SHIPPED page and
 * holds every claim on it to the registry: the embedded data is the registry
 * verbatim, every figure is recomputed from that data rather than trusted,
 * every site draws one post per role and one numbered arrow per hand-off
 * from the post handing off to the post receiving, the PPE lists are the
 * derived lists, the stop-work line is the crew's, the honesty lines are the
 * registry's, and every href resolves to a file on disk.
 *
 * MATCH STRUCTURE, NEVER A SENTENCE: the checks read data-* attributes and
 * the embedded JSON, never the prose.
 *
 *   node web/test_worksites.mjs
 *   node web/test_worksites.mjs --page=/tmp/broken.html --root=/tmp/broken-root
 */
import { existsSync, readFileSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name) => { const hit = args.find((a) => a.startsWith(`--${name}=`)); return hit === undefined ? null : hit.slice(name.length + 3); };
const ROOT = resolve(arg('root') !== null ? arg('root') : join(HERE, '..'));
const PAGE = resolve(arg('page') !== null ? arg('page') : join(ROOT, 'web/trade_craft_worksites.html'));
const WEB = dirname(PAGE);

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++; console.log('FAIL  ' + m);
  for (const e of evidence) console.log('      ' + e);
};
const unesc = (s) => s.replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');

const html = readFileSync(PAGE, 'utf8');
const reg = JSON.parse(readFileSync(join(ROOT, 'worksites/registry/worksites.json'), 'utf8'));

// verbatim embed
const m = html.match(/<script type="application\/json" id="worksites-registry">([\s\S]*?)<\/script>/);
const embedded = m ? JSON.parse(m[1].replace(/<\\\//g, '</')) : null;
const canon = (v) => Array.isArray(v) ? '[' + v.map(canon).join(',') + ']' : (v !== null && typeof v === 'object') ? '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}' : JSON.stringify(v);
ok('the registry is embedded verbatim (parsed, deep-equal to worksites/registry/worksites.json under sorted keys)', embedded !== null && canon(embedded) === canon(reg));
const D = embedded === null ? reg : embedded;
ok('the stamps on the page are the registry\'s', html.includes(`data-stamp>${D.source_stamp}<`) && html.includes(`data-authored-stamp>${D.authored_stamp}<`));

// figures: recomputed from the embedded sites, never read from counts
const fig = (k) => { const x = html.match(new RegExp(`data-fig="${k}">([^<]*)<`)); return x ? Number(x[1]) : null; };
const sites = D.sites;
const want = {
  sites: sites.length,
  unions_covered: new Set(sites.flatMap((s) => s.derived.unions)).size,
  unions_total: 111,
  crews_used: new Set(sites.map((s) => s.crew.id)).size,
  crews_total: Object.keys(JSON.parse(readFileSync(join(ROOT, 'agents/registry/crews.json'), 'utf8')).crews).length,
  roles: sites.reduce((a, s) => a + Object.keys(s.roles).length, 0),
  handoffs: sites.reduce((a, s) => a + s.handoffs.length, 0),
  handoffs_verifiable: sites.reduce((a, s) => a + s.handoffs.filter((h) => h.verifiable).length, 0),
  handoffs_unverifiable: sites.reduce((a, s) => a + s.handoffs.filter((h) => !h.verifiable).length, 0),
  seats_involved: new Set(sites.flatMap((s) => s.derived.seats)).size,
};
want.unions_total = JSON.parse(readFileSync(join(ROOT, 'unions/registry/unions.json'), 'utf8')).unions.length;
for (const [k, v] of Object.entries(want)) ok(`figure ${k} = ${v}, recomputed from the embedded sites`, fig(k) === v, [`page says ${fig(k)}`]);
const byKind = {};
for (const s of sites) byKind[s.place.kind] = (byKind[s.place.kind] || 0) + 1;
ok('places by kind recompute', Object.entries(byKind).every(([k, v]) => html.includes(`data-fig-place="${k}">${v}<`)));

// per site
for (const s of sites) {
  const sec = html.match(new RegExp(`<section class="site" id="site-${s.id}" data-site="${s.id}">([\\s\\S]*?)</section>`));
  ok(`${s.id}: one section`, sec !== null);
  if (!sec) continue;
  const body = sec[1];
  const posts = [...body.matchAll(/<g class="post" data-role="([^"]+)" data-union="([^"]+)"/g)];
  ok(`${s.id}: one marked position per role, each carrying the role's union`,
    posts.length === Object.keys(s.roles).length && posts.every((p) => p[1] in s.roles && s.roles[p[1]].union === p[2]));
  const arrows = [...body.matchAll(/<line class="arrow( unverifiable)?" [^>]*data-handoff="(\d+)" data-by="([^"]+)" data-to="([^"]+)"/g)];
  ok(`${s.id}: one numbered arrow per hand-off, from the post handing off to the post receiving, dashed when unverifiable`,
    arrows.length === s.handoffs.length && s.handoffs.every((h, i) => Number(arrows[i][2]) === h.n && arrows[i][3] === h.by && arrows[i][4] === h.to && (arrows[i][1] !== undefined) === !h.verifiable));
  const rows = [...body.matchAll(/data-handoff-row="(\d+)"/g)].map((x) => Number(x[1]));
  ok(`${s.id}: the hand-off table lists every hand-off in order`, rows.join() === s.handoffs.map((h) => h.n).join());
  for (const f of ['roles', 'unions', 'handoffs', 'handoffs_verifiable', 'seats']) {
    const x = body.match(new RegExp(`data-site-fig="${f}">([^<]*)<`));
    const v = { roles: Object.keys(s.roles).length, unions: new Set(Object.values(s.roles).map((r) => r.union)).size, handoffs: s.handoffs.length,
      handoffs_verifiable: s.handoffs.filter((h) => h.verifiable).length, seats: s.derived.seats.length }[f];
    ok(`${s.id}: site figure ${f} = ${v} recomputes`, x !== null && Number(x[1]) === v);
  }
  const sw = body.match(/data-stop-work>([^<]*)</);
  ok(`${s.id}: the stop-work line is the crew's, verbatim`, sw !== null && unesc(sw[1]) === s.stop_work);
  const ppe = [...body.matchAll(/data-ppe="([^"]+)"/g)].map((x) => x[1]);
  ok(`${s.id}: PPE on the page is the derived list (or "none" with why, for a ${s.place.kind})`,
    s.gates.ppe.required === null ? ppe.join() === 'none' : ppe.join() === s.gates.ppe.required.join());
  const gates = [...body.matchAll(/data-gate-point="([^"]+)"/g)].map((x) => x[1]);
  ok(`${s.id}: the walkaround gates are the registry's`, gates.join() === s.gates.walkaround_before_first_move.map((g) => `${g.sim}#${g.point}`).join());
  const halls = [...body.matchAll(/href="trade_craft_3d\.html\?hall=([^"]+)" data-hall="([^"]+)"/g)];
  ok(`${s.id}: every role links to the 3D hall of its union`, halls.length === Object.keys(s.roles).length && Object.values(s.roles).every((r) => halls.some((h) => h[1] === r.union && h[2] === r.union)));
  ok(`${s.id}: says no crew page exists rather than linking to one, and links the lessons page`, /data-crew-page="none"/.test(body) && /href="trade_craft_lessons\.html" data-lessons/.test(body));
  if (s.place.kind === 'space') ok(`${s.id}: a space place draws the space plan and links the spaces page anchor`, /data-plan="space"/.test(body) && body.includes(`href="${s.place.href}" data-place-href`));
  else ok(`${s.id}: a ${s.place.kind} draws a tile, not a plan with a typed footprint`, new RegExp(`data-plan="${s.place.plan.kind}"`).test(body) && !/data-plan="space"/.test(body));
}
// plan geometry, recomputed from the built SVG: text boxes are estimated from
// character count x font size (monospace advance 0.6 em), posts and badges
// from their radii. No hand-off badge sits on a role label, a post or another
// badge; and the drawing fills its viewBox - the content's bounding box sits
// inside it and leaves no side emptier than the margin allows.
const MARGIN_MAX = 32; // the 12 px margin, plus the builder's 0.02 em pad on a long tile name
const tbox = (x, y, str, size, anchor) => {
  const w = unesc(str).length * size * 0.6;
  const x0 = anchor === 'middle' ? x - w / 2 : anchor === 'end' ? x - w : x;
  return [x0, y - 0.75 * size, x0 + w, y + 0.25 * size];
};
const overlap = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
const geoBad = [];
for (const s of sites) {
  const at = html.indexOf(`data-site="${s.id}"`);
  const st = html.indexOf('<svg class="plan"', at);
  const svg = html.slice(st, html.indexOf('</svg>', st));
  const vb = (svg.match(/viewBox="(-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)"/) || []).slice(1).map(Number);
  if (vb.length !== 4) { geoBad.push(`${s.id}: no viewBox`); continue; }
  const labels = [], postBoxes = [], badges = [], all = [];
  for (const g of svg.matchAll(/<g class="post"[^>]*transform="translate\((-?[\d.]+),(-?[\d.]+)\)">([\s\S]*?)<\/g>/g)) {
    const x = Number(g[1]), y = Number(g[2]);
    const r = Number((g[3].match(/<circle r="([\d.]+)"/) || [0, 0])[1]);
    postBoxes.push([x - r, y - r, x + r, y + r]);
    for (const t of g[3].matchAll(/<text class="lbl[^"]*" y="(-?[\d.]+)" text-anchor="(\w+)">([^<]*)<\/text>/g)) {
      labels.push([...tbox(x, y + Number(t[1]), t[3], 10, t[2]), `${s.id} label "${unesc(t[3])}"`]);
    }
  }
  for (const c of svg.matchAll(/<circle class="num" cx="(-?[\d.]+)" cy="(-?[\d.]+)" r="([\d.]+)" data-badge="(\d+)"/g)) {
    const [x, y, r] = [Number(c[1]), Number(c[2]), Number(c[3])];
    badges.push([x - r, y - r, x + r, y + r, `${s.id} badge ${c[4]}`]);
  }
  if (badges.length !== s.handoffs.length) geoBad.push(`${s.id}: ${badges.length} badges for ${s.handoffs.length} hand-offs`);
  badges.forEach((b, i) => {
    for (const l of labels) if (overlap(b, l)) geoBad.push(`${b[4]} sits on ${l[4]}`);
    for (const pb of postBoxes) if (overlap(b, pb)) geoBad.push(`${b[4]} sits on a post`);
    for (const o of badges.slice(i + 1)) if (overlap(b, o)) geoBad.push(`${b[4]} sits on ${o[4]}`);
  });
  all.push(...labels, ...postBoxes, ...badges);
  for (const r of svg.matchAll(/<rect [^>]*?x="(-?[\d.]+)" y="(-?[\d.]+)" width="([\d.]+)" height="([\d.]+)"[^>]*data-(?:plan|item)=/g)) {
    const [x, y, w, h] = r.slice(1, 5).map(Number); all.push([x, y, x + w, y + h]);
  }
  for (const l of svg.matchAll(/<line class="arrow[^"]*" x1="(-?[\d.]+)" y1="(-?[\d.]+)" x2="(-?[\d.]+)" y2="(-?[\d.]+)"/g)) {
    const [a, b, c, d] = l.slice(1, 5).map(Number); all.push([Math.min(a, c), Math.min(b, d), Math.max(a, c), Math.max(b, d)]);
  }
  for (const t of svg.matchAll(/<text class="dim" x="(-?[\d.]+)" y="(-?[\d.]+)">([^<]*)<\/text>/g)) all.push(tbox(Number(t[1]), Number(t[2]), t[3], 11, 'start'));
  const bb = [Math.min(...all.map((b) => b[0])), Math.min(...all.map((b) => b[1])), Math.max(...all.map((b) => b[2])), Math.max(...all.map((b) => b[3]))];
  const gaps = [bb[0] - vb[0], bb[1] - vb[1], vb[0] + vb[2] - bb[2], vb[1] + vb[3] - bb[3]];
  if (gaps.some((g) => g < 0)) geoBad.push(`${s.id}: drawing leaves the viewBox (gaps l,t,r,b ${gaps.map((g) => g.toFixed(1)).join(',')})`);
  if (gaps.some((g) => g > MARGIN_MAX)) geoBad.push(`${s.id}: viewBox ${vb.join(' ')} leaves empty field around the drawing ${bb.map((v) => v.toFixed(0)).join(',')} (gaps l,t,r,b ${gaps.map((g) => g.toFixed(1)).join(',')}; at most ${MARGIN_MAX})`);
}
ok('every plan keeps its hand-off badges off role labels, posts and each other, and its viewBox is the drawing\'s bounds plus a margin',
  geoBad.length === 0, geoBad.slice(0, 12));
// honesty lines are the registry's
for (const k of ['authored', 'no_multi_user', 'not_a_certification', 'not_stated', 'ppe']) {
  const x = html.match(new RegExp(`data-honesty="${k}">([^<]*)<`));
  ok(`honesty line ${k} is the registry's verbatim`, x !== null && unesc(x[1]) === D.honesty[k]);
}
ok('no typed count: every data-fig on the page is one recomputed above', [...html.matchAll(/data-fig="([^"]+)"/g)].every((x) => x[1] in want));
// hrefs resolve
const hrefs = [...new Set([...html.matchAll(/href="([^"#?]+)(?:[#?][^"]*)?"/g)].map((x) => x[1]))].filter((h) => !/^(data:|https?:)/.test(h));
ok(`every href on the page resolves to a file on disk (${hrefs.join(', ')})`, hrefs.length > 0 && hrefs.every((h) => existsSync(join(WEB, h))), hrefs.filter((h) => !existsSync(join(WEB, h))));

{
  const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
  const dup = [...new Set(ids.filter((x, i) => ids.indexOf(x) !== i))];
  ok('every id on the page is unique (one arrowhead marker per site plan, each arrow pointing at its own plan\'s)', dup.length === 0
    && [...html.matchAll(/marker-end="url\(#([^)]+)\)"/g)].every((m) => ids.includes(m[1])), dup);
  ok('every hand-off table sits in its own horizontal scroll wrapper, so a 390px screen does not cut its columns off',
    (html.match(/<div class="tablewrap"><table class="sched">/g) || []).length === (html.match(/<table class="sched">/g) || []).length
    && /\.tablewrap\{overflow-x:auto/.test(html), []);
}


/* ---- simulated tasks (TASKS, wave 3): boards come from tasks/registry/tasks.json only ---- */
const TK = JSON.parse(readFileSync(new URL('../tasks/registry/tasks.json', import.meta.url), 'utf8'));
const tkRel = (h) => h === null ? null : (h.startsWith('web/') ? h.slice(4) : '../' + h);
const tkEsc = (h) => h.replace(/&/g, "&amp;");
const tkCards = (s) => s.split('<article class="tk-card" data-task="').slice(1).map((c) => {
  const id = c.slice(0, c.indexOf('"')); const m = c.match(/<a class="tk-go" href="([^"]+)"/);
  return [id, m && c.indexOf(m[0]) < c.indexOf('</article>') ? m[1] : null]; });
const tkWant = (ts) => ts.map((t) => [t.id, t.launch.href === null ? null : tkEsc(tkRel(t.launch.href))]);
const tkHall = (slug) => TK.tasks.filter((t) => t.place.kind === 'hall' && t.place.id === slug);
{
  const siteTasks = (s) => [TK.tasks.find((t) => t.id === `crew-${s.id}`)].concat(TK.tasks.filter((t) => t.seat === s.crew.seat
    && t.kind !== 'crew-handoff' && (s.place.campus === null || t.kind !== 'sim-scenario' || t.place.campus === s.place.campus)));
  const tkBad = [];
  const all = new Set();
  for (const s of D.sites) {
    const sec = html.match(new RegExp(`<section class="site" id="site-${s.id}" data-site="${s.id}">([\\s\\S]*?)</section>`));
    const want = siteTasks(s); want.forEach((t) => all.add(t.id));
    const body = sec ? sec[1] : '';
    const got = [...body.matchAll(/<article class="tk-card" data-task="([^"]+)"/g)].map((m) => m[1]);
    if (got.join() !== want.map((t) => t.id).join()) tkBad.push(`${s.id}: cards ${got.join(',')} want ${want.map((t) => t.id).join(',')}`);
    if (!new RegExp(`data-tk-board data-total="${want.length}"`).test(body)) tkBad.push(`${s.id}: board total is not ${want.length}`);
    if (JSON.stringify(tkCards(body)) !== JSON.stringify(tkWant(want))) tkBad.push(`${s.id}: card launch hrefs differ from the registry`);
  }
  ok('[tasks] every site carries a Simulated tasks board: its crew hand-off plus its seat\'s walkaround and campus scenarios, hrefs verbatim from tasks/registry', tkBad.length === 0, tkBad);
  const fig = html.match(/data-tasks-fig="tasks">(\d+)</);
  ok('[tasks] the page\'s task figure is the count of distinct tasks on its boards (recomputed)', fig !== null && Number(fig[1]) === all.size);
  const hon = html.match(/data-tasks-honesty>([^<]*)</);
  ok('[tasks] the tasks honesty line is the registry\'s verbatim, once', hon !== null && unesc(hon[1]) === TK.honesty.practice
    && (html.match(/data-tasks-honesty/g) || []).length === 1);
  const lessonLinks = [...html.matchAll(/href="trade_craft_lessons\.html#([^"]+)"/g)].map((m) => m[1]);
  ok('[tasks] every lesson link lands on the anchor the lessons page reads (#lesson-<id>)', lessonLinks.length > 0 && lessonLinks.every((a) => a.startsWith('lesson-')), lessonLinks.filter((a) => !a.startsWith('lesson-')));
  ok('[tasks] the filter chips are wired by one delegated listener', (html.match(/\[data-tk-board\]/g) || []).length >= 1 && /data-tk-filter="all"/.test(html));
}

ok('[theme] the page opens on MEDIA\'s pagehero band whose title is its one <h1>, and no second palette (body.tc-theme) fights its own tokens',
  (html.match(/<h1\b/g) || []).length === 1 && /<section class="ph[^"]*"[^>]*data-ph[\s\S]*?<h1\b/.test(html) && !/<body class="tc-theme">/.test(html));
ok('[theme] every hero word is a tasks.ws.* catalog string (en)', (() => {
  const en = JSON.parse(readFileSync(new URL('../i18n/locales/en.json', import.meta.url), 'utf8')).strings;
  return ['tasks.ws.kicker', 'tasks.ws.lede', 'tasks.ws.credit'].every((k) => html.includes(en[k].replace(/&/g, '&amp;').replace(/'/g, '&#x27;')) || html.includes(en[k]));
})());

// QA wave 4: a site style re-declares plate/panel, so status colours must follow it
// (--tc-ok/--tc-warn on body while a style is on, else the page's own values)
ok('[style] status colours (--good/--warn/--crit) follow the active site style via --tc-ok/--tc-warn on body, falling back to the page\'s own',
  html.includes(':root{--pg-good:var(--good);--pg-warn:var(--warn);--pg-crit:var(--crit)}')
  && html.includes('body{--good:var(--tc-ok,var(--pg-good));--warn:var(--tc-warn,var(--pg-warn));--crit:var(--tc-warn,var(--pg-crit))}')
  && html.includes('--tc-warn:') && html.includes('--tc-ok:'));

console.log(`web/test_worksites: ${n} checks passed${bad ? `, ${bad} FAILED` : ''}`);
process.exit(bad ? 1 : 0);
