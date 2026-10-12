#!/usr/bin/env python3
"""The Omega Claw registry: robotics/claw/registry/claw.json (CLAW, wave 18).

Two things, both built from what the repo already has:

  * AGENTS - five SCRIPTED orchestration figures (Scheduler, Referee, Data Steward, Evaluator, Coach). No AI model runs
    behind any of them. Personalities and base voice settings are AUTHORED in robotics/claw/authored/claw.json; voices
    use the device's own speech synthesis, on a click only, inside the Omega Hive bounds (hive/registry/hive.json).
    Every line is either QUOTED character-for-character from the registry path printed beside it (re-read here) or a
    TEMPLATE whose every slot is a MEASURED number filled by robotics/claw/core.mjs.
  * DATASETS - the index of an instruction-conditioned robot-learning dataset: one sample per robokit task x
    curriculum level x declared seed, produced headless by the SCRIPTED reference policy (the page simulator's own
    SIM_CORE, via robotics/claw/node.mjs). Instructions are quoted from robotics/, tasks/, lessons/, stations/ and
    restoration/ registries. Splits by seed and by task family, dedupe by trajectory hash, per-sample provenance,
    class-balance weights and a dataset card in the tc-dataset/1 sections; robotics/claw/export.mjs writes the files.

NOTHING HERE TRAINS A MODEL - no LLM, no VLA, no controller. trained_models stays 0.

Fails closed: a missing field, an unresolvable source, a line that is not its source, a voice outside the Hive bounds
or a failing dataset check stops the build with a named error. `--check` rebuilds in memory and fails if stale.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'registry' / 'claw.json'
AUTH_REL = 'robotics/claw/authored/claw.json'


def need(cond, msg):
    if not cond:
        raise SystemExit(f'claw: {msg}')


_cache = {}


def load(rel):
    if rel not in _cache:
        p = ROOT / rel
        need(p.is_file(), f'missing {rel}')
        _cache[rel] = json.loads(p.read_text())
    return _cache[rel]


_TOK = re.compile(r'\.?([A-Za-z0-9_\-]+)|\[(\d+)\]|\["([^"]+)"\]|\[([A-Za-z_]+)=([^\]]+)\]')


def resolve(ref):
    need('#' in ref, f'source {ref!r} names no path')
    rel, path = ref.split('#', 1)
    node, pos = load(rel), 0
    while pos < len(path):
        m = _TOK.match(path, pos)
        need(m is not None and m.end() > pos, f'bad source path {ref}')
        key, idx, qkey, fk, fv = m.groups()
        if idx is not None:
            need(isinstance(node, list) and int(idx) < len(node), f'source path {ref}: no index {idx}')
            node = node[int(idx)]
        elif fk is not None:
            need(isinstance(node, list), f'source path {ref}: [{fk}=..] on a non-list')
            hit = [x for x in node if isinstance(x, dict) and str(x.get(fk)) == fv]
            need(len(hit) == 1, f'source path {ref}: {len(hit)} entries with {fk}={fv}')
            node = hit[0]
        else:
            k = qkey if qkey is not None else key
            need(isinstance(node, dict) and k in node, f'source path {ref}: no key {k}')
            node = node[k]
        pos = m.end()
    return node


def quote(ref):
    t = resolve(ref)
    need(isinstance(t, str) and t.strip(), f'{ref} is not a non-empty string')
    return t


def stamp(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:16]


A = load(AUTH_REL)
HIVE = load('hive/registry/hive.json')
BOUNDS = HIVE['bounds']
HOLD = HIVE['k12']['hold_words']
REG = load('robotics/registry/robotics.json')

ROLES = ['scheduler', 'referee', 'steward', 'evaluator', 'coach']
need(sorted(A['agents']) == sorted(ROLES), f'agents must be exactly {ROLES}')
agents = []
for rid in ROLES:
    a = A['agents'][rid]
    for k in ('name', 'glyph', 'job', 'traits', 'style', 'voice', 'k12', 'lines'):
        need(k in a, f'agent {rid} lacks {k!r}')
    v = a['voice']
    need(BOUNDS['pitch'][0] <= v['pitch'] <= BOUNDS['pitch'][1], f'agent {rid} pitch {v["pitch"]} is outside the Hive bounds {BOUNDS["pitch"]}')
    need(BOUNDS['rate'][0] <= v['rate'] <= BOUNDS['rate'][1], f'agent {rid} rate {v["rate"]} is outside the Hive bounds {BOUNDS["rate"]}')
    lines = []
    for ln in a['lines']:
        need('id' in ln, f'agent {rid}: a line lacks an id')
        if 'source' in ln:
            need('template' not in ln, f'{rid}.{ln["id"]}: a line is quoted or templated, not both')
            text = quote(ln['source'])
            k12 = not any(re.search(r'\b' + re.escape(w) + r'\b', text, re.I) for w in HOLD)
            lines.append({'id': ln['id'], 'kind': 'quoted', 'text': text, 'source': ln['source'], 'k12': k12})
        else:
            need('template' in ln and 'slots' in ln, f'{rid}.{ln["id"]}: neither a source nor a template')
            used = set(re.findall(r'\{(\w+)\}', ln['template']))
            need(used == set(ln['slots']), f'{rid}.{ln["id"]}: template slots {sorted(used)} != declared {sorted(ln["slots"])}')
            need(all(k == 'n' for k in ln['slots'].values()), f'{rid}.{ln["id"]}: every slot must be a measured number (n)')
            lines.append({'id': ln['id'], 'kind': 'template', 'template': ln['template'], 'slots': ln['slots'],
                          'source': f'{AUTH_REL}#agents.{rid}.lines[{a["lines"].index(ln)}].template', 'provenance': 'AUTHORED words, MEASURED numbers',
                          'k12': not any(re.search(r'\b' + re.escape(w) + r'\b', ln['template'], re.I) for w in HOLD)})
    agents.append({'id': 'claw:' + rid, 'role': rid, 'name': a['name'], 'glyph': a['glyph'], 'job': a['job'],
                   'personality': {'traits': a['traits'], 'style': a['style'], 'provenance': 'AUTHORED'},
                   'voice': {'pitch': v['pitch'], 'rate': v['rate'], 'volume': BOUNDS['volume'], 'lang': A['voice']['lang'],
                             'engine': A['voice']['engine'], 'on_device_only': True, 'on_click_only': True, 'provenance': 'AUTHORED base'},
                   'k12': a['k12'], 'model': None, 'lines': lines})

# coach rules: AUTHORED words, play-safe in classroom mode
for i, r in enumerate(A['coach']['rules']):
    for k in ('id', 'when', 'next', 'say', 'k12'):
        need(k in r, f'coach rule {i} lacks {k!r}')
    need(r['next'] in ('same', 'up', 'practice'), f'coach rule {r["id"]}: next must be same, up or practice')
    need(not any(re.search(r'\b' + re.escape(w) + r'\b', r['say'], re.I) for w in HOLD) or not r['k12'], f'coach rule {r["id"]} is marked k12 but holds a held word')
for e in A['coach']['ladder']:
    need(e in REG['envs'] and REG['envs'][e]['runner'] == 'robokit', f'coach ladder: {e} is not a robokit env')

# the dataset index: node runs the page simulator's SIM_CORE (via robotics/bench.mjs) and every dataset check
res = subprocess.run(['node', str(HERE / 'node.mjs'), '--index'], capture_output=True, text=True, cwd=ROOT)
need(res.returncode == 0, f'node.mjs --index failed:\n{res.stderr[-3000:]}')
IDX = json.loads(res.stdout)

# the orchestrated tournament on the ARENA harness (robotics/arena/harness.mjs, imported, never edited here)
res = subprocess.run(['node', str(HERE / 'arena_adapter.mjs')], capture_output=True, text=True, cwd=ROOT)
need(res.returncode == 0, f'arena_adapter.mjs failed:\n{res.stderr[-3000:]}')
TOUR = json.loads(res.stdout)
need(TOUR['referee_disagreements'] == 0, f'the Referee disagrees with {TOUR["referee_disagreements"]} harness outcomes')

SOURCES = [AUTH_REL, 'robotics/registry/robotics.json', 'training/registry/training.json', 'datashare/registry/datashare.json',
           'datashare/revocations.json', 'hive/registry/hive.json', 'tasks/registry/tasks.json', 'lessons/registry/lessons.json',
           'stations/registry/stations.json', 'restoration/registry/scenarios.json', 'robotics/claw/core.mjs', 'robotics/claw/node.mjs',
           'web/robokit.py', 'robotics/claw/arena_adapter.mjs', 'robotics/arena/harness.mjs', 'robotics/arena/policies.js']
SOURCES += [s for s in ['robotics/arena/registry/models.json'] if (ROOT / s).is_file()]   # the arena's model registry, once it exists
stamps = {s: stamp(s) for s in SOURCES}
reg = {
    'pack': 'smartcitix-robotics-claw', 'name': 'Omega Claw', 'schema': 'claw/1',
    'source_stamp': hashlib.sha256(json.dumps(stamps, sort_keys=True).encode()).hexdigest()[:16],
    'source_stamps': stamps,
    'honesty': {
        'scripted': 'Every Omega Claw agent is SCRIPTED: each line is quoted verbatim from the registry path beside it, or is an AUTHORED template whose every number is measured. Nothing is generated.',
        'no_model': 'No AI model runs behind any agent. Voices are the device\'s own speech synthesis, on a click only; nothing is sent anywhere.',
        'trained': 'THIS PACK TRAINS NOTHING. These datasets are for training a robot-learning model elsewhere; robotics/claw trains no LLM, no VLA and no controller, and no language model is trained or used. '
                   f'The robotics registry counts {REG["counts"]["trained_models"]} trained model(s) in the whole repo, none trained by this pack (robotics/registry/robotics.json#counts.trained_models).',
        'demonstrations': 'The trajectories are demonstrations of one hand-written SCRIPTED policy in AUTHORED, SCHEMATIC arenas, not learned behaviour and not a real robot.',
        'learner_data': 'Learner episodes merge in only through the datashare intake rules (robot-training consent scope, revocation list). This pack collects nothing.',
    },
    'voice_bounds': {'pitch': BOUNDS['pitch'], 'rate': BOUNDS['rate'], 'source': 'hive/registry/hive.json#bounds'},
    'k12_hold_words_source': 'hive/registry/hive.json#k12.hold_words',
    'agents': agents,
    'families': A['families'], 'splits': A['splits'], 'balance': A['balance'], 'provenance_fields': A['provenance_fields'],
    'metrics': A['metrics'], 'coach': A['coach'],
    'dataset': IDX['index'], 'card': IDX['card'], 'reference_paths': IDX['reference_paths'], 'tournament': TOUR,
    'counts': {'agents': len(agents), 'lines': sum(len(a['lines']) for a in agents),
               'quoted': sum(1 for a in agents for l in a['lines'] if l['kind'] == 'quoted'),
               'templates': sum(1 for a in agents for l in a['lines'] if l['kind'] == 'template'),
               'samples': IDX['index']['samples'], 'tasks': len(IDX['index']['per_task']), 'families': len(A['families']),
               'coach_rules': len(A['coach']['rules']), 'tournament_runs': TOUR['queue_size'], 'policies': len(TOUR['policies']), 'models': 0, 'trained_by_this_pack': 0, 'repo_trained_models': REG['counts']['trained_models']},
}
text = json.dumps(reg, indent=1, ensure_ascii=False) + '\n'
if '--check' in sys.argv:
    need(OUT.is_file() and OUT.read_text() == text, 'robotics/claw/registry/claw.json is stale - run python3 robotics/claw/build.py')
    print(f'claw: registry current ({reg["source_stamp"]})')
else:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f'claw: wrote {OUT.relative_to(ROOT)} ({len(text)} bytes, {reg["counts"]["agents"]} agents, {reg["counts"]["samples"]} samples, source {reg["source_stamp"]})')
