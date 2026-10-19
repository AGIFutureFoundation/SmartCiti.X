"""modulelinks - links from the worlds back to their world training modules (wave 20).

Each walkable place that has a module carries one "Practice module" link to its module card on the Courses page
(web/trade_craft_courses.html#<module id>). Targets are never typed here: every id is read from
modules/registry/modules.json by family (restoration-site, wilds-world, robot-yard) and the page it lands on is
checked against the Courses page at build time. Anything missing stops the build by name (fail closed).

Links placed:
  - Bay restoration site panel (web/trade_craft_bay.html, #resto-site) and scenario runner (#resto-sims): one link per
    site that has a restoration module, shown with the panel for that site (bay_page).
  - Wilds site panel (web/trade_craft_wilds.html, #panel): one link per world, to that world's module (wilds_page).
  - Robot yard label (web/trade_craft_parishes.html and the Bay page, #robot-yard label): one link to the robot module,
    shown and hidden with the label (robot_yard_js).
  - Wave 21, the worksite districts (modules family worksite-district, read from each module's places): every work site
    section of the work sites page (worksite_hrefs), the Bay restoration panels of the sites where a work site stands
    (MODWS in bay_page), and the campus doors of the parish and Bay pages (campus_door_js, one map per page, only for
    doors that page carries).
Link text: i18n keys modlink.practice (Bay) and wilds.practice_module (wilds), all 8 locales; the robot label is English
like the label it sits beside. Stdlib only.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
REG_REL = 'modules/registry/modules.json'
COURSES = 'trade_craft_courses.html'
LOCALES = ('ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'zh')
KEY_BAY = 'modlink.practice'
KEY_WILDS = 'wilds.practice_module'
WS_REG_REL = 'worksites/registry/worksites.json'


class ModuleLinkError(SystemExit):
    pass


def _fail(msg):
    raise ModuleLinkError(f'modulelinks: {msg}')


def registry(root=ROOT):
    """modules.json, fail closed: missing, unreadable or without modules stops the build."""
    p = pathlib.Path(root) / REG_REL
    if not p.exists():
        _fail(f'{REG_REL} is missing - run python3 modules/build.py')
    try:
        reg = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        _fail(f'{REG_REL} does not parse: {e}')
    mods = reg.get('modules') if isinstance(reg, dict) else None
    if not isinstance(mods, list) or not mods:
        _fail(f'{REG_REL} has no modules list')
    ids = [m.get('id') for m in mods]
    if len(ids) != len(set(ids)) or not all(isinstance(i, str) and i.startswith('module-') for i in ids):
        _fail(f'{REG_REL} module ids must be unique strings starting with module-')
    return mods


def restoration_targets(mods):
    """site id -> module id, for every restoration-site module (each must name its site)."""
    out = {}
    for m in mods:
        if m.get('family') == 'restoration-site':
            site = m.get('site')
            if not isinstance(site, str) or not site:
                _fail(f'{m.get("id")} names no site')
            out[site] = m['id']
    if not out:
        _fail('no restoration-site modules in the registry')
    return out


def wilds_targets(mods):
    """wilds world id -> module id, for every wilds-world module (world reads 'wilds:<id>')."""
    out = {}
    for m in mods:
        if m.get('family') == 'wilds-world':
            w = m.get('world') or ''
            if not w.startswith('wilds:'):
                _fail(f'{m.get("id")} world {w!r} is not a wilds world')
            out[w.split(':', 1)[1]] = m['id']
    if not out:
        _fail('no wilds-world modules in the registry')
    return out


def robot_target(mods):
    """the one robot-yard module id."""
    ids = [m['id'] for m in mods if m.get('family') == 'robot-yard']
    if len(ids) != 1:
        _fail(f'expected exactly one robot-yard module, found {len(ids)}')
    return ids[0]


def href(module_id, mods):
    """the Courses-page link for a registry module; the id must be in the registry."""
    if module_id not in {m['id'] for m in mods}:
        _fail(f'{module_id} is not in the registry')
    return f'{COURSES}#{module_id}'


def labels(key, root=ROOT):
    """locale -> the string for key, from i18n/locales; every locale must carry a non-empty string."""
    out = {}
    for loc in LOCALES:
        p = pathlib.Path(root) / 'i18n' / 'locales' / f'{loc}.json'
        try:
            s = json.loads(p.read_text(encoding='utf-8'))['strings']
        except (OSError, ValueError, KeyError) as e:
            _fail(f'{p.name} cannot supply {key}: {e}')
        v = s.get(key)
        if not isinstance(v, str) or not v.strip():
            _fail(f'{loc} has no {key}')
        out[loc] = v
    return out


def _once(page, anchor, label):
    n = page.count(anchor)
    if n != 1:
        _fail(f'{label}: anchor must occur exactly once, found {n}: {anchor.strip()[:60]!r}')
    return page


def _js(s):
    return json.dumps(s, ensure_ascii=False).replace('</', '<\\/')


def worksite_targets(mods):
    """(worksite id -> district module id, (place kind, place id) -> district module id) from the worksite-district
    modules' places. A worksite may sit in one district module only, and a campus or restoration site may carry one
    district module only; anything else stops the build by name."""
    by_ws, by_place = {}, {}
    for m in mods:
        if m.get('family') != 'worksite-district':
            continue
        places = m.get('places')
        if not isinstance(places, list) or not places:
            _fail(f'{m.get("id")} names no places')
        for p in places:
            ws, kind, pid = p.get('worksite'), p.get('place_kind'), p.get('place')
            if not isinstance(ws, str) or not ws or not isinstance(pid, str) or not pid:
                _fail(f'{m.get("id")} has a place without a worksite or place id')
            if ws in by_ws:
                _fail(f'worksite {ws} sits in two district modules ({by_ws[ws]}, {m["id"]})')
            by_ws[ws] = m['id']
            if kind in ('campus', 'restoration-site'):
                prev = by_place.get((kind, pid))
                if prev not in (None, m['id']):
                    _fail(f'{kind} {pid} carries two district modules ({prev}, {m["id"]})')
                by_place[(kind, pid)] = m['id']
    if not by_ws:
        _fail('no worksite-district places in the registry')
    return by_ws, by_place


def worksite_hrefs(root=ROOT):
    """worksite id -> Courses-page link of its district module, for every worksite in worksites.json (fail closed)."""
    mods = registry(root)
    by_ws, _ = worksite_targets(mods)
    p = pathlib.Path(root) / WS_REG_REL
    try:
        ids = [s['id'] for s in json.loads(p.read_text(encoding='utf-8'))['sites']]
    except (OSError, ValueError, KeyError, TypeError) as e:
        _fail(f'{WS_REG_REL} cannot supply the work sites: {e}')
    missing = [w for w in ids if w not in by_ws]
    extra = sorted(set(by_ws) - set(ids))
    if missing or extra:
        _fail(f'district modules and {WS_REG_REL} disagree: no module for {missing}, module for unknown {extra}')
    return {w: href(by_ws[w], mods) for w in ids}


def worksite_label(root=ROOT):
    """The English link text on the work sites page (the same modlink.practice key the worlds use)."""
    return labels(KEY_BAY, root)['en']


def bay_page(page, root=ROOT):
    """Bay page: one script (before </body>) that puts the site's link at the end of the restoration site panel and
    the scenario runner panel, shown while that panel is open on a site that has a module. A restoration site where a
    work site of a district module stands gets a second row (MODWS) to that district module."""
    mods = registry(root)
    targets = restoration_targets(mods)
    rows = {site: href(mid, mods) for site, mid in targets.items()}
    _, by_place = worksite_targets(mods)
    wrows = {}
    for (kind, pid), mid in by_place.items():
        if kind != 'restoration-site':
            continue
        if pid not in targets:
            _fail(f'restoration site {pid} carries a district module but has no restoration module')
        wrows[pid] = href(mid, mods)
    lbl = labels(KEY_BAY, root)
    _once(page, '</body>', 'bay_page')
    js = ('(function () {\n'
          f'  const MOD = {json.dumps(rows, sort_keys=True)};\n'
          f'  const MODWS = {json.dumps(wrows, sort_keys=True)};\n'
          f'  const LBL = {json.dumps(lbl, ensure_ascii=False, sort_keys=True)};\n'
          '  function modSync(p) {\n'
          '    for (const x of p.querySelectorAll(\'[data-module-link]\')) x.remove();\n'
          '    if (p.hidden) return;\n'
          '    const lang = Object.hasOwn(LBL, document.documentElement.lang) ? document.documentElement.lang : \'en\';\n'
          '    for (const M of [MOD, MODWS]) {\n'
          '      const h = Object.hasOwn(M, p.dataset.site) ? M[p.dataset.site] : null;\n'
          '      if (!h) continue;\n'
          '      const row = document.createElement(\'p\'), a = document.createElement(\'a\');\n'
          '      row.dataset.moduleLink = \'\'; a.className = \'module-link-in\'; a.href = h; a.textContent = LBL[lang];\n'
          '      row.appendChild(a); p.appendChild(row);\n'
          '    }\n'
          '  }\n'
          '  for (const id of [\'resto-site\', \'resto-sims\']) {\n'
          '    const p = document.getElementById(id);\n'
          '    if (p) { new MutationObserver(() => modSync(p)).observe(p, { attributes: true, attributeFilter: [\'hidden\', \'data-site\'] }); modSync(p); }\n'
          '  }\n'
          '})();\n')
    block = f'<script id="module-link-kit">{js}</script>\n'
    return page.replace('</body>', block + '</body>', 1)


def campus_door_js(door_ids, root=ROOT):
    """Parish and Bay JS (after the DOOR-LINK block): a campus door on this page (door_ids, the DOOR-LINK ids) whose campus
    carries a work site of a district module gets a second 'Practice module' link beneath it, shown and hidden with the
    door. The campus key is the door id 'campus:<key>' (the place id in worksites.json). Fails closed if the page has
    no such door, so a page never ships an empty map."""
    mods = registry(root)
    _, by_place = worksite_targets(mods)
    on_page = set(door_ids)
    rows = {f'campus:{pid}': href(mid, mods) for (kind, pid), mid in by_place.items()
            if kind == 'campus' and f'campus:{pid}' in on_page}
    if not rows:
        _fail('no campus door on this page carries a worksite-district module')
    lbl = labels(KEY_BAY, root)
    return ('/* MODULE-LINK doors (wave 21): a campus door gets a "Practice module" link beneath it when a work site of a '
            'district module stands on that campus. */\n'
            f'const MOD_DOOR = {json.dumps(rows, sort_keys=True)};\n'
            f'const MOD_DOOR_LBL = {json.dumps(lbl, ensure_ascii=False, sort_keys=True)};\n'
            'for (let i = 0; i < DL_DOORS.length; i++) {\n'
            '  const d = DL_DOORS[i];\n'
            '  if (!Object.hasOwn(MOD_DOOR, d.id)) continue;\n'
            '  const a = DL.els[i], m = document.createElement(\'a\');\n'
            '  const lang = Object.hasOwn(MOD_DOOR_LBL, document.documentElement.lang) ? document.documentElement.lang : \'en\';\n'
            "  m.className = 'door-link module-link-door'; m.href = MOD_DOOR[d.id]; m.textContent = MOD_DOOR_LBL[lang]; m.hidden = true;\n"
            "  m.dataset.moduleLink = ''; m.style.transform = 'translate(-50%, 0)';\n"
            "  stage.appendChild(m);\n"
            "  new MutationObserver(() => { m.hidden = a.hidden; m.style.left = a.style.left; "
            "m.style.top = (parseFloat(a.style.top) + 6) + 'px'; }).observe(a, { attributes: true, attributeFilter: ['hidden', 'style'] });\n"
            '}\n')


def wilds_page(page, root=ROOT):
    """Wilds page: the site panel gets one 'Practice module' link to its world's module (MODULE-LINK rows)."""
    mods = registry(root)
    targets = wilds_targets(mods)
    rows = {wid: href(mid, mods) for wid, mid in targets.items()}
    _once(page, 'function openSite(id) {\n', 'wilds_page')
    _once(page, '  panel.hidden = false; openId = id;\n', 'wilds_page')
    head = ('const MOD_WILDS = ' + json.dumps(rows, sort_keys=True) + ';\n'
            'function modLinkRow() {\n'
            '  const h = Object.hasOwn(MOD_WILDS, W.id) ? MOD_WILDS[W.id] : null; if (!h) return;\n'
            '  const p = document.createElement(\'p\'), a = document.createElement(\'a\');\n'
            '  p.dataset.moduleLink = \'\'; a.className = \'module-link-in\'; a.href = h; a.textContent = L[\'practice_module\'];\n'
            '  p.appendChild(a); panelBody.appendChild(p);\n'
            '}\n')
    page = page.replace('function openSite(id) {\n', head + 'function openSite(id) {\n', 1)
    page = page.replace('  panel.hidden = false; openId = id;\n', '  modLinkRow();\n  panel.hidden = false; openId = id;\n', 1)
    return page


def robot_yard_js(js, root=ROOT):
    """Parish JS (the ROVER-YARD block): a second label, 'Practice module', beside the yard label."""
    mods = registry(root)
    h = href(robot_target(mods), mods)
    anchor = 'stage.appendChild(ryLab);\n'
    _once(js, anchor, 'robot_yard_js')
    add = ("const ryMod = document.createElement('a');\n"
           f"ryMod.className = 'robot-yard-label'; ryMod.href = {_js(h)}; ryMod.textContent = 'Practice module'; ryMod.hidden = true;\n"
           "ryMod.setAttribute('data-module-link', ''); ryMod.style.cssText = ryLab.style.cssText;\n"
           "stage.appendChild(ryMod);\n"
           "new MutationObserver(() => { ryMod.hidden = ryLab.hidden; ryMod.style.left = ryLab.style.left; "
           "ryMod.style.top = (parseFloat(ryLab.style.top) - 26) + 'px'; }).observe(ryLab, { attributes: true, attributeFilter: ['hidden', 'style'] });\n")
    return js.replace(anchor, anchor + add, 1)


def wilds_label_key():
    return KEY_WILDS
