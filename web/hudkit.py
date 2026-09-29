#!/usr/bin/env python3
"""web/hudkit.py - one small layout manager for the fixed world UI over a 3D stage (UX, wave 10).

Why: the parish and Bay pages grew a class HUD, a Reactor chip, a Dive/ROV HUD, an NPC panel, the mode buttons, the
minimap and the satellite box - each kit positioned itself (fixed or absolute) and on a phone they fought for the same
corners. Here no kit positions itself: each REGISTERS its panel into a named slot and the kit lays the slots out.

Layout = one CSS grid laid over the stage (`<div class="hud" data-hud>`, position:absolute; inset:0):

      ts   t   te        ts/te/bs/be = the four corners, t/b = the top/bottom edge centres
      .    c   .         c = the canvas centre: an EMPTY track with a floor (HUD_CENTRE_MIN_W/H) that no slot can take
      bs   b   be

- Slots never overlap each other by construction (they are grid cells); panels inside a slot stack with a gap, in
  `order`, and a slot scrolls instead of growing past its cell.
- RTL mirrors for free: grid columns follow the writing direction (the page sets <html dir> from its locale), and the
  CSS uses logical properties only.
- Safe-area insets: the layer's padding is max(8px, env(safe-area-inset-*)).
- Under HUD_COMPACT_PX (600) of STAGE width the layer is `data-hud-compact`: panels registered compact='icon' fold to a
  44 px icon button (aria-expanded) and compact='scroll' panels (the mode row) take the whole first row and wrap, so
  every button stays visible (POLISH w13; the name is kept for the builders' registrations).
- 'flow' registrations are page sections below the stage (path chooser, city life, legend/honesty): the kit adds a
  launcher chip in the dock (top-end) that scrolls to and focuses the section - discoverable from the world, never
  drawn over it.
- Progressive: the static panels keep their own CSS until the script adopts them; without JS nothing moves.

Python API (fail closed - a bad registration stops the build by name):
    from hudkit import HudError, HUD_CSS, HUD_JS, HUD_I18N_KEYS, hud_layer, flow_anchors_present
    layer_html = hud_layer(PANELS, TS, TA)     # PANELS = list of dicts (see check_panels); TS/TA = the page's
                                                # escaped text / attribute translators (their keys land in the catalog)
Runtime hooks (read by web/test_hudkit.mjs --browser): window.__hud.panels() / .overlaps() / .centreFree() / .compact
"""
import json

HUD_COMPACT_PX = 600          # stage width below which compact mode applies (the brief's "under 600 px")
HUD_CENTRE_MIN_W = '30%'      # the empty centre track can never shrink below this share of the stage
HUD_CENTRE_MIN_H = '24%'
HUD_CENTRE_MIN_W_COMPACT = '12%'   # compact: the mode row gets the width, the centre column keeps a floor
HUD_END_MAX_COMPACT = '46%'        # compact: an opened end-side panel (season board, class HUD) never squeezes the mode row away
HUD_OPEN_MAX_W_COMPACT = '150px'   # compact: an opened panel in row 2 (area t, from the start edge) stays short of the stage centre
SLOTS = ('ts', 't', 'te', 'bs', 'b', 'be')
COMPACT = ('none', 'icon', 'scroll')
HUD_I18N_KEYS = ['hud.region', 'hud.open.paths', 'hud.open.city', 'hud.open.legend', 'hud.toggle.reactor',
                 'hud.toggle.fish', 'hud.toggle.fields', 'hud.toggle.drive', 'hud.open.fish']

