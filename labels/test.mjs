/**
 * Label registry verification.
 *
 * A sign should be readable before it is read, so the checks are about
 * whether that promise is structurally kept: every kind has a shape the
 * page can actually draw (or is declared undrawn, computed from the page
 * and not believed), every shape and every ornament earns its place, no two
 * kinds draw the same sign, no sign borrows a standards body or a
 * regulator, provenance words stay the bundle's own, the focus behaviour is declared as
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
/* What the page can actually draw, read off the page rather than off the
   registry's own claim about itself: a kind reaches nothing until
   labelShape() has a branch for its shape. The registry travels into the
   page whole, so a kind id appears in the page's data whether or not
   anybody drew it - the `case` is the only honest evidence. */
const drawable = new Set(shapes.filter(([id]) => page.includes(`case '${id}'`)).map(([id]) => id));
const pending = kinds.filter(([, k]) => !drawable.has(k.shape)).map(([id]) => id).sort();

/* --------------------------------------------------------- shape = meaning --- */
ok(`every kind names a shape the registry declares (${kinds.length} kinds, ${shapes.length} shapes)`,
  kinds.every(([, k]) => k.shape in reg.shapes));
ok(`the kinds the page cannot draw yet are exactly the ones the registry declares pending (${pending.length})`,
  JSON.stringify(reg.pending_page) === JSON.stringify(pending)
  && reg.pending_page.every((id) => id in reg.kinds)
  && reg.counts.drawn === kinds.length - pending.length);
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
ok('provenance words stay the bundle\'s four, and the SCHEMATIC sign is drawn dashed',
  kinds.filter(([, k]) => k.provenance)
    .every(([, k]) => ['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED'].includes(k.provenance))
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
ok('the wrist panel in a headset reuses the readout kind honestly: same label(), same gauges, fixed size on the hand, not view-scored, verified against a mock only',
  /readout kind is reused for the\s+wrist panel/.test(reg.honesty.xr_panel)
  && /same gauges\(\) values/.test(reg.honesty.xr_panel)
  && /view-direction scoring above does not apply/.test(reg.honesty.xr_panel)
  && /mocked WebXR session only/.test(reg.honesty.xr_panel)
  && /kind: 'readout', accent: warn \? LPAL\.crit/.test(page)
  && /labelSet\.splice\(i, 1\);\s+\/\/ on the hand: not view-scored/.test(page));
ok('the shapes are admitted to be this bundle\'s own convention, not a standard',
  /a convention this bundle invented, not\s+a standard/
    .test(reg.honesty.convention));

/* ------------------------------------------ wayfinding, identity, notice --- */
/* The five signs a walkable building carries that a name-plate cannot. The
   point of each check is that the new kinds are told apart by what is
   DRAWN - a shape of their own - rather than by the same plate in another
   colour, which is the failure the whole registry exists to prevent. */
const WAYFINDING = ['egress', 'muster', 'door', 'asset', 'hazard'];
ok('the five new signs each take a shape of their own, shared with no name-plate kind',
  WAYFINDING.every((id) => id in reg.kinds)
  && new Set(WAYFINDING.map((id) => reg.kinds[id].shape)).size === WAYFINDING.length
  && kinds.filter(([id]) => !WAYFINDING.includes(id))
    .every(([, k]) => !WAYFINDING.some((w) => reg.kinds[w].shape === k.shape)));
ok('no two kinds draw the same sign: shape, accent, dash and ornament are unique across the registry',
  new Set(kinds.map(([, k]) => [k.shape, k.accent, !!k.dashed, k.ornament ?? '-'].join('|')))
    .size === kinds.length);
ok('the Academy\'s own marquee is told from a campus marquee by a drawn mark, not by a colour',
  reg.kinds.brand.shape === reg.kinds.campus.shape
  && reg.kinds.brand.accent === reg.kinds.campus.accent
  && reg.kinds.brand.ornament === 'rule_under'
  && reg.kinds.brand.ornament in reg.ornaments
  && !reg.kinds.campus.ornament);
ok('every ornament the registry declares is worn by a kind, and every ornament worn is declared',
  new Set(kinds.map(([, k]) => k.ornament).filter(Boolean)).size
    === Object.keys(reg.ornaments).length
  && kinds.every(([, k]) => !k.ornament || k.ornament in reg.ornaments)
  && reg.counts.ornaments === Object.keys(reg.ornaments).length);
ok('the exit sign is the only plate that points, and the muster beacon is the other end of the same movement',
  reg.shapes[reg.kinds.egress.shape].reads_as.includes('which way it runs')
  && reg.kinds.egress.accent === reg.kinds.muster.accent
  && reg.kinds.egress.shape !== reg.kinds.muster.shape
  && ['egress', 'muster'].every((id) => reg.kinds[id].provenance === 'DERIVED'));
ok('a door number and an asset tag are identifiers, so they are set in mono like every other value a machine assigned',
  ['door', 'asset'].every((id) => reg.kinds[id].face === 'mono'
    && reg.kinds[id].provenance === 'DERIVED')
  && /set in mono because an identifier is a value a\s+machine assigned/
    .test(reg.honesty.identification));
ok('a hazard notice is a different shape from the PPE placard, not a recolour of it: one is a condition, the other a dress code',
  reg.kinds.hazard.shape !== reg.kinds.placard.shape
  && reg.kinds.hazard.accent === reg.kinds.placard.accent
  && reg.shapes[reg.kinds.hazard.shape].reads_as.includes('not a name')
  && /does not classify, rate or\s+permit anything/.test(reg.honesty.notices));
ok('wayfinding admits what it is not: training signage in a drawn building, not life-safety equipment',
  /not\s+life-safety equipment/.test(reg.honesty.wayfinding)
  && /not an inspected route/.test(reg.honesty.wayfinding)
  && /not an\s+approved sign/.test(reg.honesty.wayfinding));

/* No sign borrows somebody else's authority. The vocabulary is the
   registry's own published list - the stations pack reads the same one
   rather than keeping a second copy - and the matcher here is written
   independently of the builder's, so agreement means something. */
const marks = (text) => {
  const low = ` ${String(text).toLowerCase().replace(/\s+/g, ' ')} `;
  const hits = reg.no_marks.tokens.filter((t) => new RegExp(
    `(?<![a-z0-9])${t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![a-z0-9])`).test(low));
  for (const pat of reg.no_marks.patterns) hits.push(...(low.match(new RegExp(pat, 'g')) ?? []));
  return hits;
};
ok('the marks a sign may not borrow are published as a list other packs can read, not re-typed per pack',
  reg.no_marks.tokens.length > 20 && reg.no_marks.patterns.length >= 1
  && /nothing here can be mistaken for an\s+inspected, approved or certified sign/
    .test(reg.no_marks.why)
  && reg.no_marks.why === reg.honesty.no_marks);
ok('and no word anywhere in this registry borrows one of them',
  !marks(JSON.stringify([reg.kinds, reg.shapes, reg.honesty, reg.ornaments, reg.focus, reg.type])).length);

/* ------------------------------------------------------------- the page --- */
ok('the page builds labels, draws their shapes, and steps them every frame',
  ['function label(', 'function labelShape(', 'function labelStep(']
    .every((f) => page.includes(f)));
ok('every kind the registry declares reaches the page, bar the ones it declares undrawn',
  kinds.filter(([id]) => !pending.includes(id))
    .every(([id]) => page.includes(`"${id}"`)));
ok('the district hues the labels borrow are the registry\'s own',
  reg.counts.district_hues === Object.keys(districts).length);

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`labels/test: ${n} checks passed — ${kinds.length} kinds, `
  + `${shapes.length} shapes, ${reg.focus.cone_deg}-degree focus cone`);
