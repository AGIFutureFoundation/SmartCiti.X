"""Path chooser + station panel for the parish world (LAYERS_CONTRACT).

  from pathkit import PATH_JS, PATH_CSS, path_data, path_labels, PATH_LABEL_KEYS

  path_data(fips)  one parish of layers/registry/layers.json, JSON-safe, with
                   the titles of explorer steps and suggested lessons read from
                   quests/ and lessons/ (fails by name on an unknown fips or id)
  PATH_CSS         scoped .pk-* CSS; colours only through theme tokens, so all
                   five styles apply
  PATH_JS          plain JS (inline in a <script>, after quest_js if the page
                   carries quests): window.TCPaths = {mount, select, open,
                   close, progress, region}
  path_labels(strings)  the path.* strings of one locale catalog (i18n
                   locales[].strings), keyed without the prefix, for
                   mount(..., {labels}); fails by name on a missing key

The region card (badges earned, borders crossed, rides, guides talked to) is
counted from the same local play state. There is deliberately no region
leaderboard: there is no server and there are no accounts, so nothing about
one player's play ever leaves the device or is compared with anyone's.

Paths are suggestions. Nothing here gates anything: every station opens from
every path, and the player can switch path at any time. Progress rings are
computed only from the device's local play state (localStorage "tc-quests",
the QUEST_CONTRACT key) and are play, never a completion record.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAYERS_PATH = 'layers/registry/layers.json'
QUESTS_PATH = 'quests/registry/quests.json'
LESSONS_PATH = 'lessons/registry/lessons.json'
PATH_STORE = 'tc-path'
PATH_LABEL_KEYS = ('choose', 'note', 'launch', 'close', 'suggested', 'source', 'found', 'of', 'noLaunch',
                   'region', 'badges', 'borders', 'rides', 'guides', 'local', 'trade', 'k12', 'explorer')


def path_labels(strings):
    """The path.* strings of one locale catalog, keyed without the prefix."""
    missing = [k for k in PATH_LABEL_KEYS if 'path.' + k not in strings]
    if missing:
        raise KeyError(f'pathkit: locale catalog has no path.{missing[0]} (missing {len(missing)} path.* keys)')
    return {k: strings['path.' + k] for k in PATH_LABEL_KEYS}
QUEST_STORE = 'tc-quests'


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise KeyError(f'pathkit: {where} has no "{k}"')
    return d[k]


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def path_data(fips):
    layers = _load(LAYERS_PATH)
    parishes = {_need(p, 'fips', LAYERS_PATH): p for p in _need(layers, 'parishes', LAYERS_PATH)}
    if fips not in parishes:
        raise KeyError(f'pathkit: {LAYERS_PATH} holds no parish {fips!r} (has {sorted(parishes)})')
    p = parishes[fips]
    quests = {_need(q, 'id', QUESTS_PATH): q for q in _need(_load(QUESTS_PATH), 'quests', QUESTS_PATH)}
    lessons = _need(_load(LESSONS_PATH), 'lessons', LESSONS_PATH)
    stations = _need(p, 'stations', f'{LAYERS_PATH}#{fips}')
    by_id = {_need(s, 'id', f'{LAYERS_PATH}#{fips}.stations'): s for s in stations}
    steps = {}
    for path in _need(p, 'paths', f'{LAYERS_PATH}#{fips}'):
        for sid in _need(path, 'steps', f'{LAYERS_PATH}#{fips}.paths'):
            if path['id'] == 'explorer':
                if sid not in quests:
                    raise KeyError(f'pathkit: explorer step {sid!r} is not in {QUESTS_PATH}')
                steps[sid] = {'title': _need(quests[sid], 'title', sid), 'hint': _need(quests[sid], 'hint', sid)}
            elif sid not in by_id:
                raise KeyError(f'pathkit: path {path["id"]} step {sid!r} is not a station of {fips}')
    for s in stations:
        if s['treasure'] not in quests:
            raise KeyError(f'pathkit: {s["id"]} treasure {s["treasure"]!r} is not in {QUESTS_PATH}; rebuild quests')
    lesson_titles = {}
    for s in stations:
        for lid in _need(s, 'suggests', s['id']):
            if lid not in lessons:
                raise KeyError(f'pathkit: {s["id"]} suggests {lid!r}, not in {LESSONS_PATH}')
            lesson_titles[lid] = _need(lessons[lid], 'title', lid)
    names = {f: _need(q, 'name', f) for f, q in parishes.items()}
    borders = []
    for o in sorted(_need(p, 'adjacent', f'{LAYERS_PATH}#{fips}')):
        bid = 'treasure-border-' + '-'.join(sorted((fips, o)))
        if o not in names or bid not in quests:
            raise KeyError(f'pathkit: {fips} border with {o!r} has no parish or no {bid} in {QUESTS_PATH}')
        borders.append({'id': bid, 'with': o, 'name': names[o]})
    region = {
        'arrive': f'treasure-parish-{fips}-arrive', 'guide': f'treasure-guide-{fips}',
        'badges': sorted(q['id'] for q in quests.values() if q['world'] == f'parish:{fips}'),
        'borders': borders,
        'rides': sorted(q['id'] for q in quests.values() if q['id'].startswith('treasure-ride-')),
    }
    for k in ('arrive', 'guide'):
        if region[k] not in quests:
            raise KeyError(f'pathkit: {region[k]!r} is not in {QUESTS_PATH}; rebuild quests')
    if not region['rides']:
        raise KeyError(f'pathkit: {QUESTS_PATH} has no treasure-ride-* entries')
    return {
        'fips': fips, 'name': _need(p, 'name', fips), 'stations': stations, 'region': region,
        'paths': p['paths'], 'steps': steps, 'lessons': lesson_titles,
        'layers': {k: _need(v, 'label', k) for k, v in _need(layers, 'layers', LAYERS_PATH).items()},
        'honesty': _need(layers, 'honesty', LAYERS_PATH),
        'k12_districts': _need(layers, 'k12_districts', LAYERS_PATH),
        'store': {'quests': QUEST_STORE, 'path': PATH_STORE},
    }


PATH_CSS = """
.pk{color:var(--ink);background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:12px;
  font:14px/1.45 system-ui,sans-serif;max-width:420px}
