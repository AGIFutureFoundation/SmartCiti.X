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
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
# The eight district hues. web/mapdata.py owns them and the campus
# map, the 3D world and the crew marks all read from there; a second set of
# numbers here would be eight facts with two owners.
from mapdata import HUES  # noqa: E402


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
]

STATS = [
    (n(HALLS), 'union halls'),
    (n(CAMPUSES), 'campuses'),
    (n(SEATS), 'training seats'),
    (n(MODULES), 'addressable modules'),
    (n(FLOORS + WALLS), 'built surfaces'),
    (n(CREWS), f'crews, {n(CREW_ROLES)} roles'),
]


# ------------------------------------------------------------------ page ---
CSS = """
:root{--plate:#0E1417;--panel:#161F23;--sunk:#0A0E10;--ink:#E8EDEC;
  --muted:#93A3A6;--dim:#6E7E82;--rule:#25333A;--mark:#E8A33D;--steel:#41C4D4}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--plate);color:var(--ink);
  font:16px/1.65 "IBM Plex Sans",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
a{color:var(--steel)}
header.top{border-bottom:1px solid var(--rule);background:
  linear-gradient(180deg,#121A1E 0%,var(--plate) 100%)}
header.top .wrap{padding-top:58px;padding-bottom:40px}
.brandline{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
h1{font:700 clamp(34px,6vw,58px)/1.02 "Barlow Condensed",system-ui,sans-serif;
  margin:0;letter-spacing:.4px}
h1 .x{color:var(--mark)}
.by{color:var(--dim);font:600 13px "IBM Plex Mono",monospace;letter-spacing:1.4px;
  text-transform:uppercase}
.tagline{color:var(--ink);font-size:clamp(17px,2.2vw,21px);max-width:62ch;margin:18px 0 0}
.sub{color:var(--muted);max-width:68ch;margin:14px 0 0}
.stripe{height:8px;background:repeating-linear-gradient(135deg,
  var(--mark) 0 14px,transparent 14px 28px);opacity:.45}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:1px;background:var(--rule);border:1px solid var(--rule);margin:34px 0 0}
.stat{background:var(--panel);padding:16px 18px}
.stat b{display:block;font:700 26px "Barlow Condensed",sans-serif;color:var(--mark)}
.stat span{color:var(--muted);font-size:13px}
section{padding:52px 0 0}
h2{font:600 26px "Barlow Condensed",sans-serif;margin:0 0 6px;letter-spacing:.3px}
h2 + p.lede{color:var(--muted);margin:0 0 22px;max-width:74ch}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
a.card{display:flex;flex-direction:column;background:var(--panel);
  border:1px solid var(--rule);border-radius:12px;padding:20px 22px 18px;
  color:inherit;text-decoration:none;transition:border-color .15s,transform .15s}
a.card:hover,a.card:focus-visible{border-color:var(--mark);transform:translateY(-2px)}
a.card.lead{grid-column:1/-1;border-color:#3A4B52}
a.card.lead b{font-size:26px}
a.card b{font:600 20px "Barlow Condensed",sans-serif;color:var(--ink);margin-bottom:2px}
a.card .kicker{color:var(--mark);font:600 12px "IBM Plex Mono",monospace;
  letter-spacing:.8px;text-transform:uppercase;margin-bottom:10px}
a.card p{margin:0;color:var(--muted);font-size:14.5px}
a.card .limit{margin-top:12px;padding-top:10px;border-top:1px dashed var(--rule);
  color:var(--dim);font-size:13px}
a.card .limit b2{display:none}
.limit-tag{color:var(--dim);font:600 11px "IBM Plex Mono",monospace;
  letter-spacing:1px;text-transform:uppercase;display:block;margin-bottom:3px}
/* the seat index: one card per operable seat, its task, its controls and
   the axes it is scored on. Two columns where there is room, one where
   there is not - a phone gets the whole of every entry, not a truncated
   one, because the thresholds are the part worth reading. */
.seats{list-style:none;margin:0;padding:0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.seat-row{background:var(--sunk);border:1px solid var(--rule);
  border-radius:10px;padding:15px 17px}
.seat-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px}
.seat-open{font:600 16.5px/1.3 "IBM Plex Sans",system-ui,sans-serif;
  color:var(--mark);text-decoration:none}
.seat-open:hover,.seat-open:focus{text-decoration:underline}
.seat-kind{color:var(--dim);font:11.5px "IBM Plex Mono",monospace;
  letter-spacing:.4px}
.seat-kind code{color:var(--dim)}
.seat-task{margin:9px 0 0;color:var(--ink);font-size:14px}
.seat-ctl{margin:9px 0 0;color:var(--muted);font-size:13px}
.seat-ctl kbd{background:var(--panel);border:1px solid var(--rule);
  border-radius:4px;padding:1px 5px;font:11.5px "IBM Plex Mono",monospace;
  color:var(--ink)}
.axes{list-style:none;margin:11px 0 0;padding:11px 0 0;
  border-top:1px solid var(--rule)}
.axes li{color:var(--muted);font-size:12.5px;margin:0 0 5px}
.axes b{color:var(--ink);font:600 12.5px "IBM Plex Mono",monospace;
  margin-right:6px}
.axes .pass{color:var(--steel);font:12px "IBM Plex Mono",monospace;
  white-space:nowrap}
.prov{display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));gap:14px}
.pv{background:var(--sunk);border:1px solid var(--rule);border-radius:10px;padding:14px 16px}
.pv b{display:block;font:600 13px "IBM Plex Mono",monospace;letter-spacing:1px;
  color:var(--steel);margin-bottom:5px}
.pv span{color:var(--muted);font-size:13.5px}
footer{margin-top:56px;border-top:1px solid var(--rule);background:var(--sunk)}
footer .wrap{padding:26px 20px 40px}
footer p{color:var(--dim);font-size:13px;max-width:82ch;margin:0 0 10px}

/* ---- the drawings ---------------------------------------------------
   Everything below styles SVG this page generated from its own registries.
   No image is fetched; there is nothing to fetch. */
.hero{display:block;width:100%;height:auto;margin:30px 0 0;
  border:1px solid var(--rule);border-radius:10px;background:var(--sunk)}
.hero .plate{fill:var(--sunk)}
.hero .grat{stroke:var(--rule);stroke-width:1;opacity:.55}
.hero .route{fill:none;stroke:var(--steel);stroke-width:1.2;opacity:.42}
.hero .dot{fill:var(--steel);stroke:var(--sunk);stroke-width:2}
.hero .dot.flag{fill:var(--mark)}
.hero .cname{fill:var(--muted);font:11.5px "IBM Plex Sans",sans-serif}
.hero .lead{stroke:var(--dim);stroke-width:1;opacity:.6}
.hero .cap{fill:var(--dim);font:10.5px "IBM Plex Mono",monospace;
  letter-spacing:.3px;text-transform:uppercase}
.bar,.strip{display:block;width:100%;height:auto;margin:18px 0 0}
.bar .seg{transition:opacity .15s}
.bar .seg:hover{opacity:.82}
.bar .dname{fill:var(--ink);font:600 11.5px "IBM Plex Sans",sans-serif}
.bar .dcount{fill:var(--dim);font:10.5px "IBM Plex Mono",monospace}
.strip .stile{fill:var(--panel);stroke:var(--rule);stroke-width:1}
.strip .sbar{fill:var(--mark)}
.strip .sname{fill:var(--muted);font:9.5px "IBM Plex Sans",sans-serif}
.strip .seat:hover .stile{stroke:var(--mark)}

/* ---- the guide, beside the cards ------------------------------------ */
.withguide{display:grid;grid-template-columns:minmax(0,1fr) 320px;
  gap:22px;align-items:start}
#guide{position:sticky;top:18px;background:var(--panel);
  border:1px solid var(--rule);border-radius:10px;padding:16px 16px 14px}
.ghead{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;
  padding-bottom:9px;border-bottom:1px solid var(--rule)}
.ghead b{font:600 16px "Barlow Condensed",sans-serif;color:var(--mark);
  letter-spacing:.4px}
.ghead span{color:var(--dim);font-size:11.5px}
.gwhat{color:var(--muted);font-size:12px;margin:10px 0 12px}
.gasks{display:flex;flex-direction:column;gap:5px;margin-bottom:12px}
.gask{text-align:start;background:var(--sunk);color:var(--ink);
  border:1px solid var(--rule);border-radius:7px;padding:7px 10px;
  font:inherit;font-size:12.5px;cursor:pointer}
.gask:hover{border-color:var(--mark)}
.gask[aria-expanded="true"]{border-color:var(--mark);color:var(--mark)}
.gans p{font-size:12.5px;line-height:1.6;margin:0 0 8px}
.gcite{color:var(--dim);font-size:10.5px}
.gcite code{font-family:"IBM Plex Mono",monospace}
.gfoot{color:var(--dim);font-size:10.5px;margin:12px 0 0;
  padding-top:10px;border-top:1px solid var(--rule)}
@media(max-width:900px){
  .withguide{grid-template-columns:1fr}
  #guide{position:static}
  .hero .cname,.bar .dname,.bar .dcount,.strip .sname{font-size:13px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}
  html{scroll-behavior:auto}}
"""


