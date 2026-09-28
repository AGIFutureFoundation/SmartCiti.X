#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the K-12 pathways page.

schools/registry/schools.json declares four grade bands (Explorer, Builder,
Practitioner, Lead), a flipped-classroom loop of four stages, 45 flipped
units and four PROPOSED district partners. Until this page, a teacher could
only meet that pack inside the 3D app's Schools panel, and nothing said
which of the walkable lessons, or which of the quests and treasures, suit
which band. This page answers that and nothing more.

WHAT FITS A BAND IS A RULE, STATED ONCE AND COMPUTED. Nobody picked lessons
for a band by hand. Each band's rule reads only fields the registries
already carry - a lesson's tier, the kinds of its steps and the loop stage
each step belongs to; a unit's stations, crib drill, floor seats and gate;
a quest's optional `band` - and the rule sentence is printed beside the
list it produced:

  K-5  Explorer      the band's own offer is "no machine seats and no station
                     quizzes", so a lesson fits only when every step is a walk,
                     a placard read or an advisor question. No unit fits:
                     every unit carries a floor seat.
  6-8  Builder       fundamentals-tier lessons whose every step is a CLASS
                     step (no floor time); the class half of each unit.
  9-10 Practitioner  applied-tier lessons, floor steps included; every unit
                     with its floor seats.
  11-12 Lead         mastery-tier lessons (the registry holds none, and the
                     page says so rather than borrowing another tier's);
                     every unit with its unaided gate, quoted from the unit.

HONESTY TRAVELS VERBATIM. The district status, the schools honesty lines,
the lessons pack's "unverified general practice" and the quests pack's
"play, never evidence" sentence are printed exactly as their registries
hold them; the build fails if any is missing. No figure here is typed:
every count is the length of a list this file computed.
"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS  # noqa: E402
from seo import apply_seo  # noqa: E402  head tags only

PAGE_PATH = 'web/trade_craft_schools.html'


def req(mapping, key, who):
    """Fail closed: a missing field stops the build and names itself."""
    if key not in mapping:
        raise KeyError(f'{who}: {key!r} is missing')
    return mapping[key]


def load(rel):
    p = ROOT / rel
    if not p.exists():
        raise FileNotFoundError(f'{rel} is not built; the schools page reads it')
    return json.load(open(p))


SCHOOLS = load('schools/registry/schools.json')
LESSONS_REG = load('lessons/registry/lessons.json')
QUESTS_REG = load('quests/registry/quests.json')
WILDS_REG = load('wilds/registry/wilds.json')
MANIFEST = load('pack/manifest.json')
HALLS = req(load('pack/registry/halls.json'), 'halls', 'halls.json')
SIMS = req(load('sims/registry/sims.json'), 'sims', 'sims.json')
STATIONS = {s['station_id']: s for s in req(load('stations/registry/stations.json'), 'stations', 'stations.json')}
CRIBS = req(load('tools/registry/toolcribs.json'), 'cribs', 'toolcribs.json')

HALL_NAME = {h['slug']: h['name'] for h in HALLS}
LESSONS = req(LESSONS_REG, 'lessons', 'lessons.json')
BANDS = req(SCHOOLS, 'bands', 'schools.json')
UNITS = req(SCHOOLS, 'units', 'schools.json')
DISTRICTS = req(SCHOOLS, 'districts', 'schools.json')
S_HONESTY = req(SCHOOLS, 'honesty', 'schools.json')
STAGES = req(req(SCHOOLS, 'model', 'schools.json'), 'stages', 'schools.json#model')
QUESTS = req(QUESTS_REG, 'quests', 'quests.json')
Q_HONESTY = req(QUESTS_REG, 'honesty', 'quests.json')
L_CONTENT = req(req(LESSONS_REG, 'honesty', 'lessons.json'), 'content', 'lessons.json#honesty')

EXPLORE_KINDS = {'walk', 'placard', 'advisor'}
BAND_IDS = ['K-5', '6-8', '9-10', '11-12']
assert [b['band'] for b in BANDS] == BAND_IDS, \
    f'schools/ declares bands {[b["band"] for b in BANDS]}, not the four this page is written for'


def kinds(L):
    return {req(st, 'kind', L['id']) for st in req(L, 'steps', L['id'])}


def stages(L):
    return {req(st, 'stage', L['id']) for st in L['steps']}


# ------------------------------------------------------------ band rules ---
# rule(lesson) -> bool, unit_part(unit) -> what of the unit this band takes
RULES = {
    'K-5': {
        'lesson': lambda L: kinds(L) <= EXPLORE_KINDS,
        'lesson_rule': 'a lesson fits when every step is a walk, a placard read or an advisor question - no seat, no station bench, no scored crib pick',
        'unit_part': None,
        'unit_rule': 'no unit fits: every flipped unit carries a floor seat, and this band sits in none',
    },
    '6-8': {
        'lesson': lambda L: req(L, 'tier', L['id']) == 'fundamentals' and stages(L) == {'class'},
        'lesson_rule': 'a lesson fits when it sits at the fundamentals tier and every step is a class step - no floor time yet',
        'unit_part': 'class',
        'unit_rule': 'the class half of each unit: its stations and its district crib drill, without the floor seat',
    },
    '9-10': {
        'lesson': lambda L: L['tier'] == 'applied',
        'lesson_rule': 'a lesson fits when it sits at the applied tier, floor steps included',
        'unit_part': 'floor',
        'unit_rule': 'each unit through the floor: stations, crib drill and simulator seat time',
    },
    '11-12': {
        'lesson': lambda L: L['tier'] == 'mastery',
        'lesson_rule': 'a lesson fits when it sits at the mastery tier',
        'unit_part': 'gate',
        'unit_rule': 'each whole unit, ending at its unaided gate, which no lesson, station hour or seat hour substitutes for',
    },
}
for b in BANDS:
    assert b['tier'] is None or b['band'] != 'K-5', 'K-5 is declared tierless by schools/'
    if b['tier'] is not None:
        # a tier-bound band's lesson rule tests the tier schools/ declares for it
        probe = {'id': 'probe', 'tier': b['tier'], 'steps': [{'kind': 'walk', 'stage': 'class'}]}
        assert RULES[b['band']]['lesson'](probe), f'{b["band"]}: the lesson rule ignores the declared tier {b["tier"]}'

LESSON_BY_HALL = {}
for lid, L in LESSONS.items():
    LESSON_BY_HALL.setdefault(req(L, 'hall', lid), []).append(lid)

PATHS = {}
for b in BANDS:
    band = b['band']
    rule = RULES[band]
    fit = sorted((lid for lid, L in LESSONS.items() if rule['lesson'](L)),
                 key=lambda lid: (HALL_NAME[LESSONS[lid]['hall']], lid))
    units = [] if rule['unit_part'] is None else list(UNITS)
    quests = [q for q in QUESTS if 'band' in q and q['band'] == band]
    fit_set = set(fit)
    sites = []
    for w in req(WILDS_REG, 'worlds', 'wilds.json'):
        for s in req(w, 'sites', f'wilds {w["id"]}'):
            hit = [x['id'] for x in req(s, 'lessons', s['id']) if x['id'] in fit_set]
            if hit:
                sites.append((w['id'], s, hit))
    PATHS[band] = {'band': b, 'lessons': fit, 'units': units, 'quests': quests, 'sites': sites}

# a quest's band must be one schools/ declares, and every lesson it requires exists
for q in QUESTS:
    if 'band' in q:
        assert q['band'] in BAND_IDS, f'quest {q["id"]} names band {q["band"]}, which schools/ does not declare'
    for lid in req(req(q, 'requires', q['id']), 'lessons', q['id']):
        assert lid in LESSONS, f'quest {q["id"]} requires lesson {lid}, which lessons/ does not hold'

# K-5 never reaches a seat: re-proved from the steps, not from the rule text
for lid in PATHS['K-5']['lessons']:
    assert not kinds(LESSONS[lid]) & {'sim', 'walkaround', 'crew', 'station', 'crib'}, \
        f'K-5 lists {lid}, which puts a learner at a seat, a bench or a scored drill'

E = lambda s: html.escape(str(s), quote=True)


def lesson_li(lid):
    L = LESSONS[lid]
    tag = 'composed' if req(L, 'authoring', lid) == 'rule' else 'hand-written'
    return (f'<li><a href="trade_craft_lessons.html#lesson-{E(lid)}">{E(L["title"])}</a>'
            f' <span class="meta">{E(L["hall_name"])} · {E(L["room_label"])} · {E(L["tier"])} · '
            f'{len(L["steps"])} steps · <span class="auth">{tag}</span></span></li>')


def unit_row(u, part):
    hall = req(u, 'hall', 'unit')
    stations = [req(STATIONS, sid, hall)['name'] for sid in req(u, 'class_stations', hall)]
    crib = req(req(CRIBS, req(u, 'class_drill', hall), hall), 'name', hall)
    here = LESSON_BY_HALL[hall] if hall in LESSON_BY_HALL else []
    cells = [f'<td><a href="trade_craft_lessons.html#course-{E(hall)}">{E(HALL_NAME[hall])}</a></td>',
             f'<td>{E(", ".join(stations)) if stations else "<span class=meta>no station</span>"}</td>',
             f'<td>{E(crib)}</td>']
    if part in ('floor', 'gate'):
        cells.append(f'<td>{E(", ".join(req(SIMS, s, hall)["name"] for s in req(u, "floor_sims", hall)))}</td>')
    if part == 'gate':
        cells.append(f'<td>{E(req(u, "gate", hall))}</td>')
    cells.append(f'<td class="num">{len(here)}</td>')
    return '<tr>' + ''.join(cells) + '</tr>'


def unit_table(units, part):
    if part is None:
        return ''
    head = ['Hall', 'Class stations', 'Crib drill']
    if part in ('floor', 'gate'):
        head.append('Floor seats')
    if part == 'gate':
        head.append('Gate')
    head.append('Lessons in hall')
    th = ''.join(f'<th>{h}</th>' for h in head)
    rows = ''.join(unit_row(u, part) for u in units)
    return f'<div class="tscroll"><table><thead><tr>{th}</tr></thead><tbody>{rows}</tbody></table></div>'


def quest_li(q):
    return (f'<li><span class="qk">{E(req(q, "kind", q["id"]))}</span> <b>{E(req(q, "title", q["id"]))}</b>'
            f' <span class="meta">{E(req(q, "world", q["id"]))}</span>'
            f'<br><span class="hint">{E(req(q, "hint", q["id"]))}</span></li>')


def band_section(band):
    P = PATHS[band]
    b = P['band']
    rule = RULES[band]
    nL, nU, nQ, nS = len(P['lessons']), len(P['units']), len(P['quests']), len(P['sites'])
    lessons = (f'<ul class="lessons">{"".join(lesson_li(l) for l in P["lessons"])}</ul>' if nL else
               f'<p class="empty" data-empty="lessons">No lesson in lessons/registry/lessons.json sits at the '
               f'{E(b["tier"])} tier today, so this band lists none rather than borrowing another tier\'s.</p>')
    quests = (f'<ul class="quests">{"".join(quest_li(q) for q in P["quests"])}</ul>' if nQ else
              '<p class="empty" data-empty="quests">No quest in quests/registry/quests.json names this band yet.</p>')
    sites = ('<ul class="sites">' + ''.join(
        f'<li><b>{E(s["id"])}</b> <span class="meta">wilds: {E(w)} · {E(req(s, "kind", s["id"]))} · '
        f'{len(hit)} fitting lesson{"s" if len(hit) != 1 else ""}</span></li>' for w, s, hit in P['sites'])
        + '</ul>') if nS else '<p class="empty" data-empty="sites">No wilds site names a lesson that fits this band.</p>'
    return f'''<section class="band" id="band-{E(band)}" data-band="{E(band)}">
<h2><span class="bn">{E(band)}</span> {E(b["level"])} <span class="tier">{E(b["tier"]) if b["tier"] else "no tier - explore only"}</span></h2>
<p class="offer">{E(b["offer"])}</p>
<div class="figs"><div class="fig"><b data-fig="lessons">{nL}</b><span>lessons fit</span></div>
<div class="fig"><b data-fig="units">{nU}</b><span>flipped units</span></div>
<div class="fig"><b data-fig="quests">{nQ}</b><span>quests &amp; treasures</span></div>
<div class="fig"><b data-fig="sites">{nS}</b><span>wilds sites</span></div></div>
<h3>Flipped units</h3>
<p class="rule" data-rule="units">{E(rule["unit_rule"])}.</p>
{unit_table(P["units"], rule["unit_part"])}
<h3>Lessons that fit</h3>
<p class="rule" data-rule="lessons">{E(rule["lesson_rule"])}.</p>
{lessons}
<h3>Quests, treasures and eggs for this band</h3>
<p class="rule" data-rule="quests">listed when the quest names this band in its own <code>band</code> field.</p>
{quests}
<h3>Out in the wilds</h3>
<p class="rule" data-rule="sites">a wilds site is listed when it names a lesson that fits this band.</p>
{sites}
</section>'''


stage_rows = ''.join(
    f'<li><b>{E(s["title"])}</b> <span class="meta">({E(s["stage"])})</span> - {E(s["what"])}.'
    f' <span class="meta">Gamified: {E(s["gamified"])}.</span></li>' for s in STAGES)
district_rows = ''.join(
    f'<tr><td>{E(req(d, "district", "district"))}</td><td>{E(req(d, "city", d["district"]))}</td>'
    f'<td class="status">{E(req(d, "status", d["district"]))}</td></tr>' for d in DISTRICTS)
jump = ''.join(f'<a href="#band-{E(b)}">{E(b)} {E(PATHS[b]["band"]["level"])}</a>' for b in BAND_IDS)
bands_html = '\n'.join(band_section(b) for b in BAND_IDS)

NAV = nav_html(PAGE_PATH, nav_labels('en'))
page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>SmartCiti.X : Trade Craft Academy — K-12 pathways</title>
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);
  font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px 48px}}
