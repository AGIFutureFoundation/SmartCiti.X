"""robotics/claw/panel.py - the training-operations panel of the Robotics lab page (the Omega Claw agents, the arena
tournament, the trainable dataset and the Coach). web/build_robotics.py imports this inside its anchored block.

Everything shown is read from robotics/claw/registry/claw.json (quoted lines, measured numbers) and the registries it
points at. The Coach runs in the page on the learner's OWN recorded episodes (the training recorder's localStorage
log, read only); nothing is sent anywhere and nothing is recorded by this panel. The page JS lifts the pure
TRAIN_OPS_CORE block of robotics/claw/core.mjs byte-for-byte (only `export ` is dropped), so the page and the node
suite score a run with the same code. Speech: the device's own speechSynthesis, on-device English voices only, on a
click only; classroom mode starts muted with the Omega Hive classroom volume and rate cap. Page markers are neutral
(train-ops / TRAIN_OPS); no team codename is emitted.
"""
import html
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
E = lambda s: html.escape(str(s), quote=True)


class TrainOpsError(Exception):
    pass


def _need(cond, msg):
    if not cond:
        raise TrainOpsError('train-ops panel: ' + msg)


def _load(rel):
    p = ROOT / rel
    _need(p.is_file(), f'missing {rel}')
    return json.loads(p.read_text())


KEYS = ['robo.to.h', 'robo.to.note', 'robo.to.mute', 'robo.to.unmute', 'robo.to.speak', 'robo.to.v.ok', 'robo.to.v.none',
        'robo.to.v.muted', 'robo.to.src', 'robo.to.h.agents', 'robo.to.h.tour', 'robo.to.tour.note', 'robo.to.c.policy',
        'robo.to.c.kind', 'robo.to.c.runs', 'robo.to.c.cap', 'robo.to.c.contacts', 'robo.to.c.pair', 'robo.to.c.only1',
        'robo.to.c.only2', 'robo.to.c.p', 'robo.to.c.ci', 'robo.to.h.data', 'robo.to.data.note', 'robo.to.c.scheme',
        'robo.to.instr', 'robo.to.card', 'robo.to.export', 'robo.to.h.coach', 'robo.to.coach.note', 'robo.to.coach.pick',
        'robo.to.coach.none', 'robo.to.coach.class', 'robo.to.m.smooth', 'robo.to.m.eff', 'robo.to.m.contacts',
        'robo.to.m.time', 'robo.to.next', 'robo.to.lesson', 'robo.to.ladder']


def keys():
    return list(KEYS)


def core_js():
    src = (HERE / 'core.mjs').read_text()
    a, b = src.find('/* TRAIN_OPS_CORE:BEGIN */'), src.find('/* TRAIN_OPS_CORE:END */')
    _need(a >= 0 and b > a, 'the TRAIN_OPS_CORE markers are missing from robotics/claw/core.mjs')
    block = src[a:b + len('/* TRAIN_OPS_CORE:END */')]
    _need(block.count('export function trainOpsCore(') == 1 and block.count('export ') == 1, 'the core block must export exactly trainOpsCore')
    return block.replace('export function trainOpsCore(', 'function trainOpsCore(')


