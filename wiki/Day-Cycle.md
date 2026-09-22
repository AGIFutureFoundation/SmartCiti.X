# The day cycle

The sky the Academy is walked under, in 14 phases of one day.
10 of those hours are not chosen: they are solved, by
bisection, from the solar elevation that defines them — -18.0°, -12.0°, -6.0°, -0.833°, 6.0° — at a real
latitude read out of `geo/`. The other 4 follow from a
definition rather than from a search.

## What is computed and what is chosen

COMPUTED: the sun's elevation and azimuth in every phase, and the hour of every phase defined by a twilight threshold, are computed in sky/build.py from a published solar-position series at a real latitude read from geo/, on a stated day of the year. Nothing in the geometry was placed by eye.

every colour in this pack is AUTHORED - chosen by eye, one person's idea of what a Bay dawn looks like, and labelled AUTHORED in each phase's own provenance block. No colour here is derived from a colour temperature, a Rayleigh integral or a photograph, and none is measured.

So the pack holds 42 derived sun numbers and
104 hand-picked hex colours, and it labels every one of
them, field by field:

| Word | What it means here |
|---|---|
| **COMPUTED** | produced by a formula in sky/build.py from stated inputs |
| **DERIVED** | the same, for one field: computed, never placed by eye |
| **CONSTRUCTED** | follows from a definition (solar midnight, solar noon) or from the midpoint of two fixed phases |
| **READ** | held as a pointer into another registry and resolved at build time; not a copy |
| **READ-FROM-PAGE** | taken from web/build_3d.py and asserted present there |
| **AUTHORED** | chosen by a person, by eye, with no measurement behind it |

## Half of this is wired

**What the page reads today.** the page reads this registry. setSun() places the key light along the selected phase's own elevation and azimuth, applyPhase() takes the sun and hemisphere colours and intensity multipliers from the phase, the star field is up when the phase puts the sun below the star layer's cutoff and is dimmed rather than culled by the weather's star_visibility, a weather state that pins an hour does so through phase_override, and the hour is a control in the top bar and a ?hour= query parameter. The six hex literals the page used to switch the light with are gone.

**What it does not.** sun_disc is declared and unread - the page draws its disc from the light's own position, which is what makes the disc and the shadows agree, so this pack's disc block has nothing to drive yet. The layer list and compose_order describe an order the page now follows but does not read from here. And the hour is STEPPED, never interpolated: setSky() rebuilds the environment map on every call, so a sun that slid continuously would rebuild it every frame.

## The site and the day

| | |
|---|---|
| Campus | `treasure-island` |
| Latitude | 37.8235° — DERIVED, Treasure Island centroid, authored (WGS84) |
| Read from | `geo/registry/campuses_geo.json#campuses.treasure-island.lat` |
| Longitude | -122.3705° — the longitude is published because the campus has one, and is NOT used: apparent solar time removes it, along with the timezone and the equation of time. |
| Day of year | 80 — the March equinox - the single day whose sun path is closest to the annual mean. A solstice would make every phase in the table unrepresentative of the rest of the year. |
| Time base | local apparent solar time |
| Declination | Spencer 1971, Fourier series for solar declination, as published by the NOAA Solar Calculator |
| Elevation | sin(h) = sin(phi)sin(dec) + cos(phi)cos(dec)cos(H) - Meeus, Astronomical Algorithms 2nd ed., 13.6 |
| Azimuth | A = atan2(sin H, cos H sin(phi) - tan(dec) cos(phi)) - Meeus 13.5, from south positive west, published here rotated to degrees clockwise from true north |
| Refraction | none applied. The formulae return the GEOMETRIC altitude of the disc centre, which is why the risen-disc phases target -0.833 deg rather than 0. |
| Solver | bisection, 60 fixed halvings per solved phase - fixed rather than to a tolerance so the result is a deterministic function of the inputs |
| Rounding | every derived number is published to 4 decimals |

## The 14 phases

`t01` is the position in the day: solar noon sits at 0.5 by
construction, and none of these is a wall-clock hour.

