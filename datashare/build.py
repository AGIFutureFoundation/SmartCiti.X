#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy - the data commons (DATASHARE, wave 11).

WHAT WAS MISSING. contrib/ fixes the shape of ONE shared package
(tc-contribution/1 and, since wave 11, /2 with robotics world episodes) and
verifies it. Nothing turned many verified packages into a DATASET a
maintainer could train on: one manifest, per-episode digests, duplicates
removed, a deterministic train/val/test split, provenance per episode, a
licence and consent-scope check across packages, a revocation list that is
honoured, an analysis of what the data covers and what it misses, and a
datasheet-style card. This pack declares that shape (`tc-dataset/1`), and
writes the one registry the tools read:

  datashare/build_dataset.mjs   packages -> dataset dir + manifest + card (node CLI)
  datashare/analyse.mjs         counts, success rates, range checks, missing
                                fields, outliers, coverage gaps (node CLI)
  datashare/core.mjs            the pure core both CLIs and the contribute page run
                                (DATASHARE_CORE markers, lifted byte-for-byte)
  datashare/intake.mjs          a Worker route module: POST one package, validate
                                it with the contrib verifier core, and store it in
                                R2 under its digest. OFF by default, NOT deployed.
  datashare/intake_core.mjs     GENERATED here: the contrib verifier core, the
                                sign-in page's AUTH-CORE recovery and the
                                registries, carried verbatim so the Worker runs
                                the same rules as `node contrib/verify.mjs`.

WHAT IT IS NOT. Nothing is uploaded by this bundle: the intake route is
written and tested against mocks, disabled unless DATASHARE_INTAKE is "on",
and not deployed. No model has been trained on any dataset this builds
(training/ and robotics/ say so and this registry repeats it). The shapes
are "shaped after" datasheet and episode-dataset practice; no compatibility
with RLDS, LeRobot or ML-Agents files is claimed - no round-trip test exists.

PROVENANCE. DERIVED: record tags, episode kinds, the privacy rule, licence and
scopes are READ from contrib/registry/contrib.json; env facts from it and from
robotics/registry/robotics.json. AUTHORED here: the split ratios, the dataset
card template, the best-practice list (each item names the code that enforces
it), the intake limits. Fail closed: a missing field stops the build by name.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'datashare.json'
CORE_OUT = HERE / 'intake_core.mjs'
BUILT = '2026-09-29'


class DatashareError(Exception):
    pass


def req(mapping, key, who):
    if not isinstance(mapping, dict) or key not in mapping:
        raise DatashareError(f'{who}: {key!r} does not resolve')
    return mapping[key]


CONTRIB_PATH = 'contrib/registry/contrib.json'
TRAINING_PATH = 'training/registry/training.json'
ROBOTICS_PATH = 'robotics/registry/robotics.json'
MANIFEST_PATH = 'pack/manifest.json'
VERIFY_PATH = 'contrib/verify.mjs'
SIGNIN_PATH = 'web/trade_craft_signin.html'

load = lambda rel: json.loads((ROOT / rel).read_text(encoding='utf-8'))
CONTRIB = load(CONTRIB_PATH)
TRAINING = load(TRAINING_PATH)
ROBOTICS = load(ROBOTICS_PATH)
MANIFEST = load(MANIFEST_PATH)
PRODUCT = req(MANIFEST, 'product', MANIFEST_PATH)
PACK_VERSION = req(MANIFEST, 'pack_version', MANIFEST_PATH)
if req(CONTRIB, 'pack_version', CONTRIB_PATH) != PACK_VERSION:
    raise DatashareError(f'{CONTRIB_PATH}: pack_version disagrees with {MANIFEST_PATH}')

