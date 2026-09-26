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
/* A LIST IS NOT A NAME. Every other kind in this registry is a name-plate
   or a mark - one line of words, as wide as those words are. The placard
   is the only kind whose content is a LIST, and while it wore a `plate` a
   room requiring seven things wore a sign twenty-two times wider than it
   was tall: 670 px across a 1280 px screen, measured at eye level in a
   hall. The shape is the fix, not a threshold. */
ok('the one kind that carries a list is drawn as a board and not as a '
   + 'name-plate, and the board is a shape of its own that no other kind '
   + 'wears',
  reg.kinds.placard.shape === 'board'
  && reg.shapes.board.reads_as.includes('down rather than across')
  && kinds.filter(([, k]) => k.shape === 'board').length === 1
  && typeof reg.shapes.board.head_px === 'number'
  && reg.shapes.board.head_px > 0);

/* WHERE IT HANGS IS A DECISION, AND SO IS THE TIE. A board hangs beside
   the way into its room nearest the hall's centre line. Two jambs are the
   same distance from that line when the doorway sits exactly on it - 15
   of the 881 rooms that hang a board - and that side is NAMED here with
   its reason rather than left to whichever way a comparison of two equal
   numbers falls, which is the fault the rule itself was written to end. */
ok('the placard says where it hangs, and the one tie that leaves names a '
   + 'side with a reason beside it rather than a preference',
  reg.kinds.placard.hangs.includes('centre line')
  && ['-x', '+x'].includes(reg.kinds.placard.jamb_on_centre)
  && reg.kinds.placard.jamb_on_centre_why.length > 80
  && /\bevidence\b/.test(reg.kinds.placard.jamb_on_centre_why));

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

/* ------------------------------------------------------------ legibility ---
   A sign should be READABLE, not only told apart, and until this block
   nothing measured it. The registry's ratios are recomputed here from the
   surfaces catalogue and this palette with an implementation written
   independently of the builder's (WCAG 2.x, sRGB D65, source-over
   compositing, the focus tint as a linear-light product), and must agree
   to three decimals. The paint contract is held to the page's fills; the
   authored palette is parsed out of the builder's source so a plate or text
   colour cannot move without an `adjusted` entry beside it; and the
   surfaces cross-read is stamped so a catalogue that moved after this was
   built fails here. */