| Phase | t01 | How | Elevation | Azimuth | Why this hour and not another |
|---|---|---|---|---|---|
| **Night** | 0.0 | construction | -52.44° | 0.0° | solar midnight: the hour angle is -180 deg by the definition of apparent solar time, so no solving is needed or honest |
| **Astronomical dawn** | 0.1865 | solved | -18.0° | 75.6504° | astronomical twilight begins when the sun centre is 18 deg below the horizon - the standard definition, being the depression at which sunlight stops interfering with the faintest stars |
| **Nautical dawn** | 0.208 | solved | -12.0° | 80.7397° | nautical twilight: sun centre 12 deg below the horizon, the standard depression at which the sea horizon is still usable for a sextant sight |
| **Civil dawn** | 0.2293 | solved | -6.0° | 85.5404° | civil twilight: sun centre 6 deg below the horizon, the standard depression below which artificial light is needed outdoors |
| **Sunrise** | 0.2474 | solved | -0.833° | 89.5631° | the upper limb touches the horizon while the CENTRE is still 50 arcminutes below it: 16 arcmin of solar semidiameter plus 34 arcmin of mean atmospheric refraction. This formula returns the geometric centre, so the target is -0.833 deg rather than 0 |
| **Golden morning** | 0.2715 | solved | 6.0° | 94.8799° | the top of the morning golden hour: the photographic convention puts its far edge at 6 deg of solar altitude |
| **Morning** | 0.3857 | construction | 36.4215° | 125.1601° | the working morning is the half-way point in time between the end of the golden hour and solar noon - constructed from two phases already fixed, so no hour is authored here |
| **Solar noon** | 0.5 | construction | 52.1106° | 180.0° | solar noon: hour angle 0 by the definition of apparent solar time, and the maximum elevation of the day |
| **Afternoon** | 0.6145 | construction | 36.4446° | 234.9796° | the mirror of morning: half way between solar noon and the start of the evening golden hour |
| **Golden hour** | 0.7289 | solved | 6.0° | 265.351° | the evening golden hour begins at 6 deg of solar altitude, the same photographic convention as its morning twin |
| **Sunset** | 0.753 | solved | -0.833° | 270.6898° | the same 50-arcminute allowance as sunrise - semidiameter plus mean refraction - applied on the falling branch |
| **Civil dusk** | 0.7712 | solved | -6.0° | 274.7329° | civil twilight ends at 6 deg of depression |
| **Nautical dusk** | 0.7925 | solved | -12.0° | 279.5632° | nautical twilight ends at 12 deg of depression |
| **Astronomical dusk** | 0.8141 | solved | -18.0° | 284.6905° | astronomical twilight ends at 18 deg of depression; past it the night is as dark as it is going to get |

5 of the 14 phases have the sun above the
horizon.

## The 5 layers

A layer renders on a predicate over the phase's own elevation or the weather's
own cloud and rain, never on a state of its own.

| Layer | Draw order | Renders when | Phases | Why |
|---|---|---|---|---|
| **Gradient dome** | 0 | always | 14 of 14 | the dome is the sky; there is no hour at which it is not drawn |
| **Star field** | 1 | `sun_elevation_deg < -6.0` | 5 of 14 | stars appear once the sun centre is below civil twilight (-6 deg). The page currently keys them off the WEATHER being `night`, which is why a clear 2 a.m. has no stars in it. |
| **Sun and moon disc** | 2 | always | 14 of 14 | one body is always in the sky; which one is the body_switch predicate below |
| **Cloud band** | 3 | `cloud_cover > 0.02` | 14 of 14 | the page already skips the band below 0.02 cover (`amount > .02`); the threshold is the page's, restated here as the predicate so the layer table is complete |
| **Horizon haze** | 4 | always | 14 of 14 | the dome must never end on an edge, at any hour |

## The stars

3 disc sizes, drawn by the page's own seeded generator
(`0x5EEDDA7A`, READ-FROM-PAGE: web/build_3d.py uses this seed; it is asserted present in that file rather than restated as an independent choice), for the star
count `world/` declares:

| Radius | Magnitude | Stars |
|---|---|---|
| 2.1 px | 0.0 | 39 |
| 1.4 px | 0.8805 | 113 |
| 0.9 px | 1.8399 | 268 |

