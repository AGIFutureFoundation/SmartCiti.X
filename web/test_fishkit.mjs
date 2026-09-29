#!/usr/bin/env node
// web/test_fishkit.mjs - headless checks of the fishing kit (web/fishkit.py): the FISH_CORE is extracted byte-for-byte
// and run seeded (no DOM); the built pages carry the kit, its data slice, the HUD registration and ONE marker mesh.
// Prints "  ok <name>" per check, FAIL at column 0, exits non-zero on any failure.
import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const ROOT = new URL('..', import.meta.url).pathname;
let fails = 0, n = 0;
const ok = (c, name, info = '') => { n++; if (c) console.log('  ok ' + name); else { fails++; console.log('FAIL ' + name + (info ? ' :: ' + info : '')); } };
const read = (p) => readFileSync(ROOT + p, 'utf8');

const kit = read('web/fishkit.py');
const B = '/* FISH_CORE:BEGIN */', E = '/* FISH_CORE:END */';
const core = kit.slice(kit.indexOf(B), kit.indexOf(E) + E.length);
ok(kit.split(B).length === 2 && kit.split(E).length === 2, 'core: exactly one FISH_CORE block');
ok(!/Math\.random|document\.|window\./.test(core), 'core: pure (no Math.random, no DOM)');
const F = new Function(core + '\nreturn { fishRng, fishInSeason, fishTimeOfDay, fishRodsFor, fishCandidates, fishPick, fishCast, fishBiteDelay, fishReelInit, fishReelStep, fishTrapCheck, fishLogAdd };')();

const reg = JSON.parse(read('outdoors/registry/outdoors.json'));
const sp = (id) => reg.species.find((s) => s.id === id);
const spot = (pred) => reg.spots.find(pred);

// seeded RNG determinism
const a = F.fishRng(42), b = F.fishRng(42), c = F.fishRng(43);
const sa = Array.from({ length: 8 }, a), sb = Array.from({ length: 8 }, b), sc = Array.from({ length: 8 }, c);
ok(JSON.stringify(sa) === JSON.stringify(sb) && JSON.stringify(sa) !== JSON.stringify(sc), 'rng: same seed same stream, other seed differs');
ok(sa.every((x) => x >= 0 && x < 1), 'rng: values in [0, 1)');

// seasons wrap, times of day
ok(F.fishInSeason(sp('dungeness-crab'), 1) && F.fishInSeason(sp('dungeness-crab'), 11) && !F.fishInSeason(sp('dungeness-crab'), 8), 'season: a Nov-Jun window wraps across the new year');
ok(F.fishInSeason(sp('crappie'), 3) && !F.fishInSeason(sp('crappie'), 8), 'season: a plain window holds inside, refuses outside');
ok(['dawn', 'day', 'dusk', 'night'].every((k, i) => F.fishTimeOfDay([6, 12, 18, 23][i]) === k), 'time: hours map to dawn/day/dusk/night');

