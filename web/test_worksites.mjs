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
// honesty lines are the registry's
for (const k of ['authored', 'no_multi_user', 'not_a_certification', 'not_stated', 'ppe']) {
  const x = html.match(new RegExp(`data-honesty="${k}">([^<]*)<`));
  ok(`honesty line ${k} is the registry's verbatim`, x !== null && unesc(x[1]) === D.honesty[k]);
}
ok('no typed count: every data-fig on the page is one recomputed above', [...html.matchAll(/data-fig="([^"]+)"/g)].every((x) => x[1] in want));
// hrefs resolve
const hrefs = [...new Set([...html.matchAll(/href="([^"#?]+)(?:[#?][^"]*)?"/g)].map((x) => x[1]))].filter((h) => !/^(data:|https?:)/.test(h));
ok(`every href on the page resolves to a file on disk (${hrefs.join(', ')})`, hrefs.length > 0 && hrefs.every((h) => existsSync(join(WEB, h))), hrefs.filter((h) => !existsSync(join(WEB, h))));

console.log(`web/test_worksites: ${n} checks passed${bad ? `, ${bad} FAILED` : ''}`);
process.exit(bad ? 1 : 0);
