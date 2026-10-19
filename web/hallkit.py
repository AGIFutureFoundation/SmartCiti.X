#!/usr/bin/env python3
"""Hall kit: one AUTHORED building archetype per union hall, unique on its campus.

    from hallkit import assign_archetypes, HALLKIT_JS, HallKitError, ARCH_KEYS

The user's ask (wave 7b): a campus drawn as one big shed with strips inside
reads as one building; each union hall should be its own, recognisable
building for its trade. This kit is the vocabulary for that and nothing
more. Every choice here is AUTHORED set design - a roof form, a cladding, a
glazing pattern, a door size class, a canopy, rooftop plant and a yard kit
chosen from what the trade FAMILY (the union registry's district) plausibly
builds with. None of it is a survey of a real hall; no address, real site
size or partner is implied (the hall plans already say "not a survey").

assign_archetypes(campuses, district_of) -> {slug: arch}
    campuses:    {campus_key: [hall slugs in registry order]}
    district_of: {slug: district key}
  Deterministic: each hall starts at the combination its own id hashes to
  (FNV-1a 32 over the slug) inside its family's combination space and steps
  forward past any combination another hall on the SAME campus already
  holds, so no two halls on a campus share an archetype. Fails closed: a
  district with no family row, a hall on two campuses, or a family whose
  space is smaller than its campus's hall count stops the build by name.

HALLKIT_JS is plain JS pasted into build_3d.py's module script (THREE in
scope). hkShell(a, W, D, H, lod, emit) calls emit(part, rgb, w, h, d, x, y, z,
rx, rz) once per box, so the host decides how to pool (the campus pools into
one vertex-coloured mesh per district, the hall view into a shell mesh and a
cutaway roof mesh). lod 0 = campus scale (few boxes), lod 1 = the walkable
full-scale hall.

    python3 web/hallkit.py --emit-json   prints the assignment for the live registries
"""
import itertools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


class HallKitError(Exception):
    pass


ROOFS = ('sawtooth', 'barrel', 'gable', 'parapet', 'monitor', 'highbay')
FACADES = ('brick', 'metal', 'precast', 'timber')
GLAZES = ('band', 'ribbon', 'clerestory', 'punched')
CANOPIES = ('flat', 'cantilever', 'portal')
PLANTS = ('hvac', 'exhaust', 'solar', 'louvre')
# roll-up door clear opening (w, h) metres by the plant class a trade moves
# through its doors - AUTHORED sizes, not a code or a standard
DOORS = {'heavy': (6.0, 6.0, 2), 'medium': (4.2, 4.5, 2), 'light': (3.0, 3.2, 1)}

# per trade family (= unions/registry/districts.json key): what the family's
# halls may be built as. AUTHORED; the kit's whole opinion lives here.
FAMILIES = {
    'structural': {'roofs': ('highbay', 'sawtooth', 'monitor'), 'facades': ('metal', 'precast', 'brick'),
                   'plants': ('exhaust', 'hvac', 'louvre'), 'door': 'heavy', 'yard': ('beams', 'mast')},
    'envelope':   {'roofs': ('gable', 'sawtooth', 'barrel'), 'facades': ('brick', 'timber', 'precast'),
                   'plants': ('hvac', 'louvre', 'solar'), 'door': 'medium', 'yard': ('pallets',)},
    'systems':    {'roofs': ('parapet', 'monitor', 'barrel'), 'facades': ('precast', 'metal', 'brick'),
                   'plants': ('hvac', 'exhaust', 'louvre'), 'door': 'medium', 'yard': ('ducts',)},
    'energy':     {'roofs': ('parapet', 'sawtooth', 'monitor'), 'facades': ('metal', 'precast'),
                   'plants': ('solar', 'hvac', 'louvre'), 'door': 'medium', 'yard': ('poles', 'transformer')},
    'earthworks': {'roofs': ('highbay', 'barrel', 'gable'), 'facades': ('metal', 'timber'),
                   'plants': ('exhaust', 'louvre'), 'door': 'heavy', 'yard': ('excavator', 'spoil')},
    'industry':   {'roofs': ('highbay', 'sawtooth', 'monitor'), 'facades': ('metal', 'brick'),
                   'plants': ('exhaust', 'hvac'), 'door': 'heavy', 'yard': ('tanks', 'piperack')},
    'transport':  {'roofs': ('barrel', 'highbay', 'sawtooth'), 'facades': ('metal', 'brick'),
                   'plants': ('louvre', 'exhaust'), 'door': 'heavy', 'yard': ('rail', 'bogie')},
    'control':    {'roofs': ('parapet', 'gable', 'monitor'), 'facades': ('precast', 'brick', 'timber'),
                   'plants': ('hvac', 'exhaust', 'louvre'), 'door': 'light', 'yard': ('drums', 'berm')},
}
ARCH_KEYS = ('family', 'roof', 'facade', 'glaze', 'canopy', 'plant', 'door', 'yard', 'seed', 'combo', 'sig')

