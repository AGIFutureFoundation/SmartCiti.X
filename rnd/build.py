#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy - the R&D registry builder.

WHY THIS PACK EXISTS. This bundle knows a great many measured facts about
itself and they are scattered: a browser eval harness that scores three
views, a reference-model note in `assets/`, a dozen `honesty` blocks in a
dozen registries, several hundred named checks across forty-one suites, and
a spec whose most valuable paragraphs are the ones recording that a
measurement did NOT show what was hoped. Somebody doing research and
development on this bundle - deciding what to build next, or what is
already proven - has nowhere to ask the three questions that actually
matter: what has been MEASURED, what is DECLARED but unbuilt, and where are
the known GAPS.

This pack answers those three from the registries themselves.

IT IS DERIVED, WHICH IS THE WHOLE POINT. Nothing below is a fact about the
bundle that was typed here. Every number is read out of a file at build
time and every entry carries the path it was read from and the locator -
a dotted JSON path or a regular expression - that found it. That is not
tidiness; it is the only property that makes an R&D register worth
consulting a second time. A backlog somebody maintains by hand is a
backlog that is wrong by the end of the week. A pack that gets wired up
drops off `declared_unbuilt` on the next build of this file without
anybody editing it, because the entry is computed from whether a renderer
names its registry path, not from a note saying so.

The same rule turns the register hostile to flattery. If 27 of 111 halls
have a lesson, the gap says 0.243 and not "good coverage". If 0 of 111
halls carry a practitioner sign-off, the gap says 0.0. If a suite runs
nine checks, it appears at the thin end of the suite table next to one
that runs 188. A pack that only surfaced good news would be worse than no
pack, because it would have to be checked against the thing it claims to
be a summary of, which is exactly the work it exists to save.

THE SEVEN BLOCKS.

`measured` - every number in this bundle that came from an ACTUAL
MEASUREMENT rather than from a choice, with what measured it, when, and
under what conditions. Three tiers, and the tier is the honest part:
MEASURED-IN-BROWSER is the scene harness's own scorecard, taken in a real
Chromium at a stated size and quality rung; MEASURED-ELSEWHERE is a figure
taken off files this repository does not contain and cannot re-measure -
the six reference models, a font's rendered character width, an ape mesh;
COMPUTED-FROM-REGISTRY is a number one pack's builder worked out from
another pack's registry, which is not a measurement of the world but IS a
measurement of this bundle. Every entry names its source FILE and the
field or pattern it was read from, and `rnd/test.mjs` re-resolves every
single pointer against the live file rather than trusting the value.

`declared_unbuilt` - the R&D backlog, computed from two independent
signals. The first is a registry that declares `honesty.not_built_yet` in
its own words. The second is arithmetic over the tree: a registry whose
repo-relative path appears in no RENDERER and in no other pack's BUILDER
is a registry nothing consumes, whatever it says about itself. Neither
signal is a list kept here.

`gaps` - coverage gaps with both halves computed live. A gap is a
numerator over a denominator, each read from the registry that owns it,
with the share to four places and the paths it was computed from. Gaps
that are CLOSED stay in the block with a share of 1.0, because a register
that only showed the open ones would be a way of hiding which closures
were ever real.

`budgets` - the two currencies of this renderer, draw calls and triangles,
per view. The measured baseline, the declared ceiling, what `kit/` and
`props/` have already claimed against that view, and what is left. Every
figure is read from `web/eval_scene.mjs` and the two packs; the ceiling
arithmetic is re-done here with the eval's own rounding and cross-checked
against what each pack published, so a ceiling cannot mean two things.

`suites` - the check count per suite, parsed out of README.md's own table
and joined to the suite list `verify_all.sh` actually runs. It shows where
the assurance is and where it is thin, and it names the suites that run
without declaring a count at all.

`open_questions` - things this bundle records as unanswered, including the
NEGATIVE findings, which are the most valuable entries in the pack and are
currently buried in source comments and spec prose where nothing points at
them. A negative finding is a measurement that did not show what was
hoped: the working-set sweep whose measured optimum contradicts the policy
it was run to support; the hue encoding that produced 94 distinct colours
for 111 halls; the mentor gate that only cohort outcome could catch. Each
is QUOTED, not paraphrased - the builder locates two anchors in the source
file and publishes the slice between them, so the text cannot drift from
the file and the test proves the slice is still verbatim. Alongside them
sit the CROSS-CHECKS: the same figure recorded in two files, compared
here, with `agree` computed. Two of them currently disagree.

`page_contract` - how a dashboard would render this.

WHAT THIS PACK DOES NOT DO. It states no fact of its own about the trades,
the halls, the world or the renderer. It reaches no network, loads nothing,
and adds no dependency. It is not a roadmap: `roadmap/` owns the campus
network's own plan and this pack does not duplicate it. Its provenance
word is DERIVED. AI-SYNTHESIZED belongs to `orbis/` and describes generated
video; nothing here is that, and the build asserts the word is absent.

A DEFAULT IS A POLICY DECISION. There is no bare `??` and no
`.get(k, default)` anywhere below. Every read goes through `need`, `dig`
or `one`, each of which raises an error naming itself and the path it was
looking in. A missing key is a broken pointer, and a broken pointer in a
register of pointers is the one bug that must never be papered over.
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-22"

# --------------------------------------------------------------- readers ---
# Every file this build opens is recorded, so `reads` at the bottom is the
# set of files actually consulted rather than a list somebody maintains.
_TEXT = {}
_JSON = {}


def text(rel):
    """The text of a repo file, read once. A path that does not exist is a
    broken pointer and stops the build naming itself."""
    if rel not in _TEXT:
        p = ROOT / rel
        if not p.is_file():
            raise FileNotFoundError(
                f'rnd: {rel} is named by this build and does not exist')
        _TEXT[rel] = p.read_text(encoding='utf8')
    return _TEXT[rel]


def flat(rel):
    """The same text with every run of whitespace collapsed to one space.
    Prose in this repo is hard-wrapped, so an anchor that spans a line
    break can only be found in the flattened form. `rnd/test.mjs` flattens
    the same way and compares, which is what makes a quote checkable."""
    return ' '.join(text(rel).split())


def reg(rel):
    """A registry, parsed once."""
    if rel not in _JSON:
        _JSON[rel] = json.loads(text(rel))
    return _JSON[rel]


def need(obj, key, where):
    """One key, or a build failure that says which key and where. There is
    no default arm: a default here would silently turn a moved field into
    a plausible-looking zero, which is the exact failure this pack exists
    to make impossible elsewhere."""
    if not isinstance(obj, dict):
        raise TypeError(f'rnd: {where}: expected an object to read {key!r} from')
    if key not in obj:
        raise KeyError(
            f'rnd: {where}: no key {key!r} (it holds {sorted(obj)[:12]})')
    return obj[key]


def dig(rel, dotted):
    """Resolve a dotted path inside a registry, naming the exact step that
    failed. This is the locator `measured` publishes, and the test walks
    the identical path against the live file."""
    node = reg(rel)
    walked = []
    for part in dotted.split('.'):
        walked.append(part)
        node = need(node, part, f'{rel}#{".".join(walked[:-1]) or "(root)"}')
    return node


def one(rel, pattern, what, group=1):
    """Exactly one match, or the build stops. Not `the first match`: a
    pattern that has started matching twice is a pattern that no longer
    identifies the thing it was written to identify."""
    hits = re.findall(pattern, text(rel))
    if len(hits) != 1:
        raise LookupError(
            f'rnd: {rel}: {what}: /{pattern}/ matched {len(hits)} times, '
            f'and this build reads it only when it matches exactly once')
    m = re.search(pattern, text(rel))
    return m.group(group)


def one_flat(rel, pattern, what, group=1):
    """The same, against the flattened text, for prose that is hard-wrapped
    across a line break. The test flattens identically."""
    src = flat(rel)
    hits = re.findall(pattern, src)
    if len(hits) != 1:
        raise LookupError(
            f'rnd: {rel} (flattened): {what}: /{pattern}/ matched '
            f'{len(hits)} times, and this build reads it only when it '
            f'matches exactly once')
    return re.search(pattern, src).group(group)


def num(s):
    """A number as this repo writes them: underscored, comma-grouped or
    plain. The separators are stripped and nothing else is interpreted."""
    return float(s.replace('_', '').replace(',', ''))


def quote(rel, start, end):
    """The slice of a file between two anchors, inclusive, flattened. The
    builder refuses an anchor that is not unique and refuses an end that
    precedes its start, so a quote cannot silently become a different
    paragraph when the file is edited around it."""
    src = flat(rel)
    if src.count(start) != 1:
        raise LookupError(f'rnd: {rel}: the opening anchor {start[:48]!r} '
                          f'appears {src.count(start)} times, not once')
    if src.count(end) != 1:
        raise LookupError(f'rnd: {rel}: the closing anchor {end[:48]!r} '
                          f'appears {src.count(end)} times, not once')
    a = src.index(start)
    b = src.index(end) + len(end)
    if b <= a:
        raise LookupError(f'rnd: {rel}: the closing anchor precedes the opening one')
    return src[a:b]


def share(n, d, what):
    """A numerator over a denominator, refusing a denominator of zero
    rather than publishing a share nobody can read."""
    if d == 0:
        raise ZeroDivisionError(f'rnd: {what}: a gap with no denominator')
    return round(n / d, 4)


def jsround(x):
    """JavaScript's Math.round, which the eval harness uses. Python rounds
    half to even and JavaScript rounds half up; they disagree on .5, and
    that disagreement is how a ceiling drifts between two files that both
    believe they are computing the same one."""
    import math
    return math.floor(x + 0.5)


# ------------------------------------------------------------- the files ---
EVAL = 'web/eval_scene.mjs'
REFERENCE = 'assets/REFERENCE.md'
KIT = 'kit/registry/kit.json'
PROPS = 'props/registry/props.json'
SKY = 'sky/registry/sky.json'
LESSONS = 'lessons/registry/lessons.json'
SIMS = 'sims/registry/sims.json'
SCHOOLS = 'schools/registry/schools.json'
RESTORATION = 'restoration/registry/restoration.json'
TRAINING = 'training/registry/training.json'
ADVISORS = 'agents/registry/advisors.json'
FINISHES = 'surfaces/registry/finishes.json'
HALLS = 'pack/registry/halls.json'
GEO = 'geo/registry/campuses_geo.json'
GEOPOSE = 'spatial/registry/geopose.json'
GUIDE = 'guide/registry/guide.json'
STATIONS = 'stations/registry/stations.json'
CAMPUSES = 'unions/registry/campuses.json'
PAGE = 'web/build_3d.py'
SPEC = 'SmartCitiX_TradeCraft_Academy_Spec.md'
README = 'README.md'
VERIFY = 'verify_all.sh'

