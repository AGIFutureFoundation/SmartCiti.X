"""The site search: one client-side index, built from the registries.

A visitor who knows what they want - "crane", "rigging", "verify" - should
not have to learn the site's map to reach it. This builds, at page-build
time, a small index of every page in web/sitenav.py, every lesson, every
hall, every simulator seat and every quest a player can look for, and the
markup + script for a command palette over it (Ctrl/Cmd+K, or the visible
search button). Nothing is fetched at run time; the index is JSON in the
page.

Each entry's link uses a scheme a page already honours, never a new one:
  lesson  -> web/trade_craft_lessons.html?hall=<its hall>   (the course page)
  hall    -> web/trade_craft_lessons.html?hall=<slug> when a course stands in
             it, else web/trade_craft_3d.html?hall=<slug>    (the 3D hall)
  seat    -> web/trade_craft_3d.html?sim=<id>
  quest   -> web/trade_craft_quests.html                     (main/side/game only:
             treasures and eggs are for finding, so the index does not list them)

Fail closed: every field is read with a subscript or need(); a missing one
stops the build with its name.

    from sitesearch import search_index, SEARCH_CSS, search_button, search_dialog, SEARCH_JS
    from sitesearch import search_trigger, SEARCH_TRIGGER_JS, SEARCH_TRIGGER_CSS   # any other page
"""
import html
import json
import pathlib
import posixpath

# ---------------------------------------------------- every other page ------
# The palette and its index live on the front door. Every other page reaches
# it through one plain link, `index.html#search`, which the front door's
# script turns into an open palette. The link is markup only (the site header
# carries no script), works without script (it lands on the front door), and
# costs a page no index bytes. SEARCH_TRIGGER_JS is optional and goes after
# a page's own scripts, never in the header: it makes Ctrl/Cmd+K follow the
# link on a page that has no palette of its own. This block is defined before
# this module reads sitenav, because sitenav imports it back (so either
# import order works).
SEARCH_HASH = 'search'


def search_trigger(current_path, label='Search'):
    """The header link to the front door's palette, relative to current_path."""
    from sitenav import FRONT_DOOR   # at call time: sitenav imports this module
    base = posixpath.dirname(current_path)
    href = posixpath.relpath(FRONT_DOOR, base or '.') + '#' + SEARCH_HASH
    if current_path == FRONT_DOOR:
        href = '#' + SEARCH_HASH
    return (f'<a class="ss-go" href="{html.escape(href)}" data-search-go '
            'aria-keyshortcuts="Control+K Meta+K">'
            '<svg aria-hidden="true" viewBox="0 0 20 20" width="16" height="16"><circle cx="8.5" cy="8.5" '
            'r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M13 13l4.5 4.5" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
            f'<span>{html.escape(label)}</span></a>')


SEARCH_TRIGGER_JS = r"""<script id="ss-go-js">
(function () {
  if (document.querySelector('dialog.ss-dlg')) return;   /* the front door handles its own keys */
  document.addEventListener('keydown', function (ev) {
    if ((ev.ctrlKey || ev.metaKey) && !ev.altKey && (ev.key === 'k' || ev.key === 'K')) {
      var a = document.querySelector('a[data-search-go]');
      if (a) { ev.preventDefault(); location.href = a.href; }
    }
  });
}());
</script>"""

SEARCH_TRIGGER_CSS = """
.ss-go{display:inline-flex;align-items:center;gap:6px;min-block-size:44px;padding-inline:10px;white-space:nowrap;flex:none;
  color:inherit;text-decoration:none;border-radius:8px}
.ss-go:hover{text-decoration:underline}
.ss-go:focus-visible{outline:none;box-shadow:var(--focus)}
"""



from sitenav import PAGES, labels as nav_labels  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

LESSONS_PATH = 'lessons/registry/lessons.json'
HALLS_PATH = 'pack/registry/halls.json'
SIMS_PATH = 'sims/registry/sims.json'
QUESTS_PATH = 'quests/registry/quests.json'
QUEST_KINDS_LISTED = ('main', 'side', 'game')

# The type words the palette shows beside a result, in one place.
TYPES = {'page': 'Page', 'lesson': 'Lesson', 'hall': 'Hall', 'seat': 'Simulator seat',
         'quest': 'Quest'}


def need(node, key, where):
    if not isinstance(node, dict) or key not in node:
        raise KeyError(f'sitesearch: {where} has no `{key}`')
    return node[key]


