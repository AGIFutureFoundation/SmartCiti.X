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

/* ----------------------------------------------------- luminaire units --- */
/* three.js r155 flipped `useLegacyLights` to false and r160 dropped the
   legacy path, so a PointLight's intensity is CANDELA and falls off as
   I / r^decay. Every luminaire here was first written with legacy-scale
   numbers (0.5 - 2.6), which at a 2.7 m ceiling or an 8.7 m mast head is
   indistinguishable from no light at all - measured on a hall interior,
   scaling them took the frame from a mean luminance of 46 to 89 out of 255.
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
  /const fin = D\.finCat\[D\.finishes\[slug\]\[curRoom\.strand\]\.surface\];/
    .test(fn('stepFamily'))
  && /return D\.step\.floor\[fin\?\.pattern\] \?\? 'hard';/.test(fn('stepFamily'))
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
  && (src.match(/const wasSilent = wkSilent; wkSilent = true;/g) ?? []).length === 2
  && (src.match(/\n  wkSilent = wasSilent;/g) ?? []).length === 2);
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

console.log(`web/test_3d: ${n} checks passed - teardown, draw-call and per-frame contracts held at the source`);
