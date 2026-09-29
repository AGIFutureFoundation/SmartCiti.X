/**
 * web/tqkit.py - TradesQuest field-job stations for the SmartCiti.X Holodeck (plain three.js). Node only:
 * builds every station with the page's vendored three.js and checks sizes, draw-call cap, provenance,
 * hall ids against unions/registry/unions.json, the step flow, fail-closed options, the DOM panel (with a
 * tiny fake document), dispose, panel contrast in both palettes, and the 8-locale strings.
 *
 *   node web/test_tqkit.mjs [--root=/copy] [--strings=<{loc:{key:value}} json, before the locale merge>]
 *                           [--tq=/path/to/game-world-focus clone, to prove each provenance path at 3ea15f0]
 */
import { readFileSync, writeFileSync, existsSync, mkdtempSync, rmSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';

const HERE = dirname(fileURLToPath(import.meta.url));
const arg = (k) => { const h = process.argv.slice(2).find((a) => a.startsWith(`--${k}=`)); return h ? h.slice(k.length + 3) : null; };
const ROOT = resolve(arg('root') || join(HERE, '..'));
let n = 0, bad = 0;
const ok = (m, c, ev = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++; console.log('FAIL  ' + m); for (const e of ev.slice(0, 6)) console.log('      ' + e);
};
const throwsLike = (fn, re) => { try { fn(); return false; } catch (e) { return re.test(String(e.message)); } };

// the module, written out and imported; three from the page's own vendored copy
const py = (code) => execFileSync('python3', ['-B', '-c', 'import sys, json; sys.path.insert(0, sys.argv[1]); import tqkit; ' + code, join(ROOT, 'web')]).toString();
const tmp = mkdtempSync(join(tmpdir(), 'tqkit-'));
const modPath = join(tmp, 'tqkit.mjs');
writeFileSync(modPath, py('sys.stdout.write(tqkit.TQKIT_JS)'));
const K = await import(pathToFileURL(modPath).href);
const THREE = await import(pathToFileURL(join(ROOT, 'web/vendor/three.module.min.js')).href);
const PY = JSON.parse(py('sys.stdout.write(json.dumps({"kinds": tqkit.TQKIT_KINDS, "halls": tqkit.TQKIT_HALLS, "keys": tqkit.TQKIT_I18N_KEYS, "css": tqkit.TQKIT_CSS, "inline": tqkit.tqkit_inline(), "js": tqkit.TQKIT_JS}))'));
rmSync(tmp, { recursive: true, force: true });

// ---- module shape
ok('the module exports createTQStation, tqPanelModel, TQ_KINDS, TQ_HALLS, TQ_KEYS, TQ_PROVENANCE',
  ['createTQStation', 'tqPanelModel', 'TQ_KINDS', 'TQ_HALLS', 'TQ_KEYS', 'TQ_PROVENANCE'].every((k) => k in K));
ok('the kinds are exactly electrical, plumbing, hvac, carpentry, the same on both sides',
  JSON.stringify(Object.keys(K.TQ_KINDS)) === JSON.stringify(['electrical', 'plumbing', 'hvac', 'carpentry'])
  && JSON.stringify(PY.kinds) === JSON.stringify(Object.keys(K.TQ_KINDS)) && JSON.stringify(PY.halls) === JSON.stringify(K.TQ_HALLS));
const inl = PY.inline;
ok('tqkit_inline() is the body between one TQ_KIT:BEGIN and one TQ_KIT:END, with no export line',
  inl.startsWith('/* TQ_KIT:BEGIN') && inl.endsWith('/* TQ_KIT:END */') && inl.split('TQ_KIT:BEGIN').length === 2 && !/^export /m.test(inl));
const tops = [...inl.matchAll(/^(?:const|let|function) (\w+)/gm)].map((m) => m[1]);
ok('every top-level name starts with tq/TQ (or is createTQStation), so it pastes into a page module',
  tops.length > 5 && tops.every((t) => /^(tq|TQ)/.test(t) || t === 'createTQStation'), tops.filter((t) => !/^(tq|TQ)/.test(t) && t !== 'createTQStation'));
ok('the kit writes no markup from strings (no innerHTML / insertAdjacentHTML / outerHTML)', !/innerHTML|insertAdjacentHTML|outerHTML/.test(PY.js));
ok('the kit never falls back on a default for registry or string data (no `??`)', !/\?\?/.test(PY.js));

// ---- hall ids against the unions registry
const unions = JSON.parse(readFileSync(join(ROOT, 'unions/registry/unions.json'), 'utf8')).unions;
const slugs = new Set(unions.map((u) => u.slug));
const allIds = Object.values(K.TQ_HALLS).flatMap((h) => [...h.primary, ...h.related]);
ok('every hall id in TQ_HALLS is a union slug in unions/registry/unions.json', allIds.length > 0 && allIds.every((s) => slugs.has(s)), allIds.filter((s) => !slugs.has(s)));
ok('every kind has at least one primary hall and no hall id appears under two kinds or twice',
  Object.values(K.TQ_HALLS).every((h) => h.primary.length >= 1) && new Set(allIds).size === allIds.length);
const want = { electrical: 'electricians', plumbing: 'pipefitters', hvac: 'hvacr', carpentry: 'carpenters' };
ok('the primary halls are the matching trades: electricians, pipefitters (plumbers), hvacr + sheetmetal, carpenters',
  Object.entries(want).every(([k, s]) => K.TQ_HALLS[k].primary.includes(s)) && K.TQ_HALLS.hvac.primary.includes('sheetmetal'));

// ---- strings (8 locales)
const LOCS = ['en', 'es', 'fr', 'de', 'pt', 'zh', 'hi', 'ar'];
const sfile = arg('strings');
const STR = {};
for (const l of LOCS) STR[l] = sfile ? JSON.parse(readFileSync(sfile, 'utf8'))[l] : JSON.parse(readFileSync(join(ROOT, `i18n/locales/${l}.json`), 'utf8')).strings;
ok(`the kit's key list is the Python TQKIT_I18N_KEYS (${PY.keys.length} keys, all under tqkit.)`,
  JSON.stringify(PY.keys) === JSON.stringify(K.TQ_KEYS) && K.TQ_KEYS.every((k) => k.startsWith('tqkit.')));
const missing = LOCS.flatMap((l) => K.TQ_KEYS.filter((k) => !(STR[l] && typeof STR[l][k] === 'string' && STR[l][k].trim())).map((k) => `${l}:${k}`));
ok(`all 8 locales carry every tqkit key${sfile ? ' (from --strings)' : ''}`, missing.length === 0, missing);
const copies = LOCS.slice(1).flatMap((l) => K.TQ_KEYS.filter((k) => STR[l] && STR.en && STR[l][k] === STR.en[k]).map((k) => `${l}:${k}`));
ok('no non-English value is a copy of the English one', missing.length === 0 && copies.length === 0, copies);
ok('the step string keeps {n} and {total} in every locale; the AUTHORED label keeps the word AUTHORED',
  missing.length === 0 && LOCS.every((l) => STR[l]['tqkit.step'].includes('{n}') && STR[l]['tqkit.step'].includes('{total}') && STR[l]['tqkit.authored'].includes('AUTHORED')));
ok('the English note says play only, never a completion record, certifies nothing',
  missing.length === 0 && /play only/i.test(STR.en['tqkit.note']) && /completion record/.test(STR.en['tqkit.note']) && /certifies nothing/.test(STR.en['tqkit.note']));
const S = missing.length === 0 ? STR.en : Object.fromEntries(K.TQ_KEYS.map((k) => [k, 'x {n} {total}']));

// ---- fake document (enough for the panel)
class El {
  constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.attrs = {}; this.className = ''; this.textContent = ''; this.parentNode = null; this.ls = {}; this.disabled = false; }
  setAttribute(k, v) { this.attrs[k] = String(v); } getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  removeAttribute(k) { delete this.attrs[k]; }
  append(...cs) { for (const c of cs) { c.parentNode = this; this.children.push(c); } }
  removeChild(c) { this.children = this.children.filter((x) => x !== c); c.parentNode = null; }
  addEventListener(t, f) { (this.ls[t] = this.ls[t] || []).push(f); }
  click() { if (!this.disabled) for (const f of this.ls.click || []) f({}); }
  all() { return [this, ...this.children.flatMap((c) => c.all())]; }
}
const doc = { createElement: (t) => new El(t) };

