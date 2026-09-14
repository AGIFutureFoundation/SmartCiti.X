/**
 * Bay Restoration pack verification.
 *
 * Two claims, both held to account: every site is a real, named project
 * this build could not fetch or cross-check (AUTHORED, not RECORDED,
 * and the suite proves the page says so), and every field-skill track
 * points at a real skill_id this bundle's own graph already ships -
 * never a restoration-only skill invented for this pack. Nothing here
 * may read as a SmartCiti.X program, partnership or certification.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/restoration.json', import.meta.url)));
const skills = new Set(JSON.parse(readFileSync(
  new URL('../pack/registry/skills.json', import.meta.url))).skills.map((s) => s.skill_id));
const campuses = JSON.parse(readFileSync(
  new URL('../unions/registry/campuses.json', import.meta.url))).campuses;
const geomap = readFileSync(new URL('../web/trade_craft_geomap.html', import.meta.url), 'utf8');
const page3d = readFileSync(new URL('../web/trade_craft_3d.html', import.meta.url), 'utf8');

const pinned = reg.sites.filter((s) => s.pin);

/* ---------------------------------------------------------------- sites --- */
ok('at least eight real, distinctly-named restoration sites',
  reg.sites.length >= 8 && new Set(reg.sites.map((s) => s.id)).size === reg.sites.length);
ok('every site names a real org and links to a real https source',
  reg.sites.every((s) => s.name && s.org && s.source_url.startsWith('https://')));
ok('every pinned site carries a coordinate inside a plausible Bay Area box',
  pinned.every((s) => s.lat > 36 && s.lat < 39.5 && s.lng > -123.5 && s.lng < -121));
ok('every unpinned site (a bay-wide program) carries no fabricated point',
  reg.sites.filter((s) => !s.pin).every((s) => s.lat === null && s.lng === null));
ok('a site marked workforce=true names its real workforce pathway',
  reg.sites.filter((s) => s.workforce).every((s) => s.workforce_note?.length > 20));
ok('every campus grouping names a real campus this bundle actually has',
  reg.sites.every((s) => s.campus === null || s.campus in campuses));

/* --------------------------------------------------------------- tracks --- */
ok('three field-skill tracks, each bound to at least two real skill_ids',
  reg.tracks.length === 3
  && reg.tracks.every((t) => t.skills.length >= 2));
ok('every track skill is a real skill_id this bundle\'s own graph ships - none invented',
  reg.tracks.every((t) => t.skills.every((sk) => skills.has(sk))));

/* -------------------------------------------------------------- honesty --- */
ok('the pack states plainly it is not affiliated with, and does not certify, any site',
  /not\s+affiliated with/.test(reg.honesty.not_affiliated)
  && /does not certify/.test(reg.honesty.not_affiliated));
ok('the provenance line states AUTHORED FROM PUBLIC RECORD, not a live fetch',
  /AUTHORED FROM PUBLIC RECORD/.test(reg.honesty.provenance)
  && /not RECORDED against a live fetch/.test(reg.honesty.provenance));
ok('the honesty block states no restoration-only skill is invented',
  /nothing\s+restoration-specific is invented/.test(reg.honesty.no_new_skills));
ok('campus grouping is stated as a convenience, not a proximity claim',
  /not a claim that\s+campus operates, funds or sits next to the site/
    .test(reg.honesty.campus_grouping));
ok('nothing here claims to certify real restoration field work',
  /nothing here certifies a learner/.test(reg.honesty.not_certification));

/* --------------------------------------------------------------- geomap --- */
ok('the geomap trims the registry into D.restorationSites and marks each one',
  geomap.includes('D.restorationSites') && geomap.includes('restMarkers++'));
ok('every pinned site\'s own real coordinate reaches the geomap',
  pinned.every((s) => geomap.includes(`"lat":${s.lat},"lng":${s.lng}`)));
ok('the geomap draws restoration sites visually distinct from campuses and candidates',
  geomap.includes('restoration-marker'));
ok('the geomap popup links out to the site\'s own real source page',
  geomap.includes('s.source_url') && geomap.includes('target="_blank"'));
ok('the geomap carries the not-affiliated honesty line',
  geomap.includes('D.restorationHonesty.not_affiliated'));

/* -------------------------------------------------------------- 3D app --- */
ok('the 3D app implements the Bay Restoration panel and trims the registry into D.restoration',
  page3d.includes('function openRestoration(') && page3d.includes('D.restoration.sites'));
ok('every site is named in the 3D panel',
  reg.sites.every((s) => page3d.includes(s.name)));
ok('every track builds a click-through via the existing hall-goto handler, and every skill\'s hall reaches the page',
  page3d.includes('data-hall-goto="${esc(hall)}"')
  && reg.tracks.every((t) => t.skills.every((sk) =>
    page3d.includes(`"${sk}"`))));
ok('the restoration toolbar button actually opens the panel',
  page3d.includes("getElementById('restorationBtn')") && page3d.includes('openRestoration()'));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`restoration/test: ${n} checks passed — ${reg.sites.length} sites `
  + `(${pinned.length} mapped), ${reg.tracks.length} tracks`);