TAG_V1 = req(CONTRIB, 'record_tag', CONTRIB_PATH)
TAG_V2 = req(CONTRIB, 'record_tag_current', CONTRIB_PATH)
RECORD_TAGS = req(CONTRIB, 'record_tags', CONTRIB_PATH)
CONSENT = req(CONTRIB, 'consent', CONTRIB_PATH)
SCOPES = sorted(req(CONSENT, 'scopes', CONTRIB_PATH + '#consent').keys())
LICENSE = req(req(CONSENT, 'license', CONTRIB_PATH + '#consent'), 'spdx', CONTRIB_PATH + '#consent.license')
PRIVACY = req(CONTRIB, 'privacy', CONTRIB_PATH)
ORIGIN = req(CONTRIB, 'origin', CONTRIB_PATH)
WORLD_ENVS = req(req(CONTRIB, 'world_envs', CONTRIB_PATH), 'envs', CONTRIB_PATH + '#world_envs')
POSE_LEN = req(req(CONTRIB, 'world_envs', CONTRIB_PATH), 'pose_len_by_medium', CONTRIB_PATH + '#world_envs')
WORLD_KINDS = req(CONTRIB, 'world_episode_kinds', CONTRIB_PATH)
EPISODE_KINDS = req(CONTRIB, 'episode_kinds', CONTRIB_PATH)
FIELDS_BY_KIND = {k: req(v, 'fields', k) for k, v in EPISODE_KINDS.items()}
FIELDS_BY_KIND.update({k: req(v, 'fields', k) for k, v in WORLD_KINDS.items()})
NO_AGENT = req(req(CONTRIB, 'honesty', CONTRIB_PATH), 'no_agent_trained', CONTRIB_PATH + '#honesty')
ROBO_HONESTY = req(ROBOTICS, 'honesty', ROBOTICS_PATH)
TRAINED = req(ROBO_HONESTY, 'trained', ROBOTICS_PATH + '#honesty')
FORMATS = req(ROBO_HONESTY, 'formats', ROBOTICS_PATH + '#honesty')
CLASSROOM = req(ORIGIN, 'classroom_from', CONTRIB_PATH + '#origin')
SIM_SEAT_ENVS = sorted(e for e, v in req(ROBOTICS, 'envs', ROBOTICS_PATH).items() if req(v, 'runner', e) == 'sim-seat')
EMBODIMENTS = req(ROBOTICS, 'embodiments', ROBOTICS_PATH)

# per-env ranges the analysis holds samples to: observation v / w and the
# action fields, read from robotics.json through contrib.json#world_envs
RANGES = {}
for eid, e in WORLD_ENVS.items():
    obs = {o['name']: [req(o, 'low', eid), req(o, 'high', eid)] for o in req(e, 'observation', eid)}
    for need_obs in ('pose_e', 'pose_n', 'yaw', 'v', 'w'):
        if need_obs not in obs:
            raise DatashareError(f'{CONTRIB_PATH}#world_envs.envs.{eid}.observation lacks {need_obs!r}')
    RANGES[eid] = {
        'pose': [obs['pose_e'], obs['pose_n'], obs['yaw']] + ([obs['depth']] if req(e, 'medium', eid) == 'water' else []),
        'vel': [obs['v'], obs['w']],
        'a': [[req(a, 'low', eid), req(a, 'high', eid)] for a in req(e, 'action_ranges', eid)],
        'a_names': req(e, 'action_fields', eid),
        'seeds': req(e, 'seeds', eid),
        'embodiments': req(e, 'embodiments', eid),
        'medium': req(e, 'medium', eid),
    }
    if req(e, 'medium', eid) == 'water' and 'depth' not in obs:
        raise DatashareError(f'{eid}: a water env declares no depth observation')

