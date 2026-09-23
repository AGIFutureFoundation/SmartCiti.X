# Sign-in, and what a bundle with no server cannot do

`web/trade_craft_signin.html`, built by `web/build_auth.py` from
`auth/registry/auth.json`: **5 sign-in methods described,
2 that work here, 3 that are off
and say why** — and **0 that authenticate
anybody**.

This bundle is static HTML generated from registries and served from a file or from GitHub Pages. There is no server, no session, no account and no database anywhere in it. Every consequence below follows from that one fact.

![The sign-in page states the limit before the first control](img/signin-page.png)

## The 5 methods

| Method | id | Kind | Configured | Writes an identity | Authenticates | Gates anything |
|---|---|---|---|---|---|---|
| **Name this device's training record** | `local-identity` | local-label | yes | yes | **no** | **no** |
| **Sign in with an Ethereum wallet (EIP-4361)** | `siwe-ethereum` | wallet-signature | yes | yes | **no** | **no** |
| **Sign in with an email link** | `email-link` | federated-issuer | **no** | no | **no** | **no** |
| **Sign in with Google** | `google-oidc` | federated-issuer | **no** | no | **no** | **no** |
| **Sign in with Microsoft** | `microsoft-entra` | federated-issuer | **no** | no | **no** | **no** |

The last two columns are the whole of it: every one of the 5 methods carries `authenticates: false` and
`gates_anything: false`, the wallet one included — 0 of them
authenticate anybody and 0 of them gate anything.

One function in the page writes the identity record, and it refuses any method
whose `configured` is not exactly `true`. That is the safety property, and
`auth/test.mjs` drives it directly rather than reading the source for it.

## Why 3 of them are off

A browser-only "sign in with Google" that set a local flag would report a learner as authenticated when nothing had authenticated them. On a product that carries training records that is worse than no sign-in, because it invites reliance. So it is not here, and what is here says why.

An authorization-code exchange needs a server that holds a client secret. A
static page cannot hold a secret — shipping one publishes it — and it cannot
receive a redirect, validate an `id_token` against an issuer's keys, or issue a
session anybody could revoke. 3 of 5 methods are issuer adapters that are OFF: email-link, google-oidc, microsoft-entra. Each names the flow it would need and the server-side piece that is missing, each is rendered as a disabled control whose own label says what is absent, and the page's single identity writer refuses any method whose configured is not exactly true.

Between them the 3 adapters name **12 missing server-side
pieces**, counted here off the records themselves; the registry's own
`counts.missing_server_side_items` says 12, which
is the same number arrived at twice rather than typed once:

### Sign in with an email link — `configured: false`

*a one-time link or code mailed to the address, redeemed once*

Email sign-in needs something that can send mail and remember which codes are still live; this bundle has no server, so it is off.

What is missing, named rather than implied:

- a mail sender that can actually deliver the link or the code
- a server-side store of issued tokens with an expiry, so a link works once and then stops working
- rate limiting and replay control on the endpoint that redeems them, or the mailbox becomes the attack surface
- a session the server issues and can revoke

It never writes an identity. The page's single identity writer refuses any method whose configured is not exactly true, and the control is rendered disabled, so a click reports what is missing and nothing else happens. It becomes available when the pieces above exist and this record is flipped to configured true - a configuration change, not a code change, and not something the page can do to itself.

### Sign in with Google — `configured: false`

*OAuth 2.0 authorization code with PKCE, over OpenID Connect*

Google sign-in needs an authorization-code exchange on a server; this bundle has no server, so it is off.

What is missing, named rather than implied:

- an HTTPS redirect URI under our control that can receive the authorization code - a file:// path or a GitHub Pages file cannot receive and hold one
- a server-side token exchange that presents the OAuth client secret to Google's token endpoint; a static page cannot keep a secret, so shipping one would publish it
- server-side validation of the id_token signature, issuer, audience and nonce against Google's published keys
- a session the server issues and can revoke - a flag in localStorage is not a session, and revoking it protects nobody

It never writes an identity. The page's single identity writer refuses any method whose configured is not exactly true, and the control is rendered disabled, so a click reports what is missing and nothing else happens. It becomes available when the pieces above exist and this record is flipped to configured true - a configuration change, not a code change, and not something the page can do to itself.

### Sign in with Microsoft — `configured: false`

*OAuth 2.0 authorization code with PKCE against Microsoft Entra ID*

Microsoft sign-in needs an authorization-code exchange on a server, and a registered tenant and redirect URI; this bundle has no server, so it is off.

What is missing, named rather than implied:

- a registered application in a Microsoft Entra ID tenant, which is an organisational decision nobody has made for this bundle
- an HTTPS redirect URI under our control that can receive the authorization code
- a server-side token exchange holding the client secret or certificate; a static page cannot hold either
- server-side validation of the id_token against the tenant's keys, and a session the server issues and can revoke

It never writes an identity. The page's single identity writer refuses any method whose configured is not exactly true, and the control is rendered disabled, so a click reports what is missing and nothing else happens. It becomes available when the pieces above exist and this record is flipped to configured true - a configuration change, not a code change, and not something the page can do to itself.

