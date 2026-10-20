"""The whitepaper page, web/smartcitix_whitepaper.html - counted, never typed.

Every figure on the page is READ from a registry at build time and carried
in an element whose data-fig names where it came from:

    data-fig="courses/registry/courses.json#/counts/courses"            the value
    data-fig="security/registry/sbom.cdx.json#/components/[name=three]*" data-op="len"

The pointer is RFC 6901 (`~1` is `/`, `~0` is `~`) with one extension: a
segment `[k=v,k2=v2]` picks the first list item whose fields match, and a
trailing `*` keeps every match (a list). data-op is `len` (the length) or
`distinct:<field>` (how many distinct values). README.md has one pointer,
`#/headline/checks`: the bold "N checks" line. web/test_whitepaper.mjs
resolves every one of them on its own and compares, and holds the visible
text of <main> to carrying no digit outside such an element.

A section exists only when its registry does: the union pathways
(unionpaths/) and the programme cards and nonprofit sectors (programs/) are
drawn when their registries are present and are left out, not promised,
when they are not.

The share card (web/img/smartcitix_whitepaper_card.png, 1200 x 630) is drawn
here with Pillow from the brand palette (brand/identity.mjs TOKENS.dark) and
the same counted figures; its sha256 is pinned beside it in
web/img/smartcitix_whitepaper_card.json and on the page. The contact QR code
is drawn here with segno. datePublished is the newest `built` date among the
registries read - reproducible, so `--check` holds from one day to the next.

    python3 web/build_whitepaper.py           # write page, card and pin
    python3 web/build_whitepaper.py --check   # fail if any of the three is stale
"""
# SHARE (wave 18). Codenames are allowed in this comment only; the built page carries none.
import hashlib
import html
import io
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from seo import apply_seo, ARTICLE_PAGES  # noqa: E402
import sitenav  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS, with_style_memory  # noqa: E402
from design_kit import STYLES as _STYLES  # noqa: E402

PAGE = 'web/smartcitix_whitepaper.html'
if PAGE not in sitenav.PAGES:
    raise SystemExit(f'build_whitepaper: {PAGE} is not declared in web/sitenav.py PAGES')
assert PAGE in ARTICLE_PAGES, f'build_whitepaper: {PAGE} is not an ARTICLE_PAGES entry in web/seo.py'
CARD = 'web/img/smartcitix_whitepaper_card.png'
PIN = 'web/img/smartcitix_whitepaper_card.json'
E = lambda s: html.escape(str(s), quote=True)  # noqa: E731


class Missing(SystemExit):
    pass


# ------------------------------------------------------------------ registries
_cache = {}


def load(rel):
    if rel not in _cache:
        p = ROOT / rel
        if not p.is_file():
            raise Missing(f'build_whitepaper: registry {rel} is missing')
        _cache[rel] = p.read_text(encoding='utf-8') if rel.endswith('.md') else json.loads(p.read_text(encoding='utf-8'))
    return _cache[rel]


def has(rel):
    return (ROOT / rel).is_file()


SEG = re.compile(r'\[([^\]]+)\](\*?)')


def _unesc(s):
    return s.replace('~1', '/').replace('~0', '~')


def resolve(spec, op=None):
    rel, _, ptr = spec.partition('#')
    doc = load(rel)
    if rel == 'README.md':
        assert ptr == '/headline/checks', f'build_whitepaper: README pointer {ptr}'
        m = re.search(r'^\*\*([0-9,]+) checks, all passing', doc, re.M)
        if not m:
            raise Missing('build_whitepaper: README.md headline "**N checks, all passing" not found')
        v = int(m.group(1).replace(',', ''))
    else:
        v = doc
        assert ptr.startswith('/'), f'build_whitepaper: pointer {spec} must start with /'
        for seg in ptr[1:].split('/'):
            m = SEG.fullmatch(seg)
            if m:
                conds = [c.split('=', 1) for c in m.group(1).split(',')]
                assert isinstance(v, list), f'build_whitepaper: {spec}: filter on a non-list'
                hits = [x for x in v if all(isinstance(x, dict) and str(x.get(_unesc(k))) == _unesc(val) for k, val in conds)]
                if m.group(2):
                    v = hits
                else:
                    if not hits:
                        raise Missing(f'build_whitepaper: {spec}: no item matches [{m.group(1)}]')
                    v = hits[0]
            elif isinstance(v, list):
                v = v[int(seg)]
            else:
                k = _unesc(seg)
                if not isinstance(v, dict) or k not in v:
                    raise Missing(f'build_whitepaper: {spec}: no field {k!r}')
                v = v[k]
    if op == 'len':
        v = len(v)
    elif op and op.startswith('distinct:'):
        v = len({json.dumps(x[op[9:]], sort_keys=True) for x in v})
    elif op:
        raise SystemExit(f'build_whitepaper: unknown op {op}')
    if v is None or (isinstance(v, str) and not v.strip()):
        raise Missing(f'build_whitepaper: {spec} is empty')
    return v


