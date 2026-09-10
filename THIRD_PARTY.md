# Third-party material

| What | From | License | Where it lives here |
|---|---|---|---|
| Three.js 0.160.0 (`three.module.min.js`, `OrbitControls`, `PointerLockControls`) | three.js (mrdoob and contributors) | MIT | vendored under `web/vendor/`, loaded by the 3D environment |
| Oakland's WGS84 coordinates | Locator.X city table (`src/app.js`, `CITIES`), AGI Future Foundation | Apache-2.0 | copied verbatim into `geo/build.py`, marked RECORDED, and cross-checked against the cited table whenever the Locator.X checkout is present |
| The RECORDED / DERIVED / SCHEMATIC provenance discipline | Locator.X rooms module (`src/rooms.js`), AGI Future Foundation | Apache-2.0 | adopted as the tagging vocabulary of the `geo/` and `surfaces/` registries — nothing is stated that the source does not support |
| 25-station BAC masonry curriculum and yard layout | the pre-rebrand yard application (this foundation's own prior work) | — | recovered as data in `archive/bac_yard_stations.json`, rebranded in `stations/` |

Everything else in this repository is original to the bundle. No Mapbox
service, token or tile is used: the `geo/` registry ships plain WGS84
coordinates and standard GeoJSON (`geo/registry/campuses.geojson`), the
interchange format any Mapbox/MapLibre-compatible stack consumes directly.
