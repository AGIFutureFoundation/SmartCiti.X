/* web/test_bayworld.mjs — the walkable Bay world page (web/trade_craft_bay.html), checked without a browser.
 * The page is the parish page machinery with the Bay registries swapped in by web/build_bayworld.py; these checks
 * pin what the swap must change (and what it must not claim). Browser metrics live in web/eval_bayworld.mjs. */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const PAGE = 'web/trade_craft_bay.html';
console.log('web/test_bayworld.mjs');
ok(existsSync(join(ROOT, PAGE)), '[page] web/trade_craft_bay.html exists');
if (!existsSync(join(ROOT, PAGE))) { console.log(`\n${pass} ok, ${fail} FAIL`); process.exit(1); }
const html = readFileSync(join(ROOT, PAGE), 'utf8');
const R = JSON.parse(readFileSync(join(ROOT, 'bayarea/registry/bayarea.json'), 'utf8'));
const EN = JSON.parse(readFileSync(join(ROOT, 'i18n/locales/en.json'), 'utf8')).strings;
const chk = spawnSync('python3', [join(ROOT, 'web/build_bayworld.py'), '--check'], { encoding: 'utf8', cwd: ROOT });
ok(chk.status === 0, '[page] the page is current (python3 web/build_bayworld.py --check)');
const vis = html.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<style[\s\S]*?<\/style>/g, '');
ok((vis.match(/<h1[\s>]/g) || []).length === 1 && vis.includes(`data-i18n="bay.title"`) && vis.includes(EN['bay.title']),
  '[page] one <h1>, carrying the bay.title key (not the parish title)');
ok(/<title>[^<]*Bay Area counties[^<]*<\/title>/.test(html) && !/<title>[^<]*parishes/.test(html),
  '[page] the document title names the Bay Area counties');
ok(html.includes(`data-stamp>${R.source_stamp}<`) && html.includes('bayarea/registry/bayarea.json'),
  `[page] the footer cites bayarea/registry/bayarea.json at stamp ${R.source_stamp}`);
ok(/not official neighbourhoods/.test(vis) && /Treasure Island/.test(vis),
  '[honesty] the page says the districts are AUTHORED, not official neighbourhoods, and that the Treasure Island campus is not placed');
ok(/data-contract="npcs" data-state="stub"/.test(html) && /data-contract="layers" data-state="stub"/.test(html)
   && /New Orleans parishes only/.test(vis),
  '[kits] kits whose registries hold no Bay county (NPC guides, learning-path layers) show as stub with that reason');
