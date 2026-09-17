#!/usr/bin/env node
/**
 * Figures lint: every surface must state the same numbers as the pack.
 *
 * This exists because the surfaces DID disagree and nothing noticed. The
 * Academy app said 111 halls and 500,000 modules; the landing page, spec and
 * registry said 33 and 333,333. Both were internally consistent, both were
 * published, and the only reason it surfaced is that someone read them side by
 * side.
 *
 * A number a reader can check is a claim, and claims need a checker — the same
 * argument as the brand lint, applied to figures instead of spelling. The
 * canonical values come from the pack manifest, which is itself verified
 * against the generated ID space, so this cannot drift from the truth without
 * the pack failing first.
 *
 *   node brand/figures.mjs [paths...]
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, extname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const manifest = JSON.parse(readFileSync(join(ROOT, 'pack/manifest.json'), 'utf8'));
const L = manifest.ledger;
// The counts that drifted in prose while the halls figure was policed: the
// campus network ("five-campus"), the hub count ("two hub campuses"), the
// simulator roster ("seven simulators") and the halls a seat is bound to
// ("40 real halls"). Each is read from the registry that owns it.
const campuses = JSON.parse(readFileSync(join(ROOT, 'unions/registry/campuses.json'), 'utf8'));
const simsReg = JSON.parse(readFileSync(join(ROOT, 'sims/registry/sims.json'), 'utf8'));
const N_CAMPUSES = campuses.count;
const N_HUBS = Object.values(campuses.campuses).filter((c) => !c.districts.length).length;
const N_SIMS = Object.keys(simsReg.sims).length;
const N_BOUND = Object.keys(simsReg.hall_bindings).length;
// Added after the wiki's Home page said "on one campus" and "three planned
// locations" a few lines above its own ten-row campus table, README said the
// avatar locker held "284 options" (the registry sums to 289 standard + 111
// crew = 400) and "district records for the three district-campus regions"
// (the registry holds four records across those three regions). Each of
// these is now a tracked figure read from the registry that owns it.
const avatarsReg = JSON.parse(readFileSync(join(ROOT, 'avatars/registry/avatars.json'), 'utf8'));
const schoolsReg = JSON.parse(readFileSync(join(ROOT, 'schools/registry/schools.json'), 'utf8'));
const AV_STD = avatarsReg.sections.filter((s) => s.kind !== 'crew');
const AV_CREW = avatarsReg.sections.find((s) => s.kind === 'crew');
const N_AV_STD_SECTIONS = AV_STD.length;
const N_AV_SECTIONS = avatarsReg.sections.length;
const N_AV_STD_OPTIONS = AV_STD.reduce((n, s) => n + s.options.length, 0);
const N_AV_CREW_LOOKS = AV_CREW.options.length;
const N_AV_OPTIONS = N_AV_STD_OPTIONS + N_AV_CREW_LOOKS;
const N_SCHOOL_DISTRICTS = schoolsReg.districts.length;
const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
  'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
  'seventeen', 'eighteen', 'nineteen', 'twenty'];
// every spelling of a count but the current one - words and digits alike
const notN = (n) => [...WORDS, ...Array.from({ length: 60 }, (_, i) => String(i + 1))]
  .filter((x) => x !== WORDS[n] && x !== String(n)).join('|');

const F = (n) => n.toLocaleString('en-US');

/**
 * Figures that are wrong ANYWHERE, with the value that replaces them. These
 * are superseded scales, not arbitrary numbers: a page may legitimately say
 * "33 lessons in this level", so only the specific claims are policed.
 */
