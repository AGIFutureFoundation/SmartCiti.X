/* The MOCKED-SESSION harness: drives ONE sim module (the rigging signal call)
   against its section 24 environment package end to end, inside headless
   Chromium, over a fake `navigator.xr` (xr/mock_webxr.js) that three.js's own
   WebXRManager runs on.

   MOCKED session in headless Chromium. No physical headset, no browser XR
   runtime, no compositor, no tracking. What this measures is the page's XR code
   path under the WebXR interfaces it uses; it says nothing about a headset.

   `runSession({ browser, base, mockSrc, fast })` returns { checks, measured }.
   `checks` is [{ name, ok, detail }]; nothing here prints or exits, so the
   suite (xr/test_session.mjs) and a mutation runner can both call it. */
import { readFileSync } from 'node:fs';

const SIMS = JSON.parse(readFileSync(new URL('../sims/registry/sims.json', import.meta.url), 'utf8'));
const FIN = JSON.parse(readFileSync(new URL('../surfaces/registry/finishes.json', import.meta.url), 'utf8'));

export const SEAT = 'rigging-signals';
export const HALL = 'riggers';
export const SCENARIO = 'bay-first-card';
export const SEAT_DEF = SIMS.sims[SEAT];
export const SEQ = SEAT_DEF.scenarios.find((s) => s.id === SCENARIO).params.seq;

/* signal -> the key the seat's own controls name for it, read off the registry
   ("Q / E" = "signal hoist up / hoist down": the first key is the first
   action). The key -> thumbstick step is the page's declared xr adapter
   (web/build_3d.py, xrInput) and is checked against its source in --static. */
export function signalKeys() {
  const out = {};
  for (const c of SEAT_DEF.controls) {
    const keys = c.keys.split('/').map((k) => k.trim());
    const acts = c.action.replace(/^signal\s+/, '').split('/').map((a) => a.trim().replace(/^signal\s+/, ''));
    keys.forEach((k, i) => { out[acts[i]] = k; });
  }
  return out;
}
const WORD = { 'hoist up': 'up', 'hoist down': 'down', 'swing left': 'swing-l', 'swing right': 'swing-r',
  'trolley out': 'out', 'trolley in': 'in', 'STOP': 'stop' };
export function signalPlan() {
  const byAction = signalKeys(), plan = {};
  for (const [a, k] of Object.entries(byAction)) if (WORD[a]) plan[WORD[a]] = k;
  return plan;                                  // { up: 'Q', down: 'E', ... stop: 'Space' }
}
// key -> [side, axis index (0 = x, 1 = y), sign]: the adapter's declared stick verbs
export const KEY_STICK = { W: ['left', 1, -1], S: ['left', 1, 1], A: ['left', 0, -1], D: ['left', 0, 1],
  Q: ['right', 0, -1], E: ['right', 0, 1] };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const median = (a) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[s.length >> 1] : NaN; };
const pct = (a, p) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.min(s.length - 1, Math.floor(s.length * p))] : NaN; };

