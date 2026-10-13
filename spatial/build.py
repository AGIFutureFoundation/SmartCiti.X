#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the spatial-fabric registry builder.

A "spatial fabric", in the sense the Metaverse Standards Forum's Open
Metaverse Browser Initiative (OMBI) uses the phrase, is the metaverse
equivalent of a website: a mapped coordinate space containing content and
services, self-hosted, accessed by proximity, and composed with other
fabrics by a browser through a multi-origin scene graph with per-branch
ownership. This pack publishes the Academy as one such fabric - as static
files a plain web server serves next to the site - and it draws the
honesty line in exactly two places:

  CLAIMED.  OGC GeoPose 1.0 (OGC 21-056r11, application/geopose+json),
  a published standard with a confirmed Basic-YPR JSON encoding. Every
  campus, institution anchor and pinned restoration site gets one, its
  horizontal position copied at build time from the registry that owns
  it (geo/, restoration/) at that registry's own provenance. This bundle
  holds NO heights and NO headings for any of them (elevation exists only
  as an on-request live USGS fetch in the learner's browser, never stored),
  so h and yaw/pitch/roll are emitted as 0 with an explicit UNKNOWN
  sidecar beside every pose. Nothing is invented to fill the slot.

  NOT CLAIMED.  The OMBI fabric manifest, the Scene Object Model (SOM) and
  RMAP. Their normative texts were not reachable from this build, so the
  manifest and scene graph here are SHAPED after the public deck and
  press (Q3 2026), not validated against a specification, not loaded in
  any metaverse browser (Sneeze, Artemis), and registered in meta/ under
  not_claimed with the reason. No RMAP endpoint, no server, no network,
  no DID is minted.

Every other operator this fabric points at - a restoration site's own
organization, the Navy/EPA/DTSC at Hunters Point, the Navy/DTSC/CDPH at
Former Naval Station Treasure Island, a port authority, a
university, a neighbouring city - is a SEPARATE ORIGIN: named, located,
and never content this fabric serves for them. That is the SOM's own
per-branch-ownership idea, and it is the same "not affiliated" line every
other pack in this bundle already holds.

No fact is typed here. Coordinates, names, provenance, categories, hall
counts, atmospheres, simulators, advisors, cribs and export doors are all
read at build time from the registries that own them, so there is one
truth, and the build asserts that every pose still equals its source.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here (this
# pack had drifted to 1.0.0 while ROADMAP said 3.2.0 was unified everywhere).
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
# BUILT is a LABEL, not a fact read from anywhere: the date this builder's
# output last changed shape, set by hand when it does. The fact a suite can
# check is the source_stamp beside it. PROBE_DATE below is different - it is
# the date of a measurement and travels with the measurement it dates.
BUILT = "2026-09-26"

PRODUCT = 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)'

# ------------------------------------------------------------------ inputs ---
geo = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))
resto = json.load(open(ROOT / 'restoration/registry/restoration.json'))
meta = json.load(open(ROOT / 'meta/registry/metaverse.json'))
campuses_root = json.load(open(ROOT / 'unions/registry/campuses.json'))
campuses_reg = campuses_root['campuses']
unions_root = json.load(open(ROOT / 'unions/registry/unions.json'))
unions = unions_root['unions']
sims = json.load(open(ROOT / 'sims/registry/sims.json'))
advisors = json.load(open(ROOT / 'agents/registry/advisors.json'))
schools = json.load(open(ROOT / 'schools/registry/schools.json'))
world = json.load(open(ROOT / 'world/registry/world.json'))
tools = json.load(open(ROOT / 'tools/registry/toolcribs.json'))
training = json.load(open(ROOT / 'training/registry/training.json'))
roadmap = json.load(open(ROOT / 'roadmap/registry/roadmap.json'))
terrain = json.load(open(ROOT / 'terrain/registry/terrain.json'))
parcels = json.load(open(ROOT / 'parcels/registry/parcels.json'))


def need(obj, key, where):
    """One key, or a build failure that says which key and where. There is
    no default arm (spec §23.1: a default is a policy decision): a default
    here would turn a moved field into a plausible-looking value."""
    if not isinstance(obj, dict):
        raise TypeError(f'spatial: {where}: expected an object to read {key!r} from')
    if key not in obj:
        raise KeyError(f'spatial: {where}: no key {key!r} (it holds {sorted(obj)[:12]})')
    return obj[key]

# ------------------------------------------------------------ the two labels ---
ENCODING = ('OGC GeoPose 1.0 Basic-YPR, OGC 21-056r11, '
            'application/geopose+json')
MEDIA_TYPE = 'application/geopose+json'
SHAPE = ('authored from the public OMBI deck and press, Q3 2026 - not '
         'validated against a normative specification, and not loaded in '
         'any metaverse browser (Sneeze, Artemis) by this build')
H_PROV = ('UNKNOWN - not held by this bundle; 0.0 is a placeholder, not a '
          'measurement')
O_PROV = 'UNKNOWN - no heading is recorded; 0 is a placeholder'

# The flagship campus every bundle-wide service is anchored at. WHICH campus
# is the flagship is a design decision unions/registry/campuses.json owns
# (`flagship: true` on exactly one campus); it used to be a slug typed here,
# and 45% of the fabric's placement rested on that string. Zero or two
# claimants fail the build by name; there is no fallback slug.
_flagships = [ck for ck, c in campuses_reg.items()
              if need(c, 'flagship', f'unions/registry/campuses.json#campuses.{ck}')]
if len(_flagships) != 1:
    raise ValueError('spatial: unions/registry/campuses.json must flag exactly one '
                     f'campus as the flagship; it flags {_flagships}')
FLAGSHIP = _flagships[0]
assert FLAGSHIP in geo['campuses'], f'flagship {FLAGSHIP} has no pose in geo/'

# ---------------------------------------------------- the reachability probe ---
# The honesty block used to ASSERT that the OMBI normative texts were not
# reachable. This is the MEASUREMENT: one curl per URL from the build
# container, through its egress proxy, TLS verification on, on the date
# given. The codes are recorded here as data - the build itself fetches
# nothing (static_files_only_no_rmap) - and both the build and the suite
# refuse a 2xx: the day one of these answers, the text is readable and the
# "shaped after the deck" label is stale, so the pack must be REVISITED,
# loudly, rather than keep saying unreachable.
# Measured twice, one curl per URL each time, and the codes were the same
# on both dates. PROBE_DATE is the later measurement, the one the codes
# below are copied from; PROBE_DATES lists both.
PROBE_DATES = ['2026-09-25', '2026-09-26']
PROBE_DATE = PROBE_DATES[-1]
PROBE_HOW = ("curl -sS -o /dev/null -w '%{http_code}' --max-time 20 <url>, once "
             'per URL per date, from the build container through its egress '
             'proxy with TLS verification on and HTTPS_PROXY as configured; no '
             'retry loop, no proxy bypass, no TLS switched off')
