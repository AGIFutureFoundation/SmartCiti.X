import markdown, re, pathlib

HERE = pathlib.Path(__file__).resolve().parent


def _spec_path():
    """The spec lives at the tree root; this builder lives in web/. Resolve by
    walking up rather than trusting the working directory (defect 13's shape)."""
    for cand in (HERE, *HERE.parents):
        p = cand / "SmartCitiX_TradeCraft_Academy_Spec.md"
        if p.exists():
            return p
    raise FileNotFoundError("SmartCitiX_TradeCraft_Academy_Spec.md not found above " + str(HERE))


md = _spec_path().read_text()
# Drop the md H1 + meta lines (the HTML header replaces them)
md = md.split("---", 1)[1].lstrip("-\n")  # everything after first hr
body = markdown.markdown(md, extensions=["tables", "fenced_code"])

# Add ids to h2s for nav
slugs = {}
def h2id(m):
    txt = re.sub(r"<[^>]+>", "", m.group(1))
    mm = re.match(r"(\d+)\.", txt)
    sid = f"s{mm.group(1)}" if mm else re.sub(r"[^a-z0-9]+", "-", txt.lower()).strip("-")
    slugs[sid] = txt
    return f'<h2 id="{sid}">{m.group(1)}</h2>'
body = re.sub(r"<h2>(.*?)</h2>", h2id, body)
# wrap tables for x-scroll
body = body.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")

CHART_DATA = [
    ("Steady learner",     39.0, 10.3, 8.9),
    ("Fast climber",       39.8,  3.7, 6.9),
    ("Struggling learner", 42.3,  0.0, 6.1),
    ("Misplaced expert",   39.6,  0.0, 3.3),
    ("Erratic performer",  36.6, 12.4, 7.8),
    ("Returner (21d gap)", 41.2, 10.3, 8.9),
]
SERIES = [("ZPD dial", "var(--c1)"), ("Fixed difficulty 50", "var(--c2)"), ("Random difficulty", "var(--c3)")]

def inband_chart():
    rowh, barh, gap, pad_l, w = 74, 15, 4, 168, 640
    h = len(CHART_DATA) * rowh + 54
    x0, plot_w = pad_l, w - pad_l - 52
    scale = lambda v: v / 50 * plot_w
    parts = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" '
             f'aria-label="In-band residency by learner archetype: the ZPD dial holds the '
             f'0.70 to 0.85 band about six times more often than fixed or random difficulty.">']
    # gridlines
    for gv in (0, 10, 20, 30, 40, 50):
        gx = x0 + scale(gv)
        parts.append(f'<line x1="{gx:.1f}" y1="26" x2="{gx:.1f}" y2="{h-26}" stroke="var(--grid)" stroke-width="1"/>')
        parts.append(f'<text x="{gx:.1f}" y="18" font-size="10.5" fill="var(--muted)" text-anchor="middle">{gv}%</text>')
    for ri, (label, *vals) in enumerate(CHART_DATA):
        top = 34 + ri * rowh
        parts.append(f'<text x="{x0-12}" y="{top + 24}" font-size="12.5" fill="var(--ink)" '
                     f'text-anchor="end" font-weight="500">{label}</text>')
        for si, v in enumerate(vals):
            y = top + si * (barh + gap)
            bw = max(scale(v), 1.2)
            parts.append(f'<rect x="{x0}" y="{y}" width="{bw:.1f}" height="{barh}" rx="3" '
                         f'fill="{SERIES[si][1]}"/>')
            parts.append(f'<text x="{x0 + bw + 7:.1f}" y="{y + barh - 3}" font-size="11" '
                         f'fill="var(--muted)" font-variant-numeric="tabular-nums">{v}</text>')
    parts.append(f'<line x1="{x0}" y1="26" x2="{x0}" y2="{h-26}" stroke="var(--line)" stroke-width="1.5"/>')
    parts.append("</svg>")
    legend = "".join(
        f'<span class="lg"><i style="background:{c}"></i>{n}</span>' for n, c in SERIES)
    return (f'<figure class="fig"><div class="legend">{legend}</div>'
            f'<div class="chart-wrap">{"".join(parts)}</div>'
            f'<figcaption>Share of served tasks whose true success probability — computed from '
            f'the learner’s hidden ability, which the dial never sees — fell inside the '
            f'0.70–0.85 band. Mean across three seeds, 400 attempts per run.</figcaption></figure>')

body = body.replace("<p>[[CHART:inband]]</p>", inband_chart())