export async function runSession({ browser, base, mockSrc, fast = false, cfg = {}, budgetMs = 80000, onCheck = null, phases = null }) {
  const has = (p) => !phases || phases.includes(p);
  const checks = [], measured = {};
  const deadline = Date.now() + budgetMs;
  const ck = (name, ok, detail = '') => { const c = { name, ok: !!ok, detail: String(detail), atMs: Date.now() - (deadline - budgetMs) }; checks.push(c); if (onCheck) onCheck(c); };
  // every wait is capped by what is left of the browser budget (never below 0.8 s), so a stalled
  // phase fails by name instead of eating the run
  const T = (ms) => Math.max(800, Math.min(fast ? 6000 : ms, deadline - Date.now()));
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|favicon/.test(m.text())) errs.push('console: ' + m.text().slice(0, 160)); });
  await page.addInitScript({ content: 'window.__xrMockCfg = ' + JSON.stringify(cfg) + ';\n' + mockSrc });
  // count the page's own (non-session) animation frames, to see the desktop loop come back
  await page.addInitScript(() => {
    const raf = window.requestAnimationFrame.bind(window);
    window.__pageRaf = 0;
    window.requestAnimationFrame = (cb) => { window.__pageRaf++; return raf(cb); };
    window.__rawRaf = raf;
  });
  const ev = (fn, arg) => page.evaluate(fn, arg);
  const mock = () => page.evaluate(() => window.__xrMock.snapshot());
  const frames = () => page.evaluate(() => window.__xrMock.stats.framesDelivered);
  const waitFrames = async (n, ms = 8000) => {
    ms = T(ms);
    const f0 = await frames();
    try { await page.waitForFunction((t) => window.__xrMock.stats.framesDelivered >= t, f0 + n, { timeout: ms, polling: 20 }); return true; }
    catch { return false; }
  };
  const gau = () => ev(() => { const g = window.__tc3d().gau; return g ? Object.fromEntries(Object.entries(g).map(([k, v]) => [k, v.txt ?? v.v])) : null; });
  const load = () => readFileSync('/proc/loadavg', 'utf8').split(' ').slice(0, 3).join(' ');
  measured.loadBefore = load();
  const done = async () => { measured.loadAfter = load(); await ctx.close(); return { checks, measured, errs }; };
  let after = { st: { hud: { texts: {} } } };

  /* ---- 1. boot, with the mock in place before any page script ---------- */
  const url = `${base}/web/trade_craft_3d.html?hall=${HALL}&sim=${SEAT}&scenario=${SCENARIO}`;
  const t0 = Date.now();
  await page.goto(url, { waitUntil: 'load' });
  let booted = true;
  try {
    await page.waitForFunction(() => window.__tc3d && window.__tc3dXR && window.__tc3dSim, null, { timeout: T(60000) });
    await page.waitForFunction(() => window.__tc3d().sim, null, { timeout: T(20000) });
  } catch (e) { booted = false; }
  measured.bootMs = Date.now() - t0;
  ck('the page booted with the mock in place and opened the seat', booted && (await ev(() => window.__tc3d().sim)) === SEAT,
    `sim=${booted ? await ev(() => window.__tc3d().sim) : 'no boot'}`);
  if (!booted) return done();
  const m0 = await mock();
  ck('the mock was installed while the document was still loading, before any page script', m0.readyStateAtInstall === 'loading', m0.readyStateAtInstall);
  let vrShown = false;
  try { await page.waitForFunction(() => document.getElementById('vrBtn').style.display !== 'none', null, { timeout: T(15000) }); vrShown = true; } catch { /* named below */ }
  const m1 = await mock();
  if (!vrShown && !fast) { /* every later phase needs the button: say so by name and stop */ }
  const arShown = await ev(() => document.getElementById('arBtn').style.display !== 'none');
  ck('the page probed immersive-vr through navigator.xr.isSessionSupported and offered Enter VR because it answered yes (AR stays hidden, the mock said no)',
    vrShown && !arShown && m1.supportCalls.includes('immersive-vr'), `calls=${m1.supportCalls.join(',')} vr=${vrShown} ar=${arShown}`);

  if (!vrShown) return done();

  /* ---- 2. the section 24 package this seat runs against ---------------- */
  const yardReg = SEAT_DEF.yard, fin = FIN.catalogue[yardReg.surface];
  const yard = await ev(() => {
    let f = null;
    window.__tc3dScene().traverse((o) => { if (o.userData?.yardSurface) f = o; });
    return f && { surface: f.userData.yardSurface, rough: f.material.roughness, metal: f.material.metalness,
      mapped: !!f.material.map, visible: f.visible, inScene: !!f.parent, page: window.__tc3d().yardSurface };
  });
  ck('the seat stands on its section 24 yard surface: the floor mesh names the registry surface and carries that catalogue entry\'s roughness and metalness',
    yard && yard.surface === yardReg.surface && yard.page === yardReg.surface && Math.abs(yard.rough - fin.roughness) < 1e-6 && Math.abs(yard.metal - fin.metalness) < 1e-6 && yard.mapped,
    JSON.stringify(yard) + ' vs ' + JSON.stringify({ s: yardReg.surface, r: fin.roughness, m: fin.metalness }));
  const preCanvas = await ev(() => { const c = document.querySelector('#main canvas'); return [c.width, c.height]; });

  /* ---- 3. enter VR through the page's own button ----------------------- */
  const tEnter = Date.now();
  await page.click('#vrBtn');
  let presenting = false;
  try { await page.waitForFunction(() => window.__tc3dXR.presenting(), null, { timeout: T(30000) }); presenting = true; } catch { /* named below */ }
  measured.enterMs = Date.now() - tEnter;
  await waitFrames(12, T(20000));
  const m2 = await mock(), st = await ev(() => window.__tc3dXR.state());
  const req = m2.requests[0] || {};
  ck('clicking Enter VR asked for an immersive-vr session with local-floor required and hand-tracking optional',
    m2.requests.length >= 1 && req.mode === 'immersive-vr' && req.required.includes('local-floor') && req.optional.includes('hand-tracking'), JSON.stringify(m2.requests));
  ck('the session started and renderer.xr.isPresenting is true, with the page\'s own state agreeing (mode, local-floor)',
    presenting && m2.sessionsStarted === 1 && st.mode === 'immersive-vr' && st.floor === true && st.refSpace === 'local-floor' && m2.refSpaces.includes('local-floor'),
    `presenting=${presenting} mode=${st.mode} floor=${st.floor} spaces=${m2.refSpaces}`);
  ck('three.js created its XRWebGLLayer and set it as the session\'s base layer (the baseLayer path, no layers array)',
    m2.layersCreated === 1 && m2.renderStates.some((k) => k.includes('baseLayer')), `layers=${m2.layersCreated} states=${JSON.stringify(m2.renderStates)}`);
  ck('both controllers connected through inputsourceschange and three.js built them (left and right), the wrist panel mounted on the left grip',
    m2.inputChanges >= 1 && Object.values(st.hands).sort().join() === 'left,right' && st.hud.mounted === 'left-grip', JSON.stringify({ h: st.hands, hud: st.hud.mounted }));

  if (!presenting) return done();

  /* ---- 4. frames through the session's own rAF -------------------------- */
  const fA = await frames(), pA = (await ev(() => window.__tc3dXR.state())).frames, tA = Date.now();
  await waitFrames(20, T(40000));
  const fB = await frames(), pB = (await ev(() => window.__tc3dXR.state())).frames, tB = Date.now();
  const dF = fB - fA, dP = pB - pA, secs = (tB - tA) / 1000;
  measured.window = { seconds: +secs.toFixed(2), sessionFrames: dF, pageFrames: dP, fps: +(dF / secs).toFixed(1) };
  ck('frames are delivered through the session\'s requestAnimationFrame and the page runs one XR frame for each (counts agree within 3)',
    dF >= 10 && Math.abs(dF - dP) <= 3, `session=${dF} page=${dP} in ${secs.toFixed(1)}s`);
  const tR = Date.now();
  await ev(() => window.__xrMock.readNow());
  measured.readbackDrainMs = Date.now() - tR;     // a read-back waits for every queued GL frame: the software GPU's real backlog
  if (dF === 0) return done();
  const m3 = await mock();
  ck('the page asked the session for a viewer pose on every frame it was given', m3.viewerPoseCalls >= m3.framesDelivered - 3, `poses=${m3.viewerPoseCalls} frames=${m3.framesDelivered}`);
  const st3 = await ev(() => window.__tc3dXR.state());
  ck('the headset pose reached the camera: the camera sits where the mock head is (x 0, y 1.6 above the rig floor, within the sway), and the seat placed the rig at its orbit view',
    Math.abs(st3.head[1] - 1.6) < .05 && Math.abs(st3.head[0]) < .06 && Math.abs(st3.rig[0] - 12) < .1 && Math.abs(st3.rig[2] - 15) < .1,
    `head=${st3.head} rig=${st3.rig}`);
  const rd = m3.lastRead;
  ck('the page drew into the layer\'s framebuffer, in both eyes, and the two eyes differ (read back from the mock\'s framebuffer)',
    rd && rd.status && rd.left.lit > .2 && rd.right.lit > .2 && rd.left.colours >= 6 && rd.right.colours >= 6 && rd.stereoDiff > .3,
    rd ? JSON.stringify({ l: rd.left, r: rd.right, d: +rd.stereoDiff.toFixed(2), size: rd.size }) : 'no readback');
  ck('the wrist panel carries the seat\'s gauges in-session (Step, Called, Given, Wrong signs)',
    ['g:step', 'g:called', 'g:given', 'g:wrong'].every((k) => st3.hud.sprites.includes(k)), st3.hud.sprites.join(','));
  measured.reads = m3.reads.length;

  if (has('play')) {
  /* ---- 5. controller input reaches the seat's handler ------------------ */
  // listen on three's own controller objects for the select events the mock raises
  await ev(() => {
    window.__sel = { start: 0, end: 0, sel: 0 };
    const rig = window.__tc3dScene().getObjectByName('xr-rig');
    for (const c of rig.children.filter((o) => o.children.some((k) => k.isLine))) {   // the target-ray groups
      c.addEventListener('selectstart', () => window.__sel.start++);
      c.addEventListener('selectend', () => window.__sel.end++);
      c.addEventListener('select', () => window.__sel.sel++);
    }
  });
  const plan = signalPlan();
  const tPlay = Date.now(); let gaveUp = null; const stepLog = [];
  for (let i = 0; i < SEQ.length; i++) {
    const sig = SEQ[i], key = plan[sig];
    const called = (await gau()).called;
    if (called !== sig) { gaveUp = `step ${i}: the page calls "${called}", the registry sequence says "${sig}"`; break; }
    let accepted = false;
    for (let tries = 0; tries < (fast ? 4 : 25) && !accepted; tries++) {
      if (key === 'Space') {
        await ev(() => window.__xrMock.button('right', 0, true)); await waitFrames(2); await ev(() => window.__xrMock.button('right', 0, false));
      } else {
        const [side, ax, sign] = KEY_STICK[key];
        await ev(([s, a, v]) => window.__xrMock.stick(s, a === 0 ? v : 0, a === 1 ? v : 0), [side, ax, sign]);
        await waitFrames(2);
        await ev((s) => window.__xrMock.stick(s, 0, 0), side);
      }
      await waitFrames(2);
      const g = await gau();
      accepted = g.step === `${i + 1}/${SEQ.length}`;
      if (!accepted) await sleep(250);               // the crane is still moving from the last call: it holds
    }
    stepLog.push([sig, key, accepted]);
    if (!accepted) { gaveUp = `signal "${sig}" (${key}) never reached the seat`; break; }
    if (i < SEQ.length - 1) await sleep(T(1500));     // one smooth crane move per call
  }
  measured.signalSeconds = +((Date.now() - tPlay) / 1000).toFixed(1);
  try { await page.waitForFunction((n) => (window.__tc3dXR.state().hud.texts['g:step'] || '').includes(n), `${SEQ.length}/${SEQ.length}`, { timeout: T(20000), polling: 100 }); } catch { /* read below */ }
  after = await ev(() => ({ gau: Object.fromEntries(Object.entries(window.__tc3d().gau || {}).map(([k, v]) => [k, v.txt ?? v.v])),
    sel: window.__sel, pbody: document.getElementById('pbody').textContent, open: document.body.classList.contains('open'),
    st: window.__tc3dXR.state(), now: Math.round(performance.now()), dash: document.getElementById('dash').textContent.replace(/\s+/g, ' ') }));
  ck('every signal in the scenario\'s sequence was sent from a thumbstick or the trigger and accepted by the seat in order (Q up, D swing right, W out, E down, trigger STOP)',
    !gaveUp && stepLog.length === SEQ.length && stepLog.every((s) => s[2]), gaveUp || JSON.stringify(stepLog));
  const m4 = await mock();
  ck('the trigger reached three.js\'s controller objects as selectstart / select / selectend, and the left-hand pick path stayed idle',
    m4.selectStart >= 1 && m4.select >= 1 && after.sel.start >= 1 && after.sel.sel >= 1 && after.sel.end >= 1 && after.sel.sel === m4.select,
    JSON.stringify({ mock: [m4.selectStart, m4.select, m4.selectEnd], three: after.sel }));
  ck('the seat reached its completion state in-session: 5/5 calls, 0 wrong, a pass result panel with the calls and wrong rows',
    after.gau.step === `${SEQ.length}/${SEQ.length}` && after.gau.wrong === '0' && /Rigging Signal Call/.test(after.pbody) && /Passed/.test(after.pbody) && /calls\s*5\/5/.test(after.pbody) && /wrong\s*0/.test(after.pbody) && after.open,
    `gau=${JSON.stringify(after.gau)} panel=${after.pbody.slice(0, 160).replace(/\s+/g, ' ')}`);
  ck('the wrist panel catches up to the final step once the page draws its next frames (the sign reads 5/5, as the dash does)',
    !!after.st.hud.texts['g:step'] && after.st.hud.texts['g:step'].includes(`${SEQ.length}/${SEQ.length}`),
    `wrist=${JSON.stringify(after.st.hud.texts)} frames=${after.st.frames} pageNow=${after.now} dashDom=${after.dash}`);
  ck('the page logged the controller\'s last input state (right trigger seen), and no real keyboard was pressed',
    after.st.input && typeof after.st.input.trig === 'boolean', JSON.stringify(after.st.input));

  /* ---- 6. the scripted reference operator, watched in-session ---------- */
  const tOp = Date.now();
  await ev(() => window.__xrMock.button('right', 4, true)); await waitFrames(3); await ev(() => window.__xrMock.button('right', 4, false));
  let opDone = null;
  try {
    await page.waitForFunction(() => { const s = window.__tc3dSim.state(); return s && s.result; }, null, { timeout: T(50000), polling: 250 });
    opDone = await ev(() => window.__tc3dSim.state());
  } catch { opDone = null; }
  const opDiag = await ev(() => ({ st: window.__tc3dSim.state(), hint: document.getElementById('hint').textContent.slice(0, 90), gau: Object.fromEntries(Object.entries(window.__tc3d().gau || {}).map(([k, v]) => [k, v.txt ?? v.v])) }));
  measured.operatorSeconds = +((Date.now() - tOp) / 1000).toFixed(1);
  ck('the A button started the scripted reference operator in-session and it drove the same seat to a pass (SCRIPTED, recorded as the operator\'s run, not the learner\'s)',
    opDone && opDone.sim === SEAT && opDone.result && opDone.result.passed === true && opDone.level === 'optimal',
    JSON.stringify(opDone ? { l: opDone.level, r: opDone.result && opDone.result.passed, s: opDone.step } : opDiag));

  /* ---- 7. leave the seat from the B button: the hall, walked in-session */
  await ev(() => window.__xrMock.button('right', 5, true)); await waitFrames(3); await ev(() => window.__xrMock.button('right', 5, false));
  let inHall = false;
  try { await page.waitForFunction(() => window.__tc3d().view === 'hall' && window.__tc3dXR.state().walk, null, { timeout: T(20000) }); inHall = true; } catch { /* named below */ }
  await waitFrames(10, T(15000));
  const hall = await ev(() => { const s = window.__tc3d(); return { view: s.view, sim: s.sim, pres: window.__tc3dXR.presenting(), walk: window.__tc3dXR.state().walk,
    lights: s.env ? s.env.roomLights : null, lux: s.env ? s.env.luxI : null, rig: window.__tc3dXR.state().rig, yaw: window.__tc3dXR.state().rigYaw }; });
  ck('the B button left the seat for its hall without leaving the session: the hall is built from its section 24 package (room luminaires lit by the registry\'s lux) and the rig walks it',
    inHall && hall.sim === null && hall.pres && hall.walk && hall.lights > 0 && hall.lux && hall.lux.max >= hall.lux.min,
    JSON.stringify(hall));
  // a thumbstick pushed forward walks the rig; the right stick snap-turns it 30 degrees
  const r0 = hall.rig, y0 = hall.yaw;
  await ev(() => window.__xrMock.stick('left', 0, -1)); await waitFrames(15, T(15000)); await ev(() => window.__xrMock.stick('left', 0, 0));
  await ev(() => window.__xrMock.stick('right', 1, 0)); await waitFrames(4); await ev(() => window.__xrMock.stick('right', 0, 0)); await waitFrames(4);
  const walked = await ev(() => ({ rig: window.__tc3dXR.state().rig, yaw: window.__tc3dXR.state().rigYaw }));
  const moved = Math.hypot(walked.rig[0] - r0[0], walked.rig[2] - r0[2]);
  ck('in the hall the left stick moves the rig and one push of the right stick snap-turns it exactly 30 degrees',
    moved > .2 && Math.abs(Math.abs(walked.yaw - y0) - Math.PI / 6) < .01, `moved=${moved.toFixed(2)} m yawDelta=${(walked.yaw - y0).toFixed(3)}`);

  }   // has('play')
  /* ---- 8. end the session (the B button in the hall) and check the non-XR view is back */
  const fBeforeEnd = await frames();
  await ev(() => window.__xrMock.button('right', 5, true)); await waitFrames(2, 4000); await ev(() => window.__xrMock.button('right', 5, false));
  let ended = false;
  try { await page.waitForFunction(() => !window.__tc3dXR.presenting(), null, { timeout: T(10000) }); ended = true; } catch { /* named below */ }
  const m5 = await mock();
  const pr0 = await ev(() => window.__pageRaf);
  let rafBack = true;
  try { await page.waitForFunction((n) => window.__pageRaf >= n + 5, pr0, { timeout: T(20000), polling: 100 }); } catch { rafBack = false; }
  const pr1 = await ev(() => window.__pageRaf), m6 = await mock();
  const back = await ev(() => { const s = window.__tc3dXR.state(), c = document.querySelector('#main canvas');
    return { pres: window.__tc3dXR.presenting(), mode: s.mode, walk: s.walk, rig: s.rig, yaw: s.rigYaw, alpha: s.clearAlpha, shadows: s.shadows,
      hudSprites: s.hud.sprites.length, canvas: [c.width, c.height], hint: document.getElementById('hint').textContent,
      view: window.__tc3d().view, cam: window.__tc3d().xr }; });
  ck('the session ended through its end event: the page and three.js both saw it (isPresenting false, mode cleared)', ended && back.mode === null && m5.endEvents === 1 && m5.sessionsEnded === 1, JSON.stringify({ ended, mode: back.mode, ev: m5.endEvents }));
  ck('after the session the XR frames stop and the page\'s own animation loop is back (page rAF resumes, session frames frozen)',
    m6.framesDelivered === m5.framesDelivered && rafBack, `session frames ${m5.framesDelivered}->${m6.framesDelivered} pageRaf +${pr1 - pr0}`);
  ck('the non-XR view is restored: rig back at the identity, wrist panel emptied, clear alpha 1, canvas back to its pre-session size, the hall view still the hall',
    back.rig.every((v) => v === 0) && back.yaw === 0 && back.hudSprites === 0 && back.alpha === 1 && back.canvas[0] === preCanvas[0] && back.canvas[1] === preCanvas[1] && back.view === 'hall' && back.walk === false,
    JSON.stringify(back));
  ck('the hint line says the session ended (not the in-session banner)', back.hint && back.hint.length > 0 && !/·/.test(back.hint.slice(0, 12)) && back.hint !== after.st.hud.texts.hint, back.hint);
  measured.sessionFrames = m6.framesDelivered;
  const gaps = m6.gaps;
  measured.gapMs = { median: +median(gaps).toFixed(1), p95: +pct(gaps, .95).toFixed(1), max: +Math.max(...gaps).toFixed(1), n: gaps.length };

  /* ---- 9. a second session starts after the first ended ---------------- */
  await ev(() => document.getElementById('vrBtn').click());
  let again = false;
  try { await page.waitForFunction(() => window.__tc3dXR.presenting(), null, { timeout: T(30000) }); again = true; } catch { /* named below */ }
  await waitFrames(8, T(15000));
  const m7 = await mock();
  await ev(() => window.__tc3dXR.end());
  let endedAgain = false;
  try { await page.waitForFunction(() => !window.__tc3dXR.presenting(), null, { timeout: T(10000) }); endedAgain = true; } catch { /* named below */ }
  const m8 = await mock();
  ck('a second session starts after the first ended and ends through the page\'s own end hook (two sessions, two end events)',
    again && endedAgain && m7.sessionsStarted === 2 && m8.endEvents === 2 && m8.framesDelivered > m6.framesDelivered, `started=${m7.sessionsStarted} ended=${m8.endEvents} frames=${m8.framesDelivered}`);
  ck('no page error or console error was raised through the whole run', errs.length === 0, errs.slice(0, 3).join(' | '));
  measured.loadAfter = load();
  measured.totalFrames = m8.framesDelivered;
  await ctx.close();
  return { checks, measured, errs };
}