def fmt(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return f'{v:,}'
    return str(v)


USED = []          # every pointer the page carries, in order


def N(spec, op=None, tag='span', cls='n'):
    """A counted figure (or a registry string), wrapped with where it came from."""
    v = resolve(spec, op)
    USED.append((spec, op))
    o = f' data-op="{E(op)}"' if op else ''
    c = f' class="{cls}"' if cls else ''
    return f'<{tag}{c} data-fig="{E(spec)}"{o}>{E(fmt(v))}</{tag}>'


def V(spec, op=None):
    return resolve(spec, op)


def Q(spec):
    """A registry sentence quoted verbatim, with its source beside it."""
    return (f'<blockquote class="q">{N(spec, tag="span", cls="")}'
            f'<cite>{E(spec.split("#")[0])}</cite></blockquote>')


# --------------------------------------------------------------- the registries
R = dict(
    courses='courses/registry/courses.json', unions='unions/registry/unions.json',
    paths='unionpaths/registry/union_paths.json', programs='programs/registry/programs.json',
    schools='schools/registry/schools.json', classroom='classroom/registry/classroom.json',
    cogx='cognitionx/registry/cognitionx.json', hive='hive/registry/hive.json',
    robotics='robotics/registry/robotics.json', evals='evals/registry/evals.json',
    rest='restoration/registry/restoration.json', scen='restoration/registry/scenarios.json',
    roadmap='roadmap/registry/roadmap.json', rnd='rnd/registry/rnd.json',
    sbom='security/registry/sbom.cdx.json', packs='holodeck/registry/packs.json',
    wilds='wilds/registry/wilds.json', parishes='parishes/registry/parishes.json',
    bay='bayarea/registry/bayarea.json', smiles='smiles/registry/smiles.json',
    readme='README.md',
    arena='robotics/arena/registry/arena.json', models='robotics/arena/registry/models.json',
    claw='robotics/claw/registry/claw.json',
)
OPTIONAL = {'paths', 'programs', 'arena', 'models', 'claw'}
for k, rel in R.items():
    if k not in OPTIONAL and not has(rel):
        raise Missing(f'build_whitepaper: registry {rel} is missing')
HAVE_PATHS, HAVE_PROGRAMS = has(R['paths']), has(R['programs'])
HAVE_ARENA, HAVE_CLAW = has(R['arena']) and has(R['models']), has(R['claw'])


def r(key, ptr):
    return f'{R[key]}#{ptr}'


# the brand: name, publisher, contact and palette from brand/identity.mjs
_ident = (ROOT / 'brand/identity.mjs').read_text(encoding='utf-8')


def _brand(field):
    m = re.search(rf"^\s*{field}: '([^']+)'", _ident, re.M)
    if not m:
        raise Missing(f'build_whitepaper: brand/identity.mjs has no {field}')
    return m.group(1)


BRAND_FULL, PUBLISHER, CONTACT, ATTRIB = _brand('full'), _brand('publisher'), _brand('contact'), _brand('attribution')
_dark = re.search(r'export const TOKENS = Object\.freeze\(\{\s*dark: \{(.*?)\}', _ident, re.S)
if not _dark:
    raise Missing('build_whitepaper: brand/identity.mjs has no TOKENS dark palette')
PAL = dict(re.findall(r"(\w+): '(#[0-9A-Fa-f]{6})'", _dark.group(1)))
for k in ('plate', 'panel', 'ink', 'muted', 'rule', 'mark', 'steel'):
    if k not in PAL:
        raise Missing(f'build_whitepaper: brand dark palette lacks {k}')

# datePublished: the newest `built` among the registries read that carry one
_built = sorted(load(rel)['built'] for k, rel in R.items()
                if rel.endswith('.json') and has(rel) and isinstance(load(rel), dict) and isinstance(load(rel).get('built'), str))
if not _built:
    raise Missing('build_whitepaper: no registry carries a built date')
DATE = _built[-1]
assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', DATE), f'build_whitepaper: built date {DATE!r}'

# ------------------------------------------------------------------- headline
HEADLINE = resolve(r('readme', '/headline/checks'))
_readme = load('README.md')
_m = re.search(r'^\*powered by AGI Corp\*\s*\n\s*\n(.+?)\n', _readme, re.M)
if not _m:
    raise Missing('build_whitepaper: README.md has no headline sentence under the attribution')
TAGLINE = _m.group(1).strip()
assert not re.search(r'\d', TAGLINE), 'build_whitepaper: README headline sentence carries a digit'

# ------------------------------------------------------------------- sections
SECTIONS = []      # (id, heading, html)


def section(sid, heading, body):
    SECTIONS.append((sid, heading, body))


def table(head, rows, cls=''):
    th = ''.join(f'<th scope="col">{h}</th>' for h in head)
    tr = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def chips(*items):
    return '<p class="chips">' + ''.join(f'<span class="chip chip-{k}">{t}</span>' for k, t in items) + '</p>'


def tiles(items):
    return '<dl class="tiles">' + ''.join(f'<div><dt>{lab}</dt><dd>{val}</dd></div>' for lab, val in items) + '</dl>'


# 1. executive summary
KEY = [  # (label, spec, op) - also drawn on the share card
    ('Courses', r('courses', '/counts/courses'), None),
    ('Union halls', r('unions', '/count'), None),
    ('Omega Hive agents', r('hive', '/counts/agents'), None),
    ('Bay restoration sites', r('rest', '/sites'), 'len'),
]
section('summary', 'Executive summary',
        f'<p class="lede">{E(TAGLINE)}</p>'
        f'<p>{E(BRAND_FULL)} is a training bundle published by {E(PUBLISHER)}: walkable worlds, trade courses, '
        f'K-12 programme pathways, a scripted agent roster and robot training sandboxes, each a pack with its own '
        f'registry. Every figure on this page is counted from those registries when the page is built, and the '
        f'bundle holds itself to {N(r("readme", "/headline/checks"))} automated checks.</p>'
        + tiles([(lab, N(spec, op)) for lab, spec, op in KEY]
                + [('Lessons', N(r('courses', '/counts/lessons'))),
                   ('Walkable campuses', N(r('roadmap', '/built_campuses'), 'len')),
                   ('Trained models', N(r('robotics', '/counts/trained_models'))),
                   ('AI models behind agents', N(r('hive', '/counts/models')))])
        + chips(('auth', 'Courses AUTHORED by rule'), ('scr', 'Agents SCRIPTED'), ('open', 'Partners PROPOSED'))
        + '<p>Lessons are unverified general practice, nothing here certifies anybody, and every partner, district '
          'and programme named is PROPOSED: no agreement exists.</p>')

# 2. worlds
wild_rows = [[N(r('wilds', f'/worlds/{i}/name'))] for i in range(V(r('wilds', '/worlds'), 'len'))]
par = load(R['parishes'])['parishes']
bayc = load(R['bay'])['counties']
section('worlds', 'Worlds',
        '<p>The Academy is a set of walkable worlds a learner moves through in the browser.</p>'
        + tiles([('Walkable campuses', N(r('roadmap', '/built_campuses'), 'len')),
                 ('Louisiana parishes', N(r('parishes', '/parishes'), 'len')),
                 ('Bay Area counties', N(r('bay', '/counties'), 'len')),
                 ('Wilderness worlds', N(r('wilds', '/worlds'), 'len')),
                 ('Classroom places', N(r('classroom', '/counts/places'))),
                 ('Holodeck packs', N(r('packs', '/counts/packs')))])
        + f'<p>The wilderness worlds are {", ".join(c[0] for c in wild_rows)}, covering '
          f'{N(r("wilds", "/counts/area_km2"))} square kilometres with {N(r("wilds", "/counts/sites"))} sites. '
          f'Of the holodeck packs, {N(r("packs", "/counts/shipping"))} ship and {N(r("packs", "/counts/proposed"))} '
          f'is PROPOSED.</p>'
        + f'<p>The {N(r("smiles", "/name"))} is an AUTHORED game district with {N(r("smiles", "/stations"), "len")} '
          f'stations; it is named only as the programme its clinic stations belong to.</p>'
        + Q(r('smiles', '/place_note'))
        + '<p>Water in the parish and Bay worlds is AUTHORED (procedural), and district layouts are AUTHORED; '
          'campus coordinates are RECORDED for some campuses and AUTHORED for others, as each registry labels them.</p>')

# 3. training and courses, with the union pathways
tiers = load(R['courses'])['counts']['lessons_by_tier']
tier_rows = [[E(t), N(r('courses', f'/counts/lessons_by_tier/{t}'))] for t in tiers]
body = (chips(('auth', 'AUTHORED by rule'), ('open', 'unverified general practice'))
        + f'<p>{N(r("courses", "/counts/courses"))} courses group {N(r("courses", "/counts/lessons"))} lessons and '
          f'{N(r("courses", "/counts/steps"))} steps: {N(r("courses", "/counts/trade_courses"))} trade courses, one per '
          f'union hall, and {N(r("courses", "/counts/strand_courses"))} strand courses. '
          f'{N(r("courses", "/counts/courses_with_seats"))} courses include a simulator seat.</p>'
        + table(['Tier', 'Lessons'], tier_rows)
        + Q(r('courses', '/honesty/content'))
        + Q(r('courses', '/honesty/not_certification')))
if HAVE_PATHS:
    bd = load(R['paths'])['by_district']
    drows = [[N(r('paths', f'/by_district/[district={d["district"]}]/name')),
              N(r('paths', f'/by_district/[district={d["district"]}]/count')),
              N(r('paths', f'/by_district/[district={d["district"]}]/lessons')),
              N(r('paths', f'/by_district/[district={d["district"]}]/steps')),
              N(r('paths', f'/by_district/[district={d["district"]}]/halls_with_seats'))] for d in bd]
    body += ('<h3>Union-hall pathways</h3>'
             + chips(('der', 'DERIVED'), ('open', 'unions named are not partners'))
             + f'<p>Each of the {N(r("paths", "/counts/halls"))} union halls has one ordered pathway through the '
               f'courses, lessons, seats, tool crib and advisor already standing in that hall: '
               f'{N(r("paths", "/counts/path_steps"))} pathway steps across {N(r("paths", "/counts/districts"))} '
               f'districts and {N(r("paths", "/counts/cohorts"))} cohorts. {N(r("paths", "/counts/halls_with_seats"))} '
               f'halls have a simulator seat and {N(r("paths", "/counts/halls_with_crews"))} a crew drill. '
               f'No apprenticeship hours, wages or credentials are stated; recorded affiliations: '
               f'{N(r("paths", "/counts/affiliations"))}.</p>'
             + table(['District', 'Halls', 'Lessons', 'Steps', 'Halls with seats'], drows)
             + Q(r('paths', '/honesty/not_partner'))
             + Q(r('paths', '/honesty/programmes')))
else:
    body += Q(r('unions', '/honesty/' + next(iter(load(R['unions'])['honesty']))))
section('training', 'Training and courses', body)

# 4. K-12 and programmes
sb = load(R['schools'])['bands']
band_rows = []
for i, b in enumerate(sb):
    row = [N(r('schools', f'/bands/{i}/band')), N(r('courses', f'/counts/lessons_by_band/{b["band"]}'))]
    if HAVE_PROGRAMS:
        row += [N(r('programs', f'/bands/[band={b["band"]}]/level')), N(r('programs', f'/counts/cards_by_band/{b["band"]}')),
                N(r('programs', f'/counts/blocks_by_band/{b["band"]}'))]
    band_rows.append(row)
dist_rows = [[N(r('schools', f'/districts/{i}/' + ('name' if 'name' in d else 'district'))), '<span class="chip chip-open">PROPOSED</span>']
             for i, d in enumerate(load(R['schools'])['districts'])]
body = (chips(('open', 'districts PROPOSED'), ('auth', 'nothing accredited'))
        + f'<p>The schools pack sets {N(r("schools", "/bands"), "len")} grade bands over {N(r("schools", "/units"), "len")} '
          f'units. The classroom has {N(r("classroom", "/counts/modules"))} teacher-facing modules and '
          f'{N(r("classroom", "/counts/moments"))} classroom moments, and Cognition.X contributes '
          f'{N(r("cogx", "/counts/blocks") if "blocks" in load(R["cogx"])["counts"] else r("cogx", "/blocks"), None if "blocks" in load(R["cogx"])["counts"] else "len")} '
          f'curriculum blocks, quoted verbatim.</p>')
if HAVE_PROGRAMS:
    body += (f'<p>{N(r("programs", "/counts/cards"))} teacher-facing programme cards pair a module with a hall, its lessons '
             f'and a play-safe greeter; {N(r("programs", "/counts/allow_list_agents"))} Omega Hive agents are on the '
             f'classroom allow-list. AI models used: {N(r("programs", "/counts/models"))}.</p>'
             + table(['Band', 'Lessons', 'Level', 'Programme cards', 'Cognition.X blocks'], band_rows))
else:
    body += table(['Band', 'Lessons'], band_rows)
body += '<h3>School districts</h3>' + table(['District', 'Status'], dist_rows)
body += Q(r('programs', '/honesty/proposed') if HAVE_PROGRAMS else r('courses', '/honesty/bands'))
if HAVE_PROGRAMS:
    body += Q(r('programs', '/honesty/un'))
section('k12', 'K-12 and programmes', body)

# 5. nonprofit sectors (only from the programmes registry)
if HAVE_PROGRAMS:
    srows = []
    for s in load(R['programs'])['sectors']:
        sid = s['id']
        cell = lambda f: N(r('programs', f'/sectors/[id={sid}]/{f}'), 'len') if f in s else '<span class="muted">none</span>'  # noqa: E731
        srows.append([N(r('programs', f'/sectors/[id={sid}]/id')), N(r('programs', f'/sectors/[id={sid}]/status')),
                      cell('scenarios'), cell('halls'), cell('agents'), cell('worlds')])
    section('sectors', 'Nonprofit sectors',
            chips(('open', 'PROPOSED'), ('der', 'mapped to existing work'))
            + f'<p>{N(r("programs", "/sectors"), "len")} nonprofit sectors are each mapped onto what already exists '
              f'in the bundle. Every organisation named is PROPOSED, and Unspoken Smiles is named only as the '
              f'existing pages describe it.</p>'
            + table(['Sector', 'Status', 'Scenarios', 'Halls', 'Agents', 'Worlds'], srows)
            + Q(r('programs', '/sectors/[id=community-health]/quotes/1/text')))

# 6. Bay restoration
site_rows = []
for s in load(R['rest'])['sites']:
    sid = s['id']
    p = lambda f: r('rest', f'/sites/[id={sid}]/{f}')  # noqa: E731
    site_rows.append([N(p('name')), N(p('org')), N(p('habitat')),
                      N(r('scen', f'/counts/by_site/{sid}')),
                      '<span class="chip chip-ok">walkable</span>' if s['walkable'] else '<span class="chip chip-open">marker only</span>'])
section('bay', 'Bay restoration',
        chips(('rec', 'sites from public record'), ('auth', 'scenarios AUTHORED'), ('open', 'not affiliated'))
        + f'<p>{N(r("rest", "/sites"), "len")} real San Francisco Bay restoration and cleanup sites, each run by its own '
          f'organisation, with {N(r("scen", "/counts/scenarios"))} AUTHORED training scenarios across '
          f'{N(r("rest", "/tracks"), "len")} tracks. Active federal cleanup sites are shown as markers, never as '
          f'walkable ground.</p>'
        + table(['Site', 'Organisation', 'Habitat', 'Scenarios', 'In the Bay world'], site_rows)
        + '<h3>Funding context</h3>'
        + f'<p>Status: {N(r("scen", "/funding_context/status"))}. Only a headline is known; no scenario is one of '
          f'the funded projects.</p>'
        + Q(r('scen', '/funding_context/headline'))
        + Q(r('rest', '/honesty/not_affiliated')))

# 7. robotics and model comparison
pe = load(R['robotics'])['reference_benchmark']['per_env']
brows = []
for env, v in pe.items():
    for lv in v['levels']:
        b = f'/reference_benchmark/per_env/{env}/levels/{lv}'
        brows.append([N(r('robotics', f'/reference_benchmark/per_env/{env}/levels/{lv}/name')) + f' <span class="muted">{E(env.split(".", 1)[-1].replace("-", " "))}</span>',
                      N(r('robotics', b + '/success')), N(r('robotics', b + '/runs'))])
TRAINED = V(r('robotics', '/counts/trained_models'))
body = (chips(('scr', 'reference policy SCRIPTED'), ('sch', 'arenas SCHEMATIC'),
              ('open', 'not a language model') if TRAINED else ('open', 'nothing trained'))
        + f'<p>{N(r("robotics", "/counts/embodiments"))} embodiments and {N(r("robotics", "/counts/envs"))} '
          f'environments are specified, with a runnable sandbox. The reference benchmark below is the SCRIPTED '
          f'reference policy, measured over every declared seed and level; on level one it succeeds in '
          f'{N(r("robotics", "/reference_benchmark/totals/success"))} of {N(r("robotics", "/reference_benchmark/totals/runs"))} runs.</p>'
        + table(['Level', 'Successes', 'Runs'], brows)
        + f'<h3>Model comparison</h3><p>Trained models in the bundle: {N(r("robotics", "/counts/trained_models"))}.')
if TRAINED and HAVE_ARENA:
    # SHARE (wave 18, landing 2): the arena's measured comparison, its BC card verbatim, and Omega Claw
    lb = load(R['arena'])['leaderboard']
    if lb['table'] != 'held_out':
        raise Missing('build_whitepaper: arena leaderboard is not the held_out table')
    lrows = []
    for row in lb['rows']:
        q = lambda f: r('arena', f'/leaderboard/rows/[policy={row["policy"]}]/{f}')  # noqa: E731
        lrows.append([N(q('rank')), N(q('name')), N(q('kind')), N(q('n')), N(q('success_rate/mean')),
                      '[' + N(q('success_rate/ci95/0')) + ', ' + N(q('success_rate/ci95/1')) + ']',
                      N(q('win_vs_ref/rate')), '[' + N(q('win_vs_ref/ci95/0')) + ', ' + N(q('win_vs_ref/ci95/1')) + ']',
                      N(q('win_vs_ref/wins')) + ' / ' + N(q('win_vs_ref/ties')) + ' / ' + N(q('win_vs_ref/losses'))])
    model = load(R['models'])['models']
    if len(model) != V(r('arena', '/counts/trained_models')):
        raise Missing('build_whitepaper: models.json and arena.json disagree on trained models')
    cards = ''
    for m_ in model:
        mid = m_['id']
        card = ''.join(f'<div><dt>{E(k.replace("_", " "))}</dt><dd>{N(r("models", f"/models/[id={mid}]/card/{k}"), tag="span", cls="")}</dd></div>'
                       for k in m_['card'])
        cards += f'<dl class="bccard" data-card="{E(mid)}">{card}</dl>'
    whats = '; '.join(N(r("models", f"/models/[id={m_['id']}]/card/what"), cls="") for m_ in model)
    # items binned in litter sort (the measure the second policy was built for), copied from the arena's learned_vs_reference
    lv = load(R['arena'])['learned_vs_reference']
    brow = []
    for row in lv['rows']:
        q = lambda f: r('arena', f'/learned_vs_reference/rows/[policy={row["policy"]}]/{f}')  # noqa: E731
        brow.append([N(q('policy')), N(q('kind')), N(q('items_binned')) + ' / ' + N(q('items_total')),
                     N(q('binned_per_episode/mean')) + ' [' + N(q('binned_per_episode/ci95/0')) + ', ' + N(q('binned_per_episode/ci95/1')) + ']',
                     N(q('episodes_with_any')) + ' / ' + N(q('episodes'))])
    body += (f' Trained here: {whats}. They are compared below with the SCRIPTED '
             f'reference, a SCRIPTED greedy policy and a random baseline on the held-out seeds, measured at build time; '
             f'intervals are bootstrap confidence intervals at level {N(r("arena", "/tables/held_out/bootstrap/level"))} '
             f'over {N(r("arena", "/tables/held_out/bootstrap/resamples"))} resamples, and the win rate is paired against '
             f'the reference on the same task, level and seed.</p>'
             + table(['Rank', 'Policy', 'Kind', 'Runs', 'Success rate', 'Interval', 'Paired win rate vs reference',
                      'Interval', 'Wins / ties / losses'], lrows)
             + f'<p class="muted">Held-out seeds: {N(r("arena", "/leaderboard/seeds"), "len")}; tasks: '
               f'{N(r("arena", "/tables/held_out/tasks"), "len")}; environments excluded, each with its reason: '
               f'{N(r("arena", "/tables/held_out/excluded"), "len")}.</p>'
             + '<h3>Litter sort: items binned on the held-out seeds</h3>'
             + '<p>Success in litter sort means every item binned, which the SCRIPTED reference itself seldom manages at the first three '
               'levels, so items binned is the measure for the learned policies. Numbers are copied from the arena registry, whatever they are.</p>'
             + table(['Policy', 'Kind', 'Items binned', 'Per episode, mean [interval]', 'Episodes binning any'], brow)
             + '<h3>The trained policies\' cards, verbatim</h3>'
             + cards
             + Q(r('arena', '/honesty/not_llm')))
else:
    body += (' There is no trained model to compare, so no model comparison is claimed.</p>')
if HAVE_CLAW:
    cp = load(R['claw'])
    trows = [[N(r('claw', f'/tournament/policies/[id={pid["id"]}]/id')), N(r('claw', f'/tournament/per_policy/{pid["id"]}/provenance')),
              N(r('claw', f'/tournament/per_policy/{pid["id"]}/runs')), N(r('claw', f'/tournament/per_policy/{pid["id"]}/success')),
              N(r('claw', f'/tournament/per_policy/{pid["id"]}/collisions')), N(r('claw', f'/tournament/per_policy/{pid["id"]}/mean_return'))]
             for pid in cp['tournament']['policies']]
    prows = [[E(k), N(r('claw', f'/tournament/paired/{k}/pairs')), N(r('claw', f'/tournament/paired/{k}/a_only')),
              N(r('claw', f'/tournament/paired/{k}/b_only')), N(r('claw', f'/tournament/paired/{k}/p')),
              N(r('claw', f'/tournament/paired/{k}/mean_return_diff'))] for k in cp['tournament']['paired']]
    srows = [[E(sp), N(r('claw', f'/dataset/splits/{sp}/train')), N(r('claw', f'/dataset/splits/{sp}/val')),
              N(r('claw', f'/dataset/splits/{sp}/test')), N(r('claw', f'/splits/{sp}/rule'))] for sp in cp['dataset']['splits']]
    arows = [[N(r('claw', f'/agents/[id={a["id"]}]/name')), N(r('claw', f'/agents/[id={a["id"]}]/job')),
              '<span class="chip chip-scr">SCRIPTED</span>'] for a in cp['agents']]
    body += ('<h3>Omega Claw: the tournament and the datasets</h3>'
             + chips(('scr', 'agents SCRIPTED'), ('open', 'no AI model'), ('der', 'datasets for training elsewhere'))
             + f'<p>A tournament of {N(r("claw", "/counts/tournament_runs"))} runs puts {N(r("claw", "/counts/policies"))} '
               f'policies through the same tasks, levels and seeds. Disagreements between the referee and the success rule: '
               f'{N(r("claw", "/tournament/referee_disagreements"))}.</p>'
             + table(['Policy', 'Provenance', 'Runs', 'Successes', 'Collisions', 'Mean return'], trows)
             + table(['Pair', 'Pairs', 'First only', 'Second only', 'Sign-test p', 'Mean return difference'], prows)
             + Q(r('claw', '/tournament/said/referee'))
             + f'<p>The dataset holds {N(r("claw", "/dataset/samples"))} samples from {N(r("claw", "/dataset/episodes"))} '
               f'seeded episodes of the SCRIPTED reference policy; learner episodes in it: {N(r("claw", "/dataset/learner"))}; '
               f'samples that met their success rule: {N(r("claw", "/dataset/success"))}.</p>'
             + table(['Split', 'Train', 'Validation', 'Test', 'Rule'], srows)
             + f'<p>{N(r("claw", "/counts/agents"))} Omega Claw agents run the tournament and the datasets. AI models behind '
               f'them: {N(r("claw", "/counts/models"))}.</p>'
             + table(['Agent', 'Job', 'Provenance'], arows)
             + Q(r('claw', '/honesty/no_model')))
body += ('<p class="deny">No language model is trained here, and no policy here uses one. The datasets are for training a '
         'robot-learning model elsewhere.</p>'
         + (Q(r('claw', '/honesty/trained')) if HAVE_CLAW else '')
         + f'<h3>Learning strategies in a simulated learner</h3><p>A separate comparison is recorded '
           f'between {N(r("evals", "/counts/strategies"))} sequencing strategies in a simulated learner: of '
           f'{N(r("evals", "/counts/comparisons"))} metric comparisons across {N(r("evals", "/counts/seeds"))} seeds, '
           f'{N(r("evals", "/counts/comparisons_separating_on_every_seed"))} separate on every seed and '
           f'{N(r("evals", "/counts/comparisons_overlapping"))} overlap. Assumptions validated against real '
           f'learners: {N(r("evals", "/counts/assumptions_validated_against_learners"))}.</p>'
         + Q(r('robotics', '/honesty/trained')))
section('robotics', 'Robotics and model comparison', body)

# 8. Omega Hive
section('hive', 'Omega Hive',
        chips(('scr', 'SCRIPTED'), ('open', 'no AI model'), ('auth', 'personalities AUTHORED'))
        + f'<p>{N(r("hive", "/counts/agents"))} agents - {N(r("hive", "/counts/advisors"))} hall advisors, '
          f'{N(r("hive", "/counts/crews"))} crews with {N(r("hive", "/counts/crew_roles"))} roles and '
          f'{N(r("hive", "/counts/npcs"))} world guides - each with an avatar, an AUTHORED personality and a voice. '
          f'They say only the {N(r("hive", "/counts/lines"))} lines quoted from their registries. The voice is the '
          f"device's own speech synthesis and speaks only on a click. AI models: {N(r('hive', '/counts/models'))}; "
          f'agents on the K-12 allow-list: {N(r("hive", "/counts/k12_agents"))}.</p>'
        + Q(r('hive', '/honesty/no_model'))
        + Q(r('hive', '/honesty/voice')))

# 9. tool stack (the SBOM)
comps = load(R['sbom'])['components']
groups = {}
for c in comps:
    if c['type'] not in ('library', 'data'):
        continue
    lic = (c.get('licenses') or [{}])[0].get('license', {})
    field = 'id' if lic.get('id') else 'name' if lic.get('name') else None
    if not field:
        raise Missing(f'build_whitepaper: SBOM component {c["name"]} has no licence id or name')
    groups.setdefault((c['type'], c['name'], c['version']), field)
stack_rows = []
for (typ, name, ver), field in groups.items():
    for ch in ',]=':
        assert ch not in name + ver, f'build_whitepaper: SBOM name {name} {ver} carries {ch!r}'
    sel = f'/components/[type={typ},name={name.replace("~", "~0").replace("/", "~1")},version={ver}]'
    stack_rows.append([N(r('sbom', sel + '/name')), N(r('sbom', sel + '/version')),
                       N(r('sbom', sel + '/licenses/0/license/' + field)), N(r('sbom', sel + '*'), 'len'), E(typ)])
section('stack', 'Tool stack',
        f'<p>Every vendored third-party file - libraries, fonts, icons and map and terrain data - is listed in the bundle\'s CycloneDX software bill of materials: '
        f'{N(r("sbom", "/components"), "len")} components. Grouped by name and version:</p>'
        + table(['Component', 'Version', 'Licence', 'Files', 'Kind'], stack_rows)
        + Q(r('sbom', '/metadata/component/description')))

# 10. roadmap
section('roadmap', 'Roadmap',
        '<p>The roadmap carries no dates: it is an ordered record of what is built and what is still open.</p>'
        + tiles([('Campus target', N(r('roadmap', '/target'))), ('Campuses built', N(r('roadmap', '/built_campuses'), 'len')),
                 ('Candidates', N(r('roadmap', '/candidates'), 'len')), ('Open gaps', N(r('rnd', '/counts/gaps_open'))),
                 ('Open questions', N(r('rnd', '/counts/open_questions'))), ('Declared, not built', N(r('rnd', '/counts/declared_unbuilt')))])
        + Q(r('roadmap', '/honesty/no_dates')))

# 11. honest status
section('status', 'Honest status',
        '<ul class="status">'
        f'<li>Trained models: {N(r("robotics", "/counts/trained_models"))}. Robots are AUTHORED and the reference policies '
        + ('SCRIPTED; the trained policy is a small behaviour-cloning network, not a language model, trained on SCRIPTED '
           'episodes and no learner data.</li>' if TRAINED else 'SCRIPTED.</li>')
        + '<li>No language model is trained here.</li>'
        f'<li>AI models behind Omega Hive agents: {N(r("hive", "/counts/models"))}.</li>'
        '<li>Partners, school districts and programmes are PROPOSED; no agreement exists. Unions named are halls in '
        'the Academy\'s own taxonomy, not partners. The UN path is PROPOSED and not affiliated.</li>'
        '<li>Nothing is accredited, and lessons are unverified general practice.</li>'
        f'<li>Bay restoration funding context: {N(r("scen", "/funding_context/status"))}.</li>'
        f'<li>Holodeck packs proposed, not shipping: {N(r("packs", "/counts/proposed"))}.</li>'
        '<li>Games, coins and badges are play.</li>'
        '</ul>'
        + Q(r('smiles', '/stations_check')))

# 12. contact, with a QR code drawn by segno
import segno  # noqa: E402
_qr = segno.make(f'mailto:{CONTACT}', error='m')
_buf = io.BytesIO()
_qr.save(_buf, kind='svg', xmldecl=False, svgns=True, nl=False, scale=6, border=2,
         dark='#12181B', light='#FFFFFF', svgclass='qr', lineclass=None, omitsize=False)
QR_SVG = _buf.getvalue().decode('utf-8')
QR_SVG = QR_SVG.replace('<svg ', '<svg role="img" aria-label="QR code: email the Foundation" ', 1)
section('contact', 'Contact',
        f'<div class="cta"><div><p>Questions, a proposed partnership or a correction: write to {E(PUBLISHER)}.</p>'
        f'<p><a class="btn" href="mailto:{E(CONTACT)}">{E(CONTACT)}</a></p>'
        '<p class="muted">The code opens the same address in a mail app.</p></div>'
        f'<figure class="qrfig" data-qr="mailto">{QR_SVG}</figure></div>')


# ----------------------------------------------------------------- share card
def draw_card():
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 630
    rgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))  # noqa: E731
    F = lambda f, s: ImageFont.truetype(str(ROOT / 'web/vendor/fonts' / f), s)  # noqa: E731
    im = Image.new('RGB', (W, H), rgb(PAL['plate']))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill=rgb(PAL['mark']))
    for x in range(0, W, 40):
        d.line([(x, 10), (x, H)], fill=rgb(PAL['sunk'] if 'sunk' in PAL else PAL['panel']), width=1)
    # the mark: a triangle and a bar, as in the favicon
    d.line([(64, 120), (100, 62), (136, 120), (64, 120)], fill=rgb(PAL['mark']), width=7, joint='curve')
    d.line([(80, 120), (120, 120)], fill=rgb(PAL['steel']), width=7)
    d.text((164, 58), BRAND_FULL, font=F('archivo-700-normal-latin.woff2', 44), fill=rgb(PAL['ink']))
    d.text((166, 112), ATTRIB + '  ·  ' + PUBLISHER, font=F('ibm-plex-sans-500-normal-latin.woff2', 22), fill=rgb(PAL['muted']))
    d.text((64, 186), 'Whitepaper', font=F('barlow-condensed-700-normal-latin.woff2', 92), fill=rgb(PAL['mark']))
    d.text((64, 300), TAGLINE, font=F('ibm-plex-sans-500-normal-latin.woff2', 30), fill=rgb(PAL['ink']))
    figs = []
    tw = (W - 128 - 3 * 24) // 4
    for i, (lab, spec, op) in enumerate(KEY):
        v = resolve(spec, op)
        figs.append({'label': lab, 'value': v, 'fig': spec, 'op': op})
        x = 64 + i * (tw + 24)
        d.rectangle([x, 380, x + tw, 540], fill=rgb(PAL['panel']), outline=rgb(PAL['rule']), width=2)
        d.rectangle([x, 380, x + 6, 540], fill=rgb(PAL['steel']))
        d.text((x + 26, 398), fmt(v), font=F('archivo-700-normal-latin.woff2', 64), fill=rgb(PAL['ink']))
        d.text((x + 28, 490), lab, font=F('ibm-plex-sans-500-normal-latin.woff2', 22), fill=rgb(PAL['muted']))
    d.text((64, 572), 'Counted from the registries · partners PROPOSED · agents SCRIPTED, no AI model',
           font=F('ibm-plex-mono-500-normal-latin.woff2', 20), fill=rgb(PAL['muted']))
    out = io.BytesIO()
    im.save(out, format='PNG', optimize=False)
    return out.getvalue(), figs


