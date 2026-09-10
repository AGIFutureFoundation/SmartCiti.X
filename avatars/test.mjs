/**
 * Avatar pack verification.
 *
 * The locker is a contract with the learner: 15–20 options in every
 * section, a crew seat for every hall on the roster, every one free, and
 * none of it able to touch a score. The guarantee and the marks policy
 * are asserted here, and the sections are held to the shape the wheel
 * renders from — a wedge with nothing to draw is a broken locker.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/avatars.json', import.meta.url)));
const unions = JSON.parse(readFileSync(new URL('../unions/registry/unions.json', import.meta.url))).unions;

const std = reg.sections.filter((s) => s.kind !== 'crew');
const crew = reg.sections.find((s) => s.kind === 'crew');

ok('a deep locker: fifteen-plus sections, every standard one holding 15-20 options',
  reg.sections.length >= 15 && std.length >= 14
  && std.every((s) => s.options.length >= 15 && s.options.length <= 20));
ok('every section carries an id, a wheel emoji, a label and a render kind',
  reg.sections.every((s) => s.id && s.emoji && s.label
    && ['color', 'style', 'crew'].includes(s.kind)));
ok('every wedge can draw: colours carry a value, styles and crews a glyph',
  reg.sections.every((s) => s.options.every((o) =>
    s.kind === 'color' ? /^#[0-9a-f]{6}$/i.test(o.value) : o.glyph?.length >= 1)));
ok('option ids are unique within their section',
  reg.sections.every((s) =>
    new Set(s.options.map((o) => o.id)).size === s.options.length));
ok('the body is a real range: 16 build combinations, 18 skin tones, 16 hairstyles, 15 eye colours, 15 facial-hair cuts',
  reg.sections.find((s) => s.id === 'build').options.length === 16
  && reg.sections.find((s) => s.id === 'skin').options.length === 18
  && reg.sections.find((s) => s.id === 'hair').options.length === 16
  && reg.sections.find((s) => s.id === 'eyes').options.length === 15
  && reg.sections.find((s) => s.id === 'facialhair').options.length === 15);
ok('the wardrobe is complete: headwear (hard hats AND ball caps), tops, vest, trousers, footwear, tools, outerwear, extras, costumes',
  ['headwear', 'headcolor', 'top', 'topcolor', 'vest', 'pants',
   'pantscolor', 'shoes', 'tools', 'outer', 'extras', 'costume'].every((id) =>
    reg.sections.some((s) => s.id === id))
  && ['hard-cap', 'full-brim', 'ball-cap', 'ball-cap-back'].every((id) =>
    reg.sections.find((s) => s.id === 'headwear').options.some((o) => o.id === id)));
ok('everyday work stays the default: outerwear, extras and costume all open on none',
  ['outer', 'extras', 'costume'].every((id) => reg.defaults[id] === 'none'
    && reg.sections.find((s) => s.id === id).options.some((o) => o.id === 'none')));

/* ----------------------------------------------------------- characters --- */
const secIds = Object.fromEntries(
  reg.sections.map((s) => [s.id, new Set(s.options.map((o) => o.id))]));
ok('seventeen one-tap characters, each with a name, an emoji and a line of story',
  reg.characters.length === 17
  && new Set(reg.characters.map((c) => c.id)).size === 17
  && reg.characters.every((c) => c.name && c.emoji && c.blurb?.length > 20));
ok('every character is made of the locker: each cfg value resolves to a real option',
  reg.characters.every((c) =>
    Object.keys(c.cfg).length === reg.sections.length
    && Object.entries(c.cfg).every(([k, v]) => secIds[k]?.has(v))));
ok('the costumes range from the krewe to the foundry, and characters wear them',
  ['krewe', 'foundry', 'diver', 'vintage-33', 'gold-journey'].every((id) =>
    secIds.costume.has(id))
  && reg.characters.filter((c) => c.cfg.costume !== 'none').length >= 8);
