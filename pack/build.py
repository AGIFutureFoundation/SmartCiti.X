#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — module registry, 111-hall scale (ACP-10).

    111 halls x 100 levels x 110 slots = 1,221,000 lessons
    1,221,000 x 9 variants             = 10,989,000 core modules
    shared cross-trade library         =     11,000
                                       = 11,000,000

WHY THE SHARED LIBRARY IS SHARED, and not per-hall as it was at 33:
11,000,000 is not divisible by 111 (it leaves 11). A structure where every
hall holds an identical per-hall library therefore cannot close on this number
at all — the arithmetic says so before any design taste does. A single
cross-trade catalogue is also the better design at this scale: a machine
library duplicated 111 times is 111 copies of the same forklift.

WHY THE LESSON LAYER IS NOW GENERATED:
At 33 halls the pack enumerated every lesson row to disk — `35,937` rows, 6.9MB.
The same approach at 1,221,000 rows is roughly 235MB of JSON and a ~90MB
ledger, which no browser will load and no bundle should carry. So the authored
artefacts are the SKELETON — halls, the level ladder, the skill graph, the
library — and lesson rows are generated deterministically from it, exactly as
the 33-hall pack already generated the 9 variants from each lesson.

That makes "11,000,000 modules" a count of addressable module IDs, not of
hand-written lessons, and every surface has to say so. The manifest carries
`authored_objects` next to `total_modules` for precisely that reason.
"""
import json, pathlib, collections, sys

ROOT = pathlib.Path(__file__).resolve().parent

# The roster is the unions pack's truth, not this pack's: the module skeleton
# consumes the built union registry rather than carrying its own copy of the
# taxonomy. unions/verify.mjs proves the two packs agree after every build.
_roster = json.load(open(ROOT.parent / "unions" / "registry" / "unions.json"))
UNIONS_111 = [(u["slug"], u["name"], u["focus"]) for u in _roster["unions"]]
assert len(UNIONS_111) == 111

OUT = ROOT / "registry"
(OUT / "halls").mkdir(parents=True, exist_ok=True)

PACK_VERSION = "3.2.0"
SPEC = "ACP-10 / Adaptive Stack v3.2"
BUILT = "2026-09-09"
SEED = 20260905

HALLS = 111
LEVELS = 100
SLOTS = 110
LESSONS_PER_HALL = LEVELS * SLOTS          # 11,000
MODALITIES = ["vr_sim", "guided_drill", "quiz_reading"]
BANDS = ["support", "core", "stretch"]
VARIANTS = len(MODALITIES) * len(BANDS)    # 9
BAND_OFFSET = {"support": -5, "core": 0, "stretch": 5}
BAND_CEILING = {"support": 5, "core": 3, "stretch": 1}
SHARED_LIBRARY = 11_000

TOTAL = HALLS * LESSONS_PER_HALL * VARIANTS + SHARED_LIBRARY
assert TOTAL == 11_000_000, TOTAL

# The ladder: 100 levels in ten tracks of ten.
TRACKS = ["Orientation", "Pre-Apprentice", "Apprentice I", "Apprentice II",
          "Apprentice III", "Journey", "Journey Advanced", "Specialist",
          "Master", "Instructor"]
assert len(TRACKS) == 10

STRANDS = ["safety", "layout", "materials", "tools", "machines", "procedure",
           "inspection", "documentation", "coordination", "troubleshooting", "leadership"]
TIERS = ["fundamentals", "applied", "mastery"]
FORMS = ["principles", "setup", "execution", "verification", "faults", "handoff",
         "standards", "field case", "drill", "measurement", "planning"]
assert len(STRANDS) == 11 and len(FORMS) == 11 and SLOTS % len(STRANDS) == 0

STATES = ["draft", "schema_ok", "calibrating", "live"]


def track_of(level):
    return TRACKS[level // 10]


def tier_of(level):
    return TIERS[min(2, level // 34)]


def pipeline_state(hall_idx, level):
    """The build front, as a pure function of position.

    It has to be a function rather than a stored field: at 11 million rows a
    per-row state column is the single largest thing in the pack, and it is
    entirely derivable. The shape is the same one the 33-hall pack recorded —
    the halls opened earliest are furthest through the pipeline.
    """
    if hall_idx < 18:
        return "live" if level <= 88 else ("calibrating" if level <= 94 else "schema_ok")
    if hall_idx < 33:
        return "live" if level <= 70 else ("calibrating" if level <= 84 else "schema_ok")
    if hall_idx < 66:
        return ("live" if level <= 44 else "calibrating" if level <= 66
                else "schema_ok" if level <= 84 else "draft")
    return ("live" if level <= 22 else "calibrating" if level <= 44
            else "schema_ok" if level <= 70 else "draft")


def lesson_of(hall_idx, level, slot):
    """One lesson row, generated. This is the function the consumer library
    mirrors; the pack ships the skeleton and this rule, not 1.2 million rows."""
    uslug = UNIONS_111[hall_idx][0]
    strand = STRANDS[slot % 11]
    tier = tier_of(level)
    form = FORMS[(slot + level) % 11]
    base_d = round(14 + (level * SLOTS + slot) / (LESSONS_PER_HALL - 1) * 78, 1)
    return {
        "lesson_id": f"u{hall_idx:03d}.l{level:03d}.s{slot:03d}",
        "skill_id": f"{uslug}.{strand}.{tier}",
        "form": form,
        "base_difficulty": base_d,
        "state": pipeline_state(hall_idx, level),
        "level_test": slot == SLOTS - 1,
        "final_exam": slot == SLOTS - 1 and level % 10 == 9,
    }


# ------------------------------------------------------------------ halls ---
halls = []
for i, (slug, name, focus) in enumerate(UNIONS_111):
    halls.append({"slug": slug, "name": name, "focus": focus, "index": i,
                  "levels": LEVELS, "slots_per_level": SLOTS,
                  "lessons": LESSONS_PER_HALL, "modules": LESSONS_PER_HALL * VARIANTS,
                  "opened_wave": 1 if i < 33 else 2})
json.dump({"pack_version": PACK_VERSION, "count": HALLS, "halls": halls},
          open(OUT / "halls.json", "w"), separators=(",", ":"))

# ------------------------------------------------------------------ skills --
skills = []
for i, (uslug, uname, _) in enumerate(UNIONS_111):
    for strand in STRANDS:
        for ti, tier in enumerate(TIERS):
            requires = [f"{uslug}.{strand}.{TIERS[ti-1]}"] if ti > 0 else (
                [] if strand == "safety" else [f"{uslug}.safety.fundamentals"])
            supports = []
            if strand == "machines":
                supports.append(f"{uslug}.tools.{tier}")
            if strand == "troubleshooting":
                supports.append(f"{uslug}.inspection.{tier}")
            skills.append({
                "skill_id": f"{uslug}.{strand}.{tier}", "union": uslug,
                "strand": strand, "tier": tier,
                "label": f"{uname} — {strand.title()} ({tier})",
                "requires": requires, "supports": supports,
                "interferes": [f"{uslug}.inspection.{tier}"] if strand == "documentation" else [],
            })
json.dump({"count": len(skills), "skills": skills},
          open(OUT / "skills.json", "w"), separators=(",", ":"))

# ----------------------------------------------------------------- ladder ---
# One level-ladder record per hall: 100 rows describing the level, from which
# every lesson in it is generated. 111 x 100 = 11,100 authored records.
for i, (slug, name, focus) in enumerate(UNIONS_111):
    levels = []
    for lv in range(LEVELS):
        levels.append({
            "level": lv, "track": track_of(lv), "tier": tier_of(lv),
            "slots": SLOTS, "state": pipeline_state(i, lv),
            "difficulty_from": round(14 + (lv * SLOTS) / (LESSONS_PER_HALL - 1) * 78, 1),
            "difficulty_to": round(14 + (lv * SLOTS + SLOTS - 1) / (LESSONS_PER_HALL - 1) * 78, 1),
            "level_test": {"questions": 33, "pass_pct": 80},
        })
    json.dump({"union": slug, "union_name": name, "focus": focus, "union_index": i,
               "levels": levels, "lessons": LESSONS_PER_HALL,
               "check": {"type": "five_option", "count": 1}},
              open(OUT / "halls" / f"{slug}.json", "w"), separators=(",", ":"))

# ---------------------------------------------------------------- library ---
KINDS = [("mach", "machine", 4_400), ("tool", "tool", 4_400),
         ("ifc", "interface", 1_100), ("ppe", "protective", 1_100)]
assert sum(k[2] for k in KINDS) == SHARED_LIBRARY
library = []
for prefix, kind, n in KINDS:
    for j in range(n):
        library.append({"item_id": f"{prefix}{j:04d}", "kind": kind,
                        "state": "live" if j % 5 else "calibrating"})
json.dump({"count": len(library), "shared": True, "items": library},
          open(OUT / "library.json", "w"), separators=(",", ":"))

json.dump({"modalities": MODALITIES, "bands": BANDS,
           "band_offset": BAND_OFFSET, "band_scaffold_ceiling": BAND_CEILING,
           "variants_per_lesson": VARIANTS},
          open(OUT / "variants.json", "w"), separators=(",", ":"))

# --------------------------------------------------------------- manifest ---
authored = HALLS + len(skills) + HALLS * LEVELS + len(library) + 1
state_counts = collections.Counter()
for i in range(HALLS):
    for lv in range(LEVELS):
        state_counts[pipeline_state(i, lv)] += SLOTS * VARIANTS
for it in library:
    state_counts[it["state"]] += 1
assert sum(state_counts.values()) == TOTAL

manifest = {
    "pack": "smartcitix-trade-craft-academy-module-registry",
    "product": "SmartCiti.X : Trade Craft Academy (powered by AGI Corp)",
    "pack_version": PACK_VERSION, "spec": SPEC, "built": BUILT,
    "deterministic_seed": SEED,
    "ledger": {
        "halls": HALLS, "levels_per_hall": LEVELS, "slots_per_level": SLOTS,
        "lessons_per_hall": LESSONS_PER_HALL,
        "core_lessons": HALLS * LESSONS_PER_HALL,
        "variants_per_lesson": VARIANTS,
        "core_modules": HALLS * LESSONS_PER_HALL * VARIANTS,
        "shared_library_modules": SHARED_LIBRARY,
        "total_modules": TOTAL,
    },
    "authored_objects": authored,
    "generated_to_authored_ratio": round(TOTAL / authored, 1),
    "enumeration": "generative",
    "honesty": {
        "modules_are": "addressable module IDs, generated from the authored skeleton",
        "not": "11,000,000 hand-written lessons",
        "taxonomy": "a taxonomy of skilled trades, not a roster of chartered locals; "
                    "no union has reviewed or endorsed it",
        "content": "lesson content is unverified general practice pending authoring "
                   "by journey-level practitioners",
    },
    "by_state": dict(state_counts),
}
json.dump(manifest, open(ROOT / "manifest.json", "w"), indent=2)

print(f"pack {PACK_VERSION}: {TOTAL:,} modules across {HALLS} halls")
print(f"  authored objects : {authored:,}  (ratio {TOTAL/authored:.0f}x)")
print(f"  by state         : " + ", ".join(f"{k} {v:,}" for k, v in sorted(state_counts.items())))
import subprocess
print("  on disk          : " + subprocess.run(['du','-sh',str(OUT)],capture_output=True,text=True).stdout.split()[0])
