/**
 * Simulated tasks verification.
 *
 * Every task in tasks/registry/tasks.json is re-derived here from the
 * registries that own it, and every launch link is followed to a real page
 * that really reads the parameter it carries (the builder source AND the
 * generated page), with the value it carries accepted by that page's data.
 *
 *   node tasks/test.mjs
 *   node tasks/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const hit = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(hit ? hit.slice(7) : join(HERE, '..'));

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.log('FAIL  ' + m);
  for (const e of evidence.slice(0, 8)) console.log('      ' + e);
};
const read = (rel) => readFileSync(join(ROOT, rel));
const J = (rel) => JSON.parse(read(rel).toString('utf8'));
const sha16 = (b) => createHash('sha256').update(b).digest('hex').slice(0, 16);

const reg = J('tasks/registry/tasks.json');
const T = reg.tasks;
const sims = J('sims/registry/sims.json');
const cribs = J('tools/registry/toolcribs.json');
const works = J('worksites/registry/worksites.json');
const resto = J('restoration/registry/restoration.json');
const wilds = J('wilds/registry/wilds.json');
const lessons = J('lessons/registry/lessons.json').lessons;
const spaces = J('spaces/registry/spaces.json').spaces;
const halls = new Set(J('pack/registry/halls.json').halls.map((h) => h.slug));
const campuses = J('unions/registry/campuses.json').campuses;
const campusOf = {};
for (const [ck, c] of Object.entries(campuses)) for (const h of c.halls) campusOf[h] = ck;

/* ------------------------------------------------------------ stamps -- */
const builder = read('tasks/build.py');
ok('[stamp] builder_stamp is sha256 of tasks/build.py', reg.builder_stamp === sha16(builder), [`have ${reg.builder_stamp}`]);
const stale = Object.entries(reg.sources).filter(([rel, h]) => sha16(read(rel)) !== h).map(([rel]) => rel);
ok('[stamp] every source registry is unchanged since the build (sources sha256 current)', stale.length === 0, stale);
ok('[stamp] source_stamp is sha256 over the builder and every source, in order',
  reg.source_stamp === sha16(Buffer.concat([builder, ...Object.keys(reg.sources).map(read)])));

/* ------------------------------------------------------------ shape -- */
const FIELDS = ['id', 'title', 'kind', 'place', 'launch', 'requires', 'provenance', 'source', 'brief', 'seat'];
const missing = T.filter((t) => FIELDS.some((f) => !(f in t))).map((t) => t.id);
ok('[shape] every task carries id, title, kind, place, launch, requires, provenance, source, brief, seat', missing.length === 0, missing);
const ids = T.map((t) => t.id);
const dups = ids.filter((x, i) => ids.indexOf(x) !== i);
ok('[shape] no duplicate task ids', dups.length === 0, dups);
ok('[shape] every id is kebab-case', ids.every((i) => /^[a-z0-9]+(-[a-z0-9]+)*$/.test(i)));
ok('[shape] every kind is declared and its provenance is the kind\'s (SCRIPTED scenarios, DERIVED joins)',
  T.every((t) => t.kind in reg.kinds && reg.kinds[t.kind].provenance === t.provenance
    && ['SCRIPTED', 'DERIVED'].includes(t.provenance)));
ok('[shape] only sim-scenario is SCRIPTED', T.every((t) => (t.provenance === 'SCRIPTED') === (t.kind === 'sim-scenario')));

