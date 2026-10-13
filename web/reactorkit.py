"""web/reactorkit.py - the embeddable Reactor live-view panel ("Holodeck live view (Reactor)").

Contract: $SP/REACTOR_CONTRACT.md (mount API, events, sizes, off state). Everything the panel does is
read from reactor/registry/reactor.json; a missing field stops the build (ReactorKitError).

Off by default. No SDK byte, no request and no storage until the learner presses Connect. The page
NEVER takes, stores or sees an API key: Connect asks this site's Worker (POST /api/reactor/token) for a
short-lived scoped JWT, then dynamic-imports the vendored SDK (web/vendor/reactor/, sha512-pinned) and
connects with its imperative Reactor class. Without the endpoint the panel says so and stays off.
api.reactor.inc is unreachable from the environment that built this: no live session was ever opened.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / 'reactor' / 'registry' / 'reactor.json'


class ReactorKitError(Exception):
    pass


def _need(d, *path):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            raise ReactorKitError('reactorkit: reactor registry is missing ' + '.'.join(path))
        cur = cur[k]
    return cur


def _registry():
    if not REG.is_file():
        raise ReactorKitError('reactorkit: reactor/registry/reactor.json is missing - run python3 reactor/build.py')
    return json.loads(REG.read_text())


def reactor_import_entries(base):
    """Comma-led import-map entries to splice into a host's existing "imports" object."""
    reg = _registry()
    vd = _need(reg, 'sdk', 'vendor_dir')
    if not vd.startswith('web/'):
        raise ReactorKitError('reactorkit: sdk.vendor_dir must live under web/')
    rel = base + vd[len('web/'):] + '/'
    imap = _need(reg, 'sdk', 'import_map')
    return ''.join(',' + json.dumps(k) + ':' + json.dumps(rel + v) for k, v in sorted(imap.items()))


def reactor_importmap_tag(base):
    return '<script type="importmap">{"imports":{' + reactor_import_entries(base)[1:] + '}}</script>'


REACTOR_CSS = """
.rk-float{position:fixed;left:12px;bottom:12px;z-index:40}
#rk-panel{font:14px/1.4 system-ui,sans-serif;color:#e8eef5;max-width:calc(100vw - 24px)}
#rk-panel .rk-chip{min-height:44px;padding:0 14px;border-radius:22px;border:1px solid #3b556e;background:#0f1b27;color:#e8eef5;font:inherit;cursor:pointer}
#rk-panel .rk-card{box-sizing:border-box;width:min(360px,calc(100vw - 24px));max-height:calc(100vh - 90px);overflow:auto;margin-top:8px;padding:12px;border-radius:12px;background:#0f1b27;border:1px solid #3b556e}
#rk-panel .rk-card[hidden]{display:none}
#rk-panel video{width:100%;aspect-ratio:16/9;background:#05090d;border-radius:8px;display:block}
#rk-panel video[hidden]{display:none}
#rk-panel button:disabled{opacity:.45;cursor:default}
#rk-panel details{margin-top:6px}
#rk-panel summary{min-height:32px;line-height:32px;cursor:pointer;color:#cfe0ef;font-size:13px}
#rk-panel .rk-row{display:flex;gap:8px;align-items:center;margin-top:8px;flex-wrap:wrap}
#rk-panel .rk-row button{min-height:44px;min-width:44px;padding:0 12px;border-radius:8px;border:1px solid #3b556e;background:#162636;color:#e8eef5;font:inherit;cursor:pointer}
#rk-panel .rk-status{font-weight:600}
#rk-panel .rk-small{font-size:12px;color:#a9b8c6;margin:6px 0 0}
#rk-panel .rk-err{color:#ffb4a8}
"""


