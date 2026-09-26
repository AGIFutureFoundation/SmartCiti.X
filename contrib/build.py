#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the contribution contract builder.

WHAT WAS MISSING. The 3D page records a learner's episodes under one
localStorage key (`tc-training`, opt-in) and, with TRACE on, a coarse gauge
sample of a running sim. training/ documents the export shaped for an
ml-agents conversion script and says plainly that no agent has been trained.
Nothing let a learner SHARE that log as training data on purpose - with a
consent statement, a scope, a licence, a digest and (optionally) a wallet
signature - in a file this bundle can verify. This pack fixes the SHAPE of
such a package (`tc-contribution/1`), documents what each field proves and
does not prove, and ships a verifier (`verify.mjs`) that re-checks a package
against the registries it names.

WHAT IT IS NOT. Nothing here uploads anything: the learner keeps the file.
No platform is integrated, no destination is validated, no agent or robot has
learned from any package, and nothing is written to any chain. A signature is
the identity of a key, not of a person. The consent statement and the licence
are fixed HERE, once, and never chosen per record; a package that carries any
other text or any other licence is refused by name.

PROVENANCE. DERIVED: the episode kinds and their field lists, the TRACE cap
and the sample shape are READ from training/registry/training.json; the
statement a wallet signs is auth/'s own; the ids a package may name resolve
against sims/, pack/ and unions/. The fixture is SCRIPTED - labelled as not a
learner - and every mutant breaks exactly one named rule.
"""
import copy
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'contrib.json'
FIX = HERE / 'fixture'
BUILT = '2026-09-26'


def req(mapping, key, who):
    """A missing key raises and names itself; no default is decided here."""
    if not isinstance(mapping, dict) or key not in mapping:
        raise KeyError(f'{who}: {key!r} does not resolve')
    return mapping[key]


MANIFEST_PATH = 'pack/manifest.json'
TRAINING_PATH = 'training/registry/training.json'
AUTH_PATH = 'auth/registry/auth.json'
SIMS_PATH = 'sims/registry/sims.json'
HALLS_PATH = 'pack/registry/halls.json'
CAMPUSES_PATH = 'unions/registry/campuses.json'

MANIFEST = json.load(open(ROOT / MANIFEST_PATH))
TRAINING = json.load(open(ROOT / TRAINING_PATH))
AUTH = json.load(open(ROOT / AUTH_PATH))
SIMS = json.load(open(ROOT / SIMS_PATH))
HALLS = json.load(open(ROOT / HALLS_PATH))
CAMPUSES = json.load(open(ROOT / CAMPUSES_PATH))

PRODUCT = req(MANIFEST, 'product', MANIFEST_PATH)
PACK_VERSION = req(MANIFEST, 'pack_version', MANIFEST_PATH)
for rel, reg in ((TRAINING_PATH, TRAINING), (AUTH_PATH, AUTH), (SIMS_PATH, SIMS),
                 (HALLS_PATH, HALLS), (CAMPUSES_PATH, CAMPUSES)):
    if req(reg, 'pack_version', rel) != PACK_VERSION:
        raise AssertionError(f'{rel}: pack_version disagrees with {MANIFEST_PATH}')

# ---------------------------------------------------------- from training/ ---
EPISODE_KINDS = req(TRAINING, 'episode_kinds', TRAINING_PATH)
ACTORS = req(TRAINING, 'actors', TRAINING_PATH)
TRAINING_STORAGE = req(TRAINING, 'storage', TRAINING_PATH)
TRAINING_KEY = req(TRAINING_STORAGE, 'key', TRAINING_PATH + '#storage')
TRACE = req(TRAINING, 'trace', TRAINING_PATH)
TRACE_MAX = req(TRACE, 'max_samples', TRAINING_PATH + '#trace')
TRAINING_HONESTY = req(TRAINING, 'honesty', TRAINING_PATH)
EXPORT_FORMAT = req(TRAINING, 'export_format', TRAINING_PATH)
NO_AGENT = req(EXPORT_FORMAT, 'no_agent_trained', TRAINING_PATH + '#export_format')

# The field list per kind is the registry's, verbatim. One field is declared
# conditional by the registry's own sentence: sim.operator is "present ONLY
# when actor is scripted-reference ... absent on a human episode". That
# sentence is parsed, not paraphrased: if training/ stops saying it, this
# build stops treating the field as conditional.
FIELDS_BY_KIND = {}
CONDITIONAL = {}
for kind, spec in EPISODE_KINDS.items():
    FIELDS_BY_KIND[kind] = list(req(spec, 'fields', f'{TRAINING_PATH}#episode_kinds.{kind}'))
    for f in FIELDS_BY_KIND[kind]:
        if f in spec and isinstance(spec[f], str) and 'present ONLY when actor is' in spec[f]:
            m = re.search(r'present ONLY when actor is ([a-z-]+)', spec[f])
            actor = m.group(1)
            if actor not in ACTORS:
                raise AssertionError(f'{TRAINING_PATH}#episode_kinds.{kind}.{f} names actor {actor!r}, not in #actors')
            CONDITIONAL.setdefault(kind, {})[f] = {
                'present_only_when': {'actor': actor},
                'why': spec[f],
            }
SIM_SPEC = req(EPISODE_KINDS, 'sim', TRAINING_PATH + '#episode_kinds')
SIM_OUTCOME = req(SIM_SPEC, 'outcome_shape', TRAINING_PATH + '#episode_kinds.sim')
TRACE_SHAPE_TEXT = req(SIM_OUTCOME, 'trace', TRAINING_PATH + '#episode_kinds.sim.outcome_shape')
# "[{t, gauges}] - OPTIONAL ..." -> the sample keys, read from the shape text
m = re.match(r'\[\{([a-z_, ]+)\}\]', TRACE_SHAPE_TEXT)
if m is None:
    raise AssertionError(f'{TRAINING_PATH}#episode_kinds.sim.outcome_shape.trace does not start with a [{{...}}] shape')
TRACE_SAMPLE_KEYS = [k.strip() for k in m.group(1).split(',')]
OUTCOME_KEYS = [k for k in SIM_OUTCOME.keys() if k != 'trace']  # passed, rows: always; trace: optional
# gauges() is described, never enumerated: "display-shaped scalars and short
# labels". So a verifier can hold a trace to its COUNT and to the sample keys
# {t, gauges}, and must say it holds nothing about what is inside gauges.
GAUGE_FIELDS_ENUMERATED = any(isinstance(v, (list, dict)) and 'gauge' in k for k, v in TRACE.items())
if GAUGE_FIELDS_ENUMERATED:
    raise AssertionError(f'{TRAINING_PATH}#trace now enumerates gauge fields; extend the trace rule to check them')

# ---------------------------------------------------------- from auth/ ---
SIWE = req(AUTH, 'siwe', AUTH_PATH)
SIWE_STATEMENT = req(SIWE, 'statement', AUTH_PATH + '#siwe')
SIGNING_METHOD = req(SIWE, 'signing_method', AUTH_PATH + '#siwe')
AUTH_STORAGE = req(AUTH, 'storage', AUTH_PATH)
IDENTITY_KEY = req(AUTH_STORAGE, 'identity_key', AUTH_PATH + '#storage')
AUTH_RECORDS = req(AUTH, 'records_named', AUTH_PATH)
if req(AUTH_RECORDS, 'training_key', AUTH_PATH + '#records_named') != TRAINING_KEY:
    raise AssertionError(f'{AUTH_PATH}#records_named.training_key is not {TRAINING_PATH}#storage.key')
WALLET_METHOD = 'siwe-ethereum'
if WALLET_METHOD not in req(AUTH, 'methods', AUTH_PATH):
    raise KeyError(f'{AUTH_PATH}#methods does not name {WALLET_METHOD!r}')

# ---------------------------------------------------------- id sources ---
SIM_MAP = req(SIMS, 'sims', SIMS_PATH)
SCENARIOS = {sid: [req(sc, 'id', f'{sid} scenario') for sc in req(S, 'scenarios', sid)] for sid, S in SIM_MAP.items()}
HALL_SLUGS = [req(h, 'slug', 'hall') for h in req(HALLS, 'halls', HALLS_PATH)]
CAMPUS_IDS = list(req(CAMPUSES, 'campuses', CAMPUSES_PATH).keys())
ID_SOURCES = {
    'sim': {'registry': SIMS_PATH + '#sims', 'keys': 'sim ids', 'count': len(SIM_MAP)},
    'scenario': {'registry': SIMS_PATH + '#sims[sim].scenarios[].id', 'keys': 'scenario ids of that seat',
                 'null_allowed': True,
                 'null_why': 'the 3D page writes scenario null when a seat was run with no scenario chosen; a null '
                             'names nothing and resolves nothing, and is not a foreign id'},
    'hall': {'registry': HALLS_PATH + '#halls[].slug', 'keys': 'hall slugs', 'count': len(HALL_SLUGS)},
    'campus': {'registry': CAMPUSES_PATH + '#campuses', 'keys': 'campus ids', 'count': len(CAMPUS_IDS)},
    'not_resolved': {
        'fields': ['advisor', 'crew', 'role', 'topic', 'answer_kind', 'point', 'controls', 'operator'],
        'why': 'this verifier resolves the ids that name a PLACE or a SEAT (sim, scenario, hall, campus). An advisor, '
               'a crew role, a topic, a walkaround point or a control scheme is carried verbatim and its shape is '
               'held to the episode field list; whether it names a real registry entry is not checked here and the '
               'verifier says so',
    },
}

# ----------------------------------------------------------------- consent ---
SCOPES = {
    'agent-training': 'the episodes may be used to train, evaluate or benchmark a software agent (for example the '
                      'ml-agents conversion the training pack describes); this bundle has trained none',
    'robot-training': 'the episodes may be used to train, evaluate or benchmark a controller for a physical robot; '
                      'training/ says these are schematic single-machine simulators and no such controller should be '
                      'trained on them for real equipment, and this bundle has trained none',
}
CONSENT_STATEMENT = ('I share the training episodes in this package, recorded by this device, for the scopes named '
                     'in consent.scope under the licence named in consent.license. I can withdraw by not sharing '
                     'the file again; copies already given away are governed by that licence. Nothing in this '
                     'package names me: it carries scenario ids, control schemes and measured outcomes, and the '
                     'label or wallet address I chose to attach.')
LICENSE = {
    'spdx': 'CC-BY-4.0',
    'name': 'Creative Commons Attribution 4.0 International',
    'why': 'one licence for every package, chosen here and never per record: attribution keeps the contributor '
           'named (by the label or key they attached) when a package is passed on, and a permissive data licence '
           'is the only one under which the ml-agents-shaped export training/ describes could actually be used '
           'by anyone. A share-alike or non-commercial clause would need a party to enforce it and this bundle has '
           'no server and no party. A package under any other SPDX id fails consent.license by name.',
    'chosen_by': 'this registry (contrib/build.py), once',
}
REVOCABLE_MEANS = ('revocable: true means the learner keeps the file and decides each time whether to hand it to '
                   'anyone. Nothing here is uploaded, so there is nothing to recall from a server; a copy already '
                   'given away is governed by the licence and by the recipient, not by this bundle.')

# ----------------------------------------------------------------- digest ---
DIGEST_RULE = {
    'alg': 'SHA-256',
    'over': 'canonical JSON of every top-level field except digest, with contributor.signature forced to null: '
            'keys sorted recursively, no whitespace, UTF-8',
    'excludes_signature_why': 'the signature is a signature OVER the digest, made after it; a digest that covered it '
                              'would be circular. Every other byte of contributor (claimed, attested_by) and of '
                              'consent is covered, so a scope or licence edited after signing breaks the digest.',
    'numbers': 'exporters write integers for counts and trace sample times so Python and JavaScript canonicalise alike',
}
SIGNED_ATTESTATION = 'wallet signature over the digest'
UNSIGNED_ATTESTATION = 'this device only'
SIGNATURE_SCHEME = 'eip191-personal_sign'


def signature_message(digest_hex, exported_at, scope):
    """The exact string a wallet signs, fixed by structure - never free text.
    The consent scope is IN the signed text so a signature vouches for the
    scope the holder saw, not just for the bytes."""
    return (SIWE_STATEMENT + '\ndigest: ' + digest_hex + '\nexported_at: ' + exported_at
            + '\nconsent: ' + ','.join(scope))


SIGNATURE_RULE = {
    'field': 'contributor.signature',
    'null_means': 'unsigned: ' + UNSIGNED_ATTESTATION + '. Then contributor.attested_by must be exactly "'
                  + UNSIGNED_ATTESTATION + '" and contributor.claimed is whatever label was on the device, or null.',
    'object_shape': {'scheme': SIGNATURE_SCHEME, 'address': '0x + 40 hex, the signer the wallet reported',
                     'message': 'the exact string signed (below)', 'sig': '0x + 130 hex: r | s | v, 65 bytes'},
    'scheme': SIGNATURE_SCHEME,
    'signing_method': SIGNING_METHOD,
    'message': {
        'structure': '<statement>\\n' + 'digest: <digest.hex>\\n' + 'exported_at: <exported_at>\\n'
                     + 'consent: <consent.scope joined by comma>',
        'statement': SIWE_STATEMENT,
        'statement_from': AUTH_PATH + '#siwe.statement - the line auth/ already puts in front of the human',
        'why_fixed': 'the verifier rebuilds this message from THIS package\'s digest.hex, exported_at and '
                     'consent.scope and requires equality, so a signature over any other text - another package, '
                     'another scope, a friendly sentence - is refused by name',
    },
    'when_signed': 'contributor.attested_by must be exactly "' + SIGNED_ATTESTATION + '", contributor.claimed must '
                   'equal signature.address, and the address recovered from (message, sig) must equal both - '
                   'compared as lowercase hex, so EIP-55 casing differences are not a mismatch',
    'order': 'digest first: a tampered digest under a valid signature fails `digest` (and the signature no longer '
             'matches the rebuilt message); a tampered message or sig with an intact digest fails '
             '`contributor.signature` alone',
    'recovery': 'auth/recover.mjs, the sign-in page\'s own keccak-256 and secp256k1 recovery, lifted from the built '
                'page. No second keccak and no second curve exist in this pack, and no signing routine: a verifier '
                'that could sign could forge.',
    'where_the_wallet_comes_from': 'the contribute page reads the identity the sign-in page stored under '
                                   + IDENTITY_KEY + '; only a record whose method is ' + WALLET_METHOD
                                   + ' carries an address, and only then is signing offered. No wallet, no signature: '
                                     'the package stays unsigned and says so. A signature is never fabricated by the page.',
    'proves': 'that the holder of the private key for signature.address signed this package\'s digest and consent '
              'scope at export. The identity of a key, not of a person.',
    'does_not_prove': [
        'who the person is: a key is held, lent, shared and stolen',
        'anything about any chain: nothing is written to any chain, nothing is anchored, no transaction exists',
        'that the episodes are true: the digest covers what the device exported, and the device can be edited',
        'that any agent or robot learned from the package, or that any destination received it',
    ],
}

# ---------------------------------------------------------------- honesty ---
HONESTY = {
    'proves': [
        'the package has not changed since it was exported: its SHA-256 digest recomputes over the canonical form',
        'every episode is of a kind training/ declares and carries exactly that kind\'s fields - no field more, none fewer',
        'every sim, scenario, hall and campus an episode names exists in this bundle at the stated pack version',
        'a trace, where attached, has no more samples than training/ caps and each sample has the declared keys',
        'the consent scope is a non-empty subset of the scopes this registry declares, the statement is this '
        'registry\'s and the licence is this registry\'s one licence',
        'the counts the package states about itself (episodes by kind, traces attached, sims covered) recompute from its episodes',
    ],
    'does_not_prove': [
        'who the contributor is: contributor.claimed is a label this device stored, attested by this device only, '
        'and nothing checks it - unless a wallet signed, in which case it is the identity of a key, not of a '
        'person; a stolen key signs just as well',
        'that any agent or robot learned from this package: ' + NO_AGENT,
        'that the package reached anyone: nothing in this bundle sends it anywhere; the learner keeps the file and '
        'hands it over, or does not',
        'anything on any blockchain: a wallet signature is computed in the browser and carried in the file; nothing '
        'is written to any chain, nothing is anchored, and no one can look it up',
        'that the device was honest: a package can be written by hand and will verify if it is internally consistent',
        'that the gauges inside a trace sample mean anything: training/ describes them as display-shaped scalars '
        'and short labels and enumerates none, so the verifier holds a trace to its count and sample keys only',
        'that an advisor, crew role, topic or walkaround point an episode names exists: only seats, scenarios, '
        'halls and campuses are resolved',
        'that the episodes came from real equipment: ' + req(TRAINING_HONESTY, 'schematic', TRAINING_PATH + '#honesty'),
    ],
    'digest': 'a digest proves integrity since export, not identity',
    'signature': 'null unless a wallet signed: this bundle has no key of its own and no server, so an unsigned '
                 'package is attested by this device only. A signed package carries an EIP-191 personal_sign '
                 'signature by the connected wallet over this package\'s digest and consent scope; it proves that '
                 'the holder of that key signed this digest at export - the identity of a key, not of a person. A '
                 'signature that does not recover to the address it claims, or that signs any other message, is '
                 'refused as a forgery. Nothing is written to any chain and nothing is anchored.',
    'nothing_sent': 'nothing is sent anywhere by this bundle: no platform is integrated, no destination is '
                    'validated, no upload exists. The contribute page writes a file to the learner\'s own downloads '
                    'and stops.',
    'no_agent_trained': NO_AGENT,
    'anonymous': req(TRAINING_HONESTY, 'anonymous', TRAINING_PATH + '#honesty'),
}

CONTRACT = {
    'record': {'is': 'the literal string tc-contribution/1', 'proves': 'which contract the verifier applies'},
    'product': {'is': MANIFEST_PATH + ' product', 'proves': 'which product wrote it; nothing about the learner'},
    'pack_version': {'is': MANIFEST_PATH + ' pack_version', 'proves': 'which registries the ids resolve against'},
    'exported_at': {'is': 'ISO-8601 string, device clock', 'proves': 'nothing: a device clock is not attested'},
    'contributor': {'is': '{claimed: string|null, attested_by: "' + UNSIGNED_ATTESTATION + '" | "' + SIGNED_ATTESTATION
                          + '", signature: null | {scheme: "' + SIGNATURE_SCHEME + '", address, message, sig}}',
                    'proves': 'unsigned: nothing about who contributed; claimed is a stored label, not checked. Signed: '
                              'that the holder of the key for `address` signed this digest and scope at export - a '
                              'key, not a person; see registry#signature'},
    'consent': {'is': '{statement: registry#consent.statement verbatim, granted_at: ISO-8601 string that parses, '
                      'scope: non-empty subset of registry#consent.scopes, revocable: true, license: registry#consent.license.spdx}',
                'proves': 'what the device recorded the learner ticking, under which fixed text and licence; signed, '
                          'the scope is inside the signed message'},
    'dataset': {'is': '{episodes: the ' + TRAINING_KEY + ' array verbatim, traces_attached: n, episode_counts_by_kind: '
                      '{kind: n}, sims_covered: [sim ids, sorted, unique], fields_by_kind: ' + TRAINING_PATH
                      + '#episode_kinds[kind].fields verbatim}',
                'proves': 'the shape of every episode against training/, every place and seat id against the bundle, '
                          'and that the counts recompute; nothing about what the episodes are worth'},
    'honesty': {'is': 'the proves / does_not_prove lists of this registry, carried in the package',
                'proves': 'that the package says of itself what this registry says of it'},
    'digest': DIGEST_RULE,
}

RULES = ['record.fields', 'digest', 'contributor.signature', 'consent.statement', 'consent.scope',
         'consent.license', 'consent.granted_at', 'episode.kind', 'episode.fields', 'episode.t', 'trace',
         'ids.sim', 'ids.scenario', 'ids.hall', 'ids.campus', 'dataset.counts']


# ------------------------------------------------------------- the fixture ---
def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def digest_of(record):
    body = {k: copy.deepcopy(v) for k, v in record.items() if k != 'digest'}
    if 'contributor' in body and isinstance(body['contributor'], dict) and 'signature' in body['contributor']:
        body['contributor']['signature'] = None
    return hashlib.sha256(canonical(body)).hexdigest()


def stamp_digest(record):
    record['digest'] = {'alg': DIGEST_RULE['alg'], 'over': DIGEST_RULE['over'], 'hex': digest_of(record)}
    return record


def counts_of(episodes):
    by = {}
    sims = set()
    traces = 0
    for ep in episodes:
        if ep['kind'] not in by:
            by[ep['kind']] = 0
        by[ep['kind']] += 1
        if 'sim' in ep and isinstance(ep['sim'], str):
            sims.add(ep['sim'])
        if ep['kind'] == 'sim' and 'trace' in ep['outcome']:
            traces += 1
    return {'episode_counts_by_kind': dict(sorted(by.items())), 'traces_attached': traces, 'sims_covered': sorted(sims)}


FIX_SIM = sorted(SIM_MAP.keys())[0]
FIX_SIM2 = sorted(SIM_MAP.keys())[1]
FIX_HALL = req(SIM_MAP[FIX_SIM], 'halls', FIX_SIM)[0]
FIX_HALL2 = req(SIM_MAP[FIX_SIM2], 'halls', FIX_SIM2)[0]
FIX_SCENARIO = req(SIM_MAP[FIX_SIM], 'scenarios', FIX_SIM)[0]
FIX_CAMPUS = req(FIX_SCENARIO, 'campus', f'{FIX_SIM} scenario')
FIX_SCENARIO2 = req(SIM_MAP[FIX_SIM2], 'scenarios', FIX_SIM2)[0]
FIX_CAMPUS2 = req(FIX_SCENARIO2, 'campus', f'{FIX_SIM2} scenario')
FIX_CONTROLS = [req(c, 'action', f'{FIX_SIM} control') for c in req(SIM_MAP[FIX_SIM], 'controls', FIX_SIM)]
FIX_CONTROLS2 = [req(c, 'action', f'{FIX_SIM2} control') for c in req(SIM_MAP[FIX_SIM2], 'controls', FIX_SIM2)]
FIX_POINT = req(req(SIM_MAP[FIX_SIM], 'walkaround', FIX_SIM)[0], 'point', f'{FIX_SIM} walkaround')
FIX_AXES = [req(a, 'axis', f'{FIX_SIM} rubric') for a in req(SIM_MAP[FIX_SIM], 'rubric', FIX_SIM)]
for hall in (FIX_HALL, FIX_HALL2):
    assert hall in HALL_SLUGS, f'fixture: {hall} is not a hall slug'
for campus in (FIX_CAMPUS, FIX_CAMPUS2):
    assert campus in CAMPUS_IDS, f'fixture: {campus} is not a campus id'
SCRIPTED_ACTOR = next(a for a in ACTORS if a != 'human')
if 'human' not in ACTORS:
    raise AssertionError(f'{TRAINING_PATH}#actors names no human actor')


def episode(kind, t, **fields):
    """One synthetic episode, in the field ORDER training/ declares, holding
    exactly that kind's fields (conditional ones only when their actor matches)."""
    ep = {'t': t, 'kind': kind}
    for f in FIELDS_BY_KIND[kind]:
        if f in ('t', 'kind'):
            continue
        cond = CONDITIONAL[kind][f] if kind in CONDITIONAL and f in CONDITIONAL[kind] else None
        if cond is not None and fields['actor'] != cond['present_only_when']['actor']:
            continue
        if f not in fields:
            raise KeyError(f'fixture: a {kind} episode needs {f!r}')
        ep[f] = fields[f]
    extra = set(fields) - set(FIELDS_BY_KIND[kind])
    if extra:
        raise KeyError(f'fixture: {kind} episode given fields the registry does not declare: {sorted(extra)}')
    return ep


