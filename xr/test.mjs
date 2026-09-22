/* xr/test.mjs — the head-mounted target list, checked.
 *
 * The rule, as everywhere in this bundle: recompute, never re-read. The
 * room counts below are walked out of surfaces/registry/finishes.json by a
 * second implementation, because the interesting number in this pack — how
 * many rooms require eye protection a headset does not provide — is the
 * one a reader will act on.
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); }
                       else { fail++; console.log('  FAIL ' + m); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));

const X = J('xr/registry/devices.json');
const D = X.devices;
const IDS = Object.keys(D).sort();

console.log('xr/test.mjs');

/* ---- provenance: the whole point of this pack ---------------------- */
ok(X.pack === 'xr', 'the registry names its own pack');
ok(X.honesty.status.startsWith('AUTHORED:'),
   'the honesty block opens with the tier, and it is AUTHORED — not one '
   + 'device fact here was checked against the page it cites');
ok(IDS.every((k) => D[k].provenance === 'AUTHORED'),
   'every device is AUTHORED; none claims a stronger tier');
ok(IDS.every((k) => D[k].claim_checked === false),
   'every device carries claim_checked false — a URL is not a verification, '
   + 'and this environment cannot open one');
ok(IDS.every((k) => /^https:\/\/\S+$/.test(D[k].claim_source)),
   'every device names the source the claim was relayed from, so a reader '
   + 'with network access can do what this build could not');
ok(!JSON.stringify(X).includes('AI-SYNTHESIZED'),
   'the reserved provenance word does not appear — it belongs to orbis/');
ok(/000\/ERR|could not|cannot open/i.test(X.honesty.status),
   'and the honesty block says WHY nothing is RECORDED rather than just '
   + 'that it is not');

/* ---- eye protection fails closed ----------------------------------- */
{
  const named = IDS.filter((k) => D[k].eye_protection.standard !== null);
  const unnamed = IDS.filter((k) => D[k].eye_protection.standard === null);
  ok(named.length + unnamed.length === IDS.length && unnamed.length > 0,
     `${named.length} of ${IDS.length} devices name an eye-protection `
     + `standard; ${unnamed.length} do not`);
  ok(IDS.every((k) => D[k].eye_protection.replaces_room_eye_ppe
     === (D[k].eye_protection.standard !== null)),
     'a device is recorded as replacing a room\'s eye protection if and '
     + 'only if a standard is actually named — there is no third state and '
     + 'no benefit of the doubt');
  ok(unnamed.every((k) => D[k].eye_protection.replaces_room_eye_ppe === false),
     'not one device without a named standard is recorded as replacing '
     + 'certified eyewear');
  ok(unnamed.every((k) => /CANNOT SAY|cannot say|NOT replace/.test(
       D[k].eye_protection.note)),
     'and each of those says in its own record that this is a limit of '
     + 'what is known here, not a finding about the product');
  ok(IDS.every((k) => (D[k].eye_protection.standard === null)
     === (D[k].eye_protection.delivered_by === null)),
     'a named standard and the way it is delivered travel together — '
     + '"certified" with no account of how is a claim with no content');
  ok(X.counts.eye_protection_standard_named === named.length
     && X.counts.eye_protection_not_established === unnamed.length
     && X.counts.eye_protection_by_the_device_itself
        === named.filter((k) => D[k].eye_protection.delivered_by
                                === 'the device itself').length,
     'the three eye-protection counts are the devices, counted');
}

/* ---- the rooms, recomputed from the surface registry --------------- */
{
  const fin = J('surfaces/registry/finishes.json');
  const rooms = [];
  (function walk(o) {
    if (o && typeof o === 'object' && !Array.isArray(o)) {
      if ('ppe' in o && !Array.isArray(o.ppe) === false) rooms.push(o);
      else if ('ppe' in o && Array.isArray(o.ppe)) rooms.push(o);
      else for (const v of Object.values(o)) walk(v);
    }
  }(fin));
  const has = (r, items) => (r.ppe || []).some((p) => items.includes(p));
  const eye = rooms.filter((r) => has(r, X.eye_ppe_items_counted));
  const head = rooms.filter((r) => has(r, X.head_ppe_items_counted));
  const both = eye.filter((r) => has(r, X.head_ppe_items_counted));

  ok(rooms.length === X.counts.rooms_total,
     `the room total is the surface registry's own (${rooms.length})`);
  ok(eye.length === X.counts.rooms_requiring_eye_protection,
     `${eye.length} rooms require eye protection, recounted here from the `
     + 'PPE lists rather than read back out of this pack');
  ok(head.length === X.counts.rooms_requiring_head_protection,
     `${head.length} rooms require head protection, likewise`);
  ok(both.length === X.counts.rooms_requiring_both,
     `${both.length} rooms require BOTH — the rooms where a head-mounted `
     + 'display is a third thing on a worker\'s head, not a replacement '
     + 'for either');
  ok(both.length > 0 && both.length < rooms.length,
     'and that set is neither empty nor everything, so the cross-reference '
     + 'is doing work');
  ok(X.eye_ppe_items_counted.length > 1
     && X.eye_ppe_items_counted.every(
       (i) => rooms.some((r) => (r.ppe || []).includes(i))),
     'every PPE item this pack counts as eye protection is an item that '
     + 'actually appears in the room registry — a filter matching nothing '
     + 'would quietly report zero');
  ok(X.head_ppe_items_counted.every(
       (i) => rooms.some((r) => (r.ppe || []).includes(i))),
     'and the same for head protection');
}

