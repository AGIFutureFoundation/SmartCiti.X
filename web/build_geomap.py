#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the geographic network map builder.

The geo registry's expanded GeoJSON (network.geojson) rendered as a real
WGS84 map with MapLibre GL (vendored, BSD-3) — the same engine family as
the Mapbox maps Locator.X ships. DELIBERATELY NO BASEMAP TILES: the style
draws only the registry's own features over a generated graticule, so
nothing appears on this map that geo/registry does not state. RECORDED
points and frames, DERIVED great-circle routes, every popup carrying its
provenance and source line.
"""
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402  head tags only
from sitenav import nav_html, labels as nav_labels, NAV_CSS, STYLE_JS  # noqa: E402
from groundtruth import GROUND_TRUTH_JS  # noqa: E402
from pagehero import theme  # noqa: E402  the enterprise theme layer, canvas mode (THEME_CONTRACT v1: no hero band here)
THEME_CSS, _THEME_JS = theme('canvas')
assert _THEME_JS == '', 'the canvas theme ships no script'

network = json.load(open(ROOT / 'geo/registry/network.geojson'))
parcels = json.load(open(ROOT / 'parcels/registry/parcels.json'))
geo = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))
manifest = json.load(open(ROOT / 'pack/manifest.json'))
roadmap = json.load(open(ROOT / 'roadmap/registry/roadmap.json'))
restoration = json.load(open(ROOT / 'restoration/registry/restoration.json'))
spatial = json.load(open(ROOT / 'spatial/registry/geopose.json'))
meta = json.load(open(ROOT / 'meta/registry/metaverse.json'))
# the registries the per-campus rollups are computed from - never typed
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))
halls_reg = json.load(open(ROOT / 'pack/registry/halls.json'))
lessons_reg = json.load(open(ROOT / 'lessons/registry/lessons.json'))
sims_reg = json.load(open(ROOT / 'sims/registry/sims.json'))
schools_reg = json.load(open(ROOT / 'schools/registry/schools.json'))
L = manifest['ledger']


def need(d, k, where):
    """Fail closed, by name: a registry field this page renders must exist.
    No default-taking get() call anywhere below - a missing field is a build
    failure that names the field and the registry, never a silent blank."""
    if not isinstance(d, dict) or k not in d:
        raise SystemExit(f'build_geomap: {where} has no field {k!r}')
    return d[k]


# ---------------------------------------------------------------- rollups ---
# Per-campus figures, computed here from the registries that own them and
# shipped inside the page's JSON only - the popup and the campus panel
# render them from D.rollups at view time, so no count is ever typed into
# the page's prose. (web/test_geomap.mjs recomputes every one and greps the
# page outside the JSON for the literal figures.)
HALL_SLUGS = {need(h, 'slug', 'pack/registry/halls.json#halls[]')
              for h in need(halls_reg, 'halls', 'pack/registry/halls.json')}
CAMPUSES = need(campuses_reg, 'campuses', 'unions/registry/campuses.json')
LESSONS = need(lessons_reg, 'lessons', 'lessons/registry/lessons.json')
HALL_BINDINGS = need(sims_reg, 'hall_bindings', 'sims/registry/sims.json')
UNITS = need(schools_reg, 'units', 'schools/registry/schools.json')
_halls_with_lesson = {need(l, 'hall', f'lessons.json#lessons.{lid}')
                      for lid, l in LESSONS.items()}
_flipped_halls = [need(u, 'hall', 'schools.json#units[]') for u in UNITS]
ROLLUPS = {}
for slug, c in CAMPUSES.items():
    halls = need(c, 'halls', f'unions/registry/campuses.json#campuses.{slug}')
    for h in halls:
        assert h in HALL_SLUGS, f'campus {slug} lists hall {h!r} that halls.json does not carry'
    # a hall may sit on exactly one campus, so a lesson's own campus tag
    # must agree with the campus that lists its hall - checked, not assumed
    for lid, l in LESSONS.items():
        if l['hall'] in halls:
            assert need(l, 'campus', f'lessons.json#lessons.{lid}') == slug, (
                f'lesson {lid} says campus {l["campus"]!r} but its hall {l["hall"]!r} is on {slug}')
    ROLLUPS[slug] = {
        'name': need(c, 'name', f'campuses.json#campuses.{slug}'),
        'flagship': need(c, 'flagship', f'campuses.json#campuses.{slug}'),
        'halls': list(halls),
        'hallsCount': len(halls),
        'hallsWithLesson': sum(1 for h in halls if h in _halls_with_lesson),
        'hallsBindingSeat': sum(1 for h in halls if h in HALL_BINDINGS),
        'flippedUnits': sum(1 for h in _flipped_halls if h in halls),
    }
_flagships = [s for s, r in ROLLUPS.items() if r['flagship'] is True]
assert len(_flagships) == 1, f'expected exactly one flagship campus, found {_flagships}'
FLAGSHIP = _flagships[0]
assert set(ROLLUPS) == {f['properties']['slug'] for f in network['features']
                        if 'slug' in f['properties']}, \
    'the campuses on network.geojson and unions/registry/campuses.json differ'

# ---------------------------------------------------- anchor provenance ---
# geo/registry/campuses_geo.json#anchors: every anchor carries `provenance`
# (RECORDED from the cited Locator.X table, or AUTHORED - typed from public
# record) and its own `source` string. Counted here from the registry, then
# cross-checked against the network features the map draws, so the legend's
# split and each popup's chip are the registry's own words - never upgraded,
# never invented. The two classes are styled apart on the map itself.
ANCHOR_PROVENANCE = {'RECORDED': 0, 'AUTHORED': 0, 'total': 0}
_anchor_by_ref = {}
for near, lst in need(geo, 'anchors', 'geo/registry/campuses_geo.json').items():
    for a in lst:
        pv = need(a, 'provenance', f'campuses_geo.json#anchors.{near}[]')
        need(a, 'source', f'campuses_geo.json#anchors.{near}[]')
        assert pv in ('RECORDED', 'AUTHORED'), f'anchor {a["name"]!r} near {near}: provenance {pv!r}'
        ANCHOR_PROVENANCE[pv] += 1
        ANCHOR_PROVENANCE['total'] += 1
        _anchor_by_ref[f'{near}/{a["name"]}'] = a
for f in network['features']:
    p = f['properties']
    if 'kind' in p and p['kind'] == 'anchor':
        a = _anchor_by_ref[f'{p["near"]}/{p["name"]}']
        assert p['provenance'] == a['provenance'] and p['source'] == a['source'], (
            f'network.geojson anchor {p["name"]!r} drifted from campuses_geo.json')
assert ANCHOR_PROVENANCE['total'] == sum(
    1 for f in network['features'] if 'kind' in f['properties'] and f['properties']['kind'] == 'anchor')

# ------------------------------------------------------- restoration walks ---
# The eight walkable sites link into the 3D environment at the campus their
# entry is grouped under (trade_craft_3d.html?campus=<slug> - the app's own
# entry point; the walk itself starts from that campus's restoration panel).
# A site with walkable=false gets its registry's own `walkable_reason`,
# verbatim, and NEVER a walk link - the refusal is the content.
for s in restoration['sites']:
    for k in ('id', 'name', 'walkable', 'walkable_reason', 'pin', 'source_url', 'campus'):
        need(s, k, f'restoration/registry/restoration.json#sites[{s["id"] if "id" in s else "?"}]')
    if s['walkable'] is True:
        assert s['pin'] is True and s['campus'] in ROLLUPS, \
            f'walkable site {s["id"]} has no pinned campus to walk from'
    else:
        assert isinstance(s['walkable_reason'], str) and s['walkable_reason'], \
            f'non-walkable site {s["id"]} carries no walkable_reason'
N_NOT_WALKABLE = sum(1 for s in restoration['sites'] if s['walkable'] is not True)
assert N_NOT_WALKABLE > 0


def walk_href(s):
    return f'trade_craft_3d.html?campus={s["campus"]}'


def _site_row(s):
    E = html.escape
    if s['walkable'] is True:
        walk = (f'<a class="walk" href="{E(walk_href(s))}">walk it in the 3D environment '
                f'(from the {E(ROLLUPS[s["campus"]]["name"])} restoration panel)</a>')
    else:
        walk = f'<span class="refusal">not walkable: {E(s["walkable_reason"])}</span>'
    return (f'<li data-site="{E(s["id"])}" data-walkable="{"true" if s["walkable"] is True else "false"}">'
            f'<b>{E(s["name"])}</b> <span class="pv">{E(s["category"])}</span><br>{walk}<br>'
            f'<a class="src" href="{E(s["source_url"])}" target="_blank" rel="noopener">{E(s["source_url"])}</a></li>')


SITE_ROWS = ''.join(_site_row(s) for s in restoration['sites'])


def _slug(s):
    """Mirrors spatial/build.py's slug() exactly — the same function, so an
    anchor's GeoPose ref can be recomputed here rather than re-shipped."""
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


# The spatial fabric's own poses, joined onto this map's own features by the
# same subject ref spatial/build.py minted them under — this is the one
# surface built to be a real WGS84 map, and it drew every campus, anchor and
# restoration marker without ever mentioning the pose registry that
# describes those exact points. campus:<slug> and restoration-site:<id> read
# straight off each feature; anchor:<campus>/<slug(name)> is recomputed with
# the identical slug() so it cannot drift from spatial/build.py's own.
POSE_BY_REF = {p['subject']['ref']: p for p in spatial['poses']}
_N_MATCHED = 0
for f in network['features']:
    p = f['properties']
    ref = (f'campus:{p["slug"]}' if 'slug' in p
           else f'anchor:{p["near"]}/{_slug(p["name"])}' if 'kind' in p and p['kind'] == 'anchor'
           else None)
    pose = POSE_BY_REF[ref] if ref in POSE_BY_REF else None
    if pose:
        p['geopose'] = {'ref': ref, 'h_m': pose['geopose']['position']['h'],
                         'position_provenance': pose['provenance']['position_horizontal']}
        _N_MATCHED += 1
assert _N_MATCHED == spatial['counts']['campuses'] + spatial['counts']['anchors'], (
    f'{_N_MATCHED} network features matched a GeoPose, expected '
    f'{spatial["counts"]["campuses"] + spatial["counts"]["anchors"]} (campuses + anchors)')

# claimed vs. not-claimed, read from meta/'s own registry rather than typed —
# the same split web/build_dashboard.py shows for the spatial fabric
_spatial_claimed = [s['id'] for s in meta['baseline']['standards'] if s['id'] == 'geopose-1.0']
_spatial_not = [x['id'] for x in meta['baseline']['not_claimed']
                if x['id'] in ('ombi-spatial-fabric', 'ombi-som', 'rmap')]

# ------------------------------------------------------------ the 3D globe ---
# geo3d/registry/geo3d.json: every hall of the 3D campus projected onto WGS84
# about its campus centroid (SCHEMATIC - north-up, no heading recorded). Drawn
# here as fill-extrusions coloured by district; each hall's lesson and task
# counts are computed below from the registries that own them.
geo3d = json.load(open(ROOT / 'geo3d/registry/geo3d.json'))
G3 = need(geo3d, 'campuses', 'geo3d/registry/geo3d.json')
assert set(G3) == set(ROLLUPS), 'geo3d/registry/geo3d.json and unions/registry/campuses.json list different campuses'
_lessons_per_hall = {}
for lid, l in LESSONS.items():
    _lessons_per_hall[l['hall']] = _lessons_per_hall[l['hall']] + 1 if l['hall'] in _lessons_per_hall else 1

# the simulated-task registry (TASKS, $SP/TASK_CONTRACT.md v1) - read through
# web/taskkit.py only. Tasks at a hall, a campus or a restoration site sit on
# their campus; a space with no campus, and every wilds-site task (an AUTHORED
# world, only inspired by a region), go to the "not on the globe" list.
TASKS_REG_PATH = ROOT / 'tasks/registry/tasks.json'
if TASKS_REG_PATH.exists():
    from taskkit import TASKS as _TASKS  # noqa: E402
    TASK_ROWS = []
    for t in need(_TASKS, 'tasks', 'tasks/registry/tasks.json'):
        pl = need(t, 'place', f'tasks.json#{t["id"]}')
        la = need(t, 'launch', f'tasks.json#{t["id"]}')
        href = need(la, 'href', f'tasks.json#{t["id"]}.launch')
        TASK_ROWS.append({
            'id': t['id'], 'title': need(t, 'title', f'tasks.json#{t["id"]}'),
            'kind': need(t, 'kind', f'tasks.json#{t["id"]}'),
            'place': {'kind': need(pl, 'kind', f'tasks.json#{t["id"]}.place'),
                      'id': need(pl, 'id', f'tasks.json#{t["id"]}.place'),
                      'campus': need(pl, 'campus', f'tasks.json#{t["id"]}.place')},
            # repo-root-relative in the registry; this page lives in web/
            'href': (href[4:] if href.startswith('web/') else '../' + href) if href is not None else None,
            'why': None if href is not None else need(la, 'why', f'tasks.json#{t["id"]}.launch'),
            'provenance': need(t, 'provenance', f'tasks.json#{t["id"]}'),
        })
    TASKS_STATE = {'state': 'built', 'honesty': need(need(_TASKS, 'honesty', 'tasks.json'), 'practice', 'tasks.json#honesty'),
                   'source_stamp': need(_TASKS, 'source_stamp', 'tasks.json')}
else:
    # an explicit, named state - the page says the registry is not built,
    # it never shows zero tasks as if that were a count
    TASK_ROWS = []
    TASKS_STATE = {'state': 'absent', 'honesty': None, 'source_stamp': None}
_ON_GLOBE_TASK_PLACES = ('hall', 'campus', 'restoration-site')


def _task_on_globe(t):
    return t['place']['kind'] in _ON_GLOBE_TASK_PLACES and t['place']['campus'] in ROLLUPS


