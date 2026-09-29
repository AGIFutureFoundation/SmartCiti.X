"""
patternkit - embeddable procedural exterior textures (PATTERN, wave 11; contract $SP/PATTERN_CONTRACT.md v1).

Reads surfaces/registry/exterior.json (built by surfaces/build.py from surfaces/exterior.py) and
hands a page one inline script. No image file is shipped: every texture is drawn at runtime onto a
power-of-two canvas from a recipe's parameters. Python API:
  EXT                              the loaded registry (fails closed on missing fields)
  PK_JS                            the kit source; defines `const PatternKit` (no data)
  data_json(recipe_ids=None, family_ids=None)   compact JSON of the recipes/colours a page needs
  inline_script(recipe_ids=None, family_ids=None)  PK_JS + PatternKit.load(<data>) for a <script>
  es_module(recipe_ids=None, family_ids=None)      the same as an ES module (export default PatternKit)
  recipe_ids(use=None) / family_ids()           ids, in registry order
  honesty_line()                                the provenance line to render once per page
JS API (PatternKit.*): load, version, recipe, recipes, families, colour, colours, shade, sizeFor,
isPow2, hintsFor, repeatFor, draw, texture, cacheSize, clearCache, rng.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / 'surfaces' / 'registry' / 'exterior.json'
VERSION = '1'
R_FIELDS = ('family', 'name', 'kind', 'params', 'tile_m', 'joint_shade', 'uses', 'why')


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise KeyError(f'patternkit: {where} has no "{k}"')
    return d[k]


def _load():
    if not REG.exists():
        raise SystemExit('patternkit: surfaces/registry/exterior.json is missing - run python3 surfaces/build.py')
    reg = json.loads(REG.read_text())
    for k in ('recipes', 'colour_families', 'quality_sizes', 'kinds', 'landuse_hints', 'provenance',
              'honesty', 'source_stamp'):
        _need(reg, k, 'exterior.json')
    for rid, r in reg['recipes'].items():
        for f in R_FIELDS:
            _need(r, f, rid)
    for fid, f in reg['colour_families'].items():
        for k in ('name', 'why', 'colours', 'lettering'):
            _need(f, k, fid)
        for c in f['colours']:
            for k in ('id', 'name', 'hex', 'use', 'label_ink', 'label_ratio'):
                _need(c, k, fid)
    return reg


EXT = _load()


def recipe_ids(use=None):
    return [k for k, r in EXT['recipes'].items() if use is None or use in r['uses']]


def family_ids():
    return list(EXT['colour_families'])


def honesty_line():
    return ('Patterns and colours: AUTHORED - drawn at runtime from parameters in surfaces/exterior.py; '
            'no photograph, supplier swatch, paint brand or standard colour value.')


def data_json(recipe_ids=None, family_ids=None):
    rids = list(EXT['recipes']) if recipe_ids is None else list(recipe_ids)
    fids = list(EXT['colour_families']) if family_ids is None else list(family_ids)
    for r in rids:
        _need(EXT['recipes'], r, 'recipes')
    for f in fids:
        _need(EXT['colour_families'], f, 'colour_families')
    d = {'v': VERSION, 'stamp': EXT['source_stamp'], 'quality_sizes': EXT['quality_sizes'],
         'kinds': EXT['kinds'],
         'recipes': {r: {k: EXT['recipes'][r][k] for k in R_FIELDS if k != 'why'} for r in rids},
         'colour_families': {f: {'name': EXT['colour_families'][f]['name'],
                                 'colours': [{k: c[k] for k in ('id', 'name', 'hex', 'use', 'label_ink')}
                                             for c in EXT['colour_families'][f]['colours']]}
                             for f in fids},
         # hints are cut to the subset so a page never carries an id it cannot draw
         'landuse_hints': {lu: {**{part: [i for i in h[part] if i in rids] for part in ('wall', 'roof', 'ground')},
                                'families': [f for f in h['families'] if f in fids]}
                           for lu, h in EXT['landuse_hints'].items()}}
    return json.dumps(d, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')


def inline_script(recipe_ids=None, family_ids=None):
    return PK_JS + '\nPatternKit.load(' + data_json(recipe_ids, family_ids) + ');\n'


def es_module(recipe_ids=None, family_ids=None):
    return inline_script(recipe_ids, family_ids) + 'export default PatternKit;\n'


PK_JS = r'''
const PatternKit = (() => {
  'use strict';
  let D = null;
  const cache = new Map();
  const fail = (m) => { throw new Error('patternkit: ' + m); };
  const need = (o, k, where) => { if (!o || typeof o !== 'object' || !(k in o)) fail(where + ' has no "' + k + '"'); return o[k]; };
  function load(data) {
    for (const k of ['v', 'quality_sizes', 'kinds', 'recipes', 'colour_families', 'landuse_hints']) need(data, k, 'data');
    D = data; cache.clear(); return api;
  }
  const loaded = () => D || fail('load(data) first');
  function recipe(id) { const R = loaded().recipes; if (!(id in R)) fail('unknown recipe ' + id); return R[id]; }
  function recipes(use) { return Object.keys(loaded().recipes).filter((k) => use === undefined || D.recipes[k].uses.includes(use)); }
  function families() { return Object.keys(loaded().colour_families); }
  function colour(id) {
    const i = String(id).indexOf('.'); const fam = loaded().colour_families[String(id).slice(0, i)];
    if (i < 1 || !fam) fail('unknown colour ' + id);
    const c = fam.colours.find((x) => x.id === id); if (!c) fail('unknown colour ' + id); return c.hex;
  }
  function hexOf(x) { return /^#[0-9a-fA-F]{6}$/.test(String(x)) ? String(x).toUpperCase() : colour(x); }
  // k < 0 darkens toward black, k > 0 lightens toward white, by |k| of the way (k in [-1, 1])
  function shade(hex, k) {
    const h = hexOf(hex); if (!(k >= -1 && k <= 1)) fail('shade k out of range: ' + k);
    const c = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
    const o = c.map((v) => Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k));
    return '#' + o.map((v) => Math.max(0, Math.min(255, v)).toString(16).padStart(2, '0')).join('').toUpperCase();
  }
  // spec: a #RRGGBB, a colour id ("earth.adobe"), or {base, joint?}; joint defaults to the recipe's joint_shade
  function colours(recipeId, spec) {
    const r = recipe(recipeId);
    if (typeof spec === 'string') { const b = hexOf(spec); return { base: b, joint: shade(b, r.joint_shade) }; }
    const b = hexOf(need(spec, 'base', 'colours'));
    return { base: b, joint: ('joint' in spec) ? hexOf(spec.joint) : shade(b, r.joint_shade) };
  }
  function sizeFor(q) { const Q = loaded().quality_sizes; if (!(q in Q)) fail('unknown quality ' + q); return Q[q]; }
  const isPow2 = (n) => Number.isInteger(n) && n > 0 && (n & (n - 1)) === 0;
  function hintsFor(landuse) { const H = loaded().landuse_hints; if (!(landuse in H)) fail('unknown land use ' + landuse); return H[landuse]; }
  function repeatFor(recipeId, widthM, heightM) { const t = recipe(recipeId).tile_m; return [widthM / t, heightM / t]; }
  // deterministic per recipe id: FNV-1a seed into mulberry32
  function rng(seed) {
    let h = 2166136261 >>> 0; for (const ch of String(seed)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; }
    let a = h;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }

  // ---- drawing: every primitive is repeated across the tile edges so the tile wraps seamlessly
  function draw(ctx, recipeId, spec, size) {
    const r = recipe(recipeId); const p = r.params; const C = colours(recipeId, spec); const S = size;
    if (!isPow2(S)) fail('size must be a power of two: ' + S);
    const R = rng(recipeId);
    const vary = (k) => shade(C.base, Math.max(-1, Math.min(1, (R() - 0.5) * 2 * k)));
    const rect = (x, y, w, h, col) => {
      ctx.fillStyle = col;
      for (const ox of [0, -S]) for (const oy of [0, -S]) {
        const X = x + ox, Y = y + oy;
        if (X < S && X + w > 0 && Y < S && Y + h > 0) ctx.fillRect(X, Y, w, h);
      }
    };
    const wrapXY = (x, y) => [((x % S) + S) % S, ((y % S) + S) % S];
    const shape = (cx, cy, rad, col, pathFn) => {
      ctx.fillStyle = col;
      for (const ox of [-S, 0, S]) for (const oy of [-S, 0, S]) {
        const X = cx + ox, Y = cy + oy;
        if (X + rad < 0 || X - rad > S || Y + rad < 0 || Y - rad > S) continue;
        ctx.beginPath(); pathFn(X, Y); ctx.closePath(); ctx.fill();
      }
    };
    rect(0, 0, S, S, C.joint);
    const K = r.kind;
    if (K === 'bond') {
      const ch = S / p.courses, sw = S / p.per_course, j = ch * p.joint;
      for (let i = 0; i < p.courses; i++) {
        const y = i * ch; let seq;
        if (p.header_every === 1) seq = ['S', 'H'];
        else if (p.header_every === 2 && i % 2 === 1) seq = ['H'];
        else seq = ['S'];
        const shift = (i % 2 === 1) ? p.offset * sw : 0;
        let x = 0, n = 0;
        while (x < S - 1e-6) {
          const t = seq[n % seq.length]; const w = t === 'S' ? sw : sw / 2;
          const [X] = wrapXY(x + shift, 0);
          rect(X + j / 2, y + j / 2, w - j, ch - j, t === 'H' ? shade(vary(p.vary), -0.12) : vary(p.vary));
          x += w; n++;
        }
      }
    } else if (K === 'herringbone') {
      const W = S / p.units, j = W * p.joint;
      for (let k = 0; k < p.units; k++) for (let s = 0; s < p.units / 4; s++) {
        let [x, y] = wrapXY((k + 4 * s) * W, k * W); rect(x + j / 2, y + j / 2, 2 * W - j, W - j, vary(p.vary));
        [x, y] = wrapXY((k + 2 + 4 * s) * W, (k - 1) * W); rect(x + j / 2, y + j / 2, W - j, 2 * W - j, vary(p.vary));
      }
    } else if (K === 'basketweave') {
      const c = S / p.cells, u = c / p.per_cell, j = c * p.joint / 2;
      for (let a = 0; a < p.cells; a++) for (let b = 0; b < p.cells; b++) for (let q = 0; q < p.per_cell; q++) {
        if ((a + b) % 2 === 0) rect(a * c + j / 2, b * c + q * u + j / 2, c - j, u - j, vary(p.vary));
        else rect(a * c + q * u + j / 2, b * c + j / 2, u - j, c - j, vary(p.vary));
      }
    } else if (K === 'lap') {
      const bh = S / p.boards;
      for (let i = 0; i < p.boards; i++) {
        const y = i * bh, col = vary(p.vary);
        rect(0, y, S, bh, col);
        if (p.bevel) rect(0, y, S, bh * 0.35, shade(col, 0.06));
        rect(0, y + bh * (1 - p.shadow), S, bh * p.shadow, C.joint);
      }
    } else if (K === 'board_batten') {
      const bw = S / p.boards, b = bw * p.batten;
      for (let i = 0; i < p.boards; i++) rect(i * bw, 0, bw, S, vary(p.vary));
      for (let i = 0; i < p.boards; i++) {
        const [x] = wrapXY(i * bw - b / 2, 0);
        rect(x, 0, b, S, shade(C.base, 0.06)); rect(x + b * 0.8, 0, b * 0.2, S, C.joint);
      }
    } else if (K === 'shingle' || K === 'slate') {
      const rh = S / p.rows, w = S / p.per_row, g = w * p.joint;
      for (let i = 0; i < p.rows; i++) for (let n = 0; n < p.per_row; n++) {
        const [x, y] = wrapXY(n * w + (i % 2) * w / 2, i * rh); const col = vary(p.vary);
        if (K === 'shingle' && p.shape === 'round') {
          const rad = (w - g) / 2, cy = y + rh - rad - g / 2;
          rect(x + g / 2, y, w - g, Math.max(0, cy - y), col);
          shape(x + w / 2, cy, rad, col, (X, Y) => ctx.arc(X, Y, rad, 0, Math.PI));
        } else {
          rect(x + g / 2, y, w - g, rh - g, col);
          if (K === 'slate') rect(x + g / 2, y + rh - g - rh * 0.12, w - g, rh * 0.12, shade(col, -0.10));
        }
      }
    } else if (K === 'speckle') {
      rect(0, 0, S, S, C.base);
      for (let i = 0; i < p.dots; i++) {
        const cx = R() * S, cy = R() * S, rad = (p.size[0] + R() * (p.size[1] - p.size[0])) * S;
        const pick = R();
        const col = p.aggregate ? (pick < 0.34 ? C.joint : shade(C.base, (pick < 0.67 ? -1 : 1) * p.spread))
          : shade(C.base, (pick - 0.5) * 2 * p.spread);
        if (p.aggregate) {
          const n = 5, a0 = R() * Math.PI, rs = Array.from({ length: n }, () => rad * (0.6 + 0.4 * R()));
          shape(cx, cy, rad, col, (X, Y) => { for (let k = 0; k < n; k++) { const a = a0 + k * 2 * Math.PI / n; const f = k ? 'lineTo' : 'moveTo'; ctx[f](X + Math.cos(a) * rs[k], Y + Math.sin(a) * rs[k]); } });
        } else shape(cx, cy, rad, col, (X, Y) => ctx.arc(X, Y, rad, 0, 2 * Math.PI));
      }
    } else if (K === 'formed') {
      const bh = S / p.boards;
      for (let i = 0; i < p.boards; i++) {
        const col = vary(p.vary); rect(0, i * bh, S, bh, col);
        for (let gi = 0; gi < p.grain; gi++) rect(0, i * bh + R() * bh, S, Math.max(1, S / 512), shade(col, -0.06));
        rect(0, i * bh, S, Math.max(1, S / 256), C.joint);
      }
      for (let a = 0; a < p.tie_holes; a++) for (let b = 0; b < 2; b++) {
        const rad = S * 0.012; shape((a + 0.5) * S / p.tie_holes, (b + 0.5) * S / 2, rad, C.joint, (X, Y) => ctx.arc(X, Y, rad, 0, 2 * Math.PI));
      }
    } else if (K === 'corrugated') {
      const sw = S / (p.waves * p.bands);
      for (let i = 0; i < p.waves * p.bands; i++) {
        const t = Math.cos(2 * Math.PI * (i + 0.5) / p.bands);
        rect(i * sw, 0, sw, S, shade(C.base, t >= 0 ? 0.14 * t : r.joint_shade * -t));
      }
    } else if (K === 'seam') {
      const pw = S / p.panels, sw = pw * p.seam;
      for (let i = 0; i < p.panels; i++) {
        rect(i * pw, 0, pw, S, i % 2 ? C.base : shade(C.base, 0.03));
        rect(i * pw, 0, sw / 2, S, shade(C.base, 0.22)); rect(i * pw + sw / 2, 0, sw / 2, S, C.joint);
      }
    } else if (K === 'cobble') {
      const cw = S / p.cols, chh = S / p.rows;
      for (let a = 0; a < p.rows; a++) for (let b = 0; b < p.cols; b++) {
        const cx = (b + 0.5 + (a % 2) / 2 + (R() - 0.5) * p.jitter) * cw, cy = (a + 0.5 + (R() - 0.5) * p.jitter) * chh;
        const rx = cw / 2 * (1 - p.joint), ry = chh / 2 * (1 - p.joint), col = vary(p.vary);
        shape(cx, cy, Math.max(rx, ry), col, (X, Y) => ctx.ellipse(X, Y, rx, ry, 0, 0, 2 * Math.PI));
      }
    } else if (K === 'hex') {
      const w = S / p.cols, h = S / p.rows, a = w / 2 * (1 - p.joint), b = (h / 0.75) / 2 * (1 - p.joint);
      for (let i = 0; i < p.rows; i++) for (let n = 0; n < p.cols; n++) {
        const cx = (n + 0.5 + (i % 2) / 2) * w, cy = (i + 0.5) * h, col = vary(p.vary);
        shape(cx, cy, Math.max(a, b), col, (X, Y) => { ctx.moveTo(X, Y - b); ctx.lineTo(X + a, Y - b / 2); ctx.lineTo(X + a, Y + b / 2); ctx.lineTo(X, Y + b); ctx.lineTo(X - a, Y + b / 2); ctx.lineTo(X - a, Y - b / 2); });
      }
    } else if (K === 'barrel') {
      const rh = S / p.rows, w = S / p.per_row, bands = 8, bw = w / bands;
      for (let i = 0; i < p.rows; i++) for (let n = 0; n < p.per_row; n++) for (let q = 0; q < bands; q++) {
        const t = Math.sin(Math.PI * (q + 0.5) / bands);
        rect(n * w + q * bw, i * rh, bw, rh * 0.86, shade(C.base, (t - 0.7) * p.shade));
        rect(n * w + q * bw, i * rh + rh * 0.86, bw, rh * 0.14, shade(C.base, -p.shade * t));
      }
    } else fail('no drawing for kind ' + K);
    return C;
  }

  function makeCanvas(S, doc) {
    if (doc && doc.createElement) { const c = doc.createElement('canvas'); c.width = S; c.height = S; return c; }
    if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(S, S);
    if (typeof document !== 'undefined') { const c = document.createElement('canvas'); c.width = S; c.height = S; return c; }
    return fail('no canvas available (pass opts.doc)');
  }
  // THREE is passed in (the page's own three.js); opts.quality 'low' | 'medium' | 'high' (default 'medium')
  function texture(THREE, recipeId, spec, opts) {
    const o = opts || {}; const q = ('quality' in o) ? o.quality : 'medium'; const S = sizeFor(q);
    const C = colours(recipeId, spec); const key = recipeId + '|' + C.base + '|' + C.joint + '|' + S;
    if (cache.has(key)) return cache.get(key);
    const cv = makeCanvas(S, o.doc); const ctx = cv.getContext('2d'); draw(ctx, recipeId, C, S);
    const t = new THREE.CanvasTexture(cv);
    t.wrapS = THREE.RepeatWrapping; t.wrapT = THREE.RepeatWrapping;
    if ('SRGBColorSpace' in THREE) t.colorSpace = THREE.SRGBColorSpace;
    t.userData = { patternkit: key, tile_m: recipe(recipeId).tile_m };
    cache.set(key, t); return t;
  }
  const api = { load, get version() { return loaded().v; }, recipe, recipes, families, colour, colours, shade, sizeFor, isPow2,
    hintsFor, repeatFor, draw, texture, rng, cacheSize: () => cache.size,
    clearCache: () => { for (const t of cache.values()) if (t && t.dispose) t.dispose(); cache.clear(); } };
  return api;
})();
'''