DATASET_TAG = 'tc-dataset/1'
SPLIT = {
    'ratios': {'train': 80, 'val': 10, 'test': 10},
    'by': 'episode id = SHA-256 of the canonical JSON of the episode (the same canonical form contrib/ digests)',
    'rule': 'bucket = first 8 hex digits of SHA-256("split:" + episode id) as an integer mod 100; bucket < 80 -> train, '
            '< 90 -> val, else test. Deterministic: the same episode lands in the same split in every build, on every '
            'machine, whatever else is in the dataset, so adding packages never moves an episode between splits.',
    'provenance': 'AUTHORED ratios',
}
DEDUPE = {
    'by': 'episode id (content digest). Two packages carrying byte-identical episodes (after canonicalisation) '
          'contribute it once; the manifest keeps every package the episode came from, first one first.',
    'package_dedupe': 'a package whose digest.hex was already admitted is skipped as a duplicate, by name',
}
LICENCE_RULE = {
    'dataset_licence': LICENSE,
    'compatible': [LICENSE],
    'rule': 'every admitted package must carry consent.license ' + LICENSE + ' (contrib/ fixes one licence for every '
            'package); a package under any other id is refused by name, so the dataset licence is that one licence '
            'and its attribution list names every admitted package by digest (and wallet address, when signed)',
    'attribution': 'unsigned packages are attributed as "unsigned package <digest16>"; contributor.claimed is never '
                   'copied into a dataset, because a label a person typed may be their name',
}
SCOPE_RULE = {
    'scopes': SCOPES,
    'rule': 'a dataset is built FOR one declared scope; a package is admitted only if its consent.scope includes it, '
            'otherwise it is refused by name (consent-scope)',
}
REVOCATION = {
    'file': 'datashare/revocations.json',
    'shape': '{"record": "tc-revocations/1", "packages": [digest hex], "episodes": [episode id]}',
    'rule': 'a package digest or an episode id on the list is excluded from every later build, by name, and the '
            'manifest records how many were excluded and why. It cannot recall a copy already given away: those are '
            'governed by the licence.',
    'how_to_ask': 'a contributor who holds the package file can name its digest (printed by contrib/verify.mjs); no '
                  'account and no server exist, so the maintainer of a dataset copy honours the list at build time',
}
REFUSALS = {
    'verifier': 'the package fails contrib/verify.mjs (any rule); the first failing rule is named',
    'privacy': 'an episode carries a forbidden key (' + ', '.join(sorted(k for ks in req(PRIVACY, 'forbidden_keys', 'privacy').values() for k in ks)[:6])
               + ', ...), an email-shaped string or free text - the same scan contrib.json#privacy declares, applied '
                 'to /1 packages too',
    'classroom': 'a /2 package whose origin.classroom_mode is not false (the verifier refuses it first)',
    'licence': LICENCE_RULE['rule'],
    'consent-scope': SCOPE_RULE['rule'],
    'revoked': REVOCATION['rule'],
    'duplicate': DEDUPE['package_dedupe'],
}

MANIFEST_SHAPE = {
    'record': DATASET_TAG,
    'built_at': 'ISO-8601, passed in by the caller (the CLI takes --built-at; default is refused: no clock is read)',
    'scope': 'the one consent scope this dataset is built for',
    'licence': LICENSE,
    'schema_versions': '{package record tags admitted, episode kinds with their field lists and world kind version, '
                       'robotics schema and contract version, contrib source_stamp}',
    'packages': '[{digest, record, signed, attribution, episodes, admitted_episodes}]',
    'episodes': '[{id, kind, split, env|sim, actor, provenance: {package, index, t}}]',
    'splits': '{train: n, val: n, test: n}',
    'refused': '[{package, reason, detail}]',
    'excluded': '{revoked_packages, revoked_episodes, duplicate_episodes}',
    'digest': 'SHA-256 over the canonical manifest without digest - so a card can name the exact manifest it describes',
}

