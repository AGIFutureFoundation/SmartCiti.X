#!/usr/bin/env python3
"""smiles/build.py - the AUTHORED Unspoken Smiles district (SMILES, wave 12).

Reads smiles/authored/district.json (zones, clinic rooms, streets, van route, game settings, guidance lines),
smiles/authored/stations.json (the 37 clinic stations transcribed with provenance from AGIFutureFoundation/
vr-safety-training at a recorded commit) and quests/source/smiles.json (tooth-fairy style eggs, world smiles:<zone>).
Writes smiles/registry/smiles.json (sha256 source_stamp over this file + render.py + every input), and renders ONE
4k map image (smiles/maps/district-4k.webp) and ONE ground atlas (smiles/maps/atlas.webp) - no tile sets.

Fail closed: a missing field stops the build with a named error; there are no defaults on authored data.
Everything drawn is AUTHORED - not a real place, not surveyed.
Usage: python3 smiles/build.py [--check]   (--check: rebuild in memory and fail if the committed registry differs)
"""
import hashlib
import re
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import render  # noqa: E402

DISTRICT = HERE / 'authored/district.json'
STATIONS = HERE / 'authored/stations.json'
EGGS = ROOT / 'quests/source/smiles.json'
OUT = HERE / 'registry/smiles.json'
MAP = HERE / 'maps/district-4k.webp'
ATLAS = HERE / 'maps/atlas.webp'
REF_CLONE = pathlib.Path('/home/user/agifuturefoundation/vr-safety-training')
EXPECTED_STATIONS = 37
DOOR_M = 6.0          # AUTHORED doorway width (or a third of a narrow wall), centred in each south wall
WALLED = {'clinic': ('clinic-tile', 4.0), 'school': ('school-floor', 5.0), 'community': ('hall-floor', 5.0),
          'shop': ('shop-floor', 5.0), 'vanlot': ('lot', 5.0), 'library': ('wood', 5.0)}
ROOM_WALL_H = 2.2
GAMES = ('brushing', 'flossing', 'snacks', 'plaque', 'handwash', 'drinks')
DISCLAIMER = 'General guidance, not medical or dental advice.'


class SmilesError(Exception):
    pass


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise SmilesError(f'smiles: {where} has no {k!r}')
    return d[k]


def inside(inner, outer):
    x, y, w, h = inner
    X, Y, W, H = outer
    return x >= X and y >= Y and x + w <= X + W and y + h <= Y + H


def overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def on_seg(p, a, b):
    return (min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
            and (a[0] == b[0] == p[0] or a[1] == b[1] == p[1]))


def solids(z):
    """AUTHORED solid footprints inside a zone (houses, market stalls) - the page makes each a physkit box."""
    if z['kind'] == 'residential':
        return [[hx, hy, render.HOUSE[0], render.HOUSE[1]] for hx, hy in render.house_lots(z['rect'])]
    if z['kind'] == 'market':
        return [[sx, sy, render.STALL[0], render.STALL[1]] for sx, sy in render.market_stalls(z['rect'])]
    return []


def walls_for(d):
    """Wall segments (drawn AND solid on the page) with one south doorway per walled zone and clinic room, plus the
    district edge. Returns (walls, doors)."""
    walls, doors = [], []

    def outline(oid, r, h, mat):
        x, z, w, dd = r
        g = min(DOOR_M, w / 3)
        segs = [((x, z), (x + w, z)), ((x, z), (x, z + dd)), ((x + w, z), (x + w, z + dd)),
                ((x, z + dd), (x + w / 2 - g / 2, z + dd)), ((x + w / 2 + g / 2, z + dd), (x + w, z + dd))]
        for i, (a, b) in enumerate(segs):
            walls.append({'id': f'{oid}:{i}', 'from': [round(a[0], 3), round(a[1], 3)], 'to': [round(b[0], 3), round(b[1], 3)], 'h': h, 'mat': mat})
        doors.append({'id': oid, 'at': [round(x + w / 2, 3), z + dd], 'width_m': round(g, 3)})
    for zn in d['zones']:
        if zn['kind'] in WALLED:
            outline(zn['id'], zn['rect'], WALLED[zn['kind']][1], WALLED[zn['kind']][0])
    for r in d['rooms']:
        outline('room-' + r['id'], r['rect'], ROOM_WALL_H, 'room')
    W, H = d['size_m']
    for i, (a, b) in enumerate((((0, 0), (W, 0)), ((0, 0), (0, H)), ((W, 0), (W, H)), ((0, H), (W, H)))):
        walls.append({'id': f'edge:{i}', 'from': list(a), 'to': list(b), 'h': 3.0, 'mat': 'room'})
    return walls, doors


