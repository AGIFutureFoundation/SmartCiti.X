#!/usr/bin/env node
/**
 * Work site crew-completion verifier.
 *
 *   node worksites/verify.mjs <site-id> <record.json>...
 *
 * Takes one declared work site and N exported records - tc-completion/1
 * records and/or tc-contribution/1 packages, which carry the training
 * episodes - and reports whether, read side by side, they complete the crew:
 *
 *   record.verifies   every record verifies under its own pack's verifier
 *                     first (completion/verify.mjs, contrib/verify.mjs -
 *                     imported, never copied); one that does not stops here
 *   role.covered      every role's evidence (both ends of every hand-off it
 *                     stands at) is present in one member's own record
 *   role.distinct     each role is held by a DISTINCT identity: a wallet
 *                     address when signed, else the typed label, flagged
 *                     "identity not attested"
 *   handoff.order     hand-offs are in order by the episodes' ISO timestamps
 *                     across members: a hand-off whose to-evidence precedes
 *                     its from-evidence fails by name, as does one that
 *                     begins before the one before it closed
 *   handoff.verifiable a hand-off the registry marked unverifiable is said
 *                     so and never counted as in order
 *   identity.attested how many of the roles are held by a recovered key
 *
 * FAIL CLOSED: every field is fetched through need(); no default anywhere.
 * Every line is `ok ...` or `FAIL ...` at column 0 (FAIL on stderr), then the
 * tallies, then the honest last line from the registry. Exit 1 on any FAIL.
 */
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';
import { verify as verifyCompletion, need } from '../completion/verify.mjs';
import { verify as verifyContribution } from '../contrib/verify.mjs';

const url = (p) => new URL(p, import.meta.url);
export const REG = JSON.parse(readFileSync(url('./registry/worksites.json'), 'utf8'));
export const LAST_LINE = need(need(REG, 'verifier', 'worksites.json'), 'last_line', 'worksites.json#verifier');
const SITES = need(REG, 'sites', 'worksites.json');
const COMPLETION_TAG = 'tc-completion/1';
const CONTRIB_TAG = 'tc-contribution/1';

export function siteById(id) {
  const s = SITES.find((x) => need(x, 'id', 'site') === id);
  if (s === undefined) throw new Error(`site ${JSON.stringify(id)} is not in worksites.json (${SITES.map((x) => x.id).join(', ')})`);
  return s;
}

const evKey = (e) => {
  const k = need(e, 'kind', 'evidence');
  if (k === 'sim') return `sim ${e.sim}/${e.scenario} passed`;
  if (k === 'walkaround') return `walkaround ${e.sim}#${e.point}`;
  if (k === 'crew') return `crew ${e.crew}:${e.role} asked ${JSON.stringify(e.topic)}`;
  if (k === 'station') return `station ${e.station} done`;
  throw new Error(`evidence kind ${JSON.stringify(k)} is not one this verifier knows`);
};

