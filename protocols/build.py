#!/usr/bin/env python3
"""protocols/ - the blockchain agent protocols and wallet rails a learner's
training-data contribution COULD be handed to, as an honest roster.

WHAT THIS IS, AND WHAT IT IS NOT

The ask was a list of the on-chain agent economies a contribution package
(contrib/, `tc-contribution/1`) could be turned into a unit of: a
token-gated agent on Virtuals, a marketplace service on SingularityNET, a
registered agent on Fetch.ai / the ASI Alliance, an Olas service, a
Bittensor subnet dataset, an Ocean data NFT - and the wallet rails a
learner could sign with. This pack is that list, in the same shape auth/
uses for its federated issuer adapters: every entry is OFF (`configured:
false`, `integrated: false`, `validated_against_spec: false`), every entry
names what a contribution would have to become and what this bundle would
have to hold to do it, and none of it is switchable from inside a page.

Nothing here integrates, sends, mints, registers, lists or signs anything.
There is no SDK vendored, no key held, no contract address typed, no RPC
called. The bundle is static HTML built from registries; it has no server,
and every one of these protocols needs one (a daemon, a running agent, an
operator, a miner, a provider) before a contribution could be handed over.

PROVENANCE, STATED WHERE A READER CANNOT MISS IT

Every description below is AUTHORED FROM GENERAL KNOWLEDGE. This build has
no network: the eight hosts were probed once by hand (one curl each, 10 s,
no retry) on the date in protocols/authored/probe.json and NONE answered -
the egress proxy refused every CONNECT. So no site was read, no spec was
fetched, no SDK documentation was opened, and the descriptions may be
stale or wrong in detail. The probe is the only RECORDED fact in this pack,
and it is read from that stamped file rather than measured at build time,
so a rebuild is byte-identical.

Two names the user gave could not be identified with confidence -
"Virtual Ventures" and "Cloudflare wallets" - and they are recorded as
`unidentified: true` with the reason, rather than mapped to a plausible
product. The nearest real Cloudflare offering (its Web3 gateways) is
named under the Cloudflare entry and stated to be not a wallet.
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'protocols.json'

PACK_VERSION = json.loads(
    (ROOT / 'pack' / 'manifest.json').read_text())['pack_version']
# BUILT is a LABEL, not a fact read from anywhere: the date this builder's
# output last changed shape, set by hand when it does. The fact a suite can
# check is the source_stamp beside it.
BUILT = '2026-09-26'
PRODUCT = 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)'
TIERS = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED')


def need(obj, key, where):
    """One key, or a build failure that says which key and where. No
    default arm: a default here would turn a missing field into a
    plausible-looking claim about a protocol."""
    if not isinstance(obj, dict):
        raise TypeError(f'protocols: {where}: expected an object to read {key!r} from')
    if key not in obj:
        raise KeyError(f'protocols: {where}: no key {key!r} (it holds {sorted(obj)[:12]})')
    return obj[key]


# ---------------------------------------------------------------- the probe ---
# Read from a file written ONCE by hand, never measured here: the build
# fetches nothing, and the date travels with the measurement it dates.
PROBE_FILE = HERE / 'authored' / 'probe.json'
PROBE = json.loads(PROBE_FILE.read_text())
PROBE_DATE = need(PROBE, 'date', 'authored/probe.json')
assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', PROBE_DATE), PROBE_DATE
PROBE_HOW = need(PROBE, 'how', 'authored/probe.json')
PROBE_000 = need(PROBE, 'meaning_of_000_56', 'authored/probe.json')
PROBE_BY_HOST = {}
for pr in need(PROBE, 'tried', 'authored/probe.json'):
    host = need(pr, 'host', 'probe.tried')
    code = need(pr, 'http_code', f'probe.tried {host}')
    assert re.fullmatch(r'[0-9]{3}', code), (host, code)
    assert isinstance(need(pr, 'curl_exit', host), int)
    assert need(pr, 'url', host).startswith('https://'), host
    assert host not in PROBE_BY_HOST, f'probe host {host} repeats'
    PROBE_BY_HOST[host] = pr


def probe_record(host):
    """The RECORDED probe for one host, shaped for a roster entry. A
    2xx would mean the host answered a HEAD-shaped GET whose body was
    thrown away - never that a spec was read - so `fetched` is False
    in this build regardless, and the code is beside it for a reader."""
    pr = need(PROBE_BY_HOST, host, 'probe hosts')
    code = pr['http_code']
    if code.startswith('2'):
        meaning = ('the host answered 2xx but the body was discarded '
                   '(-o /dev/null): the site was reachable, the spec was '
                   'still not read - REVISIT this entry with the text open')
    elif code == '000' and pr['curl_exit'] == 56:
        meaning = PROBE_000
    else:
        meaning = f'HTTP {code}, curl exit {pr["curl_exit"]}: not read'
    return {
        'fetched': False,
        'url_tried': pr['url'],
        'http_code': code,
        'curl_exit': pr['curl_exit'],
        'date': PROBE_DATE,
        'how': PROBE_HOW,
        'meaning': meaning,
        'provenance': 'RECORDED',
    }


N_PROBE_2XX = sum(1 for pr in PROBE_BY_HOST.values()
                  if pr['http_code'].startswith('2'))

# -------------------------------------------------- the contribution package ---
# contrib/ is being written in parallel. If its registry exists when this
# runs, the package id is READ from it; if it does not, the id is the one
# the brief gave and the record says so. Both branches are written out -
# there is no silent fallback.
CONTRIB_FILE = ROOT / 'contrib' / 'registry' / 'contrib.json'
if CONTRIB_FILE.exists():
    _contrib = json.loads(CONTRIB_FILE.read_text())
    CONTRIB_ID = need(_contrib, 'record_tag', 'contrib/registry/contrib.json')
    CONTRIB_SOURCE = ('read from contrib/registry/contrib.json#record_tag at '
                      'build time; that pack in turn reads this registry for '
                      'its destinations, and says on every row that nothing '
                      'is sent')
else:
    CONTRIB_ID = 'tc-contribution/1'
    CONTRIB_SOURCE = ('the brief; contrib/registry/contrib.json was not '
                      'present when this was built, so the id is AUTHORED '
                      'from the name the brief gave and nothing about the '
                      'package shape is claimed here')

CONTRIBUTION = {
    'id': CONTRIB_ID,
    'source': CONTRIB_SOURCE,
    'what_it_is': 'a learner\'s training-data contribution, packaged in '
                  'the browser from records this bundle already keeps '
                  '(completions, sim episodes) - a file a learner holds, '
                  'not something any server has received',
    'what_it_is_not': 'not sent anywhere by this bundle, not signed for '
                      'any chain, not hashed to any IPFS CID, not '
                      'registered with any protocol below',
    'provenance': 'AUTHORED',
}

# ------------------------------------------------------------------ roster ---
OFF = {
    'configured': False,
    'integrated': False,
    'validated_against_spec': False,
}
NOT_FETCHED = 'NOT fetched - the probe below is what happened when the host was asked'
WHY_OFF = ('this bundle is static files with no server, holds no key, no '
           'SDK, no contract address and no RPC, and this build read none '
           'of the protocol\'s own text; flipping any of these three flags '
           'would be a lie until a human has done the work named under '
           '`this_bundle_would_need` and read the spec')


def entry(pid, name, host, url, what, unit, contribution_becomes,
          bundle_needs, server_side_missing, identified=True,
          unidentified_why=None, nearest_real_offering=None):
    e = {
        'id': pid,
        'name': name,
        'url': url,
        'url_status': NOT_FETCHED if url is not None else 'none given',
        'unidentified': not identified,
        'what_it_is': what,
        'unit': unit,
        'contribution_would_become': contribution_becomes,
        'this_bundle_would_need': bundle_needs,
        'server_side_missing': server_side_missing,
        **OFF,
        'why_off': WHY_OFF,
        'spec_fetched': probe_record(host) if host is not None else {
            'fetched': False,
            'url_tried': None,
            'http_code': None,
            'curl_exit': None,
            'date': PROBE_DATE,
            'how': 'not probed: no URL could be named with confidence for '
                   'this entry, so there was nothing to ask',
            'meaning': 'nothing was tried, so nothing was recorded',
            'provenance': 'RECORDED',
        },
        'description_provenance': 'AUTHORED from general knowledge - this '
                                  'build read none of the protocol\'s own '
                                  'text (see spec_fetched) and the '
                                  'description may be stale or wrong in '
                                  'detail',
        'provenance': 'AUTHORED',
    }
    if not identified:
        if not unidentified_why:
            raise ValueError(f'protocols: {pid} is unidentified and says not why')
        e['unidentified_why'] = unidentified_why
    if nearest_real_offering is not None:
        e['nearest_real_offering'] = nearest_real_offering
    return e


NO_SERVER = ('a running process this bundle does not have: static files '
             'served from file:// or GitHub Pages cannot host one')

ROSTER = [
    entry(
        'virtuals-protocol', 'Virtuals Protocol', 'virtuals.io',
        'https://virtuals.io/',
        what='a launchpad and framework for tokenised AI agents, mainly on '
             'the Base chain, where each agent is issued its own ERC-20 '
             'token through a bonding curve against VIRTUAL, and agents '
             'transact with one another through the project\'s own agent '
             'commerce protocol',
        unit='a token-gated agent (an agent with its own token, whose '
             'holders gate access to it)',
        contribution_becomes='training data or a persona/knowledge module '
                             'behind one launched agent, gated by that '
                             'agent\'s token - the contribution itself is '
                             'not a chain object; the agent and its token '
                             'are',
        bundle_needs=[
            'an agent launched through the Virtuals launchpad, which means '
            'a wallet on Base holding ETH for gas and VIRTUAL for the '
            'bonding curve - this bundle holds no wallet and no funds',
            'the launched agent\'s token contract address and the '
            'launchpad\'s factory address on Base - none is typed here '
            'because none was read from the protocol',
            'the agent framework SDK and an API key for it, plus a Base '
            'JSON-RPC endpoint - none is vendored, held or called',
        ],
        server_side_missing=[
            'a process that runs the agent and answers holders - ' + NO_SERVER,
            'a key custodian for the agent\'s treasury and signing key',
        ]),
    entry(
        'virtual-ventures', 'Virtual Ventures', None, None,
        what='not identified: the name does not match a protocol, product '
             'or SDK this author can place with confidence',
        unit='unknown - no unit can be named for a product that was not '
             'identified',
        contribution_becomes='unknown',
        bundle_needs=['first, an identification: a URL or a document that '
                      'says what "Virtual Ventures" is'],
        server_side_missing=['unknown until the product is identified'],
        identified=False,
        unidentified_why='"Virtual Ventures" could be an ecosystem or '
                         'venture arm around Virtuals Protocol, a '
                         'generically named venture fund, or a product '
                         'this author has never seen; with no network to '
                         'check and no confident recollection, recording '
                         'a guess as a product would invent one, so it is '
                         'recorded unidentified. The lead can replace this '
                         'entry the day a URL is supplied.'),
    entry(
        'singularitynet', 'SingularityNET', 'singularitynet.io',
        'https://singularitynet.io/',
        what='a decentralised marketplace for AI services: a service is '
             'published with a protobuf/gRPC interface and metadata pinned '
             'to IPFS, registered under an organisation in an on-chain '
             'registry contract, served by the project\'s daemon in front '
             'of the provider\'s own endpoint, and paid for in the '
             'network token (AGIX, migrating to FET under the ASI '
             'Alliance) through payment channels; the AI Publisher portal '
             'and snet-cli are the publishing surfaces',
        unit='a marketplace service (an organisation + service id in the '
             'registry, with a live endpoint behind the daemon)',
        contribution_becomes='an input to a service somebody hosts - a '
                             'contribution is not itself a service; it '
                             'would have to be wrapped by a model or an '
                             'endpoint that answers gRPC calls',
        bundle_needs=[
            'an organisation and a service id registered through snet-cli '
            'or the AI Publisher, by a wallet holding ETH and the network '
            'token - this bundle holds neither',
            'service metadata and a protobuf definition pinned to IPFS, '
            'and the registry contract address on Ethereum - none is held '
            'or typed here',
            'snet-cli / snet-sdk and an Ethereum JSON-RPC endpoint - none '
            'is vendored, installed or called',
        ],
        server_side_missing=[
            'the snet-daemon and the service endpoint it fronts - ' + NO_SERVER,
            'a payment-channel signer for the provider side',
        ]),
    entry(
        'fetch-ai-asi', 'Fetch.ai / ASI Alliance agents', 'fetch.ai',
        'https://fetch.ai/',
        what='autonomous agents written with the uAgents Python framework, '
             'registered in the Almanac contract on the Fetch.ai Cosmos-SDK '
             'chain and discoverable through Agentverse; Fetch.ai, '
             'SingularityNET and Ocean Protocol combined into the '
             'Artificial Superintelligence (ASI) Alliance with FET as the '
             'shared token (superintelligence.io was probed too and did '
             'not answer)',
        unit='a registered agent (a uAgent with an Almanac entry and, '
             'usually, an Agentverse listing)',
        contribution_becomes='a dataset an agent serves or trains on, or a '
                             'protocol message the agent handles - the '
                             'contribution needs an agent around it',
        bundle_needs=[
            'a uAgents runtime and an agent seed/key, and an Agentverse '
            'API key if hosted there - none is held',
            'an Almanac registration paid in FET from a Cosmos wallet, and '
            'the Almanac contract address and a chain RPC/REST endpoint - '
            'none is held, typed or called',
        ],
        server_side_missing=[
            'the running agent process (or an Agentverse-hosted one) - ' + NO_SERVER,
            'a mailbox or endpoint the agent receives messages at',
        ]),
    entry(
        'olas', 'Olas (Autonolas)', 'olas.network',
        'https://olas.network/',
        what='a network for autonomous agent services co-owned on-chain: '
             'components, agents and services are registered as NFTs in '
             'on-chain registries (Ethereum, Gnosis and other chains), '
             'built with the Open Autonomy / open-aea frameworks, run by '
             'operators, and rewarded through staking programmes',
        unit='a registered component, agent or service (an NFT in the '
             'Olas registries, its package hashed to IPFS)',
        contribution_becomes='a package - a dataset component or a skill '
                             'inside an agent - hashed to IPFS and minted '
                             'into the component registry, or an input to '
                             'a service an operator runs',
        bundle_needs=[
            'the Open Autonomy tooling to package and hash the '
            'contribution, and an IPFS node or pinning service - none is '
            'vendored or reachable',
            'an owner wallet on the chosen chain holding gas for the '
            'registry mint, and the registry contract addresses and a '
            'chain RPC - none is held, typed or called',
        ],
        server_side_missing=[
            'an operator running the agent service - ' + NO_SERVER,
            'a key custodian for the operator and the service safe',
        ]),
    entry(
        'bittensor', 'Bittensor subnets', 'bittensor.com',
        'https://bittensor.com/',
        what='a Substrate-based network of subnets, each defining its own '
             'incentive mechanism: miners produce work (models, inference, '
             'data), validators score it, and TAO is emitted to both '
             'according to the scores; subnet registration and neuron '
             'registration cost TAO, and btcli / the bittensor Python SDK '
             'are the tooling',
        unit='a subnet dataset - work a miner submits to a data-oriented '
             'subnet\'s incentive mechanism, or a dataset a subnet owner '
             'defines the mechanism around',
        contribution_becomes='a miner\'s submission scored by that '
                             'subnet\'s validators - the contribution '
                             'earns nothing and exists nowhere on the '
                             'network unless a registered miner serves it',
        bundle_needs=[
            'a coldkey/hotkey wallet pair holding TAO for neuron '
            'registration on a named subnet (a netuid) - none is held',
            'the bittensor SDK / btcli and a subtensor RPC endpoint - '
            'none is installed or called',
        ],
        server_side_missing=[
            'a running miner (an axon the validators can query) - ' + NO_SERVER,
            'the subnet\'s own validator/miner code, which is per-subnet '
            'and was not read',
        ]),
    entry(
        'ocean-protocol', 'Ocean Protocol data NFTs', 'oceanprotocol.com',
        'https://oceanprotocol.com/',
        what='a data-exchange protocol where a dataset is published as an '
             'ERC-721 data NFT with ERC-20 datatokens that grant access, '
             'its metadata (a DDO) indexed by Aquarius and access served '
             'by a Provider, optionally as compute-to-data; ocean.py and '
             'ocean.js are the libraries and Ocean Market the storefront; '
             'Ocean is a member of the ASI Alliance',
        unit='a data NFT plus a datatoken (the on-chain pair that '
             'represents one published dataset)',
        contribution_becomes='the asset behind one data NFT: the '
                             'contribution file hosted at a URL a Provider '
                             'can serve, its DDO published, access sold as '
                             'datatokens',
        bundle_needs=[
            'a wallet on a supported chain holding gas (and OCEAN for '
            'pricing) - none is held',
            'ocean.py or ocean.js, the ERC-721 factory contract address on '
            'that chain, and a chain RPC - none is vendored, typed or '
            'called',
            'a URL where the contribution file is hosted for the Provider '
            'to serve - this bundle serves nothing',
        ],
        server_side_missing=[
            'a Provider and Aquarius (or the use of hosted ones, which '
            'still needs the asset hosted somewhere) - ' + NO_SERVER,
        ]),
    entry(
        'cloudflare-wallets', 'Cloudflare wallets', 'developers.cloudflare.com',
        'https://developers.cloudflare.com/web3/',
        what='not identified as a product: this author knows of no '
             'Cloudflare wallet. Cloudflare\'s real Web3 offering, from '
             'recollection, is a set of gateways - an Ethereum JSON-RPC '
             'gateway and an IPFS gateway - which hold no keys and sign '
             'nothing',
        unit='none - a gateway is a read/relay endpoint, not a unit a '
             'contribution can become',
        contribution_becomes='nothing on its own; a gateway could at most '
                             'be the RPC or IPFS endpoint another '
                             'protocol above is reached through',
        bundle_needs=['an identification first: if "Cloudflare wallets" '
                      'names a product this author does not know, a URL '
                      'for it; if it means the gateways, a Cloudflare '
                      'account and a gateway hostname, which would still '
                      'not be a wallet'],
        server_side_missing=['not applicable until the product is '
                             'identified; the gateways are Cloudflare\'s '
                             'servers, not this bundle\'s'],
        identified=False,
        unidentified_why='no Cloudflare product called a wallet could be '
                         'identified with confidence; the nearest real '
                         'offering is named beside this entry and is a '
                         'gateway, not a wallet. Recording it as a wallet '
                         'rail would invent a product.',
        nearest_real_offering={
            'name': 'Cloudflare Web3 Gateways (Ethereum Gateway, IPFS '
                    'Gateway)',
            'is_a_wallet': False,
            'what': 'hosted read/relay endpoints for the Ethereum JSON-RPC '
                    'API and for IPFS content, run by Cloudflare; a '
                    'wallet holds keys and signs, a gateway does neither',
            'caveat': 'AUTHORED from recollection - the developer docs '
                      'were probed and did not answer, so the current '
                      'status of these gateways (this author recalls the '
                      'public IPFS gateway being wound down) is not '
                      'known to this build',
            'provenance': 'AUTHORED',
        }),
]

IDS = [e['id'] for e in ROSTER]
assert len(set(IDS)) == len(IDS), 'a roster id repeats'
for e in ROSTER:
    for f in ('id', 'name', 'url', 'url_status', 'unidentified', 'what_it_is',
              'unit', 'contribution_would_become', 'this_bundle_would_need',
              'server_side_missing', 'configured', 'integrated',
              'validated_against_spec', 'why_off', 'spec_fetched',
              'description_provenance', 'provenance'):
        if f not in e:
            raise KeyError(f'protocols: {e["id"]}.{f} is missing')
    if e['configured'] is not False or e['integrated'] is not False \
            or e['validated_against_spec'] is not False:
        raise ValueError(f'protocols: {e["id"]} claims to be configured, '
                         'integrated or validated - nothing in a bundle '
                         'with no server, no key and no spec read can be')
    if e['provenance'] not in TIERS:
        raise ValueError(f'protocols: {e["id"]}.provenance not a tier')
    if not e['this_bundle_would_need'] or not e['server_side_missing']:
        raise ValueError(f'protocols: {e["id"]} names nothing missing')
    sf = e['spec_fetched']
    if sf['fetched'] is not False:
        raise ValueError(f'protocols: {e["id"]} says its spec was fetched; '
                         'the probe discards every body')

# ----------------------------------------------------------------- wallets ---
# What the sign-in pack already supports is READ from auth.json, never
# retyped: the rail is the method whose kind is wallet-signature and whose
# configured flag is exactly true.
AUTH = json.loads((ROOT / 'auth' / 'registry' / 'auth.json').read_text())
AUTH_METHODS = need(AUTH, 'methods', 'auth/registry/auth.json')
SIWE = need(AUTH_METHODS, 'siwe-ethereum', 'auth.methods')
assert need(SIWE, 'kind', 'auth.methods.siwe-ethereum') == 'wallet-signature'
assert need(SIWE, 'configured', 'auth.methods.siwe-ethereum') is True
SIWE_SPEC = need(AUTH, 'siwe', 'auth/registry/auth.json')

SUPPORTED_RAILS = [{
    'id': 'siwe-ethereum',
    'name': 'Sign-In with Ethereum (EIP-4361) over any EIP-1193 provider',
    'read_from': 'auth/registry/auth.json#methods.siwe-ethereum',
    'configured': True,
    'provider': 'window.ethereum - any EIP-1193 injected provider (a '
                'browser-extension or in-app wallet); no specific wallet '
                'vendor is named, required or detected',
    'signing_method': need(SIWE_SPEC, 'signing_method', 'auth.siwe'),
    'chain_id': need(SIWE_SPEC, 'chain_id', 'auth.siwe'),
    'verified_in_page': need(need(SIWE_SPEC, 'verification', 'auth.siwe'),
                             'implemented', 'auth.siwe.verification'),
    'authenticates': need(SIWE, 'authenticates', 'auth.methods.siwe-ethereum'),
    'gates_anything': need(SIWE, 'gates_anything', 'auth.methods.siwe-ethereum'),
    'what_it_is_for_here': 'naming which address a training record on '
                           'this device belongs to - consent to a sentence, '
                           'verified in the page; it sends no transaction, '
                           'holds no funds and reaches no chain',
    'could_it_hand_a_contribution_to_a_protocol': 'no - it signs a message, '
                                                  'not a transaction, and '
                                                  'this bundle builds no '
                                                  'transaction for any '
                                                  'protocol above',
    'provenance': 'DERIVED from auth/registry/auth.json',
}]

RAIL_OFF = {'configured': False, 'integrated': False}
CANDIDATE_RAILS = [
    {'id': 'walletconnect',
     'name': 'WalletConnect (a relay to mobile and remote wallets)',
     **RAIL_OFF,
     'would_take': ['a WalletConnect project id registered with its '
                    'cloud - an account this bundle does not have',
                    'the WalletConnect client library, vendored or fetched '
                    '- web/lint_external.mjs polices what a page may '
                    'fetch, so this is a decision, not a script tag',
                    'a relay server the page talks to, which is a network '
                    'dependency the sign-in page today does not have'],
     'reaches': 'the same EIP-4361 flow, so the protocols on Base and '
                'Ethereum (Virtuals, SingularityNET, Olas, Ocean) - for '
                'signing a message, still not for any transaction this '
                'bundle does not build',
     'provenance': 'AUTHORED'},
    {'id': 'solana-wallet-standard',
     'name': 'Sign-In with Solana over the Wallet Standard (ed25519)',
     **RAIL_OFF,
     'would_take': ['an ed25519 signature verifier in the page, held to an '
                    'oracle the way auth/test.mjs holds secp256k1 - '
                    'written and tested, not assumed',
                    'a Wallet Standard / window.solana provider detection '
                    'and a sign-in message format authored from the spec, '
                    'which this build could not read'],
     'reaches': 'the Solana side of Virtuals Protocol, if a learner\'s '
                'agent lives there',
     'provenance': 'AUTHORED'},
    {'id': 'cosmos-adr36',
     'name': 'Cosmos arbitrary-message signing (ADR-36) via a Keplr-style '
             'provider (secp256k1)',
     **RAIL_OFF,
     'would_take': ['bech32 address derivation and the ADR-36 sign-doc '
                    'shape, authored from a spec this build could not read',
                    'a provider detection for window.keplr or the Cosmos '
                    'wallet standard'],
     'reaches': 'Fetch.ai / ASI Alliance agents, whose chain is Cosmos-SDK',
     'provenance': 'AUTHORED'},
    {'id': 'substrate-sr25519',
     'name': 'Substrate signing via a polkadot.js-style extension (sr25519)',
     **RAIL_OFF,
     'would_take': ['an sr25519 verifier - a Schnorr scheme over '
                    'Ristretto255 that no page in this bundle implements, '
                    'and that would need an oracle to be trusted',
                    'SS58 address handling and the extension\'s injected '
                    'provider API'],
     'reaches': 'Bittensor, whose wallets are Substrate keys',
     'provenance': 'AUTHORED'},
    {'id': 'cloudflare-wallets',
     'name': 'Cloudflare wallets',
     **RAIL_OFF,
     'unidentified': True,
     'unidentified_why': 'see the roster entry of the same id: no Cloudflare '
                         'wallet product could be identified, and its Web3 '
                         'gateways are not a wallet, so there is no rail to '
                         'describe',
     'would_take': ['an identification first'],
     'reaches': 'nothing that can be named',
     'provenance': 'AUTHORED'},
]

WALLETS = {
    'supported': SUPPORTED_RAILS,
    'candidates': CANDIDATE_RAILS,
    'rule': 'a rail is supported only when auth/registry/auth.json carries '
            'it with configured true and auth/test.mjs holds its verifier '
            'to an oracle; every candidate here is OFF, and adding one is a '
            'code change in auth/ plus a suite, not a flag here',
    'none_sends_anything': 'no rail, supported or candidate, builds or '
                           'sends a transaction; the supported one signs a '
                           'sentence and the page verifies it. Handing a '
                           'contribution to any protocol above would need a '
                           'transaction built for that protocol\'s '
                           'contracts, and none is built here.',
}

# ----------------------------------------------------------------- honesty ---
N = len(ROSTER)
N_UNID = sum(1 for e in ROSTER if e['unidentified'] is True)
N_ID = N - N_UNID
N_CONF = sum(1 for e in ROSTER if e['configured'] is True)
N_INT = sum(1 for e in ROSTER if e['integrated'] is True)
N_VAL = sum(1 for e in ROSTER if e['validated_against_spec'] is True)
N_FETCHED = sum(1 for e in ROSTER if e['spec_fetched']['fetched'] is True)
N_PROBED = sum(1 for e in ROSTER if e['spec_fetched']['url_tried'] is not None)
N_URLS_TRIED = len(PROBE_BY_HOST)
assert N_CONF == 0 and N_INT == 0 and N_VAL == 0 and N_FETCHED == 0

HONESTY = {
    'status': 'AUTHORED. Every description in this roster is written from '
              'general knowledge by this build and says so on the entry; '
              'the only RECORDED facts are the probe codes, and they '
              'record that nothing answered.',
    'nothing_integrates': f'all {N} entries carry configured false, '
                          'integrated false and validated_against_spec '
                          'false. This bundle integrates with, sends to, '
                          'mints on, registers with or lists on none of '
                          'them: no SDK is vendored, no key is held, no '
                          'contract address is typed, no RPC is called, '
                          'no transaction is built.',
    'no_backend': 'This bundle is static HTML built from registries and '
                  'served from a file or from GitHub Pages. Every protocol '
                  'above needs a running process on the provider side - a '
                  'daemon, an agent, an operator, a miner, a data provider '
                  '- and this bundle has none.',
    'descriptions_may_be_wrong': 'None of the eight hosts answered the '
                                 f'probe on {PROBE_DATE}, so no site, spec '
                                 'or SDK document was read. Names of '
                                 'tokens, chains, contracts and tooling are '
                                 'recollection and may be stale: the '
                                 'signal that one is wrong is a human with '
                                 'the spec open, not a passing test.',
    'unidentified_are_unidentified': f'{N_UNID} of {N} names the brief '
                                     'gave could not be identified with '
                                     'confidence and are recorded '
                                     'unidentified with the reason, rather '
                                     'than mapped to a plausible product: '
                                     + ', '.join(e['id'] for e in ROSTER
                                                 if e['unidentified']) + '.',
    'wallets': 'one rail is supported and it signs a sentence, not a '
               'transaction; it is read from auth/, not restated. Every '
               'other rail is a candidate, off, with what it would take.',
    'what_would_make_one_real': 'for any entry: a human reads that '
                                'protocol\'s current documentation, a '
                                'server-side process is stood up under '
                                'somebody\'s custody, keys and funds are '
                                'held by that somebody, a transaction is '
                                'built and tested against a testnet, and '
                                'only then is the entry\'s configured flag '
                                'flipped - a configuration change after '
                                'real work, never a flag flipped here.',
}

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

payload = {
    'pack': 'protocols',
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'contribution_package': CONTRIBUTION,
    'reachability_probe': {
        'date': PROBE_DATE,
        'how': PROBE_HOW,
        'file': 'protocols/authored/probe.json',
        'tried': [PROBE_BY_HOST[h] for h in sorted(PROBE_BY_HOST)],
        'answered_2xx': N_PROBE_2XX,
        'provenance': need(PROBE, 'provenance', 'authored/probe.json'),
        'why_a_file': 'the probe was run once by hand and copied into a '
                      'stamped file; the build reads that file and '
                      'fetches nothing, so a rebuild is byte-identical and '
                      'the date is the date of the measurement',
    },
    'provenance_tiers': list(TIERS),
    'counts': {
        'protocols': N,
        'identified': N_ID,
        'unidentified': N_UNID,
        'configured': N_CONF,
        'integrated': N_INT,
        'validated_against_spec': N_VAL,
        'specs_fetched': N_FETCHED,
        'roster_entries_probed': N_PROBED,
        'probe_urls_tried': N_URLS_TRIED,
        'probe_answered_2xx': N_PROBE_2XX,
        'wallet_rails_supported': len(SUPPORTED_RAILS),
        'wallet_rails_candidate': len(CANDIDATE_RAILS),
        'wallet_rails_configured': sum(
            1 for r in SUPPORTED_RAILS + CANDIDATE_RAILS
            if r['configured'] is True),
    },
    'protocols': {e['id']: e for e in ROSTER},
    'wallets': WALLETS,
}

blob = json.dumps(payload).upper()
assert 'AI-SYNTHESIZED' not in blob, 'protocols: that tier belongs to orbis/'

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + '\n')
print(f'protocols: {N} protocols on the roster - {N_ID} identified, '
      f'{N_UNID} unidentified ({", ".join(e["id"] for e in ROSTER if e["unidentified"])}); '
      f'{N_CONF} configured, {N_INT} integrated, {N_FETCHED} specs fetched '
      f'({N_PROBED} entries probed, {N_URLS_TRIED} URLs tried on {PROBE_DATE}, '
      f'{N_PROBE_2XX} answered 2xx); '
      f'wallet rails {len(SUPPORTED_RAILS)} supported, {len(CANDIDATE_RAILS)} '
      f'candidates off (source stamp {stamp})')
