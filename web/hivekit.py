"""hivekit: the Omega Hive's shared pieces - the compact data a page embeds, the avatar portrait, the on-device voice
and the deterministic council router. Used by web/build_hive.py (the Hive page) and by the anchored hive blocks in the
3D campus and parish world builders, so every surface speaks with the same voice rule and routes with the same rule.

Rules this file enforces, so a page cannot drift from them:
  - SCRIPTED: a line is a quote of the registry text and carries its source path; the kit has no way to compose one.
  - VOICE: window.speechSynthesis only, on-device voices only (SpeechSynthesisVoice.localService), English because the
    lines are quoted in English. speak() is called only from a click handler; nothing here speaks on load, on a timer
    or on a hover. A mute switch silences every surface and is remembered on this device (fails to muted when
    storage is blocked in classroom mode, and to the page default otherwise). If the device has no on-device English
    voice the kit says so and speaks nothing - it never falls back to a network voice.
  - COUNCIL: HiveCore.council(data, question, opts) is pure (no DOM, no clock, no randomness): content words of the
    question are matched against every line's content words; each agent offers its best line; agents are ranked by
    score, then by id; at most five sit, lines already said by a higher-ranked agent are skipped, and fewer than three
    matches is reported as such rather than padded. At most two seats go to one kind of agent (advisor, crew role,
    world guide) unless that would leave fewer than three. web/test_hive.mjs runs it headless.
"""
import hashlib
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
E = lambda s: html.escape(str(s), quote=True)


class HiveKitError(Exception):
    pass


def hive_registry():
    p = ROOT / 'hive/registry/hive.json'
    if not p.exists():
        raise HiveKitError('hivekit: hive/registry/hive.json is missing - run python3 hive/build.py')
    return json.loads(p.read_text(encoding='utf-8'))


def hive_data(reg=None, kinds=None, ids=None, with_cfg=True):
    """The compact block a page embeds: unique line texts once, agents pointing at them."""
    reg = reg or hive_registry()
    texts, tidx, agents = [], {}, []
    for a in reg['agents']:
        if kinds and a['kind'] not in kinds:
            continue
        if ids is not None and a['id'] not in ids:
            continue
        lines = []
        for ln in a['lines']:
            key = (ln['text'], ln['source'])
            if key not in tidx:
                tidx[key] = len(texts)
                texts.append([ln['text'], ln['source']])
            row = {'t': tidx[key], 'k': ln['kind'], 'id': ln['id'], 'safe': 1 if ln['k12'] else 0}
            if 'ask' in ln:
                row['ask'] = ln['ask']
            lines.append(row)
        px = a['avatar']['proxy']
        row = {'id': a['id'], 'name': a['name'], 'kind': a['kind'], 'glyph': a['glyph'],
               'k12': 1 if a['k12'] else 0, 'pitch': a['voice']['pitch'], 'rate': a['voice']['rate'], 'lines': lines}
        # AVATAR w17: the opening line (an index into `lines`) and the idle gesture, both by the trait rule below
        _bh = behaviour(a)
        row.update({'o': _bh['open'], 'o12': _bh['open_k12'], 'g': _bh['gesture']})
        if with_cfg:      # the 3D worlds dress a figure from it; the Hive page draws portraits server-side instead
            row.update({'role': a['role'], 'traits': a['personality']['traits'], 'cfg': a['avatar']['cfg'],
                        'character': a['avatar']['character'], 'px': {k: (v['hex'] if v else None) for k, v in px.items()}})
        agents.append(row)
    return {'stamp': reg['source_stamp'], 'schema': reg['schema'], 'bounds': reg['bounds'],
            'k12_volume': reg['bounds']['k12_volume'], 'k12_rate_max': reg['bounds']['k12_rate_max'],
            'texts': texts, 'agents': agents}


def voice_data(ids, reg=None):
    """Voices only, for a world page that already embeds the lines it shows (the parish page's npcs.json block): the
    page finds the line in its own data and the hive supplies how it is spoken and whether classroom mode holds it."""
    reg = reg or hive_registry()
    rows = [{'id': a['id'], 'name': a['name'], 'kind': a['kind'], 'k12': 1 if a['k12'] else 0, 'pitch': a['voice']['pitch'],
             'rate': a['voice']['rate'], 'held': [ln['id'] for ln in a['lines'] if not ln['k12']]}
            for a in reg['agents'] if a['id'] in ids]
    return {'stamp': reg['source_stamp'], 'schema': reg['schema'], 'bounds': reg['bounds'],
            'k12_volume': reg['bounds']['k12_volume'], 'k12_rate_max': reg['bounds']['k12_rate_max'], 'agents': rows,
            'labels': world_labels()}


def portrait_svg(agent, size=64):
    """A small front portrait drawn from the avatar proxy colours (avatars/ locker hex values). Decorative: the name
    beside it is the label, so the SVG is aria-hidden and carries no <title> or <text>."""
    px = agent['avatar']['proxy']
    sx, sy, _ = agent['avatar']['scale']['xyz']
    w = round(26 * sx, 1)
    x0 = round(32 - w / 2, 1)
    torso_h = round(20 * sy, 1)
    parts = [f'<rect x="{x0 + 2}" y="{38 + torso_h - 6}" width="{round(w / 2 - 3, 1)}" height="{round(70 - 38 - torso_h + 6, 1)}" fill="{px["legs"]["hex"]}"/>',
             f'<rect x="{32 + 1}" y="{38 + torso_h - 6}" width="{round(w / 2 - 3, 1)}" height="{round(70 - 38 - torso_h + 6, 1)}" fill="{px["legs"]["hex"]}"/>',
             f'<rect x="{x0}" y="32" width="{w}" height="{torso_h}" rx="5" fill="{px["torso"]["hex"]}"/>']
    if px.get('vest'):
        parts.append(f'<path d="M{x0 + 3} 33 h6 v{torso_h - 2} h-6z M{x0 + w - 9} 33 h6 v{torso_h - 2} h-6z" fill="{px["vest"]["hex"]}"/>')
    parts.append(f'<circle cx="32" cy="22" r="10" fill="{px["head"]["hex"]}"/>')
    if px.get('hat'):
        parts.append(f'<path d="M20 20 a12 11 0 0 1 24 0 h3 v3 h-30 v-3z" fill="{px["hat"]["hex"]}"/>')
    elif px.get('hair'):
        parts.append(f'<path d="M22 19 a10 9 0 0 1 20 0 z" fill="{px["hair"]["hex"]}"/>')
    return (f'<svg class="hv-face" viewBox="0 0 64 72" width="{size}" height="{round(size * 72 / 64)}" aria-hidden="true" '
            f'focusable="false">{"".join(parts)}</svg>')


HIVE_CSS = r'''
.hv-voicebar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}
.hv-btn{min-block-size:44px;min-inline-size:44px;font:inherit;color:var(--tc-ink);background:var(--tc-raised);border:1px solid var(--tc-line);border-radius:8px;padding:0 12px;cursor:pointer}
.hv-btn[aria-pressed="true"]{background:var(--tc-amber);color:var(--tc-amber-ink,#12181B)}
.hv-btn:focus-visible{outline:3px solid var(--tc-link);outline-offset:2px}
.hv-status{font-size:14px;color:var(--tc-muted);min-block-size:1.5em;overflow-wrap:anywhere}
.hv-face{flex:0 0 auto;background:var(--tc-raised);border-radius:8px}
'''

