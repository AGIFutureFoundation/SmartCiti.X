/* respond/test.mjs — the first-responder scaffold, checked.
 *
 * The rule this suite follows is the bundle's: never confirm a number by
 * reading it. Every count the registry publishes is recomputed here from
 * the registry's own records, and every cross-reference is re-resolved
 * against the file it claims to come from — pack/registry/halls.json,
 * unions/registry/campuses.json, surfaces/registry/finishes.json,
 * pack/manifest.json — rather than against the copy respond/ kept.
 *
 * The safety scan is deliberately RE-IMPLEMENTED rather than imported. A
 * scan copied out of the builder would agree with the builder about a hole
 * in it. These patterns are typed out again here, and if the two ever
 * disagree the disagreement is the finding.
 *
 * There is no `??` and no `.get(k, default)` anywhere below. A lookup that
 * cannot resolve throws and names itself, because a default in a safety
 * pack is a policy decision somebody made silently.
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => {
  if (c) { pass++; console.log('  ok ' + m); }
  else { fail++; console.log('  FAIL ' + m); }
};

const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const J = (p) => JSON.parse(read(p));

/* Fail-closed read. Mirrors the builder's need(). */
const need = (o, k, what) => {
  if (o === null || typeof o !== 'object') {
    throw new Error(`respond/test: ${what}: not a mapping, cannot read ${k}`);
  }
  if (!Object.prototype.hasOwnProperty.call(o, k)) {
    throw new Error(`respond/test: ${what}: no key ${k}`);
  }
  return o[k];
};

const R = J('respond/registry/respond.json');
const HALLS = J('pack/registry/halls.json');
const CAMPUSES = J('unions/registry/campuses.json');
const FIN = J('surfaces/registry/finishes.json');
const MANIFEST = J('pack/manifest.json');

const BLOB = JSON.stringify(R);
const COMPS = need(R, 'competencies', 'registry');
const FRAMES = need(R, 'scenario_frames', 'registry');
const SERVICES = need(R, 'services', 'registry');
const AUTH = need(R, 'authorities', 'registry');
const COUNTS = need(R, 'counts', 'registry');
const GAPS = need(R, 'gaps', 'registry');
const HON = need(R, 'honesty', 'registry');
const XLINK = need(R, 'hall_cross_links', 'registry');
const DEBRIEF = need(R, 'debrief_structure', 'registry');
const SVC_KEYS = Object.keys(SERVICES).sort();

const hallRoster = need(HALLS, 'halls', 'pack/registry/halls.json')
  .map((h) => need(h, 'slug', 'pack/registry/halls.json#halls[]'));
const hallName = new Map(need(HALLS, 'halls', 'pack/registry/halls.json')
  .map((h) => [need(h, 'slug', 'halls[]'), need(h, 'name', 'halls[]')]));
const hallCampus = new Map();
for (const [ck, c] of Object.entries(need(CAMPUSES, 'campuses', 'campuses.json'))) {
  for (const s of need(c, 'halls', `campuses.${ck}`)) hallCampus.set(s, ck);
}

console.log('respond/test.mjs');

/* ---- provenance, and the stamp --------------------------------------- */
ok(need(R, 'pack', 'registry') === 'respond', 'the registry names its own pack');
ok(need(R, 'provenance', 'registry') === 'AUTHORED',
   'the provenance tier is AUTHORED — nothing here was fetched, measured or '
   + 'derived from a document this build opened');
ok(need(HON, 'status', 'honesty').startsWith('AUTHORED:'),
   'and the honesty block opens with that tier rather than burying it');
ok(!BLOB.includes('AI-SYNTHESIZED'),
   'the reserved provenance word does not appear — it belongs to orbis/');
ok(need(R, 'pack_version', 'registry')
   === need(MANIFEST, 'pack_version', 'pack/manifest.json'),
   'pack_version is the manifest\'s, not a second opinion typed here');
{
  const stamp = createHash('sha256')
    .update(readFileSync(join(HERE, 'build.py'))).digest('hex').slice(0, 16);
  ok(stamp === need(R, 'source_stamp', 'registry'),
     'source_stamp is the sha256 of the builder on disk — this registry was '
     + 'built by this build.py');
}
ok(!/https?:\/\//.test(BLOB),
   'no URL is in the payload: nothing was fetched and a citation nobody '
   + 'opened would be a costume');

