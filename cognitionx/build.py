#!/usr/bin/env python3
"""
cognitionx/build.py - Cognition.X K-12 blocks inside SmartCiti.X (the COGX pack).

What it does
  1. Reads a LOCAL checkout of Cognition.X (AGIFutureFoundation/cognition.x) at a PINNED commit.
     The commit and the sha256 of every upstream file read are pinned below; any difference stops
     the build with a named error (fail closed). No network, no scraping.
  2. Selects the K-12 blocks of the packs that match SmartCiti's worlds (PACKS below: trades,
     first response, energy/grid, transport, civic, digital/AI, and the core K-12 pack) and keeps
     every column of each block VERBATIM (block_id, pack, track, code, grade, level, credential,
     theme, description, transfer_check). The grade band is DERIVED from the grade by the level
     mapping that data/schema.md states (single grades fold into K-2 / 3-5 / 6-8 / 9-10 / 11-12);
     adult / unbanded rows are excluded and counted.
  3. Maps blocks to SmartCiti world places by ONE stated deterministic rule (MATCH_RULE below):
     shared title words. Places are real ids read from the SmartCiti registries (parish stations,
     K-12 path steps and quote path steps in layers/registry/paths.json, wilds sites, 3D campus
     halls and seats, classroom modules). Unmatched blocks stay unmapped and are counted. The rule
     is a keyword overlap, NOT a pedagogical alignment, and the registry says so.
  4. Links the Cognition.X Louisiana app: for each of SmartCiti's 13 parishes, the one of the
     app's 64 parish dashboards whose name equals parishes.json `name` exactly, read from the
     app's embedded data, with the app's own route "#/parish/<slug>" (slug rule copied from
     apps/louisiana/template.html). Reference field only.
  5. Vendors the subset it used under cognitionx/vendor/ (rows verbatim + LICENSE-CONTENT), so
     `--vendored` can rebuild without the checkout (also sha-pinned) and the suite can round-trip.

Licence: Cognition.X content is CC-BY-4.0 (vendor/LICENSE-CONTENT); code Apache-2.0. Attribution
"Cognition.X by AGI Future Foundation" with the repository link travels on the registry and on
every block consumer (the contract asks pages to show it).

Usage: python3 cognitionx/build.py [--vendored] [--check]
  --vendored  read cognitionx/vendor/* instead of the checkout (pinned sha256s; no fallback:
              without the flag a missing checkout is an error)
  --check     rebuild in memory and fail if cognitionx/registry/cognitionx.json differs
"""
import csv
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
UPSTREAM = pathlib.Path('/home/user/cognition.x')
VENDOR = HERE / 'vendor'
OUT = HERE / 'registry' / 'cognitionx.json'

REPO_URL = 'https://github.com/AGIFutureFoundation/cognition.x'
PIN_COMMIT = '1f45df64c0355804d4811bc0f7491c5501475346'
PIN_FILES = {   # sha256 of every upstream file read (full hex)
    'data/blocks.csv': '18189d88165fed8dd7a8b5f2ccd699225c6098c3b9290ba354e8d3d732d281f7',
    'data/manifest.json': '859f4705eb789b481b8513a4fa80c765934c40b82cd0a6ae2108d5702ad3a756',
    'apps/louisiana/index.html': '0f79c7fb13f733ebb562d9c60e349ada37c4860efdb3030b0483a19d1b15987e',
    'LICENSE-CONTENT': 'd557539df68e771cc1eedcc91d13f70fca930e508d11eedcafa4b15db49e3744',
}
PIN_VENDOR = {  # sha256 of every vendored file (written by this build; --vendored reads them)
    'vendor/blocks_subset.csv': '2298b5aebce927616ddaf32f443c85c010626e80b1cb359dad49504080e19491',
    'vendor/louisiana_parishes.json': 'f08ea83782348d65a069b1c61661b7e4caad0c64252f3eb53568436e9e4422f7',
    'vendor/manifest_subset.json': '916879a3b5fc166eecc9d050107fa9e8ca1bb8ce248a6529d6efeb420407cbe2',
    'vendor/LICENSE-CONTENT': 'd557539df68e771cc1eedcc91d13f70fca930e508d11eedcafa4b15db49e3744',
}

