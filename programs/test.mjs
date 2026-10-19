/* programs/test.mjs - the programs pack (K-12 program pathways, teacher program cards, nonprofit sectors) checked
 * against the registries it is composed from. Browser-free, network-free. Recompute, never re-read: the play-safe rule
 * is re-run from the hive's own hold list, the band fold from the grade ranges, every program order, card greeter
 * and sector list is re-derived here and compared. */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c, why) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m + (why !== undefined ? ' :: ' + JSON.stringify(why).slice(0, 500) : '')); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const reg = J('programs/registry/programs.json');
const SCH = J('schools/registry/schools.json'), CL = J('classroom/registry/classroom.json'), CX = J('cognitionx/registry/cognitionx.json');
const CO = J('courses/registry/courses.json'), LE = J('lessons/registry/lessons.json').lessons, HV = J('hive/registry/hive.json');
const RS = J('respond/registry/respond.json'), PA = J('layers/registry/paths.json'), SM = J('smiles/registry/smiles.json');
const RE = J('restoration/registry/restoration.json'), SC = J('restoration/registry/scenarios.json');

/* ---- provenance ---- */
const canon = (v) => Array.isArray(v) ? '[' + v.map(canon).join(', ') + ']'
  : (v && typeof v === 'object') ? '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ': ' + canon(v[k])).join(', ') + '}'
  : JSON.stringify(v);
{ const body = { ...reg }; delete body.source_stamp;
  ok('source_stamp is the sha256 of the registry body (re-hashed here)', reg.source_stamp === createHash('sha256').update(canon(body)).digest('hex').slice(0, 16)); }
ok(`every source registry is the one the pack was built from (${reg.sources.length} sha256 re-hashed)`,
  reg.sources.length === 11 && reg.sources.every((s) => existsSync(join(ROOT, s.path)) && createHash('sha256').update(readFileSync(join(ROOT, s.path))).digest('hex') === s.sha256),
  reg.sources.filter((s) => !existsSync(join(ROOT, s.path)) || createHash('sha256').update(readFileSync(join(ROOT, s.path))).digest('hex') !== s.sha256).map((s) => s.path));
ok('schema programs/1, pack smartcitix-programs, models 0', reg.schema === 'programs/1' && reg.pack === 'smartcitix-programs' && reg.counts.models === 0);

/* ---- honesty ---- */
const H = reg.honesty;
ok('honesty: districts, programmes and organisations are PROPOSED; no agreement, grant or funding exists',
  /Districts, programmes and organisations named here are PROPOSED/.test(H.proposed) && /no agreement, grant or funding exists/.test(H.proposed));
ok('honesty: the UN path is PROPOSED and not affiliated', /PROPOSED/.test(H.un) && /not affiliated with or endorsed by the United Nations/.test(H.un));
ok('honesty: nothing is accredited; lessons are unverified general practice', /Nothing here is accredited/.test(H.not_accredited) && /unverified general practice/.test(H.not_accredited));
ok('honesty: games, coins and badges are play', /^Games, coins and badges are play/.test(H.play));
ok('honesty quotes are verbatim at their sources (districts, Cognition.X blocks, standards)',
  H.districts.text === SCH.honesty.districts && H.cognitionx.text === CX.honesty.blocks && H.standards.text === CL.honesty.standards);
ok('every district is quoted with its PROPOSED status, none added',
  eq(reg.districts.map((d) => [d.district, d.status]), SCH.districts.map((d) => [d.district, d.status])) && reg.districts.every((d) => /proposed partner/.test(d.status)));
ok('Cognition.X attribution is carried whole for CC BY (author, title, source_url, license_id, license, repo, commit), as the SBOM requires',
  reg.attribution.license === 'CC-BY-4.0' && ['text', 'author', 'title', 'source_url', 'license_id', 'license', 'license_url', 'repo', 'commit'].every((k) => typeof reg.attribution[k] === 'string' && reg.attribution[k] === CX.attribution[k]));

