#!/usr/bin/env python3
"""
SmartCiti.X : the robotics MODEL ARENA (ARENA, wave 18) - writes robotics/arena/registry/arena.json (schema tc-arena/1).

WHAT THIS IS. A measured comparison of policies ("models") on the four robokit world tasks of
robotics/registry/robotics.json, every declared curriculum level, on a declared seed list. robotics/arena/harness.mjs
runs them headless on the SIM_CORE block of web/robokit.py (the code the pages run) and the policy block
robotics/arena/policies.js (the code the arena page runs) and prints the runs and per-policy statistics; this build
stores them. Policies: the SCRIPTED reference, a seeded uniform-random baseline, a SCRIPTED greedy heuristic and,
when their weights are in robotics/arena/registry/models.json, two small behaviour-cloning (BC) networks trained by
robotics/arena/train.mjs on SCRIPTED reference episodes of the TRAIN seeds and compared on the held-out TEST seeds: bc
(the first; never learned grip timing) and bcg (the second: features that expose the distance to the gripper's reach and
a class-weighted grip head). Each table also carries `sort`: items binned in litter sort per policy, because success
there means every item binned and the SCRIPTED reference itself seldom manages that at the first three levels.

WHAT THIS IS NOT. Not a language model and no call to one; not trained on any learner's data; not a claim about any
real robot (the arena is AUTHORED, the kinematics SCHEMATIC). The 11 sim-seat envs are not run: their SCRIPTED
operators live in the 3D page's simulator, which has no headless core - they are listed as excluded, by name.

Fail closed: every field read from the harness output or the model registry is indexed directly; a missing field
stops the build by name. Wall time is measured by `harness.mjs --timing` and logged, never stored here, so a rebuild
is byte-stable.
"""
import hashlib
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'registry' / 'arena.json'
MODELS = HERE / 'registry' / 'models.json'
BUILT = '2026-10-12'
SCHEMA = 'tc-arena/1'


