/** The identity, and the properties that make it usable on every surface. */
import { NAME, FORBIDDEN, TOKENS, TYPE, livery, hallCode, wordmark, markSvg, cssTokens } from './identity.mjs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

let n = 0;
const ok = (label, cond) => { if (!cond) { console.error('FAIL', label); process.exit(1); } n++; console.log('  ok ', label); };

/* --------------------------------------------------------------- naming -- */
ok('the full lockup names the platform, the programme and neither alone',
  NAME.full.includes(NAME.platform) && NAME.full.includes(NAME.programme));
ok('the attribution is lower-case "powered by" with no trailing period',
  NAME.attribution === 'powered by AGI Corp' && !NAME.attribution.endsWith('.'));
ok('no forbidden spelling is its own correction — every rule moves somewhere',
  FORBIDDEN.every((r) => r.wrong !== r.right));
ok('every forbidden spelling carries the reason it is wrong',
  FORBIDDEN.every((r) => r.why && r.why.length > 20));
ok('the canonical name does not itself contain a forbidden spelling',
  FORBIDDEN.every((r) => !NAME.full.includes(r.wrong)));

/* ---------------------------------------------------------------- theme -- */
ok('light and dark declare exactly the same token set — a missing token is an unstyled element',
  JSON.stringify(Object.keys(TOKENS.dark).sort()) === JSON.stringify(Object.keys(TOKENS.light).sort()));
ok('every token is a concrete colour, never a var() reference that could dangle',
  Object.values(TOKENS.dark).concat(Object.values(TOKENS.light)).every((v) => /^#[0-9A-Fa-f]{6}$/.test(v)));

{
  const css = cssTokens();
  ok('the bare :root carries a full palette, so the un-stamped default theme resolves',
    Object.keys(TOKENS.dark).every((k) => css.slice(0, css.indexOf('@media')).includes('--' + k.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase()))));
  ok('an explicit light choice beats a dark OS, and an explicit dark beats a light one',
    css.includes(':root:not([data-theme="dark"])') && css.includes(':root[data-theme="dark"]'));
}

/* -------------------------------------------------------------- contrast - */
const lum = (hex) => {
  const c = hex.replace('#', '').match(/../g).map((h) => parseInt(h, 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

for (const theme of ['dark', 'light']) {
  const t = TOKENS[theme];
  ok(`${theme}: body text clears 4.5:1 on the plate (${ratio(t.ink, t.plate).toFixed(1)}:1)`,
    ratio(t.ink, t.plate) >= 4.5);
  ok(`${theme}: muted text clears 4.5:1 on the plate (${ratio(t.muted, t.plate).toFixed(1)}:1)`,
    ratio(t.muted, t.plate) >= 4.5);
  ok(`${theme}: the accent clears 3:1 on the plate, so signage reads (${ratio(t.mark, t.plate).toFixed(1)}:1)`,
    ratio(t.mark, t.plate) >= 3);
  ok(`${theme}: ink on the accent clears 4.5:1, so a primary button is legible (${ratio(t.markInk, t.mark).toFixed(1)}:1)`,
    ratio(t.markInk, t.mark) >= 4.5);
}

/* -------------------------------------------------------------- livery --- */
{
  const slugs = ['ironworkers', 'electricians', 'welders', 'crane-ops', 'pipefitters',
                 'glaziers', 'roofers', 'millwrights', 'insulators', 'boilermakers'];
  const hues = slugs.map((s) => livery(s).hue);
  ok('livery is deterministic — the same hall is the same colour every load',
    livery('welders').chip === livery('welders').chip && livery('welders').hue === livery('welders').hue);
  ok('no hall lands in the amber wedge the brand accent owns',
    hues.every((h) => !(h > 28 && h < 52)));
  ok('halls are distinguishable: no two of ten share a hue',
    new Set(hues).size === hues.length);
  ok('saturation and lightness are fixed, so no hall shouts louder than another',
    slugs.every((s) => /52% 62%/.test(livery(s, 'dark').chip)));
  ok('a hall code is two upper-case letters, even for a slug full of punctuation',
    hallCode('crane-ops') === 'CR' && /^[A-Z?]{2}$/.test(hallCode('---')));
}

/* --------------------------------------------------------------- marks --- */
ok('the wordmark scales down without losing the platform name',
  wordmark({ scale: 'platform' }).includes('SmartCiti')
  && wordmark({ scale: 'compact' }).includes('Trade Craft Academy')
  && wordmark().includes('powered by AGI Corp'));
ok('only the full lockup carries the attribution — it is a signature, not a tagline',
  !wordmark({ scale: 'compact' }).includes('AGI Corp'));
ok('the mark is geometry with an accessible name, not a fetched image',
  markSvg().includes('<path') && markSvg().includes('role="img"') && !markSvg().includes('<image'));
ok('the mark takes its colour from the surface, so it works on either ground',
  markSvg().includes('currentColor'));

/* ---------------------------------------------------------------- lint --- */
{
  const lint = fileURLToPath(new URL('./lint.mjs', import.meta.url));
  let clean = true;
  try { execFileSync('node', [lint], { encoding: 'utf8' }); } catch { clean = false; }
  ok('the tree currently carries no forbidden spelling', clean);

  const { writeFileSync, rmSync } = await import('node:fs');
  const probe = '/tmp/.brandprobe.md';
  // The probe text is assembled FROM the rule table rather than written out,
  // so this file does not itself contain a forbidden spelling and the lint can
  // scan the whole tree including its own suite.
  writeFileSync(probe, FORBIDDEN.map((r) => r.wrong).join(' and '));
  let caught = false;
  try { execFileSync('node', [lint, probe], { encoding: 'utf8' }); } catch { caught = true; }
  ok('and the lint actually fails when drift is present — a check that cannot fail is not a check',
    caught);
  rmSync(probe, { force: true });

  // The quoted-literal exemption exists so documentation can cite a wrong
  // name. It must not become a way to hide one: prose on the same line as a
  // legitimate citation still has to be checked.
  const mixed = '/tmp/.brandprobe2.md';
  const bad = FORBIDDEN[0].wrong;
  writeFileSync(mixed, 'Welcome to ' + bad + ' — formerly written `' + bad + '`.');
  let mixedCaught = false;
  try { execFileSync('node', [lint, mixed], { encoding: 'utf8' }); } catch { mixedCaught = true; }
  ok('a quoted citation is exempt, but the same name in prose beside it still fails',
    mixedCaught);

  const quoted = '/tmp/.brandprobe3.md';
  writeFileSync(quoted, 'It shipped as `' + bad + '`, which was wrong.');
  let quotedClean = true;
  try { execFileSync('node', [lint, quoted], { encoding: 'utf8' }); } catch { quotedClean = false; }
  ok('a citation on its own passes — documentation can name the mistake it fixed',
    quotedClean);
  rmSync(mixed, { force: true }); rmSync(quoted, { force: true });
}

console.log(`\n${n} checks passed.`);
