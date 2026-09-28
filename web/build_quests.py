"""Builds web/trade_craft_quests.html: the quest log, the badge shelf and an
arcade of small games, each locked until the lessons it needs count as done
on this device (window.TCQuests.check, the engine in web/questkit.py).

Game content comes from the repo, never typed here:
  Signal caller   sims/registry/sims.json#sims.rigging-signals.controls (the
                  signals and the keys the seat uses) and its rubric (in order,
                  zero wrong, finish on STOP)
  Chart or refuse sims/registry/sims.json#sims.load-chart.chart (radius, chart
                  line) with its dash units; picks are only ever at a chart row
  Cut to grade    sims/registry/sims.json#sims.excavator-trench rubric: every
                  cell to its marked depth, the flagged cell stopped at half,
                  every bucket in the spoil zone. Depth is counted in bites, a
                  game unit, not a measurement.
The round clock and the pick multipliers are AUTHORED game rules, labelled so.

Quests are play: nothing here enters a completion record. The demo toggle is
off on every load, lives in memory only, and a round won with it on is not
recorded.

`python3 web/build_quests.py --check` fails if the committed page is stale.
"""
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from sitenav import nav_html, labels as nav_labels, NAV_CSS  # noqa: E402
from questkit import QUEST_CSS, quest_js, egg_attr, quest_attr, page_hooks, BY_ID, HONESTY, LESSONS  # noqa: E402

PATH = 'web/trade_craft_quests.html'
OUT = ROOT / PATH
E = html.escape
NAV = nav_html('web/trade_craft_quests.html', nav_labels('en'))


def need(d, k, where):
    if not isinstance(d, dict):
        raise TypeError(f'{where}: expected an object to read {k!r} from')
    if k not in d:
        raise KeyError(f'{where}: required field {k!r} is missing')
    return d[k]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


SIMS = need(load('sims/registry/sims.json'), 'sims', 'sims/registry/sims.json')

# ---- Signal caller: the rigging-signals seat's own controls
sig = need(SIMS, 'rigging-signals', 'sims.json#sims')
SIGNALS = []
for c in need(sig, 'controls', 'sims.rigging-signals'):
    keys = [k.strip() for k in need(c, 'keys', 'rigging-signals.controls').split('/')]
    act = need(c, 'action', 'rigging-signals.controls')
    m = re.match(r'^signal (.+)$', act)
    if not m:
        raise ValueError(f'rigging-signals control {act!r} does not read "signal ..."')
    body = m.group(1)
    names = [n.strip() for n in body.split('/')]
    if len(names) == 2 and len(keys) == 2 and ' ' in names[0]:
        verb = names[0].split(' ')[0]
        second = names[1] if ' ' in names[1] else verb + ' ' + names[1]
        names = [names[0], second]
    if len(names) != len(keys):
        raise ValueError(f'rigging-signals control {act!r}: {len(keys)} keys for {len(names)} signals')
    for k, n in zip(keys, names):
        SIGNALS.append({'key': k, 'signal': n})
if not any(s['signal'] == 'STOP' for s in SIGNALS):
    raise ValueError('rigging-signals: no STOP signal in the controls; the game ends on STOP')
SIG_TASK = need(sig, 'task', 'sims.rigging-signals')

# ---- Chart or refuse: the load-chart seat's chart and dash units
lc = need(SIMS, 'load-chart', 'sims.json#sims')
CHART = need(lc, 'chart', 'sims.load-chart')
UNITS = {d['id']: d['unit'] for d in need(lc, 'dash', 'sims.load-chart')}
for u in ('radius', 'chart'):
    if u not in UNITS:
        raise KeyError(f'sims.load-chart.dash has no {u!r} unit')
LC_TASK = need(lc, 'task', 'sims.load-chart')

