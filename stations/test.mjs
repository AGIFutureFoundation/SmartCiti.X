/**
 * Station registry verification.
 *
 * The stations are recovered content rebranded onto the live structure, so
 * every claim the registry makes about that structure — the hall exists,
 * the skill exists, the room is real — is checked against the packs that
 * own those truths. Content checks (exactly one correct quiz answer, no
 * empty checklists) make each station machine-gradable by construction.
 *
 * Round two adds the checks content DEPTH needs: a checklist line has to be
 * an instruction rather than a label, no two stations may share a line,
 * every quiz has to say why its answer is right, the authored overlay has
 * to be labelled authored and stamped, and what a room requires of the
 * person in it has to be the surfaces record's fact rather than a second
 * copy kept here - which it was, and the copy was wrong.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/stations.json', import.meta.url)));
const unions = JSON.parse(readFileSync(new URL('../unions/registry/unions.json', import.meta.url)));
const skills = JSON.parse(readFileSync(new URL('../pack/registry/skills.json', import.meta.url))).skills;
const finishes = JSON.parse(readFileSync(new URL('../surfaces/registry/finishes.json', import.meta.url)));
const labels = JSON.parse(readFileSync(new URL('../labels/registry/labels.json', import.meta.url)));
const bySlug = new Map(unions.unions.map((u) => [u.slug, u]));
const skillIds = new Set(skills.map((s) => s.skill_id));

ok('all 25 recovered stations are present', reg.count === 25 && reg.stations.length === 25);
ok('station ids are unique and well-formed',
  new Set(reg.stations.map((s) => s.station_id)).size === 25
  && reg.stations.every((s) => /^st\d{3}$/.test(s.station_id)));

/* -------------------------------------------- agreement with the packs --- */
ok('every station\'s hall exists in the union roster',
  reg.stations.every((s) => bySlug.has(s.hall)));
ok('every station\'s district is its hall\'s district — no second opinion',
  reg.stations.every((s) => bySlug.get(s.hall).district === s.district));
ok('every station\'s skill_id exists in the skill graph, and matches its own hall/strand/tier',
  reg.stations.every((s) => skillIds.has(s.skill_id)
    && s.skill_id === `${s.hall}.${s.strand}.${s.tier}`));
ok('the halls_seeded list is exactly the set of halls used',
  JSON.stringify(reg.halls_seeded)
  === JSON.stringify([...new Set(reg.stations.map((s) => s.hall))].sort()));
ok('the masonry flagship carries the plurality of stations',
  reg.stations.filter((s) => s.hall === 'bricklayers').length >= 9);

/* ----------------------------------------------- the space assignment ---- */
const ROOM_OF = {
  safety: 'Induction & PPE', procedure: 'Practice Bays', machines: 'Equipment Bay',
  tools: 'Tool Crib', materials: 'Materials Store', layout: 'Layout Floor',
  inspection: 'Inspection Bench', troubleshooting: 'Diagnostic Bench',
  coordination: 'Briefing Room', documentation: 'Records', leadership: 'Classroom',
};
ok('every station sits in the room its strand owns on the hall floor plan',
  reg.stations.every((s) => ROOM_OF[s.strand] === s.room));

/* -------------------------------------------------- gradable content ----- */
ok('every quiz has exactly one correct option among at least three',
  reg.stations.every((s) => s.quiz.options.length >= 3
    && s.quiz.options.filter((o) => o.correct).length === 1));
ok('every station carries a full checklist and four interactive actions',
  reg.stations.every((s) => s.checklist.length >= 5 && s.actions.length === 4
    && s.actions.every((a) => a.label && a.prop)));
ok('every station carries a lesson line and a doctrine line',
  reg.stations.every((s) => s.lesson?.trim() && s.doctrine?.trim()));

/* --------------------------------------------- depth, and where it came from --- */
/* The content was recovered; some of it was thin. What this section checks
   is that the deepening is real (a line that would change what a learner
   does), that it is labelled as authored rather than passed off as
   recovered, and that deepening is nowhere confused with verifying. */
ok('every station declares per-field provenance in the bundle\'s own words, and the authored counts are the stations\' own',
  reg.stations.every((s) => ['lesson', 'doctrine', 'checklist', 'quiz', 'quiz_why',
    'room_ppe', 'room_hazards', 'actions', 'assignment']
    .every((f) => ['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED']
      .includes(s.provenance[f])))
  && ['lesson', 'doctrine', 'checklist', 'quiz'].every((f) =>
    reg.authored[f] === reg.stations.filter((s) => s.provenance[f] === 'AUTHORED').length));
