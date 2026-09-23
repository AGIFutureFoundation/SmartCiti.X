/**
 * The training ladder page, held to the registries it claims to read.
 *
 * `web/build_ladder.py` writes `web/trade_craft_ladder.html`: one hall's skill
 * graph at a time, with the simulator seats marked on the cells they stand on
 * and the cells that carry no seat marked just as plainly. The page states
 * counts, draws edges and claims coverage, and every one of those is a claim
 * about a registry. This suite recomputes each claim from the registry that
 * owns it and holds the SHIPPED PAGE to the answer.
 *
 * WHICH FILE EACH CHECK READS is in its message, always, because this bundle
 * has been bitten eight times by a check that matched a GENERATOR's comment
 * quoting the string it was hunting for in the PAGE:
 *
 *   [registry]  the registries only - no page involved
 *   [shipped]   the built HTML, and the data embedded in it
 *   [generator] web/build_ladder.py's own source, comments stripped
 *   [browser]   the rendered DOM in headless Chromium (--browser only)
 *
 * MATCH STRUCTURE, NEVER A SENTENCE. Every check below reads an element, an
 * id, or a data attribute: `data-fig`, `data-const`, `data-band`,
 * `data-quote`, `data-tier`, `data-skill`, `data-edge`, `data-covered`. A
 * check that searched the prose would match the page's own honest
 * explanations - one in this bundle flagged the word AI-SYNTHESIZED inside a
 * sentence explaining that the word belongs to another pack, and flagged the
 * trade acronym HVAC as a provenance tier. So the provenance check here reads
 * `data-tier` attributes and nothing else, and the figure checks read `<b>`
 * inside a keyed `.fig` and nothing else.
 *
 * NO BROWSER BY DEFAULT. verify_all.sh reaches no network and opens no
 * browser, so the default run is static. `--browser` adds the DOM checks
 * against a served copy; it needs a server on the page's origin and
 * playwright, and it says so if it cannot reach one.
 *
 *   node web/test_ladder.mjs
 *   node web/test_ladder.mjs --browser [--origin=http://127.0.0.1:8811]
 *   node web/test_ladder.mjs --page=/tmp/broken.html --root=/tmp/broken-root
 *
 * `--page` and `--root` exist for the mutation tests: point the suite at a
 * broken copy of the page, or at a broken copy of the registries, and watch
 * the check that covers that fault fail by name. A check nobody has watched
 * fail is not a check.
 */
import { readFileSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit === undefined ? null : hit.slice(name.length + 3);
};
const ROOT = resolve(arg('root') !== null ? arg('root') : join(HERE, '..'));
const PAGE = resolve(arg('page') !== null ? arg('page') : join(HERE, 'trade_craft_ladder.html'));
const GENERATOR = join(HERE, 'build_ladder.py');
const ORIGIN = arg('origin') !== null ? arg('origin') : 'http://127.0.0.1:8811';
const PAGE_URL = arg('url') !== null ? arg('url')
  : `${ORIGIN}/web/${PAGE.split('/').pop()}`;
const WANT_BROWSER = args.includes('--browser');

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.log('FAIL  ' + m);
  for (const e of evidence) console.log('      ' + e);
};

const readJSON = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));

/* ------------------------------------------------------------ registries -- */
const SKILLS_PATH = 'pack/registry/skills.json';
const SIMS_PATH = 'sims/registry/sims.json';
const VARIANTS_PATH = 'pack/registry/variants.json';
const HALLS_PATH = 'pack/registry/halls.json';
const GATES_PATH = 'control/gates.mjs';

const skillsReg = readJSON(SKILLS_PATH);
const simsReg = readJSON(SIMS_PATH);
const variants = readJSON(VARIANTS_PATH);
const hallsReg = readJSON(HALLS_PATH);
const SKILLS = skillsReg.skills;
const SIMS = simsReg.sims;
const BINDINGS = simsReg.hall_bindings;
const gatesSrc = readFileSync(join(ROOT, GATES_PATH), 'utf8');
const { GATE } = await import(pathToFileURL(join(ROOT, GATES_PATH)).href);
const { TRANSFER, INTERFERENCE } = await import(pathToFileURL(join(ROOT, 'control/graph.mjs')).href);
const { claimsHallSignoff } = await import(pathToFileURL(join(ROOT, 'pack/hall_signoff.mjs')).href);

