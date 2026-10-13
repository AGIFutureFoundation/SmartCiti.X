/**
 * The whitepaper page (web/smartcitix_whitepaper.html), held to its registries.
 *
 * Reads the BUILT page, its share card and pin, and the registries the page
 * cites - never the generator's own arithmetic. Every data-fig pointer on the
 * page is resolved here independently (RFC 6901, `~1` = `/`, plus the
 * `[k=v,...]` / `[k=v]*` list filters and the `len` / `distinct:` ops that
 * web/build_whitepaper.py documents) and compared with what the page shows.
 *
 *   node web/test_whitepaper.mjs
 *   node web/test_whitepaper.mjs --root=/path/to/a/broken/copy   (mutation runs)
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const argRoot = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(argRoot ? argRoot.slice(7) : join(HERE, '..'));
const read = (p) => readFileSync(join(ROOT, p), 'utf8');

let failed = 0; let passed = 0;
function ok(name, cond, detail) {
  if (cond) { passed++; console.log(`  ok  ${name}`); return; }
  failed++; console.log(`FAIL ${name}`);
  for (const d of [].concat(detail ?? []).slice(0, 8)) console.log(`     ${typeof d === 'string' ? d : JSON.stringify(d)}`);
}
const unesc = (s) => s.replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');

const PAGE = 'web/smartcitix_whitepaper.html';
const CARD = 'web/img/smartcitix_whitepaper_card.png';
const PIN = 'web/img/smartcitix_whitepaper_card.json';
const html = read(PAGE);
const cut = ['</head>', '<body', '<nav'].map((m) => html.indexOf(m)).filter((i) => i >= 0);
const head = html.slice(0, Math.min(...cut));
const seoSrc = read('web/seo.py');
const BASE = seoSrc.match(/^BASE = '([^']+)'/m)[1];
const DESC_MAX = Number(seoSrc.match(/^DESC_MAX = (\d+)/m)[1]);
const CANON = BASE + PAGE;
const ident = read('brand/identity.mjs');
const brand = (f) => (ident.match(new RegExp(`^\\s*${f}: '([^']+)'`, 'm')) || [])[1];
const meta = (k) => { const m = head.match(new RegExp(`<meta (?:name|property)="${k}" content="([^"]*)"`)); return m ? unesc(m[1]) : null; };
const metaN = (k) => (head.match(new RegExp(`<meta (?:name|property)="${k}" `, 'g')) || []).length;

// ---- the resolver, written again here -------------------------------------
const cache = {};
const load = (rel) => (cache[rel] ??= rel.endsWith('.md') ? read(rel) : JSON.parse(read(rel)));
const pUnesc = (s) => s.replace(/~1/g, '/').replace(/~0/g, '~');
function resolveFig(spec, op) {
  const i = spec.indexOf('#'); const rel = spec.slice(0, i); const ptr = spec.slice(i + 1);
  let v;
  if (rel === 'README.md') {
    if (ptr !== '/headline/checks') throw new Error(`README pointer ${ptr}`);
    const m = load(rel).match(/^\*\*([0-9,]+) checks, all passing/m);
    v = m ? Number(m[1].replace(/,/g, '')) : undefined;
  } else {
    v = load(rel);
    for (const seg of ptr.slice(1).split('/')) {
      const f = seg.match(/^\[([^\]]+)\](\*?)$/);
      if (f) {
        const conds = f[1].split(',').map((c) => { const j = c.indexOf('='); return [pUnesc(c.slice(0, j)), pUnesc(c.slice(j + 1))]; });
        const hits = v.filter((x) => x && typeof x === 'object' && conds.every(([k, val]) => String(x[k]) === val));
        v = f[2] ? hits : hits[0];
      } else if (Array.isArray(v)) v = v[Number(seg)];
      else v = v?.[pUnesc(seg)];
      if (v === undefined) throw new Error(`${spec}: nothing at ${seg}`);
    }
  }
  if (op === 'len') v = Array.isArray(v) ? v.length : Object.keys(v).length;
  else if (op?.startsWith('distinct:')) v = new Set(v.map((x) => JSON.stringify(x[op.slice(9)]))).size;
  else if (op) throw new Error(`unknown op ${op}`);
  return v;
}
const show = (v) => (typeof v === 'number' && Number.isInteger(v) ? v.toLocaleString('en-US') : typeof v === 'boolean' ? String(v) : String(v));

// ---- head -------------------------------------------------------------------
ok('[head] one <title>, naming the whitepaper and the product', (head.match(/<title>/g) || []).length === 1
  && /<title>Whitepaper — SmartCiti\.X : Trade Craft Academy<\/title>/.test(head));
const desc = meta('description');
ok(`[head] one meta description, present and at most ${DESC_MAX} characters`, metaN('description') === 1 && desc && desc.length <= DESC_MAX, [desc]);
const canonHref = (head.match(/<link rel="canonical" href="([^"]+)"/) || [])[1];
ok('[head] one canonical link, resolving to BASE + the page path', (head.match(/rel="canonical"/g) || []).length === 1
  && canonHref && new URL(canonHref, CANON).href === CANON, [canonHref]);
const TITLE = unesc((head.match(/<title>([^<]*)<\/title>/) || [])[1] || '');
ok('[head] Open Graph: og:type article, og:title / og:description / og:url repeat the page, og:site_name and og:locale set',
  meta('og:type') === 'article' && meta('og:title') === TITLE && meta('og:description') === desc && meta('og:url') === CANON
  && !!meta('og:site_name') && meta('og:locale') === 'en_US' && metaN('og:type') === 1);
ok('[head] Twitter card: summary_large_image with the same title, description and image',
  meta('twitter:card') === 'summary_large_image' && meta('twitter:title') === TITLE && meta('twitter:description') === desc
  && meta('twitter:image') === meta('og:image') && !!meta('twitter:image:alt'));
ok('[head] theme-color for dark and light, lang="en", one meta charset', (head.match(/<meta name="theme-color" content="#[0-9A-Fa-f]{6}" media="\(prefers-color-scheme: (dark|light)\)">/g) || []).length === 2
  && /^<!doctype html><html lang="en">/.test(html) && (head.match(/<meta charset="utf-8">/g) || []).length === 1);

// ---- share card ----------------------------------------------------------------
const img = meta('og:image');
const cardOk = existsSync(join(ROOT, CARD));
const png = cardOk ? readFileSync(join(ROOT, CARD)) : Buffer.alloc(0);
const isPng = png.length > 24 && png.slice(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]));
const [W, H] = isPng ? [png.readUInt32BE(16), png.readUInt32BE(20)] : [0, 0];
ok('[card] og:image is BASE + web/img/smartcitix_whitepaper_card.png and the file is a 1200 x 630 PNG in the bundle',
  img === BASE + CARD && cardOk && isPng && W === 1200 && H === 630, [img, `${W}x${H}`]);
ok('[card] og:image:width / height are the PNG\'s own IHDR size, with alt text', meta('og:image:width') === String(W)
  && meta('og:image:height') === String(H) && (meta('og:image:alt') || '').length > 40);
let pin = null; try { pin = JSON.parse(read(PIN)); } catch { pin = null; }
const sha = createHash('sha256').update(png).digest('hex');
const pageSha = (html.match(/<img src="img\/smartcitix_whitepaper_card\.png"[^>]*data-sha256="([0-9a-f]{64})"/) || [])[1];
ok('[card] the card matches its pin: sha256 of the file = web/img/smartcitix_whitepaper_card.json = the page\'s data-sha256',
  pin && pin.sha256 === sha && pageSha === sha && pin.image === CARD && pin.width === W && pin.height === H, [sha, pin?.sha256, pageSha]);
const cardBad = (pin?.figures || []).filter((f) => { try { return resolveFig(f.fig, f.op) !== f.value; } catch (e) { return true; } });
ok(`[card] every figure drawn on the card (${pin?.figures?.length ?? 0}) is its registry's value now`,
  pin?.figures?.length >= 4 && cardBad.length === 0, cardBad.map((f) => `${f.label}: card ${f.value}, registry ${(() => { try { return resolveFig(f.fig, f.op); } catch (e) { return e.message; } })()}`));
const descNums = (desc || '').match(/\d[\d,]*/g) || [];
ok('[card] every number in the description is one of the card\'s counted figures', descNums.length > 0
  && descNums.every((n) => (pin?.figures || []).some((f) => show(f.value) === n)), descNums);

