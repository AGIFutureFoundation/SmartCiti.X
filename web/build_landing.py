import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'i18n').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()

# The i18n exit criterion applies here too: this page renders in English only,
# but its copy comes from the source catalog's own strings rather than being
# retyped as Python literals — i18n/catalog.mjs's load() validates the
# catalog's honesty fields the moment JS reads one, and i18n/validate.mjs is
# that same rule run for this Python build (see the identical comment in
# build_languages.py — one truth, not a second copy of the rule).
_v = subprocess.run(['node', str(ROOT / 'i18n/validate.mjs')], capture_output=True, text=True)
if _v.returncode != 0:
    sys.stderr.write(_v.stdout + _v.stderr)
    sys.exit(1)

_EN = json.loads((ROOT / 'i18n/locales/en.json').read_text(encoding='utf-8'))['strings']


def S(key):
    """Look up a source-catalog string by its dotted key. Strict, like
    catalog.mjs's t(): a missing key is a build failure, not a silent blank —
    the same contract that keeps a translation from falling back quietly."""
    if key not in _EN:
        raise KeyError(f'i18n: no en value for {key}')
    return _EN[key]


CSS = """
/* dark-first: the bare :root carries the dark plate, light is the counterpart */
:root{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --steel:#41C4D4; --steel-ink:#7FDCE8;
  --good:#5CB584; --warn:#E8A33D; --crit:#E07C68;
  color-scheme:dark light;
}
@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){
  --plate:#F1F4F3; --panel:#FFFFFF; --sunk:#E4EAE9; --ink:#141D20; --muted:#54646A;
  --rule:#CBD6D6; --mark:#9F680B; --steel:#0A7E8C; --steel-ink:#065A66;
  --good:#2C7A50; --warn:#9A6408; --crit:#A8432F;
}}
:root[data-theme="light"]{
  --plate:#F1F4F3; --panel:#FFFFFF; --sunk:#E4EAE9; --ink:#141D20; --muted:#54646A;
  --rule:#CBD6D6; --mark:#9F680B; --steel:#0A7E8C; --steel-ink:#065A66;
  --good:#2C7A50; --warn:#9A6408; --crit:#A8432F;
}
*{box-sizing:border-box}
body{margin:0;background:var(--plate);color:var(--ink);
  font:16.5px/1.65 "IBM Plex Sans",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
h1,h2,h3,.disp{font-family:"Barlow Condensed","Archivo Narrow",system-ui,sans-serif;
  text-wrap:balance;margin:0;letter-spacing:.01em}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
a{color:var(--steel-ink)}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}

/* ---------- plate rule: the one signage motif, used sparingly ---------- */
.markrule{height:6px;background:repeating-linear-gradient(135deg,
  var(--mark) 0 14px, transparent 14px 28px);border-radius:1px}

/* ---------- nav ---------- */
nav.top{display:flex;align-items:center;gap:18px;flex-wrap:wrap;
  padding:18px 0;border-bottom:1px solid var(--rule)}
.logo{font:700 19px/1 "Barlow Condensed",sans-serif;letter-spacing:.02em;text-transform:uppercase}
.logo .x{color:var(--steel)} .logo .sep{color:var(--mark);padding:0 .18em}
nav.top .links{margin-inline-start:auto;display:flex;gap:20px;flex-wrap:wrap}
nav.top a{font:600 12.5px/1 "Barlow Condensed",sans-serif;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);text-decoration:none;padding:6px 0}
nav.top a:hover,nav.top a:focus-visible{color:var(--ink);outline:none;
  box-shadow:0 2px 0 var(--mark)}

/* ---------- hero ---------- */
header.hero{padding:64px 0 52px}
.eyebrow{font:600 12px/1.4 "IBM Plex Mono",monospace;letter-spacing:.16em;
  text-transform:uppercase;color:var(--mark);margin:0 0 22px}
h1{font-size:clamp(40px,7.2vw,82px);line-height:.95;font-weight:700;
  text-transform:uppercase;margin:0 0 26px;max-width:16ch}
h1 em{font-style:normal;color:var(--mark)}
.lede{font-size:clamp(17px,1.9vw,20px);line-height:1.6;color:var(--ink);
  max-width:60ch;margin:0 0 14px}
.lede-2{color:var(--muted);max-width:62ch;margin:0}
.herorule{margin:34px 0 0;max-width:340px}

/* ---------- facts strip ---------- */
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));
  gap:1px;background:var(--rule);border-block:1px solid var(--rule);margin-top:52px}
.fact{background:var(--plate);padding:20px 22px}
.fact b{display:block;font:700 30px/1 "Barlow Condensed",sans-serif;color:var(--ink);
  font-variant-numeric:tabular-nums}
.fact span{display:block;font-size:12.5px;color:var(--muted);margin-top:7px;line-height:1.45}

/* ---------- sections ---------- */
section{padding:64px 0;border-bottom:1px solid var(--rule)}
.kicker{font:600 12px/1 "IBM Plex Mono",monospace;letter-spacing:.16em;
  text-transform:uppercase;color:var(--mark);margin:0 0 16px}
h2{font-size:clamp(28px,3.6vw,40px);line-height:1.04;font-weight:700;
  text-transform:uppercase;margin:0 0 20px;max-width:20ch}
h3{font-size:20px;line-height:1.2;font-weight:700;margin:0 0 10px;text-transform:uppercase;
  letter-spacing:.02em}
p{margin:0 0 16px;max-width:66ch}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(258px,1fr));gap:30px}
.lead-col{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:44px;align-items:start}
@media(max-width:820px){.lead-col{grid-template-columns:1fr;gap:26px}}

/* ---------- audience panels: three different shapes, three different asks -- */
.panel{border:1px solid var(--rule);background:var(--panel)}
.panel .ph{padding:20px 24px;border-bottom:1px solid var(--rule);
  display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.panel .ph h3{margin:0}
.panel .ph .tag{font:600 11px/1 "IBM Plex Mono",monospace;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);margin-inline-start:auto}
.panel .pb{padding:24px}
.panel .pb p:last-child{margin-bottom:0}

ul.ticks{list-style:none;margin:0 0 18px;padding:0;display:flex;flex-direction:column;gap:11px}
/* The marker is positioned, not a grid item: as grid columns, the text node
   after <b> became a third item and landed in the 16px column, one word per
   line. Absolute positioning keeps the content in normal inline flow. */
ul.ticks li{position:relative;padding-inline-start:22px;font-size:15px;line-height:1.55}
ul.ticks li::before{content:"";position:absolute;inset-inline-start:0;top:.5em;width:9px;height:9px;
  background:var(--mark);clip-path:polygon(0 0,100% 50%,0 100%)}
ul.ticks.steel li::before{background:var(--steel)}

dl.terms{display:grid;grid-template-columns:auto 1fr;gap:9px 20px;margin:0;font-size:14.5px}
dl.terms dt{font-family:"IBM Plex Mono",monospace;font-size:12.5px;color:var(--muted);
  letter-spacing:.02em;padding-top:2px}
dl.terms dd{margin:0}

/* ---------- status table ---------- */
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14.5px}
th{text-align:start;font:600 11px/1.3 "IBM Plex Mono",monospace;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);padding-block:0 9px;padding-inline:0 14px;border-bottom:1px solid var(--rule)}
td{padding-block:11px;padding-inline:0 14px;border-bottom:1px solid var(--rule);vertical-align:top}
tr:last-child td{border-bottom:none}
th:last-child,td:last-child{padding-inline-end:0}
.pill{display:inline-block;font:600 11px/1 "IBM Plex Mono",monospace;letter-spacing:.06em;
  text-transform:uppercase;padding:5px 9px;border:1px solid currentColor;border-radius:2px;
  white-space:nowrap}
.p-built{color:var(--good)} .p-part{color:var(--warn)} .p-no{color:var(--crit)}

/* ---------- cta ---------- */
.cta{display:inline-flex;align-items:center;gap:10px;font:700 14px/1 "Barlow Condensed",sans-serif;
  letter-spacing:.1em;text-transform:uppercase;padding:14px 20px;border-radius:2px;
  text-decoration:none;border:1px solid var(--mark);color:var(--plate);background:var(--mark)}
.cta:hover,.cta:focus-visible{filter:brightness(1.08);outline:none;
  box-shadow:0 0 0 3px color-mix(in srgb,var(--mark) 35%,transparent)}
.cta.ghost{background:none;color:var(--ink);border-color:var(--rule)}
.cta.ghost:hover,.cta.ghost:focus-visible{border-color:var(--steel);color:var(--steel-ink);filter:none;
  box-shadow:0 0 0 3px color-mix(in srgb,var(--steel) 25%,transparent)}
.ctarow{display:flex;gap:12px;flex-wrap:wrap;margin-top:26px}

.note{font-size:13.5px;color:var(--muted);line-height:1.6;max-width:70ch}
footer{padding:46px 0 64px;color:var(--muted);font-size:13.5px}
footer .frow{display:flex;gap:26px;flex-wrap:wrap;align-items:baseline}
@media (prefers-reduced-motion:no-preference){
  html{scroll-behavior:smooth}
  .herorule{transform-origin:left;animation:draw .7s cubic-bezier(.2,.7,.3,1) both}
  @keyframes draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}
}
:focus-visible{outline:2px solid var(--steel);outline-offset:3px}
"""