.wrap{{max-width:980px;margin:0 auto}}
header{{padding:36px 0 10px;border-bottom:3px solid var(--mark)}}
header h1{{font:700 34px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}}
header h1 .x{{color:var(--mark)}}
header p{{color:var(--muted);margin:6px 0 10px}}
a{{color:var(--steel)}}
.honesty{{background:var(--sunk);border-inline-start:3px solid var(--mark);border-radius:6px;
  padding:12px 22px;color:var(--muted);font-size:14px;margin:18px 0}}
.honesty li{{margin:4px 0}}
.jump{{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}}
.jump a{{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:6px 12px;
  text-decoration:none;color:var(--ink)}}
.band{{border-top:1px solid var(--rule);padding:18px 0 8px;margin-top:18px}}
.band h2{{font:700 28px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:0 0 6px}}
.band h2 .bn{{color:var(--mark)}}
.band h2 .tier{{font:500 14px/1 "IBM Plex Sans",system-ui,sans-serif;color:var(--steel);margin-inline-start:8px}}
.band h3{{font-size:17px;margin:20px 0 4px}}
.offer{{color:var(--ink);margin:4px 0}}
.rule{{color:var(--muted);font-size:14px;margin:2px 0 8px}}
.figs{{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}}
.fig{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:8px 14px;min-width:120px}}
.fig b{{display:block;font:600 24px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--mark)}}
.fig span{{color:var(--muted);font-size:13px}}
ul.lessons,ul.quests,ul.sites,ul.stages{{padding-inline-start:20px;margin:6px 0}}
ul.lessons li,ul.quests li{{margin:3px 0;overflow-wrap:anywhere}}
.meta{{color:var(--muted);font-size:13px}}
.auth{{color:var(--steel)}}
.qk{{display:inline-block;background:var(--panel);border:1px solid var(--rule);border-radius:4px;
  padding:0 6px;font-size:12px;color:var(--mark)}}
