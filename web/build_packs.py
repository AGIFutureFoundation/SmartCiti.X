#!/usr/bin/env python3
"""The holodeck packs catalogue: the "SmartCiti.X Powered by AGI Corp" series, one card per pack.

Every card comes from holodeck/registry/packs.json (python3 holodeck/build.py), which counts each
pack's contents from the registries it names. This builder types no figure: counts, statuses,
sources and deep links are read from that registry, and every word from the packs.* i18n keys
(8 locales; the page switches by ?lang= or the browser's language, Arabic right-to-left).
Filters by kind are radio buttons read by CSS :has() - they work with no script.
No price, no purchase, no download, no accreditation, no partner claim. A pack's "Open in
world" link appears only where the registry names a page that carries it.
"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS, STYLE_JS  # noqa: E402
from pagehero import theme  # noqa: E402
from design_kit import STYLE_HEAD_JS  # noqa: E402

PAGE = 'web/trade_craft_packs.html'
SERIES = 'SmartCiti.X Powered by AGI Corp'
E = lambda s: html.escape(str(s), quote=True)


class PacksError(Exception):
    pass


REG = json.loads((ROOT / 'holodeck/registry/packs.json').read_text(encoding='utf-8'))
for k in ('series', 'kinds', 'counts', 'packs', 'honesty'):
    if k not in REG:
        raise PacksError(f'packs: holodeck registry has no {k!r}')
if REG['series'] != SERIES:
    raise PacksError(f'packs: series is {REG["series"]!r}, expected exactly {SERIES!r}')
for p in REG['packs']:
    for k in ('id', 'kind', 'status', 'contents', 'requires', 'sources', 'open', 'series'):
        if k not in p:
            raise PacksError(f'packs: pack field {k!r} is missing')
    if p['status'] not in ('SHIPPING', 'PROPOSED'):
        raise PacksError(f'packs: {p["id"]} has status {p["status"]!r}')
    if p['status'] != 'SHIPPING' and p['open'] is not None:
        raise PacksError(f'packs: PROPOSED pack {p["id"]} carries a deep link')
    if p['open'] is not None and not (ROOT / p['open']).is_file():
        raise PacksError(f'packs: {p["id"]} links {p["open"]}, which does not exist')

# ---- locale catalogs: every packs.* key used here, in all 8 locales ----
CAT = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.loads(f.read_text(encoding='utf-8'))
    for need in ('locale', 'dir', 'strings'):
        if need not in c:
            raise PacksError(f'packs: {f.name} has no {need!r}')
    CAT[c['locale']] = {'dir': c['dir'], 'strings': {k: v for k, v in c['strings'].items() if k.startswith('packs.')}}
if len(CAT) != 8 or 'en' not in CAT or not any(v['dir'] == 'rtl' for v in CAT.values()):
    raise PacksError(f'packs: expected 8 locales incl. en and an rtl one, found {sorted(CAT)}')
EN = CAT['en']['strings']
USED = set()


def L(k):
    for loc, c in CAT.items():
        if k not in c['strings'] or not c['strings'][k].strip():
            raise PacksError(f'packs: i18n key {k!r} is missing from {loc}')
    USED.add(k)
    return EN[k]


def T(k, tag='span', attrs=''):
    return f'<{tag}{attrs} data-i18n="{k}">{E(L(k))}</{tag}>'


# ---- cards ----
KIND_ATTR = ' class="kind"'
STAT_ATTR = ' class="tc-stat-l"'
def title_html(p):
    if p['kind'] in ('union', 'k12'):      # quoted registry names (bundles/ package name, layers k12 label)
        return f'<span>{E(p["title"])}</span>'
    return T(p['title_key'])


def card(p):
    counts = ''.join(f'<div class="ct"><dt>{T("packs.count." + k)}</dt><dd data-count="{E(k)}">{int(v)}</dd></div>'
                     for k, v in sorted(p['contents'].items()))
    req = (', '.join(f'<a href="#pk-{E(r)}">{E(r)}</a>' for r in p['requires'])
           if p['requires'] else T('packs.none'))
    srcs = (''.join(f'<li><code>{E(s["path"])}</code> <span class="sha">{E(s["sha256"])}</span></li>' for s in p['sources'])
            if p['sources'] else f'<li>{T("packs.none")}</li>')
    badge = 'tc-badge-ok' if p['status'] == 'SHIPPING' else 'tc-badge-warn'
    if p['open']:
        href = p['open'][len('web/'):] if p['open'].startswith('web/') else '../' + p['open']
        go = f'<a class="tc-btn tc-btn-primary go" href="{E(href)}" data-open="{E(p["open"])}">{T("packs.open")}</a>'
    else:
        go = T('packs.noopen', 'p', ' class="noopen"')
    return (f'<article class="tc-card pk" id="pk-{E(p["id"])}" data-pack="{E(p["id"])}" data-kind="{E(p["kind"])}" '
            f'data-status="{E(p["status"])}">'
            f'<header class="pk-h"><span class="tc-badge {badge}" data-badge>{E(p["status"])}</span>'
            f'{T("packs.kind." + p["kind"], "span", KIND_ATTR)}</header>'
            f'<h2>{title_html(p)}</h2>'
            f'<dl class="cts">{counts}</dl>'
            f'<p class="rq">{T("packs.requires", "strong")}: {req}</p>'
            f'<details class="src"><summary>{T("packs.sources")}</summary><ul>{srcs}</ul></details>'
            f'{go}</article>')


KINDS = REG['kinds']
filters = ''.join(
    f'<label class="fk"><input type="radio" name="pk-kind" value="{k}" id="pk-k-{k}"{" checked" if k == "all" else ""}>'
    f'{T("packs.kind." + k)}</label>' for k in ['all'] + KINDS)
FILTER_CSS = ''.join(f'.cat:has(#pk-k-{k}:checked) .pk:not([data-kind="{k}"]){{display:none}}' for k in KINDS)
cards = ''.join(card(p) for p in REG['packs'])
C = REG['counts']
if C['packs'] != len(REG['packs']):
    raise PacksError('packs: counts.packs differs from the pack list')
stats = ''.join(f'<div class="tc-stat"><span class="tc-stat-v" data-stat="{k}">{int(C[k])}</span>'
                f'{T("packs.stat." + k, "span", STAT_ATTR)}</div>'
                for k in ('packs', 'shipping', 'proposed'))
honest = ''.join(f'<li>{T("packs.honest." + k)}</li>'
                 for k in ('counted', 'status', 'price', 'cert', 'k12', 'un', 'play', 'names'))

tcss, tjs = theme('doc')
for k in [k for k in EN if k.startswith('packs.home.')] + ['packs.nav', 'packs.seo.desc']:
    L(k)  # page chrome + front-door keys shipped in the catalog too

PACKS_JS = r'''/* PACKS-CORE:BEGIN */
(function () {
  var I = JSON.parse(document.getElementById('packs-i18n').textContent);
  function pick() {
    var q = new URLSearchParams(location.search).get('lang');
    if (q && Object.prototype.hasOwnProperty.call(I, q)) return q;
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < prefs.length; i++) {
      var c = String(prefs[i]).slice(0, 2).toLowerCase();
      if (Object.prototype.hasOwnProperty.call(I, c)) return c;
    }
    return 'en';
  }
  var loc = pick(), S = I[loc].strings;
  document.documentElement.lang = loc;
  document.documentElement.dir = I[loc].dir;
  document.querySelectorAll('[data-i18n]').forEach(function (el) {
    var s = S[el.getAttribute('data-i18n')];
    if (typeof s !== 'string') throw new Error('packs i18n: ' + loc + ' has no ' + el.getAttribute('data-i18n'));
    el.textContent = s;
  });
  window.__packsState = { locale: loc, dir: I[loc].dir, cards: document.querySelectorAll('.pk').length };
})();
/* PACKS-CORE:END */'''

ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' "
        "height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M16 6 L26 11 L26 21 L16 26 L6 21 L6 11 Z' fill='none' "
        "stroke='%23E8A33D' stroke-width='2.4' stroke-linejoin='round'/%3E%3Cpath d='M6 11 L16 16 L26 11 M16 16 V26' "
        "fill='none' stroke='%2341C4D4' stroke-width='2.2' stroke-linejoin='round'/%3E%3C/svg%3E")

# The page must be declared in sitenav.GROUPS; a page it does not declare stops the build.
import sitenav  # noqa: E402
if PAGE not in sitenav.PAGES:
    raise SystemExit(f'build_packs: {PAGE} is not declared in web/sitenav.py GROUPS')
NAV = nav_html(PAGE, nav_labels('en'))

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{ICON}">
<title>Holodeck packs</title>
<script id="style-head-js">{STYLE_HEAD_JS}</script>
<style>{NAV_CSS}</style>
<style id="tc-css">{tcss}</style>
<style>
body{{font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 16px 56px}}
.head{{margin:0 0 20px}}
.head .lede{{color:var(--tc-muted);max-width:72ch;margin:8px 0 0}}
.series{{margin:10px 0 0;color:var(--tc-ink);font-weight:600}}
.series span{{color:var(--tc-muted);font-weight:400}}
.stats{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:0 0 20px;max-inline-size:640px}}
.filters{{border:1px solid var(--tc-line);border-radius:8px;padding:10px 14px;margin:0 0 18px;display:flex;flex-wrap:wrap;gap:8px 16px;background:var(--tc-panel);color:var(--tc-ink)}}
.filters legend{{padding:0 6px;color:var(--tc-muted)}}
.fk{{display:inline-flex;align-items:center;gap:6px;min-block-size:44px;cursor:pointer}}
.fk input{{inline-size:18px;block-size:18px;accent-color:var(--tc-amber)}}
.grid{{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(270px,1fr))}}
.pk{{display:flex;flex-direction:column;gap:10px;padding:18px;min-inline-size:0}}
.pk-h{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.pk .kind{{color:var(--tc-muted);font-size:14px}}
.pk h2{{margin:0;font-size:20px;line-height:1.25;color:var(--tc-ink);overflow-wrap:anywhere}}
.cts{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 12px;margin:0}}
.ct{{display:flex;flex-direction:column-reverse}}
.ct dt{{color:var(--tc-muted);font-size:13px}}
.ct dd{{margin:0;font-size:22px;font-weight:700;color:var(--tc-ink);font-variant-numeric:tabular-nums}}
.rq{{margin:0;color:var(--tc-muted);font-size:14px}}
.rq strong{{color:var(--tc-ink)}}
.rq a{{color:var(--tc-link)}}
.src{{font-size:13px;color:var(--tc-muted)}}
.src summary{{cursor:pointer;min-block-size:32px;color:var(--tc-ink)}}
.src ul{{margin:4px 0 0;padding-inline-start:18px}}
.src code{{overflow-wrap:anywhere}}
.src .sha{{font-family:ui-monospace,monospace}}
.pk .go{{align-self:flex-start;margin-top:auto;min-block-size:44px;display:inline-flex;align-items:center}}
.pk .noopen{{margin:auto 0 0;color:var(--tc-muted);font-size:14px}}
.honesty{{margin:32px 0 0;border-block-start:1px solid var(--tc-line);padding-block-start:16px;color:var(--tc-muted)}}
.honesty ul{{margin:0;padding-inline-start:18px}}
.honesty li{{margin:4px 0}}
{FILTER_CSS}
</style>
</head>
<body class="tc-theme">
{NAV}
<main class="wrap cat" id="packs-main">
<header class="head">
{T("packs.kicker", "p", ' class="tc-kicker"')}
{T("packs.title", "h1", ' class="tc-page-title"')}
{T("packs.lede", "p", ' class="lede"')}
<p class="series" data-series>{T("packs.series")}: {E(REG["series"])}</p>
</header>
<div class="stats">{stats}</div>
<fieldset class="filters"><legend data-i18n="packs.filter">{E(L("packs.filter"))}</legend>{filters}</fieldset>
<section class="grid" aria-label="{E(L("packs.nav"))}">{cards}</section>
<footer class="honesty" id="packs-honesty"><ul>{honest}</ul></footer>
</main>
<script type="application/json" id="packs-i18n">__PACKS_I18N__</script>
<script>{PACKS_JS}</script>
<script>{tjs}</script>
<script id="style-js">{STYLE_JS}</script>
</body>
</html>
'''
# the catalog is cut AFTER the page is written, so it holds every key the page used
I18N = {loc: {'dir': c['dir'], 'strings': {k: c['strings'][k] for k in sorted(USED)}} for loc, c in CAT.items()}
I18N_JSON = json.dumps(I18N, ensure_ascii=False, sort_keys=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
if page.count('__PACKS_I18N__') != 1:
    raise PacksError('packs: i18n placeholder must appear exactly once')
page = page.replace('__PACKS_I18N__', I18N_JSON)
TITLE = 'SmartCiti.X : Trade Craft Academy — ' + L('packs.nav')
page = apply_seo(page, PAGE, TITLE, L('packs.seo.desc'), 'page')
emit(HERE / 'trade_craft_packs.html', page,
     f'{C["packs"]} packs | {C["shipping"]} SHIPPING | {C["proposed"]} PROPOSED | prices: none | nav+seo wired')
