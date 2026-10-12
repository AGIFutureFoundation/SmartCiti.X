/**
 * Safety Gate: may this learner enter this hazardous training station or
 * simulator seat right now?
 *
 * A TRAINING-SIM gate for SmartCiti.X : Trade Craft Academy, powered by AGI Corp;
 * It is not a real-world safety system and makes no claim against any
 * standard (see safety_gate/README.md).
 *
 * Built on what the repo already holds rather than beside it:
 *   - stations/registry/stations.json   stations, their strand, tier, room, room_ppe, room_hazards
 *   - sims/registry/sims.json           seats, their halls, rubric (zero-tolerance axes), walkaround
 *   - surfaces/registry/finishes.json   per-hall, per-room conditions (ppe, hazards) and hazard_conditions
 *   - unions/registry/unions.json       hall -> district
 *   - bus/audit.mjs AuditLog            the one append-only log; this module adds a hash chain over its own rows
 *   - bus/bus.mjs                       override.applied is published as `instructor_ui`, its single writer
 *   - security/authz.mjs ROLES/AGENT_ROLES  who is an instructor and who is a voiced agent
 *
 * Nothing about hazards is hand-listed: a target is hazardous because its own
 * registry records say so (room hazards, PPE its room conditions demand, a
 * permit class named by its own text, a zero-tolerance rubric axis).
 *
 * canEnter() is pure: it reads the learner record, the target and the context
 * (including the ledger) and returns a decision. It never writes. enter() is the
 * side-effecting wrapper that records the decision and consumes a used override.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { AuditLog } from '../bus/audit.mjs';
import { ROLES, AGENT_ROLES, principal as authzPrincipal } from '../security/authz.mjs';

export const GATE = Object.freeze({
  maxOverrideMinutes: 60,          // an override is a bridge for one session, not a standing pass
  maxPermitMinutes: 8 * 60,        // one shift
  maxContextAgeMs: 5 * 60 * 1000,  // a learner record / door check older than this is stale
  clockSkewMs: 30 * 1000,
  minReasonChars: 12,              // "ok" is not a reason
});

export const TIERS = Object.freeze(['fundamentals', 'applied', 'mastery']);
export const PREFIX = 'safety_gate.';
const GENESIS = '0'.repeat(64);

/**
 * Permit classes. Each is detected from a target's own words, or from a room
 * hazard the surfaces record already carries, and maps to the surfaces
 * hazard_conditions entry whose PPE the permitted work adds.
 */
export const PERMIT_CLASSES = Object.freeze({
  'hot-work': {
    text: /\bhot[- ]work\b(?!\s+cleared)|\bweld(?:s|er|ers|ing)?\b|\barc\b|\btorch(?:es)?\b|\bbraz(?:e|ing)\b/gi,
    roomHazards: ['hot-work'], ppeFrom: 'hot-work' },
  'confined-space': {
    text: /\bconfined[- ]spaces?\b|\btrench(?:es|ing)?\b|\bmanholes?\b|\bvessel entry\b/gi,
    roomHazards: ['confined-space'], ppeFrom: 'confined-space' },
  'lock-out': {
    text: /\block(?:ed)?[- ]?out\b|\btag(?:ged)?[- ]?out\b|\bzero[- ]energy\b/gi,
    roomHazards: ['stored-energy', 'live-electrical'], ppeFrom: 'stored-energy' },
  'work-at-height': {
    text: /\bwork[- ]at[- ]height\b|\bfall (?:protection|arrest)\b|\bharness(?:es)?\b|\bscaffold(?:s|ing)?\b|\bbasket\b/gi,
    roomHazards: ['work-at-height'], ppeFrom: 'work-at-height' },
});

const STATION_ID = /^st\d{3}$/;
const SIM_ID = /^sim:[a-z0-9]+(?:-[a-z0-9]+)*@[a-z0-9]+(?:-[a-z0-9]+)*$/;
const LEARNER_ID = /^[a-z0-9][a-z0-9_-]{0,63}$/;

