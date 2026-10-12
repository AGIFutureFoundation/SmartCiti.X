#!/usr/bin/env python3
"""The course catalogue page: web/trade_craft_courses.html (wave 16).

Reads courses/registry/courses.json (python3 courses/build.py): the trade courses (one per hall, grouped by district),
the strand courses (one per room), and one supplement per lesson - glossary, key concepts, safety notes quoting the
door placards verbatim, self-check questions answered by registry ids, a worksheet and where to go.

Every chrome word comes from the course.* i18n keys (8 locales, Arabic right-to-left); strand and tier names come
from each locale's own `strands` / `tiers` blocks. Course titles, lesson titles, room labels, tool names, placard
quotes and every other registry string are shown verbatim. Counts are read from the registry, never typed here.
The page saves nothing and sends nothing: no storage, no request; a worksheet is filled in on screen or on paper and
is gone when the tab closes. Nothing here certifies anybody - lessons are unverified general practice.
"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS, STYLE_JS  # noqa: E402
from pagehero import theme  # noqa: E402
from design_kit import STYLE_HEAD_JS  # noqa: E402
import sitenav  # noqa: E402

PAGE = 'web/trade_craft_courses.html'
E = lambda s: html.escape(str(s), quote=True)


class CoursePageError(Exception):
    pass


if PAGE not in sitenav.PAGES:
    raise CoursePageError(f'build_courses: {PAGE} is not declared in web/sitenav.py GROUPS (nav.page.courses)')


def need(c, m):
    if not c:
        raise CoursePageError('build_courses: ' + m)


REG = json.loads((ROOT / 'courses/registry/courses.json').read_text(encoding='utf-8'))
for k in ('source_stamp', 'honesty', 'rules', 'counts', 'districts', 'strands', 'courses', 'supplements',
          'supplement_counts', 'supplement_rules', 'bands', 'tiers'):
    need(k in REG, f'courses.json has no {k!r}; run python3 courses/build.py')
C, SC, COURSES, SUP = REG['counts'], REG['supplement_counts'], REG['courses'], REG['supplements']
LESSON_IDS = list(SUP)

# ---- the catalogue strings, strict: every course.* key of en must be non-empty in all 8 locales ----
I18N = {}
EN_ALL = json.loads((ROOT / 'i18n/locales/en.json').read_text(encoding='utf-8'))
KEYS = sorted(k for k in EN_ALL['strings'] if k.startswith('course.'))
need(len(KEYS) > 50, 'the course.* keys are missing from i18n/locales/en.json')
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.loads(f.read_text(encoding='utf-8'))
    s = c['strings']
    miss = [k for k in KEYS if not isinstance(s.get(k), str) or not s[k].strip()]
    need(not miss, f'locale {f.name} is missing {miss[:5]}')
    I18N[c['locale']] = {'dir': c['dir'], 'strings': {k: s[k] for k in KEYS},
                         'strands': {k: c['strands'][k] for k in c['strands']}, 'tiers': dict(c['tiers'])}
need(len(I18N) == 8, f'expected 8 locales, found {sorted(I18N)}')
EN = I18N['en']['strings']
need(set(EN_ALL['strands']) == {s['strand'] for s in REG['strands']}, 'locale strands differ from the course strands')
# the question and worksheet template keys the registry names must all be catalogue keys
for s in SUP.values():
    for q in s['questions']:
        need(q['stem'] in EN, f'question stem {q["stem"]} is not an i18n key')
    for w in s['worksheet']:
        need(w['fill'] in EN, f'worksheet key {w["fill"]} is not an i18n key')


def T(k, tag='span', attrs=''):
    need(k in EN, f'unknown key {k}')
    return f'<{tag}{attrs} data-i18n="{k}">{E(EN[k])}</{tag}>'


def TS(kind, key):
    """a strand or tier name, translated from the locale's own block"""
    return f'<span data-i18n-{kind}="{E(key)}">{E(EN_ALL[kind + "s"][key])}</span>'


def rel(p):
    need(p.startswith('web/'), f'link {p} is not a page under web/')
    return p[len('web/'):]


TITLE_OF = {lid: s['title'] for lid, s in SUP.items()}