/* ---- the authorities ------------------------------------------------- */
{
  const aids = Object.keys(AUTH);
  let shaped = 0, opened = 0, urls = 0;
  for (const a of aids) {
    const rec = need(AUTH, a, 'authorities');
    /* Per-field minimums: "judiciary" is a complete answer to `kind` and a
     * thin answer to `owns`, so one threshold for all of them would either
     * pass a placeholder or fail an honest word. `this_pack_reproduces` is
     * held to its wording instead, by the check below: "none of it" is the
     * complete answer and padding it would be the wrong fix. */
    const mins = { name: 20, kind: 8, owns: 40 };
    if (Object.entries(mins).every(([f, n]) =>
      typeof need(rec, f, `authorities.${a}`) === 'string'
      && need(rec, f, `authorities.${a}`).length >= n)) shaped++;
    if (need(rec, 'document_read_by_this_build', `authorities.${a}`) === true) opened++;
    if (need(rec, 'url', `authorities.${a}`) !== null) urls++;
  }
  ok(shaped === aids.length,
     `all ${aids.length} authority records say what the body is and what it owns`);
  ok(opened === 0,
     'not one authority document was opened by this build, and every record '
     + 'says so in its own field');
  ok(urls === 0, 'and not one carries a URL');
  ok(COUNTS.authorities === aids.length,
     'counts.authorities is the authority records, counted');
  ok(aids.every((a) => need(AUTH, a, 'authorities')
                       .this_pack_reproduces.startsWith('none of it')),
     'every authority record states outright that this pack reproduces none '
     + 'of its content');
}

/* ---- the services, their tiers and their representation -------------- */
{
  let badBody = 0, badTier = 0, tierItems = 0, badTierItem = 0;
  let endorsed = 0, missingNote = 0, acronyms = 0;
  for (const sk of SVC_KEYS) {
    const svc = need(SERVICES, sk, 'services');
    for (const b of need(svc, 'standards_bodies', `services.${sk}`)) {
      if (!Object.prototype.hasOwnProperty.call(AUTH, b)) badBody++;
    }
    const tiers = need(svc, 'tiers', `services.${sk}`);
    if (tiers.length < 4) badTier++;
    if (new Set(tiers.map((t) => need(t, 'id', 'tier'))).size !== tiers.length) badTier++;
    for (const t of tiers) {
      tierItems++;
      if (need(t, 'signed_off_by', 'tier') !== null
          || need(t, 'needs_practitioner_review', 'tier') !== true
          || !Object.prototype.hasOwnProperty.call(AUTH, need(t, 'authority', 'tier'))
          || need(t, 'what_the_role_is', 'tier').length < 30) badTierItem++;
    }
    const rep = need(svc, 'representation', `services.${sk}`);
    if (need(rep, 'endorsement', `services.${sk}.representation`) !== null) endorsed++;
    if (!/has reviewed, approved or endorsed/.test(
      need(rep, 'endorsement_note', `services.${sk}.representation`))) missingNote++;
    acronyms += need(rep, 'real_acronyms', `services.${sk}.representation`).length;
  }
  ok(SVC_KEYS.length === 5, 'five services: ' + SVC_KEYS.join(', '));
  ok(COUNTS.services === SVC_KEYS.length, 'counts.services is the services, counted');
  ok(badBody === 0,
     'every standards body a service names resolves to an authority record');
  ok(badTier === 0,
     'every service has at least four role tiers and no duplicate tier id');
  ok(badTierItem === 0,
     `all ${tierItems} role tiers carry an authority, a null sign-off and a `
     + 'practitioner-review flag');
  ok(COUNTS.role_tiers === tierItems, 'counts.role_tiers is the tiers, counted');
  ok(endorsed === 0,
     'not one representing organization has endorsed any of this, and the '
     + 'field is present-and-null rather than absent');
  ok(missingNote === 0, 'and every service says so in words as well as in a field');
  ok(acronyms >= 10,
     `the real organizations are named as types (${acronyms} acronyms across `
     + 'the five services) rather than avoided');
  for (const acr of ['IAFF', 'FOP', 'NAGE', 'AFSCME', 'SEIU', 'NASW']) {
    if (!BLOB.includes(acr)) ok(false, `${acr} should be named as an organization type`);
  }
  ok(['IAFF', 'FOP', 'NAGE', 'AFSCME', 'SEIU', 'NASW'].every((a) => BLOB.includes(a)),
     'IAFF, FOP, NAGE, AFSCME, SEIU and NASW are named as organization types');
}