// candidates: spot x season x bait x time x rod
const bayou = spot((s) => s.world === 'parishes' && s.habitat === 'bayou');
const cands = F.fishCandidates(reg, bayou, { rod: 'baitcasting-rod', bait: 'soft-plastic', time: 'dawn', month: 5 });
ok(cands.some((x) => x.sp.id === 'largemouth-bass'), 'pick: bayou + baitcaster + soft plastic at dawn in May can bring a largemouth bass');
ok(cands.every((x) => x.sp.regions.includes('gulf')), 'pick: a parish spot only offers Gulf-region species');
ok(!F.fishCandidates(reg, bayou, { rod: 'baitcasting-rod', bait: 'soft-plastic', time: 'dawn', month: 5 }).some((x) => x.sp.id === 'striped-bass'), 'pick: no Bay species in a parish bayou');
ok(F.fishCandidates(reg, bayou, { rod: 'fly-rod', bait: 'dry-fly', time: 'day', month: 5 }).length === 0, 'pick: a rod that does not suit the water offers nothing');
ok(F.fishCandidates(reg, bayou, { rod: 'spinning-rod', bait: 'chicken-neck', time: 'day', month: 5 }).length === 0 && F.fishCandidates(reg, bayou, { rod: 'spinning-rod', bait: 'worm', time: 'day', month: 5 }).length > 0, 'pick: bait matters - a crab bait on a spinning rod draws nothing where a worm does');
const crNight = F.fishCandidates(reg, spot((s) => s.world === 'parishes' && s.habitat === 'pond'), { rod: 'cane-pole', bait: 'worm', time: 'night', month: 6 });
ok(!crNight.some((x) => x.sp.id === 'bluegill'), 'pick: a species with no night weight never bites at night');
const shore = spot((s) => s.world === 'bay' && s.habitat === 'bay-shore');
ok(F.fishCandidates(reg, shore, { rod: 'crab-line', bait: 'chicken-neck', time: 'day', month: 12 }).some((x) => x.sp.id === 'dungeness-crab'), 'pick: a Bay crab line in December can bring a Dungeness crab');
ok(!F.fishCandidates(reg, shore, { rod: 'crab-line', bait: 'chicken-neck', time: 'day', month: 8 }).some((x) => x.sp.id === 'dungeness-crab'), 'pick: out of its game season the Dungeness crab never comes up');
let threw = false; try { F.fishCandidates(reg, bayou, { rod: 'no-such-rod', bait: 'worm', time: 'day', month: 5 }); } catch (e) { threw = /unknown rod/.test(e.message); }
ok(threw, 'pick: an unknown rod throws by name (fail closed)');
const r1 = F.fishRng(7), r2 = F.fishRng(7);
const picks1 = Array.from({ length: 20 }, () => F.fishPick(cands, r1).id), picks2 = Array.from({ length: 20 }, () => F.fishPick(cands, r2).id);
ok(JSON.stringify(picks1) === JSON.stringify(picks2), 'pick: seeded picks repeat exactly');
ok(F.fishPick([], F.fishRng(1)) === null, 'pick: no candidates = no bite (null)');

// cast
const rod = reg.rods.find((r) => r.id === 'spinning-rod');
ok(F.fishCast(0, 0.75, rod).quality === 'good', 'cast: controlled power straight ahead is good');
ok(F.fishCast(0, 1, rod).quality === 'tangle', 'cast: full power tangles');
ok(F.fishCast(0, 0.1, rod).quality === 'short', 'cast: weak power falls short');
ok(F.fishCast(0, 0.8, reg.rods.find((r) => r.id === 'surf-rod')).length > F.fishCast(0, 0.8, reg.rods.find((r) => r.id === 'cane-pole')).length, 'cast: a surf rod reaches farther than a cane pole');
ok(F.fishBiteDelay(sp('brown-trout'), { quality: 'ok' }, F.fishRng(3)) > F.fishBiteDelay(sp('bluegill'), { quality: 'ok' }, F.fishRng(3)), 'bite: a wary fish waits longer (same seed)');

// reel: holding in the window lands; never reeling escapes; always reeling snaps
function play(policy, seed, id = 'bluegill', rodId = 'spinning-rod') {
  const st = F.fishReelInit(sp(id), reg.rods.find((r) => r.id === rodId)), rng = F.fishRng(seed);
  for (let i = 0; i < 3000 && st.state === 'fight'; i++) F.fishReelStep(st, policy(st), 1 / 30, rng);
  return st.state;
}
ok(play((st) => st.tension < (st.lo + st.hi) / 2, 11) === 'landed', 'reel: keeping tension in the green lands the fish');
ok(play(() => false, 11) === 'escape', 'reel: never reeling lets it escape on slack line');
ok(play(() => true, 11) === 'snap', 'reel: reeling nonstop snaps the line');
const bw = F.fishReelInit(sp('red-drum'), reg.rods.find((r) => r.id === 'baitcasting-rod')), nw = F.fishReelInit(sp('bluegill'), reg.rods.find((r) => r.id === 'cane-pole'));
ok(bw.hi - bw.lo < nw.hi - nw.lo, 'reel: a strong fighter on a stiff rod has a narrower green window than a panfish on a cane pole');

// traps
const canal = spot((s) => s.world === 'parishes' && s.habitat === 'canal');
const t1 = F.fishTrapCheck(reg, canal, { rod: 'crawfish-trap', bait: 'trap-bait', time: 'day', month: 3 }, 12, F.fishRng(5));
const t2 = F.fishTrapCheck(reg, canal, { rod: 'crawfish-trap', bait: 'trap-bait', time: 'day', month: 3 }, 12, F.fishRng(5));
ok(JSON.stringify(t1) === JSON.stringify(t2) && t1.haul.length > 0 && t1.haul.every((x) => x === 'red-swamp-crawfish'), 'trap: a canal trap in March hauls crawfish, seeded');
ok(F.fishTrapCheck(reg, canal, { rod: 'crawfish-trap', bait: 'trap-bait', time: 'day', month: 9 }, 12, F.fishRng(5)).note === 'empty', 'trap: out of the game season the trap comes up empty');
ok(F.fishTrapCheck(reg, canal, { rod: 'crawfish-trap', bait: 'trap-bait', time: 'day', month: 3 }, 1, F.fishRng(5)).haul.length === 0, 'trap: an unsoaked trap holds nothing');