def course_card(c):
    o = c['outline']
    rows = ''.join(
        f'<li data-lesson="{E(r["lesson"])}"><a href="trade_craft_lessons.html#lesson-{E(r["lesson"])}">{E(r["title"])}</a>'
        f' <span class="muted">· {E(r["hall_name"]) + " · " if c["kind"] == "strand" else ""}{E(r["room_label"])} · {TS("tier", r["tier"])} · {r["steps"]} '
        f'{T("course.c.steps")}</span> <a class="sup-link" href="?lesson={E(r["lesson"])}#course-sup" data-sup="{E(r["lesson"])}">{T("course.c.supp")}</a></li>'
        for r in o)
    reason = lambda b: T('course.r.' + b)
    if c['prerequisites_outside']:
        before = '<ul>' + ''.join(
            f'<li><a href="trade_craft_lessons.html#lesson-{E(p["lesson"])}">{E(TITLE_OF[p["lesson"]])}</a> {T("course.c.needs")} '
            f'<a href="?lesson={E(p["needs"])}#course-sup" data-sup="{E(p["needs"])}">{E(TITLE_OF[p["needs"]])}</a> ({reason(p["because"])})</li>'
            for p in c['prerequisites_outside']) + '</ul>'
    else:
        before = f'<p class="muted">{T("course.c.nothing")}</p>'
    inside = ''.join(f'<li>{E(TITLE_OF[p["lesson"]])} {T("course.c.needs")} {E(TITLE_OF[p["needs"]])} ({reason(p["because"])})</li>'
                     for p in c['prerequisites_inside'])
    st = c['seat_time']
    seats = st['seats_bound'] or st['seats_in_lessons']
    if seats:
        hall = c['hall'] if c['kind'] == 'trade' else None
        names = st['seat_names']
        seat_html = ', '.join(
            (f'<a class="seat-link" href="trade_craft_3d.html?hall={E(hall)}&amp;sim={E(sid)}">{E(names[sid])}</a>' if hall else f'<code>{E(names[sid])}</code>')
            for sid in seats)
        seat_html = (f'<p>{seat_html}</p><p class="muted"><b data-seat="runs">{st["sim_runs"]}</b> {T("course.c.runs")} · '
                     f'<b data-seat="points">{st["walkaround_points"]}</b> {T("course.c.points")} · <b data-seat="crew">{st["crew_asks"]}</b> '
                     f'{T("course.c.crew")}. {T("course.c.nominutes")}</p>')
    else:
        seat_html = f'<p class="muted">{T("course.c.noseat")}</p>'
    bands = ' '.join(f'<span class="tag" data-band="{E(b)}">{E(b)}</span>' for b in c['bands']) or T('course.c.nobands', 'span', ' class="muted"')
    tiers = ' '.join(f'{TS("tier", t)} {n}' for t, n in c['tiers'].items() if n)
    meta = (f'{E(c["focus"])} · {E(c["campus_name"])}' if c['kind'] == 'trade' else E(c['focus']))
    walk = (f'<p><a href="trade_craft_3d.html?hall={E(c["hall"])}">{T("course.c.walk3d")}</a> · '
            f'<a href="trade_craft_ladder.html?hall={E(c["hall"])}">{T("course.sup.ladder")}</a></p>' if c['kind'] == 'trade' else '')
    title = E(c['title']) if c['kind'] == 'trade' else TS('strand', c['strand']) + f' <span class="muted">· {E(c["title"])}</span>'
    keys = [c['title'], c['hall'], c['district_name']] if c['kind'] == 'trade' else [c['title'], c['strand'], EN_ALL['strands'][c['strand']]]
    search = ' '.join(keys + [r['title'] + ' ' + r['hall_name'] for r in o]).lower()
    return (f'<details class="course" data-course="{E(c["id"])}" data-kind="{E(c["kind"])}" data-bands="{E(" ".join(c["bands"]))}" data-text="{E(search)}">'
            f'<summary><span class="ct">{title}</span> <span class="tag"><b data-count="lessons">{c["counts"]["lessons"]}</b> {T("course.c.lessons")}</span>'
            f' <span class="tag"><b data-count="steps">{c["counts"]["steps"]}</b> {T("course.c.steps")}</span></summary>'
            f'<p class="muted">{meta}</p>'
            f'<dl class="kv"><div><dt>{T("course.c.tiers")}</dt><dd>{tiers}</dd></div><div><dt>{T("course.c.bands")}</dt><dd>{bands}</dd></div></dl>'
            f'<h4>{T("course.c.inside")}</h4><ol class="outline">{rows}</ol>'
            + (f'<ul class="muted">{inside}</ul>' if inside else '')
            + f'<h4>{T("course.c.before")}</h4>{before}<h4>{T("course.c.seattime")}</h4>{seat_html}{walk}</details>')


