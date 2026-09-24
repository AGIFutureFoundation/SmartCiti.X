/**
 * Sellable-package registry verification.
 *
 * A package is a commercial claim: this much of the bundle, for this trade,
 * with these seats in it and these ones not. Every claim here is RECOMPUTED
 * from the registries that own the underlying facts — the skill graph, the
 * seat bindings, the lessons, the union roster — and compared against what
 * the registry published. Nothing below reads a package's own count and
 * agrees with it.
 *
 * The two claims worth the most scrutiny are the two a seller is most
 * tempted to improve: the seat coverage (how little of a package carries a
 * simulator seat) and the duration (that nothing in this bundle declares
 * one, so no hour count can be honest). Both are re-derived here, and the
 * duration claim is re-scanned rather than believed.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };
const J = (x) => JSON.stringify(x);

const reg = JSON.parse(readFileSync(new URL('./registry/bundles.json', import.meta.url)));
const builder = readFileSync(new URL('./build.py', import.meta.url), 'utf8');
const skillRows = JSON.parse(readFileSync(
  new URL('../pack/registry/skills.json', import.meta.url))).skills;
const simsReg = JSON.parse(readFileSync(
  new URL('../sims/registry/sims.json', import.meta.url)));
const lessons = JSON.parse(readFileSync(
  new URL('../lessons/registry/lessons.json', import.meta.url))).lessons;
const unions = JSON.parse(readFileSync(
  new URL('../unions/registry/unions.json', import.meta.url))).unions;
const halls = JSON.parse(readFileSync(
  new URL('../pack/registry/halls.json', import.meta.url))).halls;
const manifest = JSON.parse(readFileSync(
  new URL('../pack/manifest.json', import.meta.url)));

const P = reg.packages;
const ids = Object.keys(P);
const districtOf = Object.fromEntries(unions.map((u) => [u.slug, u.district]));
const inDistrict = {};
for (const u of unions) (inDistrict[u.district] ??= []).push(u.slug);
const byId = new Map(skillRows.map((s) => [s.skill_id, s]));
const STRANDS = new Set(skillRows.map((s) => s.strand));
const TIERS = new Set(skillRows.map((s) => s.tier));

// cell -> the seats the sims registry binds to it, inverted here the same way
// the builder inverts it, so a package's seat list is checked against the
// bindings table rather than against the builder's own working copy of it.
const seatsOnCell = new Map();
for (const list of Object.values(simsReg.hall_bindings)) {
  for (const b of list) {
    if (!seatsOnCell.has(b.skill_id)) seatsOnCell.set(b.skill_id, new Set());
    seatsOnCell.get(b.skill_id).add(b.sim);
  }
}
// the seat bindings, counted with their pile-ups intact: four seats on one
// cell is four bindings and one covered cell
const bindingsOnCell = new Map();
for (const list of Object.values(simsReg.hall_bindings)) {
  for (const b of list) {
    if (!bindingsOnCell.has(b.skill_id)) bindingsOnCell.set(b.skill_id, []);
    bindingsOnCell.get(b.skill_id).push(b.sim);
  }
}

// §23.1, in a test as much as in a builder: nothing below substitutes a
// value for a missing one. A cell with no seat on it has an empty seat list
// because the lookup says so, not because a `??` decided what absence meant.
const seatsOn = (c) => (seatsOnCell.has(c) ? [...seatsOnCell.get(c)].sort() : []);
const bindingsOn = (c) => (bindingsOnCell.has(c) ? bindingsOnCell.get(c) : []);

/** The trades a package's own filter resolves to, recomputed. */
const tradesOf = (p) => {
  const f = p.filter.trades;
  if (f.kind === 'halls') return [...new Set(f.ids)].sort();
  return [...new Set(f.ids.flatMap((d) => inDistrict[d]))].sort();
};
/** The ladder cells a package's own filter resolves to, recomputed. */
const cellsOf = (p) => {
  const t = new Set(tradesOf(p));
  const st = new Set(p.filter.strands), ti = new Set(p.filter.tiers);
  return skillRows.filter((s) => t.has(s.union) && st.has(s.strand) && ti.has(s.tier))
    .map((s) => s.skill_id).sort();
};
/** The seats those cells carry, before the package's seat filter. */
const availableOf = (p) => [...new Set(cellsOf(p).flatMap(seatsOn))].sort();