/* Everything the page claims, recomputed here from the registries - a second,
   independent count, written without looking at the generator's arithmetic. */
const byId = new Map(SKILLS.map((s) => [s.skill_id, s]));
const byUnion = new Map();
for (const s of SKILLS) {
  if (!byUnion.has(s.union)) byUnion.set(s.union, []);
  byUnion.get(s.union).push(s);
}
const STRANDS = [...new Set(SKILLS.map((s) => s.strand))];
const TIERS = [...new Set(SKILLS.map((s) => s.tier))];
const seatsOfHall = (hall) => (hall in BINDINGS ? BINDINGS[hall] : []);
const coveredCells = new Set();
for (const hall of Object.keys(BINDINGS)) for (const b of BINDINGS[hall]) coveredCells.add(b.skill_id);
const R = {
  halls: hallsReg.halls.length,
  cells: SKILLS.length,
  'requires-edges': SKILLS.reduce((a, s) => a + s.requires.length, 0),
  sims: Object.keys(SIMS).length,
  bindings: Object.values(BINDINGS).reduce((a, v) => a + v.length, 0),
  'covered-cells': coveredCells.size,
  'uncovered-cells': SKILLS.length - coveredCells.size,
  'unbound-halls': hallsReg.halls.length - Object.keys(BINDINGS).length,
  'signed-off-halls': hallsReg.halls.filter((h) => claimsHallSignoff(h.content_status)).length,
};

/* ------------------------------------------------------- the shipped page -- */
const html = readFileSync(PAGE, 'utf8');

/** The page's inline scripts, in order, as the tokenizer would cut them. */
function scriptsOf(text) {
  const out = [];
  const re = /<script\b[^>]*>/gi;
  let m;
  while ((m = re.exec(text)) !== null) {
    const close = text.indexOf('</script', m.index + m[0].length);
    out.push(text.slice(m.index + m[0].length, close < 0 ? text.length : close));
    re.lastIndex = close < 0 ? text.length : close;
  }
  return out;
}
const SCRIPTS = scriptsOf(html);
/* The renderer with its comments cut out. The comments in it quote the very
   expressions the checks below hunt for - `[data-covered="yes"]` is explained
   in a comment two lines above the line that uses it - and a check that
   matches the explanation instead of the code is answering a different
   question than the one it was written to ask. */
const RENDERER = (SCRIPTS.length > 1 ? SCRIPTS[1] : '')
  .replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');

/** The embedded registry payload, read out of the page's first script. */
function payloadOf() {
  const s = SCRIPTS.length ? SCRIPTS[0] : '';
  const i = s.indexOf('const DATA = ');
  if (i < 0) return null;
  const j = s.lastIndexOf(';');
  if (j < i) return null;
  try { return JSON.parse(s.slice(i + 'const DATA = '.length, j)); } catch { return null; }
}
const D = payloadOf();

/** The keyed network figures: {data-fig: the number printed inside it}. */
function figs() {
  const out = new Map();
  const re = /<div class="fig" data-fig="([^"]+)"><b>([^<]*)<\/b>/g;
  let m;
  while ((m = re.exec(html)) !== null) out.set(m[1], Number(m[2].replace(/,/g, '')));
  return out;
}
/** The per-hall coverage slots, by id, with whatever static content they hold. */
function covSlots() {
  const out = new Map();
  const re = /<b id="(cov-[a-z]+)">([\s\S]*?)<\/b>/g;
  let m;
  while ((m = re.exec(html)) !== null) out.set(m[1], m[2]);
  return out;
}
const attrRows = (attr) => {
  const out = new Map();
  const re = new RegExp(`<tr ${attr}="([^"]+)">([\\s\\S]*?)<\\/tr>`, 'g');
  let m;
  while ((m = re.exec(html)) !== null) {
    out.set(m[1], [...m[2].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((c) => c[1]));
  }
  return out;
};
const quotes = () => {
  const out = new Map();
  const re = /<pre data-quote="([^"]+)"[^>]*>([\s\S]*?)<\/pre>/g;
  let m;
  while ((m = re.exec(html)) !== null) out.set(m[1], m[2]);
  return out;
};
const unescape = (s) => s.replace(/&amp;/g, '&').replace(/&lt;/g, '<')
  .replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'");

