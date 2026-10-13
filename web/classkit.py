"""classkit - the in-world class session kit, embeddable in any world page.

  class_data(worlds=None)  compact data from classroom/registry/classroom.json (fail closed), optionally
                           restricted to the named worlds ('parishes' | 'wilds' | 'campus').
  class_i18n()             {locale: {dir, strings: {class.* keys}}} from i18n/locales (all 8, fail closed).
  auth_core()              the sign-in page's AUTH-CORE region, lifted verbatim (plan signatures are
                           checked with the repo's own EIP-191 recovery; this kit carries no crypto of its own).
  CLASS_CSS, CLASS_JS      the HUD (start/pause session, current lesson moment, XP, streak), the lesson-moment
                           choice card, the class-plan loader (?plan=<base64url JSON> or an imported file) and
                           the local progress store. CLASS-CORE is pure (no DOM) and is run in node by the tests.

Host page contract:  embed  <script type="application/json" id="class-data">, <script type="application/json"
id="class-i18n">, then <script>AUTH</script><script>CLASS_JS</script>; call TCClass.mount({world:'<id>'}) and
TCClass.reach('<place id>') when the learner arrives at a mapped place (or dispatch window event
'tc-class-reach' with detail {place}). Play only: localStorage (guarded), no network, never a completion record.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / 'classroom/registry/classroom.json'
SIGNIN = ROOT / 'web/trade_craft_signin.html'
WORLDS = ('parishes', 'wilds', 'campus')


class ClassKitError(Exception):
    pass


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise ClassKitError(f'classkit: {where} has no {k!r}')
    return d[k]


def class_data(worlds=None):
    if not REG.is_file():
        raise ClassKitError('classkit: classroom/registry/classroom.json is missing; run python3 classroom/build.py')
    C = json.loads(REG.read_text(encoding='utf-8'))
    ws = list(WORLDS if worlds is None else worlds)
    for w in ws:
        if w not in WORLDS:
            raise ClassKitError(f'classkit: unknown world {w!r}')
    places = [p for p in _need(C, 'places', 'registry') if _need(p, 'world', 'place') in ws]
    pids = {p['id'] for p in places}
    mods = []
    for m in _need(C, 'modules', 'registry'):
        mp = [x for x in _need(m, 'places', m['id']) if x in pids]
        if mp:
            mods.append({'id': m['id'], 'hall': _need(m, 'hall', m['id']), 'name': _need(m, 'hall_name', m['id']),
                         'moments': _need(m, 'moments', m['id']), 'lessons': _need(m, 'lessons', m['id']),
                         'places': mp, 'src': _need(m, 'unit_source', m['id'])})
    X = _need(C, 'cognitionx', 'registry')
    for m in _need(X, 'modules', 'cognitionx'):
        mp = [x for x in _need(m, 'places', m['id']) if x in pids]
        if mp:
            mods.append({'id': m['id'], 'kind': 'cognitionx', 'hall': None,
                         'name': f"Cognition.X {_need(m, 'pack', m['id'])}: {_need(m, 'name', m['id'])}",
                         'moments': _need(m, 'moments', m['id']), 'lessons': [], 'places': mp, 'src': 'cognitionx/registry/cognitionx.json'})
    keep = {mo for m in mods for mo in m['moments']}
    moments = []
    for mo in _need(X, 'moments', 'cognitionx'):
        if mo['id'] in keep:
            moments.append({k: _need(mo, k, mo['id']) for k in ('id', 'module', 'kind', 'block', 'statement_field', 'band', 'source')}
                           | {'places': [x for x in _need(mo, 'places', mo['id']) if x in pids]})
    for mo in _need(C, 'moments', 'registry'):
        if mo['id'] in keep:
            moments.append({k: _need(mo, k, mo['id']) for k in (
                'id', 'module', 'kind', 'lesson', 'title', 'title_source', 'answer', 'choices', 'answer_source', 'limits',
                'first_do', 'status')} | {'places': [x for x in _need(mo, 'places', mo['id']) if x in pids]})
    return {
        'v': 'tc-class-data/1', 'stamp': _need(C, 'source_stamp', 'registry'), 'worlds': ws,
        'honesty': _need(C, 'honesty', 'registry'), 'rules': _need(C, 'rules', 'registry'),
        'cx_attribution': _need(X, 'attribution', 'cognitionx'), 'cx_honesty': _need(X, 'honesty', 'cognitionx'),
        'modules': mods, 'moments': moments,
        'places': [{k: p[k] for k in ('id', 'world', 'kind', 'title', 'href', 'source')} for p in places],
    }


def class_i18n():
    out = {}
    for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
        c = json.loads(f.read_text(encoding='utf-8'))
        s = {k: v for k, v in _need(c, 'strings', f.name).items() if k.startswith('class.')}
        out[_need(c, 'locale', f.name)] = {'dir': _need(c, 'dir', f.name), 'strings': s}
    if len(out) != 8:
        raise ClassKitError(f'classkit: expected 8 locales, found {sorted(out)}')
    en = set(out['en']['strings'])
    need = {k for k in CLASS_KEYS}
    if not need <= en:
        raise ClassKitError(f'classkit: en is missing {sorted(need - en)[:5]}')
    for loc, c in out.items():
        miss = need - set(c['strings'])
        if miss:
            raise ClassKitError(f'classkit: locale {loc} is missing {sorted(miss)[:5]}')
    return out


def auth_core():
    if not SIGNIN.is_file():
        raise ClassKitError('classkit: web/trade_craft_signin.html is missing; run python3 web/build_auth.py')
    page = SIGNIN.read_text(encoding='utf-8')
    a, b = page.find('/* AUTH-CORE:BEGIN'), page.find('/* AUTH-CORE:END */')
    if a < 0 or b <= a:
        raise ClassKitError('classkit: the sign-in page carries no AUTH-CORE region')
    core = page[a:b + len('/* AUTH-CORE:END */')]
    return ('var TCClassAuth = (function () {\n' + core
            + '\nreturn { recoverAddress: recoverAddress, toChecksumAddress: toChecksumAddress };\n})();')


def js_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


# keys the HUD itself reads (a host page may use more class.* keys)
CLASS_KEYS = ('class.hud.title', 'class.hud.start', 'class.hud.pause', 'class.hud.resume', 'class.hud.xp',
              'class.hud.streak', 'class.hud.moment', 'class.hud.none', 'class.hud.left', 'class.hud.plan',
              'class.hud.noplan', 'class.hud.nosave', 'class.hud.play', 'class.hud.idle', 'class.card.q',
              'class.card.right', 'class.card.wrong', 'class.card.close', 'class.card.source', 'class.card.limits',
              'class.card.status', 'class.card.first', 'class.plan.refused', 'class.plan.signed', 'class.plan.bad',
              'class.plan.unsigned', 'class.card.transfer', 'class.card.tried', 'class.card.noted', 'class.cx.attr')

CLASS_CSS = '''
.tcc-hud{position:fixed;inset-block-end:12px;inset-inline-end:12px;z-index:60;max-inline-size:min(340px,calc(100vw - 24px));
 background:var(--tc-panel,Canvas);color:var(--tc-ink,CanvasText);border:1px solid var(--tc-line,GrayText);border-radius:10px;
 padding:10px 12px;font:14px/1.45 system-ui,sans-serif;box-shadow:0 4px 18px rgba(0,0,0,.25)}
.tcc-hud h2{font-size:15px;margin:0 0 6px}
.tcc-row{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center}
.tcc-row b{font-variant-numeric:tabular-nums}
.tcc-hud button,.tcc-card button{min-block-size:44px;min-inline-size:44px;padding:0 12px;border-radius:8px;
 border:1px solid var(--tc-line,currentColor);background:transparent;color:inherit;font:inherit;cursor:pointer}
.tcc-note{color:var(--tc-muted,GrayText);font-size:12px;margin:6px 0 0}
.tcc-card{border:1px solid var(--tc-line,GrayText);border-radius:10px;padding:14px;max-inline-size:min(560px,calc(100vw - 24px));
 background:var(--tc-panel,Canvas);color:var(--tc-ink,CanvasText)}
.tcc-card::backdrop{background:rgba(0,0,0,.45)}
.tcc-card h3{margin:0 0 8px;font-size:17px}
.tcc-card ol{padding:0;margin:8px 0;list-style:none;display:grid;gap:8px}
.tcc-card ol button{inline-size:100%;text-align:start;padding:8px 10px;line-height:1.4}
.tcc-card .tcc-src{font-size:12px;color:var(--tc-muted,GrayText);overflow-wrap:anywhere}
.tcc-hud [hidden],.tcc-card [hidden]{display:none}
.tcc-hud[data-cc-compact]{padding:4px}
.tcc-hud[data-cc-compact]:not([data-cc-open])>:not(h2){display:none}
.tcc-hud[data-cc-compact] h2{margin:0}
'''

CLASS_JS = r'''/* CLASS-CORE:BEGIN - pure: no DOM, no storage, no network. Lifted and run in node by web/test_classroom.mjs. */
var TCClassCore = (function () {
  'use strict';
  var PLAN_V = 'tc-class-plan/1', PROG_V = 'tc-class-progress/1';
  var XP_KEYS = ['module_complete', 'moment_correct', 'moment_tried', 'place_reached'];
  function fail(m) { throw new Error('class: ' + m); }
  function canon(o) {
    if (Array.isArray(o)) return '[' + o.map(canon).join(',') + ']';
    if (o !== null && typeof o === 'object') return '{' + Object.keys(o).sort().map(function (k) { return JSON.stringify(k) + ':' + canon(o[k]); }).join(',') + '}';
    return JSON.stringify(o);
  }
  function b64e(s) {
    var u = new TextEncoder().encode(s), b = '', i;
    for (i = 0; i < u.length; i++) b += String.fromCharCode(u[i]);
    return btoa(b).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function b64d(s) {
    if (typeof s !== 'string' || !/^[A-Za-z0-9_-]+$/.test(s)) fail('plan link is not base64url');
    var b = atob(s.replace(/-/g, '+').replace(/_/g, '/')), u = new Uint8Array(b.length), i;
    for (i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
    return new TextDecoder('utf-8', { fatal: true }).decode(u);
  }
  function unsigned(plan) { var o = {}; Object.keys(plan).forEach(function (k) { if (k !== 'sig') o[k] = plan[k]; }); return o; }
  function planMessage(plan) { return 'SmartCiti.X class plan (play; not access control)\n' + canon(unsigned(plan)); }
  function validatePlan(p, data) {
    if (p === null || typeof p !== 'object' || Array.isArray(p)) fail('plan is not an object');
    var allowed = ['modules', 'paths', 'session_minutes', 'sig', 'signer', 'title', 'v', 'worlds', 'xp'];
    Object.keys(p).forEach(function (k) { if (allowed.indexOf(k) < 0) fail('plan has unknown field ' + k); });
    if (p.v !== PLAN_V) fail('plan version is not ' + PLAN_V);
    if (typeof p.title !== 'string' || p.title.length > 120) fail('plan title must be text up to 120 characters');
    if (!Array.isArray(p.worlds) || !p.worlds.length) fail('plan names no world');
    p.worlds.forEach(function (w) { if (data.worlds.indexOf(w) < 0) fail('plan names unknown world ' + w); });
    if (!Array.isArray(p.modules) || !p.modules.length) fail('plan names no module');
    var mids = data.modules.map(function (m) { return m.id; });
    p.modules.forEach(function (m) { if (mids.indexOf(m) < 0) fail('plan names unknown module ' + m); });
    if (typeof p.paths !== 'boolean') fail('plan paths must be true or false');
    if (data.rules.session_minutes.choices.indexOf(p.session_minutes) < 0) fail('plan session length is not one of the offered lengths');
    if (p.xp === null || typeof p.xp !== 'object' || canon(Object.keys(p.xp).sort()) !== canon(XP_KEYS)) fail('plan xp must name exactly ' + XP_KEYS.join(', '));
    XP_KEYS.forEach(function (k) { var n = p.xp[k]; if (!Number.isInteger(n) || n < 0 || n > 1000) fail('plan xp.' + k + ' must be a whole number 0-1000'); });
    if (('sig' in p) !== ('signer' in p)) fail('plan carries a signature without a signer, or a signer without a signature');
    return p;
  }
  /* returns 'unsigned' | 'signed'; a signature that does not recover to the signer refuses the plan */
  function verifyPlan(p, auth) {
    if (!('sig' in p)) return 'unsigned';
    if (!auth) fail('plan is signed but this page carries no signature check; plan refused');
    var r;
    try { r = auth.recoverAddress(planMessage(p), p.sig); } catch (e) { fail('plan signature cannot be read; plan refused'); }
    if (String(r).toLowerCase() !== String(p.signer).toLowerCase()) fail('plan signature does not recover to its signer; plan refused');
    return 'signed';
  }
  function encodePlan(p) { return b64e(canon(p)); }
  function decodePlan(s, data, auth) {
    var p;
    try { p = JSON.parse(b64d(s)); } catch (e) { fail('plan cannot be read (' + e.message + ')'); }
    validatePlan(p, data);
    return { plan: p, sign: verifyPlan(p, auth) };
  }
  function defaultPlan(data) {
    return { v: PLAN_V, title: '', worlds: data.worlds.slice(), modules: data.modules.map(function (m) { return m.id; }),
      paths: true, session_minutes: data.rules.session_minutes['default'], xp: JSON.parse(JSON.stringify(data.rules.xp)) };
  }
  /* places and moments a plan shows */
  function scope(data, plan) {
    var P = {}, M = {}, byId = {};
    data.places.forEach(function (p) { byId[p.id] = p; });
    data.modules.forEach(function (m) {
      if (plan.modules.indexOf(m.id) < 0) return;
      m.places.forEach(function (id) {
        var p = byId[id];
        if (!p) fail('module ' + m.id + ' names unknown place ' + id);
        if (plan.worlds.indexOf(p.world) < 0) return;
        if (!plan.paths && p.kind === 'path-step') return;
        P[id] = p;
      });
      m.moments.forEach(function (id) { M[id] = true; });
    });
    return { places: P, moments: data.moments.filter(function (mo) { return M[mo.id] && mo.places.some(function (id) { return P[id]; }); }) };
  }
  function newProgress() { return { v: PROG_V, learner: '', moments: {}, places: {}, days: [], sessions: [] }; }
  function day(now) { return new Date(now).toISOString().slice(0, 10); }
  function markDay(st, now) { var d = day(now); if (st.days.indexOf(d) < 0) { st.days.push(d); st.days.sort(); } }
  function reach(st, placeId, data, now) {
    if (!data.places.some(function (p) { return p.id === placeId; })) fail('unknown place ' + placeId);
    if (st.places[placeId]) return false;
    st.places[placeId] = day(now);
    return true;
  }
  function answer(st, moment, lessonId, now) {
    if (moment.kind !== 'choice') fail('moment ' + moment.id + ' is not a choice card');
    if (!moment.choices.some(function (c) { return c.lesson === lessonId; })) fail('choice ' + lessonId + ' is not on card ' + moment.id);
    var r = st.moments[moment.id] || { tried: 0, correct: false };
    r.tried += 1;
    var right = lessonId === moment.answer;
    if (right) r.correct = true;
    st.moments[moment.id] = r;
    markDay(st, now);
    return right;
  }
  /* a Cognition.X transfer moment has no answer key upstream: the learner self-reports trying it (play XP only) */
  function tried(st, moment, now) {
    if (moment.kind !== 'transfer') fail('moment ' + moment.id + ' is not a transfer moment');
    var r = st.moments[moment.id] || { tried: 0, correct: false };
    r.tried += 1; r.correct = true; st.moments[moment.id] = r; markDay(st, now);
    return true;
  }
  function modulesDone(st, data) {
    return data.modules.filter(function (m) { return m.moments.length && m.moments.every(function (id) { return st.moments[id] && st.moments[id].correct; }); }).map(function (m) { return m.id; });
  }
  function streak(days, now) {
    var ds = days.slice().sort(), t = Date.parse(day(now) + 'T00:00:00Z');
    if (!ds.length) return 0;
    var last = Date.parse(ds[ds.length - 1] + 'T00:00:00Z');
    if (t - last > 86400000) return 0;
    var n = 1, i;
    for (i = ds.length - 1; i > 0; i--) {
      if (Date.parse(ds[i] + 'T00:00:00Z') - Date.parse(ds[i - 1] + 'T00:00:00Z') === 86400000) n++; else break;
    }
    return n;
  }
  function xpOf(st, data, xp) {
    var tried = 0, correct = 0;
    Object.keys(st.moments).forEach(function (k) { tried += st.moments[k].tried; if (st.moments[k].correct) correct++; });
    return Object.keys(st.places).length * xp.place_reached + tried * xp.moment_tried + correct * xp.moment_correct
      + modulesDone(st, data).length * xp.module_complete;
  }
  function badges(st, data, xp, now) {
    var met = Object.keys(st.moments).filter(function (k) { return st.moments[k].correct; }).length;
    var wset = {};
    Object.keys(st.places).forEach(function (id) { data.places.forEach(function (p) { if (p.id === id) wset[p.world] = 1; }); });
    var have = { moments: met, worlds: Object.keys(wset).length, streak: streak(st.days, now), modules: modulesDone(st, data).length, xp: xpOf(st, data, xp) };
    return data.rules.badges.filter(function (b) { if (!(b.rule.kind in have)) fail('badge rule kind ' + b.rule.kind); return have[b.rule.kind] >= b.rule.n; }).map(function (b) { return b.id; });
  }
  function checkProgress(f, data) {
    if (f === null || typeof f !== 'object' || f.v !== PROG_V) fail('not a ' + PROG_V + ' file');
    if (typeof f.learner !== 'string' || !f.learner.trim()) fail('progress file names no learner');
    if (f.moments === null || typeof f.moments !== 'object' || f.places === null || typeof f.places !== 'object' || !Array.isArray(f.days)) fail('progress file is missing moments, places or days');
    var mids = {}; data.moments.forEach(function (m) { mids[m.id] = 1; });
    Object.keys(f.moments).forEach(function (k) {
      var r = f.moments[k];
      if (!mids[k]) fail('progress file names unknown moment ' + k);
      if (!r || !Number.isInteger(r.tried) || r.tried < 1 || typeof r.correct !== 'boolean') fail('progress moment ' + k + ' is malformed');
    });
    var pids = {}; data.places.forEach(function (p) { pids[p.id] = 1; });
    Object.keys(f.places).forEach(function (k) { if (!pids[k]) fail('progress file names unknown place ' + k); });
    f.days.forEach(function (d) { if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) fail('progress day ' + d + ' is not a date'); });
    return f;
  }
  /* class scoreboard from imported files only; XP is RECOMPUTED here with the given rules, never read from the file */
  function scoreboard(files, data, xp, now) {
    var rows = [], refused = [];
    files.forEach(function (x) {
      try {
        var f = checkProgress(x.json, data);
        rows.push({ learner: f.learner.trim(), xp: xpOf(f, data, xp), met: Object.keys(f.moments).filter(function (k) { return f.moments[k].correct; }).length,
          modules: modulesDone(f, data).length, streak: streak(f.days, now), badges: badges(f, data, xp, now).length });
      } catch (e) { refused.push({ name: x.name, why: e.message }); }
    });
    rows.sort(function (a, b) { return b.xp - a.xp || (a.learner < b.learner ? -1 : a.learner > b.learner ? 1 : 0); });
    rows.forEach(function (r, i) { r.rank = i > 0 && rows[i - 1].xp === r.xp ? rows[i - 1].rank : i + 1; });
    return { rows: rows, refused: refused };
  }
  function exportProgress(st, now, planTitle) {
    return { v: PROG_V, learner: st.learner, exported_at: new Date(now).toISOString(), plan_title: planTitle,
      moments: st.moments, places: st.places, days: st.days, sessions: st.sessions,
      note: 'play - XP, streaks and badges are not a completion record and certify nothing' };
  }
  return { PLAN_V: PLAN_V, PROG_V: PROG_V, canon: canon, encodePlan: encodePlan, decodePlan: decodePlan, validatePlan: validatePlan,
    verifyPlan: verifyPlan, planMessage: planMessage, defaultPlan: defaultPlan, scope: scope, newProgress: newProgress, reach: reach,
    answer: answer, tried: tried, markDay: markDay, modulesDone: modulesDone, streak: streak, xpOf: xpOf, badges: badges, checkProgress: checkProgress,
    scoreboard: scoreboard, exportProgress: exportProgress, day: day };
})();
/* CLASS-CORE:END */
var TCClass = (function () {
  'use strict';
  var K = TCClassCore, D = JSON.parse(document.getElementById('class-data').textContent);
  var I = JSON.parse(document.getElementById('class-i18n').textContent);
  var AUTH = typeof TCClassAuth === 'undefined' ? null : TCClassAuth;
  var PROG_KEY = 'tc-class-progress', PLAN_KEY = 'tc-class-plan';
  var saved = true, st, plan, planSign = 'none', planErr = '', sc, run = null, timer = null, hud = null, card = null, cur = null;
  function loc() {
    var q = new URLSearchParams(location.search).get('lang');
    if (q && Object.prototype.hasOwnProperty.call(I, q)) return q;
    var l = String(document.documentElement.lang || 'en').slice(0, 2);
    return Object.prototype.hasOwnProperty.call(I, l) ? l : 'en';
  }
  function t(k) { var s = I[loc()].strings[k]; if (typeof s !== 'string') throw new Error('class i18n: no ' + k); return s; }
  function load(key) { try { return window.localStorage.getItem(key); } catch (e) { saved = false; return null; } }
  function save(key, v) { try { window.localStorage.setItem(key, v); } catch (e) { saved = false; } }
  function persist() { save(PROG_KEY, JSON.stringify(st)); }
  function initState() {
    var raw = load(PROG_KEY);
    st = K.newProgress();
    if (raw) { try { var p = JSON.parse(raw); if (p && p.v === K.PROG_V) st = p; } catch (e) { st = K.newProgress(); } }
    plan = K.defaultPlan(D);
    var q = new URLSearchParams(location.search).get('plan'), src = q || load(PLAN_KEY);
    if (src) {
      try { var r = K.decodePlan(src, D, AUTH); plan = r.plan; planSign = r.sign; if (q) save(PLAN_KEY, q); }
      catch (e) { planErr = e.message; planSign = 'refused'; plan = K.defaultPlan(D); }
    }
    sc = K.scope(D, plan);
  }
  function setPlan(encoded) {
    var r = K.decodePlan(encoded, D, AUTH);
    plan = r.plan; planSign = r.sign; planErr = ''; sc = K.scope(D, plan); save(PLAN_KEY, encoded); render();
    return r;
  }
  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function left() { return run ? Math.max(0, Math.ceil((run.until - Date.now()) / 60000)) : plan.session_minutes; }
  function render() {
    if (!hud) return;
    var xp = K.xpOf(st, D, plan.xp);
    hud.querySelector('[data-cc-xp]').textContent = String(xp);
    hud.querySelector('[data-cc-streak]').textContent = String(K.streak(st.days, Date.now()));
    hud.querySelector('[data-cc-left]').textContent = String(left());
    var b = hud.querySelector('[data-cc-toggle]');
    b.textContent = run && !run.paused ? t('class.hud.pause') : (run ? t('class.hud.resume') : t('class.hud.start'));
    hud.querySelector('[data-cc-moment]').textContent = cur ? (cur.kind === 'transfer' ? cur.block.theme : cur.title) : (run ? t('class.hud.none') : t('class.hud.idle'));
    var pl = hud.querySelector('[data-cc-plan]');
    pl.textContent = planSign === 'refused' ? t('class.plan.refused') + ' (' + planErr + ')'
      : (plan.title ? t('class.hud.plan') + ': ' + plan.title + ' - ' + (planSign === 'signed' ? t('class.plan.signed') : t('class.plan.unsigned')) : t('class.hud.noplan'));
    hud.querySelector('[data-cc-nosave]').hidden = saved;
    hud.setAttribute('data-cc-state', run ? (run.paused ? 'paused' : 'running') : 'idle');
  }
  function toggle() {
    var now = Date.now();
    if (!run) { run = { start: now, until: now + plan.session_minutes * 60000, paused: false }; st.sessions.push({ start: new Date(now).toISOString(), minutes: plan.session_minutes }); persist(); }
    else if (!run.paused) { run.paused = true; run.left = run.until - now; }
    else { run.paused = false; run.until = now + run.left; }
    render();
  }
  function tick() { if (run && !run.paused && Date.now() >= run.until) { run = null; cur = null; } render(); }
  function showCard(mo) {
    cur = mo;
    if (!card) { card = el('dialog', { 'class': 'tcc-card', 'data-cc-card': '' }); document.body.appendChild(card); }
    card.textContent = '';
    if (mo.kind === 'transfer') return transferCard(mo);
    card.appendChild(el('p', { 'class': 'tcc-src' }, t('class.card.status')));
    card.appendChild(el('h3', {}, mo.title));
    card.appendChild(el('p', {}, t('class.card.q')));
    var ol = el('ol'), fb = el('p', { 'data-cc-feedback': '', 'aria-live': 'polite' });
    mo.choices.forEach(function (c) {
      var li = el('li'), b = el('button', { type: 'button', 'data-cc-choice': c.lesson }, c.text);
      b.addEventListener('click', function () {
        var right = K.answer(st, mo, c.lesson, Date.now());
        persist();
        var ans = mo.choices.filter(function (x) { return x.lesson === mo.answer; })[0];
        fb.textContent = right ? t('class.card.right') : t('class.card.wrong') + ' ' + ans.text;
        render();
      });
      li.appendChild(b); ol.appendChild(li);
    });
    card.appendChild(ol); card.appendChild(fb);
    card.appendChild(el('p', {}, t('class.card.first') + ': ' + mo.first_do));
    card.appendChild(el('p', {}, t('class.card.limits') + ': ' + mo.limits));
    card.appendChild(el('p', { 'class': 'tcc-src' }, t('class.card.source') + ': ' + mo.title_source + ' ; ' + mo.answer_source));
    var close = el('button', { type: 'button', 'data-cc-close': '' }, t('class.card.close'));
    close.addEventListener('click', function () { if (card.close) card.close(); else card.removeAttribute('open'); cur = null; render(); });
    card.appendChild(close);
    if (card.showModal) { if (!card.open) card.showModal(); } else card.setAttribute('open', '');
    render();
  }
  function closeBtn() {
    var close = el('button', { type: 'button', 'data-cc-close': '' }, t('class.card.close'));
    close.addEventListener('click', function () { if (card.close) card.close(); else card.removeAttribute('open'); cur = null; render(); });
    return close;
  }
  /* Cognition.X block: statement + transfer check VERBATIM (source English), CC BY 4.0 attribution, self-reported try */
  function transferCard(mo) {
    var A = D.cx_attribution, b = mo.block;
    card.appendChild(el('p', { 'class': 'tcc-src' }, b.pack + ' - ' + b.track + ' (' + b.code + ', ' + b.grade + ')'));
    card.appendChild(el('h3', { lang: 'en', dir: 'ltr' }, b.theme));
    if (mo.statement_field === 'description') card.appendChild(el('p', { lang: 'en', dir: 'ltr' }, b.description));
    var tc = el('p', {}); tc.appendChild(el('b', {}, t('class.card.transfer') + ': ')); tc.appendChild(el('span', { lang: 'en', dir: 'ltr', 'data-cc-transfer': '' }, b.transfer_check));
    card.appendChild(tc);
    var fb = el('p', { 'data-cc-feedback': '', 'aria-live': 'polite' });
    var go = el('button', { type: 'button', 'data-cc-tried': '' }, t('class.card.tried'));
    go.addEventListener('click', function () { K.tried(st, mo, Date.now()); persist(); fb.textContent = t('class.card.noted'); render(); });
    card.appendChild(go); card.appendChild(fb);
    var at = el('p', { 'class': 'tcc-src', 'data-cc-attr': '' });
    at.appendChild(el('span', {}, t('class.cx.attr') + ' '));
    var a1 = el('a', { href: A.repo, rel: 'noopener', target: '_blank' }, A.text); at.appendChild(a1);
    at.appendChild(el('span', {}, ' - '));
    var a2 = el('a', { href: A.license_url, rel: 'license noopener', target: '_blank' }, 'CC BY 4.0'); at.appendChild(a2);
    at.appendChild(el('span', {}, '. ' + A.changes + '. ' + D.cx_honesty.blocks));
    card.appendChild(at);
    card.appendChild(el('p', { 'class': 'tcc-src' }, t('class.card.source') + ': ' + mo.source));
    card.appendChild(closeBtn());
    if (card.showModal) { if (!card.open) card.showModal(); } else card.setAttribute('open', '');
    render();
  }
  /* the learner arrived at a mapped place: award the place, then offer the next un-met moment there */
  function reach(placeId) {
    if (!run || run.paused) return null;
    if (!sc.places[placeId]) return null;
    K.reach(st, placeId, D, Date.now());
    persist();
    var mo = sc.moments.filter(function (m) { return m.places.indexOf(placeId) >= 0 && !(st.moments[m.id] && st.moments[m.id].correct); })[0];
    if (mo) showCard(mo); else render();
    /* REACTOR_CONTRACT: if the host mounted the (off-by-default) Reactor panel, hand it this place's and moment's
       own page labels as context - never learner text, never a connect; nothing here opens a network connection */
    if (mo && window.ReactorKit && typeof window.ReactorKit.setContext === 'function') {
      window.ReactorKit.setContext({ place: String(sc.places[placeId].title).slice(0, 80),
        lesson: String(mo.kind === 'transfer' ? mo.block.theme : mo.title).slice(0, 80) });
    }
    return mo ? mo.id : null;
  }
  function mount(opts) {
    initState();
    hud = el('section', { 'class': 'tcc-hud', 'data-cc-hud': '', 'aria-label': t('class.hud.title') });
    hud.innerHTML = '<h2></h2><div class="tcc-row"><button type="button" data-cc-toggle></button>'
      + '<span><span data-cc-l="xp"></span> <b data-cc-xp></b></span><span><span data-cc-l="streak"></span> <b data-cc-streak></b></span>'
      + '<span><b data-cc-left></b> <span data-cc-l="left"></span></span></div>'
      + '<p class="tcc-note"><span data-cc-l="moment"></span>: <span data-cc-moment></span></p>'
      + '<p class="tcc-note" data-cc-plan></p><p class="tcc-note" data-cc-nosave hidden></p><p class="tcc-note" data-cc-play></p>';
    var h2 = hud.querySelector('h2');
    if (opts && opts.compact) {
      /* world pages: the HUD starts folded to one 44px button so it never covers the world's own controls */
      hud.setAttribute('data-cc-compact', '');
      var tb = el('button', { type: 'button', 'aria-expanded': 'false', 'data-cc-fold': '' }, t('class.hud.title'));
      tb.addEventListener('click', function () { var o = !hud.hasAttribute('data-cc-open'); if (o) hud.setAttribute('data-cc-open', ''); else hud.removeAttribute('data-cc-open'); tb.setAttribute('aria-expanded', String(o)); });
      h2.appendChild(tb);
    } else h2.textContent = t('class.hud.title');
    ['xp', 'streak', 'left', 'moment'].forEach(function (k) { hud.querySelector('[data-cc-l="' + k + '"]').textContent = t('class.hud.' + k); });
    hud.querySelector('[data-cc-nosave]').textContent = t('class.hud.nosave');
    hud.querySelector('[data-cc-play]').textContent = t('class.hud.play');
    hud.querySelector('[data-cc-toggle]').addEventListener('click', toggle);
    ((opts && opts.host) || document.body).appendChild(hud);
    window.addEventListener('tc-class-reach', function (ev) { if (ev.detail && typeof ev.detail.place === 'string') reach(ev.detail.place); });
    timer = setInterval(tick, 15000);
    render();
    return api;
  }
  var api = { mount: mount, reach: reach, setPlan: setPlan, toggle: toggle,
    state: function () { return st; }, plan: function () { return plan; }, planSign: function () { return planSign; },
    scope: function () { return sc; }, saved: function () { return saved; }, data: D,
    exportProgress: function () { return K.exportProgress(st, Date.now(), plan.title); },
    setLearner: function (n) { st.learner = String(n).slice(0, 60); persist(); },
    refresh: render };
  return api;
})();'''
