#!/usr/bin/env python3
"""Hall interiors, derived from what the pack actually knows about each trade.

WHAT THIS IS NOT BUILT FROM: street addresses. No address data for any union
hall exists in this pack, and none was collected. Inventing addresses for real
trades would put fabricated records on a page shown to investors and partners,
so every interior carries an explicit empty `site` block instead, ready for
real survey data when there is some.

WHAT IT IS BUILT FROM, all of it real pack data:
  - the 11 skill strands each hall owns, which are already a functional
    programme for a training building (safety -> induction, tools -> crib,
    machines -> bay, procedure -> practice bays, and so on);
  - the hall's focus line, whose nouns name the trade-specific fixtures a
    welding hall or a smelter needs and a drywall hall does not;
  - the pipeline state of its 100 levels, which says how much of the hall is
    actually commissioned rather than drawn.

So a room exists because a strand requires it, and a fixture exists because the
trade's own focus line names it. Nothing here is decoration.
"""
import json, pathlib, re

def _pack_root():
    """Walk up until we find the pack, rather than assuming a layout.

    The working tree keeps this file beside `pack/`; the bundle keeps it in
    `web/`, one level down. Resolving against `__file__.parent` alone is
    exactly the v2.6 defect-13 shape — a path that only works from where the
    author happened to put it — so this looks for the directory that actually
    holds the pack.
    """
    here = pathlib.Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / 'pack' / 'registry' / 'halls.json').exists():
            return cand
    raise FileNotFoundError('cannot locate the pack from ' + str(here))


ROOT = _pack_root()

# strand -> room. The programme is the same in every hall because every hall
# teaches the same 11 strands; what differs is size, fixtures and commissioning.
ROOMS = [
    ("safety",         "Induction & PPE",   3, 2, "Gowning, atmospheric checks, permit board"),
    ("procedure",      "Practice Bays",     6, 3, "The floor the trade is actually learned on"),
    ("machines",       "Equipment Bay",     5, 3, "Plant checked out to a training area"),
    ("tools",          "Tool Crib",         3, 2, "Issue, calibration and return"),
    ("materials",      "Materials Store",   3, 2, "Stock, offcuts and consumables"),
    ("layout",         "Layout Floor",      4, 2, "Setting out, control points, marking"),
    ("inspection",     "Inspection Bench",  3, 2, "Acceptance criteria and sign-off"),
    ("troubleshooting","Diagnostic Bench",  3, 2, "Fault-finding against live rigs"),
    ("coordination",   "Briefing Room",     4, 2, "Shift start, hand-offs, cross-trade"),
    ("documentation",  "Records",           2, 2, "Permits, certificates, as-builts"),
    ("leadership",     "Classroom",         4, 2, "Level tests and the instructor track"),
]
assert len({r[0] for r in ROOMS}) == 11