DENIED = ('HTTP 403 from the egress proxy: the CONNECT was refused '
          '(organization policy denial), nothing from the host itself')
NO_RESPONSE = ('no HTTP response at all: curl exited 56, "CONNECT tunnel '
               'failed, response 403", so %{http_code} printed 000; the proxy '
               'status log records "gateway answered 403 to CONNECT" for this '
               'host')
PROBE = [
    {'url': 'https://github.com/rp1-com',
     'sought': 'the RP1 organization - OMBI lead architect and maintainer',
     'http_code': '403', 'curl_exit': 0, 'meaning': DENIED},
    {'url': 'https://github.com/open-metaverse-browser',
     'sought': 'the Open Metaverse Browser Initiative organization',
     'http_code': '403', 'curl_exit': 0, 'meaning': DENIED},
    {'url': 'https://api.github.com/search/repositories?q=ombi+spatial+fabric',
     'sought': 'a repository search for the fabric-manifest / SOM / RMAP texts',
     'http_code': '403', 'curl_exit': 0, 'meaning': DENIED},
    {'url': 'https://metaverse-standards.org/',
     'sought': "the Metaverse Standards Forum's own site, OMBI's home",
     'http_code': '000', 'curl_exit': 56, 'meaning': NO_RESPONSE},
    {'url': 'https://docs.ogc.org/is/21-056r11/21-056r11.html',
     'sought': 'OGC GeoPose 1.0 (21-056r11), the one CLAIMED standard - its '
               'text was not readable from here either; the Basic-YPR '
               'encoding used is the one confirmed in the brief and in the '
               'OSCP GeoPose Protocol',
     'http_code': '000', 'curl_exit': 56, 'meaning': NO_RESPONSE},
]
assert len({pr['url'] for pr in PROBE}) == len(PROBE), 'a probe URL repeats'
for pr in PROBE:
    code = need(pr, 'http_code', f'reachability_probe {pr["url"]}')
    assert re.fullmatch(r'[0-9]{3}', code), (pr['url'], code)
    assert pr['url'].startswith('https://'), pr['url']
    assert isinstance(need(pr, 'curl_exit', pr['url']), int)
    if code.startswith('2'):
        raise SystemExit(
            f'REVISIT spatial: {pr["url"]} answered HTTP {code} on {PROBE_DATE} '
            '- the OMBI/OGC text may now be readable, and the not-claimed shape '
            'label is stale until someone reads it. This build refuses to keep '
            'saying unreachable.')
N_PROBE_2XX = sum(1 for pr in PROBE if pr['http_code'].startswith('2'))
assert N_PROBE_2XX == 0

# The glTF export door: what the page does when the .glb button is pressed,
# as read from web/build_3d.py (exportGlb) - said here so a SOM consumer
# knows where a mesh could be fetched from and by whom.
EXPORT_TRANSPORT = ('learner-triggered, in the learner\'s own browser: the '
                    'running page serialises the live scene with three.js '
                    'GLTFExporter ({binary: true}) and hands the bytes to the '
                    'browser as a model/gltf-binary download - wrapped in a '
                    'STORE-method .zip where a host mediates saves. No server, '
                    'no network, no file on disk, nothing fetched.')

HONESTY = {
    'geopose_claimed': 'OGC GeoPose 1.0 (OGC 21-056r11) is a published '
                       'standard with a confirmed Basic-YPR JSON encoding, '
                       'and it is claimed outright: every pose in '
                       'geopose.json is exactly {position: {lat, lon, h}, '
                       'orientation: {yaw, pitch, roll}}, lat/lon in '
                       'degrees, h in metres, angles in degrees, LTP-ENU '
                       'inner frame. The horizontal position is copied at '
                       'build time from the registry that owns it and '
                       'carries that registry\'s own provenance word '
                       '(RECORDED / DERIVED / AUTHORED) and source string.',
    'no_heights_or_headings': 'this bundle holds no height and no heading '
                              'for any campus, anchor or site - elevation '
                              'exists only as an on-request live USGS 3DEP '
                              'lookup in the learner\'s own browser, never '
                              'stored - so every pose emits h = 0.0 and '
                              'yaw = pitch = roll = 0 with an explicit '
                              'UNKNOWN sidecar beside it. A zero here is a '
                              'placeholder, never a measurement, and no '
                              'height or heading is invented to fill the '
                              'slot.',
    'ombi_not_claimed': 'the OMBI spatial-fabric manifest, the Scene '
                        'Object Model (SOM) and RMAP are marked "OMBI - '
                        'New" in the public deck and their normative texts '
                        'were not reachable from this build, so fabric.json '
                        'and som.json are SHAPED after the deck\'s '
                        'vocabulary, not validated against a specification. '
                        'They are registered in meta/registry/metaverse.json '
                        'under not_claimed, with the reason, and never under '
                        'standards.',
    'static_files_only_no_rmap': 'this fabric is static files a plain web '
                                 'server serves next to the site - the '
                                 'deck\'s own "publish 3D content like a '
                                 'website" point. No RMAP endpoint, no '
                                 'server, no WebSocket, no fetch at build '
                                 'time, no DID minted: the identity field is '
                                 'honestly null. Every service listed runs '
                                 'in-page with no network, and every '
                                 'anchored .glb is produced on demand by the '
                                 'learner\'s browser, not a file sitting on '
                                 'disk. Anchoring the bundle-wide services '
                                 '(advisors, Schools panel, restoration panel, '
                                 'training recorder) at the flagship campus is '
                                 'a DESIGN decision unions/registry/campuses.json '
                                 'owns (flagship: true on exactly one campus), '
                                 'not a fact about where anything physically is.',
    'external_origins': 'every other operator this fabric points at - a '
                        'restoration site\'s own organization, the US Navy, '
                        'EPA Region 9 and California DTSC at Hunters Point, '
                        'the US Navy, California DTSC and CDPH at Former '
                        'Naval Station Treasure Island, '
                        'a port authority, a university, a museum, a '
                        'neighbouring city - is a separate origin: named, '
                        'located by its own pose, and never content this '
                        'fabric serves for them (served_by_this_fabric is '
                        'false on every one). That is the SOM\'s per-branch '
                        'ownership idea, and it is the same "not affiliated" '
                        'line restoration/ and geo/ already hold. The 111 '
                        'union halls\' real organizations are deliberately '
                        'NOT listed as origins: the halls here are '
                        'SCHEMATIC training buildings named after a craft, '
                        'not a union\'s premises.',
    'not_loaded_in_any_browser': 'nothing here has been opened in Sneeze, '
                                 'Artemis or any other metaverse browser. '
                                 'The only consumers this pack can defend '
                                 'are a reader of application/geopose+json '
                                 'and this bundle\'s own suite '
                                 '(spatial/test.mjs), which holds every pose '
                                 'against its source registry on every run.',
    'reachability_probe': {
        'date': PROBE_DATE,
        'dates': PROBE_DATES,
        'same_codes_on_every_date': True,
        'how': PROBE_HOW,
        'tried': PROBE,
        'answered_2xx': N_PROBE_2XX,
        'so': 'this is why OMBI is not claimed: none of the hosts that would '
              'hold the fabric-manifest, SOM or RMAP normative text answered '
              'from this build, so fabric.json and som.json remain SHAPED '
              'after the deck and are registered in meta/ under not_claimed',
        'revisit_rule': 'if any URL above ever answers 2xx the pack must be '
                        'REVISITED: spatial/build.py refuses to build and '
                        'spatial/test.mjs fails by URL, rather than quietly '
                        'keep saying unreachable',
        'provenance': 'RECORDED - each code is what curl returned on the date '
                      'given; nothing here is assumed, and the build itself '
                      'fetched nothing',
    },
}