Pogson: m - m_ref = -2.5 log10(A / A_ref), A = pi r^2, on the drawn disc area as a stand-in for flux. the drawn field spans 1.8399 magnitudes across three disc sizes, while a real sky holding as many stars as world/ asks for would have to reach about magnitude 3.8496. The field is therefore far too bright and far too shallow to be a sky chart, which is the same thing world/ already says in its own words: it is a night sky, not the night sky. No star here has a name, a position or a catalogue entry.

## Composing the dome

The gradient half is declared and unread. This is the order the page would
compose in once it reads it, and no other:

1. **the campus's own four stops** — `world.atmos.<campus>.sky`; read, unchanged - this is what keeps a Bay station and a Front Range yard from ending their domes identically
2. **the phase gradient** — `sky.phases[].gradient.stops`; mixed over the campus stops by 1 - campus_mix, per stop, in sRGB
3. **the weather tint** — `sky.weather_sky.<id>.gradient_tint_hex and tint_mix`; mixed over the result by tint_mix, per stop, in sRGB
4. **the weather's existing sky multiplier** — `world.weather.<id>.sky_mul`; the page's own darkHex(), unchanged and last, so nothing about this pack alters what the existing weather switch already does

## The weather over a phase

6 weather states get a sky treatment each, and each one
holds 5 pointers into `world/` rather than a copy:
30 reads in all.

| Weather | Tint mix | Stars | Horizon haze | Disc | Precipitation | What it does to the sky |
|---|---|---|---|---|---|---|
| **clear** | 0.05 | 1.0 | 1.0× | drawn | none | nothing between the eye and the sun: the phase gradient is left almost alone and the disc keeps its hard edge |
| **overcast** | 0.55 | 0.0 | 1.15× | hidden | none | a lid. The disc is not dimmed, it is gone, and the phase gradient is pulled most of the way to a flat grey - which is why an overcast dawn and an overcast noon look alike |
| **fog** | 0.7 | 0.0 | 2.2× | diffused | none | the haze band climbs until there is no horizon left to find, and the sun survives as a bright patch with no edge |
| **rain** | 0.6 | 0.0 | 1.3× | hidden | rain | darker and bluer than overcast, and the only difference the sky itself shows is that the precipitation layer renders |
| **storm** | 0.78 | 0.0 | 1.45× | hidden | rain | the phase is almost entirely overridden by the weather; a storm at noon and a storm at dusk are separated by very little, which is true of storms |
| **night** | 0.3 | 1.0 | 0.85× | moon | none | world/ carries `night` as a WEATHER because until this pack there was no time axis for it to be. It is kept, and it is kept honest: selecting it pins the phase to `night` rather than pretending to be a sky condition |

Cloud cover, fog density, fog tint, sun strength and rain rate are world/'s and are not copied into this payload - each weather entry holds the dotted path instead, and the build fails if the path does not resolve. The star count, the gradient band names, the disc geometry and the cloud recipe are read the same way.

precipitation renders when the weather record's own rain rate is above zero. This pack names the KIND and never the rate.

## What this is not

- **Not a forecast.** this is a day, not a date. The cycle is computed for one day of the year at one latitude and then used at all ten campuses, so a phase's hour is right for Treasure Island in March and approximately right elsewhere. No campus is showing its own sunrise, and the page is not tied to any clock, timezone or observation.
- **Not a clock.** positions in the day are local APPARENT SOLAR time, so noon is t01 = 0.5 by construction. A civil clock would need the equation of time and a zone offset; neither is here, and no phase should be presented as a wall-clock hour.
- **Not the page's lighting.** the page owns the base sun and hemisphere intensities, the canvas, the PMREM environment and the shadow frustum. This pack publishes multipliers and angles; it publishes no absolute intensity, no pixel and no metre.
- **Not synthesis.** the generated-video provenance word this bundle reserves for orbis/ is not used anywhere in this pack and does not appear in this payload. A bisection and a table of hand-picked colours are not that, and labelling them so would be a lie in the flattering direction.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
