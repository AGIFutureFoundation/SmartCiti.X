// media/test.mjs - the b-roll library holds to what its registry says.
// Prints `  ok ` per check; FAIL at column 0 and a non-zero exit on failure.
import { readFileSync, existsSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let fails = 0, oks = 0;
const ok = (m) => { oks++; console.log('  ok ' + m); };
const check = (cond, m) => { if (cond) ok(m); else { fails++; console.log('FAIL ' + m); } };
const sha = (p) => createHash('sha256').update(readFileSync(p)).digest('hex');

const REG = JSON.parse(readFileSync(join(HERE, 'registry', 'media.json'), 'utf8'));
const SHOTS = JSON.parse(readFileSync(join(HERE, 'shots.json'), 'utf8'));
const stampSrc = Buffer.concat(['shots.json', 'record.mjs', 'encode.py', 'build.py']
  .map((f) => readFileSync(join(HERE, f))));
check(createHash('sha256').update(stampSrc).digest('hex') === REG.source_stamp,
  'source_stamp matches shots.json + record.mjs + encode.py + build.py (registry is current)');

const BUDGET = 3 * 1024 * 1024;
check(REG.budget_bytes === BUDGET, 'the budget is 3 MB per full-size file');
check(REG.clips.length + REG.pending.length === SHOTS.clips.length,
  'every shot is either a clip or pending with a reason - none silently dropped');
const heroes = REG.clips.filter((c) => c.hero);
check(heroes.every((c) => c.known_issue === null),
  `no clip with a recorded known issue is offered as hero quality (${heroes.length} hero clips rendered)`);
check(REG.clips.every((c) => c.known_issue === null || (typeof c.known_issue === 'string' && c.known_issue.length > 20)),
  'every known issue is stated in words, not a flag');
check(REG.pending.every((p) => SHOTS.clips.some((s) => s.id === p.id) && /^not rendered yet: /.test(p.why)),
  `every pending shot is a real shot and says why (${REG.pending.length} pending)`);

// what the bytes are, not what the name says
const isWebmVp9 = (b) => b.readUInt32BE(0) === 0x1a45dfa3 && b.includes('V_VP9');
const isMp4H264 = (b) => b.subarray(4, 8).toString() === 'ftyp' && b.includes('avc1');
const isJpeg = (b) => b[0] === 0xff && b[1] === 0xd8 && b[b.length - 2] === 0xff && b[b.length - 1] === 0xd9;

const REQ = ['known_issue', 'hero', 'id', 'title', 'shows', 'source', 'camera_move', 'duration_s', 'fps', 'frames',
  'resolution', 'files', 'provenance', 'licence', 'status'];
for (const c of REG.clips) {
  const miss = REQ.filter((k) => !(k in c));
  check(!miss.length, `${c.id}: carries every registry field${miss.length ? ' (missing ' + miss + ')' : ''}`);
  for (const kind of ['webm', 'mp4', 'poster', 'preview']) {
    const f = c.files[kind];
    if (!f) { fails++; console.log(`FAIL ${c.id}: no ${kind} file`); continue; }
    const p = join(ROOT, f.path);
    if (!existsSync(p)) { fails++; console.log(`FAIL ${c.id}: ${f.path} does not exist`); continue; }
    check(sha(p) === f.sha256 && statSync(p).size === f.bytes, `${c.id}: ${kind} matches its sha256 and size`);
  }
  const w = c.files.webm && join(ROOT, c.files.webm.path);
  const m = c.files.mp4 && join(ROOT, c.files.mp4.path);
  if (w && m && existsSync(w) && existsSync(m)) {
    check(statSync(w).size <= BUDGET && statSync(m).size <= BUDGET,
      `${c.id}: webm ${statSync(w).size} and mp4 ${statSync(m).size} bytes are within budget`);
    check(isWebmVp9(readFileSync(w)) && isMp4H264(readFileSync(m)), `${c.id}: both codecs present (VP9 webm, H.264 mp4)`);
  }
  const po = c.files.poster && join(ROOT, c.files.poster.path);
  check(po && existsSync(po) && isJpeg(readFileSync(po)), `${c.id}: poster is a JPEG`);
  const pv = c.files.preview && join(ROOT, c.files.preview.path);
  check(pv && existsSync(pv) && isWebmVp9(readFileSync(pv)), `${c.id}: 480 px preview is a VP9 webm`);
  check(c.duration_s >= 6 && c.duration_s <= 15, `${c.id}: ${c.duration_s} s is within 6-15 s`);
  check(c.frames === Math.round(c.duration_s * c.fps), `${c.id}: ${c.frames} frames = duration x fps`);
  check(c.licence === 'first-party', `${c.id}: licence is first-party`);
  const wip = c.status === 'work in progress';
  check(wip ? /^RECORDED from the working tree, work in progress/.test(c.provenance)
            : /^RECORDED from this build \(commit [0-9a-f]{12}\)$/.test(c.provenance),
    `${c.id}: provenance names the commit it was recorded from${wip ? ' and says work in progress' : ''}`);
  check(existsSync(join(ROOT, c.source.page.split('#')[0])), `${c.id}: source page ${c.source.page} exists`);
}

console.log(`${oks} checks passed${fails ? `, ${fails} FAILED` : ''}.`);
process.exit(fails ? 1 : 0);