nav_items = [("s0","Principles"),("s1","ACP-01 Telemetry"),("s2","ACP-02 Profile"),("s3","ACP-03 ZPD Dial"),
             ("s4","ACP-04 Scaffolding"),("s5","ACP-05 Sequencing"),("s6","ACP-06 Assessment"),
             ("s7","ACP-07 Flow"),("s8","ACP-08 Safeguards"),("s9","ACP-09 Contracts"),("s10","Defaults"),
             ("s11","ACP-10 Ledger"),("s12","ACP-11 Fabric"),("s13","ACP-12 Agent Training"),("s14","ACP-13 Network Ops"),
             ("s15","ACP-14 Calibration"),("s16","ACP-15 Graph & Sequencing"),("s17","ACP-01/09 in code"),("s18","ACP-08 in code"),("s19","Launch posture"),
             ("s20","ACP-04 in code"),("s21","ACP-13 in code"),("s22","Identity")]
nav = "".join(f'<a href="#{i}">{t}</a>' for i,t in nav_items)

gauge = """<svg viewBox="0 0 220 130" class="gauge" role="img" aria-label="Dial gauge: predicted success, target band 0.70 to 0.85">
<path d="M 20 115 A 90 90 0 0 1 200 115" fill="none" stroke="var(--line)" stroke-width="10" stroke-linecap="round"/>
<path d="M 152.9 41.3 A 90 90 0 0 1 185.6 71.0" fill="none" stroke="var(--band)" stroke-width="12" stroke-linecap="round"/>
<g stroke="var(--muted)" stroke-width="1.5">
<line x1="20" y1="115" x2="30" y2="115"/><line x1="200" y1="115" x2="190" y2="115"/>
<line x1="110" y1="25" x2="110" y2="35"/></g>
<line x1="110" y1="115" x2="166" y2="60" stroke="var(--accent)" stroke-width="3.5" stroke-linecap="round"/>
<circle cx="110" cy="115" r="6" fill="var(--accent)"/>
<text x="20" y="128" font-size="10" fill="var(--muted)">0.0</text>
<text x="104" y="20" font-size="10" fill="var(--muted)">0.5</text>
<text x="188" y="128" font-size="10" fill="var(--muted)">1.0</text>
<text x="176" y="46" font-size="10" fill="var(--band)" font-weight="600">.70–.85</text>
</svg>"""

