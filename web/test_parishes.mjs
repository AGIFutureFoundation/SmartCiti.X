/**
 * Static checks for the parish world page (web/trade_craft_parishes.html,
 * built by web/build_parishes.py). Prints `  ok ` per check and `FAIL` at
 * column 0; exits non-zero on any failure. The browser behaviour (streaming,
 * border crossing, vehicles on their medium, satellite toggle) is held by
 * web/eval_parishes.mjs.
 */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';

const ROOT = new URL('..', import.meta.url).pathname;
const read = (p) => readFileSync(ROOT + p, 'utf8');
let fails = 0, oks = 0;
function check(name, cond, why = '') {
  if (cond) { oks++; console.log(`  ok ${name}`); } else { fails++; console.log(`FAIL ${name}${why ? ' :: ' + why : ''}`); }
}
const PAGE = 'web/trade_craft_parishes.html';
const html = read(PAGE);
const json = (id) => { const m = html.match(new RegExp(`<script type="application/json" id="${id}">([\\s\\S]*?)</script>`)); return m ? JSON.parse(m[1]) : null; };
const D = json('parishes-data');
const CAT = json('parishes-i18n');
const REG = JSON.parse(read('parishes/registry/parishes.json'));
const main = (html.match(/<script type="module" id="parishes-main">([\s\S]*?)<\/script>/) || [, ''])[1];