# minimal 24x24 stroke icons (drawn for this kit; currentColor so every site style reaches them)
ICONS = {
    'route': '<circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8.5 19H15a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h6.5"/>',
    'city': '<path d="M3 21h18M5 21V8l6-3v16M11 9h8v12M8 10v.01M8 14v.01M15 13v.01M15 17v.01"/>',
    'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/>',
    'screen': '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M10 8.5v5l4.5-2.5z"/>',
    # POLISH (wave 13): the fishing, seasons-board and driving panels fold to these on phones (KIT_FOLD below)
    'fish': '<path d="M3 12c2.5-4 8-5.5 12-2l5-3.5v11L15 14c-4 3.5-9.5 2-12-2z"/><path d="M8 11.5v.01"/>',
    'leaf': '<path d="M5 19C5 10 10 5 20 4c0 10-5 15-14 15z"/><path d="M5 19l8-8"/>',
    'car': '<path d="M5 17H3v-5l2-5h14l2 5v5h-2M3 12h18M9.5 17h5"/><circle cx="7.5" cy="17" r="2"/><circle cx="16.5" cy="17" r="2"/>',
}

# POLISH (wave 13, item 7): the kit panels that fold to a 44 px icon under HUD_COMPACT_PX. Their registrations live in
# the world builders' own blocks (FISH / FIELDS / DRIVE, under the builder locks) as compact 'none' (they had no hud.*
# launcher key); hud_layer() upgrades exactly these ids to compact 'icon' with the icon + launcher label below, so no
# builder block has to change and every world page (parish, Bay, wilds) folds them the same way. A registration that
# already says 'icon' (fieldkit's FIELDS_HUD_PANEL) must agree with this table (fail closed).
# compact_slot: in compact mode the item moves (a DOM move, never coordinates) to that slot. Fishing and the board join
# driving in t, which in compact spans the start and centre columns of row 2 (a flexible span never sizes the centre
# track), so their launchers sit side by side and an opened panel never widens a column the other rows share, never
# reaches the minimap's column, and (capped at HUD_OPEN_MAX_W_COMPACT) never the stage centre. Omitted = registered slot.
KIT_FOLD = {
    'fish': {'icon': 'fish', 'label': 'hud.toggle.fish', 'compact_slot': 't'},
    'fields': {'icon': 'leaf', 'label': 'hud.toggle.fields', 'compact_slot': 't'},
    'drive': {'icon': 'car', 'label': 'hud.toggle.drive'},
}
# ...and the fishing section's dock chip ('fishsec', registered by the builders' FISH blocks with the 'route' icon while
# no fish icon existed) takes the fish icon, so the phone dock never shows two identical route icons (paths + fishing)
KIT_FLOW_ICON = {'fishsec': 'fish'}
# POLISH w13 (lead follow-up): on phones the class HUD joins the kit launchers at the start of row 2 (area t), so the
# top-end cell keeps only the dock and nothing there scrolls; not folded (its one button is the entry itself)
KIT_COMPACT_SLOT = {'class': 't'}
HUD_DOCK_COMPACT_COLS = 3     # compact: the dock wraps after this many 44 px chips so the mode row keeps its width


class HudError(KeyError):
    """A panel registration the layout manager refuses (named, so the build stops on it)."""