# ============================================================== MEASURED ===
# Every number in this bundle that came from an actual measurement rather
# than from a choice. Each entry is a POINTER plus the value that pointer
# currently resolves to; nothing here is typed, and `rnd/test.mjs` re-walks
# every pointer against the live file and fails on any that has moved.
#
# Three tiers, because they carry very different weight:
#
#   MEASURED-IN-BROWSER    a real Chromium drew the thing and a counter was
#                          read. Re-runnable here, by `node web/eval_scene.mjs`
#                          against a local server; not run by verify_all.sh.
#   MEASURED-ELSEWHERE     a figure taken off files or a rendering this
#                          repository does not contain. It is QUOTED, and
#                          this build cannot re-take it.
#   COMPUTED-FROM-REGISTRY a number one pack's builder worked out from
#                          another pack's registry. Not a measurement of the
#                          world; it IS a measurement of this bundle, and it
#                          re-computes on every build.
TIERS = ('MEASURED-IN-BROWSER', 'MEASURED-ELSEWHERE', 'COMPUTED-FROM-REGISTRY')

MEASURED = []


def measure(mid, what, value, unit, tier, rel, locator, when, conditions,
            method, why):
    """Record one measured fact. Every argument is required; there is no
    shorthand that lets an entry ship without saying when it was taken or
    what took it, because an unconditioned measurement is an anecdote."""
    if tier not in TIERS:
        raise ValueError(f'rnd: {mid}: {tier!r} is not one of {TIERS}')
    if need(locator, 'kind', f'{mid} locator') not in ('json', 'regex'):
        raise ValueError(f'rnd: {mid}: a locator is a json path or a regex')
    for field, txt, floor in (('what', what, 12), ('when', when, 8),
                              ('conditions', conditions, 12),
                              ('method', method, 12), ('why', why, 12)):
        if not isinstance(txt, str) or len(txt) < floor:
            raise ValueError(f'rnd: {mid}: {field} is missing or too thin')
    MEASURED.append({'id': mid, 'what': what, 'value': value, 'unit': unit,
                     'tier': tier, 'file': rel, 'locator': locator,
                     'when': when, 'conditions': conditions,
                     'method': method, 'why': why})


# -- the scene scorecard. The only numbers in this bundle a browser
# -- actually produced. The date and the rig are read out of the harness's
# -- own comment, not restated, so a re-measurement moves them here too.
EVAL_WHEN = one(EVAL, r'Baseline measured (\d{4}-\d{2}-\d{2}),', 'the baseline date')
EVAL_RIG = one_flat(EVAL, r'Baseline measured \d{4}-\d{2}-\d{2}, (.*?)\. Headroom',
                    'the rig the baseline was taken on')
EVAL_METHOD = ('web/eval_scene.mjs drives the built page through each view in '
               'Playwright-driven Chromium, renders two frames so the counters '
               'belong to this view and not the last one, and reads '
               'renderer.info plus a walk of the visible scene graph')
EVAL_VIEWS = {}
for _v in re.findall(r'\n  ([a-z]+):\s*\{ calls: [\d_]+, tris: [\d_]+, meshes: [\d_]+ \},', text(EVAL)):
    EVAL_VIEWS[_v] = {}
if not EVAL_VIEWS:
    raise LookupError('rnd: web/eval_scene.mjs no longer declares a BASE table')

_EVAL_COLS = {
    'calls': (r'{v}:\s*\{{ calls: ([\d_]+)', 'draw calls',
              'the scarce currency on this page: one per material per merged '
              'group, so it counts pieces of state rather than geometry'),
    'tris': (r'{v}:\s*\{{ calls: [\d_]+, tris: ([\d_]+)', 'triangles',
             'the cheap currency here, and the one the kit and props packs '
             'were written to spend'),
    'meshes': (r'{v}:\s*\{{ calls: [\d_]+, tris: [\d_]+, meshes: ([\d_]+)',
               'visible meshes',
               'a FLOOR rather than a ceiling: it asks whether enough separate '
               'things are standing in the view for it to read as a place'),
}
for _v in sorted(EVAL_VIEWS):
    for _col, (_pat, _unit, _why) in _EVAL_COLS.items():
        _p = _pat.format(v=_v)
        _val = int(num(one(EVAL, _p, f'the measured {_v} {_col}')))
        EVAL_VIEWS[_v][_col] = _val
        measure(f'eval.{_v}.{_col}',
                f'the {_v} view, measured {_unit}', _val, _unit,
                'MEASURED-IN-BROWSER', EVAL,
                {'kind': 'regex', 'pattern': _p, 'group': 1, 'cast': 'int'},
                EVAL_WHEN, EVAL_RIG, EVAL_METHOD, _why)

# -- the reference models. Six files that were opened, measured and closed
# -- outside this repository; none is here and none ever will be. The table
# -- is parsed out of the note rather than retyped, so this pack cannot hold
# -- a figure the note has since corrected.
REF_COLS = ['file_mb', 'triangles', 'meshes', 'materials', 'images',
            'textures_mb', 'animations']
REF_UNITS = {'file_mb': 'MB', 'triangles': 'triangles', 'meshes': 'meshes',
             'materials': 'materials', 'images': 'images',
             'textures_mb': 'MB', 'animations': 'animations'}
REF_MODELS = re.findall(r'\n\| `([A-Za-z0-9_.-]+\.glb)` \|', text(REFERENCE))
if len(REF_MODELS) != len(set(REF_MODELS)) or not REF_MODELS:
    raise LookupError('rnd: assets/REFERENCE.md no longer holds a unique model table')
REF_WHEN = ('undated in ' + REFERENCE + ': '
            + quote(REFERENCE, 'It is a scratch script', 'is not committed.'))
REF_METHOD = quote(REFERENCE, 'RECORDED. Every figure above',
                   'walks the glTF JSON and the binary image chunks.')
REF_CONDITIONS = quote(REFERENCE, 'Taken from the glTF containers directly',
                       'the sum of the embedded images.')
REF_FIGURES = {}
for _m in REF_MODELS:
    _esc = re.sub(r'([.^$*+?()\[\]{}|\\])', r'\\\1', _m)
    REF_FIGURES[_m] = {}
    for _i, _col in enumerate(REF_COLS):
        _pat = (r'\| `' + _esc + r'` \|'
                + r' [\d,.]+ \|' * _i + r' ([\d,.]+) \|')
        _val = num(one(REFERENCE, _pat, f'{_m} {_col}'))
        _val = int(_val) if _col not in ('file_mb', 'textures_mb') else _val
        REF_FIGURES[_m][_col] = _val
        measure(f'reference.{_m}.{_col}',
                f'{_m}: {_col.replace("_", " ")}', _val, REF_UNITS[_col],
                'MEASURED-ELSEWHERE', REFERENCE,
                {'kind': 'regex', 'pattern': _pat, 'group': 1,
                 'cast': 'float' if _col in ('file_mb', 'textures_mb') else 'int'},
                REF_WHEN, REF_CONDITIONS, REF_METHOD,
                'the distribution these six files hold is the whole reason '
                'kit/ and props/ have a per-piece triangle budget at all; '
                'no geometry, texture or name from any of them is here')

for _mid, _pat, _what, _why in (
    ('reference.block_median_tris', r'The median mesh is (\d+) triangles',
     'the median mesh of the residential block that reads as a place',
     'kit/ sizes its exterior pieces against this and says so in its own '
     '`reference` block'),
    ('reference.house_median_tris', r'a median mesh of (\d+) triangles',
     'the median mesh of the single interior from the same source',
     'props/ sizes its interior props against this and says so in its own '
     '`measured` block'),
):
    measure(_mid, _what, int(num(one(REFERENCE, _pat, _what))), 'triangles',
            'MEASURED-ELSEWHERE', REFERENCE,
            {'kind': 'regex', 'pattern': _pat, 'group': 1, 'cast': 'int'},
            REF_WHEN, REF_CONDITIONS, REF_METHOD, _why)

# -- two rendered character widths. Both exist because a GUESSED one let an
# -- assertion pass while the text ran out of its box; the negative finding
# -- that produced them is in `open_questions`.
for _mid, _rel, _name, _what, _why in (
    ('font.map_px_per_char', 'web/build_map.py', 'PX_PER_CHAR',
     'rendered width of one uppercase character, Barlow Condensed 700 at 13.5px',
     'the campus-map pad is sized from it, so a hall name either fits by '
     'arithmetic or fails the build'),
    ('font.plan_px_per_char', 'web/interiors.py', 'PX_PER_CHAR',
     'rendered width of one uppercase character, Barlow Condensed 700 at 11px',
     'every room in the 1,221-room plan is at least wide enough for its own '
     'name because the width is derived from this'),
    ('font.plan_caption_px_per_char', 'web/interiors.py', 'CAPTION_PX_PER_CHAR',
     'rendered width of one caption character, IBM Plex Mono 400 at 7.2px',
     'the room caption is held to the same arithmetic as the room label'),
):
    _pat = r'\n' + _name + r' = ([\d.]+)'
    measure(_mid, _what, float(one(_rel, _pat, _what)), 'px/char',
            'MEASURED-ELSEWHERE', _rel,
            {'kind': 'regex', 'pattern': _pat, 'group': 1, 'cast': 'float'},
            'undated in the source; recorded at the commit that replaced the '
            'guessed constant',
            'measured in a browser at the stated family, weight and size, on '
            'uppercase text',
            'the browser was asked what it actually rendered, rather than the '
            'width being inferred from an em ratio',
            _why)

