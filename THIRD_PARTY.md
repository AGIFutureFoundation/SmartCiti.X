# Third-party material

| What | From | License | Where it lives here |
|---|---|---|---|
| Three.js 0.160.0 (`three.module.min.js`, `OrbitControls`, `PointerLockControls`) | three.js (mrdoob and contributors) | MIT | vendored under `web/vendor/`, loaded by the 3D environment |
| Oakland's WGS84 coordinates | Locator.X city table (`src/app.js`, `CITIES`), AGI Future Foundation | Apache-2.0 | copied verbatim into `geo/build.py`, marked RECORDED, and cross-checked against the cited table whenever the Locator.X checkout is present |
| The RECORDED / DERIVED / SCHEMATIC provenance discipline | Locator.X rooms module (`src/rooms.js`), AGI Future Foundation | Apache-2.0 | adopted as the tagging vocabulary of the `geo/` and `surfaces/` registries — nothing is stated that the source does not support |
| 25-station BAC masonry curriculum and yard layout | the pre-rebrand yard application (this foundation's own prior work) | — | recovered as data in `archive/bac_yard_stations.json`, rebranded in `stations/` |
| USGS The National Map orthoimagery (`USGSImageryOnly`) | United States Geological Survey | public domain (work of the U.S. federal government) | **not vendored** — declared in `parcels/registry/parcels.json` and requested by the maps in the learner's own browser; credited on the page when shown |
| Parcel and building-footprint records | City of New Orleans (`data.nola.gov`), DataSF (SF Assessor roll), Alameda County Assessor | public records published for reuse by each authority | **not copied** — `parcels/` declares the authority, licence and bounded query; the maps fetch from the authority at view time and never store the result |
| Unity avatar systems **reviewed, not used**: UniVRM (VRM Consortium), Microsoft Rocketbox (Microsoft), Ready Player Me Unity SDK (Ready Player Me) | their GitHub repositories | MIT (each) | **no code or artwork vendored** — read from their own checkouts to choose an approach, recorded in `meta/registry/metaverse.json`. Only VRM's *humanoid bone naming vocabulary* is adopted, for the exported rig's node names |
| The walk bands and destination classes (800 m / 1.2 km; shops, eating, workplaces, care, learning, lodging) | Locator.X walk module (`src/walk.js`), AGI Future Foundation | Apache-2.0 | **no code copied** — the figures and class names are RECORDED into `geo/build.py`, cross-checked against the cited file whenever the Locator.X checkout is present, and carried with that module's own caveats (not Walk Score®; straight-line, not a street-network walk) |
| MapLibre GL JS 4.7.1 (`maplibre-gl.js`, `maplibre-gl.css`) | MapLibre contributors | BSD-3-Clause | vendored under `web/vendor/maplibre/`, loaded by the network geomap (`web/trade_craft_geomap.html`) |

Everything else in this repository is original to the bundle. No Mapbox
service, token or tile is used: the `geo/` registry ships plain WGS84
coordinates and standard GeoJSON (`geo/registry/campuses.geojson` and the
expanded `geo/registry/network.geojson`), the interchange format any
Mapbox/MapLibre-compatible stack consumes directly — and the geomap page
renders exactly that file over a generated graticule, with no basemap
tiles, so nothing appears on it that the registry does not state.
