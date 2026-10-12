/**
 * Loop machinery verification.
 *
 * The loop's whole value is that a checkpoint cannot say more than it ran:
 * the gates are executed, the ledger refuses a malformed or dishonest cycle,
 * and the honesty and secrets patterns catch what they claim to catch. These
 * checks exercise the pure functions directly; nothing here runs
 * verify_all.sh, which would be slow and recursive.
 */
import { readFileSync, writeFileSync, mkdtempSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateLedger, validateCycle, AGENTS, GATE_IDS, manifestVersion } from './cycle.mjs';
import { GATES, honestyHits, secretHits, parseVerify, OVERCLAIM } from './evals.mjs';
import { heartbeatLine, registryVersions, runHeartbeat } from './heartbeat.mjs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const HERE = fileURLToPath(new URL('.', import.meta.url));
const ledger = JSON.parse(readFileSync(join(HERE, 'registry/cycles.json'), 'utf8'));
const mv = manifestVersion();

const gates = GATES.map(([id, name]) => ({ id, name, status: 'pass', detail: '', ms: 1 }));
const goodCycle = {
  n: 1, started: '2026-10-12T09:14:00Z', ended: '2026-10-12T09:44:00Z', sprint: 'loop machinery',
  shipped: ['loop/heartbeat.mjs'], agents: [{ name: 'Eval Warden', task: 'build gates', result: 'pass' }],
  gates, heartbeat_ok: true, checks_total: 1594, video: null, commit: null,
};

/* --------------------------------------------------------------- ledger --- */
ok('the cycle ledger validates against its schema and the manifest pack_version',
  validateLedger(ledger, mv).length === 0 && ledger.pack_version === mv);
ok('the ledger loop is 30-minute cadence, 5 cycles planned, started 2026-10-12T09:14:00Z',
  ledger.loop.cadence_min === 30 && ledger.loop.cycles_planned === 5
  && ledger.loop.started === '2026-10-12T09:14:00Z');
ok('the ledger honesty line says nothing here is deployed, and trips the validator if dropped',
  /nothing here is deployed/i.test(ledger.honesty)
  && validateLedger({ ...ledger, honesty: 'all good' }, mv).some((e) => /honesty/.test(e)));
ok('a well-formed cycle validates; a wrong pack_version does not',
  validateCycle(goodCycle, 1).length === 0
  && validateLedger({ ...ledger, pack_version: '9.9.9' }, mv).some((e) => /pack_version/.test(e)));
ok('a cycle with a failing gate cannot record a commit',
  validateCycle({ ...goodCycle, gates: gates.map((g, i) => (i ? g : { ...g, status: 'fail' })), commit: 'abc1234' }, 1)
    .some((e) => /stops the release/.test(e))
  && validateCycle({ ...goodCycle, commit: 'abc1234' }, 1).length === 0);
ok('cycle agents must be one of the eight named team agents',
  validateCycle({ ...goodCycle, agents: [{ name: 'Growth Hacker', task: 'x', result: 'y' }] }, 1).length === 1);

/* ------------------------------------------------- cycle.mjs end to end --- */
{
  const dir = mkdtempSync(join(tmpdir(), 'loop-test-'));
  const L = join(dir, 'cycles.json');
  writeFileSync(L, JSON.stringify(ledger, null, 2));
  const bad = join(dir, 'bad.json');
  writeFileSync(bad, JSON.stringify({ n: 1, started: 'yesterday', sprint: '', shipped: 'everything', agents: [] }));
  const r = spawnSync('node', [join(HERE, 'cycle.mjs'), 'add', '--json', bad, '--ledger', L, '--state', dir],
    { encoding: 'utf8' });
  ok('cycle.mjs add rejects a malformed cycle fixture with exit 1 and leaves the ledger unchanged',
    r.status === 1 && /cycle refused/.test(r.stderr)
    && JSON.parse(readFileSync(L, 'utf8')).cycles.length === ledger.cycles.length);
  const good = join(dir, 'good.json');
  writeFileSync(good, JSON.stringify({ ...goodCycle, n: ledger.cycles.length + 1,
    started: '2026-10-12T12:00:00Z', ended: '2026-10-12T12:30:00Z' }));
  const r2 = spawnSync('node', [join(HERE, 'cycle.mjs'), 'add', '--json', good, '--ledger', L, '--state', dir],
    { encoding: 'utf8' });
  ok('cycle.mjs add appends a valid cycle fixture to a temp ledger',
    r2.status === 0 && JSON.parse(readFileSync(L, 'utf8')).cycles.length === ledger.cycles.length + 1);
}

/* ---------------------------------------------------------------- evals --- */
ok('evals.mjs declares exactly the gates EV-01..EV-08, in order, matching the ledger schema',
  GATES.map(([id]) => id).join() === 'EV-01,EV-02,EV-03,EV-04,EV-05,EV-06,EV-07,EV-08'
  && GATES.map(([id]) => id).join() === GATE_IDS.join());
ok('honesty regex catches "accredited by X" and "partnered with" claims',
  honestyHits('The course is accredited by the State Board.').length === 1
  && honestyHits('We partnered with a district last spring.').length === 1
  && OVERCLAIM.test('deployed to three schools'));