/* ---- the play-safe rule, re-run from the hive's hold list ---- */
const HOLD = new RegExp('\\b(' + HV.k12.hold_words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')\\b', 'i');
const safe = (...t) => !t.some((x) => HOLD.test(String(x)));
const lsafe = (id) => safe(LE[id].title, LE[id].why, LE[id].limits);
ok('the rule names the hive hold list and allow-list, unchanged', eq(reg.rules.hold_words, HV.k12.hold_words) && eq(reg.rules.allow_list, { advisors: HV.k12.advisors, npc_roles: HV.k12.npc_roles }));

/* ---- bands ---- */
const span = (s) => s.split(/[-–]/).map((x) => (x.trim().toUpperCase() === 'K' ? 0 : +x));
ok('four bands, quoted from schools in order (band, level, offer)', eq(reg.bands.map((b) => [b.band, b.level, b.offer]), SCH.bands.map((b) => [b.band, b.level, b.offer])));
ok('every Cognition.X band folds into exactly one schools band by grade range',
  reg.bands.every((b) => { const [lo, hi] = span(b.band); return eq(b.cognitionx_bands, CX.bands.filter((c) => lo <= span(c)[0] && span(c)[1] <= hi)); })
  && eq(reg.bands.flatMap((b) => b.cognitionx_bands).sort(), [...CX.bands].sort()));
const ALLOW = HV.agents.filter((a) => a.k12);
ok(`the agents of every band are exactly the hive classroom allow-list (${ALLOW.length}), advisors first`,
  reg.bands.every((b) => eq(b.agents, [...ALLOW.filter((a) => a.kind === 'advisor'), ...ALLOW.filter((a) => a.kind === 'npc')].map((a) => a.id)))
  && ALLOW.every((a) => (a.kind === 'advisor' && HV.k12.advisors.includes(a.id.split(':')[1])) || (a.kind === 'npc' && HV.k12.npc_roles.includes(a.role))));
ok('each band lists the courses carrying play-safe lessons for it, in courses order, lessons in course order', reg.bands.every((b) => {
  const want = Object.entries(CO.courses).map(([cid, c]) => [cid, c.band_lessons[b.band].filter(lsafe)]).filter(([, l]) => l.length);
  return eq(b.courses.map((c) => [c.course, c.lessons.map((l) => l.id)]), want) && b.courses.every((c) => c.lessons.every((l) => l.title === LE[l.id].title));
}));
ok('every pathway lesson is play-safe and stands in that band (none held is listed)', reg.bands.every((b) => b.courses.every((c) => c.lessons.every((l) => lsafe(l.id) && CO.courses[c.course].band_lessons[b.band].includes(l.id)))));
ok('held lessons are counted, never reworded', reg.bands.every((b) => b.counts.lessons_held === new Set(Object.values(CO.courses).flatMap((c) => c.band_lessons[b.band]).filter((l) => !lsafe(l))).size));
ok('each band lists the classroom modules whose lessons stand in it (classroom order)', reg.bands.every((b) => {
  const inBand = new Set(b.courses.flatMap((c) => c.lessons.map((l) => l.id)));
  return eq(b.modules.map((m) => [m.module, m.lessons.map((l) => l.id)]), CL.modules.map((m) => [m.id, m.lessons.filter((l) => inBand.has(l))]).filter(([, l]) => l.length));
}));
const BL = Object.fromEntries(CX.blocks.map((b) => [b.block_id, b]));
ok('Cognition.X: every listed block is play-safe, in a folded band, in its module order; held blocks counted', reg.bands.every((b) => {
  let held = 0;
  const want = CX.modules.map((m) => { const ids = m.blocks.filter((x) => b.cognitionx_bands.includes(BL[x].band)); const s = ids.filter((x) => safe(BL[x].theme, BL[x].description, BL[x].transfer_check)); held += ids.length - s.length; return [m.id, s]; }).filter(([, s]) => s.length);
  return eq(b.cognitionx.map((x) => [x.cx_module, x.blocks]), want) && held === b.counts.blocks_held
    && b.cognitionx.every((x) => x.first.theme === BL[x.blocks[0]].theme && x.first.transfer_check === BL[x.blocks[0]].transfer_check);
}));
ok('the program is one ordered list: agents, then courses, then modules, then Cognition.X; n runs 1..N', reg.bands.every((b) => {
  const want = [...b.agents.map((r) => ['agent', r]), ...b.courses.map((c) => ['course', c.course]), ...b.modules.map((m) => ['module', m.module]), ...b.cognitionx.map((x) => ['cognitionx', x.cx_module])];
  return eq(b.program.map((s) => [s.kind, s.ref]), want) && b.program.every((s, i) => s.n === i + 1);
}));
ok('band counts equal the lists they count', reg.bands.every((b) => b.counts.steps === b.program.length && b.counts.courses === b.courses.length
  && b.counts.modules === b.modules.length && b.counts.cx_modules === b.cognitionx.length && b.counts.blocks === b.cognitionx.reduce((n, x) => n + x.blocks.length, 0)
  && b.counts.lessons === new Set(b.courses.flatMap((c) => c.lessons.map((l) => l.id))).size && b.counts.cards === reg.cards.filter((c) => c.band === b.band).length));

