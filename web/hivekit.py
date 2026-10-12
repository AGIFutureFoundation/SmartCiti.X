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
    const ln = say || a.lines.find((l) => l.k === 'greeting');
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
