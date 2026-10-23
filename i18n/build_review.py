#!/usr/bin/env python3
"""
Native-speaker review sheets for the seven machine-drafted locales.

For every non-source locale this writes, to dist/review/ (gitignored):

    <locale>.csv    UTF-8 with a BOM so spreadsheets open it; instruction and
                    glossary rows first (their first cell starts with '#'), then
                    the header row and one row per catalog key
    <locale>.html   the same rows as a page a reviewer can fill in a browser and
                    download as the same CSV (dir="rtl" for Arabic)

and writes one small committed file, i18n/review/summary.json (counts per
locale, the source_stamp), which --check recomputes.

Why dist/ and not the repository: a sheet is a view of the catalogs, the built
pages and the ledger, and goes stale the moment any of them changes; at
1,600+ rows x 7 locales it is also ~10 MB of text. What must survive is the
reviewer's verdict, and that lives in the committed ledgers
(i18n/review/<locale>.ledger.json) and in the catalogs. Regenerate a sheet any
time with `python3 i18n/build_review.py`.

Row columns: key, english, draft, appears_in, priority, why, status, verdict,
corrected, notes. appears_in is DERIVED, not guessed:
  pages  - every built page that either ships the key in an embedded catalogue
           or renders the English text exactly (text node, attribute or string);
  code   - every non-test source file that names the key as a literal, or as a
           dynamic prefix/template (marked "dynamic").
A key neither found says so in words; it is not given a guess.

Every file the build reads goes through Observed.read, and the source_stamp
is the sha256 over all of them, so no input can be left out of the stamp.

usage: python3 i18n/build_review.py [--check] [--out DIR] [--no-summary] [--root DIR]
"""
import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_lib as L  # noqa: E402


# ---------------------------------------------------------------- inputs ---
class Observed:
    """Every read of the build, recorded; the stamp is computed from this set."""

    def __init__(self, root):
        self.root = Path(root)
        self.seen = {}

    def read(self, rel):
        rel = str(rel)
        if rel not in self.seen:
            self.seen[rel] = (self.root / rel).read_bytes()
        return self.seen[rel]

    def text(self, rel):
        return self.read(rel).decode('utf-8', errors='replace')

    def listing(self, pattern, skip=()):
        """Glob under root; the file *names* are inputs too, so each file is read (hashed)."""
        out = []
        for p in sorted(self.root.glob(pattern)):
            rel = p.relative_to(self.root).as_posix()
            if p.is_file() and not any(rel.startswith(s) or f'/{s}' in f'/{rel}' for s in skip):
                out.append(rel)
        return out

    def stamp(self):
        h = hashlib.sha256()
        for rel in sorted(self.seen):
            h.update(rel.encode() + b'\0' + hashlib.sha256(self.seen[rel]).digest())
        return h.hexdigest()


SKIP_DIRS = ('dist/', 'node_modules/', '.git/', '__pycache__/', 'archive/')
TEST_NAME = re.compile(r'(^|/)(test[^/]*|verify[^/]*|eval[^/]*|lint[^/]*|probe[^/]*|fuzz[^/]*|soak[^/]*|rehearsal[^/]*)\.(mjs|js|py)$')


def source_files(obs):
    out = []
    for ext in ('py', 'mjs', 'js'):
        for rel in obs.listing(f'**/*.{ext}'):
            if any(rel.startswith(s) or f'/{s}' in f'/{rel}' for s in SKIP_DIRS):
                continue
            if rel.startswith('i18n/') or rel.startswith('tools/landing/') or TEST_NAME.search(rel):
                continue
            out.append(rel)
    return out


def page_files(obs):
    return [r for r in obs.listing('**/*.html')
            if not any(r.startswith(s) or f'/{s}' in f'/{r}' for s in SKIP_DIRS)]


def page_label(rel):
    s = rel[:-5] if rel.endswith('.html') else rel
    return s[len('web/trade_craft_'):] if s.startswith('web/trade_craft_') else s


# ------------------------------------------------------- where it appears ---
STR_LIT = re.compile(r"""'((?:[^'\\\n]|\\.){1,400})'|"((?:[^"\\\n]|\\.){1,400})\"""")
KEYISH = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.\-]*$')


def norm_text(s):
    s = html.unescape(s).replace(' ', ' ')
    return L.norm(s)


