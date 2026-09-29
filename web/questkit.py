"""Quests on any page: the engine, its data and the DOM hooks, declared once.

    from questkit import QUEST_CSS, quest_js, egg_attr, quest_attr, page_hooks

quest_js(scope, page=None)
    The one <script> block a page carries: the pure core lifted byte-for-byte
    from quests/engine.mjs (between the QUEST_CORE markers), the registry
    entries whose world matches `scope`, the lesson data lessonsDone() needs,
    and the glue that exposes window.TCQuests and binds the hooks. Scopes:
    "all", "campus" (campus and every hall:<id>), "wilds" (every wilds:<id>),
    "parishes" (the parish world "parishes" and every parish:<fips>) or
    "page:<repo-relative path>". Place it AFTER the page's own main script.
egg_attr(id) / quest_attr(id)
    The attribute string for a hook. The id must be in the registry (and be a
    treasure/egg, or not, respectively). Every id handed out is remembered and
    the next quest_js() call fails the build if one of them is not in its
    scope - that is how a hook placed on the wrong page stops the build.
page_hooks(page)
    The markup for a page's own trigger eggs and its hidden cache, so a
    builder adds one line before </body>: page_hooks(PATH) + quest_js('page:' + PATH).

The progress data is read from the SAME storage the progress page reads
(auth/registry/auth.json#records_named: the progress and training keys) with
the SAME evidence functions (a verbatim copy, held by quests/test.mjs). The
only key this writes is `tc-quests`, on this device. Quests are play and
never enter a completion record; the toast and the quest log say so.
"""
import html
import json
import re
import pathlib
import posixpath

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG_PATH = 'quests/registry/quests.json'
ENGINE_PATH = 'quests/engine.mjs'
BEGIN = '/* QUEST_CORE:BEGIN'
END = '/* QUEST_CORE:END */'
LESSONS_PAGE = 'web/trade_craft_lessons.html'
QUESTS_PAGE = 'web/trade_craft_quests.html'
SCOPE_PAGE = {'campus': 'web/trade_craft_3d.html', 'wilds': 'web/trade_craft_wilds.html',
              'parishes': 'web/trade_craft_parishes.html', 'all': QUESTS_PAGE}


def _need(d, k, where):
    if not isinstance(d, dict):
        raise TypeError(f'{where}: expected an object to read {k!r} from')
    if k not in d:
        raise KeyError(f'{where}: required field {k!r} is missing')
    return d[k]


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


REG = _load(REG_PATH)
QUESTS = _need(REG, 'quests', REG_PATH)
BY_ID = {q['id']: q for q in QUESTS}
HONESTY = _need(REG, 'honesty', REG_PATH)

_eng = (ROOT / ENGINE_PATH).read_text(encoding='utf-8')
if _eng.count(BEGIN) != 1 or _eng.count(END) != 1:
    raise AssertionError(f'{ENGINE_PATH}: the QUEST_CORE markers must appear exactly once each')
CORE = _eng[_eng.index(BEGIN):_eng.index(END) + len(END)]

_lessons_reg = _load('lessons/registry/lessons.json')
LESSONS = _need(_lessons_reg, 'lessons', 'lessons/registry/lessons.json')
STEP_KINDS = _need(_lessons_reg, 'step_kinds', 'lessons/registry/lessons.json')
EPISODE_KINDS = _need(_load('training/registry/training.json'), 'episode_kinds', 'training/registry/training.json')
HUMAN_ACTOR = _need(_load('sessions/registry/sessions.json'), 'human_actor', 'sessions/registry/sessions.json')
_rec = _need(_load('auth/registry/auth.json'), 'records_named', 'auth/registry/auth.json')
KEYS = {'progress': _need(_rec, 'progress_key', 'auth.json#records_named'),
        'training': _need(_rec, 'training_key', 'auth.json#records_named')}
HALL_NAMES = {h['slug']: h['name'] for h in _need(_load('pack/registry/halls.json'), 'halls', 'pack/registry/halls.json')}
# the step fields stepEvidence reads; nothing else of a step is carried
STEP_FIELDS = ('n', 'kind', 'sim', 'scenario', 'station', 'crib', 'point', 'advisor', 'topic', 'answer_kind',
               'crew', 'role', 'seat', 'muster')

FINDABLE = ('treasure', 'egg')
_issued = []


def in_scope(q, scope):
    w = q['world']
    if scope == 'all':
        return True
    if scope == 'campus':
        return w == 'campus' or w.startswith('hall:')
    if scope == 'wilds':
        return w.startswith('wilds:')
    if scope == 'parishes':
        return w == 'parishes' or w.startswith('parish:')
    if scope.startswith('page:'):
        return w == scope
    raise ValueError(f'questkit: unknown scope {scope!r}')


