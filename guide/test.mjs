/**
 * Guide registry verification.
 *
 * The claim of this pack is narrow and therefore checkable: the guide
 * answers six fixed questions about the place a learner is already in, it
 * invents nothing, and every sentence it can say is grounded in a file
 * that exists in this repo. So the checks below are mostly about
 * resolution - a `cites` that names a missing file, a control that names a
 * key the page never reads, a gesture that names a joint WebXR does not
 * define, and a count that has drifted from the thing it counts are all
 * the same bug wearing different clothes.
 *
 * Three of them are worth reading twice.
 *
 * The SEAT CONTROLS are not compared loosely. Every seat row must equal
 * the simulator registry's own row verbatim, and every seat's XR mapping
 * must equal sims/'s verbatim, because the moment the guide is allowed to
 * paraphrase a control scheme it has become a second copy of one.
 *
 * The VOICE BANNERS are not read for tone. The banner the page puts in
 * front of each switch must be exactly the six declared honesty fields
 * joined in the declared order - so there is one copy of each sentence,
 * and a banner cannot be softened without softening the registry that
 * publishes it. The ask-by-voice banner is then checked by content for the
 * facts that make it honest rather than reassuring: that the audio leaves
 * the device, whose service receives it, that this bundle can neither
 * operate nor see that service, that no audio is stored, and that an
 * unavailable feature is absent rather than quietly degraded.
 *
 * The HANDS are checked for hysteresis. One threshold makes a gesture
 * chatter on and off at the boundary; on a gesture whose job is to STOP
 * the learner moving, that is a safety bug rather than a polish one. Every
 * gesture must declare a release distance a real band away from the
 * threshold that fires it - and the whole feature must still say, in its
 * own status line, that no hand has ever made one of these on hardware.
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const url = (p) => new URL(p, import.meta.url);
const reg = JSON.parse(readFileSync(url('./registry/guide.json')));
const sims = JSON.parse(readFileSync(url('../sims/registry/sims.json')));
const training = JSON.parse(readFileSync(url('../training/registry/training.json')));
const manifest = JSON.parse(readFileSync(url('../pack/manifest.json')));
const page = readFileSync(url('../web/build_3d.py'), 'utf8');
const ROOT = fileURLToPath(url('../'));

const places = Object.entries(reg.places);
const topics = places.flatMap(([pid, p]) => p.topics.map((t) => [pid, p, t]));
const askIds = reg.ask_set.map((a) => a.id);
const shared = Object.entries(reg.controls.shared);
const seats = Object.entries(reg.controls.seats);
const gestures = Object.entries(reg.hands.gestures);
const voice = Object.entries(reg.voice.features);

/* ------------------------------------------------------------ the shape --- */
ok('the pack carries the same header every pack in this bundle carries',
  reg.pack === 'smartcitix-trade-craft-academy-guide'
  && reg.pack_version === manifest.pack_version
  && /^\d{4}-\d{2}-\d{2}$/.test(reg.built) && reg.source_stamp.length === 16);
ok('the ask set is six questions, closed, and every id is unique',
  askIds.length === 6 && new Set(askIds).size === 6
  && reg.ask_set.every((a) => a.asks.length > 10));
ok('every place answers every ask, in the declared order, and invents no seventh',
  places.every(([, p]) => p.topics.length === askIds.length
    && p.topics.every((t, i) => t.id === askIds[i])));
ok('every place says what it is, how it is reached, and whether it can be walked',
  places.every(([, p]) => p.name.length > 3 && p.what_line.length > 20
    && p.opened_by.length > 20 && typeof p.walkable === 'boolean'
    && ['world', 'panel'].includes(p.kind)));
ok('every topic is a question, and no two topics in a place share an id',
  topics.every(([, , t]) => t.ask.endsWith('?') && t.ask.length > 12)
  && places.every(([, p]) => new Set(p.topics.map((t) => t.id)).size === p.topics.length));
ok('every answer is two to four plain sentences - one is a slogan, five is a lecture',
  topics.every(([, , t]) => {
    const s = t.answer.trim().split(/(?<=[.!?])\s+/).length;
    return s >= 2 && s <= 4 && t.answer.length >= 120 && t.answer.length <= 460;
  }));

/* ------------------------------------------------------ grounded, or not --- */
ok('every topic names the repo file its answer is grounded in, and that file EXISTS',
  topics.every(([, , t]) => typeof t.cites === 'string'
    && existsSync(new URL(t.cites, url('../')))));
ok('every cite is repo-relative: no leading slash, no climbing out of the repo',
  topics.every(([, , t]) => !t.cites.startsWith('/') && !t.cites.includes('..')
    && existsSync(ROOT + t.cites)));
