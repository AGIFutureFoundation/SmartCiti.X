"""
Shared rules for the native-speaker review loop: flatten a locale catalog into
reviewable rows, derive each row's priority from i18n/review_rules.json, read
and write the per-locale review ledger, and decide what a catalog's
translation_status must say.

Used by i18n/build_review.py (writes the sheets) and i18n/ingest_review.py
(takes a filled sheet back). i18n/test_review.mjs holds both to the same
contract from the JavaScript side.

The status is derived, never typed: it is "machine-drafted, pending native
review" until a native speaker has given a verdict on at least one key, then
"machine-drafted; N of M keys checked by a native speaker, S of P safety and honesty
lines" (S of the P priority-1 keys), then "reviewed"
only when every key has a current verdict. (The partial wording avoids the
substring "reviewed" on purpose: rnd/ counts a catalog as a reviewed locale
when its status contains that word, and a part-reviewed catalog is not one.)
"""
import csv
import hashlib
import io
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

PENDING = 'machine-drafted, pending native review'
SOURCE = 'source language'
REVIEWED = 'reviewed'
PARTIAL_RE = re.compile(r'^machine-drafted; (\d+) of (\d+) keys checked by a native speaker, (\d+) of (\d+) safety and honesty lines$')

META_FIELDS = ('locale', 'language', 'english_name', 'dir', 'translation_status', 'reviewer', 'reviewed_at')
COLUMNS = ['key', 'english', 'draft', 'appears_in', 'priority', 'why', 'status',
           'verdict', 'corrected', 'notes']
VERDICTS = ('ok', 'fix')
FORMULA_LEADERS = '=+-@\t\r'


class ReviewError(Exception):
    pass


# ----------------------------------------------------------------- text ---
def norm(s):
    """Comparison form: NFC, HTML entities left alone, whitespace collapsed."""
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', s)).strip()


def sha(s):
    return hashlib.sha256(unicodedata.normalize('NFC', s).encode('utf-8')).hexdigest()


def tags_of(s):
    return re.findall(r'<[^>]+>', s)


def placeholders_of(s):
    return sorted(re.findall(r'\{\w+\}', s))


def word_count(s):
    return len(re.findall(r'\S+', re.sub(r'<[^>]+>', ' ', s)))


# ------------------------------------------------------------- catalogs ---
def flatten(cat):
    """{row id: (path tuple, text)} in catalog order. strings.* keys keep their own dots."""
    out = {}

    def walk(node, path, ident):
        if isinstance(node, dict):
            for k, v in node.items():
                if not path and k in META_FIELDS:
                    continue
                if path == ('strings',):
                    walk(v, path + (k,), f'strings.{k}')
                else:
                    walk(v, path + (k,), f'{ident}.{k}' if ident else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + (i,), f'{ident}.{i}')
        elif isinstance(node, str):
            out[ident] = (path, node)
        else:
            raise ReviewError(f'catalog value at {ident} is {type(node).__name__}, not text')

    walk(cat, (), '')
    return out


def set_leaf(cat, path, text):
    cur = cat
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = text


def dump_catalog(cat):
    return json.dumps(cat, indent=1, ensure_ascii=False) + '\n'


def read_catalog(root, locale):
    p = Path(root) / 'i18n' / 'locales' / f'{locale}.json'
    raw = p.read_text(encoding='utf-8')
    return p, raw, json.loads(raw)


def locales_of(root):
    return sorted(p.stem for p in (Path(root) / 'i18n' / 'locales').glob('*.json'))


# ---------------------------------------------------------------- rules ---
def load_rules(root=ROOT):
    return json.loads((Path(root) / 'i18n' / 'review_rules.json').read_text(encoding='utf-8'))


def _flags(f):
    return re.I if 'i' in f else 0


def priority_of(key, english, rules):
    """(priority 1|2|3, rule id). The first matching rule wins."""
    segs = key.split('.')
    n = word_count(english)
    if segs[0] in rules['p2_sections']:
        return 2, f'section:{segs[0]}'
    for s in segs:
        if s in rules['p1_key_segments']:
            return 1, f'key:{s}'
        if s in rules['p1_key_segments_sentences_only'] and n >= rules['p1_key_sentence_min_words']:
            return 1, f'key:{s}'
    for r in rules['p1_text_rules']:
        if n >= r['min_words'] and re.search(r['pattern'], english, _flags(r['flags'])):
            return 1, f'text:{r["id"]}'
    if segs[0] == 'strings' and len(segs) > 1 and segs[1] in rules['p2_prefixes']:
        return 2, f'prefix:{segs[1]}'
    if n <= rules['p2_short_label_max_words'] and not re.search(rules['p2_sentence_punctuation'], english):
        return 2, 'short_label'
    return 3, 'page_copy'


def glossary_terms(rules):
    return [g['term'] for g in rules['glossary']]


# --------------------------------------------------------------- ledger ---
def ledger_path(root, locale):
    return Path(root) / 'i18n' / 'review' / f'{locale}.ledger.json'


