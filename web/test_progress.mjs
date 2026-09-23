/**
 * The learner progression page, held to the control plane it claims to run.
 *
 * `web/build_progress.py` writes `web/trade_craft_progress.html`: the real
 * classes in `control/` - LearnerProfile, SkillGraph, ZpdDial, Sequencer, the
 * skill gates and the hint ladder - carried into one page and run over
 * whatever this browser recorded under `tc-training`. The page states
 * constants, draws a ladder, defends a recommendation and reports a gate
 * state, and every one of those is a claim about a module or a registry. This
 * suite recomputes each claim from the file that owns it and holds the SHIPPED
 * PAGE to the answer.
 *
 * THE CHECK THAT MATTERS MOST is `[browser] a record of nothing but passes,
 * carrying fields that claim a gate outright, still opens no gate`. A page
 * that reports progress is worth having only if it cannot report progress
 * that did not happen. The storage it reads is editable by anyone holding the
 * device, so the seed that check drives it with is hostile: eighty clean
 * passes, plus `gate: true`, `certified: true`, `mastered: true` and
 * `gate_qualifying: true` written straight into the episodes. The page must
 * still show every gate shut, and it must show the reason in gates.mjs's own
 * words.
 *
 * WHICH FILE EACH CHECK READS is in its message, always, because a check that
 * matches a GENERATOR's comment quoting the string it is hunting for in the
 * PAGE has bitten this bundle repeatedly:
 *
 *   [control]   control/*.mjs - the modules, imported and read, no page
 *   [registry]  the registries only - no page involved
 *   [shipped]   the built HTML, and the script carried inside it
 *   [browser]   the rendered DOM in headless Chromium (--browser only)
 *
 * MATCH STRUCTURE, NEVER A SENTENCE. Every check below reads an element, an
 * id or a data attribute - `data-fig`, `data-weight-term`, `data-dial-const`,
 * `data-gate-const`, `data-rung`, `data-hint-const`, `data-quote`,
 * `data-tier`, `data-skill`, `data-edge`, `data-gate-pass`, `data-mastered`,
 * `data-triage`. A check that searched the prose would fire on the page's own
 * honest explanations, which say the words "gate", "mastered" and "certified"
 * many times precisely in order to say that none of them applies.
 *
 * NO BROWSER BY DEFAULT. verify_all.sh opens no browser, so the default run is
 * static. `--browser` adds the DOM checks against a served copy.
 *
 *   node web/test_progress.mjs
 *   node web/test_progress.mjs --browser [--origin=http://127.0.0.1:8811]
 *   node web/test_progress.mjs --page=/tmp/broken.html --root=/tmp/broken-root
 *   node web/test_progress.mjs --browser --url=http://127.0.0.1:8812/broken.html
 *
 * `--page`, `--root` and `--url` exist for the mutation tests: point the suite
 * at a broken copy and watch the check that covers that fault fail by name. A
 * check nobody has watched fail is not a check.
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
const PAGE = resolve(arg('page') !== null ? arg('page') : join(HERE, 'trade_craft_progress.html'));
const ORIGIN = arg('origin') !== null ? arg('origin') : 'http://127.0.0.1:8811';
const PAGE_URL = arg('url') !== null ? arg('url') : `${ORIGIN}/web/${PAGE.split('/').pop()}`;
const WANT_BROWSER = args.includes('--browser');

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.log('FAIL  ' + m);
  for (const e of evidence) console.log('      ' + e);
};

const readText = (rel) => readFileSync(join(ROOT, rel), 'utf8');
const readJSON = (rel) => JSON.parse(readText(rel));

/* ------------------------------------------------------------- the sources */
const SKILLS_PATH = 'pack/registry/skills.json';
const SIMS_PATH = 'sims/registry/sims.json';
const HALLS_PATH = 'pack/registry/halls.json';
const AUTH_PATH = 'auth/registry/auth.json';
const TRAINING_PATH = 'training/registry/training.json';
const LPA_PATH = 'control/lpa.mjs';
const HINTS_PATH = 'control/hints.mjs';
const GRAPH_PATH = 'control/graph.mjs';
const GATES_PATH = 'control/gates.mjs';
const DIAL_PATH = 'control/dial.mjs';
const SEQUENCER_PATH = 'control/sequencer.mjs';
const APP_PATH = 'web/build_3d.py';
const MODULES = [LPA_PATH, HINTS_PATH, GRAPH_PATH, GATES_PATH, DIAL_PATH, SEQUENCER_PATH];
const SUITES = ['control/test.mjs', 'control/test_graph.mjs', 'control/test_hints.mjs'];

const skillsReg = readJSON(SKILLS_PATH);
const simsReg = readJSON(SIMS_PATH);
const hallsReg = readJSON(HALLS_PATH);
const authReg = readJSON(AUTH_PATH);
const trainingReg = readJSON(TRAINING_PATH);
const SKILLS = skillsReg.skills;
const BINDINGS = simsReg.hall_bindings;

/* the control modules, imported - the same declarations the page carries */
const M = (rel) => pathToFileURL(join(ROOT, rel)).href;
const { RUNG_CREDIT } = await import(M(LPA_PATH));
const { RUNGS, HINT_POLICY, masteryCeiling } = await import(M(HINTS_PATH));
const { GATE } = await import(M(GATES_PATH));
const { BAND, DEFAULTS, STATES } = await import(M(DIAL_PATH));
const { WEIGHTS, POLICY } = await import(M(SEQUENCER_PATH));

const byId = new Map(SKILLS.map((s) => [s.skill_id, s]));
const byUnion = new Map();
for (const s of SKILLS) {
  if (!byUnion.has(s.union)) byUnion.set(s.union, []);
  byUnion.get(s.union).push(s);
}
const STRANDS = [...new Set(SKILLS.map((s) => s.strand))];
const seatsOfHall = (hall) => (hall in BINDINGS ? BINDINGS[hall] : []);

/* ------------------------------------------------------- the shipped page -- */
const html = readFileSync(PAGE, 'utf8');

