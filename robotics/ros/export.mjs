#!/usr/bin/env node
/* robotics/ros/export.mjs - the SCRIPTED robotics episodes as ROS 2 MCAP files (message encoding cdr, schema encoding
 * ros2msg, profile ros2) plus a manifest and a dataset card. Nothing here trains a model, reads a learner's data or sends
 * a command to any robot: every file is a recording of the page simulator running a hand-written policy.
 *
 *   node robotics/ros/export.mjs --out <dir> [--zstd] [--policies scripted,greedy]   write the dataset tree
 *   node robotics/ros/export.mjs --index                                            print the registry index (robotics/ros/build.py stores it)
 *
 * Tree:  <dir>/DATASET_CARD.md  <dir>/manifest.json  <dir>/{train,test}/<policy>/<task>/L<level>_s<seed>.mcap
 * Split: the arena's own seed split (robotics/arena/registry/models.json): TRAIN seeds 1-10, TEST seeds 11-20; a file
 * lives under the folder of its seed's split and nowhere else. Sources: the 260 SCRIPTED reference episodes of the
 * Omega Claw dataset (instructions, scene) and the same task x level x seed grid run by the greedy heuristic through
 * the arena harness. Message definitions: robotics/ros/msgs/ (ROS 2 jazzy common_interfaces, byte for byte). */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { writeMcap } from './mcap.mjs';
import { schemaText, encodeCdr, fullName } from './ros2msg.mjs';
import { runEpisode, policies as arenaPolicies, tasks as arenaTasks } from '../arena/harness.mjs';
import { scripted, REG, POLICY_VERSION, ROOT } from '../claw/node.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
export const AUTH = JSON.parse(readFileSync(join(HERE, 'authored', 'ros.json'), 'utf8'));
const sha = (b) => createHash('sha256').update(b).digest('hex');
const need = (c, m) => { if (!c) throw new Error('ros: ' + m); };
const FMT = AUTH.format, TOPIC = Object.fromEntries(AUTH.topics.map((t) => [t.id, t]));
const neg = (x) => (x === 0 ? 0 : -x);
const short = (env) => env.replace(/^world\./, '');

/* the arena's seed split: every model in the registry must carry the same one */
export function splits() {
  const M = JSON.parse(readFileSync(join(ROOT, 'robotics/arena/registry/models.json'), 'utf8'));
  need(M.models.length > 0, 'robotics/arena/registry/models.json lists no model, so the TRAIN/TEST split is unknown');
  const s = M.models[0].split;
  for (const m of M.models) need(JSON.stringify(m.split) === JSON.stringify(s), 'models disagree on the seed split');
  need(Array.isArray(s.train) && Array.isArray(s.test) && !s.train.some((x) => s.test.includes(x)), 'TRAIN and TEST seeds overlap');
  return s;
}
export const splitOf = (seed, S = splits()) => (S.train.includes(seed) ? 'train' : S.test.includes(seed) ? 'test' : null);

/* ---- episodes ---- */
const traj = (steps) => sha(JSON.stringify(steps.map((x) => [x.i, x.pose, x.vel, x.a])));
export function* episodes({ policies = AUTH.policies } = {}) {
  const S = splits(), claw = scripted(), by = new Map(claw.map((c) => [c.task + '|' + c.level + '|' + c.seed, c]));
  need(by.size === claw.length, 'claw samples repeat a (task, level, seed)');
  for (const policy of policies) {
    need(AUTH.policies.includes(policy), 'policy ' + policy + ' is not an exported SCRIPTED policy');
    for (const t of arenaTasks(REG)) for (const level of t.levels) for (const seed of t.seeds) {
      const c = by.get(t.env + '|' + level + '|' + seed);
      need(c, `no claw sample for ${t.env} L${level} seed ${seed} (instruction and scene come from it)`);
      let src;
      if (policy === 'scripted') {
        src = { steps: c.steps, names: c.action_names, outcome: c.outcome, n_steps: c.n_steps, dt_s: c.dt_s, hz: c.hz, actor: c.actor, embodiment: REG.envs[t.env].embodiments[0], policy_version: c.provenance.policy_version, claw_id: c.id };
      } else {
        const e = runEpisode(REG, { policy, env: t.env, level, seed });
        src = { steps: e.samples, names: REG.envs[t.env].action.fields.map((f) => f.name), outcome: e.outcome, n_steps: e.steps, dt_s: e.dt_s, hz: e.hz, actor: e.actor, embodiment: e.embodiment, policy_version: arenaPolicies(REG).find((p) => p.id === policy).version, claw_id: null };
      }
      yield { policy, env: t.env, level, seed, split: splitOf(seed, S), instruction: c.instruction, scene: c.scene, level_name: c.level_name, family: c.family, ...src };
    }
  }
}

