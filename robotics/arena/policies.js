/* MODEL_ARENA_POLICIES:BEGIN - the comparison policies for the four robokit world tasks (no DOM, no network).
 * One text, two runners: robotics/arena/harness.mjs loads it with new Function() at build time, and the arena page
 * embeds it verbatim, so the browser runs the very code that was measured. Every policy here is either SCRIPTED
 * (hand-written), a seeded random baseline, or the one small behaviour-cloning network whose weights are trained
 * by robotics/arena/train.mjs and pinned in robotics/arena/registry/models.json (two such networks: bc, and bcg whose
 * grip is a class-weighted classification head over features that expose the distance to the gripper's reach). None is
 * a language model.
 * Determinism: no unseeded random source, no clock; the BC forward pass uses only + - * / and abs (softsign units). */
const ArenaPolicies = (() => {
  const wrap = (a) => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
  const hash = (s) => { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const ENV_ORDER = ['world.litter-pickup', 'world.litter-sort', 'world.rov-survey', 'world.gate-drive'];
  const fieldOf = (env, name) => env.action.fields.find((f) => f.name === name) || null;

  /* CARDS: what each policy IS. A policy without a card is refused by make() and by the arena tests. */
  const CARDS = {
    scripted: { id: 'scripted', name: 'Scripted reference', kind: 'SCRIPTED', reference: true,
      what: 'the SCRIPTED reference policy of the robotics lab (potential field to the nearest open goal, reverse after a strike, grip in reach)',
      learned: false, model: 'none', not: 'not learned, not a model, not a claim about any real robot' },
    random: { id: 'random', name: 'Uniform random', kind: 'BASELINE', reference: false,
      what: 'a uniform-random baseline: every control step draws each action field uniformly from its declared range (seeded per run)',
      learned: false, model: 'none', not: 'not learned; a floor every other policy should beat' },
    greedy: { id: 'greedy', name: 'Greedy pursuit', kind: 'SCRIPTED', reference: false,
      what: 'a SCRIPTED greedy heuristic: turn and drive straight at the nearest open goal, ignore obstacles, back up and turn for 8 steps after a strike',
      learned: false, model: 'none', not: 'not learned; a simpler hand-written variant of the reference' },
    bc: { id: 'bc', name: 'Behaviour cloning (small MLP)', kind: 'TRAINED', reference: false,
      what: null,   // filled from the model registry: "a small behaviour-cloning policy trained on N SCRIPTED episodes; ..."
      learned: true, model: 'mlp', not: 'not a language model; not trained on any learner\'s data' },
    bcg: { id: 'bcg', name: 'Behaviour cloning, grip head (small MLP)', kind: 'TRAINED', reference: false,
      what: null,   // filled from the model registry
      learned: true, model: 'mlp', not: 'not a language model; not trained on any learner\'s data' },
  };
  const ORDER = ['scripted', 'random', 'greedy', 'bc', 'bcg'];
  const MODEL_POLICIES = ['bc', 'bcg'];   // the policies whose weights come from the model registry

  /* BC features (egocentric, all from the env state the sensors describe): goal bearing/distance, the two nearest
   * obstacles within 6 m (the 'near' sensor range) and the nearest wall as bearing + clearance, contact, gripper,
   * depth error, current v and w, and a one-hot of the task. 24 numbers, each roughly in [-1, 1]. */
  const F = 24;
  function features(RC, st) {
    const o = RC.obs(st), lim = st.emb.limits, R = st.emb.radius_m, H = st.env.world.arena_half_m, x = new Array(F).fill(0);
    const has = o.target_dist > 0 ? 1 : 0;
    x[0] = Math.sin(o.target_bearing); x[1] = Math.cos(o.target_bearing); x[2] = Math.min(o.target_dist, 10) / 10; x[3] = has;
    const rel = (e, n) => wrap(Math.atan2(-(e - st.e), n - st.n) - st.yaw);
    const ob = st.obst.map((b) => [Math.hypot(b.e - st.e, b.n - st.n) - b.r - R, b]).filter((p) => p[0] <= 6)
      .sort((a, b) => a[0] - b[0] || (a[1].id < b[1].id ? -1 : 1));
    for (let k = 0; k < 2; k++) { const i = 4 + 3 * k;
      if (ob[k]) { const a = rel(ob[k][1].e, ob[k][1].n); x[i] = Math.sin(a); x[i + 1] = Math.cos(a); x[i + 2] = clamp(ob[k][0], 0, 3) / 3; }
      else { x[i + 2] = 1; } }
    const walls = [[H - R - st.e, st.e + 1, st.n], [H - R + st.e, st.e - 1, st.n], [H - R - st.n, st.e, st.n + 1], [H - R + st.n, st.e, st.n - 1]]
      .sort((a, b) => a[0] - b[0]);
    const wa = rel(walls[0][1], walls[0][2]); x[10] = Math.sin(wa); x[11] = Math.cos(wa); x[12] = clamp(walls[0][0], 0, 3) / 3;
    x[13] = st.contact ? 1 : 0; x[14] = st.carrying ? 1 : 0;
    x[15] = st.env.objects.targets ? clamp((o.target_depth || 0) - (o.depth || 0), -2, 2) / 2 : 0;
    x[16] = st.v / lim.v_max_ms; x[17] = st.w / lim.w_max_rads;
    const ei = ENV_ORDER.indexOf(st.env.id); if (ei < 0) throw new Error('arena: no BC feature slot for ' + st.env.id);
    x[18 + ei] = 1; x[22] = st.env.objects.bin ? 1 : 0; x[23] = 1;   // bias-like constant input
    return x;
  }
  /* bcg features: the 24 above plus two that expose the distance to the gripper's reach, from the same sensors: the
   * signed gap between the distance to the current goal (the nearest open item, or the bin while carrying) and the
   * reach circle the gripper closes in (radius + reach_m, + 0.3 m while carrying), scaled to +-0.5 m and to +-0.1 m
   * (one control step at full speed). 0 where the task has no gripper. 26 numbers. */
  const FG = 26;
  function featuresG(RC, st) {
    const x = features(RC, st).concat([0, 0]);
    if (st.env.objects.bin) {
      const o = RC.obs(st), gap = o.target_dist - (st.emb.radius_m + st.emb.limits.reach_m + (st.carrying ? 0.3 : 0));
      x[24] = o.target_dist > 0 ? clamp(gap / 0.5, -1, 1) : 0; x[25] = o.target_dist > 0 ? clamp(gap / 0.1, -1, 1) : 0;
    }
    return x;
  }
  /* action <-> normalised target [v / v_max, w / w_max, grip, vz / vz_max] and its mask (absent fields are 0-weighted) */
  function target(st, a) {
    const lim = st.emb.limits;
    return { y: [a.v / lim.v_max_ms, a.w / lim.w_max_rads, a.grip ? 1 : 0, lim.vz_max_ms ? (a.vz || 0) / lim.vz_max_ms : 0],
      m: [1, 1, fieldOf(st.env, 'grip') ? 1 : 0, fieldOf(st.env, 'vz') ? 1 : 0] };
  }
  const softsign = (z) => z / (1 + Math.abs(z));
  function forward(W, x) {
    const h = new Array(W.hidden), y = new Array(W.out);
    for (let j = 0; j < W.hidden; j++) { let z = W.b1[j]; for (let i = 0; i < W.in; i++) z += W.W1[j * W.in + i] * x[i]; h[j] = softsign(z); }
    for (let k = 0; k < W.out; k++) { let z = W.b2[k]; for (let j = 0; j < W.hidden; j++) z += W.W2[k * W.hidden + j] * h[j]; y[k] = z; }
    return { h, y };
  }
  function decode(st, y, gripAt) {
    const lim = st.emb.limits, a = { v: clamp(y[0] * lim.v_max_ms, lim.v_min_ms, lim.v_max_ms), w: clamp(y[1] * lim.w_max_rads, -lim.w_max_rads, lim.w_max_rads) };
    if (fieldOf(st.env, 'grip')) a.grip = y[2] >= (gripAt === undefined ? 0.5 : gripAt) ? 1 : 0;
    if (fieldOf(st.env, 'vz')) a.vz = clamp(y[3] * lim.vz_max_ms, -lim.vz_max_ms, lim.vz_max_ms);
    return a;
  }

  /* make(id, ctx) -> act(st): a fresh actor per run (its own seeded stream and memory). ctx = {RoboCore, env, seed, level, model} */
  function make(id, ctx) {
    const card = CARDS[id];
    if (!card || (!card.what && !MODEL_POLICIES.includes(id)) || !card.kind) throw new Error('arena: policy ' + id + ' has no card');
    const RC = ctx.RoboCore;
    if (id === 'scripted') return (st) => RC.policy(st);
    if (id === 'random') {
      const rnd = mulberry32(hash('random|' + ctx.env.id + '|' + ctx.level + '|' + ctx.seed));
      return (st) => { const a = {}; for (const f of st.env.action.fields) a[f.name] = f.low + rnd() * (f.high - f.low);
        if ('grip' in a) a.grip = a.grip >= 0.5 ? 1 : 0; return a; };
    }
    if (id === 'greedy') {
      let back = 0;
      return (st) => {
        const o = RC.obs(st), lim = st.emb.limits, b = o.target_bearing;
        let v = Math.abs(b) < 0.35 ? lim.v_max_ms : 0.25 * lim.v_max_ms * Math.max(0, Math.cos(b)), w = clamp(2.5 * b, -lim.w_max_rads, lim.w_max_rads);
        if (st.contact && !back) back = 8;
        if (back) { back--; v = lim.v_min_ms * 0.6; w = lim.w_max_rads; }
        const a = { v, w };
        if (st.env.objects.bin) a.grip = o.target_dist < st.emb.radius_m + lim.reach_m + (st.carrying ? 0.3 : 0) ? 1 : 0;
        if (st.env.objects.targets) a.vz = clamp(2 * (o.target_depth - o.depth), -lim.vz_max_ms, lim.vz_max_ms);
        return a;
      };
    }
    if (id === 'bc') {
      const W = ctx.model;
      if (!W || W.in !== F || !W.W1 || W.W1.length !== W.hidden * W.in) throw new Error('arena: bc needs the pinned weights from the model registry');
      return (st) => decode(st, forward(W, features(RC, st)).y);
    }
    if (id === 'bcg') {
      const W = ctx.model;
      if (!W || W.in !== FG || !W.W1 || W.W1.length !== W.hidden * W.in) throw new Error('arena: bcg needs the pinned weights from the model registry');
      return (st) => decode(st, forward(W, featuresG(RC, st)).y, 0);   // grip: the head is a margin classifier, closed where its score is >= 0
    }
    throw new Error('arena: policy ' + id + ' is carded but has no actor');
  }
  return { CARDS, ORDER, MODEL_POLICIES, ENV_ORDER, F, FG, features, featuresG, target, forward, decode, softsign, make, mulberry32, hash };
})();
/* MODEL_ARENA_POLICIES:END */