# focus-line noun -> (room it belongs in, fixture). A fixture is placed only
# when the hall's OWN focus line names it, so no hall gets equipment it has no
# stated use for.
FIXTURES = {
    "weld":       ("Practice Bays",    "welding booths, fume extraction"),
    "brazing":    ("Practice Bays",    "brazing station, purge gas"),
    "rigging":    ("Equipment Bay",    "rigging loft, load cells"),
    "lifting":    ("Equipment Bay",    "gantry, test weights"),
    "crane":      ("Equipment Bay",    "crane simulator cab"),
    "scaffold":   ("Practice Bays",    "scaffold tower, tag station"),
    "concrete":   ("Practice Bays",    "pour bay, slump and cylinder rack"),
    "masonry":    ("Practice Bays",    "brick panels, mortar bench"),
    "refractory": ("Practice Bays",    "lining mock-up, gunning rig"),
    "furnace":    ("Equipment Bay",    "furnace mock-up, tapping trough"),
    "molten":     ("Equipment Bay",    "hot-metal handling rig"),
    "moulding":   ("Practice Bays",    "moulding floor, pattern store"),
    "piping":     ("Practice Bays",    "pipe spools, pressure test rig"),
    "hydronic":   ("Practice Bays",    "hydronic loop rig"),
    "duct":       ("Practice Bays",    "duct fabrication bench, brake"),
    "glazing":    ("Practice Bays",    "curtain-wall frame, suction lifters"),
    "membrane":   ("Practice Bays",    "roof deck mock-up, torch bay"),
    "coating":    ("Practice Bays",    "spray booth, containment"),
    "insulation": ("Practice Bays",    "lagging bench, firestop panels"),
    "board":      ("Practice Bays",    "stud walls, finish level panels"),
    "tile":       ("Practice Bays",    "substrate beds, wet room"),
    "terrazzo":   ("Practice Bays",    "pour and grind bay"),
    "plaster":    ("Practice Bays",    "run-mould bench, three-coat panels"),
    "carpet":     ("Practice Bays",    "substrate panels, seam bench"),
    "relay":      ("Diagnostic Bench", "relay test set, breaker trainer"),
    "control":    ("Diagnostic Bench", "loop simulator, controller rack"),
    "plc":        ("Diagnostic Bench", "PLC trainer rack, safety relays"),
    "robot":      ("Equipment Bay",    "robot cell with safeguarding"),
    "fibre":      ("Inspection Bench", "fusion splicer, OTDR bench"),
    "fiber":      ("Inspection Bench", "fusion splicer, OTDR bench"),
    "cabling":    ("Practice Bays",    "pathway rack, certification tester"),
    "metering":   ("Inspection Bench", "meter test board, CT/PT set"),
    "transformer":("Equipment Bay",    "transformer bay, switching mimic"),
    "conductor":  ("Equipment Bay",    "pole yard, stringing rig"),
    "transmission":("Equipment Bay",   "EHV structure, live-line trainer"),
    "wellhead":   ("Equipment Bay",    "wellhead trainer, brine loop"),
    "turbine":    ("Equipment Bay",    "nacelle trainer, climb tower"),
    "blade":      ("Equipment Bay",    "blade section, torque rig"),
    "inverter":   ("Diagnostic Bench", "inverter bench, string tester"),
    "electrolys": ("Equipment Bay",    "electrolyser skid, purity bench"),
    "rail":       ("Practice Bays",    "track panel, geometry gauge"),
    "signal":     ("Diagnostic Bench", "interlocking mimic, track circuit"),
    "catenary":   ("Equipment Bay",    "contact wire rig, isolation board"),
    "brake":      ("Diagnostic Bench", "brake rig, door trainer"),
    "hydraulic":  ("Diagnostic Bench", "hydraulic bench, circuit trainer"),
    "diesel":     ("Equipment Bay",    "engine stand, aftertreatment rig"),
    "excavation": ("Equipment Bay",    "trench box, shoring set"),
    "shoring":    ("Equipment Bay",    "needle beams, jacking rig"),
    "pile":       ("Equipment Bay",    "pile rig mock-up, integrity gear"),
    "demo":       ("Practice Bays",    "takedown frame, debris chute"),
    "blast":      ("Classroom",        "shot-design table, initiation trainer"),
    "ventilation":("Equipment Bay",    "vent duct rig, gas monitors"),
    "haulage":    ("Equipment Bay",    "haulage loop, conveyor section"),
    "diving":     ("Equipment Bay",    "wet pot, umbilical rack"),
    "underwater": ("Equipment Bay",    "wet pot, cutting rig"),
    "hull":       ("Practice Bays",    "hull section, fit-up jigs"),
    "cleanroom":  ("Induction & PPE",  "gowning airlock, particle counter"),
    "medical gas":("Inspection Bench", "purity bench, zone valve panel"),
    "asbestos":   ("Induction & PPE",  "negative-air enclosure, decon unit"),
    "abatement":  ("Induction & PPE",  "enclosure, HEPA and decon"),
    "decon":      ("Induction & PPE",  "decon shower, waste lock"),
    "confined":   ("Practice Bays",    "confined-space trainer, retrieval"),
    "rope":       ("Practice Bays",    "rope tower, anchor board"),
    "rescue":     ("Practice Bays",    "rescue trainer, litter station"),
    "spill":      ("Practice Bays",    "boom tank, recovery kit"),
    "survey":     ("Layout Floor",     "control pillars, GNSS base"),
    "gnss":       ("Layout Floor",     "GNSS base and rover"),
    "photogram":  ("Layout Floor",     "flight planning desk, targets"),
    "irrigation": ("Practice Bays",    "irrigation bed, controller board"),
    "turf":       ("Practice Bays",    "turf plots, mower yard"),
    "arbor":      ("Practice Bays",    "climb trees, rigging point"),
    "elevator":   ("Equipment Bay",    "hoistway trainer, controller"),
    "sprinkler":  ("Practice Bays",    "riser assembly, head bench"),
    "alarm":      ("Diagnostic Bench", "panel trainer, device loop"),
    "access control":("Diagnostic Bench","reader board, door controller"),
    "data cent":  ("Equipment Bay",    "white-space rack, busway"),
    "machining":  ("Practice Bays",    "lathe and mill bay, metrology"),
    "turning":    ("Practice Bays",    "lathe bay, metrology bench"),
    "die":        ("Practice Bays",    "die bench, tryout press"),
    "plating":    ("Practice Bays",    "plating line mock-up, waste bench"),
    "paint":      ("Practice Bays",    "spray booth, containment"),
    # Added after auditing which halls got nothing: 24 trades' focus lines used
    # vocabulary the first table missed, so their interiors came out generic —
    # which is the one outcome this module exists to avoid. Each key below is a
    # word that appears in some hall's OWN focus line.
    "formwork":   ("Practice Bays",    "formwork panels, shore stack"),
    "framing":    ("Practice Bays",    "stud walls, framing jigs"),
    "alignment":  ("Inspection Bench", "laser alignment set, dial gauges"),
    "vibration":  ("Diagnostic Bench", "vibration analyser, balance rotor"),
    "haul":       ("Equipment Bay",    "yard tractor, load securement rack"),
    "logistics":  ("Records",          "dispatch board, manifest desk"),
    "storage":    ("Practice Bays",    "tank shell course, seam jig"),
    "hydrotest":  ("Inspection Bench", "hydrotest pump, gauge board"),
    "termination":("Practice Bays",    "MV termination kits, splice bench"),
    "mains":      ("Practice Bays",    "main and service rig, tapping bench"),
    "hydrant":    ("Practice Bays",    "hydrant assembly, valve stack"),
    "sludge":     ("Equipment Bay",    "clarifier model, blower skid"),
    "treatment":  ("Equipment Bay",    "treatment train mock-up"),
    "rack":       ("Equipment Bay",    "battery rack, BMS bench"),
    "thermal runaway":("Induction & PPE","thermal event drill area"),
    "dcfc":       ("Equipment Bay",    "DC fast charger, service board"),
    "banker":     ("Practice Bays",    "banker benches, carving stone"),
    "lettering":  ("Layout Floor",     "lettering templates, setting-out slab"),
    "stud":       ("Practice Bays",    "metal stud runs, ceiling grid"),
    "ceiling":    ("Practice Bays",    "grid rig, hanger board"),
    "unitised":   ("Practice Bays",    "unitised panel bay, anchor rig"),
    "water test": ("Inspection Bench", "water-test spray rack"),
    "penetration":("Practice Bays",    "penetration panels, listed systems rack"),
    "isolation":  ("Practice Bays",    "isolation mock-ups, STC chamber"),
    "panel":      ("Practice Bays",    "panel bay, substructure rails"),
    "tendon":     ("Practice Bays",    "tendon bed, stressing jack"),
    "stressing":  ("Equipment Bay",    "stressing jack, elongation board"),
    "bolting":    ("Practice Bays",    "connection frames, torque rig"),
    "plumbing up":("Layout Floor",     "plumb-up rig, survey targets"),
    "bacnet":     ("Diagnostic Bench", "DDC controller rack, BACnet bench"),
    "scada":      ("Diagnostic Bench", "SCADA station, historian bench"),
    "gse":        ("Equipment Bay",    "GSE apron, de-icing rig"),
    "ramp":       ("Practice Bays",    "marked ramp bay, turnaround drill"),
    "airside":    ("Induction & PPE",  "airside escort briefing, hi-vis store"),
    "pavement":   ("Practice Bays",    "pavement slab, marking bay"),
    "ndt":        ("Inspection Bench", "NDT bench, calibration blocks"),
    "moisture":   ("Diagnostic Bench", "moisture meters, drying rig"),
    "containment":("Induction & PPE",  "containment enclosure, HEPA"),
    "permit":     ("Records",          "permit board, JHA desk"),
    "audit":      ("Records",          "audit desk, incident files"),
}

