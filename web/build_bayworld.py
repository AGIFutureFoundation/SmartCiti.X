#!/usr/bin/env python3
"""web/build_bayworld.py - the walkable Bay Area world (web/trade_craft_bay.html).

Reuses the parish page machinery WHOLE, without editing it: reads web/build_parishes.py, applies the world-target
hook below IN MEMORY (every anchor must occur exactly once - a changed parish builder stops this build with a named
error, never a silent drift; the same hook is proposed for the file itself in BAY's NEEDS), registers a world target
(sys.modules['__world_target__']) and executes it. The target swaps in the Bay registries (bayarea/page_view.py,
an in-memory parish-shaped view of bayarea/registry/bayarea.json + world.json), the page path, seven place-specific
i18n keys (bay.*), the asset families for campus/city pins, and switches off the kits whose registries carry no Bay
county (NPC guides, parish quests, learning-path layers) - they show as stub with the reason. Everything else (streaming chunks, borders,
AUTHORED water, vehicles, physkit/ambientkit/fleetkit/econkit, satellite view-time layer) is the parish page's own code.

    python3 web/build_bayworld.py            # writes web/trade_craft_bay.html
    python3 web/build_bayworld.py --check    # exit 1 if the page is stale
"""
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'bayarea'))
import page_view  # noqa: E402

T = types.ModuleType('__world_target__')
T.REG, T.WORLD = page_view.load()
T.PAGE = 'web/trade_craft_bay.html'


def offshore_pins(reg):
    """WORLDS (wave 10): a restoration site the county outlines cannot hold (bayarea restoration_not_placed with a
    RECORDED point) is still pinned when ITS OWN record says pin:true - at the recorded world_m, in the county its
    record names, as an offshore pin (never moved onto land, never a walk target, never a scenario runner). A site
    with no recorded point (spartina-removal: lat/lng null, pin false) stays unpinned. Fail closed on every field."""
    import json
    rs = {s['id']: s for s in json.loads((ROOT / 'restoration/registry/restoration.json').read_text())['sites']}
    out = []
    for x in reg['restoration_not_placed']:
        if x['id'] not in rs:
            raise SystemExit(f'build_bayworld: restoration_not_placed {x["id"]} is not in restoration/registry/restoration.json')
        s = rs[x['id']]
        if s['lat'] is None or s['pin'] is not True:
            continue
        if 'world_m' not in x or x['provenance'] != 'RECORDED' or [x['lat'], x['lng']] != [s['lat'], s['lng']]:
            raise SystemExit(f'build_bayworld: {x["id"]} offshore pin needs the RECORDED point of its restoration record')
        hits = [f for f, p in reg['parishes'].items() if p['name'] == s['county']]
        if len(hits) != 1:
            raise SystemExit(f'build_bayworld: {x["id"]} record county {s["county"]!r} names {len(hits)} selected counties')
        if s['walkable'] is not False or not s['walkable_reason']:
            raise SystemExit(f'build_bayworld: {x["id"]} offshore pin expects walkable false with its reason')
        reg['parishes'][hits[0]]['landmarks'].append({
            'name': x['name'], 'kind': 'restoration site (offshore pin)', 'lat': s['lat'], 'lng': s['lng'],
            'world_m': x['world_m'], 'provenance': 'RECORDED',
            'note': (f'{x["source"]} - the island is absent from the 1:10m county outline, so this pin stands in open '
                     f'water at the recorded point; not walkable: {s["walkable_reason"]}')})
        out.append((x['id'], hits[0]))
    return out
T.KEYS = {f'parishes.{k}': f'bay.{k}' for k in ('title', 'lede', 'canvas_label', 'minimap_label', 'help', 'h.quests',
                                                'quests_pending')}
T.OFFSHORE = offshore_pins(T.REG)
T.DEEP_WORLD = 'bay'   # DEEP's underwater.json bodies for this world (world == 'bay')
T.FAMILY_OF = [('campus', 'hall'), ('city', 'tower'), ('restoration', 'other')]
T.KITS_OFF = {'npcs': 'npcs/registry/npcs.json places guides in the New Orleans parishes only - no Bay county entries',
              'quests': 'quests/registry/quests.json names New Orleans parishes only - no Bay county quests',
              'layers': 'layers/registry/layers.json holds learning paths for the New Orleans parishes only'}