# BEST PRACTICES: each row names the code that enforces it. A practice the
# code does not enforce is not listed. datashare/test.mjs holds every
# `enforced_by` to a real file and a string that occurs in it.
BEST_PRACTICES = [
    {'practice': 'schema versioning', 'what': 'every package names its record tag (tc-contribution/1 or /2), every world '
     'episode its kind version v, the dataset its tag tc-dataset/1 and the schema versions it admitted',
     'enforced_by': {'file': 'contrib/verify.mjs', 'marker': 'record is ${JSON.stringify(record.record)}, not'}},
    {'practice': 'integrity digests', 'what': 'SHA-256 per package (contrib/), per episode (the episode id) and over '
     'the manifest', 'enforced_by': {'file': 'datashare/core.mjs', 'marker': 'async function episodeId('}},
    {'practice': 'dedupe by digest', 'what': DEDUPE['by'], 'enforced_by': {'file': 'datashare/core.mjs', 'marker': "refuse('duplicate'"}},
    {'practice': 'deterministic split by hashed id', 'what': SPLIT['rule'], 'enforced_by': {'file': 'datashare/core.mjs', 'marker': "'split:' + id"}},
    {'practice': 'provenance per episode', 'what': 'every episode in the manifest names the package digest it came '
     'from, its index there, its actor (human or scripted-reference) and its time',
     'enforced_by': {'file': 'datashare/core.mjs', 'marker': 'provenance: {'}},
    {'practice': 'consent scope', 'what': SCOPE_RULE['rule'], 'enforced_by': {'file': 'datashare/core.mjs', 'marker': "refuse('consent-scope'"}},
    {'practice': 'licence compatibility', 'what': LICENCE_RULE['rule'], 'enforced_by': {'file': 'datashare/core.mjs', 'marker': "refuse('licence'"}},
    {'practice': 'revocation honoured', 'what': REVOCATION['rule'], 'enforced_by': {'file': 'datashare/core.mjs', 'marker': "refuse('revoked'"}},
    {'practice': 'no personal data', 'what': 'no name, email, free text, precise location, audio, camera or biometric '
     'field in any episode; contributor labels never copied', 'enforced_by': {'file': 'contrib/verify.mjs', 'marker': 'function privacyFindings('}},
    {'practice': 'K-12 / classroom mode shares nothing', 'what': CLASSROOM,
     'enforced_by': {'file': 'contrib/verify.mjs', 'marker': "check('origin.classroom'"}},
    {'practice': 'range and outlier checks', 'what': 'world samples held to the env observation and action ranges; '
     'return and steps flagged by a robust (median/MAD) outlier rule; missing fields counted',
     'enforced_by': {'file': 'datashare/core.mjs', 'marker': 'function analyse('}},
    {'practice': 'coverage gaps', 'what': 'per env: seeds, embodiments and actors with no episode are listed',
     'enforced_by': {'file': 'datashare/core.mjs', 'marker': 'gaps.push('}},
    {'practice': 'dataset card', 'what': 'a datasheet-style card (motivation, composition, collection, preprocessing, '
     'uses, distribution, maintenance) is written with every dataset, its figures computed from the manifest',
     'enforced_by': {'file': 'datashare/core.mjs', 'marker': 'function renderCard('}},
]

OUTLIER = {'rule': 'robust z = 0.6745 * (x - median) / MAD over the episodes of one env (world) or seat (sim); '
                   '|z| > 3.5 is flagged; skipped (and said so) when an env has fewer than 5 episodes or MAD is 0',
           'fields': ['return (world) ', 'steps (world)', 'samples (world)'], 'z': 3.5, 'min_n': 5}

