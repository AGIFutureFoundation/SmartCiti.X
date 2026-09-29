// restoration/test_scenarios.mjs - checks restoration/registry/scenarios.json
// (built by restoration/scenarios.py). Prints "  ok " per check, FAIL at column 0.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

let n = 0, bad = 0;
const ok = (m, c, detail) => {
  if (c) { n++; console.log('  ok ', m); } else { bad++; console.log('FAIL', m, detail === undefined ? '' : JSON.stringify(detail).slice(0, 400)); }
};
const R = (p) => readFileSync(new URL(p, import.meta.url));
const J = (p) => JSON.parse(R(p));
const reg = J('./registry/scenarios.json');
const resto = J('./registry/restoration.json');
const slugs = new Set(J('../unions/registry/unions.json').unions.map((u) => u.slug));
const sites = Object.fromEntries(resto.sites.map((s) => [s.id, s]));
const ALL = reg.scenarios.concat(reg.generic);
const sha16 = (b) => createHash('sha256').update(b).digest('hex').slice(0, 16);

// ---- stamp
const srcs = ['restoration/registry/restoration.json', 'unions/registry/unions.json', 'bayarea/registry/bayarea.json'];
const buf = srcs.map((p) => R('../' + p));
ok('[stamp] source_stamp recomputes over the builder and its sources (no hand edit, no stale build)',
  reg.source_stamp === sha16(Buffer.concat([R('./scenarios.py'), ...buf])));

let fresh = true;
try { execFileSync('python3', [new URL('./scenarios.py', import.meta.url).pathname, '--check'], { stdio: 'pipe' }); } catch (e) { fresh = false; }
ok('[fresh] the registry is byte-identical to a fresh build (no hand edit)', fresh);

// ---- funding context / FACTS rule
const FC = reg.funding_context;
ok('[facts] funding_context carries the headline, url, "URL slug only" source, empty funded_projects and PENDING',
  FC.headline === 'EPA awards $82 million for San Francisco Bay restoration and pollution control'
  && FC.url.startsWith('https://smartwatermagazine.com/') && FC.source === 'URL slug only - article not fetched (egress blocked)'
  && Array.isArray(FC.funded_projects) && FC.funded_projects.length === 0 && FC.status === 'PENDING');
// site_name is the site's own registry name (copied verbatim, checked below) - e.g. the Superfund
// site's name carries "EPA" - so it is blanked before the FACTS scan
const strip = (s) => ({ ...s, site_name: null });
const rest = JSON.stringify({ ...reg, funding_context: null, scenarios: reg.scenarios.map(strip), generic: reg.generic.map(strip),
  staged_tasks: reg.staged_tasks.map((t) => ({ ...t, title: null })) });
ok('[facts] every site_name (and staged task title) carries the site\'s own registry name, verbatim', reg.scenarios.every((s) => s.site_name === sites[s.site]?.name)
  && reg.staged_tasks.every((t) => t.title.endsWith(' - ' + sites[t.place.id]?.name)));
const kit = R('../web/restokit.py').toString('utf8');
const money = /\$\s?\d|\d\s?(million|billion)\b|\bUSD\b/i;
const funded = /\b(EPA|grant(ed|ee)?|award(s|ed)?|funded by|recipient)\b/i;
ok('[facts] outside the headline, no dollar amount, grant, award, recipient or EPA claim appears in the registry or the kit',
  !money.test(rest) && !funded.test(rest) && !money.test(kit) && !funded.test(kit),
  [rest.match(money), rest.match(funded), kit.match(money), kit.match(funded)]);
ok('[facts] the headline amount appears exactly once in the registry', (JSON.stringify(reg).match(/\$82 million/g) || []).length === 1);
const fcKeys = Object.keys(FC).sort().join(',');
ok('[facts] funding_context holds only headline, url, source, funded_projects, status, note', fcKeys === 'funded_projects,headline,note,source,status,url', fcKeys);

// ---- sites and trades
ok('[site] every site-linked scenario names a site in restoration.json', reg.scenarios.every((s) => s.site in sites));
ok('[site] all 11 recorded sites carry at least one scenario', resto.sites.every((s) => reg.scenarios.some((x) => x.site === s.id)) && resto.sites.length === 11);
const evBad = reg.scenarios.filter((s) => !(s.evidence && ['name', 'habitat', 'scale'].includes(s.evidence.field)
  && String(sites[s.site]?.[s.evidence.field]).includes(s.evidence.quote)));
ok('[site] every link\'s evidence quote is in the site\'s own name/habitat/scale text', evBad.length === 0, evBad.map((s) => s.id));
const trBad = ALL.flatMap((s) => s.crew.filter((r) => !slugs.has(r.trade)).map((r) => `${s.id}:${r.trade}`));
ok('[trade] every crew role names a real union slug', trBad.length === 0, trBad);
const subBad = reg.scenarios.filter((s) => !s.crew.every((r) => (sites[s.site]?.trade_needs || []).includes(r.trade)));
ok('[trade] site scenarios staff only from that site\'s own trade_needs', subBad.length === 0, subBad.map((s) => s.id));
ok('[trade] crew role names are unique within a scenario', ALL.every((s) => new Set(s.crew.map((r) => r.role)).size === s.crew.length));

