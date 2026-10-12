/* hive/test.mjs - the Omega Hive registry (hive/registry/hive.json), checked against the registries it connects.
 * Recompute, never re-read: every line is re-resolved at its source path by a resolver written here (not the build's),
 * the avatar rule, the voice offset rule and the K-12 rule are re-derived here, and the counts are recounted from
 * agents/, npcs/ and avatars/. Prints `  ok  ` per check and `FAIL` at column 0. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c, why) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m + (why ? ' :: ' + JSON.stringify(why).slice(0, 400) : '')); } };
const J = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));
const hive = J('hive/registry/hive.json');
const auth = J('hive/authored/personalities.json');
const adv = J('agents/registry/advisors.json'), crews = J('agents/registry/crews.json'), npcs = J('npcs/registry/npcs.json'), av = J('avatars/registry/avatars.json');
const cache = {};
const load = (rel) => (cache[rel] ??= J(rel));
function resolve(ref) {
  const [rel, path] = ref.split('#');
  let node = load(rel);
  const re = /\.?([A-Za-z0-9_-]+)|\[(\d+)\]|\["([^"]+)"\]/y;
  re.lastIndex = 0;
  while (re.lastIndex < path.length) {
    const m = re.exec(path);
    if (!m) return undefined;
    node = m[2] !== undefined ? node?.[+m[2]] : node?.[m[3] ?? m[1]];
    if (node === undefined) return undefined;
  }
  return node;
}
const h8 = (s) => parseInt(createHash('sha256').update(s).digest('hex').slice(0, 8), 16);
const A = hive.agents;
const byKind = (k) => A.filter((a) => a.kind === k);

/* ---- registry shape and provenance */
ok('the registry is hive/1, named Omega Hive, with a 16-hex source stamp', hive.schema === 'hive/1' && hive.name === 'Omega Hive' && /^[0-9a-f]{16}$/.test(hive.source_stamp));
ok('the source stamps it records are the source registries\' current stamps (advisors, crews, npcs, avatars)',
  Object.entries(hive.source_stamps).length === 4 && Object.entries(hive.source_stamps).every(([r, s]) => load(r).source_stamp === s));
ok('python3 hive/build.py --check: the committed registry is what the build writes now',
  spawnSync('python3', [join(ROOT, 'hive/build.py'), '--check'], { encoding: 'utf8' }).status === 0);

/* ---- every agent already in the repo, once */
const advIds = Object.keys(adv.advisors).map((k) => 'advisor:' + k);
const roleIds = Object.values(crews.crews).flatMap((c) => Object.values(c.roles).map((r) => 'crew:' + r.key));
const npcIds = npcs.npcs.map((n) => 'npc:' + n.id);
const want = [...advIds, ...roleIds, ...npcIds];
ok(`every agent in agents/ and npcs/ is in the hive exactly once (${advIds.length} advisors + ${roleIds.length} crew roles + ${npcIds.length} NPCs = ${want.length})`,
  A.length === want.length && JSON.stringify(A.map((a) => a.id)) === JSON.stringify(want) && new Set(A.map((a) => a.id)).size === A.length);
ok('the source registries\' own counts agree: 9 advisors, 6 crews, 20 roles, 168 NPCs',
  advIds.length === adv.counts.advisors && adv.counts.advisors === 9 && Object.keys(crews.crews).length === 6 && roleIds.length === crews.counts.roles
  && crews.counts.roles === 20 && npcIds.length === npcs.counts.npcs && npcs.counts.npcs === 168);
const lines = A.flatMap((a) => a.lines);
const C = hive.counts;
ok(`the counts are recounted: agents ${A.length}, lines ${lines.length}, say ${C.say}, read ${C.read}, knowledge ${C.knowledge}, models 0`,
  C.agents === A.length && C.advisors === advIds.length && C.crew_roles === roleIds.length && C.npcs === npcIds.length && C.lines === lines.length
  && ['say', 'read', 'greeting', 'knowledge'].every((k) => C[k] === lines.filter((l) => l.kind === k).length)
  && C.job_stops_limits === lines.filter((l) => ['job', 'stops', 'limits'].includes(l.kind)).length
  && C.models === 0 && C.personalities === A.length && C.voices === A.length
  && C.characters_used === new Set(A.map((a) => a.avatar.character)).size);