/* ---- attachment claims are graded, not flattened ------------------- */
{
  ok(IDS.every((k) => k in D && X.attachment_kinds[D[k].head_attachment]),
     'every device\'s attachment kind is one the pack defines');
  ok(IDS.every((k) => D[k].head_attachment_means
     === X.attachment_kinds[D[k].head_attachment]),
     'and each device carries that definition verbatim rather than a '
     + 'paraphrase of it');
  const rank = {};
  for (const k of IDS) rank[D[k].head_attachment] = D[k].head_attachment_evidence;
  ok(rank['integrator-dependent'] < rank['vendor-helmet-mount']
     && rank['vendor-helmet-mount'] < rank['integrated-certified-hardhat'],
     'the evidence ranking is ordered: a named vendor mount outranks '
     + '"an integrator will work it out", and an integrated certified '
     + 'hardhat outranks both');
  ok(new Set(IDS.map((k) => D[k].head_attachment)).size >= 4,
     'the fifteen do not all attach the same way — the column would be '
     + 'decorative if they did');
  ok(/belongs to the helmet as tested/.test(
       X.honesty.mounting_does_not_transfer_certification),
     'the pack states that hanging a device off a helmet does not transfer '
     + 'the helmet\'s rating to the combination');
}

/* ---- procurement flags --------------------------------------------- */
{
  const flagged = IDS.filter((k) => D[k].procurement_flag);
  ok(flagged.length === X.counts.procurement_flags && flagged.length > 0,
     `${flagged.length} devices carry a procurement flag this pack raised `
     + 'itself against the list as relayed');
  ok(flagged.every((k) => /not verified here/.test(
       D[k].procurement_flag.confidence)),
     'every flag says it is recollection rather than lookup, because no '
     + 'vendor host is reachable from this build');
  ok(flagged.every((k) => /high|moderate|low/.test(
       D[k].procurement_flag.confidence)),
     'and each states how sure it is, rather than asserting flatly');
  ok(flagged.every((k) => D[k].procurement_flag.consequence.length > 40),
     'and says what it means for a buyer — a flag with no consequence is '
     + 'trivia');
  ok(flagged.includes('daqri-helmet'),
     'the discontinued smart hardhat is flagged: it was relayed as a live '
     + 'option with no note attached');
}

/* ---- this pack does not close the open question -------------------- */
{
  const rnd = J('rnd/registry/rnd.json');
  const q = JSON.stringify(rnd.open_questions || rnd);
  ok(/no-headset-has-ever-run-this/.test(q),
     'rnd/ still carries the open question that no headset has run this '
     + 'bundle');
  ok(/does not close that question|must not be read as closing/.test(
       X.honesty.no_headset_has_run_this),
     'and this pack says outright that naming hardware does not close it');
  ok(/target list, not a shortlist/.test(X.honesty.not_a_recommendation),
     'the pack records the fifteen as targets and declines to reproduce '
     + 'somebody else\'s ranking as if it were a finding');
}

/* ---- the prose agrees with the arithmetic -------------------------- */
{
  const h = X.honesty;
  ok(h.eye_protection_fails_closed.includes(
       String(X.counts.eye_protection_not_established))
     && h.eye_protection_fails_closed.includes(String(X.counts.devices)),
     'the fail-closed note quotes the counts this build actually produced');
  ok(h.the_rooms_are_the_constraint.includes(
       String(X.counts.rooms_requiring_both))
     && h.the_rooms_are_the_constraint.includes(
       String(X.counts.rooms_requiring_eye_protection)),
     'and the rooms note quotes the room counts, so the sentence cannot '
     + 'drift away from the table under it');
}

/* ---- stamp and hygiene --------------------------------------------- */
{
  const src = readFileSync(join(HERE, 'build.py'));
  ok(createHash('sha256').update(src).digest('hex').slice(0, 16)
     === X.source_stamp,
     'the registry was built from the current builder (stamp check)');
  const pack = J('pack/manifest.json');
  ok(X.pack_version === pack.pack_version,
     'one bundle version, read from the manifest rather than typed here');
  ok(X.counts.devices === IDS.length
     && X.counts.vendors === new Set(IDS.map((k) => D[k].vendor)).size,
     'the headline counts are the devices and vendors, counted');
  ok(Object.values(X.counts.by_class).reduce((a, b) => a + b, 0) === IDS.length
     && Object.values(X.counts.by_attachment).reduce((a, b) => a + b, 0)
        === IDS.length,
     'both breakdowns partition the fifteen — nothing double-counted, '
     + 'nothing dropped');
  ok(IDS.every((k) => D[k].best_fit && D[k].best_fit.length > 10),
     'every device says what it is for');
}

console.log(`\n${pass} ok, ${fail} failed`);
process.exit(fail ? 1 : 0);
