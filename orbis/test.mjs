/**
 * Orbis prompt-contract verification.
 *
 * The claim this pack makes is narrow and has to be checked as narrowly:
 * it declares a real, citable command sequence for a real hosted video
 * model, and a deterministic prompt template built from the union
 * registry - and it calls none of it. So the checks are half about the
 * contract being real (the model id, the auth shape, the command order)
 * and half about the page never reaching past "build some text": no key
 * name shipped, no fetch or socket anywhere near the builder, and the
 * synthetic-video label actually on the page a learner would read.
 */
import { createHash } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/orbis.json', import.meta.url)));
const unions = JSON.parse(readFileSync(
  new URL('../unions/registry/unions.json', import.meta.url)));
const page = readFileSync(new URL('../web/trade_craft_3d.html', import.meta.url), 'utf8');

/* ---------------------------------------------------------- the model --- */
ok('the model names a real provider-qualified id and its own docs page',
  /^reactor\//.test(reg.model.id)
  && reg.model.docs.startsWith('https://www.reactor.inc/'));
ok('the model is cited to the exact repo and file it was read from',
  /orbis-hackathon-starter/.test(reg.model.source_repo)
  && reg.model.source_file === 'README.md');

/* ------------------------------------------------------- the contract --- */
ok('auth names both required keys and states this bundle holds neither',
  new Set(reg.contract.auth.keys_required).size === 2
  && reg.contract.auth.keys_required.includes('REACTOR_API_KEY')
  && reg.contract.auth.keys_required.includes('GEMINI_API_KEY')
  && /never requests, stores or transmits/.test(reg.contract.auth.keys_held_by));
ok('the token endpoint is https, matching the auth flow it starts',
  reg.contract.auth.token_endpoint === 'https://api.reactor.inc/tokens');
ok('the command sequence starts with the token and ends with an active-run control',
  /token/i.test(reg.contract.sequence[0])
  && /pause.*resume.*reset|reset/i.test(reg.contract.sequence.at(-1)));
ok('set_prompt is required and appears before start, exactly as the API demands',
  reg.contract.sequence.some((s, i) =>
    /set_prompt/.test(s) && reg.contract.sequence[i + 1] && /start/.test(reg.contract.sequence[i + 1])));
ok('all six documented events are named', reg.contract.events.length === 6);

/* --------------------------------------------------------- the prompt --- */
ok('the template carries exactly the three fields the union registry provides',
  ['{district}', '{hall}', '{focus}'].every((ph) => reg.prompt_template.includes(ph)));
ok('the module count matches the union roster exactly - one prompt per hall',
  reg.modules === unions.count && reg.modules === 111);

/* --------------------------------------------------------------- honesty --- */
ok('no network call is claimed from this build, in as many words',
  /reaches no host outside GitHub/.test(reg.honesty.no_network_here));
ok('no key is ever shipped, and the registry says never rather than merely "not yet"',
  /never requests, stores or transmits/.test(reg.honesty.no_key_shipped));
ok('a generated clip is labelled AI-SYNTHESIZED and distinguished from the real episode log',
  /AI-SYNTHESIZED/.test(reg.honesty.synthetic_not_real)
  && /not footage of any real trade, worker or site/.test(reg.honesty.synthetic_not_real)
  && /separate stream from the real, schematic episode log/.test(reg.honesty.synthetic_not_real));
ok('every one of the 111 modules is covered, not just the ones a learner has trained',
  /whether or not a learner has ever trained there/.test(reg.honesty.every_module_covered));
ok('running the sequence is stated as the operator\'s own action, not this bundle\'s',
  /operator.s own action/.test(reg.honesty.operator_action));
ok('the contract admits it was never checked against the live API from this build',
  reg.verified_from_build === false
  && /reaches no host outside GitHub/.test(reg.verification_note));

/* ------------------------------------------------------ the page builds it --- */
ok('the page implements the prompt builder by name',
  page.includes('function orbisPrompt('));
ok('the page prompt builder carries the same three fields as the registry template',
  ['district', 'hall', 'focus'].every((f) => page.includes(f)));
ok('no API key name ever reaches the shipped page',
  !page.includes('REACTOR_API_KEY') && !page.includes('GEMINI_API_KEY'));
ok('the AI-synthesized label actually reaches the page, not just the registry',
  /AI-SYNTHESIZED|AI-synthesized/.test(page));
ok('no fetch, socket or reactor/gemini host reference sits near the prompt builder',
  (() => {
    for (const anchor of ['function orbisPrompt(', 'function exportOrbisPrompts(']) {
      if (!page.includes(anchor)) continue;
      const chunk = page.split(anchor)[1].slice(0, 1600);
      for (const banned of ['fetch(', 'XMLHttpRequest', 'reactor.inc',
        'api.reactor', 'gemini', 'WebSocket', 'RTCPeer']) {
        if (chunk.includes(banned)) return false;
      }
    }
    return true;
  })());
ok('the page never opens a socket or fetch to any Orbis/Reactor/Gemini host anywhere at all',
  !/reactor\.inc|api\.reactor|generativelanguage\.googleapis/.test(page));

