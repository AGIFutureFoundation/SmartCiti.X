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
from sitenav import nav_html, labels as nav_labels, NAV_CSS  # noqa: E402
from groundtruth import GROUND_TRUTH_JS  # noqa: E402

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
    'flagship': FLAGSHIP,
    'restorationHonesty': {k: restoration['honesty'][k]
                           for k in ('not_affiliated', 'provenance')},
    # the spatial fabric this map's own features are described by
    # (spatial/registry/geopose.json) — every campus and anchor feature
    # above already carries its own `geopose` property; restoration-site
    # poses are looked up client-side by ref, since the pin filter above
    # already trims restorationSites to the ones a pose could exist for.
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
#stage{position:relative;flex:1 1 auto;min-height:0;transform:translateZ(0)}
body{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.5 "IBM Plex Sans",system-ui,sans-serif;overflow:hidden}
#bar{position:fixed;top:0;left:0;right:0;z-index:5;display:flex;flex-wrap:wrap;
  gap:8px 14px;align-items:center;padding:10px 16px;
  background:color-mix(in oklab, var(--plate) 88%, transparent);
  border-bottom:2px solid var(--mark);backdrop-filter:blur(6px)}
#bar .brand{margin:0;font:700 19px/1 "Barlow Condensed",system-ui,sans-serif;white-space:nowrap}
#bar .brand .x{color:var(--mark)}
#bar a{color:var(--steel);text-decoration:none;font-size:13px}
.barbtn{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:6px 11px;font:inherit;cursor:pointer;white-space:nowrap}
.barbtn:hover{border-color:var(--mark)}
#map{position:absolute;inset:0}
#honesty{position:fixed;right:14px;bottom:12px;z-index:5;max-width:340px;
  color:var(--muted);font-size:10.5px;text-align:end;opacity:.9;
  pointer-events:none}
#legend{position:fixed;left:14px;bottom:12px;z-index:5;
  background:color-mix(in oklab, var(--panel) 90%, transparent);
  border:1px solid var(--rule);border-radius:9px;padding:9px 13px;
  font-size:12px;color:var(--muted)}
