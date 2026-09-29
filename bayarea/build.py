#!/usr/bin/env python3
"""bayarea/build.py - the Bay Area county pack (BAY, wave 8). Mirrors parishes/ (PARISH_CONTRACT v1.4 formats).

Which counties (COMPUTED, never hand-picked): every California county (state FIPS 06) whose RECORDED us-atlas
outline (Census cartographic boundary, 1:10m, coarse) intersects the BAY FRAME. The Bay frame is DERIVED: the
bounding box of every RECORDED point the geo registry holds for the Bay campuses (geo/registry/campuses_geo.json
campuses.oakland / campuses.treasure-island and their anchors, provenance RECORDED only; the DERIVED Treasure Island
centroid is excluded). The wider RECORDED Locator.X map frame (city.oakland.bounds) is also evaluated and its
county count printed, but not used: it reaches the Central Valley and Sierra foothills, which is not the Bay.

Geometry helpers are imported from parishes/build.py; maps/tiles/streets from bayarea/render_bay.py, which imports
parishes/render.py. Nothing is fetched. Districts are AUTHORED (procedural Voronoi seeds of the same fabric the map
draws): Locator.X (Apache-2.0 code) holds no local neighbourhood data (its data/ tree is not committed), so no
official neighbourhood is available and none is claimed.

    python3 bayarea/build.py        # writes bayarea/registry/bayarea.json + bayarea/maps/*
"""
import hashlib
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'parishes'))  # parishes/ first: `import build` = parishes/build.py
import build as PB  # noqa: E402  parishes/build.py (geometry helpers only; never edited)
sys.path.insert(0, str(HERE))
import render_bay  # noqa: E402
import districts_map  # noqa: E402

TOPO = 'parishes/vendor/us-atlas/counties-10m.json'
MANIFEST = 'parishes/vendor/us-atlas/manifest.json'
GEO = 'geo/registry/campuses_geo.json'
PARCELS = 'parcels/registry/parcels.json'
RESTORE = 'restoration/registry/restoration.json'
NE = {'coastline': 'terrain/vendor/ne_coastline.json', 'rivers': 'terrain/vendor/ne_rivers.json'}
NE_MANIFEST = 'terrain/vendor/manifest.json'
WATER_LABELS = 'bayarea/authored/water_labels.json'
INPUTS = ['bayarea/build.py', 'bayarea/render_bay.py', 'bayarea/world_bay.py', 'bayarea/districts_map.py', 'parishes/build.py', 'parishes/render.py',
          TOPO, MANIFEST, GEO, PARCELS, RESTORE, NE_MANIFEST, NE['coastline'], NE['rivers'], WATER_LABELS]
STATE = '06'
BAY_CAMPUSES = ['oakland', 'treasure-island']
EARTH_R_M = PB.EARTH_R_M

PROVENANCE = {
    'outline': 'RECORDED - US Census cartographic boundary via us-atlas 3.0.1 counties-10m (1:10m, coarse, '
               'coastline-clipped); vendored in parishes/vendor/us-atlas, sha-checked',
    'frame': 'DERIVED - bounding box of the RECORDED Bay campus + anchor points in ' + GEO + ' and the recorded restoration site points in ' + RESTORE,
    'selection': 'DERIVED - computed by intersecting RECORDED outlines with the DERIVED Bay frame',
    'adjacency': 'DERIVED - two counties connect when their outlines share a TopoJSON arc',
    'area': 'DERIVED - planar area of the coarse outline in the county LOCAL frame',
    'districts': 'AUTHORED - procedural district seeds of the map fabric; NOT official neighbourhoods',
    'campuses': 'as tagged in ' + GEO + ' (oakland RECORDED, treasure-island DERIVED) - copied, never upgraded',
    'anchors': 'RECORDED - city points in ' + GEO + ' (Locator.X CITIES, Apache-2.0)',
    'maps': 'DERIVED outline + AUTHORED fabric; not imagery, not a survey',
    'water_labels': 'AUTHORED - approximate label points for general geography only',
}
WATER = ('The Census cartographic outline is clipped to the COASTLINE: San Francisco Bay, San Pablo Bay and the '
         'Pacific lie OUTSIDE every land outline and are drawn as open water. Smaller inland water (reservoirs, '
         'sloughs, parts of the delta) is NOT cut out at 1:10m and lies inside outlines; area_km2 includes it.')