def _svg(icon):
    if icon not in ICONS:
        raise HudError(f'hudkit: unknown icon {icon!r} (known: {sorted(ICONS)})')
    return ('<svg class="hud-ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            + ICONS[icon] + '</svg>')


def check_panels(panels):
    """Every registration: id (unique), kind 'panel' (adopted by CSS selector `sel` into `slot`, stacked by `order`,
    compact policy in COMPACT; compact='icon' also needs `icon` + `label`) or kind 'flow' (a page section `goto`
    reached from a dock chip with `icon` + `label`; `anchor` is markup that must be in the built page)."""
    seen = set()
    for p in panels:
        for k in ('id', 'kind'):
            if k not in p:
                raise HudError(f'hudkit: panel registration without {k!r}: {p!r}')
        if p['id'] in seen:
            raise HudError(f'hudkit: panel id {p["id"]!r} registered twice')
        seen.add(p['id'])
        if p['kind'] == 'panel':
            for k in ('sel', 'slot', 'order', 'compact'):
                if k not in p:
                    raise HudError(f'hudkit: panel {p["id"]!r} has no {k!r}')
            if p['slot'] not in SLOTS:
                raise HudError(f'hudkit: panel {p["id"]!r} slot {p["slot"]!r} is not one of {SLOTS}')
            if p['compact'] not in COMPACT:
                raise HudError(f'hudkit: panel {p["id"]!r} compact {p["compact"]!r} is not one of {COMPACT}')
            if 'compact_slot' in p and p['compact_slot'] not in SLOTS:
                raise HudError(f'hudkit: panel {p["id"]!r} compact_slot {p["compact_slot"]!r} is not one of {SLOTS}')
            if p['compact'] == 'icon':
                for k in ('icon', 'label'):
                    if k not in p:
                        raise HudError(f'hudkit: icon-compact panel {p["id"]!r} has no {k!r}')
        elif p['kind'] == 'flow':
            for k in ('goto', 'icon', 'label', 'anchor'):
                if k not in p:
                    raise HudError(f'hudkit: flow panel {p["id"]!r} has no {k!r}')
        else:
            raise HudError(f'hudkit: panel {p["id"]!r} kind {p["kind"]!r} is not panel|flow')
    return panels


def fold_kit_panels(panels):
    """KIT_FOLD applied to a registration list (a new list; the caller's dicts are not mutated)."""
    out = []
    for p in panels:
        f = KIT_FOLD[p['id']] if p.get('kind') == 'panel' and p.get('id') in KIT_FOLD else None
        if p.get('kind') == 'flow' and p.get('id') in KIT_FLOW_ICON:
            out.append({**p, 'icon': KIT_FLOW_ICON[p['id']]})
        elif p.get('kind') == 'panel' and p.get('id') in KIT_COMPACT_SLOT:
            out.append({**p, 'compact_slot': KIT_COMPACT_SLOT[p['id']]})
        elif f is None:
            out.append(p)
        elif p['compact'] == 'none':
            q = {**p, 'compact': 'icon', 'icon': f['icon'], 'label': f['label']}
            if 'compact_slot' in f:
                q['compact_slot'] = f['compact_slot']
            out.append(q)
        elif p['compact'] == 'icon' and p.get('icon') == f['icon'] and p.get('label') == f['label']:
            out.append({**p, 'compact_slot': f['compact_slot']} if 'compact_slot' in f else p)
        else:
            raise HudError(f'hudkit: kit panel {p["id"]!r} registration disagrees with KIT_FOLD {f!r}: {p!r}')
    return out


def hud_layer(panels, TS, TA):
    """The HUD layer markup to place INSIDE the stage (after its canvases). Launcher labels come from the caller's
    translators so their keys ship in the page's i18n catalog and re-translate at run time (data-i18n / -aria)."""
    check_panels(panels)
    panels = check_panels(fold_kit_panels(panels))
    slots = ''.join(f'<div class="hud-slot" data-hud-slot="{s}"></div>' for s in SLOTS)
    launch = ''
    for p in panels:
        if p['kind'] == 'panel' and p['compact'] == 'icon':
            launch += (f'<button type="button" class="hud-launch" data-hud-launch="{p["id"]}" aria-expanded="false" '
                       f'aria-label="{TA(p["label"])}" data-i18n-aria="{p["label"]}">{_svg(p["icon"])}</button>')
    dock = ''.join(f'<button type="button" class="hud-chip" data-hud-goto="{p["goto"]}" data-hud-flow="{p["id"]}" '
                   f'aria-label="{TA(p["label"])}" data-i18n-aria="{p["label"]}">{_svg(p["icon"])}'
                   f'<span class="hud-chip-t">{TS(p["label"])}</span></button>'
                   for p in panels if p['kind'] == 'flow')
    reg = [{k: p[k] for k in ('id', 'kind', 'sel', 'slot', 'compact_slot', 'order', 'compact', 'goto') if k in p} for p in panels]
    blob = json.dumps(reg, sort_keys=True).replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')
    return (f'<div class="hud" data-hud role="group" aria-label="{TA("hud.region")}" data-i18n-aria="hud.region" '
            f'data-hud-panels="{blob}" data-hud-compact-px="{HUD_COMPACT_PX}">{slots}'
            f'<div class="hud-dock" data-hud-dock>{dock}</div><div hidden data-hud-launchers>{launch}</div></div>')


def flow_anchors_present(panels, page):
    """Build-time proof that every flow panel's target section is in the page (fail closed)."""
    for p in panels:
        if p['kind'] == 'flow' and page.count(p['anchor']) != 1:
            raise HudError(f'hudkit: flow panel {p["id"]!r} target {p["anchor"]!r} found {page.count(p["anchor"])}x')
    return True


HUD_CSS = f"""
.hud{{position:absolute;inset:0;z-index:5;pointer-events:none;display:grid;gap:8px;
  grid-template-areas:"ts t te" ". c ." "bs b be";
  grid-template-columns:minmax(0,max-content) minmax({HUD_CENTRE_MIN_W},1fr) minmax(0,max-content);
  grid-template-rows:minmax(0,max-content) minmax({HUD_CENTRE_MIN_H},1fr) minmax(0,max-content);
  padding:max(8px,env(safe-area-inset-top)) max(8px,env(safe-area-inset-right)) max(8px,env(safe-area-inset-bottom)) max(8px,env(safe-area-inset-left))}}
.hud-slot{{display:flex;flex-direction:column;gap:8px;min-width:0;min-height:0;overflow:auto;scrollbar-width:thin}}
.hud-slot[data-hud-slot="ts"]{{grid-area:ts;align-items:flex-start}}
.hud-slot[data-hud-slot="t"]{{grid-area:t;align-items:center}}
.hud-slot[data-hud-slot="te"]{{grid-area:te;align-items:flex-end}}
.hud-slot[data-hud-slot="bs"]{{grid-area:bs;align-items:flex-start;justify-content:flex-end}}
.hud-slot[data-hud-slot="b"]{{grid-area:b;align-items:center;justify-content:flex-end}}
.hud-slot[data-hud-slot="be"]{{grid-area:be;align-items:flex-end;justify-content:flex-end}}
.hud-item{{pointer-events:auto;display:flex;flex-direction:column;align-items:inherit;gap:6px;max-width:100%;min-width:0}}
.hud-item:has(>.hud-adopted[hidden]){{display:none}}
.hud .hud-adopted{{position:relative!important;inset:auto!important;transform:none!important;margin:0!important;
  max-width:100%!important;z-index:auto!important}}
.hud-launch,.hud-chip{{pointer-events:auto;min-block-size:44px;min-inline-size:44px;display:inline-flex;align-items:center;
  justify-content:center;gap:6px;border-radius:8px;border:1px solid var(--tc-line,currentColor);
  background:var(--scrim,var(--tc-panel));color:var(--tc-ink,inherit);font:600 13px/1.2 system-ui,sans-serif;cursor:pointer;padding:0 10px}}
.hud-launch:focus-visible,.hud-chip:focus-visible{{outline:3px solid var(--tc-steel,currentColor);outline-offset:2px}}
.hud-ico{{inline-size:20px;block-size:20px;flex:none}}
.hud-launch{{display:none}}
.hud-dock{{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end;pointer-events:none}}
.hud-dock:empty{{display:none}}
/* compact (POLISH w13, REVIEW13 rows 1-2): the mode row owns the whole first row (area ts spans all three columns,
   its buttons wrap, the row is max-content so it never shrinks) - every mode button stays visible and nothing else
   shares its row; t spans start + centre on row 2 beside te; rows 2 and 4 give way (scroll) before row 1 does */
.hud[data-hud-compact]{{grid-template-columns:minmax(0,1fr) minmax({HUD_CENTRE_MIN_W_COMPACT},max-content) fit-content({HUD_END_MAX_COMPACT});
  grid-template-areas:"ts ts ts" "t t te" ". c ." "bs b be";
  grid-template-rows:max-content minmax(0,max-content) minmax({HUD_CENTRE_MIN_H},1fr) minmax(0,max-content)}}
.hud[data-hud-compact] .hud-slot[data-hud-slot="bs"],.hud[data-hud-compact] .hud-slot[data-hud-slot="b"],.hud[data-hud-compact] .hud-slot[data-hud-slot="be"]{{justify-content:safe flex-end}}
.hud[data-hud-compact] .hud-launch{{display:inline-flex}}
.hud[data-hud-compact] .hud-dock{{max-inline-size:calc({HUD_DOCK_COMPACT_COLS} * 44px + {HUD_DOCK_COMPACT_COLS - 1} * 6px)}}
.hud[data-hud-compact] .hud-item[data-compact="icon"]:not([data-open])>.hud-adopted{{display:none!important}}
.hud[data-hud-compact] .hud-item[data-compact="scroll"]>.hud-adopted{{flex-wrap:wrap!important;max-width:100%!important}}
.hud[data-hud-compact] .hud-item[data-compact="scroll"]>.hud-adopted>*{{flex:none}}
.hud[data-hud-compact] .hud-item[data-compact="scroll"]>.hud-adopted>:not(button){{order:1;flex:1 1 40%;min-width:0;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;padding-block:4px!important;font-size:12px!important}}
/* row 2 start (area t): the folded kit launchers and the class HUD sit side by side and wrap; one icon panel is open at a
   time (script), an opened panel goes last and stays narrower than the distance to the stage centre */
.hud[data-hud-compact] .hud-slot[data-hud-slot="t"]{{flex-direction:row;flex-wrap:wrap;align-items:flex-start;align-content:flex-start}}
.hud[data-hud-compact] .hud-item[data-open]{{order:9}}
.hud[data-hud-compact] .hud-slot[data-hud-slot="t"]>.hud-item[data-hud-panel="class"]{{order:5}}
.hud[data-hud-compact] .hud-slot[data-hud-slot="t"]>.hud-item[data-open]{{max-inline-size:min(100%,{HUD_OPEN_MAX_W_COMPACT})}}
.hud[data-hud-compact] .hud-chip-t{{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}}
"""

HUD_JS = r"""
(function () {
  const root = document.querySelector('[data-hud]');
  if (!root) return;
  const stage = root.parentElement, REG = JSON.parse(root.dataset.hudPanels), PX = Number(root.dataset.hudCompactPx);
  const slots = {}; for (const s of root.querySelectorAll('[data-hud-slot]')) slots[s.dataset.hudSlot] = s;
  const dock = root.querySelector('[data-hud-dock]'), launchers = root.querySelector('[data-hud-launchers]');
  const adopted = {}, pending = REG.filter((p) => p.kind === 'panel');
  slots.te.appendChild(dock);   // the dock heads the top-end slot (order -1)
  dock.style.order = '-1';
  function adopt(p, el) {
    const item = document.createElement('div');
    item.className = 'hud-item'; item.dataset.hudPanel = p.id; item.dataset.compact = p.compact; item.style.order = String(p.order);
    if (p.compact === 'icon') {
      const b = launchers.querySelector('[data-hud-launch="' + p.id + '"]');
      if (!b) throw new Error('hudkit: no launcher for icon panel ' + p.id);
      b.addEventListener('click', () => {
        const open = !item.hasAttribute('data-open');
        // compact: one icon panel open at a time (opening one folds the others back to their icons)
        if (open && root.hasAttribute('data-hud-compact')) for (const o of root.querySelectorAll('.hud-item[data-open]')) if (o !== item) {
          o.removeAttribute('data-open'); const ob = o.querySelector('[data-hud-launch]'); if (ob) ob.setAttribute('aria-expanded', 'false'); }
        item.toggleAttribute('data-open', open); b.setAttribute('aria-expanded', String(open));
      });
      item.appendChild(b);
    }
    el.classList.add('hud-adopted');
    item.appendChild(el);
    adopted[p.id] = item;
    place(p);
  }
  // compact_slot: the item lives in that slot while the layer is compact, in its own slot otherwise (a DOM move)
  function place(p) {
    const item = adopted[p.id]; if (!item) return;
    const want = slots[p.compact_slot && root.hasAttribute('data-hud-compact') ? p.compact_slot : p.slot];
    if (item.parentElement !== want) want.appendChild(item);
  }
  function sweep() {
    for (let i = pending.length - 1; i >= 0; i--) {
      const p = pending[i], el = document.querySelector(p.sel);
      if (el && !el.closest('.hud-item')) { adopt(p, el); pending.splice(i, 1); }
    }
    if (!pending.length && mo) mo.disconnect();
  }
  let mo = null;
  sweep();
  // kits append their panels late (class HUD to <body>, Dive/ROV HUD to the stage, NPC dialog to its root): watch those
  // parents' direct children only - never the whole subtree, so per-frame label churn costs nothing
  if (pending.length) {
    mo = new MutationObserver(sweep);
    for (const host of [document.body, stage, document.querySelector('[data-npc-root]')]) if (host) mo.observe(host, { childList: true });
  }
  for (const b of dock.querySelectorAll('[data-hud-goto]')) {
    const target = document.querySelector(b.dataset.hudGoto);
    if (!target) { b.hidden = true; continue; }
    b.addEventListener('click', () => {
      if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
      target.scrollIntoView({ block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
      target.focus({ preventScroll: true });
    });
  }
  const setCompact = () => { root.toggleAttribute('data-hud-compact', stage.clientWidth < PX); for (const p of REG) if (p.compact_slot) place(p); };
  setCompact();
  if (window.ResizeObserver) new ResizeObserver(setCompact).observe(stage); else addEventListener('resize', setCompact);
  const shown = (el) => el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
  function rects() {
    const out = [];
    for (const [id, item] of Object.entries(adopted)) if (shown(item)) out.push({ id, r: item.getBoundingClientRect() });
    for (const b of dock.querySelectorAll('[data-hud-flow]')) if (shown(b)) out.push({ id: 'flow:' + b.dataset.hudFlow, r: b.getBoundingClientRect() });
    return out.filter((o) => o.r.width > 0 && o.r.height > 0);
  }
  window.__hud = {
    get compact() { return root.hasAttribute('data-hud-compact'); },
    panels: () => rects().map((o) => ({ id: o.id, x: o.r.x, y: o.r.y, w: o.r.width, h: o.r.height })),
    pending: () => pending.map((p) => p.id),
    overlaps() {
      const rs = rects(), bad = [];
      for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) {
        const a = rs[i].r, b = rs[j].r;
        const w = Math.min(a.right, b.right) - Math.max(a.left, b.left), h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (w > 0.5 && h > 0.5) bad.push(rs[i].id + '|' + rs[j].id);
      }
      return bad;
    },
    centreFree() {
      const s = stage.getBoundingClientRect(), cx = s.left + s.width / 2, cy = s.top + s.height / 2;
      return rects().every((o) => cx < o.r.left || cx > o.r.right || cy < o.r.top || cy > o.r.bottom);
    },
  };
})();
"""


if __name__ == '__main__':
    print(f'hudkit: slots {SLOTS}, compact under {HUD_COMPACT_PX}px, centre floor {HUD_CENTRE_MIN_W} x {HUD_CENTRE_MIN_H}, '
          f'icons {sorted(ICONS)}, i18n {HUD_I18N_KEYS}')