def _get(id):
    if id not in BY_ID:
        raise KeyError(f'questkit: {id!r} is not in {REG_PATH}')
    return BY_ID[id]


def egg_attr(id):
    q = _get(id)
    if q['kind'] not in FINDABLE:
        raise ValueError(f'questkit: {id!r} is a {q["kind"]}, not a treasure or egg; use quest_attr')
    _issued.append(id)
    a = f'data-tc-egg="{html.escape(id)}"'
    if 'trigger' in q:
        a += f' data-tc-trigger="{html.escape(q["trigger"])}"'
    if 'target' in q:
        a += f' data-tc-target="{html.escape(q["target"])}"'
    return a


def quest_attr(id):
    q = _get(id)
    if q['kind'] in FINDABLE:
        raise ValueError(f'questkit: {id!r} is a {q["kind"]}; use egg_attr')
    _issued.append(id)
    return f'data-tc-quest="{html.escape(id)}"'


def page_hooks(page):
    """The page's trigger eggs (hidden spans) and its hidden cache (a small
    mark at the foot of the page), for every findable entry of world
    page:<page> that the page does not place itself (entries with a `place`)."""
    out = []
    for q in QUESTS:
        if q['world'] != f'page:{page}' or q['kind'] not in FINDABLE or 'place' in q:
            continue
        if 'trigger' in q:
            out.append(f'<span hidden {egg_attr(q["id"])}></span>')
        else:
            out.append(f'<button type="button" class="tc-cache" {egg_attr(q["id"])} '
                       f'aria-label="{html.escape(q["hint"])}">&#x25C6;</button>')
    if not out:
        raise AssertionError(f'questkit: no hooks for page:{page} in {REG_PATH}')
    return '<div class="tc-hooks">' + ''.join(out) + '</div>\n'


def _rel(current, target):
    return posixpath.relpath(target, posixpath.dirname(current) or '.')


def _data(scope, page):
    qs = [q for q in QUESTS if in_scope(q, scope)]
    if not qs:
        raise AssertionError(f'questkit: no registry entries in scope {scope!r}')
    ref_lessons, ref_halls, ref_quests = set(), set(), set()
    for q in qs:
        ref_lessons.update(q['requires']['lessons'])
        ref_halls.update(q['requires']['halls'])
        ref_quests.update(q['requires']['quests'])
    carried = set(ref_lessons) | {lid for lid, L in LESSONS.items() if L['hall'] in ref_halls}
    lessons = {}
    for lid in sorted(carried):
        L = LESSONS[lid]
        lessons[lid] = {'hall': L['hall'], 'steps': [{k: s[k] for k in STEP_FIELDS if k in s} for s in L['steps']]}
    keep = ('id', 'kind', 'title', 'world', 'place', 'requires', 'unlock_text', 'hint', 'riddle', 'reward', 'band',
            'trigger', 'target')
    return {
        'honesty': HONESTY,
        'keys': KEYS,
        'lessons_href': _rel(page, LESSONS_PAGE),
        'quests_href': _rel(page, QUESTS_PAGE),
        'lessons': lessons,
        'meta': {'step_kinds': STEP_KINDS, 'episode_kinds': EPISODE_KINDS, 'human_actor': HUMAN_ACTOR},
        'titles': {
            'lessons': {lid: LESSONS[lid]['title'] for lid in sorted(carried)},
            'lesson_hall': {lid: LESSONS[lid]['hall'] for lid in sorted(carried)},
            'halls': {h: HALL_NAMES[h] for h in sorted(ref_halls)},
            'quests': {i: BY_ID[i]['title'] for i in sorted(ref_quests)},
        },
        'quests': [{k: q[k] for k in keep if k in q} for q in qs],
    }


