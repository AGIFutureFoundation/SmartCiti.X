/* robotics/ros/ros2msg.mjs - ROS 2 `.msg` definitions (vendored byte for byte under robotics/ros/msgs/), the MCAP
 * `ros2msg` schema text, and a CDR encoder/decoder for them. No network, no ROS install needed.
 *
 *  - The .msg files are the ROS 2 `jazzy` branch of ros2/common_interfaces and ros2/rcl_interfaces at the commits
 *    pinned in robotics/ros/authored/ros.json (compared byte for byte with a fresh clone when they were vendored).
 *  - schemaText(type): the text rosbag2 stores as an MCAP schema with encoding `ros2msg`: the root .msg file
 *    unchanged, then for every dependency (depth-first, the names of one file's dependencies in sorted order, each type once)
 *    "\n" + 80 '=' + "\nMSG: <pkg>/<Type>\n" + its .msg file. This follows rosbag2_cpp's
 *    LocalMessageDefinitionSource::get_full_text (ros2/rosbag2 jazzy, rosbag2_cpp/src/rosbag2_cpp/message_definitions/
 *    local_message_definition_source.cpp, commit 12b5e8ba4eb5665501a16f0d9e050552a1149f56) and the MCAP registry entry for `ros2msg`.
 *  - encodeCdr / decodeCdr: XCDR1 little endian with the 4-byte encapsulation header 00 01 00 00 (the framing the MCAP
 *    registry names for message encoding `cdr`), alignment counted from the first byte after that header: 1/2/4/8-byte
 *    primitives aligned to their size, a string = uint32 length (including the NUL) + bytes + NUL, an unbounded
 *    sequence = uint32 count + elements, a fixed array = its elements only. No trailing padding is added. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
export const MSG_DIR = join(HERE, 'msgs');
export const DELIM = '='.repeat(80);
const PRIM = { bool: 1, byte: 1, char: 1, int8: 1, uint8: 1, int16: 2, uint16: 2, int32: 4, uint32: 4, float32: 4, int64: 8, uint64: 8, float64: 8 };
const need = (c, m) => { if (!c) throw new Error('ros2msg: ' + m); };

const cache = new Map();
/* 'geometry_msgs/Twist' | 'geometry_msgs/msg/Twist' -> 'geometry_msgs/Twist' (the form a .msg file and the MSG: line use) */
export const shortName = (t) => { const p = t.split('/'); need(p.length === 2 || (p.length === 3 && p[1] === 'msg'), 'bad type name ' + t); return p[0] + '/' + p[p.length - 1]; };
export const fullName = (t) => { const [p, n] = shortName(t).split('/'); return p + '/msg/' + n; };
export function msgText(t, dir = MSG_DIR) {
  const [pkg, name] = shortName(t).split('/'), k = dir + '|' + t;
  if (!cache.has(k)) cache.set(k, readFileSync(join(dir, pkg, 'msg', name + '.msg'), 'utf8'));
  return cache.get(k);
}
export const msgBytes = (t, dir = MSG_DIR) => { const [pkg, name] = shortName(t).split('/'); return readFileSync(join(dir, pkg, 'msg', name + '.msg')); };
export const sha256 = (b) => createHash('sha256').update(b).digest('hex');
export const gitBlobSha1 = (b) => createHash('sha1').update(Buffer.concat([Buffer.from(`blob ${b.length}\0`), b])).digest('hex');

/* the same field-type regex rosbag2 uses to find dependencies: a type at the start of a line, optional [..], then whitespace */
const FIELD_TYPE = /(?:^|\n)\s*([a-zA-Z0-9_/]+)(?:\[[^\]]*\])?\s+/g;
function dependencies(text, pkg) {
  const out = new Set();
  for (const m of text.matchAll(FIELD_TYPE)) {
    const t = m[1];
    if (t in PRIM || t === 'string') continue;
    out.add(t.includes('/') ? t : pkg + '/' + t);
  }
  return [...out].sort();
}
export function schemaText(type, dir = MSG_DIR) {
  const seen = new Set();
  const rec = (t, depth) => {
    need(depth > 0, 'recursion too deep resolving ' + type);
    const text = msgText(t, dir);
    let res = text;
    for (const d of dependencies(text, shortName(t).split('/')[0])) {
      if (seen.has(d)) continue;
      seen.add(d);
      res += '\n' + DELIM + '\nMSG: ' + d + '\n' + rec(d, depth - 1);
    }
    return res;
  };
  return rec(shortName(type), 32);
}

