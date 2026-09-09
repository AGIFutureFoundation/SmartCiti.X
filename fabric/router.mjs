/**
 * ACP-11 §12.2 — the hub-hybrid mentor topology, runnable without LLM calls.
 *
 * Chris supervises anything cross-trade or unrouted (audit trail where domain
 * boundaries are fuzzy); inside a hall, mentors hand off swarm-style (Joyce ->
 * Sam for a welding-safety question) because those boundaries are crisp.
 *
 * Published LangGraph benchmarks put supervisor routing at ~94% accuracy and
 * 2-4 LLM calls, swarm handoff at ~91% and 1-2 calls. The hybrid exists to buy
 * supervisor accuracy only where it is needed. The recursion guard is 3 hops
 * in either mode — without it, two mentors will pass a learner back and forth.
 */

export const MAX_HANDOFFS = 3;

export class Router {
  /**
   * @param {object} opts
   *   mentors:    {id: Mentor}
   *   halls:      {hallId: [mentorId, ...]}
   *   supervisor: mentorId that routes cross-trade traffic
   *   classify:   (text) => {hall, mentor|null, confidence}
   */
  constructor({ mentors, halls, supervisor, classify }) {
    this.mentors = mentors;
    this.halls = halls;
    this.supervisor = supervisor;
    this.classify = classify;
    this.log = [];
  }

  /** Which mentor should take this, and by which path. */
  route(text, hall) {
    const c = this.classify(text);
    const inHall = hall && this.halls[hall];
    if (inHall && c.mentor && this.halls[hall].includes(c.mentor) && c.confidence >= 0.6) {
      return { mentor: c.mentor, mode: 'swarm', llmCalls: 1, confidence: c.confidence };
    }
    // fuzzy or cross-trade: the supervisor decides, and the decision is logged
    return { mentor: c.mentor ?? this.supervisor, mode: 'supervisor',
             llmCalls: 2, confidence: c.confidence };
  }

  /**
   * Run one learner turn to completion, following handoffs.
   * Returns the final response plus the full hop chain for the audit log.
   */
  async handle(text, { hall = null, ctx = {} } = {}) {
    const chain = [];
    let decision = this.route(text, hall);
    let calls = decision.llmCalls;
    let current = decision.mentor;
    let response = null;
    const visited = new Set();

    for (let hop = 0; hop <= MAX_HANDOFFS; hop++) {
      const mentor = this.mentors[current];
      if (!mentor) {
        response = { text: 'Let me get an instructor.', mentor: null };
        break;
      }
      visited.add(current);
      response = await mentor.turn(text, ctx);
      chain.push({ hop, mentor: current, mode: hop === 0 ? decision.mode : 'handoff',
                   handoff: response.handoff ?? null });

      const next = response.handoff;
      if (!next) break;

      if (hop === MAX_HANDOFFS) {
        // guard tripped: stop bouncing the learner and escalate honestly
        chain.push({ hop: hop + 1, mentor: this.supervisor, mode: 'guard_tripped' });
        response = await this.mentors[this.supervisor].turn(text, { ...ctx, guard_tripped: true });
        break;
      }
      if (visited.has(next)) {
        // a loop is a routing bug; break it at the supervisor rather than spin
        chain.push({ hop: hop + 1, mentor: this.supervisor, mode: 'loop_broken' });
        response = await this.mentors[this.supervisor].turn(text, { ...ctx, loop_broken: true });
        break;
      }
      current = next;
      calls += 1;
    }

    const record = { text, hall, chain, hops: chain.length - 1, llmCalls: calls,
                     finalMentor: chain.at(-1)?.mentor ?? null, mode: decision.mode };
    this.log.push(record);
    return { response, ...record };
  }

  /** Routing accuracy against a labelled set — the metric ACP-13 reviews weekly. */
  async measureRouting(cases) {
    let right = 0, calls = 0, hops = 0;
    for (const c of cases) {
      const r = await this.handle(c.text, { hall: c.hall });
      if (r.finalMentor === c.expect) right++;
      calls += r.llmCalls; hops += r.hops;
    }
    return {
      accuracy: +(right / cases.length).toFixed(3),
      meanLlmCalls: +(calls / cases.length).toFixed(2),
      meanHops: +(hops / cases.length).toFixed(2),
      n: cases.length,
    };
  }
}

/** A deterministic keyword classifier — stands in for the model's router. */
export function keywordClassifier(table, fallbackHall = null) {
  return (text) => {
    const t = String(text).toLowerCase();
    let best = null, score = 0;
    for (const [mentor, words] of Object.entries(table)) {
      const hits = words.filter((w) => t.includes(w)).length;
      if (hits > score) { score = hits; best = mentor; }
    }
    return { mentor: best, hall: fallbackHall, confidence: score === 0 ? 0 : Math.min(1, 0.55 + 0.2 * score) };
  };
}
