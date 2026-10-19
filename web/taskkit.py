"""taskkit: render simulated tasks from tasks/registry/tasks.json, and nothing else.

Contract: $SP/TASK_CONTRACT.md (TASKS owns). Consumers call these pure helpers;
every figure they print is counted from the registry at build time, and every
launch link is the registry's own href made relative to web/. A task the
registry says no link reaches renders its `why` instead of a button.

    from taskkit import (TASKS, TASKS_CSS, TASK_FILTER_JS, tasks_for,
                         tasks_at_campus, counts_for, task_card, task_board,
                         task_list, tasks_json, rel_href)

Tasks are practice: they certify nothing and enter no completion record.
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG_PATH = ROOT / 'tasks' / 'registry' / 'tasks.json'
TASK_FIELDS = ('id', 'title', 'kind', 'place', 'launch', 'requires', 'provenance', 'source', 'brief', 'seat')
KIND_ORDER = ('sim-scenario', 'walkaround', 'crib-drill', 'crew-handoff',
              'restoration-walk', 'wilds-site-walk', 'resto-scenario')
KIND_GLYPH = {'sim-scenario': '\U0001F3AE', 'walkaround': '\U0001F50E', 'crib-drill': '\U0001F9F0',
              'crew-handoff': '\U0001F91D', 'restoration-walk': '\U0001F33F',
              'wilds-site-walk': '⛰️', 'resto-scenario': '\U0001F30A'}


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise KeyError(f'taskkit: {where} has no "{k}"')
    return d[k]


def _load():
    if not REG_PATH.exists():
        raise SystemExit('taskkit: tasks/registry/tasks.json is missing - run python3 tasks/build.py')
    reg = json.loads(REG_PATH.read_text())
    for k in ('honesty', 'kinds', 'counts', 'tasks'):
        _need(reg, k, 'tasks.json')
    for t in reg['tasks']:
        for f in TASK_FIELDS:
            _need(t, f, f'tasks.json#{t["id"] if "id" in t else "?"}')
        _need(t['place'], 'kind', t['id']); _need(t['place'], 'id', t['id'])
        _need(t['place'], 'campus', t['id']); _need(t['launch'], 'href', t['id'])
        if t['launch']['href'] is None:
            _need(t['launch'], 'why', t['id'])
        else:
            _need(t['launch'], 'lands', t['id'])
        if t['kind'] not in reg['kinds']:
            raise KeyError(f'taskkit: {t["id"]} has unknown kind {t["kind"]}')
    return reg


TASKS = _load()
# linked lessons render by title, read from the registry that owns them; the
# anchor is the one web/build_lessons.py writes and its fromHash() reads
LESSON_PAGE = 'web/trade_craft_lessons.html'
LESSON_TITLES = {k: _need(v, 'title', f'lessons.json#{k}')
                 for k, v in json.loads((ROOT / 'lessons/registry/lessons.json').read_text())['lessons'].items()}
for _t in TASKS['tasks']:
    for _l in _t['requires']:
        if _l not in LESSON_TITLES:
            raise KeyError(f'taskkit: {_t["id"]} links lesson {_l}, not in lessons/registry/lessons.json')
HONESTY = TASKS['honesty']['practice']
e = lambda s: html.escape(str(s), quote=True)  # noqa: E731


def rel_href(href, from_dir='web'):
    """Registry hrefs are repo-root relative; pages in web/ need them relative to web/."""
    if href is None:
        return None
    pre = from_dir.rstrip('/') + '/'
    return href[len(pre):] if href.startswith(pre) else '../' + href


def tasks_for(place_kind, place_id):
    return [t for t in TASKS['tasks'] if t['place']['kind'] == place_kind and t['place']['id'] == place_id]


def tasks_for_seat(sim_id):
    """Every task that runs or walks one simulator seat (scenarios, walkaround, crews on it)."""
    return [t for t in TASKS['tasks'] if t['seat'] == sim_id]


def task_by_id(task_id):
    hit = [t for t in TASKS['tasks'] if t['id'] == task_id]
    if len(hit) != 1:
        raise KeyError(f'taskkit: no single task "{task_id}" in tasks/registry/tasks.json')
    return hit[0]


def tasks_at_campus(campus):
    return [t for t in TASKS['tasks'] if t['place']['campus'] == campus]


def counts_for(tasks):
    by_kind = {}
    for t in tasks:
        by_kind[t['kind']] = by_kind[t['kind']] + 1 if t['kind'] in by_kind else 1
    return {'total': len(tasks), 'by_kind': by_kind,
            'launchable': sum(1 for t in tasks if t['launch']['href'])}


VIA_EN = 'Opens at the {hall} hall, {campus}'


def _kind_label(kind, labels):
    return labels['kind.' + kind] if labels and ('kind.' + kind) in labels else TASKS['kinds'][kind]['label']


def _lbl(labels, key, en):
    return labels[key] if labels and key in labels else en


def task_card(t, labels=None, from_dir='web'):
    """One task. `labels` is an optional dict of tasks.* strings (already localized)."""
    href = rel_href(t['launch']['href'], from_dir)
    lessons = ''
    if t['requires']:
        links = ' '.join(
            f'<a class="tk-lesson" href="{e(rel_href(LESSON_PAGE, from_dir))}#lesson-{e(l)}">{e(LESSON_TITLES[l])}</a>'
            for l in t['requires'])
        lessons = f'<p class="tk-req"><span>{e(_lbl(labels, "linked", "Linked lessons"))}:</span> {links}</p>'
    if href:
        go = (f'<a class="tk-go" href="{e(href)}" data-lands="{e(t["launch"]["lands"])}">'
              f'{e(_lbl(labels, "launch", "Launch"))} → '
              f'<small>{e(_lbl(labels, "lands." + t["launch"]["lands"], t["launch"]["lands"]))}</small></a>')
    else:
        go = f'<p class="tk-why"><b>{e(_lbl(labels, "nolink", "No launch link"))}:</b> {e(t["launch"]["why"])}</p>'
    if href and 'via' in t['launch']:
        # the seat opens at a hall on ANOTHER campus than the task's place: say so
        v = t['launch']['via']
        go = (f'<p class="tk-via" data-via-hall="{e(v["hall"])}" data-via-campus="{e(v["campus"])}">'
              + e(_lbl(labels, 'via', VIA_EN).replace('{hall}', v['hall_name']).replace('{campus}', v['campus_name']))
              + '</p>' + go)
    return (f'<article class="tk-card" data-task="{e(t["id"])}" data-kind="{e(t["kind"])}">'
            f'<div class="tk-head"><span class="tk-kind">{KIND_GLYPH[t["kind"]]} {e(_kind_label(t["kind"], labels))}</span>'
            f'<span class="tk-prov">{e(t["provenance"])}</span></div>'
            f'<h4>{e(t["title"])}</h4><p class="tk-brief">{e(t["brief"])}</p>{lessons}{go}</article>')


def task_list(tasks, labels=None, from_dir='web'):
    items = []
    for t in tasks:
        href = rel_href(t['launch']['href'], from_dir)
        name = f'<a href="{e(href)}">{e(t["title"])}</a>' if href else e(t['title'])
        items.append(f'<li data-task="{e(t["id"])}" data-kind="{e(t["kind"])}">{KIND_GLYPH[t["kind"]]} {name}</li>')
    return f'<ul class="tk-list">{"".join(items)}</ul>'


def task_board(tasks, title, labels=None, from_dir='web', board_id='tk-board'):
    """A filterable board (a div role=region, never a <section>: page suites slice their own sections): counts computed here from `tasks`, chips per kind present."""
    c = counts_for(tasks)
    kinds = [k for k in KIND_ORDER if k in c['by_kind']]
    chips = [f'<button type="button" class="tk-chip" aria-pressed="true" data-tk-filter="all">'
             f'{e(_lbl(labels, "all", "All"))} <b>{c["total"]}</b></button>']
    for k in kinds:
        chips.append(f'<button type="button" class="tk-chip" aria-pressed="false" data-tk-filter="{e(k)}">'
                     f'{KIND_GLYPH[k]} {e(_kind_label(k, labels))} <b>{c["by_kind"][k]}</b></button>')
    summary = _lbl(labels, 'summary', '{n} tasks, {l} with a launch link').replace(
        '{n}', str(c['total'])).replace('{l}', str(c['launchable']))
    cards = ''.join(task_card(t, labels, from_dir) for t in tasks)
    return (f'<div class="tk-board" role="region" aria-label="{e(title)}" id="{e(board_id)}" data-tk-board data-total="{c["total"]}">'
            f'<h3>{e(title)}</h3><p class="tk-sum">{e(summary)}</p>'
            f'<div class="tk-chips" role="group" aria-label="{e(_lbl(labels, "filter", "Filter by kind"))}">{"".join(chips)}</div>'
            f'<div class="tk-cards">{cards}</div>'
            f'<p class="tk-honest">{e(_lbl(labels, "honesty", HONESTY))}</p></div>')


def tasks_json(tasks, from_dir='web'):
    return json.dumps([{'id': t['id'], 'title': t['title'], 'kind': t['kind'], 'place': t['place'],
                        'href': rel_href(t['launch']['href'], from_dir),
                        'lands': t['launch']['lands'] if t['launch']['href'] else None,
                        'why': None if t['launch']['href'] else t['launch']['why'],
                        'via': t['launch']['via'] if 'via' in t['launch'] else None,
                        'requires': [{'id': l, 'title': LESSON_TITLES[l]} for l in t['requires']],
                        'brief': t['brief'], 'provenance': t['provenance']}
                       for t in tasks], ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


# colours are ONLY the page's theme tokens (var(--...)); no hex here, so every
# site style/theme applies to the boards
TASKS_CSS = '''
.tk-board{color:var(--ink);border:1px solid var(--rule);border-radius:10px;background:var(--panel);padding:14px 16px;margin:14px 0}
.tk-board h3{margin:0 0 4px;font-size:18px;color:var(--ink)}
.tk-board p{max-width:none}
.tk-sum,.tk-honest{color:var(--muted);font-size:13px;margin:4px 0 10px}
.tk-honest{margin-top:12px;border-top:1px solid var(--rule);padding-top:8px}
.tk-chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
.tk-chip{font:600 13px/1 inherit;font-family:inherit;background:transparent;color:var(--ink);border:1px solid var(--rule);border-radius:999px;padding:8px 12px;min-height:36px;cursor:pointer}
.tk-chip[aria-pressed="true"]{border-color:var(--mark);box-shadow:inset 0 0 0 1px var(--mark)}
.tk-chip b{color:var(--mark);margin-left:4px}
.tk-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.tk-card{border:1px solid var(--rule);border-radius:8px;padding:10px 12px;display:flex;flex-direction:column;gap:4px;min-width:0}
.tk-card[hidden]{display:none}
.tk-head{display:flex;justify-content:space-between;gap:8px;font-size:12px;color:var(--muted);padding:0;margin:0;border:0}
.tk-prov{font:600 11px/1.4 ui-monospace,monospace;letter-spacing:.04em}
.tk-card h4{color:var(--ink);margin:2px 0;font-size:15px;line-height:1.3;overflow-wrap:anywhere}
.tk-brief{margin:0;font-size:13px;color:var(--muted);overflow-wrap:anywhere}
.tk-req{margin:2px 0;font-size:12px;overflow-wrap:anywhere}
.tk-req span{color:var(--muted)}
.tk-board a.tk-lesson{color:var(--steel);margin-inline-end:4px;font:inherit;font-size:12px;text-decoration:underline}
.tk-board a.tk-go{font-family:inherit;margin-top:auto;align-self:flex-start;display:inline-flex;gap:6px;align-items:center;min-height:36px;padding:7px 12px;border-radius:6px;background:var(--mark);color:var(--mark-ink);font-weight:600;text-decoration:none;font-size:14px}
.tk-board a.tk-go small{font-family:inherit;font-weight:400;opacity:.85}
.tk-why{margin:auto 0 0;font-size:12px;color:var(--muted)}
.tk-via{margin:auto 0 6px;font-size:12px;color:var(--ink);border-left:3px solid var(--mark);padding-left:6px}
.tk-board .tk-via+a.tk-go{margin-top:0}
.tk-list{list-style:none;padding:0;margin:4px 0;font-size:13px}
.tk-list li{padding:2px 0}
'''

# one delegated listener for every [data-tk-board], including boards a page
# injects later (a detail panel); safe to include once
TASK_FILTER_SRC = '''
document.addEventListener('click', function (ev) {
  var b = ev.target.closest && ev.target.closest('[data-tk-filter]'); if (!b) return;
  var board = b.closest('[data-tk-board]'); if (!board) return;
  var k = b.getAttribute('data-tk-filter');
  board.querySelectorAll('[data-tk-filter]').forEach(function (c) {
    c.setAttribute('aria-pressed', String(c === b)); });
  board.querySelectorAll('.tk-card').forEach(function (c) {
    c.hidden = !(k === 'all' || c.getAttribute('data-kind') === k); });
});
'''
TASK_FILTER_JS = '<script>' + TASK_FILTER_SRC + '</script>'


def labels_from(strings):
    """The tasks.* strings of one locale catalog, keyed without the prefix."""
    return {k[len('tasks.'):]: v for k, v in strings.items() if k.startswith('tasks.')}


KIND_GLYPH_JSON = json.dumps(KIND_GLYPH, ensure_ascii=False)

# The same board as task_board()/task_card(), for pages that render in the
# browser in the viewer's locale. Plain JS (no <script> tag) so a page can
# inline it inside its own main script. Takes the rows tasks_json() emits and
# a label function L(key, english) for the tasks.* strings.
TASK_RENDER_JS = """
const tcTaskEsc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
const TC_TASK_GLYPH = """ + KIND_GLYPH_JSON + """;
const TC_TASK_KINDS = """ + json.dumps(list(KIND_ORDER)) + """;
const TC_TASK_KIND_EN = """ + json.dumps({k: v['label'] for k, v in TASKS['kinds'].items()}, ensure_ascii=False) + """;
function tcTaskCard(t, L, lessonHref) {
  const E = tcTaskEsc;
  const req = t.requires.length ? `<p class="tk-req"><span>${E(L('linked', 'Linked lessons'))}:</span> ` +
    t.requires.map((l) => `<a class="tk-lesson" href="${E(lessonHref)}#lesson-${E(l.id)}">${E(l.title)}</a>`).join(' ') + '</p>' : '';
  const go = t.href
    ? `<a class="tk-go" href="${E(t.href)}" data-lands="${E(t.lands)}">${E(L('launch', 'Launch'))} \u2192 <small>${E(L('lands.' + t.lands, t.lands))}</small></a>`
    : `<p class="tk-why"><b>${E(L('nolink', 'No launch link'))}:</b> ${E(t.why)}</p>`;
  // the seat opens at a hall on ANOTHER campus than the task's place: say so
  const via = t.href && t.via
    ? `<p class="tk-via" data-via-hall="${E(t.via.hall)}" data-via-campus="${E(t.via.campus)}">${E(L('via', 'Opens at the {hall} hall, {campus}').replace('{hall}', t.via.hall_name).replace('{campus}', t.via.campus_name))}</p>`
    : '';
  return `<article class="tk-card" data-task="${E(t.id)}" data-kind="${E(t.kind)}"><div class="tk-head"><span class="tk-kind">${TC_TASK_GLYPH[t.kind]} ${E(L('kind.' + t.kind, TC_TASK_KIND_EN[t.kind]))}</span>` +
    `<span class="tk-prov">${E(t.provenance)}</span></div><h4>${E(t.title)}</h4><p class="tk-brief">${E(t.brief)}</p>${req}${via}${go}</article>`;
}
function tcTaskBoard(tasks, title, L, lessonHref, boardId) {
  const E = tcTaskEsc;
  const by = {}; let launchable = 0;
  for (const t of tasks) { by[t.kind] = (by[t.kind] || 0) + 1; if (t.href) launchable++; }
  const chips = [`<button type="button" class="tk-chip" aria-pressed="true" data-tk-filter="all">${E(L('all', 'All'))} <b>${tasks.length}</b></button>`]
    .concat(TC_TASK_KINDS.filter((k) => by[k]).map((k) => `<button type="button" class="tk-chip" aria-pressed="false" data-tk-filter="${k}">${TC_TASK_GLYPH[k]} ${E(L('kind.' + k, TC_TASK_KIND_EN[k]))} <b>${by[k]}</b></button>`));
  const sum = L('summary', '{n} tasks, {l} with a launch link').replace('{n}', tasks.length).replace('{l}', launchable);
  return `<div class="tk-board" role="region" aria-label="${E(title)}" id="${E(boardId)}" data-tk-board data-total="${tasks.length}"><h3>${E(title)}</h3><p class="tk-sum">${E(sum)}</p>` +
    `<div class="tk-chips" role="group" aria-label="${E(L('filter', 'Filter by kind'))}">${chips.join('')}</div>` +
    `<div class="tk-cards">${tasks.map((t) => tcTaskCard(t, L, lessonHref)).join('')}</div>` +
    `<p class="tk-honest">${E(L('honesty', ''))}</p></div>`;
}
"""
