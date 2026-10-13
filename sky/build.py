#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy - the sky registry builder.

WHAT THIS PACK IS FOR. `world/` already owns the sky as a THING: an
equirectangular projection, four gradient bands, a sun and a moon disc, a
horizon haze, a star count, a cloud noise recipe, ten campus atmospheres
and six weather states. What it does not own is the sky as a DAY. The page
has exactly one sun direction - SUN_OFF, a fixed vector in web/build_3d.py
that trackSun() slides the shadow box along but never re-aims - so every
campus in this bundle is permanently at the same hour, and the only way it
gets dark is a WEATHER state called `night`, which is a time of day wearing
a weather's coat.

This pack declares the missing axis and nothing else: fourteen named day
PHASES, a per-weather sky treatment that POINTS AT the weather record
rather than restating it, the five draw LAYERS of a sky with the condition
each one renders under stated in data, and a contract saying exactly how
web/build_3d.py should consume all of it.

WHAT IS COMPUTED AND WHAT IS NOT. The sun's elevation and azimuth in every
phase are COMPUTED, here, in this file, from a published solar-position
algorithm at a real latitude - Treasure Island's, read from
geo/registry/campuses_geo.json - on a stated day of the year. Eleven of the
fourteen phases do not even have an authored time: their t01 is SOLVED by
bisection from the elevation that DEFINES the phase (-18 deg for
astronomical twilight, -6 for civil, -0.833 for the risen disc), so the
clock follows the sun rather than the sun following a clock. The star
field's magnitude bins are computed by running the page's own linear
congruential generator, branch for branch, so the published bins are the
stars the page will actually draw.

The COLOURS are not computed. Every hex in this file was chosen by eye and
is labelled AUTHORED in the phase's own provenance block, because a sky
colour derived from a blackbody temperature and a Rayleigh integral would
be a different and much larger claim than this bundle can support. Saying
so is the whole point: a number that looks measured and was not is worse
than an honest guess.

ONE TRUTH PER FACT. Nothing world/ owns is copied here. The weather
treatments hold POINTERS - dotted paths into world/registry/world.json -
and the build resolves them, fails if a key is absent, and then asserts
that the resolved value is NOT sitting in this payload as a literal. The
star count is world's. The gradient band names are world's. The night key
colour and the star seed are the page's, and are asserted against the page
source rather than restated as an opinion.

