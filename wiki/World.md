# The world

Everything the environment is made of that is not a building: the sky, the
weather it is seen under, the ground it stands on, and the animals moving
through it.

## There is no texture file

no texture, photograph or artwork file exists in this repository and none is downloaded: every surface is a recipe - a base colour, a grain, an octave count and a relief depth - and the page generates the image and its normal map in the learner's own browser at boot. There is therefore no third-party artwork anywhere in the render.

That is the strongest thing this bundle can say about its own look, and it
is machine-checked: the suite reads the built page and fails if it so much
as mentions a texture loader or an image extension.

| Surface | Base | Octaves | Relief | Where it is laid |
|---|---|---|---|---|
| **Asphalt** | `#1c2124` | 5 | 0.42 | the yard running surface and the ring road |
| **Concrete** | `#2a3236` | 5 | 0.26 | slabs, aprons and walkways |
| **Compacted gravel** | `#3e3d36` | 4 | 0.9 | the plant yard, where the machines actually track |
| **Rough grass** | `#2d3d25` | 5 | 0.58 | the campus green and the verges |
| **Sand and fill** | `#4d4536` | 4 | 0.44 | stockpiles and the excavator cut |
| **Tidal marsh** | `#32422c` | 5 | 0.64 | vegetated tidal marsh, wet underfoot between the channels |
| **Tidal flat** | `#3e3c32` | 5 | 0.34 | the intertidal flat a managed pond becomes as it reopens |
| **Dry upland** | `#3f4230` | 4 | 0.5 | the dry ground above the tide line and on made land: where the uplands are planted back, and the windward fill of an island yard that nobody waters |
| **Levee crown** | `#4b4740` | 3 | 0.72 | the compacted crown of a dike or levee, which is the path a crew actually walks a diked site on |
| **Open water** | `#10202e` | 5 | 0.2 | the Bay, the estuary and the river |
| **Salt-weathered slab** | `#3a4145` | 5 | 0.32 | the concrete apron of a former naval station on made ground, bleached pale and stained at every joint |
| **Container hardstand** | `#22282a` | 5 | 0.38 | the crane-rated hardstand of a working terminal, rutted on the turning circles and patched everywhere else |
| **Crushed shell** | `#4e4c40` | 4 | 0.74 | the crushed-shell yard fill of a delta with no rock in it, pale, sharp and loud underfoot |
| **Caliche pad** | `#585040` | 4 | 0.55 | the caliche and crushed-limestone pad a coastal-plain plant yard is built up on, above ground that moves |
| **Track ballast** | `#3c3c3a` | 4 | 0.96 | the angular crushed stone of a rail yard, laid to drain and never laid to be walked on |
| **Crushed basalt** | `#2f3639` | 5 | 0.8 | the blue-grey crushed basalt a rain-country yard is surfaced with, darker in the joints where it stays wet |
| **Air-cooled slag** | `#474845` | 5 | 0.88 | the pale vesicular slag a mill valley paved its own yards and roadbeds with, for a century, because it had it |
| **Decomposed granite** | `#574c3e` | 4 | 0.5 | the granitic fines and road base of a Front Range yard, pale gold and raising dust in a dry month |
| **Crushed limerock** | `#5e5c50` | 4 | 0.6 | the crushed oolitic limestone a subtropical coast quarries out from under itself and lays everything on |
| **Cinder and clinker** | `#22201e` | 5 | 0.68 | the black cinder and clinker fill a coal-era plant yard was raised on and never took back up |
| **Prairie grass** | `#4a462c` | 5 | 0.6 | the unmown bunch grass of a plains or coastal-prairie verge, gold more of the year than it is green |
| **Moss and wet turf** | `#243024` | 5 | 0.5 | the shaded rain-fed verge of a temperate-rainforest yard, which takes the joints of the path as well |

## The sky

the sky is generated, not photographed, and the night sky is placed by a fixed seed rather than from any star catalogue - it is a night sky, not the night sky.

An equirectangular dome, drawn to a 1024x512 canvas at boot:
four gradient bands from the campus's own atmosphere, a disc, a cloud band
of value noise, and after dark 420 stars.
The disc is drawn where the key light actually comes from - its azimuth and elevation are read off the light, so the sun in the sky and the shadows on the ground agree rather than merely coexisting.

## The weather

6 states on one button, in this order. A state is a set of
**multipliers over whichever campus atmosphere is loaded** — never a look of
its own — so a campus keeps its character in the rain instead of every
campus looking alike under it.

