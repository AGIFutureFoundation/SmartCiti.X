#!/usr/bin/env python3
"""Look kit (wave 19): ONE physically based look for the 3D campus, the parish / Bay and the wilds pages.

    from lookkit import look_js, LookError

Everything here is AUTHORED by rule - a stated choice, not a measurement of any real place or material sample.

1. Renderer output. ACES Filmic tone mapping, sRGB output colour space, and a stated exposure per page (EXPOSURE).
   The 3D campus page already ran ACES at 1.12; that number is kept, so its frame does not shift. The worlds pages
   ran with no tone mapping; they get ACES at 0.95.
2. Sun and sky light (SUN_RULE), from the sun's elevation h in degrees above the horizon:
     colour temperature  CCT(h)  = 2000 K + 3800 K x (1 - exp(-h / 12))           (low sun warm, high sun ~5800 K)
     sun intensity       I_sun   = 2.6 x sin(h) x 0.7^(AM^0.678) / 0.7, AM = 1 / sin(h)
                                   (the Meinel air-mass attenuation, scaled so a zenith sun is 2.6)
     sky intensity       I_sky   = 1.1 x (0.45 + 0.55 x sin(h))
     sky colour          a fixed 8000 K; the hemisphere's ground colour stays the page's own ground albedo.
   Kelvin to RGB is the Tanner Helland fit (sRGB, 0-255). The worlds pages apply the rule to their one sun and one
   hemisphere at load. The 3D campus page does NOT: its hour and weather registry (sky/) already sets the sun and sky
   per phase, and that registry stays the rule there (the kit records which rule a page uses: 'kit' or 'registry').
3. Surface classes (CLASSES): roughness / metalness / environment-light share for glass, metal, masonry,
   paving (asphalt and concrete), foliage and water. A page names which of its materials belong to which class; a
   material the page does not name keeps its own numbers. Only uniforms change, so draw calls and triangles do not.
   On the worlds pages the land, buildings and trees are diffuse (Lambert) materials, roughness 1 / metalness 0 by
   definition, and stay that way: converting the whole ground to a per-pixel PBR shader would be paid on every
   pixel of a software-rasterised frame. Their one water material becomes a standard (PBR) material of the water
   class: the same draw call, a different shader.

The page carries only the neutral marker LOOK-KIT and the hook window.__look().
"""
import json
import math


class LookError(Exception):
    pass


TONE = {'tone_mapping': 'ACESFilmic', 'output_color_space': 'srgb'}
EXPOSURE = {'campus3d': 1.12, 'worlds': 0.95}
SUN_RULE = {'cct_low_k': 2000.0, 'cct_span_k': 3800.0, 'cct_e_deg': 12.0,
            'sun_zenith_i': 2.6, 'meinel_t': 0.7, 'meinel_p': 0.678,
            'sky_i': 1.1, 'sky_base': 0.45, 'sky_slope': 0.55, 'sky_k': 8000.0}
# roughness, metalness, env = share of the image-based (sky) light the material takes where a page has one
CLASSES = {
    'glass':   {'roughness': 0.05, 'metalness': 0.0, 'env': 1.0},
    'metal':   {'roughness': 0.35, 'metalness': 0.8, 'env': 1.0},
    'masonry': {'roughness': 0.9,  'metalness': 0.0, 'env': 0.6},
    'paving':  {'roughness': 0.93, 'metalness': 0.0, 'env': 0.5},
    'foliage': {'roughness': 0.8,  'metalness': 0.0, 'env': 0.5},
    'water':   {'roughness': 0.06, 'metalness': 0.0, 'env': 1.0},
}
# per page: the material -> class map (names as the page's own JS knows them) and which sun rule applies
PAGES = {
    'campus3d': {'exposure': 'campus3d', 'sun': 'registry',
                 'map': {'win': 'glass', 'metal': 'metal', 'brick': 'masonry', 'block': 'masonry',
                         'slab': 'masonry', 'land': 'paving', 'road': 'paving', 'drive': 'paving',
                         'walkway': 'paving', 'veg': 'foliage', 'grass': 'foliage', 'water': 'water'}},
    'parishes': {'exposure': 'worlds', 'sun': 'kit', 'map': {'matWater': 'water'}},
    'wilds':    {'exposure': 'worlds', 'sun': 'kit', 'map': {'matWater': 'water'}},
}
SAMPLE_DEG = (5.0, 20.0, 38.3, 53.2, 90.0)


