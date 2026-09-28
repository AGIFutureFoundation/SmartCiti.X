"""The front door, generated.

Every other page in this bundle is built from the registries; index.html
was hand-typed, which meant its figures were a second copy of numbers the
packs already know - and a second copy of a fact is the defect this
bundle lints for everywhere else. It drifted exactly as you would expect:
it still said `400 options` after the locker grew to 447.

So it is generated now. Every number below is READ. Nothing on this page
is typed that a pack could tell us, and a pack that changes moves the
front door with it.

The deep descriptions are AUTHORED prose about what each surface is and,
just as importantly, what it does not claim - a reader arriving at a
training product for the trades is owed the limits in the same breath as
the capability, not in a footnote.
"""
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS, LOOP, PAGES, GROUPS  # noqa: E402
# The eight district hues. web/mapdata.py owns them and the campus
# map, the 3D world and the crew marks all read from there; a second set of
# numbers here would be eight facts with two owners.
from mapdata import HUES  # noqa: E402
# The front door's head tags, background footage and site search each live
# in their own module so the landing page (and, next, every page) shares one
# implementation: web/seo.py, web/herovideo.py, web/sitesearch.py.
from seo import seo_head, seo_tail  # noqa: E402
from herovideo import (hero_video_html, hero_video_control, HERO_VIDEO_CSS,  # noqa: E402
                       HERO_VIDEO_JS)
from sitesearch import search_button, search_dialog, SEARCH_JS, SEARCH_CSS  # noqa: E402


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'i18n').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()
R = lambda p: json.loads((ROOT / p).read_text(encoding='utf-8'))  # noqa: E731

unions = R('unions/registry/unions.json')
sims = R('sims/registry/sims.json')
surfaces = R('surfaces/registry/finishes.json')
world = R('world/registry/world.json')
avatars = R('avatars/registry/avatars.json')
stations = R('stations/registry/stations.json')
agents = R('agents/registry/advisors.json')
crews = R('agents/registry/crews.json')
labels = R('labels/registry/labels.json')
guide = R('guide/registry/guide.json')
restoration = R('restoration/registry/restoration.json')
geo = R('geo/registry/campuses_geo.json')
districts = R('unions/registry/districts.json')['districts']
campuses = R('unions/registry/campuses.json')['campuses']
i18n_en = R('i18n/locales/en.json')
lessons = R('lessons/registry/lessons.json')
auth = R('auth/registry/auth.json')
skills = R('pack/registry/skills.json')
variants = R('pack/registry/variants.json')

# ---------------------------------------------------------------- figures ---
# Read, never typed. Each is the pack's own count or a length over the pack's
# own rows. A `??` default here would be a quiet lie about how much of the
# world exists, so a missing key raises and the build stops.
HALLS = unions['count']
CAMPUSES = len(world['atmos'])
SEATS = len(sims['sims'])
FLOORS = len(surfaces['catalogue'])
WALLS = len(surfaces['wall_catalogue'])
PATTERNS = len(surfaces['patterns'])
GROUNDS = len(world['ground'])
WEATHER = len(world['weather'])
STATIONS = stations['count']
ADVISORS = agents['counts']['advisors']
CREWS = crews['counts']['crews']
CREW_ROLES = crews['counts']['roles']
LABEL_KINDS = labels['counts']['kinds']
LOCALES = len(list((ROOT / 'i18n/locales').glob('*.json')))
LESSONS = lessons['counts']['lessons']
LESSON_STEPS = lessons['counts']['steps']
AUTH_METHODS = auth['counts']['methods']
AUTH_WORKING = auth['counts']['configured_true']
AUTH_AUTHENTICATES = auth['counts']['methods_that_authenticate']
SKILLS = skills['count']
# The ladder's shape, recomputed here rather than restated: one cell per
# (strand, tier), and the cells a seat actually stands on. Every one of the
# eleven seats is machines/applied, so COVERED_POS is 1 of 33 - the figure
# this card exists to be honest about.
STRANDS = len({k['strand'] for k in skills['skills']})
TIERS = len({k['tier'] for k in skills['skills']})
LADDER_CELLS = STRANDS * TIERS
COVERED_POS = len({(v['skill_strand'], v['skill_tier'])
                   for v in sims['sims'].values()})
UNCOVERED_STRANDS = STRANDS - len({v['skill_strand']
                                   for v in sims['sims'].values()})
MODALITIES = len(variants['modalities'])
BANDS = len(variants['bands'])
SITES = len(restoration['sites'])
WALKABLE = len([s for s in restoration['sites'] if s['walkable']])
AV_SECTIONS = len(avatars['sections'])
AV_ALL = sum(len(sec['options']) for sec in avatars['sections'])
ROOMS = HALLS * len(surfaces['halls'][next(iter(surfaces['halls']))]['conditions'])
MODULES = 11_000_000          # the pack's own headline, asserted below
assert unions['honesty'], 'the union roster must carry its honesty block'
assert HALLS == len(unions['unions']), 'the roster and its own count disagree'
# The campus count has two owners - world/ draws the atmospheres, geo/ carries
# the coordinates - and this page states it once. If they ever disagree, the
# front door is the wrong place to find out, so the build stops here instead.
assert CAMPUSES == len(geo['campuses']), (
    f"world/ has {CAMPUSES} campus atmospheres, geo/ has "
    f"{len(geo['campuses'])} campus coordinates")

# The module figure is the one number this page states that is not a length,
# so it is checked against the pack that owns it rather than trusted.
_pack_readme = (ROOT / 'README.md').read_text(encoding='utf-8')
assert f'{MODULES:,}' in _pack_readme, (
    'the module figure on the front door is not the one the bundle states')


# --------------------------------------------------------------- drawn ---
# Three pictures, each one a picture OF something rather than a decoration
# beside it. Nothing here is a stock image, an icon font or a file fetched
# from anywhere: the page draws its own SVG from the same registries every
# figure on it is read from, so a picture cannot disagree with the number
# printed under it.