def data():
    R = _load('robotics/claw/registry/claw.json')
    REG = _load('robotics/registry/robotics.json')
    HIVE = _load('hive/registry/hive.json')
    T = R['tournament']
    ds = R['dataset']
    # the agents with every line as it is said: quoted text, or the template filled with build-time MEASURED numbers
    filled = {('scheduler', 'queue'): T['said']['scheduler'], ('referee', 'verdict'): T['said']['referee'],
              ('evaluator', 'paired'): ' '.join(T['said']['evaluator'][k] for k in sorted(T['said']['evaluator'])),
              ('steward', 'counts'): None}
    agents = []
    for a in R['agents']:
        lines = []
        for l in a['lines']:
            if l['kind'] == 'quoted':
                lines.append({'id': l['id'], 'text': l['text'], 'source': l['source'], 'kind': 'quoted', 'k12': l['k12']})
            else:
                lines.append({'id': l['id'], 'template': l['template'], 'slots': l['slots'], 'source': l['source'], 'kind': 'template',
                              'said': filled.get((a['role'], l['id'])), 'k12': l['k12']})
        agents.append({'id': a['id'], 'role': a['role'], 'name': a['name'], 'glyph': a['glyph'], 'job': a['job'],
                       'traits': a['personality']['traits'], 'style': a['personality']['style'],
                       'pitch': a['voice']['pitch'], 'rate': a['voice']['rate'], 'k12': a['k12'], 'lines': lines})
    # the Data Steward's count line: AUTHORED template, measured dataset numbers (rendered in the page by the core)
    steward_vals = {'samples': ds['samples'], 'episodes': ds['episodes'], 'duplicates': ds['duplicates'], 'revoked': 0}
    instr = []
    for src in ds['instructions']:
        rel, path = src.split('#', 1)
        instr.append({'source': src})
    # the registries the core's coach() quotes from, cut down to the paths it reads
    lessons = _load('lessons/registry/lessons.json')['lessons']
    lesson_ids = sorted({b['lesson'].split('["')[1].split('"]')[0] for b in _load('robotics/claw/authored/claw.json')['instructions'].values() if b['lesson']})
    envs = {}
    for e in REG['envs'].values():
        if e['runner'] != 'robokit':
            continue
        envs[e['id']] = {k: e[k] for k in ('id', 'name', 'objects', 'termination', 'episode_cap', 'reward', 'action', 'curriculum', 'seeds')}
    bench = {k: {'levels': {l: {'success': v['success'], 'runs': v['runs']} for l, v in b['levels'].items()}} for k, b in REG['reference_benchmark']['per_env'].items()}
    files = {
        'robotics/registry/robotics.json': {'envs': envs, 'reference_benchmark': {'per_env': bench}},
        'robotics/claw/authored/claw.json': {'coach': R['coach'], 'instructions': _load('robotics/claw/authored/claw.json')['instructions'],
                                             'families': R['families'], 'agents': _load('robotics/claw/authored/claw.json')['agents']},
        'lessons/registry/lessons.json': {'lessons': {i: {'title': lessons[i]['title']} for i in lesson_ids}},
    }
    # instruction texts: quoted here from the registry index (the build checked each against its source)
    for i in instr:
        rel, path = i['source'].split('#', 1)
    tasks_reg = _load('tasks/registry/tasks.json')
    texts = {}
    for i in instr:
        rel, path = i['source'].split('#', 1)
        if rel == 'robotics/registry/robotics.json':
            env = path.split('"]')[0].split('["')[1]
            texts[i['source']] = REG['envs'][env]['brief']
        elif rel == 'tasks/registry/tasks.json':
            tid = path.split('[id=')[1].split(']')[0]
            hit = [t for t in tasks_reg['tasks'] if t['id'] == tid]
            _need(len(hit) == 1, f'task {tid} not found')
            texts[i['source']] = hit[0][path.rsplit('.', 1)[1]]
        else:
            raise TrainOpsError('train-ops panel: no reader for instruction source ' + i['source'])
        i['text'] = texts[i['source']]
    return {
        'agents': agents, 'steward_vals': steward_vals, 'bounds': {'pitch': HIVE['bounds']['pitch'], 'rate': HIVE['bounds']['rate'], 'volume': HIVE['bounds']['volume']},
        'k12_volume': HIVE['bounds']['k12_volume'], 'k12_rate_max': HIVE['bounds']['k12_rate_max'], 'hold_words': HIVE['k12']['hold_words'],
        'tournament': {'reference': T['reference'], 'policies': T['policies'], 'per_policy': T['per_policy'], 'paired': T['paired'], 'queue_size': T['queue_size']},
        'dataset': {k: ds[k] for k in ('samples', 'episodes', 'duplicates', 'success', 'per_task', 'per_family', 'splits', 'splits_def', 'balance_ratio', 'balance_max', 'policy_version', 'digest')},
        'instructions': instr, 'card': R['card'], 'reference_paths': R['reference_paths'], 'files': files,
        'stamp': R['source_stamp'], 'trained_by_this_pack': R['counts']['trained_by_this_pack'], 'agent_models': R['counts']['models'],
    }


