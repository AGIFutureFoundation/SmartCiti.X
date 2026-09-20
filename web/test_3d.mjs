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
ok('and the rest of the outdoor rig steps back with it, where the '
  + 'atmosphere is already being written - one place decides it',
  /const INDOOR_RIG = \.35;/.test(src)
  && /const indoors = view === 'hall' \? INDOOR_RIG : 1;/.test(fn('applyAtmos'))
  && /hemi\.intensity = a\.hemi\.i \* w\.hemi_mul \* indoors;/.test(fn('applyAtmos'))
  && /fill\.intensity = FILL_I \* indoors;/.test(fn('applyAtmos')));
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

console.log(`web/test_3d: ${n} checks passed - teardown, draw-call and per-frame contracts held at the source`);