// ---- stations
const PROV = /^from game-world-focus @3ea15f0, artifacts\/trade-quest-3d\/src\/components\/game\/[A-Za-z]+\.tsx$/;
const tq = arg('tq') || '/home/user/game-world-focus';
const haveClone = existsSync(join(tq, '.git'));
for (const kind of Object.keys(K.TQ_KINDS)) {
  const st = K.createTQStation(kind, { THREE, strings: S, doc: null });
  const sz = K.TQ_KINDS[kind].size;
  const box = new THREE.Box3().setFromObject(st.group);
  const e = 1e-6;
  ok(`${kind}: the station fits its declared ${sz.w} x ${sz.d} x ${sz.h} m footprint, standing on the floor`,
    box.min.x >= -sz.w / 2 - e && box.max.x <= sz.w / 2 + e && box.min.z >= -sz.d / 2 - e && box.max.z <= sz.d / 2 + e
    && box.min.y >= -e && box.max.y <= sz.h + e, [JSON.stringify(box)]);
  const meshes = []; st.group.traverse((o) => { if (o.isMesh) meshes.push(o); });
  ok(`${kind}: ${meshes.length} meshes (draw calls) <= the cap of ${K.TQ_MESH_CAP}`, meshes.length > 6 && meshes.length <= K.TQ_MESH_CAP);
  const badProv = meshes.filter((m) => !PROV.test(m.userData.provenance) || !st.provenance.includes(m.userData.provenance) || m.userData.authored !== 'AUTHORED');
  ok(`${kind}: every mesh carries "from game-world-focus @3ea15f0, <path>" and AUTHORED; group carries its list`,
    badProv.length === 0 && st.group.userData.authored === 'AUTHORED' && st.group.userData.tqKind === kind
    && st.provenance.every((p) => PROV.test(p)) && st.provenance.every((p) => meshes.some((m) => m.userData.provenance === p)),
  badProv.map((m) => m.userData.provenance));
  if (haveClone) {
    const gone = st.provenance.filter((p) => { const path = p.split(', ')[1]; try { execFileSync('git', ['-C', tq, 'cat-file', '-e', `3ea15f0:${path}`], { stdio: 'pipe' }); return false; } catch { return true; } });
    ok(`${kind}: every provenance path exists in game-world-focus at 3ea15f0`, gone.length === 0, gone);
  } else console.log(`  note ${kind}: no game-world-focus clone at ${tq}; provenance paths checked by format only`);
  ok(`${kind}: group name, size copy and the hit target are set`, st.group.name === `tq-station-${kind}` && st.size.w === sz.w && st.size.clear > 0
    && st.group.userData.tqHit && st.group.userData.tqHit.isMesh && st.panel === null);
  const tags = meshes.filter((m) => m.userData.provenance.endsWith('HVACObjects.tsx') && m.visible === false);
  ok(`${kind}: the lockout tag is hidden until the hand-off`, tags.length === 2);
  const before = st.group.userData.tqHit.material.emissive.getHexString();
  for (let i = 0; i < 6; i++) st.advance();
  ok(`${kind}: four advances finish the station and a fifth changes nothing (step 4 of 4)`, st.step() === 4);
  ok(`${kind}: done shows the tag, turns the label green`, meshes.filter((m) => m.userData.provenance.endsWith('HVACObjects.tsx') && m.geometry.type !== 'RingGeometry' && m.visible).length >= 2
    && st.group.userData.tqHit.material.emissive.getHexString() === '22c55e' && before !== '22c55e');
  st.reset();
  ok(`${kind}: reset returns to step 0 and hides the tag again`, st.step() === 0 && meshes.filter((m) => m.visible === false).length === 2);
  const parent = new THREE.Group(); parent.add(st.group);
  let disposed = 0; meshes.forEach((m) => m.geometry.addEventListener('dispose', () => { disposed++; }));
  const geos = new Set(meshes.map((m) => m.geometry));
  st.dispose();
  ok(`${kind}: dispose detaches the group and disposes every geometry`, st.group.parent === null && parent.children.length === 0 && disposed === geos.size);
  ok(`${kind}: a disposed station refuses to advance`, throwsLike(() => st.advance(), /disposed/));
}

