/**
 * Flora pack verification (flora/registry/flora.json from flora/authored/flora.json via flora/build.py).
 * Recomputes the registry's claims from its inputs: stamp, freshness, honesty, species regions and ranges, rule
 * coverage of every (land use, water class) pair, detail recipes, and the triangle / draw-call budget.
 *
 *   node flora/test.mjs
 *   node flora/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const hit = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(hit ? hit.slice(7) : join(HERE, '..'));
let n = 0, bad = 0;
const ok = (m, c, ev = []) => { if (c) { n++; console.log('  ok  ' + m); return; } bad++; console.log('FAIL  ' + m); for (const e of ev) console.log('      ' + e); };
const reg = JSON.parse(readFileSync(join(ROOT, 'flora/registry/flora.json'), 'utf8'));
const src = JSON.parse(readFileSync(join(ROOT, 'flora/authored/flora.json'), 'utf8'));

{
  const h = createHash('sha256');
  for (const rel of reg.inputs) h.update(Buffer.concat([Buffer.from(rel), Buffer.from([0]), readFileSync(join(ROOT, rel)), Buffer.from([0])]));
  ok('[stamp] source_stamp is sha256[:16] of the declared inputs (flora/build.py, authored flora.json)', h.digest('hex').slice(0, 16) === reg.source_stamp && reg.inputs.includes('flora/build.py') && reg.inputs.includes('flora/authored/flora.json'));
  let fresh = true; try { execFileSync('python3', [join(ROOT, 'flora/build.py'), '--check'], { stdio: 'pipe' }); } catch { fresh = false; }
  ok('[stamp] flora/build.py --check: registry is current', fresh);
}
ok('[honesty] provenance AUTHORED and a page line that says AUTHORED and "not a tree survey"', reg.provenance === 'AUTHORED' && /AUTHORED/.test(reg.honesty.page_line) && /not a tree survey/.test(reg.honesty.page_line));
{
  let en = ''; try { en = JSON.parse(readFileSync(join(ROOT, 'i18n/locales/en.json'), 'utf8')).strings['veg.honesty']; } catch { en = ''; }
  ok('[honesty] i18n veg.honesty (en) is the registry page line verbatim', en === reg.honesty.page_line);
}
const WANT = { louisiana: ['live_oak', 'bald_cypress', 'sabal_palmetto', 'crape_myrtle', 'marsh_grass', 'cattail'],
  bay: ['coast_live_oak', 'eucalyptus', 'monterey_cypress', 'coastal_scrub', 'redwood'], smiles: ['shade_tree', 'school_tree'] };
for (const [r, ids] of Object.entries(WANT)) ok(`[species] region ${r} carries ${ids.join(', ')}`, ids.every((s) => reg.species[s] && reg.species[s].region === r), [ids.filter((s) => !reg.species[s]).join(',')]);
ok('[species] every species: plant family, positive [min, max] height and crown, #RRGGBB colour',
  Object.values(reg.species).every((s) => !['moss', 'detail'].includes(s.family) && reg.families[s.family] && s.height_m[0] > 0 && s.height_m[0] <= s.height_m[1] && s.crown_m[0] > 0 && s.crown_m[0] <= s.crown_m[1] && /^#[0-9a-fA-F]{6}$/.test(s.colour)));
ok('[species] Spanish moss hangs only on live oak, only at shore / near water', JSON.stringify(reg.moss.on) === '["live_oak"]' && reg.moss.water.every((w) => ['shore', 'near'].includes(w)));
for (const [r, R] of Object.entries(reg.regions)) {
  const gaps = [];
  for (const lu of R.land_uses) for (const w of ['shore', 'near', 'far']) if (!R.rules.some((x) => (x.land_use === '*' || x.land_use === lu) && (x.water === '*' || x.water === w))) gaps.push(lu + '/' + w);
  ok(`[rules] ${r}: every (land use, water class) pair matches a rule`, gaps.length === 0, gaps);
  ok(`[rules] ${r}: every rule mix names only ${r} species`, R.rules.every((x) => Object.keys(x.mix).every((s) => reg.species[s] && reg.species[s].region === r)));
  ok(`[details] ${r}: every land use has a detail rule (0 < p_kerb <= 1) naming known details`, R.land_uses.every((lu) => R.details[lu] && R.details[lu].p_kerb > 0 && R.details[lu].p_kerb <= 1 && Object.keys(R.details[lu].mix).every((d) => reg.details[d])));
}
{
  const r = reg.regions.louisiana.rules, sh = r.find((x) => x.water === 'shore');
  ok('[rules] Louisiana shoreline mix is marsh grass, cattail and bald cypress (first shore rule)', sh && ['marsh_grass', 'cattail', 'bald_cypress'].every((s) => sh.mix[s] > 0));
  const bp = reg.regions.bay.rules.filter((x) => x.mix.redwood);
  ok('[rules] Bay redwoods only in park land away from water (AUTHORED canyon stand-in on flat ground)', bp.length > 0 && bp.every((x) => x.land_use === 'park' && x.water === 'far'));
  const mc = reg.regions.bay.rules.filter((x) => x.mix.monterey_cypress);
  ok('[rules] Bay Monterey cypress only near the water', mc.length > 0 && mc.every((x) => x.water === 'near' || x.water === 'shore'));
}
ok('[details] fences, mailboxes, benches, bus shelters, bollards and planters, each a box recipe [dx, y0, dz, w, h, d, colour]',
  ['fence', 'mailbox', 'bench', 'bus_shelter', 'bollard', 'planter'].every((d) => reg.details[d] && reg.details[d].boxes.length > 0 && reg.details[d].boxes.every((b) => b.length === 7 && b[3] > 0 && b[4] > 0 && b[5] > 0)));
{
  const worst = Object.values(reg.families).reduce((a, f) => a + f.cap * f.tris, 0);
  ok('[budget] worst case sum(cap x tris) <= budgets.tris_max and matches counts.worst_case_tris', worst <= reg.budgets.tris_max && worst === reg.counts.worst_case_tris, [`${worst} vs ${reg.budgets.tris_max}`]);
  ok('[budget] families <= budgets.draw_calls_max (one InstancedMesh each)', Object.keys(reg.families).length <= reg.budgets.draw_calls_max);
  ok('[budget] every family has a positive lod_m and cap', Object.values(reg.families).every((f) => f.lod_m > 0 && f.cap > 0));
}
for (const r of ['louisiana', 'bay']) {
  const L = reg.regions[r].landcover, codes = ['10', '20', '30', '40', '50', '60', '70', '80', '90', '95', '100'];
  ok(`[landcover] ${r}: a rule (or null) for every WorldCover class; built-up 50 and water 80 place no plants; wetland 90 = reeds`,
    L && JSON.stringify(Object.keys(L).sort()) === JSON.stringify([...codes].sort()) && L['50'] === null && L['80'] === null && L['90'] && Object.keys(L['90'].mix).some((s) => reg.species[s].family === 'reed'));
}
ok('[registry] registry species / regions are the authored ones (no additions at build time)', JSON.stringify(Object.keys(reg.species).sort()) === JSON.stringify(Object.keys(src.species).sort()) && JSON.stringify(Object.keys(reg.regions).sort()) === JSON.stringify(Object.keys(src.regions).sort()));
console.log(`\nflora/test: ${n} checks passed, ${bad} failed`);
process.exit(bad ? 1 : 0);