/* ---- the competencies ------------------------------------------------ */
{
  const ids = COMPS.map((c) => need(c, 'id', 'competency'));
  ok(new Set(ids).size === ids.length, 'no competency id appears twice');
  let badSvc = 0, badTier = 0, badAuth = 0, thinLook = 0, unsigned = 0,
      unflagged = 0, thinProse = 0;
  for (const c of COMPS) {
    const sk = need(c, 'service', 'competency');
    if (!Object.prototype.hasOwnProperty.call(SERVICES, sk)) { badSvc++; continue; }
    const tierIds = need(SERVICES[sk], 'tiers', `services.${sk}`)
      .map((t) => need(t, 'id', 'tier'));
    if (!tierIds.includes(need(c, 'tier_floor', c.id))) badTier++;
    if (!Object.prototype.hasOwnProperty.call(AUTH, need(c, 'authority', c.id))) badAuth++;
    if (need(c, 'look_for', c.id).length < 3) thinLook++;
    if (need(c, 'signed_off_by', c.id) !== null) unsigned++;
    if (need(c, 'needs_practitioner_review', c.id) !== true) unflagged++;
    for (const f of ['what_it_is', 'why_it_matters', 'title']) {
      if (need(c, f, c.id).length < 24) thinProse++;
    }
  }
  ok(badSvc === 0, 'every competency belongs to a service this registry describes');
  ok(badTier === 0,
     'every competency\'s tier_floor is a real tier OF THAT SERVICE — a '
     + 'competency cannot enter at a rank its service does not have');
  ok(badAuth === 0,
     'every competency names an authority that resolves — the body that owns '
     + 'the real standard is always identified');
  ok(thinLook === 0,
     'every competency carries at least three observable behaviours, so a '
     + 'debrief has something to watch rather than something to feel');
  ok(unsigned === 0, 'no competency claims a sign-off');
  ok(unflagged === 0,
     'every competency carries needs_practitioner_review true, without exception');
  ok(thinProse === 0, 'no competency has a placeholder title or description');
  ok(COUNTS.competencies === COMPS.length,
     'counts.competencies is the competencies, counted');
  ok(COUNTS.observable_behaviours
     === COMPS.reduce((a, c) => a + c.look_for.length, 0),
     'counts.observable_behaviours is every look_for line, added up');
  ok(COMPS.length >= 40,
     `the breadth is real: ${COMPS.length} competency domains across five services`);
  ok(SVC_KEYS.every((sk) => COMPS.filter((c) => c.service === sk).length >= 8),
     'no service is a token entry — each carries at least eight domains');
  ok(SVC_KEYS.every((sk) => need(need(COUNTS, 'by_service', 'counts'), sk,
                                 'counts.by_service').competencies
                            === COMPS.filter((c) => c.service === sk).length),
     'counts.by_service is recomputed per service and matches');
}