page = f"""<title>Adaptive Stack Protocol</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --paper:#F6F8F7; --surface:#ECF1EF; --ink:#1F2A30; --muted:#5B6B70;
  --accent:#0E7C86; --accent-ink:#0A5A62; --band:#C97A10; --line:#CBD6D3;
  --code-bg:#E8EEEC; --head:#16242B;
  --c1:#0090A0; --c2:#C97A10; --c3:#6A6FBF; --grid:#DDE5E3;
  color-scheme: light dark;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --paper:#141B1E; --surface:#1C2529; --ink:#DCE5E3; --muted:#8FA1A3;
  --accent:#4FB8C0; --accent-ink:#7FD0D6; --band:#E09A3E; --line:#31403F;
  --code-bg:#1A2327; --head:#EDF3F1;
  --c1:#00A2B5; --c2:#C08325; --c3:#8A82CE; --grid:#2A3739;
}} }}
:root[data-theme="dark"] {{
  --paper:#141B1E; --surface:#1C2529; --ink:#DCE5E3; --muted:#8FA1A3;
  --accent:#4FB8C0; --accent-ink:#7FD0D6; --band:#E09A3E; --line:#31403F;
  --code-bg:#1A2327; --head:#EDF3F1;
  --c1:#00A2B5; --c2:#C08325; --c3:#8A82CE; --grid:#2A3739;
}}
* {{ box-sizing:border-box; }}
body {{ background:var(--paper); color:var(--ink); margin:0;
  font:16px/1.65 "IBM Plex Sans", system-ui, sans-serif; }}
.wrap {{ max-width:78ch; margin:0 auto; padding:0 24px 96px; }}
header.hero {{ display:flex; gap:32px; align-items:center; flex-wrap:wrap;
  padding:56px 0 24px; border-bottom:2px solid var(--ink); }}
.hero-text {{ flex:1 1 380px; }}
.eyebrow {{ font:600 12px/1 "Archivo",sans-serif; letter-spacing:.14em; text-transform:uppercase;
  color:var(--accent-ink); margin:0 0 14px; }}
h1 {{ font:700 clamp(30px,5vw,44px)/1.08 "Archivo",sans-serif; color:var(--head);
  margin:0 0 14px; text-wrap:balance; letter-spacing:-.01em; }}
.sub {{ font:600 15px/1.3 "Archivo",sans-serif; color:var(--accent-ink); margin:0 0 14px;
  letter-spacing:.01em; }}
.colon {{ color:var(--accent); font-weight:500; padding:0 .06em; }}
.standfirst {{ color:var(--muted); margin:0; max-width:56ch; }}
.gauge {{ width:200px; flex:0 0 auto; }}
nav.mods {{ display:flex; flex-wrap:wrap; gap:8px; padding:20px 0 8px;
  border-bottom:1px solid var(--line); }}
nav.mods a {{ font:500 12.5px/1 "IBM Plex Mono",monospace; color:var(--accent-ink);
  text-decoration:none; padding:7px 10px; border:1px solid var(--line); border-radius:3px; }}
nav.mods a:hover, nav.mods a:focus-visible {{ border-color:var(--accent); color:var(--ink); outline:none; }}
h2 {{ font:700 24px/1.2 "Archivo",sans-serif; color:var(--head); margin:56px 0 16px;
  padding-top:20px; border-top:1px solid var(--line); text-wrap:balance; scroll-margin-top:16px; }}
h3 {{ font:600 17px/1.3 "Archivo",sans-serif; color:var(--head); margin:32px 0 10px; }}
p {{ margin:0 0 16px; }}
strong {{ color:var(--head); }}
code {{ font:13.5px/1.5 "IBM Plex Mono",monospace; background:var(--code-bg);
  padding:1px 5px; border-radius:3px; }}
pre {{ background:var(--code-bg); border-left:3px solid var(--accent); border-radius:0 4px 4px 0;
  padding:14px 16px; overflow-x:auto; margin:0 0 18px; }}
pre code {{ background:none; padding:0; font-size:13px; }}
.tw {{ overflow-x:auto; margin:0 0 18px; }}
table {{ border-collapse:collapse; width:100%; font-size:14.5px;
  font-variant-numeric: tabular-nums; }}
th {{ font:600 11.5px/1.3 "Archivo",sans-serif; letter-spacing:.08em; text-transform:uppercase;
  text-align:left; color:var(--muted); border-bottom:2px solid var(--ink); padding:8px 12px 6px 0; }}
td {{ border-bottom:1px solid var(--line); padding:8px 12px 8px 0; vertical-align:top; }}
td:first-child code, td:first-child {{ white-space:nowrap; }}
td:last-child, th:last-child {{ padding-right:0; }}
.wrap > h2:first-of-type {{ border-top:none; padding-top:6px; margin-top:44px; }}
hr {{ border:none; border-top:1px solid var(--line); margin:40px 0; }}
ul {{ padding-left:22px; }} li {{ margin-bottom:6px; }}
a {{ color:var(--accent-ink); }}
blockquote {{ margin:0 0 16px; padding:2px 0 2px 16px; border-left:3px solid var(--band); color:var(--muted); }}
.fig {{ margin:24px 0 26px; }}
.chart-wrap {{ overflow-x:auto; }}
.chart {{ width:100%; min-width:520px; display:block; }}
.legend {{ display:flex; flex-wrap:wrap; gap:16px; margin-bottom:12px; }}
.lg {{ display:inline-flex; align-items:center; gap:7px; font-size:12.5px; color:var(--muted); }}
.lg i {{ width:11px; height:11px; border-radius:2px; display:inline-block; }}
.fig figcaption {{ font-size:12.5px; color:var(--muted); margin-top:12px; max-width:62ch; line-height:1.5; }}
@media (prefers-reduced-motion: no-preference) {{ html {{ scroll-behavior:smooth; }} }}
@media (max-width:560px) {{ header.hero {{ padding-top:36px; }} .gauge {{ width:160px; }} }}
</style>
<div class="wrap">
<header class="hero">
  <div class="hero-text">
    <p class="eyebrow">Protocol Specification · ACP Suite · v2.6</p>
    <h1>SmartCiti.X <span class="colon">:</span> Trade Craft Academy</h1>
    <p class="sub">Adaptive Stack · powered by AGI Corp</p>
    <p class="standfirst">The full adaptive loop of the Academy — telemetry, learner profiling,
    the AI–ZPD dial, scaffolding, sequencing, assessment, flow regulation, safeguards —
    and, at scale: the verified 11,000,000-module ledger, the agent fabric, agent training, and network operations.
    Schemas, update rules, thresholds, and message contracts are normative unless marked <em>tunable</em>.</p>
  </div>
  {gauge}
</header>
<nav class="mods" aria-label="Modules">{nav}</nav>
{body}
</div>
"""
(HERE / "smartcitix_trade_craft_academy.html").write_text(page)
print("ok", len(page), "bytes;", "h2 ids:", list(slugs))
