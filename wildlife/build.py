#!/usr/bin/env python3
"""wildlife/ - the regional wildlife of the world maps, as play and as safe-viewing lessons (BAYOU, wave 12).

Writes wildlife/registry/wildlife.json. Everything here is AUTHORED:
- species are real regional species NAMED GENERALLY (no subspecies claims, no counts, no record sizes);
- each species' `fact` is one general line naming the KIND of source it comes from; no number is invented;
- sighting windows are an AUTHORED GAME CALENDAR ("approximate, game calendar"), never a survey or a season date;
- habitats say which AUTHORED map surface a sighting may spawn on (water | shore | land), never a surveyed range;
- the alligator season game is a licensed-tag harvest SIMULATION with no gore (a catch is a tag recorded, the animal
  is never shown harmed); in K-12 / classroom mode it becomes an alligator NEST SURVEY / photo game instead.
Real activity follows state rules - the pack says so and names the state wildlife agencies.
Fail closed: every field is required; a missing or malformed one stops the build with a named error.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'wildlife.json'

PACK_VERSION = json.loads((ROOT / 'pack' / 'manifest.json').read_text())['pack_version']
REGIONS = ('parishes', 'bay', 'wilds')
HABITATS = {
    'water': 'on AUTHORED open water (a lake, bayou, river or bay polygon the page draws)',
    'shore': 'on AUTHORED land within a short walk of AUTHORED water (bank, marsh edge, beach, levee)',
    'land': 'on AUTHORED walkable ground away from water (park, field, woodland, trail)',
}
TIMES = ('dawn', 'day', 'dusk', 'night')
GROUPS = ('reptile', 'bird', 'mammal', 'crustacean', 'insect', 'amphibian')
RARITY = {'common': 1, 'uncommon': 2, 'rare': 3}   # AUTHORED game weight (photo points), not an abundance claim
RULES_LINE = ('Real activity follows state rules - check the state wildlife agency (Louisiana Department of Wildlife '
              'and Fisheries; California Department of Fish and Wildlife).')
PLAY_LINE = ('Sightings, photos, tags and badges here are play: kept on this device only, never a completion record, '
             'never money, never a permit or a licence.')
CALENDAR_LABEL = 'approximate, game calendar'

SAFE_VIEWING = [
    ('distance', 'Watch from a distance - use a zoom lens or binoculars instead of walking closer.'),
    ('never-feed', 'Never feed wildlife: fed animals lose their fear of people and that puts them and you at risk.'),
    ('never-harass', 'Never chase, corner, touch or harass an animal; if it changes what it is doing, you are too close.'),
    ('alligators', 'Alligators are dangerous: stay well back from the water\'s edge where they live and never approach one.'),
    ('nests', 'Leave nests, eggs and young alone - a parent is usually nearby even when you cannot see it.'),
    ('pets', 'Keep pets leashed and away from wildlife and the water\'s edge.'),
    ('trails', 'Stay on trails and boardwalks so plants and nesting ground are not trampled.'),
    ('report', 'Report injured or stranded wildlife to the state wildlife agency or a licensed rehabilitator; do not handle it.'),
]
SAFE_IDS = [s[0] for s in SAFE_VIEWING]

# (id, general name, group, regions, habitat, months, times, rarity, colour, safe_m, photo_m, danger, fact, safety)
# safe_m / photo_m are AUTHORED GAME distances in world metres (the photo game refuses a shot closer than safe_m),
# not real-world viewing distances.
S = [
 ('american-alligator', 'American alligator', 'reptile', ['parishes'], 'shore', [3, 4, 5, 6, 7, 8, 9, 10],
  ['day', 'dusk', 'night'], 'common', '#4f6b3a', 40, 120, True,
  'Once listed as endangered in the United States, the alligator recovered under protection and is now managed by state wildlife agencies (state wildlife agency).',
  'Dangerous: never approach, feed or tease an alligator - feeding wild alligators is against state law in Louisiana.'),
 ('brown-pelican', 'Brown pelican', 'bird', ['parishes', 'bay'], 'water', list(range(1, 13)),
  ['dawn', 'day'], 'common', '#8a6f4d', 25, 110, False,
  'Brown pelicans plunge-dive from the air to catch fish; the brown pelican is Louisiana\'s state bird (state wildlife agency).',
  'Never feed pelicans or leave fishing line behind - line and hooks tangle birds.'),
 ('roseate-spoonbill', 'Roseate spoonbill', 'bird', ['parishes'], 'shore', [3, 4, 5, 6, 7, 8, 9, 10],
  ['dawn', 'day'], 'rare', '#e58fa6', 30, 110, False,
  'A spoonbill sweeps its flat bill side to side in shallow water; its pink colour comes from pigments in the food it eats (bird conservation groups).',
  'Give wading birds room: if a bird stops feeding to watch you, back away.'),
 ('great-egret', 'Great egret', 'bird', ['parishes', 'bay'], 'shore', list(range(1, 13)),
  ['dawn', 'day', 'dusk'], 'common', '#f2f2ee', 25, 110, False,
  'Great egrets were once hunted for their plumes for hats; protection laws helped them recover (bird conservation groups).',
  'Keep back from rookeries - nesting colonies abandon nests when disturbed.'),
 ('great-blue-heron', 'Great blue heron', 'bird', ['parishes', 'bay', 'wilds'], 'shore', list(range(1, 13)),
  ['dawn', 'day', 'dusk'], 'common', '#6f8aa3', 25, 110, False,
  'The great blue heron stands still in the shallows and strikes fish with its bill; it is the largest heron in North America (bird field guides).',
  'Herons flush easily: move slowly, stay low and keep your distance.'),
 ('white-ibis', 'White ibis', 'bird', ['parishes'], 'shore', list(range(1, 13)),
  ['day'], 'common', '#f4f1ea', 20, 100, False,
  'A white ibis probes mud with its long curved bill for crawfish and insects (bird field guides).',
  'Never feed ibises in parks - human food harms wild birds.'),
 ('osprey', 'Osprey', 'bird', ['parishes', 'bay', 'wilds'], 'water', [3, 4, 5, 6, 7, 8, 9, 10],
  ['day'], 'uncommon', '#7a6a58', 40, 160, False,
  'Ospreys dive feet-first to catch fish and carry them head-forward in flight (bird field guides).',
  'Never climb toward a nest platform; watch from far below.'),
 ('nutria', 'Nutria', 'mammal', ['parishes'], 'shore', list(range(1, 13)),
  ['dusk', 'night'], 'common', '#6b4f36', 20, 90, False,
  'Nutria are South American rodents brought to Louisiana; their feeding strips marsh plants and adds to coastal wetland loss (state wildlife agency).',
  'Nutria can bite: never corner or hand-feed one.'),
 ('river-otter', 'North American river otter', 'mammal', ['parishes', 'bay', 'wilds'], 'water', list(range(1, 13)),
  ['dawn', 'dusk'], 'rare', '#5a4432', 30, 110, False,
  'River otters hunt fish and crawfish and den in banks near water (state wildlife agency).',
  'Otters are wild predators: watch quietly from the bank and never approach a den.'),
 ('red-eared-slider', 'Red-eared slider', 'reptile', ['parishes', 'bay'], 'shore', [3, 4, 5, 6, 7, 8, 9, 10],
  ['day'], 'common', '#5d7a3a', 10, 70, False,
  'Sliders bask on logs to warm up; released pet sliders compete with native turtles in many places, including California (state wildlife agency).',
  'Never release a pet turtle into the wild, and never take a wild turtle home.'),
 ('bald-eagle', 'Bald eagle', 'bird', ['parishes', 'bay', 'wilds'], 'water', [1, 2, 3, 10, 11, 12],
  ['day'], 'rare', '#3b2f25', 60, 200, False,
  'Bald eagles recovered after the pesticide DDT was banned in the United States; they are protected by federal law (federal wildlife agency).',
  'Nesting eagles are protected: never approach a nest tree.'),
 ('monarch-butterfly', 'Monarch butterfly', 'insect', ['parishes', 'bay'], 'land', [3, 4, 9, 10, 11, 12, 1, 2],
  ['day'], 'uncommon', '#e07b1f', 3, 30, False,
  'Monarch caterpillars eat only milkweed; western monarchs gather to overwinter in groves on the California coast (conservation groups).',
  'Never shake or touch clustered monarchs - it wastes the energy they need to survive winter.'),
 ('green-anole', 'Green anole', 'reptile', ['parishes'], 'land', [3, 4, 5, 6, 7, 8, 9, 10],
  ['day'], 'common', '#4c9a3a', 3, 30, False,
  'Green anoles change colour from green to brown with temperature and mood (state wildlife agency).',
  'Look, do not catch: grabbing a lizard can hurt it.'),
 ('white-tailed-deer', 'White-tailed deer', 'mammal', ['parishes', 'wilds'], 'land', list(range(1, 13)),
  ['dawn', 'dusk'], 'uncommon', '#9b7650', 40, 140, False,
  'A white-tailed deer raises its white tail like a flag as an alarm when it runs (state wildlife agency).',
  'Never approach a fawn lying alone - its mother leaves it hidden on purpose.'),
 ('california-sea-lion', 'California sea lion', 'mammal', ['bay'], 'water', list(range(1, 13)),
  ['day'], 'common', '#6a5238', 40, 140, False,
  'Sea lions bark loudly and can walk on land by turning their rear flippers forward; marine mammals are protected by federal law (NOAA Fisheries).',
  'Stay back from hauled-out sea lions and never touch or feed them - they can bite.'),
 ('harbor-seal', 'Harbor seal', 'mammal', ['bay'], 'shore', list(range(1, 13)),
  ['dawn', 'day'], 'uncommon', '#8c8a80', 40, 140, False,
  'Harbor seals cannot turn their rear flippers forward, so they wriggle on land; they rest hauled out on rocks and beaches (NOAA Fisheries).',
  'A seal pup alone on a beach is usually waiting for its mother: stay back and report it, never move it.'),
 ('dungeness-crab', 'Dungeness crab', 'crustacean', ['bay'], 'shore', list(range(1, 13)),
  ['dawn', 'night'], 'uncommon', '#b0553a', 3, 25, False,
  'The Dungeness crab is named after a place on the Washington coast and lives on sandy bottoms along the Pacific coast (state wildlife agency).',
  'Look in tide pools without lifting rocks away; put anything you turn over back gently.'),
 ('western-gull', 'Western gull', 'bird', ['bay'], 'shore', list(range(1, 13)),
  ['dawn', 'day', 'dusk'], 'common', '#d9dcdf', 10, 80, False,
  'Western gulls nest on islands in the Bay and along the Pacific coast (bird field guides).',
  'Never feed gulls - it teaches them to take food from people.'),
 ('black-crowned-night-heron', 'Black-crowned night heron', 'bird', ['parishes', 'bay'], 'shore', list(range(1, 13)),
  ['dusk', 'night'], 'uncommon', '#4a5560', 25, 100, False,
  'Night herons roost in trees by day and hunt at dusk and after dark (bird field guides).',
  'Keep lights low and voices quiet near roosts.'),
 ('american-avocet', 'American avocet', 'bird', ['bay'], 'shore', [3, 4, 5, 6, 7, 8, 9, 10],
  ['day'], 'uncommon', '#c98a5a', 25, 100, False,
  'Avocets sweep their upturned bills side to side through shallow water; they feed in salt ponds and mudflats (bird field guides).',
  'Shorebirds need their feeding time: stay off mudflats and give flocks space.'),
 ('california-quail', 'California quail', 'bird', ['bay'], 'land', list(range(1, 13)),
  ['dawn', 'dusk'], 'uncommon', '#6b6c7c', 15, 80, False,
  'The California quail, with its forward-curling head plume, is California\'s state bird (state wildlife agency).',
  'Keep cats indoors and dogs leashed where quail forage on the ground.'),
 ('western-pond-turtle', 'Western pond turtle', 'reptile', ['bay'], 'shore', [3, 4, 5, 6, 7, 8, 9, 10],
  ['day'], 'rare', '#5a5a3a', 10, 70, False,
  'Pond turtles are native freshwater turtles of California and a species of conservation concern (state wildlife agency).',
  'Never take a wild turtle home or release a pet turtle into a pond.'),
 ('coyote', 'Coyote', 'mammal', ['bay', 'wilds'], 'land', list(range(1, 13)),
  ['dawn', 'dusk', 'night'], 'uncommon', '#a08560', 60, 180, False,
  'Coyotes live in many cities, including parks around the Bay; they are adaptable and wary of people unless fed (state wildlife agency).',
  'Never feed a coyote; if one approaches, stand tall, make noise and back away slowly.'),
 ('beaver', 'North American beaver', 'mammal', ['wilds'], 'water', list(range(1, 13)),
  ['dusk', 'night'], 'uncommon', '#5e4028', 25, 100, False,
  'Beavers build dams that turn streams into ponds and wetlands used by many other animals (state wildlife agency).',
  'Watch from the bank at dusk; never disturb a lodge or a dam.'),
 ('american-black-bear', 'American black bear', 'mammal', ['wilds'], 'land', [4, 5, 6, 7, 8, 9, 10, 11],
  ['dawn', 'day', 'dusk'], 'rare', '#2a2522', 90, 240, True,
  'Black bears eat mostly plants, berries and insects, and learn fast where people leave food (state wildlife agency).',
  'Dangerous: never approach or feed a bear; store food and trash where bears cannot reach it.'),
 ('mule-deer', 'Mule deer', 'mammal', ['wilds'], 'land', list(range(1, 13)),
  ['dawn', 'dusk'], 'common', '#8f7457', 40, 140, False,
  'Mule deer are named for their large, mule-like ears (state wildlife agency).',
  'Give deer space, especially in the autumn rut and near fawns.'),
 ('red-tailed-hawk', 'Red-tailed hawk', 'bird', ['bay', 'wilds', 'parishes'], 'land', list(range(1, 13)),
  ['day'], 'common', '#9a5a3a', 30, 160, False,
  'Red-tailed hawks often perch on poles beside open fields watching for rodents (bird field guides).',
  'Never approach a perched raptor or its nest.'),
 ('bighorn-sheep', 'Bighorn sheep', 'mammal', ['wilds'], 'land', list(range(1, 13)),
  ['day'], 'rare', '#a38b6a', 60, 200, False,
  'Bighorn rams clash horns to settle rank in the autumn rut; their split hooves grip steep rock (state wildlife agency).',
  'Never approach sheep on cliffs - a startled animal can fall or knock rocks loose.'),
 ('american-pika', 'American pika', 'mammal', ['wilds'], 'land', [5, 6, 7, 8, 9, 10],
  ['day'], 'rare', '#8a7d6b', 8, 50, False,
  'The pika, a small rabbit relative of rocky slopes, gathers piles of plants in summer to eat through winter (national park guidance).',
  'Stay on the trail and never move rocks in a talus slope - it is the pika\'s home.'),
]

# the regions each wilds world belongs to (wilds/registry/wilds.json worlds; read to prove every id exists)
WILDS_PATH = 'wilds/registry/wilds.json'


def need(d, k, where):
    if not isinstance(d, dict):
        raise TypeError(f'wildlife: {where}: expected an object to read {k!r} from')
    if k not in d:
        raise KeyError(f'wildlife: {where}: required field {k!r} is missing')
    return d[k]


WILDS_IDS = [need(w, 'id', WILDS_PATH) for w in need(json.loads((ROOT / WILDS_PATH).read_text()), 'worlds', WILDS_PATH)]

species = []
seen = set()
NUM_RE = re.compile(r'\b\d+(\.\d+)?\s*(ft|feet|foot|lb|lbs|pounds|kg|inches|inch|cm|m|mph|km/h|years?)\b', re.I)
for row in S:
    (sid, name, group, regions, hab, months, times, rarity, colour, safe_m, photo_m, danger, fact, safety) = row
    where = f'species {sid}'
    if sid in seen:
        raise ValueError(f'wildlife: {where} declared twice')
    seen.add(sid)
    if not re.fullmatch(r'[a-z]+(-[a-z]+)*', sid):
        raise ValueError(f'wildlife: {where}: id is not kebab-case')
    if group not in GROUPS:
        raise ValueError(f'wildlife: {where}: group {group!r} not in {GROUPS}')
    if not regions or any(r not in REGIONS for r in regions):
        raise ValueError(f'wildlife: {where}: regions {regions} not within {REGIONS}')
    if hab not in HABITATS:
        raise ValueError(f'wildlife: {where}: habitat {hab!r} not in {sorted(HABITATS)}')
    if not months or any(m not in range(1, 13) for m in months) or len(set(months)) != len(months):
        raise ValueError(f'wildlife: {where}: months must be distinct 1..12')
    if not times or any(t not in TIMES for t in times):
        raise ValueError(f'wildlife: {where}: times {times} not within {TIMES}')
    if rarity not in RARITY:
        raise ValueError(f'wildlife: {where}: rarity {rarity!r} not in {sorted(RARITY)}')
    if not re.fullmatch(r'#[0-9a-f]{6}', colour):
        raise ValueError(f'wildlife: {where}: colour {colour!r} is not #rrggbb')
    if not (0 < safe_m < photo_m):
        raise ValueError(f'wildlife: {where}: need 0 < safe_m < photo_m (the photo band)')
    if not re.search(r'\((state|federal) wildlife agency\)|\(NOAA Fisheries\)|\(bird (field guides|conservation groups)\)|'
                     r'\(conservation groups\)|\(national park guidance\)', fact):
        raise ValueError(f'wildlife: {where}: fact must name the kind of source in parentheses')
    if NUM_RE.search(fact) or NUM_RE.search(safety):
        raise ValueError(f'wildlife: {where}: a fact or safety line quotes a measurement - no invented numbers')
    if danger and not re.search(r'[Dd]angerous|never approach', safety):
        raise ValueError(f'wildlife: {where}: a dangerous species needs a plain danger line')
    species.append({
        'id': sid, 'name': name, 'group': group, 'regions': regions, 'habitat': hab,
        'window': {'months': sorted(months), 'times': times, 'label': CALENDAR_LABEL},
        'rarity': rarity, 'points': RARITY[rarity], 'colour': colour,
        'game_m': {'safe': safe_m, 'photo': photo_m}, 'dangerous': danger,
        'fact': fact, 'safety': safety, 'provenance': 'AUTHORED',
        'quests': {r: f'treasure-bayou-photo-{r}-{sid}' for r in regions if r != 'wilds'},
    })
for r in REGIONS:
    if sum(1 for s in species if r in s['regions']) < 8:
        raise AssertionError(f'wildlife: region {r} has fewer than 8 species')

# ---------------------------------------------------------------- the games (AUTHORED steps, play only)
GAMES = {
    'gator-season': {
        'title': 'Alligator season (simulation)',
        'label': 'SIMULATION - licensed-tag harvest, no animal is shown harmed; a catch is a tag recorded.',
        'rules_line': RULES_LINE,
        'general': ('Louisiana runs a regulated alligator harvest season with tags issued through the state wildlife '
                    'agency; this game shows the steps only in general terms, on an approximate game calendar.'),
        'months': {'list': [8, 9], 'label': CALENDAR_LABEL},
        'region': 'parishes',
        'steps': [
            ('tag', 'Check your (simulated) licence and tag before you go out - no tag, no hunt.'),
            ('buddy', 'Go with a trained partner, tell someone your plan, wear a life jacket in the boat.'),
            ('line', 'Set a line at the marked spot on the bank of AUTHORED water - never near a swimming or boat area.'),
            ('wait', 'Keep well back from the line and the water\'s edge; alligators are dangerous.'),
            ('check', 'Check the line with your partner from the boat, never alone and never by hand.'),
            ('record', 'Record the tag number in the log - in this game a catch is a tag recorded, nothing more.'),
        ],
        'quest': 'treasure-bayou-gator-tag',
        'classroom': {
            'title': 'Alligator nest survey (K-12)',
            'label': 'Classroom mode: the alligator season is replaced by a nest SURVEY - count and photograph from a distance.',
            'steps': [
                ('distance', 'Stay far back: a mother alligator guards her nest mound.'),
                ('spot', 'Spot the nest mound of piled plants at the marsh edge through binoculars.'),
                ('photo', 'Take a photo from the survey point - never walk up to a nest.'),
                ('record', 'Record the mound on the survey sheet (a game record on this device only).'),
                ('leave', 'Leave quietly the way you came.'),
            ],
            'quest': 'treasure-bayou-nest-survey',
        },
    },
    'photo-safari': {
        'title': 'Birding photo safari',
        'label': 'Photograph birds from the photo band: too close and the shot is refused.',
        'target_group': 'bird', 'target_count': 5,
        'quests': {r: f'side-bayou-photo-safari-{r}' for r in ('parishes', 'bay')},
    },
    'turtle-crossing': {
        'title': 'Turtle crossing helper',
        'label': 'Choose what a safe helper does when a turtle is crossing a road.',
        'rounds': [
            ('A turtle is halfway across a quiet road. Traffic is clear.',
             [('Move it across in the direction it was heading, then step back.', True),
              ('Take it home as a pet.', False), ('Turn it around to where it came from.', False)],
             'Wildlife agencies advise helping only when it is safe, in the direction the turtle was going.'),
            ('A big turtle with a long tail and a strong beak is crossing.',
             [('Pick it up by the tail.', False), ('Let it cross and keep people and pets back.', True),
              ('Poke it to hurry it.', False)],
             'Snapping turtles can bite hard: never lift one by the tail; keep back and let it cross.'),
            ('Cars are coming fast on a busy road.',
             [('Run into the road to save it.', False), ('Stay safe off the road and report it if needed.', True),
              ('Wave cars to stop.', False)],
             'Your own safety comes first - never step into traffic for an animal.'),
        ],
        'quests': {r: f'treasure-bayou-turtle-{r}' for r in ('parishes', 'bay')},
    },
    'shoreline-litter': {
        'title': 'Shoreline litter for wildlife',
        'label': 'Sort shoreline litter into the right bag and learn why it matters to wildlife.',
        'items': [
            ('fishing-line', 'Tangled fishing line', 'trash', 'Loose fishing line tangles birds, turtles and otters.'),
            ('ring-carrier', 'Plastic can rings', 'trash', 'Rings can trap a bird\'s neck or a turtle\'s shell.'),
            ('plastic-bag', 'Plastic bag', 'trash', 'Turtles can mistake floating bags for food.'),
            ('can', 'Aluminium can', 'recycle', 'Cans are widely recyclable - check local rules.'),
            ('glass-bottle', 'Glass bottle', 'recycle', 'Broken glass cuts paws and feet on the shore.'),
            ('driftwood', 'Driftwood', 'leave', 'Natural driftwood is shelter for small animals - leave it.'),
        ],
        'bins': ['trash', 'recycle', 'leave'],
        'quests': {r: f'treasure-bayou-litter-{r}' for r in ('parishes', 'bay')},
    },
}
for gid, g in GAMES.items():
    for k in ('title', 'label'):
        need(g, k, f'games.{gid}')
    if 'quest' not in g and 'quests' not in g:
        raise KeyError(f'wildlife: games.{gid} names no quest')
GAMES['gator-season']['steps'] = [{'id': a, 'text': b} for a, b in GAMES['gator-season']['steps']]
GAMES['gator-season']['classroom']['steps'] = [{'id': a, 'text': b} for a, b in GAMES['gator-season']['classroom']['steps']]
GAMES['turtle-crossing']['rounds'] = [{'q': q, 'options': [{'text': t, 'right': r} for t, r in opts], 'why': why}
                                      for q, opts, why in GAMES['turtle-crossing']['rounds']]
if any(sum(o['right'] for o in r['options']) != 1 for r in GAMES['turtle-crossing']['rounds']):
    raise AssertionError('wildlife: every turtle round has exactly one right option')
GAMES['shoreline-litter']['items'] = [{'id': a, 'name': b, 'bin': c, 'why': d} for a, b, c, d in GAMES['shoreline-litter']['items']]
if any(i['bin'] not in GAMES['shoreline-litter']['bins'] for i in GAMES['shoreline-litter']['items']):
    raise AssertionError('wildlife: a litter item names a bin that is not in bins')
GORE = re.compile(r'\b(kill|killed|blood|gore|shoot|shot dead|wound|carcass|skin(ned)?|dead)\b', re.I)
if GORE.search(json.dumps(GAMES)):
    raise AssertionError(f'wildlife: the games text contains gore words: {GORE.findall(json.dumps(GAMES))}')
birds = [s for s in species if s['group'] == 'bird']
if len(birds) < GAMES['photo-safari']['target_count']:
    raise AssertionError('wildlife: fewer birds than the photo safari target')

src = pathlib.Path(__file__).read_bytes() + (ROOT / WILDS_PATH).read_bytes()
doc = {
    'pack': 'wildlife',
    'pack_version': PACK_VERSION,
    'source_stamp': hashlib.sha256(src).hexdigest()[:16],
    'source_stamp_sha256': hashlib.sha256(src).hexdigest(),
    'provenance': 'AUTHORED',
    'honesty': {
        'play': PLAY_LINE,
        'rules_line': RULES_LINE,
        'calendar': 'Sighting windows and seasons are an ' + CALENDAR_LABEL + ' - not survey data, not season dates.',
        'species': ('Real regional species named generally; facts are general lines naming the kind of source; '
                    'no sizes, limits, quotas or dates are given. Game distances are AUTHORED world metres.'),
        'habitat': 'Sightings spawn only on AUTHORED map surfaces (water, shore, land) - not a surveyed range map.',
    },
    'regions': list(REGIONS),
    'wilds_worlds': WILDS_IDS,
    'habitats': HABITATS,
    'times': list(TIMES),
    'safe_viewing': [{'id': a, 'text': b} for a, b in SAFE_VIEWING],
    'species': species,
    'games': GAMES,
    'counts': {'species': len(species), **{r: sum(1 for s in species if r in s['regions']) for r in REGIONS},
               'dangerous': sum(1 for s in species if s['dangerous'])},
}
text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
if '--check' in sys.argv:
    if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
        sys.exit('wildlife/registry/wildlife.json is stale: run python3 wildlife/build.py')
    print('wildlife/registry/wildlife.json is current')
else:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    print(f'wrote wildlife/registry/wildlife.json: {doc["counts"]}')
