"""worldmodules: the world training modules section of the Courses page (wave 19).

Reads modules/registry/modules.json (python3 modules/build.py) and builds one card per module: its Omega Hive greeter
(SCRIPTED, no AI model, the device's speech synthesis, on a click, through hivekit's HiveVoice), its brief quoted
verbatim with each source path, its ordered steps (existing step kinds only, registry text in English), where to go
in the worlds, and the supplements of its lessons (the page's own ?lesson= viewer). Every chrome word is a wmod.* key
present in all 8 locales; the Hive voice words are the existing hive.* keys. The page marker is WORLD-PRACTICE.

Called from the anchored block in web/build_courses.py: prepare() adds the words to the page catalogue and returns
the section; inject() places it before the rules box. Nothing is stored and nothing speaks on load.
"""
import html
import json
import pathlib

E = lambda s: html.escape(str(s), quote=True)
HERE = pathlib.Path(__file__).resolve().parent
ANCHOR = '<section class="box" id="course-rules"'
SCRIPT_ANCHOR = '<script id="course-page">'
TAG, LEDE, EN_OPEN = ' class="tag"', ' class="lede"', ' <span lang="en">'
FAMILIES = ['worksite-district', 'restoration-site', 'wilds-world', 'robot-yard']
HIVE_KEYS = ['hive.speak', 'hive.v.mute', 'hive.v.muted', 'hive.v.nosynth', 'hive.v.novoice', 'hive.v.refused',
             'hive.v.speaking', 'hive.v.done', 'hive.v.stopped']


class WorldModuleError(Exception):
    pass


def need(c, m):
    if not c:
        raise WorldModuleError('worldmodules: ' + m)


def step_text(s):
    """The registry's own words for a step, in English, never retyped."""
    if 'do' in s:
        return s['do']
    k = s['kind']
    if k == 'crew':
        return f'{s["role"]}: "{s["ask"]}"'
    if k == 'walkaround':
        return f'{s["label"]}: {s["check"]}'
    if k == 'sim':
        return f'{s["seat_name"]} · {s["scenario_name"]}'
    if k == 'station':
        return s['station_name']
    if k == 'world-teleop':
        return s['note']
    raise WorldModuleError(f'worldmodules: no text rule for step kind {k!r}')


def go_links(m):
    """(href, wmod key) pairs: where the module is practised in the worlds. Every target page must exist."""
    f = m['family']
    if f == 'worksite-district':
        out = [(f'trade_craft_worksites.html#site-{p["worksite"]}', 'wmod.go.site', p['title']) for p in m['places']]
    elif f == 'restoration-site':
        out = [(r['href'].removeprefix('web/'), 'wmod.go.runner', r['task']) for r in m['runners']]
    elif f == 'wilds-world':
        w = m['world'].split(':', 1)[1]
        out = [(f'trade_craft_wilds.html#{w}/{p["wilds_site"]}', 'wmod.go.site', p['title']) for p in m['places']]
    else:
        out = [('trade_craft_parishes.html', 'wmod.go.watch', None), ('trade_craft_robotics.html', 'wmod.go.drive', None)]
    for h, _, _ in out:
        need((HERE / h.split('#')[0]).exists(), f'{m["id"]}: linked page {h} does not exist')
    return out