// [page] chrome the team rules require
check('[page] exactly one <h1>', (html.match(/<h1[\s>]/g) || []).length === 1);
check('[page] brand icon link', /<link rel="icon" href="data:image\/svg\+xml,/.test(html));
check('[page] site nav present once, right after <body>', (html.match(/<nav[\s>]/g) || []).length >= 1 && /<body class="tc-theme-canvas">\s*<(nav|a|header)/.test(html));
check('[page] skip target #tc-main', html.includes('id="tc-main"'));
check('[page] meta description', /<meta name="description" content="[^"]{40,160}">/.test(html));
check('[page] style switcher remembered (STYLE_HEAD_JS before first <style>, STYLE_JS after main)',
  html.indexOf("localStorage.getItem('tc-style')") > -1 && html.indexOf("localStorage.getItem('tc-style')") < html.indexOf('<style') && html.lastIndexOf('tc-style') > html.indexOf('id="parishes-main"'));
check('[page] generated file (no model identifiers)', !/claude|gpt-\d|opus|sonnet/i.test(html));

// [theme] UI colours only from tokens
const ownStyle = (html.match(/<style>([\s\S]*?)<\/style>/) || [, ''])[1];
check('[theme] canvas theme layer', html.includes('<body class="tc-theme-canvas">') && html.includes('data-tc-theme="canvas"'));
check('[theme] page style has no hex/rgb literal (tokens only)', !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(ownStyle), (ownStyle.match(/#[0-9a-fA-F]{3,8}\b|rgba?\(/g) || []).join(' '));
check('[theme] minimap colours read from --tc-* tokens', /tok\('--tc-/.test(main) && !/mctx\.(fill|stroke)Style = '#/.test(main));

// [core] the wilds terrain core carried byte-for-byte
const core = read('wilds/core.mjs');
const CB = core.slice(core.indexOf('/* WILDS_CORE:BEGIN */'), core.indexOf('/* WILDS_CORE:END */') + '/* WILDS_CORE:END */'.length);
check('[core] WILDS_CORE block identical to wilds/core.mjs', CB.length > 100 && main.includes(CB));
check('[core] fabric scattered by wildsHash', /wildsHash\(ix, iz, SEED, 1\)/.test(main));

// [data] the PARISH contract, read not retyped
check('[data] embedded registry present', D !== null && Array.isArray(D.parishes));
check('[data] parishes = registry selection.selected, in order', JSON.stringify(D.parishes.map((p) => p.id)) === JSON.stringify(REG.selection.selected));
check('[data] source stamp matches the registry', D.source_stamp === REG.source_stamp && html.includes(`data-stamp>${REG.source_stamp}<`));
const pairs = new Set(); for (const p of D.parishes) for (const n of p.neighbours) pairs.add([p.id, n.id].sort().join('|'));
check('[data] shared borders = registry adjacency_pairs', pairs.size === REG.counts.adjacency_pairs, `${pairs.size} vs ${REG.counts.adjacency_pairs}`);
check('[data] every border is symmetric', D.parishes.every((p) => p.neighbours.every((n) => D.parishes.find((q) => q.id === n.id).neighbours.some((m) => m.id === p.id))));
const nLm = Object.values(REG.parishes).reduce((a, p) => a + p.landmarks.length + p.anchors.length, 0);
check('[data] every landmark and anchor placed, none invented', D.parishes.reduce((a, p) => a + p.landmarks.length, 0) === nLm, `${nLm}`);
check('[data] every landmark carries provenance + note and a generic family',
  D.parishes.every((p) => p.landmarks.every((l) => l.provenance && l.note && ['tower', 'dome', 'hall', 'bridge', 'other'].includes(l.family))));
check('[data] landmark world x/z = registry world_m (x = east, z = -north)',
  Object.values(REG.parishes).every((rp) => rp.landmarks.every((l, j) => { const q = D.parishes.find((p) => p.id === rp.fips).landmarks[j]; return q.x === l.world_m[0] && q.z === -l.world_m[1]; })));
check('[data] shared border points coincide in the world frame',
  D.parishes.every((p) => p.neighbours.every((n) => n.segments.every((sg) => sg.every(([x, z], i) => { const w = REG.parishes[p.id].borders.find((b) => b.with === n.id); return w.segments.some((s) => s.world_m.some(([e, nn]) => e === x && -nn === z)); })))));
check('[data] each parish carries its 4k map + preview path, label and fabric note',
  D.parishes.every((p) => p.map_4k === REG.parishes[p.id].map.path && p.map_preview === REG.parishes[p.id].map.preview && existsSync(ROOT + p.map_preview) && p.map_label.includes('not satellite')));

// [honesty] ground, satellite, play
check('[honesty] panel says no real elevation', /data-no-elevation><span data-i18n="parishes.no_elevation">[^<]*no real elevation/.test(html));
check('[honesty] registry water + outline + landmark statements shown', ['water', 'outline', 'landmarks', 'elevation', 'satellite'].every((k) => html.includes(`data-honesty-key="${k}"`)));
check('[honesty] flat ground at 0 m forced in the page', /pa\[i\] = 0/.test(main) && /water\.position\.y = -0\.4/.test(main));
check('[honesty] Mapbox refusal text verbatim from the registry', D.satellite.mapbox.refusal_text === 'Mapbox satellite: off - no token configured' && /SAT\.mapbox\.refusal_text/.test(main));
check('[honesty] Mapbox token only from ./config/runtime.json, public pk. only, read on toggle', /fetch\('\.\/config\/runtime\.json'/.test(main) && /startsWith\('pk\.'\)/.test(main) && !/readToken\(\);\s*$/m.test(main.split('async function showSatellite')[0]));
check('[honesty] no token and no baked imagery in the page', !/access_token=pk\.|"pk\.[A-Za-z0-9]/.test(html) && !/data:image\/(jpeg|png|webp)/.test(html));
check('[honesty] satellite requested only in the browser (USGS tile template from the registry)', D.satellite.usgs.tiles === REG.satellite.usgs.tiles && REG.satellite.fetched_at_build === false && REG.satellite.stored === false);
check('[honesty] quests are play, said once', (html.match(/data-i18n="parishes.play_note"/g) || []).length === 1);
check('[honesty] fleet honesty shown', html.includes('data-fleet-honesty>') && !html.includes('data-fleet-honesty></li>'));

// [perf] one InstancedMesh per asset family; chunk budgets declared once
check('[perf] fabric families are InstancedMesh (blocks, trees)', /new THREE\.InstancedMesh\(blockGeo/.test(main) && /new THREE\.InstancedMesh\(treeGeo/.test(main));
check('[perf] landmark families and border markers are InstancedMesh', /new THREE\.InstancedMesh\(f\(\), matLm, CAP\.lm\)/.test(main) && /new THREE\.InstancedMesh\(markerGeo/.test(main));
check('[perf] chunk budget declared once', (main.match(/const CHUNK_M = 250, RADIUS = 3, CELL = 25, BUILD_PER_FRAME = 3;/g) || []).length === 1 && /const CAP = \{ block: 6000, tree: 4000, marker: 64, lm: 64 \}/.test(main));

// [fleet] FLEET contract
const FL = json('fleet-registry');
if (existsSync(ROOT + 'fleet/registry/fleet.json')) {
  const reg = JSON.parse(read('fleet/registry/fleet.json'));
  check('[fleet] fleet.json embedded verbatim', JSON.stringify(FL) === JSON.stringify(reg));
  check('[fleet] kit inlined between its markers', main.includes('/* FLEET_KIT:BEGIN') && main.includes('/* FLEET_KIT:END */'));
  check('[fleet] water test for boats = outside every land outline', /fleetFlatGround\(0, 0, \(x, z\) => parishAt\(x, z\) === null\)/.test(main));
  check('[fleet] enter/exit via fleetNearest(…, 2.5) and fleetExitPoint', /fleetNearest\(\{ x: eye\.x, z: eye\.z \}, parked, 2\.5\)/.test(main) && /fleetExitPoint\(riding\.st/.test(main));
} else check('[fleet] stub named when fleet registry absent', html.includes('data-contract="fleet" data-state="stub"'));

// [layers] LAYERS contract: stations from pathkit, kiosk family instanced, chooser mounted per parish
if (existsSync(ROOT + 'layers/registry/layers.json')) {
  const P = json('parish-paths');
  check('[layers] path data embedded for every parish', P && D.parishes.every((p) => P[p.id] && Array.isArray(P[p.id].stations) && P[p.id].paths.length === 3));
  check('[layers] stations are one InstancedMesh (kiosk family)', /new THREE\.InstancedMesh\(stationGeo, matMark, 256\)/.test(main));
  check('[layers] stations placed at registry world_m (x = east, z = -north)', /const x = st\.world_m\[0\], z = -st\.world_m\[1\];/.test(main));
  check('[layers] pathkit script after the quest script', html.indexOf("PSTORE = 'tc-path'") > html.indexOf('<script data-tc-quests>') && html.indexOf('<script data-tc-quests>') > html.indexOf('id="parishes-main"'));
}

// [npcs] NPC contract: every NPC of every parish, lines verbatim with sources, kit inlined
const NR = existsSync(ROOT + 'npcs/registry/npcs.json') ? JSON.parse(read('npcs/registry/npcs.json')) : null;
if (NR && NR.places_status === 'PARISH+LAYERS') {
  const N = json('parish-npcs');
  check('[npcs] every registry NPC embedded, none added', N && N.npcs.length === NR.npcs.length && N.npcs.every((n) => NR.npcs.some((m) => m.id === n.id)));
  check('[npcs] every knowledge line verbatim from the registry with a source',
    N && N.npcs.every((n) => { const m = NR.npcs.find((q) => q.id === n.id); return n.knowledge.length === m.knowledge.length && n.knowledge.every((k, i) => k.text === m.knowledge[i].text && k.source === m.knowledge[i].source && k.text && k.source); }));
  check('[npcs] honesty passed as the registry object (the kit renders honesty.scripted)', N && typeof N.honesty === 'object' && N.honesty.scripted === NR.honesty.scripted);
  check('[npcs] every NPC home resolves to a placed coordinate', N && N.npcs.every((n) => Object.hasOwn(N.places, n.home.place)));
  check('[npcs] kit inlined and dialogue labels all from parishes.npc.* keys', main.includes('function createNPCKit') && /takeMeThere: tr\('parishes\.npc\.take'\)/.test(main));
}

// [contracts] stubs are named
for (const k of ['fleet', 'npcs', 'layers']) {
  const m = html.match(new RegExp(`<li data-contract="${k}" data-state="(wired|stub)">([\\s\\S]*?)</li>`));
  check(`[contracts] ${k} row states wired or names what is missing`, !!m && (m[1] === 'wired' || /data-why>[^<]{10,}/.test(m[2])));
}

// [i18n] the run-time catalogue: 8 locales, exactly the used keys, real translations
const locs = ['ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'zh'];
check('[i18n] catalogue carries the 8 locales', CAT && JSON.stringify(Object.keys(CAT).sort()) === JSON.stringify(locs));
const used = new Set([...html.matchAll(/data-i18n(?:-aria)?="(parishes\.[a-z0-9_.]+)"/g)].map((m) => m[1]));
for (const m of main.matchAll(/tr\('(parishes\.[a-z0-9_.]+)'\)/g)) used.add(m[1]);
check('[i18n] every key the page uses is in the catalogue, and only those', CAT && JSON.stringify([...used].sort()) === JSON.stringify(Object.keys(CAT.en.strings).sort()),
  CAT ? [...used].filter((k) => !(k in CAT.en.strings)).concat(Object.keys(CAT.en.strings).filter((k) => !used.has(k))).join(',') : '');
let same = [];
for (const l of locs) {
  const f = JSON.parse(read(`i18n/locales/${l}.json`));
  for (const k of Object.keys(CAT.en.strings)) {
    if (CAT[l].strings[k] !== f.strings[k]) same.push(`${l}:${k} differs from locale file`);
    if (l !== 'en' && f.strings[k] === JSON.parse(read('i18n/locales/en.json')).strings[k]) same.push(`${l}:${k} is an English copy`);
  }
}
check('[i18n] catalogue = locale files, no English copies', same.length === 0, same.slice(0, 4).join('; '));
check('[i18n] tr() throws by name (no fallback)', /throw new Error\(`parishes i18n: locale \$\{LOC\} has no \$\{k\}`\)/.test(main));

// [build] the page is what the builder writes today
const sha = createHash('sha256').update(html).digest('hex').slice(0, 16);
check('[build] page carries the builder banner and one importmap', (html.match(/<script type="importmap">/g) || []).length === 1);
console.log(fails ? `test_parishes: ${fails} FAIL, ${oks} ok (page ${sha})` : `test_parishes: ${oks} ok (page ${sha})`);
process.exit(fails ? 1 : 0);
