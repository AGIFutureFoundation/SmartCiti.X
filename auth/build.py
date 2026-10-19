#!/usr/bin/env python3
"""auth/ - who this learner is, said only as far as it can honestly be said.

THE ASK, AND WHY MOST OF IT CANNOT BE HONOURED HERE

The request was "a google/microsoft/email or crypto sign in option ... to
enhance user security". Three of those four cannot be delivered by this
bundle, and the reason is not effort or time: it is that this bundle is
static HTML built from registries and served off a file:// path or GitHub
Pages. There is no server anywhere in it.

  - Google and Microsoft sign-in are OAuth 2.0 authorization-code flows.
    The code is exchanged for tokens by a party that holds a CLIENT SECRET
    and receives the redirect. A static page can hold neither. A page that
    popped a Google button and then set a local flag would tell a learner
    they were authenticated when nothing authenticated them - on a product
    that carries training records, that is worse than offering no sign-in
    at all, because it invites reliance.
  - Email sign-in needs something that can send the link or the code, and
    something that can remember which codes are still live. Same wall.
  - A wallet signature (EIP-4361) IS genuinely producible in a browser and
    genuinely verifiable in a browser. So that one is real here. But
    verification in the page GATES NOTHING, because anyone can edit the
    page. It proves the holder of an address consented to a sentence. It
    does not protect a record from anybody.

So this pack ships two things that work and claim exactly what they do,
and three ADAPTERS THAT FAIL CLOSED: each names the flow it would need and
the precise server-side piece that is missing, carries configured false,
and is rendered as a disabled control whose own label says what is absent.
The single guard in web/build_auth.py's page refuses to write an identity
for any method whose `configured` is not exactly true, so the day a
backend exists this becomes a configuration change and until then nothing
in the page can pretend.

WHAT "LOCAL IDENTITY" IS, STATED WHERE A READER CANNOT MISS IT

It names whose training record this is, on this device. tc-progress and
tc-training already exist in this bundle and already hold completions and
sim episodes; today they belong to a browser. A local identity makes them
belong to a name. That is the entire claim. It is not authentication, it
is not a login, it verifies nothing, and it protects nothing from anyone
who can open the device. Every method record therefore carries
`authenticates: false` and `gates_anything: false` - including the wallet
one - and the suite refuses a payload in which any method says otherwise.

PROVENANCE

Every record here is AUTHORED. Note in particular that the EIP-4361 field
list and its order are AUTHORED FROM RECOLLECTION: this build has no
network and did not open the EIP. If the recollection is wrong, the signal
is a wallet that refuses or mangles the message, not a passing test - and
that is written into the registry rather than left for someone to find.

What is NOT authored is the verification claim. The page's keccak-256, its
secp256k1 public-key recovery and its address derivation are exercised by
auth/test.mjs against oracles that are not this pack's own code, and the
registry records which oracles, so the claim "the signature is verified in
the page" can be audited rather than believed.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'auth.json'

PACK_VERSION = json.loads(
    (ROOT / 'pack' / 'manifest.json').read_text())['pack_version']

# The records a name would attach to. Read, never retyped: the training key
# is the training pack's own, and the progress key is the one the walkable
# page actually uses - the suite re-greps both out of their sources.
TRAINING = json.loads((ROOT / 'training' / 'registry' / 'training.json').read_text())
PROGRESS_KEY = 'tc-progress'
IDENTITY_KEY = 'tc-identity'

TIERS = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED')

# ---------------------------------------------------------------------------
# EIP-4361. Order matters: a wallet renders these lines to a human, and a
# verifier re-derives the message from its parts. AUTHORED from recollection.

SIWE_FIELDS = [
    ('domain', 'the origin asking, on its own first line, so the human '
               'reading the wallet prompt sees who asked'),
    ('address', 'the checksummed account being claimed'),
    ('statement', 'one sentence the human is agreeing to, verbatim'),
    ('uri', 'the exact page that asked'),
    ('version', 'the EIP-4361 version, 1'),
    ('chain-id', 'the chain the account is claimed on'),
    ('nonce', 'fresh per attempt, so a captured signature cannot be '
              'replayed into a later attempt'),
    ('issued-at', 'when this attempt was made, ISO-8601'),
]

SIWE_STATEMENT = (
    'I am naming this Ethereum account as the owner of the Trade Craft '
    'Academy training record kept in this browser. This signature does not '
    'log me in, does not reach any server, and protects nothing: this '
    'bundle has no backend.'
)

# The claim "the page verifies the signature" is only worth what checks it.
VERIFICATION = {
    'implemented': True,
    'where': 'in the page itself, in the AUTH-CORE region of '
             'web/trade_craft_signin.html - no library is fetched and none '
             'is vendored; the code is short enough to read in one sitting',
    'method': 'keccak-256 over the EIP-191 personal-sign preimage, then '
              'secp256k1 public-key recovery from (r, s, v), then the '
              'address as the low 20 bytes of keccak-256 of the '
              'uncompressed public key, EIP-55 checksummed',
    'claims_verified_only_when': 'the recovered address equals the address '
                                 'the wallet reported, compared as lowercase '
                                 'hex. There is no other branch that reports '
                                 'a signature as verified.',
    'oracles': [
        'the Keccak-f[1600] permutation the page ships is driven in SHA3-256 '
        'mode (the same sponge, pad byte 0x06 instead of 0x01) and compared '
        'against node:crypto\'s own sha3-256 - an implementation this pack '
        'did not write',
        'secp256k1 recovery is checked against signatures produced by '
        'node:crypto with namedCurve secp256k1: the page reconstructs the '
        'exact public key node generated, over many random keys. node will '
        'not sign a digest it did not compute - crypto.sign hashes with '
        'SHA-256 whatever algorithm is named - so the oracle is applied one '
        'level down, to the curve arithmetic, which is the part no test '
        'could fake',
        'the published addresses of the private keys 1, 2 and 3 are '
        'reproduced by the page\'s own curve, keccak and EIP-55 code; the '
        'first of them is reproduced end to end from a personal_sign '
        'signature over an EIP-191 preimage',
        'a tampered signature is required to recover a DIFFERENT address, so '
        'a stub that returned the claimed address would fail',
    ],
    'if_this_were_false': 'were recovery not implemented, this field would '
                          'read false, the page would say the signature was '
                          'produced but NOT verified here, and no identity '
                          'would be written from it. An unverified signature '
                          'presented as verified is the one lie this bundle '
                          'exists not to tell.',
}

# ---------------------------------------------------------------------------
# the five methods

METHODS = {}

METHODS['local-identity'] = {
    'label': 'Name this device\'s training record',
    'kind': 'local-label',
    'flow': 'a name typed into this page and kept in this browser\'s '
            'localStorage under ' + IDENTITY_KEY,
    'configured': True,
    'sets_identity': True,
    'requires_verified_signature': False,
    'authenticates': False,
    'gates_anything': False,
    'needs_network': False,
    'what_it_claims': 'that the completions in ' + PROGRESS_KEY + ' and the '
                      'sim episodes in ' + TRAINING['storage']['key'] + ' on '
                      'THIS device belong to the name typed here.',
    'what_it_does_not_claim': 'It does not verify the name. It does not '
                              'check anything against anyone. Anybody with '
                              'this device can type any name, or open the '
                              'browser\'s storage panel and change it. It '
                              'protects nothing and it is not a login.',
    'provenance': 'AUTHORED',
}

METHODS['siwe-ethereum'] = {
    'label': 'Sign in with an Ethereum wallet (EIP-4361)',
    'kind': 'wallet-signature',
    'flow': 'EIP-4361 message built in the page, signed by the wallet with '
            'personal_sign (EIP-191), and the signer recovered in the page '
            'from the signature',
    'configured': True,
    'sets_identity': True,
    'requires_verified_signature': True,
    'authenticates': False,
    'gates_anything': False,
    'needs_network': False,
    'needs_runtime': 'window.ethereum. With no wallet in the browser this '
                     'method offers nothing and says so; it does not fall '
                     'back to anything.',
    'what_it_claims': 'that whoever held the private key for this address, '
                      'at the moment they were asked, consented to the '
                      'statement below - and that the page checked that by '
                      'recovering the address from the signature rather '
                      'than taking the wallet\'s word for it.',
    'what_it_does_not_claim': 'It is not a login and it gates nothing. '
                              'Verification happens in a page anyone can '
                              'edit, so it is evidence to the person reading '
                              'it, not a control over anybody else. It does '
                              'not prove who the person is, only that a key '
                              'was available to them. A stolen key signs '
                              'just as well.',
    'statement': SIWE_STATEMENT,
    'provenance': 'AUTHORED',
    'spec_provenance': 'the EIP-4361 field list and order in this registry '
                       'are AUTHORED FROM RECOLLECTION - this build has no '
                       'network and did not open the EIP. A wallet that '
                       'refuses or mis-renders the message is the signal '
                       'that the recollection is wrong; no test here can be.',
}

ISSUERS = [
    ('google-oidc', 'Google', 'Sign in with Google',
     'OAuth 2.0 authorization code with PKCE, over OpenID Connect',
     'Google sign-in needs an authorization-code exchange on a server; '
     'this bundle has no server, so it is off.',
     ['an HTTPS redirect URI under our control that can receive the '
      'authorization code - a file:// path or a GitHub Pages file cannot '
      'receive and hold one',
      'a server-side token exchange that presents the OAuth client secret '
      'to Google\'s token endpoint; a static page cannot keep a secret, so '
      'shipping one would publish it',
      'server-side validation of the id_token signature, issuer, audience '
      'and nonce against Google\'s published keys',
      'a session the server issues and can revoke - a flag in localStorage '
      'is not a session, and revoking it protects nobody']),
    ('microsoft-entra', 'Microsoft', 'Sign in with Microsoft',
     'OAuth 2.0 authorization code with PKCE against Microsoft Entra ID',
     'Microsoft sign-in needs an authorization-code exchange on a server, '
     'and a registered tenant and redirect URI; this bundle has no server, '
     'so it is off.',
     ['a registered application in a Microsoft Entra ID tenant, which is an '
      'organisational decision nobody has made for this bundle',
      'an HTTPS redirect URI under our control that can receive the '
      'authorization code',
      'a server-side token exchange holding the client secret or '
      'certificate; a static page cannot hold either',
      'server-side validation of the id_token against the tenant\'s keys, '
      'and a session the server issues and can revoke']),
    ('email-link', 'Email', 'Sign in with an email link',
     'a one-time link or code mailed to the address, redeemed once',
     'Email sign-in needs something that can send mail and remember which '
     'codes are still live; this bundle has no server, so it is off.',
     ['a mail sender that can actually deliver the link or the code',
      'a server-side store of issued tokens with an expiry, so a link works '
      'once and then stops working',
      'rate limiting and replay control on the endpoint that redeems them, '
      'or the mailbox becomes the attack surface',
      'a session the server issues and can revoke']),
]

for (mid, issuer, label, flow, off_label, missing) in ISSUERS:
    METHODS[mid] = {
        'label': label,
        'issuer': issuer,
        'kind': 'federated-issuer',
        'flow': flow,
        'configured': False,
        'sets_identity': False,
        'requires_verified_signature': False,
        'authenticates': False,
        'gates_anything': False,
        'needs_network': True,
        'disabled': True,
        'disabled_label': off_label,
        'missing_server_side': missing,
        'what_it_claims': 'nothing. This adapter is off and cannot be '
                          'switched on from inside the page.',
        'what_it_does_not_claim': 'It never writes an identity. The page\'s '
                                  'single identity writer refuses any method '
                                  'whose configured is not exactly true, and '
                                  'the control is rendered disabled, so a '
                                  'click reports what is missing and nothing '
                                  'else happens.',
        'becomes_available_when': 'the pieces above exist and this record is '
                                  'flipped to configured true - a '
                                  'configuration change, not a code change, '
                                  'and not something the page can do to '
                                  'itself.',
        'provenance': 'AUTHORED',
    }

# ---------------------------------------------------------------------------
# refusals this build makes rather than trusts a reviewer to notice

for mid, m in METHODS.items():
    for field in ('label', 'kind', 'flow', 'configured', 'sets_identity',
                  'authenticates', 'gates_anything', 'what_it_claims',
                  'what_it_does_not_claim', 'provenance'):
        if field not in m:
            raise KeyError('auth: methods.%s.%s is missing - a default here '
                           'would be a policy decision about somebody\'s '
                           'training record' % (mid, field))
    if m['provenance'] not in TIERS:
        raise ValueError('auth: methods.%s.provenance %r is not one of %r'
                         % (mid, m['provenance'], TIERS))
    if m['authenticates'] is not False or m['gates_anything'] is not False:
        raise ValueError('auth: methods.%s claims to authenticate or to gate '
                         'something. Nothing in a bundle with no server can '
                         'do either.' % mid)
    if m['configured'] is not True and m['sets_identity'] is not False:
        raise ValueError('auth: methods.%s is unconfigured but may set an '
                         'identity - that is the exact failure this pack '
                         'exists to prevent' % mid)
    if m['configured'] is not True:
        for field in ('disabled', 'disabled_label', 'missing_server_side',
                      'becomes_available_when'):
            if field not in m:
                raise KeyError('auth: methods.%s.%s is missing - an off '
                               'switch that does not say what is missing is '
                               'just a broken button' % (mid, field))
        if not m['missing_server_side']:
            raise ValueError('auth: methods.%s names nothing missing' % mid)

off = sorted(k for k, m in METHODS.items() if m['configured'] is not True)
on = sorted(k for k, m in METHODS.items() if m['configured'] is True)

HONESTY = {
    'status': 'AUTHORED. Every record here is written by this build; none is '
              'a measurement. The one claim that is checked rather than '
              'asserted is that the page verifies a wallet signature, and '
              'siwe.verification names the oracles auth/test.mjs holds it to.',
    'no_backend': 'This bundle is static HTML generated from registries and '
                  'served from a file or from GitHub Pages. There is no '
                  'server, no session, no account and no database anywhere '
                  'in it. Every consequence below follows from that one fact.',
    'nothing_here_authenticates': 'All %d methods carry authenticates false '
                                  'and gates_anything false, the wallet one '
                                  'included. This page cannot tell anyone '
                                  'apart and does not protect one learner\'s '
                                  'record from another.'
                                  % len(METHODS),
    'local_identity_is_a_label': 'A local identity names whose training '
                                 'record this is, on this device. It is not '
                                 'a login. Anyone holding the device can '
                                 'type any name or edit the stored record '
                                 'directly. The page says this next to the '
                                 'field, not in a footnote.',
    'wallet_proves_consent_not_access': 'A verified EIP-4361 signature shows '
                                        'that the holder of a private key '
                                        'consented to a sentence at a moment. '
                                        'The check runs in a page any reader '
                                        'can edit, so it is evidence to the '
                                        'person reading it and a control over '
                                        'nobody.',
    'issuers_fail_closed': '%d of %d methods are issuer adapters that are '
                           'OFF: %s. Each names the flow it would need and '
                           'the server-side piece that is missing, each is '
                           'rendered as a disabled control whose own label '
                           'says what is absent, and the page\'s single '
                           'identity writer refuses any method whose '
                           'configured is not exactly true.'
                           % (len(off), len(METHODS), ', '.join(off)),
    'why_not_a_button_anyway': 'A browser-only "sign in with Google" that '
                               'set a local flag would report a learner as '
                               'authenticated when nothing had authenticated '
                               'them. On a product that carries training '
                               'records that is worse than no sign-in, '
                               'because it invites reliance. So it is not '
                               'here, and what is here says why.',
    'what_would_make_this_real': 'One HTTPS service that holds the client '
                                 'secret, completes the code exchange, '
                                 'validates the id_token and issues a '
                                 'session it can revoke. Until that exists, '
                                 'flipping any configured flag in this file '
                                 'would make the page lie, and the suite '
                                 'would not catch it - the suite checks that '
                                 'the page obeys this registry, not that '
                                 'this registry is true.',
}

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

payload = {
    'pack': 'auth',
    'product': 'who a training record belongs to, said only as far as a '
               'bundle with no server can honestly say it: a device-local '
               'name, a real EIP-4361 wallet signature verified in the page, '
               'and three federated issuer adapters that fail closed',
    'pack_version': PACK_VERSION,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'storage': {
        'identity_key': IDENTITY_KEY,
        'scope': 'this browser only - localStorage, wrapped so a blocked '
                 'store never breaks the page, exactly like ' + PROGRESS_KEY,
        'record_shape': '{ v, method, label, set_at, authenticates: false, '
                        'and for a wallet identity: address, chain_id, '
                        'verified, recovered }',
        'never_leaves_the_device': 'no request is made by this page. There '
                                   'is nowhere for the record to go.',
    },
    'records_named': {
        'progress_key': PROGRESS_KEY,
        'training_key': TRAINING['storage']['key'],
        'what_a_name_attaches_to': 'completions kept under %s and sim '
                                   'episodes kept under %s, both of which '
                                   'already exist in this bundle and today '
                                   'belong to a browser rather than to a '
                                   'person' % (PROGRESS_KEY,
                                               TRAINING['storage']['key']),
    },
    'siwe': {
        'version': '1',
        'chain_id': 1,
        'fields': [f for f, _ in SIWE_FIELDS],
        'field_notes': {f: note for f, note in SIWE_FIELDS},
        'statement': SIWE_STATEMENT,
        'signing_method': 'personal_sign (EIP-191), requested from '
                          'window.ethereum',
        'nonce_bytes': 16,
        'verification': VERIFICATION,
        'no_wallet': 'No Ethereum wallet is present in this browser (there '
                     'is no window.ethereum). There is nothing to sign '
                     'with, and this page offers nothing in its place.',
    },
    'provenance_tiers': list(TIERS),
    'counts': {
        'methods': len(METHODS),
        'configured_true': len(on),
        'configured_false': len(off),
        'issuer_adapters_off': len(off),
        'methods_that_authenticate': sum(
            1 for m in METHODS.values() if m['authenticates'] is True),
        'methods_that_gate_anything': sum(
            1 for m in METHODS.values() if m['gates_anything'] is True),
        'siwe_fields': len(SIWE_FIELDS),
        'missing_server_side_items': sum(
            len(m['missing_server_side']) for m in METHODS.values()
            if m['configured'] is not True),
    },
    'methods': METHODS,
}

blob = json.dumps(payload).upper()
assert 'AI-SYNTHESIZED' not in blob, 'auth: that tier belongs to orbis/'
assert payload['counts']['methods_that_authenticate'] == 0, \
    'auth: nothing in a bundle with no server authenticates anybody'
assert payload['counts']['configured_false'] == 3, \
    'auth: the three federated issuers are off; if that changed, the page ' \
    'text and this assertion both need a human'

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + '\n')
print('auth: %d methods - %d usable (%s), %d issuer adapters OFF (%s) '
      'naming %d missing server-side pieces. Nothing here authenticates: '
      '%d of %d methods claim to.'
      % (len(METHODS), len(on), ', '.join(on), len(off), ', '.join(off),
         payload['counts']['missing_server_side_items'],
         payload['counts']['methods_that_authenticate'], len(METHODS)))
