/* robotics/ros/mcap.mjs - a small, dependency-free MCAP writer and a strict verifier, written from the MCAP format
 * specification (https://mcap.dev/spec = foxglove/mcap website/docs/spec/index.md and registry.md, read at commit
 * 6911a08f6bf91a0d43b34005a613ae6f4c74e8f6). Records, field order and widths follow that text; nothing here
 * is copied from a library. It trains nothing and opens no network connection.
 *
 *   writeMcap({...}) -> Buffer     one indexed file: Header, chunks (+ Message Index), Metadata, Attachments, Data End,
 *                                  Summary (Schema, Channel, Statistics, Chunk Index, Attachment Index, Metadata Index,
 *                                  grouped by opcode), Summary Offset, Footer, trailing magic.
 *   verifyMcap(buf) -> { issues, info }   reads the file back strictly (sequentially, then through the index) and names
 *                                  every disagreement: issues are short codes such as `data-end-crc`; info holds the
 *                                  parsed header, schemas, channels, per-channel messages and statistics.
 *
 * Multi-byte integers are little-endian; a String is a uint32 byte length then UTF-8; a Map is a uint32 byte length
 * then its entries; a Timestamp is a uint64 of nanoseconds. Chunk compression is "" (default) or "zstd" (node's zlib). */
import zlib from 'node:zlib';

export const MAGIC = Buffer.from([0x89, 0x4d, 0x43, 0x41, 0x50, 0x30, 0x0d, 0x0a]);   // 0x89 M C A P 0x30 \r \n
export const OP = { HEADER: 0x01, FOOTER: 0x02, SCHEMA: 0x03, CHANNEL: 0x04, MESSAGE: 0x05, CHUNK: 0x06, MESSAGE_INDEX: 0x07, CHUNK_INDEX: 0x08,
  ATTACHMENT: 0x09, ATTACHMENT_INDEX: 0x0a, STATISTICS: 0x0b, METADATA: 0x0c, METADATA_INDEX: 0x0d, SUMMARY_OFFSET: 0x0e, DATA_END: 0x0f };