.hint{{color:var(--muted);font-size:14px}}
.empty{{color:var(--muted);font-style:italic}}
.tscroll{{overflow-x:auto;max-width:100%}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border-top:1px solid var(--rule);padding:6px 8px;text-align:start;vertical-align:top}}
th{{color:var(--muted);font-weight:600}}
td.num{{text-align:end;font-variant-numeric:tabular-nums}}
td.status{{color:var(--muted)}}
code{{font-size:13px}}
@media (max-width:560px){{header h1{{font-size:28px}}.fig{{min-width:0;flex:1 1 40%}}}}
</style>
<style>{NAV_CSS}</style>
</head>
<body>
{NAV}<div class="wrap" id="main">
<header>
  <h1>SmartCiti<span class="x">.X</span> : Trade Craft Academy — K-12 pathways</h1>
  <p>Four grade bands through the flipped classroom: what each band walks, builds, practises and verifies, computed from the registries.</p>
</header>
<ul class="honesty" id="honesty">
  <li data-honesty="districts">{E(S_HONESTY["districts"])}</li>
  <li data-honesty="certification">{E(S_HONESTY["certification"])}</li>
  <li data-honesty="lessons">Lesson content is {E(L_CONTENT)}</li>
  <li data-honesty="quests">{E(Q_HONESTY)}</li>