ok('the published cite list is exactly the set of files the topics actually name',
  JSON.stringify(reg.cites)
  === JSON.stringify([...new Set(topics.map(([, , t]) => t.cites))].sort()));
ok('nothing in the payload is a URL - the guide fetches nothing and links nowhere',
  !/https?:\/\//.test(JSON.stringify(reg)));
ok('no answer is a template the page would have to evaluate at view time',
  topics.every(([, , t]) => !t.answer.includes('${') && !t.answer.includes('{')));

/* --------------------------------------------------------- where you are --- */
ok('every world place names a view the page actually sets, and no panel names one',
  places.every(([, p]) => p.kind === 'panel'
    ? p.view === null
    : page.includes(`view = '${p.view}'`)));
ok('every view the page can set has exactly one place speaking for it',
  (() => {
    const pageViews = new Set([...page.matchAll(/view = '([a-z]+)'/g)].map((m) => m[1]));
    const mine = places.filter(([, p]) => p.view).map(([, p]) => p.view);
    return new Set(mine).size === mine.length
      && mine.length === pageViews.size && mine.every((v) => pageViews.has(v));
  })());
ok('the four panels are panels: no view, and the same close answer shape',
  places.filter(([, p]) => p.kind === 'panel').length === 4
  && places.filter(([, p]) => p.kind === 'panel')
    .every(([, p]) => p.topics.every((t) => t.id !== 'move' || t.scheme === 'panel')));

/* ----------------------------------------------------------- the controls --- */
ok('the move topic of every place names a control scheme, and nothing else does',
  places.every(([, p]) => p.topics.every((t) =>
    t.id === 'move' ? typeof t.scheme === 'string' : !('scheme' in t))));
ok('every named scheme is one this registry declares, or the running-seat binding',
  places.every(([, p]) => {
    const s = p.topics.find((t) => t.id === 'move').scheme;
    return s in reg.controls.shared || s === 'seat:running';
  }));
ok('only a walkable place names the walking scheme, and every walkable place does',
  places.every(([pid, p]) => {
    const s = p.topics.find((t) => t.id === 'move').scheme;
    return p.walkable === (s === 'walk-keyboard');
  }));
ok('only the seat resolves a running seat, and it is the only place that does',
  places.filter(([, p]) =>
    p.topics.find((t) => t.id === 'move').scheme === 'seat:running')
    .map(([pid]) => pid).join() === 'seat');
ok('every written control row says what it does and names something checkable',
  shared.every(([, s]) => s.rows.length > 0 && s.rows.every((r) =>
    r.input.length > 2 && r.does.length > 25 && r.codes.length > 0)));
ok('every key code and handler a written scheme claims is one the page actually reads',
  shared.every(([, s]) => s.rows.every((r) => r.codes.every((c) => page.includes(c)))));
ok('no scheme lists the same input twice',
  shared.every(([, s]) => new Set(s.rows.map((r) => r.input)).size === s.rows.length));

/* ------------------------------------------- read from sims, never retyped --- */
ok('every seat the simulator registry declares has a scheme here, and none extra',
  seats.length === Object.keys(sims.sims).length
  && seats.every(([sid]) => sid in sims.sims));
ok('every seat row is the simulator registry\'s own row, verbatim - keys and action',
  seats.every(([sid, s]) => {
    const src = sims.sims[sid].controls;
    return s.rows.length === src.length && s.rows.every((r, i) =>
      r.input === src[i].keys && r.does === src[i].action);
  }));
ok('every seat name is read from sims/ too, not retyped beside it',
  seats.every(([sid, s]) => s.name === sims.sims[sid].name
    && s.source === 'sims/registry/sims.json'));
ok('every seat\'s XR mapping is the simulator registry\'s own mapping, verbatim',
  seats.every(([sid, s]) =>
    JSON.stringify(s.xr) === JSON.stringify(sims.sims[sid].xr)));
ok('every seat key resolves to a code the page actually drives a seat with',
  (() => {
    const m = page.match(/const OP_KEYS = \[([^\]]+)\]/);
    if (!m) return false;
    const opKeys = new Set([...m[1].matchAll(/'([A-Za-z]+)'/g)].map((x) => x[1]));
    opKeys.add('Space');
    return seats.every(([, s]) => s.rows.every((r) => r.codes.every((c) => opKeys.has(c))))
      && seats.every(([, s]) => s.xr.grip_key === null || opKeys.has(s.xr.grip_key));
  })());
ok('every seat row\'s codes are the codes its own key tokens spell out',
  seats.every(([, s]) => s.rows.every((r) => {
    const want = r.input.split('/').map((k) => {
      const tok = k.trim();
      return tok === 'Space' ? 'Space' : 'Key' + tok.toUpperCase();
    });
    return JSON.stringify(r.codes) === JSON.stringify(want);
  })));

