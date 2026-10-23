#!/usr/bin/env node
/* robotics/ros/test.mjs - the ROS 2 MCAP export of the SCRIPTED robotics episodes. Prints `  ok <name>` per check and
 * `FAIL <name>` at column 0 on failure; exits non-zero when anything failed. No network, no ROS install, no Python.
 * It builds all 520 files in memory one at a time (about 160 MB in all, nothing is written) and checks each against the
 * MCAP specification text, the vendored ROS 2 definitions and the source episodes. */
import assert from 'node:assert/strict';
import zlib from 'node:zlib';
import { readFileSync, readdirSync, statSync, mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { MAGIC, OP, crc32, writeMcap, verifyMcap } from './mcap.mjs';
import { schemaText, encodeCdr, decodeCdr, fields, msgBytes, gitBlobSha1, sha256, MSG_DIR, DELIM, shortName } from './ros2msg.mjs';
import { AUTH, exportAll, summarise, renderCard, splits, splitOf, episodeMcap, episodes, topicsFor } from './export.mjs';
import { scripted, REG, RoboCore, T, ROOT } from '../claw/node.mjs';
import { runEpisode, tasks as arenaTasks } from '../arena/harness.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
let failed = 0, passed = 0;
const ok = (n) => { passed++; console.log('  ok ' + n); };
const fail = (n, e) => { failed++; console.log('FAIL ' + n + ': ' + String(e && e.message || e).split('\n')[0].slice(0, 300)); };
const check = (n, f) => { try { f(); ok(n); } catch (e) { fail(n, e); } };
const read = (rel) => readFileSync(join(ROOT, rel), 'utf8');
const sha = (b) => createHash('sha256').update(b).digest('hex');
const walk = (d) => readdirSync(d).flatMap((f) => (statSync(join(d, f)).isDirectory() ? walk(join(d, f)).map((x) => f + '/' + x) : [f]));
const REL = (p) => 'robotics/ros/' + p;

/* ============================= 1. the vendored ROS 2 definitions ============================= */
check('msgs: every vendored .msg equals its pinned sha256 and git blob id', () => {
  assert.equal(AUTH.msgs.length, 13);
  for (const m of AUTH.msgs) { const b = readFileSync(join(MSG_DIR, m.path)); assert.equal(sha256(b), m.sha256, m.path + ' sha256'); assert.equal(gitBlobSha1(b), m.git_blob, m.path + ' git blob'); }
});
check('msgs: the Apache-2.0 licence text is vendored beside them and pinned', () => {
  const l = readFileSync(join(MSG_DIR, 'LICENSE'), 'utf8');
  assert.equal(sha(l), AUTH.sources.common_interfaces.licence_file_sha256); assert.match(l, /Apache License\s+Version 2\.0/);
});
check('msgs: sources are pinned to 40-hex commits, not branch names alone', () => {
  for (const k of ['common_interfaces', 'rcl_interfaces', 'rosbag2', 'mcap_spec', 'rep_103']) assert.match(AUTH.sources[k].commit, /^[0-9a-f]{40}$/, k);
  assert.equal(AUTH.sources.common_interfaces.branch, 'jazzy'); assert.equal(AUTH.sources.mcap_spec.url, 'https://mcap.dev/spec');
});
check('msgs: the vendored set is exactly the types the topics use plus their dependencies, nothing extra', () => {
  const need = new Set();
  const visit = (t) => { t = shortName(t); if (need.has(t)) return; need.add(t); for (const f of fields(t)) if (f.type.includes('/')) visit(f.type); };
  for (const t of AUTH.topics) visit(t.type);
  const have = walk(MSG_DIR).filter((f) => f.endsWith('.msg')).map((f) => f.replace('/msg/', '/').replace(/\.msg$/, '')).sort();
  assert.deepEqual(have, [...need].sort());
  assert.deepEqual(AUTH.msgs.map((m) => shortName(m.type)).sort(), have);
  assert.deepEqual(walk(MSG_DIR).filter((f) => !f.endsWith('.msg')), ['LICENSE']);
});
check('msgs: the five requested message types are used, with the right package names', () => {
  assert.deepEqual([...new Set(AUTH.topics.map((t) => t.type))].sort(), ['geometry_msgs/msg/PoseStamped', 'geometry_msgs/msg/Twist', 'nav_msgs/msg/Odometry', 'sensor_msgs/msg/JointState', 'std_msgs/msg/String']);
});

/* ============================= 2. the ros2msg schema text ============================= */
check('schema: rosbag2\'s own test vector (rosbag2_test_msgdefs/ComplexMsg) is reproduced exactly', () => {
  const d = mkdtempSync(join(tmpdir(), 'rosmsg-'));
  try {
    mkdirSync(join(d, 'rosbag2_test_msgdefs/msg'), { recursive: true });
    writeFileSync(join(d, 'rosbag2_test_msgdefs/msg/ComplexMsg.msg'), 'rosbag2_test_msgdefs/BasicMsg b\n');
    writeFileSync(join(d, 'rosbag2_test_msgdefs/msg/BasicMsg.msg'), 'float32 c\n');
    assert.equal(schemaText('rosbag2_test_msgdefs/ComplexMsg', d), 'rosbag2_test_msgdefs/BasicMsg b\n\n================================================================================\nMSG: rosbag2_test_msgdefs/BasicMsg\nfloat32 c\n');
  } finally { rmSync(d, { recursive: true, force: true }); }
});
check('schema: the delimiter is 80 equals signs, then an "MSG: pkg/Type" line', () => { assert.equal(DELIM.length, 80); assert.match(DELIM, /^=+$/); });
const SCHEMA_TYPES = [...new Set(AUTH.topics.map((t) => t.type))];
check('schema: each type\'s text = the root .msg unchanged, then each dependency\'s .msg unchanged (sorted depth-first, once)', () => {
  for (const type of SCHEMA_TYPES) {
    const text = schemaText(type), parts = text.split('\n' + DELIM + '\nMSG: ');
    assert.equal(parts[0], msgBytes(type).toString('utf8'), type + ' root');
    const names = parts.slice(1).map((p) => p.slice(0, p.indexOf('\n')));
    assert.equal(new Set(names).size, names.length, type + ' repeats a dependency');
    for (const p of parts.slice(1)) { const nl = p.indexOf('\n'); assert.equal(p.slice(nl + 1), msgBytes(p.slice(0, nl)).toString('utf8'), p.slice(0, nl)); }
    const closure = new Set(); const visit = (t) => { for (const f of fields(t)) if (f.type.includes('/') && !closure.has(f.type)) { closure.add(f.type); visit(f.type); } };
    visit(type);
    assert.deepEqual([...names].sort(), [...closure].sort(), type + ' dependency set');
  }
});
check('schema: Odometry text lists its dependencies in rosbag2 order (PoseWithCovariance..., TwistWithCovariance..., Header, Time)', () => {
  const names = [...schemaText('nav_msgs/msg/Odometry').matchAll(/^MSG: (.*)$/gm)].map((m) => m[1]);
  assert.deepEqual(names, ['geometry_msgs/PoseWithCovariance', 'geometry_msgs/Pose', 'geometry_msgs/Point', 'geometry_msgs/Quaternion', 'geometry_msgs/TwistWithCovariance', 'geometry_msgs/Twist', 'geometry_msgs/Vector3', 'std_msgs/Header', 'builtin_interfaces/Time']);
});

/* ============================= 3. CDR ============================= */
const GOLD = JSON.parse(readFileSync(join(HERE, 'authored', 'cdr_golden.json'), 'utf8'));
check('cdr: 7 vectors serialised by the rosbags package (an independent implementation) encode byte for byte and decode back', () => {
  let n = 0;
  for (const [type, list] of Object.entries(GOLD.vectors)) for (const [value, hex] of list) { n++; assert.equal(encodeCdr(type, value).toString('hex'), hex, type); assert.deepEqual(decodeCdr(type, Buffer.from(hex, 'hex')), value, type + ' decode'); }
  assert.equal(n, 7);
});
check('cdr: payloads start with the XCDR1 little-endian header 00 01 00 00; sizes are String 11, Twist 52, PoseStamped 84, Odometry 724', () => {
  const size = (t, v) => encodeCdr(t, v).length;
  const v = (x, y, z) => ({ x, y, z });
  assert.equal(encodeCdr('std_msgs/msg/String', { data: 'hi' }).subarray(0, 4).toString('hex'), '00010000');
  assert.equal(size('std_msgs/msg/String', { data: 'hi' }), 11);
  assert.equal(size('geometry_msgs/msg/Twist', { linear: v(1, 0, 0), angular: v(0, 0, 1) }), 52);
  const hdr = { stamp: { sec: 1, nanosec: 2 }, frame_id: 'odom' }, pose = { position: v(0, 0, 0), orientation: { x: 0, y: 0, z: 0, w: 1 } };
  assert.equal(size('geometry_msgs/msg/PoseStamped', { header: hdr, pose }), 84);
  assert.equal(size('nav_msgs/msg/Odometry', { header: hdr, child_frame_id: 'base_link', pose: { pose, covariance: new Array(36).fill(0) }, twist: { twist: { linear: v(0, 0, 0), angular: v(0, 0, 0) }, covariance: new Array(36).fill(0) } }), 724 - 0);
});
check('cdr: the encoder refuses a missing field, an unknown field, a short fixed array, a non-finite number and a non-string', () => {
  const twist = { linear: { x: 1, y: 0, z: 0 }, angular: { x: 0, y: 0, z: 1 } };
  encodeCdr('geometry_msgs/msg/Twist', twist);
  assert.throws(() => encodeCdr('geometry_msgs/msg/Twist', { linear: twist.linear }), /missing/);
  assert.throws(() => encodeCdr('geometry_msgs/msg/Twist', { ...twist, extra: 1 }), /no field/);
  assert.throws(() => encodeCdr('geometry_msgs/msg/Twist', { ...twist, linear: { x: NaN, y: 0, z: 0 } }), /finite/);
  assert.throws(() => encodeCdr('std_msgs/msg/String', { data: 5 }), /string/);
  const c = { header: { stamp: { sec: 0, nanosec: 0 }, frame_id: 'a' }, pose: { position: { x: 0, y: 0, z: 0 }, orientation: { x: 0, y: 0, z: 0, w: 1 } } };
  encodeCdr('geometry_msgs/msg/PoseStamped', c);
  assert.throws(() => decodeCdr('std_msgs/msg/String', Buffer.from('01000000', 'hex')), /XCDR1/);
  assert.throws(() => decodeCdr('std_msgs/msg/String', Buffer.concat([encodeCdr('std_msgs/msg/String', { data: 'a' }), Buffer.from([0])])), /left over/);
});

/* ============================= 4. the MCAP writer and verifier (unit) ============================= */
check('mcap: the magic is 0x89 M C A P 0x30 \\r \\n and CRC-32 matches the IEEE check value and node\'s zlib', () => {
  assert.equal(MAGIC.toString('hex'), '894d434150300d0a');
  assert.equal(crc32(Buffer.from('123456789')), 0xcbf43926);
  const rnd = Buffer.alloc(5000); for (let i = 0; i < rnd.length; i++) rnd[i] = (i * 7919 + 13) & 255;
  if (typeof zlib.crc32 === 'function') assert.equal(crc32(rnd), zlib.crc32(rnd) >>> 0);
});
const small = (o = {}) => writeMcap({ profile: 'ros2', library: 'test', schemas: [{ id: 1, name: 'std_msgs/msg/String', encoding: 'ros2msg', data: Buffer.from(schemaText('std_msgs/msg/String')) }],
  channels: [{ id: 1, schemaId: 1, topic: '/a', messageEncoding: 'cdr', metadata: { offered_qos_profiles: '' } }, { id: 2, schemaId: 1, topic: '/b', messageEncoding: 'cdr', metadata: {} }],
  messages: Array.from({ length: 12 }, (_, i) => ({ channel: 1 + (i % 2), sequence: i >> 1, logTime: 1000 * i, publishTime: 1000 * i, data: encodeCdr('std_msgs/msg/String', { data: 'm' + i }) })),
  metadata: [{ name: 'm', map: { k: 'v' } }], attachments: [{ logTime: 0, createTime: 0, name: 'a.json', mediaType: 'application/json', data: Buffer.from('{}') }], ...o });
check('mcap: a file with Header, chunks, Message Index, Metadata, Attachment, Data End, Summary, Summary Offset and Footer verifies clean', () => {
  const v = verifyMcap(small()); assert.deepEqual(v.issues, []);
  assert.equal(v.info.header.profile, 'ros2'); assert.equal(v.info.messages.length, 12); assert.equal(v.info.chunks.length, 1);
  assert.deepEqual(v.info.summary.offsets.map((o) => o.groupOpcode), [OP.SCHEMA, OP.CHANNEL, OP.STATISTICS, OP.CHUNK_INDEX, OP.ATTACHMENT_INDEX, OP.METADATA_INDEX]);
  const b = small(); assert.equal(b[b.length - 8 - 29], OP.FOOTER); assert.ok(b.subarray(0, 8).equals(MAGIC) && b.subarray(b.length - 8).equals(MAGIC));
});
check('mcap: many chunks (tiny chunk size) verify clean, keep every message and write one Message Index per channel per chunk', () => {
  const b = small({ chunkSize: 100 }), v = verifyMcap(b); assert.deepEqual(v.issues, []);
  assert.ok(v.info.chunks.length > 3); assert.equal(v.info.messages.length, 12);
  for (const c of v.info.chunks) assert.equal(c.indexes.length, new Set(c.rows.map((r) => r.channel)).size);
});
check('mcap: an empty recording and a recording without metadata or attachments verify clean', () => {
  assert.deepEqual(verifyMcap(small({ messages: [], metadata: [], attachments: [] })).issues, []);
  assert.deepEqual(verifyMcap(small({ metadata: [], attachments: [] })).issues, []);
});
const HAS_ZSTD = typeof zlib.zstdCompressSync === 'function';
check(HAS_ZSTD ? 'mcap: zstd chunk compression round-trips to the same messages' : 'mcap: zstd check skipped - this node has no zlib zstd (the default uncompressed path is what the registry pins)', () => {
  if (!HAS_ZSTD) return;
  const a = verifyMcap(small()), z = small({ compression: 'zstd' }), b = verifyMcap(z);
  assert.deepEqual(b.issues, []); assert.equal(b.info.chunks[0].rec.compression, 'zstd');
  assert.deepEqual(b.info.messages.map((m) => [m.channel, m.logTime, m.data.toString('hex')]), a.info.messages.map((m) => [m.channel, m.logTime, m.data.toString('hex')]));
});
check('mcap: the writer is deterministic (same input, same bytes)', () => { assert.ok(small().equals(small())); });
check('mcap: the writer refuses a schema id of zero, a channel with no schema, a message on an unknown channel and unsorted ids', () => {
  assert.throws(() => small({ schemas: [{ id: 0, name: 'x', encoding: 'ros2msg', data: Buffer.alloc(0) }] }), /non-zero/);
  assert.throws(() => small({ channels: [{ id: 1, schemaId: 9, topic: '/a', messageEncoding: 'cdr' }] }), /schema that is not defined/);
  assert.throws(() => small({ messages: [{ channel: 7, sequence: 0, logTime: 0, publishTime: 0, data: Buffer.alloc(1) }] }), /undefined channel/);
});
/* the verifier must name each way a file can be wrong: flip/patch bytes of a good file and expect the code */
const good = small({ chunkSize: 400 });
const patched = (f) => { const b = Buffer.from(good); f(b); return b; };
const find = (b, op, from = 8) => { let p = from; while (p < b.length - 8) { if (b[p] === op) return p; p += 9 + Number(b.readBigUInt64LE(p + 1)); } return -1; };
const summaryStart = (b) => Number(b.readBigUInt64LE(b.length - 8 - 29 + 9));
const MUT = {
  'magic-start': (b) => { b[0] ^= 1; }, 'magic-end': (b) => { b[b.length - 1] ^= 1; },
  'footer-position': (b) => { b[b.length - 8 - 29] = 0x0f; },
  'data-end-crc': (b) => { const p = find(b, OP.DATA_END); b[p + 9] ^= 1; },
  'summary-crc': (b) => { b[b.length - 8 - 4] ^= 1; },
  'chunk-crc': (b) => { const p = find(b, OP.CHUNK); b[p + 9 + 40 + 20] ^= 1; },
  'chunk-time-range': (b) => { const p = find(b, OP.CHUNK); b[p + 9] ^= 1; },
  'statistics-message-count': (b) => { const p = find(b, OP.STATISTICS, summaryStart(b)); b[p + 9] ^= 1; },
  'message-index-entries': (b) => { const p = find(b, OP.MESSAGE_INDEX); b[p + 9 + 2 + 4] ^= 1; },
  'chunk-index-fields': (b) => { const p = find(b, OP.CHUNK_INDEX, summaryStart(b)); b[p + 9] ^= 1; },
  'header-first': (b) => { b[8] = OP.METADATA; },
  'attachment-crc': (b) => { const p = find(b, OP.ATTACHMENT); b[p + 9 + 8] ^= 1; },
};
for (const [code, f] of Object.entries(MUT)) check(`mcap verifier names the fault: ${code}`, () => { const v = verifyMcap(patched(f)); assert.ok(v.issues.includes(code), `expected ${code}, got ${JSON.stringify(v.issues)}`); });
check('mcap verifier: truncating the file, dropping the summary, or reordering messages is caught', () => {
  assert.ok(verifyMcap(good.subarray(0, good.length - 40)).issues.length > 0);
  assert.ok(verifyMcap(good.subarray(0, 100)).issues.length > 0);
  const v = verifyMcap(good); assert.deepEqual(v.issues, []);
  const msgs = v.info.messages.map((m) => ({ ...m })); msgs.reverse();
  const rev = writeMcap({ profile: 'ros2', library: 't', schemas: [...v.info.schemas.values()], channels: [...v.info.channels.values()], messages: msgs.map((m, i) => ({ ...m, logTime: 5000 - i })), chunkSize: 400 });
  assert.deepEqual(verifyMcap(rev).issues, []);   // the writer sorts by time, so a reversed input is still valid ...
  assert.ok(verifyMcap(rev).info.messages.every((m, i, a) => i === 0 || a[i - 1].logTime <= m.logTime));   // ... and comes out in order
});

check('mcap: Chunk Index message_index_offsets are absolute file offsets ("from the start of the file", spec Chunk Index record): each points at a Message Index record of that channel, and the chunk start at its Chunk', () => {
  const buf = small({ chunkSize: 200 }), v = verifyMcap(buf); assert.deepEqual(v.issues, []);
  assert.ok(v.info.summary.chunkIndexes.length > 2);
  for (const ci of v.info.summary.chunkIndexes) {
    assert.equal(buf[ci.chunkStart], OP.CHUNK, 'chunk_start_offset is absolute');
    assert.ok(ci.offsets.length > 0);
    for (const [channel, off] of ci.offsets) {
      assert.equal(buf[off], OP.MESSAGE_INDEX, 'offset ' + off + ' for channel ' + channel + ' is not a Message Index record');
      assert.equal(buf.readUInt16LE(off + 9), channel, 'wrong channel at the offset');
      assert.ok(off >= ci.chunkStart + ci.chunkLength, 'index lies after its chunk');   // a chunk-relative value would fall inside the chunk
    }
  }
});
/* ============================= 5. the corpus ============================= */
const S = splits();
const frameYaw = (q) => Math.atan2(2 * q.w * q.z, 1 - 2 * q.z * q.z);
const angDiff = (a, b) => Math.abs(((a - b + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI);
const dtNs = (i, dt) => Math.round(i * dt * 1e9);

check('split: the TRAIN/TEST seeds are the arena\'s (1-10 / 11-20), disjoint, and cover the declared seeds', () => {
  assert.deepEqual(S.train, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]); assert.deepEqual(S.test, [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]);
  assert.equal(AUTH.split_source, 'robotics/arena/registry/models.json#models[0].split');
  for (const t of arenaTasks(REG)) assert.deepEqual([...S.train, ...S.test].sort((a, b) => a - b), t.seeds);
  assert.equal(splitOf(10, S), 'train'); assert.equal(splitOf(11, S), 'test'); assert.equal(splitOf(21, S), null);
});

/* the expected values come from SEPARATE calls of the source functions, not from the exporter's own episode list */
const claw = scripted(), clawBy = new Map(claw.map((c) => [c.task + '|' + c.level + '|' + c.seed, c]));
const expectSteps = (policy, env, level, seed) => (policy === 'scripted' ? clawBy.get(env + '|' + level + '|' + seed).steps : runEpisode(REG, { policy, env, level, seed }).samples);
const expectedPaths = [];
for (const policy of AUTH.policies) for (const t of arenaTasks(REG)) for (const level of t.levels) for (const seed of t.seeds)
  expectedPaths.push(`${seed <= 10 ? 'train' : 'test'}/${policy}/${t.env.replace('world.', '')}/L${level}_s${String(seed).padStart(2, '0')}.mcap`);

let pubBad = 0;
const rows = [], trajBySplit = { train: new Map(), test: new Map() }, problems = [];
const totals = { messages: 0, bytes: 0, samples: 0, success: 0 };
let verified = 0, decoded = 0;
const flag = (path, what) => { if (problems.length < 40) problems.push(path + ': ' + what); else if (problems.length === 40) problems.push('... more'); };
const t0 = Date.now();
const inspect = (path, buf, row, E) => {
  rows.push(row); totals.messages += row.messages; totals.bytes += buf.length; totals.samples += row.samples; if (row.success) totals.success++;
  const exp = expectSteps(E.policy, E.env, E.level, E.seed);
  const v = verifyMcap(buf); verified++;
  if (v.issues.length) flag(path, 'verifier: ' + v.issues.join(','));
  const I = v.info;
  if (I.header.profile !== 'ros2') flag(path, 'profile');
  if (I.header.library !== AUTH.format.library) flag(path, 'library');
  const tps = topicsFor(E.env), byTopic = new Map([...I.channels.values()].map((c) => [c.topic, c]));
  if (JSON.stringify([...I.channels.values()].map((c) => c.topic)) !== JSON.stringify(tps.map((t) => t.name))) flag(path, 'topic list');
  // schemas: ros2msg, the verbatim text, one per distinct type
  for (const t of tps) {
    const c = byTopic.get(t.name), sc = c && I.schemas.get(c.schemaId);
    if (!c || !sc) { flag(path, 'channel ' + t.name); continue; }
    if (c.messageEncoding !== 'cdr') flag(path, t.name + ' encoding');
    if (sc.name !== t.type || sc.encoding !== 'ros2msg') flag(path, t.name + ' schema name/encoding');
    if (sc.data.toString('utf8') !== schemaText(t.type)) flag(path, t.name + ' schema text is not the verbatim definition');
    if (!/^- history: keep_last\n  depth: \d+\n  reliability: \w+\n  durability: \w+\n/.test(c.metadata.offered_qos_profiles || '')) flag(path, t.name + ' offered_qos_profiles');
  }
  if (I.schemas.size !== new Set(tps.map((t) => t.type)).size) flag(path, 'schema count');
  // counts against the source episode
  const count = (name) => I.messages.filter((m) => m.channel === byTopic.get(name)?.id).length;
  const n = exp.length;
  if (n !== E.steps.length) flag(path, `exported ${E.steps.length} samples but the source episode has ${n}`);
  for (const name of ['/cmd_vel', '/odom', '/sim/ground_truth/pose', '/joint_states']) if (count(name) !== n) flag(path, `${name}: ${count(name)} messages for ${n} source samples`);
  if (count('/instruction') !== 1) flag(path, 'instruction count');
  const grip = REG.envs[E.env].action.fields.some((f) => f.name === 'grip');
  if (grip !== byTopic.has('/gripper_command') || (grip && count('/gripper_command') !== n)) flag(path, 'gripper_command');
  if (I.messages.length !== 1 + n * (grip ? 5 : 4)) flag(path, 'total messages');
  if (I.summary.stats.messageCount !== I.messages.length) flag(path, 'statistics');
  // time: non-decreasing in file order, strictly increasing per channel, log = publish = header stamp, sample k at i*dt
  let last = -1; const lastBy = new Map();
  for (const m of I.messages) { if (m.logTime < last) flag(path, 'time goes backwards'); last = m.logTime; if (m.publishTime !== m.logTime) flag(path, 'publish != log'); if (lastBy.has(m.channel) && m.logTime <= lastBy.get(m.channel)) flag(path, 'time not increasing on channel ' + m.channel); lastBy.set(m.channel, m.logTime); }
  const per = (name) => I.messages.filter((m) => m.channel === byTopic.get(name)?.id);
  const inst = per('/instruction')[0];
  if (inst && (inst.logTime !== 0 || decodeCdr('std_msgs/msg/String', inst.data).data !== clawBy.get(E.env + '|' + E.level + '|' + E.seed).instruction.text)) flag(path, 'instruction');
  // values: decode every message and compare with the source sample through the test's own mapping
  const names = REG.envs[E.env].action.fields.map((f) => f.name), A = (s, k) => (names.includes(k) ? s.a[names.indexOf(k)] : 0);
  const cmd = per('/cmd_vel'), odo = per('/odom'), gt = per('/sim/ground_truth/pose'), js = per('/joint_states'), gr = per('/gripper_command');
  for (let k = 0; k < n; k++) {
    const s = exp[k], t = dtNs(s.i, E.dt_s);
    const c = decodeCdr('geometry_msgs/msg/Twist', cmd[k].data), o = decodeCdr('nav_msgs/msg/Odometry', odo[k].data), g = decodeCdr('geometry_msgs/msg/PoseStamped', gt[k].data), j = decodeCdr('sensor_msgs/msg/JointState', js[k].data);
    decoded += 4;
    for (const m of [cmd[k], odo[k], gt[k], js[k]]) if (m.logTime !== t) flag(path, `sample ${k} at ${m.logTime} ns, want ${t}`);
    for (const h of [o.header, g.header, j.header]) if (h.stamp.sec * 1e9 + h.stamp.nanosec !== t) flag(path, 'header stamp != log time');
    const depth = s.pose.length > 3 ? s.pose[3] : 0;
    const bad = [];
    if (c.linear.x !== A(s, 'v') || c.angular.z !== A(s, 'w') || c.linear.y !== 0 || c.angular.x !== 0 || c.angular.y !== 0) bad.push('cmd_vel');
    if (names.includes('vz') ? c.linear.z !== (A(s, 'vz') === 0 ? 0 : -A(s, 'vz')) : c.linear.z !== 0) bad.push('cmd_vel.z');
    for (const p of [o.pose.pose, g.pose]) {
      if (p.position.x !== s.pose[0] || p.position.y !== s.pose[1] || p.position.z !== (depth === 0 ? 0 : -depth)) bad.push('position');
      if (p.orientation.x !== 0 || p.orientation.y !== 0 || Math.abs(p.orientation.z ** 2 + p.orientation.w ** 2 - 1) > 1e-12) bad.push('quaternion');
      if (angDiff(frameYaw(p.orientation), s.pose[2] + Math.PI / 2) > 1e-9) bad.push('yaw');
    }
    if (o.header.frame_id !== 'odom' || o.child_frame_id !== 'base_link' || g.header.frame_id !== 'map' || j.header.frame_id !== 'base_link') bad.push('frames');
    if (o.twist.twist.linear.x !== s.vel[0] || o.twist.twist.angular.z !== s.vel[1] || o.twist.twist.linear.y !== 0 || o.twist.twist.linear.z !== 0) bad.push('twist');
    if (o.pose.covariance.some((x) => x !== 0) || o.twist.covariance.some((x) => x !== 0)) bad.push('covariance');
    if (JSON.stringify(j.name) !== '["drive_linear","drive_yaw"]' || j.position.length || j.effort.length || j.velocity[0] !== s.vel[0] || j.velocity[1] !== s.vel[1]) bad.push('joint_states');
    if (grip) { const q = decodeCdr('sensor_msgs/msg/JointState', gr[k].data); decoded++; if (JSON.stringify(q.name) !== '["gripper"]' || q.position.length !== 1 || q.position[0] !== A(s, 'grip') || q.velocity.length || q.effort.length) bad.push('gripper'); }
    if (bad.length) { flag(path, `sample ${k}: ${[...new Set(bad)].join(',')}`); break; }
  }
  // metadata, attachment, provenance
  const md = I.metadata.find((m) => m.name === 'smartcitix.episode')?.map;
  if (!md) flag(path, 'no episode metadata'); else {
    for (const [key, want] of Object.entries({ provenance: 'SCRIPTED', not_real_robot_data: 'true', learner_data: 'none', trained_models: '0', licence: 'to be decided by the owner', record: AUTH.schema, policy: E.policy, env: E.env, level: String(E.level), seed: String(E.seed), split: path.split('/')[0], samples: String(n) }))
      if (md[key] !== want) flag(path, `metadata ${key} = ${md[key]}, want ${want}`);
    if (!/exact|no sensor/.test(md.sim_to_real_gap || '') || !/AUTHORED/.test(md.robots_and_arenas || '')) flag(path, 'metadata gap/authored');
    if (E.policy === 'scripted' ? md.claw_sample_id !== clawBy.get(E.env + '|' + E.level + '|' + E.seed).id : md.claw_sample_id !== 'none') flag(path, 'claw_sample_id');
    if (md.outcome_success !== String(E.outcome.success)) flag(path, 'outcome');
    if (md.publication !== AUTH.publication.metadata) pubBad++;
  }
  const att = I.attachments[0];
  if (!att || att.name !== 'scene.json' || att.mediaType !== 'application/json') flag(path, 'scene attachment'); else { try { JSON.parse(att.data.toString('utf8')); } catch { flag(path, 'scene.json is not JSON'); } }
  if (I.metadata.length !== 1 || I.attachments.length !== 1) flag(path, 'metadata/attachment count');
  // split / leakage
  const folder = path.split('/')[0];
  if (folder !== (S.train.includes(E.seed) ? 'train' : S.test.includes(E.seed) ? 'test' : '?')) flag(path, `seed ${E.seed} is in the wrong folder ${folder}`);
  if (folder === 'train' && !S.train.includes(Number(md?.seed))) flag(path, 'a TRAIN file holds a non-TRAIN seed');
  if (folder === 'test' && !S.test.includes(Number(md?.seed))) flag(path, 'a TEST file holds a non-TEST seed');
  const key = E.policy + '|' + E.env + '|' + row.trajectory_sha256;
  trajBySplit[folder].set(key, (trajBySplit[folder].get(key) || 0) + 1);
};
exportAll({ onFile: (path, buf, row, E) => { try { inspect(path, buf, row, E); } catch (e) { flag(path, 'exception: ' + String(e.message).slice(0, 120)); } } });
const secs = ((Date.now() - t0) / 1000).toFixed(0);

check('corpus: 520 files = 2 policies x (3+4+3+3 levels) x 20 seeds, at exactly the expected paths', () => {
  assert.equal(rows.length, 520); assert.deepEqual(rows.map((r) => r.path).sort(), [...expectedPaths].sort()); assert.equal(new Set(rows.map((r) => r.path)).size, 520);
});
check(`corpus: every file passes the MCAP verifier, the verbatim-schema, count, time, value, metadata and split checks (${verified} files, ${decoded} messages decoded, ${secs} s)`, () => {
  assert.equal(verified, 520); assert.deepEqual(problems, []);
});
check('corpus: the scripted files are the 260 Omega Claw samples (every claw sample id appears once) and the greedy files use the same instructions', () => {
  assert.equal(claw.length, 260);
  const ids = new Set(); for (const r of rows.filter((x) => x.policy === 'scripted')) ids.add(clawBy.get('world.' + r.task + '|' + r.level + '|' + r.seed).id);
  assert.equal(ids.size, 260); assert.equal(rows.filter((r) => r.policy === 'greedy').length, 260);
});
check('leakage: no TEST seed appears in a TRAIN file and no TRAIN seed in a TEST file; no trajectory is shared across the two folders', () => {
  assert.ok(rows.filter((r) => r.path.startsWith('train/')).every((r) => r.seed >= 1 && r.seed <= 10));
  assert.ok(rows.filter((r) => r.path.startsWith('test/')).every((r) => r.seed >= 11 && r.seed <= 20));
  for (const k of trajBySplit.train.keys()) assert.ok(!trajBySplit.test.has(k), 'trajectory shared across splits: ' + k.slice(0, 60));
  assert.equal(rows.filter((r) => r.split === 'train').length, 260); assert.equal(rows.filter((r) => r.split === 'test').length, 260);
});
check('timestamps: every file spans more than 0 and at most 60 s of simulated time (300 samples at 5 Hz is the recorder cap)', () => {
  for (const r of rows) assert.ok(r.duration_s > 0 && r.duration_s <= 60, r.path + ' ' + r.duration_s);
});
check('sizes: no file is larger than 1 MiB uncompressed, and the total is reported to the byte', () => {
  assert.ok(Math.max(...rows.map((r) => r.bytes)) < 1048576); assert.equal(totals.bytes, rows.reduce((a, r) => a + r.bytes, 0));
});

/* ---- frame mapping against the simulator's own update rule ---- */
check('frames: x = e, y = n, yaw_ros = yaw + pi/2, angular.z = w match one real simulator step (unicycle: e -= v sin(yaw) dt, n += v cos(yaw) dt)', () => {
  const env = REG.envs['world.litter-pickup'], emb = REG.embodiments[env.embodiments[0]], dt = env.episode_cap.dt_s;
  const st = RoboCore.reset(env, emb, 1, 1), before = { x: st.e, y: st.n, yaw: st.yaw + Math.PI / 2 };
  RoboCore.step(st, { v: 1.0, w: 0.5 });
  const after = { x: st.e, y: st.n, yaw: st.yaw + Math.PI / 2 };
  assert.ok(Math.abs(after.yaw - before.yaw - 0.5 * dt) < 1e-12, 'angular.z = +w turns yaw_ros by w dt');
  assert.ok(Math.abs(after.x - before.x - 1.0 * dt * Math.cos(after.yaw)) < 1e-12, 'x moves along cos(yaw_ros)');
  assert.ok(Math.abs(after.y - before.y - 1.0 * dt * Math.sin(after.yaw)) < 1e-12, 'y moves along sin(yaw_ros)');
  assert.ok(Math.abs(before.yaw - Math.PI / 2) < 1e-12 && after.y > before.y, 'yaw 0 faces north = +y');
});
check('frames: the ROV\'s depth is positive down in the simulator, so z = -depth and linear.z = -vz', () => {
  const env = REG.envs['world.rov-survey'], emb = REG.embodiments[env.embodiments[0]];
  const st = RoboCore.reset(env, emb, 1, 1); RoboCore.step(st, { v: 0, w: 0, vz: 1.0 });
  assert.ok(st.depth > 0, 'a positive vz dives');
  const E = [...episodes({ policies: ['scripted'] })].find((x) => x.env === 'world.rov-survey' && x.seed === 1 && x.level === 1);
  assert.deepEqual(E.names, ['v', 'w', 'vz']);
});

/* ============================= 6. the card and the registry ============================= */
const card = read(REL('DATASET_CARD.md')), reg = JSON.parse(read(REL('registry/ros.json')));
const sum = summarise(rows, S);
check('card: regenerating the card from the rebuilt files gives the committed card, byte for byte', () => { assert.equal(card, renderCard(rows, sum)); });
check('card: its counts equal the files\' (files, messages, time steps, bytes, per policy, per task, per split, successes, digest)', () => {
  const g = (re) => { const m = re.exec(card); assert.ok(m, 'card lacks ' + re); return m; };
  let m = g(/- (\d+) files, (\d+) messages, (\d+) time steps sampled at ([\d/]+) Hz of simulation time\. Total (\d+) bytes uncompressed/);
  assert.deepEqual(m.slice(1, 6).map((x, i) => (i === 3 ? x : Number(x))), [rows.length, totals.messages, totals.samples, '5', totals.bytes]);
  m = g(/By source policy: scripted (\d+), greedy (\d+)\. By task: litter-pickup (\d+), litter-sort (\d+), rov-survey (\d+), gate-drive (\d+)\./);
  const c = (f) => rows.filter(f).length;
  assert.deepEqual(m.slice(1).map(Number), [c((r) => r.policy === 'scripted'), c((r) => r.policy === 'greedy'), c((r) => r.task === 'litter-pickup'), c((r) => r.task === 'litter-sort'), c((r) => r.task === 'rov-survey'), c((r) => r.task === 'gate-drive')]);
  m = g(/TRAIN seeds (\d+)-(\d+) = (\d+) files, TEST seeds (\d+)-(\d+) = (\d+) files/);
  assert.deepEqual(m.slice(1).map(Number), [1, 10, c((r) => r.path.startsWith('train/')), 11, 20, c((r) => r.path.startsWith('test/'))]);
  m = g(/(\d+) of (\d+) episodes met their task/); assert.deepEqual(m.slice(1).map(Number), [totals.success, rows.length]);
  m = g(/Digest of all file hashes: ([0-9a-f]{16})/); assert.equal(m[1], createHash('sha256').update(JSON.stringify(rows.map((r) => [r.path, r.sha256]))).digest('hex').slice(0, 16));
  m = g(/\n  files: (\d+)\n  messages: (\d+)\n  trained_models: 0\n---/); assert.deepEqual(m.slice(1).map(Number), [rows.length, totals.messages]);
});
check('card: Hugging Face-style front matter and the tc-dataset/1 sections are all there, and the licence is left to the owner', () => {
  assert.match(card, /^---\nlicense: other\nlicense_name: to be decided by the owner\n/);
  for (const id of ['motivation', 'composition', 'collection', 'preprocessing', 'uses', 'distribution', 'maintenance']) assert.ok(card.includes(`<!-- section:${id} -->`), id);
  assert.match(card, /Licence: to be decided by the owner/);
});
check('card: says SCRIPTED, NOT real robot data, NOT learner data, trained_models 0, the sim-to-real gap, the refusal of a path to hardware, and what was NOT verified', () => {
  for (const re of [/Provenance SCRIPTED/, /NOT real robot data/, /NOT learner data/, /trained_models is 0/, /Sim-to-real gap: Large and unmeasured/, /no sensor model or noise/, /provides no path to hardware/, /named human operator/, /ros2 bag play is unverified/, /AUTHORED and SCHEMATIC/, /PROPOSED mapping/]) assert.match(card, re);
});
check('registry: ros.json lists every file with its bytes and sha256, equal to the rebuilt files, and the counts equal them', () => {
  assert.equal(reg.files.length, 520);
  const by = new Map(rows.map((r) => [r.path, r]));
  for (const [path, bytes, hash, samples, messages, success] of reg.files) { const r = by.get(path); assert.ok(r, path); assert.deepEqual([bytes, hash, samples, messages, success], [r.bytes, r.sha256, r.samples, r.messages, +r.success], path); }
  assert.deepEqual(reg.counts, { files: 520, messages: totals.messages, samples: totals.samples, bytes_uncompressed: totals.bytes, policies: 2, topics: 6, message_types: 5, vendored_msg_files: 13, trained_models: 0, learner_episodes: 0 });
  assert.deepEqual(reg.summary, JSON.parse(JSON.stringify(sum)));
});
check('registry: pack fields, provenance, honesty and the unset licence are in place', () => {
  assert.equal(reg.pack, 'smartcitix-robotics-ros'); assert.equal(reg.schema, 'ros-export/1'); assert.match(reg.source_stamp, /^[0-9a-f]{16}$/);
  assert.deepEqual(reg.honesty, AUTH.honesty); assert.equal(reg.honesty.licence, 'to be decided by the owner');
  assert.deepEqual(reg.format, AUTH.format); assert.equal(reg.counts.trained_models, 0);
  assert.equal(REG.counts.trained_models, 2, 'the repo count is read, not copied: this pack uses none of them');
});
check('registry: the source stamps match the files on disk (a stale registry would fail here)', () => {
  for (const [rel, st] of Object.entries(reg.source_stamps)) assert.equal(sha(readFileSync(join(ROOT, rel))).slice(0, 16), st, rel + ' changed since the registry was built');
});

check('publication: the card opens with the rule and repeats it in the licence section', () => {
  const rule = 'Not for publication: do not upload or share this dataset until the owner sets its licence.';
  assert.equal(AUTH.publication.rule, rule);
  assert.ok(card.split('\n---\n')[1].trimStart().startsWith('> **' + rule + '**'), 'rule is not the first line of the card body');
  const dist = card.slice(card.indexOf('<!-- section:distribution -->'), card.indexOf('<!-- section:maintenance -->'));
  assert.ok(dist.includes(rule), 'rule missing from the distribution section');
});
check('publication: every file\'s metadata record carries "not for publication until the owner sets the licence"', () => {
  assert.equal(AUTH.publication.metadata, 'not for publication until the owner sets the licence'); assert.equal(pubBad, 0, pubBad + ' file(s) lack it');
});
check('publication: the licence field still reads "to be decided by the owner" (card, authored file, registry)', () => {
  assert.equal(AUTH.licence_field, 'to be decided by the owner'); assert.match(card, /license_name: to be decided by the owner\n/); assert.equal(reg.honesty.licence, 'to be decided by the owner'); assert.deepEqual(reg.publication, AUTH.publication);
});

check('conformance: the stated reader count equals the readers listed, in the authored file, the registry and the card', () => {
  const words = { one: 1, two: 2, three: 3, four: 4, five: 5 };
  for (const text of [AUTH.honesty.conformance, reg.honesty.conformance, card]) {
    const m = /by (\w+) independent open-source readers/.exec(text); assert.ok(m, 'no reader count stated');
    assert.equal(words[m[1]], AUTH.validated_by.length, `states ${m[1]}, lists ${AUTH.validated_by.length}`);
  }
  assert.equal(AUTH.validated_by.length, 3); assert.equal(new Set(AUTH.validated_by).size, 3);
  assert.ok(card.includes(AUTH.honesty.conformance), 'the card carries the conformance sentence verbatim');
  for (const n of ['mcap', 'rosbags', '@mcap/core']) assert.ok(AUTH.honesty.conformance.includes(n), n + ' is named in the text');
});

/* ============================= 7. honesty and hygiene of the pack's own files ============================= */
const PACK = ['DATASET_CARD.md', 'registry/ros.json', 'authored/ros.json', 'build.py', 'export.mjs', 'mcap.mjs', 'ros2msg.mjs', 'test.mjs'];
check('honesty: no buyer, price, deal, demand or revenue wording anywhere in the pack or its card', () => {
  const re = /\b(buyer|buyers|customer|customers|price|prices|pricing|sell|selling|sold|sale|purchase|deal|deals|demand|revenue|invoice|market|commercial|monetis|monetiz|pilot|LOI)\b/i;
  for (const f of PACK.filter((x) => x !== 'test.mjs')) { const t = read(REL(f)); const m = re.exec(t); assert.ok(!m, f + ' contains "' + (m && m[0]) + '"'); }
});
check('hygiene: no machine path, no secret key, no model identifier, no network import in the pack\'s files', () => {
  for (const f of PACK.filter((x) => x !== 'test.mjs')) {
    const t = read(REL(f));
    assert.ok(!/(^|[^A-Za-z.])(\/tmp\/|\/home\/|\/root\/|\/Users\/|\/opt\/)/.test(t), f + ' holds a machine path');
    assert.ok(!/\brk_[A-Za-z0-9]{8,}/.test(t), f + ' holds a key');
    assert.ok(!/\b(claude|anthropic|gpt-?\d|sonnet|opus|haiku)\b/i.test(t), f + ' names a model');
    if (/\.(mjs|py)$/.test(f)) assert.ok(!/node:(http|https|net|dgram|tls)|\bfetch\(|XMLHttpRequest|WebSocket|urllib|\brequests\b|\bsocket\b/.test(t), f + ' reaches for the network');
  }
});
check('safety: nothing in the pack can reach hardware - no serial, USB, ROS client, shell-out or process spawn in the exporter and its libraries', () => {
  for (const f of ['export.mjs', 'mcap.mjs', 'ros2msg.mjs']) assert.ok(!/child_process|node:worker_threads|serialport|rclnodejs|rclpy|roslib|\bexecSync\(|\bexecFile|\bspawn(Sync)?\(/.test(read(REL(f))), f);
});
check('every topic and the format are the ones the MCAP ros2 profile names (profile ros2, message encoding cdr, schema encoding ros2msg, offered_qos_profiles on each channel)', () => {
  assert.deepEqual([AUTH.format.profile, AUTH.format.message_encoding, AUTH.format.schema_encoding], ['ros2', 'cdr', 'ros2msg']);
  assert.ok(AUTH.topics.every((t) => t.name.startsWith('/') && t.qos && ['reliable', 'best_effort'].includes(t.qos.reliability)));
});

console.log(`${passed} ok, ${failed} failed (${rows.length} files, ${totals.messages} messages, ${totals.bytes} bytes built in memory)`);
process.exit(failed ? 1 : 0);