def prepare(root, i18n, sup, page_need):
    reg = json.loads((root / 'modules/registry/modules.json').read_text(encoding='utf-8'))
    for k in ('source_stamp', 'modules', 'refused', 'counts', 'honesty', 'step_kinds'):
        need(k in reg, f'modules.json has no {k!r}; run python3 modules/build.py')
    # the words: every wmod.* key of en, non-empty in every locale, plus the hive voice words
    en_all = json.loads((root / 'i18n/locales/en.json').read_text(encoding='utf-8'))['strings']
    keys = sorted(k for k in en_all if k.startswith('wmod.')) + HIVE_KEYS
    need(len(keys) > 20, 'the wmod.* keys are missing from i18n/locales/en.json')
    for loc in i18n:
        s = json.loads((root / f'i18n/locales/{loc}.json').read_text(encoding='utf-8'))['strings']
        for k in keys:
            need(isinstance(s.get(k), str) and s[k].strip(), f'locale {loc} is missing {k}')
            i18n[loc]['strings'][k] = s[k]
    EN = i18n['en']['strings']
    for kind in reg['step_kinds']:
        need(f'wmod.k.{kind}' in EN, f'no wmod.k.{kind} word')
    for fam in FAMILIES:
        need(f'wmod.fam.{fam}' in EN, f'no wmod.fam.{fam} word')

    def T(k, tag='span', attrs=''):
        need(k in EN, f'no {k} in the catalogue')
        return f'<{tag}{attrs} data-i18n="{k}">{E(EN[k])}</{tag}>'

    import sys
    sys.path.insert(0, str(HERE))
    from hivekit import voice_data, js_json, HIVE_JS  # noqa: E402
    agents = sorted({m['greeter']['agent'] for m in reg['modules']})
    voices = voice_data(agents)
    need(sorted(a['id'] for a in voices['agents']) == agents, 'a greeter has no Hive voice row')
    lines = {m['id']: [m['greeter']['agent'], m['greeter']['line']] for m in reg['modules']}

    cards = ''
    for m in reg['modules']:
        need(m['family'] in FAMILIES, f'{m["id"]}: unknown family')
        g = m['greeter']
        brief = ''.join(f'<li><span lang="en">{E(b["text"])}</span> <code class="wmod-src">{E(b["source"])}</code></li>' for b in m['brief'])
        steps = ''.join(f'<li data-kind="{E(s["kind"])}">{T("wmod.k." + s["kind"], "span", TAG)} '
                        f'<span lang="en">{E(step_text(s))}</span></li>' for s in m['steps'])
        go = ' · '.join(f'<a href="{E(h)}" data-wmod-go="{E(k)}">{T(k)}{(EN_OPEN + E(t) + "</span>") if t else ""}</a>'
                        for h, k, t in go_links(m))
        for lid in m['supplements']:
            page_need(lid in sup, f'module {m["id"]}: supplement {lid} is not on this page')
        supp = ' · '.join(f'<a href="?lesson={E(l)}#course-sup" data-sup="{E(l)}">{E(sup[l]["title"])}</a>' for l in m['supplements'])
        cards += (
            f'<details class="wmod" id="{E(m["id"])}" data-wmod="{E(m["id"])}" data-wmod-family="{E(m["family"])}">'
            f'<summary><span class="ct" lang="en">{E(m["title"])}</span> {T("wmod.fam." + m["family"], "span", TAG)} '
            f'<span class="tag" data-wmod-steps="{len(m["steps"])}">{len(m["steps"])}</span></summary>'
            f'<p class="wmod-greet" data-wmod-agent="{E(g["agent"])}"><span aria-hidden="true">{E(g["glyph"])}</span> '
            f'{T("wmod.greeter", "b")}: <a href="trade_craft_hive.html?agent={E(g["agent"])}" lang="en">{E(g["name"])}</a> '
            f'&mdash; <q lang="en" data-wmod-line>{E(g["line"])}</q> <code class="wmod-src">{E(g["line_source"])}</code> '
            f'<button type="button" class="btn" data-wmod-speak="{E(m["id"])}">{T("hive.speak")}</button></p>'
            f'<p class="muted">{T("wmod.hive")}</p>'
            + (f'<h4>{T("wmod.brief")}</h4><ul class="wmod-brief">{brief}</ul>' if brief else '')
            + f'<h4>{T("wmod.steps")}</h4><ol class="wmod-steps">{steps}</ol>'
            f'<h4>{T("wmod.go")}</h4><p class="wmod-go">{go}</p>'
            + (f'<h4>{T("wmod.supp")}</h4><p class="wmod-supp">{supp}</p>' if supp else f'<p class="muted">{T("wmod.nosupp")}</p>')
            + '</details>')
    refused = ''.join(f'<li><code>{E(k)}</code> <span lang="en">{E(v)}</span></li>' for k, v in reg['refused'].items())
    section = (
        f'<section class="box" id="course-modules" aria-labelledby="course-h-modules">'
        f'<h2 id="course-h-modules" data-i18n="wmod.h">{E(EN["wmod.h"])}</h2>{T("wmod.lede", "p", LEDE)}'
        f'<p class="unv">{T("wmod.unv")}</p>'
        f'<p><button type="button" class="btn" data-wmod-mute aria-pressed="false">{T("hive.v.mute")}</button> '
        f'<span class="muted" data-wmod-state aria-live="polite"></span></p>'
        f'<div class="wmod-cards">{cards}</div>'
        f'<details class="wmod-refused"><summary>{T("wmod.refused")}</summary><ul>{refused}</ul></details>'
        f'<p class="muted">modules/registry/modules.json · {E(reg["schema"])} · stamp <code data-wmod-stamp>{E(reg["source_stamp"])}</code></p>'
        f'</section>')
    need(section.count('class="wmod"') == len(reg['modules']), 'a module has no card')
    css = ('<style id="wmod-css">.wmod-cards{display:grid;gap:10px}'
           'details.wmod{border:1px solid var(--tc-line);border-radius:8px;padding:0 12px;background:var(--tc-raised);min-inline-size:0}'
           'details.wmod summary{cursor:pointer;min-block-size:44px;display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:6px 0}'
           '.wmod-src{color:var(--tc-muted);font-size:12px;overflow-wrap:anywhere}.wmod-go a,.wmod-supp a{display:inline-flex;align-items:center;min-block-size:32px}'
           '.wmod-steps li,.wmod-brief li{margin:4px 0}.wmod-refused summary{cursor:pointer;min-block-size:44px;display:flex;align-items:center}</style>')
    js = ('<script type="application/json" id="wmod-voice">' + js_json({'voices': voices, 'lines': lines}) + '</script>'
          '<script id="wmod-kit">' + HIVE_JS + '</script><script id="wmod-js">' + JS + '</script>')
    return {'reg': reg, 'section': section, 'css': css, 'js': js}