/* --------------------------------------------------------------- the voice --- */
ok('both voice features are OFF by default - a microphone never defaults on',
  voice.length === 2 && voice.every(([, f]) => f.default === 'off'));
ok('each feature declares all six honesty fields, and none of them is a stub',
  voice.every(([, f]) => reg.voice.fields.length === 6
    && reg.voice.fields.every((k) => typeof f[k] === 'string' && f[k].length > 60)));
ok('each banner is exactly the six fields joined in the declared order - one copy of each sentence',
  voice.every(([, f]) => f.banner === reg.voice.fields.map((k) => f[k]).join(' ')));
ok('the two switches have their own namespaced keys, and collide with nothing already stored',
  (() => {
    const mine = voice.map(([, f]) => f.storage_key);
    const taken = new Set([...page.matchAll(/'(tc-[a-z-]+)'/g)].map((m) => m[1]));
    taken.add(training.storage.key); taken.add(training.storage.toggle_key);
    taken.add(training.trace.toggle_key);
    return new Set(mine).size === 2 && mine.every((k) => k.startsWith('tc-guide-'))
      && mine.every((k) => !taken.has(k))
      && reg.voice.storage.read_aloud_key === reg.voice.features.read_aloud.storage_key
      && reg.voice.storage.ask_by_voice_key === reg.voice.features.ask_by_voice.storage_key;
  })());
ok('an absent key reads as off: the storage block says a missing key is never consent',
  /absent, and an absent key reads as OFF/.test(reg.voice.storage.default)
  && /never read as consent/.test(reg.voice.storage.default));
ok('the ask-by-voice banner says plainly that the audio leaves the device, and to whom',
  /sends your recorded voice off this device/.test(reg.voice.features.ask_by_voice.leaves_the_device)
  && /browser's own vendor/.test(reg.voice.features.ask_by_voice.leaves_the_device)
  && /do not recognise speech inside the page/.test(reg.voice.features.ask_by_voice.leaves_the_device));
ok('it disclaims both operating and seeing that service, and stores no audio',
  /neither operates that service/.test(reg.voice.features.ask_by_voice.not_ours)
  && /nor can see what it receives/.test(reg.voice.features.ask_by_voice.not_ours)
  && /stores no audio anywhere/.test(reg.voice.features.ask_by_voice.no_audio_kept));
ok('the on-device path is stated with its failure, and it fails closed rather than falling back',
  /processLocally/.test(reg.voice.features.ask_by_voice.on_device)
  && /language-not-supported/.test(reg.voice.features.ask_by_voice.on_device)
  && /rather than quietly retrying/.test(reg.voice.features.ask_by_voice.on_device));
ok('read-aloud never claims local: it names localService and says some voices are remote',
  /usually local and not always/.test(reg.voice.features.read_aloud.leaves_the_device)
  && /sent to the voice vendor/.test(reg.voice.features.read_aloud.leaves_the_device)
  && /localService/.test(reg.voice.features.read_aloud.not_ours));
ok('an unsupported browser gets no control at all - absent, never quietly degraded',
  voice.every(([, f]) => /absent rather than degraded/.test(f.unavailable)));

/* --------------------------------------------------------------- the hands --- */
ok('the joint table is the 25 joints WebXR Hand Input defines, with no duplicates',
  reg.hands.joints.length === 25 && new Set(reg.hands.joints).size === 25
  && reg.hands.joints.includes('wrist')
  && reg.hands.joints.includes('index-finger-phalanx-intermediate')
  && !reg.hands.joints.includes('thumb-phalanx-intermediate')
  && reg.hands.session_feature === 'hand-tracking');
ok('every gesture measures between joints that actually exist, each named once',
  gestures.every(([, g]) => g.joints.length > 1
    && new Set(g.joints).size === g.joints.length
    && g.joints.every((j) => reg.hands.joints.includes(j))));
ok('every gesture declares a real hysteresis band - one threshold would chatter',
  gestures.every(([, g]) => {
    const band = Math.abs(g.release_m - g.threshold_m);
    return band >= 0.01 && band <= 0.04
      && g.threshold_m > 0.005 && g.threshold_m < 0.3
      && g.hold_ms >= 0 && g.hold_ms <= 1000;
  }));
ok('every gesture says what it measures and what it does, and applies only where you can walk',
  gestures.every(([, g]) => g.measure.length > 60 && g.does.length > 40
    && g.where.length > 0
    && g.where.every((w) => w in reg.places && reg.places[w].walkable)));
ok('exactly one gesture opens the guide, so there is one way in and not two',
  gestures.filter(([, g]) => g.does.includes('open this guide')).length === 1);