SOURCES = [
    {'what': 'The Case for the Metaverse Browser - Metaverse Standards Forum '
             '/ OMBI / RP1 deck, Q3 2026',
     'how': 'user-supplied; the source of the fabric / SOM / RMAP '
            'vocabulary the manifest and scene graph are shaped after',
     'provenance': 'AUTHORED from the deck as supplied; the deck is not in '
                   'this repository and this build fetched nothing'},
    {'what': 'Metaverse Standards Forum press release: Sneeze, the open '
             'metaverse browser engine, introduced June 15 2026 under the '
             'Apache 2.0 licence through the Open Metaverse Browser '
             'Initiative, RP1 lead architect and maintainer',
     'url': 'https://metaverse-standards.org/news/press-releases/'
            'metaverse-standards-forum-introduces-sneeze-the-worlds-first-'
            'open-metaverse-browser-engine/',
     'repo': 'github.com/MetaversalCorp/Sneeze (as cited in the deck)',
     'provenance': 'AUTHORED from public press; no code from that '
                   'repository is vendored, run or read by this bundle'},
    {'what': 'RP1 launches Artemis, a native metaverse browser built on '
             'Sneeze, July 2026',
     'url': 'https://www.businesswire.com/news/home/20260706640660/en/'
            'RP1-Launches-Artemis-the-Worlds-First-Native-Metaverse-Browser',
     'provenance': 'AUTHORED from public press; this fabric has not been '
                   'loaded in it'},
    {'what': 'OGC GeoPose 1.0 Data Exchange Standard, OGC 21-056r11, '
             'Basic-YPR and Basic-Quaternion JSON encodings, media type '
             'application/geopose+json',
     'provenance': 'the one published standard here, claimed; docs.ogc.org '
                   'was not reachable from this build, the Basic-YPR '
                   'encoding used is the one confirmed in the brief and '
                   'in the OSCP GeoPose Protocol '
                   '(github.com/OpenArCloud/oscp-geopose-protocol)'},
]


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


# ------------------------------------------------------------------ poses ---
def make_pose(kind, ident, name, campus, lat, lng, prov, source):
    """One GeoPose Basic-YPR with its provenance sidecar. The `geopose`
    member is the encoding exactly; everything beside it is ours."""
    assert -90 <= lat <= 90 and -180 <= lng <= 180, (kind, ident, lat, lng)
    assert prov in ('RECORDED', 'DERIVED', 'AUTHORED'), (kind, ident, prov)
    return {
        'subject': {'kind': kind, 'id': ident, 'name': name, 'campus': campus,
                    'ref': f'{kind}:{ident}'},
        'geopose': {
            'position': {'lat': lat, 'lon': lng, 'h': 0.0},
            'orientation': {'yaw': 0, 'pitch': 0, 'roll': 0},
        },
        'provenance': {
            'position_horizontal': prov,
            'source': source,
            'h_provenance': H_PROV,
            'orientation_provenance': O_PROV,
        },
    }


poses = []
for ck, c in geo['campuses'].items():
    assert ck in campuses_reg, f'geo campus {ck} is not a union-registry campus'
    poses.append(make_pose('campus', ck, campuses_reg[ck]['name'], ck,
                           c['lat'], c['lng'], c['provenance'], c['source']))
n_campuses = len(poses)

for ck, lst in geo['anchors'].items():
    for a in lst:
        p = make_pose('anchor', f'{ck}/{slug(a["name"])}', a['name'], ck,
                      a['lat'], a['lng'], a['provenance'], a['source'])
        p['anchor'] = {'km_from_campus': a['km'],
                       'bearing_from_campus_deg': a['bearing_deg'],
                       # a heuristic on geo/'s source string, pending a
                       # `kind` field geo/ would own: the city anchors are the
                       # ones copied from the Locator.X CITIES table
                       'kind': 'city' if 'CITIES' in a['source'] else 'institution'}
        poses.append(p)
n_anchors = len(poses) - n_campuses

unposed = []
for s in resto['sites']:
    if not s['pin']:
        assert s['lat'] is None and s['lng'] is None
        unposed.append({
            'subject': {'kind': 'restoration-site', 'id': s['id'],
                        'name': s['name'], 'campus': s['campus'],
                        'ref': f'restoration-site:{s["id"]}'},
            'why': 'no GeoPose: the registry pins no single coordinate for '
                   'this bay-wide program (pin: false, lat/lng null), and '
                   'this build invents none',
            'org': s['org'],
        })
        continue
    # the restoration registry states its provenance once, for every site,
    # in its honesty block: AUTHORED FROM PUBLIC RECORD
    assert 'AUTHORED FROM PUBLIC RECORD' in resto['honesty']['provenance']
    p = make_pose('restoration-site', s['id'], s['name'], s['campus'],
                  s['lat'], s['lng'], 'AUTHORED',
                  f'restoration/registry/restoration.json - {s["source_url"]}')
    p['site'] = {'org': s['org'], 'category': s['category'],
                 'walkable': s['walkable'],
                 'walkable_reason': need(s, 'walkable_reason',
                                         f'restoration site {s["id"]}')}
    poses.append(p)
n_sites = len(poses) - n_campuses - n_anchors

