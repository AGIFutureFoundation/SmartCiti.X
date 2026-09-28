#!/usr/bin/env python3
"""The fleet pack: generic drivable land vehicles and watercraft.

Writes fleet/registry/fleet.json: EXACTLY 50 land vehicles and 20 watercraft,
grouped into families. Every figure (dimensions, mass, top speed, accel,
turning, seats) is AUTHORED: a plausible arcade figure typed for a GENERIC
type, not measured, not taken from any make or model, and not a specification
of any real machine. No makes, models, brands or logos appear anywhere; a
denylist of common makes stops the build if one slips in.

A fleet entry links to a training seat ONLY where the sims registry already has
that seat (sims/registry/sims.json); the seat's href is read from the tasks
registry (tasks/registry/tasks.json, the seat's walkaround task), and the trade
relevance is the seat's own `halls` list. Nothing here invents a seat, a
trade link or a hall. Every other entry has sim_seat null and trades null.

Every entry of a family carries the SAME mesh recipe (the build asserts it),
so a family is one shared geometry drawn as one InstancedMesh; an entry's own
dimensions scale its instance.

Fail closed: a missing field, a wrong count, a duplicate id, an unknown
colour token, a brand word or a dangling seat stops the build by name.

    python3 fleet/build.py
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'fleet.json'
LAND_N, WATER_N = 50, 20


class FleetError(SystemExit):
    pass


def die(msg):
    raise FleetError('fleet/build.py: ' + msg)


# Common vehicle / boat / equipment makes. Whole-word, case-insensitive, over
# every string in the registry. (fleet/test.mjs holds the same list.)
BRAND_DENYLIST = [
    'ford', 'chevrolet', 'chevy', 'toyota', 'honda', 'nissan', 'dodge', 'gmc', 'jeep', 'tesla',
    'bmw', 'mercedes', 'benz', 'audi', 'volkswagen', 'vw', 'volvo', 'hyundai', 'kia', 'subaru',
    'mazda', 'mitsubishi', 'isuzu', 'hino', 'freightliner', 'peterbilt', 'kenworth', 'mack',
    'navistar', 'scania', 'iveco', 'caterpillar', 'komatsu', 'deere', 'bobcat', 'kubota', 'jcb',
    'hitachi', 'liebherr', 'terex', 'jlg', 'genie', 'hyster', 'linde', 'bayliner', 'whaler',
    'yamaha', 'mercury', 'evinrude', 'suzuki', 'kawasaki', 'polaris', 'harley', 'davidson',
    'vespa', 'segway', 'schwinn', 'gillig', 'oshkosh', 'tennant', 'elgin', 'zodiac', 'sea-doo',
    'seadoo', 'porsche', 'ferrari', 'lamborghini', 'jaguar', 'lexus', 'cadillac', 'buick',
    'chrysler', 'fiat', 'renault', 'peugeot', 'citroen', 'skoda', 'seat', 'rivian', 'lucid',
]
# 'seat' is a make too, but also the word for a training seat: the registry's
# own keys are exempt; the denylist applies to VALUES only (names, tokens,
# recipes, notes). See scan() and the test's twin.
BRAND_VALUE_EXEMPT = {'seat'}

# AUTHORED paint table: token -> sRGB hex. World colour for the vehicle
# bodies only; page chrome never uses these (it reads the theme's --tc-*).
COLOURS = {
    'paint.white': '#e9ecee', 'paint.silver': '#b9c0c6', 'paint.grey': '#6f7a82', 'paint.black': '#23282c',
    'paint.red': '#b8322c', 'paint.blue': '#2f5f9e', 'paint.navy': '#1f3350', 'paint.green': '#3d7a4a',
    'paint.yellow': '#e3b52a', 'paint.orange': '#d9702a', 'paint.teal': '#2d8a8a', 'paint.tan': '#b89a6a',
    'trim.dark': '#2b3034', 'trim.steel': '#8d969c', 'glass.tint': '#40545f', 'hull.white': '#eef0ee',
    'hull.grey': '#7c858a', 'hull.green': '#4f6b4a', 'hull.red': '#9e3a2e', 'hull.black': '#2a2d2f',
    'mark.hivis': '#e8d23a', 'mark.stripe': '#d8dde0',
}

# Family: medium, recipe (shared by every entry), entries.
# recipe keys (all required, unused -> None):
#   archetype  car | truck | bus | machine | cycle | hull | paddle
#   cab_len    cab/cabin length as a fraction of overall length
#   cab_h      cab/cabin height as a fraction of overall height
#   body       what sits behind/on the chassis (box, bed, dump, flat, tank, ladder,
#              boom, broom, lowboy, forks, bucket, arm, none, deck, rail)
#   wheel_r    wheel radius as a fraction of overall height (land) / None
#   axles      axle count (land) / None
#   hull       v | flat | pontoon | barge | tub | none (water) / None (land)
#   extra      a single family accent: lightbar, fan, monitor, knees, mast, crane, none
# entry tuple: slug, name, L, W, H (m), mass kg, top km/h, accel m/s^2, turn radius m,
#              seats, body token, trim token, accent token
def R(archetype, cab_len, cab_h, body, wheel_r, axles, hull, extra):
    return {'archetype': archetype, 'cab_len': cab_len, 'cab_h': cab_h, 'body': body,
            'wheel_r': wheel_r, 'axles': axles, 'hull': hull, 'extra': extra}


FAMILIES = [
    ('compact-car', 'Compact car', 'land', R('car', 0.5, 0.45, 'none', 0.2, 2, None, 'none'), [
        ('hatchback', 'Compact hatchback', 4.0, 1.75, 1.48, 1200, 150, 3.4, 5.2, 5, 'paint.blue', 'trim.dark', 'glass.tint'),
        ('sedan', 'Compact sedan', 4.5, 1.8, 1.45, 1350, 160, 3.2, 5.5, 5, 'paint.silver', 'trim.dark', 'glass.tint'),
        ('wagon', 'Compact wagon', 4.6, 1.8, 1.5, 1450, 150, 3.0, 5.6, 5, 'paint.green', 'trim.dark', 'glass.tint'),
    ]),
    ('van', 'Van', 'land', R('car', 0.8, 0.9, 'none', 0.17, 2, None, 'none'), [
        ('cargo-van', 'Cargo van', 5.4, 2.0, 2.3, 2100, 130, 2.4, 6.4, 2, 'paint.white', 'trim.dark', 'glass.tint'),
        ('passenger-van', 'Passenger van', 5.6, 2.0, 2.2, 2300, 130, 2.3, 6.6, 12, 'paint.silver', 'trim.dark', 'glass.tint'),
        ('step-van', 'Step van', 6.2, 2.3, 2.9, 4200, 105, 1.6, 7.4, 2, 'paint.white', 'trim.steel', 'glass.tint'),
    ]),
    ('pickup', 'Pickup', 'land', R('truck', 0.55, 1.0, 'bed', 0.22, 2, None, 'none'), [
        ('crew-cab-pickup', 'Crew-cab pickup', 5.9, 2.0, 1.9, 2400, 150, 2.8, 7.0, 5, 'paint.red', 'trim.dark', 'glass.tint'),
        ('single-cab-pickup', 'Single-cab pickup', 5.3, 2.0, 1.85, 2100, 150, 3.0, 6.6, 3, 'paint.white', 'trim.dark', 'glass.tint'),
        ('utility-body-pickup', 'Utility-body pickup', 6.2, 2.1, 2.0, 3000, 130, 2.4, 7.4, 3, 'paint.white', 'trim.steel', 'mark.hivis'),
    ]),
    ('box-truck', 'Box truck', 'land', R('truck', 0.28, 0.72, 'box', 0.14, 2, None, 'none'), [
        ('small-box-truck', 'Small box truck', 7.0, 2.3, 3.2, 5500, 110, 1.6, 8.0, 3, 'paint.white', 'trim.dark', 'glass.tint'),
        ('medium-box-truck', 'Medium box truck', 8.5, 2.5, 3.6, 8000, 105, 1.3, 9.0, 3, 'paint.white', 'trim.steel', 'glass.tint'),
        ('liftgate-box-truck', 'Box truck with liftgate', 9.0, 2.5, 3.7, 9000, 100, 1.2, 9.4, 2, 'paint.silver', 'trim.dark', 'glass.tint'),
    ]),
    ('dump-truck', 'Dump truck', 'land', R('truck', 0.3, 0.8, 'dump', 0.17, 3, None, 'none'), [
        ('single-axle-dump', 'Single-axle dump truck', 7.2, 2.5, 3.0, 11000, 95, 1.2, 8.2, 2, 'paint.orange', 'trim.dark', 'glass.tint'),
        ('tandem-dump', 'Tandem dump truck', 9.0, 2.5, 3.3, 16000, 90, 1.0, 9.6, 2, 'paint.yellow', 'trim.dark', 'glass.tint'),
        ('site-dumper', 'Articulated site dumper', 10.0, 2.9, 3.5, 22000, 55, 0.8, 8.0, 1, 'paint.yellow', 'trim.dark', 'glass.tint'),
    ]),
    ('flatbed', 'Flatbed', 'land', R('truck', 0.3, 0.85, 'flat', 0.16, 2, None, 'none'), [
        ('stake-bed', 'Stake-bed truck', 7.5, 2.4, 2.8, 6500, 105, 1.4, 8.4, 3, 'paint.white', 'trim.steel', 'glass.tint'),
        ('flatbed-truck', 'Flatbed truck', 8.5, 2.5, 2.9, 8000, 100, 1.3, 9.0, 3, 'paint.blue', 'trim.steel', 'glass.tint'),
        ('rollback-flatbed', 'Rollback flatbed', 9.0, 2.5, 3.0, 9500, 100, 1.2, 9.4, 2, 'paint.red', 'trim.steel', 'mark.hivis'),
    ]),
    ('bus', 'Bus', 'land', R('bus', 0.12, 0.35, 'box', 0.14, 2, None, 'none'), [
        ('transit-bus', 'Transit bus', 12.2, 2.6, 3.2, 12500, 90, 1.1, 12.0, 40, 'paint.blue', 'trim.dark', 'glass.tint'),
        ('school-bus', 'School bus', 11.0, 2.4, 3.1, 11000, 90, 1.1, 11.5, 48, 'paint.yellow', 'trim.dark', 'glass.tint'),
        ('shuttle-bus', 'Shuttle bus', 7.5, 2.3, 2.9, 6000, 100, 1.5, 8.5, 16, 'paint.white', 'trim.dark', 'glass.tint'),
    ]),
    ('bucket-truck', 'Utility bucket truck', 'land', R('truck', 0.3, 0.75, 'boom', 0.15, 2, None, 'lightbar'), [
        ('bucket-truck', 'Utility bucket truck', 8.5, 2.5, 3.6, 12000, 100, 1.2, 9.5, 2, 'paint.white', 'trim.steel', 'mark.hivis'),
        ('bucket-van', 'Bucket van', 6.8, 2.2, 3.2, 5500, 110, 1.6, 7.6, 2, 'paint.white', 'trim.dark', 'mark.hivis'),
    ]),
    ('tow-truck', 'Tow truck', 'land', R('truck', 0.4, 0.8, 'boom', 0.17, 2, None, 'lightbar'), [
        ('wheel-lift-tow', 'Wheel-lift tow truck', 6.5, 2.3, 2.6, 5000, 110, 1.8, 7.4, 2, 'paint.red', 'trim.steel', 'mark.hivis'),
        ('heavy-wrecker', 'Heavy wrecker', 10.0, 2.6, 3.4, 20000, 90, 1.0, 10.6, 2, 'paint.black', 'trim.steel', 'mark.hivis'),
    ]),
    ('fire-engine', 'Fire engine', 'land', R('truck', 0.35, 0.85, 'ladder', 0.14, 2, None, 'lightbar'), [
        ('pumper', 'Pumper engine', 10.0, 2.5, 3.2, 17000, 105, 1.3, 11.0, 6, 'paint.red', 'trim.steel', 'mark.stripe'),
        ('aerial-ladder', 'Aerial ladder truck', 12.5, 2.5, 3.5, 30000, 95, 1.0, 13.0, 4, 'paint.red', 'trim.steel', 'mark.stripe'),
    ]),
    ('ambulance', 'Ambulance', 'land', R('truck', 0.3, 0.8, 'box', 0.15, 2, None, 'lightbar'), [
        ('box-ambulance', 'Box ambulance', 7.0, 2.4, 3.0, 6000, 120, 1.9, 7.8, 4, 'paint.white', 'paint.red', 'mark.stripe'),
        ('van-ambulance', 'Van ambulance', 6.0, 2.1, 2.7, 4000, 130, 2.2, 7.0, 4, 'paint.white', 'paint.orange', 'mark.stripe'),
    ]),
    ('forklift', 'Forklift', 'land', R('machine', 0.55, 1.0, 'forks', 0.2, 2, None, 'none'), [
        ('counterbalance-forklift', 'Counterbalance forklift', 3.4, 1.2, 2.2, 4000, 20, 1.6, 2.2, 1, 'paint.yellow', 'trim.dark', 'trim.steel'),
        ('rough-terrain-forklift', 'Rough-terrain forklift', 4.8, 2.1, 2.7, 7500, 25, 1.4, 3.6, 1, 'paint.orange', 'trim.dark', 'trim.steel'),
        ('reach-forklift', 'Warehouse reach forklift', 2.6, 1.1, 2.3, 3000, 12, 1.4, 1.8, 1, 'paint.blue', 'trim.dark', 'trim.steel'),
    ]),
    ('skid-steer', 'Skid steer', 'land', R('machine', 0.6, 1.0, 'bucket', 0.25, 2, None, 'none'), [
        ('wheeled-skid-steer', 'Wheeled skid steer', 3.4, 1.8, 2.0, 3000, 15, 1.6, 1.4, 1, 'paint.yellow', 'trim.dark', 'trim.steel'),
        ('tracked-loader', 'Compact tracked loader', 3.6, 1.9, 2.1, 4200, 12, 1.3, 1.4, 1, 'paint.orange', 'trim.dark', 'trim.steel'),
    ]),
    ('excavator', 'Excavator', 'land', R('machine', 0.4, 0.55, 'arm', 0.12, 2, None, 'none'), [
        ('crawler-excavator', 'Crawler excavator', 9.5, 3.0, 3.0, 21000, 5, 0.6, 3.0, 1, 'paint.yellow', 'trim.dark', 'trim.steel'),
        ('mini-excavator', 'Mini excavator', 4.6, 1.8, 2.5, 3500, 4, 0.7, 1.6, 1, 'paint.orange', 'trim.dark', 'trim.steel'),
    ]),
    ('excavator-transport', 'Excavator transport', 'land', R('truck', 0.2, 0.9, 'lowboy', 0.13, 4, None, 'none'), [
        ('lowboy-tractor', 'Lowboy tractor-trailer', 18.0, 2.6, 3.4, 30000, 85, 0.7, 14.0, 2, 'paint.navy', 'trim.steel', 'mark.hivis'),
        ('tag-trailer-rig', 'Tag-trailer equipment rig', 13.0, 2.5, 3.2, 18000, 90, 0.9, 12.0, 2, 'paint.grey', 'trim.steel', 'mark.hivis'),
    ]),
    ('street-sweeper', 'Street sweeper', 'land', R('truck', 0.35, 0.85, 'broom', 0.16, 2, None, 'lightbar'), [
        ('mechanical-sweeper', 'Mechanical broom sweeper', 7.5, 2.4, 3.1, 11000, 60, 1.0, 7.0, 1, 'paint.white', 'trim.dark', 'mark.hivis'),
        ('compact-sweeper', 'Compact sweeper', 4.5, 1.3, 2.1, 3000, 40, 1.2, 3.8, 1, 'paint.green', 'trim.dark', 'mark.hivis'),
    ]),
    ('boom-lift', 'Self-propelled boom lift', 'land', R('machine', 0.3, 0.45, 'boom', 0.18, 2, None, 'none'), [
        ('telescopic-boom-lift', 'Telescopic boom lift', 8.5, 2.4, 2.6, 13000, 6, 0.5, 4.5, 2, 'paint.orange', 'trim.dark', 'trim.steel'),
    ]),
    ('utility-cart', 'Utility cart', 'land', R('car', 0.45, 0.9, 'bed', 0.16, 2, None, 'none'), [
        ('site-utility-cart', 'Site utility cart', 3.0, 1.4, 1.9, 700, 30, 2.0, 3.4, 2, 'paint.green', 'trim.dark', 'paint.tan'),
        ('campus-cart', 'Campus cart', 2.6, 1.2, 1.8, 450, 25, 2.2, 3.0, 2, 'paint.white', 'trim.dark', 'paint.tan'),
    ]),
    ('tractor', 'Utility tractor', 'land', R('machine', 0.35, 1.0, 'none', 0.38, 2, None, 'none'), [
        ('utility-tractor', 'Utility tractor', 3.8, 1.9, 2.6, 3200, 35, 1.2, 3.8, 1, 'paint.green', 'trim.dark', 'paint.yellow'),
    ]),
    ('bicycle', 'Bicycle', 'land', R('cycle', 0.0, 0.0, 'none', 0.33, 2, None, 'none'), [
        ('city-bicycle', 'City bicycle', 1.8, 0.6, 1.1, 16, 25, 1.6, 2.6, 1, 'paint.teal', 'trim.dark', 'trim.steel'),
        ('cargo-bicycle', 'Cargo bicycle', 2.5, 0.7, 1.1, 35, 20, 1.2, 3.2, 1, 'paint.orange', 'trim.dark', 'trim.steel'),
        ('road-bicycle', 'Road bicycle', 1.7, 0.45, 1.0, 9, 35, 2.0, 3.0, 1, 'paint.red', 'trim.dark', 'trim.steel'),
    ]),
    ('scooter', 'Scooter', 'land', R('cycle', 0.0, 0.0, 'rail', 0.22, 2, None, 'none'), [
        ('kick-scooter', 'Kick scooter', 1.1, 0.45, 1.15, 8, 15, 1.4, 1.8, 1, 'paint.black', 'trim.steel', 'trim.dark'),
        ('electric-scooter', 'Stand-up electric scooter', 1.15, 0.5, 1.2, 14, 25, 1.8, 2.0, 1, 'paint.grey', 'trim.dark', 'trim.steel'),
        ('moped', 'Step-through moped', 1.8, 0.7, 1.15, 90, 45, 2.2, 2.6, 2, 'paint.blue', 'trim.dark', 'trim.steel'),
    ]),
    # ------------------------------------------------------------ watercraft
    ('skiff', 'Skiff', 'water', R('hull', 0.0, 0.0, 'none', None, None, 'v', 'none'), [
        ('center-console-skiff', 'Center-console skiff', 5.5, 2.1, 1.4, 700, 55, 2.4, 9.0, 4, 'hull.white', 'trim.dark', 'paint.teal'),
        ('flats-skiff', 'Shallow-water skiff', 5.0, 1.9, 1.2, 550, 50, 2.4, 8.0, 3, 'hull.grey', 'trim.dark', 'paint.tan'),
    ]),
    ('jon-boat', 'Jon boat', 'water', R('hull', 0.0, 0.0, 'none', None, None, 'flat', 'none'), [
        ('jon-boat-small', 'Small jon boat', 3.7, 1.4, 0.9, 150, 25, 1.8, 6.0, 2, 'hull.green', 'trim.steel', 'trim.dark'),
        ('jon-boat-large', 'Large jon boat', 5.5, 1.9, 1.0, 350, 35, 1.8, 8.0, 4, 'hull.grey', 'trim.steel', 'trim.dark'),
    ]),
    ('airboat', 'Airboat', 'water', R('hull', 0.0, 0.0, 'deck', None, None, 'flat', 'fan'), [
        ('airboat', 'Airboat', 5.5, 2.4, 2.8, 900, 55, 2.6, 12.0, 6, 'hull.white', 'trim.dark', 'trim.steel'),
    ]),
    ('pontoon', 'Pontoon boat', 'water', R('hull', 0.0, 0.0, 'rail', None, None, 'pontoon', 'none'), [
        ('pontoon-small', 'Small pontoon boat', 6.5, 2.5, 1.9, 1100, 35, 1.4, 11.0, 8, 'hull.white', 'trim.steel', 'paint.navy'),
        ('pontoon-large', 'Large pontoon boat', 8.2, 2.6, 2.0, 1500, 40, 1.3, 13.0, 12, 'hull.white', 'trim.steel', 'paint.tan'),
    ]),
    ('tug', 'Tugboat', 'water', R('hull', 0.4, 0.55, 'deck', None, None, 'v', 'mast'), [
        ('harbor-tug', 'Harbor tug', 26.0, 10.0, 11.0, 450000, 22, 0.35, 45.0, 6, 'hull.red', 'hull.black', 'hull.white'),
        ('small-tug', 'Small tug', 16.0, 6.0, 8.0, 150000, 20, 0.4, 32.0, 4, 'hull.black', 'hull.red', 'hull.white'),
    ]),
    ('push-boat', 'Push boat', 'water', R('hull', 0.45, 0.7, 'deck', None, None, 'barge', 'knees'), [
        ('river-push-boat', 'River push boat', 22.0, 9.0, 12.0, 400000, 18, 0.3, 50.0, 6, 'hull.white', 'hull.black', 'hull.red'),
    ]),
    ('ferry', 'Ferry', 'water', R('hull', 0.55, 0.55, 'deck', None, None, 'barge', 'none'), [
        ('passenger-ferry', 'Passenger ferry', 30.0, 9.0, 8.0, 180000, 30, 0.3, 70.0, 150, 'hull.white', 'paint.navy', 'glass.tint'),
        ('vehicle-ferry', 'Vehicle ferry', 60.0, 16.0, 11.0, 1200000, 22, 0.15, 140.0, 300, 'hull.white', 'paint.green', 'glass.tint'),
    ]),
    ('fireboat', 'Fireboat', 'water', R('hull', 0.4, 0.6, 'deck', None, None, 'v', 'monitor'), [
        ('fireboat', 'Harbor fireboat', 20.0, 6.0, 7.0, 120000, 35, 0.5, 38.0, 8, 'paint.red', 'hull.white', 'trim.steel'),
    ]),
    ('patrol-boat', 'Patrol boat', 'water', R('hull', 0.35, 0.6, 'deck', None, None, 'v', 'lightbar'), [
        ('patrol-boat-small', 'Small patrol boat', 8.5, 2.8, 2.8, 4000, 60, 2.0, 16.0, 4, 'hull.grey', 'paint.navy', 'mark.stripe'),
        ('patrol-boat-large', 'Harbor patrol boat', 13.0, 4.0, 4.0, 12000, 55, 1.4, 24.0, 6, 'hull.white', 'paint.navy', 'mark.stripe'),
    ]),
    ('work-barge', 'Work barge', 'water', R('hull', 0.15, 0.4, 'deck', None, None, 'barge', 'crane'), [
        ('deck-barge', 'Deck barge', 30.0, 10.0, 3.0, 250000, 6, 0.1, 80.0, 2, 'hull.grey', 'hull.black', 'paint.yellow'),
        ('crane-barge', 'Crane work barge', 36.0, 14.0, 12.0, 450000, 5, 0.08, 100.0, 4, 'hull.grey', 'hull.black', 'paint.yellow'),
    ]),
    ('dredge-tender', 'Dredge tender', 'water', R('hull', 0.35, 0.6, 'deck', None, None, 'v', 'crane'), [
        ('dredge-tender', 'Dredge tender', 12.0, 4.0, 4.5, 15000, 25, 0.8, 24.0, 4, 'hull.white', 'paint.orange', 'paint.yellow'),
    ]),
    ('kayak', 'Kayak', 'water', R('paddle', 0.0, 0.0, 'none', None, None, 'tub', 'none'), [
        ('sit-on-kayak', 'Sit-on-top kayak', 3.6, 0.8, 0.4, 25, 8, 0.9, 3.0, 1, 'paint.yellow', 'trim.dark', 'paint.orange'),
    ]),
    ('canoe', 'Canoe', 'water', R('paddle', 0.0, 0.0, 'none', None, None, 'tub', 'none'), [
        ('touring-canoe', 'Touring canoe', 5.0, 0.9, 0.45, 30, 7, 0.7, 4.0, 2, 'paint.green', 'trim.dark', 'paint.tan'),
    ]),
]

# The only links to training seats: an entry family -> an EXISTING seat id in
# sims/registry/sims.json. Nothing else is linked.
SEAT_OF_FAMILY = {'forklift': 'forklift-run', 'excavator': 'excavator-trench', 'boom-lift': 'boom-lift'}
RECIPE_KEYS = ('archetype', 'cab_len', 'cab_h', 'body', 'wheel_r', 'axles', 'hull', 'extra')
ARCHETYPES = {'land': {'car', 'truck', 'bus', 'machine', 'cycle'}, 'water': {'hull', 'paddle'}}


def seat_links():
    sims = json.loads((ROOT / 'sims/registry/sims.json').read_text())
    tasks = json.loads((ROOT / 'tasks/registry/tasks.json').read_text())
    if 'sims' not in sims or 'tasks' not in tasks:
        die('sims.json has no sims or tasks.json has no tasks')
    by_id = {t['id']: t for t in tasks['tasks']}
    out = {}
    for fam, sid in SEAT_OF_FAMILY.items():
        if sid not in sims['sims']:
            die(f'family {fam} links seat {sid!r} which sims/registry/sims.json does not hold')
        s = sims['sims'][sid]
        for k in ('name', 'kind', 'halls'):
            if k not in s:
                die(f'seat {sid} has no {k!r}')
        tid = f'walkaround-{sid}'
        if tid not in by_id:
            die(f'seat {sid}: tasks registry has no {tid} to launch it from')
        href = by_id[tid]['launch']['href']
        if f'sim={sid}' not in href:
            die(f'seat {sid}: {tid} href {href!r} does not open that seat')
        out[fam] = {'id': sid, 'name': s['name'], 'kind': s['kind'],
                    'href': href, 'source': f'tasks/registry/tasks.json#{tid}.launch.href'}, \
            {'halls': list(s['halls']), 'source': f'sims/registry/sims.json#sims.{sid}.halls'}
    return out


def scan(obj, path, hits):
    pat = re.compile(r'\b(' + '|'.join(re.escape(w) for w in BRAND_DENYLIST) + r')\b', re.I)
    if isinstance(obj, dict):
        for k, v in obj.items():
            scan(v, f'{path}.{k}', hits)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan(v, f'{path}[{i}]', hits)
    elif isinstance(obj, str):
        for m in pat.finditer(obj):
            if m.group(1).lower() in BRAND_VALUE_EXEMPT and path.endswith(('.sim_seat.kind', '.honesty')):
                continue
            hits.append(f'{path}: {m.group(1)!r}')


def main():
    links = seat_links()
    families, entries, ids = [], [], set()
    for fam, fname, medium, recipe, rows in FAMILIES:
        if medium not in ARCHETYPES:
            die(f'family {fam}: medium {medium!r}')
        if tuple(recipe) != RECIPE_KEYS:
            die(f'family {fam}: recipe keys {tuple(recipe)} != {RECIPE_KEYS}')
        if recipe['archetype'] not in ARCHETYPES[medium]:
            die(f'family {fam}: archetype {recipe["archetype"]!r} is not a {medium} archetype')
        if (medium == 'land') != (recipe['hull'] is None) or (medium == 'land') != (recipe['wheel_r'] is not None):
            die(f'family {fam}: a land recipe has wheels and no hull, a water recipe a hull and no wheels')
        if not rows:
            die(f'family {fam} has no entries')
        seat, trades = links[fam] if fam in links else (None, None)
        families.append({'id': fam, 'name': fname, 'medium': medium, 'recipe': recipe,
                         'count': len(rows), 'sim_seat': seat['id'] if seat else None})
        for row in rows:
            if len(row) != 13:
                die(f'family {fam}: entry {row[:1]} has {len(row)} fields, needs 13')
            slug, name, L, W, H, mass, kmh, acc, turn, seats, pb, pt, pa = row
            eid = f'{fam}.{slug}'
            if eid in ids:
                die(f'duplicate id {eid}')
            ids.add(eid)
            for tok in (pb, pt, pa):
                if tok not in COLOURS:
                    die(f'{eid}: colour token {tok!r} is not in the paint table')
            for k, v in (('length', L), ('width', W), ('height', H), ('mass', mass), ('top', kmh),
                         ('accel', acc), ('turn', turn), ('seats', seats)):
                if not isinstance(v, (int, float)) or v <= 0:
                    die(f'{eid}: {k} must be a positive number, got {v!r}')
            if not (L >= W and L >= 0.5):
                die(f'{eid}: length {L} must be >= width {W}')
            entries.append({
                'id': eid, 'family': fam, 'name': name, 'medium': medium,
                'dims_m': {'length': L, 'width': W, 'height': H},
                'mass_kg': mass, 'top_speed_kmh': kmh, 'top_speed_ms': round(kmh / 3.6, 3),
                'accel_ms2': acc, 'turn_radius_m': turn, 'seats': seats,
                'palette': {'body': pb, 'trim': pt, 'accent': pa},
                'recipe': dict(recipe),
                'sim_seat': seat, 'trades': trades,
                'provenance': 'AUTHORED',
            })
    land = [e for e in entries if e['medium'] == 'land']
    water = [e for e in entries if e['medium'] == 'water']
    if len(land) != LAND_N:
        die(f'expected exactly {LAND_N} land vehicles, found {len(land)}')
    if len(water) != WATER_N:
        die(f'expected exactly {WATER_N} watercraft, found {len(water)}')
    for f in families:
        rs = {json.dumps(e['recipe'], sort_keys=True) for e in entries if e['family'] == f['id']}
        if len(rs) != 1:
            die(f'family {f["id"]}: entries disagree on the shared mesh recipe')
    stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    reg = {
        'pack': 'smartcitix-fleet',
        'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
        'source_stamp': stamp,
        'provenance': 'AUTHORED',
        'honesty': ('Generic vehicle and watercraft types only: no makes, models, brands or logos. Every '
                    'dimension, mass, speed, acceleration, turning and seat figure is AUTHORED - a plausible '
                    'arcade figure typed for a generic type, not measured and not the specification of any '
                    'real machine. Driving here is play, not training: only the entries linked to an existing '
                    'training seat open that seat, and no drive in the fleet enters a completion record.'),
        'units': {'dims_m': 'metres', 'mass_kg': 'kilograms', 'top_speed_kmh': 'km/h (AUTHORED)',
                  'top_speed_ms': 'm/s, DERIVED = top_speed_kmh / 3.6', 'accel_ms2': 'm/s^2',
                  'turn_radius_m': 'metres at low speed'},
        'colours': COLOURS,
        'counts': {'land': len(land), 'water': len(water), 'total': len(entries), 'families': len(families),
                   'linked_to_seat': sum(1 for e in entries if e['sim_seat'])},
        'families': families,
        'fleet': entries,
    }
    hits = []
    scan(reg, 'fleet', hits)
    if hits:
        die('brand words in the registry: ' + '; '.join(hits[:6]))
    text = json.dumps(reg, indent=1, sort_keys=True) + '\n'
    OUT.write_text(text)
    print(f'fleet: {len(land)} land + {len(water)} water = {len(entries)} entries in {len(families)} families; '
          f'{reg["counts"]["linked_to_seat"]} linked to a seat; stamp {stamp}; '
          f'sha256 {hashlib.sha256(text.encode()).hexdigest()[:16]}')


if __name__ == '__main__':
    main()
