# The spatial fabric

A *spatial fabric*, in the sense the Metaverse Standards Forum's Open
Metaverse Browser Initiative (OMBI) uses the phrase, is the metaverse
equivalent of a website: a mapped coordinate space containing content and
services, self-hosted, accessed by proximity, composed with other fabrics
by a browser through a multi-origin scene graph with per-branch
ownership. `spatial/` publishes the Academy as one — as static files a
plain web server serves next to the site — and draws its honesty line in
exactly two places.

## Claimed: OGC GeoPose 1.0

`geopose-1.0` — Open Geospatial Consortium (OGC 21-056r11). Basic-YPR poses for every campus, institution anchor and pinned restoration site (spatial/registry/geopose.json), horizontal position at its source provenance, height and heading honestly zero-with-UNKNOWN. Consumers this pack can
defend: any application/geopose+json reader, OSCP GeoPose Protocol clients.

OGC GeoPose 1.0 (OGC 21-056r11) is a published standard with a confirmed Basic-YPR JSON encoding, and it is claimed outright: every pose in geopose.json is exactly {position: {lat, lon, h}, orientation: {yaw, pitch, roll}}, lat/lon in degrees, h in metres, angles in degrees, LTP-ENU inner frame. The horizontal position is copied at build time from the registry that owns it and carries that registry's own provenance word (RECORDED / DERIVED / AUTHORED) and source string.

this bundle holds no height and no heading for any campus, anchor or site - elevation exists only as an on-request live USGS 3DEP lookup in the learner's own browser, never stored - so every pose emits h = 0.0 and yaw = pitch = roll = 0 with an explicit UNKNOWN sidecar beside it. A zero here is a placeholder, never a measurement, and no height or heading is invented to fill the slot.

Every pose in `spatial/registry/geopose.json` is the encoding exactly
(`OGC GeoPose 1.0 Basic-YPR, OGC 21-056r11, application/geopose+json`):

```json
{
 "position": {
  "lat": 37.8235,
  "lon": -122.3705,
  "h": 0.0
 },
 "orientation": {
  "yaw": 0,
  "pitch": 0,
  "roll": 0
 }
}
```

with this sidecar beside it, plus the horizontal position's real
provenance word and source string copied from the registry that owns it:

```json
{
 "h_provenance": "UNKNOWN - not held by this bundle; 0.0 is a placeholder, not a measurement",
 "orientation_provenance": "UNKNOWN - no heading is recorded; 0 is a placeholder"
}
```

### The 89 poses — 10 campuses, 69 anchors, 10 restoration sites