/* ---- CRC-32 (IEEE 802.3, the one zlib.crc32 computes; table form so it needs no particular node version) ---- */
const TABLE = new Uint32Array(256);
for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; TABLE[n] = c >>> 0; }
export function crc32(buf, crc = 0) {
  let c = (crc ^ 0xffffffff) >>> 0;
  for (let i = 0; i < buf.length; i++) c = TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

/* ---- serialisation helpers ---- */
const u8 = (n) => Buffer.from([n]);
const u16 = (n) => { const b = Buffer.alloc(2); b.writeUInt16LE(n); return b; };
const u32 = (n) => { const b = Buffer.alloc(4); b.writeUInt32LE(n >>> 0); return b; };
const u64 = (n) => { const b = Buffer.alloc(8); b.writeBigUInt64LE(BigInt(n)); return b; };
const str = (s) => { const d = Buffer.from(s, 'utf8'); return Buffer.concat([u32(d.length), d]); };
const bytes32 = (d) => Buffer.concat([u32(d.length), d]);
const bytes64 = (d) => Buffer.concat([u64(d.length), d]);
const mapStrStr = (o) => { const body = Buffer.concat(Object.entries(o).flatMap(([k, v]) => [str(k), str(String(v))])); return Buffer.concat([u32(body.length), body]); };
const mapU16U64 = (entries) => { const body = Buffer.concat(entries.flatMap(([k, v]) => [u16(k), u64(v)])); return Buffer.concat([u32(body.length), body]); };
const rec = (op, content) => Buffer.concat([u8(op), u64(content.length), content]);

const need = (c, m) => { if (!c) throw new Error('mcap: ' + m); };

/* opts: { profile, library, schemas:[{id,name,encoding,data:Buffer}], channels:[{id,schemaId,topic,messageEncoding,metadata}],
 *         messages:[{channel,sequence,logTime,publishTime,data:Buffer}] (any order; written sorted by logTime then channel),
 *         metadata:[{name,map}], attachments:[{logTime,createTime,name,mediaType,data}], chunkSize, compression } */
export function writeMcap(opts) {
  const { profile, library, schemas, channels, metadata = [], attachments = [], chunkSize = 262144, compression = '' } = opts;
  need(compression === '' || compression === 'zstd', 'compression must be "" or "zstd"');
  if (compression === 'zstd') need(typeof zlib.zstdCompressSync === 'function', 'this node has no zlib zstd');
  const sid = new Set(schemas.map((s) => s.id)), cid = new Set(channels.map((c) => c.id));
  need(!sid.has(0) && sid.size === schemas.length, 'schema ids must be unique and non-zero');
  need(cid.size === channels.length, 'channel ids must be unique');
  for (const c of channels) need(c.schemaId === 0 || sid.has(c.schemaId), 'channel ' + c.topic + ' names a schema that is not defined');
  const msgs = opts.messages.map((m, n) => ({ ...m, n })).sort((a, b) => (a.logTime - b.logTime) || (a.channel - b.channel) || (a.n - b.n));
  for (const m of msgs) need(cid.has(m.channel), 'message on undefined channel ' + m.channel);

  const out = []; let pos = 0;
  const push = (b) => { out.push(b); pos += b.length; };
  push(MAGIC);
  push(rec(OP.HEADER, Buffer.concat([str(profile), str(library)])));

  const schemaRec = (s) => rec(OP.SCHEMA, Buffer.concat([u16(s.id), str(s.name), str(s.encoding), bytes32(s.data)]));
  const channelRec = (c) => rec(OP.CHANNEL, Buffer.concat([u16(c.id), u16(c.schemaId), str(c.topic), str(c.messageEncoding), mapStrStr(c.metadata || {})]));
  const msgRec = (m) => rec(OP.MESSAGE, Buffer.concat([u16(m.channel), u32(m.sequence), u64(m.logTime), u64(m.publishTime), m.data]));

  // group messages into chunks by uncompressed size; the first chunk carries the Schema and Channel records
  const chunks = [];
  let cur = null;
  const open = () => { cur = { parts: [], size: 0, msgs: [], start: null, end: null }; chunks.push(cur); };
  open();
  for (const s of schemas) { const b = schemaRec(s); cur.parts.push(b); cur.size += b.length; }
  for (const c of channels) { const b = channelRec(c); cur.parts.push(b); cur.size += b.length; }
  for (const m of msgs) {
    if (cur.msgs.length && cur.size >= chunkSize) open();
    const b = msgRec(m);
    cur.msgs.push({ channel: m.channel, logTime: m.logTime, offset: cur.size });
    cur.parts.push(b); cur.size += b.length;
    cur.start = cur.start === null ? m.logTime : Math.min(cur.start, m.logTime); cur.end = cur.end === null ? m.logTime : Math.max(cur.end, m.logTime);
  }

  const chunkIndexes = [];
  for (const ch of chunks) {
    const records = Buffer.concat(ch.parts);
    const body = compression === 'zstd' ? zlib.zstdCompressSync(records) : records;
    const chunkStart = pos;
    push(rec(OP.CHUNK, Buffer.concat([u64(ch.start ?? 0), u64(ch.end ?? 0), u64(records.length), u32(crc32(records)), str(compression), bytes64(body)])));
    const chunkLength = pos - chunkStart;
    // one Message Index per channel that has a message in this chunk, immediately after the chunk
    const byCh = new Map();
    for (const m of ch.msgs) { if (!byCh.has(m.channel)) byCh.set(m.channel, []); byCh.get(m.channel).push(m); }
    const offsets = []; const idxStart = pos;
    for (const c of [...byCh.keys()].sort((a, b) => a - b)) {
      offsets.push([c, pos]);
      const body2 = Buffer.concat(byCh.get(c).flatMap((m) => [u64(m.logTime), u64(m.offset)]));
      push(rec(OP.MESSAGE_INDEX, Buffer.concat([u16(c), u32(body2.length), body2])));
    }
    chunkIndexes.push({ start: ch.start ?? 0, end: ch.end ?? 0, chunkStart, chunkLength, offsets, idxLength: pos - idxStart, compression, compressed: body.length, uncompressed: records.length });
  }

  const metaIdx = [];
  for (const m of metadata) { const at = pos; push(rec(OP.METADATA, Buffer.concat([str(m.name), mapStrStr(m.map)]))); metaIdx.push({ offset: at, length: pos - at, name: m.name }); }
  const attIdx = [];
  for (const a of attachments) {
    const head = Buffer.concat([u64(a.logTime), u64(a.createTime), str(a.name), str(a.mediaType), bytes64(a.data)]);
    const at = pos; push(rec(OP.ATTACHMENT, Buffer.concat([head, u32(crc32(head))])));
    attIdx.push({ offset: at, length: pos - at, logTime: a.logTime, createTime: a.createTime, size: a.data.length, name: a.name, mediaType: a.mediaType });
  }

  push(rec(OP.DATA_END, u32(crc32(Buffer.concat(out)))));

  // summary section: records grouped by opcode
  const summaryStart = pos;
  const groups = [];
  const group = (op, recs) => { if (!recs.length) return; const start = pos; for (const r of recs) push(r); groups.push({ op, start, length: pos - start }); };
  group(OP.SCHEMA, schemas.map(schemaRec));
  group(OP.CHANNEL, channels.map(channelRec));
  const counts = new Map(); for (const m of msgs) counts.set(m.channel, (counts.get(m.channel) || 0) + 1);
  const all = msgs.length ? [msgs[0].logTime, msgs[msgs.length - 1].logTime] : [0, 0];
  group(OP.STATISTICS, [rec(OP.STATISTICS, Buffer.concat([u64(msgs.length), u16(schemas.length), u32(channels.length), u32(attachments.length), u32(metadata.length), u32(chunks.length),
    u64(all[0]), u64(all[1]), mapU16U64([...counts.entries()].sort((a, b) => a[0] - b[0]))]))]);
  group(OP.CHUNK_INDEX, chunkIndexes.map((c) => rec(OP.CHUNK_INDEX, Buffer.concat([u64(c.start), u64(c.end), u64(c.chunkStart), u64(c.chunkLength), mapU16U64(c.offsets), u64(c.idxLength), str(c.compression), u64(c.compressed), u64(c.uncompressed)]))));
  group(OP.ATTACHMENT_INDEX, attIdx.map((a) => rec(OP.ATTACHMENT_INDEX, Buffer.concat([u64(a.offset), u64(a.length), u64(a.logTime), u64(a.createTime), u64(a.size), str(a.name), str(a.mediaType)]))));
  group(OP.METADATA_INDEX, metaIdx.map((m) => rec(OP.METADATA_INDEX, Buffer.concat([u64(m.offset), u64(m.length), str(m.name)]))));
  const summaryOffsetStart = pos;
  for (const g of groups) push(rec(OP.SUMMARY_OFFSET, Buffer.concat([u8(g.op), u64(g.start), u64(g.length)])));
  // footer: the CRC covers everything from the start of the summary through summary_offset_start (inclusive)
  const footHead = Buffer.concat([u8(OP.FOOTER), u64(20), u64(summaryStart), u64(summaryOffsetStart)]);
  const all2 = Buffer.concat(out);
  const crc = crc32(Buffer.concat([all2.subarray(summaryStart), footHead]));
  push(footHead); push(u32(crc)); push(MAGIC);
  return Buffer.concat(out);
}

/* ---- the strict verifier ---- */
class Cur {
  constructor(buf, at = 0, end = buf.length) { this.b = buf; this.p = at; this.end = end; }
  left() { return this.end - this.p; }
  take(n) { if (n < 0 || this.p + n > this.end) throw new Error('truncated'); const s = this.b.subarray(this.p, this.p + n); this.p += n; return s; }
  u8() { return this.take(1)[0]; }
  u16() { return this.take(2).readUInt16LE(); }
  u32() { return this.take(4).readUInt32LE(); }
  u64() { const v = this.take(8).readBigUInt64LE(); if (v > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('u64 beyond 2^53'); return Number(v); }
  str() { const n = this.u32(); const s = this.take(n); const t = s.toString('utf8'); if (Buffer.from(t, 'utf8').compare(s) !== 0) throw new Error('string is not valid UTF-8'); return t; }
  map() { const n = this.u32(); const c = new Cur(this.b, this.p, this.p + n); this.take(n); return c; }
  strMap() { const c = this.map(), o = {}; while (c.left()) { const k = c.str(); if (k in o) throw new Error('duplicate map key ' + k); o[k] = c.str(); } return o; }
  u16u64Map() { const c = this.map(), o = []; while (c.left()) o.push([c.u16(), c.u64()]); return o; }
}

function parseRecord(op, c) {
  switch (op) {
    case OP.HEADER: return { profile: c.str(), library: c.str() };
    case OP.FOOTER: return { summaryStart: c.u64(), summaryOffsetStart: c.u64(), summaryCrc: c.u32() };
    case OP.SCHEMA: { const id = c.u16(), name = c.str(), encoding = c.str(), n = c.u32(); return { id, name, encoding, data: Buffer.from(c.take(n)) }; }
    case OP.CHANNEL: return { id: c.u16(), schemaId: c.u16(), topic: c.str(), messageEncoding: c.str(), metadata: c.strMap() };
    case OP.MESSAGE: { const channel = c.u16(), sequence = c.u32(), logTime = c.u64(), publishTime = c.u64(); return { channel, sequence, logTime, publishTime, data: Buffer.from(c.take(c.left())) }; }
    case OP.CHUNK: { const startTime = c.u64(), endTime = c.u64(), uncompressedSize = c.u64(), uncompressedCrc = c.u32(), compression = c.str(), n = c.u64(); return { startTime, endTime, uncompressedSize, uncompressedCrc, compression, records: Buffer.from(c.take(n)) }; }
    case OP.MESSAGE_INDEX: { const channel = c.u16(), n = c.u32(), e = new Cur(c.b, c.p, c.p + n); c.take(n); const entries = []; while (e.left()) entries.push([e.u64(), e.u64()]); return { channel, entries }; }
    case OP.CHUNK_INDEX: return { startTime: c.u64(), endTime: c.u64(), chunkStart: c.u64(), chunkLength: c.u64(), offsets: c.u16u64Map(), indexLength: c.u64(), compression: c.str(), compressedSize: c.u64(), uncompressedSize: c.u64() };
    case OP.ATTACHMENT: { const start = c.p, logTime = c.u64(), createTime = c.u64(), name = c.str(), mediaType = c.str(), n = c.u64(); const data = Buffer.from(c.take(n)); const end = c.p; return { logTime, createTime, name, mediaType, data, crc: c.u32(), crcOk: false, _span: [start, end] }; }
    case OP.ATTACHMENT_INDEX: return { offset: c.u64(), length: c.u64(), logTime: c.u64(), createTime: c.u64(), dataSize: c.u64(), name: c.str(), mediaType: c.str() };
    case OP.STATISTICS: return { messageCount: c.u64(), schemaCount: c.u16(), channelCount: c.u32(), attachmentCount: c.u32(), metadataCount: c.u32(), chunkCount: c.u32(), startTime: c.u64(), endTime: c.u64(), channelMessageCounts: c.u16u64Map() };
    case OP.METADATA: return { name: c.str(), map: c.strMap() };
    case OP.METADATA_INDEX: return { offset: c.u64(), length: c.u64(), name: c.str() };
    case OP.SUMMARY_OFFSET: return { groupOpcode: c.u8(), groupStart: c.u64(), groupLength: c.u64() };
    case OP.DATA_END: return { dataSectionCrc: c.u32() };
    default: return null;
  }
}

/* read records of a section [from, to) -> [{op, at, length, rec}] */
function section(buf, from, to, issues, label) {
  const out = []; const c = new Cur(buf, from, to);
  while (c.left()) {
    const at = c.p;
    try {
      const op = c.u8(), n = c.u64(), body = new Cur(buf, c.p, c.p + n);
      if (c.p + n > to) throw new Error('record runs past its section');
      c.take(n);
      const r = parseRecord(op, body);
      if (r === null) { if (op >= 0x80) { out.push({ op, at, length: c.p - at, rec: null }); continue; } throw new Error('unknown opcode ' + op); }
      if (body.left() && (op === OP.DATA_END || op === OP.FOOTER)) throw new Error('record has trailing bytes');   // only these two are never extended
      out.push({ op, at, length: c.p - at, rec: r });
    } catch (e) { issues.push('malformed-' + label + ': ' + e.message + ' at ' + at); break; }
  }
  return out;
}

export function verifyMcap(buf) {
  const issues = [];
  const bad = (code) => { if (!issues.includes(code)) issues.push(code); };
  const info = { schemas: new Map(), channels: new Map(), messages: [], metadata: [], attachments: [], chunks: [] };
  if (buf.length < 8 + 8 + 9 + 8 + 20 || !buf.subarray(0, 8).equals(MAGIC)) { bad('magic-start'); return { issues, info }; }
  if (!buf.subarray(buf.length - 8).equals(MAGIC)) bad('magic-end');
  // footer is the last record before the trailing magic: 1 + 8 + 20 bytes
  const fAt = buf.length - 8 - 29;
  let footer = null;
  if (buf[fAt] !== OP.FOOTER || buf.readBigUInt64LE(fAt + 1) !== 20n) bad('footer-position');
  else footer = parseRecord(OP.FOOTER, new Cur(buf, fAt + 9, fAt + 29));
  // data section, read sequentially from the first record to Data End
  const all = section(buf, 8, buf.length - 8, issues, 'file');
  if (!all.length || all[0].op !== OP.HEADER) bad('header-first'); else info.header = all[0].rec;
  const deAt = all.findIndex((r) => r.op === OP.DATA_END);
  if (deAt < 0) { bad('data-end-missing'); return { issues, info }; }
  if (all.filter((r) => r.op === OP.DATA_END).length !== 1) bad('data-end-twice');
  if (all[all.length - 1].op !== OP.FOOTER) bad('footer-last');
  const data = all.slice(1, deAt), summary = all.slice(deAt + 1, -1);
  const dataEnd = all[deAt];
  if (dataEnd.rec.dataSectionCrc !== 0 && dataEnd.rec.dataSectionCrc !== crc32(buf.subarray(0, dataEnd.at))) bad('data-end-crc');
  for (const r of data) if (![OP.SCHEMA, OP.CHANNEL, OP.MESSAGE, OP.ATTACHMENT, OP.CHUNK, OP.MESSAGE_INDEX, OP.METADATA].includes(r.op) && r.op < 0x80) bad('data-section-record-not-allowed');
  for (const r of summary) if (![OP.SCHEMA, OP.CHANNEL, OP.CHUNK_INDEX, OP.ATTACHMENT_INDEX, OP.METADATA_INDEX, OP.STATISTICS, OP.SUMMARY_OFFSET].includes(r.op) && r.op < 0x80) bad('summary-record-not-allowed');

  // expand chunks (records inside), check CRCs and the message indexes that follow each chunk
  const dataSchemas = [], dataChannels = [];
  let prevChunk = null;
  const takeSchemaChannel = (r) => {
    if (r.op === OP.SCHEMA) { if (r.rec.id === 0) bad('schema-id-zero'); const o = info.schemas.get(r.rec.id); if (o && (o.name !== r.rec.name || o.encoding !== r.rec.encoding || !o.data.equals(r.rec.data))) bad('schema-id-conflict'); info.schemas.set(r.rec.id, r.rec); dataSchemas.push(r.rec); }
    if (r.op === OP.CHANNEL) { const o = info.channels.get(r.rec.id); if (o && JSON.stringify(o) !== JSON.stringify(r.rec)) bad('channel-id-conflict'); if (r.rec.schemaId !== 0 && !info.schemas.has(r.rec.schemaId)) bad('channel-before-schema'); info.channels.set(r.rec.id, r.rec); dataChannels.push(r.rec); }
  };
  const take = (m) => { if (!info.channels.has(m.channel)) bad('message-before-channel'); info.messages.push(m); };
  for (const r of data) {
    if (r.op === OP.SCHEMA || r.op === OP.CHANNEL) takeSchemaChannel(r);
    else if (r.op === OP.MESSAGE) take(r.rec);
    else if (r.op === OP.METADATA) info.metadata.push({ ...r.rec, at: r.at, length: r.length });
    else if (r.op === OP.ATTACHMENT) { const a = r.rec; a.crcOk = a.crc === 0 || a.crc === crc32(buf.subarray(a._span[0], a._span[1])); if (!a.crcOk) bad('attachment-crc'); info.attachments.push({ ...a, at: r.at, length: r.length }); }
    else if (r.op === OP.CHUNK) {
      const ch = r.rec; let body = ch.records;
      try { if (ch.compression === 'zstd') body = zlib.zstdDecompressSync(body); else if (ch.compression === 'lz4') throw new Error('lz4 is not supported by this verifier'); else if (ch.compression !== '') throw new Error('unknown compression ' + ch.compression); }
      catch (e) { bad('chunk-decompress'); continue; }
      if (body.length !== ch.uncompressedSize) bad('chunk-size');
      if (ch.uncompressedCrc !== 0 && ch.uncompressedCrc !== crc32(body)) bad('chunk-crc');
      const inner = section(body, 0, body.length, issues, 'chunk');
      const rows = []; let lo = null, hi = null;
      for (const q of inner) {
        if (q.op === OP.SCHEMA || q.op === OP.CHANNEL) takeSchemaChannel(q);
        else if (q.op === OP.MESSAGE) { take(q.rec); rows.push({ channel: q.rec.channel, logTime: q.rec.logTime, offset: q.at }); lo = lo === null ? q.rec.logTime : Math.min(lo, q.rec.logTime); hi = hi === null ? q.rec.logTime : Math.max(hi, q.rec.logTime); }
        else bad('chunk-record-not-allowed');
      }
      if ((lo ?? 0) !== ch.startTime || (hi ?? 0) !== ch.endTime) bad('chunk-time-range');
      prevChunk = { at: r.at, length: r.length, rec: ch, rows, indexes: [], uncompressed: body.length, compressed: ch.records.length };
      info.chunks.push(prevChunk);
    } else if (r.op === OP.MESSAGE_INDEX) {
      if (!prevChunk) { bad('message-index-without-chunk'); continue; }
      prevChunk.indexes.push({ at: r.at, length: r.length, rec: r.rec });
    }
  }
  // each chunk is followed by exactly one Message Index per channel that has messages in it, offsets pointing at those messages
  for (const c of info.chunks) {
    const chans = [...new Set(c.rows.map((x) => x.channel))].sort((a, b) => a - b);
    if (JSON.stringify(c.indexes.map((x) => x.rec.channel)) !== JSON.stringify(chans)) bad('message-index-channels');
    for (const ix of c.indexes) {
      const want = c.rows.filter((x) => x.channel === ix.rec.channel).map((x) => [x.logTime, x.offset]);
      if (JSON.stringify(ix.rec.entries) !== JSON.stringify(want)) bad('message-index-entries');
    }
  }

  // summary: grouped by opcode, summary offsets point at the groups, Schema/Channel copies equal the data section's
  const sum = { schemas: [], channels: [], stats: null, chunkIndexes: [], attachmentIndexes: [], metadataIndexes: [], offsets: [] };
  const seen = [];
  for (const r of summary) {
    if (seen[seen.length - 1] !== r.op) { if (seen.includes(r.op)) bad('summary-not-grouped'); seen.push(r.op); }
    if (r.op === OP.SCHEMA) sum.schemas.push(r.rec); else if (r.op === OP.CHANNEL) sum.channels.push(r.rec); else if (r.op === OP.STATISTICS) { if (sum.stats) bad('statistics-twice'); sum.stats = r.rec; }
    else if (r.op === OP.CHUNK_INDEX) sum.chunkIndexes.push({ ...r.rec, at: r.at }); else if (r.op === OP.ATTACHMENT_INDEX) sum.attachmentIndexes.push(r.rec); else if (r.op === OP.METADATA_INDEX) sum.metadataIndexes.push(r.rec);
    else if (r.op === OP.SUMMARY_OFFSET) sum.offsets.push({ ...r.rec, at: r.at });
  }
  info.summary = sum;
  const so = sum.offsets.length ? sum.offsets[0].at : (footer ? fAt : 0);
  const firstSummary = summary.find((r) => r.op !== OP.SUMMARY_OFFSET);
  if (footer) {
    const expectStart = firstSummary ? firstSummary.at : 0;
    if (footer.summaryStart !== expectStart) bad('footer-summary-start');
    if (footer.summaryOffsetStart !== (sum.offsets.length ? so : 0)) bad('footer-summary-offset-start');
    if (footer.summaryCrc !== 0) {
      const from = footer.summaryStart || fAt;
      if (footer.summaryCrc !== crc32(buf.subarray(from, fAt + 25))) bad('summary-crc');
    }
  }
  if (JSON.stringify(sum.schemas.map((s) => [s.id, s.name, s.encoding, s.data.toString('base64')])) !== JSON.stringify(dataSchemas.map((s) => [s.id, s.name, s.encoding, s.data.toString('base64')]))) bad('summary-schemas');
  if (JSON.stringify(sum.channels) !== JSON.stringify(dataChannels)) bad('summary-channels');
  for (const g of sum.offsets) {
    const members = summary.filter((r) => r.op === g.groupOpcode);
    if (!members.length || members[0].at !== g.groupStart || members.reduce((a, r) => a + r.length, 0) !== g.groupLength) bad('summary-offset');
  }
  if (new Set(sum.offsets.map((g) => g.groupOpcode)).size !== new Set(summary.filter((r) => r.op !== OP.SUMMARY_OFFSET).map((r) => r.op)).size) bad('summary-offset-groups');
  // statistics
  const st = sum.stats;
  if (!st) bad('statistics-missing');
  else {
    const counts = new Map(); for (const m of info.messages) counts.set(m.channel, (counts.get(m.channel) || 0) + 1);
    if (st.messageCount !== info.messages.length) bad('statistics-message-count');
    if (st.schemaCount !== info.schemas.size || st.channelCount !== info.channels.size) bad('statistics-schema-channel-count');
    if (st.attachmentCount !== info.attachments.length || st.metadataCount !== info.metadata.length || st.chunkCount !== info.chunks.length) bad('statistics-other-counts');
    if (JSON.stringify(st.channelMessageCounts) !== JSON.stringify([...counts.entries()].sort((a, b) => a[0] - b[0]))) bad('statistics-channel-counts');
    const times = info.messages.map((m) => m.logTime);
    if (st.startTime !== (times.length ? Math.min(...times) : 0) || st.endTime !== (times.length ? Math.max(...times) : 0)) bad('statistics-time-range');
  }
  // chunk indexes
  if (sum.chunkIndexes.length !== info.chunks.length) bad('chunk-index-count');
  sum.chunkIndexes.forEach((ci, i) => {
    const c = info.chunks[i]; if (!c) return;
    if (ci.chunkStart !== c.at || ci.chunkLength !== c.length || ci.startTime !== c.rec.startTime || ci.endTime !== c.rec.endTime || ci.compression !== c.rec.compression || ci.compressedSize !== c.compressed || ci.uncompressedSize !== c.uncompressed) bad('chunk-index-fields');
    const want = c.indexes.map((x) => [x.rec.channel, x.at]);
    if (JSON.stringify(ci.offsets) !== JSON.stringify(want)) bad('chunk-index-offsets');
    if (ci.indexLength !== c.indexes.reduce((a, x) => a + x.length, 0)) bad('chunk-index-length');
  });
  if (JSON.stringify(sum.attachmentIndexes.map((a) => [a.offset, a.length, a.logTime, a.createTime, a.dataSize, a.name, a.mediaType])) !== JSON.stringify(info.attachments.map((a) => [a.at, a.length, a.logTime, a.createTime, a.data.length, a.name, a.mediaType]))) bad('attachment-index');
  if (JSON.stringify(sum.metadataIndexes.map((m) => [m.offset, m.length, m.name])) !== JSON.stringify(info.metadata.map((m) => [m.at, m.length, m.name]))) bad('metadata-index');
  return { issues, info };
}