BODY = f"""
<div class="wrap">
  <nav class="top">
    <div class="logo">SmartCiti<span class="x">.X</span><span class="sep">:</span>Trade Craft Academy</div>
    <div class="links">
      <a href="#mission">{S('landing.nav.mission')}</a>
      <a href="#how">{S('landing.nav.how')}</a>
      <a href="#investors">{S('landing.nav.investors')}</a>
      <a href="#partners">{S('landing.nav.partners')}</a>
      <a href="#educators">{S('landing.nav.educators')}</a>
      <a href="#status">{S('landing.nav.status')}</a>
    </div>
  </nav>

  <header class="hero">
    <p class="eyebrow">{S('landing.hero.eyebrow')}</p>
    <h1>{S('landing.hero.title')}</h1>
    <p class="lede">{S('landing.hero.lede')}</p>
    <p class="lede lede-2">{S('landing.hero.lede2')}</p>
    <div class="markrule herorule"></div>
  </header>

  <div class="facts">
    <div class="fact"><b>111</b><span>{S('landing.facts.halls')}</span></div>
    <div class="fact"><b>11,000,000</b><span>{S('landing.facts.modules')}</span></div>
    <div class="fact"><b>0.70&ndash;0.85</b><span>{S('landing.facts.band')}</span></div>
    <div class="fact"><b>246</b><span>{S('landing.facts.checks')}</span></div>
    <div class="fact"><b>17</b><span>{S('landing.facts.defects')}</span></div>
  </div>

  <section id="mission">
    <p class="kicker">{S('landing.mission.kicker')}</p>
    <div class="lead-col">
      <div>
        <h2>{S('landing.mission.h2')}</h2>
        <p>{S('landing.mission.p1')}</p>
        <p>{S('landing.mission.p2')}</p>
      </div>
      <div>
        <h3>{S('landing.mission.h3')}</h3>
        <ul class="ticks">
          <li>{S('landing.mission.tick1')}</li>
          <li>{S('landing.mission.tick2')}</li>
          <li>{S('landing.mission.tick3')}</li>
          <li>{S('landing.mission.tick4')}</li>
        </ul>
      </div>
    </div>
  </section>

  <section id="how">
    <p class="kicker">{S('landing.how.kicker')}</p>
    <h2>{S('landing.how.h2')}</h2>
    <p>{S('landing.how.p')}</p>
    <div class="cols" style="margin-top:30px">
      <div>
        <h3>{S('landing.how.dial.h3')}</h3>
        <p class="note">{S('landing.how.dial.p')}</p>
      </div>
      <div>
        <h3>{S('landing.how.graph.h3')}</h3>
        <p class="note">{S('landing.how.graph.p')}</p>
      </div>
      <div>
        <h3>{S('landing.how.gate.h3')}</h3>
        <p class="note">{S('landing.how.gate.p')}</p>
      </div>
      <div>
        <h3>{S('landing.how.coaches.h3')}</h3>
        <p class="note">{S('landing.how.coaches.p')}</p>
      </div>
    </div>
  </section>

  <section id="investors">
    <p class="kicker">{S('landing.investors.kicker')}</p>
    <h2>{S('landing.investors.h2')}</h2>
    <div class="lead-col">
      <div>
        <p>{S('landing.investors.p1')}</p>
        <p>{S('landing.investors.p2')}</p>
        <p>{S('landing.investors.p3')}</p>
        <div class="ctarow">
          <a class="cta" href="mailto:x@agifuturefoundation.org?subject=Investor%20enquiry%20%E2%80%94%20Trade%20Craft%20Academy">{S('landing.investors.cta1')}</a>
          <a class="cta ghost" href="#status">{S('landing.investors.cta2')}</a>
        </div>
      </div>
      <div class="panel">
        <div class="ph"><h3>{S('landing.investors.panel.h3')}</h3><span class="tag">{S('landing.investors.panel.tag')}</span></div>
        <div class="pb">
          <dl class="terms">
            <dt>{S('landing.investors.term.content.dt')}</dt><dd>{S('landing.investors.term.content.dd')}</dd>
            <dt>{S('landing.investors.term.evidence.dt')}</dt><dd>{S('landing.investors.term.evidence.dd')}</dd>
            <dt>{S('landing.investors.term.compliance.dt')}</dt><dd>{S('landing.investors.term.compliance.dd')}</dd>
            <dt>{S('landing.investors.term.platform.dt')}</dt><dd>{S('landing.investors.term.platform.dd')}</dd>
          </dl>
        </div>
      </div>
    </div>
  </section>

  <section id="partners">
    <p class="kicker">{S('landing.partners.kicker')}</p>
    <h2>{S('landing.partners.h2')}</h2>
    <p>{S('landing.partners.p')}</p>
    <div class="cols" style="margin-top:30px">
      <div class="panel">
        <div class="ph"><h3>{S('landing.partners.panel.unions.h3')}</h3><span class="tag">{S('landing.partners.panel.unions.tag')}</span></div>
        <div class="pb">
          <p class="note">{S('landing.partners.panel.unions.p')}</p>
        </div>
      </div>
      <div class="panel">
        <div class="ph"><h3>{S('landing.partners.panel.employers.h3')}</h3><span class="tag">{S('landing.partners.panel.employers.tag')}</span></div>
        <div class="pb">
          <p class="note">{S('landing.partners.panel.employers.p')}</p>
        </div>
      </div>
      <div class="panel">
        <div class="ph"><h3>{S('landing.partners.panel.tech.h3')}</h3><span class="tag">{S('landing.partners.panel.tech.tag')}</span></div>
        <div class="pb">
          <p class="note">{S('landing.partners.panel.tech.p')}</p>
        </div>
      </div>
    </div>
    <div class="ctarow">
      <a class="cta" href="mailto:x@agifuturefoundation.org?subject=Partnership%20enquiry%20%E2%80%94%20Trade%20Craft%20Academy">{S('landing.partners.cta')}</a>
    </div>
  </section>

  <section id="educators">
    <p class="kicker">{S('landing.educators.kicker')}</p>
    <h2>{S('landing.educators.h2')}</h2>
    <div class="lead-col">
      <div>
        <p>{S('landing.educators.p')}</p>
        <ul class="ticks steel">
          <li>{S('landing.educators.tick1')}</li>
          <li>{S('landing.educators.tick2')}</li>
          <li>{S('landing.educators.tick3')}</li>
          <li>{S('landing.educators.tick4')}</li>
        </ul>
        <div class="ctarow">
          <a class="cta" href="mailto:x@agifuturefoundation.org?subject=Educator%20pilot%20enquiry%20%E2%80%94%20Trade%20Craft%20Academy">{S('landing.educators.cta')}</a>
        </div>
      </div>
      <div class="panel">
        <div class="ph"><h3>{S('landing.educators.panel.h3')}</h3><span class="tag">{S('landing.educators.panel.tag')}</span></div>
        <div class="pb">
          <p class="note">{S('landing.educators.panel.p1')}</p>
          <p class="note">{S('landing.educators.panel.p2')}</p>
        </div>
      </div>
    </div>
  </section>

  <section id="status">
    <p class="kicker">{S('landing.status.kicker')}</p>
    <h2>{S('landing.status.h2')}</h2>
    <p>{S('landing.status.p')}</p>
    <div class="tw" style="margin-top:26px">
      <table>
        <thead><tr><th>{S('landing.status.th.area')}</th><th>{S('landing.status.th.state')}</th><th>{S('landing.status.th.detail')}</th></tr></thead>
        <tbody>
          <tr><td>{S('landing.status.row1.area')}</td><td><span class="pill p-built">{S('landing.status.row1.pill')}</span></td>
            <td>{S('landing.status.row1.detail')}</td></tr>
          <tr><td>{S('landing.status.row2.area')}</td><td><span class="pill p-built">{S('landing.status.row2.pill')}</span></td>
            <td>{S('landing.status.row2.detail')}</td></tr>
          <tr><td>{S('landing.status.row3.area')}</td><td><span class="pill p-built">{S('landing.status.row3.pill')}</span></td>
            <td>{S('landing.status.row3.detail')}</td></tr>
          <tr><td>{S('landing.status.row4.area')}</td><td><span class="pill p-built">{S('landing.status.row4.pill')}</span></td>
            <td>{S('landing.status.row4.detail')}</td></tr>
          <tr><td>{S('landing.status.row5.area')}</td><td><span class="pill p-part">{S('landing.status.row5.pill')}</span></td>
            <td>{S('landing.status.row5.detail')}</td></tr>
          <tr><td>{S('landing.status.row6.area')}</td><td><span class="pill p-part">{S('landing.status.row6.pill')}</span></td>
            <td>{S('landing.status.row6.detail')}</td></tr>
          <tr><td>{S('landing.status.row7.area')}</td><td><span class="pill p-no">{S('landing.status.row7.pill')}</span></td>
            <td>{S('landing.status.row7.detail')}</td></tr>
          <tr><td>{S('landing.status.row8.area')}</td><td><span class="pill p-no">{S('landing.status.row8.pill')}</span></td>
            <td>{S('landing.status.row8.detail')}</td></tr>
          <tr><td>{S('landing.status.row9.area')}</td><td><span class="pill p-no">{S('landing.status.row9.pill')}</span></td>
            <td>{S('landing.status.row9.detail')}</td></tr>
        </tbody>
      </table>
    </div>
    <p class="note" style="margin-top:24px">{S('landing.status.note')}</p>
  </section>

  <footer>
    <div class="markrule" style="max-width:120px;margin-bottom:24px"></div>
    <div class="frow">
      <div style="min-width:220px">
        <div class="logo" style="font-size:16px;margin-bottom:8px">SmartCiti<span class="x">.X</span><span class="sep">:</span>Trade Craft Academy</div>
        <div>{S('landing.hero.eyebrow')}<br>
          <a href="mailto:x@agifuturefoundation.org">x@agifuturefoundation.org</a></div>
      </div>
      <div style="max-width:44ch">
        {S('landing.footer.disclaimer')}
      </div>
    </div>
  </footer>
</div>
"""

page = ('<title>Trade Craft Academy</title>\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600;700'
        '&family=IBM+Plex+Mono:wght@400;600&display=swap">\n'
        f'<style>{CSS}</style>\n{BODY}')
# Written beside this script, not into the working directory: run from the
# tree root it left a second, identical copy of the page there (defect 13's shape).
emit(HERE / 'trade_craft_landing.html', page)