REF = {p['subject']['ref']: p for p in poses}
assert len(REF) == len(poses), 'a pose ref collides'
assert n_campuses == len(campuses_reg) == need(
    campuses_root, 'count', 'unions/registry/campuses.json')
# The anchor count is geo/'s to publish, not this pack's to remember. It
# was typed as == 47 here, and the day geo/ densified its Bay anchors from
# the Locator.X table that literal was the only thing standing between a
# correct rebuild and a failed one. The tie to geo/ is the check; a second
# copy of the number is not.
assert n_anchors == sum(len(v) for v in geo['anchors'].values())
assert n_anchors > 0, 'spatial: no anchors came through from geo/'
assert n_sites == sum(1 for s in resto['sites'] if s['pin'])
assert len(unposed) == sum(1 for s in resto['sites'] if not s['pin'])
assert n_sites + len(unposed) == len(resto['sites'])

# every pose equals its source, exactly, and every zero is labelled
for p in poses:
    sub, g = p['subject'], p['geopose']
    if sub['kind'] == 'campus':
        src = geo['campuses'][sub['id']]
    elif sub['kind'] == 'anchor':
        ck, nm = sub['id'].split('/', 1)
        src = next(a for a in geo['anchors'][ck] if slug(a['name']) == nm)
    else:
        src = next(s for s in resto['sites'] if s['id'] == sub['id'])
    assert g['position']['lat'] == src['lat'] and g['position']['lon'] == src['lng'], \
        f'{sub["ref"]} drifted from its source registry'
    assert g['position']['h'] == 0.0 and all(
        g['orientation'][k] == 0 for k in ('yaw', 'pitch', 'roll'))
    assert list(g) == ['position', 'orientation']
    assert list(g['position']) == ['lat', 'lon', 'h']
    assert list(g['orientation']) == ['yaw', 'pitch', 'roll']

# ------------------------------------------------------------------ doors ---
# A door is the deep link a browser would open for a node: this bundle's own
# entry page and the one URL parameter that page validates against its own
# roster (D.halls, D.sims.sims, D.campuses). The value is never typed: it is
# the key of the registry entry the node was built from. A door with no
# parameter is the entry page itself - the locker and the .glb button open
# from its bar, not from a URL.
ENTRY = 'web/trade_craft_3d.html'
DOOR_PARAMS = ('hall', 'sim', 'campus')


def door(param, value):
    if param is None:
        assert value is None
        return {'page': ENTRY, 'param': None, 'value': None, 'href': ENTRY}
    assert param in DOOR_PARAMS, param
    assert isinstance(value, str) and value, (param, value)
    return {'page': ENTRY, 'param': param, 'value': value,
            'href': f'{ENTRY}?{param}={value}'}


# The built page is the measurement a door is held against: which URL
# parameters it reads, the rosters it validates them with, and that the
# .glb export door is really in it. `--bootstrap` (the page not yet built)
# skips the measurement and says so in the output; the suite then fails,
# which is right - a bootstrap build is not a verified one.
BOOTSTRAP = '--bootstrap' in sys.argv
PAGE = None if BOOTSTRAP else (ROOT / ENTRY).read_text()
PARAMS_READ = None
ROSTERS = None
if PAGE is not None:
    PARAMS_READ = sorted(set(re.findall(r"params\.get\('([a-z]+)'\)", PAGE)))
    assert set(DOOR_PARAMS) <= set(PARAMS_READ), \
        f'the 3D page no longer reads every door parameter: reads {PARAMS_READ}'
    # the page must validate each parameter against the roster named here -
    # matched as the code it emits, not as prose
    assert "D.halls.some(h => h.slug === params.get('hall'))" in PAGE
    assert "Object.keys(D.sims.sims).includes(params.get('sim'))" in PAGE
    assert "D.campuses[params.get('campus')]" in PAGE
    _m = re.search(r'<script id="data" type="application/json">(.*?)</script>',
                   PAGE, re.S)
    assert _m, 'the 3D page carries no data block'
    _D = json.loads(_m.group(1))
    ROSTERS = {'hall': sorted(h['slug'] for h in _D['halls']),
               'sim': sorted(_D['sims']['sims']),
               'campus': sorted(_D['campuses'])}
    for _needle in ('GLTFExporter', '{ binary: true }', 'model/gltf-binary',
                    'id="glbBtn"', 'async function exportGlb(root, name)'):
        assert _needle in PAGE, f'the 3D page lost its glTF export door: {_needle}'


def door_resolves(d):
    """True when the built page really opens this door: the value is in the
    roster the page validates that parameter against, or - for the entry
    page itself - the page exists. None when nothing was measured."""
    if ROSTERS is None:
        return None
    if d['param'] is None:
        return (ROOT / d['page']).exists()
    return d['value'] in ROSTERS[d['param']]


# ---------------------------------------------------------------- the fabric ---
hall_home = {}
for ck, c in campuses_reg.items():
    for h in c['halls']:
        assert h not in hall_home, f'hall {h} has two home campuses'
        hall_home[h] = ck
assert set(hall_home) == {u['slug'] for u in unions}, \
    'the campus registry does not home exactly the 111 union halls'
district_home = {d: ck for ck, c in campuses_reg.items() for d in c['districts']}

places = []
for ck, c in campuses_reg.items():
    assert ck in world['atmos'], f'{ck} has no atmosphere in world/'
    assert ck in roadmap['built_campuses'], f'{ck} is not a built campus'
    places.append({
        'id': f'place:{ck}',
        'name': c['name'],
        'geopose': f'campus:{ck}',
        'kind': 'hub' if not c['districts'] else 'district',
        'districts': list(c['districts']),
        'halls': len(c['halls']),
        'atmosphere': ck,
        'atmosphere_character': world['atmos'][ck]['character'],
        'walk': True,
        'walk_why': 'a BUILT entry in roadmap/registry/roadmap.json: a '
                    'walkable campus city in web/trade_craft_3d.html',
        'door': door('campus', ck),
    })

exports = {e['id']: e for e in meta['exports']}
assert set(exports) == {'avatar-glb', 'hall-glb'}
GLB_NOTE = ('exported by the learner\'s own browser from the running page '
            '(the .glb button), not a file sitting on disk')