def near_solid(at, zone):
    return any(r[0] - 2 <= at[0] <= r[0] + r[2] + 2 and r[1] - 2 <= at[1] <= r[1] + r[3] + 2 for r in solids(zone))


def egg_spot(eid, zone):
    """A deterministic spot for an egg inside its zone (sha256 of id[:n] -> fractions in [0.2, 0.8]), the first
    candidate clear of the zone's solid footprints."""
    rect = zone['rect']
    for n in range(64):
        h = hashlib.sha256(f'{eid}:{n}'.encode() if n else eid.encode()).digest()
        at = [round(rect[0] + (0.2 + 0.6 * (h[0] / 255)) * rect[2], 1), round(rect[1] + (0.2 + 0.6 * (h[1] / 255)) * rect[3], 1)]
        if not near_solid(at, zone):
            return at
    raise SmilesError(f'smiles: no clear spot for egg {eid} in {zone["id"]}')


def load():
    d = json.loads(DISTRICT.read_text(encoding='utf-8'))
    s = json.loads(STATIONS.read_text(encoding='utf-8'))
    e = json.loads(EGGS.read_text(encoding='utf-8'))
    if need(d, 'provenance', 'district') != 'AUTHORED':
        raise SmilesError('smiles: the district must be labelled AUTHORED')
    if 'not a real place' not in need(d, 'place_note', 'district'):
        raise SmilesError('smiles: place_note must say the district is not a real place')
    size = need(d, 'size_m', 'district')
    whole = [0, 0, size[0], size[1]]
    zones = need(d, 'zones', 'district')
    zid = [need(z, 'id', 'zone') for z in zones]
    if len(set(zid)) != len(zid):
        raise SmilesError(f'smiles: duplicate zone ids {zid}')
    for z in zones:
        for k in ('name', 'kind', 'rect', 'colour'):
            need(z, k, f'zone {z["id"]}')
        if not inside(z['rect'], whole):
            raise SmilesError(f'smiles: zone {z["id"]} lies outside the district')
    for i, a in enumerate(zones):
        for b in zones[i + 1:]:
            if overlap(a['rect'], b['rect']):
                raise SmilesError(f'smiles: zones {a["id"]} and {b["id"]} overlap')
    for k in ('clinic', 'school', 'park', 'playground', 'community', 'shop', 'vanlot'):
        if k not in zid:
            raise SmilesError(f'smiles: the district has no {k} zone')
    clinic = next(z for z in zones if z['id'] == 'clinic')
    st = {need(x, 'id', 'station'): x for x in need(s, 'stations', 'stations.json')}
    if len(st) != EXPECTED_STATIONS:
        raise SmilesError(f'smiles: expected {EXPECTED_STATIONS} stations, found {len(st)}')
    url_base = need(s, 'url_base', 'stations.json')
    placed = {}
    rooms = need(d, 'rooms', 'district')
    for r in rooms:
        for k in ('id', 'name', 'rect', 'stations'):
            need(r, k, f'room {r.get("id")}')
        if not inside(r['rect'], clinic['rect']):
            raise SmilesError(f'smiles: room {r["id"]} lies outside the clinic')
        for sid in r['stations']:
            if sid not in st:
                raise SmilesError(f'smiles: room {r["id"]} names unknown station {sid!r}')
            if sid in placed:
                raise SmilesError(f'smiles: station {sid} is in rooms {placed[sid]} and {r["id"]}')
            placed[sid] = r['id']
    missing = sorted(set(st) - set(placed))
    if missing:
        raise SmilesError(f'smiles: stations in no room: {missing}')
    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            if overlap(a['rect'], b['rect']):
                raise SmilesError(f'smiles: rooms {a["id"]} and {b["id"]} overlap')
    van = need(d, 'van_route', 'district')
    path = need(van, 'path', 'van_route')
    streets = need(d, 'streets', 'district')

    def on_street(a, b):
        for st in streets:
            (x0, y0), (x1, y1) = st['from'], st['to']
            if a[1] == b[1] == y0 == y1 and min(x0, x1) <= min(a[0], b[0]) and max(a[0], b[0]) <= max(x0, x1):
                return True
            if a[0] == b[0] == x0 == x1 and min(y0, y1) <= min(a[1], b[1]) and max(a[1], b[1]) <= max(y0, y1):
                return True
        return False
    for a, b in zip(path, path[1:]):
        if not on_street(a, b):
            raise SmilesError(f'smiles: van route leg {a}->{b} does not run along a street')
    if path[0] != path[-1]:
        raise SmilesError('smiles: the van route is not a loop')
    for stp in need(van, 'stops', 'van_route'):
        if not any(on_seg(stp['at'], a, b) for a, b in zip(path, path[1:])):
            raise SmilesError(f'smiles: van stop {stp["id"]} is not on the route')
    games = need(d, 'games', 'district')
    guidance = need(d, 'guidance', 'district')
    for g in GAMES:
        gz = need(need(games, g, 'games'), 'zone', f'game {g}')
        if gz not in zid:
            raise SmilesError(f'smiles: game {g} is placed in unknown zone {gz!r}')
        need(guidance, g, 'guidance')
    if need(d, 'disclaimer', 'district') != DISCLAIMER:
        raise SmilesError('smiles: the disclaimer must read exactly: ' + DISCLAIMER)
    if need(games['brushing'], 'total_s', 'brushing') % len(need(games['brushing'], 'quadrants', 'brushing')):
        raise SmilesError('smiles: brushing time does not split evenly across quadrants')
    for c in need(games['drinks'], 'categories', 'drinks'):
        for k in ('id', 'rank', 'name', 'examples'):
            need(c, k, 'drinks category')
    drinks_text = json.dumps(games['drinks']).lower()
    if re.search(r'\d\s*(g|grams?|tsp|teaspoons?|%\s*sugar|cubes?)\b', drinks_text):
        raise SmilesError('smiles: the drinks game carries a sugar amount - no registry records one')
    sorts = {need(i, 'sort', 'snack') for i in need(games['snacks'], 'items', 'snacks')}
    if sorts != {'tooth-friendly', 'sugary'}:
        raise SmilesError(f'smiles: snack sorts must be tooth-friendly and sugary, got {sorted(sorts)}')
    eggs = []
    for q in need(e, 'entries', 'quests/source/smiles.json'):
        for k in ('id', 'kind', 'title', 'world', 'place', 'hint', 'reward'):
            need(q, k, f'egg {q.get("id")}')
        if not q['world'].startswith('smiles:') or q['world'][7:] not in zid:
            raise SmilesError(f'smiles: egg {q["id"]} world {q["world"]!r} is not smiles:<zone>')
        z = next(z for z in zones if z['id'] == q['world'][7:])
        eggs.append({'id': q['id'], 'zone': z['id'], 'place': q['place'], 'title': q['title'], 'hint': q['hint'],
                     'badge': need(q['reward'], 'label', f'egg {q["id"]} reward'),
                     'reveal': need(q, 'reveal', f'egg {q["id"]}'), 'at': egg_spot(q['id'], z)})
    return d, s, e, st, placed, url_base, eggs