CSS = '''
#train-ops .to-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
#train-ops .to-agent{border:1px solid var(--tc-line);border-radius:8px;padding:12px;background:var(--tc-raised);min-inline-size:0}
#train-ops .to-agent h4{margin:0 0 4px;font-size:16px;text-transform:none;letter-spacing:0;color:var(--tc-ink)}
#train-ops .to-lines{margin:6px 0 0;padding-inline-start:18px;font-size:14px}
#train-ops .to-lines small{display:block;color:var(--tc-muted);font:11px ui-monospace,monospace;overflow-wrap:anywhere}
#train-ops button,#train-ops select{min-block-size:44px;min-inline-size:44px;font:inherit;color:var(--tc-ink);background:var(--tc-raised);border:1px solid var(--tc-line);border-radius:8px;padding:0 12px}
#train-ops button[aria-pressed="true"]{background:var(--tc-amber);color:var(--tc-amber-ink,#12181B)}
#train-ops select{max-inline-size:calc(100vw - 80px);text-overflow:ellipsis}
#train-ops .to-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 8px}
#train-ops .to-coach-out{border-inline-start:3px solid var(--tc-amber);padding:4px 12px;margin:8px 0}
#train-ops details summary{cursor:pointer;min-block-size:44px;display:flex;align-items:center}
'''


