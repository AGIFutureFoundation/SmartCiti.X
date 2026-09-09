#!/usr/bin/env python3
"""The languages page: the Academy overview in every shipped locale.

Rendered from the i18n catalogs, the pack manifest and the union registry —
the page holds no strings and no figures of its own, so it cannot disagree
with either. One section per locale, direction-aware (Arabic renders
right-to-left), with a client-side switcher and `lang`/`dir` stamped on every
section so screen readers pronounce each language correctly.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'i18n').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()
manifest = json.load(open(ROOT / 'pack/manifest.json'))
L = manifest['ledger']
districts_reg = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']

LOCALE_DIR = ROOT / 'i18n' / 'locales'
locales = {}
for f in sorted(LOCALE_DIR.glob('*.json')):
    locales[f.stem] = json.load(open(f))
assert 'en' in locales

# English first, then the rest alphabetically — the source language leads.
ORDER = ['en'] + sorted(k for k in locales if k != 'en')

F = lambda x: f"{x:,}"


def fmt(s, **vars):
    for k, v in vars.items():
        s = s.replace('{%s}' % k, str(v))
    return s


def section(code):
    c = locales[code]
    s = c['strings']
    figures = ''.join(
        f'<div class="fig"><b>{v}</b><span>{lbl}</span></div>'
        for v, lbl in [
            (F(L['halls']), fmt(s['figures.halls'], n='').strip()),
            (F(L['total_modules']), fmt(s['figures.modules'], n='').strip()),
            (str(len(districts_reg)), fmt(s['figures.districts'], n='').strip()),
        ])
    rows = ''.join(
        f'<tr><td class="dn">{c["districts"][k]["name"]}</td>'
        f'<td class="dt">{c["districts"][k]["tagline"]}</td>'
        f'<td class="dc">{len(d["halls"])}</td></tr>'
        for k, d in districts_reg.items())
    ladder = ' · '.join(c['tracks'])
    honesty = ''.join(f'<li>{s[k]}</li>' for k in
                      ('honesty.taxonomy', 'honesty.modules',
                       'honesty.content', 'honesty.translation'))
    status = ('' if c['translation_status'] == 'source language' else
              f'<p class="status">{c["translation_status"]}</p>')
    return f'''<section class="loc" id="loc-{code}" lang="{code}" dir="{c["dir"]}" hidden>
<p class="tagline">{s["tagline"]}</p>
<div class="figs">{figures}</div>
<p class="overview">{s["overview"]}</p>
<table class="districts"><tbody>{rows}</tbody></table>
<p class="ladder"><b>{c["tiers"]["fundamentals"]} → {c["tiers"]["applied"]} → {c["tiers"]["mastery"]}</b><br>{ladder}</p>
<ul class="honesty">{honesty}</ul>
{status}
</section>'''


tabs = ''.join(
    f'<button class="tab" data-loc="{code}" lang="{code}">{locales[code]["language"]}</button>'
    for code in ORDER)
sections = '\n'.join(section(code) for code in ORDER)

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartCiti.X : Trade Craft Academy — languages</title>
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);
  font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px 48px}}
.wrap{{max-width:880px;margin:0 auto}}
header{{padding:40px 0 8px;border-bottom:3px solid var(--mark)}}
header h1{{font:700 34px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}}
header h1 .x{{color:var(--mark)}}
header p{{color:var(--muted);margin:6px 0 14px}}
.tabs{{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0}}
.tab{{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  padding:8px 14px;border-radius:6px;cursor:pointer;font:inherit}}
.tab[aria-selected="true"]{{background:var(--mark);color:var(--mark-ink);border-color:var(--mark);font-weight:600}}
.loc .tagline{{font-size:19px;color:var(--steel)}}
.figs{{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}}
.fig{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;
  padding:12px 18px;min-width:140px}}
.fig b{{display:block;font:600 24px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--mark)}}
.fig span{{color:var(--muted);font-size:13px}}
.districts{{border-collapse:collapse;width:100%;margin:14px 0}}
.districts td{{border-top:1px solid var(--rule);padding:8px 10px;vertical-align:top}}
.dn{{font-weight:600;white-space:nowrap}}
.dt{{color:var(--muted)}}
.dc{{text-align:end;color:var(--steel);font-variant-numeric:tabular-nums}}
.ladder{{color:var(--muted)}}
.honesty{{background:var(--sunk);border-inline-start:3px solid var(--mark);border-radius:6px;
  padding:14px 26px;color:var(--muted);font-size:14px}}
.status{{color:var(--muted);font-size:13px;font-style:italic}}
[hidden]{{display:none!important}}
</style>
</head>
<body><div class="wrap">
<header>
  <h1>SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
  <p>powered by AGI Corp</p>
</header>
<nav class="tabs" role="tablist" aria-label="Language">{tabs}</nav>
{sections}
<script>
const tabs = [...document.querySelectorAll('.tab')];
function show(loc) {{
  for (const t of tabs) t.setAttribute('aria-selected', String(t.dataset.loc === loc));
  for (const s of document.querySelectorAll('.loc')) s.hidden = (s.id !== 'loc-' + loc);
  document.documentElement.lang = loc;
}}
for (const t of tabs) t.addEventListener('click', () => show(t.dataset.loc));
show((navigator.language || 'en').slice(0, 2).match(/^({"|".join(ORDER)})$/) ? (navigator.language || 'en').slice(0, 2) : 'en');
</script>
</div></body>
</html>
'''

out = HERE / 'trade_craft_languages.html'
out.write_text(page)
print(f"written: {len(page):,} bytes | {len(ORDER)} locales | {L['halls']} halls")