# -- the ape proportions, measured off a mesh that is not here.
for _f, _unit in (('height', 'model units'), ('span', 'model units'),
                  ('depth', 'model units'), ('span_to_height', 'ratio')):
    _path = f'tradeapes.ape_reference.{_f}'
    measure(f'ape.{_f}', f'ape anatomy reference: {_f}',
            dig('avatars/registry/avatars.json', _path), _unit,
            'MEASURED-ELSEWHERE', 'avatars/registry/avatars.json',
            {'kind': 'json', 'path': _path},
            'undated in the registry; taken at the build that introduced the '
            'TradeApes collection',
            'a user-supplied low-poly ape GLB exported by Khronos glTF '
            'Blender I/O v1.6.16, whose licence is unknown',
            dig('avatars/registry/avatars.json',
                'tradeapes.ape_reference.provenance'),
            'the proportions are the whole of what was taken; the mesh is '
            'not shipped and no geometry or texture is copied')

# -- one photometric measurement, taken on a hall interior inside this page.
# This pair used to be read as a measurement. It is no longer one: the
# figure was written down twice with two different second values and the
# frame that would settle it is gone, so both files now carry the SAME
# sentence disclosing the disagreement instead of each asserting a number.
# The locators follow that sentence.
_LUM_BEFORE = int(one(PAGE, r'(46) to 96 in this file',
                      'the luminance before the candela conversion'))
_LUM_AFTER_PAGE = int(one(PAGE, r'46 to (\d+) in this file',
                          'the luminance the page generator recorded'))
_LUM_AFTER_SUITE = int(one(PAGE, r'46 to (\d+) in the suite',
                           'the luminance the suite recorded'))
for _mid, _pat, _val, _what in (
    ('luminance.before', r'(46) to 96 in this file', _LUM_BEFORE,
     'mean frame luminance of a hall interior lit with legacy-scale '
     'intensities - the one half of this measurement the two records agree on'),
    ('luminance.after.as-the-page-recorded-it', r'46 to (\d+) in this file',
     _LUM_AFTER_PAGE,
     'what the page generator wrote down for the same frame after the '
     'candela conversion - DISPUTED, see the cross-check'),
    ('luminance.after.as-the-suite-recorded-it', r'46 to (\d+) in the suite',
     _LUM_AFTER_SUITE,
     'what the suite wrote down for the same frame - DISPUTED, and the frame '
     'is gone, so neither is quoted as measured any more'),
):
    measure(_mid, _what, _val, '0-255', 'MEASURED-IN-BROWSER', PAGE,
            {'kind': 'regex', 'pattern': _pat, 'group': 1, 'cast': 'int'},
            'undated in the source; recorded at the commit that introduced '
            'lampCd()',
            'one hall interior, measured as a mean over the rendered frame',
            'the frame was sampled rather than looked at: three.js r155 made '
            'PointLight intensity candela, and the old numbers were real '
            'lights that lit nothing',
            'it is the evidence that the lights were not merely dim but '
            'indistinguishable from absent, which is why one conversion now '
            'stands between every luminaire and the scene')

# -- numbers one pack's builder computed from another pack's registry.
for _mid, _rel, _path, _unit, _what, _why in (
    ('kit.campus_pieces', KIT, 'counts.campus_pieces', 'pieces',
     'exterior kit pieces predicted for the flagship campus',
     'it is a PREDICTION from placement rules over 51 halls, not a render'),
    ('kit.campus_triangles', KIT, 'counts.campus_triangles', 'triangles',
     'triangles those pieces would cost',
     'it is the figure the campus triangle ceiling is spent against'),
    ('kit.campus_draw_calls', KIT, 'counts.campus_draw_calls', 'draw calls',
     'draw calls those pieces would cost if they merge as declared',
     'it is the figure the campus draw-call ceiling is spent against'),
    ('kit.pieces_per_draw_call', KIT, 'counts.pieces_per_draw_call', 'pieces/call',
     'how many pieces the kit gets for one draw call',
     'the one-mesh-per-piece anti-pattern the reference models exhibit can '
     'never reach this number, which is what makes the check arithmetic'),
    ('props.prop_instances', PROPS, 'counts.prop_instances', 'props',
     'interior props the placement rules would stand across the bundle',
     'it is the size of the thing that is declared and not yet drawn'),
    ('props.rooms_requiring_ppe', PROPS, 'counts.rooms_requiring_ppe', 'rooms',
     'rooms whose own conditions record asks for protective equipment',
     'the build fails if one of them gets no PPE prop, so the number is a '
     'constraint rather than a statistic'),
    ('props.bundle_triangles', PROPS, 'budget.bundle.triangles', 'triangles',
     'triangles the whole bundle of props would cost',
     'stated so the prediction can be compared against a later measurement'),
    ('sky.equivalent_sky_magnitude', SKY, 'stars.equivalent_sky_magnitude', 'magnitude',
     'the visual magnitude a real sky would have to reach to hold as many '
     'stars as world/ asks for',
     'set against the magnitude the drawn field actually spans, it is the '
     'size of the gap between this star field and a sky chart'),
    ('sky.magnitude_cutoff', SKY, 'stars.magnitude_cutoff', 'magnitude',
     'the faintest magnitude the three drawn disc sizes reach',
     'derived from the drawn radii under Pogson, so it moves if the page '
     'changes a radius'),
    ('sky.gradient_stops', SKY, 'counts.gradient_stops', 'stops',
     'per-phase sky gradient stops declared',
     'all of them are currently unread by the page, which is why sky/ '
     'appears in declared_unbuilt'),
    ('geopose.total', GEOPOSE, 'counts.total', 'poses',
     'OGC GeoPose 1.0 Basic-YPR poses emitted from the source registries',
     'every one is height-zero and heading-zero with UNKNOWN, which the '
     'pack states rather than implies'),
    ('lessons.steps', LESSONS, 'counts.steps', 'steps',
     'lesson steps, every one resolving to a real id in another registry',
     'a step that could not resolve its ids failed the build rather than '
     'becoming a lesson with a footnote'),
):
    measure(_mid, _what, dig(_rel, _path), _unit, 'COMPUTED-FROM-REGISTRY',
            _rel, {'kind': 'json', 'path': _path},
            need(reg(_rel), 'built', _rel),
            f'computed by {_rel.split("/")[0]}/build.py from the registries '
            f'it reads; re-computed on every build of that pack',
            'derived arithmetic over another pack\'s registry, not an '
            'observation of anything rendered',
            _why)

if len({m['id'] for m in MEASURED}) != len(MEASURED):
    raise ValueError('rnd: two measured entries share an id')

# ======================================================= DECLARED_UNBUILT ===
# The R&D backlog, computed from two independent signals over the tree.
#
# SIGNAL ONE is a registry that says so itself, in a field named exactly
# `honesty.not_built_yet`. The field name is the contract - a pack that
# wants to appear here declares that key, and a pack that gets wired up
# removes it. This build reads the sentence; it never writes one.
#
# SIGNAL TWO is arithmetic. A RENDERER is a file that emits something a
# person looks at: the page generators under web/, the wiki, the ops
# console. A BUILDER is another pack's build.py. A registry whose
# repo-relative path appears in no renderer and in no builder is a
# registry nothing consumes, whatever its own honesty block says - and a
# registry that gets wired into a renderer drops out of this list on the
# next build of this file, with nobody editing anything here.
#
# Suites are scanned too but do NOT count as consumption: a test that
# reads a registry proves the registry is well-formed, not that anything
# in this bundle uses it. That distinction is the whole difference between
# a pack that is finished and a pack that is only verified.
# A RENDERER is split in two, because the difference is the whole signal.
# An APP renderer is a page generator under web/: whatever it reads is
# something a learner can actually stand in front of. A DOC renderer is the
# wiki or the ops console: whatever it reads has been written ABOUT, which
# is not the same as having been built. A registry the wiki documents and
# no page draws is precisely the shape this backlog exists to find, and
# collapsing the two would hide every entry in it.
APP_RENDERERS = sorted(
    [str(p.relative_to(ROOT)) for p in (ROOT / 'web').glob('build_*.py')]
    + ['web/groundtruth.py', 'web/interiors.py'])
DOC_RENDERERS = sorted(
    [str(p.relative_to(ROOT)) for p in (ROOT / 'console').glob('build_*.py')]
    + ['wiki/build_wiki.py'])
# This pack reads every registry in the tree by definition, so counting
# itself as a consumer would empty the backlog on its own first build.
BUILDERS = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob('*/build.py')
                  if p.parent.name != HERE.name)
SUITE_FILES = sorted(
    f for f in ({str(p.relative_to(ROOT)) for p in ROOT.glob('*/test*.mjs')}
                | {str(p.relative_to(ROOT)) for p in ROOT.glob('*/verify*.mjs')}
                | {str(p.relative_to(ROOT)) for p in ROOT.glob('web/test_*.mjs')})
    if f.split('/')[0] != HERE.name)
for _f in APP_RENDERERS + DOC_RENDERERS + BUILDERS:
    if not (ROOT / _f).is_file():
        raise FileNotFoundError(f'rnd: {_f} is scanned for reads and is gone')
if str(HERE.relative_to(ROOT)) + '/build.py' in BUILDERS:
    raise AssertionError('rnd: this pack must not count itself as a consumer')

REGISTRIES = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob('*/registry/*.json')
                    if p.parent.parent.name != HERE.name)
if not REGISTRIES:
    raise LookupError('rnd: no registries found; the scan pattern is wrong')


def named_by(rel, group, same_pack=False):
    """Which files in `group` name this registry by its repo-relative path.
    By default a file in the registry's OWN pack does not count: a pack
    reading itself is not another consumer, and counting it would let every
    pack certify its own wiring. `same_pack=True` returns exactly those
    in-pack files instead, so an entry that says nothing reads a registry
    can also say what its own pack does with it."""
    pack = rel.split('/')[0]
    return sorted(f for f in group
                  if (f.split('/')[0] == pack) == same_pack and rel in text(f))


def own_pack_readers(rel):
    """What the registry's OWN pack does with it. A pack reads its own
    registry by a relative path rather than by the repo-relative one, so
    this scan looks for the file's BASENAME inside the pack's own source -
    otherwise an entry could say nothing reads a registry while its own
    suite has been checking it all along, which would be a false finding of
    exactly the kind this pack must not produce."""
    pack, base = rel.split('/')[0], rel.split('/')[-1]
    out = []
    for p in sorted((ROOT / pack).rglob('*')):
        if p.suffix not in ('.py', '.mjs', '.js') or not p.is_file():
            continue
        r = str(p.relative_to(ROOT))
        if base in text(r):
            out.append(r)
    return out


