/**
 * K-12 pathways page verification (web/trade_craft_schools.html).
 *
 * The page claims one thing per band: these units, these lessons, these
 * quests and these wilds sites suit it, by a stated rule. Every list is
 * recomputed here from the registries - never read back from the page's
 * own figures - and the page is held to it: the right ids in the right
 * band, the counts equal to the lists, K-5 never sent to a seat, a bench
 * or a scored drill, and the honesty lines verbatim.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };
const url = (p) => new URL(p, import.meta.url);
const J = (p) => JSON.parse(readFileSync(url(p)));

const page = readFileSync(url('./trade_craft_schools.html'), 'utf8');
const builder = readFileSync(url('./build_schools.py'), 'utf8');
const schools = J('../schools/registry/schools.json');
const lessonsReg = J('../lessons/registry/lessons.json');
const questsReg = J('../quests/registry/quests.json');
const wilds = J('../wilds/registry/wilds.json');
const halls = J('../pack/registry/halls.json').halls;
const sims = J('../sims/registry/sims.json').sims;

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const L = lessonsReg.lessons;
const kinds = (x) => new Set(x.steps.map((s) => s.kind));
const stages = (x) => new Set(x.steps.map((s) => s.stage));
const BANDS = ['K-5', '6-8', '9-10', '11-12'];
const RULE = {
  'K-5': (x) => [...kinds(x)].every((k) => ['walk', 'placard', 'advisor'].includes(k)),
  '6-8': (x) => x.tier === 'fundamentals' && [...stages(x)].every((s) => s === 'class'),
  '9-10': (x) => x.tier === 'applied',
  '11-12': (x) => x.tier === 'mastery',
};
const section = (b) => {
  const i = page.indexOf(`<section class="band" id="band-${b}"`);
  return i < 0 ? '' : page.slice(i, page.indexOf('</section>', i));
};
const fig = (sec, k) => { const m = sec.match(new RegExp(`data-fig="${k}">(\\d+)<`)); return m ? Number(m[1]) : -1; };
const lessonIds = (sec) => [...sec.matchAll(/href="trade_craft_lessons\.html#lesson-([^"]+)"/g)].map((m) => m[1]);

/* ------------------------------------------------------------- the shell --- */
ok('the page carries the site nav and exactly one h1',
  /class="sitenav/.test(page) && (page.match(/<h1[\s>]/g) || []).length === 1);
ok('the page is built by web/build_schools.py through the site nav helper, and fetches nothing',
  builder.includes('from sitenav import nav_html, labels as nav_labels, NAV_CSS')
  && !/https?:\/\//.test(page.replace(/xmlns='http:\/\/www\.w3\.org\/2000\/svg'/g, '')
    // the search/link-preview card (web/seo.py) names the page's own public URL; naming is not fetching
    .replace(/<meta (?:property|name)="(?:og|twitter):[^"]*" content="[^"]*">/g, '')
    .replace(/<link rel="canonical" href="[^"]*">/g, '')
    .replace(/<script type="application\/ld\+json"[^>]*>[\s\S]*?<\/script>/g, '')));
ok('the page carries the one search card from web/seo.py: a description, a canonical URL and no second <title>',
  (page.match(/<title>/g) || []).length === 1 && (page.match(/name="description"/g) || []).length === 1
  && /<link rel="canonical" href="[^"]*trade_craft_schools\.html">/.test(page) && /id="main"/.test(page));
