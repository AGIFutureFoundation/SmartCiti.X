/**
 * auth/recover.mjs — the sign-in page's own EIP-191 / secp256k1 recovery,
 * importable from node.
 *
 * ONE TRUTH. This module contains no keccak, no curve arithmetic and no
 * address derivation of its own. It lifts the AUTH-CORE region out of the
 * built sign-in page (web/trade_craft_signin.html, written by
 * web/build_auth.py) — the same bytes auth/test.mjs lifts and holds against
 * node's sha3-256, node's secp256k1 and the published addresses of the
 * private keys 1, 2 and 3 — and exports the functions by name. A verifier
 * that imported a second copy would be a second opinion about the crypto;
 * this one runs the page's.
 *
 * It exports RECOVERY only. There is no signing routine here on purpose:
 * signing belongs to a wallet (in the browser) or to a test's throwaway key
 * (in node), never to a verifier.
 *
 * Fail closed: if the page or its markers are missing, importing this module
 * throws with the path it looked for; nothing is stubbed.
 */
import { readFileSync } from 'node:fs';

export const PAGE_PATH = 'web/trade_craft_signin.html';
const url = new URL('../' + PAGE_PATH, import.meta.url);
let page;
try { page = readFileSync(url, 'utf8'); }
catch (e) { throw new Error('auth/recover.mjs: cannot read ' + PAGE_PATH + ' (' + e.message + '); build it with python3 web/build_auth.py'); }

const BEGIN = '/* AUTH-CORE:BEGIN', END = '/* AUTH-CORE:END */';
const a = page.indexOf(BEGIN), b = page.indexOf(END);
if (a < 0 || b <= a) throw new Error('auth/recover.mjs: ' + PAGE_PATH + ' carries no AUTH-CORE region to lift');
export const CORE_SOURCE = page.slice(a, b);

const P = new Function(CORE_SOURCE + '\nreturn { keccak256, te, hex, unhex, be32, toChecksumAddress, '
  + 'personalHash, recoverAddress, verifySiwe, ptMul, ptAdd, SECP_G, SECP_N, addressOfPubkey, recoverPubkey, splitSig };')();

/** keccak-256 over bytes (Uint8Array) -> Uint8Array(32). The page's. */
export const keccak256 = P.keccak256;
export const te = P.te;
export const hex = P.hex;
export const unhex = P.unhex;
export const be32 = P.be32;
/** EIP-55 checksum casing of a 20-byte hex address. */
export const toChecksumAddress = P.toChecksumAddress;
/** keccak-256 of the EIP-191 personal_sign preimage of a string. */
export const personalHash = P.personalHash;
/** (message, 0x-hex 65-byte sig) -> checksummed address of the signer; throws on a malformed signature. */
export const recoverAddress = P.recoverAddress;
export const verifySiwe = P.verifySiwe;
/* curve arithmetic, exported so a TEST can derive a throwaway key's address
   and sign over the same arithmetic auth/test.mjs certified — not for verifiers */
export const ptMul = P.ptMul;
export const ptAdd = P.ptAdd;
export const SECP_G = P.SECP_G;
export const SECP_N = P.SECP_N;
export const addressOfPubkey = P.addressOfPubkey;
export const recoverPubkey = P.recoverPubkey;
export const splitSig = P.splitSig;