_tasks_per_hall = {}
for t in TASK_ROWS:
    if t['place']['kind'] == 'hall':
        _tasks_per_hall[t['place']['id']] = _tasks_per_hall[t['place']['id']] + 1 if t['place']['id'] in _tasks_per_hall else 1

HALLS3D = {'type': 'FeatureCollection', 'features': []}
DISTRICTS3D = {'type': 'FeatureCollection', 'features': []}
CAMERA = {}
for slug, c in G3.items():
    cen = need(c, 'centroid', f'geo3d.json#campuses.{slug}')
    CAMERA[slug] = {'lng': need(cen, 'lng', f'geo3d {slug}.centroid'), 'lat': need(cen, 'lat', f'geo3d {slug}.centroid'),
                    'halls': len(need(c, 'halls', f'geo3d {slug}'))}
    dnames = {}
    for d in need(c, 'districts', f'geo3d {slug}'):
        dnames[d['key']] = d['name']
        DISTRICTS3D['features'].append({'type': 'Feature', 'properties': {
            'campus': slug, 'district': d['key'], 'name': d['name'],
            'color': f'hsl({d["hue"]}, 50%, 45%)'},
            'geometry': {'type': 'Polygon', 'coordinates': [d['polygon']]}})
    hue_of = {d['key']: d['hue'] for d in c['districts']}
    for h in c['halls']:
        HALLS3D['features'].append({'type': 'Feature', 'properties': {
            'slug': h['slug'], 'name': h['name'], 'campus': slug, 'district': h['district'],
            'districtName': dnames[h['district']], 'h': h['h'], 'top': h['top'], 'roof': h['roof'],
            'color': f'hsl({hue_of[h["district"]]}, 50%, 45%)',
            'lessons': _lessons_per_hall[h['slug']] if h['slug'] in _lessons_per_hall else 0,
            'tasks': _tasks_per_hall[h['slug']] if h['slug'] in _tasks_per_hall else 0},
            'geometry': {'type': 'Polygon', 'coordinates': [h['polygon']]}})
assert len(HALLS3D['features']) == need(need(geo3d, 'counts', 'geo3d.json'), 'halls', 'geo3d.json#counts')

# ------------------------------------------------------------ style paint
# The map's own paint follows the reader's Style (nav menu, 5 styles): each
# paint ROLE names one --tc-* token, read off the page at load and whenever
# html[data-style] changes. The table below is the whole mapping; the pairs
# are the contrasts each style is held to, MEASURED here for every style
# (and the canvas default) from design_kit, and again by web/test_geomap.mjs
# from the CSS the page ships. RECORDED vs AUTHORED anchors and the SCHEMATIC
# hall outline must stay distinguishable in every style.
import design_kit as _K  # noqa: E402
PAINT_ROLES = {'bg': 'plate', 'grat': 'line', 'horizon': 'raised', 'frame': 'steel', 'route': 'amber',
               'recorded': 'steel', 'authored': 'plate', 'ring': 'steel', 'campus': 'amber',
               'label': 'amber-ink', 'labelPill': 'amber', 'selectedPill': 'ink', 'hallEdge': 'ink',
               'restText': 'plate', 'restPill': 'ok', 'monitorPill': 'steel'}
PAINT_PAIRS = [  # (fg role, bg role, minimum, what)
    ('label', 'labelPill', 4.5, 'campus label text on its pill'),
    ('label', 'selectedPill', 4.5, 'selected campus label text on its pill'),
    ('labelPill', 'bg', 3.0, 'campus label pill (halo) on the map background'),
    ('campus', 'bg', 3.0, 'campus dot on the map background'),
    ('recorded', 'bg', 3.0, 'RECORDED anchor fill on the map background'),
    ('ring', 'bg', 3.0, 'AUTHORED anchor ring on the map background'),
    ('recorded', 'authored', 3.0, 'RECORDED fill vs AUTHORED hollow fill'),
    ('hallEdge', 'bg', 4.5, 'SCHEMATIC hall outline on the map background'),
    ('restText', 'restPill', 4.5, 'restoration label and cluster count on their pill'),
    ('restText', 'monitorPill', 4.5, 'monitoring-site label on its pill'),
    ('route', 'bg', 3.0, 'DERIVED route on the map background'),
    ('frame', 'bg', 3.0, 'city frame on the map background'),
]
assert PAINT_ROLES['recorded'] != PAINT_ROLES['authored'], 'geomap paint: RECORDED and AUTHORED share a token'
_PAL = _K.TOKENS['palette']['dark']
_STYLE_TOKENS = {'default': {k: _PAL[k] for k in ('plate', 'raised', 'line', 'ink', 'amber', 'amber-ink', 'steel', 'ok')}}
for _s in _K.STYLES:
    _t = _s['tokens']
    _STYLE_TOKENS[_s['id']] = {'plate': _t['plate'], 'raised': _t['raised'], 'line': _t['line'], 'ink': _t['ink'],
                               'amber': _t['accent'], 'amber-ink': _t['accent-ink'], 'steel': _t['link'], 'ok': _t['ok']}
STYLE_PAINT = {'roles': PAINT_ROLES, 'pairs': [list(x) for x in PAINT_PAIRS], 'styles': {}}
for _id, _tk in _STYLE_TOKENS.items():
    _ratios = {}
    for _fg, _bg, _min, _what in PAINT_PAIRS:
        _r = round(_K.contrast(_tk[PAINT_ROLES[_fg]], _tk[PAINT_ROLES[_bg]]), 2)
        if _r < _min:
            raise ValueError(f'geomap paint: style {_id!r} {_what} measures {_r} < {_min}')
        _ratios[f'{_fg}/{_bg}'] = _r
    STYLE_PAINT['styles'][_id] = {'tokens': _tk, 'ratios': _ratios}

# ------------------------------------------------ environments on the globe ---
# worksites: a worksite stands where its place stands, and only there - a
# campus place at the campus's own centroid, a restoration site at that
# site's own pinned coordinate. A space-placed worksite carries campus null
# in worksites/registry (a custom space is a room design, not a place on a
# campus), so it is listed as not on the globe - never given a coordinate.
worksites_reg = json.load(open(ROOT / 'worksites/registry/worksites.json'))
_rest_by_id = {s['id']: s for s in restoration['sites']}
WORKSITES_ON, WORKSITES_OFF = [], []
for w in need(worksites_reg, 'sites', 'worksites/registry/worksites.json'):
    pl = need(w, 'place', f'worksites.json#{w["id"]}')
    kind, pid, camp = need(pl, 'kind', f'worksites {w["id"]}.place'), need(pl, 'id', f'worksites {w["id"]}.place'), need(pl, 'campus', f'worksites {w["id"]}.place')
    row = {'id': w['id'], 'title': need(w, 'title', f'worksites {w["id"]}'), 'place': need(pl, 'name', f'worksites {w["id"]}.place'),
           'placeKind': kind, 'campus': camp, 'href': 'trade_craft_worksites.html#site-' + w['id']}
    if kind == 'campus':
        assert pid in geo['campuses'], f'worksite {w["id"]} names campus {pid!r} that campuses_geo.json does not place'
        row['lngLat'] = [geo['campuses'][pid]['lng'], geo['campuses'][pid]['lat']]
        row['at'] = 'campus centroid (' + geo['campuses'][pid]['provenance'] + ')'
        WORKSITES_ON.append(row)
    elif kind == 'restoration-site':
        rs = _rest_by_id[pid]
        assert rs['pin'] is True, f'worksite {w["id"]} stands at restoration site {pid} that has no pinned coordinate'
        row['lngLat'] = [rs['lng'], rs['lat']]
        row['at'] = 'restoration site coordinate (AUTHORED)'
        WORKSITES_ON.append(row)
    elif kind == 'space':
        assert camp is None or camp in ROLLUPS, f'worksite {w["id"]}: space campus {camp!r}'
        if camp is None:
            row['why'] = 'a custom space with no campus in worksites/registry - a room design, not a place'
            WORKSITES_OFF.append(row)
        else:
            row['lngLat'] = [geo['campuses'][camp]['lng'], geo['campuses'][camp]['lat']]
            row['at'] = 'its campus centroid'
            WORKSITES_ON.append(row)
    else:
        raise SystemExit(f'build_geomap: worksite {w["id"]} has place kind {kind!r} this map cannot place')

# K-12: name-only, PROPOSED partners, shown AT their campus's point (never at
# an address - none is recorded), in the schools registry's own words
K12 = []
for d in need(schools_reg, 'districts', 'schools/registry/schools.json'):
    camp = need(d, 'campus', 'schools.json#districts[]')
    assert camp in ROLLUPS, f'K-12 district {d["district"]!r} names campus {camp!r}'
    K12.append({'district': need(d, 'district', 'schools.json#districts[]'), 'campus': camp,
                'city': need(d, 'city', 'schools.json#districts[]'),
                'provenance': need(d, 'provenance', 'schools.json#districts[]'),
                'status': need(d, 'status', 'schools.json#districts[]'),
                'lngLat': [geo['campuses'][camp]['lng'], geo['campuses'][camp]['lat']]})

# the wilds: AUTHORED landscapes, each only INSPIRED by a campus region -
# listed, linked, never placed
wilds_reg = json.load(open(ROOT / 'wilds/registry/wilds.json'))
WILDS_OFF = []
for wd in need(wilds_reg, 'worlds', 'wilds/registry/wilds.json'):
    ins = need(wd, 'inspiration', f'wilds.json#{wd["id"]}')
    WILDS_OFF.append({'id': wd['id'], 'name': need(wd, 'name', f'wilds.json#{wd["id"]}'),
                      'evokes': need(ins, 'evokes', f'wilds.json#{wd["id"]}.inspiration'),
                      'campus': need(ins, 'campus', f'wilds.json#{wd["id"]}.inspiration'),
                      'standing': need(ins, 'standing', f'wilds.json#{wd["id"]}.inspiration'),
                      'provenance': need(wd, 'provenance', f'wilds.json#{wd["id"]}'),
                      'href': 'trade_craft_wilds.html#' + wd['id']})
WILDS_HONESTY = need(need(wilds_reg, 'honesty', 'wilds.json'), 'landscape', 'wilds.json#honesty')

TASKS_ON = [t for t in TASK_ROWS if _task_on_globe(t)]
TASKS_OFF = [t for t in TASK_ROWS if not _task_on_globe(t)]
# the tour visits every campus in unions/registry/campuses.json order
TOUR = list(ROLLUPS)

DATA = json.dumps({
    'network': network,
    'city': geo['city'],
    'honesty': geo['honesty'],
    'halls': L['halls'],
    'imagery': parcels['imagery'],
    'sources': parcels['sources'],
    'contract': parcels['contract'],
    'recHonesty': parcels['honesty'],
    # only what the markers' lookup buttons actually render — the endpoint,
    # the query template and the one line of scope text — same trim
    # web/build_3d.py applies to the same registry entry
    'elevation': {k: parcels['elevation'][k] for k in
                  ('endpoint', 'query', 'scope')},
    # whatever roadmap candidates remain: real AUTHORED coordinates, the
    # same tier a Wikipedia infobox carries - this map is the one place
    # they can be shown at their own true position rather than a
    # schematic bearing, since every other feature here is already
    # lat/lng. With Detroit's promotion the dict is empty and the ten-
    # campus target is fully met, so nothing renders here - by design,
    # not by omission.
    'candidates': {k: {'name': c['name'], 'city': c['city'],
                       'region': c['region'], 'lat': c['lat'], 'lng': c['lng'],
                       'districts': c['districts'], 'why': c['why']}
                   for k, c in roadmap['candidates'].items()},
    'roadmapHonesty': {k: roadmap['honesty'][k]
                       for k in ('not_a_claim_of_content', 'provenance_tiers')},
    # real Bay Restoration Authority sites - AUTHORED coordinates (this
    # build reaches no network host, so nothing here is cross-checked
    # against sfbayrestore.org live), each with its own source link
    # every site, verbatim - the unpinned one too, since its refusal to be
    # pinned (walkable_reason) is content this map now shows; the marker
    # loop below still draws only the pinned ones (s.pin)
    'restorationSites': restoration['sites'],
    'nNotWalkable': N_NOT_WALKABLE,
    # the geo registry's own anchor table, verbatim, and its provenance
    # split counted from it (see ANCHOR_PROVENANCE above)
    'anchors': geo['anchors'],
    'anchorProvenance': ANCHOR_PROVENANCE,
    # per-campus rollups computed from unions/, pack/, lessons/, sims/ and
    # schools/ registries (see ROLLUPS above) - rendered from here only
    'rollups': ROLLUPS,
    'stylePaint': STYLE_PAINT,
    'flagship': FLAGSHIP,
    'restorationHonesty': {k: restoration['honesty'][k]
                           for k in ('not_affiliated', 'provenance')},
    # the spatial fabric this map's own features are described by
    # (spatial/registry/geopose.json) — every campus and anchor feature
    # above already carries its own `geopose` property; restoration-site
    # poses are looked up client-side by ref, since the pin filter above
    # already trims restorationSites to the ones a pose could exist for.
    # the 3D globe (geo3d/) and the environments layer - see above
    'geo3d': {'halls': HALLS3D, 'districts': DISTRICTS3D, 'camera': CAMERA, 'tour': TOUR,
              'placement': need(geo3d, 'placement', 'geo3d.json'), 'projection': need(geo3d, 'projection', 'geo3d.json'),
              'counts': need(geo3d, 'counts', 'geo3d.json'),
              'noHalls': {k: need(c, 'note', f'geo3d {k}') for k, c in G3.items() if not c['halls']},
              'sourceStamp': need(geo3d, 'source_stamp', 'geo3d.json')},
    'env': {'worksitesOn': WORKSITES_ON, 'worksitesOff': WORKSITES_OFF, 'k12': K12,
            'wildsOff': WILDS_OFF, 'wildsHonesty': WILDS_HONESTY,
            'tasks': {'state': TASKS_STATE, 'on': TASKS_ON, 'off': TASKS_OFF}},
    'geopose': {
        'counts': spatial['counts'],
        'encoding': spatial['encoding'], 'mediaType': spatial['media_type'],
        'crs': spatial['crs'],
        'claimedCount': len(_spatial_claimed), 'notClaimedCount': len(_spatial_not),
        'honesty': {k: spatial['honesty'][k] for k in
                    ('geopose_claimed', 'no_heights_or_headings', 'ombi_not_claimed')},
        'byRef': {p['subject']['ref']: {
            'h_m': p['geopose']['position']['h'],
            'position_provenance': p['provenance']['position_horizontal']}
            for p in spatial['poses'] if p['subject']['kind'] == 'restoration-site'},
    },
}, ensure_ascii=False, separators=(',', ':'))

