/**
 * SmartCiti.X : Trade Craft Academy — the canonical identity.
 *
 * One declaration, consumed by every surface. This file exists because the
 * identity had already drifted across surfaces that were built weeks apart:
 * the Academy app shipped as "SmartCity.X · Trade Quest Academy" while the
 * landing page said "SmartCiti.X : Trade Craft Academy", and each surface had
 * hand-rolled its own palette. Two spellings of a product name is the same
 * defect as two copies of a source list (v2.6 defect 12) — a second
 * declaration of one truth will always eventually disagree with the first.
 *
 * `brand/lint.mjs` enforces this file against the tree.
 */

export const NAME = Object.freeze({
  /** The product, written out. Never abbreviate in a title or a header. */
  full: 'SmartCiti.X : Trade Craft Academy',
  /** The platform alone, e.g. in a nav bar too narrow for the full lockup. */
  platform: 'SmartCiti.X',
  /** The programme alone, after the platform has been established on the page. */
  programme: 'Trade Craft Academy',
  /** Always present under the lockup. Lower-case "powered by" is deliberate. */
  attribution: 'powered by AGI Corp',
  /** The publisher. The Academy is a programme OF the Foundation. */
  publisher: 'AGI Future Foundation',
  /** Machine-safe forms. */
  slug: 'smartcitix-trade-craft-academy',
  domain: 'agifuturefoundation.org',
  contact: 'x@agifuturefoundation.org',
});

/**
 * Spellings that must never appear. Each carries the correct form and the
 * reason, so a lint failure teaches rather than just refuses.
 */
export const FORBIDDEN = Object.freeze([
  { wrong: 'SmartCity.X',  right: 'SmartCiti.X',
    why: 'the platform is SmartCiti.X — "Citi", not "City". The i is the mark.' },
  { wrong: 'SmartCityX',   right: 'SmartCiti.X',
    why: 'the "City" misspelling again, and the dot before the X is part of the name' },
  { wrong: 'Trade Quest Academy', right: 'Trade Craft Academy',
    why: 'the programme is Trade Craft Academy; "Quest" was an early working name' },
  { wrong: 'StoneByte',    right: 'SmartCiti.X',
    why: 'the pre-rebrand name; it must not survive anywhere' },
  { wrong: 'Stone Byte',   right: 'SmartCiti.X',
    why: 'the pre-rebrand name written as two words; it must not survive either' },
  { wrong: 'AGI Corp.',    right: 'AGI Corp',
    why: 'no trailing period — it reads as a sentence end in the lockup' },
]);

/* ------------------------------------------------------------- palette ---- */

/**
 * Two grounds, one accent family.
 *
 * `mark` (amber) is the brand accent and the only colour allowed to carry the
 * identity — signage, the wordmark dot, primary actions. `steel` is the
 * secondary, for links, wayfinding and anything the eye should follow but not
 * act on. Semantic colours are a separate family and never stand in for the
 * accent: a green "live" pill is state, not brand.
 */
export const TOKENS = Object.freeze({
  dark: {
    plate: '#12181B', panel: '#182023', sunk: '#0C1113',
    ink: '#E8EDEC', muted: '#93A3A6', rule: '#28353A',
    mark: '#E8A33D', markInk: '#12181B',
    steel: '#41C4D4', steelInk: '#7FDCE8',
    good: '#5CB584', warn: '#E8A33D', crit: '#E07C68',
  },
  light: {
    plate: '#F1F4F3', panel: '#FFFFFF', sunk: '#E4EAE9',
    ink: '#141D20', muted: '#54646A', rule: '#CBD6D6',
    // #B0730C was the amber this palette shipped with; white on it is 4.0:1,
    // so every primary button in the light theme failed AA. Darkened along the
    // same hue (37.7 deg) and saturation until white clears 4.7:1 — the hue is
    // the brand, the lightness was never load-bearing.
    mark: '#9F680B', markInk: '#FFFFFF',
    steel: '#0A7E8C', steelInk: '#065A66',
    good: '#2C7A50', warn: '#9A6408', crit: '#A8432F',
  },
});

export const TYPE = Object.freeze({
  display: `"Barlow Condensed", "Archivo Narrow", system-ui, sans-serif`,
  body: `"IBM Plex Sans", system-ui, -apple-system, sans-serif`,
  mono: `"IBM Plex Mono", ui-monospace, "SF Mono", monospace`,
  googleHref: 'https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700'
    + '&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap',
});