/* the facts one record carries, in one shape: what happened, and when */
function factsOf(record, tag, name) {
  const facts = [];
  if (tag === CONTRIB_TAG) {
    for (const ep of need(need(record, 'dataset', name), 'episodes', name + ' dataset')) {
      const kind = need(ep, 'kind', name + ' episode');
      const t = need(ep, 't', name + ' episode');
      if (kind === 'sim') {
        facts.push({ kind: 'sim', sim: need(ep, 'sim', name), scenario: need(ep, 'scenario', name),
          passed: need(need(ep, 'outcome', name), 'passed', name) === true, hall: need(ep, 'hall', name), t, src: name });
      } else if (kind === 'walkaround') {
        facts.push({ kind: 'walkaround', sim: need(ep, 'sim', name), point: need(ep, 'point', name), hall: need(ep, 'hall', name), t, src: name });
      } else if (kind === 'crew') {
        facts.push({ kind: 'crew', crew: need(ep, 'crew', name), role: need(ep, 'role', name), topic: need(ep, 'topic', name),
          hall: need(ep, 'hall', name), t, src: name });
      }
    }
    return facts;
  }
  for (const [sid, s] of Object.entries(need(record, 'sims', name))) {
    facts.push({ kind: 'sim-seat', sim: sid, passed: need(s, 'passed', name) === true, t: null, src: name });
  }
  for (const st of need(record, 'stations', name)) facts.push({ kind: 'station', station: st, t: null, src: name });
  for (const L of need(record, 'lessons', name)) {
    for (const S of need(L, 'steps', name)) {
      if (need(S, 'done', name) !== true || S.evidence === null || typeof S.evidence !== 'object') continue;
      const ev = S.evidence, kind = need(S, 'kind', name);
      if (kind === 'sim') {
        facts.push({ kind: 'sim', sim: need(ev, 'sim', name), scenario: need(ev, 'scenario', name), passed: need(ev, 'passed', name) === true,
          hall: need(L, 'hall', name), t: null, src: name, note: 'a tc-completion sim step names no time' });
      } else if (kind === 'walkaround') {
        facts.push({ kind: 'walkaround', sim: need(ev, 'sim', name), point: need(ev, 'point', name), hall: need(ev, 'hall', name), t: need(ev, 't', name), src: name });
      }
    }
  }
  return facts;
}

/* does this fact prove this evidence? returns null when it does, else a reason
   when it is close (same seat or role) and undefined when unrelated */
function matches(ev, f, site) {
  const k = ev.kind;
  if (k === 'sim') {
    if (f.kind === 'sim-seat' && f.sim === ev.sim) return `seat ${ev.sim} is marked ${f.passed ? 'passed' : 'not passed'} in a tc-completion sims block, which names no scenario`;
    if (f.kind !== 'sim' || f.sim !== ev.sim) return undefined;
    if (f.scenario !== ev.scenario) return `sim ${ev.sim} was run on scenario ${JSON.stringify(f.scenario)}, not ${ev.scenario}`;
    if (!f.passed) return `sim ${ev.sim}/${ev.scenario} was run but not passed`;
    return null;
  }
  if (k === 'walkaround') {
    if (f.kind !== 'walkaround' || f.sim !== ev.sim) return undefined;
    return f.point === ev.point ? null : `walkaround on ${ev.sim} marked point ${JSON.stringify(f.point)}, not ${ev.point}`;
  }
  if (k === 'crew') {
    if (f.kind !== 'crew' || f.crew !== ev.crew) return undefined;
    if (f.role !== ev.role) return `crew ${ev.crew} was asked as ${f.role}, not as the ${ev.role}`;
    if (f.topic !== ev.topic) return `crew ${ev.crew}:${ev.role} was asked ${JSON.stringify(f.topic)}, not ${JSON.stringify(ev.topic)}`;
    if (!need(need(site, 'crew', 'site'), 'halls', 'site.crew').includes(f.hall)) return `the crew exchange was recorded in hall ${f.hall}, which the ${ev.crew} does not reach`;
    return null;
  }
  if (k === 'station') return f.kind === 'station' && f.station === ev.station ? null : undefined;
  throw new Error(`evidence kind ${JSON.stringify(k)}`);
}

function firstMatch(ev, facts, site) {
  const hits = facts.filter((f) => matches(ev, f, site) === null);
  if (hits.length === 0) return null;
  const timed = hits.filter((f) => typeof f.t === 'string').sort((a, b) => Date.parse(a.t) - Date.parse(b.t));
  return timed.length ? timed[0] : hits[0];
}

function whyNot(ev, facts, site) {
  const near = facts.map((f) => matches(ev, f, site)).filter((r) => typeof r === 'string');
  return near.length ? near[0] : `no ${ev.kind} evidence for it in the record`;
}