CARD_SECTIONS = [
    ('motivation', 'Motivation', [
        'Why: example episodes from this bundle\'s SCHEMATIC simulators and AUTHORED robotics arenas, shared on purpose '
        'by learners who ticked a consent scope, for exercising training and evaluation pipelines.',
        'Scope this dataset was built for: {{scope}}.',
        'Trained on it so far: nothing. {{trained}}',
    ]),
    ('composition', 'Composition', [
        '{{episodes}} episodes from {{packages}} admitted package(s); by kind: {{by_kind}}.',
        'Splits (deterministic, by hashed episode id): {{splits}}.',
        'World episodes by env: {{by_env}}. Coverage gaps: {{gaps}}.',
        'No personal data: no name, email, free text, precise location, audio, camera or biometric field (refused at build).',
    ]),
    ('collection', 'Collection process', [
        'Recorded device-locally by the training recorder (opt-in per episode), exported by the learner as a '
        'contribution package with a fixed consent statement and licence, verified by contrib/verify.mjs.',
        'Actors: {{actors}}. Scripted-reference episodes are demonstrations of a hand-written policy, not learned behaviour.',
        'K-12 / classroom mode: sharing is not offered at all; a package that says otherwise is refused.',
    ]),
    ('preprocessing', 'Preprocessing', [
        'Episodes are carried verbatim. Deduplicated by content digest ({{duplicates}} duplicate episode(s) removed); '
        '{{revoked}} episode(s) excluded by the revocation list; {{refused}} package(s) refused by name.',
        'Range and outlier flags are reported, not corrected: {{flags}}.',
    ]),
    ('uses', 'Uses', [
        'Suited to: exercising a pipeline\'s plumbing, format handling and evaluation code on schematic data.',
        'Not suited to: training a controller for real equipment or a real robot; the dynamics are AUTHORED / '
        'SCHEMATIC. {{formats}}',
    ]),
    ('distribution', 'Distribution', [
        'Licence: {{licence}}. Attribution: {{attribution}}.',
        'Nothing is uploaded by this bundle; a dataset directory is written where the maintainer runs the builder.',
    ]),
    ('maintenance', 'Maintenance', [
        'Revocation: {{revocation}}',
        'Manifest digest: {{manifest_digest}}. Rebuild with the same packages and revocation list to reproduce it.',
    ]),
]

INTAKE = {
    'file': 'datashare/intake.mjs',
    'endpoint': '/api/datashare/intake',
    'flag_env': 'DATASHARE_INTAKE',
    'flag_on_value': 'on',
    'flag_default': 'off: unless the Worker env sets DATASHARE_INTAKE to "on" the route answers 404 like an unknown path',
    'r2_binding': 'DATASHARE_R2',
    'key_prefix': 'packages/sha256/',
    'key_rule': 'content-addressed: packages/sha256/<digest.hex>.json - a second POST of the same package finds the '
                'key present and stores nothing new',
    'max_bytes': 1048576,
    'content_type': 'application/json',
    'accepts': TAG_V2,
    'accepts_why': 'only a /2 package states origin.classroom_mode; a /1 package cannot prove it was not exported in '
                   'classroom mode, so the intake refuses it by name (the verifier and the dataset builder still accept it)',
    'refuses': ['wrong method (405)', 'flag off (404)', 'no R2 binding (503)', 'wrong content-type (415)',
                'oversize (413)', 'not JSON (400)', 'record tag not ' + TAG_V2 + ' (422)', 'unconsented: empty or '
                'foreign scope, wrong statement or licence (422)', 'classroom mode (422)', 'any other verifier rule (422)'],
    'deployed': False,
    'status': 'NOT DEPLOYED and OFF by default; tested only against a mocked R2 bucket (datashare/test.mjs)',
    'logs': 'nothing: no body, no header, no address',
}

HONESTY = {
    'trained': TRAINED,
    'no_agent_trained': NO_AGENT,
    'nothing_uploaded': 'nothing is uploaded by this bundle; the intake route is written, off by default and not deployed',
    'formats': FORMATS,
    'shaped_after': 'the manifest and card are shaped after datasheet-style documentation and episode-dataset practice '
                    '(versioned schemas, digests, splits by hashed id); no external format is claimed',
    'best_practices': 'each best practice listed names the file and code that enforces it; nothing else is claimed',
}

# -------------------------------------------------- intake_core.mjs (generated)
verify_src = (ROOT / VERIFY_PATH).read_text(encoding='utf-8')
a, b = verify_src.find('/* CONTRIB_CORE:BEGIN'), verify_src.find('/* CONTRIB_CORE:END */')
if a < 0 or b <= a:
    raise DatashareError(f'{VERIFY_PATH}: no CONTRIB_CORE block to carry')