CONSUMERS = {}
for _r in REGISTRIES:
    CONSUMERS[_r] = {'app_renderers': named_by(_r, APP_RENDERERS),
                     'doc_renderers': named_by(_r, DOC_RENDERERS),
                     'builders': named_by(_r, BUILDERS),
                     'suites': named_by(_r, SUITE_FILES),
                     'own_pack': own_pack_readers(_r)}

DECLARED_UNBUILT = []
for _r in REGISTRIES:
    _reasons = []
    _says = None
    _h = reg(_r)
    if isinstance(_h, dict) and 'honesty' in _h and isinstance(_h['honesty'], dict) \
            and 'not_built_yet' in _h['honesty']:
        _says = need(need(_h, 'honesty', _r), 'not_built_yet', f'{_r}#honesty')
        _reasons.append('the registry declares honesty.not_built_yet')
    _c = CONSUMERS[_r]
    if not _c['app_renderers']:
        _reasons.append('no page generator under web/ names this path, so '
                        'nothing a learner opens reads it')
        if _c['doc_renderers']:
            _reasons.append('it is DOCUMENTED but not drawn: '
                            + ', '.join(_c['doc_renderers'])
                            + ' renders a description of it')
        if not _c['builders'] and not _c['doc_renderers'] and not _c['suites']:
            _reasons.append(
                'and nothing outside its own pack names it either - not a '
                'builder, not the wiki, not another pack\'s suite; inside '
                'it, ' + (', '.join(_c['own_pack']) or 'nothing at all')
                + ' does')
    if not _reasons:
        continue
    DECLARED_UNBUILT.append({
        'registry': _r,
        'pack': _r.split('/')[0],
        'reasons': _reasons,
        'says': _says,
        'read_by_app_renderers': _c['app_renderers'],
        'read_by_doc_renderers': _c['doc_renderers'],
        'read_by_builders': _c['builders'],
        'read_by_suites': _c['suites'],
        'read_by_its_own_pack': _c['own_pack'],
        'drops_off_when': 'a page generator under web/ opens this path, or '
                          'the pack removes its own honesty.not_built_yet - '
                          'either one, on the next build of rnd/, with no '
                          'edit here',
    })

# The backlog must not be empty and must not be everything: either would
# mean the signal is measuring the scan rather than the bundle.
if not DECLARED_UNBUILT:
    raise AssertionError('rnd: the backlog computed empty, which would mean '
                         'the consumer scan is not finding reads')
if len(DECLARED_UNBUILT) == len(REGISTRIES):
    raise AssertionError('rnd: every registry computed as unbuilt, which '
                         'means the consumer scan is finding nothing at all')

# ================================================================== GAPS ===
# Coverage gaps stated by the packs themselves, with BOTH halves computed
# live from the registry that owns them. A gap is not a sentence; it is a
# numerator, a denominator and the paths they came from.
GAPS = []


def gap(gid, question, n, d, unit, sources, how, note):
    """One gap. `n` and `d` are always computed above this call, never
    typed, and `sources` names every file they were computed from so a
    reader can go and disagree with the arithmetic."""
    if not isinstance(n, int) or not isinstance(d, int):
        raise TypeError(f'rnd: {gid}: a gap counts things, in whole numbers')
    if n > d:
        raise ValueError(f'rnd: {gid}: numerator {n} exceeds denominator {d}')
    for s in sources:
        text(s)          # a source that does not resolve stops the build
    if len(how) < 30 or len(note) < 30:
        raise ValueError(f'rnd: {gid}: say how it was computed and what it means')
    GAPS.append({'id': gid, 'question': question, 'have': n, 'of': d,
                 'unit': unit, 'share': share(n, d, gid),
                 'missing': d - n, 'sources': sorted(sources),
                 'how': how, 'note': note})


HALL_SLUGS = sorted(h['slug'] for h in need(reg(HALLS), 'halls', HALLS))
N_HALLS = len(HALL_SLUGS)
FIN_HALLS = need(reg(FINISHES), 'halls', FINISHES)
ROOM_RECORDS = [(s, r) for s, rec in FIN_HALLS.items()
                for r in need(rec, 'conditions', f'{FINISHES}#halls.{s}')]
N_ROOMS = len(ROOM_RECORDS)

gap('lessons.halls',
    'how many of the halls have a walkable lesson standing in them',
    len(set(need(need(reg(LESSONS), 'spread', LESSONS), 'halls', f'{LESSONS}#spread'))),
    N_HALLS, 'halls', [LESSONS, HALLS],
    'the distinct halls named in lessons/registry/lessons.json#spread.halls, '
    'over the hall roster in pack/registry/halls.json',
    'lessons/ declares this thinness itself and caps how much of the set any '
    'one hall may hold; the spread is deliberate, the size of it is the gap')

gap('lessons.strands',
    'how many of the skill strands a lesson stands in',
    len(set(need(need(reg(LESSONS), 'spread', LESSONS), 'strands', f'{LESSONS}#spread'))),
    len(need(reg(FINISHES), 'function_defaults', FINISHES)), 'strands',
    [LESSONS, FINISHES],
    'the distinct strands in lessons/registry/lessons.json#spread.strands, '
    'over the room strands surfaces/registry/finishes.json gives every hall',
    'a CLOSED gap, kept here on purpose: a register that showed only the open '
    'ones would be a way of hiding which closures were ever real')

for _gid, _q, _used, _total, _unit, _note in (
    ('lessons.stations', 'how many recovered stations a lesson uses',
     'stations_used', 'stations_total', 'stations',
     'a station nothing walks to is a station only its own suite has seen'),
    ('lessons.sims', 'how many simulator seats a lesson sits a learner in',
     'sims_used', 'sims_total', 'seats',
     'the unused seat is the overhead crane, the newest of the eleven'),
    ('lessons.scenarios', 'how many simulator scenarios a lesson reaches',
     'scenarios_used', 'scenarios_total', 'scenarios',
     'the widest gap in the lesson pack: the scenarios exist, are scored and '
     'are reachable by hand, but no lesson walks to most of them'),
    ('lessons.walkaround_points',
     'how many walkaround check points a lesson asks for',
     'walkaround_points_used', 'walkaround_points_total', 'points',
     'the walkaround is a habit-builder rather than a gate, and two thirds of '
     'the habit is currently unpractised by any lesson'),
):
    gap(_gid, _q,
        need(need(reg(LESSONS), 'counts', LESSONS), _used, f'{LESSONS}#counts'),
        need(need(reg(LESSONS), 'counts', LESSONS), _total, f'{LESSONS}#counts'),
        _unit, [LESSONS],
        f'lessons/registry/lessons.json#counts.{_used} over #counts.{_total}, '
        'both computed by that pack from the registries it reads',
        _note)

gap('sims.halls', 'how many halls bind at least one simulator seat',
    len(need(reg(SIMS), 'hall_bindings', SIMS)), N_HALLS, 'halls',
    [SIMS, HALLS],
    'the keys of sims/registry/sims.json#hall_bindings, over the hall roster '
    'in pack/registry/halls.json',
    'a seat is bound to a hall by a real skill id, so this is the share of '
    'the trades that can practise on a machine at all')

gap('schools.halls', 'how many halls have a flipped-classroom unit',
    len({need(u, 'hall', f'{SCHOOLS}#units') for u in need(reg(SCHOOLS), 'units', SCHOOLS)}),
    N_HALLS, 'halls', [SCHOOLS, HALLS],
    'the distinct hall slugs in schools/registry/schools.json#units, over the '
    'hall roster in pack/registry/halls.json',
    'the flipped model is declared for four proposed districts, not for the '
    'network, and the number says which')

_PPE_ROOMS = sum(1 for _s, _r in ROOM_RECORDS
                 if need(need(FIN_HALLS[_s], 'conditions', FINISHES)[_r],
                         'ppe', f'{FINISHES}#halls.{_s}.conditions.{_r}'))
gap('surfaces.ppe_rooms', 'how many rooms require protective equipment',
    _PPE_ROOMS, N_ROOMS, 'rooms', [FINISHES],
    'every room condition record in surfaces/registry/finishes.json#halls '
    'whose own `ppe` list is non-empty, counted here rather than read from '
    'the number props/ published',
    'props/ fails its own build if one of these rooms gets no PPE prop - but '
    'no prop is standing in any room yet, so today the requirement is '
    'declared against nothing')

_HAZARD_HALLS = sum(1 for _s in FIN_HALLS
                    if need(FIN_HALLS[_s], 'hazard', f'{FINISHES}#halls.{_s}') is not None)
gap('surfaces.hazard_halls',
    'how many halls carry a finish-driving hazard in their practice bay',
    _HAZARD_HALLS, len(FIN_HALLS), 'halls', [FINISHES],
    'halls in surfaces/registry/finishes.json#halls whose own `hazard` field '
    'is not null, counted here',
    'the remainder are bench, design and coordination trades; the spec claims '
    'a different number for them, which is recorded as a cross-check below')

gap('pack.signed_off_halls',
    'how many halls carry a named practitioner sign-off on their content',
    sum(1 for h in need(reg(HALLS), 'halls', HALLS)
        if 'content_status' in h
        and h['content_status'] == one('pack/hall_signoff.mjs',
                                       r"return status === '([a-z -]+)';",
                                       'the one status that claims a sign-off')),
    N_HALLS, 'halls', [HALLS, 'pack/hall_signoff.mjs'],
    'hall records in pack/registry/halls.json whose `content_status` equals '
    'the one claiming status pack/hall_signoff.mjs declares, over the roster',
    'the mechanism exists, is closed-set and refuses an unnamed reviewer; no '
    'hall has used it. Every lesson, rubric, walkaround point and advisor '
    'line in this bundle is unverified general practice, and this is the '
    'number that says so')

_LOCALES = sorted(p.name for p in (ROOT / 'i18n/locales').glob('*.json'))
_REVIEWED = [l for l in _LOCALES
             if 'reviewed' in need(reg(f'i18n/locales/{l}'), 'translation_status',
                                   f'i18n/locales/{l}')]