ok('every checklist item is an instruction rather than a label - the "Rinse thoroughly" bar',
  reg.stations.every((s) => s.checklist.length >= 5
    && s.checklist.every((c) => c.split(/\s+/).length >= 5)));
ok('no lesson, doctrine or checklist line is shared between two stations',
  new Set(reg.stations.map((s) => s.lesson)).size === reg.count
  && new Set(reg.stations.map((s) => s.doctrine)).size === reg.count
  && new Set(reg.stations.flatMap((s) => s.checklist)).size
    === reg.stations.reduce((n, s) => n + s.checklist.length, 0));
ok('every quiz says why the right answer is right, and it is a reason rather than the option read back',
  reg.stations.every((s) => s.quiz.why && s.quiz.why.split(/\s+/).length >= 12
    && s.quiz.why.trim().toLowerCase()
      !== s.quiz.options.find((o) => o.correct).label.trim().toLowerCase()));
ok('the registry says deepening is not verifying: authored and recovered alike are unverified',
  /Recovered and authored alike/.test(reg.honesty.content)
  && /unverified general practice/.test(reg.honesty.content)
  && /Deepening content does not\s+verify it/.test(reg.honesty.depth)
  && /nothing in this pack is a practitioner's\s+sign-off/.test(reg.honesty.depth));

/* ------------------------------------- one truth per fact, across packs --- */
/* A station stands in a room whose door already states what it requires.
   The station reads that record; it does not keep a copy. st000's recovered
   checklist kept one and it disagreed with the door. */
ok('what the room requires is the surfaces record\'s own, read and not restated',
  reg.stations.every((s) => {
    const c = finishes.halls[s.hall].conditions[s.strand];
    return JSON.stringify(c.ppe) === JSON.stringify(s.room_ppe)
      && JSON.stringify(c.hazards) === JSON.stringify(s.room_hazards);
  }));
ok('and no checklist line retypes an item its own room record already carries',
  reg.stations.every((s) => s.checklist.every((item) => s.room_ppe.every(
    (ppe) => !new RegExp(`(?<![a-z])${ppe.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![a-z])`)
      .test(item.toLowerCase())))));
ok('the pack names the label kinds its content is printed on, and the signage pack still declares every one of them',
  Object.keys(reg.signage.kinds).length >= 3
  && Object.keys(reg.signage.kinds).every((k) => k in labels.kinds)
  && labels.kinds.placard.provenance === 'DERIVED'
  && /cannot state different things/.test(reg.signage.note));

/* No station claims an authority it does not have. The list of marks is the
   labels pack's published one - read here, not re-typed - and the matcher
   is written independently of the builder's. */
const marks = (text) => {
  const low = ` ${String(text).toLowerCase().replace(/\s+/g, ' ')} `;
  const hits = labels.no_marks.tokens.filter((t) => new RegExp(
    `(?<![a-z0-9])${t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![a-z0-9])`).test(low));
  for (const pat of labels.no_marks.patterns) hits.push(...(low.match(new RegExp(pat, 'g')) ?? []));
  return hits;
};
ok('no station cites a jurisdiction, a standard, a standards body or a trade organisation',
  reg.stations.every((s) => !marks([s.lesson, s.doctrine, ...s.checklist,
    s.quiz.question, s.quiz.why, ...s.quiz.options.map((o) => o.label)].join(' ')).length));
ok('the marks list is the signage pack\'s, so the words on a placard and the words on a checklist are policed once',
  labels.no_marks.tokens.length > 20 && /read and not copied/.test(reg.honesty.marks));

/* -------------------------------------------------------------- honesty --- */
ok('the registry declares the content unverified pending practitioner review',
  /unverified/.test(reg.honesty.content) && /review/.test(reg.honesty.content));
const src = readFileSync(new URL('../archive/bac_yard_stations.json', import.meta.url));
ok('the registry was built from the current archive source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));
const builder = readFileSync(new URL('./build.py', import.meta.url));
ok('and from the current authored overlay (second stamp: the overlay is a source too)',
  reg.authored_stamp === createHash('sha256').update(builder).digest('hex').slice(0, 16));

console.log(`stations/test: ${n} checks passed — ${reg.count} stations, ${reg.halls_seeded.length} halls seeded`);