ok(!/New Orleans/.test(vis.replace(/<nav[\s\S]*?<\/nav>/g, '').replace(/[^.]*New Orleans parishes only[^.]*/g, '')),
  '[honesty] outside the nav and the stub reasons, the page never names New Orleans');
{
  /* browser run 1 (02:24) died on "parishes i18n: locale en has no parishes.canvas_label": the script looks chrome keys
     up by their parish names, so every key literal in the page script must resolve in every embedded locale */
  const m = html.match(/<script type="application\/json" id="parishes-i18n">([\s\S]*?)<\/script>/);
  const cat = m ? JSON.parse(m[1].replace(/<\\\//g, '</')) : {};
  const mods = [...html.matchAll(/<script type="module"[^>]*>([\s\S]*?)<\/script>/g)].map((x) => x[1]).join('\n');
  const keys = [...new Set([...mods.matchAll(/['"]((?:parishes|bay)\.[a-z0-9_.]+[a-z0-9_])['"]/g)].map((x) => x[1])
    .concat([...html.matchAll(/data-i18n(?:-[a-z]+)?="((?:parishes|bay)\.[a-z0-9_.]+)"/g)].map((x) => x[1])))];
  const miss = [];
  for (const [loc, c] of Object.entries(cat)) for (const k of keys) if (typeof c.strings[k] !== 'string' || !c.strings[k].trim()) miss.push(loc + ':' + k);
  ok(Object.keys(cat).length === 8 && keys.length > 0 && miss.length === 0,
    `[i18n] every one of the ${keys.length} chrome keys the page script and data-i18n attributes name resolves in all 8 embedded locales${miss.length ? ' [' + miss.slice(0, 4).join('; ') + ']' : ''}`);
  ok(cat.en && cat.en.strings['parishes.title'] === EN['bay.title'],
    '[i18n] the parish-named title key carries the Bay title text at runtime');
}
{
  const placed = Object.values(R.counties).flatMap((c) => c.restoration_sites);
  const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const miss = placed.filter((x) => !html.includes(JSON.stringify(x.name).slice(1, -1)) && !html.includes(esc(x.name)));
  ok(placed.length > 0 && miss.length === 0, `[restoration] all ${placed.length} placed restoration sites stand in the world as pins at their recorded coordinates${miss.length ? ' [missing ' + miss.map((x) => x.id).join(', ') + ']' : ''}`);
}
{
  const U = existsSync(join(ROOT, 'underwater/registry/underwater.json')) ? JSON.parse(readFileSync(join(ROOT, 'underwater/registry/underwater.json'), 'utf8')) : null;
  ok(!U || (/DEEP_WORLD = 'bay'/.test(html) && !/DEEP_WORLD = 'parishes'/.test(html) && U.bodies.some((b) => b.world === 'bay')),
    `[deep] DEEP's underwater kit on this page draws the Bay bodies (DEEP_WORLD 'bay', ${U ? U.bodies.filter((b) => b.world === 'bay').length : 0} bodies), never the parish waters`);
}
{
  const mods = [...html.matchAll(/<script type="module"[^>]*>([\s\S]*?)<\/script>/g)].map((x) => x[1]).join('\n');
  const kitOn = /function makeClock\(/.test(mods);
  ok(kitOn || !/(?<!\? )makeClock\(8/.test(mods),
    '[npcstub] with the NPC kit off, the page never calls npckit makeClock unguarded (browser run 02:44 died on "makeClock is not defined")');
}
{
  /* WORLDS (wave 10): restoration sites outside every coarse outline are pinned only when their own record says pin:true */
  const RS = JSON.parse(readFileSync(join(ROOT, 'restoration/registry/restoration.json'), 'utf8')).sites;
  const D = JSON.parse((html.match(/<script type="application\/json" id="parishes-data">([\s\S]*?)<\/script>/) || [, 'null'])[1].replace(/<\\\//g, '</'));
  const off = D ? D.parishes.flatMap((p) => p.landmarks.filter((l) => l.kind === 'restoration site (offshore pin)').map((l) => ({ ...l, county: R.counties[p.id].name }))) : [];
  const want = R.restoration_not_placed.filter((x) => { const s = RS.find((r) => r.id === x.id); return s && s.lat !== null && s.pin === true; });
  ok(D && off.length === want.length && want.every((x) => { const s = RS.find((r) => r.id === x.id); const l = off.find((o) => o.name === x.name);
    return l && l.provenance === 'RECORDED' && l.x === x.world_m[0] && l.z === -x.world_m[1] && l.county === s.county && l.note.endsWith('not walkable: ' + s.walkable_reason); })
    && !off.some((l) => html.includes(`<li data-landmark="${l.id}"><button`)) && RS.filter((s) => s.lat === null).every((s) => !off.some((l) => l.name === s.name)),
    `[offshore] ${want.length} restoration site(s) outside every coarse outline pinned at the RECORDED point in the county their record names, with the record's not-walkable reason, no scenario runner; unpinned sites (no point) stay unpinned`);
}
const ids = [...html.matchAll(/"fips": ?"(\d{5})"/g)].map((m) => m[1]);
ok(R.selection.selected.every((f) => ids.includes(f)) && !ids.some((f) => f.startsWith('22')),
  `[data] the embedded world holds exactly the computed Bay counties (${R.selection.selected.join(' ')}) and no parish`);
ok(!/(?:fetch\(\s*|src\s*=\s*|\bfrom\s+|import\(\s*|new URL\(\s*)['"`]https?:\/\/(?!basemap\.nationalmap\.gov|api\.mapbox\.com)/i.test(html),
  '[nofetch] nothing is loaded (fetch/src/import/URL) from an absolute host except the declared view-time imagery hosts; licence links are text, not loads');
{
  /* RESTORE (wave 9): restoration training scenarios mounted at the placed restoration-site landmarks (web/restokit.py) */
  const SC = JSON.parse(readFileSync(join(ROOT, 'restoration/registry/scenarios.json'), 'utf8'));
  const placed = Object.values(R.counties).flatMap((c) => c.restoration_sites.map((x) => x.id));
  const dm = html.match(/<script type="application\/json" id="resto-data">([\s\S]*?)<\/script>/);
  const RD = dm ? JSON.parse(dm[1].replace(/<\\\//g, '</')) : { lm: {}, sc: {} };
  const runs = [...html.matchAll(/data-resto-run="([a-z0-9-]+)"/g)].map((x) => x[1]);
  ok(placed.length === 9 && placed.every((id) => runs.filter((r) => r === id).length === 1) && runs.length === placed.length
    && JSON.stringify(Object.values(RD.lm).sort()) === JSON.stringify([...placed].sort())
    && Object.keys(RD.lm).every((lid) => html.includes(`<li data-landmark="${lid}"><button type="button" class="rk-open" data-resto-run="${RD.lm[lid]}">`)),
    `[resto] each of the ${placed.length} placed restoration-site landmarks carries exactly one "Run training scenario" action, and its in-world marker id maps to that site`);
  const want = (id) => SC.scenarios.filter((s) => s.site === id).map((s) => s.id);
  ok(placed.every((id) => JSON.stringify((RD.sc[id] || []).map((s) => s.id)) === JSON.stringify(want(id)) && want(id).length > 0)
    && Object.values(RD.sc).flat().every((s) => s.label === "training scenario, not the project's actual work plan" && s.lessons === 'unverified general practice'),
    '[resto] each site opens exactly its own scenarios from restoration/registry/scenarios.json, labelled training scenario / unverified general practice');
  const cm = html.match(/<script type="application\/json" id="parishes-i18n">([\s\S]*?)<\/script>/);
  const cat = cm ? JSON.parse(cm[1].replace(/<\\\//g, '</')) : {};
  const keys = ['title', 'play', 'open', 'close', 'run', 'score', 'pass', 'fail', 'gates', 'forbidden'].map((k) => 'resto.' + k);
  ok(Object.keys(cat).length === 8 && Object.values(cat).every((c) => keys.every((k) => typeof c.strings[k] === 'string' && c.strings[k].length > 0))
    && html.includes('id="resto-sims"') && html.includes("if (h.startsWith('resto=')) addEventListener('load', () => openSite(h.slice(6), null));"),
    '[resto] the scenario panel, the #resto=<site> reader and its resto.* labels in all 8 embedded locales are on the page');
  const rs = (html.match(/<script>\s*function rkLis[\s\S]*?<\/script>/) || [''])[0];
  ok(rs.length > 0 && !/localStorage|sessionStorage|indexedDB|fetch\(|XMLHttpRequest/.test(rs),
    '[resto] the scenario runner stores nothing and fetches nothing (a run is play, never a completion record)');
}
/* WORLDS w11: the Bay page drapes ONE 2048 px atlas per county (parishes/build_atlas.py), never the 16 tiles */
{
  const AT = JSON.parse(readFileSync(join(ROOT, 'parishes/registry/ground_atlas.json'), 'utf8')).atlases;
  const want = Object.keys(R.counties).map((id) => AT['bayarea/maps/tiles/' + id]);
  ok(want.every((a) => a && html.includes(`"atlas": "${a.path}"`) && existsSync(join(ROOT, a.path))) && !/bayarea\/maps\/tiles\/\d+-r\d+c\d+\.webp/.test(html),
    `[atlas] the Bay page names ${want.length} county ground atlases (files present) and no per-tile path`);
}

console.log(`\n${pass} ok, ${fail} FAIL`);
process.exit(fail ? 1 : 0);
