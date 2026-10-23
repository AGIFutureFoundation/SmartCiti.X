/* swarm/geohash.mjs - geohash cells (public-domain grid), pure functions. Longitude bit first, then latitude, five bits per
 * character of the alphabet below. Used to name the cells a hive owns and to turn a position into a cell. No clock, no I/O. */
export const B32 = '0123456789bcdefghjkmnpqrstuvwxyz';
export const CELL_RE = /^[0-9bcdefghjkmnpqrstuvwxyz]{1,12}$/;

export function encode(lat, lng, precision) {
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) throw new Error('geohash: coordinate out of range');
  const la = [-90, 90], lo = [-180, 180];
  let out = '', bits = 0, ch = 0, even = true;
  while (out.length < precision) {
    const r = even ? lo : la, v = even ? lng : lat, mid = (r[0] + r[1]) / 2;
    if (v >= mid) { ch = (ch << 1) | 1; r[0] = mid; } else { ch <<= 1; r[1] = mid; }
    even = !even;
    if (++bits === 5) { out += B32[ch]; bits = 0; ch = 0; }
  }
  return out;
}

export function bounds(h) {
  if (typeof h !== 'string' || !CELL_RE.test(h)) throw new Error('geohash: not a cell string');
  const la = [-90, 90], lo = [-180, 180];
  let even = true;
  for (const c of h) {
    const v = B32.indexOf(c);
    for (const b of [16, 8, 4, 2, 1]) {
      const r = even ? lo : la, mid = (r[0] + r[1]) / 2;
      if (v & b) r[0] = mid; else r[1] = mid;
      even = !even;
    }
  }
  return { s: la[0], w: lo[0], n: la[1], e: lo[1] };
}

export function center(h) { const b = bounds(h); return { lat: (b.s + b.n) / 2, lng: (b.w + b.e) / 2 }; }

/* the (2k+1) x (2k+1) block of equal-length cells around h */
export function ring(h, k) {
  const b = bounds(h), c = center(h), dlat = b.n - b.s, dlng = b.e - b.w, out = new Set();
  for (let i = -k; i <= k; i++) for (let j = -k; j <= k; j++)
    out.add(encode(Math.max(-89.999, Math.min(89.999, c.lat + i * dlat)), ((c.lng + j * dlng + 180) % 360 + 360) % 360 - 180, h.length));
  return [...out].sort();
}