def unjs(s):
    s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
    return s.replace("\\'", "'").replace('\\"', '"').replace('\\/', '/').replace('\\n', ' ')


USAGE = re.compile(r"""(['"])([A-Za-z0-9_][A-Za-z0-9_.\-]*)\1(?!\s*:)""")


def page_index(raw):
    """What one built page says about catalog keys.

    cat    - key tokens that appear as a JSON/object key (an embedded catalogue entry)
    usage  - key-shaped quoted tokens NOT followed by ':' (tr('k'), data-i18n="k", a key list)
    nodes  - normalised text nodes and attribute values (what the markup renders)
    lits   - normalised JS/JSON string literals (rendered at run time, or catalogue values)
    """
    cat = set(m.group(1) for m in re.finditer(r'"([A-Za-z0-9_][A-Za-z0-9_.\-]*)"\s*:', raw))
    usage = set(m.group(2) for m in USAGE.finditer(raw))
    nodes, lits = set(), set()
    for m in re.finditer(r'>([^<>]{1,2000})<', raw):
        nodes.add(norm_text(m.group(1)))
    for m in re.finditer(r'="([^"]{1,2000})"', raw):
        nodes.add(norm_text(m.group(1)))
    for m in STR_LIT.finditer(raw):
        lits.add(norm_text(unjs(m.group(1) if m.group(1) is not None else m.group(2))))
    nodes.discard('')
    lits.discard('')
    return {'cat': cat, 'usage': usage, 'nodes': nodes, 'lits': lits}


BULK_SHARE = 0.9


def source_index(text):
    """(exact key-ish literals, dynamic prefixes, dynamic templates) named in one source file."""
    exact, prefixes, templates = set(), set(), set()
    for m in STR_LIT.finditer(text):
        s = m.group(1) if m.group(1) is not None else m.group(2)
        if '{' in s or '$' in s:
            t = re.sub(r'\$?\{[^{}]*\}', '\0', s)
            lead = t.split('\0')[0]
            if ('\0' in t and re.fullmatch(r'[A-Za-z0-9_.\-\0]+', t) and len(lead) >= 3
                    and len(t.replace('\0', '')) >= 8 and '.' in lead + t):
                templates.add(t)
            continue
        if not KEYISH.match(s) or '.' not in s:
            continue
        if s.endswith('.'):
            if s.count('.') >= 2 and len(s) >= 5:
                prefixes.add(s)
        else:
            exact.add(s)
    return exact, prefixes, templates


def derive_where(obs, ids, en_flat):
    pages = page_files(obs)
    srcs = source_files(obs)
    raws = {p: obs.text(p) for p in pages}
    pidx = {p: page_index(raws[p]) for p in pages}
    all_tokens = {k[len('strings.'):] for k in en_flat if k.startswith('strings.')}
    # a page that embeds (nearly) the whole catalogue says nothing by shipping a key: it is
    # listed for a key only where it uses the key or renders its text in the markup
    bulk = {p for p in pages if len(pidx[p]['cat'] & all_tokens) >= BULK_SHARE * len(all_tokens)}
    sidx = {s: source_index(obs.text(s)) for s in srcs}
    tpl = []
    for s, (_, _, templates) in sidx.items():
        for t in templates:
            rx = re.compile('^' + '[A-Za-z0-9_\\-]+'.join(re.escape(x) for x in t.split('\0')) + '$')
            tpl.append((rx, s))
    where = {}
    for kid in ids:
        path, en_text = en_flat[kid]
        token = kid[len('strings.'):] if kid.startswith('strings.') else None
        en_n = norm_text(en_text)
        has_markup = '<' in en_text
        # a text with {placeholders} is rendered with values filled in: match its longest fixed run
        frag = ''
        if re.search(r'\{\w+\}', en_text):
            frag = max((norm_text(x) for x in re.split(r'\{\w+\}', en_text)), key=len, default='')
            frag = frag if len(frag) >= 12 else ''
        hit_pages = []
        for p in pages:
            ix = pidx[p]
            if p in bulk:
                hit = (token is not None and token in ix['usage']) or (en_n and en_n in ix['nodes'])
            else:
                hit = ((token is not None and (token in ix['cat'] or token in ix['usage']))
                       or (en_n and (en_n in ix['nodes'] or en_n in ix['lits'])))
            if not hit and frag and p not in bulk and frag in raws[p]:
                hit = True
            if hit:
                hit_pages.append(page_label(p))
            elif has_markup and en_n and len(en_n) >= 20 and en_text in raws[p]:
                hit_pages.append(page_label(p))
        code_exact, code_dyn = [], []
        if token is not None:
            for s in srcs:
                ex, pre, _ = sidx[s]
                if token in ex:
                    code_exact.append(s)
                elif any(token.startswith(x) for x in pre):
                    code_dyn.append(s)
            for rx, s in tpl:
                if rx.match(token) and s not in code_exact and s not in code_dyn:
                    code_dyn.append(s)
        where[kid] = {'pages': sorted(set(hit_pages)), 'code': sorted(code_exact), 'dynamic': sorted(code_dyn)}
    return where, sorted(page_label(p) for p in bulk)


