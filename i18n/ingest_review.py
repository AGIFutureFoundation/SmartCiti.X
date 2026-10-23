#!/usr/bin/env python3
"""
Take a filled review sheet (CSV) back into the repository.

    python3 i18n/ingest_review.py <sheet.csv> --reviewer "AB" [--locale de] [--date 2026-11-02] [--strict] [--dry-run]
    python3 i18n/ingest_review.py --sync <locale>      # recompute a catalog's status from its ledger

What it does, only if EVERY filled row passes (all or nothing; nothing is written otherwise):
  - verdict "fix": the corrected text replaces the draft in i18n/locales/<locale>.json
  - verdict "ok" or "fix": the key gets an entry in i18n/review/<locale>.ledger.json with
    verdict, reviewed_by (the name or initials given with --reviewer), reviewed_at (the date),
    and the sha256 of the English source and of the final text. An entry counts only while
    both still match, so a later English or text change makes the verdict out of date.
  - translation_status (and reviewer / reviewed_at) are recomputed from the ledger:
        no current verdict   machine-drafted, pending native review
        N of M current       machine-drafted; N of M keys checked by a native speaker, S of P safety and honesty lines
        all M current        reviewed
A key is never marked reviewed without a verdict. A row with no verdict, no corrected text and
no notes is simply untouched. A row with ANY of those but no verdict is refused. --strict also
refuses a return in which some key has neither a verdict in the sheet nor a current one in the ledger.

Refused: unknown key; duplicate key; verdict other than ok/fix; "ok" with corrected text; "fix"
with no corrected text, text equal to the draft, or text equal to the English source; a lost or
invented {placeholder}; changed <tags>; a glossary label (SCRIPTED, AUTHORED, ...) dropped from
a row whose English carries it; a draft/english column that no longer matches the catalog (the
sheet is out of date: rebuild it); a reviewer that is empty, too long, or contains '@' (no email
address is published); a date that is not YYYY-MM-DD or lies in the future.

After a write: the pages embed the catalogs, so run the page builders (rebuild_all) again.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_lib as L  # noqa: E402


EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')


def check_reviewer(name):
    n = (name or '').strip()
    if not n:
        return 'reviewer name or initials is required (--reviewer)'
    if len(n) > 60 or len(n) < 2:
        return 'reviewer must be 2 to 60 characters: a name or initials'
    if '@' in n or re.search(r'https?:|www\.', n):
        return 'reviewer must be a name or initials, not an email address or a link: none is published'
    if re.search(r'[\x00-\x1f]', n):
        return 'reviewer contains control characters'
    return None


def check_date(d, today):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', d or ''):
        return 'date must be YYYY-MM-DD'
    try:
        dt = datetime.date.fromisoformat(d)
    except ValueError:
        return 'date is not a real calendar date'
    if dt > today:
        return 'date lies in the future'
    return None


def check_correction(row, en_t, dr_t, terms):
    """Problems with a "fix" row's corrected text."""
    c = row['corrected'].strip()
    out = []
    if not c:
        return ['verdict fix but no corrected text']
    if row['corrected'][:1] in L.FORMULA_LEADERS or c[:1] in L.FORMULA_LEADERS:
        out.append('corrected text starts with a character a spreadsheet would run as a formula '
                   f'({c[:1]!r}); reword it, the next sheet build would refuse the catalog')
    if re.search(r'[\x00-\x08\x0b-\x1f]', c) or '\n' in c:
        out.append('corrected text contains a line break or control character')
    if L.norm(c) == L.norm(dr_t):
        out.append('corrected text is the same as the draft: use verdict ok')
    if L.norm(c) == L.norm(en_t):
        out.append('corrected text is identical to the English source: a translation that only repeats English '
                   'is refused; if English is the right answer, say so in notes and leave verdict blank')
    if L.placeholders_of(c) != L.placeholders_of(en_t):
        out.append(f'placeholders differ: english has {L.placeholders_of(en_t)}, corrected has {L.placeholders_of(c)}')
    if EMAIL.search(c):
        out.append('corrected text contains an email address: none is published')
    if L.tags_of(c) != L.tags_of(en_t):
        out.append('markup differs: the <tags> must be exactly those of the English text, in the same order')
    for t in terms:
        if re.search(r'\b' + t + r'\b', en_t) and not re.search(r'\b' + t + r'\b', c):
            out.append(f'glossary label {t} is in the English and must stay, in English capitals, in the corrected text')
    return out


