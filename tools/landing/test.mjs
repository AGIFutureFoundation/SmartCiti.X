// tools/landing/test.mjs - the landing tooling cannot drift from the repository.
// rebuild_all.sh must run every builder that exists (or the builder is on the
// reasoned skip list below), the scripts must run anywhere (no machine-local
// path), be executable, and behave as documented. Prints `  ok <name>` per check;
// FAIL <name> at column 0 and a non-zero exit on failure.
import { readFileSync, readdirSync, statSync, existsSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..');
let fails = 0, oks = 0;
const ok = (m) => { oks++; console.log('  ok ' + m); };
const check = (cond, m) => { if (cond) ok(m); else { fails++; console.log('FAIL ' + m); } };
const text = (p) => readFileSync(join(ROOT, p), 'utf8');

const SCRIPTS = ['tools/landing/rebuild_all.sh', 'tools/landing/browser_round.sh', 'tools/landing/browser_runs.sh', 'tools/landing/readme_fix.py'];
const REBUILD = text('tools/landing/rebuild_all.sh');

// Builders that are deliberately NOT lines of rebuild_all.sh, each with the reason. A builder
// that is on this list and also in the script, or a path that is not a builder, fails.
const SKIP = {
  'assets/overview/build_overview.py': 'cuts a promotional overview from frames captured from the running app (assets/overview/shots.mjs); a media job, not part of the build the registries depend on',
  'console/build_slice.py': 'writes console/app_slice.json, a committed input that console/build_app.py reads; console/check_console.py holds the two to one contract, and the data rebuilds do not change it',
  'parishes/build_world.py': 'the parish world layer, imported and run by parishes/build.py itself (its main() is called there), so the script runs it through that builder',
};

// ---- what exists ----
const walk = (rel, depth, out = []) => {
  for (const e of readdirSync(join(ROOT, rel), { withFileTypes: true })) {
    if (e.name.startsWith('.') || e.name === 'node_modules' || e.name === '__pycache__') continue;
    const r = rel ? rel + '/' + e.name : e.name;
    if (e.isDirectory()) { if (depth > 0) walk(r, depth - 1, out); } else out.push(r);
  }
  return out;
};
const files = walk('', 2);
const builders = files.filter((f) => /^[^/]+\/build\.py$/.test(f) || /^[^/]+\/[^/]+\/build\.py$/.test(f)
  || /^web\/build_[^/]+\.py$/.test(f) || /^(?!web\/)[^/]+\/build_[^/]+\.py$/.test(f)
  || /^[^/]+\/[^/]+\/build_[^/]+\.py$/.test(f)
  || f === 'wiki/build_wiki.py').sort();
check(builders.length > 100, `found the builders on disk (${builders.length}) by walking the tree, not from a list`);

// ---- what the script runs ----
const named = new Set();
for (const m of REBUILD.matchAll(/(?:^|[\s;&{(])([a-z0-9_]+(?:\/[a-z0-9_]+)*\/[a-z0-9_]*build[a-z0-9_]*\.py)\b/g)) named.add(m[1]);
for (const m of REBUILD.matchAll(/for p in ([^;]+); do python3 \$p\/build\.py/g)) for (const p of m[1].trim().split(/\s+/)) named.add(p + '/build.py');
const globWeb = /for b in web\/build_\*\.py; do/.test(REBUILD);
check(globWeb, 'rebuild_all.sh loops over every web/build_*.py, so a new web builder is built without an edit');
const covered = (b) => named.has(b) || (globWeb && /^web\/build_[^/]+\.py$/.test(b));
for (const b of builders) {
  if (b in SKIP) {
    check(!named.has(b) && SKIP[b].length > 40, `${b} is on the reasoned skip list and not in the script (${SKIP[b].slice(0, 50)}...)`);
  } else {
    check(covered(b), `builder ${b} is run by rebuild_all.sh`);
  }
}
for (const s of Object.keys(SKIP)) check(builders.includes(s), `skip-list entry ${s} is a builder that exists (no stale skip)`);
for (const n of named) check(existsSync(join(ROOT, n)), `rebuild_all.sh names ${n}, which exists`);

// ---- order: the dependencies the protocol relies on ----
const at = (re) => REBUILD.search(re);
check(at(/python3 wiki\/build_wiki\.py/) > at(/python3 web\/build_home\.py/) && at(/echo REBUILT/) > at(/python3 wiki\/build_wiki\.py/),
  'the wiki is built after the pages it links, and REBUILT is printed last');
check(at(/python3 courses_roadmap\/build\.py/) > at(/python3 \$p\/build\.py/) && at(/python3 courses_roadmap\/build\.py/) > 0,
  'the course pack builder runs after the first pass has built the registries it maps onto');
check(at(/python3 security\/build_sbom\.py/) < at(/for b in web\/build_\*\.py/), 'the SBOM is built before the page builders that cite it');
check(at(/python3 compliance\/build\.py >\/dev\/null; python3 evals\/build\.py/) > at(/python3 web\/build_packs\.py/),
  'compliance and evals are rebuilt after the packs page, the second pass the stamps need');
check(/^set -e$/m.test(REBUILD) && /^cd "\$1"$/m.test(REBUILD), 'rebuild_all.sh stops on the first failing builder and builds the tree it is given');

// ---- the scripts are real and run anywhere ----
for (const s of SCRIPTS) {
  check(existsSync(join(ROOT, s)), `${s} exists`);
  check((statSync(join(ROOT, s)).mode & 0o111) !== 0, `${s} is executable`);
}
for (const s of SCRIPTS.filter((x) => x.endsWith('.sh'))) {
  const r = spawnSync('bash', ['-n', join(ROOT, s)], { encoding: 'utf8' });
  check(r.status === 0, `${s} parses as bash`);
}
const BAD = [new RegExp('/t' + 'mp\\b'), new RegExp('scratch' + 'pad', 'i'), new RegExp('claude' + '-0'), new RegExp('\\$S' + 'P\\b'), new RegExp('/home' + '/user')];
const toolFiles = walk('tools', 3).filter((f) => !/\.(json|png|jpg)$/.test(f));
check(toolFiles.length > 5, `scanned ${toolFiles.length} files under tools/ for machine-local paths`);
for (const f of toolFiles) {
  const t = text(f);
  const hit = BAD.map((re) => re.exec(t)).find(Boolean);
  check(!hit, `${f}: no scratch, temp-dir or home path${hit ? ' (found ' + hit[0] + ')' : ''}`);
}
const ROUND = text('tools/landing/browser_round.sh');
check(/CHROMIUM_LOCK/.test(ROUND) && /flock 9/.test(ROUND) && /flock -u 9/.test(ROUND), 'browser_round.sh takes and releases one chromium lock around every run');
check(/\$\{TMPDIR:\?/.test(ROUND), 'browser_round.sh refuses to guess a lock path: TMPDIR or CHROMIUM_LOCK must be set');
check(/^\. "\$RUNS"$/m.test(ROUND) && /kill \$SRV/.test(ROUND), 'browser_round.sh sources the runs file and stops its own server by PID');
const RUNS = text('tools/landing/browser_runs.sh').split('\n').filter((l) => l.startsWith('run '));
check(RUNS.length >= 8, `the default round has ${RUNS.length} run lines`);
for (const l of RUNS) {
  const w = l.split(/\s+/);
  check(/^\d+$/.test(w[2]) && Number(w[2]) <= 900, `run ${w[1]}: a numeric timeout of at most 900 s`);
  const target = (l.match(/\bnode (?:[A-Z_]+=\S+ )*(\S+\.mjs)/) || l.match(/\b(?:env \S+ )+node (\S+\.mjs)/) || [])[1];
  check(target && existsSync(join(ROOT, target)), `run ${w[1]}: its script ${target} exists in the repository`);
}

// ---- readme_fix.py does what it says, on a copy ----
const tmp = mkdtempSync(join(tmpdir(), 'landing-'));
try {
  writeFileSync(join(tmp, 'README.md'),
    '**1,000 checks, all passing**\n\nnode a/test.mjs     # 5 — **a** one\nnode b/test.mjs     # 9 — **b** two\n');
  writeFileSync(join(tmp, 'verify.txt'), 'ok a/test.mjs 7 checks\nok b/test.mjs 9 checks\nok c/test.mjs 3 checks\n12 checks, 0 failing suites\n');
  writeFileSync(join(tmp, 'rows.json'), JSON.stringify({ 'c/test.mjs': 'node c/test.mjs     # %s — **c** new' }));
  const r = spawnSync('python3', [join(HERE, 'readme_fix.py'), tmp, join(tmp, 'verify.txt'), join(tmp, 'rows.json')], { encoding: 'utf8' });
  const out = readFileSync(join(tmp, 'README.md'), 'utf8');
  check(r.status === 0 && /# 7 — \*\*a\*\*/.test(out), 'readme_fix.py moves a suite row to the count the run printed');
  check(/# 9 — \*\*b\*\*/.test(out), 'readme_fix.py leaves a row alone when its count already agrees');
  check(/^\*\*12 checks, all passing/m.test(out), 'readme_fix.py sets the headline to the run total');
  check(/^node c\/test\.mjs     # 3 — \*\*c\*\* new$/m.test(out), 'readme_fix.py inserts a new row from rows.json with the run count filled in');
  writeFileSync(join(tmp, 'rows.json'), JSON.stringify({ 'zzz/test.mjs': 'node zzz/test.mjs # %s' }));
  const bad = spawnSync('python3', [join(HERE, 'readme_fix.py'), tmp, join(tmp, 'verify.txt'), join(tmp, 'rows.json')], { encoding: 'utf8' });
  check(bad.status !== 0, 'readme_fix.py stops when rows.json names a suite the run did not print');
} finally { rmSync(tmp, { recursive: true, force: true }); }

// ---- documented ----
const README = text('tools/landing/README.md');
for (const s of [...SCRIPTS, 'tools/landing/geomap_hillshade_probe.mjs']) {
  check(README.includes(s.split('/').pop()), `tools/landing/README.md names ${s.split('/').pop()}`);
}

console.log(`${oks} checks passed${fails ? `, ${fails} FAILED` : ''}.`);
process.exit(fails ? 1 : 0);