// ---- panel model
const m0 = K.tqPanelModel('electrical', S, 0), m2 = K.tqPanelModel('electrical', S, 2), m4 = K.tqPanelModel('electrical', S, 4);
ok('panel model: step 0 = first current, rest todo; progress reads "Step 1 of 4"',
  m0.steps.map((s) => s.state).join() === 'current,todo,todo,todo' && m0.progress === S['tqkit.step'].replace('{n}', '1').replace('{total}', '4'));
ok('panel model: step 2 = two done, third current; step 4 = all done, done text, done flag',
  m2.steps.map((s) => s.state).join() === 'done,done,current,todo' && m4.done && m4.progress === S['tqkit.done'] && m4.steps.every((s) => s.state === 'done'));
ok('panel model: provenance line names game-world-focus @3ea15f0 and the AUTHORED label', m0.prov.includes('game-world-focus @3ea15f0') && m0.prov.startsWith(S['tqkit.authored']));

// ---- fail closed
ok('unknown kind throws by name', throwsLike(() => K.createTQStation('roofing', { THREE, strings: S, doc: null }), /unknown kind roofing/));
ok('missing THREE / strings / doc each throws by name',
  throwsLike(() => K.createTQStation('hvac', { strings: S, doc: null }), /has no THREE/) && throwsLike(() => K.createTQStation('hvac', { THREE, doc: null }), /has no strings/)
  && throwsLike(() => K.createTQStation('hvac', { THREE, strings: S }), /has no doc/));