GLUE_JS = r"""
const QW = window;
const Q_BY = {};
for (const q of QD.quests) Q_BY[q.id] = q;
const Q_ON = { found: [], done: [], locked: [] };
function qRead(k) { try { return QW.localStorage.getItem(k); } catch (e) { return null; } }
function qJSON(raw) { try { return raw ? JSON.parse(raw) : null; } catch (e) { return null; } }
function qState() { return questParseState(qRead(QUEST_STORE)); }
function qSave(st) { try { QW.localStorage.setItem(QUEST_STORE, JSON.stringify(st)); return true; } catch (e) { return false; } }
function qLessonsDone() { return questLessonsDone(qJSON(qRead(QD.keys.progress)), qJSON(qRead(QD.keys.training)), QD); }
function qEmit(ev, x) { for (const fn of Q_ON[ev]) { try { fn(x); } catch (e) { /* a listener's fault is its own */ } } }
function qEntry(id) { const q = Q_BY[id]; if (!q) throw new Error('quests: ' + id + ' is not carried on this page'); return q; }
function qCheck(id) { return questCheck(qEntry(id), qState(), qLessonsDone(), QD.titles); }
function qToast(msg) {
  let t = document.querySelector('[data-tc-toast]');
  if (!t) { t = document.createElement('div'); t.className = 'tc-toast'; t.setAttribute('data-tc-toast', ''); t.setAttribute('role', 'status'); t.setAttribute('aria-live', 'polite'); document.body.appendChild(t); }
  t.textContent = msg; t.classList.add('on');
  clearTimeout(qToast.h); qToast.h = setTimeout(() => t.classList.remove('on'), 5200);
}
function qRecord(id, findable) {
  const q = qEntry(id);
  if (findable !== QUEST_KINDS_FINDABLE.includes(q.kind)) throw new Error('quests: ' + id + ' is a ' + q.kind);
  const c = qCheck(id);
  if (!c.ok) { qToast('Locked: ' + q.title + '. ' + q.unlock_text); qEmit('locked', { id, check: c }); return c; }
  const r = questRecord(qState(), q, new Date().toISOString(), c);
  if (r.changed) {
    qSave(r.state);
    qToast((findable ? 'Found: ' : 'Done: ') + q.title + ' - badge "' + q.reward.label + '". ' + QD.honesty);
    qEmit(findable ? 'found' : 'done', { id, quest: q });
    qRender();
  }
  return { ok: true };
}
function qRender() {
  for (const el of document.querySelectorAll('[data-tc-questlog]')) {
    if (typeof QW.TCQuestsRender === 'function') { QW.TCQuestsRender(el, QW.TCQuests); continue; }
    const st = qState(); const ld = qLessonsDone();
    const ul = document.createElement('ul'); ul.className = 'tc-log';
    for (const q of QD.quests) {
      const got = (q.id in st.done) || (q.id in st.found);
      const c = questCheck(q, st, ld, QD.titles);
      const li = document.createElement('li');
      li.dataset.state = got ? 'got' : (c.ok ? 'open' : 'locked');
      li.textContent = (got ? '✓ ' : (c.ok ? '○ ' : '■ ')) + q.title + ' - ' + (got ? q.reward.label : (c.ok ? q.hint : q.unlock_text));
      ul.appendChild(li);
    }
    el.replaceChildren(ul);
  }
}
QW.TCQuests = {
  data: QD,
  state: qState,
  lessonsDone: qLessonsDone,
  check: qCheck,
  complete: (id) => qRecord(id, false),
  find: (id) => qRecord(id, true),
  on: (ev, fn) => { if (!(ev in Q_ON)) throw new Error('quests: no event ' + ev); Q_ON[ev].push(fn); },
  render: qRender,
  toast: qToast,
};
function qBind() {
  const words = [];
  const keyed = {};
  for (const el of document.querySelectorAll('[data-tc-egg]')) {
    const id = el.getAttribute('data-tc-egg');
    const trig = el.getAttribute('data-tc-trigger');
    if (!trig) {
      el.addEventListener('click', () => qRecord(id, true));
      el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); qRecord(id, true); } });
    } else if (trig === 'konami' || trig.startsWith('typed:')) {
      if (trig.startsWith('typed:')) words.push(trig.slice(6));
      (keyed[trig] = keyed[trig] || []).push(id);
    } else if (trig.startsWith('clicks:')) {
      const n = Number(trig.slice(7));
      const target = document.querySelector(el.getAttribute('data-tc-target') || '');
      if (!target || !(n > 0)) continue;
      let count = 0; let last = 0;
      target.addEventListener('click', () => {
        const now = performance.now();
        count = (now - last < 1500) ? count + 1 : 1; last = now;
        if (count >= n) { count = 0; qRecord(id, true); }
      });
    }
  }
  let buf = [];
  if (Object.keys(keyed).length) {
    document.addEventListener('keydown', (e) => {
      if (typeof e.key !== 'string') return;
      const r = questKeys(buf, e.key, words); buf = r.buf;
      for (const h of r.hits) for (const id of (keyed[h] || [])) qRecord(id, true);
    });
  }
  for (const el of document.querySelectorAll('[data-tc-quest]')) {
    const id = el.getAttribute('data-tc-quest');
    el.addEventListener('click', () => qRecord(id, false));
  }
  qRender();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', qBind); else qBind();
"""