def where_text(w, cap=8):
    parts = []
    if w['pages']:
        extra = f' +{len(w["pages"]) - cap} more' if len(w['pages']) > cap else ''
        parts.append('pages: ' + ', '.join(w['pages'][:cap]) + extra)
    code = w['code'] + [f'{c} (dynamic)' for c in w['dynamic'] if c not in w['code']]
    if code:
        extra = f' +{len(code) - 4} more' if len(code) > 4 else ''
        parts.append('code: ' + ', '.join(code[:4]) + extra)
    if not parts:
        return 'not found in any built page or builder source (unused, or built from a name this scan cannot see)'
    return ' | '.join(parts)


# ------------------------------------------------------------------ rows ---
GLOSSARY_NOTE = ('These labels stay in English, in capitals, exactly as written; translate the sentence '
                 'around them, not the label.')


def status_cell(entry, en_text, cur_text):
    st = L.entry_state(entry, en_text, cur_text)
    if st == 'none':
        return 'not reviewed'
    if st == 'current':
        return f'{entry["verdict"]} by {entry["reviewed_by"]} on {entry["reviewed_at"]}'
    why = 'the English source changed' if st == 'stale-english' else 'the text changed'
    return f'review out of date ({why} since {entry["reviewed_by"]} on {entry["reviewed_at"]})'


def build_rows(locale, en_flat, cat_flat, where, rules, ledger):
    rows = []
    for order, kid in enumerate(en_flat):
        en_t = en_flat[kid][1]
        dr = cat_flat[kid][1]
        pr, why = L.priority_of(kid, en_t, rules)
        for label, v in (('english', en_t), ('draft', dr)):
            if v[:1] in L.FORMULA_LEADERS:
                raise SystemExit(f'build_review: {locale} {kid}: {label} text starts with {v[:1]!r}, which a '
                                 'spreadsheet would run as a formula; reword the key before sheets can be built')
        rows.append({
            'key': kid, 'english': en_t, 'draft': dr, 'appears_in': where_text(where[kid]),
            'priority': pr, 'why': why, 'status': status_cell(ledger['entries'].get(kid), en_t, dr),
            'verdict': '', 'corrected': '', 'notes': '', '_order': order,
        })
    rows.sort(key=lambda r: (r['priority'], r['_order']))
    return rows


def instructions(locale, cat, rules, stamp, counts):
    lang = f'{cat["language"]} ({cat["english_name"]})'
    return [
        f'#locale={locale}',
        f'# SmartCiti.X translation review sheet: {lang}. Source language: English. Source stamp {stamp[:12]}.',
        f'# {counts["keys"]} rows. Priority 1 = safety and honesty lines ({counts["p1"]} rows): do these first. '
        f'Priority 2 = interface labels and vocabulary ({counts["p2"]}). Priority 3 = page copy ({counts["p3"]}).',
        '# Every draft was produced by machine and has not been read by a native speaker. You are the first human check.',
        '# For each row you have time for, read english and draft, then fill verdict: ok (the draft is correct and natural) or fix.',
        '# If verdict is fix, write the full replacement sentence in corrected. Leave verdict, corrected and notes blank on rows you skip: a blank row is simply not reviewed. A row with corrected text or notes must also have a verdict.',
        '# Keep every {placeholder} such as {n} and every <tag> exactly as in english. Do not translate the labels in the glossary below. Notes are free text for us.',
        '# Do not edit key, english or draft: the return step checks they still match. You may sort or filter; rows are matched by key.',
        '# When you are done, send the file back. Write your name or initials after the colon on the next line (no email address):',
        '# reviewer: (your name or initials)',
        '# GLOSSARY (labels that stay in English, in capitals): ' + ' | '.join(
            f'{g["term"]} = {g["meaning"]}' for g in rules['glossary']),
        '# ' + GLOSSARY_NOTE + ' ' + rules['glossary_policy'],
    ]