console.log(`ladder: page ${PAGE} (${html.length.toLocaleString('en-US')} bytes), `
  + `registries under ${ROOT}`);

/* ================================================== 1. the registries alone */
ok('[registry] skills.json: the count field equals the records, and every skill_id is unique',
  skillsReg.count === SKILLS.length && byId.size === SKILLS.length,
  [`count=${skillsReg.count} records=${SKILLS.length} distinct=${byId.size}`]);

ok(`[registry] the ladder is ${R.halls} halls x ${STRANDS.length} strands x ${TIERS.length} tiers `
  + `= ${R.cells} cells, one skill in each`,
  byUnion.size === R.halls
  && [...byUnion.values()].every((rows) => rows.length === STRANDS.length * TIERS.length)
  && new Set(SKILLS.map((s) => `${s.union}.${s.strand}.${s.tier}`)).size === SKILLS.length,
  [`halls=${byUnion.size} cells=${SKILLS.length}`]);

{
  const off = [];
  for (const s of SKILLS) {
    for (const kind of ['requires', 'supports', 'interferes']) {
      for (const e of s[kind]) {
        if (!byId.has(e)) off.push(`${s.skill_id}.${kind} -> ${e} (in no skill record)`);
        else if (byId.get(e).union !== s.union) off.push(`${s.skill_id}.${kind} -> ${e} (other hall)`);
      }
    }
  }
  ok('[registry] every requires / supports / interferes edge resolves, and stays inside its own hall',
    off.length === 0, off.slice(0, 4));
}

{
  const bad2 = [];
  for (const [hall, binds] of Object.entries(BINDINGS)) {
    for (const b of binds) {
      const s = byId.get(b.skill_id);
      if (!s) { bad2.push(`${hall}: ${b.skill_id} resolves nowhere`); continue; }
      if (s.union !== hall) bad2.push(`${hall}: ${b.skill_id} belongs to ${s.union}`);
      const sim = SIMS[b.sim];
      if (!sim) { bad2.push(`${hall}: seat ${b.sim} is in no sim record`); continue; }
      if (sim.skill_strand !== s.strand || sim.skill_tier !== s.tier) {
        bad2.push(`${hall}: ${b.skill_id} vs seat ${b.sim} ${sim.skill_strand}/${sim.skill_tier}`);
      }
    }
  }
  ok(`[registry] all ${R.bindings} hall_bindings resolve: 0 dangling skill_ids, every binding inside `
    + 'its own hall, every cell the one its seat says it proves', bad2.length === 0, bad2.slice(0, 4));
}

{
  /* only cells that resolve: a dangling binding is check 4's fault to report,
     and a crash here would take the rest of the suite down with it */
  const positions = new Set([...coveredCells].filter((c) => byId.has(c))
    .map((c) => `${byId.get(c).strand}.${byId.get(c).tier}`));
  ok(`[registry] every seat in the pack stands on ${positions.size} of the `
    + `${STRANDS.length * TIERS.length} strand x tier positions, so `
    + `${STRANDS.length - new Set([...positions].map((p) => p.split('.')[0])).size} of the `
    + `${STRANDS.length} strands carry no simulator anywhere`,
    positions.size >= 1 && Object.values(SIMS).every((s) => 'skill_strand' in s && 'skill_tier' in s),
    [...positions]);
}

/* ============================================ 2. the page against those facts */
ok('[shipped] the page carries an embedded registry payload that parses, with one record per hall',
  D !== null && Array.isArray(D.unions) && D.unions.length === byUnion.size,
  [D === null ? 'the payload did not parse' : `payload halls=${D.unions.length}`]);