// log
const L = {};
F.fishLogAdd(L, { species: 'bluegill', at: 'x', spot: 's1', released: true }); F.fishLogAdd(L, { species: 'bluegill', at: 'y', spot: 's2', released: false });
ok(L.bluegill.caught === 2 && L.bluegill.released === 1 && L.bluegill.first === 'x' && L.bluegill.spots.length === 2, 'log: codex counts catches, releases, first time and spots');

// python side: data slice + i18n + embed fail closed
const py = (code) => execFileSync('python3', ['-c', 'import sys; sys.path.insert(0, "web")\n' + code], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
const slice = JSON.parse(py('from fishkit import fish_data; import json; print(json.dumps(fish_data("bay")))'));
ok(slice.spots.every((s) => s.world === 'bay') && slice.species.every((s) => s.regions.includes('bay')) && slice.agencies.join() === 'California Department of Fish and Wildlife', 'data: the Bay slice holds only Bay spots, Bay species and the California agency');
let bad = ''; try { py('from fishkit import fish_data; fish_data("moon")'); } catch (e) { bad = String(e.stderr); }
ok(/unknown world 'moon'/.test(bad), 'data: an unknown world stops the build by name');
const cat = JSON.parse(py('from fishkit import fish_i18n; import json; print(json.dumps(fish_i18n()))'));
ok(Object.keys(cat).length === 8 && cat.ar.dir === 'rtl', 'i18n: 8 locales, Arabic rtl');
const en = cat.en.strings;
ok(Object.entries(cat).filter(([k]) => k !== 'en').every(([, v]) => Object.keys(en).filter((k) => v.strings[k] === en[k]).length <= 1), 'i18n: non-English values are translations (at most one shared word)');
ok(/\{n\}/.test(en.trap_haul) && Object.values(cat).every((v) => v.strings.trap_haul.includes('{n}')), 'i18n: trap_haul keeps its {n} placeholder in every locale');
ok(/device/.test(en.play) && /never a completion record/.test(en.play), 'honesty: the play line says device-only and never a completion record');

// built pages (when present): kit carried byte-for-byte, one marker mesh, HUD registered, honesty lines, agencies
for (const [page, world] of [['web/trade_craft_parishes.html', 'parishes'], ['web/trade_craft_bay.html', 'bay'], ['web/trade_craft_wilds.html', 'wilds']]) {
  if (!existsSync(ROOT + page)) { ok(false, `page ${page}: exists`); continue; }
  const h = read(page);
  ok(h.includes(core), `page ${world}: FISH_CORE carried byte-for-byte`);
  ok((h.match(/new THREE\.InstancedMesh\(geo, mat, MAX\)/g) || []).length === 1 && !/fish[^\n]{0,80}new THREE\.Mesh\(/.test(h), `page ${world}: ONE InstancedMesh for every fish marker`);
  const d = h.match(/<script type="application\/json" id="fish-data">([\s\S]*?)<\/script>/);
  const dj = d && JSON.parse(d[1]);
  ok(dj && dj.world === world && dj.spots.length > 0 && dj.spots.every((s) => s.world === world), `page ${world}: embeds its own spot slice`);
  ok(/"id":"fish","kind":"panel","sel":"#fish-hud"|data-hud-id="fish"|#fish-hud/.test(h) && h.includes('id="fish-hud"'), `page ${world}: fish HUD panel present and registered`);
  ok(h.includes('Louisiana Department of Wildlife and Fisheries') && h.includes('California Department of Fish and Wildlife'), `page ${world}: real-activity line names the state wildlife agencies`);
  ok(h.includes('window.__fishHost'), `page ${world}: host bridge mounted`);
  ok(dj && Object.keys(dj.eggs).length >= 1 && Object.values(dj.eggs).every((q) => /^egg-fish-/.test(q)), `page ${world}: hidden spots map to fish eggs`);
}
console.log(fails ? `web/test_fishkit: ${fails} FAILED of ${n}` : `web/test_fishkit: ${n} checks passed`);
process.exit(fails ? 1 : 0);