/* ---- teacher program cards ---- */
const PL = Object.fromEntries(CL.places.map((p) => [p.id, p]));
const BY = Object.fromEntries(HV.agents.map((a) => [a.id, a]));
ok('one card per band and classroom module of that band', eq(reg.cards.map((c) => c.id), reg.bands.flatMap((b) => b.modules.map((m) => `${b.band}/${m.module}`))));
const greeterOf = (places) => {
  const fips = [...new Set(places.filter((p) => PL[p].world === 'parishes' && PL[p].ref.fips).map((p) => PL[p].ref.fips))].sort();
  for (const f of fips) { const g = ALLOW.filter((a) => a.kind === 'npc' && a.role === 'k12-guide' && String(a.where.place || '').startsWith(`st-${f}-`)).map((a) => a.id).sort(); if (g.length) return [g[0], 'parish']; }
  return ['advisor:guide', 'campus'];
};
const MOD = Object.fromEntries(CL.modules.map((m) => [m.id, m]));
ok('every card greeter follows the rule (lowest-FIPS parish k12-guide, else the campus Orientation guide)',
  reg.cards.every((c) => eq([c.greeter.id, c.greeter.at], greeterOf(MOD[c.module].places))), reg.cards.filter((c) => !eq([c.greeter.id, c.greeter.at], greeterOf(MOD[c.module].places))).map((c) => c.id));