ATTRIBUTION = {
    'text': 'Cognition.X by AGI Future Foundation',
    'author': 'AGI Future Foundation',
    'title': 'Cognition.X blocks dataset (data/blocks.csv)',
    'source_url': REPO_URL,
    'license_id': 'CC-BY-4.0',
    'license': 'CC-BY-4.0',
    'license_url': 'https://creativecommons.org/licenses/by/4.0/',
    'license_file': 'cognitionx/vendor/LICENSE-CONTENT',
    'code_license': 'Apache-2.0 (Cognition.X code; none of it is vendored here)',
    'repo': REPO_URL,
    'commit': PIN_COMMIT,
    'changes': 'rows selected by pack and K-12 grade; every column kept verbatim; the grade band is derived '
               '(data/schema.md level mapping); places are matched by the stated title-word rule',
}

HONESTY = {
    'blocks': 'Cognition.X blocks are curriculum statements with transfer checks, quoted verbatim. They are not '
              'accredited, not a standards alignment, and not verified or reviewed by SmartCiti.X.',
    'mapping': 'A place link means the block and the place title share words under the stated rule - a keyword '
               'overlap, not a pedagogical alignment. Blocks the rule does not match stay unmapped and are counted.',
    'districts': 'K-12 districts named anywhere in SmartCiti.X remain PROPOSED partners: no district has reviewed or '
                 'agreed, and no agreement exists.',
    'louisiana': 'The Louisiana dashboard link is a reference to the Cognition.X Louisiana app (same parish name); '
                 'the dashboard figures belong to that app and are not verified by SmartCiti.X.',
    'privacy': 'No student data leaves the browser: this pack is static data; nothing here collects or sends anything.',
}

# Packs selected for SmartCiti's worlds (manifest slugs), each with why.
PACKS = [
    ('K12', 'core K-12 pack (single grades K-12)'),
    ('NOLATRADES', 'trades: the companion of the New Orleans trades campus'),
    ('RESPOND', 'first response: the companion of the first-responder paths'),
    ('EMERGENCY', 'first response: emergency preparedness'),
    ('ENERGY', 'energy and the grid'),
    ('TRANSPORT', 'transport and mobility'),
    ('NEIGH', 'civic: neighbourhood, safety and civic voice'),
    ('LEGACYLA', 'civic: the Louisiana civic leadership legacy'),
    ('DIGITAL', 'digital life, data and AI'),
]

# data/schema.md: "K-2 & 3-5 -> Explorer, 6-8 -> Builder, 9-10 -> Practitioner, 11-12 -> Lead;
# single grades map into those bands". En dash as the dataset writes it.
BANDS = ['K–2', '3–5', '6–8', '9–10', '11–12']
SINGLE = {'K': 'K–2', '1': 'K–2', '2': 'K–2', '3': '3–5', '4': '3–5', '5': '3–5',
          '6': '6–8', '7': '6–8', '8': '6–8', '9': '9–10', '10': '9–10',
          '11': '11–12', '12': '11–12'}