AVATAR_FILE = need(exports['avatar-glb'], 'file', 'meta exports avatar-glb')
HALL_FILE = need(exports['hall-glb'], 'file', 'meta exports hall-glb')
assert AVATAR_FILE.endswith('.glb') and HALL_FILE.endswith('.glb'), (AVATAR_FILE, HALL_FILE)
assert '<slug>' in HALL_FILE, HALL_FILE
anchored_content = [{
    'export': 'avatar-glb',
    'scene': AVATAR_FILE[:-len('.glb')],
    'file': AVATAR_FILE,
    'format': 'glTF 2.0 binary',
    'produced_on_demand': True,
    'how': GLB_NOTE,
    'anchored_at': None,
    'why_unanchored': 'the avatar is the learner\'s own and travels with '
                      'them; it stands nowhere on the map',
    'door': door(None, None),
    'door_scope': 'the entry page: the locker opens from its bar, no URL '
                  'parameter names it',
    'provenance': 'SCHEMATIC',
}]
for u in unions:
    _file = HALL_FILE.replace('<slug>', u['slug'])
    anchored_content.append({
        'export': 'hall-glb',
        'scene': _file[:-len('.glb')],
        'file': _file,
        'format': 'glTF 2.0 binary',
        'produced_on_demand': True,
        'how': GLB_NOTE,
        'anchored_at': f'campus:{hall_home[u["slug"]]}',
        'hall': u['slug'],
        'name': u['name'],
        'door': door('hall', u['slug']),
        'provenance': 'SCHEMATIC',
    })
assert len(anchored_content) == 1 + len(unions) == 1 + need(
    unions_root, 'count', 'unions/registry/unions.json')

TRANSPORT = 'in-page, no network'
services = []
campus_order = list(campuses_reg)
for sk, s in sims['sims'].items():
    hosting = sorted({hall_home[h] for h in s['halls']},
                     key=campus_order.index)
    assert hosting, f'sim {sk} binds no homed hall'
    assert need(s, 'operator', f'sims/registry/sims.json#sims.{sk}'), \
        f'sim {sk} declares no scripted operator'
    services.append({
        'id': f'sim:{sk}',
        'kind': 'simulator',
        'name': s['name'],
        'registry': 'sims/registry/sims.json',
        'transport': TRANSPORT,
        'anchored_at': f'campus:{hosting[0]}',
        'also_at': [f'campus:{c}' for c in hosting[1:]],
        'halls': len(s['halls']),
        'operator': {'levels': list(s['operator']['levels']),
                     'scripted_reference': True},
        'door': door('sim', sk),
        'door_scope': 'the seat itself: the door lands in the simulator, on '
                      'the campus that homes the first of its bound halls',
        'provenance': 'SCHEMATIC',
    })
PAGE_WIDE = ('page-wide: opens from the bar on every campus; the door lands on '
             'the campus the service is anchored at')
services.append({
    'id': 'advisors',
    'kind': 'scripted-advisors',
    'name': f'{advisors["counts"]["advisors"]} scripted advisors, '
            f'{advisors["counts"]["topics"]} fixed topics',
    'registry': 'agents/registry/advisors.json',
    'transport': TRANSPORT,
    'anchored_at': f'campus:{FLAGSHIP}',
    'also_at': [],
    'scope': 'every hall on every campus (each advisor stands in a named '
             'room or on the green)',
    'advisors': list(advisors['advisors']),
    'door': door('campus', FLAGSHIP),
    'door_scope': PAGE_WIDE,
    'provenance': 'AUTHORED',
})
services.append({
    'id': 'schools-panel',
    'kind': 'panel',
    'name': f'Schools panel - {schools["model"]["name"]}, '
            f'{len(schools["units"])} flipped units',
    'registry': 'schools/registry/schools.json',
    'transport': TRANSPORT,
    'anchored_at': f'campus:{FLAGSHIP}',
    'also_at': [],
    'scope': 'page-wide',
    'door': door('campus', FLAGSHIP),
    'door_scope': PAGE_WIDE,
    'provenance': 'AUTHORED',
})
for dk, crib in tools['cribs'].items():
    services.append({
        'id': f'crib:{dk}',
        'kind': 'toolroom-crib',
        'name': crib['name'],
        'registry': 'tools/registry/toolcribs.json',
        'transport': TRANSPORT,
        'anchored_at': f'campus:{district_home[dk]}',
        'also_at': [],
        'tools': len(crib['tools']),
        'door': door('campus', district_home[dk]),
        'door_scope': 'the crib opens from the toolroom of its district\'s '
                      'halls; the door lands on the campus that homes them',
        'provenance': 'SCHEMATIC',
    })
services.append({
    'id': 'restoration-panel',
    'kind': 'panel',
    'name': f'Bay Restoration panel - {len(resto["sites"])} sites, '
            f'{len(resto["tracks"])} field-skill tracks',
    'registry': 'restoration/registry/restoration.json',
    'transport': TRANSPORT,
    'anchored_at': f'campus:{FLAGSHIP}',
    'also_at': [],
    'door': door('campus', FLAGSHIP),
    'door_scope': PAGE_WIDE,
    'site_panels': [
        {'site': s['id'],
         'anchored_at': f'restoration-site:{s["id"]}' if s['pin'] else None,
         'walkable': s['walkable'],
         'door': None,
         'why_no_door': 'no page in this bundle reads a site parameter from '
                        'its URL' + (f' (the 3D page reads: '
                                     f'{", ".join(PARAMS_READ)})'
                                     if PARAMS_READ is not None else '')}
        for s in resto['sites']],
    'provenance': 'AUTHORED',
})
services.append({
    'id': 'training-recorder',
    'kind': 'recorder',
    'name': f'training-data recorder - {len(training["episode_kinds"])} '
            f'episode kinds, device-local under {training["storage"]["key"]}',
    'registry': 'training/registry/training.json',
    'transport': TRANSPORT,
    'anchored_at': f'campus:{FLAGSHIP}',
    'also_at': [],
    'scope': 'page-wide; device-local storage only',
    'door': door('campus', FLAGSHIP),
    'door_scope': PAGE_WIDE,
    'provenance': 'SCHEMATIC',
})
for s in services:
    assert 'door' in s, f'service {s["id"]} has no door'
    assert isinstance(need(s, 'also_at', s['id']), list)

# --------------------------------------------------------- the export door ---
# Where a mesh could be fetched from, and by whom: the .glb button in the
# page bar, in the locker and in any hall view. Its transport is the page's
# own exportGlb, said honestly above; the content it emits is the SCHEMATIC
# avatar or hall already listed under anchored_content, and this node is
# the SCRIPTED behaviour that produces it.
export_door = {
    'id': 'export:gltf',
    'kind': 'export',
    'name': 'glTF 2.0 binary export door - three.js GLTFExporter in the '
            'running page',
    'format': 'glTF 2.0 binary',
    'exports': [{'id': e['id'], 'from': e['from'], 'file': e['file']}
                for e in meta['exports']],
    'transport': EXPORT_TRANSPORT,
    'anchored_at': None,
    'why_unanchored': 'a door in the page bar, opened from the locker and '
                      'from any hall view; it stands nowhere on the map',
    'door': door(None, None),
    'door_scope': 'the entry page: the .glb button shows in the locker and '
                  'in every hall view (any ?hall= door), never from a URL '
                  'parameter of its own',
    'served_by_this_fabric': True,
    'provenance': 'SCRIPTED',
}