ok('names are the source registries\' own names, read at their name_source', A.every((a) => resolve(a.name_source) === a.name));

/* ---- SCRIPTED lines: every one re-resolved here, verbatim */
const KINDS = ['greeting', 'say', 'read', 'job', 'stops', 'knowledge', 'limits'];
const badLine = lines.filter((l) => !KINDS.includes(l.kind) || typeof l.text !== 'string' || !l.text.trim() || resolve(l.source) !== l.text
  || (l.via && resolve(l.via) !== l.text));
ok(`every line (${lines.length}) is character-for-character the text at its source path (and at its npcs.json path)`, badLine.length === 0, badLine.slice(0, 3));
const badAsk = lines.filter((l) => 'ask' in l && (l.ask_provenance === 'REGISTRY' ? resolve(l.ask_source) !== l.ask : !(l.ask_provenance === 'AUTHORED' && hive.asks_authored.includes(l.ask))));
ok('every ask is either registry text at its ask_source or one of the three AUTHORED asks, marked AUTHORED', badAsk.length === 0, badAsk.slice(0, 3));
const missTopics = [];
for (const [aid, a] of Object.entries(adv.advisors)) {
  const ag = A.find((x) => x.id === 'advisor:' + aid);
  if (ag.lines[0].kind !== 'greeting' || ag.lines[0].text !== a.greeting) missTopics.push(aid + ' greeting');
  a.topics.forEach((t) => { const l = ag.lines.find((x) => x.id === t.id && x.kind === t.kind);
    if (!l || l.text !== (t.kind === 'say' ? t.say : adv.bindings[t.bind])) missTopics.push(aid + ':' + t.id); });
}
for (const c of Object.values(crews.crews)) for (const r of Object.values(c.roles)) {
  const ag = A.find((x) => x.id === 'crew:' + r.key);
  for (const [k, v] of [['greeting', r.greeting], ['job', r.job], ['stops', r.stops]]) if (!ag.lines.some((l) => l.kind === k && l.text === v)) missTopics.push(r.key + ' ' + k);
  r.topics.forEach((t) => { const l = ag.lines.find((x) => x.id === t.id && x.kind === t.kind);
    if (!l || l.text !== (t.kind === 'say' ? t.say : adv.bindings[t.bind])) missTopics.push(r.key + ':' + t.id); });
}
npcs.npcs.forEach((n) => {
  const ag = A.find((x) => x.id === 'npc:' + n.id);
  n.knowledge.forEach((k, j) => { const l = ag.lines.find((x) => x.id === 'k' + j); if (!l || l.text !== k.text || l.source !== k.source) missTopics.push(n.id + ' k' + j); });
  if (!ag.lines.some((l) => l.kind === 'limits' && l.text === n.not_certification.text)) missTopics.push(n.id + ' limits');
});
ok('every advisor and crew topic (say and read), greeting, job and stop line, and every NPC knowledge and limits line is in the hive', missTopics.length === 0, missTopics.slice(0, 5));

/* ---- avatars: locker options, the nearest-character rule, the registry's own wear */
const OPTS = Object.fromEntries(av.sections.map((s) => [s.id, new Set(s.options.map((o) => o.id))]));
const OPTV = Object.fromEntries(av.sections.map((s) => [s.id, Object.fromEntries(s.options.map((o) => [o.id, o]))]));
const badCfg = A.filter((a) => Object.keys(a.avatar.cfg).sort().join() !== Object.keys(OPTS).sort().join()
  || Object.entries(a.avatar.cfg).some(([k, v]) => !OPTS[k].has(v)));