# ------------------------------------------------------------------ html ---
CSS = """
:root{--bg:#fbfaf7;--ink:#1b1b1a;--mut:#5d5b55;--line:#d9d5c9;--card:#fff;--p1:#b3261e;--p2:#8a6100;--p3:#4a5d3a;--accent:#1f5f8b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#171716;--ink:#ecebe6;--mut:#a9a79f;--line:#3a3935;--card:#201f1d;--p1:#ff8a80;--p2:#e5b84a;--p3:#a8c98f;--accent:#7fb8e0}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
header,main{max-width:1200px;margin:0 auto;padding:0 16px}
h1{font-size:1.4rem;margin:1rem 0 .3rem}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:10px 0}
.box h2{font-size:1rem;margin:.2rem 0}
.gl dt{font-weight:700}.gl dd{margin:0 0 .4rem}
.bar{position:sticky;top:0;background:var(--bg);padding:8px 0;border-bottom:1px solid var(--line);z-index:2;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
button,select,input,textarea{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:4px 8px}
button{cursor:pointer}
table{width:100%;border-collapse:collapse;table-layout:fixed}
th,td{border-bottom:1px solid var(--line);padding:6px;vertical-align:top;overflow-wrap:anywhere;text-align:start}
th{font-size:.8rem;color:var(--mut)}
td.k{font-family:ui-monospace,monospace;font-size:.78rem}
td.w{font-size:.78rem;color:var(--mut)}
tr[data-p="1"] td:first-child{border-inline-start:4px solid var(--p1)}
tr[data-p="2"] td:first-child{border-inline-start:4px solid var(--p2)}
tr[data-p="3"] td:first-child{border-inline-start:4px solid var(--p3)}
textarea{width:100%;min-height:3.2em;box-sizing:border-box}
.n{width:100%;box-sizing:border-box}
tr.hide{display:none}
.mut{color:var(--mut)}
@media (max-width:760px){table,thead,tbody,tr,td,th{display:block}thead{display:none}tr{border-bottom:2px solid var(--line);padding:6px 0}}
"""

JS = r"""
(function(){
var COLS=%COLS%, LOC=%LOC%, STAMP=%STAMP%, STORE='review:'+LOC+':'+STAMP;
function esc(c){c=String(c==null?'':c);return /[",\r\n]/.test(c)?'"'+c.replace(/"/g,'""')+'"':c;}
function toCsv(rows,who){var o=['#locale='+LOC];if(who)o.push('# reviewer: '+who.replace(/[\r\n]+/g,' '));
 o.push(COLS.map(esc).join(','));rows.forEach(function(r){o.push(COLS.map(function(c){return esc(r[c]);}).join(','));});
 return '\ufeff'+o.join('\r\n')+'\r\n';}
window.__reviewToCsv=toCsv;
var rows=[].slice.call(document.querySelectorAll('tr[data-key]'));
function rowData(tr){var g=function(s){return tr.querySelector(s);};
 return {key:tr.getAttribute('data-key'),english:g('.en').textContent,draft:g('.dr').textContent,
  appears_in:g('.w').textContent,priority:tr.getAttribute('data-p'),why:tr.getAttribute('data-why'),
  status:tr.getAttribute('data-status'),verdict:g('select').value,corrected:g('textarea').value,notes:g('.n').value};}
function touched(tr){return tr.querySelector('select').value||tr.querySelector('textarea').value.trim()||tr.querySelector('.n').value.trim();}
function count(){var n=rows.filter(touched).length;document.getElementById('cnt').textContent=n+' of '+rows.length+' rows filled';}
function save(){try{var d={who:document.getElementById('who').value,r:{}};rows.forEach(function(tr){if(touched(tr))d.r[tr.getAttribute('data-key')]=
 [tr.querySelector('select').value,tr.querySelector('textarea').value,tr.querySelector('.n').value];});localStorage.setItem(STORE,JSON.stringify(d));}catch(e){}}
function restore(){try{var d=JSON.parse(localStorage.getItem(STORE)||'null');if(!d)return;document.getElementById('who').value=d.who||'';
 rows.forEach(function(tr){var v=d.r[tr.getAttribute('data-key')];if(v){tr.querySelector('select').value=v[0];tr.querySelector('textarea').value=v[1];tr.querySelector('.n').value=v[2];}});}catch(e){}}
document.addEventListener('input',function(){count();save();});
document.addEventListener('change',function(){count();save();});
document.getElementById('dl').addEventListener('click',function(){
 var who=document.getElementById('who').value.trim();
 var sel=rows.filter(touched).map(rowData);
 var blob=new Blob([toCsv(sel,who)],{type:'text/csv;charset=utf-8'});var a=document.createElement('a');
 a.href=URL.createObjectURL(blob);a.download='review_'+LOC+'.csv';document.body.appendChild(a);a.click();a.remove();});
document.getElementById('flt').addEventListener('change',function(e){var v=e.target.value;
 rows.forEach(function(tr){tr.classList.toggle('hide',!(v==='all'||tr.getAttribute('data-p')===v));});});
restore();count();
})();
"""