| Kind | Subject | Campus | lat, lon | Horizontal provenance | Walkable |
|---|---|---|---|---|---|
| Campus | Treasure Island Campus | Treasure Island Campus | 37.8235, -122.3705 | DERIVED | — |
| Campus | Oakland Waterfront Campus | Oakland Waterfront Campus | 37.8044, -122.2712 | RECORDED | — |
| Campus | Crescent Works Campus | Crescent Works Campus | 29.9511, -90.0715 | DERIVED | — |
| Campus | Bayou Energy Hub | Bayou Energy Hub | 29.7604, -95.3698 | AUTHORED | — |
| Campus | Loop Rail Hub | Loop Rail Hub | 41.8781, -87.6298 | AUTHORED | — |
| Campus | Sound Aerospace Hub | Sound Aerospace Hub | 47.6062, -122.3321 | AUTHORED | — |
| Campus | Three Rivers Steel Hub | Three Rivers Steel Hub | 40.4406, -79.9959 | AUTHORED | — |
| Campus | Front Range Mining Hub | Front Range Mining Hub | 39.7392, -104.9903 | AUTHORED | — |
| Campus | Biscayne Coastal Hub | Biscayne Coastal Hub | 25.7617, -80.1918 | AUTHORED | — |
| Campus | Motor City Hub | Motor City Hub | 42.3314, -83.0458 | AUTHORED | — |
| Institution / city anchor | San Francisco | Treasure Island Campus | 37.7749, -122.4194 | RECORDED | — |
| Institution / city anchor | Emeryville | Treasure Island Campus | 37.8313, -122.2852 | RECORDED | — |
| Institution / city anchor | Oakland | Treasure Island Campus | 37.8044, -122.2712 | RECORDED | — |
| Institution / city anchor | Tiburon | Treasure Island Campus | 37.8735, -122.4566 | RECORDED | — |
| Institution / city anchor | Albany | Treasure Island Campus | 37.8869, -122.2978 | RECORDED | — |
| Institution / city anchor | Berkeley | Treasure Island Campus | 37.8716, -122.2727 | RECORDED | — |
| Institution / city anchor | Sausalito | Treasure Island Campus | 37.859, -122.4853 | RECORDED | — |
| Institution / city anchor | El Cerrito | Treasure Island Campus | 37.9158, -122.3108 | RECORDED | — |
| Institution / city anchor | Piedmont | Treasure Island Campus | 37.8244, -122.2316 | RECORDED | — |
| Institution / city anchor | Richmond | Treasure Island Campus | 37.9358, -122.3477 | RECORDED | — |
| Institution / city anchor | Alameda | Treasure Island Campus | 37.7652, -122.2416 | RECORDED | — |
| Institution / city anchor | Daly City | Treasure Island Campus | 37.6879, -122.4702 | RECORDED | — |
| Institution / city anchor | Orinda | Treasure Island Campus | 37.8771, -122.1797 | RECORDED | — |
| Institution / city anchor | Mill Valley | Treasure Island Campus | 37.906, -122.545 | RECORDED | — |
| Institution / city anchor | South San Francisco | Treasure Island Campus | 37.6547, -122.4077 | RECORDED | — |
| Institution / city anchor | San Leandro | Treasure Island Campus | 37.7249, -122.1561 | RECORDED | — |
| Institution / city anchor | San Rafael | Treasure Island Campus | 37.9735, -122.5311 | RECORDED | — |
| Institution / city anchor | Emeryville | Oakland Waterfront Campus | 37.8313, -122.2852 | RECORDED | — |
| Institution / city anchor | Piedmont | Oakland Waterfront Campus | 37.8244, -122.2316 | RECORDED | — |
| Institution / city anchor | Alameda | Oakland Waterfront Campus | 37.7652, -122.2416 | RECORDED | — |
| Institution / city anchor | Berkeley | Oakland Waterfront Campus | 37.8716, -122.2727 | RECORDED | — |
| Institution / city anchor | Albany | Oakland Waterfront Campus | 37.8869, -122.2978 | RECORDED | — |
| Institution / city anchor | Orinda | Oakland Waterfront Campus | 37.8771, -122.1797 | RECORDED | — |
| Institution / city anchor | El Cerrito | Oakland Waterfront Campus | 37.9158, -122.3108 | RECORDED | — |
| Institution / city anchor | San Francisco | Oakland Waterfront Campus | 37.7749, -122.4194 | RECORDED | — |
| Institution / city anchor | San Leandro | Oakland Waterfront Campus | 37.7249, -122.1561 | RECORDED | — |
| Institution / city anchor | Richmond | Oakland Waterfront Campus | 37.9358, -122.3477 | RECORDED | — |
| Institution / city anchor | Lafayette | Oakland Waterfront Campus | 37.8858, -122.118 | RECORDED | — |
| Institution / city anchor | Tiburon | Oakland Waterfront Campus | 37.8735, -122.4566 | RECORDED | — |
| Institution / city anchor | Sausalito | Oakland Waterfront Campus | 37.859, -122.4853 | RECORDED | — |
| Institution / city anchor | Castro Valley | Oakland Waterfront Campus | 37.6941, -122.0864 | RECORDED | — |
| Institution / city anchor | South San Francisco | Oakland Waterfront Campus | 37.6547, -122.4077 | RECORDED | — |
| Institution / city anchor | Walnut Creek | Oakland Waterfront Campus | 37.9101, -122.0652 | RECORDED | — |
| Institution / city anchor | Daly City | Oakland Waterfront Campus | 37.6879, -122.4702 | RECORDED | — |
| Institution / city anchor | Tulane University | Crescent Works Campus | 29.9404, -90.1207 | RECORDED | — |
| Institution / city anchor | Xavier University | Crescent Works Campus | 29.9649, -90.1073 | RECORDED | — |
| Institution / city anchor | University of New Orleans | Crescent Works Campus | 30.0288, -90.0664 | RECORDED | — |
| Institution / city anchor | Delgado Community College | Crescent Works Campus | 29.9814, -90.105 | RECORDED | — |
| Institution / city anchor | Loyola University | Crescent Works Campus | 29.9351, -90.1223 | RECORDED | — |
| Institution / city anchor | Dillard University | Crescent Works Campus | 29.9903, -90.0517 | RECORDED | — |
| Institution / city anchor | SUNO | Crescent Works Campus | 30.0421, -90.033 | RECORDED | — |
| Institution / city anchor | Port of Houston Authority | Bayou Energy Hub | 29.735, -95.27 | AUTHORED | — |
| Institution / city anchor | University of Houston | Bayou Energy Hub | 29.7199, -95.3422 | AUTHORED | — |
| Institution / city anchor | San Jacinto College | Bayou Energy Hub | 29.691, -95.183 | AUTHORED | — |
| Institution / city anchor | Houston Community College | Bayou Energy Hub | 29.7241, -95.3775 | AUTHORED | — |
| Institution / city anchor | Chicago Union Station | Loop Rail Hub | 41.8789, -87.6359 | AUTHORED | — |
| Institution / city anchor | Navy Pier | Loop Rail Hub | 41.8917, -87.6086 | AUTHORED | — |
| Institution / city anchor | University of Illinois Chicago | Loop Rail Hub | 41.8708, -87.6505 | AUTHORED | — |
| Institution / city anchor | Richard J. Daley College | Loop Rail Hub | 41.7648, -87.727 | AUTHORED | — |
| Institution / city anchor | Port of Seattle | Sound Aerospace Hub | 47.6087, -122.3428 | AUTHORED | — |
| Institution / city anchor | University of Washington | Sound Aerospace Hub | 47.6553, -122.3035 | AUTHORED | — |
| Institution / city anchor | Museum of Flight | Sound Aerospace Hub | 47.5185, -122.2971 | AUTHORED | — |
| Institution / city anchor | South Seattle College | Sound Aerospace Hub | 47.5495, -122.3576 | AUTHORED | — |
| Institution / city anchor | Port of Pittsburgh Commission | Three Rivers Steel Hub | 40.438, -79.9958 | AUTHORED | — |
| Institution / city anchor | Carnegie Mellon University | Three Rivers Steel Hub | 40.4443, -79.9436 | AUTHORED | — |
| Institution / city anchor | Carrie Blast Furnaces National Historic Landmark | Three Rivers Steel Hub | 40.4062, -79.8631 | AUTHORED | — |
| Institution / city anchor | Community College of Allegheny County | Three Rivers Steel Hub | 40.453, -80.009 | AUTHORED | — |
| Institution / city anchor | Colorado School of Mines | Front Range Mining Hub | 39.7503, -105.2211 | AUTHORED | — |
| Institution / city anchor | National Renewable Energy Laboratory | Front Range Mining Hub | 39.7407, -105.1686 | AUTHORED | — |
| Institution / city anchor | Denver Union Station | Front Range Mining Hub | 39.7539, -105.0011 | AUTHORED | — |
| Institution / city anchor | Community College of Denver | Front Range Mining Hub | 39.7444, -105.0064 | AUTHORED | — |
| Institution / city anchor | PortMiami | Biscayne Coastal Hub | 25.7716, -80.1719 | AUTHORED | — |
| Institution / city anchor | NOAA Atlantic Oceanographic and Meteorological Laboratory | Biscayne Coastal Hub | 25.7302, -80.1615 | AUTHORED | — |
| Institution / city anchor | University of Miami | Biscayne Coastal Hub | 25.7171, -80.2762 | AUTHORED | — |
| Institution / city anchor | Miami Dade College | Biscayne Coastal Hub | 25.7745, -80.1937 | AUTHORED | — |
| Institution / city anchor | Detroit/Wayne County Port Authority | Motor City Hub | 42.329, -83.0368 | AUTHORED | — |
| Institution / city anchor | Wayne State University | Motor City Hub | 42.3573, -83.071 | AUTHORED | — |
| Institution / city anchor | The Henry Ford | Motor City Hub | 42.3014, -83.2321 | AUTHORED | — |
| Institution / city anchor | Wayne County Community College District | Motor City Hub | 42.3277, -83.0574 | AUTHORED | — |
| Restoration site | Heron's Head Park Shoreline Resilience Project (Phases 1 and 2) | Treasure Island Campus | 37.7355, -122.3803 | AUTHORED | yes |
| Restoration site | Candlestick Point Stewardship Project (Phases 1 and 2) | Treasure Island Campus | 37.718, -122.375 | AUTHORED | yes |
| Restoration site | Bay Restoration: Youth Engagement and Service Learning in East Oakland | Oakland Waterfront Campus | 37.762, -122.178 | AUTHORED | yes |
| Restoration site | Alviso Shoreline Habitat Restoration | Oakland Waterfront Campus | 37.4266, -121.9765 | AUTHORED | yes |
| Restoration site | South Bay Salt Pond Restoration — ecotone levee (Phase 1) | Oakland Waterfront Campus | 37.612, -122.113 | AUTHORED | yes |
| Restoration site | Montezuma Tidal and Seasonal Wetlands Restoration Project | Oakland Waterfront Campus | 38.15, -121.95 | AUTHORED | yes |
| Restoration site | American Canyon Wetlands Restoration Plan | Oakland Waterfront Campus | 38.171, -122.26 | AUTHORED | yes |
| Restoration site | Restoring Wetland-Upland Transition Zone Habitat in the North Bay with STRAW | Oakland Waterfront Campus | 38.05, -122.53 | AUTHORED | yes |
| Restoration site | Hunters Point Naval Shipyard — EPA Superfund Site (Bayview-Hunters Point) | Treasure Island Campus | 37.728, -122.373 | AUTHORED | no — an actively litigated federal cleanup site is not something this platform can responsibly present as a place to stroll |
| Restoration site | Former Naval Station Treasure Island (NSTI) — Navy BRAC cleanup site (Treasure Island) | Treasure Island Campus | 37.824, -122.371 | AUTHORED | no — an active federal cleanup site with unresolved radiological criteria is not something this platform can responsibly present as a place to stroll |

