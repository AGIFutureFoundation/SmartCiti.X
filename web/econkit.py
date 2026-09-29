#!/usr/bin/env python3
"""City-life panel kit (SIMS). Embeddable, no network, local state only.

  from econkit import ECON_CSS, econ_panel_html, econ_js
  econ_panel_html()        -> the empty accessible panel shell (<section data-tc-econ>)
  econ_js(fips='all')      -> one <script>: the ledger core from economy/core.mjs (byte-for-byte between
                              ECON_CORE markers) + the economy registry subset + the econ.* strings of all 8 locales.

PLAY COINS only - not money. Lots are AUTHORED game lots, not real properties. The kit never calls a quest
completion and never writes any completion record; it only emits events (see $SP/ECON_CONTRACT.md).
Fail closed: a missing registry field or i18n key stops the build with a named error.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / 'economy' / 'registry' / 'economy.json'
CORE = ROOT / 'economy' / 'core.mjs'
LOCALES = ['en', 'es', 'fr', 'de', 'pt', 'zh', 'hi', 'ar']
KEYS = ['title', 'not_money', 'lots_note', 'play_note', 'coins', 'balance', 'day', 'nearby', 'none_near', 'mine',
        'rent', 'buy', 'per_day', 'open', 'hire', 'practice', 'next_day', 'reset', 'reset_confirm', 'not_saved',
        'refused', 'zone_commercial', 'zone_residential', 'staff', 'skills', 'business']
NEAR_M = 250


class EconError(Exception):
    pass


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise EconError('econkit: missing %s in %s' % (k, where))
    return d[k]


def core_src():
    src = CORE.read_text()
    a, b = '/* ECON_CORE:BEGIN */', '/* ECON_CORE:END */'
    if a not in src or b not in src:
        raise EconError('econkit: ECON_CORE markers missing in economy/core.mjs')
    return src[src.index(a):src.index(b) + len(b)]


def strings():
    out = {}
    for loc in LOCALES:
        s = _need(json.loads((ROOT / 'i18n' / 'locales' / (loc + '.json')).read_text()), 'strings', loc)
        out[loc] = {k: _need(s, 'econ.' + k, 'i18n/locales/%s.json' % loc) for k in KEYS}
    return out


def registry_subset(fips='all'):
    reg = json.loads(REG.read_text())
    pars = _need(reg, 'parishes', 'economy.json')
    want = list(pars) if fips == 'all' else list(fips)
    sub = {}
    for f in want:
        p = _need(pars, f, 'economy.json#parishes')
        sub[f] = {'name': _need(p, 'name', f), 'lots': [
            {k: _need(l, k, l['id'] if 'id' in l else f) for k in
             ('id', 'parish', 'zone', 'x', 'z', 'size_m', 'allowed', 'rent_coins_per_day', 'buy_coins', 'provenance')}
            for l in _need(p, 'lots', f)]}
    bkeys = ('id', 'label', 'trade_id', 'zone', 'setup_coins', 'income_coins_per_day_skilled',
             'income_coins_per_day_unskilled', 'staff_bonus_coins_per_day', 'staff_wage_coins_per_day', 'max_staff')
    return {'source_stamp': _need(reg, 'source_stamp', 'economy.json'),
            'coin_rules': _need(reg, 'coin_rules', 'economy.json'),
            'business_types': [{k: _need(b, k, 'business_types') for k in bkeys} for b in _need(reg, 'business_types', 'economy.json')],
            'parishes': sub}


ECON_CSS = """
.tc-econ{border:1px solid var(--line,#8886);border-radius:10px;padding:12px 14px;max-width:420px;font:14px/1.4 system-ui,sans-serif;background:var(--card,var(--panel,#fff));color:var(--ink,#111)}
.tc-econ h2{font-size:1.05rem;margin:0 0 4px}.tc-econ h3{font-size:.92rem;margin:10px 0 4px}
.tc-econ .tc-econ-note{font-size:.8rem;opacity:.85;margin:2px 0}
.tc-econ ul{list-style:none;margin:0;padding:0}.tc-econ li{padding:4px 0;border-top:1px solid var(--line,#8883)}
.tc-econ button,.tc-econ select{font:inherit;min-height:32px;margin:2px 4px 2px 0}
.tc-econ .tc-econ-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.tc-econ [role=status]{min-height:1.2em;font-size:.85rem}
"""


def econ_panel_html():
    return ('<section class="tc-econ" id="tc-econ" data-tc-econ aria-labelledby="tc-econ-h">'
            '<h2 id="tc-econ-h" data-econ-t="title">City life</h2>'
            '<p class="tc-econ-note" data-econ-t="not_money">Play coins - not money.</p>'
            '<p class="tc-econ-note" data-econ-t="lots_note"></p><p class="tc-econ-note" data-econ-t="play_note"></p>'
            '<div class="tc-econ-body"></div><div role="status" aria-live="polite" class="tc-econ-live"></div></section>')


GLUE = r"""
(function(){
var REG=__REG__, STR=__STR__, NEAR=__NEAR__;
var R=econIndex(REG), store=null, s=null, saved=false, el=null, lang='en', parish=null, px=null, pz=null, lastMove=0, timer=null, subs={};
function st(){try{return window.localStorage;}catch(e){return null;}}
function t(k){var L=STR[lang]||STR.en;return L[k];}
function emit(list){(list||[]).forEach(function(e){var n=e[0],d=e[1];(subs[n]||[]).forEach(function(fn){try{fn(d);}catch(x){}});
  try{window.dispatchEvent(new CustomEvent('tc-econ',{detail:Object.assign({name:n},d)}));}catch(x){}});}
function commit(r){saved=econSave(store,s)&&saved;emit(r.events);if(!r.ok){say(t('refused'));}render();return r;}
function say(m){if(el){var l=el.querySelector('.tc-econ-live');if(l)l.textContent=m;}}
function esc(x){return String(x).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function btn(act,id,label,extra){return '<button type="button" data-econ-act="'+act+'" data-econ-id="'+esc(id)+'"'+(extra||'')+'>'+esc(label)+'</button>';}
function lotLine(id){var l=R.lots[id],mine=s.lots[id];var z=t(l.zone==='commercial'?'zone_commercial':'zone_residential');
  var h='<b>'+esc(id)+'</b> - '+esc(z)+' ('+l.size_m[0]+' x '+l.size_m[1]+' m) ';
  if(!mine){h+=btn('rent',id,t('rent')+' '+l.rent_coins_per_day+' '+t('coins')+' '+t('per_day'))+btn('buy',id,t('buy')+' '+l.buy_coins+' '+t('coins'));}
  else{h+='<i>'+esc(mine.mode)+'</i> ';if(mine.mode==='rent')h+=btn('buy',id,t('buy')+' '+l.buy_coins+' '+t('coins'));
    if(l.allowed.indexOf('shop')>=0&&!mine.business){h+='<label>'+esc(t('business'))+' <select data-econ-sel="'+esc(id)+'">'+REG.business_types.map(function(b){return '<option value="'+b.id+'">'+esc(b.label)+' ('+b.setup_coins+' '+esc(t('coins'))+')</option>';}).join('')+'</select></label>'+btn('open',id,t('open'));}
    if(mine.business){var b=R.btypes[mine.business];h+=esc(b.label)+' - '+esc(t('staff'))+' '+mine.staff+'/'+b.max_staff+' '+btn('hire',id,t('hire'));
      if(b.trade_id&&!s.skills[b.trade_id])h+=btn('practice',b.trade_id,t('practice'));}}
  return '<li>'+h+'</li>';}
function render(){if(!el)return;var body=el.querySelector('.tc-econ-body');if(!body)return;
  el.querySelectorAll('[data-econ-t]').forEach(function(n){n.textContent=t(n.getAttribute('data-econ-t'));});
  var near=(parish&&px!==null)?econNear(R,parish,px,pz,NEAR):[];
  var h='<div class="tc-econ-bar"><span>'+esc(t('balance'))+': <b>'+s.coins+'</b> '+esc(t('coins'))+'</span><span>'+esc(t('day'))+' '+s.day+'</span>'+
    btn('tick','','▶ '+t('next_day'))+btn('reset','',t('reset'))+'</div>';
  if(!saved)h+='<p class="tc-econ-note" data-econ-unsaved>'+esc(t('not_saved'))+'</p>';
  h+='<h3>'+esc(t('nearby'))+'</h3>'+(near.length?'<ul>'+near.map(function(n){return lotLine(n.id);}).join('')+'</ul>':'<p class="tc-econ-note">'+esc(t('none_near'))+'</p>');
  var mine=Object.keys(s.lots).sort();if(mine.length)h+='<h3>'+esc(t('mine'))+'</h3><ul>'+mine.map(lotLine).join('')+'</ul>';
  var sk=Object.keys(s.skills);if(sk.length)h+='<p class="tc-econ-note">'+esc(t('skills'))+': '+sk.map(esc).join(', ')+'</p>';
  body.innerHTML=h;}
function onClick(ev){var b=ev.target.closest&&ev.target.closest('[data-econ-act]');if(!b||!el.contains(b))return;var a=b.getAttribute('data-econ-act'),id=b.getAttribute('data-econ-id');
  if(a==='rent')commit(econRent(s,R,id));else if(a==='buy')commit(econBuy(s,R,id));
  else if(a==='open'){var sel=el.querySelector('select[data-econ-sel="'+id+'"]');commit(econOpen(s,R,id,sel.value));}
  else if(a==='hire')commit(econHire(s,R,id));else if(a==='practice')commit(econPractice(s,R,id));
  else if(a==='tick')commit(econTick(s,R,1));else if(a==='reset'){if(window.confirm(t('reset_confirm')))api.reset();}}
var api={
  mountEcon:function(node,opts){opts=opts||{};el=node||document.querySelector('[data-tc-econ]');if(!el)throw new Error('econ: no panel element');
    lang=opts.lang||document.documentElement.lang||'en';if(!STR[lang])lang='en';
    store=('storage' in opts)?opts.storage:st();var L=econLoad(store,R);s=L.s;saved=L.saved&&econSave(store,s);
    if(opts.parish)parish=String(opts.parish);if(!el.__econ){el.addEventListener('click',onClick);el.__econ=1;}
    if(!timer)timer=setInterval(function(){if(!document.hidden&&el&&el.isConnected)commit(econTick(s,R,1));},R.rules.day_ms);
    render();return api;},
  onPlayerMove:function(p,x,z){var now=Date.now();parish=String(p);px=+x;pz=+z;if(now-lastMove<250)return;lastMove=now;render();},
  lotMarkers:function(p){return (R.byParish[String(p)]||[]).map(function(id){var l=R.lots[id],m=s&&s.lots[id];
    return {id:id,x:l.x,z:l.z,w:l.size_m[0],d:l.size_m[1],zone:l.zone,status:!m?'free':m.business?'business':(m.mode==='own'?'owned':'rented'),label:'AUTHORED game lot'};});},
  state:function(){return JSON.parse(JSON.stringify(s));},
  on:function(n,fn){(subs[n]=subs[n]||[]).push(fn);return api;},
  tick:function(n){return commit(econTick(s,R,n||1));},
  reset:function(){econClear(store);s=econFresh(R);saved=econSave(store,s);emit([['reset',{}]]);render();say('');}
};
window.TCEcon=api;
})();
"""


def econ_js(fips='all'):
    reg = registry_subset(fips)
    glue = (GLUE.replace('__REG__', json.dumps(reg, ensure_ascii=False, separators=(',', ':')))
                .replace('__STR__', json.dumps(strings(), ensure_ascii=False, separators=(',', ':')))
                .replace('__NEAR__', str(NEAR_M)))
    body = core_src() + '\n' + glue
    if '</script' in body.lower():
        raise EconError('econkit: </script in payload')
    return '<script data-tc-econ-kit>\n' + body + '</script>'


if __name__ == '__main__':
    import sys
    js = econ_js('all')
    if len(sys.argv) > 1 and sys.argv[1] == '--harness':
        out = pathlib.Path(sys.argv[2])
        out.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                       '<title>Econ harness</title><style>' + ECON_CSS + '</style></head><body><main><h1>Econ harness</h1>' + econ_panel_html() + '</main>' + js + '</body></html>')
        print('wrote', out)
    else:
        print(len(js), 'bytes')