# ---- the mapping rule (test.mjs re-implements it and must reach the same result) ----
STOP = sorted({
    'about', 'after', 'again', 'also', 'and', 'before', 'being', 'between', 'both', 'does', 'each', 'every',
    'from', 'have', 'here', 'into', 'just', 'know', 'make', 'more', 'most', 'much', 'must', 'only', 'other',
    'over', 'same', 'should', 'some', 'than', 'that', 'their', 'them', 'then', 'there', 'these', 'they', 'thing',
    'this', 'those', 'through', 'under', 'very', 'what', 'when', 'where', 'which', 'while', 'with', 'without',
    'your', 'yours', 'will', 'would', 'could', 'been', 'were', 'what', 'whole', 'anybody', 'everyone', 'somebody',
    'nobody', 'people', 'person', 'real', 'really', 'first', 'second', 'third', 'fourth', 'unit', 'flipped',
    'parish', 'call', 'card', 'keep', 'order', 'read', 'reading', 'build', 'work', 'worker', 'trade', 'allied',
    'above', 'below', 'down', 'across', 'around', 'system', 'service',
})
MIN_SHARED = 2
MATCH_RULE = {
    'block_text': 'theme + " " + description (the description\'s trailing " — at <band>" suffix removed)',
    'place_text': 'the place title as its registry writes it',
    'tokens': 'lower-case; split on anything not a-z; keep words of 4+ letters not in the stop list; '
              '"ies" -> "y", else a trailing single "s" (not "ss") is dropped',
    'match': f'a block maps to a place when their token sets share at least {MIN_SHARED} tokens and at least one '
             f'shared token is in the block theme',
    'order': 'places sorted by id',
    'stop': STOP,
    'min_shared': MIN_SHARED,
}
_STOPSET = set(STOP)


def tokens(text):
    out = set()
    for w in re.findall(r'[a-z]+', text.lower()):
        if len(w) < 4 or w in _STOPSET:
            continue
        if w.endswith('ies'):
            w = w[:-3] + 'y'
        elif w.endswith('s') and not w.endswith('ss'):
            w = w[:-1]
        if len(w) < 4 or w in _STOPSET:
            continue
        out.add(w)
    return out


def block_text(b):
    d = re.sub(r'\s+— at [^—]*$', '', b['description'])
    return b['theme'] + ' ' + d


LA_FIELDS = ['name', 'region', 'seat', 'world', 'districts']   # the only dashboard fields vendored / used


class CogxError(Exception):
    pass


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise CogxError(f'cognitionx: {where} has no field {k!r}')
    return d[k]


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------ upstream ---
def read_upstream():
    if not (UPSTREAM / '.git').exists():
        raise CogxError(f'cognitionx: no Cognition.X checkout at {UPSTREAM} (pass --vendored to build from the '
                        f'pinned vendor subset)')
    head = subprocess.run(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                          check=True).stdout.strip()
    if head != PIN_COMMIT:
        raise CogxError(f'cognitionx: Cognition.X checkout is at {head}, pinned {PIN_COMMIT}')
    raw = {}
    for rel, want in PIN_FILES.items():
        b = (UPSTREAM / rel).read_bytes()
        if sha(b) != want:
            raise CogxError(f'cognitionx: upstream {rel} sha256 {sha(b)} differs from pinned {want}')
        raw[rel] = b
    manifest = json.loads(raw['data/manifest.json'])
    slug_by_name = {need(p, 'name', 'manifest pack'): need(p, 'slug', 'manifest pack')
                    for p in need(manifest, 'packs', 'manifest')}
    names = {}
    for slug, _ in PACKS:
        hit = [n for n, s in slug_by_name.items() if s == slug]
        if len(hit) != 1:
            raise CogxError(f'cognitionx: pack slug {slug} not found once in data/manifest.json')
        names[hit[0]] = slug
    rows = []
    reader = csv.DictReader(io.StringIO(raw['data/blocks.csv'].decode('utf-8'), newline=''))
    header = reader.fieldnames
    for r in reader:            # streamed; only the selected packs are kept
        if r['pack'] in names:
            rows.append(r)
    la = raw['apps/louisiana/index.html'].decode('utf-8')
    key = '"parishes":'
    i = la.find(key)
    if i < 0:
        raise CogxError('cognitionx: apps/louisiana/index.html has no embedded "parishes" array')
    la_all, _ = json.JSONDecoder().raw_decode(la[i + len(key):])
    la_parishes = [{k: need(p, k, 'louisiana parish') for k in LA_FIELDS} for p in la_all]   # values verbatim
    man_sub = {'dataset': need(manifest, 'dataset', 'manifest'), 'total_blocks': need(manifest, 'total_blocks', 'manifest'),
               'packs': [p for p in manifest['packs'] if p['slug'] in names.values()]}
    return {'header': header, 'rows': rows, 'la_parishes': la_parishes, 'manifest': man_sub,
            'license': raw['LICENSE-CONTENT'], 'upstream_files': {k: sha(v) for k, v in raw.items()}}


