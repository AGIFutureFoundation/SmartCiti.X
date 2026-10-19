/* web/test_classroom.mjs - the classroom page and web/classkit.py, checked from the BUILT page against
 * classroom/registry/classroom.json. Network-free. CLASS-CORE and the lifted AUTH-CORE are run in node.
 * Prints `  ok ` per check, FAIL at column 0, exits non-zero on failure. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { randomBytes } from 'node:crypto';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); } else { fail++; console.log('FAIL ' + m); } };
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
console.log('web/test_classroom.mjs');
const P = read('web/trade_craft_classroom.html');
const REG = JSON.parse(read('classroom/registry/classroom.json'));
const KIT = read('web/classkit.py');
const script = (id) => { const m = P.match(new RegExp('<script[^>]*id="' + id + '"[^>]*>([\\s\\S]*?)</script>')); return m ? m[1] : ''; };
const D = JSON.parse(script('class-data'));
const I = JSON.parse(script('class-i18n'));

/* ---- page must-haves ---- */
ok((P.match(/<h1\b/g) || []).length === 1, 'exactly one <h1>');
ok(P.includes('data-sitenav') && /aria-current="page"/.test(P) && /<link rel="canonical" href="trade_craft_classroom\.html">/.test(P), 'site nav marks this page; canonical link');
ok(/if PAGE not in sitenav\.PAGES:\s*\n\s*raise /.test(read('web/build_classroom.py')), 'builder fails closed on an undeclared page');
const own = P.slice(P.lastIndexOf('<style>'), P.indexOf('</style>', P.lastIndexOf('<style>')));
ok(!/#[0-9a-fA-F]{3,8}\b/.test(own) && (own.match(/var\(--tc-/g) || []).length >= 10 && /<html lang="en">/.test(P),
  'light/dark from --tc-* tokens (no hex, no forced theme)');

/* ---- data = registry ---- */
ok(D.stamp === REG.source_stamp && D.modules.length === REG.modules.length + REG.cognitionx.modules.length && D.places.length === REG.places.length
  && D.moments.length === REG.moments.length + REG.cognitionx.moments.length, `embedded data = registry (${D.modules.length} modules, ${D.moments.length} moments, ${D.places.length} places)`);
const heads = Object.fromEntries([...P.matchAll(/data-cl-count="([a-z]+)">(\d+)</g)].map((m) => [m[1], Number(m[2])]));
ok(heads.modules === REG.modules.length + REG.cognitionx.modules.length && heads.moments === REG.moments.length + REG.cognitionx.moments.length && heads.places === REG.places.length,
  `header figures recounted from the registry (${JSON.stringify(heads)})`);
const pid = new Set(D.places.map((p) => p.id));
ok(D.modules.every((m) => m.places.every((x) => pid.has(x))) && D.moments.every((m) => m.places.every((x) => pid.has(x))),
  'every embedded module/moment place resolves in the embedded places');