# ---- Cut to grade: the excavator-trench rubric
ex = need(SIMS, 'excavator-trench', 'sims.json#sims')
EX_RUBRIC = {r['axis']: r for r in need(ex, 'rubric', 'sims.excavator-trench')}
for ax in ('grade', 'utility', 'spoil'):
    if ax not in EX_RUBRIC:
        raise KeyError(f'sims.excavator-trench.rubric has no {ax!r} axis')
EX_TASK = need(ex, 'task', 'sims.excavator-trench')

GAMES = [('game-signal-caller', 'signal'), ('game-load-chart', 'chart'), ('game-trench-grade', 'trench'), ('game-crib-match', 'crib')]
CRIB_ID = BY_ID['game-crib-match']['place']
CRIB = need(need(load('tools/registry/toolcribs.json'), 'cribs', 'toolcribs.json'), CRIB_ID, 'toolcribs.json#cribs')
CRIB_TOOLS = [{'name': need(t, 'name', CRIB_ID), 'use': need(t, 'use', CRIB_ID)} for t in need(CRIB, 'tools', CRIB_ID)]
if len(CRIB_TOOLS) < 4:
    raise AssertionError(f'crib {CRIB_ID} holds fewer than four tools; the game offers four choices')
CRIB_TASK = 'Each card reads what a tool in the ' + need(CRIB, 'name', CRIB_ID) + ' is for; pick that tool off the wall.'
for gid, _ in GAMES:
    if BY_ID[gid]['kind'] != 'game':
        raise AssertionError(f'{gid} is not a game in the quest registry')

# ---- modules no other page reads, brought in as treasures
comp = load('compliance/registry/compliance.json')
COMP_WHAT = need(comp, 'what_this_is', 'compliance.json')
COMP_CLASSES = list(need(comp, 'ledger_classes', 'compliance.json'))
ev = load('evals/registry/evals.json')
EV_LIMIT = need(need(ev, 'limit', 'evals.json'), 'sentence', 'evals.json#limit')
EV_METRICS = need(ev, 'metrics', 'evals.json')
ven = load('venue/registry/venue.json')
VEN_LEVELS = len(need(ven, 'levels', 'venue.json'))
VEN_AUTHOR = need(need(ven, 'attribution', 'venue.json'), 'author', 'venue.json#attribution')
sbom = load('security/registry/sbom.cdx.json')
SBOM_N = len(need(sbom, 'components', 'sbom.cdx.json'))


def game_gate(gid):
    q = BY_ID[gid]
    items = ''.join(f'<li><a href="trade_craft_lessons.html#lesson-{E(l)}" data-lesson="{E(l)}">{E(LESSONS[l]["title"])}</a>'
                    f' <span class="st" data-lesson-state="{E(l)}"></span></li>' for l in q['requires']['lessons'])
    return (f'<div class="gate" data-gate="{E(gid)}"><p><b>Locked.</b> {E(q["unlock_text"])}</p>'
            f'<ul>{items}</ul><p class="muted">A lesson counts here when every step this device can record is '
            f'done, read from the same progress record the progress page reads.</p></div>')


ARCADE = ''
for gid, kind in GAMES:
    q = BY_ID[gid]
    task = {'signal': SIG_TASK, 'chart': LC_TASK, 'trench': EX_TASK, 'crib': CRIB_TASK}[kind]
    ARCADE += f'''
<article class="game" id="{E(gid)}" data-game="{E(kind)}" {quest_attr(gid).replace('data-tc-quest', 'data-game-quest')}>
  <h3>{E(q["title"])}</h3>
  <p class="muted">From the <code>{E(q["place"])}</code> seat: {E(task)}</p>
  {game_gate(gid)}
  <div class="play" hidden>
    <div class="board" aria-live="polite"></div>
    <div class="controls"></div>
    <p class="result" role="status"></p>
    <button type="button" class="start">Start a round</button>
  </div>
</article>'''