NAV = nav_html('web/trade_craft_geomap.html', nav_labels('en'))
from questkit import QUEST_CSS, quest_js, page_hooks  # noqa: E402  quests: egg hooks only
QUEST_TAIL = '<style>' + QUEST_CSS + '</style>\n' + page_hooks('web/trade_craft_geomap.html') + quest_js('page:web/trade_craft_geomap.html')

page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>SmartCiti.X : Trade Craft Academy — network geomap</title>
<link rel="stylesheet" href="vendor/maplibre/maplibre-gl.css">
<style>
:root{
  --plate:#12181B; --panel:#182023; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --steel:#41C4D4; --good:#5CB584;
}
*{box-sizing:border-box}
html,body{height:100%}
/* the site nav sits in flow above the map; #stage holds everything the
   map page positions, and its transform makes it the containing block
   for the bar, panels and legend, so they anchor below the nav */
body{display:flex;flex-direction:column}
#stage{position:relative;flex:1 1 auto;min-height:0;transform:translateZ(0);
  display:flex;flex-direction:column}
/* the bar sits in flow above the map, so nothing the map draws (its zoom
   control, a panel, the legend) can hide underneath it at any width */
#mapwrap{position:relative;flex:1 1 auto;min-height:0}
body{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.5 "IBM Plex Sans",system-ui,sans-serif;overflow:hidden}
#bar{position:relative;z-index:5;display:flex;flex-wrap:wrap;
  gap:8px 14px;align-items:center;padding:10px 16px;
  background:color-mix(in oklab, var(--plate) 88%, transparent);
  border-bottom:2px solid var(--mark);backdrop-filter:blur(6px)}
#bar .brand{margin:0;font:700 19px/1 "Barlow Condensed",system-ui,sans-serif;white-space:nowrap}
#bar .brand .x{color:var(--mark)}
#bar a{color:var(--steel);text-decoration:none;font-size:13px}
.barbtn{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:6px 11px;font:inherit;cursor:pointer;white-space:nowrap}
.barbtn:hover{border-color:var(--mark)}
.barbtn[aria-pressed="true"]{border-color:var(--mark);color:var(--mark)}
#bar .tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
#find{background:var(--plate);color:var(--ink);border:1px solid var(--rule);border-radius:6px;
  padding:6px 10px;font:inherit;min-height:32px;width:min(260px,100%)}
#find:focus{border-color:var(--mark)}
:focus-visible{outline:2px solid var(--mark);outline-offset:2px}
#map{position:absolute;inset:0}
#honesty{position:absolute;right:14px;bottom:12px;z-index:5;max-width:min(340px,calc(100% - 190px));
  color:var(--muted);font-size:10.5px;text-align:end;opacity:.9;
  pointer-events:none}
#legend{position:absolute;left:14px;bottom:12px;z-index:5;
  max-width:min(430px,calc(100% - 28px));max-height:calc(100% - 96px);overflow:auto;
  background:color-mix(in oklab, var(--panel) 90%, transparent);
  border:1px solid var(--rule);border-radius:9px;padding:9px 13px;
  font-size:12px;color:var(--muted)}
#legend b{color:var(--ink)}
#legend summary{cursor:pointer;min-height:24px;list-style-position:inside}
#legend .lg-hint{color:var(--muted);font-size:11px}
#legend:not([open]){max-width:min(360px,calc(100% - 28px))}
#legend .lg-row{margin:3px 0;padding-inline-start:15px;text-indent:-15px}
#legend .lg-row > :first-child{text-indent:0}
.sw-cluster{display:inline-block;min-width:18px;height:14px;border-radius:999px;background:var(--good);
  color:var(--plate);font:700 9.5px/14px "IBM Plex Sans",sans-serif;text-align:center;margin-inline-end:5px;
  text-indent:0}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-inline-end:5px}
.campus-marker{background:var(--mark);color:var(--mark-ink);border-radius:999px;
  padding:2px 9px;font:600 12px "Barlow Condensed",sans-serif;white-space:nowrap;
  border:1.5px solid var(--plate);cursor:pointer;z-index:3;min-height:24px;line-height:18px}
.campus-marker.compact{font-size:0;padding:2px 6px;min-width:24px}
.campus-marker.compact::after{content:attr(data-short);font-size:11px}
.campus-marker:hover{box-shadow:0 0 0 2px var(--plate),0 0 0 4px var(--mark)}
.campus-marker.is-selected{background:var(--ink);box-shadow:0 0 0 2px var(--plate),0 0 0 4px var(--mark);z-index:4}
.candidate-marker{background:transparent;color:var(--muted);border-radius:999px;
  padding:1px 8px;font:600 11px "Barlow Condensed",sans-serif;white-space:nowrap;
  border:1.5px dashed var(--muted);cursor:pointer}
/* a restoration site is a dot on its own point (a 24px target around a 12px
   dot); its name shows when the declutter pass finds room for it, and always
   on hover or keyboard focus. Sites closer than a target's width at the
   current zoom fold into one counted cluster that zooms in on click. */
.restoration-marker{background:none;border:0;padding:0;width:24px;height:24px;
  display:grid;place-items:center;cursor:pointer;z-index:2;color:var(--plate);
  font:600 12px "Barlow Condensed",sans-serif}
.restoration-marker .rm-dot{width:12px;height:12px;border-radius:50%;background:var(--good);
  border:1.5px solid var(--plate);box-shadow:0 0 0 1px var(--good)}
.restoration-marker.env-monitoring .rm-dot{background:var(--steel);box-shadow:0 0 0 1px var(--steel)}
.restoration-marker .rm-label{position:absolute;top:22px;left:50%;transform:translateX(-50%);
  display:none;background:var(--good);border:1.5px solid var(--plate);border-radius:999px;
  padding:1px 8px;white-space:nowrap}
.restoration-marker.env-monitoring .rm-label{background:var(--steel)}
.restoration-marker.show-label .rm-label,.restoration-marker:hover .rm-label,
.restoration-marker:focus-visible .rm-label{display:block}
.restoration-marker:hover,.restoration-marker:focus-visible{z-index:5}
.restoration-marker.is-selected .rm-dot{box-shadow:0 0 0 3px var(--ink)}
.restoration-marker.folded{display:none}
.rest-cluster{min-width:26px;height:26px;border-radius:999px;background:var(--good);color:var(--plate);
  border:1.5px solid var(--plate);box-shadow:0 0 0 3px color-mix(in oklab, var(--good) 35%, transparent);
  font:700 12px "IBM Plex Sans",sans-serif;cursor:pointer;padding:0 7px;z-index:2}
.rest-cluster:hover{box-shadow:0 0 0 4px var(--good)}
.maplibregl-popup-close-button{min-width:24px;min-height:24px;color:var(--ink);font-size:18px}
.maplibregl-ctrl-group button{width:32px;height:32px}
/* a marker on the far side of the globe: MapLibre tags it covered; it must
   neither show through the Earth nor take a click or a Tab stop */
.maplibregl-marker.maplibregl-marker-covered{visibility:hidden;pointer-events:none}
.maplibregl-popup-content{background:var(--panel)!important;color:var(--ink)!important;
  border:1px solid var(--rule);border-radius:9px;font:12.5px/1.45 "IBM Plex Sans",sans-serif;
  padding:10px 13px!important;max-width:270px}
.maplibregl-popup-tip{border-top-color:var(--panel)!important;
  border-bottom-color:var(--panel)!important}
.pv{display:inline-block;border:1px solid var(--rule);border-radius:999px;
  padding:0 7px;font-size:10.5px;color:var(--muted);margin:2px 4px 4px 0}
.pv.rec{color:var(--good);border-color:var(--good)}
.pv.auth{color:var(--mark);border-color:var(--mark)}
.src{color:var(--muted);font-size:10.5px}
.roll{margin:4px 0 0;padding:0;list-style:none;font-size:11.5px;color:var(--muted)}
.roll b{color:var(--ink)}
.panel{position:absolute;top:12px;right:14px;z-index:6;width:min(380px,calc(100vw - 28px));
  max-height:calc(100% - 130px);overflow:auto;display:none;
  background:color-mix(in oklab, var(--panel) 94%, transparent);
  border:1px solid var(--rule);border-radius:9px;padding:10px 14px;font-size:12.5px}
.panel.open{display:block}
.panel h2{font:600 15px "Barlow Condensed",sans-serif;margin:0 0 6px}
.panel ul{margin:0;padding:0;list-style:none}
.panel li{padding:7px 0;border-top:1px solid var(--rule)}
.panel li:first-child{border-top:0}
.panel a{color:var(--steel)}
.panel .walk{color:var(--good)}
.refusal{color:var(--mark);font-size:11.5px}
.flag{background:var(--mark);color:var(--mark-ink);border-radius:4px;padding:0 5px;
  font:600 10.5px "Barlow Condensed",sans-serif;margin-inline-start:4px}
.anchor-swatch{display:inline-block;width:9px;height:9px;border-radius:50%;margin-inline-end:5px}
.anchor-swatch.rec{background:var(--steel)}
.anchor-swatch.auth{background:var(--plate);border:1.5px solid var(--steel)}
.flysel{background:var(--panel);color:var(--ink);border:1px solid var(--rule);border-radius:6px;
  padding:6px 8px;font:inherit;min-height:32px;cursor:pointer}
.panel h3{font:600 13px "Barlow Condensed",sans-serif;margin:10px 0 4px;color:var(--ink);letter-spacing:.02em}
.panel label{display:flex;gap:8px;align-items:center;min-height:28px;cursor:pointer}
.panel .lyr input{width:18px;height:18px;accent-color:var(--mark)}
.panel .sw{display:inline-block;width:12px;height:12px;border-radius:3px;flex:none}
.pv.sch{color:var(--steel);border-color:var(--steel)}
.pv.prop{color:var(--mark);border-color:var(--mark);border-style:dashed}
.door{display:inline-block;margin:4px 6px 0 0;color:var(--steel)}
.door.walk3d{color:var(--good)}
.popbtn{font:inherit;font-size:11px;padding:2px 9px;margin-top:5px;background:none;color:var(--ink);
  border:1px solid var(--mark);border-radius:999px;cursor:pointer}
