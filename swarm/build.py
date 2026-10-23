#!/usr/bin/env python3
"""The Omega Swarm registry: swarm/registry/swarm.json (SWARM, wave 24).

A geo-indexed network of agent hives, built from what the repo already holds and nothing else:

  * HIVES   - one per campus cluster (campuses within the authored distance of each other share a hive), each owning a
              set of geohash cells that covers every campus, anchor and restoration-site pose in
              spatial/registry/geopose.json (OGC GeoPose, already in the repo).
  * MEMBERS - the SCRIPTED roles already in the repo, instanced per hive: the five Omega Claw agents, the nine Omega
              Hive hall advisors, the twenty crew roles, and the Hive parish guides (placed at their parish);
              plus AUTHORED simulated robots (the three arena embodiments) placed at poses of their own campus.
  * CAPABILITIES - what a command may ask for: four robot tasks (the arena worlds of robotics/registry/robotics.json)
              and three software reports (read from registries).

No AI model runs behind any of it and nothing in it can reach a robot or a device. Fails closed: a missing field, a
campus cluster that is not the authored one, a pose with no cell, a cell owned by two hives, a parish too far from
every hive or a capability that names something absent stops the build with a named error. `--check` rebuilds in
memory and fails if the file on disk is stale.
"""
import hashlib
import json
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'swarm.json'
AUTH_REL = 'swarm/authored/swarm.json'
B32 = '0123456789bcdefghjkmnpqrstuvwxyz'


def need(cond, msg):
    if not cond:
        raise SystemExit(f'swarm: {msg}')


_cache = {}


def load(rel):
    if rel not in _cache:
        p = ROOT / rel
        need(p.is_file(), f'missing {rel}')
        _cache[rel] = json.loads(p.read_text())
    return _cache[rel]


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


# ---------------------------------------------------------------- geohash --
def gh_encode(lat, lng, p):
    need(-90 <= lat <= 90 and -180 <= lng <= 180, f'coordinate out of range {lat},{lng}')
    la, lo, out, bits, ch, even = [-90.0, 90.0], [-180.0, 180.0], '', 0, 0, True
    while len(out) < p:
        r, v = (lo, lng) if even else (la, lat)
        mid = (r[0] + r[1]) / 2
        if v >= mid:
            ch = (ch << 1) | 1
            r[0] = mid
        else:
            ch <<= 1
            r[1] = mid
        even = not even
        bits += 1
        if bits == 5:
            out += B32[ch]
            bits = ch = 0
    return out


def gh_bounds(h):
    la, lo, even = [-90.0, 90.0], [-180.0, 180.0], True
    for c in h:
        v = B32.index(c)
        for b in (16, 8, 4, 2, 1):
            r = lo if even else la
            mid = (r[0] + r[1]) / 2
            if v & b:
                r[0] = mid
            else:
                r[1] = mid
            even = not even
    return {'s': la[0], 'w': lo[0], 'n': la[1], 'e': lo[1]}


def gh_center(h):
    b = gh_bounds(h)
    return (b['s'] + b['n']) / 2, (b['w'] + b['e']) / 2


def gh_ring(h, k):
    b = gh_bounds(h)
    dlat, dlng = b['n'] - b['s'], b['e'] - b['w']
    la, lo = gh_center(h)
    out = set()
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            out.add(gh_encode(max(-89.999, min(89.999, la + i * dlat)), ((lo + j * dlng + 180) % 360) - 180, len(h)))
    return sorted(out)


def hav_km(a, b):
    r = 6371.0088
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def r6(x):
    return round(x, 6)