def html_sheet(locale, cat, rows, rules, stamp, counts):
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    d = cat['dir']
    glossary = ''.join(f'<dt>{e(g["term"])}</dt><dd>{e(g["meaning"])} Stays in English.</dd>' for g in rules['glossary'])
    body = []
    for r in rows:
        body.append(
            f'<tr data-key="{e(r["key"])}" data-p="{r["priority"]}" data-why="{e(r["why"])}" data-status="{e(r["status"])}">'
            f'<td class="k">{e(r["key"])}<br><span class="mut">P{r["priority"]} - {e(r["why"])}</span><br>'
            f'<span class="mut">{e(r["status"])}</span></td>'
            f'<td class="en" lang="en" dir="ltr">{e(r["english"])}</td>'
            f'<td class="dr" lang="{locale}" dir="{d}">{e(r["draft"])}</td>'
            f'<td class="w" lang="en" dir="ltr">{e(r["appears_in"])}</td>'
            f'<td><select aria-label="verdict for {e(r["key"])}"><option value=""></option><option>ok</option><option>fix</option></select></td>'
            f'<td><textarea lang="{locale}" dir="{d}" aria-label="corrected text for {e(r["key"])}"></textarea></td>'
            f'<td><input class="n" type="text" aria-label="notes for {e(r["key"])}"></td></tr>')
    js = (JS.replace('%COLS%', json.dumps(L.COLUMNS)).replace('%LOC%', json.dumps(locale))
          .replace('%STAMP%', json.dumps(stamp[:12])))
    inst = '<br>'.join(e(x[2:] if x.startswith('# ') else x) for x in instructions(locale, cat, rules, stamp, counts)
                       if x.startswith('# ') and not x.startswith(('# GLOSSARY', '# These labels', '# reviewer', '# When you are done')))
    return f"""<!doctype html>
<html lang="{locale}" dir="{d}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review sheet {e(locale)}</title><style>{CSS}</style></head>
<body>
<header lang="en" dir="ltr">
<h1>Translation review: {e(cat["language"])} ({e(cat["english_name"])})</h1>
<div class="box"><h2>How to use this sheet</h2><p>{inst}</p>
<p>Fill the three columns on the right in this page, type your name or initials above (no email address), then press Download. Your work is also kept in this browser until you clear it. Send the downloaded file back.</p></div>
<div class="box"><h2>Glossary: these labels stay in English, in capitals</h2><dl class="gl">{glossary}</dl><p>{e(rules["glossary_policy"])}</p></div>
<div class="bar"><label>Your name or initials <input id="who" type="text" maxlength="60" autocomplete="off"></label>
<label>Show <select id="flt"><option value="all">all rows</option><option value="1">priority 1 (safety and honesty)</option><option value="2">priority 2 (interface)</option><option value="3">priority 3 (page copy)</option></select></label>
<button id="dl" type="button">Download filled rows (CSV)</button><span id="cnt" class="mut" aria-live="polite"></span></div>
</header>
<main>
<table><thead><tr><th>key and priority</th><th>english</th><th>draft ({e(locale)})</th><th>appears in</th><th>verdict</th><th>corrected text</th><th>notes</th></tr></thead>
<tbody>{''.join(body)}</tbody></table>
</main>
<script>{js}</script>
</body></html>
"""