# ---------------------------------------------------------- external origins ---
external = {}
for p in poses:
    sub = p['subject']
    if sub['kind'] == 'anchor':
        key = sub['name']
        if key not in external:
            external[key] = {
                'operator': key,
                'kind': p['anchor']['kind'],
                'origin': 'external',
                'served_by_this_fabric': False,
                'note': ('named as a neighbouring place, not as an organization'
                         if p['anchor']['kind'] == 'city' else
                         'a real institution this fabric points at and does '
                         'not speak for'),
                'geoposes': [], 'unposed': [], 'provenance': set()}
        ext = external[key]
        ext['geoposes'].append(sub['ref'])
        ext['provenance'].add(p['provenance']['position_horizontal'])
for s in resto['sites']:
    key = s['org']
    if key not in external:
        external[key] = {
            'operator': key,
            'kind': 'restoration-organization'
                    if s['category'] == 'habitat-restoration'
                    else 'cleanup-and-oversight-agencies',
            'origin': 'external',
            'served_by_this_fabric': False,
            'note': resto['honesty']['not_affiliated'],
            'geoposes': [], 'unposed': [], 'provenance': set()}
    ext = external[key]
    if s['pin']:
        ext['geoposes'].append(f'restoration-site:{s["id"]}')
        ext['provenance'].add('AUTHORED')
    else:
        ext['unposed'].append(f'restoration-site:{s["id"]}')
external_origins = []
for e in external.values():
    e['provenance'] = sorted(e['provenance'])
    assert isinstance(e['operator'], str) and e['operator'].strip(), \
        'an external origin has no named operator'
    assert e['served_by_this_fabric'] is False, e['operator']
    external_origins.append(e)

# --------------------------------------------------------------------- SOM ---
# Every door this fabric declares, held against the built page. A door that
# opens onto nothing fails the build BY NAME here: the page's own rosters
# are the measurement, and a node whose door is not in them is a node this
# fabric only pretends to serve. Each door record then carries `resolves`
# (True, or None when the page was not measured, --bootstrap).
DOORED = ([('place', pl['id'], pl['door']) for pl in places]
          + [('content', c['scene'], c['door']) for c in anchored_content]
          + [('service', s['id'], s['door']) for s in services]
          + [('export', export_door['id'], export_door['door'])])
for _kind, _id, _d in DOORED:
    _d['resolves'] = door_resolves(_d)
_dead = [f'{k} {i} -> {d["href"]}' for k, i, d in DOORED if d['resolves'] is False]
if _dead:
    raise SystemExit(f'spatial: {len(_dead)} door(s) open onto nothing in '
                     f'{ENTRY} (its rosters: '
                     + ', '.join(f'{p}={len(ROSTERS[p])}' for p in DOOR_PARAMS)
                     + '): ' + '; '.join(_dead))
NAMED_ONLY = ('an external origin: this fabric names it and locates it by its '
              'own pose, and serves nothing for it, so there is no door - a '
              'browser would compose that operator\'s own fabric here, if one '
              'existed')


def node(kind, name, ref, prov, door_rec, **more):
    return {'kind': kind, 'name': name, 'geopose': ref, 'provenance': prov,
            'served_by_this_fabric': True, 'door': door_rec, **more}


fabric_children = [
    node('place', pl['name'], pl['geopose'],
         REF[pl['geopose']]['provenance']['position_horizontal'], pl['door'],
         place=pl['id'], walk=pl['walk'])
    for pl in places
] + [
    node('content', c['scene'], c['anchored_at'], c['provenance'], c['door'],
         export=c['export'], produced_on_demand=True)
    for c in anchored_content
] + [
    node('service', s['id'], s['anchored_at'], s['provenance'], s['door'],
         transport=s['transport'])
    for s in services
] + [
    node('export', export_door['id'], export_door['anchored_at'],
         export_door['provenance'], export_door['door'],
         transport=export_door['transport'],
         exports=[e['id'] for e in export_door['exports']])
]
FABRIC_KINDS = ('place', 'content', 'service', 'export')
assert {n['kind'] for n in fabric_children} == set(FABRIC_KINDS)
branches = [{
    'id': 'branch:this-fabric',
    'origin': 'this fabric',
    'owner': PRODUCT,
    'served_by_this_fabric': True,
    'provenance_tiers': sorted({n['provenance'] for n in fabric_children}),
    'children': fabric_children,
}]
for e in external_origins:
    kids = []
    for ref in e['geoposes']:
        p = REF[ref]
        k = node(p['subject']['kind'], p['subject']['name'], ref,
                 p['provenance']['position_horizontal'], None,
                 named_only=True, why_no_door=NAMED_ONLY)
        k['served_by_this_fabric'] = False
        if 'site' in p:
            k['walkable'] = p['site']['walkable']
            k['category'] = p['site']['category']
        kids.append(k)
    for ref in e['unposed']:
        kids.append({'kind': 'restoration-site', 'name': next(
            u['subject']['name'] for u in unposed if u['subject']['ref'] == ref),
            'geopose': None, 'provenance': 'AUTHORED',
            'served_by_this_fabric': False, 'door': None,
            'named_only': True, 'why_no_door': NAMED_ONLY,
            'why_no_geopose': next(u['why'] for u in unposed
                                   if u['subject']['ref'] == ref)})
    branches.append({
        'id': f'branch:external/{slug(e["operator"])[:60]}',
        'origin': 'external',
        'owner': e['operator'],
        'served_by_this_fabric': False,
        'provenance_tiers': sorted(e['provenance']) or ['AUTHORED'],
        'children': kids,
    })

# the per-branch ownership invariant: no external branch carries anything
# this fabric claims to serve, and nothing this fabric serves sits under an
# owner that is not this fabric
for b in branches:
    if b['origin'] == 'external':
        assert not b['served_by_this_fabric']
        for k in b['children']:
            assert not k['served_by_this_fabric'], (b['id'], k['name'])
            assert k['kind'] not in FABRIC_KINDS, (b['id'], k['name'])
            assert k['door'] is None and k['named_only'] is True, k['name']
    else:
        assert b['owner'] == PRODUCT
        for k in b['children']:
            assert k['served_by_this_fabric'], (b['id'], k['name'])
            assert k['door'] is not None and k['door']['resolves'] is not False
assert len({b['id'] for b in branches}) == len(branches), 'branch id collides'