// ---- labels and safety
ok('[label] every scenario is AUTHORED, labelled "training scenario, not the project\'s actual work plan", lessons "unverified general practice"',
  ALL.every((s) => s.provenance === 'AUTHORED' && s.label === "training scenario, not the project's actual work plan" && s.lessons === 'unverified general practice'));
const gBad = ALL.filter((s) => !(s.safety_gates.length >= 1 && s.forbidden.length >= 1 && s.ppe.length >= 1 && s.hazards.length >= 1
  && s.safety_gates.every((g) => s.steps.some((x) => x.id === g.before_step))));
ok('[gate] every scenario has safety gates guarding real steps, forbidden actions, PPE and hazards', gBad.length === 0, gBad.map((s) => s.id));
const env = reg.scenarios.filter((s) => sites[s.site]?.category === 'environmental-monitoring');
ok('[gate] environmental-monitoring sites carry only cleanup-support AWARENESS, forbidding exclusion-zone entry and material handling',
  env.length === 2 && env.every((s) => s.type === 'cleanup-support' && s.family === 'cleanup-awareness'
    && ['enter-exclusion', 'handle-material'].every((f) => s.forbidden.some((x) => x.id === f))));
const handsOn = /\b(remediat|excavat|decontaminat|dig|sample the soil|remove soil)/i;
ok('[gate] awareness scenarios teach no hands-on remediation step', env.every((s) => s.steps.every((x) => !handsOn.test(x.text))),
  env.flatMap((s) => s.steps.filter((x) => handsOn.test(x.text)).map((x) => x.text)));
const sp = reg.scenarios.find((s) => s.type === 'spartina-removal');
ok('[gate] Spartina removal forbids herbicide and teaches no application step',
  sp && sp.forbidden.some((f) => f.id === 'herbicide') && sp.steps.every((x) => !/herbicide|spray/i.test(x.text)));

// ---- scoring determinism (Python fixtures vs the kit's JS scorer)
const js = kit.match(/RESTO_JS = r'''([\s\S]*?)'''/);
const rkScore = new Function(js[1] + '\nreturn rkScore;')();
const fxBad = [];
for (const s of ALL) for (const f of s.fixtures) {
  const a = JSON.stringify(rkScore(s, f.run)), b = JSON.stringify(rkScore(s, f.run));
  if (a !== b || a !== JSON.stringify(f.expect)) fxBad.push(`${s.id}/${f.name}: ${a} vs ${JSON.stringify(f.expect)}`);
}
ok('[score] the kit\'s JS scorer reproduces every Python fixture exactly, twice (deterministic, one arithmetic)', fxBad.length === 0, fxBad);
ok('[score] fixtures separate pass from fail: perfect passes; gate-skipped, forbidden-action, reversed-steps, reversed-missing-ppe fail',
  ALL.every((s) => { const e = Object.fromEntries(s.fixtures.map((f) => [f.name, f.expect.pass]));
    return e.perfect && !e['gate-skipped'] && !e['forbidden-action'] && !e['reversed-steps'] && !e['reversed-missing-ppe']; }));

// ---- staged tasks (TASK_CONTRACT shape)
const bay = J('../bayarea/registry/bayarea.json');
const placed = new Set(Object.values(bay.counties).flatMap((c) => c.restoration_sites.map((x) => x.id)));
const bayPage = R('../web/trade_craft_bay.html').toString('utf8');
const FIELDS = ['id', 'title', 'kind', 'place', 'launch', 'requires', 'provenance', 'source', 'brief', 'seat'];
const stBad = reg.staged_tasks.filter((t) => FIELDS.some((f) => !(f in t)) || t.kind !== 'resto-scenario' || t.provenance !== 'DERIVED'
  || t.place.kind !== 'restoration-site' || !(t.place.id in sites) || t.place.campus !== sites[t.place.id]?.campus || t.place.campus === null
  || !(t.launch.href === null ? t.launch.why.length > 20 && !placed.has(t.place.id)
    : t.launch.href === `web/trade_craft_bay.html#resto=${t.place.id}` && t.launch.lands === 'section' && placed.has(t.place.id)
      && bayPage.includes(`data-resto-run="${t.place.id}"`))
  || t.requires.length !== 0);
ok('[task] staged tasks carry the task-contract fields, a real restoration-site place with its campus, and either the Bay page #resto= link (site placed, run button present) or an honest why', stBad.length === 0, stBad.map((t) => t.id));
ok('[task] every scenario is either staged as a task or listed unwired with a reason',
  reg.scenarios.length === reg.staged_tasks.length + reg.unwired.length && reg.unwired.every((u) => u.why.length > 20));
ok('[counts] counts recompute (none typed)', reg.counts.scenarios === reg.scenarios.length && reg.counts.generic === reg.generic.length
  && reg.counts.staged_tasks === reg.staged_tasks.length && reg.counts.sites_covered === new Set(reg.scenarios.map((s) => s.site)).size);
ok('[play] honesty says a run never enters a completion record', /never enters a completion record/.test(reg.honesty.play));

if (bad) { console.log(`restoration/test_scenarios: ${bad} FAILED, ${n} passed`); process.exit(1); }
console.log(`restoration/test_scenarios: ${n} checks passed - ${reg.scenarios.length} site scenarios across ${reg.counts.sites_covered} sites, ${reg.generic.length} generic`);
