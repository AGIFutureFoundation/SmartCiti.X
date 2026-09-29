/* web/test_robotics.mjs - the Robotics lab page (web/trade_craft_robotics.html), checked against the registries it is
 * built from. Browser-free. Recompute, never re-read: counts are recounted from robotics.json, the embedded data is
 * compared to the registry, and every chrome key is looked up in all 8 locales. The browser teleop + record probe
 * lives in the smoke / probe run (see ROBOLAB memory), not here. */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const page = readFileSync(join(HERE, 'trade_craft_robotics.html'), 'utf8');
const reg = JSON.parse(readFileSync(join(ROOT, 'robotics/registry/robotics.json'), 'utf8'));
const tr = JSON.parse(readFileSync(join(ROOT, 'training/registry/training.json'), 'utf8'));
const blob = (id) => JSON.parse(page.split(`<script type="application/json" id="${id}">`)[1].split('</script>')[0]);
const data = blob('robo-data'), I = blob('robo-i18n');
const rk = Object.values(reg.envs).filter((e) => e.runner === 'robokit');

ok('exactly one <h1>, and it is the translated page title', (page.match(/<h1[\s>]/g) || []).length === 1
  && /<h1 class="tc-page-title" data-i18n="robo.title">/.test(page));
ok('the site nav is present and marks this page current', page.includes('aria-current="page"')
  && /href="trade_craft_robotics.html" aria-current="page"/.test(page));
ok('the saved-style head script runs before paint', page.indexOf('id="style-head-js"') > 0
  && page.indexOf('id="style-head-js"') < page.indexOf('</head>'));
ok('the embedded data is the registry: same stamp, same robokit env ids, same embodiments',
  data.robo.stamp === reg.source_stamp && Object.keys(data.robo.envs).join() === rk.map((e) => e.id).join()
  && Object.keys(data.robo.embodiments).join() === Object.keys(reg.embodiments).join());
ok('the embedded training data is training/ (same key, toggle, cap, world teleop rate and cap)',
  JSON.stringify(data.train.storage) === JSON.stringify(tr.storage)
  && JSON.stringify(data.train.world_teleop) === JSON.stringify(tr.world_teleop));
ok('the figures are recounted from the registry, and trained models prints 0',
  ['envs', 'robokit_envs', 'sim_seat_envs', 'embodiments', 'trained_models'].every((k) =>
    page.includes(`data-robo-count="${k}">${reg.counts[k]}<`)) && reg.counts.trained_models === 0
  && Object.values(reg.envs).length === reg.counts.envs);
ok('every env in the registry has a catalogue entry, every embodiment a card',
  Object.keys(reg.envs).every((id) => page.includes(`data-env="${id}"`))
  && Object.keys(reg.embodiments).every((id) => page.includes(`data-emb="${id}"`)));
ok('every registry honesty line is printed verbatim', Object.keys(reg.honesty).every((k) => page.includes(`data-honesty="${k}"`)));
ok('the page says what is and is not trained (three of each)', (page.split('id="robo-is"')[1] || '').split('</ul>')[0].split('<li>').length === 4
  && (page.split('id="robo-not"')[1] || '').split('</ul>')[0].split('<li>').length === 4);
ok('links to the parish world, the Bay world, the training seats and the Contribute page, each a real file',
  ['trade_craft_parishes.html', 'trade_craft_bay.html', 'trade_craft_3d.html', 'trade_craft_contribute.html'].every((f) =>
    page.includes(`href="${f}"`) && existsSync(join(HERE, f))));
const keys = [...new Set([...page.matchAll(/data-i18n="([^"]+)"/g)].map((m) => m[1]))];
ok(`every chrome key (${keys.length}) exists, non-empty, in all 8 locales; Arabic is right-to-left`,
  Object.keys(I).length === 8 && keys.every((k) => Object.values(I).every((L) => typeof L.strings[k] === 'string' && L.strings[k].trim()))
  && I.ar.dir === 'rtl');
ok('the non-English chrome is translated, not copied (under 10% identical to English)', Object.entries(I).filter(([l]) => l !== 'en').every(([, L]) =>
  Object.keys(L.strings).filter((k) => L.strings[k] === I.en.strings[k]).length < Object.keys(L.strings).length * 0.1));
ok('the touch pad keys (every teleop touch label) are in the catalogue',
  Object.values(reg.teleop).every((t) => t.touch.every((b) => typeof I.en.strings[b.label_key] === 'string')));
ok('the sandbox panel is mounted with its controls (env, seed, reset, record, reference, export, canvas, pad)',
  ['robo-env', 'robo-seed', 'robo-reset', 'robo-rec', 'robo-ref', 'robo-export', 'robo-canvas', 'robo-pad', 'robo-cmp'].every((id) => page.includes(`id="${id}"`)));
ok('touch controls are at least 44 px', /\.robo-row select,\.robo-row button,\.robo-pad button\{min-block-size:44px;min-inline-size:44px/.test(page));
ok('classroom / K-12 mode disables recording and export', page.includes("q.has('classroom') || q.has('class')")
  && page.includes("$('#robo-rec').disabled = true; $('#robo-export').disabled = true;"));
ok('the reference-results table is computed in the page from the core, nothing typed in',
  page.includes('RoboCore.rollout(env, emb, s, data.train') && !/data-refrun-fixed/.test(page));
ok('no Math.random anywhere in the page scripts', !page.includes('Math.random'));
ok('no upload: the page makes no network request (no fetch, no XHR, no sendBeacon)', !/fetch\(|XMLHttpRequest|sendBeacon/.test(
  page.split('<script id="robo-kit">')[1].split('</script>')[0] + page.split('<script id="robo-page">')[1].split('</script>')[0]));

console.log(`test_robotics: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