ok('five original animal mascots join the costume rack, the workshop ape among them',
  ['ape-mascot', 'pelican-mascot', 'bear-mascot', 'gator-mascot',
   'ox-mascot'].every((id) => secIds.costume.has(id))
  && reg.characters.some((c) => c.cfg.costume === 'ape-mascot'));
ok('the TradeApes: 111 originals, one per hall, generated from the roster',
  reg.tradeapes.apes.length === 111
  && JSON.stringify(reg.tradeapes.apes.map((t) => t.hall).sort())
    === JSON.stringify(unions.map((u) => u.slug).sort())
  && reg.tradeapes.apes.every((t) => t.name === 'TradeApe ' + t.code
    && t.cfg.costume === 'ape-mascot' && t.cfg.crew === t.hall
    && Object.entries(t.cfg).every(([k, v]) => secIds[k]?.has(v))));
ok('the TradeApes vary: many furs, builds and vests across the collection',
  new Set(reg.tradeapes.apes.map((t) => t.cfg.topcolor)).size >= 15
  && new Set(reg.tradeapes.apes.map((t) => t.cfg.build)).size === 16
  && new Set(reg.tradeapes.apes.map((t) => t.cfg.vest)).size === 4);
ok('the TradeApes honesty: free, cosmetic, NOT tokens, imitating nobody',
  /free and cosmetic/.test(reg.tradeapes.honesty)
  && /Not tokens/.test(reg.tradeapes.honesty)
  && /no blockchain/.test(reg.tradeapes.honesty)
  && /no third-party ape artwork/.test(reg.tradeapes.honesty));
ok('the mascot policy is stated: original characters, no third-party collection imitated',
  /original Academy/.test(reg.marks) && /third-party/.test(reg.marks)
  && /not.*reproduced or derived/.test(reg.marks.replace(/\n/g, ' ')));

/* ----------------------------------------------------------------- crew --- */
ok('the crew section seats the whole roster: one option per hall, exactly',
  crew && crew.options.length === 111
  && JSON.stringify(crew.options.map((o) => o.id).sort())
    === JSON.stringify(unions.map((u) => u.slug).sort()));
ok('every crew mark is a unique three-letter code in a real district hue',
  new Set(crew.options.map((o) => o.glyph)).size === 111
  && crew.options.every((o) => /^[A-Z0-9]{3}$/.test(o.glyph)
    && o.hue >= 0 && o.hue <= 360 && o.district && o.name));
ok("each crew's district matches the roster's own assignment",
  crew.options.every((o) =>
    unions.find((u) => u.slug === o.id).district === o.district));
ok('the marks policy is stated: Academy insignia, no real logo named or drawn',
  /Academy/.test(reg.marks) && /not, and do not\s+imitate/.test(reg.marks)
  && /no local is named/.test(reg.marks));

/* ------------------------------------------------------------- contract --- */
ok('a default exists for every section and resolves to a real option',
  reg.sections.every((s) => s.options.some((o) => o.id === reg.defaults[s.id]))
  && Object.keys(reg.defaults).length === reg.sections.length);
ok('eight emotes, each with an emoji, a label and a procedural move',
  reg.emotes.length >= 8
  && reg.emotes.every((e) => e.id && e.emoji && e.label && e.move)
  && new Set(reg.emotes.map((e) => e.id)).size === reg.emotes.length);
ok('the guarantee is stated: cosmetic only, free, and score-blind',
  /cosmetic only/.test(reg.guarantee) && /free and unlocked/.test(reg.guarantee)
  && /scoring/.test(reg.guarantee));

// The guarantee holds in code, not just in prose: the page's grading and
// progress recording must never read the avatar record.
const page = readFileSync(new URL('../web/build_3d.py', import.meta.url), 'utf8');
const simResults = page.slice(page.indexOf('function simResults'),
  page.indexOf('function simResults') + 2200);
ok("the page's grader never reads the avatar record",
  !/avatar/i.test(simResults));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`avatars/test: ${n} checks passed — ${reg.sections.length} sections, `
  + `${std.reduce((a, s) => a + s.options.length, 0)} options + 111 crews, `
  + `${reg.emotes.length} emotes`);
