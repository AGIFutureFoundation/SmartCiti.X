#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the toolroom registry builder.

Every hall's floor plan carries a tools room; this registry is what hangs
in it. One tool crib per district — twelve hand tools, each with the one
line of what it is for and the schematic shape the 3D toolroom renders —
plus the CRIB DRILL: a deterministic pick exercise (match the job to the
tool) derived from the crib itself, so the drill and the crib can never
drift apart. Halls bind to their district's crib through the skill graph
(<hall>.tools.applied), and tools/test.mjs proves every binding.

DRILL CONTRACT, the same law the simulators keep: the grader is
DETERMINISTIC. A pick is right or wrong against the crib record; the
option order is index arithmetic, not chance; nothing narrative can
change a score.

HONESTY: a schematic training aid for tool identification and tool-crib
discipline — not an inventory of any real toolroom, not tool competency
certification, and no manufacturer or brand is named or drawn.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "3.2.0"
BUILT = "2026-09-10"


def tool(id_, name, glyph, shape, hue, use):
    return {'id': id_, 'name': name, 'glyph': glyph,
            'shape': shape, 'hue': hue, 'use': use}


# One crib per district. Shapes are schematic render kinds the 3D page
# owns (bar, wrench, blade, meter, cyl, coil, hook, case); hues place each
# tool on the board legibly. Uses are verb phrases — the drill asks them.
CRIBS = {
    'structural': {'name': 'Structural tool crib', 'tools': [
        tool('spud-wrench', 'Spud wrench', '\U0001f527', 'wrench', 28,
             'aligns bolt holes and pins the steel connection'),
        tool('sleever-bar', 'Sleever bar', '⚒️', 'bar', 210,
             'levers heavy steel the last inch into place'),
        tool('bull-pin', 'Bull pin', '\U0001f4cd', 'cyl', 12,
             'holds two aligned holes while the bolts go in'),
        tool('torque-wrench', 'Torque wrench', '\U0001f529', 'wrench', 200,
             'tightens a bolt to its specified torque, no further'),
        tool('shackle', 'Rigging shackle', '⛓️', 'hook', 45,
             'closes the load path between sling and pick point'),
        tool('wire-sling', 'Wire-rope sling', '➰', 'coil', 100,
             'wraps the load and carries it to the hook'),
        tool('lever-hoist', 'Lever hoist', '⚙️', 'case', 350,
             'pulls a load in tight where no crane can reach'),
        tool('beam-clamp', 'Beam clamp', '\U0001f5dc️', 'hook', 260,
             'grips a flange to make a temporary pick point'),
        tool('plumb-bob', 'Plumb bob', '\U0001f4cf', 'cone', 182,
             'drops a true vertical line off a point above'),
        tool('center-punch', 'Center punch', '✒️', 'cyl', 300,
             'dimples the layout mark so the drill cannot wander'),
        tool('bolt-gauge', 'Bolt gauge', '\U0001f4d0', 'blade', 150,
             'reads a bolt diameter and thread in one check'),
        tool('impact-wrench', 'Impact wrench', '\U0001f6e0️', 'case', 20,
             'runs structural bolts down fast before the torque pass'),
    ]},
    'envelope': {'name': 'Envelope & finish tool crib', 'tools': [
        tool('utility-knife', 'Utility knife', '\U0001f52a', 'blade', 12,
             'scores and cuts sheet goods to the line'),
        tool('taping-knife', 'Taping knife', '\U0001f3a8', 'blade', 200,
             'lays and feathers joint compound over the seam'),
        tool('brick-trowel', 'Brick trowel', '\U0001f9f1', 'blade', 28,
             'butters and beds the mortar under each course'),
        tool('jointer', 'Brick jointer', '〰️', 'bar', 45,
             'strikes the mortar joint to a weathertight profile'),
        tool('grout-float', 'Grout float', '⬜', 'case', 100,
             'presses grout into tile joints and pulls the excess'),
        tool('suction-cup', 'Glass suction cup', '\U0001fa9f', 'cyl', 182,
             'grips a glass lite so it can be walked and set'),
        tool('caulk-gun', 'Caulking gun', '\U0001f9f4', 'cyl', 260,
             'drives a steady sealant bead along the joint'),
        tool('chalk-line', 'Chalk line', '\U0001f4cf', 'case', 350,
             'snaps a straight layout line across the field'),
        tool('framing-square', 'Framing square', '\U0001f4d0', 'blade', 210,
             'checks and lays out a true right angle'),
        tool('block-plane', 'Block plane', '\U0001fab5', 'case', 30,
             'shaves a door or trim edge to the exact fit'),
        tool('putty-knife', 'Putty knife', '\U0001f58c️', 'blade', 150,
             'presses filler into small defects before paint'),
        tool('seam-roller', 'Seam roller', '\U0001f3af', 'cyl', 300,
             'sets a membrane seam with even rolling pressure'),
    ]},
    'systems': {'name': 'Building-systems tool crib', 'tools': [
        tool('multimeter', 'Multimeter', '\U0001f50b', 'meter', 48,
             'reads voltage, current and resistance in one instrument'),
        tool('wire-strippers', 'Wire strippers', '✂️', 'wrench', 12,
             'strips insulation to length without nicking the conductor'),
        tool('fish-tape', 'Fish tape', '\U0001f3a3', 'coil', 200,
             'pulls conductors through a finished conduit run'),
        tool('conduit-bender', 'Conduit bender', '\U0001f4d0', 'bar', 28,
             'sweeps a conduit offset to the marked angle'),
        tool('tubing-cutter', 'Tubing cutter', '⚙️', 'hook', 182,
             'cuts copper tube square with a rolled wheel'),
        tool('pipe-wrench', 'Pipe wrench', '\U0001f527', 'wrench', 350,
             'grips and turns threaded pipe by its jaw bite'),
        tool('crimper', 'Crimping tool', '\U0001f9f2', 'wrench', 260,
             'closes a connector onto its conductor gas-tight'),
        tool('manifold-gauge', 'Manifold gauge set', '\U0001f321️', 'meter', 100,
             'reads both sides of a refrigeration circuit at once'),
        tool('torpedo-level', 'Torpedo level', '\U0001f4cf', 'bar', 45,
             'levels short runs where a full level cannot fit'),
        tool('voltage-tester', 'Non-contact tester', '⚡', 'cyl', 55,
             'proves a circuit dead before any hand touches it'),
        tool('channel-locks', 'Tongue-and-groove pliers', '\U0001f980', 'wrench', 210,
             'adjusts its jaw span to grip what the job presents'),
        tool('nut-driver', 'Nut driver set', '\U0001f529', 'cyl', 300,
             'seats panel screws and small hex hardware cleanly'),
    ]},
    'energy': {'name': 'Energy & utilities tool crib', 'tools': [
        tool('lineman-pliers', 'Lineman pliers', '\U0001f9b7', 'wrench', 48,
             'cuts, twists and pulls conductor in one grip'),
        tool('hot-stick', 'Hot stick', '\U0001f9af', 'bar', 12,
             'operates energized gear from an insulated distance'),
        tool('cable-cutter', 'Cable cutter', '✂️', 'wrench', 200,
             'shears large cable clean without crushing the strands'),
        tool('clamp-meter', 'Clamp meter', '\U0001f9f2', 'meter', 182,
             'reads current through a conductor without breaking it'),
        tool('megohmmeter', 'Insulation tester', '\U0001f50b', 'meter', 260,
             'proves insulation resistance before energizing'),
        tool('gas-detector', 'Gas detector', '\U0001f6a8', 'meter', 350,
             'sniffs the trench and vault air before entry'),
        tool('valve-key', 'Valve key', '\U0001f511', 'bar', 100,
             'reaches and turns a buried curb valve from grade'),
        tool('pipe-locator', 'Line locator', '\U0001f4e1', 'meter', 28,
             'traces the buried line before the first dig'),
        tool('torque-screwdriver', 'Torque screwdriver', '\U0001f529', 'cyl', 45,
             'lands terminal screws at their exact rating'),
        tool('splice-shell', 'Splice shell set', '\U0001f9f0', 'case', 210,
             'rebuilds and seals a cable joint against water'),
        tool('sharpshooter', 'Sharpshooter spade', '⛏️', 'blade', 30,
             'opens a narrow potholing cut over a marked line'),
        tool('grounding-set', 'Grounding cluster', '⛓️', 'coil', 150,
             'bonds the dead line to earth before work begins'),
    ]},
    'earthworks': {'name': 'Earthworks & plant tool crib', 'tools': [
        tool('grade-rod', 'Grade rod', '\U0001f4cf', 'bar', 100,
             'reads cut and fill against the laser plane'),
        tool('laser-level', 'Rotary laser', '\U0001f526', 'meter', 12,
             'spins one level datum across the whole site'),
        tool('mattock', 'Pick mattock', '⛏️', 'wrench', 28,
             'breaks hard ground the shovel cannot start'),
        tool('round-shovel', 'Round-point shovel', '\U0001f9f9', 'blade', 45,
             'moves loose spoil and shapes the cut by hand'),
        tool('grease-gun', 'Grease gun', '\U0001f9f4', 'cyl', 200,
             'feeds every zerk on the machine its daily grease'),
        tool('pry-bar', 'Pry bar', '\U0001f9b4', 'bar', 260,
             'levers pins, plates and stubborn iron apart'),
        tool('plate-tamper', 'Hand tamper', '\U0001f528', 'bar', 350,
             'compacts backfill in lifts where plate compactors cannot go'),
        tool('string-line', 'String line', '\U0001f9f5', 'coil', 182,
             'carries line and grade between the offset stakes'),
        tool('marking-wand', 'Marking wand', '\U0001f58c️', 'cyl', 55,
             'paints the locate colors onto the ground'),
        tool('socket-set', 'Socket set', '\U0001f9f0', 'case', 210,
             'services the plant with the right drive size'),
        tool('pin-punch', 'Pin punch', '✒️', 'cyl', 300,
             'drives track and bucket pins in and out true'),
        tool('tire-gauge', 'Tire pressure gauge', '\U0001f321️', 'meter', 150,
             'checks plant tires to the loading chart'),
    ]},
    'industry': {'name': 'Heavy-industry tool crib', 'tools': [
        tool('chipping-hammer', 'Chipping hammer', '⚒️', 'wrench', 12,
             'knocks slag off the cooled weld for inspection'),
        tool('flange-spreader', 'Flange spreader', '\U0001f529', 'wrench', 28,
             'opens a bolted flange safely against its spring'),
        tool('alignment-pins', 'Flange alignment pins', '\U0001f4cd', 'cyl', 45,
             'draw two flanges into bolt-hole alignment'),
        tool('feeler-gauge', 'Feeler gauge', '\U0001f4d0', 'blade', 200,
             'measures the gap a caliper cannot enter'),
        tool('micrometer', 'Micrometer', '⚙️', 'hook', 182,
             'reads a machined diameter to the thousandth'),
        tool('file-set', 'File set', '\U0001f9f0', 'case', 100,
             'dresses an edge or fit by controlled strokes'),
        tool('deburring-tool', 'Deburring tool', '✒️', 'cyl', 260,
             'breaks the sharp edge every cut leaves behind'),
        tool('dial-indicator', 'Dial indicator', '\U0001f321️', 'meter', 350,
             'reads runout and lift as the shaft turns'),
        tool('bearing-puller', 'Bearing puller', '\U0001f9f2', 'hook', 210,
             'draws a bearing off its seat without damage'),
        tool('soapstone', 'Soapstone holder', '\U0001f58c️', 'bar', 55,
             'marks hot steel where ink and chalk fail'),
        tool('weld-gauge', 'Fillet weld gauge', '\U0001f4cf', 'blade', 300,
             'measures a finished weld against its called size'),
        tool('pipe-stand-wrench', 'Chain tongs', '⛓️', 'wrench', 150,
             'turns large pipe by wrapping it, not biting it'),
    ]},
    'transport': {'name': 'Transport & mobility tool crib', 'tools': [
        tool('track-wrench', 'Track wrench', '\U0001f527', 'wrench', 262,
             'runs rail bolts down through the joint bars'),
        tool('spike-puller', 'Spike puller', '\U0001f9b4', 'bar', 12,
             'draws a rail spike without splitting the tie'),
        tool('rail-gauge', 'Track gauge', '\U0001f4cf', 'blade', 200,
             'holds the rails at their exact set apart'),
        tool('torque-multiplier', 'Torque multiplier', '⚙️', 'case', 28,
             'multiplies hand torque for the largest fasteners'),
        tool('compression-tester', 'Compression tester', '\U0001f321️', 'meter', 45,
             'reads each diesel cylinder against its siblings'),
        tool('brake-tool', 'Brake spring tool', '\U0001f9f2', 'wrench', 100,
             'seats and releases brake springs under control'),
        tool('wheel-chock', 'Wheel chock pair', '⛔', 'case', 350,
             'holds the vehicle still before anyone goes under'),
        tool('signal-tester', 'Signal test set', '\U0001f4e1', 'meter', 182,
             'proves the circuit sees the aspect it should'),
        tool('alignment-bar', 'Alignment bar', '\U0001f4cd', 'bar', 210,
             'walks bolt holes into line on heavy assemblies'),
        tool('impact-gun', 'Impact gun', '\U0001f6e0️', 'case', 20,
             'breaks and runs lug and frame hardware fast'),
        tool('creeper-light', 'Inspection lamp', '\U0001f526', 'cyl', 55,
             'lights the underside where the fault hides'),
        tool('cable-height-stick', 'Height stick', '\U0001f9af', 'bar', 300,
             'measures wire height above the rail head safely'),
    ]},
    'control': {'name': 'Survey, safety & environment tool crib', 'tools': [
        tool('prism-pole', 'Prism pole', '\U0001f4cd', 'bar', 148,
             'holds the survey prism plumb over the point'),
        tool('auto-level', 'Auto level', '\U0001f52d', 'meter', 12,
             'reads elevation differences through a leveled scope'),
        tool('field-tripod', 'Field tripod', '\U0001f4d0', 'bar', 28,
             'plants the instrument rigid over the station'),
        tool('gas-monitor', 'Four-gas monitor', '\U0001f6a8', 'meter', 350,
             'watches the air for the four killers continuously'),
        tool('sampling-pump', 'Air sampling pump', '\U0001f32c️', 'case', 200,
             'draws a metered air volume through the media'),
        tool('decon-sprayer', 'Decon sprayer', '\U0001f9f4', 'cyl', 100,
             'washes contamination down at the exit line'),
        tool('hepa-vac', 'HEPA vacuum', '\U0001f32a️', 'case', 260,
             'captures fine hazard dust instead of scattering it'),
        tool('anemometer', 'Anemometer', '\U0001f4a8', 'meter', 182,
             'reads air speed across the containment face'),
        tool('sound-meter', 'Sound level meter', '\U0001f50a', 'meter', 45,
             'measures noise dose where hearing is on the line'),
        tool('lux-meter', 'Light meter', '\U0001f526', 'meter', 55,
             'proves the task lighting meets its required lux'),
        tool('moisture-meter', 'Moisture meter', '\U0001f4a7', 'meter', 210,
             'finds the wet wall behind the dry paint'),
        tool('rope-grab', 'Rope grab', '⛓️', 'hook', 300,
             'arrests a fall on the lifeline the moment it starts'),
    ]},
}

