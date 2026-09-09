/**
 * ACP-13 — the registries. One source of truth per aggregate.
 *
 * The rule that gives this file its shape: external listings (NANDA, ASI)
 * MIRROR from these and never the reverse. A registry that can be written by
 * something outside the system is not a source of truth, it is a cache with
 * opinions.
 */

export const PIPELINE = ['draft', 'schema_ok', 'calibrating', 'live', 'demoted'];
const RANK = Object.fromEntries(PIPELINE.map((s, i) => [s, i]));

/** Legal transitions. Anything not listed here is refused, including no-ops. */
const TRANSITIONS = {
  draft:       ['schema_ok'],
  schema_ok:   ['calibrating', 'draft'],
  calibrating: ['live', 'demoted', 'draft'],
  live:        ['demoted', 'calibrating'],
  demoted:     ['calibrating', 'draft'],
};

export class RegistryError extends Error {}

/** Freeze a record and everything reachable from it. */
function deepFreeze(o) {
  if (o === null || typeof o !== 'object' || Object.isFrozen(o)) return o;
  Object.freeze(o);
  for (const k of Object.keys(o)) deepFreeze(o[k]);
  return o;
}

class VersionedRegistry {
  constructor(name) {
    this.name = name;
    this.records = new Map();
    this.version = 0;
    this.history = [];
  }

  /**
   * Records are handed out FROZEN.
   *
   * They used to be handed out live, which meant a caller could take the
   * record it had just been given, flip `evals.pass` to true, and promote a
   * mentor that had failed its evals — the gate was real and the object behind
   * it was writable (v2.7 defect 15). The audit log already solved this shape
   * by freezing entries and returning copies; the registries now do the same.
   * A gate in front of a mutable object is a suggestion.
   */
  get(id) { return this.records.get(id) ?? null; }
  has(id) { return this.records.has(id); }
  size() { return this.records.size; }
  ids() { return [...this.records.keys()]; }

  /** Every mutation bumps the registry version and lands in the history. */
  commit(id, next, note) {
    this.records.set(id, deepFreeze(next));
    this.version += 1;
    this.history.push(Object.freeze({ v: this.version, id, note, at: this.history.length }));
    return next;
  }
}

export class ModuleRegistry extends VersionedRegistry {
  constructor() { super('module'); }

  register(id, { state = 'draft', hall = null, rev = 1 } = {}) {
    if (!RANK.hasOwnProperty(state)) throw new RegistryError(`unknown state ${state}`);
    if (this.has(id)) throw new RegistryError(`${id} already registered`);
    return this.commit(id, { id, state, hall, rev, demotions: 0 }, `register:${state}`);
  }

  /**
   * State moves are checked against the transition table, not against rank.
   * Rank ordering would happily allow draft -> live in one step, which is
   * exactly the move the pipeline exists to prevent.
   */
  transition(id, to, reason = '') {
    const rec = this.get(id);
    if (!rec) throw new RegistryError(`${id} is not registered`);
    const allowed = TRANSITIONS[rec.state] ?? [];
    if (!allowed.includes(to)) {
      throw new RegistryError(`${id}: ${rec.state} -> ${to} is not a legal transition (allowed: ${allowed.join(', ') || 'none'})`);
    }
    const next = { ...rec, state: to };
    if (to === 'demoted') next.demotions = rec.demotions + 1;
    return this.commit(id, next, `${rec.state}->${to}${reason ? ' ' + reason : ''}`);
  }

  liveIn(hall) { return this.ids().filter((id) => { const r = this.get(id); return r.state === 'live' && r.hall === hall; }); }
  countByState() {
    const out = Object.fromEntries(PIPELINE.map((s) => [s, 0]));
    for (const id of this.ids()) out[this.get(id).state] += 1;
    return out;
  }
}

export class AgentRegistry extends VersionedRegistry {
  constructor() { super('agent'); }

  register(mentorId, version, { halls = [], evals = null } = {}) {
    const prev = this.get(mentorId) ?? { id: mentorId, versions: {}, champion: null, traffic: {} };
    // Rebuild rather than mutate: the previous record is frozen, and a caller
    // holding a reference to it must not see this write appear underneath them.
    const rec = {
      ...prev,
      versions: { ...prev.versions,
                  [version]: { version, halls: [...halls],
                               evals: evals ? { ...evals } : null, promotedAt: null } },
    };
    return this.commit(mentorId, rec, `version:${version}`);
  }

  /**
   * A version may not become champion without a passing eval record. This is
   * the check §14.3 calls "eval harness before any new mentor ships", and it
   * belongs here rather than in the rollout lane so that no other caller can
   * reach champion status by a different route.
   */
  promote(mentorId, version, { split = 1.0 } = {}) {
    const rec = this.get(mentorId);
    if (!rec) throw new RegistryError(`${mentorId} is not registered`);
    const v = rec.versions[version];
    if (!v) throw new RegistryError(`${mentorId} has no version ${version}`);
    if (!v.evals || v.evals.pass !== true) {
      throw new RegistryError(`${mentorId}@${version} has no passing eval record — a mentor ships on evidence, not intent`);
    }
    const next = { ...rec, champion: version, traffic: { ...rec.traffic, [version]: split } };
    next.versions = { ...rec.versions, [version]: { ...v, promotedAt: this.version + 1 } };
    return this.commit(mentorId, next, `champion:${version}@${split}`);
  }

  champion(mentorId) { return this.get(mentorId)?.champion ?? null; }
}

export class SkillGraphRegistry extends VersionedRegistry {
  constructor() { super('skillgraph'); }

  publish(graphVersion, { nodes, edges, migration = null }) {
    const prev = this.get('graph');
    // §14.1: an edit to the graph requires a migration script for affected
    // profiles. A prerequisite that appears retroactively can strand every
    // learner who is already past it, so the migration is not optional once a
    // graph has ever been published.
    if (prev && !migration) {
      throw new RegistryError('a graph revision requires a migration for affected profiles');
    }
    return this.commit('graph', { graphVersion, nodes, edges, migration }, `graph:${graphVersion}`);
  }

  current() { return this.get('graph'); }
}

/**
 * External listings mirror outward. The direction is enforced by there being
 * no inbound method at all: `mirror()` reads the registries and returns a
 * payload, and nothing here consumes one.
 */
export function mirror(moduleReg, agentReg) {
  return {
    generated_from: { module_version: moduleReg.version, agent_version: agentReg.version },
    modules: moduleReg.ids().filter((id) => moduleReg.get(id).state === 'live').length,
    agents: agentReg.ids().map((id) => ({ id, champion: agentReg.champion(id) }))
      .filter((a) => a.champion !== null),
    direction: 'outbound-only',
  };
}