def read_vendored():
    raw = {}
    for rel, want in PIN_VENDOR.items():
        p = HERE / rel
        if not p.is_file():
            raise CogxError(f'cognitionx: vendored file {rel} is missing')
        b = p.read_bytes()
        if sha(b) != want:
            raise CogxError(f'cognitionx: vendored {rel} sha256 {sha(b)} differs from pinned {want}')
        raw[rel] = b
    reader = csv.DictReader(io.StringIO(raw['vendor/blocks_subset.csv'].decode('utf-8'), newline=''))
    rows = list(reader)
    return {'header': reader.fieldnames, 'rows': rows,
            'la_parishes': json.loads(raw['vendor/louisiana_parishes.json'])['parishes'],
            'manifest': json.loads(raw['vendor/manifest_subset.json']),
            'license': raw['vendor/LICENSE-CONTENT'], 'upstream_files': dict(PIN_FILES)}


# ------------------------------------------------------------------ SmartCiti places ---
SRC = {
    'layers': 'layers/registry/layers.json',
    'paths': 'layers/registry/paths.json',
    'wilds': 'wilds/registry/wilds.json',
    'sims': 'sims/registry/sims.json',
    'lessons': 'lessons/registry/lessons.json',
    'schools': 'schools/registry/schools.json',
    'parishes': 'parishes/registry/parishes.json',
}


