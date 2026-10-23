/* swarm/geo.mjs - planar geometry on (lat, lng) degrees for geofences: point in polygon, polygon against a cell rectangle,
 * and the haversine distance. A geofence is a simple polygon that does not cross the antimeridian; edges are straight in
 * lat/lng, which is accurate to well under a cell at the sizes a hive fence is drawn. Pure; no clock, no I/O. */
export const EARTH_KM = 6371.0088;

export function haversineKm(a, b) {
  const r = Math.PI / 180, p1 = a.lat * r, p2 = b.lat * r, dp = p2 - p1, dl = (b.lng - a.lng) * r;
  const x = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * EARTH_KM * Math.asin(Math.sqrt(x));
}

const cross = (o, a, b) => (a.lng - o.lng) * (b.lat - o.lat) - (a.lat - o.lat) * (b.lng - o.lng);
const within = (p, a, b) => Math.min(a.lat, b.lat) <= p.lat && p.lat <= Math.max(a.lat, b.lat) && Math.min(a.lng, b.lng) <= p.lng && p.lng <= Math.max(a.lng, b.lng);
const onSeg = (p, a, b) => cross(a, b, p) === 0 && within(p, a, b);

/* inclusive of the boundary */
export function pointInPolygon(p, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i], b = ring[j];
    if (onSeg(p, a, b)) return true;
    if ((a.lat > p.lat) !== (b.lat > p.lat) && p.lng < ((b.lng - a.lng) * (p.lat - a.lat)) / (b.lat - a.lat) + a.lng) inside = !inside;
  }
  return inside;
}

function segmentsMeet(a, b, c, d) {
  const d1 = Math.sign(cross(a, b, c)), d2 = Math.sign(cross(a, b, d)), d3 = Math.sign(cross(c, d, a)), d4 = Math.sign(cross(c, d, b));
  if (d1 * d2 < 0 && d3 * d4 < 0) return true;
  return onSeg(c, a, b) || onSeg(d, a, b) || onSeg(a, c, d) || onSeg(b, c, d);
}

/* does the polygon touch the cell rectangle {s,w,n,e}? */
export function polygonTouchesRect(ring, r) {
  const corners = [{ lat: r.s, lng: r.w }, { lat: r.s, lng: r.e }, { lat: r.n, lng: r.e }, { lat: r.n, lng: r.w }];
  if (ring.some((v) => v.lat >= r.s && v.lat <= r.n && v.lng >= r.w && v.lng <= r.e)) return true;
  if (corners.some((c) => pointInPolygon(c, ring))) return true;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++)
    for (let k = 0; k < 4; k++) if (segmentsMeet(ring[j], ring[i], corners[k], corners[(k + 1) % 4])) return true;
  return false;
}

/* shoelace area in square degrees (0 = degenerate) */
export function area(ring) {
  let s = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) s += (ring[j].lng * ring[i].lat) - (ring[i].lng * ring[j].lat);
  return Math.abs(s) / 2;
}

/* a simple polygon has no two non-adjacent edges that meet */
export function isSimple(ring) {
  const n = ring.length;
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    if (j === i + 1 || (i === 0 && j === n - 1)) continue;
    if (segmentsMeet(ring[i], ring[(i + 1) % n], ring[j], ring[(j + 1) % n])) return false;
  }
  return true;
}