def synthetic_gauges(i):
    # display-shaped scalars and short labels, as training/ describes gauges();
    # synthetic values, computed from the sample index so the file is deterministic
    return {'load_pct': 30 + i * 5, 'hook_cm': 150 + i * 25, 'wind': 'calm', 'note': 'fixture gauges - not a machine'}


def build_fixture():
    T = lambda s: f'{BUILT}T03:00:{s:02d}.000Z'
    rows = [{'axis': a, 'value': 1, 'ok': True} for a in FIX_AXES]
    episodes = [
        episode('walkaround', T(0), campus=FIX_CAMPUS, hall=FIX_HALL, sim=FIX_SIM, point=FIX_POINT),
        episode('sim', T(1), campus=FIX_CAMPUS, hall=FIX_HALL, sim=FIX_SIM, scenario=FIX_SCENARIO['id'],
                controls=FIX_CONTROLS, actor='human',
                outcome={'passed': True, 'rows': rows, 'trace': [{'t': i * 1000, 'gauges': synthetic_gauges(i)} for i in range(4)]}),
        episode('sim', T(2), campus=FIX_CAMPUS2, hall=FIX_HALL2, sim=FIX_SIM2, scenario=None,
                controls=FIX_CONTROLS2, actor='human', outcome={'passed': False, 'rows': []}),
        episode('sim', T(3), campus=FIX_CAMPUS, hall=FIX_HALL, sim=FIX_SIM, scenario=FIX_SCENARIO['id'],
                controls=FIX_CONTROLS, actor=SCRIPTED_ACTOR,
                operator={'level': 'fixture-level', 'seed': 7, 'scenario': FIX_SCENARIO['id'], 'steps': 120, 'dt': 0.05},
                outcome={'passed': True, 'rows': rows}),
        episode('advisor', T(4), campus=FIX_CAMPUS, hall=FIX_HALL, advisor='fixture-advisor', topic='fixture-topic',
                answer_kind='record'),
        episode('crew', T(5), campus=FIX_CAMPUS, hall=FIX_HALL, crew='fixture-crew', role='fixture-role',
                topic='fixture-topic', answer_kind='registry'),
    ]
    c = counts_of(episodes)
    rec = {
        'record': 'tc-contribution/1',
        'product': PRODUCT,
        'pack_version': PACK_VERSION,
        'exported_at': BUILT + 'T00:00:00Z',
        'contributor': {'claimed': 'fixture - not a learner', 'attested_by': UNSIGNED_ATTESTATION, 'signature': None},
        'consent': {'statement': CONSENT_STATEMENT, 'granted_at': BUILT + 'T00:00:00Z',
                    'scope': sorted(SCOPES.keys()), 'revocable': True, 'license': LICENSE['spdx']},
        'dataset': {'episodes': episodes, 'traces_attached': c['traces_attached'],
                    'episode_counts_by_kind': c['episode_counts_by_kind'], 'sims_covered': c['sims_covered'],
                    'fields_by_kind': FIELDS_BY_KIND},
        'honesty': {'proves': HONESTY['proves'], 'does_not_prove': HONESTY['does_not_prove'],
                    'nothing_sent': HONESTY['nothing_sent'], 'no_agent_trained': HONESTY['no_agent_trained'],
                    'fixture': 'this package is SCRIPTED by contrib/build.py from synthetic episodes shaped by '
                               + TRAINING_PATH + '; it is not a learner and its gauges are not a machine'},
    }
    return stamp_digest(rec)