/** The page's inline scripts, in order, as the tokenizer would cut them. */
function scriptsOf(text) {
  const out = [];
  const re = /<script\b[^>]*>/gi;
  let m;
  while ((m = re.exec(text)) !== null) {
    const close = text.indexOf('</script', m.index + m[0].length);
    out.push({ tag: m[0], body: text.slice(m.index + m[0].length, close < 0 ? text.length : close) });
    re.lastIndex = close < 0 ? text.length : close;
  }
  return out;
}
const scripts = scriptsOf(html);
const moduleScript = scripts.find((s) => /type\s*=\s*["']module["']/.test(s.tag));
const dataScript = scripts.find((s) => /id\s*=\s*["']tcdata["']/.test(s.tag));
const SCRIPT = moduleScript === undefined ? '' : moduleScript.body;
/* the page's OWN half of that script: everything after the marker the
   generator writes between the carried modules and the renderer. Every check
   that asks what the PAGE does reads this half, never the carried modules -
   the modules legitimately contain `??`, `setItem` and the word `certified`. */
const MARK = '/* ---- web/build_progress.py: the page ---- */';
const RENDERER = SCRIPT.includes(MARK) ? SCRIPT.slice(SCRIPT.indexOf(MARK) + MARK.length) : '';

/** attributes of every element carrying `attr`, as [{...attrs}] */
function tagsWith(attr) {
  const out = [];
  const re = new RegExp(`<[a-zA-Z][^>]*\\b${attr}\\s*=\\s*"[^"]*"[^>]*>`, 'g');
  for (const m of html.matchAll(re)) {
    const a = {};
    for (const p of m[0].matchAll(/([a-zA-Z_:][-\w:.]*)\s*=\s*"([^"]*)"/g)) a[p[1]] = p[2];
    out.push(a);
  }
  return out;
}
/** the text of the first element carrying attr="value" */
function textOf(attr, value) {
  const re = new RegExp(`<([a-zA-Z][\\w-]*)[^>]*\\b${attr}\\s*=\\s*"${value}"[^>]*>([\\s\\S]*?)</\\1>`);
  const m = re.exec(html);
  return m === null ? null : m[2];
}
const decode = (s) => s.replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&amp;/g, '&')
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>');

/* ======================================================== [control] checks */

/**
 * The same two mechanical edits build_progress.py applies, re-derived here
 * from the module sources rather than from the generator: drop the `import`
 * lines, strip a leading `export `. If the page's copy is not byte-for-byte
 * this, the page has become a second implementation of the control plane and
 * everything it reports is a second opinion.
 */
function carried(rel) {
  return readText(rel).split('\n')
    .filter((l) => !/^import\b.*?;\s*$/.test(l))
    .map((l) => l.replace(/^export\s+(?=const|function|class|let|var)/, ''))
    .join('\n');
}
{
  const missing = MODULES.filter((rel) => !SCRIPT.includes(carried(rel)));
  ok(`[shipped] the page carries all ${MODULES.length} control modules verbatim - `
    + 'the module source with its imports dropped and its exports stripped, and nothing else '
    + 'changed',
    missing.length === 0,
    missing.map((rel) => `${rel} is not in the page's module script as control/ writes it - `
      + 'the page is no longer running the control plane, it is running a copy of it'));
}
{
  /* a name declared twice at module top level is a SyntaxError on load */
  const dupes = [];
  const seen = new Map();
  for (const rel of MODULES) {
    for (const m of carried(rel).matchAll(/^(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)/gm)) {
      if (seen.has(m[1])) dupes.push(`${m[1]}: ${seen.get(m[1])} and ${rel}`);
      else seen.set(m[1], rel);
    }
  }
  const NEEDED = ['LearnerProfile', 'SkillGraph', 'ZpdDial', 'Sequencer', 'HintEngine',
    'checkSkillGate', 'scoreLevelTest', 'scoreJobsiteFinal', 'certified', 'masteryCeiling',
    'WEIGHTS', 'POLICY', 'GATE', 'DEFAULTS', 'BAND', 'RUNGS', 'HINT_POLICY', 'STATES'];
  const absent = NEEDED.filter((x) => !seen.has(x));
  ok(`[control] the ${MODULES.length} modules concatenate into one script without a collision, `
    + `and declare all ${NEEDED.length} names the page addresses`,
    dupes.length === 0 && absent.length === 0,
    [...dupes.map((d) => `declared twice: ${d}`),
      ...absent.map((a) => `no declaration of ${a} in any carried module`)]);
}
{
  /* the page must not hold a second opinion about any of this */
  const RESERVED = ['class LearnerProfile', 'class SkillGraph', 'class ZpdDial',
    'class Sequencer', 'class HintEngine', 'function checkSkillGate', 'function certified',
    'function masteryCeiling', 'const WEIGHTS', 'const POLICY', 'const GATE'];
  const hits = RESERVED.filter((r) => RENDERER.includes(r));
  ok("[shipped] the page's own renderer redeclares none of the control plane: it asks the "
    + 'carried modules and lays out their answers',
    RENDERER.length > 0 && hits.length === 0,
    RENDERER.length === 0
      ? [`the renderer marker ${MARK} is not in the page; nothing could be checked`]
      : hits.map((h) => `the renderer declares its own ${h}`));
}

/* ======================================================= [shipped] figures */
{
  const lines = (rel) => readText(rel).replace(/\n+$/, '').split('\n').length;
  const APP = readText(APP_PATH);
  const want = {
    'control-lines': MODULES.reduce((a, r) => a + lines(r), 0),
    'app-hits': ['LearnerProfile', 'ZpdDial', 'Sequencer', 'SkillGraph', 'checkSkillGate',
      'HintEngine', 'certified('].reduce((a, s) => a + APP.split(s).length - 1, 0),
    cells: byUnion.get(hallsReg.halls[0].slug).length,
    halls: hallsReg.halls.length,
    sims: Object.keys(simsReg.sims).length,
    'unbound-halls': hallsReg.halls.length - Object.keys(BINDINGS).length,
  };
  const got = {};
  for (const t of tagsWith('data-fig')) {
    const body = textOf('data-fig', t['data-fig']);
    const m = body === null ? null : /<b>([^<]*)<\/b>/.exec(body);
    got[t['data-fig']] = m === null ? null : Number(m[1].replace(/,/g, ''));
  }
  const wrong = Object.keys(want).filter((k) => got[k] !== want[k]);
  ok(`[shipped] every headline figure equals the file that owns it (${Object.keys(want).length} `
    + 'recomputed here from control/, the registries and the app source)',
    wrong.length === 0,
    wrong.map((k) => `data-fig="${k}": the page says ${got[k]}, the source says ${want[k]}`));
  ok('[shipped] the page reports the finding it exists for as a COUNT of how many times the 3D '
    + `app names any control class (${want['app-hits']}), not as a sentence`,
    'app-hits' in got && got['app-hits'] === want['app-hits'],
    [`data-fig="app-hits"=${got['app-hits']} recomputed=${want['app-hits']}`]);
}
{
  const rows = tagsWith('data-weight-term');
  const got = Object.fromEntries(rows.map((r) => [r['data-weight-term'],
    Number(decode(textOf('data-weight-term', r['data-weight-term']))
      .replace(/[\s\S]*?class="num">([^<]*)<[\s\S]*/, '$1'))]));
  const keys = Object.keys(WEIGHTS);
  const same = keys.length === rows.length && keys.every((k) => got[k] === WEIGHTS[k]);
  ok(`[shipped] the ${keys.length} sequencer weights on the page are ${SEQUENCER_PATH}'s WEIGHTS, `
    + 'and they sum to 1 so the page may render each as a share of the pick',
    same && Math.abs(Object.values(WEIGHTS).reduce((a, b) => a + b, 0) - 1) < 1e-9,
    [`page=${JSON.stringify(got)}`, `module=${JSON.stringify(WEIGHTS)}`]);
}
{
  const want = {
    'BAND.lo': BAND.lo, 'BAND.hi': BAND.hi,
    setpointOffset: DEFAULTS.setpointOffset, window: DEFAULTS.window,
    loopGain: DEFAULTS.loopGain, stepDown: DEFAULTS.stepDown, stepUpBase: DEFAULTS.stepUpBase,
    railLo: DEFAULTS.railLo, railHi: DEFAULTS.railHi, sessionDelta: DEFAULTS.sessionDelta,
    recoveryDrop: DEFAULTS.recoveryDrop,
  };
  const got = {};
  for (const r of tagsWith('data-dial-const')) {
    const m = /class="num">([^<]*)</.exec(textOf('data-dial-const', r['data-dial-const']));
    got[r['data-dial-const']] = m === null ? null : Number(m[1]);
  }
  const wrong = Object.keys(want).filter((k) => got[k] !== want[k]);
  ok(`[shipped] every dial constant on the page is ${DIAL_PATH}'s own `
    + `(${Object.keys(want).length}: the band, the setpoint offset, the gain, the steps, the `
    + 'rails, the session cap and the recovery drop)',
    wrong.length === 0 && Object.keys(got).length === Object.keys(want).length,
    wrong.map((k) => `data-dial-const="${k}": page=${got[k]} module=${want[k]}`));
}
{
  const want = {
    'GATE.masteryThreshold': GATE.masteryThreshold,
    'GATE.consecutiveUnaided': GATE.consecutiveUnaided,
    'GATE.atOrAbove': GATE.atOrAbove,
    'GATE.levelTest.questions': GATE.levelTest.questions,
    'GATE.levelTest.passPct': GATE.levelTest.passPct,
    'GATE.levelTest.retakeLockHours': GATE.levelTest.retakeLockHours,
    'POLICY.verifyAtOrAbove': POLICY.verifyAtOrAbove,
    'POLICY.verifyRun': POLICY.verifyRun,
    'POLICY.verifyMinEvidence': POLICY.verifyMinEvidence,
  };
  const got = {};
  for (const r of tagsWith('data-gate-const')) {
    const m = /class="num">([^<]*)</.exec(textOf('data-gate-const', r['data-gate-const']));
    got[r['data-gate-const']] = m === null ? null : Number(m[1]);
  }
  const wrong = Object.keys(want).filter((k) => got[k] !== want[k]);
  ok(`[shipped] every gate constant on the page is ${GATES_PATH}'s and ${SEQUENCER_PATH}'s own `
    + `(${Object.keys(want).length}: the three tiers and the difficulty a demonstration must be `
    + 'served at to count)',
    wrong.length === 0 && Object.keys(got).length === Object.keys(want).length,
    wrong.map((k) => `data-gate-const="${k}": page=${got[k]} module=${want[k]}`));
}
{
  const rows = tagsWith('data-rung');
  const same = rows.length === RUNGS.length
    && RUNGS.every((r, i) => rows[i]['data-rung'] === String(r.rung)
      && Number(rows[i]['data-credit']) === r.credit);
  const creditAgrees = RUNGS.every((r, i) => RUNG_CREDIT[i] === r.credit);
  ok(`[shipped] the help ladder on the page is ${HINTS_PATH}'s RUNGS, rung for rung and credit `
    + `for credit (${RUNGS.length} rungs), and ${LPA_PATH}'s RUNG_CREDIT is the same schedule - `
    + 'one table, so a hint cannot be cheap in one subsystem and expensive in another',
    same && creditAgrees,
    [`page=${JSON.stringify(rows.map((r) => [r['data-rung'], r['data-credit']]))}`,
      `module=${JSON.stringify(RUNGS.map((r) => [r.rung, r.credit]))}`,
      `RUNG_CREDIT=${JSON.stringify(RUNG_CREDIT)}`]);
}
{
  const want = {
    dwellSeconds: HINT_POLICY.dwellSeconds, maxRung: HINT_POLICY.maxRung,
    socraticMaxTurns: HINT_POLICY.socraticMaxTurns, fadeWindow: HINT_POLICY.fadeWindow,
    fadeThreshold: HINT_POLICY.fadeThreshold, fadeContractTasks: HINT_POLICY.fadeContractTasks,
  };
  const got = {};
  for (const r of tagsWith('data-hint-const')) {
    const m = /class="num">([^<]*)</.exec(textOf('data-hint-const', r['data-hint-const']));
    got[r['data-hint-const']] = m === null ? null : Number(m[1]);
  }
  const wrong = Object.keys(want).filter((k) => got[k] !== want[k]);
  ok(`[shipped] every hint-policy constant on the page is ${HINTS_PATH}'s own, including the `
    + `turn ceiling on a Socratic escalation (socraticMaxTurns=${HINT_POLICY.socraticMaxTurns})`,
    wrong.length === 0 && 'socraticMaxTurns' in got,
    wrong.map((k) => `data-hint-const="${k}": page=${got[k]} module=${want[k]}`));
}
{
  const gatesSrc = readText(GATES_PATH);
  const flat = (s) => s.replace(/\s+/g, ' ').trim();
  const quotes = tagsWith('data-quote').map((t) => t['data-quote']);
  const cert = textOf('data-quote', 'certified');
  const job = textOf('data-quote', 'jobsite-final');
  const inSrc = (q) => q !== null && flat(gatesSrc).includes(flat(decode(q)));
  ok(`[shipped] the certification rule and the jobsite final are QUOTED from ${GATES_PATH}, not `
    + 'paraphrased: both expressions appear verbatim in the module',
    quotes.includes('certified') && quotes.includes('jobsite-final') && inSrc(cert) && inSrc(job),
    [`certified quote: ${cert === null ? 'absent' : flat(decode(cert)).slice(0, 110)}`,
      `jobsite quote: ${job === null ? 'absent' : flat(decode(job)).slice(0, 110)}`]);
}
{
  const TIERS_PROV = ['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED'];
  const tiers = tagsWith('data-tier').map((t) => t['data-tier']);
  const strays = tiers.filter((t) => !TIERS_PROV.includes(t));
  ok(`[shipped] every provenance tier the page declares is one of the ${TIERS_PROV.length} this `
    + `bundle uses (${tiers.length} chips), and none of them is AI-SYNTHESIZED - that word `
    + 'belongs to orbis/ and describes generated video',
    tiers.length > 0 && strays.length === 0 && !tiers.includes('AI-SYNTHESIZED'),
    strays.map((t) => `data-tier="${t}" is not a provenance tier of this bundle`));
}

/* ------------------------------------------------ the record the page reads */
{
  const want = {
    progress: authReg.records_named.progress_key,
    training: authReg.records_named.training_key,
    training_on: trainingReg.storage.toggle_key,
    identity: authReg.storage.identity_key,
  };
  const payload = dataScript === undefined ? null : JSON.parse(dataScript.body);
  const got = payload === null ? null : payload.keys;
  const same = got !== null && Object.keys(want).every((k) => got[k] === want[k]);
  ok('[shipped] the four localStorage keys the page reads are the ones the registries declare '
    + `(${AUTH_PATH} names the record and identity keys, ${TRAINING_PATH} the recorder toggle), `
    + 'and the two registries agree with each other about the training key',
    same && trainingReg.storage.key === authReg.records_named.training_key,
    [`page=${JSON.stringify(got)}`, `registries=${JSON.stringify(want)}`]);
}
{
  /* a page that reports a record must not be able to change it */
  const writes = ['setItem', 'removeItem', 'localStorage.clear', 'sessionStorage.setItem'];
  const hits = writes.filter((w) => RENDERER.includes(w));
  ok('[shipped] the page only ever READS the device record: its renderer calls no storage '
    + `writer (${writes.join(', ')})`,
    RENDERER.length > 0 && hits.length === 0,
    hits.map((h) => `the renderer calls ${h}`));
}
{
  /* fail closed: no bare `??` and no defaulted lookup over data that should
     exist. The carried modules use `??` legitimately, so only the page's own
     half is scanned. */
  const stripped = RENDERER.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/[^\n]*/g, '$1');
  const hits = [...stripped.matchAll(/\?\?/g)].map((m) => stripped.slice(Math.max(0, m.index - 60), m.index + 12).replace(/\s+/g, ' '));
  ok("[shipped] the page's own renderer contains no `??`: every value that may be absent is "
    + 'named and branched on, because a default substituted for a missing record is this page '
    + 'deciding what the record meant',
    RENDERER.length > 0 && hits.length === 0,
    hits.slice(0, 4).map((h) => `...${h}...`));
}

/* ------------------------- the honesty rule, checked in the page's source -- */
{
  /* Every attempt the replay builds is stamped gate_qualifying: false, and
     nothing anywhere stamps it true. That one literal is what makes it
     impossible for a replayed record to satisfy checkSkillGate. */
  const stampsFalse = /gate_qualifying:\s*false/.test(RENDERER);
  const stampsTrue = /gate_qualifying:\s*true/.test(RENDERER);
  ok('[shipped] every attempt the replay hands the gates is stamped `gate_qualifying: false`, '
    + 'and nothing in the page stamps one true - the record does not say what difficulty a run '
    + 'was served at, so no replayed run can count toward a gate',
    stampsFalse && !stampsTrue,
    [stampsFalse ? '' : 'no `gate_qualifying: false` stamp in the renderer',
      stampsTrue ? 'the renderer stamps `gate_qualifying: true` somewhere' : ''].filter(Boolean));
}
{
  /* data-gate-pass and data-mastered may only ever carry a checkSkillGate
     answer. A literal "true" assigned to either is the fault this check
     exists for. */
  const literal = /'data-(?:gate-pass|mastered|demonstrated|believed)':\s*'true'/.test(RENDERER)
    || /'data-(?:gate-pass|mastered|demonstrated|believed)':\s*"true"/.test(RENDERER);
  const fromGate = /checkSkillGate\(/.test(RENDERER);
  const masteredBoundToGate = /'data-mastered':\s*String\(g[t]?\.pass\)/.test(RENDERER);
  ok('[shipped] the page can only put a gate or a mastery claim on screen by asking '
    + 'checkSkillGate: `data-mastered` is bound to the gate result and not to the posterior, '
    + 'and no gate attribute is ever written as a literal',
    fromGate && masteredBoundToGate && !literal,
    [`calls checkSkillGate: ${fromGate}`,
      `data-mastered bound to the gate result: ${masteredBoundToGate}`,
      `a gate attribute written as a literal: ${literal}`]);
}

/* ======================================================== [browser] checks */
/** the seed: hostile on purpose - see the header. */
const SEED_HALL = 'ironworkers';
const SEED_RUNS = 80;
const SEED_MISSES = 6;          // seed B: the misses a learner takes while finding their level
function seedScript(misses) {
  const sims = seatsOfHall(SEED_HALL).map((b) => b.sim);
  return `(() => {
  const misses = ${misses};
  const sims = ${JSON.stringify(sims)};
  const eps = [];
  const t0 = Date.parse('2026-09-01T09:00:00.000Z');
  for (let i = 0; i < ${SEED_RUNS}; i++) {
    const day = Math.floor(i / 10);
    eps.push({ t: new Date(t0 + day*86400000 + (i%10)*900000).toISOString(), kind: 'sim',
      campus: 'treasure-island', hall: ${JSON.stringify(SEED_HALL)}, sim: sims[i % sims.length],
      scenario: 'bay-steel', controls: ['slew the jib'], actor: 'human',
      /* hostile: fields that CLAIM a gate, a certification and a qualifying
         serve difficulty. Nothing may read them. */
      gate: true, certified: true, mastered: true, gate_qualifying: true, rung: 0,
      difficulty: 99, p_mastery: 1,
      outcome: { passed: i >= misses, gate: true, certified: true,
                 rows: [{ axis: 'placement', value: '0.4', ok: i >= misses }] } });
  }
  for (let i = 0; i < 3; i++) eps.push({ t: new Date(t0 + 9*86400000 + i*1000).toISOString(),
    kind: 'sim', campus: 'treasure-island', hall: ${JSON.stringify(SEED_HALL)}, sim: sims[0],
    scenario: 'bay-steel', controls: [], actor: 'scripted-reference',
    operator: { level: 'optimal', seed: 1, scenario: 'bay-steel', steps: 400, dt: 0.02 },
    outcome: { passed: true, rows: [] } });
  for (let i = 0; i < 2; i++) eps.push({ t: new Date(t0 + 9*86400000 + 5000 + i*1000).toISOString(),
    kind: 'sim', campus: 'treasure-island', hall: 'welders', sim: 'weld-bead', scenario: 'x',
    controls: [], actor: 'human', outcome: { passed: true, rows: [] } });
  eps.push({ t: new Date(t0 + 9*86400000 + 9000).toISOString(), kind: 'advisor',
    campus: 'treasure-island', hall: ${JSON.stringify(SEED_HALL)}, advisor: 'a', topic: 't',
    answer_kind: 'record' });
  eps.push({ t: new Date(t0 + 9*86400000 + 10000).toISOString(), kind: 'sim',
    campus: 'treasure-island', hall: ${JSON.stringify(SEED_HALL)}, sim: 'weld-bead',
    scenario: 'x', controls: [], actor: 'human', outcome: { passed: true, rows: [] } });
  eps.push({ t: new Date(t0 + 9*86400000 + 11000).toISOString(), kind: 'sim',
    campus: 'treasure-island', hall: ${JSON.stringify(SEED_HALL)}, sim: sims[0], scenario: 'x',
    controls: [], actor: 'human' });
  localStorage.setItem(${JSON.stringify(authReg.records_named.training_key)}, JSON.stringify(eps));
  localStorage.setItem(${JSON.stringify(authReg.records_named.progress_key)}, JSON.stringify({
    stations: ['st-a','st-b','st-c'], sims: Object.fromEntries(
      sims.map((s) => [s, { runs: 20, passed: true }])), tools: {}, walk: {} }));
  localStorage.setItem(${JSON.stringify(authReg.storage.identity_key)}, JSON.stringify({
    v: 1, method: 'local', label: 'bench fitter, bay 3', authenticates: false }));
})();`;
}

/** everything the DOM checks read, in one pass */
const SCRAPE = `(() => {
  const at = (id, a) => { const e = document.getElementById(id); return e === null ? null : e.getAttribute(a); };
  const all = (sel, a) => [...document.querySelectorAll(sel)].map((e) => e.getAttribute(a));
  return {
    picked: at('picknote', 'data-picked-because'),
    sel: document.getElementById('hallpick').value,
    empty: at('emptynote', 'data-empty'),
    profile: at('profilebox', 'data-profile'),
    shown: at('profilebox', 'data-shown'),
    attempts: at('profilebox', 'data-attempts'),
    identity: at('idline', 'data-identity'),
    keys: [...document.querySelectorAll('[data-key]')].map((e) => e.getAttribute('data-key') + '=' + e.getAttribute('data-key-state')),
    triage: Object.fromEntries([...document.querySelectorAll('[data-triage]')].map((e) => [e.getAttribute('data-triage'), Number(e.getAttribute('data-triage-n'))])),
    replayQualifying: at('replaynote', 'data-replay-qualifying'),
    replayDays: at('replaynote', 'data-replay-days'),
    cells: all('#ladder [data-skill]', 'data-skill'),
    requires: [...document.querySelectorAll('#ladder [data-edge="requires"]')].map((e) => e.getAttribute('data-from') + '|' + e.getAttribute('data-to')),
    supports: document.querySelectorAll('#ladder [data-edge="supports"]').length,
    interferes: document.querySelectorAll('#ladder [data-edge="interferes"]').length,
    ladderFigs: Object.fromEntries([...document.querySelectorAll('[data-ladder]')].map((e) => [e.getAttribute('data-ladder'), Number(e.querySelector('b').textContent)])),
    nodeMastered: all('#ladder [data-skill]', 'data-mastered'),
    nodes: Object.fromEntries([...document.querySelectorAll('#ladder [data-skill]')].map((e) => [
      e.getAttribute('data-skill'),
      { evidence: Number(e.getAttribute('data-evidence')), theta: Number(e.getAttribute('data-theta')),
        mastery: Number(e.getAttribute('data-mastery')), ready: e.getAttribute('data-ready'),
        attempts: Number(e.getAttribute('data-attempts')) }])),
    nodeGate: all('#ladder [data-skill]', 'data-gate-pass'),
    gates: [...document.querySelectorAll('[data-gate-skill]')].map((e) => ({
      skill: e.getAttribute('data-gate-skill'), pass: e.getAttribute('data-gate-pass'),
      believed: e.getAttribute('data-gate-believed'), demonstrated: e.getAttribute('data-gate-demonstrated'),
      qualifying: Number(e.getAttribute('data-gate-qualifying')),
      attempts: Number(e.getAttribute('data-gate-attempts')),
      mastery: Number(e.getAttribute('data-gate-mastery')),
      why: e.lastElementChild.textContent })),
    gatesPassed: Number(at('gatesum', 'data-gates-passed')),
    gatesBelieved: Number(at('gatesum', 'data-gates-believed')),
    gatesTotal: Number(at('gatesum', 'data-gates-total')),
    certified: at('certline', 'data-certified'),
    pick: at('pickline', 'data-pick-skill'),
    pickMode: at('pickline', 'data-pick-mode'),
    pickDifficulty: Number(at('pickline', 'data-pick-difficulty')),
    pickCeiling: at('pickline', 'data-pick-ceiling'),
    pickScored: at('pickline', 'data-pick-scored'),
    parts: Object.fromEntries([...document.querySelectorAll('[data-part]')].map((e) => [e.getAttribute('data-part'), Number(e.getAttribute('data-part-contribution'))])),
    partsNone: document.querySelectorAll('[data-parts="none"]').length,
    candidates: all('[data-candidate]', 'data-candidate'),
    dialState: at('dialline', 'data-dial-state'),
    dialSetpoint: Number(at('dialline', 'data-dial-setpoint')),
    dialMove: at('diallast', 'data-dial-move'),
    hintCeiling: at('hintline', 'data-hint-ceiling'),
    hintFromMastery: at('hintline', 'data-hint-from-mastery'),
    hintTaskCeiling: at('hintline', 'data-hint-task-ceiling'),
    asks: [...document.querySelectorAll('[data-ask]')].map((e) => e.getAttribute('data-ask') + '/' + e.getAttribute('data-ask-refused') + '/' + e.getAttribute('data-ask-granted')),
    hook: typeof window.__tcProgress === 'function' ? window.__tcProgress() : null,
  };
})();`;

if (!WANT_BROWSER) {
  console.log('  --  [browser] the DOM checks were not run: pass --browser (and serve the bundle) '
    + 'to drive the page in headless Chromium');
} else {
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
  });
  const pageErrors = [], consoleErrors = [];
  const hall = SEED_HALL;
  const mine = byUnion.get(hall);
  const wantCells = mine.map((s) => s.skill_id).sort();
  const wantEdges = mine.flatMap((s) => s.requires.map((e) => `${s.skill_id}|${e}`)).sort();
  const root = mine.filter((s) => s.requires.length === 0);
  const seatSkills = [...new Set(seatsOfHall(hall).map((b) => b.skill_id))];

  const open = async (url, seed) => {
    const ctx = await browser.newContext();
    const pg = await ctx.newPage();
    pg.on('pageerror', (e) => pageErrors.push(String(e)));
    pg.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
    if (seed) await pg.addInitScript(seed);
    await pg.goto(url, { waitUntil: 'load' });
    const out = await pg.evaluate(SCRAPE);
    await ctx.close();
    return out;
  };

  /* ---- 1. empty storage, nothing chosen ---- */
  const blank = await open(PAGE_URL, null);
  ok('[browser] with an empty store the page invents nothing: no hall is selected, the record '
    + 'panel reports all four keys absent or unset, and no profile is shown',
    blank.sel === '' && blank.picked === 'nothing' && blank.empty === 'no-record'
    && blank.shown === 'false' && blank.profile === 'unpicked' && blank.identity === 'none'
    && blank.hook === null
    && blank.keys.every((k) => /=(absent|unset)$/.test(k)),
    [`sel="${blank.sel}" picked=${blank.picked} empty=${blank.empty} shown=${blank.shown}`,
      `keys=${JSON.stringify(blank.keys)} identity=${blank.identity} hook=${blank.hook}`]);

  /* ---- 2. empty storage, a hall chosen: the machinery runs on an empty profile ---- */
  const emptyHall = await open(`${PAGE_URL}?hall=${hall}`, null);
  ok(`[browser] on an EMPTY profile the page still runs the machinery and says the profile is `
    + 'empty: zero attempts, zero gates, certified false, and the sequencer\'s own cold-start '
    + `pick on the hall's root skill at the first rung of POLICY.calibrationLadder `
    + `(${POLICY.calibrationLadder[0]})`,
    emptyHall.profile === 'empty' && emptyHall.empty === 'empty-profile'
    && emptyHall.attempts === '0' && emptyHall.gatesPassed === 0
    && emptyHall.certified === 'false'
    && root.some((s) => s.skill_id === emptyHall.pick)
    && emptyHall.pickMode === 'calibrating'
    && emptyHall.pickDifficulty === POLICY.calibrationLadder[0],
    [`profile=${emptyHall.profile} empty=${emptyHall.empty} attempts=${emptyHall.attempts}`,
      `pick=${emptyHall.pick} mode=${emptyHall.pickMode} difficulty=${emptyHall.pickDifficulty}`,
      `the hall's root skill(s): ${root.map((s) => s.skill_id).join(', ')}`]);
  ok(`[browser] the ladder the page draws is this hall's own: ${wantCells.length} cells and `
    + `${wantEdges.length} prerequisite edges, exactly the ones ${SKILLS_PATH} declares, with `
    + 'its support and interference edges too',
    JSON.stringify([...emptyHall.cells].sort()) === JSON.stringify(wantCells)
    && JSON.stringify([...emptyHall.requires].sort()) === JSON.stringify(wantEdges)
    && emptyHall.supports === mine.reduce((a, s) => a + s.supports.length, 0)
    && emptyHall.interferes === mine.reduce((a, s) => a + s.interferes.length, 0)
    && emptyHall.ladderFigs.cells === wantCells.length
    && emptyHall.ladderFigs.edges === wantEdges.length
    && emptyHall.ladderFigs.attempted === 0,
    [`dom cells=${emptyHall.cells.length} registry=${wantCells.length}`,
      `dom requires=${emptyHall.requires.length} registry=${wantEdges.length}`,
      `dom supports=${emptyHall.supports} interferes=${emptyHall.interferes}`,
      `figs=${JSON.stringify(emptyHall.ladderFigs)}`]);
  ok('[browser] on an empty profile the sequencer still defends its pick: every one of the '
    + `${Object.keys(WEIGHTS).length} weighted terms is on screen with its contribution, and `
    + 'the candidate it picked is one of the candidates it scored',
    emptyHall.pickScored === 'true'
    && Object.keys(WEIGHTS).every((k) => k in emptyHall.parts)
    && 'total' in emptyHall.parts
    && emptyHall.candidates.includes(emptyHall.pick),
    [`parts=${JSON.stringify(emptyHall.parts)}`,
      `candidates=${JSON.stringify(emptyHall.candidates)} pick=${emptyHall.pick}`]);
  ok('[browser] on an empty profile the help ladder is open to its full height '
    + `(masteryCeiling at the prior is ${masteryCeiling(0.15)}), and a hint asked for with no `
    + 'pause is refused by the engine with its own dwell rule',
    emptyHall.hintCeiling === String(masteryCeiling(0.15))
    && emptyHall.asks.length === 2
    && emptyHall.asks[0] === 'asked with no pause/dwell/0'
    && /\/none\/1$/.test(emptyHall.asks[1]),
    [`ceiling=${emptyHall.hintCeiling} fromMastery=${emptyHall.hintFromMastery}`,
      `asks=${JSON.stringify(emptyHall.asks)}`]);

  /* ---- 3. THE CHECK THAT MATTERS MOST ---- */
  const seeded = await open(PAGE_URL, seedScript(0));
  const gatesSrc = readText(GATES_PATH);
  {
    const everyShut = seeded.gates.every((g) => g.pass === 'false');
    const everyUnmastered = seeded.nodeMastered.every((v) => v === 'false');
    const everyUnqualified = seeded.gates.every((g) => g.qualifying === 0);
    const believedSome = seeded.gates.some((g) => g.believed === 'true'
      && g.mastery >= GATE.masteryThreshold);
    const whyFromModule = seeded.gates.every((g) => gatesSrc.includes(g.why));
    ok(`[browser] a record of nothing but passes (${SEED_RUNS} of them), carrying fields that `
      + 'claim a gate, a certification and a qualifying serve difficulty outright, still opens '
      + 'NO gate and marks NO skill mastered: every gate reads not passed, every qualifying '
      + 'count is 0, certified() answers false - and at least one skill IS believed at or above '
      + `GATE.masteryThreshold (${GATE.masteryThreshold}), so the shut gate is a real refusal `
      + 'and not an empty profile',
      everyShut && everyUnmastered && everyUnqualified && believedSome
      && seeded.gatesPassed === 0 && seeded.certified === 'false'
      && seeded.replayQualifying === '0'
      && seeded.nodeGate.every((v) => v === 'false') && whyFromModule,
      [`gates passed=${seeded.gatesPassed}/${seeded.gatesTotal} believed=${seeded.gatesBelieved}`,
        `certified=${seeded.certified} replay qualifying=${seeded.replayQualifying}`,
        `rows=${JSON.stringify(seeded.gates)}`,
        `nodes marked mastered=${seeded.nodeMastered.filter((v) => v === 'true').length}`,
        whyFromModule ? '' : 'a gate reason on the page is not a sentence gates.mjs contains']
        .filter(Boolean));
  }
  {
    /* the implication, over whatever rows exist: it can never be satisfied by
       fabricating, only by real evidence */
    const bad = seeded.gates.filter((g) => g.pass === 'true'
      && !(g.believed === 'true' && g.demonstrated === 'true'
        && g.qualifying >= GATE.consecutiveUnaided));
    const mismatch = seeded.cells.filter((_, i) => seeded.nodeMastered[i] !== seeded.nodeGate[i]);
    ok('[browser] a gate may read passed only with the evidence gates.mjs requires - believed, '
      + `demonstrated, and at least GATE.consecutiveUnaided (${GATE.consecutiveUnaided}) `
      + 'gate-qualifying demonstrations - and a cell reads mastered on exactly the cells whose '
      + 'gate passed, never on the posterior alone',
      bad.length === 0 && mismatch.length === 0,
      [...bad.map((g) => `${g.skill} reads passed on believed=${g.believed} `
        + `demonstrated=${g.demonstrated} qualifying=${g.qualifying}`),
        ...mismatch.map((c) => `${c}: data-mastered and data-gate-pass disagree`)]);
  }
  {
    const t = seeded.triage;
    ok(`[browser] the replay fed the modules exactly the ${SEED_RUNS} runs this device recorded `
      + 'as yours in this hall, and dropped the rest by name: the scripted reference operator\'s '
      + 'runs, another hall\'s, another episode kind, a seat this ladder does not carry, and a '
      + 'run with no outcome',
      t['fed to the profile'] === SEED_RUNS && t['dropped: not you'] === 3
      && t['dropped: another hall'] === 2 && t['dropped: not a seat run'] === 1
      && t['dropped: seat not on this ladder'] === 1 && t['dropped: no outcome'] === 1
      && seeded.attempts === String(SEED_RUNS),
      [`triage=${JSON.stringify(t)} profilebox attempts=${seeded.attempts}`]);
  }
  {
    /* Seed A is a record of nothing but wins on the one cell this hall's seats
       prove. What SHOULD change is the learner's position on that cell and the
       shape of the ladder around it - and what should NOT change is the
       recommendation, because the cell those seats prove rests on prerequisites
       this record has never shown. The sequencer sends the learner back down
       the ladder, and that is the right answer, not a missing feature. */
    const seatSkill = seatSkills[0];
    const before = emptyHall.nodes[seatSkill];
    const after = seeded.nodes[seatSkill];
    const unlockedByIt = mine.filter((x) => x.requires.includes(seatSkill)).map((x) => x.skill_id);
    ok('[browser] the record moves the learner on the cell its seats prove and nowhere else: '
      + `${SEED_RUNS} attempts and a posterior at or above GATE.masteryThreshold on `
      + `${seatSkill}, which was untouched on the empty profile - and the cell(s) that rest on `
      + `it (${unlockedByIt.join(', ') || 'none'}) become ready, while the cells it rests on do `
      + 'not, because propagated credit moves theta and never mastery',
      before.evidence === 0 && before.attempts === 0
      && after.attempts === SEED_RUNS && after.evidence === SEED_RUNS
      && after.mastery >= GATE.masteryThreshold && after.theta !== before.theta
      && unlockedByIt.every((c) => seeded.nodes[c].ready === 'true'
        && emptyHall.nodes[c].ready === 'false')
      && mine.find((x) => x.skill_id === seatSkill).requires
        .every((r) => seeded.nodes[r].ready === emptyHall.nodes[r].ready)
      && seeded.ladderFigs.ready > emptyHall.ladderFigs.ready,
      [`${seatSkill}: empty=${JSON.stringify(before)}`,
        `${seatSkill}: seeded=${JSON.stringify(after)}`,
        `ready: empty=${emptyHall.ladderFigs.ready} seeded=${seeded.ladderFigs.ready}`,
        `unlocked by it=${JSON.stringify(unlockedByIt.map((c) => [c, seeded.nodes[c].ready]))}`]);
    ok('[browser] and the recommendation stays on the root of the ladder, defended by a score: '
      + 'the cell this hall\'s seats prove is not ready, so it is not a candidate however many '
      + 'runs the record holds - the candidate pool grew by the cells the record did unlock',
      seeded.pickScored === 'true' && !seeded.candidates.includes(seatSkill)
      && seeded.candidates.length > emptyHall.candidates.length
      && Object.keys(WEIGHTS).every((k) => k in seeded.parts),
      [`empty candidates=${JSON.stringify(emptyHall.candidates)}`,
        `seeded candidates=${JSON.stringify(seeded.candidates)}`,
        `pick=${seeded.pick} mode=${seeded.pickMode} scored=${seeded.pickScored}`]);
  }

  /* ---- 4. seed B: the same record with the misses a learner actually takes ---- */
  const curve = await open(PAGE_URL, seedScript(SEED_MISSES));
  {
    ok(`[browser] the same ${SEED_RUNS} runs with the first ${SEED_MISSES} missed take the `
      + 'sequencer somewhere else entirely: it leaves the cold-start placement and serves a '
      + 'verification run on the cell the seats prove, at or above the gate difficulty '
      + `(theta ${POLICY.verifyAtOrAbove}) with the scaffold ceiling closed to 0 - practice `
      + 'optimises for learning, proof optimises for proof',
      seatSkills.includes(curve.pick) && curve.pickMode === 'verify'
      && curve.pickCeiling === '0' && curve.pickScored === 'false' && curve.partsNone === 1
      && curve.pickDifficulty
        >= curve.nodes[curve.pick].theta + POLICY.verifyAtOrAbove - 0.05
      && curve.pick !== emptyHall.pick && curve.pickDifficulty > emptyHall.pickDifficulty,
      [`empty: pick=${emptyHall.pick} mode=${emptyHall.pickMode} d=${emptyHall.pickDifficulty}`,
        `curve: pick=${curve.pick} mode=${curve.pickMode} d=${curve.pickDifficulty} `
        + `ceiling=${curve.pickCeiling} theta=${curve.nodes[curve.pick].theta}`,
        `the seats in this hall prove: ${seatSkills.join(', ')}`]);
    ok('[browser] on that verification run the dial has left CALIBRATING and logged a move it '
      + `can explain, and the help ladder has closed from ${emptyHall.hintCeiling} to 0: asked `
      + 'for a hint, the engine refuses it as a verification rather than falling silent',
      STATES.includes(curve.dialState) && curve.dialState !== emptyHall.dialState
      && curve.dialMove !== 'none' && curve.dialSetpoint !== emptyHall.dialSetpoint
      && curve.hintCeiling === '0' && curve.hintTaskCeiling === '0'
      && curve.asks.some((a) => a.includes('/verification/')),
      [`empty dial=${emptyHall.dialState} sp=${emptyHall.dialSetpoint}`,
        `curve dial=${curve.dialState} sp=${curve.dialSetpoint} move=${curve.dialMove}`,
        `curve ceiling=${curve.hintCeiling} fromMastery=${curve.hintFromMastery} `
        + `task=${curve.hintTaskCeiling}`,
        `asks=${JSON.stringify(curve.asks)}`]);
    ok('[browser] and the verification run it offers still opens no gate: a run the sequencer '
      + 'is willing to serve as proof is not proof until it has been served, so every gate is '
      + 'shut, nothing is mastered and certified() is false on this profile too',
      curve.gatesPassed === 0 && curve.certified === 'false'
      && curve.nodeMastered.every((v) => v === 'false')
      && curve.gates.every((g) => g.qualifying === 0)
      && curve.replayQualifying === '0',
      [`gates=${curve.gatesPassed}/${curve.gatesTotal} certified=${curve.certified} `
        + `qualifying=${curve.replayQualifying}`,
        `rows=${JSON.stringify(curve.gates)}`]);
    ok('[browser] the seeded profile is reported as a record and not as an empty one, the hall '
      + 'was offered because the record names it rather than because it was first in the list, '
      + 'and the ladder counts the cells the record actually reached',
      seeded.profile === 'record' && seeded.empty === 'has-record'
      && seeded.sel === hall && seeded.picked !== 'nothing'
      && seeded.ladderFigs.attempted === seatSkills.length
      && seeded.ladderFigs.cells === wantCells.length
      && seeded.identity === 'label' && seeded.replayDays === '8',
      [`profile=${seeded.profile} empty=${seeded.empty} sel=${seeded.sel} `
        + `because=${seeded.picked}`,
        `figs=${JSON.stringify(seeded.ladderFigs)} identity=${seeded.identity} `
        + `days=${seeded.replayDays}`]);
  }

  ok('[browser] the page raised no uncaught error and logged no console error across the empty '
    + 'store, an empty profile and two seeded records',
    pageErrors.length === 0 && consoleErrors.length === 0,
    [...pageErrors.slice(0, 3), ...consoleErrors.slice(0, 3)]);
  await browser.close();
}

console.log(`\nprogress: ${n} checks, ${bad} failure${bad === 1 ? '' : 's'}`);
process.exit(bad ? 1 : 0);