/* ---- the scenario frames --------------------------------------------- */
{
  const ids = FRAMES.map((s) => need(s, 'id', 'frame'));
  ok(new Set(ids).size === ids.length, 'no scenario frame id appears twice');
  const compIds = new Set(COMPS.map((c) => c.id));
  let badSvc = 0, badComp = 0, badHall = 0, noCampus = 0, thinQ = 0,
      thinC = 0, badAuth = 0, noNot = 0, unsigned = 0, unflagged = 0;
  for (const s of FRAMES) {
    for (const sk of need(s, 'services', s.id)) {
      if (!Object.prototype.hasOwnProperty.call(SERVICES, sk)) badSvc++;
    }
    for (const c of need(s, 'competencies', s.id)) if (!compIds.has(c)) badComp++;
    for (const h of need(s, 'halls', s.id)) {
      if (!hallRoster.includes(h)) badHall++;
      if (!hallCampus.has(h)) noCampus++;
    }
    if (need(s, 'debrief_questions', s.id).length < 4) thinQ++;
    if (new Set(need(s, 'competencies', s.id)).size < 4) thinC++;
    if (!Object.prototype.hasOwnProperty.call(AUTH, need(s, 'authority', s.id))) badAuth++;
    if (need(s, 'this_frame_is_not', s.id).length < 40) noNot++;
    if (need(s, 'signed_off_by', s.id) !== null) unsigned++;
    if (need(s, 'needs_practitioner_review', s.id) !== true) unflagged++;
    for (const f of ['situation', 'decision_pressure', 'setting']) {
      if (need(s, f, s.id).length < 20) noNot++;
    }
  }
  ok(badSvc === 0, 'every frame names services this registry describes');
  ok(badComp === 0,
     'every competency a frame claims to exercise is a competency that exists');
  ok(badHall === 0,
     'every hall slug in every frame resolves against pack/registry/halls.json '
     + '— re-read here, not taken from respond\'s own copy');
  ok(noCampus === 0,
     'and every one of them is on a campus roster in '
     + 'unions/registry/campuses.json');
  ok(thinQ === 0, 'every frame asks at least four debrief questions');
  ok(thinC === 0, 'every frame exercises at least four distinct competencies');
  ok(badAuth === 0, 'every frame names the authority that owns the real answer');
  ok(noNot === 0,
     'every frame states in its own words what it is NOT, and no frame has a '
     + 'placeholder situation, setting or pressure');
  ok(unsigned === 0, 'no frame claims a sign-off');
  ok(unflagged === 0, 'every frame carries needs_practitioner_review true');
  ok(COUNTS.scenario_frames === FRAMES.length,
     'counts.scenario_frames is the frames, counted');
  ok(COUNTS.debrief_questions
     === FRAMES.reduce((a, s) => a + s.debrief_questions.length, 0),
     'counts.debrief_questions is every question, added up');
  ok(COUNTS.multi_agency_frames
     === FRAMES.filter((s) => s.services.length >= 3).length,
     'counts.multi_agency_frames is the frames with three or more services on '
     + 'the same incident, counted');
  ok(COUNTS.multi_agency_frames > 0 && COUNTS.multi_agency_frames < FRAMES.length,
     'some frames are multi-agency and some are not — the ICS problem is not '
     + 'sprayed over everything to inflate a number');
  const noHall = FRAMES.filter((s) => s.halls.length === 0).map((s) => s.id).sort();
  ok(COUNTS.frames_without_hall_contact === noHall.length
     && JSON.stringify(need(R, 'frames_without_hall_contact', 'registry')) === JSON.stringify(noHall),
     `the ${noHall.length} frames touching no trade hall are counted AND named `
     + '— a crisis call in a flat is not a building problem and the pack does '
     + 'not invent a link to improve a coverage number');
}