ELEVATION = 'no real elevation: the Bay hills are not modelled; the ground is flat AUTHORED at 0 m'
DISTRICT_NOTE = 'AUTHORED procedural district (Voronoi seed of the map fabric) - NOT an official neighbourhood'
NO_CITY_BOUNDARY = ('no city boundary is held (us-atlas has counties only): San Francisco city = San Francisco County '
                    '(consolidated city-county); Oakland lies in Alameda County but its city limits are not held, so '
                    'Alameda districts are AUTHORED county districts, tagged by distance to the RECORDED Oakland point')


def fail(msg):
    raise SystemExit('bayarea build: ' + msg)


def need(obj, key, where):
    if not isinstance(obj, dict) or key not in obj:
        fail(f'missing {key} in {where}')
    return obj[key]


def load(p):
    return json.loads((ROOT / p).read_text())


def source_stamp():
    h = hashlib.sha256()
    for p in INPUTS:
        h.update(p.encode() + b'\0' + (ROOT / p).read_bytes() + b'\0')
    return h.hexdigest()


def natural_earth(wfwd):
    man = load(NE_MANIFEST)
    out = {'source': need(man, 'source', 'ne manifest'), 'licence': need(man, 'licence', 'ne manifest'),
           'window_deg': need(man, 'window_deg', 'ne manifest'), 'clip': 'oakland (the vendored clip around the '
           'Oakland campus; the Treasure Island clip is the same window)', 'provenance': 'RECORDED at Natural Earth '
           '1:10m scale (coarse - a generalised shoreline, not a survey); world_m = [east_m, north_m]',
           'use': 'the bays/ocean are already open water outside the Census outlines; this NE line is the RECORDED '
                  'coarse shoreline DEEP/RESTORE may draw or test against', 'layers': {}}
    for layer, path in NE.items():
        f = need(need(man, 'files', 'ne manifest'), path.split('/')[-1], 'ne manifest.files')
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != need(f, 'sha256', path):
            fail(f'{path} does not match its vendored sha256')
        clip = need(need(load(path), 'campuses', path), 'oakland', path + '.campuses')
        lines = []
        for ft in need(clip, 'features', path):
            g = need(ft, 'geometry', path)
            parts = g['coordinates'] if need(g, 'type', path) == 'MultiLineString' else [g['coordinates']]
            lines += [[list(wfwd(x, y)) for x, y in part] for part in parts]
        out['layers'][layer] = {'file': path, 'sha256': need(f, 'sha256', path), 'lines': len(lines),
                                'vertices': sum(len(l) for l in lines), 'world_m': lines}
    return out


def restoration_points(rs):
    out = []
    for S in need(rs, 'sites', 'restoration'):
        sid = need(S, 'id', 'restoration site')
        out.append((sid, need(S, 'name', sid), need(S, 'lat', sid), need(S, 'lng', sid)))
    return out


def bay_frame(geo, rs):
    pts = []
    for cid in BAY_CAMPUSES:
        c = need(need(geo, 'campuses', 'geo'), cid, 'campuses')
        pts.append((cid, need(c, 'lat', cid), need(c, 'lng', cid), need(c, 'provenance', cid)))
        for a in need(need(geo, 'anchors', 'geo'), cid, 'anchors'):
            nm = need(a, 'name', 'anchor')
            pts.append((nm, need(a, 'lat', nm), need(a, 'lng', nm), need(a, 'provenance', nm)))
    for sid, _nm, lat, lng in restoration_points(rs):
        if lat is not None and lng is not None:
            pts.append(('restoration:' + sid, lat, lng, 'RECORDED'))
    rec = [p for p in pts if p[3] == 'RECORDED']
    if len(rec) < 3:
        fail('fewer than 3 RECORDED Bay points')
    fr = {'w': min(p[2] for p in rec), 's': min(p[1] for p in rec),
          'e': max(p[2] for p in rec), 'n': max(p[1] for p in rec)}
    return fr, sorted({p[0] for p in rec}), sorted({p[0] for p in pts if p[3] != 'RECORDED'})