/** The one signage motif: a hazard-stripe rule. Used sparingly, never as fill. */
export const MOTIF = Object.freeze({
  rule: (mark = 'var(--mark)') =>
    `repeating-linear-gradient(135deg, ${mark} 0 14px, transparent 14px 28px)`,
});

/* ------------------------------------------------------------ the mark ---- */

/**
 * The wordmark, as markup rather than an image, so it inherits the page's type
 * and theme and stays legible at any size.
 *
 * @param {object} opts
 *   scale — 'full' (lockup with attribution), 'compact' (no attribution),
 *           'platform' (SmartCiti.X alone, for tight navs)
 */
export function wordmark({ scale = 'full', sub = null } = {}) {
  const dot = `<span class="bx-dot">.X</span>`;
  const plat = `SmartCiti${dot}`;
  if (scale === 'platform') return `<span class="bx-name">${plat}</span>`;
  const line = `<span class="bx-name">${plat}<span class="bx-sep">:</span>${NAME.programme}</span>`;
  if (scale === 'compact') return line;
  return `${line}<span class="bx-attr">${sub ?? NAME.attribution}</span>`;
}

/**
 * The plate mark: a hard hat over a level, drawn as geometry rather than
 * fetched, so it survives the artifact CSP and every export path.
 * Currency is deliberate — it reads at 20px in a nav and at 200px on a sign.
 */
export function markSvg({ size = 32, title = NAME.platform } = {}) {
  return `<svg class="bx-mark" width="${size}" height="${size}" viewBox="0 0 48 48" role="img" aria-label="${title}">
  <path d="M6 30 A18 18 0 0 1 42 30" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
  <path d="M24 12 L24 4" stroke="currentColor" stroke-width="3.2" stroke-linecap="round"/>
  <rect x="4" y="30" width="40" height="6" rx="3" fill="currentColor"/>
  <circle cx="24" cy="33" r="1.9" fill="var(--plate, #12181B)"/>
  <path d="M17 33 L31 33" stroke="var(--plate, #12181B)" stroke-width="1" opacity=".55"/>
</svg>`;
}

/** The CSS the wordmark needs. Scoped to bx- so it drops into any surface. */
export const MARK_CSS = `
.bx-lockup{display:inline-flex;align-items:center;gap:10px;text-decoration:none;color:inherit}
.bx-lockup .bx-mark{flex:0 0 auto;color:var(--mark)}
.bx-text{display:grid;line-height:1}
.bx-name{font-family:${TYPE.display};font-weight:700;text-transform:uppercase;
  letter-spacing:.02em;font-size:1.15em;white-space:nowrap}
.bx-name .bx-dot{color:var(--steel)}
.bx-name .bx-sep{color:var(--mark);padding:0 .3em}
.bx-attr{font-family:${TYPE.mono};font-size:.62em;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted);margin-top:.45em}
`;

/* ------------------------------------------------------------- livery ----- */

/**
 * Every union hall gets a stable colour, derived from its slug rather than
 * assigned by hand — 33 hand-picked hues drift the moment a 34th hall opens,
 * and the Academy is already at 111. Hue is spread by hash; saturation and
 * lightness are FIXED so no hall can be louder than another, and both values
 * are chosen to clear 4.5:1 against the plate in their own theme.
 */
export function livery(slug, theme = 'dark') {
  let h = 0;
  for (let i = 0; i < String(slug).length; i++) h = (h * 31 + String(slug).charCodeAt(i)) % 360;
  // Skip the amber wedge the brand accent owns, so no hall impersonates the mark.
  if (h > 28 && h < 52) h = (h + 46) % 360;
  return theme === 'dark'
    ? { hue: h, chip: `hsl(${h} 52% 62%)`, ink: `hsl(${h} 45% 88%)`, sunk: `hsl(${h} 30% 18%)` }
    : { hue: h, chip: `hsl(${h} 46% 38%)`, ink: `hsl(${h} 55% 24%)`, sunk: `hsl(${h} 40% 92%)` };
}

/** Two-letter hall code for a marker, deterministic from the slug. */
export function hallCode(slug) {
  const s = String(slug).replace(/[^a-z]/gi, '');
  return (s.slice(0, 2) || '??').toUpperCase();
}

/** The tokens as a CSS block, in the three-state theme structure. */
export function cssTokens() {
  const decl = (o) => Object.entries(o)
    .map(([k, v]) => `--${k.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase())}:${v}`).join(';');
  return `:root{${decl(TOKENS.dark)};color-scheme:dark light}
@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){${decl(TOKENS.light)}}}
:root[data-theme="light"]{${decl(TOKENS.light)}}
:root[data-theme="dark"]{${decl(TOKENS.dark)}}`;
}