# Pipeline state -> commissioning of a room. A hall whose late levels are still
# draft is not fully built, and the plan says so rather than drawing it solid.
def commissioning(states):
    live = states.get("live", 0) / max(1, sum(states.values()))
    if live >= 0.85: return "commissioned"
    if live >= 0.55: return "partial"
    if live >= 0.25: return "fitting-out"
    return "shell"


def fixtures_for(focus, name):
    """Only fixtures this trade's own words call for."""
    text = (focus + " " + name).lower()
    out = []
    for key, (room, fixture) in FIXTURES.items():
        if key in text and (room, fixture) not in out:
            out.append((room, fixture))
    return out


GRID = 12            # building is 12 grid units wide
UNIT_PX = 26         # how one grid unit is drawn in the plan
PAD_PX = 12          # label inset, left and right

# MEASURED, not estimated. Barlow Condensed 700 at 11px renders 7.275px per
# uppercase character in the browser — the same trap as the campus-plan label
# defect, where a guessed constant let an assertion pass while the text ran out
# of its box. Room widths are derived from this so the geometry guarantees the
# fit rather than the stylesheet hoping for it.
PX_PER_CHAR = 7.275          # Barlow Condensed 700, 11px, uppercase
CAPTION_PX_PER_CHAR = 4.4    # IBM Plex Mono 400, 7.2px