/* ---- the cross-links into the 111 halls ------------------------------ */
{
  const want = new Map();
  for (const s of FRAMES) for (const h of s.halls) {
    if (!want.has(h)) want.set(h, []);
    want.get(h).push(s.id);
  }
  const keys = Object.keys(XLINK).sort();
  ok(keys.join() === [...want.keys()].sort().join(),
     'hall_cross_links holds exactly the halls the frames name — no extra, '
     + 'no missing');
  let badFrames = 0, badName = 0, badCampus = 0, badPpe = 0;
  for (const h of keys) {
    const rec = need(XLINK, h, 'hall_cross_links');
    if (need(rec, 'frames', h).join() !== want.get(h).sort().join()) badFrames++;
    if (need(rec, 'hall_name', h) !== hallName.get(h)) badName++;
    if (need(rec, 'campus', h) !== hallCampus.get(h)) badCampus++;
    const conds = need(need(need(FIN, 'halls', 'finishes'), h, 'finishes.halls'),
                       'conditions', `finishes.halls.${h}`);
    const ppe = [...new Set(Object.entries(conds)
      .flatMap(([room, r]) => need(r, 'ppe', `finishes.halls.${h}.conditions.${room}`)))].sort();
    if (JSON.stringify(need(rec, 'trade_ppe_in_that_hall', h)) !== JSON.stringify(ppe)) badPpe++;
  }
  ok(badFrames === 0, 'each hall lists exactly the frames that name it');
  ok(badName === 0,
     'each cross-link\'s hall name is the name pack/registry/halls.json gives it');
  ok(badCampus === 0,
     'each cross-link\'s campus is the campus unions/registry/campuses.json '
     + 'puts that hall on');
  ok(badPpe === 0,
     'each cross-link\'s trade PPE list is recomputed from '
     + 'surfaces/registry/finishes.json — it is the TRADE\'s teaching-space '
     + 'PPE and it is not restated here by hand');
  ok(COUNTS.halls_touched === keys.length,
     'counts.halls_touched is the distinct halls, counted');
  ok(COUNTS.halls_total === hallRoster.length,
     'counts.halls_total is the roster length in pack/registry/halls.json');
  ok(COUNTS.hall_cross_links
     === keys.reduce((a, h) => a + XLINK[h].frames.length, 0),
     'counts.hall_cross_links is every hall-to-frame link, added up');
  const untouched = hallRoster.filter((h) => !keys.includes(h)).sort();
  ok(COUNTS.halls_untouched === untouched.length
     && JSON.stringify(need(R, 'halls_untouched', 'registry')) === JSON.stringify(untouched),
     `the ${untouched.length} halls no frame touches are counted AND listed by `
     + 'name, so the omission is inspectable rather than implied');
  ok(COUNTS.halls_touched + COUNTS.halls_untouched === COUNTS.halls_total,
     'touched and untouched partition the roster exactly');
}

/* ---- competency coverage --------------------------------------------- */
{
  const used = new Set(FRAMES.flatMap((s) => s.competencies));
  const unused = COMPS.map((c) => c.id).filter((c) => !used.has(c)).sort();
  ok(COUNTS.competencies_exercised === used.size,
     'counts.competencies_exercised is the distinct competencies the frames name');
  ok(COUNTS.competencies_unexercised === unused.length
     && JSON.stringify(need(R, 'competencies_unexercised', 'registry')) === JSON.stringify(unused),
     `the ${unused.length} competencies no frame exercises are counted AND `
     + 'named rather than averaged away');
  ok(COUNTS.competencies_exercised + COUNTS.competencies_unexercised
     === COMPS.length, 'exercised and unexercised partition the competencies');
}

/* ---- the debrief structure ------------------------------------------- */
{
  ok(DEBRIEF.length >= 6 && COUNTS.debrief_stages === DEBRIEF.length,
     `counts.debrief_stages is the stages, counted (${DEBRIEF.length})`);
  ok(DEBRIEF.every((d, i) => need(d, 'n', 'debrief stage') === i + 1),
     'the debrief stages are numbered 1..n with no gap');
  ok(DEBRIEF.every((d) => need(d, 'question', 'stage').length > 20
                       && need(d, 'purpose', 'stage').length > 40),
     'every stage says what it asks and why it is asked in that order');
  ok(/authority/i.test(JSON.stringify(DEBRIEF))
     && /left this pack|belongs|owner/i.test(JSON.stringify(DEBRIEF)),
     'the debrief structure itself hands the argument back to the governing '
     + 'body the moment it becomes an argument about correct procedure');
}