CARD_BYTES, CARD_FIGS = draw_card()
CARD_SHA = hashlib.sha256(CARD_BYTES).hexdigest()
# the card is bytes: the same staleness rule, done by hand (written first: the head reads its size)
card_path = ROOT / CARD
if '--check' in sys.argv:
    if not card_path.is_file() or card_path.read_bytes() != CARD_BYTES:
        print(f'STALE: {CARD}\n       run: python3 web/build_whitepaper.py')
        sys.exit(1)
else:
    card_path.parent.mkdir(parents=True, exist_ok=True)
    if not card_path.is_file() or card_path.read_bytes() != CARD_BYTES:
        card_path.write_bytes(CARD_BYTES)
CARD_ALT = ('The whitepaper share card: the ' + BRAND_FULL + ' wordmark, the word Whitepaper, the line "' + TAGLINE
            + '" and four counted figures: ' + ', '.join(f'{fmt(f["value"])} {f["label"].lower()}' for f in CARD_FIGS) + '.')

# ----------------------------------------------------------------------- page
STYLED = ('html:is([data-style],:has(input[name="tc-style"]:is('
          + ','.join(f'[value="{x["id"]}"]' for x in _STYLES) + '):checked))')
NAV = nav_html(PAGE, nav_labels('en'))
TITLE = 'Whitepaper — ' + BRAND_FULL
DESC = (f'{BRAND_FULL} whitepaper, counted from its registries: {fmt(V(KEY[0][1]))} courses, {fmt(V(KEY[1][1]))} union '
        f'halls, {fmt(V(KEY[2][1]))} scripted agents.')
