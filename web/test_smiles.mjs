/* web/test_smiles.mjs - the Unspoken Smiles world page (web/trade_craft_smiles.html, SMILES wave 12), checked against
 * smiles/registry/smiles.json and the i18n catalog. Browser-free; the walk + game probe lives in the SMILES probe run. */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const page = readFileSync(join(HERE, 'trade_craft_smiles.html'), 'utf8');
const kit = readFileSync(join(HERE, 'smileskit.py'), 'utf8');
const reg = JSON.parse(readFileSync(join(ROOT, 'smiles/registry/smiles.json'), 'utf8'));
const blob = (id) => JSON.parse(page.split(`<script type="application/json" id="${id}">`)[1].split('</script>')[0]);
const W = blob('sm-world'), D = blob('sm-data'), I = blob('sm-i18n');
const slice = (s) => s.slice(s.indexOf('/* SMILES_CORE:BEGIN'), s.indexOf('/* SMILES_CORE:END */'));

ok('exactly one <h1>, and it is the translated page title', (page.match(/<h1[\s>]/g) || []).length === 1
  && /<h1 class="tc-page-title" data-i18n="smiles.title">/.test(page));
ok('the site nav is present', page.includes('data-sitenav') && page.includes('id="tc-main"'));
ok('the saved-style head script runs before paint', page.indexOf('id="style-head-js"') > 0 && page.indexOf('id="style-head-js"') < page.indexOf('</head>'));
ok('the page says AUTHORED, not a real place, and that play is device-only and never a record',
  page.includes('<span class="tag">AUTHORED</span>') && /not a real place/.test(I.en.strings['smiles.authored'])
  && /never a completion record/.test(I.en.strings['smiles.play']) && page.includes('data-play-note'));
ok('the embedded data is the registry (same stamp, games and guidance)', D.stamp === reg.source_stamp
  && Object.keys(reg.games).length === 6 && Object.keys(reg.games).every((k) => JSON.stringify(D.games[k]) === JSON.stringify(reg.games[k]) && D.guidance[k] === reg.guidance[k])
  && D.disclaimer === reg.disclaimer);
ok('all 37 stations are linked from their clinic room at their source URL', reg.stations.length === 37
  && reg.stations.every((s) => page.includes(`<li data-station="${s.id}"><a href="${s.url}"`)) && Object.keys(W.stations).length === 37);
ok('every clinic room has a card and walk-in outline data', reg.rooms.every((r) => page.includes(`data-room="${r.id}"`))
  && JSON.stringify(W.rooms.map((r) => r.id)) === JSON.stringify(reg.rooms.map((r) => r.id)));
ok('every egg is on the shelf and in the world at its registry spot', reg.eggs.every((g) => page.includes(`data-egg="${g.id}"`)
  && JSON.stringify(W.eggs.find((x) => x.id === g.id).at) === JSON.stringify(g.at)));
ok('the ground is the ONE 4k map and walls use the ONE atlas (no tiles)', W.map === '../' + reg.map.image && W.atlas === '../' + reg.atlas.image
  && existsSync(join(ROOT, reg.map.image)) && existsSync(join(ROOT, reg.atlas.image)) && !/maps\/tiles/.test(page));
ok('the game core ships byte-for-byte from web/smileskit.py', slice(page).length > 1000 && slice(page) === slice(kit));
ok('six games with a tab each, and every game ends with guidance + the disclaimer', ['brushing', 'flossing', 'snacks', 'plaque', 'handwash', 'drinks'].every((g) =>
  page.includes(`data-sm-game="${g}"`)) && page.includes('id="sm-guidance"') && page.includes('data-i18n="smiles.disclaimer"'));
ok('hudkit lays out the world panels (near, toast, pad, minimap, eggs) and flow chips', page.includes('data-hud ') && ['near', 'toast', 'pad', 'minimap', 'eggs'].every((id) =>
  page.includes(`&quot;id&quot;: &quot;${id}&quot;`)) && page.includes('id="hud-kit"'));