ok('between six and twelve packages ship, each with a hyphenated id, a buyer, a pitch and a limits sentence',
  ids.length >= 6 && ids.length <= 12
  && ids.every((i) => /^[a-z][a-z0-9-]+$/.test(i))
  && new Set(ids).size === ids.length
  && Object.values(P).every((p) => p.name.length > 3 && p.who.length > 60
    && p.why.length > 80 && p.limits.length > 80));
ok('the pack carries one bundle version, the manifest\'s, and names every registry it resolved against',
  reg.pack_version === manifest.pack_version
  && Array.isArray(reg.reads) && reg.reads.length >= 6
  && reg.reads.includes('pack/registry/skills.json')
  && reg.reads.includes('sims/registry/sims.json')
  && reg.reads.includes('lessons/registry/lessons.json'));
ok('every filter names a closed vocabulary: real halls or real districts, real strands, real tiers, real seats',
  Object.values(P).every((p) => {
    const f = p.filter;
    const tradesOK = f.trades.kind === 'halls'
      ? f.trades.ids.every((h) => h in districtOf)
      : f.trades.kind === 'districts' && f.trades.ids.every((d) => d in inDistrict);
    const seatsOK = f.seats.kind === 'named'
      ? f.seats.ids.length > 0 && f.seats.ids.every((s) => s in simsReg.sims)
      : f.seats.kind === 'whatever-the-cells-carry' && f.seats.ids.length === 0;
    return tradesOK && f.trades.ids.length > 0 && seatsOK
      && f.strands.length > 0 && f.strands.every((s) => STRANDS.has(s))
      && f.tiers.length > 0 && f.tiers.every((t) => TIERS.has(t));
  }));
/* THE CONTENTS ARE THE FILTER, APPLIED AGAIN. This is the check the whole
   pack stands on: a package that named its contents could name anything, so
   the registry's contents are compared against the filter resolved a second
   time here, out of the same registries the builder read. */
ok('every package\'s trades and ladder cells are exactly its own filter resolved again against the union roster and the skill graph',
  Object.values(P).every((p) => J(p.contents.trades) === J(tradesOf(p))
    && J(p.contents.ladder_cells) === J(cellsOf(p))
    && p.size.trades === p.contents.trades.length
    && p.size.ladder_cells === p.contents.ladder_cells.length
    && J(p.contents.districts) === J([...new Set(p.contents.trades.map((h) => districtOf[h]))].sort())));
ok('no package resolves the whole ladder - that is the product, not a package of it',
  Object.values(P).every((p) => p.size.ladder_cells < skillRows.length)
  && Object.values(P).some((p) => p.size.ladder_cells > 20));
ok('every package\'s seats are exactly what the sims bindings put on its own cells, after its own seat filter',
  Object.values(P).every((p) => {
    const avail = availableOf(p);
    const want = p.filter.seats.kind === 'named'
      ? [...new Set(p.filter.seats.ids)].sort() : avail;
    return J(p.contents.seats) === J(want)
      && want.every((s) => avail.includes(s))
      && p.size.seats === want.length
      && J(p.contents.seat_names) === J(want.map((s) => simsReg.sims[s].name));
  }));
ok('the seats a package\'s own cells carry but it does not sell are named rather than dropped',
  Object.values(P).every((p) => J(p.coverage.seats_on_these_cells_not_sold)
    === J(availableOf(p).filter((s) => !p.contents.seats.includes(s))))
  && Object.values(P).some((p) => p.coverage.seats_on_these_cells_not_sold.length > 0));
ok('the lessons in a package are the lessons registry counted again over its cells, steps and all',
  Object.values(P).every((p) => {
    const cells = new Set(p.contents.ladder_cells);
    const want = Object.keys(lessons).filter((l) => cells.has(lessons[l].skill_id)).sort();
    return J(p.contents.lessons) === J(want)
      && p.size.lessons === want.length
      && p.size.lesson_steps === want.reduce((a, l) => a + lessons[l].steps.length, 0);
  }));
ok('the scenario count is the sims registry counted again - the yards each sold seat actually declares',
  Object.values(P).every((p) => p.size.seat_scenarios
    === p.contents.seats.reduce((a, s) => a + simsReg.sims[s].scenarios.length, 0)));