/* ---- the training items and the sign-off gap ------------------------- */
{
  const tiers = SVC_KEYS.reduce((a, sk) => a + SERVICES[sk].tiers.length, 0);
  ok(COUNTS.training_items === tiers + COMPS.length + FRAMES.length,
     `counts.training_items is ${tiers} tiers + ${COMPS.length} competencies `
     + `+ ${FRAMES.length} frames, added up here`);
  ok(COUNTS.signed_off_items === 0, 'counts.signed_off_items is zero');
  ok(COUNTS.organization_endorsements === 0,
     'counts.organization_endorsements is zero');
  ok(COUNTS.authority_documents_opened === 0,
     'counts.authority_documents_opened is zero');
  const byId = new Map(GAPS.map((g) => [need(g, 'id', 'gap'), g]));
  ok(byId.size === GAPS.length, 'no gap id appears twice');
  ok(GAPS.length >= 8, `${GAPS.length} gaps are published`);
  let badShare = 0, badMissing = 0, overflow = 0, thin = 0;
  for (const g of GAPS) {
    const have = need(g, 'have', g.id), of = need(g, 'of', g.id);
    /* The builder rounds to four places, so the tolerance is half a unit
     * in the last published place and not machine epsilon. */
    if (Math.abs(need(g, 'share', g.id) - have / of) > 5e-5) badShare++;
    if (need(g, 'missing', g.id) !== of - have) badMissing++;
    if (have > of || of <= 0) overflow++;
    if (need(g, 'how', g.id).length < 40 || need(g, 'note', g.id).length < 40) thin++;
  }
  ok(badShare === 0, 'every gap share is have/of, recomputed');
  ok(badMissing === 0, 'every gap missing is of-have, recomputed');
  ok(overflow === 0, 'no gap claims more than it counts against');
  ok(thin === 0, 'every gap says how it was computed and what it means');
  const signoff = GAPS.filter((g) => g.id.includes('signed_off'));
  ok(signoff.length >= 4,
     `${signoff.length} separate sign-off gaps are published, not one summary `
     + 'number that could hide a partial answer');
  ok(signoff.every((g) => g.have === 0 && g.of > 0),
     'every sign-off gap reads 0 of N with N greater than zero — the same '
     + 'shape as pack.signed_off_halls at 0/111');
  ok(need(byId.get('respond.signed_off_items'), 'of', 'gap')
     === COUNTS.training_items,
     'the widest sign-off gap counts against every training item this build '
     + 'produced');
  ok(need(byId.get('respond.signed_off_competencies'), 'of', 'gap')
     === COMPS.length
     && need(byId.get('respond.signed_off_scenario_frames'), 'of', 'gap')
        === FRAMES.length
     && need(byId.get('respond.signed_off_role_tiers'), 'of', 'gap') === tiers,
     'each sign-off gap counts against the right denominator, recomputed');
  ok(need(byId.get('respond.halls_touched_by_a_frame'), 'have', 'gap')
     === COUNTS.halls_touched
     && need(byId.get('respond.halls_touched_by_a_frame'), 'of', 'gap')
        === hallRoster.length,
     'the hall coverage gap is measured against the live roster, and it is '
     + 'not zero — a gap block that only carried zeroes would be theatre');
  ok(need(byId.get('respond.practitioner_reviewed_services'), 'have', 'gap') === 0
     && need(byId.get('respond.practitioner_reviewed_services'), 'of', 'gap')
        === SVC_KEYS.length,
     'no service has been reviewed, and the denominator is the five services');
}

