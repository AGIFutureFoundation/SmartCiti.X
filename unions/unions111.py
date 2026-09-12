"""The 111-hall taxonomy — the source of the unions pack.

This file used to live inside the module pack, which coupled two different
truths: WHO the trades are (this roster and its districts) and WHAT the
Academy generates for them (the module skeleton). They are now separate
packs: `unions/` owns the roster and emits `unions/registry/`, and the
module pack in `pack/` consumes that registry rather than carrying its own
copy of the taxonomy. `unions/verify.mjs` proves the two agree.

The first 33 are the existing halls, unchanged and in their original order, so
every module ID minted under the 33-hall pack keeps its union index. The 78
that follow extend the network into trades the Academy had not covered.

HONESTY NOTE, carried into the pack manifest and every surface: this is a
TAXONOMY of skilled trades, not a roster of chartered locals. No union has
reviewed it, no local is named, and the grouping is ours. Where a name matches
a real trade classification that is because the trade is real, not because the
organisation has endorsed anything.
"""

EXISTING_33 = [
    ("ironworkers",    "Ironworkers",                 "Structural steel, rebar, rigging and connecting"),
    ("electricians",   "Electrical Workers",          "Power, control, low-voltage and code compliance"),
    ("pipefitters",    "Plumbers & Pipefitters",      "Process piping, drainage, medical gas and hydronics"),
    ("carpenters",     "Carpenters",                  "Framing, formwork, finish and layout"),
    ("operating-eng",  "Operating Engineers",         "Earthmoving, lifting and heavy plant operation"),
    ("laborers",       "Laborers",                    "Site prep, materials, excavation support and cleanup"),
    ("sheetmetal",     "Sheet Metal Workers",         "Duct fabrication, architectural metal and balancing"),
    ("bricklayers",    "Bricklayers & Allied Craft",  "Masonry, refractory, tile and stone"),
    ("cement-masons",  "Cement Masons",               "Placement, finishing, curing and decorative concrete"),
    ("roofers",        "Roofers & Waterproofers",     "Low-slope, steep-slope, membranes and moisture control"),
    ("painters",       "Painters & Allied Trades",    "Coatings, containment, industrial and decorative finish"),
    ("glaziers",       "Glaziers",                    "Curtain wall, storefront, glazing and sealants"),
    ("insulators",     "Heat & Frost Insulators",     "Mechanical insulation, abatement and firestopping"),
    ("millwrights",    "Millwrights",                 "Precision alignment, machinery install and vibration"),
    ("boilermakers",   "Boilermakers",                "Pressure vessels, tanks, tubes and code welding"),
    ("elevator",       "Elevator Constructors",       "Traction and hydraulic install, controls and testing"),
    ("teamsters",      "Teamsters",                   "Haul, delivery, logistics and vehicle compliance"),
    ("welders",        "Welding Trades",              "SMAW, GMAW, GTAW, FCAW, procedure and qualification"),
    ("hvacr",          "HVAC/R Technicians",          "Refrigeration, air systems, controls and commissioning"),
    ("crane-ops",      "Crane Operators",             "Mobile, tower and overhead lifting operations"),
    ("riggers",        "Riggers & Signalpersons",     "Load calculation, rigging hardware and signals"),
    ("heavy-equip",    "Heavy Equipment Technicians", "Diagnostics, hydraulics, drivetrain and field service"),
    ("drywall",        "Drywall Finishers",           "Board, level of finish, texture and acoustic assemblies"),
    ("flooring",       "Floor Coverers",              "Substrate prep, resilient, carpet, terrazzo and epoxy"),
    ("grounds",        "Grounds & Landscape",         "Mowing, trimming, irrigation, arbor and turf care"),
    ("line-workers",   "Utility Line Workers",        "Distribution, transmission, switching and storm work"),
    ("solar",          "Solar Installers",            "PV array, racking, inverters and interconnection"),
    ("wind",           "Wind Turbine Technicians",    "Nacelle systems, blades, climb rescue and torque"),
    ("demolition",     "Demolition Workers",          "Selective demo, structural takedown and debris control"),
    ("scaffold",       "Scaffold Erectors",           "System scaffold, shoring, suspended access and tags"),
    ("surveyors",      "Construction Surveyors",      "Layout, control networks, GNSS and as-builts"),
    ("fire-sprinkler", "Fire Sprinkler Fitters",      "Hydraulics, hangers, heads, testing and inspection"),
    ("hazmat",         "Hazmat & Environmental",      "Containment, decon, monitoring and disposal"),
]

