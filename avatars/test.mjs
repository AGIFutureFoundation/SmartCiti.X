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
ok('the wardrobe is complete: headwear (hard hats AND ball caps), tops, vest, trousers, footwear, tools',
  ['headwear', 'headcolor', 'top', 'topcolor', 'vest', 'pants',
   'pantscolor', 'shoes', 'tools'].every((id) =>
    reg.sections.some((s) => s.id === id))
  && ['hard-cap', 'full-brim', 'ball-cap', 'ball-cap-back'].every((id) =>
    reg.sections.find((s) => s.id === 'headwear').options.some((o) => o.id === id)));

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
