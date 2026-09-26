/* The JS twin of surfaces/surfaces.py's state rule (spec §24, states).
 *
 * The registry emits the closure of the rule in full, but a page that shipped
 * 1,220 rows would be carrying a table it could compute (§24.4: write it once
 * and let both read it). So the page ships the AXES the registry publishes and
 * derives a state from its base with this function - and surfaces/test.mjs
 * holds every emitted state to exactly what this function returns, so the
 * Python and the JS cannot drift apart without the suite saying so.
 *
 * Integer arithmetic only: per channel, mixed = (base*(100-pct) + target*pct)
 * div 100, floored; roughness in hundredths. No Math.random, no clock.
 */
export function mixHex(color, target, pct) {
  const a = [1, 3, 5].map((i) => parseInt(color.slice(i, i + 2), 16));
  const b = [1, 3, 5].map((i) => parseInt(target.slice(i, i + 2), 16));
  const m = a.map((x, i) => Math.floor((x * (100 - pct) + b[i] * pct) / 100));
  return '#' + m.map((v) => v.toString(16).padStart(2, '0')).join('');
}

/** base: a catalogue entry {name,color,roughness,metalness,pattern,tile_m};
 *  axes: registry.states.axes; returns the derived state's renderer values. */
export function stateOf(base, wear, intensity, wet, axes) {
  const w = axes.wear[wear], it = axes.intensity[intensity], W = axes.wet;
  const pct = Math.floor(w.mix_pct * it.scale_pct / 100);
  const dr = Math.floor(w.roughness_delta * it.scale_pct / 100);
  let color = mixHex(base.color, w.target, pct);
  let r100 = Math.min(100, Math.max(0, Math.round(base.roughness * 100) + dr));
  if (wet) {
    color = mixHex(color, W.tint, W.mix_pct);
    r100 = Math.floor(r100 * W.roughness_pct / 100);
  }
  const adverb = intensity === 'heavy' ? 'heavily' : 'lightly';
  return {
    name: `${base.name}, ${adverb} ${wear}${wet ? ', wet' : ''}`,
    color, roughness: r100 / 100, metalness: base.metalness,
    pattern: base.pattern, tile_m: base.tile_m,
  };
}

/** Parse a state id back into its axes: "<base>~<wear>-<intensity>~<wet|dry>". */
export function parseStateId(id) {
  const m = /^(.+)~([a-z]+)-(heavy|light)~(wet|dry)$/.exec(id);
  if (!m) return null;
  return { base: m[1], wear: m[2], intensity: m[3], wet: m[4] === 'wet' };
}