def smartciti():
    raw = {k: (ROOT / p).read_bytes() for k, p in SRC.items()}
    reg = {k: json.loads(v) for k, v in raw.items()}
    stamps = {SRC[k]: sha(v)[:16] for k, v in raw.items()}
    places = {}

    def add(pid, world, kind, title, source, ref):
        if pid in places:
            raise CogxError(f'cognitionx: duplicate place {pid}')
        if not isinstance(title, str) or not title:
            raise CogxError(f'cognitionx: place {pid} has no title')
        places[pid] = {'id': pid, 'world': world, 'kind': kind, 'title': title, 'source': source, 'ref': ref}

    parish_names = {}
    for p in need(reg['layers'], 'parishes', SRC['layers']):
        fips = need(p, 'fips', 'layers parish')
        parish_names[fips] = need(p, 'name', fips)
        for st in need(p, 'stations', fips):
            sid = need(st, 'id', fips)
            add(f'parish:{fips}/{sid}', 'parishes', 'station', need(st, 'title', sid),
                f'{SRC["layers"]}#parishes[fips={fips}].stations[id={sid}]',
                {'fips': fips, 'station': sid, 'layer': need(st, 'layer', sid)})
    for p in need(reg['paths'], 'parishes', SRC['paths']):
        fips = need(p, 'fips', 'paths parish')
        for path in need(p, 'paths', fips):
            pid_ = need(path, 'id', fips)
            for n, step in enumerate(need(path, 'steps', f'{fips}/{pid_}'), 1):
                kind = need(step, 'kind', f'{fips}/{pid_}#{n}')
                if pid_ == 'k12':
                    if kind != 'station':
                        raise CogxError(f'cognitionx: k12 step {fips}#{n} is not a station step')
                    add(f'k12:{fips}/{n}', 'parishes', 'path-step', need(step, 'title', f'k12 {fips}#{n}'),
                        f'{SRC["paths"]}#parishes[fips={fips}].paths[id=k12].steps[{n - 1}]',
                        {'fips': fips, 'path': 'k12', 'n': n, 'station': need(step, 'id', f'k12 {fips}#{n}')})
                elif kind == 'quote':
                    sid = need(step, 'id', f'{fips}/{pid_}#{n}')
                    add(f'path:{fips}/{sid}', 'parishes', 'path-quote', need(step, 'title', sid),
                        f'{SRC["paths"]}#parishes[fips={fips}].paths[id={pid_}].steps[{n - 1}]',
                        {'fips': fips, 'path': pid_, 'n': n, 'step': sid})
    for w in need(reg['wilds'], 'worlds', SRC['wilds']):
        wid = need(w, 'id', 'wilds world')
        for i, site in enumerate(need(w, 'sites', wid)):
            sid = need(site, 'id', wid)
            add(f'wilds:{wid}/{sid}', 'wilds', 'site', need(site, 'title', sid),
                f'{SRC["wilds"]}#worlds[id={wid}].sites[{i}]', {'world': wid, 'site': sid})
    hall_names = {}
    lessons = need(reg['lessons'], 'lessons', SRC['lessons'])
    for lid in sorted(lessons):
        hall_names[need(lessons[lid], 'hall', lid)] = need(lessons[lid], 'hall_name', lid)
    sims = need(reg['sims'], 'sims', SRC['sims'])
    units = {need(u, 'hall', 'schools unit'): u for u in need(reg['schools'], 'units', SRC['schools'])}
    for hall in sorted(hall_names):
        add(f'campus:{hall}', 'campus', 'hall', hall_names[hall], f'{SRC["lessons"]}#lessons[hall={hall}]',
            {'hall': hall})
    for hall, bindings in sorted(need(reg['sims'], 'hall_bindings', SRC['sims']).items()):
        if hall not in hall_names:
            continue        # a seat without a lesson hall has no campus hall place (same as the classroom pack)
        for sim in sorted({need(b, 'sim', hall) for b in bindings}):
            add(f'campus:{hall}/{sim}', 'campus', 'seat', f'{hall_names[hall]}: {need(need(sims, sim, SRC["sims"]), "name", sim)}',
                f'{SRC["sims"]}#hall_bindings.{hall}[sim={sim}]', {'hall': hall, 'sim': sim})
    # classroom modules: one per schools unit, id mod-<hall> (the classroom pack's rule; see COGX_CONTRACT)
    for hall in sorted(units):
        if hall not in hall_names:
            raise CogxError(f'cognitionx: schools unit {hall} has no lesson hall')
        add(f'module:mod-{hall}', 'classroom', 'module', hall_names[hall], f'{SRC["schools"]}#units[hall={hall}]',
            {'module': f'mod-{hall}', 'hall': hall})
    fips_names = {}
    for fips, p in sorted(need(reg['parishes'], 'parishes', SRC['parishes']).items()):
        if need(p, 'fips', fips) != fips:
            raise CogxError(f'cognitionx: {SRC["parishes"]} key {fips} holds fips {p["fips"]}')
        fips_names[fips] = (need(p, 'name', fips), need(p, 'full_name', fips))
    return places, stamps, fips_names, sorted(units)


# ------------------------------------------------------------------ build ---
def la_slug(name):     # apps/louisiana/template.html: n.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/(^-|-$)/g,"")
    return re.sub(r'(^-|-$)', '', re.sub(r'[^a-z0-9]+', '-', name.lower()))