ok('honesty regex passes negated or planned sentences: "not accredited", "planned deployment to"',
  honestyHits('This course is not accredited.').length === 0
  && honestyHits('Nothing here is accredited, deployed to schools or endorsed.').length === 0
  && honestyHits('Being deployed to a pilot site is planned for 2027.').length === 0
  && honestyHits('`accredited by` is a phrase the lint hunts.').length === 0);
ok('a regex rule table naming the phrases is not a claim; a sentence beside it still is',
  honestyHits("const CLAIM = /accredited|endorsed|certified by|partnered with/i;").length === 0
  && honestyHits('Rules: accredited|endorsed. We are endorsed by ACME.').length === 1);
ok('honesty check is per sentence: a negation in the previous sentence does not excuse a claim',
  honestyHits('This is not a demo. It is accredited by ACME.').length === 1);
{
  const fake = 'ghp_' + 'A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8';
  ok('secrets regex catches a fake ghp_ token fixture, an AWS key id and a PEM header',
    secretHits(`token = "${fake}"`).length === 1
    && secretHits('aws_access_key_id = AKIA' + 'ABCDEFGHIJKLMNOP').length === 1
    && secretHits('-----BEGIN ' + 'RSA PRIVATE KEY-----').length === 1);
}
ok('secrets regex passes clean text, including ordinary words like "task-" and "sk-ills"',
  secretHits('The skill graph has no secrets. Run task-runner; sk-1 is a label.').length === 0);
ok('verify_all.sh summary parser reads the total and the failing suites',
  JSON.stringify(parseVerify('ok    a.mjs  3 checks\nFAIL  b/test.mjs\n----\n1594 checks, 1 failing suites\nstderr trailing\n'))
    === JSON.stringify({ total: 1594, failing: 1, failed: ['b/test.mjs'] })
  && parseVerify('garbage') === null);

/* ------------------------------------------------------------ metaprompt --- */
{
  const mp = readFileSync(join(HERE, 'METAPROMPT.md'), 'utf8');
  ok('METAPROMPT names all 8 agents, each with a role prompt',
    AGENTS.length === 8 && AGENTS.every((a) => mp.includes(`**${a}.**`) && mp.includes(`| ${a} |`)));
  const words = mp.split('## Orchestrator meta-prompt')[1].split('## Role prompts')[0].trim().split(/\s+/).length;
  ok(`the orchestrator meta-prompt is about 200 words (${words}) and states the honesty doctrine`,
    words >= 150 && words <= 260 && /labelled planned/.test(mp)
    && /no partners, accreditation, endorsements or deployments/.test(mp)
    && /If any gate fails, the release stops/.test(mp));
  const rows = mp.split('\n').filter((l) => /^\| [A-Z][a-z]+ ?[A-Za-z]* \| `/.test(l));
  const dirs = rows.map((l) => l.split('|')[3].trim().split(' ')[0]);
  ok('every agent writes exactly one directory and no two agents share one',
    rows.length === 8 && new Set(dirs).size === 8);
}

/* ------------------------------------------------------------- heartbeat --- */
{
  const line = runHeartbeat(new Date('2026-10-12T10:00:00Z'));
  ok('a heartbeat line has the {ts, ok, checks:[{name,ok,detail}]} shape',
    typeof line.ts === 'string' && !Number.isNaN(Date.parse(line.ts)) && typeof line.ok === 'boolean'
    && Array.isArray(line.checks) && line.checks.length >= 7
    && line.checks.every((c) => typeof c.name === 'string' && typeof c.ok === 'boolean' && typeof c.detail === 'string'));
  ok('heartbeat is ok on soft warnings and not ok on a hard failure',
    heartbeatLine([{ name: 'a', ok: false, detail: '', hard: false }]).ok === true
    && heartbeatLine([{ name: 'a', ok: false, detail: '', hard: true }]).ok === false);
  ok('every registry declaring pack_version declares the manifest version',
    registryVersions().length > 20 && registryVersions().every((r) => r.version === mv));
  // loop/state/ is gitignored, so on a clean checkout there is no history yet;
  // the check still runs (and counts) on every machine so README's count holds.
  const hb = join(HERE, 'state/heartbeat.jsonl');
  const hbLast = existsSync(hb) ? JSON.parse(readFileSync(hb, 'utf8').trim().split('\n').pop()) : null;
  ok('loop/state/heartbeat.jsonl is absent on a clean checkout, or its last line has the heartbeat shape',
    hbLast === null || (typeof hbLast.ts === 'string' && typeof hbLast.ok === 'boolean' && Array.isArray(hbLast.checks)
      && hbLast.checks.every((c) => 'name' in c && 'ok' in c && 'detail' in c)));
}

ok('a cycle may not record its review video by a machine path (media lives outside the repo)',
  validateCycle({ ...goodCycle, video: { path: '/tmp/x/review_c1.mp4', duration_s: 120 } }, 1).length > 0
  && validateCycle({ ...goodCycle, video: { path: 'review_c1.mp4', duration_s: 120 } }, 1).length === 0);
{
  const draft = JSON.parse(readFileSync(join(HERE, 'registry/tech_draft.json'), 'utf8'));
  ok('the planning draft carries no gate id the executed gates use (DRAFT-EV only, and says so)',
    draft.evals.every((e) => e.id.startsWith('DRAFT-EV-') && !GATE_IDS.includes(e.id))
    && /loop\/evals\.mjs/.test(draft.status_note));
}

console.log(`${n} checks passed`);