gap('i18n.reviewed_locales',
    'how many shipped locales have been reviewed by a native speaker',
    len(_REVIEWED), len(_LOCALES), 'locales',
    [f'i18n/locales/{l}' for l in _LOCALES],
    'each catalog\'s own `translation_status` field, counted here; a catalog '
    'claiming review must name its reviewer and a date or i18n/ refuses it',
    'seven of the eight are machine-drafted and say so; the eighth is the '
    'source language. Nothing in this bundle has been read by a native '
    'speaker of any language but English')

_VIEWS_PAGE = sorted(set(re.findall(r"view = '([a-z]+)'", text(PAGE))))
gap('eval.views_scored',
    'how many of the views the page can show have ever been scored in a browser',
    len([v for v in EVAL_VIEWS if v in _VIEWS_PAGE]), len(_VIEWS_PAGE), 'views',
    [EVAL, PAGE],
    'the view ids in the BASE table of web/eval_scene.mjs that web/build_3d.py '
    'actually sets, over every view id that file sets',
    'the avatar locker, a running simulator and a restoration site have no '
    'measured cost at all: every budget in this bundle is an argument about '
    'three views out of six')

gap('eval.campuses_scored',
    'how many campuses the scene harness has ever driven to',
    len({one(EVAL, r"__tc3dDo\('view', 'campus:([a-z-]+)'\)",
             'the campus the harness drives to')}),
    len(need(reg(CAMPUSES), 'campuses', CAMPUSES)), 'campuses',
    [EVAL, CAMPUSES],
    'the campus slugs web/eval_scene.mjs navigates to, over the campus roster '
    'in unions/registry/campuses.json',
    'kit/ says this in its own words: the baseline its whole-campus arithmetic '
    'is added to is a measurement of one campus, and the other nine are '
    'unmeasured ground')

gap('restoration.walkable',
    'how many restoration sites a learner can walk into',
    sum(1 for s in need(reg(RESTORATION), 'sites', RESTORATION)
        if need(s, 'walkable', f'{RESTORATION}#sites')),
    len(need(reg(RESTORATION), 'sites', RESTORATION)), 'sites', [RESTORATION],
    'sites in restoration/registry/restoration.json whose own `walkable` flag '
    'is true, over every site',
    'this gap is CLOSED BY POLICY and should not be closed further: the two '
    'that are not walkable are an actively litigated Superfund site and a '
    'cleanup with unresolved radiological criteria, and each carries its own '
    'written reason')

_GEO_ANCHORS = [a for v in need(reg(GEO), 'anchors', GEO).values()
                for a in (v if isinstance(v, list) else [v])]
gap('geo.recorded_anchors',
    'how many map anchors are RECORDED from a cited source rather than typed '
    'from general knowledge',
    sum(1 for a in _GEO_ANCHORS
        if need(a, 'provenance', f'{GEO}#anchors') == 'RECORDED'),
    len(_GEO_ANCHORS), 'anchors', [GEO],
    'anchors in geo/registry/campuses_geo.json#anchors whose own `provenance` '
    'reads RECORDED, over every anchor',
    'the rest are AUTHORED, the weaker tier, and the pack labels each one; '
    'they are real named institutions but nothing here cross-checked them')

gap('spatial.posed',
    'how many spatial subjects carry a GeoPose',
    need(need(reg(GEOPOSE), 'counts', GEOPOSE), 'total', f'{GEOPOSE}#counts'),
    need(need(reg(GEOPOSE), 'counts', GEOPOSE), 'total', f'{GEOPOSE}#counts')
    + need(need(reg(GEOPOSE), 'counts', GEOPOSE), 'unposed', f'{GEOPOSE}#counts'),
    'subjects', [GEOPOSE],
    'spatial/registry/geopose.json#counts.total over that plus #counts.unposed',
    'the one unposed subject is a bay-wide program that pins no single '
    'coordinate, and the pack refuses to invent one for it')

if len({g['id'] for g in GAPS}) != len(GAPS):
    raise ValueError('rnd: two gaps share an id')

# =============================================================== BUDGETS ===
# Two currencies, three views. For each: what the browser measured, what
# the harness permits, what kit/ and props/ have already claimed against
# that view, and what is left. Every figure is read; the ceiling arithmetic
# is re-done here with the harness's own rounding and then cross-checked
# against the ceilings the two packs published, so a ceiling cannot come to
# mean two different things in two files.
CALL_HEADROOM = float(one(EVAL, r'const CALL_HEADROOM = ([\d.]+);', 'the draw-call headroom'))
TRI_HEADROOM = float(one(EVAL, r'const TRI_HEADROOM = ([\d.]+);', 'the triangle headroom'))
MESH_FLOOR = float(one(EVAL, r'const MESH_FLOOR = ([\d.]+);', 'the visible-mesh floor'))

# Who claims against which view, read from each pack's own budget block.
# A pack is bound to a view here by the view IT names, never by this file's
# opinion of where its pieces stand.
KIT_VIEW = need(need(reg(KIT), 'budget', KIT), 'budgeted_campus', f'{KIT}#budget') and 'campus'
PROPS_VIEW = need(need(need(reg(PROPS), 'budget', PROPS), 'ceiling_source', f'{PROPS}#budget'),
                  'view', f'{PROPS}#budget.ceiling_source')
CLAIMS = {
    'campus': {'kit': {'draw_calls': dig(KIT, 'counts.campus_draw_calls'),
                       'triangles': dig(KIT, 'counts.campus_triangles'),
                       'allowance_draw_calls': dig(KIT, 'budget.draw_call_ceiling'),
                       'allowance_triangles': dig(KIT, 'budget.triangle_ceiling'),
                       'what': 'the exterior kit clothing 51 halls at the one '
                               'campus the harness drives to; a PREDICTION, '
                               'nothing is drawn yet'}},
    PROPS_VIEW: {'props': {'draw_calls': dig(PROPS, 'budget.delta.draw_calls'),
                           'triangles': dig(PROPS, 'budget.delta.triangles'),
                           'allowance_draw_calls': dig(PROPS, 'budget.self_imposed.calls_per_hall'),
                           'allowance_triangles': dig(PROPS, 'budget.self_imposed.tris_per_hall'),
                           'what': 'the worst hall standing its full set of '
                                   'props in eleven rooms; a PREDICTION, '
                                   'nothing is drawn yet'}},
}
if KIT_VIEW not in EVAL_VIEWS or PROPS_VIEW not in EVAL_VIEWS:
    raise LookupError('rnd: a pack budgets against a view the harness never scored')

BUDGETS = {'currencies': {}, 'multipliers': {
    'call_headroom': CALL_HEADROOM, 'tri_headroom': TRI_HEADROOM,
    'mesh_floor': MESH_FLOOR,
    'source': EVAL,
    'why': 'the multipliers are read from the harness, so a change to its '
           'policy moves every ceiling below with it instead of leaving '
           'three stale copies behind'}}
for _cur, _col, _mult, _round in (('draw_calls', 'calls', CALL_HEADROOM, True),
                                  ('triangles', 'tris', TRI_HEADROOM, False)):
    _rows = {}
    for _v in sorted(EVAL_VIEWS):
        _base = EVAL_VIEWS[_v][_col]
        _ceiling = jsround(_base * _mult) if _round else int(_base * _mult)
        _headroom = _ceiling - _base
        _claims = CLAIMS[_v] if _v in CLAIMS else {}
        _claimed = sum(need(c, _cur, f'a claim on {_v}') for c in _claims.values())
        _rows[_v] = {
            'measured_baseline': _base,
            'ceiling': _ceiling,
            'headroom': _headroom,
            'claimed_by': {p: need(c, _cur, f'a claim on {_v}')
                           for p, c in _claims.items()},
            'allowance_by': {p: need(c, f'allowance_{_cur}', f'a claim on {_v}')
                             for p, c in _claims.items()},
            'claimed_total': _claimed,
            'left': _headroom - _claimed,
            'left_share': share(_headroom - _claimed, _headroom, f'{_v}.{_cur}'),
            'claims': {p: need(c, 'what', f'a claim on {_v}') for p, c in _claims.items()},
        }
        if _rows[_v]['left'] < 0:
            raise AssertionError(
                f'rnd: {_v}: the packs have already claimed more {_cur} than '
                f'the harness leaves ({_claimed} of {_headroom})')
    BUDGETS['currencies'][_cur] = {
        'unit': _cur.replace('_', ' '),
        'views': _rows,
        'headroom_multiplier': _mult,
        # Which currency is scarce is NOT a judgement made here. It is the
        # one the harness gives the smaller multiplier, which is the same as
        # saying the one whose measured baseline already eats the larger
        # share of its own ceiling - and that share is published per view so
        # the claim can be checked rather than believed.
        'baseline_share_of_ceiling': {
            v: share(_rows[v]['measured_baseline'], _rows[v]['ceiling'],
                     f'{v}.{_cur}.spent')
            for v in _rows},
    }

_MULTS = {c: b['headroom_multiplier'] for c, b in BUDGETS['currencies'].items()}
for _cur, _blk in BUDGETS['currencies'].items():
    _blk['scarce'] = _MULTS[_cur] == min(_MULTS.values())
    _blk['scarce_why'] = (
        f'web/eval_scene.mjs permits {_MULTS[_cur]}x the measured baseline in '
        f'this currency against {max(_MULTS.values())}x in the other, so a '
        f'view already stands at '
        f'{max(_blk["baseline_share_of_ceiling"].values()):.0%} of its own '
        f'ceiling here before anything is added')
if sum(1 for b in BUDGETS['currencies'].values() if b['scarce']) != 1:
    raise AssertionError('rnd: exactly one currency is the scarce one, or the '
                         'harness has stopped distinguishing them')