if (D !== null) {
  /* (a) every skill_id the page renders resolves in skills.json */
  const rendered = D.unions.flatMap((u) => u.cells.map((c) => c[0]));
  const unresolved = rendered.filter((id) => !byId.has(id));
  ok(`[shipped] every one of the ${rendered.length.toLocaleString('en-US')} skill_ids the page can `
    + `render resolves in ${SKILLS_PATH}`,
    rendered.length === SKILLS.length && unresolved.length === 0,
    unresolved.slice(0, 4).map((x) => `${x} is in no skill record`));

  /* (c) no edge to a skill the hall does not have */
  const stray = [];
  for (const u of D.unions) {
    const mine = new Set(u.cells.map((c) => c[0]));
    for (const c of u.cells) {
      for (const [i, kind] of [[4, 'requires'], [5, 'supports'], [6, 'interferes']]) {
        for (const e of c[i]) if (!mine.has(e)) stray.push(`${u.slug}: ${c[0]} ${kind} ${e}`);
      }
    }
  }
  ok('[shipped] no edge in the payload points at a skill its own hall does not have',
    stray.length === 0, stray.slice(0, 4));

  /* the edges are the registry's edges, not a subset and not a superset */
  const pageEdges = new Set();
  for (const u of D.unions) for (const c of u.cells) for (const e of c[4]) pageEdges.add(`${c[0]}|${e}`);
  const regEdges = new Set();
  for (const s of SKILLS) for (const e of s.requires) regEdges.add(`${s.skill_id}|${e}`);
  ok(`[shipped] the payload carries exactly the ${regEdges.size.toLocaleString('en-US')} prerequisite `
    + 'edges the registry declares - none added, none dropped',
    pageEdges.size === regEdges.size && [...regEdges].every((e) => pageEdges.has(e)),
    [`page=${pageEdges.size} registry=${regEdges.size}`]);

  /* the seats are hall_bindings, exactly */
  const mismatch = [];
  for (const u of D.unions) {
    const want = seatsOfHall(u.slug).map((b) => `${b.sim}|${b.skill_id}`).sort().join(',');
    const got = u.seats.map((s) => `${s[0]}|${s[1]}`).sort().join(',');
    if (want !== got) mismatch.push(`${u.slug}: page [${got}] vs registry [${want}]`);
  }
  ok(`[shipped] every hall's seat list is its own hall_bindings entry, exactly `
    + `(${R.bindings} bindings across ${Object.keys(BINDINGS).length} halls)`,
    mismatch.length === 0, mismatch.slice(0, 4));

  /* (b) the covered-cell count, recomputed */
  const pageCovered = new Set(D.unions.flatMap((u) => u.seats.map((s) => s[1])));
  ok(`[shipped] the payload's covered cells recount to ${R['covered-cells']}, the same cells `
    + `${SIMS_PATH} hall_bindings names`,
    pageCovered.size === coveredCells.size && [...coveredCells].every((c) => pageCovered.has(c)),
    [`page=${pageCovered.size} registry=${coveredCells.size}`]);

  /* the rubric axes, verbatim */
  const rub = [];
  for (const [slug, rec] of Object.entries(D.sims)) {
    const src = SIMS[slug];
    if (!src) { rub.push(`${slug} is in no sim record`); continue; }
    if (rec.rubric.length !== src.rubric.length) { rub.push(`${slug}: axis count`); continue; }
    src.rubric.forEach((a, i) => {
      const p = rec.rubric[i];
      if (p.axis !== a.axis || p.measure !== a.measure || p.pass !== a.pass) {
        rub.push(`${slug}.${a.axis}: page ${JSON.stringify(p)} vs registry ${JSON.stringify(a)}`);
      }
      if (a.pass === 'informational' && 'fails_when' in p) rub.push(`${slug}.${a.axis}: informational axis carries fails_when`);
      if (a.pass !== 'informational' && p.fails_when !== a.fails_when) rub.push(`${slug}.${a.axis}: fails_when`);
    });
  }
  const axes = Object.values(SIMS).reduce((a, s) => a + s.rubric.length, 0);
  ok(`[shipped] all ${axes} rubric axes across the ${R.sims} seats carry the registry's own measure `
    + 'and pass bar, and only a pass-gated axis carries a fails_when',
    rub.length === 0 && Object.keys(D.sims).length === R.sims, rub.slice(0, 4));
}