trade_html = ''
for d in REG['districts']:
    cards = ''.join(course_card(COURSES[cid]) for cid in d['courses'])
    trade_html += (f'<section class="district" data-district="{E(d["district"])}"><h3>{E(d["name"])} '
                   f'<span class="muted">· {E(d["tagline"])}</span></h3><div class="cards">{cards}</div></section>')
strand_html = '<div class="cards">' + ''.join(course_card(COURSES['strand.' + s['strand']]) for s in REG['strands']) + '</div>'
need(trade_html.count('class="course"') == C['trade_courses'] and strand_html.count('class="course"') == C['strand_courses'],
     'a course has no card')

stats = ''.join(f'<div class="st"><dt>{T(k)}</dt><dd data-course-count="{c}">{v}</dd></div>' for k, c, v in (
    ('course.s.courses', 'courses', C['courses']), ('course.s.trade', 'trade_courses', C['trade_courses']),
    ('course.s.strand', 'strand_courses', C['strand_courses']), ('course.s.lessons', 'lessons', C['lessons']),
    ('course.s.steps', 'steps', C['steps']), ('course.s.questions', 'questions', SC['questions']),
    ('course.s.terms', 'glossary_terms', SC['glossary_terms'])))
honest = (''.join(f'<li>{T(k)}</li>' for k in ('course.hon.cert', 'course.hon.gate', 'course.hon.bands', 'course.hon.time'))
          + ''.join(f'<li data-honesty="{E(k)}" lang="en">{E(v)}</li>' for k, v in REG['honesty'].items()))
band_opts = ''.join(f'<option value="{E(b["band"])}">{E(b["band"])}</option>' for b in REG['bands'])
lesson_opts = ''.join(f'<option value="{E(lid)}">{E(s["hall_name"])} · {E(s["title"])}</option>' for lid, s in SUP.items())


def rule_rows(d, prefix=''):
    out = ''
    for k, v in d.items():
        if isinstance(v, dict):
            out += rule_rows(v, prefix + k + ' · ')
        else:
            out += f'<li><code>{E(prefix + k)}</code> {E(", ".join(v) if isinstance(v, list) else v)}</li>'
    return out


rules = f'<ul lang="en">{rule_rows(REG["rules"])}{rule_rows(REG["supplement_rules"], "supplement · ")}</ul>'
links = ''.join(f'<li><a href="{h}">{T(k)}</a></li>' for h, k in (
    ('trade_craft_lessons.html', 'course.l.lessons'), ('trade_craft_ladder.html', 'course.l.ladder'),
    ('trade_craft_3d.html', 'course.l.campus'), ('trade_craft_classroom.html', 'course.l.classroom')))
for h in ('trade_craft_lessons.html', 'trade_craft_ladder.html', 'trade_craft_3d.html', 'trade_craft_classroom.html'):
    need((HERE / h).exists(), f'linked page {h} does not exist')

# the data the supplement viewer renders from: the registry's supplements, whole, plus the stamp
DATA = {'stamp': REG['source_stamp'], 'supplements': SUP}


def js_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