/* ---- one episode -> one MCAP file ---- */
const quat = (yaw) => ({ x: 0, y: 0, z: Math.sin((yaw + Math.PI / 2) / 2), w: Math.cos((yaw + Math.PI / 2) / 2) });
const ns = (i, dt) => Math.round(i * dt * 1e9);
const stampOf = (t) => ({ sec: Math.floor(t / 1e9), nanosec: t % 1e9 });
const zeros36 = () => new Array(36).fill(0);
const qosYaml = (q) => AUTH.qos_yaml.replace('{depth}', q.depth).replace('{reliability}', q.reliability).replace('{durability}', q.durability);

export function topicsFor(env) {
  const hasGrip = REG.envs[env].action.fields.some((f) => f.name === 'grip');
  return AUTH.topics.filter((t) => t.id !== 'gripper_command' || hasGrip);
}
export function episodeMessages(E) {
  const idOf = Object.fromEntries(topicsFor(E.env).map((t, k) => [t.id, k + 1]));
  const a = (s, name) => { const k = E.names.indexOf(name); return k < 0 ? 0 : s.a[k]; };
  const frames = AUTH.frames, out = [], seq = {};
  const add = (id, t, type, value) => { seq[id] = (seq[id] ?? -1) + 1; out.push({ channel: idOf[id], sequence: seq[id], logTime: t, publishTime: t, data: encodeCdr(type, value) }); };
  add('instruction', 0, TOPIC.instruction.type, { data: E.instruction.text });
  for (const s of E.steps) {
    const t = ns(s.i, E.dt_s), stamp = stampOf(t), depth = s.pose.length > 3 ? s.pose[3] : 0;
    const pose = { position: { x: s.pose[0], y: s.pose[1], z: neg(depth) }, orientation: quat(s.pose[2]) };
    add('cmd_vel', t, TOPIC.cmd_vel.type, { linear: { x: a(s, 'v'), y: 0, z: neg(a(s, 'vz')) }, angular: { x: 0, y: 0, z: a(s, 'w') } });
    add('odom', t, TOPIC.odom.type, { header: { stamp, frame_id: frames.odom }, child_frame_id: frames.base,
      pose: { pose, covariance: zeros36() }, twist: { twist: { linear: { x: s.vel[0], y: 0, z: 0 }, angular: { x: 0, y: 0, z: s.vel[1] } }, covariance: zeros36() } });
    add('ground_truth_pose', t, TOPIC.ground_truth_pose.type, { header: { stamp, frame_id: frames.world }, pose });
    add('joint_states', t, TOPIC.joint_states.type, { header: { stamp, frame_id: frames.base }, name: AUTH.joint_names.joint_states, position: [], velocity: [s.vel[0], s.vel[1]], effort: [] });
    if (idOf.gripper_command) add('gripper_command', t, TOPIC.gripper_command.type, { header: { stamp, frame_id: frames.base }, name: AUTH.joint_names.gripper_command, position: [a(s, 'grip')], velocity: [], effort: [] });
  }
  return { messages: out, idOf };
}
export const filePath = (E) => `${E.split}/${E.policy}/${short(E.env)}/L${E.level}_s${String(E.seed).padStart(2, '0')}.mcap`;