def mutants(good):
    """Each mutant breaks exactly one rule and names the rule it must fail."""
    out = {}
    eps = lambda m: m['dataset']['episodes']
    sim_ep = lambda m: next(e for e in eps(m) if e['kind'] == 'sim' and 'trace' in e['outcome'])

    m = copy.deepcopy(good)
    m['digest']['hex'] = '0' * 64
    out['bad-digest'] = ('digest', m)

    m = copy.deepcopy(good)
    eps(m)[0]['score'] = 99
    out['foreign-field-on-episode'] = ('episode.fields', stamp_digest(m))

    m = copy.deepcopy(good)
    del eps(m)[0]['point']
    out['missing-field-on-episode'] = ('episode.fields', stamp_digest(m))

    # operator on a human episode: the registry says it is absent there
    m = copy.deepcopy(good)
    sim_ep(m)['operator'] = {'level': 'x', 'seed': 1, 'scenario': None, 'steps': 1, 'dt': None}
    out['operator-on-human-episode'] = ('episode.fields', stamp_digest(m))

    m = copy.deepcopy(good)
    eps(m)[0]['kind'] = 'joystick'
    m['dataset']['episode_counts_by_kind'] = counts_of(eps(m))['episode_counts_by_kind']
    out['unknown-kind'] = ('episode.kind', stamp_digest(m))

    m = copy.deepcopy(good)
    sim_ep(m)['sim'] = 'not-a-seat'
    m['dataset']['sims_covered'] = counts_of(eps(m))['sims_covered']
    out['unknown-sim'] = ('ids.sim', stamp_digest(m))

    m = copy.deepcopy(good)
    sim_ep(m)['scenario'] = 'no-such-scenario'
    out['unknown-scenario'] = ('ids.scenario', stamp_digest(m))

    m = copy.deepcopy(good)
    eps(m)[0]['hall'] = 'no-such-hall'
    out['unknown-hall'] = ('ids.hall', stamp_digest(m))

    m = copy.deepcopy(good)
    eps(m)[0]['campus'] = 'atlantis'
    out['unknown-campus'] = ('ids.campus', stamp_digest(m))

    m = copy.deepcopy(good)
    m['consent']['scope'] = []
    out['empty-scope'] = ('consent.scope', stamp_digest(m))

    m = copy.deepcopy(good)
    m['consent']['scope'] = ['agent-training', 'marketing']
    out['foreign-scope'] = ('consent.scope', stamp_digest(m))

    m = copy.deepcopy(good)
    m['consent']['license'] = 'CC0-1.0'
    out['wrong-license'] = ('consent.license', stamp_digest(m))

    m = copy.deepcopy(good)
    m['consent']['statement'] = 'I agree to everything.'
    out['wrong-statement'] = ('consent.statement', stamp_digest(m))

    m = copy.deepcopy(good)
    m['consent']['granted_at'] = 'last tuesday'
    out['consent-granted-at-unparseable'] = ('consent.granted_at', stamp_digest(m))

    m = copy.deepcopy(good)
    sim_ep(m)['outcome']['trace'] = [{'t': i * 1000, 'gauges': synthetic_gauges(i)} for i in range(TRACE_MAX + 1)]
    out['trace-over-max-samples'] = ('trace', stamp_digest(m))

    m = copy.deepcopy(good)
    sim_ep(m)['outcome']['trace'][1] = {'t': 1000, 'gauges': synthetic_gauges(1), 'joint_angles': [0, 0, 0]}
    out['trace-sample-foreign-key'] = ('trace', stamp_digest(m))

    m = copy.deepcopy(good)
    m['contributor']['signature'] = 'sig:' + '0' * 32
    out['forged-signature'] = ('contributor.signature', stamp_digest(m))

    m = copy.deepcopy(good)
    m['contributor']['attested_by'] = SIGNED_ATTESTATION
    out['attested-by-wallet-unsigned'] = ('contributor.signature', stamp_digest(m))

    m = copy.deepcopy(good)
    m['dataset']['traces_attached'] = 5
    out['counts-drift'] = ('dataset.counts', stamp_digest(m))

    m = copy.deepcopy(good)
    eps(m)[0]['t'] = 'yesterday'
    out['episode-t-unparseable'] = ('episode.t', stamp_digest(m))

    m = copy.deepcopy(good)
    del m['consent']['revocable']
    out['missing-field'] = ('record.fields', stamp_digest(m))

    return out