#legend b{color:var(--ink)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-inline-end:5px}
.campus-marker{background:var(--mark);color:#12181B;border-radius:999px;
  padding:2px 9px;font:600 12px "Barlow Condensed",sans-serif;white-space:nowrap;
  border:1.5px solid #12181B;cursor:pointer;z-index:3}
.candidate-marker{background:transparent;color:var(--muted);border-radius:999px;
  padding:1px 8px;font:600 11px "Barlow Condensed",sans-serif;white-space:nowrap;
  border:1.5px dashed var(--muted);cursor:pointer}
.restoration-marker{background:var(--good);color:#0C1113;border-radius:999px;
  padding:2px 9px;font:600 12px "Barlow Condensed",sans-serif;white-space:nowrap;
  border:1.5px solid #0C1113;cursor:pointer;z-index:2}
.restoration-marker.env-monitoring{background:var(--steel)}
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
.panel{position:fixed;top:58px;right:14px;z-index:6;width:min(380px,calc(100vw - 28px));
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
.flag{background:var(--mark);color:#12181B;border-radius:4px;padding:0 5px;
  font:600 10.5px "Barlow Condensed",sans-serif;margin-inline-start:4px}
.anchor-swatch{display:inline-block;width:9px;height:9px;border-radius:50%;margin-inline-end:5px}
.anchor-swatch.rec{background:var(--steel)}
.anchor-swatch.auth{background:#12181B;border:1.5px solid var(--steel)}
@media(pointer:coarse){.barbtn{min-height:42px}#honesty{display:none}}
</style>
<style>__SITENAV_CSS__</style>
</head>
<body>
__SITENAV__<div id="stage">
<div id="bar">
  <h1 class="brand">SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
  <a href="trade_craft_3d.html">⬡ 3D environment</a>
  <a href="trade_craft_interactive.html">▦ interactive map</a>
  <button class="barbtn" data-fit="network">⌂ Network</button>
  <button class="barbtn" data-fit="bay">Bay Area</button>
  <button class="barbtn" data-fit="nola">New Orleans</button>
  <button class="barbtn" id="satBtn">🛰️ Imagery</button>
  <button class="barbtn" id="parBtn">▦ Footprints</button>
  <button class="barbtn" data-panel="campuses">☰ Campuses</button>
  <button class="barbtn" data-panel="sites">🌿 Restoration sites</button>
</div>
<div id="map"></div>
<section class="panel" id="campuses" aria-label="campus rollups">
  <h2>The campuses, rolled up from the registries</h2>
  <ul id="campusList"></ul>
  <p class="src">Halls per campus from unions/registry/campuses.json; a hall &ldquo;with a lesson&rdquo; has an entry in lessons/registry/lessons.json; a hall &ldquo;binding a seat&rdquo; appears in sims/registry/sims.json hall_bindings; flipped-classroom units are schools/registry/schools.json units on that campus&rsquo;s halls. Every figure is computed at build from those registries and rendered here from the page&rsquo;s own JSON.</p>
</section>
<section class="panel" id="sites" aria-label="Bay Restoration sites">
  <h2>Bay Restoration sites</h2>
  <ul id="siteList">__SITE_ROWS__</ul>
  <p class="src">__RESTORATION_NOT_AFFILIATED__</p>
</section>
<div id="legend">
  <b>The geo registry, drawn</b><br>
  <span class="dot" style="background:var(--mark)"></span>campus — RECORDED/DERIVED for the __N_FLAGSHIP__ flagship campuses, AUTHORED for the __N_HUB__ hub campuses<br>
  <span class="anchor-swatch rec"></span>anchor, <b>RECORDED</b> — <span data-anchor-count="RECORDED"></span> of <span data-anchor-count="total"></span>: the coordinate is copied from the source its popup cites<br>
  <span class="anchor-swatch auth"></span>anchor, <b>AUTHORED</b> — <span data-anchor-count="AUTHORED"></span> of <span data-anchor-count="total"></span>: typed from public record, no source fetched; the popup states this plainly<br>
  <span class="dot" style="background:none;border:1.5px dashed var(--mark);border-radius:0"></span>great-circle route — DERIVED<br>
  <span class="dot" style="background:none;border:1px solid var(--steel);border-radius:0"></span>city frame — RECORDED for the __N_FLAGSHIP__ flagship campuses, AUTHORED for the __N_HUB__ hub campuses<br>
  <span class="dot" style="background:none;border:1.5px dashed var(--muted)"></span>roadmap candidate — AUTHORED, not built<br>
  <span class="dot" style="background:var(--good)"></span>Bay Restoration site (habitat-restoration) — real project, not affiliated with this bundle<br>
  <span class="dot" style="background:var(--steel)"></span>Bay Restoration site (environmental-monitoring) — a real federal cleanup site (Hunters Point, NPL-listed and litigated; Treasure Island NSTI, a Navy BRAC cleanup, not NPL-listed); located but never rendered as a walkable scene<br>
  <span style="display:inline-block;width:9px;height:9px;border:1px solid var(--muted);border-radius:2px;margin-inline-end:5px;vertical-align:-1px"></span><span title="__GEOPOSE_HONESTY__">every campus, anchor and pinned restoration marker on this map also holds a <b>GeoPose 1.0</b> pose (__N_POSES__ total — __N_CLAIMED__ claimed standard / __N_NOTCLAIMED__ not-claimed OMBI shapes; click a marker for its own pose line; hover for the height/heading honesty line)</span>
</div>
<div id="honesty"></div>
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

const map = new maplibregl.Map({
  container: 'map',
  attributionControl: false,
  style: {
    version: 8,
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
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#0C1113' } },
      { id: 'sat', type: 'raster', source: 'sat',
        layout: { visibility: 'none' },
        paint: { 'raster-opacity': .85 } },
      { id: 'grat', type: 'line', source: 'grat',
        paint: { 'line-color': '#1c262b', 'line-width': 1 } },
      // RECORDED footprints, extruded as they arrive from the authority
      { id: 'parcels', type: 'fill-extrusion', source: 'parcels',
        paint: { 'fill-extrusion-color': '#41C4D4',
                 'fill-extrusion-opacity': .55,
                 'fill-extrusion-height': 9 } },
      { id: 'frames-fill', type: 'fill', source: 'net',
        filter: ['==', ['get', 'kind'], 'frame'],
        paint: { 'fill-color': '#41C4D4', 'fill-opacity': .05 } },
      { id: 'frames', type: 'line', source: 'net',
        filter: ['==', ['get', 'kind'], 'frame'],
        paint: { 'line-color': '#41C4D4', 'line-width': 1.2,
                 'line-opacity': .7 } },
      { id: 'routes', type: 'line', source: 'net',
        filter: ['==', ['get', 'kind'], 'route'],
        paint: { 'line-color': '#E8A33D', 'line-width': 1.6,
                 'line-dasharray': [2.5, 2] } },
      // the two provenance classes drawn apart: RECORDED solid steel,
      // AUTHORED a hollow ring - read from each feature's own `provenance`
      { id: 'anchors', type: 'circle', source: 'net',
        filter: ['==', ['get', 'kind'], 'anchor'],
        paint: { 'circle-radius': 4.5,
                 'circle-color': ['match', ['get', 'provenance'],
                                  'RECORDED', '#41C4D4', '#12181B'],
                 'circle-stroke-color': ['match', ['get', 'provenance'],
                                         'RECORDED', '#0C1113', '#41C4D4'],
                 'circle-stroke-width': 1.5 } },
      { id: 'campuses', type: 'circle', source: 'net',
        filter: ['has', 'slug'],
        paint: { 'circle-radius': 7, 'circle-color': '#E8A33D',
                 'circle-stroke-color': '#0C1113', 'circle-stroke-width': 2 } },
    ],
  },
  center: [-106, 34], zoom: 3.1,
});
map.addControl(new maplibregl.NavigationControl({ showCompass: false }));

/* campus labels as DOM markers - no glyph server needed */
let markers = 0;
const campusLabels = [];
for (const f of D.network.features.filter((x) => x.properties.slug)) {
  const el = document.createElement('div');
  el.className = 'campus-marker';
  el.textContent = f.properties.name;
  el.addEventListener('click', (ev) => { ev.stopPropagation(); popupFor(f); });
  campusLabels.push({ el, m: new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [0, -10] })
    .setLngLat(f.geometry.coordinates).addTo(map) });
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
  new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [0, -10] })
    .setLngLat([c.lng, c.lat]).addTo(map);
  candMarkers++;
}
function popupForCandidate(ck, c) {
  new maplibregl.Popup({ closeButton: false })
    .setLngLat([c.lng, c.lat])
    .setHTML(`<b>${c.name}</b><br><span class="pv">AUTHORED</span>`
      + `<span class="pv">proposed</span>`
      + `<br>${c.city}, ${c.region}<br>${c.why}`
      + `<br><span class="src">${D.roadmapHonesty.not_a_claim_of_content}</span>`)
    .addTo(map);
}

