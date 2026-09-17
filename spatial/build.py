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

PACK_VERSION = "1.0.0"
BUILT = "2026-09-16"

PRODUCT = 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)'

# ------------------------------------------------------------------ inputs ---
geo = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))
resto = json.load(open(ROOT / 'restoration/registry/restoration.json'))
meta = json.load(open(ROOT / 'meta/registry/metaverse.json'))
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
unions = json.load(open(ROOT / 'unions/registry/unions.json'))['unions']
sims = json.load(open(ROOT / 'sims/registry/sims.json'))
advisors = json.load(open(ROOT / 'agents/registry/advisors.json'))
schools = json.load(open(ROOT / 'schools/registry/schools.json'))
world = json.load(open(ROOT / 'world/registry/world.json'))
tools = json.load(open(ROOT / 'tools/registry/toolcribs.json'))
training = json.load(open(ROOT / 'training/registry/training.json'))
roadmap = json.load(open(ROOT / 'roadmap/registry/roadmap.json'))

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

# the flagship campus every page-wide service is anchored at - the same
# reference point roadmap/build.py and the 3D region board already use
FLAGSHIP = 'treasure-island'
assert FLAGSHIP in campuses_reg and FLAGSHIP in geo['campuses']

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
                                 'disk.',
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
                 'walkable_reason': s.get('walkable_reason')}
    poses.append(p)
n_sites = len(poses) - n_campuses - n_anchors

REF = {p['subject']['ref']: p for p in poses}
assert len(REF) == len(poses), 'a pose ref collides'
assert n_campuses == len(campuses_reg) == 10
assert n_anchors == sum(len(v) for v in geo['anchors'].values()) == 47
assert n_sites == sum(1 for s in resto['sites'] if s['pin']) == 10
assert len(unposed) == 1

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
    })

exports = {e['id']: e for e in meta['exports']}
assert set(exports) == {'avatar-glb', 'hall-glb'}
GLB_NOTE = ('exported by the learner\'s own browser from the running page '
            '(the .glb button), not a file sitting on disk')
anchored_content = [{
    'export': 'avatar-glb',
    'scene': 'tc-avatar',
    'file': exports['avatar-glb']['file'],
    'format': 'glTF 2.0 binary',
    'produced_on_demand': True,
    'how': GLB_NOTE,
    'anchored_at': None,
    'why_unanchored': 'the avatar is the learner\'s own and travels with '
                      'them; it stands nowhere on the map',
    'provenance': 'SCHEMATIC',
}]
for u in unions:
    anchored_content.append({
        'export': 'hall-glb',
        'scene': f'tc-hall-{u["slug"]}',
        'file': f'tc-hall-{u["slug"]}.glb',
        'format': 'glTF 2.0 binary',
        'produced_on_demand': True,
        'how': GLB_NOTE,
        'anchored_at': f'campus:{hall_home[u["slug"]]}',
        'hall': u['slug'],
        'name': u['name'],
        'provenance': 'SCHEMATIC',
    })
assert len(anchored_content) == 1 + len(unions) == 112

TRANSPORT = 'in-page, no network'
services = []
campus_order = list(campuses_reg)
for sk, s in sims['sims'].items():
    hosting = sorted({hall_home[h] for h in s['halls']},
                     key=campus_order.index)
    assert hosting, f'sim {sk} binds no homed hall'
    assert s.get('operator'), f'sim {sk} declares no scripted operator'
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
        'provenance': 'SCHEMATIC',
    })