NEW_78 = [
    # --- heavy industry & process -------------------------------------------
    ("refractory",     "Refractory Masons",           "Furnace linings, castables, gunning and dryout"),
    ("pipeline",       "Pipeline Trades",             "Mainline welding, coating, tie-ins and integrity digs"),
    ("tank-erectors",  "Tank Erectors",               "Field-erected storage, floating roofs and hydrotest"),
    ("shipfitters",    "Shipfitters",                 "Hull sections, tack and fit, alignment and launch"),
    ("marine-pipe",    "Marine Pipefitters",          "Shipboard systems, sea valves and pressure test"),
    ("divers",         "Commercial Divers",           "Underwater cutting, welding, inspection and lift bags"),
    ("blasters",       "Drillers & Blasters",         "Shot design, loading, initiation and vibration control"),
    ("miners",         "Underground Miners",          "Ground support, ventilation, haulage and rescue"),
    ("smelter",        "Smelter Operators",           "Furnace tapping, molten handling and pot lines"),
    ("foundry",        "Foundry Workers",             "Moulding, pouring, shakeout and heat treatment"),
    ("machinists",     "Machinists",                  "Turning, milling, CNC setup, metrology and fits"),
    ("toolmakers",     "Tool & Die Makers",           "Die build, jig and fixture, grinding and tryout"),
    ("fabricators",    "Structural Fabricators",      "Layout, cut, fit and weld-out in the shop"),
    ("platers",        "Platers & Coaters",           "Surface prep, electroplating, anodising and waste"),

    # --- energy & utilities -------------------------------------------------
    ("substation",     "Substation Technicians",      "Relays, breakers, transformers and switching orders"),
    ("cable-splicers", "Cable Splicers",              "MV/HV terminations, splices and cable fault work"),
    ("meter-techs",    "Meter Technicians",           "Metering, CT/PT, revenue accuracy and sealing"),
    ("gas-distrib",    "Gas Distribution Fitters",    "Mains, services, fusion, purging and leak survey"),
    ("water-distrib",  "Water Distribution Fitters",  "Mains, valves, hydrants, chlorination and tapping"),
    ("wastewater",     "Wastewater Operators",        "Treatment trains, blowers, sludge and permit limits"),
    ("nuclear",        "Nuclear Plant Trades",        "Rad-controlled work, ALARA, containment and outage"),
    ("hydro",          "Hydro Plant Trades",          "Turbines, wickets, gates, penstocks and governors"),
    ("geothermal",     "Geothermal Technicians",      "Wellhead, brine handling, scaling and binary cycle"),
    ("battery-storage","Battery Storage Technicians", "Racks, BMS, thermal runaway response and commissioning"),
    ("ev-charging",    "EV Charging Installers",      "Service upgrades, DCFC, networking and commissioning"),
    ("hydrogen",       "Hydrogen Systems Trades",     "Electrolysers, compression, purity and leak detection"),
    ("transmission",   "Transmission Linemen",        "EHV structures, conductor stringing and live-line work"),
    ("district-energy","District Energy Operators",   "Steam and chilled loops, vaults and metering"),

    # --- building trades & specialties ---------------------------------------
    ("masonry-restore","Masonry Restoration",         "Repointing, consolidation, Dutchman and cleaning"),
    ("stone-carvers",  "Stone Carvers",               "Banker work, lettering, tracery and matching"),
    ("plasterers",     "Plasterers",                  "Three-coat, veneer, ornamental run and repair"),
    ("terrazzo",       "Terrazzo Workers",            "Divider strips, pours, grinding and sealing"),
    ("tilesetters",    "Tile Setters",                "Substrates, waterproofing, large format and grout"),
    ("lathers",        "Lathers & Metal Framers",     "Metal stud, furring, ceiling grid and backing"),
    ("curtainwall",    "Curtain Wall Erectors",       "Unitised panels, anchors, sequencing and water test"),
    ("waterproofers",  "Below-Grade Waterproofers",   "Membranes, injection, drainage and blindside"),
    ("firestop",       "Firestop Installers",         "Penetrations, joints, listed systems and inspection"),
    ("acoustic",       "Acoustic Specialists",        "Isolation, mass-loaded assemblies and STC testing"),
    ("cladding",       "Rainscreen Cladding Fitters", "Substructure, panels, cavity drainage and tolerance"),
    ("shoring",        "Shoring & Underpinning",      "Needle beams, jacking, monitoring and sequencing"),
    ("piling",         "Piling Crews",                "Driven, bored, sheet piles, refusal and integrity"),
    ("concrete-pump",  "Concrete Pump Operators",     "Boom setup, ground bearing, line safety and cleanout"),
    ("post-tension",   "Post-Tension Technicians",    "Tendon layout, stressing, elongation and grouting"),
    ("precast",        "Precast Erectors",            "Yard to crane, connections, grouting and tolerance"),
    ("steel-erectors", "Steel Erectors",              "Detailing, plumbing up, bolting and connection safety"),
    ("decking",        "Metal Deck Installers",       "Layout, puddle welds, shear studs and edge form"),
    ("window-glazing", "Architectural Glaziers",      "Structural silicone, blast glazing and heritage sash"),

    # --- systems, controls & digital -----------------------------------------
    ("bas-controls",   "Building Automation Techs",   "DDC, BACnet, sequences of operation and tuning"),
    ("fire-alarm",     "Fire Alarm Technicians",      "Initiating and notification circuits, cause and effect"),
    ("security-sys",   "Security Systems Installers", "Access control, CCTV, intrusion and cabling standards"),
    ("network-cabling","Structured Cabling Techs",    "Copper and fibre, testing, labelling and pathways"),
    ("fiber-splicers", "Fiber Splicers",              "Fusion splicing, OTDR, loss budgets and closures"),
    ("data-center",    "Data Centre Technicians",     "White space, busway, CRAC/CRAH and change control"),
    ("instrumentation","Instrumentation Technicians", "Loop checks, calibration, transmitters and control valves"),
    ("plc-techs",      "PLC & Controls Technicians",  "Ladder logic, I/O, safety relays and commissioning"),
    ("robotics",       "Industrial Robotics Techs",   "Cells, teach pendants, safeguarding and payload"),
    ("automation-int", "Automation Integrators",      "SCADA, historians, protocols and cutover planning"),
    ("cleanroom",      "Cleanroom Trades",            "Classification, gowning, laminar flow and validation"),
    ("medical-gas",    "Medical Gas Installers",      "Brazing, purity, zone valves and verification"),

    # --- transport, logistics & mobility --------------------------------------
    ("rail-track",     "Rail Track Workers",          "Ballast, ties, rail laying, welds and geometry"),
    ("rail-signals",   "Rail Signal Technicians",     "Interlockings, track circuits, crossings and testing"),
    ("catenary",       "Overhead Catenary Linemen",   "Contact wire, tensioning, isolation and clearances"),
    ("transit-vehicle","Transit Vehicle Technicians", "Propulsion, brakes, doors and inspection cycles"),
    ("aviation-ground","Aviation Ground Support",     "GSE, ramp safety, de-icing and turnaround"),
    ("airfield",       "Airfield Trades",             "Lighting, markings, pavement and airside escort"),
    ("port-crane",     "Port Crane Technicians",      "STS and RTG cranes, spreaders, ropes and drives"),
    ("marine-terminal","Marine Terminal Operators",   "Mooring, loading arms, spill response and manifests"),
    ("fleet-diesel",   "Fleet Diesel Technicians",    "Aftertreatment, electrical, hydraulics and DOT checks"),
    ("bridge-inspect", "Bridge Inspection Crews",     "Access, NDT, fracture-critical members and reporting"),

    # --- environment, safety & site services ----------------------------------
    ("asbestos",       "Asbestos Abatement Workers",  "Enclosures, negative air, wet removal and clearance"),
    ("lead-abatement", "Lead Abatement Workers",      "Containment, HEPA, waste characterisation and clearance"),
    ("mold-remediation","Mould Remediation Techs",    "Moisture mapping, containment, drying and verification"),
    ("spill-response", "Spill Response Technicians",  "Booming, recovery, decon and incident command"),
    ("confined-space", "Confined Space Rescue",       "Atmospheric testing, retrieval, patient packaging"),
    ("high-angle",     "High-Angle Rescue",           "Rope systems, anchors, edge management and litter work"),
    ("site-safety",    "Site Safety Coordinators",    "Permits, JHAs, audits, incident investigation"),
    ("industrial-clean","Industrial Cleaning Crews",  "Hydroblasting, vacuum trucks, tank entry and decon"),
    ("survey-drone",   "Aerial Survey Operators",     "Flight planning, photogrammetry, airspace and accuracy"),
]

