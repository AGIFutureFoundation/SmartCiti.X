/**
 * Work sites, held to the registries they claim to read.
 *
 *   node worksites/test.mjs
 *
 * Stamp, every id resolved again by name, every per-site derivation and every
 * rollup recomputed from the authored declarations and the owning registries,
 * the fixture verified through the CLI and in memory, two of its records
 * signed with the throwaway-key routine completion/test.mjs exports (never a
 * second signer), every mutant failing by the name the registry gives it, and
 * no typed count anywhere: every figure is recomputed here.
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { throwawayKey, signPersonal } from '../completion/test.mjs';
import { digestOf as completionDigest, signatureMessage as completionMessage, SIGNATURE_SCHEME, SIGNED_ATTESTATION } from '../completion/verify.mjs';
import { digestOf as contribDigest, signatureMessage as contribMessage } from '../contrib/verify.mjs';
import { verifySite, siteById, REG, LAST_LINE } from './verify.mjs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };
const url = (p) => new URL(p, import.meta.url);
const read = (p) => JSON.parse(readFileSync(url(p), 'utf8'));
const need = (o, k, w) => { if (o === null || typeof o !== 'object' || !Object.prototype.hasOwnProperty.call(o, k)) throw new Error(`${w} lacks ${k}`); return o[k]; };

const reg = REG;
const crews = read('../agents/registry/crews.json').crews;
const sims = read('../sims/registry/sims.json').sims;
const unions = read('../unions/registry/unions.json').unions;
const campuses = read('../unions/registry/campuses.json').campuses;
const restoration = read('../restoration/registry/restoration.json').sites;
const spaces = read('../spaces/registry/spaces.json').spaces;
const stations = read('../stations/registry/stations.json').stations;
const training = read('../training/registry/training.json');
const finishes = read('../surfaces/registry/finishes.json');
const lessons = read('../lessons/registry/lessons.json').lessons;
const authoredDir = fileURLToPath(url('./authored/'));
const authoredFiles = readdirSync(authoredDir).filter((f) => f.endsWith('.json')).sort();
const authored = Object.fromEntries(authoredFiles.map((f) => [f.replace(/\.json$/, ''), JSON.parse(readFileSync(join(authoredDir, f), 'utf8'))]));

// ---- stamps
const stamp = createHash('sha256').update(readFileSync(url('./build.py'))).digest('hex').slice(0, 16);
ok('source_stamp is the sha256 of build.py', reg.source_stamp === stamp);
const astamp = createHash('sha256').update(Buffer.concat(authoredFiles.map((f) => readFileSync(join(authoredDir, f))))).digest('hex').slice(0, 16);
ok('authored_stamp is the sha256 of the authored declarations in name order', reg.authored_stamp === astamp);
ok('provenance separates AUTHORED declarations from DERIVED everything else', /AUTHORED/.test(reg.provenance.declarations) && /DERIVED/.test(reg.provenance.everything_else));

// ---- sites: one per authored file, ids resolve by name
const sites = reg.sites;
ok('one registry site per authored declaration, in name order', sites.map((s) => s.id).join() === Object.keys(authored).join() && sites.length === 8);
const unionSlugs = new Set(unions.map((u) => u.slug));
const walkable = new Set(restoration.filter((s) => s.walkable === true).map((s) => s.id));
const spaceById = Object.fromEntries(spaces.map((s) => [s.id, s]));
const stationIds = new Set(stations.map((s) => s.station_id));
for (const s of sites) {
  const a = authored[s.id];
  const crew = crews[s.crew.id];
  ok(`${s.id}: crew ${s.crew.id} resolves and its seat, muster and halls are read from crews.json`,
    crew !== undefined && s.crew.seat === crew.seat && s.crew.muster === crew.muster && JSON.stringify(s.crew.halls) === JSON.stringify(crew.halls));
  const pk = s.place.kind;
  ok(`${s.id}: place ${pk} ${s.place.id} resolves (${pk === 'campus' ? 'campuses.json' : pk === 'space' ? 'spaces.json' : 'restoration.json, walkable'})`,
    pk === 'campus' ? s.place.id in campuses : pk === 'space' ? s.place.id in spaceById : walkable.has(s.place.id));
  const roleUnions = Object.values(s.roles).map((r) => r.union);
  ok(`${s.id}: every role is a crew role assigned a real union, at least two distinct`,
    Object.keys(s.roles).sort().join() === Object.keys(crew.roles).sort().join() && roleUnions.every((u) => unionSlugs.has(u)) && new Set(roleUnions).size >= 2);
  ok(`${s.id}: a role's union is a hall the crew reaches, or why_not_reached says why`,
    Object.values(s.roles).every((r) => (crew.halls.includes(r.union) && r.hall_reached_by_crew === true && r.why_not_reached === null)
      || (!crew.halls.includes(r.union) && r.hall_reached_by_crew === false && typeof r.why_not_reached === 'string' && r.why_not_reached.length > 0)));
  ok(`${s.id}: the hand-offs are the crew's run, verbatim by/to and step, in order`,
    s.handoffs.length === crew.run.length && s.handoffs.every((h, i) => h.n === i + 1 && h.by === crew.run[i].by && h.to === crew.run[i].to && h.step === crew.run[i].step));
  ok(`${s.id}: stop_work is the crew's, verbatim`, s.stop_work === crew.stop_work && a.stop_work === crew.stop_work);
  const evOk = (e, role) => {
    const u = s.roles[role].union;
    if (e.kind === 'sim') return e.sim in sims && sims[e.sim].scenarios.some((x) => x.id === e.scenario) && sims[e.sim].halls.includes(u);
    if (e.kind === 'walkaround') return e.sim in sims && sims[e.sim].walkaround.some((w) => w.id === e.point) && sims[e.sim].halls.includes(u);
    if (e.kind === 'crew') return e.crew === s.crew.id && e.role === role && crew.roles[role].topics.some((t) => t.id === e.topic);
    if (e.kind === 'station') return stationIds.has(e.station);
    return false;
  };
  ok(`${s.id}: every hand-off evidence resolves by name and belongs to the role it evidences`,
    s.handoffs.every((h) => evOk(h.from_evidence, h.by) && evOk(h.to_evidence, h.to)));
  // verifiability is read from training.json, never typed
  const carried = (e) => {
    const needs = { sim: ['sim', 'scenario', 'outcome'], walkaround: ['sim', 'point'], crew: ['crew', 'role', 'topic', 'hall'], station: ['station'] }[e.kind];
    const ek = e.kind === 'station' ? null : e.kind;
    return ek !== null && ek in training.episode_kinds && needs.every((f) => training.episode_kinds[ek].fields.includes(f));
  };
  ok(`${s.id}: each evidence's verifiability recomputes from training.json#episode_kinds, and an unverifiable one says why`,
    s.handoffs.every((h) => [h.from_evidence, h.to_evidence].every((e) => e.verifiable === carried(e) && (e.verifiable || /no episode kind|records no/.test(e.why_unverifiable)))
      && h.verifiable === (h.from_evidence.verifiable && h.to_evidence.verifiable) && (h.verifiable ? h.why_unverifiable === null : typeof h.why_unverifiable === 'string')));
  // PPE
  if (pk === 'space') {
    const sp = spaceById[s.place.id];
    const want = new Set(finishes.base_conditions[sp.strand].ppe);
    for (const h of new Set(sp.hazards.map((x) => x.hazard))) for (const p of finishes.hazard_conditions[h].ppe) want.add(p);
    ok(`${s.id}: PPE recomputes from surfaces/ for the space's strand and the hazards its finishes stand for, and equals what spaces/ derived`,
      JSON.stringify(s.gates.ppe.required) === JSON.stringify([...want].sort()) && JSON.stringify(s.gates.ppe.required) === JSON.stringify([...sp.ppe.required].sort())
      && s.gates.ppe.derived_from.finishes.floor === sp.floor.id && s.gates.ppe.derived_from.finishes.wall === sp.wall.id && a.gates.ppe === 'derived');
  } else {
    ok(`${s.id}: a ${pk} has no finishes here, so PPE is null with why_none rather than typed`,
      s.gates.ppe.required === null && /no finishes/.test(s.gates.ppe.why_none) && a.gates.ppe === 'derived');
  }
  ok(`${s.id}: every walkaround gate point resolves on its seat with the registry's own check text`,
    s.gates.walkaround_before_first_move.every((g) => g.sim in sims && sims[g.sim].walkaround.some((w) => w.id === g.point && w.check === g.check && w.on_fault === g.on_fault)));
  // derived block recomputed
  const d = s.derived;
  const u2 = [...new Set(roleUnions)].sort();
  const seats = new Set([crew.seat]);
  const kinds = {};
  for (const h of s.handoffs) {
    for (const [e, r] of [[h.from_evidence, h.by], [h.to_evidence, h.to]]) { (kinds[r] = kinds[r] || new Set()).add(e.kind); if ('sim' in e) seats.add(e.sim); }
  }
  for (const g of s.gates.walkaround_before_first_move) seats.add(g.sim);
  const nv = s.handoffs.filter((h) => h.verifiable).length;
  ok(`${s.id}: derived unions, halls, seats, evidence kinds by role, hand-off counts and crew lessons recompute`,
    JSON.stringify(d.unions) === JSON.stringify(u2) && JSON.stringify(d.halls) === JSON.stringify([...new Set([...crew.halls, ...u2])].sort())
    && JSON.stringify(d.seats) === JSON.stringify([...seats].sort()) && d.handoffs === s.handoffs.length && d.handoffs_verifiable === nv
    && d.handoffs_unverifiable === s.handoffs.length - nv && d.roles === Object.keys(s.roles).length
    && JSON.stringify(d.evidence_kinds_by_role) === JSON.stringify(Object.fromEntries(Object.keys(kinds).sort().map((r) => [r, [...kinds[r]].sort()])))
    && JSON.stringify(d.lessons_with_this_crew) === JSON.stringify(Object.keys(lessons).filter((l) => lessons[l].steps.some((st) => st.kind === 'crew' && st.crew === s.crew.id)).sort()));
}

// ---- rollups
const c = reg.counts;
const allU = [...new Set(sites.flatMap((s) => s.derived.unions))].sort();
const byKind = {};
for (const s of sites) byKind[s.place.kind] = (byKind[s.place.kind] || 0) + 1;
ok('rollups recompute: sites, unions covered of 111, halls, crews used, roles, hand-offs verifiable/unverifiable, places by kind, seats',
  c.sites === sites.length && c.unions_covered === allU.length && JSON.stringify(reg.unions_covered) === JSON.stringify(allU) && c.unions_total === unions.length && unions.length === 111
  && c.halls_involved === new Set(sites.flatMap((s) => s.derived.halls)).size && c.crews_used === new Set(sites.map((s) => s.crew.id)).size && c.crews_total === Object.keys(crews).length
  && c.roles === sites.reduce((a, s) => a + s.derived.roles, 0) && c.handoffs === sites.reduce((a, s) => a + s.handoffs.length, 0)
  && c.handoffs_verifiable === sites.reduce((a, s) => a + s.derived.handoffs_verifiable, 0) && c.handoffs_unverifiable === c.handoffs - c.handoffs_verifiable
  && JSON.stringify(c.places_by_kind) === JSON.stringify(Object.fromEntries(Object.keys(byKind).sort().map((k) => [k, byKind[k]])))
  && c.seats_involved === new Set(sites.flatMap((s) => s.derived.seats)).size);
ok('at least one hand-off is marked unverifiable, so the marking is exercised, and it is a station (no episode kind carries one)',
  c.handoffs_unverifiable > 0 && sites.flatMap((s) => s.handoffs).filter((h) => !h.verifiable).every((h) => [h.from_evidence, h.to_evidence].some((e) => e.kind === 'station' && !e.verifiable)));
ok('honesty: authored scenarios, no multi-user session, not a certification, no duration or price; the last line is the verifier\'s',
  /AUTHORED/.test(reg.honesty.authored) && /no multi-user session/.test(reg.honesty.no_multi_user) && /nothing here is a certification/.test(reg.honesty.not_a_certification)
  && /no duration and no price/.test(reg.honesty.not_stated) && reg.verifier.last_line === LAST_LINE && reg.honesty.not_a_certification === LAST_LINE);
ok('no source text in worksites/ carries a nullish-coalescing default or a dict .get with a default (this line excepted)',
  ['./build.py', './verify.mjs', './test.mjs'].every((f) => readFileSync(url(f), 'utf8').split('\n').filter((l) => !/this line excepted/.test(l))
    .every((l) => !l.includes('?' + '?') && !/\.get\([^)]*,/.test(l))));

// ---- fixture: good set verifies, in memory and through the CLI
const fixDir = fileURLToPath(url('./fixture/'));
const loadDir = (sub) => readdirSync(join(fixDir, sub)).filter((f) => f.endsWith('.json')).sort().map((f) => ({ name: f, record: JSON.parse(readFileSync(join(fixDir, sub, f), 'utf8')) }));
const site = siteById(reg.fixture.site);
const good = loadDir('good');
ok('fixture files on disk are the ones the registry counts, all labelled not-a-learner and unsigned',
  reg.counts.fixture_files === readdirSync(fixDir, { withFileTypes: true }).filter((d) => d.isDirectory()).reduce((a, d) => a + readdirSync(join(fixDir, d.name)).length, 0)
  && good.every(({ record }) => /not a learner/.test((record.identity || record.contributor).claimed) && (record.identity || record.contributor).signature === null));
const g = verifySite(site, good);
ok(`the good fixture completes the crew: roles ${Object.keys(site.roles).length} of ${Object.keys(site.roles).length}, hand-offs ${site.handoffs.length} in order, 0 identities attested, ${good.length} records under 4 identities`,
  g.complete && g.fails.length === 0 && g.n.roles === Object.keys(site.roles).length && g.n.handoffs === site.handoffs.length && g.n.attested === 0
  && g.tallies.includes(`records read ${good.length} under 4 identities`) && g.lines.filter((l) => /identity not attested/.test(l)).length >= 4);
ok('a completion record and a contribution package under one label merge into one member (the rigger holds both)',
  g.lines.some((l) => /^ok role rigger .*held by fixture crew B/.test(l)) && good.filter((r) => /fixture crew B/.test((r.record.identity || r.record.contributor).claimed)).length === 2);

// ---- signed, in memory, with the routine completion/test.mjs exports
{
  const keyA = throwawayKey(), keyB = throwawayKey();
  const signContrib = (rec, key) => {
    const out = JSON.parse(JSON.stringify(rec));
    out.contributor.claimed = key.address; out.contributor.attested_by = SIGNED_ATTESTATION; out.contributor.signature = null;
    out.digest = { ...out.digest, hex: contribDigest(out) };
    const message = contribMessage(out.digest.hex, out.exported_at, out.consent.scope);
    out.contributor.signature = { scheme: SIGNATURE_SCHEME, address: key.address, message, sig: signPersonal(key.d, message) };
    return out;
  };
  const signCompletion = (rec, key) => {
    const out = JSON.parse(JSON.stringify(rec));
    out.identity.claimed = key.address; out.identity.attested_by = SIGNED_ATTESTATION; out.identity.signature = null;
    out.digest = { ...out.digest, hex: completionDigest(out) };
    const message = completionMessage(out.digest.hex, out.exported_at);
    out.identity.signature = { scheme: SIGNATURE_SCHEME, address: key.address, message, sig: signPersonal(key.d, message) };
    return out;
  };
  const signed = good.map(({ name, record }) => {
    if (name === 'member-a-lift-director.json') return { name, record: signContrib(record, keyA) };
    if (name === 'member-b-rigger.json') return { name, record: signContrib(record, keyB) };
    if (name === 'member-b-rigger-completion.json') return { name, record: signCompletion(record, keyB) };
    return { name, record };
  });
  const r = verifySite(site, signed);
  ok('with two members signed by throwaway keys (the rigger\'s package AND record under one key), the crew completes with 2 of 4 identities attested and both roles name the recovered address',
    r.complete && r.n.attested === 2 && r.lines.some((l) => new RegExp(`^ok role lift-director .*held by ${keyA.address}, signed`).test(l))
    && r.lines.some((l) => new RegExp(`^ok role rigger .*held by ${keyB.address}, signed`).test(l)) && r.tallies.includes('identities attested 2 of 4'));
  const forged = signed.map((x) => x.name === 'member-b-rigger.json' ? { name: x.name, record: (() => { const m = JSON.parse(JSON.stringify(x.record)); m.contributor.signature.sig = signPersonal(keyA.d, m.contributor.signature.message); return m; })() } : x);
  const f = verifySite(site, forged);
  ok('a package signed by another key than the one it claims fails record.verifies by contributor.signature and the crew is NOT complete',
    !f.complete && f.fails.some((m) => /^record member-b-rigger.json: contributor.signature/.test(m)));
  // the CLI, on a temp dir: what a union clerk would run
  const dir = mkdtempSync(join(tmpdir(), 'tc-worksite-'));
  try {
    const paths = signed.map(({ name, record }) => { const p = join(dir, name); writeFileSync(p, JSON.stringify(record, null, 1)); return p; });
    const cli = spawnSync(process.execPath, [fileURLToPath(url('./verify.mjs')), site.id, ...paths], { encoding: 'utf8' });
    ok('node worksites/verify.mjs <site> <records> exits 0, prints per-role and per-hand-off lines, the three tallies and the honest last line',
      cli.status === 0 && /^ok role /m.test(cli.stdout) && /^ok handoff 6 /m.test(cli.stdout) && /^roles covered 4 of 4$/m.test(cli.stdout)
      && /^handoffs in order 6 of 6$/m.test(cli.stdout) && /^identities attested 2 of 4$/m.test(cli.stdout) && cli.stdout.trim().endsWith(LAST_LINE));
    const none = spawnSync(process.execPath, [fileURLToPath(url('./verify.mjs')), 'no-such-site', paths[0]], { encoding: 'utf8' });
    ok('an unknown site id fails by name and exits 1', none.status === 1 && /^FAIL site "no-such-site" is not in worksites.json/m.test(none.stderr));
  } finally { rmSync(dir, { recursive: true, force: true }); }
}

// ---- mutants: each fails by the name the registry gives it, and by nothing outside it
for (const [name, m] of Object.entries(reg.fixture.mutants)) {
  const recs = loadDir(m.dir.replace(/^fixture\//, ''));
  const r = verifySite(site, recs);
  ok(`mutant ${name} fails by ${JSON.stringify(m.fails)} and the crew is NOT complete`,
    !r.complete && r.fails.length > 0 && r.fails[0].includes(m.fails));
  const cli = spawnSync(process.execPath, [fileURLToPath(url('./verify.mjs')), site.id, ...recs.map((x) => join(fixDir, m.dir.replace(/^fixture\//, ''), x.name))], { encoding: 'utf8' });
  ok(`mutant ${name} through the CLI exits 1 with FAIL on stderr and "crew completion: NOT complete"`,
    cli.status === 1 && /^FAIL /m.test(cli.stderr) && /^crew completion: NOT complete$/m.test(cli.stdout));
}
ok('the registry names exactly the mutants on disk and the five kinds asked for are among them',
  Object.keys(reg.fixture.mutants).sort().join() === readdirSync(fixDir).filter((d) => d.startsWith('mutant-')).map((d) => d.slice(7)).sort().join()
  && ['role-uncovered', 'two-roles-one-identity', 'handoff-out-of-order', 'bad-digest', 'wrong-scenario'].every((k) => k in reg.fixture.mutants));

console.log(`worksites: ${n} checks passed`);