PROVENANCE. This pack's word is COMPUTED. The generated-video provenance
word that `orbis/` owns is not used here and does not appear anywhere in
this payload - the build asserts that, because borrowing it for a table of
hand-picked colours and a bisection would be a false label.
"""
import hashlib
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

BUILT = "2026-09-20"

# --------------------------------------------------------------- no defaults ---
# A default is a policy decision. There is no `??` and no `.get(k, d)` in
# this file: a missing key stops the build and names itself.


def need(d, key, where):
    if not isinstance(d, dict):
        raise TypeError(f'{where}: expected a mapping to read {key!r} from, '
                        f'got {type(d).__name__}')
    if key not in d:
        raise KeyError(f'{where}: required key {key!r} is missing. This build '
                       f'does not substitute a default for it - a default is a '
                       f'policy decision and nobody made this one.')
    return d[key]


def read_path(root, dotted, where):
    """Resolve a dotted path into a registry, naming the key that failed."""
    cur = root
    walked = []
    for part in dotted.split('.'):
        cur = need(cur, part, f'{where}: resolving {dotted!r} at '
                              f'{".".join(walked) or "<root>"}')
        walked.append(part)
    return cur


# ------------------------------------------------------------ what is read ---
MANIFEST = json.load(open(ROOT / 'pack/manifest.json'))
PACK_VERSION = need(MANIFEST, 'pack_version', 'pack/manifest.json')
PRODUCT = need(MANIFEST, 'product', 'pack/manifest.json')

WORLD = json.load(open(ROOT / 'world/registry/world.json'))
GEO = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))
PAGE_SRC = (ROOT / 'web/build_3d.py').read_text()

READS = [
    'pack/manifest.json',
    'world/registry/world.json',
    'geo/registry/campuses_geo.json',
    'web/build_3d.py',
]
for _r in READS:
    assert (ROOT / _r).exists(), f'this pack reads {_r}, which does not exist'

# The four gradient bands are world's names, not a second list here. The
# number of stops a phase gradient carries IS that band count.
SKY_BANDS = need(need(WORLD, 'sky', 'world.json'), 'bands', 'world.json: sky')
STOPS = len(SKY_BANDS)
WX_IDS = sorted(need(WORLD, 'weather', 'world.json').keys())

# --------------------------------------------------------------- the site ---
# The flagship campus. Its latitude is the one the solar formula runs at,
# read from the geo registry rather than typed beside it.
SITE_CAMPUS = 'treasure-island'
_site = read_path(GEO, f'campuses.{SITE_CAMPUS}', 'geo/registry/campuses_geo.json')
SITE_LAT = need(_site, 'lat', f'geo campuses.{SITE_CAMPUS}')
SITE_LON = need(_site, 'lng', f'geo campuses.{SITE_CAMPUS}')
SITE_LAT_PROV = need(_site, 'provenance', f'geo campuses.{SITE_CAMPUS}')
SITE_LAT_SRC = need(_site, 'source', f'geo campuses.{SITE_CAMPUS}')

# The day the cycle is computed for. The March equinox is chosen because
# its sun path is the closest of any single day to the annual mean: a
# solstice would make every phase in the table unrepresentative of the rest
# of the year. Day 80 of a non-leap year is 21 March.
DAY_OF_YEAR = 80

# t01 is a position in the LOCAL APPARENT SOLAR day, not in a civil clock
# day. That is a deliberate simplification and it is why no longitude, no
# time zone and no equation of time appear below: by definition solar noon
# is t01 = 0.5 and the hour angle is a straight function of t01. A civil
# clock would need the equation of time and a zone offset, would put noon
# at a different t01 in every city, and would buy this renderer nothing.
TIME_BASE = 'local apparent solar time'


def hour_angle_deg(t01):
    """Hour angle: -180 deg at solar midnight, 0 at solar noon, +180 at the
    next midnight. Direct from the definition of apparent solar time."""
    return t01 * 360.0 - 180.0


def declination_rad(t01):
    """Solar declination for the stated day of year.

    Spencer's Fourier series for declination (J. W. Spencer, 'Fourier
    series representation of the position of the Sun', Search 2(5), 1971),
    which is the series the NOAA Solar Calculator publishes. Accurate to
    a few hundredths of a degree, which is far inside anything a 1024x512
    canvas sky can show.
    """
    g = 2.0 * math.pi / 365.0 * (DAY_OF_YEAR - 1 + (t01 * 24.0 - 12.0) / 24.0)
    return (0.006918
            - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.001480 * math.sin(3 * g))


def sun_elevation_deg(t01):
    """sin(h) = sin(phi)sin(dec) + cos(phi)cos(dec)cos(H).

    The standard altitude equation of the horizontal coordinate system;
    see Meeus, 'Astronomical Algorithms' 2nd ed., ch. 13 (13.6). This is
    the GEOMETRIC altitude of the centre of the disc: no refraction is
    added to it, which is why the risen-disc phases below target -0.833
    deg rather than 0.
    """
    phi = math.radians(SITE_LAT)
    dec = declination_rad(t01)
    ha = math.radians(hour_angle_deg(t01))
    s = (math.sin(phi) * math.sin(dec)
         + math.cos(phi) * math.cos(dec) * math.cos(ha))
    return math.degrees(math.asin(max(-1.0, min(1.0, s))))


def sun_azimuth_deg(t01):
    """A = atan2(sin H, cos H sin(phi) - tan(dec) cos(phi)), measured from
    SOUTH and positive westward (Meeus, 'Astronomical Algorithms' 2nd ed.,
    13.5), then rotated to the convention a renderer wants: degrees
    clockwise from true north, so 90 is due east and 270 due west.
    """
    phi = math.radians(SITE_LAT)
    dec = declination_rad(t01)
    ha = math.radians(hour_angle_deg(t01))
    a = math.atan2(math.sin(ha),
                   math.cos(ha) * math.sin(phi) - math.tan(dec) * math.cos(phi))
    return (math.degrees(a) + 180.0) % 360.0


# Bisection is run a FIXED number of times rather than to a tolerance, so
# the answer is a deterministic function of the inputs and the test can
# re-run the identical loop and land on the identical double.
BISECT_STEPS = 60


def solve_t01(target_elev_deg, branch):
    """Find the t01 at which the sun's geometric altitude equals the value
    that DEFINES this phase. Elevation is monotone in t01 on each branch -
    rising from solar midnight to noon, falling from noon to midnight - so
    a plain bisection is exact enough and cannot land on the wrong root."""
    if branch == 'rising':
        lo, hi = 0.0, 0.5
    elif branch == 'falling':
        lo, hi = 0.5, 1.0
    else:
        raise ValueError(f'a phase branch is "rising" or "falling", not {branch!r}')
    f_lo, f_hi = sun_elevation_deg(lo), sun_elevation_deg(hi)
    if not (min(f_lo, f_hi) <= target_elev_deg <= max(f_lo, f_hi)):
        raise ValueError(
            f'the sun never reaches {target_elev_deg} deg on the {branch} branch '
            f'at latitude {SITE_LAT} on day {DAY_OF_YEAR}: the branch spans '
            f'{f_lo:.3f}..{f_hi:.3f} deg. This phase cannot be solved and the '
            f'build will not invent a time for it.')
    for _ in range(BISECT_STEPS):
        mid = (lo + hi) / 2.0
        if (sun_elevation_deg(mid) < target_elev_deg) == (branch == 'rising'):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# The geometric altitude of the disc CENTRE at which the upper limb
# touches the horizon: 16 arcmin of solar semidiameter plus 34 arcmin of
# mean refraction, i.e. 50 arcmin below true. Declared once and used by
# the sunrise and sunset phases, the disc layer's body switch and the
# count of phases with the sun up.
RISEN_DISC_DEG = -0.833

R4 = 4  # every derived number is published to four decimals, and only four


def r4(x):
    return round(x, R4)


# --------------------------------------------------------------- the phases ---
# A closed, ordered, CYCLIC set. Each entry says how its t01 is arrived at:
#
#   solved       - t01 is bisected from the elevation that defines the
#                  phase. The elevation is a standard definition, not a
#                  preference, and the source of each one is in `why`.
#   construction - t01 follows from the definition of apparent solar time
#                  (midnight is 0.0, noon is 0.5) or from the midpoint of
#                  two already-solved phases. No eye was involved either way.
#
# The COLOURS on every one of these are AUTHORED. See the module docstring.
PHASE_SPEC = [
    ('night', 'Night', {
        'by': 'construction', 't01': 0.0,
        'why': 'solar midnight: the hour angle is -180 deg by the definition of '
               'apparent solar time, so no solving is needed or honest'}),
    ('astronomical-dawn', 'Astronomical dawn', {
        'by': 'solved', 'target_elev_deg': -18.0, 'branch': 'rising',
        'why': 'astronomical twilight begins when the sun centre is 18 deg below '
               'the horizon - the standard definition, being the depression at '
               'which sunlight stops interfering with the faintest stars'}),
    ('nautical-dawn', 'Nautical dawn', {
        'by': 'solved', 'target_elev_deg': -12.0, 'branch': 'rising',
        'why': 'nautical twilight: sun centre 12 deg below the horizon, the '
               'standard depression at which the sea horizon is still usable '
               'for a sextant sight'}),
    ('civil-dawn', 'Civil dawn', {
        'by': 'solved', 'target_elev_deg': -6.0, 'branch': 'rising',
        'why': 'civil twilight: sun centre 6 deg below the horizon, the standard '
               'depression below which artificial light is needed outdoors'}),
    ('sunrise', 'Sunrise', {
        'by': 'solved', 'target_elev_deg': RISEN_DISC_DEG, 'branch': 'rising',
        'why': 'the upper limb touches the horizon while the CENTRE is still 50 '
               'arcminutes below it: 16 arcmin of solar semidiameter plus 34 '
               'arcmin of mean atmospheric refraction. This formula returns the '
               'geometric centre, so the target is -0.833 deg rather than 0'}),
    ('golden-morning', 'Golden morning', {
        'by': 'solved', 'target_elev_deg': 6.0, 'branch': 'rising',
        'why': 'the top of the morning golden hour: the photographic convention '
               'puts its far edge at 6 deg of solar altitude'}),
    ('morning', 'Morning', {
        'by': 'construction', 'midpoint_of': ('golden-morning', 'noon'),
        'why': 'the working morning is the half-way point in time between the '
               'end of the golden hour and solar noon - constructed from two '
               'phases already fixed, so no hour is authored here'}),
    ('noon', 'Solar noon', {
        'by': 'construction', 't01': 0.5,
        'why': 'solar noon: hour angle 0 by the definition of apparent solar '
               'time, and the maximum elevation of the day'}),
    ('afternoon', 'Afternoon', {
        'by': 'construction', 'midpoint_of': ('noon', 'golden-hour'),
        'why': 'the mirror of morning: half way between solar noon and the start '
               'of the evening golden hour'}),
    ('golden-hour', 'Golden hour', {
        'by': 'solved', 'target_elev_deg': 6.0, 'branch': 'falling',
        'why': 'the evening golden hour begins at 6 deg of solar altitude, the '
               'same photographic convention as its morning twin'}),
    ('sunset', 'Sunset', {
        'by': 'solved', 'target_elev_deg': RISEN_DISC_DEG, 'branch': 'falling',
        'why': 'the same 50-arcminute allowance as sunrise - semidiameter plus '
               'mean refraction - applied on the falling branch'}),
    ('civil-dusk', 'Civil dusk', {
        'by': 'solved', 'target_elev_deg': -6.0, 'branch': 'falling',
        'why': 'civil twilight ends at 6 deg of depression'}),
    ('nautical-dusk', 'Nautical dusk', {
        'by': 'solved', 'target_elev_deg': -12.0, 'branch': 'falling',
        'why': 'nautical twilight ends at 12 deg of depression'}),
    ('astronomical-dusk', 'Astronomical dusk', {
        'by': 'solved', 'target_elev_deg': -18.0, 'branch': 'falling',
        'why': 'astronomical twilight ends at 18 deg of depression; past it the '
               'night is as dark as it is going to get'}),
]

# The colours. Chosen by eye, every one of them, and labelled AUTHORED in
# each phase's own provenance block. `campus_mix` is how much of the
# campus's OWN four stops (world.atmos[k].sky) survives the phase tint -
# 1.0 at noon, because the campus stops were authored for a working day,
# and least at the hours a campus has least character of its own.
PHASE_COLOUR = {
    'night': {
        'sun_color_hex': '#9db4d8', 'sun_intensity_mul': 0.14,
        'hemi_sky_hex': '#35455c', 'hemi_ground_hex': '#0d0c0a',
        'hemi_intensity_mul': 0.30, 'campus_mix': 0.35,
        'gradient': ['#05080d', '#0a1018', '#141d27', '#1d2630']},
    'astronomical-dawn': {
        'sun_color_hex': '#6f86b4', 'sun_intensity_mul': 0.16,
        'hemi_sky_hex': '#3b4a63', 'hemi_ground_hex': '#100f0d',
        'hemi_intensity_mul': 0.34, 'campus_mix': 0.35,
        'gradient': ['#060a11', '#0d1520', '#1b2635', '#2a3444']},
    'nautical-dawn': {
        'sun_color_hex': '#7d90bc', 'sun_intensity_mul': 0.22,
        'hemi_sky_hex': '#47576f', 'hemi_ground_hex': '#141310',
        'hemi_intensity_mul': 0.42, 'campus_mix': 0.40,
        'gradient': ['#081020', '#12203a', '#2b3b56', '#41506a']},
    'civil-dawn': {
        'sun_color_hex': '#b59ac0', 'sun_intensity_mul': 0.36,
        'hemi_sky_hex': '#5d6a84', 'hemi_ground_hex': '#1b1814',
        'hemi_intensity_mul': 0.58, 'campus_mix': 0.45,
        'gradient': ['#0e1b32', '#25375a', '#5b5f7e', '#8a7a86']},
    'sunrise': {
        'sun_color_hex': '#ff9d5c', 'sun_intensity_mul': 0.55,
        'hemi_sky_hex': '#7d8196', 'hemi_ground_hex': '#241d16',
        'hemi_intensity_mul': 0.72, 'campus_mix': 0.50,
        'gradient': ['#1b2c4d', '#456089', '#b07f7a', '#ff9f6a']},
    'golden-morning': {
        'sun_color_hex': '#ffc07a', 'sun_intensity_mul': 0.82,
        'hemi_sky_hex': '#9fb0c4', 'hemi_ground_hex': '#2a2118',
        'hemi_intensity_mul': 0.88, 'campus_mix': 0.60,
        'gradient': ['#2b4a78', '#5f86ad', '#a8b0ad', '#ffc98d']},
    'morning': {
        'sun_color_hex': '#ffe0b0', 'sun_intensity_mul': 0.95,
        'hemi_sky_hex': '#aec2cb', 'hemi_ground_hex': '#241d16',
        'hemi_intensity_mul': 1.00, 'campus_mix': 0.80,
        'gradient': ['#3a6ca3', '#6d9cc4', '#a9c0cc', '#d8d4c4']},
    'noon': {
        'sun_color_hex': '#fff6e2', 'sun_intensity_mul': 1.00,
        'hemi_sky_hex': '#bcd2dc', 'hemi_ground_hex': '#2a2622',
        'hemi_intensity_mul': 1.08, 'campus_mix': 1.00,
        'gradient': ['#2f6fb0', '#6aa3cf', '#b3cbd8', '#dfe2dd']},
    'afternoon': {
        'sun_color_hex': '#ffe3b4', 'sun_intensity_mul': 0.93,
        'hemi_sky_hex': '#b0c4ce', 'hemi_ground_hex': '#272019',
        'hemi_intensity_mul': 1.00, 'campus_mix': 0.80,
        'gradient': ['#356ea4', '#6f9ac2', '#aebfc6', '#d9cfba']},
    'golden-hour': {
        'sun_color_hex': '#ffb066', 'sun_intensity_mul': 0.78,
        'hemi_sky_hex': '#a09aa0', 'hemi_ground_hex': '#2b2018',
        'hemi_intensity_mul': 0.84, 'campus_mix': 0.60,
        'gradient': ['#2e4f7e', '#6b7fa4', '#c39a84', '#ffbe7e']},
    'sunset': {
        'sun_color_hex': '#ff8347', 'sun_intensity_mul': 0.50,
        'hemi_sky_hex': '#7a7386', 'hemi_ground_hex': '#241a13',
        'hemi_intensity_mul': 0.68, 'campus_mix': 0.50,
        'gradient': ['#1d2d52', '#4a5180', '#b56a63', '#ff8a52']},
    'civil-dusk': {
        'sun_color_hex': '#9c7fae', 'sun_intensity_mul': 0.32,
        'hemi_sky_hex': '#56587a', 'hemi_ground_hex': '#181510',
        'hemi_intensity_mul': 0.54, 'campus_mix': 0.45,
        'gradient': ['#101c36', '#233255', '#5a5375', '#8a6a78']},
    'nautical-dusk': {
        'sun_color_hex': '#74849f', 'sun_intensity_mul': 0.20,
        'hemi_sky_hex': '#414f68', 'hemi_ground_hex': '#121108',
        'hemi_intensity_mul': 0.40, 'campus_mix': 0.40,
        'gradient': ['#0a1020', '#131f36', '#283350', '#3a4460']},
    'astronomical-dusk': {
        'sun_color_hex': '#6a80ab', 'sun_intensity_mul': 0.15,
        'hemi_sky_hex': '#38465e', 'hemi_ground_hex': '#0f0e0c',
        'hemi_intensity_mul': 0.32, 'campus_mix': 0.35,
        'gradient': ['#070b12', '#0c1319', '#181f2b', '#232b38']},
}

PHASE_PROVENANCE = {
    't01': None,                      # filled per phase: DERIVED or CONSTRUCTED
    'elevation_deg': 'DERIVED',
    'azimuth_deg': 'DERIVED',
    'sun_color_hex': 'AUTHORED',
    'sun_intensity_mul': 'AUTHORED',
    'hemi_sky_hex': 'AUTHORED',
    'hemi_ground_hex': 'AUTHORED',
    'hemi_intensity_mul': 'AUTHORED',
    'gradient': 'AUTHORED',
    'campus_mix': 'AUTHORED',
}

_spec_ids = [pid for pid, _n, _s in PHASE_SPEC]
assert len(set(_spec_ids)) == len(_spec_ids), 'two phases share an id'
assert set(PHASE_COLOUR) == set(_spec_ids), (
    'every phase is coloured and nothing else is: '
    f'{sorted(set(PHASE_COLOUR) ^ set(_spec_ids))}')

# pass one: everything whose t01 does not depend on another phase
_t01 = {}
for pid, _name, spec in PHASE_SPEC:
    by = need(spec, 'by', f'phase {pid}')
    if by == 'solved':
        _t01[pid] = solve_t01(need(spec, 'target_elev_deg', f'phase {pid}'),
                              need(spec, 'branch', f'phase {pid}'))
    elif by == 'construction' and 't01' in spec:
        _t01[pid] = spec['t01']
    elif by == 'construction' and 'midpoint_of' in spec:
        continue
    else:
        raise ValueError(f'phase {pid}: `by` is "solved" or "construction", '
                         f'and a construction states either t01 or midpoint_of')
# pass two: the midpoints, now that what they sit between is fixed
for pid, _name, spec in PHASE_SPEC:
    if pid in _t01:
        continue
    a, b = need(spec, 'midpoint_of', f'phase {pid}')
    for other in (a, b):
        if other not in _t01:
            raise KeyError(f'phase {pid}: midpoint_of names {other!r}, which is '
                           f'not a phase with a fixed t01 - a midpoint cannot be '
                           f'taken between something and nothing')
    _t01[pid] = (_t01[a] + _t01[b]) / 2.0

PHASES = []
for _i, (pid, name, spec) in enumerate(PHASE_SPEC):
    t01 = _t01[pid]
    colour = PHASE_COLOUR[pid]
    by = spec['by']
    prov = dict(PHASE_PROVENANCE)
    prov['t01'] = 'DERIVED' if by == 'solved' else 'CONSTRUCTED'
    entry = {
        'id': pid,
        'name': name,
        'order': _i,
        'next': _spec_ids[(_i + 1) % len(_spec_ids)],
        't01': r4(t01),
        't01_by': by,
        'why': need(spec, 'why', f'phase {pid}'),
        'elevation_deg': r4(sun_elevation_deg(t01)),
        'azimuth_deg': r4(sun_azimuth_deg(t01)),
        'sun': {'color_hex': need(colour, 'sun_color_hex', f'phase {pid}'),
                'intensity_mul': need(colour, 'sun_intensity_mul', f'phase {pid}')},
        'hemi': {'sky_hex': need(colour, 'hemi_sky_hex', f'phase {pid}'),
                 'ground_hex': need(colour, 'hemi_ground_hex', f'phase {pid}'),
                 'intensity_mul': need(colour, 'hemi_intensity_mul', f'phase {pid}')},
        'gradient': {'stops': need(colour, 'gradient', f'phase {pid}'),
                     'bands': SKY_BANDS,
                     'campus_mix': need(colour, 'campus_mix', f'phase {pid}')},
        'provenance': prov,
    }
    if by == 'solved':
        entry['target_elev_deg'] = spec['target_elev_deg']
        entry['branch'] = spec['branch']
    PHASES.append(entry)

# -- the phases are a real cycle, in order, and the geometry agrees with the
# -- definition each solved phase was solved from.
for _a, _b in zip(PHASES, PHASES[1:]):
    assert _a['t01'] < _b['t01'], (
        f'phases are ordered by time: {_a["id"]} at t01 {_a["t01"]} is not '
        f'before {_b["id"]} at {_b["t01"]}')
assert PHASES[0]['t01'] == 0.0 and PHASES[-1]['t01'] < 1.0, \
    'the cycle starts at solar midnight and closes before the next one'
for _p in PHASES:
    assert len(_p['gradient']['stops']) == STOPS, (
        f'{_p["id"]}: a phase gradient has one stop per band world/ declares '
        f'({STOPS}), not {len(_p["gradient"]["stops"])}')
    for _hx in (_p['gradient']['stops'] + [_p['sun']['color_hex'],
                                           _p['hemi']['sky_hex'],
                                           _p['hemi']['ground_hex']]):
        assert (isinstance(_hx, str) and len(_hx) == 7 and _hx[0] == '#'
                and all(c in '0123456789abcdef' for c in _hx[1:])), \
            f'{_p["id"]}: {_hx!r} is not a lowercase #rrggbb colour'
    for _k in ('sun', 'hemi'):
        _m = _p[_k]['intensity_mul']
        assert 0.0 < _m <= 1.2, (
            f'{_p["id"]}: {_k} intensity_mul {_m} is a MULTIPLIER on the number '
            f'the page already owns, so it lives in (0, 1.2]')
    assert 0.0 <= _p['gradient']['campus_mix'] <= 1.0, \
        f'{_p["id"]}: campus_mix is a fraction of the campus stops'
    if _p['t01_by'] == 'solved':
        assert abs(_p['elevation_deg'] - _p['target_elev_deg']) < 1e-3, (
            f'{_p["id"]}: solved to t01 {_p["t01"]} but the sun is at '
            f'{_p["elevation_deg"]} deg there, not the {_p["target_elev_deg"]} '
            f'deg that defines the phase')
_noon = [p for p in PHASES if p['id'] == 'noon'][0]
assert _noon['elevation_deg'] == max(p['elevation_deg'] for p in PHASES), \
    'solar noon is the highest the sun gets; if it is not, the formula is wrong'
assert abs(_noon['azimuth_deg'] - 180.0) < 0.5, (
    f'at a northern latitude the noon sun is due south; this one is at '
    f'{_noon["azimuth_deg"]} deg, so the azimuth convention has drifted')

# ----------------------------------------------------------- weather skies ---
# ONE TRUTH PER FACT. Cloud cover, fog density, fog tint, sun strength and
# the precipitation rate are ALREADY world's. They are not restated here.
# Each entry holds a dotted POINTER into world/registry/world.json, the
# build resolves it, and the payload keeps the pointer rather than the
# number - so there is exactly one place in this bundle where a weather's
# cloud cover can be changed.
WEATHER_READS = {
    'cloud_cover': 'cloud',
    'fog_density_mul': 'fog_mul',
    'fog_color_mul': 'fog_tint',
    'sun_intensity_mul': 'sun_mul',
    'precipitation_rate': 'rain',
}

WEATHER_SKY = {
    'clear': {
        'gradient_tint_hex': '#cfe3f2', 'tint_mix': 0.05,
        'star_visibility': 1.00, 'horizon_haze_mul': 1.00,
        'sun_disc': 'drawn', 'precipitation': 'none',
        'phase_override': None,
        'note': 'nothing between the eye and the sun: the phase gradient is '
                'left almost alone and the disc keeps its hard edge'},
    'overcast': {
        'gradient_tint_hex': '#b7c0c6', 'tint_mix': 0.55,
        'star_visibility': 0.00, 'horizon_haze_mul': 1.15,
        'sun_disc': 'hidden', 'precipitation': 'none',
        'phase_override': None,
        'note': 'a lid. The disc is not dimmed, it is gone, and the phase '
                'gradient is pulled most of the way to a flat grey - which is '
                'why an overcast dawn and an overcast noon look alike'},
    'fog': {
        'gradient_tint_hex': '#d3d8da', 'tint_mix': 0.70,
        'star_visibility': 0.00, 'horizon_haze_mul': 2.20,
        'sun_disc': 'diffused', 'precipitation': 'none',
        'phase_override': None,
        'note': 'the haze band climbs until there is no horizon left to find, '
                'and the sun survives as a bright patch with no edge'},
    'rain': {
        'gradient_tint_hex': '#8e9aa4', 'tint_mix': 0.60,
        'star_visibility': 0.00, 'horizon_haze_mul': 1.30,
        'sun_disc': 'hidden', 'precipitation': 'rain',
        'phase_override': None,
        'note': 'darker and bluer than overcast, and the only difference the '
                'sky itself shows is that the precipitation layer renders'},
    'storm': {
        'gradient_tint_hex': '#5b636d', 'tint_mix': 0.78,
        'star_visibility': 0.00, 'horizon_haze_mul': 1.45,
        'sun_disc': 'hidden', 'precipitation': 'rain',
        'phase_override': None,
        'note': 'the phase is almost entirely overridden by the weather; a '
                'storm at noon and a storm at dusk are separated by very '
                'little, which is true of storms'},
    'night': {
        'gradient_tint_hex': '#1a2230', 'tint_mix': 0.30,
        'star_visibility': 1.00, 'horizon_haze_mul': 0.85,
        'sun_disc': 'moon', 'precipitation': 'none',
        'phase_override': 'night',
        'note': 'world/ carries `night` as a WEATHER because until this pack '
                'there was no time axis for it to be. It is kept, and it is '
                'kept honest: selecting it pins the phase to `night` rather '
                'than pretending to be a sky condition'},
}

# -- both directions. A weather world/ declares with no sky treatment fails
# -- the build; a treatment for a weather world/ does not declare fails too.
_missing = [w for w in WX_IDS if w not in WEATHER_SKY]
assert not _missing, (
    f'world/registry/world.json declares weather {_missing} with no sky '
    f'treatment here. Every weather state must say what it does to the sky; '
    f'this build will not fall back to a default one.')
_extra = [w for w in WEATHER_SKY if w not in WX_IDS]
assert not _extra, (
    f'{_extra} is not a weather state world/registry/world.json declares. '
    f'This pack does not invent weather; it dresses the six that exist.')
assert sorted(WEATHER_SKY) == WX_IDS, 'the weather id sets must match exactly'

DISC_STATES = ['drawn', 'diffused', 'hidden', 'moon']
PRECIP_KINDS = ['none', 'rain']

_resolved = {}
for _wid in WX_IDS:
    _e = WEATHER_SKY[_wid]
    _reads = {}
    for _local, _wkey in WEATHER_READS.items():
        _dotted = f'weather.{_wid}.{_wkey}'
        _val = read_path(WORLD, _dotted, f'weather_sky.{_wid}')
        _reads[_local] = _dotted
        _resolved[f'{_wid}.{_local}'] = _val
    _e['reads'] = _reads
    _e['provenance'] = {
        **{k: 'READ' for k in WEATHER_READS},
        'gradient_tint_hex': 'AUTHORED', 'tint_mix': 'AUTHORED',
        'star_visibility': 'AUTHORED', 'horizon_haze_mul': 'AUTHORED',
        'sun_disc': 'AUTHORED', 'precipitation': 'AUTHORED',
        'phase_override': 'AUTHORED',
    }
    _hx = need(_e, 'gradient_tint_hex', f'weather_sky.{_wid}')
    assert len(_hx) == 7 and _hx[0] == '#' and all(c in '0123456789abcdef'
                                                   for c in _hx[1:]), \
        f'weather_sky.{_wid}: {_hx!r} is not a lowercase #rrggbb colour'
    assert 0.0 <= need(_e, 'tint_mix', f'weather_sky.{_wid}') <= 1.0
    assert 0.0 <= need(_e, 'star_visibility', f'weather_sky.{_wid}') <= 1.0
    assert need(_e, 'sun_disc', f'weather_sky.{_wid}') in DISC_STATES, \
        f'weather_sky.{_wid}: sun_disc is one of {DISC_STATES}'
    assert need(_e, 'precipitation', f'weather_sky.{_wid}') in PRECIP_KINDS
    _po = need(_e, 'phase_override', f'weather_sky.{_wid}')
    assert _po is None or _po in _spec_ids, \
        f'weather_sky.{_wid}: phase_override {_po!r} is not a phase this pack declares'
    # the values world owns are read, checked, and NOT kept
    _cc = _resolved[f'{_wid}.cloud_cover']
    assert 0.0 <= _cc <= 1.0, (
        f'world weather.{_wid}.cloud is {_cc}, outside 0..1 - the cloud band '
        f'alpha this pack hands the page would be meaningless')
    _rain = _resolved[f'{_wid}.precipitation_rate']
    _renders = _rain > 0
    assert _renders == (_e['precipitation'] != 'none'), (
        f'weather_sky.{_wid}: says precipitation {_e["precipitation"]!r} but '
        f'world weather.{_wid}.rain is {_rain}. The kind is authored; WHETHER '
        f'it renders is world\'s to say, and the two disagree.')

PRECIP_PREDICATE = {
    'field': 'precipitation_rate', 'op': '>', 'value': 0,
    'says': 'precipitation renders when the weather record\'s own rain rate is '
            'above zero. This pack names the KIND and never the rate.',
}

# ------------------------------------------------------------- the layers ---
# The draw order is not an opinion. It is READ OFF the page: each layer
# names a unique anchor string in web/build_3d.py's skyCanvas(), and the
# order is the order those anchors appear in that file. If somebody
# reorders the drawing, this registry reorders with it or the build stops.
PREDICATE_FIELDS = {
    'always': 'no condition - the layer is always drawn',
    'sun_elevation_deg': 'the current phase\'s derived solar altitude',
    'cloud_cover': 'the current weather\'s cloud cover, read from '
                   'world.weather.<id>.cloud',
    'precipitation_rate': 'the current weather\'s rain rate, read from '
                          'world.weather.<id>.rain',
}
PREDICATE_OPS = {
    'always': lambda a, b: True,
    '<': lambda a, b: a < b,
    '>': lambda a, b: a > b,
    '<=': lambda a, b: a <= b,
    '>=': lambda a, b: a >= b,
}

STAR_ELEV_CUTOFF = -6.0   # civil twilight, the standard at which stars appear

LAYER_SPEC = [
    ('gradient-dome', 'Gradient dome', 'gr.addColorStop(0, stops[0]);',
     {'field': 'always', 'op': 'always', 'value': None,
      'says': 'the dome is the sky; there is no hour at which it is not drawn'},
     {'stops': STOPS, 'bands': SKY_BANDS,
      'composed_from': 'the phase gradient, mixed with the campus stops by the '
                       'phase\'s campus_mix, then tinted by the weather'}),
    ('star-field', 'Star field', '// the stars go under everything else',
     {'field': 'sun_elevation_deg', 'op': '<', 'value': STAR_ELEV_CUTOFF,
      'says': 'stars appear once the sun centre is below civil twilight (-6 '
              'deg). The page currently keys them off the WEATHER being '
              '`night`, which is why a clear 2 a.m. has no stars in it.'},
     {'count_read_from': 'sky.stars.count',
      'attenuated_by': 'the weather\'s star_visibility'}),
    ('sun-disc', 'Sun and moon disc',
     'const disc = opts.moon ? SKY.disc.moon : SKY.disc.sun;',
     {'field': 'always', 'op': 'always', 'value': None,
      'says': 'one body is always in the sky; which one is the body_switch '
              'predicate below'},
     {'body_switch': {'field': 'sun_elevation_deg', 'op': '>', 'value': RISEN_DISC_DEG,
                      'says': 'the sun is the body while its centre is above '
                              '-0.833 deg - the same risen-disc threshold the '
                              'sunrise and sunset phases are solved from; below '
                              'it the moon is drawn instead'},
      'geometry_read_from': 'sky.disc',
      'placed_by': 'the phase azimuth and elevation, which the page must set '
                   'on its key light FIRST so the disc and the shadows agree'}),
    ('cloud-band', 'Cloud band', '// the cloud band: value noise over octaves',
     {'field': 'cloud_cover', 'op': '>', 'value': 0.02,
      'says': 'the page already skips the band below 0.02 cover (`amount > '
              '.02`); the threshold is the page\'s, restated here as the '
              'predicate so the layer table is complete'},
     {'recipe_read_from': 'sky.clouds',
      'luminance': 'world\'s day_lum above the risen-disc threshold, night_lum '
                   'below it - keyed off the phase rather than off the weather'}),
    ('horizon-haze', 'Horizon haze', 'const hz = SKY.horizon_haze;',
     {'field': 'always', 'op': 'always', 'value': None,
      'says': 'the dome must never end on an edge, at any hour'},
     {'recipe_read_from': 'sky.horizon_haze',
      'scaled_by': 'the weather\'s horizon_haze_mul, and the campus\'s own '
                   '`haze` tint where it names one'}),
]

LAYERS = []
for _lid, _lname, _anchor, _pred, _params in LAYER_SPEC:
    _n = PAGE_SRC.count(_anchor)
    assert _n == 1, (
        f'layer {_lid}: its anchor in web/build_3d.py appears {_n} times, not '
        f'once. The draw order is derived from where these anchors sit, so an '
        f'anchor that is ambiguous or gone makes the order a guess.')
    assert need(_pred, 'field', f'layer {_lid}') in PREDICATE_FIELDS, \
        f'layer {_lid}: predicate field is not one this pack declares'
    assert need(_pred, 'op', f'layer {_lid}') in PREDICATE_OPS, \
        f'layer {_lid}: predicate op is not one this pack declares'
    LAYERS.append({'id': _lid, 'name': _lname, 'page_anchor': _anchor,
                   'renders_when': _pred, 'params': _params,
                   '_at': PAGE_SRC.index(_anchor)})

LAYERS.sort(key=lambda l: l['_at'])
for _i, _l in enumerate(LAYERS):
    _l['order'] = _i
    _l['order_provenance'] = 'DERIVED: the position of `page_anchor` in web/build_3d.py'
    del _l['_at']

# which phases and which weathers each layer actually renders in - derived
# by evaluating the predicate, never listed by hand
for _l in LAYERS:
    _p = _l['renders_when']
    _f, _op, _v = _p['field'], _p['op'], _p['value']
    _fn = PREDICATE_OPS[_op]
    if _f == 'sun_elevation_deg':
        _l['renders_in_phases'] = [x['id'] for x in PHASES
                                   if _fn(x['elevation_deg'], _v)]
        _l['renders_in_weather'] = list(WX_IDS)
    elif _f in ('cloud_cover', 'precipitation_rate'):
        _l['renders_in_phases'] = [x['id'] for x in PHASES]
        _l['renders_in_weather'] = [w for w in WX_IDS
                                    if _fn(_resolved[f'{w}.{_f}'], _v)]
    else:
        _l['renders_in_phases'] = [x['id'] for x in PHASES]
        _l['renders_in_weather'] = list(WX_IDS)
    assert _l['renders_in_phases'], f'layer {_l["id"]}: renders in no phase at all'

_stars_layer = [l for l in LAYERS if l['id'] == 'star-field'][0]
assert _stars_layer['order'] == 1, (
    'the star field is drawn second, under everything but the dome - that is '
    'what the page does and what makes a star behind a cloud impossible')
assert 'noon' not in _stars_layer['renders_in_phases'], \
    'stars at noon: the star predicate is not doing its job'
assert 'night' in _stars_layer['renders_in_phases'], 'no stars at night'

# ------------------------------------------------------------- the stars ---
# Reproducible because it is the PAGE'S generator, run here, branch for
# branch. web/build_3d.py: seeded(seed) is an LCG, x = (x*1664525 +
# 1013904223) mod 2^32, returning x / 2^32; the star loop draws x, y and an
# alpha, then picks a radius with `rnd() < .08 ? 2.1 : rnd() < .32 ? 1.4 :
# .9` - which consumes ONE draw on the bright branch and TWO otherwise.
# Getting that branch wrong would desynchronise the whole sequence, so the
# bins below are a real check on the page and not a decoration.
STAR_SEED = 0x5EEDDA7A
# The literal is FORMATTED from the number, not typed beside it, so changing
# the seed changes what is looked for in the page rather than leaving a
# stale string to agree with the page while the arithmetic has walked off.
STAR_SEED_HEX = '0x' + format(STAR_SEED, 'X')
assert STAR_SEED_HEX in PAGE_SRC, (
    f'the star seed declared here, {STAR_SEED_HEX}, is not a seed '
    f'web/build_3d.py uses. This pack does not hold a second opinion about the '
    f'seed; it holds the page\'s.')
STAR_COUNT_PATH = 'sky.stars.count'
STAR_COUNT = read_path(WORLD, STAR_COUNT_PATH, 'sky.stars')
STAR_RADII = [2.1, 1.4, 0.9]          # the three the page draws, in its order


def lcg(seed):
    x = seed & 0xFFFFFFFF

    def nxt():
        nonlocal x
        x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        return x / 4294967296.0
    return nxt


_rnd = lcg(STAR_SEED)
_bin_counts = {r: 0 for r in STAR_RADII}
for _ in range(STAR_COUNT):
    _rnd(); _rnd(); _rnd()                      # x, y, alpha
    if _rnd() < 0.08:
        _bin_counts[2.1] += 1
    elif _rnd() < 0.32:
        _bin_counts[1.4] += 1
    else:
        _bin_counts[0.9] += 1
assert sum(_bin_counts.values()) == STAR_COUNT, \
    'every star lands in exactly one radius bin or the branch emulation is wrong'

# Magnitudes from the radii, by Pogson's ratio on the drawn disc AREA as a
# stand-in for flux: m_i - m_ref = -2.5 log10(A_i / A_ref), A = pi r^2.
# The ANCHOR is a choice and is labelled one: the brightest class is put at
# magnitude 0.00, which is Vega's defining magnitude. The SPACING between
# the classes is not a choice - it falls out of the radii the page draws.
STAR_ANCHOR_MAG = 0.0
_r_ref = max(STAR_RADII)
STAR_BINS = []
for _r in STAR_RADII:
    _m = STAR_ANCHOR_MAG - 2.5 * math.log10((_r * _r) / (_r_ref * _r_ref))
    STAR_BINS.append({'radius_px': _r, 'magnitude': r4(_m),
                      'count': _bin_counts[_r]})
STAR_CUTOFF = max(b['magnitude'] for b in STAR_BINS)

# What magnitude a REAL sky would have to reach to hold this many stars.
# The rows are the classic all-sky cumulative naked-eye counts (the table
# reproduced in Allen, 'Astrophysical Quantities'); the slope and intercept
# below are a least-squares fit computed here, not a quoted pair.
STAR_COUNT_TABLE = [(1, 15), (2, 48), (3, 171), (4, 513), (5, 1602), (6, 4800)]
_mx = [m for m, _n in STAR_COUNT_TABLE]
_my = [math.log10(n) for _m, n in STAR_COUNT_TABLE]
_mbar = sum(_mx) / len(_mx)
_ybar = sum(_my) / len(_my)
_sxy = sum((a - _mbar) * (b - _ybar) for a, b in zip(_mx, _my))
_sxx = sum((a - _mbar) ** 2 for a in _mx)
STAR_FIT_SLOPE = _sxy / _sxx
STAR_FIT_INTERCEPT = _ybar - STAR_FIT_SLOPE * _mbar
STAR_EQUIV_MAG = (math.log10(STAR_COUNT) - STAR_FIT_INTERCEPT) / STAR_FIT_SLOPE
assert STAR_EQUIV_MAG > STAR_CUTOFF, (
    'the honesty note below claims the drawn field is brighter and shallower '
    'than a real sky of the same star count; the numbers no longer say so')

STARS = {
    'seed': STAR_SEED,
    'seed_hex': STAR_SEED_HEX,
    'seed_provenance': 'READ-FROM-PAGE: web/build_3d.py uses this seed; it is '
                       'asserted present in that file rather than restated as '
                       'an independent choice',
    'generator': 'x = (x * 1664525 + 1013904223) mod 2^32, value x / 2^32 - '
                 'web/build_3d.py, seeded()',
    'count_read_from': f'world/registry/world.json#{STAR_COUNT_PATH}',
    'bins': STAR_BINS,
    'bins_provenance': 'DERIVED: the page\'s own generator run here for the '
                       'star count world/ declares, following the same radius '
                       'branch the page takes, so these are the stars the page '
                       'will actually draw',
    'magnitude_model': 'Pogson: m - m_ref = -2.5 log10(A / A_ref), A = pi r^2, '
                       'on the drawn disc area as a stand-in for flux',
    'magnitude_anchor': STAR_ANCHOR_MAG,
    'magnitude_anchor_provenance': 'AUTHORED: the brightest drawn class is '
                                   'placed at magnitude 0.00, Vega\'s defining '
                                   'magnitude. The anchor is a choice; the '
                                   'spacing between classes is not.',
    'magnitude_cutoff': r4(STAR_CUTOFF),
    'magnitude_cutoff_provenance': 'DERIVED: the faintest magnitude the three '
                                   'drawn radii reach under the model above',
    'equivalent_sky_magnitude': r4(STAR_EQUIV_MAG),
    'equivalent_sky_fit': {
        'table': [list(t) for t in STAR_COUNT_TABLE],
        'table_provenance': 'the classic all-sky cumulative naked-eye star '
                            'counts by visual magnitude, as tabulated in Allen, '
                            '"Astrophysical Quantities". Quoted, not measured '
                            'here, and not from any catalogue file in this repo.',
        'slope': r4(STAR_FIT_SLOPE),
        'intercept': r4(STAR_FIT_INTERCEPT),
        'fit_provenance': 'DERIVED: least squares of log10(N) on magnitude over '
                          'the six tabulated rows, computed in this builder',
    },
    'honesty': 'the drawn field spans '
               f'{r4(STAR_CUTOFF)} magnitudes across three disc sizes, while a '
               'real sky holding as many stars as world/ asks for would have to '
               f'reach about magnitude {r4(STAR_EQUIV_MAG)}. The field is '
               'therefore far too bright and far too shallow to be a sky chart, '
               'which is the same thing world/ already says in its own words: it '
               'is a night sky, not the night sky. No star here has a name, a '
               'position or a catalogue entry.',
    'elevation_cutoff_deg': STAR_ELEV_CUTOFF,
}

# ------------------------------------------------------------ the contract ---
PAGE_CONTRACT = {
    'data': 'the page already parses one blob; add this registry to it as '
            '`D.sky` beside `D.world`, then `const SKYDAY = D.sky;`. Nothing '
            'in here is fetched and nothing is generated at render time.',
    'entry': 'applyPhase(phaseId) sets the sun and the hemisphere for a phase '
             'and nothing else; applyAtmos(campusKey) keeps doing everything '
             'it already does and calls applyPhase last, so a campus change, '
             'a weather change and an hour change all land in one place.',
    'sun_vector': 'the page\'s SUN_OFF is a FIXED direction - (35, 48, 20) '
                  'normalised, which is 49.98 deg of elevation and 29.74 deg '
                  'of azimuth, one permanent mid-morning for all ten campuses. '
                  'Replace the constant with a function of the phase: dir = '
                  '(cos(el)sin(az), sin(el), -cos(el)cos(az)) in three.js axes '
                  'for an azimuth measured clockwise from north, scaled by the '
                  'same 96 m. trackSun() then needs SUN_FWD / SUN_RIGHT / '
                  'SUN_UP rebuilt whenever the phase changes - they are cached '
                  'from SUN_OFF today precisely because it never moved.',
    'intensity': 'the page keeps owning both base numbers. key.intensity stays '
                 '`a.sun.i * w.sun_mul` and gains one factor: '
                 '`* phase.sun.intensity_mul`. hemi.intensity stays '
                 '`a.hemi.i * w.hemi_mul * indoors` and gains '
                 '`* phase.hemi.intensity_mul`. This registry publishes no '
                 'absolute intensity and could not: it does not know what the '
                 'page\'s base is.',
    'colour': 'applyAtmos currently switches the key and hemisphere colours on '
              '`night` and on `w.sun_mul < .7`. Both branches go: the colour '
              'is the phase\'s, every time, and the weather only scales the '
              'strength. The `night` branch\'s 0x9db4d8 is this pack\'s night '
              'phase sun colour, kept identical so the swap changes nothing at '
              'that hour.',
    'gradient': 'compose in the stated order and no other. See `compose_order`.',
    'stars': 'stop keying the star field off `w.stars`. Draw it when the '
             'phase\'s elevation_deg is below the star layer\'s cutoff, then '
             'multiply its alpha by the weather\'s star_visibility - so a clear '
             'night has stars, an overcast one does not, and the two are no '
             'longer the same switch.',
    'disc': 'skyCanvas reads the sun\'s screen position off key.position. That '
            'stays exactly as it is - it is what makes the disc and the '
            'shadows agree - which is why the sun vector must be set from the '
            'phase BEFORE setSky() is called, not after.',
    'must_not_duplicate': [
        'setSky', 'skyCanvas', 'SKY', 'ATMOS', 'WX', 'WX_CYCLE', 'DEF_ATMOS',
        'applyAtmos', 'trackSun', 'SUN_OFF', 'SUN_FWD', 'SUN_RIGHT', 'SUN_UP',
        'skyEnvRT', 'fogBanks', 'darkHex', 'seeded', 'valueNoise', 'hemi', 'key',
    ],
    'must_not_duplicate_why': 'every name above already exists in '
                              'web/build_3d.py and is asserted to exist by this '
                              'pack\'s test. A second setSky or a second star '
                              'seed is the defect this registry exists to '
                              'prevent, not a convenience.',
    'must_read_not_copy': [
        'world.sky.stars.count', 'world.sky.disc', 'world.sky.clouds',
        'world.sky.horizon_haze', 'world.sky.bands', 'world.weather.<id>.cloud',
        'world.weather.<id>.fog_mul', 'world.weather.<id>.fog_tint',
        'world.weather.<id>.sun_mul', 'world.weather.<id>.rain',
        'world.atmos.<id>.sky', 'world.atmos.<id>.haze',
    ],
    'env_map': 'setSky() rebuilds the PMREM environment on every call and '
               'disposes the old render target first. A day cycle calls it far '
               'more often than a weather change does, so the phase must be '
               'stepped rather than interpolated per frame, or the leak check '
               'will be counting PMREM targets every frame.',
    'episode': 'the hour is a view setting. It changes no score, unlocks '
               'nothing, and nothing about which phase a learner chose is '
               'recorded anywhere.',
}

COMPOSE_ORDER = [
    {'step': 1, 'what': 'the campus\'s own four stops',
     'from': 'world.atmos.<campus>.sky',
     'how': 'read, unchanged - this is what keeps a Bay station and a Front '
            'Range yard from ending their domes identically'},
    {'step': 2, 'what': 'the phase gradient',
     'from': 'sky.phases[].gradient.stops',
     'how': 'mixed over the campus stops by 1 - campus_mix, per stop, in sRGB'},
    {'step': 3, 'what': 'the weather tint',
     'from': 'sky.weather_sky.<id>.gradient_tint_hex and tint_mix',
     'how': 'mixed over the result by tint_mix, per stop, in sRGB'},
    {'step': 4, 'what': 'the weather\'s existing sky multiplier',
     'from': 'world.weather.<id>.sky_mul',
     'how': 'the page\'s own darkHex(), unchanged and last, so nothing about '
            'this pack alters what the existing weather switch already does'},
]

HONESTY = {
    'status': 'COMPUTED: the sun\'s elevation and azimuth in every phase, and '
              'the hour of every phase defined by a twilight threshold, are '
              'computed in sky/build.py from a published solar-position series '
              'at a real latitude read from geo/, on a stated day of the year. '
              'Nothing in the geometry was placed by eye.',
    'colours_are_authored': 'every colour in this pack is AUTHORED - chosen by '
                            'eye, one person\'s idea of what a Bay dawn looks '
                            'like, and labelled AUTHORED in each phase\'s own '
                            'provenance block. No colour here is derived from a '
                            'colour temperature, a Rayleigh integral or a '
                            'photograph, and none is measured.',
    'not_a_forecast': 'this is a day, not a date. The cycle is computed for one '
                      'day of the year at one latitude and then used at all ten '
                      'campuses, so a phase\'s hour is right for Treasure Island '
                      'in March and approximately right elsewhere. No campus is '
                      'showing its own sunrise, and the page is not tied to any '
                      'clock, timezone or observation.',
    'time_is_solar': 'positions in the day are local APPARENT SOLAR time, so '
                     'noon is t01 = 0.5 by construction. A civil clock would '
                     'need the equation of time and a zone offset; neither is '
                     'here, and no phase should be presented as a wall-clock '
                     'hour.',
    'one_truth': 'cloud cover, fog density, fog tint, sun strength and rain rate '
                 'are world/\'s and are not copied into this payload - each '
                 'weather entry holds the dotted path instead, and the build '
                 'fails if the path does not resolve. The star count, the '
                 'gradient band names, the disc geometry and the cloud recipe '
                 'are read the same way.',
    'page_owns': 'the page owns the base sun and hemisphere intensities, the '
                 'canvas, the PMREM environment and the shadow frustum. This '
                 'pack publishes multipliers and angles; it publishes no '
                 'absolute intensity, no pixel and no metre.',
    'provenance_word': 'the generated-video provenance word this bundle reserves '
                       'for orbis/ is not used anywhere in this pack and does '
                       'not appear in this payload. A bisection and a table of '
                       'hand-picked colours are not that, and labelling them so '
                       'would be a lie in the flattering direction.',
    # Partly built, and the line between the two halves is the point. This
    # field said "no line of web/build_3d.py reads this registry today"; the
    # page reads it now, and saying so is as much the pack's job as saying
    # the opposite was.
    'built_so_far': 'the page reads this registry. setSun() places the key '
                    'light along the selected phase\'s own elevation and '
                    'azimuth, applyPhase() takes the sun and hemisphere '
                    'colours and intensity multipliers from the phase, the '
                    'star field is up when the phase puts the sun below the '
                    'star layer\'s cutoff and is dimmed rather than culled by '
                    'the weather\'s star_visibility, a weather state that '
                    'pins an hour does so through phase_override, and the '
                    'hour is a control in the top bar and a ?hour= query '
                    'parameter. The six hex literals the page used to switch '
                    'the light with are gone.',
    'gradient_built': 'the gradient is wired too, in the order compose_order '
                      'declares: the campus\'s own four stops stay the base, '
                      'this phase\'s 4 stops mix over them by 1 - campus_mix, '
                      'the weather\'s tint mixes over that by tint_mix, and '
                      'the weather\'s existing sky_mul goes through the '
                      'page\'s own darkHex() last, so nothing here changed '
                      'what the weather switch already did. horizon_haze_mul '
                      'scales the horizon band. Measured on a horizon-facing '
                      'camera at the flagship campus, against noon: golden '
                      'hour 136%, sunset 117%, civil dusk 96%, night 68% - '
                      'the low-sun hours are brighter than noon because a low '
                      'sun lights the whole dome, which is the arc a sky '
                      'actually has and not the one a linear dimmer gives.',
    # Two of the three things this block used to list are not backlog at all:
    # they are decisions, each taken for a stated reason, and filing them
    # under the same word as real backlog made the backlog look bigger than
    # it is AND hid that anyone had decided anything. A reader cannot tell
    # "nobody got to it" from "we considered it and chose otherwise" if both
    # are called not_built_yet. So they are split, and a decision only earns
    # its place here by carrying the reason it was taken.
    'decided': {
        'sun_disc_is_drawn_from_the_light': 'sun_disc is declared here and '
            'deliberately unread. The page draws its disc from the key '
            'light\'s own position, which is what makes the disc and the '
            'shadows agree; a disc driven from this block instead could sit '
            'where the shadows say the sun is not. The block stays as a '
            'record of the geometry, not as a thing waiting to be wired.',
        'the_hour_is_stepped_not_interpolated': 'the hour moves in phases and '
            'never slides between them. setSky() rebuilds the environment map '
            'on every call, so a continuously moving sun would rebuild it '
            'every frame. This is a chosen trade, not an unfinished one.',
    },
    'not_built_yet': 'the layer list and compose_order describe an order the '
                     'page follows but does not read from here. The page is '
                     'handed compose_order in its own blob and re-derives the '
                     'same order in code, so the order has two owners and '
                     'they agree today by inspection rather than by '
                     'construction. That is the one thing in this pack still '
                     'genuinely undone.',
}
assert HONESTY['status'].startswith('COMPUTED:'), \
    'this pack carries the COMPUTED provenance word'

PROVENANCE_WORDS = {
    'COMPUTED': 'produced by a formula in sky/build.py from stated inputs',
    'DERIVED': 'the same, for one field: computed, never placed by eye',
    'CONSTRUCTED': 'follows from a definition (solar midnight, solar noon) or '
                   'from the midpoint of two fixed phases',
    'READ': 'held as a pointer into another registry and resolved at build '
            'time; not a copy',
    'READ-FROM-PAGE': 'taken from web/build_3d.py and asserted present there',
    'AUTHORED': 'chosen by a person, by eye, with no measurement behind it',
}

# ------------------------------------------------------------------ build ---
stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

_gradient_stops = sum(len(p['gradient']['stops']) for p in PHASES)
_authored_hex = sum(
    1 for p in PHASES
    for h in p['gradient']['stops'] + [p['sun']['color_hex'],
                                       p['hemi']['sky_hex'],
                                       p['hemi']['ground_hex']]
) + len(WEATHER_SKY)
_layer_predicates = len(LAYERS) + sum(
    1 for l in LAYERS if 'body_switch' in l['params'])
_derived_numbers = sum(
    1 for p in PHASES for k, v in p['provenance'].items()
    if v in ('DERIVED', 'CONSTRUCTED') and k in ('t01', 'elevation_deg',
                                                 'azimuth_deg'))

doc = {
    'pack': 'smartcitix-trade-craft-academy-sky',
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'counts': {
        'phases': len(PHASES),
        'solved_phases': sum(1 for p in PHASES if p['t01_by'] == 'solved'),
        'constructed_phases': sum(1 for p in PHASES
                                  if p['t01_by'] == 'construction'),
        'phases_above_horizon': sum(1 for p in PHASES
                                    if p['elevation_deg'] > RISEN_DISC_DEG),
        'stops_per_gradient': STOPS,
        'gradient_stops': _gradient_stops,
        'weather_sky_entries': len(WEATHER_SKY),
        'weather_reads': len(WEATHER_SKY) * len(WEATHER_READS),
        'weather_reads_per_entry': len(WEATHER_READS),
        'precipitating_weather': sum(
            1 for w in WX_IDS if WEATHER_SKY[w]['precipitation'] != 'none'),
        'layers': len(LAYERS),
        'layer_predicates': _layer_predicates,
        'layer_phase_renders': sum(len(l['renders_in_phases']) for l in LAYERS),
        'layer_weather_renders': sum(len(l['renders_in_weather']) for l in LAYERS),
        'star_magnitude_bins': len(STAR_BINS),
        'star_count_rows': len(STAR_COUNT_TABLE),
        'authored_hex_colours': _authored_hex,
        'derived_sun_numbers': _derived_numbers,
        'reserved_page_names': len(PAGE_CONTRACT['must_not_duplicate']),
        'compose_steps': len(COMPOSE_ORDER),
        'reads_files': len(READS),
    },
    'site': {
        'campus': SITE_CAMPUS,
        'lat_deg': SITE_LAT,
        'lon_deg': SITE_LON,
        'lat_provenance': SITE_LAT_PROV,
        'lat_source': SITE_LAT_SRC,
        'lat_read_from': f'geo/registry/campuses_geo.json#campuses.{SITE_CAMPUS}.lat',
        'day_of_year': DAY_OF_YEAR,
        'day_why': 'the March equinox - the single day whose sun path is closest '
                   'to the annual mean. A solstice would make every phase in the '
                   'table unrepresentative of the rest of the year.',
        'time_base': TIME_BASE,
        'longitude_unused': 'the longitude is published because the campus has '
                            'one, and is NOT used: apparent solar time removes '
                            'it, along with the timezone and the equation of '
                            'time.',
        'declination_formula': 'Spencer 1971, Fourier series for solar '
                               'declination, as published by the NOAA Solar '
                               'Calculator',
        'elevation_formula': 'sin(h) = sin(phi)sin(dec) + cos(phi)cos(dec)cos(H) '
                             '- Meeus, Astronomical Algorithms 2nd ed., 13.6',
        'azimuth_formula': 'A = atan2(sin H, cos H sin(phi) - tan(dec) cos(phi)) '
                           '- Meeus 13.5, from south positive west, published '
                           'here rotated to degrees clockwise from true north',
        'refraction': 'none applied. The formulae return the GEOMETRIC altitude '
                      'of the disc centre, which is why the risen-disc phases '
                      'target -0.833 deg rather than 0.',
        'solver': f'bisection, {BISECT_STEPS} fixed halvings per solved phase - '
                  f'fixed rather than to a tolerance so the result is a '
                  f'deterministic function of the inputs',
        'rounding': f'every derived number is published to {R4} decimals',
        'risen_disc_deg': RISEN_DISC_DEG,
    },
    'provenance_words': PROVENANCE_WORDS,
    'phases': PHASES,
    'weather_sky': WEATHER_SKY,
    'weather_reads': WEATHER_READS,
    'precipitation_predicate': PRECIP_PREDICATE,
    'predicate_fields': PREDICATE_FIELDS,
    'predicate_ops': sorted(PREDICATE_OPS),
    'layers': LAYERS,
    'stars': STARS,
    'compose_order': COMPOSE_ORDER,
    'page_contract': PAGE_CONTRACT,
    'reads': READS,
}

# -- the counts are computed above and tied here to the things they count,
# -- so a count and its subject cannot drift apart without the build saying so
assert doc['counts']['gradient_stops'] == doc['counts']['phases'] * STOPS, \
    'every phase carries one gradient of one stop per band'
assert (doc['counts']['solved_phases'] + doc['counts']['constructed_phases']
        == doc['counts']['phases']), 'a phase is solved or constructed, never both'
assert doc['counts']['weather_sky_entries'] == len(WX_IDS), \
    'one sky treatment per weather state world/ declares, and no more'
assert doc['counts']['derived_sun_numbers'] == doc['counts']['phases'] * 3, \
    'every phase publishes a derived t01, elevation and azimuth'

# -- nothing world owns is sitting in this payload as a value. A numeric
# -- scan would fire on coincidence (an authored 0.5 is not a copied 0.5), so
# -- the check is structural and exact instead: a weather entry may hold the
# -- POINTER under `reads` and must not hold the field at all, and none of
# -- world's own weather field names may appear as a key beside it.
WORLD_WX_FIELDS = sorted({k for w in need(WORLD, 'weather', 'world.json').values()
                          for k in w})
for _wid in WX_IDS:
    _e = WEATHER_SKY[_wid]
    for _local, _wkey in WEATHER_READS.items():
        assert _local not in _e, (
            f'weather_sky.{_wid}: holds {_local!r} as a field of its own. World '
            f'owns weather.{_wid}.{_wkey}; hold the pointer under `reads`, not '
            f'a second copy of the number.')
        _ptr = need(need(_e, 'reads', f'weather_sky.{_wid}'), _local,
                    f'weather_sky.{_wid}.reads')
        assert _ptr == f'weather.{_wid}.{_wkey}', (
            f'weather_sky.{_wid}.reads.{_local} must be the dotted path '
            f'weather.{_wid}.{_wkey}, not {_ptr!r}')
        assert isinstance(_ptr, str), 'a read is a path, never a value'
    for _bad in WORLD_WX_FIELDS:
        assert _bad not in _e, (
            f'weather_sky.{_wid}: {_bad!r} is a field world/registry/world.json '
            f'already owns on this same weather state. One truth per fact.')


def _numbers_in(o):
    if isinstance(o, bool):
        return []
    if isinstance(o, (int, float)):
        return [o]
    if isinstance(o, dict):
        return [n for v in o.values() for n in _numbers_in(v)]
    if isinstance(o, list):
        return [n for v in o for n in _numbers_in(v)]
    return []


assert STAR_COUNT not in _numbers_in(STARS), (
    f'the star count {STAR_COUNT} is world/registry/world.json\'s '
    f'({STAR_COUNT_PATH}) and appears as a number in this pack\'s star block. '
    f'The bins are derived FROM it; the count itself stays where it lives.')
assert 'count' not in STARS, \
    'the star block names where the count is read from; it does not hold one'

_payload = json.dumps(doc)

# -- no network, anywhere, in anything
assert 'http://' not in _payload and 'https://' not in _payload, \
    'nothing in this pack is fetched: no URL may appear in the payload'
# -- orbis owns the generated-video word; it is not borrowed here
assert 'AI-SYNTHESIZED' not in _payload, \
    'that provenance word belongs to orbis/ and would be a false label here'

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'sky.json').write_text(json.dumps(doc, indent=1) + '\n')

c = doc['counts']
print(f"sky: {c['phases']} phases "
      f"({c['solved_phases']} solved from a twilight definition, "
      f"{c['constructed_phases']} constructed), "
      f"{c['phases_above_horizon']} of them with the disc fully up; "
      f"{c['gradient_stops']} gradient stops over {c['stops_per_gradient']} bands; "
      f"{c['weather_sky_entries']} weather skies holding {c['weather_reads']} "
      f"pointers into world/ and copying none of it; "
      f"{c['layers']} draw layers, order read off the page, "
      f"{c['layer_predicates']} predicates; "
      f"{c['star_magnitude_bins']} star bins from the page's own seed "
      f"(cutoff {doc['stars']['magnitude_cutoff']} mag against "
      f"{doc['stars']['equivalent_sky_magnitude']} for a real sky); "
      f"noon sun {_noon['elevation_deg']} deg at lat {SITE_LAT} "
      f"(source stamp {stamp})")