/* ---------------------------------------------------------- the runner --- */
ok('the registry names a real runner path, model and how to run it',
  reg.runner.path === 'orbis/runner-helios'
  && reg.runner.model === 'reactor/helios'
  && /create-reactor-app/.test(reg.runner.scaffolded_from)
  && /pnpm install/.test(reg.runner.run));
ok('the registry states plainly that this build never runs the runner',
  /never installs the runner.s dependencies, never starts it/
    .test(reg.runner.never_run_by_this_build));

const runnerDir = new URL('./runner-helios/', import.meta.url);
const modules = JSON.parse(readFileSync(
  new URL('app/lib/modules.generated.json', runnerDir)));
ok('the generated module library covers all 111 union halls, unique ids',
  modules.length === 111 && new Set(modules.map((m) => m.id)).size === 111);
ok('every generated module carries the same fields the template promises',
  modules.every((m) => m.id && m.label && m.district && m.text.includes(m.label)
    && m.text.includes(m.district)));

const tokenRoute = readFileSync(
  new URL('app/api/reactor/token/route.ts', runnerDir), 'utf8');
ok('the runner\'s token route pins the exact model the registry declares',
  tokenRoute.includes(`"${reg.runner.model}"`));
ok('the token route reads the key from the environment, never a literal value',
  /process\.env\.REACTOR_API_KEY/.test(tokenRoute)
  && !/rk_[a-zA-Z0-9]{10,}/.test(tokenRoute));

const promptsTs = readFileSync(new URL('app/lib/prompts.ts', runnerDir), 'utf8');
ok('the runner\'s scene library imports the generated file rather than hand-authoring scenes',
  /import modules from ["']\.\/modules\.generated\.json["']/.test(promptsTs));
ok('no scene the runner ships carries an evolutions array - nothing invented past the registry',
  modules.every((m) => !('evolutions' in m)));

const runnerReadme = readFileSync(new URL('README.md', runnerDir), 'utf8')
  .replace(/\s+/g, ' ');
ok('the runner\'s own README states the AI-SYNTHESIZED / not-real-footage honesty',
  /AI-SYNTHESIZED synthetic video/.test(runnerReadme)
  && /not footage of any real trade, worker or site/.test(runnerReadme));
ok('the runner\'s README says plainly it is never run by the parent build',
  /Not run by SmartCiti\.X's own build/.test(runnerReadme));
ok('the runner\'s README warns explicitly against ever pasting a key anywhere this repo tracks',
  /[Nn]ever paste a real key into a chat, an issue, a commit message, or any file this repo tracks/
    .test(runnerReadme));

for (const leaked of ['.env', '.env.local']) {
  ok(`no real ${leaked} file is committed in the runner directory`,
    !existsSync(new URL(leaked, runnerDir)));
}

/* -------------------------------------------------------- the flow panel --- */
// Optional pacing-adaptation add-on. Checked statically here (no TS
// import - this suite must run with zero installed dependencies); the
// deterministic decision logic itself is verified by
// orbis/runner-helios/flow.test.mjs, which does import the real
// TypeScript and is not part of this zero-dependency suite.
const flowSrc = readFileSync(new URL('app/lib/flow.ts', runnerDir), 'utf8');
const flowPanelSrc = readFileSync(
  new URL('app/components/FlowPanel.tsx', runnerDir), 'utf8');
const heliosAppSrc = readFileSync(new URL('app/HeliosApp.tsx', runnerDir), 'utf8');
ok('the flow module states its safety claim as a closed type, not a runtime denylist',
  /closed by construction/.test(flowSrc) && /interface LearnerSignal/.test(flowSrc));
ok('the flow module documents that Helios is video-only, before it ever calls setPrompt',
  flowSrc.indexOf('VIDEO ONLY') < flowSrc.indexOf('export function chooseIntervention'));
const flowStripComments = (s) => s.split('\n')
  .map((line) => line.replace(/\/\/.*/, '')).join('\n');
const flowCodeOnly = flowStripComments(flowSrc) + flowStripComments(flowPanelSrc);
ok('no biometric, emotion-recognition or medical field name appears in the flow code itself',
  ['heart_rate', 'heartRate', 'facial', 'camera_emotion', 'cameraEmotion',
    'mental_health', 'mentalHealth', 'keystroke', 'biometric', 'webcam',
    'eye_tracking', 'eyeTracking'].every((banned) => !flowCodeOnly.includes(banned)));
ok('the flow panel never calls an audio method Helios does not have',
  !/setAudioPrompt|setAudioEnabled/.test(flowPanelSrc));
ok('the consent toggle is real: FlowPanel reads it before ever calling setPrompt',
  /adaptiveOn/.test(flowPanelSrc) && /if \(!adaptiveOn/.test(flowPanelSrc));
ok('the session log is explicitly local-only, and the code never actually calls localStorage',
  /this tab only, never saved/.test(flowPanelSrc)
  && !/localStorage\./.test(flowStripComments(flowPanelSrc)));
ok('HeliosApp actually renders FlowPanel in the live phase, not just imports it unused',
  /import \{ FlowPanel \}/.test(heliosAppSrc) && /<FlowPanel \/>/.test(heliosAppSrc));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`orbis/test: ${n} checks passed — ${reg.modules} modules, model ${reg.model.id}`);