def satellite(parcels):
    img = need(parcels, 'imagery', 'parcels')
    return {'fetched_at_build': False, 'stored': False,
            'rule': "view-time only, in the learner's browser; never fetched, stored or baked by any build; "
                    'the 4k maps contain no imagery',
            'usgs': {k: need(img, k, 'imagery') for k in ('id', 'tiles', 'scheme', 'zoom', 'tile_size', 'attribution',
                                                          'licence')}
            | {'source': PARCELS + '#imagery', 'token': None,
               'when_unavailable': 'fall back to the drawn 4k map; say "USGS imagery did not answer"'},
            'mapbox': {'refusal_text': 'Mapbox satellite: off - no token configured', 'configured_here': False,
                       'rule': 'same deploy-time pk. token rule as parishes/registry/parishes.json#satellite.mapbox'}}


def districts_of(gid, P, fab):
    SX, SY, TY, ANG = fab['SX'], fab['SY'], fab['TY'], fab['ANG']
    outline = P['outline_local_m']
    out = []
    for i in range(fab['ni']):
        for j in range(fab['nj']):
            pt = (float(SX[i, j]), float(SY[i, j]))
            if not PB.in_polys(pt, outline):
                continue
            out.append({'id': f'{gid}-D{len(out) + 1:03d}', 'seed_local_m': [round(pt[0]), round(pt[1])],
                        'use': render_bay.USE_ORDER[int(TY[i, j])],
                        'grid_angle_deg': round(math.degrees(float(ANG[i, j])) % 180, 1),
                        'provenance': 'AUTHORED'})
    return out


