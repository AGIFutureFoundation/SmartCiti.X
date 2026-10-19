/* xr/test_session.mjs - the MOCKED-SESSION harness, as a suite.
 *
 *   node xr/test_session.mjs            static half only: pure node, no browser (what verify_all.sh runs)
 *   node xr/test_session.mjs --static   the same, said out loud
 *   flock <the shared browser lock> node xr/test_session.mjs --browser
 *                                        the static half, then the MOCKED session driven in
 *                                        headless Chromium (landing browser round, <= 90 s)
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

/* ---- honesty, in every file this harness ships ----------------------- */
{
  for (const [n, s] of [['the mock', MOCK], ['the harness', HARN], ['this suite', SELF]]) {
    ok(/MOCKED/.test(s) && /[Nn]o physical headset/.test(s), `${n} says MOCKED session and no physical headset`);
  }
  ok(!/headset (run|verified|tested)\b/i.test(MOCK + HARN) && !/(verified|proven) on (a )?(real|physical) (headset|device)/i.test(MOCK + HARN), 'no file claims a headset run');
  const all = MOCK + HARN;
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
    ok(false, 'the browser half ran to the end', String(e && e.stack || e).slice(0, 400));
  } finally { stop(); }
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