def kelvin_rgb(k):
    """Tanner Helland's fit, sRGB 0-255 ints."""
    t = k / 100.0
    r = 255.0 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    g = (99.4708025861 * math.log(t) - 161.1195681661) if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    b = 255.0 if t >= 66 else (0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(int(round(min(255.0, max(0.0, v)))) for v in (r, g, b))


def sun_rule(h_deg):
    if not 0 < h_deg <= 90:
        raise LookError(f'lookkit: sun elevation {h_deg} is not in (0, 90]')
    R = SUN_RULE
    s = math.sin(math.radians(h_deg))
    cct = R['cct_low_k'] + R['cct_span_k'] * (1 - math.exp(-h_deg / R['cct_e_deg']))
    am = 1 / s
    sun_i = R['sun_zenith_i'] * s * R['meinel_t'] ** (am ** R['meinel_p']) / R['meinel_t']
    sky_i = R['sky_i'] * (R['sky_base'] + R['sky_slope'] * s)
    hx = lambda c: (c[0] << 16) | (c[1] << 8) | c[2]  # noqa: E731
    return {'h': h_deg, 'cct': round(cct), 'sunI': round(sun_i, 4), 'skyI': round(sky_i, 4),
            'sunHex': hx(kelvin_rgb(cct)), 'skyHex': hx(kelvin_rgb(R['sky_k']))}


def _check():
    for k in ('tone_mapping', 'output_color_space'):
        if k not in TONE:
            raise LookError(f'lookkit: TONE has no {k!r}')
    for name, c in CLASSES.items():
        for k in ('roughness', 'metalness', 'env'):
            if k not in c or not 0 <= c[k] <= 1:
                raise LookError(f'lookkit: class {name!r} {k} missing or outside [0, 1]')
    for pid, p in PAGES.items():
        if p['exposure'] not in EXPOSURE or p['sun'] not in ('kit', 'registry'):
            raise LookError(f'lookkit: page {pid!r} names an unknown exposure or sun rule')
        bad = sorted(set(p['map'].values()) - set(CLASSES))
        if bad:
            raise LookError(f'lookkit: page {pid!r} maps to unknown classes {bad}')


def look_js(page_id):
    """The page JS block (neutral marker LOOK-KIT). Needs THREE in scope; defines LOOK, lookRenderer, lookSun,
    lookMat, lookMats and window.__look."""
    _check()
    if page_id not in PAGES:
        raise LookError(f'lookkit: no page {page_id!r} (known: {sorted(PAGES)})')
    p = PAGES[page_id]
    cfg = {'page': page_id, 'tone': TONE, 'exposure': EXPOSURE[p['exposure']], 'sunRule': p['sun'],
           'rule': SUN_RULE, 'classes': CLASSES, 'map': p['map'],
           'samples': [sun_rule(h) for h in SAMPLE_DEG]}
    blob = json.dumps(cfg, sort_keys=True, separators=(',', ':')).replace('</', '<\\/')
    return ('/* LOOK-KIT BEGIN: one physically based look - ACES Filmic, sRGB out, a stated exposure, the sun and sky '
            'by an AUTHORED rule, roughness and metalness per surface class (AUTHORED, not measured) */\n'
            f'const LOOK = {blob};\n' + _JS + '/* LOOK-KIT END */\n')


_JS = r"""const lookStat = { r: null, sun: null, applied: {} };
function lookRenderer(r) {
  if (LOOK.tone.tone_mapping !== 'ACESFilmic' || LOOK.tone.output_color_space !== 'srgb') throw new Error('LOOK-KIT: unknown output');
  r.toneMapping = THREE.ACESFilmicToneMapping;
  r.outputColorSpace = THREE.SRGBColorSpace;
  r.toneMappingExposure = LOOK.exposure;
  lookStat.r = r;
}
function lookKelvin(k) {
  const t = k / 100, c = (v) => Math.round(Math.min(255, Math.max(0, v)));
  const r = t <= 66 ? 255 : 329.698727446 * Math.pow(t - 60, -0.1332047592);
  const g = t <= 66 ? 99.4708025861 * Math.log(t) - 161.1195681661 : 288.1221695283 * Math.pow(t - 60, -0.0755148492);
  const b = t >= 66 ? 255 : (t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307);
  return (c(r) << 16) | (c(g) << 8) | c(b);
}
function lookSunRule(h) {
  if (!(h > 0 && h <= 90)) throw new Error('LOOK-KIT: sun elevation ' + h + ' is not in (0, 90]');
  const R = LOOK.rule, s = Math.sin(h * Math.PI / 180);
  const cct = R.cct_low_k + R.cct_span_k * (1 - Math.exp(-h / R.cct_e_deg));
  const sunI = R.sun_zenith_i * s * Math.pow(R.meinel_t, Math.pow(1 / s, R.meinel_p)) / R.meinel_t;
  const skyI = R.sky_i * (R.sky_base + R.sky_slope * s);
  return { h: h, cct: Math.round(cct), sunI: Math.round(sunI * 1e4) / 1e4, skyI: Math.round(skyI * 1e4) / 1e4,
           sunHex: lookKelvin(Math.round(cct)), skyHex: lookKelvin(R.sky_k) };
}
function lookSun(sun, hemi) {
  if (LOOK.sunRule !== 'kit') throw new Error('LOOK-KIT: this page keeps its registry sun');
  const d = sun.position.clone().sub(sun.target.position).normalize();
  const h = Math.asin(d.y) * 180 / Math.PI, s = lookSunRule(h);
  sun.color.setHex(s.sunHex); sun.intensity = s.sunI;
  hemi.color.setHex(s.skyHex); hemi.intensity = s.skyI;
  lookStat.sun = { h: Math.round(h * 10) / 10, cct: s.cct, sunI: s.sunI, skyI: s.skyI,
                   sunHex: sun.color.getHexString(), skyHex: hemi.color.getHexString() };
}
function lookMat(m, cls) {
  const c = LOOK.classes[cls];
  if (!c) throw new Error('LOOK-KIT: no surface class ' + cls);
  if (!m || !('roughness' in m) || !('metalness' in m)) throw new Error('LOOK-KIT: a ' + cls + ' material has no roughness / metalness');
  m.roughness = c.roughness; m.metalness = c.metalness;
  if ('envMapIntensity' in m) m.envMapIntensity = c.env;
  (lookStat.applied[cls] = lookStat.applied[cls] || []).push(m);
}
function lookMats(table) {
  for (const k of Object.keys(LOOK.map)) {
    if (!table[k]) throw new Error('LOOK-KIT: the page has no material ' + k);
    lookMat(table[k], LOOK.map[k]);
  }
}
window.__look = () => {
  const r = lookStat.r, cls = {};
  for (const k of Object.keys(lookStat.applied))
    cls[k] = lookStat.applied[k].map((m) => ({ roughness: m.roughness, metalness: m.metalness }));
  return { page: LOOK.page, sunRule: LOOK.sunRule,
           tone: r && r.toneMapping === THREE.ACESFilmicToneMapping ? 'ACESFilmic' : (r ? String(r.toneMapping) : null),
           space: r ? r.outputColorSpace : null, exposure: r ? r.toneMappingExposure : null,
           sun: lookStat.sun, classes: cls, mapped: Object.keys(LOOK.map).length };
};
"""

if __name__ == '__main__':
    _check()
    for h in SAMPLE_DEG:
        print(sun_rule(h))