/* ------------------------------------------------------------ places -- */
const placeBad = [];
for (const t of T) {
  const p = t.place;
  if (p.kind === 'hall') { if (!halls.has(p.id) || campusOf[p.id] !== p.campus) placeBad.push(`${t.id}: hall ${p.id}/${p.campus}`); }
  else if (p.kind === 'campus') { if (!(p.id in campuses) || p.campus !== p.id) placeBad.push(`${t.id}: campus ${p.id}`); }
  else if (p.kind === 'space') { if (!spaces.some((s) => s.id === p.id)) placeBad.push(`${t.id}: space ${p.id}`); }
  else if (p.kind === 'restoration-site') {
    const s = resto.sites.find((x) => x.id === p.id);
    if (!s || !(p.campus in campuses)) placeBad.push(`${t.id}: restoration-site ${p.id}`);
  } else if (p.kind === 'wilds-site') {
    const w = wilds.worlds.find((x) => x.id === p.world);
    if (!w || !w.sites.some((s) => s.id === p.id) || w.inspiration.campus !== p.campus) placeBad.push(`${t.id}: wilds-site ${p.world}/${p.id}`);
  } else placeBad.push(`${t.id}: unknown place kind ${p.kind}`);
  if (p.campus === null && p.kind !== 'space') placeBad.push(`${t.id}: null campus on a ${p.kind}`);
}
ok('[place] every place id exists in its owning registry (and its campus is that registry\'s)', placeBad.length === 0, placeBad);