UNIONS_111 = EXISTING_33 + NEW_78
assert len(EXISTING_33) == 33
assert len(NEW_78) == 78
assert len(UNIONS_111) == 111
slugs = [u[0] for u in UNIONS_111]
assert len(set(slugs)) == 111, 'slugs must be unique'
assert all(s == s.lower() and ' ' not in s for s in slugs)


DISTRICTS = {
    'structural': ('Structural', 'Steel, welds, lifts and the loads they carry',
        ['ironworkers', 'welders', 'boilermakers', 'millwrights', 'riggers', 'crane-ops', 'steel-erectors', 'fabricators', 'shipfitters', 'decking', 'precast', 'piling']),
    'envelope': ('Envelope & Finish', 'Everything between the frame and the weather',
        ['carpenters', 'drywall', 'glaziers', 'roofers', 'bricklayers', 'cement-masons', 'flooring', 'painters', 'insulators', 'plasterers', 'terrazzo', 'tilesetters', 'lathers', 'curtainwall', 'waterproofers', 'firestop', 'acoustic', 'cladding', 'masonry-restore', 'stone-carvers', 'window-glazing']),
    'systems': ('Building Systems', 'Power, process, air, controls and data',
        ['electricians', 'pipefitters', 'hvacr', 'sheetmetal', 'fire-sprinkler', 'elevator', 'bas-controls', 'fire-alarm', 'security-sys', 'network-cabling', 'fiber-splicers', 'data-center', 'instrumentation', 'plc-techs', 'robotics', 'automation-int', 'cleanroom', 'medical-gas']),
    'energy': ('Energy & Utilities', 'Generation, distribution, water and storm work',
        ['line-workers', 'solar', 'wind', 'substation', 'cable-splicers', 'meter-techs', 'gas-distrib', 'water-distrib', 'wastewater', 'nuclear', 'hydro', 'geothermal', 'battery-storage', 'ev-charging', 'hydrogen', 'transmission', 'district-energy']),
    'earthworks': ('Earthworks & Plant', 'Ground, machines, access and haul',
        ['operating-eng', 'heavy-equip', 'laborers', 'demolition', 'teamsters', 'scaffold', 'grounds', 'shoring', 'concrete-pump', 'post-tension', 'blasters', 'miners']),
    'industry': ('Heavy Industry', 'Process plant, marine, metal and machine shops',
        ['refractory', 'pipeline', 'tank-erectors', 'marine-pipe', 'divers', 'smelter', 'foundry', 'machinists', 'toolmakers', 'platers']),
    'transport': ('Transport & Mobility', 'Rail, air, port and fleet',
        ['rail-track', 'rail-signals', 'catenary', 'transit-vehicle', 'aviation-ground', 'airfield', 'port-crane', 'marine-terminal', 'fleet-diesel', 'bridge-inspect']),
    'control': ('Survey, Safety & Environment', 'Where work is set out, made safe and made clean',
        ['surveyors', 'hazmat', 'asbestos', 'lead-abatement', 'mold-remediation', 'spill-response', 'confined-space', 'high-angle', 'site-safety', 'industrial-clean', 'survey-drone']),
}