def panel_html(T, EN):
    D = data()
    tr = D['tournament']
    pol = ''.join(f'<tr><td>{E(p["id"])}</td><td><span class="tag">{E(p["provenance"])}</span></td><td>{tr["per_policy"][p["id"]]["runs"]}</td>'
                  f'<td>{tr["per_policy"][p["id"]]["success"]}</td><td>{tr["per_policy"][p["id"]]["cap"]}</td><td>{tr["per_policy"][p["id"]]["collisions"]}</td>'
                  f'<td>{tr["per_policy"][p["id"]]["mean_return"]}</td></tr>' for p in tr['policies'])
    pairs = ''.join(f'<tr><td>{E(k)}</td><td>{v["pairs"]}</td><td>{v["a_only"]}</td><td>{v["b_only"]}</td><td>{v["p"]}</td>'
                    f'<td>{v["mean_return_diff"]} [{v["ci95"][0]}, {v["ci95"][1]}]</td></tr>' for k, v in sorted(tr['paired'].items()))
    ds = D['dataset']
    splits = ''.join(f'<tr><td>{E(s)}</td><td>{E(json.dumps(ds["splits_def"][s]))}</td><td>{ds["splits"][s].get("train", 0)}</td><td>{ds["splits"][s].get("val", 0)}</td><td>{ds["splits"][s].get("test", 0)}</td></tr>' for s in sorted(ds['splits']))
    tasks = ' · '.join(f'{E(k)} {v}' for k, v in sorted(ds['per_task'].items()))
    instr = ''.join(f'<li>“{E(i["text"])}”<small>{E(i["source"])}</small></li>' for i in D['instructions'])
    card = E(D['card'])
    agents = ''.join(
        f'<article class="to-agent" data-agent="{E(a["id"])}"><h4><span aria-hidden="true">{E(a["glyph"])}</span> {E(a["name"])}</h4>'
        f'<p class="muted">{E(a["job"])} · {E(", ".join(a["traits"]))}</p><p class="muted"><i>{E(a["style"])}</i></p>'
        f'<button type="button" data-to-speak="{E(a["id"])}">{T("robo.to.speak")}</button>'
        f'<ul class="to-lines" data-to-lines="{E(a["id"])}"></ul></article>' for a in D['agents'])
    stats = (f'<div class="st"><dt>{T("robo.to.c.runs")}</dt><dd data-to="samples">{ds["samples"]}</dd></div>'
             f'<div class="st"><dt>{T("robo.success")}</dt><dd data-to="success">{ds["success"]} / {ds["samples"]}</dd></div>'
             f'<div class="st"><dt>{T("robo.to.c.scheme")}</dt><dd data-to="balance">{ds["balance_ratio"]}</dd></div>')
    return f'''<section class="box" aria-labelledby="to-h" id="train-ops" data-train-ops>
<h2 id="to-h" data-i18n="robo.to.h">{E(EN["robo.to.h"])}</h2>
<p class="muted">{T("robo.to.note")}</p>
<div class="to-row"><button type="button" id="to-mute" aria-pressed="false">{T("robo.to.mute")}</button> <span class="muted" id="to-voice" aria-live="polite"></span></div>
<h3 data-i18n="robo.to.h.agents">{E(EN["robo.to.h.agents"])}</h3>
<div class="to-grid">{agents}</div>
<h3 data-i18n="robo.to.h.tour">{E(EN["robo.to.h.tour"])}</h3>
<p class="muted">{T("robo.to.tour.note")} <b data-to="queue">{tr["queue_size"]}</b></p>
<div class="tw"><table id="to-policies"><thead><tr><th>{T("robo.to.c.policy")}</th><th>{T("robo.to.c.kind")}</th><th>{T("robo.to.c.runs")}</th><th>{T("robo.success")}</th><th>{T("robo.to.c.cap")}</th><th>{T("robo.to.c.contacts")}</th><th>{T("robo.return")}</th></tr></thead><tbody>{pol}</tbody></table></div>
<div class="tw"><table id="to-paired"><thead><tr><th>{T("robo.to.c.pair")}</th><th>{T("robo.to.c.runs")}</th><th>{T("robo.to.c.only1")}</th><th>{T("robo.to.c.only2")}</th><th>{T("robo.to.c.p")}</th><th>{T("robo.to.c.ci")}</th></tr></thead><tbody>{pairs}</tbody></table></div>
<h3 data-i18n="robo.to.h.data">{E(EN["robo.to.h.data"])}</h3>
<p class="muted">{T("robo.to.data.note")}</p>
<dl class="stats">{stats}</dl>
<p class="muted" data-to="tasks">{tasks}</p>
<div class="tw"><table id="to-splits"><thead><tr><th>{T("robo.to.c.scheme")}</th><th></th><th>train</th><th>val</th><th>test</th></tr></thead><tbody>{splits}</tbody></table></div>
<h4>{T("robo.to.instr")}</h4><ul class="to-lines">{instr}</ul>
<details><summary>{T("robo.to.card")}</summary><pre class="card-pre" id="to-card">{card}</pre></details>
<p class="muted">{T("robo.to.export")} <code>node robotics/claw/export.mjs --out DIR</code></p>
<h3 data-i18n="robo.to.h.coach">{E(EN["robo.to.h.coach"])}</h3>
<p class="muted">{T("robo.to.coach.note")}</p>
<p class="muted" id="to-class" hidden>{T("robo.to.coach.class")}</p>
<div class="to-row"><label>{T("robo.to.coach.pick")} <select id="to-run"></select></label></div>
<p class="muted" id="to-none">{T("robo.to.coach.none")}</p>
<div id="to-coach" hidden><dl class="stats"><div class="st"><dt>{T("robo.to.m.smooth")}</dt><dd data-m="smooth">-</dd></div>
<div class="st"><dt>{T("robo.to.m.eff")}</dt><dd data-m="eff">-</dd></div><div class="st"><dt>{T("robo.to.m.contacts")}</dt><dd data-m="collisions">-</dd></div>
<div class="st"><dt>{T("robo.to.m.time")}</dt><dd data-m="time">-</dd></div></dl>
<div class="to-coach-out"><p id="to-say"></p><p class="muted"><span>{T("robo.to.next")}</span> <b id="to-next"></b></p><p class="muted" id="to-lesson-row" hidden><span>{T("robo.to.lesson")}</span> <b id="to-lesson"></b></p><p class="muted" id="to-said"></p></div></div>
<p class="muted"><span>{T("robo.to.ladder")}</span> <span id="to-ladder"></span></p>
<p class="muted">robotics/claw/registry/claw.json · stamp <code data-to-stamp>{E(D["stamp"])}</code> · models behind the agents {D["agent_models"]} · models trained by this panel {D["trained_by_this_pack"]}</p>
</section>'''