| State | Sky | Sun | Cloud | Rain | Why it is worth standing in |
|---|---|---|---|---|---|
| ☀️ **Clear** | 1.75x | 1.0x | 0.18 | 0.00 | the working day the halls were drawn for - hard shadows, dry ground, and nothing in the air to hide a hand signal |
| ☁️ **Overcast** | 1.18x | 0.62x | 0.72 | 0.00 | flat light, no shadows to judge a line by - the light a layout hand complains about |
| 🌫️ **Fog** | 1.3x | 0.5x | 0.50 | 0.00 | the visibility a crane signal has to survive; the Bay campuses were drawn with this in mind, and it leaves the ground damp without a drop having fallen |
| 🌧️ **Rain** | 0.85x | 0.55x | 0.85 | 0.55 | wet ground, longer stopping distances, and every surface in the yard reading differently |
| ⛈️ **Storm** | 0.5x | 0.42x | 1.00 | 1.00 | the condition that stops a lift - and the one worth practising the stop in |
| 🌙 **Night** | 0.3x | 0.28x | 0.30 | 0.00 | the shift most of this work actually happens on - dew on the steel by the small hours, and every edge lit by a tower rather than by the sun |

schematic weather, not a forecast and not an observation: nothing here is tied to a reading taken at any real place or time, and the per-campus atmospheres are authored by reputation rather than measured.

## The campus atmospheres

| Campus | Ground / verge | Character |
|---|---|---|
| **Treasure Island Campus** | `salt-slab` / `upland` | marine layer off the Pacific; cool, grey and bright at once, and the thickest air on the network - authored by reputation, not measured |
| **Oakland Waterfront Campus** | `hardstand` / `gravel` | the estuary side, warmer and harder-edged than the island, with one thin bank off the water that is gone by the time the yard is working - authored by reputation, not measured |
| **Crescent Works Campus** | `shell` / `marsh` | Gulf humidity and a low warm haze that does not lift with the morning, and river fog off the water before it - authored by reputation, not measured |
| **Bayou Energy Hub** | `caliche` / `prairie` | Gulf-coast heat haze over a working ship channel that never clears the way a sea breeze clears, and a refinery glow at the sky's edge after dark - authored by reputation, not measured |
| **Loop Rail Hub** | `ballast` / `prairie` | a flat lakefront wind that never really stops, cold and grey off the water most of the year - authored by reputation, not measured |
| **Sound Aerospace Hub** | `basalt` / `moss` | a low marine overcast off the Sound that sits on the cranes rather than above them, a working waterfront and the hum of aerospace manufacturing just south of the green - authored by reputation, not measured |
| **Three Rivers Steel Hub** | `slag` / `grass` | a river haze that settles in the valley overnight and burns off late, over three confluent rivers crossed by more bridges than any other American city, and a post-industrial skyline standing where the mills once were - authored by reputation, not measured |
| **Front Range Mining Hub** | `decomposed-granite` / `prairie` | thin, dry high-altitude light off the Front Range with a view that goes as far as the ground allows, a mining and energy heritage at 5,280 feet, and the Rockies standing on the western horizon - authored by reputation, not measured |
| **Biscayne Coastal Hub** | `limerock` / `grass` | subtropical coastal heat and humidity off Biscayne Bay, afternoon thunderheads stacking through hurricane season, and a working seaport at the harbor's edge - authored by reputation, not measured |
| **Motor City Hub** | `cinder` / `gravel` | a Great Lakes river haze off the Detroit River, a working industrial waterfront across from Windsor, Ontario, and a century of automotive manufacturing standing behind the skyline - authored by reputation, not measured |

## The animals

6 kinds, 101 placed across the 10 campuses. They are
the only moving thing on an idle campus, and they give the scene the one
thing the buildings cannot: a sense of scale a learner reads without being
told.

| Animal | Flock | Span | Campuses | Why it is in the yard |
|---|---|---|---|---|
| 🐦 **Gull** | 5 | 1.2 m | treasure-island, oakland, seattle | a working waterfront has gulls over it; both Bay campuses and the Sound waterfront at Seattle are on one |
| 🦩 **Brown pelican** | 3 | 2.0 m | new-orleans, houston, miami | Louisiana’s state bird, and unmistakable over any Gulf coast or Biscayne Bay alike - the ship channel and the working port both |
| 🐦 **Ring-billed gull** | 5 | 1.1 m | chicago | the lakefront gull, by reputation the most familiar bird on the Chicago waterfront |
| 🕊️ **Egret** | 2 | 1.0 m | new-orleans | standing in the wet margin, which is most of the ground around this campus |
| 🕊️ **Pigeon** | 6 | 0.6 m | treasure-island, oakland, new-orleans, houston, chicago, seattle, pittsburgh, denver, miami, detroit | every yard in every city has them, and they are the scale reference nobody thinks about |
| 🐕 **Yard dog** | 1 | 1.0 m | treasure-island, oakland, new-orleans, houston, chicago, seattle, pittsburgh, denver, miami, detroit | the yard dog is a fixture of the trade, and it teaches the habit of looking down before reversing |

ambience, not a wildlife survey: common names, schematic bodies and authored paths. No species record, population count or sighting is claimed, and no animal here is drawn from any photograph.

Viewers who ask for reduced motion get a still yard: no animals, no rain.

## And the ground it all stands on

the ground a campus stands on is SCHEMATIC like the buildings on it: the surfaces are the ones the trade actually works over, but their extent and placement are drawn to teach, not surveyed.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