.pk h2{font-size:15px;margin:0 0 8px}
.pk-choose{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 8px}
.pk-choose button{display:flex;align-items:center;gap:6px;min-height:44px;padding:4px 10px 4px 4px;border-radius:22px;
  border:1px solid var(--rule);background:var(--surface);color:var(--ink);font:inherit;cursor:pointer}
.pk-choose button[aria-checked="true"]{border-color:var(--mark);background:var(--raised);font-weight:600}
.pk-choose button:focus-visible,.pk button:focus-visible,.pk a:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.pk-ring{width:34px;height:34px;flex:none}
.pk-ring .pk-track{stroke:var(--rule)}
.pk-ring .pk-fill{stroke:var(--mark);transition:stroke-dasharray .3s}
.pk-ring text{fill:var(--ink);font-size:10px}
.pk-count{color:var(--muted);font-size:12px;font-weight:400}
.pk-note{color:var(--muted);font-size:12px;margin:6px 0}
.pk-steps{list-style:decimal;margin:0;padding:0 0 0 22px;max-height:40vh;overflow:auto}
.pk-steps li{margin:2px 0}
.pk-steps button{background:none;border:0;padding:6px 2px;min-height:32px;color:var(--link);font:inherit;
  text-align:start;cursor:pointer;text-decoration:underline}
.pk-steps .pk-got{color:var(--mark);margin-inline-start:4px}
.pk-layer{display:inline-block;font-size:11px;color:var(--mark-ink);background:var(--mark);border-radius:4px;
  padding:0 5px;margin-inline-end:4px}
.pk-panel{margin-top:10px;border-top:1px solid var(--rule);padding-top:10px}
.pk-panel[hidden]{display:none}
.pk-panel h3{font-size:15px;margin:0 0 6px}
.pk-go{display:inline-block;min-height:40px;line-height:40px;padding:0 14px;border-radius:8px;background:var(--mark);
  color:var(--mark-ink);text-decoration:none;font-weight:600}