/* ------------------------------------- the keyed figures, element by element */
{
  const f = figs();
  const wrong = [];
  for (const [k, v] of Object.entries(R)) {
    if (!f.has(k)) { wrong.push(`no <div class="fig" data-fig="${k}"> on the page`); continue; }
    if (f.get(k) !== v) wrong.push(`data-fig="${k}": page ${f.get(k)}, registry ${v}`);
  }
  ok(`[shipped] every one of the ${Object.keys(R).length} keyed network figures equals the number `
    + 'recomputed from the registry that owns it', wrong.length === 0, wrong.slice(0, 5));
}

/* (d) a coverage claim can never be larger than the data: the page types no
   per-hall coverage number at all - the slots ship EMPTY and the renderer
   fills each one from the cells it actually drew. */
{
  const slots = covSlots();
  const want = ['cov-cells', 'cov-covered', 'cov-uncovered', 'cov-seats', 'cov-edges', 'cov-strands'];
  const filled = want.filter((k) => !slots.has(k) || slots.get(k).trim() !== '');
  ok(`[shipped] all ${want.length} per-hall coverage slots ship EMPTY - the page types no coverage `
    + 'number, so it cannot type one larger than the data', filled.length === 0,
    filled.map((k) => `#${k} holds ${JSON.stringify(slots.has(k) ? slots.get(k) : null)}`));
}
ok('[shipped] the renderer fills the covered-cell slot by counting the cells it drew and marked '
  + 'covered, not from any number of its own',
  /getElementById\('cov-covered'\)\.textContent\s*=\s*String\(coveredEls\.length\)/.test(RENDERER)
  && /coveredEls\s*=\s*svg\.querySelectorAll\('\[data-covered="yes"\]'\)/.test(RENDERER),
  ['the renderer, with its comments stripped, does not derive #cov-covered from [data-covered="yes"]']);