/* ---- the honesty block earns every number it quotes ------------------ */
{
  const q = (s, n) => String(s).includes(String(n));
  ok(q(need(HON, 'status', 'honesty'), COUNTS.authorities),
     'the status note quotes the authority count it claims');
  const nq = need(HON, 'nobody_qualified_has_read_this', 'honesty');
  ok(q(nq, COUNTS.training_items) && q(nq, COUNTS.signed_off_items),
     'the sign-off note quotes both the item count and the zero');
  ok(/serving firefighter/i.test(nq) && /police officer/i.test(nq)
     && /paramedic/i.test(nq) && /emergency manager/i.test(nq)
     && /licensed social worker/i.test(nq),
     'and it names all five kinds of practitioner who have not read this, '
     + 'rather than saying "an expert"');
  ok(/must not be used as the basis of any real certification/i.test(nq),
     'and says outright that it must not be used as the basis of real '
     + 'certification');
  const sc = need(HON, 'scaffold_not_protocol', 'honesty');
  ok(q(sc, COUNTS.forbidden_patterns_scanned) && q(sc, COUNTS.training_items),
     'the scaffold note quotes the number of forbidden patterns scanned and '
     + 'the number of items that name an authority');
  ok(/no procedure/i.test(sc) && /no drug/i.test(sc) && /no dose/i.test(sc)
     && /no triage cut-off/i.test(sc) && /no tactical technique/i.test(sc),
     'and lists what it refuses to carry, item by item');
  const un = need(HON, 'unions_and_associations', 'honesty');
  ok(q(un, COUNTS.services) && q(un, COUNTS.organization_endorsements),
     'the union note quotes the service count and the endorsement count');
  ok(/no local, lodge, chapter, council or bargaining unit number/i.test(un)
     && /has reviewed, approved or endorsed/i.test(un),
     'and states that no local number appears and that nobody endorsed this');
  const xl = need(HON, 'the_cross_links_are_real', 'honesty');
  ok(q(xl, COUNTS.halls_touched) && q(xl, COUNTS.halls_untouched)
     && q(xl, COUNTS.halls_total) && q(xl, COUNTS.frames_without_hall_contact),
     'the cross-link note quotes all four of the numbers it describes');
  const cv = need(HON, 'coverage_is_published_as_a_number', 'honesty');
  ok(q(cv, COUNTS.competencies) && q(cv, COUNTS.scenario_frames)
     && q(cv, COUNTS.competencies_exercised) && q(cv, COUNTS.halls_touched)
     && q(cv, GAPS.length),
     'the coverage note quotes the competency, frame, exercised, hall and gap '
     + 'counts it claims');
  ok(q(need(HON, 'what_a_frame_is', 'honesty'), COUNTS.scenario_frames),
     'the frame note quotes the number of frames');
  ok(q(need(HON, 'the_debrief_structure_is_ours', 'honesty'), DEBRIEF.length),
     'the debrief note quotes the number of stages');
  ok(/not the federal exercise/i.test(need(HON, 'the_debrief_structure_is_ours', 'honesty'))
     && /critical incident stress/i.test(need(HON, 'the_debrief_structure_is_ours', 'honesty')),
     'and disclaims the two things a debrief structure is most likely to be '
     + 'mistaken for');
  ok(/not responder PPE/i.test(need(HON, 'ppe_is_not_transferable', 'honesty')),
     'the PPE note says outright that trade PPE is not responder PPE and does '
     + 'not transfer');
  /* The checks above ask whether each number APPEARS in its note. That is
   * not enough: a note that says "the 117 training items ... the number is
   * 0 of 118" still contains both 117 and 0, and a mutation test caught
   * exactly that. So the ratios are also checked as CONTIGUOUS phrases. */
  ok(nq.includes(`${COUNTS.signed_off_items} of ${COUNTS.training_items}`),
     `the sign-off note reads "${COUNTS.signed_off_items} of `
     + `${COUNTS.training_items}" as one phrase, not two numbers that happen `
     + 'to be in the same paragraph');
  ok(un.includes(`${COUNTS.organization_endorsements} of `
                 + `${COUNTS.services} services`),
     'the union note reads the endorsement ratio as one phrase');
  ok(xl.includes(`${COUNTS.halls_untouched} of the ${COUNTS.halls_total} halls`),
     'the cross-link note reads the untouched-halls ratio as one phrase');
  ok(cv.includes(`${COUNTS.competencies_exercised} of `
                 + `${COUNTS.competencies}`)
     && cv.includes(`${COUNTS.halls_touched} halls touched of`),
     'the coverage note reads its two ratios as phrases rather than as loose '
     + 'numbers');
  ok(Object.keys(HON).length >= 8,
     `the honesty block carries ${Object.keys(HON).length} separate admissions`);
  ok(!/\b(authoritative|best.in.class|world.class|industry.leading|gold standard|state.of.the.art)\b/i.test(BLOB),
     'the registry never calls itself authoritative or any of its cousins');
  {
    const hits = BLOB.match(/comprehensive/gi);
    const negated = BLOB.match(/described as comprehensive/gi);
    ok(hits !== null && negated !== null && hits.length === negated.length,
       'the only place the word "comprehensive" appears is the sentence '
       + 'denying that this pack is one');
  }
}

