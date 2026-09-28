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
const vid = html.match(/<video([^>]*)>([\s\S]*?)<\/video>/);
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

console.log(`${oks} checks passed${fails ? `, ${fails} FAILED` : ''}.`);
process.exit(fails ? 1 : 0);