# ------------------------------------------------------------- the counts ---
# What these count: LEAVES of the scene graph - the children of the root
# branches (a place, a .glb, a service, the export door, or an external
# origin's named site or city). A ROOT branch is an owner, not a thing a
# door opens onto, and its count lives under invariants.counts.branches.
# The names say "branches" because that is what the deck calls a leaf a
# browser would resolve; the `unit` field says what was counted so that a
# reader never mistakes 14 owners for 154 leaves.
_leaves = [k for b in branches for k in b['children']]
_with_door = [k for k in _leaves if k['door'] is not None]
_resolving = [k for k in _with_door if k['door']['resolves'] is True]
_named_only = [k for k in _leaves if k['door'] is None]
assert len(_with_door) + len(_named_only) == len(_leaves)
assert len(_with_door) == len(fabric_children)
assert all(k['named_only'] is True for k in _named_only)
assert len(_named_only) == sum(len(b['children']) for b in branches[1:])
_by_param = {}
for k in _with_door:
    _p = k['door']['param'] if k['door']['param'] is not None else 'entry-page'
    _by_param[_p] = _by_param[_p] + 1 if _p in _by_param else 1
doors_block = {
    'unit': 'leaves of som:root - the children of every branch, never the '
            'branches themselves (those are owners; see invariants.counts)',
    'page': ENTRY,
    'measured_against': ('the <script id="data"> payload of the built page: '
                         'D.halls[].slug for ?hall=, Object.keys(D.sims.sims) '
                         'for ?sim=, Object.keys(D.campuses) for ?campus=; the '
                         'page itself for a door with no parameter')
                        if ROSTERS is not None else None,
    'roster_sizes': ({p: len(ROSTERS[p]) for p in DOOR_PARAMS}
                     if ROSTERS is not None else None),
    'leaves': len(_leaves),
    'branches_with_a_door': len(_with_door),
    'branches_whose_door_resolves': len(_resolving),
    'branches_that_can_only_be_named': len(_named_only),
    'doors_by_parameter': _by_param,
    'rule': 'a door to nothing fails the build by name (spatial/build.py) and '
            'the suite by href (spatial/test.mjs); every leaf this fabric '
            'serves has a door, and every leaf it only names has none',
}
if ROSTERS is not None:
    assert doors_block['branches_with_a_door'] == doors_block['branches_whose_door_resolves']

# ---------------------------------------------------------------- ownership ---
# No leaf under this fabric's branch points at another operator's content:
# the poses it stands on are the campuses' own, the poses external leaves
# stand on are the anchors' and sites', and the two sets do not meet. The
# restoration panel's per-site sub-panels are this fabric's own AUTHORED
# panels ABOUT a site, anchored at that site's pose; they are counted here
# so nobody has to wonder whether that is a fabric leaf on an external pose
# (it is not: the SOM leaf for the panel stands at the flagship campus).
_mine_refs = {k['geopose'] for k in fabric_children if k['geopose'] is not None}
_ext_refs = {k['geopose'] for b in branches[1:] for k in b['children']
             if k['geopose'] is not None}
_mine_kinds = sorted({REF[r]['subject']['kind'] for r in _mine_refs})
_ext_kinds = sorted({REF[r]['subject']['kind'] for r in _ext_refs})
assert _mine_kinds == ['campus'], _mine_kinds
assert set(_ext_kinds) <= {'anchor', 'restoration-site'}, _ext_kinds
assert not (_mine_refs & _ext_refs), sorted(_mine_refs & _ext_refs)
_rp = next(s for s in services if s['id'] == 'restoration-panel')
ownership_block = {
    'rule': 'one owner per branch: every leaf this fabric serves stands on a '
            'pose of its own (a campus), every external leaf stands on the '
            'pose of the operator it names (an anchor or a restoration site), '
            'and no pose is shared between the two',
    'this_fabric_pose_kinds': _mine_kinds,
    'external_pose_kinds': _ext_kinds,
    'poses_shared_between_this_fabric_and_an_external_branch': len(_mine_refs & _ext_refs),
    'external_origins': len(external_origins),
    'external_origins_served_by_this_fabric': sum(
        1 for e in external_origins if e['served_by_this_fabric']),
    'external_origins_without_a_named_operator': sum(
        1 for e in external_origins
        if not (isinstance(e['operator'], str) and e['operator'].strip())),
    'fabric_leaves_on_an_external_pose': len(_mine_refs & _ext_refs),
    'site_panels_anchored_at_external_poses': sum(
        1 for sp in _rp['site_panels'] if sp['anchored_at'] is not None),
    'site_panels_note': 'these are fabric.json#services[restoration-panel]'
                        '.site_panels: this fabric\'s own AUTHORED panels about '
                        'a site, each anchored at the site\'s pose; they are '
                        'not SOM leaves and serve nothing for the operator',
}
assert ownership_block['external_origins_served_by_this_fabric'] == 0
assert ownership_block['external_origins_without_a_named_operator'] == 0

# ----------------------------------------------------------------- coverage ---
# What the poses carry, counted from the poses as emitted, not typed: a pose
# "has" a height or a heading only when its sidecar says something other
# than the UNKNOWN placeholder. Today none does, and the block says why in
# structure: terrain/ is a water mask (Natural Earth outlines, 125 m cells,
# no elevation) and the only elevation in the bundle is USGS 3DEP fetched in
# the learner's browser on request - never stored, so never a pose's h.
TERRAIN_FILE = 'terrain/registry/terrain.json'
PARCELS_FILE = 'parcels/registry/parcels.json'
_th = need(terrain, 'honesty', TERRAIN_FILE)
_tc = need(terrain, 'counts', TERRAIN_FILE)
_el = need(parcels, 'elevation', PARCELS_FILE)
coverage_block = {
    'poses': len(poses),
    'poses_with_horizontal_position': sum(
        1 for p in poses if p['provenance']['position_horizontal']
        in ('RECORDED', 'DERIVED', 'AUTHORED')),
    'poses_with_height': sum(
        1 for p in poses if p['provenance']['h_provenance'] != H_PROV),
    'poses_with_heading': sum(
        1 for p in poses if p['provenance']['orientation_provenance'] != O_PROV),
    'how': 'counted from the poses in this file: a pose has a height when its '
           'h_provenance is not the UNKNOWN placeholder, a heading when its '
           'orientation_provenance is not; a zero in the encoding is never '
           'read as a value',
    'why': {
        'terrain': {
            'registry': TERRAIN_FILE,
            'holds': 'a land/water mask and shoreline outlines, in local '
                     'metres - no elevation',
            'source': need(terrain, 'source', TERRAIN_FILE),
            'cell_m': need(_tc, 'cell_m', f'{TERRAIN_FILE}#counts'),
            'no_elevation': need(_th, 'no_elevation', f'{TERRAIN_FILE}#honesty'),
        },
        'usgs': {
            'registry': f'{PARCELS_FILE}#elevation',
            'id': need(_el, 'id', f'{PARCELS_FILE}#elevation'),
            'name': need(_el, 'name', f'{PARCELS_FILE}#elevation'),
            'runs_in': 'the learner\'s own browser, on request, one coordinate '
                       'per opened card',
            'scope': need(_el, 'scope', f'{PARCELS_FILE}#elevation'),
            'verified_from_build': need(_el, 'verified_from_build',
                                        f'{PARCELS_FILE}#elevation'),
            'stored_by_this_bundle': False,
        },
        'so': 'no registry in this bundle holds a height or a heading for any '
              'subject, and this build invents none: h and yaw/pitch/roll stay '
              '0 with the UNKNOWN sidecar until a registry that owns a '
              'measurement exists',
    },
    'provenance': 'DERIVED - recounted from the emitted poses on every build',
}
assert coverage_block['poses_with_horizontal_position'] == len(poses)
assert _el['verified_from_build'] is False
assert 'elevation' in _th['no_elevation'].lower() or 'height' in _th['no_elevation'].lower()