/* records: [{name, record}] - already parsed. Returns {lines, fails, tallies} */
export function verifySite(site, records) {
  const lines = [], fails = [];
  const ok = (m) => lines.push('ok ' + m);
  const bad = (m) => { lines.push('FAIL ' + m); fails.push(m); };
  const members = new Map();

  // record.verifies - each record under its own pack's verifier, first
  for (const { name, record } of records) {
    const tag = need(record, 'record', name);
    let run, who;
    if (tag === COMPLETION_TAG) { run = verifyCompletion(record); who = need(record, 'identity', name); }
    else if (tag === CONTRIB_TAG) { run = verifyContribution(record); who = need(record, 'contributor', name); }
    else { bad(`record ${name}: record.verifies - ${JSON.stringify(tag)} is neither ${COMPLETION_TAG} nor ${CONTRIB_TAG}`); continue; }
    const failing = Object.entries(run.tally).filter(([, t]) => t.fails.length);
    if (failing.length) {
      for (const [rule, t] of failing) bad(`record ${name}: ${rule} - ${t.fails[0]}`);
      continue;
    }
    const claimed = need(who, 'claimed', name + ' identity');
    const signed = run.signature.state === 'signed';
    const key = signed ? 'key:' + run.signature.recovered.toLowerCase() : 'label:' + String(claimed);
    ok(`record ${name}: ${tag} verifies; ${signed ? 'signed by ' + run.signature.recovered : 'unsigned, identity not attested'}`);
    if (!members.has(key)) members.set(key, { key, claimed: String(claimed), signed, files: [], facts: [] });
    const m = members.get(key);
    m.files.push(name);
    m.facts.push(...factsOf(record, tag, name));
  }
  if (fails.length) return finish(site, lines, fails, { roles: 0, handoffs: 0, attested: 0 }, members);

  // the evidence each role owes: both ends of every hand-off it stands at
  const roles = need(site, 'roles', 'site');
  const handoffs = need(site, 'handoffs', 'site');
  const owed = {};
  for (const r of Object.keys(roles)) owed[r] = new Map();
  for (const h of handoffs) {
    owed[need(h, 'by', 'handoff')].set(evKey(h.from_evidence), h.from_evidence);
    owed[need(h, 'to', 'handoff')].set(evKey(h.to_evidence), h.to_evidence);
  }
  const memberList = [...members.values()];
  const covers = {};
  for (const r of Object.keys(roles)) {
    covers[r] = memberList.filter((m) => [...owed[r].values()].every((ev) => firstMatch(ev, m.facts, site) !== null));
  }
  // role.distinct - a maximum matching of roles to distinct members
  const held = new Map();   // member key -> role
  const assign = {};
  const tryRole = (r, seen) => {
    for (const m of covers[r]) {
      if (seen.has(m.key)) continue;
      seen.add(m.key);
      if (!held.has(m.key) || tryRole(held.get(m.key), seen)) { held.set(m.key, r); assign[r] = m; return true; }
    }
    return false;
  };
  for (const r of Object.keys(roles)) tryRole(r, new Set());
  let nRoles = 0, nAttested = 0;
  for (const [r, spec] of Object.entries(roles)) {
    const label = `role ${r} (${spec.name}, ${spec.union})`;
    if (r in assign) {
      nRoles++;
      if (assign[r].signed) nAttested++;
      ok(`${label}: held by ${assign[r].claimed}${assign[r].signed ? ', signed' : ' - identity not attested'}; evidence: ${[...owed[r].keys()].join('; ')}`);
    } else if (covers[r].length) {
      bad(`${label}: only ${covers[r].map((m) => m.claimed).join(', ')} carries its evidence, and that identity already holds role ${covers[r].map((m) => held.get(m.key)).join(', ')} - one identity cannot hold two roles`);
    } else {
      const why = [];
      for (const ev of owed[r].values()) {
        const missing = memberList.length ? memberList.map((m) => firstMatch(ev, m.facts, site) === null ? `${m.claimed}: ${whyNot(ev, m.facts, site)}` : null).filter((x) => x !== null) : ['no records'];
        if (missing.length === memberList.length || memberList.length === 0) why.push(`${evKey(ev)} - ${missing.join(' | ')}`);
      }
      bad(`${label}: uncovered - no record carries all of its evidence (${why.join('; ')})`);
    }
  }
  // handoff.order / handoff.verifiable
  let nOrder = 0, prevClose = null;
  for (const h of handoffs) {
    const label = `handoff ${h.n} ${h.by}->${h.to}`;
    if (h.verifiable !== true) { lines.push(`unverifiable ${label}: ${h.why_unverifiable}`); prevClose = null; continue; }
    if (!(h.by in assign) || !(h.to in assign)) { bad(`${label}: role ${!(h.by in assign) ? h.by : h.to} is not covered, so the order cannot be read`); prevClose = null; continue; }
    const fr = firstMatch(h.from_evidence, assign[h.by].facts, site), to = firstMatch(h.to_evidence, assign[h.to].facts, site);
    if (typeof fr.t !== 'string' || typeof to.t !== 'string') {
      const which = typeof fr.t !== 'string' ? 'from-evidence ' + evKey(h.from_evidence) : 'to-evidence ' + evKey(h.to_evidence);
      bad(`${label}: ${which} carries no timestamp (${(typeof fr.t !== 'string' ? fr : to).note}); the tc-contribution package for that member would`);
      prevClose = null; continue;
    }
    const tf = Date.parse(fr.t), tt = Date.parse(to.t);
    if (tt < tf) { bad(`${label}: to-evidence ${evKey(h.to_evidence)} at ${to.t} precedes from-evidence ${evKey(h.from_evidence)} at ${fr.t}`); prevClose = null; continue; }
    if (prevClose !== null && tf < prevClose.t) { bad(`${label}: from-evidence ${evKey(h.from_evidence)} at ${fr.t} begins before handoff ${prevClose.n} closed at ${new Date(prevClose.t).toISOString()}`); prevClose = null; continue; }
    nOrder++;
    ok(`${label}: ${evKey(h.from_evidence)} at ${fr.t} (${assign[h.by].claimed}) -> ${evKey(h.to_evidence)} at ${to.t} (${assign[h.to].claimed})`);
    prevClose = { t: tt, n: h.n };
  }
  return finish(site, lines, fails, { roles: nRoles, handoffs: nOrder, attested: nAttested }, members);
}

