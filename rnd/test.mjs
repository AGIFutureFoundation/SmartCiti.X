/**
 * R&D registry verification.
 *
 * This pack's only claim is that it restates nothing: every value in it was
 * read out of a named file through a named locator, and the entry carries
 * both. That claim is checkable in exactly one way, and it is the way this
 * suite is built - it does not compare the registry against itself. It goes
 * back to the source files, in a different language, and re-derives.
 *
 * So every JSON locator is re-walked against the live registry it points
 * into; every regular-expression locator is re-run against the live file
 * and required to match exactly once; the scene baselines are re-parsed out
 * of web/eval_scene.mjs; the budget ceilings are recomputed from that file's
 * own multipliers with JavaScript's own Math.round (which is where the
 * builder had to reproduce it, since Python rounds half to even); the suite
 * table is re-joined from verify_all.sh's loop and README.md's table; the
 * backlog's renderer scan is re-run over web/, wiki/ and console/; and
 * every quoted negative finding is required to still be verbatim in the
 * file it was sliced from.
 *
 * Three of these are worth reading twice.
 *
 * THE BACKLOG IS RE-DERIVED, NOT COMPARED. `declared_unbuilt` is the
 * useful half of this pack and the easy half to fake: a hand-kept list
 * looks identical to a computed one until the day a pack gets wired up.
 * So this suite recomputes the whole scan - which registries exist, which
 * page generators name them, which of them declare their own
 * `honesty.not_built_yet` - and requires the published list to be exactly
 * the one that scan produces. Wire a registry into a page generator and
 * this check FAILS until rnd/ is rebuilt, which is the behaviour wanted.
 *
 * THE GAPS ARE RECOUNTED FROM THE REGISTRIES. Not from the numbers other
 * packs published about themselves - from the records. The PPE gap is
 * counted room by room out of surfaces/registry/finishes.json here, so it
 * is an independent count of the same thing props/ counted, not a second
 * copy of props/'s answer.
 *
 * THE CROSS-CHECKS MUST STILL DISAGREE - or agree. Two figures in this
 * bundle are recorded in two files with two different values. This suite
 * re-reads both halves of every cross-check and requires `agree` to be
 * what the files actually say. Fixing one of them does not break this
 * suite; it changes the answer, and the count of disagreements falls.
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const url = (p) => new URL(p, import.meta.url);
const ROOT = fileURLToPath(url('../'));
const read = (rel) => readFileSync(ROOT + rel, 'utf8');
const flat = (rel) => read(rel).split(/\s+/).join(' ');
const json = (rel) => JSON.parse(read(rel));

const reg = json('rnd/registry/rnd.json');
const manifest = json('pack/manifest.json');

const M = reg.measured;
const G = reg.gaps;
const U = reg.declared_unbuilt;
const Q = reg.open_questions;
const X = reg.cross_checks;
const payload = JSON.stringify(reg);

/** Resolve a dotted path, returning a sentinel rather than throwing, so a
 *  broken pointer fails the check it belongs to instead of the run. */
const MISSING = Symbol('missing');
const dig = (obj, dotted) => dotted.split('.').reduce(
  (o, k) => (o !== MISSING && o !== null && typeof o === 'object' && k in o ? o[k] : MISSING), obj);

/** Every match of a pattern, so "exactly once" is checkable rather than
 *  assumed. A locator that has started matching twice no longer identifies
 *  the thing it was written to identify. */
const hits = (rel, pattern) => read(rel).match(new RegExp(pattern, 'g')) ?? [];
const cap = (rel, pattern) => new RegExp(pattern).exec(read(rel));
const numOf = (s) => Number(String(s).replace(/[_,]/g, ''));
const jsround = (x) => Math.round(x);

/* ------------------------------------------------------------ the shape --- */
ok('the pack carries the same header every pack in this bundle carries',
  reg.pack === 'smartcitix-trade-craft-academy-rnd'
  && reg.pack_version === manifest.pack_version
  && /^\d{4}-\d{2}-\d{2}$/.test(reg.built) && reg.source_stamp.length === 16);
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256')
    .update(readFileSync(url('./build.py'))).digest('hex').slice(0, 16));
