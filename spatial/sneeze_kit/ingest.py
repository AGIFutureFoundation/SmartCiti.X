#!/usr/bin/env python3
"""
Record a real run of the world tiles in Sneeze or Artemis into spatial/registry/sneeze_runs.json.

  python3 spatial/sneeze_kit/ingest.py my-run.json              # validate, record, update the status tables
  python3 spatial/sneeze_kit/ingest.py my-run.json --dry-run    # say what would happen, write nothing
  python3 spatial/sneeze_kit/ingest.py my-run.json --screens DIR   # also check each screenshot hash has a file in DIR
  python3 spatial/sneeze_kit/ingest.py --recompute              # rebuild the tables from the stored runs (also creates the empty file)
  python3 spatial/sneeze_kit/ingest.py --check                  # exit 1 if the stored tables differ from what the runs give

WHAT IT ENFORCES
  REFUSES (nothing is written): no person; a placeholder person/date/OS/version; no engine version AND no
  commit; a date in the future; a run whose pre-flight did not pass, or whose tile/manifest hashes differ from
  spatial/registry/tiles.json (a different build) unless --allow-other-build, which records it and flips
  nothing; an unknown manifest, tile or field; a field marked observed/contradicted without written evidence
  and at least one declared screenshot hash; a screenshot hash that is not declared; a run that observed nothing;
  the same run twice; anything the schema (results.schema.json) rejects.
  FLIPS only a registry field that is "proposed", only when the run says "observed" with evidence AND the per-tile
  observations in the same run support it (PREREQ below) -> "observed in <Engine> <version>". A field with no rule
  here, a "documented" field, and a field whose prerequisites are unmet are left as they are, with the reason
  stored. The word "claimed" is never written by this script: no input can produce it.
  Screenshots are referenced by sha256; the images are not stored. The run file is a person's report, not
  tamper-proof: the registry records it as reported by <person>, nothing more.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as C  # noqa: E402

RUNS_SCHEMA = 'smartcitix-sneeze-runs/1'
EARLIEST = datetime.date(2026, 6, 15)   # Sneeze was introduced on this date (tiles.json / the wiki cite the press release)
MIN_EVIDENCE = 10
BIG_TILE_KM = 10.0                      # the proposed-field row speaks of 10-100 km extents


# ------------------------------------------------------------------ schema ---
def validate(schema, data, path='$'):
    """The subset of JSON Schema the results schema uses. Returns a list of error strings."""
    errs = []
    if 'const' in schema and data != schema['const']:
        return [f'{path}: must be {schema["const"]!r}']
    if 'enum' in schema and data not in schema['enum']:
        return [f'{path}: {data!r} is not one of {schema["enum"]}']
    t = schema.get('type')
    pytypes = {'object': dict, 'array': list, 'string': str, 'boolean': bool}
    if t and (not isinstance(data, pytypes[t]) or (t != 'boolean' and isinstance(data, bool))):
        return [f'{path}: must be a {t}']
    if t == 'string':
        if len(data) < schema.get('minLength', 0):
            errs.append(f'{path}: too short (minimum {schema["minLength"]} characters)')
        if len(data) > schema.get('maxLength', 10 ** 9):
            errs.append(f'{path}: too long (maximum {schema["maxLength"]} characters)')
        if 'pattern' in schema and not re.search(schema['pattern'], data):
            errs.append(f'{path}: {data[:40]!r} does not match {schema["pattern"]}')
    elif t == 'array':
        if len(data) < schema.get('minItems', 0):
            errs.append(f'{path}: needs at least {schema["minItems"]} item(s)')
        for i, x in enumerate(data):
            errs += validate(schema.get('items', {}), x, f'{path}[{i}]')
    elif t == 'object':
        props = schema.get('properties', {})
        for k in schema.get('required', []):
            if k not in data:
                errs.append(f'{path}.{k}: required')
        addl = schema.get('additionalProperties', True)
        for k, v in data.items():
            if k in props:
                errs += validate(props[k], v, f'{path}.{k}')
            elif addl is False:
                errs.append(f'{path}.{k}: not a field of this format')
            elif isinstance(addl, dict):
                errs += validate(addl, v, f'{path}.{k}')
    return errs


# ------------------------------------------------------------- run labels ---
def version_text(run):
    e = run['engine']
    v = (e.get('version') or '').strip()
    c = (e.get('commit') or '').strip()
    if v and c:
        return f'{v} (commit {c[:12]})'
    return v or f'commit {c[:12]}'


def label(run):
    return f'{run["engine"]["name"]} {version_text(run)}'


# --------------------------------------------------------- semantic checks ---
def check_run(run, tiles, today, screens_dir=None, allow_other_build=False):
    """Return (errors, build_match). Errors are refusals."""
    errs = validate(json.loads(C.SCHEMA_FILE.read_text(encoding='utf-8')), run)
    if errs:
        return errs, False
    e = errs.append
    name = run['person']['name'].strip()
    if C.is_placeholder(name):
        e('person.name: a real name or public handle is required (no placeholder)')
    elif re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+', name):
        e('person.name: give a name or handle, not an email address (this registry is public)')
    for k in ('name', 'version'):
        if C.is_placeholder(run['os'][k]):
            e(f'os.{k}: required (no placeholder)')
    eng = run['engine']
    ver = (eng.get('version') or '').strip()
    if ver and C.is_placeholder(ver):
        e('engine.version: still a placeholder; give the real version, or delete the line and give engine.commit')
    if not ver and not eng.get('commit'):
        e('engine: a version or a commit is required (Sneeze has no published release; give the commit you built)')
    for k in ('repo_commit',):
        if C.is_placeholder(run['build'][k]) or not re.fullmatch(r'[0-9a-f]{7,40}', run['build'][k]):
            e(f'build.{k}: give the git commit hash of the checkout the tiles were built from')
    try:
        d = datetime.date.fromisoformat(run['date'])
        if d > today + datetime.timedelta(days=1):
            e(f'date: {run["date"]} is in the future')
        if d < EARLIEST:
            e(f'date: {run["date"]} is before Sneeze existed ({EARLIEST})')
    except ValueError:
        e(f'date: {run["date"]!r} is not a real calendar date')

    reg_man = {m['id']: m for m in tiles['manifests']}
    reg_tile = {t['id']: t for t in tiles['tiles']}
    table = C.field_table(tiles)
    declared = {}
    for i, s in enumerate(run['screenshots']):
        if s['sha256'] in declared:
            e(f'screenshots[{i}]: sha256 declared twice')
        declared[s['sha256']] = s
        if C.is_placeholder(s['caption']):
            e(f'screenshots[{i}].caption: describe what the picture shows')
    if screens_dir is not None:
        have = set()
        sd = pathlib.Path(screens_dir)
        for f in sorted(sd.iterdir())[:500] if sd.is_dir() else []:
            if f.is_file():
                have.add(C.sha256_file(f))
        for h in declared:
            if h not in have:
                e(f'screenshots: no file with sha256 {h[:12]}.. in {screens_dir}')

    def refs_ok(where, hs):
        for h in hs or []:
            if h not in declared:
                e(f'{where}: screenshot {h[:12]}.. is not declared in "screenshots"')

    # ---- build identity: the run must be of the build the registry records
    pf = run['preflight']
    match = True
    if not pf['passed']:
        e('preflight.passed is false: fix the build and run preflight.py again before reporting a run')
    if pf['tiles_source_stamp'] != tiles['source_stamp'] or run['build']['tiles_source_stamp'] != tiles['source_stamp']:
        match = False
    seen_m = set()
    for mi, mo in enumerate(run['manifests']):
        w = f'manifests[{mi}]({mo["id"]})'
        if mo['id'] not in reg_man:
            e(f'{w}: not a manifest in tiles.json')
            continue
        if mo['id'] in seen_m:
            e(f'{w}: manifest reported twice')
        seen_m.add(mo['id'])
        if pf['manifest_sha256'].get(mo['id']) != reg_man[mo['id']]['sha256']:
            match = False
        for tid in reg_man[mo['id']]['tiles']:
            if pf['tile_sha256'].get(tid) != reg_tile[tid]['sha256']:
                match = False
        refs_ok(w, mo.get('screenshots'))
        seen_t = set()
        for ti, to in enumerate(mo['tiles']):
            tw = f'{w}.tiles[{ti}]({to["tile"]})'
            if to['tile'] not in reg_man[mo['id']]['tiles']:
                e(f'{tw}: not a tile of this manifest')
            if to['tile'] in seen_t:
                e(f'{tw}: tile reported twice')
            seen_t.add(to['tile'])
            refs_ok(tw, to.get('screenshots'))
            vals = [to[k] for k in ('appears', 'orientation', 'scale', 'child_position', 'smooth')]
            observed = any(v in ('pass', 'fail') for v in vals)
            if mo['loaded'] == 'untested' and observed:
                e(f'{tw}: observations given but the manifest says loaded: "untested"')
            if mo['loaded'] == 'no' and 'pass' in vals:
                e(f'{tw}: a "pass" on a manifest reported as not loaded')
            if to['appears'] in ('fail', 'untested', 'not_applicable') and any(v == 'pass' for v in (to['orientation'], to['scale'], to['smooth'])):
                e(f'{tw}: orientation/scale/smooth cannot pass when the tile does not appear')
        if mo['geopose_anchor_read'] == 'yes' and mo['loaded'] not in ('yes', 'partial'):
            e(f'{w}: geopose_anchor_read "yes" needs the manifest loaded')
    if not any(mo['loaded'] != 'untested' for mo in run['manifests']):
        e('manifests: the run observed nothing (every manifest is "untested")')
    if not match and not allow_other_build:
        e('build: the hashes in this run do not equal spatial/registry/tiles.json (a different build was tested). '
          'Rebuild with python3 spatial/build.py, run preflight.py and test again; or pass --allow-other-build to record it without flipping anything')

    # ---- fields
    seen_f = set()
    for fi, f in enumerate(run.get('fields', [])):
        w = f'fields[{fi}]({f["field"]})'
        if f['field'] not in table:
            e(f'{w}: not a field in tiles.json#field_status')
            continue
        if f['field'] in seen_f:
            e(f'{w}: field reported twice')
        seen_f.add(f['field'])
        refs_ok(w, f.get('screenshots'))
        if f['verdict'] in ('observed', 'contradicted'):
            ev = (f.get('evidence') or '').strip()
            if len(ev) < MIN_EVIDENCE or C.is_placeholder(ev):
                e(f'{w}: "{f["verdict"]}" needs written evidence (at least {MIN_EVIDENCE} characters saying what you saw)')
            if not f.get('screenshots'):
                e(f'{w}: "{f["verdict"]}" needs at least one screenshot hash')
    return errs, match


# -------------------------------------------------------- field outcomes ---
def _iter_tiles(run, tiles):
    reg_tile = {t['id']: t for t in tiles['tiles']}
    reg_man = {m['id']: m for m in tiles['manifests']}
    for mo in run['manifests']:
        for to in mo['tiles']:
            yield mo, to, reg_tile[to['tile']], reg_man[mo['id']]


def _loaded(mo):
    return mo['loaded'] == 'yes'


def pre_anchors(run, tiles):
    for mo in run['manifests']:
        m = next(x for x in tiles['manifests'] if x['id'] == mo['id'])
        if _loaded(mo) and any(next(t for t in tiles['tiles'] if t['id'] == i)['anchor'] for i in m['tiles']):
            return True, ''
    return False, 'needs a manifest with GeoPose anchors reported as fully loaded (loaded: "yes")'


def pre_provenance(run, tiles):
    if any(_loaded(mo) for mo in run['manifests']):
        return True, ''
    return False, 'needs a manifest reported as fully loaded (loaded: "yes")'


def pre_enu(run, tiles):
    for mo in run['manifests']:
        m = next(x for x in tiles['manifests'] if x['id'] == mo['id'])
        if not _loaded(mo) or len(m['tiles']) < 2:
            continue
        kids = [to for to in mo['tiles'] if to['tile'] != m['tiles'][0]]
        root = [to for to in mo['tiles'] if to['tile'] == m['tiles'][0]]
        if kids and root and root[0]['appears'] == 'pass' and all(k['appears'] == 'pass' and k['child_position'] == 'pass' for k in kids):
            return True, ''
    return False, 'needs a loaded multi-tile manifest (parishes or bayarea) where the first tile and every other tile appears and every child_position is "pass"'


def pre_geopose(run, tiles):
    if any(_loaded(mo) and mo['geopose_anchor_read'] == 'yes' for mo in run['manifests']):
        return True, ''
    return False, 'needs a loaded manifest with geopose_anchor_read "yes"'


def pre_scale(run, tiles):
    for mo, to, t, _ in _iter_tiles(run, tiles):
        e, _, n = C.kilometres(t)
        if _loaded(mo) and max(e, n) >= BIG_TILE_KM and to['appears'] == 'pass' and to['scale'] == 'pass':
            return True, ''
    return False, f'needs a tile at least {BIG_TILE_KM:.0f} km across that appears and has scale "pass"'


def pre_frame(run, tiles):
    big = max(tiles['tiles'], key=lambda t: t['bytes'])['id']
    for mo, to, t, _ in _iter_tiles(run, tiles):
        if t['id'] == big and _loaded(mo) and to['appears'] == 'pass' and to['smooth'] == 'pass':
            return True, ''
    return False, f'needs the largest tile ({big}) to appear and be "smooth": "pass"'


def never(why):
    return lambda run, tiles: (False, why)


# Rules keyed by the registry's exact field text. A proposed field with no rule here is never flipped.
PREREQ = {
    'manifest.Data.Anchors (GeoPose sidecar)': pre_anchors,
    'manifest.Data.Provenance (sidecar)': pre_provenance,
    'world horizontal axes are east/north (ENU)': pre_enu,
    'GeoPose anchor consumed by any Sneeze component': pre_geopose,
    'attaching one manifest to another (child fabrics)': never('no manifest built here attaches another, so this kit cannot show it'),
    'camera / render scale at 10-100 km tile extents': pre_scale,
    "a tile this size loads inside Sneeze's frame budget": pre_frame,
    'signing (JWS, X.509 chain)': never('no signed manifest is built here, so this kit cannot show it'),
}


# What "observed" means for each proposed field - stated on the status row so nobody reads more into it.
OBSERVED_MEANS = {
    'manifest.Data.Anchors (GeoPose sidecar)': 'the engine loaded a manifest that carries the Data.Anchors block without error; it does NOT mean the engine uses the block',
    'manifest.Data.Provenance (sidecar)': 'the engine loaded a manifest that carries the Data.Provenance block without error; it does NOT mean the engine uses the block',
    'world horizontal axes are east/north (ENU)': 'in a loaded multi-tile manifest every tile appeared and sat where its recorded east/north offset puts it relative to the first tile, as seen on screen',
    'GeoPose anchor consumed by any Sneeze component': 'the person saw the engine use Data.Anchors (place the world by it, display it or log it)',
    'attaching one manifest to another (child fabrics)': 'cannot be observed with the manifests built here',
    'camera / render scale at 10-100 km tile extents': 'a tile at least 10 km across appeared and the person judged its size to match the checklist table',
    "a tile this size loads inside Sneeze's frame budget": 'the largest tile appeared and the camera stayed smooth on one person\'s machine in one run',
    'signing (JWS, X.509 chain)': 'cannot be observed with the manifests built here (none is signed)',
}


def field_outcomes(run, tiles, build_match):
    """{field: outcome string} for every field the run reports. Outcomes:
    'flipped' (observed, proposed field, evidence, prerequisites met), 'contradicted',
    or 'kept: <reason>'. Pure function of the run and the registry."""
    table = C.field_table(tiles)
    out = {}
    for f in run.get('fields', []):
        name, v = f['field'], f['verdict']
        if v == 'untested':
            continue
        if not build_match:
            out[name] = 'kept: the run tested a different build than the registry records'
        elif table[name] != 'proposed':
            out[name] = 'kept: already documented, nothing to flip'
        elif v == 'not_observed':
            out[name] = 'kept: looked for, not seen'
        elif v == 'contradicted':
            out[name] = 'contradicted'
        else:
            rule = PREREQ.get(name)
            if rule is None:
                out[name] = 'kept: no automatic rule for this field; review by hand'
            else:
                ok, why = rule(run, tiles)
                out[name] = 'flipped' if ok else f'kept: {why}'
    return out


# ------------------------------------------------------- derived tables ---
def derive(tiles, records):
    """Status tables as a pure function of the stored run records and the registry."""
    table = C.field_table(tiles)
    good = [r for r in records if r['build_match']]
    fields = []
    for f in tiles['field_status']:
        name = f['field']
        obs = sorted({label(r['run']) for r in good if r['field_outcomes'].get(name) == 'flipped'})
        con = sorted({label(r['run']) for r in good if r['field_outcomes'].get(name) == 'contradicted'})
        ids = sorted(r['run_id'] for r in good if r['field_outcomes'].get(name) in ('flipped', 'contradicted'))
        if table[name] != 'proposed':
            st = table[name]
        elif obs and con:
            st = f'disputed: observed in {", ".join(obs)}; contradicted in {", ".join(con)}'
        elif obs:
            st = f'observed in {", ".join(obs)}'
        elif con:
            st = f'contradicted in {", ".join(con)}'
        else:
            st = 'proposed'
        row = {'field': name, 'registry_status': table[name], 'status': st, 'run_ids': ids}
        if table[name] == 'proposed' and name in OBSERVED_MEANS:
            row['observed_means'] = OBSERVED_MEANS[name]
        fields.append(row)
    mans = []
    for m in tiles['manifests']:
        parts, ids = [], []
        for word, tag in (('yes', 'observed loaded in'), ('partial', 'observed partly loaded in'), ('no', 'tried and did not load in')):
            ls = sorted({label(r['run']) for r in good for mo in r['run']['manifests'] if mo['id'] == m['id'] and mo['loaded'] == word})
            if ls:
                parts.append(f'{tag} {", ".join(ls)}')
        for r in good:
            if any(mo['id'] == m['id'] and mo['loaded'] != 'untested' for mo in r['run']['manifests']):
                ids.append(r['run_id'])
        mans.append({'id': m['id'], 'status': '; '.join(parts) if parts else m['status'], 'run_ids': sorted(ids)})
    tl = []
    for t in tiles['tiles']:
        checks = {}
        for k in ('appears', 'orientation', 'scale', 'child_position', 'smooth'):
            d = {'pass': set(), 'fail': set()}
            for r in good:
                for mo in r['run']['manifests']:
                    for to in mo['tiles']:
                        if to['tile'] == t['id'] and to[k] in d:
                            d[to[k]].add(label(r['run']))
            checks[k] = {w: sorted(s) for w, s in d.items() if s}
        seen = checks['appears'].get('pass')
        tl.append({'tile': t['id'], 'status': f'observed appearing in {", ".join(seen)}' if seen else t['status'], 'checks': {k: v for k, v in checks.items() if v}})
    return fields, mans, tl


def document(tiles, records):
    f, m, t = derive(tiles, records)
    good = [r for r in records if r['build_match']]
    return {
        'schema': RUNS_SCHEMA,
        'about': 'Runs of the Sneeze world tiles by people who had Sneeze or Artemis, as REPORTED by them (not tamper-proof). '
                 'Written only by spatial/sneeze_kit/ingest.py. The status tables below are a function of the runs: '
                 '"proposed" until a run observed it, then "observed in <engine> <version>"; no stronger word is ever written. '
                 'With run_count 0 nothing has been loaded in Sneeze or Artemis.',
        'run_count': len(records),
        'runs_on_the_recorded_build': len(good),
        'runs': records,
        'field_status': f,
        'manifest_status': m,
        'tile_status': t,
    }


def load_records(path):
    p = pathlib.Path(path)
    if not p.is_file():
        return []
    d = C.load_json(p)
    return d.get('runs', [])


def write_atomic(path, doc):
    p = pathlib.Path(path)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.sneeze_runs.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + '\n')
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def run_id(run):
    return hashlib.sha256(C.canonical(run).encode()).hexdigest()[:16]


def pages_to_update(root):
    hits = []
    p = root / 'wiki' / 'Spatial-Fabric.md'
    if p.is_file() and 'not loaded' in p.read_text(encoding='utf-8'):
        hits.append('wiki/Spatial-Fabric.md')
    return hits + ['the status strings in spatial/tiles.py, and the pages built from spatial/registry/tiles.json']


def main(argv=None):
    ap = argparse.ArgumentParser(description='Record a Sneeze/Artemis run into spatial/registry/sneeze_runs.json.')
    ap.add_argument('run', nargs='?', help='the filled-in results file')
    ap.add_argument('--registry', default=None)
    ap.add_argument('--runs', default=None, help='the runs file to update (default spatial/registry/sneeze_runs.json)')
    ap.add_argument('--screens', default=None, help='folder of screenshot files; each declared hash must match a file in it')
    ap.add_argument('--allow-other-build', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--recompute', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--today', default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    tiles = C.load_tiles(a.registry)
    runs_path = pathlib.Path(a.runs) if a.runs else C.DEFAULT_RUNS
    records = load_records(runs_path)

    if a.check:
        stored = C.load_json(runs_path) if runs_path.is_file() else None
        want = document(tiles, records)
        ok = stored == want
        for r in records:
            if r['run_id'] != run_id(r['run']):
                ok = False
                print(f'FAIL run {r["run_id"]}: stored run does not hash to its id')
            if r['field_outcomes'] != field_outcomes(r['run'], tiles, r['build_match']):
                ok = False
                print(f'FAIL run {r["run_id"]}: stored field outcomes differ from what the rules give')
        print('  ok sneeze_runs.json equals what its runs derive' if stored == want else 'FAIL sneeze_runs.json differs from what its runs derive (run ingest.py --recompute)')
        return 0 if ok else 1
    if a.recompute:
        for r in records:
            r['field_outcomes'] = field_outcomes(r['run'], tiles, r['build_match'])
        write_atomic(runs_path, document(tiles, records))
        print(f'recomputed {runs_path.name}: {len(records)} run(s)')
        return 0
    if not a.run:
        ap.error('give the results file, or --recompute / --check')
    try:
        run = C.load_json(a.run)
    except (OSError, ValueError) as ex:
        print(f'REFUSED: cannot read {a.run}: {ex}', file=sys.stderr)
        return 1
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.datetime.now(datetime.timezone.utc).date()
    errs, match = check_run(run, tiles, today, a.screens, a.allow_other_build)
    if errs:
        print(f'REFUSED: {len(errs)} problem(s); nothing was written', file=sys.stderr)
        for x in errs:
            print('  - ' + x, file=sys.stderr)
        return 1
    rid = run_id(run)
    if any(r['run_id'] == rid for r in records):
        print(f'REFUSED: this exact run ({rid}) is already recorded; nothing was written', file=sys.stderr)
        return 1
    rec = {'run_id': rid, 'build_match': match, 'field_outcomes': field_outcomes(run, tiles, match), 'run': run}
    records = sorted(records + [rec], key=lambda r: (r['run']['date'], r['run_id']))
    doc = document(tiles, records)
    flipped = [k for k, v in rec['field_outcomes'].items() if v == 'flipped']
    print(f'run {rid} by {run["person"]["name"].strip()} on {run["date"]} in {label(run)}: ' + ('recorded' if not a.dry_run else 'would be recorded (dry run)'))
    if not match:
        print('  build differs from the registry: recorded, nothing flipped')
    for k, v in sorted(rec['field_outcomes'].items()):
        print(f'  field {k}: {v}')
    print(f'  flipped from proposed: {len(flipped)}')
    if not a.dry_run:
        write_atomic(runs_path, doc)
        print(f'wrote {runs_path.name}: {doc["run_count"]} run(s)')
        if flipped or any(mo['loaded'] != 'untested' for mo in run['manifests']):
            print('The pages still say "not loaded in Sneeze or Artemis" until their builders read this file. Review: ' + '; '.join(pages_to_update(C.ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
