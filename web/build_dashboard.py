#!/usr/bin/env python3
"""The network dashboard: SmartCiti.X's whole platform, read live from the
verified registries - three campuses built, seven candidates on the
roadmap toward ten, and the pack that stands behind each one.

Every figure on this page is read from a registry's own JSON, not
retyped: halls and modules from the pack manifest, districts and campuses
from the union registry, simulators from sims/, tool cribs from tools/,
advisors from agents/, the world's weather and fauna from world/, the
sign system from labels/, and the training-data recorder's shape from
training/. If a number here disagrees with its source, the source is
right and this page is stale - which `--check` mode exists to catch.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'roadmap').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()
sys.path.insert(0, str(ROOT / 'web'))
from mapdata import HUES  # noqa: E402
manifest = json.load(open(ROOT / 'pack/manifest.json'))
L = manifest['ledger']
districts = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']
unions = json.load(open(ROOT / 'unions/registry/unions.json'))
sims = json.load(open(ROOT / 'sims/registry/sims.json'))
tools = json.load(open(ROOT / 'tools/registry/toolcribs.json'))
agents = json.load(open(ROOT / 'agents/registry/advisors.json'))
world = json.load(open(ROOT / 'world/registry/world.json'))
labels = json.load(open(ROOT / 'labels/registry/labels.json'))
training = json.load(open(ROOT / 'training/registry/training.json'))
roadmap = json.load(open(ROOT / 'roadmap/registry/roadmap.json'))

F = lambda x: f"{x:,}"
built = roadmap['built_campuses']
cand = roadmap['candidates']
target = roadmap['target']
pct = round(len(built) / target * 100)

tool_count = sum(len(c['tools']) for c in tools['cribs'].values())

STATS = [
    (F(L['halls']), 'training halls'),
    (F(L['total_modules']), 'generated modules'),
    (str(len(districts)), 'districts'),
    (str(unions['count']), 'union crafts named'),
    (str(len(sims['sims'])), 'operable simulators'),
    (f"{len(tools['cribs'])} / {tool_count}", 'tool cribs / tools'),
    (f"{agents['counts']['advisors']} / {agents['counts']['topics']}",
     'advisors / topics'),
    (str(world['counts']['weather']), 'weather states'),
    (str(world['counts']['ground']), 'generated ground surfaces'),
    (str(world['counts']['animals']), 'animals in the yards'),
    (str(labels['counts']['kinds']), 'sign kinds'),
    (str(len(training['episode_kinds'])), 'training-data episode kinds'),
]


def campus_card(slug, c, is_built):
    dist_chips = ''.join(
        f'<span class="chip" style="border-color:hsl({HUES[d]} 45% 40%);color:hsl({HUES[d]} 65% 72%)">{districts[d]["name"]}</span>'
        for d in c['districts'])
    if is_built:
        tag = '<span class="tag built">BUILT</span>'
        sub = (f'{c["city"]}, {c["region"]} · {c["halls"]} halls · '
               f'<span class="prov rec">RECORDED</span>')
    else:
        tag = '<span class="tag planned">CANDIDATE</span>'
        sub = (f'{c["city"]}, {c["region"]} · '
               f'<span class="prov auth">AUTHORED</span>')
    why = f'<p class="why">{c["why"]}</p>' if not is_built else ''
    return f'''<div class="card">
  <div class="ch">{tag}<b>{c["name"]}</b></div>
  <p class="sub">{sub}</p>
  <div class="chips">{dist_chips}</div>
  {why}
</div>'''


built_cards = '\n'.join(campus_card(k, v, True) for k, v in built.items())
cand_cards = '\n'.join(campus_card(k, v, False) for k, v in cand.items())
checklist_rows = ''.join(
    f'<li><b>{row["step"]}</b> — {row["what"]} '
    f'<code>{row["file"]}</code></li>' for row in roadmap['checklist'])
stat_tiles = ''.join(
    f'<div class="fig"><b>{v}</b><span>{lbl}</span></div>' for v, lbl in STATS)

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartCiti.X : Trade Craft Academy — network dashboard</title>
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4; --good:#5CB584;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);
  font:15px/1.6 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px 56px}}
.wrap{{max-width:1040px;margin:0 auto}}
header{{padding:36px 0 10px;border-bottom:3px solid var(--mark)}}
header h1{{font:700 32px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}}
header h1 .x{{color:var(--mark)}}
header p{{color:var(--muted);margin:6px 0 0}}
h2{{font:600 22px "Barlow Condensed",system-ui,sans-serif;letter-spacing:.02em;
  margin:34px 0 4px;padding-bottom:6px;border-bottom:1px solid var(--rule)}}
.lead{{color:var(--muted);font-size:13.5px;margin:2px 0 16px;max-width:720px}}
.meter-wrap{{display:flex;align-items:center;gap:16px;margin:14px 0 22px;flex-wrap:wrap}}
.meter{{flex:1;min-width:220px;height:14px;background:var(--sunk);
  border:1px solid var(--rule);border-radius:8px;overflow:hidden}}
.meter i{{display:block;height:100%;background:linear-gradient(90deg,var(--mark),var(--good))}}
.meter-n{{font:700 26px "Barlow Condensed",system-ui,sans-serif;white-space:nowrap}}
.meter-n span{{color:var(--muted);font-size:15px;font-weight:400}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}}
.card{{background:var(--panel);border:1px solid var(--rule);border-radius:9px;padding:14px 16px}}
.ch{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.ch b{{font:600 16px "Barlow Condensed",system-ui,sans-serif}}
.tag{{font-size:10px;letter-spacing:.06em;font-weight:700;border-radius:4px;padding:2px 7px}}
.tag.built{{background:var(--good);color:#0c1113}}
.tag.planned{{background:var(--sunk);color:var(--mark);border:1px solid var(--mark)}}
.sub{{color:var(--muted);font-size:12.5px;margin:4px 0}}
.prov{{font-weight:700;letter-spacing:.03em}}
.prov.rec{{color:var(--good)}}
.prov.auth{{color:var(--mark)}}
.chips{{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0}}
.chip{{font-size:11px;border:1px solid var(--rule);border-radius:999px;padding:2px 9px;color:var(--muted)}}
.why{{color:var(--ink);font-size:12.5px;margin:8px 0 0;line-height:1.55}}
.figs{{display:flex;flex-wrap:wrap;gap:10px}}
.fig{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;
  padding:11px 16px;min-width:130px;flex:1}}
.fig b{{display:block;font:600 22px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--steel)}}
.fig span{{color:var(--muted);font-size:12px}}
.checklist{{background:var(--sunk);border-radius:8px;padding:16px 20px;list-style:none;margin:0}}
.checklist li{{padding:6px 0;border-bottom:1px solid var(--rule);color:var(--muted);font-size:13px}}
.checklist li:last-child{{border-bottom:none}}
.checklist code{{background:var(--panel);border-radius:4px;padding:1px 6px;font-size:11.5px;color:var(--steel)}}
.honesty{{background:var(--sunk);border-inline-start:3px solid var(--mark);border-radius:6px;
  padding:14px 22px;color:var(--muted);font-size:13px;margin-top:30px}}
.honesty li{{margin:5px 0}}
footer{{color:var(--muted);font-size:12px;margin-top:30px;padding-top:14px;border-top:1px solid var(--rule)}}
a{{color:var(--steel)}}
</style>
</head>
<body><div class="wrap">
<header>
  <h1>SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
  <p>Network dashboard — powered by AGI Corp</p>
</header>

<h2>Ten walkable worlds</h2>
<p class="lead">{roadmap['honesty']['target_not_claim']}</p>
<div class="meter-wrap">
  <div class="meter-n">{len(built)}<span>/{target} built</span></div>
  <div class="meter" role="progressbar" aria-valuenow="{len(built)}" aria-valuemin="0"
       aria-valuemax="{target}"><i style="width:{pct}%"></i></div>
  <div class="meter-n" style="font-size:16px;color:var(--muted)">{len(cand)} candidates</div>
</div>
<div class="grid">
{built_cards}
{cand_cards}
</div>

<h2>Building the next one</h2>
<p class="lead">{roadmap['honesty']['not_a_claim_of_content']}</p>
<ul class="checklist">{checklist_rows}</ul>

<h2>The platform, live</h2>
<p class="lead">Every figure below reads from its own registry at build time.</p>
<div class="figs">{stat_tiles}</div>

<div class="honesty">
  <li>{roadmap['honesty']['provenance_tiers']}</li>
  <li>{roadmap['honesty']['no_dates']}</li>
  <li>{agents['honesty']['status']}</li>
  <li>{training['honesty']['schematic']}</li>
</div>
<footer>
  <a href="trade_craft_3d.html">3D environment</a> ·
  <a href="trade_craft_map.html">campus map</a> ·
  <a href="trade_craft_geomap.html">network geomap</a> ·
  <a href="../wiki/Home.md">wiki</a>
</footer>
</div></body>
</html>
'''

out = HERE / 'trade_craft_dashboard.html'
if '--check' in sys.argv:
    if not out.exists() or out.read_text() != page:
        print('STALE: web/trade_craft_dashboard.html')
        print('       run: python3 web/build_dashboard.py')
        sys.exit(1)
    print('dashboard is current')
else:
    out.write_text(page)
    print(f"written: {len(page):,} bytes | {len(built)}/{target} built, "
          f"{len(cand)} candidates")