.tasklist{margin:4px 0 0;padding:0;list-style:none;max-height:180px;overflow:auto}
.tasklist li{padding:3px 0;border-top:1px solid var(--rule);font-size:11.5px}
.hide-campus .campus-marker{display:none}
.hide-rest .restoration-marker,.hide-rest .rest-cluster{display:none}
#tourBtn[aria-pressed="true"]{background:var(--mark);color:var(--plate)}
@media(pointer:coarse){.barbtn{min-height:42px}#honesty{display:none}}
@media(max-width:700px){
  #bar{padding:8px 12px;gap:6px 10px}
  #bar .brand{font-size:17px}
  #bar .tools{flex-wrap:nowrap;overflow-x:auto;width:100%;padding-bottom:2px}
  #find{flex:0 0 190px}
  .campus-marker{font-size:11px;padding:2px 7px}
  #honesty{left:14px;right:14px;max-width:none;bottom:54px;font-size:10px}
}
</style>
<style>__SITENAV_CSS__</style>
<style>__THEME_CSS__
/* the page's own tokens follow the site theme: whatever style the reader
   picks sets the --tc-* palette, and every panel, button and chip here is
   coloured through these names only */
body.tc-theme-canvas{--plate:var(--tc-plate);--panel:var(--tc-panel);--ink:var(--tc-ink);--muted:var(--tc-muted);
  --rule:var(--tc-line);--mark:var(--tc-amber);--mark-ink:var(--tc-amber-ink);--steel:var(--tc-steel);--good:var(--tc-ok)}
/* the theme's panel and button styling, kept compact for a full-screen map bar */
body.tc-theme-canvas #bar .tc-btn{min-block-size:32px;padding:6px 11px;font-size:13.5px;border-radius:8px}
body.tc-theme-canvas .barbtn[aria-pressed="true"]{border-color:var(--mark);color:var(--mark)}
body.tc-theme-canvas .panel.tc-panel,body.tc-theme-canvas #legend.tc-panel{border-radius:12px}
@media(pointer:coarse){body.tc-theme-canvas #bar .tc-btn{min-block-size:42px}}
</style>
</head>
<body class="tc-theme-canvas">
__SITENAV__<div id="stage">
<div id="bar">
  <h1 class="brand">SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
  <a href="trade_craft_3d.html">⬡ 3D environment</a>
  <a href="trade_craft_interactive.html">▦ interactive map</a>
  <div class="tools">
  <input id="find" type="search" list="findList" autocomplete="off"
    placeholder="Find a campus or site" aria-label="Find a campus or restoration site and open it on the map">
  <datalist id="findList"></datalist>
  <button class="barbtn tc-btn tc-btn-ghost" id="projBtn" aria-pressed="true" title="Switch between the globe and a flat (Web Mercator) map">🌐 Globe view</button>
  <button class="barbtn tc-btn tc-btn-ghost" data-fit="network" title="Reset the view to the whole network">⌂ Network</button>
  <button class="barbtn tc-btn tc-btn-ghost" data-fit="bay">Bay Area</button>
  <button class="barbtn tc-btn tc-btn-ghost" data-fit="nola">New Orleans</button>
  <button class="barbtn tc-btn tc-btn-ghost" id="satBtn" aria-pressed="false">🛰️ Imagery</button>
  <button class="barbtn tc-btn tc-btn-ghost" id="parBtn">▦ Footprints</button>
  <button class="barbtn tc-btn tc-btn-ghost" data-panel="campuses" aria-pressed="false" aria-controls="campuses">☰ Campuses</button>
  <button class="barbtn tc-btn tc-btn-ghost" data-panel="sites" aria-pressed="false" aria-controls="sites">🌿 Restoration sites</button>
  <button class="barbtn tc-btn tc-btn-ghost" data-panel="layers" aria-pressed="false" aria-controls="layers">⛶ Layers &amp; environments</button>
  <select class="flysel" id="flySel" aria-label="Fly the camera to a campus, pitched, with its 3D halls"><option value="">🎥 Fly to a campus…</option></select>
  <button class="barbtn tc-btn tc-btn-ghost" id="tourBtn" aria-pressed="false" title="Visit every campus in turn; press again or Escape to stop">▶ Tour</button>
  </div>
</div>
<div id="mapwrap">
<div id="map"></div>
<section class="panel tc-panel" id="campuses" aria-label="campus rollups">
  <h2>The campuses, rolled up from the registries</h2>
  <ul id="campusList"></ul>
  <p class="src">Halls per campus from unions/registry/campuses.json; a hall &ldquo;with a lesson&rdquo; has an entry in lessons/registry/lessons.json; a hall &ldquo;binding a seat&rdquo; appears in sims/registry/sims.json hall_bindings; flipped-classroom units are schools/registry/schools.json units on that campus&rsquo;s halls. Every figure is computed at build from those registries and rendered here from the page&rsquo;s own JSON.</p>
</section>
<section class="panel tc-panel" id="sites" aria-label="Bay Restoration sites">
  <h2>Bay Restoration sites</h2>
  <ul id="siteList">__SITE_ROWS__</ul>
  <p class="src">__RESTORATION_NOT_AFFILIATED__</p>
</section>
<section class="panel tc-panel" id="layers" aria-label="Layers and environments">
  <h2>Layers &amp; environments</h2>
  <div class="lyr" id="layerToggles"></div>
  <p class="src" id="g3dPlacement"></p>
  <h3>Simulated tasks, by place</h3>
  <p class="src" id="tasksHonesty"></p>
  <ul id="taskCampusList"></ul>
  <h3>Not on the globe</h3>
  <p class="src" id="wildsHonesty"></p>
  <ul id="offGlobe"></ul>
</section>
<details id="legend" class="tc-panel">
  <summary><b>Legend: the geo registry, drawn</b> <span class="lg-hint">what is RECORDED, DERIVED, AUTHORED, SCHEMATIC</span></summary>
  <div class="lg-row"><span class="dot" style="background:var(--mark)"></span>campus — RECORDED/DERIVED for the __N_FLAGSHIP__ flagship campuses, AUTHORED for the __N_HUB__ hub campuses</div>
  <div class="lg-row"><span class="anchor-swatch rec"></span>anchor, <b>RECORDED</b> — <span data-anchor-count="RECORDED"></span> of <span data-anchor-count="total"></span>: the coordinate is copied from the source its popup cites</div>
  <div class="lg-row"><span class="anchor-swatch auth"></span>anchor, <b>AUTHORED</b> — <span data-anchor-count="AUTHORED"></span> of <span data-anchor-count="total"></span>: typed from public record, no source fetched; the popup states this plainly</div>
  <div class="lg-row"><span class="dot" style="background:none;border:1.5px dashed var(--mark);border-radius:0"></span>great-circle route — DERIVED</div>
  <div class="lg-row"><span class="dot" style="background:none;border:1px solid var(--steel);border-radius:0"></span>city frame — RECORDED for the __N_FLAGSHIP__ flagship campuses, AUTHORED for the __N_HUB__ hub campuses</div>
  <div class="lg-row"><span class="dot" style="background:none;border:1.5px dashed var(--muted)"></span>roadmap candidate — AUTHORED, not built</div>
  <div class="lg-row"><span class="dot" style="background:hsl(210,50%,45%);border-radius:2px"></span>3D hall, coloured by district — <b>SCHEMATIC</b>: the 3D campus stood up north-up about its centroid; <span id="g3dCount"></span></div>
  <div class="lg-row"><span class="dot" style="background:#C98BE0"></span>worksite · <span class="dot" style="background:#F2D16B"></span>K-12 district, <b>PROPOSED</b>, shown at its campus · <span class="dot" style="background:#5CB584;border:2px solid #0C1113"></span>simulated tasks at a campus — open ⛶ Layers for lists</div>
  <div class="lg-row"><span class="dot" style="background:var(--good)"></span>Bay Restoration site (habitat-restoration) — real project, not affiliated with this bundle</div>
  <div class="lg-row"><span class="dot" style="background:var(--steel)"></span>Bay Restoration site (environmental-monitoring) — a real federal cleanup site (Hunters Point, NPL-listed and litigated; Treasure Island NSTI, a Navy BRAC cleanup, not NPL-listed); located but never rendered as a walkable scene</div>
  <div class="lg-row"><span class="sw-cluster" aria-hidden="true">n</span>Bay Restoration sites too close to tell apart at this zoom, folded into one counted marker — click it to zoom in; names show where there is room, and on hover or focus</div>
  <div class="lg-row"><span style="display:inline-block;width:9px;height:9px;border:1px solid var(--muted);border-radius:2px;margin-inline-end:5px;vertical-align:-1px"></span><span title="__GEOPOSE_HONESTY__">every campus, anchor and pinned restoration marker on this map also holds a <b>GeoPose 1.0</b> pose (__N_POSES__ total — __N_CLAIMED__ claimed standard / __N_NOTCLAIMED__ not-claimed OMBI shapes; click a marker for its own pose line; hover for the height/heading honesty line)</span></div>
</details>
<div id="honesty"></div>
</div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script src="vendor/maplibre/maplibre-gl.js"></script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
// operator overrides: a self-hosted mirror of either source. They also
// let the harness prove the drawing paths without the public services.
const qs = new URLSearchParams(location.search);
if (qs.get('imagery')) D.imagery.tiles = qs.get('imagery');
const RECORDS_OVERRIDE = qs.get('records');
__GROUND_TRUTH_JS__
document.getElementById('honesty').textContent =
  'No basemap tiles: the registry drawn on the graticule, and nothing else. '
  + D.honesty.siting + ' ' + D.honesty.provenance;

/* the graticule: 2-degree lines generated here, DERIVED trivially */
const grat = { type: 'FeatureCollection', features: [] };
for (let lng = -180; lng <= 180; lng += 2)
  grat.features.push({ type: 'Feature', properties: {},
    geometry: { type: 'LineString', coordinates: [[lng, -85], [lng, 85]] } });
for (let lat = -84; lat <= 84; lat += 2)
  grat.features.push({ type: 'Feature', properties: {},
    geometry: { type: 'LineString', coordinates: [[-180, lat], [180, lat]] } });

/* the network's frame, computed from the campus features (never typed) */
const CAMPUS_LL = D.network.features.filter((x) => x.properties.slug).map((x) => x.geometry.coordinates);
const NETWORK_BOUNDS = [[Math.min(...CAMPUS_LL.map((c) => c[0])), Math.min(...CAMPUS_LL.map((c) => c[1]))],
                        [Math.max(...CAMPUS_LL.map((c) => c[0])), Math.max(...CAMPUS_LL.map((c) => c[1]))]];
document.getElementById('legend').addEventListener('toggle', () => {
  if (typeof placeCampusLabels === 'function' && loaded) placeCampusLabels();
});
// the legend opens folded to its one-line summary everywhere (the markup
// carries no `open`); a phone keeps the explicit fold as well
const PHONE = matchMedia('(max-width: 700px)').matches;
if (PHONE) document.getElementById('legend').open = false;
/* every fit keeps its frame clear of the open legend (bottom-left) and of
   the zoom control, so no campus label lands under either */
function fitPadding() {
  const lg = document.getElementById('legend');
  const base = PHONE ? 30 : 60;
  return { top: base + 20, right: PHONE ? 70 : base + 40, bottom: base + 20,
           left: lg.open && !PHONE ? lg.offsetWidth + 40 : PHONE ? 70 : base + 20 };
}
/* the environments layer, built from D.env only: worksites at their place's
   own point, K-12 districts at their campus's point (PROPOSED, name only),
   and one counted task marker per campus - grouped per point so a click
   lists everything standing there */
const ENV = { type: 'FeatureCollection', features: [] };
const ENV_GROUPS = {};
function envAdd(kind, key, lngLat, item) {
  const gk = kind + ':' + key;
  if (!ENV_GROUPS[gk]) {
    ENV_GROUPS[gk] = { kind, key, lngLat, items: [] };
    ENV.features.push({ type: 'Feature', properties: { kind, key: gk, n: 0 },
      geometry: { type: 'Point', coordinates: lngLat } });
  }
  ENV_GROUPS[gk].items.push(item);
  ENV.features.find((f) => f.properties.key === gk).properties.n = ENV_GROUPS[gk].items.length;
}
for (const w of D.env.worksitesOn) envAdd('worksite', w.lngLat.join(','), w.lngLat, w);
for (const k of D.env.k12) envAdd('k12', k.campus, k.lngLat, k);
const CAMPUS_FEATURE = Object.fromEntries(D.network.features.filter((x) => x.properties.slug)
  .map((x) => [x.properties.slug, x]));
for (const t of D.env.tasks.on)
  envAdd('tasks', t.place.campus, CAMPUS_FEATURE[t.place.campus].geometry.coordinates, t);
/* the map's paint follows the reader's Style: each role in D.stylePaint.roles
   names a --tc-* token, read off the page here (at load) and again whenever
   html[data-style] changes - no paint colour below is typed */
function paintColours() {
  const cs = getComputedStyle(document.body), c = {};
  for (const [role, t] of Object.entries(D.stylePaint.roles)) {
    const v = cs.getPropertyValue('--tc-' + t).trim();
    if (!/^#[0-9a-fA-F]{6}$/.test(v)) throw new Error('geomap paint: --tc-' + t + ' reads ' + JSON.stringify(v));
    c[role] = v;
  }
  return c;
}
let PC = paintColours();
const SKY_BLEND = ['interpolate', ['linear'], ['zoom'], 0, 1, 5, 1, 7, 0];
const skyOf = (c) => ({ 'sky-color': c.bg, 'horizon-color': c.horizon, 'fog-color': c.bg, 'atmosphere-blend': SKY_BLEND });
const PAINT_OF = (c) => [
  ['bg', 'background-color', c.bg], ['grat', 'line-color', c.grat],
  ['parcels', 'fill-extrusion-color', c.recorded], ['halls3d-edge', 'line-color', c.hallEdge],
  ['frames-fill', 'fill-color', c.frame], ['frames', 'line-color', c.frame], ['routes', 'line-color', c.route],
  ['anchors', 'circle-color', ['match', ['get', 'provenance'], 'RECORDED', c.recorded, c.authored]],
  ['anchors', 'circle-stroke-color', ['match', ['get', 'provenance'], 'RECORDED', c.bg, c.ring]],
  ['campuses', 'circle-color', c.campus], ['campuses', 'circle-stroke-color', c.bg],
  ['env-worksites', 'circle-stroke-color', c.bg], ['env-k12', 'circle-stroke-color', c.bg],
  ['env-tasks', 'circle-stroke-color', c.bg]];
function applyStylePaint() {
  PC = paintColours();
  for (const [layer, prop, v] of PAINT_OF(PC)) map.setPaintProperty(layer, prop, v);
  map.setSky(skyOf(PC));
  window.__geoPaint = { style: document.documentElement.getAttribute('data-style'), colours: PC };
}
window.__geoPaint = { style: document.documentElement.getAttribute('data-style'), colours: PC };
const map = new maplibregl.Map({
  container: 'map',
  attributionControl: false,
  style: {
    version: 8,
    // the Earth as a globe (MapLibre 5): every feature stays at its own
    // registry lat/lng - the projection changes, the coordinates never do
    projection: { type: 'globe' },
    // a thin atmosphere at the globe's rim, fading out as you zoom in
    sky: skyOf(PC),
    sources: {
      // the public-domain federal orthoimagery, straight from its authority
      sat: { type: 'raster', tiles: [D.imagery.tiles],
             tileSize: D.imagery.tile_size,
             maxzoom: D.imagery.zoom.max,
             attribution: D.imagery.attribution },
      grat: { type: 'geojson', data: grat },
      // the city's own building footprints, filled at view time
      parcels: { type: 'geojson',
                 data: { type: 'FeatureCollection', features: [] } },
      net: { type: 'geojson', data: D.network },
      halls3d: { type: 'geojson', data: D.geo3d.halls },
      districts3d: { type: 'geojson', data: D.geo3d.districts },
      env: { type: 'geojson', data: ENV },
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': PC.bg } },
      { id: 'sat', type: 'raster', source: 'sat',
        layout: { visibility: 'none' },
        paint: { 'raster-opacity': .85 } },
      { id: 'grat', type: 'line', source: 'grat',
        paint: { 'line-color': PC.grat, 'line-width': 1 } },
      // RECORDED footprints, extruded as they arrive from the authority
      { id: 'parcels', type: 'fill-extrusion', source: 'parcels',
        paint: { 'fill-extrusion-color': PC.recorded,
                 'fill-extrusion-opacity': .55,
                 'fill-extrusion-height': 9 } },
      // the 3D campus, stood up on the Earth (geo3d/registry, SCHEMATIC)
      { id: 'districts3d-fill', type: 'fill', source: 'districts3d', minzoom: 12,
        paint: { 'fill-color': ['get', 'color'], 'fill-opacity': .14 } },
      { id: 'districts3d-line', type: 'line', source: 'districts3d', minzoom: 12,
        paint: { 'line-color': ['get', 'color'], 'line-width': 1.4, 'line-dasharray': [3, 2] } },
      { id: 'halls3d', type: 'fill-extrusion', source: 'halls3d', minzoom: 12,
        paint: { 'fill-extrusion-color': ['get', 'color'],
                 'fill-extrusion-height': ['get', 'h'], 'fill-extrusion-base': 0,
                 'fill-extrusion-opacity': .92 } },
      // each SCHEMATIC hall's ground outline in the style's ink, so a hall
      // reads against every style's background whatever its district hue
      { id: 'halls3d-edge', type: 'line', source: 'halls3d', minzoom: 12,
        paint: { 'line-color': PC.hallEdge, 'line-width': 1.2 } },
      { id: 'frames-fill', type: 'fill', source: 'net',
        filter: ['==', ['get', 'kind'], 'frame'],
        paint: { 'fill-color': PC.frame, 'fill-opacity': .05 } },
      { id: 'frames', type: 'line', source: 'net',
        filter: ['==', ['get', 'kind'], 'frame'],
        paint: { 'line-color': PC.frame, 'line-width': 1.2,
                 'line-opacity': .7 } },
      { id: 'routes', type: 'line', source: 'net',
        filter: ['==', ['get', 'kind'], 'route'],
        paint: { 'line-color': PC.route, 'line-width': 1.6,
                 'line-dasharray': [2.5, 2] } },
      // the two provenance classes drawn apart: RECORDED solid steel,
      // AUTHORED a hollow ring - read from each feature's own `provenance`
      { id: 'anchors', type: 'circle', source: 'net',
        filter: ['==', ['get', 'kind'], 'anchor'],
        paint: { 'circle-radius': 4.5,
                 'circle-color': ['match', ['get', 'provenance'],
                                  'RECORDED', PC.recorded, PC.authored],
                 'circle-stroke-color': ['match', ['get', 'provenance'],
                                         'RECORDED', PC.bg, PC.ring],
                 'circle-stroke-width': 1.5 } },
      { id: 'campuses', type: 'circle', source: 'net',
        filter: ['has', 'slug'],
        paint: { 'circle-radius': 7, 'circle-color': PC.campus,
                 'circle-stroke-color': PC.bg, 'circle-stroke-width': 2 } },
      // the environments at their own points, fanned off the campus dot by a
      // fixed pixel offset so none covers it (the coordinate is unchanged)
      { id: 'env-worksites', type: 'circle', source: 'env', filter: ['==', ['get', 'kind'], 'worksite'],
        paint: { 'circle-radius': 5.5, 'circle-color': '#C98BE0', 'circle-stroke-color': PC.bg,
                 'circle-stroke-width': 1.5, 'circle-translate': [14, 10] } },
      { id: 'env-k12', type: 'circle', source: 'env', filter: ['==', ['get', 'kind'], 'k12'],
        paint: { 'circle-radius': 5.5, 'circle-color': '#F2D16B', 'circle-stroke-color': PC.bg,
                 'circle-stroke-width': 1.5, 'circle-translate': [-14, 10] } },
      { id: 'env-tasks', type: 'circle', source: 'env', filter: ['==', ['get', 'kind'], 'tasks'],
        paint: { 'circle-radius': ['interpolate', ['linear'], ['get', 'n'], 1, 5, 40, 11],
                 'circle-color': '#5CB584', 'circle-stroke-color': PC.bg,
                 'circle-stroke-width': 2, 'circle-translate': [0, 18] } },
    ],
  },
  // the opening view: the globe turned to the campus network, framed on the
  // ten campuses' own coordinates and padded clear of the legend
  bounds: NETWORK_BOUNDS, fitBoundsOptions: { padding: fitPadding() },
});
// zoom in / out, top-left: the panels open on the right and the legend and
// honesty line sit along the bottom, so the control is never under either
map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
// the Style menu sets html[data-style]; repaint the map from the tokens then
let styleLoaded = false;
map.once('load', () => { styleLoaded = true; applyStylePaint(); });
new MutationObserver(() => { if (styleLoaded) applyStylePaint(); })
  .observe(document.documentElement, { attributes: true, attributeFilter: ['data-style'] });

/* one popup at a time, owned by the marker that opened it: that marker shows
   a selected state while the popup is up, a keyboard open moves focus into
   the popup (its close button), and closing hands focus back to the marker */
let currentPopup = null, selectedEl = null;
function showPopup(lngLat, htmlText, ownerEl, byKeyboard) {
  if (currentPopup) currentPopup.remove();
  const pop = new maplibregl.Popup({ closeButton: true, maxWidth: '290px' })
    .setLngLat(lngLat).setHTML(htmlText).addTo(map);
  currentPopup = pop;
  if (selectedEl) selectedEl.classList.remove('is-selected');
  selectedEl = ownerEl || null;
  if (selectedEl) { selectedEl.classList.add('is-selected'); selectedEl.setAttribute('aria-expanded', 'true'); }
  const closeBtn = pop.getElement().querySelector('.maplibregl-popup-close-button');
  if (closeBtn) closeBtn.setAttribute('aria-label', 'Close this popup');
  if (byKeyboard && closeBtn) closeBtn.focus();
  pop.on('close', () => {
    if (currentPopup === pop) currentPopup = null;
    if (ownerEl) {
      ownerEl.classList.remove('is-selected'); ownerEl.setAttribute('aria-expanded', 'false');
      if (byKeyboard) ownerEl.focus();
    }
    if (selectedEl === ownerEl) selectedEl = null;
  });
  return pop;
}
// a click the keyboard made (Enter / Space on a button) carries detail 0
const viaKeyboard = (ev) => ev.detail === 0;
// the marker a click came from, read by popupFor / popupForRestoration
let opener = { el: null, kbd: false };
const openedBy = (el, ev) => { opener = { el, kbd: viaKeyboard(ev) }; };

/* campus labels as DOM markers - no glyph server needed. Each is a real
   <button>: Tab reaches it, Enter and Space open the same popup a click does */
let markers = 0;
const campusLabels = [];
const campusEl = {};
for (const f of D.network.features.filter((x) => x.properties.slug)) {
  const el = document.createElement('button');
  el.type = 'button';
  el.className = 'campus-marker';
  el.textContent = f.properties.name;
  el.setAttribute('aria-expanded', 'false');
  el.addEventListener('click', (ev) => { ev.stopPropagation(); openedBy(el, ev); popupFor(f); });
  campusLabels.push({ el, f, m: new maplibregl.Marker({ element: el, opacityWhenCovered: '0', anchor: 'bottom', offset: [0, -10] })
    .setLngLat(f.geometry.coordinates).addTo(map) });
  el.setAttribute('aria-label', f.properties.name + ' - campus');
  el.dataset.short = f.properties.name.split(/\s+/).map((x) => x[0]).join('');
  campusEl[f.properties.slug] = el;
  markers++;
}

/* whatever roadmap candidates remain - real AUTHORED coordinates, dashed
   to match the labels doctrine ("the dashed outline is the claim"), never
   drawn into D.network itself: this map's own network.geojson source
   states only the built network, and candidates are not that. With
   Detroit's promotion D.candidates is empty and the loop below draws
   nothing - the ten-campus target is fully met, not exceeded. */
let candMarkers = 0;
for (const [ck, c] of Object.entries(D.candidates)) {
  const el = document.createElement('div');
  el.className = 'candidate-marker';
  el.textContent = c.name;
  el.addEventListener('click', (ev) => { ev.stopPropagation(); popupForCandidate(ck, c); });
  new maplibregl.Marker({ element: el, opacityWhenCovered: '0', anchor: 'bottom', offset: [0, -10] })
    .setLngLat([c.lng, c.lat]).addTo(map);
  candMarkers++;
}
function popupForCandidate(ck, c) {
  showPopup([c.lng, c.lat],
    `<b>${c.name}</b><br><span class="pv">AUTHORED</span>`
      + `<span class="pv">proposed</span>`
      + `<br>${c.city}, ${c.region}<br>${c.why}`
      + `<br><span class="src">${D.roadmapHonesty.not_a_claim_of_content}</span>`);
}

/* Bay Restoration sites: real, independently-run projects - AUTHORED
   coordinates on this map's side only, each linking to its own real
   source page rather than anything this bundle claims to run */
let restMarkers = 0;
const restItems = [];
/* only a PINNED site has a coordinate: the unpinned one (lat/lng null) used
   to get a marker too, which MapLibre read as 0,0 - a green dot off West
   Africa. Its refusal to be pinned is content, so it stays in the sites panel. */
for (const s of D.restorationSites.filter((x) => x.pin === true)) {
  const el = document.createElement('button');
  el.type = 'button';
  el.className = 'restoration-marker' + (s.category === 'environmental-monitoring' ? ' env-monitoring' : '');
  el.setAttribute('aria-expanded', 'false');
  el.innerHTML = '<span class="rm-dot"></span><span class="rm-label"></span>';
  el.querySelector('.rm-label').textContent = s.name;
  el.addEventListener('click', (ev) => { ev.stopPropagation(); openedBy(el, ev); popupForRestoration(s); });
  /* the dot sits on its own point; the name hangs BELOW it, and the campus
     label stands ABOVE its point and stacks higher: a site that shares a
     campus's coordinates (Treasure Island) cannot cover the campus label */
  restItems.push({ el, s, m: new maplibregl.Marker({ element: el, opacityWhenCovered: '0', anchor: 'top', offset: [0, -12] })
    .setLngLat([s.lng, s.lat]).addTo(map) });
  el.setAttribute('aria-label', s.name + ' - Bay Restoration site');
  restMarkers++;
}

/* sites closer on screen than one target's width fold into one counted
   cluster (greedy, in registry order); a click on it zooms to just those
   sites. Rebuilt after every zoom, so a site unfolds as soon as it has room. */
let clusterMarkers = [];
const FOLD_PX = 26;
function foldRestoration() {
  for (const c of clusterMarkers) c.remove();
  clusterMarkers = [];
  const pts = restItems.map((r) => map.project([r.s.lng, r.s.lat]));
  const taken = new Array(restItems.length).fill(false);
  for (let i = 0; i < restItems.length; i++) {
    if (taken[i]) continue;
    const group = [i];
    for (let j = i + 1; j < restItems.length; j++)
      if (!taken[j] && Math.hypot(pts[i].x - pts[j].x, pts[i].y - pts[j].y) < FOLD_PX) group.push(j);
    for (const k of group) taken[k] = true;
    for (const k of group) restItems[k].el.classList.toggle('folded', group.length > 1);
    if (group.length < 2) continue;
    const sites = group.map((k) => restItems[k].s);
    const lng = sites.reduce((a, x) => a + x.lng, 0) / sites.length;
    const lat = sites.reduce((a, x) => a + x.lat, 0) / sites.length;
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'rest-cluster';
    b.textContent = String(sites.length);
    b.dataset.sites = sites.map((x) => x.id).join(' ');
    b.setAttribute('aria-label', sites.length + ' Bay Restoration sites here: '
      + sites.map((x) => x.name).join('; ') + '. Zoom in to separate them');
    b.title = sites.map((x) => x.name).join(' · ');
    b.addEventListener('click', (ev) => {
      ev.stopPropagation();
      const w = Math.min(...sites.map((x) => x.lng)), e = Math.max(...sites.map((x) => x.lng));
      const so = Math.min(...sites.map((x) => x.lat)), n = Math.max(...sites.map((x) => x.lat));
      map.fitBounds([[w, so], [e, n]], { padding: 90, maxZoom: 14, duration: 700 });
    });
    /* hung below the point like a single site, so it never covers a campus label */
    const aria = b.getAttribute('aria-label');
    clusterMarkers.push(new maplibregl.Marker({ element: b, opacityWhenCovered: '0', anchor: 'top', offset: [0, -13] })
      .setLngLat([lng, lat]).addTo(map));
    b.setAttribute('aria-label', aria);
  }
}

/* campus labels that collide at the current zoom (Treasure Island and Oakland
   Waterfront sit a few kilometres apart, one pixel apart at the opening zoom;
   Loop Rail and Motor City likewise) would leave one campus unclickable. Each
   label tries above its dot, then below, right and left, then the four
   diagonals, and takes the first slot that overlaps no label already placed
   and no restoration dot. When dots fill every slot it takes the first slot
   clear of other campus labels: campus labels stack above restoration
   markers, so only another campus label can take a campus's clicks. Only the
   label moves: the dot in the campuses layer stays on the campus's own
   coordinates. Flagship campuses are placed first.
   Every rectangle is COMPUTED from map.project() and the element's own
   size, never measured after setOffset(): MapLibre applies a marker's new
   offset on its next render, so a measured rectangle is the old slot (that
   is how Loop Rail and Motor City used to end up on top of each other). */
function placeCampusLabels() {
  foldRestoration();
  const hit = (r, q) => r.left < q.right && q.left < r.right && r.top < q.bottom && q.top < r.bottom;
  const box = (ll, o, w, h, anchor) => {
    const p = map.project(ll), cx = p.x + o[0], cy = p.y + o[1];
    const top = anchor === 'bottom' ? cy - h : cy;
    return { left: cx - w / 2, right: cx + w / 2, top, bottom: top + h };
  };
  for (const r of restItems) r.el.classList.remove('show-label');
  const dots = [...document.querySelectorAll('.restoration-marker')]
    .filter((e) => !e.classList.contains('folded'))
    .map((e) => restItems.find((r) => r.el === e))
    .map((r) => ({ r, rect: box([r.s.lng, r.s.lat], [0, -12], 24, 24, 'top') }));
  const placed = [];
  const VW = map.getContainer().clientWidth, VH = map.getContainer().clientHeight;
  /* the map's own chrome is an obstacle too: no label slides under the open
     legend or the zoom control, where it could not be read or clicked */
  const cr = map.getContainer().getBoundingClientRect();
  const chrome = [document.getElementById('legend'), document.querySelector('.maplibregl-ctrl-top-left')]
    .filter((e) => e).map((e) => e.getBoundingClientRect()).filter((r) => r.width)
    .map((r) => ({ left: r.left - cr.left - 4, right: r.right - cr.left + 4, top: r.top - cr.top - 4, bottom: r.bottom - cr.top + 4 }));
  const obstacles = chrome.slice();
  const scr = new Map(campusLabels.map((c) => [c, map.project(c.f.geometry.coordinates)]));
  const crowd = (c) => campusLabels.filter((d) => d !== c
    && Math.hypot(scr.get(c).x - scr.get(d).x, scr.get(c).y - scr.get(d).y) < 140).length;
  const order = campusLabels.slice().sort((a, b) => crowd(b) - crowd(a)
    || (D.rollups[b.f.properties.slug].flagship === true) - (D.rollups[a.f.properties.slug].flagship === true));
  const trySlots = (c) => {
    const w = c.el.offsetWidth, h = c.el.offsetHeight, ll = c.f.geometry.coordinates;
    const slots = [[0, -10], [0, 10 + h], [w / 2 + 12, h / 2], [-(w / 2 + 12), h / 2],
                   [w / 2 + 8, -6], [-(w / 2 + 8), -6], [w / 2 + 8, h + 6], [-(w / 2 + 8), h + 6],
                   // a second ring, for a phone-sized frame of the whole network
                   [0, -14 - h], [0, 14 + 2 * h], [w / 2 + 12, -h / 2 - 4], [-(w / 2 + 12), -h / 2 - 4],
                   [w / 2 + 12, 3 * h / 2 + 4], [-(w / 2 + 12), 3 * h / 2 + 4]];
    let clearOfAll = null, clearOfCampus = null;
    for (const o of slots) {
      const r = box(ll, o, w, h, 'bottom');
      // a slot off the map's own frame is no slot: the label would be cut off
      if (r.left < 2 || r.top < 2 || r.right > VW - 2 || r.bottom > VH - 2) continue;
      if (placed.some((q) => hit(r, q)) || obstacles.some((q) => hit(r, q))) continue;
      if (clearOfCampus === null) clearOfCampus = o;
      if (!dots.some((d) => hit(r, d.rect))) { clearOfAll = o; break; }
    }
    return { o: clearOfAll !== null ? clearOfAll : clearOfCampus, first: slots[0], w, h, ll };
  };
  for (const c of order) {
    if (c.el.classList.contains('maplibregl-marker-covered')) continue;
    c.el.classList.remove('compact');
    let t = trySlots(c);
    /* no slot clear of every other campus label: the label folds to its
       initials (its accessible name and popup keep the full name) and tries
       again, so no campus label ever sits on another's clicks */
    if (t.o === null) { c.el.classList.add('compact'); t = trySlots(c); }
    const o = t.o !== null ? t.o : t.first;
    c.m.setOffset(o);
    placed.push(box(t.ll, o, t.w, t.h, 'bottom'));
  }
  /* a cluster stands for sites spread over many kilometres, so it may step
     aside from its centroid to keep clear of the campus labels */
  for (const cm of clusterMarkers) {
    const el = cm.getElement(), w = el.offsetWidth, h = el.offsetHeight, ll = cm.getLngLat();
    const slots = [[0, -13], [0, 16], [w / 2 + 16, -13], [-(w / 2 + 16), -13], [0, 40], [0, -44]];
    const o = slots.find((s) => !placed.some((q) => hit(box(ll, s, w, h, 'top'), q))) ?? slots[0];
    cm.setOffset(o);
    placed.push(box(ll, o, w, h, 'top'));
  }
  /* declutter by priority: campus labels and clusters are placed; a site's
     name shows only where it overlaps no campus label, no cluster, no other
     dot and no other shown name (walkable sites first); the rest keep their
     dot, and show their name on hover or keyboard focus */
  const byPriority = dots.slice().sort((a, b) => (b.r.s.walkable === true) - (a.r.s.walkable === true));
  for (const d of byPriority) {
    d.r.el.classList.add('show-label');
    const lab = d.r.el.querySelector('.rm-label');
    const lr = box([d.r.s.lng, d.r.s.lat], [0, 10], lab.offsetWidth, lab.offsetHeight, 'top');
    if (placed.some((q) => hit(lr, q)) || dots.some((q) => q !== d && hit(lr, q.rect)))
      d.r.el.classList.remove('show-label');
    else placed.push(lr);
  }
}
map.on('load', placeCampusLabels);
map.on('zoomend', placeCampusLabels);
map.on('resize', placeCampusLabels);
// on a globe a pan turns the Earth, so neighbours on screen change with it
map.on('moveend', placeCampusLabels);
// the spatial fabric's own pose for this exact point, when one exists —
// campus/anchor features carry it inline (properties.geopose, joined at
// build time); a restoration site's is looked up by ref, computed the
// same way build_geomap.py's own Python does (restoration-site:<id>). The
// full honesty sentence (spatial/registry/geopose.json's own wording, never
// softened) sits on the legend's GeoPose row as a hover title rather than
// repeated on every popup.
function geoposeLine(pose) {
  if (!pose) return '';
  return `<br><span class="pv" style="color:var(--steel);border-color:var(--steel)">GeoPose 1.0</span>`
    + `<span class="pv">${pose.position_provenance}</span>`
    + `<br><span class="src">h = ${pose.h_m.toFixed(1)} m — UNKNOWN, a placeholder, never a measurement</span>`;
}
// The same on-request, live, never-stored ground truth the 3D app fires per
// POI and per restoration site (elevationLookup(), siteElevation(),
// siteAerial() there) — ported here from the shared web/groundtruth.py
// module rather than copy-pasted, so a real USGS elevation and a real USGS
// aerial thumbnail are one click away on a campus, anchor or restoration
// marker too. `seq` makes each popup's result containers unique, since more
// than one popup can be open on this map at once.
let __gtSeq = 0;
function groundTruthButtons(lat, lng) {
  const id = 'gt' + (__gtSeq++);
  return `<p style="margin:6px 0 2px">`
    + `<button class="opt gt-elev-btn" data-lat="${lat}" data-lng="${lng}" data-id="elev-${id}" `
    + `style="font:inherit;font-size:10.5px;padding:2px 8px;background:none;color:var(--ink);`
    + `border:1px solid var(--rule);border-radius:999px;cursor:pointer">↕ ground elevation</button> `
    + `<button class="opt gt-aerial-btn" data-lat="${lat}" data-lng="${lng}" data-id="aer-${id}" `
    + `style="font:inherit;font-size:10.5px;padding:2px 8px;background:none;color:var(--ink);`
    + `border:1px solid var(--rule);border-radius:999px;cursor:pointer">🛰 aerial</button></p>`
    + `<p id="elev-${id}"></p><div id="aer-${id}"></div>`;
}
document.addEventListener('click', (e) => {
  const eb = e.target.closest('.gt-elev-btn');
  if (eb) {
    eb.disabled = true; eb.textContent = 'looking up…';
    gtElevationInto(document.getElementById(eb.dataset.id), D,
      parseFloat(eb.dataset.lat), parseFloat(eb.dataset.lng), true);
    return;
  }
  const ab = e.target.closest('.gt-aerial-btn');
  if (ab) {
    ab.disabled = true; ab.textContent = 'loading…';
    gtAerialInto(document.getElementById(ab.dataset.id), D,
      parseFloat(ab.dataset.lat), parseFloat(ab.dataset.lng));
  }
});
// a walkable site walks; a non-walkable one states its registry's own
// refusal, verbatim, and gets no link - same rule as the static list
function walkLine(s) {
  if (s.walkable === true)
    return `<a class="walk" href="trade_craft_3d.html?campus=${s.campus}">walk it in the 3D environment`
      + ` (from the ${D.rollups[s.campus].name} restoration panel)</a>`;
  return `<span class="refusal">not walkable: ${s.walkable_reason}</span>`;
}
function rollupList(slug) {
  const r = D.rollups[slug];
  return `<ul class="roll">`
    + `<li><b>${r.hallsCount}</b> halls on this campus</li>`
    + `<li><b>${r.hallsWithLesson}</b> halls with a lesson</li>`
    + `<li><b>${r.hallsBindingSeat}</b> halls binding a seat</li>`
    + `<li><b>${r.flippedUnits}</b> flipped-classroom units</li>`
    + `<li>flagship: <b>${r.flagship ? 'yes' : 'no'}</b></li></ul>`;
}
function popupForRestoration(s) {
  const el = opener.el, byKeyboard = opener.kbd;
  opener = { el: null, kbd: false };
  const wf = s.workforce
    ? `<br><b>Workforce pathway:</b> ${s.workforce_note}` : '';
  // environmental-monitoring sites point at real monitoring participation
  // instead of a workforce/job-training pathway - kept in its own field
  // so the two are never conflated
  const pt = s.participation
    ? `<br><b>Monitoring participation:</b> ${s.participation_note}` : '';
  const cat = s.category === 'environmental-monitoring'
    ? `<br><span class="pv" style="color:var(--steel);border-color:var(--steel)">environmental monitoring — not walkable: ${s.walkable_reason}</span>`
    : '';
  // the one site that needs it (Treasure Island NSTI) states in its own
  // voice that it is NOT NPL-listed and which EPA ID is the other place
  const dis = s.disambiguation ? `<br><b>Note:</b> ${s.disambiguation}` : '';
  const pose = geoposeLine(D.geopose.byRef['restoration-site:' + s.id]);
  showPopup([s.lng, s.lat],
    `<b>${s.name}</b><br><span class="pv rec">real project</span>`
      + `<span class="pv">AUTHORED coordinate</span>` + cat
      + `<br>${s.org}<br>${s.city}, ${s.county} · ${s.habitat}<br>${s.scale}`
      + dis + wf + pt + pose + `<br>` + walkLine(s)
      + `<br><a href="${s.source_url}" target="_blank" rel="noopener" class="src">${s.source_url}</a>`
      + `<br><span class="src">${D.restorationHonesty.not_affiliated}</span>`
      + groundTruthButtons(s.lat, s.lng), el, byKeyboard);
}

function popupFor(f, lngLat) {
  const el = opener.el, byKeyboard = opener.kbd;
  opener = { el: null, kbd: false };
  const p = f.properties;
  const at = lngLat ?? (f.geometry.type === 'Point'
    ? f.geometry.coordinates : map.getCenter());
  const chips = `<span class="pv ${p.provenance === 'RECORDED' ? 'rec' : ''}">${p.provenance}</span>`
    + (p.km !== undefined ? `<span class="pv">${p.km} km</span>` : '')
    + (p.bearing_deg !== undefined ? `<span class="pv">${p.bearing_deg}°</span>` : '');
  // ground truth only makes sense at a single real point - a campus or an
  // anchor - never a route (two endpoints) or a city frame (a polygon)
  const gt = (!p.kind || p.kind === 'anchor') && f.geometry.type === 'Point'
    ? groundTruthButtons(f.geometry.coordinates[1], f.geometry.coordinates[0]) : '';
  // an anchor's coordinate class, in the registry's own word, with what
  // that word means here - never upgraded on the way to the screen
  const anchorPv = p.kind === 'anchor'
    ? (p.provenance === 'RECORDED'
        ? `<br><span class="src">coordinate RECORDED — copied from the source cited below</span>`
        : `<br><span class="pv auth">AUTHORED coordinate</span><span class="src">typed from public record; no source was fetched</span>`)
    : '';
  const flag = p.slug && D.rollups[p.slug].flagship ? `<span class="flag">FLAGSHIP</span>` : '';
  showPopup(at,
    `<b>${p.name ?? (p.kind === 'route'
        ? p.from + ' ↔ ' + p.to : 'city frame · ' + p.campus)}</b>${flag}<br>${chips}`
      + (p.halls ? `<br>${p.halls} halls · ${p.districts} districts · ${p.city}, ${p.region}` : '')
      + (p.slug ? rollupList(p.slug) + campusDoors(p.slug) : '')
      + (p.blurb ? `<br>${p.blurb}` : '')
      + geoposeLine(p.geopose) + anchorPv
      + `<br><span class="src">source: ${p.source}</span>` + gt,
    el || (p.slug ? campusEl[p.slug] : null), byKeyboard);
}
for (const layer of ['campuses', 'anchors', 'routes', 'frames']) {
  map.on('click', layer, (e) => popupFor(e.features[0], e.lngLat));
  map.on('mouseenter', layer, () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', layer, () => { map.getCanvas().style.cursor = ''; });
}

/* the campus panel and the legend's anchor split, rendered from D only */
document.getElementById('campusList').innerHTML = Object.entries(D.rollups)
  .map(([slug, r]) => `<li data-campus="${slug}"><b>${r.name}</b>`
    + (r.flagship ? `<span class="flag">FLAGSHIP</span>` : '') + rollupList(slug) + `</li>`)
  .join('');
for (const el of document.querySelectorAll('[data-anchor-count]'))
  el.textContent = D.anchorProvenance[el.dataset.anchorCount];
let openPanel = null;
document.querySelectorAll('[data-panel]').forEach((b) =>
  b.addEventListener('click', () => {
    const id = b.dataset.panel;
    for (const s of document.querySelectorAll('.panel'))
      s.classList.toggle('open', s.id === id && openPanel !== id);
    openPanel = openPanel === id ? null : id;
    for (const x of document.querySelectorAll('[data-panel]'))
      x.setAttribute('aria-pressed', String(x.dataset.panel === openPanel));
  }));

/* Escape closes the open popup first, then an open panel */
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  if (tour.on) { stopTour(); document.getElementById('tourBtn').focus(); return; }
  if (currentPopup) { currentPopup.remove(); return; }
  if (openPanel) {
    const b = document.querySelector(`[data-panel="${openPanel}"]`);
    b.click(); b.focus();
  }
});

/* find: every campus and every pinned restoration site, by its own name
   from D - pick one and the map flies to it and opens its popup */
const FIND = [];
for (const c of campusLabels)
  FIND.push({ name: c.f.properties.name, lngLat: c.f.geometry.coordinates, zoom: 11,
              open: () => { opener = { el: c.el, kbd: true }; popupFor(c.f); } });
for (const r of restItems)
  FIND.push({ name: r.s.name, lngLat: [r.s.lng, r.s.lat], zoom: 13,
              open: () => { opener = { el: r.el, kbd: true }; popupForRestoration(r.s); } });
document.getElementById('findList').innerHTML = FIND
  .map((x) => `<option value="${x.name.replace(/"/g, '&quot;')}"></option>`).join('');
function findGo(q) {
  const hit = FIND.find((x) => x.name.toLowerCase() === q.trim().toLowerCase())
    ?? FIND.find((x) => q.trim().length > 1 && x.name.toLowerCase().includes(q.trim().toLowerCase()));
  if (!hit) return false;
  map.once('moveend', () => { placeCampusLabels(); hit.open(); });
  map.flyTo({ center: hit.lngLat, zoom: Math.max(map.getZoom(), hit.zoom), duration: 800 });
  return true;
}
const findEl = document.getElementById('find');
findEl.addEventListener('change', () => findGo(findEl.value));
findEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); findGo(findEl.value); } });