One HTTPS service that holds the client secret, completes the code exchange, validates the id_token and issues a session it can revoke. Until that exists, flipping any configured flag in this file would make the page lie, and the suite would not catch it - the suite checks that the page obeys this registry, not that this registry is true.

## The two that work, and exactly how far

### Name this device's training record

*a name typed into this page and kept in this browser's localStorage under tc-identity*

It claims that the completions in tc-progress and the sim episodes in tc-training on THIS device belong to the name typed here.

**What it is not.** It does not verify the name. It does not check anything against anyone. Anybody with this device can type any name, or open the browser's storage panel and change it. It protects nothing and it is not a login.
A local identity names whose training record this is, on this device. It is not a login. Anyone holding the device can type any name or edit the stored record directly. The page says this next to the field, not in a footnote.

### Sign in with an Ethereum wallet (EIP-4361)

*EIP-4361 message built in the page, signed by the wallet with personal_sign (EIP-191), and the signer recovered in the page from the signature*

It claims that whoever held the private key for this address, at the moment they were asked, consented to the statement below - and that the page checked that by recovering the address from the signature rather than taking the wallet's word for it.

**What it is not.** It is not a login and it gates nothing. Verification happens in a page anyone can edit, so it is evidence to the person reading it, not a control over anybody else. It does not prove who the person is, only that a key was available to them. A stolen key signs just as well.
A verified EIP-4361 signature shows that the holder of a private key consented to a sentence at a moment. The check runs in a page any reader can edit, so it is evidence to the person reading it and a control over nobody.

The signature is verified **in the page**: keccak-256 over the EIP-191 personal-sign preimage, then secp256k1 public-key recovery from (r, s, v), then the address as the low 20 bytes of keccak-256 of the uncompressed public key, EIP-55 checksummed
Verified means one thing only — the recovered address equals the address the wallet reported, compared as lowercase hex. There is no other branch that reports a signature as verified.
The check lives in the page itself, in the AUTH-CORE region of web/trade_craft_signin.html - no library is fetched and none is vendored; the code is short enough to read in one sitting, and `auth/test.mjs` lifts that
region out and runs it in node against oracles this pack did not write:

- the Keccak-f[1600] permutation the page ships is driven in SHA3-256 mode (the same sponge, pad byte 0x06 instead of 0x01) and compared against node:crypto's own sha3-256 - an implementation this pack did not write
- secp256k1 recovery is checked against signatures produced by node:crypto with namedCurve secp256k1: the page reconstructs the exact public key node generated, over many random keys. node will not sign a digest it did not compute - crypto.sign hashes with SHA-256 whatever algorithm is named - so the oracle is applied one level down, to the curve arithmetic, which is the part no test could fake
- the published addresses of the private keys 1, 2 and 3 are reproduced by the page's own curve, keccak and EIP-55 code; the first of them is reproduced end to end from a personal_sign signature over an EIP-191 preimage
- a tampered signature is required to recover a DIFFERENT address, so a stub that returned the claimed address would fail

Needs a runtime, and says so when it is absent:
window.ethereum. With no wallet in the browser this method offers nothing and says so; it does not fall back to anything. No Ethereum wallet is present in this browser (there is no window.ethereum). There is nothing to sign with, and this page offers nothing in its place.

## The EIP-4361 message, and where its shape came from

8 fields, in this order, over a
16-byte nonce, signed with personal_sign (EIP-191), requested from window.ethereum:

| # | Field | What it is |
|---|---|---|
| 1 | `domain` | the origin asking, on its own first line, so the human reading the wallet prompt sees who asked |
| 2 | `address` | the checksummed account being claimed |
| 3 | `statement` | one sentence the human is agreeing to, verbatim |
| 4 | `uri` | the exact page that asked |
| 5 | `version` | the EIP-4361 version, 1 |
| 6 | `chain-id` | the chain the account is claimed on |
| 7 | `nonce` | fresh per attempt, so a captured signature cannot be replayed into a later attempt |
| 8 | `issued-at` | when this attempt was made, ISO-8601 |

**The field order is AUTHORED FROM RECOLLECTION.**
the EIP-4361 field list and order in this registry are AUTHORED FROM RECOLLECTION - this build has no network and did not open the EIP. A wallet that refuses or mis-renders the message is the signal that the recollection is wrong; no test here can be.

The statement the wallet shows, verbatim: *I am naming this Ethereum account as the owner of the Trade Craft Academy training record kept in this browser. This signature does not log me in, does not reach any server, and protects nothing: this bundle has no backend.*

## What this page is not

- **Not a login.** All 5 methods carry authenticates false and gates_anything false, the wallet one included. This page cannot tell anyone apart and does not protect one learner's record from another.
- **Not a gate.** Every method carries `gates_anything: false`; there is
  nothing here to protect and nothing here protecting it.
- **Not a measurement.** AUTHORED. Every record here is written by this build; none is a measurement. The one claim that is checked rather than asserted is that the page verifies a wallet signature, and siwe.verification names the oracles auth/test.mjs holds it to.
- **Storage.** `tc-identity`,
  this browser only - localStorage, wrapped so a blocked store never breaks the page, exactly like tc-progress — no request is made by this page. There is nowhere for the record to go.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
