#!/usr/bin/env python3
"""reactor/build.py - the Reactor (live world model) registry.

Writes reactor/registry/reactor.json and reactor/config.mjs (the same object, importable by the
Worker route reactor/route.mjs). Everything here is AUTHORED configuration or a pin recorded from
the npm registry; nothing is measured. Reactor is NOT LIVE: no key is deployed with the Worker in
this repo, and api.reactor.inc is unreachable from the build environment, so no request to it has
ever been made from here.

The API key never appears in this file, the registry, the pages or the tests. It lives only in a
Worker secret (`wrangler secret put REACTOR_API_KEY`) or, for `wrangler dev`, in the gitignored
cloudflare/worker/.dev.vars.

  python3 reactor/build.py
"""
import hashlib
import os
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'reactor' / 'registry' / 'reactor.json'
MJS = ROOT / 'reactor' / 'config.mjs'

# Pinned from registry.npmjs.org (dist.integrity of the exact version).
SDK = {
    'package': '@reactor-team/js-sdk',
    'version': '3.0.2',
    'license': 'Apache-2.0',
    'integrity': 'sha512-h13EP2WpFXS/qbC7l3HGkfSibN/Gk1WPZou25kwHNtt04bj8JtqzoP/Kupn3/3tV997RHXApANoO6Bie7TssLg==',
    'vendor_dir': 'web/vendor/reactor',
    'entry': 'index.js',
    'import_map': {
        'react': 'shims/react.js',
        'react/jsx-runtime': 'shims/react-jsx-runtime.js',
        'awaitqueue': 'shims/awaitqueue.js',
        'hls.js': 'shims/unavailable.js',
        'mp4box': 'shims/unavailable.js',
    },
    'import_map_why': 'the SDK module imports these bare names; the imperative Reactor class needs only a serial '
                      'queue (awaitqueue). React components, HLS clip playback and MP4 remuxing are not used here, so '
                      'those names resolve to AUTHORED shims that refuse if called.',
    'used_api': ['Reactor', 'connect', 'disconnect', 'on', 'off', 'getSchema', 'getCapabilities', 'sendCommand',
                 'uploadFile', 'getStatus'],
}

# The model catalogue is the PUBLISHED @reactor-models npm scope, snapshotted by reactor/fetch_catalogue.py into
# reactor/catalogue_npm.json (name, version, licence, integrity, and the MODEL_NAME(S) and sendCommand wire names
# read from each sha512-checked tarball). Nothing about a model is typed here. The page still sends only the
# commands the connected model declares at run time (getCapabilities()/getSchema()).
CATALOGUE = ROOT / 'reactor' / 'catalogue_npm.json'
ORBIS = ROOT / 'orbis' / 'registry' / 'orbis.json'

# The ONE model the Worker mints tokens for and the page connects to. Operator-selectable at build time:
#   REACTOR_MODEL=reactor/helios python3 reactor/build.py   (then rebuild the pages that mount web/reactorkit.py)
# An unset REACTOR_MODEL means DEFAULT_MODEL; a name outside the catalogue stops the build.
DEFAULT_MODEL = 'reactor/lingbot-world-2'
MODEL_WHY = ('default: a world model steered by camera move/look commands fits walking a place. Its typed package '
             'is read, not vendored: it is a thin wrapper that calls sendCommand with the wire names recorded here, and '
             'the base SDK plus a runtime schema check sends the same commands without a second vendored package.')

TOKEN = {
    'endpoint': '/api/reactor/token',
    'secret_env': 'REACTOR_API_KEY',
    'origin_env': 'SITE_ORIGIN',
    'upstream': 'https://api.reactor.inc/tokens',
    'key_header': 'Reactor-API-Key',
    'body_max_bytes': 256,
    'jwt_max_chars': 8192,
    # AUTHORED scope: one model, one session at a time, five minutes. A leaked token can start at
    # most this and act only on the sessions it created (per the SDK README).
    'constraints': {'max_sessions': 1, 'max_session_duration_seconds': 300},
    'constraints_note': 'max_session_duration_seconds is named in the SDK README; its placement inside '
                        '`constraints` follows the README example and is unverified against the live API (blocked here).',
    'reply': 'only {"jwt": "..."} - nothing from the upstream reply but the jwt string',
}

RATE_LIMIT = {
    'applies_to': '/api/reactor/token',
    'kind': 'token bucket in KV per hashed client IP - the payments limiter (payments/worker.mjs takeToken), reused',
    'max_env': 'RATE_LIMIT_REACTOR_MAX',
    'window_env': 'RATE_LIMIT_REACTOR_WINDOW_S',
    'salt_env': 'RATE_LIMIT_SALT',
    'ip_header': 'cf-connecting-ip',
    'kv_binding': 'PAYMENTS_KV',
    'limits': 'set by the operator in env; no limit is policy in this repo',
}

