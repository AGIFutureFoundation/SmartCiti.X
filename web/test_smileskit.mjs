/* web/test_smileskit.mjs - the Unspoken Smiles mini-game core (web/smileskit.py, SMILES wave 12), run in node.
 * The core between SMILES_CORE markers is sliced from the kit, evaluated, and played with fixed seeds: every game is
 * deterministic, reads its figures from smiles/registry/smiles.json, and never invents a number. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const kit = readFileSync(join(HERE, 'smileskit.py'), 'utf8');
const reg = JSON.parse(readFileSync(join(ROOT, 'smiles/registry/smiles.json'), 'utf8'));
const G = reg.games;
const a = kit.indexOf('/* SMILES_CORE:BEGIN'), b = kit.indexOf('/* SMILES_CORE:END */');
const core = kit.slice(a, b);
const C = new Function(core + '\nreturn SmilesCore;')();

ok('the core is pure: no Math.random, no Date, no DOM, no storage', a > 0 && b > a
  && !/Math\.random|Date\.|new Date|document\.|window\.|localStorage/.test(core));
const deal = (s) => C.snackNew(G.snacks, s).deck.map((x) => x.id).join();
ok('snack sort is seeded: same seed same deck, another seed another order, every item dealt once',
  deal(7) === deal(7) && deal(7) !== deal(8) && new Set(C.snackNew(G.snacks, 7).deck.map((x) => x.id)).size === G.snacks.items.length);
let s = C.snackNew(G.snacks, 3); while (!C.snackDone(s)) C.snackSort(s, s.deck[s.i].sort);
let w = C.snackNew(G.snacks, 3); while (!C.snackDone(w)) C.snackSort(w, s.deck[w.i].sort === 'sugary' ? 'tooth-friendly' : 'sugary');
ok('snack sort scores the registry sort: all right = 3 stars, all wrong = 0', C.snackScore(s) === 3 && C.snackScore(w) === 0);
let br = C.brushNew(G.brushing);
ok('brushing time comes from the registry and splits evenly per quadrant', br.total === G.brushing.total_s && br.per * G.brushing.quadrants.length === br.total);
for (let i = 0; i < br.total; i++) C.brushTick(br, G.brushing.quadrants[0], 1);
ok('brushing only one quadrant for the whole time covers a quarter and scores 1 star', C.brushDone(br) && C.brushCoverage(br) === 0.25 && C.band(C.brushCoverage(br)) === 1);
br = C.brushNew(G.brushing);
for (const q of G.brushing.quadrants) for (let i = 0; i < br.per; i++) C.brushTick(br, q, 1);
ok('brushing every quadrant its share gives full coverage and ends exactly at the guidance time', C.brushDone(br) && C.brushCoverage(br) === 1 && br.elapsed === G.brushing.total_s);
C.brushTick(br, G.brushing.quadrants[0], 50);
ok('the brushing clock stops at the total (no over-credit)', br.elapsed === G.brushing.total_s);
let fl = C.flossNew(G.flossing);
C.flossStep(fl, 3); for (let i = 0; i < fl.gaps; i++) C.flossStep(fl, i);
ok('flossing follows the path in order: an out-of-order gap is a miss, the arch gap count is teeth - 1',
  C.flossDone(fl) && fl.misses === 1 && fl.gaps === G.flossing.arch_teeth - 1 && C.flossScore(fl) === 3);
const pl = C.plaqueNew(G.plaque, 11), pl2 = C.plaqueNew(G.plaque, 11);
ok('plaque hunt: seeded distinct spots inside the grid, same seed same spots', pl.spots.length === G.plaque.spots
  && new Set(pl.spots).size === pl.spots.length && pl.spots.every((c) => c >= 0 && c < G.plaque.grid[0] * G.plaque.grid[1])
  && pl.spots.join() === pl2.spots.join() && pl.spots.join() !== C.plaqueNew(G.plaque, 12).spots.join());
for (const c of pl.spots) C.plaqueScrub(pl, c);
ok('plaque hunt ends when every spot is scrubbed; perfect taps score 3', C.plaqueDone(pl) && C.plaqueScore(pl) === 3);
const wa = C.washNew(G.handwash);
C.washNext(wa); C.washNext(wa);
const early = C.washNext(wa);
for (let i = 0; i < G.handwash.scrub_s; i++) C.washTick(wa, 1);
const late = C.washNext(wa); C.washNext(wa); C.washNext(wa);
ok('handwashing will not leave the scrub step before the registry scrub time', wa.need === G.handwash.scrub_s && early === false && late === true && C.washDone(wa)
  && JSON.stringify(wa.steps) === JSON.stringify(G.handwash.steps));
const dr = C.drinksNew(G.drinks, 5, 12);
ok('sugar-in-drinks pairs always compare two different categories, names come from registry examples',
  dr.pairs.every((p) => p.a.rank !== p.b.rank && [p.a, p.b].every((x) => G.drinks.categories.find((c) => c.id === x.cat).examples.includes(x.name))));
while (!C.drinksDone(dr)) C.drinksPick(dr, dr.pairs[dr.i].a.rank > dr.pairs[dr.i].b.rank ? 'a' : 'b');
ok('the right answer is the higher category rank (added sugar more likely) - no gram figure is used', dr.right === 12 && C.drinksScore(dr) === 3
  && !/gram|tsp|teaspoon/i.test(core));
ok('every game has a guidance line and the disclaimer is the registry one', ['brushing', 'flossing', 'snacks', 'plaque', 'handwash', 'drinks'].every((g) => reg.guidance[g])
  && kit.includes("'smiles.disclaimer'") && reg.disclaimer === 'General guidance, not medical or dental advice.');
ok('each game has a K-12 band', /BANDS = \{'brushing': 'K-5', 'flossing': 'K-5', 'snacks': 'K-5', 'plaque': '6-8', 'handwash': 'K-5', 'drinks': '6-8'\}/.test(kit));
ok('game touch targets are at least 44 px', /\.sm-tabs button,\.sm-stage button\{min-block-size:44px;min-inline-size:44px/.test(kit));
ok('scores are device-local play (localStorage in try/catch), no network', /try \{ const k = D\.store;[^]*catch \(e\)/.test(kit) && !/fetch\(|XMLHttpRequest|sendBeacon/.test(kit));

console.log(`test_smileskit: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
