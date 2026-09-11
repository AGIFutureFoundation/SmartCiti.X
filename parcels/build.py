#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the city-records registry builder.

To mimic a city you need the city's own records, and this registry is the
contract for reaching them: per campus region, the AUTHORITY that publishes
the parcel and building-footprint records, the dataset it publishes them
under, the licence, the field names, and the exact query the map issues.

WHAT IS AND IS NOT HERE. No parcel record is copied into this repository.
This is a source contract: the maps fetch footprints from the authority in
the LEARNER'S OWN BROWSER, at view time, and render what comes back. That
keeps one truth per fact (the authority's), avoids redistributing records
this bundle has no licence to republish, and means a stale record here is
impossible - there is no record here to go stale.

PROVENANCE. Every authority, dataset id and record count below is RECORDED
from Locator.X's committed builders (Apache-2.0), the same sibling source
the geo registry copies its coordinates from, and cross-checked against
that checkout whenever it is present - exactly as geo/build.py does.

HONESTY. A parcel record is a public administrative record, not a claim
about any person: nothing here names an owner, and the maps render
geometry and use-class only. The imagery layer is public-domain federal
orthoimagery requested from the authority the same way; where the network
cannot reach either source the maps fall back to their SCHEMATIC layers
and say so on the page.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "3.2.0"
BUILT = "2026-09-11"

# The authorities, RECORDED from the Locator.X builders that consume them.
# `cite` is the verbatim string those builders carry; the cross-check below
# fails the build if the sibling checkout no longer contains it.
SOURCES = {
    'new-orleans': {
        'region': 'Orleans and Jefferson parishes, Louisiana',
        'authority': 'City of New Orleans (data.nola.gov) parcel and '
                     'building-footprint GIS',
        'cite': 'data.nola.gov',
        'cite_file': 'build_data_nola.py',
        'records': 125803,
        'records_cite': '125,803 parcels across Orleans and Jefferson parishes',
        'records_cite_file': 'build_atlas_nola.py',
        'licence': 'City of New Orleans open data - public records, '
                   'published for reuse with attribution',
        'kind': 'parcel + building footprint',
        # ArcGIS FeatureServer query: GeoJSON out, bbox in, CORS-enabled.
        'endpoint': 'https://services.arcgis.com/mQjZPm5VsAyGyND5/arcgis/rest/'
                    'services/Building_Footprint/FeatureServer/0/query',
        'query': {'where': '1=1', 'outFields': 'OBJECTID',
                  'geometryType': 'esriGeometryEnvelope', 'inSR': '4326',
                  'outSR': '4326', 'f': 'geojson', 'resultRecordCount': '600'},
    },
    'treasure-island': {
        'region': 'City and County of San Francisco, California',
        'authority': 'San Francisco Assessor secured roll, published by '
                     'DataSF (dataset wv5m-vpq2)',
        'cite': 'SF Assessor secured roll (DataSF wv5m-vpq2), closed roll 2025',
        'cite_file': 'build_data.py',
        'records': 128319,
        'records_cite': '128,319 real sites from county records',
        'records_cite_file': 'build_atlas_nola.py',
        'licence': 'DataSF open data - public records, published for reuse',
        'kind': 'assessor parcel roll',
        'endpoint': 'https://data.sfgov.org/resource/ramy-di5m.geojson',
        'query': {'$limit': '600'},
    },
    'oakland': {
        'region': 'Alameda County, California',
        'authority': 'Alameda County Assessor parcels, published as an '
                     'ArcGIS FeatureServer',
        'cite': 'Alameda County Assessor parcels (ArcGIS FeatureServer), '
                'roll 2025',
        'cite_file': 'build_data.py',
        'records': 128319,
        'records_cite': '128,319 real sites from county records',
        'records_cite_file': 'build_atlas_nola.py',
        'licence': 'Alameda County open data - public records, published '
                   'for reuse',
        'kind': 'assessor parcel roll',
        'endpoint': 'https://services3.arcgis.com/HESxeTbDliKKvec2/arcgis/'
                    'rest/services/Alameda_County_Parcels/FeatureServer/0/query',
        'query': {'where': '1=1', 'outFields': 'OBJECTID',
                  'geometryType': 'esriGeometryEnvelope', 'inSR': '4326',
                  'outSR': '4326', 'f': 'geojson', 'resultRecordCount': '600'},
    },
}

# Orthoimagery: the one basemap this bundle will draw, chosen because it is
# a work of the United States government and therefore public domain - no
# key, no account, no attribution obligation beyond courtesy.
IMAGERY = {
    'id': 'usgs-imagery-only',
    'name': 'USGS National Map - imagery only',
    'authority': 'United States Geological Survey',
    'licence': 'public domain (work of the U.S. federal government)',
    'attribution': 'Imagery: USGS The National Map',
    'tiles': 'https://basemap.nationalmap.gov/arcgis/rest/services/'
             'USGSImageryOnly/MapServer/tile/{z}/{y}/{x}',
    'scheme': 'xyz (ArcGIS z/y/x order)',
    'zoom': {'min': 0, 'max': 16},
    'tile_size': 256,
    'provenance': 'RECORDED - the published service of the cited authority',
    'verified_from_build': False,
    'verification_note': 'the build sandbox reaches no host outside GitHub '
                         'and the package registries, so this endpoint is '
                         'declared from its authority rather than probed '
                         'here; the maps request it in the learner\'s '
                         'browser and fall back to the SCHEMATIC ground '
                         'when it does not answer.',
}

CONTRACT = (
    'source contract, not a data copy: no parcel or imagery record is '
    'stored in this repository. The maps request them from the authority '
    'in the learner\'s own browser at view time, render what comes back, '
    'and fall back to the SCHEMATIC layers when the request fails.'
)

HONESTY = {
    'records': 'a parcel record is a public administrative record, not a '
               'claim about any person: no owner is named, and the maps '
               'render geometry and use-class only.',
    'fidelity': 'footprints fetched from an authority are RECORDED and '
                'drawn as they arrive; everything the Academy draws around '
                'them - the campus buildings, roads and water - remains '
                'SCHEMATIC and is labelled so on the page.',
    'availability': 'no endpoint here is guaranteed: authorities move '
                    'datasets. A failed fetch is a fallback, never an '
                    'error, and the page says which layer it is showing.',
}

# ---------------------------------------------------------------- checks ---
campuses = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
assert set(SOURCES) == set(campuses), 'a records source per campus, exactly'

geo = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))
for ck, s in SOURCES.items():
    frame = geo['city'][ck]['bounds']
    s['frame'] = frame          # the RECORDED city frame bounds the query
    assert s['endpoint'].startswith('https://'), f'{ck}: endpoint must be https'

# Cross-check against the sibling checkout, exactly as geo/build.py does.
locx = ROOT.parent / 'locator.x'
checked = 'Locator.X checkout not present; citations carried as recorded'
if locx.exists():
    for ck, s in SOURCES.items():
        src = (locx / s['cite_file']).read_text()
        assert s['cite'] in src, \
            f"{ck}: authority citation drifted from {s['cite_file']}"
        rsrc = (locx / s['records_cite_file']).read_text()
        assert s['records_cite'] in rsrc, \
            f"{ck}: record count drifted from {s['records_cite_file']}"
    checked = 'cross-checked against the Locator.X checkout'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-city-records',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'contract': CONTRACT,
    'recorded_check': checked,
    'honesty': HONESTY,
    'sources': SOURCES,
    'imagery': IMAGERY,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'parcels.json').write_text(json.dumps(doc, indent=1) + '\n')
tot = sum({s['records'] for s in SOURCES.values()})
print(f"city records: {len(SOURCES)} authorities ({tot:,} records published "
      f"upstream), 1 public-domain imagery service; {checked} "
      f"(source stamp {stamp})")