/* ---- i18n: 8 locales, RTL, translations, honesty in every locale ---- */
const used = [...new Set([...P.matchAll(/data-i18n="([^"]+)"/g)].map((m) => m[1]))];
const kitKeys = [...KIT.matchAll(/'(class\.[a-z.]+[a-z])'/g)].map((m) => m[1]);
const all = [...new Set([...used, ...kitKeys])];
ok(Object.keys(I).sort().join() === 'ar,de,en,es,fr,hi,pt,zh' && I.ar.dir === 'rtl', '8 locales embedded, Arabic right-to-left');
ok(all.length >= 50 && Object.values(I).every((c) => all.every((k) => typeof c.strings[k] === 'string' && c.strings[k].trim())),
  `every page + HUD key (${all.length}) present in all 8 locales`);
const LOAN = new Set(['class.hud.xp', 'class.card.source', 'class.f.modules', 'class.l.badges']);
ok(Object.entries(I).filter(([l]) => l !== 'en').every(([, c]) => all.every((k) => LOAN.has(k) || c.strings[k] !== I.en.strings[k])),
  'every non-English string is a translation (4 named loanwords allowed)');
const HON = ['class.h.server', 'class.h.plan', 'class.h.play', 'class.h.data', 'class.h.lessons'];
ok(HON.every((k) => used.includes(k)) && /No server/.test(I.en.strings['class.h.server']) && /not access control/.test(I.en.strings['class.h.plan'])
  && /play/.test(I.en.strings['class.h.play']) && /No student data leaves/.test(I.en.strings['class.h.data'])
  && /unverified general practice/.test(I.en.strings['class.h.lessons']) && /PROPOSED/.test(I.en.strings['class.h.lessons'])
  && Object.values(I).every((c) => HON.every((k) => c.strings[k].length > 20)),
  'honesty: no server/accounts, plans not access control, scores are play, no data leaves, lessons unverified + districts PROPOSED - shown, in 8 locales');

/* ---- no network, never a completion record, storage guarded ---- */
const JS = script('class-kit') + script('class-page') + script('class-auth');
ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|importScripts|\bimport\s*\(|https?:\/\//.test(JS), 'no network call in the kit, the page or the lifted auth core');
const sets = [...(script('class-kit') + script('class-page')).matchAll(/setItem\(([^,]+),/g)].map((m) => m[1].trim());
ok(!/completion/i.test(script('class-kit').replace(/never enter a completion record|not a completion record/g, '')) && sets.every((s) => s === 'key')
  && /PROG_KEY = 'tc-class-progress', PLAN_KEY = 'tc-class-plan'/.test(JS), 'never writes a completion record: the only stored keys are tc-class-progress / tc-class-plan');
const ls = [...script('class-kit').matchAll(/localStorage/g)].length;
ok(ls === 2 && /function load\(key\) \{ try \{ return window\.localStorage\.getItem\(key\); \} catch \(e\) \{ saved = false; return null; \} \}/.test(JS)
  && /function save\(key, v\) \{ try \{ window\.localStorage\.setItem\(key, v\); \} catch \(e\) \{ saved = false; \} \}/.test(JS),
  'every localStorage touch is inside try/catch and a throw flips the page to not-saved');

/* ---- CLASS-CORE and AUTH-CORE, lifted and run ---- */
const core = JS.slice(JS.indexOf('/* CLASS-CORE:BEGIN'), JS.indexOf('/* CLASS-CORE:END */'));
const K = new Function(core + '\nreturn TCClassCore;')();
const A = new Function(script('class-auth') + '\nreturn TCClassAuth;')();
const plan = K.defaultPlan(D);
plan.title = 'Year 7 - week 1'; plan.modules = D.modules.slice(0, 3).map((m) => m.id); plan.worlds = ['parishes', 'wilds'];
const enc = K.encodePlan(plan);
ok(/^[A-Za-z0-9_-]+$/.test(enc) && K.canon(K.decodePlan(enc, D, A).plan) === K.canon(plan) && K.decodePlan(enc, D, A).sign === 'unsigned',
  'plan round-trip: encode -> base64url -> decode gives the same plan (unsigned)');
const refuses = (p, re) => { try { K.decodePlan(K.encodePlan(p), D, A); return false; } catch (e) { return re.test(e.message); } };
ok(refuses({ ...plan, modules: ['mod-nope'] }, /unknown module/) && refuses({ ...plan, worlds: ['moon'] }, /unknown world/)
  && refuses({ ...plan, admin: true }, /unknown field/) && refuses({ ...plan, session_minutes: 7 }, /session length/),
  'plans naming unknown modules/worlds/fields or lengths are refused by name');
const sc = K.scope(D, plan);
ok(Object.values(sc.places).every((p) => plan.worlds.includes(p.world)) && sc.moments.every((m) => plan.modules.includes(m.module))
  && Object.keys(sc.places).length > 0, 'a plan restricts shown places to its worlds and modules');
{
  const SECP_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141n;
  const beI = (u) => BigInt('0x' + Buffer.from(u).toString('hex'));
  const h32 = (n) => n.toString(16).padStart(64, '0');
  const modp = (a, m) => ((a % m) + m) % m;
  const invN = (a) => { let [r0, r1, s0, s1] = [modp(a, SECP_N), SECP_N, 1n, 0n]; while (r1) { const q = r0 / r1; [r0, r1] = [r1, r0 - q * r1]; [s0, s1] = [s1, s0 - q * s1]; } return modp(s0, SECP_N); };
  const P2 = new Function(script('class-auth').replace('return { recoverAddress: recoverAddress, toChecksumAddress: toChecksumAddress };',
    'return { recoverAddress, toChecksumAddress, keccak256, ptMul, SECP_G };') + '\nreturn TCClassAuth;')();
  const signPersonal = (d, message) => {
    const body = Buffer.from(message, 'utf8');
    const pre = Buffer.concat([Buffer.from('\x19Ethereum Signed Message:\n' + body.length, 'utf8'), body]);
    const z = beI(P2.keccak256(new Uint8Array(pre))) % SECP_N;
    for (;;) {
      const k = (beI(randomBytes(32)) % (SECP_N - 1n)) + 1n, R = P2.ptMul(k, P2.SECP_G), r = R[0] % SECP_N;
      if (r === 0n) continue;
      let s = (invN(k) * (z + r * d)) % SECP_N; if (s === 0n) continue;
      let rec = Number(R[1] & 1n); if (s > SECP_N / 2n) { s = SECP_N - s; rec ^= 1; }
      return '0x' + h32(r) + h32(s) + (27 + rec).toString(16).padStart(2, '0');
    }
  };
  const sp = { ...plan, signer: '0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf' };
  sp.sig = signPersonal(1n, K.planMessage(sp));
  ok(K.decodePlan(K.encodePlan(sp), D, A).sign === 'signed', 'a plan signed (EIP-191, test key 1) verifies with the sign-in page\'s own recovery');
  ok(refuses({ ...sp, title: 'Year 7 - week 2' }, /does not recover to its signer; plan refused/)
    && refuses({ ...sp, modules: D.modules.slice(0, 4).map((m) => m.id) }, /plan refused/)
    && refuses({ ...sp, signer: '0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF' }, /plan refused/),
    'a signed plan tampered after signing (title, modules or signer) is refused');
  ok((() => { try { K.decodePlan(K.encodePlan(sp), D, null); return false; } catch (e) { return /no signature check/.test(e.message); } })(),
    'a signed plan on a page without the auth core is refused, not trusted');
}
/* scoreboard math: XP recomputed from moments/places with the rules, never read from the file */
{
  const xp = { module_complete: 50, moment_correct: 20, moment_tried: 5, place_reached: 5 };
  const m0 = D.modules.find((m) => m.moments.length === 1);
  const mo = D.moments.find((x) => x.id === m0.moments[0]);
  const f1 = { v: K.PROG_V, learner: 'Ana', xp: 999999, moments: { [mo.id]: { tried: 2, correct: true } }, places: { [mo.places[0]]: '2026-09-28', [D.places[0].id]: '2026-09-28' }, days: ['2026-09-27', '2026-09-28'] };
  const f2 = { v: K.PROG_V, learner: 'Ben', moments: { [D.moments[1].id]: { tried: 1, correct: false } }, places: {}, days: ['2026-09-20'] };
  const f3 = { v: K.PROG_V, learner: 'Cy', moments: { 'mo-nope': { tried: 1, correct: true } }, places: {}, days: [] };
  const want1 = (mo.places[0] === D.places[0].id ? 1 : 2) * 5 + 2 * 5 + 20 + 50;
  const now = Date.parse('2026-09-28T12:00:00Z');
  const r = K.scoreboard([{ name: 'a.json', json: f1 }, { name: 'b.json', json: f2 }, { name: 'c.json', json: f3 }, { name: 'd.json', json: null }], D, xp, now);
  ok(r.rows.length === 2 && r.rows[0].learner === 'Ana' && r.rows[0].xp === want1 && r.rows[0].rank === 1 && r.rows[0].modules === 1
    && r.rows[0].streak === 2 && r.rows[1].xp === 5 && r.rows[1].rank === 2 && r.rows[1].streak === 0,
    `scoreboard math: Ana ${want1} XP (places + 2 tries + correct + module), rank 1, streak 2; Ben 5 XP, streak 0; file xp ignored`);
  ok(r.refused.length === 2 && /unknown moment mo-nope/.test(r.refused[0].why) && /not a tc-class-progress/.test(r.refused[1].why),
    'malformed or foreign progress files are refused by name, not scored');
  const tie = K.scoreboard([{ name: 'x', json: { ...f2, learner: 'Zed' } }, { name: 'y', json: f2 }], D, xp, now);
  ok(tie.rows.map((x) => x.learner + x.rank).join() === 'Ben2,Zed2'.replace('Ben2', 'Ben1').replace('Zed2', 'Zed1'), 'equal XP share a rank, ordered by name');
  ok(K.streak(['2026-09-25', '2026-09-26', '2026-09-28'], now) === 1 && K.streak(['2026-09-26', '2026-09-27'], now) === 2
    && K.streak(['2026-09-20'], now) === 0 && K.streak([], now) === 0, 'streak: consecutive days ending today or yesterday');
  const st = K.newProgress();
  ok(K.reach(st, D.places[0].id, D, now) === true && K.reach(st, D.places[0].id, D, now) === false
    && (() => { try { K.reach(st, 'parish:0/none', D, now); return false; } catch (e) { return /unknown place/.test(e.message); } })(),
    'a place awards once; an unknown place id throws by name');
  const ex = K.exportProgress(st, now, 'T');
  ok(ex.v === 'tc-class-progress/1' && /not a completion record/.test(ex.note) && !('xp' in ex), 'exported progress is a play file, says so, and carries no XP claim');
}

ok(/window\.ReactorKit\.setContext\(\{ place: String\(sc\.places\[placeId\]\.title\)\.slice\(0, 80\),/.test(script('class-kit'))
  && !/ReactorKit\.(connect|start)\b/.test(script('class-kit')), 'Reactor: the kit only passes page labels as context (80 chars) and never connects');

/* ---- Cognition.X transfer moments (COGX_CONTRACT): verbatim, attributed, self-reported play ---- */
{
  const X = REG.cognitionx, tx = D.moments.filter((m) => m.kind === 'transfer');
  ok(tx.length === X.moments.length && tx.every((m) => { const r = X.moments.find((x) => x.id === m.id).block; return Object.keys(r).length === Object.keys(m.block).length && Object.keys(r).every((k) => m.block[k] === r[k]); }),
    `embedded Cognition.X transfer moments = registry, block columns verbatim (${tx.length})`);
  const A = D.cx_attribution;
  ok(A.license === 'CC-BY-4.0' && P.includes('href="' + A.license_url + '" rel="license noopener">CC BY 4.0</a>') && P.includes('>' + A.text + '</a>')
    && script('class-kit').includes("'CC BY 4.0'") && script('class-kit').includes('A.text'), 'CC BY 4.0 attribution linked on the page and on every transfer card');
  const st = K.newProgress(), mo = tx[0], now = Date.parse('2026-09-28T12:00:00Z');
  ok(K.tried(st, mo, now) === true && st.moments[mo.id].correct === true
    && (() => { try { K.tried(st, D.moments.find((m) => m.kind === 'choice'), now); return false; } catch (e) { return /not a transfer moment/.test(e.message); } })()
    && (() => { try { K.answer(st, mo, 'x', now); return false; } catch (e) { return /not a choice card/.test(e.message); } })(),
    'a transfer moment is self-reported play (no invented quiz); choice and transfer actions cannot be swapped');
}

console.log(`${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
