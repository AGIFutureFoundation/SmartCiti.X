#!/usr/bin/env python3
"""The network dashboard: SmartCiti.X's whole platform, read live from the
verified registries - the built campuses (district campuses and regional
hubs alike), whatever the roadmap still holds as a candidate toward ten,
and the pack that stands behind each one.

Every figure on this page is read from a registry's own JSON, not
retyped: halls and modules from the pack manifest, districts and campuses
from the union registry, simulators from sims/, tool cribs from tools/,
advisors from agents/, the world's weather and fauna from world/, the
sign system from labels/, the training-data recorder's shape from
training/, the synthetic-video prompt contract and its real runners from
orbis/, the avatar locker and TradeApes collection from avatars/, and the
metaverse interchange layer's reviewed standards from meta/, the real
Bay Restoration sites and their field-skill bridge from restoration/, and
the spatial fabric's GeoPose count and claimed / not-claimed split from
spatial/ (both of whose files this page also embeds for download, the
same inline pattern the geomap uses for its GeoJSON, since Pages serves
no registry file). If
a number here disagrees with its source, the source is right and this
page is stale - which `--check` mode exists to catch.
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
from staleness import emit  # noqa: E402
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
orbis = json.load(open(ROOT / 'orbis/registry/orbis.json'))
avatars = json.load(open(ROOT / 'avatars/registry/avatars.json'))
schools = json.load(open(ROOT / 'schools/registry/schools.json'))
# The locker's own decomposition: standard sections and their options, plus
# the one crew section seating every hall. README had typed `284 options`;
# the registry sums to 289 + 111, and only a read can stay right.
av_std = [s for s in avatars['sections'] if s['kind'] != 'crew']
av_crew = next(s for s in avatars['sections'] if s['kind'] == 'crew')
av_std_options = sum(len(s['options']) for s in av_std)
av_options = av_std_options + len(av_crew['options'])
meta = json.load(open(ROOT / 'meta/registry/metaverse.json'))
restoration = json.load(open(ROOT / 'restoration/registry/restoration.json'))
geopose_path = ROOT / 'spatial/registry/geopose.json'
fabric_path = ROOT / 'spatial/registry/fabric.json'
spatial = json.load(open(geopose_path))
fabric = json.load(open(fabric_path))

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
    (f"{sum(1 for s in sims['sims'].values() if s.get('operator'))} / "
     f"{len(sims['operator_levels'])}",
     'scripted reference operators / levels'),
    (f"{orbis['modules']} / {len(orbis['runners'])}",
     'Orbis module prompts / real runners'),
    (f"{len(avatars['sections'])} / {len(avatars['tradeapes']['apes'])}",
     'avatar locker sections / TradeApes'),
    (f"{len(av_std)} / {av_std_options} + {len(av_crew['options'])} = {av_options}",
     'standard locker sections / options + crew looks = avatar options'),
    (f"{len(schools['districts'])} / {len(schools['units'])}",
     'proposed school districts / live flipped units'),
    (str(len(meta['avatar_systems_reviewed'])), 'Unity avatar systems reviewed'),
    (f"{len(restoration['sites'])} / {len(restoration['tracks'])}",
     'real Bay Restoration sites / field-skill tracks'),
    (str(spatial['counts']['total']),
     'GeoPose 1.0 poses (campuses, anchors, restoration sites)'),
]

# the spatial fabric's own split: what it claims (GeoPose) and what it
# honestly does not (the OMBI shapes), both read from meta/'s registry
spatial_claimed = [s['id'] for s in meta['baseline']['standards']
                   if s['id'] == 'geopose-1.0']
spatial_not = [x['id'] for x in meta['baseline']['not_claimed']
               if x['id'] in ('ombi-spatial-fabric', 'ombi-som', 'rmap')]
SPATIAL_STATS = [
    (str(spatial['counts']['total']), 'GeoPose 1.0 Basic-YPR poses'),
    (f"{spatial['counts']['campuses']} / {spatial['counts']['anchors']} / "
     f"{spatial['counts']['restoration_sites']}",
     'campuses / anchors / restoration sites posed'),
    (str(spatial['counts']['unposed']), 'honestly unposed (no coordinate held)'),
    (f"{len(spatial_claimed)} / {len(spatial_not)}",
     'claimed (GeoPose) / not claimed (OMBI fabric, SOM, RMAP)'),
    (str(len(fabric['services'])), 'in-page services, no network'),
    (str(len(fabric['external_origins'])),
     'external origins, none served by this fabric'),
]
# embedded for download: a <script> of a non-JS type is inert, and "</"
# is escaped so no JSON string can close the element early
_embed = lambda p: p.read_text().replace('</', '<\\/')
geopose_json = _embed(geopose_path)
fabric_json = _embed(fabric_path)


PROV_CLASS = {'RECORDED': 'rec', 'DERIVED': 'rec', 'AUTHORED': 'auth'}


def campus_card(slug, c, is_built):
    is_hub = is_built and not c['districts']
    dist_chips = ''.join(
        f'<span class="chip" style="border-color:hsl({HUES[d]} 45% 40%);color:hsl({HUES[d]} 65% 72%)">{districts[d]["name"]}</span>'
        for d in c['districts'])
    if is_hub:
        dist_chips = '<span class="chip">regional hub · no home district</span>'
    prov = c['provenance'] if is_built else 'AUTHORED'
    prov_span = f'<span class="prov {PROV_CLASS[prov]}">{prov}</span>'
    if is_built:
        tag = '<span class="tag built">BUILT</span>'
        halls_bit = '0 home halls (111 regional)' if is_hub else f'{c["halls"]} halls'
        sub = f'{c["city"]}, {c["region"]} · {halls_bit} · {prov_span}'
    else:
        tag = '<span class="tag planned">CANDIDATE</span>'
        sub = f'{c["city"]}, {c["region"]} · {prov_span}'
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
spatial_tiles = ''.join(
    f'<div class="fig"><b>{v}</b><span>{lbl}</span></div>' for v, lbl in SPATIAL_STATS)

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
.dl{{display:inline-block;font:600 13px "Barlow Condensed",system-ui,sans-serif;letter-spacing:.03em;
  background:var(--sunk);color:var(--steel);border:1px solid var(--steel);border-radius:6px;
  padding:6px 12px;margin:8px 8px 0 0;cursor:pointer}}
.dl:hover{{background:var(--steel);color:var(--mark-ink)}}
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

<h2>Spatial fabric</h2>
<p class="lead">{spatial['honesty']['geopose_claimed']}</p>
<div class="figs">{spatial_tiles}</div>
<p class="lead" style="margin-top:14px">{fabric['fabric']['shape']}.</p>
<p class="sub">{spatial['counts']['total']} GeoPose 1.0 poses · encoding <code>{spatial['encoding']}</code> · CRS {spatial['crs']} ·
  operator {fabric['fabric']['operator']} · origin {fabric['fabric']['origin']} · entry <code>{fabric['fabric']['entry']}</code></p>
<p>
  <button class="dl" data-dl="geopose-json" data-name="geopose.json">⬇ geopose.json</button>
  <button class="dl" data-dl="fabric-json" data-name="fabric.json">⬇ fabric.json</button>
  <span class="sub">both embedded in this page and served from your own browser — no server, no fetch</span>
</p>
<script id="geopose-json" type="application/geopose+json">{geopose_json}</script>
<script id="fabric-json" type="application/json">{fabric_json}</script>

<div class="honesty">
  <li>{roadmap['honesty']['provenance_tiers']}</li>
  <li>{roadmap['honesty']['no_dates']}</li>
  <li>{agents['honesty']['status']}</li>
  <li>{training['honesty']['schematic']}</li>
  <li>{sims['honesty']['operator']}</li>
  <li>{sims['honesty']['xr']}</li>
  <li>{orbis['honesty']['synthetic_not_real']}</li>
  <li>{avatars['guarantee']}</li>
  <li>{meta['honesty']['status']}</li>
  <li>WebXR, as the metaverse layer claims it: {next(s['role'] for s in meta['baseline']['standards'] if s['id'] == 'webxr')}</li>
  <li>{restoration['honesty']['not_affiliated']}</li>
  <li>{spatial['honesty']['ombi_not_claimed']}</li>
  <li>{spatial['honesty']['no_heights_or_headings']}</li>
</div>
<script>
document.querySelectorAll('[data-dl]').forEach((b) => b.addEventListener('click', () => {{
  const src = document.getElementById(b.dataset.dl);
  const url = URL.createObjectURL(new Blob([src.textContent], {{ type: src.type }}));
  const a = document.createElement('a'); a.href = url; a.download = b.dataset.name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}}));
</script>
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
emit(out, page, f"{len(built)}/{target} built, {len(cand)} candidates")