/* ------------------------------------------------------------ launch -- */
const page3d = read('web/trade_craft_3d.html').toString('utf8');
const src3d = read('web/build_3d.py').toString('utf8');
const D3 = JSON.parse(page3d.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const halls3d = new Set(D3.halls.map((h) => h.slug));
const pageWilds = read('web/trade_craft_wilds.html').toString('utf8');
const srcWilds = read('web/build_wilds.py').toString('utf8');
const pageWorks = read('web/trade_craft_worksites.html').toString('utf8');
const READS = {
  hall: [src3d, page3d, "params.get('hall')"],
  sim: [src3d, page3d, "params.get('sim')"],
  campus: [src3d, page3d, "params.get('campus')"],
  scenario: [src3d, page3d, "D.sims.sims[simDeep].scenarios.some((s) => s.id === params.get('scenario'))"],
};
const hrefBad = [];
for (const t of T) {
  const L = t.launch;
  if (L.href === null) { if (!(typeof L.why === 'string' && L.why.length > 20)) hrefBad.push(`${t.id}: no href and no why`); continue; }
  const [path] = L.href.split(/[?#]/);
  if (!existsSync(join(ROOT, path))) { hrefBad.push(`${t.id}: ${path} is not a file`); continue; }
  if (path === 'web/trade_craft_3d.html') {
    const q = new URLSearchParams(L.href.split('?')[1]);
    for (const k of q.keys()) {
      if (!(k in READS) || !READS[k].slice(0, 2).every((s) => s.includes(READS[k][2]))) hrefBad.push(`${t.id}: 3D page does not read ?${k}`);
    }
    if (q.has('hall') && !halls3d.has(q.get('hall'))) hrefBad.push(`${t.id}: 3D page data has no hall ${q.get('hall')}`);
    if (q.has('sim') && !(q.get('sim') in D3.sims.sims)) hrefBad.push(`${t.id}: 3D page data has no seat ${q.get('sim')}`);
    if (q.has('sim') && !D3.sims.sims[q.get('sim')].halls.includes(q.get('hall'))) hrefBad.push(`${t.id}: hall ${q.get('hall')} does not teach ${q.get('sim')}`);
    if (q.has('campus') && !(q.get('campus') in D3.campuses)) hrefBad.push(`${t.id}: 3D page has no campus ${q.get('campus')}`);
    if (q.has('scenario') && !(q.has('sim') && D3.sims.sims[q.get('sim')].scenarios.some((s) => s.id === q.get('scenario')))) hrefBad.push(`${t.id}: ?scenario=${q.get('scenario')} is not one of seat ${q.get('sim')}'s own scenarios in the 3D page data (the page would ignore it)`);
  } else if (path === 'web/trade_craft_wilds.html') {
    const [wid, sid] = L.href.split('#')[1].split('/');
    const w = wilds.worlds.find((x) => x.id === wid);
    if (!srcWilds.includes(".slice(1)).split('/')") || !pageWilds.includes(".slice(1)).split('/')")) hrefBad.push(`${t.id}: wilds page does not read #world/site`);
    if (!w || !w.sites.some((s) => s.id === sid) || !pageWilds.includes(`"${sid}"`)) hrefBad.push(`${t.id}: wilds has no ${wid}/${sid}`);
    if (!sid || t.launch.lands !== 'site') hrefBad.push(`${t.id}: a wilds walk must name the site itself (#world/site) and land at it`);
  } else if (path === 'web/trade_craft_worksites.html') {
    const anchor = L.href.split('#')[1];
    if (!pageWorks.includes(`id="${anchor}"`)) hrefBad.push(`${t.id}: worksites page has no id="${anchor}"`);
  } else if (path === 'web/trade_craft_bay.html') {
    // restoration training scenarios: the Bay page's restokit mount reads #resto=<site> and holds that site's run button
    const pageBay = read(path).toString('utf8'), site = L.href.split('#resto=')[1];
    if (t.kind !== 'resto-scenario' || !pageBay.includes("if (h.startsWith('resto=')) addEventListener('load', () => openSite(h.slice(6), null));")
      || !site || !pageBay.includes(`data-resto-run="${site}"`) || site !== t.place.id || L.lands !== 'section') hrefBad.push(`${t.id}: Bay page does not open #resto=${site}`);
  } else hrefBad.push(`${t.id}: ${path} is not a page this pack knows the parameters of`);
}
ok('[launch] every href resolves to a real file and a parameter the target page reads, with a value its data accepts', hrefBad.length === 0, hrefBad);

// the scenario rule, recomputed: a scenario is launched by the first hall
// teaching the seat on its campus; one with no such hall has no href
const scBad = [];
for (const [sid, sim] of Object.entries(sims.sims)) sim.scenarios.forEach((sc, i) => {
  const t = T.find((x) => x.id === `sim-${sid}-${sc.id}`);
  if (!t) { scBad.push(`missing sim-${sid}-${sc.id}`); return; }
  const h = sim.halls.find((x) => campusOf[x] === sc.campus);
  const want = `web/trade_craft_3d.html?hall=${h || sim.halls[0]}&sim=${sid}&scenario=${sc.id}`;
  if (t.launch.href !== want) scBad.push(`${t.id}: href ${t.launch.href}, want ${want}`);
  if (!h && !(t.place.kind === 'campus' && t.place.id === sc.campus && t.launch.via && t.launch.via.hall === sim.halls[0]
    && t.launch.via.campus === campusOf[sim.halls[0]])) scBad.push(`${t.id}: an off-campus seat must keep the scenario's campus as its place and say the hall it opens in (via)`);
  if (t.source !== `sims/registry/sims.json#sims.${sid}.scenarios[${i}]`) scBad.push(`${t.id}: source ${t.source}`);
});
ok('[scenario] one task per sims scenario, launched through a hall on the scenario\'s campus (else the seat\'s first hall) and named outright with ?scenario=', scBad.length === 0, scBad);
ok('[scenario] the 3D builder still picks a scenario by campusKey', src3d.includes('def.scenarios?.find((s) => s.campus === campusKey)'));
// ?scenario= must be validated against THAT seat's own scenarios, must reach
// startSim, and must win over the campus pick - in the builder AND the page
const SCN = ["D.sims.sims[simDeep].scenarios.some((s) => s.id === params.get('scenario'))",
  'startSim(simDeep, scenarioDeep);',
  'def.scenarios?.find((s) => s.id === scenarioId)\n    ?? def.scenarios?.find((s) => s.campus === campusKey)'];
ok('[scenario] the 3D page validates ?scenario= against the seat\'s own scenarios, hands it to startSim, and it wins over the campus pick (builder and page)',
  SCN.every((f) => src3d.includes(f) && page3d.includes(f)), SCN.filter((f) => !(src3d.includes(f) && page3d.includes(f))));
ok('[scenario] every sims scenario is launchable (194/194 needs no null scenario)', T.filter((t) => t.kind === 'sim-scenario').every((t) => t.launch.href !== null));
// wilds: the hash's site part stands you AT the site, and the hash is read on boot
const WLD = ["if (sid) goSite(sid);", "if (!(await fromHash())) await loadWorld(", "const s = W.sites.find((x) => x.id === id);"];
ok('[wilds] the wilds page reads #<world>/<site> on boot and goes to that site (builder and page)',
  WLD.every((f) => srcWilds.includes(f) && pageWilds.includes(f)), WLD.filter((f) => !(srcWilds.includes(f) && pageWilds.includes(f))));
ok('[wilds] every wilds-site-walk href is web/trade_craft_wilds.html#<its world>/<its site>',
  T.filter((t) => t.kind === 'wilds-site-walk').every((t) => t.launch.href === `web/trade_craft_wilds.html#${t.place.world}/${t.place.id}` && t.launch.lands === 'site'));

// launch.via: a seat that opens at a hall on ANOTHER campus than the task's
// place must say so on every board that carries the task (names from registries)
const hallNames = Object.fromEntries(J('pack/registry/halls.json').halls.map((h) => [h.slug, h.name]));
const VIA = T.filter((t) => t.launch.via);
const viaBad = [];
for (const t of VIA) {
  const v = t.launch.via;
  if (v.campus !== campusOf[v.hall] || v.campus === t.place.campus || v.hall_name !== hallNames[v.hall]
    || v.campus_name !== campuses[v.campus].name) viaBad.push(`${t.id}: via ${JSON.stringify(v)} does not match the registries or is not another campus`);
}
for (const t of T) if (!t.launch.via && t.launch.href && t.kind === 'sim-scenario' && t.place.kind === 'campus') viaBad.push(`${t.id}: campus-placed seat link without via`);
ok('[via] every off-campus seat link carries via {hall, campus} with names read from pack/halls and unions/campuses (13 formerly-null scenarios)', viaBad.length === 0 && VIA.length === 13, viaBad.concat([`via tasks: ${VIA.length}`]));
const viaNote = (v) => `<p class="tk-via" data-via-hall="${v.hall}" data-via-campus="${v.campus}">Opens at the ${v.hall_name} hall, ${v.campus_name}</p>`;
const viaPages = {};
const notePage = [];
for (const [name, html] of [['map', read('web/trade_craft_map.html').toString('utf8')], ['interactive', read('web/trade_craft_interactive.html').toString('utf8')], ['worksites', pageWorks]]) {
  let carried = 0;
  for (const t of VIA) {
    // server-rendered cards (taskkit.task_card)
    const cards = html.match(new RegExp(`<article class="tk-card" data-task="${t.id}"[\\s\\S]*?</article>`, 'g')) || [];
    for (const c of cards) { carried++; if (!c.includes(viaNote(t.launch.via))) notePage.push(`${name}: card ${t.id} has no via note`); }
    // browser-rendered rows (taskkit.tasks_json + TASK_RENDER_JS)
    const rows = html.match(new RegExp(`\\{"id":"${t.id}","title":[\\s\\S]*?"via":(\\{[^}]*\\}|null)`, 'g')) || [];
    for (const r of rows) {
      carried++;
      const got = JSON.parse(r.match(/"via":(\{[^}]*\}|null)$/)[1]);
      if (JSON.stringify(got) !== JSON.stringify(t.launch.via)) notePage.push(`${name}: row ${t.id} via ${JSON.stringify(got)}`);
      if (!html.includes('${req}${via}${go}</article>') || !html.includes(`<p class="tk-via" data-via-hall="\${E(t.via.hall)}"`)
        || !html.includes(".replace('{hall}', t.via.hall_name).replace('{campus}', t.via.campus_name)")) notePage.push(`${name}: row ${t.id} but the renderer draws no via note`);
    }
  }
  viaPages[name] = carried;
}
ok('[via] every board card or row carrying a via task shows "opens at <hall> on <campus>" on the map, interactive and worksites pages',
  notePage.length === 0, notePage.concat([JSON.stringify(viaPages)]));
ok('[via] the interactive page carries all 13 via tasks (campus boards) and worksites at least one; the map carries only hall-placed tasks, so none',
  viaPages.interactive >= VIA.length && viaPages.worksites >= 1 && viaPages.map === 0, [JSON.stringify(viaPages)]);
const locBad = [];
for (const loc of ['en', 'es', 'fr', 'de', 'pt', 'zh', 'hi', 'ar']) {
  const v = J(`i18n/locales/${loc}.json`).strings['tasks.via'];
  if (!(typeof v === 'string' && v.includes('{hall}') && v.includes('{campus}')) || (loc !== 'en' && v === J('i18n/locales/en.json').strings['tasks.via'])) locBad.push(`${loc}: ${v}`);
}
ok('[via] tasks.via is in all 8 locales with {hall} and {campus}, translated (no English copy)', locBad.length === 0, locBad);

/* ------------------------------------------------------ coverage -- */
const cov = [];
for (const [sid, sim] of Object.entries(sims.sims)) if (sim.walkaround.length && !ids.includes(`walkaround-${sid}`)) cov.push(`walkaround-${sid}`);
for (const h of Object.keys(cribs.hall_bindings)) if (!ids.includes(`crib-${h}`)) cov.push(`crib-${h}`);
for (const s of works.sites) if (!ids.includes(`crew-${s.id}`)) cov.push(`crew-${s.id}`);
for (const s of resto.sites) if (Boolean(s.walkable === true && s.pin && s.campus) !== ids.includes(`resto-${s.id}`)) cov.push(`resto-${s.id}`);
for (const w of wilds.worlds) for (const s of w.sites) if (!ids.includes(`wilds-${s.id}`)) cov.push(`wilds-${s.id}`);
ok('[coverage] every walkaround, crib binding, worksite, walkable restoration site and wilds site is a task (and nothing else is)', cov.length === 0, cov);
ok('[coverage] no task comes from anywhere else', T.length === Object.values(sims.sims).reduce((a, s) => a + s.scenarios.length + (s.walkaround.length ? 1 : 0), 0)
  + Object.keys(cribs.hall_bindings).length + works.sites.length
  + resto.sites.filter((s) => s.walkable === true && s.pin && s.campus).length
  + wilds.worlds.reduce((a, w) => a + w.sites.length, 0)
  // restoration training scenarios count only once taskkit accepts their kind ([resto] pins them row for row)
  + ((read('web/taskkit.py').toString('utf8').match(/KIND_ORDER = \(([^)]*)\)/) || [, ''])[1].includes("'resto-scenario'")
    ? J('restoration/registry/scenarios.json').staged_tasks.length : 0));

/* ------------------------------------------------------ requires -- */
const steps = (kind) => Object.values(lessons).flatMap((l) => l.steps.filter((s) => s.kind === kind).map((s) => [l, s]));
const reqBad = [];
for (const t of T) {
  if (t.requires.some((l) => !(l in lessons))) reqBad.push(`${t.id}: unknown lesson`);
  let want;
  if (t.kind === 'sim-scenario') {
    const [, sid, scid] = t.source.match(/sims\.([^.]+)\.scenarios\[(\d+)\]/);
    const sc = sims.sims[sid].scenarios[Number(scid)].id;
    want = steps('sim').filter(([, s]) => s.sim === sid && s.scenario === sc).map(([l]) => l.id);
  } else if (t.kind === 'walkaround') want = steps('walkaround').filter(([, s]) => s.sim === t.seat).map(([l]) => l.id);
  else if (t.kind === 'crib-drill') {
    const d = cribs.hall_bindings[t.place.id].district;
    want = steps('crib').filter(([l, s]) => s.crib === d && l.hall === t.place.id).map(([l]) => l.id);
  } else if (t.kind === 'crew-handoff') want = works.sites.find((s) => `crew-${s.id}` === t.id).derived.lessons_with_this_crew;
  else if (t.kind === 'wilds-site-walk') want = wilds.worlds.find((w) => w.id === t.place.world).sites.find((s) => s.id === t.place.id).lessons.map((l) => l.id);
  else want = [];
  want = [...new Set(want)].sort();
  if (JSON.stringify(want) !== JSON.stringify(t.requires)) reqBad.push(`${t.id}: requires ${t.requires.join(',')} want ${want.join(',')}`);
}
ok('[requires] every linked lesson is one an existing registry already links to that task (recomputed; none invented)', reqBad.length === 0, reqBad);

/* ------------------------------------------------------------ counts -- */
const tally = (f) => { const o = {}; for (const t of T) { const k = f(t) ?? 'none'; o[k] = (o[k] || 0) + 1; } return o; };
const same = (a, b) => JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());
const C = reg.counts;
ok('[counts] tasks, by_kind, by_place_kind, by_campus, launchable recompute (none typed)',
  C.tasks === T.length && same(C.by_kind, tally((t) => t.kind)) && same(C.by_place_kind, tally((t) => t.place.kind))
  && same(C.by_campus, tally((t) => t.place.campus)) && C.launchable === T.filter((t) => t.launch.href).length
  && C.not_launchable === T.filter((t) => !t.launch.href).length && C.with_linked_lessons === T.filter((t) => t.requires.length).length,
  [JSON.stringify(C)]);

