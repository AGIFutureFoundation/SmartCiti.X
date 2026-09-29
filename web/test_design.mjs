// web/test_design.mjs - the template gallery and the design kit behind it.
// Static: reads the built page, the icon manifest and the b-roll registry.
// Prints `  ok ` per check; FAIL at column 0 and a non-zero exit on failure.
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
const FILE = process.env.DESIGN_PAGE || join(HERE, 'trade_craft_design.html');
let fails = 0, oks = 0;
const check = (cond, m) => { if (cond) { oks++; console.log('  ok ' + m); } else { fails++; console.log('FAIL ' + m); } };

const html = readFileSync(FILE, 'utf8');
const ICONS = JSON.parse(readFileSync(join(HERE, 'vendor/icons/manifest.json'), 'utf8'));
const MEDIA = JSON.parse(readFileSync(join(ROOT, 'media/registry/media.json'), 'utf8'));
const TEMPLATES = JSON.parse(execFileSync('python3', ['-c',
  'import sys,json;sys.path.insert(0,"web");import design_kit as k;print(json.dumps(k.TEMPLATES))'],
  { cwd: ROOT, encoding: 'utf8' }));

// structure
check((html.match(/<h1[\s>]/g) || []).length === 1, 'exactly one <h1>');
check(/<nav class="sitenav" data-sitenav/.test(html), 'carries the site nav');
check(/<link rel="stylesheet" href="vendor\/fonts\/fonts.css">/.test(html), 'uses the self-hosted fonts');
check(!/(?:src|href)="https?:/.test(html), 'no page asset or link reaches another origin');
check(/<link rel="icon" href="data:image\/svg\+xml,/.test(html), 'declares the inline brand icon (no favicon.ico request)');
check(TEMPLATES.length >= 11, `the kit declares its templates (${TEMPLATES.length})`);
for (const t of TEMPLATES) {
  // from this template's section marker to the next one (a template may
  // itself be a <section>, so the closing tag is no boundary)
  const at = html.indexOf(`<section class="g-sec" id="t-${t}"`);
  const next = html.indexOf('<section class="g-sec"', at + 1);
  const sec = at < 0 ? '' : html.slice(at, next < 0 ? undefined : next);
  check(sec.includes('data-theme="dark"') && sec.includes('data-theme="light"'),
    `${t}: shown in dark AND light`);
  check(new RegExp(`<pre><code>from design_kit import[^<]*\\b${t}\\b`).test(sec)
    && new RegExp(`\\n${t}\\(`).test(sec), `${t}: carries its usage snippet`);
}

// the palettes: the brand as given, and a light theme that reads
const pal = (theme) => {
  const m = html.match(new RegExp(`\\[data-theme="${theme}"\\]\\{([^}]*)\\}`));
  const out = {};
  if (m) for (const [, k, v] of m[1].matchAll(/--dk-([a-z-]+):(#[0-9A-Fa-f]{6})/g)) out[k] = v;
  return out;
};
const dark = pal('dark'), light = pal('light');
const BRAND = { plate: '#12181B', panel: '#182023', ink: '#E8EDEC', muted: '#93A3A6', amber: '#E8A33D', steel: '#41C4D4' };
check(Object.entries(BRAND).every(([k, v]) => dark[k] === v), 'the dark palette is the brand, value for value');
const lum = (h) => {
  const c = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
    .map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
// computed HERE from the page's own CSS, independently of design_kit.contrast()
const PAIRS = [['ink', 'plate', 7], ['ink', 'panel', 7], ['muted', 'plate', 4.5], ['muted', 'panel', 4.5],
  ['amber', 'panel', 4.5], ['steel', 'panel', 4.5], ['link', 'panel', 4.5], ['amber-ink', 'amber', 4.5]];
for (const [name, p] of [['dark', dark], ['light', light]]) {
  const bad = PAIRS.filter(([f, b, min]) => !(p[f] && p[b] && ratio(p[f], p[b]) >= min))
    .map(([f, b]) => `${f}/${b}`);
  check(!bad.length, `${name}: every text/background pair meets WCAG AA${bad.length ? ' - fails ' + bad : ''}`);
}

// the hero: a muted looping video with a poster, both codecs, a real pause control
// (the design_kit hero template's own video: the first one inside a data-dk-hero section)
const kitHeroAt = html.indexOf('<section class="dk-hero" data-dk-hero');
const vid = kitHeroAt < 0 ? null : html.slice(kitHeroAt).match(/<video([^>]*)>([\s\S]*?)<\/video>/);
check(vid && /\bmuted\b/.test(vid[1]) && /\bplaysinline\b/.test(vid[1]) && /\bloop\b/.test(vid[1]) && /poster="/.test(vid[1]),
  'hero video is muted, inline, looping and has a poster');
const srcs = vid ? [...vid[2].matchAll(/<source src="([^"]+)" type="([^"]+)">/g)] : [];
check(srcs.length === 2 && srcs[0][2] === 'video/webm' && srcs[1][2] === 'video/mp4',
  'hero offers VP9 webm first, then H.264 mp4');
const known = new Set(MEDIA.clips.flatMap((c) => Object.values(c.files).map((f) => f.path)));
const used = [...srcs.map((s) => s[1]), vid && vid[1].match(/poster="([^"]+)"/)[1]].filter(Boolean);
check(used.length === 3 && used.every((u) => known.has('web/' + u) && existsSync(join(HERE, u))),
  'every hero file is a registered b-roll file that exists');
{
  const shown = MEDIA.clips.find((c) => used.length && 'web/' + used[0] === c.files.webm.path);
  check(shown && (shown.hero || html.includes(`shows ${shown.id}, which is NOT hero quality`)),
    'the hero clip is hero quality, or the page says plainly that it is not');
}
check(/<button type="button" class="dk-hero-pause" aria-pressed="false"/.test(html), 'the pause control is a button with a pressed state');
check(/prefers-reduced-motion: reduce\)'\)\.matches[\s\S]*removeAttribute\('autoplay'\)/.test(html),
  'reduced motion: the video never autoplays');

// icons: only vendored ones, inlined and hidden from assistive tech
const iconNames = [...html.matchAll(/class="dk-icon lucide lucide-([a-z0-9-]+)"/g)].map((m) => m[1]);
check(iconNames.length > 0 && iconNames.every((n) => ICONS.icons.includes(n)), `every inlined icon is a vendored one (${new Set(iconNames).size} distinct)`);
check(!/<svg (?![^>]*aria-hidden="true")[^>]*class="dk-icon/.test(html), 'every icon is aria-hidden');

// figures: computed from the registries, never typed
const stat = (label) => { const m = html.match(new RegExp(`dk-stat-v">(\\d+)</span><span class="dk-stat-l">${label}<`)); return m ? +m[1] : NaN; };
check(stat('templates in this kit') === TEMPLATES.length, 'stat: templates = design_kit.TEMPLATES');
check(stat('icons vendored') === ICONS.icons.length, 'stat: icons = the icon manifest');
check(stat('b-roll clips') === MEDIA.clips.length, 'stat: clips = the b-roll registry');
check(stat('seconds of footage') === MEDIA.clips.reduce((a, c) => a + c.duration_s, 0), 'stat: seconds = the b-roll registry');

// the site nav reads --ink/--panel/--line/--muted/--mark (web/sitenav.py NAV_CSS). A kit page must hand it the kit
// palette and keep `.dk a` off the nav links, or the header labels fall to 2.09:1 in dark (HOMEUX, wave 1).
const bridge = html.match(/body\.dk\{([^}]*)\}/);
check(!!bridge && ['ink', 'panel', 'line', 'muted', 'mark'].every((v) => new RegExp(`--${v}:var\\(--dk-`).test(bridge[1])),
  'nav palette: body.dk maps --ink/--panel/--line/--muted/--mark onto kit tokens');
check(/\.dk \.sitenav a\{color:inherit\}/.test(html),
  'nav palette: .dk .sitenav a{color:inherit} (0,2,1) outranks .dk a (0,1,1) on nav links');
check(/:root\{[^}]*color-scheme:dark/.test(html) && /prefers-color-scheme: light\)\{:root:not\(\[data-theme="dark"\]\)\{[^}]*color-scheme:light/.test(html),
  'nav palette: root color-scheme follows the kit theme (system colours match the plate)');
// the site nav's skip link (sitenav, wave 2) targets #main; the page's main region must carry that id, exactly once
check((html.match(/\bid="main"/g) || []).length === 1 && /<main id="main">/.test(html),
  'skip link: <main id="main"> is the one #main target');


// ------------------------------------------------------------ wave 3: pagehero band, theme layer, clip gallery
const PH = JSON.parse(execFileSync('python3', ['-c',
  'import sys,json;sys.path.insert(0,"web");import pagehero as p;'
  + 'print(json.dumps({"ids":p.clip_ids(),"text":p.HERO_TEXT,"alpha":p.SCRIM_TEXT_ALPHA,"min":p.MIN_RATIO,"patterns":p.PATTERNS}))'],
  { cwd: ROOT, encoding: 'utf8' }));
const bands = [...html.matchAll(/<section class="ph" data-ph data-ph-clip="([^"]+)"[^>]*>([\s\S]*?)<\/section>/g)];
check(bands.length >= 1 && /<body class="[^"]*\btc-theme\b/.test(html), `pagehero: the page opens on a hero band and opts into the theme (${bands.length} bands)`);
const top = bands[0];
check(!!top && html.indexOf(top[0]) > html.indexOf('id="tc-main"') && html.indexOf(top[0]) < html.indexOf('<main id="main">'),
  'pagehero: the first band sits right after the nav skip target, before <main>');
check(!!top && /<h1 class="ph-title">/.test(top[2]), 'pagehero: the first band carries the page\'s one <h1>');
const clipIds = new Set(MEDIA.clips.map((c) => c.id));
check(bands.every((b) => clipIds.has(b[1])), 'pagehero: every band\'s clip id resolves in media/registry/media.json');
check(bands.every((b) => {
  const c = MEDIA.clips.find((x) => x.id === b[1]);
  const poster = (b[2].match(/<img src="([^"]+)" alt="" width="(\d+)" height="(\d+)"/) || []);
  const v = b[2].match(/<video([^>]*)>/);
  return c && poster[1] && 'web/' + poster[1] === c.files.poster.path && existsSync(join(HERE, poster[1]))
    && v && !/\ssrc=/.test(v[1]) && /\bmuted\b/.test(v[1]) && /\bloop\b/.test(v[1]) && /\bplaysinline\b/.test(v[1])
    && /aria-hidden="true"/.test(v[1]) && /tabindex="-1"/.test(v[1])
    && 'web/' + v[1].match(/data-webm="([^"]+)"/)[1] === c.files.webm.path
    && 'web/' + v[1].match(/data-webm480="([^"]+)"/)[1] === c.files.preview.path
    && 'web/' + v[1].match(/data-mp4="([^"]+)"/)[1] === c.files.mp4.path;
}), 'pagehero: poster <img alt=""> sized, video muted/loop/inline/aria-hidden with NO src in markup, sources are the clip\'s registered files');
check(bands.every((b) => /<button type="button" class="ph-toggle" aria-pressed="false" hidden data-pause="[^"]+" data-play="[^"]+">/.test(b[2])),
  'pagehero: every band has a pause/play <button> with a pressed state and both labels (WCAG 2.2.2)');
// the band's script: reduced motion and Save-Data leave the poster; the source is only set after that gate
{
  const js = (html.match(/<script>(\(\(\) => \{\n  const reduce = matchMedia\('\(prefers-reduced-motion: reduce\)'\);[\s\S]*?)<\/script>/) || [])[1] || '';
  const gate = js.indexOf("if (reduce.matches || saveData) { state('poster'); continue; }");
  const src = js.indexOf('v.src =');
  check(gate > 0 && src > gate && /saveData = !!\(conn && conn\.saveData\)/.test(js),
    'pagehero reduced-motion path: reduced motion or Save-Data -> poster only, video src is set only after that gate');
  check(/max-width: 640px[\s\S]*v\.dataset\.webm480/.test(js) && /aria-pressed', String\(s === 'paused'\)/.test(js),
    'pagehero: small screens take the 480 px preview; the toggle\'s aria-pressed follows the state');
  check(/@media \(prefers-reduced-motion:reduce\)\{\.ph-media video\{display:none\}/.test(html),
    'pagehero reduced-motion path: CSS also hides the video under reduced motion');
}
// contrast, recomputed HERE from the page's CSS and the registry's measured brightest colour
{
  const css = html.match(/\.ph-scrim\{[^}]*background:linear-gradient\(0deg,([^}]*)\)\}/);
  const alphas = css ? [...css[1].matchAll(/rgb\(18 24 27 \/ ([0-9.]+)\)/g)].map((m) => +m[1]) : [];
  const a = alphas.length ? Math.min(...alphas) : NaN;
  const desk = html.match(/@media \(min-width:900px\)\{\.ph-scrim\{background:\s*linear-gradient\(90deg,([^)]*\)[^)]*\)[^)]*\))/);
  const deskA = desk ? [...desk[1].matchAll(/\/ ([0-9.]+)\) (\d+)%/g)].filter((m) => +m[2] <= 58).map((m) => +m[1]) : [];
  check(a === PH.alpha && deskA.length >= 2 && Math.min(...deskA) >= PH.alpha,
    `pagehero contrast: the scrim is plate at >= ${PH.alpha} wherever text sits (phone ${a}, desktop text zone ${deskA})`);
  const colorOf = (sel, prop = 'color') => { const m = html.match(new RegExp(`${sel}\\{[^}]*?\\b${prop}:(#[0-9A-Fa-f]{6})`)); return m ? m[1] : null; };
  const grad = html.match(/\.ph-accent-gradient\{background:linear-gradient\(95deg,(#[0-9A-Fa-f]{6}),(#[0-9A-Fa-f]{6})\)/);
  const cols = { title: colorOf('\\.ph-title'), lede: colorOf('\\.ph-lede'), kicker: colorOf('\\.ph-kicker'),
    'accent-from': grad && grad[1], 'accent-to': grad && grad[2] };
  const hex = (c) => '#' + c.map((x) => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, '0')).join('').toUpperCase();
  const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const low = [];
  for (const b of bands) {
    const c = MEDIA.clips.find((x) => x.id === b[1]);
    if (!c || !c.measured || !/^#[0-9A-Fa-f]{6}$/.test(c.measured.brightest_rgb || '')) { low.push(`${b[1]}: no measured brightest colour`); continue; }
    const under = hex(rgb('#12181B').map((p, i) => a * p + (1 - a) * rgb(c.measured.brightest_rgb)[i]));
    for (const [k, v] of Object.entries(cols)) {
      const r = v ? ratio(v, under) : 0;
      if (!(r >= 4.5)) low.push(`${b[1]} ${k} ${v} on ${under} = ${r.toFixed(2)}`);
    }
    const shown = +(b[0].match(/data-ph-contrast-min="([0-9.]+)"/) || [])[1];
    if (!(shown >= 4.5)) low.push(`${b[1]}: data-ph-contrast-min ${shown}`);
  }
  check(Object.values(cols).every(Boolean) && !low.length,
    'pagehero contrast asserted: every hero text colour >= 4.5:1 over the scrim composited on the clip\'s measured brightest colour'
    + (low.length ? ' - ' + low.join('; ') : ''));
}
check(MEDIA.clips.every((c) => c.measured && /^#[0-9A-F]{6}$/.test(c.measured.brightest_rgb) && c.measured.pixels > 0),
  'every registered clip carries its measured brightest colour (media/build.py)');
check(PH.ids.length === MEDIA.clips.length && PH.ids.every((i) => clipIds.has(i)),
  `every clip id resolves: pagehero.clip_ids() is exactly the registry's clips (${PH.ids.length})`);
// the clip gallery shows every registered clip, and each plays only on request
{
  const cards = [...html.matchAll(/<article class="tc-card g-clip" data-clip="([^"]+)"[^>]*><video([^>]*)><source src="([^"]+)"/g)];
  const ids = cards.map((m) => m[1]);
  check(ids.length === MEDIA.clips.length && MEDIA.clips.every((c) => ids.includes(c.id)),
    `clip gallery: every registered clip is shown once (${ids.length})`);
  check(cards.every((m) => /\bcontrols\b/.test(m[2]) && /preload="none"/.test(m[2]) && !/\bautoplay\b/.test(m[2])
    && existsSync(join(HERE, m[3])) && MEDIA.clips.find((c) => c.id === m[1]).files.preview.path === 'web/' + m[3]),
    'clip gallery: previews have controls, preload none, never autoplay, and play the registered 480 px file');
  check(MEDIA.clips.every((c) => ['webm', 'mp4'].every((k) => c.files[k].bytes <= MEDIA.budget_bytes)),
    'every clip is within the per-codec budget');
}
// the theme layer
check(/body\.tc-theme\{[^}]*--tc-plate:#12181B/.test(html) && /body\.tc-theme \[data-theme="light"\]\{[^}]*--tc-plate:#F4F6F6/.test(html),
  'theme: tc tokens come from design_kit (dark default, light override)');
check(/body\.tc-theme :focus-visible\{outline:3px solid var\(--tc-steel\)/.test(html), 'theme: a visible focus ring');
check(/html\.tc-reveal-on body\.tc-theme \[data-tc-reveal\]\{opacity:0/.test(html)
  && /prefers-reduced-motion:reduce\)\{[^@]*html\.tc-reveal-on body\.tc-theme \[data-tc-reveal\]\{opacity:1;transform:none;transition:none\}/.test(html)
  && /if \(matchMedia\('\(prefers-reduced-motion: reduce\)'\)\.matches \|\| !\('IntersectionObserver' in window\)\) return;/.test(html),
  'theme: scroll reveal hides nothing without JS, IntersectionObserver or motion');
check(/@supports \(\(-webkit-backdrop-filter:blur\(1px\)\) or \(backdrop-filter:blur\(1px\)\)\)\{body\.tc-theme \.tc-panel/.test(html)
  && /body\.tc-theme \.tc-panel\{background:var\(--tc-panel\)/.test(html), 'theme: glass panel with a solid fallback');
// kit provenance
check(PH.patterns.length >= 5 && PH.patterns.every((p) => html.includes(`<td>${p.kit.replace(/&/g, '&amp;')}</td><td>${p.license}</td>`)),
  `kit provenance: every re-expressed template-kit pattern is named with its kit and licence (${PH.patterns.length})`);

// ------------------------------------------------------------ wave 3: the five site styles (nav Style menu)
{
  const ST = JSON.parse(execFileSync('python3', ['-c',
    'import sys,json;sys.path.insert(0,"web");import design_kit as k;'
    + 'print(json.dumps({"ids":[s["id"] for s in k.STYLES],"key":k.STYLE_KEY,"pairs":k.STYLE_PAIRS,"hero":k.STYLE_HERO_TEXT}))'],
    { cwd: ROOT, encoding: 'utf8' }));
  check(ST.ids.length === 5 && new Set(ST.ids).size === 5, `styles: exactly five distinct styles (${ST.ids})`);
  const blocks = {};
  for (const m of html.matchAll(/\/\*style:([a-z]+)\*\/[^{]*\{([^}]*)\}/g)) {
    const tok = {};
    for (const [, k, v] of m[2].matchAll(/--(dk-[a-z-]+|st-scrim|st-scrim-a):([#0-9A-Za-z.]+)/g)) tok[k] = v;
    blocks[m[1]] = tok;
  }
  check(ST.ids.every((i) => blocks[i]) && Object.keys(blocks).length === 5, 'styles: the page CSS carries one token block per style');
  const T = (i, k) => blocks[i] && blocks[i][{ 'accent': 'dk-amber', 'accent-ink': 'dk-amber-ink', 'scrim': 'st-scrim' }[k] || 'dk-' + k];
  const hex2 = (c) => '#' + c.map((x) => Math.round(x).toString(16).padStart(2, '0')).join('').toUpperCase();
  const rgb2 = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  for (const i of ST.ids) {
    const low = [];
    for (const [f, b, min] of ST.pairs) {
      const r = T(i, f) && T(i, b) ? ratio(T(i, f), T(i, b)) : 0;
      if (!(r >= min)) low.push(`${f}/${b} ${r.toFixed(2)} < ${min}`);
    }
    const a = blocks[i] ? +blocks[i]['st-scrim-a'] : NaN;
    const under = T(i, 'scrim') ? hex2(rgb2(T(i, 'scrim')).map((p) => a * p + (1 - a) * 255)) : null;
    for (const [k, v] of Object.entries(ST.hero)) {
      const r = under ? ratio(v, under) : 0;
      if (!(r >= 4.5)) low.push(`hero ${k} over scrim ${r.toFixed(2)} < 4.5`);
    }
    // the page's own hero rule for this style must use that same scrim alpha
    const ph = new RegExp(`html\\[data-style="${i}"\\] \\.ph-scrim[^{]*\\{background:linear-gradient\\(0deg,rgb\\(([0-9 ]+) \\/ [.0-9]+\\) 0%,rgb\\([0-9 ]+ \\/ ([.0-9]+)\\) 45%`).exec(html);
    if (!ph || +ph[2] !== a || ph[1] !== rgb2(T(i, 'scrim')).join(' ')) low.push('hero scrim rule does not use the style scrim');
    check(!low.length, `style ${i}: text/bg, muted/bg, accent button, links and the hero scrim all meet contrast`
      + (low.length ? ' - ' + low.join('; ') : ''));
  }
  // every document page's hero clip (web/herovideo.py DOC_HERO_PAGES), in every style: the style's own scrim
  // composited over THAT clip's measured brightest colour (media.json), each hero text colour >= 4.5
  const DOC = JSON.parse(execFileSync('python3', ['-c',
    'import sys,json;sys.path.insert(0,"web");import herovideo as h;'
    + 'print(json.dumps({k:v[1] for k,v in h.DOC_HERO_PAGES.items()}))'], { cwd: ROOT, encoding: 'utf8' }));
  const lowDoc = [];
  let measuredDoc = 0;
  for (const [pg, cid] of Object.entries(DOC)) {
    const c = MEDIA.clips.find((x) => x.id === cid);
    if (!c || !c.measured || !/^#[0-9A-Fa-f]{6}$/.test(c.measured.brightest_rgb || '')) { lowDoc.push(`${pg}: clip ${cid} has no measured brightest colour`); continue; }
    for (const i of ST.ids) {
      const a = blocks[i] ? +blocks[i]['st-scrim-a'] : NaN;
      const under = T(i, 'scrim') ? hex2(rgb2(T(i, 'scrim')).map((p, j) => a * p + (1 - a) * rgb2(c.measured.brightest_rgb)[j])) : null;
      for (const [k, v] of Object.entries(ST.hero)) {
        const r = under ? ratio(v, under) : 0;
        measuredDoc++;
        if (!(r >= 4.5)) lowDoc.push(`${pg}/${cid}/${i} hero ${k} ${r.toFixed(2)} < 4.5`);
      }
    }
  }
  check(!lowDoc.length && measuredDoc === Object.keys(DOC).length * ST.ids.length * Object.keys(ST.hero).length,
    `document-page heroes: every page's clip, measured under each of the five styles' scrims, keeps all hero text >= 4.5 (${measuredDoc} pairs)`
    + (lowDoc.length ? ' - ' + lowDoc.join('; ') : ''));
  // every style in BOTH colour schemes: the style block's tokens win (!important); any token a style leaves unset
  // falls back to that scheme's palette, so the nav, badge and button pairs are resolved per scheme and measured
  const schemePal = (scheme) => {
    const dkB = html.match(new RegExp(`\\n\\[data-theme="${scheme}"\\]\\{([^{}]*--dk-plate:[^{}]*)\\}`));
    const tcB = html.match(new RegExp(`\\n\\[data-theme="${scheme}"\\] body\\.tc-theme,body\\.tc-theme\\[data-theme="${scheme}"\\]\\{([^{}]*)\\}`));
    const p = {};
    for (const b of [dkB, tcB]) if (b) for (const [, k, v] of b[1].matchAll(/--((?:dk|tc)-[a-z-]+):(#[0-9A-Fa-f]{6})/g)) p[k] = v;
    return dkB && tcB ? p : null;
  };
  const SCHEME_PAIRS = [
    ['nav ink/panel', 'ink', 'panel', 'dk-ink', 'dk-panel', 7], ['nav muted/panel', 'muted', 'panel', 'dk-muted', 'dk-panel', 4.5],
    ['badge ink/panel', 'tc-ink', 'tc-panel', 'tc-ink', 'tc-panel', 4.5], ['badge ok/panel', 'tc-ok', 'tc-panel', 'tc-ok', 'tc-panel', 4.5],
    ['badge warn/panel', 'tc-warn', 'tc-panel', 'tc-warn', 'tc-panel', 4.5], ['badge info/panel', 'tc-steel', 'tc-panel', 'tc-steel', 'tc-panel', 4.5],
    ['badge muted/panel', 'tc-muted', 'tc-panel', 'tc-muted', 'tc-panel', 4.5],
    ['button tc primary', 'tc-amber-ink', 'tc-amber', 'tc-amber-ink', 'tc-amber', 4.5], ['button kit primary', 'dk-amber-ink', 'dk-amber', 'dk-amber-ink', 'dk-amber', 4.5],
    ['button kit ghost', 'dk-ink', 'dk-panel', 'dk-ink', 'dk-panel', 4.5]];
  const lowScheme = [];
  let schemeN = 0;
  for (const scheme of ['dark', 'light']) {
    const P = schemePal(scheme);
    if (!P) { lowScheme.push(`no ${scheme} palette found in the page CSS`); continue; }
    for (const i of ST.ids) {
      const full = [...html.matchAll(new RegExp(`/\\*style:${i}\\*/[^{]*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]).join(';');
      const S = {};
      for (const [, k, v] of full.matchAll(/--([a-z-]+):(#[0-9A-Fa-f]{6})!important/g)) S[k] = v;
      for (const [name, sf, sb, pf, pb, min] of SCHEME_PAIRS) {
        const f = S[sf] || P[pf], b = S[sb] || P[pb];
        const r = f && b ? ratio(f, b) : 0;
        schemeN++;
        if (!(r >= min)) lowScheme.push(`${i}/${scheme} ${name} ${r.toFixed(2)} < ${min}`);
      }
    }
  }
  check(!lowScheme.length && schemeN === 2 * ST.ids.length * SCHEME_PAIRS.length,
    `styles x schemes: every style's nav, badge and button pairs pass in BOTH light and dark schemes (${schemeN} pairs)`
    + (lowScheme.length ? ' - ' + lowScheme.join('; ') : ''));
  // the kit-hero preview's text sits on a SOLID plate from tokens (QA eval_styles: a weak scrim stop over a
  // white pixel measured 1.10-1.58), so it reads ink/panel and muted/panel, asserted per style above
  const kp = html.match(/\.g-frame \.dk-hero \.dk-hero-body\{([^}]*)\}/);
  const kc = html.match(/\.g-frame \.dk-hero \.dk-hero-credit\{([^}]*)\}/);
  const kr = (sel) => (html.match(new RegExp(`\\.g-frame \\.dk-hero ${sel.replace(/\./g, '\\.')}\\{color:(var\\(--dk-[a-z]+\\))`)) || [])[1];
  check(kp && /background:var\(--dk-panel\)/.test(kp[1]) && /(^|;)color:var\(--dk-ink\)/.test(kp[1]) && !/#[0-9A-Fa-f]{3,6}/.test(kp[1])
    && kc && /background:var\(--dk-panel\)/.test(kc[1]) && /color:var\(--dk-muted\)/.test(kc[1])
    && kr('.dk-hero-body .dk-eyebrow') === 'var(--dk-muted)' && kr('.dk-hero-body .dk-hero-lede') === 'var(--dk-muted)'
    && kr('.dk-hero-body .dk-btn-ghost') === 'var(--dk-ink)',
    'kit-hero preview: body text, eyebrow, lede, ghost button and credit sit on a solid --dk-panel plate in token colours (no hex)');
  const radios = [...html.matchAll(new RegExp(`<input type="radio" name="${ST.key}" value="([a-z]+)">`, 'g'))].map((m) => m[1]);
  check(JSON.stringify(radios) === JSON.stringify(ST.ids) && /<details class="sitenav-style" data-sitenav-style><summary>/.test(html)
    && /<fieldset class="sn-styles"><legend>[^<]+<\/legend>/.test(html),
    'switcher: the nav Style menu is a disclosure with a legend-labelled radio group of the five styles');
  const head = html.slice(0, html.indexOf('</head>'));
  const hs = head.indexOf(`localStorage.getItem('${ST.key}')`);
  check(hs > 0 && hs < head.indexOf('<style>') && /\(\(\)=>\{try\{var s=localStorage\.getItem/.test(head)
    && /catch\(e\)\{\}\}\)\(\);/.test(head),
    'switcher: a head snippet sets <html data-style> from storage before the first stylesheet, inside try/catch');
  check(/try\{v=localStorage\.getItem\(K\)\}catch\(e\)\{v=null\}/.test(html) && /try\{localStorage\.setItem\(K,t\.value\)\}catch\(e\)\{\}/.test(html),
    'switcher: the page script reads and writes storage only inside try/catch');
  check(ST.ids.every((i) => html.includes(`html:has(input[name="${ST.key}"][value="${i}"]:checked)`)),
    'switcher: each style also applies from the checked radio alone (works with storage or script blocked)');
  const cards = [...html.matchAll(/<article class="g-style" data-style-preview="([a-z]+)" data-style-min="([0-9.]+)">[\s\S]*?<ul class="g-ratios">([\s\S]*?)<\/ul>/g)];
  check(cards.length === 5 && cards.every((c) => ST.ids.includes(c[1]) && +c[2] >= 4.5 && (c[3].match(/<li>/g) || []).length === ST.pairs.length + Object.keys(ST.hero).length),
    'design page: a side-by-side preview of all five styles, each card listing its measured ratios');
}
// ---- Materials & colour (PATTERN, wave 11): exterior recipes + colour categories drawn by patternkit
{
  const EXT = JSON.parse(readFileSync(join(ROOT, 'surfaces/registry/exterior.json'), 'utf8'));
  const en = JSON.parse(readFileSync(join(ROOT, 'i18n/locales/en.json'), 'utf8')).strings;
  const at = html.indexOf('<section class="g-sec" id="materials"');
  const next = html.indexOf('<section class="g-sec"', at + 1);
  const sec = at < 0 ? '' : html.slice(at, next < 0 ? html.indexOf('</main>') : next);
  check(sec.length > 0 && /<a href="#materials">/.test(html), 'materials: the section exists and the table of contents links it');
  const cvs = [...sec.matchAll(/<canvas class="pk-cv" width="(\d+)" height="(\d+)" data-recipe="([^"]+)" data-part="([a-z]+)"/g)];
  check(cvs.length === Object.keys(EXT.recipes).length && cvs.every((m) => m[3] in EXT.recipes && EXT.recipes[m[3]].uses.includes(m[4])
    && (+m[1] & (+m[1] - 1)) === 0 && m[1] === m[2]),
    `materials: one runtime-drawn preview canvas per recipe (${cvs.length}), square power-of-two, part from the recipe uses`);
  check(!/<img[\s>]|\.png|\.jpg|\.webp/i.test(sec), 'materials: previews ship no image file (drawn at runtime)');
  check(html.includes('const PatternKit') && html.includes('PatternKit.load(') && html.includes(EXT.source_stamp),
    'materials: patternkit and the registry data (by source stamp) are inlined');
  const sws = [...sec.matchAll(/<li class="pk-sw" style="background:(#[0-9A-F]{6});color:(#[0-9A-F]{6})"/g)];
  const lets = [...sec.matchAll(/<li class="pk-let" style="background:(#[0-9A-F]{6});color:(#[0-9A-F]{6})"/g)];
  const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  const L = (h) => { const c = [1, 3, 5].map((i) => lin(parseInt(h.slice(i, i + 2), 16))); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
  const cr = (a, b) => { const x = L(a), y = L(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const nCol = Object.values(EXT.colour_families).reduce((a, f) => a + f.colours.length, 0);
  const nLet = Object.values(EXT.colour_families).reduce((a, f) => a + f.lettering.length, 0);
  const worst = Math.min(...[...sws, ...lets].map((m) => cr(m[2], m[1])));
  check(sws.length === nCol && lets.length === nLet && worst >= 4.5,
    `materials: every text pair the section shows (${sws.length} swatches + ${lets.length} lettering) reaches WCAG AA 4.5:1 (worst ${worst.toFixed(2)})`);
  const fams = [...sec.matchAll(/<button type="button" class="pk-f" data-fam="([a-z]*)" aria-pressed="(true|false)"/g)];
  check(fams.length === Object.keys(EXT.colour_families).length + 1 && fams[0][1] === '' && fams[0][2] === 'true'
    && fams.slice(1).every((m) => m[1] in EXT.colour_families) && /role="group"/.test(sec),
    'materials: a category filter (All + every colour category) as a labelled toggle-button group');
  check(sec.includes('<p class="pk-prov">') && sec.includes(en['pattern.provenance']) && /AUTHORED/.test(en['pattern.provenance']) && /Machado 2009/.test(sec) && sec.includes(`dE ${EXT.checks.cvd.min_delta_e}`),
    'materials: honest provenance line (AUTHORED) and the stated CVD method and floor');
  check(['title', 'filter', 'all', 'swatches', 'previews', 'lettering'].every((k) => sec.includes(en['pattern.' + k].replace(/&/g, '&amp;'))),
    'materials: UI strings come from the pattern.* locale keys');
}
console.log(`${oks} checks passed${fails ? `, ${fails} FAILED` : ''}.`);
process.exit(fails ? 1 : 0);