def hero_map(w=1040, h=340):
    """The ten campuses at their real coordinates, and the routes between.

    An equirectangular projection - longitude straight onto x, latitude onto
    y - which is the wrong projection for measuring anything and the right
    one for a diagram that must not imply a survey. The dot area is the
    hall count, so Treasure Island reads as the flagship because it holds
    the most halls, not because it was drawn bigger.
    """
    pts = {k: (v['lng'], v['lat']) for k, v in geo['campuses'].items()}
    xs = [p[0] for p in pts.values()]
    ys = [p[1] for p in pts.values()]
    pad = 54
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sx = (w - pad * 2) / (x1 - x0)
    sy = (h - pad * 2) / (y1 - y0)
    def xy(lng, lat):
        return (pad + (lng - x0) * sx, h - pad - (lat - y0) * sy)

    flag = 'treasure-island'
    assert flag in pts, 'the flagship campus is not in the geo registry'
    fx, fy = xy(*pts[flag])

    # the graticule: whole degrees of longitude, so the frame is a real
    # grid rather than a texture
    grid = []
    step = 10
    lo = int(x0 // step) * step
    while lo <= x1 + step:
        gx, _ = xy(lo, y0)
        if pad * .4 < gx < w - pad * .4:
            grid.append(f'<line x1="{gx:.1f}" y1="{pad*.5:.0f}" x2="{gx:.1f}" '
                        f'y2="{h-pad*.5:.0f}" class="grat"/>')
        lo += step
    la = int(y0 // step) * step
    while la <= y1 + step:
        _, gy = xy(x0, la)
        if pad * .4 < gy < h - pad * .4:
            grid.append(f'<line x1="{pad*.5:.0f}" y1="{gy:.1f}" x2="{w-pad*.5:.0f}" '
                        f'y2="{gy:.1f}" class="grat"/>')
        la += step

    # Place every dot first, then push the LABELS apart. Drawn straight
    # from the coordinates, Detroit and Pittsburgh printed on top of each
    # other - which is what the projection honestly gives you and is still
    # unreadable. The dots stay exactly where the data puts them; only the
    # text slides, and only vertically, so a label never implies a position
    # its dot does not have.
    placed = []
    for k, (lng, lat) in sorted(pts.items(), key=lambda kv: -kv[1][1]):
        cx, cy = xy(lng, lat)
        ly = cy
        for pk, pcx, ply in placed:
            if abs(pcx - cx) < 96 and abs(ply - ly) < 15:
                ly = ply + 15
        placed.append((k, cx, ly))
    label_y = {k: ly for k, _, ly in placed}

    routes, dots, names = [], [], []
    for k, (lng, lat) in sorted(pts.items(), key=lambda kv: -kv[1][1]):
        cx, cy = xy(lng, lat)
        halls = len(campuses[k]['halls'])
        # area proportional to halls, so a campus twice the size reads twice
        # the size rather than four times it
        r = 5.5 + (halls ** .5) * 1.5
        if k != flag:
            # bowed, not straight: a straight line between two points on a
            # sphere is the one thing this projection definitely is not
            mx, my = (fx + cx) / 2, (fy + cy) / 2 - abs(cx - fx) * .13
            routes.append(f'<path d="M{fx:.1f} {fy:.1f} Q{mx:.1f} {my:.1f} '
                          f'{cx:.1f} {cy:.1f}" class="route"/>')
        cls = 'dot flag' if k == flag else 'dot'
        dots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="{cls}">'
                    f'<title>{esc(campuses[k]["name"])} \u2014 {halls} halls, '
                    f'{esc(campuses[k]["city"])}</title></circle>')
        anchor, dx = ('end', -r - 7) if cx > w * .6 else ('start', r + 7)
        ly = label_y[k]
        # a leader line where the label had to move, so the pairing stays
        # obvious rather than becoming a guess
        if abs(ly - cy) > 1:
            names.append(f'<line x1="{cx+dx*.5:.1f}" y1="{cy:.1f}" '
                         f'x2="{cx+dx:.1f}" y2="{ly:.1f}" class="lead"/>')
        names.append(f'<text x="{cx+dx:.1f}" y="{ly+4:.1f}" text-anchor="{anchor}" '
                     f'class="cname">{esc(campuses[k]["city"])}</text>')

    return (f'<svg viewBox="0 0 {w} {h}" class="hero" role="img" '
            f'aria-label="The ten campuses at their real coordinates, '
            f'{n(HALLS)} halls between them">'
            f'<rect width="{w}" height="{h}" class="plate"/>'
            + ''.join(grid) + ''.join(routes) + ''.join(dots) + ''.join(names)
            + f'<text x="{pad*.5:.0f}" y="{h-14}" class="cap">WGS84 \u00b7 '
            f'equirectangular \u00b7 dot area is the hall count \u00b7 routes are '
            f'drawn, not surveyed</text></svg>')


def district_bar(w=1040, h=124):
    """All 111 halls, banded by district, in each district's own hue."""
    tot = sum(len(d['halls']) for d in districts.values())
    assert tot == HALLS, f'the districts hold {tot} halls, the roster says {HALLS}'
    out, x = [], 0.0
    for k, d in districts.items():
        c = len(d['halls'])
        seg = (w - 0) * c / tot
        hue = HUES[k]
        out.append(f'<rect x="{x:.1f}" y="0" width="{seg-2:.1f}" height="34" '
                   f'rx="3" fill="hsl({hue} 52% 46%)" class="seg">'
                   f'<title>{esc(d["name"])} \u2014 {c} halls</title></rect>')
        # "Transport & Mobility" is wider than the ten-hall band it sits
        # under, so it ran into its neighbour. Wrap onto two lines rather
        # than truncate: the district's name is the one thing this band is
        # for, and a clipped name is a name nobody can read.
        words, lines, cur = esc(d['name']).split(' '), [], ''
        for wd in words:
            if len(cur) + len(wd) + 1 <= 13 or not cur:
                cur = (cur + ' ' + wd).strip()
            else:
                lines.append(cur); cur = wd
        lines.append(cur)
        # Three lines, not two. At two, "Transport & Mobility" printed as
        # "Transport &" and "Survey, Safety & Environment" lost the word
        # Environment - a clipped name, which is the thing the wrap was
        # added to avoid. Every district name fits in three.
        assert len(lines) <= 3, f'{k}: {d["name"]} needs {len(lines)} lines'
        for li, ln in enumerate(lines):
            out.append(f'<text x="{x:.1f}" y="{50 + li*11:.0f}" class="dname">{ln}</text>')
        out.append(f'<text x="{x:.1f}" y="{50 + len(lines)*11 + 4:.0f}" '
                   f'class="dcount">{c} halls</text>')
        # every hall as its own tick, so the band is a count and not a bar
        for i in range(c):
            tx = x + 2 + (seg - 6) * (i + .5) / c
            out.append(f'<rect x="{tx:.1f}" y="108" width="1.6" height="10" '
                       f'rx=".8" fill="hsl({hue} 52% 58%)" opacity=".85"/>')
        x += seg
    return (f'<svg viewBox="0 0 {w} {h}" class="bar" role="img" '
            f'aria-label="{n(HALLS)} halls across {len(districts)} districts">'
            + ''.join(out) + '</svg>')


def seat_strip(w=1040, h=96):
    """One tile per operable training seat, drawn as its own silhouette."""
    ids = list(sims['sims'])
    cell = w / len(ids)
    out = []
    for i, sid in enumerate(ids):
        x = i * cell
        sm = sims['sims'][sid]
        # a schematic mark per seat, built from the seat's own id so two
        # seats cannot share a drawing by accident
        seed = sum(ord(ch) for ch in sid)
        bars = ''.join(
            f'<rect x="{x+12+j*7:.1f}" y="{36 - ((seed >> j) % 5 + 2) * 3:.1f}" '
            f'width="4" height="{((seed >> j) % 5 + 2) * 3}" rx="1" '
            f'class="sbar" opacity="{.45 + .07*j:.2f}"/>' for j in range(5))
        # "Overhead Crane Shop Move" is three times the width of the tile
        # it names, and printed on one line it ran straight through its
        # neighbours. Stack the words instead: a seat's name is the whole
        # point of the tile, so it wraps rather than clipping.
        words, lines, cur = esc(sm['name']).split(' '), [], ''
        for wd in words:
            if len(cur) + len(wd) + 1 <= 11 or not cur:
                cur = (cur + ' ' + wd).strip()
            else:
                lines.append(cur); cur = wd
        lines.append(cur)
        lines = lines[:3]
        top = h - 10 - (len(lines) - 1) * 10
        txt = ''.join(
            f'<text x="{x+cell/2:.1f}" y="{top + li*10:.1f}" text-anchor="middle" '
            f'class="sname">{ln}</text>' for li, ln in enumerate(lines))
        out.append(f'<g class="seat"><rect x="{x+2:.1f}" y="4" width="{cell-6:.1f}" '
                   f'height="{h-8}" rx="7" class="stile"/>{bars}{txt}'
                   f'<title>{esc(sm["name"])}</title></g>')
    return (f'<svg viewBox="0 0 {w} {h}" class="strip" role="img" '
            f'aria-label="{n(SEATS)} operable training seats">'
            + ''.join(out) + '</svg>')


def esc(t):
    return (' '.join(str(t).split())
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def need(node, key, where):
    """Read one registry field, or stop the build naming the path.

    The front door prints a seat's task line and its rubric thresholds. A
    `??` or a `.get(key, '')` here would put a blank where a threshold
    belongs and ship it, which is worse than not shipping: a reader would
    take the silence for "no limit". A default is a policy decision, and
    the policy for a registry that has lost a field is to refuse the page
    and say which field, in the path the reader has to go and open.
    """
    if not isinstance(node, dict) or key not in node:
        raise KeyError(f'sims/registry/sims.json: {where}.{key} is missing, '
                       'and the front door prints it - read it or remove the '
                       'entry; there is no default for it')
    return node[key]


# ------------------------------------------------------- the way in ---------
# WHY THIS BLOCK EXISTS. A visitor arrives with two questions - what can I
# learn here, and where do I start - and an index of surfaces answers
# neither. So the front door leads with a COURSE: one trade's lessons in the
# order the lessons registry's own ladder puts them, reached by the deep link
# the rest of this bundle already answers to (`?hall=<slug>`), and it names
# in the same breath how thin the thing behind that door is.
#
# Every figure below is READ through this file's own `need()` - the one
# web/build_ladder.py carries. A missing field fails here by name rather than
# defaulting: a default is this script deciding, quietly, what a registry
# meant, and on this page that decision would reach a reader as a promise.
LESSONS_PATH = 'lessons/registry/lessons.json'
SIMS_PATH = 'sims/registry/sims.json'
SKILLS_PATH = 'pack/registry/skills.json'
HALLS_PATH = 'pack/registry/halls.json'
SIGNOFF_PATH = 'pack/hall_signoff.mjs'

halls_reg = R(HALLS_PATH)

# -- what a course is, counted from the registry that owns the lessons ------
LESSON_ROWS = need(lessons, 'lessons', LESSONS_PATH)
STEP_KINDS = need(lessons, 'step_kinds', LESSONS_PATH)
LESSON_LADDER = need(lessons, 'ladder', LESSONS_PATH)
LESSON_PREREQS = need(LESSON_LADDER, 'prerequisites', f'{LESSONS_PATH}#ladder')
COURSE_HALLS = need(need(lessons, 'spread', LESSONS_PATH), 'halls', f'{LESSONS_PATH}#spread')

# Which KINDS of step stand a learner in a seat is not a list typed here:
# `step_kinds` declares the file each kind reads, and the kinds that read the
# simulator registry are exactly the kinds that reach a seat.
SEAT_KINDS = {k for k, spec in STEP_KINDS.items()
              if need(spec, 'reads', f'{LESSONS_PATH}#step_kinds.{k}') == SIMS_PATH}
if not SEAT_KINDS:
    raise AssertionError(
        f'{LESSONS_PATH}#step_kinds: no kind of step reads {SIMS_PATH}, so no step '
        'on this page could reach a seat; the front door will not claim one')


def _seat_steps(lid):
    L = LESSON_ROWS[lid]
    return len([s for s in need(L, 'steps', f'{LESSONS_PATH}#lessons.{lid}')
                if need(s, 'kind', f'{LESSONS_PATH}#lessons.{lid}.steps[]') in SEAT_KINDS])


COURSE_OF = {}
for _lid, _L in LESSON_ROWS.items():
    COURSE_OF.setdefault(need(_L, 'hall', f'{LESSONS_PATH}#lessons.{_lid}'), []).append(_lid)
if sorted(COURSE_OF) != sorted(COURSE_HALLS):
    raise AssertionError(
        f'{LESSONS_PATH}: spread.halls and the lessons disagree about which halls '
        'carry a course; the front door will not guess which list is right')

HALL_NAME = {need(h, 'slug', f'{HALLS_PATH}#halls[]'): need(h, 'name', f'{HALLS_PATH}#halls[]')
             for h in need(halls_reg, 'halls', HALLS_PATH)}
COURSES = []
for _slug in COURSE_HALLS:
    if _slug not in HALL_NAME:
        raise KeyError(f'{LESSONS_PATH}#spread.halls: {_slug!r} is in no record of {HALLS_PATH}')
    COURSES.append({
        'hall': _slug,
        'name': HALL_NAME[_slug],
        'lessons': len(COURSE_OF[_slug]),
        'steps': sum(len(need(LESSON_ROWS[i], 'steps', f'{LESSONS_PATH}#lessons.{i}'))
                     for i in COURSE_OF[_slug]),
        'seat_steps': sum(_seat_steps(i) for i in COURSE_OF[_slug]),
    })
COURSE_COUNT = len(COURSES)
HALLS_WITHOUT_COURSE = HALLS - COURSE_COUNT
COURSES_WITH_A_SEAT = len([c for c in COURSES if c['seat_steps']])
COURSES_WITHOUT_A_SEAT = COURSE_COUNT - COURSES_WITH_A_SEAT

# -- the one lesson this page sends a first-time visitor to -------------------
# Chosen by a RULE, not an opinion: the first lesson in the registry's own
# order that sits at the foot of the ladder (nothing has to come before it)
# and whose steps reach a simulator seat. If the registry ever holds no such
# lesson, this build fails rather than picking a second-best one silently.
START = None
for _lid in LESSON_ROWS:
    if _lid not in LESSON_PREREQS:
        raise KeyError(f'{LESSONS_PATH}#ladder.prerequisites: lesson {_lid!r} has no record')
    if not LESSON_PREREQS[_lid] and _seat_steps(_lid):
        START = _lid
        break
if START is None:
    raise AssertionError(
        f'{LESSONS_PATH}: no lesson both stands at the foot of the ladder and reaches a '
        'seat, so this page has no honest first step to offer')
START_L = LESSON_ROWS[START]
START_W = f'{LESSONS_PATH}#lessons.{START}'
START_HALL = need(START_L, 'hall', START_W)
START_STEPS = len(need(START_L, 'steps', START_W))
START_SEAT_STEPS = _seat_steps(START)
START_COURSE = [c for c in COURSES if c['hall'] == START_HALL][0]

# -- how much of the ladder a seat actually stands on -------------------------
# The two figures a training coordinator should read before any other: how
# many of the ladder's rungs carry a seat at all, and how many of THOSE sit
# on a prerequisite chain that carries one too. The second is recomputed here
# from skills.json rather than read out of the block it is compared against,
# because a figure that read its own source would agree with anything.
COVERAGE = need(sims, 'coverage', SIMS_PATH)
CELLS_TOTAL = SKILLS
if need(need(COVERAGE, 'cells', f'{SIMS_PATH}#coverage'), 'total',
        f'{SIMS_PATH}#coverage.cells') != CELLS_TOTAL:
    raise AssertionError(
        f'{SIMS_PATH}#coverage.cells.total disagrees with {SKILLS_PATH} count; the '
        'front door will not choose between two owners of the same number')
BINDINGS = need(sims, 'hall_bindings', SIMS_PATH)
CELLS_WITH_SEAT = {need(b, 'skill_id', f'{SIMS_PATH}#hall_bindings.{h}')
                   for h, bs in BINDINGS.items() for b in bs}
_requires = {need(s, 'skill_id', f'{SKILLS_PATH}#skills[]'):
             need(s, 'requires', f'{SKILLS_PATH}#skills[]')
             for s in skills['skills']}


def _closure(cell):
    """Every cell below this one on the ladder, or fail on a dangling edge.

    An unresolvable prerequisite chain is not an empty one, so this raises
    rather than returning a short answer that would flatter the coverage.
    """
    seen, stack = set(), [cell]
    while stack:
        here = stack.pop()
        if here not in _requires:
            raise KeyError(f'{SKILLS_PATH}: cell {here!r} is required by a cell but has no record')
        for r in _requires[here]:
            if r not in seen:
                seen.add(r)
                stack.append(r)
    return seen


CELLS_WITH_SEAT_UNREACHED = len([c for c in CELLS_WITH_SEAT
                                 if not (_closure(c) & CELLS_WITH_SEAT)])
if CELLS_WITH_SEAT_UNREACHED != len(need(COVERAGE, 'unreachable_seat_cells',
                                         f'{SIMS_PATH}#coverage')):
    raise AssertionError(
        f'{SIMS_PATH}#coverage.unreachable_seat_cells lists '
        f'{len(COVERAGE["unreachable_seat_cells"])} cells; recomputing from {SKILLS_PATH} '
        f'gives {CELLS_WITH_SEAT_UNREACHED}')

# -- how many halls a practitioner has signed off -----------------------------
# Read by IMPORTING pack/hall_signoff.mjs through node, the way
# web/build_ladder.py does, rather than by matching a status string here: the
# module owns which status counts as a sign-off claim, and a front door with
# its own opinion about that would be a second policy.
_signoff = subprocess.run(
    ['node', '--input-type=module', '-e',
     "import { createRequire } from 'node:module';"
     "const require = createRequire(process.cwd() + '/x.js');"
     "const hs = await import('./pack/hall_signoff.mjs');"
     "const halls = JSON.parse(require('fs').readFileSync("
     "  'pack/registry/halls.json','utf8')).halls;"
     "console.log(JSON.stringify({ signed: halls.filter("
     "  (h) => hs.claimsHallSignoff(h.content_status)).length, total: halls.length }));"],
    cwd=str(ROOT), capture_output=True, text=True)
if _signoff.returncode != 0:
    raise RuntimeError(f'cannot read {SIGNOFF_PATH} through node:\n{_signoff.stderr.strip()}')
_signoff = json.loads(_signoff.stdout)
HALLS_SIGNED_OFF = need(_signoff, 'signed', SIGNOFF_PATH)
if need(_signoff, 'total', SIGNOFF_PATH) != HALLS:
    raise AssertionError(
        f'{HALLS_PATH} holds {_signoff["total"]} halls, the union roster holds {HALLS}')


# ------------------------------------------------------------- the seats ---
# One row per operable seat, read from the registry that owns them. Nothing
# below is typed: not the count, not a name, not a task line, not a control
# and not a threshold. The deep link is the seat's own slug, which is the
# key the registry files it under and the value the walkable world
# validates `?sim=` against - so a seat cannot be listed here under a name
# that page would refuse.
SEAT_ROWS = []
for _slug in sims['sims']:
    _s = sims['sims'][_slug]
    _w = f'sims.{_slug}'
    SEAT_ROWS.append({
        'slug': _slug,
        'name': need(_s, 'name', _w),
        'kind': need(_s, 'kind', _w),
        'tier': need(_s, 'skill_tier', _w),
        'task': need(_s, 'task', _w),
        'controls': [(need(c, 'keys', _w + '.controls'),
                      need(c, 'action', _w + '.controls'))
                     for c in need(_s, 'controls', _w)],
        'rubric': [(need(r, 'axis', _w + '.rubric'),
                    need(r, 'measure', _w + '.rubric'),
                    need(r, 'pass', _w + '.rubric'))
                   for r in need(_s, 'rubric', _w)],
    })
assert len(SEAT_ROWS) == SEATS, 'the seat index and the seat count disagree'
# The honesty line the seats themselves carry, printed with them rather
# than paraphrased here - the limit in the same breath as the capability.
SEAT_HONESTY = need(need(sims, 'honesty', 'root'), 'status', 'honesty')


# The seats named in prose. This clause used to type all of them out by
# hand - a second copy of eleven names that no build could have corrected -
# so it is read now, in the registry's own order, with the last one joined
# by "and" the way a sentence wants it.
_names = [esc(r['name']) for r in SEAT_ROWS]
SEAT_LIST = ', '.join(_names[:-1]) + ' and ' + _names[-1]


def seat_index():
    """The deep-link index: every seat, what it asks, and what it measures."""
    out = []
    for r in SEAT_ROWS:
        ctl = ' \u00b7 '.join(f'<kbd>{esc(k)}</kbd> {esc(a)}'
                               for k, a in r['controls'])
        axes = ''.join(
            f'<li><b>{esc(ax)}</b> {esc(me)} '
            f'<span class="pass">pass {esc(pa)}</span></li>'
            for ax, me, pa in r['rubric'])
        out.append(
            f'<li class="seat-row" id="seat-{r["slug"]}">'
            f'<div class="seat-head">'
            f'<a class="seat-open" href="web/trade_craft_3d.html?sim={r["slug"]}">'
            f'\u25b6 {esc(r["name"])}</a>'
            f'<span class="seat-kind">{esc(r["kind"])} \u00b7 {esc(r["tier"])}'
            f' \u00b7 <code>{esc(r["slug"])}</code></span></div>'
            f'<p class="seat-task">{esc(r["task"])}</p>'
            f'<p class="seat-ctl">{ctl}</p>'
            f'<ul class="axes">{axes}</ul></li>')
    return f'<ul class="seats">{"".join(out)}</ul>'


def n(x):
    return f'{x:,}'


# --------------------------------------- the three declared surfaces ------
# The floor plans, the contribution page and the site plans each carry a
# registry that says, in its own words, what the page is and what it is not.
# The front door's card for each is READ from that registry - the body, the
# limit and the badge - never typed here, and each rendered slot names the
# field it was read from in a `data-from` attribute so web/test_home.mjs can
# open the registry and hold the shipped text to the field verbatim. The
# badge is the field's own head clause: everything before its first colon,
# a rule the suite recomputes rather than a word chosen here.
SPACES_PATH = 'spaces/registry/spaces.json'
CONTRIB_PATH = 'contrib/registry/contrib.json'
WORKSITES_PATH = 'worksites/registry/worksites.json'
spaces_reg = R(SPACES_PATH)
contrib_reg = R(CONTRIB_PATH)
worksites_reg = R(WORKSITES_PATH)


def field(reg, path, where):
    """Read `a.b[2].c` off a registry through need(), naming the path."""
    node = reg
    for part in path.split('.'):
        m = re.fullmatch(r'([^\[]+)((?:\[\d+\])*)', part)
        node = need(node, m.group(1), where + '#' + path)
        for idx in re.findall(r'\[(\d+)\]', m.group(2)):
            if not isinstance(node, list) or int(idx) >= len(node):
                raise KeyError(f'{where}#{path}: index [{idx}] is out of range')
            node = node[int(idx)]
    if not isinstance(node, str) or not node.strip():
        raise KeyError(f'{where}#{path} is not a non-empty string')
    return node


def badge_of(text):
    return text.split(':', 1)[0].strip()


DECLARED = {
    'spaces': {
        'href': 'web/trade_craft_spaces.html', 'reg': spaces_reg, 'path': SPACES_PATH,
        'badge': 'honesty.status', 'body': 'honesty.status', 'limit': 'honesty.not_stated',
        'counts': ('counts.spaces', 'counts.items')},
    'contribute': {
        'href': 'web/trade_craft_contribute.html', 'reg': contrib_reg, 'path': CONTRIB_PATH,
        'badge': 'honesty.nothing_sent', 'body': 'honesty.nothing_sent',
        'limit': 'honesty.does_not_prove[1]', 'counts': ('counts.scopes', 'counts.rules')},
    'worksites': {
        'href': 'web/trade_craft_worksites.html', 'reg': worksites_reg, 'path': WORKSITES_PATH,
        'badge': 'honesty.no_multi_user', 'body': 'contract', 'limit': 'honesty.no_multi_user',
        'counts': ('counts.sites', 'counts.roles')},
}
for _k, _d in DECLARED.items():
    for slot in ('badge', 'body', 'limit'):
        _d[slot + '_text'] = field(_d['reg'], _d[slot], _d['path'])
    _d['badge_text'] = badge_of(_d['badge_text'])
    _d['count_values'] = []
    for cp in _d['counts']:
        node = _d['reg']
        for part in cp.split('.'):
            node = need(node, part, _d['path'] + '#' + cp)
        if not isinstance(node, int):
            raise KeyError(f"{_d['path']}#{cp} is not an integer")
        _d['count_values'].append(node)
SPACES_N, SPACES_ITEMS = DECLARED['spaces']['count_values']
CONTRIB_SCOPES, CONTRIB_RULES = DECLARED['contribute']['count_values']
SITES_N, SITE_ROLES = DECLARED['worksites']['count_values']


# ------------------------------------------------------------------ copy ---
# AUTHORED prose. Each card says what the surface IS, what a reader can do
# with it, and what it does not claim - the limits in the same breath as the
# capability, because a training product for the trades owes a reader that.
CARDS = [
    {'href': 'web/trade_craft_ladder.html',
     'title': 'The union training ladder',
     'kicker': f'{n(SKILLS)} skills \u00b7 {n(LADDER_CELLS)} cells a trade \u00b7 '
               f'{n(COVERED_POS)} a seat stands on',
     'body': f"""The module graph and the simulators, joined where a member
        can see it. Each trade's own {n(LADDER_CELLS)} cells -
        {n(STRANDS)} strands by {n(TIERS)} tiers - with the prerequisite
        edges the registry declares, and the cell each training seat proves
        outlined and linked straight into that seat. The same cell can be
        taken {n(MODALITIES * BANDS)} ways: {n(MODALITIES)} modalities across
        {n(BANDS)} support bands.""",
     'limit': f"""Every seat is machines/applied, so a seat stands on
        {n(COVERED_POS)} of {n(LADDER_CELLS)} cells and
        {n(UNCOVERED_STRANDS)} of {n(STRANDS)} strands carry no simulator at
        all. The ladder draws the gaps as plainly as the coverage, and a
        passing run certifies nobody."""},
    {'href': 'web/trade_craft_lessons.html',
     'title': 'The walkable lessons',
     'kicker': f'{n(LESSONS)} lessons \u00b7 {n(LESSON_STEPS)} steps you can stand in',
     'body': f"""{n(LESSONS)} lessons a learner walks rather than reads:
        {n(LESSON_STEPS)} steps that send you to a placard, a station, a tool
        crib, a walkaround, an advisor or a seat, in the room where the work
        happens. Each lesson names the hall it stands in and links through to
        it, and each hall names its lessons back.""",
     'limit': """A step marks itself in the open tab and nowhere else:
        nothing is stored, and no lesson carries a practitioner sign-off."""},
    {'href': 'web/trade_craft_signin.html',
     'title': 'Sign in, and what a bundle with no server cannot do',
     'kicker': f'{n(AUTH_METHODS)} methods \u00b7 {n(AUTH_WORKING)} that work here \u00b7 '
               f'{n(AUTH_AUTHENTICATES)} that authenticate anybody',
     'body': f"""Name whose training record this device holds, or sign a
        real EIP-4361 message with a wallet. All {n(AUTH_METHODS)} methods
        are described, including the ones that are off and exactly what each
        is missing.""",
     'limit': f"""{n(AUTH_AUTHENTICATES)} of {n(AUTH_METHODS)} authenticate
        anybody. An authorization-code exchange needs a server holding a
        client secret and this bundle has none, so Google, Microsoft and
        email-link fail closed rather than setting a flag that would report a
        learner as signed in when nothing signed them in."""},
    {'href': 'web/trade_craft_3d.html', 'lead': True,
     'title': 'The walkable world',
     'kicker': f'{n(HALLS)} halls · {n(CAMPUSES)} campuses · {n(SEATS)} training seats',
     'body': f"""Every hall's floor plan stands up as a building you walk
        through on foot, with doorways cut where two rooms actually meet and
        partitions you cannot pass through. Ten campuses stand on ten
        different regional surfaces - a former naval station's bleached
        apron, delta crushed shell, rail ballast, mill slag - and your
        footsteps take their sound from whatever the registry says is under
        you. {n(SEATS)} operable training seats stand in the yard, and
        the index below links straight into each one:
        {SEAT_LIST}.""",
     'limit': """The physics is schematic - the shape of a hydraulic drive,
        not any machine's response curve - and nothing here is equipment
        certification."""},
    {'href': 'web/trade_craft_interactive.html',
     'title': 'The interactive campus map',
     'kicker': f'toggleable layers · {n(LOCALES)} languages',
     'body': f"""All {n(HALLS)} halls with layers you switch on and off:
        districts, pipeline state, module layers, training stations. Every
        hall opens to its own generated floor plan, and the whole surface
        reads in {n(LOCALES)} languages including right-to-left.""",
     'limit': """A taxonomy of skilled trades, not a roster of chartered
        locals: no real union's logo is drawn and no local is named."""},
    {'href': 'web/trade_craft_geomap.html',
     'title': 'The network geomap',
     'kicker': f'{n(CAMPUSES)} campuses on a real WGS84 map',
     'body': """The network on a real map, with every campus, anchor and
        city frame carrying its own provenance in its own popup - RECORDED
        where a coordinate was taken from a public source, AUTHORED where it
        was placed by us, DERIVED for the great-circle routes between
        them.""",
     'limit': """An AUTHORED coordinate is a placement, not a site. No
        property has been surveyed and no building is depicted."""},
    {'href': 'web/trade_craft_dashboard.html',
     'title': 'The network dashboard',
     'kicker': 'every figure read from its own registry',
     'body': f"""Each number on this page is read live from the pack that
        owns it rather than typed beside it - {n(FLOORS)} floor finishes,
        {n(WALLS)} wall finishes, {n(GROUNDS)} ground recipes,
        {n(STATIONS)} training stations - with the progress meter toward ten
        walkable worlds and both provenance tiers side by side.""",
     'limit': """A figure being consistent is not a figure being verified.
        These count what this bundle contains."""},
    {'href': 'console/trade_craft_console.html',
     'title': 'The adaptive console',
     'kicker': 'the real control plane, running in the page',
     'body': """The Adaptive Challenge Protocol running on real pack data:
        the ZPD dial that picks the next challenge, the hint ladder that
        opens only as far as it has to, and the gates between tiers. Not a
        mock - the same control plane the protocol specifies.""",
     'limit': """It schedules practice. It does not assess competence, and
        nothing it records is a credential."""},
    {'href': 'web/trade_craft_landing.html',
     'title': 'The programme',
     'kicker': 'the ladder, and the honest numbers',
     'body': """What the Academy is for, how the ladder is meant to work,
        and the figures without the polish - including the ones that are
        smaller than a prospectus would print.""",
     'limit': """Lesson content is unverified general practice pending
        authoring by journey-level practitioners from the halls."""},
    {'href': 'web/trade_craft_map.html',
     'title': 'The campus plan',
     'kicker': f'{n(HALLS)} generated floor plans',
     'body': """The engineered drawing: district hues, three-letter hall
        codes, and a floor plan generated for every hall from the skill
        strands that hall actually teaches.""",
     'limit': """A functional programme derived from a trade's own strands,
        not a survey of a building. No address data exists for any hall."""},
    {'href': 'web/trade_craft_languages.html',
     'title': 'Languages',
     'kicker': f'{n(LOCALES)} locales, right-to-left included',
     'body': """The Academy overview in every locale the bundle carries,
        with the right-to-left rendering asserted rather than assumed.""",
     'limit': """Translated by machine and not yet reviewed by native
        speakers of the trades' own vocabulary - the roadmap says so."""},
    {'href': 'web/smartcitix_trade_craft_academy.html',
     'title': 'The protocol specification',
     'kicker': 'including the adversarial review findings',
     'body': """The Adaptive Challenge Protocols rendered in full, with the
        adversarial review kept in the document rather than answered
        privately - the findings against it are part of it.""",
     'limit': """A specification is a design, not a proof that the design
        works on people."""},
    # The three declared surfaces. Body, limit and badge are the registry's
    # own sentences (see DECLARED above); only the title and the counts'
    # words are this script's.
    {'href': DECLARED['spaces']['href'], 'from': DECLARED['spaces'],
     'title': 'The floor plans',
     'kicker': f'{n(SPACES_N)} spaces \u00b7 {n(SPACES_ITEMS)} items drawn to scale',
     'body': DECLARED['spaces']['body_text'],
     'limit': DECLARED['spaces']['limit_text']},
    {'href': DECLARED['contribute']['href'], 'from': DECLARED['contribute'],
     'title': 'The page that builds a contribution',
     'kicker': f'{n(CONTRIB_SCOPES)} consent scopes \u00b7 {n(CONTRIB_RULES)} verifier rules',
     'body': DECLARED['contribute']['body_text'],
     'limit': DECLARED['contribute']['limit_text']},
    {'href': DECLARED['worksites']['href'], 'from': DECLARED['worksites'],
     'title': 'The site plans',
     'kicker': f'{n(SITES_N)} sites \u00b7 {n(SITE_ROLES)} crew roles',
     'body': DECLARED['worksites']['body_text'],
     'limit': DECLARED['worksites']['limit_text']},
]


# ------------------------------------------------------------ the way in ---
# The markup for it. Three things a visitor can DO, one real first step, and
# the whole list of trades that have a course - then the limits, in the same
# breath rather than in a footer, because a reader who has already clicked
# has not been told anything.
def fig(key, value):
    """One figure, in a slot of its own.

    Every number a check has to find on this page is rendered here and only
    here, as the text of a `data-fig`. A check that hunted these out of the
    prose would match the page's own sentences - this bundle has watched a
    prose check flag a trade acronym as a provenance tier - so the figures
    get slots and the checks read slots.
    """
    return f'<b class="fig" data-fig="{esc(key)}">{n(value)}</b>'


DOABLE = [
    ('WORK A COURSE',
     f'Take one trade\'s lessons in the order the ladder puts them - '
     f'{fig("courses", COURSE_COUNT)} of the {fig("halls", HALLS)} halls have a '
     f'course standing in them, and {fig("halls_without_course", HALLS_WITHOUT_COURSE)} '
     f'have no lesson at all. Pick yours below.'),
    ('WALK A HALL',
     f'Stand in any of the {fig("halls_walkable", HALLS)} halls on foot and read '
     f'what is on its walls: every hall has a floor plan you walk through, in '
     f'one of {fig("campuses", CAMPUSES)} campuses.'),
    ('DRIVE A SEAT',
     f'Sit in {fig("seats", SEATS)} operable machine seats and be scored by a '
     f'rubric you can read before you start. {fig("courses_with_a_seat", COURSES_WITH_A_SEAT)} '
     f'of the {fig("courses_listed", COURSE_COUNT)} courses reach one at some step; '
     f'{fig("courses_without_a_seat", COURSES_WITHOUT_A_SEAT)} never do.'),
]

START_CARD = (
    f'<a class="card lead start" id="start-here" '
    f'data-start-lesson="{esc(START)}" data-start-hall="{esc(START_HALL)}" '
    f'href="web/trade_craft_lessons.html?hall={esc(START_HALL)}">'
    f'<span class="kicker">start here &middot; {esc(need(START_L, "hall_name", START_W))} '
    f'&middot; {START_STEPS} steps, {START_SEAT_STEPS} of them in a seat</span>'
    f'<b>{esc(need(START_L, "title", START_W))}</b>'
    f'<p>{esc(need(START_L, "why", START_W))}</p>'
    f'<p class="limit"><span class="limit-tag">why this one, and not an editor\'s pick</span>'
    f'It is the first lesson in the registry\'s own order with nothing ahead of it in the '
    f'lessons pack\'s advisory order over its {n(LESSONS)} lessons - which is not the '
    f'{n(CELLS_TOTAL)}-rung skill ladder the seats stand on, and these lessons do not climb '
    f'that one: each stands on a single rung of it - and whose steps reach a simulator '
    f'seat. Opening it opens the whole '
    f'{esc(need(START_L, "hall_name", START_W))} course: '
    f'{START_COURSE["lessons"]} lessons, {START_COURSE["steps"]} steps, in order.</p>'
    f'<p class="limit"><span class="limit-tag">what finishing it is not</span>'
    f'{esc(need(START_L, "limits", START_W))}</p></a>')

TRADE_LINKS = ''.join(
    f'<a class="trade" data-hall="{esc(c["hall"])}" '
    f'data-course-lessons="{c["lessons"]}" data-course-steps="{c["steps"]}" '
    f'data-course-seat-steps="{c["seat_steps"]}" '
    f'href="web/trade_craft_lessons.html?hall={esc(c["hall"])}">'
    f'<span class="tname">{esc(c["name"])}</span>'
    f'<span class="tsteps">{c["steps"]} steps</span></a>' for c in COURSES)

# The limits, where a visitor meets them. Two of these carry figures this
# script computed above; the other three carry none, because they are not
# quantities and a number invented to make them look measured would be the
# same defect pointing the other way.
LIMITS = [
    ('certification', 'NOT CERTIFICATION',
     'No seat, lesson or course here certifies anyone on anything. The '
     'simulators carry schematic physics and deterministic rubrics; passing '
     'one is practice, not a ticket. Where a trade has a real ticket it is '
     'issued by a jurisdiction, an employer or a hall, and this bundle is '
     'none of those.'),
    ('signoff', 'NOT SIGNED OFF BY ANYONE WHO DOES THE WORK',
     f'{fig("halls_signed_off", HALLS_SIGNED_OFF)} of {fig("halls_signoff_total", HALLS)} '
     'halls carry a practitioner sign-off. Every lesson here is unverified '
     'general practice, written to be argued with and corrected by '
     'journey-level practitioners from the halls it names - and none of them '
     'has reviewed a line of it yet.'),
    ('coverage', 'THE SEATS COVER A THIN SLICE',
     f'{fig("cells_with_seat", len(CELLS_WITH_SEAT))} of the ladder\'s '
     f'{fig("cells_total", CELLS_TOTAL)} rungs carry a simulator seat, and all '
     f'{fig("cells_with_seat_unreached", CELLS_WITH_SEAT_UNREACHED)} of those sit on a '
     'prerequisite chain with no seat anywhere in it. A rung with no seat is '
     'not partly covered; it is uncovered, and the ladder page draws the gaps '
     'as plainly as the coverage.'),
    ('roster', 'NOT A UNION ROSTER',
     'A taxonomy of skilled trades, not a roster of chartered locals. No real '
     'local is named and no real union\'s mark is drawn.'),
    ('survey', 'NOT SURVEYED',
     'No site has been surveyed and no real building is depicted. A campus is '
     'composed from a place\'s own character, and the registry says so in each '
     'record.'),
]


# ------------------------------------------------------------ key figures ---
# The hero's figures. Each carries, in `data-src`, the registry file and the
# field it was counted from, so web/test_home.mjs can open that file, count
# again and hold the shipped number to its own answer. Nothing here is typed:
# a stat whose rule is not one of these reads is not a stat this page prints.
STATS = [
    ('halls', HALLS, 'union halls', 'unions/registry/unions.json#count'),
    ('campuses', CAMPUSES, 'campuses', 'geo/registry/campuses_geo.json#campuses'),
    ('seats', SEATS, 'training seats', 'sims/registry/sims.json#sims'),
    ('lessons', LESSONS, 'walkable lessons', 'lessons/registry/lessons.json#counts.lessons'),
    ('steps', LESSON_STEPS, 'lesson steps', 'lessons/registry/lessons.json#counts.steps'),
    ('modules', MODULES, 'addressable modules', 'README.md'),
    ('surfaces', FLOORS + WALLS, 'built surfaces',
     'surfaces/registry/finishes.json#catalogue+wall_catalogue'),
    ('locales', LOCALES, 'languages', 'i18n/locales/*.json'),
]


def _png_size(rel):
    """A shipped screenshot's pixel size, read from its own PNG header, or
    stop the build naming the file. Width and height go on the <img> so the
    page reserves the space and does not jump as the pictures arrive."""
    path = ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(f'{rel}: the front door shows this screenshot and it is not there')
    head = path.read_bytes()[:24]
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError(f'{rel} is not a PNG')
    return int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')


# ------------------------------------------------------- the learner loop ---
# The six steps are web/sitenav.py's LOOP - the same declaration the site
# header draws its loop strip from - and each step's name is that step's own
# catalog label. What is authored here is one line on what the step asks of
# a learner, and which shipped screenshot (wiki/img/process-*.png, the ones
# web/smoke.mjs captures) shows it. A step with no screenshot says so in a
# labelled placeholder rather than borrowing a picture of something else.
NAV_EN = nav_labels('en')
LOOP_COPY = {
    'web/trade_craft_signin.html': (
        None, None,
        'Say whose training record this device holds, or sign a message with a '
        'wallet. The page lists every method, including the ones that fail closed.'),
    'web/trade_craft_lessons.html': (
        'wiki/img/process-interactive-lessons.png',
        'The interactive campus map with its lessons layer switched on',
        'Pick your trade’s course. Each lesson names the hall it stands in and '
        'every step it will ask of you.'),
    'web/trade_craft_3d.html': (
        'wiki/img/process-3d-sim.png',
        'The walkable world, seen from inside a training seat',
        'Walk the hall on foot, read its walls, and sit in a seat scored by a '
        'rubric you can read before you start.'),
    'web/trade_craft_progress.html': (
        'wiki/img/process-progress-completion.png',
        'The progress page at its section for carrying a record off this device',
        'Carry your record off this device as a file that carries its own digest.'),
    'web/trade_craft_verify.html': (
        'wiki/img/process-verify.png',
        'The verify page, where a record’s digest and rules are checked again',
        'Anyone can recheck the file in a browser. The page says what a pass '
        'means, and what it does not.'),
    'web/trade_craft_contribute.html': (
        'wiki/img/process-contribute.png',
        'The contribute page, where consent scopes are chosen before anything is built',
        'Build a contribution under consent scopes you choose. The page itself '
        'sends nothing anywhere.'),
}
if sorted(LOOP_COPY) != sorted(p for p, _ in LOOP):
    raise AssertionError('web/sitenav.py LOOP and the front door’s loop copy name '
                         'different pages; the strip would show a step it cannot describe')
LOOP_STEPS = []
for _i, (_p, _k) in enumerate(LOOP):
    _img, _alt, _line = LOOP_COPY[_p]
    LOOP_STEPS.append({'page': _p, 'key': _k.split('.')[-1], 'label': NAV_EN[_k],
                       'img': _img, 'alt': _alt, 'line': _line,
                       'size': _png_size(_img) if _img else None})


def loop_strip():
    out = []
    for i, s in enumerate(LOOP_STEPS):
        if s['img']:
            w, h = s['size']
            pic = (f'<img src="{s["img"]}" alt="{esc(s["alt"])}" width="{w}" height="{h}" '
                   f'loading="lazy" decoding="async">')
        else:
            pic = ('<div class="shot-ph" data-placeholder>'
                   '<span>Placeholder</span>No screenshot of this step yet</div>')
        out.append(
            f'<li class="step" data-loop-step="{esc(s["key"])}">'
            f'<a class="step-link" href="{s["page"]}">'
            f'<span class="shot">{pic}</span>'
            f'<span class="step-no" aria-hidden="true"></span>'
            f'<h3>{esc(s["label"])}</h3></a>'
            f'<p>{esc(s["line"])}</p></li>')
    return f'<ol class="loop" aria-label="{esc(NAV_EN["nav.loop"])}">{"".join(out)}</ol>'


# ------------------------------------------------------ who it is for ---------
# Four readers arrive at this door with four different questions. Each path
# is authored prose and a handful of links; every link label that names a
# page is that page's own catalog label, so the path and the header can never
# call one page by two names.
def _nl(page):
    return esc(NAV_EN[PAGES[page][1]])


PATHS = [
    ('learners', 'Learners and apprentices',
     'Start with one lesson in your own trade, walk it on campus, and keep a '
     'record you can carry off the device.',
     ['web/trade_craft_lessons.html', 'web/trade_craft_3d.html', 'web/trade_craft_progress.html']),
    ('instructors', 'Training directors and instructors',
     'See which rungs of each trade’s ladder a simulator seat stands on and '
     'which it does not, and read the protocol that schedules practice.',
     ['web/trade_craft_ladder.html', 'web/trade_craft_dashboard.html',
      'web/smartcitix_trade_craft_academy.html']),
    ('employers', 'Employers checking a record',
     'Recheck a learner’s exported record in your own browser. A pass says the '
     'file is intact and consistent; it is not a certification.',
     ['web/trade_craft_verify.html']),
    ('partners', 'Halls and partners',
     'Contribute training data under consent scopes, lay out work sites and '
     'spaces, or read what the programme is for.',
     ['web/trade_craft_contribute.html', 'web/trade_craft_worksites.html',
      'web/trade_craft_spaces.html', 'web/trade_craft_landing.html']),
]
for _k, _t, _b, _links in PATHS:
    for _p in _links:
        if _p not in PAGES or not (ROOT / _p).is_file():
            raise FileNotFoundError(f'audience path {_k}: {_p} is not a built, declared page')


def paths_html():
    out = []
    for k, title, body, links in PATHS:
        lis = ''.join(f'<li><a href="{p}">{_nl(p)}<span aria-hidden="true"> →</span></a></li>'
                      for p in links)
        out.append(f'<article class="path" data-path="{k}"><h3>{esc(title)}</h3>'
                   f'<p>{esc(body)}</p><ul>{lis}</ul></article>')
    return f'<div class="paths">{"".join(out)}</div>'


# ------------------------------------------ what a record is and is not -------
# Read verbatim from the registry the verifier itself is built on, each line
# naming its field in `data-from`. The front door does not paraphrase what a
# record proves: a paraphrase is a second claim, and the second claim is the
# one that drifts.
COMPLETION_PATH = 'completion/registry/completion.json'
completion_reg = R(COMPLETION_PATH)
_c_honesty = need(completion_reg, 'honesty', COMPLETION_PATH)
RECORD_PROVES = need(_c_honesty, 'proves', f'{COMPLETION_PATH}#honesty')
RECORD_NOT = need(_c_honesty, 'does_not_prove', f'{COMPLETION_PATH}#honesty')
RECORD_ACCRED = field(completion_reg, 'honesty.accreditation', COMPLETION_PATH)
for _name, _rows in (('proves', RECORD_PROVES), ('does_not_prove', RECORD_NOT)):
    if not isinstance(_rows, list) or not _rows or not all(isinstance(r, str) and r.strip() for r in _rows):
        raise KeyError(f'{COMPLETION_PATH}#honesty.{_name} is not a list of sentences')


def record_html():
    def rows(name, items):
        return ''.join(f'<li data-from="{COMPLETION_PATH}#honesty.{name}[{i}]">{esc(t)}</li>'
                       for i, t in enumerate(items))
    return (
        '<div class="record">'
        '<div class="rec rec-yes"><h4>A verified record proves</h4>'
        f'<ul>{rows("proves", RECORD_PROVES)}</ul></div>'
        '<div class="rec rec-no"><h4>It does not prove</h4>'
        f'<ul>{rows("does_not_prove", RECORD_NOT)}</ul></div>'
        f'<p class="rec-foot" data-from="{COMPLETION_PATH}#honesty.accreditation">'
        f'{esc(RECORD_ACCRED)}</p></div>')


def _catalog(key):
    """One string out of the en catalog, or stop the build naming the key."""
    s = need(i18n_en, 'strings', 'i18n/locales/en.json')
    if not isinstance(s.get(key), str) or not s[key].strip():
        raise KeyError(f'i18n/locales/en.json: strings.{key} is missing, and the front door prints it')
    return s[key]



# ------------------------------------------------------------------ page ---
# One small design system, declared once as tokens: a type scale, a spacing
# scale, three radii, the surface/ink/accent colours for dark AND light (the
# reader's own prefers-color-scheme picks), and one focus ring. Every rule
# below reads a token; a colour typed further down is a bug. The contrast of
# each ink on each surface was measured in the browser with getComputedStyle
# (web/test_home.mjs --browser holds body text to WCAG AA in both schemes).
CSS = """
:root{
  --fs-xs:12.5px;--fs-sm:14px;--fs-md:16px;--fs-lg:18px;--fs-xl:22px;
  --fs-2xl:clamp(26px,3.2vw,34px);--fs-3xl:clamp(36px,5.4vw,60px);
  --s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:24px;--s6:32px;--s7:48px;--s8:72px;
  --r-sm:6px;--r-md:10px;--r-lg:16px;
  --font:"IBM Plex Sans",system-ui,sans-serif;
  --display:"Barlow Condensed","IBM Plex Sans",system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,monospace;
  color-scheme:dark;
  --plate:#0D1316;--panel:#141C20;--sunk:#0A0F11;--raise:#1A252A;
  --ink:#E9EEED;--muted:#B3BFC1;--dim:#8FA0A3;--rule:#27353B;--rule-2:#384A51;
  --mark:#EBA844;--steel:#5FD0DE;--btn:#EBA844;--btn-ink:#17110A;
  --btn2:transparent;--btn2-ink:#E9EEED;--hero:linear-gradient(180deg,#121B1F 0%,#0D1316 100%);
  --shadow:0 1px 2px rgba(0,0,0,.35),0 8px 24px -12px rgba(0,0,0,.6);
  --focus:0 0 0 3px #0D1316,0 0 0 5px #F2C46E;
}
@media (prefers-color-scheme:light){:root{
  color-scheme:light;
  --plate:#F4F6F5;--panel:#FFFFFF;--sunk:#EBEFEE;--raise:#FFFFFF;
  --ink:#13201F;--muted:#3E4D51;--dim:#526267;--rule:#D2DAD8;--rule-2:#B4C1BF;
  --mark:#8C4E00;--steel:#08646F;--btn:#A35C00;--btn-ink:#FFFFFF;
  --btn2:#FFFFFF;--btn2-ink:#13201F;--hero:linear-gradient(180deg,#FFFFFF 0%,#F4F6F5 100%);
  --shadow:0 1px 2px rgba(16,32,31,.06),0 8px 24px -14px rgba(16,32,31,.22);
  --focus:0 0 0 3px #FFFFFF,0 0 0 5px #08646F;
}}
*{box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--plate);color:var(--ink);
  font:var(--fs-md)/1.6 var(--font);-webkit-font-smoothing:antialiased}
img,svg{max-width:100%}
.wrap{max-width:1200px;margin:0 auto;padding-inline:var(--s5)}
a{color:var(--steel);text-underline-offset:3px}
a:focus-visible,button:focus-visible,summary:focus-visible{outline:none;box-shadow:var(--focus);
  border-radius:var(--r-sm)}
code,kbd{font-family:var(--mono)}

/* ---- type ------------------------------------------------------------ */
h1,h2,h3,h4{color:var(--ink);margin:0}
h1{font:700 var(--fs-3xl)/1 var(--display);letter-spacing:.2px}
h1 .x{color:var(--mark)}
h2{font:700 var(--fs-2xl)/1.1 var(--display);letter-spacing:.2px}
h3{font:600 var(--fs-lg)/1.3 var(--font)}
h4{font:600 var(--fs-sm)/1.4 var(--font)}
.eyebrow{display:block;color:var(--mark);font:600 var(--fs-xs)/1.4 var(--mono);
  letter-spacing:.12em;text-transform:uppercase;margin:0 0 var(--s2)}
.lede{color:var(--muted);max-width:72ch;margin:var(--s2) 0 var(--s5)}
.sec-head{margin-bottom:var(--s5)}
section{padding-block:var(--s8) 0}
.sub-head{margin:var(--s7) 0 var(--s2)}
.sub-head + .lede{margin-top:var(--s1)}

/* ---- buttons: one family ---------------------------------------------- */
.btn{display:inline-flex;align-items:center;gap:var(--s2);min-height:44px;
  padding:0 var(--s5);border-radius:var(--r-sm);font:600 var(--fs-md)/1 var(--font);
  text-decoration:none;border:1px solid transparent;transition:transform .12s,background .12s}
.btn-primary{background:var(--btn);color:var(--btn-ink)}
.btn-primary:hover{filter:brightness(1.06);transform:translateY(-1px)}
.btn-secondary{background:var(--btn2);color:var(--btn2-ink);border-color:var(--rule-2)}
.btn-secondary:hover{border-color:var(--mark)}
.btn-row{display:flex;flex-wrap:wrap;gap:var(--s3);margin:var(--s5) 0 0}
.textlink{font-weight:600}

/* ---- hero -------------------------------------------------------------- */
header.top{background:var(--hero);border-bottom:1px solid var(--rule)}
header.top .wrap{padding-block:var(--s7) var(--s7)}
.hero-grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,.9fr);
  gap:var(--s7);align-items:start}
.by{display:inline-block;margin-top:var(--s3);color:var(--dim);
  font:600 var(--fs-xs) var(--mono);letter-spacing:.12em;text-transform:uppercase}
.tagline{font-size:clamp(18px,2vw,21px);line-height:1.5;max-width:56ch;margin:var(--s5) 0 0}
.sub{color:var(--muted);max-width:64ch;margin:var(--s4) 0 0;font-size:var(--fs-sm)}
.also{color:var(--muted);font-size:var(--fs-sm);margin:var(--s4) 0 0}
.figs{background:var(--panel);border:1px solid var(--rule);border-radius:var(--r-lg);
  padding:var(--s5);box-shadow:var(--shadow)}
.figs-title{display:flex;justify-content:space-between;gap:var(--s3);flex-wrap:wrap;
  align-items:baseline;margin-bottom:var(--s4)}
.figs-title h2{font:600 var(--fs-sm)/1.4 var(--font);color:var(--ink)}
.figs-title span{color:var(--dim);font-size:var(--fs-xs)}
.stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;
  background:var(--rule);border:1px solid var(--rule);border-radius:var(--r-md);overflow:hidden;margin:0}
.stat{background:var(--panel);padding:var(--s3) var(--s4)}
.stat dd{margin:0;font:700 28px/1.1 var(--display);color:var(--mark);
  font-variant-numeric:tabular-nums}
.stat dt{color:var(--muted);font-size:var(--fs-xs)}
.stat{display:flex;flex-direction:column-reverse}
.figs-note{color:var(--dim);font-size:var(--fs-xs);margin:var(--s3) 0 0}
.netmap{margin:var(--s7) 0 0}
.netmap figcaption{color:var(--dim);font-size:var(--fs-xs);margin-top:var(--s2)}

/* ---- cards: one family -------------------------------------------------- */
.paths{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--s4)}
.path,a.card,.pv,.seat-row,.rec{background:var(--panel);border:1px solid var(--rule);
  border-radius:var(--r-md)}
.path{padding:var(--s5);display:flex;flex-direction:column;gap:var(--s2);
  border-top:3px solid var(--mark)}
.path p{margin:0;color:var(--muted);font-size:var(--fs-sm);flex:1}
.path ul{list-style:none;margin:var(--s3) 0 0;padding:var(--s3) 0 0;
  border-top:1px solid var(--rule);display:grid;gap:var(--s1)}
.path a{font-weight:600;font-size:var(--fs-sm);text-decoration:none;display:inline-block;
  padding:2px 0}
.path a:hover{text-decoration:underline}

/* ---- the learner loop ----------------------------------------------------- */
.loop{list-style:none;margin:0;padding:0;counter-reset:step;display:grid;
  grid-template-columns:repeat(6,minmax(0,1fr));gap:var(--s4)}
.step{counter-increment:step;display:flex;flex-direction:column;position:relative}
.step-link{display:flex;flex-direction:column;gap:var(--s2);text-decoration:none;color:inherit}
.shot{display:block;aspect-ratio:16/10;overflow:hidden;border-radius:var(--r-md);
  border:1px solid var(--rule);background:var(--sunk)}
.shot img{display:block;width:100%;height:100%;object-fit:cover;object-position:top left;
  transition:transform .2s}
.step-link:hover .shot img{transform:scale(1.03)}
.step-link:hover .shot{border-color:var(--mark)}
.shot-ph{height:100%;display:grid;place-content:center;text-align:center;gap:var(--s1);
  color:var(--muted);font-size:var(--fs-xs);padding:var(--s3);
  background:repeating-linear-gradient(135deg,transparent 0 10px,var(--rule) 10px 11px)}
.shot-ph span{font:600 11px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--dim)}
.step-no::before{content:counter(step);display:inline-grid;place-items:center;
  width:26px;height:26px;border-radius:50%;background:var(--btn);color:var(--btn-ink);
  font:700 var(--fs-xs)/1 var(--font)}
.step-no{margin-top:var(--s1)}
.step h3{font-size:var(--fs-md);color:var(--ink)}
.step-link:hover h3{color:var(--mark)}
.step p{margin:var(--s1) 0 0;color:var(--muted);font-size:var(--fs-sm);line-height:1.5}

/* ---- the way in ---------------------------------------------------------- */
.fig{color:var(--mark);font-family:var(--mono);font-weight:600;font-variant-numeric:tabular-nums}
.prov{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:var(--s3)}
.prov.limitrow{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.doable{margin-bottom:var(--s5)}
.pv{padding:var(--s4) var(--s5)}
.pv b{display:block;font:600 var(--fs-xs)/1.4 var(--mono);letter-spacing:.1em;
  color:var(--steel);margin-bottom:var(--s2)}
.pv b.fig{display:inline;font:600 inherit/inherit var(--mono);letter-spacing:0;
  margin-bottom:0;color:var(--mark)}
.pv span{color:var(--muted);font-size:var(--fs-sm)}
.limitrow .pv{border-inline-start:3px solid var(--mark)}
a.card{display:flex;flex-direction:column;padding:var(--s5);color:inherit;text-decoration:none;
  transition:border-color .15s,transform .15s,box-shadow .15s}
a.card:hover{border-color:var(--mark);transform:translateY(-2px);box-shadow:var(--shadow)}
a.card.lead{grid-column:1/-1;border-color:var(--rule-2)}
a.card b{font:600 var(--fs-xl)/1.2 var(--display);color:var(--ink);margin-bottom:var(--s2)}
a.card.lead b{font-size:26px}
a.card .kicker{color:var(--mark);font:600 var(--fs-xs)/1.4 var(--mono);
  letter-spacing:.06em;text-transform:uppercase;margin-bottom:var(--s2)}
a.card p{margin:0;color:var(--muted);font-size:var(--fs-sm)}
a.card .limit{margin-top:var(--s3);padding-top:var(--s3);border-top:1px dashed var(--rule-2);
  color:var(--muted);font-size:13.5px}
.limit-tag{color:var(--dim);font:600 11.5px var(--mono);letter-spacing:.08em;
  text-transform:uppercase;display:block;margin-bottom:var(--s1)}
a.card .badge{display:inline-block;align-self:start;margin:0 0 var(--s2);padding:2px 8px;
  border:1px solid var(--rule-2);border-radius:999px;color:var(--muted);
  font:600 11.5px var(--mono);letter-spacing:.05em;text-transform:uppercase}
a.card.start{margin:0;border-inline-start:3px solid var(--mark)}
a.card.start .limit + .limit{margin-top:var(--s2)}
.trades{display:grid;grid-template-columns:repeat(auto-fill,minmax(236px,1fr));gap:var(--s2)}
a.trade{display:flex;justify-content:space-between;align-items:baseline;gap:var(--s3);
  background:var(--panel);border:1px solid var(--rule);border-radius:var(--r-sm);
  padding:var(--s2) var(--s3);color:var(--ink);text-decoration:none;font-size:var(--fs-sm)}
a.trade:hover{border-color:var(--mark)}
a.trade .tsteps{color:var(--dim);font:12px var(--mono);white-space:nowrap}

/* ---- trust ----------------------------------------------------------- */
.trust{background:var(--sunk);border-block:1px solid var(--rule);margin-top:var(--s8);
  padding-block:var(--s7) var(--s7)}
.trust section{padding-top:0}
.record{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.4fr);gap:var(--s4)}
.rec{padding:var(--s4) var(--s5)}
.rec h4{margin-bottom:var(--s2)}
.rec-yes h4{color:var(--steel)}
.rec-no h4{color:var(--mark)}
.rec ul{margin:0;padding-inline-start:1.1em;display:grid;gap:var(--s2)}
.rec li{color:var(--muted);font-size:var(--fs-sm);line-height:1.5}
.rec-foot{grid-column:1/-1;margin:0;color:var(--ink);font-weight:600;font-size:var(--fs-sm)}
.rec-foot::first-letter{text-transform:uppercase}

/* ---- the campus -------------------------------------------------------- */
.seats{list-style:none;margin:var(--s4) 0 0;padding:0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:var(--s3)}
.seat-row{padding:var(--s4) var(--s4)}
.seat-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px}
/* every control on the page is at least 24px tall (WCAG 2.5.8), links in
   running prose included - measured in web/test_home.mjs --browser */
.seat-open{font:600 var(--fs-md)/1.3 var(--font);color:var(--mark);text-decoration:none;
  display:inline-block;padding-block:3px}
.lede a,.also a,.gcite a{display:inline-block;padding-block:2px}
.seat-open:hover{text-decoration:underline}
.seat-kind{color:var(--dim);font:12px var(--mono)}
.seat-kind code{color:var(--dim)}
.seat-task{margin:var(--s2) 0 0;color:var(--ink);font-size:var(--fs-sm)}
.seat-ctl{margin:var(--s2) 0 0;color:var(--muted);font-size:13px}
.seat-ctl kbd{background:var(--sunk);border:1px solid var(--rule);border-radius:4px;
  padding:1px 5px;font-size:12px;color:var(--ink)}
.axes{list-style:none;margin:var(--s3) 0 0;padding:var(--s3) 0 0;border-top:1px solid var(--rule)}
.axes li{color:var(--muted);font-size:13px;margin:0 0 5px}
.axes b{color:var(--ink);font:600 13px var(--mono);margin-inline-end:6px}
.axes .pass{color:var(--steel);font:12.5px var(--mono);white-space:nowrap}
details.disclose{margin-top:var(--s4);border:1px solid var(--rule);border-radius:var(--r-md);
  background:var(--panel)}
details.disclose>summary{cursor:pointer;padding:var(--s3) var(--s4);font-weight:600;
  color:var(--ink);min-height:44px;display:flex;align-items:center;gap:var(--s2)}
details.disclose>summary::marker{color:var(--mark)}
details.disclose[open]>summary{border-bottom:1px solid var(--rule)}
details.disclose>.seats{padding:0 var(--s4) var(--s4)}

/* ---- the drawings: SVG this page generated from its own registries ---- */
.hero{display:block;width:100%;height:auto;border:1px solid var(--rule);
  border-radius:var(--r-md);background:var(--sunk)}
.hero .plate{fill:var(--sunk)}
.hero .grat{stroke:var(--rule);stroke-width:1;opacity:.7}
.hero .route{fill:none;stroke:var(--steel);stroke-width:1.2;opacity:.45}
.hero .dot{fill:var(--steel);stroke:var(--sunk);stroke-width:2}
.hero .dot.flag{fill:var(--mark)}
.hero .cname{fill:var(--muted);font:12px var(--font)}
.hero .lead{stroke:var(--dim);stroke-width:1;opacity:.6}
.hero .cap{fill:var(--dim);font:10.5px var(--mono);letter-spacing:.3px;text-transform:uppercase}
.bar,.strip{display:block;width:100%;height:auto;margin:var(--s3) 0 0}
.bar .seg:hover{opacity:.82}
.bar .dname{fill:var(--ink);font:600 11.5px var(--font)}
.bar .dcount{fill:var(--dim);font:10.5px var(--mono)}
.strip .stile{fill:var(--panel);stroke:var(--rule);stroke-width:1}
.strip .sbar{fill:var(--mark)}
.strip .sname{fill:var(--muted);font:9.5px var(--font)}
.strip .seat:hover .stile{stroke:var(--mark)}

/* ---- the index and the guide ----------------------------------------- */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:var(--s4)}
.withguide{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:var(--s5);align-items:start}
#guide{position:sticky;top:var(--s4);background:var(--panel);border:1px solid var(--rule);
  border-radius:var(--r-md);padding:var(--s4)}
.ghead{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;padding-bottom:9px;
  border-bottom:1px solid var(--rule)}
.ghead b{font:600 var(--fs-md) var(--display);color:var(--mark);letter-spacing:.4px}
.ghead span{color:var(--dim);font-size:var(--fs-xs)}
.gwhat{color:var(--muted);font-size:13px;margin:10px 0 12px}
.gasks{display:flex;flex-direction:column;gap:5px;margin-bottom:12px}
.gask{text-align:start;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);
  border-radius:var(--r-sm);padding:8px 10px;font:inherit;font-size:13px;cursor:pointer;min-height:36px}
.gask:hover{border-color:var(--mark)}
.gask[aria-expanded="true"]{border-color:var(--mark);color:var(--mark)}
.gans p{font-size:13px;line-height:1.6;margin:0 0 8px;color:var(--ink)}
.gcite{color:var(--dim);font-size:12px}
.gfoot{color:var(--dim);font-size:12px;margin:12px 0 0;padding-top:10px;border-top:1px solid var(--rule)}

/* ---- footer ------------------------------------------------------------ */
footer{margin-top:var(--s8);border-top:1px solid var(--rule);background:var(--sunk)}
footer .wrap{padding-block:var(--s7)}
.foot-grid{display:grid;grid-template-columns:minmax(0,1.6fr) repeat(5,minmax(0,1fr));gap:var(--s5)}
.foot-brand b{font:700 var(--fs-xl) var(--display);color:var(--ink)}
.foot-brand p{color:var(--muted);font-size:13px;margin:var(--s2) 0 0}
.foot-col .foot-h{margin:0 0 var(--s2);font:600 var(--fs-xs)/1.4 var(--mono);letter-spacing:.1em;text-transform:uppercase;
  color:var(--dim)}
.foot-col ul{list-style:none;margin:0;padding:0;display:grid;gap:var(--s1)}
.foot-col a{color:var(--muted);text-decoration:none;font-size:var(--fs-sm);
  display:inline-block;padding-block:2px}
.foot-col a:hover{color:var(--ink);text-decoration:underline}
.foot-fine{margin-top:var(--s6);padding-top:var(--s5);border-top:1px solid var(--rule)}
.foot-fine p{color:var(--muted);font-size:13px;max-width:90ch;margin:0 0 var(--s2)}

/* ---- responsive ------------------------------------------------------- */
@media(max-width:1080px){
  .loop{grid-template-columns:repeat(3,minmax(0,1fr))}
  .paths{grid-template-columns:repeat(2,minmax(0,1fr))}
  .foot-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
  .foot-brand{grid-column:1/-1}
}
@media(max-width:900px){
  .hero-grid{grid-template-columns:1fr;gap:var(--s6)}
  .withguide{grid-template-columns:1fr}
  #guide{position:static}
  .record{grid-template-columns:1fr}
  .hero .cname,.bar .dname,.bar .dcount,.strip .sname{font-size:13px}
}
@media(max-width:640px){
  .wrap{padding-inline:var(--s4)}
  header.top .wrap{padding-block:var(--s6)}
  section{padding-top:var(--s7)}
  .paths,.loop{grid-template-columns:1fr}
  .loop .step-link{display:grid;grid-template-columns:120px minmax(0,1fr);
    grid-template-rows:auto 1fr;column-gap:var(--s3);align-items:start}
  .loop .shot{grid-row:1/3}
  .loop .step p{margin-inline-start:calc(120px + var(--s3))}
  .btn{flex:1 1 auto;justify-content:center}
  .grid,.seats{grid-template-columns:1fr}
  .trades{grid-template-columns:repeat(2,minmax(0,1fr))}
  a.trade{flex-direction:column;gap:0}
  .foot-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .stat dd{font-size:24px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}html{scroll-behavior:auto}}
"""



def card(c):
    d = c['from'] if 'from' in c else None
    src = (lambda slot: f' data-from="{esc(d["path"])}#{esc(d[slot])}"') if d else (lambda slot: '')
    badge = (f'<span class="badge" data-badge{src("badge")}>{esc(d["badge_text"])}</span>'
             if d else '')
    return (
        f'<a class="card{" lead" if c.get("lead") else ""}" href="{c["href"]}"'
        f'{" data-declared=" + chr(34) + esc(d["path"]) + chr(34) if d else ""}>'
        f'<span class="kicker">{esc(c["kicker"])}</span>'
        f'<b>{esc(c["title"])}</b>{badge}'
        f'<p{src("body")}>{esc(c["body"])}</p>'
        f'<p class="limit"{src("limit")}><span class="limit-tag">What it does not claim</span>'
        f'{esc(c["limit"])}</p></a>')


# The five words, each in a slot of its own. A tier is rendered ONLY here, as
# the `data-tier` of a `.pv`, so there is exactly one place on this page where
# a word claims to be a provenance tier and exactly one place a check has to
# look - the same discipline web/build_lessons.py holds its chips to. A check
# that read the prose instead would flag the trade acronym HVAC, which has
# happened in this bundle.
PROV = [
    ('RECORDED', 'taken from a public source and cited where it is used'),
    ('DERIVED', 'computed from something recorded, by a rule you can read'),
    ('AUTHORED', 'written by us, and labelled as written rather than found'),
    ('SCHEMATIC', 'the shape of a thing, not a measurement of one'),
    ('SCRIPTED', 'a hand-written deterministic policy, with no model behind it'),
]

# ------------------------------------------------------- the guide ------
# The same helper the walkable world carries, on the front door. Six fixed
# questions about this page, answered from guide/registry/guide.json - the
# `home` place - with each answer citing the file it was written from.
# Nothing here takes free text, because nothing behind it could answer free
# text, and nothing here is fetched.
GUIDE_HOME = guide['places']['home']
assert [t['id'] for t in GUIDE_HOME['topics']] == \
    [a['id'] for a in guide['ask_set'][0]['asks']] if isinstance(
        guide['ask_set'][0].get('asks'), list) else True

GUIDE_HTML = f"""<aside id="guide" aria-label="guide">
  <div class="ghead">
    <b>\u2753 Guide</b>
    <span>{esc(GUIDE_HOME['name'])}</span>
  </div>
  <p class="gwhat">{esc(GUIDE_HOME['what_line'])}</p>
  <div class="gasks">
    {''.join(f'<button class="gask" data-a="{t["id"]}"'
             f'{" aria-expanded=true" if i == 0 else ""}>{esc(t["ask"])}</button>'
             for i, t in enumerate(GUIDE_HOME['topics']))}
  </div>
  {''.join(f'<div class="gans" id="ga-{t["id"]}"{"" if i == 0 else " hidden"}>'
           f'<p>{esc(t["answer"])}</p>'
           f'<p class="gcite">read from <code>{esc(t["cites"])}</code></p></div>'
           for i, t in enumerate(GUIDE_HOME['topics']))}
  <p class="gfoot">{esc(guide['honesty']['status'])}</p>
</aside>"""

GUIDE_JS = """<script>
/* The guide is six buttons and six answers, all of them already on the
   page. No fetch, no template, no state worth losing: clicking an ask
   shows its answer and hides the others. It works without JavaScript too -
   every answer is in the markup and only the hiding is scripted, so a
   reader with scripts off gets all six rather than none. */
(function () {
  var asks = document.querySelectorAll('.gask');
  asks.forEach(function (b) {
    b.addEventListener('click', function () {
      asks.forEach(function (o) {
        var a = document.getElementById('ga-' + o.dataset.a);
        var on = o === b;
        o.setAttribute('aria-expanded', on ? 'true' : 'false');
        if (a) a.hidden = !on;
      });
    });
  });
}());
</script>"""

NAV = nav_html('index.html', nav_labels('en'))

# The <main id="main"> a skip link lands on. test_nav holds that the site
# nav is the first thing in <body>, so the skip link itself belongs INSIDE
# nav_html (web/sitenav.py, requested of its owner) rather than before it;
# its style ships here and in NAV_CSS's owner's hands alike.
UX_CSS = """
.sitenav-skip,.skip{position:absolute;inset-inline-start:12px;inset-block-start:-100px;z-index:100;
  padding:10px 16px;border-radius:8px;background:var(--btn);color:var(--btn-ink);
  font-weight:700;text-decoration:none}
.sitenav-skip:focus,.skip:focus{inset-block-start:12px;outline:none;box-shadow:var(--focus)}
main:focus{outline:none}
"""
from questkit import QUEST_CSS, quest_js, page_hooks  # noqa: E402  quests: egg hooks only
QUEST_TAIL = '<style>' + QUEST_CSS + '</style>\n' + page_hooks('index.html') + quest_js('page:index.html')

STATS_HTML = ''.join(
    f'<div class="stat" data-stat="{k}" data-src="{esc(src)}"><dt>{esc(label)}</dt>'
    f'<dd>{n(v)}</dd></div>' for k, v, label, src in STATS)

FOOT_COLS = ''.join(
    f'<div class="foot-col"><p class="foot-h">{esc(NAV_EN[g])}</p><ul>'
    + ''.join(f'<li><a href="{p}">{_nl(p)}</a></li>' for p, _k in items)
    + '</ul></div>' for g, items in GROUPS)

BODY = f"""<body>
{NAV}<main id="main" tabindex="-1">
<header class="top" data-hero-host>{hero_video_html()}<div class="wrap">
  <div class="hero-grid">
    <div class="hero-copy">
      <span class="eyebrow">Union trade training &middot; walkable campus &middot; verifiable records</span>
      <h1>SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
      <span class="by">powered by AGI Corp</span>
      <p class="tagline">A walkable training world for the skilled trades &mdash;
        {n(HALLS)} union halls across {n(CAMPUSES)} campuses, with
        {n(SEATS)} operable machine seats standing in the yard.</p>
      <p class="sub">Every surface, figure and lesson in this bundle traces to a
        registry you can read, and each carries the word for how it was come by.
        Nothing is fetched at run time; nothing is generated when you look at it.
        Where a thing is unverified, it says so &mdash; on the page, not in an
        appendix.</p>
      <div class="btn-row">
        <a class="btn btn-primary" data-cta="primary" href="web/trade_craft_lessons.html">Start learning</a>
        <a class="btn btn-secondary" data-cta="secondary" href="web/trade_craft_3d.html">Walk the campus</a>
      </div>
      <p class="also">Checking someone&rsquo;s record?
        <a class="textlink" href="web/trade_craft_verify.html">{_nl('web/trade_craft_verify.html')}</a>
        &middot; New here? <a class="textlink" href="#start-here">Take the first lesson</a></p>
      {search_button()}
      {hero_video_control()}
    </div>
    <aside class="figs" aria-labelledby="figs-h">
      <div class="figs-title"><h2 id="figs-h">Key figures</h2>
        <span>counted from the registries when this page was built</span></div>
      <dl class="stats">{STATS_HTML}</dl>
      <p class="figs-note">These count what this bundle contains. A figure being
        consistent is not a figure being verified.</p>
    </aside>
  </div>
  <figure class="netmap">{hero_map()}
    <figcaption>The campuses at their real coordinates; dot area is the hall count.</figcaption></figure>
</div></header>

<div class="wrap">
<section id="paths">
  <div class="sec-head"><span class="eyebrow">Who it is for</span>
    <h2>Four ways in, depending on why you are here</h2></div>
  {paths_html()}
</section>

<section id="loop">
  <div class="sec-head"><span class="eyebrow">How it works</span>
    <h2>The learner loop, in {n(len(LOOP_STEPS))} steps</h2>
    <p class="lede">The same loop the header shows on each of these pages: sign
      in, take a lesson, walk it, carry the record away, have it checked, and
      share it if you choose.</p></div>
  {loop_strip()}
</section>

<section id="start">
  <div class="sec-head"><span class="eyebrow">Start here</span>
  <h2>What you can do here, and where to start</h2>
  <p class="lede">Three things, in plain words. Everything further down this
    page is the index behind them, and the limits come straight after, because
    a reader who has already clicked has not been told anything.</p></div>
  <div class="prov doable">
    {''.join(f'<div class="pv" data-do="{esc(w)}"><b>{esc(w)}</b><span>{d}</span></div>'
             for w, d in DOABLE)}
  </div>
  {START_CARD}
  <h3 id="trades" class="sub-head">Or take your own trade&rsquo;s course</h3>
  <p class="lede">Each link opens that trade's lessons in the order the
    lessons registry's own ladder puts them, with every step numbered straight
    through, each step linking to the simulator seat it opens and saying so
    where it opens none. The number beside a trade is that course's step
    count.</p>
  <nav class="trades" aria-label="courses by trade">{TRADE_LINKS}</nav>
</section>
</div>

<div class="trust"><div class="wrap">
<section id="trust">
  <div class="sec-head"><span class="eyebrow">Trust and limits</span>
  <h2>What none of this is</h2>
  <p class="lede">The limits, stated once, plainly, where a visitor meets
    them.</p></div>
  <div class="prov limitrow" id="limits">
    {''.join(f'<div class="pv" data-limit="{esc(k)}"><b>{esc(w)}</b><span>{d}</span></div>'
             for k, w, d in LIMITS)}
  </div>
  <h3 class="sub-head" id="record">What a record is, and what it is not</h3>
  <p class="lede">Read word for word from the registry the verifier is built
    on, so the front door cannot promise more than the check behind it.</p>
  {record_html()}
  <h3 class="sub-head" id="claims">How to read a claim here</h3>
  <p class="lede">Every record in this bundle carries one of five words for
    how it was come by. They are not decoration: a build refuses a record
    that claims the wrong one, and the suites check it.</p>
  <div class="prov">
    {''.join(f'<div class="pv" data-tier="{w}"><b>{w}</b><span>{esc(d)}</span></div>'
             for w, d in PROV)}
  </div>
</section>
</div></div>

<div class="wrap">
<section id="campus">
  <div class="sec-head"><span class="eyebrow">Inside the campus</span>
  <h2>Every hall, and every seat in the yard</h2></div>
  <h3 class="sub-head">Every hall, by district</h3>
  <p class="lede">All {n(HALLS)} halls, banded into the {len(districts)}
    districts that organise them. Each tick is one hall; the colours are the
    same eight the campus map and the walkable world use.</p>
  {district_bar()}
  <h3 class="sub-head">The yard</h3>
  <p class="lede">{n(SEATS)} operable training seats stand in the campus
    yard. Every one is a machine you sit in and drive, scored by a rubric
    you can read.</p>
  {seat_strip()}
  <h3 class="sub-head" id="seats">Every seat, and the way in</h3>
  <p class="lede">One link per seat, straight into the machine rather than
    into the front of the world. Each says what it asks of you and what it
    measures you against, because the rubric is the whole of the judgement:
    every axis below is computed from measured state, and nothing you say
    about a run can move it. {esc(SEAT_HONESTY)}</p>
  <details class="disclose"><summary>Show all {n(SEATS)} seats with their tasks,
    controls and pass marks</summary>{seat_index()}</details>
</section>
<section id="surfaces">
  <div class="sec-head"><span class="eyebrow">The full index</span>
  <h2>Every surface in this bundle</h2>
  <p class="lede">{n(len(CARDS))} surfaces, each built from the same
    registries, for a reader who wants the whole thing rather than a course.
    <a href="#start-here">The course above</a> is the way in if you do not
    already know this architecture.</p></div>
  <div class="withguide">
    <div class="grid">{''.join(card(c) for c in CARDS)}</div>
    {GUIDE_HTML}
  </div>
</section>
</div>
</main>
<footer><div class="wrap">
  <div class="foot-grid">
    <div class="foot-brand"><b>SmartCiti.X : Trade Craft Academy</b>
      <p>{esc(_catalog('honesty.modules'))}</p></div>
    {FOOT_COLS}
  </div>
  <div class="foot-fine">
  <p>Built from {n(FLOORS)} floor finishes, {n(WALLS)} wall finishes and
    {n(PATTERNS)} surface patterns over {n(GROUNDS)} ground recipes and
    {n(WEATHER)} weather states; {n(STATIONS)} training stations;
    {n(ADVISORS)} advisors and {n(CREWS)} crews of {n(CREW_ROLES)} roles;
    {n(LABEL_KINDS)} kinds of sign; a locker of {n(AV_ALL)} options across
    {n(AV_SECTIONS)} sections; {n(SITES)} real restoration sites, of which
    {n(WALKABLE)} are walkable. Every one of those figures is read from its
    own registry by the script that generated this page.</p>
  </div>
</div></footer>
{GUIDE_JS}
</body>"""


# ------------------------------------------------------------------ gate ---
# The defect this page was generated to end: index.html said `400 options`
# for months after the locker grew to 447, because the figure was typed into
# prose rather than read. Generating the page does not by itself prevent
# that - a number typed into a CARD body would drift exactly the same way.
#
# So every multi-digit figure that survives into the rendered prose must be
# one this script derived. The allow-list below is deliberately short and
# every entry names why that number is not a pack figure; anything else
# stops the build with the number in the message, which is what a reader
# needs to go and find it.
_DERIVED = {
    HALLS, CAMPUSES, SEATS, FLOORS, WALLS, PATTERNS, GROUNDS, WEATHER,
    STATIONS, ADVISORS, CREWS, CREW_ROLES, LABEL_KINDS, LOCALES, SITES,
    WALKABLE, AV_SECTIONS, AV_ALL, ROOMS, MODULES, len(CARDS), len(PROV),
    FLOORS + WALLS,   # the "built surfaces" stat, a sum of two read figures
    len(districts),   # the district count, in the band's own lede
    # Every district's hall count and every campus's, which the drawings
    # print in their tooltips and labels. They are read - `len(d['halls'])`
    # off the registry that owns the roster - so they belong here rather
    # than in an exception list. Adding them by hand would be the very
    # thing this gate exists to stop.
    *(len(d['halls']) for d in districts.values()),
    *(len(c['halls']) for c in campuses.values()),
    # The three cards added when the ladder, the lessons and the sign-in
    # page got a way in from the front door. Each is read or recomputed
    # above from the registry that owns it - the ladder's shape from
    # skills.json, its covered position from the seats' own declared
    # strand and tier - so they belong here for the same reason the
    # district hall counts do.
    LESSONS, LESSON_STEPS, AUTH_METHODS, AUTH_WORKING, AUTH_AUTHENTICATES,
    SKILLS, STRANDS, TIERS, LADDER_CELLS, COVERED_POS, UNCOVERED_STRANDS,
    MODALITIES, BANDS, MODALITIES * BANDS,
    # The course figures the front door now leads with. Every one is counted
    # above from the registry that owns it - the courses and their steps from
    # lessons.json, the rungs from skills.json, the rungs a seat stands on
    # from the seats' own hall_bindings, the sign-off tally by importing
    # pack/hall_signoff.mjs - so they belong here for exactly the reason the
    # district hall counts do, and a number typed into the copy beside them
    # is still caught.
    COURSE_COUNT, HALLS_WITHOUT_COURSE, COURSES_WITH_A_SEAT,
    COURSES_WITHOUT_A_SEAT, HALLS_SIGNED_OFF, CELLS_TOTAL, len(CELLS_WITH_SEAT),
    CELLS_WITH_SEAT_UNREACHED, START_STEPS, START_SEAT_STEPS,
    *(c['lessons'] for c in COURSES),
    *(c['steps'] for c in COURSES),
    *(c['seat_steps'] for c in COURSES),
    # The three declared surfaces' kicker counts, each read off its own
    # registry's `counts` block through need() (see DECLARED above).
    SPACES_N, SPACES_ITEMS, CONTRIB_SCOPES, CONTRIB_RULES, SITES_N, SITE_ROLES,
}



def _figures_in(html):
    """Every multi-digit figure in the rendered text, commas folded.

    Digits glued to letters are not figures - WGS84 is the name of a
    coordinate system, not a count of anything - so a run of digits only
    counts when letters and digits do not touch it on either side.
    """
    text = re.sub(r'<[^>]+>', ' ', html)
    text = text.replace('&mdash;', ' ')
    # ...and neither is the number in a hyphenated standard's designation.
    # EIP-4361 names the sign-in message format the way WGS84 names a
    # coordinate system: 4361 counts nothing and cannot drift. The letters
    # must be UPPERCASE for this to apply, so `top-10` is still a figure and
    # still caught - this narrows the rule rather than opening a hole in it.
    text = re.sub(r'(?<![A-Za-z0-9])[A-Z]{2,}-\d+(?![A-Za-z0-9])', ' ', text)
    found = re.findall(r'(?<![A-Za-z0-9])\d[\d,]*(?![A-Za-z0-9])', text)
    return {int(m.replace(',', ''))
            for m in found if len(m.replace(',', '')) > 1}


# The seat index prints the registry's own rubric thresholds - `>= 90`,
# `>= 95` and the rest - and those are figures too. They are admitted by
# READING THEM BACK out of the very rows the entries were rendered from,
# never by listing them here: retune a threshold in sims.json and the gate
# moves with it, while a threshold typed into this file would still be
# caught. The read is scoped to the exact fields the section renders, so
# this stays a gate rather than a hole.
_DERIVED |= {f for r in SEAT_ROWS
             for txt in ([r['name'], r['kind'], r['tier'], r['task']]
                         + [x for c in r['controls'] for x in c]
                         + [x for a in r['rubric'] for x in a])
             for f in _figures_in(txt)}
_DERIVED |= _figures_in(SEAT_HONESTY)

# The declared surfaces' cards print their registries' own sentences, so any
# figure inside those is admitted by READING IT BACK from the field the card
# was rendered from - the same rule the start card holds for its lesson.
_DERIVED |= {f for d in DECLARED.values()
             for slot in ('badge_text', 'body_text', 'limit_text')
             for f in _figures_in(d[slot])}

# The start card prints the chosen lesson's own title, `why` and `limits`,
# and those sentences are the registry's, not this script's. Any figure
# inside them is admitted by READING IT BACK out of the very record the card
# was rendered from - never by listing it here - so a rewritten lesson moves
# the gate with it while a number typed into this file is still caught.
_DERIVED |= {f for s in (need(START_L, 'title', START_W),
                         need(START_L, 'why', START_W),
                         need(START_L, 'limits', START_W),
                         need(START_L, 'hall_name', START_W))
             for f in _figures_in(s)}

_loose = _figures_in(BODY) - _DERIVED
BODY_Q = BODY.replace('</body>', QUEST_TAIL + '</body>')  # quests: engine carried after the prose lint
assert not _loose, (
    'these figures appear in the front door\'s prose but were not read from a '
    'registry by this script: ' + ', '.join(str(x) for x in sorted(_loose)) +
    ' - read them, or the page will drift the way `400 options` did')

_SEO = ('SmartCiti.X : Trade Craft Academy',
        f'A walkable training world for the skilled trades: {HALLS} union halls, '
        f'{CAMPUSES} campuses and {SEATS} operable machine seats, every figure read '
        'from its own registry.', 'home')
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + seo_head('index.html', *_SEO) +
        '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 '
        'viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%226%22 '
        'fill=%22%230C1113%22/%3E%3Cpath d=%22M7 21 L16 7 L25 21 Z%22 fill=%22none%22 '
        'stroke=%22%23E8A33D%22 stroke-width=%222.6%22 stroke-linejoin=%22round%22/%3E'
        '%3Cpath d=%22M11 21 h10%22 stroke=%22%2341C4D4%22 stroke-width=%222.6%22 '
        'stroke-linecap=%22round%22/%3E%3C/svg%3E">\n'
        '<!-- Self-hosted: nothing on this page is fetched from another '
        'origin at run time. See web/fetch_fonts.py. -->\n'
        '<link rel="stylesheet" href="web/vendor/fonts/fonts.css">\n'
        f'<style>{CSS}</style>\n<style>{NAV_CSS}</style>\n'
        f'<style>{HERO_VIDEO_CSS}{SEARCH_CSS}{UX_CSS}</style>\n</head>\n{BODY_Q}\n</html>\n')
# The palette's index (registry titles, which may hold figures of their own)
# and the two small scripts join the page after the prose gate above, like
# the quest engine: the gate is about typed prose, and these are data.
_tail = (search_dialog('index.html') + SEARCH_JS + '\n' + HERO_VIDEO_JS + '\n'
         + seo_tail('index.html', *_SEO))
assert page.count('</body>') == 1, 'build_home: expected exactly one </body>'
page = page.replace('</body>', _tail + '</body>')

emit(ROOT / 'index.html', page,
     f'{len(CARDS)} cards | {HALLS} halls, {CAMPUSES} campuses, {SEATS} seats')