// ---- JSON-LD ------------------------------------------------------------------
const lds = [...html.matchAll(/<script type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)];
let ld = null; try { ld = lds.length === 1 ? JSON.parse(lds[0][1]) : null; } catch { ld = null; }
const graph = ld?.['@graph'] || [];
const types = graph.map((g) => g['@type']);
ok('[jsonld] exactly one JSON-LD block, and it parses as a schema.org @graph of TechArticle, Organization, WebSite',
  ld && ld['@context'] === 'https://schema.org' && JSON.stringify(types) === '["TechArticle","Organization","WebSite"]', types);
const art = graph[0] || {}; const org = graph[1] || {};
ok('[jsonld] the Organization is the publisher from brand/identity.mjs, with its contact address',
  org.name === brand('publisher') && org.email === brand('contact') && art.publisher?.['@id'] === org['@id'] && art.author?.['@id'] === org['@id']);
const keys = []; const walk = (o) => { if (o && typeof o === 'object') for (const [k, v] of Object.entries(o)) { keys.push(k); walk(v); } }; walk(ld);
const FORBID = /^(aggregateRating|rating|ratingValue|review|reviews|offers|offer|price|priceCurrency|priceRange|lowPrice|highPrice|hasCourseInstance|educationalCredentialAwarded|accreditation|hasCredential|award)$/i;
ok('[jsonld] no rating, review, offer, price or credential anywhere in the structured data (nor the word price in the page)',
  ld && !keys.some((k) => FORBIDF(k)) && !/\bprice/i.test(lds[0]?.[1] || 'x') && !/\b(?:prices?|\$\s?\d)/i.test(html.replace(/<script[\s\S]*?<\/script>/g, '')),
  keys.filter((k) => FORBIDF(k)));