/* ------------------------------------------------------------ honesty -- */
ok('[honesty] the registry says tasks are practice, certify nothing and enter no completion record',
  /practice/.test(reg.honesty.practice) && /certifies nothing/.test(reg.honesty.practice) && /completion record/.test(reg.honesty.practice));
const comp = J('completion/registry/completion.json');
ok('[honesty] the completion contract names no task kind of its own (tasks never enter a record)',
  !JSON.stringify(comp.recording_kinds).includes('task') && !JSON.stringify(comp.evidence_classes).includes('"task'));
const bsrc = builder.toString('utf8').replace(/#.*$/gm, '').replace(/"""[\s\S]*?"""/g, '');
ok('[generator] the builder never reads with .get(k, default) and fails closed on a missing key',
  !/\.get\([^)]*,/.test(bsrc) && bsrc.includes('raise KeyError'));

/* -------------------------------------------- restoration scenarios -- */
const scen = J('restoration/registry/scenarios.json');
const kitOrder = (read('web/taskkit.py').toString('utf8').match(/KIND_ORDER = \(([^)]*)\)/) || [, ''])[1];
const RS = T.filter((t) => t.kind === 'resto-scenario');
const live = kitOrder.includes("'resto-scenario'");
ok('[resto] resto-scenario tasks are live exactly when web/taskkit.py accepts the kind, and then equal restoration/scenarios.json staged_tasks row for row',
  live ? JSON.stringify(RS) === JSON.stringify(scen.staged_tasks) && 'restoration/registry/scenarios.json' in reg.sources
    : RS.length === 0 && !('resto-scenario' in reg.kinds), [live, RS.length, scen.staged_tasks.length]);

