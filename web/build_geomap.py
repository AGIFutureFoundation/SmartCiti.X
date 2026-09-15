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
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

network = json.load(open(ROOT / 'geo/registry/network.geojson'))
parcels = json.load(open(ROOT / 'parcels/registry/parcels.json'))
geo = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))
manifest = json.load(open(ROOT / 'pack/manifest.json'))
roadmap = json.load(open(ROOT / 'roadmap/registry/roadmap.json'))
restoration = json.load(open(ROOT / 'restoration/registry/restoration.json'))
L = manifest['ledger']

DATA = json.dumps({
    'network': network,
    'city': geo['city'],
    'honesty': geo['honesty'],
    'halls': L['halls'],
    'imagery': parcels['imagery'],
    'sources': parcels['sources'],
    'contract': parcels['contract'],
    'recHonesty': parcels['honesty'],
    # the roadmap's five candidates: real AUTHORED coordinates, the same
    # tier a Wikipedia infobox carries - this map is the one place they
    # can be shown at their own true position rather than a schematic
    # bearing, since every other feature here is already lat/lng
    'candidates': {k: {'name': c['name'], 'city': c['city'],
                       'region': c['region'], 'lat': c['lat'], 'lng': c['lng'],
                       'districts': c['districts'], 'why': c['why']}
                   for k, c in roadmap['candidates'].items()},
    'roadmapHonesty': {k: roadmap['honesty'][k]
                       for k in ('not_a_claim_of_content', 'provenance_tiers')},
    # real Bay Restoration Authority sites - AUTHORED coordinates (this
    # build reaches no network host, so nothing here is cross-checked
    # against sfbayrestore.org live), each with its own source link
    'restorationSites': [s for s in restoration['sites'] if s['pin']],
    'restorationHonesty': {k: restoration['honesty'][k]
                           for k in ('not_affiliated', 'provenance')},
}, ensure_ascii=False, separators=(',', ':'))

page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartCiti.X : Trade Craft Academy — network geomap</title>
<link rel="stylesheet" href="vendor/maplibre/maplibre-gl.css">
<style>
:root{
  --plate:#12181B; --panel:#182023; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --steel:#41C4D4; --good:#5CB584;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.5 "IBM Plex Sans",system-ui,sans-serif;overflow:hidden}
#bar{position:fixed;top:0;left:0;right:0;z-index:5;display:flex;flex-wrap:wrap;
  gap:8px 14px;align-items:center;padding:10px 16px;
  background:color-mix(in oklab, var(--plate) 88%, transparent);
  border-bottom:2px solid var(--mark);backdrop-filter:blur(6px)}
#bar .brand{font:700 19px/1 "Barlow Condensed",system-ui,sans-serif;white-space:nowrap}
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
  border:1.5px solid #12181B;cursor:pointer}
.candidate-marker{background:transparent;color:var(--muted);border-radius:999px;
  padding:1px 8px;font:600 11px "Barlow Condensed",sans-serif;white-space:nowrap;
  border:1.5px dashed var(--muted);cursor:pointer}
