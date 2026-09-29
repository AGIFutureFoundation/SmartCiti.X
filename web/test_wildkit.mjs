#!/usr/bin/env node
/* web/test_wildkit.mjs - the wildlife kit's pure core (WILD-CORE) run in node, plus its Python side, fail-closed.
   Prints "  ok " per check, FAIL at column 0, exits non-zero on failure. */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let fails = 0;
function ok(name, cond, detail) {
  if (cond) { console.log('  ok ' + name); return; }
  fails++; console.log('FAIL ' + name);
  for (const d of [].concat(detail || []).slice(0, 8)) console.log('     ' + d);
}
const py = (args) => { try { return { out: execFileSync('python3', args, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }), code: 0 }; } catch (e) { return { out: String(e.stdout || '') + String(e.stderr || ''), code: e.status }; } };
const JS = py(['web/wildkit.py', '--emit']).out;
const core = JS.slice(JS.indexOf('/* WILD-CORE:BEGIN'), JS.indexOf('/* WILD-CORE:END */'));
ok('WILD-CORE is marked and pure (no DOM, storage or network inside it)', core.length > 500 && !/document\.|localStorage|fetch\(|XMLHttpRequest|window\./.test(core.replace(/\/\*[\s\S]*?\*\//g, '')));
const C = new Function(core + '\nreturn { wildRng, wildCellSpawns, wildNearby, wildJudge, wildBearing, wildGatorMode, wildInWindow, wildHabitatOk, wildParse };')();
const D = JSON.parse(py(['web/wildkit.py', '--data', 'parishes']).out);
const B = JSON.parse(py(['web/wildkit.py', '--data', 'bay']).out);

// an AUTHORED test map: water where x < 0, ground elsewhere up to 2 km
const isWater = (x, z) => x < 0 && Math.abs(z) < 2000 && x > -2000;
const isGround = (x, z) => x >= 0 && x < 2000 && Math.abs(z) < 2000;
const a = C.wildNearby(D, 7, 10, 10, 6, null, isWater, isGround, new Map());
const b = C.wildNearby(D, 7, 10, 10, 6, null, isWater, isGround, new Map());
ok(`spawns are deterministic from (seed, cell) (${a.length} near the shore in June)`, a.length > 0 && JSON.stringify(a) === JSON.stringify(b));
const c = C.wildNearby(D, 8, 10, 10, 6, null, isWater, isGround, new Map());
ok('a different seed deals different spawns', JSON.stringify(a) !== JSON.stringify(c));
const byId = Object.fromEntries(D.species.map((s) => [s.id, s]));
const offHab = a.filter((s) => !C.wildHabitatOk(byId[s.sp].habitat, s.x, s.z, isWater, isGround));
ok('every spawn stands on its AUTHORED habitat (water / shore / land predicates)', offHab.length === 0, offHab.map((s) => s.id));
const dryOnly = C.wildNearby(D, 7, 1000, 0, 6, null, () => false, isGround, new Map());
ok('no water on the map: no water or shore species spawn', dryOnly.every((s) => byId[s.sp].habitat === 'land'));
const jan = C.wildNearby(D, 7, 10, 10, 1, null, isWater, isGround, new Map());
ok('the game calendar filters: nothing out of its months spawns (January has no alligator or slider)', jan.every((s) => byId[s.sp].months.includes(1)) && !jan.some((s) => ['american-alligator', 'red-eared-slider'].includes(s.sp)));
const g = byId['american-alligator'];
ok('photo judge: closer than the safe distance is refused (too_close), inside the band ok, beyond it too_far',
  C.wildJudge(g, g.safe - 1) === 'too_close' && C.wildJudge(g, (g.safe + g.photo) / 2) === 'ok' && C.wildJudge(g, g.photo + 1) === 'too_far');
ok('bearing: north is -z, east is +x', C.wildBearing(0, 0, 0, -10) === 'N' && C.wildBearing(0, 0, 10, 0) === 'E' && C.wildBearing(0, 0, -10, 10) === 'SW');
const hm = C.wildGatorMode(false, D), sm = C.wildGatorMode(true, D);
ok('gator season: harvest SIMULATION by default, nest SURVEY in classroom mode (different quests, the swap is labelled)',
  hm.mode === 'harvest-sim' && sm.mode === 'survey' && hm.quest === 'treasure-bayou-gator-tag' && sm.quest === 'treasure-bayou-nest-survey' && /Classroom mode/.test(sm.label) && /SIMULATION/.test(hm.label));
ok('the gator game rides only with the parish region (Bay has none)', D.games.gator && !B.games.gator && C.wildGatorMode(false, B) === null);
ok('store parser fails closed to an empty tc-wild/1 record', JSON.stringify(C.wildParse('{bad')) === '{"v":"tc-wild/1","seen":{}}' && C.wildParse('{"v":"tc-wild/1","seen":{"nutria":"x"}}').seen.nutria === 'x');
ok('every species carries its region quest id (bay: treasure-bayou-photo-bay-*)', B.species.every((s) => s.quest === 'treasure-bayou-photo-bay-' + s.id));

// python side, fail closed
const bad = py(['-c', 'import sys;sys.path.insert(0,"web");import wildkit;wildkit.wild_data("mars")']);
ok('wild_data refuses an unknown region by name', bad.code !== 0 && /region 'mars'/.test(bad.out));
const i18n = JSON.parse(py(['-c', 'import sys,json;sys.path.insert(0,"web");import wildkit;print(json.dumps({"k":wildkit.WILD_I18N_KEYS,"c":wildkit.wild_i18n()}))']).out);
const en = i18n.c.en.strings;
const copies = Object.entries(i18n.c).filter(([l]) => l !== 'en').flatMap(([l, c]) => i18n.k.filter((k) => c.strings[k] === en[k] && !/^\W*$/.test(en[k])).map((k) => `${l}:${k}`));
ok(`wild.* keys in all 8 locales (${i18n.k.length} keys), non-English values translated`, Object.keys(i18n.c).length === 8 && copies.length === 0, copies);
ok('placeholders {name} {m} {dir} survive in every locale', Object.values(i18n.c).every((c) => ['{name}', '{m}', '{dir}'].every((p) => c.strings['wild.near'].includes(p)) && c.strings['wild.photo_ok'].includes('{name}')));
const panel = py(['-c', 'import sys;sys.path.insert(0,"web");import wildkit;print(wildkit.wild_panel_html("parishes"));print(wildkit.WILD_CSS)']).out;
ok('panel: one section #wild-panel, a <details> fold, 44 px targets, play + calendar honesty lines', (panel.match(/id="wild-panel"/g) || []).length === 1
  && panel.includes('<details') && /min-block-size:44px/.test(panel) && /never a completion record/.test(panel) && /approximate, game calendar/.test(panel));
// builders mount through hudkit, inside a BAYOU block
for (const f of ['web/build_parishes.py', 'web/build_wilds.py']) {
  const s = readFileSync(join(ROOT, f), 'utf8');
  const blk = s.slice(s.indexOf('# BEGIN BAYOU w12'), s.indexOf('# END BAYOU w12'));
  ok(`${f}: one BAYOU w12 block registering hudkit panel 'wild'`, (s.match(/# BEGIN BAYOU w12/g) || []).length === 1 && /'id': 'wild', 'kind': 'panel', 'sel': '#wild-panel'/.test(blk));
}

console.log(fails ? `web/test_wildkit: ${fails} FAILED` : 'web/test_wildkit: all passed');
process.exit(fails ? 1 : 0);