.pk-why,.pk-src,.pk-prov{color:var(--muted);font-size:12px;overflow-wrap:anywhere}
.pk-src code{color:var(--ink);font-size:11px;word-break:break-all}
.pk-close{float:inline-end;min-height:36px;min-width:36px;border:1px solid var(--rule);background:var(--surface);
  color:var(--ink);border-radius:8px;cursor:pointer}
.pk-suggest a{color:var(--link)}
.pk-card{margin:10px 0;padding:8px 10px;border:1px solid var(--rule);border-radius:8px;background:var(--surface)}
.pk-card h3{font-size:14px;margin:0 0 6px}
.pk-card dl{display:grid;grid-template-columns:1fr auto;gap:2px 12px;margin:0}
.pk-card dt{color:var(--muted)}
.pk-card dd{margin:0;font-weight:600;font-variant-numeric:tabular-nums}
"""

PATH_JS = r"""
(function () {
  'use strict';
  var QSTORE = 'tc-quests', PSTORE = 'tc-path';
  var S = { data: null, root: null, opts: {}, path: null, opener: null };
  /* mount() is idempotent: a page may re-mount the same (or another) element on every parish change. The
     previous mount's DOM listeners are removed through its AbortController, and the TCQuests 'found' listener
     (the engine has no off()) is bound once per page and always renders the CURRENT mount. */
  var AC = null, FOUND_BOUND = false;
  function unmount() { if (AC) { AC.abort(); AC = null; } }
  var EN = {
    choose: 'Choose a path', note: 'Paths are suggestions: every station is open from every path, and you can switch at any time.',
    launch: 'Launch', close: 'Close', suggested: 'Suggested first (never a lock):', source: 'Source:',
    found: 'visited', of: 'of', noLaunch: 'No launch link:',
    region: 'Region card', badges: 'Badges earned', borders: 'Borders crossed', rides: 'Rides (land, water)',
    guides: 'Guide talked to', trade: 'Trade path', k12: 'K-12 path', explorer: 'Explorer / free play', local: 'Counted on this device only, from your own play. There is no leaderboard: no server, no accounts.'
  };
  /* No region leaderboard, by design: there is no server and there are no accounts, so play is never sent
     anywhere or ranked against anyone. The region card below counts this device's own play state only. */
  function L(k) { return (S.opts.labels && Object.prototype.hasOwnProperty.call(S.opts.labels, k)) ? S.opts.labels[k] : EN[k]; }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function href(h) { return (S.opts.hrefPrefix || '') + String(h).replace(/^web\//, ''); }
  function stationById(id) {
    for (var i = 0; i < S.data.stations.length; i++) if (S.data.stations[i].id === id) return S.data.stations[i];
    throw new Error('pathkit: no station ' + id);
  }
  function playState() {
    if (window.TCQuests && typeof window.TCQuests.state === 'function') return window.TCQuests.state();
    try { var raw = window.localStorage.getItem(QSTORE); var v = raw ? JSON.parse(raw) : null;
      return v && typeof v === 'object' ? v : { found: {}, done: {} }; } catch (e) { return { found: {}, done: {} }; }
  }
  function stepQuest(pathId, step) { return pathId === 'explorer' ? step : stationById(step).treasure; }
  function progress() {
    var st = playState(), found = st.found || {}, done = st.done || {}, out = {};
    S.data.paths.forEach(function (p) {
      var n = 0;
      p.steps.forEach(function (s) { var q = stepQuest(p.id, s); if (q in found || q in done) n++; });
      out[p.id] = { found: n, total: p.steps.length };
    });
    return out;
  }
  function region() {
    var st = playState(), got = Object.assign({}, st.found || {}, st.done || {}), R = S.data.region;
    var n = function (ids) { return ids.filter(function (i) { return i in got; }).length; };
    return {
      badges: { got: n(R.badges), total: R.badges.length },
      borders: { got: n(R.borders.map(function (b) { return b.id; })), total: R.borders.length },
      rides: { got: n(R.rides), total: R.rides.length },
      guides: { got: n([R.guide]), total: 1 },
      arrived: R.arrive in got
    };
  }
  function card() {
    var r = region(), row = function (k) {
      return '<dt>' + esc(L(k)) + '</dt><dd>' + r[k].got + ' ' + esc(L('of')) + ' ' + r[k].total + '</dd>';
    };
    return '<section class="pk-card" aria-labelledby="pk-card-h"><h3 id="pk-card-h">' + esc(L('region')) + ': ' +
      esc(S.data.name) + '</h3><dl>' + row('badges') + row('borders') + row('rides') + row('guides') +
      '</dl><p class="pk-note">' + esc(L('local')) + '</p></section>';
  }
  function ring(f, t) {
    var r = 14, c = 2 * Math.PI * r, frac = t ? f / t : 0;
    return '<svg class="pk-ring" viewBox="0 0 34 34" aria-hidden="true"><circle class="pk-track" cx="17" cy="17" r="' + r +
      '" fill="none" stroke-width="4"/><circle class="pk-fill" cx="17" cy="17" r="' + r + '" fill="none" stroke-width="4"' +
      ' stroke-dasharray="' + (c * frac).toFixed(2) + ' ' + c.toFixed(2) + '" transform="rotate(-90 17 17)"/>' +
      '<text x="17" y="20" text-anchor="middle">' + Math.round(frac * 100) + '</text></svg>';
  }
  function render() {
    var d = S.data, pr = progress(), st = playState(), got = Object.assign({}, st.found || {}, st.done || {});
    var cur = null;
    d.paths.forEach(function (p) { if (p.id === S.path) cur = p; });
    var h = '<h2 id="pk-h">' + esc(L('choose')) + '</h2><div class="pk-choose" role="radiogroup" aria-labelledby="pk-h">';
    d.paths.forEach(function (p) {
      var on = p.id === S.path;
      h += '<button type="button" role="radio" data-pk-path="' + esc(p.id) + '" aria-checked="' + on + '" tabindex="' + (on ? 0 : -1) +
        '">' + ring(pr[p.id].found, pr[p.id].total) + '<span>' + esc(L(p.id)) + ' <span class="pk-count">' + pr[p.id].found +
        ' ' + esc(L('of')) + ' ' + pr[p.id].total + '</span></span></button>';
    });
    h += '</div><p class="pk-note">' + esc(L('note')) + ' ' + esc(d.honesty.play) + '</p>' + card() +
      '<ol class="pk-steps" aria-label="' + esc(L(cur.id)) + '">';
    cur.steps.forEach(function (s) {
      var q = stepQuest(cur.id, s), mark = q in got ? '<span class="pk-got" aria-label="' + esc(L('found')) + '">&#10003;</span>' : '';
      if (cur.id === 'explorer') {
        h += '<li><b>' + esc(d.steps[s].title) + '</b>' + mark + '<div class="pk-note">' + esc(d.steps[s].hint) + '</div></li>';
      } else {
        var t = stationById(s);
        h += '<li><button type="button" data-pk-open="' + esc(s) + '"><span class="pk-layer">' + esc(d.layers[t.layer]) + '</span>' +
          esc(t.title) + '</button>' + mark + '</li>';
      }
    });
    h += '</ol><div class="pk-panel" role="region" aria-live="polite" hidden></div>';
    S.root.innerHTML = h;
  }
  function panel(st) {
    var d = S.data, el = S.root.querySelector('.pk-panel'), h = '';
    h += '<button type="button" class="pk-close" data-pk-close aria-label="' + esc(L('close')) + '">&times;</button>';
    h += '<h3 id="pk-st-h" tabindex="-1"><span class="pk-layer">' + esc(d.layers[st.layer]) + '</span>' + esc(st.title) + '</h3>';
    if (st.launch.href) h += '<p><a class="pk-go" href="' + esc(href(st.launch.href)) + '">' + esc(L('launch')) + '</a></p>';
    else h += '<p class="pk-why">' + esc(L('noLaunch')) + ' ' + esc(st.launch.why) + '</p>';
    if (st.suggests.length) {
      h += '<p class="pk-suggest">' + esc(L('suggested')) + ' ' + st.suggests.map(function (lid) {
        return '<a href="' + esc(href('web/trade_craft_lessons.html#lesson-' + lid)) + '">' + esc(d.lessons[lid]) + '</a>';
      }).join(', ') + '</p>';
    }
    h += '<p class="pk-src">' + esc(L('source')) + ' <code>' + esc(st.ref.source) + '</code></p>';
    h += '<p class="pk-prov">' + esc(d.honesty.placement) + (st.layer === 'k12-unit' ? ' ' + esc(d.honesty.k12) : '') +
      (st.layer === 'lesson' ? ' ' + esc(d.honesty.lessons) : '') + '</p>';
    el.innerHTML = h;
    el.hidden = false;
    el.setAttribute('aria-labelledby', 'pk-st-h');
    el.querySelector('#pk-st-h').focus();
  }
  function open(id) {
    var st = stationById(id);
    S.opener = id;   /* the step button is re-rendered below; focus returns to its successor on close */
    if (window.TCQuests && typeof window.TCQuests.find === 'function') window.TCQuests.find(st.treasure);
    render();
    panel(st);
    if (typeof S.opts.onStation === 'function') S.opts.onStation(st);
    return st;
  }
  function close() {
    var el = S.root.querySelector('.pk-panel');
    if (el) { el.hidden = true; el.innerHTML = ''; }
    var back = S.opener ? S.root.querySelector('[data-pk-open="' + S.opener + '"]') : null;
    if (!back) back = S.root.querySelector('[aria-checked="true"]');
    if (back) back.focus();
  }
  function select(pid, focus) {
    var ok = S.data.paths.some(function (p) { return p.id === pid; });
    if (!ok) throw new Error('pathkit: no path ' + pid);
    S.path = pid;
    try { window.localStorage.setItem(PSTORE, pid); } catch (e) { /* storage unavailable: the choice lasts this visit */ }
    render();
    if (focus) S.root.querySelector('[data-pk-path="' + pid + '"]').focus();
    if (typeof S.opts.onPath === 'function') S.opts.onPath(pid);
  }
  function mount(root, data, opts) {
    unmount();
    AC = new AbortController();
    var sig = { signal: AC.signal };
    S.root = root; S.data = data; S.opts = opts || {}; S.opener = null;
    root.classList.add('pk');
    var saved = null;
    try { saved = window.localStorage.getItem(PSTORE); } catch (e) { saved = null; }
    S.path = data.paths.some(function (p) { return p.id === saved; }) ? saved : data.paths[0].id;
    render();
    root.addEventListener('click', function (e) {
      var t = e.target.closest('[data-pk-path],[data-pk-open],[data-pk-close]');
      if (!t) return;
      if (t.hasAttribute('data-pk-path')) select(t.getAttribute('data-pk-path'), true);
      else if (t.hasAttribute('data-pk-open')) open(t.getAttribute('data-pk-open'));
      else close();
    }, sig);
    root.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !root.querySelector('.pk-panel').hidden) { e.preventDefault(); close(); return; }
      var t = e.target.closest('[data-pk-path]');
      if (!t) return;
      var ids = S.data.paths.map(function (p) { return p.id; }), i = ids.indexOf(t.getAttribute('data-pk-path'));
      var k = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
      if (document.dir === 'rtl' && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) k = -k;
      if (e.key === 'Home') k = -i; if (e.key === 'End') k = ids.length - 1 - i;
      if (k === undefined) return;
      e.preventDefault();
      select(ids[(i + k + ids.length) % ids.length], true);
    }, sig);
    if (!FOUND_BOUND && window.TCQuests && typeof window.TCQuests.on === 'function') {
      FOUND_BOUND = true;
      window.TCQuests.on('found', function () {
        if (!S.root) return;
        var p = S.root.querySelector('.pk-panel'); if (p && p.hidden) render();
      });
    }
    return window.TCPaths;
  }
  window.TCPaths = { mount: mount, select: function (p) { select(p, false); }, open: open, close: close, progress: progress, region: region,
    unmount: function () { unmount(); S.root = null; } };
})();
"""