/* ------------------------------------------ what a package does NOT reach --- */
/* The seat-coverage figures, recomputed per package from the bindings table:
   covered cells, the pile-ups that would otherwise flatter them, and the
   bindings behind both. A package that sold four seats landing on one cell
   and called it four covered cells would be selling one rung four times. */
ok('every package\'s seat coverage recomputes: covered cells, pile-ups, and the bindings behind them',
  Object.values(P).every((p) => {
    const sold = p.contents.ladder_cells
      .map((c) => [c, bindingsOn(c).filter((s) => p.contents.seats.includes(s))])
      .filter(([, v]) => v.length);
    const piled = sold.filter(([, v]) => v.length > 1);
    return p.coverage.cells_with_a_seat === sold.length
      && p.coverage.cells_carrying_more_than_one_seat === piled.length
      && p.coverage.seats_absorbed_by_those_cells === piled.reduce((a, [, v]) => a + v.length, 0)
      && p.coverage.seat_bindings === sold.reduce((a, [, v]) => a + v.length, 0)
      && p.coverage.cells_with_a_seat <= p.size.ladder_cells;
  }));
/* The unreachable list is the sims registry's own, narrowed to the package —
   and the sims registry's own list is re-derived here from the skill graph
   before it is trusted. Both halves have to hold: a package cannot quietly
   drop a cell from its share of it, and sims/ cannot quietly shorten the list
   everybody reads. */
const closure = (cell) => {
  const seen = new Set(); const stack = [cell];
  while (stack.length) {
    const row = byId.get(stack.pop());
    if (!row) return null;
    for (const r of row.requires) if (!seen.has(r)) { seen.add(r); stack.push(r); }
  }
  return seen;
};
ok('the sims registry\'s unreachable-cell list is re-derived here from the skill graph and agrees, and every package carries exactly its own share of it',
  (() => {
    const cells = [...seatsOnCell.keys()];
    const derived = cells.filter((c) => {
      const pre = closure(c);
      return pre !== null && pre.size > 0 && ![...pre].some((p) => seatsOnCell.has(p));
    }).sort();
    if (J(derived) !== J([...simsReg.coverage.unreachable_seat_cells].sort())) return false;
    const un = new Set(derived);
    return Object.values(P).every((p) => {
      const sold = p.contents.ladder_cells.filter((c) =>
        seatsOn(c).some((s) => p.contents.seats.includes(s)));
      return J(p.coverage.unreachable_seat_cells) === J(sold.filter((c) => un.has(c)).sort())
        && J(p.coverage.reachable_seat_cells) === J(sold.filter((c) => !un.has(c)).sort())
        && p.coverage.unreachable_seat_cells.length
           + p.coverage.reachable_seat_cells.length === p.coverage.cells_with_a_seat;
    });
  })());
ok('the coverage block points at the pack that owns the figure instead of restating it, and says what covered and reachable mean',
  reg.coverage_contract.source === 'sims/registry/sims.json#coverage'
  && reg.coverage_contract.means.length > 120
  && reg.coverage_contract.honest.length > 120
  && /uncovered|no seat/.test(reg.coverage_contract.honest));

/* ------------------------------------------------- the hour nobody has ----- */
/* `contact_hours: null` is a claim about the whole bundle: that no registry
   declares a length of time, so no hour count could be derived and none was
   invented. The claim is re-scanned here with the BUILDER'S OWN pattern,
   read out of build.py rather than retyped, over the registries the registry
   says were scanned. Declare a duration anywhere in them and this fails —
   which is the point: the null would have gone stale. */
const durPattern = /DURATION_KEY = re\.compile\(\s*r'([^']+)'/.exec(builder)[1];
const DUR = new RegExp(durPattern, 'i');
const durKeys = (doc, where) => {
  const out = [];
  if (doc && typeof doc === 'object' && !Array.isArray(doc)) {
    for (const [k, v] of Object.entries(doc)) {
      if (DUR.test(k)) out.push(`${where}.${k}`);
      out.push(...durKeys(v, `${where}.${k}`));
    }
  } else if (Array.isArray(doc)) {
    doc.forEach((v, i) => out.push(...durKeys(v, `${where}[${i}]`)));
  }
  return out;
};
ok('no package invents an hour: the duration is declared undeclared, with a reason, and a fresh scan of the registries it names finds no field that declares one',
  reg.duration.declared === false && reg.duration.contact_hours === null
  && reg.duration.why.length > 120 && reg.duration.checked.length > 120
  && reg.duration.registries_scanned.length >= 5
  && Object.values(P).every((p) => p.size.contact_hours === null)
  && reg.duration.registries_scanned.every((rel) =>
    durKeys(JSON.parse(readFileSync(new URL('../' + rel, import.meta.url))), rel).length === 0)
  && DUR.test('contact_hours') && DUR.test('minutes'));