# -------------------------------------------------------------------- write ---
stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
good = build_fixture()
muts = mutants(good)

registry = {
    'pack': 'smartcitix-trade-craft-academy-contribution',
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'provenance': 'DERIVED',
    'provenance_note': 'every fact here is read from the registry that owns it and re-derivable by build.py; '
                       'the episode shapes are ' + TRAINING_PATH + '#episode_kinds verbatim; the fixture package is '
                       'SCRIPTED and labelled as not a learner',
    'honesty': HONESTY,
    'record_tag': 'tc-contribution/1',
    'training_source': {'key': TRAINING_KEY, 'where': 'localStorage of the built 3D page', 'registry': TRAINING_PATH,
                        'cap': req(TRAINING_STORAGE, 'cap', TRAINING_PATH + '#storage'),
                        'export_format_this_wraps': EXPORT_FORMAT},
    'contract': CONTRACT,
    'consent': {
        'statement': CONSENT_STATEMENT,
        'scopes': SCOPES,
        'license': LICENSE,
        'revocable': True,
        'revocable_means': REVOCABLE_MEANS,
        'granted_at': 'ISO-8601 string the page writes at the moment the export button is pressed with the boxes '
                      'ticked; Date.parse must be finite. A device clock is not attested.',
        'recorder_consent': req(TRAINING_HONESTY, 'consent', TRAINING_PATH + '#honesty'),
    },
    'episode_kinds': {k: {'fields': FIELDS_BY_KIND[k],
                          'conditional_fields': CONDITIONAL[k] if k in CONDITIONAL else {},
                          'what': req(EPISODE_KINDS[k], 'what', f'{TRAINING_PATH}#episode_kinds.{k}')}
                      for k in EPISODE_KINDS},
    'actors': ACTORS,
    'trace': {
        'max_samples': TRACE_MAX,
        'max_samples_policy': req(TRACE, 'max_samples_policy', TRAINING_PATH + '#trace'),
        'attached_at': 'dataset.episodes[].outcome.trace on a sim episode, optional',
        'outcome_keys_always': OUTCOME_KEYS,
        'sample_keys': TRACE_SAMPLE_KEYS,
        'sample_keys_from': TRAINING_PATH + '#episode_kinds.sim.outcome_shape.trace',
        'gauge_fields_enumerated': False,
        'gauge_fields_why': 'training/ describes gauges() as display-shaped scalars and short labels sampled from the '
                            'running sim and enumerates no field names, so the verifier holds a trace to its sample '
                            'COUNT (at most max_samples) and to the sample keys ' + ', '.join(TRACE_SAMPLE_KEYS)
                            + ' - and says it checks nothing inside gauges',
        'sampled_from': req(TRACE, 'sampled_from', TRAINING_PATH + '#trace'),
    },
    'id_sources': ID_SOURCES,
    'digest': DIGEST_RULE,
    'signature': SIGNATURE_RULE,
    'verifier': {
        'file': 'contrib/verify.mjs',
        'usage': 'node contrib/verify.mjs <package.json>',
        'rules': RULES,
        'last_line': 'a contribution proves what a device recorded and, if signed, which key vouched for it - not '
                     'who, and not that any agent or robot learned from it; nothing is sent anywhere by this bundle',
    },
    'destinations': {
        'source': 'protocols/registry/protocols.json, read by web/build_contribute.py at build time if present',
        'rule': 'the contribute page lists whatever agent-protocol destinations that registry names, and says on '
                'every row: not integrated, not validated, nothing sent by this bundle. With no such registry the '
                'section renders from an empty list and says no destination is configured. No platform name is '
                'typed by this pack.',
    },
    'fixture': {
        'label': good['contributor']['claimed'],
        'good': 'fixture/good.json',
        'mutants': {name: {'file': f'fixture/mutant-{name}.json', 'fails': rule} for name, (rule, _) in muts.items()},
        'episodes': good['dataset']['episode_counts_by_kind'],
        'traces_attached': good['dataset']['traces_attached'],
        'sims_covered': good['dataset']['sims_covered'],
    },
    'counts': {
        'episode_kinds': len(EPISODE_KINDS),
        'scopes': len(SCOPES),
        'rules': len(RULES),
        'mutants': len(muts),
        'sims': len(SIM_MAP),
        'halls': len(HALL_SLUGS),
        'campuses': len(CAMPUS_IDS),
    },
}

OUT.parent.mkdir(parents=True, exist_ok=True)
FIX.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(registry, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
(FIX / 'good.json').write_text(json.dumps(good, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
for name, (rule, rec) in muts.items():
    (FIX / f'mutant-{name}.json').write_text(json.dumps(rec, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'contrib: {len(RULES)} rules, {len(muts)} mutants, fixture {sum(good["dataset"]["episode_counts_by_kind"].values())} '
      f'episodes / {good["dataset"]["traces_attached"]} trace, {len(EPISODE_KINDS)} episode kinds from {TRAINING_PATH} '
      f'(source stamp {stamp})')