export function episodeMcap(E, { compression = '', chunkSize = FMT.chunk_size_bytes } = {}) {
  need(E.split === 'train' || E.split === 'test', `seed ${E.seed} is in neither the TRAIN nor the TEST split`);
  const { messages, idOf } = episodeMessages(E), tps = topicsFor(E.env);
  const types = [...new Set(tps.map((t) => t.type))];
  const schemas = types.map((type, k) => ({ id: k + 1, name: type, encoding: FMT.schema_encoding, data: Buffer.from(schemaText(type), 'utf8') }));
  const channels = tps.map((t) => ({ id: idOf[t.id], schemaId: types.indexOf(t.type) + 1, topic: t.name, messageEncoding: FMT.message_encoding, metadata: { offered_qos_profiles: qosYaml(t.qos) } }));
  const H = AUTH.honesty;
  const meta = { record: AUTH.schema, pack: AUTH.pack, provenance: 'SCRIPTED', robots_and_arenas: 'AUTHORED, SCHEMATIC', policy: E.policy, actor: E.actor, policy_version: E.policy_version,
    env: E.env, embodiment: E.embodiment, level: String(E.level), level_name: E.level_name, family: E.family, seed: String(E.seed), split: E.split, split_source: AUTH.split_source,
    samples: String(E.steps.length), steps: String(E.n_steps), hz: String(E.hz), dt_s: String(E.dt_s),
    outcome_done: E.outcome.done, outcome_success: String(E.outcome.success), outcome_return: String(E.outcome.return), outcome_collected: String(E.outcome.collected),
    instruction_source: E.instruction.source, claw_sample_id: E.claw_id ?? 'none', trajectory_sha256: traj(E.steps), time_base: AUTH.time_base,
    frames: `${AUTH.frames.world} / ${AUTH.frames.odom} / ${AUTH.frames.base}: local east-north-up, x = e, y = n, z = -depth (PROPOSED mapping, see the dataset card)`,
    not_real_robot_data: 'true', learner_data: 'none', trained_models: '0', sim_to_real_gap: H.sim_to_real, licence: AUTH.licence_field };
  const scene = Buffer.from(JSON.stringify(E.scene), 'utf8');
  const buf = writeMcap({ profile: FMT.profile, library: FMT.library, schemas, channels, messages, chunkSize, compression,
    metadata: [{ name: 'smartcitix.episode', map: meta }], attachments: [{ logTime: 0, createTime: 0, name: 'scene.json', mediaType: 'application/json', data: scene }] });
  const nameOf = Object.fromEntries(tps.map((t) => [idOf[t.id], t.name])), per = {};
  for (const m of messages) per[nameOf[m.channel]] = (per[nameOf[m.channel]] || 0) + 1;
  return { buf, messages: messages.length, per_topic: per, trajectory_sha256: meta.trajectory_sha256, span_ns: messages.length ? messages[messages.length - 1].logTime : 0 };
}

/* every file's row; `onFile(path, buf, row)` is called for each file so a caller can write or discard it */
export function exportAll({ policies, compression = '', onFile } = {}) {
  const rows = [];
  for (const E of episodes({ policies })) {
    const r = episodeMcap(E, { compression }), path = filePath(E);
    const row = { path, policy: E.policy, task: short(E.env), level: E.level, seed: E.seed, split: E.split, samples: E.steps.length, hz: E.hz, messages: r.messages,
      duration_s: Math.round(r.span_ns / 1e6) / 1000, success: E.outcome.success, bytes: r.buf.length, sha256: sha(r.buf), trajectory_sha256: r.trajectory_sha256, per_topic: r.per_topic };
    rows.push(row);
    if (onFile) onFile(path, r.buf, row, E);
  }
  return rows;
}

export function summarise(rows, S = splits()) {
  const by = (f) => { const o = {}; for (const r of rows) { const k = f(r); o[k] = (o[k] || 0) + 1; } return o; };
  const total = rows.reduce((a, r) => a + r.bytes, 0);
  return { files: rows.length, bytes: total, messages: rows.reduce((a, r) => a + r.messages, 0), samples: rows.reduce((a, r) => a + r.samples, 0),
    by_policy: by((r) => r.policy), by_split: by((r) => r.split), by_task: by((r) => r.task), by_policy_split: by((r) => r.policy + '/' + r.split),
    hz: [...new Set(rows.map((r) => r.hz))], success: rows.filter((r) => r.success).length, seeds: { train: S.train, test: S.test },
    max_file_bytes: Math.max(...rows.map((r) => r.bytes)), min_file_bytes: Math.min(...rows.map((r) => r.bytes)),
    digest: sha(JSON.stringify(rows.map((r) => [r.path, r.sha256]))).slice(0, 16) };
}