def build(vendored):
    up = read_vendored() if vendored else read_upstream()
    if up['header'] != ['block_id', 'pack', 'track', 'code', 'grade', 'level', 'credential', 'theme',
                        'description', 'transfer_check']:
        raise CogxError(f'cognitionx: blocks.csv header changed: {up["header"]}')
    slug_by_name = {p['name']: p['slug'] for p in up['manifest']['packs']}
    places, stamps, fips_names, unit_halls = smartciti()
    ptok = {pid: tokens(p['title']) for pid, p in places.items()}

    blocks, excluded = [], []
    for r in up['rows']:
        g = r['grade']
        band = g if g in BANDS else SINGLE[g] if g in SINGLE else None
        if band is None:
            excluded.append(r['block_id'])
            continue
        bt, tt = tokens(block_text(r)), tokens(r['theme'])
        hits = sorted(pid for pid, t in ptok.items() if len(bt & t) >= MIN_SHARED and tt & t)
        b = {k: r[k] for k in up['header']}
        halls = {places[p]['ref']['hall'] for p in hits if places[p]['world'] in ('campus', 'classroom')}
        b.update({'pack_slug': slug_by_name[r['pack']], 'band': band,
                  'statement_field': 'description' if r['description'] else 'theme', 'places': hits,
                  'classroom_modules': sorted(f'mod-{h}' for h in halls if h in unit_halls)})
        blocks.append(b)
    blocks.sort(key=lambda b: b['block_id'])

    # Cognition.X modules for the classroom plan builder: the upstream structure, not an invention -
    # one per (pack, track) on tracked packs; the legacy K-12 pack (no tracks) one per derived band.
    cx_modules = {}
    for b in blocks:
        slug = b['pack_slug']
        if b['track']:
            key = (slug, b['track'])
        elif slug == 'K12':
            key = (slug, b['band'])
        else:
            raise CogxError(f'cognitionx: block {b["block_id"]} has no track and is not in the K12 pack')
        cx_modules.setdefault(key, []).append(b['block_id'])
    order = {s: i for i, (s, _) in enumerate(PACKS)}
    modules, seen_n = [], {}
    for (slug, name), ids in sorted(cx_modules.items(), key=lambda kv: (order[kv[0][0]], min(kv[1]))):
        seen_n[slug] = (seen_n[slug] if slug in seen_n else 0) + 1
        bl = [x for x in blocks if x['block_id'] in set(ids)]
        modules.append({'id': f'cx-{slug.lower()}-{seen_n[slug]}', 'pack_slug': slug, 'pack': bl[0]['pack'],
                        'group': 'track' if bl[0]['track'] else 'band', 'name': name,
                        'bands': [bd for bd in BANDS if any(x['band'] == bd for x in bl)],
                        'blocks': sorted(ids), 'mapped_blocks': sum(1 for x in bl if x['places'])})
    mod_of = {bid: m['id'] for m in modules for bid in m['blocks']}
    for b in blocks:
        b['module'] = mod_of[b['block_id']]
    used_places = sorted({p for b in blocks for p in b['places']})

    # Louisiana dashboards
    la_by_name = {need(p, 'name', 'la parish'): p for p in up['la_parishes']}
    la_links, la_missing = [], []
    for fips in sorted(fips_names):
        nm, sc = fips_names[fips]
        if nm not in la_by_name:
            la_missing.append(fips)
            continue
        p = la_by_name[nm]
        la_links.append({'fips': fips, 'smartciti_name': sc, 'dashboard': {
            'name': nm, 'slug': la_slug(nm), 'route': '#/parish/' + la_slug(nm),
            'app': 'apps/louisiana/index.html', 'url': f'{REPO_URL}/blob/{PIN_COMMIT}/apps/louisiana/index.html',
            'seat': need(p, 'seat', nm), 'region': need(p, 'region', nm), 'world': need(p, 'world', nm),
            'districts': need(p, 'districts', nm), 'source': f'apps/louisiana/index.html#parishes[name={nm}]'}})
    if la_missing:
        raise CogxError(f'cognitionx: SmartCiti parishes without a same-name Louisiana dashboard: {la_missing}')

    by = lambda key: {k: sum(1 for b in blocks if b[key] == k) for k in sorted({b[key] for b in blocks})}
    mapped = [b for b in blocks if b['places']]
    counts = {
        'blocks': len(blocks), 'excluded_unbanded': len(excluded),
        'by_band': {bd: sum(1 for b in blocks if b['band'] == bd) for bd in BANDS},
        'by_pack': by('pack_slug'),
        'mapped': len(mapped), 'unmapped': len(blocks) - len(mapped),
        'mapped_by_pack': {s: sum(1 for b in mapped if b['pack_slug'] == s) for s, _ in PACKS},
        'mapped_by_band': {bd: sum(1 for b in mapped if b['band'] == bd) for bd in BANDS},
        'modules': len(modules),
        'places_total': len(places), 'places_used': len(used_places),
        'places_used_by_world': {w: sum(1 for p in used_places if places[p]['world'] == w)
                                 for w in sorted({p['world'] for p in places.values()})},
        'links': sum(len(b['places']) for b in blocks),
        'louisiana_dashboards': len(up['la_parishes']), 'louisiana_linked': len(la_links),
    }
    doc = {
        'pack': 'cognitionx',
        'product': 'COGX·Cognition.X K-12 in SmartCiti.X',
        'source_stamp': sha((HERE / 'build.py').read_bytes())[:16],
        'sources': stamps,
        'upstream': {'repo': REPO_URL, 'commit': PIN_COMMIT, 'files_sha256': dict(PIN_FILES),
                     'vendored_sha256': dict(PIN_VENDOR)},
        'attribution': ATTRIBUTION,
        'honesty': HONESTY,
        'selection': {'packs': [{'slug': s, 'why': w} for s, w in PACKS],
                      'grades': 'K-12 only: tracked bands K–2..11–12 and single grades K..12; other rows excluded',
                      'band_rule': 'data/schema.md level mapping: single grades fold into K–2 / 3–5 / 6–8 / '
                                   '9–10 / 11–12; statement = description, or theme where description is empty'},
        'bands': BANDS,
        'mapping_rule': MATCH_RULE,
        'louisiana': {'rule': 'parishes/registry/parishes.json name (the Census NAME, e.g. "St. Bernard") equals the app '
                              'parish name exactly; slug and route '
                              'as apps/louisiana/template.html builds them',
                      'links': la_links},
        'counts': counts,
        'modules': modules,
        'places': [places[p] for p in used_places],
        'blocks': blocks,
    }
    return doc, up