HIVE_JS = r'''
/* Omega Hive kit: pure council router + on-device voice. Lines are quotes; nothing here writes one. */
var HiveCore = (function () {
  'use strict';
  var STOP = {};
  ('the a an and or but if then than that this these those there here is are was were be been being am do does did done '
   + 'i me my mine we us our you your he she it its they them their what which who whom whose when where why how can could '
   + 'should would will shall may might must to of in on at by for from with without into onto about over under up down out '
   + 'off as so not no nor too very just only also any all each every some more most other such own same one two get got '
   + 'have has had having tell say said ask asked know want need like make let lets please').split(' ').forEach(function (w) { STOP[w] = 1; });
  function stem(w) {
    if (w.length > 5 && /ing$/.test(w)) return w.slice(0, -3);
    if (w.length > 4 && /ed$/.test(w)) return w.slice(0, -2);
    if (w.length > 4 && /es$/.test(w)) return w.slice(0, -2);
    if (w.length > 3 && /s$/.test(w) && !/ss$/.test(w)) return w.slice(0, -1);
    return w;
  }
  function words(t) {
    var m = String(t).toLowerCase().match(/[a-z]+/g) || [], out = [];
    for (var i = 0; i < m.length; i++) if (m[i].length > 2 && !STOP[m[i]]) out.push(stem(m[i]));
    return out;
  }
  function uniq(a) { var s = {}, o = []; for (var i = 0; i < a.length; i++) if (!s[a[i]]) { s[a[i]] = 1; o.push(a[i]); } return o; }
  /* council(data, question, {k12, max, min}) -> {asked, words, members:[{agent, line, hits, score}], short, none} */
  function council(data, question, opts) {
    opts = opts || {};
    var max = opts.max || 5, min = opts.min || 3, k12 = !!opts.k12;
    var q = uniq(words(question)), qs = {};
    q.forEach(function (w) { qs[w] = 1; });
    var cand = [], need = q.length <= 3 ? 1 : 2;   /* a line must share two words with a longer question, one with a short one */
    if (q.length) data.agents.forEach(function (a, ai) {
      if (k12 && !a.k12) return;
      var best = null;
      a.lines.forEach(function (ln, li) {
        if (k12 && !ln.safe) return;
        var lw = uniq(words(data.texts[ln.t][0] + ' ' + (ln.ask || ''))), hits = 0;
        for (var i = 0; i < lw.length; i++) if (qs[lw[i]]) hits++;
        if (hits < need) return;
        var score = hits / Math.sqrt(Math.max(4, lw.length));
        if (!best || score > best.score || (score === best.score && li < best.line)) best = { agent: ai, line: li, hits: hits, score: score };
      });
      if (best) cand.push(best);
    });
    cand.sort(function (x, y) {
      if (y.score !== x.score) return y.score - x.score;
      var ix = data.agents[x.agent].id, iy = data.agents[y.agent].id;
      return ix < iy ? -1 : ix > iy ? 1 : 0;
    });
    /* seats: at most two per kind (advisor, crew role, world guide) so a council is a mix; if that leaves fewer
       than `min`, the next-ranked candidates fill the seats regardless of kind. A line already said is never repeated. */
    var said = {}, members = [], perKind = {}, seated = {};
    function seat(i, capped) {
      var c = cand[i], a = data.agents[c.agent], t = a.lines[c.line].t;
      if (seated[i] || said[t] || (capped && (perKind[a.kind] || 0) >= 2)) return;
      said[t] = 1; seated[i] = 1; perKind[a.kind] = (perKind[a.kind] || 0) + 1; members.push(c);
    }
    for (var i = 0; i < cand.length && members.length < max; i++) seat(i, true);
    for (var j = 0; j < cand.length && members.length < min; j++) seat(j, false);
    members.sort(function (x, y) { return cand.indexOf(x) - cand.indexOf(y); });
    return { asked: String(question), words: q, members: members, short: members.length > 0 && members.length < min, none: members.length === 0 };
  }
  return { words: words, council: council, stem: stem };
})();

var HiveVoice = (function () {
  'use strict';
  var KEY = 'tc.hive.muted', synth = (typeof window !== 'undefined' && window.speechSynthesis) || null;
  var state = { muted: false, k12: false, data: null, onstate: null };
  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function init(data, opts) {
    state.data = data; state.k12 = !!(opts && opts.k12); state.onstate = (opts && opts.onstate) || null;
    var s = stored();
    /* classroom starts muted and stays muted until the class turns it on; elsewhere the remembered switch wins */
    state.muted = state.k12 ? s !== '0' : s === '1';
    return state.muted;
  }
  function setMuted(on) {
    state.muted = !!on;
    try { localStorage.setItem(KEY, on ? '1' : '0'); } catch (e) { /* not remembered */ }
    if (on) stop();
    return state.muted;
  }
  function localVoice() {
    if (!synth) return null;
    var vs = [];
    try { vs = synth.getVoices() || []; } catch (e) { return null; }
    var mine = vs.filter(function (v) { return v.localService && /^en/i.test(v.lang || ''); });
    return mine.length ? mine[0] : null;   /* on-device only: a network voice is never chosen */
  }
  function tell(code) { if (state.onstate) state.onstate(code); }
  function utter(agent, text) {
    var u = new SpeechSynthesisUtterance(text), v = localVoice();
    u.voice = v; u.lang = v.lang;
    var b = state.data.bounds;
    u.pitch = Math.min(b.pitch[1], Math.max(b.pitch[0], agent.pitch));
    u.rate = Math.min(state.k12 ? state.data.k12_rate_max : b.rate[1], Math.max(b.rate[0], agent.rate));
    u.volume = state.k12 ? state.data.k12_volume : b.volume;
    return u;
  }
  /* speak a queue of [agent, text] pairs, in order. Call ONLY from a click handler. */
  function speak(queue) {
    if (state.muted) { tell('muted'); return false; }
    if (!synth || typeof SpeechSynthesisUtterance === 'undefined') { tell('nosynth'); return false; }
    if (!localVoice()) { tell('novoice'); return false; }
    try {
      synth.cancel();
      queue.forEach(function (p, i) {
        var u = utter(p[0], p[1]);
        if (i === queue.length - 1) u.onend = function () { tell('done'); };
        synth.speak(u);
      });
      tell('speaking');
      return true;
    } catch (e) { tell('refused'); return false; }
  }
  function stop() { try { if (synth) synth.cancel(); } catch (e) { /* nothing speaking */ } tell('stopped'); }
  return { init: init, setMuted: setMuted, speak: speak, stop: stop, muted: function () { return state.muted; }, localVoice: localVoice };
})();
'''


def hive_i18n_keys():
    return ['hive.v.mute', 'hive.v.stop', 'hive.v.muted', 'hive.v.nosynth', 'hive.v.novoice', 'hive.v.refused',
            'hive.v.speaking', 'hive.v.done', 'hive.v.stopped', 'hive.v.ready', 'hive.speak']