const S2 = Object.assign({}, S); delete S2['tqkit.hvac.s3'];
ok('a missing string throws naming the key; another kind\'s missing key does not block this kind',
  throwsLike(() => K.createTQStation('hvac', { THREE, strings: S2, doc: null }), /missing string tqkit\.hvac\.s3/) && !throwsLike(() => K.createTQStation('plumbing', { THREE, strings: S2, doc: null }), /./));
ok('a bad step index throws', throwsLike(() => K.tqPanelModel('hvac', S, 5), /bad step/) && throwsLike(() => K.tqPanelModel('hvac', S, 1.5), /bad step/));

// ---- DOM panel
const sp = K.createTQStation('carpentry', { THREE, strings: S, doc });
const P = sp.panel, els = P ? P.all() : [];
const lis = els.filter((e) => e.tagName === 'LI'), btns = els.filter((e) => e.tagName === 'BUTTON');
ok('panel: one <section role=region> labelled by the title, 4 steps, exactly one aria-current=step',
  P && P.tagName === 'SECTION' && P.getAttribute('role') === 'region' && P.getAttribute('aria-label') === S['tqkit.carpentry.title']
  && lis.length === 4 && lis.filter((l) => l.getAttribute('aria-current') === 'step').length === 1 && lis[0].textContent === S['tqkit.carpentry.s1']);
ok('panel: no heading element (the page keeps its one <h1>); two real type=button buttons',
  !els.some((e) => /^H[1-6]$/.test(e.tagName)) && btns.length === 2 && btns.every((b) => b.getAttribute('type') === 'button'));
ok('panel: the play-only note appears exactly once; progress is aria-live=polite',
  els.filter((e) => e.textContent === S['tqkit.note']).length === 1 && els.some((e) => e.className === 'tqk-progress' && e.getAttribute('aria-live') === 'polite'));
let seen = -1; sp.onChange((d) => { seen = d; });
const next = btns.find((b) => b.className === 'tqk-next'), rst = btns.find((b) => b.className === 'tqk-reset');
next.click(); next.click();
ok('panel: Next advances the station, moves aria-current, marks steps done, notifies onChange',
  sp.step() === 2 && seen === 2 && lis[2].getAttribute('aria-current') === 'step' && lis[0].getAttribute('data-state') === 'done' && !lis[0].getAttribute('aria-current'));
next.click(); next.click();
ok('panel: at the end Next is disabled and the done text shows', next.disabled === true && els.some((e) => e.textContent === S['tqkit.done']));
rst.click();
ok('panel: Start again resets to step 1', sp.step() === 0 && next.disabled === false && lis[0].getAttribute('aria-current') === 'step');
const host = new El('div'); host.append(P); sp.dispose();
ok('panel: dispose removes the panel from the page', host.children.length === 0);

// ---- panel CSS: contrast in both palettes, targets, focus, reduced motion
const css = PY.css;
const pal = (block) => Object.fromEntries([...block.matchAll(/--tqk-([a-z-]+):(#[0-9a-f]{6})/g)].map((m) => [m[1], m[2]]));
const dark = pal(css.slice(0, css.indexOf('@media (prefers-color-scheme:light)')));
const light = pal(css.slice(css.indexOf('[data-theme="light"] .tqk-panel')));
const lum = (h) => { const c = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
const cr = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
const pairs = [['ink', 'bg'], ['muted', 'bg'], ['accent-ink', 'accent'], ['done', 'bg']];
const low = [];
for (const [name, p] of [['dark', dark], ['light', light]]) for (const [f, b] of pairs) { const r = p[f] && p[b] ? cr(p[f], p[b]) : 0; if (r < 4.5) low.push(`${name} ${f}/${b} ${r.toFixed(2)}`); }
ok('panel CSS: every text/background pair is >= 4.5:1 (WCAG AA) in dark and light', low.length === 0, low);
ok('panel CSS: the light palette also applies under prefers-color-scheme:light (same values)',
  JSON.stringify(pal(css.slice(css.indexOf('@media (prefers-color-scheme:light)'), css.indexOf('[data-theme="light"] .tqk-panel')))) === JSON.stringify(light));
ok('panel CSS: 44 px targets, a visible focus ring, reduced-motion respected, logical properties only',
  /min-block-size:44px/.test(css) && /min-inline-size:44px/.test(css) && /:focus-visible\{outline:3px/.test(css) && /prefers-reduced-motion:reduce/.test(css)
  && !/(margin|padding)-(left|right)|[^-]left:|[^-]right:/.test(css));

console.log(bad ? `FAIL  ${bad} of ${n + bad} checks failed` : `test_tqkit: ${n} checks ok`);
process.exit(bad ? 1 : 0);