JS = r'''/* TRAIN_OPS panel: agents, voice on a click, the Coach on the learner's own recorded runs (read only, on this device) */
(function () {
  'use strict';
  var D = JSON.parse(document.getElementById('train-ops-data').textContent);
  var root = document.getElementById('train-ops'); if (!root) return;
  var P = window.__roboPage || {}, I = JSON.parse(document.getElementById('robo-i18n').textContent);
  var loc = P.locale && I[P.locale] ? P.locale : 'en', S = I[loc].strings;
  var t = function (k) { if (typeof S[k] !== 'string') throw new Error('train-ops i18n: ' + loc + ' has no ' + k); return S[k]; };
  var classroom = !!P.classroom;
  var core = trainOpsCore({ load: function (rel) { if (!D.files[rel]) throw new Error('train-ops: ' + rel + ' is not embedded'); return D.files[rel]; },
    sha256: function () { throw new Error('train-ops: no hashing in the page'); } });
  var hold = classroom ? D.hold_words : [];
  var held = function (s) { return hold.some(function (w) { return new RegExp('\\b' + w + '\\b', 'i').test(s); }); };
  /* lines, as each agent says them: quoted registry text, or an AUTHORED template filled with MEASURED numbers */
  function said(a, l) {
    if (l.kind === 'quoted') return l.text;
    if (l.said) return l.said;
    if (a.role === 'steward' && l.id === 'counts') return core.render(l, D.steward_vals);
    return null;
  }
  D.agents.forEach(function (a) {
    var ul = root.querySelector('[data-to-lines="' + a.id + '"]');
    a.lines.forEach(function (l) { var s = said(a, l); if (s === null || (classroom && (!l.k12 || held(s)))) return;
      var li = document.createElement('li'); li.textContent = s; var sm = document.createElement('small'); sm.textContent = l.source; li.appendChild(sm); ul.appendChild(li); });
  });
  /* VOICE: window.speechSynthesis, on-device English voices only, on a click only; classroom starts muted */
  var KEY = 'tc.trainops.muted', synth = window.speechSynthesis || null, muted;
  try { var sv = localStorage.getItem(KEY); muted = classroom ? sv !== '0' : sv === '1'; } catch (e) { muted = classroom; }
  function localVoice() { if (!synth) return null; var vs = []; try { vs = synth.getVoices() || []; } catch (e) { return null; }
    var m = vs.filter(function (v) { return v.localService && /^en/i.test(v.lang || ''); }); return m.length ? m[0] : null; }
  function voiceState() { var el = document.getElementById('to-voice'), b = document.getElementById('to-mute');
    b.setAttribute('aria-pressed', String(muted)); b.textContent = t(muted ? 'robo.to.unmute' : 'robo.to.mute');
    el.textContent = muted ? t('robo.to.v.muted') : (localVoice() ? t('robo.to.v.ok') : t('robo.to.v.none')); }
  function speak(a, texts) {
    if (muted || !synth) return 0; var v = localVoice(); if (!v) return 0;
    try { synth.cancel(); } catch (e) { /* nothing queued */ }
    texts.forEach(function (s) { var u = new SpeechSynthesisUtterance(s); u.voice = v; u.lang = v.lang;
      u.pitch = Math.min(D.bounds.pitch[1], Math.max(D.bounds.pitch[0], a.pitch));
      u.rate = Math.min(classroom ? D.k12_rate_max : D.bounds.rate[1], Math.max(D.bounds.rate[0], a.rate));
      u.volume = classroom ? D.k12_volume : D.bounds.volume; synth.speak(u); });
    return texts.length;
  }
  root.querySelectorAll('[data-to-speak]').forEach(function (b) { b.addEventListener('click', function () {
    var a = D.agents.filter(function (x) { return x.id === b.getAttribute('data-to-speak'); })[0];
    var ul = root.querySelector('[data-to-lines="' + a.id + '"]'), texts = [];
    ul.querySelectorAll('li').forEach(function (li) { texts.push(li.firstChild.textContent); });
    if (a.role === 'coach' && lastCoach) texts = lastCoach.slice();
    window.__trainOps.spoken = speak(a, texts); }); });
  document.getElementById('to-mute').addEventListener('click', function () { muted = !muted; if (muted && synth) { try { synth.cancel(); } catch (e) { /* idle */ } }
    try { localStorage.setItem(KEY, muted ? '1' : '0'); } catch (e) { /* not remembered */ } voiceState(); });
  if (synth && 'onvoiceschanged' in synth) synth.addEventListener('voiceschanged', voiceState);
  voiceState();
  /* COACH: the learner's own recorded world episodes, read from this browser's training log; nothing is written or sent */
  var ladder = D.files['robotics/claw/authored/claw.json'].coach.ladder, envs = D.files['robotics/registry/robotics.json'].envs;
  document.getElementById('to-ladder').textContent = ladder.map(function (e) { return envs[e].name; }).join(' → ');
  var runs = [];
  if (classroom) document.getElementById('to-class').hidden = false;
  else { try { var a0 = JSON.parse(localStorage.getItem(JSON.parse(document.getElementById('robo-data').textContent).train.storage.key)); if (Array.isArray(a0)) runs = a0.filter(function (e) {
    return e && e.kind === 'world-teleop' && e.actor === 'human' && envs[e.env] && Array.isArray(e.samples) && D.reference_paths[e.env].rows.some(function (r) { return r[0] === e.seed; }); }); } catch (e) { runs = []; } }
  var sel = document.getElementById('to-run'), lastCoach = null;
  runs.forEach(function (e, i) { var o = document.createElement('option'); o.value = String(i); o.textContent = (e.t || '') + ' · ' + envs[e.env].name + ' · seed ' + e.seed; sel.appendChild(o); });
  document.getElementById('to-none').hidden = runs.length > 0; sel.disabled = !runs.length;
  function show(i) {
    var e = runs[i], env = envs[e.env], ref = D.reference_paths[e.env], row = ref.rows.filter(function (r) { return r[0] === e.seed; })[0];
    var m = core.metrics(env, e, { path_m: row[1], time_s: row[2], success: !!row[3] });
    var c = core.coach(D.files['robotics/registry/robotics.json'], D.files['robotics/claw/authored/claw.json'], e.env, ref.level, m, classroom, D.hold_words);
    var q = function (k, v) { root.querySelector('[data-m="' + k + '"]').textContent = v; };
    q('smooth', m.smooth); q('eff', m.eff < 0 ? '-' : m.eff); q('collisions', m.collisions); q('time', m.time < 0 ? '-' : m.time + ' s');
    var coachA = D.agents.filter(function (a) { return a.role === 'coach'; })[0];
    var l1 = coachA.lines.filter(function (l) { return l.id === 'metrics'; })[0], l2 = coachA.lines.filter(function (l) { return l.id === 'finish'; })[0];
    var lines = [core.render(l1, { smooth: m.smooth, collisions: m.collisions })];
    if (m.success && m.eff >= 0) lines.push(core.render(l2, { time: m.time, eff: m.eff }));
    document.getElementById('to-said').textContent = lines.join(' ');
    document.getElementById('to-say').textContent = c.say ? c.say.text : '';
    document.getElementById('to-next').textContent = c.next.env_name + ' · ' + c.next.level + ' ' + c.next.level_name;
    document.getElementById('to-lesson-row').hidden = !c.next.lesson; document.getElementById('to-lesson').textContent = c.next.lesson ? c.next.lesson.text : '';
    document.getElementById('to-coach').hidden = false;
    lastCoach = lines.concat(c.say ? [c.say.text] : []);
    window.__trainOps.last = { metrics: m, coach: c };
  }
  sel.addEventListener('change', function () { show(+sel.value); });
  window.__trainOps = { core: core, runs: runs.length, classroom: classroom, muted: function () { return muted; }, show: show, spoken: 0, last: null };
  if (runs.length) show(0);
})();
'''


def scripts():
    """the three page scripts: the embedded data, the lifted core, the panel"""
    raw = json.dumps(data(), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return (f'<script type="application/json" id="train-ops-data">{raw}</script>\n'
            f'<script id="train-ops-core">{core_js()}</script>\n<script id="train-ops-js">{JS}</script>')