/* ---- the dataset card: Hugging Face-style YAML front matter + the tc-dataset/1 sections ---- */
export function renderCard(rows, sum, registryStamp = null) {
  const H = AUTH.honesty, S = splits();
  const tp = (id) => `\`${TOPIC[id].name}\` (${TOPIC[id].type}) - ${TOPIC[id].what}; ${TOPIC[id].count}`;
  const kb = (n) => (n / 1024).toFixed(1) + ' KiB';
  return `---
license: other
license_name: ${AUTH.licence_field}
pretty_name: SmartCiti.X SCRIPTED robotics episodes as ROS 2 MCAP
task_categories:
  - robotics
tags:
  - ros2
  - mcap
  - rosbag2
  - synthetic
  - simulation
  - scripted
size_categories:
  - n<1K
annotations_creators:
  - machine-generated
source_datasets:
  - original
language:
  - en
configs:
  - config_name: default
    data_files:
      - split: train
        path: train/**/*.mcap
      - split: test
        path: test/**/*.mcap
dataset_info:
  record: ${AUTH.schema}
  provenance: SCRIPTED
  files: ${sum.files}
  messages: ${sum.messages}
  trained_models: 0
---

# SmartCiti.X SCRIPTED robotics episodes as ROS 2 MCAP (${AUTH.schema} card, tc-dataset/1 sections)

<!-- section:motivation -->
## Motivation
- Simulated robot episodes in the file format ROS 2 tools read: MCAP files with message encoding \`cdr\`, schema encoding \`ros2msg\` and the \`ros2\` profile, using standard message types (geometry_msgs/Twist, geometry_msgs/PoseStamped, nav_msgs/Odometry, sensor_msgs/JointState, std_msgs/String). They let a robotics team exercise a data pipeline, a bag reader or a loader on small, fully labelled, reproducible data.
- This card says what the files are and are not. It makes no claim about any use beyond that.

<!-- section:composition -->
## Composition
- ${sum.files} files, ${sum.messages} messages, ${sum.samples} time steps sampled at ${sum.hz.join('/')} Hz of simulation time. Total ${sum.bytes} bytes uncompressed (${(sum.bytes / 1048576).toFixed(1)} MiB; largest file ${kb(sum.max_file_bytes)}, smallest ${kb(sum.min_file_bytes)}); chunk compression is off by default.
- By source policy: ${Object.entries(sum.by_policy).map(([k, v]) => `${k} ${v}`).join(', ')}. By task: ${Object.entries(sum.by_task).map(([k, v]) => `${k} ${v}`).join(', ')}. One file per policy x task x curriculum level x seed.
- Splits (the model arena's own, robotics/arena/registry/models.json): TRAIN seeds ${S.train[0]}-${S.train[S.train.length - 1]} = ${sum.by_split.train} files, TEST seeds ${S.test[0]}-${S.test[S.test.length - 1]} = ${sum.by_split.test} files. A file sits in the folder of its seed's split and in no other; a TEST seed never appears in a TRAIN file. The Omega Claw JSONL has its own seed splits (train 1-16, val 17-18, test 19-20); do not mix the two schemes.
- ${sum.success} of ${sum.files} episodes met their task's success rule; the rest are kept and labelled in each file's metadata, not filtered.
- Topics in each file:
  - ${tp('instruction')}
  - ${tp('cmd_vel')}
  - ${tp('odom')}
  - ${tp('ground_truth_pose')}
  - ${tp('joint_states')}
  - ${tp('gripper_command')}
- Each file also holds one MCAP Metadata record, \`smartcitix.episode\` (policy, policy version, task, level, seed, split, outcome, trajectory hash, provenance, this card's limits), and one Attachment, \`scene.json\` (the seeded scene layout: obstacles, items, gates, bin, targets).
- Time: ${AUTH.time_base}. Message log time, publish time and header stamps agree.

<!-- section:collection -->
## Collection process
- Provenance SCRIPTED. Each episode is produced headless by the page simulator's own SIM_CORE (web/robokit.py) driven by a hand-written policy: the SCRIPTED reference (the Omega Claw dataset's 260 samples; policy version ${POLICY_VERSION}) or the SCRIPTED greedy heuristic (robotics/arena/policies.js). Deterministic: a rebuild reproduces every byte.
- Robots (a wheeled rover, an arm on a base, a survey ROV) and the arenas are AUTHORED and SCHEMATIC. The instruction text of every file is quoted from a registry and is the same for both policies on the same task.
- Nothing was recorded from a real machine or a person. No learner data was read.

<!-- section:preprocessing -->
## Preprocessing
- Frames and signs (PROPOSED mapping, checked against the simulator's own update rule in the suite): the simulator's east/north metres become x/y of a local east-north-up frame (REP 103: X east, Y north, Z up; yaw zero pointing east, counter-clockwise positive); its heading (0 = north, positive toward west) becomes yaw about z with yaw_ros = yaw + pi/2; v is linear.x and w is angular.z; the ROV's depth (positive down) becomes z = -depth and vz becomes linear.z = -vz. The origin is the start point, not a geographic location.
- Odometry covariances are 0: the simulated pose is exact. Wheel joints, gripper state and \`near\` ids are not exported (no joint model; \`near\` is in the Omega Claw JSONL).
- The ros2msg schema text of every channel is the ROS 2 jazzy .msg files byte for byte (ros2/common_interfaces at a941f14bb318d8d904505ed935ccbb97f24a70a4, ros2/rcl_interfaces at 7aa3caf43377ea6ad615bc1040832e2c7566bfbe, Apache-2.0), joined the way rosbag2 joins them. CDR is XCDR1 little endian.
- Every check is in robotics/ros/test.mjs: magic bytes, header, footer, summary and indexes, CRCs, schema text, message counts against the source episodes, monotonic timestamps, no TEST seed in a TRAIN file, and this card's counts.

<!-- section:uses -->
## Uses
- Intended use: testing bag readers, loaders, message-type handling and training-pipeline plumbing on synthetic data.
- NOT real robot data. NOT recorded from any robot, vehicle, ROV or person. NOT learner data. NOT the output of a trained model: trained_models is 0 for this pack.
- Sim-to-real gap: ${H.sim_to_real}
- ${H.robots}
- Conformance: ${H.conformance}
- Not written: ${H.omitted}

<!-- section:distribution -->
## Distribution
- Licence: ${AUTH.licence_field}. Until the owner decides, this card grants no licence; the vendored ROS message definitions stay under their own Apache-2.0 licence (robotics/ros/msgs/LICENSE).
- Nothing is uploaded or hosted by this repository: robotics/ros/export.mjs writes the files where it is run (\`node robotics/ros/export.mjs --out <dir>\`, optional \`--zstd\` chunk compression).

<!-- section:maintenance -->
## Maintenance
- Digest of all file hashes: ${sum.digest}. The registry robotics/ros/registry/ros.json stores every file's size and sha256; \`python3 robotics/ros/build.py --check\` fails when it is stale.
- Known gaps: no image, lidar, IMU or point-cloud topics; one embodiment per task; two policies; ${sum.files} episodes.${registryStamp ? ' Source stamp ' + registryStamp + '.' : ''}
`;
}