ok(`every agent wears a full locker outfit (${Object.keys(OPTS).length} sections, every value an avatars/ option id)`, badCfg.length === 0, badCfg.map((a) => a.id).slice(0, 3));
const VARY = ['build', 'skin', 'hair', 'haircolor', 'eyes', 'facialhair'];
const COMPARE = Object.keys(OPTS).filter((k) => !VARY.includes(k) && k !== 'crew');
const nearest = (cfg) => { let best = null, bn = -1; for (const c of av.characters) { const n = COMPARE.filter((k) => k in cfg && c.cfg[k] === cfg[k]).length; if (n > bn) { best = c; bn = n; } } return [best.id, bn]; };
const wearOf = (a) => a.kind === 'advisor' ? adv.advisors[a.id.slice(8)].crew : a.kind === 'crew-role'
  ? (() => { const [c, r] = a.id.slice(5).split(':'); return crews.crews[c].roles[r].wears; })() : null;
const badNear = A.filter((a) => { const w = wearOf(a) ?? a.avatar.cfg; const [id, n] = nearest(w); return id !== a.avatar.character || n !== a.avatar.shared_sections; });
ok('every agent\'s locker character is the nearest one to its wear (most equal sections, ties by locker order), re-derived here', badNear.length === 0, badNear.map((a) => a.id).slice(0, 3));
const badWear = A.filter((a) => { const w = wearOf(a); return w ? Object.entries(w).some(([k, v]) => a.avatar.cfg[k] !== v)
  : JSON.stringify(a.avatar.cfg) !== JSON.stringify(npcs.npcs.find((n) => 'npc:' + n.id === a.id).appearance.cfg); });
ok('advisors and crew roles wear exactly what their registry says; NPC outfits are npcs.json\'s, unchanged', badWear.length === 0, badWear.map((a) => a.id).slice(0, 3));
const badProxy = A.filter((a) => Object.values(a.avatar.proxy).some((p) => p && resolve(p.source) !== p.hex)
  || a.avatar.proxy.torso.hex !== OPTV.topcolor[a.avatar.cfg.topcolor].value || a.avatar.proxy.head.hex !== OPTV.skin[a.avatar.cfg.skin].value
  || JSON.stringify(resolve(a.avatar.scale.source)) !== JSON.stringify(a.avatar.scale.xyz));
ok('every portrait colour and body scale is the locker value at its source path', badProxy.length === 0, badProxy.map((a) => a.id).slice(0, 3));
ok(`the roster wears ${C.characters_used} of the locker's ${av.characters.length} characters, and each one named exists`,
  A.every((a) => av.characters.some((c) => c.id === a.avatar.character && resolve(a.avatar.character_source) === c.id)));