ok('the pack carries the DERIVED provenance word and never borrows orbis\'s',
  /^DERIVED: /.test(reg.honesty.status)
  && !payload.includes('AI-SYNTH' + 'ESIZED'));
ok('nothing in the payload is a URL - this pack reads files in this repo and '
  + 'nothing else',
  !/https?:\/\//.test(payload));
ok('every file the registry says it read exists, and there are enough of them '
  + 'for this to be a register of the bundle rather than of three files',
  reg.reads.length >= 25 && reg.reads.every((r) => existsSync(ROOT + r))
  && ['web/eval_scene.mjs', 'README.md', 'verify_all.sh', 'assets/REFERENCE.md']
    .every((r) => reg.reads.includes(r)));

/* ---------------------------------------------------------- the measured --- */
ok('every measured fact names its file, its locator, its tier, when it was '
  + 'taken, under what conditions and what took it',
  M.length > 0 && M.every((m) => reg.tiers.includes(m.tier)
    && typeof m.file === 'string' && existsSync(ROOT + m.file)
    && reg.reads.includes(m.file)
    && ['json', 'regex'].includes(m.locator.kind)
    && m.when.length >= 8 && m.conditions.length > 12
    && m.method.length > 12 && m.why.length > 12));
ok('every id is unique, so a pointer cannot be published twice with two values',
  new Set(M.map((m) => m.id)).size === M.length);

const jsonPtr = M.filter((m) => m.locator.kind === 'json');
ok(`all ${jsonPtr.length} json pointers still resolve in the live registry `
  + 'they point into, to the value published here',
  jsonPtr.length > 0 && jsonPtr.every((m) => {
    const got = dig(json(m.file), m.locator.path);
    return got !== MISSING && got === m.value;
  }));

const rePtr = M.filter((m) => m.locator.kind === 'regex');
ok(`all ${rePtr.length} regex pointers still match their file EXACTLY once, `
  + 'and still capture the value published here',
  rePtr.length > 0 && rePtr.every((m) => {
    if (hits(m.file, m.locator.pattern).length !== 1) return false;
    const c = cap(m.file, m.locator.pattern);
    if (!c) return false;
    const v = numOf(c[m.locator.group]);
    return m.locator.cast === 'int' ? v === m.value && Number.isInteger(v) : v === m.value;
  }));

/* The scene baselines are the only numbers a browser produced, so they are
   re-parsed from the harness here rather than trusted through the locator
   that produced them. */
const evalSrc = read('web/eval_scene.mjs');
const BASE = {};
for (const m of evalSrc.matchAll(/\n {2}([a-z]+):\s*\{ calls: ([\d_]+), tris: ([\d_]+), meshes: ([\d_]+) \}/g)) {
  BASE[m[1]] = { calls: numOf(m[2]), tris: numOf(m[3]), meshes: numOf(m[4]) };
}
ok('the measured scene baselines are the harness\'s own BASE table, view for '
  + 'view and column for column',
  Object.keys(BASE).length > 0
  && Object.entries(BASE).every(([v, row]) => Object.entries(row).every(([col, val]) =>
    M.some((m) => m.id === `eval.${v}.${col}` && m.value === val
      && m.tier === 'MEASURED-IN-BROWSER' && m.file === 'web/eval_scene.mjs')))
  && M.filter((m) => m.id.startsWith('eval.')).length
     === Object.keys(BASE).length * 3);
ok('the baseline carries the date and the rig the harness states, not a date '
  + 'this pack chose',
  M.filter((m) => m.id.startsWith('eval.')).every((m) =>
    evalSrc.includes(`Baseline measured ${m.when},`)
    && flat('web/eval_scene.mjs').includes(m.conditions)));

/* The reference models are re-parsed from the note the same way. */
const refRows = [...read('assets/REFERENCE.md')
  .matchAll(/\n\| `([A-Za-z0-9_.-]+\.glb)` \| ([\d.]+) \| ([\d,]+) \| (\d+) \| (\d+) \| (\d+) \| ([\d.]+) \| (\d+) \|/g)];
ok(`all ${refRows.length} reference models are re-parsed from assets/REFERENCE.md `
  + 'and every published figure matches the table',
  refRows.length >= 5 && refRows.every((r) =>
    M.some((m) => m.id === `reference.${r[1]}.triangles` && m.value === numOf(r[3]))
    && M.some((m) => m.id === `reference.${r[1]}.meshes` && m.value === numOf(r[4]))
    && M.some((m) => m.id === `reference.${r[1]}.materials` && m.value === numOf(r[5]))
    && M.some((m) => m.id === `reference.${r[1]}.textures_mb` && m.value === numOf(r[7]))));
ok('the two medians kit/ and props/ size themselves against are the note\'s '
  + 'own, and the note is labelled as un-re-runnable from here',
  M.find((m) => m.id === 'reference.block_median_tris').value
    === numOf(/The median mesh is (\d+) triangles/.exec(read('assets/REFERENCE.md'))[1])
  && M.find((m) => m.id === 'reference.house_median_tris').value
    === numOf(/a median mesh of (\d+) triangles/.exec(read('assets/REFERENCE.md'))[1])
  && M.filter((m) => m.file === 'assets/REFERENCE.md')
    .every((m) => m.tier === 'MEASURED-ELSEWHERE'));
ok('a figure taken off a file this repository does not contain is never '
  + 'labelled as measured in a browser here',
  M.filter((m) => m.tier === 'MEASURED-IN-BROWSER')
    .every((m) => ['web/eval_scene.mjs', 'web/build_3d.py'].includes(m.file)));
ok('the tier counts are the tiers, and every entry has one',
  reg.counts.measured === M.length
  && reg.counts.measured_in_browser + reg.counts.measured_elsewhere
     + reg.counts.computed_from_registry === M.length
  && reg.counts.measured_source_files === new Set(M.map((m) => m.file)).size);

/* The point of the whole pack, asserted directly: a distinctive measured
   value must not be sitting as a literal in this pack's own builder. If it
   is, the number was typed and the locator is decoration. */
const builder = read('rnd/build.py');
const typed = M.filter((m) => Number.isInteger(m.value) && m.value >= 1000)
  .filter((m) => builder.includes(String(m.value)));
ok('no measured value of any size is typed as a literal in rnd/build.py - '
  + `every one of the ${M.filter((m) => Number.isInteger(m.value) && m.value >= 1000).length} `
  + 'distinctive ones is read',
  typed.length === 0);

/* -------------------------------------------------------- the backlog ----- */
const registries = readdirSync(ROOT, { withFileTypes: true })
  .filter((d) => d.isDirectory() && d.name !== 'rnd'
    && existsSync(ROOT + d.name + '/registry'))
  .flatMap((d) => readdirSync(ROOT + d.name + '/registry')
    .filter((f) => f.endsWith('.json')).map((f) => `${d.name}/registry/${f}`))
  .sort();
const appRenderers = readdirSync(ROOT + 'web')
  .filter((f) => /^build_.*\.py$/.test(f)).map((f) => 'web/' + f)
  .concat(['web/groundtruth.py', 'web/interiors.py']).sort();
const drawnBy = (r) => appRenderers.filter((f) =>
  f.split('/')[0] !== r.split('/')[0] && read(f).includes(r));
const expectUnbuilt = registries.filter((r) => {
  const says = dig(json(r), 'honesty.not_built_yet');
  return says !== MISSING || drawnBy(r).length === 0;
}).sort();

ok('the registry scan is the whole tree, minus this pack, and the published '
  + 'consumer table covers every one of them',
  registries.length >= 30
  && registries.every((r) => r in reg.consumers)
  && Object.keys(reg.consumers).length === registries.length
  && reg.counts.registries_scanned === registries.length);
ok('the backlog is exactly what a fresh scan produces - a registry wired into '
  + 'a page generator, or a not_built_yet removed, drops off and this check '
  + 'fails until rnd/ is rebuilt',
  JSON.stringify(U.map((u) => u.registry).sort()) === JSON.stringify(expectUnbuilt));
ok('the backlog is neither empty nor everything, so the signal is measuring '
  + 'the bundle rather than the scan',
  U.length > 0 && U.length < registries.length);
ok('every backlog entry that quotes a pack\'s own words quotes them exactly, '
  + 'from that pack\'s own honesty.not_built_yet',
  U.filter((u) => u.says !== null).length > 0
  && U.filter((u) => u.says !== null).every((u) =>
    u.says === dig(json(u.registry), 'honesty.not_built_yet')));
ok('no backlog entry claims nothing draws a registry that a page generator '
  + 'demonstrably opens',
  U.every((u) => {
    const drawn = drawnBy(u.registry);
    return JSON.stringify(drawn) === JSON.stringify(u.read_by_app_renderers)
      && (drawn.length === 0
        || u.reasons.every((r) => !r.startsWith('no page generator')));
  }));
ok('documented is not the same as drawn, and the entries that are only '
  + 'documented say which file documents them',
  U.filter((u) => u.read_by_doc_renderers.length && !u.read_by_app_renderers.length)
    .every((u) => u.reasons.some((r) => r.startsWith('it is DOCUMENTED'))
      && u.read_by_doc_renderers.every((f) => existsSync(ROOT + f)))
  && reg.counts.declared_unbuilt_documented_but_not_drawn
     === U.filter((u) => u.read_by_doc_renderers.length
       && !u.read_by_app_renderers.length).length);
ok('a pack reading its own registry never counts as a consumer, and the entry '
  + 'says what its own pack does with it instead',
  U.every((u) => [...u.read_by_app_renderers, ...u.read_by_doc_renderers,
    ...u.read_by_builders, ...u.read_by_suites]
    .every((f) => f.split('/')[0] !== u.registry.split('/')[0])
    && u.read_by_its_own_pack.every((f) => f.split('/')[0] === u.registry.split('/')[0]
      && existsSync(ROOT + f))));
ok('this pack excludes itself from every scan, or it would consume every '
  + 'registry in the tree and empty its own backlog',
  !reg.scanned.builders.some((b) => b.startsWith('rnd/'))
  && !Object.keys(reg.consumers).some((r) => r.startsWith('rnd/'))
  && !Object.values(reg.consumers).some((c) =>
    [...c.app_renderers, ...c.doc_renderers, ...c.builders, ...c.suites]
      .some((f) => f.startsWith('rnd/'))));

/* ------------------------------------------------------------- the gaps --- */
ok('every gap is arithmetic: the halves sum to the whole and the share is '
  + 'the quotient, to four places',
  G.length > 0 && G.every((g) => g.have + g.missing === g.of
    && Math.abs(g.share - Number((g.have / g.of).toFixed(4))) < 1e-9
    && Number.isInteger(g.have) && Number.isInteger(g.of) && g.of > 0));
ok('every gap names the files it was computed from, and every one of them '
  + 'exists and was read',
  G.every((g) => g.sources.length > 0
    && g.sources.every((s) => existsSync(ROOT + s) && reg.reads.includes(s))));
ok('closed gaps are kept in the list, so a closure can be checked rather '
  + 'than taken on trust',
  reg.counts.gaps === G.length
  && reg.counts.gaps_closed === G.filter((g) => g.share === 1).length
  && reg.counts.gaps_open === G.filter((g) => g.share < 1).length);

const halls = json('pack/registry/halls.json').halls;
const lessons = json('lessons/registry/lessons.json');
const fin = json('surfaces/registry/finishes.json').halls;
const gapOf = (id) => G.find((g) => g.id === id);

ok('the lesson-coverage gap is recounted here from the two registries, not '
  + 'read from either pack\'s summary of itself',
  gapOf('lessons.halls').have === new Set(lessons.spread.halls).size
  && gapOf('lessons.halls').of === halls.length);
ok('the simulator-binding gap is recounted from the seat registry\'s own '
  + 'hall bindings',
  gapOf('sims.halls').have
    === Object.keys(json('sims/registry/sims.json').hall_bindings).length
  && gapOf('sims.halls').of === halls.length);
ok('the PPE gap is recounted ROOM BY ROOM out of the surface registry here, '
  + 'so it is an independent count and not a copy of props/\'s answer',
  (() => {
    let ppe = 0, rooms = 0;
    for (const h of Object.values(fin)) {
      for (const c of Object.values(h.conditions)) { rooms++; if (c.ppe.length) ppe++; }
    }
    return gapOf('surfaces.ppe_rooms').have === ppe
      && gapOf('surfaces.ppe_rooms').of === rooms
      && json('props/registry/props.json').counts.rooms_requiring_ppe === ppe;
  })());
ok('the practitioner sign-off gap is recounted against the closed status set '
  + 'pack/hall_signoff.mjs declares, and it is still zero of the whole roster',
  (() => {
    const claiming = /return status === '([a-z -]+)';/.exec(read('pack/hall_signoff.mjs'))[1];
    const signed = halls.filter((h) => h.content_status === claiming).length;
    return gapOf('pack.signed_off_halls').have === signed
      && gapOf('pack.signed_off_halls').of === halls.length;
  })());
ok('the locale-review gap is recounted from each catalog\'s own '
  + 'translation_status field',
  (() => {
    const files = readdirSync(ROOT + 'i18n/locales').filter((f) => f.endsWith('.json')).sort();
    const reviewed = files.filter((f) =>
      json('i18n/locales/' + f).translation_status.includes('reviewed')).length;
    return gapOf('i18n.reviewed_locales').have === reviewed
      && gapOf('i18n.reviewed_locales').of === files.length;
  })());
ok('the scored-views gap is recounted from the harness against the views the '
  + 'page generator actually sets',
  (() => {
    const pageViews = new Set([...read('web/build_3d.py').matchAll(/view = '([a-z]+)'/g)]
      .map((m) => m[1]));
    const scored = Object.keys(BASE).filter((v) => pageViews.has(v)).length;
    return gapOf('eval.views_scored').have === scored
      && gapOf('eval.views_scored').of === pageViews.size;
  })());
ok('the widest gap the registry publishes is the widest gap in it, and it is '
  + 'published as a number rather than as a word',
  reg.counts.widest_gap_share === Math.min(...G.map((g) => g.share)));

/* ---------------------------------------------------------- the budgets --- */
const CALL_H = Number(/const CALL_HEADROOM = ([\d.]+);/.exec(evalSrc)[1]);
const TRI_H = Number(/const TRI_HEADROOM = ([\d.]+);/.exec(evalSrc)[1]);
ok('the headroom multipliers are the harness\'s own, so its policy moves '
  + 'every ceiling here with it',
  reg.budgets.multipliers.call_headroom === CALL_H
  && reg.budgets.multipliers.tri_headroom === TRI_H
  && reg.budgets.multipliers.source === 'web/eval_scene.mjs');
ok('every ceiling is recomputed here from the measured baseline and the '
  + 'harness\'s multiplier, with the harness\'s own rounding',
  Object.entries(BASE).every(([v, row]) => {
    const c = reg.budgets.currencies.draw_calls.views[v];
    const t = reg.budgets.currencies.triangles.views[v];
    return c.measured_baseline === row.calls && t.measured_baseline === row.tris
      && c.ceiling === jsround(row.calls * CALL_H)
      && t.ceiling === Math.trunc(row.tris * TRI_H);
  }));
ok('the budget arithmetic closes in both currencies and every view: headroom '
  + 'is the ceiling less the baseline, and what is left is the headroom less '
  + 'what is claimed',
  Object.values(reg.budgets.currencies).every((cur) =>
    Object.values(cur.views).every((r) =>
      r.ceiling - r.measured_baseline === r.headroom
      && r.headroom - r.claimed_total === r.left
      && r.left >= 0
      && Object.values(r.claimed_by).reduce((a, b) => a + b, 0) === r.claimed_total)));
ok('what kit/ and props/ have claimed is read from their own budget blocks, '
  + 'view for view, and neither exceeds the allowance it set itself',
  (() => {
    const kit = json('kit/registry/kit.json');
    const props = json('props/registry/props.json');
    const campus = reg.budgets.currencies.draw_calls.views.campus;
    const hall = reg.budgets.currencies.draw_calls.views[props.budget.ceiling_source.view];
    const hallT = reg.budgets.currencies.triangles.views[props.budget.ceiling_source.view];
    return campus.claimed_by.kit === kit.counts.campus_draw_calls
      && reg.budgets.currencies.triangles.views.campus.claimed_by.kit
         === kit.counts.campus_triangles
      && hall.claimed_by.props === props.budget.delta.draw_calls
      && hallT.claimed_by.props === props.budget.delta.triangles
      && Object.values(reg.budgets.currencies).every((cur) =>
        Object.values(cur.views).every((r) =>
          Object.entries(r.claimed_by).every(([p, v]) => v <= r.allowance_by[p])));
  })());
ok('every figure this pack recomputed from the harness agrees with the figure '
  + 'the pack that spends it published, or one of the three files is stale',
  reg.budget_agreements.length >= 6 && reg.budget_agreements.every((a) => {
    const [file, path] = a.agrees_with.split('#');
    return a.recomputed_from === 'web/eval_scene.mjs'
      && dig(json(file), path) === a.value;
  }));
ok('which currency is scarce is DERIVED from the harness\'s own multipliers, '
  + 'not decided here: exactly one is scarce, it is the one with the smaller '
  + 'multiplier, and its baseline already eats the larger share of its ceiling '
  + 'in every single view',
  Object.values(reg.budgets.currencies).filter((c) => c.scarce).length === 1
  && reg.budgets.currencies.draw_calls.headroom_multiplier === CALL_H
  && reg.budgets.currencies.triangles.headroom_multiplier === TRI_H
  && reg.budgets.currencies.draw_calls.scarce === (CALL_H < TRI_H)
  && Object.keys(BASE).every((v) =>
    reg.budgets.currencies.draw_calls.baseline_share_of_ceiling[v]
    > reg.budgets.currencies.triangles.baseline_share_of_ceiling[v]));
ok('and the packs are spending the CHEAP currency hard and the scarce one '
  + 'barely - which is the design working, and is visible only because both '
  + 'are published',
  Object.entries(reg.budgets.currencies.triangles.views)
    .filter(([, r]) => r.claimed_total > 0)
    .every(([v, r]) =>
      r.left_share < reg.budgets.currencies.draw_calls.views[v].left_share));

/* ----------------------------------------------------------- the suites --- */
const loop = /for t in (.*?); do/s.exec(read('verify_all.sh'))[1]
  .replace(/\\\s*\n/g, ' ').trim().split(/\s+/);
ok('the suite list is verify_all.sh\'s own loop, in its own order, and every '
  + 'file in it exists',
  JSON.stringify(reg.suites.rows.map((r) => r.suite)) === JSON.stringify(loop)
  && reg.suites.suites_run === loop.length
  && loop.every((t) => existsSync(ROOT + t)));
ok('every declared check count is README.md\'s own number for that suite, '
  + 're-parsed here from the table',
  reg.suites.rows.every((r) => {
    const m = new RegExp('^node ' + r.suite.replace(/[.\/]/g, '\\$&') + ' +# *(\\d+)? ', 'm')
      .exec(read('README.md'));
    const want = m && m[1] ? Number(m[1]) : null;
    return r.readme_checks === want && r.declared === (want !== null);
  }));
ok('the total is the sum of the declared counts, and the shortfall against '
  + 'the README headline is computed rather than reconciled by hand',
  reg.suites.declared_total
    === reg.suites.rows.filter((r) => r.declared)
      .reduce((a, r) => a + r.readme_checks, 0)
  && reg.suites.unaccounted_for === reg.suites.readme_headline - reg.suites.declared_total
  && reg.suites.readme_headline
     === numOf(/\n\*\*([\d,]+) checks, all passing/.exec(read('README.md'))[1]));
ok('the thin end and the thick end are both published, so the table cannot '
  + 'be read as uniform assurance',
  reg.suites.thinnest[0].checks === reg.suites.min
  && reg.suites.thickest[0].checks === reg.suites.max
  && reg.suites.min < reg.suites.max
  && reg.suites.thinnest.every((t) => reg.suites.rows
    .some((r) => r.suite === t.suite && r.readme_checks === t.checks)));
ok('a suite that runs without declaring a count is named rather than quietly '
  + 'dropped from the total',
  reg.suites.suites_without_a_count
    .every((s) => loop.includes(s)
      && !reg.suites.rows.find((r) => r.suite === s).declared)
  && reg.suites.suites_without_a_count.length
     === reg.suites.rows.filter((r) => !r.declared).length);

/* -------------------------------------------------- the open questions ---- */
ok('every open question quotes its source file VERBATIM, spans its own two '
  + 'anchors, and both anchors are unique in that file',
  Q.length > 0 && Q.every((q) => {
    const src = flat(q.file);
    return src.includes(q.quote)
      && q.quote.includes(q.anchors.from) && q.quote.includes(q.anchors.to)
      && src.split(q.anchors.from).length === 2
      && src.split(q.anchors.to).length === 2;
  }));
ok('a negative finding is never summarised, only quoted - the shortest quote '
  + 'here is still a whole sentence',
  Q.every((q) => q.quote.length >= 60 && /[.!?]$/.test(q.quote.trim())));
ok('the kinds are a closed set, and the bundle\'s recorded NEGATIVE findings '
  + 'are the larger half of them',
  Q.every((q) => ['negative-finding', 'unproved', 'unresolved-policy'].includes(q.kind))
  && reg.counts.negative_findings === Q.filter((q) => q.kind === 'negative-finding').length
  && reg.counts.negative_findings > Q.length / 2);
ok('every question says what is open and why it matters, and names a file '
  + 'that exists and was read',
  Q.every((q) => q.asks.length > 25 && q.why_it_matters.length > 40
    && existsSync(ROOT + q.file) && reg.reads.includes(q.file)));
ok('the negative findings are drawn from more than one corner of the bundle - '
  + 'a register that found them all in one file has only read one file',
  new Set(Q.filter((q) => q.kind === 'negative-finding').map((q) => q.file)).size >= 3);

ok('every cross-check re-reads both halves, and `agree` is what the two files '
  + 'actually say rather than what this pack remembers',
  X.length > 0 && X.every((c) => {
    const val = (h) => (h.pattern
      ? numOf(cap(h.file, h.pattern)[1])
      : h.value);
    if (h1(c)) return false;
    return val(c.a) === c.a.value && val(c.b) === c.b.value
      && c.agree === (c.a.value === c.b.value);
  }));
function h1(c) {
  // a half that quotes a pattern must still match its file exactly once
  for (const h of [c.a, c.b]) {
    if (h.pattern && hits(h.file, h.pattern).length !== 1) return true;
  }
  return false;
}
ok('the count of disagreements is the number of cross-checks that disagree, '
  + 'so fixing one lowers it without anybody editing this pack',
  reg.counts.cross_checks === X.length
  && reg.counts.cross_checks_disagreeing === X.filter((c) => !c.agree).length);
/* This check was written to catch the luminance disagreement being
   quietly fixed - and it fired, because the disagreement WAS fixed. It was
   not fixed by picking a winner, which is the outcome it was guarding
   against: the frame was gone, so neither 96 nor 89 could be shown right.
   It was fixed by having both files carry the SAME sentence stating that
   the two records disagree and that the true value is unknown. So the
   check now guards the repair rather than the defect: both files must
   carry the disclosure, the two disputed values must still be visible in
   it (a disclosure that drops the numbers discloses nothing), and the
   register must still refuse to call either one measured. */
ok('the luminance disagreement is disclosed identically in both files, '
  + 'still names both disputed values, and is not quietly resolved into a '
  + 'single number the frame can no longer justify',
  (() => {
    const c = X.find((x) => x.id === 'luminance.after-the-candela-conversion');
    const page = read('web/build_3d.py'), suite = read('web/test_3d.mjs');
    const phrase = /46 to 96 in this file, 46 to (\d+) in the suite/;
    const a = phrase.exec(page), b = phrase.exec(suite);
    if (!a || !b) return false;
    return numOf(a[1]) === 89 && numOf(b[1]) === 89
      && c.a.value === 89 && c.b.value === 89 && c.agree === true
      && /the frame that would settle which is right is gone/.test(page)
      && /the frame that would settle which is right is gone/.test(suite)
      && reg.measured.some((m) => /DISPUTED/.test(m.what));
  })());
ok('the hazard-free hall count the spec states in prose is checked against '
  + 'the number the surface registry actually holds',
  (() => {
    const c = X.find((x) => x.id === 'hazard-free-halls');
    const live = Object.values(fin).filter((h) => h.hazard === null).length;
    const said = numOf(/After extending it from their own words, (\d+) halls remain/
      .exec(read('SmartCitiX_TradeCraft_Academy_Spec.md'))[1]);
    return c.b.value === live && c.a.value === said && c.agree === (live === said);
  })());

/* ------------------------------------------------ what the pack admits ---- */
ok('the honesty block says this pack measures nothing itself, that the pack '
  + 'budgets are predictions, and that three of six views have ever been scored',
  /reaches no network, opens no browser and runs no harness/.test(reg.honesty.not_a_measurement)
  && /PREDICTIONS/.test(reg.honesty.predictions_are_not_measurements)
  && /no measured cost at all/.test(reg.honesty.three_views_of_six)
  && /does not flatter|only good news/.test(reg.honesty.does_not_flatter));
ok('it disclaims being a roadmap, and holds no schedule, owner or due date '
  + 'anywhere in the backlog',
  /not a plan and\s*not a commitment/.test(reg.honesty.not_a_roadmap)
  && U.every((u) => !('due' in u) && !('owner' in u) && !('priority' in u)
    && !('eta' in u)));
ok('the backlog states its own exit condition, so an entry cannot outlive the '
  + 'thing it describes',
  U.every((u) => /next build of rnd\//.test(u.drops_off_when)));
ok('the page contract names every piece of wiring a board would need and '
  + 'records nothing',
  ['data', 'route', 'measured', 'declared_unbuilt', 'gaps', 'budgets',
    'suites', 'open_questions', 'cross_checks', 'episode']
    .every((k) => typeof reg.page_contract[k] === 'string'
      && reg.page_contract[k].length > 30)
  && /nothing is recorded/i.test(reg.page_contract.episode));
ok('no real union local, employer or person is named anywhere in this register',
  !/\bLocal\s+\d|\bIBEW\b|\bUA\s+\d|\bLiUNA\b/i.test(payload));

/* ------------------------------------------------------------ the counts --- */
ok('the counts the registry publishes are the counts it actually holds',
  reg.counts.measured === M.length
  && reg.counts.declared_unbuilt === U.length
  && reg.counts.declared_unbuilt_by_their_own_words
     === U.filter((u) => u.says !== null).length
  && reg.counts.declared_unbuilt_not_drawn
     === U.filter((u) => u.read_by_app_renderers.length === 0).length
  && reg.counts.gaps === G.length
  && reg.counts.open_questions === Q.length
  && reg.counts.cross_checks === X.length
  && reg.counts.budget_views === Object.keys(BASE).length
  && reg.counts.budget_currencies === Object.keys(reg.budgets.currencies).length
  && reg.counts.budget_agreements === reg.budget_agreements.length
  && reg.counts.files_read === reg.reads.length
  && reg.counts.app_renderers_scanned === reg.scanned.app_renderers.length
  && reg.counts.doc_renderers_scanned === reg.scanned.doc_renderers.length
  && reg.counts.builders_scanned === reg.scanned.builders.length
  && reg.counts.suites_scanned === reg.scanned.suites.length
  && reg.counts.suites_run === reg.suites.suites_run
  && reg.counts.suite_checks_declared === reg.suites.declared_total);

const worst = G.reduce((a, b) => (a.share <= b.share ? a : b));
console.log(`rnd/test: ${n} checks passed — ${M.length} measured facts over `
  + `${new Set(M.map((m) => m.file)).size} files, every pointer re-resolved; `
  + `${U.length} of ${registries.length} registries declared-and-unbuilt; `
  + `${G.filter((g) => g.share < 1).length} open gaps, widest `
  + `${worst.id} at ${worst.have}/${worst.of}; `
  + `${reg.suites.declared_total} declared checks over ${loop.length} suites `
  + `(${reg.suites.min}–${reg.suites.max}); ${Q.length} open questions, `
  + `${reg.counts.negative_findings} of them negative findings; `
  + `${X.filter((c) => !c.agree).length} of ${X.length} cross-checks disagree`);