### Honestly unposed — 1

| Program | Run by | Why no GeoPose |
|---|---|---|
| San Francisco Estuary Invasive Spartina Removal | San Francisco Estuary Invasive Spartina Project (multi-agency) | no GeoPose: the registry pins no single coordinate for this bay-wide program (pin: false, lat/lng null), and this build invents none |

## Not claimed: the OMBI fabric manifest, SOM and RMAP

the OMBI spatial-fabric manifest, the Scene Object Model (SOM) and RMAP are marked "OMBI - New" in the public deck and their normative texts were not reachable from this build, so fabric.json and som.json are SHAPED after the deck's vocabulary, not validated against a specification. They are registered in meta/registry/metaverse.json under not_claimed, with the reason, and never under standards.

| Shape | Why not claimed |
|---|---|
| `ombi-spatial-fabric` | the OMBI fabric manifest (spatial/registry/fabric.json) is shaped after the public deck and press, Q3 2026 - no normative specification was reachable from this build, so the shape is unvalidated, and it has not been loaded in Sneeze, Artemis or any other metaverse browser |
| `ombi-som` | the Scene Object Model (spatial/registry/som.json) is SOM-shaped - a multi-origin scene graph with per-branch ownership, authored from the deck's vocabulary - not conformant to a specification this build could read, and unverified in any browser |
| `rmap` | no RMAP endpoint, server or protocol is implemented: the fabric is static files, every service runs in-page with no network, and no DID is minted |