def main():
    topo = load(TOPO)
    man = load(MANIFEST)
    geo = load(GEO)
    wl = load(WATER_LABELS)
    if need(wl, 'provenance', 'water_labels') != 'AUTHORED':
        fail('water_labels.json must be AUTHORED')
    arcs = PB.decode_arcs(topo)
    geoms = need(need(need(topo, 'objects', 'topology'), 'counties', 'objects'), 'geometries', 'counties')
    by_id = {need(g, 'id', 'geometry'): g for g in geoms}
    rs = load(RESTORE)
    frame, frame_points, frame_excluded = bay_frame(geo, rs)
    wide = need(need(need(geo, 'city', 'geo'), 'oakland', 'city'), 'bounds', 'city.oakland')
    oak_center = need(need(need(geo, 'city', 'geo'), 'oakland', 'city'), 'center', 'city.oakland')
    world_origin = (need(oak_center, 'lat', 'center'), need(oak_center, 'lng', 'center'))
    print(f'Bay frame (DERIVED from {len(frame_points)} RECORDED points) w={frame["w"]} s={frame["s"]} '
          f'e={frame["e"]} n={frame["n"]}')
    selected, excluded, wide_sel = [], [], []
    for gid, g in sorted(by_id.items()):
        polys = PB.polygons_of(g, arcs)
        if gid.startswith(STATE) and PB.intersects_frame(polys, wide):
            wide_sel.append(gid)
        how = PB.intersects_frame(polys, frame)
        if how is None:
            continue
        name = need(need(g, 'properties', gid), 'name', gid)
        if gid.startswith(STATE):
            selected.append((gid, name, how))
        else:
            excluded.append({'fips': gid, 'name': name, 'why': 'not a California county'})
    for gid, name, how in selected:
        print(f'  selected {gid} {name} County ({how})')
    print(f'  wider RECORDED Locator.X map frame would select {len(wide_sel)} counties (not used)')
    sel_ids = [s[0] for s in selected]
    owners = {}
    for gid, g in by_id.items():
        for a in PB.arc_ids(g):
            owners.setdefault(a, set()).add(gid)
    wfwd = PB.ltp(*world_origin)
    counties = {}
    for gid, name, how in selected:
        g = by_id[gid]
        polys = PB.polygons_of(g, arcs)
        lat0, lng0 = PB.centroid_ll(polys)
        fwd = PB.ltp(lat0, lng0)
        outline_m = [[[fwd(x, y) for x, y in ring] for ring in poly] for poly in polys]
        area = sum(abs(PB.ring_area_m2(p[0])) - sum(abs(PB.ring_area_m2(h)) for h in p[1:]) for p in outline_m)
        mine = PB.arc_ids(g)
        adj, outside, borders = [], [], []
        for nb in sorted({o for a in mine for o in owners[a] if o != gid}):
            shared = sorted(a for a in mine if nb in owners[a])
            if nb in sel_ids:
                adj.append(nb)
                segs = [{'arc': a, 'wgs84': [[x, y] for x, y in arcs[a]],
                         'world_m': [list(wfwd(x, y)) for x, y in arcs[a]],
                         'local_m': [list(fwd(x, y)) for x, y in arcs[a]]} for a in shared]
                borders.append({'with': nb, 'segments': segs,
                                'length_m': round(sum(math.dist(p, q) for s in segs
                                                      for p, q in zip(s['local_m'], s['local_m'][1:])), 1)})
            else:
                outside.append({'fips': nb, 'name': need(need(by_id[nb], 'properties', nb), 'name', nb),
                                'shared_arcs': len(shared), 'selected': False})
        allpts = [p for q in polys for p in q[0]]
        counties[gid] = {
            'fips': gid, 'name': name, 'full_name': f'{name} County', 'selected_because': how,
            'outline': {'crs': 'WGS84 (EPSG:4326), [lng, lat]', 'provenance': 'RECORDED',
                        'polygons': [[[[x, y] for x, y in ring] for ring in poly] for poly in polys],
                        'rings': sum(len(p) for p in polys), 'vertices': sum(len(r) for p in polys for r in p)},
            'frame': {'origin': {'lat': lat0, 'lng': lng0, 'what': 'area-weighted centroid of the coarse outline'},
                      'formula': 'see registry.frames.ltp_formula', 'R_m': EARTH_R_M,
                      'max_ew_scale_error_pct': round(100 * max(abs(math.cos(math.radians(y)) / math.cos(math.radians(lat0)) - 1)
                                                               for poly in polys for r in poly for x, y in r), 3),
                      'origin_in_world_m': list(wfwd(lng0, lat0))},
            'outline_local_m': [[[list(p) for p in ring] for ring in poly] for poly in outline_m],
            'outline_world_m': [[[list(wfwd(x, y)) for x, y in ring] for ring in poly] for poly in polys],
            'bbox_wgs84': [min(p[0] for p in allpts), min(p[1] for p in allpts),
                           max(p[0] for p in allpts), max(p[1] for p in allpts)],
            'area_km2': round(area / 1e6, 1),
            'area_note': 'area inside the coarse 1:10m cartographic outline (coastline-clipped, includes small inland '
                         'water); not the official Census land or total area',
            'adjacent': adj, 'borders': borders, 'neighbours_not_selected': outside,
            'landmarks': [], 'campuses': [], 'anchors': [], 'restoration_sites': [],
            'city_note': NO_CITY_BOUNDARY,
        }
    # campuses (as tagged) and RECORDED city anchors: kept only when inside a selected outline
    dropped = []
    for cid in BAY_CAMPUSES:
        c = geo['campuses'][cid]
        pt = (c['lng'], c['lat'])
        home = [p for p in counties if PB.in_polys(pt, counties[p]['outline']['polygons'])]
        rec = {'name': need(c, 'city', cid) + ' campus (' + cid + ')', 'campus': cid, 'lat': pt[1], 'lng': pt[0],
               'world_m': list(wfwd(*pt)), 'provenance': need(c, 'provenance', cid), 'source': need(c, 'source', cid),
               'site_plan': 'campusplan/registry/campusplan.json (SITES) holds the campus lots; not in the main tree at '
                            'this build, so only the geo registry point is placed'}
        if len(home) != 1:
            dropped.append({'name': rec['name'], 'why': f'point lies in {len(home)} selected coarse outlines '
                            '(small islands are not in the 1:10m outline); kept in registry.campuses_not_placed'})
            rec['county'] = None
            continue
        p = home[0]
        o = counties[p]['frame']['origin']
        rec['local_m'] = list(PB.ltp(o['lat'], o['lng'])(*pt))
        rec['county'] = p
        counties[p]['campuses'].append(rec)
    offshore = [d for d in dropped]
    seen = set()
    for cid in BAY_CAMPUSES:
        for A in geo['anchors'][cid]:
            nm = A['name']
            if nm in seen or A['provenance'] != 'RECORDED':
                continue
            seen.add(nm)
            pt = (A['lng'], A['lat'])
            home = [p for p in counties if PB.in_polys(pt, counties[p]['outline']['polygons'])]
            if len(home) != 1:
                dropped.append({'name': nm, 'why': f'point lies in {len(home)} selected outlines (dropped, not moved)'})
                continue
            p = home[0]
            o = counties[p]['frame']['origin']
            counties[p]['anchors'].append({'name': nm, 'kind': 'city', 'lat': pt[1], 'lng': pt[0],
                                           'local_m': list(PB.ltp(o['lat'], o['lng'])(*pt)), 'world_m': list(wfwd(*pt)),
                                           'provenance': 'RECORDED', 'source': A['source']})
    restoration_not_placed = []
    for sid, nm, lat, lng in restoration_points(rs):
        if lat is None or lng is None:
            restoration_not_placed.append({'id': sid, 'name': nm, 'why': 'the restoration registry records no single '
                                           'point (lat/lng null) - not placed, never guessed'})
            continue
        pt = (lng, lat)
        home = [p for p in counties if PB.in_polys(pt, counties[p]['outline']['polygons'])]
        rec = {'id': sid, 'name': nm, 'kind': 'restoration site', 'lat': lat, 'lng': lng, 'world_m': list(wfwd(*pt)),
               'provenance': 'RECORDED', 'source': RESTORE + '#sites[' + sid + '].lat/lng'}
        if len(home) != 1:
            rec['why'] = (f'point lies in {len(home)} selected coarse outlines (open water or an island absent at 1:10m): '
                          'kept at its recorded world_m, not moved onto land')
            restoration_not_placed.append(rec)
            continue
        o = counties[home[0]]['frame']['origin']
        rec['local_m'] = list(PB.ltp(o['lat'], o['lng'])(*pt))
        counties[home[0]]['restoration_sites'].append(rec)
    for d in dropped + restoration_not_placed:
        print(f'  not placed: {d["name"]} - {d["why"]}')
    water_labels = []
    for W in need(wl, 'labels', 'water_labels'):
        nm = need(W, 'name', 'water_label')
        pt = (need(W, 'lng', nm), need(W, 'lat', nm))
        water_labels.append({'name': nm, 'lat': pt[1], 'lng': pt[0], 'world_m': list(wfwd(*pt)),
                             'inside_outline_of': [p for p in counties if PB.in_polys(pt, counties[p]['outline']['polygons'])],
                             'provenance': 'AUTHORED', 'note': need(W, 'note', nm)})
    stamp = source_stamp()
    maps = render_bay.render_all(ROOT, counties, by_id, arcs, PB.polygons_of, PB.ltp, frame, water_labels, stamp,
                                 (STATE,), districts_of)
    oak = geo['campuses']['oakland']
    for gid in counties:
        mp = maps[gid]
        ex = mp['extent_wgs84']
        mp['corners_world_m'] = {'nw': list(wfwd(ex[0], ex[3])), 'ne': list(wfwd(ex[2], ex[3])),
                                 'se': list(wfwd(ex[2], ex[1])), 'sw': list(wfwd(ex[0], ex[1])),
                                 'note': 'the map is square in its LOCAL frame; place by these world corners'}
        C = counties[gid]
        C['map'] = mp
        o = C['frame']['origin']
        oe, on = PB.ltp(o['lat'], o['lng'])(oak['lng'], oak['lat'])
        for dct in C['districts']:
            dct['km_to_oakland_point'] = round(math.dist(dct['seed_local_m'], (oe, on)) / 1000, 2)
        C['districts_note'] = DISTRICT_NOTE
        exl = mp['extent_local_m']
        mp['districts_map'] = districts_map.draw(ROOT, gid, C, exl['left'], exl['top'], mp['m_per_px'])
    reg = {
        'pack': 'bayarea', 'pack_version': need(load('pack/manifest.json'), 'pack_version', 'manifest'), 'contract': 'PARISH_CONTRACT v1.4 formats (county wording)',
        'source_stamp': stamp[:16], 'source_stamp_sha256': stamp, 'inputs': INPUTS,
        'provenance_tiers': ['RECORDED', 'DERIVED', 'AUTHORED'], 'provenance': PROVENANCE,
        'source': {'package': need(man, 'package', 'manifest'), 'version': need(man, 'version', 'manifest'),
                   'integrity': need(man, 'integrity', 'manifest'), 'license': need(man, 'license', 'manifest'),
                   'data_origin': need(man, 'data_origin', 'manifest'), 'file': TOPO,
                   'file_sha256': need(need(need(man, 'files', 'manifest'), 'counties-10m.json', 'files'), 'sha256', 'f')},
        'bay_frame': {'bounds': frame, 'provenance': PROVENANCE['frame'], 'recorded_points': frame_points,
                      'excluded_points': frame_excluded, 'source': GEO + '#campuses+anchors.{oakland,treasure-island}'},
        'selection': {'rule': 'every California county (state FIPS 06) whose RECORDED outline intersects the DERIVED '
                              'Bay frame (any vertex inside, any frame corner inside, or any edge crossing)',
                      'selected': sel_ids, 'excluded_other_state': excluded, 'provenance': PROVENANCE['selection'],
                      'wider_frame': {'bounds': wide, 'source': GEO + '#city.oakland.bounds (RECORDED, Locator.X map '
                                      'frame)', 'would_select': len(wide_sel), 'fips': wide_sel,
                                      'why_not_used': 'it reaches the Central Valley and Sierra foothills; the Bay '
                                                      'frame from the campus points is the honest Bay extent'}},
        'frames': {'ltp_formula': PB.LTP_FORMULA, 'R_m': EARTH_R_M,
                   'world': {'origin': {'lat': world_origin[0], 'lng': world_origin[1]},
                             'source': GEO + '#city.oakland.center',
                             'what': 'one shared metre frame for every county; world_m = [east_m, north_m]'},
                   'local': 'per county: origin = counties[fips].frame.origin; local_m = [east_m, north_m]'},
        'water': {'statement': WATER, 'inland_water_cut_out': False, 'labels': water_labels},
        'elevation': ELEVATION,
        'districts_rule': DISTRICT_NOTE + '. Locator.X (/home/user/locator.x, Apache-2.0 code, CC BY 4.0 docs) was '
                          'checked: its data/ tree is not committed (data/README.md), so it offers no local district '
                          'data; no official neighbourhood list is used or claimed.',
        'city_note': NO_CITY_BOUNDARY,
        'landmarks_rule': 'none authored in this pack (landmarks: [] everywhere); only campus points and RECORDED city '
                          'points are pinned',
        'campuses_not_placed': offshore,
        'restoration_rule': ('every site in ' + RESTORE + ' with a recorded lat/lng is inside the Bay frame by '
                             'construction (its point widens the frame); placed in the county whose coarse outline '
                             'holds it, else kept in restoration_not_placed at its recorded world_m'),
        'restoration_not_placed': restoration_not_placed,
        'not_placed': dropped,
        'fetches': 'none - every input is a local file listed in inputs',
        'landmarks_method': 'no landmark is authored in the bayarea pack; pins are the geo registry campus points (as '
                            'tagged) and RECORDED Locator.X city points only',
        'borders_note': ('shared borders are DERIVED from shared TopoJSON arcs of the coarse 1:10m outlines; whether a '
                         'border runs over land or water is NOT recorded. By its coordinates the short 06001|06075 arc '
                         '(about 0.4 km) lies in the open bay on the Bay Bridge corridor: treat it as a water crossing '
                         '(AUTHORED note), not a road. Marin has no selected neighbour: the Golden Gate is open water '
                         'between outlines, so Marin joins the world by water only.'),
        'satellite': satellite(load(PARCELS)),
        'natural_earth': natural_earth(wfwd),
        'counts': {'counties': len(counties), 'adjacency_pairs': sum(len(c['adjacent']) for c in counties.values()) // 2,
                   'districts': sum(len(c['districts']) for c in counties.values()),
                   'campuses_placed': sum(len(c['campuses']) for c in counties.values()),
                   'anchors': sum(len(c['anchors']) for c in counties.values()),
                   'restoration_placed': sum(len(c['restoration_sites']) for c in counties.values()),
                   'restoration_not_placed': len(restoration_not_placed),
                   'maps_4k': len(maps), 'tiles': sum(len(m['ground_tiles']['tiles']) for m in maps.values())},
        'counties': counties,
    }
    out = ROOT / 'bayarea' / 'registry' / 'bayarea.json'
    out.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n')
    for gid, c in counties.items():
        print(f'  {gid} {c["name"]}: {c["area_km2"]} km2, {len(c["districts"])} districts, adj {c["adjacent"]}, '
              f'4k {c["map"]["bytes"]} B')
    print(f'wrote {out.relative_to(ROOT)}: {reg["counts"]} stamp {stamp[:16]}')
    import world_bay as BW  # bayarea/world_bay.py (the world layer is derived from what was just written)
    BW.main()


if __name__ == '__main__':
    main()