const RULES = [
  { wrong: /\b333,333\b/g, right: F(L.total_modules),
    why: 'the 33-hall module total; the pack now closes at ' + F(L.total_modules) },
  { wrong: /\b500,000 modules\b/g, right: F(L.total_modules) + ' modules',
    why: 'the figure the Academy app carried, which matched no pack' },
  { wrong: /\b35,937\b/g, right: F(L.core_lessons),
    why: 'the 33-hall lesson count' },
  { wrong: /\b36,237\b/g, right: F(manifest.authored_objects),
    why: 'the 33-hall authored-object count' },
  { wrong: /\b33 (?:trade )?unions?\b/g, right: `${L.halls} trade unions`,
    why: `the network is ${L.halls} halls` },
  { wrong: /\b33 union halls\b/g, right: `${L.halls} union halls`,
    why: `the network is ${L.halls} halls` },
  // Added after "the 33 halls are grouped" survived in the map footer: the
  // rules above policed "33 unions" and "33 union halls" but not the bare
  // "33 halls". A lint's coverage is only the phrasings someone thought of,
  // so a miss is a rule to add, not a reason to trust the pass.
  { wrong: /\b33 halls\b/g, right: `${L.halls} halls`,
    why: `the network is ${L.halls} halls` },
  // Added after "The five-campus network" survived on the landing page
  // through five hub-campus merges: the campus count was never a rule.
  { wrong: new RegExp(`\\b(?:${notN(N_CAMPUSES)})-campus network\\b`, 'gi'),
    right: `${WORDS[N_CAMPUSES]}-campus network`,
    why: `the network is ${N_CAMPUSES} campuses (unions/registry/campuses.json)` },
  { wrong: new RegExp(`(?<!\\bno )\\b(?:${notN(N_HUBS)}) hub campuses\\b`, 'gi'),
    right: `${WORDS[N_HUBS]} hub campuses`,
    why: `${N_HUBS} campuses are hubs - no home district (unions/registry/campuses.json)` },
  { wrong: new RegExp(`\\b(?:${notN(N_SIMS)}) (?:simulators|operable (?:training )?seats)\\b`, 'gi'),
    right: `${WORDS[N_SIMS]} simulators`,
    why: `the roster is ${N_SIMS} simulators (sims/registry/sims.json)` },
  { wrong: new RegExp(`\\b(?:${notN(N_BOUND)}) real halls\\b`, 'gi'),
    right: `${N_BOUND} real halls`,
    why: `the seats bind ${N_BOUND} halls (sims/registry/sims.json hall_bindings)` },
  // The single-campus era's phrasings. "on one campus" survived a line break
  // ("on one\ncampus"), so the rule tolerates whitespace.
  { wrong: /\bon one\s+campus\b/gi, right: `across ${N_CAMPUSES} campuses`,
    why: `the network is ${N_CAMPUSES} campuses (unions/registry/campuses.json)` },
  { wrong: new RegExp(`\\b(?:${notN(N_CAMPUSES)}) (?:planned )?locations\\b`, 'gi'),
    right: `${N_CAMPUSES} planned locations`,
    why: `the network is ${N_CAMPUSES} planned locations (unions/registry/campuses.json)` },
  // The avatar locker: standard sections, the crew section and the options
  // they hold. Any three-digit "N options" that is not the standard total,
  // the crew total or the grand total is a stale locker figure.
  { wrong: new RegExp(`\\b(?:${notN(N_AV_STD_SECTIONS)}) standard sections\\b`, 'gi'),
    right: `${N_AV_STD_SECTIONS} standard sections`,
    why: `the locker has ${N_AV_STD_SECTIONS} standard sections + 1 crew section = ${N_AV_SECTIONS} (avatars/registry/avatars.json)` },
  { wrong: new RegExp(`\\b(?:${notN(N_AV_SECTIONS)}) locker sections\\b`, 'gi'),
    right: `${N_AV_SECTIONS} locker sections`,
    why: `the locker has ${N_AV_SECTIONS} sections in all (avatars/registry/avatars.json)` },
  { wrong: new RegExp(`\\b(?!(?:${N_AV_STD_OPTIONS}|${N_AV_CREW_LOOKS}|${N_AV_OPTIONS})\\b)\\d{3} options\\b`, 'g'),
    right: `${N_AV_STD_OPTIONS} options (standard) / ${N_AV_OPTIONS} options (with the ${N_AV_CREW_LOOKS}-look crew section)`,
    why: `the locker holds ${N_AV_STD_OPTIONS} standard options + ${N_AV_CREW_LOOKS} crew looks = ${N_AV_OPTIONS} (avatars/registry/avatars.json)` },
  // The schools pack's proposed-district records: four records across the
  // three district-campus regions, and the count is the records, not the regions.
  { wrong: new RegExp(`\\b(?:${notN(N_SCHOOL_DISTRICTS)}) proposed (?:school[- ])?districts?\\b`, 'gi'),
    right: `${N_SCHOOL_DISTRICTS} proposed districts`,
    why: `the registry holds ${N_SCHOOL_DISTRICTS} proposed-district records (schools/registry/schools.json)` },
];