QUEST_CSS = """
.tc-toast{position:fixed;inset-inline:16px;inset-block-end:16px;max-inline-size:36rem;margin-inline:auto;padding:.7rem 1rem;
  border-radius:10px;background:var(--ink,#1b1f24);color:var(--paper,#fff);font:inherit;font-size:.92rem;line-height:1.4;
  box-shadow:0 6px 24px rgba(0,0,0,.25);opacity:0;transform:translateY(8px);transition:opacity .2s,transform .2s;
  pointer-events:none;z-index:9999}
.tc-toast.on{opacity:1;transform:none}
.tc-hooks{display:flex;justify-content:flex-end;padding:0 16px 8px}
.tc-cache{appearance:none;border:0;background:none;color:inherit;opacity:.18;font-size:.7rem;line-height:1;
  padding:.4rem;cursor:pointer;min-inline-size:24px;min-block-size:24px}
.tc-cache:hover,.tc-cache:focus-visible{opacity:.9}
@media (prefers-reduced-motion:reduce){.tc-toast{transition:none}}
"""


def quest_js(scope, page=None):
    """The <script> block for `scope`. Fails the build if any hook handed out
    by egg_attr/quest_attr since the last call is not in this scope."""
    if page is None:
        if scope.startswith('page:'):
            page = scope[5:]
        elif scope in SCOPE_PAGE:
            page = SCOPE_PAGE[scope]
        else:
            raise ValueError(f'questkit: say which page scope {scope!r} is built into')
    wrong = [i for i in _issued if not in_scope(BY_ID[i], scope)]
    _issued.clear()
    if wrong:
        raise AssertionError(f'questkit: hooks {wrong} are not in scope {scope!r} (their world is elsewhere)')
    d, expand = _compact_story(_data(scope, page))
    data = json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return ('<script data-tc-quests>\n(function () {\n"use strict";\n' + CORE + '\nconst QD = ' + data + ';\n'
            + expand + GLUE_JS + '})();\n</script>\n')


# Wave 7 side-story entries (treasure-story-* / side-story-*, PATHS_CONTRACT v1) repeat the same titles, hints and
# labels in every parish, so a page carries them as compact rows over one shared text table and STORY_EXPAND rebuilds
# the exact entries (and their titles) before the glue runs. Only entries whose full form the row reproduces exactly
# are compacted; pages with none carry byte-identical script as before.
STORY_ID = re.compile(r'^(treasure|side)-story-')
STORY_EXPAND = r"""if (QD.story) {
  const T = QD.story.t;
  for (const r of QD.story.q) {
    const e = { id: r[0], kind: r[1] ? 'side' : 'treasure', title: T[r[2]], world: r[3], place: r[0].replace(/^(treasure|side)-/, ''),
      requires: { lessons: [], halls: [], quests: r[4] }, unlock_text: T[r[5]], hint: T[r[6]], reward: { badge: 'badge-' + r[0], label: T[r[7]] } };
    QD.quests.push(e);
  }
  for (const [i, t] of QD.story.titles) QD.titles.quests[i] = T[t];
  delete QD.story;
}
"""


def _story_full(r, T):
    """Python twin of STORY_EXPAND for one row (key order as in _data's keep)."""
    return {'id': r[0], 'kind': 'side' if r[1] else 'treasure', 'title': T[r[2]], 'world': r[3],
            'place': re.sub(r'^(treasure|side)-', '', r[0]),
            'requires': {'lessons': [], 'halls': [], 'quests': r[4]}, 'unlock_text': T[r[5]], 'hint': T[r[6]],
            'reward': {'badge': 'badge-' + r[0], 'label': T[r[7]]}}


def _compact_story(d):
    table, idx = [], {}

    def t(x):
        if x not in idx:
            idx[x] = len(table)
            table.append(x)
        return idx[x]
    keep, rows, tail = [], [], True
    for q in reversed(d['quests']):   # only the contiguous run of story entries at the end (keeps entry order)
        if tail and STORY_ID.match(q['id']) and q['kind'] in ('treasure', 'side'):
            try:
                r = [q['id'], 1 if q['kind'] == 'side' else 0, t(q['title']), q['world'], q['requires']['quests'],
                     t(q['unlock_text']), t(q['hint']), t(q['reward']['label'])]
            except KeyError:
                r = None
            if r is not None and _story_full(r, table) == q:
                rows.append(r)
                continue
        tail = False
        keep.append(q)
    if not rows:
        return d, ''
    rows.reverse()
    keep.reverse()
    tq = d['titles']['quests']
    moved = [[i, t(tq[i])] for i in sorted(tq) if STORY_ID.match(i)]
    out = dict(d)
    out['quests'] = keep
    out['titles'] = dict(d['titles'], quests={i: v for i, v in tq.items() if not STORY_ID.match(i)})
    out['story'] = {'t': table, 'q': rows, 'titles': moved}
    return out, STORY_EXPAND