_assigned = [s for _, _, v in DISTRICTS.values() for s in v]
assert len(_assigned) == 111, f'districts cover {len(_assigned)} halls, need 111'
assert set(_assigned) == set(slugs), 'district map must match the taxonomy exactly'
assert len(set(_assigned)) == 111, 'a hall may belong to exactly one district'


# ---------------------------------------------------------------- campuses --
# The network's planned campuses. Districts are assigned whole — a district
# trains where its trades cluster: structural, systems and finish work at
# the flagship island campus; heavy industry, port and plant on the Oakland
# waterfront; energy, water and environmental response on the Gulf.
#
# Houston and Chicago are a fourth kind of campus: a HUB. Each hosts no
# district of its own (districts: []) — every district that exists already
# has exactly one home among the three original campuses, and that
# invariant (asserted below) is not relaxed for either. Instead the
# chapters mechanic in unions/build.py, which already gives every hall a
# regional chapter at every campus that is not its home, does the rest for
# free: with a fourth and fifth campus in CAMPUSES, every one of the 111
# halls now also holds a regional chapter at Houston and at Chicago. Each
# hub is a real, walkable point on the network map, not a copy of anyone's
# home turf, and hosting two hubs is the same mechanic doing the same
# thing twice, not a special case written for either one.
#
# HONESTY, same rule as the taxonomy: these are PLANNED locations named for
# real cities. No site has been surveyed, no address is recorded, and no
# figure here comes from any city's records.
CAMPUSES = {
    'treasure-island': ('Treasure Island Campus', 'San Francisco', 'California',
        'The flagship: structure, systems and finish on the bay',
        ['structural', 'systems', 'envelope']),
    'oakland': ('Oakland Waterfront Campus', 'Oakland', 'California',
        'Port, plant and heavy industry on the working estuary',
        ['industry', 'transport', 'earthworks']),
    'new-orleans': ('Crescent Works Campus', 'New Orleans', 'Louisiana',
        'Energy, water and environmental response on the Gulf',
        ['energy', 'control']),
    'houston': ('Bayou Energy Hub', 'Houston', 'Texas',
        'The network\'s first hub: no home district of its own, and a '
        'regional chapter seat for every one of the 111 trades',
        []),
    'chicago': ('Loop Rail Hub', 'Chicago', 'Illinois',
        'The network\'s second hub: no home district of its own, and a '
        'regional chapter seat for every one of the 111 trades',
        []),
}

_hosted = [d for _, _, _, _, ds in CAMPUSES.values() for d in ds]
assert len(_hosted) == len(DISTRICTS), 'campuses must host every district'
assert set(_hosted) == set(DISTRICTS), 'campus map must match the districts exactly'
assert len(set(_hosted)) == len(_hosted), 'a district trains at exactly one campus'
_campus_halls = sum(len(DISTRICTS[d][2]) for d in _hosted)
assert _campus_halls == 111, f'campuses host {_campus_halls} halls, need 111'
