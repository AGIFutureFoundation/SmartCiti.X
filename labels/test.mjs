/**
 * Label registry verification.
 *
 * A sign should be readable before it is read, so the checks are about
 * whether that promise is structurally kept: every kind has a shape the
 * page can actually draw, every shape earns its place, provenance words
 * stay the bundle's own three, the focus behaviour is declared as
 * presentation and nothing reads it as a score, and the legibility floor
 * is a real number rather than a hope.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/labels.json', import.meta.url)));
const page = readFileSync(new URL('../web/trade_craft_3d.html', import.meta.url), 'utf8');
const districts = JSON.parse(readFileSync(
  new URL('../unions/registry/districts.json', import.meta.url))).districts;
const kinds = Object.entries(reg.kinds);
const shapes = Object.entries(reg.shapes);

/* --------------------------------------------------------- shape = meaning --- */
ok(`every kind names a shape the page can draw (${kinds.length} kinds, ${shapes.length} shapes)`,
  kinds.every(([, k]) => k.shape in reg.shapes)
  && shapes.every(([id]) => page.includes(`case '${id}'`)));
ok('every shape says in words what it reads as, so the convention can be taught',
  shapes.every(([, s]) => s.reads_as.length > 15 && s.draws.length > 20));
ok('no shape is declared and left undrawn - every one is used by some kind',
  new Set(kinds.map(([, k]) => k.shape)).size === shapes.length);
ok('the speech bubble is the advisor\'s, and it is the only one with a tail besides the hall tab',
  reg.kinds.advisor.shape === 'speech' && reg.shapes.speech.tail === true
  && shapes.filter(([, s]) => s.tail).length === 2);
ok('a hall is a tab you can enter and a room is a plate you are already in',
  reg.kinds.hall.shape === 'tab' && reg.kinds.room.shape === 'plate');

/* ------------------------------------------------------ colour = provenance --- */
ok('every accent resolves: a palette colour, or the district\'s own hue',
  kinds.every(([, k]) => k.accent === 'district' || k.accent in reg.palette));
ok('the kinds that wear a district hue are the ones a district actually owns',
  kinds.filter(([, k]) => k.accent === 'district')
    .every(([id]) => ['hall', 'district', 'station'].includes(id)));
ok('provenance words stay the bundle\'s three, and the SCHEMATIC sign is drawn dashed',
  kinds.filter(([, k]) => k.provenance)
    .every(([, k]) => ['RECORDED', 'DERIVED', 'SCHEMATIC'].includes(k.provenance))
  && reg.kinds.schematic.dashed === true
  && reg.kinds.anchor.provenance === 'RECORDED'
  && reg.kinds.anchor.accent === 'recorded');
ok('a label never upgrades a claim, and the registry says so',
  /restate the claim the registry behind\s+them already makes/
    .test(reg.honesty.provenance)
  && /never upgrades a claim/.test(reg.honesty.provenance));

/* ------------------------------------------------------------ type = rank --- */
ok('three faces, three ranks, and no fourth',
  ['display', 'body', 'mono'].every((f) => f in reg.type)
  && kinds.every(([, k]) => ['display', 'body', 'mono'].includes(k.face)));
ok('anything a machine measured is set in mono',
  reg.kinds.readout.face === 'mono' && reg.kinds.route.face === 'mono');
ok('the type scale is real numbers the page uses',
  reg.type.title_px > reg.type.sub_px && reg.type.sub_px > 16
  && page.includes('LTYPE.title_px') && page.includes('LTYPE.sub_px'));

/* ------------------------------------------------------- field of vision --- */
ok('the focus cone is a cone, and distance is judged relative to the view',
  reg.focus.cone_deg > 10 && reg.focus.cone_deg < 90
  && reg.focus.fade_from_rel > 1
  && reg.focus.fade_from_rel < reg.focus.fade_to_rel
  && /relative to how far out the view\s+is/.test(reg.focus.contract));
ok('the page scores angle and distance and multiplies them, as declared',
  /_lblTo\.dot\(_lblFwd\)/.test(page)
  && /const rel = dist \/ ref;/.test(page)
  && /const want = ang \* near;/.test(page));
ok('exactly one label is the focus, and it is tinted and lifted',
  /the single most centred label within reach is the FOCUS/
    .test(reg.focus.focus_rule)
  && reg.focus.lift_m > 0 && reg.focus.grow > 0
  && /best\.material\.color\.set\(LPAL\.mark\)/.test(page)
  && /best\.position\.y \+= LFOCUS\.lift_m/.test(page));
ok('it is eased rather than snapped, so nothing flickers as the head turns',
  reg.focus.ease > 0 && /u\.focus \+= \(want - u\.focus\) \* ease/.test(page));
ok('and it works without a cursor, which is the point in a headset',
  /without a\s+cursor/.test(reg.focus.focus_rule));

/* ----------------------------------------------------------- legibility --- */
ok('a label is clamped to a readable band of the viewport at both ends',
  reg.focus.screen.min_frac > 0
  && reg.focus.screen.min_frac < reg.focus.screen.max_frac
  && reg.focus.screen.max_frac < .5
  && /LFOCUS\.screen\.min_frac/.test(page)
  && /LFOCUS\.screen\.max_frac/.test(page));
ok('it is drawn at device pixel ratio and carries a shadow for a bright sky',
  /devicePixelRatio/.test(page) && /shadowColor/.test(page)
  && /drawn at device pixel ratio/.test(reg.honesty.legibility));
ok('reduced motion keeps the shapes and drops the breathing',
  /keep the shapes\s+and the colours and lose the easing/
    .test(reg.honesty.reduced_motion)
  && /const ease = reduced \? 1 :/.test(page));

/* ------------------------------------------------------ presentation only --- */
ok('focus is presentation: no label is a score and none gates anything',
  /Looking at a label changes\s+nothing/.test(reg.honesty.presentation_only)
  && /no label is a score, none gates anything/
    .test(reg.honesty.presentation_only));
ok('no grader anywhere reads which sign a learner faced',
  page.split(/function (?:score|grade)/).slice(1)
    .every((c) => !/labelFocus/.test(c.slice(0, 2500))));
ok('the shapes are admitted to be this bundle\'s own convention, not a standard',
  /a convention this bundle invented, not\s+a standard/
    .test(reg.honesty.convention));

/* ------------------------------------------------------------- the page --- */
ok('the page builds labels, draws their shapes, and steps them every frame',
  ['function label(', 'function labelShape(', 'function labelStep(']
    .every((f) => page.includes(f)));
ok('every kind the registry declares reaches the page',
  kinds.every(([id]) => page.includes(`"${id}"`)));
ok('the district hues the labels borrow are the registry\'s own',
  reg.counts.district_hues === Object.keys(districts).length);

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`labels/test: ${n} checks passed — ${kinds.length} kinds, `
  + `${shapes.length} shapes, ${reg.focus.cone_deg}-degree focus cone`);