def _read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def search_index():
    """[{t: type, n: name, d: detail, u: url from the bundle root}] in a
    stable order: pages, lessons, halls, seats, quests."""
    nav = nav_labels('en')
    out = []
    for path, (group, key) in PAGES.items():
        out.append({'t': 'page', 'n': nav[key], 'd': nav[group], 'u': path})

    lessons = need(_read(LESSONS_PATH), 'lessons', LESSONS_PATH)
    course_halls = set()
    for lid, row in lessons.items():
        w = f'{LESSONS_PATH}#lessons.{lid}'
        hall = need(row, 'hall', w)
        course_halls.add(hall)
        out.append({'t': 'lesson', 'n': need(row, 'title', w),
                    'd': need(row, 'hall_name', w),
                    'u': f'web/trade_craft_lessons.html?hall={hall}'})

    for h in need(_read(HALLS_PATH), 'halls', HALLS_PATH):
        w = f'{HALLS_PATH}#halls[]'
        slug = need(h, 'slug', w)
        url = (f'web/trade_craft_lessons.html?hall={slug}' if slug in course_halls
               else f'web/trade_craft_3d.html?hall={slug}')
        out.append({'t': 'hall', 'n': need(h, 'name', w), 'd': need(h, 'focus', w), 'u': url})

    for sid, s in need(_read(SIMS_PATH), 'sims', SIMS_PATH).items():
        w = f'{SIMS_PATH}#sims.{sid}'
        out.append({'t': 'seat', 'n': need(s, 'name', w), 'd': need(s, 'task', w),
                    'u': f'web/trade_craft_3d.html?sim={sid}'})

    # Quests are published by another pack this wave; until its registry
    # exists the index simply has no quest rows (the existence test is on
    # the FILE, not a default for a missing field).
    if (ROOT / QUESTS_PATH).exists():
        for q in need(_read(QUESTS_PATH), 'quests', QUESTS_PATH):
            w = f'{QUESTS_PATH}#quests[]'
            if need(q, 'kind', w) in QUEST_KINDS_LISTED:
                out.append({'t': 'quest', 'n': need(q, 'title', w), 'd': need(q, 'hint', w),
                            'u': 'web/trade_craft_quests.html'})
    for e in out:
        assert e['u'].split('?')[0] in PAGES, f'sitesearch: {e["u"]} is not a page'
    return out


def search_button(label='Search pages, lessons, halls and seats'):
    return ('<button type="button" id="' + SEARCH_HASH + '" class="ss-open" data-search-open hidden '
            'aria-haspopup="dialog" aria-controls="ss-dlg" aria-keyshortcuts="Control+K Meta+K">'
            '<svg aria-hidden="true" viewBox="0 0 20 20" width="18" height="18"><circle cx="8.5" cy="8.5" r="5.5" '
            'fill="none" stroke="currentColor" stroke-width="2"/><path d="M13 13l4.5 4.5" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
            f'<span class="ss-label">{html.escape(label)}</span>'
            '<kbd class="ss-kbd" data-search-kbd>Ctrl K</kbd></button>')


