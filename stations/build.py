#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the stations pack builder.

Rebrands the recovered pre-rebrand yard curriculum (archive/
bac_yard_stations.json) into the live 111-hall structure: every station is
assigned to a hall from the union roster, a strand from the skill graph,
a tier, and — through the strand — the room of that hall's floor plan where
the station physically belongs. The interactive map renders stations in
exactly those rooms, so the content and the space cannot drift apart.

The assignment table below is AUTHORED — it is a curatorial judgement about
which hall each station serves — and everything derived from it (skill_id,
room, district) is computed from the registries, then proven by
stations/test.mjs rather than trusted.

HONESTY: station content is recovered, machine-gradable curriculum from the
pre-rebrand era; it remains unverified general practice until reviewed by
journey-level practitioners (ROADMAP v3.4), and the registry says so.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'web'))
from interiors import ROOMS  # noqa: E402

PACK_VERSION = "3.2.0"
BUILT = "2026-09-09"

archive = json.load(open(ROOT / 'archive' / 'bac_yard_stations.json'))
unions = json.load(open(ROOT / 'unions' / 'registry' / 'unions.json'))['unions']
skills = json.load(open(ROOT / 'pack' / 'registry' / 'skills.json'))['skills']
by_slug = {u['slug']: u for u in unions}
skill_ids = {s['skill_id'] for s in skills}
room_of = {strand: label for strand, label, *_ in ROOMS}

# station id -> (hall slug, strand, tier). Authored; verified downstream.
ASSIGN = {
    0:  ("bricklayers",    "safety",          "fundamentals"),  # PPE & Readiness
    1:  ("bricklayers",    "materials",       "fundamentals"),  # Mortar & Material Prep
    2:  ("bricklayers",    "procedure",       "fundamentals"),  # Bricklaying Technique
    3:  ("scaffold",       "safety",          "applied"),       # Scaffold & Fall Protection
    4:  ("bricklayers",    "safety",          "applied"),       # Silica Dust & Respiratory
    5:  ("riggers",        "procedure",       "fundamentals"),  # Rigging & Material Handling
    6:  ("bricklayers",    "layout",          "fundamentals"),  # Blueprint & Layout Reading
    7:  ("bricklayers",    "documentation",   "fundamentals"),  # Apprenticeship & Union Pathway
    8:  ("cement-masons",  "materials",       "applied"),       # Curing & Weather Protection
    9:  ("masonry-restore","procedure",       "applied"),       # Restoration & Tuckpointing
    10: ("bricklayers",    "procedure",       "applied"),       # Reinforced Masonry & Grouting
    11: ("stone-carvers",  "materials",       "applied"),       # Stone Veneer & Anchored Stone
    12: ("bricklayers",    "coordination",    "mastery"),       # Estimating & Bidding
    13: ("site-safety",    "leadership",      "applied"),       # Jobsite Safety Culture
    14: ("masonry-restore","materials",       "fundamentals"),  # Cleaning & Sealing Masonry
    15: ("refractory",     "procedure",       "applied"),       # Refractory Masonry
    16: ("masonry-restore","documentation",   "applied"),       # Historic Preservation Standards
    17: ("masonry-restore","tools",           "fundamentals"),  # Pointing & Joint Finishes
    18: ("bricklayers",    "inspection",      "applied"),       # Masonry Anchorage & Ties
    19: ("waterproofers",  "procedure",       "applied"),       # Flashing & Moisture Control
    20: ("bricklayers",    "materials",       "applied"),       # Concrete Masonry Units (CMU)
    21: ("stone-carvers",  "procedure",       "applied"),       # Natural Stone Setting
    22: ("tilesetters",    "procedure",       "fundamentals"),  # Tile & Terrazzo
    23: ("lathers",        "procedure",       "fundamentals"),  # Welding & Metal Stud Framing
    24: ("waterproofers",  "materials",       "fundamentals"),  # Caulking & Sealants
}

stations = []
for s in archive['stations']:
    hall, strand, tier = ASSIGN[s['id']]
    assert hall in by_slug, f'unknown hall {hall}'
    skill_id = f'{hall}.{strand}.{tier}'
    assert skill_id in skill_ids, f'no such skill {skill_id}'
    stations.append({
        "station_id": f"st{s['id']:03d}",
        "name": s['name'],
        "hall": hall,
        "district": by_slug[hall]['district'],
        "skill_id": skill_id,
        "strand": strand,
        "tier": tier,
        "room": room_of[strand],
        "lesson": s['lesson'],
        "checklist": s['checklist'],
        "doctrine": s['doctrine'],
        "actions": s['actions'],
        "quiz": s['quiz'],
        "color": s['color'],
    })

stamp = hashlib.sha256((ROOT / 'archive' / 'bac_yard_stations.json')
                       .read_bytes()).hexdigest()[:16]

doc = {
    "pack": "smartcitix-trade-craft-academy-station-registry",
    "product": "SmartCiti.X : Trade Craft Academy (powered by AGI Corp)",
    "pack_version": PACK_VERSION,
    "built": BUILT,
    "source_stamp": stamp,
    "count": len(stations),
    "halls_seeded": sorted({s['hall'] for s in stations}),
    "honesty": {
        "content": "recovered pre-rebrand yard curriculum, machine-gradable "
                   "but unverified general practice pending review by "
                   "journey-level practitioners",
        "assignment": "hall/strand/tier assignment is authored curation; "
                      "everything derived from it is computed from the "
                      "registries and verified by stations/test.mjs",
    },
    "stations": stations,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'stations.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"stations registry: {len(stations)} stations across "
      f"{len(doc['halls_seeded'])} halls (source stamp {stamp})")
