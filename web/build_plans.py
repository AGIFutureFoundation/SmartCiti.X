#!/usr/bin/env python3
"""The Plans page: who each plan is for, with no prices, and a plain statement that
payments are not live.

Every plan card comes from payments/registry/catalog.json; every word from the plans.*
i18n keys. The catalogue carries no price, and this builder refuses one if it ever
does. "Choose" POSTs {plan, idempotency_key} to /api/checkout (payments/worker.mjs);
only a reply URL on checkout.stripe.com is ever followed. Served as static HTML with
no Worker behind it (GitHub Pages, file://), the button says why nothing happened.
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
from pagehero import pagehero, theme  # noqa: E402
from design_kit import STYLE_HEAD_JS  # noqa: E402

PAGE = 'web/trade_craft_plans.html'
E = lambda s: html.escape(str(s), quote=True)


class PlansError(Exception):
    pass


CAT = json.loads((ROOT / 'payments/registry/catalog.json').read_text())
EN = json.loads((ROOT / 'i18n/locales/en.json').read_text())['strings']


def L(k):
    if k not in EN:
        raise PlansError(f'plans: i18n key {k!r} is missing from en.json')
    return EN[k]


for k in ('live', 'status', 'plans', 'checkout'):
    if k not in CAT:
        raise PlansError(f'plans: catalog.{k} is missing')
if CAT['live'] is not False:
    raise PlansError('plans: catalog says live - this page states payments are not live; change both together')
for p in CAT['plans']:
    for k in ('id', 'label_key', 'desc_key', 'price', 'price_id', 'commercial_terms'):
        if k not in p:
            raise PlansError(f'plans: plan field {k!r} is missing')
    if p['price'] is not None or p['price_id'] is not None:
        raise PlansError(f'plans: {p["id"]} carries a price - never show one')

ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' "
        "height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' "
        "stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' "
        "stroke-linecap='round'/%3E%3C/svg%3E")

head_css, hero_html, hero_js = pagehero(PAGE, {
    'clip': 'hall-orbit', 'kicker': L('plans.hero.kicker'), 'title': L('plans.hero.title'),
    'accent': L('plans.hero.accent'), 'accent_style': 'gradient', 'lede': L('plans.hero.lede'),
    'actions': [], 'as_h1': True,
    'labels': {'pause': L('plans.hero.pause'), 'play': L('plans.hero.play')},
    'credit': L('plans.hero.credit')})
tcss, tjs = theme('doc')

cards = ''.join(
    f'<article class="tc-card plan" data-plan="{E(p["id"])}" data-tc-lift>'
    f'<h2>{E(L(p["label_key"]))}</h2><p>{E(L(p["desc_key"]))}</p>'
    f'<p class="price"><span class="tc-badge tc-badge-muted">{E(L("plans.price"))}</span></p>'
    f'<button type="button" class="tc-btn tc-btn-primary choose" data-plan="{E(p["id"])}">'
    f'{E(L("plans.choose"))}</button>'
    f'<p class="msg" role="status" aria-live="polite"></p></article>'
    for p in CAT['plans'])

MSG = {k: L('plans.' + k) for k in ('working', 'err.static', 'err.not_configured', 'err.generic',
                                     'return.success', 'return.cancelled')}
CFG = {'endpoint': CAT['checkout']['endpoint'], 'hosted': CAT['checkout']['hosted_prefix'], 'msg': MSG}
# </ can never close the script: JSON-escape the only characters that matter
CFG_JSON = json.dumps(CFG, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

PLANS_JS = r'''/* PLANS-CORE:BEGIN */
(function () {
  var C = JSON.parse(document.getElementById('plans-cfg').textContent);
  var keys = {};
  function newKey() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    var a = new Uint8Array(16); crypto.getRandomValues(a);
    return Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
  }
  function say(card, text) { card.querySelector('.msg').textContent = text; }
  async function choose(btn) {
    var card = btn.closest('.plan'), plan = btn.getAttribute('data-plan');
    if (location.protocol === 'file:') { say(card, C.msg['err.static']); return; }
    if (!keys[plan]) keys[plan] = newKey();
    btn.disabled = true; say(card, C.msg.working);
    var res = null, body = null;
    try {
      res = await fetch(C.endpoint, { method: 'POST', credentials: 'same-origin',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ plan: plan, idempotency_key: keys[plan] }) });
      body = await res.json();
    } catch (e) { body = null; }
    btn.disabled = false;
    if (res && res.ok && body && typeof body.url === 'string' && body.url.indexOf(C.hosted) === 0) {
      location.assign(body.url); return;
    }
    if (!res || !body || res.status === 404 || res.status === 405) { say(card, C.msg['err.static']); return; }
    if (body.error === 'not_configured') { say(card, C.msg['err.not_configured']); return; }
    say(card, C.msg['err.generic']);
  }
  document.querySelectorAll('.choose').forEach(function (b) { b.addEventListener('click', function () { choose(b); }); });
  var q = new URLSearchParams(location.search).get('checkout');
  var ret = document.getElementById('plans-return');
  if (q === 'success' || q === 'cancelled') { ret.textContent = C.msg['return.' + q]; ret.hidden = false; }
  window.__plansState = { endpoint: C.endpoint, hosted: C.hosted };
})();
/* PLANS-CORE:END */'''

# The page is declared in sitenav.GROUPS (about); a page it does not declare stops the build.
import sitenav  # noqa: E402
if PAGE not in sitenav.PAGES:
    raise SystemExit(f'build_plans: {PAGE} is not declared in web/sitenav.py GROUPS')
NAV = nav_html(PAGE, nav_labels('en'))

page = f'''<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{ICON}">
<title>Plans</title>
<script id="style-head-js">{STYLE_HEAD_JS}</script>
<style>{NAV_CSS}</style>
<style id="ph-css">{head_css}</style>
<style id="tc-css">{tcss}</style>
<style>
body{{font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
/* AUDIT row 11 (UX): the page tokens the site nav and the banners read, bound to the theme layer on <body>, so the
   nav and the page share one scheme (before this the nav fell back to the OS Canvas colours: a light bar over a dark page) */
body.tc-theme{{--plate:var(--tc-plate);--panel:var(--tc-panel);--raised:var(--tc-raised);--line:var(--tc-line);--rule:var(--tc-line);--ink:var(--tc-ink);--muted:var(--tc-muted);--mark:var(--tc-amber);--link:var(--tc-link)}}
.wrap{{max-width:1040px;margin:0 auto;padding:24px 16px 56px}}
.banner{{display:flex;gap:12px;align-items:flex-start;background:var(--panel);color:var(--ink);
  border:1px solid var(--line);border-inline-start:4px solid var(--mark);border-radius:8px;padding:14px 18px;margin:0 0 18px}}
.banner strong{{font-size:17px}}
.notes{{color:var(--muted);margin:0 0 22px;padding:0;list-style:none}}
.notes li{{margin:4px 0}}
.plans{{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}}
.plan{{display:flex;flex-direction:column;gap:10px;padding:18px}}
.plan h2{{margin:0;font-size:22px;color:var(--ink)}}
.plan p{{margin:0;color:var(--muted)}}
.plan .choose{{align-self:flex-start;margin-top:auto}}
.plan .msg{{min-height:1.4em;color:var(--ink);font-size:14px}}
.return{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:0 0 18px;color:var(--ink)}}
[hidden]{{display:none!important}}
</style>
</head>
<body class="tc-theme">
{NAV}{hero_html}
<main class="wrap">
<div class="banner" role="note" id="plans-banner"><span class="tc-badge tc-badge-warn">!</span><strong>{E(L("plans.banner"))}</strong></div>
<p class="return" id="plans-return" role="status" hidden></p>
<ul class="notes"><li>{E(L("plans.gate_note"))}</li><li>{E(L("plans.card_note"))}</li></ul>
<noscript><p class="banner">{E(L("plans.noscript"))}</p></noscript>
<section class="plans" aria-label="{E(L("plans.nav"))}">{cards}</section>
</main>
<script type="application/json" id="plans-cfg">{CFG_JSON}</script>
<script>{PLANS_JS}</script>
<script>{tjs}</script>
<script>{hero_js}</script>
<script id="style-js">{STYLE_JS}</script>
</body>
</html>
'''
TITLE = 'SmartCiti.X : Trade Craft Academy \u2014 ' + L('plans.nav')
SEO_STATE = 'wired'
page = apply_seo(page, PAGE, TITLE, L('plans.seo.desc'), 'page')
emit(HERE / 'trade_craft_plans.html', page,
     f'{len(CAT["plans"])} plans | prices: none | live: false | nav+seo {SEO_STATE}')