ok('touch targets are at least 44 px (pad, world panel buttons, room links, game buttons)', /#sm-pad button\{min-block-size:44px;min-inline-size:44px/.test(page)
  && /\.sm-panel button\{min-block-size:44px;min-inline-size:44px/.test(page) && /\.room li a\{display:inline-flex;align-items:center;min-block-size:44px/.test(page)
  && /\.sm-tabs button,\.sm-stage button\{min-block-size:44px;min-inline-size:44px/.test(page));
const keys = [...new Set([...page.matchAll(/data-i18n(?:-aria)?="([^"]+)"/g)].map((m) => m[1]))];
ok(`every chrome key (${keys.length}) exists, non-empty, in all 8 locales; Arabic is right-to-left`, Object.keys(I).length === 8
  && keys.every((k) => Object.values(I).every((L) => typeof L.strings[k] === 'string' && L.strings[k].trim())) && I.ar.dir === 'rtl');
ok('the non-English chrome is translated, not copied (under 10% identical to English)', Object.entries(I).filter(([l]) => l !== 'en').every(([, L]) =>
  Object.keys(L.strings).filter((k) => L.strings[k] === I.en.strings[k]).length < Object.keys(L.strings).length * 0.1));
ok('the disclaimer reads exactly "General guidance, not medical or dental advice." in English', I.en.strings['smiles.disclaimer'] === 'General guidance, not medical or dental advice.');
ok('atlas cells are cut only after the atlas image loads (no texture update without image data)',
  /loader\.load\(W\.atlas, \(atlas\) => \{/.test(page) && !/atlas\.clone\(\)[^\n]*\n?[^\n]*return new THREE/.test(page));
ok('no Math.random, no network in the page scripts', !page.includes('Math.random') && !/fetch\(|XMLHttpRequest|sendBeacon/.test(page.split('<script id="sm-kit">')[1]));
ok('three.js comes from the vendored module, nothing external', page.includes("import * as THREE from './vendor/three.module.min.js'") && !/src="https?:/.test(page));
ok('eggs reach TCQuests only when the quest registry carries all of them', W.quests === (page.includes('QUEST_CORE:BEGIN'))
  && page.includes('const T = W.quests ? window.TCQuests : null;') && page.includes('if (T && T.data && T.data.quests.some((q) => q.id === g.id)) { T.find(g.id);'));
{ // POLISH w13 (item 5): one toast per egg find - the quest engine's (carrying the page's reveal line) or the page's, never both
  const fe = (page.match(/const findEggs = [\s\S]*?\} \} \};/) || [''])[0];
  ok('one toast per egg find: with quests on the quest engine toast carries the reveal line, else the page toast (never both)',
    /if \(T && T\.data && T\.data\.quests\.some\(\(q\) => q\.id === g\.id\)\) \{ T\.find\(g\.id\); T\.toast\(said\); \} else toast\(said\);/.test(fe)
    && (fe.match(/\btoast\(/g) || []).length === 2 && (fe.match(/T\.toast\(/g) || []).length === 1 && /const said = `\$\{t\('smiles\.egg\.got'\)\}: \$\{g\.title\} - \$\{g\.badge\}\. \$\{g\.reveal\}`/.test(fe));
}
ok('no fabricated sugar figures on the page (categories only)', !/\d\s*(grams?|tsp|teaspoons?)\b/i.test(page.split('id="sm-data">')[1].split('</script>')[0]));

// physics: the page's walls are the registry walls, made solid with the page's own copy of web/physkit.py (run here)
const physSrc = page.slice(page.indexOf('/* PHYS_KIT:BEGIN'), page.indexOf('/* PHYS_KIT:END */'));
const PK = new Function(physSrc + '\nreturn { createPhysics, physAvatar, physCoeffs };')();
const PREG = JSON.parse(page.split('<script type="application/json" id="sm-phys">')[1].split('</script>')[0]);
const boxes = reg.walls.map((w) => { const [x0, z0] = w.from, [x1, z1] = w.to, len = Math.hypot(x1 - x0, z1 - z0);
  return { id: w.id, cx: (x0 + x1) / 2, cz: (z0 + z1) / 2, hx: len / 2, hz: 0.2, yaw: -Math.atan2(z1 - z0, x1 - x0), y0: 0, y1: w.h, kind: 'wall' }; })
  .concat(reg.zones.flatMap((z) => z.solids.map((r, i) => ({ id: z.id + i, cx: r[0] + r[2] / 2, cz: r[1] + r[3] / 2, hx: r[2] / 2, hz: r[3] / 2, yaw: 0, y0: 0, y1: 3, kind: 'building' }))));
const walk = (x, z, vx, vz, secs) => { const P = PK.createPhysics({ reg: PREG, cell: 16, ground: () => 0, water: () => null }); P.addBoxes(boxes);
  const av = PK.physAvatar(x, 0, z); for (let i = 0; i < secs * 60; i++) P.stepAvatar(av, { vx, vz, jump: false }, 1 / 60); return av; };
const R0 = PK.physCoeffs(PREG).avatar.radius;
ok('the page draws the registry walls and makes them solid with the shared physkit (no forked physics)', page.includes('for (const w of W.walls) wall(')
  && page.includes('PW.addBoxes(BOXES)') && page.includes('PW.stepAvatar(av,') && physSrc.length > 1000 && W.walls.length === reg.walls.length);
ok(`every doorway (${reg.doors.length}) can be walked through, north from the street side`, reg.doors.length === reg.rooms.length + reg.zones.filter((z) =>
  ['clinic', 'school', 'community', 'shop', 'vanlot', 'library'].includes(z.kind)).length && reg.doors.every((d) => walk(d.at[0], d.at[1] + 2, 0, -9, 1).z < d.at[1] - 3));
ok('walls are solid: walking into each building\'s south wall beside the doorway stops at the wall', reg.zones.filter((z) =>
  ['clinic', 'school', 'community', 'shop', 'vanlot', 'library'].includes(z.kind)).every((z) => { const zs = z.rect[1] + z.rect[3];
  const av = walk(z.rect[0] + 3, zs + 3, 0, -9, 2); return av.z >= zs + R0 - 0.05; }));
ok('houses and market stalls are solid too', reg.zones.filter((z) => z.solids.length).every((z) => { const r = z.solids[0];
  const av = walk(r[0] + r[2] / 2, r[1] + r[3] + 3, 0, -9, 2); return av.z >= r[1] + r[3] + R0 - 0.05; }));
console.log(`test_smiles: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
