/**
 * ACP-01 — telemetry envelope, signal extraction and quality guards.
 *
 * The spec's §1.4 guards are the interesting part, and each exists because the
 * naive version is wrong:
 *   - dedupe on event_id, because transport is at-least-once
 *   - trust server receipt time when client clock skew exceeds two minutes
 *   - a session with fewer than three usable events produces NO profile update,
 *     because silence is not evidence
 */

export const MIN_USABLE_EVENTS = 3;
export const MAX_CLOCK_SKEW_MS = 2 * 60 * 1000;

export const VERBS = Object.freeze(['attempted', 'completed', 'failed', 'hint_requested',
  'paused', 'resumed', 'abandoned', 'edited', 'control_input', 'answered']);

/** Build a well-formed envelope, or explain why the input cannot make one. */
export function envelope({ learner_id, session_id, verb, context = {}, payload = {},
                           ts = null, event_id = null, receivedAt = Date.now() }) {
    if (!learner_id) return { error: 'missing learner_id' };
    if (!VERBS.includes(verb)) return { error: `unknown verb "${verb}"` };
    const clientTs = ts ? Date.parse(ts) : NaN;
    // Clock skew: a client clock hours off would reorder a learner's history,
    // so past a threshold the server's receipt time is the one we trust.
    const skew = Number.isFinite(clientTs) ? Math.abs(receivedAt - clientTs) : Infinity;
    const useTs = skew > MAX_CLOCK_SKEW_MS ? receivedAt : clientTs;
    return {
      event_id: event_id ?? `${learner_id}:${session_id ?? 'anon'}:${useTs}:${verb}:${Math.random().toString(36).slice(2, 8)}`,
      ts: new Date(useTs).toISOString(),
      clock_skew_ms: Number.isFinite(skew) ? skew : null,
      ts_source: skew > MAX_CLOCK_SKEW_MS ? 'server' : 'client',
      learner_id,
      session_id: session_id ?? null,
      context: {
        module_id: context.module_id ?? null,
        skill_ids: context.skill_ids ?? [],
        difficulty: context.difficulty ?? null,
        modality: context.modality ?? 'quiz',      // §1.4: missing modality -> quiz
        device_tier: context.device_tier ?? 'standard',
        scaffold_level: context.scaffold_level ?? 0,
      },
      verb,
      payload,
    };
  }

/**
 * Reduce a window of envelopes to the ACP-01 signal set.
 * Returns `{ usable:false }` when there is not enough to say anything — the
 * caller must then make NO profile update.
 */
export function extractSignals(events) {
  const seen = new Set();
  const clean = [];
  for (const e of events) {
    if (!e || e.error) continue;
    if (seen.has(e.event_id)) continue;            // at-least-once dedupe
    seen.add(e.event_id);
    clean.push(e);
  }
  const outcomes = clean.filter((e) => e.verb === 'completed' || e.verb === 'failed');
  if (clean.length < MIN_USABLE_EVENTS) {
    return { usable: false, reason: 'silence is not evidence', n: clean.length, deduped: events.length - clean.length };
  }
  const lat = outcomes.map((e) => e.payload?.latency_ms).filter(Number.isFinite);
  const mean = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
  const m = mean(lat);
  const sd = lat.length > 1 ? Math.sqrt(mean(lat.map((x) => (x - m) ** 2))) : 0;
  const hints = clean.filter((e) => e.verb === 'hint_requested');
  return {
    usable: true,
    n: clean.length,
    deduped: events.length - clean.length,
    acc: outcomes.length ? outcomes.filter((e) => e.verb === 'completed').length / outcomes.length : 0,
    lat_mean_ms: m,
    lat_var: sd,
    hint_rate: outcomes.length ? hints.length / outcomes.length : 0,
    hint_depth: mean(hints.map((e) => e.payload?.rung ?? 1)),
    idle: clean.filter((e) => e.verb === 'paused').length,
    abandon: clean.some((e) => e.verb === 'abandoned'),
    skew_events: clean.filter((e) => e.ts_source === 'server').length,
  };
}

/**
 * ACP-01 egress: envelope -> xAPI 1.0.3 statement. The spec is explicit that
 * this is an adapter on the same pipeline, not a second pipeline.
 */
const VERB_IRI = {
  attempted: 'http://adlnet.gov/expapi/verbs/attempted',
  completed: 'http://adlnet.gov/expapi/verbs/completed',
  failed: 'http://adlnet.gov/expapi/verbs/failed',
  answered: 'http://adlnet.gov/expapi/verbs/answered',
  abandoned: 'https://w3id.org/xapi/adl/verbs/abandoned',
  hint_requested: 'http://adlnet.gov/expapi/verbs/asked',
  paused: 'http://adlnet.gov/expapi/verbs/suspended',
  resumed: 'http://adlnet.gov/expapi/verbs/resumed',
  edited: 'http://adlnet.gov/expapi/verbs/interacted',
  control_input: 'http://adlnet.gov/expapi/verbs/interacted',
};

export function toXapi(e, { base = 'https://smartciti.x/xapi' } = {}) {
  if (!e || e.error) return null;
  const st = {
    id: e.event_id,
    timestamp: e.ts,
    actor: { objectType: 'Agent', account: { homePage: base, name: e.learner_id } },
    verb: { id: VERB_IRI[e.verb] ?? `${base}/verbs/${e.verb}`, display: { 'en-US': e.verb } },
    object: {
      objectType: 'Activity',
      id: `${base}/module/${e.context.module_id ?? 'unknown'}`,
      definition: { type: `${base}/activitytype/${e.context.modality}` },
    },
    context: {
      registration: e.session_id ?? undefined,
      extensions: {
        [`${base}/ext/difficulty`]: e.context.difficulty,
        [`${base}/ext/skills`]: e.context.skill_ids,
        [`${base}/ext/scaffold_level`]: e.context.scaffold_level,
      },
    },
  };
  if (e.verb === 'completed' || e.verb === 'failed') {
    st.result = { success: e.verb === 'completed',
                  duration: e.payload?.latency_ms ? `PT${(e.payload.latency_ms / 1000).toFixed(2)}S` : undefined };
  }
  // ACP-08: affect scores never leave in an export.
  return st;
}