def card(c):
    return (
        f'<a class="card{" lead" if c.get("lead") else ""}" href="{c["href"]}">'
        f'<span class="kicker">{esc(c["kicker"])}</span>'
        f'<b>{esc(c["title"])}</b>'
        f'<p>{esc(c["body"])}</p>'
        f'<p class="limit"><span class="limit-tag">What it does not claim</span>'
        f'{esc(c["limit"])}</p></a>')


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

BODY = f"""<body>
<header class="top"><div class="wrap">
  <div class="brandline">
    <h1>SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
    <span class="by">powered by AGI Corp</span>
  </div>
  <p class="tagline">A walkable training world for the skilled trades &mdash;
    {n(HALLS)} union halls across {n(CAMPUSES)} campuses, with
    {n(SEATS)} operable machine seats standing in the yard.</p>
  <p class="sub">Every surface, figure and lesson in this bundle traces to a
    registry you can read, and each carries the word for how it was come by.
    Nothing is fetched at run time; nothing is generated when you look at it.
    Where a thing is unverified, it says so &mdash; on the page, not in an
    appendix.</p>
  <div class="stats">
    {''.join(f'<div class="stat"><b>{v}</b><span>{esc(k)}</span></div>' for v, k in STATS)}
  </div>
  {hero_map()}
</div></header>
<div class="stripe"></div>
<div class="wrap">
<section>
  <h2>Every hall, by district</h2>
  <p class="lede">All {n(HALLS)} halls, banded into the {len(districts)}
    districts that organise them. Each tick is one hall; the colours are the
    same eight the campus map and the walkable world use.</p>
  {district_bar()}
</section>
<section>
  <h2>The yard</h2>
  <p class="lede">{n(SEATS)} operable training seats stand in the campus
    yard. Every one is a machine you sit in and drive, scored by a rubric
    you can read.</p>
  {seat_strip()}
</section>
<section id="seats">
  <h2>Every seat, and the way in</h2>
  <p class="lede">One link per seat, straight into the machine rather than
    into the front of the world. Each says what it asks of you and what it
    measures you against, because the rubric is the whole of the judgement:
    every axis below is computed from measured state, and nothing you say
    about a run can move it. {esc(SEAT_HONESTY)}</p>
  {seat_index()}
</section>
<section>
  <h2>Where to start</h2>
  <p class="lede">{n(len(CARDS))} surfaces, each built from the same
    registries. The walkable world is the one to open first.</p>
  <div class="withguide">
    <div class="grid">{''.join(card(c) for c in CARDS)}</div>
    {GUIDE_HTML}
  </div>
</section>
<section>
  <h2>How to read a claim here</h2>
  <p class="lede">Every record in this bundle carries one of five words for
    how it was come by. They are not decoration: a build refuses a record
    that claims the wrong one, and the suites check it.</p>
  <div class="prov">
    {''.join(f'<div class="pv"><b>{w}</b><span>{esc(d)}</span></div>' for w, d in PROV)}
  </div>
</section>
<section>
  <h2>What this is not</h2>
  <p class="lede">The limits, stated once, plainly.</p>
  <div class="prov">
    <div class="pv"><b>NOT CERTIFICATION</b><span>No seat here certifies
      anyone on any equipment. The simulators carry schematic physics and
      deterministic rubrics; passing one is practice, not a ticket.</span></div>
    <div class="pv"><b>NOT A UNION ROSTER</b><span>A taxonomy of skilled
      trades, not a roster of chartered locals. No real local is named and no
      real union's mark is drawn.</span></div>
    <div class="pv"><b>NOT SURVEYED</b><span>No site has been surveyed and no
      real building is depicted. A campus is composed from a place's own
      character, and the registry says so in each record.</span></div>
    <div class="pv"><b>NOT YET REVIEWED</b><span>Lesson content is unverified
      general practice, pending authoring by journey-level practitioners from
      the halls each seat names.</span></div>
  </div>
</section>
</div>
<footer><div class="wrap">
  <p>{esc(i18n_en['strings'].get('honesty.modules', ''))}</p>
  <p>Built from {n(FLOORS)} floor finishes, {n(WALLS)} wall finishes and
    {n(PATTERNS)} surface patterns over {n(GROUNDS)} ground recipes and
    {n(WEATHER)} weather states; {n(STATIONS)} training stations;
    {n(ADVISORS)} advisors and {n(CREWS)} crews of {n(CREW_ROLES)} roles;
    {n(LABEL_KINDS)} kinds of sign; a locker of {n(AV_ALL)} options across
    {n(AV_SECTIONS)} sections; {n(SITES)} real restoration sites, of which
    {n(WALKABLE)} are walkable. Every one of those figures is read from its
    own registry by the script that generated this page.</p>
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

_loose = _figures_in(BODY) - _DERIVED
assert not _loose, (
    'these figures appear in the front door\'s prose but were not read from a '
    'registry by this script: ' + ', '.join(str(x) for x in sorted(_loose)) +
    ' - read them, or the page will drift the way `400 options` did')

page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>SmartCiti.X : Trade Craft Academy</title>\n'
        '<meta name="description" content="A walkable training world for the '
        f'skilled trades: {HALLS} union halls, {CAMPUSES} campuses and {SEATS} '
        'operable machine seats, every figure read from its own registry.">\n'
        '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 '
        'viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%226%22 '
        'fill=%22%230C1113%22/%3E%3Cpath d=%22M7 21 L16 7 L25 21 Z%22 fill=%22none%22 '
        'stroke=%22%23E8A33D%22 stroke-width=%222.6%22 stroke-linejoin=%22round%22/%3E'
        '%3Cpath d=%22M11 21 h10%22 stroke=%22%2341C4D4%22 stroke-width=%222.6%22 '
        'stroke-linecap=%22round%22/%3E%3C/svg%3E">\n'
        '<!-- Self-hosted: nothing on this page is fetched from another '
        'origin at run time. See web/fetch_fonts.py. -->\n'
        '<link rel="stylesheet" href="web/vendor/fonts/fonts.css">\n'
        f'<style>{CSS}</style>\n</head>\n{BODY}\n</html>\n')

emit(ROOT / 'index.html', page,
     f'{len(CARDS)} cards | {HALLS} halls, {CAMPUSES} campuses, {SEATS} seats')
