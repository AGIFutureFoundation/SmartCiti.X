/**
 * Avatar pack verification.
 *
 * The locker is a contract with the learner: many options per section,
 * every one free, and none of it able to touch a score. The guarantee is
 * asserted here, and the sections are held to the shape the wheel
 * renders from — a wedge with nothing to draw is a broken locker.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/avatars.json', import.meta.url)));

ok('a full locker: at least eight sections, each with four or more options',
  reg.sections.length >= 8
  && reg.sections.every((s) => s.options.length >= 4));
ok('every section carries an id, a wheel emoji, a label and a render kind',
  reg.sections.every((s) => s.id && s.emoji && s.label
    && ['color', 'style'].includes(s.kind)));
ok('every wedge can draw: colour options carry a value, style options a glyph',
  reg.sections.every((s) => s.options.every((o) =>
    s.kind === 'color' ? /^#[0-9a-f]{6}$/i.test(o.value) : o.glyph?.length >= 1)));
ok('option ids are unique within their section',
  reg.sections.every((s) =>
    new Set(s.options.map((o) => o.id)).size === s.options.length));
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
  + `${reg.sections.reduce((a, s) => a + s.options.length, 0)} options, `
  + `${reg.emotes.length} emotes`);
