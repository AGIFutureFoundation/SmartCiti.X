/**
 * datashare/core.mjs - the data commons core: packages -> dataset manifest,
 * analysis and dataset card. Pure: no file, network, storage, DOM or clock.
 *
 * ONE CORE, THREE SHELLS. Everything lives in datashareCore(cfg, sha256hex)
 * between the DATASHARE_CORE markers. datashare/build_dataset.mjs and
 * datashare/analyse.mjs (node) and the contribute page's "Share data" section
 * (web/build_contribute.py lifts the block byte-for-byte) all run it, so the
 * browser and the CLI split, dedupe, refuse and analyse identically.
 *
 *   cfg        datashare/registry/datashare.json, parsed
 *   sha256hex  async (utf-8 string) -> 64 lowercase hex chars
 *
 * Packages are VERIFIED by the caller with the contrib verifier core
 * (contrib/verify.mjs) and handed in with the verdict; this core never
 * re-implements a verifier rule. It adds the dataset rules: duplicate,
 * revoked, licence, consent-scope, privacy (the same scan contrib.json#privacy
 * declares, applied to /1 packages too) and classroom.
 *
 * Fail closed: a missing registry field throws by name; no nullish default.
 */
/* DATASHARE_CORE:BEGIN - datashareCore(cfg, sha256hex) -> { canonical, episodeId, splitOf, privacyScan,
   buildDataset, analyse, renderCard, digestOf }. No file, network, storage, DOM or clock in here. */
