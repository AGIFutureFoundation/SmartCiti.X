/**
 * The loop, assembled over the bus.
 *
 * This is the integration the spec described and the code did not have: the
 * control plane, the sequencer, assessment and the mentors as bus participants
 * with enforced roles, rather than objects calling each other's methods. The
 * difference that matters is that "mentors are read-only consumers of dial
 * state" is now a rule the bus applies, not a rule a reviewer has to remember.
 */
import { Bus, ContractViolation } from './bus.mjs';
import { AuditLog } from './audit.mjs';
import { envelope, extractSignals, toXapi } from './telemetry.mjs';
import { LearnerProfile, pSuccess } from '../control/lpa.mjs';
import { ZpdDial } from '../control/dial.mjs';
import { SkillGraph } from '../control/graph.mjs';
import { HintEngine } from '../control/hints.mjs';
import { Sequencer } from '../control/sequencer.mjs';
import { checkSkillGate } from '../control/gates.mjs';
import { ParityMonitor, StopConditions, OverrideManager } from './safeguards.mjs';

export class Session {
  constructor({ skills, learnerId = 'L1', clock = () => 0, strict = true } = {}) {
    this.learnerId = learnerId;
    this.audit = new AuditLog();
    this.bus = new Bus({ audit: this.audit, strict });
    this.clock = clock;

    this.profile = new LearnerProfile(learnerId);
    this.graph = new SkillGraph(skills);
    this.skillIds = skills.map((s) => s.skill_id);
    for (const id of this.skillIds) this.profile.get(id);
    this.dial = new ZpdDial(this.profile);
    this.seq = new Sequencer(this.graph, this.profile, this.dial, { clock });
    this.hints = new HintEngine(this.profile);       // ACP-04

    // Each component gets a publisher bound to its role. Nothing is handed a
    // way to claim a role it does not own.
    this.asClient = this.bus.publisherFor('client');
    this.asLpa = this.bus.publisherFor('lpa');
    this.asDial = this.bus.publisherFor('dial');
    this.asSequencer = this.bus.publisherFor('sequencer');
    this.asAssessment = this.bus.publisherFor('assessment');
    this.asMentor = this.bus.publisherFor('mentor');
    this.asHints = this.bus.publisherFor('hint_engine');   // ACP-04 owns its own topic

    // ACP-08. These sit above the loop and can override or halt it.
    this.parity = new ParityMonitor({ audit: this.audit });
    this.parity.run();                       // a never-run parity job is itself a stop
    this.stop = new StopConditions({ audit: this.audit, parity: this.parity });
    this.overrides = new OverrideManager({ audit: this.audit, bus: this.bus });

    this.history = [];
    this.pending = [];            // telemetry buffered until it is usable
    this.xapi = [];               // egress queue
    this.wire();
  }

  wire() {
    // telemetry -> signals -> profile
    this.bus.subscribe('telemetry.event', 'lpa', (m) => this.onTelemetry(m.payload));
    // telemetry -> xAPI egress (the same pipeline, an adapter on the end of it)
    this.bus.subscribe('telemetry.event', 'lrs', (m) => {
      const st = toXapi(m.payload);
      if (st) this.xapi.push(st);
    });
    // every dial adaptation lands on the audit log, which is also what the
    // learner's "Why this?" reads — one source of truth, per ACP-08
    this.bus.subscribe('dial.state_changed', 'audit', (m) => {
      const p = m.payload;
      this.audit.append({ actor: 'dial', action: `dial.${p.action}`, why: p.why,
                          before: p.before, after: p.after,
                          learner: this.learnerId, skill: p.skillId });
    });
    this.bus.subscribe('gate.decision', 'audit', (m) => {
      const p = m.payload;
      this.audit.append({ actor: 'assessment', action: 'gate.decision', why: p.why,
                          after: { pass: p.pass }, learner: this.learnerId, skill: p.skill });
    });
    // A rejected telemetry event is a client bug that must be visible, not a
    // silent no-op — the fuzz pass showed how quietly bad input can vanish.
    this.bus.subscribe('profile.updated', 'audit', (m) => {
      if (m.payload.rejected) {
        this.audit.append({ actor: 'lpa', action: 'telemetry.rejected',
                            why: m.payload.rejected, learner: this.learnerId,
                            skill: m.payload.skill });
      }
    });
    this.bus.subscribe('quest.assembled', 'audit', (m) => {
      const p = m.payload;
      this.audit.append({ actor: 'sequencer', action: `pick.${p.mode}`, why: p.why,
                          after: { difficulty: p.difficulty },
                          learner: this.learnerId, skill: p.skill });
    });
  }

  /* ------------------------------------------------------------- ingest -- */
  /** A client emits raw events; nothing else may publish on this topic. */
  emit(ev) {
    const e = envelope({ ...ev, learner_id: this.learnerId });
    if (e.error) return { rejected: e.error };
    return this.asClient('telemetry.event', e, { event_id: e.event_id });
  }

  onTelemetry(e) {
    this.pending.push(e);
    const sig = extractSignals(this.pending);
    // §1.4: fewer than three usable events produces NO profile update.
    if (!sig.usable) return { held: sig.n, reason: sig.reason };
    this.pending = [];
    return sig;
  }