# The crib drill, derived from the crib itself: five picks per district,
# spread across the board by stride so every drill samples the whole crib.
# ask = the tool's own use line; the page renders the question around it.
DRILL_PICKS = 5


def drill_for(tools):
    n = len(tools)
    tasks = []
    for i in range(DRILL_PICKS):
        t = tools[(i * 5 + 2) % n]
        tasks.append({'ask': 'Pick the tool that ' + t['use'],
                      'tool': t['id']})
    return tasks


districts = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']
unions = json.load(open(ROOT / 'unions/registry/unions.json'))['unions']
skills = {s['skill_id'] for s in
          json.load(open(ROOT / 'pack/registry/skills.json'))['skills']}

assert set(CRIBS) == set(districts), 'one crib per district, exactly'
for dk, crib in CRIBS.items():
    ids = [t['id'] for t in crib['tools']]
    assert len(ids) == 12 and len(set(ids)) == 12, f'{dk}: 12 unique tools'

district_of = {slug: k for k, d in districts.items() for slug in d['halls']}
bindings = {}
for u in unions:
    skill = f"{u['slug']}.tools.applied"
    assert skill in skills, f"no such skill {skill}"
    bindings[u['slug']] = {'district': district_of[u['slug']],
                           'skill_id': skill}

drills = {dk: drill_for(crib['tools']) for dk, crib in CRIBS.items()}
for dk, tasks in drills.items():
    ids = {t['id'] for t in CRIBS[dk]['tools']}
    assert all(x['tool'] in ids for x in tasks)
    assert len({x['tool'] for x in tasks}) == DRILL_PICKS

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-toolroom-registry',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'drill': {
        'name': 'Crib check',
        'picks': DRILL_PICKS,
        'contract': 'deterministic: a pick is right or wrong against the '
                    'crib record; the option order is index arithmetic, '
                    'not chance; nothing narrative can change a score',
    },
    'honesty': {
        'status': 'a schematic training aid for tool identification and '
                  'tool-crib discipline - not an inventory of any real '
                  'toolroom, not tool competency certification, and no '
                  'manufacturer or brand is named or drawn.',
    },
    'cribs': CRIBS,
    'drills': drills,
    'hall_bindings': bindings,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'toolcribs.json').write_text(
    json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
n_tools = sum(len(c['tools']) for c in CRIBS.values())
print(f"toolroom registry: {len(CRIBS)} cribs, {n_tools} tools, "
      f"{len(drills) * DRILL_PICKS} drill picks, "
      f"{len(bindings)} halls bound (source stamp {stamp})")