class ArenaError(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise ArenaError(msg)


# ---- the tables this registry carries (AUTHORED choice of policies x seed lists) ----------------------------------
# all_seeds: the three non-trained policies on every declared seed. held_out: every policy, both BC models included, on
# the TEST seeds only (neither saw them), so each BC row is a held-out number and the others are measured on the same tasks.
TABLES = {
    'all_seeds': {'policies': ['scripted', 'random', 'greedy'], 'seeds': 'all'},
    'held_out': {'policies': ['scripted', 'random', 'greedy', 'bc', 'bcg'], 'seeds': 'test'},
}
LEADERBOARD_TABLE = 'held_out'
NEEDS_MODELS = any('bc' in t['policies'] or 'bcg' in t['policies'] for t in TABLES.values())

robotics = json.loads((ROOT / 'robotics/registry/robotics.json').read_text())
need('reference_benchmark' in robotics, 'robotics.json has no reference_benchmark - run robotics/build.py first')
models = json.loads(MODELS.read_text()) if NEEDS_MODELS else {'models': []}
need(not NEEDS_MODELS or isinstance(models.get('models'), list) and models['models'], 'models.json lists no model')
for m in models['models']:
    for k in ('id', 'policy', 'provenance', 'card', 'weights', 'weights_sha256', 'split', 'train'):
        need(k in m, f'models.json: model {m.get("id")} has no {k}')
    need(hashlib.sha256(json.dumps(m['weights'], separators=(',', ':')).encode()).hexdigest() == m['weights_sha256'],
         f'models.json: model {m["id"]} weights do not match their sha256 pin')
    need(not set(m['split']['train']) & set(m['split']['test']), f'models.json: model {m["id"]} train and test seeds overlap')


def harness(policies, seeds):
    r = subprocess.run(['node', str(HERE / 'harness.mjs'), '--policies', ','.join(policies), '--seeds', seeds],
                       capture_output=True, text=True, cwd=ROOT)
    need(r.returncode == 0, f'arena: harness.mjs failed:\n{r.stderr[-2000:]}')
    out = json.loads(r.stdout)
    for k in ('harness', 'policies', 'policy_versions', 'cards', 'seeds', 'tasks', 'excluded', 'columns', 'runs', 'summary',
              'results_sha256', 'bootstrap', 'sort', 'sort_sha256'):
        need(k in out, f'arena: harness printed no {k}')
    need(out['harness'] == SCHEMA, 'arena: harness schema mismatch')
    need(out['policies'] == policies, 'arena: harness ran other policies than asked')
    return out


tables = {}
for name, t in TABLES.items():
    out = harness(t['policies'], t['seeds'])
    need(len(out['runs']) == len(t['policies']) * len(out['tasks']) * len(out['seeds']), f'arena: {name} run count is off')
    tables[name] = {'seed_list': t['seeds'], **out}

# the SCRIPTED rows must reproduce robotics.json's reference benchmark seed for seed (same core, same seeds)
RB = robotics['reference_benchmark']['per_env']
for r in tables['all_seeds']['runs']:
    if r[0] != 'scripted':
        continue
    bs = [b for b in RB[r[1]]['levels'][str(r[2])]['by_seed'] if b[0] == r[3]]
    need(len(bs) == 1 and bs[0][1] == r[4] and bs[0][3] == r[5] and abs(bs[0][4] - r[8]) < 0.006,
         f'arena: scripted run {r[1]} L{r[2]} seed {r[3]} differs from robotics.json reference_benchmark')

cards = {}
for t in tables.values():
    cards.update(t['cards'])
for pid, c in cards.items():
    for k in ('id', 'name', 'kind', 'what', 'learned', 'model', 'not'):
        need(c.get(k) not in (None, ''), f'arena: policy {pid} card has no {k}')
    need(c['kind'] in ('SCRIPTED', 'BASELINE', 'TRAINED'), f'arena: policy {pid} card kind {c["kind"]} unknown')
    need((c['kind'] == 'TRAINED') == bool(c['learned']), f'arena: policy {pid} card says learned without TRAINED kind (or back)')
trained = [m for m in models['models'] if m['provenance'] == 'TRAINED']

LB = tables[LEADERBOARD_TABLE]
board = []
for pid in LB['policies']:
    s = LB['summary'][pid]
    board.append({'policy': pid, 'name': cards[pid]['name'], 'kind': cards[pid]['kind'], 'n': s['n'],
                  'success_rate': s['success_rate'], 'win_vs_ref': s['win_vs_ref'], 'return': s['return'],
                  'collisions': s['collisions'], 'steps': s['steps']})
board.sort(key=lambda b: (-b['success_rate']['mean'], -b['return']['mean'], b['policy']))
for i, b in enumerate(board):
    b['rank'] = i + 1

# the number exit criterion 5 reads ("a learned policy that bins something"): items binned in litter sort on the held-out
# seeds for the SCRIPTED reference and every TRAINED policy, copied from the table's own `sort` block, whatever it is.
SORT = LB['sort']['summary']
learned = []
for pid in ['scripted'] + [p for p in LB['policies'] if cards[p]['kind'] == 'TRAINED']:
    sm = LB['summary'][pid]
    learned.append({'policy': pid, 'kind': cards[pid]['kind'], 'items_binned': SORT[pid]['items_binned'], 'items_total': SORT[pid]['items_total'],
                    'episodes': SORT[pid]['episodes'], 'episodes_with_any': SORT[pid]['episodes_with_any'],
                    'binned_per_episode': SORT[pid]['binned_per_episode'], 'share_of_items': SORT[pid]['share_of_items'],
                    'success_rate': sm['success_rate'], 'win_vs_ref': sm['win_vs_ref'], 'bins_something': SORT[pid]['items_binned'] > 0})

src = b''.join((HERE / f).read_bytes() for f in ('build.py', 'harness.mjs', 'policies.js') + (('train.mjs',) if NEEDS_MODELS else ()))
stamp = hashlib.sha256(src).hexdigest()[:16]
doc = {
    'pack': 'smartcitix-robotics-arena', 'schema': SCHEMA, 'built': BUILT, 'source_stamp': stamp,
    'honesty': {
        'what': 'MEASURED at build time by robotics/arena/harness.mjs: policies compared on the AUTHORED, SCHEMATIC robokit '
                'world tasks, every declared level, on declared seeds. A sandbox comparison, not a claim about any real robot.',
        'trained': (f'{len(trained)} model{"s" if len(trained) != 1 else ""} trained here: ' + '; '.join(m['card']['what'] for m in trained) + '.') if trained
                   else 'No model is trained in this table: every policy compared here is SCRIPTED or a seeded random baseline.',
        'not_llm': 'No policy here is a language model, and none calls one. No network.',
        'data': 'No learner data is read: the BC networks are trained only on SCRIPTED reference episodes generated on the '
                'TRAIN seeds; every table run is generated by the harness from declared seeds.',
        'seats': 'The 11 sim-seat envs are not run (excluded, with the reason): their SCRIPTED operators live in the 3D '
                 'page\'s simulator, which has no headless core.',
        'wall_time': 'Wall time per run is measured by `node robotics/arena/harness.mjs --timing` and logged; it is '
                     'machine-dependent, so it is not stored here and is outside every results_sha256.',
    },
    'cards': cards,
    'models': [{k: m[k] for k in ('id', 'policy', 'provenance', 'weights_sha256', 'split', 'train', 'card')} for m in models['models']],
    'tables': tables,
    'learned_vs_reference': {'table': LEADERBOARD_TABLE, 'seeds': LB['seeds'], 'task': 'world.litter-sort, all four levels (items binned)',
                             'what': 'the held-out items-binned numbers of the SCRIPTED reference and every TRAINED policy, copied from the table; '
                                     'bins_something is items_binned > 0, recorded whatever it is',
                             'rows': learned},
    'leaderboard': {'table': LEADERBOARD_TABLE, 'seeds': LB['seeds'], 'order': 'success rate, then mean return', 'rows': board},
    'counts': {'policies': len(cards), 'trained_models': len(trained),
               'runs': sum(len(t['runs']) for t in tables.values()),
               'tasks': len(tables['all_seeds']['tasks']), 'excluded_envs': len(tables['all_seeds']['excluded'])},
}
OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
for name, t in tables.items():
    print(f'arena: {name} (seeds {t["seeds"][0]}-{t["seeds"][-1]}): ' + ', '.join(
        f'{p} {t["summary"][p]["success_rate"]["mean"]:.3f} [{t["summary"][p]["success_rate"]["ci95"][0]:.3f},'
        f'{t["summary"][p]["success_rate"]["ci95"][1]:.3f}]' for p in t['policies']) + f' | results {t["results_sha256"][:16]}')
print(f'arena: {len(cards)} policies, {len(trained)} trained models, {doc["counts"]["runs"]} runs, stamp {stamp}')