GAME_DATA = json.dumps({
    'signals': SIGNALS, 'chart': CHART, 'units': {'radius': UNITS['radius'], 'chart': UNITS['chart']},
    'games': {gid: kind for gid, kind in GAMES}, 'crib': CRIB_TOOLS,
    'trench_fail': {ax: EX_RUBRIC[ax]['fails_when'] for ax in ('grade', 'utility', 'spoil')},
}, ensure_ascii=False).replace('</', '<\\/')

ARCADE_JS = r"""
const G = JSON.parse(document.getElementById('arcade-data').textContent);
let DEMO = false;
function rnd(n) { return Math.floor(Math.random() * n); }
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
function finish(card, won, line) {
  const gid = card.id;
  const res = card.querySelector('.result');
  if (!won) { res.textContent = 'Not this round: ' + line; return; }
  const r = window.TCQuests.complete(gid);
  res.textContent = r.ok ? 'Round won: ' + line : 'Round won in demo mode: ' + line + ' Demo rounds are not recorded.';
}
/* Signal caller: the card calls five moves, then STOP; give each in order. */
function playSignal(card) {
  const board = card.querySelector('.board'), ctl = card.querySelector('.controls');
  const moves = G.signals.filter((s) => s.signal !== 'STOP');
  const stop = G.signals.find((s) => s.signal === 'STOP');
  const calls = []; for (let i = 0; i < 5; i++) calls.push(moves[rnd(moves.length)]); calls.push(stop);
  let at = 0, wrong = 0, left = 30; const t0 = performance.now();
  ctl.replaceChildren();
  const show = () => { board.textContent = 'Card calls: ' + calls[at].signal.toUpperCase() + '  (' + (at + 1) + ' of ' + calls.length + ') - clock ' + left + ' s - wrong ' + wrong; };
  const give = (s) => {
    if (at >= calls.length) return;
    if (s !== calls[at]) { wrong++; show(); return; }
    at++;
    if (at === calls.length) { clearInterval(tick); document.removeEventListener('keydown', keys); const secs = ((performance.now() - t0) / 1000).toFixed(1);
      finish(card, wrong === 0, wrong === 0 ? 'every call given in order, finished on STOP, zero wrong (' + secs + ' s, informational).' : wrong + ' signal(s) given out of turn; the rubric passes only at zero.'); board.textContent = 'Card done.'; return; }
    show();
  };
  for (const s of G.signals) { const b = el('button', 'sig', s.signal + ' [' + s.key + ']'); b.type = 'button'; b.addEventListener('click', () => give(s)); ctl.appendChild(b); }
  const keys = (e) => { const k = e.key === ' ' ? 'Space' : e.key.toUpperCase(); const s = G.signals.find((x) => x.key.toUpperCase() === k); if (s) { e.preventDefault(); give(s); } };
  document.addEventListener('keydown', keys);
  const tick = setInterval(() => { left--; if (left <= 0) { clearInterval(tick); document.removeEventListener('keydown', keys); at = calls.length; finish(card, false, 'the round clock ran out with calls unsigned.'); board.textContent = 'Time.'; } else show(); }, 1000);
  show();
}
/* Chart or refuse: six picks, each at a chart row's radius. */
function playChart(card) {
  const board = card.querySelector('.board'), ctl = card.querySelector('.controls');
  const MULT = [0.5, 0.8, 1, 1.1, 1.3];
  const picks = []; for (let i = 0; i < 6; i++) { const row = G.chart[rnd(G.chart.length)]; picks.push({ r: row[0], line: row[1], load: Math.round(row[1] * MULT[rnd(MULT.length)] * 10) / 10 }); }
  let at = 0, wrongCalls = 0, overloads = 0;
  const table = el('table', 'chart'); const hr = el('tr'); hr.append(el('th', '', 'Radius (' + G.units.radius + ')'), el('th', '', 'Chart (' + G.units.chart + ')')); table.append(hr);
  for (const [r, c] of G.chart) { const tr = el('tr'); tr.append(el('td', '', String(r)), el('td', '', String(c))); table.append(tr); }
  const show = () => { board.replaceChildren(table, el('p', 'pick', 'Pick ' + (at + 1) + ' of ' + picks.length + ': ' + picks[at].load + ' ' + G.units.chart + ' at ' + picks[at].r + ' ' + G.units.radius)); };
  const judge = (accept) => {
    if (at >= picks.length) return;
    const p = picks[at]; const allowed = p.load <= p.line;
    if (accept !== allowed) wrongCalls++;
    if (accept && !allowed) overloads++;
    at++;
    if (at === picks.length) { board.replaceChildren(table); finish(card, wrongCalls === 0, wrongCalls === 0 ? 'every pick judged with the chart, zero overloads hooked.' : wrongCalls + ' pick(s) called wrong, ' + overloads + ' overweight pick(s) hooked.'); return; }
    show();
  };
  ctl.replaceChildren();
  const a = el('button', 'sig', 'Hook it [Space]'); a.type = 'button'; a.addEventListener('click', () => judge(true));
  const x = el('button', 'sig', 'Refuse [X]'); x.type = 'button'; x.addEventListener('click', () => judge(false));
  ctl.append(a, x);
  const keys = (e) => { if (at >= picks.length) { document.removeEventListener('keydown', keys); return; } if (e.key === ' ') { e.preventDefault(); judge(true); } else if (e.key === 'x' || e.key === 'X') judge(false); };
  document.addEventListener('keydown', keys);
  show();
}
/* Cut to grade: dig each cell to its marked bites; the flagged cell stops at half. */
function playTrench(card) {
  const board = card.querySelector('.board'), ctl = card.querySelector('.controls');
  const cells = []; for (let i = 0; i < 5; i++) cells.push({ mark: 2 + rnd(3), dug: 0 });
  const flag = rnd(cells.length); cells[flag].mark = 4; cells[flag].stop = 2;
  let bucket = false, strikes = 0, spills = 0;
  const draw = () => {
    board.replaceChildren();
    const row = el('div', 'trench');
    cells.forEach((c, i) => {
      const b = el('button', 'cell' + (i === flag ? ' flag' : ''), (i === flag ? 'flag ' : '') + c.dug + '/' + (i === flag ? c.stop : c.mark));
      b.type = 'button'; b.setAttribute('aria-label', 'cell ' + (i + 1) + (i === flag ? ', flagged utility, stop at ' + c.stop : ', marked ' + c.mark) + ' bites, dug ' + c.dug);
      b.addEventListener('click', () => { if (bucket) { card.querySelector('.result').textContent = 'The bucket is full: dump it first.'; return; } c.dug++; bucket = true; if (i === flag && c.dug > c.stop) strikes++; draw(); });
      row.appendChild(b);
    });
    board.append(row, el('p', 'muted', 'Bucket: ' + (bucket ? 'full' : 'empty') + '. Depth is counted in bites, a game unit.'));
  };
  ctl.replaceChildren();
  const spoil = el('button', 'sig', 'Dump in the spoil zone'); spoil.type = 'button';
  spoil.addEventListener('click', () => { if (!bucket) return; bucket = false; draw(); });
  const beside = el('button', 'sig', 'Dump beside the cut'); beside.type = 'button';
  beside.addEventListener('click', () => { if (!bucket) return; bucket = false; spills++; draw(); });
  const done = el('button', 'sig', 'Call it finished'); done.type = 'button';
  done.addEventListener('click', () => {
    const off = cells.filter((c, i) => (i === flag ? c.dug !== c.stop : c.dug !== c.mark)).length;
    const fails = [];
    if (off) fails.push(G.trench_fail.grade);
    if (strikes) fails.push(G.trench_fail.utility);
    if (spills || bucket) fails.push(G.trench_fail.spoil);
    finish(card, fails.length === 0, fails.length === 0 ? 'every cell at its mark, the flagged cell stopped shallow, every bucket in the zone.' : fails.join('; ') + '.');
  });
  ctl.append(spoil, beside, done);
  draw();
}
/* Crib match: five cards, each a tool's use from the crib; pick the tool among four. */
function playCrib(card) {
  const board = card.querySelector('.board'), ctl = card.querySelector('.controls');
  let at = 0, wrong = 0; const cards = [];
  for (let i = 0; i < 5; i++) cards.push(G.crib[rnd(G.crib.length)]);
  const show = () => {
    const c = cards[at]; const opts = [c];
    while (opts.length < 4) { const t = G.crib[rnd(G.crib.length)]; if (!opts.includes(t)) opts.push(t); }
    opts.sort(() => Math.random() - 0.5);
    board.textContent = 'Card ' + (at + 1) + ' of ' + cards.length + ': it ' + c.use + '.';
    ctl.replaceChildren(...opts.map((t) => { const b = el('button', 'sig', t.name); b.type = 'button'; b.addEventListener('click', () => pick(t)); return b; }));
  };
  const pick = (t) => {
    if (t !== cards[at]) wrong++;
    at++;
    if (at === cards.length) { ctl.replaceChildren(); board.textContent = 'Crib closed.'; finish(card, wrong === 0, wrong === 0 ? 'every tool picked for its use.' : wrong + ' tool(s) picked for the wrong use.'); return; }
    show();
  };
  show();
}
const PLAY = { signal: playSignal, chart: playChart, trench: playTrench, crib: playCrib };
function paintLocks() {
  const done = window.TCQuests.lessonsDone();
  for (const card of document.querySelectorAll('.game')) {
    const c = window.TCQuests.check(card.id);
    const open = c.ok || DEMO;
    card.dataset.locked = open ? 'false' : 'true';
    card.querySelector('.gate').hidden = open;
    card.querySelector('.play').hidden = !open;
    for (const s of card.querySelectorAll('[data-lesson-state]')) s.textContent = done.has(s.dataset.lessonState) ? '(done on this device)' : '(not yet)';
  }
}
function renderLog(root, T) {
  const st = T.state(); const done = T.lessonsDone();
  const kinds = [['main', 'Main quests'], ['game', 'Arcade games'], ['side', 'Side quests'], ['treasure', 'Treasures'], ['egg', 'Easter eggs']];
  root.replaceChildren();
  for (const [k, label] of kinds) {
    const qs = T.data.quests.filter((q) => q.kind === k);
    const got = qs.filter((q) => (q.id in st.done) || (q.id in st.found)).length;
    const det = el('details', 'logk'); if (k === 'main' || k === 'game') det.open = true;
    det.append(el('summary', '', label + ' - ' + got + ' of ' + qs.length));
    const ul = el('ul', 'tc-log');
    for (const q of qs) {
      const have = (q.id in st.done) || (q.id in st.found);
      const c = T.check(q.id);
      const li = el('li'); li.dataset.state = have ? 'got' : (c.ok ? 'open' : 'locked');
      li.append(el('b', '', q.title), el('span', 'muted', ' - ' + (have ? 'badge "' + q.reward.label + '"' : (q.kind === 'egg' || q.kind === 'treasure') ? (q.riddle || q.hint) : (c.ok ? q.hint : q.unlock_text))));
      if (!have && c.ok && (q.kind === 'main' || q.kind === 'side') && !document.querySelector('[data-tc-quest="' + q.id + '"]')) {
        const b = el('button', 'mini', 'Report in'); b.type = 'button'; b.addEventListener('click', () => T.complete(q.id)); li.append(' ', b);
      }
      ul.append(li);
    }
    det.append(ul); root.append(det);
  }
  const shelf = document.getElementById('shelf');
  const labels = {}; for (const q of T.data.quests) labels[q.reward.badge] = q.reward.label;
  shelf.replaceChildren(...(st.badges.length ? st.badges.map((b) => el('li', 'badge', labels[b] || b)) : [el('li', 'muted', 'No badges on this device yet.')]));
  paintLocks();
}
window.TCQuestsRender = renderLog;
document.addEventListener('DOMContentLoaded', () => {
  const demo = document.getElementById('demo');
  demo.checked = false;
  demo.addEventListener('change', () => { DEMO = demo.checked; paintLocks(); });
  for (const card of document.querySelectorAll('.game')) card.querySelector('.start').addEventListener('click', () => { card.querySelector('.result').textContent = ''; PLAY[card.dataset.game](card); });
  for (const ev of ['found', 'done']) window.TCQuests.on(ev, () => window.TCQuests.render());
});
"""