for _f, _s in FAMILIES.items():
    assert set(_s['roofs']) <= set(ROOFS) and set(_s['facades']) <= set(FACADES), _f
    assert set(_s['plants']) <= set(PLANTS) and _s['door'] in DOORS, _f


def fnv1a(s):
    h = 0x811c9dc5
    for b in s.encode('utf-8'):
        h ^= b
        h = (h * 0x01000193) & 0xffffffff
    return h


def _space(fam):
    s = FAMILIES[fam]
    return list(itertools.product(s['roofs'], s['facades'], GLAZES, CANOPIES, s['plants']))


def assign_archetypes(campuses, district_of):
    out, home = {}, {}
    for ck, slugs in campuses.items():
        used = set()
        for sg in slugs:
            if sg in home:
                raise HallKitError(f'hall {sg} is on two campuses ({home[sg]}, {ck})')
            home[sg] = ck
            if sg not in district_of:
                raise HallKitError(f'hall {sg} on {ck} has no district')
            fam = district_of[sg]
            if fam not in FAMILIES:
                raise HallKitError(f'district {fam} (hall {sg}) has no archetype family in web/hallkit.py')
            space = _space(fam)
            n_fam = sum(1 for x in slugs if district_of.get(x) == fam)
            if n_fam > len(space):
                raise HallKitError(f'family {fam} has {len(space)} combinations for {n_fam} halls on {ck}')
            seed = fnv1a(sg)
            i = seed % len(space)
            while (fam,) + space[i] in used:
                i = (i + 1) % len(space)
            used.add((fam,) + space[i])
            roof, facade, glaze, canopy, plant = space[i]
            spec = FAMILIES[fam]
            dw, dh, dn = DOORS[spec['door']]
            combo = f'{fam}/{roof}/{facade}/{glaze}/{canopy}/{plant}'
            out[sg] = {
                'family': fam, 'roof': roof, 'facade': facade, 'glaze': glaze,
                'canopy': canopy, 'plant': plant,
                'door': {'cls': spec['door'], 'w': dw, 'h': dh, 'n': dn},
                'yard': spec['yard'][seed % len(spec['yard'])] if spec['door'] == 'heavy'
                or fam in ('energy', 'control') else None,
                'seed': seed, 'combo': combo, 'sig': f'{combo}#{seed:08x}',
            }
    return out


