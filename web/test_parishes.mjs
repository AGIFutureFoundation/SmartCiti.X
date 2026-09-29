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

// wave 7: the label key list is pathkit's own PATH_LABEL_KEYS (18 in wave 6, 32 with the seven-path chooser)
const PATH_KEYS = [...(read('web/pathkit.py').match(/PATH_LABEL_KEYS = \(([\s\S]*?)\)/) || [, ''])[1].matchAll(/'([^']+)'/g)].map((m) => m[1]);
const locs = ['ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'zh'];
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
check('[perf] chunk budget declared once', (main.match(/const CHUNK_M = 250, RADIUS = 3, CELL = 25, BUILD_PER_FRAME = 3;/g) || []).length === 1 && /const CAP = \{ block: 6000, tree: 4000, lamp: 2500, marker: 64, lm: 64 \}/.test(main));

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
  check('[npcs] kit inlined; dialogue labels from the kit\'s npc.* keys via the page catalogue (strict tr)', main.includes('function createNPCKit') && /labels: labelsFrom\(tr\),/.test(main) && CAT && ['npc.talk', 'npc.quotelang', 'npc.role.pilot'].every((k) => locs.every((l) => CAT[l].strings[k])));
}

// [wave 5b] fail closed on an undeclared page; pathkit localised; quest finds; overview headroom; detail
const bsrc = read('web/build_parishes.py');
check('[nav] an undeclared page stops the build (no sibling-nav fallback)', /if PAGE not in sitenav\.PAGES:\n    raise BuildError/.test(bsrc) && (bsrc.match(/nav_html\(/g) || []).length === 1 && !bsrc.includes("nav_html('web/trade_craft_wilds.html'"));
const PL = json('parish-path-labels');
check('[layers] pathkit labels from pathkit.path_labels in all 8 locales, picked by the page locale', /labels: PATH_L/.test(main) && /const PATH_L = JSON\.parse\(document\.getElementById\('parish-path-labels'\)\.textContent\)\[LOC\];/.test(main) && PL && ['ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'zh'].every((l) => PL[l] && Object.keys(PL[l]).length === PATH_KEYS.length && PATH_KEYS.every((k) => k in PL[l]) && Object.values(PL[l]).every((v) => typeof v === 'string' && v.trim())));
check('[quests] no click-to-find button for finds the world fires by play', !/data-tc-egg="treasure-(parish-\d+-(arrive|lm-)|guide-|station-)/.test(html));
const FI = json('parish-finds');
if (FI) {
  const QR = JSON.parse(read('quests/registry/quests.json')).quests.map((q) => q.id);
  const all = [...Object.values(FI.arrive), ...Object.values(FI.border), ...Object.values(FI.landmark), ...Object.values(FI.ride)];
  check('[quests] every wired find is a quest registry id', all.length > 0 && all.every((id) => QR.includes(id)));
  check('[quests] every border and landmark treasure in the registry is wired', QR.filter((q) => /^treasure-border-|^treasure-parish-\d+-lm-/.test(q)).every((q) => all.includes(q)));
  check('[quests] finds fire on border crossing, arrival, landmark reach and boarding', /qfind\(FINDS\.border\[/.test(main) && /qfind\(FINDS\.arrive\[/.test(main) && /qfind\(FINDS\.landmark\[l\.id\]\)/.test(main) && /qfind\(FINDS\.ride\[v\.medium\]\)/.test(main));
  check('[quests] a teleport is not a border crossing', /jumping = true; checkParish\(\); jumping = false;/.test(main) && /if \(current && !jumping\)/.test(main));
}
check('[perf] overview hides fleet, skips NPC updates and chunk streaming', /if \(fl\) fl\.group\.visible = !over;/.test(main) && /if \(npcKit && !over\)/.test(main) && /if \(!over\) \{ if \(c !== cell\)/.test(main));
check('[detail] street lamps are one InstancedMesh on AUTHORED street cells', /new THREE\.InstancedMesh\(lampGeo, matLamp, CAP\.lamp\)/.test(main) && /out\.lamp\.push/.test(main));
check('[perf] overview replaces the water pass with a water-coloured clear', /water\.visible = !over; scene\.background = over \? WATER_BG : SKY_BG;/.test(main));
check('[theme] quest toast text token defined from the theme (--paper)', /--paper:var\(--tc-plate\)/.test(ownStyle));
check('[npcs] guides follow their routines on the kit clock, never in the overview', /npcClock\.tick\(dt\)/.test(main) && /const npcClock = makeClock\(8, 1 \/ 60\);/.test(main));
check('[perf] overview renders at the declared 0.6 pixel scale and skips the parish check', /const OVERVIEW_PR = 0\.6;/.test(main) && /applyPR\(m === 'overview' \? OVERVIEW_PR : 1\);/.test(main) && /if \(mode !== 'overview'\) checkParish\(\);/.test(main));
check('[detail] water shimmer is a uniform, not a mesh', /matWater\.emissiveIntensity = /.test(main));

// [kit] wave 6: the AUTHORED building kit, ground tiles, atmosphere (browser measures: web/eval_parishes.mjs kit/ground/atmosphere rows)
check('[kit] two building families (house, midrise incl. industrial shells), each ONE InstancedMesh with per-instance colour',
  /new THREE\.InstancedMesh\(houseGeo, kitMat\('house'\), CAP\.block\)/.test(main) && /new THREE\.InstancedMesh\(blockGeo, kitMat\('midrise'\), CAP\.block\)/.test(main)
  && /const KIT = \{ house: houses, midrise: blocks \};/.test(main) && /m\.setColorAt\(0, KC\.set\(0xffffff\)\)/.test(main)
  && /if \(nb >= CAP\.block\) break;/.test(main));
check('[kit] style and height by an AUTHORED land-use district; park lots build no building',
  /function landUse\(x, z\) \{ const h = wildsHash\(Math\.floor\(x \/ DISTRICT_M\), Math\.floor\(z \/ DISTRICT_M\), SEED, 7\);/.test(main)
  && /if \(use === 'park'\) \{ if \(h < 0\.8\) out\.tree\.push/.test(main) && /out\.block\.push\(kitLot\(use, /.test(main));
check('[kit] gable roofs and a porch/gallery hint are geometry; windows are a shader pattern, not triangles',
  /const houseGeo = mergeGeometries\(\[walls\(\), gable\(0\.42, 0\.04, 0\.08\), porch\(\)\]\);/.test(main)
  && /float win = step\(0\.3, f\.x\)/.test(main) && /smoothstep\(160\.0, 480\.0, vKitD\)/.test(main));
check('[kit] trees are open-ended (14 triangles, pays for the roofs)', /CylinderGeometry\(0\.25, 0\.3, 2, 4, 1, true\)/.test(main) && /ConeGeometry\(2\.2, 6, 6, 1, true\)/.test(main) && /side: THREE\.DoubleSide/.test(main));
{
  const regP = Object.values(REG.parishes);
  const tilesOk = D && D.parishes.every((p) => { const r = REG.parishes[p.id]; const g = r && r.map.ground_tiles; return g && p.ground.tiles.length === g.tiles.length && g.tiles.length === g.grid * g.grid && p.ground.tiles.every(([src]) => existsSync(ROOT + src)); });
  check('[ground] every parish carries its PARISH v1.3 ground tiles and each file exists', !!tilesOk && regP.length === D.parishes.length);
  const lbl = regP[0].map.ground_tiles.label;
  const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  check('[ground] the ground_tiles label is shown verbatim next to the 3D view', html.includes(`<p class="help" data-ground-label lang="en">${esc(lbl)}</p>`) && html.indexOf('data-ground-label') > html.indexOf('id="stage"'));
}
check('[ground] tiles drape as ONE composed texture per parish on the flat land (no extra mesh, still y = 0)',
  /const GROUND_PX = 2048;/.test(main) && /cx\.drawImage\(im, col \* cell, row \* cell, cell, cell\)/.test(main) && /new THREE\.Mesh\(g, streetMat\(LAND\[p\.idx % LAND\.length\], p\)\)/.test(main) && /pa\[i\] = 0/.test(main));
check('[ground] the AUTHORED street grid is painted in the land shader, near field only', /float road = max\(step\(5\.0, q\.x\)/.test(main) && /float far = 1\.0 - smoothstep\(220\.0, 420\.0, vGroundDist\);/.test(main));
check('[atmos] sky is a gradient on a transparent canvas (no sky mesh); fog = horizon colour; declared sun',
  /alpha: true, powerPreference/.test(main) && /renderer\.setClearColor\(HORIZON, 0\);/.test(main) && /canvas\.style\.backgroundImage = 'linear-gradient\(180deg,'/.test(main)
  && /scene\.fog = new THREE\.Fog\(HORIZON, /.test(main) && /sun\.position\.copy\(SUN\)/.test(main));
check('[atmos] water: fresnel sky reflection + ripple on its one material', /matWater\.onBeforeCompile = /.test(main) && /float fr = pow\(1\.0 - clamp\(v\.y, 0\.0, 1\.0\), 4\.0\)/.test(main) && /waterU\.uTime\.value = now \/ 1000;/.test(main));
check('[review] satellite toggle: one shared config read and superseded calls stop (REVIEW wave 6)',
  /if \(tokenP\) return tokenP;/.test(main) && /const gen = \+\+satGen;/.test(main) && /if \(gen !== satGen\) return satState\(\);/.test(main));
check('[review] E/T keys ignore key-repeat, modifier chords and typing (REVIEW wave 6)',
  /const plainKey = \(e\) => !e\.repeat && !e\.ctrlKey && !e\.metaKey && !e\.altKey/.test(main) && /\(e\.key === 'e' \|\| e\.key === 'E'\) && plainKey\(e\)/.test(main) && /\(e\.key === 't' \|\| e\.key === 'T'\) && plainKey\(e\)/.test(main));
check('[review] riding + overview: every mode change goes through applyMode; a mode button returns to the ride (REVIEW wave 6)',
  /riding = null; applyMode\('walk'\);/.test(main) && /riding\.snap = true; applyMode\(/.test(main) && /if \(mode !== 'overview'\) return false;\s*applyMode\(riding\.medium === 'water' \? 'boat' : 'drive'\); return true;/.test(main)
  && !/(?<!let |\.)\bmode = (?!m;)/.test(main));

// wave 7: world layer, physics, ambience, city life, seven paths - each kit present, mounted, and honest
const WREG = existsSync(ROOT + 'parishes/registry/world.json') ? JSON.parse(read('parishes/registry/world.json')) : null;
const liOf = (k) => (html.match(new RegExp(`<li data-legend="${k}" lang="en">([^<]*)</li>`)) || [, null])[1];
const unesc = (t) => t && t.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'");
check('[world] PARISH v1.4 wired: every parish carries its world file and the streets path with arterial/collector/local cross-sections',
  !!WREG && /<li data-contract="world" data-state="wired">/.test(html) && D.parishes.every((p) => p.world === WREG.parishes[p.id].path && p.roads
    && p.roads.path === REG.parishes[p.id].map.streets.path && ['arterial', 'collector', 'local'].every((c) => { const q = p.roads.classes[c], w = WREG.roads.classes[c];
      return q && q.carriageway_m === w.carriageway_m && q.curb_height_m === w.curb_height_m && JSON.stringify(q.sidewalk_m) === JSON.stringify(w.sidewalk_m); })));
check('[roads] streets meshed as ONE merged mesh (carriageway, kerb faces, both sidewalks); the painted grid switches off where meshed',
  /const roads = new THREE\.Mesh\(roadGeo, matRoad\);/.test(main) && /ROAD_COL\.asphalt/.test(main) && /ROAD_COL\.kerb/.test(main) && /ROAD_COL\.walk/.test(main)
  && /far \*= uGrid;/.test(main) && /m\.material\.userData\.grid\.value = 0;/.test(main) && (main.match(/new THREE\.Mesh\(roadGeo/g) || []).length === 1);
check('[roads] lots stand back from the meshed kerbs and face their street; lamps stand on the sidewalks',
  /rn\.edge < Math\.hypot\(lot\[2\], lot\[4\]\) \/ 2 \+ 0\.5/.test(main) && /lot\[6\] = Math\.atan2\(-rn\.nx, -rn\.nz\);/.test(main) && /out\.lamp\.push\(\[px, pz,/.test(main));
check('[water] AUTHORED water legend verbatim from world.json, never RECORDED; water is cut out of the land (no new mesh)',
  !!WREG && unesc(liOf('water_world')) === WREG.water_note && /AUTHORED water - procedural, NOT the real lakes, rivers or bayous/.test(liOf('water_world') || '')
  && !/RECORDED/.test(liOf('water_world') || '') && /shapes\[k\]\.holes\.push\(/.test(main) && D.world && D.world.surface_y === WREG.water_levels.surface_y_m);
check('[phys] physkit mounted: registry embedded verbatim, page boxes (buildings + kerbs) handed to createPhysics, walk and drive stepped by it',
  json('physics-registry') !== null && JSON.stringify(json('physics-registry')) === JSON.stringify(JSON.parse(read('physics/registry/physics.json')))
  && /PHYS_KIT:BEGIN/.test(main) && /createPhysics\(\{ reg: PHYS_REG, cell: 16, ground: \(\) => 0, water: waterAt \}\)/.test(main)
  && /y0: 0, y1: h, kind: 'building' \}\);/.test(main) && /y0: 0, y1: ROAD_Y \+ s\.kh, kind: 'curb' \}\);/.test(main) && /W\.addBoxes\(list\);/.test(main) && /W\.stepAvatar\(av, \{/.test(main) && /fleetPhysStep\(riding\.st, riding\.spec, input, fground, dt, \{/.test(main)
  && /<li data-contract="physics" data-state="wired">/.test(html));
check('[phys] honesty: arcade physics line verbatim; vehicles never strike people; help says no injury is depicted; no "realistic" crash claim',
  unesc(liOf('physics')) === JSON.parse(read('physics/registry/physics.json')).honesty && /Vehicles never strike people, NPCs, pets or animals\./.test(liOf('physics') || '')
  && /no injury is depicted/.test(JSON.parse(read('i18n/locales/en.json')).strings['parishes.world.help'] || '') && /no injury is depicted/.test((html.match(/<li data-legend="help"><span data-i18n="parishes\.world\.help">([^<]*)</) || [, ''])[1]) && /<li data-legend="help">/.test(html) && !/realistic crash|crash[- ]test(?!,)/i.test(html.replace(/not a crash test/g, ''))
  && /people: people\(\)/.test(main) && /cls: 'npc'/.test(main) && /out\.push\(\.\.\.amb\.people\(\)\)/.test(main));
check('[phys] splash visual and crash smoke are drawn only while they play (0 draw calls idle)',
  /splash\.visible = false;/.test(main) && /if \(t > 0\.8\) splash\.visible = false;/.test(main) && /fleetSmoke\(THREE, 48\)/.test(main) && /smoke\.puff\(/.test(main));
check('[ambient] ambientkit mounted OFF by default behind the Living world button; hidden in the overview; its page line verbatim',
  /function createAmbient\(/.test(main) && /let amb = null;/.test(main) && /<button type="button" class="tc-btn tc-btn-ghost" id="amb" aria-pressed="false">/.test(html)
  && /amb\.setOverview\(over\)/.test(main) && /amb\.onChunkLoad\(a, b, landUse\)/.test(main) && /amb\.onChunkUnload\(a, b\)/.test(main)
  && existsSync(ROOT + 'ambient/registry/ambient.json') && unesc(liOf('ambient')) === JSON.parse(read('ambient/registry/ambient.json')).honesty.page_line
  && /<li data-contract="ambient" data-state="wired">/.test(html));
check('[econ] city-life panel mounted per parish: play coins - not money; local state only; no payments or Stripe in its script',
  /<section class="tc-econ" id="tc-econ" data-tc-econ/.test(html) && /<script data-tc-econ-kit>/.test(html) && /TCEcon\.mountEcon\(null, \{ parish: current\.id \}\)/.test(main)
  && /TCEcon\.onPlayerMove\(current\.id/.test(main) && /play coins - not money/i.test(html)
  && !/stripe|payments\//i.test((html.match(/<script data-tc-econ-kit>([\s\S]*?)<\/script>/) || [, 'x stripe'])[1]) && /<li data-contract="economy" data-state="wired">/.test(html));
{
  const PD = json('parish-paths'), ids = ['trades', 'k12', 'responders', 'un', 'relief', 'teachers', 'roam'];
  check('[paths] seven-path chooser data in every parish (fixed order), UN path PROPOSED with its disclaimer on the page',
    !!PD && D.parishes.every((p) => PD[p.id] && PD[p.id].adventure && JSON.stringify(PD[p.id].adventure.paths.map((q) => q.id)) === JSON.stringify(ids)
      && PD[p.id].adventure.paths.find((q) => q.id === 'un').status === 'PROPOSED' && PD[p.id].adventure.un_disclaimer === 'not affiliated with or endorsed by the United Nations')
    && /not affiliated with or endorsed by the United Nations/.test(html));
}

check('[perf] the painted-grid shader block runs only nearer than its fade on unmeshed land; the overview skips splash, smoke and city-life work',
  /if \(vGroundDist < 420\.0 && uGrid > 0\.5\) \{ vec2 q = mod\(vGroundXZ, 100\.0\);/.test(main) && /if \(!over\) \{ stepSplash\(dt\); if \(smoke && smoke\.mesh\.visible\) smoke\.update\(dt\); \}/.test(main)
  && /if \(!over && !DIAG\.noEcon && window\.TCEcon && current\)/.test(main));

// [contracts] stubs are named
for (const k of ['fleet', 'npcs', 'layers']) {
  const m = html.match(new RegExp(`<li data-contract="${k}" data-state="(wired|stub)">([\\s\\S]*?)</li>`));
  check(`[contracts] ${k} row states wired or names what is missing`, !!m && (m[1] === 'wired' || /data-why>[^<]{10,}/.test(m[2])));
}

// [i18n] the run-time catalogue: 8 locales, exactly the used keys, real translations
check('[i18n] catalogue carries the 8 locales', CAT && JSON.stringify(Object.keys(CAT).sort()) === JSON.stringify(locs));
const used = new Set([...html.matchAll(/data-i18n(?:-aria)?="(parishes\.[a-z0-9_.]+)"/g)].map((m) => m[1]));
for (const m of main.matchAll(/tr\('(parishes\.[a-z0-9_.]+)'\)/g)) used.add(m[1]);
if (/labels: labelsFrom\(tr\)/.test(main)) for (const m of main.matchAll(/'(npc\.[a-z0-9.]+)'/g)) used.add(m[1]);
{ const pl = main.match(/const PATH_L = Object\.fromEntries\(\[([^\]]+)\]\.map\(\(k\) => \[k, tr\('parishes\.path\.' \+ k\.toLowerCase\(\)\)\]\)\);/);
  if (pl) for (const m of pl[1].matchAll(/'([a-zA-Z]+)'/g)) used.add('parishes.path.' + m[1].toLowerCase()); }
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
