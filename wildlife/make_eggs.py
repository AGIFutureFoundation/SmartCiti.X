#!/usr/bin/env python3
"""wildlife/make_eggs.py - writes quests/source/bayou.json (BAYOU's quest source, GAMES_CONTRACT v1).

Two parts, both AUTHORED play:
1. finds the wildlife kit fires by play (web/wildkit.py): one photo treasure per species per region
   (world 'parishes' | 'bay'), the gator-season tag / K-12 nest survey, the turtle helper, the litter sort,
   a photo-safari side quest per region, and one field-guide treasure per wilds world (place 'trailhead');
2. hidden easter eggs across the parish, Bay, wilds and campus maps - riddles, typed words and the old code -
   each with a one-line informative `reveal` that names the kind of source and quotes no invented number.
`python3 wildlife/make_eggs.py --check` fails when the file is stale. Run python3 quests/build.py afterwards.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / 'quests' / 'source' / 'bayou.json'
W = json.loads((HERE / 'registry' / 'wildlife.json').read_text())
NOREQ = {'lessons': [], 'halls': [], 'quests': []}
E = []


def add(kind, slug, title, world, place, hint, label, reveal, band='K-5', trigger=None, target=None, riddle=None,
        requires=None):
    eid = f'{kind}-bayou-{slug}'
    e = {'id': eid, 'kind': kind, 'title': title, 'world': world, 'place': place,
         'requires': requires if requires is not None else NOREQ, 'hint': hint,
         'reward': {'badge': 'badge-' + eid, 'label': label}, 'provenance': 'AUTHORED', 'reveal': reveal}
    if band:
        e['band'] = band
    if trigger:
        e['trigger'] = trigger
    if target:
        e['target'] = target
    if riddle:
        e['riddle'] = riddle
    E.append(e)
    return eid


RW = {'parishes': 'parishes', 'bay': 'bay'}
# ---------------------------------------------------------------- 1. kit-fired finds
photo_ids = {'parishes': [], 'bay': []}
for sp in W['species']:
    for region, qid in sp['quests'].items():
        slug = qid[len('treasure-bayou-'):]
        add('treasure', slug, f'Photo: {sp["name"]}', RW[region], sp['id'],
            f'Photograph a {sp["name"].lower()} from the photo band - not too close.',
            f'{sp["name"]} photographer', sp['fact'])
        if sp['group'] == 'bird':
            photo_ids[region].append(qid)
G = W['games']
gs = G['gator-season']
add('treasure', 'gator-tag', 'Alligator season: tag recorded (simulation)', 'parishes', 'gator-season',
    'Work through the licensed-tag simulation with a partner, safety first.', 'Tag recorder (simulation)',
    gs['general'] + ' ' + W['honesty']['rules_line'], band=None)
add('treasure', 'nest-survey', 'Alligator nest survey (K-12)', 'parishes', 'nest-survey',
    'In classroom mode, survey an alligator nest mound from a distance.', 'Nest surveyor',
    'Female alligators build nest mounds of plants and guard them, so surveys are done from a distance '
    '(state wildlife agency).')
for region in ('parishes', 'bay'):
    add('treasure', f'turtle-{region}', 'Turtle crossing helper', RW[region], 'turtle-crossing',
        'Answer the turtle-crossing rounds the safe way.', 'Turtle helper',
        'Wildlife agencies advise helping a turtle across only when it is safe, in the direction it was going '
        '(state wildlife agency).')
    add('treasure', f'litter-{region}', 'Shoreline litter for wildlife', RW[region], 'shoreline-litter',
        'Sort the shoreline litter into the right bags.', 'Shoreline keeper',
        'Discarded fishing line and plastic entangle and choke birds, turtles and marine mammals (federal ocean agency).')
    add('side', f'photo-safari-{region}', 'Birding photo safari', RW[region], 'photo-safari',
        'Photograph every bird in this region\'s field guide, from the photo band.', 'Safari birder',
        'Birders watch from a distance with binoculars; bird conservation groups ask people never to flush '
        'birds for a photo (bird conservation groups).', band=None,
        requires={'lessons': [], 'halls': [], 'quests': sorted(photo_ids[region])})
WILDS_GUIDE = {
    'mountain': 'Mountain wildlife such as pikas live among loose rock slopes; stay on the trail (national park guidance).',
    'forest': 'Forest bears learn fast where people leave food - store food where bears cannot reach it (state wildlife agency).',
    'canyon': 'Bighorn sheep climb steep canyon rock on split hooves; never approach them on cliffs (state wildlife agency).',
    'delta': 'Marsh and delta wetlands filter water and shelter young fish and birds (federal wildlife agency).',
}
for wid in W['wilds_worlds']:
    if wid not in WILDS_GUIDE:
        raise KeyError(f'make_eggs: no AUTHORED field-guide line for wilds world {wid!r}')
    add('treasure', f'wilds-{wid}-guide', 'Field guide page', f'wilds:{wid}', 'trailhead',
        'Take a wildlife photo from the photo band anywhere in this world.', 'Field guide keeper', WILDS_GUIDE[wid])

# ---------------------------------------------------------------- 2. hidden eggs (typed / konami / clicks)
PARISH_EGGS = [
    ('22071', 'pelican', 'The state bird', 'A bird on the state flag feeds its young. Type its name.',
     'The brown pelican, Louisiana\'s state bird, disappeared from the state\'s coast and was brought back by '
     'reintroduction from Florida (state wildlife agency).'),
    ('22075', 'birdfoot', 'The river\'s foot', 'At the river\'s mouth the channels spread like toes. Type the shape.',
     'The Mississippi River\'s bird\'s-foot delta is named for the shape its channels make on a map '
     '(geological survey).'),
    ('22087', 'spoonbill', 'The pink wader', 'A pink bird with a spoon for a bill. Type what it is called.',
     'Roseate spoonbills nest in colonies in coastal Louisiana marshes; their pink comes from their food '
     '(bird conservation groups).'),
    ('22051', 'barataria', 'The pirate bay', 'A bay south of the city once hid privateers. Type its name.',
     'Barataria Bay is an estuary where river water meets Gulf salt water - a nursery for shrimp, crabs and fish '
     '(state wildlife agency).'),
    ('22109', 'goodearth', 'The good earth', 'This parish\'s French name means two English words. Type them as one.',
     'Terrebonne is French for "good earth"; coastal Louisiana is losing wetland to erosion and sinking land '
     '(geological survey).'),
    ('22057', 'fourche', 'The fork', 'The bayou that names this parish was once a fork of the river. Type the French.',
     'Lafourche means "the fork": Bayou Lafourche was once a branch of the Mississippi River (state historical guidance).'),
    ('22103', 'pontchartrain', 'Not quite a lake', 'The big water on the north shore is called a lake. Type its name.',
     'Lake Pontchartrain is a brackish estuary joined to the Gulf through passes, not a freshwater lake '
     '(state wildlife agency).'),
    ('22105', 'tupelo', 'Knees in the water', 'A swamp tree that stands with the cypress. Type its name.',
     'Bald cypress and swamp tupelo grow in standing water; cypress "knees" rise from the roots '
     '(state forestry guidance).'),
    ('22063', 'maurepas', 'The smaller lake', 'West of the big lake lies a smaller one ringed by swamp. Type it.',
     'Lake Maurepas, west of Lake Pontchartrain, is ringed by cypress-tupelo swamp (state wildlife agency).'),
    ('22005', 'manchac', 'The old shortcut', 'A bayou once linked the river to the lakes. Type its name.',
     'Bayou Manchac once linked the Mississippi River toward Lake Maurepas and was used as a route by early '
     'travellers (state historical guidance).'),
    ('22093', 'bonfire', 'Fires on the levee', 'On one winter night the levee is lit. Type what burns.',
     'Bonfires on the Mississippi River levee in St. James Parish light Christmas Eve, a local tradition '
     '(state tourism guidance).'),
    ('22095', 'swampbridge', 'The bridge on stilts', 'Highways here cross the swamp high on piles. Type what they are.',
     'Highways across the Manchac swamp run on long elevated bridges built on piles over the wetland '
     '(state transportation guidance).'),
    ('22089', 'diversion', 'Let the river build', 'Open a gate and let the river carry mud to the marsh. Type the word.',
     'River diversions send Mississippi water and sediment into wetlands to help build land; the Bonnet Carre '
     'Spillway relieves river floods into Lake Pontchartrain (state coastal agency).'),
]
for fips, word, title, riddle, reveal in PARISH_EGGS:
    add('egg', f'parish-{fips}-{word}', title, f'parish:{fips}', 'hidden', riddle, f'Bayou riddler: {title}',
        reveal, trigger=f'typed:{word}', riddle=riddle)
add('egg', 'parishes-konami', 'The old code in the bayou', 'parishes', 'hidden',
    'Some keys remember an older arcade - try them in the world.', 'Old-code gator watcher',
    'Alligators are cold-blooded and bask in the sun to warm up; that is why they lie still on banks '
    '(state wildlife agency).', trigger='konami', riddle='Up, up, down, down, left, right, left, right, B, A.')
add('egg', 'parishes-gator', 'Say see you later', 'parishes', 'hidden',
    'Type the animal you say "see you later" to.', 'Later, gator',
    'Only American alligators and Chinese alligators exist today; the American one lives in the southeastern '
    'United States (state wildlife agency).', trigger='typed:alligator', riddle='See you later...')
add('egg', 'parishes-nutria', 'The marsh eater', 'parishes', 'hidden',
    'A rodent from another continent eats the marsh. Type its name.', 'Marsh defender',
    'Nutria feeding strips marsh plants and adds to coastal wetland loss; the state pays for their control '
    'through a program (state wildlife agency).', trigger='typed:nutria', riddle='Orange teeth, webbed feet.')

BAY_EGGS = [
    ('06075', 'sealion', 'The barking dock', 'Some bayside docks bark. Type who barks.',
     'Sea lions began hauling out on floating docks on the San Francisco waterfront around 1990 and became a '
     'well-known sight (NOAA Fisheries).'),
    ('06041', 'redwood', 'The tallest trees', 'The tallest trees on Earth grow in these coastal hills. Type them.',
     'Coast redwoods are the tallest trees on Earth and grow where summer fog brings moisture (national park guidance).'),
    ('06001', 'saltpond', 'The coloured ponds', 'Seen from a plane, some Bay ponds are red and green. Type what they are.',
     'Former salt evaporation ponds in the South Bay are being restored to tidal marsh; tiny organisms colour '
     'them red and green (federal wildlife agency).'),
    ('06081', 'monarch', 'The winter groves', 'Orange wings gather on coastal trees in winter. Type the butterfly.',
     'Western monarch butterflies overwinter in groves along the California coast (conservation groups).'),
    ('06013', 'otter', 'The otter comeback', 'A playful swimmer has been seen again in Bay creeks. Type it.',
     'River otters have been reported returning to many San Francisco Bay Area creeks and marshes '
     '(conservation groups).'),
    ('06097', 'estuary', 'Where rivers meet the sea', 'The Bay is not a lake and not the ocean. Type what it is.',
     'San Francisco Bay is an estuary: fresh water from rivers mixes with salt water from the Pacific '
     '(federal geological survey).'),
    ('06095', 'suisun', 'The big marsh', 'The largest brackish marsh on the West Coast lies here. Type its name.',
     'Suisun Marsh is the largest brackish marsh on the west coast of the United States (state wildlife agency).'),
    ('06055', 'vineyard', 'Rows on the hills', 'Rows of vines cover these valleys. Type what they are called.',
     'Vineyards border creeks and wetlands, so growers and wildlife agencies work on keeping stream habitat '
     'healthy (state wildlife agency).'),
    ('06085', 'avocet', 'The upturned bill', 'A shorebird sweeps an upturned bill through the ponds. Type it.',
     'American avocets feed in South Bay salt ponds and mudflats, sweeping their bills through shallow water '
     '(bird field guides).'),
]
for fips, word, title, riddle, reveal in BAY_EGGS:
    add('egg', f'bay-{fips}-{word}', title, f'bay:{fips}', 'hidden', riddle, f'Bay riddler: {title}', reveal,
        trigger=f'typed:{word}', riddle=riddle)
add('egg', 'bay-konami', 'The old code by the Bay', 'bay', 'hidden', 'Some keys remember an older arcade.',
    'Old-code seal spotter',
    'Harbor seals rest hauled out on rocks and beaches; if a seal lifts its head to watch you, you are too close '
    '(NOAA Fisheries).', trigger='konami', riddle='Up, up, down, down, left, right, left, right, B, A.')
add('egg', 'bay-fog', 'Summer fog', 'bay', 'hidden', 'Type what rolls through the Golden Gate on summer afternoons.',
    'Fog watcher',
    'Summer fog forms when moist ocean air cools over cold coastal water and is drawn inland through the Golden '
    'Gate (national weather service).', trigger='typed:fog', riddle='Cool, grey, and it comes in on little cat feet.')

WILDS_EGGS = [
    ('mountain', 'pika', 'The rock rabbit', 'A tiny cousin of the rabbit squeaks from the talus. Type it.',
     'Pikas gather "haypiles" of plants in summer to eat through the winter under the snow (national park guidance).'),
    ('forest', 'bearbox', 'Lock the food', 'Where bears roam, food goes in this. Type it as one word.',
     'Bear-resistant food lockers keep bears from learning to raid camps (national park guidance).'),
    ('canyon', 'bighorn', 'Horns on the ledge', 'Rams clash on the canyon rim. Type what they are.',
     'Bighorn rams clash horns in the autumn to settle rank (state wildlife agency).'),
    ('delta', 'beaver', 'The dam builder', 'Who turns a stream into a pond? Type it.',
     'Beaver dams create ponds and wetlands that many other animals use (state wildlife agency).'),
]
for wid, word, title, riddle, reveal in WILDS_EGGS:
    add('egg', f'wilds-{wid}-{word}', title, f'wilds:{wid}', 'trailhead', riddle, f'Wilds riddler: {title}',
        reveal, trigger=f'typed:{word}', riddle=riddle)

# campus: hidden hooks the 3D page must emit (NEEDS build_3d); typed words distinct from the page's own 'solidarity'
CAMPUS_EGGS = [
    ('hardhatbird', 'The bird on the crane', 'Birds nest on tall structures. Type what a crew does before it lifts.',
     'Crews check for nesting birds before work on tall structures because active nests of most wild birds are '
     'protected by federal law (federal wildlife agency).', 'typed:nestcheck'),
    ('swale', 'The green ditch', 'A planted ditch that slows rainwater. Type its name.',
     'A bioswale is a planted channel that slows and filters stormwater before it reaches creeks and bays '
     '(federal environmental agency).', 'typed:bioswale'),
]
for slug, title, riddle, reveal, trig in CAMPUS_EGGS:
    add('egg', f'campus-{slug}', title, 'campus', 'hidden', riddle, f'Campus naturalist: {title}', reveal,
        trigger=trig, riddle=riddle)

doc = {'from': 'BAYOU', 'for': 'quests/build.py (GAMES_CONTRACT v1)',
       'note': ('AUTHORED play generated by wildlife/make_eggs.py from wildlife/registry/wildlife.json: photo finds, '
                'the gator-season simulation tag and K-12 nest survey, turtle/litter games, and hidden eggs with '
                'informative reveals. Never a completion record.'),
       'entries': E}
text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
if '--check' in sys.argv:
    if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
        sys.exit('quests/source/bayou.json is stale: run python3 wildlife/make_eggs.py')
    print('quests/source/bayou.json is current')
else:
    OUT.write_text(text, encoding='utf-8')
    print(f'wrote quests/source/bayou.json: {len(E)} entries '
          f'({sum(1 for e in E if e["kind"] == "egg")} eggs, {sum(1 for e in E if e["kind"] == "treasure")} treasures)')