/* ------------------------------------------------------------ helpers --- */
export function canonical(v) {
  if (v === null || typeof v !== 'object') return JSON.stringify(v ?? null);
  if (Array.isArray(v)) return `[${v.map(canonical).join(',')}]`;
  return `{${Object.keys(v).sort().map((k) => `${JSON.stringify(k)}:${canonical(v[k])}`).join(',')}}`;
}
const sha = (s) => createHash('sha256').update(s).digest('hex');
const deepFreeze = (o) => {
  if (o && typeof o === 'object' && !Object.isFrozen(o)) {
    Object.freeze(o);
    for (const k of Object.keys(o)) deepFreeze(o[k]);
  }
  return o;
};
const isStr = (s) => typeof s === 'string';
/** An actor id for the audit row, read defensively: a refused actor may be hostile. */
const actorIdOf = (a) => {
  try { const id = a?.id; return isStr(id) ? id : 'anonymous'; } catch { return 'anonymous'; }
};
const fin = (n) => typeof n === 'number' && Number.isFinite(n);

/* ---------------------------------------------------- hazard derivation --- */
function permitsFromText(text) {
  const out = new Map();
  for (const [cls, def] of Object.entries(PERMIT_CLASSES)) {
    const hits = [...new Set((text.match(def.text) ?? []).map((m) => m.toLowerCase()))].sort();
    if (hits.length) out.set(cls, hits);
  }
  return out;
}

function classify(rec, finishes) {
  const { roomPpe, roomHazards, text, zeroAxes = [] } = rec;
  const reasons = [];
  const baseItems = new Set(Object.values(finishes.base_conditions).flatMap((c) => c.ppe));
  const hazardOnly = new Set(Object.values(finishes.hazard_conditions).flatMap((c) => c.ppe)
    .filter((p) => !baseItems.has(p)));

  for (const h of roomHazards) reasons.push(`room-hazard:${h}`);
  for (const p of roomPpe) if (hazardOnly.has(p)) reasons.push(`hazard-ppe:${p}`);
  if (roomPpe.includes('hard hat')) reasons.push('working-floor:hard hat required by room conditions');
  for (const a of zeroAxes) reasons.push(`zero-tolerance-axis:${a}`);

  // Permit classes: from a room hazard the surfaces record carries, or from the
  // target's own words - but text only counts on a working floor (its room
  // conditions demand a hard hat). A briefing room that prices a scaffold, or
  // an inspection bench that reads about one, is not work at height.
  const permits = new Map();
  for (const [cls, def] of Object.entries(PERMIT_CLASSES)) {
    const viaRoom = roomHazards.filter((h) => def.roomHazards.includes(h));
    if (viaRoom.length) permits.set(cls, viaRoom.map((h) => `room:${h}`));
  }
  if (roomPpe.includes('hard hat')) {
    for (const [cls, hits] of permitsFromText(text)) {
      permits.set(cls, [...(permits.get(cls) ?? []), ...hits.map((h) => `text:${h}`)]);
    }
  }
  for (const [cls, why] of permits) reasons.push(`permit:${cls} (${why.join(', ')})`);

  const ppe = new Set(roomPpe);
  for (const cls of permits.keys()) {
    for (const p of finishes.hazard_conditions[PERMIT_CLASSES[cls].ppeFrom]?.ppe ?? []) ppe.add(p);
  }
  return { hazardous: reasons.length > 0, reasons, permits: [...permits.keys()].sort(),
           permitEvidence: Object.fromEntries(permits), ppe: [...ppe].sort() };
}

function safetySkills(hall, tier, strand) {
  const t = TIERS.indexOf(tier);
  if (t < 0) throw new Error(`unknown tier "${tier}"`);
  // A safety-strand target teaches its own tier, so it may require only the
  // tiers below it - otherwise the induction room would be locked behind itself.
  const upto = strand === 'safety' ? t - 1 : Math.min(t, 1);
  return TIERS.slice(0, Math.max(upto + 1, 0)).map((x) => `${hall}.safety.${x}`);
}