def reactor_panel(base):
    reg = _registry()
    cfg = {
        'model': _need(reg, 'model'),
        'endpoint': base + '..' + _need(reg, 'token', 'endpoint'),
        'sdk': base + _need(reg, 'sdk', 'vendor_dir')[len('web/'):] + '/' + _need(reg, 'sdk', 'entry'),
        'max_seconds': _need(reg, 'session', 'max_seconds'),
        'disconnect_on_hidden': _need(reg, 'session', 'disconnect_on_hidden'),
        'stats_fields': _need(reg, 'session', 'stats_fields'),
        'parts': _need(reg, 'bridge', 'prompt_parts'),
        'end': _need(reg, 'bridge', 'prompt_end'),
        'fields': _need(reg, 'bridge', 'fields'),
        'commands': _need(reg, 'bridge', 'commands'),
        'no_endpoint': 'Reactor: off - no token endpoint configured',
    }
    hon = _need(reg, 'honesty')
    texts = [_need(hon, k) for k in ('model_output', 'not_live', 'untested', 'play', 'no_key_in_browser')]
    esc = lambda s: s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    notes = ''.join(f'<p class="rk-small">{esc(t)}</p>' for t in texts[1:])
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace('</', '<\\/')
    return f"""<section id="rk-panel" class="rk-float" lang="en" aria-label="Holodeck live view (Reactor)" data-model="{esc(cfg['model'])}">
<button type="button" class="rk-chip" id="rk-toggle" aria-expanded="false" aria-controls="rk-card">Holodeck live view (Reactor)</button>
<div class="rk-card" id="rk-card" hidden>
<video id="rk-video" playsinline muted autoplay hidden></video>
<p class="rk-status" id="rk-status" role="status" aria-live="polite">Reactor: off - press Connect to ask this site for a token</p>
<p class="rk-small" id="rk-stats"></p>
<div class="rk-row"><button type="button" id="rk-connect">Connect</button><button type="button" id="rk-disconnect" disabled>Disconnect</button></div>
<p class="rk-small">{esc(texts[0])}</p>
<details><summary>Where the key goes, and what this is</summary>
<p class="rk-small">Model: {esc(cfg['model'])}. Where your key goes: an operator stores it as the Worker secret REACTOR_API_KEY (or in cloudflare/worker/.dev.vars for local wrangler dev) - never in this page.</p>
{notes}
</details>
</div>
</section>
<script>
(function(){{
'use strict';
var CFG = {cfg_json};
var $ = function(id){{ return document.getElementById(id); }};
var st = 'off', reactor = null, timer = null, ctx = {{}}, imageFn = null, declared = [], sent = [];
function emit(name, detail){{ window.dispatchEvent(new CustomEvent('reactorkit:' + name, {{detail: detail}})); }}
function setStatus(s, text, isErr){{ st = s; var el = $('rk-status'); el.textContent = text; el.className = 'rk-status' + (isErr ? ' rk-err' : ''); emit('status', {{status: s}}); }}
function fail(code, message){{ if (code === 'no_endpoint') setStatus('off', message, false); else setStatus('error', 'Reactor: could not connect - ' + message, true); emit('error', {{code: code, message: message}}); $('rk-connect').disabled = false; $('rk-disconnect').disabled = true; }}
function clip(v, n){{ return typeof v === 'string' ? v.slice(0, n) : ''; }}
function cleanCtx(c){{
  var out = {{}}, f = CFG.fields;
  Object.keys(f).forEach(function(k){{
    var spec = f[k], v = c[k];
    if (spec.type === 'enum') {{ if (spec.values.indexOf(v) >= 0) out[k] = v; }}
    else {{ var s = clip(v, spec.max_chars).trim(); if (s) out[k] = s; }}
  }});
  return out;
}}
function promptText(){{
  var t = '';
  for (var i = 0; i < CFG.parts.length; i++) {{
    var pt = CFG.parts[i], v = ctx[pt.field];
    if (!v) {{ if (pt.required) return null; continue; }}
    t += pt.text.replace('{{' + pt.field + '}}', v);
  }}
  return t + CFG.end;
}}
function declares(name){{ return declared.indexOf(name) >= 0; }}
function readDeclared(){{
  var names = [];
  try {{ var cap = reactor.getCapabilities(); if (cap && Array.isArray(cap.commands)) cap.commands.forEach(function(c){{ if (c && typeof c.name === 'string') names.push(c.name); }}); }} catch (e) {{}}
  try {{ var sc = reactor.getSchema(); if (sc && sc.paths) Object.keys(sc.paths).forEach(function(p){{ names.push(p.replace(/^\\//, '')); }}); }} catch (e) {{}}
  declared = names.filter(function(n, i){{ return names.indexOf(n) === i; }});
  emit('commands', {{declared: declared.slice(), sent: sent.slice()}});
}}
function send(key, value){{
  var c = CFG.commands[key];
  if (!reactor || st !== 'ready' || !c || !declares(c.command)) return Promise.resolve(false);
  var data = {{}}; if (c.param) data[c.param] = value;
  sent.push(c.command); emit('commands', {{declared: declared.slice(), sent: sent.slice()}});
  return reactor.sendCommand(c.command, data).then(function(){{ return true; }}, function(e){{ emit('error', {{code: e && e.code || 'command', message: String(e && e.message || e)}}); return false; }});
}}
function onReady(){{
  readDeclared();
  var p = promptText(), chain = Promise.resolve();
  if (p) chain = chain.then(function(){{ return send('prompt', p); }});
  if (imageFn && declares(CFG.commands.image.command)) chain = chain.then(function(){{ return imageFn(); }}).then(function(blob){{ return blob ? reactor.uploadFile(blob) : null; }}).then(function(ref){{ return ref ? send('image', ref) : false; }});
  chain.then(function(){{ return send('start'); }});
}}
function stats(s){{
  var parts = [], d = {{}};
  CFG.stats_fields.forEach(function(k){{ var v = s && s[k]; d[k] = (typeof v === 'number' && isFinite(v)) ? v : null; }});
  if (d.rtt !== null) parts.push('RTT ' + Math.round(d.rtt) + ' ms');
  if (d.packetLossRatio !== null) parts.push('loss ' + (d.packetLossRatio * 100).toFixed(1) + '%');
  if (d.framesPerSecond !== null) parts.push(Math.round(d.framesPerSecond) + ' fps');
  $('rk-stats').textContent = parts.join(' · ');
  emit('stats', d);
}}
function disconnect(reason){{
  if (timer) {{ clearTimeout(timer); timer = null; }}
  var r = reactor; reactor = null; declared = [];
  $('rk-video').srcObject = null; $('rk-video').hidden = true; $('rk-stats').textContent = '';
  $('rk-connect').disabled = false; $('rk-disconnect').disabled = true;
  if (r) r.disconnect().catch(function(){{}});
  setStatus('disconnected', 'Reactor: disconnected' + (reason ? ' - ' + reason : ''));
}}
function connect(){{
  if (reactor || st === 'connecting') return;           // one session at a time
  $('rk-connect').disabled = true;
  setStatus('connecting', 'Reactor: asking this site for a token...');
  fetch(CFG.endpoint, {{method: 'POST', credentials: 'same-origin', headers: {{'content-type': 'application/json'}}, body: '{{}}'}})
  .then(function(res){{
    return res.text().then(function(t){{
      var j = null; try {{ j = JSON.parse(t); }} catch (e) {{ j = null; }}
      if (res.status === 404 || !j) throw {{code: 'no_endpoint', message: CFG.no_endpoint}};
      if (!res.ok) throw {{code: j.error || ('http_' + res.status), message: (j.detail || ('HTTP ' + res.status)) + (res.status === 429 ? ' - retry in ' + res.headers.get('retry-after') + ' s' : '')}};
      if (typeof j.jwt !== 'string') throw {{code: 'bad_reply', message: 'Reactor: the token endpoint returned no token'}};
      return j.jwt;
    }});
  }}, function(){{ throw {{code: 'no_endpoint', message: CFG.no_endpoint}}; }})
  .then(function(jwt){{
    setStatus('connecting', 'Reactor: loading the SDK...');
    return import(CFG.sdk).then(function(mod){{
      var r = new mod.Reactor({{modelName: CFG.model, jwt: jwt}});
      reactor = r;
      r.on('statusChanged', function(s){{ if (reactor !== r) return; setStatus(s, 'Reactor: ' + s); if (s === 'ready') onReady(); }});
      r.on('error', function(e){{ if (reactor !== r) return; emit('error', {{code: e && e.code || 'error', message: String(e && e.message || e)}}); $('rk-status').textContent = 'Reactor error: ' + (e && e.message || e); }});
      r.on('trackReceived', function(name, track, stream){{ if (reactor !== r) return; if (track && track.kind === 'video') {{ var v = $('rk-video'); v.srcObject = stream || new MediaStream([track]); v.hidden = false; v.play().catch(function(){{}}); }} }});
      r.on('statsUpdate', function(s){{ if (reactor === r) stats(s); }});
      r.on('capabilitiesReceived', function(){{ if (reactor === r) readDeclared(); }});
      r.on('schemaReceived', function(){{ if (reactor === r) readDeclared(); }});
      $('rk-disconnect').disabled = false;
      timer = setTimeout(function(){{ disconnect('session cap of ' + CFG.max_seconds + ' s reached'); }}, CFG.max_seconds * 1000);
      return r.connect();
    }}, function(e){{ throw {{code: 'sdk_load', message: 'Reactor SDK failed to load: ' + (e && e.message || e)}}; }});
  }})
  .catch(function(e){{
    var r = reactor; reactor = null; if (timer) {{ clearTimeout(timer); timer = null; }}
    if (r) r.disconnect().catch(function(){{}});
    fail(e && e.code || 'error', e && e.message ? e.message : String(e));
  }});
}}
$('rk-toggle').addEventListener('click', function(){{
  var card = $('rk-card'), open = card.hidden; card.hidden = !open; this.setAttribute('aria-expanded', String(open));
  if (!open && reactor) disconnect('panel closed');
}});
$('rk-connect').addEventListener('click', connect);
$('rk-disconnect').addEventListener('click', function(){{ disconnect(''); }});
document.addEventListener('visibilitychange', function(){{ if (CFG.disconnect_on_hidden && document.hidden && reactor) disconnect('tab hidden'); }});
window.ReactorKit = {{
  setContext: function(c){{ var before = promptText(); ctx = cleanCtx(Object.assign({{}}, ctx, c || {{}})); var p = promptText(); if (p && p !== before) send('prompt', p); }},
  setReferenceImage: function(fn){{ imageFn = typeof fn === 'function' ? fn : null; }},
  move: function(dir, down){{ var c = CFG.commands[dir]; if (c && c.on) send(dir, down ? c.on : c.off); }},
  dock: function(el){{ var p = $('rk-panel'); p.classList.remove('rk-float'); el.appendChild(p); }},
  status: function(){{ return st; }}
}};
}})();
</script>"""