/**
 * One bundle version. Every registry that declares a pack_version must
 * declare the manifest's: five packs had drifted to 3.3.0 - 3.5.0 (and two
 * to 1.0.0) while ROADMAP said the version was unified across every surface.
 * The registries are skipped by the text walk below, so they are read here.
 */
function registryVersionHits() {
  const out = [];
  for (const d of readdirSync(ROOT, { withFileTypes: true })) {
    if (!d.isDirectory() || SKIP.has(d.name) && d.name !== 'pack') continue;
    const reg = join(ROOT, d.name, 'registry');
    let files; try { files = readdirSync(reg); } catch { continue; }
    for (const f of files) {
      if (extname(f) !== '.json') continue;
      let doc; try { doc = JSON.parse(readFileSync(join(reg, f), 'utf8')); } catch { continue; }
      if (!doc || typeof doc !== 'object' || !('pack_version' in doc)) continue;
      if (doc.pack_version !== manifest.pack_version) {
        out.push({ file: `${d.name}/registry/${f}`, n: 1,
          wrong: { source: `pack_version ${doc.pack_version}` }, right: manifest.pack_version,
          why: `one bundle version: pack/manifest.json says ${manifest.pack_version}; the build should read it, not type its own` });
      }
    }
  }
  return out;
}

const EXT = new Set(['.md', '.html', '.mjs', '.js', '.py', '.json', '.txt', '.sh']);
// `archive/` holds superseded working files kept for provenance; `pack/` is
// the frozen 33-hall pack, which correctly states its own figures.
const SKIP = new Set(['node_modules', '.git', 'dist', '__pycache__', 'registry',
                      'ledger', 'pack', 'archive']);
const SELF = new Set(['brand/figures.mjs']);

function* walk(dir) {
  let e; try { e = readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const x of e) {
    if (SKIP.has(x.name)) continue;
    const p = join(dir, x.name);
    if (x.isDirectory()) yield* walk(p);
    else if (EXT.has(extname(x.name))) yield p;
  }
}

const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const files = [];
for (const t of (args.length ? args : [ROOT])) {
  const st = statSync(t);
  if (st.isDirectory()) files.push(...walk(t)); else files.push(t);
}

const hits = registryVersionHits();
for (const f of files) {
  const rel = relative(ROOT, f) || f;
  if (SELF.has(rel)) continue;
  let text; try { text = readFileSync(f, 'utf8'); } catch { continue; }
  // Same exemption as the brand lint: a quoted literal or fenced block may
  // cite a superseded figure, because the migration notes have to name it.
  const scan = text
    .replace(/```[\s\S]*?```/g, (m) => ' '.repeat(m.length))
    .replace(/`[^`\n]*`/g, (m) => ' '.repeat(m.length))
    .replace(/<code\b[^>]*>[\s\S]*?<\/code>/gi, (m) => ' '.repeat(m.length));
  for (const r of RULES) {
    const found = scan.match(r.wrong);
    if (found) hits.push({ file: rel, n: found.length, ...r });
  }
}

if (!hits.length) {
  console.log(`figures: ${files.length} files agree with the pack — `
    + `${L.halls} halls, ${F(L.total_modules)} modules, ${N_CAMPUSES} campuses, `
    + `${N_AV_OPTIONS} avatar options, ${N_SCHOOL_DISTRICTS} proposed districts, `
    + `every registry at pack ${manifest.pack_version}`);
  process.exit(0);
}
console.error(`figures: ${hits.length} stale figure${hits.length === 1 ? '' : 's'}\n`);
for (const h of hits) {
  console.error(`  ${h.file}`);
  console.error(`    ${h.wrong.source} x${h.n} -> ${h.right}`);
  console.error(`    ${h.why}\n`);
}
console.error('surfaces must state the pack\'s figures; cite a superseded one in backticks.');
process.exit(1);