/** Build the target index from the registries. Pure over its inputs. */
export function buildIndex({ stations, sims, finishes, unions }) {
  const halls = finishes.halls;
  const districtOf = new Map(unions.unions.map((u) => [u.slug, u.district]));
  const targets = new Map();
  const disagreements = [];

  for (const s of stations.stations) {
    const cond = halls[s.hall]?.conditions?.[s.strand];
    if (!cond) throw new Error(`${s.station_id}: no surfaces conditions for ${s.hall}/${s.strand}`);
    if (canonical(cond.ppe) !== canonical(s.room_ppe) || canonical(cond.hazards) !== canonical(s.room_hazards)) {
      disagreements.push(s.station_id);
    }
    const text = [s.name, ...(s.checklist ?? []), s.quiz?.question ?? ''].join('\n');
    const c = classify({ roomPpe: cond.ppe, roomHazards: cond.hazards, text }, finishes);
    targets.set(s.station_id, deepFreeze({
      id: s.station_id, kind: 'station', name: s.name, hall: s.hall,
      district: districtOf.get(s.hall) ?? s.district, strand: s.strand, tier: s.tier, room: s.room,
      ...c, safetySkills: c.hazardous ? safetySkills(s.hall, s.tier, s.strand) : [],
    }));
  }

  for (const [simId, sim] of Object.entries(sims.sims)) {
    const zeroAxes = sim.rubric.filter((r) => r.pass === '== 0').map((r) => r.axis);
    // the seat's own words: its task and what its walkaround checks (not the
    // on_fault advice, which describes what a crew does when a check fails)
    const text = [sim.name, sim.task, ...(sim.walkaround ?? []).flatMap((w) => [w.point, w.check])].join('\n');
    for (const hall of sim.halls) {
      const cond = halls[hall]?.conditions?.[sim.skill_strand];
      if (!cond) throw new Error(`sim ${simId}@${hall}: no surfaces conditions for ${hall}/${sim.skill_strand}`);
      const c = classify({ roomPpe: cond.ppe, roomHazards: cond.hazards, text, zeroAxes }, finishes);
      const id = `sim:${simId}@${hall}`;
      targets.set(id, deepFreeze({
        id, kind: 'sim', sim: simId, name: sim.name, hall, district: districtOf.get(hall) ?? null,
        strand: sim.skill_strand, tier: sim.skill_tier, room: sim.skill_strand,
        ...c, safetySkills: c.hazardous ? safetySkills(hall, sim.skill_tier, sim.skill_strand) : [],
      }));
    }
  }
  return deepFreeze({ targets, disagreements, stamps: {
    stations: stations.source_stamp, sims: sims.source_stamp, surfaces: finishes.source_stamp } });
}

const ROOT = fileURLToPath(new URL('..', import.meta.url));
export function loadIndex(root = ROOT) {
  const rd = (p) => JSON.parse(readFileSync(join(root, p), 'utf8'));
  return buildIndex({
    stations: rd('stations/registry/stations.json'), sims: rd('sims/registry/sims.json'),
    finishes: rd('surfaces/registry/finishes.json'), unions: rd('unions/registry/unions.json'),
  });
}

/* -------------------------------------------------------------- ledger --- */
/**
 * The gate's rows go on bus/audit.mjs's AuditLog - the same log every other
 * safeguard writes - and this ledger keeps a SHA-256 chain over the gate's
 * own rows. The AuditLog hands out frozen entries; the chain is what lets a
 * reader prove nobody swapped, dropped or slipped in a row afterwards.
 */
export class SafetyLedger {
  #chain = [];
  #issuer = null;
  constructor({ audit = null, clock = () => Date.now(), bus = null, issuer = null } = {}) {
    // The issuer is fixed at construction and never exposed: a caller holding
    // the ledger can ask whether a principal is vouched for, never mint one.
    if (issuer !== null && !ISSUERS.has(issuer)) throw new Error('issuer must come from createIssuer()');
    this.#issuer = issuer;
    this.clock = clock;
    this.audit = audit ?? new AuditLog({ clock, limit: Number.MAX_SAFE_INTEGER });
    this.publish = bus ? bus.publisherFor('instructor_ui') : null;
  }

  static body(e) {
    return { seq: e.seq, ts: e.ts, actor: e.actor, action: e.action, why: e.why,
             learner: e.learner, skill: e.skill, before: e.before, after: e.after };
  }