def min_units(label):
    """The narrowest room that can hold its own name."""
    need_px = len(label) * PX_PER_CHAR + PAD_PX * 2
    return max(1, -(-int(need_px) // UNIT_PX))


def plan_for(hall, states):
    """Lay the 11 rooms out inside the envelope. Deterministic, and the
    packing is asserted non-overlapping and in-bounds by the caller."""
    fx = fixtures_for(hall["focus"], hall["name"])
    by_room = {}
    for room, fixture in fx:
        by_room.setdefault(room, []).append(fixture)

    rooms, x, y, row_h = [], 0, 0, 0
    rows = []                       # index ranges, so the last room can fill
    for strand, label, w, h, purpose in ROOMS:
        # A room is at least wide enough for its own name, then earns one more
        # unit if this trade puts fixtures in it.
        w2 = max(w, min_units(label))
        if by_room.get(label) and w2 + 1 <= GRID:
            w2 += 1
        w2 = min(w2, GRID)
        if x + w2 > GRID:
            rows.append((len(rooms), x))
            x, y, row_h = 0, y + row_h, 0
        rooms.append({
            "strand": strand, "label": label, "purpose": purpose,
            "x": x, "y": y, "w": w2, "h": h,
            "fixtures": by_room.get(label, []),
        })
        x += w2
        row_h = max(row_h, h)
    rows.append((len(rooms), x))
    depth = y + row_h

    # Stretch the last room of each row out to the envelope. A plan with a
    # ragged right edge reads as unfinished drawing rather than as a building,
    # and the slack is real floor area that belongs to something.
    start = 0
    for end, filled in rows:
        if end > start and filled < GRID:
            rooms[end - 1]["w"] += GRID - filled
        start = end

    # The caption under each room carries its size and the strand that requires
    # it. On the narrowest rooms "documentation" and "troubleshooting" run past
    # the wall, so the caption is trimmed to what fits — measured, like the
    # label above it, rather than hoped for.
    for r in rooms:
        dims = f"{r['w'] * 3}x{r['h'] * 3}m"
        full = f"{dims} - {r['strand']}"
        room_px = r["w"] * UNIT_PX - PAD_PX
        r["caption"] = full if len(full) * CAPTION_PX_PER_CHAR <= room_px else dims
        assert len(r["caption"]) * CAPTION_PX_PER_CHAR <= room_px, (
            f"{hall['slug']}: caption '{r['caption']}' does not fit "
            f"{r['w'] * UNIT_PX}px")
    return {
        "slug": hall["slug"], "name": hall["name"], "focus": hall["focus"],
        "index": hall["index"],
        "envelope": {"w": GRID, "d": depth, "unit_m": 3},
        "rooms": rooms,
        "commissioning": commissioning(states),
        "fixture_count": len(fx),
        # Deliberately empty. See the module docstring.
        "site": {"address": None, "recorded": False,
                 "note": "No address data has been collected for this hall. "
                         "The plan is a functional programme derived from the "
                         "trade's own skill strands, not a survey of a building."},
    }


def build(halls, state_of):
    plans = {}
    for h in halls:
        p = plan_for(h, state_of(h["index"]))
        # no room may leave the envelope or overlap another
        for r in p["rooms"]:
            assert 0 <= r["x"] and r["x"] + r["w"] <= GRID, f"{h['slug']}: {r['label']} out of envelope"
            assert r["w"] * UNIT_PX >= len(r["label"]) * PX_PER_CHAR + PAD_PX, (
                f"{h['slug']}: '{r['label']}' needs "
                f"{len(r['label']) * PX_PER_CHAR + PAD_PX:.0f}px and its room is "
                f"{r['w'] * UNIT_PX}px")
            assert r["y"] + r["h"] <= p["envelope"]["d"], f"{h['slug']}: {r['label']} past the back wall"
        for i, a in enumerate(p["rooms"]):
            for b in p["rooms"][i + 1:]:
                if not (a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"]
                        or a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"]):
                    raise AssertionError(f"{h['slug']}: {a['label']} overlaps {b['label']}")
        plans[h["slug"]] = p
    return plans
