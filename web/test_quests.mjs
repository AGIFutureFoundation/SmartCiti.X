#!/usr/bin/env node
/* web/test_quests.mjs - web/trade_craft_quests.html structure. No browser.
   Prints "  ok " per check, FAIL at column 0, exits non-zero on failure. */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let fails = 0;
function ok(name, cond, detail) {
  if (cond) { console.log('  ok ' + name); return; }
  fails++; console.log('FAIL ' + name); if (detail) console.log('     ' + detail);
}
const html = readFileSync(join(HERE, 'trade_craft_quests.html'), 'utf8');
const reg = JSON.parse(readFileSync(join(ROOT, 'quests/registry/quests.json'), 'utf8'));
let fresh = true; try { execFileSync('python3', [join(HERE, 'build_quests.py'), '--check'], { stdio: 'pipe' }); } catch (e) { fresh = false; }
ok('the committed page is what web/build_quests.py builds', fresh);
ok('one <h1>', (html.match(/<h1[\s>]/g) || []).length === 1);
// wave 3 (lead ruling): the body may carry MEDIA's theme('doc') class, and nothing else; the nav is still first
ok('the site nav is the first thing in the body', /<body(?: class="tc-theme")?>\s*<nav class="sitenav"/.test(html));
ok('a quest log hook (data-tc-questlog) and a badge shelf', html.includes('data-tc-questlog') && html.includes('id="shelf"'));
const games = [...html.matchAll(/<article class="game" id="([a-z0-9-]+)" data-game="[a-z]+"/g)].map((m) => m[1]);
ok(`at least three arcade games (${games.length}), each a registry game`, games.length >= 3 && games.every((g) => reg.quests.some((q) => q.id === g && q.kind === 'game')));
const gates = games.filter((g) => new RegExp(`id="${g}"[\\s\\S]*?<div class="gate" data-gate="${g}">[\\s\\S]*?<div class="play" hidden>`).test(html));
ok('every game ships locked: its gate is shown and its play area is hidden until check() passes',
  gates.length === games.length && (html.match(/<div class="play" hidden>/g) || []).length === games.length
  && (html.match(/<div class="play"/g) || []).length === games.length && !/<div class="gate"[^>]*hidden/.test(html));
const links = games.every((g) => reg.quests.find((q) => q.id === g).requires.lessons.every((l) => html.includes(`href="trade_craft_lessons.html#lesson-${l}"`)));
ok('every locked game links to exactly the lessons it needs', links);
ok('the demo toggle is off by default and says it is for demos', /<input type="checkbox" id="demo">/.test(html) && !/id="demo"[^>]*checked/.test(html) && /For demos only/.test(html) && /demo\.checked = false/.test(html));
ok('a demo win is not recorded (complete() is still gated)', /Demo rounds are not recorded/.test(html) && !/localStorage[^;]*demo/i.test(html));
ok('the honesty sentence is on the page once', html.split(reg.honesty).length - 1 >= 1 && /This is play/.test(html));
ok('games read the seats\' own data (signals, chart, rubric) from the sims registry', /"signals": \[/.test(html) && /"chart": \[\[/.test(html) && /"trench_fail":/.test(html) && /"crib": \[\{"name"/.test(html));
ok('the quest engine is carried after the page\'s own script', html.indexOf('id="arcade-js"') > 0 && html.indexOf('data-tc-quests') > html.indexOf('id="arcade-js"'));
console.log(fails ? `web/test_quests: ${fails} FAILED` : 'web/test_quests: all passed');
process.exit(fails ? 1 : 0);
