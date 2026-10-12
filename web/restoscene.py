"""restoscene - habitat scenes, restoration crews and site panels at the Bay restoration sites (web/trade_craft_bay.html).

Wave 18 (RESTORE). Mounted ONLY by the anchored RESTORE block in web/build_bayworld.py (which wraps the world target's
finish()); this module edits no file. Page markers are neutral: HABITAT-SCENE (3D), RESTORE-SITE (panel), SITE-CREW.

  site_rows(reg, page)   -> the per-site rows the page embeds (fails closed on every registry field it reads)
  SCENE_JS               the page script: pure core (rsPlan, between HABITAT-SCENE CORE BEGIN/END) + the mount
  PANEL_CSS / panel_html(rows, cat_id) / panel_js()
  mount(page, reg, cat)  -> page with everything inserted (each anchor exactly once, else RestoSceneError)

What is RECORDED, what is AUTHORED (and the page says so):
  - RECORDED: each site's point (the landmark's world_m, from restoration/registry/restoration.json lat/lng via
    bayarea), its habitat line, its recorded ground, walkable / walkable_reason, the scenario and staged-task lines,
    the rubric and the funding context - all quoted verbatim with their registry paths.
  - AUTHORED: the habitat scene. LAYER_RULE picks layers from words in the site's OWN habitat / ground / ground_why
    text (the matched words are printed); rsPlan lays the layers out by a fixed rule around the recorded point,
    oriented to the nearest AUTHORED water. Generic forms; not a survey, not the project's design, no acreage or
    species count. Colours of the ground pads are DERIVED from world/registry/world.json ground recipes.
  - SCRIPTED crew: roster agents from hive/registry/hive.json (name, outfit proxy colours, voice). A crew member says
    ONLY the scenario's own lines (title, steps, safety gates) and the staged task's title and brief, verbatim, with
    their paths; voice on a click (HiveVoice, on-device speech only) and a Mute switch. No line is written here.
Non-walkable sites (the active federal cleanup sites) get no scene and no crew: their panel quotes walkable_reason.
"""
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent


class RestoSceneError(Exception):
    pass


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise RestoSceneError(f'restoscene: {where} has no "{k}"')
    return d[k]


def _load(rel):
    p = ROOT / rel
    if not p.exists():
        raise RestoSceneError(f'restoscene: {rel} is missing')
    return json.loads(p.read_text(encoding='utf-8'))


# ---- the AUTHORED layer rule: (layer, field, regex) - a layer is drawn when the site's OWN text matches -------------
LAYER_RULE = [
    ('nursery', 'ground_why', r'nursery'),
    ('upland-planting', 'habitat', r'upland|shoreline|green infrastructure'),
    ('riprap', 'habitat+ground', r'shoreline.*\|upland$'),
    ('living-shoreline', 'habitat', r'shoreline'),
    ('seasonal-wetland', 'habitat', r'seasonal'),
    ('transition', 'habitat', r'transition|upland'),
    ('levee-crown', 'ground', r'^levee$'),
    ('tidal-marsh', 'habitat', r'marsh|wetland|tidal'),
    ('channels', 'habitat+ground', r'(marsh|wetland|tidal).*\|(marsh|mudflat|levee)$'),
    ('salt-pond-cells', 'habitat', r'pond'),
    ('mudflat', 'ground', r'^(mudflat|marsh|levee)$'),
]
# a transition band needs a marsh to transition into
LAYER_NEEDS = {'transition': 'tidal-marsh'}
LAYER_TITLE = {  # AUTHORED short names shown beside each layer (English, like the registry text they sit next to)
    'nursery': 'nursery rows', 'upland-planting': 'upland native planting', 'riprap': 'riprap revetment',
    'living-shoreline': 'living shoreline (coir logs, planted terrace, rock sill)', 'seasonal-wetland': 'seasonal wetland',
    'transition': 'wetland-upland transition band', 'levee-crown': 'levee crown', 'tidal-marsh': 'tidal marsh (pickleweed and cordgrass bands)',
    'channels': 'tidal channels', 'salt-pond-cells': 'salt-pond levees and cells', 'mudflat': 'mudflat'}
SCENE_LABEL = ('Habitat scene: AUTHORED by a fixed rule from this site\'s own recorded habitat and ground text, laid around '
               'the RECORDED point; generic forms, not a survey and not the project\'s design.')
CREW_LABEL = ('Crew: SCRIPTED roster agents (no AI model). They say only this site\'s scenario and staged-task lines, '
              'quoted with their source; the device\'s own speech, on a click.')
GROUND_MIX = 0.5   # pad colour = mix(recipe base, recipe grain, GROUND_MIX) - DERIVED from world.json


def layers_for(site):
    """[{layer, field, quote}] in LAYER_RULE order; quote is the matched words of the site's own text."""
    txt = {'habitat': need(site, 'habitat', site['id']), 'ground': need(site, 'ground', site['id']),
           'ground_why': need(site, 'ground_why', site['id'])}
    out = []
    for layer, field, rx in LAYER_RULE:
        s = txt['habitat'] + '|' + txt['ground'] if field == 'habitat+ground' else txt[field]
        m = re.search(rx, s)
        if m:
            out.append({'layer': layer, 'field': field, 'quote': m.group(0)})
    have = {x['layer'] for x in out}
    out = [x for x in out if x['layer'] not in LAYER_NEEDS or LAYER_NEEDS[x['layer']] in have]
    if not out:
        raise RestoSceneError(f'restoscene: {site["id"]} - no layer matches its recorded habitat/ground text')
    return out


def _hexmix(rec, t):
    b = int(rec['base'][1:], 16)
    br, bg, bb = (b >> 16) & 255, (b >> 8) & 255, b & 255
    gr, gg, gb = (int(v) for v in rec['grain'].split(','))
    return (round(br + (gr - br) * t) << 16) | (round(bg + (gg - bg) * t) << 8) | round(bb + (gb - bb) * t)


def ground_colours():
    g = need(_load('world/registry/world.json'), 'ground', 'world.json')
    return {k: _hexmix(need(g, k, 'world.json ground'), GROUND_MIX) for k in ('marsh', 'mudflat', 'upland', 'levee', 'water', 'sand', 'gravel')}


def _pick(cands, key, used):
    if not cands:
        raise RestoSceneError(f'restoscene: no roster candidate for {key}')
    i = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % len(cands)
    for k in range(len(cands)):
        a = cands[(i + k) % len(cands)]
        if a['id'] not in used:
            return a
    return cands[i]


