#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the Orbis synthetic-training-data
prompt contract.

WHAT THIS IS. The training pack (`training/`) already records real,
schematic episodes from a learner's own interactions - a sim run, an
advisor answer, a walkaround check - and exports them for the org's
`ml-agents` fork. That stream is sparse: it only covers a hall once a
learner has actually practiced there. This pack adds a second, separate
stream: a deterministic PROMPT CONTRACT that turns any of the 111 union
modules (hall + district + focus, already in the union registry - no
second copy) into a text prompt for Reactor's hosted Visko Orbis Stable
API, so an operator who wants denser synthetic video for robotics-training
augmentation can generate it themselves, for any module, whether or not a
learner has ever trained there.

WHAT THIS IS NOT. This build calls no network host outside GitHub and
never will - it cannot mint a Reactor token, connect to Orbis, or call
Gemini, and ships no API key. The page this pack extends does the same:
it builds prompt TEXT locally and stops there. Generating an actual clip
is the operator's own action, run outside this bundle, against the cited
public API, with their own REACTOR_API_KEY and GEMINI_API_KEY. A clip
made that way is AI-SYNTHESIZED synthetic video - it is not footage of
any real trade, worker or site, it is not the real episode log this
bundle already records, and nothing here claims otherwise.

PROVENANCE. The model id, endpoint, auth requirement and command sequence
below are RECORDED verbatim from the Orbis hackathon starter's own README
(github.com/AGIFutureFoundation/orbis-hackathon-starter, read directly -
not cross-checked against a sibling checkout at build time, because nothing
in this pack calls that host either; `verified_from_build` says so plainly,
matching the same honest shape parcels/build.py already uses for the
imagery and elevation services).

HOW THIS PAIRS WITH training/build.py. That pack already records the
OTHER half of a robotics-training pipeline: real, schematic episode
JSON from a learner's own sim runs, advisor answers and walkaround
checks, exported toward the org's `ml-agents` fork. This pack's clips
are a different input to the SAME goal, not a rival to it - an
AI-SYNTHESIZED video for a module a learner may never have practiced,
versus a SCHEMATIC episode log for one they actually did. An operator
combining both feeds one training pipeline two complementary streams
for the same 111 union modules; neither stream claims to be the other,
and this build still runs neither pipeline itself.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "3.3.0"
BUILT = "2026-09-12"

# ------------------------------------------------------------- the model ---
MODEL = {
    'id': 'reactor/visko-orbis-stable',
    'provider': 'Reactor (public Visko Orbis Stable API)',
    'docs': 'https://www.reactor.inc/models/visko-orbis-stable/api',
    'source_repo': 'github.com/AGIFutureFoundation/orbis-hackathon-starter',
    'source_file': 'README.md',
}

# ---------------------------------------------------------- the contract ---
# The command sequence, RECORDED verbatim from the starter's own "API
# flow" section. Auth is two operator-supplied keys, kept server-side by
# the operator's own deployment of that starter - never requested, held
# or transmitted by this bundle.
CONTRACT = {
    'auth': {
        'token_endpoint': 'https://api.reactor.inc/tokens',
        'keys_required': ['REACTOR_API_KEY', 'GEMINI_API_KEY'],
        'keys_held_by': "the operator's own deployment of the Orbis "
                        'starter, server-side only - this bundle never '
                        'requests, stores or transmits either key',
    },
    'sequence': [
        'POST /api/token mints a scoped session JWT from the token endpoint',
        'connect to the model with recv-only main_video and main_audio tracks',
        'read the state snapshot; treat its available_resolutions as authoritative',
        'set_image (optional) to supply a reference frame before start',
        'set_resolution (optional) to stage a delivery tier for the next start',
        'set_prompt (required) supplies the prompt text this pack builds',
        'start begins generation; another set_prompt steers it mid-run',
        'pause / resume / reset control an active generation',
    ],
    'chunking': 'chunks emit roughly every 1.8 seconds; the first chunk '
               'carries no frames while the upscaler primes',
    'events': ['state', 'prompt_accepted', 'resolution_accepted',
               'generation_started', 'chunk_complete', 'command_error'],
}

# -------------------------------------------------------- the prompt text ---
# One deterministic template, in Python and in the page, kept to the same
# string so neither can drift from the other. Every placeholder resolves
# against the union registry this build already ships - no fact is
# authored twice.
PROMPT_TEMPLATE = (
    'A {district} apprentice practicing {hall}: {focus}. Training-yard '
    'setting, full PPE visible, single continuous take, documentary '
    'style, no on-screen text.'
)