def js_json(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def kit_stamp():
    return hashlib.sha256(HIVE_JS.encode()).hexdigest()[:16]


# ---- the worlds (wave 16 H2): voice on a click for the figures that already walk and stand in the 3D worlds -------
# Both adapters only ADD a Speak and a Mute button to a dialogue the world already draws; they never open a dialogue,
# never speak on their own, and speak the registry line the dialogue is showing, matched back to the hive by
# (name, text, source) for a world guide and by (agent id, topic id) for a hall advisor or crew role.
HIVE_WORLD_CSS = r'''
.hv-wbtn{min-block-size:44px;min-inline-size:44px;font:inherit;color:var(--ink,var(--tc-ink));background:var(--panel,var(--tc-raised));border:1px solid var(--rule,var(--tc-line));border-radius:8px;padding:0 12px;cursor:pointer}
.hv-wbtn[aria-pressed="true"]{background:var(--mark,var(--tc-amber));color:var(--mark-ink,var(--tc-amber-ink,#12181B))}
.hv-wstate{display:block;font-size:.78rem;color:var(--muted,var(--tc-muted));min-block-size:1em}
'''

# parish world: the NPC kit's dialogue panel (.npc-panel); NPCD is the page's own npcs.json block.
HIVE_PARISH_JS = r'''
/* Omega Hive voice for the world guides (web/hivekit.py). */
const hiveWorld = (function () {
  const el = document.getElementById('hive-voice'), panel = document.querySelector('.npc-panel');
  if (!el || !panel || !window.HiveVoice) return null;
  const HV = JSON.parse(el.textContent), qs = new URLSearchParams(location.search);
  const k12 = qs.has('classroom') || qs.has('class');
  let said = 0;
  const stateEl = () => panel.querySelector('[data-hive-state]');
  /* the words travel in the hive block itself (hive.* keys, 8 locales), so this map's own catalogue is untouched */
  const lab = () => HV.labels[String(document.documentElement.lang || 'en').slice(0, 2)] || HV.labels.en;
  HiveVoice.init(HV, { k12, onstate: (s) => { const st = stateEl(); if (st) st.textContent = lab()[s] || ''; } });
  /* the line is the page's own: the NPC block this map already embeds (npcs.json). The hive adds only the voice and
     whether classroom mode holds that line. */
  const byName = {}, byId = {};
  NPCD.npcs.forEach((n) => { (byName[n.name] = byName[n.name] || []).push(n); });
  HV.agents.forEach((a) => { byId[a.id] = a; });
  function current() {
    const name = panel.querySelector('#npc-dlg-title'), text = panel.querySelector('.npc-line blockquote p'), src = panel.querySelector('.npc-line .npc-src code');
    if (!name || !text || !src) return null;
    for (const n of byName[name.textContent] || []) {
      const j = n.knowledge.findIndex((k) => k.text === text.textContent && k.source === src.textContent);
      const a = byId['npc:' + n.id];
      if (j >= 0 && a) return { agent: a, line: { id: 'k' + j, safe: a.held.indexOf('k' + j) < 0 }, text: n.knowledge[j].text };
    }
    return null;
  }
  function decorate() {
    const row = panel.querySelector('.npc-actions');
    if (!row || row.querySelector('[data-hive]')) return;
    const sp = document.createElement('button'), mu = document.createElement('button'), st = document.createElement('span');
    sp.type = 'button'; sp.className = 'hv-wbtn'; sp.dataset.hive = 'speak'; sp.textContent = lab().speak;
    mu.type = 'button'; mu.className = 'hv-wbtn'; mu.dataset.hive = 'mute'; mu.textContent = lab().mute;
    mu.setAttribute('aria-pressed', HiveVoice.muted() ? 'true' : 'false');
    st.className = 'hv-wstate'; st.dataset.hiveState = ''; st.setAttribute('role', 'status');
    row.appendChild(sp); row.appendChild(mu); row.appendChild(st);
  }
  new MutationObserver(decorate).observe(panel, { childList: true });
  decorate();
  panel.addEventListener('click', (e) => {
    const b = e.target.closest('[data-hive]');
    if (!b) return;
    if (b.dataset.hive === 'mute') { HiveVoice.setMuted(!HiveVoice.muted()); b.setAttribute('aria-pressed', HiveVoice.muted() ? 'true' : 'false'); return; }
    const c = current();
    if (!c || (k12 && (!c.agent.k12 || !c.line.safe))) return;
    if (HiveVoice.speak([[c.agent, c.text]])) said++;
  });
  return { current, agents: HV.agents.length, k12, said: () => said };
})();
'''

# 3D campus: the advisor / crew-role panel (#pbody), redrawn by openAdvisor(aid, topicId). Called at its end.
HIVE_CAMPUS_JS = r'''
/* Omega Hive voice for the hall advisors and crew roles (web/hivekit.py). */
const hiveCampus = (function () {
  const el = document.getElementById('hive-voice');
  if (!el || !window.HiveVoice) return null;
  const HV = JSON.parse(el.textContent), qs = new URLSearchParams(location.search), byId = {};
  const k12 = qs.has('classroom') || qs.has('class');
  HV.agents.forEach((a) => { byId[a.id] = a; });
  HiveVoice.init(HV, { k12 });
  let cur = null, said = 0;
  const lab = () => HV.labels[String(document.documentElement.lang || 'en').slice(0, 2)] || HV.labels.en;
  function pick(aid, topicId) {
    const a = byId[(String(aid).includes(':') ? 'crew:' : 'advisor:') + aid];
    if (!a) return null;
    const say = topicId ? a.lines.find((l) => l.id === topicId && l.k === 'say') : null;
    /* AGENT-AVATAR: with no topic, the line the dialogue opened with (the trait rule's opener), else the greeting */
    const op = a.lines[k12 ? a.o12 : a.o];
    const ln = say || (op && (op.k === 'greeting' || op.k === 'say') ? op : null) || a.lines.find((l) => l.k === 'greeting');
    return ln ? { agent: a, line: ln, text: HV.texts[ln.t][0] } : null;
  }
  function decorate(aid, topicId) {
    cur = pick(aid, topicId);
    const body = document.getElementById('pbody');
    if (!cur || !body) return null;
    const row = document.createElement('p'), sp = document.createElement('button'), mu = document.createElement('button');
    row.className = 'hv-wrow';
    sp.type = 'button'; sp.className = 'hv-wbtn'; sp.dataset.hive = 'speak'; sp.textContent = lab().speak;
    mu.type = 'button'; mu.className = 'hv-wbtn'; mu.dataset.hive = 'mute'; mu.textContent = lab().mute;
    mu.setAttribute('aria-pressed', HiveVoice.muted() ? 'true' : 'false');
    row.appendChild(sp); row.appendChild(document.createTextNode(' ')); row.appendChild(mu);
    const h2 = body.querySelector('h2');
    if (h2 && h2.nextSibling) body.insertBefore(row, h2.nextSibling); else body.appendChild(row);
    return cur;
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('#pbody [data-hive]');
    if (!b) return;
    if (b.dataset.hive === 'mute') { HiveVoice.setMuted(!HiveVoice.muted()); b.setAttribute('aria-pressed', HiveVoice.muted() ? 'true' : 'false'); return; }
    if (!cur || (k12 && (!cur.agent.k12 || !cur.line.safe))) return;
    if (HiveVoice.speak([[cur.agent, cur.text]])) said++;
  });
  return { decorate, current: () => cur, agents: HV.agents.length, k12, said: () => said };
})();
'''


WORLD_LABEL_KEYS = {'speak': 'hive.speak', 'mute': 'hive.v.mute', 'muted': 'hive.v.muted', 'nosynth': 'hive.v.nosynth',
                    'novoice': 'hive.v.novoice', 'refused': 'hive.v.refused', 'ready': 'hive.v.ready'}


def world_labels():
    """The Speak / Mute / voice-state words in all 8 locales, carried in a world page's hive block so the world's own
    run-time catalogue (and the suites that hold it to exactly the keys it uses) is not touched."""
    out = {}
    for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
        c = json.loads(f.read_text(encoding='utf-8'))
        row = {}
        for name, k in WORLD_LABEL_KEYS.items():
            if not isinstance(c['strings'].get(k), str) or not c['strings'][k].strip():
                raise HiveKitError(f'hivekit: locale {c["locale"]} has no {k}')
            row[name] = c['strings'][k]
        out[c['locale']] = row
    if len(out) != 8:
        raise HiveKitError(f'hivekit: expected 8 locales, found {sorted(out)}')
    return out


def world_embed(data):
    """The tail a world page carries: its hive voice block (JSON) and the kit (classic script, so it runs before the
    page's module script)."""
    return (f'<style id="hive-world-css">{HIVE_WORLD_CSS}</style>'
            f'<script type="application/json" id="hive-voice">{js_json(data)}</script>'
            f'<script id="hive-kit">{HIVE_JS}</script>')


# ==== AVATAR BEGIN (wave 17, AVATAR·Agents Embodied) ===================================================================
# Each agent in the roster is drawn in the worlds wearing its own outfit and behaves by its AUTHORED personality. That
# stays SCRIPTED: no line is written here. Two choices are made by a fixed rule from the three AUTHORED traits.
#   - GESTURE: the class of the agent's FIRST trait in the table below (wave / nod / point). It is one idle gesture: a
#     simple transform animation on the figure (the rig's own bones in the 3D campus, the instanced arm/head parts in the
#     parish world). The table is AUTHORED; a trait missing from it stops the build by name (fail closed).
#   - OPENER: the line the dialogue opens with. The candidates are the agent's own quoted lines that can open a talk, in
#     registry order: an advisor's or crew role's greeting and its `say` answers, a world guide's knowledge lines. The
#     opener is candidates[(sum of the three traits' class numbers, wave 0 / nod 1 / point 2) mod len(candidates)], so a
#     wholly warm figure opens with its greeting (or first line). In classroom mode the opener is the first play-safe
#     candidate from that index onward. Pages print and speak the quote with its registry source, never a new text.
# Page markers are neutral (AGENT-AVATAR); this comment may name the team.
GESTURES = ('wave', 'nod', 'point')
TRAIT_GESTURE_AUTHORED = {
    # warm and outgoing: greets with a raised hand
    'wave': ['welcoming', 'cheerful', 'hospitable', 'friendly', 'encouraging', 'gentle', 'kind', 'humane', 'inclusive',
             'courteous', 'helpful', 'cooperative', 'relaxed', 'outdoorsy', 'responsive', 'visible'],
    # steady and attentive: acknowledges with a nod
    'nod': ['experienced', 'patient', 'composed', 'thoughtful', 'calm', 'unhurried', 'careful', 'alert', 'watchful',
            'observant', 'vigilant', 'attentive', 'aware', 'steady', 'steady at height', 'steadfast', 'dependable',
            'grounded', 'ground-minded', 'weather-minded', 'quiet', 'fair', 'focused', 'absorbed', 'single-minded',
            'deliberate', 'measured', 'even', 'dry', 'skeptical', 'candid', 'sturdy', 'secured', 'ready', 'unflashy', 'plain'],
    # directive and procedural: points to the work
    'point': ['direct', 'authoritative', 'decisive', 'frank', 'clear', 'informative', 'practical', 'procedural',
              'process-minded', 'structured', 'organised', 'orderly', 'tidy', 'precise', 'exact', 'exacting', 'meticulous',
              'rigorous', 'methodical', 'sequential', 'checklist-minded', 'diagram-minded', 'route-minded', 'signal-minded',
              'boundary-minded', 'positional', 'literal', 'concise', 'plain-spoken', 'brisk', 'firm', 'formal', 'thorough',
              'accountable', 'disciplined', 'hands-on'],
}
TRAIT_GESTURE = {}
for _g, _ts in TRAIT_GESTURE_AUTHORED.items():
    for _t in _ts:
        if _t in TRAIT_GESTURE:
            raise HiveKitError(f'hivekit: AVATAR trait {_t!r} is in two gesture classes')
        TRAIT_GESTURE[_t] = _g
OPENER_KINDS = {'advisor': ('greeting', 'say'), 'crew-role': ('greeting', 'say'), 'npc': ('knowledge',)}
BEHAVIOUR_RULE = ('SCRIPTED. Gesture: the class (wave, nod, point) of the first AUTHORED trait. Opener: the agent\'s '
                  'greeting and say lines (a guide\'s knowledge lines), in registry order, indexed by the sum of the three '
                  'traits\' classes (wave 0, nod 1, point 2) modulo their count; classroom mode takes the first play-safe '
                  'one from there. Every line is a registry quote.')


def behaviour(a):
    """{'gesture', 'open', 'open_k12', 'open_id', 'phase'} for one hive agent (registry row), by the AUTHORED trait rule."""
    traits = a['personality']['traits']
    cls = []
    for t in traits:
        if t not in TRAIT_GESTURE:
            raise HiveKitError(f'hivekit: AVATAR - trait {t!r} of {a["id"]} has no gesture class in TRAIT_GESTURE_AUTHORED')
        cls.append(TRAIT_GESTURE[t])
    if a['kind'] not in OPENER_KINDS:
        raise HiveKitError(f'hivekit: AVATAR - no opener kinds for agent kind {a["kind"]!r}')
    cands = [i for i, ln in enumerate(a['lines']) if ln['kind'] in OPENER_KINDS[a['kind']]]
    if not cands:
        raise HiveKitError(f'hivekit: AVATAR - {a["id"]} has no line that can open a dialogue')
    j = sum(GESTURES.index(c) for c in cls) % len(cands)
    pick = cands[j]
    safe = [cands[(j + k) % len(cands)] for k in range(len(cands)) if a['lines'][cands[(j + k) % len(cands)]]['k12']]
    pick12 = safe[0] if safe else pick
    phase = int(hashlib.sha256((a['id'] + ':gesture').encode()).hexdigest()[:8], 16) / 2 ** 32
    return {'gesture': cls[0], 'open': pick, 'open_k12': pick12, 'open_id': a['lines'][pick]['id'],
            'open_id_k12': a['lines'][pick12]['id'], 'phase': round(phase, 3)}


def avatar_rows(kinds, reg=None, ids=None):
    """What a world page needs to dress and animate its figures: per agent the locker cfg, the proxy colours (the same
    hexes the Hive page portraits are drawn from), the gesture and the opener line id. key = the page's own figure key
    (advisor id, "<crew>:<role>", or the guide's npcs.json id)."""
    reg = reg or hive_registry()
    rows = []
    for a in reg['agents']:
        if a['kind'] not in kinds or (ids is not None and a['id'] not in ids):
            continue
        bh = behaviour(a)
        px = {k: (v['hex'] if v else None) for k, v in a['avatar']['proxy'].items()}
        for k in ('torso', 'legs', 'head'):
            if not px.get(k):
                raise HiveKitError(f'hivekit: AVATAR - {a["id"]} has no proxy colour for {k}')
        key = a['id'].split(':', 1)[1]
        rows.append({'id': a['id'], 'key': key, 'character': a['avatar']['character'], 'cfg': a['avatar']['cfg'], 'px': px,
                     'scale': a['avatar']['scale']['xyz'], 'g': bh['gesture'], 'oid': bh['open_id'], 'oid12': bh['open_id_k12'],
                     'phase': bh['phase'], 'traits': a['personality']['traits']})
    return {'stamp': reg['source_stamp'], 'rule': BEHAVIOUR_RULE, 'agents': rows}


# the 3D campus (web/build_3d.py AVATAR block): dresses the hall advisors and crew roles, opens their dialogue on the
# rule's line and runs the gesture. Function declarations only (hoisted), state kept on agentAv itself, because the
# campus builds and spawns figures before the module script reaches the line where this text is inserted.
AVATAR_3D_JS = r'''
/* AGENT-AVATAR: each hall advisor and crew role wears its own outfit from the agent roster (the locker options, their
   colours and accessories), opens its dialogue with the quoted line its AUTHORED traits pick, and makes one idle
   gesture (a wave, a nod or a point) as a transform on the rig's own bones. SCRIPTED: every line is a registry quote. */
function agentAv() {
  if (agentAv.by) return agentAv;
  const el = document.getElementById('agent-avatar');
  agentAv.d = el ? JSON.parse(el.textContent) : { agents: [] };
  agentAv.by = {}; agentAv.t0 = {}; agentAv.last = {}; agentAv.built = 0;
  for (const r of agentAv.d.agents) agentAv.by[r.key] = r;
  const qs = new URLSearchParams(location.search);
  agentAv.k12 = qs.has('classroom') || qs.has('class');
  return agentAv;
}
function agentOutfit(aid) { return agentAv().by[aid] ?? null; }
/* the locker rig reads colours and build through optOf(), i.e. from avatarCfg: dress it in THIS cfg, then hand the
   learner's own look back, so a figure never wears the learner's colours */
function agentBody(cfg) {
  const keep = avatarCfg;
  avatarCfg = cfg;
  let g;
  try { g = buildAvatarMesh(cfg); } finally { avatarCfg = keep; }
  g.userData.agentCfg = cfg;
  agentAv().built++;
  return g;
}
/* the far stand-in: the same three boxes as proxyFigure(), in the figure's own proxy colours */
function agentProxy(aid) {
  const r = agentOutfit(aid);
  if (!r) return null;
  const M = (hex) => new THREE.MeshStandardMaterial({ color: hex, roughness: .8 });
  const g = new THREE.Group();
  const torso = new THREE.Mesh(boxGeo(.44, .62, .26), M(r.px.torso));
  torso.position.y = 1.22;
  const legs = new THREE.Mesh(boxGeo(.38, .82, .24), M(r.px.legs));
  legs.position.y = .5;
  const head = new THREE.Mesh(boxGeo(.22, .24, .22), M(r.px.hat || r.px.head));
  head.position.y = 1.66;
  g.add(torso, legs, head);
  return g;
}
function agentOpenId(aid) {
  const r = agentOutfit(aid);
  return r ? (agentAv().k12 ? r.oid12 : r.oid) : 'greeting';
}
/* the panel's first paragraph when no topic is asked: the opener, a registry quote; a `say` opener carries its source */
function agentOpener(aid, a, esc) {
  agentAv().t0[aid] = clock.elapsedTime;          // the gesture plays as the dialogue opens
  const id = agentOpenId(aid);
  const tp = id !== 'greeting' ? a.topics.find((x) => x.id === id && x.kind === 'say') : null;
  if (!tp) return '<p class="focus" data-agent-open="greeting">' + esc(a.greeting) + '</p>';
  return '<p class="focus" data-agent-open="' + esc(id) + '">' + esc(tp.say) + '</p><p class="src">written in '
    + esc(tp.cites) + '</p>';
}
/* one idle gesture: every 9 s at the figure's own phase, and as its dialogue opens, for 1.6 s. Only the near, rigged
   body moves; reduced-motion users keep the rest pose. */
function agentGesture(m, t) {
  const A = agentAv(), aid = m.userData.advisor, r = A.by[aid];
  const b = m.userData.body?.userData?.bones;
  if (!r || !b || reduced) return;
  const DUR = 1.6, EVERY = 9, t0 = A.t0[aid];
  let u = -1;
  if (t0 !== undefined && t >= t0 && t - t0 < DUR) u = t - t0;
  else { const ph = (t + r.phase * EVERY) % EVERY; if (ph < DUR) u = ph; }
  const env = u < 0 ? 0 : Math.sin(Math.PI * u / DUR);
  const ua = b.rightUpperArm, la = b.rightLowerArm, nk = b.neck;
  if (r.g === 'wave' && ua && la) {
    ua.rotation.x = -2.5 * env; ua.rotation.z = .3 * env; la.rotation.z = .45 * Math.sin(u * 18) * env;
  } else if (r.g === 'point' && ua && la) {
    ua.rotation.x = -1.45 * env; ua.rotation.z = 0; la.rotation.z = 0;
  } else if (r.g === 'nod' && nk) {
    nk.rotation.x = .28 * Math.sin(u * 4 * Math.PI / DUR) * env;
  }
  A.last[aid] = { g: r.g, env: Math.round(env * 1000) / 1000, t };
}
/* the harness hook's figure key: an advisor id, "<crew>:<role>", a roster id ("advisor:<id>", "crew:<crew>:<role>"),
   each with an optional trailing topic */
function agentHookKey(arg) {
  const s = String(arg).replace(/^(advisor|crew):/, '');
  return advisorHookArgs(s)[0];
}
/* read-only harness surface: what each standing figure is wearing and doing */
function agentFigure(k) {
  const m = advisorMeshes.find((x) => x.userData.advisor === agentHookKey(k));
  if (!m) return null;
  const hexes = (o) => { const s = new Set(); o.traverse((c) => { const ms = c.material ? [].concat(c.material) : [];
    for (const x of ms) if (x.color) s.add('#' + x.color.getHexString()); }); return [...s]; };
  return { key: m.userData.advisor, cfg: m.userData.body.userData.agentCfg ?? null, body: hexes(m.userData.body),
           proxy: m.userData.proxy.children.map((c) => '#' + c.material.color.getHexString()), near: m.userData.body.visible };
}
window.__agentAvatars = { rows: () => agentAv().d.agents.length, outfit: agentOutfit, openId: agentOpenId,
  last: () => agentAv().last, t0: (k) => agentAv().t0[k], k12: () => !!agentAv().k12, built: () => agentAv().built, hookKey: agentHookKey, figure: agentFigure,
  here: () => advisorMeshes.map((m) => m.userData.advisor), learnerCfg: () => avatarCfg };
'''
def guide_rows(ids, reg=None):
    """The parish world's slim outfit / behaviour rows for the guides placed on the map: k = npcs.json id, o / o12 = the
    opener's index into that guide's knowledge lines (hive line id 'k<i>'), g = gesture, h = hair hex (None = none
    shown), hat = wears headwear, t = top colour (sleeves), s = skin, b = wears a tool belt, p = gesture phase."""
    reg = reg or hive_registry()
    rows = []
    for r in avatar_rows(['npc'], reg=reg, ids=ids)['agents']:
        if not (r['oid'].startswith('k') and r['oid12'].startswith('k')):
            raise HiveKitError(f'hivekit: AVATAR - guide {r["id"]} opens on a non-knowledge line {r["oid"]}')
        rows.append({'k': r['key'], 'o': int(r['oid'][1:]), 'o12': int(r['oid12'][1:]), 'g': r['g'], 'h': r['px'].get('hair'),
                     'hat': 1 if r['px'].get('hat') else 0, 't': r['px']['torso'], 's': r['px']['head'],
                     'b': 0 if r['cfg']['tools'] == 'none' else 1, 'p': r['phase']})
    return {'stamp': reg['source_stamp'], 'rule': BEHAVIOUR_RULE, 'belt': GUIDE_BELT_HEX, 'rows': rows}


# the locker rig's belt colour (web/build_3d.py buildAvatarMesh: `dark`, the belt under every tool set)
GUIDE_BELT_HEX = '#26262a'

# the parish world (web/build_parishes.py AVATAR block). Function declarations for what the NPC kit calls while it is
# being created (the opener); the parts layer is mounted after the kit exists.
AVATAR_PARISH_OPEN_JS = r"""
/* AGENT-AVATAR: the line a guide's dialogue opens with - the trait rule's opener (an index into its own npcs.json
   knowledge lines, so the quote and its source are the page's own); classroom mode takes the play-safe opener */
function agentGuideRows() {
  if (!agentGuideRows.by) {
    const el = document.getElementById('agent-avatar-guides');
    agentGuideRows.d = el ? JSON.parse(el.textContent) : { rows: [] };
    agentGuideRows.by = {};
    for (const r of agentGuideRows.d.rows) agentGuideRows.by[r.k] = r;
    const qs = new URLSearchParams(location.search);
    agentGuideRows.k12 = qs.has('classroom') || qs.has('class');
  }
  return agentGuideRows.by;
}
function agentGuideOpen(n) {
  const r = agentGuideRows()[n.id];
  if (!r) return 0;
  const i = agentGuideRows.k12 ? r.o12 : r.o;
  return Math.max(0, Math.min(n.knowledge.length - 1, i));
}
"""

AVATAR_PARISH_JS = r"""
/* AGENT-AVATAR: the world guides wear the rest of their roster outfit - hair (bare-headed guides), sleeves in their top
   colour and a tool belt where they carry tools - as three more InstancedMeshes (one draw call each, hidden in the
   overview with the kit's own parts). The parts are a POOL: only the CAP nearest guides within DRAW metres hold a slot,
   so the layer costs at most CAP x 4 boxes whatever the roster's size. Each guide makes one idle gesture - a wave, a nod
   or a point - as a transform of those instances: when it greets you or starts talking, and every 9 s at its own phase
   while you are within 40 m; reduced-motion users keep the rest pose. SCRIPTED: nothing is said or written here. */
const agentGuides = (function () {
  if (!npcKit) return null;
  const by = agentGuideRows(), D = agentGuideRows.d;
  const list = npcKit.agents.filter((a) => by[a.id]);
  if (!list.length) return null;
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const kitPart = (k) => scene.children.find((c) => c.userData.npcPart === k && c.isInstancedMesh) || null;
  const torso = kitPart('torso'), head = kitPart('head'), hat = kitPart('hat');
  const CAP = 24, DRAW = 90;
  const box = (w, h, d, y) => { const g = new THREE.BoxGeometry(w, h, d); g.translate(0, y, 0); return g; };
  const mk = (name, geo, cap) => {
    const m = new THREE.InstancedMesh(geo, new THREE.MeshStandardMaterial({ roughness: 0.8 }), Math.max(1, cap));
    m.count = cap; m.frustumCulled = false; m.userData.npcPart = name; m.name = 'agent-avatar:' + name; scene.add(m); return m;
  };
  const hair = mk('hair', box(0.24, 0.07, 0.24, 0), CAP), arms = mk('arms', box(0.11, 0.56, 0.12, -0.28), 2 * CAP),
    belt = mk('belt', box(0.46, 0.08, 0.28, 0), CAP);
  const col = new THREE.Color(), M = new THREE.Matrix4(), B = new THREE.Matrix4(), L = new THREE.Matrix4(), ZERO = new THREE.Matrix4().makeScale(0, 0, 0);
  const P = new THREE.Vector3(), S = new THREE.Vector3(), Q = new THREE.Quaternion(), Qx = new THREE.Quaternion(), E = new THREE.Euler();
  const UP = new THREE.Vector3(0, 1, 0), XA = new THREE.Vector3(1, 0, 0), TP = new THREE.Vector3();
  for (let i = 0; i < CAP; i++) {
    hair.setMatrixAt(i, ZERO); belt.setMatrixAt(i, ZERO); arms.setMatrixAt(2 * i, ZERO); arms.setMatrixAt(2 * i + 1, ZERO);
    hair.setColorAt(i, col.set(D.belt)); belt.setColorAt(i, col); arms.setColorAt(2 * i, col); arms.setColorAt(2 * i + 1, col);
  }
  for (const m of [hair, arms, belt]) m.count = 0;
  const DUR = 1.6, EVERY = 9, NEAR = 40;
  const st = new Map(list.map((a) => [a, { e: 0, s: '', t0: -1 }]));
  let T = 0, played = 0, writes = 0, slotOf = {};
  const last = {};
  function write(a, r, e, u, k, nodNow) {
    const [sx, sy, sz] = a.scale;
    let y0 = 0;
    if (torso) { torso.getMatrixAt(a.idx, M); y0 = TP.setFromMatrixPosition(M).y - 1.22 * sy; }
    B.compose(P.set(a.x, y0, a.z), Q.setFromAxisAngle(UP, a.heading), S.set(sx, sy, sz));
    const nod = r.g === 'nod' ? 0.28 * Math.sin(u * 4 * Math.PI / DUR) * e : 0;
    hair.setColorAt(k, col.set(r.h || r.s)); belt.setColorAt(k, col.set(D.belt));
    arms.setColorAt(2 * k, col.set(r.t)); arms.setColorAt(2 * k + 1, col);
    if (r.h && !r.hat) {
      L.makeRotationX(nod).setPosition(0, 1.80, 0); hair.setMatrixAt(k, M.multiplyMatrices(B, L));
    } else hair.setMatrixAt(k, ZERO);
    belt.setMatrixAt(k, r.b ? M.multiplyMatrices(B, L.makeTranslation(0, 0.92, 0)) : ZERO);
    arms.setMatrixAt(2 * k, M.multiplyMatrices(B, L.makeTranslation(0.28, 1.5, 0)));
    let rx = 0, rz = 0;
    if (r.g === 'wave') { rx = -2.5 * e; rz = -0.3 * e + 0.35 * Math.sin(u * 18) * e; }
    else if (r.g === 'point') rx = -1.45 * e;
    L.makeRotationFromEuler(E.set(rx, 0, rz)).setPosition(-0.28, 1.5, 0);
    arms.setMatrixAt(2 * k + 1, M.multiplyMatrices(B, L));
    if (nodNow && head) {   // the kit's own head pose is left alone unless a nod is playing or just ended
      Q.setFromAxisAngle(UP, a.heading).multiply(Qx.setFromAxisAngle(XA, nod));
      head.setMatrixAt(a.idx, M.compose(P.set(a.x, y0 + 1.66 * sy, a.z), Q, S.set(sx, sy, sz)));
      if (hat && r.hat) hat.setMatrixAt(a.idx, M.compose(P.set(a.x, y0 + 1.82 * sy, a.z), Q, S));
    }
    writes++;
  }
  function frame(dt, px, pz) {
    T += Math.min(dt, 0.1);
    let k = 0, nodded = false;
    slotOf = {};
    for (const a of list) {
      const r = by[a.id], s = st.get(a);
      if (a.state !== s.s) {
        if ((a.state === 'greet' || a.state === 'talk') && s.s !== 'greet' && s.s !== 'talk') { s.t0 = T; played++; }
        s.s = a.state;
      }
      const d = Math.hypot(a.x - px, a.z - pz);
      if (d > DRAW || k >= CAP) continue;
      let u = s.t0 >= 0 && T - s.t0 < DUR ? T - s.t0 : -1;
      if (u < 0 && d < NEAR) { const ph = (T + r.p * EVERY) % EVERY; if (ph < DUR) u = ph; }
      const e = still || u < 0 ? 0 : Math.sin(Math.PI * u / DUR);
      const nodNow = r.g === 'nod' && (e > 0 || s.e > 0);
      if (nodNow) nodded = true;
      s.e = e; slotOf[a.id] = k;
      write(a, r, e, u, k++, nodNow);
      if (e > 0) last[a.id] = { g: r.g, env: Math.round(e * 1000) / 1000, t: T };
    }
    hair.count = k; belt.count = k; arms.count = 2 * k;
    for (const m of [hair, arms, belt]) { m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true; }
    if (nodded) { if (head) head.instanceMatrix.needsUpdate = true; if (hat) hat.instanceMatrix.needsUpdate = true; }
  }
  return { frame, rows: list.length, cap: CAP, parts: [hair, arms, belt], played: () => played, writes: () => writes, last: () => last,
    slotted: () => Object.keys(slotOf).length,
    gestureOf: (id) => (by[id] ? by[id].g : null), openOf: (id) => (by[id] ? (agentGuideRows.k12 ? by[id].o12 : by[id].o) : null),
    colourOf: (id) => { const k = slotOf[id]; if (k === undefined) return null; const c = new THREE.Color();
      const g = (m, i) => (m.instanceColor ? (m.getColorAt(i, c), '#' + c.getHexString()) : null);
      return { hair: g(hair, k), arm: g(arms, 2 * k), belt: g(belt, k) }; } };
})();
window.__agentGuides = agentGuides;
"""

# ---- the Hive council point on the flagship campus plaza (3D) ------------------------------------------------------
# The same deterministic council the Hive page runs (HiveCore.council over every agent's quoted lines), opened from a
# point on the plaza. The suggested asks are the Hive page's: registry asks (an AUTHORED selection; web/build_hive.py
# SUGGEST - web/test_hive.mjs holds the two lists equal). Voice on a click only, with Mute; classroom mode is play-safe.
COUNCIL_FLAGSHIP = 'treasure-island'
COUNCIL_SUGGEST = [('advisor:guide', 'what'), ('advisor:guide', 'real'), ('advisor:layout-hand', 'control'),
                   ('advisor:inspector', 'cert'), ('advisor:safety-steward', 'refuse'), ('crew:crane-lift-crew:lift-director', 'plan'),
                   ('crew:trench-crew:spotter', 'where'), ('crew:confined-space-crew:attendant', 'never'), ('advisor:dispatcher', 'sited')]
COUNCIL_LABEL_KEYS = {'council': 'hive.h.council', 'note': 'hive.cn.note', 'ask': 'hive.cn.ask', 'go': 'hive.cn.go',
                      'play': 'hive.cn.play', 'none': 'hive.cn.none', 'short': 'hive.cn.short', 'try': 'hive.cn.try',
                      'matched': 'hive.cn.matched', 'src': 'hive.src', 'speak': 'hive.speak', 'mute': 'hive.v.mute',
                      'muted': 'hive.v.muted', 'nosynth': 'hive.v.nosynth', 'novoice': 'hive.v.novoice', 'speaking': 'hive.v.speaking',
                      'is1': 'hive.is.1', 'is2': 'hive.is.2', 'is3': 'hive.is.3', 'k12': 'hive.k12.note'}


def council_labels():
    out = {}
    for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
        c = json.loads(f.read_text(encoding='utf-8'))
        row = {}
        for name, k in COUNCIL_LABEL_KEYS.items():
            if not isinstance(c['strings'].get(k), str) or not c['strings'][k].strip():
                raise HiveKitError(f'hivekit: AVATAR council - locale {c["locale"]} has no {k}')
            row[name] = c['strings'][k]
        out[c['locale']] = row
    if len(out) != 8:
        raise HiveKitError(f'hivekit: AVATAR council - expected 8 locales, found {sorted(out)}')
    return out


def council_data(reg=None):
    """The whole roster's council block for the 3D plaza: hive_data() of every agent (lines once, by index), the suggested
    registry asks and the council's words in all 8 locales."""
    reg = reg or hive_registry()
    d = hive_data(reg, with_cfg=False)
    by = {a['id']: a for a in reg['agents']}
    asks = []
    for aid, lid in COUNCIL_SUGGEST:
        ln = next((x for x in by[aid]['lines'] if x['id'] == lid and x.get('ask_provenance') == 'REGISTRY'), None) if aid in by else None
        if ln is None:
            raise HiveKitError(f'hivekit: AVATAR council - suggested ask {aid}:{lid} is not a registry ask in the hive')
        asks.append([aid + ':' + lid, ln['ask']])
    d.update({'asks': asks, 'labels': council_labels(), 'flagship': COUNCIL_FLAGSHIP})
    return d


AVATAR_COUNCIL_JS = r"""
/* AGENT-AVATAR council point: on the flagship campus plaza, a plinth that opens the same deterministic council the Hive
   page runs (HiveCore.council over every agent's quoted lines - SCRIPTED, no model). Up to five agents answer, each
   with a registry line and its source. The voice is the device's own speech synthesis, on a click only, with Mute;
   classroom mode seats play-safe agents and lines only and starts muted. */
function agentCouncilData() {
  if (agentCouncilData.d === undefined) {
    const el = document.getElementById('agent-council');
    agentCouncilData.d = el ? JSON.parse(el.textContent) : null;
    const qs = new URLSearchParams(location.search);
    agentCouncilData.k12 = qs.has('classroom') || qs.has('class');
    agentCouncilData.hits = []; agentCouncilData.last = null; agentCouncilData.said = 0;
  }
  return agentCouncilData.d;
}
function agentCouncilLab() {
  const C = agentCouncilData();
  return C.labels[String(document.documentElement.lang || 'en').slice(0, 2)] || C.labels.en;
}
function agentCouncilPoint(key) {
  const C = agentCouncilData();
  agentCouncilData.hits = [];
  if (!C || key !== C.flagship || !campusGroup) return null;
  const g = new THREE.Group();
  const plinth = new THREE.Mesh(new THREE.CylinderGeometry(1.15, 1.3, .32, 6),
    new THREE.MeshStandardMaterial({ color: '#d9c22e', roughness: .55 }));
  plinth.position.y = .16;
  const post = new THREE.Mesh(new THREE.CylinderGeometry(.16, .2, 2.1, 6),
    new THREE.MeshStandardMaterial({ color: '#2c3e5a', emissive: '#14304a', roughness: .5 }));
  post.position.y = 1.37;
  g.add(plinth, post);
  const L = agentCouncilLab();
  const plate = label('⬡  ' + L.council, L.go, .44, { kind: 'advisor' });
  plate.position.set(0, 2.9, 0);
  g.add(plate);
  g.position.set(-9, 0, 8);
  g.userData.agentCouncil = true; plinth.userData.agentCouncil = true; post.userData.agentCouncil = true;
  campusGroup.add(g);
  agentCouncilData.hits = [plinth, post];
  return g;
}
function agentCouncilPick(ray) {
  if (!agentCouncilData.hits || !agentCouncilData.hits.length) return false;
  const h = ray.intersectObjects(agentCouncilData.hits, false)[0];
  if (!h) return false;
  if (walkActive && plc.isLocked) plc.unlock();
  openAgentCouncil();
  return true;
}
function openAgentCouncil(question) {
  const C = agentCouncilData();
  if (!C) return null;
  const L = agentCouncilLab(), k12 = agentCouncilData.k12;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  document.getElementById('pbody').innerHTML =
    '<h2>⬡ ' + esc(L.council) + '</h2>'
    + '<p class="src" data-council-honest>' + esc(L.is1) + ' ' + esc(L.is2) + ' ' + esc(L.is3) + '</p>'
    + (k12 ? '<p class="src" data-council-k12>' + esc(L.k12) + '</p>' : '')
    + '<p>' + esc(L.note) + '</p>'
    + '<form id="agentCouncilForm"><label>' + esc(L.ask) + ' <input id="agentCouncilQ" type="text" autocomplete="off" '
    + 'style="min-block-size:44px;inline-size:100%;font:inherit"></label> <button class="opt" type="submit">' + esc(L.go) + '</button></form>'
    + '<h3>' + esc(L.try) + '</h3><div class="asks">'
    + C.asks.map((a) => '<button class="opt" type="button" data-council-ask="' + esc(a[1]) + '" data-ask-of="' + esc(a[0]) + '">' + esc(a[1]) + '</button>').join('')
    + '</div><ol id="agentCouncilOut"></ol><p id="agentCouncilNote" class="src"></p>'
    + '<p><button type="button" class="hv-wbtn" data-council="play" disabled>' + esc(L.play) + '</button> '
    + '<button type="button" class="hv-wbtn" data-council="mute" aria-pressed="' + (HiveVoice.muted() ? 'true' : 'false') + '">' + esc(L.mute) + '</button>'
    + '<span class="hv-wstate" role="status" data-council-state></span></p>';
  document.getElementById('panel').scrollTop = 0;
  document.body.classList.add('open');
  return question ? agentConvene(question) : null;
}
function agentConvene(question) {
  const C = agentCouncilData(), L = agentCouncilLab();
  const r = HiveCore.council(C, question, { k12: agentCouncilData.k12 });
  agentCouncilData.last = r;
  const out = document.getElementById('agentCouncilOut'), note = document.getElementById('agentCouncilNote');
  if (!out) return r;
  out.textContent = '';
  r.members.forEach((m, i) => {
    const a = C.agents[m.agent], ln = a.lines[m.line], li = document.createElement('li');
    li.dataset.agent = a.id;
    const b = document.createElement('b'), p = document.createElement('p'), src = document.createElement('p'), code = document.createElement('code'), sp = document.createElement('button');
    b.textContent = a.glyph + ' ' + a.name; p.textContent = C.texts[ln.t][0];
    src.className = 'src'; src.textContent = L.matched + ': ' + m.hits + ' · ' + L.src + ' '; code.textContent = C.texts[ln.t][1]; src.appendChild(code);
    sp.type = 'button'; sp.className = 'hv-wbtn'; sp.dataset.councilSpeak = String(i); sp.textContent = L.speak;
    li.append(b, p, src, sp); out.appendChild(li);
  });
  note.textContent = r.none ? L.none : r.short ? L.short : '';
  const play = document.querySelector('#pbody [data-council="play"]');
  if (play) play.disabled = r.none;
  return r;
}
function agentCouncilSay(queue) {
  const st = document.querySelector('#pbody [data-council-state]'), L = agentCouncilLab();
  const ok = HiveVoice.speak(queue);
  if (ok) agentCouncilData.said += queue.length;
  if (st) st.textContent = ok ? L.speaking : HiveVoice.muted() ? L.muted
    : !window.speechSynthesis ? L.nosynth : L.novoice;
  return ok;
}
document.addEventListener('submit', (e) => {
  if (e.target.id !== 'agentCouncilForm') return;
  e.preventDefault(); agentConvene(document.getElementById('agentCouncilQ').value);
});
document.addEventListener('click', (e) => {
  const b = e.target.closest('#pbody [data-council], #pbody [data-council-ask], #pbody [data-council-speak]');
  if (!b || !agentCouncilData()) return;
  const C = agentCouncilData(), r = agentCouncilData.last;
  if (b.dataset.councilAsk) { document.getElementById('agentCouncilQ').value = b.dataset.councilAsk; agentConvene(b.dataset.councilAsk); return; }
  if (b.dataset.council === 'mute') { HiveVoice.setMuted(!HiveVoice.muted()); b.setAttribute('aria-pressed', HiveVoice.muted() ? 'true' : 'false'); return; }
  if (!r) return;
  const pair = (m) => { const a = C.agents[m.agent]; return [a, C.texts[a.lines[m.line].t][0]]; };
  if (b.dataset.council === 'play') agentCouncilSay(r.members.map(pair));
  else if (b.dataset.councilSpeak !== undefined) { const m = r.members[+b.dataset.councilSpeak]; if (m) agentCouncilSay([pair(m)]); }
});
/* read ?classroom / ?class now, while the address still carries it: the page's syncURL() rewrites the query on the
   first view change, and a lazy read after that would miss classroom mode */
agentAv(); agentCouncilData();
window.__agentCouncil = { open: openAgentCouncil, convene: (q) => agentConvene(q), last: () => agentCouncilData.last,
  said: () => agentCouncilData.said, point: () => agentCouncilData.hits.length, k12: () => !!agentCouncilData.k12,
  asks: () => (agentCouncilData() ? agentCouncilData().asks.map((a) => a[1]) : []) };
"""

# ---- Hive page portraits on a device-tier canvas ---------------------------------------------------------------------
# The server-side SVG portrait (portrait_svg) stays in the page as the no-script picture. With script, each one is
# repainted - shape for shape, the same proxy hexes - onto a canvas whose backing store is 2x on a capable device and
# 1x (the base size, 64 x 72) on a low-tier one; the CSS size never changes. Tier: ?tex=base|high|ultra overrides (the
# 3D page's word); otherwise base when the device reports under 4 GB, under 4 cores or Save-Data, else 2x.
PORTRAIT_JS = r"""
/* AGENT-AVATAR portraits: each card's SVG face repainted onto a device-tier canvas (2x backing store on a capable
   device, the base size on a low-tier one; the CSS size is unchanged). Decorative: aria-hidden, like the SVG. */
var HivePortrait = (function () {
  'use strict';
  function scale() {
    var q = new URLSearchParams(location.search).get('tex');
    if (q === 'base') return 1;
    if (q === 'high' || q === 'ultra') return 2;
    var mem = navigator.deviceMemory || 4, cores = navigator.hardwareConcurrency || 4;
    var save = !!(navigator.connection && navigator.connection.saveData);
    return (mem < 4 || cores < 4 || save) ? 1 : 2;
  }
  var S = scale(), n = 0;
  function paint(svg) {
    var vb = (svg.getAttribute('viewBox') || '0 0 64 72').split(/\s+/).map(Number);
    var w = +svg.getAttribute('width') || vb[2], h = +svg.getAttribute('height') || vb[3];
    var c = document.createElement('canvas');
    c.width = Math.round(w * S); c.height = Math.round(h * S);
    c.style.width = w + 'px'; c.style.height = h + 'px';
    c.className = svg.getAttribute('class') || 'hv-face';
    c.setAttribute('aria-hidden', 'true'); c.dataset.portraitScale = String(S);
    var g = c.getContext('2d');
    if (!g) return null;
    g.scale(c.width / vb[2], c.height / vb[3]);
    Array.prototype.forEach.call(svg.children, function (el) {
      g.fillStyle = el.getAttribute('fill') || '#000';
      var t = el.tagName.toLowerCase();
      if (t === 'rect') {
        var x = +el.getAttribute('x'), y = +el.getAttribute('y'), rw = +el.getAttribute('width'), rh = +el.getAttribute('height'), rx = +el.getAttribute('rx') || 0;
        g.beginPath();
        if (rx && g.roundRect) g.roundRect(x, y, rw, rh, rx); else g.rect(x, y, rw, rh);
        g.fill();
      } else if (t === 'circle') {
        g.beginPath(); g.arc(+el.getAttribute('cx'), +el.getAttribute('cy'), +el.getAttribute('r'), 0, 2 * Math.PI); g.fill();
      } else if (t === 'path') {
        g.fill(new Path2D(el.getAttribute('d')));
      }
    });
    return c;
  }
  function upgrade(root) {
    var faces = (root || document).querySelectorAll('svg.hv-face');
    Array.prototype.forEach.call(faces, function (svg) { var c = paint(svg); if (c) { svg.replaceWith(c); n++; } });
    return n;
  }
  /* a canvas copied by cloneNode is blank: copy its pixels */
  function clone(face) {
    if (!face || face.tagName.toLowerCase() !== 'canvas') return face.cloneNode(true);
    var c = face.cloneNode(false), g = c.getContext('2d');
    if (g) g.drawImage(face, 0, 0);
    return c;
  }
  try { upgrade(document); } catch (e) { /* the SVG portraits stay */ }
  window.__hivePortraits = { scale: S, count: function () { return n; } };
  return { scale: S, upgrade: upgrade, clone: clone, paint: paint };
})();
"""

# ==== AVATAR END =======================================================================================================