def apply(root, locale, rows, reviewer, date, strict, dry):
    rules = L.load_rules(root)
    terms = L.glossary_terms(rules)
    cpath, raw, cat = L.read_catalog(root, locale)
    if L.dump_catalog(cat) != raw:
        return ['catalog is not in canonical formatting (indent 1, UTF-8, trailing newline); refusing to rewrite it'], None
    _, _, en = L.read_catalog(root, 'en')
    en_flat, cat_flat = L.flatten(en), L.flatten(cat)
    if list(en_flat) != list(cat_flat):
        return [f'{locale} does not mirror the English key set; run node i18n/test.mjs'], None
    ledger = L.read_ledger(root, locale)
    errs, seen, plan = [], {}, []
    why = check_reviewer(reviewer)
    if why:
        errs.append(why)
    why = check_date(date, datetime.date.today())
    if why:
        errs.append(why)
    for r in rows:
        key = r['key'].strip()
        if not key:
            if any((r.get(c) or '').strip() for c in L.COLUMNS):
                errs.append('a row with no key')
            continue
        if key in seen:
            errs.append(f'{key}: appears more than once in the sheet')
            continue
        seen[key] = r
        verdict = r['verdict'].strip().lower()
        filled = any(r[c].strip() for c in ('verdict', 'corrected', 'notes'))
        if key not in en_flat:
            errs.append(f'{key}: unknown key (not in the catalog)')
            continue
        if not filled:
            continue
        en_t, dr_t = en_flat[key][1], cat_flat[key][1]
        if L.norm(r['english']) != L.norm(en_t):
            errs.append(f'{key}: english column no longer matches the catalog; the sheet is out of date, rebuild it')
            continue
        if L.norm(r['draft']) != L.norm(dr_t):
            errs.append(f'{key}: draft column no longer matches the catalog; the sheet is out of date, rebuild it')
            continue
        if not verdict:
            errs.append(f'{key}: corrected text or notes given but the verdict is blank; give ok or fix, or clear the row')
            continue
        if verdict not in L.VERDICTS:
            errs.append(f'{key}: verdict {r["verdict"]!r} is not ok or fix')
            continue
        if verdict == 'ok' and r['corrected'].strip():
            errs.append(f'{key}: verdict ok but corrected text given; use fix, or clear the corrected text')
            continue
        final = dr_t
        if verdict == 'fix':
            bad = check_correction(r, en_t, dr_t, terms)
            if bad:
                errs.extend(f'{key}: {b}' for b in bad)
                continue
            final = L.unicodedata.normalize('NFC', r['corrected'].strip())
        note = r['notes'].strip()
        if EMAIL.search(note) or len(note) > 500:
            errs.append(f'{key}: notes contain an email address (none is published) or run past 500 characters')
            continue
        plan.append((key, verdict, final, dr_t, en_t, r['notes'].strip()))
    if strict:
        missing = [k for k in en_flat
                   if (k not in seen or not seen[k]['verdict'].strip())
                   and L.entry_state(ledger['entries'].get(k), en_flat[k][1], cat_flat[k][1]) != 'current']
        if missing:
            errs.append(f'--strict: {len(missing)} key(s) have no verdict, e.g. {missing[0]}')
    if not plan and not errs:
        errs.append('no row carries a verdict: nothing to ingest')
    if errs:
        return errs, None

    for key, verdict, final, was, en_t, notes in plan:
        prev = ledger['entries'].get(key)
        e = {'verdict': verdict, 'reviewed_by': reviewer.strip(), 'reviewed_at': date,
             'en_sha': L.sha(en_t), 'text_sha': L.sha(final)}
        if verdict == 'fix':
            e['was'] = was
        if notes:
            e['notes'] = notes
        if prev:
            hist = list(prev.get('history', []))
            hist.append({k: v for k, v in prev.items() if k != 'history'})
            e['history'] = hist
        ledger['entries'][key] = e
        if verdict == 'fix':
            L.set_leaf(cat, en_flat[key][0], final)
    return [], finish(root, locale, cat, en_flat, ledger, dry)