T.SEO = ('The Bay Area counties \u2014 SmartCiti.X : Trade Craft Academy',
         f'Walk and drive {len(T.REG["selection"]["selected"])} connected Bay Area counties: Census outlines (coarse), '
         'AUTHORED streets and districts, not official neighbourhoods.')
FOOT_A = 'Parish registry <code>parishes/registry/parishes.json</code>'
FOOT_B = ('County registry <code>bayarea/registry/bayarea.json</code> (via <code>bayarea/page_view.py</code>; '
          'districts AUTHORED, not official neighbourhoods; Treasure Island is absent from the 1:10m outline, so its '
          'campus is not placed)')
TITLE_A = '<title>SmartCiti.X : Trade Craft Academy — the parishes</title>'
TITLE_B = '<title>SmartCiti.X : Trade Craft Academy — the Bay Area counties</title>'
SWAPS = [(FOOT_A, FOOT_B), (TITLE_A, TITLE_B),
         ('<code>parishes/registry/world.json</code>', '<code>bayarea/registry/world.json</code>')]


def finish(page, states, why):
    for k, reason in T.KITS_OFF.items():
        if k in states and states[k] != 'stub':
            raise SystemExit(f'build_bayworld: kit {k} is not off')
        if k in why and why[k] in page:
            page = page.replace(why[k], reason)
    for a, b in SWAPS:
        if page.count(a) < 1:
            raise SystemExit(f'build_bayworld: anchor not found in the parish page: {a[:60]!r}')
        page = page.replace(a, b)
    # the page script looks chrome keys up by their PARISH names at runtime (JS_KEYS, t('parishes.x')): alias every
    # mapped parish key to its bay.* text in each embedded locale, so the runtime shows Bay text and never misses a key
    import json
    import re
    m = re.search(r'(<script type="application/json" id="parishes-i18n">)(.*?)(</script>)', page, flags=re.S)
    if not m:
        raise SystemExit('build_bayworld: embedded i18n catalog not found')
    cat = json.loads(m.group(2).replace('<\\/', '</'))
    for loc, c in cat.items():
        for pk, bk in T.KEYS.items():
            if bk in c['strings']:
                c['strings'][pk] = c['strings'][bk]
    # RESTORE (wave 9): restoration training scenarios at the placed restoration-site landmarks (web/restokit.py)
    sys.path.insert(0, str(HERE))
    import restokit
    for loc, c in cat.items():
        c['strings'].update(restokit.i18n_for(loc))
    blob = json.dumps(cat, ensure_ascii=False, sort_keys=True).replace('</', '<\\/')
    page = page[:m.start(2)] + blob + page[m.end(2):]
    lms = [(f'{f}-lm{j}', lm['name']) for f, p in T.REG['parishes'].items() for j, lm in enumerate(p['landmarks'])
           if lm['kind'] == 'restoration site' and f'<li data-landmark="{f}-lm{j}">' in page]
    lm_site, rk_css, rk_html = restokit.mount_for_landmarks(lms, 'parishes-i18n')
    for lid, site in lm_site.items():
        a = f'<li data-landmark="{lid}">'
        page = page.replace(a, a + f'<button type="button" class="rk-open" data-resto-run="{site}">Run training scenario</button> ', 1)
    for a, b in (('</head>', f'<style>{rk_css}</style>\n</head>'), ('</body>', rk_html + '</body>')):
        if page.count(a) != 1:
            raise SystemExit(f'build_bayworld: restokit anchor {a} found {page.count(a)}x')
        page = page.replace(a, b)
    n = re.search(r'· (\d+) parishes ·', page)
    if not n:
        raise SystemExit('build_bayworld: footer count anchor not found')
    return page.replace(n.group(0), f'· {n.group(1)} counties ·', 1)


T.finish = finish
sys.modules['__world_target__'] = T

