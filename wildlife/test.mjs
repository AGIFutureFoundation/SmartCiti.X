#!/usr/bin/env node
/* wildlife/test.mjs - the wildlife pack, held to the wave-12 rules (games are play AND informative; wildlife safety is
   part of the game). Prints "  ok " per check, FAIL at column 0, exits non-zero on failure. */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
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
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const R = JSON.parse(read('wildlife/registry/wildlife.json'));
const S = R.species;

const run = (args) => { try { return execFileSync('python3', args, { cwd: ROOT, encoding: 'utf8' }); } catch (e) { return String(e.stdout || '') + String(e.stderr || ''); } };
ok('python3 wildlife/build.py --check: the registry is current', /is current/.test(run(['wildlife/build.py', '--check'])));
ok('python3 wildlife/make_eggs.py --check: quests/source/bayou.json is current', /is current/.test(run(['wildlife/make_eggs.py', '--check'])));
const stamp = createHash('sha256').update(Buffer.concat([readFileSync(join(ROOT, 'wildlife/build.py')), readFileSync(join(ROOT, 'wilds/registry/wilds.json'))])).digest('hex');
ok('source_stamp is sha256 over the builder and the wilds registry it reads', R.source_stamp === stamp.slice(0, 16) && R.source_stamp_sha256 === stamp);

const ids = S.map((s) => s.id);
ok(`species ids unique and kebab-case (${S.length})`, new Set(ids).size === ids.length && ids.every((i) => /^[a-z]+(-[a-z]+)*$/.test(i)));
const WANT = ['american-alligator', 'brown-pelican', 'roseate-spoonbill', 'great-egret', 'great-blue-heron', 'nutria', 'river-otter',
  'red-eared-slider', 'california-sea-lion', 'harbor-seal', 'dungeness-crab', 'monarch-butterfly'];
ok('the brief\'s regional species are all present, named generally', WANT.every((w) => ids.includes(w)), WANT.filter((w) => !ids.includes(w)));
const perRegion = Object.fromEntries(R.regions.map((r) => [r, S.filter((s) => s.regions.includes(r)).length]));
ok(`every region has at least 8 species (${JSON.stringify(perRegion)})`, R.regions.every((r) => perRegion[r] >= 8) && JSON.stringify(R.counts) === JSON.stringify({ species: S.length, ...perRegion, dangerous: S.filter((s) => s.dangerous).length }));
const badF = S.filter((s) => !['water', 'shore', 'land'].includes(s.habitat) || !(s.game_m.safe > 0 && s.game_m.safe < s.game_m.photo)
  || !s.window.months.length || s.window.months.some((m) => m < 1 || m > 12) || s.window.label !== 'approximate, game calendar' || s.provenance !== 'AUTHORED').map((s) => s.id);
ok('every species: AUTHORED habitat, a safe < photo game band, months 1..12 labelled "approximate, game calendar"', badF.length === 0, badF);
const NUM = /\b\d+(\.\d+)?\s*(ft|feet|foot|lb|lbs|pounds|kg|inches|inch|cm|m|mph|km\/h|years?)\b/i;
const badFact = S.filter((s) => !/\((state|federal) wildlife agency|NOAA Fisheries|bird (field guides|conservation groups)|conservation groups|national park guidance\)/.test(s.fact) || NUM.test(s.fact) || NUM.test(s.safety)).map((s) => s.id);
ok('every fact names the kind of source and no fact or safety line quotes a measurement', badFact.length === 0, badFact);
const gator = S.find((s) => s.id === 'american-alligator');
ok('alligators are marked dangerous and their safety line says so plainly (never approach, never feed)',
  gator && gator.dangerous === true && /[Dd]angerous/.test(gator.safety) && /never approach/.test(gator.safety) && /feed/.test(gator.safety));
const sv = R.safe_viewing.map((r) => r.id);
ok('safe-viewing rules: distance, never feed, never harass, alligators dangerous, nests, pets, trails, report',
  ['distance', 'never-feed', 'never-harass', 'alligators', 'nests', 'pets', 'trails', 'report'].every((k) => sv.includes(k))
  && /never approach/i.test(R.safe_viewing.find((r) => r.id === 'alligators').text));
ok('honesty: play (device-only, never a record, never money, never a permit) + the state-rules line naming LDWF and CDFW',
  /play/.test(R.honesty.play) && /never a completion record/.test(R.honesty.play) && /never money/.test(R.honesty.play) && /licence/.test(R.honesty.play)
  && /Louisiana Department of Wildlife and Fisheries/.test(R.honesty.rules_line) && /California Department of Fish and Wildlife/.test(R.honesty.rules_line));
const G = R.games;
const gs = G['gator-season'];
ok('gator season is a SIMULATION: tag recorded, no animal shown harmed, rules line, approximate game calendar',
  /SIMULATION/.test(gs.label) && /tag recorded/.test(gs.label) && /no animal is shown harmed/.test(gs.label) && gs.rules_line === R.honesty.rules_line
  && gs.months.label === 'approximate, game calendar' && gs.steps.some((s) => s.id === 'tag') && gs.steps.some((s) => s.id === 'record'));
