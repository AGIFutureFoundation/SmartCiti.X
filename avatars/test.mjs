/**
 * Avatar pack verification.
 *
 * The locker is a contract with the learner: 15–20 options in every
 * section, a crew seat for every hall on the roster, every one free, and
 * none of it able to touch a score. The guarantee and the marks policy
 * are asserted here, and the sections are held to the shape the wheel
 * renders from — a wedge with nothing to draw is a broken locker, and a
 * wedge with nothing to SAY is an unreadable one, so the name and the
 * hazard note are contract too.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/avatars.json', import.meta.url)));
const unions = JSON.parse(readFileSync(new URL('../unions/registry/unions.json', import.meta.url))).unions;

const std = reg.sections.filter((s) => s.kind !== 'crew');
const crew = reg.sections.find((s) => s.kind === 'crew');
const sec = (id) => reg.sections.find((s) => s.id === id);
const ids = (id) => new Set(sec(id).options.map((o) => o.id));
const opt = (sid, oid) => sec(sid).options.find((o) => o.id === oid);

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
/* The wheel draws a two-letter glyph and no words at all, so an option
   that is not named cannot be told from the one beside it, and two
   options sharing a name, a glyph or a swatch are one option wearing two
   ids. Both were true of this pack before: nothing carried a name. */
ok('every option says its own name, and no two in a section say the same one',
  reg.sections.every((s) => s.options.every((o) => typeof o.name === 'string'
    && o.name.trim().length > 1)
    && new Set(s.options.map((o) => o.name)).size === s.options.length));
ok('nothing is a duplicate wearing another id: one glyph per wedge, one colour per swatch',
  reg.sections.every((s) => s.kind === 'color'
    ? new Set(s.options.map((o) => o.value.toLowerCase())).size === s.options.length
    : new Set(s.options.map((o) => o.glyph)).size === s.options.length));
ok('the body is a real range: 16 build combinations, 18 skin tones, 18 hairstyles, 15 eye colours, 19 facial-hair cuts',
  sec('build').options.length === 16 && sec('skin').options.length === 18
  && sec('hair').options.length === 18 && sec('eyes').options.length === 15
  && sec('facialhair').options.length === 19);
ok('textured hair is wearable to work: afro, braids, locs, cornrows and twists all on the rack',
  ['afro', 'braids', 'locs', 'cornrows', 'twists'].every((i) => ids('hair').has(i)));
ok('the wardrobe is complete: headwear (hard hats AND ball caps), tops, vest, trousers, footwear, tools, outerwear, extras, costumes',
  ['headwear', 'headcolor', 'top', 'topcolor', 'vest', 'pants',
   'pantscolor', 'shoes', 'tools', 'outer', 'extras', 'costume'].every((id) =>
    reg.sections.some((s) => s.id === id))
  && ['hard-cap', 'full-brim', 'ball-cap', 'ball-cap-back'].every((id) =>
    ids('headwear').has(id)));
ok('everyday work stays the default: outerwear, extras and costume all open on none',
  ['outer', 'extras', 'costume'].every((id) => reg.defaults[id] === 'none'
    && ids(id).has('none')));
/* One work-palette, offered whole to all three cloth sections. The
   slices this pack used to take forbade a white hard hat and hi-vis
   trousers, both of which are ordinary workwear. */
ok('the cloth palette is offered whole: headwear, top and trousers all reach white and both hi-vis hues',
  ['headcolor', 'topcolor', 'pantscolor'].every((id) =>
    sec(id).options.length === 18
    && ['white', 'hi-vis-orange', 'hi-vis-yellow'].every((c) => ids(id).has(c))));

/* ------------------------------------------------- the hazard notes ----- */
/* Kit sections hold nothing but protective equipment and trade belts, so
   every option in them names the hazard or the trade it answers; the
   wardrobe sections name it only on the pieces that are equipment rather
   than clothes. The rule is restated here rather than read from the
   registry - a rule that reads itself out of the file it is grading
   proves nothing. */