METRICS = ', '.join(EV_METRICS) if isinstance(EV_METRICS, list) else ', '.join(EV_METRICS.keys())
HOOKS = page_hooks(PATH)

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quests and arcade — Trade Craft Academy</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<style>
:root{{--plate:#12181B;--panel:#182023;--sunk:#0C1113;--ink:#E8EDEC;--muted:#93A3A6;--rule:#28353A;--mark:#E8A33D;
  --mark-ink:#12181B;--steel:#41C4D4;--good:#5CB584;--crit:#E07C68}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:1020px;margin:0 auto;padding:0 16px}}
a{{color:var(--steel)}}
header.page{{padding:30px 0 10px;border-bottom:3px solid var(--mark)}}
h1{{font:700 34px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0;cursor:default}}
h2{{font:700 22px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:28px 0 10px;color:var(--mark)}}
h3{{margin:0 0 6px;font-size:18px}}
.lead{{background:var(--panel);border:1px solid var(--rule);border-inline-start:4px solid var(--mark);border-radius:8px;padding:12px 16px;margin-top:16px}}
.muted{{color:var(--muted);font-size:13.5px}}
code{{font:13px ui-monospace,Menlo,monospace;color:var(--muted);overflow-wrap:anywhere}}
.arcade{{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr))}}
.game{{background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:14px}}
.game[data-locked="true"]{{border-style:dashed}}
.gate ul{{padding-inline-start:18px;margin:6px 0}}
.controls{{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}}
button{{font:inherit}}
.sig,.start,.mini,.board-btn{{background:var(--sunk);color:var(--ink);border:1px solid var(--rule);border-radius:7px;padding:7px 10px;cursor:pointer;min-block-size:36px}}
.start{{background:var(--mark);color:var(--mark-ink);border-color:var(--mark);font-weight:600}}
.board{{background:var(--sunk);border-radius:8px;padding:10px;min-block-size:3rem;overflow-x:auto}}
table.chart{{border-collapse:collapse}} table.chart td,table.chart th{{border:1px solid var(--rule);padding:3px 10px;text-align:end}}
.trench{{display:flex;flex-wrap:wrap;gap:6px}}
.cell{{background:#3a2d1e;color:var(--ink);border:1px solid var(--rule);border-radius:6px;padding:10px 8px;min-inline-size:56px;cursor:pointer}}
.cell.flag{{border-color:var(--crit);color:var(--crit)}}
.result{{min-block-size:1.4em}}
.demo{{background:var(--sunk);border:1px dashed var(--crit);border-radius:8px;padding:10px 12px;margin:10px 0}}
.tc-log{{list-style:none;padding:0;margin:6px 0}}
.tc-log li{{padding:5px 0;border-top:1px solid var(--rule)}}
.tc-log li[data-state="got"] b{{color:var(--good)}}
.tc-log li[data-state="locked"]{{opacity:.8}}
details.logk{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:8px 12px;margin:8px 0}}
details.logk summary{{cursor:pointer;font-weight:600}}
#shelf{{display:flex;flex-wrap:wrap;gap:6px;list-style:none;padding:0}}
.badge{{background:var(--sunk);border:1px solid var(--mark);color:var(--mark);border-radius:999px;padding:3px 10px;font-size:13px}}
.clue{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:10px 14px;margin:8px 0}}
.clue summary{{cursor:pointer;min-block-size:32px;padding-block:4px}}
footer.page{{margin-top:30px;border-top:1px solid var(--rule);padding:14px 0 24px;color:var(--muted)}}
{QUEST_CSS}
{NAV_CSS}
</style>
</head>
<body>
{NAV}<div class="wrap">
<header class="page">
  <h1>Quests and arcade</h1>
  <p class="muted">Side quests, games, treasures and easter eggs across the whole academy, gated by the lessons they use.</p>