# The cross-checks that make the arithmetic above worth anything: the two
# packs each published a ceiling of their own, and those must be the same
# numbers this file just recomputed from the harness. If they are not, one
# of the three files is stale and the build says which pair disagrees.
_CAMPUS_CALLS = BUDGETS['currencies']['draw_calls']['views'][KIT_VIEW]
_CAMPUS_TRIS = BUDGETS['currencies']['triangles']['views'][KIT_VIEW]
_HALL_CALLS = BUDGETS['currencies']['draw_calls']['views'][PROPS_VIEW]
_HALL_TRIS = BUDGETS['currencies']['triangles']['views'][PROPS_VIEW]
BUDGET_AGREEMENTS = []
for _label, _mine, _theirs, _rel, _path in (
    ('the campus draw-call headroom', _CAMPUS_CALLS['headroom'],
     dig(KIT, 'budget.draw_call_ceiling'), KIT, 'budget.draw_call_ceiling'),
    ('the campus triangle headroom', _CAMPUS_TRIS['headroom'],
     dig(KIT, 'budget.triangle_headroom_total'), KIT, 'budget.triangle_headroom_total'),
    ('the hall draw-call ceiling', _HALL_CALLS['ceiling'],
     dig(PROPS, 'budget.ceiling_source.max_calls'), PROPS, 'budget.ceiling_source.max_calls'),
    ('the hall triangle ceiling', _HALL_TRIS['ceiling'],
     dig(PROPS, 'budget.ceiling_source.max_tris'), PROPS, 'budget.ceiling_source.max_tris'),
    ('the hall draw-call headroom', _HALL_CALLS['headroom'],
     dig(PROPS, 'budget.ceiling_source.headroom_calls'), PROPS, 'budget.ceiling_source.headroom_calls'),
    ('the hall triangle headroom left after props',
     _HALL_TRIS['left'], dig(PROPS, 'budget.delta.triangles_headroom'),
     PROPS, 'budget.delta.triangles_headroom'),
    ('the hall draw-call headroom left after props',
     _HALL_CALLS['left'], dig(PROPS, 'budget.delta.draw_calls_headroom'),
     PROPS, 'budget.delta.draw_calls_headroom'),
):
    if _mine != _theirs:
        raise AssertionError(
            f'rnd: {_label}: recomputed from {EVAL} it is {_mine}, but '
            f'{_rel}#{_path} publishes {_theirs}. One of them is stale.')
    BUDGET_AGREEMENTS.append({'figure': _label, 'value': _mine,
                              'recomputed_from': EVAL,
                              'agrees_with': f'{_rel}#{_path}'})

# ================================================================ SUITES ===
# Where the assurance actually is. The suite list is parsed out of
# verify_all.sh's own loop and the counts out of README.md's own table, so
# this block is a join of two files neither of which this pack may edit.
_LOOP = re.search(r'for t in (.*?); do', text(VERIFY), re.S)
if not _LOOP:
    raise LookupError('rnd: verify_all.sh no longer runs its suites from one loop')
SUITE_LIST = re.sub(r'\\\s*\n', ' ', _LOOP.group(1)).split()
if len(SUITE_LIST) != len(set(SUITE_LIST)):
    raise ValueError('rnd: verify_all.sh names a suite twice')

SUITE_ROWS = []
for _t in SUITE_LIST:
    if not (ROOT / _t).is_file():
        raise FileNotFoundError(f'rnd: verify_all.sh runs {_t}, which is gone')
    _m = re.search(r'^node ' + re.escape(_t) + r' +# *(\d+)? ', text(README), re.M)
    SUITE_ROWS.append({
        'suite': _t,
        'pack': _t.split('/')[0],
        'readme_checks': int(_m.group(1)) if (_m and _m.group(1)) else None,
        'declared': bool(_m and _m.group(1)),
        'in_readme_table': bool(_m),
    })
_DECLARED = [r for r in SUITE_ROWS if r['declared']]
_COUNTS = sorted(r['readme_checks'] for r in _DECLARED)
_HEADLINE = int(num(one(README, r'\n\*\*([\d,]+) checks, all passing',
                        'the README headline check count')))