/* Bay Restoration sites: real, independently-run projects - AUTHORED
   coordinates on this map's side only, each linking to its own real
   source page rather than anything this bundle claims to run */
let restMarkers = 0;
for (const s of D.restorationSites) {
  const el = document.createElement('div');
  el.className = 'restoration-marker' + (s.category === 'environmental-monitoring' ? ' env-monitoring' : '');
  el.textContent = s.name;
  el.addEventListener('click', (ev) => { ev.stopPropagation(); popupForRestoration(s); });
  /* hung BELOW its point: a site that shares a campus's coordinates (Treasure
     Island) would otherwise sit on the campus label and swallow its clicks */
  new maplibregl.Marker({ element: el, anchor: 'top', offset: [0, 10] })
    .setLngLat([s.lng, s.lat]).addTo(map);
  restMarkers++;
}

/* campus labels that collide at the current zoom (Treasure Island and Oakland
   Waterfront sit a few kilometres apart, one pixel apart at the opening zoom)
   would leave one campus unclickable. Each label tries above its dot, then
   below, right and left, and takes the first slot that overlaps no label
   already placed and no restoration marker. When restoration markers fill
   every slot (the Bay at the opening zoom), it takes the first slot clear of
   other campus labels: campus labels stack above restoration markers, so only
   another campus label can take a campus's clicks. Only the label moves: the
   dot in the campuses layer stays on the campus's own coordinates. A label
   with no slot clear of other campus labels keeps its first slot, and the
   browser smoke reports it. */