HEAD_LINE = f'{BRAND_FULL}: the whitepaper'
SOURCES = sorted({spec.split('#')[0] for spec, _ in USED} | {f['fig'].split('#')[0] for f in CARD_FIGS})

toc = ''.join(f'<li><a href="#{sid}">{E(h)}</a></li>' for sid, h, _ in SECTIONS)
secs = ''.join(f'<section id="{sid}" data-paper-section="{sid}"><h2>{E(h)}</h2>{b}</section>\n' for sid, h, b in SECTIONS)
src_list = ''.join(f'<li><code>{E(s)}</code> <span class="muted">stamp</span> '
                   f'<code>{E(load(s).get("source_stamp", "") if isinstance(load(s), dict) else "")}</code></li>'
                   if s.endswith('.json') else f'<li><code>{E(s)}</code></li>' for s in SOURCES)
# the stamps carry hex digits; they are registry values, so they ride as data-fig too
src_list = ''.join(
    (f'<li><code>{E(s)}</code> <span class="muted">source stamp</span> {N(s + "#/source_stamp", tag="code", cls="")}</li>'
     if s.endswith('.json') and isinstance(load(s), dict) and 'source_stamp' in load(s)
     else f'<li><code>{E(s)}</code></li>') for s in SOURCES)

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{E(TITLE)}</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="stylesheet" href="vendor/fonts/fonts.css">
<style>
:root {{
  --paper:#F1F4F3; --surface:#FFFFFF; --ink:#141D20; --muted:#54646A; --line:#CBD6D6;
  --accent:#0A7E8C; --accent-ink:#065A66; --mark:#9F680B; --head:#141D20; --code-bg:#E4EAE9;
  --ok:#22603C; --open:#8E3627; --chip-bg:#E4EAE9;
  color-scheme: light dark;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --paper:#12181B; --surface:#182023; --ink:#E8EDEC; --muted:#A3B1B4; --line:#28353A;
  --accent:#41C4D4; --accent-ink:#7FDCE8; --mark:#E8A33D; --head:#F4F7F6; --code-bg:#0C1113;
  --ok:#6CCB8E; --open:#E07C68; --chip-bg:#0C1113;
}} }}
:root[data-theme="dark"] {{
  --paper:#12181B; --surface:#182023; --ink:#E8EDEC; --muted:#A3B1B4; --line:#28353A;
  --accent:#41C4D4; --accent-ink:#7FDCE8; --mark:#E8A33D; --head:#F4F7F6; --code-bg:#0C1113;
  --ok:#6CCB8E; --open:#E07C68; --chip-bg:#0C1113;
}}
{STYLED} {{ --paper:var(--plate); --surface:var(--panel); --code-bg:var(--raised); --head:var(--ink); --accent-ink:var(--link); --chip-bg:var(--raised); }}
/* under a site theme the chips take the theme's own ink on its raised plate, the pair every theme guarantees AA */
{STYLED} .chip {{ color:var(--ink); }}
* {{ box-sizing:border-box; }}
body {{ background:var(--paper); color:var(--ink); margin:0; font:16px/1.65 "IBM Plex Sans", system-ui, sans-serif; }}
nav.sitenav {{ --sn-mark:var(--accent-ink); }}
.wrap {{ max-width:80ch; margin:0 auto; padding:0 16px 96px; overflow-wrap:anywhere; }}
header.hero {{ padding:48px 0 24px; border-bottom:2px solid var(--ink); }}
.eyebrow {{ font:600 12px/1 "Archivo",sans-serif; letter-spacing:.14em; text-transform:uppercase; color:var(--accent-ink); margin:0 0 14px; }}
h1 {{ font:700 clamp(30px,5.4vw,46px)/1.08 "Archivo",sans-serif; color:var(--head); margin:0 0 12px; text-wrap:balance; }}
.attrib {{ font:500 14px/1.3 "IBM Plex Sans",sans-serif; color:var(--muted); margin:0 0 16px; }}
.card {{ margin:20px 0 0; }}
.card img {{ display:block; width:100%; height:auto; border:1px solid var(--line); border-radius:6px; }}
.card figcaption {{ font-size:13px; color:var(--muted); margin-top:8px; }}
nav.toc ol {{ display:flex; flex-wrap:wrap; gap:8px; list-style:none; padding:0; margin:20px 0 0; }}
nav.toc a {{ display:inline-block; font:500 13px/1 "IBM Plex Mono",monospace; color:var(--accent-ink); text-decoration:none;
  padding:8px 10px; border:1px solid var(--line); border-radius:4px; }}