ok('the hand table admits it is unverified on hardware and mocked-session only',
  /^UNVERIFIED-ON-HARDWARE:/.test(reg.hands.honesty.status)
  && /no headset has been available/.test(reg.hands.honesty.status)
  && /MOCKED WebXR session only/.test(reg.hands.honesty.status)
  && /AUTHORED/.test(reg.hands.honesty.thresholds_are_authored));
ok('and that claim is grounded in the page\'s own admission, not in this pack\'s good intentions',
  page.includes('mocked WebXR session')
  && /do not exist in it yet/.test(reg.hands.honesty.declared_not_built));

/* -------------------------------------------------- what the guide admits --- */
ok('the pack carries the SCRIPTED provenance word and never borrows orbis\'s',
  /^SCRIPTED: /.test(reg.honesty.status)
  && /No model runs behind it/.test(reg.honesty.status)
  && /reaches no network/.test(reg.honesty.status));
ok('AI-SYNTHESIZED appears in exactly one answer, the one explaining that orbis owns it',
  topics.filter(([, , t]) => t.answer.includes('AI-SYNTHESIZED'))
    .map(([pid, , t]) => `${pid}/${t.id}`).join() === 'panel-orbis/limits');
ok('the book is closed, and asking by voice picks a declared topic rather than making one',
  /cannot be asked an open question/.test(reg.honesty.closed_book)
  && /never produces a new answer/.test(reg.honesty.closed_book));
ok('opening the guide is not a gate: no field could express one, and no answer promises one',
  /changes no score and unlocks nothing/.test(reg.honesty.not_scored)
  && topics.every(([, , t]) => !('requires' in t) && !('unlocks' in t)
    && !('after' in t) && !('score' in t) && !('points' in t)));
ok('and every sentence that mentions locking - bar the pointer lock, which is an input - denies that anything is',
  JSON.stringify(reg).split(/(?<=\.)\s|\\n/)
    .filter((s) => /\block(ed|ing|s)?\b/i.test(s) && !/pointer/i.test(s))
    .every((s) => /\b(no|not|nothing|never)\b/i.test(s)));
ok('the guide stores two switch states and nothing a learner said',
  /whether each of the two voice switches is on/.test(reg.honesty.device_local)
  && /neither key ever holds audio/.test(reg.voice.storage.not_kept)
  && /audio, a transcript or anything a learner said/.test(reg.voice.storage.not_kept));
ok('no real union local, employer or person is named anywhere in the guide',
  !/\bLocal\s+\d|\bIBEW\b|\bUA\s+\d|\bLiUNA\b/i.test(JSON.stringify(reg)));
ok('the page contract names every piece of wiring the guide needs and nothing it does not',
  ['data', 'button', 'route', 'ask', 'controls', 'voice', 'hands', 'episode']
    .every((k) => typeof reg.page_contract[k] === 'string'
      && reg.page_contract[k].length > 30)
  && /nothing is recorded/i.test(reg.page_contract.episode));

/* -------------------------------------------------------------- the counts --- */
ok('the counts the registry publishes are the counts it actually holds',
  reg.counts.places === places.length
  && reg.counts.world_places === places.filter(([, p]) => p.kind === 'world').length
  && reg.counts.panel_places === places.filter(([, p]) => p.kind === 'panel').length
  && reg.counts.asks === askIds.length
  && reg.counts.topics === topics.length
  && reg.counts.topics === reg.counts.places * reg.counts.asks
  && reg.counts.cited_files === new Set(topics.map(([, , t]) => t.cites)).size
  && reg.counts.control_schemes === shared.length
  && reg.counts.seat_schemes === seats.length
  && reg.counts.xr_seat_mappings === seats.length
  && reg.counts.gestures === gestures.length
  && reg.counts.hand_joints === reg.hands.joints.length
  && reg.counts.voice_features === voice.length);
ok('the control count is the written rows plus the rows read from sims/, not a typed number',
  reg.counts.shared_controls === shared.reduce((a, [, s]) => a + s.rows.length, 0)
  && reg.counts.seat_controls === seats.reduce((a, [, s]) => a + s.rows.length, 0)
  && reg.counts.seat_controls
     === Object.values(sims.sims).reduce((a, s) => a + s.controls.length, 0)
  && reg.counts.controls === reg.counts.shared_controls + reg.counts.seat_controls);

const src = readFileSync(url('./build.py'));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`guide/test: ${n} checks passed — ${places.length} places, `
  + `${topics.length} topics over ${askIds.length} asks, `
  + `${reg.counts.cited_files} files cited; ${reg.counts.controls} controls `
  + `(${reg.counts.shared_controls} written, ${reg.counts.seat_controls} read from sims/); `
  + `${gestures.length} gestures, unverified on hardware; both voice switches off by default`);