const NOTE_ALL = ['headwear', 'vest', 'shoes', 'tools', 'outer', 'extras'];
const NOTE_SOME = {
  top: ['coveralls', 'hi-vis-tee', 'thermal', 'rain-shell', 'fr-shirt',
        'hi-vis-long-sleeve', 'sun-hoodie', 'smock'],
  pants: ['insulated', 'rain-pants', 'hi-vis', 'painter-white', 'fr-pants',
          'hi-vis-class-e', 'knee-pad-pants', 'saw-chaps', 'hip-waders'],
};
const noted = (s) => s.options.filter((o) => o.note).map((o) => o.id).sort();
ok('every piece of kit names the hazard or the trade it answers, and only kit does',
  NOTE_ALL.every((id) => sec(id).options.every((o) => o.note))
  && Object.entries(NOTE_SOME).every(([id, want]) =>
    JSON.stringify(noted(sec(id))) === JSON.stringify([...want].sort()))
  && reg.sections.filter((s) => !NOTE_ALL.includes(s.id)
    && !(s.id in NOTE_SOME)).every((s) => s.options.every((o) => !o.note)));
ok('a note is a sentence, and no note is used twice anywhere in the locker',
  (() => {
    const all = reg.sections.flatMap((s) => s.options).filter((o) => o.note)
      .map((o) => o.note);
    return all.length >= 100 && new Set(all).size === all.length
      && all.every((t) => t.length >= 40 && t.endsWith('.'));
  })());

/* --------------------------------------------------- families of kit ---- */
/* Graded kit is only useful whole. Each of these families was partial:
   two visibility classes of three, one harness of four, two respiratory
   classes of five - and a locker that offers part of a family teaches
   the gap. */
ok('high-visibility spans all three classes, lowest to highest',
  ['hi-vis-1', 'hi-vis-2', 'hi-vis-3'].every((i) => ids('vest').has(i))
  && [...ids('vest')].filter((i) => i.startsWith('hi-vis-')).length === 3);
ok('the ensemble rule is wearable: a sleeved hi-vis top and hi-vis trousers both exist',
  ids('top').has('hi-vis-long-sleeve') && ids('pants').has('hi-vis-class-e')
  && /sleeves/.test(opt('vest', 'hi-vis-3').note));
ok('four fall-protection harnesses, each naming the D-ring the line clips to',
  (() => {
    const h = sec('vest').options.filter((o) => o.id.startsWith('harness'));
    return h.length === 4 && h.every((o) => /D-ring/.test(o.note))
      && /dorsal/.test(opt('vest', 'harness').note)
      && /Hip/i.test(opt('vest', 'harness-position').note)
      && /Shoulder/i.test(opt('vest', 'harness-suspension').note)
      && /sternal/i.test(opt('vest', 'harness-ladder').note);
  })());
ok('every extra declares the body region it occupies, from one vocabulary',
  sec('extras').options.every((o) => ['none', 'eyes', 'ears', 'airway',
    'face', 'head', 'hands', 'arms', 'legs', 'torso'].includes(o.slot)));
ok('respiratory protection spans five classes, from filtering facepiece to supplied air',
  (() => {
    const air = sec('extras').options.filter((o) => o.slot === 'airway');
    return air.length === 5
      && ['dust-mask', 'respirator', 'full-face-apr', 'papr-hood',
          'supplied-air'].every((i) => ids('extras').has(i));
  })());
ok('the powered hood says why it exists: a tight mask cannot seal over facial hair, and this locker holds nineteen beards',
  /facial hair/.test(opt('extras', 'papr-hood').note)
  && /fit-tested/.test(opt('extras', 'respirator').note)
  && sec('facialhair').options.length === 19);
ok('both hearing-protection fits are offered, because the choice is a fit question',
  ['ear-muffs', 'ear-plugs'].every((i) => ids('extras').has(i))
  && /hood/.test(opt('extras', 'ear-plugs').note));
ok('correction and impact protection come in one pair: prescription safety glasses are on the rack',
  ids('extras').has('rx-safety-glasses')
  && opt('extras', 'rx-safety-glasses').slot === 'eyes');
ok('heat is dressed head to foot: vented shell, sun shade, sun hoodie, cooling vest, mesh',
  ['vented-cap', 'sun-shade'].every((i) => ids('headwear').has(i))
  && ids('top').has('sun-hoodie')
  && ['cooling-vest', 'mesh'].every((i) => ids('vest').has(i)));
