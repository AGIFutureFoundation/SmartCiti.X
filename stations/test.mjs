/**
 * Station registry verification.
 *
 * The stations are recovered content rebranded onto the live structure, so
 * every claim the registry makes about that structure — the hall exists,
 * the skill exists, the room is real — is checked against the packs that
 * own those truths. Content checks (exactly one correct quiz answer, no
 * empty checklists) make each station machine-gradable by construction.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/stations.json', import.meta.url)));
const unions = JSON.parse(readFileSync(new URL('../unions/registry/unions.json', import.meta.url)));
const skills = JSON.parse(readFileSync(new URL('../pack/registry/skills.json', import.meta.url))).skills;
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

/* -------------------------------------------------------------- honesty --- */
ok('the registry declares the content unverified pending practitioner review',
  /unverified/.test(reg.honesty.content) && /review/.test(reg.honesty.content));
const src = readFileSync(new URL('../archive/bac_yard_stations.json', import.meta.url));
ok('the registry was built from the current archive source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`stations/test: ${n} checks passed — ${reg.count} stations, ${reg.halls_seeded.length} halls seeded`);