nav.toc a:hover, nav.toc a:focus-visible {{ border-color:var(--accent); color:var(--ink); }}
h2 {{ font:700 26px/1.2 "Archivo",sans-serif; color:var(--head); margin:52px 0 14px; padding-top:20px;
  border-top:1px solid var(--line); scroll-margin-top:16px; text-wrap:balance; }}
h3 {{ font:600 18px/1.3 "Archivo",sans-serif; color:var(--head); margin:28px 0 10px; }}
p {{ margin:0 0 14px; }}
.lede {{ font-size:19px; color:var(--head); }}
.muted {{ color:var(--muted); }}
a {{ color:var(--accent-ink); }}
code {{ font:13px/1.5 "IBM Plex Mono",monospace; background:var(--code-bg); padding:1px 5px; border-radius:3px; overflow-wrap:anywhere; }}
.bccard {{ display:grid; gap:6px; margin:0 0 16px; padding:12px 14px; background:var(--surface); border:1px solid var(--line); border-radius:4px; }}
.bccard div {{ display:grid; grid-template-columns:minmax(90px,140px) 1fr; gap:12px; }}
.bccard dt {{ font:600 12px/1.5 "IBM Plex Mono",monospace; color:var(--muted); }}
.bccard dd {{ margin:0; overflow-wrap:anywhere; }}
.deny {{ font-weight:600; color:var(--head); }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:18px 0 20px; }}
.tiles div {{ background:var(--surface); border:1px solid var(--line); border-inline-start:4px solid var(--accent); border-radius:4px; padding:12px 14px; }}
.tiles dt {{ font-size:13px; color:var(--muted); }}
.tiles dd {{ margin:4px 0 0; font:700 28px/1.1 "Archivo",sans-serif; color:var(--head); font-variant-numeric:tabular-nums; }}
.chips {{ display:flex; flex-wrap:wrap; gap:8px; }}
.chip {{ font:600 11.5px/1 "IBM Plex Mono",monospace; letter-spacing:.04em; padding:6px 8px; border-radius:3px;
  background:var(--chip-bg); border:1px solid var(--line); color:var(--ink); max-width:100%; overflow-wrap:anywhere; }}
