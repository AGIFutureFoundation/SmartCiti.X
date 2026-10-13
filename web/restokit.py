"""
restokit - embeddable runner for the Bay restoration TRAINING SCENARIOS
(restoration/registry/scenarios.json, built by restoration/scenarios.py).

Pure data + one inline script. A host page (BAY / DEEP / ENV own theirs)
mounts it; this module edits no page. API (see RESTORE_CONTRACT.md):
  RESTO                       loaded registry (fails closed on missing fields)
  scenarios_for_site(site_id) -> [scenario]   (site-linked, exact match)
  generic_scenarios()         -> [scenario]   (water-quality, unlinked)
  scenarios_json(rows)        -> compact JSON for the page script
  RESTO_CSS                   scoped .rk-* CSS, theme tokens only
  RESTO_JS                    rkScore(sc, run) (same arithmetic as scenarios.py score_run)
                              and rkMount(el, scenarios, L)  L = (k, en) => t('resto.' + k)
  honesty_line()              the one-line label to render once per mount
A run is practice: it is scored in the browser, kept nowhere, and never
enters a completion record.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / 'restoration' / 'registry' / 'scenarios.json'
SC_FIELDS = ('id', 'site', 'type', 'family', 'title', 'label', 'provenance', 'lessons', 'crew',
             'steps', 'tools', 'ppe', 'hazards', 'safety_gates', 'forbidden', 'fixtures')


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise KeyError(f'restokit: {where} has no "{k}"')
    return d[k]


def _load():
    if not REG.exists():
        raise SystemExit('restokit: restoration/registry/scenarios.json is missing - run python3 restoration/scenarios.py')
    reg = json.loads(REG.read_text())
    for k in ('honesty', 'funding_context', 'rubric', 'scenarios', 'generic'):
        _need(reg, k, 'scenarios.json')
    for sc in reg['scenarios'] + reg['generic']:
        for f in SC_FIELDS:
            _need(sc, f, sc['id'] if 'id' in sc else 'scenario')
    return reg


RESTO = _load()


def scenarios_for_site(site_id):
    return [s for s in RESTO['scenarios'] if s['site'] == site_id]


def generic_scenarios():
    return list(RESTO['generic'])


def honesty_line():
    h = RESTO['honesty']
    return f"{h['label']} - {h['lessons']}. {h['play']}"


def scenarios_json(rows):
    keep = ('id', 'site', 'type', 'title', 'label', 'lessons', 'crew', 'steps', 'tools', 'ppe',
            'hazards', 'safety_gates', 'forbidden')
    return json.dumps([{k: s[k] for k in keep} for s in rows], ensure_ascii=False, separators=(',', ':'))


RESTO_CSS = '''
.rk-box{border:1px solid var(--rule);background:var(--panel);color:var(--ink);padding:.75rem;border-radius:.5rem;max-width:100%}
.rk-box h3{margin:.2rem 0 .4rem;font-size:1rem}
.rk-label{color:var(--muted);font-size:.85rem;margin:.2rem 0 .5rem}
.rk-row{display:flex;flex-wrap:wrap;gap:.35rem;margin:.35rem 0}
.rk-row button,.rk-row label,.rk-row select{font:inherit;font-size:.85rem;border:1px solid var(--rule);background:var(--panel);color:var(--ink);border-radius:.35rem;padding:.25rem .45rem}
.rk-row button[aria-pressed="true"]{border-color:var(--mark);outline:2px solid var(--mark)}
.rk-seq{color:var(--muted);font-size:.8rem;word-break:break-word}
.rk-out{margin-top:.5rem;font-size:.9rem;border-top:1px solid var(--rule);padding-top:.4rem}
'''

RESTO_JS = r'''
function rkLis(a){const b=a.map(()=>1);for(let i=0;i<a.length;i++)for(let j=0;j<i;j++)if(a[j]<a[i]&&b[j]+1>b[i])b[i]=b[j]+1;return a.length?Math.max(...b):0;}
function rkScore(sc, run){
  const seq=run.sequence, ids=sc.steps.map((s)=>s.id), first={};
  seq.forEach((t,i)=>{ if(!(t in first)) first[t]=i; });
  let gates=true;
  for(const g of sc.safety_gates){ const gi=first['gate:'+g.id], si=first['step:'+g.before_step];
    if(gi===undefined || (si!==undefined && gi>si)) gates=false; }
  const forbidden=!seq.some((t)=>t.startsWith('forbidden:'));
  const done=[]; for(const t of seq){ if(t.startsWith('step:')){ const k=ids.indexOf(t.slice(5)); if(k>=0 && !done.includes(k)) done.push(k);} }
  const order=Math.floor(rkLis(done)*100/ids.length);
  const ppe=Math.floor(sc.ppe.filter((p)=>run.ppe.includes(p)).length*100/sc.ppe.length);
  const crew=Math.floor(sc.crew.filter((r)=>r.role in run.crew && run.crew[r.role]===r.trade).length*100/sc.crew.length);
  const score=Math.floor((order*5+crew*2+ppe*3)/10);
  return {gates, forbidden, ppe, order, crew, score, pass: gates && forbidden && ppe===100 && order>=80 && crew===100};
}
function rkMount(el, scenarios, L){
  const esc=(s)=>String(s).replace(/[&<>"]/g,(c)=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const trades=[...new Set(scenarios.flatMap((s)=>s.crew.map((r)=>r.trade)))].sort();
  el.innerHTML=scenarios.map((sc,i)=>{
    const acts=[...sc.steps.map((s)=>['step:'+s.id,s.text]),...sc.safety_gates.map((g)=>['gate:'+g.id,g.text]),
      ...sc.forbidden.map((f)=>['forbidden:'+f.id,f.text])].sort((a,b)=>a[0].split(':')[1]<b[0].split(':')[1]?-1:1);
    return `<section class="rk-box" data-rk="${i}"><h3>${esc(sc.title)}</h3>
<p class="rk-label">${esc(sc.label)} &middot; ${esc(L('lessons','lessons'))}: ${esc(sc.lessons)}</p>
<p class="rk-label">${esc(L('hazards','Hazards'))}: ${sc.hazards.map((h)=>esc(h.text)).join('; ')}</p>
<p class="rk-label">${esc(L('tools','Tools'))}: ${sc.tools.map(esc).join(', ')}</p>
<div class="rk-row" data-rk-ppe>${esc(L('ppe','PPE'))}: ${sc.ppe.map((p)=>`<label><input type="checkbox" value="${esc(p)}"> ${esc(p)}</label>`).join('')}</div>
<div class="rk-row" data-rk-crew>${esc(L('crew','Crew'))}: ${sc.crew.map((r)=>`<label>${esc(r.role)} <select data-role="${esc(r.role)}"><option value="">-</option>${trades.map((t)=>`<option>${esc(t)}</option>`).join('')}</select></label>`).join('')}</div>
<div class="rk-row" data-rk-acts>${acts.map(([k,t])=>`<button type="button" data-act="${esc(k)}">${esc(t)}</button>`).join('')}</div>
<p class="rk-seq" data-rk-seq></p>
<div class="rk-row"><button type="button" data-rk-score>${esc(L('run','Score this run'))}</button><button type="button" data-rk-reset>${esc(L('reset','Reset'))}</button></div>
<div class="rk-out" data-rk-out aria-live="polite"></div></section>`;}).join('');
  el.querySelectorAll('[data-rk]').forEach((box)=>{
    const sc=scenarios[Number(box.dataset.rk)]; let seq=[];
    const show=()=>{ box.querySelector('[data-rk-seq]').textContent=seq.length+' '+L('actions','actions'); };
    box.querySelectorAll('[data-act]').forEach((b)=>b.addEventListener('click',()=>{ seq.push(b.dataset.act); b.setAttribute('aria-pressed','true'); show(); }));
    box.querySelector('[data-rk-reset]').addEventListener('click',()=>{ seq=[]; box.querySelectorAll('[data-act]').forEach((b)=>b.removeAttribute('aria-pressed')); box.querySelector('[data-rk-out]').textContent=''; show(); });
    box.querySelector('[data-rk-score]').addEventListener('click',()=>{
      const run={sequence:seq, ppe:[...box.querySelectorAll('[data-rk-ppe] input:checked')].map((c)=>c.value),
        crew:Object.fromEntries([...box.querySelectorAll('[data-rk-crew] select')].filter((s)=>s.value).map((s)=>[s.dataset.role,s.value]))};
      const r=rkScore(sc,run);
      box.querySelector('[data-rk-out]').textContent=(r.pass?L('pass','Pass'):L('fail','Not yet'))+' - '+L('score','Score')+' '+r.score
        +' | '+L('gates','gates')+' '+(r.gates?'ok':'x')+' | '+L('forbidden','forbidden')+' '+(r.forbidden?'ok':'x')
        +' | order '+r.order+'% | PPE '+r.ppe+'% | crew '+r.crew+'%';
    });
  });
}
'''


# ---------------------------------------------------------------- world mount --
# A world page whose landmarks include restoration sites mounts the runner with
# mount_for_landmarks(): each landmark whose name is a scenario site's own
# registry name gets a "Run training scenario" action (the in-world marker
# button and the landmark list row both open that site's scenarios).
I18N_KEYS = ('title', 'lessons', 'hazards', 'tools', 'ppe', 'crew', 'run', 'reset', 'actions', 'pass', 'fail',
             'score', 'gates', 'forbidden', 'play', 'open', 'close')


def i18n_for(loc):
    """resto.* strings for one locale, read from i18n/locales (fails closed on a missing key)"""
    s = _need(json.loads((ROOT / 'i18n' / 'locales' / f'{loc}.json').read_text()), 'strings', f'{loc}.json')
    return {'resto.' + k: _need(s, 'resto.' + k, f'{loc}.json strings') for k in I18N_KEYS}


def mount_for_landmarks(landmarks, catalog_id):
    """landmarks: [(landmark_id, name)] for restoration-site landmarks. Returns (lm_to_site, css, html) where
    html is the panel + data + script to put before </body>; catalog_id names the page's embedded i18n JSON
    ({loc: {strings: {...}}}) that must carry i18n_for(loc) keys; the locale is read from <html lang> at click time."""
    by_name = {}
    for s in RESTO['scenarios']:
        if s['site_name'] not in by_name:
            by_name[s['site_name']] = s['site']
    lm_site = {}
    for lid, name in landmarks:
        if name not in by_name:
            raise KeyError(f'restokit: landmark {lid} ({name}) names no scenario site')
        lm_site[lid] = by_name[name]
    sites = sorted(set(lm_site.values()))
    data = {'lm': lm_site, 'sc': {sid: json.loads(scenarios_json(scenarios_for_site(sid))) for sid in sites}}
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    css = RESTO_CSS + '''
.rk-panel{position:fixed;inset:auto 0 0 0;max-height:78vh;overflow:auto;z-index:60;background:var(--panel);color:var(--ink);border-top:2px solid var(--mark);padding:.75rem 16px}
.rk-panel[hidden]{display:none}
.rk-panel h2{margin:.2rem 0;font-size:1.05rem}
.rk-open{font:inherit;font-size:.8rem;margin-left:.35rem;border:1px solid var(--mark);background:var(--panel);color:var(--ink);border-radius:.35rem;padding:.1rem .4rem}
'''
    html = ('<section id="resto-sims" class="rk-panel" hidden role="dialog" aria-modal="false" aria-labelledby="rk-h">'
            '<h2 id="rk-h" data-rk-title></h2><p class="rk-label" data-rk-play></p>'
            '<div class="rk-row"><button type="button" data-rk-close></button></div><div data-rk-host></div></section>\n'
            f'<script type="application/json" id="resto-data">{blob}</script>\n'
            '<script>\n' + RESTO_JS + '''
(function () {
  const RD = JSON.parse(document.getElementById('resto-data').textContent);
  const CAT = JSON.parse(document.getElementById(''' + json.dumps(catalog_id) + ''').textContent);
  const L = (k) => { const loc = Object.hasOwn(CAT, document.documentElement.lang) ? document.documentElement.lang : 'en';
    const s = CAT[loc].strings['resto.' + k]; if (typeof s !== 'string') throw new Error('restokit: no resto.' + k + ' in ' + loc); return s; };
  const panel = document.getElementById('resto-sims');
  function openSite(site, from) {
    const rows = RD.sc[site]; if (!rows) throw new Error('restokit: no scenarios for ' + site);
    panel.querySelector('[data-rk-title]').textContent = L('title');
    panel.querySelector('[data-rk-play]').textContent = L('play');
    panel.querySelector('[data-rk-close]').textContent = L('close');
    panel.dataset.site = site; panel.hidden = false;
    rkMount(panel.querySelector('[data-rk-host]'), rows, (k) => L(k));
    panel._from = from; panel.querySelector('[data-rk-close]').focus();
  }
  panel.querySelector('[data-rk-close]').addEventListener('click', () => { panel.hidden = true; if (panel._from && panel._from.isConnected) panel._from.focus(); });
  document.addEventListener('click', (e) => {
    const run = e.target.closest('[data-resto-run]');
    if (run) { openSite(run.dataset.restoRun, run); return; }
    const lm = e.target.closest('.lbl.lm[data-landmark]');
    if (lm && Object.hasOwn(RD.lm, lm.dataset.landmark)) openSite(RD.lm[lm.dataset.landmark], lm);
  });
  const labelRuns = () => { for (const b of document.querySelectorAll('[data-resto-run]')) b.textContent = L('open'); };
  addEventListener('load', labelRuns);
  const h = decodeURIComponent(location.hash.slice(1));
  if (h.startsWith('resto=')) addEventListener('load', () => openSite(h.slice(6), null));
})();
</script>\n''')
    return lm_site, css, html