const FITS = {
  network: NETWORK_BOUNDS,
  bay: [[D.city['treasure-island'].bounds.w, D.city['treasure-island'].bounds.s],
        [D.city['treasure-island'].bounds.e, D.city['treasure-island'].bounds.n]],
  nola: [[D.city['new-orleans'].bounds.w, D.city['new-orleans'].bounds.s],
         [D.city['new-orleans'].bounds.e, D.city['new-orleans'].bounds.n]],
};
document.querySelectorAll('[data-fit]').forEach((b) =>
  b.addEventListener('click', () =>
    map.fitBounds(FITS[b.dataset.fit], { padding: fitPadding(), duration: 700 })));

/* globe or flat: the same features, the same coordinates, two projections */
let projection = 'globe';
const projBtn = document.getElementById('projBtn');
projBtn.addEventListener('click', () => {
  projection = projection === 'globe' ? 'mercator' : 'globe';
  map.setProjection({ type: projection });
  projBtn.setAttribute('aria-pressed', String(projection === 'globe'));
  projBtn.textContent = projection === 'globe' ? '🌐 Globe view' : '▭ Flat view';
  map.once('idle', placeCampusLabels);
});

/* ---------------------------------------------------------------------
   The city's own records, and the sky's own picture of it. Both are
   fetched from their authority in THIS browser - nothing is stored in
   the bundle - and a failure is a fallback with a line on the page,
   never an error. */
