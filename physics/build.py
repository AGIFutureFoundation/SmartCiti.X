#!/usr/bin/env python3
"""Physics coefficients for the arcade physics in web/physkit.py and the crash
response in web/fleetkit.py.

Every figure here is AUTHORED for play except world.gravity (standard gravity,
RECORDED, used rounded to 9.81 m/s^2). None of it is a measurement of a real
vehicle, person, building or body of water; crashes are play, not a crash test,
and nothing here is safety or engineering advice.

    python3 physics/build.py          writes physics/registry/physics.json
    python3 physics/build.py --check  fails if the file on disk is stale
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'registry' / 'physics.json'

HONESTY = ('Physics is an arcade approximation: gravity 9.81 m/s^2; friction, restitution, mass, buoyancy, '
           'drag and damage are AUTHORED. Crashes are play - not a crash test, not safety or engineering '
           'advice. Vehicles never strike people, NPCs, pets or animals.')


def A(value, unit, note):
    return {'value': value, 'unit': unit, 'provenance': 'AUTHORED', 'note': note}


COEFFS = {
    'world': {
        'gravity': {'value': 9.81, 'unit': 'm/s^2', 'provenance': 'RECORDED',
                    'note': 'standard acceleration of gravity 9.80665 m/s^2, used rounded to 9.81'},
        'max_substep_frac': A(0.5, 'avatar radii', 'no sub-step moves more than this fraction of the radius'),
    },
    'avatar': {
        'radius': A(0.3, 'm', 'collision circle of the walker'),
        'height': A(1.75, 'm', 'capsule height for box overlap'),
        'step_up': A(0.25, 'm', 'tallest ledge (curb) walked onto without a jump'),
        'jump_speed': A(4.2, 'm/s', 'take-off speed (about 0.9 m apex under 9.81)'),
        'air_control': A(0.35, 'fraction', 'share of steering kept while airborne'),
        'ground_accel': A(30.0, 'm/s^2', 'how fast walking speed follows input'),
        'max_fall_speed': A(55.0, 'm/s', 'terminal speed cap (arcade)'),
        'land_event_speed': A(4.0, 'm/s', 'falls faster than this emit a land event'),
    },
    'water': {
        'wade_min': A(0.1, 'm', 'water depth at the feet from which the walker wades'),
        'swim_depth': A(1.0, 'm', 'water depth at the feet from which the walker swims (= PARISH world.json wade_max_depth_m)'),
        'climb_out_m': A(0.6, 'm', 'tallest bank above the water surface a wader or swimmer climbs out onto'),
        'wade_speed': A(0.6, 'fraction', 'walking speed multiplier while wading'),
        'swim_speed': A(0.45, 'fraction', 'walking speed multiplier while swimming'),
        'float_depth': A(1.35, 'm', 'a swimmer floats with the feet this far under the surface (head stays above)'),
        'float_rate': A(3.0, '1/s', 'how fast a swimmer eases to the float depth'),
        'splash_speed': A(2.0, 'm/s', 'entering water faster than this (down or across) splashes'),
        'body_buoyancy': A(1.6, 'fraction of g', 'upward push on a submerged generic body'),
        'water_drag': A(2.5, '1/s', 'velocity damping in water for bodies'),
    },
    'body': {
        'restitution': A(0.35, 'ratio', 'bounce of a generic rigid body'),
        'friction': A(0.6, 'ratio', 'tangential damping on contact'),
        'air_drag': A(0.02, '1/s', 'linear damping in air'),
        'sleep_speed': A(0.05, 'm/s', 'below this at rest a body sleeps'),
    },
    'crash': {
        'restitution_vehicle': A(0.25, 'ratio', 'vehicle-vs-vehicle bounce'),
        'restitution_static': A(0.15, 'ratio', 'vehicle-vs-building/curb/barrier bounce'),
        'spin_gain': A(1.0, 'ratio', 'scales the yaw spin an off-centre impulse gives'),
        'max_spin': A(2.5, 'rad/s', 'largest yaw spin a crash leaves (arcade cap)'),
        'slide_decay': A(2.2, '1/s', 'knock-back slide and yaw spin fade'),
        'dent_min_ms': A(2.0, 'm/s', 'impacts slower than this leave no dent'),
        'dent_per_ms': A(0.04, '1/(m/s)', 'dent added per m/s of impact speed above dent_min_ms'),
        'crumple_max': A(0.12, 'fraction', 'largest drawn squash of length at dent 1 (display only)'),
        'wheel_step': A(0.2, 'm', 'boxes this low or lower are driven over (curbs), taller ones are struck'),
        'drop_m': A(0.5, 'm', 'ground falling away by more than this under a moving vehicle makes it airborne'),
        'tumble_rate': A(0.08, 'rad/s per m/s', 'pitch/roll rate per m/s of speed when leaving a drop'),
        'reset_s': A(6.0, 's', 'a crashed or blocked traffic agent resets after this long'),
        'yield_margin': A(1.5, 'm', 'extra clearance a vehicle keeps from any person, NPC, pet or animal'),
        'smoke_min_ms': A(3.0, 'm/s', 'impacts faster than this puff smoke'),
    },
}


def build():
    stamp = hashlib.sha256((HERE / 'build.py').read_bytes()).hexdigest()[:16]
    for g, group in COEFFS.items():
        for k, c in group.items():
            for f in ('value', 'unit', 'provenance', 'note'):
                if f not in c:
                    raise KeyError(f'physics coeffs.{g}.{k} has no {f}')
            if c['provenance'] not in ('AUTHORED', 'RECORDED'):
                raise ValueError(f'physics coeffs.{g}.{k} provenance {c["provenance"]}')
    return {
        'pack': 'physics',
        'source_stamp': stamp,
        'honesty': HONESTY,
        'units': 'SI: metres, seconds, kilograms; angles in radians',
        'provenance_rule': 'world.gravity RECORDED (standard gravity); every other coefficient AUTHORED for play',
        'pedestrian_classes': ['person', 'npc', 'pet', 'animal'],
        'coeffs': COEFFS,
    }


if __name__ == '__main__':
    text = json.dumps(build(), indent=1, ensure_ascii=False) + '\n'
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            raise SystemExit('physics/registry/physics.json is stale: run python3 physics/build.py')
        print('physics.json is current')
    else:
        OUT.write_text(text)
        n = sum(len(g) for g in COEFFS.values())
        print(f'wrote {OUT.relative_to(HERE.parent)}: {n} coefficients')