**The fabric manifest** (`spatial/registry/fabric.json`) — operator
*SmartCiti.X : Trade Craft Academy (powered by AGI Corp)*, origin *self-hosted static files*,
entry `web/trade_craft_3d.html`, identity `did: null`
(no DID is minted by this bundle). It names 10
places (one per campus, each with its GeoPose, district or hub kind, hall
count, atmosphere and walkable city layer),
112 anchored content doors (the existing
`avatar-glb` and `hall-glb` exports, `glTF 2.0 binary`, produced on
demand by the learner's own browser — never files sitting on disk),
23 embedded services and
66 external origins.

this fabric is static files a plain web server serves next to the site - the deck's own "publish 3D content like a website" point. No RMAP endpoint, no server, no WebSocket, no fetch at build time, no DID minted: the identity field is honestly null. Every service listed runs in-page with no network, and every anchored .glb is produced on demand by the learner's browser, not a file sitting on disk. Anchoring the bundle-wide services (advisors, Schools panel, restoration panel, training recorder) at the flagship campus is a DESIGN decision unions/registry/campuses.json owns (flagship: true on exactly one campus), not a fact about where anything physically is.

### The services — every one in-page, no network

| Service | Kind | What | Anchored at | Its own registry |
|---|---|---|---|---|
| `sim:crane-lift` | simulator | Tower Crane Lift | `campus:treasure-island` | `sims/registry/sims.json` |
| `sim:excavator-trench` | simulator | Excavator Trench Cut | `campus:oakland` | `sims/registry/sims.json` |
| `sim:forklift-run` | simulator | Forklift Yard Run | `campus:oakland` | `sims/registry/sims.json` |
| `sim:weld-bead` | simulator | Weld Bead Run | `campus:treasure-island` | `sims/registry/sims.json` |
| `sim:scaffold-bay` | simulator | Scaffold Bay Build | `campus:treasure-island` | `sims/registry/sims.json` |
| `sim:rigging-signals` | simulator | Rigging Signal Call | `campus:treasure-island` | `sims/registry/sims.json` |
| `sim:load-chart` | simulator | Load Chart Judgment | `campus:treasure-island` | `sims/registry/sims.json` |
| `sim:pressure-washer` | simulator | Pressure Washer Surface Clean | `campus:treasure-island` | `sims/registry/sims.json` |
| `sim:airless-sprayer` | simulator | Airless Paint Sprayer Finish | `campus:treasure-island` | `sims/registry/sims.json` |
| `sim:boom-lift` | simulator | Boom Lift Basket Work | `campus:treasure-island` | `sims/registry/sims.json` |
| `sim:overhead-crane` | simulator | Overhead Crane Shop Move | `campus:treasure-island` | `sims/registry/sims.json` |
| `advisors` | scripted-advisors | 9 scripted advisors, 35 fixed topics | `campus:treasure-island` | `agents/registry/advisors.json` |
| `schools-panel` | panel | Schools panel - gamified flipped classroom, 45 flipped units | `campus:treasure-island` | `schools/registry/schools.json` |
| `crib:structural` | toolroom-crib | Structural tool crib | `campus:treasure-island` | `tools/registry/toolcribs.json` |
| `crib:envelope` | toolroom-crib | Envelope & finish tool crib | `campus:treasure-island` | `tools/registry/toolcribs.json` |
| `crib:systems` | toolroom-crib | Building-systems tool crib | `campus:treasure-island` | `tools/registry/toolcribs.json` |
| `crib:energy` | toolroom-crib | Energy & utilities tool crib | `campus:new-orleans` | `tools/registry/toolcribs.json` |
| `crib:earthworks` | toolroom-crib | Earthworks & plant tool crib | `campus:oakland` | `tools/registry/toolcribs.json` |
| `crib:industry` | toolroom-crib | Heavy-industry tool crib | `campus:oakland` | `tools/registry/toolcribs.json` |
| `crib:transport` | toolroom-crib | Transport & mobility tool crib | `campus:oakland` | `tools/registry/toolcribs.json` |
| `crib:control` | toolroom-crib | Survey, safety & environment tool crib | `campus:new-orleans` | `tools/registry/toolcribs.json` |
| `restoration-panel` | panel | Bay Restoration panel - 11 sites, 3 field-skill tracks | `campus:treasure-island` | `restoration/registry/restoration.json` |
| `training-recorder` | recorder | training-data recorder - 4 episode kinds, device-local under tc-training | `campus:treasure-island` | `training/registry/training.json` |

## Other operators are other origins

every other operator this fabric points at - a restoration site's own organization, the US Navy, EPA Region 9 and California DTSC at Hunters Point, the US Navy, California DTSC and CDPH at Former Naval Station Treasure Island, a port authority, a university, a museum, a neighbouring city - is a separate origin: named, located by its own pose, and never content this fabric serves for them (served_by_this_fabric is false on every one). That is the SOM's per-branch ownership idea, and it is the same "not affiliated" line restoration/ and geo/ already hold. The 111 union halls' real organizations are deliberately NOT listed as origins: the halls here are SCHEMATIC training buildings named after a craft, not a union's premises.

**The SOM-shaped scene graph** (`spatial/registry/som.json`) has one
branch per origin: this fabric's own branch (owner
*SmartCiti.X : Trade Craft Academy (powered by AGI Corp)*, provenance tiers
AUTHORED, DERIVED, RECORDED, SCHEMATIC, SCRIPTED,
146 nodes) and
66 external branches. The invariant the
build and the suite both assert: every branch has exactly one owner; no external branch contains a place, content or service this fabric serves, and every node this fabric serves sits under its own branch - asserted by spatial/build.py and spatial/test.mjs