ok('cold is dressed head to foot: liner under the shell, heated and insulated layers, pac boots',
  ids('headwear').has('hard-cap-liner')
  && ['heated-liner', 'insulated-coverall'].every((i) => ids('outer').has(i))
  && ids('shoes').has('insulated-pac'));
ok('the boot is rated feature by feature, not by its toe alone',
  ['met-guard', 'eh-rated', 'puncture-sole'].every((i) => ids('shoes').has(i))
  && /not an insulator/.test(opt('shoes', 'eh-rated').note));
ok('the cautions are stated where kit is easiest to mistake: vented shells and bump caps',
  /no electrical rating/.test(opt('headwear', 'vented-cap').note)
  && /not\s+impact-rated/.test(opt('headwear', 'bump-cap').note)
  && /under a shell/.test(opt('headwear', 'winter-liner').note));
ok('twenty tool belts, the line trades, sheet metal, painters, millwrights and cabling among them',
  sec('tools').options.length === 20
  && ['lineman', 'sheet-metal', 'painter', 'millwright',
      'low-voltage'].every((i) => ids('tools').has(i)));

/* ----------------------------------------------------------- characters --- */
const secIds = Object.fromEntries(
  reg.sections.map((s) => [s.id, new Set(s.options.map((o) => o.id))]));
ok('twenty-two one-tap characters, each with a name, an emoji and a line of story',
  reg.characters.length === 22
  && new Set(reg.characters.map((c) => c.id)).size === 22
  && reg.characters.every((c) => c.name && c.emoji && c.blurb?.length > 20));
ok('every character is made of the locker: each cfg value resolves to a real option',
  reg.characters.every((c) =>
    Object.keys(c.cfg).length === reg.sections.length
    && Object.entries(c.cfg).every(([k, v]) => secIds[k]?.has(v))));
/* An option nobody is ever seen wearing is an option nobody finds, so the
   families added to the rack are worn by somebody on the character tab. */
ok('the new kit is worn: somebody on the character tab carries each family',
  [['vest', 'harness-suspension'], ['extras', 'supplied-air'],
   ['vest', 'cooling-vest'], ['outer', 'insulated-coverall'],
   ['shoes', 'eh-rated'], ['top', 'fr-shirt'],
   ['headwear', 'hard-cap-liner'], ['tools', 'lineman'],
   ['pants', 'hi-vis-class-e']].every(([s, o]) =>
    reg.characters.some((c) => c.cfg[s] === o)));
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
/* The generator used to step through the sections on typed moduli (16,
   15, 14...) - a second copy of every count, which went stale the moment
   a section grew and quietly stranded its new options. It now reads the
   lengths, so a full section is a fully walked one. */
ok('the TradeApe generator walks whole sections: no option of a walked section is stranded',
  ['build', 'eyes', 'headcolor', 'topcolor', 'pantscolor', 'shoes']
    .every((id) => new Set(reg.tradeapes.apes.map((t) => t.cfg[id])).size
      === Math.min(sec(id).options.length, 111))
  && new Set(reg.tradeapes.apes.map((t) => t.cfg.tools)).size
    === sec('tools').options.length - 1
  && reg.tradeapes.apes.every((t) => t.cfg.tools !== 'none'));
ok('the ape reference is measurements-only, and says so',
  (() => { const r = reg.tradeapes.ape_reference;
    return Math.abs(r.span_to_height - r.span / r.height) < .01
      && Math.abs(r.depth_to_height - r.depth / r.height) < .01
      && /measurements\s+only/.test(r.provenance)
      && /not shipped/.test(r.provenance)
      && /no third-party artwork/.test(r.provenance); })());
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
ok('twelve emotes, each with an emoji, a label, a procedural move and a line saying what it is',
  reg.emotes.length === 12
  && reg.emotes.every((e) => e.id && e.emoji && e.label && e.move
    && e.note?.endsWith('.'))
  && new Set(reg.emotes.map((e) => e.id)).size === reg.emotes.length
  && new Set(reg.emotes.map((e) => e.move)).size === reg.emotes.length
  && new Set(reg.emotes.map((e) => e.emoji)).size === reg.emotes.length);
