/* The MOCKED-SESSION seat harness: drives the sim seats through ONE mocked
   WebXR session in headless Chromium, over xr/mock_webxr.js, with the
   thumbsticks, grip and trigger of two mocked controllers.

   MOCKED session in headless Chromium. No physical headset, no browser XR
   runtime, no compositor, no tracking. What this measures is the page's
   controller path into each seat under the WebXR interfaces it uses; it says
   nothing about a headset, and nothing about a person's hands.

   One session, many seats. The page is booted into the first seat, the
   session is entered once through the page's own Enter VR button, and each
   further seat is started in-session through the page's start hook
   (window.__tc3dSim.start - the call a hall station makes). Per seat:

     1. KEY STATE. The thumbsticks and the grip are pushed in the two
        directions the seat's registry controls name, and the page's own `keys`
        must show exactly those verbs held, then released; at least one gauge
        must move while they are held; the trigger must reach the page.
     2. COMPLETION. A SCRIPTED coach (the page's reference policy, returned
        by window.__tc3dCoach, never attached as the operator's run) writes
        what it would press onto the mocked controllers frame by frame, and
        the seat must reach its own result panel: the seat's registry name and
        every rubric axis of the registry, with a verdict. The run is made by
        the controllers; the policy behind the sticks is SCRIPTED, not a person.

   Every expectation is read from sims/registry/sims.json; no key, axis name
   or seat title is typed here. judgeSeat() is pure (an observation in, checks
   out) so the static half of the suite can mutate it without a browser. */
import { readFileSync } from 'node:fs';

const SIMS = JSON.parse(readFileSync(new URL('../sims/registry/sims.json', import.meta.url), 'utf8'));
export const SEAT_IDS = Object.keys(SIMS.sims);
export const seatDef = (id) => SIMS.sims[id];
export const firstScenario = (id) => SIMS.sims[id].scenarios[0].id;

const STICK_KEYS = ['W', 'A', 'S', 'D', 'Q', 'E'];
export const CODE = (k) => 'Key' + k;

/* the verbs a seat's registry controls name: letters split on "/", Space apart */
export function seatVerbs(def) {
  const toks = [];
  for (const c of def.controls) for (const k of c.keys.split('/').map((x) => x.trim())) toks.push(k);
  const stick = STICK_KEYS.filter((k) => toks.includes(k));
  const grip = def.xr.grip_key ? def.xr.grip_key.replace(/^Key/, '') : null;
  return { toks, stick, grip, space: toks.includes('Space'), codes: [...stick, ...(grip ? [grip] : [])].map(CODE) };
}

/* the two sweeps: left stick x/y and right stick x pushed one way, then the other */
export const SWEEPS = [
  { label: 'A, W, Q and the grip', keys: ['A', 'W', 'Q'], pad: { lx: -1, ly: -1, rx: -1 }, grip: true },
  { label: 'D, S, E', keys: ['D', 'S', 'E'], pad: { lx: 1, ly: 1, rx: 1 }, grip: false },
];
/* what a sweep must hold for a seat: only the verbs its registry controls name */
export function sweepWant(def, sw) {
  const v = seatVerbs(def);
  const want = sw.keys.filter((k) => v.stick.includes(k)).map(CODE);
  if (sw.grip && v.grip) want.push(CODE(v.grip));
  return want;
}

/* the keys the coach may press: stick verbs the seat names, and the grip key when the seat has one */
export function coachAllowed(def) { return seatVerbs(def).codes; }

/* a seat order that keeps neighbours in one hall, so the in-session start rarely rebuilds a hall */
export function hallOrder(ids) {
  const out = []; let hall = null;
  const left = [...ids];
  while (left.length) {
    const count = {};
    for (const id of left) for (const h of SIMS.sims[id].halls) count[h] = (count[h] || 0) + 1;
    const best = hall && left.some((id) => SIMS.sims[id].halls.includes(hall)) ? hall
      : Object.entries(count).sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0][0];
    hall = best;
    for (let i = 0; i < left.length;) { if (SIMS.sims[left[i]].halls.includes(best)) out.push(...left.splice(i, 1)); else i++; }
  }
  return out;
}