flagship_block = {
    'campus': FLAGSHIP,
    'decided_by': f'unions/registry/campuses.json#campuses.{FLAGSHIP}.flagship',
    'claimants': len(_flagships),
    'anchors_services': sorted(s['id'] for s in services
                               if s['door_scope'] == PAGE_WIDE),
    'why': 'a DESIGN decision the campus registry owns, not a fact about '
           'where anything physically is; the page-wide services stand here '
           'because they open from the bar on every campus',
}
assert len(flagship_block['anchors_services']) > 0

# every reference resolves, every service id resolves to its own registry
for c in anchored_content:
    assert c['anchored_at'] is None or c['anchored_at'] in REF, c
for s in services:
    assert s['anchored_at'] in REF, s['id']
    for r in s['also_at']:
        assert r in REF
    assert (ROOT / s['registry']).exists(), s['registry']
    kind, _, ident = s['id'].partition(':')
    if kind == 'sim':
        assert ident in sims['sims']
    elif kind == 'crib':
        assert ident in tools['cribs']
for sp in _rp['site_panels']:
    assert sp['anchored_at'] is None or sp['anchored_at'] in REF
for n in fabric_children:
    assert n['geopose'] is None or n['geopose'] in REF
for b in branches[1:]:
    for k in b['children']:
        assert k['geopose'] is None or k['geopose'] in REF
assert not any(e['served_by_this_fabric'] for e in external_origins)
assert not any(e['operator'] in {u['name'] for u in unions}
               for e in external_origins), 'a union hall crept in as an origin'

# the network dashboard renders this pack - the same drift guard every
# other platform-wide registry keeps
BOOTSTRAP = '--bootstrap' in sys.argv
if not BOOTSTRAP:
    dash = (ROOT / 'web/trade_craft_dashboard.html').read_text()
    assert f'<b>{len(poses)}</b><span>GeoPose 1.0' in dash, \
        'the dashboard does not render the pose count on its GeoPose tile'
    assert HONESTY['ombi_not_claimed'] in dash, \
        'the dashboard does not carry the OMBI-not-claimed honesty line'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
head = {
    'pack': 'smartcitix-trade-craft-academy-spatial-fabric',
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
}

geopose_doc = {
    **head,
    'encoding': ENCODING,
    'media_type': MEDIA_TYPE,
    'crs': geo['crs'],
    'counts': {'campuses': n_campuses, 'anchors': n_anchors,
               'restoration_sites': n_sites, 'total': len(poses),
               'unposed': len(unposed)},
    'coverage': coverage_block,
    'honesty': HONESTY,
    'poses': poses,
    'unposed': unposed,
}

fabric_doc = {
    **head,
    'fabric': {
        'name': 'SmartCiti.X : Trade Craft Academy - spatial fabric',
        'operator': PRODUCT,
        'origin': 'self-hosted static files',
        'entry': 'web/trade_craft_3d.html',
        'shape': SHAPE,
        'identity': {'did': None, 'note': 'no DID is minted by this bundle'},
        'poses': 'spatial/registry/geopose.json',
        'scene_graph': 'spatial/registry/som.json',
        'content_formats': ['glTF 2.0 binary'],
        'transport': 'none - no RMAP endpoint, no server, no network; a '
                     'plain web server serving these files next to the '
                     'site is the whole deployment',
        'flagship': flagship_block,
        'doors': 'spatial/registry/som.json#doors',
    },
    'places': places,
    'anchored_content': anchored_content,
    'services': services,
    'export_door': export_door,
    'external_origins': external_origins,
    'honesty': HONESTY,
    'sources': SOURCES,
}

som_doc = {
    **head,
    'shape': SHAPE,
    'root': {
        'id': 'som:root',
        'composition': 'a metaverse browser would compose these branches '
                       'into one scene; this build composes nothing and '
                       'only declares who owns what',
        'branches': branches,
    },
    'invariants': {
        'per_branch_ownership': 'every branch has exactly one owner; no '
                                'external branch contains a place, content '
                                'or service this fabric serves, and every '
                                'node this fabric serves sits under its own '
                                'branch - asserted by spatial/build.py and '
                                'spatial/test.mjs',
        'counts': {'branches': len(branches),
                   'external_branches': len(branches) - 1,
                   'fabric_nodes': len(fabric_children)},
    },
    'doors': doors_block,
    'ownership': ownership_block,
    'honesty': HONESTY,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
for name, doc in (('geopose.json', geopose_doc), ('fabric.json', fabric_doc),
                  ('som.json', som_doc)):
    (OUT / name).write_text(json.dumps(doc, indent=1) + '\n')
print(f"spatial fabric: {len(poses)} GeoPoses ({n_campuses} campuses, "
      f"{n_anchors} anchors, {n_sites} sites; {len(unposed)} unposed), "
      f"{len(places)} places, {len(anchored_content)} anchored .glb doors, "
      f"{len(services)} services, {len(external_origins)} external origins, "
      f"{len(branches)} SOM branches / {len(_leaves)} leaves "
      f"({len(_with_door)} doored, {len(_resolving)} resolving, "
      f"{len(_named_only)} named only), heights {coverage_block['poses_with_height']}"
      f"/{len(poses)}, headings {coverage_block['poses_with_heading']}/{len(poses)} "
      f"(source stamp {stamp})")