CONTRIB_BLOCK = verify_src[a:b + len('/* CONTRIB_CORE:END */')]
signin = (ROOT / SIGNIN_PATH).read_text(encoding='utf-8')
a2, b2 = signin.find('/* AUTH-CORE:BEGIN'), signin.find('/* AUTH-CORE:END */')
if a2 < 0 or b2 <= a2:
    raise DatashareError(f'{SIGNIN_PATH}: no AUTH-CORE region to carry; build it with python3 web/build_auth.py')
AUTH_BLOCK = signin[a2:b2]
import re  # noqa: E402
m = re.search(r'export const REGISTRY_FILES = \{\n(.*?)\n\};', verify_src, re.S)
if not m:
    raise DatashareError(f'{VERIFY_PATH}: no REGISTRY_FILES map')
REG_FILES = dict(re.findall(r"^\s*(\w+): '([^']+)',$", m.group(1), re.M))
if not REG_FILES:
    raise DatashareError(f'{VERIFY_PATH}: REGISTRY_FILES is empty')
regs_js = ',\n'.join(f'  {k}: ' + json.dumps(load(rel), ensure_ascii=False, separators=(',', ':')) for k, rel in REG_FILES.items())
core_mjs = ('// GENERATED by datashare/build.py - do not edit. The contrib verifier core (' + VERIFY_PATH + ', CONTRIB_CORE),\n'
            '// the sign-in page\'s AUTH-CORE recovery (' + SIGNIN_PATH + ') and the registries REGISTRY_FILES names, carried\n'
            '// verbatim so the Worker intake runs the rules `node contrib/verify.mjs` runs. No file, network or clock is read.\n'
            + CONTRIB_BLOCK + '\n'
            + 'function authCore() {\n' + AUTH_BLOCK + '\nreturn { recoverAddress };\n}\n'
            + 'export const REGISTRIES = {\n' + regs_js + '\n};\n'
            + 'export const REGISTRY_FILES = ' + json.dumps(REG_FILES) + ';\n'
            + 'export const CORE = contribCore(REGISTRIES);\n'
            + 'export const recoverAddress = authCore().recoverAddress;\n')
CORE_OUT.write_text(core_mjs, encoding='utf-8')

# ---------------------------------------------------------------- fixtures
# SCRIPTED from contrib/'s own fixtures (not learners): each one exercises one
# dataset rule the verifier alone does not. Digests restamped with contrib's rule.
import copy  # noqa: E402
FIX = HERE / 'fixture'


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def restamp(rec):
    body = {k: copy.deepcopy(v) for k, v in rec.items() if k != 'digest'}
    body['contributor']['signature'] = None
    rec['digest']['hex'] = hashlib.sha256(canonical(body)).hexdigest()
    return rec


