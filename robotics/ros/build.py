#!/usr/bin/env python3
"""The ROS 2 export registry: robotics/ros/registry/ros.json and robotics/ros/DATASET_CARD.md (ROSDATA, wave 24).

What it is: the SCRIPTED robotics episodes (the reference policy of the Omega Claw dataset and the greedy heuristic of the
model arena, on the four world tasks x every curriculum level x seeds 1-20) written as ROS 2 MCAP files by
robotics/ros/export.mjs: message encoding cdr, schema encoding ros2msg, profile ros2, message definitions taken byte for
byte from ROS 2 jazzy (robotics/ros/msgs/). The files themselves are NOT stored in the repository (about 160 MB
uncompressed): `node robotics/ros/export.mjs --out <dir>` writes them when run, and this registry stores every file's size
and sha256 so the suite and `--check` can prove a rebuild is byte-equal.

What it is not: real robot data, learner data, or the output of a model. Provenance SCRIPTED; robots and arenas
AUTHORED and SCHEMATIC; trained_models 0 for this pack; the sim-to-real gap is stated in the registry and the card.
The licence field is left as "to be decided by the owner". Nothing here says who the data is for or on what terms.

Fails closed: a missing authored field, a vendored .msg whose bytes differ from the pin, a pin that is not a 40-hex commit,
or a failing export stops the build with a named error. `--check` rebuilds in memory and fails if the registry or the card
is stale.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'registry' / 'ros.json'
CARD = HERE / 'DATASET_CARD.md'


def need(cond, msg):
    if not cond:
        raise SystemExit(f'ros: {msg}')


A = json.loads((HERE / 'authored' / 'ros.json').read_text())
for k in ('schema', 'pack', 'format', 'policies', 'split_source', 'time_base', 'frames', 'topics', 'joint_names', 'mapping', 'honesty', 'sources', 'msgs', 'qos_yaml', 'licence_field'):
    need(k in A, f'robotics/ros/authored/ros.json lacks {k!r}')
for k in ('provenance', 'not_real', 'learner_data', 'trained', 'sim_to_real', 'conformance', 'omitted', 'robots', 'licence'):
    need(k in A['honesty'], f'honesty lacks {k!r}')
need(A['licence_field'] == 'to be decided by the owner' == A['honesty']['licence'], 'the licence field is the owner\'s to decide: it must read "to be decided by the owner"')
need(A['format']['profile'] == 'ros2' and A['format']['message_encoding'] == 'cdr' and A['format']['schema_encoding'] == 'ros2msg', 'format must be the MCAP ros2 profile with cdr and ros2msg')
for name in ('common_interfaces', 'rcl_interfaces', 'rosbag2', 'mcap_spec', 'rep_103'):
    need(re.fullmatch(r'[0-9a-f]{40}', A['sources'][name]['commit']), f'source {name} is not pinned to a 40-hex commit')

# the vendored message definitions are the pinned bytes
for m in A['msgs']:
    p = HERE / 'msgs' / m['path']
    need(p.is_file(), f'missing vendored message definition {m["path"]}')
    b = p.read_bytes()
    need(hashlib.sha256(b).hexdigest() == m['sha256'], f'{m["path"]} differs from its pinned sha256 (a vendored ROS definition must stay byte for byte)')
    need(hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest() == m['git_blob'], f'{m["path"]} differs from its pinned git blob id')
lic = HERE / 'msgs' / 'LICENSE'
need(lic.is_file() and hashlib.sha256(lic.read_bytes()).hexdigest() == A['sources']['common_interfaces']['licence_file_sha256'], 'msgs/LICENSE is not the pinned Apache-2.0 text')
need({m['type'] for m in A['msgs']} >= {t['type'] for t in A['topics']}, 'a topic uses a message type that is not vendored')

res = subprocess.run(['node', str(HERE / 'export.mjs'), '--index'], capture_output=True, text=True, cwd=ROOT)
need(res.returncode == 0, f'export.mjs --index failed:\n{res.stderr[-3000:]}')
IDX = json.loads(res.stdout)
SUM = IDX['summary']
need(SUM['files'] == 520 and SUM['by_split'] == {'train': 260, 'test': 260}, f'unexpected file counts {SUM["files"]} {SUM["by_split"]}')


def stamp(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:16]


SOURCES = ['robotics/ros/authored/ros.json', 'robotics/ros/mcap.mjs', 'robotics/ros/ros2msg.mjs', 'robotics/ros/export.mjs',
           'robotics/registry/robotics.json', 'robotics/arena/registry/models.json', 'robotics/arena/policies.js', 'robotics/arena/harness.mjs',
           'robotics/claw/node.mjs', 'robotics/claw/core.mjs', 'robotics/claw/authored/claw.json', 'training/registry/training.json', 'web/robokit.py']
SOURCES += ['robotics/ros/msgs/' + m['path'] for m in A['msgs']]
stamps = {s: stamp(s) for s in SOURCES}
reg = {
    'pack': A['pack'], 'name': 'ROS 2 export of the SCRIPTED robotics episodes', 'schema': A['schema'],
    'source_stamp': hashlib.sha256(json.dumps(stamps, sort_keys=True).encode()).hexdigest()[:16],
    'source_stamps': stamps,
    'honesty': A['honesty'],
    'format': A['format'], 'time_base': A['time_base'], 'frames': A['frames'], 'topics': A['topics'], 'joint_names': A['joint_names'], 'mapping': A['mapping'],
    'split_source': A['split_source'], 'sources': A['sources'], 'msgs': A['msgs'],
    'summary': SUM,
    'counts': {'files': SUM['files'], 'messages': SUM['messages'], 'samples': SUM['samples'], 'bytes_uncompressed': SUM['bytes'], 'policies': len(A['policies']),
               'topics': len(A['topics']), 'message_types': len({t['type'] for t in A['topics']}), 'vendored_msg_files': len(A['msgs']), 'trained_models': 0, 'learner_episodes': 0},
    'columns': ['path', 'bytes', 'sha256', 'samples', 'messages', 'success'],
    'files': [[r['path'], r['bytes'], r['sha256'], r['samples'], r['messages'], int(r['success'])] for r in IDX['rows']],
}
text = json.dumps(reg, indent=1, ensure_ascii=False) + '\n'
card = IDX['card']
if '--check' in sys.argv:
    need(OUT.is_file() and OUT.read_text() == text, 'robotics/ros/registry/ros.json is stale - run python3 robotics/ros/build.py')
    need(CARD.is_file() and CARD.read_text() == card, 'robotics/ros/DATASET_CARD.md is stale - run python3 robotics/ros/build.py')
    print(f'ros: registry current ({reg["source_stamp"]})')
else:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    CARD.write_text(card)
    print(f'ros: wrote {OUT.relative_to(ROOT)} ({len(text)} bytes) and {CARD.relative_to(ROOT)}: {SUM["files"]} files, {SUM["messages"]} messages, {SUM["bytes"]} bytes uncompressed, source {reg["source_stamp"]}')