def write_vendor(up):
    VENDOR.mkdir(exist_ok=True)
    buf = io.StringIO(newline='')
    w = csv.DictWriter(buf, fieldnames=up['header'], lineterminator='\n')
    w.writeheader()
    for r in sorted(up['rows'], key=lambda r: r['block_id']):
        w.writerow(r)
    files = {
        'vendor/blocks_subset.csv': buf.getvalue().encode('utf-8'),
        'vendor/louisiana_parishes.json': (json.dumps({'source': 'apps/louisiana/index.html embedded "parishes" '
                                                                 'array; fields ' + ', '.join(LA_FIELDS) + ' verbatim', 'commit': PIN_COMMIT,
                                                       'parishes': up['la_parishes']},
                                                      indent=1, ensure_ascii=False) + '\n').encode('utf-8'),
        'vendor/manifest_subset.json': (json.dumps(up['manifest'], indent=1, ensure_ascii=False) + '\n').encode('utf-8'),
        'vendor/LICENSE-CONTENT': up['license'],
    }
    for rel, b in files.items():
        if PIN_VENDOR[rel] != sha(b):
            raise CogxError(f'cognitionx: vendored {rel} would be {sha(b)}, pinned {PIN_VENDOR[rel]} '
                            f'(update PIN_VENDOR after reviewing the change)')
        (HERE / rel).write_bytes(b)


def main():
    vendored = '--vendored' in sys.argv
    doc, up = build(vendored)
    text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    if '--check' in sys.argv:
        if OUT.read_text(encoding='utf-8') != text:
            raise CogxError('cognitionx: registry/cognitionx.json is stale; rerun python3 cognitionx/build.py')
        print('cognitionx: registry up to date')
        return
    if not vendored:
        write_vendor(up)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    c = doc['counts']
    print(f"cognitionx: {c['blocks']} blocks ({c['mapped']} mapped, {c['unmapped']} unmapped) | "
          f"{c['places_used']}/{c['places_total']} places | LA {c['louisiana_linked']}/{c['louisiana_dashboards']} | "
          f"stamp {doc['source_stamp']}")


if __name__ == '__main__':
    try:
        main()
    except CogxError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