ok('every greeter is on the classroom allow-list and its line is a play-safe line quoted verbatim from the hive', reg.cards.every((c) => {
  const a = BY[c.greeter.id]; if (!a || !a.k12) return false;
  const i = +c.greeter.opener.hive_ref.match(/lines\[(\d+)\]$/)[1], ln = a.lines[i];
  return ln && ln.text === c.greeter.opener.text && ln.k12 === true && safe(ln.text) && ln.source === c.greeter.opener.source && ln.kind === c.greeter.opener.kind;
}));
ok('greeter line is the first play-safe one by kind (greeting, then say, then knowledge)', reg.cards.every((c) => {
  const a = BY[c.greeter.id]; for (const k of ['greeting', 'say', 'knowledge']) { const ln = a.lines.find((l) => l.kind === k && l.k12 === true && safe(l.text)); if (ln) return ln.text === c.greeter.opener.text; } return false;
}));
ok('every card says the voice starts muted in classroom mode', reg.cards.every((c) => /starts muted/.test(c.voice)));
const KINDS = Object.fromEntries(reg.bands.map((b) => [b.band, b.kinds]));
ok('what a class does follows the band (K-5 the offer only; stations admit home and drill; sims the floor; the gate only when the offer names it)', reg.cards.every((c) => {
  const k = KINDS[c.band], u = SCH.units.find((x) => x.hall === c.hall), b = SCH.bands.find((x) => x.band === c.band);
  const want = [['offer', b.offer]];
  if (k.includes('station')) want.push(['home', u.home], ['class_drill', u.class_drill]);
  if (k.includes('sim') && u.floor_sims.length) want.push(['floor_sims', u.floor_sims.join(', ')]);
  if (/unaided verification gate/.test(b.offer)) want.push(['gate', u.gate]);
  return eq(c.does.map((d) => [d.what, d.text]), want);
}));
ok('K-5 and 6-8 cards list no simulator seat (no machine seats / no floor time)', reg.cards.filter((c) => !KINDS[c.band].includes('sim')).every((c) => c.where.every((w) => w.kind !== 'seat')));
ok('every card place is a classroom place and its page exists', reg.cards.every((c) => c.where.every((w) => PL[w.id] && PL[w.id].href === w.href && existsSync(join(ROOT, w.href.split('?')[0])))));
ok('every card lesson is play-safe', reg.cards.every((c) => c.lessons.every((l) => lsafe(l.id))));

/* ---- sectors ---- */
const SEC = Object.fromEntries(reg.sectors.map((s) => [s.id, s]));
ok('four sectors: community health, disaster response, humanitarian training, environmental restoration; all PROPOSED',
  eq(reg.sectors.map((s) => s.id), ['community-health', 'disaster-response', 'humanitarian-training', 'environmental-restoration']) && reg.sectors.every((s) => s.status === 'PROPOSED'));
const hc = SEC['community-health'];
ok('community health quotes the Smiles disclaimer: not medical or dental advice', hc.quotes[0].text === SM.disclaimer && /not medical or dental advice/.test(hc.quotes[0].text));
const strs = (v, out = []) => { if (typeof v === 'string') out.push(v); else if (v && typeof v === 'object') Object.values(v).forEach((x) => strs(x, out)); return out; };
const SMILES_OK = new Set([SM.name, SM.place_note, ...SM.programmes.map((p) => p.name)]);
ok('Unspoken Smiles is named only as the existing pages describe it (every mention is a Smiles registry string, verbatim)',
  eq(hc.programmes.map((p) => [p.id, p.name, p.stations]), SM.programmes.map((p) => [p.id, p.name, p.stations])) && hc.quotes[1].text === SM.place_note
  && strs(reg).filter((x) => /Unspoken Smiles/i.test(x)).every((x) => SMILES_OK.has(x)), strs(reg).filter((x) => /Unspoken Smiles/i.test(x) && !SMILES_OK.has(x)));
ok('community health lists the six Smiles games as play scenarios and no hall, course or agent it cannot ground',
  eq(hc.scenarios.map((s) => s.id), Object.keys(SM.games)) && hc.halls.length === 0 && hc.courses.length === 0 && hc.agents.length === 0 && hc.empty_why.courses);
const dr = SEC['disaster-response'];
ok('disaster response: the 25 respond frames, the halls they touch, their trade courses and the responder figures',
  eq(dr.scenarios.map((s) => s.id), RS.scenario_frames.map((f) => f.id)) && eq(dr.halls.map((h) => h.hall), Object.keys(RS.hall_cross_links).sort())
  && dr.halls.length === RS.counts.halls_touched && eq(dr.agents, HV.agents.filter((a) => a.kind === 'npc' && a.role === 'responder').map((a) => a.id).sort())
  && dr.courses.every((c) => c in CO.courses) && eq(dr.courses, dr.halls.map((h) => 'trade.' + h.hall).filter((c) => c in CO.courses)));