main section:first-of-type h2 {{ border-top:none; }}
.chip-open {{ color:var(--open); border-color:var(--open); }}
.chip-ok {{ color:var(--ok); border-color:var(--ok); }}
.chip-scr, .chip-auth, .chip-der, .chip-rec, .chip-sch {{ color:var(--accent-ink); }}
.tw {{ overflow-x:auto; margin:0 0 18px; }}
table {{ border-collapse:collapse; width:100%; font-size:14.5px; font-variant-numeric:tabular-nums; }}
th {{ font:600 11.5px/1.3 "Archivo",sans-serif; letter-spacing:.08em; text-transform:uppercase; text-align:start;
  color:var(--muted); border-bottom:2px solid var(--ink); padding:8px 12px 6px 0; }}
td {{ border-bottom:1px solid var(--line); padding:8px 12px 8px 0; vertical-align:top; }}
blockquote.q {{ margin:0 0 14px; padding:4px 0 4px 16px; border-inline-start:3px solid var(--mark); color:var(--muted); }}
blockquote.q cite {{ display:block; font:12px/1.4 "IBM Plex Mono",monospace; margin-top:4px; font-style:normal; overflow-wrap:anywhere; }}
ul.status li {{ margin-bottom:8px; }}
.cta {{ display:flex; flex-wrap:wrap; gap:24px; align-items:center; background:var(--surface); border:1px solid var(--line);
  border-radius:6px; padding:20px; }}
