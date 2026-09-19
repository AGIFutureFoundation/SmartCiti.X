#!/usr/bin/env python3
"""The 3D environment: every hall's floor plan, standing up.

Renders web/trade_craft_3d.html — a Three.js scene generated from the same
registries as every other surface:

  - the hall's rooms extruded from the interiors geometry (12 grid units
    wide, 3 m per unit) as a dollhouse: floor slab, low partitions, a
    district-hued fascia carrying the hall name;
  - the recovered training stations standing as beacons inside the rooms
    their strands own — click one for its lesson, checklist and gradable
    scenario check;
  - the recovered yard prop layout dressed along the apron in front of the
    building (schematic primitives; the geometry is a functional programme,
    not a building survey, and the page says so);
  - hall selector across all 111 halls grouped by district, deep-linkable
    (?hall=slug&lang=xx), UI in every shipped locale.

Three.js is pinned at 0.160.0 — the same major the recovered yard app used —
vendored into web/vendor/ and loaded as ES modules via import map, so the
page works offline and on any static host with no CDN dependency. Serve the
tree over HTTP (python3 -m http.server) — browsers refuse module imports
from file:// URLs. The page holds no data of its own.
"""
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'unions').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()
sys.path.insert(0, str(ROOT / 'web'))
from interiors import build as build_interiors  # noqa: E402
from staleness import emit  # noqa: E402
from mapdata import strand_modules, PIPELINE_JS, HUES, make_codes  # noqa: E402
from groundtruth import GROUND_TRUTH_JS  # noqa: E402

manifest = json.load(open(ROOT / 'pack/manifest.json'))
L = manifest['ledger']
halls_json = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
districts_reg = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
finishes_reg = json.load(open(ROOT / 'surfaces/registry/finishes.json'))
geo_reg = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))
avatars_reg = json.load(open(ROOT / 'avatars/registry/avatars.json'))
chapters_reg = json.load(open(ROOT / 'unions/registry/chapters.json'))
sims_reg = json.load(open(ROOT / 'sims/registry/sims.json'))
parcels_reg = json.load(open(ROOT / 'parcels/registry/parcels.json'))
tools_reg = json.load(open(ROOT / 'tools/registry/toolcribs.json'))
stations_reg = json.load(open(ROOT / 'stations/registry/stations.json'))
agents_reg = json.load(open(ROOT / 'agents/registry/advisors.json'))
training_reg = json.load(open(ROOT / 'training/registry/training.json'))
orbis_reg = json.load(open(ROOT / 'orbis/registry/orbis.json'))
schools_reg = json.load(open(ROOT / 'schools/registry/schools.json'))
world_reg = json.load(open(ROOT / 'world/registry/world.json'))
labels_reg = json.load(open(ROOT / 'labels/registry/labels.json'))
roadmap_reg = json.load(open(ROOT / 'roadmap/registry/roadmap.json'))
restoration_reg = json.load(open(ROOT / 'restoration/registry/restoration.json'))

def trim(rows, *drop):
    """Ship what is drawn, not what is explained.

    Every registry carries the prose that makes its records checkable by a
    person - what a surface is for, why an animal is in the yard, what a
    sign reads as. None of that is rendered by the page, and a byte
    shipped to every learner should be one they can see, so it is dropped
    on the way in. The registry keeps the whole truth; the wiki prints it.
    """
    if not isinstance(rows, dict):
        return rows
    if rows and all(isinstance(v, dict) for v in rows.values()):
        return {k: {kk: vv for kk, vv in v.items() if kk not in drop}
                for k, v in rows.items()}
    return {k: v for k, v in rows.items() if k not in drop}


yard = json.load(open(ROOT / 'archive/bac_yard_stations.json'))['yard_placements']



def hall_level_states(slug):
    doc = json.load(open(ROOT / f'pack/registry/halls/{slug}.json'))
    c = {'live': 0, 'calibrating': 0, 'schema_ok': 0, 'draft': 0}
    for lv in doc['levels']:
        c[lv['state']] += 1
    return c


census = {h['slug']: hall_level_states(h['slug']) for h in halls_json}
per_level = L['slots_per_level'] * L['variants_per_lesson']
plans = build_interiors(halls_json, lambda i: {
    k: v * per_level for k, v in census[halls_json[i]['slug']].items()})

district_of = {slug: k for k, d in districts_reg.items() for slug in d['halls']}

stations_by_hall = {}
for s in stations_reg['stations']:
    stations_by_hall.setdefault(s['hall'], []).append(s['station_id'])

# Payload dedupe, measured before it was written: labels and purposes are
# one per strand (ROOM_DEFS), room geometry depends only on the envelope
# depth (LAYOUTS), so each hall ships depth + its own fixtures and the
# page inflates rooms at boot. Asserted here, so a plan change that
# breaks the invariant fails the build instead of the page.
ROOM_DEFS, LAY_LIST, LAY_IDX = {}, [], {}
for h in halls_json:
    lay = [{'strand': r['strand'], 'x': r['x'], 'y': r['y'],
            'w': r['w'], 'h': r['h']} for r in plans[h['slug']]['rooms']]
    key = json.dumps(lay, sort_keys=True)
    for i, (k2, _) in enumerate(LAY_LIST):
        if k2 == key:
            LAY_IDX[h['slug']] = i
            break
    else:
        LAY_IDX[h['slug']] = len(LAY_LIST)
        LAY_LIST.append((key, lay))
    for r in plans[h['slug']]['rooms']:
        rd = {'label': r['label'], 'purpose': r['purpose']}
        assert ROOM_DEFS.setdefault(r['strand'], rd) == rd, \
            f"room def diverges for strand {r['strand']}"

HALLS = [{
    'slug': h['slug'], 'name': h['name'], 'focus': h['focus'],
    'index': h['index'], 'district': district_of[h['slug']],
    'fixtures': {r['strand']: r['fixtures']
                 for r in plans[h['slug']]['rooms'] if r['fixtures']},
    'lay': LAY_IDX[h['slug']],
    'depth': plans[h['slug']]['envelope']['d'],
    'stations': stations_by_hall.get(h['slug'], []),
} for h in halls_json]

# finishes collapse the same way: 12 distinct maps across 111 halls
FIN_MAPS, FIN_IDX = [], {}
for sl, h in finishes_reg['halls'].items():
    key = json.dumps(h['rooms'], sort_keys=True)
    for i, (k2, m2) in enumerate(FIN_MAPS):
        if k2 == key:
            FIN_IDX[sl] = i
            break
    else:
        FIN_IDX[sl] = len(FIN_MAPS)
        FIN_MAPS.append((key, h['rooms']))

# and the walls collapse on exactly the same principle - one copy of each
# distinct wall map, an index per hall. The two indexes are NOT the same
# index: a wall resolves against every hazard the trade carries and a floor
# against the finish-driving one, so two halls can share a floor map and
# differ in their walls. Deduping them together would quietly make one of
# those two facts a copy of the other.
WALL_MAPS, WALL_IDX = [], {}
for sl, h in finishes_reg['halls'].items():
    key = json.dumps(h['walls'], sort_keys=True)
    for i, (k2, m2) in enumerate(WALL_MAPS):
        if k2 == key:
            WALL_IDX[sl] = i
            break
    else:
        WALL_IDX[sl] = len(WALL_MAPS)
        WALL_MAPS.append((key, h['walls']))

I18N = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.load(open(f))
    s = c['strings']
    I18N[c['locale']] = {
        'language': c['language'], 'dir': c['dir'],
        'strings': {k: s[k] for k in (
            'nav.campus', 'language.select', 'hall.rooms', 'hall.stations',
            'station.checklist', 'station.quiz', 'ui.close',
            'map.layer.modules', 'figures.modules', 'figures.lessons', 'room.finish',
            'figures.halls', 'figures.districts', 'figures.campuses',
            'view.campus', 'view.region', 'ui.walk',
            'hint.campus', 'hint.walk', 'hint.walkRefused', 'geo.note',
            'yard.name', 'yard.seats',
            'sim.start', 'sim.results', 'sim.pass', 'sim.retry',
            'sim.sound', 'sim.view', 'sim.choose', 'progress.local',
            'city.note', 'avatar.title', 'chapters.hall',
            'honesty.taxonomy', 'honesty.content')},
        'districts': {k: v['name'] for k, v in c['districts'].items()},
        'strands': c['strands'], 'tiers': c['tiers'], 'states': c['states'],
    }

# --------------------------------------------------------------- footfall ---
# What a footstep sounds like. A closed set of STEP FAMILIES, and the two
# things a walker can be standing on - a room's floor pattern and a world
# ground recipe - each declaring which family it steps like. One truth: the
# timbre lives once, per family; nothing here restates a finish or a recipe.
#
# SCHEMATIC, like the rest of the audio in this page: synthesised in the
# browser from filtered noise, never a recording of a real floor.
STEP_FAMILIES = {
    'hard':  {'f': 620,  'q': 1.3, 'dur': .085, 'ring': 0,   'grit': .30,
              'why': 'a hard flat floor gives a short slap and no tail'},
    'grit':  {'f': 1100, 'q': .65, 'dur': .135, 'ring': 0,   'grit': .92,
              'why': 'loose aggregate under a boot carries on after the step'},
    'metal': {'f': 2100, 'q': 3.4, 'dur': .155, 'ring': .62, 'grit': .22,
              'why': 'plate and grating ring, and open grating rings longest'},
    'wood':  {'f': 270,  'q': 1.1, 'dur': .115, 'ring': .14, 'grit': .32,
              'why': 'timber knocks low and hollow'},
    'soft':  {'f': 420,  'q': .5,  'dur': .10,  'ring': 0,   'grit': .55,
              'why': 'ground cover damps the step and returns nothing'},
    'wet':   {'f': 700,  'q': .8,  'dur': .17,  'ring': 0,   'grit': .70,
              'why': 'saturated ground slaps and then sucks at the boot'},
}
# every floor PATTERN in the surfaces registry, and every ground RECIPE in
# the world registry, maps to exactly one family - asserted below, so a new
# finish or a new recipe cannot land without someone deciding how it sounds
FLOOR_STEP = {
    'slab': 'hard', 'smooth': 'hard', 'tile': 'hard', 'brick': 'hard',
    'broom': 'grit', 'speckle': 'grit',
    'checker': 'metal', 'grate': 'metal',
    'block': 'wood', 'plank': 'wood',
}
GROUND_STEP = {
    'asphalt': 'hard', 'concrete': 'hard',
    'gravel': 'grit', 'levee': 'grit',
    'grass': 'soft', 'sand': 'soft', 'upland': 'soft', 'marsh': 'soft',
    'mudflat': 'wet', 'water': 'wet',
}
_pats = {f['pattern'] for f in finishes_reg['catalogue'].values()}
assert not sorted(_pats - set(FLOOR_STEP)), (
    f'floor patterns with no step family: {sorted(_pats - set(FLOOR_STEP))}')
assert not sorted(set(FLOOR_STEP) - _pats), (
    f'step families for patterns no finish uses: {sorted(set(FLOOR_STEP) - _pats)}')
assert sorted(GROUND_STEP) == sorted(world_reg['ground']), (
    'GROUND_STEP must name every world ground recipe and no others')
_used = set(FLOOR_STEP.values()) | set(GROUND_STEP.values())
assert not sorted(_used - set(STEP_FAMILIES)), (
    f'unknown step family: {sorted(_used - set(STEP_FAMILIES))}')
assert not sorted(set(STEP_FAMILIES) - _used), (
    f'step family declared and never reachable: {sorted(set(STEP_FAMILIES) - _used)}')

DATA = json.dumps({
    'districts': {k: {'name': d['name'], 'halls': d['halls'], 'hue': HUES[k]}
                  for k, d in districts_reg.items()},
    'campuses': campuses_reg,
    'geo': {'campuses': {k: {'lat': v['lat'], 'lng': v['lng']}
                         for k, v in geo_reg['campuses'].items()},
            'routes': geo_reg['routes_km'],
            'anchors': {k: [{'name': a['name'], 'km': a['km'],
                             'bearing_deg': a['bearing_deg']} for a in lst]
                        for k, lst in geo_reg['anchors'].items()},
            # city-layer placements: true east/north km offsets from the
            # campus point, equirectangular at the campus latitude
            'cityPois': {
                ck: [{'name': a['name'],
                      'e': round((a['lng'] - geo_reg['campuses'][ck]['lng'])
                                 * 111.32 * math.cos(math.radians(
                                     geo_reg['campuses'][ck]['lat'])), 2),
                      'n': round((a['lat'] - geo_reg['campuses'][ck]['lat'])
                                 * 110.574, 2),
                      'km': a['km'], 'bearing': a['bearing_deg'],
                      'lat': a['lat'], 'lng': a['lng'],
                      'src': a['source'], 'prov': a['provenance'],
                      'blurb': a.get('blurb', ''),
                      'bp': a.get('blurb_provenance', '')}
                     for a in geo_reg['anchors'][ck]]
                for ck in geo_reg.get('city', {})}},
    'finMaps': [m for _, m in FIN_MAPS],
    'finIdx': FIN_IDX,
    'roomDefs': ROOM_DEFS,
    'layouts': [lay for _, lay in LAY_LIST],
    'finCat': finishes_reg['catalogue'],
    'step': {'fam': STEP_FAMILIES, 'floor': FLOOR_STEP, 'ground': GROUND_STEP},
    'wallCat': finishes_reg['wall_catalogue'],
    'wallMaps': [m for _, m in WALL_MAPS],
    'wallIdx': WALL_IDX,
    'baseCond': finishes_reg['base_conditions'],
    'condOver': {sl: {st: c for st, c in h['conditions'].items()
                      if c['hazards']}
                 for sl, h in finishes_reg['halls'].items()
                 if any(c['hazards'] for c in h['conditions'].values())},
    'halls': HALLS,
    'stations': {s['station_id']: {k: s[k] for k in (
        'station_id', 'name', 'hall', 'room', 'strand', 'tier',
        'lesson', 'checklist', 'doctrine', 'quiz')}
        for s in stations_reg['stations']},
    'yard': yard,
    'sims': {'sims': sims_reg['sims'], 'bindings': sims_reg['hall_bindings'],
             'honesty': sims_reg['honesty']['status'],
             'walkHonesty': sims_reg['honesty']['walkaround'],
             # the scripted reference operator: its closed level set and
             # its one SCRIPTED honesty line - each seat's own operator
             # metadata (guarantees, procedure) and shared yard layout
             # already travel inside sims_reg['sims'] above
             'operatorLevels': sims_reg['operator_levels'],
             'operatorHonesty': sims_reg['honesty']['operator']},
    'imagery': parcels_reg['imagery'],
    'recHonesty': parcels_reg['honesty'],
    # only what the page actually renders: the endpoint, the query template, and the one line of scope text the lookup button shows
    'elevation': trim(parcels_reg['elevation'], 'name', 'authority',
                      'licence', 'cite', 'cite_file', 'provenance',
                      'verified_from_build', 'verification_note',
                      'traps_guarded', 'id'),
    'tools': {'cribs': tools_reg['cribs'], 'drills': tools_reg['drills'],
              'drill': tools_reg['drill'],
              'honesty': tools_reg['honesty']['status']},
    # characters and apes travel as deltas against the locker defaults
    # (the registry keeps the full truth; the page inflates at boot)
    'avatars': {'sections': avatars_reg['sections'],
                'defaults': avatars_reg['defaults'],
                'characters': [
                    {**{k: c[k] for k in ('id', 'name', 'emoji', 'blurb')},
                     'd': {k: v for k, v in c['cfg'].items()
                           if avatars_reg['defaults'].get(k) != v}}
                    for c in avatars_reg['characters']],
                'tradeapes': {
                    **avatars_reg['tradeapes'],
                    'apes': [
                        {'hall': a['hall'], 'code': a['code'],
                         'district': a['district'], 'hue': a['hue'],
                         'd': {k: v for k, v in a['cfg'].items()
                               if k != 'crew'
                               and avatars_reg['defaults'].get(k) != v}}
                        for a in avatars_reg['tradeapes']['apes']]},
                'emotes': avatars_reg['emotes'],
                'guarantee': avatars_reg['guarantee']},
    'chapters': {'of': {slug: c['home']
                        for slug, c in chapters_reg['chapters'].items()},
                 'regions': {k: v['abbr']
                             for k, v in chapters_reg['regions'].items()},
                 'hosted': chapters_reg['hosted'],
                 'honesty': chapters_reg['honesty']['chapters']},
    'strandmods': strand_modules(),
    # the advisors who stand in the rooms: their look, where each one stands,
    # and the fixed list of questions each can answer. A `read` topic carries
    # only a binding - the page resolves it against the record that already
    # holds the fact, so nothing here is a second copy of one
    # the sky, the weather it is seen under, the ground it stands on and
    # the animals moving through it - every texture a recipe, never a file.
    # The page carries only what it RENDERS; the prose that explains each
    # record stays in the registry and reaches people through the wiki,
    # because a byte shipped to every learner should be one they can see
    'world': {'sky': trim(world_reg['sky'], 'note', 'placement', 'projection'),
              'weather': world_reg['weather'],
              'ground': trim(world_reg['ground'], 'where', 'name'),
              'fauna': trim(world_reg['fauna'], 'why', 'name', 'glyph'),
              'atmos': trim(world_reg['atmos'], 'character'),
              # what each campus is BUILT of - facade pattern, envelope and
              # trim colours, roofline. `why` is prose for the reader and
              # stays out of the wire, like `character` above it.
              'fabric': trim(world_reg['fabric'], 'why')},
    # every sign in the world: its shape, its palette, its type and how it
    # reacts to being looked at - again, only the parts that are drawn
    'labels': {'shapes': trim(labels_reg['shapes'], 'draws', 'reads_as'),
               'palette': labels_reg['palette'],
               'type': trim(labels_reg['type'], 'note'),
               'kinds': trim(labels_reg['kinds'], 'what', 'provenance'),
               'focus': trim(labels_reg['focus'], 'contract', 'focus_rule')},
    # the training-data recorder: only what the page needs to build the
    # UI and the export envelope - the essays stay in the registry, read
    # from the wiki, exactly like the world and label packs
    'training': {'storage': training_reg['storage'],
                 # the page READS its sample interval and cap from here -
                 # the one declared pair, never a second hand-typed one
                 'trace': {'toggle_key': training_reg['trace']['toggle_key'],
                           'sample_hz': training_reg['trace']['sample_hz'],
                           'max_samples': training_reg['trace']['max_samples']},
                 'export_format': trim(training_reg['export_format'],
                     'consumer', 'not_a_demo_file', 'no_agent_trained'),
                 'kinds': trim(training_reg['episode_kinds'],
                     'granularity', 'what'),
                 # the lines actually shown in the records panel;
                 # device-local reuses the existing progress.local i18n
                 # string, and the rest stays registry+wiki only
                 'honesty': {k: training_reg['honesty'][k]
                             for k in ('schematic', 'not_scored',
                                       'orbis_pairing')}},
    # the Orbis prompt contract: text-only, built locally from the union
    # registry already shipped above - no key, no fetch, no second copy
    # of a hall's name or focus. See orbis/build.py for the full contract
    # this trims down to what the page's prompt builder actually needs.
    'orbis': {'model': orbis_reg['model']['id'],
              'template': orbis_reg['prompt_template'],
              'honesty': {k: orbis_reg['honesty'][k]
                          for k in ('synthetic_not_real', 'no_network_here',
                                    'every_module_covered')},
              # this panel only ever builds text - see D.orbis.runners for
              # the two real, separately-installed apps that actually
              # generate a clip. Deliberately just a path and a model id:
              # the full run command names REACTOR_API_KEY by NAME (an
              # instruction, not a value) for an operator's own terminal,
              # and this shipped page never names a key at all, anywhere -
              # each runner's own README carries that instruction instead
              'runners': [{'path': r['path'], 'model': r['model']}
                          for r in orbis_reg['runners']]},
    # the schools pack: the flipped-classroom model, grade bands and
    # proposed-district records this bundle already computes for the
    # wiki - trimmed to what the Schools panel actually renders, same
    # honesty text, no fact re-authored here
    'schools': {'stages': schools_reg['model']['stages'],
                'loop': schools_reg['model']['loop'],
                'bands': schools_reg['bands'],
                'districts': schools_reg['districts'],
                'units': schools_reg['units'],
                'honesty': {k: schools_reg['honesty'][k]
                            for k in ('districts', 'certification')}},
    'advisors': {'who': agents_reg['advisors'],
                 'honesty': agents_reg['honesty'],
                 'walk': geo_reg['walk']},
    # the network roadmap: whatever candidate metros remain, trimmed to
    # what the region board's own markers need - bearing and distance
    # already computed from the flagship campus in roadmap/build.py, not
    # derived twice. Built campuses need no trim here; D.campuses already
    # IS them. With Detroit's promotion, CANDIDATES is empty, so this
    # dict renders nothing - the ten-campus target is fully met.
    'roadmap': {'target': roadmap_reg['target'],
                'candidates': {k: {'name': c['name'], 'city': c['city'],
                                   'region': c['region'],
                                   'districts': c['districts'], 'why': c['why'],
                                   'km_from_flagship': c['km_from_flagship'],
                                   'bearing_from_flagship_deg':
                                       c['bearing_from_flagship_deg']}
                               for k, c in roadmap_reg['candidates'].items()},
                'honesty': {k: roadmap_reg['honesty'][k]
                            for k in ('not_a_claim_of_content',
                                      'provenance_tiers')}},
    # Bay Restoration: real, independently-run sites and the real skills
    # in this bundle's own graph their field work draws on - see
    # restoration/build.py. Nothing here is a SmartCiti.X program.
    # A pinned, campus-grouped site also carries its true east/north km
    # offset from that campus point - the exact formula D.geo.cityPois
    # already uses - so the walkable city layer can place a real marker
    # at it; nothing here re-derives or upgrades the site's own AUTHORED
    # coordinate, it is only re-projected onto the same in-world scale.
    # `walkable` gates this the same as `pin`/`campus` already did: a site
    # with walkable=False (Hunters Point, an actively litigated federal
    # Superfund site, and Former Naval Station Treasure Island, a Navy
    # BRAC cleanup with unresolved radiological criteria - the island the
    # Treasure Island campus scene itself sits on; see restoration/
    # build.py) never gets the e/n offset
    # below, so it can never be placed as a walkable-city marker or
    # entered via startRestorationWalk() - it still reaches the map
    # through its own real pin (the geomap) and the flat panel list
    # (openRestoration), just never the walkable ground scene.
    'restoration': {'sites': [
        {**s, **({'e': round((s['lng'] - geo_reg['campuses'][s['campus']]['lng'])
                              * 111.32 * math.cos(math.radians(
                                  geo_reg['campuses'][s['campus']]['lat'])), 2),
                  'n': round((s['lat'] - geo_reg['campuses'][s['campus']]['lat'])
                             * 110.574, 2)}
           if s.get('pin') and s.get('campus') and s.get('walkable', True) else {})}
        for s in restoration_reg['sites']],
                    'tracks': restoration_reg['tracks'],
                    'honesty': restoration_reg['honesty']},
    'i18n': I18N,
}, ensure_ascii=False, separators=(',', ':'))

SIM_JS = """/* ------------------------------------------------------- simulators ----- */
// Schematic physics for practising control discipline; the graders are
// deterministic - every rubric axis is computed from measured state.
let sim = null, curSimId = null, simView = null, curScenario = null;
let simRider = null;
let waBeacons = [], waDone = new Set(), waTotal = 0;
// the scripted reference operator's live run (null while a human has the
// seat) and the headless flag the sweep raises so the frame loop never
// steps a seat the sweep is stepping at a fixed dt - see OPERATORS below
let opRun = null, opHeadless = false;

/* Sound is synthesized in-page (WebAudio) - the registry says so and no
   recording is shipped. The context is created on the sim-start click, the
   one place a user gesture is guaranteed. */
let ac = null, master = null, engine = null, beeper = null, audioOn = true;
function acEnsure() {
  if (!ac) {
    ac = new (window.AudioContext || window.webkitAudioContext)();
    master = ac.createGain();
    master.gain.value = audioOn ? .9 : 0;
    master.connect(ac.destination);
  }
  if (ac.state === 'suspended') ac.resume();
}
function engineStart(kind) {
  if (kind === 'arc') {
    // the welding arc: looped noise through a highpass - silent until struck
    const src = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
    src.buffer = noiseBuf(1.3); src.loop = true;
    f.type = 'highpass'; f.frequency.value = 1500;
    g.gain.value = 0;
    src.connect(f); f.connect(g); g.connect(master); src.start();
    engine = { osc: src, g, kind };
    return;
  }
  const osc = ac.createOscillator(), g = ac.createGain(), f = ac.createBiquadFilter();
  // electric: the boom lift's hydraulic pump whine - a higher, cleaner tone
  osc.type = kind === 'diesel' ? 'sawtooth' : kind === 'electric' ? 'sine' : 'triangle';
  osc.frequency.value = kind === 'diesel' ? 42 : kind === 'electric' ? 160 : 95;
  f.type = 'lowpass'; f.frequency.value = kind === 'diesel' ? 320 : kind === 'electric' ? 1400 : 900;
  g.gain.value = 0;
  osc.connect(f); f.connect(g); g.connect(master); osc.start();
  engine = { osc, g, kind };
}
function engineSet(load) {  // 0..1 - throttle / hoist activity / arc heat
  if (!engine) return;
  if (engine.kind === 'arc') {
    engine.g.gain.setTargetAtTime(load * .17, ac.currentTime, .03);
    return;
  }
  const base = engine.kind === 'diesel' ? 42 : engine.kind === 'electric' ? 160 : 95;
  engine.osc.frequency.setTargetAtTime(base * (1 + load * 1.6), ac.currentTime, .08);
  engine.g.gain.setTargetAtTime(.05 + load * .13, ac.currentTime, .1);
}
function engineStop() {
  if (engine) { engine.osc.stop(); engine = null; }
  if (beeper) { beeper.o.stop(); beeper = null; }
}
function beeperEnsure() {
  if (beeper) return;
  const o = ac.createOscillator(), g = ac.createGain();
  o.type = 'square'; o.frequency.value = 950; g.gain.value = 0;
  o.connect(g); g.connect(master); o.start();
  beeper = { o, g };
}
function beeperSet(on) {  // the pulsing reverse beeper, gated per frame
  if (!beeper) return;
  const t = ac.currentTime;
  beeper.g.gain.setTargetAtTime(
    on && Math.floor(t * 2.5) % 2 === 0 ? .05 : 0, t, .012);
}
function blip(f0, f1, dur, type = 'sine', vol = .14) {
  if (!ac) return;
  const o = ac.createOscillator(), g = ac.createGain(), t = ac.currentTime;
  o.type = type; o.frequency.setValueAtTime(f0, t);
  if (f1) o.frequency.exponentialRampToValueAtTime(f1, t + dur);
  g.gain.setValueAtTime(vol, t);
  g.gain.exponentialRampToValueAtTime(.001, t + dur);
  o.connect(g); g.connect(master); o.start(t); o.stop(t + dur + .02);
}
function thud() {  // filtered noise burst: a cone clipped, a stack struck
  if (!ac) return;
  const n = Math.floor(ac.sampleRate * .12), buf = ac.createBuffer(1, n, ac.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
  const s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
  s.buffer = buf; f.type = 'lowpass'; f.frequency.value = 220; g.gain.value = .5;
  s.connect(f); f.connect(g); g.connect(master); s.start();
}
function chime(good) {
  (good ? [660, 880, 1320] : [440, 330]).forEach((f, i) =>
    setTimeout(() => blip(f, null, .3, 'triangle', .12), i * 120));
}

/* Haptics, where the platform offers them: gamepad rumble and the vibration
   API. Both are best-effort - absence is silent, never an error. */
function buzz(ms, mag = .6) {
  try { navigator.vibrate?.(ms); } catch (e) { /* unsupported */ }
  try {
    for (const gp of navigator.getGamepads?.() ?? []) {
      gp?.vibrationActuator?.playEffect?.('dual-rumble',
        { duration: ms, strongMagnitude: mag, weakMagnitude: mag * .6 });
    }
  } catch (e) { /* unsupported */ }
  // in a headset: the XR input sources' own actuators (WebXR Gamepads
  // Module), both hands - absent on a platform without them, never an error
  try {
    for (const src of renderer.xr.getSession()?.inputSources ?? [])
      src.gamepad?.hapticActuators?.[0]?.pulse?.(mag, ms);
  } catch (e) { /* unsupported */ }
}

/* The dash is data-driven: the sims registry declares every gauge (id,
   label, unit, warn threshold), and each sim only supplies live values. */
const dashCells = new Map();        // gauge id -> { cell, gv, txt, warn }
function initDash(def) {
  const el = document.getElementById('dash');
  el.innerHTML = def.dash.map((g) =>
    `<div class="g" id="g-${g.id}"><span class="gv">\\u2013</span>` +
    `<span class="gl">${g.label}${g.unit ? ' ' + g.unit : ''}</span></div>`).join('');
  el.style.display = 'flex';
  dashCells.clear();
  for (const g of def.dash) {
    const cell = document.getElementById('g-' + g.id);
    dashCells.set(g.id, { cell, gv: cell.querySelector('.gv'), txt: null, warn: null });
  }
}
// one formatter for a gauge value, read by the DOM dash and the XR wrist
// panel alike, so the two never show a different number for the same gauge
function gaugeText(x) {
  const v = typeof x === 'object' ? x.v : x;
  return typeof x === 'object' && x.txt !== undefined ? x.txt
    : Math.abs(v) >= 100 ? String(Math.round(v)) : (Math.round(v * 10) / 10).toFixed(1);
}
// written only on change: every gauge used to be rewritten every frame
// (6-7 DOM mutations per frame in every seat) whether or not it moved
function setDash(def, vals) {
  for (const g of def.dash) {
    const c = dashCells.get(g.id);
    const x = vals[g.id];
    if (!c || x === undefined) continue;
    const v = typeof x === 'object' ? x.v : x;
    const txt = gaugeText(x);
    if (txt !== c.txt) { c.gv.textContent = txt; c.txt = txt; }
    const warn = g.warn_at !== undefined && v >= g.warn_at;
    if (warn !== c.warn) { c.cell.classList.toggle('warn', warn); c.warn = warn; }
  }
}

function setSimView(mode) {
  simView = mode;
  document.getElementById('camBtn').textContent =
    '\\u25a6 ' + t('sim.view') + ': ' + mode;
  controls.enabled = mode === 'orbit';
  if (mode === 'orbit') {
    // a sim may declare its own orbit frame (a bench sits closer than a tower)
    const oc = sim?.orbitCam;
    camera.position.set(...(oc?.pos ?? [36, 28, 42]));
    controls.target.set(...(oc?.tgt ?? [0, 11, 0]));
    controls.update();
    // in a headset the orbit frame is a viewpoint: the rig stands where the
    // orbit camera would, facing the target, and the head is free
    if (xrLive()) xrOrbitPlace(oc?.pos ?? [36, 28, 42], oc?.tgt ?? [0, 11, 0]);
  }
}

/* A seat is a POSE, not a camera write. Every operator view (cab, driver,
   visor, deck, signal, chart, wand, spray, basket, pendant) hands its eye
   position and the point it looks at here, once per frame. On a desktop
   this is exactly the camera.position + lookAt it always was. Presenting
   in a headset, the pose lands on the XR rig instead - the rig stands
   where the eye would (floor-relative, so the headset's own height is
   added back, not doubled) and turns to face the look point - and the
   camera is never written, because the headset owns it. */
const _seatP = new THREE.Vector3();
function seatPose(px, py, pz, lx, ly, lz, lerp = 0) {
  if (!renderer.xr.isPresenting) {
    if (lerp) camera.position.lerp(_seatP.set(px, py, pz), lerp);
    else camera.position.set(px, py, pz);
    camera.lookAt(lx, ly, lz);
    return;
  }
  // the head's height above the rig floor is the headset's own reading
  // (about 1.6 m in a local-floor space, near 0 in a plain local one)
  _seatP.set(px, py - camera.position.y, pz);
  if (lerp) xrRig.position.lerp(_seatP, lerp); else xrRig.position.copy(_seatP);
  xrRig.rotation.set(0, Math.atan2(-(lx - px), -(lz - pz)), 0);
}
function xrOrbitPlace(pos, tgt) {
  // xrHeadY, not camera.position.y: the orbit controls have just written
  // their own frame into the camera, and the headset overwrites it next frame
  xrRig.position.set(pos[0], pos[1] - xrHeadY, pos[2]);
  xrRig.rotation.set(0, Math.atan2(-(tgt[0] - pos[0]), -(tgt[2] - pos[2])), 0);
}

// the Operator's mesh is a child of sim.group, so disposeOf(sim.group)
// below frees it - this just drops the now-dangling advisorMeshes entry
// so proximity/rendering never touches a mesh no longer in the scene
function clearOperatorAdvisor() {
  const i = advisorMeshes.findIndex((m) => m.userData.advisor === 'operator');
  if (i >= 0) advisorMeshes.splice(i, 1);
  if (nearAdvisor === 'operator') nearAdvisor = null;
}

function teardownSim() {
  if (!sim) return;
  clearOperatorAdvisor();
  // the scripted operator leaves with the seat: drop its run and lift
  // every key it was holding, so nothing it pressed leaks into walk mode
  opRun = null;
  for (const kk of OP_KEYS) keys[kk] = false;
  xrPadRelease();
  document.getElementById('opCtl').style.display = 'none';
  scene.remove(sim.group);
  disposeOf(sim.group);
  sim = null; simView = null; curScenario = null; simRider = null;
  waBeacons = []; waDone = new Set(); waTotal = 0;
  controls.enabled = true;
  engineStop();
  const dash = document.getElementById('dash');
  dash.style.display = 'none'; dash.innerHTML = '';
  document.getElementById('camBtn').style.display = 'none';
  document.getElementById('sndBtn').style.display = 'none';
  document.getElementById('opBtn').style.display = 'none';
  xrHudClear();
}

function exitSim() { teardownSim(); showHall(slug); }

function startSim(simId, scenarioId) {
  // a walker in a headset hands the rig to the seat; a desktop walker unlocks
  if (xrWalk) { xrWalk = false; walkActive = false; }
  else walkLeave();
  if (sim) teardownSim();
  if (curRestoSite) teardownRestoWalk();
  simTicks = []; traceClock = 0;
  curSimId = simId; view = 'sim';
  if (hallGroup) hallGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  if (regionGroup) regionGroup.visible = false;
  ground.visible = grid.visible = true;
  applyAtmos(campusKey);
  scene.fog.near = 90 * fogMul; scene.fog.far = 260 * fogMul;
  document.getElementById('mm').style.display = 'none';
  document.getElementById('glbBtn').style.display = 'none';
  document.getElementById('glbInBtn').style.display = 'none';
  const def = D.sims.sims[simId];
  // the campus you train at picks the regional scenario; the rubric never
  // varies. A scenario id names one outright - the scripted operator's
  // sweep and a retry of the same yard use that
  const sc = def.scenarios?.find((s) => s.id === scenarioId)
    ?? def.scenarios?.find((s) => s.campus === campusKey)
    ?? def.scenarios?.[0] ?? null;
  curScenario = sc;
  const P = sc?.params ?? {};
  sim = simId === 'crane-lift' ? craneSim(P)
    : simId === 'excavator-trench' ? excavatorSim(P)
    : simId === 'weld-bead' ? weldSim(P)
    : simId === 'scaffold-bay' ? scaffoldSim(P)
    : simId === 'rigging-signals' ? riggingSim(P)
    : simId === 'load-chart' ? loadChartSim(P)
    : simId === 'pressure-washer' ? pressureWasherSim(P)
    : simId === 'airless-sprayer' ? paintSprayerSim(P)
    : simId === 'boom-lift' ? boomLiftSim(P)
    : simId === 'overhead-crane' ? overheadCraneSim(P) : forkliftSim(P);
  scene.add(sim.group);
  // your avatar takes the seat the sim declares - the learner is IN the yard
  if (sim.mount) {
    cfgInit();
    simRider = buildAvatarMesh(avatarCfg);
    simRider.scale.multiplyScalar(.92);
    simRider.position.set(...sim.mount.pos);
    simRider.rotation.y = sim.mount.yaw;
    if (sim.mount.seated) {
      const { arms } = simRider.userData;
      arms.armL.rotation.x = arms.armR.rotation.x = -1.05;
    }
    if (sim.mount.armUp) {
      // the signalperson: one hand high where the operator can read it
      simRider.userData.arms.armR.rotation.x = -2.7;
    }
    sim.mount.parent.add(simRider);
  }
  // the pre-shift walkaround: five clipboards ringing the machine. A
  // habit-builder, not a gate - the registry says so: nothing is locked
  // behind them and marking them changes no score.
  waBeacons = []; waDone = new Set(); waTotal = 0;
  if (def.walkaround) {
    waTotal = def.walkaround.length;
    const wb = new THREE.Box3().setFromObject(sim.group);
    const wr = Math.min(16, Math.max(7,
      Math.max(wb.max.x - wb.min.x, wb.max.z - wb.min.z) / 2 + 3));
    const wcx = (wb.min.x + wb.max.x) / 2, wcz = (wb.min.z + wb.max.z) / 2;
    def.walkaround.forEach((w, i) => {
      const ang = i * Math.PI * 2 / waTotal + .35;
      const px = wcx + Math.cos(ang) * wr, pz = wcz + Math.sin(ang) * wr;
      box(.06, 1.05, .06, mat.part, px, .55, pz, sim.group);
      const clip = box(.36, .46, .05, mat.paint, px, 1.25, pz, sim.group);
      clip.lookAt(wcx, 1.25, wcz);
      clip.userData.wapt = i;
      waBeacons.push(clip);
    });
    // the Operator: a live advisor standing in THIS seat's own yard, not a
    // hall room - a step outside the walkaround ring so it never overlaps
    // a clipboard or the machine itself. See agents/build.py for why its
    // topics bind to curSimId rather than the hall's first bound seat.
    const oAng = -1.9, oRad = wr + 3.2;
    placeAdvisor('operator', sim.group,
      wcx + Math.cos(oAng) * oRad, wcz + Math.sin(oAng) * oRad, null);
  }
  const ob = document.getElementById('opBtn');
  ob.style.display = '';
  ob.textContent = '\U0001f477 ' + t('sim.operator');
  // the scripted reference operator's own control: pick a level, watch it
  // drive this seat at real time (see OPERATORS) - not offered headless,
  // where there is nobody to watch
  if (!opHeadless) {
    const lv = document.getElementById('opLvl');
    lv.innerHTML = Object.keys(D.sims.operatorLevels).map((l) =>
      `<option value="${l}">${l}</option>`).join('');
    document.getElementById('opCtl').style.display = '';
  }
  // a seat used to hide the headset buttons because its cab view wrote the
  // camera every frame; a seat now writes a POSE (seatPose) that lands on
  // the XR rig while presenting, so every seat is operable in-session
  controls.autoRotate = false;
  setSimView(def.view_modes[0]);
  acEnsure(); engineStart(def.audio.engine === 'diesel' ? 'diesel'
    : def.audio.engine === 'arc' ? 'arc'
    : def.audio.engine === 'electric-hydraulic' ? 'electric' : 'hoist');
  if (def.audio.alerts.includes('reverse-beeper')) beeperEnsure();
  initDash(def);
  document.getElementById('hname').textContent =
    def.name + ' \\u2014 ' + D.halls.find(x => x.slug === slug).name;
  document.getElementById('hfocus').textContent =
    (sc ? sc.name + ' \\u2014 ' + sc.brief + ' ' : '') + def.task;
  document.getElementById('hint').textContent =
    def.controls.map(c => c.keys + ' ' + c.action).join(' \\u00b7 ') + ' \\u00b7 Esc';
  document.getElementById('simBtn').style.display = 'none';
  document.getElementById('walkBtn').style.display = 'none';
  document.getElementById('avaBtn').style.display = 'none';
  wheelShow(false);
  if (avatarGroup) avatarGroup.visible = false;
  document.getElementById('camBtn').style.display = '';
  const sb = document.getElementById('sndBtn');
  sb.style.display = '';
  sb.textContent = '\\u266a ' + t('sim.sound') + (audioOn ? '' : ' \\u2717');
}

document.getElementById('camBtn').addEventListener('click', () => {
  if (!sim) return;
  const modes = D.sims.sims[curSimId].view_modes;
  setSimView(modes[(modes.indexOf(simView) + 1) % modes.length]);
});
document.getElementById('sndBtn').addEventListener('click', () => {
  audioOn = !audioOn;
  if (master) master.gain.value = audioOn ? .9 : 0;
  document.getElementById('sndBtn').textContent =
    '\\u266a ' + t('sim.sound') + (audioOn ? '' : ' \\u2717');
});
document.getElementById('opBtn').addEventListener('click', () => {
  if (sim) openAdvisor('operator');
});
// watch the scripted reference operator drive this seat, at real time, at
// the chosen level: the same seat and yard restarted with the operator in
// it - its run records as a SCRIPTED episode, never as the learner's own
document.getElementById('opRefBtn').addEventListener('click', () => {
  if (!sim) return;
  const id = curSimId, sc = curScenario?.id, level = document.getElementById('opLvl').value;
  startSim(id, sc);
  opAttach(level, 1, false);
});

function simResults(simId, rows, passed) {
  const def = D.sims.sims[simId];
  const i = D.i18n[loc];
  if (!opRun?.sweep) { chime(passed); buzz(passed ? 180 : 90, .5); }
  // the run lands in the device-local record, naming who drove the seat
  recordEpisode({ kind: 'sim', campus: curScenario?.campus ?? campusKey, hall: slug, sim: simId,
    scenario: curScenario?.id ?? null,
    actor: opRun ? 'scripted-reference' : 'human',
    ...(opRun ? { operator: { level: opRun.level, seed: opRun.seed, scenario: opRun.scenario,
      steps: opRun.step, dt: opRun.fixedDt } } : {}),
    controls: def.controls.map((c) => c.action),
    outcome: traceOn && simTicks.length
      ? { passed, rows, trace: simTicks }
      : { passed, rows } });
  const rec = prog.sims[simId] ?? {};
  if (!opRun) {
    // a human run: runs, passes, best time. A scripted reference run is
    // its own record (the episode above) and never the learner's - no
    // progress credit, no best time, and a headless sweep shows no panel
    rec.runs = (rec.runs ?? 0) + 1;
    if (passed) {
      rec.passed = true;
      const tv = parseFloat(rows.find((r) => r.axis === 'time')?.value);
      if (isFinite(tv)) rec.best = Math.min(rec.best ?? Infinity, tv);
    }
    prog.sims[simId] = rec; saveProg(); renderChrome();
  } else {
    opRun.result = { passed, rows };
    if (opRun.sweep) return;
  }
  const recLine = rec.passed && isFinite(rec.best)
    ? `<p style="color:var(--muted);font-size:12.5px">\\u2713 ${rec.runs}\\u00d7 \\u00b7 best ${rec.best.toFixed(1)} s</p>`
    : '';
  const opChip = opRun
    ? `<span class="chip">\U0001f916 scripted reference \\u00b7 ${opRun.level} \\u00b7 not your record</span>`
    : '';
  document.getElementById('pbody').innerHTML = `
    <h2>${def.name}</h2>
    <span class="chip" style="${passed ? 'border-color:var(--good);color:var(--good)' : 'border-color:var(--crit);color:var(--crit)'}">
      ${passed ? t('sim.pass') : t('sim.retry')}</span>${opChip}
    <h3>${t('sim.results')}</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13.5px"><tbody>
      ${rows.map(r => `<tr><td>${r.axis}</td>
        <td style="text-align:end;font-family:'IBM Plex Mono',monospace">${r.value}</td>
        <td style="text-align:end">${r.ok === null ? '' : r.ok ? '\\u2713' : '\\u2717'}</td></tr>`).join('')}
    </tbody></table>
    ${recLine}
    <p style="color:var(--muted);font-size:12px;margin-top:12px">${D.sims.honesty} ${t('progress.local')}</p>
    <p><button class="barbtn" id="simRetry">\\u21bb ${t('sim.retry')}</button>
       <button class="barbtn" id="simExit">${t('ui.close')}</button></p>
    <style>#pbody td{border-top:1px solid var(--rule);padding:6px 8px;color:var(--muted)}</style>`;
  document.body.classList.add('open');
}

/* ------------------------------------------------ a lever is not a switch --
   Four of the machine seats drove their axes as ON/OFF velocity: press A
   and the jib slews at full rate that instant, release and it stops dead.
   The forklift was the one seat that already did it properly - it carries
   an acceleration and lerps its steering - so this is the other four
   catching up with the precedent already in this file.

   `drive` moves a normalised command level (-1..1) toward what the operator
   is asking for, at a spool-up rate when it is building and a spool-down
   rate when it is coming off. That is what makes a lift feel like a lift:
   you cannot stop a slew on a mark, so you come off the lever early, and a
   load that is already swinging punishes you for not having.

   SCHEMATIC, like the rest of the physics here: this is the SHAPE of a
   hydraulic drive - build, hold, coast - not any machine's real response
   curve, and the sims registry's honesty line still governs.  */
const SPOOL = { up: 3.2, down: 4.0 };     // per second, toward the commanded level
function drive(cur, want, dt, sp = SPOOL) {
  const rate = (want === 0 || want * cur < 0) ? sp.down : sp.up;
  const step = rate * dt;
  return cur + Math.max(-step, Math.min(step, want - cur));
}
const axis = (neg, pos) => (pos ? 1 : 0) - (neg ? 1 : 0);
/* A machine with something in its hand is slower than an empty one: a
   loaded hoist is line pull, not free fall, and a full bucket is weight on
   the same pump. One factor, applied to the axis that actually carries the
   load, so the operator feels the pick change the machine. SCHEMATIC. */
const LOADED = .62;

/* A fenced training yard, so a sim reads as a place on the campus rather
   than a void: perimeter fence, corner light masts, painted apron border. */
function simYard(g, hw, hd, cx = 0, cz = 0, simId = curSimId) {
  const fence = new THREE.MeshStandardMaterial({ color: 0x5a6468, roughness: .6 });
  const lamp = new THREE.MeshStandardMaterial({
    color: 0xfff2cf, emissive: 0xffdf9a, emissiveIntensity: .9 });

  /* The yard's own floor. Until now a sim yard was a fence and four masts
     standing on the page's global ground plane, so the welder, the
     excavator and the pressure washer all worked on the same nothing. Each
     seat declares what it stands on in the sims registry, by an id from the
     surfaces catalogue - one truth, in the pack that owns it - and it is
     laid here with the same relief every hall floor got. */
  const yard = D.sims.sims[simId]?.yard;
  if (yard) {
    const fin = D.finCat[yard.surface];
    const fmat = finishMat(fin, hw * 2 / U * 2, hd * 2 / U * 2);
    const floor = new THREE.Mesh(boxGeo(hw * 2, .12, hd * 2), fmat);
    floor.position.set(cx, -.06, cz); floor.receiveShadow = true;
    floor.userData.yardSurface = yard.surface;
    g.add(floor);
  }
  for (let x = -hw; x <= hw; x += 6) {
    box(.14, 1.9, .14, fence, cx + x, .95, cz - hd, g);
    box(.14, 1.9, .14, fence, cx + x, .95, cz + hd, g);
  }
  for (let z = -hd + 6; z <= hd - 6; z += 6) {
    box(.14, 1.9, .14, fence, cx - hw, .95, cz + z, g);
    box(.14, 1.9, .14, fence, cx + hw, .95, cz + z, g);
  }
  box(hw * 2, .08, .06, fence, cx, 1.55, cz - hd, g, false);
  box(hw * 2, .08, .06, fence, cx, 1.55, cz + hd, g, false);
  box(.06, .08, hd * 2, fence, cx - hw, 1.55, cz, g, false);
  box(.06, .08, hd * 2, fence, cx + hw, 1.55, cz, g, false);
  box(hw * 2, .04, .5, mat.paint, cx, .03, cz - hd + 1.2, g, false);
  box(hw * 2, .04, .5, mat.paint, cx, .03, cz + hd - 1.2, g, false);
  for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    const mx = cx + sx * (hw - 1.4), mz = cz + sz * (hd - 1.4);
    box(.3, 9, .3, mat.metal, mx, 4.5, mz, g);
    box(1.5, .35, .55, lamp, mx, 9.15, mz, g, false);
    // The mast head was an emissive box: a bright object that lit nothing,
    // so a yard at dusk was a yard with four glowing rectangles in the dark.
    // It carries a real light now, reaching its own quarter of the yard, on
    // the same quality-ladder budget the room lights ride.
    // reach the far side of the yard, not a quarter of it: four masts at a
    // corner each have to overlap in the middle or the middle is where the
    // work happens in the dark
    const ml = new THREE.PointLight(0xffe9c8, lampCd(2.6, 8.7, 1.35),
      Math.hypot(hw, hd) * 2.2, 1.35);
    ml.position.set(mx, 8.7, mz);
    ml.visible = qLevel !== 'low';
    g.add(ml); roomLights.push(ml);
  }

  /* The yard's own working light.
     A seat is entered from a hall, so it inherits that campus's sky - and
     every campus here is authored at dusk or under a marine layer. Measured
     on a running seat, 95% of the frame sat below 54/255: the machine, the
     yard surface and the gauges were all in the dark, which is not what a
     yard a crew is working in looks like at any hour.
     A yard therefore carries its own hemisphere, sized to it, sky-coloured
     from the campus's own atmosphere so the place still reads as that place.
     It is a FIXTURE, like the masts: it goes in the group, rides the quality
     ladder and is freed with the seat. */
  const atmY = D.world.atmos?.[campusKey];
  const yardHemi = new THREE.HemisphereLight(
    atmY?.hemi?.sky ?? 0xaec2cb, 0x2a2622, 1.45);
  yardHemi.position.set(cx, 12, cz);
  yardHemi.visible = qLevel !== 'low';
  g.add(yardHemi); roomLights.push(yardHemi);
}

/* --------------------------------------------------- tower crane lift ---- */
function craneSim(P = {}) {
  const sh = P.stack_h ?? 1, drift = P.drift ?? 0;
  const g = new THREE.Group();
  simYard(g, 33, 30);
  const MAST_H = 24, JIB = 28;
  box(1.4, MAST_H, 1.4, mat.metal, 0, MAST_H / 2, 0, g);
  const slewG = new THREE.Group(); slewG.position.y = MAST_H; g.add(slewG);
  box(JIB, .9, 1.1, mat.post, JIB / 2 - 3, .8, 0, slewG);
  box(7, .9, 1.1, mat.metal, -6.5, .8, 0, slewG);
  box(2.2, 2.2, 2.2, mat.part, -8.5, -.4, 0, slewG);   // counterweight
  box(1.8, 1.8, 1.8, mat.win, 1.6, -1, 1.4, slewG);    // cab
  const trolley = box(1.2, .6, 1.2, mat.steel, 10, .1, 0, slewG);
  const cableMat = new THREE.LineBasicMaterial({ color: 0xd8dde0 });
  const cableGeo = new THREE.BufferGeometry().setFromPoints(
    [new THREE.Vector3(), new THREE.Vector3()]);
  g.add(new THREE.Line(cableGeo, cableMat));
  const hook = new THREE.Mesh(new THREE.OctahedronGeometry(.45), mat.post);
  hook.castShadow = true; g.add(hook);
  // the supply pad and target ring sit where the registry's layout says -
  // the one truth this sim and its scripted operator both read
  const LAY = D.sims.sims['crane-lift'].layout;
  const load = box(2.4, 1.6, 2.4, mat.brick, LAY.supply[0], .8, LAY.supply[1], g);
  // pads and obstacles
  const supply = box(4, .2, 4, mat.slab, LAY.supply[0], .1, LAY.supply[1], g, false);
  const target = new THREE.Mesh(new THREE.RingGeometry(1.6, 2.6, 32),
    new THREE.MeshBasicMaterial({ color: 0x5CB584, side: THREE.DoubleSide }));
  target.rotation.x = -Math.PI / 2;
  target.position.set(LAY.target[0], .12, LAY.target[1]); g.add(target);
  const stacks = [box(5, 6 * sh, 3, mat.wall, 2, 3 * sh, -12, g),
                  box(4, 8 * sh, 3, mat.wall, -3, 4 * sh, 4, g)];
  const st = { slew: .6, r: 14.5, h: 6, vslew: 0, attached: false, done: false,
               cS: 0, cT: 0, cH: 0,   // commanded lever levels, spooled
               loadV: new THREE.Vector2(), swingPeak: 0, swingNow: 0, strikes: 0,
               inStrike: false, t0: null, act: 0, chirped: false };
  // start the hook over open ground
  // update() runs every frame and passes its own scratch vector so the
  // hot path allocates nothing; action() fires rarely (a keypress), so it
  // keeps the simple allocate-a-fresh-one default
  const _hp = new THREE.Vector3(), _tp = new THREE.Vector3();
  function hookPos(out = new THREE.Vector3()) {
    return out.set(Math.cos(st.slew) * st.r, st.h, Math.sin(st.slew) * st.r);
  }
  function finish() {
    st.done = true;
    const d = Math.hypot(load.position.x - target.position.x,
                         load.position.z - target.position.z);
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'placement', value: d.toFixed(2) + ' m', ok: d <= 1.2 },
      { axis: 'swing', value: st.swingPeak.toFixed(2) + ' m', ok: st.swingPeak <= 2.0 },
      { axis: 'strikes', value: String(st.strikes), ok: st.strikes === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('crane-lift', rows, d <= 1.2 && st.swingPeak <= 2 && st.strikes === 0);
  }
  return {
    group: g, orbit: true,
    mount: { parent: g, pos: [4.4, 0, 2.6], yaw: -.6 },
    action() {
      if (st.done) return;
      const hp = hookPos();
      if (!st.attached) {
        const d = Math.hypot(hp.x - load.position.x, hp.z - load.position.z);
        if (d < 1.6 && hp.y < 4.5) {
          st.attached = true; st.t0 = performance.now();
          st.loadV.set(0, 0);
        }
      } else { st.attached = false; load.position.y = .8; finish(); }
    },
    update(dt) {
      if (st.done) return;
      const sr = 0.55, tr = 6, hr = 5 * (st.attached ? LOADED : 1);
      // slew, trolley and hoist all spool up and coast down: the jib does
      // not start or stop on the key, and the load knows it - and the hoist
      // is slower on the pick than it is on the empty hook
      st.cS = drive(st.cS, axis(keys.KeyA, keys.KeyD), dt);
      st.cT = drive(st.cT, axis(keys.KeyS, keys.KeyW), dt);
      st.cH = drive(st.cH, axis(keys.KeyE, keys.KeyQ), dt);
      st.slew += sr * st.cS * dt;
      st.r = Math.max(4, Math.min(26, st.r + tr * st.cT * dt));
      st.h = Math.max(1.2, Math.min(22, st.h + hr * st.cH * dt));
      const moving = Math.abs(st.cS) * .4 + Math.abs(st.cT) * .3 + Math.abs(st.cH) * .5;
      st.act += (Math.min(1, moving) - st.act) * Math.min(1, 5 * dt);
      engineSet(st.act);
      slewG.rotation.y = -st.slew;
      trolley.position.x = st.r;
      const hp = hookPos(_hp);
      if (st.attached) {
        // pendulum: the load chases the hook in the plan, and it shows;
        // a scenario's river breeze is a constant, deterministic lean
        st.loadV.x += drift * 1.5 * dt;
        const k = 4.5, damp = 1.6;
        const ax = (hp.x - load.position.x) * k - st.loadV.x * damp;
        const az = (hp.z - load.position.z) * k - st.loadV.y * damp;
        st.loadV.x += ax * dt; st.loadV.y += az * dt;
        load.position.x += st.loadV.x * dt;
        load.position.z += st.loadV.y * dt;
        load.position.y = Math.max(.8, hp.y - 2.2);
        const swing = Math.hypot(hp.x - load.position.x, hp.z - load.position.z);
        st.swingNow = swing;
        st.swingPeak = Math.max(st.swingPeak, swing);
        if (swing > 1.6 && !st.chirped) { st.chirped = true; blip(600, 1200, .25); }
        if (swing < 1.2) st.chirped = false;
        // strikes against the stacks
        let hit = false;
        for (const b of stacks) {
          const bb = b.geometry.parameters;
          if (Math.abs(load.position.x - b.position.x) < bb.width / 2 + 1.2
            && Math.abs(load.position.z - b.position.z) < bb.depth / 2 + 1.2
            && load.position.y - .8 < b.position.y + bb.height / 2) hit = true;
        }
        if (hit && !st.inStrike) { st.strikes++; st.inStrike = true; thud(); buzz(140); }
        if (!hit) st.inStrike = false;
      } else st.swingNow = 0;
      if (st.attached) {
        hook.position.set(load.position.x, load.position.y + 1.6, load.position.z);
      } else {
        hook.position.copy(hp);
        hook.position.y = Math.max(1.4, hp.y - 1);
      }
      const pts = cableGeo.attributes.position.array;
      const tp = _tp.set(Math.cos(st.slew) * st.r, MAST_H, Math.sin(st.slew) * st.r);
      pts[0] = tp.x; pts[1] = tp.y; pts[2] = tp.z;
      pts[3] = hook.position.x; pts[4] = hook.position.y; pts[5] = hook.position.z;
      cableGeo.attributes.position.needsUpdate = true;
      if (simView === 'cab') {
        // the operator's cab hangs BELOW the jib (sight to the hook must
        // clear it - the hook always rides directly under the jib line)
        const eye = slewG.localToWorld(new THREE.Vector3(3.8, -.6, 1.4));
        // aim between the hook and the horizon so the yard stays in frame
        seatPose(eye.x, eye.y, eye.z, hook.position.x, hook.position.y + 8, hook.position.z);
      }
    },
    gauges: () => ({
      slew: ((st.slew * 180 / Math.PI) % 360 + 360) % 360,
      radius: st.r,
      hook: st.h,
      swing: st.swingNow,
      strikes: { v: st.strikes, txt: String(st.strikes) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* ------------------------------------------------ excavator trench cut --- */
function excavatorSim(P = {}) {
  const g = new THREE.Group();
  simYard(g, 26, 20);
  // the machine: tracks fixed, house slews, boom+stick reach by 2-link IK
  const L1 = 5, L2 = 4.2, PIV_Y = 1.9;
  box(1.1, .7, 4.2, mat.part, -.95, .35, 0, g);
  box(1.1, .7, 4.2, mat.part, .95, .35, 0, g);
  const hg = new THREE.Group(); hg.position.y = .7; g.add(hg);
  box(2.2, 1.3, 2.6, mat.post, 0, .75, -.3, hg);        // house
  box(1.4, 1, 1, mat.part, 0, .8, -1.6, hg);            // counterweight
  box(.9, 1, .9, mat.win, .8, 1.6, .4, hg);             // cab
  const boomG = new THREE.Group();
  boomG.position.set(0, PIV_Y - .7, .2); hg.add(boomG);
  box(L1, .5, .4, mat.metal, L1 / 2, 0, 0, boomG);
  const stickG = new THREE.Group();
  stickG.position.set(L1, 0, 0); boomG.add(stickG);
  box(L2, .32, .3, mat.metal, L2 / 2, 0, 0, stickG);
  const bucket = box(.9, .7, .95, mat.part, L2, -.3, 0, stickG);
  const spoilInBucket = box(.7, .4, .75, mat.wood, L2, .15, 0, stickG, false);
  spoilInBucket.visible = false;
  // the trench: cells and flagged utilities come from the regional scenario;
  // the trench line, cell pitch, spoil zone and bite are the registry's
  // layout - read here and by the scripted operator, typed nowhere twice
  const LAY = D.sims.sims['excavator-trench'].layout;
  const SPEC = P.cells ?? [{ d: 1.5 }, { d: 1.5 }, { d: .5, util: true }, { d: 1.5 }];
  const CZ = LAY.trench_z, span = SPEC.length - 1;
  const cells = SPEC.map((c, i) => {
    const cx = (i - span / 2) * LAY.pitch;
    const m = new THREE.Mesh(boxGeo(1.8, .1, 1.8),
      new THREE.MeshStandardMaterial({ color: 0x53575a, roughness: .95 }));
    m.position.set(cx, .05, CZ); m.receiveShadow = true; g.add(m);
    return { x: cx, z: CZ, target: c.d, d: 0, util: !!c.util, struck: false, mesh: m };
  });
  const markW = SPEC.length * 2 + 1.2;
  box(markW, .04, .28, mat.paint, 0, .11, CZ - 1.1, g, false);  // trench edge marks
  box(markW, .04, .28, mat.paint, 0, .11, CZ + 1.1, g, false);
  // utility flagging: locate posts + a painted crossing stripe per flagged cell
  const flagMat = new THREE.MeshStandardMaterial({
    color: 0xf2c744, emissive: 0x6b5410, roughness: .5 });
  for (const c of cells.filter((x) => x.util)) {
    box(.1, 1.1, .1, flagMat, c.x - 1.1, .55, c.z, g);
    box(.1, 1.1, .1, flagMat, c.x + 1.1, .55, c.z, g);
    box(.3, .04, 2.4, flagMat, c.x, .12, c.z, g, false);
  }
  // spoil zone and its growing pile
  const PAD = { x: LAY.spoil[0], z: LAY.spoil[1] };
  const pad = new THREE.Mesh(new THREE.CylinderGeometry(1.9, 1.9, .08, 28),
    new THREE.MeshBasicMaterial({ color: 0x8a6a42, transparent: true, opacity: .4 }));
  pad.position.set(PAD.x, .05, PAD.z); g.add(pad);
  const pile = new THREE.Mesh(new THREE.ConeGeometry(1.3, 1.1, 16), mat.wood);
  pile.position.set(PAD.x, .1, PAD.z); pile.scale.setScalar(.01);
  pile.castShadow = true; g.add(pile);
  const st = { slew: .35, r: 5.5, bh: 1.4, act: 0, carrying: false, done: false,
               cS: 0, cR: 0, cB: 0,   // commanded lever levels, spooled
               strikes: 0, spoilIn: 0, spoilOut: 0, t0: null };
  const tipPos = () => new THREE.Vector3(
    Math.cos(st.slew) * st.r, st.bh, Math.sin(st.slew) * st.r);
  function cellShade(c) {
    const over = c.d > c.target + .01;
    const shade = Math.min(1, c.d / c.target);
    c.mesh.material.color.setHSL(over ? .02 : .58, over ? .45 : .2,
      .33 - .2 * shade);
  }
  function finish() {
    st.done = true;
    const atGrade = cells.filter((c) => Math.abs(c.d - c.target) < .01).length;
    const dumps = st.spoilIn + st.spoilOut;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'grade', value: atGrade + '/' + cells.length, ok: atGrade === cells.length },
      { axis: 'utility', value: String(st.strikes), ok: st.strikes === 0 },
      { axis: 'spoil', value: st.spoilIn + '/' + dumps, ok: st.spoilOut === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('excavator-trench', rows,
      atGrade === cells.length && st.strikes === 0 && st.spoilOut === 0);
  }
  return {
    group: g, orbit: true,
    mount: { parent: g, pos: [3.2, 0, 3.4], yaw: -.7 },
    action() {
      if (st.done) return;
      const tip = tipPos();
      if (!st.carrying) {
        const cell = cells.find((c) =>
          Math.hypot(tip.x - c.x, tip.z - c.z) < 1.1);
        if (cell && tip.y < .6 && cell.d < 2.5) {
          if (!st.t0) st.t0 = performance.now();
          cell.d += LAY.bite; st.carrying = true; spoilInBucket.visible = true;
          cellShade(cell);
          blip(180, 90, .18, 'sawtooth', .18);      // bite
          if (cell.util && cell.d > cell.target + .01 && !cell.struck) {
            cell.struck = true; st.strikes++;
            blip(980, 490, .6, 'square', .2);        // utility alarm
            buzz(320, .9);
          }
        }
      } else {
        st.carrying = false; spoilInBucket.visible = false;
        if (Math.hypot(tip.x - PAD.x, tip.z - PAD.z) < 1.9) st.spoilIn++;
        else st.spoilOut++;
        thud(); buzz(70, .3);
        pile.scale.setScalar(Math.min(1.6, .2 + st.spoilIn * .16));
        if (cells.every((c) => c.d >= c.target)) finish();
      }
    },
    update(dt) {
      if (st.done) return;
      const f = st.carrying ? LOADED : 1;
      const sr = .5, rr = 3.4 * f, hr = 2.6 * f;
      // house slew, stick and boom on the same spooling drive: a full
      // bucket does not start or stop where the lever does - and it swings
      // the boom out slower than an empty one does
      st.cS = drive(st.cS, axis(keys.KeyA, keys.KeyD), dt);
      st.cR = drive(st.cR, axis(keys.KeyS, keys.KeyW), dt);
      st.cB = drive(st.cB, axis(keys.KeyE, keys.KeyQ), dt);
      st.slew += sr * st.cS * dt;
      st.r = Math.max(2.6, Math.min(L1 + L2 - .6, st.r + rr * st.cR * dt));
      st.bh = Math.max(-2.4, Math.min(3.2, st.bh + hr * st.cB * dt));
      const moving = Math.abs(st.cS) * .4 + Math.abs(st.cR) * .4 + Math.abs(st.cB) * .5;
      st.act += (Math.min(1, moving) - st.act) * Math.min(1, 5 * dt);
      engineSet(.15 + st.act * .85);
      hg.rotation.y = -st.slew;
      // 2-link IK in the boom plane: reach r out, bucket height bh
      const py = PIV_Y;
      const dx = st.r, dy = st.bh - py;
      const d = Math.min(L1 + L2 - .05, Math.max(1.4, Math.hypot(dx, dy)));
      const base = Math.atan2(dy, dx);
      const cosA = Math.min(1, Math.max(-1,
        (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)));
      const cosB = Math.min(1, Math.max(-1,
        (L1 * L1 + L2 * L2 - d * d) / (2 * L1 * L2)));
      boomG.rotation.z = base + Math.acos(cosA);
      stickG.rotation.z = -(Math.PI - Math.acos(cosB));
      if (simView === 'cab') {
        const eye = hg.localToWorld(new THREE.Vector3(.8, 2.5, 1));
        const tip = tipPos();
        seatPose(eye.x, eye.y, eye.z, tip.x, Math.min(tip.y, .8), tip.z);
      }
    },
    gauges: () => ({
      slew: ((st.slew * 180 / Math.PI) % 360 + 360) % 360,
      reach: st.r,
      depth: st.bh,
      grade: { v: 0, txt: cells.filter((c) => Math.abs(c.d - c.target) < .01).length + '/' + cells.length },
      spoil: { v: st.spoilOut, txt: st.spoilIn + '/' + (st.spoilIn + st.spoilOut) },
      utility: { v: st.strikes, txt: String(st.strikes) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* --------------------------------------------------- forklift yard run --- */
function forkliftSim(P = {}) {
  const nGates = P.gates ?? 4, dockW = P.dock_w ?? 2.2;
  // the course geometry is the registry's layout - gate line, cone offset,
  // dock and start - read here and by the scripted operator that threads it
  const LAY = D.sims.sims['forklift-run'].layout, GL = LAY.gates;
  const laneEnd = -(GL.z0 - GL.pitch * nGates);   // the pallet waits one pitch past the last gate
  const yardHD = (laneEnd + 26) / 2;
  const g = new THREE.Group();
  simYard(g, 32, yardHD, 0, 16 - yardHD);
  const fl = new THREE.Group(); g.add(fl);
  box(1.6, 1.1, 2.6, mat.post, 0, .8, 0, fl);
  box(1.2, .9, 1.2, mat.win, 0, 1.75, -.3, fl);
  box(.15, 2.4, .15, mat.metal, -.55, 1.2, 1.4, fl);
  box(.15, 2.4, .15, mat.metal, .55, 1.2, 1.4, fl);
  const forks = new THREE.Group(); fl.add(forks);
  box(.18, .1, 1.5, mat.metal, -.4, .18, 2.2, forks);
  box(.18, .1, 1.5, mat.metal, .4, .18, 2.2, forks);
  for (const [wx, wz] of [[-.8, .9], [.8, .9], [-.8, -.9], [.8, -.9]]) {
    const w = new THREE.Mesh(new THREE.CylinderGeometry(.4, .4, .3, 14), mat.part);
    w.rotation.z = Math.PI / 2; w.position.set(wx, .4, wz);
    w.castShadow = true; fl.add(w);
  }
  // course: cone gates, pallet, dock — the gate count is the scenario's
  const GATES = Array.from({ length: nGates }, (_, i) =>
    [GL.side[i % GL.side.length] * GL.x, GL.z0 - GL.pitch * i, 0]);
  const cones = [], gates = [];
  GATES.forEach(([gx, gz], gi) => {
    const pair = [];
    for (const off of [-GL.cone_offset, GL.cone_offset]) {
      const c = new THREE.Mesh(new THREE.ConeGeometry(.32, .8, 12), mat.cone);
      c.position.set(gx + off, .4, gz); c.castShadow = true;
      g.add(c); cones.push(c); pair.push(c);
    }
    gates.push({ x: gx, z: gz, taken: false, pair });
  });
  const pallet = new THREE.Group(); g.add(pallet);
  box(1.2, .14, 1.2, mat.wood, 0, .07, 0, pallet);
  box(1, .7, 1, mat.brick, 0, .52, 0, pallet);
  pallet.position.set(0, 0, -laneEnd);
  const dock = new THREE.Mesh(new THREE.PlaneGeometry(dockW * 2 + .6, dockW * 2 + .6),
    new THREE.MeshBasicMaterial({ color: 0x41C4D4, transparent: true, opacity: .28 }));
  dock.rotation.x = -Math.PI / 2;
  dock.position.set(LAY.dock[0], .06, LAY.dock[1]); g.add(dock);
  const st = { v: 0, steer: 0, phi: Math.PI, carrying: false, done: false,
               hits: 0, t0: null, placed: false };
  fl.position.set(LAY.start[0], 0, LAY.start[1]); fl.rotation.y = st.phi;
  function finish(docked) {
    st.done = true;
    const taken = gates.filter(x => x.taken).length;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'gates', value: taken + '/' + gates.length, ok: taken === gates.length },
      { axis: 'cones', value: String(st.hits), ok: st.hits === 0 },
      { axis: 'docking', value: docked ? 'in the bay' : 'missed', ok: docked },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('forklift-run', rows,
      taken === gates.length && st.hits === 0 && docked);
  }
  return {
    group: g, orbit: false,
    mount: { parent: fl, pos: [0, .58, -.34], yaw: 0, seated: true },
    action() {
      if (st.done) return;
      const dir = new THREE.Vector3(Math.sin(st.phi), 0, Math.cos(st.phi));
      const tip = fl.position.clone().addScaledVector(dir, 2.4);
      if (!st.carrying) {
        if (Math.abs(st.v) < 1
          && tip.distanceTo(pallet.position) < 1.7) st.carrying = true;
      } else {
        st.carrying = false;
        pallet.position.set(tip.x, 0, tip.z);
        const inDock = Math.abs(pallet.position.x - dock.position.x) < dockW
          && Math.abs(pallet.position.z - dock.position.z) < dockW;
        finish(inDock);
      }
    },
    update(dt) {
      if (st.done) return;
      const acc = 5.5, drag = 1.6, vmax = 6;
      if (keys.KeyW || keys.ArrowUp) st.v += acc * dt;
      else if (keys.KeyS || keys.ArrowDown) st.v -= acc * dt;
      else st.v -= st.v * drag * dt;
      st.v = Math.max(-vmax / 2, Math.min(vmax, st.v));
      const target = (keys.KeyA || keys.ArrowLeft) ? .55
        : (keys.KeyD || keys.ArrowRight) ? -.55 : 0;
      st.steer += (target - st.steer) * Math.min(1, 8 * dt);
      if (Math.abs(st.v) > .05) {
        if (!st.t0) st.t0 = performance.now();
        st.phi += st.v / 2.2 * Math.tan(st.steer) * dt;
      }
      engineSet(Math.abs(st.v) / vmax);
      beeperSet(st.v < -.3);
      const dir = new THREE.Vector3(Math.sin(st.phi), 0, Math.cos(st.phi));
      fl.position.addScaledVector(dir, st.v * dt);
      fl.position.x = Math.max(-30, Math.min(30, fl.position.x));
      fl.position.z = Math.max(-(laneEnd + 8), Math.min(14, fl.position.z));
      fl.rotation.y = st.phi;
      if (st.carrying)
        pallet.position.copy(fl.position.clone().addScaledVector(dir, 2.4).setY(.35));
      // cones and gates
      for (const c of cones) {
        if (!c.userData.hit && c.position.distanceTo(fl.position) < 1.3) {
          c.userData.hit = true; c.rotation.z = 1.2; st.hits++;
          thud(); buzz(140);
        }
      }
      for (let gi = 0; gi < gates.length; gi++) {
        const gt = gates[gi];
        if (!gt.taken && (gi === 0 || gates[gi - 1].taken)
          && Math.hypot(fl.position.x - gt.x, fl.position.z - gt.z) < 2.4) {
          gt.taken = true;
          gt.pair.forEach((c) => { c.material = mat.steel; });
          blip(880, 1320, .18); buzz(60, .3);
        }
      }
      if (simView === 'driver') {
        // the seat: eye height over the chassis, sight line past the mast
        const eye = fl.position.clone().addScaledVector(dir, .5).setY(2.25);
        const at = eye.clone().addScaledVector(dir, 10).setY(1.7);
        seatPose(eye.x, eye.y, eye.z, at.x, at.y, at.z);
      } else {
        const camTo = fl.position.clone().addScaledVector(dir, -8.5).setY(5.2);
        const at = fl.position.clone().addScaledVector(dir, 4).setY(1.2);
        seatPose(camTo.x, camTo.y, camTo.z, at.x, at.y, at.z, Math.min(1, 5 * dt));
      }
    },
    gauges: () => ({
      speed: Math.abs(st.v) * 3.6,
      steer: st.steer * 180 / Math.PI,
      heading: ((st.phi * 180 / Math.PI) % 360 + 360) % 360,
      x: fl.position.x,
      z: fl.position.z,
      load: { v: st.carrying ? 1 : 0, txt: st.carrying ? '\\u25a0' : '\\u2013' },
      gates: { v: 0, txt: gates.filter(x => x.taken).length + '/' + gates.length },
      cones: { v: st.hits, txt: String(st.hits) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* ------------------------------------------------------ weld bead run ---- */
function weldSim(P = {}) {
  const SEGS = P.segs ?? 10, BAND = P.band ?? [2, 5];
  const SEG_W = .45, FUSE = .42, BURN = 1.5, TRAVEL = .5;
  const seamL = SEGS * SEG_W, x0 = -seamL / 2;
  const g = new THREE.Group();
  simYard(g, 16, 12);
  // the bench: two plates meeting at the marked seam, welding screens behind
  const topY = 1.02;
  box(seamL + 1.6, .1, 2.2, mat.steel, 0, topY - .05, 0, g);
  for (const lx of [-seamL / 2 - .5, seamL / 2 + .5])
    for (const lz of [-.8, .8]) box(.14, .95, .14, mat.part, lx, .48, lz, g);
  box(seamL + 1.2, .05, .9, mat.metal, 0, topY + .02, -.6, g);   // plates
  box(seamL + 1.2, .05, .9, mat.metal, 0, topY + .02, .6, g);
  box(seamL, .02, .1, mat.paint, 0, topY + .05, 0, g, false);    // seam mark
  for (const sx of [-seamL / 2 - 2.2, seamL / 2 + 2.2]) {        // screens
    const scr = new THREE.Mesh(boxGeo(.08, 1.9, 3.2),
      new THREE.MeshStandardMaterial({ color: 0x5a3021, roughness: .7,
        transparent: true, opacity: .85 }));
    scr.position.set(sx, 1.3, 0); g.add(scr);
  }
  // the seam, segment by segment: dark until fused, amber in band,
  // pale out of band, a scorched hole where it burned through
  const segs = Array.from({ length: SEGS }, (_, i) => {
    const m = new THREE.Mesh(boxGeo(SEG_W - .04, .05, .16),
      new THREE.MeshStandardMaterial({ color: 0x22282b, roughness: .8 }));
    m.position.set(x0 + (i + .5) * SEG_W, topY + .06, 0); g.add(m);
    return { x: x0 + (i + .5) * SEG_W, heat: 0, good: 0,
             fused: false, burned: false, inBand: null, mesh: m };
  });
  // the torch, and the arc that lives under it
  const torch = new THREE.Group(); g.add(torch);
  const noz = new THREE.Mesh(new THREE.CylinderGeometry(.05, .08, .5, 10), mat.part);
  noz.rotation.z = .5; noz.position.y = .3; torch.add(noz);
  box(.07, .3, .07, mat.post, .22, .62, 0, torch, false);
  const arcGlow = new THREE.Mesh(new THREE.SphereGeometry(.09, 10, 10),
    new THREE.MeshStandardMaterial({ color: 0xffffff,
      emissive: 0xbfe8ff, emissiveIntensity: 2.4 }));
  arcGlow.visible = false; torch.add(arcGlow);
  const st = { x: x0 - .3, gap: 3.5, arc: false, done: false,
               burns: 0, t0: null };
  const segAt = () => {
    const i = Math.floor((st.x - x0) / SEG_W);
    return i >= 0 && i < SEGS ? segs[i] : null;
  };
  const inBand = () => st.gap >= BAND[0] && st.gap <= BAND[1];
  /* Arc length IS heat input. A long arc spreads the heat and loses it to
     the air, so the seam is slow to fuse - lack of fusion is the classic
     long-arc defect. A tight one concentrates it and burns through sooner.
     Inside the band the bead runs at rate, which is why the band is the
     thing being taught: it was scored before this and now it is also felt.
     SCHEMATIC - the shape of the relationship, not a heat-input formula. */
  const ARC_HEAT = .12;                      // per mm of arc off the band's middle
  const heatRate = () => {
    const mid = (BAND[0] + BAND[1]) / 2;
    return Math.max(.45, Math.min(1.35, 1 + (mid - st.gap) * ARC_HEAT));
  };
  function paint(s) {
    s.mesh.material.color.setHex(
      s.burned ? 0x0c0e0f : s.inBand ? 0xE8A33D : 0xb9c2c6);
    if (s.burned) s.mesh.scale.y = .4;
  }
  function bandPct() {
    const fused = segs.filter((s) => s.fused);
    return fused.length
      ? Math.round(100 * fused.filter((s) => s.inBand).length / fused.length) : 0;
  }
  function finish() {
    st.done = true; st.arc = false; arcGlow.visible = false; engineSet(0);
    const fused = segs.filter((s) => s.fused).length;
    const pct = bandPct();
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'fusion', value: fused + '/' + SEGS, ok: fused === SEGS },
      { axis: 'band', value: pct + '%', ok: pct >= 90 },
      { axis: 'burns', value: String(st.burns), ok: st.burns === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('weld-bead', rows, fused === SEGS && pct >= 90 && st.burns === 0);
  }
  return {
    group: g, orbit: true,
    orbitCam: { pos: [5.5, 4.5, 8], tgt: [0, 1, 0] },
    mount: { parent: g, pos: [-1.4, 0, 1.7], yaw: Math.PI },
    action() {
      if (st.done) return;
      if (!st.arc) {
        if (st.gap <= 6) {
          st.arc = true;
          if (!st.t0) st.t0 = performance.now();
          blip(1400, 2600, .12, 'square', .08);           // strike
        }
      } else { st.arc = false; blip(900, 300, .1, 'square', .05); }
    },
    update(dt) {
      if (st.done) return;
      if (keys.KeyW) st.x = Math.min(x0 + seamL + .4, st.x + TRAVEL * dt);
      if (keys.KeyS) st.x = Math.max(x0 - .4, st.x - TRAVEL * dt);
      if (keys.KeyQ) st.gap = Math.min(7.5, st.gap + 4 * dt);
      if (keys.KeyE) st.gap = Math.max(.5, st.gap - 4 * dt);
      if (st.arc && st.gap > 6.2) {                       // too long: the arc pops out
        st.arc = false; blip(2200, 400, .2, 'square', .1);
      }
      const s = st.arc ? segAt() : null;
      if (s && !s.burned) {
        // both the heat and the in-band credit are weighted the same way, so
        // the band score reads as the share of HEAT laid down in the band
        const hr = heatRate() * dt;
        s.heat += hr;
        if (inBand()) s.good += hr;
        if (!s.fused && s.heat >= FUSE) {
          s.fused = true; s.inBand = s.good / s.heat >= .75; paint(s);
          if (segs.every((x) => x.fused || x.burned)) return finish();
        }
        if (s.heat >= BURN) {                             // lingered: burn-through
          s.burned = true; s.fused = false; s.inBand = null; st.burns++;
          paint(s); blip(240, 60, .5, 'sawtooth', .22); buzz(300, .9);
          if (segs.every((x) => x.fused || x.burned)) return finish();
        }
      }
      torch.position.set(st.x, topY + .12 + st.gap * .022, 0);
      arcGlow.visible = st.arc;
      if (st.arc) arcGlow.scale.setScalar(.8 + .5 * Math.abs(Math.sin(performance.now() / 37)));
      arcGlow.position.y = -.02 - st.gap * .02;
      engineSet(st.arc ? .55 + .25 * Math.random() : 0);  // crackle drive (audio only)
      if (simView === 'visor')
        seatPose(st.x - .7, topY + 1.15, 1.45, st.x + .2, topY + .05, 0);
    },
    gauges: () => {
      const s = segAt();
      return {
        gap: st.gap,
        heat: Math.min(100, ((s && !s.burned ? s.heat : 0) / BURN) * 100),
        seam: { v: 0, txt: segs.filter((x) => x.fused).length + '/' + SEGS },
        band: { v: 0, txt: bandPct() + '%' },
        burns: { v: st.burns, txt: String(st.burns) },
        time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
      };
    },
  };
}

/* --------------------------------------------------- scaffold bay build --- */
function scaffoldSim(P = {}) {
  const PLANKS = P.planks ?? 3, RAILS = P.rails ?? 2;
  const g = new THREE.Group();
  simYard(g, 13, 10);
  const railMat = new THREE.MeshStandardMaterial({ color: 0xd8a13a, roughness: .5 });
  const alu = new THREE.MeshStandardMaterial({ color: 0xa8b4b8,
    roughness: .45, metalness: .5 });
  const mk = (geo, m, x, y, z) => {
    const mesh = new THREE.Mesh(geo, m);
    mesh.position.set(x, y, z); mesh.castShadow = true;
    mesh.visible = false; g.add(mesh);
    return mesh;
  };
  // the bay's parts, all prebuilt and hidden - placing a part reveals it.
  // STAGE LAW: sills, frames, braces, planks, then rails, and the rack
  // refuses anything out of order.
  const parts = [];
  for (const [sx, sz] of [[-1.6, -.75], [-1.6, .75], [1.6, -.75], [1.6, .75]])
    parts.push({ stage: 0,
      mesh: mk(boxGeo(.5, .1, .5), mat.wood, sx, .1, sz) });
  for (const fx of [-1.6, 1.6]) {
    const fg = new THREE.Group(); fg.position.set(fx, 0, 0);
    fg.visible = false; g.add(fg);
    for (const pz of [-.75, .75]) {
      const post = new THREE.Mesh(new THREE.CylinderGeometry(.05, .05, 2.3, 8), alu);
      post.position.set(0, 1.3, pz); post.castShadow = true; fg.add(post);
    }
    for (const ry of [.6, 2]) {
      const rung = new THREE.Mesh(new THREE.CylinderGeometry(.04, .04, 1.5, 8), alu);
      rung.rotation.x = Math.PI / 2; rung.position.set(0, ry, 0); fg.add(rung);
    }
    parts.push({ stage: 1, mesh: fg });
  }
  for (const bz of [-.8, .8]) {
    const br = new THREE.Mesh(new THREE.CylinderGeometry(.035, .035, 3.7, 8), alu);
    br.rotation.z = Math.PI / 2 - .55; br.position.set(0, 1.3, bz);
    br.castShadow = true; br.visible = false; g.add(br);
    parts.push({ stage: 2, mesh: br });
  }
  for (let i = 0; i < PLANKS; i++) {
    const pz = -((PLANKS - 1) / 2) * .55 + i * .55;
    parts.push({ stage: 3,
      mesh: mk(boxGeo(3.4, .08, .5), mat.wood, 0, 2.14, pz) });
  }
  for (let i = 0; i < RAILS; i++) {
    const side = i % 2 ? .85 : -.85, ry = 2.65 + Math.floor(i / 2) * .4;
    parts.push({ stage: 4,
      mesh: mk(boxGeo(3.4, .07, .07), railMat, 0, ry, side) });
  }
  const STAGES = ['sills', 'frames', 'braces', 'planks', 'rails'];
  // the ghost previews where the selected rack's next part will land
  const ghost = new THREE.Mesh(boxGeo(1, 1, 1),
    new THREE.MeshBasicMaterial({ color: 0x41C4D4, transparent: true,
      opacity: .28, depthWrite: false }));
  ghost.visible = false; g.add(ghost);
  const gBox = new THREE.Box3(), gSize = new THREE.Vector3(), gMid = new THREE.Vector3();
  let gLast = null;   // the ghost target never moves once placed - recompute its box only when it changes, not every frame
  const st = { rack: 0, faults: 0, t0: null, done: false, la: false, ld: false, lr: false };
  const nextOf = (stage) => parts.find((p) => p.stage === stage && !p.mesh.visible);
  const legal = () => { for (let i = 0; i < 5; i++) if (nextOf(i)) return i; return -1; };
  function finish() {
    st.done = true; ghost.visible = false;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'sequence', value: String(st.faults), ok: st.faults === 0 },
      { axis: 'complete', value: parts.length + '/' + parts.length, ok: true },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('scaffold-bay', rows, st.faults === 0);
  }
  return {
    group: g, orbit: true,
    orbitCam: { pos: [6, 4.5, 8.5], tgt: [0, 1.6, 0] },
    mount: { parent: g, pos: [2.4, 0, 1.8], yaw: -2.4 },
    action() {
      if (st.done) return;
      const lg = legal();
      if (lg < 0) return;
      if (st.rack !== lg) {                       // out of order: refused
        st.faults++;
        blip(150, 75, .32, 'square', .18); buzz(220, .8);
        return;
      }
      const p = nextOf(lg);
      p.mesh.visible = true;
      if (!st.t0) st.t0 = performance.now();
      blip(1250, 720, .07, 'triangle', .1);       // lock click
      if (!parts.some((x) => !x.mesh.visible)) finish();
    },
    update(dt) {
      if (st.done) return;
      // rack selection steps on the key edge, not the hold
      if (keys.KeyA && !st.la) st.rack = (st.rack + 4) % 5;
      if (keys.KeyD && !st.ld) st.rack = (st.rack + 1) % 5;
      if (keys.KeyR && !st.lr && legal() >= 0) st.rack = legal();
      st.la = !!keys.KeyA; st.ld = !!keys.KeyD; st.lr = !!keys.KeyR;
      engineSet(.06);
      const nx = nextOf(st.rack);
      if (nx) {
        if (nx !== gLast) {
          gLast = nx;
          gBox.setFromObject(nx.mesh);
          gBox.getSize(gSize); gBox.getCenter(gMid);
          ghost.position.copy(gMid);
          ghost.scale.set(Math.max(.12, gSize.x), Math.max(.12, gSize.y),
            Math.max(.12, gSize.z));
        }
        ghost.visible = true;
      } else { gLast = null; ghost.visible = false; }
      if (simView === 'deck') seatPose(2.7, 3.05, 0, -1.6, 2.1, 0);
    },
    gauges: () => ({
      rack: { v: 0, txt: STAGES[st.rack] },
      stage: { v: 0, txt: legal() < 0 ? '\\u2013' : STAGES[legal()] },
      placed: { v: 0, txt: parts.filter((p) => p.mesh.visible).length + '/' + parts.length },
      faults: { v: st.faults, txt: String(st.faults) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* ------------------------------------------------- rigging signal call --- */
function riggingSim(P = {}) {
  const SEQ = P.seq ?? ['up', 'swing-r', 'out', 'down', 'stop'];
  const g = new THREE.Group();
  simYard(g, 18, 14);
  // a yard derrick: mast, slewing boom, trolley line, hook and load -
  // it moves ONLY on a correct call from the signalperson
  const MAST = 9;
  box(.8, MAST, .8, mat.metal, -4, MAST / 2, -3, g);
  const slewG = new THREE.Group(); slewG.position.set(-4, MAST, -3); g.add(slewG);
  box(10, .5, .6, mat.post, 5, 0, 0, slewG);
  box(3, .5, .6, mat.metal, -1.5, 0, 0, slewG);
  const cableGeo = new THREE.BufferGeometry().setFromPoints(
    [new THREE.Vector3(), new THREE.Vector3()]);
  g.add(new THREE.Line(cableGeo, new THREE.LineBasicMaterial({ color: 0xd8dde0 })));
  const load = box(1.6, 1.2, 1.6, mat.brick, 0, .6, 0, g);
  // the signal pad, painted where the operator can see the hands
  const pad = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.1, .08, 24),
    new THREE.MeshBasicMaterial({ color: 0xE8A33D, transparent: true, opacity: .35 }));
  pad.position.set(4.5, .06, 6.2); g.add(pad);
  const st = { i: 0, wrong: 0, t0: null, done: false, given: '\\u2013',
               slew: .55, r: 5.5, h: 3.2, latch: {},
               tgt: null };
  const hookPos = () => {
    const tip = slewG.localToWorld(new THREE.Vector3(st.r, 0, 0));
    return new THREE.Vector3(tip.x, st.h, tip.z);
  };
  function finish() {
    st.done = true;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'calls', value: st.i + '/' + SEQ.length, ok: st.i === SEQ.length },
      { axis: 'wrong', value: String(st.wrong), ok: st.wrong === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('rigging-signals', rows, st.i === SEQ.length && st.wrong === 0);
  }
  function give(sig) {
    if (st.done || st.tgt) return;         // the crane is still moving: hold
    st.given = sig;
    if (sig === SEQ[st.i]) {
      if (!st.t0) st.t0 = performance.now();
      blip(1450, 1900, .1, 'sine', .12);   // the whistle: call acknowledged
      setTimeout(() => blip(1450, 1900, .1, 'sine', .12), 140);
      st.i++;
      if (sig === 'stop') return finish();
      st.tgt = {
        'up': { h: st.h + 2.4 }, 'down': { h: Math.max(1.2, st.h - 2.4) },
        'swing-l': { slew: st.slew - .55 }, 'swing-r': { slew: st.slew + .55 },
        'out': { r: Math.min(9, st.r + 2.2) }, 'in': { r: Math.max(2.5, st.r - 2.2) },
      }[sig];
    } else {                               // out of turn: the crane holds
      st.wrong++;
      blip(220, 110, .35, 'square', .16); buzz(200, .7);
    }
  }
  return {
    group: g, orbit: true,
    orbitCam: { pos: [12, 9, 15], tgt: [0, 4, 0] },
    mount: { parent: g, pos: [4.5, .1, 6.2], yaw: -2.55, armUp: true },
    action() { give('stop'); },
    update(dt) {
      if (!st.done) {
        const SIGS = { KeyQ: 'up', KeyE: 'down', KeyA: 'swing-l',
                       KeyD: 'swing-r', KeyW: 'out', KeyS: 'in' };
        for (const [k, sig] of Object.entries(SIGS)) {
          if (keys[k] && !st.latch[k]) give(sig);
          st.latch[k] = !!keys[k];
        }
        if (st.tgt) {                      // one smooth move per call
          let close = true;
          for (const [prop, want] of Object.entries(st.tgt)) {
            st[prop] += (want - st[prop]) * Math.min(1, 3.2 * dt);
            if (Math.abs(want - st[prop]) > .04) close = false;
          }
          if (close) { Object.assign(st, st.tgt); st.tgt = null; }
        }
        engineSet(st.tgt ? .6 : .12);
      }
      slewG.rotation.y = -st.slew;
      const hp = hookPos();
      load.position.set(hp.x, Math.max(.6, hp.y - 1.4), hp.z);
      const pts = cableGeo.attributes.position.array;
      const tip = slewG.localToWorld(new THREE.Vector3(st.r, 0, 0));
      pts[0] = tip.x; pts[1] = tip.y; pts[2] = tip.z;
      pts[3] = load.position.x; pts[4] = load.position.y + .6; pts[5] = load.position.z;
      cableGeo.attributes.position.needsUpdate = true;
      if (simView === 'signal') {
        // the signalperson's eye: on the pad, watching the load
        seatPose(4.5, 1.75, 7.1, load.position.x, load.position.y + 1, load.position.z);
      }
    },
    gauges: () => ({
      step: { v: 0, txt: st.i + '/' + SEQ.length },
      called: { v: 0, txt: st.done ? '\\u2013' : (SEQ[st.i] ?? '\\u2013') },
      given: { v: 0, txt: st.given },
      wrong: { v: st.wrong, txt: String(st.wrong) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* ------------------------------------------------- load chart judgment --- */
function loadChartSim(P = {}) {
  const CHART = D.sims.sims['load-chart'].chart;
  const cap = Object.fromEntries(CHART);
  const PICKS = P.picks ?? [{ w: 3, r: 4 }, { w: 4.8, r: 6 }, { w: 4.1, r: 8 }];
  const g = new THREE.Group();
  simYard(g, 18, 14);
  // the crane whose chart it is: mast and a fixed boom over the pick line
  const MAST = 9;
  box(.8, MAST, .8, mat.metal, -6, MAST / 2, -4, g);
  box(14, .5, .6, mat.post, 1, MAST, -4, g);
  // the pick line: a painted tick at every chart radius
  for (const [r] of CHART) {
    box(.18, .04, 1.2, mat.paint, -6 + r, .06, -4, g, false);
  }
  // the chart board - one honest number per radius, drawn as data
  const cc = document.createElement('canvas'); cc.width = 256; cc.height = 320;
  const cx2 = cc.getContext('2d');
  const ctex = new THREE.CanvasTexture(cc);
  function drawChart(hi) {
    cx2.fillStyle = '#0C1113'; cx2.fillRect(0, 0, 256, 320);
    cx2.strokeStyle = '#E8A33D'; cx2.lineWidth = 6; cx2.strokeRect(3, 3, 250, 314);
    cx2.fillStyle = '#E8EDEC'; cx2.font = '700 30px "Barlow Condensed", sans-serif';
    cx2.fillText('LOAD CHART', 42, 44);
    cx2.font = '26px "IBM Plex Mono", monospace';
    CHART.forEach(([r, t2], i) => {
      const y = 92 + i * 44;
      if (i === hi) { cx2.fillStyle = 'rgba(232,163,61,.28)'; cx2.fillRect(10, y - 30, 236, 40); }
      cx2.fillStyle = i === hi ? '#E8A33D' : '#93A3A6';
      cx2.fillText(String(r).padStart(2) + ' m', 26, y);
      cx2.fillStyle = '#E8EDEC';
      cx2.fillText(t2.toFixed(1) + ' t', 140, y);
    });
    ctex.needsUpdate = true;
  }
  drawChart(-1);
  const board = new THREE.Mesh(new THREE.PlaneGeometry(2.6, 3.25),
    new THREE.MeshBasicMaterial({ map: ctex }));
  board.position.set(4, 2.1, 3); board.rotation.y = -.5; g.add(board);
  box(.14, 2.2, .14, mat.part, 3.2, 1.1, 3.4, g);
  box(.14, 2.2, .14, mat.part, 4.8, 1.1, 2.6, g);
  // `respawn` is sim time, not a wall-clock timer, so the next pick lands
  // the same number of steps after a judgment under any drive - the frame
  // loop or the scripted operator's fixed-step sweep
  const st = { i: 0, errs: 0, over: 0, t0: null, done: false, hi: -1,
               lq: false, le: false, lx: false, respawn: 0 };
  let loadMesh = null, loadLab = null;
  const anims = [];
  function spawn() {
    if (st.done) return;
    if (st.i >= PICKS.length) return finish();
    const p = PICKS[st.i];
    const s2 = .7 + p.w * .13;
    loadMesh = box(s2, s2 * .8, s2, mat.brick, -6 + p.r, s2 * .4, -4, g);
    loadLab = label(p.w.toFixed(1) + ' t', p.r + ' m radius', .55,
      { kind: 'readout' });
    loadLab.position.set(-6 + p.r, s2 * .8 + 1.2, -4); g.add(loadLab);
  }
  spawn();
  function finish() {
    st.done = true;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'judgments', value: (PICKS.length - st.errs) + '/' + PICKS.length,
        ok: st.errs === 0 },
      { axis: 'overloads', value: String(st.over), ok: st.over === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('load-chart', rows, st.errs === 0);
  }
  function judge(accept) {
    if (st.done || !loadMesh) return;
    const p = PICKS[st.i];
    const legal = p.w <= cap[p.r];
    if (!st.t0) st.t0 = performance.now();
    const m = loadMesh, lb = loadLab;
    loadMesh = null; loadLab = null;
    if (accept === legal) {
      if (accept) { blip(1100, 1500, .12, 'triangle', .12); anims.push({ m, lb, up: true }); }
      else { blip(700, 500, .15, 'triangle', .1); anims.push({ m, lb, up: false }); }
    } else {
      st.errs++;
      anims.push({ m, lb, up: false });
      if (accept) {                          // an overweight pick accepted
        st.over++;
        blip(240, 90, .6, 'sawtooth', .22); buzz(320, .9);
      } else { blip(300, 200, .3, 'square', .12); buzz(120, .4); }
    }
    st.i++;
    st.respawn = .65;
  }
  return {
    group: g, orbit: true,
    orbitCam: { pos: [10, 7, 13], tgt: [0, 2.5, 0] },
    mount: { parent: g, pos: [2.4, 0, 4.6], yaw: 2.5 },
    action() { judge(true); },
    update(dt) {
      if (!st.done) {
        if (st.respawn > 0) {
          st.respawn -= dt;
          if (st.respawn <= 0) { st.respawn = 0; spawn(); }
        }
        if (keys.KeyX && !st.lx) judge(false);
        st.lx = !!keys.KeyX;
        if (keys.KeyQ && !st.lq) { st.hi = (st.hi + CHART.length) % CHART.length; drawChart(st.hi); }
        if (keys.KeyE && !st.le) { st.hi = (st.hi + 1) % CHART.length; drawChart(st.hi); }
        st.lq = !!keys.KeyQ; st.le = !!keys.KeyE;
        engineSet(anims.some((a) => a.up) ? .5 : .1);
      }
      for (let i = anims.length - 1; i >= 0; i--) {
        const a = anims[i];
        if (a.up) a.m.position.y += 2.6 * dt;
        else a.m.position.z -= 2.6 * dt;
        a.lb.position.copy(a.m.position).y += 1.4;
        if (a.m.position.y > 6.5 || a.m.position.z < -9) {
          // freed here, at removal, rather than waiting on a teardown that
          // may be minutes away if this run keeps going: disposeOf() drops
          // the sign from labelSet and releases its (shared) texture
          g.remove(a.m); g.remove(a.lb);
          disposeOf(a.lb);
          anims.splice(i, 1);
        }
      }
      if (simView === 'chart')
        seatPose(2.7, 2.15, 4.9, board.position.x, board.position.y, board.position.z);
    },
    gauges: () => {
      const p = PICKS[Math.min(st.i, PICKS.length - 1)];
      return {
        pick: { v: 0, txt: Math.min(st.i, PICKS.length) + '/' + PICKS.length },
        load: p.w,
        radius: p.r,
        chart: cap[p.r],
        errors: { v: st.errs, txt: String(st.errs) },
        time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
      };
    },
  };
}

/* ----------------------------------------- pressure washer surface clean --- */
function pressureWasherSim(P = {}) {
  // the cell size and standoff window are the registry's layout - read
  // here and by the scripted operator that sweeps the same grid
  const LAY = D.sims.sims['pressure-washer'].layout;
  const COLS = P.cols ?? 6, ROWS = P.rows ?? 4, CELL = LAY.cell;
  const panelW = COLS * CELL, panelH = ROWS * CELL, x0 = -panelW / 2;
  const g = new THREE.Group();
  simYard(g, 14, 11);
  // the fouled test panel, upright and facing the yard
  box(panelW + .3, panelH + .3, .1, mat.metal, 0, panelH / 2 + .4, -.06, g);
  const FOUL = 0x5b4a30, CLEAN = 0xaeb8ba, SCORCH = 0x241c14;
  const cells = [];
  for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
    const cx = x0 + (c + .5) * CELL, cy = (r + .5) * CELL + .4;
    const m = new THREE.Mesh(boxGeo(CELL - .05, CELL - .05, .05),
      new THREE.MeshStandardMaterial({ color: FOUL, roughness: .95 }));
    m.position.set(cx, cy, .01); g.add(m);
    cells.push({ expose: 0, bad: 0, clean: false, damaged: false, mesh: m });
  }
  // the containment berm - not shown until deployed, a habit the run checks
  const berm = box(panelW + 1, .28, .5, mat.paint, 0, .14, 1.3, g, false);
  berm.visible = false;
  // the wand: a hand tool standing off the panel along Z
  const wand = new THREE.Group(); g.add(wand);
  box(.1, .1, .5, mat.part, 0, 0, .2, wand, false);
  box(.08, .08, .28, mat.metal, 0, 0, -.14, wand, false);
  const jet = new THREE.Mesh(new THREE.SphereGeometry(.09, 10, 10),
    new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0x9fd8ff,
      emissiveIntensity: 2.2 }));
  jet.position.set(0, 0, -.3); jet.visible = false; wand.add(jet);
  const EFF_MAX = LAY.standoff.effective_max, DAMAGE_GAP = LAY.standoff.damage_under;
  const CLEAN_DWELL = .55, DAMAGE_DWELL = .9;
  const st = { u: 0, v: panelH / 2, gap: 1.0, spray: false, done: false,
               damage: 0, containSet: false, containOk: null, t0: null, lc: false };
  const cellAt = () => {
    const c = Math.floor((st.u - x0) / CELL), r = Math.floor(st.v / CELL);
    return c >= 0 && c < COLS && r >= 0 && r < ROWS ? cells[r * COLS + c] : null;
  };
  function paint(c) {
    c.mesh.material.color.setHex(c.damaged ? SCORCH : c.clean ? CLEAN : FOUL);
    if (c.damaged) c.mesh.scale.z = .3;
  }
  function finish() {
    st.done = true; st.spray = false; jet.visible = false; engineSet(0);
    const cleaned = cells.filter((c) => c.clean).length;
    const pct = Math.round(100 * cleaned / cells.length);
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'coverage', value: pct + '%', ok: pct >= 95 },
      { axis: 'damage', value: String(st.damage), ok: st.damage === 0 },
      { axis: 'containment', value: st.containOk ? 'set before spray' : 'set late or never',
        ok: !!st.containOk },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('pressure-washer', rows,
      pct >= 95 && st.damage === 0 && !!st.containOk);
  }
  return {
    group: g, orbit: true,
    orbitCam: { pos: [5, 4, 7.5], tgt: [0, panelH / 2, 0] },
    mount: { parent: g, pos: [-panelW / 2 - 1.4, 0, 1.4], yaw: -.5 },
    action() {
      if (st.done) return;
      st.spray = !st.spray;
      if (st.spray) {
        if (st.containOk === null) st.containOk = st.containSet;
        if (!st.t0) st.t0 = performance.now();
        blip(220, 340, .14, 'sawtooth', .06);
      } else blip(340, 180, .1, 'sawtooth', .05);
    },
    update(dt) {
      if (st.done) return;
      const SPD = .95;
      if (keys.KeyA) st.u = Math.max(x0, st.u - SPD * dt);
      if (keys.KeyD) st.u = Math.min(x0 + panelW, st.u + SPD * dt);
      if (keys.KeyW) st.v = Math.min(panelH, st.v + SPD * dt);
      if (keys.KeyS) st.v = Math.max(0, st.v - SPD * dt);
      if (keys.KeyQ) st.gap = Math.min(3.2, st.gap + 2.2 * dt);
      if (keys.KeyE) st.gap = Math.max(.2, st.gap - 2.2 * dt);
      if (keys.KeyC && !st.lc) {
        st.containSet = !st.containSet; berm.visible = st.containSet;
        blip(st.containSet ? 500 : 300, st.containSet ? 800 : 200, .12, 'triangle', .1);
      }
      st.lc = !!keys.KeyC;
      const cell = st.spray ? cellAt() : null;
      if (cell && !cell.damaged) {
        if (st.gap <= EFF_MAX) {
          cell.expose += dt;
          if (!cell.clean && cell.expose >= CLEAN_DWELL) { cell.clean = true; paint(cell); }
        }
        if (st.gap <= DAMAGE_GAP) {
          cell.bad += dt;
          if (cell.bad >= DAMAGE_DWELL) {
            cell.damaged = true; cell.clean = false; st.damage++; paint(cell);
            blip(240, 60, .5, 'sawtooth', .22); buzz(300, .9);
          }
        }
        if (cells.every((c) => c.clean || c.damaged)) return finish();
      }
      engineSet(st.spray ? .6 : .1);
      wand.position.set(st.u, st.v + .4, st.gap);
      jet.visible = st.spray;
      if (jet.visible) jet.scale.setScalar(.8 + .4 * Math.abs(Math.sin(performance.now() / 45)));
      if (simView === 'wand')
        seatPose(st.u - .3, st.v + .55, st.gap + .5, st.u, st.v + .4, -.06);
    },
    gauges: () => ({
      u: st.u,
      v: st.v,
      gap: st.gap,
      coverage: { v: 0, txt: Math.round(100 * cells.filter((c) => c.clean).length / cells.length) + '%' },
      damage: { v: st.damage, txt: String(st.damage) },
      containment: { v: 0, txt: st.containSet ? '\\u2713' : '\\u2013' },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* --------------------------------------------- airless paint sprayer finish --- */
function paintSprayerSim(P = {}) {
  // cell size, masked margin and standoff window: the registry's layout,
  // shared with the scripted operator exactly as the washer bench's is
  const LAY = D.sims.sims['airless-sprayer'].layout;
  const COLS = P.cols ?? 6, ROWS = P.rows ?? 4, CELL = LAY.cell;
  const panelW = COLS * CELL, panelH = ROWS * CELL, x0 = -panelW / 2, MASK = LAY.mask;
  const g = new THREE.Group();
  simYard(g, 14, 11);
  // the wall, oversized so a masked boundary sits inside its own face
  box(panelW + MASK * 2 + .3, panelH + MASK * 2 + .3, .1, mat.wall,
    0, panelH / 2 + .4, -.06, g);
  // masking tape traced exactly at the paintable boundary
  box(panelW + .06, .04, .04, mat.paint, 0, .4, .02, g, false);
  box(panelW + .06, .04, .04, mat.paint, 0, panelH + .4, .02, g, false);
  box(.04, panelH + .06, .04, mat.paint, x0, panelH / 2 + .4, .02, g, false);
  box(.04, panelH + .06, .04, mat.paint, x0 + panelW, panelH / 2 + .4, .02, g, false);
  const BASE = 0x8a8f8f, COAT = 0xE8A33D, RUN = 0x7a4a12;
  const cells = [];
  for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
    const cx = x0 + (c + .5) * CELL, cy = (r + .5) * CELL + .4;
    const m = new THREE.Mesh(boxGeo(CELL - .05, CELL - .05, .05),
      new THREE.MeshStandardMaterial({ color: BASE, roughness: .85 }));
    m.position.set(cx, cy, .01); g.add(m);
    cells.push({ expose: 0, bad: 0, coated: false, run: false, mesh: m });
  }
  // the gun: a hand tool standing off the wall along Z
  const gun = new THREE.Group(); g.add(gun);
  box(.1, .1, .5, mat.part, 0, 0, .2, gun, false);
  box(.08, .08, .28, mat.metal, 0, 0, -.14, gun, false);
  const jet = new THREE.Mesh(new THREE.SphereGeometry(.09, 10, 10),
    new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xE8A33D,
      emissiveIntensity: 2 }));
  jet.position.set(0, 0, -.3); jet.visible = false; gun.add(jet);
  const EFF_MAX = LAY.standoff.effective_max, RUN_GAP = LAY.standoff.damage_under;
  const COAT_DWELL = .5, RUN_DWELL = .9;
  const st = { u: 0, v: panelH / 2, gap: 1.0, spray: false, done: false,
               runs: 0, overspray: 0, inOver: false, t0: null };
  const cellAt = () => {
    const c = Math.floor((st.u - x0) / CELL), r = Math.floor(st.v / CELL);
    return c >= 0 && c < COLS && r >= 0 && r < ROWS ? cells[r * COLS + c] : null;
  };
  function paint(c) {
    c.mesh.material.color.setHex(c.run ? RUN : c.coated ? COAT : BASE);
  }
  function finish() {
    st.done = true; st.spray = false; jet.visible = false; engineSet(0);
    const coated = cells.filter((c) => c.coated).length;
    const pct = Math.round(100 * coated / cells.length);
    const holidays = cells.length - coated;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'coverage', value: pct + '%', ok: pct >= 95 },
      { axis: 'runs', value: String(st.runs), ok: st.runs === 0 },
      { axis: 'holidays', value: String(holidays), ok: holidays === 0 },
      { axis: 'overspray', value: String(st.overspray), ok: st.overspray === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('airless-sprayer', rows,
      pct >= 95 && st.runs === 0 && holidays === 0 && st.overspray === 0);
  }
  return {
    group: g, orbit: true,
    orbitCam: { pos: [5, 4, 7.5], tgt: [0, panelH / 2, 0] },
    mount: { parent: g, pos: [-panelW / 2 - 1.4, 0, 1.4], yaw: -.5 },
    action() {
      if (st.done) return;
      st.spray = !st.spray;
      if (st.spray) {
        if (!st.t0) st.t0 = performance.now();
        blip(260, 420, .12, 'sawtooth', .07);
      } else blip(340, 180, .1, 'sawtooth', .05);
    },
    update(dt) {
      if (st.done) return;
      const SPD = .95;
      if (keys.KeyA) st.u = Math.max(x0 - MASK - .3, st.u - SPD * dt);
      if (keys.KeyD) st.u = Math.min(x0 + panelW + MASK + .3, st.u + SPD * dt);
      if (keys.KeyW) st.v = Math.min(panelH + MASK, st.v + SPD * dt);
      if (keys.KeyS) st.v = Math.max(-MASK, st.v - SPD * dt);
      if (keys.KeyQ) st.gap = Math.min(3.2, st.gap + 2.2 * dt);
      if (keys.KeyE) st.gap = Math.max(.2, st.gap - 2.2 * dt);
      const outMask = st.u < x0 - .02 || st.u > x0 + panelW + .02
        || st.v < .02 || st.v > panelH - .02;
      if (st.spray && outMask && !st.inOver) {
        st.inOver = true; st.overspray++;
        blip(180, 90, .3, 'square', .16); buzz(180, .6);
      }
      if (!st.spray || !outMask) st.inOver = false;
      const cell = st.spray && !outMask ? cellAt() : null;
      if (cell && !cell.run) {
        if (st.gap <= EFF_MAX) {
          cell.expose += dt;
          if (!cell.coated && cell.expose >= COAT_DWELL) { cell.coated = true; paint(cell); }
        }
        if (st.gap <= RUN_GAP) {
          cell.bad += dt;
          if (cell.bad >= RUN_DWELL) {
            cell.run = true; cell.coated = true; st.runs++; paint(cell);
            blip(200, 70, .4, 'sawtooth', .18); buzz(260, .7);
          }
        }
        if (cells.every((c) => c.coated)) return finish();
      }
      engineSet(st.spray ? .6 : .1);
      gun.position.set(st.u, st.v + .4, st.gap);
      jet.visible = st.spray;
      if (jet.visible) jet.scale.setScalar(.8 + .4 * Math.abs(Math.sin(performance.now() / 45)));
      if (simView === 'spray')
        seatPose(st.u - .3, st.v + .55, st.gap + .5, st.u, st.v + .4, -.06);
    },
    gauges: () => ({
      u: st.u,
      v: st.v,
      gap: st.gap,
      coverage: { v: 0, txt: Math.round(100 * cells.filter((c) => c.coated).length / cells.length) + '%' },
      runs: { v: st.runs, txt: String(st.runs) },
      holidays: { v: 0, txt: String(cells.filter((c) => !c.coated).length) },
      overspray: { v: st.overspray, txt: String(st.overspray) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* ------------------------------------------ scripted reference operator
   Every seat can be driven by a scripted reference operator: one policy
   per sim, a deterministic function of the seat's own gauges() readout
   (the same numbers the dash shows - nothing the sim keeps private), the
   scenario's params, the seat's declared layout and a level, plus a small
   per-run scratch memory (which procedure step it is on) and a fixed-seed
   generator the degraded levels draw their slips from. No model, no
   network, no Math.random anywhere below. Each policy is written as a
   switch over the procedure step ids the sims registry declares for that
   seat, in that order, so the Operator advisor's `seat.procedure` answer
   IS this code's outline. At `optimal` it passes every pass-gated axis on
   every regional scenario - opSweep() below is how the build proves it.
   Its runs are SCRIPTED episodes (D.sims.operatorHonesty): the operator's
   own record, never the learner's. Inputs land in the same `keys` object
   a keyboard fills and the same sim.action() Space calls, so the seat
   cannot tell the two apart - which is the point. */
/* ---------------------------------------------------- boom lift basket ----
   An aerial work platform: a turret on a chassis on the level pad, a
   two-stage boom, a railed basket. Schematic kinematics - swing, boom
   elevation, extension - with one honest envelope: outreach x platform
   load against the rated moment the registry's layout declares. The
   overhead line, where a scenario has one, is an exclusion cylinder the
   basket must never enter. Tie-off and stabilizers are latched facts:
   set before the basket first leaves the ground, or late. */
function boomLiftSim(P = {}) {
  const LAY = D.sims.sims['boom-lift'].layout;
  const PTS = P.points ?? [[-3.5, 7, 7], [0, 7, 7], [3.5, 7, 7]];
  const LINE = P.line ?? null;
  const g = new THREE.Group();
  simYard(g, 22, 18);
  const PIV = LAY.pivot_y, L0 = LAY.boom_min, L1 = LAY.boom_max, EXT = L1 - L0;
  const EL_MAX = LAY.elev_max_deg * Math.PI / 180;
  const MAX_OUT = LAY.rated_moment / LAY.load_kg;
  // the pad, the chassis and its wheels, four stabilizer feet (down = set)
  box(6.4, .12, 4.4, mat.slab, 0, .06, 0, g, false);
  box(2.6, .9, 1.7, mat.post, 0, .75, 0, g);
  for (const [wx, wz] of [[-1.05, .95], [1.05, .95], [-1.05, -.95], [1.05, -.95]]) {
    const w = new THREE.Mesh(new THREE.CylinderGeometry(.42, .42, .32, 14), mat.part);
    w.rotation.x = Math.PI / 2; w.position.set(wx, .42, wz); w.castShadow = true; g.add(w);
  }
  const feet = [[-2.1, 1.5], [2.1, 1.5], [-2.1, -1.5], [2.1, -1.5]].map(([fx, fz]) => {
    box(1.3, .14, .14, mat.metal, fx / 2, 1.0, fz, g);            // the outrigger arm
    const leg = box(.14, .9, .14, mat.metal, fx, 1.05, fz, g);     // the leg: drops when set
    box(.5, .08, .5, mat.part, fx, .12, fz, g, false);
    return leg;
  });
  const turret = new THREE.Group(); turret.position.y = PIV; g.add(turret);
  box(1.6, .7, 1.5, mat.part, 0, -.3, 0, turret);
  const boomG = new THREE.Group(); turret.add(boomG);
  box(L0, .44, .44, mat.metal, L0 / 2, 0, 0, boomG);
  const stage = box(EXT, .32, .32, mat.metal, L0 - EXT / 2, 0, 0, boomG);
  const basketG = new THREE.Group(); boomG.add(basketG);   // counter-rotates: hangs level
  box(1.8, .1, .9, mat.part, 0, -.55, 0, basketG);
  for (const [bx, bz] of [[-.85, -.4], [.85, -.4], [-.85, .4], [.85, .4]])
    box(.05, 1.1, .05, mat.post, bx, 0, bz, basketG, false);
  box(1.8, .05, .05, mat.post, 0, .5, -.4, basketG, false);
  box(1.8, .05, .05, mat.post, 0, .5, .4, basketG, false);
  box(.05, .05, .9, mat.post, -.85, .5, 0, basketG, false);
  box(.05, .05, .9, mat.post, .85, .5, 0, basketG, false);
  const anchor = box(.12, .12, .12, mat.steel, 0, .35, 0, basketG, false);
  // the work: a wall bay behind the points, one marker per point, in order
  const wz = Math.max(...PTS.map((p) => p[2])) + .9;
  box(18, 13, .6, mat.wall, 0, 6.5, wz, g);
  const markMat = () => new THREE.MeshStandardMaterial({
    color: 0xE8A33D, emissive: 0x7a4d08, roughness: .5 });
  const marks = PTS.map(([px, py, pz], i) => {
    const m = box(.5, .5, .12, markMat(), px, py, wz - .36, g, false);
    m.userData.i = i; return m;
  });
  // the overhead line and its exclusion zone, drawn as what they are
  let zone = null;
  if (LINE) {
    for (const px of [-14, 14]) box(.3, LINE.y + .4, .3, mat.metal, px, (LINE.y + .4) / 2, LINE.z, g);
    const wire = new THREE.Mesh(new THREE.CylinderGeometry(.05, .05, 28, 8), mat.part);
    wire.rotation.z = Math.PI / 2; wire.position.set(0, LINE.y, LINE.z); g.add(wire);
    zone = new THREE.Mesh(new THREE.CylinderGeometry(LINE.r, LINE.r, 28, 20, 1, true),
      new THREE.MeshBasicMaterial({ color: 0xE07C68, transparent: true, opacity: .16,
        side: THREE.DoubleSide, depthWrite: false }));
    zone.rotation.z = Math.PI / 2; zone.position.set(0, LINE.y, LINE.z); g.add(zone);
  }
  const st = { sw: 0, el: 0, ext: 0, stab: false, tied: false, lifted: false,
               cS: 0, cE: 0, cQ: 0,   // commanded lever levels, spooled
               stabLate: false, tieLate: false, exceed: 0, inExceed: false,
               strikes: 0, inZone: false, next: 0, done: false, t0: null, act: 0 };
  const _bp = new THREE.Vector3();
  const boomLen = () => L0 + st.ext;
  function basketPos(out = new THREE.Vector3()) {
    const L = boomLen(), h = Math.cos(st.el) * L;
    return out.set(Math.cos(st.sw) * h, PIV + Math.sin(st.el) * L, Math.sin(st.sw) * h);
  }
  const outreach = () => Math.cos(st.el) * boomLen();
  const momentPct = () => outreach() * LAY.load_kg / LAY.rated_moment * 100;
  function finish() {
    st.done = true;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const tieOk = st.tied && !st.tieLate, stabOk = st.stab && !st.stabLate;
    const rows = [
      { axis: 'reach', value: st.next + '/' + PTS.length, ok: st.next === PTS.length },
      { axis: 'envelope', value: String(st.exceed), ok: st.exceed === 0 },
      { axis: 'tie-off', value: tieOk ? 'clipped first' : st.tied ? 'clipped late' : 'never clipped', ok: tieOk },
      { axis: 'slope', value: stabOk ? 'set first' : st.stab ? 'set late' : 'never set', ok: stabOk },
      { axis: 'strikes', value: String(st.strikes), ok: st.strikes === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('boom-lift', rows,
      st.next === PTS.length && st.exceed === 0 && tieOk && stabOk && st.strikes === 0);
  }
  return {
    group: g, orbit: true, orbitCam: { pos: [22, 14, 24], tgt: [0, 5, 3] },
    mount: { parent: basketG, pos: [0, -.5, 0], yaw: -Math.PI / 2 },
    action() {
      if (st.done) return;
      const bp = basketPos();
      if (!st.lifted && !st.tied) {
        // on the ground: the harness clips to the basket anchor
        st.tied = true; st.t0 = performance.now();
        anchor.material = mat.post; blip(700, 1050, .12, 'triangle', .12);
        return;
      }
      const p = PTS[st.next];
      if (p && bp.distanceTo(_bp.set(p[0], p[1], p[2])) <= LAY.point_tol) {
        marks[st.next].material = mat.steel; st.next++;
        blip(880, 1320, .18); buzz(60, .3);
      }
    },
    update(dt) {
      if (st.done) return;
      const sr = .5, er = 1.6, qr = .45;
      st.cS = drive(st.cS, axis(keys.KeyA, keys.KeyD), dt);
      st.sw += sr * st.cS * dt;
      // the limit alarm: at the envelope the boom will not extend further
      // the boom will not extend past the rated moment however hard the
      // lever is held, and the drive still has to spool down off it
      st.cE = drive(st.cE, axis(keys.KeyS, keys.KeyW && momentPct() < 100), dt);
      st.cQ = drive(st.cQ, axis(keys.KeyE, keys.KeyQ), dt);
      st.ext = Math.max(0, Math.min(EXT, st.ext + er * st.cE * dt));
      st.el = Math.max(0, Math.min(EL_MAX, st.el + qr * st.cQ * dt));
      if (keys.KeyC && !st.lc && !st.lifted && !st.stab) {
        st.stab = true; for (const f of feet) f.position.y = .55;
        blip(320, 200, .25, 'square', .1);
      }
      st.lc = !!keys.KeyC;
      // the engine note follows the drive, not the lever: it is still
      // spooling down after the operator has let go
      const moving = Math.abs(st.cS) * .4 + Math.abs(st.cE) * .4 + Math.abs(st.cQ) * .5;
      st.act += (Math.min(1, moving) - st.act) * Math.min(1, 5 * dt);
      engineSet(.1 + st.act * .9);
      const bp = basketPos(_bp);
      if (!st.lifted && bp.y > LAY.stow_h) {
        // the basket leaves the ground: the two latched facts are read now
        st.lifted = true; st.tieLate = !st.tied; st.stabLate = !st.stab;
        if (!st.t0) st.t0 = performance.now();
      }
      const m = momentPct();
      if (m > 100 && !st.inExceed) {
        st.exceed++; st.inExceed = true; blip(1100, 500, .5, 'square', .18); buzz(220, .8);
      }
      if (m < 96) st.inExceed = false;
      if (LINE) {
        const d = Math.hypot(bp.y - LINE.y, bp.z - LINE.z);
        if (d < LINE.r && !st.inZone) {
          st.strikes++; st.inZone = true; zone.material.opacity = .4;
          blip(980, 490, .6, 'square', .2); buzz(320, .9);
        }
        if (d > LINE.r + .3 && st.inZone) { st.inZone = false; zone.material.opacity = .16; }
      }
      turret.rotation.y = -st.sw;
      boomG.rotation.z = st.el;
      stage.position.x = L0 - EXT / 2 + st.ext;
      basketG.position.x = boomLen();
      basketG.rotation.z = -st.el;
      if (st.next === PTS.length && st.lifted && bp.y <= LAY.stow_h) finish();
      if (simView === 'basket') {
        // standing in the basket, facing out along the boom toward the work
        seatPose(bp.x, bp.y + .6, bp.z,
          bp.x + Math.cos(st.sw) * 4, bp.y + .4, bp.z + Math.sin(st.sw) * 4);
      }
    },
    gauges: () => ({
      height: basketPos(_bp).y,
      outreach: outreach(),
      swing: ((st.sw * 180 / Math.PI) % 360 + 360) % 360,
      elev: st.el * 180 / Math.PI,
      moment: momentPct(),
      tieoff: { v: st.tied ? 1 : 0, txt: st.tied ? '\\u25a0' : '\\u2013' },
      stab: { v: st.stab ? 1 : 0, txt: st.stab ? '\\u25a0' : '\\u2013' },
      points: { v: st.next, txt: st.next + '/' + PTS.length },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* ---------------------------------------------------- overhead crane -----
   A bridge crane in a shop bay: runway beams on columns, a bridge that
   travels x, a trolley that traverses z, a hoist. The load is a pendulum
   under the hook exactly as the tower crane's is; the bay's pedestrian
   aisle and the scenario's workstation are painted rectangles a loaded
   pass over counts against, and every obstacle under the route has a
   height the load has to clear. */
function overheadCraneSim(P = {}) {
  const LAY = D.sims.sims['overhead-crane'].layout;
  const [BX, BZ] = LAY.bay;
  const PICK = P.pickup ?? [-8, -5], TGT = P.target ?? [6, 6];
  const OBS = P.obstacles ?? [], WS = P.workstation ?? null, AISLE = LAY.aisle;
  const g = new THREE.Group();
  const RAIL_Y = 8.2;
  /* The one seat that is INDOORS, so it draws its own bay rather than
     calling simYard's fenced outdoor yard - but it gets the same two things
     the yards just got: the floor its registry entry declares (a marked
     shop-bay slab, which is the route this seat travels) and high-bay
     lights that actually light it rather than four bright rectangles. */
  const yard = D.sims.sims['overhead-crane'].yard;
  const bayMat = finishMat(D.finCat[yard.surface],
    (BX * 2 + 6) / U * 2, (BZ * 2 + 6) / U * 2);
  const bay = new THREE.Mesh(boxGeo(BX * 2 + 6, .1, BZ * 2 + 6), bayMat);
  bay.position.set(0, .05, 0); bay.receiveShadow = true;
  bay.userData.yardSurface = yard.surface; g.add(bay);
  for (const [lx, lz] of [[-BX * .55, -BZ * .55], [BX * .55, -BZ * .55],
                          [-BX * .55, BZ * .55], [BX * .55, BZ * .55]]) {
    box(1.2, .25, .5, new THREE.MeshStandardMaterial({
      color: 0xfff2cf, emissive: 0xffdf9a, emissiveIntensity: .9 }),
      lx, RAIL_Y + 1.9, lz, g, false);
    const hb = new THREE.PointLight(0xffe9c8, lampCd(2.4, RAIL_Y + 1.6, 1.35),
      Math.hypot(BX, BZ) * 2.4, 1.35);
    hb.position.set(lx, RAIL_Y + 1.6, lz);
    hb.visible = qLevel !== 'low';
    g.add(hb); roomLights.push(hb);
  }
  // and the shop's own ambient, for the same reason the outdoor yards have
  // one: a bay lit only by a campus sun at dusk is a bay nobody can work in
  const bayHemi = new THREE.HemisphereLight(0xc8d2d6, 0x2a2622, 1.3);
  bayHemi.position.set(0, RAIL_Y, 0);
  bayHemi.visible = qLevel !== 'low';
  g.add(bayHemi); roomLights.push(bayHemi);
  for (let x = -BX - 2; x <= BX + 2; x += 6) for (const z of [-BZ - 1.4, BZ + 1.4])
    box(.5, RAIL_Y, .5, mat.metal, x, RAIL_Y / 2, z, g);
  for (const z of [-BZ - 1.4, BZ + 1.4]) box(BX * 2 + 6, .5, .45, mat.metal, 0, RAIL_Y + .25, z, g);
  const bridge = new THREE.Group(); g.add(bridge);
  box(.55, .8, BZ * 2 + 3.4, mat.post, 0, RAIL_Y + .9, 0, bridge);
  const trolley = box(1.0, .55, 1.0, mat.steel, 0, RAIL_Y + .3, 0, bridge);
  const ropeMat = new THREE.LineBasicMaterial({ color: 0xd8dde0 });
  const ropeGeo = new THREE.BufferGeometry().setFromPoints(
    [new THREE.Vector3(), new THREE.Vector3()]);
  g.add(new THREE.Line(ropeGeo, ropeMat));
  const hook = new THREE.Mesh(new THREE.OctahedronGeometry(.35), mat.post);
  hook.castShadow = true; g.add(hook);
  // the floor as the route sees it: aisle, workstation, obstacles, target
  const zoneMat = (c, o) => new THREE.MeshBasicMaterial({
    color: c, transparent: true, opacity: o, depthWrite: false });
  const rect = (r, y, m) => {
    const p = new THREE.Mesh(new THREE.PlaneGeometry(r.x[1] - r.x[0], r.z[1] - r.z[0]), m);
    p.rotation.x = -Math.PI / 2;
    p.position.set((r.x[0] + r.x[1]) / 2, y, (r.z[0] + r.z[1]) / 2); g.add(p); return p;
  };
  rect(AISLE, .12, zoneMat(0xE8A33D, .22));
  box(AISLE.x[1] - AISLE.x[0], .03, .18, mat.paint, (AISLE.x[0] + AISLE.x[1]) / 2, .13, AISLE.z[0], g, false);
  box(AISLE.x[1] - AISLE.x[0], .03, .18, mat.paint, (AISLE.x[0] + AISLE.x[1]) / 2, .13, AISLE.z[1], g, false);
  if (WS) {
    rect(WS, .12, zoneMat(0xE07C68, .2));
    box(WS.x[1] - WS.x[0] - 1, .9, 1.1, mat.wood, (WS.x[0] + WS.x[1]) / 2, .5, (WS.z[0] + WS.z[1]) / 2, g);
  }
  const obs = OBS.map((o) => box(o.w, o.h, o.d, mat.wall, o.x, o.h / 2, o.z, g));
  box(2.4, .12, 2.4, mat.slab, PICK[0], .12, PICK[1], g, false);
  rect({ x: [TGT[0] - 1.1, TGT[0] + 1.1], z: [TGT[1] - 1.1, TGT[1] + 1.1] }, .13, zoneMat(0x5CB584, .3));
  const load = box(1.6, 1.2, 1.6, mat.brick, PICK[0], .78, PICK[1], g);
  const st = { bx: PICK[0] - 4, tz: PICK[1] + 3, h: 5, attached: false, done: false,
               cX: 0, cZ: 0, cH: 0,   // commanded lever levels, spooled
               loadV: new THREE.Vector2(), swayPeak: 0, swayNow: 0, incursions: 0,
               inZone: false, limits: 0, atLimit: false, lowCarry: false, t0: null,
               act: 0, rumble: false };
  const inRect = (x, z, r) => x >= r.x[0] && x <= r.x[1] && z >= r.z[0] && z <= r.z[1];
  const loadPct = (P.load_t ?? 3) / (LAY.capacity_t ?? 5) * 100;
  function finish() {
    st.done = true;
    const d = Math.hypot(load.position.x - TGT[0], load.position.z - TGT[1]);
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'placement', value: d.toFixed(2) + ' m', ok: d <= .5 },
      { axis: 'sway', value: st.swayPeak.toFixed(2) + ' m', ok: st.swayPeak <= .6 },
      { axis: 'path', value: String(st.incursions), ok: st.incursions === 0 },
      { axis: 'limits', value: String(st.limits), ok: st.limits === 0 },
      { axis: 'clear', value: st.lowCarry ? 'carried low' : 'clear', ok: !st.lowCarry },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('overhead-crane', rows,
      d <= .5 && st.swayPeak <= .6 && st.incursions === 0 && st.limits === 0 && !st.lowCarry);
  }
  return {
    group: g, orbit: true, orbitCam: { pos: [20, 16, 24], tgt: [0, 3, 0] },
    mount: { parent: g, pos: [PICK[0] + 2.2, 0, PICK[1] + 1.4], yaw: -2.2 },
    action() {
      if (st.done) return;
      if (!st.attached) {
        const d = Math.hypot(st.bx - load.position.x, st.tz - load.position.z);
        if (d < 1.0 && st.h < 2.4) {
          st.attached = true; st.t0 = performance.now(); st.loadV.set(0, 0);
          blip(500, 760, .12, 'triangle', .12);
        }
      } else { st.attached = false; load.position.y = .78; finish(); }
    },
    update(dt) {
      if (st.done) return;
      const br = 1.3, tr = 1.0, hr = .9;
      // bridge and trolley are big masses on rails: they build and they
      // coast, and the sway axis is scored on exactly that
      st.cX = drive(st.cX, axis(keys.KeyA, keys.KeyD), dt);
      st.cZ = drive(st.cZ, axis(keys.KeyS, keys.KeyW), dt);
      const bridging = Math.abs(st.cX) > .02;
      st.bx = Math.max(-BX, Math.min(BX, st.bx + br * st.cX * dt));
      st.tz = Math.max(-BZ, Math.min(BZ, st.tz + tr * st.cZ * dt));
      // the hoist spools like the rest of the machine - and the upper limit
      // switch cuts the HOIST-UP command, which is the whole point of one:
      // the block still reaches the switch and still trips it, and then the
      // circuit is open until the operator lowers away
      st.cH = drive(st.cH, axis(keys.KeyE, keys.KeyQ && st.h < LAY.hook_max - 1e-6), dt);
      st.h = Math.max(st.attached ? LAY.hang : LAY.hook_min,
                      Math.min(LAY.hook_max, st.h + hr * st.cH * dt));
      // two-block: hoisting into the upper limit switch
      if (st.h >= LAY.hook_max - 1e-6 && !st.atLimit) {
        st.atLimit = true; st.limits++; blip(1100, 500, .5, 'square', .18); buzz(220, .8);
      }
      if (st.h < LAY.hook_max - .5) st.atLimit = false;
      if (bridging && !st.rumble) blip(70, 55, .35, 'sawtooth', .16);   // the bridge rumble
      st.rumble = !!bridging;
      // the motor note follows the drives, not the buttons: a pendant let go
      // is a machine still coasting
      const moving = Math.abs(st.cX) * .5 + Math.abs(st.cZ) * .3 + Math.abs(st.cH) * .5;
      st.act += (Math.min(1, moving) - st.act) * Math.min(1, 5 * dt);
      engineSet(st.act);
      bridge.position.x = st.bx;
      trolley.position.z = st.tz;
      if (st.attached) {
        const k = 5, damp = 1.4;
        const ax = (st.bx - load.position.x) * k - st.loadV.x * damp;
        const az = (st.tz - load.position.z) * k - st.loadV.y * damp;
        st.loadV.x += ax * dt; st.loadV.y += az * dt;
        load.position.x += st.loadV.x * dt;
        load.position.z += st.loadV.y * dt;
        // the load's centre hangs (hang - .6) under the hook: its underside
        // sits `hang` below it, the number the registry's carry height is
        // judged against
        load.position.y = Math.max(.78, st.h - (LAY.hang - .6));
        const sway = Math.hypot(st.bx - load.position.x, st.tz - load.position.z);
        st.swayNow = sway; st.swayPeak = Math.max(st.swayPeak, sway);
        const lx = load.position.x, lz = load.position.z, bottom = load.position.y - .6;
        // the route: never over the aisle or the workstation while loaded
        const over = inRect(lx, lz, AISLE) || (WS && inRect(lx, lz, WS));
        if (over && !st.inZone) {
          st.incursions++; st.inZone = true; blip(700, 300, .4, 'square', .16); buzz(200, .7);
        }
        if (!over) st.inZone = false;
        // and above every obstacle it crosses, by the declared clearance
        for (const o of obs) {
          const p = o.geometry.parameters;
          if (Math.abs(lx - o.position.x) < p.width / 2 + .8
            && Math.abs(lz - o.position.z) < p.depth / 2 + .8
            && bottom < p.height + LAY.clearance && !st.lowCarry) {
            st.lowCarry = true; thud(); buzz(140);
          }
        }
        hook.position.set(lx, load.position.y + .95, lz);
      } else {
        st.swayNow = 0;
        hook.position.set(st.bx, st.h, st.tz);
      }
      const pts = ropeGeo.attributes.position.array;
      pts[0] = st.bx; pts[1] = RAIL_Y; pts[2] = st.tz;
      pts[3] = hook.position.x; pts[4] = hook.position.y; pts[5] = hook.position.z;
      ropeGeo.attributes.position.needsUpdate = true;
      if (simView === 'pendant') {
        // the pendant operator walks the floor beside the load, watching it
        const fx = hook.position.x, fz = hook.position.z;
        seatPose(fx + 2.4, 1.7, fz + 1.8, fx, Math.min(hook.position.y, 2.2), fz,
          Math.min(1, 6 * dt));
      }
    },
    gauges: () => ({
      bridge: st.bx,
      trolley: st.tz,
      hook: st.h,
      sway: st.swayNow,
      load: { v: st.attached ? loadPct : 0, txt: st.attached ? loadPct.toFixed(0) : '\\u2013' },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

const OP_KEYS = ['KeyW', 'KeyS', 'KeyA', 'KeyD', 'KeyQ', 'KeyE', 'KeyR', 'KeyX', 'KeyC'];
const OP_DASH = '\\u2013';
function opRng(handle) {              // FNV-1a of the run handle seeds an LCG
  let h = 2166136261;
  for (let i = 0; i < handle.length; i++) {
    h ^= handle.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0;
  }
  let s = h || 1;
  return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; };
}
const wrapDeg = (d) => ((d + 180) % 360 + 360) % 360 - 180;
// hold a key toward a target reading; true once inside the tolerance
function seek(k, cur, want, tol, minus, plus) {
  if (Math.abs(want - cur) <= tol) return true;
  k[want > cur ? plus : minus] = true;
  return false;
}
// a novice's slip: with probability L.slip per step, one wrong key held too
function slip(k, c) {
  if (c.L.slip && c.rng() < c.L.slip) k[OP_KEYS[Math.floor(c.rng() * 6)]] = true;
}
// a novice's wandering setpoint: every so often, a new seeded offset
function wander(c, key, span, low, high) {
  const m = c.m;
  if (c.step >= (m[key + 'At'] ?? 0)) {
    m[key + 'At'] = c.step + low + Math.floor(c.rng() * (high - low));
    m[key] = -span + c.rng() * span * 1.4;
  }
  return m[key] ?? 0;
}

const OPERATORS = {
  'crane-lift': {
    levels: { optimal: { carry: 20, gate: [.5, .9], settle: .3, tol: .5 },
              novice: { carry: 8, gate: [1.2, 1.9], settle: .8, tol: .8, slip: .05 },
              hurried: { carry: 20, gate: [1e9, 1e9], settle: 1e9, tol: .9 } },
    step(g, c) {
      const k = {}, L = c.L, m = c.m, lay = c.def.layout;
      const slew = g.slew * Math.PI / 180, r = g.radius;
      const hx = Math.cos(slew) * r, hz = Math.sin(slew) * r;
      // the swing gate, with hysteresis: move while the swing gauge is
      // low, hold everything while it is high - the whole discipline
      if (g.swing > L.gate[1]) m.hold = true; else if (g.swing < L.gate[0]) m.hold = false;
      // slew toward a bearing; the tolerance is tangential at the radius
      // the hook will finally be at, so a small angle stays small there
      const slewTo = (x, z, atR) => {
        const da = wrapDeg((Math.atan2(z, x) - slew) * 180 / Math.PI);
        if (Math.abs(da) * Math.PI / 180 * atR <= L.tol) return true;
        if (!m.hold) k[da > 0 ? 'KeyD' : 'KeyA'] = true;
        return false;
      };
      const trolleyTo = (want) => m.hold ? false : seek(k, r, want, .3, 'KeyS', 'KeyW');
      let act = false;
      const [sx, sz] = lay.supply, [tx, tz] = lay.target;
      switch (c.id) {
        case 'reach': {
          const a = slewTo(sx, sz, Math.hypot(sx, sz)), b = trolleyTo(Math.hypot(sx, sz));
          const h = seek(k, g.hook, 4, .3, 'KeyE', 'KeyQ');
          if (a && b && h) c.next();
          break;
        }
        case 'hook': act = true; c.next(); break;
        case 'hoist':
          if (g.time.txt === OP_DASH) c.goto('reach');          // the hook missed
          else if (seek(k, g.hook, L.carry, .3, 'KeyE', 'KeyQ')) c.next();
          break;
        case 'pull-in': if (trolleyTo(7)) c.next(); break;
        case 'slew': if (slewTo(tx, tz, Math.hypot(tx, tz))) c.next(); break;
        case 'trolley': {
          const a = slewTo(tx, tz, Math.hypot(tx, tz)), b = trolleyTo(Math.hypot(tx, tz));
          if (a && b) c.next();
          break;
        }
        case 'settle': if (g.swing <= L.settle) c.next(); break;
        case 'lower': if (seek(k, g.hook, 3, .25, 'KeyE', 'KeyQ')) c.next(); break;
        case 'release':
          if (Math.hypot(hx - tx, hz - tz) > L.tol * 2) c.goto('trolley');
          else if (g.swing <= L.settle) { act = true; c.next(); }
          break;
      }
      slip(k, c);
      return { keys: k, act };
    },
  },
  'excavator-trench': {
    levels: { optimal: { tol: .45, dumpTol: .6 },
              novice: { tol: .45, dumpTol: .6, slip: .04, extra: .35 },
              hurried: { tol: .6, dumpTol: 2.4 } },
    step(g, c) {
      const k = {}, L = c.L, m = c.m, lay = c.def.layout, cells = c.P.cells ?? [];
      if (!m.dug) {
        m.dug = cells.map(() => 0);
        // the count per cell is the marked depth over the bite - a novice
        // mis-counts one bite extra on some cells (seeded)
        m.need = cells.map((x) => Math.round(x.d / lay.bite)
          + (L.extra && c.rng() < L.extra ? 1 : 0));
      }
      const slew = g.slew * Math.PI / 180, r = g.reach;
      const tx = Math.cos(slew) * r, tz = Math.sin(slew) * r;
      const go = (x, z, tol) => {
        const da = wrapDeg((Math.atan2(z, x) - slew) * 180 / Math.PI), wr = Math.hypot(x, z);
        const okA = Math.abs(da) * Math.PI / 180 * wr <= tol, okR = Math.abs(wr - r) <= tol;
        if (!okA) k[da > 0 ? 'KeyD' : 'KeyA'] = true;
        if (!okR) k[wr > r ? 'KeyW' : 'KeyS'] = true;
        return okA && okR && Math.hypot(tx - x, tz - z) <= tol * 1.5;
      };
      let act = false;
      const i = m.dug.findIndex((d, j) => d < m.need[j]);
      switch (c.id) {
        case 'cell': {
          if (i < 0) break;                       // the last dump finishes the run
          const x = (i - (cells.length - 1) / 2) * lay.pitch;
          const a = go(x, lay.trench_z, L.tol), b = seek(k, g.depth, .3, .2, 'KeyE', 'KeyQ');
          if (a && b) c.next();
          break;
        }
        case 'dig': act = true; m.dug[i]++; c.next(); break;
        case 'carry': {
          const a = go(lay.spoil[0], lay.spoil[1], L.dumpTol);
          const b = seek(k, g.depth, 1.2, .3, 'KeyE', 'KeyQ');
          if (a && b) c.next();
          break;
        }
        case 'dump': act = true; c.goto('cell'); break;
      }
      slip(k, c);
      return { keys: k, act };
    },
  },
  'forklift-run': {
    levels: { optimal: { v: 3.2, vTurn: 1.5, lane: true, exit: 1.5, aim: 1, dockFrac: .55 },
              novice: { v: 3.2, vTurn: 1.5, lane: true, exit: 1.5, aim: 1, dockFrac: .55, slip: .05 },
              hurried: { v: 6, vTurn: 6, lane: false, exit: 0, aim: 0, dockFrac: 1.6 } },
    step(g, c) {
      const k = {}, L = c.L, m = c.m, lay = c.def.layout, G = lay.gates;
      const n = c.P.gates ?? 4, w = c.P.dock_w ?? 2.2;
      const gateAt = (i) => [G.side[i % G.side.length] * G.x, G.z0 - i * G.pitch];
      const palletZ = G.z0 - n * G.pitch;
      // the clear return lane: outside every cone row, past the dock
      const laneX = lay.dock[0] + 2.5;
      const hd = g.heading * Math.PI / 180, dx = Math.sin(hd), dz = Math.cos(hd);
      const x = g.x, z = g.z, v = g.speed / 3.6;
      const tipX = x + 2.4 * dx, tipZ = z + 2.4 * dz;
      const bearing = (px, pz) =>          // + is left, which is KeyA
        Math.atan2(dz * (px - x) - dx * (pz - z), dx * (px - x) + dz * (pz - z));
      const range = (px, pz) => Math.hypot(px - x, pz - z);
      const steerTo = (px, pz, vWant) => {
        const b = bearing(px, pz);
        if (b > .04) k.KeyA = true; else if (b < -.04) k.KeyD = true;
        const want = Math.abs(b) > .45 ? Math.min(vWant, L.vTurn) : vWant;
        if (v < want - .15) k.KeyW = true;
        else if (v > want + .4 && v > 1) k.KeyS = true;
      };
      // a gate counts as taken 2.4 m before its centre, while the truck is
      // still crossing the cone line on its approach diagonal. Between
      // gates the next one is a full pitch down and across, a gentle turn
      // that clears the cones; the pallet is not - it sits on the centre
      // line, so the turn for it starts right at the last gate's inner
      // cone. So after the LAST take the truck first drives on through an
      // exit point past the centre on that same diagonal, then turns
      const taken = parseInt(g.gates.txt, 10);
      if (taken !== m.taken) {
        m.taken = taken;
        if (taken === n && L.exit) {
          const [gx, gz] = gateAt(taken - 1);
          const [px, pz] = taken > 1 ? gateAt(taken - 2) : lay.start;
          const len = Math.hypot(gx - px, gz - pz);
          m.exit = [gx + (gx - px) / len * L.exit, gz + (gz - pz) / len * L.exit];
        }
      }
      if (m.exit && (range(...m.exit) < 1.2
          || dx * (m.exit[0] - x) + dz * (m.exit[1] - z) < 0)) m.exit = null;   // reached or passed
      // pursuit of a gate's exact centre cuts the corner toward the inner
      // cone (the one facing the gate before); the aim point sits a little
      // outward of centre so the truck crosses the line nearer the centre
      const aimAt = (i) => {
        const [gx, gz] = gateAt(i), px = i > 0 ? gateAt(i - 1)[0] : lay.start[0];
        return [gx + Math.sign(gx - px) * (L.aim ?? 0), gz];
      };
      let act = false;
      switch (c.id) {
        case 'gates':
          if (taken >= n) c.next();
          else if (m.exit) steerTo(...m.exit, L.v);
          else steerTo(...aimAt(taken), L.v);
          break;
        case 'approach': {
          const d = range(0, palletZ) - 2.4;
          if (Math.hypot(tipX, tipZ - palletZ) < 1.3 && v < .9) c.next();
          else if (m.exit) steerTo(...m.exit, L.v);
          else steerTo(0, palletZ, Math.max(.4, Math.min(L.v, d * .8)));
          break;
        }
        case 'lift':
          if (g.load.v === 1) { m.wp = 0; c.next(); }
          else if (v < 1) act = true;
          else k.KeyS = true;
          break;
        case 'return': {
          if (!L.lane) { c.next(); break; }
          const wps = [[laneX, palletZ], [laneX, lay.dock[1] - 12]];
          if (m.wp >= wps.length) { c.next(); break; }
          if (range(...wps[m.wp]) < 2.5) m.wp++; else steerTo(...wps[m.wp], L.v);
          break;
        }
        case 'dock': {
          const [ox, oz] = lay.dock;
          if (Math.abs(tipX - ox) < w * L.dockFrac && Math.abs(tipZ - oz) < w * L.dockFrac) {
            act = true; c.next();
          } else steerTo(ox, oz, Math.max(.5, Math.min(L.v, (range(ox, oz) - 2.4) * .8)));
          break;
        }
      }
      slip(k, c);
      return { keys: k, act };
    },
  },
  'weld-bead': {
    levels: { optimal: { duty: 1 }, novice: { duty: 1, wander: .9 }, hurried: { duty: .4 } },
    step(g, c) {
      const k = {}, L = c.L, band = c.P.band ?? [2, 5];
      let want = (band[0] + band[1]) / 2, act = false;
      // a novice's gap wanders around the band - and drifts back late,
      // only once it is clear of it, never so far the arc pops out
      if (L.wander) {
        want += wander(c, 'gapOff', L.wander, 30, 90);
        want = Math.max(band[0] - .4, Math.min(band[1] + .4, want));
      }
      switch (c.id) {
        case 'gap': if (seek(k, g.gap, want, .12, 'KeyE', 'KeyQ')) c.next(); break;
        case 'strike': act = true; c.next(); break;
        case 'travel':
          if (g.time.txt === OP_DASH) { c.goto('strike'); break; }   // the arc did not take
          seek(k, g.gap, want, .12, 'KeyE', 'KeyQ');
          // travel without pausing - a hurried hand stutters, and lingers
          if (L.duty >= 1 || c.step % 10 < L.duty * 10) k.KeyW = true;
          break;
      }
      return { keys: k, act };
    },
  },
  'scaffold-bay': {
    levels: { optimal: {}, novice: { slip: .12 }, hurried: { blind: true } },
    step(g, c) {
      const k = {}, L = c.L, m = c.m;
      if (g.stage.txt === OP_DASH) return { keys: k, act: false };     // the bay is built
      if (L.blind) {          // never reads the stage: steps the rack and places regardless
        if (c.step % 2) k.KeyD = true;
        return { keys: k, act: c.step % 3 === 0 };
      }
      if (m.blind > 0) { m.blind--; return { keys: k, act: true }; }
      switch (c.id) {
        case 'rack':
          if (g.rack.txt === g.stage.txt) c.next();
          else if (c.step % 2 === 0) k.KeyR = true;        // edge-triggered: press, release
          break;
        case 'place':
          if (L.slip && c.rng() < L.slip) { k.KeyD = true; m.blind = 1; break; }   // a slip: wrong rack, placed anyway
          if (g.rack.txt !== g.stage.txt) { c.goto('rack'); break; }
          return { keys: k, act: true };
      }
      return { keys: k, act: false };
    },
  },
  'rigging-signals': {
    levels: { optimal: {}, novice: { slip: .15 }, hurried: { guess: true } },
    step(g, c) {
      const k = {}, L = c.L, m = c.m;
      const KEY = { up: 'KeyQ', down: 'KeyE', 'swing-l': 'KeyA', 'swing-r': 'KeyD',
                    out: 'KeyW', in: 'KeyS' };
      if (g.called.txt === OP_DASH) return { keys: k, act: false };    // the card is done
      switch (c.id) {
        case 'read': {
          m.sig = g.called.txt;
          const opts = Object.keys(KEY);
          if (L.guess) m.sig = [...opts, 'stop'][m.g = ((m.g ?? -1) + 1) % 7];  // never reads the card
          else if (L.slip && c.rng() < L.slip) m.sig = opts[Math.floor(c.rng() * opts.length)];
          c.next();
          break;
        }
        case 'give':            // one press, then a release frame: the seat latches on the edge
          c.goto('read');
          if (m.sig === 'stop') return { keys: k, act: true };
          k[KEY[m.sig]] = true;
          break;
      }
      return { keys: k, act: false };
    },
  },
  'load-chart': {
    levels: { optimal: {}, novice: { slip: .2 }, hurried: { acceptAll: true } },
    step(g, c) {
      const k = {}, L = c.L, m = c.m;
      switch (c.id) {
        case 'read':            // the chart line at this radius is the seat's own gauge
          m.accept = L.acceptAll ? true : g.load <= g.chart;
          if (L.slip && c.rng() < L.slip) m.accept = !m.accept;
          c.next();
          break;
        case 'judge':
          c.goto('read');
          if (m.accept) return { keys: k, act: true };
          k.KeyX = true;
          break;
      }
      return { keys: k, act: false };
    },
  },
  'pressure-washer': {
    levels: { optimal: { dwell: .7, contain: true },
              novice: { dwell: 1.0, contain: true, wander: .7, slip: .03 },
              hurried: { dwell: 1.0, contain: false, off: -.6 } },
    step(g, c) { return opBench(g, c, 'containment'); },
  },
  'airless-sprayer': {
    levels: { optimal: { dwell: .6 },
              novice: { dwell: 1.0, wander: .7, slip: .03 },
              hurried: { dwell: 1.0, off: -.6, over: .5 } },
    step(g, c) { return opBench(g, c, null); },
  },
  'boom-lift': {
    // transit: go up to the transit elevation before going out, and come
    // back up before coming in - the arc a basket sweeps at that angle
    // clears a low overhead line and a fully extended boom still sits
    // inside the envelope. A hurried hand aims straight at the point and
    // extends along the line of sight; a novice does that on some points
    // (seeded), and slips keys
    levels: { optimal: { stab: true, tie: true, transit: true, tol: .5 },
              novice: { stab: true, tie: true, transit: true, tol: .6, slip: .04, direct: .5 },
              hurried: { stab: false, tie: false, transit: false, tol: .7 } },
    step(g, c) {
      const k = {}, L = c.L, m = c.m, lay = c.def.layout, pts = c.P.points ?? [];
      const n = parseInt(g.points.txt, 10), N = pts.length;
      const el = g.elev * Math.PI / 180, len = g.outreach / Math.max(.05, Math.cos(el));
      const solve = (p) => {
        const d = Math.hypot(p[0], p[2]), dy = p[1] - lay.pivot_y;
        return { bearing: Math.atan2(p[2], p[0]) * 180 / Math.PI,
                 len: Math.hypot(d, dy), el: Math.atan2(dy, d) * 180 / Math.PI };
      };
      const seekEl = (want, tol) => seek(k, g.elev, want, tol, 'KeyE', 'KeyQ');
      const seekLen = (want, tol) => seek(k, len, want, tol, 'KeyS', 'KeyW');
      const seekSw = (want, tol) => {
        const da = wrapDeg(want - g.swing);
        if (Math.abs(da) <= tol) return true;
        k[da > 0 ? 'KeyD' : 'KeyA'] = true;
        return false;
      };
      // this point's own transit: the declared angle, or - a hurried or
      // slipping hand - straight at the point
      if (m.pt !== n) {
        m.pt = n;
        m.direct = !L.transit || (L.direct ? c.rng() < L.direct : false);
      }
      const p = pts[n], s = p ? solve(p) : null;
      const transit = m.direct && s ? s.el : lay.transit_elev_deg;
      let act = false;
      switch (c.id) {
        case 'level':
          if (g.height <= lay.stow_h + .01) c.next();
          break;
        case 'stabilizers':
          if (!L.stab || g.stab.txt !== OP_DASH) c.next();
          else if (c.step % 2 === 0) k.KeyC = true;              // edge-triggered
          break;
        case 'tie-off':
          if (!L.tie || g.tieoff.txt !== OP_DASH) c.next();
          else act = true;
          break;
        case 'raise':
          if (seekEl(transit, 1.5)) { if (n >= N) c.goto('stow'); else c.next(); }
          break;
        case 'swing':
          seekEl(transit, 1.5);
          if (seekSw(s.bearing, 1.0)) c.next();
          break;
        case 'extend':
          seekEl(transit, 1.5); seekSw(s.bearing, 1.0);
          if (seekLen(s.len, .15)) c.next();
          break;
        case 'settle': {
          const a = seekSw(s.bearing, .8), b = seekLen(s.len, .12), e = seekEl(s.el, .6);
          const bx = g.outreach * Math.cos(g.swing * Math.PI / 180);
          const bz = g.outreach * Math.sin(g.swing * Math.PI / 180);
          if (a && b && e && Math.hypot(bx - p[0], g.height - p[1], bz - p[2]) <= lay.point_tol * L.tol)
            c.next();
          break;
        }
        case 'work':
          // do the task; the next step reads the points gauge - a miss
          // simply runs raise/swing/extend/settle again for the same point
          act = true; c.goto('raise');
          break;
        case 'stow': {
          // retract at transit, swing parallel to the line (bearing 0), lower
          if (!seekLen(lay.boom_min, .15)) { seekEl(lay.transit_elev_deg, 1.5); break; }
          if (!seekSw(0, 1.5)) { seekEl(lay.transit_elev_deg, 1.5); break; }
          seekEl(0, .8);
          break;
        }
      }
      slip(k, c);
      return { keys: k, act };
    },
  },
  'overhead-crane': {
    levels: { optimal: { carry: null, gate: [.12, .3], settle: .1, tol: .12, diag: false },
              novice: { carry: null, gate: [.12, .3], settle: .1, tol: .18, diag: false, slip: .05, low: .5 },
              hurried: { carry: 'limit', gate: [1e9, 1e9], settle: 1e9, tol: .3, diag: true } },
    step(g, c) {
      const k = {}, L = c.L, m = c.m, lay = c.def.layout;
      const [px, pz] = c.P.pickup ?? [-8, -5], [tx, tz] = c.P.target ?? [6, 6];
      // the sway gate, with hysteresis, exactly the tower crane's
      if (g.sway > L.gate[1]) m.hold = true; else if (g.sway < L.gate[0]) m.hold = false;
      const bridgeTo = (x) => m.hold ? false : seek(k, g.bridge, x, L.tol, 'KeyA', 'KeyD');
      const trolleyTo = (z) => m.hold ? false : seek(k, g.trolley, z, L.tol, 'KeyS', 'KeyW');
      // the carry height: the declared one; a novice on some yards carries
      // low (seeded); a hurried hand hoists into the upper limit
      if (m.carry === undefined)
        m.carry = L.carry === 'limit' ? lay.hook_max + 1
          : (L.low && c.rng() < L.low) ? lay.carry_h - 1.2 : lay.carry_h;
      let act = false;
      switch (c.id) {
        case 'reach': {
          const a = seek(k, g.bridge, px, .1, 'KeyA', 'KeyD'), b = seek(k, g.trolley, pz, .1, 'KeyS', 'KeyW');
          const h = seek(k, g.hook, 2.2, .12, 'KeyE', 'KeyQ');
          if (a && b && h) c.next();
          break;
        }
        case 'hook': act = true; c.next(); break;
        case 'hoist':
          if (g.time.txt === OP_DASH) c.goto('reach');          // the hook missed
          // a hurried hand hoists until the limit switch stops it
          else if (seek(k, g.hook, m.carry, .1, 'KeyE', 'KeyQ')
            || (L.carry === 'limit' && g.hook >= lay.hook_max - .01)) c.next();
          break;
        case 'bridge':
          if (L.diag) trolleyTo(tz);
          if (bridgeTo(tx)) c.next();
          break;
        case 'trolley':
          bridgeTo(tx);
          if (trolleyTo(tz)) c.next();
          break;
        case 'settle': if (g.sway <= L.settle) c.next(); break;
        case 'lower': if (seek(k, g.hook, 2.2, .1, 'KeyE', 'KeyQ')) c.next(); break;
        case 'release':
          if (Math.hypot(g.bridge - tx, g.trolley - tz) > L.tol * 2) c.goto('bridge');
          else if (g.sway <= L.settle) { act = true; c.next(); }
          break;
      }
      slip(k, c);
      return { keys: k, act };
    },
  },
};
// the two hand-tool benches share one raster policy: contain (the washer),
// set the standoff to the middle of the effective window, pull the
// trigger, then sweep the grid row by row with a dwell just past the
// clean/coat time. A novice's standoff wanders; a hurried hand skips the
// berm, crowds the surface and (spraying) overshoots the mask at row ends
function opBench(g, c, containGauge) {
  const k = {}, L = c.L, m = c.m, lay = c.def.layout;
  const cols = c.P.cols ?? 6, rows = c.P.rows ?? 4, cell = lay.cell;
  const x0 = -cols * cell / 2, so = lay.standoff;
  let want = (so.damage_under + so.effective_max) / 2 + (L.off ?? 0);
  if (L.wander) want += wander(c, 'gapOff', L.wander, 60, 180);
  let act = false;
  switch (c.id) {
    case 'contain':
      if (!containGauge || !L.contain || g[containGauge].txt !== OP_DASH) c.next();
      else if (c.step % 2 === 0) k.KeyC = true;              // edge-triggered
      break;
    case 'standoff': if (seek(k, g.gap, want, .08, 'KeyE', 'KeyQ')) c.next(); break;
    case 'spray': act = true; m.i = 0; m.t = 0; c.next(); break;
    case 'raster': {
      seek(k, g.gap, want, .08, 'KeyE', 'KeyQ');             // hold the standoff all sweep
      if (m.i >= cols * rows) break;
      const r = Math.floor(m.i / cols), ci = r % 2 ? cols - 1 - m.i % cols : m.i % cols;
      let ux = x0 + (ci + .5) * cell;
      if (L.over && (ci === 0 || ci === cols - 1)) ux += (ci === 0 ? -1 : 1) * L.over;
      const a = seek(k, g.u, ux, .05, 'KeyA', 'KeyD');
      const b = seek(k, g.v, (r + .5) * cell, .05, 'KeyS', 'KeyW');
      if (a && b) { m.t += c.dt; if (m.t >= L.dwell) { m.i++; m.t = 0; } }
      break;
    }
  }
  slip(k, c);
  return { keys: k, act };
}

/* the driver: attach a policy to the running seat, step it once per
   physics step, run a seat headlessly to completion at a fixed dt, and
   sweep seats x scenarios x levels x seeds through simResults() exactly
   as a human run goes - one integration point, downstream of the score */
function opAttach(level, seed, sweep, fixedDt = null) {
  const def = D.sims.sims[curSimId], op = OPERATORS[curSimId];
  if (!op || !def.operator.levels.includes(level))
    throw new Error('no scripted reference operator for ' + curSimId + ' at ' + level);
  const scenario = curScenario?.id ?? null, proc = def.operator.procedure;
  opRun = { sim: curSimId, level, seed, scenario, sweep, def, fixedDt,
    P: curScenario?.params ?? {}, L: op.levels[level], m: { phase: 0 },
    step: 0, dt: fixedDt ?? 1 / 60, result: null,
    rng: opRng(curSimId + ':' + scenario + ':' + level + ':' + seed),
    next() { this.m.phase++; },
    goto(pid) { this.m.phase = proc.findIndex((p) => p.id === pid); },
    get id() { return proc[this.m.phase]?.id ?? null; } };
}
function opStep(dt) {
  if (!opRun || !sim || opRun.result) return;
  opRun.dt = dt;
  const out = OPERATORS[opRun.sim].step(sim.gauges(), opRun) ?? {};
  for (const kk of OP_KEYS) keys[kk] = !!(out.keys && out.keys[kk]);
  if (out.act) sim.action?.();
  opRun.step++;
  if (!opRun.sweep && opRun.step % 12 === 1) {
    const p = opRun.def.operator.procedure[opRun.m.phase];
    document.getElementById('hint').textContent = '\U0001f916 scripted reference \\u00b7 '
      + opRun.level + ' \\u00b7 ' + (p ? 'step ' + (opRun.m.phase + 1) + '/'
        + opRun.def.operator.procedure.length + ': ' + p.step : 'done')
      + ' \\u00b7 Esc';
  }
}
function opRunHeadless(simId, scenarioId, level, seed, dt, maxSec, every = 0) {
  const def = D.sims.sims[simId];
  if (!def) throw new Error('no such seat: ' + simId);
  if (!def.halls.includes(slug)) showHall(def.halls[0]);   // a seat is entered from its hall
  opHeadless = true;
  try {
    startSim(simId, scenarioId);
    opAttach(level, seed, true, dt);
    const max = Math.ceil(maxSec / dt), samples = [];
    let n = 0;
    while (!opRun.result && n < max) {
      // `every` > 0 samples the gauges every N steps for a harness to read
      if (every && n % every === 0) samples.push({ step: n, phase: opRun.id, g: sim.gauges() });
      opStep(dt); sim.update(dt); traceStep(dt); n++;
    }
    const r = opRun.result;
    return { sim: simId, scenario: curScenario?.id ?? null, level, seed, steps: n, dt,
      passed: r ? r.passed : null, timedOut: !r,
      axes: r ? Object.fromEntries(r.rows.map((x) => [x.axis, x.value])) : null,
      ok: r ? Object.fromEntries(r.rows.filter((x) => x.ok !== null)
        .map((x) => [x.axis, x.ok])) : null,
      ...(every ? { samples } : {}) };
  } finally {
    opRun = null; teardownSim(); opHeadless = false;
  }
}
// where a headless run was launched from, and the way back: a run tears the
// launching view down for its seat, so the view is marked before and
// restored after - by a single run and by the sweep through the SAME two
// calls, never left reading 'sim' with no seat in it
function opViewMark() { return { view, slug, campusKey }; }
function opViewRestore(before) {
  if (before.view === 'campus') showCampus(before.campusKey);
  else if (before.view === 'region') showRegion();
  else showHall(before.slug);
}
async function opSweep(o = {}) {
  const sims = o.sims ?? Object.keys(OPERATORS);
  const levels = o.levels ?? Object.keys(D.sims.operatorLevels);
  const seeds = o.seeds ?? [1], dt = o.dt ?? 1 / 60, maxSec = o.maxSec ?? 400;
  const before = opViewMark(), rows = [];
  for (const id of sims) {
    const scs = (D.sims.sims[id].scenarios ?? [null])
      .filter((s) => !o.scenarios || o.scenarios.includes(s?.id));
    for (const sc of scs) for (const level of levels) for (const seed of seeds) {
      rows.push(opRunHeadless(id, sc?.id, level, seed, dt, maxSec));
      await new Promise((res) => setTimeout(res, 0));   // let the page breathe between runs
    }
  }
  opViewRestore(before);   // back to where the sweep was launched from
  return { recorded: trainingOn, rows };
}"""

AVATAR_JS = """/* --------------------------------------------- avatar + mobile layer ---- */
// The locker is data (avatars registry): sections, options, emotes. The
// avatar is COSMETIC ONLY - the registry guarantee, asserted by its suite:
// nothing here is read by any grader.
const isTouch = 'ontouchstart' in window;
let avatarGroup = null, avatarMesh = null, walkAvatar = null;
let avatarCfg = null, lastEmote = null;
let emo = null;                       // {move, t} while an emote plays
let wheelSection = 0;                 // index into sections; length = emotes tab
let crewDistrict = null;              // the crew wheel's first level

function cfgInit() {
  const base = { ...D.avatars.defaults };
  const saved = prog.avatar;
  if (saved && typeof saved === 'object') {
    for (const s of D.avatars.sections) {
      if (s.options.some((o) => o.id === saved[s.id])) base[s.id] = saved[s.id];
    }
  }
  avatarCfg = base;
}

function optOf(sectionId) {
  const s = D.avatars.sections.find((x) => x.id === sectionId);
  return s.options.find((o) => o.id === avatarCfg[sectionId]) ?? s.options[0];
}

/* The humanoid: capsule body, real facial features, hair by style, the
   full wardrobe, and the crew mark - the hall's three-letter code on a
   shield in its district hue - stamped on vest, shirt and headwear.
   Parts are named for the emote moves: shoulders pivot, the hat lifts,
   the whole body spins or hops. The marks are the Academy's own insignia
   (the registry says so); no real union's logo is drawn. */
const crewTexCache = {};
function crewMarkTex(crewId) {
  if (crewTexCache[crewId]) return crewTexCache[crewId];
  const o = D.avatars.sections.find((s) => s.kind === 'crew')
    .options.find((x) => x.id === crewId);
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g2 = c.getContext('2d');
  g2.clearRect(0, 0, 128, 128);
  const hue = o?.hue ?? 40;
  // the shield
  g2.beginPath();
  g2.moveTo(14, 18); g2.lineTo(114, 18); g2.lineTo(114, 72);
  g2.quadraticCurveTo(114, 104, 64, 122);
  g2.quadraticCurveTo(14, 104, 14, 72); g2.closePath();
  g2.fillStyle = `hsl(${hue},52%,36%)`; g2.fill();
  g2.lineWidth = 6; g2.strokeStyle = `hsl(${hue},60%,68%)`; g2.stroke();
  g2.fillStyle = '#f2f4f2';
  g2.font = '700 44px "Barlow Condensed", system-ui, sans-serif';
  g2.textAlign = 'center'; g2.textBaseline = 'middle';
  g2.fillText(o?.glyph ?? '', 64, 62);
  g2.font = '600 15px "IBM Plex Sans", sans-serif';
  g2.fillText('TCA', 64, 96);
  const tex = new THREE.CanvasTexture(c);
  crewTexCache[crewId] = tex;
  return tex;
}
function markPlane(w, h, crewId) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
    new THREE.MeshBasicMaterial({ map: crewMarkTex(crewId), transparent: true }));
  return m;
}

function capsule(r, len, m, x, y, z, parent) {
  const c = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 4, 10), m);
  c.position.set(x, y, z); c.castShadow = true; parent.add(c);
  return c;
}
function sphere(r, m, x, y, z, parent, sx = 1, sy = 1, sz = 1) {
  const o = new THREE.Mesh(new THREE.SphereGeometry(r, 18, 14), m);
  o.position.set(x, y, z); o.scale.set(sx, sy, sz);
  o.castShadow = true; parent.add(o);
  return o;
}

function buildAvatarMesh(cfg) {
  const g = new THREE.Group();
  const M = (hex, rough = .8) => new THREE.MeshStandardMaterial({
    color: hex, roughness: rough });
  const skin = M(optOf('skin').value, .65);
  const hairM = M(optOf('haircolor').value, .85);
  const eyeM = M(optOf('eyes').value, .3);
  const topM = M(optOf('topcolor').value, .85);
  const pantsM = M(optOf('pantscolor').value, .9);
  const hatM = M(optOf('headcolor').value, .5);
  const hiviz = new THREE.MeshStandardMaterial({
    color: 0xd9c22e, emissive: 0x4a4208, roughness: .6 });
  const reflect = new THREE.MeshStandardMaterial({
    color: 0xe8ecec, emissive: 0x555b5b, roughness: .35 });
  const dark = M('#26262a', .85);
  const shoeHex = { 'steel-toe-brown': '#6a4a2a', 'steel-toe-black': '#26262a',
    'steel-toe-tan': '#a5793f', 'comp-toe-grey': '#6c7276', logger: '#4a3320',
    wellington: '#2e4d3a', hiker: '#7a5a34', 'rubber-yellow': '#d9c22e',
    'rubber-green': '#3c6b45', 'sneaker-white': '#e6e6e2',
    'sneaker-black': '#26262a', 'sneaker-red': '#a03a34',
    'sneaker-blue': '#2f4d8a', 'high-top': '#33363a', 'slip-on': '#5d4127',
    lineman: '#3a2a1c' }[cfg.shoes] ?? '#6a4a2a';
  const shoeM = M(shoeHex, .7);
  const crewId = cfg.crew;

  // costume recipes: a themed re-dress plus a few props; the everyday
  // locker stays stored untouched underneath (costume 'none')
  let CS = {
    krewe: { top: '#5a2d82', pants: '#2f6b45', hat: '#c9a227', noVest: true },
    foundry: { top: '#9aa1a6', pants: '#7d848a', hat: '#b9bcbe',
      metal: true, noVest: true },
    diver: { top: '#274a52', pants: '#274a52', hat: '#8a6a2a', noVest: true },
    'vintage-33': { top: '#8a7f6a', pants: '#5b5244', hat: '#4a4238',
      noVest: true },
    'storm-rider': { top: '#2e4d3a', pants: '#2e4d3a', hat: '#d9c22e' },
    'gold-journey': { top: '#c9a227', pants: '#8a6a1e', hat: '#c9a227',
      metal: true, noVest: true },
    hazmat: { top: '#e3dc9a', pants: '#e3dc9a', hat: '#e3dc9a', noVest: true },
    'arc-guard': { top: '#6c7276', pants: '#6c7276', hat: '#33363a',
      noVest: true },
    tunnel: { top: '#e8722a', pants: '#e8722a', hat: '#d9c22e' },
    parade: { top: '#e6e6e2', pants: '#e6e6e2', hat: '#2c3e5a', noVest: true },
    'night-reflective': { top: '#33363a', pants: '#33363a', hat: '#33363a' },
    mascot: { top: '#2f4d8a', pants: '#d9c22e', hat: '#e8722a' },
    frost: { top: '#bcd4e6', pants: '#9cb8cc', hat: '#e6eef4', noVest: true },
    gala: { top: '#1d1f24', pants: '#1d1f24', hat: '#1d1f24', noVest: true },
    'ape-mascot': { top: '#3a2f28', pants: '#3a2f28', hat: '#3a2f28' },
    'pelican-mascot': { top: '#e8e6de', pants: '#e8e6de', hat: '#e8e6de' },
    'bear-mascot': { top: '#5d4127', pants: '#5d4127', hat: '#5d4127' },
    'gator-mascot': { top: '#3c6b45', pants: '#3c6b45', hat: '#3c6b45' },
    'ox-mascot': { top: '#6b5341', pants: '#6b5341', hat: '#6b5341' },
  }[cfg.costume];
  // an animal mascot costume swaps the whole head for an original
  // Academy animal; its fur takes the topcolor pick, so the TradeApes
  // (and any dressed mascot) vary coat by coat
  const ANIMAL = /-mascot$/.test(cfg.costume) ? cfg.costume : null;
  if (ANIMAL) CS = { ...CS, top: optOf('topcolor').value,
    pants: optOf('topcolor').value };
  // the ape is a TRUE ape, proportioned to the measured reference in the
  // registry (span ~ height, deep hunch): long arms, wide shoulders,
  // heavy haunches, low-poly flat shading
  const APE = ANIMAL === 'ape-mascot';
  const APR = D.avatars.tradeapes.ape_reference;
  const APE_ARM = 1.12, APE_SHX = 1.06;
  if (CS) {
    topM.color.set(CS.top); pantsM.color.set(CS.pants); hatM.color.set(CS.hat);
    if (CS.metal) { topM.metalness = .55; topM.roughness = .35; }
  } else {
    if (cfg.pants === 'painter-white') pantsM.color.set('#e6e6e2');
    if (cfg.top === 'hi-vis-tee') { topM.color.set('#d9c22e'); topM.emissive.set('#4a4208'); }
    if (cfg.top === 'rain-shell') topM.roughness = .3;
  }
  const vestOn = cfg.vest !== 'none' && !CS?.noVest;

  const shorts = cfg.pants === 'shorts';
  const coveralls = cfg.top === 'coveralls';
  const legM = coveralls ? topM : pantsM;

  // legs: thigh + calf capsules, then footwear with real silhouettes -
  // shafts on the boots, soles and laces on the sneakers
  const SHAFT = { wellington: .3, 'rubber-yellow': .3, 'rubber-green': .3,
    lineman: .24, logger: .2, 'high-top': .15, hiker: .13 }[cfg.shoes] ?? 0;
  const SOLED = /sneaker|high-top|hiker/.test(cfg.shoes);
  const LACED = /sneaker|high-top|hiker|steel|comp|logger|lineman/.test(cfg.shoes);
  /* ---------------------------------------------------- the skeleton ---
     A real VRM / Unity humanoid bone hierarchy (vrm-c/UniVRM, MIT): every
     bone below is an actual transform node, nested as the spec nests them,
     and the geometry hangs off the bone it belongs to. That buys three
     things at once - elbows and knees that bend, a walk cycle that reads
     as walking, and an export a Unity Humanoid or VRM importer maps whole
     instead of in part. Rest-pose world heights are unchanged, so every
     capsule sits exactly where it always did. */
  const bone = (name, parent, x, y, z) => {
    const b = new THREE.Group();
    b.name = name; b.position.set(x, y, z); parent.add(b);
    return b;
  };
  const hips = bone('hips', g, 0, .95, 0);
  const spine = bone('spine', hips, 0, .15, 0);          // world 1.10
  const chest = bone('chest', spine, 0, .25, 0);         // world 1.35
  const neck = bone('neck', chest, 0, .22, 0);           // world 1.57
  const bones = { hips, spine, chest, neck };   // head joins below
  for (const [side, sx] of [['left', -1], ['right', 1]]) {
    const up = bone(side + 'UpperLeg', hips, sx * .13, -.13, 0);   // world .82
    const lo = bone(side + 'LowerLeg', up, 0, -.40, 0);            // world .42
    const ft = bone(side + 'Foot', lo, 0, -.32, 0);                // world .10
    bones[side + 'UpperLeg'] = up;
    bones[side + 'LowerLeg'] = lo;
    bones[side + 'Foot'] = ft;
    capsule(.095, .3, legM, 0, 0, 0, up);
    capsule(.08, .26, shorts ? skin : legM, 0, 0, 0, lo);
    if (SHAFT) box(.155, SHAFT, .18, shoeM, 0, .03 + SHAFT / 2, -.01, ft);
    const b = box(.17, .13, .3, shoeM, 0, 0, .03, ft);
    sphere(.085, shoeM, 0, -.01, .17, ft, 1, .8, 1);
    if (SOLED) box(.18, .035, .33, M('#e6e6e2', .6), 0, -.072, .03, ft, false);
    if (LACED) box(.1, .022, .07, dark, 0, .058, .1, ft, false);
    b.castShadow = true;
    // trouser details ride the bone whose limb they belong to
    if (cfg.pants === 'cargo') box(.05, .13, .16, pantsM, sx * .055, -.02, 0, up, false);
    if (cfg.pants === 'hi-vis') box(.16, .05, .21, reflect, 0, .08, 0, lo, false);
    if (cfg.pants === 'fr-pants') box(.165, .04, .21, M('#33363a', .8), 0, -.10, 0, lo, false);
    if (cfg.extras === 'knee-pads') box(.14, .12, .1, dark, 0, .18, .09, lo, false);
  }
  if (cfg.pants === 'carpenter')
    box(.03, .15, .05, pantsM, .215, .88, .02, g, false);   // the hammer loop
  // hips and torso
  box(.4, .16, .26, coveralls ? topM : pantsM, 0, 1.0, 0, g);
  capsule(.2, .38, topM, 0, 1.32, 0, g);
  if (APE) {
    const furB = new THREE.MeshStandardMaterial({
      color: CS.top, roughness: .95, flatShading: true });
    capsule(.235, .28, furB, 0, 1.28, .04, g);           // barrel chest
    sphere(.19, furB, 0, 1.02, .05, g, 1, .85, 1);       // the belly
    for (const sx of [-1, 1])
      sphere(.135, furB, sx * .17, .78, .02, g, 1, 1.1, 1);  // haunches
    // span/height ratio, recorded for the harness to hold against the
    // registry's measured reference
    g.userData.apeSpanRatio =
      (2 * .3 * APE_SHX + 2 * .64 * APE_ARM + .12) / 1.93;
  }
  if (cfg.top === 'flannel' || cfg.top === 'work-shirt') {
    box(.05, .5, .27, M('#2a2523', .9), 0, 1.32, 0, g);   // placket line
  }
  if (cfg.top === 'hoodie') {
    const hood = new THREE.Mesh(new THREE.TorusGeometry(.14, .05, 8, 14), topM);
    hood.position.set(0, 1.56, -.1); hood.rotation.x = .5; g.add(hood);
  }
  if (cfg.top === 'polo') box(.23, .05, .27, topM, 0, 1.545, 0, g, false);
  if (cfg.top === 'henley')
    for (const yy of [1.46, 1.4, 1.34])
      sphere(.012, M('#d9d4c8', .5), .02, yy, .21, g);
  if (cfg.top === 'denim-jacket') {
    for (const sx of [-1, 1])
      box(.02, .42, .265, M('#3a4a5c', .9), sx * .1, 1.32, 0, g, false);
    box(.42, .06, .27, M('#3a4a5c', .9), 0, 1.1, 0, g, false);
  }
  if (cfg.top === 'chore-coat') box(.43, .16, .3, topM, 0, 1.04, 0, g);
  if (cfg.top === 'sweatshirt') box(.41, .05, .28, topM, 0, 1.11, 0, g, false);
  if (cfg.top === 'thermal')
    for (const yy of [1.24, 1.36])
      box(.415, .02, .27, M('#00000022', .9), 0, yy, 0, g, false);
  if (cfg.pants === 'bib-overalls') {
    box(.26, .3, .04, pantsM, 0, 1.38, .2, g);
    for (const sx of [-1, 1]) box(.05, .3, .03, pantsM, sx * .1, 1.55, .16, g);
  }
  // outerwear shell, worn under the vest, over everything else
  const OUTER = !CS && {
    parka: { c: '#4a5a64', hood: 1, long: 1 },
    'rain-slicker': { c: '#d9c22e', sheen: 1, hood: 1, long: 1 },
    'welding-jacket': { c: '#7a5a34' }, bomber: { c: '#2e4d3a' },
    duster: { c: '#5d4127', long: 2 },
    windbreaker: { c: '#2f4d8a', sheen: 1 },
    'lined-flannel': { c: '#a03a34' },
    'hi-vis-parka': { c: '#e8722a', viz: 1, hood: 1 },
    softshell: { c: '#33363a' }, 'chore-canvas': { c: '#a5793f', long: 1 },
    puffer: { c: '#2c3e5a', puff: 1 }, anorak: { c: '#3c6b45', hood: 1 },
    varsity: { c: '#2c3e5a' }, trench: { c: '#8a7f6a', long: 2 },
  }[cfg.outer];
  if (OUTER) {
    const om = M(OUTER.c, OUTER.sheen ? .3 : .85);
    capsule(.225, .34, om, 0, 1.31, 0, g);
    for (const sx of [-1, 1]) capsule(.088, .16, om, sx * .3, 1.4, 0, g);
    if (OUTER.long) box(.43, .1 + .08 * OUTER.long, .31, om, 0, 1.0, 0, g);
    if (OUTER.hood) {
      const hd = new THREE.Mesh(new THREE.TorusGeometry(.15, .055, 8, 14), om);
      hd.position.set(0, 1.6, -.11); hd.rotation.x = .5; g.add(hd);
    }
    if (OUTER.puff)
      for (const yy of [1.2, 1.33, 1.46]) {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(.215, .05, 8, 16), om);
        ring.rotation.x = Math.PI / 2; ring.position.y = yy; g.add(ring);
      }
    if (OUTER.viz) box(.5, .05, .52, reflect, 0, 1.26, 0, g, false);
    if (cfg.outer === 'varsity')
      for (const sx of [-1, 1]) capsule(.09, .14, M('#e6e6e2', .8), sx * .3, 1.38, 0, g);
  }
  // the shirt mark
  // the crew mark rides the chest BONE, so it moves with the torso
  const crewMark = markPlane(.14, .16, crewId);
  crewMark.position.set(.1, .05, .215); chest.add(crewMark);

  // vest over it
  if (vestOn) {
    const vm = ['hi-vis-2', 'hi-vis-3', 'mesh'].includes(cfg.vest) ? hiviz
      : cfg.vest === 'fire-resist' ? M('#a03a34', .7)
      : cfg.vest === 'life-vest' ? M('#e8722a', .6)
      : cfg.vest === 'tool-vest' ? M('#5d4127', .85)
      : M('#4a5a64', .8);
    box(.46, .42, .05, vm, 0, 1.34, .2, g);
    box(.46, .42, .05, vm, 0, 1.34, -.2, g);
    for (const sx of [-1, 1]) box(.1, .06, .44, vm, sx * .17, 1.56, 0, g);
    if (cfg.vest !== 'tool-vest') {
      box(.46, .05, .055, reflect, 0, 1.24, .2, g, false);
      box(.46, .05, .055, reflect, 0, 1.24, -.2, g, false);
      if (cfg.vest === 'hi-vis-3' || cfg.vest === 'surveyor')
        for (const sx of [-1, 1])
          box(.06, .4, .055, reflect, sx * .12, 1.34, .2, g, false);
    }
    const back = markPlane(.2, .24, crewId);
    back.position.set(0, 1.36, -.228); back.rotation.y = Math.PI; g.add(back);
  }
  // tool belt
  if (cfg.tools !== 'none') {
    box(.44, .09, .3, dark, 0, .95, 0, g);
    const n = { basic: 1, framing: 3, electric: 2, plumber: 2, mason: 2,
      welder: 2, surveyor: 1, drywall: 2, hvac: 2, glazier: 1, roofer: 3,
      concrete: 2, rigger: 3, finisher: 2 }[cfg.tools] ?? 1;
    for (let i = 0; i < n; i++)
      box(.11, .16, .07, M('#5d4127', .9), -.16 + i * .16, .84, .18, g);
  }

  // arms on shoulder pivots
  const sleeves = ['long-sleeve', 'flannel', 'hoodie', 'sweatshirt',
    'denim-jacket', 'chore-coat', 'coveralls', 'thermal', 'rain-shell',
    'fleece', 'work-shirt'].includes(cfg.top);
  const tank = cfg.top === 'tank';
  const arms = {};
  const handM = cfg.extras === 'gloves' ? M('#e8722a', .7)
    : ANIMAL ? M(CS.top, .95)
    : cfg.costume === 'parade' || cfg.costume === 'mascot' ? M('#e6e6e2', .6)
    : skin;
  if (APE) handM.flatShading = true;
  for (const [nm, side, sx] of [['armL', 'left', -1], ['armR', 'right', 1]]) {
    // the arm chain hangs off the chest, so a shrug carries the whole arm
    const p = bone(side + 'UpperArm', chest, sx * .3, .17, 0);     // world 1.52
    const lo = bone(side + 'LowerArm', p, 0, -.28, 0);             // world 1.24
    const hd = bone(side + 'Hand', lo, 0, -.28, 0);                // world 0.96
    bones[side + 'UpperArm'] = p;
    bones[side + 'LowerArm'] = lo;
    bones[side + 'Hand'] = hd;
    capsule(.07, .2, tank ? skin : topM, 0, -.14, 0, p);
    capsule(.06, .18, sleeves ? topM : skin, 0, -.14, 0, lo);
    sphere(APE ? .082 : cfg.costume === 'mascot' ? .085 : .06, handM, 0, -.02, 0, hd);
    if (cfg.extras === 'elbow-pads') box(.1, .1, .09, dark, 0, -.02, .05, lo, false);
    if (cfg.costume === 'night-reflective' || cfg.costume === 'tunnel')
      box(.15, .035, .15, reflect, 0, .04, 0, lo, false);
    if (APE) { p.scale.y = APE_ARM; p.position.x *= APE_SHX; }
    arms[nm] = p;
    arms[nm + 'Lo'] = lo;
  }

  // neck + head with the face
  capsule(.06, .06, skin, 0, 1.6, 0, g);
  const head = bone('head', neck, 0, .21, 0);        // world 1.78
  bones.head = head;
  if (ANIMAL) {
    const fur = M(CS.top, .95);
    const eyePair = (ex, ey, ez, r = .018) => {
      for (const sx of [-1, 1]) {
        sphere(r * 1.7, M('#f2f2ee', .4), sx * ex, ey, ez, head, 1, 1, .55);
        sphere(r, eyeM, sx * ex, ey, ez + .02, head);
      }
    };
    if (ANIMAL === 'ape-mascot') {
      fur.flatShading = true;
      const face = new THREE.MeshStandardMaterial({
        color: '#c9a180', roughness: .7, flatShading: true });
      const lid = M('#a5794f', .75);
      sphere(.165, fur, 0, .015, -.01, head, 1, 1.05, 1);
      sphere(.115, face, 0, -.005, .085, head, 1, 1.04, .6);
      sphere(.08, face, 0, -.075, .115, head, 1.3, .8, .95);
      box(.06, .016, .02, M('#241f1c', .6), 0, -.1, .185, head, false);
      for (const sx of [-1, 1]) {
        sphere(.013, M('#241f1c', .5), sx * .022, -.052, .18, head);
        sphere(.052, fur, sx * .175, .02, -.02, head, .5, 1, .9);
        sphere(.03, face, sx * .175, .02, .01, head, .35, .7, .6);
        // the layered eye: lid band, sclera, iris, pupil
        sphere(.03, lid, sx * .052, .052, .112, head, 1.1, .55, .55);
      }
      box(.135, .03, .032, fur, 0, .082, .112, head, false);
      eyePair(.052, .033, .118);
      for (const sx of [-1, 1])
        sphere(.008, M('#0a0a0c', .3), sx * .052, .033, .152, head);
      head.scale.setScalar(1.12);
      head.position.y -= .06; head.position.z += .07;
    } else if (ANIMAL === 'pelican-mascot') {
      sphere(.15, fur, 0, .02, -.01, head, 1, 1.05, 1);
      const beak = M('#e08a2a', .55);
      box(.07, .025, .26, beak, 0, -.02, .22, head, false);
      box(.06, .02, .22, beak, 0, -.05, .2, head, false);
      sphere(.05, M('#e8b25a', .6), 0, -.085, .16, head, 1, 1.1, .9);
      eyePair(.055, .05, .11, .015);
    } else if (ANIMAL === 'bear-mascot') {
      sphere(.155, fur, 0, .01, 0, head, 1, 1, 1);
      const muz = M('#c9a180', .7);
      sphere(.07, muz, 0, -.045, .12, head, 1.1, .85, .9);
      sphere(.026, M('#241f1c', .4), 0, -.02, .19, head);
      for (const sx of [-1, 1]) sphere(.05, fur, sx * .11, .13, -.01, head);
      eyePair(.055, .04, .12);
    } else if (ANIMAL === 'gator-mascot') {
      sphere(.15, fur, 0, .02, -.02, head, 1, .9, 1);
      box(.13, .045, .22, fur, 0, -.03, .18, head);
      box(.12, .03, .2, M('#5b8a5f', .8), 0, -.065, .17, head, false);
      box(.11, .012, .18, M('#e6e6e2', .6), 0, -.048, .18, head, false);
      for (const sx of [-1, 1]) sphere(.035, fur, sx * .06, .1, .04, head);
      eyePair(.06, .095, .06, .016);
    } else if (ANIMAL === 'ox-mascot') {
      sphere(.155, fur, 0, .01, 0, head, 1.05, 1, 1);
      const muz = M('#cbb8a2', .7);
      sphere(.085, muz, 0, -.06, .11, head, 1.15, .8, .9);
      for (const sx of [-1, 1]) {
        sphere(.014, M('#241f1c', .5), sx * .03, -.06, .185, head);
        const horn = new THREE.Mesh(new THREE.ConeGeometry(.025, .12, 8),
          M('#e3d9c2', .5));
        horn.position.set(sx * .13, .14, 0);
        horn.rotation.z = sx * -.7; head.add(horn);
        sphere(.04, fur, sx * .15, .04, -.02, head, .5, .8, .9);
      }
      eyePair(.06, .04, .12);
    }
  } else {
  sphere(.145, skin, 0, 0, 0, head, 1, 1.08, 1);
  for (const sx of [-1, 1]) {
    sphere(.032, M('#f2f2ee', .4), sx * .052, .02, .118, head, 1, 1, .5);
    sphere(.016, eyeM, sx * .052, .02, .138, head);
    box(.05, .012, .02, hairM, sx * .052, .065, .125, head, false);
  }
  sphere(.028, skin, 0, -.01, .145, head, .8, 1.1, .9);           // nose
  box(.05, .012, .015, M('#8a5a4a', .6), 0, -.062, .132, head, false); // mouth
  for (const sx of [-1, 1]) sphere(.03, skin, sx * .14, 0, 0, head, .5, 1, .8);
  }

  // facial hair, from the hair colour
  const fh = ANIMAL ? 'none' : cfg.facialhair;
  if (fh !== 'none') {
    const fhM = new THREE.MeshStandardMaterial({
      color: optOf('haircolor').value, roughness: .95,
      transparent: fh === 'stubble', opacity: fh === 'stubble' ? .35 : 1 });
    const mo = () => box(.085, .02, .03, fhM, 0, -.035, .132, head, false);
    if (['light-mustache', 'mustache', 'handlebar', 'walrus'].includes(fh)) mo();
    if (fh === 'handlebar') for (const sx of [-1, 1])
      box(.02, .04, .025, fhM, sx * .05, -.05, .128, head, false);
    if (fh === 'walrus') box(.1, .035, .035, fhM, 0, -.05, .13, head, false);
    if (['goatee', 'circle-beard', 'soul-patch'].includes(fh))
      box(.05, .05, .03, fhM, 0, -.105, .11, head, false);
    if (fh === 'circle-beard') mo();
    if (['stubble', 'short-beard', 'full-beard', 'long-beard',
         'garibaldi'].includes(fh))
      sphere(.148, fhM, 0, -.045, 0, head, .95, .8, .95);
    if (['full-beard', 'long-beard', 'garibaldi'].includes(fh)) mo();
    if (fh === 'long-beard') capsule(.05, .1, fhM, 0, -.2, .06, head);
    if (fh === 'garibaldi') sphere(.09, fhM, 0, -.15, .05, head, 1, .9, .8);
    if (['chin-strap', 'mutton-chops'].includes(fh)) {
      for (const sx of [-1, 1])
        box(.03, .1, .06, fhM, sx * .125, -.04, .04, head, false);
      if (fh === 'chin-strap') box(.08, .03, .03, fhM, 0, -.125, .09, head, false);
    }
  }

  // hair, unless a full hat hides it anyway
  const hs = ANIMAL ? 'bald' : cfg.hair;
  if (hs !== 'bald') {
    const shell = (sy, y) => sphere(.152, hairM, 0, y, -.01, head, 1, sy, 1);
    if (['buzz', 'crew', 'undercut'].includes(hs)) shell(.62, .05);
    else if (['short', 'side-part', 'waves', 'curls'].includes(hs)) shell(.75, .045);
    else if (hs === 'afro') sphere(.2, hairM, 0, .07, -.01, head);
    else if (hs === 'bob') { shell(.85, .03); sphere(.15, hairM, 0, -.03, -.05, head, 1, .9, .8); }
    else if (hs === 'bun') { shell(.7, .045); sphere(.055, hairM, 0, .1, -.15, head); }
    else if (hs === 'ponytail') { shell(.7, .045); capsule(.04, .16, hairM, 0, -.06, -.16, head); }
    else if (hs === 'braids') { shell(.7, .045);
      for (const sx of [-1, 0, 1]) capsule(.025, .16, hairM, sx * .07, -.08, -.13, head); }
    else if (hs === 'locs') { shell(.75, .05);
      for (const sx of [-2, -1, 0, 1, 2]) capsule(.022, .12, hairM, sx * .05, -.05, -.12, head); }
    else if (hs === 'mohawk') box(.035, .09, .24, hairM, 0, .12, -.01, head);
    else if (hs === 'long') { shell(.8, .04);
      box(.2, .3, .05, hairM, 0, -.12, -.12, head, false); }
    if (hs === 'curls') sphere(.16, hairM, 0, .06, -.01, head, 1, .7, 1);
  }

  // headwear, on its own group so the hat-tip emote can lift it
  const hat = new THREE.Group(); hat.position.y = ANIMAL ? .17 : .13;
  head.add(hat);
  const hw = ANIMAL ? 'none' : cfg.headwear;
  const markFront = () => {
    const mk = markPlane(.09, .1, crewId);
    mk.position.set(0, .035, .135); mk.rotation.x = -.15; hat.add(mk);
  };
  if (['hard-cap', 'full-brim', 'climbing', 'vintage', 'carbon'].includes(hw)) {
    const dome = new THREE.Mesh(new THREE.CylinderGeometry(
      hw === 'vintage' ? .12 : .135, .15,
      hw === 'vintage' ? .13 : .09, 14),
      hw === 'carbon' ? M('#2a2d31', .35) : hatM);
    dome.position.y = .06; dome.castShadow = true; hat.add(dome);
    if (hw === 'full-brim') {
      const brim = new THREE.Mesh(new THREE.CylinderGeometry(.21, .225, .02, 16),
        hw === 'carbon' ? M('#2a2d31', .35) : hatM);
      brim.position.y = .015; hat.add(brim);
    } else if (hw !== 'climbing') box(.14, .02, .1, hatM, 0, .015, .17, hat, false);
    if (hw === 'climbing') box(.04, .06, .2, hatM, 0, .05, 0, hat, false);
    markFront();
  } else if (hw === 'ball-cap' || hw === 'ball-cap-back') {
    sphere(.15, hatM, 0, .03, 0, hat, 1, .68, 1);
    const brim = box(.13, .015, .12, hatM, 0, .02, hw === 'ball-cap' ? .19 : -.19, hat, false);
    if (hw === 'ball-cap') markFront();
  } else if (hw === 'flat-cap') {
    sphere(.15, hatM, 0, .025, -.02, hat, 1, .5, 1.05);
    box(.12, .012, .08, hatM, 0, .01, .16, hat, false);
  } else if (hw === 'beanie' || hw === 'winter-liner') {
    sphere(.152, hatM, 0, .03, 0, hat, 1, .8, 1);
    if (hw === 'winter-liner') for (const sx of [-1, 1])
      box(.03, .1, .08, hatM, sx * .14, -.05, .01, hat, false);
  } else if (hw === 'bucket') {
    const dm = new THREE.Mesh(new THREE.CylinderGeometry(.13, .14, .1, 14), hatM);
    dm.position.y = .05; hat.add(dm);
    const br = new THREE.Mesh(new THREE.CylinderGeometry(.19, .2, .015, 16), hatM);
    br.position.y = 0; hat.add(br);
  } else if (hw === 'welding-cap') {
    const dm = new THREE.Mesh(new THREE.CylinderGeometry(.135, .14, .09, 12), hatM);
    dm.position.y = .045; hat.add(dm);
    box(.1, .012, .07, hatM, 0, .005, .16, hat, false);
  } else if (hw === 'visor') {
    const band = new THREE.Mesh(new THREE.TorusGeometry(.145, .022, 8, 18), hatM);
    band.rotation.x = Math.PI / 2; band.position.y = .02; hat.add(band);
    box(.13, .014, .11, hatM, 0, .02, .18, hat, false);
  } else if (hw === 'headband') {
    const band = new THREE.Mesh(new THREE.TorusGeometry(.148, .02, 8, 18), hatM);
    band.rotation.x = Math.PI / 2; band.position.y = .015; hat.add(band);
  } else if (hw === 'bandana') {
    sphere(.152, hatM, 0, .02, 0, hat, 1, .55, 1);
    box(.05, .06, .02, hatM, 0, -.02, -.15, hat, false);
  }

  // extras: eye, ear and chest kit
  const ex = cfg.extras;
  if (ex === 'safety-glasses' || ex === 'sunglasses') {
    const lm = ex === 'sunglasses' ? M('#1a1c20', .3)
      : new THREE.MeshStandardMaterial({ color: 0xcfd8dc, roughness: .2,
          transparent: true, opacity: .55 });
    box(.13, .035, .02, lm, 0, .02, .148, head, false);
    for (const sx of [-1, 1]) box(.09, .012, .01, dark, sx * .1, .03, .07, head, false);
  }
  if (ex === 'ear-muffs') {
    for (const sx of [-1, 1]) sphere(.045, dark, sx * .15, .01, 0, head, .6, 1, 1);
    box(.24, .02, .02, dark, 0, .15, 0, head, false);
  }
  if (ex === 'respirator' || ex === 'dust-mask') {
    const mm = ex === 'respirator' ? M('#6c7276', .5) : M('#e6e6e2', .8);
    sphere(.07, mm, 0, -.035, .12, head, 1, .8, .7);
    if (ex === 'respirator')
      for (const sx of [-1, 1]) sphere(.028, M('#33363a', .5), sx * .05, -.05, .15, head);
  }
  if (ex === 'face-shield') {
    const sh = new THREE.Mesh(new THREE.PlaneGeometry(.24, .2),
      new THREE.MeshStandardMaterial({ color: 0xcfd8dc, roughness: .15,
        transparent: true, opacity: .35, side: THREE.DoubleSide }));
    sh.position.set(0, 0, .19); head.add(sh);
  }
  if (ex === 'welding-shield') {
    const sh = new THREE.Mesh(new THREE.PlaneGeometry(.22, .18),
      M('#173a2a', .4));
    sh.position.set(0, .16, .16); sh.rotation.x = -.5; hat.add(sh);
  }
  if (ex === 'headlamp') {
    box(.06, .04, .03, dark, 0, .05, .16, hat, false);
    sphere(.016, new THREE.MeshStandardMaterial({ color: 0xfff2cf,
      emissive: 0xffdf9a, emissiveIntensity: 1.2 }), 0, .05, .18, hat);
  }
  if (ex === 'radio') box(.06, .1, .04, dark, -.16, 1.44, .19, g, false);
  if (ex === 'id-badge') {
    const b2 = markPlane(.07, .09, crewId);
    b2.position.set(-.12, 1.3, .218); g.add(b2);
  }
  if (ex === 'tool-lanyard') {
    const ln = box(.015, .3, .015, M('#d9c22e', .6), .24, 1.14, .1, g, false);
    ln.rotation.z = .4;
  }

  // costume props
  if (CS) {
    const gold = M('#c9a227', .35); gold.metalness = .6;
    switch (cfg.costume) {
      case 'krewe':
        ['#5a2d82', '#c9a227', '#2f6b45'].forEach((c, i) => {
          const t = new THREE.Mesh(new THREE.TorusGeometry(.12 + .025 * i, .015, 6, 16), M(c, .35));
          t.position.set(0, 1.5 - .055 * i, .06); t.rotation.x = 1.25; g.add(t);
        });
        for (const sx of [-1, 1]) {
          const f = new THREE.Mesh(new THREE.ConeGeometry(.05, .16, 8), gold);
          f.position.set(sx * .3, 1.62, 0); g.add(f);
        }
        break;
      case 'foundry': {
        const hd = new THREE.Mesh(new THREE.CylinderGeometry(.16, .18, .2, 12),
          M('#b9bcbe', .3));
        hd.position.y = .06; hat.add(hd);
        box(.3, .4, .03, M('#8a8f94', .4), 0, 1.2, .22, g); break;
      }
      case 'diver': {
        const helm = new THREE.Mesh(new THREE.SphereGeometry(.2, 16, 12),
          M('#8a6a2a', .35));
        helm.position.y = .02; head.add(helm);
        const win = new THREE.Mesh(new THREE.CircleGeometry(.075, 16),
          new THREE.MeshStandardMaterial({ color: 0xbfe0e8, roughness: .15,
            transparent: true, opacity: .6 }));
        win.position.set(0, .02, .2); head.add(win);
        const hose = new THREE.Mesh(new THREE.TorusGeometry(.12, .02, 6, 14), dark);
        hose.position.set(0, 1.42, -.16); hose.rotation.y = .6; g.add(hose); break;
      }
      case 'vintage-33':
        for (const sx of [-1, 1])
          box(.05, .42, .03, M('#4a4238', .9), sx * .1, 1.34, .2, g, false);
        break;
      case 'gold-journey': {
        const sash = box(.1, .5, .03, gold, 0, 1.32, .21, g, false);
        sash.rotation.z = .6; break;
      }
      case 'parade': {
        const sash = box(.1, .5, .03, M('#a03a34', .6), 0, 1.32, .21, g, false);
        sash.rotation.z = -.6;
        const plume = new THREE.Mesh(new THREE.ConeGeometry(.03, .16, 8),
          M('#a03a34', .7));
        plume.position.set(0, .16, 0); hat.add(plume);
        for (const sx of [-1, 1]) box(.1, .03, .1, gold, sx * .3, 1.6, 0, g, false);
        break;
      }
      case 'hazmat': {
        const hd = new THREE.Mesh(new THREE.SphereGeometry(.185, 14, 10),
          M('#e3dc9a', .6));
        hd.position.y = .01; hd.scale.y = 1.1; head.add(hd);
        const win2 = new THREE.Mesh(new THREE.CircleGeometry(.08, 16),
          new THREE.MeshStandardMaterial({ color: 0xcfd8dc, roughness: .15,
            transparent: true, opacity: .5 }));
        win2.position.set(0, .02, .19); head.add(win2); break;
      }
      case 'arc-guard':
        box(.34, .12, .3, M('#6c7276', .6), 0, 1.6, 0, g); break;
      case 'tunnel':
        box(.42, .05, .28, reflect, 0, 1.3, 0, g, false);
        box(.42, .05, .28, reflect, 0, 1.14, 0, g, false); break;
      case 'night-reflective':
        box(.42, .05, .28, reflect, 0, 1.36, 0, g, false);
        box(.42, .05, .28, reflect, 0, 1.18, 0, g, false); break;
      case 'mascot': hat.scale.setScalar(1.7); break;
      case 'frost': {
        const cl = new THREE.Mesh(new THREE.TorusGeometry(.11, .04, 8, 14),
          M('#e6eef4', .7));
        cl.position.set(0, 1.56, 0); cl.rotation.x = Math.PI / 2; g.add(cl); break;
      }
      case 'gala':
        box(.16, .3, .02, M('#e6e6e2', .5), 0, 1.36, .21, g, false);
        box(.09, .035, .03, M('#1d1f24', .5), 0, 1.5, .215, g, false);
        for (const sx of [-1, 1])
          box(.03, .2, .022, M('#101114', .4), sx * .09, 1.42, .212, g, false);
        break;
      case 'storm-rider':
        box(.44, .06, .3, M('#d9c22e', .5), 0, 1.5, 0, g, false); break;
    }
  }

  const sc = optOf('build').scale ?? [1, 1, 1];
  g.scale.set(sc[0], sc[1], sc[2]);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  g.userData = { ...g.userData, arms, head, hat, bones };
  // The rig is NAMED for export in the VRM / Unity humanoid vocabulary
  // (vrm-c/UniVRM, MIT): bone() above named every bone as it was built,
  // so an importer meets the whole hierarchy rather than three loose
  // nodes. Only the root and the headwear are not VRM bones.
  g.name = 'tc-avatar';
  hat.name = 'headwear';                    // accessory, not a VRM bone
  return g;
}

function refreshAvatarMeshes() {
  if (avatarMesh) {
    const parent = avatarMesh.parent;
    parent.remove(avatarMesh);
    disposeOf(avatarMesh);
    avatarMesh = buildAvatarMesh(avatarCfg);
    parent.add(avatarMesh);
  }
  if (walkAvatar) {
    const pos = walkAvatar.position.clone(), rot = walkAvatar.rotation.y;
    scene.remove(walkAvatar);
    walkAvatar = buildAvatarMesh(avatarCfg);
    walkAvatar.position.copy(pos); walkAvatar.rotation.y = rot;
    scene.add(walkAvatar);
  }
}

/* --------------------------------------------------------- the gait ----
   With a real skeleton the walk can be a walk: the legs swing in
   opposition with the knees bending only on the return, the feet roll,
   the arms counter-swing at the elbow, and the hips rise on each step.
   Driven by DISTANCE TRAVELLED rather than elapsed time, so the stride
   is tied to the ground and never moonwalks when the frame rate dips.
   Reduced-motion users keep the rest pose. */
const GAIT_LIMBS = ['leftUpperLeg', 'rightUpperLeg', 'leftLowerLeg',
  'rightLowerLeg', 'leftFoot', 'rightFoot', 'leftUpperArm', 'rightUpperArm',
  'leftLowerArm', 'rightLowerArm'];
function gait(av, dist) {
  const b = av?.userData?.bones;
  if (!b || reduced) return;
  const ph = dist * 2.2;                      // one stride per ~2.9 m
  const sw = Math.sin(ph), op = Math.sin(ph + Math.PI);
  b.leftUpperLeg.rotation.x = sw * .55;
  b.rightUpperLeg.rotation.x = op * .55;
  b.leftLowerLeg.rotation.x = Math.max(0, -sw) * .95;   // knees bend one way
  b.rightLowerLeg.rotation.x = Math.max(0, -op) * .95;
  b.leftFoot.rotation.x = -b.leftLowerLeg.rotation.x * .45;
  b.rightFoot.rotation.x = -b.rightLowerLeg.rotation.x * .45;
  b.leftUpperArm.rotation.x = op * .40;
  b.rightUpperArm.rotation.x = sw * .40;
  b.leftLowerArm.rotation.x = -Math.abs(op) * .35;
  b.rightLowerArm.rotation.x = -Math.abs(sw) * .35;
  b.chest.rotation.y = sw * .08;
  b.hips.rotation.y = -sw * .05;
  b.hips.position.y = .95 + Math.abs(sw) * .03;
}
function gaitRest(av, dt) {                    // settle back to the rest pose
  const b = av?.userData?.bones;
  if (!b) return;
  // decay per SECOND, not per frame, so the settle looks the same on a
  // 120 Hz laptop and on a phone the quality ladder has dropped to 20 fps
  const k = Math.exp(-11 * Math.min(dt || .016, .1));
  for (const n of GAIT_LIMBS) b[n].rotation.x *= k;
  b.chest.rotation.y *= k; b.hips.rotation.y *= k;
  b.hips.position.y += (.95 - b.hips.position.y) * (1 - k);
}
// the locker's idle: a breath in the spine, and a head that notices you.
// Both are bounded - the neck turns at most ~34 deg and the head ~23, so
// the avatar looks around rather than swivelling like a doll.
const NECK_MAX = .6, HEAD_MAX = .4;
function idleBreath(av, t, dt) {
  const b = av?.userData?.bones;
  if (!b || reduced) return;
  b.spine.rotation.x = Math.sin(t * 1.1) * .014;
  b.chest.rotation.x = Math.sin(t * 1.1 + .5) * .012;
  // look toward the camera: the yaw between where the body faces and where
  // the viewer stands, split between neck and head and clamped at both
  const eye = eyePos();
  const dx = eye.x - av.position.x;
  const dz = eye.z - av.position.z;
  let yaw = Math.atan2(dx, dz) - av.rotation.y;
  yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));       // wrap to +/- PI
  const pitch = Math.max(-.3, Math.min(.3,
    -(eye.y - (av.position.y + 1.6)) * .08));
  const k = Math.min(1, (dt || .016) * 4);
  const nY = Math.max(-NECK_MAX, Math.min(NECK_MAX, yaw * .45));
  const hY = Math.max(-HEAD_MAX, Math.min(HEAD_MAX, yaw * .35));
  b.neck.rotation.y += (nY - b.neck.rotation.y) * k;
  b.head.rotation.y += (hY - b.head.rotation.y) * k;
  b.head.rotation.x += (pitch - b.head.rotation.x) * k;
}

/* ------------------------------------------------------ emote engine ---- */
function playEmote(id) {
  const e = D.avatars.emotes.find((x) => x.id === id);
  if (!e) return;
  lastEmote = id; emo = { move: e.move, t: 0 };
  buzz(30, .2);
}
const _emoTargets = [null, null];
function stepEmote(dt) {
  if (!emo) return;
  _emoTargets[0] = avatarMesh; _emoTargets[1] = walkAvatar;
  emo.t += dt;
  const T = 1.3, k = Math.min(1, emo.t / T);
  const s = Math.sin(k * Math.PI);            // rise and settle
  for (const av of _emoTargets) {
    if (!av) continue;
    const { arms, head, hat } = av.userData;
    arms.armL.rotation.set(0, 0, 0); arms.armR.rotation.set(0, 0, 0);
    arms.armLLo.rotation.set(0, 0, 0); arms.armRLo.rotation.set(0, 0, 0);
    hat.position.y = .13; av.position.y = av.userData.baseY ?? av.position.y;
    switch (emo.move) {
      case 'arm-wave':
        arms.armR.rotation.z = -2.6 * s;
        arms.armR.rotation.x = Math.sin(emo.t * 14) * .5 * s;
        arms.armRLo.rotation.z = -.5 * s; break;   // the elbow joins in
      case 'arm-up': arms.armR.rotation.x = -2.9 * s; break;
      case 'arm-point': arms.armR.rotation.x = -1.55 * s; break;
      case 'hat-tip':
        arms.armR.rotation.x = -2.4 * s;
        hat.position.y = .13 + .14 * s; hat.rotation.z = .35 * s; break;
      case 'clap':
        arms.armLLo.rotation.x = arms.armRLo.rotation.x = -.9;
        arms.armL.rotation.x = arms.armR.rotation.x = -1.4;
        arms.armL.rotation.z = .5 * Math.abs(Math.sin(emo.t * 12));
        arms.armR.rotation.z = -.5 * Math.abs(Math.sin(emo.t * 12)); break;
      case 'flex':
        arms.armL.rotation.z = 2.2 * s; arms.armR.rotation.z = -2.2 * s; break;
      case 'spin': av.rotation.y += dt * 10 * s; break;
      case 'jump':
        av.userData.baseY ??= av.position.y;
        av.position.y = av.userData.baseY + Math.abs(Math.sin(emo.t * 9)) * .35 * s;
        break;
    }
    // an emote owns the whole body: unwind any idle head-turn under it
    const b = av.userData.bones;
    if (b) {
      const d = Math.min(1, dt * 6);
      b.neck.rotation.y *= 1 - d;
      b.head.rotation.y *= 1 - d; b.head.rotation.x *= 1 - d;
    }
    if (k >= 1) {
      arms.armL.rotation.set(0, 0, 0); arms.armR.rotation.set(0, 0, 0);
      arms.armLLo.rotation.set(0, 0, 0); arms.armRLo.rotation.set(0, 0, 0);
      hat.position.y = .13; hat.rotation.z = 0;
      if (av.userData.baseY !== undefined) av.position.y = av.userData.baseY;
    }
  }
  if (k >= 1) emo = null;
}

/* ------------------------------------------------- the thumb wheel ------ */
// One radial control, sized for a thumb: wedges are the current locker
// section's options (colour or glyph), or the emote emojis on the last
// tab. Tap a wedge to apply or play.
function renderWheel() {
  const tabs = document.getElementById('wheelTabs');
  const sections = D.avatars.sections;
  const isChars = wheelSection === sections.length;
  const isEmotes = wheelSection === sections.length + 1;
  const isApes = wheelSection === sections.length + 2;
  tabs.innerHTML = sections.map((s, i) =>
    `<button class="wtab ${i === wheelSection ? 'on' : ''}" data-tab="${i}"
       title="${s.label}">${s.emoji}</button>`).join('')
    + `<button class="wtab ${isChars ? 'on' : ''}" data-tab="${sections.length}"
        title="Characters">\\ud83c\\udfaa</button>`
    + `<button class="wtab ${isEmotes ? 'on' : ''}" data-tab="${sections.length + 1}"
        title="Emotes">\\ud83d\\ude00</button>`
    + `<button class="wtab ${isApes ? 'on' : ''}" data-tab="${sections.length + 2}"
        title="${D.avatars.tradeapes.collection}">\\ud83e\\udd8d</button>`;
  const svg = document.getElementById('wheel');
  const sec = sections[wheelSection] ?? null;
  const isCrew = sec?.kind === 'crew';
  // the crew wheel is two levels deep: pick a district, then a hall
  let items, pickAttr = 'data-pick', hubGlyph;
  if (isEmotes) { items = D.avatars.emotes; hubGlyph = '\\ud83d\\ude00'; }
  else if (isChars) {
    items = D.avatars.characters.map((c) => ({ id: c.id, emoji: c.emoji }));
    pickAttr = 'data-charpick'; hubGlyph = '\\ud83c\\udfaa';
  }
  else if ((isCrew || isApes) && !crewDistrict) {
    const crewSec = sections.find((x) => x.kind === 'crew');
    const seen = new Map();
    for (const o of crewSec.options)
      if (!seen.has(o.district)) seen.set(o.district, o.hue);
    items = [...seen].map(([d, hue]) => ({
      id: d, glyph: d.slice(0, 2).toUpperCase(), hue,
      value: `hsl(${hue},45%,34%)` }));
    pickAttr = 'data-crewdist';
    hubGlyph = isApes ? '\\ud83e\\udd8d' : sec.emoji;
  } else if (isApes) {
    items = D.avatars.tradeapes.apes
      .filter((t) => t.district === crewDistrict)
      .map((t) => ({ id: t.hall, glyph: t.code,
        value: `hsl(${t.hue},45%,34%)` }));
    pickAttr = 'data-apepick'; hubGlyph = '\\u2190';
  } else if (isCrew) {
    items = sec.options.filter((o) => o.district === crewDistrict)
      .map((o) => ({ ...o, value: `hsl(${o.hue},45%,34%)` }));
    pickAttr = 'data-pick'; hubGlyph = '\u2190';
  } else { items = sec.options; hubGlyph = sec.emoji; }
  const cur = isEmotes ? lastEmote
    : isApes ? (avatarCfg.costume === 'ape-mascot' ? avatarCfg.crew : null)
    : sec ? avatarCfg[sec.id] : null;
  const N = items.length, R = 92, r0 = 34, cx = 100, cy = 100;
  const wedge = (i) => {
    const a0 = (i / N) * Math.PI * 2 - Math.PI / 2 + .015;
    const a1 = ((i + 1) / N) * Math.PI * 2 - Math.PI / 2 - .015;
    const p = (a, rr) => `${cx + Math.cos(a) * rr},${cy + Math.sin(a) * rr}`;
    return `M ${p(a0, r0)} L ${p(a0, R)} A ${R} ${R} 0 0 1 ${p(a1, R)} `
      + `L ${p(a1, r0)} A ${r0} ${r0} 0 0 0 ${p(a0, r0)} Z`;
  };
  const mid = (i, rr) => {
    const a = ((i + .5) / N) * Math.PI * 2 - Math.PI / 2;
    return [cx + Math.cos(a) * rr, cy + Math.sin(a) * rr];
  };
  const fsz = N > 14 ? 11 : 15;
  svg.innerHTML = items.map((o, i) => {
    const sel = o.id === cur;
    const fill = (isEmotes || isChars) ? 'var(--panel)'
      : o.value ?? 'var(--panel)';
    const [tx, ty] = mid(i, (r0 + R) / 2);
    const glyph = (isEmotes || isChars) ? o.emoji : o.glyph ?? '';
    return `<path d="${wedge(i)}" fill="${fill}"
        stroke="${sel ? 'var(--mark)' : 'var(--rule)'}"
        stroke-width="${sel ? 3 : 1}" ${pickAttr}="${o.id}"/>`
      + (glyph ? `<text x="${tx}" y="${ty}" text-anchor="middle"
          dominant-baseline="central" font-size="${isEmotes ? 17 : fsz}"
          fill="var(--ink)" pointer-events="none">${glyph}</text>` : '');
  }).join('')
    + `<circle cx="${cx}" cy="${cy}" r="${r0 - 6}" fill="var(--sunk)"
        stroke="var(--rule)" ${(isCrew || isApes) && crewDistrict ? 'data-crewback="1"' : ''}
        style="${(isCrew || isApes) && crewDistrict ? 'cursor:pointer' : ''}"/>`
    + `<text x="${cx}" y="${cy}" text-anchor="middle" dominant-baseline="central"
        font-size="20" pointer-events="none">${hubGlyph}</text>`;
}
function wheelShow(on) {
  document.getElementById('wheelWrap').style.display = on ? '' : 'none';
  if (on) renderWheel();
}
document.getElementById('wheelWrap').addEventListener('click', (e) => {
  const tab = e.target.closest('[data-tab]');
  if (tab) { wheelSection = +tab.dataset.tab; crewDistrict = null; renderWheel(); return; }
  const dist = e.target.closest('[data-crewdist]');
  if (dist) { crewDistrict = dist.dataset.crewdist; renderWheel(); return; }
  if (e.target.closest('[data-crewback]')) { crewDistrict = null; renderWheel(); return; }
  const ap = e.target.closest('[data-apepick]');
  if (ap) {
    const t = D.avatars.tradeapes.apes.find((x) => x.hall === ap.dataset.apepick);
    if (t) {
      avatarCfg = { ...t.cfg };
      prog.avatar = avatarCfg; saveProg();
      refreshAvatarMeshes(); renderWheel();
      if (view === 'avatar') {
        document.getElementById('hname').textContent = t.name;
        document.getElementById('hfocus').textContent =
          D.halls.find((h) => h.slug === t.hall).name + ' \\u00b7 '
          + D.avatars.tradeapes.honesty;
      }
    }
    return;
  }
  const chp = e.target.closest('[data-charpick]');
  if (chp) {
    const ch = D.avatars.characters.find((c) => c.id === chp.dataset.charpick);
    if (ch) {
      avatarCfg = { ...ch.cfg };
      prog.avatar = avatarCfg; saveProg();
      refreshAvatarMeshes(); renderWheel();
      if (view === 'avatar') {
        document.getElementById('hname').textContent = ch.name;
        document.getElementById('hfocus').textContent =
          ch.blurb + ' \u00b7 ' + D.avatars.guarantee;
      }
    }
    return;
  }
  const pick = e.target.closest('[data-pick]');
  if (!pick) return;
  const sections = D.avatars.sections;
  if (wheelSection === sections.length + 1) { playEmote(pick.dataset.pick); return; }
  avatarCfg[sections[wheelSection].id] = pick.dataset.pick;
  prog.avatar = avatarCfg; saveProg();
  refreshAvatarMeshes(); renderWheel();
});

/* ---------------------------------------------------- the locker view --- */
/* ---------------------------------------------- the metaverse layer ----- */
// Files, not a place: the connection to Unity, Sketchfab, Blender or any
// other glTF 2.0 consumer is standard files out and the learner's own
// files in. No service, no account, no upload - the meta registry states
// the contract and this page implements exactly it. The exporter/loader
// modules load on demand (repository or Pages build); where module
// resolution is unavailable the buttons degrade to a HUD line.
let lastExport = null, importedGlb = null;
function exportable(root) {
  const c = root.clone(true);
  const rm = [];
  c.traverse((o) => { if (o.isSprite || o.isLine || o.isPoints) rm.push(o); });
  rm.forEach((o) => o.parent?.remove(o));
  return c;
}
/* A minimal STORE-method zip around one file: where a host mediates
   saves (the published artifact) the allowlist takes .zip, so the .glb
   travels inside one, unchanged. */
const crcTable = (() => {
  const t = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[i] = c >>> 0;
  }
  return t;
})();
function zipOne(name, u8) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < u8.length; i++)
    crc = crcTable[(crc ^ u8[i]) & 0xFF] ^ (crc >>> 8);
  crc = (crc ^ 0xFFFFFFFF) >>> 0;
  const nm = new TextEncoder().encode(name);
  const out = new Uint8Array(30 + nm.length + u8.length + 46 + nm.length + 22);
  const dv = new DataView(out.buffer);
  const put = (off, bytes) => out.set(bytes, off);
  // local file header
  dv.setUint32(0, 0x04034b50, true); dv.setUint16(4, 20, true);
  dv.setUint32(14, crc, true);
  dv.setUint32(18, u8.length, true); dv.setUint32(22, u8.length, true);
  dv.setUint16(26, nm.length, true);
  put(30, nm); put(30 + nm.length, u8);
  // central directory
  const cd = 30 + nm.length + u8.length;
  dv.setUint32(cd, 0x02014b50, true); dv.setUint16(cd + 4, 20, true);
  dv.setUint16(cd + 6, 20, true);
  dv.setUint32(cd + 16, crc, true);
  dv.setUint32(cd + 20, u8.length, true); dv.setUint32(cd + 24, u8.length, true);
  dv.setUint16(cd + 28, nm.length, true);
  put(cd + 46, nm);
  // end of central directory
  const eo = cd + 46 + nm.length;
  dv.setUint32(eo, 0x06054b50, true);
  dv.setUint16(eo + 8, 1, true); dv.setUint16(eo + 10, 1, true);
  dv.setUint32(eo + 12, 46 + nm.length, true); dv.setUint32(eo + 16, cd, true);
  return out;
}
async function exportGlb(root, name) {
  try {
    const { GLTFExporter } = await import('three/addons/gltf/GLTFExporter.js');
    const bin = await new Promise((res, rej) =>
      new GLTFExporter().parse(exportable(root), res, rej, { binary: true }));
    lastExport = { name, bytes: bin.byteLength };
    const kb = (bin.byteLength / 1024).toFixed(0);
    // where the host mediates saves, offer the confirmed .zip door first
    const dlc = window.claude?.use ? await claude.use('downloads') : null;
    if (dlc) {
      try {
        await dlc.save({ filename: name + '.zip',
          data: new Blob([zipOne(name, new Uint8Array(bin))]) });
        document.getElementById('hint').textContent = name + '.zip · ' + kb
          + ' KB — unzip for the .glb (glTF 2.0, Unity / Sketchfab / Blender ready)';
      } catch (err) {
        document.getElementById('hint').textContent = err?.code === 'declined'
          ? 'save declined' : 'save unavailable — ' + (err?.message ?? err);
      }
      return;
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([bin], { type: 'model/gltf-binary' }));
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    document.getElementById('hint').textContent = name + ' · ' + kb
      + ' KB · glTF 2.0 — Unity / Sketchfab / Blender ready';
  } catch (e) {
    document.getElementById('hint').textContent =
      'glTF export unavailable here — ' + (e?.message ?? e);
  }
}
async function importGlb(file) {
  try {
    const { GLTFLoader } = await import('three/addons/gltf/GLTFLoader.js');
    const buf = await file.arrayBuffer();
    const gltf = await new Promise((res, rej) =>
      new GLTFLoader().parse(buf, '', res, rej));
    if (importedGlb) avatarGroup.remove(importedGlb.stand);
    const obj = gltf.scene;
    // the guest stand: the learner's OWN file, fitted, local only
    const bb = new THREE.Box3().setFromObject(obj);
    const size = bb.getSize(new THREE.Vector3());
    obj.scale.setScalar(1.3 / Math.max(size.x, size.y, size.z, .001));
    bb.setFromObject(obj);
    obj.position.set(2.2 - (bb.min.x + bb.max.x) / 2,
      .35 - bb.min.y, -(bb.min.z + bb.max.z) / 2);
    const stand = new THREE.Group(); stand.name = 'guest-asset';
    const ped = new THREE.Mesh(new THREE.CylinderGeometry(.9, 1.05, .35, 20),
      mat.slab);
    ped.position.set(2.2, .17, 0); ped.receiveShadow = true;
    stand.add(ped, obj);
    avatarGroup.add(stand);
    let nodes = 0; obj.traverse(() => nodes++);
    importedGlb = { stand, nodes, name: file.name };
    document.getElementById('hint').textContent = file.name + ' · ' + nodes
      + ' nodes on the guest stand — local only, never uploaded; its licence'
      + ' (e.g. CC-BY attribution) stays the learner\\'s to honour';
  } catch (e) {
    document.getElementById('hint').textContent =
      'could not read that file as glTF — ' + (e?.message ?? e);
  }
}
document.getElementById('glbBtn').addEventListener('click', () => {
  if (view === 'avatar' && avatarMesh) exportGlb(avatarMesh, 'tc-avatar.glb');
  else if (view === 'hall' && hallGroup)
    exportGlb(hallGroup, 'tc-hall-' + slug + '.glb');
});
document.getElementById('glbInBtn').addEventListener('click', () =>
  document.getElementById('glbFile').click());
document.getElementById('glbFile').addEventListener('change', (e) => {
  if (e.target.files?.[0]) importGlb(e.target.files[0]);
  e.target.value = '';
});

function showAvatar() {
  if (sim) teardownSim();
  if (walkActive) exitWalkMode();
  view = 'avatar';
  if (hallGroup) hallGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  if (regionGroup) regionGroup.visible = false;
  ground.visible = grid.visible = true;
  applyAtmos(null);
  scene.fog.near = 40; scene.fog.far = 140;
  document.getElementById('mm').style.display = 'none';
  if (!avatarGroup) {
    avatarGroup = new THREE.Group();
    const ped = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.9, .35, 24),
      mat.slab);
    ped.position.y = .17; ped.receiveShadow = true; avatarGroup.add(ped);
    avatarMesh = buildAvatarMesh(avatarCfg);
    avatarMesh.position.y = .35; avatarGroup.add(avatarMesh);
    scene.add(avatarGroup);
  }
  avatarGroup.visible = true;
  controls.enabled = true; controls.autoRotate = !reduced;
  controls.minDistance = 2.5; controls.maxDistance = 14;
  camera.position.set(3.1, 2.5, 5.2); controls.target.set(0, 1.1, 0);
  document.getElementById('hname').textContent = t('avatar.title');
  document.getElementById('hfocus').textContent = D.avatars.guarantee;
  document.getElementById('hint').textContent = '';
  for (const id of ['walkBtn', 'simBtn', 'campusBtn', 'camBtn', 'sndBtn'])
    document.getElementById(id).style.display = 'none';
  document.getElementById('glbBtn').style.display = '';
  document.getElementById('glbInBtn').style.display = '';
  wheelShow(true);
}
document.getElementById('avaBtn').addEventListener('click', showAvatar);

/* --------------------------------------------- touch walk (3rd person) -- */
// On touch devices walk mode is third-person: a left thumb-stick moves the
// avatar, a right-side drag turns the view, and the emote wheel rides the
// right thumb. Desktop keeps first-person pointer lock.
let tYaw = 0, tPitch = .28, joyVec = { x: 0, y: 0 };
function enterTouchWalk() {
  walkActive = true;
  controls.enabled = false; controls.autoRotate = false;
  cfgInit(); // ensure cfg
  if (!walkAvatar) {
    walkAvatar = buildAvatarMesh(avatarCfg);
    scene.add(walkAvatar);
  }
  walkAvatar.visible = true;
  const spawn = view === 'hall'
    ? new THREE.Vector3(0, 0, -(D.halls.find(x => x.slug === slug).depth * U) / 2 - 8)
    : new THREE.Vector3(0, 0, 30);
  walkAvatar.position.copy(spawn);
  walkAvatar.userData.baseY = spawn.y;
  tYaw = Math.PI; tPitch = .28;
  document.getElementById('joy').style.display = '';
  document.getElementById('emoBtn').style.display = '';
  document.getElementById('hint').textContent = '';
}
function exitWalkMode() {
  if (xrWalk) { walkEnded(); return; }
  if (!isTouch && walkActive) { plc.unlock(); return; }
  walkActive = false;
  if (walkAvatar) walkAvatar.visible = false;
  document.getElementById('joy').style.display = 'none';
  document.getElementById('emoBtn').style.display = 'none';
  document.getElementById('actBtn').style.display = 'none';
  wheelShow(false);
  controls.enabled = true;
  nearSlug = null; nearPoi = null; nearTrack = null;
}
function touchWalkStep(dt) {
  const sp = 5.2 * dt;
  const was = _twWas.copy(walkAvatar.position);
  const f = _twF.set(Math.sin(tYaw), 0, Math.cos(tYaw));
  const r = _twR.set(f.z, 0, -f.x);
  walkAvatar.position.addScaledVector(f, -joyVec.y * sp);
  walkAvatar.position.addScaledVector(r, -joyVec.x * sp);
  if (Math.hypot(joyVec.x, joyVec.y) > .1)
    walkAvatar.rotation.y = tYaw + Math.PI + Math.atan2(-joyVec.x, -joyVec.y);
  // stay on the grounds (campus) or in the hall envelope
  if (view === 'campus') {
    const len = Math.hypot(walkAvatar.position.x, walkAvatar.position.z);
    if (len > walkLim) walkAvatar.position.multiplyScalar(walkLim / len);
  } else if (view === 'hall') {
    const DEP = hallRec.depth * U;
    walkAvatar.position.x = Math.min(21, Math.max(-21, walkAvatar.position.x));
    walkAvatar.position.z = Math.min(DEP / 2 - .8,
      Math.max(-DEP / 2 - 26, walkAvatar.position.z));
  } else if (view === 'restoration') {
    const len = Math.hypot(walkAvatar.position.x, walkAvatar.position.z);
    if (len > RESTO_R) walkAvatar.position.multiplyScalar(RESTO_R / len);
  }
  // the gait rides the distance actually covered, after the clamps
  const moved = walkAvatar.position.distanceTo(was);
  walkAvatar.userData.dist = (walkAvatar.userData.dist ?? 0) + moved;
  if (moved > .0015) gait(walkAvatar, walkAvatar.userData.dist);
  else gaitRest(walkAvatar, dt);
  // third-person camera
  const back = _twF.set(Math.sin(tYaw), 0, Math.cos(tYaw));
  const eye = _twEye.copy(walkAvatar.position)
    .addScaledVector(back, 5.6).setY(walkAvatar.position.y + 2.2 + tPitch * 4);
  camera.position.lerp(eye, Math.min(1, 8 * dt));
  camera.lookAt(walkAvatar.position.x, walkAvatar.position.y + 1.4,
    walkAvatar.position.z);
  // nearest door / institution for the action button
  if (view === 'campus') {
    let best = null, bd = 1e9, bp = null, pd = 1e9;
    const wp = _wp;
    for (const b of buildings) {
      b.getWorldPosition(wp);
      const d = Math.hypot(wp.x - walkAvatar.position.x, wp.z - walkAvatar.position.z);
      if (d < bd) { bd = d; best = b; }
    }
    for (const b of cityHits) {
      b.getWorldPosition(wp);
      const d = Math.hypot(wp.x - walkAvatar.position.x, wp.z - walkAvatar.position.z);
      if (d < pd) { pd = d; bp = b; }
    }
    // the training yard's stands, on the same footing as a hall door
    let bs = null, sd = 1e9;
    for (const b of seatHits) {
      b.getWorldPosition(wp);
      const d = Math.hypot(wp.x - walkAvatar.position.x, wp.z - walkAvatar.position.z);
      if (d < sd) { sd = d; bs = b; }
    }
    const act = document.getElementById('actBtn');
    if (bs && sd < 6) {
      // nearest wins where they overlap, and a seat stand is a smaller
      // target than a building, so it is tested first
      nearSeat = bs.userData.seat; nearSlug = nearPoi = null;
      act.style.display = '';
      act.textContent = '\\u23ce ' + D.sims.sims[nearSeat].name;
    } else if (best && bd < 12) {
      nearSlug = best.userData.slug; nearPoi = null; nearSeat = null;
      act.style.display = '';
      act.textContent = '\\u23ce ' + D.halls.find(x => x.slug === nearSlug).name;
    } else if (bp && pd < 15) {
      nearPoi = bp.userData.poi; nearSlug = null; nearSeat = null;
      act.style.display = ''; act.textContent = '\\u23ce ' + nearPoi;
    } else { nearSlug = nearPoi = nearSeat = null; act.style.display = 'none'; }
  } else if (view === 'restoration') {
    let bt = null, td = 1e9;
    const wp = _wp;
    for (const b of restoBeacons) {
      b.getWorldPosition(wp);
      const d = Math.hypot(wp.x - walkAvatar.position.x, wp.z - walkAvatar.position.z);
      if (d < td) { td = d; bt = b; }
    }
    const act = document.getElementById('actBtn');
    if (bt && td < 6) {
      nearTrack = bt.userData.restoTrack;
      act.style.display = '';
      act.textContent = '\\u23ce ' + D.restoration.tracks.find((x) => x.id === nearTrack).title;
    } else { nearTrack = null; act.style.display = 'none'; }
  }
}
document.getElementById('actBtn').addEventListener('click', () => {
  if (nearSeat) enterSeatFromYard(nearSeat);
  else if (nearSlug) { showHall(nearSlug); enterTouchWalk(); }
  else if (nearTrack) openRestoTrack(nearTrack);
  else if (nearPoi) openCityPoi(nearPoi);
});
document.getElementById('emoBtn').addEventListener('click', () => {
  wheelSection = D.avatars.sections.length + 1;   // the emote tab
  const w = document.getElementById('wheelWrap');
  wheelShow(w.style.display === 'none');
});

// left thumb-stick
(() => {
  const joy = document.getElementById('joy'), knob = document.getElementById('knob');
  let pid = null, cx = 0, cy = 0;
  joy.addEventListener('pointerdown', (e) => {
    pid = e.pointerId;
    try { joy.setPointerCapture(pid); } catch (err) { /* pointer already gone */ }
    const r = joy.getBoundingClientRect();
    cx = r.left + r.width / 2; cy = r.top + r.height / 2;
  });
  joy.addEventListener('pointermove', (e) => {
    if (e.pointerId !== pid) return;
    const dx = (e.clientX - cx) / 46, dy = (e.clientY - cy) / 46;
    const len = Math.hypot(dx, dy) || 1, cl = Math.min(1, len);
    joyVec.x = dx / len * cl; joyVec.y = dy / len * cl;
    knob.style.transform = `translate(${joyVec.x * 34}px, ${joyVec.y * 34}px)`;
  });
  const end = (e) => {
    if (e.pointerId !== pid) return;
    pid = null; joyVec.x = joyVec.y = 0;
    knob.style.transform = '';
  };
  joy.addEventListener('pointerup', end);
  joy.addEventListener('pointercancel', end);
})();

// right-side look drag
renderer.domElement.addEventListener('pointermove', (e) => {
  if (!(walkActive && isTouch)) return;
  if (e.buttons === 0 && e.pointerType === 'mouse') return;
  if (e.clientX < innerWidth * .45) return;   // left half is the stick's
  tYaw -= e.movementX * .006;
  tPitch = Math.min(1.1, Math.max(-.2, tPitch + e.movementY * .004));
});

"""

ADVISOR_JS = """/* ------------------------------------------------ advisor agents -------
   Somebody to ask. Each advisor is one of the Academy's own rigged
   avatars, standing in the room it speaks for, breathing and turning its
   head toward you like any other figure here - and answering a FIXED list
   of questions.

   Nothing is generated. A topic is either a `say` written in the advisor
   registry, or a `read` naming a binding that is resolved HERE against the
   record that already holds the fact - the hall's own condition record,
   the district's own crib, the seat's own walkaround. So the advisor never
   becomes a second copy of anything: change the condition record and the
   safety steward's answer changes with it.

   An advisor is not an instructor and not a gate. No grader reads any of
   this state, and there is nothing here for one to read. */
const ADVISOR_TABLE = D.advisors.who;
let advisorMeshes = [], nearAdvisor = null, curAdvisor = null, curTopic = null;

function advisorCfg(aid, crewSlug) {
  // an advisor wears locker options only - the look is one a learner could
  // also choose, and it takes the crew mark of the hall it stands in
  return { ...D.avatars.defaults, ...ADVISOR_TABLE[aid].crew,
           crew: crewSlug || D.avatars.defaults.crew };
}

function clearAdvisors() {
  for (const m of advisorMeshes) { m.parent?.remove(m); disposeOf(m); }
  advisorMeshes = []; nearAdvisor = null;
  const b = document.getElementById('advBtn');
  if (b) b.style.display = 'none';
}

// A whole rigged avatar is about forty draw calls. Seven of them standing
// in one hall is not worth what it costs at the far end of the room, so an
// advisor carries two bodies: the real one, and a three-box stand-in that
// reads as a person from across the floor. Only one is ever visible, and
// the swap happens well outside conversation range.
const ADV_DETAIL = 20;
function proxyFigure() {
  const g = new THREE.Group();
  const torso = new THREE.Mesh(boxGeo(.44, .62, .26), mat.part);
  torso.position.y = 1.22;
  const legs = new THREE.Mesh(boxGeo(.38, .82, .24), mat.wall);
  legs.position.y = .5;
  const head = new THREE.Mesh(boxGeo(.22, .24, .22), mat.metal);
  head.position.y = 1.66;
  g.add(torso, legs, head);
  return g;
}

function placeAdvisor(aid, parent, x, z, crewSlug) {
  const a = ADVISOR_TABLE[aid];
  if (!a) return null;
  const g = new THREE.Group();
  const body = buildAvatarMesh(advisorCfg(aid, crewSlug));
  const proxy = proxyFigure();
  proxy.visible = false;
  g.add(body, proxy);
  g.position.set(x, .45, z);
  g.rotation.y = Math.atan2(-x, -z);          // face the middle of the room
  g.scale.setScalar(.98);
  g.userData = { advisor: aid, body, proxy };
  const plate = label(a.glyph + '  ' + a.name, a.role, .44,
    { kind: 'advisor' });
  plate.position.set(0, 2.72, 0);
  g.add(plate);
  parent.add(g); advisorMeshes.push(g);
  return g;
}

// the hall: one advisor per room that has one, plus the guide at the door
function spawnHallAdvisors(h, W, DEP) {
  for (const [aid, a] of Object.entries(ADVISOR_TABLE)) {
    // the campus green (dispatcher) and a sim's own yard (operator) are
    // both placed by their own spawners, never as a hall room
    if (a.stands_in === 'green' || a.stands_in === 'yard') continue;
    if (a.stands_in === 'door') { placeAdvisor(aid, hallGroup, 2.6,
      DEP / 2 - 3.2, h.slug); continue; }
    const r = roomRects.find((x) => x.strand === a.stands_in);
    if (!r) continue;                         // not every hall has every room
    const mx = (r.x0 + r.x1) / 2, mz = (r.z0 + r.z1) / 2;
    const len = Math.hypot(mx, mz) || 1;      // stand a step toward the aisle
    placeAdvisor(aid, hallGroup, mx - mx / len * .9, mz - mz / len * .9,
      h.slug);
  }
}

// the campus green: the dispatcher, who speaks for the whole site
function spawnCampusAdvisors() {
  for (const [aid, a] of Object.entries(ADVISOR_TABLE))
    if (a.stands_in === 'green')
      placeAdvisor(aid, campusGroup, 0, 11, null);
}

/* ---- what an advisor is standing near enough to be asked ---------------- */
const ADV_REACH = 4.2;
const _advNear = new THREE.Vector3();
function advisorNear(pos) {
  let best = null, bd = 1e9, v = _advNear;
  for (const m of advisorMeshes) {
    const d = m.getWorldPosition(v).distanceTo(pos);
    if (d < bd) { bd = d; best = m; }
  }
  return bd < ADV_REACH ? best.userData.advisor : null;
}

// Called every frame: offers the nearest advisor while walking, and keeps
// them alive - the same breath and head-turn every other figure here gets,
// so they read as people standing in a room rather than as signage.
const _advV = new THREE.Vector3();
let advBtnEl = null;
function advisorProximity(dt) {
  const btn = advBtnEl ??= document.getElementById('advBtn');
  if (!advisorMeshes.length) { if (nearAdvisor) clearAdvisors(); return; }
  const t = clock.elapsedTime;
  for (const m of advisorMeshes) {
    // the Operator is asked via a button, never approached on foot - a
    // sim's own orbitCam often sits well inside ADV_DETAIL, so distance
    // alone would leave its full ~40-draw-call rigged body on screen for
    // the whole run; it stays low-poly always, the same way it stays
    // reachable without ever needing to be walked up to
    const isOperator = m.userData.advisor === 'operator';
    const near = !isOperator
      && m.getWorldPosition(_advV).distanceTo(eyePos()) < ADV_DETAIL;
    m.userData.body.visible = near;
    m.userData.proxy.visible = !near;
    if (near) idleBreath(m.userData.body, t + m.position.x, dt);
  }
  if (!walkActive) {
    if (nearAdvisor) { nearAdvisor = null; btn.style.display = 'none'; }
    return;
  }
  const here = isTouch && walkAvatar && !xrWalk ? walkAvatar.position : eyePos();
  const who = advisorNear(here);
  if (who === nearAdvisor) return;
  nearAdvisor = who;
  btn.style.display = who ? '' : 'none';
  if (who) btn.textContent = ADVISOR_TABLE[who].glyph + '  Ask the '
    + ADVISOR_TABLE[who].name.toLowerCase();
}

/* ---- resolving a `read` topic against the record that holds the fact ---- */
// the seat bound to a hall, if it has one: bindings are a list because a
// hall can host more than one machine, and the first is the hall's own
function seatOf(sg) {
  const bl = D.sims.bindings[sg];
  return bl && bl.length ? D.sims.sims[bl[0].sim] : null;
}
function advRead(bind, aid) {
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const h = D.halls.find((x) => x.slug === slug);
  // a room-bound answer is about the room this advisor is standing in,
  // never a room picked here: move the steward and the answer moves
  const st = (ADVISOR_TABLE[aid] || {}).stands_in;
  const room = () => h && h.rooms.find((r) => r.strand === st);
  const cond = () => (D.condOver[slug] && D.condOver[slug][st])
    || D.baseCond[st] || D.baseCond.safety;
  const li = (xs) => '<ul>' + xs.map((x) => '<li>' + x + '</li>').join('') + '</ul>';
  const cite = (w) => '<p class="src">' + esc(w) + '</p>';
  switch (bind) {
    case 'conditions.ppe': {
      const c = cond();
      // what this room demands, and then what the floor the trade is
      // actually learned on demands - the second is usually the longer
      // list, and hearing it at the door is the point of the door
      const bay = (D.condOver[slug] && D.condOver[slug].procedure)
        || D.baseCond.procedure;
      const extra = bay.ppe.filter((x) => !c.ppe.includes(x));
      return li(c.ppe.map(esc))
        + (extra.length ? '<h3>And on the practice floor, also</h3>'
            + li(extra.map(esc)) : '')
        + cite('read from this hall\\u2019s own condition records '
          + '(surfaces registry, \\u00a724.2)');
    }
    case 'conditions.hazards': {
      const c = cond();
      return (c.hazards && c.hazards.length
        ? li(c.hazards.map(esc))
        : '<p>None declared for this room \\u2014 which is a statement about '
          + 'the record, not a promise about a real one.</p>')
        + cite('read from this room\\u2019s condition record');
    }
    case 'conditions.env': {
      const c = cond();
      return '<p>' + c.lux + ' lux, ' + c.ach + ' air changes an hour, '
        + c.noise_db + ' dB, ' + c.temp_c[0] + '\\u2013' + c.temp_c[1]
        + ' \\u00b0C.</p>' + cite('read from this room\\u2019s condition record');
    }
    case 'surface.finish': {
      const r = room();
      if (!r) return '<p>That room is not laid out in this hall.</p>';
      const f = D.finCat[D.finishes[slug][r.strand].surface];
      return '<p><b>' + esc(f.name) + '</b> \\u2014 ' + esc(f.why) + '</p>'
        + cite('read from the finishes registry');
    }
    case 'crib.tools': {
      const c = h && D.tools.cribs[h.district];
      if (!c) return '<p>No crib is bound to this hall.</p>';
      return li(c.tools.map((t) => t.glyph + ' <b>' + esc(t.name) + '</b> \\u2014 '
        + esc(t.use))) + cite('read from the toolcrib registry');
    }
    case 'crib.drill':
      return '<p><b>' + esc(D.tools.drill.name) + '</b>, '
        + D.tools.drill.picks + ' picks. ' + esc(D.tools.drill.contract)
        + '</p>' + cite('read from the toolcrib registry');
    case 'sim.walkaround': {
      const s = seatOf(slug);
      if (!s) return '<p>No seat is bound to this hall, so there is nothing '
        + 'to walk before a start.</p>';
      return li(s.walkaround.map((w) => '<b>' + esc(w.point) + '</b> \\u2014 '
        + esc(w.check))) + cite('read from the simulator registry');
    }
    case 'sim.rubric': {
      const s = seatOf(slug);
      if (!s) return '<p>No seat is bound to this hall.</p>';
      return li(s.rubric.map((r) => '<b>' + esc(r.axis) + '</b> \\u2014 '
        + esc(r.measure) + ' (pass ' + esc(r.pass) + ')'))
        + '<p>' + esc(D.sims.honesty) + '</p>'
        + cite('read from the simulator registry');
    }
    // the Operator's own bindings: the ACTUAL running seat (curSimId), not
    // the hall's first bound one - see agents/build.py's header note
    case 'seat.task': {
      const s = D.sims.sims[curSimId];
      if (!s) return '<p>No seat is running.</p>';
      return '<p><b>' + esc(s.name) + '</b></p><p>' + esc(s.task) + '</p>'
        + cite('read from the simulator registry');
    }
    case 'seat.controls': {
      const s = D.sims.sims[curSimId];
      if (!s) return '<p>No seat is running.</p>';
      return li(s.controls.map((c) => '<b>' + esc(c.keys) + '</b> \\u2014 '
        + esc(c.action))) + cite('read from the simulator registry');
    }
    case 'seat.dash': {
      const s = D.sims.sims[curSimId];
      if (!s) return '<p>No seat is running.</p>';
      return li(s.dash.map((g) => '<b>' + esc(g.label) + '</b>'
        + (g.unit ? ' (' + esc(g.unit) + ')' : '')
        + (g.warn_at !== undefined ? ' \\u2014 warns past ' + esc(g.warn_at) : '')))
        + cite('read from the simulator registry');
    }
    case 'seat.rubric': {
      const s = D.sims.sims[curSimId];
      if (!s) return '<p>No seat is running.</p>';
      return li(s.rubric.map((r) => '<b>' + esc(r.axis) + '</b> \\u2014 '
        + esc(r.measure) + ' (pass ' + esc(r.pass) + ')'))
        + '<p>' + esc(D.sims.honesty) + '</p>'
        + cite('read from the simulator registry');
    }
    case 'seat.walkaround': {
      const s = D.sims.sims[curSimId];
      if (!s) return '<p>No seat is running.</p>';
      return li(s.walkaround.map((w) => '<b>' + esc(w.point) + '</b> \\u2014 '
        + esc(w.check))) + cite('read from the simulator registry');
    }
    case 'seat.trade': {
      const s = D.sims.sims[curSimId];
      if (!s) return '<p>No seat is running.</p>';
      return li(s.halls.map((sg) => {
        const hh = D.halls.find((x) => x.slug === sg);
        return '<b>' + esc(hh ? hh.name : sg) + '</b>';
      })) + cite('read from the simulator registry\\u2019s hall bindings');
    }
    case 'seat.procedure': {
      const s = D.sims.sims[curSimId];
      if (!s) return '<p>No seat is running.</p>';
      // the scripted reference operator's own step list - the same ids the
      // page's policy for this seat is written as a switch over
      const op = s.operator;
      return '<ol>' + op.procedure.map((p) => '<li>' + esc(p.step) + '</li>').join('')
        + '</ol><p>At the <b>optimal</b> level this passes <b>'
        + op.guarantees.map(esc).join('</b>, <b>') + '</b> on every regional '
        + 'scenario; ' + op.levels.filter((l) => l !== 'optimal').map(esc).join(' and ')
        + ' are its labelled, seeded degradations.</p><p>'
        + esc(D.sims.operatorHonesty) + '</p>'
        + cite('read from the simulator registry\\u2019s scripted reference operator');
    }
    case 'hall.rooms':
      return li((h ? h.rooms : []).map((r) => '<b>' + esc(r.label) + '</b> \\u2014 '
        + esc(r.purpose))) + cite('read from this hall\\u2019s own layout');
    case 'hall.focus':
      return '<p>' + esc(h ? h.focus : '') + '</p>'
        + cite('read from the hall registry');
    case 'campus.districts': {
      const c = D.campuses[campusKey];
      return li(c.districts.map((k) => '<b>' + esc(D.districts[k].name)
        + '</b> \\u2014 ' + D.districts[k].halls.length + ' halls'))
        + cite('read from the campus registry');
    }
    case 'campus.network':
      return li(D.geo.routes.filter((r) => r.from === campusKey
          || r.to === campusKey)
        .map((r) => '<b>' + esc(D.campuses[r.from === campusKey ? r.to : r.from]
          .name) + '</b> \\u2014 ' + r.km + ' km, bearing ' + r.bearing_deg
          + '\\u00b0'))
        + cite('DERIVED by great circle from the RECORDED coordinates');
    case 'city.anchors': {
      // the citation follows the anchors' OWN real tier - RECORDED where a
      // sibling Locator.X table backs them, AUTHORED where none does (the
      // hub campuses) - never a hardcoded claim
      const cp = D.geo.cityPois[campusKey] || [];
      const allRecorded = cp.length > 0 && cp.every((a) => a.prov === 'RECORDED');
      return li((D.geo.anchors[campusKey] || []).map((a) => '<b>' + esc(a.name)
        + '</b> \\u2014 ' + a.km + ' km, bearing ' + a.bearing_deg + '\\u00b0'))
        + cite(allRecorded ? 'RECORDED anchors, Locator.X (Apache-2.0)'
          : 'AUTHORED anchors, typed from public record \\u2014 not cross-checked against a committed source');
    }
    case 'city.walk': {
      const W = D.advisors.walk, r10 = W.bands_m.ten_minute / 1000;
      const r15 = W.bands_m.fifteen_minute / 1000;
      const an = D.geo.anchors[campusKey] || [];
      const inside = an.filter((a) => a.km <= r15);
      const head = '<p>' + W.pace_note + '.</p>';
      const body = inside.length
        ? li(inside.map((a) => '<b>' + esc(a.name) + '</b> \\u2014 ' + a.km
            + ' km, inside the ' + (a.km <= r10 ? 'ten' : 'fifteen')
            + '-minute band'))
        : '<p>Not one recorded place around this campus is inside the '
          + 'fifteen-minute band \\u2014 the nearest is '
          + (an.length ? esc(an[0].name) + ' at ' + an[0].km + ' km'
             : 'not recorded') + '. This is car territory, and saying so is '
          + 'the useful part.</p>';
      return head + body + '<p class="src">' + esc(W.honesty.straight_line)
        + '</p><p class="src">' + esc(W.honesty.not_a_score) + '</p>';
    }
  }
  return '<p>No binding.</p>';
}

/* ---- the panel --------------------------------------------------------- */
function openAdvisor(aid, topicId) {
  const a = ADVISOR_TABLE[aid];
  if (!a) return;
  curAdvisor = aid; curTopic = topicId || null;
  if (topicId) {
    const tp = a.topics.find((x) => x.id === topicId);
    if (tp) recordEpisode({ kind: 'advisor', campus: campusKey, hall: slug,
      advisor: aid, topic: topicId, answer_kind: tp.kind });
  }
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const t = topicId && a.topics.find((x) => x.id === topicId);
  const answer = !t ? '<p class="focus">' + esc(a.greeting) + '</p>'
    : (t.kind === 'read' ? advRead(t.bind, aid)
       : '<p>' + esc(t.say) + '</p><p class="src">written in '
         + esc(t.cites) + '</p>');
  document.getElementById('pbody').innerHTML =
    '<h2>' + a.glyph + ' ' + esc(a.name) + '</h2>'
    + '<span class="chip">' + esc(a.role) + '</span>'
    + (t ? '<h3>' + esc(t.ask) + '</h3>' : '')
    + answer
    + '<h3>Ask</h3><div class="asks">'
    + a.topics.map((x) => '<button class="opt" data-adv="' + aid
        + '" data-topic="' + x.id + '"' + (t && t.id === x.id
          ? ' style="border-color:var(--mark)"' : '') + '>'
        + esc(x.ask) + '</button>').join('')
    + '</div>'
    + '<p class="src">' + esc(D.advisors.honesty.status) + '</p>'
    + '<p class="src">' + esc(D.advisors.honesty.not_scored) + '</p>'
    + '<p class="src">' + esc(D.advisors.honesty.not_a_person) + '</p>';
  document.body.classList.add('open');
}

document.addEventListener('click', (e) => {
  const b = e.target.closest('[data-adv]');
  if (b) openAdvisor(b.dataset.adv, b.dataset.topic);
});
document.getElementById('advBtn').addEventListener('click', () => {
  if (nearAdvisor) { if (walkActive && plc.isLocked) plc.unlock();
                     openAdvisor(nearAdvisor); }
});
"""

XR_JS = r"""/* ------------------------------------------------------------- WebXR ----
   Experimental, and a viewpoint, not a second world: the same scene, the
   same registries, the same seats and the same graders. What exists here:
   a rig the headset rides in (xrRig, the camera's parent), a local-floor
   reference space with a plain local fallback, AR passthrough (the drawn
   sky, ground, grid and fog banks suppressed around the draw, clear alpha
   0), controller input - thumbsticks, trigger, grip, the two face buttons -
   landing in the same `keys` a keyboard fills, snap-turn locomotion on the
   rig (a comfort default: no smooth rotation), a wrist panel of `readout`
   signs driven by the same gauges() the dash reads, and every seat
   operable in-session through the registry's own `xr` mapping. What does
   NOT exist: hand tracking, rendered hands or a body beyond two schematic
   controllers, and any run on a physical headset - this build proves the
   layer against a mocked WebXR session in headless Chromium only. */
let xrMode = null, vrSupported = false, arSupported = false, xrProbeNote = null;
let xrBlend = 'opaque', xrFloor = true, xrWalk = false, xrWalkKey = null;
const XR_LOCAL_EYE = 1.6;              // rig lift in a plain `local` space
const XR_SNAP = Math.PI / 6;           // 30 degrees a click
const XR_SCALES = [1, .8, .65];        // the framebuffer ladder
const XR_FPS = 60, XR_WINDOW = 3;      // the headset's own budget and window
let xrScaleIdx = 0, xrFov = 0, xrQAcc = 0, xrQFrames = 0, xrQNote = null;
let xrHeadY = XR_LOCAL_EYE;            // the headset's last reported height over the rig
const xrStat = { frames: 0, arHidden: null, lastInput: null, picks: 0 };

async function xrProbe() {
  if (!navigator.xr?.isSessionSupported) {
    xrProbeNote = 'navigator.xr is not offered by this browser'; return;
  }
  for (const [mode, id, set] of [
    ['immersive-vr', 'vrBtn', (v) => { vrSupported = v; }],
    ['immersive-ar', 'arBtn', (v) => { arSupported = v; }]]) {
    try {
      if (await navigator.xr.isSessionSupported(mode)) {
        document.getElementById(id).style.display = '';
        set(true);
      }
    } catch (e) {
      // a refused probe is a fact worth a line, not a silently hidden button
      xrProbeNote = mode + ' probe refused: ' + (e?.message ?? e);
      document.getElementById('hint').textContent = 'XR: ' + xrProbeNote;
    }
  }
}
xrProbe();
function xrSay(msg) {
  document.getElementById('hint').textContent = msg;
  xrHudLines(true);
}
async function xrStart(mode) {
  if (renderer.xr.isPresenting) return null;
  try {
    let session;
    try {
      session = await navigator.xr.requestSession(mode, { requiredFeatures: ['local-floor'] });
      xrFloor = true;
    } catch (e1) {
      session = await navigator.xr.requestSession(mode, { requiredFeatures: ['local'] });
      xrFloor = false;
    }
    renderer.xr.setReferenceSpaceType(xrFloor ? 'local-floor' : 'local');
    renderer.xr.setFramebufferScaleFactor(XR_SCALES[xrScaleIdx]);
    xrMode = mode;
    xrBlend = session.environmentBlendMode ?? 'opaque';
    xrHeadY = xrFloor ? XR_LOCAL_EYE : 0;
    session.addEventListener('end', xrEnded);
    // the controllers exist before the session does: three.js maps input
    // sources onto controllers it already knows at the change event
    xrCtlBuild();
    await renderer.xr.setSession(session);
    xrBegan();
    return session;
  } catch (e) {
    xrMode = null;
    xrSay('XR session unavailable: ' + (e?.message ?? e));
    return null;
  }
}
document.getElementById('vrBtn').addEventListener('click', () => xrStart('immersive-vr'));
document.getElementById('arBtn').addEventListener('click', () => xrStart('immersive-ar'));

function xrBegan() {
  key.castShadow = false;                        // shadows off in a headset by default
  if (xrBlend !== 'opaque') renderer.setClearAlpha(0);
  xrCtlBuild();
  xrHudBuild();
  walkLeave();
  if (sim) {
    if (simView === 'orbit') {
      const oc = sim.orbitCam;
      xrOrbitPlace(oc?.pos ?? [36, 28, 42], oc?.tgt ?? [0, 11, 0]);
    }
  } else if (['hall', 'campus', 'restoration'].includes(view)) {
    xrWalkStart();
  } else {
    // the region board, the locker: the rig stands where the camera was
    xrRig.position.set(camera.position.x, camera.position.y - xrHeadY, camera.position.z);
    xrRig.rotation.set(0, 0, 0); camera.position.set(0, 0, 0);
  }
  xrSay((xrMode === 'immersive-ar' ? 'AR' : 'VR') + ' session · '
    + (xrFloor ? 'local-floor space' : 'local space - rig lifted ' + XR_LOCAL_EYE + ' m, no floor tracking')
    + ' · ' + xrBlend + ' · left stick walks, right stick snaps 30°, B/Y leaves');
}
// presenting, and not on the way out: the session's 'end' event reaches
// this page's listener BEFORE three.js's own (registered later, in
// setSession), so inside xrEnded renderer.xr.isPresenting still reads true
// - anything that would re-place the rig for a headset must ask this instead
function xrLive() { return renderer.xr.isPresenting && xrMode !== null; }
// lift every key the controller adapter wrote and forget its edge cache: at
// session end (a stick held as the session ends must not keep driving the
// seat from a headset that is gone) and when a seat is torn down (the next
// seat starts from a clean cache, so a stick still held registers again).
// The face-button latches are NOT touched here: a seat is torn down by the
// A/X and B/Y presses themselves, and clearing the latch under a press
// still held would re-fire its rising edge on the very next frame
function xrPadRelease() {
  for (const kk in xrPad.edge) if (xrPad.edge[kk]) keys[kk] = false;
  xrPad.edge = {};
}
function xrEnded() {
  xrMode = null; xrBlend = 'opaque';
  xrPadRelease();
  xrPad.trig = xrPad.lTrig = xrPad.grip = xrPad.a = xrPad.b = false;   // no session: nothing is held
  renderer.setClearAlpha(1);
  key.castShadow = qLevel !== 'low';
  xrHudClear();
  if (xrWalk) walkEnded();
  else if (sim) {
    xrRig.position.set(0, 0, 0); xrRig.rotation.set(0, 0, 0);
    if (simView === 'orbit') setSimView('orbit');
  } else rigCollapse();
  document.getElementById('hint').textContent = 'XR session ended';
}
// fold the rig into the camera: the camera keeps its world pose, the rig
// returns to the identity, and every desktop control sees the camera alone
const _rcP = new THREE.Vector3(), _rcQ = new THREE.Quaternion();
function rigCollapse() {
  camera.getWorldPosition(_rcP); camera.getWorldQuaternion(_rcQ);
  xrRig.position.set(0, 0, 0); xrRig.rotation.set(0, 0, 0); xrRig.updateMatrixWorld(true);
  camera.position.copy(_rcP); camera.quaternion.copy(_rcQ);
}

/* ---- walking in a headset: the rig is the body ------------------------ */
function xrWalkStart() {
  const [sx, sz] = walkSpawn();
  xrWalk = true; walkActive = true;
  controls.enabled = false; controls.autoRotate = false;
  xrRig.position.set(sx, xrFloor ? 0 : XR_LOCAL_EYE, sz);
  xrRig.rotation.set(0, Math.atan2(sx, sz), 0);          // facing the origin
  xrWalkKey = view + ':' + slug + ':' + (curRestoSite?.id ?? '');
  document.getElementById('cross').style.display = 'none';
  document.getElementById('hint').textContent = t('hint.walk');
  nearSlug = null; nearPoi = null; nearTrack = null;
}
const _xf = new THREE.Vector3(), _xr = new THREE.Vector3(), _xh = new THREE.Vector3();
// smooth locomotion on the left stick, relative to where the head looks;
// a snap turn on the right stick, about the head, re-armed near centre
function xrMove(dt) {
  const [lx, ly] = xrPad.l, mag = Math.hypot(lx, ly);
  if (mag > .15) {
    camera.getWorldDirection(_xf); _xf.y = 0; _xf.normalize();
    _xr.set(-_xf.z, 0, _xf.x);
    const sp = 3 * dt * Math.min(1, mag);
    xrRig.position.addScaledVector(_xf, -ly * sp).addScaledVector(_xr, lx * sp);
  }
  const rx = xrPad.r[0];
  if (xrPad.snapArmed && Math.abs(rx) > .6) { xrSnap(-Math.sign(rx) * XR_SNAP); xrPad.snapArmed = false; }
  else if (Math.abs(rx) < .3) xrPad.snapArmed = true;
}
function xrSnap(a) {
  camera.getWorldPosition(_xh);
  xrRig.rotation.y += a; xrRig.updateMatrixWorld(true);
  const after = camera.getWorldPosition(_xf);
  xrRig.position.add(_xh.sub(after));            // the head stays put
}
// per-frame housekeeping while presenting: a view change under a walking
// rig (a door entered, the campus button, a seat left) re-places the walker
// at that view's spawn; a seat or the board takes the rig for itself
function xrFrame(dt) {
  xrStat.frames++;
  xrHeadY = camera.position.y;
  const onFoot = !sim && ['hall', 'campus', 'restoration'].includes(view);
  if (onFoot) {
    const k = view + ':' + slug + ':' + (curRestoSite?.id ?? '');
    if (!xrWalk || k !== xrWalkKey) xrWalkStart();
  } else if (xrWalk) { xrWalk = false; walkActive = false; }
  if (xrHud.fallback) xrHud.group.position.set(0, xrHeadY - .3, -.6);
  xrHudLines(false);
}

/* ---- the controller adapter ------------------------------------------ */
const xrPad = { l: [0, 0], r: [0, 0], trig: false, lTrig: false, grip: false,
                a: false, b: false, snapArmed: true, edge: {} };
function xrInput(dt) {
  const ses = renderer.xr.getSession(); if (!ses) return;
  let L = null, R = null;
  for (const src of ses.inputSources ?? []) {
    const gp = src.gamepad; if (!gp) continue;
    if (src.handedness === 'left') L = gp;
    else if (src.handedness === 'right') R = gp;
    else if (!R) R = gp;
  }
  // xr-standard mapping: axes 2/3 are the thumbstick (0/1 a touchpad),
  // buttons 0 trigger, 1 squeeze, 4 A/X, 5 B/Y
  const stick = (gp) => !gp ? [0, 0]
    : gp.axes.length >= 4 ? [gp.axes[2] || 0, gp.axes[3] || 0] : [gp.axes[0] || 0, gp.axes[1] || 0];
  const btn = (gp, i) => !!gp?.buttons?.[i]?.pressed;
  xrPad.l = stick(L); xrPad.r = stick(R);
  const trig = btn(R, 0), lTrig = btn(L, 0), grip = btn(R, 1) || btn(L, 1);
  const a = btn(R, 4) || btn(L, 4), b = btn(R, 5) || btn(L, 5);
  const rose = (name, now) => { const was = xrPad[name]; xrPad[name] = now; return now && !was; };
  const DZ = .5;
  if (sim) {
    // the seat's own mapping, declared once in the registry: sticks to the
    // W/S/A/D and Q/E verbs, grip to the seat's secondary edge key
    const map = D.sims.sims[curSimId].xr;
    const [lx, ly] = xrPad.l, [rx] = xrPad.r;
    const want = { KeyW: ly < -DZ, KeyS: ly > DZ, KeyA: lx < -DZ, KeyD: lx > DZ,
                   KeyQ: rx < -DZ, KeyE: rx > DZ };
    if (map.grip_key) want[map.grip_key] = grip;
    // written on change only, so a keyboard beside the headset still counts
    for (const kk in want) if (want[kk] !== xrPad.edge[kk]) { keys[kk] = want[kk]; xrPad.edge[kk] = want[kk]; }
    // the Space verb, on the press edge - and the operator's while it drives
    if (rose('trig', trig) && !opRun) sim.action?.();
    xrPad.grip = grip;
    if (rose('a', a)) xrWatchToggle();
    if (rose('b', b)) exitSim();
  } else {
    xrPad.trig = trig; xrPad.grip = grip; xrPad.a = a;
    if (rose('b', b)) ses.end();
  }
  if (rose('lTrig', lTrig)) xrPickLeft();
  xrStat.lastInput = { l: xrPad.l, r: xrPad.r, trig, lTrig, grip, a, b };
}
// the A/X button: start watching the scripted reference operator at the
// level the HUD last selected, or take the seat back - the same restart
// the HUD's watch button does
function xrWatchToggle() {
  if (!sim) return;
  const id = curSimId, sc = curScenario?.id;
  if (opRun) { startSim(id, sc); xrSay('the seat is yours again'); return; }
  const level = document.getElementById('opLvl').value || 'optimal';
  startSim(id, sc); opAttach(level, 1, false);
}
// the left ray picks whatever a click would: a clipboard, an advisor, a
// station, a door
const _xrM = new THREE.Matrix4();
function xrPickLeft() {
  const ctl = xrCtl.rays.left; if (!ctl) return;
  _xrM.identity().extractRotation(ctl.matrixWorld);
  ray.ray.origin.setFromMatrixPosition(ctl.matrixWorld);
  ray.ray.direction.set(0, 0, -1).applyMatrix4(_xrM);
  ray.camera = camera;                 // sprites (labels) raycast against a camera
  xrStat.picks++;
  pickWith(ray);
}

/* ---- two schematic controllers, and the left hand's ray --------------- */
const xrCtl = { built: false, grips: [], rays: {}, hands: {} };
function xrCtlBuild() {
  if (xrCtl.built) return; xrCtl.built = true;
  const body = new THREE.MeshStandardMaterial({ color: 0x2c3639, roughness: .7 });
  const ring = new THREE.MeshStandardMaterial({ color: 0x41C4D4, roughness: .5, emissive: 0x0e3a40 });
  for (let i = 0; i < 2; i++) {
    const grip = renderer.xr.getControllerGrip(i);
    const handle = new THREE.Mesh(new THREE.CylinderGeometry(.015, .018, .1, 12), body);
    handle.rotation.x = -Math.PI / 2 + .35; handle.position.set(0, -.02, .04);
    const halo = new THREE.Mesh(new THREE.TorusGeometry(.03, .004, 8, 24), ring);
    halo.rotation.x = Math.PI / 2; halo.position.set(0, .01, -.03);
    grip.add(handle); grip.add(halo);
    xrRig.add(grip);
    const ctl = renderer.xr.getController(i);
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(
      [new THREE.Vector3(), new THREE.Vector3(0, 0, -2)]),
      new THREE.LineBasicMaterial({ color: 0xE8A33D, transparent: true, opacity: .6 }));
    line.visible = false; ctl.add(line); xrRig.add(ctl);
    ctl.addEventListener('connected', (e) => {
      const h = e.data?.handedness ?? 'none';
      xrCtl.hands[i] = h; grip.userData.hand = h;
      if (h === 'left') { xrCtl.rays.left = ctl; line.visible = true; xrHudMount(grip); }
    });
    ctl.addEventListener('disconnected', () => {
      if (xrCtl.hands[i] === 'left') { xrCtl.rays.left = null; line.visible = false; xrHudMount(null); }
      xrCtl.hands[i] = null;
    });
    xrCtl.grips.push(grip);
  }
}

/* ---- the wrist panel: readout signs off the same gauges as the dash --- */
const xrHud = { group: new THREE.Group(), sprites: {}, texts: {}, last: 0,
                lastLines: 0, mounted: null, fallback: false };
xrHud.group.name = 'xr-wrist-panel';
function xrHudBuild() { if (!xrHud.mounted) xrHudMount(null); }
function xrHudMount(grip) {
  if (xrHud.group.parent) xrHud.group.parent.remove(xrHud.group);
  if (grip) {
    grip.add(xrHud.group); xrHud.group.position.set(0, .05, .1);
    xrHud.fallback = false; xrHud.mounted = 'left-grip';
  } else {
    // no left controller: a panel 0.6 m ahead of the rig, 0.3 m below the eye
    xrRig.add(xrHud.group); xrHud.group.position.set(0, xrHeadY - .3, -.6);
    xrHud.fallback = true; xrHud.mounted = 'rig';
  }
}
function xrHudDrop(slot) {
  const sp = xrHud.sprites[slot]; if (!sp) return;
  // its map is a shared label texture: released through the cache, not disposed here
  xrHud.group.remove(sp); lblTexRelease(sp.userData.lbl?.texKey); sp.material.dispose();
  delete xrHud.sprites[slot]; delete xrHud.texts[slot];
}
function xrHudClear() { for (const k of Object.keys(xrHud.sprites)) xrHudDrop(k); }
// a sign is redrawn only when its text changes - the canvas is the cost
function xrHudSprite(slot, text, sub, scale, warn) {
  const k = text + '' + (sub ?? '') + (warn ? '!' : '');
  if (xrHud.texts[slot] === k) return xrHud.sprites[slot];
  xrHudDrop(slot);
  const sp = label(text, sub, scale, { kind: 'readout', accent: warn ? LPAL.crit : undefined });
  const i = labelSet.indexOf(sp); if (i >= 0) labelSet.splice(i, 1);   // on the hand: not view-scored
  sp.material.opacity = 1; sp.renderOrder = 10;
  xrHud.group.add(sp); xrHud.sprites[slot] = sp; xrHud.texts[slot] = k;
  return sp;
}
function setXRDash(def, vals) {
  if (!renderer.xr.isPresenting) return;
  const now = performance.now();
  if (now - xrHud.last < 150) return;
  xrHud.last = now;
  const per = 4;
  for (let i = 0; i < def.dash.length; i++) {
    const g = def.dash[i];
    const x = vals[g.id]; if (x === undefined) continue;
    const v = typeof x === 'object' ? x.v : x;
    const warn = g.warn_at !== undefined && v >= g.warn_at;
    const sp = xrHudSprite('g:' + g.id, (warn ? '▲ ' : '') + gaugeText(x),
      g.label + (g.unit ? ' ' + g.unit : ''), .045, warn);
    sp.position.set((i % per - (per - 1) / 2) * .08, -.07 - Math.floor(i / per) * .06, 0);
  }
}
function xrOpStatus() {
  if (!sim) return null;
  if (!opRun || opRun.sweep) return 'your hands on the seat';
  const proc = opRun.def.operator.procedure, p = proc[opRun.m.phase];
  return 'reference operator · ' + opRun.level + ' · '
    + (opRun.result ? 'done' : 'watching')
    + (p && !opRun.result ? ' · ' + (opRun.m.phase + 1) + '/' + proc.length + ' ' + p.step.slice(0, 48) : '');
}
function xrHudLines(force) {
  if (!renderer.xr.isPresenting) return;
  const now = performance.now();
  if (!force && now - xrHud.lastLines < 250) return;
  xrHud.lastLines = now;
  const hint = (document.getElementById('hint').textContent || '').slice(0, 72);
  xrHudSprite('hint', hint || '–', null, .04, false).position.set(0, .06, 0);
  const op = xrOpStatus();
  if (op) xrHudSprite('op', op, null, .04, false).position.set(0, 0, 0);
  else xrHudDrop('op');
}

/* ---- the draw: passthrough, and the headset's own quality ladder ------ */
const _bankVis = [];
function xrRender() {
  if (renderer.xr.isPresenting && xrBlend !== 'opaque') {
    // passthrough: the drawn sky, the ground disc, the grid and the fog
    // banks would paint over the room. They are hidden around the draw
    // only, so every view change that sets them stays exactly as written.
    const bg = scene.background, fn = scene.fog.near, ff = scene.fog.far;
    const gv = ground.visible, grv = grid.visible, banks = _bankVis;
    banks.length = fogBanks.length;
    for (let i = 0; i < fogBanks.length; i++) {
      banks[i] = fogBanks[i].m.visible; fogBanks[i].m.visible = false;
    }
    scene.background = null; scene.fog.near = 1e6; scene.fog.far = 2e6;
    ground.visible = false; grid.visible = false;
    xrStat.arHidden = { sky: scene.background === null, ground: !ground.visible,
      grid: !grid.visible, fogFar: scene.fog.far, banks: banks.length,
      clearAlpha: renderer.getClearAlpha() };
    renderer.render(scene, camera);
    scene.background = bg; scene.fog.near = fn; scene.fog.far = ff;
    ground.visible = gv; grid.visible = grv;
    for (let i = 0; i < fogBanks.length; i++) fogBanks[i].m.visible = banks[i];
    return;
  }
  xrStat.arHidden = null;
  renderer.render(scene, camera);
}
function xrQStep(dt) {
  if (!renderer.xr.isPresenting || navigator.webdriver) return;
  xrQAcc += dt; xrQFrames++;
  if (xrQAcc >= XR_WINDOW) {
    const fps = xrQFrames / xrQAcc;
    if (fps < XR_FPS) xrQDrop(fps);
    xrQAcc = 0; xrQFrames = 0;
  }
}
// the ladder, honestly: three.js r160 cannot resize the XR framebuffer
// while presenting (setFramebufferScaleFactor only warns), so a scale step
// is recorded here and applied when the next session starts; in-session
// the live levers are fixed foveation (setFoveation applies at once) and
// the fog banks
function xrQDrop(fps) {
  if (xrFov < 1) {
    xrFov = Math.min(1, xrFov + .5); renderer.xr.setFoveation(xrFov);
    for (const b of fogBanks) b.m.visible = false;
  } else if (xrScaleIdx < XR_SCALES.length - 1) xrScaleIdx++;
  else return;
  xrQNote = 'XR performance: ' + Math.round(fps) + ' fps · foveation ' + xrFov
    + ' · framebuffer scale ' + XR_SCALES[xrScaleIdx]
    + (xrScaleIdx ? ' (applied at the next session start)' : '');
  xrSay(xrQNote);
}
// what a harness can read and drive - the layer is proven against a mocked
// session, and this is the surface it reads
window.__tc3dXR = {
  start: xrStart,
  end: () => renderer.xr.getSession()?.end(),
  presenting: () => renderer.xr.isPresenting,
  forceQ: (fps) => xrQDrop(fps),
  state: () => ({ mode: xrMode, blend: xrBlend, floor: xrFloor, walk: xrWalk,
    walkKey: xrWalkKey, probe: xrProbeNote, scale: XR_SCALES[xrScaleIdx],
    foveation: xrFov, qNote: xrQNote, frames: xrStat.frames, picks: xrStat.picks,
    arHidden: xrStat.arHidden, clearAlpha: renderer.getClearAlpha(),
    shadows: key.castShadow, refSpace: xrFloor ? 'local-floor' : 'local',
    hud: { mounted: xrHud.mounted, fallback: xrHud.fallback,
      sprites: Object.keys(xrHud.sprites), texts: { ...xrHud.texts },
      at: xrHud.group.getWorldPosition(new THREE.Vector3()).toArray().map((v) => Math.round(v * 100) / 100) },
    hands: { ...xrCtl.hands }, ctlBuilt: xrCtl.built,
    rig: xrRig.position.toArray().map((v) => Math.round(v * 1000) / 1000),
    rigYaw: Math.round(xrRig.rotation.y * 1000) / 1000,
    head: camera.position.toArray().map((v) => Math.round(v * 1000) / 1000),
    eye: eyePos().toArray().map((v) => Math.round(v * 1000) / 1000),
    input: xrStat.lastInput }),
};"""

page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>SmartCiti.X : Trade Craft Academy — 3D hall environment</title>
<style>
:root{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
  --good:#5CB584; --crit:#E07C68;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.5 "IBM Plex Sans",system-ui,sans-serif;overflow:hidden}
#bar{position:fixed;top:0;left:0;right:0;z-index:5;display:flex;flex-wrap:wrap;
  gap:8px 14px;align-items:center;padding:10px 16px;
  background:color-mix(in oklab, var(--plate) 86%, transparent);
  border-bottom:2px solid var(--mark);backdrop-filter:blur(6px)}
#bar .brand{font:700 19px/1 "Barlow Condensed",system-ui,sans-serif;white-space:nowrap}
#bar .brand .x{color:var(--mark)}
#bar a{color:var(--steel);text-decoration:none;font-size:13px;white-space:nowrap}
select{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:6px 9px;font:inherit;max-width:46vw}
#lang{margin-inline-start:auto}
.barbtn{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:6px 11px;font:inherit;cursor:pointer;white-space:nowrap}
.barbtn:hover{border-color:var(--mark)}
#cross{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:6;
  color:var(--mark);font:400 26px/1 "IBM Plex Mono",monospace;display:none;
  pointer-events:none;text-shadow:0 0 6px rgba(0,0,0,.8)}
#hud{position:fixed;left:16px;bottom:14px;z-index:5;max-width:min(430px,86vw);
  background:color-mix(in oklab, var(--panel) 90%, transparent);
  border:1px solid var(--rule);border-radius:9px;padding:10px 14px}
#hud h2{font:600 20px "Barlow Condensed",sans-serif;margin:0}
#hud .focus{color:var(--muted);font-size:12.5px;margin:2px 0 0}
#hud .hint{color:var(--muted);font-size:11.5px;margin:6px 0 0}
#honesty{position:fixed;right:16px;bottom:14px;z-index:5;max-width:300px;
  color:var(--muted);font-size:10.5px;text-align:end;opacity:.85}
#dash{position:fixed;left:50%;bottom:14px;transform:translateX(-50%);z-index:6;
  display:none;gap:2px;background:color-mix(in oklab, var(--sunk) 90%, transparent);
  border:1px solid var(--rule);border-radius:10px;padding:8px 14px;
  backdrop-filter:blur(6px)}
#dash .g{min-width:66px;text-align:center;border-inline-start:1px solid var(--rule);
  padding:0 9px}
#dash .g:first-child{border-inline-start:none}
#dash .gv{display:block;font:600 21px/1.2 "IBM Plex Mono",monospace}
#dash .gl{display:block;color:var(--muted);font-size:10px;letter-spacing:.06em;
  text-transform:uppercase;margin-top:2px}
#dash .g.warn .gv{color:var(--crit)}
/* warning is shape AND colour, never colour alone (colourblind-safe) */
#dash .g.warn .gl::before{content:"\\25b2  ";color:var(--crit)}
/* the minimap: the campus from above, you as the amber arrow */
#mm{position:fixed;right:14px;top:62px;z-index:5;border:1px solid var(--rule);
  border-radius:9px;width:150px;height:150px}
@media(pointer:coarse){#mm{width:110px;height:110px;top:auto;bottom:200px}}
/* the thumb wheel: radial options sized for a phone thumb */
#wheelWrap{position:fixed;left:50%;bottom:10px;transform:translateX(-50%);
  z-index:7;display:flex;flex-direction:column;align-items:center;gap:6px}
#wheelTabs{display:flex;gap:4px;flex-wrap:wrap;justify-content:center;
  max-width:min(92vw,360px)}
.wtab{background:var(--panel);border:1px solid var(--rule);border-radius:999px;
  min-width:40px;min-height:40px;font-size:18px;cursor:pointer;padding:2px}
.wtab.on{border-color:var(--mark);box-shadow:0 0 0 1px var(--mark)}
#wheel{width:min(64vw,250px);height:min(64vw,250px);
  filter:drop-shadow(0 4px 14px rgba(0,0,0,.5))}
#wheel path{cursor:pointer}
/* touch-walk controls */
#joy{position:fixed;left:18px;bottom:22px;z-index:7;width:112px;height:112px;
  border-radius:50%;background:color-mix(in oklab, var(--panel) 70%, transparent);
  border:1px solid var(--rule);touch-action:none}
#knob{position:absolute;left:50%;top:50%;width:52px;height:52px;margin:-26px;
  border-radius:50%;background:var(--panel);border:2px solid var(--mark)}
.fab{position:fixed;right:18px;bottom:22px;z-index:7;min-width:56px;
  min-height:56px;border-radius:999px;background:var(--panel);color:var(--ink);
  border:1px solid var(--rule);font:inherit;font-size:24px;cursor:pointer}
.fab.wide{right:18px;bottom:90px;font-size:14px;padding:0 16px;max-width:60vw;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
@media(pointer:coarse){
  .barbtn,select{min-height:42px}
  #hud{max-width:min(300px,72vw);padding:8px 11px}
  #hud h2{font-size:17px}
  #honesty{display:none}
  /* keep the wheel clear of the thumb-stick while walking */
  #wheelWrap{left:auto;right:10px;transform:none;bottom:150px}
}
canvas{display:block}
#nogl{display:none;position:fixed;inset:0;place-content:center;text-align:center;
  color:var(--muted);padding:40px}
/* station panel */
#ov{position:fixed;inset:0;background:rgba(6,10,12,.7);display:none;z-index:9}
#panel{position:fixed;top:0;inset-inline-end:0;bottom:0;width:min(480px,100%);
  background:var(--panel);border-inline-start:1px solid var(--rule);z-index:10;
  transform:translateX(105%);transition:transform .22s ease;overflow-y:auto;
  padding:20px 22px 40px}
html[dir="rtl"] #panel{transform:translateX(-105%)}
body.open #ov{display:block}
body.open #panel{transform:none}
#panel h2{font:600 22px "Barlow Condensed",sans-serif;margin:2px 0 4px;
  padding-inline-end:70px}
#panel .chip{display:inline-block;border:1px solid var(--rule);border-radius:999px;
  padding:2px 10px;font-size:12px;color:var(--muted);margin:0 4px 10px 0}
#panel h3{font:600 14px "Barlow Condensed",sans-serif;letter-spacing:.04em;
  text-transform:uppercase;color:var(--steel);margin:16px 0 6px}
#panel ul{margin:4px 0;padding-inline-start:20px;color:var(--muted)}
#pclose{position:absolute;top:12px;inset-inline-end:14px;background:none;
  border:1px solid var(--rule);color:var(--muted);border-radius:6px;
  padding:5px 11px;cursor:pointer;font:inherit}
.q{background:var(--sunk);border-radius:6px;padding:9px 12px;margin-top:8px}
.q .opt{display:block;background:none;border:1px solid var(--rule);color:var(--ink);
  border-radius:5px;padding:6px 9px;margin:5px 0;cursor:pointer;font:inherit;
  width:100%;text-align:start}
.q .opt.ok{border-color:var(--good);color:var(--good)}
.q .opt.bad{border-color:var(--crit);color:var(--crit)}
#panel p.src{color:var(--muted);font-size:11px;margin:6px 0 0}
.asks{display:flex;flex-direction:column;gap:4px}
.asks .opt{background:var(--sunk);border:1px solid var(--rule);color:var(--ink);border-radius:6px;padding:8px 10px;cursor:pointer;font:inherit;text-align:start;min-height:40px}
.asks .opt:hover{border-color:var(--mark)}
#advBtn{right:18px;bottom:158px}
@media(prefers-reduced-motion:reduce){#panel{transition:none}}
</style>
</head>
<body>
<div id="bar">
  <span class="brand">SmartCiti<span class="x">.X</span> : Trade Craft Academy</span>
  <a href="trade_craft_interactive.html" id="back"></a>
  <select id="hall" aria-label="hall"></select>
  <button id="regionBtn" class="barbtn"></button>
  <button id="campusBtn" class="barbtn"></button>
  <button id="walkBtn" class="barbtn"></button>
  <button id="simBtn" class="barbtn"></button>
  <button id="avaBtn" class="barbtn"></button>
  <button id="camBtn" class="barbtn" style="display:none"></button>
  <button id="sndBtn" class="barbtn" style="display:none"></button>
  <button id="opBtn" class="barbtn" style="display:none"></button>
  <button id="dnBtn" class="barbtn" aria-label="day / night">🌙</button>
  <button id="recBtn" class="barbtn" aria-label="records">⏱</button>
  <button id="orbisBtn" class="barbtn" aria-label="Orbis synthetic-training prompt">🎬</button>
  <button id="schoolsBtn" class="barbtn" aria-label="schools flipped-classroom program">🎓</button>
  <button id="restorationBtn" class="barbtn" aria-label="Bay Restoration sites and training tracks">🌊</button>
  <button id="vrBtn" class="barbtn" style="display:none">🥽 VR</button>
  <button id="arBtn" class="barbtn" style="display:none">📱 AR</button>
  <button id="satBtn" class="barbtn" style="display:none">🛰️</button>
  <button id="glbBtn" class="barbtn" style="display:none">⬇ .glb</button>
  <button id="glbInBtn" class="barbtn" style="display:none">＋ .glb</button>
  <input id="glbFile" type="file" accept=".glb,.gltf" style="display:none">
  <select id="lang"></select>
</div>
<div id="wheelWrap" style="display:none">
  <div id="wheelTabs"></div>
  <svg id="wheel" viewBox="0 0 200 200" role="listbox" aria-label="options"></svg>
</div>
<div id="joy" style="display:none"><div id="knob"></div></div>
<button id="emoBtn" class="fab" style="display:none">😀</button>
<button id="advBtn" class="fab wide" style="display:none"></button>
<button id="actBtn" class="fab wide" style="display:none"></button>
<div id="hud"><h2 id="hname"></h2><p class="focus" id="hfocus"></p><p class="hint" id="hint"></p>
  <p class="hint" id="opCtl" style="display:none">🤖 scripted reference operator
    <select id="opLvl" aria-label="operator level" style="padding:2px 6px;font-size:11.5px"></select>
    <button id="opRefBtn" class="barbtn" style="padding:2px 8px;font-size:11.5px">▶ watch it drive</button></p></div>
<canvas id="mm" width="150" height="150" style="display:none"></canvas>
<div id="dash"></div>
<div id="honesty"></div>
<div id="nogl"></div>
<div id="cross">+</div>
<div id="ov"></div>
<aside id="panel"><button id="pclose"></button><div id="pbody"></div></aside>
<script id="data" type="application/json">__DATA__</script>
<script type="importmap">
{"imports":{
  "three":"./vendor/three.module.min.js",
  "three/addons/":"./vendor/addons/"
}}
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const D = JSON.parse(document.getElementById('data').textContent);
// inflate the deduped payload: rooms from the per-depth layout and the
// per-strand defs, finishes from the 12 distinct maps - one truth per
// fact on the wire, the full shape everywhere downstream
for (const h of D.halls) {
  h.rooms = D.layouts[h.lay].map((r) => ({
    ...r, label: D.roomDefs[r.strand].label,
    purpose: D.roomDefs[r.strand].purpose,
    fixtures: h.fixtures?.[r.strand] ?? [] }));
}
D.finishes = Object.fromEntries(Object.entries(D.finIdx)
  .map(([sl, i2]) => [sl, D.finMaps[i2]]));
D.walls = Object.fromEntries(Object.entries(D.wallIdx)
  .map(([sl, i2]) => [sl, D.wallMaps[i2]]));
D.avatars.characters = D.avatars.characters.map((c) => ({
  ...c, cfg: { ...D.avatars.defaults, ...c.d } }));
D.avatars.tradeapes.apes = D.avatars.tradeapes.apes.map((a) => ({
  ...a, name: 'TradeApe ' + a.code,
  cfg: { ...D.avatars.defaults, ...a.d, crew: a.hall } }));
const params = new URLSearchParams(location.search);
let loc = D.i18n[params.get('lang')] ? params.get('lang') : 'en';
let slug = D.halls.some(h => h.slug === params.get('hall')) ? params.get('hall') : 'bricklayers';
let view = 'region';
const t = (k) => D.i18n[loc].strings[k] ?? D.i18n.en.strings[k] ?? k;
const U = 3;                       // metres per grid unit
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ------------------------------------------------------------- scene ---- */
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true });
} catch (e) {
  document.getElementById('nogl').style.display = 'grid';
  document.getElementById('nogl').textContent =
    'WebGL is unavailable in this browser; the 3D environment needs it. ' +
    'The interactive map carries the same content in 2D.';
  throw e;
}
// mobile budget: cap the pixel ratio and drop shadow maps on touch GPUs
renderer.setPixelRatio(Math.min(devicePixelRatio,
  ('ontouchstart' in window) ? 1.5 : 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = !('ontouchstart' in window);
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.12;
renderer.xr.enabled = true;
document.body.appendChild(renderer.domElement);

/* WebXR - experimental: the buttons appear only where the platform
   actually offers the session kind, and a refused session degrades to a
   HUD line, never an error. The same scene, the same registries; XR is
   a viewpoint, not a second world. */
/* Adaptive quality: when the frame rate stays under budget the page
   steps itself down ONCE - pixel ratio to 1, the sun stops casting
   shadows, the fog banks rest - and says so in the HUD. Manual override
   via the __tc3dDo hook; reduced-motion users are already served. */
let qLevel = 'high', qAuto = true, qAcc = 0, qFrames = 0;
// declared up here because setQuality() below reads it and the ladder can
// fire before the first hall is ever built
let roomLights = [];

/* Candela, not "brightness".
   three.js r155 flipped `useLegacyLights` to false and r160 removed the
   legacy path, so a PointLight's intensity is now CANDELA and its
   contribution falls off as I / r^decay. Every luminaire in this bundle was
   first written with legacy-scale numbers (0.5 - 2.6), which at a 2.7 m
   ceiling or an 8.7 m mast head is indistinguishable from no light at all:
   measured on a hall interior, cranking them 60x took the scene from a mean
   luminance of 46 to 96 out of 255. They WERE real lights and they DID vary
   with the registry's lux - they just were not lighting anything, which is
   the same near-miss as an emissive box that only looks like a lamp.

   `lampCd` converts a relative brightness into the candela that delivers it
   at the height the fitting is actually mounted at. One conversion, so a
   lamp cannot be bright in one room and invisible in the next. */
const LAMP_K = 11;
const lampCd = (rel, height_m, decay) => rel * Math.pow(height_m, decay) * LAMP_K;
function setQuality(l) {
  qLevel = l;
  renderer.setPixelRatio(l === 'low' ? 1
    : Math.min(devicePixelRatio, isTouch ? 1.5 : 2));
  key.castShadow = l !== 'low';
  for (const b of fogBanks) b.m.visible = l !== 'low';
  // the per-room lights are on the same budget the shadows and the fog
  // banks are on: a device that cannot afford the ladder's top rung does
  // not pay eleven point lights for it either. Coming back UP hands the
  // choice to roomLitStep rather than lighting all eleven and leaving them.
  for (const rl of roomLights) rl.visible = l !== 'low';
  _rlDirty = true;
}
/* Eleven point lights, and a walker stands in one room.
   A forward renderer costs every fragment for every light in range, and a
   hall carries one per room. Measured on this page with the camera inside
   the ironworkers hall, holding everything else constant:

     11 room lights lit   1.24 fps      (software raster, so read the ratio)
      4 lit               1.64 fps      +32%
      0 lit               2.06 fps      +66%

   So the hall lights the few rooms nearest the eye and douses the rest.
   The doused ones do not go black - the hall's hemisphere and the sun still
   reach them - they simply stop costing a per-fragment light each. Only the
   hall's OWN room lights are culled: a yard's masts and its hemisphere are
   its whole lighting rig and are left alone.

   It re-evaluates on movement, not every frame: sorting eleven lights on a
   camera that has not moved is work for nothing. */
const ROOM_LIT_MAX = 4;
const _rlEye = new THREE.Vector3(), _rlPos = new THREE.Vector3();
let _rlLastEye = new THREE.Vector3(1e9, 0, 0), _rlDirty = true;
function roomLitStep() {
  if (qLevel === 'low') return;          // the ladder already doused them all
  camera.getWorldPosition(_rlEye);
  if (!_rlDirty && _rlEye.distanceToSquared(_rlLastEye) < 2.25) return;  // 1.5 m
  _rlDirty = false;
  _rlLastEye.copy(_rlEye);
  const room = [];
  for (const l of roomLights) {
    if (!l.userData?.roomLight) continue;
    l.getWorldPosition(_rlPos);
    room.push([_rlPos.distanceToSquared(_rlEye), l]);
  }
  if (room.length <= ROOM_LIT_MAX) return;
  room.sort((a, b) => a[0] - b[0]);
  for (let i = 0; i < room.length; i++) room[i][1].visible = i < ROOM_LIT_MAX;
}

let qRose = false;
function qStep(dt) {
  // harness runs (webdriver) keep deterministic visuals; they force via the hook
  if (!qAuto || reduced || navigator.webdriver) return;
  if (renderer.xr.isPresenting) return;       // a headset has its own ladder: xrQStep
  qAcc += dt; qFrames++;
  if (qLevel === 'low') {
    // one step back up, once: a 10 s window comfortably over budget (a
    // stalled tab that recovered, a heavy view left behind) restores the
    // full ladder; a second drop after that stays down, so it cannot flap
    if (qRose) return;
    if (qAcc >= 10) {
      if (qFrames / qAcc >= 45) { qRose = true; setQuality('high'); }
      qAcc = 0; qFrames = 0;
    }
    return;
  }
  if (qAcc >= 5) {
    if (qFrames / qAcc < 22) {
      setQuality('low');
      document.getElementById('hint').textContent =
        '⚡ performance mode: resolution and shadows stepped down';
    }
    qAcc = 0; qFrames = 0;
  }
}

// the WebXR layer itself - probe, session, rig, controllers, wrist panel -
// lives in the XR block (XR_JS) just above the frame loop, once the scene
// it moves through exists

const scene = new THREE.Scene();

/* ---------------------------------------------------------- the sky ----
   An equirectangular dome drawn into one canvas: the campus's own four
   gradient bands, a sun or a moon with its glow, a band of value-noise
   cloud thickened or thinned by the weather record, and after dark a star
   field placed by a FIXED seed - so it is a night sky, the same one every
   time, rather than a photograph of the night sky. No image is loaded to
   make any of it; see D.world.honesty.sky. */
const SKY = D.world.sky;
// a small deterministic generator: the same world every visit
function seeded(seed) {
  let x = seed >>> 0;
  return () => ((x = (x * 1664525 + 1013904223) >>> 0) / 4294967296);
}
// two-dimensional value noise, tiled, summed over octaves
function valueNoise(rnd, size) {
  const g = new Float32Array(size * size);
  for (let i = 0; i < g.length; i++) g[i] = rnd();
  return (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y);
    const fx = x - xi, fy = y - yi;
    const at = (a, b) => g[((b % size) + size) % size * size
      + ((a % size) + size) % size];
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    const t = at(xi, yi) + (at(xi + 1, yi) - at(xi, yi)) * sx;
    const u = at(xi, yi + 1) + (at(xi + 1, yi + 1) - at(xi, yi + 1)) * sx;
    return t + (u - t) * sy;
  };
}

function skyCanvas(stops, opts) {
  const W = 1024, H = 512;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, H);
  gr.addColorStop(0, stops[0]); gr.addColorStop(.55, stops[1]);
  gr.addColorStop(.8, stops[2]); gr.addColorStop(1, stops[3]);
  g.fillStyle = gr; g.fillRect(0, 0, W, H);

  // the stars go under everything else, and never move between visits
  if (opts.stars) {
    const rnd = seeded(0x5EEDDA7A);
    for (let i = 0; i < SKY.stars.count; i++) {
      const x = rnd() * W, y = rnd() * H * .62, a = .25 + rnd() * .7;
      const r = rnd() < .08 ? 2.1 : rnd() < .32 ? 1.4 : .9;
      g.fillStyle = `rgba(232,240,255,${(a * (1 - y / (H * .95))).toFixed(3)})`;
      g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
    }
  }

  // Sun or moon, drawn where the key light ACTUALLY comes from: azimuth
  // and elevation are read off the light itself, so the disc in the sky
  // and the shadows on the ground agree instead of merely coexisting.
  const disc = opts.moon ? SKY.disc.moon : SKY.disc.sun;
  const kp = key.position;
  const klen = Math.hypot(kp.x, kp.y, kp.z) || 1;
  const dx = W * ((Math.atan2(kp.z, kp.x) / (Math.PI * 2)) + .5);
  const dy = H * (1 - (Math.asin(Math.min(1, kp.y / klen)) / Math.PI + .5));
  const glow = g.createRadialGradient(dx, dy, 0, dx, dy, disc.glow_px);
  glow.addColorStop(0, disc.color + 'cc');
  glow.addColorStop(.35, disc.color + '44');
  glow.addColorStop(1, disc.color + '00');
  g.fillStyle = glow;
  g.fillRect(dx - disc.glow_px, dy - disc.glow_px,
    disc.glow_px * 2, disc.glow_px * 2);
  g.fillStyle = disc.color;
  g.beginPath(); g.arc(dx, dy, disc.radius_px, 0, 7); g.fill();
  // the canvas wraps around the horizon, so a disc near the seam is drawn
  // on both sides of it rather than being sliced in half
  if (dx < disc.glow_px || dx > W - disc.glow_px) {
    const wrap = dx < disc.glow_px ? dx + W : dx - W;
    const g2 = g.createRadialGradient(wrap, dy, 0, wrap, dy, disc.glow_px);
    g2.addColorStop(0, disc.color + 'cc');
    g2.addColorStop(.35, disc.color + '44');
    g2.addColorStop(1, disc.color + '00');
    g.fillStyle = g2;
    g.fillRect(wrap - disc.glow_px, dy - disc.glow_px,
      disc.glow_px * 2, disc.glow_px * 2);
    g.fillStyle = disc.color;
    g.beginPath(); g.arc(wrap, dy, disc.radius_px, 0, 7); g.fill();
  }
  if (opts.moon) {                       // bite a crescent out of it
    g.globalCompositeOperation = 'destination-out';
    g.beginPath();
    g.arc(dx - disc.radius_px * .5, dy - disc.radius_px * .25,
      disc.radius_px * .92, 0, 7);
    g.fill();
    g.globalCompositeOperation = 'source-over';
  }

  // the cloud band: value noise over octaves, alpha driven by the weather
  const amount = opts.cloud ?? .2;
  if (amount > .02) {
    const rnd = seeded(0xC10D5);
    const n = valueNoise(rnd, 64);
    const y0 = H * SKY.clouds.band_from, y1 = H * SKY.clouds.band_to;
    const img = g.getImageData(0, y0, W, y1 - y0);
    const d = img.data;
    for (let y = 0; y < y1 - y0; y++) {
      const fade = Math.sin(Math.PI * (y / (y1 - y0)));
      for (let x = 0; x < W; x++) {
        let v = 0, amp = .5, f = SKY.clouds.base_frequency;
        for (let o = 0; o < SKY.clouds.octaves; o++) {
          v += n(x * f, (y + y0) * f) * amp; amp *= .5; f *= 2.1;
        }
        const a = Math.max(0, (v - (1 - amount) * .58)) * fade * 3.2
          * Math.min(1, opts.dim ?? 1);
        if (a <= 0) continue;
        const i = (y * W + x) * 4;
        const lum = opts.moon ? 96 : 232;
        d[i] += (lum - d[i]) * Math.min(1, a);
        d[i + 1] += (lum - d[i + 1]) * Math.min(1, a);
        d[i + 2] += (lum + 6 - d[i + 2]) * Math.min(1, a);
      }
    }
    g.putImageData(img, 0, y0);
  }
  // a bright band just above the horizon, so the dome does not end on an
  // edge the eye can find
  const hz = SKY.horizon_haze;
  const hg = g.createLinearGradient(0, H * (1 - hz.height * 2), 0, H);
  const haze = opts.moon ? '150,166,190' : '214,226,236';
  hg.addColorStop(0, `rgba(${haze},0)`);
  hg.addColorStop(1, `rgba(${haze},${(hz.strength * (opts.moon ? .35 : 1))
    .toFixed(2)})`);
  g.fillStyle = hg;
  g.fillRect(0, H * (1 - hz.height * 2), W, H * hz.height * 2);
  return c;
}

function setSky(stops, opts = {}) {
  scene.background?.dispose?.();
  const t = new THREE.CanvasTexture(skyCanvas(stops, opts));
  t.mapping = THREE.EquirectangularReflectionMapping;
  t.colorSpace = THREE.SRGBColorSpace;
  scene.background = t;
}
scene.fog = new THREE.Fog(0x1a2229, 70, 170);

/* ------------------------------------------------- generated surfaces ----
   Every surface in this bundle is a RECIPE, never a file: a base colour, a
   grain, an octave count and a relief depth, all declared in the world
   registry. The colour map and its NORMAL map are both generated here, in
   this browser, at boot - which is why the render contains no third-party
   artwork, and why the whole surface set can be regenerated smaller when
   the quality ladder steps down. See D.world.honesty.textures. */
const GROUND_RECIPES = D.world.ground;
const groundCache = new Map();

function noiseTex(base, grain, n = 1400, size = 256) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d');
  g.fillStyle = base; g.fillRect(0, 0, size, size);
  for (let i = 0; i < n; i++) {
    g.fillStyle = `rgba(${grain},${.05 + Math.random() * .1})`;
    const r = Math.random() * 2.2;
    g.fillRect(Math.random() * size, Math.random() * size, r, r);
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 4;
  return t;
}

// one recipe -> { map, normalMap }, generated once and shared
function groundTex(id, size = 256) {
  const hit = groundCache.get(id + ':' + size);
  if (hit) return hit;
  const r = GROUND_RECIPES[id];
  if (!r) return { map: null, normalMap: null };
  const rnd = seeded(0xA5 + id.length * 7919);
  const n = valueNoise(rnd, 32);
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d');
  g.fillStyle = r.base; g.fillRect(0, 0, size, size);
  // the height field the relief is read from, built as we shade
  const h = new Float32Array(size * size);
  const img = g.getImageData(0, 0, size, size), d = img.data;
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    let v = 0, amp = .5, f = 1 / 22;
    for (let o = 0; o < r.octaves; o++) {
      v += n(x * f, y * f) * amp; amp *= .5; f *= 2.07;
    }
    h[y * size + x] = v;
    const i = (y * size + x) * 4;
    const k = (v - .5) * 46;
    d[i] = Math.max(0, Math.min(255, d[i] + k));
    d[i + 1] = Math.max(0, Math.min(255, d[i + 1] + k));
    d[i + 2] = Math.max(0, Math.min(255, d[i + 2] + k));
  }
  g.putImageData(img, 0, 0);
  // the speckle sits on top of the noise, in the recipe's grain colour
  for (let i = 0; i < r.speckle; i++) {
    g.fillStyle = `rgba(${r.grain},${(.05 + rnd() * .12).toFixed(3)})`;
    const rr = rnd() * 2.4;
    g.fillRect(rnd() * size, rnd() * size, rr, rr);
  }
  const map = new THREE.CanvasTexture(c);
  map.wrapS = map.wrapT = THREE.RepeatWrapping;
  map.anisotropy = 4; map.colorSpace = THREE.SRGBColorSpace;

  // the normal map, read straight off the height field by central difference
  let normalMap = null;
  if (r.relief > .01) {
    const nc = document.createElement('canvas'); nc.width = nc.height = size;
    const ng = nc.getContext('2d');
    const nimg = ng.createImageData(size, size), nd = nimg.data;
    const at = (x, y) => h[(((y % size) + size) % size) * size
      + (((x % size) + size) % size)];
    const k = r.relief * 5.5;
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const dx = (at(x + 1, y) - at(x - 1, y)) * k;
      const dy = (at(x, y + 1) - at(x, y - 1)) * k;
      const len = Math.hypot(dx, dy, 1);
      const i = (y * size + x) * 4;
      nd[i] = (-dx / len * .5 + .5) * 255;
      nd[i + 1] = (-dy / len * .5 + .5) * 255;
      nd[i + 2] = (1 / len * .5 + .5) * 255;
      nd[i + 3] = 255;
    }
    ng.putImageData(nimg, 0, 0);
    normalMap = new THREE.CanvasTexture(nc);
    normalMap.wrapS = normalMap.wrapT = THREE.RepeatWrapping;
    normalMap.anisotropy = 4;
  }
  const out = { map, normalMap, recipe: r };
  groundCache.set(id + ':' + size, out);
  return out;
}

// One recipe can be laid at several scales, and a texture carries its own
// repeat, so the pair is cached per (recipe, repeat) rather than per
// recipe. The canvas underneath is still generated once and shared.
const groundMapCache = new Map();
function groundMaps(id, repeat) {
  const key = id + '@' + repeat;
  const hit = groundMapCache.get(key);
  if (hit) return hit;
  const base = groundTex(id);
  const map = base.map.clone(); map.needsUpdate = true;
  map.repeat.set(repeat, repeat);
  let normalMap = null;
  if (base.normalMap) {
    normalMap = base.normalMap.clone(); normalMap.needsUpdate = true;
    normalMap.repeat.set(repeat, repeat);
  }
  const out = { map, normalMap };
  groundMapCache.set(key, out);
  return out;
}

// a standard material straight off a recipe, repeat and relief included
function groundMat(id, tint, repeat) {
  const r = GROUND_RECIPES[id];
  const t = groundMaps(id, repeat ?? r.repeat);
  return new THREE.MeshStandardMaterial({
    map: t.map, normalMap: t.normalMap,
    normalScale: t.normalMap ? new THREE.Vector2(r.relief, r.relief) : null,
    color: tint ?? 0xffffff,
    roughness: r.roughness, metalness: r.metalness });
}

const asphaltTex = groundMaps('asphalt', 34).map;
const concreteTex = groundMaps('concrete', 9).map;

// far clears both the campus fog-far (1280) and the region board's
// (1300) with margin, so nothing pops at the clip plane before fog hides it
const camera = new THREE.PerspectiveCamera(50, innerWidth/innerHeight, .1, 1600);
camera.position.set(30, 26, 42);
/* The XR rig: the camera's parent, and the thing that MOVES when a body
   moves - walking, a seat pose, a snap turn. On a desktop it sits at the
   identity except in walk mode, so orbit and pointer-lock math see the
   camera exactly as before; in a headset three.js writes the head pose
   into the camera relative to this group, so the rig is the only thing
   the page may ever move. eyePos() is where the eye actually is, in world
   space, and every reader that used to take camera.position for that
   reads it instead. */
const xrRig = new THREE.Group(); xrRig.name = 'xr-rig';
xrRig.add(camera);
const _eye = new THREE.Vector3();
function eyePos() { return camera.getWorldPosition(_eye); }
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * .49;
controls.minDistance = 8; controls.maxDistance = 120;
controls.autoRotate = !reduced;
controls.autoRotateSpeed = .45;
controls.addEventListener('start', () => { controls.autoRotate = false; });

scene.add(xrRig);
const hemi = new THREE.HemisphereLight(0xaec2cb, 0x241d16, 1.05);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xffe0b0, 1.6);
key.position.set(35, 48, 20);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
const S = 60;
Object.assign(key.shadow.camera, { left: -S, right: S, top: S, bottom: -S, far: 140 });
scene.add(key);
const fill = new THREE.DirectionalLight(0x41C4D4, .25);
fill.position.set(-30, 20, -30);
scene.add(fill);

// the first sky, now that the light it draws the sun from exists
setSky(['#0c141c', '#1a2a36', '#33404a', '#463a2a'], { cloud: .18 });

/* ------------------------------------------------------- atmosphere ----- */
// Authored ambience per campus and six weather states, both read from the
// world registry rather than written here: the fog is San Francisco's and
// the haze is New Orleans's BY REPUTATION, not by any weather record, and
// a weather state is a set of multipliers applied to whichever campus
// atmosphere is loaded - so a campus keeps its own character in the rain
// instead of every campus looking alike under it.
const ATMOS = D.world.atmos;
const WX = D.world.weather;
const WX_CYCLE = Object.entries(WX).sort((a, b) => a[1].order - b[1].order)
  .map(([k]) => k);
const DEF_ATMOS = {
  sky: ['#0c141c', '#1a2a36', '#33404a', '#463a2a'],
  fog: { color: 0x1a2229, mul: 1 }, banks: 0,
  sun: { color: 0xffe0b0, i: 1.6 },
  hemi: { sky: 0xaec2cb, ground: 0x241d16, i: 1.05 },
  amb: { wind: .2 }, ground: 'concrete', verge: 'grass',
};
let atmosKey = null, fogMul = 1, fogBanks = [], wx = 'clear', night = false;
let genMs = 0;
const darkHex = (hex, f) => '#' + [1, 3, 5].map((i) =>
  Math.round(Math.min(255, parseInt(hex.slice(i, i + 2), 16) * f))
    .toString(16).padStart(2, '0')).join('');

function applyAtmos(k) {
  const a = ATMOS[k] ?? DEF_ATMOS;
  const w = WX[wx] ?? WX.clear;
  atmosKey = ATMOS[k] ? k : null;
  night = wx === 'night';
  fogMul = a.fog.mul * w.fog_mul;
  const t0 = performance.now();
  setSky(a.sky.map((h) => darkHex(h, w.sky_mul)),
    { cloud: w.cloud, moon: !!w.moon, stars: !!w.stars,
      dim: Math.min(1, w.sky_mul) });
  genMs += performance.now() - t0;
  scene.fog.color.setHex(a.fog.color).multiplyScalar(w.fog_tint);
  // after dark the sun is swapped for moonlight rather than dimmed; under
  // weather it keeps its own colour and simply loses strength
  if (night) { key.color.setHex(0x9db4d8); hemi.color.setHex(0x35455c);
               hemi.groundColor.setHex(0x0d0c0a); }
  else if (w.sun_mul < .7) { key.color.setHex(0x8a949c);
               hemi.color.setHex(0x5c6a74); hemi.groundColor.setHex(0x1a1a18); }
  else { key.color.setHex(a.sun.color); hemi.color.setHex(a.hemi.sky);
         hemi.groundColor.setHex(a.hemi.ground); }
  key.intensity = a.sun.i * w.sun_mul;
  hemi.intensity = a.hemi.i * w.hemi_mul;
  mat.win.emissiveIntensity = w.window_glow;
  rain.visible = w.rain > 0 && !reduced;
  rainRate = w.rain;
  ambSync({ ...a.amb, wind: (a.amb.wind ?? .2) + w.wind,
            ...(w.thunder ? { thunder: true } : {}) });
  faunaWeather(w);
}

/* ----------------------------------------------------------- fauna -----
   The animals that belong in a working yard, declared per campus in the
   world registry and built here out of the same shared boxes as
   everything else. Ambience, not a survey: common names, schematic
   bodies, authored paths. Nothing is drawn from any photograph and no
   sighting, count or species record is claimed - see D.world.honesty.fauna.

   They cost almost nothing (three or four shared-geometry meshes each),
   they are the only moving thing on an idle campus, and they give the
   scene something the buildings cannot: a sense of scale that a learner
   reads without being told. */
const FAUNA = D.world.fauna;
let faunaGroup = null, faunaBodies = [], faunaGust = 0;

function faunaBody(f) {
  const g = new THREE.Group();
  const col = new THREE.Color(f.color), acc = new THREE.Color(f.accent);
  const mBody = new THREE.MeshStandardMaterial({ color: col, roughness: .85 });
  const mAcc = new THREE.MeshStandardMaterial({ color: acc, roughness: .8 });
  const sp = f.span_m;
  if (f.body === 'bird' || f.body === 'wader') {
    const torso = new THREE.Mesh(boxGeo(sp * .3, sp * .2, sp * .5), mBody);
    g.add(torso);
    const wingL = new THREE.Mesh(boxGeo(sp * .48, sp * .05, sp * .26), mBody);
    const wingR = wingL.clone();
    wingL.position.set(-sp * .36, 0, 0); wingR.position.set(sp * .36, 0, 0);
    g.add(wingL, wingR);
    const head = new THREE.Mesh(boxGeo(sp * .16, sp * .16, sp * .2), mAcc);
    head.position.set(0, sp * .12, sp * .32); g.add(head);
    if (f.body === 'wader') {              // long neck, long legs, standing
      const neck = new THREE.Mesh(boxGeo(sp * .07, sp * .5, sp * .07), mBody);
      neck.position.set(0, sp * .34, sp * .2); g.add(neck);
      head.position.set(0, sp * .6, sp * .24);
      for (const sx of [-1, 1]) {
        const leg = new THREE.Mesh(boxGeo(sp * .05, sp * .55, sp * .05), mAcc);
        leg.position.set(sx * sp * .07, -sp * .34, 0); g.add(leg);
      }
      wingL.visible = wingR.visible = false;
    }
    g.userData.wings = [wingL, wingR];
  } else {                                  // quadruped: the yard dog
    const torso = new THREE.Mesh(boxGeo(sp * .26, sp * .28, sp * .62), mBody);
    torso.position.y = sp * .42; g.add(torso);
    const head = new THREE.Mesh(boxGeo(sp * .2, sp * .2, sp * .24), mAcc);
    head.position.set(0, sp * .58, sp * .38); g.add(head);
    const tail = new THREE.Mesh(boxGeo(sp * .06, sp * .06, sp * .3), mAcc);
    tail.position.set(0, sp * .52, -sp * .42); tail.rotation.x = -.5;
    g.add(tail);
    const legs = [];
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      const leg = new THREE.Mesh(boxGeo(sp * .07, sp * .42, sp * .07), mBody);
      leg.position.set(sx * sp * .1, sp * .21, sz * sp * .22);
      g.add(leg); legs.push(leg);
    }
    g.userData.legs = legs; g.userData.tail = tail;
  }
  return g;
}

function clearFauna() {
  if (!faunaGroup) return;
  faunaGroup.parent?.remove(faunaGroup);
  disposeOf(faunaGroup);
  faunaGroup = null; faunaBodies = [];
}

// birds fly at a groundspeed: angular rate is scaled by radius so a
// bigger campus doesn't make them cover more ground per second
const FAUNA_REF_R = 84;
function spawnFauna(campusKey, radius) {
  clearFauna();
  if (reduced) return;                      // stillness for those who ask
  faunaGroup = new THREE.Group();
  faunaGroup.name = 'tc-fauna';
  const rnd = seeded(0xFA0A + (campusKey || '').length * 131);
  const angK = FAUNA_REF_R / radius;
  for (const [fk, f] of Object.entries(FAUNA)) {
    if (!f.campuses.includes(campusKey)) continue;
    for (let i = 0; i < f.flock; i++) {
      const b = faunaBody(f);
      b.userData.kind = fk;
      b.userData.motion = f.motion;
      b.userData.speed = f.speed * (.8 + rnd() * .45) * angK;
      b.userData.phase = rnd() * Math.PI * 2;
      b.userData.rad = radius * (.3 + rnd() * .55);
      b.userData.h = f.height_m[0]
        + rnd() * (f.height_m[1] - f.height_m[0]);
      b.userData.flap = 4 + rnd() * 3;
      b.userData.span = f.span_m;
      faunaGroup.add(b); faunaBodies.push(b);
    }
  }
  scene.add(faunaGroup);
}

// weather reaches the animals too: they fly lower and faster in wind, and
// in a storm they are simply not out
function faunaWeather(w) {
  faunaGust = w.wind;
  if (faunaGroup) faunaGroup.visible = w.rain < .9;
}

function faunaStep(t, dt) {
  if (!faunaGroup || !faunaGroup.visible) return;
  for (const b of faunaBodies) {
    const u = b.userData;
    const sp = u.speed * (1 + faunaGust * .6);
    const a = u.phase + t * sp * .22;
    if (u.motion === 'circuit' || u.motion === 'glide') {
      const wob = u.motion === 'glide' ? 0 : Math.sin(t * sp + u.phase) * 2.2;
      b.position.set(Math.cos(a) * u.rad, u.h + wob - faunaGust * 3,
        Math.sin(a) * u.rad);
      b.rotation.y = -a + Math.PI / 2;
      b.rotation.z = Math.sin(t * sp * .7 + u.phase) * .18;
      const fl = u.motion === 'glide'
        ? Math.sin(t * 1.1 + u.phase) * .12          // pelicans mostly glide
        : Math.sin(t * u.flap + u.phase) * .85;
      if (u.wings) { u.wings[0].rotation.z = fl; u.wings[1].rotation.z = -fl; }
    } else if (u.motion === 'hop') {
      const hop = Math.max(0, Math.sin(t * 2.4 + u.phase)) * .35;
      b.position.set(Math.cos(a * .6) * u.rad, hop,
        Math.sin(a * .6) * u.rad);
      b.rotation.y = -a * .6 + Math.PI / 2;
      if (u.wings) { const f2 = hop * 1.6;
        u.wings[0].rotation.z = f2; u.wings[1].rotation.z = -f2; }
    } else if (u.motion === 'perch') {
      b.position.set(Math.cos(u.phase) * u.rad, 0, Math.sin(u.phase) * u.rad);
      b.rotation.y = u.phase * 2;
      b.position.y = Math.sin(t * .6 + u.phase) * .03;   // barely, breathing
    } else {                                  // patrol: the yard dog, trotting
      const seg = (t * sp * .1 + u.phase) % (Math.PI * 2);
      b.position.set(Math.cos(seg) * u.rad, 0, Math.sin(seg) * u.rad);
      b.rotation.y = -seg + Math.PI / 2;
      if (u.legs) u.legs.forEach((l, i) => {
        l.rotation.x = Math.sin(t * 7 * sp + i * 1.7) * .5;
      });
      if (u.tail) u.tail.rotation.y = Math.sin(t * 4) * .35;
    }
  }
}

// the rain: one Points cloud recycled over the camera target in storms
const rain = (() => {
  const N = 900, pos = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    pos[i * 3] = (Math.random() - .5) * 220;
    pos[i * 3 + 1] = Math.random() * 90;
    pos[i * 3 + 2] = (Math.random() - .5) * 220;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const pts = new THREE.Points(geo, new THREE.PointsMaterial({
    color: 0xaac2d2, size: .8, transparent: true, opacity: .6 }));
  pts.visible = false; pts.frustumCulled = false;
  return pts;
})();
scene.add(rain);
let rainRate = 0;
function rainStep(dt) {
  if (!rain.visible) return;
  // rain is a rate, not a switch: a shower falls slower and thinner than
  // a storm, from the same one particle cloud
  rain.material.opacity = .22 + rainRate * .42;
  rain.material.size = .5 + rainRate * .45;
  const p = rain.geometry.attributes.position.array;
  const cx2 = controls.target.x, cz2 = controls.target.z;
  for (let i = 0; i < p.length; i += 3) {
    p[i + 1] -= (28 + rainRate * 34) * dt;
    if (p[i + 1] < 0) {
      p[i + 1] = 80 + Math.random() * 10;
      p[i] = cx2 + (Math.random() - .5) * 220;
      p[i + 2] = cz2 + (Math.random() - .5) * 220;
    }
  }
  rain.geometry.attributes.position.needsUpdate = true;
}
// re-apply the current view's atmosphere and fog band (the night toggle)
function reAtmos() {
  if (view === 'campus') {
    applyAtmos(campusKey);
    scene.fog.near = 320 * fogMul; scene.fog.far = 1280 * fogMul;
  } else if (view === 'hall') {
    applyAtmos(campusKey);
    scene.fog.near = 70 * fogMul; scene.fog.far = 170 * fogMul;
  } else if (view === 'sim') {
    applyAtmos(campusKey);
    scene.fog.near = 90 * fogMul; scene.fog.far = 260 * fogMul;
  } else applyAtmos(null);
}

/* Ambient sound beds - synthesized like everything else (no recordings):
   looped filtered noise for the wind, sparse gull chirps, a rare harbor
   horn, the NOLA insect shimmer and far thunder. All ride the master
   gain, so the one mute silences the world too. */
let ambNodes = [], ambTimers = [], ambCfg = null;
function ambStop() {
  for (const t of ambTimers) clearTimeout(t);
  for (const n of ambNodes) { try { n.stop?.(); } catch (e) {} n.disconnect?.(); }
  ambTimers = []; ambNodes = [];
}
function noiseBuf(secs = 2) {
  const n = Math.floor(ac.sampleRate * secs);
  const buf = ac.createBuffer(1, n, ac.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
  return buf;
}
function ambLoop(fn, lo, hi) {
  const tick = () => { fn(); ambTimers.push(setTimeout(tick,
    (lo + Math.random() * (hi - lo)) * 1000)); };
  ambTimers.push(setTimeout(tick, (lo + Math.random() * (hi - lo)) * 500));
}
function ambSync(cfg) {
  ambCfg = cfg ?? ambCfg;
  if (!ac || !ambCfg) return;
  ambStop();
  const a = ambCfg;
  if (a.wind) {
    const src = ac.createBufferSource(); src.buffer = noiseBuf(); src.loop = true;
    const f = ac.createBiquadFilter(); f.type = 'lowpass';
    f.frequency.value = 240 + 360 * a.wind;
    const g = ac.createGain(); g.gain.value = .012 + .04 * a.wind;
    src.connect(f); f.connect(g); g.connect(master); src.start();
    ambNodes.push(src, f, g);
  }
  if (a.insects) {
    const src = ac.createBufferSource(); src.buffer = noiseBuf(); src.loop = true;
    const f = ac.createBiquadFilter(); f.type = 'bandpass';
    f.frequency.value = 4800; f.Q.value = 9;
    const g = ac.createGain(); g.gain.value = .011;
    const lfo = ac.createOscillator(), lg = ac.createGain();
    lfo.frequency.value = .6; lg.gain.value = .006;
    lfo.connect(lg); lg.connect(g.gain); lfo.start();
    src.connect(f); f.connect(g); g.connect(master); src.start();
    ambNodes.push(src, f, g, lfo, lg);
  }
  if (a.gulls) ambLoop(() => {
    const n = 2 + Math.floor(Math.random() * 2);
    for (let i = 0; i < n; i++)
      setTimeout(() => blip(1500 - i * 160, 950, .22, 'triangle', .04), i * 260);
  }, 8, 18);
  if (a.harbor) ambLoop(() => blip(98, 94, 1.6, 'square', .035), 28, 55);
  if (a.thunder) ambLoop(() => {
    const nb = ac.createBufferSource(); nb.buffer = noiseBuf(3);
    const f = ac.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 110;
    const g = ac.createGain(); g.gain.setValueAtTime(.12, ac.currentTime);
    g.gain.exponentialRampToValueAtTime(.001, ac.currentTime + 2.8);
    nb.connect(f); f.connect(g); g.connect(master); nb.start();
    ambNodes.push(nb, f, g);
  }, 35, 75);
}
// the world gets its voice on the first gesture the browser allows
renderer.domElement.addEventListener('pointerdown', () => {
  acEnsure(); ambSync(ambCfg);
}, { once: true });

// the drawn ground's outer edge - sized to clear the campus dressing at
// the scale below, so nothing floats past it
const GROUND_R = 520;
// ground: dark apron with a faint work grid
const ground = new THREE.Mesh(
  new THREE.CircleGeometry(GROUND_R, 64),
  groundMat('asphalt', 0x8f9698, 68));
// a campus can stand on a different surface from its neighbour, and the
// atmosphere record is where that is said
function setGroundSurface(campusKey) {
  const a = ATMOS[campusKey] ?? DEF_ATMOS;
  ground.material.dispose();
  ground.material = groundMat(a.ground, 0x8f9698, 68);
}
ground.rotation.x = -Math.PI/2; ground.receiveShadow = true;
scene.add(ground);
const grid = new THREE.GridHelper(GROUND_R * 2, 180, 0x28353A, 0x1b2427);
grid.position.y = .02; scene.add(grid);

const mat = {
  slab:  new THREE.MeshStandardMaterial({ map: concreteTex, color: 0xb8bdbd, roughness: .9 }),
  win:   new THREE.MeshStandardMaterial({ color: 0x0b0f11,
           emissive: 0xffc27a, emissiveIntensity: .5, roughness: .4 }),
  // open water, rough grass, plant-yard gravel and stockpile sand all come
  // straight off their recipes in the world registry - colour map and
  // normal map both generated in this browser, never loaded
  water: groundMat('water', 0x8fb4c8, 10),
  grass: groundMat('grass'),
  gravel: groundMat('gravel'),
  sand:  groundMat('sand'),
  land:  new THREE.MeshStandardMaterial({ map: asphaltTex, color: 0xcdd2d3,
           roughness: .95 }),
  road:  new THREE.MeshStandardMaterial({ color: 0x565c60, roughness: .95 }),
  drive: new THREE.MeshStandardMaterial({ color: 0x777d81, roughness: .9 }),
  walkway: new THREE.MeshStandardMaterial({ map: concreteTex, color: 0xcdd2d0,
           roughness: .95 }),
  paint: new THREE.MeshStandardMaterial({ color: 0xd8dcd8, roughness: .5 }),
  wall:  new THREE.MeshStandardMaterial({ color: 0x39454a, roughness: .85 }),
  part:  new THREE.MeshStandardMaterial({ color: 0x2c3639, roughness: .85 }),
  post:  new THREE.MeshStandardMaterial({ color: 0xE8A33D, roughness: .45,
                                          emissive: 0x7a4d08 }),
  steel: new THREE.MeshStandardMaterial({ color: 0x41C4D4, roughness: .5 }),
  wood:  new THREE.MeshStandardMaterial({ color: 0x8a6a42, roughness: .9 }),
  metal: new THREE.MeshStandardMaterial({ color: 0x8f9a9d, roughness: .55,
                                          metalness: .55 }),
  brick: new THREE.MeshStandardMaterial({ color: 0xb3462f, roughness: .92 }),
  block: new THREE.MeshStandardMaterial({ color: 0x9aa0a2, roughness: .92 }),
  cone:  new THREE.MeshStandardMaterial({ color: 0xE07C48, roughness: .6 }),
  // schematic marsh/shrub vegetation clumps at the walkable restoration
  // sites - one shared low-poly material, never a downloaded plant asset
  veg:   new THREE.MeshStandardMaterial({ color: 0x4c6b3a, roughness: .95 }),
};
// every material above is a page-wide singleton, reused by name across
// halls, campuses and every sim yard - disposeOf() must never free one of
// these just because the group it happens to sit in is being torn down
for (const m of Object.values(mat)) m.userData.shared = true;

/* ------------------------------------------------------- the signs -----
   Every word in this world is on a sign, and a sign should be readable
   before it is read. Its SHAPE says what kind of thing it marks - a
   speech bubble is somebody who will talk to you, a tab with a pointer is
   a place you can enter, a pin on a stem is somewhere real out there, a
   chip is something you can open, a readout is a number a machine
   measured. Its COLOUR says whose it is and where it came from: a hall
   wears its district's own hue, a RECORDED place wears a solid accent, a
   SCHEMATIC one is drawn dashed and says so. Its TYPE says rank: display
   for names, sans for the line under them, mono for anything measured.

   All of that is declared in the label registry, never here. */
const LBL = D.labels;
const LKIND = LBL.kinds, LPAL = LBL.palette, LTYPE = LBL.type;
const LFOCUS = LBL.focus;
let labelSet = [];

const lblFace = (f) => LTYPE[f] ?? LTYPE.display;
const lblAccent = (kind, hue) => kind.accent === 'district'
  ? (hue == null ? LPAL.mark : `hsl(${hue} 58% 62%)`)
  : (LPAL[kind.accent] ?? LPAL.mark);

// the ten plates, drawn on the 2D context; `case` per shape so the
// registry and the page cannot drift apart without the build noticing
function labelShape(g, shape, w, h, accent, dashed) {
  const S = LBL.shapes[shape] ?? LBL.shapes.plate;
  const r = Math.min(S.radius, h / 2);
  const body = h - (S.tail ? 14 : 0) - (S.stem ? 22 : 0);
  g.save();
  g.shadowColor = 'rgba(0,0,0,.55)'; g.shadowBlur = 10; g.shadowOffsetY = 3;
  g.fillStyle = LPAL.plate;
  switch (shape) {
    case 'speech':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      g.beginPath();                       // the tail, off to the left
      g.moveTo(26, body - 1); g.lineTo(44, body - 1); g.lineTo(30, body + 14);
      g.closePath(); g.fill();
      break;
    case 'tab':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      g.beginPath();                       // the pointer, centred
      g.moveTo(w / 2 - 11, body - 1); g.lineTo(w / 2 + 11, body - 1);
      g.lineTo(w / 2, body + 14); g.closePath(); g.fill();
      break;
    case 'chip':
      g.beginPath(); g.roundRect(0, 0, w, body, body / 2); g.fill();
      break;
    case 'plate':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      break;
    case 'pin':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      g.shadowBlur = 0;
      g.strokeStyle = accent; g.lineWidth = 3;
      g.beginPath(); g.moveTo(w / 2, body); g.lineTo(w / 2, body + 15);
      g.stroke();
      g.fillStyle = accent;
      g.beginPath(); g.arc(w / 2, body + 18, 5, 0, 7); g.fill();
      break;
    case 'banner':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      break;
    case 'marquee':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      g.shadowBlur = 0;
      g.fillStyle = accent; g.fillRect(18, 12, w - 36, 3);
      break;
    case 'ribbon':
      g.beginPath();
      g.moveTo(14, 0); g.lineTo(w, 0); g.lineTo(w - 14, body); g.lineTo(0, body);
      g.closePath(); g.fill();
      break;
    case 'ghost':
      break;                               // no plate at all, by design
    case 'readout':
      g.fillStyle = 'rgba(6,10,12,.9)';
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      g.shadowBlur = 0;
      g.strokeStyle = accent; g.lineWidth = 2;
      g.beginPath(); g.roundRect(1, 1, w - 2, body - 2, r); g.stroke();
      break;
  }
  g.restore();
  // the accent: a stripe for the wide shapes, a dashed outline where the
  // registry says the thing behind the sign is SCHEMATIC
  if (shape === 'banner' || shape === 'plate') {
    g.fillStyle = accent;
    g.fillRect(0, 0, shape === 'banner' ? 8 : 5, body);
  }
  if (dashed) {
    g.save();
    g.setLineDash([9, 7]); g.strokeStyle = accent; g.lineWidth = 2;
    g.beginPath(); g.roundRect(1, 1, w - 2, body - 2, r); g.stroke();
    g.restore();
  }
  return body;
}

/* label(text, sub, scale, opts)
   opts: { kind, hue, badge }  - kind names a row of the label registry;
   hue is the district's, for the kinds whose accent is 'district'. */
/* Identical signs share one texture: the same text on the same kind of
   sign with the same accent is the same bitmap, so it is drawn once and
   reference-counted - the sprite (its own material, its own scale, its own
   focus) stays per sign, and disposeOf() releases the texture with the
   last sprite that used it. No atlas: a sign is still its own draw. */
const lblTexCache = new Map();
function lblTexRelease(key) {
  const e = key && lblTexCache.get(key);
  if (!e) return;
  if (--e.refs <= 0) { e.tex.dispose(); lblTexCache.delete(key); }
}
function label(text, sub, scale = 1, opts = {}) {
  const kindId = opts.kind && LKIND[opts.kind] ? opts.kind : 'room';
  const kind = LKIND[kindId];
  const shape = kind.shape;
  // opts.accent: an explicit accent colour - the XR wrist panel's warning
  // readouts use the dash's own crit colour, the same rule as .warn
  const accent = opts.accent ?? lblAccent(kind, opts.hue);
  const texKey = kindId + '|' + accent + '|' + text + '|' + (sub ?? '');
  const hit = lblTexCache.get(texKey);
  if (hit) {
    hit.refs++;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({
      map: hit.tex, transparent: true, depthTest: false }));
    sp.scale.set(hit.w / 90 * scale, hit.h / 90 * scale, 1);
    sp.userData.lbl = { kind: kindId, base: sp.scale.clone(), baseY: null,
                        accent, focus: 0, hide: kind.hide_beyond_m || 0,
                        floor: kind.min_focus, texKey };
    labelSet.push(sp);
    return sp;
  }
  const marquee = shape === 'marquee';
  const dpr = Math.min(2, devicePixelRatio || 1);

  const c = document.createElement('canvas');
  const g = c.getContext('2d');
  const titlePx = marquee ? LTYPE.title_px + 4
    : shape === 'chip' ? LTYPE.chip_px : LTYPE.title_px;
  const titleFont = (kind.face === 'mono' ? '600 ' : '600 ')
    + titlePx + 'px ' + lblFace(kind.face);
  g.font = titleFont;
  const title = marquee ? text.toUpperCase() : text;
  const track = marquee ? LTYPE.tracking_marquee : 0;
  const tw = g.measureText(title).width + track * title.length;
  let sw = 0;
  if (sub) {
    g.font = LTYPE.sub_px + 'px ' + lblFace(kind.face === 'mono' ? 'mono' : 'body');
    sw = g.measureText(sub).width;
  }
  const padX = shape === 'chip' ? 26 : shape === 'ghost' ? 6 : 22;
  const w = Math.max(tw, sw, shape === 'chip' ? 48 : 110) + padX * 2
    + (shape === 'plate' || shape === 'banner' ? 10 : 0);
  const bodyH = (sub ? 104 : shape === 'chip' ? 54 : 68)
    + (marquee ? 14 : 0);
  const h = bodyH + (LBL.shapes[shape].tail ? 14 : 0)
    + (LBL.shapes[shape].stem ? 22 : 0);

  c.width = Math.ceil(w * dpr); c.height = Math.ceil(h * dpr);
  g.scale(dpr, dpr);
  const body = labelShape(g, shape, w, h, accent, !!kind.dashed);

  const left = padX + (shape === 'plate' ? 5 : shape === 'banner' ? 8 : 0);
  const baseline = sub ? (marquee ? 62 : 52) : body / 2 + titlePx * .35;
  g.save();
  g.shadowColor = 'rgba(0,0,0,.75)'; g.shadowBlur = 6;
  g.fillStyle = shape === 'readout' ? accent : LPAL.ink;
  g.font = titleFont;
  if (track) {                              // letter-spaced caps, by hand
    let x = left;
    for (const ch of title) { g.fillText(ch, x, baseline);
      x += g.measureText(ch).width + track; }
  } else g.fillText(title, left, baseline);
  if (sub) {
    g.fillStyle = shape === 'ghost' ? LPAL.ink : LPAL.muted;
    g.font = LTYPE.sub_px + 'px '
      + lblFace(kind.face === 'mono' ? 'mono' : 'body');
    g.fillText(sub, left, baseline + 36);
  }
  g.restore();

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  lblTexCache.set(texKey, { tex, w, h, refs: 1 });
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({
    map: tex, transparent: true, depthTest: false }));
  sp.scale.set(w / 90 * scale, h / 90 * scale, 1);
  sp.userData.lbl = { kind: kindId, base: sp.scale.clone(), baseY: null,
                      accent, focus: 0, hide: kind.hide_beyond_m || 0,
                      floor: kind.min_focus, texKey };
  labelSet.push(sp);
  return sp;
}

/* ---- and how a sign reads the view ------------------------------------
   Each frame every live label is scored on the angle between the view
   direction and the label (inside the declared cone) and again on
   distance; the two multiply. The score drives opacity, size and tint,
   eased rather than snapped so nothing flickers as the head turns. The
   single most centred label within reach is the FOCUS: it takes the
   accent tint and lifts, so a learner can see what they are about to act
   on without a cursor - which is what makes this work in a headset, where
   there is no cursor to have.

   This is presentation and nothing else: no label is a score, none gates
   anything, and no grader reads any of it. */
let labelFocus = null;
const _lblFwd = new THREE.Vector3(), _lblTo = new THREE.Vector3();
const _lblPos = new THREE.Vector3();
function labelStep(dt) {
  if (!labelSet.length) return;
  let live = 0, best = null, bestScore = 0;
  camera.getWorldDirection(_lblFwd);
  const eye = eyePos();
  const cos = Math.cos(LFOCUS.cone_deg * Math.PI / 180);
  const ease = reduced ? 1 : Math.min(1, (dt || .016) * LFOCUS.ease);
  const ref = Math.max(LFOCUS.near_full_m, eye.distanceTo(controls.target));
  const tanHalfFov = Math.tan(camera.fov * Math.PI / 360);
  for (const sp of labelSet) {
    if (!sp.parent) continue;               // its group was disposed
    labelSet[live++] = sp;
    // a sign in a hidden group (the cached region board behind a campus,
    // the campus behind a hall) is not scored: nothing on screen to score
    let hid = false;
    for (let o = sp.parent; o && o !== scene; o = o.parent)
      if (!o.visible) { hid = true; break; }
    if (hid) continue;
    const u = sp.userData.lbl;
    sp.getWorldPosition(_lblPos);
    const dist = _lblPos.distanceTo(eye);
    if (u.hide && dist > u.hide) { sp.visible = false; continue; }
    _lblTo.copy(_lblPos).sub(eye).normalize();
    const dot = _lblTo.dot(_lblFwd);
    // angle: 1 dead ahead, 0 at the edge of the cone and beyond
    const ang = dot <= cos ? 0 : (dot - cos) / (1 - cos);
    // distance, judged RELATIVE to how far out the view is: a sign 200 m
    // off is far when you are walking and near when you are looking at
    // the whole campus from above, so the reference is the camera's own
    // distance to what it is looking at
    const rel = dist / ref;
    const near = rel <= LFOCUS.fade_from_rel ? 1
      : rel >= LFOCUS.fade_to_rel ? 0
      : 1 - (rel - LFOCUS.fade_from_rel)
          / (LFOCUS.fade_to_rel - LFOCUS.fade_from_rel);
    const want = ang * near;
    u.focus += (want - u.focus) * ease;
    const lit = Math.max(u.floor, LFOCUS.floor) ;
    sp.visible = near > .01;
    sp.material.opacity = reduced ? 1
      : Math.min(1, lit + (1 - lit) * u.focus) * (.25 + .75 * near);
    // A world-space sign grows without limit as you walk up to it. Clamp
    // what the eye actually gets: never more than max_frac of the
    // viewport's height, never less than min_frac while it is in range.
    const grow = 1 + LFOCUS.grow * u.focus;
    let h = u.base.y * grow;
    const span = 2 * dist * tanHalfFov;           // world height of the view
    const lo = span * LFOCUS.screen.min_frac, hi = span * LFOCUS.screen.max_frac;
    const k2 = h > hi ? hi / h : h < lo ? lo / h : 1;
    sp.scale.set(u.base.x * grow * k2, h * k2, 1);
    if (want > bestScore && rel < LFOCUS.fade_from_rel) {
      bestScore = want; best = sp;
    }
  }
  labelSet.length = live;
  if (best !== labelFocus) {
    if (labelFocus) {
      labelFocus.material.color.setHex(0xffffff);
      const u = labelFocus.userData.lbl;
      if (u.baseY !== null) { labelFocus.position.y = u.baseY; u.baseY = null; }
    }
    labelFocus = best;
    if (best) {
      best.material.color.set(LPAL.mark);
      const u = best.userData.lbl;
      u.baseY = best.position.y;
      best.position.y += LFOCUS.lift_m;
    }
  }
}

/* Floor and wall surfaces: a colour map AND a normal map, both generated
   here from the registry's own pattern key.

   The floors used to return a colour map only, so a checkerplate floor and
   a sheet-vinyl floor caught the light identically - the pattern was
   PAINTED ON, and at a raking angle you could see it was painted on. The
   ground outside had proper relief (groundTex, above, reads a normal map
   off its own height field); the rooms inside did not. Same trick, applied
   where the learner actually stands.

   The height field is drawn alongside the colour, by the same pass, so a
   mortar course is low BECAUSE it was drawn low and not because a second
   table says it should be. `relief` is how far that reads - 0 is a flat
   painted surface and the normal map is skipped entirely. */
const PATTERN_RELIEF = {
  slab: .30, tile: .45, brick: .90, plank: .55, block: .80, checker: 1.00,
  grate: 1.20, broom: .25, smooth: .04, speckle: .30,
  panel: .60, plywood: .30, board: .10, fabric: .35, screen: .70, mesh: .95,
};

/* A height field to a normal map, by central difference - the same
   arithmetic groundTex uses, lifted out so the ground, the floors and the
   walls all read relief the same way instead of three times differently. */
function normalFromHeight(h, size, relief) {
  if (!(relief > .01)) return null;
  const nc = document.createElement('canvas'); nc.width = nc.height = size;
  const ng = nc.getContext('2d');
  const nimg = ng.createImageData(size, size), nd = nimg.data;
  const at = (x, y) => h[(((y % size) + size) % size) * size
    + (((x % size) + size) % size)];
  const k = relief * 5.5;
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const dx = (at(x + 1, y) - at(x - 1, y)) * k;
    const dy = (at(x, y + 1) - at(x, y - 1)) * k;
    const len = Math.hypot(dx, dy, 1);
    const i = (y * size + x) * 4;
    nd[i] = (-dx / len * .5 + .5) * 255;
    nd[i + 1] = (-dy / len * .5 + .5) * 255;
    nd[i + 2] = (1 / len * .5 + .5) * 255;
    nd[i + 3] = 255;
  }
  ng.putImageData(nimg, 0, 0);
  const t = new THREE.CanvasTexture(nc);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4;
  return t;
}

/* One pass paints the colour canvas and the height canvas together. `g` is
   the colour context, `hg` the height context (mid-grey is the datum; dark
   is a groove, light is proud). */
function paintPattern(g, hg, pat, S2) {
  const line = (ctx, x1, y1, x2, y2, w) => { ctx.lineWidth = w; ctx.beginPath();
    ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke(); };
  const groove = (x1, y1, x2, y2, w) => {
    g.strokeStyle = 'rgba(0,0,0,.28)'; line(g, x1, y1, x2, y2, w);
    hg.strokeStyle = '#3a3a3a'; line(hg, x1, y1, x2, y2, w);
  };
  const proud = (x, y, w, h2, a) => {
    g.fillStyle = `rgba(255,255,255,${a})`; g.fillRect(x, y, w, h2);
    hg.fillStyle = '#c8c8c8'; hg.fillRect(x, y, w, h2);
  };
  switch (pat) {
    case 'slab': groove(1, 1, S2 - 1, 1, 2); groove(1, 1, 1, S2 - 1, 2);
      groove(1, S2 - 1, S2 - 1, S2 - 1, 2); groove(S2 - 1, 1, S2 - 1, S2 - 1, 2); break;
    case 'tile': for (let i = 0; i <= S2; i += 32) {
      groove(i, 0, i, S2, 2); groove(0, i, S2, i, 2); } break;
    case 'brick': for (let y = 0; y < S2; y += 16) { groove(0, y, S2, y, 2);
      for (let x = ((y / 16) % 2) * 16; x < S2; x += 32) groove(x, y, x, y + 16, 2); } break;
    case 'plank': for (let x = 0; x <= S2; x += 16) groove(x, 0, x, S2, 2); break;
    case 'block': for (let i = 0; i <= S2; i += 10) {
      groove(i, 0, i, S2, 2); groove(0, i, S2, i, 2); } break;
    case 'checker':
      for (let y = 8; y < S2; y += 16) for (let x = 8; x < S2; x += 16) {
        for (const ctx of [g, hg]) {
          ctx.save(); ctx.translate(x, y); ctx.rotate(.785);
          ctx.fillStyle = ctx === g ? 'rgba(255,255,255,.16)' : '#d2d2d2';
          ctx.fillRect(-4, -1.4, 8, 2.8); ctx.restore();
        }
      }
      break;
    case 'grate':
      // the bars are proud and the slots between them read as holes
      for (let y = 2; y < S2; y += 10) {
        g.fillStyle = 'rgba(0,0,0,.5)'; g.fillRect(0, y, S2, 4);
        hg.fillStyle = '#242424'; hg.fillRect(0, y, S2, 4);
        proud(0, y + 4, S2, 6, .06);
      }
      break;
    case 'broom': for (let x = 0; x < S2; x += 3) {
      const a = .04 + Math.random() * .06;
      g.strokeStyle = `rgba(0,0,0,${a})`; line(g, x, 0, x, S2, 1);
      hg.strokeStyle = '#6e6e6e'; line(hg, x, 0, x, S2, 1); } break;
    case 'panel':
      // a lined panel wall: a shallow rib every so often, a seam less often
      for (let x = 0; x < S2; x += 16) { proud(x + 2, 0, 5, S2, .05); groove(x, 0, x, S2, 2); }
      groove(0, S2 / 2, S2, S2 / 2, 3); break;
    case 'plywood':
      // sheet edges, and the long grain running with them
      groove(0, 0, 0, S2, 3); groove(0, 0, S2, 0, 3);
      for (let y = 0; y < S2; y += 2) {
        const a = .03 + Math.random() * .07;
        g.strokeStyle = `rgba(90,60,25,${a})`; line(g, 0, y, S2, y + (Math.random() * 4 - 2), 1);
        hg.strokeStyle = '#767676'; line(hg, 0, y, S2, y, 1); }
      break;
    case 'board':
      // a flat drawn-on board: a joint line, and nothing else standing proud
      groove(S2 / 2, 0, S2 / 2, S2, 2); break;
    case 'fabric':
      // a woven face: a fine two-way weave, no hard edges
      for (let i = 0; i < S2; i += 3) {
        g.strokeStyle = 'rgba(0,0,0,.10)'; line(g, i, 0, i, S2, 1.4);
        g.strokeStyle = 'rgba(255,255,255,.06)'; line(g, 0, i, S2, i, 1.4);
        hg.strokeStyle = '#6a6a6a'; line(hg, i, 0, i, S2, 1.4);
        hg.strokeStyle = '#969696'; line(hg, 0, i, S2, i, 1.4); }
      break;
    case 'screen':
      // a screened bay: heavy frame, light infill
      for (let i = 0; i <= S2; i += 42) { groove(i, 0, i, S2, 4); groove(0, i, S2, i, 4); }
      for (let i = 0; i <= S2; i += 14) { groove(i, 0, i, S2, 1); }
      break;
    case 'mesh':
      // you can see through this one, so the wire is what catches the light
      for (let i = 0; i <= S2; i += 9) { proud(i, 0, 2, S2, .10); proud(0, i, S2, 2, .10); }
      for (let i = 4; i <= S2; i += 9) { groove(i, 0, i, S2, 3); groove(0, i, S2, i, 3); }
      break;
    default:   // smooth, speckle: aggregate scatter, no joints
      for (let i = 0; i < 700; i++) {
        const x = Math.random() * S2, y = Math.random() * S2;
        const up = Math.random() > .5;
        g.fillStyle = `rgba(${up ? '255,255,255' : '0,0,0'},${.06 + Math.random() * .1})`;
        g.fillRect(x, y, 2, 2);
        hg.fillStyle = up ? '#9a9a9a' : '#666'; hg.fillRect(x, y, 2, 2);
      }
  }
}

/* One recipe -> { map, normalMap }, generated once and shared. Floors and
   walls both come through here; a wall is not a special case, it is a
   surface with its own pattern and its own reason for having one. */
const surfCache = new Map();
function surfaceMaps(color, pattern) {
  const key = pattern + '|' + color;
  const hit = surfCache.get(key);
  if (hit) return hit;
  const S2 = 128;
  const c = document.createElement('canvas'); c.width = c.height = S2;
  const g = c.getContext('2d');
  const hc = document.createElement('canvas'); hc.width = hc.height = S2;
  const hg = hc.getContext('2d');
  g.fillStyle = color; g.fillRect(0, 0, S2, S2);
  hg.fillStyle = '#808080'; hg.fillRect(0, 0, S2, S2);
  // the grain the surface has before anything is drawn on it
  for (let i = 0; i < 260; i++) { g.fillStyle = `rgba(255,255,255,${Math.random() * .05})`;
    g.fillRect(Math.random() * S2, Math.random() * S2, 1.6, 1.6); }
  for (let i = 0; i < 260; i++) { g.fillStyle = `rgba(0,0,0,${Math.random() * .07})`;
    g.fillRect(Math.random() * S2, Math.random() * S2, 1.6, 1.6); }
  paintPattern(g, hg, pattern, S2);

  const map = new THREE.CanvasTexture(c);
  map.wrapS = map.wrapT = THREE.RepeatWrapping;
  map.anisotropy = 4; map.colorSpace = THREE.SRGBColorSpace;

  const hd = hg.getImageData(0, 0, S2, S2).data;
  const h = new Float32Array(S2 * S2);
  for (let i = 0; i < h.length; i++) h[i] = hd[i * 4] / 255;
  const normalMap = normalFromHeight(h, S2, PATTERN_RELIEF[pattern] ?? 0);

  const out = { map, normalMap };
  surfCache.set(key, out);
  return out;
}

/* A room's floor material, at the repeat its own tile size asks for. The
   canvas underneath is shared through surfaceMaps; only the repeat differs
   per room, so the texture pair is cloned and the clone carries the
   repeat - three.js reference-counts the shared source, so the clone a
   torn-down hall disposes never takes the cached original's GPU texture
   with it. */
function finishMat(fin, w, d) {
  const { map, normalMap } = surfaceMaps(fin.color, fin.pattern);
  const rx = Math.max(1, w / fin.tile_m), rz = Math.max(1, d / fin.tile_m);
  const m2 = map.clone(); m2.needsUpdate = true; m2.repeat.set(rx, rz);
  const spec = { map: m2, roughness: fin.roughness, metalness: fin.metalness };
  if (normalMap) {
    const n2 = normalMap.clone(); n2.needsUpdate = true; n2.repeat.set(rx, rz);
    spec.normalMap = n2;
    spec.normalScale = new THREE.Vector2(.8, .8);
  }
  return new THREE.MeshStandardMaterial(spec);
}

/* A wall material, the same way. `runM` is how far the wall runs and
   `hM` how tall it is, so a long back wall tiles its blockwork across the
   run instead of stretching one course over twelve metres. */
function wallMat(wal, runM, hM) {
  const { map, normalMap } = surfaceMaps(wal.color, wal.pattern);
  const rx = Math.max(1, runM / wal.tile_m), ry = Math.max(1, hM / wal.tile_m);
  const m2 = map.clone(); m2.needsUpdate = true; m2.repeat.set(rx, ry);
  const spec = { map: m2, roughness: wal.roughness, metalness: wal.metalness };
  if (normalMap) {
    const n2 = normalMap.clone(); n2.needsUpdate = true; n2.repeat.set(rx, ry);
    spec.normalMap = n2;
    spec.normalScale = new THREE.Vector2(.9, .9);
  }
  return new THREE.MeshStandardMaterial(spec);
}

/* The shared materials that describe a SURFACE rather than a colour now get
   the same treatment. mat.wall is the campus building envelope - 111 of them
   on the board, every one a flat slab of one colour until now - and mat.brick
   and mat.block exist precisely because brick and block have a pattern; a
   flat rectangle of brick-coloured paint is not brick.

   These are page-wide singletons, so this costs one texture pair each and
   not one draw call: the buildings already carry their own mesh for the
   raycast, and nothing new is added to the scene. mat.part is deliberately
   left flat - it is used on thirty-odd small parts at wildly different
   scales, where a repeat that suits one suits none of the others. */
for (const [key, pattern, rep] of [
  ['wall', 'panel', 3], ['brick', 'brick', 6], ['block', 'block', 5],
]) {
  const m2 = mat[key];
  const { map, normalMap } = surfaceMaps('#' + m2.color.getHexString(), pattern);
  m2.map = map.clone(); m2.map.repeat.set(rep, rep); m2.map.needsUpdate = true;
  if (normalMap) {
    m2.normalMap = normalMap.clone();
    m2.normalMap.repeat.set(rep, rep); m2.normalMap.needsUpdate = true;
    m2.normalScale = new THREE.Vector2(.7, .7);
  }
  // the map carries the colour now, so the tint must not double it
  m2.color.setHex(0xffffff);
  m2.needsUpdate = true;
}

/* The geometry cache: identical box dimensions share ONE BufferGeometry
   (a hall's fence posts alone repeat a size dozens of times). Shared
   geometries are marked and never disposed on teardown - disposeOf()
   below is the one legal teardown path. */
const geoCache = new Map();
function boxGeo(w, h, d) {
  const k = w + '|' + h + '|' + d;
  let g2 = geoCache.get(k);
  if (!g2) {
    g2 = new THREE.BoxGeometry(w, h, d);
    g2.userData.shared = true;
    geoCache.set(k, g2);
  }
  return g2;
}
const sphereGeoCache = new Map();
function sphereGeo(r, seg, rings) {
  const k = r + '|' + seg + '|' + rings;
  let g2 = sphereGeoCache.get(k);
  if (!g2) {
    g2 = new THREE.SphereGeometry(r, seg, rings);
    g2.userData.shared = true;
    sphereGeoCache.set(k, g2);
  }
  return g2;
}
// materials get the same shared/unshared split as geometry above: the
// `mat` table (and anything else marked userData.shared) is a page-wide
// singleton and must survive; a sim or an avatar builds its OWN fresh
// materials (and, for canvas-based ones, their own textures) every time
// it is entered/placed, and those are exactly what a teardown should free
const MAT_MAPS = ['map', 'normalMap', 'emissiveMap', 'roughnessMap',
  'metalnessMap', 'alphaMap', 'aoMap', 'bumpMap'];
function disposeOf(root) {
  root.traverse((o) => {
    if (o.geometry && !o.geometry.userData?.shared) o.geometry.dispose();
    // a label sprite leaves labelSet HERE, not when labelStep next notices
    // it is orphaned: a sprite inside a removed-but-intact group keeps its
    // parent, so every view's signs used to stay in the set forever, each
    // one scored, positioned and scaled again every frame (+328 sprites per
    // region->campus->hall->walk->sim->resto->region cycle, never freed)
    if (o.isSprite && o.userData.lbl) {
      const i = labelSet.indexOf(o);
      if (i >= 0) labelSet.splice(i, 1);
      if (labelFocus === o) labelFocus = null;
      lblTexRelease(o.userData.lbl.texKey);
      o.material.dispose();          // its map is the shared texture, released above
      return;
    }
    // a room or mast light leaves roomLights HERE, for the same reason a
    // label sprite leaves labelSet here: the list is walked by the quality
    // ladder, and a list that keeps every light every torn-down hall and
    // sim yard ever built grows without bound and re-shows lights that are
    // no longer in the scene
    if (o.isLight) {
      const li = roomLights.indexOf(o);
      if (li >= 0) roomLights.splice(li, 1);
      o.dispose?.();
      return;
    }
    if (!o.material) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m || m.userData?.shared) continue;
      for (const k of MAT_MAPS) m[k]?.dispose?.();
      m.dispose();
    }
  });
}
function box(w, h, d, m, x, y, z, group, shadow = true) {
  const b = new THREE.Mesh(boxGeo(w, h, d), m);
  b.position.set(x, y, z);
  b.castShadow = shadow; b.receiveShadow = true;
  group.add(b); return b;
}

/* ------------------------------------------------------- yard props ----- */
const PROPS = {
  sawhorse: (g,x,z) => { box(1.6,.1,.25,mat.wood,x,.75,z,g);
    for (const dx of [-.65,.65]) { box(.08,.8,.5,mat.wood,x+dx,.4,z,g); } },
  wheelbarrow: (g,x,z) => { box(.9,.35,.6,mat.metal,x,.45,z,g);
    box(.06,.5,.06,mat.metal,x+.6,.3,z-.2,g); box(.06,.5,.06,mat.metal,x+.6,.3,z+.2,g);
    const wheel = new THREE.Mesh(new THREE.TorusGeometry(.2,.07,8,20), mat.part);
    wheel.position.set(x-.5,.2,z); wheel.castShadow = true; g.add(wheel); },
  mixer: (g,x,z) => { box(1,.7,.8,mat.metal,x,.35,z,g);
    const drum = new THREE.Mesh(new THREE.CylinderGeometry(.45,.3,.9,14), mat.cone);
    drum.rotation.z = .7; drum.position.set(x,.95,z); drum.castShadow = true; g.add(drum); },
  cone: (g,x,z) => { const c = new THREE.Mesh(new THREE.ConeGeometry(.28,.7,12), mat.cone);
    c.position.set(x,.35,z); c.castShadow = true; g.add(c);
    box(.55,.05,.55,mat.cone,x,.02,z,g,false); },
  ladder: (g,x,z) => { for (const dx of [-.28,.28]) box(.07,2.6,.07,mat.metal,x+dx,1.3,z,g);
    for (let i=0;i<6;i++) box(.6,.05,.05,mat.metal,x,.3+i*.42,z,g,false); },
  toolbox: (g,x,z) => { box(.8,.45,.45,mat.steel,x,.25,z,g); },
  rebar: (g,x,z) => { for (let i=0;i<5;i++)
    box(.05,.05,2.4,mat.metal,x+i*.09,.1+i*.02,z,g,false); },
  generator: (g,x,z) => { box(1.2,.9,.8,mat.part,x,.45,z,g);
    box(.1,.5,.1,mat.metal,x+.4,1.1,z,g,false); },
  signStand: (g,x,z) => { box(.08,1.5,.08,mat.metal,x,.75,z,g);
    box(.9,.6,.06,mat.post,x,1.5,z,g,false); },
  brickPallet: (g,x,z) => { box(1.1,.12,1.1,mat.wood,x,.06,z,g,false);
    box(.95,.55,.95,mat.brick,x,.42,z,g); },
  blockPallet: (g,x,z) => { box(1.1,.12,1.1,mat.wood,x,.06,z,g,false);
    box(.95,.6,.95,mat.block,x,.45,z,g); },
};

/* ---------------------------------------------------------- the hall ---- */
let hallGroup = null, beacons = [], floors = [], roomRects = [], curRoom = null;
// The hall's own solid fabric: shell walls and partition segments, as
// axis-aligned rectangles in the hall's frame (a hall is not turned). Built
// from the SAME runs that are drawn, so there is no opening you can see and
// cannot use, and none you can use and cannot see.
let hallSolids = [];
let cribCount = 0;

/* ------------------------------------------------------- the tool crib --- */
// The toolroom registry hangs a district's twelve tools on a pegboard in
// every hall's tools room. Shapes are schematic render kinds the registry
// declares; clicking the board opens the crib and its deterministic drill.
function toolMesh(tl) {
  const m = new THREE.MeshStandardMaterial({
    color: new THREE.Color().setHSL(tl.hue / 360, .5, .55),
    roughness: .45, metalness: .35 });
  let geo;
  switch (tl.shape) {
    case 'bar': geo = boxGeo(.05, .46, .05); break;
    case 'blade': geo = boxGeo(.02, .34, .16); break;
    case 'cyl': geo = new THREE.CylinderGeometry(.035, .035, .4, 8); break;
    case 'cone': geo = new THREE.ConeGeometry(.07, .3, 8); break;
    case 'meter': geo = boxGeo(.09, .26, .18); break;
    case 'case': geo = boxGeo(.12, .2, .3); break;
    case 'coil': geo = new THREE.TorusGeometry(.13, .035, 8, 14); break;
    case 'hook': geo = new THREE.TorusGeometry(.1, .04, 8, 12, Math.PI * 1.5); break;
    default: {                                   // wrench: shaft + open head
      const grp = new THREE.Group();
      const bar = new THREE.Mesh(boxGeo(.045, .38, .045), m);
      const head = new THREE.Mesh(boxGeo(.05, .09, .14), m);
      head.position.y = .21; grp.add(bar, head);
      grp.traverse((o) => { if (o.isMesh) o.castShadow = true; });
      return grp;
    }
  }
  const mesh = new THREE.Mesh(geo, m); mesh.castShadow = true;
  return mesh;
}
function buildCrib(h, rx, rz, rw, rd) {
  const dk = h.district, crib = D.tools.cribs[dk];
  const bw = Math.max(2.4, Math.min(rd - 1.2, 4.2));
  const bx = rx + rw / 2 - .32;
  const board = box(.1, 1.7, bw, mat.part, bx, 1.5, rz, hallGroup);
  board.userData.crib = dk;
  beacons.push(board);
  box(.06, .08, bw, mat.post, bx - .06, 2.38, rz, hallGroup, false);  // rail
  crib.tools.forEach((tl, i) => {
    const row = i % 2, col = (i - row) / 2;
    const tm = toolMesh(tl);
    tm.position.set(bx - .16, row ? 1.02 : 1.9,
      rz - bw / 2 + (col + .5) * bw / 6);
    tm.rotation.x = .1;
    hallGroup.add(tm);
  });
  // the crib chest below the board, and its check-out counter
  const chest = box(.8, .62, 1.1,
    new THREE.MeshStandardMaterial({ color: 0x8a2f22, roughness: .6 }),
    bx - .6, .69, rz - bw / 2 - .2, hallGroup);
  chest.userData.crib = dk;
  beacons.push(chest);
  box(.84, .03, 1.14, mat.metal, bx - .6, 1.02, rz - bw / 2 - .2, hallGroup, false);
  const lab = label(crib.name, D.tools.drill.name + ' · ' + crib.tools.length,
    .5, { kind: 'crib' });
  lab.position.set(bx - .6, 2.85, rz); hallGroup.add(lab);
  cribCount++;
}

function buildHall(sg) {
  if (hallGroup) { scene.remove(hallGroup); disposeOf(hallGroup); }
  hallGroup = new THREE.Group(); beacons = []; floors = []; roomRects = []; curRoom = null;
  hallSolids = [];
  // Every material this hall builds for itself - wall faces, wainscots,
  // floors, luminaires - is deliberately left UNMARKED, because
  // userData.shared is what disposeOf() checks before it frees something.
  // An explicit list of them would be a second copy of a fact the traverse
  // already has, and the two could drift; the contract is the absence of
  // the mark, and web/test_3d.mjs asserts that rather than a list.
  // the room lights go with the hall; the ladder re-reads this list rather
  // than walking the scene graph looking for point lights
  roomLights = [];
  _rlDirty = true;          // a new hall re-evaluates even from a still camera
  hallGroup.name = 'tc-hall-' + sg;
  cribCount = 0;
  const h = D.halls.find(x => x.slug === sg);
  const hue = D.districts[h.district].hue;
  const W = 12 * U, DEP = h.depth * U;
  const cx = (x) => x - W/2, cz = (z) => z - DEP/2;   // centre the building

  // slab and perimeter (front face open).
  //
  // The shell used to be three boxes of mat.wall - one flat colour, the
  // same in all 111 halls, in a world whose FLOORS had twenty-two finishes.
  // The shell now wears the wall the hall's own busiest room wears (the
  // practice bay, which is where a trade's hazards actually show up), so a
  // foundry is brick-faced to the eaves and a cleanroom is coved white.
  const wallRec = D.walls[h.slug];
  const shellW = D.wallCat[wallRec.procedure.wall];
  const shellMat = wallMat(shellW, W / U * 2, 3.2);
  box(W + .6, .35, DEP + .6, mat.slab, 0, .17, 0, hallGroup);
  box(W, 3.2, .25, shellMat, 0, 1.95, cz(DEP), hallGroup);          // back
  box(.25, 3.2, DEP, shellMat, cx(0), 1.95, 0, hallGroup);          // left
  box(.25, 3.2, DEP, shellMat, cx(W), 1.95, 0, hallGroup);          // right
  // the shell is solid: the walker used to be held in a box 3 m wider than
  // the building on each side, so the side walls were scenery
  wallRect(0, cz(DEP), W / 2, .125);
  wallRect(cx(0), 0, .125, DEP / 2);
  wallRect(cx(W), 0, .125, DEP / 2);
  // the wainscot: the band at the height the work actually reaches. It is
  // the part of a working wall that gets hit, and leaving it off is most of
  // why a rendered room reads as a rendering.
  if (shellW.wainscot_m > 0) {
    const wsMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(shellW.wainscot), roughness: .8 });
    const wy = .35 + shellW.wainscot_m / 2;
    for (const b of [
      box(W - .02, shellW.wainscot_m, .06, wsMat, 0, wy, cz(DEP) - .16, hallGroup, false),
      box(.06, shellW.wainscot_m, DEP - .02, wsMat, cx(0) + .16, wy, 0, hallGroup, false),
      box(.06, shellW.wainscot_m, DEP - .02, wsMat, cx(W) - .16, wy, 0, hallGroup, false),
    ]) b.userData.wainscot = true;
  }
  // district fascia over the open front
  const fascia = new THREE.Mesh(boxGeo(W + .8, .55, .5),
    new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(hue/360, .55, .5), roughness: .5 }));
  fascia.position.set(0, 3.6, cz(0)); fascia.castShadow = true;
  hallGroup.add(fascia);
  const sign = label(h.name, D.i18n[loc].districts[h.district], 1.35,
    { kind: 'hall', hue: D.districts[h.district].hue });
  sign.position.set(0, 5.1, cz(0)); hallGroup.add(sign);

  // roof trusses across the span, and lit strips along the side walls
  for (let tz = 4; tz < DEP - 1; tz += 6) {
    box(W - .6, .18, .5, mat.metal, 0, 3.05, cz(tz), hallGroup, false);
    const lamp = new THREE.Mesh(boxGeo(1.6, .1, .5), mat.win);
    lamp.position.set(0, 2.9, cz(tz)); hallGroup.add(lamp);
  }
  for (const wx of [cx(0) + .18, cx(W) - .18]) {
    const strip = new THREE.Mesh(boxGeo(.06, .55, DEP * .8), mat.win);
    strip.position.set(wx, 2.55, 0); hallGroup.add(strip);
  }

  // rooms: tinted floor + low partitions + label.
  // The rectangles are worked out FIRST, because a doorway belongs to the
  // boundary between two rooms and cannot be placed while looking at one.
  for (const r of h.rooms)
    roomRects.push({ x0: r.x * U - W/2, x1: r.x * U - W/2 + r.w * U,
                     z0: r.y * U - DEP/2, z1: r.y * U - DEP/2 + r.h * U,
                     label: r.label, strand: r.strand });
  const doors = planDoors(roomRects, -DEP / 2);
  const stns = h.stations.map(id => D.stations[id]);
  for (const r of h.rooms) {
    const rw = r.w * U, rd = r.h * U;
    const rx = cx(r.x * U + rw/2), rz = cz(r.y * U + rd/2);
    const fin = D.finCat[D.finishes[h.slug][r.strand].surface];
    const fmat = finishMat(fin, (rw - .3) / U * 2, (rd - .3) / U * 2);
    const floor = new THREE.Mesh(boxGeo(rw - .3, .06, rd - .3), fmat);
    floor.position.set(rx, .38, rz); floor.receiveShadow = true;
    floor.name = 'room-' + r.strand;
    floor.userData.room = r.label;
    hallGroup.add(floor); floors.push(floor);
    // safety rooms carry a hazard-stripe threshold at the doorway
    if (r.strand === 'safety') {
      const stripe = new THREE.Mesh(boxGeo(Math.min(rw-.6,2.4), .07, .5),
        mat.post);
      stripe.position.set(rx, .42, rz + rd/2 - .4); hallGroup.add(stripe);
    }
    /* The trade's own fixtures. The comment here has always said "benched
       along the back of the room" and the code has always put them 0.8 m
       in from the FRONT - which was harmless while a bench was something
       you walked through, and is not now: the front edge is where a room's
       doorway onto the row in front of it is, and a 1.3 m bench across a
       1.8 m opening closes it.

       So they go against the back wall, as the comment said, and into its
       SOLID pieces - the same list the partition is drawn from - so a
       bench can never stand across a doorway. A bay holds as many benches
       as fit; a room with no solid back wall at all benches at its centre
       and the reachability test is what would catch that. */
    const bays = runSegments(doors, 'z@' + (rz + rd / 2).toFixed(2),
                             rx - rw / 2, rx + rw / 2)
      .filter(([, len]) => len >= 1.6)
      .sort((a, b2) => b2[1] - a[1]);
    const spots = [];
    for (const [c, len] of bays) {
      const k = Math.max(1, Math.floor(len / 1.6));
      for (let i2 = 0; i2 < k; i2++) spots.push(c - len / 2 + (i2 + .5) * (len / k));
    }
    (r.fixtures || []).slice(0, 3).forEach((fx, fi) => {
      const bx = spots[fi] ?? rx;
      const bz = rz + rd/2 - .8;
      box(1.3, .12, .7, mat.steel, bx, .95, bz, hallGroup);
      box(.12, .5, .6, mat.part, bx - .5, .62, bz, hallGroup);
      box(.12, .5, .6, mat.part, bx + .5, .62, bz, hallGroup);
      box(.5, .35, .35, mat.metal, bx, 1.25, bz, hallGroup);
      const fl = label(fx, null, .34, { kind: 'fixture' });
      fl.position.set(bx, 1.85, bz); hallGroup.add(fl);
      wallRect(bx, bz, .7, .4);          // you cannot walk through a bench
    });
    // The partitions used to be four boxes of one flat mat.part, in every
    // room of every hall. A room's partition now wears that ROOM's wall -
    // the marker panel in the layout room, the fabric-faced panel where
    // people talk, the mesh guard around mobile plant - so standing in a
    // hall you can read what a room is for off its walls before you read
    // its sign.
    const wal = D.wallCat[wallRec[r.strand].wall];
    const pmat = wallMat(wal, rw / U * 2, 1.1);
    const ws = wal.wainscot_m > 0 ? new THREE.MeshStandardMaterial({
      color: new THREE.Color(wal.wainscot), roughness: .8 }) : null;
    const bh = ws ? Math.min(wal.wainscot_m, .9) : 0, by = .35 + bh / 2;
    /* Doored partitions cost more boxes than solid ones did - a run can
       break into several pieces - so a room's segments are MERGED into one
       geometry per material, exactly as the campus merges its parts. The
       hall interior went from 44 partition boxes to about 80 segments and
       from 177 draw calls to 213 while they were separate; merged, it
       draws fewer than it did before any of this. */
    const wallPool = new Map(), push = (m2, ge) =>
      (wallPool.get(m2) ?? wallPool.set(m2, []).get(m2)).push(ge);
    const slab = (w2, h2, d2, x2, y2, z2) => {
      const ge = new THREE.BoxGeometry(w2, h2, d2);
      ge.translate(x2, y2, z2);
      return ge;
    };
    // along the room's width, front and back
    for (const zz of [rz - rd / 2, rz + rd / 2])
      for (const [c, len] of runSegments(doors, 'z@' + zz.toFixed(2),
                                         rx - rw / 2, rx + rw / 2)) {
        push(pmat, slab(len, 1.1, .12, c, .9, zz));
        if (ws) push(ws, slab(len, bh, .14, c, by, zz));
        wallRect(c, zz, len / 2, .06);
      }
    // and along its depth, left and right
    for (const xx of [rx - rw / 2, rx + rw / 2])
      for (const [c, len] of runSegments(doors, 'x@' + xx.toFixed(2),
                                         rz - rd / 2, rz + rd / 2)) {
        push(pmat, slab(.12, 1.1, len, xx, .9, c));
        wallRect(xx, c, .06, len / 2);
      }
    for (const [m2, list] of wallPool) {
      const merged = mergeGeometries(list);
      list.forEach((ge) => ge.dispose());
      const mesh = new THREE.Mesh(merged, m2);
      mesh.castShadow = true; mesh.receiveShadow = true;
      if (m2 === ws) mesh.userData.wainscot = true;
      hallGroup.add(mesh);
    }
    const lab = label(r.label, D.i18n[loc].strands[r.strand], .55,
      { kind: 'room' });
    lab.position.set(rx, 2.2, rz); hallGroup.add(lab);

    /* Light the room at the illuminance its own record asks for.
       D.baseCond / D.condOver have carried a lux figure per room since
       §24.2 landed, and until now it was TEXT - printed in two panels and
       nowhere in the render, so a 1000 lx inspection room and a 300 lx
       leadership room were lit identically. The figure now drives the
       luminaire over the room: brighter rooms are brighter, and the
       difference is the registry's, not a mood choice made here.

       It is a RELATIVE mapping and nothing claims otherwise - 1000 lx in
       the record does not mean 1000 lx reaching a photometer in this
       scene, and the panel that prints the number keeps §24.3's caveat. */
    const rc = condOf(h.slug, r.strand);
    const luxN = Math.max(0, Math.min(1, (rc.lux - 200) / 800));
    const lmat = new THREE.MeshStandardMaterial({
      color: 0x0b0f11, emissive: 0xffe6c0,
      emissiveIntensity: .30 + luxN * .85, roughness: .4 });
    const lum = new THREE.Mesh(boxGeo(Math.min(rw * .5, 2.2), .08, .34), lmat);
    lum.position.set(rx, 2.86, rz); hallGroup.add(lum);
    // An emissive box is a bright OBJECT, not a light - it would have made
    // the luminaire look brighter over a room that was lit exactly the same
    // as its neighbour, which is a picture of the fix rather than the fix.
    // The lamp therefore carries a real light, reaching only its own room
    // (the decay and the range are the room's, not the hall's), so a 1000 lx
    // inspection bench genuinely reads brighter than a 300 lx briefing room.
    const rl = new THREE.PointLight(0xffe9c8,
      lampCd(.55 + luxN * 1.45, 2.32, 1.7),   // 2.7 m fitting over a .38 m floor
      Math.max(rw, rd) * .85, 1.7);
    rl.position.set(rx, 2.7, rz);
    // a hall has eleven of these and a forward renderer pays for every one
    // of them on every fragment; roomLitStep() below lights the nearest few
    rl.userData.roomLight = true;
    rl.visible = qLevel !== 'low';   // the quality ladder's own budget
    hallGroup.add(rl); roomLights.push(rl);

    /* The door placard. What a room requires of you has lived in the
       registry since \u00a724.2 and could only be read by opening a panel,
       so it was possible to walk into a hot-work bay having never been told
       to put a hood on. It is hung at the doorway, at reading height, and
       it carries the room's OWN merged list - the hazard's additions
       included, because that is what the record says the room asks for.

       Rooms that require nothing get no placard rather than a sign that
       says "nothing": the explicit "none" answer is the door advisor's,
       which has a translated surface to say it in. A placard here would
       have to invent one. */
    if (rc.ppe.length) {
      const plac = label(rc.ppe.join(' \u00b7 '),
        D.i18n[loc].strands[r.strand], .42, { kind: 'placard' });
      plac.position.set(rx, 1.62, rz + rd/2 + .09);
      hallGroup.add(plac);
    }

    // stations standing in this room
    const here = stns.filter(s => s.room === r.label);
    here.forEach((s, i) => {
      const px = rx - rw/2 + (i + 1) * rw / (here.length + 1);
      const post = new THREE.Mesh(new THREE.CylinderGeometry(.09, .12, 1.5, 10), mat.post);
      post.position.set(px, 1.1, rz); post.castShadow = true;
      const gem = new THREE.Mesh(new THREE.OctahedronGeometry(.34), mat.post);
      gem.position.set(px, 2.15, rz); gem.castShadow = true;
      gem.userData.station = s.station_id; gem.userData.spin = true;
      post.userData.station = s.station_id;
      hallGroup.add(post, gem); beacons.push(gem, post);
    });

    // the district's tool crib hangs in the tools room
    if (r.strand === 'tools') buildCrib(h, rx, rz, rw, rd);
  }

  // the apron: recovered yard layout for seeded halls, a light deterministic
  // dressing for the rest. Original yard coords span ±16; fold them onto the
  // strip in front of the open face.
  const props = h.stations.length ? D.yard
    : Array.from({ length: 7 }, (_, i) => {
        const keys = Object.keys(PROPS);
        return { t: keys[(h.index * 7 + i * 3) % keys.length],
                 p: [((h.index + i * 5) % 13) - 6 + ((i % 2) ? 8 : -8), 0, -(4 + (i * 2.4) % 10)] };
      });
  for (const pr of props) {
    const fn = PROPS[pr.t]; if (!fn) continue;
    const px = pr.p[0] * (h.stations.length ? .95 : 1);
    const pz = h.stations.length ? -(DEP/2 + 3 + (pr.p[2] + 16) * .42) : cz(0) + pr.p[2];
    if (Math.abs(px) > 60 || Math.abs(pz) > 60) continue;
    fn(hallGroup, px, pz);
  }
  clearAdvisors();
  clearFauna();
  spawnHallAdvisors(h, W, DEP);
  scene.add(hallGroup);

  document.getElementById('hname').textContent = h.name + scoreChip();
  // the regional chapter line: home region marked, chapters at the rest
  const home = D.chapters.of[h.slug];
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  // the reverse of the Schools panel's own hall links: a hall that runs a
  // flipped unit gets a small badge straight back to that unit's entry
  const unit = D.schools.units.find((u) => u.hall === sg);
  document.getElementById('hfocus').innerHTML = esc(h.focus) + ' \\u00b7 '
    + Object.entries(D.chapters.regions)
        .map(([ck, ab]) => ab + (ck === home ? ' \\u2302' : ''))
        .join(' \\u00b7 ')
    + (unit ? ` <button class="barbtn" data-schools-hall="${esc(sg)}"
        style="font-size:10.5px;padding:1px 7px;vertical-align:2px">\U0001f393 flipped unit</button>` : '')
    // the reverse of the Bay Restoration panel's own hall links: a hall
    // that teaches a real field-skill track gets a badge straight back
    + (D.restoration.tracks.some((t) => t.skills.some((sk) => sk.split('.')[0] === sg))
        ? ` <button class="barbtn" data-restoration-hall="${esc(sg)}"
        style="font-size:10.5px;padding:1px 7px;vertical-align:2px">\U0001f30a Bay Restoration</button>` : '');
}

/* -------------------------------------------------------- campus view --- */
let campusGroup = null, buildings = [], hallRec = null;
// Each district's building footprints, kept in THAT DISTRICT'S OWN frame
// with the turn that gets a world point into it. These are the same
// rectangles the road layout is already checked against - a hall is one
// solid thing, and both the streets and the walker are kept out of it.
let solids = [];
const BODY_R = .45;                // shoulders, near enough, in metres
let regionGroup = null, plates = [], anchorPins = 0;
let campusKey = D.halls.some(h => h.slug === params.get('hall'))
  ? Object.keys(D.campuses).find(k =>
      D.campuses[k].halls.includes(params.get('hall')))
  : (D.campuses[params.get('campus')] ? params.get('campus') : 'treasure-island');

const campusOfHall = (sg) =>
  Object.keys(D.campuses).find(k => D.campuses[k].halls.includes(sg));

/* ---- buildings, campus roads, and the cluster frame --------------------- */
// Buildings and roads share one cluster-local frame (u lateral, v radial),
// so "roads never intersect buildings" is a rectangle test the build runs
// on itself: any overlap counts in roadFaults, and the harness asserts 0.
let roadFaults = 0, roadCount = 0;

const STYLE_OF = { industry: 'saw', transport: 'saw', earthworks: 'saw',
                   envelope: 'gable', control: 'gable',
                   structural: 'flat', systems: 'flat', energy: 'flat' };

/* Buildings pool their decoration into ONE mesh per material PER DISTRICT
   - band, trims, window strips, door and roofline of every hall in the
   district become four draw calls for the district rather than four per
   building (a 51-hall campus went from 516 draws to a third of that). The
   main box stays its own mesh: it is the raycast target the hover and
   click handlers read, and buildings[] still counts one per hall. Merged
   geometries are per-district (not shared), so disposeOf() frees them on
   rebuild. The station beacons are one InstancedMesh per campus. */
const hueMatCache = new Map();
function hueMatOf(hue) {
  let m2 = hueMatCache.get(hue);
  if (!m2) {
    m2 = new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(hue / 360, .5, .45), roughness: .6 });
    m2.userData.shared = true;   // per-hue cache, page-wide like sphereGeoCache/boxGeoCache above -
                                  // disposeOf() must never free one of these on a campus teardown
    hueMatCache.set(hue, m2);
  }
  return m2;
}
/* The campus's own built fabric: what THIS city builds with.
   Ten campuses each had their own sky, fog, sun and ground, and then all
   ten drew the same flat envelope with the same trim - ten cities told
   apart only by their weather. The facade pattern, the envelope and trim
   colours and the roofline now come from the world registry's `fabric`
   block, authored by reputation and saying so, exactly like the
   `character` line beside it. Three materials per campus, built once when
   the campus is built and freed with it. */
let fabMats = null, fabKey = null;
/* The carriageway. Every campus paved its streets in one flat grey
   (mat.road, 0x565c60) whatever its ground was - a gravel-verged estuary
   yard and a concrete island both had the same asphalt. The campus already
   declares what it is surfaced with in the world registry's `atmos.ground`,
   and the roads take it now: the same recipe, laid at a road's own repeat.
   It costs nothing in draw calls - roads merge into one mesh per material
   per campus either way - and it is freed with the campus like the rest of
   the fabric. */
function roadMatOf(ck) {
  const g = D.world.atmos?.[ck]?.ground;
  return (g === 'grass' || g === 'sand' || !g)
    ? mat.road                     // a road is never grass: fall back
    : groundMat(g, 0xb9c0c2, 16);  // tinted down, so lane paint still reads
}
// The last resort if the registry ever ships no fabric at all: the page
// still renders, in the flagship's own colours, rather than failing to boot.
const FABRIC_FALLBACK = { facade: 'panel', facade_color: '#3f4b50',
  trim: '#9db2b8', roof: 'flat', roof_color: '#6d7a7e' };
function fabricOf(ck) {
  if (fabKey === ck && fabMats) return fabMats;
  // A missing fabric table degrades to the flagship's rather than throwing:
  // this reads through TWO levels, and reading a field off an undefined
  // table is exactly the fault this bundle fixed in openCandidate and
  // openWa. It is also how this function shipped broken for one build -
  // the registry had the table and the page payload did not.
  const fab = D.world.fabric ?? {};
  const f = fab[ck] ?? fab['treasure-island'] ?? FABRIC_FALLBACK;
  const { map, normalMap } = surfaceMaps(f.facade_color, f.facade);
  const wall = new THREE.MeshStandardMaterial({ roughness: .82 });
  wall.map = map.clone(); wall.map.repeat.set(3, 3); wall.map.needsUpdate = true;
  if (normalMap) {
    wall.normalMap = normalMap.clone();
    wall.normalMap.repeat.set(3, 3); wall.normalMap.needsUpdate = true;
    wall.normalScale = new THREE.Vector2(.75, .75);
  }
  fabMats = {
    spec: f,
    road: roadMatOf(ck),
    wall,
    trim: new THREE.MeshStandardMaterial({
      color: new THREE.Color(f.trim), roughness: .55 }),
    roof: new THREE.MeshStandardMaterial({
      color: new THREE.Color(f.roof_color), roughness: .7, metalness: .25 }),
  };
  fabKey = ck;
  return fabMats;
}

function building(h, style, g, pool, ox = 0, oz = 0) {   // built at the local origin, door toward -z
  const fab = fabricOf(campusKey);
  const dep = Math.max(h.depth, 5), wid = 12;
  const hgt = 6 + (h.depth % 3) * .7;
  const bld = box(wid, hgt, dep, fab.wall, 0, hgt / 2, 0, g);
  bld.userData.slug = h.slug;
  const parts = pool;                // material -> [transformed geometries], district-wide
  const add = (m2, w, hh, d2, x, y, z, rz = 0) => {
    const ge = new THREE.BoxGeometry(w, hh, d2);
    const mx = new THREE.Matrix4().makeRotationZ(rz).setPosition(x + ox, y, z + oz);
    ge.applyMatrix4(mx);
    (parts.get(m2) ?? parts.set(m2, []).get(m2)).push(ge);
  };
  const hueMat = hueMatOf(D.districts[h.district].hue);
  add(hueMat, wid + .4, .9, dep + .4, 0, hgt - .2, 0);
  for (const [tx, tz] of [[-wid/2, -dep/2], [wid/2, -dep/2],
                          [-wid/2, dep/2], [wid/2, dep/2]])
    add(hueMat, .5, hgt, .5, tx, hgt / 2, tz);
  for (const zz of [-dep/2 - .03, dep/2 + .03])
    add(mat.win, wid * .78, .7, .06, 0, hgt * .55, zz);
  add(fab.trim, 1.6, 2.4, .1, 0, 1.2, -dep/2 - .06);   // the door surround
  if (style === 'saw') {              // industrial sawtooth roofline
    for (let sx = -wid/2 + 2; sx < wid/2 - .5; sx += 4)
      add(fab.roof, 3.2, 1.5, dep - .6, sx, hgt + .55, 0, .42);
  } else if (style === 'gable') {     // pitched pair
    add(fab.roof, wid * .6, .5, dep + .3, -wid * .24, hgt + 1.1, 0, .48);
    add(fab.roof, wid * .6, .5, dep + .3, wid * .24, hgt + 1.1, 0, -.48);
  } else {                            // flat: parapet already, rooftop unit
    add(fab.roof, 1.6, .8, 1.2, wid * .22, hgt + .4, dep * .15);
  }
  // the pilasters at the corners wear the city's trim, not one shared steel
  for (const px of [-wid/2 + .3, wid/2 - .3])
    add(fab.trim, .34, hgt * .92, .34, px, hgt * .46, -dep/2 + .2);
  if (h.stations.length) beaconAt.push(new THREE.Vector3(0, hgt + 2, 0));
  else beaconAt.push(null);
  return { mesh: bld, w: wid, d: dep };
}
// the district's pooled decoration: one mesh per material, into the district group
function flushParts(pool, g) {
  for (const [m2, list] of pool) {
    const merged = mergeGeometries(list);
    list.forEach((ge) => ge.dispose());
    const mesh = new THREE.Mesh(merged, m2);
    mesh.castShadow = true; mesh.receiveShadow = true;
    g.add(mesh);
  }
  pool.clear();
}
// the station beacons: one instanced draw for the campus, spun in the loop
let beaconAt = [], beaconInst = null, beaconSpin = 0;
const _bcnM = new THREE.Matrix4();
function flushBeacons(spots, g) {
  beaconInst = null;
  if (!spots.length) return;
  beaconInst = new THREE.InstancedMesh(new THREE.OctahedronGeometry(.9), mat.post, spots.length);
  beaconInst.userData.spots = spots;
  beaconInst.castShadow = true;
  spinBeacons(0);
  g.add(beaconInst);
}
function spinBeacons(dt) {
  if (!beaconInst) return;
  beaconSpin += dt * 1.1;
  const spots = beaconInst.userData.spots;
  for (let i = 0; i < spots.length; i++) {
    _bcnM.makeRotationY(beaconSpin).setPosition(spots[i]);
    beaconInst.setMatrixAt(i, _bcnM);
  }
  beaconInst.instanceMatrix.needsUpdate = true;
}

/* Roads and lane dashes accumulate in the district's own frame and merge
   into ONE mesh per material per campus build (the dashes were the largest
   single mesh swarm on the board; the road planes were the next). Each
   piece is carried into campus coordinates through the district group's
   world matrix as it is added - the dashes used to be merged straight into
   the campus group in district-local (u, v), which drew them across the
   plaza instead of along their streets. */
const roadAcc = new Map();          // material -> [world-space geometries]
let dashAcc = [], dashFrame = null;
const _rdM = new THREE.Matrix4();
function roadRect(u, v, w, len, m, g, y = .05) {
  const ge = new THREE.PlaneGeometry(w, len);
  _rdM.makeRotationX(-Math.PI / 2).setPosition(u, y, v);
  g.updateWorldMatrix(true, false);
  ge.applyMatrix4(_rdM).applyMatrix4(g.matrixWorld);
  (roadAcc.get(m) ?? roadAcc.set(m, []).get(m)).push(ge);
  return { u, v, w, h: len };
}
function flushRoads(g) {
  for (const [m, list] of roadAcc) {
    const merged = mergeGeometries(list);
    list.forEach((ge) => ge.dispose());
    const mesh = new THREE.Mesh(merged, m);
    mesh.receiveShadow = true;
    g.add(mesh);            // roadCount counts rectangles laid, not meshes drawn
  }
  roadAcc.clear();
}
function dashGeo(w, d2, x, z, ry = 0) {
  const ge = new THREE.BoxGeometry(w, .02, d2);
  ge.applyMatrix4(new THREE.Matrix4().makeRotationY(ry).setPosition(x, .09, z));
  if (dashFrame) { dashFrame.updateWorldMatrix(true, false); ge.applyMatrix4(dashFrame.matrixWorld); }
  dashAcc.push(ge);
}
function dashesU(u0, u1, v, g) {
  dashFrame = g;
  for (let u = u0 + 2; u < u1 - 2; u += 4) dashGeo(1.6, .16, u, v);
  dashFrame = null;
}
function dashesV(v0, v1, u, g) {
  dashFrame = g;
  for (let v = v0 + 2; v < v1 - 2; v += 4) dashGeo(.16, 1.6, u, v);
  dashFrame = null;
}
function flushDashes(g) {
  if (!dashAcc.length) return;
  const merged = mergeGeometries(dashAcc);
  dashAcc.forEach((ge) => ge.dispose());
  dashAcc = [];
  const mesh = new THREE.Mesh(merged, mat.paint);
  mesh.receiveShadow = true;
  g.add(mesh);
}

/* ------------------------------ campus dressing, keyed by campus slug --- */
function dressCampus(key, g, R) {
  if (key === 'treasure-island') {
    // the island: a bay ring beyond the ground's edge and a flag over the plaza
    const bay = new THREE.Mesh(new THREE.RingGeometry(GROUND_R - 2, GROUND_R + 760, 64), mat.water);
    bay.rotation.x = -Math.PI / 2; bay.position.y = -.08; g.add(bay);
    box(.14, 15, .14, mat.metal, 0, 7.5, -30, g);
    const flag = new THREE.Mesh(new THREE.PlaneGeometry(4.6, 2.6),
      new THREE.MeshStandardMaterial({ color: 0xE8A33D, side: THREE.DoubleSide }));
    flag.position.set(2.4, 13.4, -30); g.add(flag);
  }
  if (key === 'oakland') {
    // container rows and a gantry crane on the estuary edge
    const cols = [0xB3462F, 0x3A5A78, 0x5B7A5A, 0x8a6a42, 0x41626b];
    for (let i = 0; i < 14; i++) {
      const cx = -46 + (i % 7) * 15, cz = R + 34 + Math.floor(i / 7) * 6;
      const stack = 1 + (i * 7) % 3;
      for (let sN = 0; sN < stack; sN++) {
        const c = box(12, 2.6, 2.5, new THREE.MeshStandardMaterial({
          color: cols[(i + sN) % cols.length], roughness: .8 }),
          cx, 1.3 + sN * 2.6, cz, g);
        c.castShadow = true;
      }
    }
    for (const lx of [-14, 14]) {
      box(1.2, 26, 1.2, mat.metal, lx, 13, R + 46, g);
      box(1.2, 26, 1.2, mat.metal, lx, 13, R + 52, g);
    }
    box(34, 1.6, 2, mat.post, 0, 26, R + 49, g);
    const quay = new THREE.Mesh(new THREE.PlaneGeometry(400, 160), mat.water);
    quay.rotation.x = -Math.PI / 2; quay.position.set(0, -.06, R + 140); g.add(quay);
  }
  if (key === 'new-orleans') {
    // the river: a broad channel, pilings, and a working barge
    const river = new THREE.Mesh(new THREE.PlaneGeometry(560, 130), mat.water);
    river.rotation.x = -Math.PI / 2; river.position.set(0, -.06, R + 105); g.add(river);
    box(440, 2.4, 5, mat.slab, 0, 1.2, R + 38, g);      // the levee
    for (let i = 0; i < 12; i++)
      box(.8, 3.6, .8, mat.wood, -110 + i * 20, 1.2, R + 50, g);
    box(30, 2, 10, mat.part, 26, .9, R + 78, g);        // barge hull
    box(6, 3, 4, mat.metal, 36, 3.4, R + 78, g);        // wheelhouse
  }
  if (key === 'houston') {
    // the hub has no district ring to dress a road frontage against, so
    // its skyline stands free on the green: a refinery silhouette on the
    // horizon (tanks, a flare stack) rather than anything at the plaza -
    // a hub campus is a real place to stand, not an empty green circle
    const tankMat = new THREE.MeshStandardMaterial({ color: 0x7a8288, roughness: .85 });
    for (let i = 0; i < 6; i++) {
      const ang = i / 6 * Math.PI * 2 + .3, rad = R + 60 + (i % 2) * 22;
      const h = 9 + (i % 3) * 4;
      const t = new THREE.Mesh(new THREE.CylinderGeometry(6, 6, h, 16), tankMat);
      t.position.set(Math.cos(ang) * rad, h / 2, Math.sin(ang) * rad);
      t.castShadow = true; g.add(t);
    }
    const stack = box(1.6, 34, 1.6, mat.metal, R + 92, 17, -R - 20, g);
    stack.castShadow = true;
    const flame = new THREE.Mesh(new THREE.ConeGeometry(1.4, 3.6, 8),
      new THREE.MeshBasicMaterial({ color: 0xff8a3c }));
    flame.position.set(R + 92, 35.6, -R - 20); g.add(flame);
    const chan = new THREE.Mesh(new THREE.PlaneGeometry(420, 90), mat.water);
    chan.rotation.x = -Math.PI / 2; chan.position.set(0, -.06, -(R + 130)); g.add(chan);
  }
  if (key === 'chicago') {
    // the second hub, dressed the same way as the first: a free skyline
    // on the green rather than anything at the plaza. Generic massing
    // only - no real building is modeled or named - plus an elevated
    // rail viaduct, schematic like every road on this network.
    const skyMat = new THREE.MeshStandardMaterial({ color: 0x2b3038, roughness: .8 });
    for (let i = 0; i < 9; i++) {
      const ang = i / 9 * Math.PI * 2 + .5, rad = R + 55 + (i % 3) * 16;
      const h = 14 + (i * 5) % 26;
      const t = box(4.4, h, 4.4, skyMat, Math.cos(ang) * rad, h / 2, Math.sin(ang) * rad, g);
      t.castShadow = true;
    }
    const pierMat = mat.metal;
    for (let i = 0; i < 10; i++) {
      const px = -108 + i * 24;
      box(1, 8, 1, pierMat, px, 4, R + 70, g);
      box(1, 8, 1, pierMat, px, 4, R + 78, g);
    }
    const track = box(240, .8, 10, mat.part, -0, 8.2, R + 74, g);
    track.castShadow = true;
    const lake = new THREE.Mesh(new THREE.PlaneGeometry(460, 140), mat.water);
    lake.rotation.x = -Math.PI / 2; lake.position.set(0, -.06, -(R + 140)); g.add(lake);
  }
  if (key === 'seattle') {
    // the third hub, dressed the same way as the first two: a free
    // skyline on the green rather than anything at the plaza. Generic
    // massing only - no real building is modeled or named - plus a
    // container-gantry crane for the working port and the Sound itself
    // as a schematic water band.
    const skyMat = new THREE.MeshStandardMaterial({ color: 0x333c42, roughness: .82 });
    for (let i = 0; i < 8; i++) {
      const ang = i / 8 * Math.PI * 2 + .4, rad = R + 58 + (i % 2) * 18;
      const h = 10 + (i % 4) * 6;
      const t = box(5, h, 5, skyMat, Math.cos(ang) * rad, h / 2, Math.sin(ang) * rad, g);
      t.castShadow = true;
    }
    const craneMat = mat.metal;
    const craneLeg1 = box(1.2, 20, 1.2, craneMat, R + 96, 10, -R - 16, g);
    const craneLeg2 = box(1.2, 20, 1.2, craneMat, R + 96, 10, -R - 30, g);
    craneLeg1.castShadow = craneLeg2.castShadow = true;
    const craneBoom = box(60, 1.4, 1.4, craneMat, R + 66, 20.6, -R - 23, g);
    craneBoom.castShadow = true;
    const sound = new THREE.Mesh(new THREE.PlaneGeometry(460, 140), mat.water);
    sound.rotation.x = -Math.PI / 2; sound.position.set(0, -.06, -(R + 130)); g.add(sound);
  }
  if (key === 'pittsburgh') {
    // the fourth hub, dressed the same way as the first three: a free
    // skyline on the green rather than anything at the plaza. Generic
    // massing only - no real building is modeled or named - plus a
    // schematic steel truss bridge, standing in for the bridge city's
    // best-known feature, and a river band behind it.
    const skyMat = new THREE.MeshStandardMaterial({ color: 0x3a3630, roughness: .8 });
    for (let i = 0; i < 7; i++) {
      const ang = i / 7 * Math.PI * 2 + .35, rad = R + 56 + (i % 2) * 20;
      const h = 11 + (i % 3) * 7;
      const t = box(4.6, h, 4.6, skyMat, Math.cos(ang) * rad, h / 2, Math.sin(ang) * rad, g);
      t.castShadow = true;
    }
    const steelMat = mat.metal;
    for (const bx of [-14, 14]) {
      const pier = box(1, 9, 1, steelMat, bx, 4.5, R + 60, g);
      pier.castShadow = true;
    }
    const deck = box(30, .8, 4, mat.road, 0, 9, R + 60, g);
    deck.castShadow = true;
    for (let i = 0; i < 6; i++) {
      const sx = -13 + i * 5.2;
      const strut = box(.7, 6.5, .7, steelMat, sx, 12.2, R + 60, g);
      strut.rotation.z = (i % 2 === 0) ? .5 : -.5;
      strut.castShadow = true;
    }
    const river = new THREE.Mesh(new THREE.PlaneGeometry(420, 120), mat.water);
    river.rotation.x = -Math.PI / 2; river.position.set(0, -.06, -(R + 120)); g.add(river);
  }
  if (key === 'denver') {
    // the fifth hub, dressed the same way as the first four: a free
    // skyline on the green rather than anything at the plaza, plus a
    // schematic mountain-range silhouette standing on the western
    // horizon for the Front Range/Rockies the campus is named for.
    // Generic massing only - no real building or peak is modeled or
    // named.
    const skyMat = new THREE.MeshStandardMaterial({ color: 0x35383c, roughness: .8 });
    for (let i = 0; i < 8; i++) {
      const ang = i / 8 * Math.PI * 2 + .3, rad = R + 56 + (i % 2) * 18;
      const h = 10 + (i % 3) * 6;
      const t = box(4.6, h, 4.6, skyMat, Math.cos(ang) * rad, h / 2, Math.sin(ang) * rad, g);
      t.castShadow = true;
    }
    const peakMat = new THREE.MeshStandardMaterial({ color: 0x565a5e, roughness: .95 });
    const snowMat = new THREE.MeshStandardMaterial({ color: 0xe8ecef, roughness: .7 });
    for (let i = 0; i < 9; i++) {
      const px = -180 + i * 46, ph = 26 + (i % 4) * 10;
      const peak = new THREE.Mesh(new THREE.ConeGeometry(22, ph, 4), peakMat);
      peak.rotation.y = Math.PI / 4;
      peak.position.set(px, ph / 2, -(R + 170));
      peak.castShadow = true; g.add(peak);
      const cap = new THREE.Mesh(new THREE.ConeGeometry(8, ph * .28, 4), snowMat);
      cap.rotation.y = Math.PI / 4;
      cap.position.set(px, ph - ph * .14, -(R + 170));
      g.add(cap);
    }
  }
  if (key === 'miami') {
    // the sixth hub, dressed the same way as the first five: a free
    // skyline on the green rather than anything at the plaza, plus a
    // schematic gantry crane standing in for the working seaport at
    // Dodge Island and a row of stylized palm silhouettes along the
    // shore. Generic massing only - no real building, crane or palm
    // species is modeled or named.
    const skyMat = new THREE.MeshStandardMaterial({ color: 0xe4e0d4, roughness: .75 });
    for (let i = 0; i < 8; i++) {
      const ang = i / 8 * Math.PI * 2 + .25, rad = R + 56 + (i % 2) * 18;
      const h = 12 + (i % 4) * 8;
      const t = box(4.8, h, 4.8, skyMat, Math.cos(ang) * rad, h / 2, Math.sin(ang) * rad, g);
      t.castShadow = true;
    }
    const craneMat = mat.metal;
    const craneLeg1 = box(1.2, 18, 1.2, craneMat, R + 92, 9, -R - 18, g);
    const craneLeg2 = box(1.2, 18, 1.2, craneMat, R + 92, 9, -R - 32, g);
    craneLeg1.castShadow = craneLeg2.castShadow = true;
    const craneBoom = box(56, 1.4, 1.4, craneMat, R + 64, 18.6, -R - 25, g);
    craneBoom.castShadow = true;
    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x6b5238, roughness: .9 });
    const frondMat = new THREE.MeshStandardMaterial({ color: 0x2f6b3a, roughness: .8 });
    for (let i = 0; i < 7; i++) {
      const px = -160 + i * 50, pz = R + 96;
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(.55, .8, 9, 6), trunkMat);
      trunk.position.set(px, 4.5, pz);
      trunk.castShadow = true; g.add(trunk);
      for (let k = 0; k < 6; k++) {
        const frond = new THREE.Mesh(new THREE.ConeGeometry(.6, 5.5, 3), frondMat);
        frond.position.set(px, 9.6, pz);
        frond.rotation.z = Math.PI / 2.3;
        frond.rotation.y = k / 6 * Math.PI * 2;
        frond.castShadow = true; g.add(frond);
      }
    }
    const bay = new THREE.Mesh(new THREE.PlaneGeometry(480, 150), mat.water);
    bay.rotation.x = -Math.PI / 2; bay.position.set(0, -.06, -(R + 140)); g.add(bay);
  }
  if (key === 'detroit') {
    // the seventh and final hub, dressed the same way as the first six: a
    // free skyline on the green rather than anything at the plaza, plus a
    // row of schematic factory sheds and smokestacks standing in for a
    // century of automotive-industrial manufacturing, and the Detroit
    // River as schematic water along the campus's southern edge. Generic
    // massing only - no real plant, building or stack is modeled or named.
    const skyMat = new THREE.MeshStandardMaterial({ color: 0x4a4640, roughness: .8 });
    for (let i = 0; i < 8; i++) {
      const ang = i / 8 * Math.PI * 2 + .2, rad = R + 56 + (i % 2) * 18;
      const h = 11 + (i % 3) * 7;
      const t = box(4.6, h, 4.6, skyMat, Math.cos(ang) * rad, h / 2, Math.sin(ang) * rad, g);
      t.castShadow = true;
    }
    const shedMat = new THREE.MeshStandardMaterial({ color: 0x585048, roughness: .85 });
    const stackMat = new THREE.MeshStandardMaterial({ color: 0x3a3632, roughness: .7 });
    const bandMat = new THREE.MeshStandardMaterial({ color: 0xb3402a, roughness: .6 });
    for (let i = 0; i < 4; i++) {
      const sx = -150 + i * 44, sz = R + 96;
      const shed = box(30, 8, 14, shedMat, sx, 4, sz, g);
      shed.castShadow = true;
      for (let k = 0; k < 2; k++) {
        const stx = sx - 8 + k * 16;
        const stack = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.5, 16, 10), stackMat);
        stack.position.set(stx, 16, sz);
        stack.castShadow = true; g.add(stack);
        const band = new THREE.Mesh(new THREE.CylinderGeometry(1.15, 1.15, 1.2, 10), bandMat);
        band.position.set(stx, 22, sz); g.add(band);
      }
    }
    const river = new THREE.Mesh(new THREE.PlaneGeometry(480, 140), mat.water);
    river.rotation.x = -Math.PI / 2; river.position.set(0, -.06, -(R + 140)); g.add(river);
  }
}

/* ------------------------------------------------- the city layer -------- */
// A campus with a RECORDED city frame (New Orleans, from Locator.X's
// region record) grows into its real surroundings: each institution from
// the POI table stands at its true east/north offset (13 units per km,
// walkable), joined to the ring road by SCHEMATIC avenues; the river and
// lake bands are schematic too, and the labels say which is which.
let cityPois = 0, walkLim = 169, cityHits = [], chapterHit = [], restorationHits = [];

/* The regional chapter hall: one pavilion on each plaza carrying every
   union homed elsewhere - the 111-trade network made visible per campus.
   An Academy structure only; the panel repeats the no-local-named honesty. */
function openChapters() {
  const hosted = D.halls.filter((h) => D.chapters.of[h.slug] !== campusKey);
  const byHome = {};
  for (const h of hosted) (byHome[D.chapters.of[h.slug]] ??= []).push(h.name);
  document.getElementById('pbody').innerHTML = `
    <h2>${t('chapters.hall')}</h2>
    <span class="chip">${D.campuses[campusKey].name}</span>
    <span class="chip">${hosted.length} / 111</span>
    ${Object.entries(byHome).map(([ck, names]) => `
      <h3>${D.campuses[ck].name} · ${D.chapters.regions[ck]}</h3>
      <p style="color:var(--muted);font-size:13px;line-height:1.7">${names.join(' · ')}</p>`).join('')}
    <p style="color:var(--muted);font-size:12px">${D.chapters.honesty}</p>`;
  document.body.classList.add('open');
}
window.__tc3dChapters = openChapters;

/* ------------------------------------------------- the campus training yard --
   Simulation used to be something you reached through a PANEL: enter a
   hall, open its sim list, click a seat. The seats were never anywhere.
   This puts them on the ground, on the campus green between the plaza and
   the ring, as a fenced yard with a stand for each seat the campus can
   actually teach - walk up to one and it opens, exactly as a hall does.

   Which seats: the ones bound to halls THIS campus hosts, read from the
   sims registry's own bindings. A hub campus hosts no halls of its own, so
   it draws no yard - its chapter seats are a roster of trades, never a
   place, which is the same line the chapter hall panel already holds. */
// Each training stand's pad, where it stands and what it is made of. A
// stand wears its seat's own declared yard surface - crushed stone under
// the excavator, an asphalt apron under the crane, a sealed slab under the
// load-chart board - so stepping onto one off the campus concrete is a
// change you can hear. The rect is recorded where the pad is BUILT.
let yardPads = [];
let seatHits = [], nearSeat = null;
function buildTrainingYard(g, R) {
  seatHits = []; yardPads = [];
  const halls = new Set(D.campuses[campusKey]?.halls ?? []);
  if (!halls.size) return;                       // a hub: no home halls, no yard
  const seats = [...new Set([...halls]
    .flatMap((sg) => (D.sims.bindings[sg] ?? []).map((b) => b.sim)))]
    .filter((id) => D.sims.sims[id])
    .sort();
  if (!seats.length) return;
  const fab = fabricOf(campusKey);
  const yg = new THREE.Group();
  // on the green, off to one side of the plaza so it never fights the
  // dispatcher or the chapter hall for the same ground
  const YR = Math.min(46, Math.max(26, seats.length * 4.2));
  yg.position.set(-(R * .52), 0, R * .40);
  g.add(yg);

  // the apron: the campus's own ground worked into a hard standing
  const apron = new THREE.Mesh(new THREE.CircleGeometry(YR * .62, 40),
    groundMat(D.world.atmos[campusKey]?.ground ?? 'concrete'));
  apron.rotation.x = -Math.PI / 2; apron.position.y = .04;
  apron.receiveShadow = true; yg.add(apron);

  // a stand per seat, ringed, each wearing the district hue of the first
  // hall that teaches it - so the yard reads as this campus's own trades
  seats.forEach((id, i) => {
    const def = D.sims.sims[id];
    const a = i / seats.length * Math.PI * 2;
    const sx = Math.cos(a) * YR * .40, sz = Math.sin(a) * YR * .40;
    const homeHall = def.halls.find((sg) => halls.has(sg));
    const hue = homeHall ? D.districts[D.halls.find((h) => h.slug === homeHall).district].hue : 40;
    const padFin = D.finCat[def.yard.surface];
    const pad = new THREE.Mesh(boxGeo(5.2, .18, 5.2),
      finishMat(padFin, 5.2 / U * 2, 5.2 / U * 2));
    pad.position.set(sx, .12, sz); pad.receiveShadow = true; yg.add(pad);
    yardPads.push({ x: yg.position.x + sx, z: yg.position.z + sz,
                    hw: 2.6, hd: 2.6, fam: famOfFinish(padFin) });
    const post = new THREE.Mesh(new THREE.CylinderGeometry(.16, .2, 2.5, 10),
      hueMatOf(hue));
    post.position.set(sx, 1.35, sz); post.castShadow = true;
    post.userData.seat = id; yg.add(post); seatHits.push(post);
    campusSolid(yg.position.x + sx, yg.position.z + sz, .24);
    const head = new THREE.Mesh(new THREE.OctahedronGeometry(.62), mat.post);
    head.position.set(sx, 3.1, sz); head.castShadow = true;
    head.userData.seat = id; yg.add(head); seatHits.push(head);
    const sl = label(def.name, def.yard.name, .82, { kind: 'station', hue });
    sl.position.set(sx, 4.6, sz); yg.add(sl);
  });

  // the gate sign, so the yard says what it is before you are in it
  const gs = label(t('yard.name'), seats.length + ' ' + t('yard.seats'), 1.25,
    { kind: 'district' });
  gs.position.set(0, 6.4, YR * .52); yg.add(gs);
  // a light mast, because this is a working yard like any other
  box(.3, 8, .3, mat.metal, 0, 4, -YR * .5, yg);
  box(1.4, .3, .5, mat.win, 0, 8.2, -YR * .5, yg, false);
  campusSolid(yg.position.x, yg.position.z - YR * .5, .3);
  const ml = new THREE.PointLight(0xffe9c8, lampCd(1.2, 7.7, 1.6), YR * 1.4, 1.6);
  ml.position.set(0, 7.7, -YR * .5); ml.visible = qLevel !== 'low';
  yg.add(ml); roomLights.push(ml);
  // and the yard's perimeter, in the campus's own trim
  for (let k = 0; k < 28; k++) {
    const a = k / 28 * Math.PI * 2;
    const px = Math.cos(a) * YR * .6, pz = Math.sin(a) * YR * .6;
    box(.13, 1.5, .13, fab.trim, px, .75, pz, yg, false);
    campusSolid(yg.position.x + px, yg.position.z + pz, .16);
  }
}

function buildChapterHall(g, key) {
  // Seven of the ten campuses are HUBS: no districts, no halls, and so no
  // buildings at all - the fabric above would have dressed nothing there.
  // The chapter hall is the one building a hub actually has, so it is
  // where that city's fabric has to show: its envelope, its trim band and
  // its roof, the same three materials the hall districts wear.
  const fab = fabricOf(key);
  const pav = new THREE.Group(); g.add(pav);
  const base = new THREE.Mesh(new THREE.CylinderGeometry(7, 7.6, .9, 8), mat.slab);
  base.position.y = .45; base.receiveShadow = true; pav.add(base);
  const walls = new THREE.Mesh(new THREE.CylinderGeometry(5.6, 6, 4.2, 8), fab.wall);
  walls.position.y = 3; walls.castShadow = walls.receiveShadow = true; pav.add(walls);
  const band = new THREE.Mesh(new THREE.CylinderGeometry(5.75, 5.75, .5, 8), fab.trim);
  band.position.y = 4.6; pav.add(band);
  const roof = new THREE.Mesh(new THREE.ConeGeometry(7.2, 2.6, 8), fab.roof);
  roof.position.y = 6.5; roof.castShadow = true; pav.add(roof);
  walls.userData.chapters = true;
  chapterHit = [walls];
  // it is a building, and the walker used to go straight through it
  campusSolid(0, 0, 6);
  const cl = label(t('chapters.hall'), '+' + D.chapters.hosted[key], 2,
    { kind: 'district' });
  cl.position.y = 12; pav.add(cl);
}
const CITY_S = 13;   // units per real kilometre in the city layer

/* An institution's panel: the RECORDED coordinate with a live-map link
   built from it, the authored blurb labelled as authored, and the union
   honesty line - hall addresses are not recorded, no local is named. */
/* elevation (USGS EPQS) and aerial imagery (USGS National Map): the shared
   web/groundtruth.py module, so this page and web/build_geomap.py cannot
   drift into two different answers for the same coordinate. */
__GROUND_TRUTH_JS__
// this page's own D is always the first argument the shared module wants;
// elevationLookup keeps its old two-argument call shape for every existing
// call site below rather than touching each one.
function elevationLookup(lat, lng, cb) { gtElevationLookup(D, lat, lng, cb); }

function openCityPoi(name) {
  const p = (D.geo.cityPois?.[campusKey] ?? []).find((x) => x.name === name);
  if (!p) return;
  const osm = `https://www.openstreetmap.org/?mlat=${p.lat}&mlon=${p.lng}`
    + `#map=16/${p.lat}/${p.lng}`;
  const recorded = p.prov === 'RECORDED';
  document.getElementById('pbody').innerHTML = `
    <h2>${p.name}</h2>
    <span class="chip" style="border-color:var(${recorded ? '--good' : '--mark'});color:var(${recorded ? '--good' : '--mark'})">${p.prov}</span>
    <span class="chip">${p.km} km · ${p.bearing}°</span>
    ${p.blurb ? `<p>${p.blurb}</p>` : ''}
    <p style="font-family:'IBM Plex Mono',monospace;font-size:13.5px">
      ${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}
      <span style="color:var(--muted)">WGS84</span></p>
    <p><a href="${osm}" target="_blank" rel="noopener"
      style="color:var(--steel)">↗ OpenStreetMap</a>
      <span style="color:var(--muted)">· live map from the ${p.prov} coordinate</span></p>
    <p id="elevRow">
      <button class="opt" id="elevGo" style="display:inline-block;width:auto;padding:5px 12px">
        ↕ Look up ground elevation</button></p>
    <p style="color:var(--muted);font-size:12px">coordinate: ${p.src}${
      p.bp ? `<br>description: ${p.bp}` : ''}</p>
    <p style="color:var(--muted);font-size:12px">${t('honesty.taxonomy')}</p>`;
  document.body.classList.add('open');
  const go = document.getElementById('elevGo');
  go?.addEventListener('click', () => {
    go.textContent = 'Looking up…'; go.disabled = true;
    gtElevationInto(document.getElementById('elevRow'), D, p.lat, p.lng, false);
  });
}
window.__tc3dPoi = openCityPoi;   // test hook
window.__tc3dElev = elevationLookup;   // test hook

/* Bay Restoration site markers: a real, AUTHORED-FROM-PUBLIC-RECORD point
   (restoration/build.py), re-projected onto the SAME log-eased bay-scale
   ring the campus's own far city anchors use - decoupled from cityLog so
   a site lands in a walkable, rendered band regardless of how close this
   campus's institution layer happens to sit. Clicking one opens the same
   Bay Restoration panel the toolbar button does, focused on that site. */
function restoPos(p) {
  const km = Math.hypot(p.e, p.n) || .001;
  // within 15km, the same true linear km scale the institution layer uses;
  // beyond it, the log-eased ring (matching cityPos's own far-anchor
  // mode) keeps a distant site inside a walkable, rendered radius
  if (km <= 15) return [p.e * CITY_S, -p.n * CITY_S];
  const r = 96 + 95 * Math.log10(1 + km);
  return [p.e / km * r, -p.n / km * r];
}
// real ground truth at a restoration site's own coordinate, fetched only
// on click, from the SAME two sources the city layer's institution panels
// already use - never a second copy of either service's contract. This
// stays a flat 2D panel result, never blended into the walkable scene's
// own ground: that ground is deliberately schematic and non-real-scale
// (restoPos above compresses real distance onto a walkable 46-unit
// radius), so a real photo laid under it would misstate what is real.
function siteElevation(id, lat, lng) {
  gtElevationInto(document.getElementById('elevr-' + id), D, lat, lng, true);
}
function singleTileUrl(lat, lng, z) { return gtSingleTileUrl(D, lat, lng, z, SAT_TILES); }
function siteAerial(id, lat, lng) {
  gtAerialInto(document.getElementById('satr-' + id), D, lat, lng, SAT_TILES);
}
window.__tc3dSiteElev = siteElevation;   // test hook
window.__tc3dSiteAerial = siteAerial;    // test hook

function buildRestorationSites(g) {
  const sites = D.restoration.sites.filter((s) => s.campus === campusKey && s.e !== undefined);
  if (!sites.length) return;
  const pad = new THREE.MeshStandardMaterial({ color: 0x2f6b52, roughness: .92 });
  const post = new THREE.MeshStandardMaterial({ color: 0x6b5a3a, roughness: .8 });
  sites.forEach((s) => {
    const [x, z] = restoPos(s);
    const p = box(9, .12, 9, pad, x, .12, z, g, false);
    const m = box(.5, 2.6, .5, post, x, 1.4, z, g);
    p.userData.restorationSite = m.userData.restorationSite = s.id;
    restorationHits.push(p, m);
    const rl = label(s.name, (s.workforce ? 'workforce pathway \\u00b7 ' : '')
      + 'AUTHORED \\u00b7 real site', 1.4, { kind: 'schematic' });
    rl.position.set(x, 5, z); g.add(rl);
  });
}

// Two placement modes, both labelled with REAL kilometres: a compact city
// (New Orleans) lays its places at true linear offsets; a bay-scale region
// (the SF Bay, cities out to ~29 km) compresses distance the same way the
// network view does - true bearings, log-eased range - because a linear
// board that far would not be walkable. The i18n geo note states the deal.
let cityLog = false;
function cityPos(p) {
  const km = Math.hypot(p.e, p.n) || .001;
  if (!cityLog) return [p.e * CITY_S, -p.n * CITY_S];
  const r = 96 + 95 * Math.log10(1 + p.km);
  return [p.e / km * r, -p.n / km * r];
}
/* ------------------------------------------- orthoimagery ground ------- */
// The campus city layer places its RECORDED anchors at true east/north
// offsets from the campus point. This lays the authority's own public-
// domain orthoimagery underneath them at the SAME scale, georeferenced
// off the same record, so the picture and the points agree. Fetched in
// this browser from the cited service - never bundled - and a tile that
// does not arrive leaves the SCHEMATIC ground exactly as it was.
let satPlane = null, satState = 'off';
// an operator may point this at their own mirror of the same service;
// the harness uses it to prove the drawing path without the public one
const SAT_TILES = params.get('imagery') || null;
const SAT_Z = 14, SAT_SPAN = 3;          // a 3x3 tile block on the campus
const tileLat = (y, n) =>
  Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) * 180 / Math.PI;
function satClear() {
  if (satPlane) { scene.remove(satPlane); satPlane.material.map?.dispose();
    satPlane.geometry.dispose(); satPlane = null; }
}
async function satGround() {
  if (satPlane) {                        // a second press puts it away
    satClear(); satState = 'off';
    document.getElementById('hint').textContent = t('hint.campus');
    return;
  }
  const pt = D.geo.campuses[campusKey];
  const n = 2 ** SAT_Z;
  const x0 = Math.floor((pt.lng + 180) / 360 * n) - 1;
  const la = pt.lat * Math.PI / 180;
  const y0 = Math.floor((1 - Math.log(Math.tan(la) + 1 / Math.cos(la))
    / Math.PI) / 2 * n) - 1;
  satState = 'loading';
  document.getElementById('hint').textContent =
    'Asking ' + D.imagery.authority + ' for orthoimagery...';
  const S = 256;
  const cv = document.createElement('canvas');
  cv.width = cv.height = S * SAT_SPAN;
  const cx2 = cv.getContext('2d');
  try {
    await Promise.all(Array.from({ length: SAT_SPAN * SAT_SPAN }, (_, i) => {
      const dx = i % SAT_SPAN, dy = (i - dx) / SAT_SPAN;
      const url = (SAT_TILES ?? D.imagery.tiles).replace('{z}', SAT_Z)
        .replace('{y}', y0 + dy).replace('{x}', x0 + dx);
      return new Promise((res, rej) => {
        const im = new Image();
        im.crossOrigin = 'anonymous';
        im.onload = () => { cx2.drawImage(im, dx * S, dy * S, S, S); res(); };
        im.onerror = () => rej(new Error('tile ' + (x0 + dx) + '/' + (y0 + dy)));
        im.src = url;
      });
    }));
  } catch (e) {
    satState = 'failed';
    document.getElementById('hint').textContent =
      'Orthoimagery did not answer from this network - the schematic ground '
      + 'stands. ' + D.recHonesty.availability;
    return;
  }
  // georeference the block onto the same km scale the anchors use
  const kmE = (d) => (d - pt.lng) * 111.32 * Math.cos(la);
  const kmN = (d) => (d - pt.lat) * 110.574;
  const west = x0 / n * 360 - 180, east = (x0 + SAT_SPAN) / n * 360 - 180;
  const north = tileLat(y0, n), south = tileLat(y0 + SAT_SPAN, n);
  const eW = kmE(west) * CITY_S, eE = kmE(east) * CITY_S;
  const nN = kmN(north) * CITY_S, nS = kmN(south) * CITY_S;
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  satPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(Math.abs(eE - eW), Math.abs(nN - nS)),
    new THREE.MeshStandardMaterial({ map: tex, roughness: .95 }));
  satPlane.rotation.x = -Math.PI / 2;
  satPlane.position.set((eW + eE) / 2, .05, -(nN + nS) / 2);
  satPlane.receiveShadow = true;
  satPlane.name = 'orthoimagery-ground';
  scene.add(satPlane);
  satState = 'live';
  document.getElementById('hint').textContent =
    D.imagery.attribution + ' - ' + D.imagery.licence
    + ', georeferenced to the campus record. ' + D.recHonesty.fidelity;
}
document.getElementById('satBtn').addEventListener('click', satGround);

function buildCity(g, R) {
  const pois = D.geo.cityPois?.[campusKey] ?? [];
  if (!pois.length) return;
  cityLog = pois.some((p) => p.km > 15);
  const grass = new THREE.MeshStandardMaterial({ color: 0x3d5238, roughness: .95 });
  /* The city blocks used to run a seven-step RAINBOW - hue 42, 152, 205,
     268, 20, 96, 330 - keyed on nothing but the index a place happened to
     sit at. It made every city layer look like the same bag of sweets, and
     the colour said nothing true about the place (these are real,
     RECORDED or SCHEMATIC locations; their colour is presentation only).
     They now vary in LIGHTNESS around the campus's own facade colour, so
     adjacent blocks still read apart and the city looks like that city. */
  const fabCity = fabricOf(campusKey);
  const baseHSL = new THREE.Color(fabCity.spec.facade_color).getHSL({ h: 0, s: 0, l: 0 });
  const ferryMat = new THREE.LineBasicMaterial({
    color: 0x41C4D4, transparent: true, opacity: .55 });
  pois.forEach((p, i) => {
    const [x, z] = cityPos(p);
    const len = Math.hypot(x, z), ux = x / len, uz = z / len;
    if (!cityLog) {
      // the avenue: ring road out to the place's block
      const r0 = R - 22, aLen = len - r0 - 9;
      const av = box(aLen, .06, 3.6, fabricOf(campusKey).road, 0, .03, 0, g, false);
      av.position.set((r0 + aLen / 2) * ux, .03, (r0 + aLen / 2) * uz);
      av.rotation.y = -Math.atan2(uz, ux);
      for (let d = r0 + 4; d < len - 10; d += 7)
        box(1.7, .02, .16, mat.paint, d * ux, .08, d * uz, g, false)
          .rotation.y = -Math.atan2(uz, ux);
    } else {
      // across open water: a schematic ferry line, not a road
      const geoL = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3((R + 42) * ux, .5, (R + 42) * uz),
        new THREE.Vector3((len - 14) * ux, .5, (len - 14) * uz)]);
      g.add(new THREE.Line(geoL, ferryMat));
      // and its own ground: a shoreline pad in the bay
      box(24, .14, 24, mat.land, x, .07, z, g, false);
    }
    // the place: green, main block, tower, and its name with real km
    box(15, .12, 15, grass, x, .13, z, g, false);
    const hgt = 7 + (i % 3) * 2.5;
    const step = [0, .09, -.07, .05, -.04, .12, -.10][i % 7];
    const bmat = new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(baseHSL.h,
        Math.min(.6, baseHSL.s + .06),
        Math.max(.14, Math.min(.62, baseHSL.l + step))),
      roughness: .78 });
    const bld = box(8, hgt, 6.5, bmat, x - 2, .15 + hgt / 2, z + 1.5, g);
    const twr = box(2.6, hgt + 5, 2.6, bmat, x + 4, .15 + (hgt + 5) / 2, z - 3.5, g);
    box(3, .5, 3, mat.slab, x + 4, hgt + 5.4, z - 3.5, g, false);
    bld.userData.poi = twr.userData.poi = p.name;
    cityHits.push(bld, twr);
    const pl = label(p.name, p.km + ' km \\u00b7 ' + p.prov, 1.7,
      { kind: p.prov === 'RECORDED' ? 'anchor' : 'schematic' });
    pl.position.set(x, hgt + 10, z); g.add(pl);
    cityPois++;
  });
  cityWater(g, campusKey, R, pois);
}

/* Schematic water and crossings per city - drawn, labelled SCHEMATIC. */
function cityWater(g, key, R, pois) {
  const tag = (name, x, z) => {
    const l = label(name, 'SCHEMATIC', 1.6, { kind: 'schematic' });
    l.position.set(x, 7, z); g.add(l);
  };
  if (key === 'new-orleans') {
    // the crescent south of the uptown institutions, the lake north
    const river = new THREE.Mesh(new THREE.TubeGeometry(
      new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(-150, 0, 92), new THREE.Vector3(-15, 0, 70),
        new THREE.Vector3(110, 0, 24)), 48, 10, 8), mat.water);
    river.scale.y = .012; river.position.y = .09; g.add(river);
    tag('Mississippi River', -30, 76);
    const lake = new THREE.Mesh(new THREE.PlaneGeometry(340, 70), mat.water);
    lake.rotation.x = -Math.PI / 2; lake.position.set(10, .08, -168);
    g.add(lake);
    tag('Lake Pontchartrain', 10, -150);
    return;
  }
  if (key === 'treasure-island') {
    // the campus is an island: the Bay all around, spans east and west
    const bay = new THREE.Mesh(
      new THREE.RingGeometry(R + 52, 430, 72), mat.water);
    bay.rotation.x = -Math.PI / 2; bay.position.y = .06; g.add(bay);
    tag('San Francisco Bay', 0, -(R + 110));
    const sf = pois.find((p) => p.name === 'San Francisco');
    const spans = [];
    if (sf) {
      const [sx, sz] = cityPos(sf), sl = Math.hypot(sx, sz);
      spans.push([sx / sl, sz / sl]);              // the west span, to SF
    }
    const rte = D.geo.routes.find((r) =>
      r.from === 'treasure-island' && r.to === 'oakland');
    if (rte) {
      const b = rte.bearing_deg * Math.PI / 180;
      spans.push([Math.sin(b), -Math.cos(b)]);     // the east span
    }
    for (const [ux, uz] of spans) {
      const r0 = R + 42, r1 = 205, mid = (r0 + r1) / 2, len = r1 - r0;
      const deck = box(len, .5, 5, mat.road, mid * ux, 2.6, mid * uz, g, false);
      deck.rotation.y = -Math.atan2(uz, ux);
      for (let d = r0 + 10; d < r1; d += 26)
        box(1, 2.6, 1, mat.metal, d * ux, 1.3, d * uz, g, false);
    }
    tag('Bay Bridge', spans.length ? 160 * spans[0][0] : 0, 8);
    return;
  }
  if (key === 'oakland') {
    // the waterfront: the Bay west of the campus grounds
    const bay = new THREE.Mesh(new THREE.PlaneGeometry(240, 560), mat.water);
    bay.rotation.x = -Math.PI / 2;
    bay.position.set(-(R + 60) - 120, .06, 0); g.add(bay);
    tag('San Francisco Bay', -(R + 90), 0);
    return;
  }
  if (key === 'houston') {
    // the real bayou this hub is named for - a winding schematic ribbon,
    // never claimed as more than that
    const bayou = new THREE.Mesh(new THREE.TubeGeometry(
      new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(-160, 0, 60), new THREE.Vector3(-10, 0, 90),
        new THREE.Vector3(140, 0, 40)), 48, 8, 8), mat.water);
    bayou.scale.y = .012; bayou.position.y = .09; g.add(bayou);
    tag('Buffalo Bayou', -30, 92);
    return;
  }
  if (key === 'chicago') {
    // the real river the Loop sits on - the same schematic ribbon idiom
    const river = new THREE.Mesh(new THREE.TubeGeometry(
      new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(-150, 0, 70), new THREE.Vector3(0, 0, 96),
        new THREE.Vector3(150, 0, 60)), 48, 8, 8), mat.water);
    river.scale.y = .012; river.position.y = .09; g.add(river);
    tag('Chicago River', 0, 98);
    const lake = new THREE.Mesh(new THREE.PlaneGeometry(260, 90), mat.water);
    lake.rotation.x = -Math.PI / 2; lake.position.set(0, .07, -(R + 145));
    g.add(lake);
    tag('Lake Michigan', 0, -(R + 140));
    return;
  }
  if (key === 'seattle') {
    // the real Sound this hub is named for - the same schematic water
    // band idiom, never claimed as more than that
    const sound = new THREE.Mesh(new THREE.PlaneGeometry(260, 120), mat.water);
    sound.rotation.x = -Math.PI / 2; sound.position.set(0, .07, -(R + 140));
    g.add(sound);
    tag('Puget Sound', 0, -(R + 135));
    return;
  }
  if (key === 'pittsburgh') {
    // the real confluence this hub is named for - three schematic river
    // ribbons meeting at the Point, never claimed as more than that
    const allegheny = new THREE.Mesh(new THREE.TubeGeometry(
      new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(150, 0, -30), new THREE.Vector3(40, 0, 20),
        new THREE.Vector3(-10, 0, 70)), 40, 8, 8), mat.water);
    allegheny.scale.y = .012; allegheny.position.y = .09; g.add(allegheny);
    tag('Allegheny River', 70, -14);
    const monongahela = new THREE.Mesh(new THREE.TubeGeometry(
      new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(-150, 0, 100), new THREE.Vector3(-60, 0, 85),
        new THREE.Vector3(-10, 0, 70)), 40, 8, 8), mat.water);
    monongahela.scale.y = .012; monongahela.position.y = .09; g.add(monongahela);
    tag('Monongahela River', -90, 92);
    const ohio = new THREE.Mesh(new THREE.TubeGeometry(
      new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(-10, 0, 70), new THREE.Vector3(-70, 0, 40),
        new THREE.Vector3(-150, 0, 10)), 40, 9, 8), mat.water);
    ohio.scale.y = .012; ohio.position.y = .09; g.add(ohio);
    tag('Ohio River', -100, 28);
    return;
  }
  if (key === 'denver') {
    // the real river this hub sits beside - the same schematic ribbon
    // idiom, never claimed as more than that
    const platte = new THREE.Mesh(new THREE.TubeGeometry(
      new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(-140, 0, -60), new THREE.Vector3(-20, 0, 10),
        new THREE.Vector3(80, 0, 100)), 48, 8, 8), mat.water);
    platte.scale.y = .012; platte.position.y = .09; g.add(platte);
    tag('South Platte River', -20, 14);
  }
  if (key === 'miami') {
    // Biscayne Bay, the water PortMiami sits on - a schematic water
    // plane east of the campus grounds, the same idiom Oakland's Bay
    // already uses
    const bay = new THREE.Mesh(new THREE.PlaneGeometry(260, 560), mat.water);
    bay.rotation.x = -Math.PI / 2;
    bay.position.set((R + 60) + 120, .06, 0); g.add(bay);
    tag('Biscayne Bay', R + 90, 0);
  }
  if (key === 'detroit') {
    // the real river the Detroit/Wayne County Port Authority sits on -
    // the same schematic water-band idiom Puget Sound and Biscayne Bay
    // already use, never claimed as more than that
    const river = new THREE.Mesh(new THREE.PlaneGeometry(260, 140), mat.water);
    river.rotation.x = -Math.PI / 2; river.position.set(0, .07, -(R + 140));
    g.add(river);
    tag('Detroit River', 0, -(R + 135));
  }
}

function buildCampus(key) {
  // the previous campus's fabric goes with it: these are per-campus
  // materials, not page-wide, so they are not marked shared and the
  // teardown below frees them along with everything they clothed
  fabMats = null; fabKey = null;
  // the old campus is FREED, not just detached: every rebuild used to leak
  // its merged building meshes, roads, ring geometry and every label
  // texture (+284 geometries per campus<->hall trip, +568 per resto walk)
  if (campusGroup) { scene.remove(campusGroup); disposeOf(campusGroup); }
  campusGroup = new THREE.Group(); buildings = []; beaconAt = []; solids = [];
  campusGroup.userData.key = key; campusGroup.userData.loc = loc;
  roadFaults = 0; roadCount = 0; cityPois = 0; cityHits = []; restorationHits = [];
  const camp = D.campuses[key];
  const dk = camp.districts;
  const R = dk.length === 2 ? 124 : 168;   // the campus scale: districts this far out
  campusR = R;
  const rr = R - 24;
  // the ring road, dashed, and the plaza walkway
  const ring = new THREE.Mesh(new THREE.RingGeometry(rr - 2.4, rr + 2.4, 96),
    fabricOf(campusKey).road);
  ring.rotation.x = -Math.PI / 2; ring.position.y = .05;
  ring.receiveShadow = true; campusGroup.add(ring); roadCount++;
  for (let a = 0; a < 64; a++) {         // the ring road's dashes, into the one dash mesh
    const th = a / 64 * Math.PI * 2;
    dashGeo(.16, 1.6, Math.cos(th) * rr, Math.sin(th) * rr, -th);
  }
  // the green: rough grass between the plaza walkway and the ring road,
  // which is what a campus actually has there and what makes the ring
  // read as a road rather than a line on a slab
  const green = new THREE.Mesh(new THREE.RingGeometry(27, rr - 3, 72),
    mat.grass);
  green.rotation.x = -Math.PI / 2; green.position.y = .035;
  green.receiveShadow = true; campusGroup.add(green);
  const wlk = new THREE.Mesh(new THREE.RingGeometry(24, 27, 64), mat.walkway);
  wlk.rotation.x = -Math.PI / 2; wlk.position.y = .04;
  wlk.receiveShadow = true; campusGroup.add(wlk);

  dk.forEach((k, di) => {
    const d = D.districts[k];
    const ang = di / dk.length * Math.PI * 2 - Math.PI / 2;
    const rad = new THREE.Vector2(Math.cos(ang), Math.sin(ang));
    const psi = Math.atan2(rad.x, rad.y);
    const cg = new THREE.Group();
    cg.position.set(rad.x * R, 0, rad.y * R);
    cg.rotation.y = psi;               // local +z = outward, doors face the plaza
    campusGroup.add(cg);
    const cols = Math.ceil(Math.sqrt(d.halls.length * 1.7));
    // The district decides the roofline it has an opinion about (an
    // industry district is sawtooth wherever it is); where it has none,
    // the CITY decides, so Seattle's unopinionated districts are gabled
    // and Houston's are flat. Two independent facts, both still visible.
    const style = STYLE_OF[k] ?? (D.world.fabric?.[campusKey]?.roof ?? 'flat');
    // row pitch sized to the district's deepest building, so a street
    // always fits between rows with clearance on both sides
    const maxDep = Math.max(...d.halls.map((sg) =>
      Math.max(D.halls.find(x => x.slug === sg).depth, 5)));
    const pitch = maxDep + 8;
    const rows = {}, rects = [], roads = [], pool = new Map();
    d.halls.forEach((sg, i) => {
      const h = D.halls.find(x => x.slug === sg);
      const gx = (i % cols) - (cols - 1) / 2, gz = Math.floor(i / cols);
      const bg = new THREE.Group();
      bg.position.set(gx * 16, 0, gz * pitch);
      cg.add(bg);
      const b = building(h, style, bg, pool, gx * 16, gz * pitch);
      const spot = beaconAt[beaconAt.length - 1];
      if (spot) { bg.updateWorldMatrix(true, false); bg.localToWorld(spot); }
      buildings.push(b.mesh);
      (rows[gz] ??= []).push({ u: gx * 16, v: gz * pitch, halfD: b.d / 2 });
      rects.push({ u: gx * 16, v: gz * pitch, hw: b.w / 2 + .2, hd: b.d / 2 + .2 });
    });
    // roads, cluster-local: a street along each row's frontage, a driveway
    // to every door, the alley to the ring, and the spur to the plaza
    for (const members of Object.values(rows)) {
      const rv = members[0].v;
      const u0 = Math.min(...members.map(m => m.u)) - 8;
      const u1 = Math.max(...members.map(m => m.u)) + 8;
      const maxHalfD = Math.max(...members.map(m => m.halfD));
      const sv = rv - maxHalfD - 2.6;
      roads.push(roadRect((u0 + u1) / 2, sv, u1 - u0, 3.6, fabricOf(campusKey).road, cg));
      dashesU(u0, u1, sv, cg);
      for (const m of members) {
        const top = rv - m.halfD - .45, bot = sv + 1.8;
        if (top - bot > .1)
          roads.push(roadRect(m.u, (top + bot) / 2, 2.4, top - bot, mat.drive, cg, .045));
      }
      roadCount += 1 + members.length;
    }
    const lastV = Math.max(...Object.values(rows).map(m => m[0].v));
    // the alley runs up a real gap between columns: even grids have a
    // building at u=8 and their free lane at u=0, odd grids the reverse
    const alleyU = (cols % 2 === 0) ? 0 : 8;
    roads.push(roadRect(alleyU, ((rr - R) + (lastV - 2.6)) / 2, 3.2,
      (lastV - 2.6) - (rr - R), fabricOf(campusKey).road, cg));
    dashesV(rr - R, lastV - 2.6, alleyU, cg);
    roads.push(roadRect(0, ((27 - R) + (rr - R)) / 2, 4.2,
      (rr - R) - (27 - R), fabricOf(campusKey).road, cg));
    dashesV(27 - R, rr - R, 0, cg);
    roadCount += 2;
    // the walker is kept out of the same rectangles the roads are: one
    // reach that covers the district, so a stroll tests eight numbers
    // before it tests a hundred
    solids.push({ cx: rad.x * R, cz: rad.y * R,
                  cos: Math.cos(psi), sin: Math.sin(psi),
                  reach: Math.max(...rects.map((b) =>
                    Math.hypot(Math.abs(b.u) + b.hw, Math.abs(b.v) + b.hd))) + 2,
                  rects });
    // the guarantee: no road rectangle overlaps a building rectangle
    for (const r of roads) for (const b of rects) {
      if (Math.abs(r.u - b.u) < r.w / 2 + b.hw
        && Math.abs(r.v - b.v) < r.h / 2 + b.hd) {
        roadFaults++;
        (window.__faults ??= []).push({ r, b });
      }
    }
    flushParts(pool, cg);
    const dl = label(D.i18n[loc].districts[k], null, 3,
      { kind: 'district', hue: d.hue });
    dl.position.set(rad.x * (R - 14), 15, rad.y * (R - 14));
    campusGroup.add(dl);
  });
  flushRoads(campusGroup);
  flushBeacons(beaconAt.filter(Boolean), campusGroup);
  const plaza = new THREE.Mesh(new THREE.CylinderGeometry(24, 24, .3, 48),
    new THREE.MeshStandardMaterial({ map: concreteTex, color: 0xb8bdbd, roughness: .95 }));
  plaza.position.y = .15; plaza.receiveShadow = true; campusGroup.add(plaza);
  const sign = label(camp.name, camp.city + ', ' + camp.region, 3.2,
    { kind: 'campus' });
  sign.position.set(0, 18, 0); campusGroup.add(sign);
  dressCampus(key, campusGroup, R + 42);
  buildChapterHall(campusGroup, key);
  buildTrainingYard(campusGroup, R);
  buildCity(campusGroup, R);
  buildRestorationSites(campusGroup);
  flushDashes(campusGroup);
  walkLim = cityPois ? (cityLog ? 536 : 350) : campusR + 85;
  campusGroup.userData.walkLim = walkLim;
  // fog banks: the island's weather, drifting flat haze sheets
  fogBanks = [];
  const nb = ATMOS[key]?.banks ?? 0;
  for (let i = 0; i < nb; i++) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(150 + i * 22, 34),
      new THREE.MeshBasicMaterial({ color: 0xcfd8dc, transparent: true,
        opacity: .09 + (i % 3) * .025, depthWrite: false }));
    m.rotation.x = -Math.PI / 2;
    const ang = i / nb * Math.PI * 2, rad = 70 + (i % 3) * 45;
    m.position.set(Math.cos(ang) * rad, 7 + (i % 4) * 5, Math.sin(ang) * rad);
    campusGroup.add(m);
    fogBanks.push({ m, ang, rad, sp: .015 + (i % 3) * .008 });
  }
  setGroundSurface(key);
  clearAdvisors();
  spawnCampusAdvisors();
  spawnFauna(key, R);
  scene.add(campusGroup);
  buildMinimap(key, R);
}

/* ------------------------------------------------------------ minimap --- */
// The walkable campus, from above: roads, buildings in district hues,
// the city places, and you. Drawn once per campus; the player arrow
// rides the render loop.
let mmBase = null, mmInfo = { n: 0, s: 1 };
function buildMinimap(key, R) {
  const ext = Math.max(walkLim, R + 60);
  const S2 = 66 / ext;
  mmInfo = { n: 0, s: S2, done: 0 };
  const c = document.createElement('canvas'); c.width = c.height = 150;
  const g2 = c.getContext('2d');
  g2.fillStyle = 'rgba(12,17,19,.88)'; g2.fillRect(0, 0, 150, 150);
  const X = (x) => 75 + x * S2, Y = (z) => 75 + z * S2;
  // water backdrop where the city layers put it
  if (key === 'treasure-island') {
    g2.fillStyle = 'rgba(20,40,58,.8)'; g2.fillRect(0, 0, 150, 150);
    g2.fillStyle = 'rgba(12,17,19,.95)';
    g2.beginPath(); g2.arc(75, 75, (R + 52) * S2, 0, 7); g2.fill();
  } else if (key === 'oakland') {
    g2.fillStyle = 'rgba(20,40,58,.8)';
    g2.fillRect(0, 0, X(-(R + 60)), 150);
  }
  // the ring road
  g2.strokeStyle = '#565c60'; g2.lineWidth = 3;
  g2.beginPath(); g2.arc(75, 75, (R - 24) * S2, 0, 7); g2.stroke();
  // buildings, axis-aligned, in their district hue
  const bb = new THREE.Box3();
  for (const b of buildings) {
    bb.setFromObject(b);
    const h = D.halls.find((x) => x.slug === b.userData.slug);
    const hue = D.districts[h.district].hue;
    g2.fillStyle = `hsl(${hue},45%,52%)`;
    g2.fillRect(X(bb.min.x), Y(bb.min.z),
      Math.max(2, (bb.max.x - bb.min.x) * S2),
      Math.max(2, (bb.max.z - bb.min.z) * S2));
    mmInfo.n++;
    // a fully-worked hall (stations done, every bound seat passed) rings amber
    const bound = D.sims.bindings[h.slug] ?? [];
    if ((h.stations.length || bound.length)
      && h.stations.every((id) => doneStations.has(id))
      && bound.every((x) => prog.sims[x.sim]?.passed)) {
      g2.strokeStyle = '#E8A33D'; g2.lineWidth = 1.5;
      g2.beginPath();
      g2.arc(X((bb.min.x + bb.max.x) / 2), Y((bb.min.z + bb.max.z) / 2),
        Math.max(4, (bb.max.x - bb.min.x) * S2), 0, 7);
      g2.stroke();
      mmInfo.done++;
    }
  }
  // the chapter hall and the city places
  g2.fillStyle = '#E8A33D';
  g2.beginPath(); g2.arc(75, 75, 3, 0, 7); g2.fill();
  g2.fillStyle = '#41C4D4';
  for (const p of (D.geo.cityPois?.[key] ?? [])) {
    const [px, pz] = cityPos(p);
    g2.beginPath(); g2.arc(X(px), Y(pz), 2.5, 0, 7); g2.fill();
  }
  mmBase = c; mmDirty = true;
}
// the arrow only moves while walking: an orbiting campus draws the base
// once (mmDirty, set by buildMinimap) and then leaves the canvas alone -
// and once more when a walk ends, so no arrow is left standing
let mmDirty = true, mmCtx = null, mmArrow = false;
const _mmDir = new THREE.Vector3();
function mmDraw() {
  const cv = document.getElementById('mm');
  if (!mmBase || cv.style.display === 'none') return;
  if (!walkActive && !mmDirty && !mmArrow) return;
  mmDirty = false; mmArrow = walkActive;
  const g2 = mmCtx ??= cv.getContext('2d');
  g2.clearRect(0, 0, 150, 150);
  g2.drawImage(mmBase, 0, 0);
  if (walkActive) {
    const touchWalk = isTouch && !xrWalk;
    const px = touchWalk ? walkAvatar.position.x : eyePos().x;
    const pz = touchWalk ? walkAvatar.position.z : eyePos().z;
    let yaw;
    if (touchWalk) yaw = tYaw + Math.PI;
    else { camera.getWorldDirection(_mmDir);
      yaw = Math.atan2(_mmDir.x, _mmDir.z); }
    const x = 75 + px * mmInfo.s, y = 75 + pz * mmInfo.s;
    g2.save(); g2.translate(x, y); g2.rotate(yaw + Math.PI);
    g2.fillStyle = '#E8A33D';
    g2.beginPath(); g2.moveTo(0, -6); g2.lineTo(4, 5); g2.lineTo(-4, 5);
    g2.closePath(); g2.fill(); g2.restore();
  }
}

/* ---------------------------------------------------------- region view --- */
// Plate positions from the geo registry: TRUE bearings between the real
// coordinates; distances log-compressed so 9 km of bay and 3,000 km of
// gulf share one board. The route labels carry the real kilometres.
const PLATE_POS = (() => {
  const range = (km) => 34 + 50 * Math.log10(1 + km);
  const pos = { 'treasure-island': [0, 0] };
  for (const r of D.geo.routes) {
    if (r.from !== 'treasure-island') continue;
    const b = r.bearing_deg * Math.PI / 180, d = range(r.km);
    pos[r.to] = [Math.sin(b) * d, -Math.cos(b) * d];
  }
  const ks = Object.keys(pos);
  const cx = ks.reduce((a, k) => a + pos[k][0], 0) / ks.length;
  const cz = ks.reduce((a, k) => a + pos[k][1], 0) / ks.length;
  for (const k of ks) { pos[k][0] -= cx; pos[k][1] -= cz; }
  return pos;
})();

// Whatever roadmap candidates remain, placed by the same true bearing/log-range
// scheme as the built plates above, from the same flagship reference
// point (treasure-island) - honest position, not a decorative ring. The
// centroid shift is recomputed from the built plates' own RAW positions
// (before their centering) so both sets share exactly one frame - PLATE_POS
// only exposes its already-centered result, not that intermediate value.
const CAND_POS = (() => {
  const range = (km) => 34 + 50 * Math.log10(1 + km);
  const raw = { 'treasure-island': [0, 0] };
  for (const r of D.geo.routes) {
    if (r.from !== 'treasure-island') continue;
    const b = r.bearing_deg * Math.PI / 180, d = range(r.km);
    raw[r.to] = [Math.sin(b) * d, -Math.cos(b) * d];
  }
  const rk = Object.keys(raw);
  const cx = rk.reduce((a, k) => a + raw[k][0], 0) / rk.length;
  const cz = rk.reduce((a, k) => a + raw[k][1], 0) / rk.length;
  const pos = {};
  for (const [k, c] of Object.entries(D.roadmap.candidates)) {
    const b = c.bearing_from_flagship_deg * Math.PI / 180,
      d = range(c.km_from_flagship);
    pos[k] = [Math.sin(b) * d - cx, -Math.cos(b) * d - cz];
  }
  return pos;
})();

function buildRegion() {
  if (regionGroup) { scene.remove(regionGroup); disposeOf(regionGroup); }
  regionGroup = new THREE.Group(); plates = []; anchorPins = 0;
  // the gulf-to-bay board: water underneath everything
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1600), mat.water);
  sea.rotation.x = -Math.PI / 2; sea.position.y = -.12; sea.receiveShadow = true;
  regionGroup.add(sea);
  const centers = {};
  for (const [key, camp] of Object.entries(D.campuses)) {
    const [px, pz] = PLATE_POS[key];
    centers[key] = new THREE.Vector3(px, 0, pz);
    /* The board is the first thing anybody sees, and every plate on it was
       the same pale disc of mat.land - ten places drawn identically, with
       seven of them (the hubs, which host no districts) completely bare.
       A plate now wears its OWN campus's ground recipe on top and its own
       fabric trim on the rim, both already declared in the world registry
       and used by the campus view, so the board reads as ten different
       places from the first frame rather than after you fly into one. */
    const atm = D.world.atmos[key];
    const fabR = D.world.fabric?.[key];
    const plate = new THREE.Mesh(new THREE.CylinderGeometry(36, 40, 2.2, 48), [
      new THREE.MeshStandardMaterial({                       // the rim
        color: new THREE.Color(fabR?.trim ?? '#9db2b8'), roughness: .85 }),
      groundMat(atm?.ground ?? 'concrete', undefined, 10),   // the top
      groundMat(atm?.verge ?? 'grass', undefined, 10),       // the underside
    ]);
    plate.position.set(px, 1.1, pz); plate.receiveShadow = plate.castShadow = true;
    plate.userData.campus = key;
    regionGroup.add(plate); plates.push(plate);
    /* A hub hosts no districts, so its plate had nothing standing on it at
       all. It does have one building - the chapter hall every campus has -
       and the count of trades seated there is already in the plate label.
       Drawing that one building, in the hub's own fabric, is what a hub
       actually is: a seat for the whole network and no home district. */
    if (!camp.districts.length) {
      const f2 = fabR ?? FABRIC_FALLBACK;
      const drum = new THREE.Mesh(new THREE.CylinderGeometry(6, 6.6, 7, 8),
        new THREE.MeshStandardMaterial({
          color: new THREE.Color(f2.facade_color), roughness: .8 }));
      drum.position.set(px, 5.7, pz);
      drum.castShadow = drum.receiveShadow = true;
      drum.userData.campus = key;
      regionGroup.add(drum); plates.push(drum);
      const cone = new THREE.Mesh(new THREE.ConeGeometry(7.6, 3.4, 8),
        new THREE.MeshStandardMaterial({
          color: new THREE.Color(f2.roof_color), roughness: .7, metalness: .2 }));
      cone.position.set(px, 10.9, pz); cone.castShadow = true;
      cone.userData.campus = key;
      regionGroup.add(cone); plates.push(cone);
    }
    // one block per hosted district, sized by its hall count
    camp.districts.forEach((dkey, i) => {
      const d = D.districts[dkey];
      const ang = i / camp.districts.length * Math.PI * 2;
      const bx = px + Math.cos(ang) * 19, bz = pz + Math.sin(ang) * 19;
      const hgt = 4 + d.halls.length * .55;
      const blk = box(11, hgt, 11, new THREE.MeshStandardMaterial({
        color: new THREE.Color().setHSL(d.hue / 360, .45, .4), roughness: .7 }),
        bx, 2.2 + hgt / 2, bz, regionGroup);
      blk.userData.campus = key; plates.push(blk);
      const cl = label(String(d.halls.length), null, 1.4,
        { kind: 'station', hue: d.hue });
      cl.position.set(bx, hgt + 6, bz); regionGroup.add(cl);
    });
    const pl = label(camp.name,
      camp.city + ', ' + camp.region + ' · +' + D.chapters.hosted[key], 3.4,
      { kind: 'campus' });
    pl.position.set(px, 30, pz); regionGroup.add(pl);
    // RECORDED anchors from the geo registry: real cities and institutions
    // around each campus, marked at their true bearing on the plate rim.
    // The rim radius is log-eased so a 4 km and a 40 km anchor both read;
    // the label carries the real kilometres, like the route labels do.
    for (const a of (D.geo.anchors[key] ?? [])) {
      const b = a.bearing_deg * Math.PI / 180;
      const rr = 28 + 8 * Math.log10(1 + a.km);
      const ax = px + Math.sin(b) * rr, az = pz - Math.cos(b) * rr;
      const pin = new THREE.Mesh(new THREE.CylinderGeometry(.55, .9, 4.6, 10),
        new THREE.MeshStandardMaterial({ color: 0xE8A33D, roughness: .5,
          emissive: 0x7a4d08 }));
      pin.position.set(ax, 3.4, az); regionGroup.add(pin);
      anchorPins++;
      const al = label(a.name, a.km + ' km', 1.15, { kind: 'anchor' });
      al.position.set(ax, 9.6, az); regionGroup.add(al);
    }
  }
  // whatever roadmap candidates remain: a dashed schematic ring, not a plate -
  // the shape itself is the claim (labels/registry: 'the dashed outline
  // is the claim'), placed at the real bearing/distance CAND_POS computed,
  // never a hall, union or curriculum content standing there to walk into
  for (const [ck, c] of Object.entries(D.roadmap.candidates)) {
    const [px, pz] = CAND_POS[ck];
    const ring = new THREE.Mesh(new THREE.RingGeometry(30, 32, 48, 1, 0, Math.PI * 1.7),
      new THREE.MeshBasicMaterial({ color: 0x93A3A6, transparent: true,
        opacity: .55, side: THREE.DoubleSide }));
    ring.rotation.x = -Math.PI / 2; ring.position.set(px, .3, pz);
    ring.userData.candidate = ck; regionGroup.add(ring); plates.push(ring);
    const cl = label(c.name, c.city + ', ' + c.region, 2.6, { kind: 'schematic' });
    cl.position.set(px, 14, pz); regionGroup.add(cl);
  }
  // glowing routes between the campuses
  const lineMat = new THREE.LineBasicMaterial({ color: 0xE8A33D, transparent: true, opacity: .65 });
  const pairs = [];
  const pkeys = Object.keys(D.campuses);
  for (let i = 0; i < pkeys.length; i++)
    for (let j = i + 1; j < pkeys.length; j++) pairs.push([pkeys[i], pkeys[j]]);
  for (const [a, b] of pairs) {
    const pa = centers[a], pb = centers[b];
    const mid = pa.clone().add(pb).multiplyScalar(.5); mid.y = 26;
    const curve = new THREE.QuadraticBezierCurve3(
      pa.clone().setY(3), mid, pb.clone().setY(3));
    const geo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(40));
    regionGroup.add(new THREE.Line(geo, lineMat));
    const km = D.geo.routes.find((r) =>
      (r.from === a && r.to === b) || (r.from === b && r.to === a))?.km;
    if (km !== undefined) {
      const kl = label(`${km.toLocaleString('en-US')} km`, null, 2.2,
      { kind: 'route' });
      kl.position.copy(mid).setY(mid.y + 5);
      regionGroup.add(kl);
    }
  }
  const sign = label('SmartCiti.X : Trade Craft Academy', 'powered by AGI Corp',
    3.6, { kind: 'brand' });
  sign.position.set(0, 44, 10); regionGroup.add(sign);
  scene.add(regionGroup);
}

function showRegion() {
  if (sim) teardownSim();
  if (curRestoSite) teardownRestoWalk();
  view = 'region';
  walkLeave();
  if (avatarGroup) avatarGroup.visible = false;
  wheelShow(false);
  if (hallGroup) hallGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  ground.visible = grid.visible = false;
  applyAtmos(null);
  // the board is static (real coordinates, real names, no locale in it):
  // built once, shown again - it used to be rebuilt on every return, 111
  // label textures and every plate and pin each time, none of it freed
  if (!regionGroup) buildRegion();
  regionGroup.visible = true;
  scene.fog.near = 380; scene.fog.far = 1300;
  document.getElementById('mm').style.display = 'none';
  controls.maxDistance = 700; controls.minDistance = 60;
  camera.position.set(0, 225, 235); controls.target.set(10, 0, 0);
  document.getElementById('hname').textContent = t('view.region');
  document.getElementById('hfocus').textContent =
    t('figures.campuses').replace('{n}', Object.keys(D.campuses).length) + ' · ' +
    t('figures.halls').replace('{n}', D.halls.length) + ' · ' +
    t('figures.districts').replace('{n}', Object.keys(D.districts).length);
  document.getElementById('hint').textContent =
    t('hint.campus') + ' \u00b7 ' + t('geo.note');
  document.getElementById('walkBtn').style.display = 'none';
  document.getElementById('avaBtn').style.display = '';
  document.getElementById('campusBtn').style.display = 'none';
  document.getElementById('simBtn').style.display = 'none';
  document.getElementById('glbBtn').style.display = 'none';
  document.getElementById('glbInBtn').style.display = 'none';
  document.getElementById('satBtn').style.display = 'none';
  satClear(); satState = 'off';
  syncURL();
}

// the campus rollup: the whole training loop summed over the campus's
// halls - stations, bound seats, and the districts' crib checks
function campusRollup(key) {
  const halls = D.campuses[key].halls.map((sg) => D.halls.find((x) => x.slug === sg));
  let sd = 0, stot = 0, sp = 0, sb = 0;
  for (const h of halls) {
    stot += h.stations.length;
    sd += h.stations.filter((id) => doneStations.has(id)).length;
    const b = D.sims.bindings[h.slug] ?? [];
    sb += b.length;
    sp += b.filter((x) => prog.sims[x.sim]?.passed).length;
  }
  const dists = D.campuses[key].districts;
  const cd = dists.filter((dk) => prog.tools[dk]?.passed).length;
  return `✓ ${sd}/${stot} · ▶ ${sp}/${sb} · \U0001f9f0 ${cd}/${dists.length}`;
}

function showCampus(key) {
  if (sim) teardownSim();
  if (curRestoSite) teardownRestoWalk();
  campusKey = key; view = 'campus';
  walkLeave();
  if (avatarGroup) avatarGroup.visible = false;
  wheelShow(false);
  if (hallGroup) hallGroup.visible = false;
  if (regionGroup) regionGroup.visible = false;
  ground.visible = grid.visible = true;
  applyAtmos(key);
  if (campusGroup && campusGroup.userData.key === key
      && campusGroup.userData.loc === loc) {
    // the same campus in the same language is shown again, not rebuilt:
    // leaving the restoration walk (and a hall) used to rebuild it whole.
    // What a hall or a walk can change is re-laid: the fauna the walk
    // replaced, the advisors the hall cleared, the minimap's done-rings
    campusGroup.visible = true;
    walkLim = campusGroup.userData.walkLim;
    setGroundSurface(key);
    clearAdvisors(); spawnCampusAdvisors();
    spawnFauna(key, campusR);
    buildMinimap(key, campusR);
  } else buildCampus(key);
  scene.fog.near = 320 * fogMul; scene.fog.far = 1280 * fogMul;
  document.getElementById('mm').style.display = '';
  controls.maxDistance = 760; controls.minDistance = 20;
  camera.position.set(0, 300, 350); controls.target.set(0, 0, 0);
  const camp = D.campuses[key];
  document.getElementById('hname').textContent =
    camp.name + '  ' + campusRollup(key);
  document.getElementById('hfocus').textContent =
    camp.city + ', ' + camp.region + ' — ' + camp.tagline
    + (D.geo.cityPois?.[key] ? ' · ' + t('city.note') : '');
  document.getElementById('hint').textContent = t('hint.campus');
  document.getElementById('walkBtn').style.display = '';
  document.getElementById('avaBtn').style.display = '';
  document.getElementById('campusBtn').style.display = 'none';
  document.getElementById('simBtn').style.display = 'none';
  document.getElementById('glbBtn').style.display = 'none';
  document.getElementById('glbInBtn').style.display = 'none';
  document.getElementById('satBtn').style.display = '';
  syncURL();
}

function showHall(sg) {
  if (sim) teardownSim();
  if (curRestoSite) teardownRestoWalk();
  slug = sg; view = 'hall'; campusKey = campusOfHall(sg);
  hallRec = D.halls.find(x => x.slug === sg);
  if (avatarGroup) avatarGroup.visible = false;
  if (!(isTouch && walkActive)) wheelShow(false);
  if (regionGroup) regionGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  ground.visible = grid.visible = true;
  applyAtmos(campusKey);
  buildHall(sg);
  scene.fog.near = 70 * fogMul; scene.fog.far = 170 * fogMul;
  document.getElementById('mm').style.display = 'none';
  controls.maxDistance = 120; controls.minDistance = 8;
  camera.position.set(30, 26, 42); controls.target.set(0, 2, 0);
  document.getElementById('hint').textContent =
    '\u25cf ' + t('hall.stations') + ' \u00b7 ' + t('hall.rooms') + ' \u2192 ' + t('map.layer.modules');
  document.getElementById('walkBtn').style.display = '';
  document.getElementById('avaBtn').style.display = '';
  const cb = document.getElementById('campusBtn');
  cb.style.display = ''; cb.textContent = '\u2191 ' + D.campuses[campusKey].name;
  document.getElementById('simBtn').style.display =
    (D.sims.bindings[sg] && !('ontouchstart' in window)) ? '' : 'none';
  document.getElementById('glbBtn').style.display = '';
  document.getElementById('glbInBtn').style.display = 'none';
  document.getElementById('satBtn').style.display = 'none';
  satClear(); satState = 'off';
  syncURL();
}

/* ----------------------------------------------------------- walk mode --- */
const plc = new PointerLockControls(camera, renderer.domElement);
let walkActive = false;
const keys = {};
document.addEventListener('keydown', (e) => {
  keys[e.code] = true;
  if (sim && e.code === 'Escape' && !document.body.classList.contains('open'))
    exitSim();
  if (curRestoSite && e.code === 'Escape' && !document.body.classList.contains('open'))
    exitRestoWalk();
  // while the scripted reference operator has the seat, the seat is its:
  // Space is its verb (the policy calls sim.action() itself), Esc still exits
  if (sim && e.code === 'Space') { e.preventDefault(); if (!opRun) sim.action?.(); }
  if (walkActive && view === 'campus' && nearSeat
      && (e.code === 'Enter' || e.code === 'KeyE')) {
    plc.unlock(); enterSeatFromYard(nearSeat);
  }
  if (walkActive && view === 'campus' && nearSlug && !nearSeat
      && (e.code === 'Enter' || e.code === 'KeyE')) enterHallWalking(nearSlug);
  if (walkActive && view === 'campus' && nearPoi
      && (e.code === 'Enter' || e.code === 'KeyE')) {
    plc.unlock(); openCityPoi(nearPoi);
  }
  if (walkActive && view === 'restoration' && nearTrack
      && (e.code === 'Enter' || e.code === 'KeyE')) {
    plc.unlock(); openRestoTrack(nearTrack);
  }
});
document.addEventListener('keyup', (e) => { keys[e.code] = false; });

let campusR = 168, nearSlug = null, nearPoi = null, nearTrack = null;
function enterWalk() {
  if (view === 'region' || view === 'avatar') return;
  if (isTouch) {
    if (walkActive) return exitWalkMode();
    return enterTouchWalk();
  }
  if (renderer.xr.isPresenting) return;      // in a headset you are already on foot
  controls.autoRotate = false; controls.enabled = false;
  // the walker is the RIG: it stands at eye height, the camera sits at its
  // origin and the pointer lock turns only the camera. On unlock the rig
  // collapses back into the camera, so orbit math never sees the rig.
  const [sx, sz] = walkSpawn();
  xrRig.position.set(sx, 1.7, sz); xrRig.rotation.set(0, 0, 0);
  camera.position.set(0, 0, 0); xrRig.updateMatrixWorld(true);
  camera.lookAt(0, 1.7, 0);
  // A refused pointer lock used to be an uncaught exception, and a silent
  // dead end: `controls.enabled` is already false and the camera is already
  // parked inside the rig by this line, and neither `lock` nor `unlock`
  // fires when the request is refused - so nothing ever put the orbit
  // controls back. The browser refuses for ordinary reasons (the user
  // denies it, the page is framed without pointer-lock permission, there
  // was no fresh user gesture), and `requestPointerLock` can throw
  // SYNCHRONOUSLY as well as fire `pointerlockerror`, so both paths land on
  // the same recovery. A refused session degrades to a HUD line, never an
  // error - the same rule WebXR entry already follows.
  try { plc.lock(); } catch (err) { walkRefused(err); }
}

/* The lock was refused. Put back exactly what enterWalk() took away, and
   say so, because a walk button that does nothing at all reads as a bug. */
function walkRefused(err) {
  walkActive = false; xrWalk = false;
  document.getElementById('cross').style.display = 'none';
  rigCollapse();
  controls.enabled = true;
  const fwd = new THREE.Vector3(); camera.getWorldDirection(fwd);
  controls.target.copy(camera.position).addScaledVector(fwd, 6);
  walkRefusedAt = Date.now();
  document.getElementById('hint').textContent = t('hint.walkRefused');
  console.warn('walk mode: the browser refused the pointer lock', err ?? '');
}
let walkRefusedAt = 0;
// where a walker stands when a view is entered on foot: outside a hall's
// door, or on the campus green
function walkSpawn() {
  if (view === 'hall') {
    const h = D.halls.find(x => x.slug === slug);
    return [0, -(h.depth * U) / 2 - 8];
  }
  return [0, 30];
}

/* Walking into a seat. A simulator is entered FROM ITS HALL everywhere else
   in this app, and that stays true: the seat is started against the hall on
   this campus that actually teaches it, so the run is recorded against a
   real binding rather than against the plaza. If a seat somehow has no hall
   here, it refuses and says so rather than starting an unbound run. */
function enterSeatFromYard(id) {
  const def = D.sims.sims[id];
  if (!def) return refusePanel('There is no seat by that name in the registry.');
  const here = new Set(D.campuses[campusKey]?.halls ?? []);
  const hall = def.halls.find((sg) => here.has(sg));
  if (!hall) {
    return refusePanel(`${def.name} is not taught at `
      + `${D.campuses[campusKey].name} \u2014 no hall homed here teaches it, `
      + 'and a run has to be recorded against a hall that does.');
  }
  slug = hall;
  startSim(id, null);
}

function enterHallWalking(sg) {
  showHall(sg);                     // ...which writes the hall's ORBIT frame into the camera
  const [sx, sz] = walkSpawn();
  xrRig.position.x = sx; xrRig.position.z = sz;
  // a walker's eye is the rig: the camera sits back at the rig's origin,
  // keeping only the way it was looking, exactly as enterWalk() seats it
  camera.position.set(0, 0, 0);
  document.getElementById('hint').textContent = t('hint.walk');
}
plc.addEventListener('lock', () => {
  walkActive = true;
  document.getElementById('cross').style.display = 'block';
  document.getElementById('hint').textContent = t('hint.walk');
});
// the end of a walk, on a desktop (pointer unlock) or in a headset (the
// session ends, or the B/Y button): the rig folds back into the camera and
// the orbit controls pick up looking the way the walker was looking
function walkEnded() {
  walkActive = false; xrWalk = false;
  document.getElementById('cross').style.display = 'none';
  rigCollapse();
  controls.enabled = true;
  const fwd = new THREE.Vector3(); camera.getWorldDirection(fwd);
  controls.target.copy(camera.position).addScaledVector(fwd, 6);
  if (view === 'hall') document.getElementById('hint').textContent =
    '● ' + t('hall.stations') + ' · ' + t('hall.rooms') + ' → ' + t('map.layer.modules');
  else if (view === 'campus') document.getElementById('hint').textContent = t('hint.campus');
  nearSlug = null;
}
plc.addEventListener('unlock', () => { if (!xrWalk && walkActive) walkEnded(); });
// the asynchronous half of the same refusal: some browsers fire this rather
// than throwing, and a few do both, so the recovery is idempotent
document.addEventListener('pointerlockerror', () => {
  if (!walkActive && !renderer.xr.isPresenting) walkRefused('pointerlockerror');
});
// leaving a desktop walk for a view that writes its own camera frame (a seat,
// the campus, a restoration site): the pointer-lock 'unlock' event lands a
// task LATER, and walkEnded() folding the rig into the camera then would
// bake the walker's offset into the frame the new view has just written -
// so the walk ends here, now, and the late event finds nothing left to end
function walkLeave() {
  if (!walkActive || xrWalk) return;
  if (isTouch) { exitWalkMode(); return; }
  plc.unlock(); walkEnded();
}

/* A hall is a solid thing. The campus stroll used to walk straight through
   the buildings, which is the single loudest way a walkable world tells you
   it is not one. The walker is pushed out of the same footprints the road
   layout is already checked against - no second copy of where a building
   is - along whichever axis it is least far into, which is what keeps a
   wall a wall rather than a trap: you slide along it instead of sticking.
   The plaza, the chapter hall and the yard dressing are NOT in this set;
   what a stroller actually walks into is the halls. */
function pushOutOfSolids(rig, list = solids) {
  for (const d of list) {
    const dx = rig.x - d.cx, dz = rig.z - d.cz;
    if (dx * dx + dz * dz > d.reach * d.reach) continue;      // nowhere near
    // world -> the district's own frame (it is turned to face the plaza)
    let u = dx * d.cos - dz * d.sin;
    let v = dx * d.sin + dz * d.cos;
    let hit = false;
    for (const b of d.rects) {
      // a round thing is round: a mast, a post, the chapter hall's drum.
      // Pushing one out along an axis would square it off.
      if (b.r !== undefined) {
        const du = u - b.u, dv = v - b.v, rr = b.r + BODY_R;
        const dd = Math.hypot(du, dv);
        if (dd >= rr) continue;
        hit = true;
        if (dd < 1e-4) u = b.u + rr;                 // dead centre: any way out
        else { u = b.u + du / dd * rr; v = b.v + dv / dd * rr; }
        continue;
      }
      const ou = (b.hw + BODY_R) - Math.abs(u - b.u);
      const ov = (b.hd + BODY_R) - Math.abs(v - b.v);
      if (ou <= 0 || ov <= 0) continue;                       // outside this one
      hit = true;
      // out along the shallower axis, so a wall is slid along, not stuck to
      if (ou < ov) u = b.u + (u >= b.u ? 1 : -1) * (b.hw + BODY_R);
      else v = b.v + (v >= b.v ? 1 : -1) * (b.hd + BODY_R);
    }
    if (hit) {                                                // and back again
      rig.x = d.cx + u * d.cos + v * d.sin;
      rig.z = d.cz - u * d.sin + v * d.cos;
    }
  }
}

/* Partitions with a way through them. The rooms tile the envelope wall to
   wall - there is no corridor in this plan - so a partition that runs solid
   all the way across seals the room it encloses.

   The first try cut a centred doorway into each of a room's four runs, and
   sealed most of the building: two rooms sharing a boundary each drew their
   own partition on it, and because the rooms are different widths the two
   doorways landed at different places, so the pair blocked everything.

   A doorway therefore belongs to the BOUNDARY BETWEEN TWO ROOMS, not to a
   room: one door per shared edge, centred on the overlap the two rooms
   actually share, plus one in each room's frontage onto the open front of
   the building, which is how a walker gets in at all. Every room then has a
   way through to each of its neighbours by construction, and the hall test
   proves it rather than trusting it. */
const DOOR_W = 1.8;                  // clear opening, before a body is in it
const _DEPS = .05;                   // two edges this close are the same edge
function planDoors(rects, frontZ) {
  // doors, keyed by the line they sit on: 'x@<pos>' or 'z@<pos>'
  const doors = new Map();
  const cut = (key, s, e) => {
    const L = e - s;
    if (L <= .05) return;
    const w = Math.min(DOOR_W, L * .9), m = (s + e) / 2;
    (doors.get(key) ?? doors.set(key, []).get(key)).push([m - w / 2, m + w / 2]);
  };
  const ov = (a0, a1, b0, b1) => [Math.max(a0, b0), Math.min(a1, b1)];
  for (let i = 0; i < rects.length; i++) {
    const a = rects[i];
    // the building's open front is a way in, so the frontage is a doorway too
    if (Math.abs(a.z0 - frontZ) < _DEPS) cut('z@' + a.z0.toFixed(2), a.x0, a.x1);
    for (let j = i + 1; j < rects.length; j++) {
      const b = rects[j];
      for (const [pa, pb] of [[a.x1, b.x0], [b.x1, a.x0]])
        if (Math.abs(pa - pb) < _DEPS) {
          const [s, e] = ov(a.z0, a.z1, b.z0, b.z1);
          if (e > s) cut('x@' + pa.toFixed(2), s, e);
        }
      for (const [pa, pb] of [[a.z1, b.z0], [b.z1, a.z0]])
        if (Math.abs(pa - pb) < _DEPS) {
          const [s, e] = ov(a.x0, a.x1, b.x0, b.x1);
          if (e > s) cut('z@' + pa.toFixed(2), s, e);
        }
    }
  }
  return doors;
}
/* One run of partition, minus the doorways cut into its line. Returns the
   solid pieces as [centre, length] along the run. */
function runSegments(doors, key, s, e) {
  let parts = [[s, e]];
  for (const [d0, d1] of doors.get(key) ?? []) {
    const next = [];
    for (const [a, b] of parts) {
      if (d1 <= a || d0 >= b) { next.push([a, b]); continue; }
      if (d0 > a) next.push([a, d0]);
      if (d1 < b) next.push([d1, b]);
    }
    parts = next;
  }
  return parts.filter(([a, b]) => b - a > .05)
              .map(([a, b]) => [(a + b) / 2, b - a]);
}
/* Record a piece of hall fabric where it is DRAWN, in the one shape the
   push-out reads. The hall is not turned, so it is its own frame. */
/* The things on the grounds that are not halls: the chapter hall's drum,
   the yard's light mast and its perimeter, the stand posts. They live in
   one campus-level entry, recorded where they are BUILT, and they are
   discs because they are round. */
function campusSolid(x, z, r) {
  if (!solids.length || !solids[0].props)
    solids.unshift({ cx: 0, cz: 0, cos: 1, sin: 0, reach: 0,
                     props: true, rects: [] });
  const e = solids[0];
  e.rects.push({ u: x, v: z, r });
  // one reach over the lot, so a stroll on the far side of the grounds
  // tests one number instead of forty
  e.reach = Math.max(e.reach, Math.hypot(x, z) + r + 1);
}
function wallRect(x, z, hw, hd) {
  // one entry holding every rect: a hall is one frame, and the walker is
  // always inside it, so there is nothing for a per-entry reach to skip
  if (!hallSolids.length)
    hallSolids.push({ cx: 0, cz: 0, cos: 1, sin: 0, reach: Infinity, rects: [] });
  hallSolids[0].rects.push({ u: x, v: z, hw, hd });
}

/* ------------------------------------------------------------- the walk ---
   Speeds a person actually moves at. 1.7 m/s is a brisk walk; 5.0 m/s on
   Shift is a real run, not the 10 m/s this used to do. The grounds are
   large on purpose - a city layer is a real city - so crossing one takes
   the time crossing one takes; the minimap, the door prompts and the deep
   links are how you skip it, not an impossible sprint. */
const WALK_MS = 1.7, RUN_MS = 5.0, EYE_H = 1.7, BACK_FRAC = .62;
const WALK_SPOOL = { up: 6.5, down: 9.5 };   // a body, not a hydraulic drive
let wkF = 0, wkS = 0;                        // spooled walk / strafe levels

/* The stride. Cadence is speed over step length, and step length grows with
   speed the way a real one does, so a walk lands near 105 steps/min and a
   run near 180 - which is why the bob and the footfalls read as a gait
   rather than a metronome. The head rises and falls on the same phase.
   SCHEMATIC: the shape of a gait, not a gait analysis. */
let wkPhase = 0, wkFoot = 0;
// a probe drives the walker hundreds of thousands of steps: it must not
// move the page it is measuring, and it must not make it scream either
let wkSilent = false;
function strideStep(speed, dt) {
  if (speed < .12) { wkPhase = 0; return 0; }
  const stepM = .62 + speed * .21;           // longer stride, faster gait
  wkPhase += (speed / stepM) * Math.PI * dt; // one PI of phase is one foot
  const foot = Math.floor(wkPhase / Math.PI);
  if (foot !== wkFoot) { wkFoot = foot; if (!wkSilent) footfall(speed / RUN_MS); }
  return Math.sin(wkPhase * 2) * (.011 + speed * .006);
}

/* What is underfoot, as the registries know it: inside a hall it is the
   room's own floor finish, and outdoors it is the campus or site ground
   recipe. Both resolve to one of the six step families declared in the
   build, which is where the timbre lives - nothing is restated here. */
// one place turns a built finish into a step family, so a room's floor and
// a training stand's pad cannot come to disagree about what a slab sounds like
const famOfFinish = (fin) => D.step.floor[fin?.pattern] ?? 'hard';
function stepFamily() {
  if (view === 'hall' && curRoom)
    return famOfFinish(D.finCat[D.finishes[slug][curRoom.strand].surface]);
  // on the grounds, a training stand is its own surface underfoot
  if (view === 'campus')
    for (const p of yardPads)
      if (Math.abs(xrRig.position.x - p.x) < p.hw
        && Math.abs(xrRig.position.z - p.z) < p.hd) return p.fam;
  /* Otherwise the same record that laid the ground says what it is: the
     site's own recipe at a restoration site, the campus atmosphere's on the
     grounds.

     The ROADS are deliberately not sampled, and that is a finding rather
     than an omission. A roadway takes the campus's own ground recipe unless
     that ground is grass or sand, and all ten campuses are laid on concrete
     or asphalt - which are the same step family. So a road-versus-ground
     test would be a branch that cannot change the answer on any campus that
     exists. If a campus is ever laid on grass, this is the place. */
  const g = view === 'restoration'
    ? (curRestoSite?.ground ?? 'grass')
    : (ATMOS[campusKey] ?? DEF_ATMOS).ground;
  return D.step.ground[g] ?? 'hard';
}

/* A footstep, synthesised: a short noise burst through a bandpass the
   family tunes, plus a ring for the families that ring. No recording of a
   real floor is loaded, here or anywhere else in this page. */
function footfall(effort) {
  if (!ac) return;
  const k = D.step.fam[stepFamily()];
  if (!k) return;
  const t = ac.currentTime;
  const n = Math.max(1, Math.floor(ac.sampleRate * k.dur));
  const buf = ac.createBuffer(1, n, ac.sampleRate);
  const d = buf.getChannelData(0);
  // the grit term decides how much of the burst survives past the impact:
  // a hard floor is all attack, loose aggregate keeps rustling
  for (let i = 0; i < n; i++) {
    const x = i / n;
    d[i] = (Math.random() * 2 - 1) * Math.pow(1 - x, 1 + (1 - k.grit) * 7);
  }
  const src = ac.createBufferSource(), f = ac.createBiquadFilter();
  const g = ac.createGain();
  src.buffer = buf;
  f.type = 'bandpass'; f.frequency.value = k.f; f.Q.value = k.q;
  // heavier on the boot when running, and never two identical steps
  const vol = (.05 + effort * .05) * (.86 + Math.random() * .28);
  g.gain.setValueAtTime(vol, t);
  g.gain.exponentialRampToValueAtTime(.0008, t + k.dur);
  src.connect(f); f.connect(g); g.connect(master); src.start(t);
  if (k.ring > 0) {
    const o = ac.createOscillator(), rg = ac.createGain();
    o.type = 'triangle';
    o.frequency.setValueAtTime(k.f * (.94 + Math.random() * .12), t);
    rg.gain.setValueAtTime(vol * k.ring, t);
    rg.gain.exponentialRampToValueAtTime(.0008, t + k.dur * 1.6);
    o.connect(rg); rg.connect(master); o.start(t); o.stop(t + k.dur * 1.7);
  }
}

const _wf = new THREE.Vector3(), _wr = new THREE.Vector3();
// scratch vectors for the walk (module scope, like _wf/_wr/_lblPos): the
// loop allocated five to eight Vector3s per frame in the campus stroll
const _wp = new THREE.Vector3(), _twWas = new THREE.Vector3(), _twF = new THREE.Vector3();
const _twR = new THREE.Vector3(), _twEye = new THREE.Vector3();
function walkStep(dt) {
  const rig = xrRig.position;
  if (renderer.xr.isPresenting) {
    xrMove(dt);
    // a local-floor space puts the floor at the rig; a plain local space
    // reports the head near zero, so the rig itself stands at eye height
    rig.y = xrFloor ? 0 : XR_LOCAL_EYE;
  } else {
    // forward is where the camera looks, flattened; right is its x axis -
    // the same vectors PointerLockControls.moveForward/moveRight use, on
    // the rig instead of the camera
    /* The walker used to be a hovercraft: full speed on the first frame, a
       dead stop on the last, and 41% faster on the diagonal, because two
       full-speed vectors were added together. And "walking" was 5 m/s -
       18 km/h, which is a sprint. A body leans into a stride and settles
       out of one, does not gain speed by facing a corner, and moves at a
       speed a person moves at. Same doctrine as the machine drives, with a
       body's rates rather than a hydraulic drive's. */
    const fwd = axis(keys.KeyS || keys.ArrowDown, keys.KeyW || keys.ArrowUp);
    const str = axis(keys.KeyA || keys.ArrowLeft, keys.KeyD || keys.ArrowRight);
    // a corner is not a speed-up: the command lands on the unit circle
    const m = Math.hypot(fwd, str);
    wkF = drive(wkF, m ? fwd / m : 0, dt, WALK_SPOOL);
    wkS = drive(wkS, m ? str / m : 0, dt, WALK_SPOOL);
    const top = (keys.ShiftLeft || keys.ShiftRight) ? RUN_MS : WALK_MS;
    // nobody walks backwards as fast as forwards, and nobody runs backwards:
    // the reverse component is held to a back-pedal off the WALK speed, so
    // Shift buys nothing going that way
    const fTop = wkF >= 0 ? top : WALK_MS * BACK_FRAC;
    camera.getWorldDirection(_wf); _wf.y = 0; _wf.normalize();
    _wr.set(-_wf.z, 0, _wf.x);
    rig.addScaledVector(_wf, wkF * fTop * dt);
    rig.addScaledVector(_wr, wkS * top * dt);
    rig.y = EYE_H + strideStep(Math.hypot(wkF * fTop, wkS * top), dt);
  }
  if (view === 'hall') {
    // the shell and the partitions are solid; the box below is the backstop
    pushOutOfSolids(rig, hallSolids);
    const DEP = hallRec.depth * U;
    rig.x = Math.min(21, Math.max(-21, rig.x));
    rig.z = Math.min(DEP/2 - .8, Math.max(-DEP/2 - 26, rig.z));
    const px = rig.x, pz = rig.z;
    let room = null;
    for (const r of roomRects)
      if (px >= r.x0 && px <= r.x1 && pz >= r.z0 && pz <= r.z1) { room = r; break; }
    if (room !== curRoom) {
      curRoom = room;
      if (room) {
        const fin = D.finCat[D.finishes[slug][room.strand].surface];
        document.getElementById('hfocus').textContent =
          room.label + ' \u2014 ' + fin.name;
        document.getElementById('hint').textContent =
          condLine(condOf(slug, room.strand));
      } else {
        document.getElementById('hfocus').textContent = hallRec.focus;
        document.getElementById('hint').textContent = t('hint.walk');
      }
    }
    return;
  }
  if (view === 'restoration') {
    const rlen = Math.hypot(rig.x, rig.z);
    if (rlen > RESTO_R) {
      rig.x *= RESTO_R / rlen; rig.z *= RESTO_R / rlen;
    }
    let rbest = null, rbd = 1e9;
    const rwp = _wp;
    for (const b of restoBeacons) {
      b.getWorldPosition(rwp);
      const d = Math.hypot(rwp.x - rig.x, rwp.z - rig.z);
      if (d < rbd) { rbd = d; rbest = b; }
    }
    if (rbest && rbd < 6) {
      nearTrack = rbest.userData.restoTrack;
      document.getElementById('hint').textContent =
        '⏎ ' + D.restoration.tracks.find((x) => x.id === nearTrack).title;
    } else if (nearTrack) {
      nearTrack = null;
      document.getElementById('hint').textContent = t('hint.walk');
    }
    return;
  }
  // campus stroll: out of the buildings, on the grounds, nearest door offered
  pushOutOfSolids(rig);
  const len = Math.hypot(rig.x, rig.z);
  const lim = walkLim;
  if (len > lim) {
    rig.x *= lim / len; rig.z *= lim / len;
  }
  let best = null, bd = 1e9;
  const wp = _wp;
  for (const b of buildings) {
    b.getWorldPosition(wp);
    const d = Math.hypot(wp.x - rig.x, wp.z - rig.z);
    if (d < bd) { bd = d; best = b; }
  }
  if (best && bd < 11) {
    if (nearPoi) nearPoi = null;
    nearSlug = best.userData.slug;
    const h = D.halls.find(x => x.slug === nearSlug);
    document.getElementById('hint').textContent = '\u23ce ' + h.name;
    return;
  }
  // strolling the city layer: the nearest institution offers its panel
  let pbest = null, pd = 1e9;
  for (const b of cityHits) {
    b.getWorldPosition(wp);
    const d = Math.hypot(wp.x - rig.x, wp.z - rig.z);
    if (d < pd) { pd = d; pbest = b; }
  }
  if (pbest && pd < 14) {
    nearSlug = null;
    nearPoi = pbest.userData.poi;
    document.getElementById('hint').textContent = '\u23ce ' + nearPoi;
  } else if (nearSlug || nearPoi) {
    nearSlug = null; nearPoi = null;
    document.getElementById('hint').textContent = t('hint.walk');
  }
}

__SIM_JS__

__AVATAR_JS__
__ADVISOR_JS__

/* ---------------------------------------------------------------- UI ---- */
function renderChrome() {
  const i = D.i18n[loc];
  document.documentElement.lang = loc;
  document.documentElement.dir = i.dir;
  document.getElementById('back').textContent = '← ' + t('nav.campus');
  const hall = document.getElementById('hall');
  // ✓ stations complete · ▶ every bound seat passed · 🧰 district crib passed
  const mark = (h) => {
    let m = !h.stations.length ? ''
      : h.stations.every((id) => doneStations.has(id)) ? ' ✓' : ' ●';
    const bound = D.sims.bindings[h.slug] ?? [];
    if (bound.length && bound.every((b) => prog.sims[b.sim]?.passed)) m += ' ▶';
    if (prog.tools[h.district]?.passed) m += ' \U0001f9f0';
    return m;
  };
  hall.innerHTML = Object.entries(D.districts).map(([k, d]) =>
    `<optgroup label="${i.districts[k]}">` +
    d.halls.map(sg => `<option value="${sg}" ${sg===slug?'selected':''}>` +
      `${D.halls.find(x=>x.slug===sg).name}${mark(D.halls.find(x=>x.slug===sg))}</option>`).join('') +
    `</optgroup>`).join('');
  const lang = document.getElementById('lang');
  lang.setAttribute('aria-label', t('language.select'));
  lang.innerHTML = Object.entries(D.i18n).map(([c, v]) =>
    `<option value="${c}" ${c===loc?'selected':''}>${v.language}</option>`).join('');
  document.getElementById('regionBtn').textContent = '⌂ ' + t('view.region');
  document.getElementById('walkBtn').textContent = '⤞ ' + t('ui.walk');
  document.getElementById('simBtn').textContent = '▶ ' + t('sim.start');
  document.getElementById('avaBtn').textContent = '👤 ' + t('avatar.title');
  document.getElementById('honesty').textContent =
    t('honesty.taxonomy') + ' ' + t('honesty.content') + ' ' + t('progress.local');
  document.getElementById('pclose').textContent = t('ui.close');
}

/* ------------------------------------------------ training-data recorder
   Three interaction shapes, one per episode: a completed sim run (the
   scenario, the declared control scheme, the measured rubric outcome), an
   advisor exchange (which fixed topic, whether the answer was read from a
   record or written in the advisor registry), a walkaround point checked.
   Episode-level, not frame-by-frame - see D.training.honesty. Device-local,
   like tc-progress, under its OWN key so the two records never collide;
   on by default with a visible toggle; never read by any grader. */
const TR_KEY = D.training.storage.key, TR_ON_KEY = D.training.storage.toggle_key;
function trLoad() {
  try { const a = JSON.parse(localStorage.getItem(TR_KEY)); return Array.isArray(a) ? a : []; }
  catch (e) { return []; }
}
let trainingLog = trLoad();
let trainingOn = (() => {
  try { const v = localStorage.getItem(TR_ON_KEY); return v === null ? true : v === '1'; }
  catch (e) { return true; }
})();
function trainingToggle(on) {
  trainingOn = on;
  try { localStorage.setItem(TR_ON_KEY, on ? '1' : '0'); } catch (e) { /* blocked store */ }
}
function recordEpisode(ep) {
  if (!trainingOn) return;
  trainingLog.push({ t: new Date().toISOString(), ...ep });
  if (trainingLog.length > D.training.storage.cap) trainingLog.shift();
  try { localStorage.setItem(TR_KEY, JSON.stringify(trainingLog)); }
  catch (e) { /* private mode / blocked store: session-only */ }
}

/* TRACE: the finer-grained recorder D.training.honesty.granularity
   describes - off by default (heavier than an episode), its own toggle,
   separate from trainingOn. While on, a running sim's own gauges()
   readout - the exact numbers the dashboard already shows, nothing
   computed anew - is sampled once a second and folded into that sim's
   own episode as outcome.trace when the run ends. Not a per-tick
   physics or joint trajectory: see D.training.trace and D.training.honesty
   for exactly what it is. */
const TRACE_KEY = D.training.trace.toggle_key;
// the sample interval and cap are READ from the embedded registry - the
// one declared pair; training/build.py checks the page reads them here
const TRACE_MS = Math.round(1000 / D.training.trace.sample_hz);
const TRACE_MAX = D.training.trace.max_samples;
let traceOn = (() => {
  try { return localStorage.getItem(TRACE_KEY) === '1'; } catch (e) { return false; }
})();
function traceToggle(on) {
  traceOn = on;
  try { localStorage.setItem(TRACE_KEY, on ? '1' : '0'); } catch (e) { /* blocked store */ }
}
let simTicks = [], traceClock = 0;
function traceStep(dt) {
  if (!traceOn || !sim || !sim.gauges || simTicks.length >= TRACE_MAX) return;
  traceClock += dt * 1000;
  if (traceClock < TRACE_MS) return;
  traceClock = 0;
  simTicks.push({ t: Math.round(simTicks.length * TRACE_MS), gauges: sim.gauges() });
}
function clearTraining() {
  trainingLog = [];
  try { localStorage.removeItem(TR_KEY); } catch (e) { /* blocked store */ }
}
function exportTraining() {
  return JSON.stringify({ pack: 'smartcitix-trade-craft-academy-training-data',
    exported: new Date().toISOString(), episodes: trainingLog });
}

/* ---------------------------------------------- Orbis synthetic-training
   prompts. Text only, built locally from the union registry this page
   already ships - no key, no fetch, no socket, ever. A clip made from one
   of these outside this page is AI-SYNTHESIZED synthetic video for
   robotics-training augmentation, not the real episode log above and not
   footage of any real trade, worker or site. See D.orbis.honesty and
   orbis/build.py for the full contract. */
function orbisPrompt(sg) {
  const h = D.halls.find((x) => x.slug === sg);
  if (!h) return '';
  const district = D.districts[h.district].name;
  return D.orbis.template.replace('{district}', district)
    .replace('{hall}', h.name).replace('{focus}', h.focus);
}
function exportOrbisPrompts() {
  return D.halls.map((h) => `# ${h.slug} \\u2014 ${h.name}\\n${orbisPrompt(h.slug)}`)
    .join('\\n\\n');
}
function openOrbis() {
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const h = D.halls.find((x) => x.slug === slug);
  // this panel only ever builds text (below); the two real apps that
  // actually generate a clip are a separate, deliberate step an operator
  // takes on their own machine, with their own key - named here so this
  // is the one place a learner or operator finds both, not an orphaned
  // text tool next to two runners nothing on this page ever mentions
  const runnerRows = D.orbis.runners.map((r) => `<li><code>${esc(r.path)}/</code>
    \\u2014 <code>${esc(r.model)}</code><br>
    <span style="font-size:10.5px">its own README has the exact install/run steps</span></li>`).join('');
  document.getElementById('pbody').innerHTML = `
    <h2>\U0001f3ac ${esc(D.orbis.model)}</h2>
    <span class="chip">synthetic training video \\u2014 generated outside this page</span>
    <h3>${esc(h.name)}</h3>
    <textarea id="orbisTa" readonly style="width:100%;height:90px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);border-radius:7px;font:12px 'IBM Plex Mono',monospace;padding:7px"></textarea>
    <p><button class="barbtn" id="orbisExpBtn">\\u21aa export all 111</button></p>
    <div id="orbisBox"></div>
    <p style="color:var(--muted);font-size:12px">${esc(D.orbis.honesty.synthetic_not_real)}</p>
    <p style="color:var(--muted);font-size:12px">${esc(D.orbis.honesty.no_network_here)}</p>
    <p style="color:var(--muted);font-size:12px">${esc(D.orbis.honesty.every_module_covered)}
       <button class="barbtn" id="orbisRecBtn" style="font-size:11px;padding:2px 8px">\\u23f1 open training-data records</button></p>
    <h3>Want to actually generate a clip?</h3>
    <p style="color:var(--muted);font-size:12px">This panel only ever builds the text above. Two real, separately-runnable apps checked into this repo do the actual generation \\u2014 install and run either yourself, with your own Reactor API key, on your own machine:</p>
    <ul style="color:var(--muted);font-size:12px;padding-left:18px">${runnerRows}</ul>
    <p style="color:var(--muted);font-size:12px">Neither is installed, started, or given a key by this page or this repo\\u2019s own build \\u2014 that stays true everywhere else in this bundle too.</p>`;
  document.body.classList.add('open');
  const ta = document.getElementById('orbisTa');
  ta.value = orbisPrompt(slug); ta.select();
  // writeText returns a promise: a denied permission rejects it, which a
  // synchronous try/catch never sees - so the promise is caught as well
  try { navigator.clipboard?.writeText(ta.value)?.catch(() => {}); } catch (e) { /* manual copy */ }
  document.getElementById('orbisRecBtn')?.addEventListener('click', openRecords);
}
window.__tc3dOrbis = openOrbis;

// the schools panel: the flipped-classroom model, grade bands and the
// proposed district records, plus a click-through from each flipped
// unit straight to the hall that runs it - nothing here duplicates a
// hall panel's own stations/seat/crib content, it only links to it
function openSchools(focusHall) {
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const stageRows = D.schools.stages.map((s) => `<li style="margin:7px 0">
    <b>${esc(s.title)}</b><br>
    <span style="font-size:12px">${esc(s.what)}</span><br>
    <span style="font-size:11px;color:var(--muted)">${esc(s.implemented_by)}</span></li>`).join('');
  const bandRows = D.schools.bands.map((b) => `<li style="margin:5px 0">
    <b>${esc(b.band)}</b> \\u00b7 ${esc(b.level)}<br>
    <span style="font-size:12px">${esc(b.offer)}</span></li>`).join('');
  const distRows = D.schools.districts.map((d) => `<li style="margin:5px 0">
    <b>${esc(d.district)}</b>, ${esc(d.city)} (${esc(D.campuses[d.campus].name)})<br>
    <span style="font-size:11px;color:var(--muted)">${esc(d.status)}</span></li>`).join('');
  const unitRows = D.schools.units.map((u) => {
    const h = D.halls.find((x) => x.slug === u.hall);
    const sims = u.floor_sims.map((id) => D.sims.sims[id].name).join(', ');
    const here = u.hall === focusHall;
    return `<li id="unit-${esc(u.hall)}" style="margin:6px 0;${here
        ? 'border:1px solid var(--mark);border-radius:8px;padding:6px' : ''}">
      <button class="barbtn" data-hall-goto="${esc(u.hall)}" style="font-size:12px;padding:2px 8px">\\u2192 ${esc(h ? h.name : u.hall)}</button><br>
      <span style="font-size:11px;color:var(--muted)">${esc(sims)}</span></li>`;
  }).join('');
  document.getElementById('pbody').innerHTML = `
    <h2>\U0001f393 Schools \\u00b7 flipped classroom</h2>
    <span class="chip">${D.schools.units.length} flipped units</span>
    <span class="chip">${D.schools.districts.length} proposed districts</span>
    <p style="color:var(--muted);font-size:12px">${esc(D.schools.loop)}</p>
    <h3>The loop</h3>
    <ul style="list-style:none;padding:0">${stageRows}</ul>
    <h3>Grade bands</h3>
    <ul style="list-style:none;padding:0">${bandRows}</ul>
    <h3>Proposed district partners</h3>
    <ul style="list-style:none;padding:0">${distRows}</ul>
    <p style="color:var(--muted);font-size:12px">${esc(D.schools.honesty.districts)}</p>
    <p style="color:var(--muted);font-size:12px">${esc(D.schools.honesty.certification)}</p>
    <h3>Flipped units \\u2014 jump to a hall</h3>
    <ul style="list-style:none;padding:0">${unitRows}</ul>`;
  if (focusHall) document.getElementById('unit-' + focusHall)
    ?.scrollIntoView({ block: 'center' });
  document.body.classList.add('open');
}
window.__tc3dSchools = openSchools;

// a roadmap candidate's own card: no hall stands here to enter, so this
// panel never offers one - a name, a real bearing/distance, the proposed
// district emphasis and the honesty text, nothing more
/* A panel that says why it has nothing to show. Every other refusal in this
   bundle names its reason (ACP-08's safeguards, the hint ladder, the
   rollout lanes); a panel that throws instead is the one place that did
   not, and a stack trace is not a reason a learner can read. */
function refusePanel(why) {
  document.getElementById('pbody').innerHTML =
    '<h2>\u2014</h2><p>' + String(why).replace(/[&<>]/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])) + '</p>';
  document.body.classList.add('open');
  return null;
}

function openCandidate(ck) {
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  // The candidate list empties as candidates are BUILT - it is empty now,
  // with the ten-campus target met - so every id this panel ever knew is
  // eventually a stale id. Reading .districts off undefined threw; a
  // promoted city should say it was promoted.
  const c = D.roadmap.candidates[ck];
  if (!c) {
    // D.campuses IS the built set (build_3d.py says so where it trims the
    // roadmap), so a promoted id is recognised there rather than in a
    // second list that could disagree with it.
    const built = D.campuses[ck];
    return refusePanel(built
      ? `${built.name} is no longer a candidate \u2014 it is built, and it is `
        + 'on the network board with the rest of them.'
      : `There is no candidate campus called \u201c${esc(ck)}\u201d. `
        + `${Object.keys(D.roadmap.candidates).length} candidates remain: the `
        + `${D.roadmap.target}-campus target is met.`);
  }
  const distRows = c.districts.map((dk) =>
    `<li>${esc(D.districts[dk].name)}</li>`).join('');
  document.getElementById('pbody').innerHTML = `
    <h2>\U0001f4cd ${esc(c.name)}</h2>
    <span class="chip">proposed · not built</span>
    <span class="chip">${c.km_from_flagship.toLocaleString('en-US')} km, bearing ${Math.round(c.bearing_from_flagship_deg)}° from the flagship campus</span>
    <p style="color:var(--muted);font-size:12px">${esc(c.city)}, ${esc(c.region)}</p>
    <p>${esc(c.why)}</p>
    <h3>Proposed district emphasis</h3>
    <ul style="list-style:none;padding:0">${distRows}</ul>
    <p style="color:var(--muted);font-size:12px">${esc(D.roadmap.honesty.not_a_claim_of_content)}</p>
    <p style="color:var(--muted);font-size:12px">${esc(D.roadmap.honesty.provenance_tiers)}</p>`;
  document.body.classList.add('open');
}
window.__tc3dCandidate = openCandidate;

// the Bay Restoration panel: real, independently-run restoration sites
// plus the real skills in this bundle's own graph their field work
// draws on - each track links straight to the hall that teaches it
function openRestoration(focusHall, focusSite) {
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const siteRows = D.restoration.sites.map((s) => {
    const wf = s.workforce
      ? `<br><span style="font-size:11px;color:var(--good)">▶ real workforce pathway: ${esc(s.workforce_note)}</span>` : '';
    // environmental-monitoring sites (Hunters Point, Treasure Island
    // NSTI) point at a real monitoring / oversight participation body
    // instead - explicitly not job training, so it never reads as a
    // workforce pathway (NSTI also carries a real workforce note, One
    // Treasure Island's program, which its own text says is not the
    // cleanup)
    const pt = s.participation
      ? `<br><span style="font-size:11px;color:var(--steel)">▶ real monitoring participation: ${esc(s.participation_note)}</span>` : '';
    const camp = s.campus ? `<span class="chip" style="font-size:10.5px">near ${esc(D.campuses[s.campus].name)}</span>` : '';
    const cat = `<span class="chip" style="font-size:10.5px">${s.category === 'environmental-monitoring'
      ? '\U0001f9ea environmental monitoring' : '\U0001f331 habitat restoration'}</span>`;
    const trades = s.trade_needs && s.trade_needs.length
      ? `<br><span style="font-size:11px;color:var(--muted)">real trade fit: ${s.trade_needs.map((tn) => esc(tn)).join(', ')}</span>` : '';
    // the one site that needs it (Treasure Island NSTI) states in its own
    // voice that it is NOT NPL-listed, and which EPA ID is the other place
    const dis = s.disambiguation
      ? `<br><span style="font-size:11px;color:var(--steel)">\u26a0 ${esc(s.disambiguation)}</span>` : '';
    const walk = s.e !== undefined
      ? `<span class="chip" style="font-size:10.5px">\U0001f6b6 walkable in the city layer</span>
         <button class="barbtn" data-resto-walk="${esc(s.id)}"
           style="font-size:11px;padding:2px 8px;margin:2px 0 2px 6px">\U0001f6b6 Walk this site</button>`
      : (s.walkable === false && s.walkable_reason
        ? `<span class="chip" style="font-size:10.5px;color:var(--muted)">not a walkable scene: ${esc(s.walkable_reason)}</span>` : '');
    // real data at the site's own RECORDED-by-org coordinate, fetched live
    // in the learner's own browser only on request - the same two sources
    // (USGS 3DEP elevation, USGS National Map imagery) the city layer's
    // own institution panels already use, never a second copy of either
    const real = s.pin ? `<p style="margin:4px 0 0">
        <button class="opt" data-elev-go="${esc(s.id)}" style="display:inline-block;width:auto;padding:3px 10px;font-size:11px">↕ Elevation</button>
        <button class="opt" data-sat-go="${esc(s.id)}" style="display:inline-block;width:auto;padding:3px 10px;font-size:11px;margin-left:4px">\U0001f6f0 Real aerial view</button>
        <span id="elevr-${esc(s.id)}"></span>
        <span id="satr-${esc(s.id)}" style="display:block"></span></p>` : '';
    // the environmental-monitoring sites' own multi-fact citation lists
    // (Hunters Point, Treasure Island NSTI) - flat, never blended into a
    // walkable scene. Each fact cites its own real source, a September
    // 2026 snapshot of public record, not a live feed.
    const facts = (s.facts && s.facts.length) ? `<ul style="margin:6px 0 0;padding-left:16px;font-size:11.5px">${
      s.facts.map((f) => `<li style="margin:3px 0">${esc(f.text)} <a href="${esc(f.source_url)}" target="_blank" rel="noopener" style="font-size:11px">source</a></li>`).join('')
    }</ul>` : '';
    return `<li id="site-${esc(s.id)}" style="margin:9px 0;${s.id === focusSite
        ? 'border:1px solid var(--mark);border-radius:8px;padding:6px' : ''}">
      <b>${esc(s.name)}</b> ${camp} ${cat}<br>
      <span style="font-size:11.5px;color:var(--muted)">${esc(s.org)} · ${esc(s.city)}, ${esc(s.county)}</span><br>
      <span style="font-size:12px">${esc(s.habitat)} — ${esc(s.scale)}</span>${dis}${wf}${pt}${trades}<br>
      <a href="${esc(s.source_url)}" target="_blank" rel="noopener" style="font-size:11px">${esc(s.source_url)}</a>
      ${walk}${real}${facts}</li>`;
  }).join('');
  const trackRows = D.restoration.tracks.map((t) => {
    const here = focusHall && t.skills.some((sk) => sk.split('.')[0] === focusHall);
    const skillBtns = t.skills.map((sk) => {
      const hall = sk.split('.')[0];
      const h = D.halls.find((x) => x.slug === hall);
      return `<button class="barbtn" data-hall-goto="${esc(hall)}" style="font-size:11px;padding:2px 8px;margin:2px 4px 2px 0">→ ${esc(h ? h.name : hall)}</button>`;
    }).join('');
    return `<li id="track-${esc(t.id)}" style="margin:9px 0;${here
        ? 'border:1px solid var(--mark);border-radius:8px;padding:6px' : ''}">
      <b>${esc(t.title)}</b><br>
      <span style="font-size:12px;color:var(--muted)">${esc(t.what)}</span><br>
      ${skillBtns}</li>`;
  }).join('');
  document.getElementById('pbody').innerHTML = `
    <h2>\U0001f30a Bay Restoration</h2>
    <span class="chip">${D.restoration.sites.length} real sites</span>
    <span class="chip">${D.restoration.tracks.length} field-skill tracks</span>
    <p style="color:var(--muted);font-size:12px">${esc(D.restoration.honesty.not_affiliated)}</p>
    <h3>Real restoration sites</h3>
    <ul style="list-style:none;padding:0">${siteRows}</ul>
    <h3>Field-skill tracks — jump to the hall that teaches it</h3>
    <ul style="list-style:none;padding:0">${trackRows}</ul>
    <p style="color:var(--muted);font-size:12px">${esc(D.restoration.honesty.provenance)}</p>
    <p style="color:var(--muted);font-size:12px">${esc(D.restoration.honesty.no_new_skills)}</p>
    <p style="color:var(--muted);font-size:12px">${esc(D.restoration.honesty.not_certification)}</p>
    <p style="color:var(--muted);font-size:12px">${esc(D.restoration.honesty.environmental_monitoring_category)}</p>`;
  document.body.classList.add('open');
  if (focusSite) {
    document.getElementById('site-' + focusSite)?.scrollIntoView({ block: 'center' });
  } else if (focusHall) {
    const t = D.restoration.tracks.find((x) =>
      x.skills.some((sk) => sk.split('.')[0] === focusHall));
    if (t) document.getElementById('track-' + t.id)?.scrollIntoView({ block: 'center' });
  }
}
window.__tc3dRestoration = openRestoration;

/* ---------------------------------------- the walkable site scene -------- */
// A standalone, ground-level scene for ONE real restoration site - not one
// shared template stamped eight times. Each site's terrain is composed
// from THAT site's own real, registry-sourced habitat/scale/org facts
// (restoration/build.py), the same way dressCampus() customizes each real
// campus by name below. It is schematic ground, not a survey or aerial
// scan of the actual site - the on-screen honesty line says so every time
// a learner enters one, and every prop here (a levee, a nursery bed, a
// monitoring transect) is a fair schematic reading of that site's own
// published description, never an invented detail.
let restoGroup = null, restoBeacons = [], curRestoSite = null;
const RESTO_R = 46;

function stakeLine(n, x0, z0, x1, z1, g, tall) {
  for (let i = 0; i < n; i++) {
    const u = n > 1 ? i / (n - 1) : 0;
    box(.1, tall ?? .9, .1, mat.post, x0 + (x1 - x0) * u, (tall ?? .9) / 2,
      z0 + (z1 - z0) * u, g);
  }
}
function flagAt(x, z, g, color) {
  box(.06, .8, .06, mat.post, x, .4, z, g);
  const f = new THREE.Mesh(new THREE.PlaneGeometry(.4, .26),
    new THREE.MeshStandardMaterial({ color: color ?? 0xE8A33D, side: THREE.DoubleSide }));
  f.position.set(x + .2, .68, z); g.add(f);
}
function vegClump(x, z, g, n, spread) {
  for (let i = 0; i < n; i++) {
    const a = i / n * Math.PI * 2, r = spread * (.3 + .7 * ((i * 53) % 100) / 100);
    // snapped to a coarse step so repeated clumps across a site (up to
    // ~100 spheres) share one of a handful of cached geometries instead
    // of each getting its own BufferGeometry
    const s = Math.round((.35 + ((i * 29) % 100) / 220) * 20) / 20;
    const c = new THREE.Mesh(sphereGeo(s, 6, 5), mat.veg);
    c.position.set(x + Math.cos(a) * r, s * .7, z + Math.sin(a) * r);
    c.castShadow = true; g.add(c);
  }
}
function fieldCanopy(x, z, g) {
  box(2.6, .08, 2.6, mat.slab, x, .04, z, g, false);
  for (const [dx, dz] of [[-1.1, -1.1], [1.1, -1.1], [-1.1, 1.1], [1.1, 1.1]])
    box(.08, 1.8, .08, mat.metal, x + dx, .9, z + dz, g);
  const roof = new THREE.Mesh(new THREE.PlaneGeometry(3, 3),
    new THREE.MeshStandardMaterial({ color: 0xE8A33D, side: THREE.DoubleSide }));
  roof.rotation.x = -Math.PI / 2; roof.position.set(x, 1.84, z); g.add(roof);
  box(.7, .6, .5, mat.part, x + 1.6, .3, z - 1.6, g);
  box(.7, .5, .5, mat.part, x + 1.9, .25, z - 1.3, g);
}
function berm(w, h, d, x, z, rot, g) {
  const b = box(w, h, d, mat.grass, x, h / 2, z, g);
  if (rot) b.rotation.y = rot;
  return b;
}
function waterAt(w, d, x, z, g, rot) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), mat.water);
  m.rotation.x = -Math.PI / 2; if (rot) m.rotation.z = rot;
  m.position.set(x, -.05, z); g.add(m);
  return m;
}

function buildRestoGround(g, site) {
  /* The pad used to be mat.grass at every site, so a tidal marsh, an
     intertidal flat and a dry upland all read as the campus green. Each
     walkable site names its own ground in the restoration registry - by a
     recipe id from the world pack, with the words in its own habitat line
     that chose it - and it is laid here with the relief that recipe
     declares. Schematic, like everything standing on it. */
  const gid = site.ground ?? 'grass';
  const pad = new THREE.Mesh(new THREE.CircleGeometry(RESTO_R + 6, 48),
    groundMat(gid));
  pad.rotation.x = -Math.PI / 2; pad.receiveShadow = true;
  pad.userData.restoGround = gid;
  g.add(pad);

  /* The site's own entry sign. A real restoration site has one at the gate:
     whose project it is, and what kind of work this is. Both are already in
     the registry and were readable only by opening the panel, so a learner
     could walk a site without ever being told whose ground they were on.
     The organisation is named because it is THEIRS - none of these is our
     programme, and the honesty line in the panel says so in words. */
  const entry = label(site.org, site.category.replace(/-/g, ' '), .62,
    { kind: 'placard' });
  entry.position.set(0, 2.4, RESTO_R - 2);
  g.add(entry);

  if (site.id === 'herons-head') {
    // shoreline resilience + green infrastructure, an Eco-Apprentice crew
    // actually working the ground here - riprap shoreline meeting the
    // bay, shallow rain-garden swales set back from it, and the crew's
    // own field canopy since this is a real, active paid-training site
    waterAt(140, 60, 0, -46, g);
    box(120, .08, 18, mat.sand, 0, .05, -22, g, false);
    for (let i = 0; i < 3; i++)
      box(46, .3, 4, mat.grass, -20 + i * 20, .18, 2 + i * 9, g, false);
    vegClump(24, 12, g, 10, 8);
    fieldCanopy(-18, 16, g);
  } else if (site.id === 'candlestick-point') {
    // rocky shoreline stewardship: clean-up bins along the tideline, a
    // native-plant propagation bed, and a numbered monitoring transect -
    // the site's own three named activities, nothing added
    waterAt(150, 50, 0, -50, g);
    for (let i = -2; i <= 2; i++)
      box(1.6 + Math.abs(i) * .2, .7, 1.6, mat.steel, i * 9, .35, -34, g);
    vegClump(-22, 10, g, 14, 7);
    stakeLine(6, -30, 0, 30, 0, g, 1.1);
  } else if (site.id === 'east-oakland-youth') {
    // Planting Justice: shoreline and upland restoration, a youth nursery
    // laid out in rows, and a stump-seat circle for the service-learning
    // cohort the site's own program actually trains
    waterAt(130, 46, 0, -44, g);
    for (let r = 0; r < 4; r++) for (let c = 0; c < 8; c++)
      vegClump(-24 + c * 6.4, 8 + r * 6, g, 3, 1.6);
    for (let i = 0; i < 8; i++) {
      const a = i / 8 * Math.PI * 2;
      box(.7, .4, .7, mat.wood, Math.cos(a) * 4 + 16, .2, Math.sin(a) * 4 - 6, g);
    }
  } else if (site.id === 'alviso-shoreline') {
    // the smallest funded footprint in the pack ("approximately 2 acres")
    // - a modest marsh-adjacent wet edge, not a bay frontage, with its
    // own restored-area boundary flagged at the corners
    waterAt(50, 20, 20, -18, g, .15);
    vegClump(6, -8, g, 16, 14);
    for (const [x, z] of [[-16, -16], [16, -16], [-16, 16], [16, 16]])
      flagAt(x, z, g, 0xE8A33D);
  } else if (site.id === 'south-bay-salt-ponds') {
    // a real ecotone levee dividing the managed former salt pond (still
    // water) from the tidal marsh it is being restored into (broken,
    // channelled water) - the actual before/after this project performs
    berm(90, 1.6, 5, 0, 0, 0, g);
    waterAt(80, 30, 0, -22, g);
    waterAt(70, 10, -30, 24, g, .3);
    waterAt(70, 8, 26, 30, g, -.25);
    vegClump(30, 22, g, 12, 10);
  } else if (site.id === 'montezuma-wetlands') {
    // diked baylands along the real, named Montezuma Slough, with duller,
    // shallower seasonal-wetland pools set apart from the slough itself
    berm(120, 1.3, 4, 0, -8, 0, g);
    waterAt(140, 16, 0, -30, g);
    const seasonal = new THREE.MeshStandardMaterial({ color: 0x6a7a5e, roughness: .5 });
    for (const [x, z, w, d] of [[-22, 14, 16, 10], [10, 20, 20, 8], [28, 8, 10, 12]]) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), seasonal);
      m.rotation.x = -Math.PI / 2; m.position.set(x, -.04, z); g.add(m);
    }
  } else if (site.id === 'american-canyon') {
    // honestly what the registry itself says this is: a PLAN summarizing
    // restoration opportunities, not built work yet - so the ground here
    // reads proposed and dashed, the same visual language the roadmap
    // board already uses for AUTHORED-but-not-built content
    for (let i = 0; i < 28; i += 2) {
      const a = i / 28 * Math.PI * 2;
      box(1.4, .04, .12, mat.paint, Math.cos(a) * 30, .03, Math.sin(a) * 30, g, false)
        .rotation.y = -a;
    }
    waterAt(120, 40, 0, -50, g);
    const l = label('proposed · not yet built', 'AUTHORED', 1.3, { kind: 'schematic' });
    l.position.set(0, 6, 0); g.add(l);
  } else if (site.id === 'straw-north-bay') {
    // STRAW (Students and Teachers Restoring a Watershed): a long, narrow
    // transition-zone corridor - real to the registry's own "1.3 linear
    // miles across four sites" - marked with small student-group flags
    // rather than one crew canopy
    waterAt(160, 14, 0, -6, g, .08);
    for (let i = -3; i <= 3; i++) vegClump(i * 11, 8 + Math.abs(i), g, 6, 5);
    for (let i = -2; i <= 2; i++) flagAt(i * 15, 20, g, 0x41C4D4);
  }
}

function buildRestoTrackBeacons(g) {
  restoBeacons = [];
  D.restoration.tracks.forEach((tr, i) => {
    const ang = i / D.restoration.tracks.length * Math.PI * 2 + Math.PI / 2;
    const x = Math.cos(ang) * 14, z = Math.sin(ang) * 14 + 6;
    box(.4, 2.2, .4, mat.post, x, 1.1, z, g);
    const sign = box(1.5, .9, .08, mat.paint, x, 2.1, z, g);
    sign.userData.restoTrack = tr.id;
    restoBeacons.push(sign);
    const l = label(tr.title, 'field-skill track', 1.1, { kind: 'station' });
    l.position.set(x, 3.3, z); g.add(l);
  });
}

function openRestoTrack(trackId) {
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const tr = D.restoration.tracks.find((x) => x.id === trackId);
  if (!tr || !curRestoSite) return;
  const tabs = D.restoration.tracks.map((x) =>
    `<button class="barbtn" data-resto-track="${esc(x.id)}"
      style="font-size:11px;padding:2px 8px;margin:2px 4px 2px 0;${x.id === trackId
        ? 'border-color:var(--mark);color:var(--mark)' : ''}">${esc(x.title)}</button>`).join('');
  const skillBtns = tr.skills.map((sk) => {
    const hall = sk.split('.')[0];
    const h = D.halls.find((x) => x.slug === hall);
    return `<button class="barbtn" data-hall-goto="${esc(hall)}" style="font-size:11px;padding:2px 8px;margin:2px 4px 2px 0">→ ${esc(h ? h.name : hall)}</button>`;
  }).join('');
  document.getElementById('pbody').innerHTML = `
    <h2>${esc(tr.title)}</h2>
    <span class="chip">at ${esc(curRestoSite.name)}</span>
    <p style="color:var(--muted);font-size:12px">${esc(tr.what)}</p>
    <p style="font-size:12px">${esc(curRestoSite.habitat)} — ${esc(curRestoSite.scale)}</p>
    <h3>Train this at the real hall that teaches it</h3>
    <p>${skillBtns}</p>
    <h3>Other tracks at this site</h3>
    <p>${tabs}</p>
    <p style="color:var(--muted);font-size:12px">${esc(D.restoration.honesty.no_new_skills)}</p>`;
  document.body.classList.add('open');
}
window.__tc3dRestoTrack = openRestoTrack;

function teardownRestoWalk() {
  if (!curRestoSite) return;
  if (restoGroup) { scene.remove(restoGroup); disposeOf(restoGroup); restoGroup = null; }
  restoBeacons = []; nearTrack = null; curRestoSite = null;
  clearFauna();
}
function exitRestoWalk() {
  const ck = curRestoSite?.campus ?? campusKey;
  teardownRestoWalk();
  showCampus(ck);
}
function startRestorationWalk(siteId) {
  const site = D.restoration.sites.find((s) => s.id === siteId && s.e !== undefined);
  if (!site) return;
  walkLeave();
  if (sim) teardownSim();
  if (curRestoSite) teardownRestoWalk();
  view = 'restoration'; curRestoSite = site; campusKey = site.campus;
  if (hallGroup) hallGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  if (regionGroup) regionGroup.visible = false;
  if (avatarGroup) avatarGroup.visible = false;
  ground.visible = grid.visible = false;
  applyAtmos(site.campus);
  restoGroup = new THREE.Group();
  buildRestoGround(restoGroup, site);
  buildRestoTrackBeacons(restoGroup);
  scene.add(restoGroup);
  spawnFauna(site.campus, RESTO_R);
  scene.fog.near = 30 * fogMul; scene.fog.far = 130 * fogMul;
  controls.maxDistance = 90; controls.minDistance = 8;
  camera.position.set(0, 13, 40); controls.target.set(0, 1, -10);
  document.getElementById('mm').style.display = 'none';
  document.getElementById('hname').textContent = site.name;
  document.getElementById('hfocus').textContent = site.org + ' · ' + site.habitat;
  document.getElementById('hint').textContent =
    'Schematic ground, composed from this site’s own real habitat '
    + 'description — not a survey or aerial scan of the actual site.';
  document.getElementById('walkBtn').style.display = '';
  document.getElementById('avaBtn').style.display = 'none';
  const cb = document.getElementById('campusBtn');
  cb.style.display = ''; cb.textContent = '↑ ' + D.campuses[site.campus].name;
  document.getElementById('simBtn').style.display = 'none';
  document.getElementById('glbBtn').style.display = 'none';
  document.getElementById('glbInBtn').style.display = 'none';
  document.getElementById('satBtn').style.display = 'none';
}
/* A fixed-step drive of the walker, for the same reason opRunHeadless
   exists for the seats: a desktop walk is entered through pointer lock,
   which no headless browser grants, so the kinematics are exercised
   directly here. It leaves the rig, the keys and the spooled levels exactly
   as it found them, so a probe cannot move the page it is measuring. */
/* The companion to the walk probe: strolls out from the plaza on N
   headings and reports how many fixed steps ended up INSIDE a building.
   It reads the footprints the collision itself uses, so the two cannot
   disagree about where a hall is - only about whether the push-out worked.
   Leaves the rig where it found it, like the walk probe. */
/* The hall's contract, proven rather than hoped for. Giving the partitions
   substance without giving them doorways would seal every room, so the two
   facts are tested together on a grid over the hall's own footprint:

     - no cell a body fits in is inside a wall (the push-out's job), and
     - EVERY room still holds a cell reachable on foot from the doorway,

   the second being the failure mode that matters. The flood is over the
   same rectangles the collision reads, so the test and the walls cannot
   disagree about where a wall is. */
window.__tc3dHallTest = (cell = .3) => {
  if (view !== 'hall' || !hallSolids.length) return { skipped: 'not in a hall' };
  const DEP = hallRec.depth * U, W = 12 * U;
  const rects = hallSolids[0].rects;
  const blocked = (x, z) => {
    for (const b of rects)
      if (Math.abs(x - b.u) < b.hw + BODY_R && Math.abs(z - b.v) < b.hd + BODY_R)
        return true;
    return false;
  };
  const nx = Math.floor(W / cell), nz = Math.floor((DEP + 2) / cell);
  const at = (i, j) => [-W / 2 + (i + .5) * cell, -DEP / 2 - 1 + (j + .5) * cell];
  const open = new Uint8Array(nx * nz), seen = new Uint8Array(nx * nz);
  let free = 0;
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const [x, z] = at(i, j);
    if (!blocked(x, z)) { open[j * nx + i] = 1; free++; }
  }
  // flood from the open front, which is how a walker gets in
  const q = [];
  for (let i = 0; i < nx; i++) if (open[i]) { seen[i] = 1; q.push(i); }
  for (let h = 0; h < q.length; h++) {
    const k = q[h], i = k % nx, j = (k - i) / nx;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const i2 = i + di, j2 = j + dj;
      if (i2 < 0 || j2 < 0 || i2 >= nx || j2 >= nz) continue;
      const k2 = j2 * nx + i2;
      if (open[k2] && !seen[k2]) { seen[k2] = 1; q.push(k2); }
    }
  }
  const unreachable = [];
  for (const r of roomRects) {
    let ok = false;
    for (let j = 0; j < nz && !ok; j++) for (let i = 0; i < nx && !ok; i++) {
      if (!seen[j * nx + i]) continue;
      const [x, z] = at(i, j);
      if (x >= r.x0 && x <= r.x1 && z >= r.z0 && z <= r.z1) ok = true;
    }
    if (!ok) unreachable.push(r.label);
  }
  // and the walker itself: out of the doorway on many headings, counting
  // the steps that ended up inside a wall. The grid above proves the rooms
  // can be reached; this proves the walls cannot be crossed.
  const p0 = xrRig.position.clone(), r0 = xrRig.rotation.y;
  const wasKeys = { ...keys }, wasF = wkF, wasS = wkS;
  const wasSilent = wkSilent; wkSilent = true;
  const dt = 1 / 60, n = Math.round(24 / dt);
  let steps = 0, breaches = 0, contacts = 0;
  for (let hh = 0; hh < 36; hh++) {
    xrRig.position.set(0, EYE_H, -DEP / 2 + 1.2);
    camera.rotation.set(0, 0, 0);
    xrRig.rotation.y = (hh / 36) * Math.PI * 2;
    xrRig.updateMatrixWorld(true);
    wkF = wkS = 0;
    for (const k of Object.keys(keys)) delete keys[k];
    keys.KeyW = true;
    for (let i = 0; i < n; i++) {
      walkStep(dt); steps++;
      const x = xrRig.position.x, z = xrRig.position.z;
      for (const b of rects) {
        if (Math.abs(x - b.u) < b.hw && Math.abs(z - b.v) < b.hd) { breaches++; break; }
      }
      if (blocked(x, z)) contacts++;
    }
  }
  for (const k of Object.keys(keys)) delete keys[k];
  Object.assign(keys, wasKeys);
  xrRig.position.copy(p0); xrRig.rotation.y = r0;
  wkF = wasF; wkS = wasS; wkSilent = wasSilent;
  return { slug, rooms: roomRects.length, walls: rects.length,
           cells: nx * nz, free, reached: q.length, unreachable,
           steps, breaches, contacts };
};
window.__tc3dSolidTest = (headings = 72, seconds = 200, dt = 1 / 60) => {
  const p0 = xrRig.position.clone(), r0 = xrRig.rotation.y;
  const wasSilent = wkSilent; wkSilent = true;
  const wasKeys = { ...keys }, wasF = wkF, wasS = wkS;
  // inside the building itself, and inside the body-width boundary the
  // push-out holds: the first must never happen, the second is the contact
  // that proves this walk actually met a wall
  const probe = (x, z, pad) => {
    for (const d of solids) {
      const dx = x - d.cx, dz = z - d.cz;
      if (dx * dx + dz * dz > (d.reach + pad) * (d.reach + pad)) continue;
      const u = dx * d.cos - dz * d.sin, v = dx * d.sin + dz * d.cos;
      for (const b of d.rects) {
        // discs and rectangles both live in this list, and a probe that
        // only understood rectangles would report nothing at all about the
        // round things - which is how a test comes to prove nothing
        if (b.r !== undefined) {
          if (Math.hypot(u - b.u, v - b.v) < b.r + pad) return true;
        } else if (Math.abs(u - b.u) < b.hw + pad
                   && Math.abs(v - b.v) < b.hd + pad) return true;
      }
    }
    return false;
  };
  let steps = 0, breaches = 0, contacts = 0, met = 0, worst = 0;
  const n = Math.max(1, Math.round(seconds / dt));
  for (let h = 0; h < headings; h++) {
    const a = (h / headings) * Math.PI * 2;
    xrRig.position.set(0, EYE_H, 0);
    camera.rotation.set(0, 0, 0);
    xrRig.rotation.y = a;
    // the heading only exists once the matrix carries it: walkStep asks the
    // camera for its WORLD direction, and nothing has rendered since
    xrRig.updateMatrixWorld(true);
    wkF = wkS = 0;
    for (const k of Object.keys(keys)) delete keys[k];
    keys.KeyW = true;
    let touchedHere = false;
    for (let i = 0; i < n; i++) {
      walkStep(dt); steps++;
      const x = xrRig.position.x, z = xrRig.position.z;
      if (probe(x, z, 0)) breaches++;
      if (probe(x, z, BODY_R + 1e-3)) { contacts++; touchedHere = true; }
    }
    if (touchedHere) met++;
    worst = Math.max(worst, Math.hypot(xrRig.position.x, xrRig.position.z));
  }
  for (const k of Object.keys(keys)) delete keys[k];
  Object.assign(keys, wasKeys);
  xrRig.position.copy(p0); xrRig.rotation.y = r0; wkF = wasF; wkS = wasS;
  wkSilent = wasSilent;
  return { headings, seconds: n * dt, steps, breaches, contacts,
           headingsThatMetAWall: met, solids: solids.length,
           rects: solids.reduce((a, d) => a + d.rects.length, 0),
           farthest: +worst.toFixed(1) };
};
/* What the walker is standing on, and what each training stand is made of.
   Reads the live rects - not a second list - and with a point given it
   samples there and puts the walker back where it was. */
window.__tc3dUnderfoot = (x, z) => {
  if (x === undefined)
    return { here: stepFamily(),
             pads: yardPads.map((p) => ({ x: +p.x.toFixed(1),
                                          z: +p.z.toFixed(1), fam: p.fam })) };
  const ax = xrRig.position.x, az = xrRig.position.z;
  xrRig.position.x = x; xrRig.position.z = z;
  const here = stepFamily();
  xrRig.position.x = ax; xrRig.position.z = az;
  return { here };
};
window.__tc3dWalkProbe = (keyList, seconds, dt = 1 / 60) => {
  const wasKeys = { ...keys };
  const wasSilent = wkSilent; wkSilent = true;
  const p0 = xrRig.position.clone();
  const wasF = wkF, wasS = wkS, wasPhase = wkPhase, wasFoot = wkFoot;
  wkF = wkS = 0;
  for (const k of Object.keys(keys)) delete keys[k];
  for (const k of keyList) keys[k] = true;
  const n = Math.max(1, Math.round(seconds / dt));
  for (let i = 0; i < n; i++) walkStep(dt);
  const dx = xrRig.position.x - p0.x, dz = xrRig.position.z - p0.z;
  const dist = Math.hypot(dx, dz);
  for (const k of Object.keys(keys)) delete keys[k];
  Object.assign(keys, wasKeys);
  xrRig.position.copy(p0);
  wkF = wasF; wkS = wasS; wkPhase = wasPhase; wkFoot = wasFoot;
  wkSilent = wasSilent;
  return { dist: +dist.toFixed(3), seconds: n * dt,
           mps: +(dist / (n * dt)).toFixed(3), family: stepFamily() };
};
window.__tc3dRestoWalk = startRestorationWalk;
window.__tc3dRestoExit = exitRestoWalk;

/* The learner record is device-local only - localStorage, every access
   wrapped so a blocked store never breaks the page - and the honesty line
   in the corner says exactly that. Not a transcript, not certification. */
const PROG_KEY = 'tc-progress';
function loadProg() {
  try { return JSON.parse(localStorage.getItem(PROG_KEY)) ?? {}; }
  catch (e) { return {}; }
}
function saveProg() {
  prog.stations = [...doneStations];
  try { localStorage.setItem(PROG_KEY, JSON.stringify(prog)); }
  catch (e) { /* private mode / blocked store: session-only progress */ }
}
const prog = loadProg();
const doneStations = new Set(Array.isArray(prog.stations) ? prog.stations : []);
prog.sims = typeof prog.sims === 'object' && prog.sims ? prog.sims : {};
prog.tools = typeof prog.tools === 'object' && prog.tools ? prog.tools : {};
prog.walk = typeof prog.walk === 'object' && prog.walk ? prog.walk : {};
let curStation = null;
function scoreChip() {
  const h = D.halls.find(x => x.slug === slug);
  if (view !== 'hall' || !h) return '';
  // the hall's whole training loop reads out here: stations, seats, crib
  const parts = [];
  if (h.stations.length) {
    const d = h.stations.filter((id) => doneStations.has(id)).length;
    parts.push(`\u2713 ${d}/${h.stations.length}`);
  }
  const bound = D.sims.bindings[slug] ?? [];
  if (bound.length)
    parts.push(`\u25b6 ${bound.filter((b) => prog.sims[b.sim]?.passed).length}/${bound.length}`);
  if (prog.tools[h.district]?.passed) parts.push('\U0001f9f0 \u2713');
  return parts.length ? '  ' + parts.join(' \u00b7 ') : '';
}
function openStation(id) {
  curStation = id;
  const s = D.stations[id]; const i = D.i18n[loc];
  document.getElementById('pbody').innerHTML = `
    <h2>${s.name}</h2>
    <span class="chip">${s.room}</span><span class="chip">${i.strands[s.strand]} · ${i.tiers[s.tier]}</span>
    <p>${s.lesson}</p><p style="color:var(--muted)">${s.doctrine}</p>
    <h3>${t('station.checklist')}</h3><ul>${s.checklist.map(c=>`<li>${c}</li>`).join('')}</ul>
    <h3>${t('station.quiz')}</h3><div class="q">${s.quiz.question}
      ${s.quiz.options.map(o=>`<button class="opt" data-ok="${o.correct?1:0}">${o.label}</button>`).join('')}</div>`;
  document.body.classList.add('open');
}

__PIPELINE_JS__

function condOf(hallSlug, strand) {
  return D.condOver[hallSlug]?.[strand] ?? D.baseCond[strand];
}
function condLine(c) {
  return `${c.lux} lx \u00b7 ${c.ach} ACH \u00b7 ${c.noise_db} dB \u00b7 `
    + `${c.temp_c[0]}\u2013${c.temp_c[1]} \u00b0C \u00b7 PPE: `
    + (c.ppe.length ? c.ppe.join(', ') : '\u2014');
}

function openRoom(roomLabel) {
  const h = D.halls.find(x => x.slug === slug);
  const r = h.rooms.find(x => x.label === roomLabel);
  const i = D.i18n[loc];
  const sm = D.strandmods[r.strand];
  const F = (n) => n.toLocaleString('en-US');
  const rows = sm.samples.map(x => {
    const id = 'u' + String(h.index).padStart(3, '0') + '.' + x.suffix;
    const st = pipeline(h.index, x.level);
    return `
    <tr><td style="font-family:'IBM Plex Mono',monospace;font-size:12px">${id}</td>
    <td>${i.tiers[x.tier]}</td><td>${x.form}</td>
    <td style="text-align:end">${x.d}</td><td>${i.states[st]}</td></tr>`; }).join('');
  document.getElementById('pbody').innerHTML = `
    <h2>${r.label}</h2>
    <span class="chip">${i.strands[r.strand]}</span>
    <span class="chip">${r.w*3}×${r.h*3} m</span>
    <p style="color:var(--muted)">${r.purpose}</p>
    ${r.fixtures?.length ? `<ul>${r.fixtures.map(f=>`<li>${f}</li>`).join('')}</ul>` : ''}
    ${r.strand === 'tools' ? `<p><button class="barbtn" data-crib="${h.district}">🧰 ${D.tools.cribs[h.district].name}</button></p>` : ''}
    ${(() => { const pf = D.finishes[h.slug][r.strand];
      const fin = D.finCat[pf.surface];
      return `<h3>${t('room.finish')}</h3>
        <p><b>${fin.name}</b>` +
        (pf.placed_by === 'hazard'
          ? ` <span class="chip">${pf.hazard}</span>` : '') +
        `<br><span style="color:var(--muted)">${fin.why}.</span></p>` +
        (() => { const c = condOf(h.slug, r.strand);
          return `<p style="color:var(--muted);font-size:13px">${condLine(c)}` +
            (c.hazards?.length
              ? '<br>' + c.hazards.map(z=>`<span class="chip">${z}</span>`).join(' ')
              : '') + `</p>
            <p style="font-size:11px;color:var(--muted);opacity:.8">geometry: SCHEMATIC \u00b7 finish: DERIVED \u00b7 conditions: DERIVED</p>`; })(); })()}
    <h3>${t('map.layer.modules')}</h3>
    <p style="color:var(--muted);font-size:13px">
      ${t('figures.lessons').replace('{n}', F(sm.lessons))} ·
      ${t('figures.modules').replace('{n}', F(sm.modules))} ·
      θ ${sm.d_from}–${sm.d_to}</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tbody>${rows}</tbody></table>
    <style>#pbody td{border-top:1px solid var(--rule);padding:6px 8px;color:var(--muted)}</style>`;
  document.body.classList.add('open');
}

/* -------------------------------------------------- the crib + drill ---- */
// The crib drill keeps the registry's own contract: a pick is right or
// wrong against the crib record, the option order is index arithmetic,
// not chance, and the result lands in the same device-local record.
/* The walkaround panel: one clipboard, the whole card's state, and the
   mark. Non-gating by registry rule - nothing reads waDone but the HUD. */
function openWa(i) {
  // A walkaround point belongs to the seat you are sitting in, so there has
  // to BE one. Called with no seat active (the __tc3dDo harness hook can do
  // that, and so could a stale button left over from a torn-down sim) this
  // used to read .walkaround off undefined and throw a raw TypeError. A
  // refusal is explained, never silent, and never a stack trace.
  const def = D.sims.sims[curSimId];
  if (!def) return refusePanel('There is no simulator running, and a '
    + 'walkaround is a check on the machine you are about to operate.');
  const w = def.walkaround[i];
  if (!w) return refusePanel(`That seat has ${def.walkaround.length} `
    + `walkaround points; there is no point ${i}.`);
  document.getElementById('pbody').innerHTML = `
    <h2>📋 ${w.point}</h2>
    <span class="chip">${def.name}</span>
    <span class="chip">${waDone.size}/${waTotal}</span>
    <p>${w.check}.</p>
    ${waDone.has(i) ? `<p style="color:var(--good)">✓</p>`
      : `<p><button class="barbtn" data-wa="${i}">✓ ${w.point}</button></p>`}
    <ul style="color:var(--muted);font-size:12.5px">${def.walkaround.map((x, j) =>
      `<li>${waDone.has(j) ? '✓' : '·'} ${x.point}</li>`).join('')}</ul>
    <p style="color:var(--muted);font-size:12px">${D.sims.walkHonesty}</p>`;
  document.body.classList.add('open');
}

let curCrib = null, drill = null;
function openCrib(dk) {
  curCrib = dk; curStation = null; drill = null;
  const c = D.tools.cribs[dk];
  const rec = prog.tools[dk];
  document.getElementById('pbody').innerHTML = `
    <h2>${c.name}</h2>
    <span class="chip">${D.i18n[loc].districts[dk]}</span>
    <span class="chip">${c.tools.length}</span>
    ${rec?.passed ? `<span class="chip" style="border-color:var(--good);color:var(--good)">✓ ${D.tools.drill.name}</span>` : ''}
    <ul style="list-style:none;padding:0">${c.tools.map((tl) =>
      `<li style="margin:7px 0">${tl.glyph} <b>${tl.name}</b><br>
       <span style="color:var(--muted);font-size:12.5px">${tl.use}</span></li>`).join('')}</ul>
    <p><button class="barbtn" id="drillGo">▶ ${D.tools.drill.name}</button></p>
    <p style="color:var(--muted);font-size:12px">${D.tools.honesty} ${t('progress.local')}</p>`;
  document.body.classList.add('open');
}
function drillStart() {
  drill = { i: 0, right: 0, t0: performance.now() };
  drillQ();
}
function drillQ() {
  const tasks = D.tools.drills[curCrib];
  if (drill.i >= tasks.length) return drillEnd();
  const c = D.tools.cribs[curCrib], task = tasks[drill.i];
  const ti = c.tools.findIndex((x) => x.id === task.tool);
  // options by index arithmetic - the registry's own contract, no chance
  const picks = [0, 3, 6, 9].map((o) => c.tools[(ti + o) % c.tools.length]);
  const rot = drill.i % 4;
  const order = picks.map((_, j) => picks[(j + rot) % 4]);
  document.getElementById('pbody').innerHTML = `
    <h2>${c.name}</h2>
    <span class="chip">${D.tools.drill.name} ${drill.i + 1}/${tasks.length}</span>
    <div class="q"><p>${task.ask}.</p>
    ${order.map((x) => `<button class="opt" data-drill="1" data-ok="${x.id === task.tool ? 1 : 0}">${x.glyph} ${x.name}</button>`).join('')}</div>`;
}
function drillEnd() {
  const tasks = D.tools.drills[curCrib];
  const secs = (performance.now() - drill.t0) / 1000;
  const passed = drill.right === tasks.length;
  const rec = prog.tools[curCrib] ?? {};
  rec.runs = (rec.runs ?? 0) + 1;
  if (passed) { rec.passed = true; rec.best = Math.min(rec.best ?? Infinity, secs); }
  prog.tools[curCrib] = rec; saveProg(); renderChrome();
  if (view === 'hall') document.getElementById('hname').textContent =
    D.halls.find((x) => x.slug === slug).name + scoreChip();
  chime(passed); buzz(passed ? 160 : 80, .5);
  document.getElementById('pbody').innerHTML = `
    <h2>${D.tools.cribs[curCrib].name}</h2>
    <span class="chip" style="${passed ? 'border-color:var(--good);color:var(--good)' : 'border-color:var(--crit);color:var(--crit)'}">
      ${passed ? t('sim.pass') : t('sim.retry')}</span>
    <h3>${t('sim.results')}</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13.5px"><tbody>
      <tr><td>picks</td><td style="text-align:end;font-family:'IBM Plex Mono',monospace">${drill.right}/${tasks.length}</td>
        <td style="text-align:end">${passed ? '✓' : '✗'}</td></tr>
      <tr><td>time</td><td style="text-align:end;font-family:'IBM Plex Mono',monospace">${secs.toFixed(1)} s</td><td></td></tr>
    </tbody></table>
    ${rec.passed && isFinite(rec.best) ? `<p style="color:var(--muted);font-size:12.5px">✓ ${rec.runs}× · best ${rec.best.toFixed(1)} s</p>` : ''}
    <p style="color:var(--muted);font-size:12px;margin-top:12px">${D.tools.honesty} ${t('progress.local')}</p>
    <p><button class="barbtn" id="drillRetry">↻ ${t('sim.retry')}</button>
       <button class="barbtn" id="drillExit">${t('ui.close')}</button></p>
    <style>#pbody td{border-top:1px solid var(--rule);padding:6px 8px;color:var(--muted)}</style>`;
  drill = null;
}

const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
renderer.domElement.addEventListener('pointerdown', (e) => {
  if (renderer.xr.isPresenting) return;     // the left-hand ray picks in-session
  if (walkActive) ptr.set(0, 0);
  else ptr.set(e.clientX/innerWidth*2-1, -(e.clientY/innerHeight)*2+1);
  ray.setFromCamera(ptr, camera);
  pickWith(ray);
});
// one dispatch for whatever a ray hits - the pointer's ray on a desktop,
// the left controller's ray in a headset - so in-session picking opens
// exactly what a click would
function pickWith(ray) {
  if (view === 'region') {
    const phit = ray.intersectObjects(plates, false)[0];
    if (phit?.object.userData.campus) showCampus(phit.object.userData.campus);
    else if (phit?.object.userData.candidate) openCandidate(phit.object.userData.candidate);
    return;
  }
  if (view === 'campus') {
    const phit = ray.intersectObjects(chapterHit, false)[0];
    if (phit?.object.userData.chapters) {
      if (walkActive) plc.unlock();
      return openChapters();
    }
    const chit = ray.intersectObjects(cityHits, false)[0];
    if (chit?.object.userData.poi) {
      if (walkActive) plc.unlock();
      return openCityPoi(chit.object.userData.poi);
    }
    const rhit = ray.intersectObjects(restorationHits, false)[0];
    if (rhit?.object.userData.restorationSite) {
      if (walkActive) plc.unlock();
      return openRestoration(null, rhit.object.userData.restorationSite);
    }
    const bhit = ray.intersectObjects(buildings, false)[0];
    if (bhit?.object.userData.slug) showHall(bhit.object.userData.slug);
    return;
  }
  if (view === 'sim' && waBeacons.length) {
    const wh = ray.intersectObjects(waBeacons, false)[0];
    if (wh?.object.userData.wapt !== undefined)
      return openWa(wh.object.userData.wapt);
  }
  const ahit = ray.intersectObjects(advisorMeshes, true)[0];
  if (ahit) {
    let o = ahit.object;
    while (o && !o.userData.advisor) o = o.parent;
    if (o) {
      if (walkActive && plc.isLocked) plc.unlock();
      return openAdvisor(o.userData.advisor);
    }
  }
  const hit = ray.intersectObjects(beacons, false)[0];
  if (hit?.object.userData.station) {
    if (walkActive) plc.unlock();
    return openStation(hit.object.userData.station);
  }
  if (hit?.object.userData.crib) {
    if (walkActive) plc.unlock();
    return openCrib(hit.object.userData.crib);
  }
  if (walkActive) return;
  const fhit = ray.intersectObjects(floors, false)[0];
  if (fhit?.object.userData.room) openRoom(fhit.object.userData.room);
}
let hoverPending = false;
renderer.domElement.addEventListener('pointermove', (e) => {
  if (view === 'hall' || hoverPending) return;
  hoverPending = true;
  requestAnimationFrame(() => {
    hoverPending = false;
    ptr.set(e.clientX/innerWidth*2-1, -(e.clientY/innerHeight)*2+1);
    ray.setFromCamera(ptr, camera);
    if (view === 'campus') {
      const chit = ray.intersectObjects(cityHits, false)[0];
      if (chit?.object.userData.poi) {
        const p = D.geo.cityPois[campusKey].find((x) => x.name === chit.object.userData.poi);
        document.getElementById('hname').textContent = p.name;
        document.getElementById('hfocus').textContent =
          p.km + ' km · ' + p.prov + ' — ' + (p.blurb || '');
        renderer.domElement.style.cursor = 'pointer';
        return;
      }
      const rhit = ray.intersectObjects(restorationHits, false)[0];
      if (rhit?.object.userData.restorationSite) {
        const s = D.restoration.sites.find((x) => x.id === rhit.object.userData.restorationSite);
        document.getElementById('hname').textContent = s.name;
        document.getElementById('hfocus').textContent =
          'Bay Restoration · AUTHORED — ' + s.habitat + ', ' + s.org;
        renderer.domElement.style.cursor = 'pointer';
        return;
      }
      const bhit = ray.intersectObjects(buildings, false)[0];
      if (bhit?.object.userData.slug) {
        const h = D.halls.find(x => x.slug === bhit.object.userData.slug);
        document.getElementById('hname').textContent = h.name;
        document.getElementById('hfocus').textContent = h.focus;
        renderer.domElement.style.cursor = 'pointer';
      } else renderer.domElement.style.cursor = '';
    } else {
      const phit = ray.intersectObjects(plates, false)[0];
      if (phit?.object.userData.campus) {
        const c = D.campuses[phit.object.userData.campus];
        document.getElementById('hname').textContent = c.name;
        document.getElementById('hfocus').textContent =
          c.city + ', ' + c.region + ' — ' + c.tagline;
        renderer.domElement.style.cursor = 'pointer';
      } else if (phit?.object.userData.candidate) {
        const c = D.roadmap.candidates[phit.object.userData.candidate];
        document.getElementById('hname').textContent = c.name + ' (proposed)';
        document.getElementById('hfocus').textContent =
          c.city + ', ' + c.region + ' — ' + c.km_from_flagship + ' km away';
        renderer.domElement.style.cursor = 'pointer';
      } else renderer.domElement.style.cursor = '';
    }
  });
});
document.addEventListener('click', (e) => {
  if (e.target.closest('#pclose') || e.target.id === 'ov')
    document.body.classList.remove('open');
  const ss = e.target.closest('[data-sim-start]');
  if (ss) {
    document.body.classList.remove('open');
    startSim(ss.dataset.simStart); return;
  }
  const hg = e.target.closest('[data-hall-goto]');
  if (hg) {
    document.body.classList.remove('open');
    showHall(hg.dataset.hallGoto); return;
  }
  const sh = e.target.closest('[data-schools-hall]');
  if (sh) { openSchools(sh.dataset.schoolsHall); return; }
  const rh = e.target.closest('[data-restoration-hall]');
  if (rh) { openRestoration(rh.dataset.restorationHall); return; }
  const rw = e.target.closest('[data-resto-walk]');
  if (rw) {
    document.body.classList.remove('open');
    startRestorationWalk(rw.dataset.restoWalk); return;
  }
  const rt = e.target.closest('[data-resto-track]');
  if (rt) { openRestoTrack(rt.dataset.restoTrack); return; }
  const eg = e.target.closest('[data-elev-go]');
  if (eg) {
    const s = D.restoration.sites.find((x) => x.id === eg.dataset.elevGo);
    if (s) siteElevation(s.id, s.lat, s.lng);
    return;
  }
  const sg = e.target.closest('[data-sat-go]');
  if (sg) {
    const s = D.restoration.sites.find((x) => x.id === sg.dataset.satGo);
    if (s) siteAerial(s.id, s.lat, s.lng);
    return;
  }
  if (e.target.id === 'simRetry') {
    document.body.classList.remove('open');
    // the same seat in the same yard, back in the learner's own hands
    const id = curSimId, sc = curScenario?.id;
    teardownSim(); view = 'hall'; startSim(id, sc); return;
  }
  if (e.target.id === 'simExit') {
    document.body.classList.remove('open'); exitSim(); return;
  }
  if (e.target.id === 'cardBtn') return drawCard();
  /* portable saves: the record as JSON, exported and imported by the
     learner alone - it never leaves the device unless they carry it */
  if (e.target.id === 'expBtn') {
    saveProg();
    const j = JSON.stringify(prog);
    document.getElementById('saveBox').innerHTML =
      `<textarea id="saveTa" readonly style="width:100%;height:90px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);border-radius:7px;font:11px 'IBM Plex Mono',monospace;padding:7px"></textarea>
       <p style="color:var(--muted);font-size:11.5px;margin:4px 0 0">${t('progress.local')}</p>`;
    const ta = document.getElementById('saveTa');
    ta.value = j; ta.select();
    try { navigator.clipboard?.writeText(j)?.catch(() => {}); } catch (err) { /* manual copy */ }
    return;
  }
  if (e.target.id === 'impBtn') {
    document.getElementById('saveBox').innerHTML =
      `<textarea id="saveTa" style="width:100%;height:90px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);border-radius:7px;font:11px 'IBM Plex Mono',monospace;padding:7px"></textarea>
       <p><button class="barbtn" id="impGo">⇲ ✓</button>
       <span id="impMsg" style="color:var(--muted);font-size:12px"></span></p>`;
    return;
  }
  if (e.target.id === 'impGo') {
    try {
      const p = JSON.parse(document.getElementById('saveTa').value);
      if (typeof p !== 'object' || p === null || Array.isArray(p))
        throw new Error('not a record');
      localStorage.setItem(PROG_KEY, JSON.stringify(p));
      location.reload();
    } catch (err) {
      document.getElementById('impMsg').textContent = '✗ ' + (err?.message ?? err);
    }
    return;
  }
  if (e.target.id === 'trExpBtn') {
    const j = exportTraining();
    document.getElementById('trBox').innerHTML =
      `<textarea id="trTa" readonly style="width:100%;height:90px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);border-radius:7px;font:11px 'IBM Plex Mono',monospace;padding:7px"></textarea>`;
    const ta = document.getElementById('trTa');
    ta.value = j; ta.select();
    try { navigator.clipboard?.writeText(j)?.catch(() => {}); } catch (err) { /* manual copy */ }
    return;
  }
  if (e.target.id === 'trClearBtn') {
    clearTraining();
    openRecords();
    return;
  }
  if (e.target.id === 'orbisExpBtn') {
    const txt = exportOrbisPrompts();
    document.getElementById('orbisBox').innerHTML =
      `<textarea id="orbisAllTa" readonly style="width:100%;height:140px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);border-radius:7px;font:11px 'IBM Plex Mono',monospace;padding:7px"></textarea>`;
    const ta = document.getElementById('orbisAllTa');
    ta.value = txt; ta.select();
    try { navigator.clipboard?.writeText(txt)?.catch(() => {}); } catch (err) { /* manual copy */ }
    return;
  }
  const wa = e.target.closest('[data-wa]');
  if (wa && sim) {
    const i = +wa.dataset.wa;
    waDone.add(i);
    recordEpisode({ kind: 'walkaround', campus: campusKey, hall: slug,
      sim: curSimId, point: D.sims.sims[curSimId].walkaround[i].id });
    waBeacons[i].material = mat.steel;
    blip(900, 1300, .1, 'triangle', .1);
    if (waDone.size === waTotal) {
      chime(true);
      prog.walk[curSimId] = (prog.walk[curSimId] ?? 0) + 1;
      saveProg();
    }
    openWa(i);
    return;
  }
  const cb = e.target.closest('[data-crib]');
  if (cb) return openCrib(cb.dataset.crib);
  if (e.target.id === 'drillGo' || e.target.id === 'drillRetry')
    return drillStart();
  if (e.target.id === 'drillExit') {
    document.body.classList.remove('open'); return;
  }
  const dp = e.target.closest('.opt[data-drill]');
  if (dp && drill) {
    dp.parentElement.querySelectorAll('.opt').forEach((o) => {
      o.classList.toggle('ok', o.dataset.ok === '1'); o.disabled = true; });
    if (dp.dataset.ok === '1') drill.right++;
    else dp.classList.add('bad');
    drill.i++;
    setTimeout(drillQ, 500);
    return;
  }
  const opt = e.target.closest('.opt');
  if (opt) { opt.parentElement.querySelectorAll('.opt').forEach(o =>
      o.classList.toggle('ok', o.dataset.ok === '1'));
    if (opt.dataset.ok !== '1') opt.classList.add('bad');
    else if (curStation) { doneStations.add(curStation); saveProg();
      const el = document.getElementById('hname');
      const h = D.halls.find(x => x.slug === slug);
      if (view === 'hall') el.textContent = h.name + scoreChip(); } }
});
document.getElementById('hall').addEventListener('change', (e) => {
  showHall(e.target.value);
});
// the weather cycle: every state the world registry declares, in its own
// declared order, each one a set of multipliers on this campus's own
// atmosphere rather than a separate look
function setWeather(id) {
  if (!WX[id]) return;
  wx = id;
  const nxt = WX_CYCLE[(WX_CYCLE.indexOf(wx) + 1) % WX_CYCLE.length];
  const b = document.getElementById('dnBtn');
  b.textContent = WX[nxt].glyph;
  b.title = WX[wx].name + ' \u2014 ' + WX[wx].blurb
    + '. Next: ' + WX[nxt].name;
  b.setAttribute('aria-label', 'weather: ' + WX[wx].name
    + '; next ' + WX[nxt].name);
  reAtmos();
}
document.getElementById('dnBtn').addEventListener('click', () => {
  setWeather(WX_CYCLE[(WX_CYCLE.indexOf(wx) + 1) % WX_CYCLE.length]);
});
setWeather(WX[params.get('wx')] ? params.get('wx') : 'clear');
// the records panel: every seat and drill from the device-local record
function openRecords() {
  const td = "style=\\"text-align:end\\"";
  const mono = "style=\\"text-align:end;font-family:'IBM Plex Mono',monospace\\"";
  const row = (name, r) => `<tr><td>${name}</td>
    <td ${td}>${r?.runs ?? 0}</td>
    <td ${td}>${r?.passed ? '✓' : '·'}</td>
    <td ${mono}>${isFinite(r?.best) ? r.best.toFixed(1) + ' s' : '\\u2013'}</td></tr>`;
  const head = `<tr><th></th><th ${td}>\\u00d7</th><th ${td}>✓</th><th ${td}>best</th></tr>`;
  document.getElementById('pbody').innerHTML = `
    <h2>⏱ ${t('sim.results')}</h2>
    <span class="chip">✓ ${doneStations.size}/${Object.keys(D.stations).length}</span>
    <span class="chip">▶ ${Object.values(prog.sims).filter((r) => r.passed).length}/${Object.keys(D.sims.sims).length}</span>
    <span class="chip">\U0001f9f0 ${Object.values(prog.tools).filter((r) => r.passed).length}/${Object.keys(D.tools.cribs).length}</span>
    <span class="chip">📋 ${Object.values(prog.walk).reduce((a, b) => a + b, 0)}</span>
    <h3>${t('sim.start')}</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px"><tbody>
      ${head}${Object.entries(D.sims.sims).map(([id, def]) => row(def.name, prog.sims[id])).join('')}
    </tbody></table>
    <h3>${D.tools.drill.name}</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px"><tbody>
      ${head}${Object.entries(D.tools.cribs).map(([dk, c]) => row(c.name, prog.tools[dk])).join('')}
    </tbody></table>
    <p><button class="barbtn" id="cardBtn">🪪 ${t('sim.results')}</button>
       <button class="barbtn" id="expBtn">⇪ JSON</button>
       <button class="barbtn" id="impBtn">⇲ JSON</button></p>
    <div id="saveBox"></div>
    <div id="cardBox"></div>
    <h3>🤖 Training-data episodes</h3>
    <span class="chip">${trainingLog.length} / ${D.training.storage.cap} kept</span>
    <p style="margin:6px 0">
      <label style="display:inline-flex;align-items:center;gap:6px;cursor:pointer">
        <input type="checkbox" id="trOn" ${trainingOn ? 'checked' : ''}>
        <span style="font-size:12.5px;color:var(--muted)">record episodes as I train</span>
      </label></p>
    <p style="margin:6px 0">
      <label style="display:inline-flex;align-items:center;gap:6px;cursor:pointer">
        <input type="checkbox" id="traceOn" ${traceOn ? 'checked' : ''}>
        <span style="font-size:12.5px;color:var(--muted)">also capture a per-second gauge trace during sim runs (off by default, heavier)</span>
      </label></p>
    <p><button class="barbtn" id="trExpBtn">⇪ export</button>
       <button class="barbtn" id="trClearBtn">🗑 clear</button></p>
    <div id="trBox"></div>
    <p style="margin:10px 0 6px">
      <button class="barbtn" id="trSweepBtn">🤖 generate scripted episodes</button>
      <select id="trSweepLvl" aria-label="operator level" style="max-width:none">
        ${Object.keys(D.sims.operatorLevels).map((l) => `<option value="${l}">${l}</option>`).join('')}
      </select></p>
    <p style="color:var(--muted);font-size:12px;margin:0 0 6px">every seat \\u00d7 every regional scenario, driven headlessly at a fixed step by the scripted reference operator at that level - kept as SCRIPTED episodes through the same recorder, under the same toggle and cap; a human episode is never touched</p>
    <div id="trSweepBox"></div>
    <p style="color:var(--muted);font-size:12px">${D.sims.operatorHonesty}</p>
    <p style="color:var(--muted);font-size:12px">${D.training.honesty.schematic}</p>
    <p style="color:var(--muted);font-size:12px">${D.training.honesty.not_scored}</p>
    <p style="color:var(--muted);font-size:12px">${D.training.honesty.orbis_pairing}
       <button class="barbtn" id="trOrbisBtn" style="font-size:11px;padding:2px 8px">\U0001f3ac open Orbis</button></p>
    <p style="color:var(--muted);font-size:12px;margin-top:12px">${t('progress.local')} ${D.sims.honesty}</p>
    <style>#pbody td,#pbody th{border-top:1px solid var(--rule);padding:5px 8px;color:var(--muted);font-weight:400}</style>`;
  document.body.classList.add('open');
  document.getElementById('trOn')?.addEventListener('change', (e) => trainingToggle(e.target.checked));
  document.getElementById('traceOn')?.addEventListener('change', (e) => traceToggle(e.target.checked));
  document.getElementById('trOrbisBtn')?.addEventListener('click', openOrbis);
  document.getElementById('trSweepBtn')?.addEventListener('click', async (e) => {
    const btn = e.target, box = document.getElementById('trSweepBox');
    const level = document.getElementById('trSweepLvl').value;
    btn.disabled = true; btn.textContent = '\\u2026 running';
    try {
      const out = await window.__tc3dSim.sweep({ levels: [level] });
      const n = out.rows.length, np = out.rows.filter((r) => r.passed).length;
      const cell = (r) => Object.entries(r.axes ?? {}).map(([a, v]) =>
        `${a} ${v}${r.ok?.[a] === undefined ? '' : r.ok[a] ? ' \\u2713' : ' \\u2717'}`).join(' \\u00b7 ');
      box.innerHTML = `<p style="font-size:12.5px">${np}/${n} passed at <b>${level}</b> \\u00b7 `
        + (out.recorded ? `${n} SCRIPTED episodes kept (${trainingLog.length} / ${D.training.storage.cap})`
          : 'recorder is off \\u2014 the runs happened, nothing was kept') + `</p>
        <table style="width:100%;border-collapse:collapse;font-size:12px"><tbody>
        ${out.rows.map((r) => `<tr><td>${D.sims.sims[r.sim].name}</td><td>${r.scenario}</td>
          <td>${r.timedOut ? 'timed out' : r.passed ? '\\u2713' : '\\u2717'}</td>
          <td style="color:var(--muted)">${cell(r)}</td></tr>`).join('')}
        </tbody></table>`;
      document.querySelector('#pbody .chip').textContent = `${trainingLog.length} / ${D.training.storage.cap} kept`;
    } finally { btn.disabled = false; btn.textContent = '\U0001f916 generate scripted episodes'; }
  });
}
/* The progress card: the record drawn as one image the learner can save
   (long-press / right-click - the page never uploads it anywhere). */
function drawCard() {
  const c = document.createElement('canvas');
  c.width = 640; c.height = 460; c.id = 'pcard';
  c.style.cssText = 'width:100%;border:1px solid var(--rule);border-radius:10px;margin-top:8px';
  const g2 = c.getContext('2d');
  g2.fillStyle = '#12181B'; g2.fillRect(0, 0, 640, 460);
  g2.fillStyle = '#E8A33D'; g2.fillRect(0, 0, 640, 5);
  g2.fillStyle = '#E8EDEC'; g2.font = '700 30px "Barlow Condensed", sans-serif';
  g2.fillText('SmartCiti.X : Trade Craft Academy', 28, 48);
  g2.fillStyle = '#93A3A6'; g2.font = '15px "IBM Plex Sans", sans-serif';
  g2.fillText('Training record · ' + new Date().toISOString().slice(0, 10), 28, 74);
  const chips = [
    ['✓', doneStations.size + '/' + Object.keys(D.stations).length + ' stations'],
    ['▶', Object.values(prog.sims).filter((r) => r.passed).length + '/'
      + Object.keys(D.sims.sims).length + ' seats'],
    ['\U0001f9f0', Object.values(prog.tools).filter((r) => r.passed).length + '/'
      + Object.keys(D.tools.cribs).length + ' cribs'],
    ['📋', Object.values(prog.walk).reduce((a, b) => a + b, 0) + ' walkarounds'],
  ];
  chips.forEach(([ic, txt], i) => {
    const x = 28 + i * 150;
    g2.strokeStyle = '#28353A'; g2.lineWidth = 1.5;
    g2.beginPath(); g2.roundRect(x, 92, 140, 34, 17); g2.stroke();
    g2.fillStyle = '#E8EDEC'; g2.font = '14px "IBM Plex Sans", sans-serif';
    g2.fillText(ic + ' ' + txt, x + 12, 114);
  });
  g2.font = '15px "IBM Plex Mono", monospace';
  Object.entries(D.sims.sims).forEach(([id, def], i) => {
    const y = 168 + i * 32, r = prog.sims[id];
    g2.fillStyle = '#93A3A6'; g2.fillText(def.name, 28, y);
    g2.fillStyle = r?.passed ? '#5CB584' : '#41505a';
    g2.fillText(r?.passed ? '✓' : '·', 420, y);
    g2.fillStyle = '#E8EDEC';
    g2.fillText(isFinite(r?.best) ? r.best.toFixed(1) + ' s' : '\\u2013', 470, y);
  });
  g2.fillStyle = '#68787c'; g2.font = '12px "IBM Plex Sans", sans-serif';
  g2.fillText('Device-local record · cosmetic only · not equipment certification', 28, 436);
  const bx = document.getElementById('cardBox');
  bx.innerHTML = '<p style="color:var(--muted);font-size:11.5px;margin:8px 0 0">'
    + t('progress.local') + '</p>';
  bx.prepend(c);
}
document.getElementById('recBtn').addEventListener('click', () => {
  if (walkActive) plc.unlock();
  openRecords();
});
document.getElementById('orbisBtn').addEventListener('click', () => {
  if (walkActive) plc.unlock();
  openOrbis();
});
document.getElementById('schoolsBtn').addEventListener('click', () => {
  if (walkActive) plc.unlock();
  openSchools();
});
document.getElementById('restorationBtn').addEventListener('click', () => {
  if (walkActive) plc.unlock();
  openRestoration();
});
document.getElementById('regionBtn').addEventListener('click', showRegion);
document.getElementById('campusBtn').addEventListener('click',
  () => showCampus(campusKey));
document.getElementById('walkBtn').addEventListener('click', enterWalk);
document.getElementById('simBtn').addEventListener('click', () => {
  const b = D.sims.bindings[slug];
  if (!b?.length) return;
  if (b.length === 1) return startSim(b[0].sim);
  // more than one machine trains here: the learner picks the seat
  document.getElementById('pbody').innerHTML = `<h2>${t('sim.choose')}</h2>`
    + b.map((x) => {
      const d = D.sims.sims[x.sim];
      const done = prog.sims[x.sim]?.passed ? ' ✓' : '';
      return `<p><button class="barbtn" data-sim-start="${x.sim}">▶ ${d.name}${done}</button><br>
        <span style="color:var(--muted);font-size:12.5px">${d.task}</span></p>`;
    }).join('');
  document.body.classList.add('open');
});
document.getElementById('lang').addEventListener('change', (e) => {
  loc = e.target.value; renderChrome();
  if (view === 'avatar') showAvatar();
  else if (view === 'region') showRegion();
  else if (view === 'campus') showCampus(campusKey);
  else showHall(slug);
});
function syncURL() {
  history.replaceState(null, '', view === 'region' ? `?lang=${loc}`
    : view === 'campus' ? `?campus=${campusKey}&lang=${loc}`
    : `?hall=${slug}&lang=${loc}`);
}
addEventListener('resize', () => {
  camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

cfgInit();
renderChrome();
if (D.halls.some(h => h.slug === params.get('hall'))) showHall(params.get('hall'));
else if (D.campuses[params.get('campus')]) showCampus(params.get('campus'));
else showRegion();
// test hooks: state for assertions, and the two panel openers the toolroom
// harness drives (module scope hides them from the page's own globals)
window.__tc3dDo = (fn, arg) => {
  if (fn === 'room') openRoom(arg ?? D.halls.find((x) => x.slug === slug)
    .rooms.find((r) => r.strand === 'tools').label);
  else if (fn === 'crib') openCrib(arg);
  else if (fn === 'wa') openWa(arg);
  else if (fn === 'quality') { qAuto = false; setQuality(arg); }
  else if (fn === 'emote') playEmote(arg);
  else if (fn === 'advisor') openAdvisor(...String(arg).split(':'));
  else if (fn === 'wx') setWeather(arg);
  // place the camera: "eyeX,eyeY,eyeZ|atX,atY,atZ" - used by the harnesses
  // and, later, by anything that wants to drive the view
  else if (fn === 'cam') {
    const [eye, at] = String(arg).split('|').map((v) => v.split(',').map(Number));
    camera.position.set(...eye);
    if (at) { controls.target.set(...at); camera.lookAt(...at); }
    controls.autoRotate = false; controls.update();
  }
  // test hooks: stand the walker beside an advisor, or well away from one
  else if (fn === 'walkTo' || fn === 'walkAway') {
    const m = advisorMeshes.find((x) => x.userData.advisor === arg);
    if (m && walkAvatar) {
      const v = m.getWorldPosition(new THREE.Vector3());
      const off = fn === 'walkTo' ? 1.4 : 40;
      walkAvatar.position.set(v.x + off, walkAvatar.position.y, v.z + off);
    }
  }
};
// the scripted reference operator's driver surface: what a test harness or
// a robotics pipeline sharing this page context can drive. In-page and
// deterministic - no network, no model - see OPERATORS in the sim layer
// harness only: light N of the room lights and douse the rest, so the cost
// of the room-light count can be measured rather than guessed at
window.__tc3dSetLit = (n) => {
  roomLights.forEach((l, i) => { l.visible = i < n; });
};
window.__tc3dSim = {
  keys,
  levels: () => Object.keys(D.sims.operatorLevels),
  operators: () => Object.keys(OPERATORS),
  action() { sim?.action?.(); },
  gauges() { return sim?.gauges ? sim.gauges() : null; },
  // start a seat in a named yard; with a level, the operator drives it at
  // real time in the frame loop (what the HUD's watch button does)
  start(simId, scenarioId, opts = {}) {
    const def = D.sims.sims[simId];
    if (!def) throw new Error('no such seat: ' + simId);
    if (!def.halls.includes(slug)) showHall(def.halls[0]);
    startSim(simId, scenarioId);
    if (opts.level) opAttach(opts.level, opts.seed ?? 1, false);
    return { sim: simId, scenario: curScenario?.id ?? null, level: opts.level ?? null };
  },
  stop() { if (sim) exitSim(); },
  // one headless run to completion at a fixed step; returns its outcome,
  // and hands the launching view back exactly as the sweep does
  run(simId, scenarioId, o = {}) {
    const before = opViewMark();
    try {
      return opRunHeadless(simId, scenarioId, o.level ?? 'optimal', o.seed ?? 1,
        o.dt ?? 1 / 60, o.maxSec ?? 400, o.every ?? 0);
    } finally { opViewRestore(before); }
  },
  sweep: opSweep,
  state: () => opRun ? { sim: opRun.sim, scenario: opRun.scenario, level: opRun.level,
    seed: opRun.seed, step: opRun.step, phase: opRun.id, sweep: opRun.sweep,
    result: opRun.result } : null,
};
window.__tc3d = () => ({ view, buildings: buildings.length, plates: plates.length,
  beacons: beacons.length, floors: floors.length, slug, campusKey, loc, walkActive,
  sim: curSimId && sim ? curSimId : null, roadFaults, roadCount,
  anchors: anchorPins, simCam: simView, audio: !!ac, city: cityPois,
  restoSites: restorationHits.length / 2,
  scenario: curScenario?.id ?? null,
  chHosted: D.chapters.hosted[campusKey] ?? null,
  isTouch, shadows: renderer.shadowMap.enabled,
  // orbit is the fallback control scheme, so whether it is enabled is the
  // fact that says the view is still steerable. enterWalk() disables it
  // before it asks for the pointer lock; a refused lock used to leave it
  // disabled with nothing able to turn it back on, and a frame-difference
  // check cannot see that, because this scene animates every frame anyway.
  orbit: controls.enabled, walkRefusedAt,
  // the campus training yard: how many seats stand on it, and which one the
  // walker is close enough to enter
  yardSeats: seatHits.length / 2, nearSeat,
  // the length of the list the quality ladder walks. It is a leak check:
  // every torn-down hall and sim yard must take its lights OUT of it, not
  // merely out of the scene, or a long session ends up walking hundreds of
  // dead lights every time the ladder steps
  litList: roomLights.length,
  // the walkable restoration site's own ground, read off the scene graph
  restoGround: restoGroup ? (() => { let v = null;
    restoGroup.traverse((o) => { if (o.userData?.restoGround) v = o.userData.restoGround; });
    return v; })() : null,
  // what the running seat's yard is actually floored and lit with, read off
  // the scene graph rather than off the registry it was built from
  yardSurface: sim ? (() => { let v = null;
    sim.group.traverse((o) => { if (o.userData?.yardSurface) v = o.userData.yardSurface; });
    return v; })() : null,
  yardLights: sim ? (() => { let n2 = 0;
    sim.group.traverse((o) => { if (o.isLight) n2++; }); return n2; })() : null,
  avatar: avatarCfg ? { ...avatarCfg } : null, emote: lastEmote,
  apeSpan: (avatarMesh ?? walkAvatar)?.userData?.apeSpanRatio ?? null,
  atmos: atmosKey, fogNear: Math.round(scene.fog.near),
  fogFar: Math.round(scene.fog.far), camFar: camera.far,
  banks: fogBanks.length, mmN: mmInfo.n,
  mmVis: document.getElementById('mm').style.display !== 'none',
  simRider: !!simRider, ambN: ambNodes.length,
  cribs: cribCount, curCrib, drillN: drill ? drill.i : null,
  // the environment summary: what the hall actually BUILT, counted off the
  // scene graph rather than off the intent. A harness that only checked the
  // source would have passed on an emissive box that lit nothing, so the
  // numbers here are read from the objects themselves.
  env: hallGroup ? (() => {
    let mapped = 0, normals = 0, wainscot = 0, placards = 0;
    const lux = roomLights.map((l) => +l.intensity.toFixed(3));
    hallGroup.traverse((o) => {
      if (o.isSprite && o.userData.lbl?.kind === 'placard') placards++;
      if (o.userData?.wainscot) wainscot++;
      const m = o.material;
      if (!m || m.isSpriteMaterial) return;
      if (m.map) mapped++;
      if (m.normalMap) normals++;
    });
    return { roomLights: roomLights.length, lit: roomLights.filter((l) => l.visible).length,
             luxI: { min: Math.min(...lux), max: Math.max(...lux) },
             mapped, normals, wainscot, placards,
             surfTex: surfCache.size };
  })() : null,
  gau: sim?.gauges ? sim.gauges() : null,
  rollup: view === 'campus' ? campusRollup(campusKey) : null,
  mmDone: mmInfo.done ?? 0, night, wx, rain: rain.visible,
  wa: waTotal ? { done: waDone.size, total: waTotal } : null,
  xr: { vr: document.getElementById('vrBtn').style.display !== 'none',
        ar: document.getElementById('arBtn').style.display !== 'none',
        mode: xrMode, presenting: renderer.xr.isPresenting, walk: xrWalk,
        note: xrProbeNote },
  meta: { exp: lastExport,
    imp: importedGlb ? { nodes: importedGlb.nodes, name: importedGlb.name } : null },
  quality: qLevel, px: renderer.getPixelRatio(),
  advisors: { here: advisorMeshes.map((m) => m.userData.advisor),
              near: nearAdvisor, open: curAdvisor, topic: curTopic },
  training: { on: trainingOn, count: trainingLog.length,
    trace: { on: traceOn, ticks: simTicks.length },
              kinds: trainingLog.map((e) => e.kind),
              actors: trainingLog.map((e) => e.actor ?? null),
              last: trainingLog[trainingLog.length - 1] ?? null },
  operator: window.__tc3dSim.state(),
  orbis: { model: D.orbis.model, prompt: orbisPrompt(slug) },
  labels: { live: labelSet.filter((x) => x.parent).length,
            kinds: [...new Set(labelSet.filter((x) => x.parent)
              .map((x) => x.userData.lbl.kind))].sort(),
            shown: labelSet.filter((x) => x.parent && x.visible).length,
            focus: labelFocus ? { kind: labelFocus.userData.lbl.kind,
              at: labelFocus.getWorldPosition(new THREE.Vector3())
                .toArray().map((v) => Math.round(v)) } : null,
            lit: labelSet.filter((x) => x.parent)
              .map((x) => Math.round(x.userData.lbl.focus * 100)),
            // what the eye actually gets: each visible sign's height as a
            // fraction of the viewport, and its opacity - the two numbers
            // the design makes a promise about
            frac: (() => {
              const tan = Math.tan(camera.fov * Math.PI / 360);
              const v = new THREE.Vector3();
              return labelSet.filter((x) => x.parent && x.visible).map((x) => {
                const d = x.getWorldPosition(v).distanceTo(eyePos());
                return Math.round(x.scale.y / (2 * d * tan) * 1000) / 1000;
              }).filter((r) => isFinite(r) && r > 0);
            })(),
            op: labelSet.filter((x) => x.parent && x.visible)
              .map((x) => Math.round(x.material.opacity * 100)),
            band: LFOCUS.screen },
  world: { wx, cycle: WX_CYCLE, rain: rainRate,
           fauna: faunaBodies.map((b) => b.userData.kind),
           // rounded so a harness can watch them move without floating noise
           faunaAt: faunaBodies.map((b) => b.position.toArray()
             .map((v) => Math.round(v * 10) / 10).join(',')),
           faunaOut: !!(faunaGroup && faunaGroup.visible),
           ground: Object.keys(GROUND_RECIPES),
           maps: groundMapCache.size, genMs: Math.round(genMs) },
  rig: (() => {                       // the VRM skeleton, as it really is
    const av = avatarMesh ?? walkAvatar ?? simRider;
    if (!av?.userData?.bones) return null;
    av.updateMatrixWorld(true);
    const v = new THREE.Vector3(), out = {};
    for (const [n, b] of Object.entries(av.userData.bones))
      out[n] = Math.round(b.getWorldPosition(v).y * 100) / 100;
    return out;
  })(),
  rigTree: (() => {                   // and how those bones hang together
    const av = avatarMesh ?? walkAvatar ?? simRider;
    if (!av?.userData?.bones) return null;
    const out = {};
    av.traverse((o) => { if (o.name) out[o.name] = o.parent?.name ?? null; });
    return out;
  })(),
  pose: (() => {                      // the joints a gait actually drives
    const av = avatarMesh ?? walkAvatar ?? simRider;
    const b = av?.userData?.bones;
    if (!b) return null;
    const r = (x) => Math.round(x * 1000) / 1000;
    return { leg: r(b.leftUpperLeg.rotation.x), knee: r(b.leftLowerLeg.rotation.x),
      legR: r(b.rightUpperLeg.rotation.x), arm: r(b.rightUpperArm.rotation.x),
      elbow: r(b.rightLowerArm.rotation.x), hipY: r(b.hips.position.y),
      neckY: r(b.neck.rotation.y), headY: r(b.head.rotation.y),
      headX: r(b.head.rotation.x), dist: r(av.userData.dist ?? 0) };
  })(),
  sat: { state: satState, plane: !!satPlane,
         tiles: SAT_TILES ?? D.imagery.tiles, z: SAT_Z,
         span: satPlane ? [Math.round(satPlane.geometry.parameters.width),
                           Math.round(satPlane.geometry.parameters.height)] : null,
         at: satPlane ? satPlane.position.toArray()
                          .map((v) => Math.round(v * 10) / 10) : null },
  perf: { calls: renderer.info.render.calls,
    tris: renderer.info.render.triangles,
    geoms: renderer.info.memory.geometries,
    tex: renderer.info.memory.textures,
    cached: geoCache.size, lblTex: lblTexCache.size,
    labelSet: labelSet.length,
    campusBeacons: beaconInst ? beaconInst.count : 0,
    // Shader programs and live lights: the two costs a draw-call count
    // cannot see. A forward renderer compiles a program per material per
    // light-count, so adding lights to a scene makes every material in it
    // more expensive AND can force a recompile storm on the frame the
    // count changes - which is exactly what a hall full of room lights
    // does if nothing is watching.
    programs: renderer.info.programs?.length ?? 0,
    // Lights, counted two ways, because they are not the same number and
    // the difference is the whole point. `lightsInScene` is a census of the
    // graph, including the hall you left behind with its group hidden.
    // `lightsLit` is what the renderer will actually collect: three.js's
    // projectObject returns early on an invisible object, so a light under
    // a hidden group costs nothing. Reporting only the census would have
    // made a hidden hall look like a running cost it is not.
    lightsInScene: (() => { let n2 = 0; scene.traverse((o) => { if (o.isLight) n2++; }); return n2; })(),
    // what they are and where, when the two numbers disagree
    lightList: (() => {
      const out = [];
      const walk = (o, path) => { if (!o.visible) return;
        if (o.isLight) out.push(o.type + '@' + path);
        for (const c of o.children) walk(c, path + '/' + (o.name || o.type)); };
      walk(scene, ''); return out;
    })(),
    lightsLit: (() => {
      let n2 = 0;
      const walk = (o) => { if (!o.visible) return; if (o.isLight) n2++;
        for (const c of o.children) walk(c); };
      walk(scene); return n2;
    })(),
    surfTex: surfCache.size, groundTex: groundCache.size },
  wheel: document.querySelectorAll('#wheel path').length,
  progress: { stations: doneStations.size, sims: Object.keys(prog.sims).length,
    tools: Object.keys(prog.tools).length },
  dash: document.querySelectorAll('#dash .g').length,
  cam: eyePos().toArray().map((v) => Math.round(v * 10) / 10),
  rigAt: xrRig.position.toArray().map((v) => Math.round(v * 100) / 100),
  rigYaw: Math.round(xrRig.rotation.y * 1000) / 1000,
  probe: (() => { const r = new THREE.Raycaster();
    r.setFromCamera(new THREE.Vector2(-.4, .4), camera);
    const h = r.intersectObjects(scene.children, true)[0];
    return h ? [h.object.material?.color?.getHexString?.(),
      Math.round(h.distance * 10) / 10, h.object.geometry?.type] : null; })() });
__XR_JS__

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();
  // the controller adapter runs first: thumbsticks, trigger, grip and
  // buttons land in the same `keys` a keyboard fills (and the same
  // sim.action() a Space press calls), so nothing below can tell them apart
  if (renderer.xr.isPresenting) xrInput(dt);
  if (!reduced) {
    for (const b of beacons) if (b.userData.spin) b.rotation.y += dt * 1.4;
    if (view === 'campus') spinBeacons(dt);
  }
  // a seat the headless sweep is stepping at its own fixed dt is never
  // also stepped here; a seat the scripted operator drives at real time
  // gets its inputs from opStep() before the physics step, exactly where
  // a keypress would already be waiting in `keys`
  if (sim && !opHeadless) {
    if (opRun) opStep(dt);
    sim.update(dt);
    if (sim.gauges) {
      const gv = sim.gauges();
      setDash(D.sims.sims[curSimId], gv);
      setXRDash(D.sims.sims[curSimId], gv);
    }
    traceStep(dt);
  }
  stepEmote(dt);
  if (view === 'avatar' && !emo) idleBreath(avatarMesh, clock.elapsedTime, dt);
  if (!reduced) for (const b of fogBanks) {
    b.ang += dt * b.sp;
    b.m.position.x = Math.cos(b.ang) * b.rad;
    b.m.position.z = Math.sin(b.ang) * b.rad;
  }
  rainStep(dt); qStep(dt); xrQStep(dt);
  if (view === 'campus') mmDraw();
  if (renderer.xr.isPresenting) xrFrame(dt);
  if (walkActive) (isTouch && !xrWalk ? touchWalkStep : walkStep)(dt);
  // in a sim's operator view the sim owns the camera - the orbit controls
  // must not re-clamp it to their own distance limits. A presenting XR
  // session owns the camera even harder: the headset's own pose IS the
  // camera transform, and orbit controls updating on top of that is the
  // classic WebXR bug where the view fights itself every frame
  else if ((!sim || controls.enabled) && !renderer.xr.isPresenting)
    controls.update();
  advisorProximity(dt);
  faunaStep(clock.elapsedTime, dt);
  labelStep(dt);
  roomLitStep();
  xrRender();
});
</script>
</body>
</html>
'''

page = page.replace('__DATA__', DATA).replace('__PIPELINE_JS__', PIPELINE_JS)
page = page.replace('__SIM_JS__', SIM_JS).replace('__XR_JS__', XR_JS)
page = page.replace('__AVATAR_JS__', AVATAR_JS)
page = page.replace('__ADVISOR_JS__', ADVISOR_JS)
page = page.replace('__GROUND_TRUTH_JS__', GROUND_TRUTH_JS)
out = HERE / 'trade_craft_3d.html'
emit(out, page, f"{len(HALLS)} halls | {stations_reg['count']} stations | {len(I18N)} locales")