SESSION = {
    'one_at_a_time': True,
    'max_seconds': TOKEN['constraints']['max_session_duration_seconds'],
    'disconnect_on_hidden': True,
    'sdk_loaded': 'only on Connect (dynamic import) - a page with the panel off loads no SDK byte',
    'stats_fields': ['rtt', 'packetLossRatio', 'framesPerSecond'],
}

# The context bridge: world state -> model commands. Each field is typed and capped; the prompt is
# composed from an AUTHORED template. A command is sent only when the connected model declares it.
BRIDGE = {
    'fields': {
        'place': {'type': 'string', 'max_chars': 80, 'what': 'parish, landmark or hall the learner is in'},
        'time_of_day': {'type': 'enum', 'values': ['dawn', 'day', 'dusk', 'night'], 'what': 'the world clock'},
        'path': {'type': 'string', 'max_chars': 60, 'what': 'the trade path being walked'},
        'lesson': {'type': 'string', 'max_chars': 80, 'what': 'the lesson title on screen'},
    },
    # ordered parts: `place` is required; every other clause is added only when the host supplies that field
    'prompt_parts': [
        {'field': 'place', 'required': True, 'text': 'A walk through {place}'},
        {'field': 'time_of_day', 'required': False, 'text': ' at {time_of_day}'},
        {'field': 'path', 'required': False, 'text': ', seen by an apprentice on the {path} path'},
        {'field': 'lesson', 'required': False, 'text': ' studying {lesson}'},
    ],
    'prompt_end': '.',
    'prompt_provenance': 'AUTHORED template; the words are the page\'s own labels, never learner input',
    'commands': {
        'prompt': {'command': 'set_prompt', 'param': 'prompt'},
        'image': {'command': 'set_image', 'param': 'image', 'from': 'a still of the world canvas the host page supplies, uploaded with uploadFile()'},
        'start': {'command': 'start'},
        'forward': {'command': 'set_move_longitudinal', 'param': 'move_longitudinal', 'on': 'forward', 'off': 'idle'},
        'back': {'command': 'set_move_longitudinal', 'param': 'move_longitudinal', 'on': 'back', 'off': 'idle'},
        'left': {'command': 'set_look_horizontal', 'param': 'look_horizontal', 'on': 'left', 'off': 'idle'},
        'right': {'command': 'set_look_horizontal', 'param': 'look_horizontal', 'on': 'right', 'off': 'idle'},
    },
    'gate': 'a command is sent only if its name is declared by getCapabilities().commands or getSchema().paths at run time',
}

HONESTY = {
    'model_output': 'Generated video is model output, not real footage and not a record of any real place.',
    'not_live': 'Reactor is not live until an operator deploys the Worker with the REACTOR_API_KEY secret.',
    'untested': 'api.reactor.inc is unreachable from the environment that built this; the token route is tested '
                'only against a mocked fetch and no live session has been opened from here.',
    'play': 'The live view is play: it never enters a completion record and certifies nothing.',
    'no_key_in_browser': 'The page never takes, stores or sees an API key; it asks this site\'s Worker for a short-lived token.',
}

OPERATOR = [
    'Credits are spent only by the DEPLOYED Worker: each Connect mints one scoped token and runs one session against api.reactor.inc. Nothing in this repository, its build or its tests can spend credits - api.reactor.inc is blocked from the environment that built it.',
    'Pick the model: `REACTOR_MODEL=<model_name from models[]> python3 reactor/build.py`, then rebuild the pages that mount the panel; the Worker and the page read the same registry value.',
    'Production: `cd cloudflare/worker && wrangler secret put REACTOR_API_KEY` and paste the key at the prompt (it is stored encrypted by Cloudflare, never in a file).',
    'Local: put `REACTOR_API_KEY=...` in cloudflare/worker/.dev.vars (gitignored; `chmod 600`); `wrangler dev` reads it.',
    'Set plain vars RATE_LIMIT_REACTOR_MAX and RATE_LIMIT_REACTOR_WINDOW_S (RATE_LIMIT_SALT, SITE_ORIGIN and the PAYMENTS_KV binding are shared with payments).',
    'Never paste the key into a page, a registry, a test or a commit; `node reactor/test.mjs` scans every tracked file for one.',
]


class ReactorError(Exception):
    pass


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise ReactorError(f'reactor: {where} has no {k}')
    return d[k]