/* ---- AUTHORED personalities, plain tone */
const fam = auth.families;
const badPers = A.filter((a) => {
  const p = a.personality, src = a.kind === 'advisor' ? auth.advisors[a.id.slice(8)] : a.kind === 'crew-role' ? auth.crew_roles[a.id.slice(5)] : auth.npc_roles[a.role];
  const npc = a.kind === 'npc' ? npcs.npcs.find((n) => 'npc:' + n.id === a.id) : null;
  const extra = npc && npc.role === 'mentor' && npc.family ? [fam[npc.family]] : [];
  return !src || p.provenance !== 'AUTHORED' || p.tone !== 'plain' || p.style !== src.style
    || JSON.stringify(p.traits) !== JSON.stringify([...src.traits, ...extra]);
});
ok('every agent carries its AUTHORED personality (three traits, plus a family trait for a trade mentor) from hive/authored', badPers.length === 0, badPers.map((a) => a.id).slice(0, 3));
const allStyles = [...Object.values(auth.advisors), ...Object.values(auth.crew_roles), ...Object.values(auth.npc_roles)];
ok('personalities are plain: no exclamation, no quoted catchphrase, no catchphrase field, and every style is distinct',
  allStyles.every((p) => !/[!"“”]/.test(p.style) && !('catchphrase' in p) && p.traits.length === 3) && new Set(allStyles.map((p) => p.style)).size === allStyles.length);
ok(`every advisor (${Object.keys(auth.advisors).length}), crew role (${Object.keys(auth.crew_roles).length}) and NPC role (${Object.keys(auth.npc_roles).length}) is authored, and nothing else is`,
  JSON.stringify(Object.keys(auth.advisors)) === JSON.stringify(Object.keys(adv.advisors)) && JSON.stringify(Object.keys(auth.crew_roles).sort()) === JSON.stringify(roleIds.map((x) => x.slice(5)).sort())
  && JSON.stringify(Object.keys(auth.npc_roles).sort()) === JSON.stringify(Object.keys(npcs.counts.by_role).sort()));

/* ---- on-device voice profiles */
const B = auth.bounds;
const clamp = (x, lo, hi) => Math.round(Math.min(hi, Math.max(lo, x)) * 1000) / 1000;
const badVoice = A.filter((a) => {
  const v = a.voice, src = a.kind === 'advisor' ? auth.advisors[a.id.slice(8)] : a.kind === 'crew-role' ? auth.crew_roles[a.id.slice(5)] : auth.npc_roles[a.role];
  const off = a.kind === 'npc' ? (h8(a.id + ':voice') % 9 - 4) * 0.01 : 0;
  return v.engine !== 'speechSynthesis' || v.on_device_only !== true || v.lang !== 'en' || v.volume !== B.volume
    || Math.abs(v.pitch - clamp(src.voice.pitch + off, ...B.pitch)) > 1e-9 || Math.abs(v.rate - clamp(src.voice.rate + off, ...B.rate)) > 1e-9
    || v.pitch < B.pitch[0] || v.pitch > B.pitch[1] || v.rate < B.rate[0] || v.rate > B.rate[1];
});
ok(`every voice is on-device speechSynthesis in English, inside pitch ${B.pitch} and rate ${B.rate}, and equals its AUTHORED base (+ the sha256 offset for NPCs)`,
  badVoice.length === 0, badVoice.map((a) => a.id).slice(0, 3));
ok('no two advisors or crew roles share a voice (pitch, rate)', new Set(A.filter((a) => a.kind !== 'npc').map((a) => a.voice.pitch + '/' + a.voice.rate)).size === advIds.length + roleIds.length);

/* ---- K-12 play-safe */
const K = auth.k12, HOLD = new RegExp('\\b(' + K.hold_words.join('|') + ')\\b', 'i');
const badK = A.filter((a) => a.k12 !== (a.kind === 'advisor' ? K.advisors.includes(a.id.slice(8)) : a.kind === 'crew-role' ? K.crew_roles.includes(a.id.slice(5)) : K.npc_roles.includes(a.role))
  || a.lines.some((l) => l.k12 !== !HOLD.test(l.text)));
ok(`K-12: the play-safe roster (${A.filter((a) => a.k12).length}) is exactly the AUTHORED allow-list, and every line's flag is the held-word rule`, badK.length === 0, badK.map((a) => a.id).slice(0, 3));
ok('K-12: no crew role is play-safe, and every play-safe agent keeps at least one line to say', A.filter((a) => a.k12).every((a) => a.kind !== 'crew-role' && a.lines.some((l) => l.k12)));
ok(`K-12: the held-word rule withholds lines it should (${lines.filter((l) => !l.k12).length} held across the hive, e.g. the attendant's casualty line)`,
  lines.some((l) => !l.k12 && /casualt/.test(l.text)) && C.k12_lines_held === A.filter((a) => a.k12).flatMap((a) => a.lines).filter((l) => !l.k12).length);

/* ---- honesty */
const hon = Object.values(hive.honesty).join(' ');
ok('the honesty block says SCRIPTED, no AI model, the device\'s speech synthesis, never on its own, AUTHORED personalities, and play',
  /SCRIPTED/.test(hive.honesty.scripted) && /No AI model/.test(hive.honesty.no_model) && /speech synthesis/.test(hive.honesty.voice)
  && /never on its own/.test(hive.honesty.voice) && /AUTHORED/.test(hive.honesty.personality) && /certifies nothing/.test(hive.honesty.play));
const raw = readFileSync(join(ROOT, 'hive/registry/hive.json'), 'utf8') + readFileSync(join(ROOT, 'hive/authored/personalities.json'), 'utf8');
ok('no model identifier, network voice or cloud speech service is named anywhere in the hive', !/\b(gpt-\d|claude-|gemini|llama|mistral|openai|anthropic|polly|elevenlabs|wavenet|cloud tts)\b/i.test(raw + hon));

console.log(`hive/test: ${pass} checks passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
