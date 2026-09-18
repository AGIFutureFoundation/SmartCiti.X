"""Shared ground-truth lookups: USGS elevation and USGS aerial imagery.

The 3D environment (`web/build_3d.py`) fires a live USGS 3DEP elevation
lookup and a live USGS National Map aerial-tile fetch per POI and per
restoration site, on request, never stored. The geomap (`web/build_geomap.py`)
is the one surface built to be a real WGS84 map, and it drew every campus,
anchor and restoration marker without ever offering the same ground truth —
only a blanket satellite-imagery toggle for the whole view.

This module is the ONE copy of that fetch/cache/render logic, so the two
pages cannot drift the way two hand-typed copies would: a trap guard fixed
here (the elevation service's inconsistent Feet/Meters typing, a point off
the DEM answering HTTP 200 with a non-JSON body, a malformed acquisition
date) lands in both pages at once, not in whichever one someone remembers to
patch. `web/mapdata.py` is the same pattern for the module-registry fold;
this is that pattern applied to ground truth.

Both callers already load their `D.elevation` and `D.imagery` config from
the SAME registry entry, `parcels/registry/parcels.json` (`elevation` /
`imagery`), so this module carries no registry data of its own — only the
functions that read `D.elevation` / `D.imagery` / `D.recHonesty` at runtime,
in the learner's own browser, and render "on request, live, never invented,
never stored" the same way in both pages.
"""

GROUND_TRUTH_JS = """\
/* ---- shared ground truth (web/groundtruth.py): USGS elevation (3DEP EPQS)
   and USGS National Map aerial imagery, on request only, live, never
   invented, never stored. One copy of this logic, inlined into every page
   that needs it (web/build_3d.py, web/build_geomap.py), so the two cannot
   drift into two different answers for the same coordinate. Every caller
   supplies D (that page's own data blob, holding D.elevation / D.imagery
   straight from parcels/registry/parcels.json) and the DOM to render into. */
const __gtElevCache = {};
function gtElevationLookup(D, lat, lng, cb) {
  const key = lat.toFixed(5) + ',' + lng.toFixed(5);
  if (__gtElevCache[key]) { cb(__gtElevCache[key]); return; }
  const q = D.elevation.query;
  const url = D.elevation.endpoint + '?x=' + encodeURIComponent(lng)
    + '&y=' + encodeURIComponent(lat) + '&units=' + q.units
    + '&wkid=' + q.wkid + '&includeDate=' + q.includeDate;
  const done = (o) => { __gtElevCache[key] = o; cb(o); };
  fetch(url).then((r) => r.text()).then((txt) => {
    let j = null;
    try { j = JSON.parse(txt); }
    catch (e) {
      done({ ok: false, why: 'The elevation service returned a non-JSON '
        + 'body for this point, which is how it reports a location '
        + 'outside its coverage.' });
      return;
    }
    const v = j && j.value;
    const num = typeof v === 'string' ? parseFloat(v) : v;
    if (num == null || !isFinite(num)) {
      done({ ok: false, why: 'No elevation is published for this coordinate.' });
      return;
    }
    done({ ok: true, feet: num,
      res: j.resolution == null ? null : j.resolution,
      acquired: (j.attributes && j.attributes.AcquisitionDate) || null });
  }).catch(() => done({ ok: false,
    why: 'The elevation service could not be reached from here.' }));
}
// The result HTML a lookup renders into, at either a full (12px) or a
// compact (10.5px) size — the same two sizes build_3d.py's own city-POI
// panel and its restoration-site rows used before this module existed.
function gtElevationHTML(D, o, small) {
  const fs = small ? '10.5px' : '12px';
  return o.ok
    ? `<span class="chip" style="font-size:${fs};border-color:var(--steel);color:var(--steel)">`
      + `${Math.round(o.feet)} ft</span>`
      + `<span style="color:var(--muted);font-size:${fs}"> USGS 3DEP ground `
      + `elevation at this coordinate${o.res ? ` · ${o.res} ft resolution` : ''}`
      + `${o.acquired ? ` · surveyed ${o.acquired}` : ''}. `
      + D.elevation.scope + `</span>`
    : `<span style="color:var(--crit);font-size:${fs}">${o.why}</span>`;
}
// Renders a lookup's result straight into a container element, the shape
// both pages' click handlers want: show "looking up...", fetch, replace.
function gtElevationInto(container, D, lat, lng, small) {
  if (!container) return;
  container.innerHTML = `<span style="font-size:${small ? '10.5px' : '12px'};color:var(--muted)"> looking up…</span>`;
  gtElevationLookup(D, lat, lng, (o) => { container.innerHTML = gtElevationHTML(D, o, small); });
}
function gtSingleTileUrl(D, lat, lng, z, tilesOverride) {
  const n = 2 ** z;
  const x = Math.floor((lng + 180) / 360 * n);
  const la = lat * Math.PI / 180;
  const y = Math.floor((1 - Math.log(Math.tan(la) + 1 / Math.cos(la)) / Math.PI) / 2 * n);
  return (tilesOverride ?? D.imagery.tiles).replace('{z}', z).replace('{y}', y).replace('{x}', x);
}
// A single orthoimagery tile at (lat, lng), loaded on click into `box` —
// the same 170x170 thumbnail treatment build_3d.py's restoration-site rows
// used, now shared. tilesOverride lets a page honour its own `?imagery=`
// operator override (build_3d.py's SAT_TILES) without a second copy of the
// tile-math above.
function gtAerialInto(box, D, lat, lng, tilesOverride) {
  if (!box) return;
  box.innerHTML = `<span style="font-size:10.5px;color:var(--muted)">Asking ${D.imagery.authority} for orthoimagery…</span>`;
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.style.cssText = 'display:block;width:170px;height:170px;border-radius:6px;'
    + 'margin-top:4px;border:1px solid var(--rule);object-fit:cover';
  img.onload = () => {
    box.innerHTML = '';
    box.appendChild(img);
    const cap = document.createElement('div');
    cap.style.cssText = 'font-size:10px;color:var(--muted);margin-top:2px;max-width:170px';
    cap.textContent = D.imagery.attribution + ' - ' + D.imagery.licence + '. ' + D.recHonesty.fidelity;
    box.appendChild(cap);
  };
  img.onerror = () => {
    box.innerHTML = `<span style="font-size:10.5px;color:var(--crit)">Orthoimagery did not answer from `
      + `this network. ${D.recHonesty.availability}</span>`;
  };
  img.src = gtSingleTileUrl(D, lat, lng, D.imagery.zoom.max, tilesOverride);
}
"""
