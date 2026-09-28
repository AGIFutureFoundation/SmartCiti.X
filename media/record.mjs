/**
 * House-made b-roll, rendered FRAME BY FRAME from the product's own pages.
 *
 * Software GL cannot hold 24 fps, so nothing here is a screen recording.
 * The page's clock is replaced before it boots: performance.now() and
 * requestAnimationFrame are routed through a virtual clock, and once the
 * scene has settled the clock only moves when this script steps it by
 * exactly 1/fps. Each step places the camera on the shot's path through
 * the page's own hook (__tc3dDo('cam', ...)), runs one frame of the page's
 * own loop, and screenshots it. The result is smooth, exactly-timed motion
 * however slowly each frame renders.
 *
 * The globe map has no camera hook, so its MapLibre instance is caught as
 * it is constructed (a wrapper on maplibregl.Map, installed before the
 * page script runs) and driven with jumpTo(); each frame waits for the
 * map to be idle.
 *
 * Run (from the repo root, against a served git-archive of HEAD):
 *   flock $SP/chromium.lock node media/record.mjs <clip-id> <frames-dir> [from] [to]
 * env MEDIA_BASE = http://127.0.0.1:<port>/  (the served tree)
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { readFileSync, mkdirSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SHOTS = JSON.parse(readFileSync(join(HERE, 'shots.json'), 'utf8'));
const [id, outDir, fromArg, toArg] = process.argv.slice(2);
const BASE = process.env.MEDIA_BASE;
if (!BASE) throw new Error('MEDIA_BASE is not set');
const clip = SHOTS.clips.find((c) => c.id === id);
if (!clip) throw new Error('no such clip: ' + id);
for (const k of ['page', 'setup', 'seconds', 'path']) {
  if (clip[k] === undefined) throw new Error(`clip ${id}: missing field ${k}`);
}
const FPS = SHOTS.fps;
const N = Math.round(clip.seconds * FPS);
const from = fromArg === undefined ? 0 : +fromArg;
const to = toArg === undefined ? N : Math.min(N, +toArg);
mkdirSync(outDir, { recursive: true });

// ease in and out, so every move starts and lands like a real rig
const ease = (t) => t * t * (3 - 2 * t);
const lerp = (a, b, t) => a + (b - a) * t;
const lerp3 = (a, b, t) => a.map((v, i) => lerp(v, b[i], t));

function camAt(i) {
  const t = ease(N <= 1 ? 0 : i / (N - 1));
  const p = clip.path;
  if (p.kind === 'lerp') return { eye: lerp3(p.eye0, p.eye1, t), at: lerp3(p.at0, p.at1, t) };
  if (p.kind === 'orbit') {
    const a = (lerp(p.deg0, p.deg1, t) * Math.PI) / 180;
    const r = lerp(p.r0, p.r1, t);
    const c = p.center;
    return { eye: [c[0] + r * Math.sin(a), lerp(p.h0, p.h1, t), c[2] + r * Math.cos(a)],
             at: c };
  }
  if (p.kind === 'hold') return null;   // the page owns the camera (a running seat)
  if (p.kind === 'globe') {
    return { center: [lerp(p.lng0, p.lng1, t), lerp(p.lat0, p.lat1, t)],
             zoom: lerp(p.zoom0, p.zoom1, t), bearing: lerp(p.bearing0, p.bearing1, t),
             pitch: lerp(p.pitch0, p.pitch1, t) };
  }
  throw new Error(`clip ${id}: unknown path kind ${p.kind}`);
}

// the virtual clock: free-running until __vt.start(), then stepped only
const CLOCK = `(() => {
  const realRaf = window.requestAnimationFrame.bind(window);
  const realNow = performance.now.bind(performance);
  let stepped = false, vt = 0, q = [];
  performance.now = () => (stepped ? vt : realNow());
  window.requestAnimationFrame = (cb) => { if (!stepped) return realRaf(cb); q.push(cb); return q.length; };
  window.__vt = {
    start() { vt = realNow(); stepped = true; },
    step(ms) { vt += ms; const cbs = q; q = []; for (const cb of cbs) cb(vt); return cbs.length; },
  };
  // catch the globe's MapLibre instance as it is made
  let ml;
  Object.defineProperty(window, 'maplibregl', { configurable: true,
    get() { return ml; },
    set(v) { const M = v.Map; v.Map = class extends M { constructor(o) { super(o); window.__mediaMap = this; } }; ml = v; } });
})();`;

const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const ctx = await browser.newContext({ viewport: { width: SHOTS.width, height: SHOTS.height },
  reducedMotion: 'no-preference' });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(e.message.slice(0, 200)));
const isGlobe = clip.path.kind === 'globe';
if (!isGlobe) await page.addInitScript(CLOCK);
else await page.addInitScript(CLOCK.replace('performance.now = ', 'void 0; const _x = '));
const t0 = Date.now();
await page.goto(BASE + clip.page, { waitUntil: 'load' });
if (isGlobe) {
  await page.waitForFunction(() => window.__mediaMap && window.__geomap && window.__geomap().loaded,
    null, { timeout: 60000 });
} else {
  await page.waitForFunction(() => typeof window.__tc3d === 'function' && window.__tc3d().view,
    null, { timeout: 60000 });
}
// only the picture: every piece of page chrome hidden, nothing burned in
await page.addStyleTag({ content: 'body *{visibility:hidden!important;animation:none!important}'
  + ' canvas{visibility:visible!important}' });
// the one picture: any second canvas (the campus minimap) is page chrome too
await page.evaluate(() => {
  const cs = [...document.querySelectorAll('canvas')].sort((a, b) => b.width * b.height - a.width * a.height);
  cs.slice(1).forEach((c) => { c.style.setProperty('visibility', 'hidden', 'important'); });
});
for (const [fn, arg] of clip.setup) {
  if (fn === 'simStart') {
    const [simId, level] = String(arg).split(':');
    await page.evaluate(([s, l]) => window.__tc3dSim.start(s, undefined, { level: l, seed: 1 }), [simId, level]);
  } else await page.evaluate(([f, a]) => window.__tc3dDo(f, a), [fn, arg]);
  await page.waitForTimeout(800);
}
await page.waitForTimeout(isGlobe ? 1500 : 3000);

// signs are sprites drawn in the scene: move them to a layer the camera
// does not render, so no text is burned into the footage
const unsign = () => page.evaluate(() => {
  if (!window.__tc3dScene) return 0;
  let n = 0;
  window.__tc3dScene().traverse((o) => { if (o.isSprite && o.userData.lbl) { o.layers.set(31); n++; } });
  return n;
});
async function place(i) {
  const c = camAt(i);
  if (isGlobe) {
    await page.evaluate((v) => new Promise((res) => {
      const m = window.__mediaMap;
      m.jumpTo(v);
      if (m.loaded() && m.areTilesLoaded()) { requestAnimationFrame(() => requestAnimationFrame(res)); return; }
      const done = setTimeout(res, 4000);
      m.once('idle', () => { clearTimeout(done); res(); });
    }), c);
  } else if (c === null) {
    await page.evaluate((ms) => window.__vt.step(ms), 1000 / FPS);
  } else {
    const arg = c.eye.map((v) => v.toFixed(4)).join(',') + '|' + c.at.map((v) => v.toFixed(4)).join(',');
    await page.evaluate(([a, ms]) => { window.__tc3dDo('cam', a); window.__vt.step(ms); }, [arg, 1000 / FPS]);
  }
}

if (!isGlobe) {
  await page.evaluate(() => window.__vt.start());
  // settle at the first frame's pose: damping, fades and labels come to rest
  for (let k = 0; k < 36; k++) { if (k % 12 === 0) await unsign(); await place(from); }
}
const DEADLINE = t0 + 1000 * +(process.env.MEDIA_DEADLINE ?? 200);
const tf = Date.now();
let wrote = 0;
for (let i = from; i < to; i++) {
  const f = join(outDir, `f${String(i).padStart(4, '0')}.png`);
  if (Date.now() > DEADLINE) { console.log(JSON.stringify({ id, stoppedAt: i })); break; }
  if (!isGlobe && i % 24 === 0) await unsign();
  await place(i);
  if (existsSync(f)) continue;
  await page.screenshot({ path: f, type: 'png' });
  wrote++;
}
const state = await page.evaluate(() => (window.__tc3d ? window.__tc3d().view : 'globe'));
console.log(JSON.stringify({ id, from, to, wrote, frames: N, view: state,
  secs: Math.round((Date.now() - t0) / 1000),
  msPerFrame: wrote ? Math.round((Date.now() - tf) / wrote) : null, errors }));
await browser.close();
if (errors.length) process.exit(2);
