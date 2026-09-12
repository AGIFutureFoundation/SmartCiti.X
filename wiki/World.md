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
| **Asphalt** | `#191f22` | 3 | 0.35 | the yard running surface and the ring road |
| **Concrete** | `#262e31` | 3 | 0.22 | slabs, aprons and walkways |
| **Compacted gravel** | `#3b3a34` | 2 | 0.85 | the plant yard, where the machines actually track |
| **Rough grass** | `#2b3a24` | 4 | 0.55 | the campus green and the verges |
| **Sand and fill** | `#4a4234` | 3 | 0.4 | stockpiles and the excavator cut |
| **Open water** | `#10202e` | 5 | 0.18 | the Bay, the estuary and the river |

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
| ☀️ **Clear** | 1.75x | 1.0x | 0.18 | 0.00 | the working day the halls were drawn for |
| ☁️ **Overcast** | 1.18x | 0.62x | 0.72 | 0.00 | flat light, no shadows to judge a line by - the light a layout hand complains about |
| 🌫️ **Fog** | 1.3x | 0.5x | 0.50 | 0.00 | the visibility a crane signal has to survive; the Bay campuses were drawn with this in mind |
| 🌧️ **Rain** | 0.85x | 0.55x | 0.85 | 0.55 | wet ground, longer stopping distances, and every surface in the yard reading differently |
| ⛈️ **Storm** | 0.5x | 0.42x | 1.00 | 1.00 | the condition that stops a lift - and the one worth practising the stop in |
| 🌙 **Night** | 0.3x | 0.28x | 0.30 | 0.00 | the shift most of this work actually happens on |

schematic weather, not a forecast and not an observation: nothing here is tied to a reading taken at any real place or time, and the per-campus atmospheres are authored by reputation rather than measured.

## The campus atmospheres

| Campus | Ground / verge | Character |
|---|---|---|
| **Treasure Island Campus** | `concrete` / `grass` | marine layer off the Pacific; cool, grey and bright at once - authored by reputation, not measured |
| **Oakland Waterfront Campus** | `asphalt` / `gravel` | the estuary side, warmer and harder-edged than the island - authored by reputation, not measured |
| **Crescent Works Campus** | `concrete` / `grass` | Gulf humidity and a low warm haze - authored by reputation, not measured |
| **Bayou Energy Hub** | `asphalt` / `gravel` | Gulf-coast heat haze over a working ship channel, a refinery glow at the sky's edge after dark - authored by reputation, not measured |
| **Loop Rail Hub** | `concrete` / `gravel` | a flat lakefront wind that never really stops, cold and grey off the water most of the year - authored by reputation, not measured |

## The animals

6 kinds, 58 placed across the 5 campuses. They are
the only moving thing on an idle campus, and they give the scene the one
thing the buildings cannot: a sense of scale a learner reads without being
told.

| Animal | Flock | Span | Campuses | Why it is in the yard |
|---|---|---|---|---|
| 🐦 **Gull** | 5 | 1.2 m | treasure-island, oakland | a working waterfront has gulls over it; both Bay campuses are on one |
| 🦩 **Brown pelican** | 3 | 2.0 m | new-orleans, houston | Louisiana’s state bird, and unmistakable over any Gulf coast - the ship channel included |
| 🐦 **Ring-billed gull** | 5 | 1.1 m | chicago | the lakefront gull, by reputation the most familiar bird on the Chicago waterfront |
| 🕊️ **Egret** | 2 | 1.0 m | new-orleans | standing in the wet margin, which is most of the ground around this campus |
| 🕊️ **Pigeon** | 6 | 0.6 m | treasure-island, oakland, new-orleans, houston, chicago | every yard in every city has them, and they are the scale reference nobody thinks about |
| 🐕 **Yard dog** | 1 | 1.0 m | treasure-island, oakland, new-orleans, houston, chicago | the yard dog is a fixture of the trade, and it teaches the habit of looking down before reversing |

ambience, not a wildlife survey: common names, schematic bodies and authored paths. No species record, population count or sighting is claimed, and no animal here is drawn from any photograph.

Viewers who ask for reduced motion get a still yard: no animals, no rain.

## And the ground it all stands on

the ground a campus stands on is SCHEMATIC like the buildings on it: the surfaces are the ones the trade actually works over, but their extent and placement are drawn to teach, not surveyed.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