# ---- SUP_RENDER: a pure function (no DOM) from one supplement and one locale's strings to HTML. web/test_courses.mjs
# extracts it between its markers and runs it for every lesson in every locale.
SUP_RENDER = r'''/* SUP_RENDER:BEGIN */
function supEsc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function supFmt(t, args) { return String(t).replace(/\{(\w+)\}/g, function (m, k) { if (!Object.prototype.hasOwnProperty.call(args, k)) throw new Error('sup: no value for {' + k + '}'); return supEsc(args[k]); }); }
function supRel(p) { if (p.indexOf('web/') !== 0) throw new Error('sup: link ' + p + ' is not under web/'); return supEsc(p.slice(4)); }
function supHTML(s, L) {
  var S = L.strings, t = function (k) { if (typeof S[k] !== 'string') throw new Error('sup: no string ' + k); return S[k]; };
  var h = '';
  h += '<h3 id="sup-title" data-sup-lesson="' + supEsc(s.lesson) + '">' + supEsc(s.title) + '</h3>';
  h += '<p class="muted">' + supEsc(s.hall_name) + ' · ' + supEsc(s.room_label) + ' · ' + supEsc(L.strands[s.strand]) + ' · ' + supEsc(L.tiers[s.tier]) + '</p>';
  h += '<p class="sup-links"><a href="' + supRel(s.where.links.lesson) + '">' + supEsc(t('course.c.lesson')) + '</a> · <a href="' + supRel(s.where.links.hall3d) + '">'
    + supEsc(t('course.c.walk3d')) + '</a> · <a href="' + supRel(s.where.links.ladder) + '">' + supEsc(t('course.sup.ladder')) + '</a></p>';
  // safety first: the limits and the placards are met before anything else
  h += '<section class="sup-sec" data-sec="safety"><h4>' + supEsc(t('course.sup.safety')) + '</h4><p class="unv">' + supEsc(t('course.sup.unverified')) + '</p>';
  h += '<p class="limits"><b>' + supEsc(t('course.sup.limits')) + ':</b> <span lang="en">' + supEsc(s.safety.limits) + '</span></p>';
  s.safety.placards.forEach(function (p) {
    h += '<figure class="placard" data-placard="' + supEsc(p.strand) + '" data-hung="' + (p.placard_hung ? '1' : '0') + '"><figcaption>'
      + supFmt(t(p.placard_hung ? 'course.sup.placard' : 'course.sup.record'), { room: p.room_label }) + '</figcaption>'
      + '<blockquote lang="en" data-quote>' + supEsc(p.quote) + '</blockquote>'
      + (p.hazards.length ? '<p class="muted">' + supEsc(t('course.sup.hazards')) + ': <span lang="en">' + p.hazards.map(supEsc).join(', ') + '</span></p>' : '')
      + (p.read_in_lesson ? '<p class="muted">' + supEsc(t('course.sup.readhere')) + '</p>' : '') + '</figure>';
  });
  if (s.safety.lines.length) {
    h += '<ul class="sl">' + s.safety.lines.map(function (x) { return '<li data-sl="' + supEsc(x.kind) + '"><b>' + supEsc(t('course.sl.' + x.kind)) + ' · ' + supEsc(x.label) + ':</b> <span lang="en">' + supEsc(x.text) + '</span></li>'; }).join('') + '</ul>';
  }
  h += '<p class="muted" lang="en">' + supEsc(s.safety.not_certification) + '</p></section>';
  h += '<section class="sup-sec" data-sec="glossary"><h4>' + supEsc(t('course.sup.glossary')) + '</h4><dl class="gloss">' + s.glossary.map(function (g) {
    return '<div data-term="' + supEsc(g.kind) + '"><dt><span lang="en">' + supEsc(g.term) + '</span> <span class="tag">' + supEsc(t('course.g.' + g.kind)) + '</span></dt><dd>'
      + (g.meaning === null ? supFmt(t('course.sup.listed'), { room: g.listed_in }) : '<span lang="en">' + supEsc(g.meaning) + '</span>') + '</dd></div>';
  }).join('') + '</dl></section>';
  h += '<section class="sup-sec" data-sec="concepts"><h4>' + supEsc(t('course.sup.concepts')) + '</h4><ul class="concepts">' + s.concepts.map(function (c) {
    return '<li><span lang="en">' + supEsc(c.text) + '</span> <small class="muted"><code>' + supEsc(c.source) + '</code></small></li>'; }).join('') + '</ul></section>';
  h += '<section class="sup-sec" data-sec="questions"><h4>' + supEsc(t('course.sup.questions')) + '</h4><form class="quiz" data-quiz="' + supEsc(s.lesson) + '" onsubmit="return false">';
  s.questions.forEach(function (q, i) {
    h += '<fieldset data-q="' + supEsc(q.id) + '"><legend>' + (i + 1) + '. ' + supFmt(t(q.stem), q.args) + '</legend>' + q.options.map(function (o) {
      return '<label class="opt"><input type="radio" name="' + supEsc(q.id) + '" value="' + supEsc(o.id) + '"> <span lang="en">' + supEsc(o.label) + '</span></label>'; }).join('')
      + '<p class="verdict" hidden><b>' + supEsc(t('course.sup.answer')) + ':</b> <code>' + supEsc(q.answer.id) + '</code> <small class="muted"><code>' + supEsc(q.answer.ref) + '</code></small></p></fieldset>';
  });
  h += '<p><button type="button" class="btn" data-check>' + supEsc(t('course.sup.check')) + '</button> <span class="score" aria-live="polite"></span></p></form></section>';
  h += '<section class="sup-sec ws" data-sec="worksheet"><h4>' + supEsc(t('course.sup.worksheet')) + '</h4><p class="muted">' + supEsc(t('course.sup.wsnote')) + '</p>'
    + '<p class="ws-head"><label>' + supEsc(t('course.sup.wsname')) + ' <input type="text" maxlength="60"></label> <label>' + supEsc(t('course.sup.wsdate')) + ' <input type="text" maxlength="20"></label></p><ol class="ws-lines">';
  s.worksheet.forEach(function (w) {
    h += '<li data-ws="' + w.n + '"><p lang="en">' + supEsc(w.do) + '</p><label>' + supFmt(t(w.fill), w.args) + '<textarea rows="2"></textarea></label></li>';
  });
  h += '</ol></section>';
  var W = s.where;
  h += '<section class="sup-sec" data-sec="where"><h4>' + supEsc(t('course.sup.where')) + '</h4><dl class="kv">';
  h += '<div><dt>' + supEsc(t('course.sup.places')) + '</dt><dd>' + W.places.map(function (p) { return '<span lang="en">' + supEsc(p.label) + '</span>'; }).join(', ') + '</dd></div>';
  h += '<div><dt>' + supEsc(t('course.sup.crib')) + '</dt><dd lang="en">' + supEsc(W.crib.name) + '</dd></div>';
  if (W.advisors.length) h += '<div><dt>' + supEsc(t('course.sup.advisors')) + '</dt><dd>' + W.advisors.map(function (a) { return '<span lang="en">' + supEsc(a.name) + '</span> (' + supFmt(t('course.sup.at'), { place: a.at }) + ')'; }).join(', ') + '</dd></div>';
  if (W.seats.length) h += '<div><dt>' + supEsc(t('course.sup.seats')) + '</dt><dd>' + W.seats.map(function (x) { return '<a href="' + supRel(x.href) + '" lang="en">' + supEsc(x.name) + '</a>'; }).join(', ') + '</dd></div>';
  if (W.crews.length) h += '<div><dt>' + supEsc(t('course.sup.crews')) + '</dt><dd lang="en">' + W.crews.map(function (x) { return supEsc(x.name); }).join(', ') + '</dd></div>';
  if (W.stations.length) h += '<div><dt>' + supEsc(t('course.sup.stations')) + '</dt><dd lang="en">' + W.stations.map(function (x) { return supEsc(x.name) + ' · ' + supEsc(x.room); }).join(', ') + '</dd></div>';
  h += '</dl></section>';
  return h;
}
/* SUP_RENDER:END */'''