</header>

<section class="lead" id="honesty">
  <p><b>This is play.</b> {E(HONESTY)} Lessons stay unverified general practice, exactly as the lessons page says.</p>
  <p><button type="button" class="start" {quest_attr("main-report-in")}>Report in</button>
     <span class="muted">Start the main chain here.</span></p>
</section>

<h2 id="arcade-h">Arcade</h2>
<p class="muted">Each game is locked until the lessons it needs count as done on this device. A lesson counts when every
step this device can record is done (walk and placard steps are recorded by nothing, so they are not waited on). The
round clock and the pick sizes are AUTHORED game rules; the signals, keys, chart and rubric are the simulator seats' own.</p>
<div class="demo">
  <label><input type="checkbox" id="demo"> Unlock everything for a demo</label>
  <p class="muted">For demos only. Off every time the page loads, kept nowhere, and a round won with it on is not recorded.</p>
</div>
<div class="arcade">{ARCADE}
</div>

<h2>Badge shelf</h2>
<ul id="shelf"></ul>

<h2>Quest log</h2>
<div data-tc-questlog></div>

<h2>Clues on the board</h2>
<details class="clue" id="compliance-placard"><summary {egg_attr("treasure-compliance-placard")} tabindex="0">A placard by the shelf</summary>
  <p>{E(COMP_WHAT)}</p>
  <p class="muted">Ledger classes: {E(", ".join(COMP_CLASSES))}. Read from <code>compliance/registry/compliance.json</code>.</p></details>