/* ------------------------------------------------ what nobody has signed --- */
const signoff = await import('../pack/hall_signoff.mjs');
ok('the practitioner sign-off count is read through the module that owns the rule, and it is nobody, in every package',
  halls.filter((h) => signoff.claimsHallSignoff(h.content_status)).length === 0
  && Object.values(P).every((p) =>
    p.signoff.practitioner_signed_off_halls === 0
    && p.signoff.of_halls_in_this_package === p.contents.trades.length));
/* A seller reaching for standing this bundle does not have would reach for
   it in the NAME or the PITCH. `limits` is the one field allowed to say any
   of these words, and only in order to refuse them. The vocabulary is read
   out of the builder rather than retyped here. */
const claimPattern = /CLAIM_WORDS = re\.compile\(\s*r'([^']+)'/.exec(builder)[1];
const CLAIM = new RegExp(claimPattern, 'i');
ok('no package is sold on a claim word - the name, the buyer and the pitch stay clear of them, and the registry refuses certification outright',
  Object.values(P).every((p) => !CLAIM.test(p.name) && !CLAIM.test(p.who) && !CLAIM.test(p.why))
  && Object.values(P).some((p) => CLAIM.test(p.limits))
  && /no package here certifies/.test(reg.honesty.not_certification)
  && /exactly the standing it started with/.test(reg.honesty.not_certification)
  && CLAIM.test('certifies') && CLAIM.test('licence'));
ok('a package with no seat in it says so in its own limits, and the pack counts them rather than leaving them to be discovered',
  Object.values(P).every((p) => p.size.seats > 0 || /no simulator seat/.test(p.limits))
  && reg.counts.packages_with_no_seat
     === Object.values(P).filter((p) => p.size.seats === 0).length);
ok('the pack declares no price, no term and no headcount, and says why',
  /nothing here is a quote/.test(reg.honesty.not_a_price)
  && /declares no price/.test(reg.honesty.not_a_price)
  && !('price' in reg) && !('pricing' in reg)
  && Object.values(P).every((p) => !('price' in p) && !('price' in p.size)));

ok('the totals are the packages counted again, not a summary typed beside them',
  reg.counts.packages === ids.length
  && reg.counts.trades_offered === new Set(Object.values(P).flatMap((p) => p.contents.trades)).size
  && reg.counts.seats_offered === new Set(Object.values(P).flatMap((p) => p.contents.seats)).size
  && reg.counts.cells_offered === new Set(Object.values(P).flatMap((p) => p.contents.ladder_cells)).size
  && reg.counts.lessons_offered === new Set(Object.values(P).flatMap((p) => p.contents.lessons)).size);
ok('the provenance words come from the recorded set, and AI-SYNTHESIZED appears in neither the registry nor the builder',
  ['AUTHORED', 'DERIVED', 'RECORDED', 'SCHEMATIC', 'SCRIPTED']
    .includes(reg.provenance.filters)
  && reg.provenance.filters === 'AUTHORED' && reg.provenance.contents === 'DERIVED'
  && !/AI-SYNTHESIZED/.test(JSON.stringify(reg))
  && /orbis\//.test(reg.provenance.note)
  && !/AI-SYNTHESIZED/.test(builder));
ok('the pack says plainly that nothing draws it yet, in its own words, rather than leaving it to be found',
  reg.honesty.not_built_yet.length > 80
  && /no page/.test(reg.honesty.not_built_yet));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`bundles/test: ${n} checks passed — ${ids.length} packages, `
  + `${reg.counts.seats_offered} seats and ${reg.counts.cells_offered} ladder cells offered, `
  + `${reg.counts.packages_with_no_seat} of the packages with no seat in them`);