ok('K-12 swap: classroom mode replaces the season with a nest SURVEY / photo game and says so',
  /nest survey/i.test(gs.classroom.title) && /Classroom mode/.test(gs.classroom.label) && /replaced/.test(gs.classroom.label)
  && gs.classroom.steps.some((s) => s.id === 'photo') && gs.classroom.steps.some((s) => s.id === 'distance') && gs.classroom.quest === 'treasure-bayou-nest-survey');
const GORE = /\b(kill|killed|blood|gore|shoot|shot dead|wound|carcass|skinned|dead)\b/i;
ok('no gore words anywhere in the games text', !GORE.test(JSON.stringify(G)), JSON.stringify(G).match(GORE));
ok('turtle rounds: exactly one right option each, a reason each', G['turtle-crossing'].rounds.every((r) => r.options.filter((o) => o.right).length === 1 && r.why.length > 20));
ok('litter items: each in a known bin with a wildlife reason', G['shoreline-litter'].items.every((i) => G['shoreline-litter'].bins.includes(i.bin) && i.why.length > 15));

// the quest source this pack generates, and the registry that loads it
const B = JSON.parse(read('quests/source/bayou.json'));
const Q = JSON.parse(read('quests/registry/quests.json'));
const QI = Object.fromEntries(Q.quests.map((q) => [q.id, q]));
const want = [];
for (const s of S) for (const [r, id] of Object.entries(s.quests)) want.push([id, r]);
const missQ = want.filter(([id, r]) => !QI[id] || QI[id].world !== r || QI[id].kind !== 'treasure').map(([id]) => id);
ok(`every species photo treasure (${want.length}) is in the quest registry in its region's world`, missQ.length === 0, missQ);
const gameIds = [gs.quest, gs.classroom.quest, ...Object.values(G['turtle-crossing'].quests), ...Object.values(G['shoreline-litter'].quests), ...Object.values(G['photo-safari'].quests)];
ok('every game quest id is in the quest registry', gameIds.every((i) => QI[i]), gameIds.filter((i) => !QI[i]));
const eggs = B.entries.filter((e) => e.kind === 'egg');
const eggW = (p) => eggs.filter((e) => e.world === p || e.world.startsWith(p + ':')).length;
ok(`hidden eggs across parish (${eggW('parish') + eggW('parishes')}), Bay (${eggW('bay')}), wilds (${eggW('wilds')}) and campus (${eggW('campus')}) maps`,
  eggW('parish') >= 10 && eggW('bay') >= 8 && eggW('wilds') >= 4 && eggW('campus') >= 2);
const badEgg = eggs.filter((e) => !e.trigger || !e.riddle || !/\((state|federal|geological|national|NOAA|bird|conservation)[^)]*\)\.?$/.test(e.reveal) || NUM.test(e.reveal)).map((e) => e.id);
ok('every egg has a trigger, a riddle and an informative reveal ending in its kind of source, with no invented measurement', badEgg.length === 0, badEgg);
const words = eggs.filter((e) => e.trigger.startsWith('typed:')).map((e) => e.trigger);
const allTyped = Q.quests.filter((q) => q.trigger && q.trigger.startsWith('typed:')).map((q) => q.trigger);
ok('typed egg words are unique across the whole quest registry', new Set(allTyped).size === allTyped.length && words.length > 0,
  allTyped.filter((w, i) => allTyped.indexOf(w) !== i));

// pages that mount the kit carry its panel, data and core, and the eggs of their world
for (const [page, region] of [['web/trade_craft_parishes.html', 'parishes'], ['web/trade_craft_bay.html', 'bay'], ['web/trade_craft_wilds.html', 'wilds']]) {
  if (!existsSync(join(ROOT, page))) { ok(`${page} exists`, false); continue; }
  const h = read(page);
  const d = h.match(/<script type="application\/json" id="wild-data">([\s\S]*?)<\/script>/);
  const data = d ? JSON.parse(d[1].replace(/<\\\//g, '</')) : null;
  ok(`${page}: wildlife panel, core and ${region} data from the current registry`, h.includes('id="wild-panel"') && h.includes('WILD-CORE:BEGIN')
    && data && data.region === region && data.stamp === R.source_stamp && data.species.length === perRegion[region]);
  const hookIds = [...h.matchAll(/data-tc-egg="(egg-[a-z0-9-]+)"/g)].map((m) => m[1]);
  const wantEggs = Q.quests.filter((e) => e.kind === 'egg' && e.trigger).filter((e) => (region === 'parishes' ? (e.world === 'parishes' || e.world.startsWith('parish:')) : region === 'bay' ? (e.world === 'bay' || e.world.startsWith('bay:')) : e.world.startsWith('wilds:'))).map((e) => e.id);
  ok(`${page}: every triggered ${region} egg of every source (${wantEggs.length}) has a hook and the page carries the quest engine`, h.includes('QUEST_CORE:BEGIN') && wantEggs.every((i) => hookIds.includes(i)), wantEggs.filter((i) => !hookIds.includes(i)));
}

console.log(fails ? `wildlife/test: ${fails} FAILED` : 'wildlife/test: all passed');
process.exit(fails ? 1 : 0);
