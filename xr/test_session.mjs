/* xr/test_session.mjs - the MOCKED-SESSION harness, as a suite.
 *
 *   node xr/test_session.mjs            static half only: pure node, no browser (what verify_all.sh runs)
 *   node xr/test_session.mjs --static   the same, said out loud
 *   flock <the shared browser lock> node xr/test_session.mjs --browser
 *                                        the static half, then the MOCKED session driven in
 *                                        headless Chromium (landing browser round, <= 90 s)
 *   flock <lock> node xr/test_session.mjs --browser --seats=A|B|C|all|id,id,...
 *                                        the static half, then ONE mocked session that enters VR once and
 *                                        drives the named sim seats in turn through the controller map
 *                                        (key state, then completion; <= 90 s a batch, see SEAT_BATCHES)
 *                                        options: --coach-secs=N (cap per seat), --probe[=all] (time each
 *                                        seat's reference run headlessly before the session)
 *
 * MOCKED session in headless Chromium. No physical headset, no browser XR
 * runtime, no tracking. The roadmap criterion "one VR sim module running
 * against a section 24 environment package end to end" is therefore
 * "mocked half met, headset half not met" - and this file does not say more.
 *
 * What the static half holds: the mock covers every WebXR member three.js
 * r160's WebXRManager touches (read out of the vendored build), the page
 * still exposes the hooks and the thumbstick adapter the harness drives, the
 * signal plan is derived from the sims registry and still matches the
 * adapter, the seat's section 24 yard surface exists, and the honesty text
 * is present. What the browser half holds is in xr/session_harness.mjs.
 */
import { readFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';
import { SEAT, HALL, SCENARIO, SEAT_DEF, SEQ, signalPlan, KEY_STICK, runSession } from './session_harness.mjs';
import { SEAT_IDS, seatDef, firstScenario, seatVerbs, sweepWant, SWEEPS, coachAllowed, hallOrder, levelOf, judgeSeat, runSeats } from './seats_harness.mjs';
import { SEAT_BATCHES, SEAT_EXPECT, SEAT_COACH_SECS } from './seat_batches.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
const R = (p) => readFileSync(join(ROOT, p), 'utf8');
let pass = 0, fail = 0;
const ok = (c, m, d = '') => {
  if (c) { pass++; console.log('  ok ' + m); }
  else { fail++; console.log('FAIL ' + m + (d ? '\n     ' + d : '')); }
};
const args = process.argv.slice(2);
const BROWSER = args.includes('--browser');
console.log('xr/test_session.mjs' + (BROWSER ? ' --browser' : ' (static)'));

const MOCK = R('xr/mock_webxr.js'), HARN = R('xr/session_harness.mjs'), SELF = R('xr/test_session.mjs');
const SEATH = R('xr/seats_harness.mjs'), BATCHF = R('xr/seat_batches.mjs');
const PAGE = R('web/build_3d.py');
const THREE = R('web/vendor/three.module.min.js');
const J = (p) => JSON.parse(R(p));

/* ---- the mock ------------------------------------------------------- */
{
  let parses = true;
  try { new vm.Script(MOCK, { filename: 'mock_webxr.js' }); } catch (e) { parses = false; }
  ok(parses, 'the mock parses as a plain script (it is injected with page.addInitScript, so no module syntax)');
  ok(!/\bimport\s|\bexport\s|require\(/.test(MOCK), 'and it uses no import, export or require');

  // every member of the session / frame / layer / space that three.js r160's WebXRManager
  // calls or reads: the list is checked against three's own source, then against the mock
  const need = {
    'session.requestReferenceSpace': ['requestReferenceSpace', /requestReferenceSpace\(/],
    'session.updateRenderState': ['updateRenderState', /updateRenderState\(/],
    'session.requestAnimationFrame': ['requestAnimationFrame', /requestAnimationFrame\(/],
    'session.addEventListener (select / selectstart / selectend / squeeze / end / inputsourceschange)': ['EventTarget', /"inputsourceschange"/],
    'session.renderState (a baseLayer path: no `layers`)': ['renderState', /renderState\.layers/],
    'session.environmentBlendMode': ['environmentBlendMode', /environmentBlendMode/],
    'frame.getViewerPose': ['getViewerPose', /getViewerPose\(/],
    'frame.getPose': ['getPose', /getPose\(/],
    'layer.getViewport': ['getViewport', /getViewport\(/],
    'layer.framebuffer / framebufferWidth / framebufferHeight': ['framebufferWidth', /framebufferWidth/],
    'layer.fixedFoveation': ['fixedFoveation', /fixedFoveation/],
    'inputSource.targetRaySpace / gripSpace / gamepad': ['targetRaySpace', /targetRaySpace/],
    'gl.makeXRCompatible': ['makeXRCompatible', /makeXRCompatible/],
    'XRWebGLLayer constructor': ['XRWebGLLayer', /new XRWebGLLayer\(/],
  };
  for (const [what, [needle, inThree]] of Object.entries(need)) {
    ok(inThree.test(THREE) && MOCK.includes(needle), `the mock provides ${what}, and three.js r160 still uses it`,
      `in three: ${inThree.test(THREE)}, in mock: ${MOCK.includes(needle)}`);
  }
  ok(/gripSpace/.test(MOCK) && /mapping: 'xr-standard'/.test(MOCK), 'the mock\'s controllers are xr-standard gamepads with a grip and a target-ray space, the mapping the page polls');
  const muts = [...MOCK.matchAll(/MUT: ([a-z-]+)/g)].map((m) => m[1]);
  ok(muts.length >= 5 && new Set(muts).size === muts.length, `the mock tags ${muts.length} one-line mutation points, each named once (${muts.join(', ')})`);
  ok(/framebufferRenderbuffer/.test(MOCK) && /readPixels/.test(MOCK), 'the mock\'s layer is a real WebGL framebuffer that is read back, so "the page drew in both eyes" is measured, not assumed');
  ok(/three tracks|texture-binding cache/.test(MOCK) && !/bindTexture/.test(MOCK), 'the mock never touches three.js\'s texture-binding cache (renderbuffers only)');
}

/* ---- the page still offers what the harness drives -------------------- */
{
  ok(/window\.__tc3dXR = \{[\s\S]*presenting: \(\) => renderer\.xr\.isPresenting[\s\S]*state: \(\) => \(\{/.test(PAGE), 'the page exposes window.__tc3dXR with start, end, presenting and state');
  ok(/window\.__tc3dSim = \{[\s\S]*state: \(\) => opRun/.test(PAGE), 'and window.__tc3dSim.state for the scripted operator\'s run');
  ok(/xrRig\.name = 'xr-rig'|new THREE\.Group\(\); xrRig\.name = 'xr-rig'/.test(PAGE) && /scene\.add\(xrRig\)/.test(PAGE), 'the rig is a named object in the scene, so a harness can listen on three.js\'s controllers');
  ok(/getElementById\('vrBtn'\)\.addEventListener\('click', \(\) => xrStart\('immersive-vr'\)\)/.test(PAGE), 'Enter VR is the page\'s own button, wired to xrStart');
  ok(/requestSession\(mode,\s*\{ requiredFeatures: \['local-floor'\], optionalFeatures: \[XR_HANDS\] \}\)/.test(PAGE) && /XR_HANDS = 'hand-tracking'/.test(PAGE),
    'the session request is local-floor required, hand-tracking optional - what the browser half asserts the mock was asked');
  // the thumbstick adapter's own verbs, which KEY_STICK in the harness restates
  const m = PAGE.match(/const want = \{ KeyW: ly < -DZ, KeyS: ly > DZ, KeyA: lx < -DZ, KeyD: lx > DZ,\s*KeyQ: rx < -DZ, KeyE: rx > DZ \};/);
  ok(!!m, 'the adapter maps the left stick to W/S/A/D and the right stick x to Q/E, as the harness\'s KEY_STICK says');
  ok(KEY_STICK.W[0] === 'left' && KEY_STICK.W[1] === 1 && KEY_STICK.W[2] === -1 && KEY_STICK.S[2] === 1 && KEY_STICK.A[1] === 0 && KEY_STICK.A[2] === -1 && KEY_STICK.D[2] === 1
    && KEY_STICK.Q[0] === 'right' && KEY_STICK.Q[2] === -1 && KEY_STICK.E[2] === 1, 'and KEY_STICK in the harness restates exactly that (up is stick left/forward, down is right/back)');
  ok(/rose\('trig', trig\) && !opRun\) sim\.action\?\.\(\)/.test(PAGE) && /rose\('a', a\)\) xrWatchToggle\(\)/.test(PAGE) && /rose\('b', b\)\) exitSim\(\)/.test(PAGE) && /rose\('b', b\)\) ses\.end\(\)/.test(PAGE),
    'the right trigger is the seat\'s Space verb, A starts the scripted operator, B leaves the seat in a seat and ends the session elsewhere');
  ok(/btn\(R, 0\)/.test(PAGE) && /btn\(R, 4\) \|\| btn\(L, 4\)/.test(PAGE) && /btn\(R, 5\) \|\| btn\(L, 5\)/.test(PAGE) && /axes\[2\] \|\| 0, gp\.axes\[3\] \|\| 0/.test(PAGE),
    'the page reads xr-standard buttons 0 / 4 / 5 and thumbstick axes 2 and 3 - the indices the mock writes');
}

/* ---- the seat, from its registry, and its section 24 package ---------- */
{
  const plan = signalPlan();
  const want = { up: 'Q', down: 'E', 'swing-l': 'A', 'swing-r': 'D', out: 'W', in: 'S', stop: 'Space' };
  ok(JSON.stringify(Object.fromEntries(Object.entries(plan).sort())) === JSON.stringify(Object.fromEntries(Object.entries(want).sort())),
    'the harness derives each signal\'s key from the seat\'s own declared controls (hoist up/down Q/E, swing A/D, trolley out/in W/S, STOP Space)', JSON.stringify(plan));
  ok(SEQ.length >= 4 && SEQ[SEQ.length - 1] === 'stop' && SEQ.every((s) => plan[s]), `the scenario ${SCENARIO} sequence (${SEQ.join(' > ')}) is all signals the plan can send, ending in STOP`);
  ok(SEAT_DEF.halls.includes(HALL) && SEAT_DEF.view_modes[0] === 'orbit', `the hall ${HALL} teaches ${SEAT}, and the seat opens in its orbit view (the rig is placed at the orbit camera)`);
  const x = SEAT_DEF.xr;
  ok(/STOP/.test(x.trigger) && /A \/ X/.test(x.primary) && /B \/ Y/.test(x.secondary) && x.grip_key === null, 'the seat\'s xr mapping in the registry names trigger = STOP, A/X = the scripted operator, B/Y = leave');
  const fin = J('surfaces/registry/finishes.json');
  const surf = fin.catalogue[SEAT_DEF.yard.surface];
  ok(!!surf && typeof surf.roughness === 'number' && typeof surf.metalness === 'number' && /^section 24|^section 24 of/.test(fin.spec), `the seat's yard surface (${SEAT_DEF.yard.surface}) is in the section 24 catalogue with a roughness and a metalness the browser half compares against the floor mesh`);
  ok(SEAT_DEF.operator.levels.includes('optimal') && /document\.getElementById\('opLvl'\)\.value \|\| 'optimal'/.test(PAGE), 'the scripted operator\'s default level is optimal when the HUD has not chosen one');
}

/* ---- the other seats: controller map, coach and judge (pure node) ------ */
{
  const others = SEAT_IDS.filter((i) => i !== SEAT);
  ok(SEAT_IDS.length === 11 && others.length === 10, `the registry holds ${SEAT_IDS.length} seats: the rigging signal call (driven by the session harness) and ${others.length} others for the seat harness`);
  const LETTERS = ['W', 'A', 'S', 'D', 'Q', 'E', 'R', 'X', 'C'];
  let bad = [];
  for (const id of SEAT_IDS) {
    const d = seatDef(id), v = seatVerbs(d);
    const unknown = v.toks.filter((t) => t !== 'Space' && !LETTERS.includes(t));
    const letters = v.toks.filter((t) => ['R', 'X', 'C'].includes(t));
    if (unknown.length || letters.length > 1 || (letters.length === 1) !== !!d.xr.grip_key || (letters[0] && d.xr.grip_key !== 'Key' + letters[0]) || (v.space && !/Space/.test(d.xr.trigger))) bad.push(id);
  }
  ok(bad.length === 0, 'every seat\'s registry controls are W/A/S/D/Q/E, Space, and at most one of R/X/C - and that one is the seat\'s xr grip_key, Space is its xr trigger', bad.join(','));
  ok(SEAT_IDS.every((i) => seatDef(i).scenarios.length >= 1 && firstScenario(i) === seatDef(i).scenarios[0].id), 'each seat opens its first registry scenario in the batch run');
  ok(SEAT_IDS.every((i) => seatDef(i).rubric.length >= 3 && seatDef(i).rubric.every((r) => r.axis)), 'each seat\'s rubric axes (the completion signal) are in the registry');
  // the page's side: the coach hook, anchored, a pure reader of the reference policy
  const blk = (PAGE.match(/\/\* XR-SEATS BEGIN[\s\S]*?XR-SEATS END \*\//) || [''])[0];
  ok((PAGE.match(/XR-SEATS BEGIN/g) || []).length === 1 && (PAGE.match(/XR-SEATS END/g) || []).length === 1 && blk.length > 400, 'the page carries one anchored XR-SEATS block');
  ok(/window\.__tc3dCoach = \{/.test(blk) && ['begin(', 'next()', 'done()', 'state()', 'end()'].every((m) => blk.includes(m)), 'the block exposes begin, next, done, state and end');
  ok(!/\bopRun\s*=[^=]/.test(blk.replace(/\/\*[\s\S]*?\*\//g, '')) && !/sim\.action|(^|[^.\w])keys\[|(^|[^.\w])keys\.Key/.test(blk.replace(/\/\*[\s\S]*?\*\//g, '')), 'the coach never attaches the scripted operator run and never presses a key or the seat\'s action itself: it only returns what the policy would press');
  ok(/OPERATORS\[c\.sim\]\.step\(sim\.gauges\(\), c\)/.test(blk) && /OP_KEYS\.filter/.test(blk) && /rng: opRng\(/.test(blk), 'it runs the same reference policy opStep runs, on the same context shape opAttach builds, and answers only with OP_KEYS');
  const att = (PAGE.match(/function opAttach\([\s\S]*?\n\}/) || [''])[0];
  ok(att.includes('P: curScenario?.params ?? {}, L: op.levels[level], m: { phase: 0 }') && blk.includes('P: curScenario?.params ?? {}, L: op.levels[level], m: { phase: 0 }'), 'and the coach context is built from the same fields opAttach builds');
  ok(SEAT_IDS.every((i) => new RegExp("'?" + i + "'?:\\s*\\{").test((PAGE.match(/const OPERATORS = \{[\s\S]*?\n\};/) || [''])[0])), 'every seat has a reference policy in the page for the coach to read');
  // the driver in the seat harness restates the stick adapter - checked against it
  ok(/\(has\('KeyD'\) \? 1 : 0\) - \(has\('KeyA'\) \? 1 : 0\), \(has\('KeyS'\) \? 1 : 0\) - \(has\('KeyW'\) \? 1 : 0\)/.test(SEATH) && /\(has\('KeyE'\) \? 1 : 0\) - \(has\('KeyQ'\) \? 1 : 0\)/.test(SEATH),
    'the seat harness writes the left stick x from D minus A and y from S minus W, the right stick x from E minus Q - the sign the page\'s want map reads (checked above against the adapter)');
  ok(/rose\('trig', trig\)/.test(PAGE) && /const press = r\.act && !d\.prevAct/.test(SEATH), 'the Space verb is written as a trigger press edge, never held across two frames, because the page acts on the rising edge only');
  ok(/m\.button\('right', 1, !!\(d\.grip && has\(d\.grip\)\)\)/.test(SEATH) && /btn\(R, 1\) \|\| btn\(L, 1\)/.test(PAGE), 'the grip key is written to the right squeeze button, which the page reads as the seat\'s secondary key');
  ok(/beforeFrame/.test(MOCK) && /m\.beforeFrame = /.test(SEATH), 'the mock calls the driver just before it delivers each frame, so the page reads fresh controllers in that frame');
  ok(SEATH.includes("page.click('#vrBtn')") && !/__tc3dXR\.start\(/.test(SEATH) && /Enter VR once|enter VR once/i.test(SEATH), 'the seat run enters VR once, through the page\'s own button, and never calls the page\'s start hook for it');
  ok(/window\.__tc3dSim\.start\(i, s\)/.test(SEATH), 'seats after the first are started in-session through the page\'s start hook (the call a hall station makes)');

  // hall order and the batch table
  const ord = hallOrder(others);
  ok(ord.length === 10 && new Set(ord).size === 10 && others.every((i) => ord.includes(i)), 'hallOrder returns each seat once', ord.join(','));
  const inBatches = Object.values(SEAT_BATCHES).flat();
  ok(new Set(inBatches).size === inBatches.length && inBatches.every((i) => SEAT_IDS.includes(i)), 'no seat sits in two batches and every batch seat is a registry seat');
  ok(others.every((i) => inBatches.includes(i)), 'the batches together cover the ten seats the rigging session does not');
  ok(Object.keys(SEAT_EXPECT).every((i) => SEAT_IDS.includes(i)) && Object.values(SEAT_EXPECT).every((x) => x === 'completion' || x === 'key-state'), 'the expectation table names only registry seats and only completion or key-state');
  ok(Object.values(SEAT_BATCHES).every((b) => b.length >= 1 && b.length <= 6) && SEAT_COACH_SECS >= 8, 'a batch holds one to six seats (the 90 s budget is the limit, the browser half enforces it)');

  // the judge: a perfect observation passes every check; each broken one fails by name
  const perfect = (id) => {
    const d = seatDef(id), v = seatVerbs(d);
    return { seat: id, started: { sim: id, scenario: firstScenario(id) }, gauges0: { a: '0' }, gauges1: { a: '1' }, gaugesMoved: true,
      sweeps: SWEEPS.map((sw) => ({ label: sw.label, want: sweepWant(d, sw), got: sweepWant(d, sw), heldOk: true, releasedOk: true, after: [] })),
      trigger: { selects: 1, pagePressed: true }, opAttached: false,
      coach: { began: true, keysUsed: [...coachAllowed(d)], steps: 100 },
      panel: { title: d.name, chip: 'Passed', open: true, scripted: false, rows: [...d.rubric.map((r) => ({ axis: r.axis, value: '1', ok: '✓' })), { axis: 'time', value: '3 s', ok: '' }] } };
  };
  const failing = (id, o, e = 'completion') => judgeSeat(id, o, e).filter((c) => !c.ok).map((c) => c.name);
  ok(SEAT_IDS.every((i) => failing(i, perfect(i)).length === 0), 'the judge passes a complete observation for every registry seat (its expectations come from the registry alone)');
  ok(SEAT_IDS.every((i) => judgeSeat(i, perfect(i)).length >= 8), 'and asks at least eight named questions of each seat');
  const t1 = SEAT_IDS[0];
  const mut = (f, e = 'completion') => { const o = perfect(t1); f(o); return failing(t1, o, e); };
  ok(mut((o) => { o.sweeps[0].got = o.sweeps[0].got.slice(1); }).some((n) => /puts exactly those verbs/.test(n)), 'the judge fails a seat whose sticks left a registry verb out of the page\'s keys');
  ok(mut((o) => { o.sweeps[1].got = [...o.sweeps[1].got, 'KeyR']; }).some((n) => /puts exactly those verbs/.test(n)), 'and one that held an extra verb');
  ok(mut((o) => { o.sweeps[1].releasedOk = false; }).some((n) => /puts exactly those verbs/.test(n)), 'and one that kept a verb after release');
  ok(mut((o) => { o.gaugesMoved = false; }).some((n) => /gauge reading moved/.test(n)), 'and one whose gauges never moved');
  ok(mut((o) => { o.trigger.selects = 0; }).some((n) => /right trigger/.test(n)), 'and one the trigger never reached');
  ok(mut((o) => { o.panel = null; }).some((n) => /result panel inside the time cap/.test(n)), 'and one that never reached its result panel');
  ok(mut((o) => { o.panel.title = 'Another Seat'; }).some((n) => /result panel inside the time cap/.test(n)), 'and one whose panel names another seat');
  ok(mut((o) => { o.panel.rows.shift(); }).some((n) => /every rubric axis/.test(n)), 'and one whose panel is missing a rubric axis');
  ok(mut((o) => { o.panel.chip = 'Try again'; }).some((n) => /verdict is Passed/.test(n)), 'and one whose verdict is not a pass');
  ok(mut((o) => { o.panel.rows[0].ok = '✗'; }).some((n) => /verdict is Passed/.test(n)), 'and one with a graded axis marked failed');
  ok(mut((o) => { o.opAttached = true; }).some((n) => /controllers' own/.test(n)), 'and one where the scripted operator\'s run was attached');
  ok(mut((o) => { o.coach.keysUsed.push('KeyZ'); }).some((n) => /every key the coach pressed/.test(n)), 'and one where the coach pressed a key the registry does not name');
  ok(mut((o) => { o.started.scenario = 'x'; }).some((n) => /started the seat/.test(n)), 'and one that opened the wrong scenario');
  ok(failing(t1, null).length === 1 && /time slot/.test(failing(t1, null)[0]) && failing(t1, { skipped: 'no time' }).length === 1, 'and one that was never run (a batch that is too big fails by name)');
  ok(mut((o) => { o.panel = null; o.opAttached = null; }, 'key-state').length === 0, 'a seat expected at key state only is not asked for a result panel');
  ok(levelOf(seatDef(t1), perfect(t1)) === 'completion (pass)' && levelOf(seatDef(t1), { ...perfect(t1), panel: null }) === 'key state only' && levelOf(seatDef(t1), { ...perfect(t1), panel: null, sweeps: [] }) === 'failed' && levelOf(seatDef(t1), { skipped: 'x' }) === 'not run',
    'the report classifies a seat as completion, key state only, failed or not run from the observation alone');
}

/* ---- honesty, in every file this harness ships ----------------------- */
{
  for (const [n, s] of [['the mock', MOCK], ['the harness', HARN], ['the seat harness', SEATH], ['the batch table', BATCHF], ['this suite', SELF]]) {
    ok(/MOCKED/.test(s) && /[Nn]o physical headset/.test(s), `${n} says MOCKED session and no physical headset`);
  }
  ok(!/headset (run|verified|tested)\b/i.test(MOCK + HARN + SEATH + BATCHF) && !/(verified|proven) on (a )?(real|physical) (headset|device)/i.test(MOCK + HARN + SEATH + BATCHF), 'no file claims a headset run');
  const all = MOCK + HARN + SEATH + BATCHF;
  ok(!/\/tmp\/|\$SP|\bmemory\/|\bconsole log|rk_[A-Za-z0-9]/.test(all), 'no internal path, scratch reference or key shape in any shipped file');
  ok(!/\b(opus|sonnet|haiku|claude-[0-9a-z-]+)\b/i.test(all.replace(/Claude's own/g, '')), 'and no model identifier');
}

/* ---- the browser half ------------------------------------------------- */
let server = null;
async function freePort() {
  return new Promise((res) => { const s = createServer(); s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)); }); });
}
if (BROWSER) {
  const t0 = Date.now();
  const port = await freePort();
  server = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1'], { cwd: ROOT, stdio: 'ignore' });
  const pid = server.pid;
  const stop = () => { try { process.kill(pid); } catch { /* gone */ } };
  process.on('exit', stop);
  for (const sg of ['SIGTERM', 'SIGINT']) process.on(sg, () => { stop(); process.exit(143); });
  try {
    for (let i = 0; i < 50; i++) {
      try { const r = await fetch(`http://127.0.0.1:${port}/web/trade_craft_3d.html`, { method: 'HEAD' }); if (r.ok) break; } catch { /* not up yet */ }
      await new Promise((r) => setTimeout(r, 100));
    }
    const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
    const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
      args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
    const mockSrc = process.env.XR_MOCK_PATH ? readFileSync(process.env.XR_MOCK_PATH, 'utf8') : MOCK;
    let res;
    const hard = new Promise((r) => setTimeout(() => r('late'), 88000));
    const seatArg = (args.find((a) => a.startsWith('--seats=')) || '').slice(8);
    if (seatArg) {
      /* ---- the seat batch: one session, the named seats in turn ---------- */
      const argv = (n, d) => { const a = args.find((x) => x.startsWith('--' + n + '=')); return a ? a.slice(n.length + 3) : d; };
      const list = SEAT_BATCHES[seatArg] ? SEAT_BATCHES[seatArg] : seatArg === 'all' ? hallOrder(SEAT_IDS.filter((i) => i !== SEAT)) : seatArg.split(',').filter(Boolean);
      if (!list.length || !list.every((i) => SEAT_IDS.includes(i))) throw new Error('--seats= names an unknown seat: ' + seatArg);
      const probe = args.some((a) => a === '--probe' || a.startsWith('--probe='));
      const probeSeats = argv('probe', '') === 'all' ? hallOrder(SEAT_IDS.filter((i) => i !== SEAT)) : null;
      console.log('seats in this run: ' + list.join(', '));
      const sink = {};
      try {
        res = await Promise.race([runSeats({ sink, browser, base: `http://127.0.0.1:${port}`, mockSrc, seats: list, probe, probeSeats,
          coachMs: Number(argv('coach-secs', SEAT_COACH_SECS)) * 1000, expectOf: (i) => SEAT_EXPECT[i] || 'completion',
          onCheck: (c) => ok(c.ok, 'MOCKED session: ' + c.name + (process.env.XR_TRACE ? ` [+${(c.atMs / 1000).toFixed(1)}s]` : ''), c.detail) }), hard]);
        if (res === 'late') { ok(false, 'the seat batch finished inside its 90 s budget'); res = { measured: sink.measured || { seats: {}, probe: {} } }; }
      } finally { await browser.close().catch(() => {}); }
      const m = res.measured;
      console.log(`MEASURED MOCKED session in headless Chromium (no physical headset), load average ${m.loadBefore} before, ${m.loadAfter} after; boot ${m.bootMs} ms, Enter VR to presenting ${m.enterMs} ms, ${m.totalFrames} session frames, whole run ${((Date.now() - t0) / 1000).toFixed(1)} s`);
      for (const [id, p] of Object.entries(m.probe || {})) console.log(`PROBE ${id}: ${JSON.stringify(p)}`);
      for (const id of list) {
        const o = m.seats[id]; if (!o) { console.log(`SEAT ${id}: not run`); continue; }
        console.log(`SEAT ${id}: ${levelOf(seatDef(id), o)}; seat ${o.seatSecs} s (start ${o.startMs} ms); coach ${o.coach && o.coach.secs} s at ${o.coach && o.coach.fps} fps, ${o.coach && o.coach.steps} controller frames, ${o.coach && o.coach.acts} trigger presses, phase ${o.coach && o.coach.state ? (o.coach.state.phaseIdx + '/' + o.coach.state.phases + ' ' + o.coach.state.phase) : '-'}; panel ${o.panel ? o.panel.title + ' / ' + o.panel.chip + ' / ' + o.panel.rows.map((r) => r.axis + '=' + r.value).join(' ') : 'none'}; sticks moved gauges ${o.gaugesMoved}${o.error ? '; ERROR ' + o.error : ''}`);
      }
      throw new Error('__seats_done__');
    }
    try { res = await Promise.race([runSession({ browser, base: `http://127.0.0.1:${port}`, mockSrc, onCheck: (c) => ok(c.ok, 'MOCKED session: ' + c.name + (process.env.XR_TRACE ? ` [+${(c.atMs / 1000).toFixed(1)}s]` : ''), c.detail) }), hard]);
      if (res === 'late') { ok(false, 'the browser half finished inside its 90 s budget'); res = null; } }
    finally { await browser.close().catch(() => {}); }
    if (!res) throw new Error('no measurements: the run did not finish');
    const m = res.measured;
    console.log(`MEASURED MOCKED session in headless Chromium (no physical headset), load average ${m.loadBefore} before, ${m.loadAfter} after:`);
    console.log(`MEASURED boot ${m.bootMs} ms; Enter VR to presenting ${m.enterMs} ms; ${m.window.sessionFrames} session frames delivered in ${m.window.seconds} s (${m.window.fps} per second, page ran ${m.window.pageFrames});`);
    console.log(`MEASURED delivery gap median ${m.gapMs.median} ms, p95 ${m.gapMs.p95} ms, max ${m.gapMs.max} ms over ${m.gapMs.n} gaps, ${m.totalFrames} frames across two sessions. These are the browser's animation-frame cadence handed to the session, NOT a render rate: one framebuffer read-back waited ${m.readbackDrainMs} ms for the software GPU's queue;`);
    console.log(`MEASURED signals to completion ${m.signalSeconds} s; scripted operator to a pass ${m.operatorSeconds} s; whole browser half ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  } catch (e) {
    if (!(e && e.message === '__seats_done__')) ok(false, 'the browser half ran to the end', String(e && e.stack || e).slice(0, 400));
  } finally { stop(); }
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