.cta > div {{ flex:1 1 260px; }}
.btn {{ display:inline-block; font:600 16px/1 "Archivo",sans-serif; background:var(--ink); color:var(--paper); text-decoration:none;
  padding:14px 18px; border-radius:4px; overflow-wrap:anywhere; }}
.btn:focus-visible {{ outline:3px solid var(--accent); outline-offset:3px; }}
.qrfig {{ margin:0; flex:0 0 auto; }}
.qrfig svg {{ display:block; width:168px; height:168px; border-radius:4px; }}
footer.src {{ margin-top:56px; padding-top:16px; border-top:1px solid var(--line); font-size:13px; color:var(--muted); }}
footer.src ul {{ padding-inline-start:18px; }}
@media (prefers-reduced-motion: no-preference) {{ html {{ scroll-behavior:smooth; }} }}
</style>
<style>{NAV_CSS}</style>
</head><body>
{NAV}<main class="wrap" data-paper-date="{E(DATE)}">
<header class="hero">
  <p class="eyebrow">Whitepaper</p>
  <h1>{E(BRAND_FULL)}</h1>
  <p class="attrib">{E(ATTRIB)} &middot; published by {E(PUBLISHER)}</p>
  <figure class="card"><img src="img/smartcitix_whitepaper_card.png" width="1200" height="630" alt="{E(CARD_ALT)}" data-sha256="{CARD_SHA}">
  <figcaption>The share card for this page, drawn when the page is built from the same counted figures.</figcaption></figure>
  <nav class="toc" aria-label="Sections"><ol>{toc}</ol></nav>
</header>
{secs}<footer class="src"><p>Built from these registries; each figure above names its own source in the page markup.</p><ul>{src_list}</ul></footer>
</main>
</body></html>
"""
page = apply_seo(page, PAGE, TITLE, DESC, 'article',
                 article={'date': DATE, 'image': CARD, 'image_alt': CARD_ALT, 'publisher': PUBLISHER,
                          'email': CONTACT, 'headline': HEAD_LINE})
page = with_style_memory(page)

pin = json.dumps({'image': CARD, 'sha256': CARD_SHA, 'width': 1200, 'height': 630,
                  'generator': 'web/build_whitepaper.py', 'page': PAGE, 'figures': CARD_FIGS},
                 indent=1, ensure_ascii=False) + '\n'

emit(ROOT / PIN, pin, f'card sha256 {CARD_SHA[:12]}')
emit(ROOT / PAGE, page, f'{len(SECTIONS)} sections, {len(USED)} counted figures, date {DATE}'
     + ('' if HAVE_PATHS else '; union pathways omitted (no registry)')
     + ('' if HAVE_PROGRAMS else '; programmes and sectors omitted (no registry)'))