let satOn = false, satState = 'off';
let parcelState = 'off', parcelCount = 0, parcelCampus = null;
const statusEl = document.getElementById('honesty');
function status(extra) {
  statusEl.textContent = (extra ? extra + ' ' : '')
    + (satOn ? D.imagery.attribution + ' (' + D.imagery.licence + '). ' : '')
    + D.honesty.siting + ' ' + D.recHonesty.fidelity;
}
status('No basemap tiles unless you ask: the registry drawn on the graticule.');

document.getElementById('satBtn').addEventListener('click', () => {
  satOn = !satOn;
  satState = satOn ? 'requested' : 'off';
  map.setLayoutProperty('sat', 'visibility', satOn ? 'visible' : 'none');
  document.getElementById('satBtn').setAttribute('aria-pressed', String(satOn));
  status(satOn ? 'Imagery requested from ' + D.imagery.authority + '.'
    : 'Imagery off.');
});
// a tile that never arrives is expected here, not a fault: say so once
map.on('error', (e) => {
  if (satOn && /sat/.test(e.sourceId ?? '') && satState !== 'failed') {
    satState = 'failed';
    status('Imagery did not answer from this network - the graticule stands in.');
  }
});

// which campus frame is the view sitting in?
function campusInView() {
  const c = map.getCenter();
  for (const [ck, s] of Object.entries(D.sources)) {
    const f = s.frame;
    if (c.lng > f.w && c.lng < f.e && c.lat > f.s && c.lat < f.n) return ck;
  }
  return null;
}
async function loadParcels() {
  const ck = campusInView();
  if (!ck) {
    parcelState = 'no-frame';
    status('Zoom into a campus frame first - footprints are fetched per city.');
    return;
  }
  const src = D.sources[ck];
  const b = map.getBounds();
  const q = new URLSearchParams(src.query);
  // the envelope goes on only where the declared query asks for one
  if (src.query.geometryType)
    q.set('geometry', [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(','));
  parcelState = 'loading'; parcelCampus = ck;
  status('Asking ' + src.authority + ' for footprints in view...');
  try {
    const res = await fetch(RECORDS_OVERRIDE
      ?? (src.endpoint + '?' + q.toString()));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const fc = await res.json();
    const feats = (fc.features ?? []).filter((f) => f.geometry);
    map.getSource('parcels').setData({ type: 'FeatureCollection', features: feats });
    parcelCount = feats.length;
    parcelState = feats.length ? 'live' : 'empty';
    status(feats.length
      ? feats.length + ' RECORDED footprints drawn from ' + src.authority + '.'
      : 'That authority returned no footprint in this view.');
  } catch (err) {
    parcelState = 'failed';
    status('Could not reach ' + src.authority + ' from this network - '
      + 'the schematic layers stand in. ' + D.recHonesty.availability);
  }
}
document.getElementById('parBtn').addEventListener('click', loadParcels);

/* ---------------------------------------------------------------------
   The 3D globe: every hall of the 3D campus stood up at its SCHEMATIC place
   (geo3d/registry/geo3d.json - north-up about the campus centroid, no
   heading or survey recorded), a pitched camera per campus, a tour, the
   environments layer and what is deliberately NOT on the globe. */
const ESC = (x) => String(x).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
function tasksAt(slug) { return D.env.tasks.on.filter((t) => t.place.campus === slug); }
function taskBody(t) {
  const go = t.href !== null
    ? `<a class="door walk3d" href="${ESC(t.href)}">launch ↗</a>`
    : `<span class="refusal">not launchable: ${ESC(t.why)}</span>`;
  return `<b>${ESC(t.title)}</b> <span class="pv">${ESC(t.kind)}</span>`
    + `<span class="pv">${ESC(t.provenance)}</span> ${go}`;
}
const taskLi = (t) => `<li data-task="${ESC(t.id)}">${taskBody(t)}</li>`;
// why a task is listed off the globe, from its own place - never guessed
const offWhy = (t) => t.place.kind === 'wilds-site'
  ? 'stands in an AUTHORED wild world, not at a real location'
  : t.place.campus === null ? 'a custom space with no campus' : 'its place is not one this map stands on the Earth';
function tasksLine(slug) {
  if (D.env.tasks.state.state !== 'built')
    return `<br><span class="src">simulated tasks: tasks/registry/tasks.json is not built in this tree</span>`;
  const ts = tasksAt(slug);
  return `<br><b>${ts.length}</b> simulated tasks here <button type="button" class="popbtn" data-task-campus="${slug}">list them</button>`;
}
function campusDoors(slug) {
  const cam = D.geo3d.camera[slug];
  const k12 = D.env.k12.filter((k) => k.campus === slug);
  const halls = cam.halls > 0
    ? `<button type="button" class="popbtn" data-fly="${slug}">🎥 fly in: ${cam.halls} halls in 3D <span class="pv sch">SCHEMATIC</span></button>`
    : `<br><span class="src">${ESC(D.geo3d.noHalls[slug])}</span>`;
  return halls + tasksLine(slug)
    + (k12.length ? `<br><span class="pv prop">PROPOSED</span> K-12: ${k12.map((k) => ESC(k.district)).join('; ')}` : '')
    + `<br><a class="door walk3d" href="trade_craft_3d.html?campus=${slug}">⬡ walk it in 3D</a>`
    + `<a class="door" href="trade_craft_map.html">▦ 2D map</a>`
    + `<a class="door" href="trade_craft_interactive.html">▦ interactive map</a>`;
}
function popupForHall(p, lngLat) {
  showPopup(lngLat,
    `<b>${ESC(p.name)}</b><br><span class="pv sch">SCHEMATIC placement</span>`
      + `<span class="pv">${ESC(p.districtName)} district</span>`
      + `<br>${ESC(D.rollups[p.campus].name)}`
      + `<ul class="roll"><li><b>${p.lessons}</b> lessons for this hall</li>`
      + (D.env.tasks.state.state === 'built' ? `<li><b>${p.tasks}</b> simulated tasks at this hall</li>` : `<li>simulated tasks: registry not built</li>`)
      + `<li>wall ${p.h.toFixed(1)} m (as drawn in the 3D campus, ${ESC(p.roof)} roof)</li></ul>`
      + `<a class="door walk3d" href="trade_craft_3d.html?hall=${ESC(p.slug)}">⬡ walk it in 3D</a>`
      + `<a class="door" href="trade_craft_interactive.html?hall=${ESC(p.slug)}">▦ on the interactive map</a>`
      + `<br><span class="src">${ESC(D.geo3d.placement)}</span>`);
}
/* MapLibre's globe projection answers no rendered-feature query for a
   fill-extrusion (it does on the flat map), so a hall is hit-tested here:
   its footprint projected to the screen, point-in-polygon, nearest first.
   The footprints come from D.geo3d only - the same rings the layer draws. */
/*hit:begin - pure screen-space picking, unit-tested by web/test_geomap.mjs.
   A hall is hit on its ground footprint, on its top face (the footprint
   raised by the drawn wall height) or on a wall between them - the convex
   hull of the eight screen corners - so a tall hall seen at a pitch answers
   where it is drawn, not only where it stands. The hall drawn nearest the
   viewer (its ground centroid lowest on screen) wins an overlap. */
function inPoly(pt, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++)
    if ((ring[i].y > pt.y) !== (ring[j].y > pt.y)
        && pt.x < (ring[j].x - ring[i].x) * (pt.y - ring[i].y) / (ring[j].y - ring[i].y) + ring[i].x) inside = !inside;
  return inside;
}
function hull(ps) {
  const p = ps.slice().sort((a, b) => a.x - b.x || a.y - b.y);
  const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lo = [], up = [];
  for (const q of p) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
  for (const q of p.reverse()) { while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
  return lo.slice(0, -1).concat(up.slice(0, -1));
}
function pickHall(pt, boxes) {
  let best = null;
  for (const b of boxes) {
    const via = inPoly(pt, b.top) ? 'roof' : inPoly(pt, b.ground) ? 'ground'
      : inPoly(pt, hull(b.ground.concat(b.top))) ? 'wall' : null;
    if (via === null) continue;
    const cy = b.ground.reduce((a, q) => a + q.y, 0) / b.ground.length;
    if (best === null || cy > best.cy) best = { id: b.id, via, cy };
  }
  return best;
}
/*hit:end*/
/* MapLibre's globe projection answers no rendered-feature query for a
   fill-extrusion (it does on the flat map), so a hall is hit-tested here
   from D.geo3d only - the same rings and wall height the layer draws. The
   top face is projected by the map's own transform with the wall height as
   the elevation (globe and flat alike). */
const AT_HEIGHT = (h) => ({ getElevationForLngLat: () => h, getElevationForLngLatZoom: () => h });
function screenAt(c, h) { return map.transform.locationToScreenPoint(maplibregl.LngLat.convert(c), AT_HEIGHT(h)); }
function hallBoxes() {
  return D.geo3d.halls.features.map((f, i) => {
    const cs = f.geometry.coordinates[0].slice(0, 4);
    return { id: i, ground: cs.map((c) => map.project(c)), top: cs.map((c) => screenAt(c, f.properties.h)) };
  });
}
let lastHallVia = null;
function hallAt(pt) {
  if (!layerOn.halls3d || map.getZoom() < 12) return null;
  const hit = pickHall(pt, hallBoxes());
  lastHallVia = hit ? hit.via : null;
  return hit ? D.geo3d.halls.features[hit.id] : null;
}
function hallsInView() {
  if (!layerOn.halls3d || map.getZoom() < 12) return 0;
  const W = map.getContainer().clientWidth, H = map.getContainer().clientHeight;
  return D.geo3d.halls.features.filter((f) => {
    const q = map.project(f.geometry.coordinates[0][0]);
    return q.x >= 0 && q.y >= 0 && q.x <= W && q.y <= H;
  }).length;
}
map.on('click', (e) => {
  const f = hallAt(e.point);
  if (f) popupForHall(f.properties, e.lngLat);
});
function popupForEnv(gk) {
  const g = ENV_GROUPS[gk];
  let body = '';
  if (g.kind === 'worksite')
    body = `<b>Worksites here</b><br><span class="pv auth">AUTHORED scenario</span><span class="src">${ESC(g.items[0].at)}</span>`
      + `<ul class="tasklist">` + g.items.map((w) => `<li><b>${ESC(w.title)}</b><br>${ESC(w.place)} `
      + `<a class="door" href="${ESC(w.href)}">open the worksite</a></li>`).join('') + `</ul>`;
  else if (g.kind === 'k12')
    body = `<b>K-12 districts</b> <span class="pv prop">PROPOSED</span><br><span class="src">shown at the ${ESC(D.rollups[g.key].name)} campus point: no address is recorded</span>`
      + `<ul class="tasklist">` + g.items.map((k) => `<li><b>${ESC(k.district)}</b> (${ESC(k.city)})<br><span class="src">${ESC(k.status)}; ${ESC(k.provenance)}</span></li>`).join('')
      + `</ul><a class="door" href="trade_craft_schools.html#districts">the K-12 pathways page</a>`;
  else
    body = `<b>${g.items.length} simulated tasks at ${ESC(D.rollups[g.key].name)}</b><br><span class="src">${ESC(D.env.tasks.state.honesty)}</span>`
      + `<ul class="tasklist">` + g.items.map(taskLi).join('') + `</ul>`;
  showPopup(g.lngLat, body);
}
for (const layer of ['env-worksites', 'env-k12', 'env-tasks']) {
  map.on('click', layer, (e) => { e.preventDefault(); popupForEnv(e.features[0].properties.key); });
  map.on('mouseenter', layer, () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', layer, () => { map.getCanvas().style.cursor = ''; });
}
map.on('mouseenter', 'halls3d', () => { map.getCanvas().style.cursor = 'pointer'; });
map.on('mouseleave', 'halls3d', () => { map.getCanvas().style.cursor = ''; });

/* the cinematic camera: pitched, turned, flown - or jumped when the reader
   asks the system for reduced motion */
const TOUR_DWELL_MS = 2600;
function campusView(slug, i) {
  const c = D.geo3d.camera[slug];
  return { center: [c.lng, c.lat], zoom: c.halls > 0 ? 16.1 : 13.2, pitch: 58,
           bearing: -30 + (i % 4) * 20 };
}
function flyToCampus(slug, opts) {
  const v = campusView(slug, D.geo3d.tour.indexOf(slug));
  if (REDUCED) map.jumpTo(v);
  else map.flyTo({ ...v, duration: opts && opts.duration ? opts.duration : 4200, essential: false });
}
document.addEventListener('click', (e) => {
  const fb = e.target.closest('[data-fly]');
  if (fb) { if (currentPopup) currentPopup.remove(); flyToCampus(fb.dataset.fly); return; }
  const tb = e.target.closest('[data-task-campus]');
  if (tb) {
    const gk = 'tasks:' + tb.dataset.taskCampus;
    if (ENV_GROUPS[gk]) popupForEnv(gk);
    else showPopup(D.geo3d.camera[tb.dataset.taskCampus] ? [D.geo3d.camera[tb.dataset.taskCampus].lng, D.geo3d.camera[tb.dataset.taskCampus].lat] : map.getCenter(),
      `<b>No simulated task stands at this campus</b><br><span class="src">none in tasks/registry/tasks.json</span>`);
  }
});
const flySel = document.getElementById('flySel');
flySel.insertAdjacentHTML('beforeend', D.geo3d.tour.map((k) =>
  `<option value="${k}">${ESC(D.rollups[k].name)} — ${D.geo3d.camera[k].halls} halls</option>`).join(''));
flySel.addEventListener('change', () => { if (flySel.value) { stopTour(); flyToCampus(flySel.value); } });

const tour = { on: false, idx: -1, campus: null, timer: null, visited: [] };
const tourBtn = document.getElementById('tourBtn');
function tourStep() {
  if (!tour.on) return;
  tour.idx++;
  if (tour.idx >= D.geo3d.tour.length) {
    stopTour();
    map.fitBounds(NETWORK_BOUNDS, { padding: fitPadding(), pitch: 0, bearing: 0, duration: REDUCED ? 0 : 1800 });
    return;
  }
  tour.campus = D.geo3d.tour[tour.idx];
  tour.visited.push(tour.campus);
  flySel.value = tour.campus;
  map.once('moveend', () => { if (tour.on) tour.timer = setTimeout(tourStep, TOUR_DWELL_MS); });
  flyToCampus(tour.campus, { duration: 5200 });
}
function startTour() {
  if (currentPopup) currentPopup.remove();
  Object.assign(tour, { on: true, idx: -1, campus: null, visited: [] });
  tourBtn.setAttribute('aria-pressed', 'true'); tourBtn.textContent = '■ Stop tour';
  tourStep();
}
function stopTour() {
  if (!tour.on) return;
  tour.on = false; clearTimeout(tour.timer); tour.timer = null;
  tourBtn.setAttribute('aria-pressed', 'false'); tourBtn.textContent = '▶ Tour';
}
tourBtn.addEventListener('click', () => (tour.on ? stopTour() : startTour()));
// a reader who grabs the map takes the camera back
map.on('dragstart', () => stopTour());

/* the layers panel: every toggle is a real checkbox with a label */
const LAYERS = [
  { key: 'campuses', label: 'Campuses', map: ['campuses'], cls: 'hide-campus', sw: '#E8A33D' },
  { key: 'halls3d', label: '3D halls and district outlines (SCHEMATIC)', map: ['halls3d', 'halls3d-edge', 'districts3d-fill', 'districts3d-line'], sw: 'hsl(210,50%,45%)' },
  { key: 'anchors', label: 'Anchors', map: ['anchors'], sw: '#41C4D4' },
  { key: 'routes', label: 'Great-circle routes and city frames', map: ['routes', 'frames', 'frames-fill'], sw: '#E8A33D' },
  { key: 'restoration', label: 'Bay Restoration sites', map: [], cls: 'hide-rest', sw: '#5CB584' },
  { key: 'worksites', label: 'Worksites', map: ['env-worksites'], sw: '#C98BE0' },
  { key: 'k12', label: 'K-12 districts (PROPOSED, at their campus)', map: ['env-k12'], sw: '#F2D16B' },
  { key: 'tasks', label: 'Simulated tasks (counted per campus)', map: ['env-tasks'], sw: '#5CB584' },
];
const layerOn = Object.fromEntries(LAYERS.map((l) => [l.key, true]));
document.getElementById('layerToggles').innerHTML = LAYERS.map((l) =>
  `<label><input type="checkbox" checked data-layer="${l.key}"><span class="sw" style="background:${l.sw}"></span>${l.label}</label>`).join('');
document.getElementById('layerToggles').addEventListener('change', (e) => {
  const l = LAYERS.find((x) => x.key === e.target.dataset.layer);
  if (!l) return;
  layerOn[l.key] = e.target.checked;
  for (const id of l.map) map.setLayoutProperty(id, 'visibility', e.target.checked ? 'visible' : 'none');
  if (l.cls) document.getElementById('map').classList.toggle(l.cls, !e.target.checked);
  if (loaded) placeCampusLabels();
});
document.getElementById('g3dPlacement').textContent = D.geo3d.placement + '. ' + D.geo3d.projection;
document.getElementById('g3dCount').textContent = D.geo3d.counts.halls + ' halls on ' + D.geo3d.counts.campuses_with_halls
  + ' campuses (' + D.geo3d.counts.campuses_without_halls + ' list no halls: none drawn)';
document.getElementById('tasksHonesty').textContent = D.env.tasks.state.state === 'built'
  ? D.env.tasks.state.honesty : 'tasks/registry/tasks.json is not built in this tree, so no task is listed.';
document.getElementById('taskCampusList').innerHTML = D.geo3d.tour.map((k) => {
  const ts = tasksAt(k);
  return `<li data-task-row="${k}"><b>${ESC(D.rollups[k].name)}</b> — ${ts.length} tasks`
    + (ts.length ? ` <button type="button" class="popbtn" data-task-campus="${k}">list</button>` : '') + `</li>`;
}).join('');
document.getElementById('wildsHonesty').textContent = D.env.wildsHonesty;
document.getElementById('offGlobe').innerHTML =
  D.env.wildsOff.map((w) => `<li data-off="wilds:${w.id}"><b>${ESC(w.name)}</b> <span class="pv auth">${ESC(w.provenance)}</span>`
    + `<br>an authored landscape, only <i>inspired by</i> ${ESC(w.evokes)} (the ${ESC(D.rollups[w.campus].name)} region) - ${ESC(w.standing)}`
    + `<br><a class="door" href="${ESC(w.href)}">open the wild world</a></li>`).join('')
  + D.env.worksitesOff.map((w) => `<li data-off="worksite:${w.id}"><b>${ESC(w.title)}</b> <span class="pv">worksite</span>`
    + `<br>${ESC(w.why)}<br><a class="door" href="${ESC(w.href)}">open the worksite</a></li>`).join('')
  + D.env.tasks.off.map((t) => `<li data-off="task:${ESC(t.id)}">${taskBody(t)}<br><span class="src">${offWhy(t)}</span></li>`).join('');

let loaded = false;
map.on('load', () => { loaded = true; });
// test hook: state without poking MapLibre internals
window.__geomap = () => ({
  loaded, markers, candMarkers, restMarkers, projection: map.getProjection().type,
  covered: [...document.querySelectorAll('.maplibregl-marker-covered')].length,
  clusters: clusterMarkers.map((c) => c.getElement().dataset.sites.split(' ')),
  restLabelsShown: restItems.filter((r) => r.el.classList.contains('show-label')).map((r) => r.s.id),
  selected: selectedEl ? selectedEl.textContent || selectedEl.getAttribute('aria-label') : null,
  layers: map.getStyle().layers.map((l) => l.id),
  features: D.network.features.length,
  center: [Math.round(map.getCenter().lng * 10) / 10,
           Math.round(map.getCenter().lat * 10) / 10],
  zoom: Math.round(map.getZoom() * 10) / 10,
  popups: document.querySelectorAll('.maplibregl-popup').length,
  sat: { on: satOn, state: satState, tiles: D.imagery.tiles,
         visible: map.getLayoutProperty('sat', 'visibility') },
  parcels: { state: parcelState, count: parcelCount, campus: parcelCampus,
             authorities: Object.keys(D.sources).length },
  rollups: D.rollups, flagship: D.flagship, anchorProvenance: D.anchorProvenance,
  notWalkable: D.restorationSites.filter((s) => s.walkable !== true).map((s) => s.id),
  panel: openPanel,
  geopose: { total: D.geopose.counts.total,
             claimed: D.geopose.claimedCount, notClaimed: D.geopose.notClaimedCount,
             matchedFeatures: D.network.features.filter((f) => f.properties.geopose).length },
  status: statusEl.textContent,
  pitch: Math.round(map.getPitch()), bearing: Math.round(map.getBearing()),
  reducedMotion: REDUCED,
  tour: { on: tour.on, idx: tour.idx, campus: tour.campus, visited: tour.visited.slice(), order: D.geo3d.tour },
  geo3d: { halls: D.geo3d.halls.features.length, districts: D.geo3d.districts.features.length,
           counts: D.geo3d.counts,
           inView: loaded ? hallsInView() : 0 },
  layerOn: { ...layerOn },
  visibility: Object.fromEntries(['halls3d', 'env-worksites', 'env-k12', 'env-tasks', 'anchors', 'campuses']
    .map((id) => [id, map.getLayoutProperty(id, 'visibility') === 'none' ? 'none' : 'visible'])),
  env: { groups: Object.keys(ENV_GROUPS), worksitesOn: D.env.worksitesOn.length,
         worksitesOff: D.env.worksitesOff.length, k12: D.env.k12.length,
         tasksState: D.env.tasks.state.state, tasksOn: D.env.tasks.on.length, tasksOff: D.env.tasks.off.length,
         wildsOff: D.env.wildsOff.length },
});
</script>
__QUEST_TAIL__<script>__STYLE_JS__</script>
</body>
</html>
'''

out = HERE / 'trade_craft_geomap.html'
# the legend's campus split is the geo registry's own provenance count, read
# here rather than typed - a hub is a campus whose coordinate is AUTHORED
_n_hub = sum(1 for c in geo['campuses'].values() if c['provenance'] == 'AUTHORED')
_n_flag = len(geo['campuses']) - _n_hub
assert _n_hub > 0 and _n_flag > 0
page = page.replace('__STYLE_JS__', STYLE_JS).replace('__THEME_CSS__', THEME_CSS).replace('__SITENAV_CSS__', NAV_CSS).replace('__SITENAV__', NAV).replace('__QUEST_TAIL__', QUEST_TAIL)
page = (page.replace('__N_FLAGSHIP__', str(_n_flag)).replace('__N_HUB__', str(_n_hub))
        .replace('__N_POSES__', str(spatial['counts']['total']))
        .replace('__N_CLAIMED__', str(len(_spatial_claimed)))
        .replace('__N_NOTCLAIMED__', str(len(_spatial_not)))
        .replace('__GEOPOSE_HONESTY__', html.escape(spatial['honesty']['no_heights_or_headings']))
        .replace('__SITE_ROWS__', SITE_ROWS)
        .replace('__RESTORATION_NOT_AFFILIATED__', html.escape(restoration['honesty']['not_affiliated']))
        .replace('__GROUND_TRUTH_JS__', GROUND_TRUTH_JS))
assert '__N_' not in page, 'a legend count token went unreplaced'
assert '__GEOPOSE_HONESTY__' not in page, 'the geopose honesty token went unreplaced'
assert '__SITE_ROWS__' not in page and '__RESTORATION_NOT_AFFILIATED__' not in page, \
    'a restoration panel token went unreplaced'
assert '__GROUND_TRUTH_JS__' not in page, 'the ground-truth module token went unreplaced'
page = apply_seo(page, 'web/trade_craft_geomap.html', 'SmartCiti.X : Trade Craft Academy \u2014 network geomap',
    'The network geomap: every campus, anchor and city frame on a WGS84 globe, with provenance in every popup and no basemap tiles unless you ask.', 'page')
emit(out, page.replace('__DATA__', DATA), f"{len(network['features'])} features on the geomap")
