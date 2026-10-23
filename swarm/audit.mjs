/* swarm/audit.mjs - the audit log format for every routed command (swarm-audit/1). One row per command, refused ones
 * included, chained by SHA-256: hash = sha256(prev + '\n' + canonical(row without hash)). There is no clock field: a row
 * is a function of the command, the registries and the router's own source, so the same command gives the same row.
 * The log is held in memory; the caller decides where to write toJSONL(). Nothing here reads the network or a device. */
import { createHash } from 'node:crypto';

export const SCHEMA = 'swarm-audit/1';
export const GENESIS = '0'.repeat(64);
export const sha256 = (s) => createHash('sha256').update(String(s)).digest('hex');

/* stable JSON: keys sorted, no undefined, no non-finite numbers, plain data only */
export function canonical(v, depth = 0) {
  if (depth > 40) throw new Error('canonical: too deep');
  if (v === null || typeof v === 'string' || typeof v === 'boolean') return JSON.stringify(v);
  if (typeof v === 'number') { if (!Number.isFinite(v)) throw new Error('canonical: non-finite number'); return JSON.stringify(Object.is(v, -0) ? 0 : v); }
  if (Array.isArray(v)) return '[' + v.map((x) => canonical(x, depth + 1)).join(',') + ']';
  if (typeof v === 'object' && Object.getPrototypeOf(v) === Object.prototype)
    return '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canonical(v[k], depth + 1)).join(',') + '}';
  throw new Error('canonical: not plain data');
}

const REQUIRED = ['command', 'status', 'refusal', 'resolved', 'gate', 'results', 'provenance'];

export class SwarmAudit {
  constructor() { this._rows = []; }
  get length() { return this._rows.length; }
  get head() { return this._rows.length ? this._rows[this._rows.length - 1].hash : GENESIS; }
  append(body) {
    for (const k of REQUIRED) if (!(k in body)) throw new Error('audit: missing ' + k);
    const row = { schema: SCHEMA, seq: this._rows.length, prev: this.head, ...JSON.parse(canonical(body)) };
    row.hash = sha256(row.prev + '\n' + canonical(row));
    const frozen = deepFreeze(row);
    this._rows.push(frozen);
    return frozen;
  }
  rows() { return this._rows.slice(); }
  /* walk the chain from genesis; optionally against a head published somewhere else */
  verify(expectHead) {
    let prev = GENESIS;
    for (let i = 0; i < this._rows.length; i++) {
      const r = this._rows[i], { hash, ...rest } = r;
      if (r.schema !== SCHEMA) return { ok: false, at: i, why: 'schema' };
      if (r.seq !== i) return { ok: false, at: i, why: 'seq' };
      if (r.prev !== prev) return { ok: false, at: i, why: 'prev' };
      if (hash !== sha256(prev + '\n' + canonical(rest))) return { ok: false, at: i, why: 'hash' };
      prev = hash;
    }
    if (expectHead !== undefined && expectHead !== prev) return { ok: false, at: this._rows.length, why: 'head' };
    return { ok: true, at: this._rows.length, head: prev };
  }
  toJSONL() { return this._rows.map((r) => canonical(r)).join('\n') + (this._rows.length ? '\n' : ''); }
}

/* verify rows that were written out and read back */
export function verifyRows(rows) {
  const a = new SwarmAudit();
  a._rows = rows;
  return a.verify();
}

function deepFreeze(o) {
  if (o && typeof o === 'object' && !Object.isFrozen(o)) { Object.freeze(o); for (const k of Object.keys(o)) deepFreeze(o[k]); }
  return o;
}