/* Borrowing the yard's hand vocabulary for a cosmetic emote is fine;
   letting it read as a qualification is not, so the registry says out
   loud what playing one does not confer. */
ok('the gesture emotes disclaim what they are not: a shape played on a pedestal, not a qualification',
  ['hoist', 'lower', 'stop', 'tie-off'].every((id) =>
    reg.emotes.some((e) => e.id === id))
  && /not a signalperson qualification/.test(reg.gestures)
  && /qualified\s+signalperson signals/.test(reg.gestures));
ok('the guarantee is stated: cosmetic only, free, and score-blind',
  /cosmetic only/.test(reg.guarantee) && /free and unlocked/.test(reg.guarantee)
  && /scoring/.test(reg.guarantee));
/* Four provenance words carry weight across this bundle, and one of them
   belongs to another pack: orbis/ owns AI-SYNTHESIZED. Avatar parts are
   AUTHORED - typed from public knowledge, not checked against any
   standard this build can read - and the notes must not read as the
   standard itself. */
ok('the parts declare AUTHORED provenance, and say the notes are not the standard',
  /^AUTHORED/.test(reg.provenance) && /not cross-checked/.test(reg.provenance)
  && /not a substitute/.test(reg.provenance)
  && /nothing here is graded/.test(reg.provenance));
ok('no part of the locker claims a synthesis provenance that another pack owns',
  !/synthes/i.test(JSON.stringify(reg)));

// The guarantee holds in code, not just in prose: the page's grading and
// progress recording must never read the avatar record.
const page = readFileSync(new URL('../web/build_3d.py', import.meta.url), 'utf8');
const simResults = page.slice(page.indexOf('function simResults'),
  page.indexOf('function simResults') + 2200);
ok("the page's grader never reads the avatar record",
  !/avatar/i.test(simResults));
/* The page draws the wardrobe from keyed tables, and a key with no option
   behind it is geometry nothing can reach - the shape a renamed or
   dropped option leaves behind. Every key in the four tables that dress
   the avatar has to be a real id of the section it is keyed on. */
const between = (from, to) => {
  const a = page.indexOf(from);
  return a < 0 ? '' : page.slice(a + from.length, page.indexOf(to, a));
};
const keysOf = (blob, re) => [...blob.matchAll(re)].map((m) => m[1]);
const tables = [
  ['costume', between('let CS = {', '}[cfg.costume]'), /['\s]([a-z0-9-]+)'?\s*:\s*\{/g],
  ['outer', between('const OUTER = !CS && {', '}[cfg.outer]'), /['\s]([a-z0-9-]+)'?\s*:\s*\{/g],
  ['shoes', between('const shoeHex = {', '}[cfg.shoes]'), /([a-z0-9-]+)'?\s*:\s*'#[0-9a-f]{6}'/g],
  ['tools', between('const n = { basic:', '}[cfg.tools]'), /([a-z0-9-]+)\s*:\s*\d/g],
];
ok('the page draws no dead option: every key in its costume, outerwear, footwear and tool-belt tables is a real id',
  tables.every(([id, blob, re]) => {
    const keys = keysOf(blob, re);
    return keys.length >= 10 && keys.every((k) => ids(id).has(k));
  }));

/* -------------------------------------------------------- the dashboard --- */
const dash = readFileSync(
  new URL('../web/trade_craft_dashboard.html', import.meta.url), 'utf8');
ok('the network dashboard renders the locker-section / TradeApes count',
  dash.includes(`${reg.sections.length} / ${reg.tradeapes.apes.length}`));
ok('the network dashboard carries the cosmetic-only guarantee',
  dash.includes(reg.guarantee));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`avatars/test: ${n} checks passed — ${reg.sections.length} sections, `
  + `${std.reduce((a, s) => a + s.options.length, 0)} options + 111 crews, `
  + `${reg.sections.flatMap((s) => s.options).filter((o) => o.note).length} hazard notes, `
  + `${reg.emotes.length} emotes`);