| External origin (owner) | Nodes | Provenance tiers |
|---|---|---|
| San Francisco | 2 | RECORDED |
| Emeryville | 2 | RECORDED |
| Oakland | 1 | RECORDED |
| Tiburon | 2 | RECORDED |
| Albany | 2 | RECORDED |
| Berkeley | 2 | RECORDED |
| Sausalito | 2 | RECORDED |
| El Cerrito | 2 | RECORDED |
| Piedmont | 2 | RECORDED |
| Richmond | 2 | RECORDED |
| Alameda | 2 | RECORDED |
| Daly City | 2 | RECORDED |
| Orinda | 2 | RECORDED |
| Mill Valley | 1 | RECORDED |
| South San Francisco | 2 | RECORDED |
| San Leandro | 2 | RECORDED |
| San Rafael | 1 | RECORDED |
| Lafayette | 1 | RECORDED |
| Castro Valley | 1 | RECORDED |
| Walnut Creek | 1 | RECORDED |
| Tulane University | 1 | RECORDED |
| Xavier University | 1 | RECORDED |
| University of New Orleans | 1 | RECORDED |
| Delgado Community College | 1 | RECORDED |
| Loyola University | 1 | RECORDED |
| Dillard University | 1 | RECORDED |
| SUNO | 1 | RECORDED |
| Port of Houston Authority | 1 | AUTHORED |
| University of Houston | 1 | AUTHORED |
| San Jacinto College | 1 | AUTHORED |
| Houston Community College | 1 | AUTHORED |
| Chicago Union Station | 1 | AUTHORED |
| Navy Pier | 1 | AUTHORED |
| University of Illinois Chicago | 1 | AUTHORED |
| Richard J. Daley College | 1 | AUTHORED |
| Port of Seattle | 1 | AUTHORED |
| University of Washington | 1 | AUTHORED |
| Museum of Flight | 1 | AUTHORED |
| South Seattle College | 1 | AUTHORED |
| Port of Pittsburgh Commission | 1 | AUTHORED |
| Carnegie Mellon University | 1 | AUTHORED |
| Carrie Blast Furnaces National Historic Landmark | 1 | AUTHORED |
| Community College of Allegheny County | 1 | AUTHORED |
| Colorado School of Mines | 1 | AUTHORED |
| National Renewable Energy Laboratory | 1 | AUTHORED |
| Denver Union Station | 1 | AUTHORED |
| Community College of Denver | 1 | AUTHORED |
| PortMiami | 1 | AUTHORED |
| NOAA Atlantic Oceanographic and Meteorological Laboratory | 1 | AUTHORED |
| University of Miami | 1 | AUTHORED |
| Miami Dade College | 1 | AUTHORED |
| Detroit/Wayne County Port Authority | 1 | AUTHORED |
| Wayne State University | 1 | AUTHORED |
| The Henry Ford | 1 | AUTHORED |
| Wayne County Community College District | 1 | AUTHORED |
| Port of San Francisco; Literacy for Environmental Justice | 1 | AUTHORED |
| California State Parks; community stewardship partners | 1 | AUTHORED |
| Planting Justice | 1 | AUTHORED |
| Grassroots Ecology | 1 | AUTHORED |
| South Bay Salt Pond Restoration Project (multi-agency) | 1 | AUTHORED |
| San Francisco Bay Restoration Authority (Measure AA) | 1 | AUTHORED |
| City of American Canyon | 1 | AUTHORED |
| Point Blue Conservation Science (STRAW program) | 1 | AUTHORED |
| San Francisco Estuary Invasive Spartina Project (multi-agency) | 1 | AUTHORED |
| US Navy (CERCLA lead agency for investigation and cleanup); US EPA Region 9 and California DTSC (oversight and enforcement of Navy cleanup activities) | 1 | AUTHORED |
| US Navy (BRAC / CERCLA lead agency for investigation and cleanup); California DTSC (lead regulator), California Department of Public Health (radiological matters) and the San Francisco Bay Regional Water Quality Control Board (oversight) | 1 | AUTHORED |