def read_ledger(root, locale):
    p = ledger_path(root, locale)
    if not p.exists():
        return {'locale': locale, 'schema': 1, 'entries': {}}
    d = json.loads(p.read_text(encoding='utf-8'))
    if d.get('locale') != locale or d.get('schema') != 1 or not isinstance(d.get('entries'), dict):
        raise ReviewError(f'{p}: not a schema-1 ledger for {locale}')
    return d


def dump_ledger(led):
    return json.dumps(led, indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def entry_state(entry, en_text, cur_text):
    """'current' only while neither the English source nor the reviewed text has moved."""
    if entry is None:
        return 'none'
    if entry.get('en_sha') != sha(en_text):
        return 'stale-english'
    if entry.get('text_sha') != sha(cur_text):
        return 'stale-text'
    return 'current'


def review_counts(en_flat, cat_flat, ledger):
    """(current verdicts, stale verdicts, unknown ledger keys)."""
    cur = stale = 0
    for k, (_, en_t) in en_flat.items():
        e = ledger['entries'].get(k)
        st = entry_state(e, en_t, cat_flat[k][1])
        if st == 'current':
            cur += 1
        elif st != 'none':
            stale += 1
    unknown = sorted(set(ledger['entries']) - set(en_flat))
    return cur, stale, unknown


def p1_counts(en_flat, cat_flat, ledger, rules):
    """(safety and honesty keys with a current verdict, all safety and honesty keys)."""
    done = total = 0
    for k, (_, en_t) in en_flat.items():
        if priority_of(k, en_t, rules)[0] != 1:
            continue
        total += 1
        if entry_state(ledger['entries'].get(k), en_t, cat_flat[k][1]) == 'current':
            done += 1
    return done, total


def status_for(current, total, p1_done, p1_total):
    if current <= 0:
        return PENDING
    if current >= total:
        return REVIEWED
    return (f'machine-drafted; {current} of {total} keys checked by a native speaker, '
            f'{p1_done} of {p1_total} safety and honesty lines')


def reviewer_fields(en_flat, cat_flat, ledger):
    """(reviewers joined, latest date) over the current verdicts, or (None, None)."""
    names, dates = set(), []
    for k, (_, en_t) in en_flat.items():
        e = ledger['entries'].get(k)
        if entry_state(e, en_t, cat_flat[k][1]) == 'current':
            names.add(e['reviewed_by'])
            dates.append(e['reviewed_at'])
    if not names:
        return None, None
    return ', '.join(sorted(names)), max(dates)


# ------------------------------------------------------------------ csv ---
def csv_text(rows, header_lines):
    buf = io.StringIO(newline='')
    w = csv.writer(buf, lineterminator='\r\n')
    for h in header_lines:
        w.writerow([h])
    w.writerow(COLUMNS)
    for r in rows:
        w.writerow([r[c] for c in COLUMNS])
    return buf.getvalue()


def parse_sheet(text):
    """(locale, reviewer, rows): rows as dicts; locale from a '#locale=' row and reviewer from a
    '# reviewer: NAME' row when the sheet carries them (else None).

    Rows above the header and any row whose first cell starts with '#' are
    instructions and are skipped. A UTF-8 BOM is tolerated. Columns are found
    by name, so a reviewer who re-orders, sorts or filters loses nothing. A semicolon- or
    tab-separated file (what some spreadsheets save) is read too.
    """
    if text.startswith('\ufeff'):
        text = text[1:]
    delim = ','
    for line in text.splitlines():
        if re.match(r'^"?key"?[,;\t]"?english"?', line.strip().lower()):
            # a spreadsheet in a locale that writes a decimal comma saves ";"; text export uses a tab
            for d in (';', '\t'):
                if line.count(d) >= len(COLUMNS) - 1 and line.count(',') < len(COLUMNS) - 1:
                    delim = d
            break
    rows = list(csv.reader(io.StringIO(text, newline=''), delimiter=delim))
    locale = None
    reviewer = None
    header = None
    out = []
    for r in rows:
        if not r or all(not c.strip() for c in r):
            continue
        if header is None:
            first = r[0].strip()
            m = re.match(r'^#\s*locale\s*=\s*([A-Za-z-]+)\s*$', first)
            if m:
                locale = m.group(1)
                continue
            m = re.match(r'^#\s*reviewer\s*:\s*(.*)$', first)
            if m and m.group(1).strip() and not m.group(1).strip().startswith('('):
                reviewer = m.group(1).strip()
                continue
            if first.startswith('#'):
                continue
            header = [c.strip().lower() for c in r]
            missing = [c for c in COLUMNS if c not in header]
            if missing:
                raise ReviewError(f'sheet header lacks column(s): {", ".join(missing)}')
            continue
        if r[0].strip().startswith('#'):
            continue
        if len(r) > len(header):
            raise ReviewError(f'row {r[0]!r} has {len(r)} cells, the header has {len(header)}')
        r = r + [''] * (len(header) - len(r))
        out.append(dict(zip(header, r)))
    if header is None:
        raise ReviewError('no header row (key, english, draft, ...) found in the sheet')
    return locale, reviewer, out