ok('the builder fails closed: no `.get(` default and no `??` on registry data',
  !/\.get\(/.test(builder) && !/\?\?/.test(builder));
ok('the four bands schools/ declares each have a section, in order, with the level and offer verbatim',
  schools.bands.map((b) => b.band).join() === BANDS.join()
  && schools.bands.every((b) => section(b.band).includes(esc(b.level)) && section(b.band).includes(esc(b.offer)))
  && BANDS.map((b) => page.indexOf(`id="band-${b}"`)).every((v, i, a) => v > 0 && (i === 0 || v > a[i - 1])));

/* ------------------------------------------------------------ honesty ---- */
ok('every district is named with its PROPOSED-partner status verbatim, and the schools honesty lines reach the page',
  schools.districts.every((d) => page.includes(esc(d.district)) && page.includes(esc(d.status)))
  && page.includes(esc(schools.honesty.districts)) && page.includes(esc(schools.honesty.certification)));
ok('lesson content is called unverified general practice, in the lessons pack\'s own words',
  page.includes(esc(lessonsReg.honesty.content)) && /unverified general practice/.test(page));
ok('quests are said to be play, never evidence, once and in the quests pack\'s own sentence',
  page.split(esc(questsReg.honesty)).length === 2 && /never evidence/.test(questsReg.honesty));

/* --------------------------------------------------- the band pathways --- */
for (const b of BANDS) {
  const sec = section(b);
  const want = Object.keys(L).filter((id) => RULE[b](L[id])).sort();
  const got = lessonIds(sec).slice().sort();
  ok(`${b}: the lessons listed are exactly the lessons the band rule selects, recomputed (${want.length})`,
    JSON.stringify(want) === JSON.stringify(got) && fig(sec, 'lessons') === want.length);
  const wantQ = questsReg.quests.filter((q) => q.band === b);
  ok(`${b}: the quests listed are exactly those naming this band (${wantQ.length}), with their hints`,
    fig(sec, 'quests') === wantQ.length
    && wantQ.every((q) => sec.includes(esc(q.title)) && sec.includes(esc(q.hint)))
    && (sec.match(/<span class="qk">/g) || []).length === wantQ.length);
  const wantSites = wilds.worlds.flatMap((w) => w.sites.filter((s) => s.lessons.some((x) => want.includes(x.id))));
  ok(`${b}: the wilds sites listed are exactly those naming a lesson that fits (${wantSites.length})`,
    fig(sec, 'sites') === wantSites.length && wantSites.every((s) => sec.includes(`<b>${esc(s.id)}</b>`)));
}
ok('K-5 is explore-only: no unit table, and no listed lesson puts a learner at a seat, a bench or a scored drill',
  fig(section('K-5'), 'units') === 0 && !section('K-5').includes('<table')
  && lessonIds(section('K-5')).every((id) => ![...kinds(L[id])].some((k) => ['sim', 'walkaround', 'crew', 'station', 'crib'].includes(k))));
ok('6-8 takes the class half of every unit: stations and crib drill, and no floor seat column',
  fig(section('6-8'), 'units') === schools.units.length && !section('6-8').includes('<th>Floor seats</th>')
  && section('6-8').includes('<th>Crib drill</th>'));
ok('9-10 carries simulator floor time: every unit with its floor seats named from sims/',
  fig(section('9-10'), 'units') === schools.units.length
  && schools.units.every((u) => {
    /* per row, not per section: a name that survives in some other row must not cover for this one */
    const sec = section('9-10');
    const i = sec.indexOf(`#course-${u.hall}"`);
    const row = i < 0 ? '' : sec.slice(sec.lastIndexOf('<tr>', i), sec.indexOf('</tr>', i));
    const seats = row.split('</td>')[3] || '';
    return u.floor_sims.every((s) => seats.includes(esc(sims[s].name)));
  }));
ok('11-12 ends at the unaided gate, quoted from each unit, and says plainly when no lesson sits at its tier',
  fig(section('11-12'), 'units') === schools.units.length
  && schools.units.every((u) => section('11-12').includes(esc(u.gate)))
  && (Object.values(L).some((x) => x.tier === 'mastery') || section('11-12').includes('data-empty="lessons"')));
ok('every unit row links to its hall\'s course on the lessons page, and every lesson link lands on a lesson that exists',
  schools.units.every((u) => section('9-10').includes(`trade_craft_lessons.html#course-${u.hall}"`))
  && lessonIds(page).every((id) => id in L));
ok('every hall named in a unit row is the roster\'s own name',
  schools.units.every((u) => section('9-10').includes(esc(halls.find((h) => h.slug === u.hall).name))));
ok('a composed lesson is labelled composed wherever it is listed, never passed off as hand-written',
  BANDS.every((b) => [...section(b).matchAll(/#lesson-([^"]+)">[^<]*<\/a> <span class="meta">[^]*?<span class="auth">([^<]+)</g)]
    .every((m) => (L[m[1]].authoring === 'rule') === (m[2] === 'composed'))));
ok('the page carries no badge, score or completion field: pathways are guidance, not a record',
  !/localStorage|sessionStorage|indexedDB/.test(page) && !/data-tc-quest=|data-tc-egg=/.test(page));

const stamp = createHash('sha256').update(page).digest('hex').slice(0, 16);
console.log(`schools page: ${n} checks, 0 failures - `
  + BANDS.map((b) => `${b} ${fig(section(b), 'lessons')}L/${fig(section(b), 'units')}U/${fig(section(b), 'quests')}Q`).join(', ')
  + ` (page ${stamp})`);