services.append({
    'id': 'advisors',
    'kind': 'scripted-advisors',
    'name': f'{advisors["counts"]["advisors"]} scripted advisors, '
            f'{advisors["counts"]["topics"]} fixed topics',
    'registry': 'agents/registry/advisors.json',
    'transport': TRANSPORT,
    'anchored_at': f'campus:{FLAGSHIP}',
    'scope': 'every hall on every campus (each advisor stands in a named '
             'room or on the green)',
    'advisors': list(advisors['advisors']),
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
    'scope': 'page-wide',
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
        'tools': len(crib['tools']),
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
    'site_panels': [
        {'site': s['id'],
         'anchored_at': f'restoration-site:{s["id"]}' if s['pin'] else None,
         'walkable': s['walkable']}
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
    'scope': 'page-wide; device-local storage only',
    'provenance': 'SCHEMATIC',
})

# ---------------------------------------------------------- external origins ---
external = {}
for p in poses:
    sub = p['subject']
    if sub['kind'] == 'anchor':
        key = sub['name']
        ext = external.setdefault(key, {
            'operator': key,
            'kind': p['anchor']['kind'],
            'origin': 'external',
            'served_by_this_fabric': False,
            'note': ('named as a neighbouring place, not as an organization'
                     if p['anchor']['kind'] == 'city' else
                     'a real institution this fabric points at and does not '
                     'speak for'),
            'geoposes': [], 'provenance': set()})
        ext['geoposes'].append(sub['ref'])
        ext['provenance'].add(p['provenance']['position_horizontal'])
for s in resto['sites']:
    key = s['org']
    ext = external.setdefault(key, {
        'operator': key,
        'kind': 'restoration-organization'
                if s['category'] == 'habitat-restoration'
                else 'cleanup-and-oversight-agencies',
        'origin': 'external',
        'served_by_this_fabric': False,
        'note': resto['honesty']['not_affiliated'],
        'geoposes': [], 'provenance': set()})
    if s['pin']:
        ext['geoposes'].append(f'restoration-site:{s["id"]}')
        ext['provenance'].add('AUTHORED')
    else:
        ext.setdefault('unposed', []).append(f'restoration-site:{s["id"]}')
external_origins = []
for e in external.values():
    e['provenance'] = sorted(e['provenance'])
    external_origins.append(e)

# --------------------------------------------------------------------- SOM ---
def node(kind, name, ref, prov, **more):
    return {'kind': kind, 'name': name, 'geopose': ref, 'provenance': prov,
            'served_by_this_fabric': True, **more}


fabric_children = [
    node('place', pl['name'], pl['geopose'],
         REF[pl['geopose']]['provenance']['position_horizontal'],
         place=pl['id'], walk=pl['walk'])
    for pl in places
] + [
    node('content', c['scene'], c['anchored_at'], c['provenance'],
         export=c['export'], produced_on_demand=True)
    for c in anchored_content
] + [
    node('service', s['id'], s['anchored_at'], s['provenance'],
         transport=s['transport'])
    for s in services
]
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
                 p['provenance']['position_horizontal'])
        k['served_by_this_fabric'] = False
        if 'site' in p:
            k['walkable'] = p['site']['walkable']
            k['category'] = p['site']['category']
        kids.append(k)
    for ref in e.get('unposed', []):
        kids.append({'kind': 'restoration-site', 'name': next(
            u['subject']['name'] for u in unposed if u['subject']['ref'] == ref),
            'geopose': None, 'provenance': 'AUTHORED',
            'served_by_this_fabric': False,
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
            assert k['kind'] not in ('service', 'content', 'place'), \
                (b['id'], k['name'])
    else:
        assert b['owner'] == PRODUCT
        for k in b['children']:
            assert k['served_by_this_fabric'], (b['id'], k['name'])
assert len({b['id'] for b in branches}) == len(branches), 'branch id collides'

# every reference resolves, every service id resolves to its own registry
for c in anchored_content:
    assert c['anchored_at'] is None or c['anchored_at'] in REF, c
for s in services:
    assert s['anchored_at'] in REF, s['id']
    for r in s.get('also_at', []):
        assert r in REF
    for sp in s.get('site_panels', []):
        assert sp['anchored_at'] is None or sp['anchored_at'] in REF
    assert (ROOT / s['registry']).exists(), s['registry']
    kind, _, ident = s['id'].partition(':')
    if kind == 'sim':
        assert ident in sims['sims']
    elif kind == 'crib':
        assert ident in tools['cribs']
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
    },
    'places': places,
    'anchored_content': anchored_content,
    'services': services,
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
      f"{len(branches)} SOM branches (source stamp {stamp})")