/* ---- parse a .msg into fields: { type, array: null | {fixed:N} | {seq:true}, name } ---- */
const fieldCache = new Map();
export function fields(type, dir = MSG_DIR) {
  const key = dir + '|' + shortName(type);
  if (!fieldCache.has(key)) fieldCache.set(key, parseFields(shortName(type), dir));
  return fieldCache.get(key);
}
function parseFields(type, dir) {
  const [pkg] = type.split('/'), out = [];
  for (const raw of msgText(type, dir).split('\n')) {
    const line = raw.replace(/#.*$/, '').trim();
    if (!line) continue;
    if (/^\S+\s+[A-Z][A-Z0-9_]*\s*=/.test(line)) continue;   // a constant, not a field
    const m = /^([A-Za-z0-9_/]+)(?:\[(<=)?(\d*)\])?\s+([a-z][a-z0-9_]*)(?:\s+(.*))?$/.exec(line);
    need(m, 'cannot parse line "' + line + '" in ' + type);
    let t = m[1];
    const isArr = line.slice(m[1].length).startsWith('[');
    need(!m[2], 'bounded sequences are not used by the vendored types');
    const array = isArr ? (m[3] === '' ? { seq: true } : { fixed: Number(m[3]) }) : null;
    if (!(t in PRIM) && t !== 'string') t = t.includes('/') ? shortName(t) : pkg + '/' + t;
    out.push({ type: t, array, name: m[4] });
  }
  return out;
}

/* ---- CDR ---- */
class Out {
  constructor() { this.b = []; this.n = 0; }
  align(a) { const pad = (a - (this.n % a)) % a; if (pad) { this.b.push(Buffer.alloc(pad)); this.n += pad; } }
  put(buf) { this.b.push(buf); this.n += buf.length; }
}
function wprim(o, t, v) {
  const size = PRIM[t]; o.align(size);
  const b = Buffer.alloc(size);
  switch (t) {
    case 'bool': need(typeof v === 'boolean', 'bool field is not a boolean'); b.writeUInt8(v ? 1 : 0); break;
    case 'byte': case 'char': case 'uint8': b.writeUInt8(v); break;
    case 'int8': b.writeInt8(v); break;
    case 'int16': b.writeInt16LE(v); break;
    case 'uint16': b.writeUInt16LE(v); break;
    case 'int32': b.writeInt32LE(v); break;
    case 'uint32': b.writeUInt32LE(v); break;
    case 'int64': b.writeBigInt64LE(BigInt(v)); break;
    case 'uint64': b.writeBigUInt64LE(BigInt(v)); break;
    case 'float32': b.writeFloatLE(v); break;
    case 'float64': need(typeof v === 'number' && Number.isFinite(v), 'float64 field is not a finite number'); b.writeDoubleLE(v); break;
    default: throw new Error('ros2msg: primitive ' + t);
  }
  o.put(b);
}
function wvalue(o, f, v, dir) {
  const one = (x) => {
    if (f.type === 'string') { need(typeof x === 'string', 'string field ' + f.name + ' is not a string'); const d = Buffer.from(x, 'utf8'); o.align(4); const l = Buffer.alloc(4); l.writeUInt32LE(d.length + 1); o.put(l); o.put(d); o.put(Buffer.alloc(1)); }
    else if (f.type in PRIM) wprim(o, f.type, x);
    else wmsg(o, f.type, x, dir);
  };
  if (!f.array) return one(v);
  need(Array.isArray(v), 'field ' + f.name + ' must be an array');
  if (f.array.fixed !== undefined) need(v.length === f.array.fixed, `field ${f.name} needs ${f.array.fixed} elements, has ${v.length}`);
  else { o.align(4); const l = Buffer.alloc(4); l.writeUInt32LE(v.length); o.put(l); }
  for (const x of v) one(x);
}
function wmsg(o, type, val, dir) {
  const fs = fields(type, dir);
  need(val && typeof val === 'object', 'value for ' + type + ' is not an object');
  const extra = Object.keys(val).filter((k) => !fs.some((f) => f.name === k));
  need(!extra.length, `${type} has no field ${extra.join(',')}`);
  for (const f of fs) { need(f.name in val, `${type}.${f.name} is missing`); wvalue(o, f, val[f.name], dir); }
}
export function encodeCdr(type, value, dir = MSG_DIR) {
  const o = new Out();
  wmsg(o, shortName(type), value, dir);
  return Buffer.concat([Buffer.from([0x00, 0x01, 0x00, 0x00]), ...o.b]);
}

class In {
  constructor(buf) { need(buf.length >= 4 && buf[0] === 0 && buf[1] === 1 && buf[2] === 0 && buf[3] === 0, 'not an XCDR1 little-endian payload (encapsulation header 00 01 00 00)'); this.buf = buf; this.p = 4; }
  align(a) { this.p += (a - ((this.p - 4) % a)) % a; }
  take(n) { need(this.p + n <= this.buf.length, 'payload ends inside a field'); const s = this.buf.subarray(this.p, this.p + n); this.p += n; return s; }
}
function rprim(i, t) {
  const size = PRIM[t]; i.align(size); const b = i.take(size);
  switch (t) {
    case 'bool': return b[0] === 1; case 'byte': case 'char': case 'uint8': return b.readUInt8(); case 'int8': return b.readInt8();
    case 'int16': return b.readInt16LE(); case 'uint16': return b.readUInt16LE(); case 'int32': return b.readInt32LE(); case 'uint32': return b.readUInt32LE();
    case 'int64': return Number(b.readBigInt64LE()); case 'uint64': return Number(b.readBigUInt64LE()); case 'float32': return b.readFloatLE(); case 'float64': return b.readDoubleLE();
  }
}
function rvalue(i, f, dir) {
  const one = () => {
    if (f.type === 'string') { i.align(4); const n = i.take(4).readUInt32LE(); need(n >= 1, 'string length 0'); const s = i.take(n); need(s[n - 1] === 0, 'string is not NUL terminated'); return s.subarray(0, n - 1).toString('utf8'); }
    if (f.type in PRIM) return rprim(i, f.type);
    return rmsg(i, f.type, dir);
  };
  if (!f.array) return one();
  let n;
  if (f.array.fixed !== undefined) n = f.array.fixed; else { i.align(4); n = i.take(4).readUInt32LE(); }
  return Array.from({ length: n }, one);
}
function rmsg(i, type, dir) { const o = {}; for (const f of fields(type, dir)) o[f.name] = rvalue(i, f, dir); return o; }
export function decodeCdr(type, buf, dir = MSG_DIR) {
  const i = new In(buf), v = rmsg(i, shortName(type), dir);
  need(i.p === buf.length, `${buf.length - i.p} byte(s) left over after ${type}`);
  return v;
}