  /* -------------------------------------------------------------- serve -- */
  next() {
    const pick = this.seq.next(this.skillIds, this.history);
    if (!pick) return null;

    // A human pin beats the dial; the safeguards beat both. Order matters:
    // a halted system must not honour a setpoint it no longer trusts.
    if (this.easierDelta) {
      pick.difficulty += this.easierDelta;
      pick.why = `${pick.why} Running easier today, as you asked.`;
    }
    const pinned = this.overrides.pinnedDifficulty(this.learnerId, pick.skill);
    if (pinned !== null) {
      pick.difficulty = pinned;
      pick.mode = 'pinned';
      pick.why = 'Your instructor pinned this level for you.';
    }
    if (this.stop.halted) {
      pick.difficulty = this.stop.setpointFor(this.dial, pick.skill, 50);
      pick.mode = 'halted';
      pick.why = `Adaptation is paused while we check something — ${this.stop.reasons[0]}.`;
    }
    this.asSequencer('quest.assembled', pick);
    return pick;
  }

  /** The learner's own lever (ACP-08): bounded, logged, and answered kindly. */
  easierToday() {
    const r = this.overrides.easierToday({ learner: this.learnerId });
    // Actually apply it. The UI said tasks would get easier, so they must.
    if (r.ok) this.easierDelta = (this.easierDelta ?? 0) + r.delta;
    return r;
  }

  /** Clears at the next session boundary — it is an easier DAY, not a setting. */
  clearEasier() { this.easierDelta = 0; }

  /** Record one attempt end to end, through the bus. */
  /**
   * A learner asks for help on the task currently served. Routed through the
   * hint engine so the ceiling on the served task is the ceiling that applies —
   * see `attempt()` for why the request path alone is not enough.
   */
  requestHint(pick, { rung = 1, dwellSeconds = Infinity } = {}) {
    const r = this.hints.request(pick.skill, {
      rung, dwellSeconds, taskCeiling: pick.scaffold_ceiling ?? 0,
      skill: this.graph.node(pick.skill) ?? pick.skill,
    });
    // Published as the hint engine, not as the mentor. The mentor DELIVERS
    // help; it does not decide how much is allowed. Binding this to the mentor
    // role would have let a conversational agent write the record of its own
    // restraint — the same separation the bus enforces for dial state.
    this.asHints('hint.served', { skill: pick.skill, granted: r.granted,
                                  asked: r.asked, refused: r.refused, why: r.why });
    return r;
  }

  attempt(pick, { correct, rung = 0, latency_ms = 9000 }) {
    // The recorded rung is clamped to the ceiling of the task that was served.
    //
    // The engine and the mentor both enforce the ladder, but neither of them is
    // on this path: a caller can hand `attempt()` any rung it likes, and this
    // is the function that writes the evidence certification is built from. An
    // unclamped rung here would let a hinted attempt be recorded as unaided —
    // the one lie that makes a gate meaningless. Over-rungs are recorded as
    // such rather than silently corrected.
    const ceiling = pick.scaffold_ceiling ?? 0;
    const askedRung = Math.max(0, Math.trunc(Number(rung)) || 0);
    if (askedRung > ceiling) {
      this.audit.append({ actor: 'session', action: 'hint.over_ceiling',
        why: `an attempt on ${pick.skill} was reported at rung ${askedRung} with a ceiling of `
           + `${ceiling}; recorded at the ceiling, and the discrepancy kept`,
        after: { skill: pick.skill, reported: askedRung, ceiling } });
    }
    rung = Math.min(askedRung, ceiling);
    this.hints.record(pick.skill, { rung });
    // the client's view of what happened
    this.emit({
      session_id: 's1', verb: correct ? 'completed' : 'failed',
      context: { module_id: pick.module_id ?? pick.skill, difficulty: pick.difficulty,
                 skill_ids: [pick.skill], modality: 'vr_sim', scaffold_level: rung },
      payload: { latency_ms, rung },
    });
    if (rung > 0) {
      this.emit({ session_id: 's1', verb: 'hint_requested',
                  context: { module_id: pick.module_id ?? pick.skill, skill_ids: [pick.skill] },
                  payload: { rung } });
    }

    // Evidence from an overridden episode is biased (§2.2) and weighted down.
    const w = this.overrides.evidenceWeight(this.learnerId, pick.skill);
    const rec = this.profile.record(pick.skill,
      { difficulty: pick.difficulty, correct, rung, weight: w });
    this.asLpa('profile.updated', { skill: pick.skill, theta: this.profile.get(pick.skill).theta,
                                    delta: rec.delta, rejected: rec.rejected ?? null });
    const moved = this.graph.propagate(this.profile, pick.skill, rec.delta ?? 0, { correct });

    const dialRec = this.dial.observe(pick.skill, { correct, rung, latZ: 0, difficulty: pick.difficulty });
    if (dialRec) this.asDial('dial.state_changed', dialRec);

    this.seq.record(pick.skill, { correct, mode: pick.mode });
    const before = this.profile.get(pick.skill).gated_at !== undefined;
    const g = checkSkillGate(this.profile, pick.skill, this.history);
    if (g.pass && !before) this.asAssessment('gate.decision', g);

    this.history.push({ skill: pick.skill, correct, rung, difficulty: pick.difficulty,
                        mode: pick.mode, gate_qualifying: pick.mode === 'verify' });
    return { rec, dialRec, gate: g, moved };
  }

  /** What the learner is shown — the same rows the auditor sees. */
  whyThis(n = 8) { return this.audit.whyThis(this.learnerId, n); }
}

export { ContractViolation };