# ------------------------------------------------------- the real runners ---
# Two SEPARATE things from everything above: real, runnable companion
# apps - not a contract, an actual integration - each scaffolded from
# Reactor's own `create-reactor-app` templates
# (github.com/reactor-team/create-reactor-app, Apache-2.0, LICENSE and
# NOTICE carried into each runner directory unchanged) and checked into
# this repo at each entry's 'path'. They target two different models -
# `reactor/helios` (video only) and `reactor/visko-orbis-stable` (video
# + real audio + resolution tiers, the same model MODEL above names) -
# because that is the model each template pins its own token to
# (app/api/reactor/token/route.ts). Each runner's scene library
# (app/lib/prompts.ts) is generated by THIS build from the same union
# registry every other fact in this pack comes from, written to that
# entry's 'modules_file' - one source of truth, two consumers.
#
# The honesty line this bundle draws everywhere else still holds for
# both runners: neither runs, nor is invoked, from this repository's own
# build or verify pipeline. Each is a real Next.js app an operator
# installs and runs themselves, with their own REACTOR_API_KEY, on their
# own machine. This build does not exercise either, does not install
# either's dependencies, and does not hold - or ever request - that key.
RUNNERS = [
    {
        'path': 'orbis/runner-helios',
        'model': 'reactor/helios',
        'scaffolded_from': 'github.com/reactor-team/create-reactor-app '
                           '(templates/helios), Apache-2.0',
        'modules_file': 'app/lib/modules.generated.json',
        'run': 'cd orbis/runner-helios && cp .env.example .env.local && '
              '# put a REACTOR_API_KEY you generated yourself into '
              '.env.local && pnpm install && pnpm dev',
        'never_run_by_this_build': 'this repository\'s own build and '
                                   'verify pipeline never installs the '
                                   'runner\'s dependencies, never starts '
                                   'it, and never holds a REACTOR_API_KEY '
                                   '- it only keeps the runner\'s '
                                   'generated module library in sync '
                                   'with the union registry',
    },
    {
        'path': 'orbis/runner-visko-orbis-stable',
        'model': 'reactor/visko-orbis-stable',
        'scaffolded_from': 'github.com/reactor-team/create-reactor-app '
                           '(templates/visko-orbis-stable), Apache-2.0',
        'modules_file': 'app/lib/modules.generated.json',
        'run': 'cd orbis/runner-visko-orbis-stable && cp .env.example '
              '.env.local && # put a REACTOR_API_KEY you generated '
              'yourself into .env.local && pnpm install && pnpm dev',
        'never_run_by_this_build': 'this repository\'s own build and '
                                   'verify pipeline never installs the '
                                   'runner\'s dependencies, never starts '
                                   'it, and never holds a REACTOR_API_KEY '
                                   '- it only keeps the runner\'s '
                                   'generated module library in sync '
                                   'with the union registry',
    },
]

HONESTY = {
    'no_network_here': 'this build reaches no host outside GitHub, and '
                       'the page it extends calls no network host at '
                       'all: it builds prompt text locally and stops - '
                       'generating an actual clip happens outside this '
                       'bundle, on the operator\'s own Orbis deployment',
    'no_key_shipped': 'this bundle never requests, stores or transmits a '
                      'REACTOR_API_KEY or a GEMINI_API_KEY',
    'synthetic_not_real': 'a clip generated from one of these prompts is '
                          'AI-SYNTHESIZED synthetic video - it is not '
                          'footage of any real trade, worker or site, and '
                          'it is a separate stream from the real, '
                          'schematic episode log training/ already '
                          'records from a learner\'s own interactions',
    'every_module_covered': 'the prompt builder works from the union '
                            'registry, not the training log, so every '
                            'one of the 111 modules has a prompt whether '
                            'or not a learner has ever trained there',
    'operator_action': 'running the sequence above against a real prompt '
                       'is the operator\'s own action, with their own '
                       'keys, against the cited public API - this pack '
                       'declares the contract, it does not exercise it',
}

# ---------------------------------------------------------------- checks ---
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))
unions_reg = json.load(open(ROOT / 'unions/registry/unions.json'))
districts_reg = json.load(open(ROOT / 'unions/registry/districts.json'))

assert unions_reg['count'] == 111, 'a prompt per module means 111 modules'
for ph in ('{district}', '{hall}', '{focus}'):
    assert ph in PROMPT_TEMPLATE, f'the template is missing {ph}'
assert MODEL['id'].startswith('reactor/'), 'the model id must name its provider'
assert CONTRACT['auth']['token_endpoint'].startswith('https://'), \
    'the token endpoint must be https'
