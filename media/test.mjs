// media/test.mjs - the b-roll library holds to what its registry says.
// Prints `  ok ` per check; FAIL at column 0 and a non-zero exit on failure.
import { readFileSync, existsSync, statSync, readdirSync } from 'node:fs';
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
// Text may not carry links either; binaries are scanned without the link pattern, since a container
// format may legitimately name a schema URL, and with a key pattern long enough not to fire on noise.
const LEAK = /rk_|https?:\/\/|\/tmp|claude|anthropic|scratch/i;
const LEAK_BYTES = /rk_[0-9a-f]{16}|\/tmp\/|\/home\/|\/root\/|scratchpad|claude|anthropic/i;
const SHOTS = JSON.parse(readFileSync(join(HERE, 'shots.json'), 'utf8'));
const LIB = JSON.parse(readFileSync(join(HERE, 'library.json'), 'utf8'));
const stampSrc = Buffer.concat(['shots.json', 'record.mjs', 'encode.py', 'build.py', 'library.json']
  .map((f) => readFileSync(join(HERE, f))));
check(createHash('sha256').update(stampSrc).digest('hex') === REG.source_stamp,
  'source_stamp matches shots.json + record.mjs + encode.py + build.py + library.json (registry is current)');

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

// ---- the stills and the explainer (media/library.json, web/media/stills, web/media/explainer) ----
const CAPTURE_SENTENCE = 'RECORDED: captured in headless Chromium from the pages at commit 83db20b, 1280x720';
const EXPLAINER_SENTENCE = 'DERIVED: composed from recorded page footage and stills at 83db20b, captioned, silent';
const jpegSize = (b) => {
  let i = 2;
  while (i + 9 < b.length) {
    const m = b[i + 1], n = b.readUInt16BE(i + 2);
    if (m >= 0xc0 && m <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(m)) return [b.readUInt16BE(i + 7), b.readUInt16BE(i + 5)];
    i += 2 + n;
  }
  return null;
};
const mvhdSeconds = (b) => {
  const k = b.indexOf('mvhd'); const o = k + 4;
  return b[o] === 1 ? Number(b.readBigUInt64BE(o + 24)) / b.readUInt32BE(o + 20) : b.readUInt32BE(o + 16) / b.readUInt32BE(o + 12);
};
const listed = (d) => readdirSync(join(ROOT, d)).sort();

check(REG.capture && REG.capture.provenance === CAPTURE_SENTENCE && LIB.capture.provenance === CAPTURE_SENTENCE,
  'the capture provenance is recorded in words: headless Chromium, commit 83db20b, 1280x720');
check(REG.stills.length === LIB.stills.length && REG.stills.length >= 13,
  `every authored still is in the registry (${REG.stills.length} stills)`);
check(JSON.stringify(listed('web/media/stills')) === JSON.stringify(LIB.stills.map((s) => s.file).sort()),
  'web/media/stills holds exactly the files library.json names - no unregistered file');
for (const s of REG.stills) {
  const p = join(ROOT, s.file.path);
  const b = existsSync(p) ? readFileSync(p) : null;
  check(b && sha(p) === s.file.sha256 && b.length === s.file.bytes, `still ${s.id}: matches its sha256 and size`);
  check(b && isJpeg(b), `still ${s.id}: is a JPEG by its bytes`);
  const dim = b && jpegSize(b);
  check(dim && dim[0] === s.file.width && dim[1] === s.file.height && s.file.width === 1280 && s.file.height <= 720,
    `still ${s.id}: ${s.file.width}x${s.file.height} is what the header says, within the 1280x720 viewport`);
  check(s.provenance === CAPTURE_SENTENCE && s.licence === 'first-party', `still ${s.id}: provenance recorded, first-party`);
  check(existsSync(join(ROOT, s.source.page)) && s.caption.length > 30 && !/\n/.test(s.caption) && s.caption.includes(s.source.page),
    `still ${s.id}: a one-line caption naming its page ${s.source.page}, which exists`);
  check(b && b.length < 200 * 1024, `still ${s.id}: ${b && b.length} bytes is under 200 KB`);
  check(!LEAK.test(s.caption), `still ${s.id}: the caption holds no key, link, internal path or model name`);
  check(b && !LEAK_BYTES.test(b.toString('latin1')), `still ${s.id}: the image bytes (metadata included) hold no key, internal path or model name`);
}
const EX = REG.explainer;
check(EX && EX.provenance === EXPLAINER_SENTENCE && LIB.explainer.provenance === EXPLAINER_SENTENCE,
  'the explainer provenance is recorded in words: composed from recorded footage and stills at 83db20b, captioned, silent');
check(JSON.stringify(listed('web/media/explainer')) === JSON.stringify(Object.values(LIB.explainer.files).sort()),
  'web/media/explainer holds exactly mp4, poster and captions - no webm, nothing unregistered');
for (const kind of ['mp4', 'poster', 'captions']) {
  const f = EX.files[kind]; const p = join(ROOT, f.path);
  check(existsSync(p) && sha(p) === f.sha256 && statSync(p).size === f.bytes, `explainer ${kind}: matches its sha256 and size`);
}
const exB = readFileSync(join(ROOT, EX.files.mp4.path));
check(isMp4H264(exB) && !exB.includes('soun'), 'explainer: an H.264 mp4 with no audio track (it is silent in the bytes, not only in the sentence)');
check(Math.abs(mvhdSeconds(exB) - LIB.explainer.seconds) < 0.5 && EX.duration_s === LIB.explainer.seconds,
  `explainer: the movie header says ${mvhdSeconds(exB).toFixed(1)} s, the registry ${EX.duration_s} s`);
check(EX.files.mp4.bytes <= EX.budget_bytes && EX.budget_bytes <= 10 * 1024 * 1024, `explainer: ${EX.files.mp4.bytes} bytes is within its own ${EX.budget_bytes}-byte budget (10 MB at most)`);
const pdim = jpegSize(readFileSync(join(ROOT, EX.files.poster.path)));
check(isJpeg(readFileSync(join(ROOT, EX.files.poster.path))) && pdim[0] === 1280 && pdim[1] === 720, 'explainer: the poster is a 1280x720 JPEG');
const caps = readFileSync(join(ROOT, EX.files.captions.path), 'utf8');
const capLines = caps.split('\n').filter((x) => x.trim());
check(capLines.length === EX.caption_lines && capLines.length >= 10, `explainer: the captions file carries ${capLines.length} lines, as registered`);
check(!LEAK.test(caps), 'explainer: the captions hold no key, link, internal path or model name');
for (const kind of ['mp4', 'poster']) {
  check(!LEAK_BYTES.test(readFileSync(join(ROOT, EX.files[kind].path)).toString('latin1')), `explainer ${kind}: the bytes (metadata included) hold no key, internal path or model name`);
}
check(/No AI model/.test(caps) && /unverified general practice/.test(caps) && /not partners or affiliates/.test(caps),
  'explainer: the captions carry the standing honesty lines (no AI model, unverified practice, not partners)');
check(EX.figures_note.includes('not refreshed'), 'explainer: says its spoken figures are those of the capture commit, not refreshed');

console.log(`${oks} checks passed${fails ? `, ${fails} FAILED` : ''}.`);
process.exit(fails ? 1 : 0);
