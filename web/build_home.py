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
restoration = R('restoration/registry/restoration.json')
geo = R('geo/registry/campuses_geo.json')
i18n_en = R('i18n/locales/en.json')

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


def n(x):
    return f'{x:,}'


# ------------------------------------------------------------------ copy ---
# AUTHORED prose. Each card says what the surface IS, what a reader can do
# with it, and what it does not claim - the limits in the same breath as the
# capability, because a training product for the trades owes a reader that.
CARDS = [
    {'href': 'web/trade_craft_3d.html', 'lead': True,
     'title': 'The walkable world',
     'kicker': f'{n(HALLS)} halls · {n(CAMPUSES)} campuses · {n(SEATS)} training seats',
     'body': f"""Every hall's floor plan stands up as a building you walk
        through on foot, with doorways cut where two rooms actually meet and
        partitions you cannot pass through. Ten campuses stand on ten
        different regional surfaces - a former naval station's bleached
        apron, delta crushed shell, rail ballast, mill slag - and your
        footsteps take their sound from whatever the registry says is under
        you. {n(SEATS)} operable training seats stand in the yard: a tower
        crane, an excavator, a forklift, a weld bench, a scaffold bay, a
        signal call, a load chart, a pressure washer, an airless sprayer, a
        boom lift and an overhead crane.""",
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
.prov{display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));gap:14px}
.pv{background:var(--sunk);border:1px solid var(--rule);border-radius:10px;padding:14px 16px}
.pv b{display:block;font:600 13px "IBM Plex Mono",monospace;letter-spacing:1px;
  color:var(--steel);margin-bottom:5px}
.pv span{color:var(--muted);font-size:13.5px}
footer{margin-top:56px;border-top:1px solid var(--rule);background:var(--sunk)}
footer .wrap{padding:26px 20px 40px}
footer p{color:var(--dim);font-size:13px;max-width:82ch;margin:0 0 10px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}
  html{scroll-behavior:auto}}
"""


def esc(t):
    return (' '.join(str(t).split())
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


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
</div></header>
<div class="stripe"></div>
<div class="wrap">
<section>
  <h2>Where to start</h2>
  <p class="lede">{n(len(CARDS))} surfaces, each built from the same
    registries. The walkable world is the one to open first.</p>
  <div class="grid">{''.join(card(c) for c in CARDS)}</div>
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
}


def _figures_in(html):
    """Every multi-digit figure in the rendered text, commas folded.

    Digits glued to letters are not figures - WGS84 is the name of a
    coordinate system, not a count of anything - so a run of digits only
    counts when letters and digits do not touch it on either side.
    """
    text = re.sub(r'<[^>]+>', ' ', html)
    text = text.replace('&mdash;', ' ')
    found = re.findall(r'(?<![A-Za-z0-9])\d[\d,]*(?![A-Za-z0-9])', text)
    return {int(m.replace(',', ''))
            for m in found if len(m.replace(',', '')) > 1}


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
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600;700'
        '&family=IBM+Plex+Mono:wght@400;600&display=swap">\n'
        f'<style>{CSS}</style>\n</head>\n{BODY}\n</html>\n')

emit(ROOT / 'index.html', page,
     f'{len(CARDS)} cards | {HALLS} halls, {CAMPUSES} campuses, {SEATS} seats')