def catalogue():
    if not CATALOGUE.is_file():
        raise ReactorError('reactor: reactor/catalogue_npm.json is missing - run python3 reactor/fetch_catalogue.py')
    cat = json.loads(CATALOGUE.read_text())
    orb = json.loads(ORBIS.read_text()) if ORBIS.is_file() else None
    runners = {}
    if orb is not None:
        for r in need(orb, 'runners', 'orbis registry'):
            runners[need(r, 'model', 'orbis runner')] = need(r, 'path', 'orbis runner')
    models = []
    for p in need(cat, 'packages', 'catalogue'):
        for mn in need(p, 'model_names', p['npm_package']):
            rp = runners[mn] if mn in runners else None
            models.append({
                'model_name': mn,
                'npm_package': need(p, 'npm_package', 'package'), 'npm_version': need(p, 'npm_version', mn),
                'npm_license': need(p, 'npm_license', mn), 'npm_integrity': need(p, 'npm_integrity', mn),
                'npm_description': need(p, 'description', mn),
                'wire_commands': need(p, 'wire_commands', mn),
                'bridge_ready': 'set_prompt' in need(p, 'wire_commands', mn),
                'orbis_runner': rp,
                'orbis_note': (f'the orbis/ pack runs this model in {rp} (operator-run app, its own key)' if rp else
                               'no orbis/ runner for this model id'),
                'source': 'npm ' + p['npm_package'] + '@' + p['npm_version'] + ': model name(s) and wire commands read from its tarball dist',
            })
    notes = []
    for term, hits in need(cat, 'searched_for', 'catalogue').items():
        if hits:
            raise ReactorError(f'reactor: catalogue search for {term} found {hits} - review and record them as models')
        notes.append(f'{term}: not found in the @reactor-models catalogue (npm, {need(cat, "fetched", "catalogue")})')
    return cat, models, notes, runners


def build():
    cat, MODELS, notes, runners = catalogue()
    MODEL = os.environ['REACTOR_MODEL'] if 'REACTOR_MODEL' in os.environ else DEFAULT_MODEL
    names = [m['model_name'] for m in MODELS]
    if MODEL not in names:
        raise ReactorError(f'reactor: model {MODEL} is not in the published catalogue {names}')
    if DEFAULT_MODEL not in names:
        raise ReactorError(f'reactor: DEFAULT_MODEL {DEFAULT_MODEL} is not in the published catalogue')
    for mn in runners:
        if mn not in names:
            raise ReactorError(f'reactor: orbis/ runner model {mn} is not in the published catalogue')
    model = [m for m in MODELS if m['model_name'] == MODEL][0]
    if not model['bridge_ready']:
        raise ReactorError(f'reactor: {MODEL} sends no set_prompt, so the world bridge cannot drive it; pick a model '
                           f'with bridge_ready: {[m["model_name"] for m in MODELS if m["bridge_ready"]]}')
    bridge = dict(BRIDGE)
    bridge['commands'] = {k: c for k, c in BRIDGE['commands'].items() if c['command'] in model['wire_commands']}
    bridge['dropped_for_model'] = sorted(k for k, c in BRIDGE['commands'].items() if c['command'] not in model['wire_commands'])
    for part in BRIDGE['prompt_parts']:
        if part['field'] not in BRIDGE['fields'] or '{' + part['field'] + '}' not in part['text']:
            raise ReactorError(f'reactor: prompt part {part} does not name its own field')
    if not BRIDGE['prompt_parts'][0]['required']:
        raise ReactorError('reactor: the first prompt part (place) must be required')
    if SESSION['max_seconds'] != TOKEN['constraints']['max_session_duration_seconds']:
        raise ReactorError('reactor: session cap differs from the token constraint')
    doc = {
        'pack': 'reactor', 'brand': 'REACTOR·Live World Models', 'provenance': 'AUTHORED', 'live': False,
        'status': 'Reactor is not live: no key is deployed with this Worker',
        'sdk': SDK, 'catalogue': {'scope': cat['scope'], 'fetched': cat['fetched'], 'source': cat['source'],
                                  'packages': len(cat['packages']), 'snapshot': 'reactor/catalogue_npm.json'},
        'models': MODELS, 'default_model': DEFAULT_MODEL, 'model': MODEL, 'model_why': MODEL_WHY,
        'model_select': 'REACTOR_MODEL=<model_name> python3 reactor/build.py (unset = default_model)',
        'notes': notes,
        'token': TOKEN, 'rate_limit': RATE_LIMIT, 'session': SESSION, 'bridge': bridge,
        'honesty': HONESTY, 'operator': OPERATOR,
        'related': {'orbis/': 'the Orbis pack builds prompt TEXT for Reactor\'s Visko Orbis Stable and points to operator-run apps '
                              '(orbis/runner-*); it never mints a token. This pack is the in-page live view and its token route.'},
    }
    body = json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False)
    doc['source_stamp'] = hashlib.sha256(body.encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    OUT.write_text(text)
    MJS.write_text('// GENERATED by reactor/build.py from the same object as registry/reactor.json. Do not edit.\n'
                   'export default ' + text.rstrip('\n') + ';\n')
    print(f'reactor: wrote {OUT.relative_to(ROOT)} + {MJS.relative_to(ROOT)} (model {MODEL}, stamp {doc["source_stamp"][:16]})')


if __name__ == '__main__':
    try:
        build()
    except ReactorError as e:
        sys.exit(str(e))