# WORLD-PRACTICE: the greeter speaks only from its button's click; the mute switch is the Hive's own (remembered on
# this device); with no on-device English voice nothing is spoken and the state line says so.
JS = r'''(function () {
  'use strict';
  /* WORLD-PRACTICE BEGIN */
  var box = document.getElementById('course-modules'); if (!box || !window.HiveVoice) return;
  var D = JSON.parse(document.getElementById('wmod-voice').textContent);
  var I = JSON.parse(document.getElementById('course-i18n').textContent);
  function L(k) { var loc = Object.prototype.hasOwnProperty.call(I, document.documentElement.lang) ? document.documentElement.lang : 'en'; return I[loc].strings[k]; }
  var stateEl = box.querySelector('[data-wmod-state]'), muteBtn = box.querySelector('[data-wmod-mute]');
  function say(code) { var k = { muted: 'hive.v.muted', nosynth: 'hive.v.nosynth', novoice: 'hive.v.novoice', refused: 'hive.v.refused', speaking: 'hive.v.speaking', done: 'hive.v.done', stopped: 'hive.v.stopped' }[code]; stateEl.textContent = k ? L(k) : ''; }
  var muted = HiveVoice.init(D.voices, { onstate: say });
  muteBtn.setAttribute('aria-pressed', muted ? 'true' : 'false');
  muteBtn.addEventListener('click', function () { var on = HiveVoice.setMuted(!HiveVoice.muted()); muteBtn.setAttribute('aria-pressed', on ? 'true' : 'false'); say(on ? 'muted' : ''); });
  box.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('[data-wmod-speak]'); if (!b) return;
    var pair = D.lines[b.getAttribute('data-wmod-speak')]; if (!pair) return;
    var agent = D.voices.agents.filter(function (a) { return a.id === pair[0]; })[0]; if (!agent) return;
    HiveVoice.speak([[agent, pair[1]]]);
  });
  var want = (location.hash || '').slice(1);
  if (/^module-/.test(want)) { var el = document.getElementById(want); if (el && el.tagName === 'DETAILS') { el.open = true; el.scrollIntoView(); } }
  /* WORLD-PRACTICE END */
})();'''


def inject(page, wm):
    need(page.count(ANCHOR) == 1, 'the rules box moved; the world modules section has no anchor')
    need(page.count(SCRIPT_ANCHOR) == 1, 'the page script moved; the world modules script has no anchor')
    need(page.count('</head>') == 1, 'no </head>')
    page = page.replace(ANCHOR, wm['section'] + '\n' + ANCHOR)
    page = page.replace('</head>', wm['css'] + '\n</head>')
    # after the page script, so the catalogue and the [data-i18n] pass are already in place
    i = page.index(SCRIPT_ANCHOR)
    j = page.index('</script>', i) + len('</script>')
    return page[:j] + wm['js'] + page[j:]