<details class="clue" id="eval-drawer"><summary>The eval drawer</summary>
  <p>{E(EV_LIMIT)}</p>
  <p class="muted">Metrics the sequencer eval reports: {E(METRICS)}. Read from <code>evals/registry/evals.json</code>.</p>
  <p><button type="button" class="mini" {quest_attr("side-inspect-sequencer-eval")}>I read what it does not prove</button></p></details>
<details class="clue" id="venue-clue"><summary>A room measured, not drawn</summary>
  <p>The venue pack measured {VEN_LEVELS} levels from a scanned model by {E(VEN_AUTHOR)}; nothing of the model is copied here.</p>
  <p><button type="button" class="mini" {egg_attr("treasure-venue-room")}>Mark the room found</button>
     <span class="muted">Read from <code>venue/registry/venue.json</code>.</span></p></details>
<details class="clue" id="sbom-manifest"><summary>The parts manifest</summary>
  <p>The bundle's software bill of materials lists {SBOM_N} components.</p>
  <p><button type="button" class="mini" {egg_attr("treasure-sbom-manifest")}>Count them</button>
     <span class="muted">Read from <code>security/registry/sbom.cdx.json</code>.</span></p></details>

<footer class="page">
  <a href="trade_craft_lessons.html">lessons</a> · <a href="trade_craft_progress.html">your progress</a>
</footer>
</div>
{HOOKS}<script type="application/json" id="arcade-data">{GAME_DATA}</script>
<script id="arcade-js">
{ARCADE_JS}</script>
{quest_js("all", PATH)}</body>
</html>
'''

if '--check' in sys.argv:
    if not OUT.exists() or OUT.read_text(encoding='utf-8') != page:
        sys.exit(f'{PATH} is stale: run python3 web/build_quests.py')
    print(f'{PATH} is current')
else:
    OUT.write_text(page, encoding='utf-8')
    print(f'wrote {PATH}: {len(GAMES)} games, {len(BY_ID)} quest entries')