assert set(CONTRACT['auth']['keys_required']) == \
    {'REACTOR_API_KEY', 'GEMINI_API_KEY'}, 'the two required keys must be named'
assert len(CONTRACT['sequence']) >= 6, 'the command sequence looks incomplete'
assert 'never' in HONESTY['no_key_shipped'], \
    'the honesty note must state plainly that no key is shipped'
assert 'AI-SYNTHESIZED' in HONESTY['synthetic_not_real'], \
    'a synthetic clip must be labelled as such, in as many words'

# the runner's scene library - built once, here, from the union roster
MODULES = [
    {'id': u['slug'], 'label': u['name'],
     'district': districts_reg['districts'][u['district']]['name'],
     'text': PROMPT_TEMPLATE.format(
         district=districts_reg['districts'][u['district']]['name'],
         hall=u['name'], focus=u['focus'])}
    for u in unions_reg['unions']
]
assert len(MODULES) == 111, 'the runner scene library must cover all 111 modules'
assert len({m['id'] for m in MODULES}) == 111, 'every module id must be unique'

runners_present = []
for runner in RUNNERS:
    runner_dir = ROOT / runner['path']
    if not runner_dir.is_dir():
        continue
    assert (runner_dir / 'app/api/reactor/token/route.ts').exists(), \
        f"{runner['path']} exists but is missing its token route"
    token_route = (runner_dir / 'app/api/reactor/token/route.ts').read_text()
    assert f'"{runner["model"]}"' in token_route, \
        f"{runner['path']}'s token route must pin the model this entry declares"
    # referencing REACTOR_API_KEY by NAME is normal and necessary (the app
    # reads it from the operator's own environment) - what must never
    # happen is an actual populated secrets file checked into the repo
    for leaked in ('.env', '.env.local'):
        assert not (runner_dir / leaked).exists(), \
            f"a real {leaked} file must never be committed to {runner['path']}"
    modules_out = runner_dir / runner['modules_file']
    modules_out.parent.mkdir(parents=True, exist_ok=True)
    modules_out.write_text(json.dumps(MODULES, indent=1) + '\n')
    runners_present.append(runner)

BOOTSTRAP = '--bootstrap' in __import__('sys').argv
if not BOOTSTRAP:
    page = (ROOT / 'web/trade_craft_3d.html').read_text()
    assert 'function orbisPrompt(' in page, \
        'the page does not implement the Orbis prompt builder'
    for ph in ('{district}', '{hall}', '{focus}'):
        assert ph.strip('{}') in page, \
            f'the page prompt builder is missing the {ph} field'
    # never a network call anywhere near the prompt builder or its export
    for anchor in ('function orbisPrompt(', 'function exportOrbisPrompts('):
        if anchor in page:
            chunk = page.split(anchor, 1)[1][:1600]
            for banned in ('fetch(', 'XMLHttpRequest', 'reactor.inc',
                           'api.reactor', 'gemini', 'WebSocket', 'RTCPeer'):
                assert banned not in chunk, \
                    f'a prompt-builder code path near "{anchor}" reaches the network ({banned})'
    assert 'REACTOR_API_KEY' not in page and 'GEMINI_API_KEY' not in page, \
        'no key name may appear in the shipped page - nothing here holds one'
    assert 'AI-SYNTHESIZED' in page or 'AI-synthesized' in page.replace(
        'AI-SYNTHESIZED', 'AI-synthesized'), \
        'the synthetic-video honesty label must actually reach the page'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-orbis-prompts',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'model': MODEL,
    'contract': CONTRACT,
    'prompt_template': PROMPT_TEMPLATE,
    'modules': unions_reg['count'],
    'runners': RUNNERS,
    'honesty': HONESTY,
    'verified_from_build': False,
    'verification_note': 'this build reaches no host outside GitHub and '
                         'npm/pypi, so the contract above is carried as '
                         'RECORDED from the cited README rather than '
                         "re-checked against Reactor's live API on every "
                         'build',
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'orbis.json').write_text(json.dumps(doc, indent=1) + '\n')
if runners_present:
    names = ', '.join(r['path'].rsplit('/', 1)[-1] for r in runners_present)
    runner_note = f", runner scene libraries synced ({len(MODULES)} " \
                  f"modules each): {names}"
else:
    runner_note = ", no runners present in this checkout"
print(f"orbis registry: prompt contract for {unions_reg['count']} union "
      f"modules, model {MODEL['id']}{runner_note} (source stamp {stamp})")