# ------------------------------------------------------------------ build --
def build():
    auth = load(AUTH_REL)
    gp, hv, cl, rb, sims = (load(r) for r in ('spatial/registry/geopose.json', 'hive/registry/hive.json',
                                               'robotics/claw/registry/claw.json', 'robotics/registry/robotics.json',
                                               'sims/registry/sims.json'))
    npcs, prs, advisors = load('npcs/registry/npcs.json'), load('parishes/registry/parishes.json'), load('agents/registry/advisors.json')
    P = auth['cell_scheme']['precision']
    need(auth['cell_scheme']['alphabet'] == B32, 'authored alphabet is not the geohash alphabet')

    # poses: every campus, anchor and restoration site GeoPose holds
    poses = []
    for x in gp['poses']:
        s, pos = x['subject'], x['geopose']['position']
        need(s['campus'], f'pose {s["ref"]} names no campus')
        poses.append({'ref': s['ref'], 'kind': s['kind'], 'name': s['name'], 'campus': s['campus'],
                      'lat': pos['lat'], 'lon': pos['lon']})
    poses.sort(key=lambda p: p['ref'])
    campus_pose = {p['campus']: p for p in poses if p['kind'] == 'campus'}
    need(len(campus_pose) == gp['counts']['campuses'], 'campus pose count differs from GeoPose counts')

    # clusters: single-linkage at the authored distance
    names = sorted(campus_pose)
    parent = {c: c for c in names}

    def find(c):
        while parent[c] != c:
            c = parent[c]
        return c
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if hav_km((campus_pose[a]['lat'], campus_pose[a]['lon']), (campus_pose[b]['lat'], campus_pose[b]['lon'])) <= auth['cluster_rule']['max_km']:
                parent[find(a)] = find(b)
    groups = {}
    for c in names:
        groups.setdefault(find(c), []).append(c)
    derived = sorted(tuple(sorted(g)) for g in groups.values())
    written = sorted(tuple(sorted(h['campuses'])) for h in auth['hives'].values())
    need(derived == written, f'campus clusters {derived} are not the authored hives {written}')
    hive_of_campus = {c: hid for hid, h in auth['hives'].items() for c in h['campuses']}

    # cells
    cells = {hid: {} for hid in auth['hives']}   # hive -> cell -> set(reasons)

    def add(hid, cell, why):
        cells[hid].setdefault(cell, set()).add(why)
    cover = []
    for p in poses:
        hid = hive_of_campus[p['campus']]
        p['cell'] = gh_encode(p['lat'], p['lon'], P)
        add(hid, p['cell'], p['kind'])
        cover.append({'ref': p['ref'], 'kind': p['kind'], 'campus': p['campus'], 'hive': hid, 'cell': p['cell']})
    for c, p in campus_pose.items():
        for cell in gh_ring(p['cell'], auth['cell_scheme']['campus_ring']):
            add(hive_of_campus[c], cell, 'ring')

    # parish guides: nearest hive home, cell of the parish centre
    home = {}
    for hid, h in auth['hives'].items():
        c0 = sorted(h['campuses'])[0]
        home[hid] = {'campus': c0, 'lat': campus_pose[c0]['lat'], 'lon': campus_pose[c0]['lon'], 'cell': campus_pose[c0]['cell']}
    parish_at = {}
    for pr in npcs['parishes']:
        o = prs['parishes'][pr['fips']]['outline']['polygons']
        pts = [v for poly in o for ring in poly for v in ring]
        need(pts, f'parish {pr["fips"]} has no outline')
        lat = (min(v[1] for v in pts) + max(v[1] for v in pts)) / 2
        lon = (min(v[0] for v in pts) + max(v[0] for v in pts)) / 2
        hid = min(home, key=lambda h: (hav_km((lat, lon), (home[h]['lat'], home[h]['lon'])), h))
        d = hav_km((lat, lon), (home[hid]['lat'], home[hid]['lon']))
        need(d <= auth['parish_rule']['max_km_from_hive_home'], f'parish {pr["fips"]} is {d:.0f} km from the nearest hive')
        cell = gh_encode(lat, lon, P)
        add(hid, cell, 'parish')
        parish_at[pr['fips']] = {'hive': hid, 'lat': r6(lat), 'lon': r6(lon), 'cell': cell, 'km_from_home': round(d, 1)}
    owner = {}
    for hid, cs in cells.items():
        for cell in cs:
            need(cell not in owner, f'cell {cell} is owned by both {owner.get(cell)} and {hid}')
            owner[cell] = hid

    # members: software roles
    members = []
    claw_ids = [a['id'] for a in cl['agents']]
    need(len(claw_ids) == 5, 'expected five Omega Claw agents')
    hv_by_id = {a['id']: a for a in hv['agents']}
    for hid in sorted(auth['hives']):
        h = home[hid]
        for aid in claw_ids:
            members.append({'id': f'sw:{hid}/{aid}', 'kind': 'software', 'role': aid, 'role_kind': 'claw', 'hive': hid,
                            'lat': h['lat'], 'lon': h['lon'], 'cell': h['cell'], 'provenance': 'SCRIPTED',
                            'source': f'robotics/claw/registry/claw.json#agents[id={aid}]'})
        for a in hv['agents']:
            if a['kind'] in ('advisor', 'crew-role'):
                members.append({'id': f'sw:{hid}/{a["id"]}', 'kind': 'software', 'role': a['id'], 'role_kind': a['kind'], 'hive': hid,
                                'lat': h['lat'], 'lon': h['lon'], 'cell': h['cell'], 'provenance': 'SCRIPTED',
                                'source': f'hive/registry/hive.json#agents[id={a["id"]}]'})
    for a in hv['agents']:
        if a['kind'] == 'npc':
            at = parish_at[a['parish']]
            members.append({'id': f'sw:{at["hive"]}/{a["id"]}', 'kind': 'software', 'role': a['id'], 'role_kind': 'npc', 'hive': at['hive'],
                            'lat': at['lat'], 'lon': at['lon'], 'cell': at['cell'], 'provenance': 'SCRIPTED',
                            'source': f'hive/registry/hive.json#agents[id={a["id"]}]'})
    # members: simulated robots (AUTHORED), at poses of their own campus
    for emb, n in auth['robots_per_campus'].items():
        need(emb in rb['embodiments'], f'embodiment {emb} is not in robotics.json')
    for campus in names:
        hid = hive_of_campus[campus]
        mine = [p for p in poses if p['campus'] == campus]
        sites = [p for p in mine if p['kind'] == 'restoration-site']
        for emb, n in sorted(auth['robots_per_campus'].items()):
            for k in range(1, n + 1):
                rid = f'sim-robot:{hid}/{campus}/{emb}-{k}'
                pool = sites if (emb == 'rov.survey' and sites) else mine
                p = pool[int(sha(rid + ':place')[:8], 16) % len(pool)]
                members.append({'id': rid, 'kind': 'robot', 'role': emb, 'hive': hid, 'campus': campus, 'simulated': True,
                                'real_hardware': False, 'medium': rb['embodiments'][emb]['medium'], 'lat': p['lat'], 'lon': p['lon'],
                                'cell': p['cell'], 'placed_at': p['ref'], 'provenance': 'AUTHORED',
                                'source': f'robotics/registry/robotics.json#embodiments.{emb}'})
    members.sort(key=lambda m: m['id'])
    need(len({m['id'] for m in members}) == len(members), 'duplicate member id')
    for m in members:
        need(owner.get(m['cell']) == m['hive'], f'member {m["id"]} stands in cell {m["cell"]} that hive {m["hive"]} does not own')

    # capabilities
    def src(ref):
        rel, path = ref.split('#', 1)
        node = load(rel)
        for k in path.split('.'):
            need(isinstance(node, dict) and k in node, f'source {ref} does not resolve')
            node = node[k]
        return node
    caps = {}
    for cid, c in sorted(auth['capabilities'].items()):
        if c['kind'] == 'robot':
            env = rb['envs'].get(c['env'])
            need(env and env['runner'] == 'robokit', f'{cid}: {c["env"]} is not a robokit arena world')
            emb = env['embodiments'][0]
            need(emb in auth['robots_per_campus'], f'{cid}: no robot of embodiment {emb}')
            seats = sorted({m.group(1) for s in env['sources'] for m in [re.match(r'sims/registry/sims\.json#sims\.([a-z0-9-]+)', s)] if m})
            gate = []
            for seat in seats:
                need(seat in sims['sims'], f'{cid}: sim seat {seat} not in sims.json')
                gate += [f'sim:{seat}@{hall}' for hall in sorted(sims['sims'][seat]['halls'])]
            lv = env['curriculum']['record_levels'][0]
            caps[cid] = {'kind': 'robot', 'env': env['id'], 'embodiment': emb, 'summary': c['summary'],
                         'level': lv, 'levels': [l['level'] for l in env['curriculum']['levels']], 'seeds': env['seeds'], 'gate_targets': gate,
                         'gate_probe': None if gate else f'sim:{env["id"].split(".", 1)[1]}@arena',
                         'gate_note': ('the arena world is the bay-yard lane of the forklift-run seat; the gate holds every one of that seat\'s hall records' if gate
                                       else 'the gate index (stations and simulator seats) holds no record for this headless arena world, so it answers unknown-target')}
        else:
            role = c['role']
            need(role in claw_ids or role in hv_by_id, f'{cid}: role {role} is not in the Hive or Claw registries')
            caps[cid] = {'kind': 'software', 'role': role, 'summary': c['summary'],
                         'payload': {k: {'value': src(v), 'source': v} for k, v in sorted(c['payload'].items())}}

    stamp_src = (pathlib.Path(__file__).read_bytes() + (ROOT / AUTH_REL).read_bytes()
                 + ''.join(load(r)['source_stamp'] for r in ('spatial/registry/geopose.json', 'hive/registry/hive.json', 'robotics/claw/registry/claw.json',
                                                              'robotics/registry/robotics.json', 'sims/registry/sims.json', 'npcs/registry/npcs.json',
                                                              'parishes/registry/parishes.json', 'agents/registry/advisors.json')).encode())
    hives = []
    for hid in sorted(auth['hives']):
        cs = cells[hid]
        hives.append({'id': hid, 'name': auth['hives'][hid]['name'], 'campuses': sorted(auth['hives'][hid]['campuses']), 'home': home[hid],
                      'cells': {c: sorted(w) for c, w in sorted(cs.items())},
                      'counts': {'cells': len(cs), 'members': sum(1 for m in members if m['hive'] == hid),
                                 'robots': sum(1 for m in members if m['hive'] == hid and m['kind'] == 'robot'),
                                 'software': sum(1 for m in members if m['hive'] == hid and m['kind'] == 'software')}})
    reg = {
        'pack': 'smartcitix-swarm', 'name': auth['name'], 'schema': 'swarm/1',
        'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
        'source_stamp': hashlib.sha256(stamp_src).hexdigest()[:16],
        'sources': {k: load(v)['source_stamp'] for k, v in {
            'geopose': 'spatial/registry/geopose.json', 'hive': 'hive/registry/hive.json', 'claw': 'robotics/claw/registry/claw.json',
            'robotics': 'robotics/registry/robotics.json', 'sims': 'sims/registry/sims.json', 'npcs': 'npcs/registry/npcs.json',
            'parishes': 'parishes/registry/parishes.json', 'advisors': 'agents/registry/advisors.json'}.items()},
        'honesty': {
            'scripted': 'Every software member is a SCRIPTED role already in the Omega Hive or Omega Claw registries; every robot is an AUTHORED simulated robot. No AI model runs behind any of them (models: 0).',
            'simulation_only': 'Nothing in this pack sends a command to a real robot or a device. Every routed command is a dry run against the robotics arena worlds, and every robot command passes through safety_gate/ first.',
            'real_hardware': auth['real_hardware']['refusal'] + '. ' + auth['real_hardware']['rule'],
            'gate': 'The safety gate decides whether a person may enter a hazardous training station or simulator seat. It is not a real-world safety system. It is not a real-world safety system and no standard is claimed. A simulated robot holds no induction, PPE or permit, so a hazardous seat holds its command; a world the gate has no record for runs as a headless dry run and the audit row says so.',
            'location': 'No learner location is stored or sent. Robot and role positions are poses already in the repo (campuses, anchors, restoration sites) or the centre of a parish outline, never a person.',
            'geopose': 'Positions are copied from spatial/registry/geopose.json (horizontal only; height and heading are UNKNOWN there and unused here). A pose is a map anchor, not a parcel.',
            'sim_to_real': 'A dry run is a SCHEMATIC simulation of an AUTHORED task. Its numbers say nothing about how a physical robot would behave.',
            'standards': 'Geohash is used as a public-domain cell scheme; this pack makes no conformance claim to any robotics or fleet-management standard.'},
        'cell_scheme': auth['cell_scheme'], 'cluster_rule': auth['cluster_rule'], 'parish_rule': auth['parish_rule'],
        'robot_placement_rule': auth['robot_placement_rule'], 'dry_run': auth['dry_run'], 'region_limits': auth['region_limits'],
        'real_hardware': auth['real_hardware'], 'optimise': auth['optimise'],
        'hives': hives, 'coverage': cover,
        'unposed': [{'ref': u['subject']['ref'], 'why': u['why']} for u in gp['unposed']],
        'parishes': parish_at, 'capabilities': caps, 'members': members,
        'counts': {'hives': len(hives), 'cells': len(owner), 'poses': len(cover), 'unposed': len(gp['unposed']),
                   'members': len(members), 'software': sum(1 for m in members if m['kind'] == 'software'),
                   'robots': sum(1 for m in members if m['kind'] == 'robot'), 'capabilities': len(caps),
                   'real_hardware_members': 0, 'operators': len(auth['real_hardware']['operators']), 'models': 0},
    }
    return reg


def main():
    reg = build()
    text = json.dumps(reg, indent=1, ensure_ascii=False, sort_keys=False) + '\n'
    if '--check' in sys.argv:
        if not OUT.is_file() or OUT.read_text() != text:
            print('swarm/build.py --check: FAIL swarm/registry/swarm.json is stale; run python3 swarm/build.py', file=sys.stderr)
            sys.exit(1)
        print(f'swarm/build.py --check: up to date (stamp {reg["source_stamp"]})')
        return
    OUT.write_text(text)
    c = reg['counts']
    print(f'swarm: {c["hives"]} hives, {c["cells"]} cells covering {c["poses"]} poses ({c["unposed"]} unposed), '
          f'{c["software"]} software + {c["robots"]} simulated robots, {c["capabilities"]} capabilities, stamp {reg["source_stamp"]}')


if __name__ == '__main__':
    main()
