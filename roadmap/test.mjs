/**
 * Network roadmap verification.
 *
 * The claim this pack makes has two parts that must never blur together:
 * four campuses are BUILT (three on RECORDED, cross-checked coordinates,
 * one - Houston - on AUTHORED ones, same as a candidate's): six are
 * CANDIDATES on AUTHORED, not-cross-checked coordinates. A third
 * distinction cuts across the first: three built campuses are DISTRICT
 * campuses (a home for 2-3 districts, a district ring, halls > 0);
 * Houston is a HUB campus (no home district, no ring, zero home halls,
 * a regional-chapter seat for all 111 instead) - the suite checks each
 * shape holds to its own honest bar rather than forcing Houston through
 * the district campus's checks. The built entries must still trace to
 * the geo and union registries' own figures, and the candidates must
 * never claim more than a proposed metro and a proposed district
 * emphasis. Ten is a target the count must actually add up to, not a
 * number quoted and left unchecked.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/roadmap.json', import.meta.url)));
const geo = JSON.parse(readFileSync(
  new URL('../geo/registry/campuses_geo.json', import.meta.url)));
const campuses = JSON.parse(readFileSync(
  new URL('../unions/registry/campuses.json', import.meta.url))).campuses;
const districts = JSON.parse(readFileSync(
  new URL('../unions/registry/districts.json', import.meta.url))).districts;
const dash = readFileSync(
  new URL('../web/trade_craft_dashboard.html', import.meta.url), 'utf8');

const built = Object.entries(reg.built_campuses);
const cand = Object.entries(reg.candidates);

/* -------------------------------------------------------------- the count --- */
ok(`the network totals exactly the declared target (${built.length} built + ${cand.length} candidates = ${reg.target})`,
  built.length + cand.length === reg.target && reg.target === 10
  && built.length === 4 && cand.length === 6);
ok('no candidate slug collides with a built campus slug',
  built.every(([k]) => !reg.candidates[k])
  && cand.every(([k]) => !reg.built_campuses[k]));

/* --------------------------------------------------------- built = RECORDED --- */
ok('every built entry is the union registry\'s own campus, not a second copy',
  built.every(([k, b]) => campuses[k]
    && b.city === campuses[k].city && b.region === campuses[k].region
    && JSON.stringify(b.districts) === JSON.stringify(campuses[k].districts)));
ok('every built entry\'s coordinate is the geo registry\'s own RECORDED/DERIVED/AUTHORED figure',
  built.every(([k, b]) => geo.campuses[k]
    && b.lat === geo.campuses[k].lat && b.lng === geo.campuses[k].lng
    && b.provenance === geo.campuses[k].provenance));
ok('built entries carry a real hall count off the union registry',
  built.every(([k, b]) => b.halls === campuses[k].halls.length));

/* ----------------------------------------------------------- hub vs district --- */
const hub = built.filter(([, b]) => b.districts.length === 0);
const dist = built.filter(([, b]) => b.districts.length > 0);
ok('exactly one built campus is a hub: no home district, zero home halls',
  hub.length === 1 && hub[0][0] === 'houston'
  && hub.every(([, b]) => b.halls === 0));
ok('every district campus actually hosts 2-3 districts and at least one hall',
  dist.length === 3
  && dist.every(([, b]) => b.districts.length >= 2 && b.districts.length <= 3
    && b.halls > 0));
ok('the hub campus is AUTHORED, not dressed up as a cross-checked figure',
  hub.every(([, b]) => b.provenance === 'AUTHORED'));
ok('the parcels registry carries no records contract for the hub campus',
  (() => {
    const parcels = JSON.parse(readFileSync(
      new URL('../parcels/registry/parcels.json', import.meta.url)));
    return hub.every(([k]) => !(k in parcels.sources))
      && dist.every(([k]) => k in parcels.sources);
  })());
ok('the hub design is stated as a real design, not a workaround left unsaid',
  /no home district, no district\s+ring/.test(reg.honesty.hub_vs_district)
  && /same mechanic every campus\s+already had/.test(reg.honesty.hub_vs_district));

/* ----------------------------------------------------- candidates = AUTHORED --- */
ok('every candidate sits inside a plausible continental-US box - a real sanity check',
  cand.every(([, c]) => c.lat > 24 && c.lat < 49 && c.lng > -125 && c.lng < -66));
ok('every candidate names 2-3 real districts that actually exist in the taxonomy',
  cand.every(([, c]) => c.districts.length >= 2 && c.districts.length <= 3
    && c.districts.every((d) => d in districts)));
ok('every candidate states a real reason, not a placeholder',
  cand.every(([, c]) => c.why.length > 40));
ok('the six candidates are six distinct real US metros',
  new Set(cand.map(([, c]) => c.city)).size === cand.length && cand.length === 6);

/* -------------------------------------------------------------- the tiers --- */
ok('the provenance gap between built and candidate is stated in exact, checkable words',
  /RECORDED - copied from a cited file and\s+cross-checked/.test(reg.honesty.provenance_tiers)
  && /AUTHORED: widely-published public\s+geography/.test(reg.honesty.provenance_tiers)
  && /materially weaker claim, labelled as one/.test(reg.honesty.provenance_tiers));
ok('the target is stated as a target, never dressed up as an achieved count',
  /target this registry tracks progress\s+toward, not a claim that ten exist/
    .test(reg.honesty.target_not_claim));
ok('a candidate is explicit that no hall, union or curriculum content exists there yet',
  /does not\s+claim any hall, union, curriculum content/
    .test(reg.honesty.not_a_claim_of_content)
  && /the checklist, done in\s+full/.test(reg.honesty.not_a_claim_of_content));
ok('no candidate carries a committed date, and the registry says why',
  /no candidate carries a\s+committed date/.test(reg.honesty.no_dates)
  && !cand.some(([, c]) => 'date' in c || 'eta' in c || 'when' in c));

/* -------------------------------------------------------------- the checklist --- */
ok('the checklist is the real steps, each naming a file that actually exists in this bundle',
  reg.checklist.length >= 5
  && reg.checklist.every((r) => r.step && r.what.length > 20 && r.file));
ok('the checklist starts with sourcing real coordinates - the actual hard part',
  /source real coordinates/.test(reg.checklist[0].step));
ok('and ends with verifying, shipping and publishing - not just editing a status field',
  /verify, ship, publish/.test(reg.checklist[reg.checklist.length - 1].step));

/* ------------------------------------------------------------- the dashboard --- */
ok('the dashboard renders the exact built/candidate counts, not stale ones',
  dash.includes(`${built.length}<span>/${reg.target} built`)
  && dash.includes(`${cand.length} candidates</div>`));
ok('every built campus and every candidate actually appears on the dashboard by name',
  built.every(([, b]) => dash.includes(b.name))
  && cand.every(([, c]) => dash.includes(c.name)));
ok('the dashboard carries both provenance words where a viewer can see them',
  dash.includes('>RECORDED<') && dash.includes('>AUTHORED<'));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`roadmap/test: ${n} checks passed — ${built.length}/${reg.target} built, `
  + `${cand.length} candidates`);