EDITS = [
 ("PAGE = 'web/trade_craft_parishes.html'\n",
  "PAGE = 'web/trade_craft_parishes.html'\n"
  "# optional WORLD TARGET (web/build_bayworld.py): a module registered as sys.modules['__world_target__'] before this\n"
  "# builder runs supplies REG, WORLD, PAGE, KEYS, FAMILY_OF, KITS_OFF, SEO, finish(); absent => the parish page, unchanged\n"
  "_TGT = sys.modules.get('__world_target__')\n"
  "if _TGT is not None:\n"
  "    PAGE = _TGT.PAGE\n"
  "_K = (lambda k: _TGT.KEYS[k] if k in _TGT.KEYS else k) if _TGT is not None else (lambda k: k)\n"
  "_OFF = (lambda kit: kit in _TGT.KITS_OFF) if _TGT is not None else (lambda kit: False)\n"),
 ("def T(k):\n", "def T(k):\n    k = _K(k)\n"),
 ("def TS(k):\n", "def TS(k):\n    k = _K(k)\n"),
 ("def TA(k):\n", "def TA(k):\n    k = _K(k)\n"),
 ("REG = json.loads(REG_PATH.read_text())\n", "REG = _TGT.REG if _TGT is not None else json.loads(REG_PATH.read_text())\n"),
 ("    _w = json.loads((ROOT / 'parishes/registry/world.json').read_text())\n",
  "    _w = _TGT.WORLD if _TGT is not None else json.loads((ROOT / 'parishes/registry/world.json').read_text())\n"),
 ("\n\ndef family(kind):\n", "\nif _TGT is not None:\n    FAMILY_OF = FAMILY_OF + _TGT.FAMILY_OF\n\n\ndef family(kind):\n"),
 ("if (ROOT / 'npcs/registry/npcs.json').exists():\n", "if (ROOT / 'npcs/registry/npcs.json').exists() and not _OFF('npcs'):\n"),
 ("if (ROOT / 'layers/registry/layers.json').exists() and (HERE / 'pathkit.py').exists():\n",
  "if (ROOT / 'layers/registry/layers.json').exists() and (HERE / 'pathkit.py').exists() and not _OFF('layers'):\n"),
 ("if qreg_path.exists() and (HERE / 'questkit.py').exists():\n", "if qreg_path.exists() and (HERE / 'questkit.py').exists() and not _OFF('quests'):\n"),
 ("page = apply_seo(page, PAGE, 'The parishes", "if _TGT is not None:\n    page = _TGT.finish(page, STATES, WHY)\npage = apply_seo(page, PAGE, 'The parishes"),
 ("emit(HERE / 'trade_craft_parishes.html', page,", "emit(ROOT / PAGE, page,"),
 ("    DEEP_WORLD = 'parishes'   # the underwater.json world these pages draw (a world target may override it)\n",
  "    DEEP_WORLD = 'parishes'   # the underwater.json world these pages draw (a world target may override it)\n"
  "    DEEP_WORLD = _TGT.DEEP_WORLD if _TGT is not None else DEEP_WORLD\n"),
]

# browser run 02:44: with the NPC kit off (stub) npckit's makeClock is absent and the unguarded clock line threw at
# start-up. WORLDS (wave 10) moved the guard INTO web/build_parishes.py; this page has NPCs off, so the guarded line is
# REQUIRED here (exactly once) - a parish builder without it stops this build by name instead of shipping the crash.
NPC_GUARD = 'const npcClock = NPCD ? makeClock(8, 1 / 60) : null;'


def hooked_source():
    s = (HERE / 'build_parishes.py').read_text()
    if s.count(NPC_GUARD) != 1 or s.count('makeClock(8') != 1:
        raise SystemExit('build_bayworld: npc clock guard missing in web/build_parishes.py - expected exactly once: '
                         + repr(NPC_GUARD))
    for a, b in EDITS:
        if s.count(a) != 1:
            raise SystemExit(f'build_bayworld: the parish builder changed - hook anchor found {s.count(a)}x: {a[:60]!r}')
        s = s.replace(a, b)
    # the SEO strings: parameterise the one apply_seo call
    a = "page = apply_seo(page, PAGE, 'The parishes \\u2014 SmartCiti.X : Trade Craft Academy',\n                 'Walk and drive connected New Orleans parishes on flat authored ground: generic landmark assets, '\n                 'satellite imagery as a view-time layer only.', 'page')"
    if s.count(a) != 1:
        raise SystemExit('build_bayworld: the parish builder changed - SEO anchor not found')
    s = s.replace(a, "page = apply_seo(page, PAGE, *(_TGT.SEO if _TGT is not None else (\n    'The parishes \\u2014 SmartCiti.X : Trade Craft Academy',\n    'Walk and drive connected New Orleans parishes on flat authored ground: generic landmark assets, '\n    'satellite imagery as a view-time layer only.')), 'page')")
    return s


if __name__ == '__main__':
    sys.argv[0] = str(HERE / 'build_bayworld.py')
    g = {'__name__': '__main__', '__file__': str(HERE / 'build_parishes.py'), '__builtins__': __builtins__}
    exec(compile(hooked_source(), str(HERE / 'build_parishes.py'), 'exec'), g)