ok('[shipped] the renderer refuses to draw a seat on a cell its hall does not have, and refuses an '
  + 'edge to a skill its hall does not have - both throw by name rather than drawing one fewer',
  /if \(!byId\.has\(sid\)\) \{[\s\S]{0,400}?throw new Error\(/.test(RENDERER)
  && /if \(!byId\.has\(other\)\) \{[\s\S]{0,300}?throw new Error\(/.test(RENDERER),
  ['the renderer has no fail-closed throw on an unknown seat cell or an unknown edge target']);

/* ------------------------------------------- the control-plane policy quoted */
{
  const rows = attrRows('data-const');
  const want = new Map([
    ['GATE.masteryThreshold', String(GATE.masteryThreshold)],
    ['GATE.consecutiveUnaided', String(GATE.consecutiveUnaided)],
    ['GATE.atOrAbove', String(GATE.atOrAbove)],
    ['GATE.levelTest.questions', String(GATE.levelTest.questions)],
    ['GATE.levelTest.passPct', String(GATE.levelTest.passPct)],
    ['GATE.levelTest.retakeLockHours', String(GATE.levelTest.retakeLockHours)],
    ['TRANSFER.maxHops', String(TRANSFER.maxHops)],
    ['TRANSFER.sigmaShare', String(TRANSFER.sigmaShare)],
    ['INTERFERENCE.discount', String(INTERFERENCE.discount)],
  ]);
  const wrong = [];
  for (const [k, v] of want) {
    if (!rows.has(k)) { wrong.push(`no <tr data-const="${k}"> on the page`); continue; }
    const shown = rows.get(k)[1];
    if (shown !== v) wrong.push(`${k}: page ${shown}, ${GATES_PATH} ${v}`);
  }
  ok(`[shipped] all ${want.size} control-plane constants on the page are the values `
    + `${GATES_PATH} and control/graph.mjs actually export`, wrong.length === 0, wrong.slice(0, 5));
}
{
  const q = quotes();
  const certLine = /return (skillGates\.every[\s\S]*?jobsiteFinal\?\.pass === true);/.exec(gatesSrc);
  const jobLine = /const pass = (stepOrder[\s\S]*?oral >= 2);/.exec(gatesSrc);
  const norm = (s) => s.replace(/\s+/g, ' ').trim();
  ok(`[shipped] the certification expression the page shows is ${GATES_PATH}'s own, verbatim`,
    certLine !== null && q.has('certified')
    && norm(unescape(q.get('certified'))).endsWith(norm(certLine[1]) + ';'),
    [`page: ${q.has('certified') ? norm(unescape(q.get('certified'))) : '(absent)'}`,
      `source: ${certLine ? norm(certLine[1]) : '(not found in gates.mjs)'}`]);
  ok(`[shipped] the jobsite-final pass expression the page shows is ${GATES_PATH}'s own, verbatim`,
    jobLine !== null && q.has('jobsite-final')
    && norm(unescape(q.get('jobsite-final'))).includes(norm(jobLine[1])),
    [`page: ${q.has('jobsite-final') ? norm(unescape(q.get('jobsite-final'))) : '(absent)'}`,
      `source: ${jobLine ? norm(jobLine[1]) : '(not found in gates.mjs)'}`]);
}

/* ------------------------------------------------------ the declared variants */
{
  const rows = attrRows('data-band');
  const wrong = [];
  for (const b of variants.bands) {
    if (!rows.has(b)) { wrong.push(`no <tr data-band="${b}"> on the page`); continue; }
    const [, offset, ceiling] = rows.get(b);
    if (Number(offset) !== variants.band_offset[b]) wrong.push(`${b}: offset ${offset} vs ${variants.band_offset[b]}`);
    if (Number(ceiling) !== variants.band_scaffold_ceiling[b]) wrong.push(`${b}: ceiling ${ceiling} vs ${variants.band_scaffold_ceiling[b]}`);
  }
  ok(`[shipped] the ${variants.bands.length} band rows carry ${VARIANTS_PATH}'s own band_offset and `
    + 'band_scaffold_ceiling', wrong.length === 0 && rows.size === variants.bands.length,
    wrong.slice(0, 4));
}
ok(`[shipped] the page's modality and band lists are ${VARIANTS_PATH}'s, and `
  + `${variants.modalities.length} x ${variants.bands.length} is the declared `
  + `${variants.variants_per_lesson} variants per lesson`,
  D !== null && JSON.stringify(D.variants.modalities) === JSON.stringify(variants.modalities)
  && JSON.stringify(D.variants.bands) === JSON.stringify(variants.bands)
  && D.variants.per_lesson === variants.variants_per_lesson
  && variants.modalities.length * variants.bands.length === variants.variants_per_lesson,
  [D === null ? 'no payload' : JSON.stringify(D.variants)]);
/* The pack declares a `vr_sim` modality and the page says the seats are not
   it. That sentence is only true while no seat record names a module, so the
   registry is checked rather than the sentence. */
ok(`[registry] no seat record in ${SIMS_PATH} names a generated variant module, which is what lets `
  + 'the page say a vr_sim variant id and a built seat are two separate things',
  !/module_id|lesson_id|vr_sim/.test(readFileSync(join(ROOT, SIMS_PATH), 'utf8')),
  [`${SIMS_PATH} now mentions a module or variant id`]);

/* --------------------------------------------------------------- provenance */
{
  const tiers = [...html.matchAll(/data-tier="([^"]*)"/g)].map((m) => m[1]);
  const allowed = new Set(['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED']);
  const outside = tiers.filter((t) => !allowed.has(t));
  ok(`[shipped] every provenance tier on the page is one of the ${allowed.size} this bundle uses, `
    + 'declared only as a data-tier attribute - never asserted in a sentence',
    tiers.length > 0 && outside.length === 0,
    outside.length ? outside.map((t) => `data-tier="${t}" is not a tier of this bundle`)
      : ['the page declares no data-tier at all']);
  ok('[shipped] no provenance tier on the page is AI-SYNTHESIZED - that word belongs to orbis/ and '
    + 'names generated video, and this check reads the tier attributes, not the prose that explains it',
    !tiers.includes('AI-SYNTHESIZED'), ['a data-tier claims AI-SYNTHESIZED']);
}

/* ---------------------------------------------------------- the honest limit */
ok('[shipped] the page states the certification limit where a reader meets it - in the lead '
  + `section, above the ladder, not in a footer (halls with a sign-off: ${R['signed-off-halls']})`,
  (() => {
    const lead = html.indexOf('<section class="lead" id="limits">');
    const ladder = html.indexOf('<svg id="grid"');
    const cert = html.indexOf('It certifies nobody', lead);
    return lead >= 0 && cert > lead && ladder > cert;
  })(),
  ['the limit is not inside #limits ahead of the ladder']);

/* --------------------------------------------------------------- generator -- */
{
  const src = readFileSync(GENERATOR, 'utf8');
  /* comments and docstrings stripped: this file's own prose explains what it
     refuses to do, in the words the check hunts for */
  const code = src.replace(/"""[\s\S]*?"""/g, ' ').replace(/^\s*#[^\n]*$/gm, ' ');
  ok('[generator] no default-valued lookup over registry data: no `.get(k, default)` and no bare '
    + '`??` - a missing field fails closed through need() instead',
    !/\.get\([^)]*,[^)]*\)/.test(code) && !/\?\?/.test(code), ['a defaulted lookup survives in the generator']);
  const named = [SKILLS_PATH, SIMS_PATH, VARIANTS_PATH, HALLS_PATH, GATES_PATH,
    'control/graph.mjs', 'pack/hall_signoff.mjs', 'pack/manifest.json'];
  const missing = named.filter((p) => !src.includes(p));
  ok(`[generator] the generator names all ${named.length} registry and control paths it reads, so a `
    + 'scan for readers of a registry finds it', missing.length === 0, missing);
}

/* ---------------------------------------------------------------- browser -- */
if (!WANT_BROWSER) {
  console.log('  --  [browser] the DOM checks were not run: pass --browser (and serve the bundle) '
    + 'to drive the page in headless Chromium');
} else {
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
  });
  const page = await browser.newPage();
  const pageErrors = [], consoleErrors = [];
  page.on('pageerror', (e) => pageErrors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });

  for (const hall of ['ironworkers', 'welders']) {
    await page.goto(`${PAGE_URL}?hall=${hall}`, { waitUntil: 'load' });
    const dom = await page.evaluate(() => ({
      cells: [...document.querySelectorAll('#grid [data-skill]')].map((e) => e.getAttribute('data-skill')),
      covered: [...document.querySelectorAll('#grid [data-covered="yes"]')].map((e) => e.getAttribute('data-skill')),
      requires: [...document.querySelectorAll('#grid [data-edge="requires"]')]
        .map((e) => e.getAttribute('data-from') + '|' + e.getAttribute('data-to')),
      supports: document.querySelectorAll('#grid [data-edge="supports"]').length,
      interferes: document.querySelectorAll('#grid [data-edge="interferes"]').length,
      covCells: document.getElementById('cov-cells').textContent,
      covCovered: document.getElementById('cov-covered').textContent,
      covUncovered: document.getElementById('cov-uncovered').textContent,
      covEdges: document.getElementById('cov-edges').textContent,
      covSeats: document.getElementById('cov-seats').textContent,
      gapN: document.getElementById('gap-n').textContent,
      gaps: [...document.querySelectorAll('[data-gap-strand]')].map((e) => e.getAttribute('data-gap-strand')),
      seats: [...document.querySelectorAll('[data-seat]')].map((e) => e.getAttribute('data-seat')),
      links: [...document.querySelectorAll('[data-open-seat]')].map((a) => a.getAttribute('href')),
    }));
    const mine = byUnion.get(hall);
    const wantCells = mine.map((s) => s.skill_id).sort();
    const wantEdges = mine.flatMap((s) => s.requires.map((e) => `${s.skill_id}|${e}`)).sort();
    const wantCovered = seatsOfHall(hall).map((b) => b.skill_id);
    const wantCoveredSet = [...new Set(wantCovered)].sort();
    const coveredStrands = new Set(wantCoveredSet.map((c) => byId.get(c).strand));

    ok(`[browser] ${hall}: the DOM renders ${wantCells.length} cells, and they are exactly this `
      + "hall's own cells in skills.json",
      JSON.stringify([...dom.cells].sort()) === JSON.stringify(wantCells),
      [`dom=${dom.cells.length} registry=${wantCells.length}`]);
    ok(`[browser] ${hall}: the DOM draws ${wantEdges.length} prerequisite edges and every one is an `
      + 'edge the registry declares between two cells of this hall',
      JSON.stringify([...dom.requires].sort()) === JSON.stringify(wantEdges)
      && dom.requires.every((e) => e.split('|').every((id) => wantCells.includes(id))),
      [`dom=${dom.requires.length} registry=${wantEdges.length}`]);
    ok(`[browser] ${hall}: the DOM marks ${wantCoveredSet.length} covered cell(s), the cells `
      + 'hall_bindings binds a seat to, and the coverage badge equals that count',
      JSON.stringify([...dom.covered].sort()) === JSON.stringify(wantCoveredSet)
      && dom.covCovered === String(wantCoveredSet.length)
      && dom.covCells === String(wantCells.length)
      && dom.covUncovered === String(wantCells.length - wantCoveredSet.length)
      && dom.covEdges === String(wantEdges.length)
      && dom.covSeats === String(seatsOfHall(hall).length),
      [`dom covered=[${dom.covered}] badge=${dom.covCovered} registry=[${wantCoveredSet}]`,
        `cells=${dom.covCells} uncovered=${dom.covUncovered} edges=${dom.covEdges} seats=${dom.covSeats}`]);
    ok(`[browser] ${hall}: the gap list names the ${STRANDS.length - coveredStrands.size} strands with `
      + 'no seat, counted off the same cells the ladder drew',
      JSON.stringify(dom.gaps.sort())
        === JSON.stringify(STRANDS.filter((s) => !coveredStrands.has(s)).sort())
      && dom.gapN === `${STRANDS.length - coveredStrands.size} of ${STRANDS.length}`,
      [`dom=[${dom.gaps}] badge=${dom.gapN}`]);
    ok(`[browser] ${hall}: every seat card is a hall_bindings seat, and each one links to its own `
      + 'seat in the 3D environment',
      JSON.stringify(dom.seats) === JSON.stringify(seatsOfHall(hall).map((b) => b.sim))
      && dom.links.every((h, i) => h === `trade_craft_3d.html?hall=${hall}&sim=${dom.seats[i]}`),
      [`seats=[${dom.seats}]`, `links=[${dom.links}]`]);
    ok(`[browser] ${hall}: the DOM draws the registry's `
      + `${mine.reduce((a, s) => a + s.supports.length, 0)} support and `
      + `${mine.reduce((a, s) => a + s.interferes.length, 0)} interference edges too`,
      dom.supports === mine.reduce((a, s) => a + s.supports.length, 0)
      && dom.interferes === mine.reduce((a, s) => a + s.interferes.length, 0),
      [`dom supports=${dom.supports} interferes=${dom.interferes}`]);
  }

  /* follow one covered cell through to the seat it links to */
  {
    const hall = 'welders';
    const seat = seatsOfHall(hall)[0];
    await page.goto(`${PAGE_URL}?hall=${hall}`, { waitUntil: 'load' });
    const href = await page.getAttribute(`[data-open-seat="${seat.sim}"]`, 'href');
    const target = new URL(href, `${PAGE_URL}?hall=${hall}`).href;
    const resp = await page.goto(target, { waitUntil: 'load' });
    /* The 3D page rewrites its own URL once the world stands up (syncURL()
       replaces the query with ?hall=&lang=), so the query string is NOT the
       evidence that the seat opened - the page's own state hook is. Waiting
       for it rather than reading it once is deliberate: the deep link opens
       the seat in a microtask after the scene is built. */
    let opened = null;
    try {
      await page.waitForFunction(
        (want) => window.__tc3d && window.__tc3d().sim === want, seat.sim, { timeout: 30000 });
      opened = await page.evaluate(() => window.__tc3d().sim);
    } catch { opened = await page.evaluate(() => (window.__tc3d ? window.__tc3d().sim : 'no hook')); }
    ok(`[browser] the ${hall} covered cell links straight into seat ${seat.sim}: the 3D environment `
      + `answers ${resp.status()} and stands that seat up`,
      resp.ok() && opened === seat.sim, [target, `status=${resp.status()} seat open=${opened}`]);
  }

  ok('[browser] the page raised no uncaught error and logged no console error while two halls were '
    + 'driven and one seat followed',
    pageErrors.length === 0 && consoleErrors.length === 0,
    [...pageErrors.slice(0, 3), ...consoleErrors.slice(0, 3)]);
  await browser.close();
}

console.log(`\nladder: ${n} checks, ${bad} failure${bad === 1 ? '' : 's'}`);
process.exit(bad ? 1 : 0);