function placeCampusLabels() {
  const hit = (r, q) => r.left < q.right && q.left < r.right && r.top < q.bottom && q.top < r.bottom;
  const rest = [...document.querySelectorAll('.restoration-marker')].map((e) => e.getBoundingClientRect());
  const placed = [];
  for (const c of campusLabels) {
    c.m.setOffset([0, -10]);
  }
  for (const c of campusLabels) {
    const w = c.el.offsetWidth, h = c.el.offsetHeight;
    const slots = [[0, -10], [0, 10 + h], [w / 2 + 12, h / 2], [-(w / 2 + 12), h / 2]];
    let clearOfAll = null, clearOfCampus = null;
    for (const o of slots) {
      c.m.setOffset(o);
      const r = c.el.getBoundingClientRect();
      if (placed.some((q) => hit(r, q))) continue;
      if (clearOfCampus === null) clearOfCampus = o;
      if (!rest.some((q) => hit(r, q))) { clearOfAll = o; break; }
    }
    c.m.setOffset(clearOfAll !== null ? clearOfAll : clearOfCampus !== null ? clearOfCampus : slots[0]);
    placed.push(c.el.getBoundingClientRect());
  }
}
map.on('load', placeCampusLabels);
map.on('zoomend', placeCampusLabels);
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
  new maplibregl.Popup({ closeButton: false })
    .setLngLat([s.lng, s.lat])
    .setHTML(`<b>${s.name}</b><br><span class="pv rec">real project</span>`
      + `<span class="pv">AUTHORED coordinate</span>` + cat
      + `<br>${s.org}<br>${s.city}, ${s.county} · ${s.habitat}<br>${s.scale}`
      + dis + wf + pt + pose + `<br>` + walkLine(s)
      + `<br><a href="${s.source_url}" target="_blank" rel="noopener" class="src">${s.source_url}</a>`
      + `<br><span class="src">${D.restorationHonesty.not_affiliated}</span>`
      + groundTruthButtons(s.lat, s.lng))
    .addTo(map);
}

function popupFor(f, lngLat) {
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
  new maplibregl.Popup({ closeButton: false })
    .setLngLat(at)
    .setHTML(`<b>${p.name ?? (p.kind === 'route'
        ? p.from + ' ↔ ' + p.to : 'city frame · ' + p.campus)}</b>${flag}<br>${chips}`
      + (p.halls ? `<br>${p.halls} halls · ${p.districts} districts · ${p.city}, ${p.region}` : '')
      + (p.slug ? rollupList(p.slug) : '')
      + (p.blurb ? `<br>${p.blurb}` : '')
      + geoposeLine(p.geopose) + anchorPv
      + `<br><span class="src">source: ${p.source}</span>` + gt)
    .addTo(map);
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
  }));

const FITS = {
  network: [[-126, 27], [-86, 41]],
  bay: [[D.city['treasure-island'].bounds.w, D.city['treasure-island'].bounds.s],
        [D.city['treasure-island'].bounds.e, D.city['treasure-island'].bounds.n]],
  nola: [[D.city['new-orleans'].bounds.w, D.city['new-orleans'].bounds.s],
         [D.city['new-orleans'].bounds.e, D.city['new-orleans'].bounds.n]],
};
document.querySelectorAll('[data-fit]').forEach((b) =>
  b.addEventListener('click', () =>
    map.fitBounds(FITS[b.dataset.fit], { padding: 60, duration: 700 })));

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
  document.getElementById('satBtn').style.borderColor =
    satOn ? 'var(--mark)' : 'var(--rule)';
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

let loaded = false;
map.on('load', () => { loaded = true; });
// test hook: state without poking MapLibre internals
window.__geomap = () => ({
  loaded, markers, candMarkers, restMarkers,
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
});
</script>
</body>
</html>
'''

out = HERE / 'trade_craft_geomap.html'
# the legend's campus split is the geo registry's own provenance count, read
# here rather than typed - a hub is a campus whose coordinate is AUTHORED
_n_hub = sum(1 for c in geo['campuses'].values() if c['provenance'] == 'AUTHORED')
_n_flag = len(geo['campuses']) - _n_hub
assert _n_hub > 0 and _n_flag > 0
page = page.replace('__SITENAV_CSS__', NAV_CSS).replace('__SITENAV__', NAV)
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
emit(out, page.replace('__DATA__', DATA), f"{len(network['features'])} features on the geomap")
