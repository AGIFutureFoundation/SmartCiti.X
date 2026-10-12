/**
 * The honesty scanner, shared by EV-05 (loop/evals.mjs) and courses/test.mjs.
 * courses/build.py implements the same rules in Python over the same
 * vocabulary (loop/honesty.json); courses/test.mjs proves both give identical
 * verdicts on loop/registry/honesty_fixtures.json.
 *
 * Rules:
 *  1. Fenced blocks and `code spans` are quoting, not claiming; they are
 *     blanked, keeping newlines so line numbers stay right.
 *  2. Abbreviations (e.g., i.e., Art. 5, No. 5) become a placeholder that is
 *     neither a word nor a sentence end, so "No. 4765" is not a negation.
 *  3. Text splits into clauses on . ! ? ; (before whitespace), on ", " before
 *     "but"/"not", and on hard line breaks. A line break is soft (the
 *     sentence continues) only when the line ends in a word character, comma,
 *     ")" or ":" and the next line starts with a letter, "(" or "`".
 *  4. A claim is negated only by a negation that occurs EARLIER in its clause:
 *     "accredited by ACME, not endorsed" is a claim; "planned" after a claim
 *     does not excuse it.
 *  5. A claim that is a member of a regex alternation ("accredited|endorsed")
 *     is a rule table naming what a lint hunts, not a claim. Membership means
 *     the claim touches a TIGHT pipe, one with a non-space character on both
 *     sides; "the program is |accredited| by the board" has no tight pipe and
 *     is a claim.
 */
import { readFileSync } from 'node:fs';

export const VOCAB = JSON.parse(readFileSync(new URL('./honesty.json', import.meta.url), 'utf8'));
const CLAIM = new RegExp(VOCAB.claims.join('|'), 'gi');
const NEG = new RegExp(VOCAB.negations.join('|'), 'gi');
const ABBR = new RegExp(VOCAB.abbreviations.join('|'), 'g');
export const PLACEHOLDER = '§§';
const BREAK = /[.!?;](?=\s|$)|,\s+(?=(?:but|not)\b)|\n/gi;

/** Blank code fences (keeping newlines) and code spans; replace abbreviations. */
export function prepare(text) {
  return text
    .replace(/```[\s\S]*?```/g, (m) => m.replace(/[^\n]/g, ''))
    .replace(/`[^`\n]*`/g, ' ')
    .replace(ABBR, PLACEHOLDER);
}

function softWrap(t, i) {
  const prev = t.slice(t.lastIndexOf('\n', i - 1) + 1, i).trimEnd();
  let j = t.indexOf('\n', i + 1); if (j < 0) j = t.length;
  const next = t.slice(i + 1, j).trimStart();
  return /[\w,):]$/.test(prev) && /^[A-Za-z(`]/.test(next);
}

/** Clauses of prepared text, each {start, text}. */
export function clauses(t) {
  const out = []; let start = 0;
  for (const m of t.matchAll(BREAK)) {
    if (m[0] === '\n' && softWrap(t, m.index)) continue;
    const end = m.index + m[0].length;
    out.push({ start, text: t.slice(start, end) }); start = end;
  }
  out.push({ start, text: t.slice(start) });
  return out.filter((c) => c.text.trim());
}

// A tight pipe has a non-space, non-pipe character on both sides: "a|b".
const tight = (c, i) => c[i] === '|' && /[^\s|]/.test(c[i - 1] ?? '') && /[^\s|]/.test(c[i + 1] ?? '');

/** True when the claim at [s,e) is a member of a regex alternation (touches a tight pipe). */
const inAlternation = (c, s, e) => tight(c, s - 1) || tight(c, e);

/** Unnegated, unexempt claims in one clause: the first one's index, or -1. */
export function clauseClaim(c) {
  const negs = [...c.matchAll(NEG)].map((m) => m.index);
  for (const m of c.matchAll(CLAIM)) {
    if (negs.some((i) => i < m.index)) continue;
    if (inAlternation(c, m.index, m.index + m[0].length)) continue;
    return m.index;
  }
  return -1;
}

/** Overclaiming clauses in a text: [{line, text}]. */
export function claimHits(text) {
  const t = prepare(text);
  const hits = [];
  for (const cl of clauses(t)) {
    const k = clauseClaim(cl.text);
    if (k < 0) continue;
    const at = cl.start + k;
    const line = t.slice(0, at).split('\n').length;
    hits.push({ line, text: cl.text.replace(/\s+/g, ' ').trim().slice(0, 120) });
  }
  return hits;
}

/** 'flag' | 'clean' — the verdict the fixture corpus records. */
export const verdict = (text) => (claimHits(text).length ? 'flag' : 'clean');