</ul>
<nav class="jump" aria-label="Grade bands">{jump}</nav>
<section id="loop">
<h2>The flipped loop</h2>
<p class="rule">{E(SCHOOLS["model"]["loop"])}.</p>
<ul class="stages">{stage_rows}</ul>
</section>
{bands_html}
<section id="districts">
<h2>Districts</h2>
<p class="rule">Every district below is a PROPOSED partner, named from public record only.</p>
<div class="tscroll"><table><thead><tr><th>District</th><th>City</th><th>Status</th></tr></thead><tbody>{district_rows}</tbody></table></div>
</section>
</div>
</body>
</html>
'''

# the honesty lines reach the page verbatim, or the page is not built
for must in (S_HONESTY['districts'], S_HONESTY['certification'], L_CONTENT, Q_HONESTY,
             req(DISTRICTS[0], 'status', 'district')):
    assert E(must) in page, f'honesty text missing from the page: {must[:60]}'
assert page.count('<h1') == 1, 'one h1'

out = HERE / 'trade_craft_schools.html'
page = apply_seo(page, 'web/trade_craft_schools.html', 'K-12 pathways \u2014 SmartCiti.X : Trade Craft Academy',
    'K-12 pathways by grade band, computed from the lesson, unit, quest and outdoor-site registries; every district is a proposed partner with no agreement.', 'page')
# wave 3 (HOMEUX): MEDIA's pagehero band + the theme layer, head/hero region only;
# every word from the catalog (hero.schools.*), see web/herovideo.py doc_hero().
from herovideo import adopt_doc_hero  # noqa: E402
page = adopt_doc_hero('schools', page)
emit(out, page, ' | '.join(f'{b}: {len(PATHS[b]["lessons"])} lessons, {len(PATHS[b]["units"])} units, '
                           f'{len(PATHS[b]["quests"])} quests' for b in BAND_IDS))