_SUM = sum(_COUNTS)
SUITES = {
    'source_of_the_list': VERIFY,
    'source_of_the_counts': README,
    'rows': SUITE_ROWS,
    'suites_run': len(SUITE_ROWS),
    'suites_declaring_a_count': len(_DECLARED),
    'suites_without_a_count': [r['suite'] for r in SUITE_ROWS if not r['declared']],
    'declared_total': _SUM,
    'readme_headline': _HEADLINE,
    'unaccounted_for': _HEADLINE - _SUM,
    'unaccounted_note': 'the headline counts every `  ok ` line verify_all.sh '
                        'sees, which includes suites the README table gives no '
                        'number to and web/test_interiors.py, which the table '
                        'does not list at all. The difference is that remainder '
                        'and is computed, not reconciled by hand.',
    'min': _COUNTS[0],
    'max': _COUNTS[-1],
    'median': _COUNTS[len(_COUNTS) // 2] if len(_COUNTS) % 2
              else (_COUNTS[len(_COUNTS) // 2 - 1] + _COUNTS[len(_COUNTS) // 2]) / 2,
    'thinnest': [{'suite': r['suite'], 'checks': r['readme_checks']}
                 for r in sorted(_DECLARED, key=lambda r: r['readme_checks'])[:6]],
    'thickest': [{'suite': r['suite'], 'checks': r['readme_checks']}
                 for r in sorted(_DECLARED, key=lambda r: -r['readme_checks'])[:6]],
    'note': 'a thin suite is not automatically a bad one - tools/ has 13 '
            'checks over a registry of twelve hand tools - but a thin suite '
            'over a large surface is where an unfound defect is most likely '
            'to be sitting, and this table is the only place the two are '
            'shown side by side.',
}

# ======================================================= OPEN_QUESTIONS ===
# What this bundle records as unanswered - and in particular the NEGATIVE
# findings, which are the most valuable entries here and are currently
# buried in spec prose and source comments where nothing points at them.
#
# A negative finding is a measurement that did not show what was hoped. It
# is worth more than a positive one because nobody writes it down unless
# they are being honest, and because it is the only kind of result that
# tells a later reader which road is already closed.
#
# Every entry is QUOTED, never paraphrased: the builder locates two anchors
# in the source file and publishes the slice between them. A paraphrase
# would be a second copy of the finding, free to drift from the first; a
# slice cannot drift, and the suite proves it is still verbatim.
OPEN_QUESTIONS = []


def question(qid, kind, asks, rel, start, end, why_it_matters):
    if kind not in ('negative-finding', 'unproved', 'unresolved-policy'):
        raise ValueError(f'rnd: {qid}: {kind!r} is not a kind of open question')
    if len(asks) < 25 or len(why_it_matters) < 40:
        raise ValueError(f'rnd: {qid}: say what is open and why it matters')
    OPEN_QUESTIONS.append({
        'id': qid, 'kind': kind, 'asks': asks, 'file': rel,
        'anchors': {'from': start, 'to': end},
        'quote': quote(rel, start, end),
        'why_it_matters': why_it_matters,
    })


question(
    'working-set.measured-optimum-is-not-the-shipped-default',
    'negative-finding',
    'the parameter sweep run to support interleaving measured its optimum at '
    'one or two open skills; the shipped default is three. Which is right?',
    SPEC, 'The measured optimum is',
    'hedges against a known model deficiency rather than over-fitting to it.',
    'this is the sharpest recorded negative in the bundle: an experiment that '
    'contradicted the policy it was run to support, kept, labelled '
    'uncomfortable, and answered by declining to over-fit to an '
    'under-specified model. The honest reading is written down, and the '
    'question is explicitly left for real telemetry to settle.')

question(
    'sequencing.blocked-practice-acquires-more',
    'negative-finding',
    'the traditional curriculum this bundle argues against acquired 2.4x more '
    'raw ability than the graph sequencer. Is durable ability the right thing '
    'to optimise?',
    SPEC, '**Massed practice acquires more and keeps less.**',
    'a certificate should mean the holder can still do it next month.',
    'the comparison was not reported as a clean win, and the number that lost '
    'is printed next to the number that won. A pack summarising this bundle '
    'without that line would be flattering it.')

question(
    'review.same-mind-same-day',
    'negative-finding',
    'simulation, soak and fuzz all probe the paths the author thought of. '
    'What class of defect can no harness in this bundle catch?',
    SPEC, 'Every defect in §23.1 and §23.3 shares one property',
    'the branch nobody had exercised.',
    'it is the standing argument against reading this bundle\'s own check '
    'count as a measure of its correctness - which is exactly what the '
    '`suites` block above could otherwise be mistaken for.')

question(
    'livery.hue-cannot-carry-identity',
    'negative-finding',
    'hashing 111 hall slugs into hue produced 94 distinct colours with '
    'three-way ties, and the first fix collapsed to 21. What channel carries '
    'identity?',
    SPEC, 'Over the real roster it produced', 'identical to a reader.',
    'a measurement that killed the design it was run to validate, including '
    'the tempting fix - 111 hues three degrees apart would have been distinct '
    'to a Set and identical to a reader, which is a defect a test cannot see.')

question(
    'mentor.gate-5-is-the-only-one-that-catches-over-helping',
    'negative-finding',
    'an over-helping mentor passes the scope, knowledge and persona gates '
    'cleanly. What does that say about gates that look at the turn rather '
    'than the outcome?',
    SPEC, '*Gate 5 earns its place.*', 'against the −0.03 threshold.',
    'the failure mode named here is the one users never report, because it '
    'feels generous - so the only instrument that finds it is a cohort '
    'outcome measured after the fact.')

question(
    'hazard.a-reason-that-did-no-work',
    'negative-finding',
    'a hazard-driven finish turned out identical to the function default it '
    'was supposed to override. How many recorded reasons change nothing?',
    SPEC, '**A hazard is only recorded as hazard-driven when it changed '
          'something.**', 'which is what actually happened.',
    'a provenance field that records a cause which changed no outcome is '
    'worse than an empty one, because it reports a decision that was never '
    'made. The same trap is open to every `why` field in every registry '
    'this pack reads.')

question(
    'constants.a-guessed-one-passes-its-own-assertion',
    'negative-finding',
    'an assertion built on a guessed character width sat passing while four '
    'hall names ran out of their pads. Which other constants in this bundle '
    'are guesses?',
    'web/build_map.py', 'PX_PER_CHAR is MEASURED, not estimated.',
    'it reports confidence it has not earned.',
    'the guess was 43 per cent low and the check never fired. This is the '
    'reason `measured` above distinguishes a measurement from a choice at '
    'all, and the reason every entry in it carries the file it was read from.')

question(
    'ceilings.a-limit-that-cannot-fire-is-not-a-limit',
    'negative-finding',
    'the first draft of the scene harness permitted 400 draw calls on a view '
    'costing 249 and 900,000 triangles on one costing 4,508. What else in '
    'this bundle is held to a limit that cannot fire?',
    EVAL, 'A ceiling loose enough never to fire is not a', 'without a word.',
    'every budget in the `budgets` block above descends from this correction; '
    'without it the whole arithmetic would be decoration.')

question(
    'audio.a-prompt-measured-worse-than-none',
    'negative-finding',
    'setting an audio prompt from the scene description was measured to make '
    'the audio worse than leaving it unset. Which other helpful-looking knobs '
    'hurt?',
    'orbis/runner-visko-orbis-stable/skill/SKILL.md',
    "**Don't set `set_audio_prompt` from a scene description.**", 'says why.',
    'the finding was acted on by REMOVING a control from the panel, which is '
    'the rarest response to a negative result and the one that leaves no '
    'trace unless it is written down.')

question(
    'roads.a-branch-that-cannot-change-the-answer',
    'unresolved-policy',
    'the roads are deliberately not sampled for footstep sound, and the '
    'reasoning has already had to be restated once. Does it survive the next '
    'campus?',
    PAGE, 'The ROADS are deliberately not sampled', 'this is the place.',
    'the conclusion held while the reason underneath it changed completely - '
    'which is the shape of a finding that is about to stop being true, and it '
    'is recorded in the file rather than in anybody\'s head.')

question(
    'xr.no-headset-has-ever-run-this',
    'unproved',
    'four hand gestures, 25 joints and every hysteresis band are declared and '
    'proved against a mocked WebXR session. Do they work on hardware?',
    GUIDE, 'UNVERIFIED-ON-HARDWARE', 'MOCKED WebXR session only.',
    'the largest unproved claim in the bundle, and the pack that makes it '
    'says so in its own status line rather than in a footnote. No amount of '
    'passing checks can close this one.')

question(
    'stars.too-bright-and-too-shallow',
    'unproved',
    'the drawn star field spans under two magnitudes where a real sky holding '
    'that many stars would reach nearly four. Is it a sky or a decoration?',
    SKY, 'the drawn field spans', 'No star here has a name, a position or a '
    'catalogue entry.',
    'sky/ computed the number that embarrasses its own star field and '
    'published it. That is the behaviour this pack exists to make visible.')

# ---------------------------------------------------------- cross-checks ---
# The same figure, recorded in two files. Computed here, not remembered.
# `agree` is the whole point: an entry whose halves match is a fact this
# bundle keeps consistently, and an entry whose halves differ is a defect
# nobody has noticed. Fixing one does not require editing this file - the
# next build simply computes `agree: true` and the count of disagreements
# falls by one.
CROSS_CHECKS = []


def cross(cid, what, a_rel, a_pat, b_rel, b_pat, consequence, cast=int):
    va = cast(num(one(a_rel, a_pat, f'{cid}: the first record')))
    vb = cast(num(one(b_rel, b_pat, f'{cid}: the second record')))
    CROSS_CHECKS.append({
        'id': cid, 'what': what, 'agree': va == vb,
        'a': {'file': a_rel, 'pattern': a_pat, 'value': va},
        'b': {'file': b_rel, 'pattern': b_pat, 'value': vb},
        'consequence': consequence,
    })


cross('luminance.after-the-candela-conversion',
      'the mean frame luminance a hall interior reached after the luminaires '
      'were converted to candela, recorded in the page generator and again in '
      'the suite that checks it',
      PAGE, r'46 to 96 in this file, 46 to (\d+) in the suite',
      'web/test_3d.mjs', r'46 to 96 in this file, 46 to (\d+) in the suite',
      'This began as two files asserting two different numbers for one '
      'frame - 96 and 89 - with nothing in the bundle able to say which was '
      'right, because the frame was gone. It was not repaired by picking a '
      'winner. Both files now carry the SAME sentence, which states the '
      'disagreement, and a check in web/test_3d.mjs holds them to it. What '
      'this cross-check compares is therefore no longer two measurements; '
      'it is two copies of one disclosure, and they agree. The underlying '
      'number is still unknown and the register still says so.')

def cross_computed(cid, what, a, b, consequence):
    """The same shape, where one or both halves are a COUNT rather than a
    number written in the file. Each half still names the file it came from
    and the sentence that says how it was counted."""
    for half in (a, b):
        text(need(half, 'file', cid))
        need(half, 'how', cid)
        need(half, 'value', cid)
    CROSS_CHECKS.append({'id': cid, 'what': what,
                         'agree': a['value'] == b['value'],
                         'a': a, 'b': b, 'consequence': consequence})


cross_computed(
    'hazard-free-halls',
    'how many halls have no finish-driving hazard: the figure the spec states '
    'in prose, against the figure the surface registry actually holds',
    {'file': SPEC,
     'how': 'the number written in section 24.2 of the spec, read by pattern',
     'value': int(one(SPEC,
                      r'After extending it from their own words, (\d+) halls remain',
                      'the spec\'s count of hazard-free halls'))},
    {'file': FINISHES,
     'how': 'halls in surfaces/registry/finishes.json#halls whose own `hazard` '
            'field is null, counted here',
     'value': len(FIN_HALLS) - _HAZARD_HALLS},
    'the spec\'s number is prose and the registry\'s is data; they disagree, '
    'and the phrase the spec says those halls "now say" appears nowhere in the '
    'registry at all. The registry is what the page renders, so the prose is '
    'the half that is stale.')

if len({c['id'] for c in CROSS_CHECKS}) != len(CROSS_CHECKS):
    raise ValueError('rnd: two cross-checks share an id')

# ========================================================= PAGE_CONTRACT ===
CONTRACT = (
    'this pack states no fact of its own. Every value in it is read out of '
    'another file at build time and carries the path and the locator it was '
    'read with, so a reader can resolve any entry back to its source and '
    'disagree with it there rather than here. Three questions are answered: '
    'what has been measured, what is declared and unbuilt, and where the '
    'known gaps are - plus the budgets those measurements govern, the suites '
    'that hold the assurance, and the questions this bundle records as open.'
)

HONESTY = {
    'status': 'DERIVED: nothing in this registry was authored as a fact about '
              'the bundle. Every number is read from a named file through a '
              'named locator, and the suite re-resolves every pointer against '
              'the live file rather than trusting the value stored here.',
    'not_a_measurement': 'this pack measures nothing. It reaches no network, '
                         'opens no browser and runs no harness. Where it says '
                         'MEASURED-IN-BROWSER, another file did the measuring '
                         'and this one is quoting its record of it.',
    'not_a_roadmap': 'declared_unbuilt is a computed backlog, not a plan and '
                     'not a commitment. Nothing here schedules anything, no '
                     'entry carries a date it is due, and roadmap/ owns the '
                     'campus network\'s own plan without this pack '
                     'duplicating a line of it.',
    'predictions_are_not_measurements': 'the whole-campus and whole-hall '
                                        'figures kit/ and props/ publish are '
                                        'PREDICTIONS of what their placement '
                                        'rules would cost. Both are drawn '
                                        'now and both publish a browser '
                                        'probe beside the prediction, so a '
                                        'reader can compare them - but this '
                                        'register still holds the PREDICTED '
                                        'figures, because that is what the '
                                        'packs publish. The budget block '
                                        'spends them against a measured '
                                        'baseline anyway, '
                                        'because that is the only way to know '
                                        'whether they fit - but a spent '
                                        'prediction is not a spent budget.',
    'three_views_of_six': 'every budget in this bundle is an argument about '
                          'three of the six views the page can show. The '
                          'avatar locker, a running simulator and a '
                          'restoration site have no measured cost at all.',
    'does_not_flatter': 'a gap is published with its numerator and its '
                        'denominator whether or not the share is comfortable, '
                        'a closed gap stays in the list so the closure can be '
                        'checked, and the thinnest suites are named beside '
                        'the thickest. A register that reported only good '
                        'news would have to be checked against the thing it '
                        'summarises, which is the work it exists to save.',
    'provenance_word': 'DERIVED, and that word is this pack\'s whole claim. '
                       'The generated-video provenance word this bundle '
                       'reserves for orbis/ is not used anywhere in this '
                       'pack and does not appear in this payload; the build '
                       'asserts its absence rather than promising it.',
    'the_backlog_computes': 'a pack that gets wired up drops off '
                            'declared_unbuilt on the next build of this file, '
                            'because the entry is computed from whether a '
                            'renderer names its registry path - not from a '
                            'note here saying it is unbuilt.',
}

PAGE_CONTRACT = {
    'data': 'D.rnd, one payload, read-only. Nothing on the page writes to it '
            'and nothing is stored in the browser: this is a register, not a '
            'workspace.',
    'route': 'a single R&D board, four panels wide, reachable from the front '
             'door rather than from inside a view - it describes the bundle, '
             'not a place in it',
    'measured': 'one row per entry, grouped by `tier`, with the value, the '
                'unit, the file and the locator rendered as literal text. The '
                'locator is the point: a reader who does not believe a number '
                'is given the exact path or pattern that produced it.',
    'declared_unbuilt': 'the backlog, one card per registry, each listing its '
                        'computed reasons and the files that do and do not '
                        'read it. A card carries no owner, no date and no '
                        'priority, because this pack has no standing to '
                        'assign any of the three.',
    'gaps': 'one bar per gap, drawn as have-of-total with the share printed '
            'as a number beside it. A bar is never drawn as a percentage '
            'alone: 24 per cent and 27-of-111 are different amounts of '
            'information and only the second can be argued with.',
    'budgets': 'two columns, one per currency, three rows of views. Each cell '
               'shows baseline, ceiling, claimed and left, and the claimed '
               'segment is labelled PREDICTED so it cannot be read as drawn.',
    'suites': 'the check table sorted ascending, so the thin end is at the '
              'top where a reader looking for where to add assurance will '
              'find it first',
    'open_questions': 'each quote rendered verbatim in a monospaced block '
                      'with its file and its two anchors beneath it, and the '
                      'negative findings first. Nothing here is summarised on '
                      'the page: a summary of a negative finding is how a '
                      'negative finding becomes a positive one.',
    'cross_checks': 'the disagreements rendered first with both values side '
                    'by side and both paths, and the agreements collapsed '
                    'beneath them',
    'episode': 'nothing is recorded. No score, no progress, no episode and no '
               'storage key: opening this board is not an interaction with '
               'the Academy, it is a reading of it.',
}

# ================================================================= build ===
stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

_by_tier = {t: sum(1 for m in MEASURED if m['tier'] == t) for t in TIERS}
_open_gaps = [g for g in GAPS if g['share'] < 1.0]

doc = {
    'pack': 'smartcitix-trade-craft-academy-rnd',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'contract': CONTRACT,
    'honesty': HONESTY,
    'counts': {
        'measured': len(MEASURED),
        'measured_in_browser': _by_tier['MEASURED-IN-BROWSER'],
        'measured_elsewhere': _by_tier['MEASURED-ELSEWHERE'],
        'computed_from_registry': _by_tier['COMPUTED-FROM-REGISTRY'],
        'measured_source_files': len({m['file'] for m in MEASURED}),
        'registries_scanned': len(REGISTRIES),
        'app_renderers_scanned': len(APP_RENDERERS),
        'doc_renderers_scanned': len(DOC_RENDERERS),
        'builders_scanned': len(BUILDERS),
        'suites_scanned': len(SUITE_FILES),
        'declared_unbuilt': len(DECLARED_UNBUILT),
        'declared_unbuilt_by_their_own_words': sum(
            1 for d in DECLARED_UNBUILT if d['says'] is not None),
        'declared_unbuilt_not_drawn': sum(
            1 for d in DECLARED_UNBUILT if not d['read_by_app_renderers']),
        'declared_unbuilt_documented_but_not_drawn': sum(
            1 for d in DECLARED_UNBUILT
            if d['read_by_doc_renderers'] and not d['read_by_app_renderers']),
        'declared_unbuilt_read_by_nothing': sum(
            1 for d in DECLARED_UNBUILT
            if not d['read_by_app_renderers'] and not d['read_by_doc_renderers']
            and not d['read_by_builders'] and not d['read_by_suites']),
        'gaps': len(GAPS),
        'gaps_open': len(_open_gaps),
        'gaps_closed': len(GAPS) - len(_open_gaps),
        'widest_gap_share': min(g['share'] for g in GAPS),
        'budget_views': len(EVAL_VIEWS),
        'budget_currencies': len(BUDGETS['currencies']),
        'budget_agreements': len(BUDGET_AGREEMENTS),
        'suites_run': SUITES['suites_run'],
        'suite_checks_declared': SUITES['declared_total'],
        'open_questions': len(OPEN_QUESTIONS),
        'negative_findings': sum(1 for q in OPEN_QUESTIONS
                                 if q['kind'] == 'negative-finding'),
        'cross_checks': len(CROSS_CHECKS),
        'cross_checks_disagreeing': sum(1 for c in CROSS_CHECKS if not c['agree']),
        'files_read': len(_TEXT),
    },
    'tiers': list(TIERS),
    'measured': MEASURED,
    'declared_unbuilt': DECLARED_UNBUILT,
    'consumers': CONSUMERS,
    'scanned': {'app_renderers': APP_RENDERERS,
                'doc_renderers': DOC_RENDERERS,
                'builders': BUILDERS, 'suites': SUITE_FILES,
                'why': 'an app renderer is a page generator under web/ and '
                       'what it reads is something a learner can stand in '
                       'front of; a doc renderer is the wiki or the console '
                       'and what it reads has been written ABOUT, which is '
                       'not the same as built; a builder is another pack\'s '
                       'build.py; and a suite reads a registry to check it, '
                       'which is not consumption at all. This pack excludes '
                       'itself from every one of the four, because it reads '
                       'every registry in the tree by definition.'},
    'gaps': GAPS,
    'budgets': BUDGETS,
    'budget_agreements': BUDGET_AGREEMENTS,
    'suites': SUITES,
    'open_questions': OPEN_QUESTIONS,
    'cross_checks': CROSS_CHECKS,
    'page_contract': PAGE_CONTRACT,
    'reads': sorted(_TEXT),
}

# ---------------------------------------------------------------- checks ---
# Each is a claim this pack makes about itself, turned into the assertion
# that would catch it becoming false.

payload = json.dumps(doc)

# -- no network, of any kind, anywhere in the payload. This pack reads the
# -- tree and nothing else, and a URL in a derived register would be a
# -- pointer nobody in this repository can resolve.
assert 'http://' not in payload and 'https://' not in payload, \
    'rnd names no URL: it reads files in this repository and nothing else'

# -- the provenance word. DERIVED is this pack's; AI-SYNTHESIZED is orbis's
# -- and describes generated video, which nothing here is.
assert HONESTY['status'].startswith('DERIVED:'), \
    'the rnd pack must carry the DERIVED provenance word'
assert 'AI-SYNTHESIZED' not in payload, \
    'AI-SYNTHESIZED belongs to orbis/ and nothing in this payload is that'

# -- every measured entry resolves. The values above were produced by these
# -- same locators, so this re-walk is a check on the LOCATOR being
# -- publishable and re-runnable rather than on the value - the suite then
# -- runs the identical walk from the other side, in another language.
for m in MEASURED:
    loc = m['locator']
    if loc['kind'] == 'json':
        got = dig(m['file'], loc['path'])
    else:
        raw = one(m['file'], loc['pattern'], f'{m["id"]}: its own locator')
        got = int(num(raw)) if loc['cast'] == 'int' else float(num(raw))
    assert got == m['value'], \
        f'{m["id"]}: the published value {m["value"]} is not what its own ' \
        f'locator resolves to ({got}) in {m["file"]}'

# -- every quote is still the file's own words
for q in OPEN_QUESTIONS:
    assert q['quote'] in flat(q['file']), \
        f'{q["id"]}: the quote is no longer verbatim in {q["file"]}'
    assert q['anchors']['from'] in q['quote'] and q['anchors']['to'] in q['quote'], \
        f'{q["id"]}: the quote does not span its own anchors'

# -- the backlog is computed, not listed. Every entry must carry at least
# -- one reason that was derived from a scan or from another pack's own
# -- words, and no entry may claim a renderer reads it while also claiming
# -- nothing does.
for d in DECLARED_UNBUILT:
    assert d['reasons'], f'{d["registry"]}: an entry with no computed reason'
    assert not (d['read_by_app_renderers']
                and any('no page generator' in r for r in d['reasons'])), \
        f'{d["registry"]}: the reasons contradict the scan'
    if d['says'] is not None:
        assert d['says'] == dig(d['registry'], 'honesty.not_built_yet'), \
            f'{d["registry"]}: the published sentence is not the registry\'s own'

# -- the gaps are arithmetic, and the counts over them agree with the list
assert doc['counts']['gaps_open'] + doc['counts']['gaps_closed'] == len(GAPS)
for g in GAPS:
    assert g['have'] + g['missing'] == g['of'], f'{g["id"]}: the halves do not sum'
    assert abs(g['share'] - round(g['have'] / g['of'], 4)) < 1e-9, \
        f'{g["id"]}: the share is not the quotient'

# -- the budget arithmetic closes in both directions
for cur, blk in BUDGETS['currencies'].items():
    for v, row in blk['views'].items():
        assert row['ceiling'] - row['measured_baseline'] == row['headroom'], \
            f'{v}/{cur}: the headroom is not the ceiling less the baseline'
        assert row['headroom'] - row['claimed_total'] == row['left'], \
            f'{v}/{cur}: what is left is not the headroom less what is claimed'
        assert sum(row['claimed_by'].values()) == row['claimed_total'], \
            f'{v}/{cur}: the claims do not sum to the total'
        for p, claimed in row['claimed_by'].items():
            assert claimed <= row['allowance_by'][p], \
                f'{v}/{cur}: {p} claims {claimed} against its own allowance ' \
                f'of {row["allowance_by"][p]}'

# -- this pack restates nothing: no entry may exist without the file it was
# -- read from, and every one of those files must be in `reads`
for entry, where in ([(m, m['file']) for m in MEASURED]
                     + [(q, q['file']) for q in OPEN_QUESTIONS]
                     + [(d, d['registry']) for d in DECLARED_UNBUILT]):
    assert where in doc['reads'], f'an entry cites {where}, which was never read'
for g in GAPS:
    for s in g['sources']:
        assert s in doc['reads'], f'{g["id"]} cites {s}, which was never read'

# -- and it reads WIDELY: a register of this bundle computed from three
# -- files would be a summary of three files
assert len(doc['reads']) >= 25, \
    f'rnd read only {len(doc["reads"])} files; that is not a register of this bundle'

# -- the counts are the things they count
assert doc['counts']['measured'] == len(MEASURED)
assert sum(_by_tier.values()) == len(MEASURED), 'a measured entry has no tier'
assert doc['counts']['negative_findings'] > 0, \
    'a register of this bundle with no negative finding in it has not looked'

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'rnd.json').write_text(json.dumps(doc, indent=1) + '\n')

c = doc['counts']
print(f"rnd: {c['measured']} measured facts "
      f"({c['measured_in_browser']} in a browser, {c['measured_elsewhere']} "
      f"elsewhere, {c['computed_from_registry']} computed from a registry) "
      f"over {c['measured_source_files']} files; "
      f"{c['declared_unbuilt']} of {c['registries_scanned']} registries "
      f"declared-and-unbuilt "
      f"({c['declared_unbuilt_documented_but_not_drawn']} documented but not drawn); "
      f"{c['gaps_open']} open gaps and {c['gaps_closed']} closed, widest "
      f"{c['widest_gap_share']:.3f}; {c['budget_agreements']} budget figures "
      f"cross-checked over {c['budget_views']} views; "
      f"{c['suite_checks_declared']} declared checks over {c['suites_run']} "
      f"suites; {c['open_questions']} open questions "
      f"({c['negative_findings']} of them negative findings), "
      f"{c['cross_checks_disagreeing']} of {c['cross_checks']} cross-checks "
      f"disagreeing; {c['files_read']} files read (source stamp {stamp})")