def site_rows(reg, page):
    """One row per restoration site of restoration/registry/restoration.json that the Bay page shows (a landmark row on
    the page) - walkable sites get layers, crew and scene data; non-walkable ones carry walkable_reason verbatim."""
    rest = _load('restoration/registry/restoration.json')
    scr = _load('restoration/registry/scenarios.json')
    hive = _load('hive/registry/hive.json')
    courses = need(_load('courses/registry/courses.json'), 'courses', 'courses.json')
    lessons_page = (ROOT / 'web/trade_craft_lessons.html').read_text(encoding='utf-8')
    sites = {s['id']: s for s in need(rest, 'sites', 'restoration.json')}
    by_name = {need(s, 'name', 'site'): sid for sid, s in sites.items()}
    sc_all = need(scr, 'scenarios', 'scenarios.json')
    tasks = need(scr, 'staged_tasks', 'scenarios.json')
    agents = need(hive, 'agents', 'hive.json')
    rows = []
    for f, p in reg['parishes'].items():
        for j, lm in enumerate(p['landmarks']):
            if not need(lm, 'kind', f'{f}.landmarks[{j}]').startswith('restoration site'):
                continue
            lid = f'{f}-lm{j}'
            name = lm['name'].split('\n')[0]
            if name not in by_name:
                raise RestoSceneError(f'restoscene: landmark {lid} ({name}) names no restoration site')
            sid = by_name[name]
            s = sites[sid]
            if need(lm, 'provenance', lid) != 'RECORDED' or [lm['lat'], lm['lng']] != [s['lat'], s['lng']]:
                raise RestoSceneError(f'restoscene: {lid} is not at the RECORDED point of {sid}')
            on_page = f'<li data-landmark="{lid}">' in page
            runner = lm['kind'] == 'restoration site'
            walk = need(s, 'walkable', sid)
            if walk is not True and not need(s, 'walkable_reason', sid):
                raise RestoSceneError(f'restoscene: {sid} is not walkable and has no walkable_reason')
            scs = [(i, x) for i, x in enumerate(sc_all) if x['site'] == sid]
            tks = [(i, t) for i, t in enumerate(tasks) if need(need(t, 'place', 'task'), 'id', 'task.place') == sid]
            row = {'id': sid, 'lm': lid, 'on_page': on_page, 'runner': runner, 'name': s['name'], 'org': need(s, 'org', sid),
                   'source_url': need(s, 'source_url', sid), 'x': lm['world_m'][0], 'z': -lm['world_m'][1],   # the page's frame: z = -north (build_parishes)
                   'walkable': walk is True, 'walkable_reason': s['walkable_reason'], 'habitat': need(s, 'habitat', sid),
                   'ground': s['ground'], 'ground_why': s['ground_why'],
                   'src': f'restoration/registry/restoration.json#sites[{sid}]',
                   'scenarios': [{'id': x['id'], 'title': need(x, 'title', x['id']), 'label': need(x, 'label', x['id']),
                                  'type': x['type'], 'src': f'restoration/registry/scenarios.json#scenarios[{i}]',
                                  'steps': [need(st, 'text', x['id']) for st in need(x, 'steps', x['id'])],
                                  'gates': [need(g, 'text', x['id']) for g in need(x, 'safety_gates', x['id'])],
                                  'crew': [[need(r, 'role', x['id']), need(r, 'trade', x['id'])] for r in need(x, 'crew', x['id'])]}
                                 for i, x in scs],
                   'tasks': [{'id': t['id'], 'title': need(t, 'title', t['id']), 'brief': need(t, 'brief', t['id']),
                              'href': need(need(t, 'launch', t['id']), 'href', t['id']), 'kind': need(t, 'kind', t['id']),
                              'src': f'restoration/registry/scenarios.json#staged_tasks[{i}]'} for i, t in tks]}
            if not row['scenarios']:
                raise RestoSceneError(f'restoscene: {sid} has no scenario')
            # courses and lessons: the course of each crew trade (courses/registry/courses.json trade.<trade>)
            trades = []
            for x in row['scenarios']:
                for _, tr in x['crew']:
                    if tr not in trades:
                        trades.append(tr)
            row['courses'] = []
            for tr in trades:
                c = courses.get('trade.' + tr)
                if c is None:
                    raise RestoSceneError(f'restoscene: {sid} crew trade {tr} has no course trade.{tr}')
                ls = []
                for o in need(c, 'outline', c['id']):
                    if f'id="lesson-{o["lesson"]}"' not in lessons_page:
                        raise RestoSceneError(f'restoscene: lesson {o["lesson"]} has no card on web/trade_craft_lessons.html')
                    ls.append({'id': o['lesson'], 'title': need(o, 'title', o['lesson']), 'href': f'trade_craft_lessons.html#lesson-{o["lesson"]}'})
                row['courses'].append({'id': c['id'], 'title': need(c, 'title', c['id']), 'trade': tr,
                                       'href': 'trade_craft_courses.html', 'src': f'courses/registry/courses.json#courses[{c["id"]}]', 'lessons': ls})
            if row['walkable']:
                row['layers'] = layers_for(s)
                # crew: one roster agent per crew role of the site's scenarios (registry order). AUTHORED pick rule:
                # the hive's world-guide mentors of the role's trade district (courses.json trade.<t>.district), index
                # sha256('<site>:<role>') mod n, skipping an agent already on this site's crew.
                crew, used = [], set()
                for k, x in enumerate(row['scenarios']):
                    for role, tr in x['crew']:
                        if any(c['role'] == role for c in crew):
                            continue
                        dist = courses['trade.' + tr]['district']
                        cands = sorted((a for a in agents if a['kind'] == 'npc' and a['role'] == 'mentor' and a['family'] == dist), key=lambda a: a['id'])
                        a = _pick(cands, f'{sid}:{role}', used)
                        used.add(a['id'])
                        px = need(need(a, 'avatar', a['id']), 'proxy', a['id'])
                        t0 = row['tasks'][[t['id'] for t in row['tasks']].index('resto-sim-' + x['id'][3:])] if ('resto-sim-' + x['id'][3:]) in [t['id'] for t in row['tasks']] else None
                        lines = [[x['title'], x['src'] + '.title']] + [[st, f'{x["src"]}.steps[{n}].text'] for n, st in enumerate(x['steps'])] \
                            + [[g, f'{x["src"]}.safety_gates[{n}].text'] for n, g in enumerate(x['gates'])]
                        if t0 is not None:
                            lines += [[t0['title'], t0['src'] + '.title'], [t0['brief'], t0['src'] + '.brief']]
                        crew.append({'agent': a['id'], 'name': a['name'], 'name_src': need(a, 'name_source', a['id']),
                                     'role': role, 'trade': tr, 'scenario': x['id'],
                                     'col': {k2: int(need(need(px, k2, a['id']), 'hex', a['id'])[1:], 16) for k2 in ('torso', 'legs', 'head', 'hat', 'vest')},
                                     'voice': {'pitch': need(a, 'voice', a['id'])['pitch'], 'rate': a['voice']['rate']},
                                     'lines': lines})
                row['crew'] = crew
            rows.append(row)
    ids = [r['id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise RestoSceneError('restoscene: a site appears on two landmarks')
    return rows, {'rubric': need(scr, 'rubric', 'scenarios.json'), 'funding': need(scr, 'funding_context', 'scenarios.json'),
                  'funding_src': 'restoration/registry/scenarios.json#funding_context', 'rubric_src': 'restoration/registry/scenarios.json#rubric',
                  'honesty': need(scr, 'honesty', 'scenarios.json'), 'scene_label': SCENE_LABEL, 'crew_label': CREW_LABEL,
                  'layer_title': LAYER_TITLE, 'col': ground_colours(), 'stamps': {'scenarios': scr['source_stamp'], 'restoration': rest['source_stamp'], 'hive': hive['source_stamp']}}


# ---- the page script -------------------------------------------------------------------------------------------------
SCENE_JS = r"""/* HABITAT-SCENE BEGIN: AUTHORED habitat scenes at the RECORDED Bay restoration-site points - tidal marsh (pickleweed
   and cordgrass bands, channels), mudflat, salt-pond levees and cells, restored shoreline (riprap, living shoreline),
   upland planting, nursery rows - picked by a fixed rule from each site's own recorded habitat text, oriented to the
   nearest AUTHORED water. Five InstancedMeshes (pads, tufts, rocks, berms, boxes), drawn only within RS_VIEW m of the
   site nearest the eye and never in the overview; tufts and rocks only within RS_NEAR m. Generic forms, not a survey. */
/* HABITAT-SCENE CORE BEGIN */
const RS_LAND = 42, RS_WET = 85, RS_CLEAR = 9, RS_VIEW = 650, RS_NEAR = 300, RS_WATER_Y = -0.4;
const RS_CAP = { pad: 220, tuft: 700, rock: 290, berm: 70, box: 200 };
const RS_TRIS = { pad: 2, tuft: 6, rock: 20, berm: 10, box: 12 };
const RS_SP = {   /* AUTHORED plant forms: [colours], height range, width range */
  cord: [[0x6f8f3a, 0x7d9a44, 0x5f7f34], [0.9, 1.4], [0.7, 1.0]], pickle: [[0x8a5a3c, 0x7f7a3a, 0x6f8a3c], [0.22, 0.4], [0.7, 1.1]],
  grass: [[0xa49a5c, 0x8f9450, 0xb2a568], [0.45, 0.8], [0.6, 0.9]], shrub: [[0x3f5a32, 0x4a6638, 0x56703e], [0.9, 1.6], [1.2, 1.9]],
  seedling: [[0x5f8a3c, 0x6f9a48], [0.25, 0.45], [0.3, 0.45]] };
const RS_ROCK = [0x77736a, 0x6a665e, 0x837d70, 0x5e5b55];
const RS_BOX = { coir: 0x6b5232, bench: 0x8b6f52, pot: 0x3a3430, stake: 0xd8c23a, post: 0x5a4a38, board: 0x2f5a46 };
/* the direction of the nearest AUTHORED water: 24 bearings, each sampled every 5 m to 300 m, then every 25 m to 3 km, for its first wet
   or off-county point at distance d; the direction is the sum of the hit bearings weighted 1/d^4 (so the nearest shore
   dominates and two equal shores average). No hit within 3 km: bearing 0 and d null. */
function rsWaterDir(site, env) {
  let sx = 0, sz = 0, dmin = null;
  for (let b = 0; b < 24; b++) {
    const a = b * Math.PI / 12, wx = Math.sin(a), wz = -Math.cos(a);
    for (let d = 5; d <= 3000; d += d < 300 ? 5 : 25) { const p = env.probe(site.x + wx * d, site.z + wz * d, true); if (p === 'water' || p === 'out') { const w = 1 / (d * d * d * d); sx += wx * w; sz += wz * w; if (dmin === null || d < dmin) dmin = d; break; } }
  }
  const n = Math.hypot(sx, sz);
  return n > 0 ? { wx: sx / n, wz: sz / n, d: dmin } : { wx: 0, wz: -1, d: null };
}
/* a jittered grid of points over a (u, v) rectangle; every term is a hash of the cell, the layer key and the site seed */
function rsGrid(u0, u1, v0, v1, step, k, env, fn) {
  for (let i = 0; u0 + i * step < u1; i++) for (let j = 0; v0 + j * step < v1; j++) {
    const h1 = env.hash(i, j, k), h2 = env.hash(i, j, k + 1), h3 = env.hash(i, j, k + 2);
    fn(u0 + (i + 0.1 + 0.8 * h1) * step, v0 + (j + 0.1 + 0.8 * h2) * step, h3, i + ':' + j);
  }
}
function rsLayout(site, has, env) {
  const C = [], add = (fam, key, u, v, y0, yaw, sx, sy, sz, col, opt) => C.push({ fam, key, u, v, y0, yaw, sx, sy, sz, col, land: !!(opt && opt.land), wet: !!(opt && opt.wet), lift: (opt && opt.lift) || 0 });
  const col = env.col, pick = (a, h) => a[Math.min(a.length - 1, Math.floor(h * a.length))];
  const tuft = (sp, k, u0, u1, v0, v1, step, keep, opt) => rsGrid(u0, u1, v0, v1, step, k, env, (u, v, h, id) => {
    if (h > keep) return; const S = RS_SP[sp], g = env.hash(Math.round(u * 7), Math.round(v * 7), k + 9);
    add('tuft', sp + k + ':' + id, u, v, 0, g * 6.283, S[2][0] + (S[2][1] - S[2][0]) * h, S[1][0] + (S[1][1] - S[1][0]) * g, S[2][0] + (S[2][1] - S[2][0]) * (1 - h), pick(S[0], g), opt);
  });
  const pads = (k, u0, u1, v0, v1, size, c, lift, opt) => rsGrid(u0, u1, v0, v1, size, k, env, (u, v, h, id) => {
    const t = 0.88 + 0.24 * h, r = Math.min(255, ((c >> 16) & 255) * t), g = Math.min(255, ((c >> 8) & 255) * t), b = Math.min(255, (c & 255) * t);
    add('pad', 'p' + k + ':' + id, u, v, 0, 0, size * 1.08, 1, size * 1.08, (r << 16) | (g << 8) | b, { lift, land: opt && opt.land, wet: opt && opt.wet });
  });
  const berm = (k, ua, va, ub, vb, base, hgt, c, gaps) => {   /* a levee as 6 m berm segments; gaps: segment indices left open */
    const L = Math.hypot(ub - ua, vb - va), n = Math.max(1, Math.round(L / 6)), yaw = Math.atan2(-(vb - va), ub - ua);
    for (let s = 0; s < n; s++) { if (gaps && gaps.includes(s)) continue; const t = (s + 0.5) / n; add('berm', 'b' + k + ':' + s, ua + (ub - ua) * t, va + (vb - va) * t, 0, yaw, L / n + 0.3, hgt, base, c); }
  };
  const marsh = has['tidal-marsh'], shore = has['riprap'] || has['living-shoreline'];
  if (has['salt-pond-cells']) {
    /* managed ponds: an ecotone levee (wide, gentle), then 2 x 2 cells walled by levees; the far +u cell is breached and
       holds mudflat and cordgrass instead of pond water */
    berm('eco', -40, -16, 40, -16, 12, 1.3, col.levee);
    tuft('grass', 11, -38, 38, -40, -24, 2.6, 0.7);
    tuft('pickle', 12, -38, 38, -11, -7, 1.6, 0.85);
    for (const vv of [-4, 16, 36]) berm('cv' + vv, -36, vv, 36, vv, 5, 1.6, col.levee, vv === 36 ? [8, 9, 10] : null);
    for (const uu of [-36, 0, 36]) berm('cu' + uu, uu, -4, uu, 36, 5, 1.6, col.levee);
    pads(21, -34, -2, -2, 14, 6, col.water, 0.05); pads(22, 2, 34, -2, 14, 6, col.water, 0.05); pads(23, -34, -2, 18, 34, 6, col.water, 0.05);
    pads(24, 2, 34, 18, 34, 6, col.mudflat, 0.04);
    tuft('cord', 25, 4, 32, 18, 34, 2.4, 0.45);
    pads(26, -40, 40, 40, 70, 7, col.mudflat, 0.03, { wet: true });
  } else {
    let v0 = -40;
    if (has['nursery']) {
      /* nursery rows: benches with pots and seedlings, landward */
      for (let r = 0; r < 3; r++) for (let s = -2; s <= 2; s++) {
        const u = s * 6.5, v = -36 + r * 4.5, k = 'n' + r + ':' + s;
        add('box', k, u, v, 0, 0, 5, 0.75, 1.2, RS_BOX.bench, { land: true });
        for (let q = 0; q < 4; q++) add('box', k + 'p' + q, u - 1.8 + q * 1.2, v, 0.75, 0, 0.35, 0.3, 0.35, RS_BOX.pot, { land: true });
        tuft('seedling', 40 + r * 7 + s, u - 2.2, u + 2.2, v - 0.5, v + 0.5, 0.6, 0.9, { land: true, lift: 1.05 });
      }
      v0 = -30;
    }
    if (has['seasonal-wetland']) {
      /* seasonal wetland behind the levee: shallow ponded pads among pickleweed and grass */
      pads(31, -40, 40, -40, -8, 7, col.marsh, 0.03);
      rsGrid(-40, 40, -40, -8, 14, 32, env, (u, v, h, id) => { if (h < 0.5) add('pad', 'sw' + id, u, v, 0, h * 3, 6 + 5 * h, 1, 4 + 4 * h, col.water, { lift: 0.06 }); });
      tuft('pickle', 33, -40, 40, -40, -8, 2.0, 0.55); tuft('grass', 34, -40, 40, -40, -30, 2.4, 0.6);
      v0 = 99;
    }
    if (has['levee-crown']) {
      berm('crown', -44, -4, 44, -4, 7, 2, col.levee);
      for (let s = -3; s <= 3; s++) add('box', 'stake' + s, s * 12, -4, 2, 0, 0.07, 1.1, 0.07, RS_BOX.stake);
    }
    const shoreV = marsh ? 16 : 6;
    if (has['upland-planting'] || has['transition']) {
      const v1 = marsh ? (has['transition'] ? -12 : -20) : shoreV;
      if (v0 < v1) {
        tuft('grass', 42, -40, 40, v0, v1, 2.3, 0.62, { land: true });
        tuft('shrub', 43, -40, 40, v0, v1, 6.5, 0.5, { land: true });
      }
    }
    if (marsh) {
      const m0 = has['levee-crown'] ? 0 : -20;
      pads(51, -40, 40, m0, shoreV, 6, col.marsh, 0.04);
      tuft('pickle', 52, -40, 40, m0, m0 + (shoreV - m0) * 0.45, 1.5, 0.82);
      tuft('cord', 53, -40, 40, m0 + (shoreV - m0) * 0.45, shoreV, 1.7, 0.78);
      if (has['transition']) tuft('grass', 54, -40, 40, m0 - 8, m0 + 2, 2.0, 0.45);
    }
    if (has['channels']) {
      /* two meandering channels from the flat into the marsh: pads of open water along a sine path */
      const cv0 = has['levee-crown'] ? 2 : -18;
      for (const [k, u0, amp] of [[0, -14, 6], [1, 17, 4]]) for (let v = 60; v > cv0; v -= 2.4) {
        const u = u0 + amp * Math.sin(v / 9 + k * 2), w = 2.2 + 2.6 * Math.max(0, (v + 18) / 78);
        add('pad', 'ch' + k + ':' + v.toFixed(1), u, v, 0, Math.atan2(amp * Math.cos(v / 9 + k * 2) / 9, 1), w, 1, 2.9, col.water, { lift: 0.07 });
      }
    }
    if (has['mudflat']) pads(61, -44, 44, shoreV, 70, 7, col.mudflat, 0.03, { wet: true });   // the open flat: only where the world has water or no county land
    if (has['riprap']) {
      /* riprap: a band of placed rock along the shore, on the -u half when a living shoreline shares the reach */
      const ru1 = has['living-shoreline'] ? -2 : 40;
      rsGrid(-40, ru1, shoreV, shoreV + 12, 1.5, 71, env, (u, v, h, id) => add('rock', 'r' + id, u, v, -0.15, h * 6.283, 0.7 + 0.7 * h, 0.45 + 0.4 * env.hash(Math.round(u * 5), Math.round(v * 5), 72), 0.7 + 0.6 * (1 - h), pick(RS_ROCK, h)));
    }
    if (has['living-shoreline']) {
      /* living shoreline: coir logs along two contours, a planted terrace between them, a low rock sill offshore */
      const lu0 = has['riprap'] ? 2 : -40;
      for (const vv of [shoreV + 1, shoreV + 9]) for (let u = lu0 + 1.6; u < 40; u += 3.3) add('box', 'coir' + vv + ':' + u.toFixed(1), u, vv, 0, 0, 3.0, 0.35, 0.35, RS_BOX.coir);
      tuft('cord', 81, lu0, 40, shoreV + 1.5, shoreV + 8.5, 1.6, 0.85);
      tuft('pickle', 82, lu0, 40, shoreV - 3, shoreV + 1, 1.5, 0.8);
      rsGrid(lu0, 40, shoreV + 18, shoreV + 21, 1.4, 83, env, (u, v, h, id) => add('rock', 's' + id, u, v, -0.3, h * 6.283, 0.6 + 0.5 * h, 0.35, 0.6 + 0.4 * h, pick(RS_ROCK, 1 - h)));
    }
  }
  /* the site board: two posts and a blank board beside the point (no text in 3D: the panel carries the words) */
  add('box', 'post0', -2, -RS_CLEAR - 1, 0, 0, 0.12, 1.6, 0.12, RS_BOX.post, { land: true });
  add('box', 'post1', 2, -RS_CLEAR - 1, 0, 0, 0.12, 1.6, 0.12, RS_BOX.post, { land: true });
  add('box', 'board', 0, -RS_CLEAR - 1, 1.0, 0, 4.4, 1.1, 0.08, RS_BOX.board, { land: true });
  return C;
}
/* crew places: on dry land behind the point, facing the water, 4.5 m apart; the first dry free spot of a fixed list */
function rsCrewSpots(n, toWorld, env) {
  const spots = [], tries = [];
  for (const v of [-13, -17, 13, -21]) for (const u of [0, -4.5, 4.5, -9, 9, -13.5, 13.5]) tries.push([u, v]);
  for (const [u, v] of tries) { if (spots.length >= n) break; const [x, z] = toWorld(u, v); if (env.probe(x, z) === 'land') spots.push({ u, v, x, z }); }
  return spots;
}
/* the plan: candidates -> world points -> kept by the radius rule (dry land within RS_LAND, water or off-county within
   RS_WET, never on a street, never inside RS_CLEAR of the landmark mesh) -> nearest-first pool per family to RS_CAP */
function rsPlan(site, env) {
  const W = env.water || rsWaterDir(site, env), px = -W.wz, pz = W.wx, toWorld = (u, v) => [site.x + u * px + v * W.wx, site.z + u * pz + v * W.wz];
  const has = Object.fromEntries(site.layers.map((l) => [l.layer, 1]));
  const C = rsLayout(site, has, env), fam = { pad: [], tuft: [], rock: [], berm: [], box: [] }, drop = { radius: 0, road: 0, land: 0, cap: 0 };
  const yawW = Math.atan2(-W.wz, W.wx);
  for (const c of C) {
    const d = Math.hypot(c.u, c.v), [x, z] = toWorld(c.u, c.v), p = env.probe(x, z);
    if (d < RS_CLEAR) { drop.radius++; continue; }
    if (p === 'road') { drop.road++; continue; }
    if (p === 'land' ? d > RS_LAND : d > RS_WET) { drop.radius++; continue; }
    if ((c.land && p !== 'land') || (c.wet && p === 'land')) { drop.land++; continue; }
    const y = (p === 'land' ? env.ground(x, z) : RS_WATER_Y + 0.02) + c.y0 + c.lift;
    fam[c.fam].push([+x.toFixed(2), +y.toFixed(3), +z.toFixed(2), c.yaw + yawW, c.sx, c.sy, c.sz, c.col, d, c.key]);
  }
  for (const f of Object.keys(fam)) {
    fam[f].sort((a, b) => a[8] - b[8] || (a[9] < b[9] ? -1 : a[9] > b[9] ? 1 : 0));
    const cap = RS_CAP[f] - (f === 'box' ? 5 * site.crewN : 0);
    if (fam[f].length > cap) { drop.cap += fam[f].length - cap; fam[f].length = cap; }
  }
  const crew = rsCrewSpots(site.crewN, toWorld, env).map((s) => ({ ...s, y: env.ground(s.x, s.z), yaw: yawW + Math.PI / 2 }));
  return { water: W, fam, crew, drop, cand: C.length };
}
/* HABITAT-SCENE CORE END */
function rsTuftGeo() {   /* a clump of six thin blades leaning out from the centre: 6 triangles, unlit (MeshBasicMaterial) */
  const P = [];
  for (let k = 0; k < 6; k++) {
    const a = k * Math.PI / 3 + (k % 2) * 0.4, c = Math.cos(a), s = Math.sin(a), r0 = 0.08, r1 = 0.5 - 0.12 * (k % 2), w = 0.11;
    P.push(r0 * c - w * s, 0, -(r0 * s + w * c), r0 * c + w * s, 0, -(r0 * s - w * c), r1 * c, 1 - 0.15 * (k % 2), -r1 * s);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  return g;
}
function rsBermGeo() {   /* trapezoid levee section: base 1 wide (z), crown 0.4, height 1, length 1 along x; no bottom */
  const A = [-0.5, 0, -0.5], B = [0.5, 0, -0.5], Cc = [0.5, 0, 0.5], D = [-0.5, 0, 0.5], E = [-0.5, 1, -0.2], F = [0.5, 1, -0.2], G2 = [0.5, 1, 0.2], H = [-0.5, 1, 0.2];
  const T = [E, H, G2, E, G2, F, A, E, F, A, F, B, D, Cc, G2, D, G2, H, A, D, H, A, H, E, B, F, G2, B, G2, Cc], P = [];
  for (const v of T) P.push(...v);
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.computeVertexNormals();
  return g;
}
const rsBoxGeo = new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0);
const RS_GEO = { pad: new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), tuft: rsTuftGeo(), rock: new THREE.IcosahedronGeometry(0.5, 0), berm: rsBermGeo(), box: rsBoxGeo };
const RS_MESH = {};
for (const f of Object.keys(RS_GEO)) {
  const mat = f === 'tuft' ? new THREE.MeshBasicMaterial({ color: 0xd8d8d8, side: THREE.DoubleSide }) : new THREE.MeshLambertMaterial({ color: 0xffffff });
  if ((f === 'pad' || f === 'berm') && typeof worldTexHook === 'function') worldTexHook(mat, 'ground');   // WORLD-TEX detail by device tier (base tier: unchanged)
  const m = new THREE.InstancedMesh(RS_GEO[f], mat, RS_CAP[f]);
  m.count = 0; m.frustumCulled = false; m.visible = false; m.name = 'habitat-scene:' + f; m.userData.habitatScene = f;
  m.setColorAt(0, new THREE.Color(0xffffff)); scene.add(m); RS_MESH[f] = m;
}
const RSD = JSON.parse(document.getElementById('resto-site-data').textContent);
const RS = { on: true, site: null, key: '', t: 0, plans: {}, wd: {}, builds: 0, ms: 0, crewEls: [] };
const rsM4 = new THREE.Matrix4(), rsQ = new THREE.Quaternion(), rsV = new THREE.Vector3(), rsS = new THREE.Vector3(), rsC = new THREE.Color(), rsUP = new THREE.Vector3(0, 1, 0), rsPV = new THREE.Vector3();
function rsEnv(site) {
  const seed = [...site.id].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
  return { col: RSD.col, hash: (a, b, k) => wildsHash(a, b, seed, k),
    probe: (x, z, wetOnly) => { if (!parishAt(x, z)) return 'out'; if (inWaterAt(x, z)) return 'water'; if (wetOnly) return 'land'; const r = roadNear(x, z, 14); return r && r.edge < 0.5 ? 'road' : 'land'; },
    ground: (x, z) => elevY(x, z) };
}
function rsBuild(site) {
  const t0 = performance.now(), env = rsEnv(site), wk = loaded.size + ',' + waterCut.size;
  if (!RS.wd[site.id] || RS.wd[site.id].k !== wk) RS.wd[site.id] = { k: wk, W: rsWaterDir(site, env) };   // the water search is cached per site until counties or water change
  env.water = RS.wd[site.id].W;
  const P = rsPlan({ ...site, crewN: site.crew.length }, env);
  for (const f of Object.keys(RS_MESH)) {
    const m = RS_MESH[f], L = P.fam[f]; let n = 0;
    for (const b of L) {
      rsM4.compose(rsV.set(b[0], b[1], b[2]), rsQ.setFromAxisAngle(rsUP, b[3]), rsS.set(b[4], b[5], b[6]));
      m.setMatrixAt(n, rsM4); m.setColorAt(n++, rsC.set(b[7]));
    }
    if (f === 'box') for (let i = 0; i < P.crew.length; i++) {   /* SITE-CREW: roster outfit proxy colours, five boxes a figure */
      const s = P.crew[i], c = site.crew[i].col, parts = [[0, 0.36, 0.85, 0.24, c.legs], [0.85, 0.46, 0.6, 0.28, c.torso], [0.95, 0.5, 0.42, 0.3, c.vest], [1.47, 0.24, 0.26, 0.24, c.head], [1.73, 0.3, 0.08, 0.3, c.hat]];
      for (const [y0, sx, sy, sz, hex] of parts) { rsM4.compose(rsV.set(s.x, s.y + y0, s.z), rsQ.setFromAxisAngle(rsUP, s.yaw), rsS.set(sx, sy, sz)); m.setMatrixAt(n, rsM4); m.setColorAt(n++, rsC.set(hex)); }
    }
    m.count = n; m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true;
  }
  RS.plans[site.id] = P; RS.site = site; RS.builds++; RS.ms = +(performance.now() - t0).toFixed(1);
  for (const e of RS.crewEls) e.el.remove();
  RS.crewEls = P.crew.map((s, i) => {
    const el = document.createElement('button'); el.type = 'button'; el.className = 'lbl lm rs-crew'; el.dataset.siteCrew = site.id + ':' + i;
    el.textContent = site.crew[i].name; el.setAttribute('aria-label', site.crew[i].name + ' - ' + site.crew[i].role); el.hidden = true;
    labelsEl.append(el); return { el, x: s.x, y: s.y + 2.3, z: s.z };
  });
}
function rsNearest() {
  let best = null, bd = Infinity;
  for (const s of RSD.sites) if (s.walkable && s.on_page) { const d = Math.hypot(s.x - eye.x, s.z - eye.z); if (d < bd) { bd = d; best = s; } }
  return best ? { s: best, d: bd } : null;
}
/* called from frame() after the street kit: hidden in the overview; built for the walkable site nearest the eye when it
   is within RS_VIEW; rebuilt when streets, water or loaded counties change (throttled to 500 ms) */
function habitatSceneFrame(over) {
  const n = RS.on && !over ? rsNearest() : null, show = !!(n && n.d < RS_VIEW);
  if (show) {
    const now = performance.now(), key = n.s.id + ',' + roadSegs + ',' + loaded.size + ',' + waterCut.size;
    if (key !== RS.key && now - RS.t > 500) { RS.t = now; RS.key = key; rsBuild(n.s); }
  }
  const near = show && n.d < RS_NEAR;
  for (const f of Object.keys(RS_MESH)) RS_MESH[f].visible = show && RS.site === (n && n.s) && (near || (f !== 'tuft' && f !== 'rock'));
  const w = stage.clientWidth, h = stage.clientHeight;
  for (const c of RS.crewEls) {
    rsPV.set(c.x, c.y, c.z); const far = !show || rsPV.distanceTo(camera.position) > 160; rsPV.project(camera);
    const vis = !far && rsPV.z < 1 && Math.abs(rsPV.x) < 1.05 && Math.abs(rsPV.y) < 1.05;
    c.el.hidden = !vis;
    if (vis) c.el.style.transform = `translate(${((rsPV.x + 1) / 2 * w).toFixed(0)}px,${((1 - rsPV.y) / 2 * h).toFixed(0)}px) translate(-50%,-100%)`;
  }
}
window.__habitatScene = {
  stats: () => { const o = { on: RS.on, site: RS.site && RS.site.id, builds: RS.builds, ms: RS.ms, calls: 0, tris: 0, fam: {} };
    for (const [f, m] of Object.entries(RS_MESH)) { o.fam[f] = { count: m.count, visible: m.visible }; if (m.visible && m.count) { o.calls++; o.tris += m.count * RS_TRIS[f]; } }
    return o; },
  plan: (id) => { const P = RS.plans[id]; return P ? { water: P.water, drop: P.drop, cand: P.cand, crew: P.crew, n: Object.fromEntries(Object.entries(P.fam).map(([f, L]) => [f, L.length])),
    pts: Object.fromEntries(Object.entries(P.fam).map(([f, L]) => [f, L.map((b) => [b[0], b[2], b[8]])])) } : null; },
  build: (id) => { const s = RSD.sites.find((q) => q.id === id); if (!s || !s.walkable) throw new Error('habitat scene: no walkable site ' + id); rsBuild(s); RS.key = ''; return window.__habitatScene.plan(id); },
  set: (on) => { RS.on = !!on; RS.key = ''; return RS.on; },
  sites: () => RSD.sites.map((s) => ({ id: s.id, walkable: s.walkable, x: s.x, z: s.z, layers: s.layers ? s.layers.map((l) => l.layer) : [] })),
};
/* HABITAT-SCENE END */
"""

PANEL_CSS = '''
.rs-panel{position:fixed;inset:auto 0 0 0;max-height:78vh;overflow:auto;z-index:61;background:var(--panel);color:var(--ink);border-top:2px solid var(--mark);padding:.75rem 16px}
.rs-panel[hidden]{display:none}
.rs-panel h2{margin:.2rem 0;font-size:1.05rem}
.rs-panel h3{margin:.6rem 0 .3rem;font-size:.95rem}
.rs-panel p,.rs-panel li{font-size:.85rem;overflow-wrap:anywhere}
.rs-panel .rs-src{color:var(--muted);font-size:.75rem}
.rs-panel table{border-collapse:collapse;font-size:.8rem;max-width:100%}
.rs-panel td,.rs-panel th{border:1px solid var(--rule);padding:.2rem .35rem;text-align:start;vertical-align:top}
.rs-panel blockquote{margin:.3rem 0;padding:.3rem .6rem;border-inline-start:3px solid var(--mark)}
.rs-row{display:flex;flex-wrap:wrap;gap:.35rem;margin:.35rem 0}
.rs-row button{font:inherit;font-size:.85rem;min-block-size:36px;border:1px solid var(--rule);background:var(--panel);color:var(--ink);border-radius:.35rem;padding:.25rem .55rem}
.rs-row button[aria-pressed="true"]{border-color:var(--mark);outline:2px solid var(--mark)}
.rs-crew{pointer-events:auto;cursor:pointer}
'''

PANEL_I18N = ('resto.title', 'resto.crew', 'resto.close', 'resto.open', 'resto.lessons', 'tasks.title', 'tasks.launch',
              'course.s.courses', 'course.s.lessons', 'course.sup.source', 'hive.speak', 'hive.v.mute', 'hive.v.muted',
              'hive.v.nosynth', 'hive.v.novoice', 'resto.score', 'resto.gates')


def i18n_for(loc):
    s = need(json.loads((ROOT / 'i18n' / 'locales' / f'{loc}.json').read_text(encoding='utf-8')), 'strings', f'{loc}.json')
    return {k: need(s, k, f'{loc}.json strings') for k in PANEL_I18N}


PANEL_JS = r"""
/* RESTORE-SITE: the site panel - crew (SCRIPTED, voice on a click, Mute), scenarios and staged tasks, the rubric, the
   funding context quoted verbatim, and the related courses and lessons. Opened from the landmark list, a crew label in
   the world, or #site=<id>. Every line shown or spoken is a registry quote printed with its path. */
(function () {
  const RSD = JSON.parse(document.getElementById('resto-site-data').textContent);
  const CAT = JSON.parse(document.getElementById('parishes-i18n').textContent);
  const L = (k) => { const loc = Object.hasOwn(CAT, document.documentElement.lang) ? document.documentElement.lang : 'en';
    const s = CAT[loc].strings[k]; if (typeof s !== 'string') throw new Error('site panel: no ' + k + ' in ' + loc); return s; };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const src = (p) => `<span class="rs-src">${esc(L('course.sup.source'))}: <code>${esc(p)}</code></span>`;
  const panel = document.getElementById('resto-site'), host = panel.querySelector('[data-rs-host]');
  const say = (t) => { const el = panel.querySelector('[data-rs-state]'); if (el) el.textContent = t; };
  let voiceOk = false;
  function voiceInit() {
    if (voiceOk || !window.HiveVoice) return voiceOk;
    HiveVoice.init(JSON.parse(document.getElementById('site-crew-voice').textContent), { onstate: (c) => { say(c === 'muted' ? L('hive.v.muted') : c === 'nosynth' ? L('hive.v.nosynth') : c === 'novoice' ? L('hive.v.novoice') : ''); } });
    voiceOk = true; return true;
  }
  function render(s, focusCrew) {
    const F = RSD.funding, parts = [];
    parts.push(`<h2 id="rs-h">${esc(s.name)}</h2><p>${esc(s.org)} &middot; <a href="${esc(s.source_url)}" rel="noopener">${esc(s.source_url)}</a> ${src(s.src)}</p>`);
    parts.push(`<p>RECORDED habitat: &ldquo;${esc(s.habitat)}&rdquo;</p>`);
    if (!s.walkable) parts.push(`<p data-rs-notwalk>RECORDED: not walkable &mdash; &ldquo;${esc(s.walkable_reason)}&rdquo; ${src(s.src + '.walkable_reason')}</p>`);
    else {
      parts.push(`<p data-rs-scene>${esc(RSD.scene_label)}</p><ul>${s.layers.map((l) => `<li>${esc(RSD.layer_title[l.layer])} &mdash; ${esc(l.field)}: &ldquo;${esc(l.quote)}&rdquo;</li>`).join('')}</ul>`);
      parts.push(`<h3>${esc(L('resto.crew'))}</h3><p>${esc(RSD.crew_label)}</p>`);
      parts.push(`<div class="rs-row"><button type="button" data-rs-mute aria-pressed="${window.HiveVoice && HiveVoice.muted() ? 'true' : 'false'}">${esc(L('hive.v.mute'))}</button></div><p class="rs-src" data-rs-state aria-live="polite"></p>`);
      parts.push(s.crew.map((c, i) => `<section data-rs-crew="${i}"><p><b>${esc(c.name)}</b> &middot; ${esc(c.role)} (${esc(c.trade)}) ${src(c.name_src)}</p>
<div class="rs-row"><button type="button" data-rs-speak="${i}">${esc(L('hive.speak'))}</button></div>
<ol>${c.lines.map((ln) => `<li>&ldquo;${esc(ln[0])}&rdquo; ${src(ln[1])}</li>`).join('')}</ol></section>`).join(''));
    }
    parts.push(`<h3>${esc(L('resto.title'))}</h3>` + s.scenarios.map((x) => `<section><p><b>${esc(x.title)}</b> &middot; ${esc(x.label)} ${src(x.src)}</p>
<ol>${x.steps.map((t) => `<li>${esc(t)}</li>`).join('')}</ol><p>${esc(L('resto.gates'))}: ${x.gates.map(esc).join('; ')}</p>
${s.runner ? `<div class="rs-row"><button type="button" data-resto-run="${esc(s.id)}">${esc(L('resto.open'))}</button></div>` : ''}</section>`).join(''));
    /* a staged task launches this page's own scenario runner: the link carries data-resto-run so the runner opens in place
       (a same-page #resto= link alone changes the hash and nothing else) */
    parts.push(`<h3>${esc(L('tasks.title'))}</h3><ul>${s.tasks.map((t) => `<li>${t.href === null ? esc(t.title) : `<a href="${esc(t.href.replace(/^web\//, ''))}"${s.runner ? ` data-resto-run="${esc(s.id)}"` : ''}>${esc(t.title)}</a>`} &mdash; ${esc(t.brief)} ${src(t.src)}</li>`).join('')}</ul>`);
    parts.push(`<h3>${esc(L('resto.score'))}</h3><table><tbody>${RSD.rubric.map((r) => `<tr><th>${esc(r.axis)}</th><td>${esc(r.measure)}</td><td>${esc(r.pass)}</td></tr>`).join('')}</tbody></table>${src(RSD.rubric_src)}`);
    parts.push(`<h3 lang="en">Funding context</h3><blockquote data-rs-funding><a href="${esc(F.url)}" rel="noopener">${esc(F.headline)}</a></blockquote>
<p>${esc(F.status)} &middot; ${esc(F.source)}</p><p>${esc(F.note)}</p>${src(RSD.funding_src)}`);
    parts.push(`<h3>${esc(L('course.s.courses'))} &middot; ${esc(L('course.s.lessons'))}</h3><ul>${s.courses.map((c) => `<li><a href="${esc(c.href)}">${esc(c.title)}</a> ${src(c.src)}<ul>${c.lessons.map((l) => `<li><a href="${esc(l.href)}">${esc(l.title)}</a></li>`).join('')}</ul></li>`).join('')}</ul>`);
    parts.push(`<p class="rs-src">${esc(RSD.honesty.label)} &middot; ${esc(RSD.honesty.lessons)}. ${esc(RSD.honesty.play)}</p>`);
    host.innerHTML = parts.join('\n');
    if (focusCrew !== undefined) { const c = host.querySelector(`[data-rs-crew="${focusCrew}"]`); if (c) c.scrollIntoView({ block: 'nearest' }); }
  }
  function open(id, from, focusCrew) {
    const s = RSD.sites.find((q) => q.id === id); if (!s) throw new Error('site panel: no site ' + id);
    voiceInit(); render(s, focusCrew);
    panel.querySelector('[data-rs-close]').textContent = L('resto.close');
    panel.dataset.site = id; panel.hidden = false; panel._from = from; panel.querySelector('[data-rs-close]').focus();
  }
  panel.querySelector('[data-rs-close]').addEventListener('click', () => { panel.hidden = true; if (window.HiveVoice) HiveVoice.stop(); if (panel._from && panel._from.isConnected) panel._from.focus(); });
  panel.addEventListener('click', (e) => {
    if (e.target.closest('[data-resto-run]')) { panel.hidden = true; return; }   // the scenario runner opens its own panel
    const sp = e.target.closest('[data-rs-speak]'), mu = e.target.closest('[data-rs-mute]');
    const s = RSD.sites.find((q) => q.id === panel.dataset.site);
    if (mu && window.HiveVoice) { HiveVoice.setMuted(!HiveVoice.muted()); mu.setAttribute('aria-pressed', HiveVoice.muted() ? 'true' : 'false'); return; }
    if (sp && s && window.HiveVoice) { const c = s.crew[Number(sp.dataset.rsSpeak)]; HiveVoice.speak(c.lines.map((ln) => [c.voice, ln[0]])); }
  });
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-site-open]'); if (b) { open(b.dataset.siteOpen, b); return; }
    const c = e.target.closest('[data-site-crew]'); if (c) { const [id, i] = c.dataset.siteCrew.split(':'); open(id, c, Number(i)); }
  });
  addEventListener('load', () => { for (const b of document.querySelectorAll('[data-site-open]')) b.textContent = L('resto.crew') + ' · ' + L('tasks.title'); });
  const h = decodeURIComponent(location.hash.slice(1));
  if (h.startsWith('site=')) addEventListener('load', () => open(h.slice(5), null));
  window.__restoSite = { open: (id) => { open(id, null); return panel.dataset.site; }, sites: () => RSD.sites.map((s) => s.id) };
})();
"""

ANCHORS = {
    'js': 'window.__parishes = {',
    'frame': '  streetKitFrame(over);   // STREET-KIT\n',
    'head': '</head>',
    'body': '</body>',
}


def mount(page, reg, cat):
    """Insert the habitat scene, the site panel, its data and the hive voice block into the built Bay page."""
    import sys
    sys.path.insert(0, str(ROOT / 'web'))
    from hivekit import voice_data, js_json, HIVE_JS  # noqa: E402
    for k, a in ANCHORS.items():
        if page.count(a) != 1:
            raise RestoSceneError(f'restoscene: anchor {k} ({a.strip()[:40]!r}) must occur exactly once, found {page.count(a)}')
    rows, glob = site_rows(reg, page)
    for loc, c in cat.items():
        c['strings'].update(i18n_for(loc))
    data = dict(glob, sites=rows)
    crew_ids = sorted({c['agent'] for r in rows if r['walkable'] for c in r['crew']})
    voices = voice_data(set(crew_ids))
    if sorted(a['id'] for a in voices['agents']) != crew_ids:
        raise RestoSceneError('restoscene: a crew agent has no hive voice')
    for r in rows:
        if not r['on_page']:
            continue
        if not r['runner']:
            continue   # an offshore pin carries no action in the landmark list (its note already quotes the reason)
        a = f'<li data-landmark="{r["lm"]}"><button type="button" class="rk-open" data-resto-run="{r["id"]}">Run training scenario</button> '
        if page.count(a) != 1:
            raise RestoSceneError(f'restoscene: landmark row {r["lm"]} has no scenario runner to sit beside')
        page = page.replace(a, a + f'<button type="button" class="rk-open" data-site-open="{r["id"]}">{r["id"]}</button> ', 1)
    page = page.replace(ANCHORS['js'], SCENE_JS + ANCHORS['js'], 1)
    page = page.replace(ANCHORS['frame'], ANCHORS['frame'] + '  habitatSceneFrame(over);   // HABITAT-SCENE\n', 1)
    page = page.replace(ANCHORS['head'], f'<style>{PANEL_CSS}</style>\n</head>', 1)
    tail = ('<section id="resto-site" class="rs-panel" hidden role="dialog" aria-modal="false" aria-labelledby="rs-h">'
            '<div class="rs-row"><button type="button" data-rs-close></button></div><div data-rs-host></div></section>\n'
            f'<script type="application/json" id="resto-site-data">{js_json(data)}</script>\n'
            + f'<script type="application/json" id="site-crew-voice">{js_json(voices)}</script>'
            + f'<script id="site-crew-kit">{HIVE_JS}</script>' + '\n<script>' + PANEL_JS + '</script>\n')
    page = page.replace(ANCHORS['body'], tail + ANCHORS['body'], 1)
    return page, data
