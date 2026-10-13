// web/test_restokit.mjs - checks the embeddable restoration scenario runner (web/restokit.py).
// Prints "  ok " per check, FAIL at column 0, exits non-zero on failure.
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

let n = 0, bad = 0;
const ok = (m, c, d) => { if (c) { n++; console.log('  ok ', m); } else { bad++; console.log('FAIL', m, d === undefined ? '' : JSON.stringify(d).slice(0, 400)); } };
const ROOT = new URL('../', import.meta.url);
const kit = readFileSync(new URL('web/restokit.py', ROOT), 'utf8');
const reg = JSON.parse(readFileSync(new URL('restoration/registry/scenarios.json', ROOT)));
const LOC = ['ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'zh'];
const S = Object.fromEntries(LOC.map((l) => [l, JSON.parse(readFileSync(new URL(`i18n/locales/${l}.json`, ROOT))).strings]));

const css = (kit.match(/RESTO_CSS = '''([\s\S]*?)'''/) || [, ''])[1];
ok('[theme] RESTO_CSS is scoped .rk-* and colours only with var(--...) tokens', css.length > 0
  && !/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/.test(css) && css.split('}').filter((r) => r.trim()).every((r) => r.trim().startsWith('.rk-')));
const js = (kit.match(/RESTO_JS = r'''([\s\S]*?)'''/) || [, ''])[1];
let api = null;
try { api = new Function(js + '\nreturn {rkScore, rkMount};')(); } catch (e) { api = null; }
ok('[api] RESTO_JS parses and defines rkScore and rkMount', api && typeof api.rkScore === 'function' && typeof api.rkMount === 'function');

// the kit never offers the scorer a shortcut: gates and forbidden are hard fails
const sc = reg.scenarios[0];
const perfect = sc.fixtures.find((f) => f.name === 'perfect').run;
const r1 = api.rkScore(sc, perfect);
const noPpe = api.rkScore(sc, { ...perfect, ppe: [] });
const late = api.rkScore(sc, { ...perfect, sequence: perfect.sequence.filter((t) => !t.startsWith('gate:')).concat(perfect.sequence.filter((t) => t.startsWith('gate:'))) });
ok('[score] a gate acknowledged after the step it guards fails the run; missing PPE fails it; the perfect run passes',
  r1.pass === true && late.gates === false && late.pass === false && noPpe.pass === false && noPpe.ppe === 0);
const sameTwice = reg.scenarios.every((s) => s.fixtures.every((f) => JSON.stringify(api.rkScore(s, f.run)) === JSON.stringify(api.rkScore(s, f.run))));
ok('[score] scoring is deterministic (same run, same result, every fixture)', sameTwice);

// labels: every L('key', ...) the kit uses exists as resto.<key> in all 8 locales, translated
const keys = [...new Set([...js.matchAll(/L\('([a-z]+)'/g)].map((m) => m[1]))];
const missing = LOC.flatMap((l) => keys.filter((k) => !(('resto.' + k) in S[l])).map((k) => `${l}:${k}`));
ok(`[i18n] every label the kit uses (${keys.length}) exists as resto.* in all 8 locales`, keys.length >= 10 && missing.length === 0, missing);
const copies = LOC.filter((l) => l !== 'en').flatMap((l) => Object.keys(S.en).filter((k) => k.startsWith('resto.') && S[l][k] === S.en[k]).map((k) => `${l}:${k}`));
ok('[i18n] no resto.* value is an English copy in another locale', copies.length === 0, copies);

// python API: loads, filters by site, fails closed
const py = execFileSync('python3', ['-c', `
import sys, json; sys.path.insert(0, 'web')
import restokit as k
print(json.dumps({'hp': [s['id'] for s in k.scenarios_for_site('hunters-point-shipyard')],
  'gen': len(k.generic_scenarios()), 'line': k.honesty_line(),
  'js': len(json.loads(k.scenarios_json(k.scenarios_for_site('herons-head'))))}))`], { cwd: new URL('.', ROOT).pathname }).toString();
const P = JSON.parse(py);
ok('[api] scenarios_for_site / generic_scenarios / scenarios_json / honesty_line work from the registry',
  JSON.stringify(P.hp) === JSON.stringify(reg.scenarios.filter((s) => s.site === 'hunters-point-shipyard').map((s) => s.id))
  && P.gen === reg.generic.length && P.js === reg.scenarios.filter((s) => s.site === 'herons-head').length
  && P.line.includes("not the project's actual work plan") && P.line.includes('unverified general practice'));
const src = kit.replace(/"""[\s\S]*?"""/g, '').replace(/#.*$/gm, '');
ok('[generator] the kit never reads with .get(k, default) or ?? and fails closed with KeyError', !/\.get\([^)]*,/.test(src) && !/\?\?/.test(src) && src.includes('raise KeyError'));
ok('[play] the kit stores nothing (no storage, no network)', !/localStorage|sessionStorage|indexedDB|fetch\(|XMLHttpRequest/.test(js));

if (bad) { console.log(`web/test_restokit: ${bad} FAILED, ${n} passed`); process.exit(1); }
console.log(`web/test_restokit: ${n} checks passed`);