/* ---- the safety scan, re-implemented -------------------------------- */
{
  /* Typed out again rather than imported from the builder. If these ever
   * disagree with build.py's list, that disagreement is the finding. */
  const PATTERNS = [
    ['a dose, rate or engineering figure with a unit attached',
     /\b\d+(\.\d+)?\s*(mg|mcg|ug|ml|cc|mL|gram|grams|units?|joules?|J\b|gpm|lpm|psi|bar|kPa|mmHg|bpm|L\/min|mg\/kg|mcg\/kg)\b/],
    ['a named local, lodge, chapter, council or apparatus number',
     /\b(local|lodge|chapter|council|branch|post|unit|station|engine|truck|medic|squad|battalion|district|company)\s+(no\.?\s*)?\d+\b/i],
    ['a person named behind a rank or honorific',
     /\b(Chief|Captain|Lieutenant|Sergeant|Officer|Firefighter|Paramedic|Deputy|Sheriff|Commissioner|Dr\.|Prof\.)\s+(?!(?:Standards|Officer|Officers|Training|Safety|Support)\b)[A-Z][a-z]{2,}/],
    ['a reserved provenance word that belongs to orbis/', /AI-SYNTHESIZED/],
    ['a clinical agent or intervention named as if it were guidance',
     /\b(epinephrine|naloxone|adrenaline|midazolam|ketamine|fentanyl|tourniquet|defibrillat|intubat|cricothyro|needle decompress|chest seal)\w*/i],
    ['a triage category or scoring threshold presented as a cut-off',
     /\b(START triage|SALT triage|triage tag|immediate\/delayed|Glasgow Coma|GCS \d|RPM score)\b/i],
    ['a tactical entry, restraint or control instruction',
     /\b(breach the|stack on|dynamic entry|prone restraint|chokehold|carotid|pressure point|joint lock|forced entry technique)\b/i],
    ['a run-time fetch', /https?:\/\//],
  ];
  ok(PATTERNS.length === COUNTS.forbidden_patterns_scanned,
     `this suite re-implements all ${PATTERNS.length} forbidden patterns the `
     + 'builder claims to scan');
  for (const [label, re] of PATTERNS) {
    const m = BLOB.match(re);
    ok(m === null, `the safety scan finds nothing matching: ${label}`
       + (m === null ? '' : ` — found ${JSON.stringify(m[0])}`));
  }
  /* A second, blunter pass: no digit may sit next to a word that would make
   * it read as an operational figure, and no rank may be followed by a
   * possessive personal name. */
  ok(!/\b\d+\s*(minutes? of air|psi|second rule|compressions?)\b/i.test(BLOB),
     'no number in this registry reads as a timing, pressure or count a '
     + 'reader could act on');
  ok(COMPS.every((c) => !/\bstep 1\b|\bstep one\b|\bfirst,? then\b/i.test(JSON.stringify(c))),
     'no competency is written as an ordered procedure');
}

/* ---- the reads are real ---------------------------------------------- */
{
  const reads = need(R, 'reads', 'registry');
  let missing = 0;
  for (const p of reads) { try { read(p); } catch { missing++; } }
  ok(missing === 0,
     `all ${reads.length} files this pack says it read are on disk and parse`);
  ok(reads.includes('pack/registry/halls.json')
     && reads.includes('pack/manifest.json'),
     'and they include the hall roster and the manifest the version came from');
}

console.log(`\n${pass} ok, ${fail} failed`);
process.exit(fail ? 1 : 0);
