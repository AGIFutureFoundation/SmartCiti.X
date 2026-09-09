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
from unions111 import UNIONS_111, EXISTING_33, DISTRICTS  # noqa: E402

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

(OUT / "unions.json").write_text(json.dumps(unions_doc, indent=1) + "\n")
(OUT / "districts.json").write_text(json.dumps(districts_doc, indent=1) + "\n")
print(f"unions registry: {len(unions)} unions in {len(DISTRICTS)} districts "
      f"(source stamp {stamp})")