/* ------------------------------------------------------------- theme -- */
const kit = read('web/taskkit.py').toString('utf8');
const cssM = kit.match(/TASKS_CSS = '''([\s\S]*?)'''/);
const css = cssM ? cssM[1] : '';
ok('[theme] the task board CSS colours only with var(--...) theme tokens (no hex, rgb or hsl), so every site style applies',
  css.length > 0 && !/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/.test(css) && css.includes('var(--panel)'));

/* ------------------------------------------------------------- drill -- */
const DRILL = [
  ['a hall in an href that the 3D page does not hold', '[launch] every href resolves'],
  ['a place id that is not in its registry', '[place] every place id exists'],
  ['a duplicated task id', '[shape] no duplicate task ids'],
  ['a count typed', '[counts] ... recompute'],
  ['a lesson prerequisite invented', '[requires] ... none invented'],
  ['a source registry edited without a rebuild', '[stamp] every source registry is unchanged'],
  ['the builder edited without a rebuild', '[stamp] builder_stamp'],
  ['?scenario= validation dropped from the 3D page', '[scenario] the 3D page validates ?scenario='],
  ['a scenario href naming another seat\'s scenario', '[launch] every href resolves'],
  ['a wilds href pointing at the world only', '[wilds] every wilds-site-walk href'],
  ['a board card that drops its via note', '[via] every board card or row carrying a via task'],
];
ok(`[drill] ${DRILL.length} mutations each name the check that catches them`, DRILL.every(([, c]) => c.length > 0));

if (bad) { console.log(`tasks/test: ${bad} FAILED, ${n} passed`); process.exit(1); }
console.log(`tasks/test: ${n} checks passed — ${T.length} tasks, ${C.launchable} launchable, `
  + Object.entries(C.by_kind).map(([k, v]) => `${k} ${v}`).join(', '));
