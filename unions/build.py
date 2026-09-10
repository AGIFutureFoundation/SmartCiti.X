#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the unions pack builder.

Emits the union registry: the roster of 111 trade halls and the eight
districts that group them. This is deliberately a SEPARATE pack from the
module registry in `pack/` — the roster answers "who are the trades", the
module pack answers "what does the Academy generate for them", and coupling
the two in one directory is how a change to one silently became a change to
the other. The module pack consumes this registry; `unions/verify.mjs`
proves the two agree instead of trusting them to.

The registry carries a source stamp — a hash of unions111.py — so a stale
build is detectable, the same shape as the console's staleness guard.

HONESTY NOTE, carried into every artefact this emits: this is a taxonomy of
skilled trades, not a roster of chartered locals. No union has reviewed it,
no local is named, and the grouping is ours.
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from unions111 import UNIONS_111, EXISTING_33, DISTRICTS, CAMPUSES  # noqa: E402

PACK_VERSION = "3.2.0"
BUILT = "2026-09-09"

OUT = ROOT / "registry"
OUT.mkdir(parents=True, exist_ok=True)


def source_stamp():
    """Hash of the authored taxonomy, so a consumer can detect a stale build."""
    return hashlib.sha256((ROOT / "unions111.py").read_bytes()).hexdigest()[:16]


district_of = {}
for key, (_name, _tag, members) in DISTRICTS.items():
    for slug in members:
        assert slug not in district_of, f"{slug} appears in two districts"
        district_of[slug] = key

unions = []
for i, (slug, name, focus) in enumerate(UNIONS_111):
    unions.append({
        "index": i,
        "slug": slug,
        "name": name,
        "focus": focus,
        "district": district_of[slug],
        "cohort": "existing-33" if i < len(EXISTING_33) else "new-78",
    })

stamp = source_stamp()

unions_doc = {
    "pack": "smartcitix-trade-craft-academy-union-registry",
    "product": "SmartCiti.X : Trade Craft Academy (powered by AGI Corp)",
    "pack_version": PACK_VERSION,
    "built": BUILT,
    "source_stamp": stamp,
    "count": len(unions),
    "cohorts": {"existing-33": len(EXISTING_33),
                "new-78": len(UNIONS_111) - len(EXISTING_33)},
    "honesty": {
        "taxonomy": "a taxonomy of skilled trades, not a roster of chartered "
                    "locals; no union has reviewed or endorsed it",
    },
    "unions": unions,
}

districts_doc = {
    "pack": "smartcitix-trade-craft-academy-union-registry",
    "pack_version": PACK_VERSION,
    "built": BUILT,
    "source_stamp": stamp,
    "count": len(DISTRICTS),
    "districts": {
        key: {"name": name, "tagline": tag, "halls": members}
        for key, (name, tag, members) in DISTRICTS.items()
    },
}

campus_of = {}
for ckey, (_n, _city, _region, _tag, dists) in CAMPUSES.items():
    for d in dists:
        campus_of[d] = ckey

campuses_doc = {
    "pack": "smartcitix-trade-craft-academy-union-registry",
    "pack_version": PACK_VERSION,
    "built": BUILT,
    "source_stamp": stamp,
    "count": len(CAMPUSES),
    "honesty": {
        "siting": "planned locations named for real cities; no site has been "
                  "surveyed, no address is recorded, and no figure comes "
                  "from any city's records",
    },
    "campuses": {
        ckey: {"name": n, "city": city, "region": region, "tagline": tag,
               "districts": dists,
               "halls": [s for d in dists for s in DISTRICTS[d][2]]}
        for ckey, (n, city, region, tag, dists) in CAMPUSES.items()
    },
}

# ---------------------------------------------------------- chapters -------
# The regional chapter network: every hall keeps its HOME campus (where its
# district lives) and holds a regional chapter at each of the other two, so
# all 111 trades train in all three regions. This is the Academy's own
# regional structure - a design decision about planned campuses, NOT a claim
# about any real union's locals, chapters or jurisdictions; the taxonomy
# honesty note governs here too, and no local is named.
REGION_ABBR = {"treasure-island": "SF", "oakland": "OAK", "new-orleans": "NOLA"}

chapters = {}
for u in unions:
    home = campus_of[u["district"]]
    chapters[u["slug"]] = {
        "home": home,
        "home_code": f'{u["slug"]}@{REGION_ABBR[home]}',
        "regional": {
            ck: {"code": f'{u["slug"]}@{REGION_ABBR[ck]}',
                 "role": "regional chapter"}
            for ck in CAMPUSES if ck != home
        },
    }

hosted = {ck: sum(1 for c in chapters.values() if ck in c["regional"])
          for ck in CAMPUSES}
for ck, camp in campuses_doc["campuses"].items():
    assert hosted[ck] == len(unions) - len(camp["halls"]), \
        f"hosted count mismatch at {ck}"

chapters_doc = {
    "pack": "smartcitix-trade-craft-academy-union-registry",
    "pack_version": PACK_VERSION,
    "built": BUILT,
    "source_stamp": stamp,
    "count": sum(1 + len(c["regional"]) for c in chapters.values()),
    "regions": {ck: {"abbr": REGION_ABBR[ck],
                     "name": CAMPUSES[ck][0], "city": CAMPUSES[ck][1]}
                for ck in CAMPUSES},
    "hosted": hosted,
    "honesty": {
        "chapters": "the Academy's own regional training structure across "
                    "its planned campuses - not a claim about any real "
                    "union's locals, chapters or jurisdictions; no local "
                    "is named",
    },
    "chapters": chapters,
}

(OUT / "unions.json").write_text(json.dumps(unions_doc, indent=1) + "\n")
(OUT / "districts.json").write_text(json.dumps(districts_doc, indent=1) + "\n")
(OUT / "campuses.json").write_text(json.dumps(campuses_doc, indent=1) + "\n")
(OUT / "chapters.json").write_text(json.dumps(chapters_doc, indent=1) + "\n")
print(f"unions registry: {len(unions)} unions in {len(DISTRICTS)} districts "
      f"across {len(CAMPUSES)} campuses; {chapters_doc['count']} chapter "
      f"seats ({len(unions)} homes + "
      f"{chapters_doc['count'] - len(unions)} regional) "
      f"(source stamp {stamp})")
