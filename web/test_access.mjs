/**
 * Static checks for the doors between the walkable worlds and the 3D interiors, keyboard access, and the
 * cross-links between the directory pages and the worlds (DOOR-LINK on web/trade_craft_parishes.html and
 * web/trade_craft_bay.html, built by web/build_parishes.py; DOOR-BACK on web/trade_craft_3d.html, built by
 * web/build_3d.py). Every door and link is re-derived here from the registries and asserted to exist on its
 * target page. Prints `  ok ` per check and `FAIL` at column 0; exits non-zero on any failure.
 */
import { readFileSync, existsSync } from 'node:fs';

const ROOT = new URL('..', import.meta.url).pathname;
const read = (p) => readFileSync(ROOT + p, 'utf8');
const reg = (p) => JSON.parse(read(p));
let fails = 0, oks = 0;
function check(name, cond, why = '') {
  if (cond) { oks++; console.log(`  ok ${name}`); } else { fails++; console.log(`FAIL ${name}${why ? ' :: ' + why : ''}`); }
}
const pageJson = (html, id) => { const m = html.match(new RegExp(`<script type="application/json" id="${id}">([\\s\\S]*?)</script>`)); return m ? JSON.parse(m[1]) : null; };
const between = (s, a, b) => { const i = s.indexOf(a), j = s.indexOf(b, i + 1); return i < 0 || j < 0 ? '' : s.slice(i, j + b.length); };
const PAR = read('web/trade_craft_parishes.html'), BAY = read('web/trade_craft_bay.html'), P3 = read('web/trade_craft_3d.html');
const D3 = JSON.parse(P3.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const CP = reg('campusplan/registry/campusplan.json'), UN = reg('unions/registry/unions.json'), UC = reg('unions/registry/campuses.json');
const RS = reg('restoration/registry/restoration.json'), BA = reg('bayarea/registry/bayarea.json'), RB = reg('robotics/registry/robotics.json');
const unionBySlug = new Map(UN.unions.map((u) => [u.slug, u]));
const doorsOf = (html) => { const m = html.match(/const DL_DOORS = (\[[\s\S]*?\]), DL_WORLD = '(\w+)'/); return m ? { doors: JSON.parse(m[1].replace(/<\\\//g, '</')), world: m[2] } : null; };
const DLP = doorsOf(PAR), DLB = doorsOf(BAY);

// [doors] the parish world: one door per union-hall lot of a campus placed in a parish of this page, plus its commons
{
  const D = pageJson(PAR, 'parishes-data'), fips = new Set(D.parishes.map((p) => p.id));
  const want = [];
  for (const [k, c] of Object.entries(CP.campuses)) {
    const pl = c.placement.parish; if (!pl || !fips.has(pl.fips)) continue;
    want.push({ id: `campus:${k}`, x: +(pl.world_scene.x + c.commons.x).toFixed(2), z: +(pl.world_scene.z + c.commons.z).toFixed(2) });
    for (const l of c.lots) want.push({ id: `hall:${l.hall}`, x: +(pl.world_scene.x + l.building.door.x).toFixed(2), z: +(pl.world_scene.z + l.building.door.z).toFixed(2) });
  }
  check('[doors] parish page embeds the DOOR-LINK door list for world "parishes"', DLP && DLP.world === 'parishes');
  const got = new Map((DLP ? DLP.doors : []).map((d) => [d.id, d]));
  check('[doors] parish doors = campusplan lots + commons of the campuses placed in this world (re-derived)', DLP && DLP.doors.length === want.length && want.length > 1,
    `want ${want.length}, page ${DLP && DLP.doors.length}`);
  const bad = want.filter((w) => { const d = got.get(w.id); return !d || Math.abs(d.x - w.x) > 0.01 || Math.abs(d.z - w.z) > 0.01; });
  check('[doors] every parish door stands on its lot door point (placement world_scene + building.door)', bad.length === 0, bad.slice(0, 3).map((b) => b.id).join(', '));
  const halls = (DLP ? DLP.doors : []).filter((d) => d.kind === 'hall');
  const nameBad = halls.filter((d) => unionBySlug.get(d.id.slice(5))?.name !== d.name);
  check('[doors] every hall door carries the unions registry name of its hall', halls.length > 0 && nameBad.length === 0, nameBad.map((d) => d.id).join(', '));
  const campusBad = halls.filter((d) => !Object.values(UC.campuses).some((c) => c.halls.includes(d.id.slice(5))));
  check('[doors] every hall door names a hall listed on a campus in unions/registry/campuses.json', campusBad.length === 0, campusBad.map((d) => d.id).join(', '));
}
// [doors] the Bay world: its campus landmark and each walkable restoration site the 3D page can walk
{
  const D = pageJson(BAY, 'parishes-data'), fips = new Set(D.parishes.map((p) => p.id));
  const walk = new Set(RS.sites.filter((s) => s.pin === true && s.campus && s.walkable === true).map((s) => s.id));
  const wantResto = [], wantCampus = [];
  for (const [f, c] of Object.entries(BA.counties)) {
    if (!fips.has(f)) continue;
    for (const x of c.campuses) wantCampus.push(`campus:${x.campus}`);
    for (const x of c.restoration_sites) if (walk.has(x.id)) wantResto.push(`resto:${x.id}`);
  }
  const ids = (DLB ? DLB.doors : []).map((d) => d.id).sort();
  check('[doors] Bay page embeds the DOOR-LINK door list for world "bay"', DLB && DLB.world === 'bay');
  check('[doors] Bay doors = campus landmarks + walkable restoration sites (re-derived from bayarea + restoration)',
    JSON.stringify(ids) === JSON.stringify([...wantCampus, ...wantResto].sort()) && wantResto.length > 0, `page ${ids.join(',')}`);
  const notWalk = RS.sites.filter((s) => s.walkable !== true).map((s) => `resto:${s.id}`);
  check('[doors] no door to a site that is not walkable (Hunters Point, Treasure Island NSTI)', !ids.some((i) => notWalk.includes(i)));
}
// [doors] every door target exists on the 3D page, through its existing deep link
{
  const all = [...(DLP ? DLP.doors : []), ...(DLB ? DLB.doors : [])];
  const hallSet = new Set(D3.halls.map((h) => h.slug)), campusSet = new Set(Object.keys(D3.campuses));
  const restoSet = new Set(D3.restoration.sites.filter((s) => s.e !== undefined).map((s) => s.id));
  const miss = all.filter((d) => {
    const m = d.href.match(/^trade_craft_3d\.html\?(hall|campus|resto)=([a-z0-9-]+)$/);
    if (!m) return true;
    return !(m[1] === 'hall' ? hallSet : m[1] === 'campus' ? campusSet : restoSet).has(m[2]) || m[2] !== d.id.split(':')[1];
  });
  check('[doors] every door href is trade_craft_3d.html?hall|campus|resto=<id> and the id exists in the 3D page data', all.length > 0 && miss.length === 0, miss.map((d) => d.id).join(', '));
  check('[doors] the 3D page reads ?hall= and ?campus= (existing deep links) and the new ?resto= through startRestorationWalk',
    /params\.get\('hall'\)/.test(P3) && /D\.campuses\[params\.get\('campus'\)\]/.test(P3)
    && /s\.id === params\.get\('resto'\) && s\.e !== undefined/.test(P3) && /if \(restoDeep\) startRestorationWalk\(restoDeep\);/.test(P3));
}
// [doors] each marker: DOM element, 0 draw calls, near the eye only, hidden in the overview
for (const [nm, html] of [['parish', PAR], ['Bay', BAY]]) {
  const blk = between(html, '/* DOOR-LINK BEGIN', '/* DOOR-LINK END */');
  check(`[doors] ${nm}: one DOOR-LINK block`, blk.length > 0 && html.split('/* DOOR-LINK BEGIN').length === 2);
  check(`[doors] ${nm}: markers are DOM links, no mesh, no scene.add (0 draw calls)`, /document\.createElement\('a'\)/.test(blk)
    && !/new THREE\.(Instanced)?Mesh|scene\.add|new THREE\.\w*Geometry/.test(blk) && /calls: 0/.test(blk));
  const r = +(blk.match(/DL_R = (\d+)/) || [, 1e9])[1];
  check(`[doors] ${nm}: markers show only within DL_R <= 80 m of the eye`, r <= 80 && /Math\.hypot\(d\.x - eye\.x, d\.z - eye\.z\) > DL_R/.test(blk), `DL_R ${r}`);
  check(`[doors] ${nm}: hidden in the overview (doorLinkFrame(over) hides on over)`, /function doorLinkFrame\(over\)/.test(blk) && /if \(over \|\| DL\.closed/.test(blk)
    && html.includes('  robotYardFrame(over);   // ROVER-YARD\n  doorLinkFrame(over);   // DOOR-LINK\n'));
  check(`[doors] ${nm}: the click appends from=<world>&at=<x>,<z>,<yaw>&place=<parish name> for the way back`,
    /a\.addEventListener\('click', \(\) => \{ a\.href = dlHref\(d\); \}\);\n  dlKeys\(a\); stage\.appendChild\(a\);/.test(blk) && /'&from=' \+ DL_WORLD \+ '&at=' \+ eye\.x\.toFixed\(1\)/.test(blk) && /'&place=' \+ encodeURIComponent\(p\)/.test(blk));
  check(`[doors] ${nm}: ?at= lands the walker on that point after the start spot, only inside a parish of this world`,
    /teleport\(o\[0\], o\[1\], 0\); \}\ndoorLinkArrive\(\);/.test(html) && /!parishAt\(v\[0\], v\[1\]\)\) \{ DL\.arrived = \{ ok: false/.test(blk));
}
// [doors] the Bay restoration panels (site panel and scenario runner) carry the site's 3D door
{
  const blk = between(BAY, '/* DOOR-LINK BEGIN', '/* DOOR-LINK END */');
  const ids = (blk.match(/for \(const id of \[([^\]]*)\]\) \{\n  const p = document\.getElementById\(id\);/) || [, ''])[1].match(/'[^']+'/g) || [];
  check('[doors] Bay: both restoration panels on the page are watched for the site they show', ids.length === 2 && ids.every((q) => BAY.includes(`id=${q.replace(/'/g, '"')}`))
    && /observe\(p, \{ attributes: true, attributeFilter: \['hidden', 'data-site'\] \}\)/.test(blk));
  check('[doors] Bay: a shown panel gets one labelled "Walk this site in 3D" door for its site, only when that site has a door',
    /const d = !p\.hidden && DL_DOORS\.find\(\(q\) => q\.id === 'resto:' \+ p\.dataset\.site\);/.test(blk) && /for \(const x of p\.querySelectorAll\('\[data-door-panel\]'\)\) x\.remove\(\);/.test(blk)
    && /a\.setAttribute\('aria-label', 'Enter ' \+ d\.name \+ ' \(' \+ DL_KIND\.resto \+ '\)'\);\n  a\.addEventListener\('click', \(\) => \{ a\.href = dlHref\(d\); \}\);/.test(blk) && /\.door-link-in:focus-visible\{outline:3px solid/.test(blk));
}
// [back] the 3D page offers "Back to <world place>" when opened from a world door
{
  const blk = between(P3, '/* DOOR-BACK BEGIN', '/* DOOR-BACK END */');
  check('[back] one DOOR-BACK block, after the view boot and the first sky', blk.length > 0 && P3.indexOf("bootMark('skyDrawn');\n/* DOOR-BACK BEGIN") > 0);
  const w = (blk.match(/const DOOR_WORLDS = (\{[^}]*\})/) || [, '{}'])[1];
  const worlds = Object.fromEntries([...w.matchAll(/(\w+): '([^']+)'/g)].map((m) => [m[1], m[2]]));
  check('[back] the worlds are a closed list and each back target page exists and lands ?at=', Object.keys(worlds).sort().join() === 'bay,parishes'
    && Object.values(worlds).every((f) => existsSync(ROOT + 'web/' + f) && read('web/' + f).includes('doorLinkArrive();')));
  check('[back] the link text is written with textContent, never innerHTML', /a\.textContent = '(\\u2190|\u2190) Back to ' \+ doorBack\.place/.test(blk) && !/innerHTML/.test(blk));
  // run the parser on hostile and good inputs
  const iife = (blk.match(/const doorBack = (\(\(\) => \{[\s\S]*?\}\)\(\));/) || [, null])[1];
  const run = (q) => { const params = new URLSearchParams(q); return new Function('params', 'DOOR_WORLDS', `return ${iife};`)(params, worlds); };
  let r1 = null, r2 = 'x', r3 = 'x', r4 = null;
  try { r1 = run('?hall=solar&from=parishes&at=1601.9,2743.6,0.00&place=Orleans%20Parish'); r2 = run('?from=evil&at=1,2'); r3 = run('?from=bay&at=1,NaN');
    r4 = run('?from=bay&at=5,6&place=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E' + 'x'.repeat(90)); } catch (e) { r1 = null; }
  check('[back] parser: a world door link gives "Back to Orleans Parish" -> trade_craft_parishes.html?at=1601.9,2743.6,0', r1 && r1.place === 'Orleans Parish' && r1.href === 'trade_craft_parishes.html?at=1601.9,2743.6,0');
  check('[back] parser: an unknown world or a non-finite point gives no back link', r2 === null && r3 === null);
  check('[back] parser: markup characters are stripped and the place is capped at 60 characters', r4 && !/[<>=]/.test(r4.place) && r4.place.length <= 60);
}
// [robot-yard] the robot yard has no 3D interior in the registry; its door stays its existing arena link
{
  const pages = RB.envs['world.litter-pickup'].world.pages;
  check('[robot-yard] robotics.json lists no 3D page for world.litter-pickup (so no 3D door is invented)', !pages.includes('web/trade_craft_3d.html') && pages.includes('web/trade_craft_robotics.html'));
  for (const [nm, html] of [['parish', PAR], ['Bay', BAY]])
    check(`[robot-yard] ${nm}: the yard link gets a label and keyboard handling, its href unchanged`, /ryLab\.href = 'trade_craft_robotics\.html#model-arena'/.test(html)
      && /querySelector\('\[data-robot-yard\]'\)[\s\S]{0,80}setAttribute\('aria-label', 'Robot yard: /.test(html) && /dlKeys\(y\)/.test(html));
}
// [keys] keyboard and screen-reader access: labels, a visible focus ring, Enter/Space, Esc; skip links still work
for (const [nm, html] of [['parish', PAR], ['Bay', BAY]]) {
  const blk = between(html, '/* DOOR-LINK BEGIN', '/* DOOR-LINK END */');
  check(`[keys] ${nm}: each door has an accessible name "Enter <place> (<kind>)"`, /a\.setAttribute\('aria-label', 'Enter ' \+ d\.name \+ ' \(' \+ DL_KIND\[d\.kind\] \+ '\)'\)/.test(blk)
    && /hall: 'union hall · 3D interior', campus: 'campus · 3D view', resto: 'restoration site · 3D walk'/.test(blk));
  check(`[keys] ${nm}: a visible focus ring (3px outline on :focus-visible)`, /\.door-link:focus-visible,\[data-robot-yard\]:focus-visible\{outline:3px solid #ffd54a/.test(blk));
  check(`[keys] ${nm}: Space opens a focused door (Enter is the link's own), and the walker keys do not see either`,
    /if \(e\.key === ' ' \|\| e\.key === 'Spacebar'\) \{ e\.preventDefault\(\); e\.stopPropagation\(\); el\.click\(\); \}/.test(blk) && /else if \(e\.key === 'Enter'\) \{ e\.stopPropagation\(\); \}/.test(blk));
  check(`[keys] ${nm}: Esc closes the doors and returns focus to the 3D view`, /else if \(e\.key === 'Escape'\) \{ e\.preventDefault\(\); e\.stopPropagation\(\); dlClose\(el\); \}/.test(blk)
    && /function dlClose\(el\) \{[\s\S]*?for \(const a of DL\.els\) a\.hidden = true;[\s\S]*?c\.focus\(\);/.test(blk));
  check(`[keys] ${nm}: a hidden door is out of the Tab order (hidden attribute), a focused one is never hidden off-screen`, /a\.hidden = true; a\.dataset\.door/.test(blk) && /if \(off && f !== a\)/.test(blk));
}
{
  const blk = between(P3, '/* DOOR-BACK BEGIN', '/* DOOR-BACK END */');
  check('[keys] 3D: the back link has a visible focus ring and a 44 px target, and Space opens it', /\.door-back:focus-visible\{outline:3px solid #ffd54a/.test(blk) && /min-block-size:44px/.test(blk)
    && /if \(e\.key === ' '\) \{ e\.preventDefault\(\); a\.click\(\); \}/.test(blk));
}
for (const [nm, html] of [['parish', PAR], ['Bay', BAY], ['3D', P3]])
  check(`[keys] ${nm}: the skip link still targets the main landmark`, (html.match(/<a class="skip" href="#tc-main">/g) || []).length === 1 && (html.match(/id="tc-main"/g) || []).length === 1);
// [xlink] K-12 program cards -> the world places they name (each re-derived from layers / paths / wilds and asserted to exist)
{
  const PG = read('web/trade_craft_programs.html'), PRG = reg('programs/registry/programs.json');
  const LAY = Object.fromEntries(reg('layers/registry/layers.json').parishes.map((p) => [p.fips, Object.fromEntries(p.stations.map((s) => [s.id, s]))]));
  const PTH = Object.fromEntries(reg('layers/registry/paths.json').parishes.map((p) => [p.fips, p.paths]));
  const WLD = Object.fromEntries(reg('wilds/registry/wilds.json').worlds.map((w) => [w.id, new Set(w.sites.map((s) => s.id))]));
  const parFips = new Set(pageJson(PAR, 'parishes-data').parishes.map((p) => p.id));
  const want = new Map(), bad = [];
  for (const c of PRG.cards) for (const w of c.where) {
    const [kind, rest] = [w.id.slice(0, w.id.indexOf(':')), w.id.slice(w.id.indexOf(':') + 1)];
    if (kind === 'parish' || kind === 'k12') {
      let [fips, tail] = rest.split('/');
      if (kind === 'k12') { const k = (PTH[fips] || []).find((p) => p.id === 'k12'); tail = k && k.steps[+tail - 1] ? k.steps[+tail - 1].id : null; }
      const st = LAY[fips] && LAY[fips][tail];
      if (!st || !parFips.has(fips)) { bad.push(w.id); continue; }
      want.set(w.id, `trade_craft_parishes.html?at=${st.world_m[0].toFixed(1)},${(-st.world_m[1] + 6).toFixed(1)},0`);
    } else if (kind === 'wilds') {
      const [wid, sid] = rest.split('/');
      if (!WLD[wid] || !WLD[wid].has(sid)) { bad.push(w.id); continue; }
      want.set(w.id, `trade_craft_wilds.html#${wid}/${sid}`);
    }
  }
  const got = [...PG.matchAll(/data-world-place="([^"]+)" href="([^"]+)"/g)].map((m) => [m[1], m[2].replace(/&amp;/g, '&')]);
  check('[xlink] every K-12 card parish station, K-12 path step and wilds site resolves in the registries', bad.length === 0 && want.size > 0, bad.slice(0, 3).join(', '));
  const nPlaces = PRG.cards.reduce((n, c) => n + c.where.filter((w) => /^(parish|k12|wilds):/.test(w.id)).length, 0);
  check('[xlink] programs: one "go" link per named world place on the cards', got.length === nPlaces && nPlaces > 0, `links ${got.length}, places ${nPlaces}`);
  const wrong = got.filter(([id, h]) => want.get(id) !== h);
  check('[xlink] programs: each go link lands on its place (parish ?at= 6 m from the kiosk, wilds #<world>/<site>)', wrong.length === 0, wrong.slice(0, 2).map((x) => x.join(' -> ')).join('; '));
  check('[xlink] programs: the target pages read the link (parish doorLinkArrive, wilds fromHash/goSite)', PAR.includes('doorLinkArrive();') && /async function fromHash\(\)[\s\S]{0,200}goSite\(sid\)/.test(read('web/trade_craft_wilds.html')));
  check('[xlink] programs: go links carry an accessible name', (PG.match(/class="go-place" data-world-place="[^"]+" href="[^"]+" lang="en" dir="ltr" aria-label="Go to [^"]+ in the world"/g) || []).length === got.length);
}
// [xlink] union directory cards -> the hall's door in the walkable world
{
  const UP = read('web/trade_craft_unions.html');
  const doors = new Map((DLP ? DLP.doors : []).filter((d) => d.kind === 'hall').map((d) => [d.id.slice(5), d]));
  const facing = new Map(); for (const c of Object.values(CP.campuses)) if (c.placement.parish) for (const l of c.lots) facing.set(l.hall, l.building.facing);
  const cards = [...UP.matchAll(/<article class="uh" id="hall-([a-z0-9-]+)"[\s\S]*?<\/article>/g)].map((m) => [m[1], m[0]]);
  const links = cards.map(([h, c]) => [h, [...c.matchAll(/data-link="world-door" href="([^"]+)"/g)].map((m) => m[1])]);
  const extra = links.filter(([h, l]) => !doors.has(h) && l.length), missing = links.filter(([h, l]) => doors.has(h) && l.length !== 1);
  check('[xlink] unions: every hall with a world door has exactly one world-door link, and no other hall has one', cards.length === UN.unions.length && doors.size > 0 && !extra.length && !missing.length,
    `extra ${extra.map((x) => x[0])}, missing ${missing.map((x) => x[0])}`);
  const off = links.filter(([h, l]) => l.length).filter(([h, [href]]) => {
    const d = doors.get(h), n = facing.get(h) === 'N';
    return href !== `trade_craft_parishes.html?at=${d.x.toFixed(1)},${(n ? d.z - 8 : d.z + 8).toFixed(1)},${n ? 3.14 : 0}`;
  });
  check('[xlink] unions: each world-door link stands the walker 8 m in front of that hall\'s door marker on the parish page, facing it', off.length === 0, off.slice(0, 2).map((x) => x[0]).join(', '));
}
// [xlink] restoration panels -> their scenario runner
{
  const SC = reg('restoration/registry/scenarios.json');
  const run = Object.fromEntries(SC.staged_tasks.filter((t) => t.place.kind === 'restoration-site' && t.launch.href).map((t) => [t.place.id, t.launch.href.slice(4)]));
  const m = P3.match(/function restoRunLink\(id\) \{[^\n]*\n  const R = (\{[^\n]*\});/);
  const R = m ? JSON.parse(m[1]) : {};
  check('[xlink] 3D Bay Restoration panel: each site row links its scenario runner (scenarios.json staged task launch)', JSON.stringify(R) === JSON.stringify(Object.fromEntries(Object.entries(run).sort()))
    && Object.keys(R).length > 0 && P3.includes('${walk}${real}${facts}${restoRunLink(s.id)}</li>`;'));
  const gone = Object.keys(R).filter((id) => R[id] !== `trade_craft_bay.html#resto=${id}` || !BAY.includes(`data-resto-run="${id}"`));
  check('[xlink] every runner link target exists: a Bay run button per site and the #resto= opener', gone.length === 0 && /if \(h\.startsWith\('resto='\)\) addEventListener\('load', \(\) => openSite\(h\.slice\(6\), null\)\)/.test(BAY), gone.join(', '));
  check('[xlink] Bay site panel: a site with a runner carries the run button that opens it in place', /\$\{s\.runner \? `<div class="rs-row"><button type="button" data-resto-run="\$\{esc\(s\.id\)\}">/.test(BAY));
}
// [markers] neutral page markers only
for (const [nm, html] of [['parish', PAR], ['Bay', BAY], ['3D', P3], ['unions', read('web/trade_craft_unions.html')], ['programs', read('web/trade_craft_programs.html')]])
  check(`[markers] ${nm} page carries no team codename for this work`, !/\bACCESS\b/.test(html));

console.log(fails ? `test_access: ${fails} FAIL, ${oks} ok` : `test_access: ${oks} ok`);
process.exit(fails ? 1 : 0);