function FORBIDF(k) { return FORBID.test(k); }
const figSpecs = [...html.matchAll(/data-fig="([^"]+)"/g)].map((m) => unesc(m[1]));
const sources = [...new Set(figSpecs.map((s) => s.split('#')[0]))];
const builts = sources.filter((s) => s.endsWith('.json') && existsSync(join(ROOT, s))).map((s) => load(s)).filter((d) => d && typeof d.built === 'string').map((d) => d.built).sort();
const newest = builts[builts.length - 1];
ok('[jsonld] datePublished = article:published_time = the newest built date among the registries the page cites',
  art.datePublished === newest && art.dateModified === newest && meta('article:published_time') === newest, [art.datePublished, newest]);
ok('[jsonld] the TechArticle names the canonical URL, the card image and the page\'s own headline and description',
  art.url === CANON && art.mainEntityOfPage === CANON && art.image === img && art.description === desc && art.headline && art.headline.length <= 110);

// ---- figures --------------------------------------------------------------------
const main = html.slice(html.indexOf('<main'), html.indexOf('</main>'));
const figEls = [...main.matchAll(/<(\w+)\b[^>]*\bdata-fig="([^"]+)"(?: data-op="([^"]+)")?[^>]*>([^<]*)<\/\1>/g)];
const figBad = [];
for (const [, , spec, op, text] of figEls) {
  let v; try { v = resolveFig(unesc(spec), op && unesc(op)); } catch (e) { figBad.push(`${unesc(spec)}: ${e.message}`); continue; }
  if (show(v) !== unesc(text)) figBad.push(`${unesc(spec)}${op ? ' |' + op : ''}: page "${unesc(text)}", registry "${show(v)}"`);
}
ok(`[figures] every figure on the page (${figEls.length}) matches its registry, resolved here independently`,
  figEls.length > 100 && figEls.length === (main.match(/data-fig="/g) || []).length && figBad.length === 0, figBad);
const vis = main.replace(/<(script|style|svg)\b[\s\S]*?<\/\1>/g, ' ').replace(/<(\w+)\b[^>]*\bdata-fig="[^"]*"[^>]*>[^<]*<\/\1>/g, ' ')
  .replace(/<[^>]+>/g, ' ').replace(/K-12/g, ' ');
const typed = unesc(vis).match(/.{0,30}\d.{0,10}/g) || [];
ok('[figures] no number is typed: the visible text of <main> carries no digit outside a data-fig element (bar the name K-12)', typed.length === 0, typed);
const head1 = figEls.find(([, , s]) => unesc(s) === 'README.md#/headline/checks');
ok('[figures] the check count is the README headline\'s', head1 && head1[4] === (read('README.md').match(/^\*\*([0-9,]+) checks, all passing/m) || [])[1]);

// ---- sections ---------------------------------------------------------------------
const secIds = [...main.matchAll(/<section id="([a-z0-9-]+)" data-paper-section="\1">/g)].map((m) => m[1]);
const hasProg = existsSync(join(ROOT, 'programs/registry/programs.json'));
const hasPaths = existsSync(join(ROOT, 'unionpaths/registry/union_paths.json'));
const want = ['summary', 'worlds', 'training', 'k12', ...(hasProg ? ['sectors'] : []), 'bay', 'robotics', 'hive', 'stack', 'roadmap', 'status', 'contact'];
ok(`[sections] the sections are exactly ${want.length}, in order; a section whose registry is absent is omitted (programmes ${hasProg ? 'present' : 'absent'})`,
  JSON.stringify(secIds) === JSON.stringify(want), [secIds.join(','), want.join(',')]);
const sec = (id) => { const i = main.indexOf(`<section id="${id}"`); return i < 0 ? '' : main.slice(i, main.indexOf('</section>', i)); };
ok(`[sections] union pathways appear iff unionpaths/ has a registry (${hasPaths ? 'present' : 'absent'}), and no section cites a registry that is absent`,
  /Union-hall pathways/.test(sec('training')) === hasPaths && sources.every((s) => existsSync(join(ROOT, s))), sources.filter((s) => !existsSync(join(ROOT, s))));
const textOf = (h) => unesc(h.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ');
const HV = textOf(sec('hive'));
ok('[labels] Omega Hive: SCRIPTED, no AI model, the device\'s speech synthesis, on a click, AUTHORED personalities',
  /SCRIPTED/.test(HV) && /no AI model/.test(HV) && /speech synthesis/.test(HV) && /on a click/.test(HV) && /AUTHORED personalit/.test(HV));
const T = textOf(sec('training'));
ok('[labels] courses: AUTHORED by rule, lessons unverified general practice; unions named are not partners',
  /AUTHORED by rule/.test(T) && /unverified general practice/.test(T) && (!hasPaths || /not partners/.test(T)));
const K = textOf(sec('k12')); const S = textOf(sec('sectors'));
ok('[labels] districts, programmes and sectors are PROPOSED; the UN path PROPOSED and not affiliated',
  /PROPOSED/.test(K) && (sec('k12').match(/chip chip-open">PROPOSED/g) || []).length === (load('schools/registry/schools.json').districts || []).length
  && (!hasProg || (/PROPOSED/.test(S) && /not affiliated/.test(K))));
// SHARE (wave 18, landing 2): the robotics section follows the registries - a trained model is counted, compared and carded
const RB = sec('robotics'); const RT = textOf(RB);
const trained = (() => { try { return resolveFig('robotics/registry/robotics.json#/counts/trained_models'); } catch { return null; } })();
const hasArena = existsSync(join(ROOT, 'robotics/arena/registry/arena.json')) && existsSync(join(ROOT, 'robotics/arena/registry/models.json'));
const hasClaw = existsSync(join(ROOT, 'robotics/claw/registry/claw.json'));
ok('[labels] robotics: the reference policy SCRIPTED, trained models counted from the registry, and no language model trained here',
  /SCRIPTED/.test(RT) && RB.includes('data-fig="robotics/registry/robotics.json#/counts/trained_models">' + show(trained) + '<')
  && /No language model is trained here/.test(RT) && /datasets are for training a robot-learning model elsewhere/.test(RT)
  && (trained === 0 ? /no model comparison is claimed/.test(RT) : !/no model comparison is claimed/.test(RT)));
const lbRows = hasArena ? JSON.parse(read('robotics/arena/registry/arena.json')).leaderboard.rows : [];
const lbOnPage = lbRows.filter((row) => ['success_rate/mean', 'success_rate/ci95/0', 'success_rate/ci95/1', 'win_vs_ref/rate', 'win_vs_ref/ci95/0', 'win_vs_ref/ci95/1']
  .every((f) => RB.includes(`data-fig="robotics/arena/registry/arena.json#/leaderboard/rows/[policy=${row.policy}]/${f}"`)));
ok(`[robotics] the held-out comparison is the arena leaderboard: every policy (${lbRows.length}) with its success rate, paired win rate and both intervals, counted`,
  trained === 0 || (hasArena && lbRows.length >= 2 && lbOnPage.length === lbRows.length
    && JSON.parse(read('robotics/arena/registry/arena.json')).leaderboard.table === 'held_out'), lbRows.map((r) => r.policy).filter((p) => !lbOnPage.some((x) => x.policy === p)));
let bcBad = ['no card'];
if (hasArena && trained > 0) {
  const models = JSON.parse(read('robotics/arena/registry/models.json')).models;
  const arena = JSON.parse(read('robotics/arena/registry/arena.json'));
  const dl = (RB.match(/<dl class="bccard" data-card="([^"]+)">([\s\S]*?)<\/dl>/) || []);
  const m = models.find((x) => x.id === unesc(dl[1] || ''));
  bcBad = [];
  if (!m) bcBad.push('no card on the page names a model in models.json');
  else {
    const shown = Object.fromEntries([...(dl[2] || '').matchAll(/data-fig="robotics\/arena\/registry\/models\.json#\/models\/\[id=[^\]]+\]\/card\/([a-z_]+)"[^>]*>([^<]*)</g)].map((x) => [x[1], unesc(x[2])]));
    for (const [k, v] of Object.entries(m.card)) if (shown[k] !== show(v)) bcBad.push(`card.${k}: page "${shown[k]}", models.json "${show(v)}"`);
    for (const k of Object.keys(shown)) if (!(k in m.card)) bcBad.push(`card.${k} is not in models.json`);
    const ac = arena.cards[m.policy] || {};
    for (const [k, v] of Object.entries(m.card)) if (k in ac && JSON.stringify(ac[k]) !== JSON.stringify(v)) bcBad.push(`arena.json cards.${m.policy}.${k} disagrees with models.json`);
    if (!/not a language model/.test(m.card.what || '')) bcBad.push('the card does not say it is not a language model');
  }
}
ok('[robotics] the trained policy\'s card is printed verbatim, every field of models.json\'s card, and arena.json\'s card for it agrees',
  trained === 0 || bcBad.length === 0, bcBad);
let clawBad = [];
if (hasClaw) {
  const cl = JSON.parse(read('robotics/claw/registry/claw.json'));
  for (const f of ['counts/tournament_runs', 'dataset/samples', 'dataset/episodes', 'dataset/learner', 'counts/agents', 'counts/models'])
    if (!RB.includes(`data-fig="robotics/claw/registry/claw.json#/${f}"`)) clawBad.push('missing ' + f);
  for (const sp of Object.keys(cl.dataset.splits)) for (const k of ['train', 'val', 'test'])
    if (!RB.includes(`data-fig="robotics/claw/registry/claw.json#/dataset/splits/${sp}/${k}"`)) clawBad.push(`missing split ${sp}.${k}`);
  for (const a of cl.agents) { if (a.model !== null || !RB.includes(`/agents/[id=${a.id}]/name"`)) clawBad.push(`agent ${a.id}`); }
  if (cl.counts.models !== 0 || !/SCRIPTED/.test(RT) || !/no AI model/.test(RT)) clawBad.push('Omega Claw agents not SCRIPTED with no AI model');
}
ok(`[robotics] Omega Claw (${hasClaw ? 'present' : 'absent'}): the tournament, the dataset and its splits, and every agent from claw.json, SCRIPTED with no AI model`,
  clawBad.length === 0, clawBad);
const allText = textOf(html.replace(/<(script|style|svg)\b[\s\S]*?<\/\1>/g, ' ').replace(/<head>[\s\S]*?<\/head>/, ' '));
const llm = allText.split(/(?<=[.!?;])\s+/).filter((t) => /\b(LLMs?|large language models?|language models?|GPT|chatbots?|VLA|vision-language)\b/i.test(t)
  && !/\b(no|not|never|none|nothing|neither|nor)\b/i.test(t));
ok('[hygiene] no language-model claim: every sentence on the page that names an LLM, a language model, GPT, a chatbot or a VLA is a denial', llm.length === 0, llm);
const contact = brand('contact');
const C = sec('contact');
let qrSame = false;
try {
  const py = `import segno,io;q=segno.make('mailto:${contact}',error='m');b=io.BytesIO();q.save(b,kind='svg',xmldecl=False,svgns=True,nl=False,scale=6,border=2,dark='#12181B',light='#FFFFFF',svgclass='qr',lineclass=None,omitsize=False);print(b.getvalue().decode())`;
  const want = execFileSync('python3', ['-c', py], { encoding: 'utf8' }).trim();
  const pathOf = (s) => (s.match(/ d="([^"]+)"/) || [])[1];
  qrSame = !!pathOf(want) && pathOf(want) === pathOf(C);
} catch { qrSame = false; }
ok('[contact] a mailto call to action to the brand contact, and a QR code that segno draws for the same mailto',
  contact === 'x@agifuturefoundation.org' && C.includes(`href="mailto:${contact}"`) && /<svg [^>]*class="qr"/.test(C) && qrSame);

// ---- hygiene -------------------------------------------------------------------------
const CODENAMES = ['SHARE', 'PATHWAYS', 'PROGRAMS', 'RESTORE', 'WP', 'WP2', 'WP3', 'VIDEO', 'VIDEO2', 'VIDEO3', 'EVAL', 'EVAL2', 'EVAL3',
  'LEAD', 'HIVE', 'AVATAR', 'BUILD', 'COURSE', 'GROUND', 'GROUND2', 'POLISH', 'ROBO', 'SCENES', 'STREETS', 'WORLD', 'WORLDHD'];
const hitsC = CODENAMES.filter((c) => new RegExp(`(?<![\\w-])${c}(?![\\w-])`).test(html));
const INTERNAL = [/\/tmp\//, /scratchpad/i, /\$SP\b/, /\/home\//, /\bmemory\//, /\bconsoles?\b/i, /\.claude/];
const hitsI = INTERNAL.filter((re) => re.test(html)).map(String);
ok('[hygiene] no agent codename and no internal path anywhere in the page (head, markup, scripts, SVG)', hitsC.length === 0 && hitsI.length === 0, [...hitsC, ...hitsI]);
ok('[hygiene] page markers are neutral: every data-* attribute name is from the neutral set', [...new Set([...html.matchAll(/\bdata-([a-z0-9-]+)=/g)].map((m) => m[1]))]
  .every((n) => /^(fig|op|paper-section|paper-date|sha256|qr|seo-jsonld|sitenav|sitenav-loop|style|theme)$/.test(n) || /^[a-z-]+$/.test(n) && !CODENAMES.some((c) => n.toUpperCase().split('-').includes(c))));

// SHARE (wave 18, landing 2): the 390 px overflow the browser smoke measured came from a nowrap chip and then from a
// 56-character registry path in a quote; the page now lets any long token wrap, and no chip refuses to.
const css = (html.match(/<style>\n:root[\s\S]*?<\/style>/) || [''])[0];
ok('[layout] phone width: the main column wraps long registry tokens (overflow-wrap:anywhere) and no chip is white-space:nowrap',
  /\.wrap \{[^}]*overflow-wrap:anywhere/.test(css) && !/\.chip \{[^}]*nowrap/.test(css));
// ---- wiring --------------------------------------------------------------------------
const nav = read('web/sitenav.py');
const block = (nav.match(/# SHARE BEGIN[^\n]*\n([\s\S]*?)# SHARE END/) || [])[1] || '';
ok('[wiring] web/sitenav.py declares the page inside its anchored SHARE block', /\('web\/smartcitix_whitepaper\.html', 'nav\.page\.whitepaper'\)/.test(block));
ok('[wiring] sitemap.xml lists the page at its canonical URL, and web/seo.py names it an ARTICLE_PAGES entry',
  read('sitemap.xml').includes(`<loc>${CANON}</loc>`) && /ARTICLE_PAGES = \([^)]*'web\/smartcitix_whitepaper\.html'/.test(seoSrc));
ok('[wiring] .github/assemble_site.sh ships web/img (the card) with the pages', /cp -r web\/img _site\/web\/img/.test(read('.github/assemble_site.sh')));
if (!argRoot) {
  let current = true; let out = '';
  try { out = execFileSync('python3', [join(ROOT, 'web/build_whitepaper.py'), '--check'], { encoding: 'utf8' }); } catch (e) { current = false; out = String(e.stdout); }
  ok('[generator] the page, the card and its pin are what web/build_whitepaper.py writes now', current, out.trim().split('\n'));
}

console.log(`whitepaper: ${passed + failed} checks, ${failed} failures`);
process.exit(failed ? 1 : 0);
