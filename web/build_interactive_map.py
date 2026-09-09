#!/usr/bin/env python3
"""The interactive campus map: every registry, one surface, layered.

Renders web/trade_craft_interactive.html — a self-contained page with:

  - the 111 halls tiled by district, with four toggleable layers
    (district hue, pipeline state, module layers, training stations);
  - a detail panel per hall: its figures, level census, generated floor
    plan (the same room geometry the interiors pack asserts), its skill
    lattice, and — where the recovered station content seeds it — the
    stations drawn inside the rooms their strands own;
  - the full i18n catalog set, so the whole surface renders in any of the
    shipped locales, direction-aware.

Everything is read from the registries: the union roster, the module
manifest, the hall files, the skill graph, the station registry, the
interiors geometry and the locale catalogs. The page holds no data of its
own, so it cannot disagree with any of them.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'unions').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()
sys.path.insert(0, str(ROOT / 'web'))
from interiors import build as build_interiors  # noqa: E402

manifest = json.load(open(ROOT / 'pack/manifest.json'))
L = manifest['ledger']
halls_json = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
districts_reg = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']
stations_reg = json.load(open(ROOT / 'stations/registry/stations.json'))

# District hues: eight values far enough apart to read as categories.
HUES = {'structural': 210, 'envelope': 28, 'systems': 182, 'energy': 48,
        'earthworks': 100, 'industry': 348, 'transport': 262, 'control': 148}
assert set(HUES) == set(districts_reg), 'every district needs a hue'


def hall_level_states(slug):
    doc = json.load(open(ROOT / f'pack/registry/halls/{slug}.json'))
    c = {'live': 0, 'calibrating': 0, 'schema_ok': 0, 'draft': 0}
    for lv in doc['levels']:
        c[lv['state']] += 1
    return c


census = {h['slug']: hall_level_states(h['slug']) for h in halls_json}
# interiors wants module-state counts; levels * slots * variants per level.
per_level = L['slots_per_level'] * L['variants_per_lesson']
plans = build_interiors(halls_json, lambda i: {
    k: v * per_level for k, v in census[halls_json[i]['slug']].items()})

stations_by_hall = {}
for s in stations_reg['stations']:
    stations_by_hall.setdefault(s['hall'], []).append(s)

district_of = {slug: k for k, d in districts_reg.items() for slug in d['halls']}

HALLS = [{
    'slug': h['slug'], 'name': h['name'], 'focus': h['focus'],
    'index': h['index'], 'district': district_of[h['slug']],
    'lessons': h['lessons'], 'modules': h['modules'],
    'census': census[h['slug']],
    'rooms': [{'strand': r['strand'], 'label': r['label'],
               'purpose': r['purpose'], 'x': r['x'], 'y': r['y'],
               'w': r['w'], 'h': r['h']} for r in plans[h['slug']]['rooms']],
    'depth': plans[h['slug']]['envelope']['d'],
    'stations': [s['station_id'] for s in stations_by_hall.get(h['slug'], [])],
} for h in halls_json]

DISTRICTS = {k: {'name': d['name'], 'tagline': d['tagline'],
                 'halls': d['halls'], 'hue': HUES[k]}
             for k, d in districts_reg.items()}

I18N = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.load(open(f))
    I18N[c['locale']] = {
        'language': c['language'], 'dir': c['dir'],
        'strings': c['strings'], 'districts': c['districts'],
        'strands': c['strands'], 'tiers': c['tiers'], 'states': c['states'],
    }

DATA = json.dumps({
    'ledger': {'halls': L['halls'], 'total_modules': L['total_modules'],
               'districts': len(DISTRICTS)},
    'per_level': per_level,
    'districts': DISTRICTS,
    'halls': HALLS,
    'stations': {s['station_id']: s for s in stations_reg['stations']},
    'i18n': I18N,
}, ensure_ascii=False, separators=(',', ':'))

page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartCiti.X : Trade Craft Academy — interactive campus map</title>
<style>
:root{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
  --good:#5CB584; --warn:#E8A33D; --crit:#E07C68;
}
*{box-sizing:border-box}
body{margin:0;background:var(--plate);color:var(--ink);
  font:15px/1.55 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px 48px}
.wrap{max-width:1180px;margin:0 auto}
header{padding:30px 0 10px;border-bottom:3px solid var(--mark);
  display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 22px}
header h1{font:700 30px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}
header h1 .x{color:var(--mark)}
header .attr{color:var(--muted);font-size:13px}
.figs{display:flex;gap:16px;flex-wrap:wrap;margin-left:auto;color:var(--muted);font-size:13px}
.figs b{color:var(--mark);font:600 17px "Barlow Condensed",sans-serif}
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:16px 0}
.bar .lbl{color:var(--muted);font-size:13px;margin-inline-end:2px}
.tgl{display:inline-flex;align-items:center;gap:6px;background:var(--panel);
  border:1px solid var(--rule);border-radius:999px;padding:6px 13px;cursor:pointer;
  font-size:13px;user-select:none}
.tgl input{accent-color:var(--mark);margin:0}
select{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:6px 10px;font:inherit;margin-inline-start:auto}
.legend{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin:2px 0 14px}
.legend .sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-inline-end:5px;vertical-align:-1px}
.campus{display:grid;grid-template-columns:repeat(auto-fill,minmax(430px,1fr));gap:18px}
@media(max-width:480px){.campus{grid-template-columns:1fr}}
.district{background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:14px 16px}
.district h2{font:600 19px "Barlow Condensed",sans-serif;margin:0;
  border-inline-start:4px solid;padding-inline-start:10px}
.district .tag{color:var(--muted);font-size:12.5px;margin:3px 0 10px;padding-inline-start:14px}
.halls{display:grid;grid-template-columns:repeat(auto-fill,minmax(122px,1fr));gap:8px}
.hall{position:relative;background:var(--sunk);border:1px solid var(--rule);border-radius:7px;
  padding:8px 9px 7px;cursor:pointer;text-align:start;color:var(--ink);font:inherit;
  display:flex;flex-direction:column;gap:5px;min-height:58px}
.hall:hover{border-color:var(--mark)}
.hall .nm{font-size:12px;line-height:1.25;font-weight:600}
.hall .stbar{display:flex;height:5px;border-radius:3px;overflow:hidden;background:var(--rule)}
.hall .stbar i{display:block;height:100%}
.hall .badge{position:absolute;top:-6px;inset-inline-end:-6px;background:var(--mark);
  color:var(--mark-ink);font:700 10.5px/1 "IBM Plex Mono",monospace;border-radius:999px;
  padding:4px 6px;display:none}
body.L-stations .hall .badge{display:block}
body:not(.L-modules) .hall .stbar{display:none}
body.L-districts .hall{border-inline-start-width:4px}
/* detail panel */
#ov{position:fixed;inset:0;background:rgba(6,10,12,.72);display:none;z-index:9}
#panel{position:fixed;top:0;inset-inline-end:0;bottom:0;width:min(560px,100%);
  background:var(--panel);border-inline-start:1px solid var(--rule);z-index:10;
  transform:translateX(105%);transition:transform .22s ease;overflow-y:auto;
  padding:20px 22px 40px}
html[dir="rtl"] #panel{transform:translateX(-105%)}
body.open #ov{display:block}
body.open #panel{transform:none}
#panel h2{font:600 24px "Barlow Condensed",sans-serif;margin:2px 0 2px}
#panel .focus{color:var(--muted);margin:0 0 10px}
#panel .chip{display:inline-block;border:1px solid var(--rule);border-radius:999px;
  padding:2px 10px;font-size:12px;color:var(--muted);margin:0 4px 10px 0}
#panel h3{font:600 15px "Barlow Condensed",sans-serif;letter-spacing:.04em;
  text-transform:uppercase;color:var(--steel);margin:20px 0 8px}
#close{position:absolute;top:12px;inset-inline-end:14px;background:none;border:1px solid var(--rule);
  color:var(--muted);border-radius:6px;padding:5px 11px;cursor:pointer;font:inherit}
.cbar{display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--rule);margin:4px 0 6px}
.cbar i{display:block;height:100%}
.ckey{color:var(--muted);font-size:12px;display:flex;gap:12px;flex-wrap:wrap}
svg text{font-family:"IBM Plex Mono",monospace}
.stn{border:1px solid var(--rule);border-radius:8px;margin:8px 0;overflow:hidden}
.stn>button{width:100%;text-align:start;background:var(--sunk);color:var(--ink);
  border:none;padding:9px 12px;cursor:pointer;font:inherit;display:flex;gap:8px;align-items:baseline}
.stn .dot{width:9px;height:9px;border-radius:50%;background:var(--mark);flex:none;align-self:center}
.stn .rm{margin-inline-start:auto;color:var(--muted);font-size:11.5px;white-space:nowrap}
.stn .body{display:none;padding:10px 14px;border-top:1px solid var(--rule);font-size:13.5px}
.stn.open .body{display:block}
.stn .body ul{margin:6px 0;padding-inline-start:20px;color:var(--muted)}
.stn .q{background:var(--sunk);border-radius:6px;padding:8px 12px;margin-top:8px}
.stn .q .opt{display:block;background:none;border:1px solid var(--rule);color:var(--ink);
  border-radius:5px;padding:5px 9px;margin:5px 0;cursor:pointer;font:inherit;width:100%;text-align:start}
.stn .q .opt.ok{border-color:var(--good);color:var(--good)}
.stn .q .opt.bad{border-color:var(--crit);color:var(--crit)}
.lattice{display:grid;grid-template-columns:auto repeat(3,1fr);gap:4px;font-size:11.5px}
.lattice div{background:var(--sunk);border-radius:4px;padding:4px 7px;color:var(--muted)}
.lattice .hd{background:none;color:var(--steel)}
.lattice .on{color:var(--ink)}
footer{color:var(--muted);font-size:12.5px;margin-top:26px;border-top:1px solid var(--rule);padding-top:12px}
</style>
</head>
<body class="L-districts L-modules L-stations">
<div class="wrap">
<header>
  <h1>SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
  <span class="attr">powered by AGI Corp</span>
  <div class="figs" id="figs"></div>
</header>
<div class="bar" id="layers"></div>
<div class="legend" id="legend"></div>
<div class="campus" id="campus"></div>
<footer id="honesty"></footer>
</div>
<div id="ov"></div>
<aside id="panel" aria-label="hall detail"><button id="close"></button><div id="pbody"></div></aside>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const STATE_COLORS = {live:'var(--good)', calibrating:'var(--steel)', schema_ok:'var(--warn)', draft:'var(--rule)'};
const STATES = ['live','calibrating','schema_ok','draft'];
let loc = 'en';
const t = (k) => D.i18n[loc].strings[k] ?? D.i18n.en.strings[k] ?? k;
const fmt = (s, v) => s.replace(/\\{(\\w+)\\}/g, (m,k) => k in v ? v[k] : m);
const F = (n) => n.toLocaleString('en-US');
const dname = (k) => D.i18n[loc].districts[k]?.name ?? D.districts[k].name;
const dtag = (k) => D.i18n[loc].districts[k]?.tagline ?? D.districts[k].tagline;

function liveShare(h){ const c=h.census; const tot=STATES.reduce((a,s)=>a+c[s],0); return c.live/tot; }

function render(){
  const i = D.i18n[loc];
  document.documentElement.lang = loc;
  document.documentElement.dir = i.dir;
  document.getElementById('figs').innerHTML =
    `<span><b>${F(D.ledger.halls)}</b> ${fmt(t('figures.halls'),{n:''}).trim()}</span>`+
    `<span><b>${F(D.ledger.total_modules)}</b> ${fmt(t('figures.modules'),{n:''}).trim()}</span>`+
    `<span><b>${D.ledger.districts}</b> ${fmt(t('figures.districts'),{n:''}).trim()}</span>`;
  const LAYERS = [['districts','map.layer.districts'],['pipeline','map.layer.pipeline'],
                  ['modules','map.layer.modules'],['stations','map.layer.stations']];
  document.getElementById('layers').innerHTML =
    `<span class="lbl">${t('map.layers')}:</span>` +
    LAYERS.map(([k,lk]) => `<label class="tgl"><input type="checkbox" data-l="${k}" ${document.body.classList.contains('L-'+k)?'checked':''}>${t(lk)}</label>`).join('') +
    `<select id="lang" aria-label="${t('language.select')}">` +
    Object.entries(D.i18n).map(([c,v]) => `<option value="${c}" ${c===loc?'selected':''}>${v.language}</option>`).join('') + `</select>`;
  document.getElementById('legend').innerHTML =
    STATES.map(s => `<span><span class="sw" style="background:${STATE_COLORS[s]}"></span>${i.states[s]}</span>`).join('') +
    `<span><span class="sw" style="background:var(--mark);border-radius:50%"></span>${t('map.layer.stations')}</span>`;
  document.getElementById('campus').innerHTML = Object.entries(D.districts).map(([k,d]) => `
    <section class="district" style="--hue:${d.hue}">
      <h2 style="border-color:hsl(${d.hue} 62% 58%)">${dname(k)} · ${d.halls.length}</h2>
      <p class="tag">${dtag(k)}</p>
      <div class="halls">` +
      d.halls.map(slug => { const h = D.halls.find(x=>x.slug===slug);
        const pipe = document.body.classList.contains('L-pipeline');
        const hueOn = document.body.classList.contains('L-districts');
        const bg = pipe ? `background:color-mix(in oklab, var(--good) ${Math.round(liveShare(h)*38)}%, var(--sunk))` : '';
        const bd = hueOn ? `border-inline-start-color:hsl(${d.hue} 62% 55%)` : '';
        const bar = STATES.map(s => `<i style="width:${100*h.census[s]/100}%;background:${STATE_COLORS[s]}"></i>`).join('');
        const badge = h.stations.length ? `<span class="badge">${h.stations.length}</span>` : '';
        return `<button class="hall" data-slug="${slug}" style="${bg};${bd}">${badge}<span class="nm">${h.name}</span><span class="stbar">${bar}</span></button>`;
      }).join('') + `</div></section>`).join('');
  document.getElementById('honesty').textContent =
    t('honesty.taxonomy') + ' ' + t('honesty.modules') + ' ' + t('honesty.content');
  document.getElementById('close').textContent = t('ui.close');
}

function planSVG(h){
  const U = 26, W = 12*U, H = h.depth*U;
  const dh = D.districts[h.district].hue;
  let dots = '';
  const stns = h.stations.map(id => D.stations[id]);
  const byRoom = {};
  stns.forEach(s => { (byRoom[s.room] ??= []).push(s); });
  const rects = h.rooms.map(r => {
    const list = byRoom[r.label] ?? [];
    const dot = list.map((s,j) =>
      `<circle cx="${r.x*U + (j+1)*(r.w*U)/(list.length+1)}" cy="${(r.y+r.h/2)*U + 6}" r="5.5" fill="var(--mark)"><title>${s.name}</title></circle>`).join('');
    return `<g><rect x="${r.x*U+1}" y="${r.y*U+1}" width="${r.w*U-2}" height="${r.h*U-2}" rx="3"
      fill="hsl(${dh} 25% 16%)" stroke="hsl(${dh} 30% 32%)"/>
      <text x="${r.x*U+7}" y="${r.y*U+16}" font-size="10.5" fill="var(--ink)">${r.label}</text>
      <text x="${r.x*U+7}" y="${r.y*U+29}" font-size="9" fill="var(--muted)">${D.i18n[loc].strands[r.strand]}</text>${dot}</g>`;
  }).join('');
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;background:var(--sunk);border-radius:8px">${rects}</svg>`;
}

function openHall(slug){
  const h = D.halls.find(x=>x.slug===slug);
  const i = D.i18n[loc];
  const tot = STATES.reduce((a,s)=>a+h.census[s],0);
  const cbar = STATES.map(s=>`<i style="width:${100*h.census[s]/tot}%;background:${STATE_COLORS[s]}"></i>`).join('');
  const ckey = STATES.map(s=>`<span>${i.states[s]}: ${h.census[s]} ${t('unit.levels')}</span>`).join('');
  const stns = h.stations.map(id => D.stations[id]).map(s => `
    <div class="stn" id="${s.station_id}">
      <button data-st="${s.station_id}"><span class="dot"></span><b>${s.name}</b>
        <span class="rm">${s.room} · ${i.tiers[s.tier]}</span></button>
      <div class="body"><p>${s.lesson}</p>
        <b>${t('station.checklist')}</b><ul>${s.checklist.map(c=>`<li>${c}</li>`).join('')}</ul>
        <div class="q"><b>${t('station.quiz')}:</b> ${s.quiz.question}
          ${s.quiz.options.map((o,j)=>`<button class="opt" data-ok="${o.correct?1:0}">${o.label}</button>`).join('')}</div>
      </div></div>`).join('');
  const lat = `<div class="lattice"><div class="hd"></div>` +
    Object.entries(i.tiers).map(([,v])=>`<div class="hd">${v}</div>`).join('') +
    Object.entries(i.strands).map(([sk,sv]) => `<div class="hd">${sv}</div>` +
      ['fundamentals','applied','mastery'].map(tier => {
        const seeded = h.stations.some(id => D.stations[id].strand===sk && D.stations[id].tier===tier);
        return `<div class="${seeded?'on':''}">${seeded?'●':'·'}</div>`; }).join('')).join('');
  document.getElementById('pbody').innerHTML = `
    <h2>${h.name}</h2><p class="focus">${h.focus}</p>
    <span class="chip">${dname(h.district)}</span>
    <span class="chip">${F(h.lessons)} · ${fmt(t('figures.lessons'),{n:''}).trim()}</span>
    <span class="chip">${fmt(t('figures.modules'),{n:F(h.modules)})}</span>
    <h3>${t('map.layer.pipeline')}</h3><div class="cbar">${cbar}</div><div class="ckey">${ckey}</div>
    <h3>${t('hall.rooms')}</h3>${planSVG(h)}
    ${stns ? `<h3>${t('hall.stations')} (${h.stations.length})</h3>${stns}` : ''}
    <h3>${t('hall.skills')}</h3>${lat}`;
  document.body.classList.add('open');
}

document.addEventListener('click', (e) => {
  const hall = e.target.closest('.hall');
  if (hall) return openHall(hall.dataset.slug);
  if (e.target.closest('#close') || e.target.id === 'ov')
    return document.body.classList.remove('open');
  const st = e.target.closest('.stn > button');
  if (st) return st.parentElement.classList.toggle('open');
  const opt = e.target.closest('.opt');
  if (opt) { opt.parentElement.querySelectorAll('.opt').forEach(o =>
      o.classList.toggle('ok', o.dataset.ok==='1'));
    if (opt.dataset.ok!=='1') opt.classList.add('bad'); return; }
});
document.addEventListener('change', (e) => {
  if (e.target.dataset?.l) { document.body.classList.toggle('L-'+e.target.dataset.l, e.target.checked); render(); }
  if (e.target.id === 'lang') { loc = e.target.value; render(); }
});
render();
</script>
</body>
</html>
'''

page = page.replace('__DATA__', DATA)
out = HERE / 'trade_craft_interactive.html'
out.write_text(page)
n_st = stations_reg['count']
print(f"written: {len(page):,} bytes | {L['halls']} halls | {n_st} stations | "
      f"{len(I18N)} locales")