/* ---- CLI ---- */
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const arg = (k) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : undefined; };
  const policies = arg('--policies') ? arg('--policies').split(',') : undefined;
  const compression = process.argv.includes('--zstd') ? 'zstd' : '';
  if (process.argv.includes('--index')) {
    const rows = exportAll({ policies });
    const sum = summarise(rows);
    process.stdout.write(JSON.stringify({ summary: sum, rows, card: renderCard(rows, sum) }) + '\n');
  } else {
    const out = arg('--out');
    if (!out) { console.error('FAIL export: --out <dir> is required'); process.exit(1); }
    const rows = exportAll({ policies, compression, onFile: (p, buf) => { mkdirSync(dirname(join(out, p)), { recursive: true }); writeFileSync(join(out, p), buf); } });
    const sum = summarise(rows);
    writeFileSync(join(out, 'manifest.json'), JSON.stringify({ record: AUTH.schema, pack: AUTH.pack, provenance: 'SCRIPTED', trained_models: 0, compression: compression || 'none', summary: sum, files: rows }, null, 1) + '\n');
    writeFileSync(join(out, 'DATASET_CARD.md'), renderCard(rows, sum));
    console.log(`ros dataset: ${sum.files} files, ${sum.messages} messages, ${sum.bytes} bytes (${compression || 'uncompressed'} chunks), train ${sum.by_split.train} / test ${sum.by_split.test} -> ${out}`);
  }
}