function datashareCore(cfg, sha256hex) {
  function need(o, k, who) {
    if (o === null || typeof o !== 'object' || !Object.prototype.hasOwnProperty.call(o, k)) throw new Error('datashare: ' + who + ' lacks ' + JSON.stringify(k));
    return o[k];
  }
  if (typeof sha256hex !== 'function') throw new Error('datashare: a sha256hex function is required');
  const TAG = need(cfg, 'dataset_tag', 'datashare.json');
  const ACCEPTS = need(cfg, 'accepts', 'datashare.json');
  const TAGS = need(ACCEPTS, 'package_tags', 'datashare.json#accepts');
  const TAG_V2 = need(ACCEPTS, 'intake_tag', 'datashare.json#accepts');
  const FIELDS = need(cfg, 'fields_by_kind', 'datashare.json');
  const LICENCE = need(need(cfg, 'licence', 'datashare.json'), 'dataset_licence', 'datashare.json#licence');
  const COMPATIBLE = need(cfg.licence, 'compatible', 'datashare.json#licence');
  const SCOPES = need(need(cfg, 'consent_scope', 'datashare.json'), 'scopes', 'datashare.json#consent_scope');
  const RATIOS = need(need(cfg, 'split', 'datashare.json'), 'ratios', 'datashare.json#split');
  const PRIV = need(cfg, 'privacy', 'datashare.json');
  const FORBIDDEN = new Map();
  for (const [cls, keys] of Object.entries(need(PRIV, 'forbidden_keys', 'datashare.json#privacy'))) for (const k of keys) FORBIDDEN.set(k.toLowerCase(), cls);
  const EMAIL_RE = new RegExp(need(PRIV, 'email_pattern', 'datashare.json#privacy'));
  const FREE_MAX = need(PRIV, 'free_text_max', 'datashare.json#privacy');
  const ENVS = need(cfg, 'envs', 'datashare.json');
  const SIM_ENVS = need(cfg, 'sim_seat_envs', 'datashare.json');
  const OUT = need(cfg, 'outlier', 'datashare.json');
  const CARD = need(need(cfg, 'card', 'datashare.json'), 'template', 'datashare.json#card');
  const HON = need(cfg, 'honesty', 'datashare.json');
  const REVO = need(cfg, 'revocation', 'datashare.json');

  function canonical(v) {
    if (v === null || typeof v === 'boolean' || typeof v === 'string') return JSON.stringify(v);
    if (typeof v === 'number') { if (!Number.isFinite(v)) throw new Error('datashare: a non-finite number cannot be canonical'); return JSON.stringify(v); }
    if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
    if (typeof v === 'object') return '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
    throw new Error('datashare: a ' + typeof v + ' cannot be canonical');
  }
  async function episodeId(ep) { return sha256hex(canonical(ep)); }
  async function splitOf(id) {
    const bucket = parseInt((await sha256hex('split:' + id)).slice(0, 8), 16) % 100;
    if (bucket < RATIOS.train) return 'train';
    if (bucket < RATIOS.train + RATIOS.val) return 'val';
    return 'test';
  }
  async function digestOf(obj) {
    const body = {};
    for (const k of Object.keys(obj)) if (k !== 'digest') body[k] = obj[k];
    return sha256hex(canonical(body));
  }
  // the same scan contrib.json#privacy declares, over every episode of any package version
  function privacyScan(record) {
    const found = [];
    const eps = need(need(record, 'dataset', 'package'), 'episodes', 'package.dataset');
    const visit = (v, path) => {
      if (Array.isArray(v)) { v.forEach((x, i) => visit(x, path + '[' + i + ']')); return; }
      if (v !== null && typeof v === 'object') {
        for (const k of Object.keys(v)) {
          if (FORBIDDEN.has(k.toLowerCase())) found.push(path + '.' + k + ': a ' + FORBIDDEN.get(k.toLowerCase()) + ' field');
          visit(v[k], path + '.' + k);
        }
        return;
      }
      if (typeof v === 'string' && EMAIL_RE.test(v)) found.push(path + ': an email-shaped string');
      if (typeof v === 'string' && v.length > FREE_MAX) found.push(path + ': free text (' + v.length + ' characters)');
    };
    (Array.isArray(eps) ? eps : []).forEach((ep, i) => visit(ep, 'episode ' + i));
    return found;
  }
  const where = (ep) => (typeof ep.env === 'string' ? ep.env : (typeof ep.sim === 'string' ? 'sim.' + ep.sim : '(' + String(ep.kind) + ')'));

  /* packages: [{name, record, verdict: {ok: bool, rule: first failing rule or null, detail}}] in a fixed order.
     Returns {manifest, items: [{id, split, episode}]} - refusals are named in manifest.refused. */
  async function buildDataset(opts) {
    const packages = need(opts, 'packages', 'buildDataset options');
    const scope = need(opts, 'scope', 'buildDataset options');
    const builtAt = need(opts, 'built_at', 'buildDataset options');
    const revocations = need(opts, 'revocations', 'buildDataset options');
    if (!SCOPES.includes(scope)) throw new Error('datashare: scope ' + JSON.stringify(scope) + ' is not one contrib.json declares (' + SCOPES.join(', ') + ')');
    if (typeof builtAt !== 'string' || !Number.isFinite(Date.parse(builtAt))) throw new Error('datashare: built_at must be an ISO-8601 string; no clock is read here');
    if (revocations === null || typeof revocations !== 'object' || need(revocations, 'record', 'revocations') !== 'tc-revocations/1'
        || !Array.isArray(need(revocations, 'packages', 'revocations')) || !Array.isArray(need(revocations, 'episodes', 'revocations'))) {
      throw new Error('datashare: revocations must be ' + need(REVO, 'shape', 'revocation'));
    }
    const revokedP = new Set(revocations.packages), revokedE = new Set(revocations.episodes);
    const refused = [], admitted = [], seenPkg = new Set(), seenEp = new Map(), items = [];
    const excluded = { revoked_packages: 0, revoked_episodes: 0, duplicate_episodes: 0 };
    const tagsSeen = new Set();
    for (const p of packages) {
      const name = need(p, 'name', 'package entry'), rec = need(p, 'record', name), verdict = need(p, 'verdict', name);
      const refuse = (reason, detail) => refused.push({ package: name, reason: reason, detail: detail });
      if (need(verdict, 'ok', name + ' verdict') !== true) { refuse('verifier', 'contrib/verify.mjs fails ' + need(verdict, 'rule', name + ' verdict') + ': ' + need(verdict, 'detail', name + ' verdict')); continue; }
      const digest = need(need(rec, 'digest', name), 'hex', name + '.digest');
      if (!TAGS.includes(need(rec, 'record', name))) { refuse('verifier', 'record ' + JSON.stringify(rec.record) + ' is not a package tag this dataset admits'); continue; }
      if (seenPkg.has(digest)) { refuse('duplicate', 'package digest ' + digest.slice(0, 16) + ' was already admitted'); continue; }
      if (revokedP.has(digest)) { excluded.revoked_packages++; refuse('revoked', 'package digest ' + digest.slice(0, 16) + ' is on the revocation list'); continue; }
      const consent = need(rec, 'consent', name);
      if (!COMPATIBLE.includes(need(consent, 'license', name + '.consent'))) { refuse('licence', 'licence ' + JSON.stringify(consent.license) + ' is not ' + COMPATIBLE.join(' / ')); continue; }
      if (!need(consent, 'scope', name + '.consent').includes(scope)) { refuse('consent-scope', 'consent.scope ' + JSON.stringify(consent.scope) + ' does not include ' + scope); continue; }
      const priv = privacyScan(rec);
      if (priv.length) { refuse('privacy', priv.slice(0, 3).join('; ') + (priv.length > 3 ? ' (+' + (priv.length - 3) + ' more)' : '')); continue; }
      if (rec.record === TAG_V2 && need(need(rec, 'origin', name), 'classroom_mode', name + '.origin') !== false) { refuse('classroom', 'origin.classroom_mode is not false'); continue; }
      seenPkg.add(digest); tagsSeen.add(rec.record);
      const who = need(rec, 'contributor', name);
      const signed = need(who, 'signature', name + '.contributor') !== null;
      const entry = { digest: digest, record: rec.record, signed: signed,
        attribution: signed ? 'wallet ' + need(who.signature, 'address', name + '.contributor.signature') : 'unsigned package ' + digest.slice(0, 16),
        episodes: 0, admitted_episodes: 0 };
      const eps = need(need(rec, 'dataset', name), 'episodes', name + '.dataset');
      for (let i = 0; i < eps.length; i++) {
        const ep = eps[i];
        entry.episodes++;
        const id = await episodeId(ep);
        if (revokedE.has(id)) { excluded.revoked_episodes++; continue; }
        if (seenEp.has(id)) { excluded.duplicate_episodes++; seenEp.get(id).also_in.push(digest); continue; }
        const split = await splitOf(id);
        const row = { id: id, kind: ep.kind, split: split, where: where(ep), actor: typeof ep.actor === 'string' ? ep.actor : null,
          provenance: { package: digest, index: i, t: ep.t, record: rec.record }, also_in: [] };
        seenEp.set(id, row); items.push({ id: id, split: split, episode: ep }); entry.admitted_episodes++;
      }
      admitted.push(entry);
    }
    const rows = [...seenEp.values()];
    const splits = { train: 0, val: 0, test: 0 };
    for (const r of rows) splits[r.split]++;
    const manifest = {
      record: TAG, built_at: builtAt, scope: scope, licence: LICENCE,
      schema_versions: { package_tags: [...tagsSeen].sort(), fields_by_kind: FIELDS, world_kind_versions: need(cfg, 'world_kind_versions', 'datashare.json'),
        robotics_schema: need(ACCEPTS, 'robotics_schema', 'accepts'), robotics_contract_version: need(ACCEPTS, 'robotics_contract_version', 'accepts'),
        contrib_source_stamp: need(ACCEPTS, 'contrib_source_stamp', 'accepts') },
      packages: admitted, episodes: rows, splits: splits, refused: refused, excluded: excluded,
      honesty: { trained: need(HON, 'trained', 'honesty'), nothing_uploaded: need(HON, 'nothing_uploaded', 'honesty') },
    };
    manifest.digest = { alg: 'SHA-256', over: 'canonical manifest without digest', hex: await digestOf(manifest) };
    return { manifest: manifest, items: items };
  }

  const median = (xs) => { const s = [...xs].sort((a, b) => a - b); const n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
  const inRange = (x, r) => (r === null || r[0] === null || r[1] === null) ? true : (typeof x === 'number' && x >= r[0] - 1e-9 && x <= r[1] + 1e-9);

  /* items: [{id?, split?, episode}] -> the analysis the page and the CLI print */
  function analyse(items) {
    const byKind = {}, byWhere = {}, bySplit = {}, missing = {}, unknownKinds = {};
    const range = {}, series = {}, flags = [], gaps = [];
    const cover = {};
    for (const e of Object.keys(ENVS)) cover[e] = { n: 0, seeds: new Set(), embodiments: new Set(), actors: new Set() };
    items.forEach((it, ix) => {
      const ep = need(it, 'episode', 'item');
      const kind = ep !== null && typeof ep === 'object' ? ep.kind : undefined;
      const label = typeof it.id === 'string' ? it.id.slice(0, 12) : '#' + ix;
      if (typeof kind !== 'string' || !(kind in FIELDS)) { unknownKinds[String(kind)] = (unknownKinds[String(kind)] || 0) + 1; return; }
      byKind[kind] = (byKind[kind] || 0) + 1;
      if (typeof it.split === 'string') bySplit[it.split] = (bySplit[it.split] || 0) + 1;
      const lack = FIELDS[kind].filter((f) => !(f in ep) && !(f === 'operator' && ep.actor !== 'scripted-reference'));
      if (lack.length) { missing[kind] = (missing[kind] || 0) + 1; flags.push({ episode: label, where: where(ep), flag: 'missing', detail: lack.join(', ') }); }
      const w = where(ep);
      const o = ep.outcome !== null && typeof ep.outcome === 'object' ? ep.outcome : null;
      if (!(w in byWhere)) byWhere[w] = { n: 0, outcomes: 0, success: 0, kind: kind };
      byWhere[w].n++;
      if (o !== null && (typeof o.success === 'boolean' || typeof o.passed === 'boolean')) { byWhere[w].outcomes++; if (o.success === true || o.passed === true) byWhere[w].success++; }
      if (typeof ep.env === 'string' && ep.env in ENVS) {
        const env = ENVS[ep.env], c = cover[ep.env];
        c.n++; c.seeds.add(ep.seed); c.embodiments.add(ep.embodiment); c.actors.add(ep.actor);
        if (!(ep.env in range)) range[ep.env] = { checked: 0, out_of_range: 0, by_field: {} };
        const R = range[ep.env];
        const hit = (field, x, r) => { R.checked++; if (!inRange(x, r)) { R.out_of_range++; R.by_field[field] = (R.by_field[field] || 0) + 1; } };
        for (const s of Array.isArray(ep.samples) ? ep.samples : []) {
          (Array.isArray(s.pose) ? s.pose : []).forEach((x, i) => hit(['pose_e', 'pose_n', 'yaw', 'depth'][i], x, i < env.pose.length ? env.pose[i] : null));
          (Array.isArray(s.vel) ? s.vel : []).forEach((x, i) => hit(['v', 'w'][i], x, i < 2 ? env.vel[i] : null));
          (Array.isArray(s.a) ? s.a : []).forEach((x, i) => hit('a.' + (i < env.a_names.length ? env.a_names[i] : i), x, i < env.a.length ? env.a[i] : null));
        }
        if (!(ep.env in series)) series[ep.env] = [];
        series[ep.env].push({ label: label, return: o !== null ? o.return : null, steps: ep.steps, samples: Array.isArray(ep.samples) ? ep.samples.length : null });
      }
    });
    const outlierNotes = [];
    for (const [env, rows] of Object.entries(series)) {
      if (rows.length < OUT.min_n) { outlierNotes.push(env + ': ' + rows.length + ' episode(s), fewer than ' + OUT.min_n + ' - outlier rule skipped'); continue; }
      for (const f of ['return', 'steps', 'samples']) {
        const xs = rows.map((r) => r[f]).filter((x) => typeof x === 'number' && Number.isFinite(x));
        if (xs.length < OUT.min_n) continue;
        const med = median(xs), mad = median(xs.map((x) => Math.abs(x - med)));
        if (mad === 0) { outlierNotes.push(env + '.' + f + ': MAD is 0 - outlier rule skipped'); continue; }
        for (const r of rows) {
          const z = 0.6745 * (r[f] - med) / mad;
          if (typeof r[f] === 'number' && Math.abs(z) > OUT.z) flags.push({ episode: r.label, where: env, flag: 'outlier', detail: f + ' ' + r[f] + ' (robust z ' + z.toFixed(1) + ')' });
        }
      }
    }
    for (const [env, r] of Object.entries(range)) if (r.out_of_range) flags.push({ episode: '*', where: env, flag: 'range', detail: r.out_of_range + ' of ' + r.checked + ' values outside the env ranges (' + Object.entries(r.by_field).map(([k, n]) => k + ' ' + n).join(', ') + ')' });
    for (const [env, c] of Object.entries(cover)) {
      const spec = ENVS[env];
      if (c.n === 0) { gaps.push({ env: env, gap: 'no episodes' }); continue; }
      const seeds = spec.seeds.filter((s) => !c.seeds.has(s));
      if (seeds.length) gaps.push({ env: env, gap: 'seeds with no episode: ' + seeds.join(', ') });
      const embs = spec.embodiments.filter((e) => !c.embodiments.has(e));
      if (embs.length) gaps.push({ env: env, gap: 'embodiments with no episode: ' + embs.join(', ') });
      for (const a of ['human', 'scripted-reference']) if (!c.actors.has(a)) gaps.push({ env: env, gap: 'no ' + a + ' episode' });
    }
    for (const s of SIM_ENVS) if (!(s in byWhere)) gaps.push({ env: s, gap: 'no episodes' });
    const where_ = {};
    for (const k of Object.keys(byWhere).sort()) {
      const b = byWhere[k];
      where_[k] = { kind: b.kind, n: b.n, outcomes: b.outcomes, success: b.success, rate: b.outcomes ? Math.round(1000 * b.success / b.outcomes) / 1000 : null };
    }
    return { episodes: items.length, by_kind: byKind, by_split: bySplit, by_where: where_, missing_fields: missing, unknown_kinds: unknownKinds,
      range: range, flags: flags, outlier_notes: outlierNotes, gaps: gaps };
  }

  /* the datasheet-style card, every slot filled from the manifest and the analysis */
  function renderCard(manifest, analysis) {
    const kv = (o) => Object.keys(o).sort().map((k) => k + ' ' + o[k]).join(', ') || 'none';
    const envs = Object.entries(analysis.by_where).filter(([k]) => k in ENVS).map(([k, v]) => k + ' ' + v.n + (v.rate === null ? '' : ' (success ' + Math.round(100 * v.rate) + '%)'));
    const actors = {};
    for (const e of manifest.episodes) if (e.actor !== null) actors[e.actor] = (actors[e.actor] || 0) + 1;
    const slots = {
      scope: manifest.scope, trained: need(HON, 'trained', 'honesty'), episodes: String(manifest.episodes.length), packages: String(manifest.packages.length),
      by_kind: kv(analysis.by_kind), splits: kv(manifest.splits), by_env: envs.join(', ') || 'none',
      gaps: analysis.gaps.length ? analysis.gaps.length + ' (' + analysis.gaps.slice(0, 4).map((g) => g.env + ': ' + g.gap).join('; ') + (analysis.gaps.length > 4 ? '; ...' : '') + ')' : 'none',
      actors: kv(actors), duplicates: String(manifest.excluded.duplicate_episodes), revoked: String(manifest.excluded.revoked_episodes),
      refused: String(manifest.refused.length), flags: analysis.flags.length ? analysis.flags.length + ' flag(s): ' + kv(analysis.flags.reduce((m, f) => { m[f.flag] = (m[f.flag] || 0) + 1; return m; }, {})) : 'none',
      formats: need(HON, 'formats', 'honesty'), licence: manifest.licence,
      attribution: manifest.packages.map((p) => p.attribution).join('; ') || 'none', revocation: need(REVO, 'rule', 'revocation'),
      manifest_digest: manifest.digest.hex,
    };
    const fill = (s) => s.replace(/\{\{([a-z_]+)\}\}/g, (m, k) => { if (!(k in slots)) throw new Error('datashare: card slot ' + k + ' has no value'); return slots[k]; });
    const out = ['# Dataset card - ' + manifest.record + ' (' + manifest.scope + ')', '', 'Built ' + manifest.built_at + ' · manifest ' + manifest.digest.hex.slice(0, 16), ''];
    for (const sec of CARD) { out.push('## ' + sec.title, ''); for (const l of sec.lines) out.push('- ' + fill(l)); out.push(''); }
    return out.join('\n');
  }

  return { TAG: TAG, canonical: canonical, episodeId: episodeId, splitOf: splitOf, digestOf: digestOf, privacyScan: privacyScan,
    buildDataset: buildDataset, analyse: analyse, renderCard: renderCard };
}
/* DATASHARE_CORE:END */

export { datashareCore };