/* the hall the page is booted into: one of the first seat's halls, the one that also teaches the most
   seats of the batch, so the in-session start of the later seats does not rebuild a hall (a hall rebuild
   was measured at 15 s to 52 s in the mocked session at load 4 to 6) */
export function bootHall(ids) {
  const halls = SIMS.sims[ids[0]].halls;
  let best = halls[0], bestN = -1;
  for (const h of halls) { const n = ids.filter((i) => SIMS.sims[i].halls.includes(h)).length; if (n > bestN) { best = h; bestN = n; } }
  return best;
}

/* the classification the report prints */
export function levelOf(def, obs) {
  if (!obs || obs.skipped) return 'not run';
  const p = obs.panel;
  const keysOk = (obs.sweeps || []).length === SWEEPS.length && obs.sweeps.every((s) => s.heldOk && s.releasedOk);
  if (p && p.title === def.name) return /Passed/.test(p.chip || '') ? 'completion (pass)' : 'completion (retry verdict)';
  return keysOk ? 'key state only' : 'failed';
}

/* ---- the pure judge: an observation in, named checks out ---------------- */
export function judgeSeat(id, obs, expect = 'completion') {
  const def = SIMS.sims[id], out = [];
  const c = (what, ok, detail = '') => out.push({ name: `${id}: ${what}`, ok: !!ok, detail: String(detail) });
  const v = seatVerbs(def);
  if (!obs || obs.skipped) {
    c('the seat got its time slot in this batch (a batch that leaves a seat unrun is too big)', false, obs ? obs.skipped : 'no observation');
    return out;
  }
  if (obs.error) c('the seat ran without a harness error', false, obs.error);
  c(`the page started the seat in the open session, opening scenario ${firstScenario(id)}, and drew its gauges`,
    obs.started && obs.started.sim === id && obs.started.scenario === firstScenario(id) && obs.gauges0 && Object.keys(obs.gauges0).length >= 1,
    JSON.stringify(obs.started) + ' gauges=' + (obs.gauges0 ? Object.keys(obs.gauges0).join(',') : 'none'));
  for (const sw of SWEEPS) {
    const want = sweepWant(def, sw), s = (obs.sweeps || []).find((x) => x.label === sw.label);
    if (!want.length) { c(`no verb of the registry controls sits on the sweep ${sw.label}`, !s || !s.got.length, ''); continue; }
    c(`pushing the sticks${sw.grip && v.grip ? ' and holding the grip' : ''} for ${want.map((k) => k.replace('Key', '')).join(', ')} puts exactly those verbs in the page's keys, and releasing lifts them`,
      s && JSON.stringify([...s.got].sort()) === JSON.stringify([...want].sort()) && s.heldOk && s.releasedOk && s.after.length === 0,
      s ? JSON.stringify({ want, got: s.got, after: s.after }) : 'sweep not run');
  }
  /* each sweep is compared with the reading taken just before it: a seat whose verbs cancel when pressed
     together (the scaffold bay steps its rack on A and jumps it on R, in one frame) answers the other sweep */
  const moved = (obs.sweeps || []).filter((x) => x.gBefore && x.gHeld && JSON.stringify(x.gBefore) !== JSON.stringify(x.gHeld));
  c('at least one gauge reading moved while the controllers held the seat\'s verbs (the seat answers the sticks)',
    moved.length >= 1, JSON.stringify((obs.sweeps || []).map((x) => ({ s: x.label, a: x.gBefore, b: x.gHeld }))).slice(0, 420));
  c('the right trigger reached three.js as a select and the page read it as pressed', obs.trigger && obs.trigger.selects >= 1 && obs.trigger.pagePressed === true, JSON.stringify(obs.trigger));
  if (expect === 'completion') {
    const rub = def.rubric.map((r) => r.axis), p = obs.panel;
    c('the controllers drove the seat to its result panel inside the time cap (the seat\'s own completion signal)',
      p && p.title === def.name && p.open === true,
      p ? `panel "${p.title}"` : `no panel; coach ${JSON.stringify(obs.coach)}`);
    c(`the result panel carries every rubric axis of the registry (${rub.join(', ')})`,
      p && rub.every((a) => p.rows.some((r) => r.axis === a)), p ? p.rows.map((r) => r.axis).join(',') : 'no panel');
    c('the verdict is Passed and no graded axis is marked failed',
      p && /Passed/.test(p.chip || '') && p.rows.every((r) => r.ok !== '✗'),
      p ? `${p.chip} ${p.rows.map((r) => r.axis + ':' + r.value + r.ok).join(' ')}` : 'no panel');
    c('the run is the controllers\' own: no scripted-operator run was attached and the panel carries no scripted-reference chip',
      p && p.scripted === false && obs.opAttached === false, JSON.stringify({ scripted: p && p.scripted, opAttached: obs.opAttached }));
  }
  const allowed = coachAllowed(def), stray = (obs.coach && obs.coach.keysUsed || []).filter((k) => !allowed.includes(k));
  c('every key the coach pressed is a verb this seat\'s registry controls name (sticks) or its registry grip key',
    obs.coach && obs.coach.began !== false && stray.length === 0, JSON.stringify({ used: obs.coach && obs.coach.keysUsed, allowed, stray }));
  return out;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function runSeats({ browser, base, mockSrc, seats, budgetMs = 80000, coachMs = 22000, coachMsOf = () => coachMs, probe = false, probeSeats = null, expectOf = () => 'completion', onCheck = null, cfg = {}, sink = {} }) {
  const checks = [], measured = { seats: {}, probe: {} };
  sink.measured = measured;                         // a caller that gives up on a late run still reads the partial measurements
  const deadline = Date.now() + budgetMs;
  const ck = (name, ok, detail = '') => { const k = { name, ok: !!ok, detail: String(detail), atMs: Date.now() - (deadline - budgetMs) }; checks.push(k); if (onCheck) onCheck(k); };
  const left = () => deadline - Date.now();
  const Tc = (ms) => Math.max(500, Math.min(ms, left() - 1500));
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|favicon/.test(m.text())) errs.push('console: ' + m.text().slice(0, 160)); });
  await page.addInitScript({ content: 'window.__xrMockCfg = ' + JSON.stringify(cfg) + ';\n' + mockSrc });
  const ev = (fn, arg) => page.evaluate(fn, arg);
  const frames = () => page.evaluate(() => window.__xrMock.stats.framesDelivered);
  const waitFrames = async (n, ms = 6000) => {
    ms = Tc(ms);
    const f0 = await frames();
    try { await page.waitForFunction((t) => window.__xrMock.stats.framesDelivered >= t, f0 + n, { timeout: ms, polling: 20 }); return true; } catch { return false; }
  };
  const load = () => readFileSync('/proc/loadavg', 'utf8').split(' ').slice(0, 3).join(' ');
  measured.loadBefore = load();
  const fin = async () => { measured.loadAfter = load(); measured.errs = errs; await ctx.close().catch(() => {}); return { checks, measured, errs }; };

  /* ---- boot into the first seat, with the mock in place ---------------- */
  const first = seats[0], fdef = seatDef(first);
  const t0 = Date.now();
  await page.goto(`${base}/web/trade_craft_3d.html?hall=${bootHall(seats)}&sim=${first}&scenario=${firstScenario(first)}`, { waitUntil: 'load' });
  let booted = true;
  try {
    await page.waitForFunction(() => window.__tc3d && window.__tc3dXR && window.__tc3dSim && window.__tc3dCoach, null, { timeout: Tc(60000) });
    await page.waitForFunction(() => window.__tc3d().sim, null, { timeout: Tc(20000) });
  } catch { booted = false; }
  measured.bootMs = Date.now() - t0;
  ck('the page booted with the mock in place, opened the first seat and exposes the coach hook', booted && (await ev(() => window.__tc3d().sim)) === first, `first=${first} sim=${booted ? await ev(() => window.__tc3d().sim) : 'no boot'}`);
  if (!booted) return fin();

  /* ---- optional probe: how long each seat's reference run takes in simulated seconds --- */
  if (probe) {
    for (const id of (probeSeats || seats)) {
      if (left() < 40000) { measured.probe[id] = { skipped: true }; continue; }
      const t = Date.now();
      try {
        const r = await ev(([i, sc]) => { const o = window.__tc3dSim.run(i, sc, { level: 'optimal', dt: 1 / 30, maxSec: 400 }); return { steps: o.steps, dt: o.dt, passed: o.passed, timedOut: o.timedOut }; }, [id, firstScenario(id)]);
        measured.probe[id] = { simSec: +(r.steps * r.dt).toFixed(1), passed: r.passed, timedOut: r.timedOut, wallMs: Date.now() - t };
      } catch (e) { measured.probe[id] = { error: String(e.message || e).slice(0, 120) }; }
    }
    // the probe tears the first seat down; the loop below starts every seat afresh
  }

  /* ---- enter VR once, through the page's own button -------------------- */
  let vrShown = false;
  try { await page.waitForFunction(() => document.getElementById('vrBtn').style.display !== 'none', null, { timeout: Tc(15000) }); vrShown = true; } catch { /* named */ }
  ck('the page offered Enter VR (the mock answered immersive-vr)', vrShown);
  if (!vrShown) return fin();
  const tEnter = Date.now();
  await page.click('#vrBtn');
  let presenting = false;
  try { await page.waitForFunction(() => window.__tc3dXR.presenting(), null, { timeout: Tc(30000) }); presenting = true; } catch { /* named */ }
  measured.enterMs = Date.now() - tEnter;
  await waitFrames(6, 15000);
  const m2 = await ev(() => window.__xrMock.snapshot()), st = await ev(() => window.__tc3dXR.state());
  ck('Enter VR started one immersive-vr session (local-floor required) with both controllers connected', presenting && m2.sessionsStarted === 1 && m2.requests[0] && m2.requests[0].required.includes('local-floor') && Object.values(st.hands).sort().join() === 'left,right',
    JSON.stringify({ presenting, started: m2.sessionsStarted, hands: st.hands }));
  if (!presenting) return fin();

  /* the per-frame driver: while it is on, the coach's next inputs are written onto the controllers
     in the frame the page is handed (the mock calls beforeFrame just before delivering it) */
  await ev(() => {
    const d = window.__seatDrv = { on: false, grip: null, n: 0, prevAct: false, used: {}, phase: null, acts: 0, last: 0, maxGap: 0, slow: 0 };
    const m = window.__xrMock;
    m.beforeFrame = () => {
      if (!d.on) { d.last = 0; return; }
      const now = performance.now(); if (d.last) { const gp = now - d.last; if (gp > d.maxGap) d.maxGap = gp; if (gp > 250) d.slow++; } d.last = now;   // the frame gaps the coach was driven through
      const r = window.__tc3dCoach.next(); if (!r) return;
      const has = (k) => r.keys.includes(k);
      m.stick('left', (has('KeyD') ? 1 : 0) - (has('KeyA') ? 1 : 0), (has('KeyS') ? 1 : 0) - (has('KeyW') ? 1 : 0));
      m.stick('right', (has('KeyE') ? 1 : 0) - (has('KeyQ') ? 1 : 0), 0);
      m.button('right', 1, !!(d.grip && has(d.grip)));
      const press = r.act && !d.prevAct; d.prevAct = press; if (press) d.acts++;
      m.button('right', 0, press);
      for (const k of r.keys) d.used[k] = (d.used[k] || 0) + 1;
      d.phase = r.phase; d.n++;
    };
  });
  const releaseAll = () => ev(() => { const m = window.__xrMock; m.stick('left', 0, 0); m.stick('right', 0, 0); m.button('right', 1, false); m.button('right', 0, false); });

  const keysNow = (codes) => ev((cs) => cs.map((c) => !!window.__tc3dSim.keys[c]), codes);
  // the seat's raw gauges (what its physics holds), not the dash's rounded text: a slow drive moves the raw number first
  const gau = () => ev(() => { const g = window.__tc3dSim.gauges(); return g ? JSON.parse(JSON.stringify(g, (k, v) => (typeof v === 'number' ? Math.round(v * 1000) / 1000 : v))) : null; });
  const startSeat = async (id) => {
    const sc = firstScenario(id), t = Date.now();
    await ev(([i, s]) => window.__tc3dSim.start(i, s), [id, sc]);
    try { await page.waitForFunction((i) => window.__tc3d().sim === i && window.__tc3d().gau, id, { timeout: Tc(15000), polling: 50 }); } catch { /* judged */ }
    await waitFrames(3, 8000);
    return { sim: await ev(() => window.__tc3d().sim), scenario: await ev(() => window.__tc3d().scenario ?? null), ms: Date.now() - t };
  };

  /* ---- the seats ---------------------------------------------------------- */
  const fpsOf = async (n0, t0s) => { const n1 = await frames(); return +(((n1 - n0) / ((Date.now() - t0s) / 1000)) || 0).toFixed(1); };
  for (const id of seats) {
    const def = seatDef(id), v = seatVerbs(def), obs = { seat: id, sweeps: [], coach: { keysUsed: [] }, opAttached: null };
    if (left() < 9000) { obs.skipped = `only ${Math.round(left() / 1000)} s left when this seat was due`; measured.seats[id] = obs; for (const k of judgeSeat(id, obs, expectOf(id))) ck(k.name, k.ok, k.detail); continue; }
    const tSeat = Date.now(), f0 = await frames();
    try {
      const s0 = await startSeat(id);
      obs.started = { sim: s0.sim, scenario: s0.scenario }; obs.startMs = s0.ms;
      obs.gauges0 = await gau();
      /* 1. key state */
      for (const sw of SWEEPS) {
        const want = sweepWant(def, sw), entry = { label: sw.label, want, got: [], heldOk: false, releasedOk: false, after: [] };
        obs.sweeps.push(entry);
        entry.gBefore = await gau();
        if (!want.length) { entry.heldOk = entry.releasedOk = true; continue; }
        const hasX = sw.keys.some((k) => ['A', 'D'].includes(k) && v.stick.includes(k)), hasY = sw.keys.some((k) => ['W', 'S'].includes(k) && v.stick.includes(k)),
          hasR = sw.keys.some((k) => ['Q', 'E'].includes(k) && v.stick.includes(k));
        await ev(([lx, ly, rx, grip]) => { const m = window.__xrMock; m.stick('left', lx, ly); m.stick('right', rx, 0); m.button('right', 1, grip); },
          [hasX ? sw.pad.lx : 0, hasY ? sw.pad.ly : 0, hasR ? sw.pad.rx : 0, !!(sw.grip && v.grip)]);
        await waitFrames(3, 5000);
        const all = v.codes;
        const held = await keysNow(all);
        entry.got = all.filter((_, i) => held[i]);
        entry.heldOk = want.every((k) => entry.got.includes(k));
        await waitFrames(3, 5000);                       // let the drive spool up before the gauges are compared
        entry.gHeld = await gau();                       // this sweep's reading while its verbs are held, compared with its OWN baseline
        entry.moved = JSON.stringify(entry.gBefore) !== JSON.stringify(entry.gHeld);
        await releaseAll();
        await waitFrames(2, 4000);
        const rel = await keysNow(all);
        entry.after = all.filter((_, i) => rel[i]);
        entry.releasedOk = entry.after.length === 0;
      }
      const mv = obs.sweeps.find((x) => x.moved) || obs.sweeps.find((x) => x.gHeld);
      obs.gauges1 = mv ? mv.gHeld : await gau();
      obs.gaugesMoved = obs.sweeps.some((x) => x.moved);
      /* the trigger: a press and a release is one select on the controller three.js built */
      const s0m = await ev(() => window.__xrMock.stats.select);
      await ev(() => window.__xrMock.button('right', 0, true));
      await waitFrames(2, 4000);
      const pagePressed = await ev(() => !!(window.__tc3dXR.state().input && window.__tc3dXR.state().input.trig));
      await ev(() => window.__xrMock.button('right', 0, false));
      await waitFrames(2, 4000);
      obs.trigger = { selects: (await ev(() => window.__xrMock.stats.select)) - s0m, pagePressed };
      /* 2. completion: restart the seat clean, then let the coach write the controllers */
      if (expectOf(id) === 'completion' || coachMsOf(id) > 0) {
        const s1 = await startSeat(id);
        const began = await ev(([g]) => { const d = window.__seatDrv; d.used = {}; d.n = 0; d.acts = 0; d.prevAct = false; d.grip = g; d.phase = null; d.last = 0; d.maxGap = 0; d.slow = 0; return window.__tc3dCoach.begin('optimal', 1); }, [v.grip ? CODE(v.grip) : null]);
        obs.coach.began = !!began; obs.coach.phases = began && began.phases;
        const nF = await frames(), tC = Date.now();
        await ev(() => { window.__seatDrv.on = true; });
        const cap = Tc(Math.min(coachMsOf(id), left() - 3500));
        try { await page.waitForFunction(() => window.__tc3dCoach.done(), null, { timeout: cap, polling: 150 }); } catch { /* panel judged below */ }
        obs.coach.secs = +((Date.now() - tC) / 1000).toFixed(1);
        obs.coach.fps = await fpsOf(nF, tC);
        await ev(() => { window.__seatDrv.on = false; });
        await releaseAll();
        const info = await ev(() => {
          const pb = document.getElementById('pbody'), h = pb.querySelector('h2'), chip = pb.querySelector('.chip');
          const rows = [...pb.querySelectorAll('tbody tr')].map((tr) => { const td = tr.querySelectorAll('td'); return { axis: td[0].textContent.trim(), value: td[1].textContent.trim(), ok: td[2].textContent.trim() }; });
          return { coach: window.__tc3dCoach.state(), drv: { n: window.__seatDrv.n, acts: window.__seatDrv.acts, used: window.__seatDrv.used, phase: window.__seatDrv.phase, maxGap: Math.round(window.__seatDrv.maxGap), slow: window.__seatDrv.slow },
            panel: h ? { title: h.textContent, chip: chip && chip.textContent.trim(), rows, open: document.body.classList.contains('open'), scripted: /scripted reference/.test(pb.textContent) } : null,
            op: window.__tc3dSim.state(), stepGau: window.__tc3d().gau ? Object.fromEntries(Object.entries(window.__tc3d().gau).map(([k, x]) => [k, x.txt ?? x.v])) : null };
        });
        obs.panel = info.panel; obs.opAttached = info.op !== null;
        /* a seat that ended on a retry verdict: is that the controller path, or the reference policy at this frame
           rate? The same policy is run headless at the frame time the session actually delivered, and at 1/60 s.
           Diagnostic only - it is reported next to the verdict and never changes it. */
        if (info.panel && !/Passed/.test(info.panel.chip || '') && left() > 6000) {
          const dtc = obs.coach.fps > 0 ? 1 / obs.coach.fps : 0.09;
          try {
            obs.dtDiag = await ev(([i, sc, d]) => { const f = (dt) => { const o = window.__tc3dSim.run(i, sc, { level: 'optimal', dt, maxSec: 200 }); return { dt: +dt.toFixed(3), passed: !!o.passed, timedOut: !!o.timedOut }; }; return { atSessionDt: f(d), at60: f(1 / 60) }; }, [id, firstScenario(id), dtc]);
          } catch (e) { obs.dtDiag = { error: String(e.message || e).slice(0, 100) }; }
        }
        obs.coach.state = info.coach; obs.coach.steps = info.drv.n; obs.coach.maxGapMs = info.drv.maxGap; obs.coach.slowFrames = info.drv.slow; obs.coach.acts = info.drv.acts; obs.coach.keysUsed = Object.keys(info.drv.used); obs.coach.stepGau = info.stepGau;
        obs.startMs2 = s1.ms;
      }
      await ev(() => window.__tc3dCoach.end());
    } catch (e) { obs.error = String(e && e.message || e).slice(0, 200); await ev(() => { window.__seatDrv.on = false; }).catch(() => {}); await releaseAll().catch(() => {}); }
    obs.seatSecs = +((Date.now() - tSeat) / 1000).toFixed(1);
    obs.level = levelOf(def, obs);
    measured.seats[id] = obs;
    for (const k of judgeSeat(id, obs, expectOf(id))) ck(k.name, k.ok, k.detail);
  }

  /* ---- end the session --------------------------------------------------- */
  await ev(() => window.__tc3dXR.end());
  let ended = false;
  try { await page.waitForFunction(() => !window.__tc3dXR.presenting(), null, { timeout: Tc(8000) }); ended = true; } catch { /* named */ }
  const m9 = await ev(() => window.__xrMock.snapshot());
  ck('the session ended through its end event after the last seat, and the page saw it', ended && m9.endEvents === 1 && m9.sessionsEnded === 1, JSON.stringify({ ended, ev: m9.endEvents }));
  ck('no page error or console error was raised through the whole run', errs.length === 0, errs.slice(0, 3).join(' | '));
  measured.totalFrames = m9.framesDelivered;
  return fin();
}