GOOD1 = load('contrib/fixture/good.json')
GOOD2 = load('contrib/fixture/v2/good.json')
FIXTURES = {}
m = copy.deepcopy(GOOD2); m['consent']['scope'] = ['agent-training']
FIXTURES['v2-agent-only'] = ('consent-scope when built for robot-training; admitted for agent-training', restamp(m))
m = copy.deepcopy(GOOD1)
next(e for e in m['dataset']['episodes'] if e['kind'] == 'sim' and 'trace' in e['outcome'])['outcome']['trace'][0]['gauges']['email'] = 'someone@example.org'
FIXTURES['v1-email'] = ('privacy: a /1 package the /1 verifier passes, refused by the dataset scan', restamp(m))
m = copy.deepcopy(GOOD2); m['exported_at'] = BUILT + 'T01:00:00Z'
FIXTURES['v2-reexport'] = ('admitted; every episode is a duplicate of good-v2 by content digest', restamp(m))
REVOKED_EP = hashlib.sha256(canonical(next(e for e in GOOD2['dataset']['episodes'] if e['kind'] in WORLD_KINDS))).hexdigest()
FIX.mkdir(parents=True, exist_ok=True)
for name, (why, rec) in FIXTURES.items():
    (FIX / f'{name}.json').write_text(json.dumps(rec, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
(FIX / 'revocations.json').write_text(json.dumps({'record': 'tc-revocations/1', 'packages': [FIXTURES['v1-email'][1]['digest']['hex']],
                                                  'episodes': [REVOKED_EP]}, indent=1) + '\n', encoding='utf-8')
(HERE / 'revocations.json').write_text(json.dumps({'record': 'tc-revocations/1', 'packages': [], 'episodes': [],
                                                   'note': 'the live list: empty - no contributor has asked; add a package digest or episode id to exclude it from every later build'},
                                                  indent=1) + '\n', encoding='utf-8') if not (HERE / 'revocations.json').exists() else None

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
registry = {
    'pack': 'smartcitix-datashare',
    'brand': 'DATASHARE·Data Commons',
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'provenance': 'DERIVED',
    'provenance_note': 'record tags, kinds, privacy, licence and scopes are read from ' + CONTRIB_PATH + '; env facts '
                       'from it and ' + ROBOTICS_PATH + '; the split ratios, card template, best-practice list and '
                       'intake limits are AUTHORED here',
    'honesty': HONESTY,
    'dataset_tag': DATASET_TAG,
    'accepts': {'package_tags': [TAG_V1, TAG_V2], 'intake_tag': TAG_V2, 'contrib_source_stamp': req(CONTRIB, 'source_stamp', CONTRIB_PATH),
                'robotics_schema': req(ROBOTICS, 'schema', ROBOTICS_PATH), 'robotics_contract_version': req(ROBOTICS, 'contract_version', ROBOTICS_PATH)},
    'fields_by_kind': FIELDS_BY_KIND,
    'world_kind_versions': {k: req(v, 'v', k) for k, v in WORLD_KINDS.items()},
    'manifest_shape': MANIFEST_SHAPE,
    'split': SPLIT,
    'dedupe': DEDUPE,
    'licence': LICENCE_RULE,
    'consent_scope': SCOPE_RULE,
    'revocation': REVOCATION,
    'refusals': REFUSALS,
    'privacy': PRIVACY,
    'classroom': CLASSROOM,
    'envs': RANGES,
    'pose_len_by_medium': POSE_LEN,
    'sim_seat_envs': SIM_SEAT_ENVS,
    'embodiments': sorted(EMBODIMENTS.keys()),
    'outlier': OUTLIER,
    'best_practices': BEST_PRACTICES,
    'card': {'template': [{'id': i, 'title': t, 'lines': ls} for i, t, ls in CARD_SECTIONS],
             'style': 'datasheet-style sections; every {{slot}} is filled from the manifest and the analysis, never typed'},
    'intake': INTAKE,
    'intake_core': {'file': 'datashare/intake_core.mjs', 'carries': [VERIFY_PATH + '#CONTRIB_CORE', SIGNIN_PATH + '#AUTH-CORE'],
                    'registries': REG_FILES},
    'fixtures': {name: {'file': f'fixture/{name}.json', 'exercises': why} for name, (why, _) in FIXTURES.items()},
    'fixture_revocations': {'file': 'fixture/revocations.json', 'revokes_episode': REVOKED_EP, 'revokes_package': 'v1-email'},
    'counts': {'best_practices': len(BEST_PRACTICES), 'card_sections': len(CARD_SECTIONS), 'world_envs': len(RANGES),
               'sim_seat_envs': len(SIM_SEAT_ENVS), 'kinds': len(FIELDS_BY_KIND), 'trained_models': 0},
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(registry, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
(HERE / 'intake_config.mjs').write_text('// GENERATED by datashare/build.py from the same object as registry/datashare.json. Do not edit.\n'
                                      'export default ' + json.dumps({'intake': INTAKE, 'source_stamp': stamp}, indent=1, ensure_ascii=False) + ';\n',
                                      encoding='utf-8')
print(f'datashare: {DATASET_TAG}, {len(BEST_PRACTICES)} enforced practices, {len(CARD_SECTIONS)} card sections, '
      f'{len(RANGES)} world envs, {len(SIM_SEAT_ENVS)} sim-seat envs, intake off and not deployed (source stamp {stamp})')
