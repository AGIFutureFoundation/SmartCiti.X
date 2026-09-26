/**
 * The console, held to its sources and its registry.
 *
 * check_console.py says whether the page is behind the protocol modules it
 * inlines; it prints no counted checks. This suite counts what the page
 * promises about crews and heartbeats: every crew the agents registry holds
 * has a console on the page, every role is on the heartbeat board, the
 * monitor the board runs is the tested one and not a copy, and the page
 * types no check count of its own.
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };
const url = (p) => new URL(p, import.meta.url);
const html = readFileSync(url('./trade_craft_console.html'), 'utf8');
const app = readFileSync(url('./build_app.py'), 'utf8');
const slice = JSON.parse(readFileSync(url('./app_slice.json'), 'utf8'));
const crewReg = JSON.parse(readFileSync(url('../agents/registry/crews.json'), 'utf8'));
const sources = readFileSync(url('./console_sources.py'), 'utf8');
const embedded = JSON.parse(/^const SLICE = (.*);$/m.exec(html)[1]);

ok('the page embeds the slice it was built from, and the slice carries the crews',
  JSON.stringify(embedded) === JSON.stringify(slice) && slice.crews && slice.crews.crews);
ok('every crew in the agents registry has a console on the page, and no other',
  JSON.stringify(Object.keys(slice.crews.crews).sort())
  === JSON.stringify(Object.keys(crewReg.crews).sort()));
ok('every role of every crew is on the page with the name, job, standing and stop-work right the registry gives it',
  Object.entries(crewReg.crews).every(([cid, c]) =>
    Object.entries(c.roles).every(([rid, r]) => {
      const s = slice.crews.crews[cid].roles[rid];
      return s && s.name === r.name && s.job === r.job && s.standing === r.standing && s.stops === r.stops;
    })));
ok('the run of hand-offs is the registry’s, step for step',
  Object.entries(crewReg.crews).every(([cid, c]) =>
    JSON.stringify(slice.crews.crews[cid].run) === JSON.stringify(c.run)));
ok('the counts the crew panel shows are the registry’s own counts, not retyped',
  JSON.stringify(slice.crews.counts) === JSON.stringify(crewReg.counts)
  && /C\.counts\.crews.*C\.counts\.roles.*C\.counts\.handoffs/.test(app));
ok('the standing vocabulary travels with the crews, so a role’s standing is explained in the registry’s words',
  JSON.stringify(slice.crews.standing) === JSON.stringify(crewReg.standing)
  && /title="\$\{C\.standing\[r\.standing\]\}"/.test(app));
ok('the page says what a crew is in the registry’s own SCRIPTED sentence',
  slice.crews.honesty === crewReg.honesty.status && /^SCRIPTED: /.test(slice.crews.honesty)
  && /\$\('#crewhonesty'\)\.textContent = C\.honesty;/.test(app));

/* ------------------------------------------------------------ heartbeats --- */
ok('the heartbeat monitor on the page is the tested module, inlined from ops/heartbeat.mjs',
  /'ops\/heartbeat\.mjs'/.test(sources) && /class HeartbeatMonitor \{/.test(html)
  && /export class HeartbeatMonitor/.test(readFileSync(url('../ops/heartbeat.mjs'), 'utf8')));
ok('the page is built from the current sources, heartbeat monitor included (stamp check)',
  (() => {
    const block = sources.slice(sources.indexOf('SOURCES = ['), sources.indexOf(']', sources.indexOf('SOURCES = [')));
    const list = [...block.matchAll(/'([^']+\.m?js)'/g)].map((m) => m[1]);
    const h = createHash('sha256');
    for (const f of list) h.update(readFileSync(url('../' + f)));
    return list.includes('ops/heartbeat.mjs')
      && /control-plane-source-stamp: ([0-9a-f]{16})/.exec(html)[1] === h.digest('hex').slice(0, 16);
  })());
ok('every role of every crew registers a heartbeat at muster, on the session’s own audit log',
  /S\.hb = new HeartbeatMonitor\(\{ audit: S\.audit, now: 0, grace: 0 \}\);/.test(app)
  && /for \(const rid of Object\.keys\(c\.roles\)\)\s*\n\s*S\.hb\.register\(hbId\(cid, rid\), \{ kind: 'crew', intervalMs: HB_INTERVAL_MS \}\);/.test(app));
ok('a tick beats every role still reporting and then sweeps: the sweep, not the silence, makes the record',
  /if \(!S\.silenced\.has\(hbId\(cid, rid\)\)\) S\.hb\.beat\(hbId\(cid, rid\), S\.hbClock\);/.test(app)
  && /return S\.hb\.sweep\(HB_INTERVAL_MS\);/.test(app));
ok('a crew with a stale role reads as one that cannot run its task',
  /cannot run: \$\{stale\} role/.test(app));
ok('the liveness log reads the same audit log the dial writes, filtered by actor, not a second log',
  /S\.audit\.entries\(\{ actor: 'heartbeat' \}\)/.test(app) && !/new AuditLog\(\)/.test(app.split('bootCrews')[1] ?? ''));
ok('the Crews view is wired like the other four: a tab, a section, and the toggle list',
  /data-view="crews"/.test(html) && /id="view-crews"/.test(html)
  && /const VIEWS = \['learn', 'graph', 'cert', 'ops', 'crews'\];/.test(app));
ok('a link can land on a view: the page opens the view its hash names, so the front door reaches the crew consoles directly',
  /const wantView = location\.hash\.replace\('#', ''\);\s*\n\s*if \(VIEWS\.includes\(wantView\)\) showView\(wantView\);/.test(app));
/* Spec §25.4: the console runs in a browser, where node:fs does not exist.
   No static node: import may survive bundling and nothing may require();
   the pack library's one dynamic file read is behind its own isNode guard,
   which is asserted rather than assumed. */
ok('the page keeps no static node: import and no require(); the one dynamic file read is behind the pack library\u2019s isNode guard',
  (() => { const js = html.split('<script type="module">')[1] ?? html;
    return !/^import\s.*['"]node:/m.test(js) && !/require\(/.test(js)
      && /const isNode = typeof process !== 'undefined' && process\.versions\?\.node;/.test(js)
      && (js.match(/await import\('node:/g) ?? []).every(() => /if \(isNode && /.test(js)); })());
ok('the console types no check count of its own; verify_all.sh counts',
  !/\d+-check suite/.test(html) && /verify_all\.sh/.test(html));

console.log(`console/test: ${n} checks passed — ${Object.keys(slice.crews.crews).length} crew consoles, `
  + `${slice.crews.counts.roles} roles on the heartbeat board`);