def search_dialog(current_path):
    """The palette. Hrefs in the index are from the bundle root; the script
    rewrites them relative to `current_path`'s directory."""
    base = posixpath.dirname(current_path)
    prefix = posixpath.relpath('.', base) + '/' if base else ''
    idx = json.dumps(search_index(), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    types = json.dumps(TYPES, separators=(',', ':'))
    return (
        '<dialog id="ss-dlg" class="ss-dlg" aria-labelledby="ss-title">'
        '<form method="dialog" class="ss-form" role="search">'
        '<h2 id="ss-title" class="ss-title">Search this site</h2>'
        '<label class="ss-lbl" for="ss-q">Search pages, lessons, halls, simulator seats and quests</label>'
        '<input id="ss-q" class="ss-q" type="search" autocomplete="off" spellcheck="false" '
        'role="combobox" aria-expanded="true" aria-controls="ss-list" aria-autocomplete="list" '
        'placeholder="Try: crane, rigging, verify">'
        '<p id="ss-status" class="ss-status" role="status" aria-live="polite"></p>'
        '<ul id="ss-list" class="ss-list" role="listbox" aria-label="Results"></ul>'
        '<p class="ss-help"><kbd>&uarr;</kbd><kbd>&darr;</kbd> move &middot; <kbd>Enter</kbd> open '
        '&middot; <kbd>Esc</kbd> close</p>'
        '<button class="ss-close" value="close" aria-label="Close search">&times;</button>'
        '</form></dialog>\n'
        f'<script type="application/json" id="ss-index" data-prefix="{html.escape(prefix)}">{idx}</script>\n'
        f'<script id="ss-types" type="application/json">{types}</script>\n')


SEARCH_JS = r"""<script id="ss-js">
/* The command palette. Opens on the visible button or Ctrl/Cmd+K, filters
   the in-page index as you type (every word must match, name or detail),
   arrow keys move the active option, Enter follows it, Esc closes and
   returns focus to where it was. The button stays hidden without script,
   so no control is ever offered that cannot work. */
(function () {
  var dlg = document.getElementById('ss-dlg');
  var q = document.getElementById('ss-q');
  var list = document.getElementById('ss-list');
  var status = document.getElementById('ss-status');
  var idxEl = document.getElementById('ss-index');
  if (!dlg || !q || !list || !idxEl || typeof dlg.showModal !== 'function') return;
  var INDEX = JSON.parse(idxEl.textContent);
  var TYPES = JSON.parse(document.getElementById('ss-types').textContent);
  var PREFIX = idxEl.getAttribute('data-prefix');
  var MAX = 40, active = -1, rows = [], back = null;
  var mac = /Mac|iPhone|iPad/.test(navigator.platform);
  document.querySelectorAll('[data-search-kbd]').forEach(function (k) { k.textContent = mac ? '⌘ K' : 'Ctrl K'; });
  function fold(s) { return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }
  INDEX.forEach(function (e) { e.k = fold(e.n + ' ' + e.d + ' ' + TYPES[e.t]); e.nk = fold(e.n); });
  function score(e, words) {
    var s = 0;
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (e.k.indexOf(w) < 0) return -1;
      if (e.nk.indexOf(w) === 0) s += 6; else if (e.nk.indexOf(' ' + w) >= 0) s += 4;
      else if (e.nk.indexOf(w) >= 0) s += 2; else s += 1;
    }
    return s + (e.t === 'page' ? 1 : 0);
  }
  function render() {
    var words = fold(q.value).split(/\s+/).filter(Boolean);
    var hits;
    if (!words.length) hits = INDEX.filter(function (e) { return e.t === 'page'; });
    else hits = INDEX.map(function (e) { return [score(e, words), e]; })
      .filter(function (p) { return p[0] >= 0; })
      .sort(function (a, b) { return b[0] - a[0]; }).map(function (p) { return p[1]; });
    var total = hits.length;
    rows = hits.slice(0, MAX);
    list.textContent = '';
    rows.forEach(function (e, i) {
      var li = document.createElement('li');
      li.id = 'ss-o' + i; li.setAttribute('role', 'option'); li.setAttribute('aria-selected', 'false');
      var a = document.createElement('a'); a.href = PREFIX + e.u; a.tabIndex = -1;
      var t = document.createElement('span'); t.className = 'ss-type'; t.textContent = TYPES[e.t];
      var n = document.createElement('span'); n.className = 'ss-name'; n.textContent = e.n;
      var d = document.createElement('span'); d.className = 'ss-detail'; d.textContent = e.d;
      a.appendChild(t); a.appendChild(n); a.appendChild(d); li.appendChild(a);
      li.addEventListener('mousemove', function () { move(i); });
      list.appendChild(li);
    });
    status.textContent = !words.length ? 'Showing every page. Type to search.'
      : total === 0 ? 'No results.' : total > MAX ? total + ' results, showing the first ' + MAX + '.'
      : total + (total === 1 ? ' result.' : ' results.');
    move(rows.length ? 0 : -1);
  }
  function move(i) {
    var o = list.children;
    if (active >= 0 && o[active]) o[active].setAttribute('aria-selected', 'false');
    active = i;
    if (i >= 0 && o[i]) {
      o[i].setAttribute('aria-selected', 'true');
      q.setAttribute('aria-activedescendant', o[i].id);
      o[i].scrollIntoView({ block: 'nearest' });
    } else q.removeAttribute('aria-activedescendant');
  }
  function open() {
    if (dlg.open) return;
    back = document.activeElement;
    dlg.showModal(); q.value = ''; render(); q.focus();
  }
  dlg.addEventListener('close', function () { if (back && back.focus) back.focus(); });
  dlg.addEventListener('click', function (ev) { if (ev.target === dlg) dlg.close(); });
  q.addEventListener('input', render);
  q.addEventListener('keydown', function (ev) {
    if (ev.key === 'ArrowDown') { ev.preventDefault(); if (rows.length) move((active + 1) % rows.length); }
    else if (ev.key === 'ArrowUp') { ev.preventDefault(); if (rows.length) move((active - 1 + rows.length) % rows.length); }
    else if (ev.key === 'Home' && ev.ctrlKey) { ev.preventDefault(); move(rows.length ? 0 : -1); }
    // a search box eats the first Esc to clear itself; here Esc always closes
    else if (ev.key === 'Escape') { ev.preventDefault(); dlg.close(); }
    else if (ev.key === 'Enter') {
      ev.preventDefault();
      var a = active >= 0 && list.children[active] ? list.children[active].querySelector('a') : null;
      if (a) location.href = a.href;
    }
  });
  document.querySelectorAll('[data-search-open]').forEach(function (b) {
    b.hidden = false; b.addEventListener('click', open);
  });
  /* index.html#search: every other page's header link lands here (sitesearch.search_trigger) */
  function fromHash() {
    if (location.hash !== '#search') return;
    history.replaceState(null, '', location.pathname + location.search);
    open();
  }
  window.addEventListener('hashchange', fromHash);
  fromHash();
  document.addEventListener('keydown', function (ev) {
    if ((ev.ctrlKey || ev.metaKey) && !ev.altKey && (ev.key === 'k' || ev.key === 'K')) {
      ev.preventDefault(); if (dlg.open) dlg.close(); else open();
    }
  });
}());
</script>"""


SEARCH_CSS = """
.ss-open{display:flex;align-items:center;gap:10px;inline-size:100%;max-inline-size:34rem;
  min-block-size:46px;margin-block-start:var(--s4,16px);padding-block:0;padding-inline:14px;
  background:var(--panel);color:var(--muted);border:1px solid var(--rule-2);
  border-radius:var(--r-md,10px);font:inherit;font-size:15px;cursor:pointer;text-align:start;
  box-shadow:var(--shadow)}
.ss-open[hidden]{display:none}
.ss-open:hover{border-color:var(--mark);color:var(--ink)}
.ss-open:focus-visible{outline:none;box-shadow:var(--focus)}
.ss-label{flex:1 1 auto;min-inline-size:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ss-kbd,.ss-help kbd{font:600 12px/1 var(--mono,monospace);padding:4px 6px;border-radius:5px;
  border:1px solid var(--rule-2);background:var(--sunk);color:var(--ink);white-space:nowrap}
.ss-dlg{inline-size:min(40rem,calc(100vw - 24px));max-block-size:min(34rem,calc(100dvh - 48px));
  margin-block-start:min(12vh,96px);padding:0;border:1px solid var(--rule-2);border-radius:14px;
  background:var(--panel);color:var(--ink);box-shadow:0 24px 64px -16px rgba(0,0,0,.6);overflow:hidden}
.ss-dlg::backdrop{background:rgba(5,9,10,.62)}
.ss-form{display:flex;flex-direction:column;max-block-size:inherit;position:relative;padding:14px}
.ss-title{font:700 20px/1.2 var(--display,inherit);margin:0 44px 6px 0}
.ss-lbl{font-size:13px;color:var(--muted);margin-block-end:6px}
.ss-q{font:inherit;font-size:17px;padding:10px 12px;border-radius:8px;border:1px solid var(--rule-2);
  background:var(--sunk);color:var(--ink);inline-size:100%}
.ss-q:focus-visible{outline:none;box-shadow:var(--focus)}
.ss-status{font-size:13px;color:var(--muted);margin:8px 2px 6px;min-block-size:1.2em}
.ss-list{list-style:none;margin:0;padding:0;overflow:auto;flex:1 1 auto;min-block-size:0}
.ss-list li a{display:grid;grid-template-columns:8.5em minmax(0,1fr);column-gap:10px;
  padding:8px 10px;border-radius:8px;color:var(--ink);text-decoration:none}
.ss-list li[aria-selected="true"] a{background:var(--sunk);box-shadow:inset 3px 0 0 var(--mark)}
.ss-type{grid-row:1/3;font:600 11.5px/1.5 var(--mono,monospace);letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);padding-block-start:2px}
.ss-name{font-weight:600}
.ss-detail{font-size:13px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ss-help{font-size:12.5px;color:var(--muted);margin:10px 2px 0;display:flex;gap:6px;align-items:center;
  flex-wrap:wrap}
.ss-close{position:absolute;inset-block-start:10px;inset-inline-end:10px;inline-size:40px;block-size:40px;
  border-radius:8px;border:1px solid var(--rule);background:transparent;color:var(--ink);
  font-size:22px;line-height:1;cursor:pointer}
.ss-close:focus-visible{outline:none;box-shadow:var(--focus)}
@media(max-width:520px){.ss-list li a{grid-template-columns:1fr}.ss-type{grid-row:auto}
  .ss-kbd{display:none}}
"""