function finish(site, lines, fails, n, members) {
  const roles = Object.keys(need(site, 'roles', 'site')).length;
  const handoffs = need(site, 'handoffs', 'site').length;
  const tallies = [
    `roles covered ${n.roles} of ${roles}`,
    `handoffs in order ${n.handoffs} of ${handoffs}`,
    `identities attested ${n.attested} of ${roles}`,
    `records read ${members.size === 0 ? 0 : [...members.values()].reduce((a, m) => a + m.files.length, 0)} under ${members.size} identities`,
  ];
  return { lines, fails, tallies, complete: fails.length === 0 && n.roles === roles && n.handoffs === handoffs, n };
}

const isMain = process.argv[1] && new URL(`file://${process.argv[1]}`).pathname === new URL(import.meta.url).pathname;
if (isMain) {
  const [siteId, ...files] = process.argv.slice(2);
  if (!siteId || files.length === 0) { console.error('usage: node worksites/verify.mjs <site-id> <record.json>...'); process.exit(2); }
  let site;
  try { site = siteById(siteId); } catch (e) { console.error('FAIL ' + e.message); process.exit(1); }
  const records = files.map((f) => ({ name: basename(f), record: JSON.parse(readFileSync(f, 'utf8')) }));
  let out;
  try { out = verifySite(site, records); } catch (e) { console.error('FAIL record.fields - ' + e.message); process.exit(1); }
  console.log(`site ${site.id}: ${site.title} - ${site.crew.name} at ${site.place.kind} ${site.place.id}`);
  for (const l of out.lines) (l.startsWith('FAIL') ? console.error : console.log)(l);
  for (const t of out.tallies) console.log(t);
  console.log(out.complete ? 'crew completion: complete' : 'crew completion: NOT complete');
  console.log(LAST_LINE);
  process.exit(out.fails.length ? 1 : 0);
}