HALLKIT_JS = r"""/* ------------------------------------------------ hall kit (hallkit.py) ---
   One AUTHORED archetype per union hall: roof form, cladding, glazing,
   roll-up doors, canopy, rooftop plant, yard kit. Every box goes through
   emit(part, rgb, w, h, d, x, y, z, rx, rz) so the caller pools it; part is
   'shell' | 'roof' | 'yard'. The building spans x in [-W/2, W/2], z in
   [-D/2, D/2] (door at -z), walls up to y = H. lod 0 = campus, 1 = hall. */
const HK_FACADE = { brick: 0x8e4a36, metal: 0x7c8a94, precast: 0xc4bba8, timber: 0x9a6b43 };
const HK_ROOF = { brick: 0x4a4f55, metal: 0x5d6970, precast: 0x6b6f72, timber: 0x3f4a3c };
const HK_GLASS = 0x2a4656, HK_DOOR = 0xa9b0b4, HK_STEEL = 0x55606a, HK_YELLOW = 0xd9a520;
function hkRand(seed) {                       // mulberry32 off the hall's own seed
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function hkTint(hex, rnd) {                   // the hall's own shade of its cladding
  const c = new THREE.Color(hex), hsl = {};
  c.getHSL(hsl);
  c.setHSL(hsl.h + (rnd() - .5) * .04, Math.min(1, hsl.s * (.85 + rnd() * .3)),
    Math.min(.85, hsl.l * (.85 + rnd() * .3)));
  return c.getHex();
}
function hkShell(a, W, D, H, lod, emit) {
  if (!a || !a.roof || !HK_FACADE[a.facade])
    throw new Error('hallkit: the hall carries no archetype (D.halls[].arch)');
  const rnd = hkRand(a.seed);
  const s = W / 36;                           // 1 at the hall's real 36 m width
  const fac = hkTint(HK_FACADE[a.facade], rnd), rf = hkTint(HK_ROOF[a.facade], rnd);
  const e = (part, c, w, h, d, x, y, z, rx = 0, rz = 0) => emit(part, c, w, h, d, x, y, z, rx, rz);
  let top = H;
  const up = (y) => { if (y > top) top = y; };
  /* the roof form */
  if (a.roof === 'gable') {
    const ang = .38, half = W / 2 + .4 * s, rise = half * Math.tan(ang);
    for (const sx of [-1, 1])
      e('roof', rf, half / Math.cos(ang), .3 * s + .1, D + .6 * s, sx * half / 2, H + rise / 2, 0, 0, -sx * ang);
    up(H + rise + .3);
  } else if (a.roof === 'sawtooth') {
    const n = lod ? Math.max(3, Math.round(D / 9)) : Math.max(2, Math.min(3, Math.round(D / 6)));
    const p = D / n, ang = .5, rise = p * .55;
    for (let i = 0; i < n; i++) {
      const z0 = -D / 2 + i * p;
      e('roof', rf, W, .25 * s + .08, p / Math.cos(ang) * .98, 0, H + rise / 2, z0 + p / 2, ang);
      e('roof', HK_GLASS, W * .96, rise, .12, 0, H + rise / 2, z0 + p - .08);
    }
    up(H + rise + .3);
  } else if (a.roof === 'barrel') {
    const k = lod ? 7 : 3, phi = 1.1, r = (W / 2 + .3 * s) / Math.sin(phi / 2);
    const yc = H - r * Math.cos(phi / 2);
    for (let i = 0; i < k; i++) {
      const th = -phi / 2 + (i + .5) * phi / k;
      e('roof', rf, 2 * r * Math.sin(phi / (2 * k)) + .06, .25 * s + .08, D + .5 * s,
        r * Math.sin(th), yc + r * Math.cos(th), 0, 0, -th);
    }
    up(yc + r + .3);
  } else if (a.roof === 'monitor') {
    const mw = W * .3, mh = Math.max(1.2, H * .2);
    e('roof', rf, W + .3 * s, .25 * s + .08, D + .3 * s, 0, H + .1, 0);
    e('roof', fac, mw, mh, D * .8, 0, H + mh / 2 + .2, 0);
    e('roof', rf, mw + .8 * s, .2 * s + .08, D * .8 + .6 * s, 0, H + mh + .25, 0);
    if (lod) for (const sx of [-1, 1])
      e('roof', HK_GLASS, .1, mh * .6, D * .76, sx * (mw / 2 + .05), H + mh / 2 + .2, 0);
    up(H + mh + .4);
  } else if (a.roof === 'highbay') {
    const bw = W * .5, bh = Math.max(1.8, H * .38);
    e('roof', rf, W + .3 * s, .25 * s + .08, D + .3 * s, 0, H + .1, 0);
    e('roof', fac, bw, bh, D + .2, -W * .18, H + bh / 2, 0);
    e('roof', rf, bw + .6 * s, .22 * s + .08, D + .6 * s, -W * .18, H + bh + .1, 0);
    if (lod) {                                // the crane runway the high bay is for
      for (const sx of [-1, 1])
        e('roof', HK_YELLOW, .45, .6, D * .9, -W * .18 + sx * (bw / 2 - .6), H - .9, 0);
      e('roof', HK_YELLOW, bw - .8, .8, .7, -W * .18, H - .35, D * .12);
    }
    up(H + bh + .3);
  } else {                                    // parapet: a flat roof behind a parapet wall
    const ph = Math.max(.6, H * .1);
    e('roof', rf, W, .2, D, 0, H + .05, 0);
    e('shell', fac, W + .3, ph, .3, 0, H + ph / 2, -D / 2);
    if (lod) {
      e('shell', fac, W + .3, ph, .3, 0, H + ph / 2, D / 2);
      for (const sx of [-1, 1]) e('shell', fac, .3, ph, D, sx * W / 2, H + ph / 2, 0);
    }
    up(H + ph);
  }
  /* the cladding: a front header over the door line and, full size, the
     three closed faces, standing just proud of the walls the page draws */
  const headY = Math.min(H * .62, Math.max(DOORS_H(a) * s + .6 * s, H * .45));
  e('shell', fac, W + .2, H - headY, .3, 0, (H + headY) / 2, -D / 2 - .18);
  if (lod) {
    e('shell', fac, W + .2, H, .3, 0, H / 2, D / 2 + .18);
    for (const sx of [-1, 1]) e('shell', fac, .3, H, D + .2, sx * (W / 2 + .18), H / 2, 0);
    for (const sx of [-1, 1]) e('shell', 0x3b3f43, .4, .6, D + .8, sx * (W / 2 + .38), .3, 0);   // plinth
    e('shell', 0x3b3f43, W + .8, .6, .4, 0, .3, D / 2 + .38);
  }
  hkFacadeDetails(W, D, H, lod, e);   // FACADE w11: exterior details (civic recipe, facades/registry)
  /* glazing */
  const gz = (y, h) => {
    e('shell', HK_GLASS, W * .8, h, .12, 0, y, D / 2 + .36 * (lod ? 1 : .2));
    if (lod) for (const sx of [-1, 1]) e('shell', HK_GLASS, .12, h, D * .82, sx * (W / 2 + .36), y, 0);
  };
  if (a.glaze === 'band') gz(H * .58, Math.max(.6, H * .12));
  else if (a.glaze === 'ribbon') { gz(H * .42, Math.max(.4, H * .07)); if (lod) gz(H * .72, Math.max(.4, H * .07)); }
  else if (a.glaze === 'clerestory') gz(H * .86, Math.max(.5, H * .1));
  else if (lod) {                             // punched windows along each side
    const n = Math.max(3, Math.floor(D / 5));
    for (let i = 0; i < n; i++) for (const sx of [-1, 1])
      e('shell', HK_GLASS, .12, 1.4, 1.6, sx * (W / 2 + .36), H * .55, -D / 2 + (i + .5) * D / n);
  } else gz(H * .55, .5);
  /* roll-up doors, sized to the plant the trade moves (side walls in the
     hall, where the walk has no doorway to keep; the front at campus scale) */
  const dw = Math.min(a.door.w * s, W * .3), dh = Math.min(a.door.h * s, H * .8);
  if (lod) {
    for (let i = 0; i < a.door.n; i++) {
      const z = D / 2 - (i + 1) * D / (a.door.n + 1);
      for (const sx of [-1, 1]) {
        e('shell', HK_DOOR, .16, dh, dw, sx * (W / 2 + .4), dh / 2 + .3, z);
        e('shell', HK_STEEL, .3, .4, dw + .4, sx * (W / 2 + .42), dh + .5, z);   // coil box
        for (let k = 1; k < 5; k++)
          e('shell', HK_STEEL, .05, .06, dw * .98, sx * (W / 2 + .5), .3 + k * dh / 5, z);
      }
    }
  } else e('shell', HK_DOOR, dw, dh, .12, W * .28, dh / 2, -D / 2 - .36);
  /* the entrance canopy (and, full size, the posts a portal stands on) */
  const cw = lod ? 9 * s + 2 : W * .3, cd = lod ? 3.2 : 1.6 * s + .6, cy = lod ? 3.6 : Math.min(H * .5, 2.6);
  if (a.canopy === 'cantilever')
    e('shell', HK_STEEL, cw, .18, cd, 0, cy, -D / 2 - cd / 2 - .3, -.12);
  else e('shell', a.canopy === 'portal' ? fac : HK_STEEL, cw, .22, cd, 0, cy, -D / 2 - cd / 2 - .3);
  if (lod && a.canopy === 'portal')
    for (const sx of [-1, 1]) e('shell', fac, .5, cy, .5, sx * (cw / 2 - .3), cy / 2, -D / 2 - cd - .1);
  /* rooftop plant */
  const ry = a.roof === 'gable' || a.roof === 'barrel' ? null : H + .2;
  if (ry !== null) {
    const px = a.roof === 'highbay' ? W * .28 : W * .3;
    if (a.plant === 'hvac') {
      e('roof', 0xb8bec2, 3 * s + .6, 1.4 * s + .4, 2 * s + .5, px, ry + (1.4 * s + .4) / 2, D * .15);
      if (lod) e('roof', 0xb8bec2, 2.4, 1.2, 1.8, px, ry + .6, -D * .2);
    } else if (a.plant === 'exhaust') {
      e('roof', HK_STEEL, .9 * s + .3, 4 * s + 1, .9 * s + .3, px, ry + (4 * s + 1) / 2, D * .2);
      if (lod) e('roof', HK_STEEL, .7, 3.5, .7, px - 2.2, ry + 1.75, D * .2);
    } else if (a.plant === 'solar') {
      const rows = lod ? 4 : 2;
      for (let i = 0; i < rows; i++)
        e('roof', 0x1d2a3a, W * .4, .08, 1.6 * s + .5, -W * .15, ry + .5, -D * .3 + i * D * .6 / Math.max(1, rows - 1), -.3);
    } else e('roof', 0x8d969b, 2.6 * s + .6, 1.1 * s + .3, 1.2 * s + .4, px, ry + .5, 0);
  }
  /* the yard kit, for the families that work outdoors with heavy plant;
     at the back of a campus lot, beside the hall at full size */
  if (a.yard) {
    const yx = lod ? W / 2 + 7 : 0, yz = lod ? D * .15 : D / 2 + 1.6;
    const Y = (c, w, h, d, dx, y, dz, rx = 0, rz = 0) => e('yard', c, w, h, d, yx + dx, y, yz + dz, rx, rz);
    const k = lod ? 1 : .35;
    switch (a.yard) {
      case 'beams': for (let i = 0; i < (lod ? 4 : 2); i++) Y(0x6a4a3a, 9 * k, .45, .35, 0, .25 + i * .45, 0); break;
      case 'mast': Y(HK_YELLOW, .8 * k + .2, 12 * k, .8 * k + .2, 0, 6 * k, 0); if (lod) Y(HK_YELLOW, 10, .6, .6, 3, 12, 0); break;
      case 'pallets': for (let i = 0; i < (lod ? 4 : 2); i++) Y(0xa07a4a, 1.2 * k + .3, 1 * k, 1.2 * k + .3, (i - 1.5) * 1.8 * k, .5 * k, 0); break;
      case 'ducts': Y(0x9aa3a8, 6 * k, .8 * k, .8 * k, 0, .4 * k, 0); if (lod) Y(0x9aa3a8, 6, .8, .8, 0, 1.2, 0); break;
      case 'poles': for (let i = 0; i < (lod ? 3 : 2); i++) Y(0x5a4632, 10 * k, .35, .35, 0, .2 + i * .36, 0); break;
      case 'transformer': Y(0x6f8f7a, 2.2 * k + .3, 2 * k + .3, 1.6 * k + .3, 0, (2 * k + .3) / 2, 0); break;
      case 'excavator': Y(HK_YELLOW, 3 * k + .4, 2 * k + .3, 2.2 * k + .3, 0, (2 * k + .3) / 2 + .4 * k, 0);
        if (lod) { Y(0x333333, 4, .8, 3, 0, .4, 0); Y(HK_YELLOW, .5, .5, 5, 0, 3, -3.2, .5); } break;
      case 'spoil': Y(0x6b5a44, 4 * k + .5, 1.6 * k, 3 * k + .5, 0, .8 * k, 0, 0, .25); break;
      case 'tanks': Y(0x9fa8ad, 2.6 * k + .4, 4 * k + .5, 2.6 * k + .4, 0, (4 * k + .5) / 2, 0); if (lod) Y(0x9fa8ad, 2.6, 4, 2.6, 3.4, 2, 0); break;
      case 'piperack': Y(HK_STEEL, 8 * k, .3, 1.8 * k + .2, 0, 3 * k, 0); if (lod) for (const dx of [-3.6, 3.6]) Y(HK_STEEL, .3, 3, .3, dx, 1.5, 0); break;
      case 'rail': for (const dz of [-.75, .75]) Y(0x6b6f72, 12 * k, .15, .12, 0, .1, dz); break;
      case 'bogie': Y(0x3a3f44, 2.6 * k + .3, 1 * k + .2, 2 * k + .3, 0, (1 * k + .2) / 2, 0); break;
      case 'drums': for (let i = 0; i < (lod ? 4 : 2); i++) Y(0x2f6f9a, .6 * k + .2, .9 * k + .2, .6 * k + .2, (i - 1.5) * .9 * k, (.9 * k + .2) / 2, 0); break;
      case 'berm': Y(0x5f6a48, 5 * k + .5, .5 * k + .1, 3 * k + .5, 0, .25 * k, 0); break;
      default: throw new Error('hallkit: unknown yard kit ' + a.yard);
    }
  }
  return { top, headY };
}
function DOORS_H(a) { return a.door.h; }
/* FACADE w11: exterior details from the AUTHORED civic recipe (facades/registry/facades.json; hallkit.py checks this
   literal against the registry at import) */
const HK_CIVIC = {"cornice": {"depth_m": 0.6, "h_m": 0.7, "hex": 13616820, "out_m": 0.0, "y_m": -0.7}, "downpipes": {"depth_m": 0.16, "h_m": -0.5, "hex": 9213082, "out_m": 0.08, "spacing_m": 18.0, "width_m": 0.16, "y_m": 0.0}, "entry-steps": {"depth_m": 2.4, "h_m": 0.6, "hex": 13616820, "out_m": 0.0, "width_m": 8.0, "y_m": 0.0}, "piers": {"depth_m": 0.4, "h_m": -0.7, "hex": 13616820, "out_m": 0.15, "spacing_m": 6.0, "width_m": 0.9, "y_m": 0.0}};
function hkFacadeDetails(W, D, H, lod, e) {
  const C = HK_CIVIC, fz = -D / 2 - .33;           // the cladding's outer face on the door side
  const co = C['cornice'], pi = C['piers'], dp = C['downpipes'], st = C['entry-steps'];
  e('shell', co.hex, W + .6, co.h_m, co.depth_m, 0, H + co.y_m + co.h_m / 2, fz - co.depth_m / 2);
  const ph = H + pi.h_m, n = lod ? Math.max(2, Math.floor(W / pi.spacing_m) + 1) : 2;
  for (let i = 0; i < n; i++) {
    const x = -W / 2 + pi.width_m / 2 + (W - pi.width_m) * i / (n - 1);
    if (Math.abs(x) < 5.5) continue;              // keep the entrance and its canopy clear
    e('shell', pi.hex, pi.width_m, ph, pi.depth_m, x, ph / 2, fz - pi.out_m - pi.depth_m / 2);
  }
  if (lod) for (const sx of [-1, 1]) e('shell', dp.hex, dp.width_m, H + dp.h_m, dp.depth_m, sx * (W / 2 - .15), (H + dp.h_m) / 2, fz - dp.out_m - dp.depth_m / 2);
  else e('shell', st.hex, Math.min(st.width_m, W * .3), st.h_m, st.depth_m, 0, st.h_m / 2, fz - st.depth_m / 2);   // the walk keeps its threshold flat at full size
}
/* one pooled, vertex-coloured material for every archetype box, page-wide */
let hkMatShared = null;
function hkMat() {
  if (!hkMatShared) {
    hkMatShared = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .72, metalness: .12 });
    hkMatShared.userData.shared = true;
  }
  return hkMatShared;
}
const _hkM = new THREE.Matrix4(), _hkE = new THREE.Euler(), _hkC = new THREE.Color();
function hkBoxGeo(c, w, h, d, x, y, z, rx, rz) {
  const ge = new THREE.BoxGeometry(Math.max(.02, w), Math.max(.02, h), Math.max(.02, d));
  _hkE.set(rx, 0, rz);
  ge.applyMatrix4(_hkM.makeRotationFromEuler(_hkE).setPosition(x, y, z));
  _hkC.setHex(c);
  const n = ge.attributes.position.count, col = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { col[i * 3] = _hkC.r; col[i * 3 + 1] = _hkC.g; col[i * 3 + 2] = _hkC.b; }
  ge.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return ge;
}
/* the union's name on its own building (full size only): one textured plane */
function hkSign(text, w, h) {
  const cv = document.createElement('canvas'); cv.width = 1024; cv.height = 160;
  const g = cv.getContext('2d');
  g.fillStyle = '#1d2327'; g.fillRect(0, 0, 1024, 160);
  g.fillStyle = '#f2efe6'; g.font = '600 84px system-ui, sans-serif';
  g.textAlign = 'center'; g.textBaseline = 'middle';
  let fs = 84;
  while (g.measureText(text).width > 960 && fs > 30) { fs -= 4; g.font = `600 ${fs}px system-ui, sans-serif`; }
  g.fillText(text, 512, 84);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex }));
  m.userData.hkSign = text;
  return m;
}
"""