def verify_against_ref(s):
    """When the read-only reference clone is on this machine, prove the transcription still matches it."""
    if not REF_CLONE.exists():
        return 'reference clone absent on this machine; transcription kept as recorded'
    sha = s['ref_commit']
    for p in s['programmes']:
        raw = subprocess.run(['git', '-C', str(REF_CLONE), 'show', f'{sha}:{p["pack_file"]}'], capture_output=True)
        if raw.returncode:
            raise SmilesError(f'smiles: cannot read {p["pack_file"]} at {sha} in the reference clone')
        pk = json.loads(raw.stdout)
        if [x['id'] for x in pk['stations']] != p['station_ids']:
            raise SmilesError(f'smiles: {p["id"]} station list differs from the reference at {sha}')
    return f'verified against the reference clone at {sha}'


def build():
    d, s, e, st, placed, url_base, eggs = load()
    ref_note = verify_against_ref(s)
    stations = []
    for sid in sorted(st):
        x = st[sid]
        stations.append({'id': sid, 'name': x['name'], 'app': x['app'], 'room': placed[sid], 'programmes': x['programmes'],
                         'source': x['source'], 'url': url_base + x['source']})
    MAP.parent.mkdir(parents=True, exist_ok=True)
    map_bytes = render.render_map(d, eggs)
    atlas_bytes, cells = render.render_atlas()
    MAP.write_bytes(map_bytes)
    ATLAS.write_bytes(atlas_bytes)
    inputs = [pathlib.Path(__file__), HERE / 'render.py', DISTRICT, STATIONS, EGGS]
    stamp = hashlib.sha256(b''.join(p.read_bytes() for p in inputs)).hexdigest()
    zones = [dict(z, eggs=[g['id'] for g in eggs if g['zone'] == z['id']], solids=solids(z),
                  games=[g for g in GAMES if d['games'][g]['zone'] == z['id']]) for z in d['zones']]
    for z in zones:
        for r in z['solids']:
            if not inside(r, z['rect']):
                raise SmilesError(f'smiles: a solid footprint in {z["id"]} lies outside the zone')
            for g in eggs:
                if g['zone'] == z['id'] and near_solid(g['at'], z):
                    raise SmilesError(f'smiles: egg {g["id"]} is inside or against a solid footprint in {z["id"]}')
    walls, doors = walls_for(d)
    reg = {
        'walls': walls,
        'doors': doors,
        'walls_note': 'AUTHORED walls: each is drawn and is a solid box in the shared arcade physics (web/physkit.py); one south doorway per building and clinic room.',
        'schema': 'smiles/1',
        'name': d['name'],
        'provenance': 'AUTHORED',
        'place_note': d['place_note'],
        'size_m': d['size_m'],
        'source_stamp': stamp,
        'inputs': [str(p.relative_to(ROOT)) for p in inputs],
        'stations_from': {k: s[k] for k in ('from', 'ref_commit', 'branch', 'url_base', 'note')},
        'stations_check': ref_note,
        'programmes': [{'id': p['id'], 'name': p['name'], 'pack_file': p['pack_file'], 'stations': len(p['station_ids'])}
                       for p in s['programmes']],
        'streets': d['streets'],
        'zones': zones,
        'rooms': d['rooms'],
        'rooms_note': d['rooms_note'],
        'stations': stations,
        'van_route': d['van_route'],
        'games': d['games'],
        'guidance': d['guidance'],
        'disclaimer': d['disclaimer'],
        'play_note': d['play_note'],
        'eggs': eggs,
        'map': {'image': str(MAP.relative_to(ROOT)), 'px': d['map_px'], 'm_per_px': round(d['size_m'][0] / d['map_px'], 6),
                'sha256': hashlib.sha256(map_bytes).hexdigest(), 'bytes': len(map_bytes), 'provenance': 'AUTHORED'},
        'atlas': {'image': str(ATLAS.relative_to(ROOT)), 'grid': render.ATLAS_GRID, 'cells': cells,
                  'sha256': hashlib.sha256(atlas_bytes).hexdigest(), 'bytes': len(atlas_bytes), 'provenance': 'AUTHORED'},
        'counts': {'zones': len(zones), 'rooms': len(d['rooms']), 'stations': len(stations), 'eggs': len(eggs),
                   'games': len(GAMES), 'van_stops': len(d['van_route']['stops'])},
    }
    return json.dumps(reg, indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    text = build()
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            raise SystemExit('smiles: registry is stale - run python3 smiles/build.py')
        print('smiles: registry current')
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    r = json.loads(text)
    print(f'smiles: {r["counts"]} map {r["map"]["bytes"]} B atlas {r["atlas"]["bytes"]} B stamp {r["source_stamp"][:16]}')


if __name__ == '__main__':
    main()