.restoration-marker{background:var(--good);color:#0C1113;border-radius:999px;
  padding:2px 9px;font:600 12px "Barlow Condensed",sans-serif;white-space:nowrap;
  border:1.5px solid #0C1113;cursor:pointer}
.maplibregl-popup-content{background:var(--panel)!important;color:var(--ink)!important;
  border:1px solid var(--rule);border-radius:9px;font:12.5px/1.45 "IBM Plex Sans",sans-serif;
  padding:10px 13px!important;max-width:270px}
.maplibregl-popup-tip{border-top-color:var(--panel)!important;
  border-bottom-color:var(--panel)!important}
.pv{display:inline-block;border:1px solid var(--rule);border-radius:999px;
  padding:0 7px;font-size:10.5px;color:var(--muted);margin:2px 4px 4px 0}
.pv.rec{color:var(--good);border-color:var(--good)}
.src{color:var(--muted);font-size:10.5px}
@media(pointer:coarse){.barbtn{min-height:42px}#honesty{display:none}}
</style>
</head>
<body>
<div id="bar">
  <span class="brand">SmartCiti<span class="x">.X</span> : Trade Craft Academy</span>
  <a href="trade_craft_3d.html">⬡ 3D environment</a>
  <a href="trade_craft_interactive.html">▦ interactive map</a>
  <button class="barbtn" data-fit="network">⌂ Network</button>
  <button class="barbtn" data-fit="bay">Bay Area</button>
  <button class="barbtn" data-fit="nola">New Orleans</button>
  <button class="barbtn" id="satBtn">🛰️ Imagery</button>
  <button class="barbtn" id="parBtn">▦ Footprints</button>
</div>
<div id="map"></div>
<div id="legend">
  <b>The geo registry, drawn</b><br>
  <span class="dot" style="background:var(--mark)"></span>campus — RECORDED/DERIVED for the three flagship campuses, AUTHORED for the two hub campuses<br>
  <span class="dot" style="background:var(--steel)"></span>anchor — RECORDED from Locator.X near the flagship campuses, AUTHORED near the hub campuses (click a dot for the one that applies)<br>
  <span class="dot" style="background:none;border:1.5px dashed var(--mark);border-radius:0"></span>great-circle route — DERIVED<br>
  <span class="dot" style="background:none;border:1px solid var(--steel);border-radius:0"></span>city frame — RECORDED for the three flagship campuses, AUTHORED for the two hub campuses<br>
  <span class="dot" style="background:none;border:1.5px dashed var(--muted)"></span>roadmap candidate — AUTHORED, not built<br>
  <span class="dot" style="background:var(--good)"></span>Bay Restoration site — real project, not affiliated with this bundle
</div>
<div id="honesty"></div>
<script id="data" type="application/json">__DATA__</script>
<script src="vendor/maplibre/maplibre-gl.js"></script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
// operator overrides: a self-hosted mirror of either source. They also
// let the harness prove the drawing paths without the public services.
const qs = new URLSearchParams(location.search);
if (qs.get('imagery')) D.imagery.tiles = qs.get('imagery');
const RECORDS_OVERRIDE = qs.get('records');
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
      { id: 'anchors', type: 'circle', source: 'net',
        filter: ['==', ['get', 'kind'], 'anchor'],
        paint: { 'circle-radius': 4.5, 'circle-color': '#41C4D4',
                 'circle-stroke-color': '#0C1113', 'circle-stroke-width': 1.5 } },
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
for (const f of D.network.features.filter((x) => x.properties.slug)) {
  const el = document.createElement('div');
  el.className = 'campus-marker';
  el.textContent = f.properties.name;
  el.addEventListener('click', (ev) => { ev.stopPropagation(); popupFor(f); });
  new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [0, -10] })
    .setLngLat(f.geometry.coordinates).addTo(map);
  markers++;
}

/* the five roadmap candidates - real AUTHORED coordinates, dashed to
   match the labels doctrine ("the dashed outline is the claim"), never
   drawn into D.network itself: this map's own network.geojson source
   states only the built network, and candidates are not that */
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
  el.className = 'restoration-marker';
  el.textContent = s.name;
  el.addEventListener('click', (ev) => { ev.stopPropagation(); popupForRestoration(s); });
  new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [0, -10] })
    .setLngLat([s.lng, s.lat]).addTo(map);
  restMarkers++;
}
function popupForRestoration(s) {
  const wf = s.workforce
    ? `<br><b>Workforce pathway:</b> ${s.workforce_note}` : '';
  new maplibregl.Popup({ closeButton: false })
    .setLngLat([s.lng, s.lat])
    .setHTML(`<b>${s.name}</b><br><span class="pv rec">real project</span>`
      + `<span class="pv">AUTHORED coordinate</span>`
      + `<br>${s.org}<br>${s.city}, ${s.county} · ${s.habitat}<br>${s.scale}`
      + wf
      + `<br><a href="${s.source_url}" target="_blank" rel="noopener" class="src">${s.source_url}</a>`
      + `<br><span class="src">${D.restorationHonesty.not_affiliated}</span>`)
    .addTo(map);
}

function popupFor(f, lngLat) {
  const p = f.properties;
  const at = lngLat ?? (f.geometry.type === 'Point'
    ? f.geometry.coordinates : map.getCenter());
  const chips = `<span class="pv ${p.provenance === 'RECORDED' ? 'rec' : ''}">${p.provenance}</span>`
    + (p.km !== undefined ? `<span class="pv">${p.km} km</span>` : '')
    + (p.bearing_deg !== undefined ? `<span class="pv">${p.bearing_deg}°</span>` : '');
  new maplibregl.Popup({ closeButton: false })
    .setLngLat(at)
    .setHTML(`<b>${p.name ?? (p.kind === 'route'
        ? p.from + ' ↔ ' + p.to : 'city frame · ' + p.campus)}</b><br>${chips}`
      + (p.halls ? `<br>${p.halls} halls · ${p.districts} districts · ${p.city}, ${p.region}` : '')
      + (p.blurb ? `<br>${p.blurb}` : '')
      + `<br><span class="src">${p.source}</span>`)
    .addTo(map);
}
for (const layer of ['campuses', 'anchors', 'routes', 'frames']) {
  map.on('click', layer, (e) => popupFor(e.features[0], e.lngLat));
  map.on('mouseenter', layer, () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', layer, () => { map.getCanvas().style.cursor = ''; });
}

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
  status: statusEl.textContent,
});
</script>
</body>
</html>
'''

out = HERE / 'trade_craft_geomap.html'
out.write_text(page.replace('__DATA__', DATA))
print(f"written: {len(out.read_text()):,} bytes | "
      f"{len(network['features'])} features on the geomap")