def finish(root, locale, cat, en_flat, ledger, dry):
    """Recompute status from the ledger and write the catalog and the ledger."""
    cat_flat = L.flatten(cat)
    cur, stale, unknown = L.review_counts(en_flat, cat_flat, ledger)
    if unknown:
        raise L.ReviewError(f'ledger names keys the catalog does not have: {unknown[:5]}')
    s1, p1 = L.p1_counts(en_flat, cat_flat, ledger, L.load_rules(root))
    cat['translation_status'] = L.status_for(cur, len(en_flat), s1, p1)
    who, when = L.reviewer_fields(en_flat, cat_flat, ledger)
    cat.pop('reviewer', None)
    cat.pop('reviewed_at', None)
    if who:
        cat['reviewer'], cat['reviewed_at'] = who, when
    summary = f'{locale}: {cur} of {len(en_flat)} keys have a current verdict' + (f', {stale} out of date' if stale else '')
    if not dry:
        L.ledger_path(root, locale).parent.mkdir(parents=True, exist_ok=True)
        L.ledger_path(root, locale).write_text(L.dump_ledger(ledger), encoding='utf-8')
        (Path(root) / 'i18n' / 'locales' / f'{locale}.json').write_text(L.dump_catalog(cat), encoding='utf-8')
    return summary + f'; translation_status now "{cat["translation_status"]}"'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheet', nargs='?')
    ap.add_argument('--locale')
    ap.add_argument('--reviewer', help='name or initials; if omitted, the sheet\'s "# reviewer: NAME" row is used')
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--sync', metavar='LOCALE')
    ap.add_argument('--root', default=str(L.ROOT))
    a = ap.parse_args()
    root = Path(a.root)
    try:
        if a.sync:
            if a.sheet:
                print('--sync takes no sheet', file=sys.stderr)
                return 2
            _, raw, cat = L.read_catalog(root, a.sync)
            if L.dump_catalog(cat) != raw:
                print('catalog is not in canonical formatting; refusing to rewrite it', file=sys.stderr)
                return 2
            _, _, en = L.read_catalog(root, 'en')
            print(finish(root, a.sync, cat, L.flatten(en), L.read_ledger(root, a.sync), a.dry_run))
            return 0
        if not a.sheet:
            ap.error('give the filled sheet (CSV), or --sync LOCALE')
        data = Path(a.sheet).read_bytes()
        if data[:2] in (b'\xff\xfe', b'\xfe\xff'):
            text = data.decode('utf-16')          # "Unicode text" export
        else:
            try:
                text = data.decode('utf-8-sig')
            except UnicodeDecodeError:
                print('ingest_review: the file is not UTF-8; save the sheet as "CSV UTF-8" and send that', file=sys.stderr)
                return 2
        in_sheet, sheet_reviewer, rows = L.parse_sheet(text)
        locale = a.locale or in_sheet
        if not locale:
            print('the sheet names no locale (#locale= row) and --locale was not given', file=sys.stderr)
            return 2
        if a.locale and in_sheet and a.locale != in_sheet:
            print(f'--locale {a.locale} but the sheet says {in_sheet}', file=sys.stderr)
            return 2
        if locale == 'en' or not (root / 'i18n' / 'locales' / f'{locale}.json').exists():
            print(f'{locale!r} is not a shipped non-source locale', file=sys.stderr)
            return 2
        errs, msg = apply(root, locale, rows, a.reviewer or sheet_reviewer, a.date, a.strict, a.dry_run)
    except (L.ReviewError, OSError, UnicodeDecodeError) as e:
        print(f'ingest_review: {e}', file=sys.stderr)
        return 2
    if errs:
        print(f'ingest_review: refused, nothing written ({len(errs)} problem(s)):', file=sys.stderr)
        for e in errs[:60]:
            print(f'  - {e}', file=sys.stderr)
        if len(errs) > 60:
            print(f'  ... and {len(errs) - 60} more', file=sys.stderr)
        return 1
    print(('dry run, nothing written: ' if a.dry_run else '') + msg)
    if not a.dry_run:
        print('next: run the page builders again (the pages embed the catalogs), then node i18n/test_review.mjs')
    return 0


if __name__ == '__main__':
    sys.exit(main())
