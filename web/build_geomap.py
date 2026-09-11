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
geo = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))
manifest = json.load(open(ROOT / 'pack/manifest.json'))
L = manifest['ledger']

DATA = json.dumps({
    'network': network,
    'city': geo['city'],
    'honesty': geo['honesty'],
    'halls': L['halls'],
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
</div>
<div id="map"></div>
<div id="legend">
  <b>The geo registry, drawn</b><br>
  <span class="dot" style="background:var(--mark)"></span>campus (RECORDED/DERIVED siting)<br>
  <span class="dot" style="background:var(--steel)"></span>anchor — RECORDED from Locator.X<br>
  <span class="dot" style="background:none;border:1.5px dashed var(--mark);border-radius:0"></span>great-circle route — DERIVED<br>
  <span class="dot" style="background:none;border:1px solid var(--steel);border-radius:0"></span>city frame — RECORDED
</div>
<div id="honesty"></div>
<script id="data" type="application/json">__DATA__</script>
<script src="vendor/maplibre/maplibre-gl.js"></script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
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
      grat: { type: 'geojson', data: grat },
      net: { type: 'geojson', data: D.network },
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#0C1113' } },
      { id: 'grat', type: 'line', source: 'grat',
        paint: { 'line-color': '#1c262b', 'line-width': 1 } },
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

let loaded = false;
map.on('load', () => { loaded = true; });
// test hook: state without poking MapLibre internals
window.__geomap = () => ({
  loaded, markers,
  layers: map.getStyle().layers.map((l) => l.id),
  features: D.network.features.length,
  center: [Math.round(map.getCenter().lng * 10) / 10,
           Math.round(map.getCenter().lat * 10) / 10],
  zoom: Math.round(map.getZoom() * 10) / 10,
  popups: document.querySelectorAll('.maplibregl-popup').length,
});
</script>
</body>
</html>
'''

out = HERE / 'trade_craft_geomap.html'
out.write_text(page.replace('__DATA__', DATA))
print(f"written: {len(out.read_text()):,} bytes | "
      f"{len(network['features'])} features on the geomap")