# ------------------------------------------------------------------ main ---
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='recompute i18n/review/summary.json and fail if it differs')
    ap.add_argument('--out', help='directory for the sheets (default: <root>/dist/review)')
    ap.add_argument('--no-summary', action='store_true', help='write the sheets only; leave i18n/review/summary.json alone (tests)')
    ap.add_argument('--root', default=str(L.ROOT))
    a = ap.parse_args()
    root = Path(a.root)
    obs = Observed(root)
    for own in ('i18n/build_review.py', 'i18n/review_lib.py', 'i18n/review_rules.json'):
        obs.read(own)
    rules = json.loads(obs.text('i18n/review_rules.json'))
    locs = [l for l in L.locales_of(root) if l != 'en']
    en = json.loads(obs.text('i18n/locales/en.json'))
    en_flat = L.flatten(en)
    ids = list(en_flat)
    where, bulk_pages = derive_where(obs, ids, en_flat)
    cats, ledgers = {}, {}
    for l in locs:
        cats[l] = json.loads(obs.text(f'i18n/locales/{l}.json'))
        lp = f'i18n/review/{l}.ledger.json'
        if (root / lp).exists():
            obs.read(lp)
        ledgers[l] = L.read_ledger(root, l)
    # the pages' presence is part of the stamp through derive_where's reads
    stamp = obs.stamp()

    summary = {'schema': 1, 'source_stamp': stamp, 'files_read': len(obs.seen),
               'pages_scanned': len(page_files(obs)), 'pages_carrying_whole_catalogue': bulk_pages, 'sources_scanned': len(source_files(obs)),
               'keys_with_no_derived_location': sum(
                   1 for w in where.values() if not (w['pages'] or w['code'] or w['dynamic'])),
               'locales': {}}
    out_dir = Path(a.out) if a.out else root / 'dist' / 'review'
    sheets = {}
    for l in locs:
        cat = cats[l]
        cat_flat = L.flatten(cat)
        if list(cat_flat) != ids:
            raise SystemExit(f'build_review: {l} does not mirror the English key set; run i18n/test.mjs')
        rows = build_rows(l, en_flat, cat_flat, where, rules, ledgers[l])
        counts = {'keys': len(rows)}
        for p in (1, 2, 3):
            counts[f'p{p}'] = sum(1 for r in rows if r['priority'] == p)
        cur, stale, unknown = L.review_counts(en_flat, cat_flat, ledgers[l])
        if unknown:
            raise SystemExit(f'build_review: {l} ledger names keys the catalog no longer has: {unknown[:5]}')
        s1, p1 = L.p1_counts(en_flat, cat_flat, ledgers[l], rules)
        summary['locales'][l] = {**counts, 'checked_by_native': cur, 'p1_checked_by_native': s1, 'out_of_date': stale,
                                 'translation_status': cat['translation_status'],
                                 'status_would_be': L.status_for(cur, len(rows), s1, p1)}
        sheets[l] = (rows, counts, cat)
    new_summary = json.dumps(summary, indent=1, sort_keys=True) + '\n'
    sp = root / 'i18n' / 'review' / 'summary.json'
    if a.check:
        have = sp.read_text(encoding='utf-8') if sp.exists() else ''
        if have != new_summary:
            print('build_review --check: i18n/review/summary.json is stale or missing; run python3 i18n/build_review.py',
                  file=sys.stderr)
            return 1
        print(f'build_review --check: current ({len(locs)} locales, stamp {stamp[:12]})')
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for l, (rows, counts, cat) in sheets.items():
        text = L.csv_text(rows, instructions(l, cat, rules, stamp, counts))
        (out_dir / f'{l}.csv').write_bytes(('\ufeff' + text).encode('utf-8'))
        (out_dir / f'{l}.html').write_text(html_sheet(l, cat, rows, rules, stamp, counts), encoding='utf-8')
    if not a.no_summary:
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(new_summary, encoding='utf-8')
    for l in locs:
        s = summary['locales'][l]
        print(f'{l}: {s["keys"]} keys, priority 1: {s["p1"]}, 2: {s["p2"]}, 3: {s["p3"]}, '
              f'checked by a native speaker: {s["checked_by_native"]}')
    print(f'sheets in {out_dir}; stamp {stamp[:12]}; read {len(obs.seen)} files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
