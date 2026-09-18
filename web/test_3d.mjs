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
// the body of a top-level `function name(`: up to the column-0 brace that closes it
const fn = (name) => {
  const i = src.indexOf(`\nfunction ${name}(`);
  if (i < 0) return '';
  const j = src.indexOf('\n}\n', i + 1);
  return src.slice(i, j < 0 ? undefined : j + 2);
};

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
  /if \(qRose\) return;/.test(fn('qStep')) && /qFrames \/ qAcc >= 45\) \{ qRose = true; setQuality\('high'\); \}/.test(fn('qStep'))
  && /qFrames \/ qAcc < 22/.test(fn('qStep')));

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
  && /new THREE\.PointLight\(0xffe9c8, \.55 \+ luxN \* 1\.45,/.test(src));
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
  /new THREE\.PointLight\(0xffe9c8, 1\.5,/.test(fn('simYard'))
  && /ml\.visible = qLevel !== 'low';/.test(fn('simYard')));
ok('the one indoor seat floors and lights its shop bay the same way, without '
  + 'borrowing the outdoor fence',
  /const yard = D\.sims\.sims\['overhead-crane'\]\.yard;/.test(src)
  && /const hb = new THREE\.PointLight\(0xffe9c8, 1\.3,/.test(src));
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
ok('the district still decides a roofline it has an opinion about; the city '
  + 'breaks the tie',
  /STYLE_OF\[k\] \?\? \(D\.world\.fabric\?\.\[campusKey\]\?\.roof \?\? 'flat'\)/.test(src));
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
/* Reading through two levels of an absent table is what broke this function
   for one build: the registry had `fabric` and the page payload did not. */
ok('an absent fabric table degrades to a fallback instead of throwing',
  /const fab = D\.world\.fabric \?\? \{\};/.test(fn('fabricOf'))
  && /fab\[ck\] \?\? fab\['treasure-island'\] \?\? FABRIC_FALLBACK/.test(fn('fabricOf'))
  && /const FABRIC_FALLBACK = /.test(src));
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
  /finishMat\(D\.finCat\[def\.yard\.surface\]/.test(fn('buildTrainingYard')));
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

console.log(`web/test_3d: ${n} checks passed - teardown, draw-call and per-frame contracts held at the source`);
