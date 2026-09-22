/**
 * 3D environment: the teardown and per-frame contracts, held at the source.
 *
 * A read-only profile of the page found the region board rebuilt on every
 * return and never freed, the campus detached but never disposed, every
 * view's label sprites kept in labelSet (and scored every frame) long
 * after their group was gone, and the restoration walk rebuilding the
 * whole campus on exit - about +18 MB of heap, +787 geometries and +328
 * sprites per region->campus->hall->walk->sim->resto->region cycle, never
 * reclaimed. No browser runs here (verify_all.sh reaches no network and
 * opens no browser); these hold the generator's source to the fixes so
 * the leak cannot come back quietly. A bug becomes a check.
 */
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const src = readFileSync(new URL('./build_3d.py', import.meta.url), 'utf8');
// the body of a top-level `function name(` - or `async function name(`:
// up to the column-0 brace that closes it. The async form matters, and it
// bit once: fn('guideListen') came back EMPTY against an async function, so
// a check written over it would have passed on nothing at all. An empty
// body is now a failure rather than a silent pass.
const fn = (name) => {
  let i = src.indexOf(`\nfunction ${name}(`);
  if (i < 0) i = src.indexOf(`\nasync function ${name}(`);
  if (i < 0) { console.error('FAIL no such function in the source:', name); process.exit(1); }
  const j = src.indexOf('\n}\n', i + 1);
  return src.slice(i, j < 0 ? undefined : j + 2);
};

/* The source with its comments cut out.
   Twice now a check counting or forbidding a string has matched the COMMENT
   that explains why the string is gone - the old `ontouchstart` expression
   and the old fixed sun vector are both quoted in the notes beside their
   replacements. A check that reads its own explanation is answering a
   different question than the one it was written to ask. */
const strip = (t) => t.replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '');
const code = strip(src);
/* One function's body, comments cut out. Four checks in a row have now
   matched the COMMENT that explains why a string is gone rather than the
   string: the old `ontouchstart` expression, the old fixed sun vector, the
   forbidden fabric constant, and `fab['treasure-island']` quoted inside the
   very function that stopped using it. A check written as "this is no
   longer here" must read code, and the comment explaining the removal is
   the likeliest place for the removed text to still be. */
const fnCode = (name) => strip(fn(name));

/* ------------------------------------------------------------ teardown --- */
ok('disposeOf() is the one teardown path, and it still never disposes a shared (cached) geometry',
  /if \(o\.geometry && !o\.geometry\.userData\?\.shared\) o\.geometry\.dispose\(\);/.test(fn('disposeOf')));
ok('disposeOf() prunes a label sprite out of labelSet, drops the focus if it was the focus, and releases its texture',
  /labelSet\.splice\(i, 1\)/.test(fn('disposeOf'))
  && /if \(labelFocus === o\) labelFocus = null;/.test(fn('disposeOf'))
  && /lblTexRelease\(o\.userData\.lbl\.texKey\)/.test(fn('disposeOf')));
ok('buildRegion() disposes the board it replaces, and showRegion() builds the static board once and shows it again',
  /if \(regionGroup\) \{ scene\.remove\(regionGroup\); disposeOf\(regionGroup\); \}/.test(fn('buildRegion'))
  && /if \(!regionGroup\) buildRegion\(\);\s*regionGroup\.visible = true;/.test(fn('showRegion')));
ok('buildCampus() disposes the campus it replaces (merged buildings, roads, ring, every label texture)',
  /if \(campusGroup\) \{ scene\.remove\(campusGroup\); disposeOf\(campusGroup\); \}/.test(fn('buildCampus')));
ok('showCampus() restores the campus it already holds - same campus, same locale - instead of rebuilding it (the restoration walk exits through it)',
  /campusGroup\.userData\.key === key\s*&& campusGroup\.userData\.loc === loc/.test(fn('showCampus'))
  && /campusGroup\.visible = true;/.test(fn('showCampus'))
  && /spawnFauna\(key, campusR\);\s*buildMinimap\(key, campusR\);/.test(fn('showCampus'))
  && /showCampus\(ck\)/.test(fn('exitRestoWalk')));
ok('labelStep() still drops orphaned sprites, and skips a sign whose group is hidden (the cached board behind a campus)',
  /if \(!sp\.parent\) continue;/.test(fn('labelStep'))
  && /for \(let o = sp\.parent; o && o !== scene; o = o\.parent\)\s*if \(!o\.visible\)/.test(fn('labelStep')));