PAGE_JS = r'''(function () {
  'use strict';
  var I = JSON.parse(document.getElementById('course-i18n').textContent);
  var D = JSON.parse(document.getElementById('course-data').textContent);
  var q = new URLSearchParams(location.search), loc = 'en', want = q.get('lang');
  if (want && Object.prototype.hasOwnProperty.call(I, want)) loc = want;
  else {
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < prefs.length; i++) { var c = String(prefs[i]).slice(0, 2).toLowerCase(); if (Object.prototype.hasOwnProperty.call(I, c)) { loc = c; break; } }
  }
  var L = I[loc], S = L.strings;
  document.documentElement.lang = loc; document.documentElement.dir = L.dir;
  document.querySelectorAll('[data-i18n]').forEach(function (el) {
    var s = S[el.getAttribute('data-i18n')];
    if (typeof s !== 'string') throw new Error('course i18n: ' + loc + ' has no ' + el.getAttribute('data-i18n'));
    el.textContent = s;
  });
  document.querySelectorAll('[data-i18n-strand]').forEach(function (el) { el.textContent = L.strands[el.getAttribute('data-i18n-strand')]; });
  document.querySelectorAll('[data-i18n-tier]').forEach(function (el) { el.textContent = L.tiers[el.getAttribute('data-i18n-tier')]; });
  document.getElementById('course-search').placeholder = S['course.f.search'];
  /* the filter: text and band; nothing is stored */
  var cards = [].slice.call(document.querySelectorAll('details.course'));
  function filter() {
    var text = document.getElementById('course-search').value.trim().toLowerCase(), band = document.getElementById('course-band').value, n = 0;
    cards.forEach(function (c) {
      var hit = (!text || c.getAttribute('data-text').indexOf(text) >= 0) && (!band || (' ' + c.getAttribute('data-bands') + ' ').indexOf(' ' + band + ' ') >= 0);
      c.hidden = !hit; if (hit) n++;
    });
    document.querySelectorAll('section.district').forEach(function (d) { d.hidden = !d.querySelector('details.course:not([hidden])'); });
    document.getElementById('course-shown').textContent = S['course.f.shown'].replace('{n}', String(n));
    document.getElementById('course-empty').hidden = n > 0;
    return n;
  }
  document.getElementById('course-search').addEventListener('input', filter);
  document.getElementById('course-band').addEventListener('change', filter);
  /* the supplement viewer */
  var view = document.getElementById('sup-view'), pick = document.getElementById('sup-pick'), cur = null;
  function open(id, scroll) {
    var s = D.supplements[id];
    if (!s) { view.innerHTML = ''; document.getElementById('sup-none').hidden = false; cur = null; return false; }
    view.innerHTML = supHTML(s, L); document.getElementById('sup-none').hidden = true; pick.value = id; cur = id;
    var u = new URL(location.href); u.searchParams.set('lesson', id); history.replaceState(null, '', u.pathname + u.search + '#course-sup');
    if (scroll) document.getElementById('course-sup').scrollIntoView();
    return true;
  }
  pick.addEventListener('change', function () { open(pick.value, false); });
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('a[data-sup]');
    if (a) { ev.preventDefault(); open(a.getAttribute('data-sup'), true); return; }
    var b = ev.target.closest && ev.target.closest('[data-check]');
    if (b && cur) {
      var s = D.supplements[cur], right = 0;
      s.questions.forEach(function (qq) {
        var fs = view.querySelector('fieldset[data-q="' + CSS.escape(qq.id) + '"]'), got = fs.querySelector('input:checked');
        var good = !!got && got.value === qq.answer.id; if (good) right++;
        fs.setAttribute('data-result', good ? 'right' : 'wrong'); fs.querySelector('.verdict').hidden = false;
      });
      view.querySelector('.score').textContent = S['course.sup.score'].replace('{n}', String(right)).replace('{total}', String(s.questions.length));
    }
  });
  var first = q.get('lesson');
  if (first) open(first, true);
  window.__coursePage = { locale: loc, dir: L.dir, courses: cards.length, lessons: Object.keys(D.supplements).length, filter: filter, open: open, current: function () { return cur; } };
  filter();
})();'''

