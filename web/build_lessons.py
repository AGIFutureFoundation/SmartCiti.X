#!/usr/bin/env python3
"""The lessons page: the walkable lessons, opened so a learner can work them.

WHY THIS FILE EXISTS. `lessons/registry/lessons.json` holds a set of short
walks through the halls - each one a room to stand in, a handful of steps in
a chosen order, and what each step records. `rnd/registry/rnd.json` listed it
as declared-and-unbuilt for one computed reason: "no page generator under
web/ names this path, so nothing a learner opens reads it". The wiki
described the pack; nothing drew it. A lesson nobody can open is not a
lesson, so this generator opens it.

ONE TRUTH PER FACT. Every count, title, step line, room label, hall name,
prerequisite reason and honesty sentence on this page is READ from the
registry that owns it at build time. Nothing is retyped: there is no typed
lesson count, no typed step count and no typed lesson title anywhere below.
A missing field fails the build by name through `need()` rather than
defaulting - a default is a policy decision, and this file is not entitled
to make one on a registry's behalf.

WHAT IT DRAWS. The pack's own limits first, where a learner meets them
before the capability; the eight step kinds with what each one records and,
where it records nothing, the registry's own reason for that; the ladder as
advice with its enforcement sentence quoted; then every lesson, in the
registry's order, with its hall (linked through to that hall in the 3D
environment), its room, its `why`, its `limits`, its prerequisites as named
links, and every one of its steps numbered in the order the registry gives,
each with its instruction line, its note, the names it read and from where,
and whether it writes an episode or nothing at all.

WHAT IT REFUSES TO DO. It does not lock a lesson behind its prerequisites -
the registry says the ladder is advice and the page contract forbids a page
from turning it into a gate. It records nothing: the step marks are a tally
in the open tab, are never stored, never leave the browser and reach no
training log, because opening or abandoning a lesson is nobody's episode.
And it never calls anything here AI-SYNTHESIZED: this pack is AUTHORED, and
that other word belongs to `orbis/` and describes generated video.
"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'lessons').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()

# The registry this page exists to open. Named here by its repo-relative
# path on purpose: rnd/build.py scans the generators under web/ for exactly
# this string, and a page that reads a registry without naming it would
# close the gap in the scan while leaving it open in the bundle.
LESSONS_PATH = 'lessons/registry/lessons.json'


def need(d, k, where):
    """Read a required field, or fail by name.

    No `.get(k, default)` anywhere in this file: a default substituted for a
    missing field is this generator deciding, silently, what a registry
    meant. If the field is gone the page is wrong, and the build says which
    field and where rather than rendering a plausible blank.
    """
    if not isinstance(d, dict):
        raise TypeError(f'{where}: expected an object to read {k!r} from, got {type(d).__name__}')
    if k not in d:
        raise KeyError(f'{where}: required field {k!r} is missing')
    return d[k]


def item(seq, i, where):
    if not isinstance(seq, (list, tuple)):
        raise TypeError(f'{where}: expected a list, got {type(seq).__name__}')
    if i >= len(seq):
        raise IndexError(f'{where}: index {i} is past the end ({len(seq)} items)')
    return seq[i]


reg = json.load(open(ROOT / LESSONS_PATH))
manifest = json.load(open(ROOT / 'pack/manifest.json'))
halls_reg = json.load(open(ROOT / 'pack/registry/halls.json'))
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))

R = LESSONS_PATH
PACK_VERSION = need(reg, 'pack_version', R)
if PACK_VERSION != need(manifest, 'pack_version', 'pack/manifest.json'):
    raise AssertionError(
        f'{R}: pack_version {PACK_VERSION} disagrees with the manifest '
        f'{manifest["pack_version"]}; rebuild lessons/build.py')

PRODUCT = need(reg, 'product', R)
BUILT = need(reg, 'built', R)
HON = need(reg, 'honesty', R)
COUNTS = need(reg, 'counts', R)
SPREAD = need(reg, 'spread', R)
KINDS = need(reg, 'step_kinds', R)
OFF_ROOM = need(reg, 'off_room_places', R)
PLUGS = need(reg, 'plugs_into', R)
LADDER = need(reg, 'ladder', R)
CONTRACT = need(reg, 'page_contract', R)
READS = need(reg, 'reads', R)
LESSONS = need(reg, 'lessons', R)

# The hall's own name and the campus's own name, read from the registries
# that own them rather than trusted from the lesson record - and required to
# agree, because two copies of one name is the defect this bundle lints for.
HALL_NAME = {need(h, 'slug', 'pack/registry/halls.json#halls[]'):
             need(h, 'name', 'pack/registry/halls.json#halls[]')
             for h in need(halls_reg, 'halls', 'pack/registry/halls.json')}
CAMPUS_NAME = {k: need(c, 'name', f'unions/registry/campuses.json#campuses.{k}')
               for k, c in need(campuses_reg, 'campuses',
                                'unions/registry/campuses.json').items()}

# The provenance tiers this bundle uses, closed. AI-SYNTHESIZED is
# deliberately not in it: it belongs to orbis/ and describes generated
# video, and a hand-written walk through a building is not that.
#
# `names` is not a tier and is not rendered as one: the registry records it
# as READ, meaning the display names in every step were fetched from the
# registries that own them rather than written here. It gets its own slot
# and its own word, so the tier slot holds tiers and only tiers.
TIERS = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED')
NAMES_SOURCE = 'READ'

E = html.escape
F = lambda x: f"{x:,}"


def tier(v, where):
    if v not in TIERS:
        raise ValueError(f'{where}: provenance tier {v!r} is not one of {", ".join(TIERS)}')
    return v


def prov_html(prov, where):
    """The lesson's provenance, each tier in a slot of its own.

    A tier is rendered ONLY here, as the `data-tier` of a `.prov` chip, so
    there is exactly one place on the page where a word claims to be a
    provenance tier and exactly one place a check has to look. The `names`
    entry is not a tier and does not get a tier slot: it is the registry
    saying the display names were read from the packs that own them.
    """
    out = ''
    for k, v in prov.items():
        if k == 'names':
            if v != NAMES_SOURCE:
                raise ValueError(
                    f'{where}.names: expected {NAMES_SOURCE!r}, got {v!r}; the names on a step '
                    'are read from the registries that own them or the step is not one')
            out += (f'<span class="prov names" data-source="{E(v)}">names {E(v)} from the '
                    f'registries that own them</span>')
        else:
            out += (f'<span class="prov" data-tier="{E(tier(v, f"{where}.{k}"))}">'
                    f'{E(k)} {E(tier(v, f"{where}.{k}"))}</span>')
    return out


# The pack's own first clause, used as the short warning chip so the chip is
# the registry's words and not a paraphrase of them.
SIGNOFF_SENTENCE = need(HON, 'content', f'{R}#honesty')
SIGNOFF_CHIP = SIGNOFF_SENTENCE.split('.')[0].strip()

for lid, L in LESSONS.items():
    w = f'{R}#lessons.{lid}'
    if need(L, 'id', w) != lid:
        raise AssertionError(f'{w}: the record is keyed {lid!r} but calls itself {L["id"]!r}')
    hall = need(L, 'hall', w)
    if hall not in HALL_NAME:
        raise KeyError(f'{w}: hall {hall!r} is in no hall record of pack/registry/halls.json')
    if need(L, 'hall_name', w) != HALL_NAME[hall]:
        raise AssertionError(
            f'{w}: hall_name {L["hall_name"]!r} is not the halls registry\'s '
            f'own {HALL_NAME[hall]!r}')
    campus = need(L, 'campus', w)
    if campus not in CAMPUS_NAME:
        raise KeyError(f'{w}: campus {campus!r} is in no campus record')
    for s in need(L, 'steps', w):
        n = need(s, 'n', f'{w}.steps')
        k = need(s, 'kind', f'{w}.steps[{n}]')
        if k not in KINDS:
            raise KeyError(f'{w}.steps[{n}]: kind {k!r} is not a declared step kind')

PREREQS = need(LADDER, 'prerequisites', f'{R}#ladder')
for lid in LESSONS:
    if lid not in PREREQS:
        raise KeyError(f'{R}#ladder.prerequisites: lesson {lid!r} has no prerequisite record')

TOTAL_STEPS = sum(len(need(L, 'steps', f'{R}#lessons.{lid}')) for lid, L in LESSONS.items())
if TOTAL_STEPS != need(COUNTS, 'steps', f'{R}#counts'):
    raise AssertionError(
        f'{R}: counts.steps says {COUNTS["steps"]} but the lessons hold {TOTAL_STEPS}')
if len(LESSONS) != need(COUNTS, 'lessons', f'{R}#counts'):
    raise AssertionError(
        f'{R}: counts.lessons says {COUNTS["lessons"]} but the registry holds {len(LESSONS)}')


# ------------------------------------------------------------- fragments ---

def figure(value, label):
    return f'<div class="fig"><b>{E(value)}</b><span>{E(label)}</span></div>'


FIGS = ''.join(figure(v, l) for v, l in [
    (F(need(COUNTS, 'lessons', f'{R}#counts')), 'walkable lessons'),
    (F(need(COUNTS, 'steps', f'{R}#counts')), 'steps to work through'),
    (F(need(COUNTS, 'step_kinds', f'{R}#counts')), 'kinds of step'),
    (f"{need(COUNTS, 'halls_covered', f'{R}#counts')} / "
     f"{need(COUNTS, 'halls_total', f'{R}#counts')}", 'halls stood in'),
    (f"{need(COUNTS, 'strands_covered', f'{R}#counts')} / "
     f"{need(COUNTS, 'strands_total', f'{R}#counts')}", 'strands covered'),
    (F(need(COUNTS, 'rooms_stood_in', f'{R}#counts')), 'rooms stood in'),
    (F(need(COUNTS, 'campuses_covered', f'{R}#counts')), 'campuses'),
    (f"{need(COUNTS, 'recording_steps', f'{R}#counts')} / "
     f"{need(COUNTS, 'silent_steps', f'{R}#counts')}", 'steps that record / that do not'),
    (F(need(COUNTS, 'prerequisite_edges', f'{R}#counts')), 'ladder edges, advisory'),
    # Not a typed zero standing in for a count: the registry has no sign-off
    # field at all, so the honest figure is the word, not a number.
    ('none', 'lessons a practitioner has signed off'),
])

HONESTY_KEYS = ('status', 'content', 'not_certification', 'not_a_gate',
                'not_scored', 'one_truth', 'no_jurisdiction', 'scope')
HONESTY = ''.join(f'<li><b>{E(k.replace("_", " "))}</b> {E(need(HON, k, f"{R}#honesty"))}</li>'
                  for k in HONESTY_KEYS)

KIND_ROWS = ''
for k, spec in KINDS.items():
    w = f'{R}#step_kinds.{k}'
    rec = need(spec, 'records', w)
    why = need(spec, 'why_no_episode', w)
    if rec is None:
        if why is None:
            raise AssertionError(f'{w}: records nothing and gives no reason for recording nothing')
        rec_cell = (f'<span class="pill silent">records nothing</span> '
                    f'<span class="why">{E(why)}</span>')
    else:
        if why is not None:
            raise AssertionError(f'{w}: writes a {rec!r} episode and also explains writing none')
        rec_cell = (f'<span class="pill records">writes one {E(rec)} episode</span> '
                    f'<span class="why">to the device-local training log training/ already keeps</span>')
    KIND_ROWS += (f'<tr><td class="kn"><span class="kind">{E(k)}</span></td>'
                  f'<td class="ka">{E(need(spec, "act", w))}</td>'
                  f'<td class="ks"><span class="stage">{E(need(spec, "stage", w))}</span></td>'
                  f'<td class="kr">{rec_cell}</td>'
                  f'<td class="kf"><code>{E(need(spec, "reads", w))}</code></td></tr>')

LAYERS = need(LADDER, 'layers', f'{R}#ladder')
REASONS = need(LADDER, 'reasons', f'{R}#ladder')


def lesson_link(lid, where):
    if lid not in LESSONS:
        raise KeyError(f'{where}: names lesson {lid!r}, which this registry does not hold')
    return (f'<a class="llink" href="#lesson-{E(lid)}">'
            f'{E(need(LESSONS[lid], "title", f"{R}#lessons.{lid}"))}</a>')


LAYER_BLOCKS = ''
for depth, ids in sorted(LAYERS.items(), key=lambda kv: int(kv[0])):
    chips = ' '.join(lesson_link(i, f'{R}#ladder.layers.{depth}') for i in ids)
    LAYER_BLOCKS += (f'<div class="layer"><h3>layer {E(str(depth))} '
                     f'<span class="muted">{len(ids)} lessons</span></h3>'
                     f'<p class="chips">{chips}</p></div>')

REASON_ROWS = ''.join(
    f'<tr><td class="rn"><span class="chip">{E(k)}</span></td><td>{E(v)}</td></tr>'
    for k, v in REASONS.items())

OFF_ROOM_ROWS = ''.join(
    f'<tr><td class="rn"><span class="chip">{E(need(v, "short", f"{R}#off_room_places.{k}"))}</span></td>'
    f'<td>{E(need(v, "what", f"{R}#off_room_places.{k}"))}</td></tr>'
    for k, v in OFF_ROOM.items())

CONTRACT_KEYS = ('steps', 'ladder', 'limits', 'records', 'episode')
CONTRACT_ROWS = ''.join(
    f'<li><b>{E(k)}</b> {E(need(CONTRACT, k, f"{R}#page_contract"))}</li>'
    for k in CONTRACT_KEYS)

READS_ROWS = ''.join(f'<li><code>{E(p)}</code></li>' for p in READS)


def step_html(lid, L, s, i):
    w = f'{R}#lessons.{lid}.steps[{i}]'
    n = need(s, 'n', w)
    kind = need(s, 'kind', w)
    spec = KINDS[kind]
    rec = need(s, 'records', w)
    kind_rec = need(spec, 'records', f'{R}#step_kinds.{kind}')
    if rec != kind_rec:
        raise AssertionError(
            f'{w}: step records {rec!r} but its kind {kind!r} records {kind_rec!r}; '
            'a step may not reclassify what it writes')
    if rec is None:
        rec_line = (f'<span class="pill silent">records nothing</span> '
                    f'{E(need(spec, "why_no_episode", f"{R}#step_kinds.{kind}"))}')
    else:
        rec_line = (f'<span class="pill records">writes one {E(rec)} episode</span> '
                    f'to the device-local training log')
    where = need(s, 'where', w)
    if where in OFF_ROOM:
        place = need(OFF_ROOM[where], 'short', f'{R}#off_room_places.{where}')
    else:
        place = need(L, 'room_label', f'{R}#lessons.{lid}')
    names = ''.join(f'<span class="name">{E(x)}</span>'
                    for x in need(s, 'names_read', w))
    return (f'<li class="step" data-step="{E(str(n))}">'
            f'<label class="markbox"><input type="checkbox" class="mark" '
            f'aria-label="mark step {E(str(n))} worked"><span class="sn">{E(str(n))}</span></label>'
            f'<div class="sbody">'
            f'<p class="do">{E(need(s, "do", w))}</p>'
            f'<p class="note">{E(need(s, "note", w))}</p>'
            f'<p class="smeta"><span class="kind">{E(kind)}</span>'
            f'<span class="stage">{E(need(s, "stage", w))}</span>'
            f'<span class="place">{E(place)}</span>{rec_line}</p>'
            f'<p class="sread">names READ from <code>{E(need(s, "reads", w))}</code>: {names}</p>'
            f'</div></li>')


def lesson_html(lid, L):
    w = f'{R}#lessons.{lid}'
    hall = need(L, 'hall', w)
    campus = need(L, 'campus', w)
    prov = need(L, 'provenance', w)
    steps = need(L, 'steps', w)
    prereqs = PREREQS[lid]
    if prereqs:
        pre = ''.join(
            f'<li>{lesson_link(need(p, "needs", f"{R}#ladder.prerequisites.{lid}"), w)} '
            f'<span class="chip">{E(need(p, "because", f"{R}#ladder.prerequisites.{lid}"))}</span> '
            f'<span class="why">{E(need(p, "reason", f"{R}#ladder.prerequisites.{lid}"))}</span></li>'
            for p in prereqs)
        pre_block = (f'<div class="pre"><h4>work these first, if you have not</h4>'
                     f'<ul>{pre}</ul>'
                     f'<p class="why">{E(need(LADDER, "enforcement", f"{R}#ladder"))}</p></div>')
    else:
        pre_block = ('<div class="pre"><h4>no prerequisites</h4>'
                     f'<p class="why">{E(need(LADDER, "enforcement", f"{R}#ladder"))}</p></div>')
    prov_chips = prov_html(prov, f'{w}.provenance')
    search = ' '.join([lid, need(L, 'title', w), need(L, 'hall_name', w),
                       need(L, 'strand', w), need(L, 'tier', w),
                       CAMPUS_NAME[campus], need(L, 'room_label', w)])
    return (f'<article class="lesson" id="lesson-{E(lid)}" data-search="{E(search.lower())}">'
            f'<header class="lhead">'
            f'<h3>{E(need(L, "title", w))}</h3>'
            f'<p class="where">'
            f'<a class="hall" href="trade_craft_3d.html?hall={E(hall)}">'
            f'{E(need(L, "hall_name", w))}</a>'
            f'<span class="room">{E(need(L, "room_label", w))}</span>'
            f'<span class="chip">{E(need(L, "strand", w))}</span>'
            f'<span class="chip">{E(need(L, "tier", w))}</span>'
            f'<span class="chip">{E(CAMPUS_NAME[campus])}</span>'
            f'<code>{E(need(L, "skill_id", w))}</code></p>'
            f'<p class="why">{E(need(L, "why", w))}</p>'
            f'<p class="limits"><span class="pill warn">{E(SIGNOFF_CHIP)}</span> '
            f'{E(need(L, "limits", w))}</p>'
            f'<p class="signoff">No practitioner has signed this lesson off: '
            f'{E(SIGNOFF_SENTENCE)}</p>'
            f'</header>'
            f'{pre_block}'
            f'<div class="steps"><h4>{len(steps)} steps, in this order '
            f'<span class="done">not marked</span></h4>'
            f'<ol class="steplist">'
            + ''.join(step_html(lid, L, s, i) for i, s in enumerate(steps))
            + f'</ol></div>'
            f'<footer class="lfoot"><p class="provrow">{prov_chips}</p></footer>'
            f'</article>')


LESSON_BLOCKS = '\n'.join(lesson_html(lid, L) for lid, L in LESSONS.items())
INDEX_CHIPS = ' '.join(lesson_link(lid, f'{R}#lessons') for lid in LESSONS)

SPREAD_NOTE = need(SPREAD, 'note', f'{R}#spread')
LOOP = need(PLUGS, 'loop', f'{R}#plugs_into')
HOW = need(PLUGS, 'how', f'{R}#plugs_into')

ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'"
        "%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 "
        "L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/"
        "%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/"
        "%3E%3C/svg%3E")

SCRIPT = r'''/* Two behaviours, both local to the open tab. The marks are a tally, not a
   record: nothing is written to storage, nothing is sent anywhere, and no
   training episode is produced by opening, marking or abandoning a lesson.
   The filter hides lessons from view; it never removes them from the page,
   and it never disables one whose prerequisites are unmarked, because the
   registry says the ladder is advice and a page that enforced it would be a
   gate wearing a lesson's clothes. */
const listEl = document.getElementById('lessons');
const filterEl = document.getElementById('filter');
const shownEl = document.getElementById('shown');
const lessonEls = Array.prototype.slice.call(listEl.querySelectorAll('article.lesson'));

function tally(article) {
  const boxes = article.querySelectorAll('input.mark');
  let done = 0;
  boxes.forEach(function (b) {
    const li = b.closest('li.step');
    if (b.checked) { done += 1; li.classList.add('marked'); } else { li.classList.remove('marked'); }
  });
  article.querySelector('.done').textContent = done + ' of ' + boxes.length + ' marked';
}

listEl.addEventListener('change', function (ev) {
  const box = ev.target;
  if (!box.classList || !box.classList.contains('mark')) return;
  tally(box.closest('article.lesson'));
});

function applyFilter() {
  const q = filterEl.value.trim().toLowerCase();
  let shown = 0;
  lessonEls.forEach(function (a) {
    const hit = q === '' || a.dataset.search.indexOf(q) !== -1;
    a.hidden = !hit;
    if (hit) shown += 1;
  });
  shownEl.textContent = shown + ' of ' + lessonEls.length + ' lessons shown';
}

filterEl.addEventListener('input', applyFilter);
lessonEls.forEach(tally);
applyFilter();
'''

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartCiti.X : Trade Craft Academy — lessons</title>
<link rel="icon" href="{ICON}">
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4; --warn:#E8A33D;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);
  font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px 48px}}
.wrap{{max-width:940px;margin:0 auto}}
a{{color:var(--steel)}}
header.page{{padding:40px 0 10px;border-bottom:3px solid var(--mark)}}
header.page h1{{font:700 34px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}}
header.page h1 .x{{color:var(--mark)}}
header.page p{{color:var(--muted);margin:6px 0 14px}}
h2{{font:700 22px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:34px 0 10px;
  color:var(--mark);letter-spacing:.02em}}
h3{{font:700 20px/1.25 "Barlow Condensed",system-ui,sans-serif;margin:0 0 6px}}
h4{{font:600 15px/1.3 system-ui,sans-serif;margin:14px 0 6px;color:var(--muted)}}
section{{margin:0 0 10px}}
.lead{{background:var(--panel);border:1px solid var(--rule);border-left:4px solid var(--warn);
  border-radius:8px;padding:14px 18px}}
.lead ul{{margin:8px 0 0;padding-inline-start:20px}}
.lead li{{margin:6px 0;color:var(--muted)}}
.lead li b{{color:var(--ink);text-transform:uppercase;font-size:12px;letter-spacing:.06em;
  margin-inline-end:6px}}
.figs{{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}}
.fig{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;
  padding:10px 14px;min-width:120px}}
.fig b{{display:block;font:600 24px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--mark)}}
.fig span{{color:var(--muted);font-size:13px}}
table{{width:100%;border-collapse:collapse;background:var(--panel);
  border:1px solid var(--rule);border-radius:8px;overflow:hidden}}
td,th{{border-top:1px solid var(--rule);padding:8px 10px;vertical-align:top;font-size:14px}}
tr:first-child td{{border-top:0}}
code{{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}}
.kind,.stage,.chip,.place,.name{{display:inline-block;border-radius:4px;
  padding:1px 7px;font-size:12px;border:1px solid var(--rule);margin-inline-end:6px}}
.kind{{background:var(--sunk);color:var(--mark);font-weight:600}}
.stage{{background:var(--sunk);color:var(--steel)}}
.place{{background:var(--sunk);color:var(--muted)}}
.chip{{background:var(--sunk);color:var(--muted)}}
.name{{background:transparent;color:var(--ink);border-style:dashed;margin:2px 6px 2px 0}}
.pill{{display:inline-block;border-radius:4px;padding:1px 7px;font-size:12px;
  font-weight:600;margin-inline-end:6px}}
.pill.records{{background:rgba(65,196,212,.16);color:var(--steel);border:1px solid var(--rule)}}
.pill.silent{{background:var(--sunk);color:var(--muted);border:1px solid var(--rule)}}
.pill.warn{{background:var(--mark);color:var(--mark-ink)}}
.why,.muted{{color:var(--muted);font-size:13px}}
.layer{{margin:10px 0}}
.layer h3{{font-size:15px;margin:0 0 4px;color:var(--steel)}}
.chips a{{display:inline-block;margin:0 8px 6px 0}}
.toolbar{{position:sticky;top:0;background:var(--plate);padding:10px 0;z-index:2;
  border-bottom:1px solid var(--rule);display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.toolbar input{{flex:1 1 260px;background:var(--sunk);border:1px solid var(--rule);
  color:var(--ink);border-radius:6px;padding:8px 12px;font:inherit}}
.toolbar .shown{{color:var(--muted);font-size:13px}}
.lesson{{background:var(--panel);border:1px solid var(--rule);border-radius:10px;
  padding:16px 18px;margin:14px 0}}
.lesson[hidden]{{display:none}}
.lhead .where{{margin:2px 0 8px;display:flex;flex-wrap:wrap;align-items:center;gap:2px}}
.lhead .hall{{font-weight:600;margin-inline-end:8px}}
.room{{display:inline-block;border-radius:4px;padding:1px 7px;font-size:12px;
  background:var(--sunk);color:var(--ink);border:1px solid var(--rule);margin-inline-end:6px}}
.lhead .why{{margin:0 0 8px;color:var(--ink);font-size:15px}}
.limits{{margin:0;font-size:14px;color:var(--ink)}}
.signoff{{margin:6px 0 0;color:var(--muted);font-size:13px}}
.pre{{border-top:1px solid var(--rule);margin-top:12px;padding-top:6px}}
.pre ul{{margin:0;padding-inline-start:18px}}
.pre li{{margin:4px 0;font-size:14px}}
.steps{{border-top:1px solid var(--rule);margin-top:12px;padding-top:6px}}
.steps h4{{display:flex;justify-content:space-between;align-items:baseline;gap:10px}}
.done{{color:var(--steel);font-weight:600;font-variant-numeric:tabular-nums}}
ol.steplist{{list-style:none;margin:0;padding:0}}
li.step{{display:flex;gap:12px;border-top:1px solid var(--rule);padding:10px 0}}
li.step:first-child{{border-top:0}}
.markbox{{display:flex;flex-direction:column;align-items:center;gap:4px;cursor:pointer;
  min-width:34px}}
.markbox input{{width:18px;height:18px;accent-color:var(--mark)}}
.sn{{font:600 13px/1 ui-monospace,monospace;color:var(--muted)}}
li.step.marked .do{{color:var(--muted);text-decoration:line-through}}
.sbody{{flex:1}}
.do{{margin:0;font-size:15px}}
.note{{margin:4px 0 6px;color:var(--muted);font-size:13.5px;font-style:italic}}
.smeta{{margin:0 0 4px}}
.sread{{margin:0;color:var(--muted);font-size:12.5px}}
.lfoot{{border-top:1px solid var(--rule);margin-top:12px;padding-top:8px}}
.prov{{display:inline-block;border-radius:4px;padding:1px 7px;font-size:11px;
  border:1px solid var(--rule);margin:0 6px 4px 0;background:var(--sunk);color:var(--muted);
  letter-spacing:.04em}}
.prov.names{{border-style:dashed}}
footer.page{{margin-top:34px;border-top:1px solid var(--rule);padding:14px 0;
  color:var(--muted);font-size:14px}}
footer.page a{{margin-inline-end:10px}}
</style>
</head>
<body>
<div class="wrap">

<header class="page">
  <h1>{E(PRODUCT.split("(")[0].strip())} — <span class="x">lessons</span></h1>
  <p>{E(PRODUCT)} · pack {E(PACK_VERSION)} · built {E(BUILT)} · every line below is read from
     <code>{E(LESSONS_PATH)}</code></p>
</header>

<section class="lead" id="limits">
  <h2>Read this before you work one</h2>
  <ul>{HONESTY}</ul>
</section>

<section class="figs">{FIGS}</section>

<section>
  <h2>Where a lesson sits in the loop</h2>
  <p>{E(LOOP)}</p>
  <p class="why">{E(HOW)}</p>
  <p class="why">{E(SPREAD_NOTE)}</p>
</section>

<section>
  <h2>The eight kinds of step, and what each one records</h2>
  <table><tbody>{KIND_ROWS}</tbody></table>
  <h4>steps that happen outside a room</h4>
  <table><tbody>{OFF_ROOM_ROWS}</tbody></table>
</section>

<section>
  <h2>The ladder is advice, not a gate</h2>
  <p class="why">{E(need(LADDER, "enforcement", f"{R}#ladder"))}</p>
  <table><tbody>{REASON_ROWS}</tbody></table>
  {LAYER_BLOCKS}
</section>

<section>
  <h2>What this page promised the registry it would do</h2>
  <ul class="lead">{CONTRACT_ROWS}</ul>
</section>

<section>
  <h2>Every lesson, every step</h2>
  <p class="chips">{INDEX_CHIPS}</p>
</section>

<div class="toolbar">
  <input id="filter" type="search" placeholder="filter by hall, strand, tier, campus or title"
         aria-label="filter the lessons">
  <span class="shown" id="shown"></span>
  <span class="shown">marks live in this tab only: nothing here is stored, sent or recorded</span>
</div>

<main id="lessons">
{LESSON_BLOCKS}
</main>

<section>
  <h2>What this page read</h2>
  <ul class="lead"><li><code>{E(LESSONS_PATH)}</code></li>{READS_ROWS}
  <li><code>pack/registry/halls.json</code></li>
  <li><code>unions/registry/campuses.json</code></li></ul>
</section>

<footer class="page">
  <a href="trade_craft_3d.html">3D environment</a>
  <a href="trade_craft_dashboard.html">network dashboard</a>
  <a href="trade_craft_landing.html">landing</a>
  <a href="../wiki/Home.md">wiki</a>
</footer>
</div>
<script>
{SCRIPT}</script>
</body>
</html>
'''

out = HERE / 'trade_craft_lessons.html'
emit(out, page, f"{len(LESSONS)} lessons, {TOTAL_STEPS} steps, "
                f"{COUNTS['halls_covered']} halls, certifies nobody")