const hu = SEC['humanitarian-training'];
const unPath = PA.parishes[0].paths.find((p) => p.id === 'un');
ok('humanitarian training: the UN training path stays PROPOSED and not affiliated (quoted)', hu.paths[0].status === 'PROPOSED' && unPath.status === 'PROPOSED'
  && hu.quotes[0].text === PA.un_disclaimer && /not affiliated/.test(hu.quotes[0].text) && hu.quotes[1].text === PA.honesty.un);
const want = []; for (const par of PA.parishes) for (const p of par.paths) if (p.id === 'un' || p.id === 'relief') for (const s of p.steps) if (s.kind === 'quote' && !want.includes(s.ref_id)) want.push(s.ref_id);
ok('humanitarian training: every item the un / relief paths quote, once; the trainer and relief roles', eq(hu.scenarios.map((s) => s.ref_id), want)
  && eq(hu.agents, [...HV.agents.filter((a) => a.role === unPath.npc_role).map((a) => a.id).sort(), ...HV.agents.filter((a) => a.role === 'relief-coordinator').map((a) => a.id).sort()]) && hu.agents.length > 0);
const er = SEC['environmental-restoration'];
ok('environmental restoration: the 11 sites with their organisations verbatim, the 16 scenarios with their label', eq(er.sites.map((s) => [s.id, s.name, s.org, s.walkable]), RE.sites.map((s) => [s.id, s.name, s.org, s.walkable]))
  && eq(er.scenarios.map((s) => [s.id, s.title, s.label]), SC.scenarios.map((s) => [s.id, s.title, s.label])) && er.quotes[0].text === RE.honesty.not_affiliated);
ok('restoration halls are the sites\' trade needs and the scenario crews, with trade courses', eq(er.halls.map((h) => h.hall), [...new Set([...RE.sites.flatMap((s) => s.trade_needs), ...SC.scenarios.flatMap((s) => s.crew.map((c) => c.trade))])])
  && er.courses.every((c) => c in CO.courses));
ok('every sector agent is a hive agent; every sector course a course; every world page exists', reg.sectors.every((s) => s.agents.every((a) => a in BY) && s.courses.every((c) => c in CO.courses)
  && s.worlds.every((w) => existsSync(join(ROOT, 'web', w.href)))));
const keys = (v, out = []) => { if (Array.isArray(v)) v.forEach((x) => keys(x, out)); else if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) { out.push(k); keys(x, out); } return out; };
const RJ = JSON.stringify(reg);
ok('no funding, grant, price or accreditation field, and the restoration funding context is not carried (never invented, not restated)',
  !keys(reg).filter((k) => k !== 'not_accredited').some((k) => /fund|grant|price|budget|accredit|partner_since|agreement/i.test(k)) && !RJ.includes(SC.funding_context.headline)
  && !strs(SC.funding_context).filter((x) => x.length > 30).some((x) => RJ.includes(x)), keys(reg).filter((k) => /fund|grant|price|budget|accredit/i.test(k)));
ok('pack counts equal the lists they count', reg.counts.cards === reg.cards.length && reg.counts.sectors === reg.sectors.length && reg.counts.allow_list_agents === ALLOW.length
  && reg.counts.blocks === CX.blocks.length && reg.counts.greeters === new Set(reg.cards.map((c) => c.greeter.id)).size);

console.log(`  (measured) ${reg.cards.length} cards (${Object.entries(reg.counts.cards_by_band).map(([b, n]) => b + ' ' + n).join(', ')}); lessons ${Object.entries(reg.counts.lessons_by_band).map(([b, n]) => b + ' ' + n).join(', ')}; blocks ${Object.entries(reg.counts.blocks_by_band).map(([b, n]) => b + ' ' + n).join(', ')}; ${ALLOW.length} allow-listed agents; ${reg.counts.greeters} greeters; sectors ${reg.sectors.map((s) => s.id + ' ' + s.courses.length + 'c/' + s.agents.length + 'a').join(', ')}`);
console.log(`programs/test: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