# BEGIN FACADE w11 (FACADE·Exteriors & Signs): exterior details on every hall shell - cornice, piers, corner
# downpipes and (campus scale) an entry stoop - read from the AUTHORED civic recipe in facades/registry/facades.json
# and emitted as more boxes into the host's pooled vertex-coloured mesh (0 extra draw calls). The front is local -z
# (the door face). Fails closed: a missing registry or component stops the build by name.
def _civic_recipe():
    reg_path = ROOT / 'facades' / 'registry' / 'facades.json'
    if not reg_path.exists():
        raise HallKitError('facades/registry/facades.json missing: run python3 facades/build.py (hall exterior details)')
    reg = json.loads(reg_path.read_text())
    comps = {c['id']: c for c in reg['styles']['civic']['components']}
    out = {}
    for k in ('cornice', 'piers', 'entry-steps', 'downpipes'):
        if k not in comps:
            raise HallKitError(f'facades civic recipe has no component {k!r} (hall exterior details)')
        c = comps[k]
        out[k] = {f: c[f] for f in ('y_m', 'h_m', 'depth_m', 'out_m')}
        for f in ('width_m', 'spacing_m'):
            if f in c:
                out[k][f] = c[f]
        out[k]['hex'] = int(reg['colour_categories'][c['colour_category']]['hex'][1:], 16)
    return out


_HK_CIVIC_LIVE = 'const HK_CIVIC = ' + json.dumps(_civic_recipe(), sort_keys=True) + ';'
if HALLKIT_JS.count(_HK_CIVIC_LIVE) != 1:
    raise HallKitError('web/hallkit.py: the HK_CIVIC literal in HALLKIT_JS is stale against facades/registry civic recipe - '
                       'paste: ' + _HK_CIVIC_LIVE)
# END FACADE w11

def _live():
    halls = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
    dreg = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']
    creg = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
    district_of = {sg: k for k, d in dreg.items() for sg in d['halls']}
    known = {h['slug'] for h in halls}
    camp = {k: [sg for sg in c['halls'] if sg in known] for k, c in creg.items()}
    return assign_archetypes(camp, district_of)


if __name__ == '__main__':
    if '--emit-json' in sys.argv:
        print(json.dumps(_live(), indent=1, sort_keys=True))
    else:
        a = _live()
        from collections import Counter
        print(len(a), 'halls;', dict(Counter(v['roof'] for v in a.values())))