const surf = JSON.parse(readFileSync(new URL('../surfaces/registry/finishes.json', import.meta.url)));
const LEG = reg.legibility;
const parseC = (c) => {
  if (/^#[0-9a-f]{6}$/i.test(c)) return [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)).concat([1]);
  const m = /^rgba\((\d+),(\d+),(\d+),(\d*\.?\d+)\)$/.exec(c.trim());
  if (!m) throw new Error(`unreadable colour ${c}`);
  return [+m[1], +m[2], +m[3], +m[4]];
};
const chan = (v) => { const x = v / 255; return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; };
const W = [0.2126, 0.7152, 0.0722];
const Y = (c) => W.reduce((a, w, i) => a + w * chan(c[i]), 0);
const Yt = (c, t) => W.reduce((a, w, i) => a + w * chan(c[i]) * chan(t[i]), 0);
const cr = (p, q) => (Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05);
const contrast = (a, b) => cr(Y(a), Y(b));
const blend = (fg, bg) => [0, 1, 2].map((i) => fg[i] * fg[3] + bg[i] * (1 - fg[3])).concat([1]);
const near3 = (a, b) => Math.abs(a - b) < 0.0006;
const fam = {
  floor: Object.fromEntries(Object.entries(surf.catalogue).map(([id, f]) => [id, f.color])),
  wall: Object.fromEntries(Object.entries(surf.wall_catalogue).map(([id, w]) => [id, w.color])),
  wainscot: Object.fromEntries(Object.entries(surf.wall_catalogue).filter(([, w]) => w.wainscot_m > 0)
    .map(([id, w]) => [id, w.wainscot])),
};
const worstOf = (fn) => {
  let best = null;
  for (const [f, cols] of Object.entries(fam)) for (const [id, c] of Object.entries(cols)) {
    const r = fn(parseC(c)); if (!best || r < best.ratio) best = { ratio: r, family: f, finish: id };
  }
  return best;
};
const same = (a, b) => near3(a.ratio, b.ratio) && a.family === b.family && a.finish === b.finish;
const readoutBox = /case 'readout':\s*g\.fillStyle = '(rgba\([^)]*\))';/.exec(page)?.[1];
ok('the paint contract says what the page fills: ink titles, muted sub lines, the plate; a readout in its accent on a box the page owns; a ghost with no plate',
  Object.keys(reg.paint).sort().join() === Object.keys(reg.shapes).sort().join()
  && /g\.fillStyle = shape === 'readout' \? accent : LPAL\.ink;/.test(page)
  && /g\.fillStyle = shape === 'ghost' \? LPAL\.ink : LPAL\.muted;/.test(page)
  && /g\.fillStyle = LPAL\.plate;\s*switch \(shape\)/.test(page)
  && /case 'ghost':\s*break;/.test(page)
  && Object.entries(reg.paint).every(([sh, p]) => sh === 'ghost' ? (p.title === 'ink' && p.sub === 'ink' && p.plate === 'none')
    : sh === 'readout' ? (p.title === 'accent' && p.sub === 'muted' && p.plate === 'page')
      : (p.title === 'ink' && p.sub === 'muted' && p.plate === 'plate'))
  && readoutBox && LEG.readout_box.color === readoutBox);
ok('every palette key has exactly one role - text, plate or accent - and the roles cover the palette',
  Object.values(reg.palette_roles).flat().sort().join() === Object.keys(reg.palette).sort().join()
  && reg.palette_roles.text.includes('ink') && reg.palette_roles.plate.includes('plate'));
/* the authored palette, parsed out of the builder's source: a registry
   colour that differs from it must carry an `adjusted` entry with its
   numbers, or the change was silent */
const srcText = src.toString('utf8');
const authoredMatch = /PALETTE_AUTHORED = \{([\s\S]*?)\n\}/.exec(srcText);
const authoredBlock = authoredMatch ? authoredMatch[1] : '';
const authored = Object.fromEntries([...authoredBlock.matchAll(/'([a-z_]+)':\s*'([^']+)'/g)].map((m) => [m[1], m[2]]));
const adjustedFor = Object.fromEntries(LEG.adjusted.map((a) => [a.role, a]));
ok(`the registry palette is the authored one in the builder's source, except where an adjusted entry records the move (${LEG.adjusted.length} adjusted)`,
  Object.keys(authored).length === Object.keys(reg.palette).length
  && Object.entries(reg.palette).every(([k, v]) => (k in adjustedFor
    ? adjustedFor[k].from === authored[k] && adjustedFor[k].to === v && v !== authored[k]
    : v === authored[k])));
ok('every adjusted entry names its role, both colours, a reason, and a ratio after that clears 4.5:1 and beats the ratio before',
  Array.isArray(LEG.adjusted) && LEG.adjusted.every((a) => a.role in reg.palette && /^#|^rgba/.test(a.from)
    && /^#|^rgba/.test(a.to) && a.why.length > 20 && a.ratio_after >= 4.5 && a.ratio_after > a.ratio_before));
/* every kind, recomputed */
const mark = parseC(reg.palette.mark);
let allOk = true, worstTitle = Infinity, worstSub = Infinity;
for (const [id, k] of kinds) {
  const e = LEG.roles[id], p = reg.paint[k.shape];
  const text = (role) => parseC(role === 'accent' ? reg.palette[k.accent === 'district' ? 'mark' : k.accent] : reg.palette[role]);
  const title = text(p.title), sub = text(p.sub);
  if (e.shape !== k.shape || e.title !== p.title || e.sub !== p.sub || e.plate !== p.plate) { allOk = false; break; }
  if (p.plate === 'none') {
    const below = Object.values(fam).flatMap((c) => Object.values(c)).filter((c) => contrast(title, parseC(c)) < 4.5).length;
    if (!same(e.title_on_finish, worstOf((bg) => contrast(title, bg)))
      || !same(e.sub_on_finish, worstOf((bg) => contrast(sub, bg))) || e.below_4_5_finishes !== below) { allOk = false; break; }
    continue;
  }
  const plate = parseC(p.plate === 'page' ? readoutBox : reg.palette[p.plate]);
  const tOn = worstOf((bg) => contrast(title, blend(plate, bg)));
  const sOn = worstOf((bg) => contrast(sub, blend(plate, bg)));
  const pOn = worstOf((bg) => contrast(blend(plate, bg), bg));
  const pBelow = Object.values(fam).flatMap((c) => Object.values(c)).filter((c) => contrast(blend(plate, parseC(c)), parseC(c)) < 3).length;
  const tTint = worstOf((bg) => cr(Yt(title, mark), Yt(blend(plate, bg), mark)));
  const sTint = worstOf((bg) => cr(Yt(sub, mark), Yt(blend(plate, bg), mark)));
  if (!same(e.title_on_plate, tOn) || !same(e.sub_on_plate, sOn) || !same(e.plate_on_finish, pOn)
    || e.plate_below_3_finishes !== pBelow || !same(e.focus_tint.title_on_plate, tTint)
    || !same(e.focus_tint.sub_on_plate, sTint)) { allOk = false; break; }
  worstTitle = Math.min(worstTitle, tOn.ratio); worstSub = Math.min(worstSub, sOn.ratio);
  if (tOn.ratio < 4.5 || sOn.ratio < 4.5 || tTint.ratio < 3 || sTint.ratio < 3) { allOk = false; break; }
}
ok(`every kind's text on its own plate, its plate on every finish and its focus-tinted lines recompute to 3 decimals over ${Object.values(fam).reduce((a, c) => a + Object.keys(c).length, 0)} finishes`,
  allOk && Object.keys(LEG.roles).sort().join() === kinds.map(([id]) => id).sort().join()
  && Object.entries(LEG.finishes_measured).every(([f, k]) => k === Object.keys(fam[f]).length));
ok(`every title and sub line clears 4.5:1 on its own plate over every finish (worst title ${worstTitle.toFixed(3)}, worst sub ${worstSub.toFixed(3)}), and 3:1 under the focus tint`,
  allOk && near3(LEG.worst_title_on_plate, worstTitle) && near3(LEG.worst_sub_on_plate, worstSub)
  && worstTitle >= 4.5 && worstSub >= 4.5 && LEG.thresholds.normal_text === 4.5 && LEG.thresholds.focus_tint_floor === 3
  && /refuses and names the kind/.test(LEG.rule));
ok('the surfaces catalogue was read as it stands now (cross-read stamp and the colours themselves)',
  LEG.surfaces_stamp === surf.source_stamp
  && LEG.catalogue_sha === createHash('sha256').update(
    `{${Object.keys(fam).sort().map((f) => `${JSON.stringify(f)}: {${Object.keys(fam[f]).sort().map((id) => `${JSON.stringify(id)}: ${JSON.stringify(fam[f][id])}`).join(', ')}}`).join(', ')}}`)
    .digest('hex').slice(0, 16));

console.log(`labels/test: ${n} checks passed — ${kinds.length} kinds, `
  + `${shapes.length} shapes, ${reg.focus.cone_deg}-degree focus cone`);
