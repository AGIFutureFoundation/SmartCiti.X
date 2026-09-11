/**
 * City-records registry verification.
 *
 * This pack's whole value is that it does NOT hold the records — so the
 * checks are about the contract rather than the content: every campus has
 * an authority with a licence and a real https query, every query is
 * bounded by that campus's own RECORDED city frame, the imagery is the
 * public-domain federal service and admits it was never probed from the
 * build, and nothing anywhere drifts toward naming an owner or claiming
 * the fetched records as this bundle's own.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/parcels.json', import.meta.url)));
const campuses = JSON.parse(readFileSync(
  new URL('../unions/registry/campuses.json', import.meta.url))).campuses;
const geo = JSON.parse(readFileSync(
  new URL('../geo/registry/campuses_geo.json', import.meta.url)));

/* ------------------------------------------------------------ contract --- */
ok('the contract is a source contract: no record is stored, the browser fetches, failure falls back',
  /source contract, not a data copy/.test(reg.contract)
  && /no parcel or imagery record is stored/.test(reg.contract)
  && /learner's own browser/.test(reg.contract)
  && /fall back to the SCHEMATIC layers/.test(reg.contract));
ok('the registry holds no record geometry at all - only the way to ask for it',
  !JSON.stringify(reg).includes('coordinates')
  && Object.values(reg.sources).every((s) => !('features' in s)));

/* ----------------------------------------------------------- authority --- */
ok('every campus names an authority, a dataset licence, a record count and a record kind',
  JSON.stringify(Object.keys(reg.sources).sort())
    === JSON.stringify(Object.keys(campuses).sort())
  && Object.values(reg.sources).every((s) => s.authority.length > 20
      && s.licence.length > 20 && s.records > 1000 && s.kind
      && s.region));
ok('the New Orleans authority is the city GIS the record count comes from',
  /data\.nola\.gov/.test(reg.sources['new-orleans'].authority)
  && reg.sources['new-orleans'].records === 125803);
ok('the Bay authorities are the two county rolls: the SF assessor and Alameda County',
  /DataSF/.test(reg.sources['treasure-island'].authority)
  && /wv5m-vpq2/.test(reg.sources['treasure-island'].cite)
  && /Alameda County Assessor/.test(reg.sources.oakland.authority));
ok('every citation names the Locator.X builder it was recorded from, and the check ran',
  Object.values(reg.sources).every((s) => /\.py$/.test(s.cite_file)
    && /\.py$/.test(s.records_cite_file) && s.cite.length > 5)
  && /cross-checked|carried as recorded/.test(reg.recorded_check));

/* -------------------------------------------------------------- query --- */
ok('every query is https, and asks for a bounded page of records rather than a whole city',
  Object.values(reg.sources).every((s) => s.endpoint.startsWith('https://')
    && Object.values(s.query).some((v) => /^\d+$/.test(String(v))
        && +v > 0 && +v <= 2000)));
ok("every query is framed by that campus's own RECORDED city frame",
  Object.entries(reg.sources).every(([ck, s]) => {
    const f = geo.city[ck].bounds;
    return s.frame.w === f.w && s.frame.s === f.s
      && s.frame.e === f.e && s.frame.n === f.n;
  }));

/* ------------------------------------------------------------ imagery --- */
ok('the imagery is the public-domain federal service, with its tile scheme and zoom stated',
  /United States Geological Survey/.test(reg.imagery.authority)
  && /USGS/.test(reg.imagery.name)
  && /public domain/.test(reg.imagery.licence)
  && /\{z\}/.test(reg.imagery.tiles) && /\{y\}/.test(reg.imagery.tiles)
  && /\{x\}/.test(reg.imagery.tiles)
  && reg.imagery.zoom.max >= 14 && reg.imagery.tile_size === 256);
ok('the imagery admits it was never probed from the build, and says what happens when it is silent',
  reg.imagery.verified_from_build === false
  && /reaches no host outside GitHub/.test(reg.imagery.verification_note)
  && /fall back to the SCHEMATIC ground/.test(reg.imagery.verification_note));

/* ------------------------------------------------------------- honesty --- */
ok('the records honesty refuses to name a person: public record, geometry and use-class only',
  /public administrative record, not a\s+claim about any person/.test(reg.honesty.records)
  && /no owner is named/.test(reg.honesty.records));
ok('the fidelity note keeps the line: fetched footprints RECORDED, everything drawn around them SCHEMATIC',
  /RECORDED/.test(reg.honesty.fidelity) && /SCHEMATIC/.test(reg.honesty.fidelity)
  && /labelled so on the page/.test(reg.honesty.fidelity));
ok('the availability note treats a failed fetch as a fallback, never an error',
  /no endpoint here is guaranteed/.test(reg.honesty.availability)
  && /never an error/.test(reg.honesty.availability));
ok('no owner-bearing field is requested by any query',
  Object.values(reg.sources).every((s) =>
    !/owner|OWNER|name|NAME/.test(JSON.stringify(s.query))));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`parcels/test: ${n} checks passed — ${Object.keys(reg.sources).length} `
  + `authorities, imagery ${reg.imagery.id}`);