ok('teardownRestoWalk() and teardownSim() still dispose what they built',
  /disposeOf\(restoGroup\)/.test(fn('teardownRestoWalk')) && /disposeOf\(/.test(fn('teardownSim')));

/* ---------------------------------------------------------- draw calls --- */
ok('a building keeps its own wall box (the raycast target carrying userData.slug) while its decoration pools per district',
  /bld\.userData\.slug = h\.slug;/.test(fn('building'))
  && /const parts = pool;/.test(fn('building'))
  && /flushParts\(pool, cg\);/.test(fn('buildCampus'))
  && /ray\.intersectObjects\(buildings, false\)/.test(src));
ok('the station beacons are one InstancedMesh per campus, spun as one in the loop',
  /new THREE\.InstancedMesh\(new THREE\.OctahedronGeometry\(\.9\), mat\.post/.test(fn('flushBeacons'))
  && /if \(view === 'campus'\) spinBeacons\(dt\);/.test(src));
ok('road planes merge into one mesh per material per campus, and the ring dashes join the one dash mesh',
  /roadAcc\.get\(m\)/.test(fn('roadRect')) && /flushRoads\(campusGroup\);/.test(fn('buildCampus'))
  && /dashGeo\(\.16, 1\.6, Math\.cos\(th\) \* rr, Math\.sin\(th\) \* rr, -th\);/.test(fn('buildCampus')));
ok('roads and dashes are carried through the district frame into campus coordinates (the dashes used to be merged untransformed)',
  /ge\.applyMatrix4\(_rdM\)\.applyMatrix4\(g\.matrixWorld\)/.test(fn('roadRect'))
  && /ge\.applyMatrix4\(dashFrame\.matrixWorld\)/.test(fn('dashGeo')));

/* ------------------------------------------------------------ per frame --- */
ok('setDash() writes a gauge only when its text or warn state changed',
  /if \(txt !== c\.txt\) \{ c\.gv\.textContent = txt; c\.txt = txt; \}/.test(fn('setDash'))
  && /if \(warn !== c\.warn\)/.test(fn('setDash')));
ok('mmDraw() redraws only while walking or once after a build, on a cached 2D context',
  /if \(!walkActive && !mmDirty && !mmArrow\) return;/.test(fn('mmDraw'))
  && /mmCtx \?\?= cv\.getContext\('2d'\)/.test(fn('mmDraw'))
  && /mmDirty = true;/.test(fn('buildMinimap')));
ok('the walk allocates nothing per frame: scratch vectors and the hall record cached on showHall()',
  !/new THREE\.Vector3\(/.test(fn('walkStep')) && !/new THREE\.Vector3\(/.test(fn('touchWalkStep'))
  && !/D\.halls\.find\(x => x\.slug === slug\)/.test(fn('walkStep'))
  && !/D\.halls\.find\(x => x\.slug === slug\)/.test(fn('touchWalkStep'))
  && /hallRec = D\.halls\.find\(x => x\.slug === sg\);/.test(fn('showHall')));
ok('the advisors, the emote and the XR draw allocate nothing per frame either',
  !/new THREE\.Vector3\(/.test(fn('advisorNear')) && /advBtnEl \?\?=/.test(fn('advisorProximity'))
  && !/\.filter\(/.test(fn('stepEmote')) && !/fogBanks\.map\(/.test(fn('xrRender'))
  && !/\.forEach\(/.test(fn('setXRDash')));

/* ------------------------------------------------------------- textures --- */
ok('identical signs share one CanvasTexture, reference-counted, released with the last sprite',
  /const texKey = kindId \+ '\|' \+ accent \+ '\|' \+ text \+ '\|' \+ \(sub \?\? ''\);/.test(fn('label'))
  && /if \(--e\.refs <= 0\) \{ e\.tex\.dispose\(\); lblTexCache\.delete\(key\); \}/.test(fn('lblTexRelease'))
  && /lblTexRelease\(sp\.userData\.lbl\?\.texKey\)/.test(fn('xrHudDrop')) && !/map\?\.dispose/.test(fn('xrHudDrop'))
  // no sign's map is disposed by hand anywhere: the satellite plane is the one non-label map that is
  && (src.match(/\.map\?\.dispose\(\)/g) || []).length === 1 && /satPlane\.material\.map\?\.dispose\(\)/.test(src));
ok('the glTF exporter and loader are imported on first use of the .glb buttons, never at boot',
  /await import\('three\/addons\/gltf\/GLTFExporter\.js'\)/.test(src)
  && /await import\('three\/addons\/gltf\/GLTFLoader\.js'\)/.test(src)
  && !/^import .*GLTF/m.test(src) && !/modulepreload/.test(src));

ok('the quality ladder steps back up once - a 10 s window at or above 45 fps - and never flaps',
  /if \(qRose\) return;/.test(fn('qLadder'))
  && /qFrames \/ qAcc >= 45\) \{ qRose = true; setQuality\('high'\); \}/.test(fn('qLadder'))
  && /qFrames \/ qAcc < 22/.test(fn('qLadder'))
  // the guard stays where it was: a harness run must not be demoted out
  // from under a measurement, and the ladder's logic is reached through it
  && /if \(!qAuto \|\| reduced \|\| navigator\.webdriver\) return;/.test(fn('qStep'))
  && /qLadder\(dt\);/.test(fn('qStep')));

/* ------------------------------------------------- surfaces and light --- */
/* The world read as a rendering rather than a place, and each of these is
   the specific reason. Floors carried twenty-two finishes and walls carried
   one flat colour; the pattern was painted into the colour map with no
   relief, so a checkerplate floor and a sheet-vinyl floor caught the light
   identically; and the illuminance figure every room has carried since
   24.2 was TEXT in two panels and drove nothing at all. A bug becomes a
   check - including the near-miss: an emissive box is a bright object, not
   a light, and would have looked like the fix without being it. */
ok('one surface engine serves floors and walls, and it returns a normal map beside the colour map',
  /function surfaceMaps\(color, pattern\)/.test(src)
  && /const out = \{ map, normalMap \};/.test(fn('surfaceMaps'))
  && /function finishMat\(fin, w, d\)/.test(src)
  && /function wallMat\(wal, runM, hM\)/.test(src));
ok('the relief is read off a height field the pattern pass drew, not off a second table that could disagree with it',
  /function paintPattern\(g, hg, pat, S2\)/.test(src)
  && /const normalMap = normalFromHeight\(h, S2, PATTERN_RELIEF\[pattern\] \?\? 0\);/.test(src)
  && /function normalFromHeight\(h, size, relief\)/.test(src));
ok('a pattern with no relief declared skips the normal map rather than shipping a flat one',
  /if \(!\(relief > \.01\)\) return null;/.test(fn('normalFromHeight')));
ok('the hall shell and every room partition read their wall from the registry, not from one flat mat.wall',
  /const wallRec = D\.walls\[h\.slug\];/.test(src)
  && /const shellW = D\.wallCat\[wallRec\.procedure\.wall\];/.test(src)
  && /const wal = D\.wallCat\[wallRec\[r\.strand\]\.wall\];/.test(src));
ok('the wall map is deduped on the wire on its OWN index, not folded into the finish index',
  /WALL_MAPS, WALL_IDX = \[\], \{\}/.test(src)
  && /D\.walls = Object\.fromEntries\(Object\.entries\(D\.wallIdx\)/.test(src));
ok("the room's illuminance record drives a real light, not only the luminaire's emissive",
  /const rc = condOf\(h\.slug, r\.strand\);/.test(src)
  && /const luxN = Math\.max\(0, Math\.min\(1, \(rc\.lux - 200\) \/ 800\)\);/.test(src)
  // the intensity now goes through lampCd - see the luminaire-units block
  // below, which is where that changed and why
  && /new THREE\.PointLight\(0xffe9c8,\s*\n?\s*lampCd\(\.55 \+ luxN \* 1\.45,/.test(src));
ok('those lights ride the quality ladder, so a device on the bottom rung does not pay for eleven of them',
  /rl\.visible = qLevel !== 'low';/.test(src)
  && /for \(const rl of roomLights\) rl\.visible = l !== 'low';/.test(fn('setQuality')));
ok('the PPE placard is hung only where the room actually requires PPE (an empty list gets no sign, not a sign saying nothing)',
  /if \(rc\.ppe\.length\) \{/.test(src)
  && /kind: 'placard'/.test(src));
ok('the shared envelope materials carry their own surface, and the tint is not doubled onto the map',
  /\['wall', 'panel', 3\], \['brick', 'brick', 6\], \['block', 'block', 5\],/.test(src)
  && /m2\.color\.setHex\(0xffffff\);/.test(src));
/* The teardown contract for the new materials is the ABSENCE of a mark:
   disposeOf() frees any material not carrying userData.shared, so a hall's
   own wall, wainscot, floor and luminaire materials must never carry it -
   while the page-wide `mat` table and the per-hue cache must. Asserting the
   absence is the whole contract; a registry of them would be a second copy
   of a fact the traverse already holds. */
ok('a hall\'s own materials are never marked shared (so disposeOf frees them), while the page-wide tables still are',
  /for \(const m of Object\.values\(mat\)\) m\.userData\.shared = true;/.test(src)
  && /m2\.userData\.shared = true;/.test(fn('hueMatOf'))
  && !/userData\.shared\s*=/.test(fn('finishMat'))
  && !/userData\.shared\s*=/.test(fn('wallMat'))
  && !/userData\.shared\s*=/.test(fn('buildHall')));

/* ------------------------------------------- yards, walks and their light --- */
/* The same gap the halls had, one level out: a simulator yard was a fence
   and four masts on the page's global ground plane, and every restoration
   walk stood on one rough-grass pad whatever its habitat. Both now read
   their footing from the registry that owns it. And the mast head was the
   same near-miss the room luminaire was - a bright object that lit nothing. */
ok('a sim yard lays the floor its own registry entry declares, with relief',
  /const yard = D\.sims\.sims\[simId\]\?\.yard;/.test(fn('simYard'))
  && /finishMat\(fin, hw \* 2 \/ U \* 2, hd \* 2 \/ U \* 2\)/.test(fn('simYard')));
ok('the yard mast heads carry a real light, not only an emissive box',
  /new THREE\.PointLight\(0xffe9c8, lampCd\(2\.6, 8\.7, 1\.35\)/.test(fn('simYard'))
  && /ml\.visible = qLevel !== 'low';/.test(fn('simYard')));
ok('the one indoor seat floors and lights its shop bay the same way, without '
  + 'borrowing the outdoor fence',
  /const yard = D\.sims\.sims\['overhead-crane'\]\.yard;/.test(src)
  && /const hb = new THREE\.PointLight\(0xffe9c8, lampCd\(2\.4,/.test(src));
ok('a restoration walk lays the ground its site names, not one grass pad for all',
  /const gid = site\.ground \?\? 'grass';/.test(fn('buildRestoGround'))
  && /groundMat\(gid\)/.test(fn('buildRestoGround')));
ok('a restoration walk names the organisation whose site it is, at the entry',
  /const entry = label\(site\.org, site\.category/.test(fn('buildRestoGround')));

/* Lights are torn down like label sprites are: out of the list, not just out
   of the scene. A list the quality ladder walks that keeps every light every
   torn-down hall and sim yard ever built grows without bound and re-shows
   lights that are no longer in the scene. */
ok('disposeOf() prunes a light out of roomLights and disposes it, the same '
  + 'way it prunes a label sprite out of labelSet',
  /if \(o\.isLight\) \{/.test(fn('disposeOf'))
  && /roomLights\.splice\(li, 1\)/.test(fn('disposeOf')));

/* The refused pointer lock: enterWalk() disables the orbit controls BEFORE it
   asks, and neither the lock nor the unlock event fires on a refusal, so
   nothing was left able to put them back. Both the synchronous throw and the
   pointerlockerror event now land on one idempotent recovery. */
ok('a refused pointer lock is caught, not thrown, on both paths',
  /try \{ plc\.lock\(\); \} catch \(err\) \{ walkRefused\(err\); \}/.test(src)
  && /document\.addEventListener\('pointerlockerror'/.test(src));
ok('the recovery puts back exactly what enterWalk took away, and says so',
  /controls\.enabled = true;/.test(fn('walkRefused'))
  && /t\('hint\.walkRefused'\)/.test(fn('walkRefused')));

/* A panel that cannot answer says why. Both of these read a field off an
   undefined record and threw a raw TypeError: every candidate id is stale now
   that the ten-campus target is met, and a walkaround has no seat to check
   when no simulator is running. */
ok('the candidate and walkaround panels refuse with a reason instead of throwing',
  /function refusePanel\(why\)/.test(src)
  && /if \(!def\) return refusePanel\(/.test(fn('openWa'))
  && /if \(!c\) \{/.test(fn('openCandidate')));

/* ------------------------------------------------------- built fabric --- */
ok('a building wears its CAMPUS fabric, not one page-wide wall material',
  /const fab = fabricOf\(campusKey\);/.test(fn('building'))
  && /box\(wid, hgt, dep, fab\.wall, 0, hgt \/ 2, 0, g\)/.test(fn('building'))
  && /add\(fab\.roof,/.test(fn('building'))
  && /add\(fab\.trim,/.test(fn('building')));
/* This check used to assert the opposite: that a `?? fabric.roof ?? 'flat'`
   chain followed STYLE_OF, described as "the city breaks the tie". The kit/
   pack, reading this file, computed that STYLE_OF already names all eight
   districts the union registry declares - so NEITHER arm could ever fire.
   It was dead code, and the comment beside it described a case that does
   not occur, which is worse than no comment: it tells the next reader the
   fallback matters. */
ok('the district decides the roofline outright - there is no tie to break, '
  + 'because STYLE_OF covers every district and the build proves it',
  /const style = STYLE_OF\[k\];/.test(src)
  && /if \(!style\) throw new Error\('no roofline style for district ' \+ k\)/.test(src)
  && !/STYLE_OF\[k\] \?\?/.test(code)
  && /assert _styled == set\(districts_reg\)/.test(src));
ok('a campus with no built fabric breaks the build instead of quietly '
  + 'wearing the flagship\'s livery - the fallback constant was a second '
  + 'copy of treasure-island\'s five drawn fields AND it failed open',
  // matched against the JS DECLARATION, not the bare name: the build-time
  // gate that forbids the constant is Python, `code` only strips JavaScript
  // comments, and so the check was matching the very line that exists to
  // prevent what it was checking for. Third time this shape has bitten -
  // the `ontouchstart` count and the old sun vector were the first two.
  // The DECLARATION with its brace. Matching the bare name matched the
  // build-time gate that forbids it - the gate is Python, `code` strips
  // only JavaScript comments, so the check kept finding the very line
  // written to prevent what it was checking for. Third time this shape has
  // bitten: the `ontouchstart` count and the old sun vector were the first
  // two. The gate itself is asserted separately, below.
  !/const FABRIC_FALLBACK = \{/.test(code)
  && /assert 'const FABRIC_FALLBACK' not in page/.test(src)
  && /const fab = D\.world\.fabric;/.test(fn('fabricOf'))
  && /throw new Error\('no built fabric for campus '/.test(fn('fabricOf'))
  && /_nofab = sorted\(set\(campuses_reg\) - set\(_fab\)\)/.test(src));
/* Seven of the ten campuses are hubs with no halls, so the fabric would have
   dressed nothing there. The chapter hall is the one building they have. */
ok('a hub\'s chapter hall wears the same three fabric materials',
  /const fab = fabricOf\(key\);/.test(fn('buildChapterHall'))
  && /CylinderGeometry\(5\.6, 6, 4\.2, 8\), fab\.wall/.test(fn('buildChapterHall'))
  && /CylinderGeometry\(5\.75, 5\.75, \.5, 8\), fab\.trim/.test(fn('buildChapterHall'))
  && /ConeGeometry\(7\.2, 2\.6, 8\), fab\.roof/.test(fn('buildChapterHall')));
ok('the city layer no longer paints real places from a rainbow keyed on '
  + 'their index',
  !/const hues = \[42, 152, 205, 268, 20, 96, 330\]/.test(src)
  && /const baseHSL = new THREE\.Color\(fabCity\.spec\.facade_color\)/.test(fn('buildCity')));
/* This check used to assert the OPPOSITE, and it was wrong to. It read
   "an absent fabric table degrades to a fallback instead of throwing", and
   it held the page to a three-level chain - `D.world.fabric ?? {}`, then
   `fab[ck] ?? fab['treasure-island'] ?? FABRIC_FALLBACK`.

   Reading through an absent table IS the fault it was written after, and
   guarding the read was right. Choosing the flagship's livery as the answer
   was not. Ten campuses told apart by their built fabric is the whole point
   of that registry, so a campus whose row went missing did not break - it
   quietly wore Treasure Island's colours on every building and looked
   entirely fine. A defect that looks fine is the one nobody finds.

   The guard stays, as a throw. The build gates every campus on having a
   row, so the throw is unreachable unless the payload and the registry come
   apart - which is exactly the fault this function shipped with once. */
ok('an absent fabric row BREAKS the build rather than quietly borrowing the '
  + 'flagship\'s livery - the read is still guarded, the answer is not a '
  + 'default',
  /const fab = D\.world\.fabric;/.test(fnCode('fabricOf'))
  && /const f = fab\?\.\[ck\];/.test(fnCode('fabricOf'))
  && !/fab\['treasure-island'\]/.test(fnCode('fabricOf'))
  && /throw new Error\('no built fabric for campus '/.test(fnCode('fabricOf')));
ok('the per-campus fabric materials are dropped when the campus is',
  /fabMats = null; fabKey = null;/.test(fn('buildCampus')));

/* -------------------------------------------- the campus training yard --- */
/* Simulation used to be reachable only through a panel - enter a hall, open
   its list, click a seat - so the seats were never anywhere. These hold the
   yard to the two things that make it honest rather than decorative: it
   draws only where a campus has home halls, and entering a stand starts the
   run against a hall that actually teaches that seat. */
ok('the yard is built from the sims registry\'s own bindings for THIS campus',
  /const halls = new Set\(D\.campuses\[campusKey\]\?\.halls \?\? \[\]\);/.test(fn('buildTrainingYard'))
  && /D\.sims\.bindings\[sg\] \?\? \[\]/.test(fn('buildTrainingYard')));
ok('a hub draws no yard: no home halls, and a chapter seat is a roster, not a place',
  /if \(!halls\.size\) return;/.test(fn('buildTrainingYard')));
ok('each stand is paved in that seat\'s own declared floor, not one apron for all',
  /const padFin = D\.finCat\[def\.yard\.surface\];/.test(fn('buildTrainingYard'))
  && /finishMat\(padFin,/.test(fn('buildTrainingYard')));
ok('walking into a stand starts the seat against a hall on THIS campus that '
  + 'teaches it, and refuses rather than starting an unbound run',
  /const hall = def\.halls\.find\(\(sg\) => here\.has\(sg\)\);/.test(fn('enterSeatFromYard'))
  && /if \(!hall\) \{/.test(fn('enterSeatFromYard'))
  && /return refusePanel\(/.test(fn('enterSeatFromYard')));
ok('a seat stand is a nearer target than a hall door, so it is tested first',
  /if \(bs && sd < 6\) \{/.test(src)
  && /nearSeat = bs\.userData\.seat; nearSlug = nearPoi = null;/.test(src));
ok('the yard mast light rides the quality ladder like every other',
  /ml\.visible = qLevel !== 'low';/.test(fn('buildTrainingYard')));

/* ------------------------------------------- the board and the streets --- */
/* The network board is the first thing anybody sees, and every plate on it
   was the same pale disc of mat.land - ten places drawn identically, seven
   of them (the hubs, which host no districts) completely bare. */
ok('a region plate wears its own campus ground on top and its own trim on the rim',
  /const atm = D\.world\.atmos\[key\];/.test(fn('buildRegion'))
  && /groundMat\(atm\?\.ground \?\? 'concrete', undefined, 10\)/.test(fn('buildRegion'))
  && /new THREE\.Color\(fabR\?\.trim \?\? '#9db2b8'\)/.test(fn('buildRegion')));
ok('a hub plate is no longer bare: it carries the one building a hub has, '
  + 'in that hub\'s own fabric',
  /if \(!camp\.districts\.length\) \{/.test(fn('buildRegion'))
  && /new THREE\.Color\(f2\.facade_color\)/.test(fn('buildRegion'))
  && /new THREE\.Color\(f2\.roof_color\)/.test(fn('buildRegion')));
/* Streets were one flat grey on all ten campuses whatever the ground was. */
ok('a campus paves its streets in its own declared ground, and never in grass '
  + 'or sand - those fall back to the shared asphalt',
  /function roadMatOf\(ck\)/.test(src)
  && /\(g === 'grass' \|\| g === 'sand' \|\| !g\)\s*\?\s*mat\.road/.test(fn('roadMatOf'))
  && /groundMat\(g, 0xb9c0c2, 16\)/.test(fn('roadMatOf')));
ok('the carriageway is built with the campus fabric and freed with it',
  /road: roadMatOf\(ck\),/.test(fn('fabricOf'))
  && /fabricOf\(campusKey\)\.road/.test(src));

/* ----------------------------------------------------- luminaire units --- */
/* three.js r155 flipped `useLegacyLights` to false and r160 dropped the
   legacy path, so a PointLight's intensity is CANDELA and falls off as
   I / r^decay. Every luminaire here was first written with legacy-scale
   numbers (0.5 - 2.6), which at a 2.7 m ceiling or an 8.7 m mast head is
   indistinguishable from no light at all - measured on a hall interior, cranking them 60x lifted the frame from near-black to readable. The exact pair was written down twice and the two records disagree - 46 to 96 in this file, 46 to 89 in the suite beside it - and the frame that would settle which is right is gone. So neither number is quoted as measured any more: what survives the disagreement is the direction and the order of magnitude, and a check now holds the two files to the same sentence so they cannot drift apart again unnoticed.
   They were real lights and they did vary with the registry's lux; they
   simply were not lighting anything, which is the same near-miss as an
   emissive box that only looks like a lamp, in different clothes.

   So: every point light in this page goes through the one conversion. A new
   one written with a legacy-scale number fails here rather than shipping
   dark. */
ok('there is one candela conversion, and it states the height it converts for',
  /const LAMP_K = 11;/.test(src)
  && /const lampCd = \(rel, height_m, decay\) =>/.test(src));
{
  const pls = [...src.matchAll(/new THREE\.PointLight\(([^;]*?)\)/gs)]
    .map((m) => m[1].replace(/\s+/g, ' ').trim());
  ok(`every point light (${pls.length}) takes its intensity from lampCd, not a bare number`,
    pls.length >= 4 && pls.every((a) => /lampCd\(/.test(a)));
}
/* And the thing the conversion must not break: a brighter room stays
   brighter. The lux ratio is the fact; the candela is only how it is
   delivered. */
ok('the room luminaire still scales with the room\'s own lux record',
  /lampCd\(\.55 \+ luxN \* 1\.45, 2\.32, 1\.7\)/.test(src)
  && /const luxN = Math\.max\(0, Math\.min\(1, \(rc\.lux - 200\) \/ 800\)\);/.test(src));
/* A seat is entered from a hall and inherits that campus's sky, and every
   campus here is authored at dusk or under a marine layer - so a yard needs
   its own working light or the machine, the surface and the gauges are all
   in the dark. */
ok('a simulator yard carries its own working light, not just the campus sun',
  /const yardHemi = new THREE\.HemisphereLight\(/.test(fn('simYard'))
  && /roomLights\.push\(yardHemi\)/.test(fn('simYard')));

/* ------------------------------------------------ the room-light budget --- */
/* A hall carries one point light per room and a walker stands in one room.
   A forward renderer pays for every light in range on every fragment, and
   measured on this page with the camera inside the ironworkers hall,
   everything else held constant:

     11 room lights lit   1.24 fps      (software raster - read the ratio)
      4 lit               1.64 fps      +32%
      0 lit               2.06 fps      +66%

   So the nearest few are lit and the rest are doused. These hold the parts
   that make that safe rather than merely cheaper. */
ok('only the hall\'s own room lights are culled - a yard\'s rig is its whole '
  + 'lighting and is left alone',
  /rl\.userData\.roomLight = true;/.test(src)
  && /if \(!l\.userData\?\.roomLight\) continue;/.test(fn('roomLitStep')));
ok('the culler defers to the quality ladder rather than fighting it',
  /if \(qLevel === 'low'\) return;/.test(fn('roomLitStep')));
ok('it re-evaluates on movement, not on every frame',
  /_rlEye\.distanceToSquared\(_rlLastEye\) < 2\.25/.test(fn('roomLitStep'))
  && /roomLitStep\(\);/.test(src));
/* Two ways the lit set could get stuck: a new hall built under a camera
   that has not moved, and the ladder stepping back UP (which relights all
   eleven and would leave them lit if nothing re-ran the choice). */
ok('a freshly built hall re-evaluates even from a still camera',
  /_rlDirty = true;\s*\/\/ a new hall re-evaluates/.test(src));
ok('stepping the quality ladder back up hands the choice to the culler '
  + 'rather than leaving all eleven lit',
  /for \(const rl of roomLights\) rl\.visible = l !== 'low';\s*\n\s*_rlDirty = true;/.test(src));
ok('a hall never lights more rooms than the budget allows',
  /const ROOM_LIT_MAX = 4;/.test(src)
  && /room\[i\]\[1\]\.visible = i < ROOM_LIT_MAX;/.test(fn('roomLitStep')));
ok('the culler allocates nothing per frame beyond its own sort: the eye and '
  + 'position vectors are module-scope scratch',
  /const _rlEye = new THREE\.Vector3\(\), _rlPos = new THREE\.Vector3\(\);/.test(src));

/* ------------------------------------------------------- machine drives ---
   The four lever seats used to drive their axes as on/off velocity
   (`if (keys.KeyA) st.slew -= sr * dt;`), so a jib started and stopped
   exactly on the key and a load could only swing from the pendulum, never
   from the operator. forkliftSim already modelled a real drive, so these
   hold the other four to that precedent - and hold the helper itself to
   the one property that makes it a drive rather than a lerp: coming off a
   lever, or reversing through zero, uses the DOWN rate, not the up one. */
ok('the spool helper exists and is a drive, not a lerp: off-lever and '
  + 'through-zero both come down at the down rate',
  /const SPOOL = \{ up: 3\.2, down: 4\.0 \};/.test(src)
  && /const rate = \(want === 0 \|\| want \* cur < 0\) \? sp\.down : sp\.up;/.test(fn('drive'))
  && /Math\.max\(-step, Math\.min\(step, want - cur\)\)/.test(fn('drive')));

/* Each seat: the axis is read into a commanded level, the level is spooled,
   and the MOTION is integrated from the level - never from the key. The
   third of those is the one that matters, so it is asserted per axis. */
const seats = {
  craneSim:         [['cS', 'st.slew += sr * st.cS * dt'],
                     ['cT', 'st.r + tr * st.cT * dt'],
                     ['cH', 'st.h + hr * st.cH * dt']],
  excavatorSim:     [['cS', 'st.slew += sr * st.cS * dt'],
                     ['cR', 'st.r + rr * st.cR * dt'],
                     ['cB', 'st.bh + hr * st.cB * dt']],
  boomLiftSim:      [['cS', 'st.sw += sr * st.cS * dt'],
                     ['cE', 'st.ext + er * st.cE * dt'],
                     ['cQ', 'st.el + qr * st.cQ * dt']],
  overheadCraneSim: [['cX', 'st.bx + br * st.cX * dt'],
                     ['cZ', 'st.tz + tr * st.cZ * dt'],
                     ['cH', 'st.h + hr * st.cH * dt']],
};
for (const [seat, axes] of Object.entries(seats)) {
  const body = fn(seat);
  ok(`${seat}() spools every lever axis and integrates its motion from the `
    + `spooled level, not from the key (${axes.map(([a]) => a).join(', ')})`,
    body.length > 0
    && axes.every(([a, motion]) =>
      new RegExp(`st\\.${a} = drive\\(st\\.${a}, axis\\(`).test(body)
      && body.includes(motion)));
  ok(`${seat}() starts its commanded levels at rest, so a seat re-entered `
    + 'is a machine at idle rather than one still running',
    axes.every(([a]) => new RegExp(`\\b${a}: 0\\b`).test(body)));
}

/* Two places where spooling must NOT quietly undo a safety or a score. */
ok('the boom lift\'s moment limit is folded into the COMMANDED axis, so the '
  + 'boom stops extending at the envelope and still has to spool down off it',
  /st\.cE = drive\(st\.cE, axis\(keys\.KeyS, keys\.KeyW && momentPct\(\) < 100\), dt\);/
    .test(fn('boomLiftSim')));
ok('the overhead crane scores sway against the spooled bridge level rather '
  + 'than the key, so coasting still counts as bridging',
  /const bridging = Math\.abs\(st\.cX\) > \.02;/.test(fn('overheadCraneSim')));
ok('the overhead crane\'s upper limit switch cuts the HOIST-UP command - '
  + 'which is what a limit switch is - while the block still reaches the '
  + 'switch and still trips it',
  /st\.cH = drive\(st\.cH, axis\(keys\.KeyE, keys\.KeyQ && st\.h < LAY\.hook_max - 1e-6\), dt\);/
    .test(fn('overheadCraneSim'))
  && /st\.atLimit = true; st\.limits\+\+;/.test(fn('overheadCraneSim')));

/* ------------------------------------------------------------ the arc ---
   Arc length was scored (the `band` axis) but changed nothing: heat went in
   at the same rate whether the arc was 1 mm or 6 mm, so a long arc cost a
   mark and never a weld. Lack of fusion IS the long-arc defect, so now the
   gap drives the heat. Measured on the built page, torch held still on one
   segment: a 0.5 mm arc burns through in 1.27 s against 1.65 s at the
   band's middle (0.77x); before, the two were 1.70 s and 1.69 s (1.01x). */
ok('the arc-length heat factor is derived from the band\'s own middle rather '
  + 'than a second hard-coded number, and is bounded both ways (the check '
  + 'below is the one that holds it to actually driving the heat)',
  /const mid = \(BAND\[0\] \+ BAND\[1\]\) \/ 2;/.test(fn('weldSim'))
  && /Math\.max\(\.45, Math\.min\(1\.35, 1 \+ \(mid - st\.gap\) \* ARC_HEAT\)\)/
       .test(fn('weldSim')));
ok('the heat and the in-band credit are weighted the SAME way, so the band '
  + 'score stays one honest ratio rather than mixing seconds with heat',
  /const hr = heatRate\(\) \* dt;\s*\n\s*s\.heat \+= hr;\s*\n\s*if \(inBand\(\)\) s\.good \+= hr;/
    .test(fn('weldSim')));

/* A machine with a load in its hand is slower. The factor is one constant
   so the two seats cannot drift apart, and each applies it to the axis that
   actually carries - the crane's hoist, the excavator's stick and boom -
   rather than to everything, which would just be a global slowdown. */
ok('a loaded machine is slower than an empty one, from one shared factor',
  /const LOADED = \.62;/.test(src));
ok('the crane hoists slower on the pick than on the empty hook',
  /hr = 5 \* \(st\.attached \? LOADED : 1\)/.test(fn('craneSim')));
ok('the excavator works its stick and boom slower with a full bucket, and '
  + 'its house slew - which carries no weight out - is left alone',
  /const f = st\.carrying \? LOADED : 1;/.test(fn('excavatorSim'))
  && /const sr = \.5, rr = 3\.4 \* f, hr = 2\.6 \* f;/.test(fn('excavatorSim')));

/* forkliftSim set the precedent and is deliberately left alone; its scripted
   operator steers toward a point, which is a different thing from spooling a
   lever, and used to be called `drive` too - shadowing the helper above. */
ok('forkliftSim() still integrates its own acceleration and steering lerp, '
  + 'untouched by the lever drive',
  /st\.v \+= /.test(fn('forkliftSim')));
ok('the scripted operator\'s steer-to-a-point helper no longer shadows the '
  + 'lever drive',
  /const steerTo = \(px, pz, vWant\) => \{/.test(src)
  && !/const drive = \(/.test(src));

/* ----------------------------------------------------------- the walker ---
   The walker was a hovercraft. It reached full speed on the first frame and
   stopped dead on the last; it was 41% faster on the diagonal, because two
   full-speed vectors were added together rather than a command landing on
   the unit circle; "walking" was 5 m/s, which is 18 km/h, and Shift made it
   10 m/s, which is faster than any human has run. Measured with the page's
   own fixed-step walk probe, before and after:

                            before      after
     walking                5.00 m/s    1.67 m/s
     diagonal / straight    1.414       1.005
     running                9.69 m/s    4.91 m/s
     back-pedal             5.00 m/s    1.04 m/s   (6.79 with Shift, now none)
     0.25 s from a stop     1.25 m      0.31 m

   These hold the four facts that produced those numbers. */
const walk = fn('walkStep');
ok('a corner is not a speed-up: the walk command lands on the unit circle '
  + 'before it is spooled, rather than two full-speed vectors being added',
  /const m = Math\.hypot\(fwd, str\);/.test(walk)
  && /wkF = drive\(wkF, m \? fwd \/ m : 0, dt, WALK_SPOOL\);/.test(walk)
  && /wkS = drive\(wkS, m \? str \/ m : 0, dt, WALK_SPOOL\);/.test(walk));
ok('the walker leans into a stride and settles out of one, on the same drive '
  + 'the machines use, with a body\'s rates rather than a hydraulic drive\'s',
  /const WALK_SPOOL = \{ up: 6\.5, down: 9\.5 \};/.test(src)
  && /function drive\(/.test(src));
ok('the speeds are speeds a person moves at: a brisk walk, a real run, and '
  + 'a back-pedal that Shift cannot turn into a reverse sprint',
  /const WALK_MS = 1\.7, RUN_MS = 5\.0, EYE_H = 1\.7, BACK_FRAC = \.62;/.test(src)
  && /const fTop = wkF >= 0 \? top : WALK_MS \* BACK_FRAC;/.test(walk));
ok('the head rides the stride rather than a clock: the bob and the footfalls '
  + 'come off one phase, whose cadence is the speed actually travelled',
  /rig\.y = EYE_H \+ strideStep\(Math\.hypot\(wkF \* fTop, wkS \* top\), dt\);/.test(walk)
  && /wkPhase \+= \(speed \/ stepM\) \* Math\.PI \* dt;/.test(fn('strideStep'))
  && /if \(foot !== wkFoot\) \{ wkFoot = foot; if \(!wkSilent\) footfall\(speed \/ RUN_MS\); \}/
       .test(fn('strideStep')));
ok('standing still is standing still: the stride resets rather than drifting '
  + 'on, so the first step after a stop is a first step',
  /if \(speed < \.12\) \{ wkPhase = 0; return 0; \}/.test(fn('strideStep')));

/* ---------------------------------------------------------- the footfall ---
   What you are standing on is already known - the surfaces registry names a
   room's floor and the world registry names a ground - so a footstep reads
   it rather than restating it. The timbre itself lives once, per step
   family, in the build, which asserts that every floor pattern and every
   ground recipe maps to one (and that no family is declared unreachable). */
ok('a footstep reads the floor the registries already named: the room\'s own '
  + 'finish indoors, the site\'s or the campus\'s ground recipe outdoors',
  /return famOfFinish\(D\.finCat\[D\.finishes\[slug\]\[curRoom\.strand\]\.surface\]\);/
    .test(fn('stepFamily'))
  && /\? \(curRestoSite\?\.ground \?\? 'grass'\)/.test(fn('stepFamily'))
  && /: \(ATMOS\[campusKey\] \?\? DEF_ATMOS\)\.ground;/.test(fn('stepFamily')));
ok('the step families are the one place a timbre is written, and the page '
  + 'reads them from the payload rather than carrying a second copy',
  /const k = D\.step\.fam\[stepFamily\(\)\];/.test(fn('footfall'))
  && !/STEP_FAMILIES/.test(src.slice(src.indexOf('<script'))));
ok('a footstep is synthesised in the browser from filtered noise, like every '
  + 'other sound on this page - no recording of a real floor is loaded',
  /const buf = ac\.createBuffer\(1, n, ac\.sampleRate\);/.test(fn('footfall'))
  && /f\.type = 'bandpass'; f\.frequency\.value = k\.f; f\.Q\.value = k\.q;/
       .test(fn('footfall'))
  && !/new Audio\(|\.mp3|\.wav|\.ogg/.test(src));
ok('the families that ring get a ring, and the ones that do not are not '
  + 'paying for an oscillator they never hear',
  /if \(k\.ring > 0\) \{/.test(fn('footfall')));
ok('no two steps are identical - a real gait is not a metronome',
  /\(\.86 \+ Math\.random\(\) \* \.28\)/.test(fn('footfall')));
ok('a probe silences the footfalls it drives: hundreds of thousands of '
  + 'steps must not move the page being measured, or make it scream',
  /let wkSilent = false;/.test(src)
  && /if \(foot !== wkFoot\) \{ wkFoot = foot; if \(!wkSilent\) footfall\(speed \/ RUN_MS\); \}/
       .test(fn('strideStep'))
  // every probe that drives walkStep in a loop silences it and restores it:
  // the walk probe, the campus solidity test and the hall test
  && (() => {
    const drivers = (src.match(/window\.__tc3d(WalkProbe|SolidTest|HallTest)\b/g)
                     ?? []).length;
    const on = (src.match(/const wasSilent = wkSilent; wkSilent = true;/g) ?? []).length;
    const off = (src.match(/wkSilent = wasSilent;/g) ?? []).length;
    return drivers === 3 && on === 3 && off === 3;
  })());
ok('the walk probe leaves the page exactly as it found it, so measuring the '
  + 'walker cannot move it',
  /xrRig\.position\.copy\(p0\);/.test(src)
  && /wkF = wasF; wkS = wasS; wkPhase = wasPhase; wkFoot = wasFoot;/.test(src));

/* ---------------------------------------------------------- solid halls ---
   The campus stroll walked straight through the buildings, which is the
   single loudest way a walkable world tells you it is not one. Measured
   with the page's own solidity test - 72 headings out of the plaza, 200 s
   of walking each, 864,000 fixed steps, asking after every one whether the
   walker is inside a footprint:

                       before     after
     steps inside      14,370     0
     contact steps     17,105     52,708
     headings that
       met a wall      17 of 72   17 of 72

   Same headings meet a wall either way; the difference is that the walker
   now rests against it instead of passing through it. */
const solid = fn('pushOutOfSolids');
ok('the walker is kept out of the SAME footprints the road layout is already '
  + 'checked against - there is no second copy of where a building is',
  /solids\.push\(\{ cx: rad\.x \* R, cz: rad\.y \* R,/.test(src)
  && /for \(const r of roads\) for \(const b of rects\) \{/.test(src)
  && /rects \}\);/.test(src));
ok('a district is turned to face the plaza, so the walker is carried into '
  + 'its frame and back rather than its footprints being flattened',
  /let u = dx \* d\.cos - dz \* d\.sin;/.test(solid)
  && /rig\.x = d\.cx \+ u \* d\.cos \+ v \* d\.sin;/.test(solid)
  && /rig\.z = d\.cz - u \* d\.sin \+ v \* d\.cos;/.test(solid));
ok('a wall is slid along, not stuck to: the push is along the axis the '
  + 'walker is least far into',
  /if \(ou < ov\) u = b\.u \+ \(u >= b\.u \? 1 : -1\) \* \(b\.hw \+ BODY_R\);/.test(solid)
  && /else v = b\.v \+ \(v >= b\.v \? 1 : -1\) \* \(b\.hd \+ BODY_R\);/.test(solid));
ok('a stroll tests the three districts before it tests the hundred halls',
  /if \(dx \* dx \+ dz \* dz > d\.reach \* d\.reach\) continue;/.test(solid));
ok('the walker has a body rather than being a point on the floor',
  /const BODY_R = \.45;/.test(src));
ok('the collision runs on the campus stroll, where the buildings are - the '
  + 'hall interior and a restoration site have their own bounds',
  /pushOutOfSolids\(rig\);\s*\n\s*const len = Math\.hypot\(rig\.x, rig\.z\);/.test(walk));
ok('the solidity test reads the footprints the collision itself uses, so '
  + 'the two cannot disagree about where a hall is',
  /const probe = \(x, z, pad\) => \{[\s\S]*?for \(const d of solids\) \{[\s\S]*?for \(const b of d\.rects\)/
    .test(src));
ok('and it leaves the rig and the heading where it found them',
  /xrRig\.position\.copy\(p0\); xrRig\.rotation\.y = r0; wkF = wasF; wkS = wasS;/
    .test(src));

/* -------------------------------------------------- rooms with doorways ---
   Indoors the walker was a ghost: the waist-high partitions and the hall's
   own side walls were scenery, and the walker was held in a box three
   metres wider than the building on each side.

   Giving the partitions substance is only half of it. The rooms tile the
   envelope wall to wall - there is no corridor in this plan - so partitions
   that run solid seal every room. The first attempt cut a centred doorway
   into each of a room's four runs and sealed most of the building, because
   two rooms sharing a boundary each drew their own partition on it and,
   being different widths, put their doorways in different places. A doorway
   belongs to the BOUNDARY between two rooms.

   Measured across all 111 halls (1,221 rooms, 9,069 wall segments): zero
   rooms unreachable on foot from the open front. And on eight halls, 36
   headings out of the doorway, 51,840 fixed steps each:

     steps inside a wall   before 664-1,616    after 0

   Draw calls in the hall interior: 177 before any of this, 213 with the
   doorways unmerged, 139 once each room's segments are merged per material. */
ok('a doorway is cut on the boundary BETWEEN two rooms, over the overlap the '
  + 'two actually share, not into one room\'s own run',
  /function planDoors\(rects, frontZ\) \{/.test(src)
  && /const \[s, e\] = ov\(a\.z0, a\.z1, b\.z0, b\.z1\);/.test(fn('planDoors'))
  && /const \[s, e\] = ov\(a\.x0, a\.x1, b\.x0, b\.x1\);/.test(fn('planDoors')));
ok('the building\'s open front is a way in, so a room\'s frontage onto it is '
  + 'a doorway too - otherwise nothing could be entered at all',
  /if \(Math\.abs\(a\.z0 - frontZ\) < _DEPS\) cut\('z@' \+ a\.z0\.toFixed\(2\), a\.x0, a\.x1\);/
    .test(fn('planDoors')));
ok('the room rectangles are worked out BEFORE anything is drawn, because a '
  + 'doorway cannot be placed while looking at one room',
  /for \(const r of h\.rooms\)\s*\n\s*roomRects\.push\(\{/.test(src)
  && /const doors = planDoors\(roomRects, -DEP \/ 2\);/.test(src));
ok('a run is drawn as itself minus the doorways cut into its line, and the '
  + 'collision records the SAME segments - no opening you can see and '
  + 'cannot use, none you can use and cannot see',
  /for \(const \[c, len\] of runSegments\(doors, 'z@' \+ zz\.toFixed\(2\),/.test(src)
  && /wallRect\(c, zz, len \/ 2, \.06\);/.test(src)
  && /for \(const \[c, len\] of runSegments\(doors, 'x@' \+ xx\.toFixed\(2\),/.test(src)
  && /wallRect\(xx, c, \.06, len \/ 2\);/.test(src));
ok('the hall shell is solid too: its back and both sides are recorded where '
  + 'they are drawn, rather than left as scenery outside the walker\'s box',
  /wallRect\(0, cz\(DEP\), W \/ 2, \.125\);/.test(src)
  && /wallRect\(cx\(0\), 0, \.125, DEP \/ 2\);/.test(src)
  && /wallRect\(cx\(W\), 0, \.125, DEP \/ 2\);/.test(src));
ok('the hall collision runs before the box clamp, which is now only a '
  + 'backstop',
  /pushOutOfSolids\(rig, hallSolids\);\s*\n\s*const DEP = hallRec\.depth \* U;/
    .test(fn('walkStep')));
ok('one push-out serves both the campus and the hall - the campus\'s turned '
  + 'districts and the hall\'s own frame are the same shape of problem',
  /function pushOutOfSolids\(rig, list = solids\) \{\s*\n\s*for \(const d of list\) \{/
    .test(src));
ok('the hall\'s walls live in ONE entry rather than one per rectangle, so a '
  + 'step tests a list and not a hundred lists',
  /if \(!hallSolids\.length\)\s*\n\s*hallSolids\.push\(\{ cx: 0, cz: 0, cos: 1, sin: 0, reach: Infinity, rects: \[\] \}\);/
    .test(fn('wallRect'))
  && /hallSolids\[0\]\.rects\.push\(\{ u: x, v: z, hw, hd \}\);/.test(fn('wallRect')));
ok('a room\'s partition segments are merged per material, so doorways cost '
  + 'fewer draw calls than the solid walls they replaced',
  /const merged = mergeGeometries\(list\);\s*\n\s*list\.forEach\(\(ge\) => ge\.dispose\(\)\);\s*\n\s*const mesh = new THREE\.Mesh\(merged, m2\);\s*\n\s*mesh\.castShadow = true; mesh\.receiveShadow = true;\s*\n\s*if \(m2 === ws\)/
    .test(src));
ok('the hall test proves BOTH halves together - that no body-sized cell is '
  + 'inside a wall, and that every room is still reachable on foot - since '
  + 'substance without doorways would pass the first and fail the second',
  /const unreachable = \[\];/.test(src)
  && /if \(!ok\) unreachable\.push\(r\.label\);/.test(src)
  && /if \(Math\.abs\(x - b\.u\) < b\.hw && Math\.abs\(z - b\.v\) < b\.hd\) \{ breaches\+\+; break; \}/
       .test(src));

/* ------------------------------------------------ what a stand is made of ---
   A training stand wears its seat's own declared yard surface - crushed
   stone under the excavator, an asphalt apron under the crane, a sealed
   slab under the load-chart board - and until now that was a texture you
   could look at and not a surface you could hear. Measured on Treasure
   Island: 4 of its 9 stands sound different from the ground beside them,
   and the other 5 correctly match it, because a sealed slab and a concrete
   campus ARE the same family.

   The roads are deliberately not sampled: a roadway takes the campus's own
   ground recipe unless that ground is grass or sand, and all ten campuses
   are concrete or asphalt, which share a family - so the branch could not
   change the answer on any campus that exists. That is recorded in the
   source as a finding, not left as a silent gap. */
ok('one place turns a built finish into a step family, so a room\'s floor and '
  + 'a stand\'s pad cannot come to disagree about what a slab sounds like',
  /const famOfFinish = \(fin\) => D\.step\.floor\[fin\?\.pattern\] \?\? 'hard';/.test(src)
  && /return famOfFinish\(D\.finCat\[D\.finishes\[slug\]\[curRoom\.strand\]\.surface\]\);/
       .test(fn('stepFamily'))
  && /fam: famOfFinish\(padFin\)/.test(src));
ok('a stand\'s pad is recorded where it is BUILT, carrying the seat\'s own '
  + 'declared yard surface rather than a second copy of it',
  /const padFin = D\.finCat\[def\.yard\.surface\];/.test(fn('buildTrainingYard'))
  && /yardPads\.push\(\{ x: yg\.position\.x \+ sx, z: yg\.position\.z \+ sz,/
       .test(fn('buildTrainingYard')));
ok('on the grounds a stand is checked before the campus ground is assumed',
  /if \(view === 'campus'\)\s*\n\s*for \(const p of yardPads\)/.test(fn('stepFamily')));
ok('the pads are rebuilt with the yard, so a campus cannot inherit the '
  + 'stands of the one before it',
  /seatHits = \[\]; yardPads = \[\];/.test(fn('buildTrainingYard')));
ok('why the roads are not sampled is written down, so it is a finding and '
  + 'not a silent gap',
  /The ROADS are deliberately not sampled, and that is a finding rather/
    .test(fn('stepFamily')));
ok('sampling a point puts the walker back where it was',
  /const ax = xrRig\.position\.x, az = xrRig\.position\.z;[\s\S]*?xrRig\.position\.x = ax; xrRig\.position\.z = az;/
    .test(src));

/* ------------------------------------------------------- things on the ground ---
   The halls were solid but everything else on the grounds was not: the
   chapter hall - a building, and the one building a hub has at all - was a
   drum the walker went straight through, and so were the yard's light
   mast, its perimeter and its stand posts. Indoors the benches were
   ghosts too.

   Measured with the campus solidity test, once its probe was taught about
   discs (before that it only understood rectangles, so it reported nothing
   whatever about the round things - a test that could not fail):

     steps inside a prop    before 15,480    after 0

   And indoors, the benches moved as well as hardened. The comment has
   always said "benched along the back of the room"; the code put them
   0.8 m in from the FRONT, which was harmless while you could walk
   through one and is not now - the front edge is where a room's doorway
   onto the row in front of it is, and a 1.3 m bench across a 1.8 m
   opening closes it. All 111 halls still report zero rooms sealed. */
ok('a round thing is round: a disc is pushed out along its radius rather '
  + 'than squared off onto an axis',
  /if \(b\.r !== undefined\) \{[\s\S]*?const dd = Math\.hypot\(du, dv\);[\s\S]*?u = b\.u \+ du \/ dd \* rr; v = b\.v \+ dv \/ dd \* rr;/
    .test(fn('pushOutOfSolids')));
ok('a walker standing exactly on a post\'s centre still gets out, rather '
  + 'than dividing by a zero distance',
  /if \(dd < 1e-4\) u = b\.u \+ rr;/.test(fn('pushOutOfSolids')));
ok('the chapter hall is a building - the one building a hub has - and is '
  + 'recorded where it is built',
  /campusSolid\(0, 0, 6\);/.test(fn('buildChapterHall')));
ok('the yard\'s mast, its perimeter and its stand posts are solid too, each '
  + 'recorded in the yard\'s own placed frame',
  /campusSolid\(yg\.position\.x, yg\.position\.z - YR \* \.5, \.3\);/
    .test(fn('buildTrainingYard'))
  && /campusSolid\(yg\.position\.x \+ px, yg\.position\.z \+ pz, \.16\);/
       .test(fn('buildTrainingYard'))
  && /campusSolid\(yg\.position\.x \+ sx, yg\.position\.z \+ sz, \.24\);/
       .test(fn('buildTrainingYard')));
ok('the props share one entry with one reach over the lot, so a stroll on '
  + 'the far side of the grounds tests one number instead of forty',
  /e\.reach = Math\.max\(e\.reach, Math\.hypot\(x, z\) \+ r \+ 1\);/.test(fn('campusSolid')));
ok('a bench stands against the room\'s BACK wall, as the comment always '
  + 'said, and in that wall\'s solid pieces - so it can never close a '
  + 'doorway it is standing in front of',
  /const bays = runSegments\(doors, 'z@' \+ \(rz \+ rd \/ 2\)\.toFixed\(2\),/.test(src)
  && /const bz = rz \+ rd\/2 - \.8;/.test(src)
  && /const bx = spots\[fi\] \?\? rx;/.test(src));
ok('and you cannot walk through a bench',
  /wallRect\(bx, bz, \.7, \.4\);/.test(src));
ok('the solidity probe understands both shapes, so it cannot go quiet about '
  + 'the round ones and report a clean sweep it never took',
  /if \(b\.r !== undefined\) \{\s*\n\s*if \(Math\.hypot\(u - b\.u, v - b\.v\) < b\.r \+ pad\) return true;\s*\n\s*\} else if/
    .test(src));

/* ------------------------------------------------------- surface fidelity ---
   Every surface in this world is drawn in the browser onto a canvas, and
   the canvas was 128 square with anisotropy typed as 4 in five separate
   places. 128 was chosen when floors were flat colours; they now carry a
   pattern, a normal map and a grain, and at 128 a bay floor you are
   standing on is mush.

   Measured on the built page, booting straight into a hall and holding
   steady state: 3.56 fps at 128 with anisotropy 4, 3.20 fps at 384 with
   what the GPU offers - a tenth of the frame rate under a software
   rasteriser, for nine times the texture pixels. Draw calls, triangles and
   texture COUNT are unchanged: 139 in the hall, 268 on the campus. */
ok('the surface size rides the quality ladder rather than being one number '
  + 'for a phone and a workstation alike',
  /const SURF_PX = \{ low: 128, high: 384 \};/.test(src)
  && /const surfPx = \(\) => SURF_PX\[qLevel\] \?\? SURF_PX\.low;/.test(src)
  && /const S2 = surfPx\(\);/.test(fn('surfaceMaps')));
ok('the surface cache is keyed on the size, so stepping the ladder cannot '
  + 'hand back a texture built for the other rung',
  /const key = pattern \+ '\|' \+ color \+ '\|' \+ S2;/.test(fn('surfaceMaps')));
ok('the grain is counted per unit AREA: a fixed 260 splats on a 384 canvas '
  + 'is a sprinkle on a field, and grain is most of what stops a floor '
  + 'reading as plastic',
  /const grains = Math\.round\(260 \* \(S2 \/ 128\) \* \(S2 \/ 128\)\);/
    .test(fn('surfaceMaps')));
ok('anisotropy is asked of the machine rather than typed, and is asked in '
  + 'ONE place - it used to be the literal 4 in five of them',
  /const maxAniso = renderer\.capabilities\.getMaxAnisotropy\(\);/.test(src)
  && !/anisotropy = 4\b/.test(src)
  && (src.match(/anisotropy = anisoNow\(\)/g) ?? []).length >= 5);
ok('and it rides the same ladder, because a machine that cannot afford the '
  + 'pixels cannot afford to filter them either',
  /const anisoNow = \(\) => qLevel === 'low' \? Math\.min\(4, maxAniso\) : maxAniso;/
    .test(src));
ok('what the ladder does NOT do is written down: a texture already on the '
  + 'GPU is not rebuilt when the rung changes',
  /A texture ALREADY on the GPU is not\s*\n\s*rebuilt when the ladder steps/.test(src));

/* ------------------------------------------------------------ wet ground ---
   The world pack declares a `wet` figure per weather - 0 clear, .12
   overcast, .4 fog, .85 rain, 1 storm - and nothing read it, so the rain
   state's own line about "every surface in the yard reading differently"
   was a promise the render did not keep. A wet surface is smoother and
   darker; now that the sky lights the world, dropping roughness buys a
   reflection rather than a flatter grey. Measured on the built page:

     clear     roughness 0.970   #8f9698
     overcast            0.918   #8c9395
     fog                 0.795   #868c8e
     rain                0.599   #7a8082
     storm               0.533   #757c7e

   Fog wets a yard with no rain falling, which is why `wet` is its own
   figure in the registry and not a function of the rain rate. */
ok('the weather\'s declared wetness reaches the ground, rather than being a '
  + 'figure the registry ships and nothing reads',
  /const k = w\.wet \?\? 0;/.test(fn('wetGround'))
  && /m\.roughness = m\.userData\.dryRough \* \(1 - \.45 \* k\);/.test(fn('wetGround'))
  && /wetGround\(\);\s*\/\/ the yard takes the weather/.test(src));
ok('the DRY values are remembered once, so repeated weather changes tone '
  + 'from the surface\'s own colour instead of compounding on the last wet',
  /if \(m\.userData\.dryRough === undefined\) \{/.test(fn('wetGround'))
  && /m\.color\.setHex\(m\.userData\.dryColor\)\.lerp\(_wetTint, \.38 \* k\);/
       .test(fn('wetGround')));
ok('only the material is re-toned, never the texture: the maps are cached '
  + 'and the live mesh must not be rebuilt to change the weather',
  !/groundMat\(/.test(fn('wetGround')));

/* ------------------------------------------------------- indoors is indoors ---
   A hall is an open-topped box - a back wall, two side walls, roof
   trusses and no deck - so once the sky became an environment map, every
   room surface was lit by the full outdoor sky on top of the hemisphere,
   the sun and the cool fill: four unoccluded outdoor sources.

   Be exact about what this bought, because it is less than it sounds.
   Cutting the environment map alone moved the bright-room-to-dim-room
   ratio from 1.249 to 1.250 - nothing, because it was one source of four.
   Stepping the whole outdoor rig back indoors as well took it to 1.254.
   Then sampling the FLOOR rather than the whole frame (which includes the
   sky above an open hall, the far rooms and the walls, all compressed by
   ACES) showed the honest number: 1.005 before, 1.012 after, against a
   registry that asks for 3.33.

   So this reduces the outdoor wash indoors, which is right in itself and
   costs nothing - and it does NOT make the per-room lux figures read in
   the render. That remains open, and is written down here rather than
   left as an unexplained gap. */
ok('an indoor surface sees a fraction of the sky, declared once and used '
  + 'by both factories that build a room surface',
  /const INDOOR_ENV = \.3;/.test(src)
  && (src.match(/envMapIntensity: INDOOR_ENV/g) ?? []).length === 2);
ok('and the rest of the outdoor rig steps back with it - the hemisphere '
  + 'moved into applyPhase() when the hour got the last word on it, and '
  + 'the step-back had to move WITH it or a hall would be lit outdoors',
  /const INDOOR_RIG = \.35;/.test(src)
  // the fill stays where the atmosphere is written; the hemisphere is now
  // the hour's, so it takes its own `indoors` from the same rule
  && /const indoors = view === 'hall' \? INDOOR_RIG : 1;/.test(fn('applyAtmos'))
  && /fill\.intensity = FILL_I \* indoors;/.test(fn('applyAtmos'))
  && /const indoors = view === 'hall' \? INDOOR_RIG : 1;/.test(fn('applyPhase'))
  && /hemi\.intensity = a\.hemi\.i \* w\.hemi_mul \* indoors \* eff\.hemi\.intensity_mul;/
     .test(fn('applyPhase'))
  // and nothing downstream may write either intensity back
  && !/hemi\.intensity = a\.hemi\.i \* w\.hemi_mul \* indoors;/.test(fn('applyAtmos')));
ok('the fill\'s own strength is declared once rather than typed at its '
  + 'construction and again wherever it is re-set',
  /const FILL_I = \.25;/.test(src)
  && /new THREE\.DirectionalLight\(0x41C4D4, FILL_I\)/.test(src));
ok('what this did NOT achieve is written down: the per-room lux figures '
  + 'still do not read in the render, measured at 1.012 against 3.33',
  /it does NOT make the per-room lux figures read/.test(src)
  || /1\.005 before, 1\.012 after/.test(src));
ok('a probe can stand the eye somewhere, because reaching for the camera '
  + 'as a global silently measures the view it was already looking at',
  /window\.__tc3dLook = \(x, y, z, tx, ty, tz\) => \{/.test(src)
  && /camera\.updateMatrixWorld\(true\);/.test(src));


/* ---------------------------------------------------------- sun frustum --- */
// Measured before the fix: the sun's shadow box was a fixed +/-60 in light
// space nailed to the world origin, covering x in [-112.8, 104.4] and z in
// [-99.6, 94.7] against shadow casters spanning 307.8 m - 47% of the campus,
// in the same place no matter where you stood, with a hard line at the edge.
// Measured after: 100% from the opening orbit, and on foot the box rides with
// the view at 6.8 cm per texel against the old box's 10.6. These hold the
// three things that silently un-do it.
ok('the sun\'s shadow box is sized inside trackSun(), not nailed to a constant '
  + 'half-extent at the world origin',
  /function trackSun\(\) \{/.test(src)
  && /Object\.assign\(key\.shadow\.camera, \{ left: -R, right: R, top: R, bottom: -R,/
     .test(fn('trackSun'))
  && !/const S = 60;/.test(src));
ok('key.target is IN the scene graph - three.js leaves a directional light\'s '
  + 'default target outside it, where moving it does nothing at all',
  /scene\.add\(key\.target\);/.test(src));
ok('trackSun() updates the target\'s world matrix after moving it, because a '
  + 'light aimed through a stale matrix points where it used to',
  /key\.target\.updateMatrixWorld\(true\);/.test(fn('trackSun')));
ok('the box is aimed at the ground under the view, not at the eye: from the '
  + 'opening orbit 225 m up, an eye-centred box holds no ground at all',
  /_sunFocus\.copy\(_sunEye\)\.addScaledVector\(_sunDir, reach\);/.test(fn('trackSun'))
  && /_sunFocus\.y = 0;/.test(fn('trackSun')));
ok('the box centre is snapped to whole shadow texels, or every shadow edge in '
  + 'the scene crawls as the box slides under it',
  /const texel = \(R \* 2\) \/ key\.shadow\.mapSize\.x;/.test(fn('trackSun'))
  && /Math\.round\(_sunFocus\.dot\(SUN_RIGHT\) \/ texel\) \* texel/.test(fn('trackSun')));
ok('the radius is quantised before it is used, so the texel grid the snap '
  + 'depends on does not itself move every frame',
  /const SUN_R_STEP = 10;/.test(src)
  && /Math\.round\(want \/ SUN_R_STEP\) \* SUN_R_STEP/.test(fn('trackSun')));
ok('trackSun() runs after everything that can move the camera and before the '
  + 'frame is drawn, not at the top of the loop a frame behind it',
  /\n  trackSun\(\);\n  xrRender\(\);/.test(src));
ok('trackSun() is never called at module top level: walkActive is a `let` '
  + 'declared further down, so an eager call throws on its temporal dead zone',
  !/\n(?:const [A-Za-z_]+ = )?trackSun\(\);\n(?!  )/.test(src.replace(/\n  trackSun\(\);/g, '')));
ok('a probe can ask what the sun can actually reach - the half-extent it '
  + 'renders with, the texel that buys, and how much of the campus is inside',
  /window\.__tc3dShadowBox = \(\) => \{/.test(src)
  && /r: sunR, texelCm:/.test(src)
  && /focusCovered: box\.containsPoint/.test(src));


/* -------------------------------------------- the guide, voice, hands --- */
// Driven in a browser before these were written: the six asks render and
// answer for all ten places, a running seat's control rows come back
// verbatim from sims/, both voice switches start off and write nothing to
// localStorage until clicked, and the gesture recogniser reads 13 synthetic
// hand positions the way the registry declares - band in both directions,
// and an untracked hand reading as no gesture. These hold the source to it.
ok('the guide routes view -> place by INVERTING each place\'s own view field, '
  + 'not by a second table that would disagree the first time one is renamed',
  /for \(const \[id, pl\] of Object\.entries\(G\.places\)\) if \(pl\.view\) GUIDE_OF_VIEW\[pl\.view\] = id;/
    .test(src));
ok('the panel stays on the place it rendered: the ask buttons read '
  + 'guidePlaceId, not the view behind the panel',
  /let guidePlaceId = null, guideAskId = null/.test(src)
  && /guideRender\(guidePlaceId, a\.dataset\.guideAsk\)/.test(src)
  && !/guideRender\(guidePlaceNow\(\), a\.dataset/.test(src));
ok('a running seat\'s controls are RESOLVED against D.sims.sims[curSimId] at '
  + 'the moment you ask, never copied into the guide registry',
  /if \(id === 'seat:running'\)/.test(fn('guideScheme'))
  && /D\.sims\.sims\[curSimId\]/.test(fn('guideScheme'))
  && /sm\.controls\.map\(\(c\) => \(\{ input: c\.keys, does: c\.action \}\)\)/.test(fn('guideScheme')));
{
  // scoped to what the guide itself renders: the page has read-only
  // textareas elsewhere (the save slot, the orbis payload), and a check
  // that swept the whole file would be answering about those instead
  const guideMarkup = fn('guideRender') + fn('guideVoiceBox') + fn('guideRows')
    + fn('guideHandsBox');
  ok('the guide accepts no free text - the six asks are the whole surface, '
    + 'because nothing behind it could answer free text',
    !/<textarea|contenteditable|type="text"|type="search"/.test(guideMarkup)
    && (guideMarkup.match(/<input /g) || []).length === 1
    && /<input type="checkbox" data-guide-voice=/.test(guideMarkup));
}
ok('a voice switch is OFF unless localStorage says exactly \'1\': an absent '
  + 'key, a blocked store and a thrown read all come back off',
  /const vOn = \(k\) => \{ try \{ return localStorage\.getItem\(k\) === '1'; \}\s*\n\s*catch \(e\) \{ return false; \} \};/
    .test(src));
ok('the recogniser constructor is whichever name the browser offers, and '
  + 'null when it offers neither - the control is then absent, not degraded',
  /const SR = window\.SpeechRecognition \?\? window\.webkitSpeechRecognition \?\? null;/.test(src)
  && /const have = id === 'ask_by_voice' \? !!SR : !!synth;/.test(src));
ok('speech-to-text asks to recognise on the device where that is offered, '
  + 'and FAILS CLOSED on a missing language pack rather than retrying '
  + 'through the browser vendor\'s service with the audio it was given',
  /typeof SR\.availableOnDevice === 'function'/.test(fn('guideListen'))
  && /r\.processLocally = true;/.test(fn('guideListen'))
  && /e\?\.error === 'language-not-supported'/.test(fn('guideListen'))
  && /does not fall back to the vendor service/.test(fn('guideListen')));
ok('a network-only voice is disclosed BEFORE it speaks, not after: the '
  + 'guide prefers a localService voice and says when there is none',
  /pool\.find\(\(v\) => v\.localService\) \?\? pool\[0\]/.test(fn('guideVoice'))
  && /if \(v && !v\.localService\)/.test(fn('guideVoiceBox')));
ok('the guide button survives a panel: the whole bar rises over the scrim '
  + 'and everything on it except the guide is deadened',
  /body\.open #bar\{z-index:12\}/.test(src)
  && /body\.open #bar > \*:not\(#guideBtn\)\{pointer-events:none;opacity:\.3\}/.test(src));
ok('a hand gesture holds on a LOOSER number than it fires on - one '
  + 'threshold on a stop gesture chatters, and a stop that chatters is '
  + 'worse than no stop',
  /return was \? d < g\.release_m : d < g\.threshold_m;/.test(fn('gestHeld'))
  && /const hi = was \? g\.release_m : g\.threshold_m;/.test(fn('gestHeld')));
ok('an untracked joint reads as null, not as the origin - which would be a '
  + 'pinch every time hand tracking dropped',
  /if \(!j \|\| j\.visible === false\) return null;/.test(fn('jointAt'))
  && /if \(ext\.some\(\(d\) => d === null\)\) return false;/.test(fn('gestHeld')));
ok('the gestures are the registry\'s, walked by id, with the registry\'s own '
  + 'distances and dwell - none of the four is named in the loop',
  /for \(const \[id, g\] of Object\.entries\(HANDS\.gestures\)\)/.test(fn('xrHands'))
  && /now - prev\.since >= g\.hold_ms/.test(fn('xrHands')));
ok('"stop" releases every walk key and the edge cache, not only the keys '
  + 'this hand set - a stop that leaves a stick\'s key down has not stopped',
  /for \(const k of \['KeyW', 'KeyS', 'KeyA', 'KeyD', 'ShiftLeft'\]\) keys\[k\] = false;/
    .test(fn('xrGestFire'))
  && /xrPad\.edge = \{\};/.test(fn('xrGestFire')));
ok('hands are read AFTER the stick adapter, so a pointing hand sets the '
  + 'walk command instead of having a resting stick overwrite it',
  /xrStat\.lastInput = \{ l: xrPad\.l[^\n]*\n(?:[^\n]*\n){0,3}\s*xrHands\(dt, ses\);/.test(src));
ok('hand tracking is asked for as an OPTIONAL feature on both session '
  + 'shapes, so asking for it can never cost the session',
  (src.match(/optionalFeatures: \[XR_HANDS\]/g) || []).length === 2);
ok('the recogniser can be tested without a session, a headset or a hand, '
  + 'which is the only claim this build can honestly make about it',
  /window\.__tc3dHandProbe = \(id, joints, was = false\) => \{/.test(src)
  && /gestHeld\(g, was, hand\)/.test(src));
ok('the XR note no longer says hand tracking does not exist, and still says '
  + 'plainly that no hand has been held up to these distances',
  !/NOT exist: hand tracking/.test(src)
  && /Nobody has held a real hand up to these distances/.test(src));
ok('a view the guide has no place for stops the build, and so does a place '
  + 'for a view the page never sets',
  /_views = set\(re\.findall\(r"\\bview = '\(\[a-z\]\+\)'", page\)\)/.test(src)
  && /the page sets these views that the guide has no place for/.test(src)
  && /the guide has places for views this page never sets/.test(src));


/* ------------------------------------------ shadows on every device ----- */
// Shadows used to be switched off by `!('ontouchstart' in window)`, which
// answers "does this device have a touchscreen" and was being read as "can
// this device afford a shadow map". Those are different questions: the flag
// is true on a 2-in-1 with a discrete GPU and equally true on a budget
// phone. So every touch device lost the only cue that puts an object on the
// ground, including the ones with the GPU to spare.
//
// The claim replacing it - that a device which genuinely cannot hold shadows
// loses them on MEASURED frames - was proven before these were written, by
// feeding the ladder synthetic frame times: 60, 30 and 24 fps for six
// seconds all keep shadows; 21 and 12 fps drop to the low rung and clear
// them; 21 fps for four seconds does not, because the window has not closed.
ok('shadows are enabled for every device - the touchscreen flag no longer '
  + 'decides, because it was answering a different question',
  /renderer\.shadowMap\.enabled = true;/.test(src)
  && !/shadowMap\.enabled = !\('ontouchstart' in window\)/.test(src));
ok('the shadow map is SIZED to the device rather than taken away, and the '
  + 'size is declared once instead of typed at the light',
  /const SHADOW_PX = isTouch \? 1024 : 2048;/.test(src)
  && /key\.shadow\.mapSize\.set\(SHADOW_PX, SHADOW_PX\);/.test(src));
{
  // Counted over `code`, not `src`: the note beside the declaration quotes
  // the old expression. Writing this check found a THIRD reader - the
  // sim-binding visibility line still tested the flag inline - which is
  // exactly the disagreement it exists to prevent.
  ok('`ontouchstart` is tested ONCE and shared - three separate readers '
    + 'tested it for themselves, which is how they could have disagreed',
    (code.match(/'ontouchstart' in window/g) || []).length === 1);
}
ok('isTouch is declared before the renderer block that reads it: the emitted '
  + 'page puts that block at line ~269 and the walking code ~7,000 lines on',
  src.indexOf("const isTouch = 'ontouchstart' in window;")
    < src.indexOf('renderer.setPixelRatio(Math.min(devicePixelRatio, isTouch'));
ok('the ladder that takes shadows away is reachable without the harness '
  + 'guard, so the claim that a weak device loses them can be PROVEN',
  /window\.__tc3dQualityProbe = \(fps, seconds\) => \{/.test(src)
  && /for \(let t = 0; t < seconds \* fps; t\+\+\) qLadder\(dt\);/.test(src));
ok('the quality probe puts the rung back exactly as it found it - a probe '
  + 'that leaves the scene changed has measured one thing and broken another',
  // sliced by hand: fn() finds `function name(`, and this is an arrow
  // assigned to window. Since fn() now EXITS on a name it cannot find
  // rather than returning '', passing it one is a hard failure, not a
  // silent fallback - which is how this was caught.
  /setQuality\(was\.q\);\s*\n\s*return out;/.test(src.slice(
    src.indexOf('window.__tc3dQualityProbe'),
    src.indexOf('window.__tc3dQualityProbe') + 1400)));
ok('the debug hook reports what actually varies now - whether the ladder is '
  + 'paying for shadows, and how many texels - not a flag that is always true',
  /isTouch, shadows: key\.castShadow, shadowPx: SHADOW_PX,/.test(src));


/* ------------------------------------------------- the hour of the day --- */
// The sun was ONE fixed vector - (35, 48, 20) normalised, 49.98 degrees of
// elevation - shared by all ten campuses at every hour, forever. sky/ solves
// the real elevation and azimuth for fourteen phases at this campus's own
// latitude, and the page now places the light along that.
//
// Driven before these were written: all fourteen phases render, the sun
// rises in the east (azimuth 89.6 at sunrise, direction x = +1), is due
// south and 52.1 degrees up at noon, sets in the west (azimuth 270.7,
// x = -1), and is below the horizon at night (y = -0.79) and above it at
// noon (y = +0.79). Leak-checked over 56 sky rebuilds: zero drift in
// textures, geometries and lit lights.
ok('the sun\'s direction is a function of the HOUR, not a constant - the '
  + 'fixed (35, 48, 20) vector is gone',
  /function setSun\(elevDeg, azDeg\) \{/.test(src)
  && !/new THREE\.Vector3\(35, 48, 20\)\.normalize\(\)/.test(code));
ok('the light\'s basis is REBUILT when the sun moves - it was cached once '
  + 'precisely because the sun never did, and a stale basis snaps the '
  + 'shadow box to a grid belonging to a different hour',
  /SUN_FWD\.copy\(SUN_OFF\)\.normalize\(\);/.test(fn('setSun'))
  && /SUN_RIGHT\.crossVectors\(_sunAxis, SUN_FWD\)\.normalize\(\);/.test(fn('setSun'))
  && /sunR = 0;/.test(fn('setSun')));
ok('azimuth is converted from degrees-clockwise-from-north, which is what '
  + 'sky/ publishes, into the axes three.js actually uses',
  /SUN_OFF\.set\(c \* Math\.sin\(az\), Math\.sin\(el\), -c \* Math\.cos\(az\)\)/.test(fn('setSun')));
{
  // Asserted as an ORDER, not as a line distance. The first version of this
  // check wanted setSky within eight lines of applyPhase, and wiring the
  // gradient - which belongs exactly between them - broke a check whose
  // guarantee was untouched. What matters is which runs first.
  const body = fnCode('applyAtmos');
  ok('the hour is applied BEFORE the sky is drawn: setSky reads where the '
    + 'sun is, whether the stars are up and which gradient to compose, and '
    + 'all three are the hour\'s',
    body.indexOf('applyPhase();') > -1
    && body.indexOf('setSky(') > body.indexOf('applyPhase();')
    && body.indexOf('const gStops') > body.indexOf('applyPhase();')
    && body.indexOf('setSky(') > body.indexOf('const gStops'));
}
ok('the weather\'s two colour branches are gone - six hex literals that '
  + 'existed in no registry, making the light a function of the weather '
  + 'when it is a function of the hour',
  !/key\.color\.setHex\(0x9db4d8\)/.test(code)
  && !/key\.color\.setHex\(0x8a949c\)/.test(code)
  && /key\.color\.setHex\(parseInt\(eff\.sun\.color_hex/.test(fn('applyPhase')));
ok('the page keeps owning the base intensities and the hour only scales '
  + 'them, so a campus and a weather state still mean what they meant',
  /key\.intensity = a\.sun\.i \* w\.sun_mul \* eff\.sun\.intensity_mul;/.test(fn('applyPhase'))
  && /hemi\.intensity = a\.hemi\.i \* w\.hemi_mul \* indoors \* eff\.hemi\.intensity_mul;/
     .test(fn('applyPhase')));
ok('a weather state may PIN the hour rather than dress it - `night` is a '
  + 'weather state in world/, not a time, and sky/ marks that explicitly '
  + 'instead of the page inferring it',
  /ws\?\.phase_override \? PHASE_OF\[ws\.phase_override\] : ph/.test(fn('applyPhase')));
ok('the stars belong to the SUN: they are up when the hour puts it below '
  + 'the star layer\'s own cutoff, not when one weather state asks',
  /starsUp = eff\.elevation_deg < SKYDAY\.layers\.find\(\(l\) => l\.id === 'star-field'\)/
    .test(fn('applyPhase'))
  && !/stars: !!w\.stars/.test(code));
ok('the weather DIMS the stars rather than culling them - an overcast night '
  + 'is not a smaller sky, it is a dimmer one',
  /const vis = opts\.starAlpha \?\? 1;/.test(fn('skyCanvas'))
  && /const alpha = a \* \(1 - y \/ \(H \* \.95\)\) \* vis;/.test(fn('skyCanvas')));
ok('a bad phase id THROWS rather than falling back to a default hour, and '
  + 'a bad ?hour= query string is ignored rather than throwing',
  /throw new Error\('no such sky phase: ' \+ phaseId\)/.test(fn('applyPhase'))
  && /throw new Error\('no such sky phase: ' \+ id\)/.test(fn('setPhase'))
  && /if \(want && PHASE_OF\[want\]\)/.test(src));
ok('a probe can compare what the hour SAYS about the stars with what the '
  + 'sky was actually drawn with - they disagreed on every hour change '
  + 'until the ordering was fixed, and an assumption cannot catch that',
  /let starsDrawn = false;/.test(src)
  && /stars: \(starsDrawn = starsUp\)/.test(src)
  && /starsUp, starsDrawn, starAlpha,/.test(src));
ok('the hour is a control a person can reach, filled from the registry in '
  + 'its own order and labelled with the sun\'s real elevation',
  /<select id="hour" aria-label="hour of the day"><\/select>/.test(src)
  && /sel\.innerHTML = PHASES\.map\(\(ph\) => \{/.test(src)
  && /sel\.addEventListener\('change', \(\) => setPhase\(sel\.value\)\);/.test(src));


/* ------------------------------------------------- the sky's own colour --- */
// Capturing frames for the overview is what found this. The hour moved the
// sun and the lights, and painted the dome for daytime whatever the time:
// measured on the campus, night came out at luma 34.8 against golden hour's
// 36.6, a difference of 1.8 out of 255, which is why night looked like
// dusk. The gradient half of sky/ was declared and unread, and its own
// honesty block said so.
//
// Measured after, on a horizon-facing camera where the dome is actually
// visible, against noon: golden hour 136%, sunset 117%, civil dusk 96%,
// night 68%. The low-sun hours come out BRIGHTER than noon, which is the
// arc a sky really has - a low sun lights the whole dome - and not the one
// a linear dimmer would have given.
ok('the sky gradient is composed in the order sky/ declares and no other: '
  + 'the campus\'s own stops stay the base, the hour mixes over them, the '
  + 'weather tints that, and the weather\'s own sky_mul goes last',
  /const gStops = a\.sky\.map\(\(h, i\) => \{/.test(code)
  && /mixHex\(h, ph\.gradient\.stops\[i\], 1 - ph\.gradient\.campus_mix\)/.test(code)
  && /darkHex\(mixHex\(lit, ws\.gradient_tint_hex, ws\.tint_mix\), w\.sky_mul\)/.test(code));
ok('the campus keeps its own character rather than becoming one more thing '
  + 'mixed in - a Bay station and a Front Range yard must not end their '
  + 'domes identically',
  /setSky\(gStops,/.test(code)
  && /haze: a\.haze,/.test(code));
ok('the mix is per channel in sRGB, because these are colours chosen by eye '
  + 'against a screen and linear-space mixing moves them somewhere their '
  + 'author did not pick',
  /const mixHex = \(a, b, t\) => '#' \+ \[1, 3, 5\]\.map\(\(i\) => \{/.test(code));
ok('the weather scales the horizon band, and the identity is named as an '
  + 'identity rather than left to read as a policy default',
  /\* \(opts\.hazeMul \?\? 1\)/.test(code)
  && /not a policy\s*\n\s*\/\/ default but the identity/.test(src));
ok('the hour control follows the hour whoever set it - a programmatic '
  + 'change left the bar reading "Solar noon" while the sky was at night, '
  + 'and the control is the thing a person checks to find out the state',
  /const sel = document\.getElementById\('hour'\);/.test(fnCode('setPhase'))
  && /if \(sel && sel\.value !== id\) sel\.value = id;/.test(fnCode('setPhase')));
ok('applyPhase hands the resolved hour and weather treatment out rather '
  + 'than having applyAtmos resolve either a second time',
  /phaseGrad = eff; wxSky = ws;/.test(code)
  && /const ph = phaseGrad, ws = wxSky;/.test(code));

/* ---- real terrain ----------------------------------------------------
   Two checks below are scoped to a FUNCTION BODY rather than to `code`,
   and that is deliberate. `code` is the BUILDER, and the builder now
   carries build-time gates that quote the very JS they guard - so
   counting `tintTerrain(parseInt(gStops` across the file found two: the
   call, and the assertion that there is only one call. That is the same
   trap as the comment-matching one above, wearing different clothes: the
   text a check forbids or counts is likeliest to appear in the thing
   written to enforce it. Scope to where the code actually runs. */
ok('the terrain pack is shipped to the page, and the page holds no second '
  + 'copy of where a campus is - geo/ already answers that',
  /'terrain': \{/.test(src) || /D\.terrain/.test(code));
ok('every campus the page can open has ground built for it, checked at '
  + 'build rather than discovered as a thrown error in a browser',
  /these campuses can be opened but have no terrain/.test(src));
ok('buildTerrain refuses a campus with no terrain instead of quietly '
  + 'drawing the old disc - a missing world should stop, not degrade',
  /throw new Error\('no terrain built for campus ' \+ key\)/
    .test(fnCode('buildTerrain')));
ok('the mask is run-length encoded into quads before it is drawn: 9,216 '
  + 'cells as meshes would cost more draw calls than the whole campus',
  /mergeGeometries\(geos\)/.test(fnCode('buildTerrain'))
  && /let run = -1;/.test(fnCode('terrainRuns')));
ok('terrainRuns drops any run that lies wholly inside the apron, so the '
  + 'ground a learner stands on is never cut by a 1:10,000,000 shoreline',
  /const far = Math\.max\(Math\.abs\(x0\), Math\.abs\(x1\)\) > inner/
    .test(fnCode('terrainRuns'))
  && /if \(far\) out\.push/.test(fnCode('terrainRuns')));
ok('the water is coloured from the composed sky gradient\'s own horizon '
  + 'stop, once - a second solve of the same colour is how the sky and '
  + 'the stars fell out of step earlier in this file',
  (fnCode('applyAtmos').match(/tintTerrain\(parseInt\(gStops/g) || [])
    .length === 1);
ok('and water is modelled as reflection AND absorption, because reflection '
  + 'alone put a yellow bay under Miami at golden hour',
  /const WATER_ABSORB = /.test(code)
  && /\.lerp\(_waterBody, WATER_ABSORB\)/.test(fnCode('tintTerrain')));
ok('the land keeps its own tone rather than drifting to the same horizon '
  + 'the water reflects - at 22% it did, and the coastline went invisible',
  /\.lerp\(new THREE\.Color\(horizonHex\), \.10\)/.test(fnCode('tintTerrain')));
ok('the campus fog far plane is read from the terrain window, so the fog '
  + 'that used to hide a 520 m disc edge cannot hide six kilometres of bay',
  /T\.local\.half_m \* \.95/.test(fnCode('setCampusFog'))
  && !/1280 \* fogMul/.test(fnCode('setCampusFog')));
ok('and the weather still closes the view down - the multiplier is applied '
  + 'to the derived distance, not replaced by it',
  /scene\.fog\.far = far \* fogMul;/.test(fnCode('setCampusFog')));
ok('the terrain belongs to the campus group, so it is torn down with the '
  + 'campus and needs no disposal path of its own',
  /buildTerrain\(key, campusGroup\);/.test(code));
ok('a probe reports the terrain the page actually built, including whether '
  + 'the mask thinks this campus is standing on water',
  /window\.__tc3dTerrain = /.test(code)
  && /anchorOnLand: T\.facts\.anchor_on_land/.test(code));

ok('a measurement recorded twice in two files, with two different values '
  + 'and no surviving frame to settle it, is reported as a disagreement in '
  + 'BOTH files rather than as a number in each - and this check is what '
  + 'stops the two accounts drifting apart again',
  /the two records disagree/.test(src)
  // matched in two halves on purpose: written as one literal, this check
  // would itself be a second copy of the sentence, and any tool counting
  // the phrase across the tree would find two and call it a duplicate
  && /46 to 96 in this/.test(src) && /file, 46 to 89 in the suite/.test(src)
  && /the frame that would settle which is right is gone/.test(src));


/* ---- the kit and the props, drawn ------------------------------------
   kit/registry/kit.json and props/registry/props.json were DECLARED BUT
   UNBUILT: 1,117 campus pieces and 5,082 prop instances that nothing a
   learner opened ever read. They are drawn now, and these hold the shape
   of that drawing: through the pools that already exist (never a mesh per
   piece), by name against tables that already exist (never a colour from
   a registry that publishes none), owned by the group that tears them
   down, and reported by a probe that puts the drawn figure beside the
   declared one. Every check here is scoped to a function body: the
   builder now carries gates that quote the very strings these forbid. */
const kitReg = JSON.parse(readFileSync(new URL('../kit/registry/kit.json', import.meta.url), 'utf8'));
const propsReg = JSON.parse(readFileSync(new URL('../props/registry/props.json', import.meta.url), 'utf8'));

ok('both packs are shipped to the page as the slices it draws from, and '
  + 'the kit run formulas are read out of kit/build.py\'s own RUNS table '
  + 'rather than restated',
  /'kit': \{/.test(src) && /'props': \{/.test(src)
  && /_kit_runs_m = re\.search\(r'\\nRUNS = \\\{\(\.\*\?\)\\n\\\}', _kit_build_src, re\.S\)/.test(src)
  && /const KIT_RUNS = \{ __KIT_RUNS__ \};/.test(src)
  && /page\.replace\('__KIT_RUNS__', KIT_RUNS_JS\)/.test(src));
ok('the kit hangs on the envelope building() just drew - called from '
  + 'inside it with that envelope - and enters the SAME district pool, '
  + 'not a second one',
  /kitDress\(h, style, fab, pool, ox, oz, wid, dep, hgt, g\);/.test(fnCode('building'))
  && /\(pool\.get\(m2\) \?\? pool\.set\(m2, \[\]\)\.get\(m2\)\)\.push\(kitBase\(pid\)\.clone\(\)/
    .test(fnCode('kitDress')));
ok('building() itself pushes none of the kit\'s NEW materials through '
  + 'add(): the kit registry reads which materials add() already pools to '
  + 'price its own draw calls, and a kit piece pushed through '
  + 'add(mat.metal) would have priced itself free',
  (() => {
    const fresh = new Set(Object.values(kitReg.budget.campuses)
      .flatMap((c) => c.new_pooled_materials));
    return fresh.size > 0
      && [...fresh].every((m) => !fnCode('building').includes('add(' + m + ','))
      && !/\badd\(kitMat/.test(fnCode('building'));
  })());
ok('flushParts() stays the only merge door for the kit: kitDress() builds '
  + 'no mesh and merges nothing itself, and buildCampus() still flushes '
  + 'each district once',
  !/mergeGeometries\(/.test(fnCode('kitDress'))
  && !/new THREE\.Mesh\(/.test(fnCode('kitDress'))
  && (fnCode('buildCampus').match(/flushParts\(pool, cg\);/g) || []).length === 1);
ok('the two instanced kit families are their own InstancedMesh per campus '
  + 'and never ride the station beacons, which spin every frame',
  /new THREE\.InstancedMesh\(kitGeo\(pid\)/.test(fnCode('flushKit'))
  && !/beaconInst|beaconAt|spinBeacons/.test(fnCode('flushKit') + fnCode('kitDress')));
ok('a kit material is resolved BY NAME against the page\'s own tables and '
  + 'a name with nothing behind it throws - the kit publishes no colours '
  + 'and the page invents none for it',
  /throw new Error\('kit material ' \+ name \+ ' names nothing this page builds'\)/
    .test(fnCode('kitMat'))
  && !/0x[0-9a-fA-F]{6}/.test(fnCode('kitMat') + fnCode('kitDress') + fnCode('flushKit')));
ok('a kit piece that comes out of its recipe with a different triangle '
  + 'count than the registry budgets throws, so the probe\'s triangles are '
  + 'the ones drawn',
  /tris !== p\.tri_budget\)\s+throw new Error/.test(fnCode('kitGeo')));
ok('a kit count mode, datum or merge mode the page does not resolve is a '
  + 'thrown error, not a quiet default',
  /throw new Error\('kit count mode '/.test(fnCode('kitDress'))
  && /throw new Error\('kit datum '/.test(fnCode('kitDress'))
  && /which this page does not grant'\)/.test(fnCode('kitDress')));
ok('every piece the kit registry declares has a shape in the page, and '
  + 'every shape is a declared piece (the build gates the same pair)',
  (() => {
    const blk = code.match(/\nconst KIT_SHAPES = \{([\s\S]*?)\n\};/);
    const shapes = new Set([...blk[1].matchAll(/^ {2}'([a-z-]+)': \(/gm)].map((m) => m[1]));
    const pieces = new Set(Object.keys(kitReg.pieces));
    return shapes.size === pieces.size && [...pieces].every((p) => shapes.has(p))
      && /KIT_SHAPES and kit\.json disagree about which pieces exist/.test(src);
  })());
ok('the kit belongs to the campus group: reset when a campus is built, '
  + 'flushed into it after the beacons, and freed with it',
  /kitReset\(\);/.test(fnCode('buildCampus'))
  && /flushKit\(campusGroup\);/.test(fnCode('buildCampus'))
  && !/userData\.shared = true/.test(fnCode('kitGeo') + fnCode('flushKit')));
ok('a probe reports the kit actually drawn beside the figures the registry '
  + 'predicted and the ceiling it was held to - all three read from the '
  + 'payload, none typed here',
  /window\.__tc3dKit = /.test(code)
  && /D\.kit\.budget\.campuses\[k\]/.test(code)
  && /drawCallsAdded: kitStat\.newCalls \+ kitStat\.instanced/.test(code)
  && /ceiling: \{ draw_calls: D\.kit\.budget\.draw_call_ceiling/.test(code));
ok('the build gates what the browser would otherwise throw on: a kit or '
  + 'prop material the page does not build, and a safety fixture '
  + 'triggered by PPE no room record names',
  /kit\/registry\/kit\.json names a material the page does not build/.test(src)
  && /props\/registry\/props\.json names a material the page does not build/.test(src)
  && /is triggered by PPE no room record names/.test(src));
ok('the kit registry\'s honesty now names the functions that draw it, and '
  + 'the page has them',
  /kitDress\(\)/.test(kitReg.honesty.budget_limit)
  && /__tc3dKit\(\)/.test(kitReg.honesty.budget_limit)
  && /\nfunction kitDress\(/.test(src) && /\nfunction flushKit\(/.test(src));

ok('the props of all eleven rooms pool into ONE map hoisted above the room '
  + 'loop and flush ONCE after it - pooling per room would multiply the '
  + 'hall\'s draw calls by eleven',
  (() => {
    const b = fnCode('buildHall');
    const pool = b.indexOf('propPool = new Map(); propInst = new Map();');
    const loop = b.indexOf('for (const r of h.rooms) {');
    const flush = b.indexOf('flushProps(hallGroup);');
    return pool > 0 && loop > pool && flush > loop
      && (b.match(/flushProps\(hallGroup\);/g) || []).length === 1;
  })());
ok('a room\'s props are placed against the rectangle and the doorways its '
  + 'partitions were cut with, and a safety fixture is stood by the room\'s '
  + 'OWN conditions record - the one the placard is drawn from, handed in '
  + 'rather than looked up a second time',
  /placeRoomProps\(h, r, rx, rz, rw, rd, doors, benches, rc\.ppe,/.test(fnCode('buildHall'))
  && /runSegments\(doors, 'x@' \+ x0\.toFixed\(2\), zF, zB\)/.test(fnCode('placeRoomProps'))
  && !/condOf\(|D\.condOver|D\.baseCond/.test(fnCode('placeRoomProps')));
ok('the fixtures a room\'s record REQUIRES claim their wall before the '
  + 'furniture its purpose line earns it',
  (() => {
    const b = fnCode('placeRoomProps');
    return b.indexOf('ppe_any') > 0 && b.indexOf('want.push(...ids);') > b.indexOf('ppe_any');
  })());
ok('a floor-standing prop registers with wallRect() so the walker cannot '
  + 'pass through it; a wall-mounted one hangs above nothing a walker '
  + 'occupies and registers nothing',
  /if \(!wallMounted\) wallRect\(x, \(z0 \+ z1\) \/ 2, sd \/ 2, sw \/ 2\);/.test(fnCode('placeRoomProps'))
  && /wallRect\(x, z, sw \/ 2, sd \/ 2\);/.test(fnCode('placeRoomProps')));
ok('a corner prop is kept out of the fixture benches by the SAME solid '
  + 'rectangles the walker is, read back from where the bench registered '
  + 'them rather than from a second copy of the bench size',
  /benches\.push\(hallSolids\[0\]\.rects\[hallSolids\[0\]\.rects\.length - 1\]\);/.test(fnCode('buildHall'))
  && /!benches\.some\(\(b\) => Math\.abs\(x - b\.u\) < sw \/ 2 \+ b\.hw \+ BODY_R\)/.test(fnCode('placeRoomProps')));
ok('the tool crib says which run of which wall it took, and the tools '
  + 'room\'s props are placed after it has said so',
  /return \{ wall: 'right', z0: rz - bw \/ 2 - \.75, z1: rz \+ bw \/ 2 \};/.test(fnCode('buildCrib'))
  && /const reserved = r\.strand === 'tools' \? \[buildCrib\(h, rx, rz, rw, rd\)\] : \[\];/.test(fnCode('buildHall'))
  && /for \(const rv of reserved\) used\[rv\.wall\]\.push\(\[rv\.z0, rv\.z1\]\);/.test(fnCode('placeRoomProps')));
ok('a prop material is resolved by name and throws on nothing; an anchor '
  + 'or merge mode the page does not resolve throws too',
  /throw new Error\('prop material ' \+ name \+ ' names nothing this page builds'\)/.test(fnCode('propMat'))
  && /throw new Error\('prop anchor '/.test(fnCode('placeRoomProps'))
  && /which this page does not grant'\)/.test(fnCode('placeRoomProps')));
ok('a prop whose recipe adds up to a different triangle count than the '
  + 'registry states throws, and its geometry is never marked shared, so '
  + 'disposeOf() frees it with the hall',
  /tris !== p\.tris\)\s+throw new Error/.test(fnCode('propGeo'))
  && !/userData\.shared = true/.test(fnCode('propGeo')));
ok('the pooled props go through flushParts() and each safety fixture is '
  + 'one InstancedMesh per hall - never the beacons\' - and the recipe '
  + 'cache is emptied once the clones are merged',
  /flushParts\(propPool, g\)/.test(fnCode('flushProps'))
  && /new THREE\.InstancedMesh\(propGeo\(p\)\.clone\(\)/.test(fnCode('flushProps'))
  && !/beaconInst/.test(fnCode('flushProps'))
  && /for \(const ge of propGeoCache\.values\(\)\) ge\.dispose\(\);/.test(fnCode('flushProps')));
ok('a probe reports the props actually standing beside the count the '
  + 'registry\'s rule wanted, names each one that found no wall and why, '
  + 'and quotes the registry\'s own per-hall budget rather than a typed one',
  /window\.__tc3dProps = /.test(code)
  && /skipped: propStat\.skipped\.slice\(\)/.test(code)
  && /declared: \{ per_hall: D\.props\.budget\.per_hall/.test(code)
  && /why: 'no clear back corner'/.test(fnCode('placeRoomProps')));
ok('the props registry\'s honesty says it is built, names the function '
  + 'that builds it, the page has that function, and the claim is not '
  + 'filed under a key called not_built_yet',
  !('not_built_yet' in propsReg.honesty)
  && /^BUILT\./.test(propsReg.honesty.built)
  && /placeRoomProps\(\)/.test(propsReg.honesty.built)
  && /\nfunction placeRoomProps\(/.test(src));
ok('every strand the props registry places into is one the room table '
  + 'inflates, and the page throws rather than furnishing a strand it has '
  + 'no row for',
  /throw new Error\('props registry covers no strand named '/.test(fnCode('placeRoomProps'))
  && /props\/registry\/props\.json and the room table disagree about the strands/.test(src));

ok('the city layer\'s pads, greens, avenues, dashes and tower caps pool '
  + 'into one mesh per material through flushParts() - 17 places used to '
  + 'cost 51 draw calls for flat slabs nothing raycasts - while the block '
  + 'and the tower stay the click targets',
  /flushParts\(cityPool, g\)/.test(fnCode('buildCity'))
  && !/box\(24, \.14, 24/.test(fnCode('buildCity'))
  && !/box\(15, \.12, 15/.test(fnCode('buildCity'))
  && !/box\(3, \.5, 3,/.test(fnCode('buildCity'))
  && /cityHits\.push\(bld, twr\);/.test(fnCode('buildCity'))
  && /return out;/.test(fnCode('flushParts')));

console.log(`web/test_3d: ${n} checks passed - teardown, draw-call and per-frame contracts held at the source`);

/* ------------------------------------------- first responders + EI ------ */
/* Two packs that the bundle's own R&D register listed as DECLARED AND
   UNBUILT: nothing a learner opened read either registry. These checks hold
   the two things a surface for them can most easily get wrong - dropping
   the review status, and rendering a standards body as though the content
   came from it - plus the bidirectional hall link and the one rule the EI
   pack enforces with a regex: it names TYPES of resource and never an
   instance of one.

   Everything below reads either a function body with its comments cut out
   (fnCode) or the SHIPPED payload parsed out of the built page, never the
   generator's prose - a check that reads the comment explaining a removal
   has answered a different question, and this file has been bitten by that
   eight times. */
const respondReg = JSON.parse(readFileSync(new URL('../respond/registry/respond.json', import.meta.url), 'utf8'));
const eiReg = JSON.parse(readFileSync(new URL('../ei/registry/ei.json', import.meta.url), 'utf8'));
const builtPage = readFileSync(new URL('./trade_craft_3d.html', import.meta.url), 'utf8');
const wire = JSON.parse(builtPage.match(
  /<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1]);

ok('the responder panel exists, the bar opens it, and every service, role '
  + 'tier, competency domain and scenario frame the registry declares '
  + 'reaches the shipped payload',
  /\nfunction openResponder\(/.test(src)
  && /window\.__tc3dRespond = openResponder;/.test(code)
  && /getElementById\('respondBtn'\)\.addEventListener/.test(code)
  && Object.keys(wire.respond.services).length === respondReg.counts.services
  && Object.values(wire.respond.services)
       .reduce((n, s) => n + s.tiers.length, 0) === respondReg.counts.role_tiers
  && wire.respond.competencies.length === respondReg.counts.competencies
  && wire.respond.frames.length === respondReg.counts.scenario_frames);

ok('the review status is read from each record\'s OWN two fields and the '
  + 'banner from the registry\'s own counts - no panel function types the '
  + 'number of signed-off items',
  /rec\.needs_practitioner_review === true && rec\.signed_off_by === null/
    .test(fnCode('respUnsigned'))
  && /C\.signed_off_items \+ ' of '\s*\+ C\.training_items/.test(fnCode('openResponder'))
  && !/117|\b0 of\b/.test(fnCode('openResponder'))
  && !/117/.test(fnCode('respFrameCard'))
  // and it is actually true of every item that ships, all 117 of them
  && [...Object.values(wire.respond.services).flatMap((s) => s.tiers),
      ...wire.respond.competencies, ...wire.respond.frames]
       .every((r) => r.needs_practitioner_review === true
                  && r.signed_off_by === null));

ok('no authority is rendered without the line saying whether a document of '
  + 'that body was opened, and a body the registry does not carry throws '
  + 'rather than defaulting',
  /document_read_by_this_build === true/.test(fnCode('respAuthority'))
  && /no document of this body was opened by this build/.test(fnCode('respAuthority'))
  && /this pack reproduces/.test(fnCode('respAuthority'))
  && /throw new Error\('respond: no authority record at D\.respond\./
       .test(fnCode('respAuthority'))
  && !/\?\?/.test(fnCode('respAuthority'))
  && Object.values(wire.respond.authorities)
       .every((a) => a.document_read_by_this_build === false)
  && respondReg.counts.authority_documents_opened === 0);

ok('the hall cross-links run both ways: a frame card links into each hall '
  + 'it names, and a hall whose slug the registry pairs gets a badge back '
  + 'into the panel - 81 halls with one, 30 without',
  /data-hall-goto="' \+ esc\(sg\)/.test(fnCode('respFrameCard'))
  && /showHall\(hg\.dataset\.hallGoto\)/.test(code)
  && builtPage.includes('D.respond.crossLinks[sg] ? ` <button class="barbtn" data-respond-hall=')
  && /openResponder\(rh\.dataset\.respondHall\)/.test(code)
  && Object.keys(wire.respond.crossLinks).length === respondReg.counts.halls_touched
  && Object.values(wire.respond.crossLinks)
       .reduce((n, x) => n + x.frames.length, 0)
       === respondReg.counts.hall_cross_links);

ok('the cross-links ship no second copy of a hall\'s protective equipment - '
  + 'the surfaces registry already reaches this page and owns that fact',
  Object.values(respondReg.hall_cross_links)
    .every((x) => Array.isArray(x.trade_ppe_in_that_hall))
  && Object.values(wire.respond.crossLinks)
       .every((x) => !('trade_ppe_in_that_hall' in x))
  && wire.baseCond !== undefined);

ok('the EI layer is printed on the advisor it binds to, and a figure the '
  + 'pack binds nothing to (a crew role) gets nothing invented for it',
  /\+ advisorConduct\(aid\);/.test(fnCode('openAdvisor'))
  && /const b = D\.ei\.bindings\[aid\];\s*if \(!b\) return '';/
       .test(fnCode('advisorConduct'))
  && eiReg.agent_bindings.length === eiReg.counts.advisors_in_registry
  && eiReg.agent_bindings.every((b) => b.agent in wire.advisors.who)
  && Object.keys(wire.ei.bindings).length === eiReg.counts.agent_bindings);

ok('every response is rendered with what it does NOT do, its stop condition '
  + 'and its handoff rung beside what it does - and a rung the ladder does '
  + 'not have throws instead of defaulting',
  /What it does not do/.test(fnCode('eiDoes'))
  && /r\.does_not\.map/.test(fnCode('eiDoes'))
  && /esc\(r\.stop_condition\)/.test(fnCode('eiDoes'))
  && /eiRungLine\(r\.handoff/.test(fnCode('eiDoes'))
  && /throw new Error\('ei: no handoff rung called '/.test(fnCode('eiRung'))
  && !/\?\?/.test(fnCode('eiRungLine'))
  && Object.values(wire.ei.responses).every((r) => r.does_not.length > 0
       && typeof r.stop_condition === 'string' && r.stop_condition.length > 0));

ok('the post-incident state is rendered as a refusal, not a coach: the '
  + 'universal response is printed only where its state is hand-off-only, '
  + 'it lasts one turn, and it neither asks what happened nor offers a '
  + 'technique',
  /st\.agent_may !== 'hand-off-only'/.test(fnCode('advisorConduct'))
  && /this block renders a refusal, not a coach/.test(fnCode('advisorConduct'))
  && /hand-off only, '\s*\+ r\.max_turns/.test(fnCode('advisorConduct'))
  && wire.ei.states['post-incident-distress'].agent_may === 'hand-off-only'
  && wire.ei.responses['post-incident.disclosed'].max_turns === 1
  && wire.ei.responses['post-incident.disclosed'].universal === true
  && wire.ei.responses['post-incident.disclosed'].does_not
       .some((x) => /does not ask what happened/.test(x))
  && wire.ei.responses['post-incident.disclosed'].does_not
       .some((x) => /does not offer a technique/.test(x))
  && eiReg.agent_bindings.every((b) =>
       b.universal_responses.includes('post-incident.disclosed')));

/* The one rule the ei pack enforces with a regex, re-asked of the bytes
   that actually ship. The patterns are READ OUT of ei/build.py rather than
   retyped here, for the same reason build_3d.py reads them: a second copy
   of a rule is a second chance for the two to disagree about it. */
const eiBuildSrc = readFileSync(new URL('../ei/build.py', import.meta.url), 'utf8');
const eiBanBlock = eiBuildSrc.slice(eiBuildSrc.indexOf('\nBANNED = ['),
  eiBuildSrc.indexOf('\n]\n', eiBuildSrc.indexOf('\nBANNED = [')));
const eiBanned = eiBanBlock.split('\n    (').slice(1).map((entry) =>
  new RegExp([...entry.matchAll(/r'((?:[^'\\]|\\.)*)'/g)]
    .map((m) => m[1]).join('')));
const eiStrings = (node, path, out = []) => {
  if (typeof node === 'string') out.push([path, node]);
  else if (Array.isArray(node)) node.forEach((v, i) => eiStrings(v, `${path}[${i}]`, out));
  else if (node && typeof node === 'object')
    for (const [k, v] of Object.entries(node)) eiStrings(v, `${path}.${k}`, out);
  return out;
};
const eiHits = eiStrings(wire.ei, 'D.ei')
  .flatMap(([p, s]) => eiBanned.map((re) => [p, s.match(re)])
    .filter(([, m]) => m).map(([p2, m]) => `${p2}: ${m[0]}`));

ok(`the EI layer ships ${eiBanned.length} banned patterns' worth of nothing: `
  + 'no telephone number, emergency or crisis line, dialling instruction, '
  + 'web or email address or named support organisation reaches the page, '
  + 'and the ladder names a resource TYPE on every one of its rungs',
  eiBanned.length === 5
  && eiHits.length === 0
  && wire.ei.ladder.length === eiReg.counts.handoff_rungs
  && wire.ei.ladder.every((r) => typeof r.resource_type === 'string'
       && r.resource_type.length > 0 && typeof r.why_no_contact_detail === 'string'));

ok('build_3d.py re-runs that refusal over the bytes it is about to ship, '
  + 'reading the patterns out of ei/build.py rather than retyping them, and '
  + 'stops the build on a hit',
  /_EI_BAN_SRC = \(ROOT \/ 'ei\/build\.py'\)\.read_text\(\)/.test(src)
  && /EI_BANNED = ast\.literal_eval\(/.test(src)
  && /ships %s \(%r\) to the page/.test(src)
  && /raise SystemExit\(\s*\n\s*'build_3d: %s ships/.test(src));

ok('neither panel puts anything in the scene: a panel is DOM, and this one '
  + 'is held to costing nothing in draw calls',
  ['openResponder', 'respFrameCard', 'respAuthority', 'advisorConduct',
   'eiDoes', 'eiSignalRows'].every((f) => !/THREE\./.test(fnCode(f))
     && !/scene\.add/.test(fnCode(f))));