## Not loaded in any browser

nothing here has been opened in Sneeze, Artemis or any other metaverse browser. The only consumers this pack can defend are a reader of application/geopose+json and this bundle's own suite (spatial/test.mjs), which holds every pose against its source registry on every run.

## Sources

- The Case for the Metaverse Browser - Metaverse Standards Forum / OMBI / RP1 deck, Q3 2026 *(AUTHORED from the deck as supplied; the deck is not in this repository and this build fetched nothing)*
- Metaverse Standards Forum press release: Sneeze, the open metaverse browser engine, introduced June 15 2026 under the Apache 2.0 licence through the Open Metaverse Browser Initiative, RP1 lead architect and maintainer — https://metaverse-standards.org/news/press-releases/metaverse-standards-forum-introduces-sneeze-the-worlds-first-open-metaverse-browser-engine/ *(AUTHORED from public press; no code from that repository is vendored, run or read by this bundle)*
- RP1 launches Artemis, a native metaverse browser built on Sneeze, July 2026 — https://www.businesswire.com/news/home/20260706640660/en/RP1-Launches-Artemis-the-Worlds-First-Native-Metaverse-Browser *(AUTHORED from public press; this fabric has not been loaded in it)*
- OGC GeoPose 1.0 Data Exchange Standard, OGC 21-056r11, Basic-YPR and Basic-Quaternion JSON encodings, media type application/geopose+json *(the one published standard here, claimed; docs.ogc.org was not reachable from this build, the Basic-YPR encoding used is the one confirmed in the brief and in the OSCP GeoPose Protocol (github.com/OpenArCloud/oscp-geopose-protocol))*

Both files download from the [network dashboard](../web/trade_craft_dashboard.html).

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