  append(action, { actor, why = '', learner = null, skill = null, after = null }) {
    if (!action.startsWith(PREFIX)) throw new Error(`ledger rows are ${PREFIX}*`);
    const e = this.audit.append({ actor, action, why, learner, skill, after: deepFreeze(after) });
    const prev = this.#chain.length ? this.#chain[this.#chain.length - 1].hash : GENESIS;
    const hash = sha(`${prev}\n${canonical(SafetyLedger.body(e))}`);
    this.#chain.push(Object.freeze({ seq: e.seq, hash }));
    return { entry: e, hash };
  }

  /** Did this ledger's issuer mint exactly this object (identity, not shape)? */
  vouches(p) { return this.#issuer !== null && vouchedBy(this.#issuer, p); }

  head() { return this.#chain.length ? this.#chain[this.#chain.length - 1].hash : GENESIS; }
  hashAt(seq) { return this.#chain.find((c) => c.seq === seq)?.hash ?? null; }

  /** Recompute the chain against the log. Read-only. */
  verify({ expectHead = null } = {}) {
    if (this.audit.truncated) return { ok: false, why: 'audit log truncated' };
    const entries = this.audit.entries();
    const bySeq = new Map();
    for (const e of entries) {
      if (bySeq.has(e.seq)) return { ok: false, why: `duplicate seq ${e.seq}` };
      bySeq.set(e.seq, e);
    }
    let prev = GENESIS;
    const chained = new Set();
    for (const c of this.#chain) {
      const e = bySeq.get(c.seq);
      if (!e) return { ok: false, why: `chained row ${c.seq} missing from the log` };
      const h = sha(`${prev}\n${canonical(SafetyLedger.body(e))}`);
      if (h !== c.hash) return { ok: false, why: `row ${c.seq} altered after it was chained` };
      prev = h; chained.add(c.seq);
    }
    for (const e of entries) {
      if (isStr(e.action) && e.action.startsWith(PREFIX) && !chained.has(e.seq)) {
        return { ok: false, why: `row ${e.seq} (${e.action}) is on the log but was never chained` };
      }
    }
    if (expectHead && expectHead !== prev) return { ok: false, why: 'head differs from the published head' };
    return { ok: true, rows: chained.size, head: prev };
  }

  /** Is this token exactly a row this ledger chained under `action`? Read-only. */
  holds(token, action) {
    if (!token || typeof token !== 'object' || !Number.isInteger(token.seq) || !isStr(token.hash)) return false;
    if (this.hashAt(token.seq) !== token.hash) return false;
    const e = this.audit.entries().find((x) => x.seq === token.seq);
    if (!e || e.action !== action) return false;
    const { seq, hash, ...fields } = token;
    return canonical(fields) === canonical(e.after);
  }

  rows(action) { return this.audit.entries({ action }); }
}

/* ------------------------------------------------------- provenance --- */
/**
 * Who may override or issue a permit is a question of WHERE a principal came
 * from, not what it looks like. createIssuer() returns a capability; its
 * mint() is the only way to obtain a principal this gate will accept for an
 * override or a permit. Provenance is held here, module-private, keyed by the
 * exact frozen object minted - so a hand-built object, an authz.principal()
 * built directly, a structural or spread copy, a thawed copy, or a principal
 * from a different issuer is never vouched for, whatever roles/caps it carries.
 *
 * This is a training-sim trust boundary inside one process, not
 * authentication: whoever holds an issuer can mint any principal, and code
 * that controls the process can replace the gate. The issuer belongs to the
 * code that has already authenticated the instructor (the console's login).
 */
const MINTED = new WeakMap();   // principal object -> the issuer that minted it
const ISSUERS = new WeakSet();  // issuers created by createIssuer()

const deeplyFrozen = (p) => Object.isFrozen(p)
  && ['roles', 'caps', 'assigned'].every((k) => Array.isArray(p[k]) && Object.isFrozen(p[k]));

function vouchedBy(issuer, p) {
  return !!p && typeof p === 'object' && MINTED.get(p) === issuer && deeplyFrozen(p);
}

export function createIssuer({ name = 'issuer' } = {}) {
  const issuer = Object.freeze({
    name: String(name),
    /** Mint a principal through security/authz.mjs and record its provenance. */
    mint(spec) {
      const p = authzPrincipal(spec);
      if (!deeplyFrozen(p)) throw new Error('authz.principal() returned a mutable principal');
      MINTED.set(p, issuer);
      return p;
    },
    vouches: (p) => vouchedBy(issuer, p),
  });
  ISSUERS.add(issuer);
  return issuer;
}

/* ------------------------------------------------- who may issue / override */
function isInstructor(p) {
  return !!p && Array.isArray(p.roles) && p.roles.includes('instructor')
    && !p.roles.some((r) => AGENT_ROLES.includes(r))
    && Array.isArray(p.caps) && ROLES.instructor.every((c) => p.caps.includes(c));
}

function issuerProblem(ledger, actor, learnerId, learnerTenant) {
  if (!actor || typeof actor !== 'object') return 'no principal';
  if (!ledger.vouches(actor)) {
    return 'principal not minted by this gate\'s issuer (provenance, not shape, confers authority)';
  }
  if (!isStr(actor.id)) return 'no principal';
  if (actor.roles?.some((r) => AGENT_ROLES.includes(r))) return 'a voiced agent may not authorise entry';
  if (actor.id === learnerId) return 'a learner may not authorise their own entry';
  if (!isInstructor(actor)) return 'only an instructor may authorise this';
  if (actor.tenant !== learnerTenant) return 'cross-tenant';
  if (!actor.assigned?.includes(learnerId)) return 'learner not assigned to this instructor';
  return null;
}

/**
 * Instructor override. Time-boxed, reasoned, appended to the log (refusals
 * too), published on the bus as instructor_ui. Returns the token canEnter
 * will check against the log.
 */
export function grantOverride(ledger, index, { actor, learner, learnerTenant, target, reason, minutes }) {
  const now = ledger.clock();
  const refuse = (why) => {
    ledger.append(`${PREFIX}override.refused`, { actor: actorIdOf(actor), why,
      learner: isStr(learner) ? learner : null, skill: isStr(target) ? target : null,
      after: { target: isStr(target) ? target : null, minutes: fin(minutes) ? minutes : null } });
    return { ok: false, why };
  };
  const p = issuerProblem(ledger, actor, learner, learnerTenant);
  if (p) return refuse(p);
  if (!isStr(target) || !index.targets.has(target)) return refuse('unknown target');
  if (!isStr(reason) || reason.trim().length < GATE.minReasonChars) {
    return refuse(`an override needs a reason of at least ${GATE.minReasonChars} characters`);
  }
  if (!fin(minutes) || minutes <= 0 || minutes > GATE.maxOverrideMinutes) {
    return refuse(`an override is time-boxed to 1..${GATE.maxOverrideMinutes} minutes`);
  }
  const record = {
    override_id: `ovr-${ledger.rows(`${PREFIX}override.granted`).length + 1}-${sha(canonical([actor.id, learner, target, now])).slice(0, 8)}`,
    learner, target, actor: actor.id, actor_roles: [...actor.roles].sort(), reason: reason.trim(),
    issued_at: now, expires_at: now + minutes * 60000,
  };
  const { entry, hash } = ledger.append(`${PREFIX}override.granted`, {
    actor: actor.id, why: record.reason, learner, skill: target, after: record });
  ledger.publish?.('override.applied', { kind: 'safety_gate.override', ...record, head: ledger.head() });
  return { ok: true, override: Object.freeze({ ...record, seq: entry.seq, hash }) };
}

/** A permit for permit-class work on one target, for one learner, for one shift. */
export function issuePermit(ledger, index, { actor, learner, learnerTenant, target, cls, minutes = 240 }) {
  const now = ledger.clock();
  const refuse = (why) => {
    ledger.append(`${PREFIX}permit.refused`, { actor: actorIdOf(actor), why,
      learner: isStr(learner) ? learner : null, skill: isStr(target) ? target : null, after: { cls: isStr(cls) ? cls : null } });
    return { ok: false, why };
  };
  const p = issuerProblem(ledger, actor, learner, learnerTenant);
  if (p) return refuse(p);
  const t = isStr(target) ? index.targets.get(target) : null;
  if (!t) return refuse('unknown target');
  if (!t.permits.includes(cls)) return refuse(`${target} is not ${cls} work`);
  if (!fin(minutes) || minutes <= 0 || minutes > GATE.maxPermitMinutes) return refuse('permit outside one shift');
  const record = { permit_id: `pmt-${ledger.rows(`${PREFIX}permit.issued`).length + 1}`, cls, learner, target,
                   actor: actor.id, issued_at: now, expires_at: now + minutes * 60000 };
  const { entry, hash } = ledger.append(`${PREFIX}permit.issued`, {
    actor: actor.id, why: `${cls} permit`, learner, skill: target, after: record });
  return { ok: true, permit: Object.freeze({ ...record, seq: entry.seq, hash }) };
}

/* ------------------------------------------------------------ decision --- */
/**
 * @returns {{allow:boolean, reasons:string[], required:string[], via?:string, target?:string}}
 * Pure: no writes. Reason strings start with a code: stale-context, unknown-target,
 * invalid-learner, not-hazardous, induction, ppe, permit, tier, override, allow.
 */
export function canEnter(learner, station, context) {
  const reasons = [];
  const out = (allow, required = [], extra = {}) => Object.freeze({
    allow, reasons: Object.freeze([...reasons]), required: Object.freeze([...required]), ...extra });

  // 1. context must be present and fresh
  const c = context;
  if (!c || typeof c !== 'object' || !c.index?.targets) { reasons.push('stale-context: no context or index'); return out(false); }
  if (!fin(c.now) || !fin(c.asOf)) { reasons.push('stale-context: now/asOf missing'); return out(false); }
  if (c.asOf > c.now + GATE.clockSkewMs) { reasons.push('stale-context: record dated in the future'); return out(false); }
  if (c.now - c.asOf > GATE.maxContextAgeMs) { reasons.push(`stale-context: record is ${Math.round((c.now - c.asOf) / 1000)}s old`); return out(false); }

  // 2. the target must be a canonical id the registries know - no normalising
  const id = typeof station === 'object' && station !== null ? station.id : station;
  if (!isStr(id) || !(STATION_ID.test(id) || SIM_ID.test(id)) || !c.index.targets.has(id)) {
    reasons.push(`unknown-target: ${JSON.stringify(id ?? null)} is not a canonical registry id`);
    return out(false);
  }
  const t = c.index.targets.get(id);

  // 3. the learner record
  if (!learner || typeof learner !== 'object' || !isStr(learner.id) || !LEARNER_ID.test(learner.id) || !isStr(learner.tenant)) {
    reasons.push('invalid-learner: no canonical learner record');
    return out(false, [], { target: id });
  }

  if (!t.hazardous) {
    reasons.push(`not-hazardous: ${id} (${t.name}) - its room conditions name no hazard, permit or working-floor PPE`);
    return out(true, [], { target: id, via: 'open' });
  }

  const required = [
    `induction:hall:${t.hall}|district:${t.district}`,
    ...t.ppe.map((p) => `ppe:${p}`),
    ...t.permits.map((p) => `permit:${p}`),
    ...t.safetySkills.map((s) => `tier:${s}`),
  ];
  const unmet = [];
  const ledgerOk = c.ledger ? c.ledger.verify() : { ok: false, why: 'no ledger' };

  // (a) induction for this hall or its district, completed and in date
  const scopes = new Set([`hall:${t.hall}`, t.district ? `district:${t.district}` : null].filter(Boolean));
  const inducted = (Array.isArray(learner.inductions) ? learner.inductions : []).some((i) =>
    i && scopes.has(i.scope) && fin(i.completed_at) && i.completed_at <= c.now
      && fin(i.expires_at) && i.expires_at > c.now);
  if (!inducted) unmet.push(`induction: no in-date site induction for hall:${t.hall} or district:${t.district}`);

  // (b) PPE checked at this door, for this learner, recently, exactly as the room states it
  const pc = c.ppeCheck;
  let ppeMissing = t.ppe;
  if (!pc || pc.learner !== learner.id || pc.target !== id || !fin(pc.at) || pc.at > c.now + GATE.clockSkewMs
      || c.now - pc.at > GATE.maxContextAgeMs || !Array.isArray(pc.items)) {
    if (t.ppe.length) reasons.push('ppe: no current door check for this learner at this target');
  } else {
    const have = new Set(pc.items.filter(isStr));
    ppeMissing = t.ppe.filter((p) => !have.has(p));
  }
  if (ppeMissing.length) reasons.push(`ppe: missing ${ppeMissing.join(', ')}`);

  // (c) permits for permit-class work, on the chained log, for this learner and target, in date
  for (const cls of t.permits) {
    const ok = ledgerOk.ok && (Array.isArray(c.permits) ? c.permits : []).some((pm) =>
      pm && pm.cls === cls && pm.learner === learner.id && pm.target === id
        && fin(pm.issued_at) && pm.issued_at <= c.now && fin(pm.expires_at) && pm.expires_at > c.now
        && c.ledger.holds(pm, `${PREFIX}permit.issued`));
    if (!ok) unmet.push(`permit: no valid ${cls} permit for ${learner.id} at ${id}${ledgerOk.ok ? '' : ` (ledger: ${ledgerOk.why})`}`);
  }

  // (d) prerequisite safety tiers passed
  const passed = new Set(Array.isArray(learner.passed) ? learner.passed.filter(isStr) : []);
  for (const s of t.safetySkills) if (!passed.has(s)) unmet.push(`tier: ${s} not passed`);

  reasons.push(...unmet);

  // PPE is never overridable: nobody can sign equipment onto a body.
  if (ppeMissing.length) {
    if (c.override) reasons.push('override: an override never waives PPE');
    return out(false, required, { target: id });
  }
  if (!unmet.length) {
    reasons.push(`allow: inducted, PPE checked, ${t.permits.length} permit(s), ${t.safetySkills.length} tier(s)`);
    return out(true, required, { target: id, via: 'credentials' });
  }

  // Override: only an instructor's, chained on the log, for this learner and
  // target, inside its time box, never used before.
  const o = c.override;
  if (!o) return out(false, required, { target: id });
  const bad = (why) => { reasons.push(`override: ${why}`); return out(false, required, { target: id }); };
  if (!ledgerOk.ok) return bad(`ledger does not verify (${ledgerOk.why})`);
  if (!c.ledger.holds(o, `${PREFIX}override.granted`)) return bad('token is not a granted override on the chained log');
  if (!Array.isArray(o.actor_roles) || !o.actor_roles.includes('instructor') || o.actor_roles.some((r) => AGENT_ROLES.includes(r))) return bad('not an instructor override');
  if (!isStr(o.reason) || o.reason.trim().length < GATE.minReasonChars) return bad('no reason on record');
  if (o.learner !== learner.id) return bad('issued for a different learner');
  if (o.target !== id) return bad('issued for a different target');
  if (!(o.issued_at <= c.now)) return bad('not yet valid');
  if (!(c.now < o.expires_at)) return bad(`expired at ${new Date(o.expires_at).toISOString()}`);
  if (c.ledger.rows(`${PREFIX}override.consumed`).some((e) => e.after?.override_id === o.override_id)) return bad('already used (replay)');
  reasons.push(`override: ${o.override_id} by ${o.actor} until ${new Date(o.expires_at).toISOString()} - "${o.reason}" - waives ${unmet.length} unmet item(s)`);
  return out(true, required, { target: id, via: 'override', override_id: o.override_id });
}

/**
 * The side-effecting door: decide, record the decision on the chained log,
 * and consume an override that was used so it cannot be replayed.
 */
export function enter(learner, station, context) {
  const d = canEnter(learner, station, context);
  const L = context?.ledger;
  if (L && d.target && context.index?.targets.get(d.target)?.hazardous) {
    L.append(`${PREFIX}${d.allow ? 'allow' : 'deny'}`, {
      actor: 'safety_gate', why: d.reasons.join(' | '), learner: isStr(learner?.id) ? learner.id : null,
      skill: d.target, after: { via: d.via ?? null, override_id: d.override_id ?? null } });
    if (d.via === 'override') {
      const o = context.override;
      L.append(`${PREFIX}override.consumed`, { actor: o.actor, why: o.reason, learner: learner.id, skill: d.target,
        after: { override_id: o.override_id, actor: o.actor, reason: o.reason, expires_at: o.expires_at, granted_seq: o.seq } });
    }
  }
  return d;
}