tcss, tjs = theme('doc')
NAV = nav_html(PAGE, nav_labels('en'))
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' "
        "fill='%230C1113'/%3E%3Cpath d='M8 8 h10 l6 6 v10 h-16 z' fill='none' stroke='%23E8A33D' stroke-width='2.2' stroke-linejoin='round'/%3E"
        "%3Cpath d='M12 16 h8 M12 20 h6' stroke='%2341C4D4' stroke-width='2.2' stroke-linecap='round'/%3E%3C/svg%3E")

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{ICON}">
<title>Courses</title>
<script id="style-head-js">{STYLE_HEAD_JS}</script>
<style>{NAV_CSS}</style>
<style id="tc-css">{tcss}</style>
<style>
body{{font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px 16px 120px}}
.lede{{color:var(--tc-muted);max-width:72ch}}
main,section,li,p,summary,dd,dt,legend,label,blockquote{{overflow-wrap:anywhere}}
.box{{border:1px solid var(--tc-line);border-radius:10px;padding:16px;margin:0 0 20px;background:var(--tc-panel);color:var(--tc-ink);min-inline-size:0}}
.box h2{{margin:0 0 10px;font-size:22px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:0 0 12px}}
.st{{display:flex;flex-direction:column-reverse}}
.st dt{{color:var(--tc-muted);font-size:13px}}
.st dd{{margin:0;font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}}
.honesty{{color:var(--tc-muted);padding-inline-start:20px}}
.honesty li{{margin:4px 0}}
.muted{{color:var(--tc-muted);font-size:14px}}
.tag{{font:600 12px/1.3 ui-monospace,monospace;border:1px solid var(--tc-line);border-radius:4px;padding:2px 6px;color:var(--tc-muted);display:inline-block}}
code{{font:12.5px ui-monospace,monospace}}
a{{color:var(--tc-link)}}
.district h3{{font-size:18px;margin:16px 0 8px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px;align-items:start}}
details.course{{border:1px solid var(--tc-line);border-radius:8px;padding:0 12px;background:var(--tc-raised);min-inline-size:0}}
details.course[open]{{grid-column:1/-1}}
details.course summary{{cursor:pointer;min-block-size:44px;display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:6px 0}}
.ct{{font-weight:600}}
h4{{margin:10px 0 4px;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--tc-muted)}}
.outline li{{margin:4px 0}}
.sup-link{{display:inline-flex;align-items:center;min-block-size:32px}}
.seat-link{{display:inline-flex;align-items:center;min-block-size:32px}}
.kv{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:6px 16px;margin:6px 0}}
.kv dt{{color:var(--tc-muted);font-size:13px}}.kv dd{{margin:0}}
.find{{display:flex;flex-wrap:wrap;gap:10px;align-items:center}}
.find input,.find select,#sup-pick{{min-block-size:44px;font:inherit;color:var(--tc-ink);background:var(--tc-raised);border:1px solid var(--tc-line);border-radius:8px;padding:0 10px;max-inline-size:100%;min-inline-size:0}}
.find input{{inline-size:min(420px,100%)}}
#sup-pick{{inline-size:100%}}
.sup-sec{{border-block-start:1px solid var(--tc-line);padding-block-start:8px;margin-block-start:12px}}
.unv{{font-weight:600}}
.placard{{margin:8px 0;border:1px solid var(--tc-line);border-inline-start:4px solid var(--tc-amber);border-radius:6px;padding:8px 12px;background:var(--tc-raised)}}
.placard[data-hung="0"]{{border-inline-start-color:var(--tc-line)}}
.placard figcaption{{font-weight:600;font-size:14px}}
.placard blockquote{{margin:4px 0;font:14px/1.5 ui-monospace,monospace}}
.gloss{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px 16px}}
.gloss dt{{font-weight:600}}.gloss dd{{margin:0 0 4px;color:var(--tc-muted);font-size:14px}}
.quiz fieldset{{border:1px solid var(--tc-line);border-radius:8px;margin:0 0 10px;padding:8px 12px;min-inline-size:0}}
.quiz fieldset[data-result="right"]{{border-color:var(--tc-ok)}}
.quiz fieldset[data-result="wrong"]{{border-color:var(--tc-warn)}}
.quiz legend{{font-weight:600;padding:0 4px}}
.opt{{display:flex;align-items:center;gap:8px;min-block-size:44px;cursor:pointer}}
.opt input{{flex:none;inline-size:18px;block-size:18px;accent-color:var(--tc-amber)}}
.btn{{min-block-size:44px;padding:0 14px;border-radius:8px;border:1px solid var(--tc-line);background:var(--tc-raised);color:var(--tc-ink);font:inherit;cursor:pointer}}
.ws-lines li{{margin:0 0 10px}}.ws-lines p{{margin:0}}
.ws textarea,.ws-head input{{display:block;inline-size:100%;font:inherit;color:var(--tc-ink);background:var(--tc-raised);border:1px solid var(--tc-line);border-radius:6px;min-block-size:44px}}
.ws-head{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px}}
.links a{{display:inline-flex;align-items:center;min-block-size:44px}}
@media print{{
  nav.sitenav,.honesty,#course-find,#course-trade,#course-strand,#course-rules,#course-links,header .stats,.sup-pick-row,[data-check],.quiz .verdict{{display:none!important}}
  body,.box{{background:#fff!important;color:#000!important;border:none}}
  .ws textarea,.ws-head input{{border:none;border-block-end:1px solid #000;border-radius:0;background:#fff}}
  .sup-sec{{break-inside:avoid-page}}
}}
</style>
</head>
<body class="tc-theme">
{NAV}
<main class="wrap" id="course-main">
<header>
{T("course.kicker", "p", ' class="tc-kicker"')}
{T("course.title", "h1", ' class="tc-page-title"')}
{T("course.lede", "p", ' class="lede"')}
<dl class="stats">{stats}</dl>
</header>
<ul class="honesty" id="course-honesty">{honest}</ul>
<section class="box" id="course-find" aria-labelledby="course-h-find"><h2 id="course-h-find" data-i18n="course.h.find">{E(EN["course.h.find"])}</h2>
<div class="find"><input type="search" id="course-search" aria-label="{E(EN["course.f.search"])}" placeholder="{E(EN["course.f.search"])}">
<label>{T("course.f.band")} <select id="course-band"><option value="" data-i18n="course.f.any">{E(EN["course.f.any"])}</option>{band_opts}</select></label>
<span class="muted" id="course-shown" aria-live="polite"></span></div>
<p class="muted" id="course-empty" hidden>{T("course.empty")}</p></section>
<section class="box" id="course-trade" aria-labelledby="course-h-trade"><h2 id="course-h-trade" data-i18n="course.h.trade">{E(EN["course.h.trade"])}</h2>{trade_html}</section>
<section class="box" id="course-strand" aria-labelledby="course-h-strand"><h2 id="course-h-strand" data-i18n="course.h.strand">{E(EN["course.h.strand"])}</h2>{strand_html}</section>
<section class="box" id="course-sup" aria-labelledby="course-h-sup"><h2 id="course-h-sup" data-i18n="course.h.sup">{E(EN["course.h.sup"])}</h2>
<p class="sup-pick-row"><label>{T("course.sup.pick")}<br><select id="sup-pick"><option value=""></option>{lesson_opts}</select></label></p>
<p class="muted" id="sup-none">{T("course.sup.none")}</p>
<div id="sup-view" aria-live="polite"></div></section>
<section class="box" id="course-rules" aria-labelledby="course-h-rules"><h2 id="course-h-rules" data-i18n="course.h.rules">{E(EN["course.h.rules"])}</h2>{rules}</section>
<section class="box links" id="course-links" aria-labelledby="course-h-links"><h2 id="course-h-links" data-i18n="course.h.links">{E(EN["course.h.links"])}</h2><ul>{links}</ul></section>
<p class="muted">courses/registry/courses.json · {E(REG["schema"])} · stamp <code data-stamp>{E(REG["source_stamp"])}</code></p>
</main>
<script type="application/json" id="course-data">{js_json(DATA)}</script>
<script type="application/json" id="course-i18n">{js_json(I18N)}</script>
<script id="course-render">{SUP_RENDER}</script>
<script id="course-page">{PAGE_JS}</script>
<script>{tjs}</script>
<script id="style-js">{STYLE_JS}</script>
</body>
</html>
'''
TITLE = 'SmartCiti.X : Trade Craft Academy — ' + EN['course.nav']
page = apply_seo(page, PAGE, TITLE, EN['course.seo.desc'], 'page')
emit(HERE / 'trade_craft_courses.html', page,
     f'{C["courses"]} courses ({C["trade_courses"]} trade, {C["strand_courses"]} strand) | {SC["supplements"]} supplements | '
     f'{SC["questions"]} questions | stamp {REG["source_stamp"]}')
