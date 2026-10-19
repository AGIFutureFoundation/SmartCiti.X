#!/usr/bin/env python3
"""respond/ - the first-responder and disaster-relief training scaffold.

WHAT THIS PACK IS, AND THE ONE THING IT REFUSES TO BE

The bundle teaches 111 building trades. A building that is being built is
also a building that can burn, fall, flood, leak or strand somebody, and
the people who turn up when that happens are a workforce too: fire
service, law enforcement, EMS, emergency management and disaster relief,
and the social workers and crisis responders who carry the part of the
call that has no hose or handcuff in it. They have role tiers, they have
apprenticeships by another name, they have unions and professional
associations, and they have standards bodies. That is a training pack
shaped like every other training pack in this bundle.

It is also the one domain in this bundle where being wrong can kill
somebody who trusted the page. So this pack is a SCAFFOLD and never a
PROTOCOL. Concretely, and enforced by assertions at the bottom of this
file:

  * no procedure, no step order for an operational task
  * no drug, no dose, no route, no rate
  * no triage cut-off, no vital-sign threshold, no timing
  * no tactical entry, arrest, restraint or control technique
  * no flow rate, pressure, air-time or distance figure

What it DOES carry is the part a training programme needs before any of
that: who the roles are, what the competency domains are, why each one
matters, WHICH REAL BODY OWNS THE ACTUAL STANDARD, what a debrief would
watch for, and structured scenario frames that create decision pressure
without telling anybody what to do. When a reader wants the protocol,
this pack's job is to hand them the name of the body that owns it and get
out of the way.

PROVENANCE: AUTHORED, ALL OF IT

This build has no network. Every standards host - NFPA, NREMT, FEMA, the
state POST commissions, NASW - is unreachable from here, and none was
opened. So every authority record carries `document_read_by_this_build:
false` and no URL, because a URL nobody opened is a citation costume.
Nothing here is RECORDED and nothing is DERIVED from a fetched document.
The tier is AUTHORED and the honesty block says so in its first clause.
The word reserved for orbis/ does not appear.

THE UNIONS AND ASSOCIATIONS

IAFF, FOP, NAGE, AFSCME, SEIU, NASW and the rest are real organizations
with real members. This pack names them as ORGANIZATION TYPES and states
what kind of body each is. It names no local, lodge, chapter or council
number, no officer and no member, and every service record carries
`endorsement: None` with a sentence saying outright that no organization
has reviewed or endorsed a line of this. The union pack next door already
holds that line for the trades; this pack holds it for the services.

SIGN-OFF IS A MECHANISM WITH NOTHING IN IT

Every training item here - every role tier, every competency, every
scenario frame - carries `authority`, `signed_off_by: None` and
`needs_practitioner_review: True`. The bundle's widest gap is
pack.signed_off_halls at 0/111. This pack publishes the same shape of
number for responder content, and it reads 0 of however many items this
build produced. It is computed from the items, not typed.
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'respond.json'

HALLS_PATH = 'pack/registry/halls.json'
CAMPUSES_PATH = 'unions/registry/campuses.json'
FINISHES_PATH = 'surfaces/registry/finishes.json'
MANIFEST_PATH = 'pack/manifest.json'


def need(d, key, what):
    """Read a key that must be there. A default here would be a policy
    decision about somebody's training, and section 23.1 of the spec says
    a default is a policy decision. Missing data stops the build and the
    error names itself and the path it was reading."""
    if not isinstance(d, dict):
        raise TypeError('respond: %s: expected a mapping to read %r from, '
                        'got %s' % (what, key, type(d).__name__))
    if key not in d:
        raise KeyError('respond: %s: no key %r (it holds %r)'
                       % (what, key, sorted(d)[:12]))
    return d[key]


def need_in(seq, value, what):
    """The same fail-closed read for membership. An unresolvable hall slug
    or an unknown authority id stops the build rather than being quietly
    dropped or invented."""
    if value not in seq:
        near = sorted(s for s in seq if isinstance(s, str)
                      and s[:3] == str(value)[:3])[:6]
        raise KeyError('respond: %s: %r does not resolve (nearest by prefix: '
                       '%r). This pack does not invent identifiers.'
                       % (what, value, near))
    return value


def jload(rel):
    p = ROOT / rel
    if not p.is_file():
        raise SystemExit('respond: %s is not on disk; this pack reads it '
                         'rather than restating it' % rel)
    return json.loads(p.read_text())


PACK_VERSION = need(jload(MANIFEST_PATH), 'pack_version', MANIFEST_PATH)

HALL_RECORDS = need(jload(HALLS_PATH), 'halls', HALLS_PATH)
HALL_NAME = {need(h, 'slug', HALLS_PATH + '#halls[]'):
             need(h, 'name', HALLS_PATH + '#halls[]') for h in HALL_RECORDS}
HALL_SLUGS = sorted(HALL_NAME)
N_HALLS = len(HALL_SLUGS)

CAMPUSES = need(jload(CAMPUSES_PATH), 'campuses', CAMPUSES_PATH)
HALL_CAMPUS = {}
for _ck, _c in CAMPUSES.items():
    for _s in need(_c, 'halls', CAMPUSES_PATH + '#campuses.' + _ck):
        need_in(HALL_NAME, _s, CAMPUSES_PATH + '#campuses.%s.halls' % _ck)
        HALL_CAMPUS[_s] = _ck

FIN_HALLS = need(jload(FINISHES_PATH), 'halls', FINISHES_PATH)


# ---------------------------------------------------------------------------
# THE AUTHORITIES. Each one is a real body that owns a real standard. This
# pack names the body and describes its remit in its own words as far as
# this build can honestly state them; it reproduces none of its content.
# `document_read_by_this_build` is False for every one of them and that is
# not a placeholder - this environment has no network and no standards
# document was opened.

AUTHORITIES = {
    'nfpa': {
        'name': 'National Fire Protection Association',
        'kind': 'standards-development organization',
        'owns': 'the professional qualification standards for fire service '
                'roles and the codes those roles work against',
        'this_pack_reproduces': 'none of it - the body is named so a reader '
                                'goes to the source for the actual '
                                'requirement',
    },
    'fire-accrediting-bodies': {
        'name': 'fire service certification accrediting bodies',
        'kind': 'certification accreditation bodies',
        'owns': 'accreditation of the agencies that issue fire service '
                'certificates, and therefore whether a certificate travels '
                'between states',
        'this_pack_reproduces': 'none of it - no certificate, reciprocity '
                                'claim or equivalency is asserted here',
    },
    'state-fire-marshal': {
        'name': 'the state fire marshal or state fire training authority',
        'kind': 'state regulator',
        'owns': 'what a firefighter in that state must hold, and the '
                'delivery of the training that leads to it',
        'this_pack_reproduces': 'none of it - requirements differ by state '
                                'and this pack states none of them',
    },
    'ahj': {
        'name': 'the authority having jurisdiction',
        'kind': 'local regulator or agency head',
        'owns': 'the operating procedure that actually binds on a given '
                'incident, which is local and is not this pack',
        'this_pack_reproduces': 'none of it - an SOP belongs to the agency '
                                'that wrote it',
    },
    'state-post': {
        'name': 'the state Peace Officer Standards and Training commission',
        'kind': 'state licensing and standards commission',
        'owns': 'law enforcement certification, the minimum training '
                'curriculum, and decertification',
        'this_pack_reproduces': 'none of it - no curriculum content, no '
                                'hours and no standard is restated',
    },
    'law-enforcement-accreditation': {
        'name': 'law enforcement agency accreditation bodies',
        'kind': 'voluntary accreditation body',
        'owns': 'written-directive standards an agency is assessed against',
        'this_pack_reproduces': 'none of it',
    },
    'courts': {
        'name': 'the courts and the constitutional case law they produce',
        'kind': 'judiciary',
        'owns': 'the limits on state authority that every officer works '
                'inside, which move and are not a training pack\'s to state',
        'this_pack_reproduces': 'none of it - no holding, no test and no '
                                'element is summarised here',
    },
    'nremt': {
        'name': 'the National Registry of Emergency Medical Technicians',
        'kind': 'national certification body',
        'owns': 'the national EMS certification examinations and the '
                'practice analysis behind them',
        'this_pack_reproduces': 'none of it',
    },
    'national-ems-scope-model': {
        'name': 'the national EMS scope of practice model and the state EMS '
                'office that adopts it',
        'kind': 'federal model document and state regulator',
        'owns': 'what each certification level may and may not do, which is '
                'set by the state and not by a training vendor',
        'this_pack_reproduces': 'none of it - no skill is listed as in or '
                                'out of any level\'s scope here',
    },
    'ems-medical-director': {
        'name': 'the EMS agency medical director',
        'kind': 'named physician with delegated practice authority',
        'owns': 'the clinical protocol, the standing orders and every dose '
                'in them; a paramedic practises on that physician\'s licence',
        'this_pack_reproduces': 'none of it - there is no drug, dose, route '
                                'or clinical threshold anywhere in this pack '
                                'and there never will be',
    },
    'fema-nims': {
        'name': 'FEMA and the National Incident Management System',
        'kind': 'federal doctrine and training programme',
        'owns': 'the incident command structure, its position descriptions '
                'and the resource typing everything else refers to',
        'this_pack_reproduces': 'none of it - ICS positions are named as '
                                'names, and the doctrine is left where it is',
    },
    'em-accreditation': {
        'name': 'the emergency management accreditation programme',
        'kind': 'voluntary programme accreditation body',
        'owns': 'the standard a state or local emergency management '
                'programme is assessed against',
        'this_pack_reproduces': 'none of it',
    },
    'em-professional-association': {
        'name': 'the professional association of emergency managers',
        'kind': 'professional association and credentialing body',
        'owns': 'the voluntary individual credential for emergency managers '
                'and its competency framework',
        'this_pack_reproduces': 'none of it',
    },
    'exercise-programme-doctrine': {
        'name': 'the federal exercise and evaluation programme doctrine',
        'kind': 'federal doctrine',
        'owns': 'how an exercise is designed, conducted, evaluated and '
                'turned into an improvement plan',
        'this_pack_reproduces': 'none of it - the debrief structures below '
                                'are this pack\'s own scaffold and are not '
                                'that doctrine',
    },
    'voad': {
        'name': 'the voluntary organizations active in disaster network and '
                'its member relief organizations',
        'kind': 'coordinating network of non-governmental relief bodies',
        'owns': 'how voluntary and faith-based relief organizations '
                'coordinate with each other and with government',
        'this_pack_reproduces': 'none of it',
    },
    'nasw-code': {
        'name': 'the National Association of Social Workers code of ethics',
        'kind': 'professional association ethical code',
        'owns': 'the ethical standards a social worker is held to, '
                'including the ones that bite hardest in a disaster',
        'this_pack_reproduces': 'none of it - no standard is quoted or '
                                'paraphrased as if it were the code',
    },
    'state-social-work-board': {
        'name': 'the state social work licensing board',
        'kind': 'state licensing board',
        'owns': 'who may call themselves a social worker in that state, at '
                'what level, under what supervision',
        'this_pack_reproduces': 'none of it',
    },
    'social-work-accreditation': {
        'name': 'the social work education accreditation body',
        'kind': 'educational accreditation body',
        'owns': 'what an accredited social work degree must contain',
        'this_pack_reproduces': 'none of it',
    },
    'behavioral-health-agency': {
        'name': 'the federal behavioral health services agency and the '
                'state behavioral health authority',
        'kind': 'federal agency and state authority',
        'owns': 'crisis system guidance, the national crisis line standards '
                'and the service definitions underneath them',
        'this_pack_reproduces': 'none of it',
    },
    'health-privacy-law': {
        'name': 'federal health privacy law and the substance use disorder '
                'confidentiality regulation, as applied by state law',
        'kind': 'statute and regulation',
        'owns': 'what may be recorded, what may be said aloud and to whom',
        'this_pack_reproduces': 'none of it - no rule is summarised as if a '
                                'reader could rely on the summary',
    },
    'state-mandated-reporting-law': {
        'name': 'state mandated reporting statute',
        'kind': 'state statute',
        'owns': 'who must report what, to whom, and in what time',
        'this_pack_reproduces': 'none of it - the duty differs by state and '
                                'by role and a wrong summary here would be '
                                'worse than none',
    },
    'osha-and-state-plans': {
        'name': 'the federal occupational safety and health administration '
                'and the state plans that stand in for it',
        'kind': 'federal and state regulator',
        'owns': 'the worker-protection rules that bind on responders as '
                'employees, including the ones about entry and rescue',
        'this_pack_reproduces': 'none of it',
    },
    'employer-agency': {
        'name': 'the employing agency and, where one exists, the collective '
                'bargaining agreement',
        'kind': 'employer and negotiated agreement',
        'owns': 'staffing, duty hours, peer support access, discipline and '
                'the conditions a responder actually works under',
        'this_pack_reproduces': 'none of it - no agreement is quoted, '
                                'characterised or assumed to exist',
    },
}


# ---------------------------------------------------------------------------
# THE SERVICES. Role tiers are described by what the role IS, not by a
# rank name that differs between every agency in the country. The
# representing-organization field names TYPES of organization, gives the
# real acronyms where a reader would recognise them, and states plainly
# that none of them has endorsed anything here.

SERVICES = {
    'fire': {
        'name': 'Fire Service',
        'scope': 'fire suppression, rescue, hazardous materials response '
                 'and, in most of the country, the first medical response '
                 'as well',
        'standards_bodies': ['nfpa', 'fire-accrediting-bodies',
                             'state-fire-marshal', 'ahj', 'osha-and-state-plans'],
        'representation': {
            'kinds': ['international labour union of fire fighters and '
                      'fire-based emergency medical workers',
                      'professional association of fire chiefs and fire '
                      'officers',
                      'state and provincial associations of fire fighters'],
            'real_acronyms': ['IAFF', 'IAFC'],
            'what_they_do_here': 'they represent the workforce and the '
                                 'officers respectively; they are named as '
                                 'the kind of body a reader would go to, '
                                 'not as a party to this',
        },
        'tiers': [
            ('recruit', 'Recruit / probationary firefighter',
             'in an academy or a probationary period, working under direct '
             'supervision and not yet counted as a working member of a crew'),
            ('firefighter', 'Firefighter',
             'a working member of a crew, expected to hold their position on '
             'a task and to communicate what they find'),
            ('driver-operator', 'Driver / operator',
             'responsible for getting the apparatus there and for what it '
             'can then do; a technical role with its own qualification'),
            ('company-officer', 'Company officer',
             'supervises one company, owns its accountability, and is the '
             'first person on most incidents who is making decisions rather '
             'than executing them'),
            ('chief-officer', 'Chief officer',
             'commands multiple companies or an incident, and is '
             'accountable for strategy, risk and the people at it'),
            ('prevention-investigation', 'Prevention, inspection and '
             'investigation roles',
             'the side of the service that works before and after the '
             'incident: code enforcement, plan review, origin and cause'),
        ],
    },
    'law': {
        'name': 'Law Enforcement',
        'scope': 'patrol response, investigation, traffic, court process and '
                 'the scene-security role at almost every other service\'s '
                 'incidents',
        'standards_bodies': ['state-post', 'law-enforcement-accreditation',
                             'courts', 'ahj'],
        'representation': {
            'kinds': ['fraternal police organization',
                      'police labour union or benevolent association',
                      'public employee union representing civilian and '
                      'sworn staff',
                      'professional association of chiefs and sheriffs'],
            'real_acronyms': ['FOP', 'NAGE', 'AFSCME'],
            'what_they_do_here': 'representation in this service is split '
                                 'between fraternal bodies, bargaining '
                                 'units and chiefs\' associations, which '
                                 'want different things; the pack names the '
                                 'kinds rather than picking one',
        },
        'tiers': [
            ('cadet', 'Cadet / academy recruit',
             'in a basic academy, not yet certified, no independent '
             'authority to act'),
            ('probationary', 'Probationary officer in field training',
             'certified but riding with a field training officer; every '
             'decision is reviewed'),
            ('officer', 'Patrol officer / deputy',
             'working a beat alone or with a partner, making the first '
             'decision at most calls'),
            ('first-line-supervisor', 'First-line supervisor',
             'supervises a squad, reviews their reports and their force, and '
             'is the first accountability layer'),
            ('command', 'Mid-level command',
             'runs a shift, a district or a unit; sets the local priorities '
             'and owns the resourcing'),
            ('executive', 'Agency executive',
             'chief, sheriff or commissioner: accountable to a governing '
             'body and to the public for what the agency does'),
        ],
    },
    'ems': {
        'name': 'Emergency Medical Services',
        'scope': 'out-of-hospital emergency medical care and transport, '
                 'delivered from fire departments, third services, hospital '
                 'systems and private providers',
        'standards_bodies': ['nremt', 'national-ems-scope-model',
                             'ems-medical-director', 'ahj',
                             'osha-and-state-plans'],
        'representation': {
            'kinds': ['international labour union of fire fighters and '
                      'fire-based emergency medical workers',
                      'public employee union representing third-service and '
                      'county EMS staff',
                      'service employees union representing hospital-based '
                      'and private-provider EMS staff',
                      'professional association of emergency medical '
                      'technicians and paramedics'],
            'real_acronyms': ['IAFF', 'AFSCME', 'SEIU', 'NAEMT'],
            'what_they_do_here': 'who represents an EMS worker depends on '
                                 'who employs them, which is the single most '
                                 'confusing fact about this workforce and is '
                                 'recorded here rather than smoothed over',
        },
        'tiers': [
            ('emr', 'Emergency medical responder level',
             'the entry certification level; often held by people whose main '
             'job is something else entirely'),
            ('emt', 'Emergency medical technician level',
             'the level most of the workforce holds, and the level most '
             'transport crews are built around'),
            ('aemt', 'Advanced emergency medical technician level',
             'an intermediate level that exists in some states and not '
             'others, which is itself worth a learner knowing'),
            ('paramedic', 'Paramedic level',
             'the highest widely recognised out-of-hospital level, '
             'practising under a physician medical director\'s delegated '
             'authority'),
            ('field-supervisor', 'Field training officer / field supervisor',
             'supervises crews in the field, signs off new members and is '
             'the first review of a difficult call'),
            ('ems-officer', 'EMS officer / chief',
             'runs the service: staffing, quality, medical direction '
             'relationship, and the answer when it goes wrong'),
        ],
    },
    'em': {
        'name': 'Emergency Management and Disaster Relief',
        'scope': 'preparedness, coordination, sheltering, resource movement '
                 'and recovery - the work that happens above and around the '
                 'incident rather than at it',
        'standards_bodies': ['fema-nims', 'em-accreditation',
                             'em-professional-association',
                             'exercise-programme-doctrine', 'voad', 'ahj'],
        'representation': {
            'kinds': ['public employee union representing county, state and '
                      'municipal emergency management staff',
                      'federal-sector employee union',
                      'professional association of emergency managers',
                      'coordinating network of voluntary and faith-based '
                      'relief organizations'],
            'real_acronyms': ['AFSCME', 'NAGE', 'SEIU', 'IAEM'],
            'what_they_do_here': 'a great deal of disaster relief is done by '
                                 'volunteers and non-governmental bodies who '
                                 'have no bargaining unit at all, and a '
                                 'training scaffold that only described '
                                 'government staff would be describing a '
                                 'minority of the people in the building',
        },
        'tiers': [
            ('volunteer', 'Trained volunteer / community team member',
             'a neighbour with training, working inside a structure, not an '
             'employee of anything'),
            ('specialist', 'Emergency management specialist / planner',
             'writes the plans, runs the exercises, maintains the '
             'relationships that have to exist before the day'),
            ('coordinator', 'Emergency management coordinator',
             'runs a function or a facility during an activation and '
             'coordinates across agencies that do not report to them'),
            ('director', 'Emergency management director',
             'accountable to an elected official for the jurisdiction\'s '
             'preparedness and for what the activation does'),
            ('ics-section', 'ICS section-level role',
             'a positional role inside an incident command structure - '
             'operations, planning, logistics, finance and administration - '
             'held for the duration and then handed back'),
            ('ics-command', 'ICS command-level role',
             'incident commander or unified command member, including the '
             'information, safety and liaison roles that report to command'),
        ],
    },
    'social': {
        'name': 'Social Work and Crisis Response',
        'scope': 'behavioural health crisis response, co-response alongside '
                 'police and EMS, disaster behavioural health, case work and '
                 'the long tail of a disaster that arrives months later',
        'standards_bodies': ['nasw-code', 'state-social-work-board',
                             'social-work-accreditation',
                             'behavioral-health-agency', 'health-privacy-law',
                             'state-mandated-reporting-law'],
        'representation': {
            'kinds': ['professional association of social workers',
                      'public employee union representing county and state '
                      'behavioural health and child welfare staff',
                      'service employees union representing non-profit and '
                      'hospital behavioural health workers'],
            'real_acronyms': ['NASW', 'AFSCME', 'SEIU'],
            'what_they_do_here': 'the professional association owns the '
                                 'ethical code; the unions bargain the '
                                 'caseload, and caseload is a safety '
                                 'question in this service the way staffing '
                                 'is in the other four',
        },
        'tiers': [
            ('peer-specialist', 'Peer support specialist',
             'credentialed on the basis of lived experience rather than a '
             'degree, and a distinct role rather than a junior clinician'),
            ('case-worker', 'Bachelor-level case worker',
             'carries a caseload, navigates systems, works under supervision'),
            ('clinician', 'Master-level clinician, pre-licence',
             'clinical work under a licensed supervisor, accumulating the '
             'hours the state requires'),
            ('licensed-clinical', 'Licensed clinical social worker',
             'independently licensed, may supervise, carries the clinical '
             'accountability'),
            ('supervisor', 'Clinical or programme supervisor',
             'responsible for other people\'s clinical decisions and for '
             'the conditions they make them in'),
            ('programme-director', 'Programme director',
             'owns the service design, the staffing and the relationship '
             'with the other four services'),
        ],
    },
}


# ---------------------------------------------------------------------------
# THE COMPETENCY DOMAINS.
#
# A competency domain here is a thing a learner should be able to
# DEMONSTRATE and a debrief should be able to WATCH FOR. It is not a
# procedure and it deliberately stops short of one: "states what the
# supply constraint is before committing" is a competency; how much water
# comes out of a given line is a protocol, and it belongs to the authority
# named on the record.
#
# Fields:
#   id, service, tier_floor  - where in the service this first bites
#   what_it_is / why_it_matters
#   authority                - the body that owns the real standard
#   look_for                 - what a debrief would observe. Behaviours,
#                              not knowledge claims: "said it out loud" and
#                              "changed the plan when the report came back"
#                              are observable; "understands" is not.

def C(cid, service, tier_floor, title, what, why, authority, look_for):
    return {'id': cid, 'service': service, 'tier_floor': tier_floor,
            'title': title, 'what_it_is': what, 'why_it_matters': why,
            'authority': authority, 'look_for': list(look_for)}


COMPETENCIES = [
    # ---- fire service ----------------------------------------------------
    C('fire.size-up', 'fire', 'firefighter',
      'Scene size-up and its transmission',
      'Forming a picture of what is in front of you on arrival and saying '
      'it out loud so that everybody still driving towards it has the same '
      'picture.',
      'The first sixty seconds of description sets what every later crew '
      'expects to find, and a size-up nobody transmitted is a size-up only '
      'one person has.',
      'nfpa',
      ['gives a description that a person who cannot see the building could '
       'act on',
       'names what is NOT there as well as what is - no smoke showing is '
       'information',
       'updates the picture out loud when it changes rather than quietly '
       'revising it',
       'separates what is observed from what is assumed']),
    C('fire.command-establishment', 'fire', 'company-officer',
      'Establishing, holding and transferring command',
      'Declaring that command exists, holding it visibly, and passing it in '
      'a way that leaves no gap where nobody is in charge.',
      'Every multi-agency review of a bad incident finds the same gap: two '
      'people each thought the other had it, or a transfer happened on a '
      'radio channel one of them was not on.',
      'fema-nims',
      ['announces command in terms that can be heard and logged',
       'a transfer includes a face-to-face or explicit acknowledgement, not '
       'an assumption',
       'the person relinquishing command can say what they handed over',
       'nobody on the incident is unable to name who has command']),
    C('fire.crew-integrity', 'fire', 'firefighter',
      'Crew integrity and personnel accountability',
      'Staying a crew: knowing where your people are, being findable '
      'yourself, and being counted.',
      'A responder who is alone in a building nobody knows they are in is '
      'the precondition for most of the worst outcomes in this service.',
      'nfpa',
      ['can state where each member of their crew is without looking',
       'does not separate without saying so and being acknowledged',
       'responds to accountability checks promptly and accurately',
       'flags a crew that has gone quiet rather than waiting']),
    C('fire.air-awareness', 'fire', 'firefighter',
      'Treating breathing air as a managed resource',
      'Holding, as a habit, the awareness that a finite consumable is being '
      'spent and that the exit takes as long as the entry did.',
      'This is a culture competency, not an arithmetic one. The actual '
      'management points and thresholds belong to the standard and the '
      'agency procedure and are not stated here.',
      'nfpa',
      ['reports air status without being asked for it',
       'plans the way out at the same time as the way in',
       'treats a crew member\'s consumption as the crew\'s problem',
       'does not negotiate with an alarm']),
    C('fire.mayday-readiness', 'fire', 'firefighter',
      'Recognising trouble and declaring it early',
      'Being able to recognise that you are the emergency now, and saying so '
      'before the situation has decided for you.',
      'The reluctance to declare is the documented failure mode - responders '
      'delay because declaring feels like a personal failure. The scaffold '
      'here is the psychological one; the message format and the response to '
      'it belong to the standard and the agency.',
      'nfpa',
      ['can articulate what would make them declare, in advance',
       'does not treat a declaration by somebody else as an overreaction',
       'a crew that declares is debriefed on the decision, not on the noise',
       'the training culture has actually rehearsed somebody declaring']),
    C('fire.building-construction-literacy', 'fire', 'firefighter',
      'Reading what a building is made of',
      'Recognising construction type, era and alteration from the outside, '
      'and knowing that the answer changes what the building will do.',
      'This is the single competency that most directly connects this pack '
      'to the rest of the bundle: the 111 trade halls are the people who '
      'built, altered and maintained the thing the crew is standing in.',
      'nfpa',
      ['names the construction features they can actually see',
       'identifies where a building has been altered rather than built',
       'says what they do not know about the concealed spaces',
       'connects a construction observation to a consequence out loud']),
    C('fire.apparatus-positioning-judgement', 'fire', 'driver-operator',
      'Positioning as a decision that forecloses other decisions',
      'Understanding that where the apparatus stops decides what it and '
      'everything behind it can do for the rest of the incident.',
      'A position is easy to take and expensive to change. The judgement is '
      'about what the next three arriving units will now be unable to do; '
      'the distances and the setup belong to the manufacturer and the '
      'agency.',
      'ahj',
      ['states what the position is FOR before taking it',
       'leaves room for the units not yet on scene',
       'reports the position in terms others can build on',
       'can explain what the position gave up']),
    C('fire.water-supply-reasoning', 'fire', 'driver-operator',
      'Reasoning about supply as a constraint',
      'Thinking about where the water is coming from, how long it lasts and '
      'who else is drawing on it, as a constraint on the plan rather than a '
      'plumbing detail.',
      'Supply failures are rarely dramatic; they are a plan that quietly '
      'could not be sustained. No flow, pressure or volume figure appears in '
      'this pack.',
      'ahj',
      ['identifies the supply before it is needed, not when it fails',
       'tells command what the constraint is in time to change the plan',
       'notices when another unit\'s draw is the explanation',
       'reports a supply problem as a problem, not as an apology']),
    C('fire.fireground-communication', 'fire', 'firefighter',
      'Radio discipline and closed-loop communication',
      'Brief, ordered, acknowledged traffic: who you are, who you want, what '
      'you need, and hearing it come back.',
      'The fireground is loud, the channel is shared, and an unacknowledged '
      'message is not a message. This is the competency that makes every '
      'other one transmissible.',
      'fema-nims',
      ['messages are addressed and acknowledged, both ways',
       'priority traffic is recognisably different from routine traffic',
       'the speaker stops when the message is complete',
       'an unacknowledged transmission is repeated rather than assumed']),
    C('fire.risk-benefit-framing', 'fire', 'company-officer',
      'Risk and benefit as an explicit frame',
      'Being able to say what is being risked, for what, and on what '
      'information - before committing, and again when the information '
      'changes.',
      'The frame is the profession\'s own and is stated in its standards and '
      'its culture. What this pack scaffolds is the habit of saying it out '
      'loud; what counts as acceptable risk is the agency\'s and the '
      'standard\'s to set.',
      'ahj',
      ['states the benefit being sought, specifically',
       'states what information the decision rests on and how old it is',
       'revisits the decision when a report contradicts the assumption',
       'is able to withdraw without treating it as a defeat']),
    C('fire.company-officer-supervision', 'fire', 'company-officer',
      'Supervising a company under load',
      'Keeping a small team effective when the environment is hostile, the '
      'information is partial and the officer is also doing a task.',
      'The step from doing to supervising is the step most often taken with '
      'no training at all, and it is where crew integrity is either kept or '
      'lost.',
      'nfpa',
      ['delegates rather than absorbing every task',
       'knows the state of each member, not just the task',
       'gives an assignment the member can repeat back',
       'notices a member who has stopped speaking']),
    C('fire.post-incident-analysis', 'fire', 'company-officer',
      'Running a debrief that people tell the truth in',
      'Structuring a review so that what actually happened surfaces, '
      'including the parts that are embarrassing.',
      'A debrief that only produces agreement has produced nothing. This '
      'competency is the one that makes every other record in this pack '
      'correctable.',
      'exercise-programme-doctrine',
      ['separates what happened from who did it',
       'the most junior person present says something',
       'produces at least one thing that will actually change',
       'records a disagreement as a disagreement rather than resolving it '
       'for the room']),
    C('fire.contamination-discipline', 'fire', 'firefighter',
      'Exposure reduction as an ordinary habit',
      'Treating post-incident contamination as a routine hazard with routine '
      'handling, rather than as a special case.',
      'The long-run occupational disease burden in this service is the '
      'largest single threat to the people in it, and it is carried home on '
      'gear. The specific cleaning and monitoring requirements belong to the '
      'standard and the employer.',
      'osha-and-state-plans',
      ['the habit is visible when nobody is watching',
       'contaminated gear does not travel into clean space',
       'a new member is corrected without ceremony',
       'the officer models it rather than mandating it']),
    C('fire.wui-awareness', 'fire', 'firefighter',
      'Wildland-urban interface awareness',
      'Recognising that a structure incident in an interface is also a '
      'landscape incident, with different time constants and a different '
      'evacuation problem.',
      'The interface is where this service, law enforcement, emergency '
      'management and social services all end up on the same road at the '
      'same time, and each has a different clock.',
      'ahj',
      ['recognises the interface condition and says so',
       'thinks about egress for civilians and for the crew as one question',
       'hands off to the agency that owns the landscape fire rather than '
       'competing with it',
       'can state what the weather is doing to the problem']),

    # ---- law enforcement -------------------------------------------------
    C('law.authority-literacy', 'law', 'cadet',
      'Knowing where the authority comes from and where it stops',
      'Being able to articulate the source and the limit of the authority '
      'being exercised, in the moment and afterwards in writing.',
      'Authority that cannot be articulated is authority that will not '
      'survive review, and the person it was exercised on already knew that.',
      'courts',
      ['can state the basis for an action at the time, not only later',
       'the written account matches the stated basis',
       'stops when the basis stops',
       'asks a supervisor rather than proceeding on an unclear basis']),
    C('law.de-escalation-communication', 'law', 'probationary',
      'De-escalation as communication, and time as a resource',
      'Using distance, time, cover and language to reduce the pressure on a '
      'decision rather than to accelerate it.',
      'Most of what this competency is about is deciding not to close the '
      'distance yet. The tactics are the agency\'s and the POST '
      'commission\'s; the scaffold here is the disposition.',
      'state-post',
      ['creates time rather than consuming it',
       'the words used would read the same way in a transcript',
       'asks rather than commands where asking is available',
       'can say afterwards what they were trying to achieve with each step']),
    C('law.crisis-recognition-referral', 'law', 'probationary',
      'Recognising a behavioural health crisis and getting the right people',
      'Identifying that the call is a health call, and knowing the referral '
      'and co-response pathway rather than improvising a clinical judgement.',
      'This is the hinge between this service and the social work service, '
      'and the competency is explicitly NOT to assess or diagnose - it is to '
      'recognise and hand over.',
      'behavioral-health-agency',
      ['names what they observed rather than what they concluded',
       'requests the co-response or clinical resource early',
       'can describe the local pathway without looking it up',
       'hands over with information rather than with a label']),
    C('law.force-reporting-and-review', 'law', 'officer',
      'Reporting and reviewing force, as an accountability practice',
      'Documenting what was done and why in a way that a reviewer, a court '
      'and the public can follow. This pack carries nothing about technique.',
      'The review is where the profession either learns or does not. A '
      'report that is a template is a review that did not happen.',
      'state-post',
      ['the account is specific enough to be disagreed with',
       'the account is written before the officer has seen the video, where '
       'the agency requires that',
       'a supervisor\'s review adds something rather than initialling',
       'a pattern across reports is treated as a finding']),
    C('law.procedural-justice', 'law', 'officer',
      'Procedural justice in ordinary encounters',
      'Voice, neutrality, respect and explanation, in the encounters nobody '
      'will ever review, which is almost all of them.',
      'Legitimacy is built in the routine stop and spent in the crisis. The '
      'research base and the standard belong to others; the behaviours are '
      'observable here.',
      'law-enforcement-accreditation',
      ['explains what is happening and why, unprompted',
       'lets the person speak before the decision is announced',
       'treats the outcome and the explanation as separate obligations',
       'behaves the same way when not recorded']),
    C('law.field-supervision', 'law', 'first-line-supervisor',
      'First-line supervision as the first accountability layer',
      'Being present at the calls that matter, reviewing what the squad '
      'produced, and intervening early rather than documenting late.',
      'The first-line supervisor is the only person positioned to stop a '
      'developing problem, and is usually the least trained for it.',
      'law-enforcement-accreditation',
      ['goes to the call rather than waiting for the report',
       'gives a correction close to the event',
       'can name which of their people is currently struggling',
       'escalates rather than absorbing']),
    C('law.report-and-evidence-integrity', 'law', 'probationary',
      'Report writing and evidence integrity',
      'Writing an account that is accurate, complete and honest about '
      'uncertainty, and handling evidence so that its history is intact.',
      'Everything downstream - charging, defence, review, the person\'s life '
      '- runs on this document and this chain.',
      'courts',
      ['records what is not known as not known',
       'distinguishes observation from inference in the text',
       'the evidence record is contemporaneous',
       'a correction is made as a correction, not as an overwrite']),
    C('law.impartiality', 'law', 'cadet',
      'Impartial policing and bias awareness',
      'Noticing the decision points where a judgement was made on something '
      'other than behaviour, and building the habit of checking.',
      'Named here as a domain with an authority rather than as a slogan; the '
      'curriculum content belongs to the POST commission and the agency.',
      'state-post',
      ['can identify the decision point in their own account',
       'accepts an audit of their own stop data without treating it as an '
       'accusation',
       'interrupts a colleague\'s shortcut in the moment',
       'the explanation given is behaviour-based and survives being written '
       'down']),
    C('law.interagency-role-clarity', 'law', 'officer',
      'Knowing your role inside somebody else\'s incident',
      'At a fire, a hazmat release or a disaster, the officer is usually '
      'supporting a structure they do not command, and the competency is '
      'knowing that and working inside it.',
      'The documented multi-agency failure is not hostility; it is two '
      'agencies each running their own incident on the same ground.',
      'fema-nims',
      ['identifies the incident commander and reports in',
       'requests through the structure rather than around it',
       'holds a perimeter as an assignment with a stated purpose',
       'does not create a second command post']),
    C('law.wellness-peer-support', 'law', 'officer',
      'Wellness, peer support and the culture that permits it',
      'Knowing what support exists, being willing to use it, and being '
      'willing to be the person who suggests it to somebody else.',
      'The access, the confidentiality and the limits of any programme are '
      'the employer\'s and the agreement\'s; the competency is the '
      'willingness.',
      'employer-agency',
      ['can name the support that exists without looking it up',
       'has used it or can say honestly why not',
       'raises it with a colleague rather than about a colleague',
       'a supervisor\'s response to a disclosure is not a duty change by '
       'default']),
    C('law.community-legitimacy', 'law', 'command',
      'Building and spending legitimacy deliberately',
      'Treating the relationship with a community as an account that is paid '
      'into in ordinary times and drawn on in emergencies.',
      'In a disaster, whether an evacuation order is believed depends on '
      'work done years earlier by people who are not on the incident.',
      'law-enforcement-accreditation',
      ['can name the community relationships the agency actually has',
       'brings community organizations into planning rather than into '
       'briefings',
       'accepts a public account of a failure',
       'measures something other than activity']),
    C('law.handover-to-medical', 'law', 'officer',
      'Handover to the medical service',
      'Getting the scene to the point where clinicians can work, and giving '
      'them what they need in the order they need it.',
      'The officer is very often the first person with a patient and the '
      'last person with the information about how they got that way. The '
      'clinical content belongs entirely to EMS and the medical director.',
      'ems-medical-director',
      ['states scene safety status explicitly',
       'reports what was observed, with times, not a diagnosis',
       'does not delay the handover to finish the police task',
       'stays reachable for the question that comes ten minutes later']),

    # ---- EMS -------------------------------------------------------------
    C('ems.scene-assessment', 'ems', 'emt',
      'Scene safety and situational assessment',
      'Reading the environment before and while working in it, and treating '
      'it as a thing that changes.',
      'The clinician who is injured has converted one patient into two and '
      'removed the person who was going to treat the first.',
      'osha-and-state-plans',
      ['pauses at the threshold rather than at the patient',
       'states the hazard out loud to the partner',
       'reassesses when the scene composition changes',
       'withdraws and says why, rather than continuing and hoping']),
    C('ems.assessment-framework', 'ems', 'emt',
      'Working to an assessment framework rather than to a hunch',
      'Following a consistent structure so that the same information is '
      'gathered every time, including on the calls that look obvious.',
      'The framework is the authority\'s. This pack records that a framework '
      'exists, that consistency is the point, and that no finding, '
      'threshold or cut-off appears anywhere in this pack.',
      'nremt',
      ['the same structure is visible on a simple call and a complex one',
       'findings are stated as findings, in order',
       'a reassessment actually happens and is recorded',
       'the partner can follow the assessment without being told it']),
    C('ems.scope-literacy', 'ems', 'emr',
      'Knowing the edge of your own certification',
      'Being able to say what your level may do here, in this state, for '
      'this agency - and what it may not.',
      'The edge moves between states and between agencies. A clinician who '
      'is unsure of their own edge will either exceed it or stop short of '
      'it, and both are harms.',
      'national-ems-scope-model',
      ['can state the limit without hedging',
       'asks for the higher level early rather than late',
       'does not let a bystander\'s expectation move the limit',
       'reports having reached the limit as information, not as failure']),
    C('ems.medical-direction', 'ems', 'emt',
      'Working under medical direction',
      'Understanding that the protocol belongs to a named physician, that '
      'practice happens on their authority, and how to reach them.',
      'This is the fact that most distinguishes this service from the other '
      'four, and the reason this pack contains no clinical content at all.',
      'ems-medical-director',
      ['can name who their medical director is, as a role',
       'contacts medical control when the situation is outside the standing '
       'order, rather than improvising',
       'documents the contact and the instruction',
       'raises a protocol that did not fit through the review route rather '
       'than working around it next time']),
    C('ems.documentation-handover', 'ems', 'emt',
      'The verbal handover and the record behind it',
      'Transferring a patient with the information the receiving team needs, '
      'in an order they can use, and writing a record that still makes sense '
      'a year later.',
      'The handover is the highest-density information transfer in the whole '
      'chain and the most frequently identified failure point in reviews.',
      'nremt',
      ['gives a structured handover without reading the whole record aloud',
       'stops for the receiving team\'s question',
       'the written record supports the verbal one',
       'the times in the record are real times']),
    C('ems.consent-capacity-refusal', 'ems', 'emt',
      'Consent, capacity and refusal',
      'The legal and ethical frame around treating somebody who does not '
      'want to be treated, or who may not be able to decide.',
      'The highest-risk call in this service is frequently the one where '
      'nobody was transported. The determination itself belongs to the state '
      'and the medical director.',
      'ems-medical-director',
      ['treats a refusal as an assessment, not as an exit',
       'documents what was explained and what was understood',
       'involves medical control where the agency requires it',
       'leaves a route back - the person knows how to change their mind']),
    C('ems.mci-role-clarity', 'ems', 'emt',
      'Role clarity in a mass casualty incident',
      'Knowing which positional role you hold, doing that and not the other '
      'one, and accepting that the ordinary standard of care has been '
      'replaced by a system decision made above you.',
      'The triage system, its categories and every cut-off in it belong to '
      'the state EMS office and the medical director. This pack names the '
      'role discipline and stops.',
      'fema-nims',
      ['takes the assigned role and stays in it',
       'does not begin individual care while holding a system role',
       'reports counts upward in the form that was asked for',
       'hands the role over explicitly when relieved']),
    C('ems.crew-resource-management', 'ems', 'emt',
      'Crew resource management in a two-person team',
      'Two people, one of whom may be far more experienced, making decisions '
      'without the junior one going silent.',
      'The junior clinician who noticed something and said nothing is a '
      'recurring finding, and it is a team design problem rather than a '
      'character problem.',
      'nremt',
      ['the senior clinician invites the challenge explicitly',
       'the junior clinician raises a concern and it changes something',
       'roles are stated at the start of the call',
       'a disagreement is resolved audibly and then recorded']),
    C('ems.exposure-control', 'ems', 'emr',
      'Infection and exposure control as routine',
      'Standard precautions as an unremarkable habit, plus knowing what to '
      'do about an exposure afterwards.',
      'The reporting pathway, the prophylaxis and the timeframes belong to '
      'the employer and the health authority; the habit belongs here.',
      'osha-and-state-plans',
      ['the habit does not degrade under time pressure',
       'an exposure is reported the same day it happens',
       'a new member is corrected immediately',
       'the vehicle is treated as a clinical space']),
    C('ems.special-population-framing', 'ems', 'emt',
      'Recognising that populations differ, without pretending to the '
      'specifics',
      'Holding the awareness that paediatric, geriatric, pregnant, disabled '
      'and non-communicating patients are not small or large versions of a '
      'default patient.',
      'Named as a domain with an owner. Every specific difference - '
      'anatomical, physiological, pharmacological - belongs to the authority '
      'and none is stated here.',
      'nremt',
      ['reaches for the reference or the resource rather than the analogy',
       'adapts communication to the patient in front of them',
       'involves a carer or interpreter as a source rather than a nuisance',
       'says out loud when the call is outside their usual population']),
    C('ems.behavioural-emergency', 'ems', 'emt',
      'The behavioural emergency, and the other services in it',
      'Working a call whose presenting problem is behavioural, alongside '
      'police and crisis clinicians, without defaulting to the tool nearest '
      'to hand.',
      'This is the four-way junction of this pack: the patient, the '
      'clinician, the officer and the social worker are all in the same '
      'small room with different obligations.',
      'behavioral-health-agency',
      ['establishes who is leading the interaction, early',
       'reduces the number of people in the space',
       'treats the medical assessment as still owed',
       'the handover names what was tried, not only what happened']),
    C('ems.fatigue-and-critical-incident', 'ems', 'field-supervisor',
      'Fatigue, critical incident stress and the supervisor\'s part in it',
      'Recognising the accumulation, having a route for the call that lands '
      'badly, and knowing that shift design is a clinical safety question.',
      'Duty hours and support access are bargained and employer-set; the '
      'competency is the supervisor noticing and acting.',
      'employer-agency',
      ['a supervisor takes a crew out of service and says why',
       'the difficult call gets a check-in that is not a debrief',
       'a pattern in one person is noticed by somebody other than them',
       'the support offered is specific, not a poster']),

    # ---- emergency management and disaster relief ------------------------
    C('em.ics-role-discipline', 'em', 'volunteer',
      'Holding an ICS position and only that position',
      'Taking a positional role, working inside its span, and handing it '
      'back cleanly - including when your day job is more senior than the '
      'role.',
      'The structure only works if rank outside it does not leak into it. '
      'The position descriptions and the doctrine belong to the national '
      'system; the discipline is the competency.',
      'fema-nims',
      ['can state their position and who they report to',
       'requests through their supervisor rather than laterally',
       'does not exercise authority their position does not carry',
       'briefs their relief rather than simply leaving']),
    C('em.eoc-coordination', 'em', 'specialist',
      'Operating a coordination facility',
      'Running the place where agencies that do not report to each other '
      'have to produce one picture and one set of priorities.',
      'An emergency operations centre coordinates; it does not command the '
      'incident. Confusing the two produces the second command post that '
      'every after-action report warns about.',
      'em-accreditation',
      ['the common picture is maintained and is actually common',
       'a request is tracked from arrival to resolution',
       'the facility supports the incident rather than directing it',
       'shift change does not lose the thread']),
    C('em.mutual-aid-requesting', 'em', 'coordinator',
      'Requesting and receiving help from other jurisdictions',
      'Knowing the mechanisms by which resources cross a jurisdictional '
      'line, and what obligations come attached.',
      'Asking late is the most common and most expensive error, and the '
      'second most common is asking for a capability in words the other '
      'jurisdiction does not use.',
      'fema-nims',
      ['asks before the need is acute',
       'requests a capability in typed terms rather than by local name',
       'plans for the receiving of it - feeding, housing, tasking',
       'demobilises deliberately rather than by attrition']),
    C('em.planning-cycle', 'em', 'specialist',
      'The operational period planning cycle',
      'The rhythm by which objectives are set, a plan is produced for a '
      'fixed period, and the next period starts from what actually '
      'happened.',
      'The cycle is the mechanism that stops an incident being managed by '
      'whoever spoke last. Its structure and forms belong to the national '
      'system.',
      'fema-nims',
      ['objectives are written so that somebody could tell if they were met',
       'the plan covers a stated period and then is replaced',
       'the planning meeting produces decisions rather than updates',
       'the next period reflects the last one\'s results']),
    C('em.public-information-warning', 'em', 'coordinator',
      'Public information and warning',
      'Saying something true, actionable and timely to a public that may '
      'not trust you, in the languages they actually speak.',
      'A warning that is not believed is not a warning, and belief was '
      'decided before the event. Message content and alerting systems are '
      'governed elsewhere.',
      'fema-nims',
      ['one voice, and it is identifiable',
       'the message says what to DO, not only what is happening',
       'the message exists in the languages of the affected population',
       'a correction is issued as visibly as the original']),
    C('em.mass-care-coordination', 'em', 'coordinator',
      'Mass care and sheltering coordination',
      'Coordinating the feeding, sheltering and reunification effort, most '
      'of which is delivered by organizations that do not work for you.',
      'This is where government and the voluntary sector meet, and where the '
      'relationship either exists already or does not exist at all.',
      'voad',
      ['the voluntary organizations are in the planning, not only the '
       'response',
       'shelter capability is described in terms of who it can actually '
       'take',
       'reunification is treated as a named function with an owner',
       'the count reported is a count somebody could reproduce']),
    C('em.damage-assessment', 'em', 'specialist',
      'Coordinating damage assessment',
      'Getting a defensible picture of what is damaged, quickly enough to '
      'drive decisions and rigorously enough to survive audit.',
      'The assessment drives both immediate life safety and every later '
      'assistance programme, which are different questions asked of the same '
      'walk down the same street.',
      'em-accreditation',
      ['the method is stated before the data is collected',
       'assessors record what they saw, not what they concluded about '
       'eligibility',
       'safety of the assessors is somebody\'s explicit job',
       'the trade expertise needed for a structural judgement is requested '
       'rather than improvised']),
    C('em.continuity', 'em', 'director',
      'Continuity of operations for the responding jurisdiction',
      'Keeping the jurisdiction\'s own essential functions running while it '
      'responds, including when its own buildings and staff are affected.',
      'The agency responding to the disaster is also in the disaster. This '
      'is routinely the plan that exists on paper and has never been walked.',
      'em-accreditation',
      ['essential functions are named and prioritised in advance',
       'succession is written down and the successors know',
       'the plan has been exercised from a degraded starting state',
       'staff whose own homes are affected are planned for']),
    C('em.volunteer-donations', 'em', 'coordinator',
      'Volunteer and donations management',
      'Handling the spontaneous arrival of people and goods, which is a '
      'certainty and is usually treated as a surprise.',
      'Unmanaged generosity consumes the response. Saying so out loud is not '
      'cynicism; it is the difference between help and a second logistics '
      'problem.',
      'voad',
      ['a donations plan exists before it is needed',
       'spontaneous volunteers are registered rather than turned away or '
       'turned loose',
       'unsolicited goods have a stated destination',
       'the ask to the public is specific']),
    C('em.access-functional-needs', 'em', 'specialist',
      'Access and functional needs inclusion',
      'Planning so that disabled people, people without transport, people '
      'with limited English and people in institutions are in the plan '
      'rather than an exception to it.',
      'Every evacuation and sheltering failure that becomes a lawsuit '
      'becomes one here. The legal requirements belong to statute and are '
      'not stated in this pack.',
      'em-accreditation',
      ['the plan names the populations rather than saying "vulnerable"',
       'disability-led organizations were in the planning',
       'transport-dependent populations have a stated mechanism',
       'the shelter can actually receive the people the plan sends it']),
    C('em.recovery-transition', 'em', 'director',
      'Recovery and the transition out of response',
      'Handing the problem from the responding structure to the long, '
      'unglamorous recovery structure without dropping it.',
      'Recovery lasts years, is where most of the money goes, and has almost '
      'none of the training attention. The transition is where communities '
      'get lost.',
      'em-accreditation',
      ['the transition has a date, a structure and a named owner',
       'the recovery structure includes people who were not in the response',
       'unmet-needs work is a standing function rather than an appeal',
       'the case-management handover to social services is explicit']),
    C('em.exercise-and-after-action', 'em', 'specialist',
      'Exercise design and turning findings into change',
      'Designing an exercise that can fail, evaluating it honestly and '
      'producing improvements somebody is accountable for.',
      'An exercise designed to be passed has taught nothing and has consumed '
      'the day everybody had. The doctrine is federal; the honesty is local.',
      'exercise-programme-doctrine',
      ['objectives are set before the scenario is written',
       'the exercise is allowed to produce a failure',
       'findings have an owner and a date',
       'the next exercise starts from the last one\'s findings']),

    # ---- social work and crisis response ---------------------------------
    C('social.ethics-and-boundaries', 'social', 'case-worker',
      'Professional ethics and boundaries under disaster conditions',
      'Holding the professional frame when the usual conditions - an office, '
      'a scheduled hour, a known caseload - have all gone.',
      'The code does not suspend in a disaster, and the situations that test '
      'it hardest are the ones where suspending it would feel kind.',
      'nasw-code',
      ['can name the boundary being pressured, in the moment',
       'consults rather than deciding alone',
       'dual relationships are surfaced rather than managed privately',
       'documents the ethical reasoning, not only the action']),
    C('social.trauma-informed-practice', 'social', 'peer-specialist',
      'Trauma-informed practice as a default posture',
      'Assuming that the person in front of you may have a history that '
      'makes the ordinary interaction costly, and designing the interaction '
      'accordingly.',
      'Applies to colleagues as well as clients, which is the part most '
      'often left out of the training.',
      'behavioral-health-agency',
      ['offers choice where choice is available',
       'explains before doing',
       'does not require the story to be retold to each new person',
       'notices when the setting itself is the problem']),
    C('social.crisis-engagement', 'social', 'peer-specialist',
      'Engagement and de-escalation in a crisis contact',
      'Establishing enough connection, fast, that a person in acute distress '
      'will stay in the conversation.',
      'This is the competency that co-response exists to bring to a call. '
      'Clinical intervention beyond engagement belongs to the clinician\'s '
      'licence and to the state board.',
      'behavioral-health-agency',
      ['slows the interaction rather than resolving it',
       'the person\'s own words are used back to them',
       'the number of people and the amount of noise is actively reduced',
       'can say afterwards what the person actually asked for']),
    C('social.risk-screening-referral', 'social', 'case-worker',
      'Screening and referral pathways',
      'Recognising the indicators that a referral is needed and knowing '
      'where the referral goes, in this jurisdiction, today.',
      'No screening tool, score, threshold or cut-off appears in this pack. '
      'Those belong to the instrument\'s owner, the state authority and the '
      'clinical supervisor.',
      'behavioral-health-agency',
      ['uses the instrument the agency actually adopted, as intended',
       'the referral is warm rather than a phone number',
       'the loop is closed - somebody knows whether it landed',
       'a refused referral is documented and revisited']),
    C('social.mandated-reporting', 'social', 'case-worker',
      'Mandated reporting literacy',
      'Knowing that you are a mandated reporter, what that duty attaches to '
      'in your state and role, and what it does to the relationship.',
      'The duty is statutory, varies by state and role, and is one of the '
      'few things in this pack where a wrong summary could directly harm a '
      'child or an adult. No content is restated here.',
      'state-mandated-reporting-law',
      ['can state that they are a reporter and under what law, in general '
       'terms',
       'consults the agency route rather than deciding alone under pressure',
       'tells the client what the limits of confidentiality are at the start',
       'documents the decision either way']),
    C('social.co-response-role-clarity', 'social', 'clinician',
      'Role clarity in co-response',
      'Working on a call alongside an armed officer or a medical crew with a '
      'clear, agreed division of who is leading what.',
      'Co-response fails in one of two directions: the clinician is a '
      'passenger, or the clinician is treated as having authority they do '
      'not have. Both are design failures.',
      'behavioral-health-agency',
      ['the division of roles is agreed before the door, not at it',
       'the clinician can call for the interaction to slow down and it does',
       'the officer\'s safety role and the clinician\'s engagement role are '
       'both stated',
       'the debrief includes both agencies in the same room']),
    C('social.cultural-humility-language-access', 'social', 'case-worker',
      'Cultural humility and language access',
      'Working with people whose frame is not yours, and getting real '
      'interpretation rather than using a family member.',
      'In a disaster this becomes an operational question about who receives '
      'services at all, not a courtesy.',
      'nasw-code',
      ['a qualified interpreter is obtained rather than improvised',
       'children are not used as interpreters',
       'the worker asks rather than assuming the frame',
       'materials exist in the languages of the population served']),
    C('social.documentation-confidentiality', 'social', 'case-worker',
      'Documentation and confidentiality',
      'Recording what is needed, sharing what is permitted, and knowing that '
      'the rules differ for behavioural health and substance use records.',
      'In multi-agency disaster work the pressure to share everything is '
      'constant and the consequences of over-sharing land on the client.',
      'health-privacy-law',
      ['knows which record is under which rule',
       'shares the minimum that answers the question asked',
       'a request from another agency is answered against the rule rather '
       'than the relationship',
       'the client is told what was shared where that is required']),
    C('social.psychological-first-aid', 'social', 'peer-specialist',
      'Psychological first aid in a disaster setting',
      'The immediate, non-clinical support offered to large numbers of '
      'people in the hours and days after an event.',
      'It is explicitly not therapy and explicitly not debriefing, and the '
      'distinction is the competency. The model belongs to its publishers '
      'and is not reproduced here.',
      'behavioral-health-agency',
      ['meets practical needs first and says so',
       'does not require or invite disclosure',
       'identifies who needs more than this and refers',
       'works at the scale the situation actually has']),
    C('social.vicarious-trauma-supervision', 'social', 'supervisor',
      'Vicarious trauma and the supervision that catches it',
      'Recognising the cumulative cost of the work in yourself and in the '
      'people you supervise, and building supervision that can hold it.',
      'Attrition in this workforce is a service continuity problem as much '
      'as a human one, and it is predictable.',
      'nasw-code',
      ['supervision covers the worker as well as the case',
       'caseload is treated as a safety variable and is actually adjusted',
       'the supervisor models using support',
       'a leaving worker is exit-interviewed honestly']),
    C('social.resource-navigation', 'social', 'case-worker',
      'Community resource navigation',
      'Knowing what actually exists in this jurisdiction, whether it is open, '
      'and what it really takes to get in.',
      'The gap between the resource list and the resource is where most of '
      'the harm in this service happens, and it is invisible from a desk.',
      'voad',
      ['the list is current because somebody checks it',
       'eligibility barriers are named to the client in advance',
       'the worker has contacted the resource rather than only listed it',
       'gaps are reported upward as findings']),
    C('social.disaster-behavioral-health-integration', 'social',
      'programme-director',
      'Integrating behavioural health into the emergency structure',
      'Getting behavioural health a seat in the planning and in the incident '
      'structure rather than an appearance at the shelter after the press '
      'leaves.',
      'It is nearly always the last function integrated and the one with the '
      'longest tail; the structure it has to integrate into is the national '
      'incident management system\'s.',
      'fema-nims',
      ['behavioural health is a named function in the plan, with a position',
       'the function is activated at the same time as the others',
       'the staffing plan covers weeks, not the first forty-eight hours',
       'responder support and public support are planned as separate '
       'workloads']),
]


# ---------------------------------------------------------------------------
# THE DEBRIEF STRUCTURE.
#
# One structure, used by every scenario frame below, so that a learner
# moving between services meets the same shape. It is this pack's own
# scaffold. It is NOT the federal after-action doctrine and it is not a
# critical incident stress intervention - both of those are owned
# elsewhere and both are named as such on the record.

DEBRIEF = [
    ('facts', 'What actually happened, in order',
     'Establish an agreed sequence before anybody explains anything. '
     'Disagreements about the sequence are recorded as disagreements.'),
    ('picture', 'What did each person think was going on at the time',
     'The gap between two people\'s pictures at the same moment is the '
     'finding. This is the question that most often produces one.'),
    ('decisions', 'Which decisions were made, by whom, on what information',
     'Attach each decision to the information available then, not to the '
     'information available now.'),
    ('pressure', 'What pressure was acting on the decision',
     'Time, hierarchy, an audience, a family member, a radio that would not '
     'clear. Pressure is a cause, not an excuse, and it is usually '
     'designable.'),
    ('competencies', 'Which of the named competencies were exercised, and '
     'what was observed',
     'Tie the discussion back to the observable behaviours on the '
     'competency records so that the debrief produces something comparable '
     'across sessions.'),
    ('authority', 'Which real standard or protocol governs the part we are '
     'now arguing about',
     'The moment a debrief starts arguing about the correct procedure, it '
     'has left this pack\'s scope. Name the body, go and read the actual '
     'standard, and bring it back.'),
    ('change', 'What will be different, who owns it, by when',
     'A debrief with no owner and no date has produced agreement rather '
     'than change.'),
    ('people', 'Who needs something after this, and what is the route',
     'Held separately and last, and it is not a clinical intervention. The '
     'route belongs to the employer and to the behavioural health '
     'authority.'),
]


# ---------------------------------------------------------------------------
# THE SCENARIO FRAMES.
#
# A frame is a SITUATION and a PRESSURE, not a solution. There is no
# correct answer recorded for any of them, and that is deliberate: the
# correct answer is the one the governing authority and the local agency
# give, and this pack does not hold either.
#
# `halls` are cross-links into the bundle's 111 trade halls - the people
# whose work made the built thing the responder is now standing in. Every
# slug is resolved against pack/registry/halls.json at build time and an
# unresolvable one stops the build. Some frames touch no trade hall at all
# and carry an empty list; that is a real answer and is counted.

def S(sid, title, setting, situation, pressure, services, comps, halls,
      questions, authority, not_this):
    return {'id': sid, 'title': title, 'setting': setting,
            'situation': situation, 'decision_pressure': pressure,
            'services': list(services), 'competencies': list(comps),
            'halls': list(halls), 'debrief_questions': list(questions),
            'authority': authority, 'this_frame_is_not': not_this}


SCENARIOS = [
    S('resp.s.night-residential-fire',
      'A house fire at three in the morning',
      'a two-storey timber-framed dwelling in a residential street',
      'Companies arrive to a working fire in an occupied dwelling. The '
      'first-arriving officer has a partial account from a neighbour about '
      'who lives there and no confirmation about who is out.',
      'Incomplete information about occupancy, a short window in which the '
      'first decisions foreclose the later ones, and a crowd whose '
      'expectations are not the officer\'s risk frame.',
      ['fire', 'ems'],
      ['fire.size-up', 'fire.command-establishment', 'fire.crew-integrity',
       'fire.risk-benefit-framing', 'fire.fireground-communication',
       'ems.scene-assessment'],
      ['carpenters', 'drywall', 'roofers', 'insulators', 'electricians'],
      ['At what moment did the first officer\'s picture of occupancy '
       'change, and who else knew?',
       'What information was the commit decision made on, and how old was '
       'it?',
       'Who could name the incident commander at any given minute, and who '
       'could not?',
       'What did the crowd change about the decision, and was that '
       'acknowledged out loud?',
       'What would have had to be true for the decision to go the other '
       'way?'],
      'ahj',
      'a tactical worksheet. No assignment, order of operations or entry '
      'decision is recorded here or implied by the questions.'),

    S('resp.s.sprinkler-impairment',
      'A commercial building whose suppression system is out of service',
      'a mid-rise commercial occupancy under partial renovation',
      'A fire is reported in a building where the sprinkler system has been '
      'impaired for contractor work and the alarm panel has been in trouble '
      'for two days. The impairment paperwork exists somewhere.',
      'A protection assumption that the building normally carries has been '
      'removed, quietly, by a process that is nobody on the incident\'s '
      'fault.',
      ['fire', 'em'],
      ['fire.size-up', 'fire.building-construction-literacy',
       'fire.water-supply-reasoning', 'fire.risk-benefit-framing',
       'fire.post-incident-analysis'],
      ['fire-sprinkler', 'fire-alarm', 'bas-controls', 'firestop',
       'pipefitters'],
      ['When did anybody on the incident learn that the system was '
       'impaired?',
       'What in the pre-incident information would have carried that, and '
       'did it?',
       'Which assumptions in the initial plan depended on a working system?',
       'Who owns the impairment process in this jurisdiction, and is that a '
       'finding for them rather than for the crews?',
       'What would make this discoverable on arrival next time?'],
      'nfpa',
      'a guide to suppression system operation or impairment procedure. '
      'Both belong to the code and to the building owner.'),

    S('resp.s.structural-collapse',
      'A partial structural collapse with people unaccounted for',
      'a building under renovation in a dense block',
      'Part of a floor system has come down during occupied hours. The '
      'number of people inside is disputed between the contractor, the '
      'building manager and a bystander. Adjacent structures are of '
      'unknown stability.',
      'A rescue problem that is simultaneously an engineering problem, where '
      'the expertise that could answer the engineering question is not on '
      'the first alarm and the people who might be alive are on a clock.',
      ['fire', 'ems', 'em', 'law', 'social'],
      ['fire.size-up', 'fire.command-establishment',
       'fire.building-construction-literacy', 'fire.risk-benefit-framing',
       'em.ics-role-discipline', 'em.mutual-aid-requesting',
       'em.damage-assessment', 'ems.mci-role-clarity',
       'law.interagency-role-clarity', 'social.psychological-first-aid'],
      ['ironworkers', 'steel-erectors', 'shoring', 'cement-masons',
       'post-tension', 'precast', 'riggers', 'crane-ops', 'demolition',
       'bridge-inspect', 'laborers'],
      ['How long after arrival did anybody with structural expertise get a '
       'say, and how was it requested?',
       'How was the disputed occupancy count handled - which number drove '
       'the plan, and was the uncertainty stated?',
       'What was the mechanism for stopping work if the structure moved, '
       'and who was authorised to use it?',
       'Which trades\' knowledge would have changed the picture, and does '
       'the jurisdiction have a way to reach them at 2am?',
       'Who was talking to the families, from what point, and with what '
       'information?'],
      'fema-nims',
      'a collapse rescue or shoring manual. Structural collapse technical '
      'rescue is a specialist discipline with its own standards and this '
      'pack states none of them.'),

    S('resp.s.utility-strike',
      'An excavator strikes a buried utility',
      'a street excavation beside an occupied building',
      'A crew digging in the street has struck something. The dispatch '
      'information is contradictory about what was struck. People are '
      'standing near the excavation.',
      'The correct response differs completely depending on what was struck, '
      'and the people who know are the crew standing closest to it.',
      ['fire', 'ems', 'law'],
      ['fire.size-up', 'fire.fireground-communication',
       'fire.risk-benefit-framing', 'ems.scene-assessment',
       'law.interagency-role-clarity', 'law.authority-literacy'],
      ['line-workers', 'gas-distrib', 'water-distrib', 'substation',
       'cable-splicers', 'operating-eng', 'laborers', 'surveyors'],
      ['What was the first reliable statement about what had been struck, '
       'and where did it come from?',
       'Who from the utility was on scene or on the phone, and how long did '
       'that take?',
       'How was the perimeter decided, and what was it protecting against?',
       'Was the digging crew treated as a hazard, a resource or both?',
       'What does the locate-and-mark record say, and whose finding is that?'],
      'ahj',
      'a utility emergency procedure. What to do about a struck gas, '
      'electrical or water asset belongs to the utility and the '
      'jurisdiction.'),

    S('resp.s.industrial-hazmat',
      'A release at a process facility',
      'a fenced industrial site with process piping and storage',
      'A release has occurred inside a facility fence line. Site personnel '
      'have begun their own response. The wind is carrying towards a '
      'residential area.',
      'Two command systems - the facility\'s and the jurisdiction\'s - meet '
      'at a fence, while a protective action decision for the public needs '
      'making on incomplete product information.',
      ['fire', 'em', 'ems', 'law'],
      ['fire.size-up', 'fire.command-establishment',
       'fire.risk-benefit-framing', 'em.ics-role-discipline',
       'em.public-information-warning', 'em.mutual-aid-requesting',
       'ems.scene-assessment', 'law.interagency-role-clarity'],
      ['hazmat', 'pipefitters', 'pipeline', 'tank-erectors',
       'spill-response', 'industrial-clean', 'instrumentation',
       'confined-space'],
      ['How was unified command actually established with the facility, and '
       'when?',
       'What product information was available, how was it obtained, and '
       'how confident was it?',
       'What drove the protective action decision, and who made it?',
       'How were the facility\'s own responders accounted for?',
       'Which of the trade disciplines on site had information nobody '
       'asked for?'],
      'osha-and-state-plans',
      'a hazardous materials response guide. Product identification, '
      'protective distances, decontamination and entry all belong to the '
      'regulation, the emergency response guidance and the agency '
      'procedure.'),

    S('resp.s.confined-space',
      'A worker down in a below-grade space',
      'a municipal wastewater structure',
      'A maintenance worker is unresponsive in a below-grade space. A second '
      'worker has already gone in after them and is now also unresponsive. A '
      'third is at the opening.',
      'The single most reliably fatal pattern in this domain is the '
      'would-be rescuer, and the pressure to become one is at its maximum in '
      'the first ninety seconds.',
      ['fire', 'ems'],
      ['fire.size-up', 'fire.crew-integrity', 'fire.risk-benefit-framing',
       'fire.command-establishment', 'ems.scene-assessment',
       'ems.scope-literacy'],
      ['confined-space', 'wastewater', 'water-distrib', 'divers',
       'site-safety', 'industrial-clean'],
      ['What stopped, or did not stop, the third worker?',
       'At what point was it stated out loud that this was now a recovery '
       'risk rather than a rescue, and who was empowered to say that?',
       'What did the site\'s own permit and rescue arrangements say, and '
       'did anybody read them?',
       'Who held the "nobody enters" authority, and was that person '
       'physically at the opening?',
       'How does this jurisdiction train the reflex, rather than the '
       'knowledge?'],
      'osha-and-state-plans',
      'a permit-required confined space entry or rescue procedure. Entry, '
      'atmospheric monitoring and retrieval are regulated activities and '
      'nothing about them is stated here.'),

    S('resp.s.high-angle-facade',
      'Workers stranded on a facade access system',
      'a high-rise with a suspended platform',
      'A suspended access platform has failed on one side, leaving two '
      'workers at height in harnesses. The building\'s roof rigging is '
      'reachable. Weather is deteriorating.',
      'A slow problem that feels fast, where the technically correct answer '
      'takes longer than everybody watching believes it should.',
      ['fire', 'ems'],
      ['fire.size-up', 'fire.crew-integrity', 'fire.risk-benefit-framing',
       'fire.command-establishment', 'ems.scene-assessment',
       'ems.crew-resource-management'],
      ['high-angle', 'scaffold', 'riggers', 'curtainwall', 'window-glazing',
       'cladding', 'waterproofers'],
      ['How was the tempo of the incident managed against the tempo the '
       'audience expected?',
       'Who on scene actually understood the access system, and how were '
       'they found?',
       'What was the plan if the weather closed before the primary method '
       'worked?',
       'How was information given to the two workers, and by whom?',
       'What did the building\'s own rescue plan say it would do?'],
      'osha-and-state-plans',
      'a rope rescue or fall protection procedure. Technical rescue at '
      'height has its own standards and this pack reproduces none of them.'),

    S('resp.s.elevator-entrapment',
      'An entrapment in a tall building during a power event',
      'a high-rise office building on generator power',
      'Multiple cars are stopped with occupants inside during a utility '
      'outage. One occupant is reporting a medical complaint. Building '
      'engineering staff are present but the lift contractor is an hour '
      'away.',
      'A low-acuity problem that becomes a high-acuity one in one car, with '
      'a finite crew and several simultaneous demands.',
      ['fire', 'ems'],
      ['fire.command-establishment', 'fire.fireground-communication',
       'fire.risk-benefit-framing', 'ems.scene-assessment',
       'ems.assessment-framework', 'ems.scope-literacy'],
      ['elevator', 'bas-controls', 'electricians', 'battery-storage'],
      ['How was the triage between cars decided, and by whom?',
       'What did building engineering know that the crew did not, and how '
       'was that surfaced?',
       'How was information given to occupants who could not be reached '
       'quickly?',
       'What is the jurisdiction\'s arrangement with lift contractors, and '
       'is that a finding?',
       'Was the medical complaint reassessed while the mechanical problem '
       'was being worked?'],
      'ahj',
      'a lift release procedure. Moving a lift car is the contractor\'s and '
      'the code\'s business.'),

    S('resp.s.rail-incident',
      'A transit incident in a tunnel section',
      'an underground station and the tunnel beyond it',
      'A train has stopped between stations with passengers aboard and '
      'smoke reported. Traction power status is unclear to the responders '
      'and clear to the transit control centre, which is not on the '
      'responders\' radio system.',
      'Two organizations with complete and non-overlapping halves of the '
      'information, a communications environment that degrades underground, '
      'and self-evacuating passengers.',
      ['fire', 'ems', 'em', 'law', 'social'],
      ['fire.size-up', 'fire.command-establishment',
       'fire.fireground-communication', 'fire.crew-integrity',
       'em.ics-role-discipline', 'em.public-information-warning',
       'ems.mci-role-clarity', 'law.interagency-role-clarity',
       'social.psychological-first-aid'],
      ['rail-track', 'rail-signals', 'catenary', 'transit-vehicle',
       'substation', 'transmission', 'fire-alarm'],
      ['How and when was traction power status confirmed, and by whom, to '
       'whom?',
       'What did the responders do in the interval before that '
       'confirmation?',
       'How was self-evacuation handled - as a problem or as a fact?',
       'Where did the transit organization sit in the command structure, '
       'and had that ever been exercised?',
       'What happened to communications underground, and what was the '
       'fallback?'],
      'fema-nims',
      'a rail emergency procedure. Track access, power isolation and train '
      'evacuation belong to the transit authority and its regulator.'),

    S('resp.s.airport-ground',
      'A ground emergency at an airfield',
      'the movement area of a commercial airfield',
      'An aircraft ground incident has occurred with the airfield still '
      'active. Mutual aid units are arriving at a perimeter gate and do not '
      'have movement area authorisation.',
      'A controlled-access environment where the ordinary reflex - drive to '
      'the incident - is itself the hazard.',
      ['fire', 'ems', 'em'],
      ['fire.command-establishment', 'fire.apparatus-positioning-judgement',
       'fire.fireground-communication', 'em.ics-role-discipline',
       'em.mutual-aid-requesting', 'ems.mci-role-clarity'],
      ['aviation-ground', 'airfield', 'fleet-diesel', 'operating-eng'],
      ['How were arriving mutual aid units staged, and who told them?',
       'Who held movement area authority and how did that interact with '
       'incident command?',
       'What did the airfield emergency plan say, and when was it last '
       'walked with the mutual aid agencies?',
       'How was the casualty count communicated, and to whom first?',
       'What would have happened if the first unit had simply driven on?'],
      'ahj',
      'an aircraft rescue and firefighting procedure. That discipline has '
      'its own standards, its own agents and its own training, none of '
      'which is here.'),

    S('resp.s.port-terminal',
      'An incident at a working marine terminal',
      'a container and bulk terminal on a working waterfront',
      'An incident has occurred at a terminal with active cargo operations, '
      'a vessel alongside and a cargo manifest that is partly electronic and '
      'partly not.',
      'Jurisdiction is genuinely unclear, cargo information is commercially '
      'held, and the terminal cannot simply be stopped without consequences '
      'that nobody on the first alarm is authorised to accept.',
      ['fire', 'em', 'law'],
      ['fire.size-up', 'fire.command-establishment',
       'fire.risk-benefit-framing', 'em.ics-role-discipline',
       'em.mutual-aid-requesting', 'law.authority-literacy',
       'law.interagency-role-clarity'],
      ['port-crane', 'marine-terminal', 'marine-pipe', 'divers',
       'shipfitters', 'teamsters', 'fleet-diesel'],
      ['Who was in unified command, and how long did agreeing that take?',
       'How was cargo information obtained and how confident was it?',
       'What was the cost of stopping operations, and who was authorised to '
       'accept it?',
       'How were terminal workers accounted for as distinct from ship\'s '
       'crew?',
       'Which federal and state agencies had a role, and were they '
       'notified?'],
      'fema-nims',
      'a marine firefighting or port security procedure. Both are '
      'specialist, both are federally governed, and neither is described '
      'here.'),

    S('resp.s.riverine-flood',
      'A river forecast to crest above a levee',
      'a low-lying district behind flood defences',
      'The forecast has moved. A decision about evacuating a district has to '
      'be made hours before the water arrives, on a forecast with a stated '
      'uncertainty, in a community with previous experience of an '
      'evacuation that turned out to be unnecessary.',
      'The decision has to be made while the evidence is still ambiguous, '
      'and the cost of being wrong is asymmetric in both directions.',
      ['em', 'fire', 'law', 'social', 'ems'],
      ['em.public-information-warning', 'em.mass-care-coordination',
       'em.access-functional-needs', 'em.ics-role-discipline',
       'em.eoc-coordination', 'law.community-legitimacy',
       'social.cultural-humility-language-access',
       'social.resource-navigation', 'ems.scene-assessment'],
      ['water-distrib', 'wastewater', 'pipeline', 'grounds',
       'marine-terminal', 'shoring', 'site-safety'],
      ['Who made the evacuation decision and on what forecast product?',
       'How was the uncertainty communicated to the public - was it '
       'communicated at all?',
       'What was done for households without transport, and how were they '
       'identified before the day?',
       'What did the previous unnecessary evacuation cost in credibility, '
       'and was that named in the decision?',
       'Which institutions - care facilities, schools, custody - had a '
       'plan, and who checked?'],
      'fema-nims',
      'a flood fight or swiftwater rescue procedure. Levee operations and '
      'water rescue are separate disciplines with their own authorities.'),

    S('resp.s.wui-evacuation',
      'A fire moving towards an interface community',
      'a residential area at the edge of open land',
      'A landscape fire is moving under wind towards a community on a single '
      'access road. Some residents are preparing to leave, some are '
      'preparing to stay, and the road is about to be needed in both '
      'directions.',
      'Evacuation and suppression want the same road, the window is set by '
      'weather rather than by anybody\'s plan, and the decision authority is '
      'split across agencies.',
      ['fire', 'law', 'em', 'social'],
      ['fire.wui-awareness', 'fire.size-up', 'fire.risk-benefit-framing',
       'fire.command-establishment', 'law.community-legitimacy',
       'law.interagency-role-clarity', 'em.public-information-warning',
       'em.access-functional-needs', 'social.psychological-first-aid'],
      ['roofers', 'cladding', 'insulators', 'grounds', 'line-workers',
       'waterproofers'],
      ['When was the evacuation trigger set, and by whom - before the day or '
       'during it?',
       'How was the single access road deconflicted between incoming '
       'apparatus and outgoing residents?',
       'What was said to residents who intended to stay, and by whom?',
       'How did the agencies with different legal authorities agree on one '
       'message?',
       'Who was checking on the households that had been identified in '
       'advance, and had they been?'],
      'ahj',
      'a wildland fire tactics or evacuation procedure. Landscape fire '
      'behaviour and evacuation authority both belong elsewhere.'),

    S('resp.s.behavioural-co-response',
      'A behavioural health call at a private address',
      'a small flat with one person in acute distress',
      'A call has come in from a family member. An officer and a crisis '
      'clinician arrive together. The person in distress is alone in a room '
      'and is not answering. The family member is asking the responders to '
      'do something now.',
      'Three obligations in one doorway - safety, care and the person\'s own '
      'autonomy - with a family member applying pressure towards the '
      'fastest option.',
      ['law', 'social', 'ems'],
      ['law.crisis-recognition-referral', 'law.de-escalation-communication',
       'law.authority-literacy', 'social.co-response-role-clarity',
       'social.crisis-engagement', 'social.trauma-informed-practice',
       'social.risk-screening-referral', 'ems.behavioural-emergency',
       'ems.consent-capacity-refusal'],
      [],
      ['Who led the interaction, and was that agreed before the door or at '
       'it?',
       'What was the slowest acceptable tempo, and did anybody protect it?',
       'How was the family member\'s pressure handled without dismissing '
       'their information?',
       'At what point would the legal authority to act have changed, and '
       'did everybody present know that line?',
       'What happened after - who owned the follow-up, and was the loop '
       'closed?'],
      'behavioral-health-agency',
      'a crisis intervention protocol, a risk assessment instrument or a '
      'legal standard for involuntary intervention. All three belong to the '
      'state, the board and the behavioural health authority.'),

    S('resp.s.mass-casualty-venue',
      'A mass casualty event at a public venue',
      'an indoor venue with several thousand people present',
      'A mass casualty incident has occurred at a public venue. The scene is '
      'not yet confirmed secure, casualties are being moved by members of '
      'the public, and hospitals are being self-referred to faster than they '
      'are being notified.',
      'Every service is at maximum, the structure has to be built while it '
      'is being used, and the informal system is outrunning the formal one.',
      ['fire', 'ems', 'law', 'em', 'social'],
      ['ems.mci-role-clarity', 'ems.documentation-handover',
       'ems.scene-assessment', 'fire.command-establishment',
       'fire.fireground-communication', 'law.interagency-role-clarity',
       'law.handover-to-medical', 'em.ics-role-discipline',
       'em.public-information-warning', 'em.eoc-coordination',
       'social.psychological-first-aid', 'social.disaster-behavioral-health-integration'],
      ['site-safety', 'security-sys', 'fire-alarm', 'acoustic',
       'network-cabling'],
      ['How long until one person could state the total casualty count, and '
       'how wrong was the first number?',
       'What was done about casualties who arrived at hospitals by private '
       'car?',
       'How was the boundary between the security problem and the medical '
       'problem managed in space and in command?',
       'Which positional roles were filled late, and what did that cost?',
       'Who was responsible for the uninjured thousands, and when did that '
       'start?'],
      'fema-nims',
      'a triage system, a tactical response doctrine or a hospital surge '
      'plan. Each has an owner and none of them is this pack.'),

    S('resp.s.shelter-operations',
      'A congregate shelter on its fourth day',
      'a school gymnasium operating as a shelter',
      'A shelter opened for an overnight event is still open on day four. '
      'The population has changed from evacuees to people with nowhere to '
      'go. Two residents are in conflict, one needs dialysis, and the '
      'voluntary agency staffing it is at the end of its rota.',
      'The problem has silently changed category from response to social '
      'services, and the structure running it was designed for the first '
      'category.',
      ['em', 'social', 'ems'],
      ['em.mass-care-coordination', 'em.volunteer-donations',
       'em.access-functional-needs', 'em.recovery-transition',
       'social.resource-navigation', 'social.ethics-and-boundaries',
       'social.trauma-informed-practice',
       'social.vicarious-trauma-supervision', 'ems.special-population-framing',
       'ems.scene-assessment'],
      ['grounds', 'hvacr', 'water-distrib', 'wastewater', 'site-safety'],
      ['On what day did this stop being a response problem, and who noticed?',
       'Who was responsible for the medical needs of residents, as distinct '
       'from emergency response to them?',
       'How was the voluntary agency\'s staffing limit surfaced, and by '
       'whom?',
       'What was the exit plan for each resident, and when was it first '
       'written?',
       'What did the conflict between residents reveal about the shelter\'s '
       'design rather than about the residents?'],
      'voad',
      'a shelter operations manual or a medical special-needs sheltering '
      'standard. Both belong to the sheltering organizations and the state '
      'health authority.'),

    S('resp.s.energy-storage-fire',
      'A thermal event in an energy storage installation',
      'a data centre campus with battery storage and on-site generation',
      'A thermal event has been reported in a battery installation serving a '
      'data centre. Site staff have isolated what they believe they can. The '
      'behaviour of the installation over the next hours is not something '
      'anybody on scene has seen before.',
      'A hazard whose time constant is hours or days rather than minutes, '
      'in a facility whose operator has strong commercial reasons to '
      'minimise disruption.',
      ['fire', 'em'],
      ['fire.size-up', 'fire.command-establishment',
       'fire.risk-benefit-framing', 'fire.building-construction-literacy',
       'em.ics-role-discipline', 'em.public-information-warning',
       'fire.post-incident-analysis'],
      ['battery-storage', 'data-center', 'ev-charging', 'hydrogen',
       'substation', 'electricians', 'instrumentation', 'hvacr'],
      ['What did the site\'s own emergency plan say, and had the fire '
       'service ever read it?',
       'Who made the decision to hold rather than intervene, and on what '
       'basis?',
       'How was the multi-hour nature of the incident resourced - relief, '
       'feeding, command continuity?',
       'What was told to the neighbouring occupancies, and when?',
       'Which trades on that site had the knowledge the incident needed?'],
      'nfpa',
      'a guide to energy storage system firefighting. That is an active, '
      'contested technical area owned by the codes and the manufacturers, '
      'and nothing about agents, isolation or entry is stated here.'),

    S('resp.s.earthquake-facade',
      'Facade and masonry hazard after an earthquake',
      'a downtown block of older masonry buildings',
      'After a significant earthquake, the street is full of people, '
      'parapets and cladding are visibly displaced on several buildings, and '
      'the natural gathering point for the public is directly beneath them.',
      'The urge of every responder and every civilian is to be in the street, '
      'and the street is the hazard.',
      ['fire', 'em', 'law', 'social'],
      ['fire.size-up', 'fire.building-construction-literacy',
       'em.damage-assessment', 'em.ics-role-discipline',
       'em.public-information-warning', 'law.interagency-role-clarity',
       'social.psychological-first-aid'],
      ['masonry-restore', 'bricklayers', 'stone-carvers', 'cladding',
       'curtainwall', 'shoring', 'bridge-inspect', 'steel-erectors'],
      ['Who first said the street itself was unsafe, and how long did that '
       'take?',
       'How were cordons set with no engineering assessment available yet?',
       'How were building inspectors and structural engineers requested, '
       'and how long did they take?',
       'What was the message to a public that wanted to go back inside?',
       'Which of the building trades could have answered the questions being '
       'asked, and is there a standing arrangement to reach them?'],
      'em-accreditation',
      'a post-earthquake safety evaluation procedure. Placarding and '
      'structural evaluation are the building official\'s and the '
      'engineer\'s.'),

    S('resp.s.underground-entrapment',
      'Entrapment in an underground works',
      'a tunnel or mine working with a single access',
      'Workers are unaccounted for beyond a blockage in an underground '
      'working. Atmosphere beyond the blockage is unknown. The operator has '
      'its own trained rescue capability and its own commercial exposure.',
      'Specialist capability sits with the operator, statutory authority '
      'sits with regulators who are not yet on scene, and the families are '
      'already at the gate.',
      ['fire', 'ems', 'em', 'social'],
      ['fire.command-establishment', 'fire.crew-integrity',
       'fire.risk-benefit-framing', 'em.ics-role-discipline',
       'em.mutual-aid-requesting', 'ems.scope-literacy',
       'social.psychological-first-aid', 'social.crisis-engagement'],
      ['miners', 'blasters', 'shoring', 'confined-space', 'high-angle',
       'surveyors', 'instrumentation'],
      ['How was command shared with the operator\'s own rescue organisation?',
       'What was the information route to the families, and who owned it '
       'from the first hour?',
       'How was the temptation to commit untrained responders managed?',
       'When did the statutory regulator arrive, and what changed then?',
       'What was the plan for a multi-day operation, written on day one?'],
      'osha-and-state-plans',
      'a mine or tunnel rescue procedure. Underground rescue is a '
      'regulated, certified discipline and nothing about it is described '
      'here.'),

    S('resp.s.post-fire-reentry',
      'Re-entry to a fire-damaged older building',
      'a fire-damaged mixed-use building of early twentieth century '
      'construction',
      'The fire is out. Residents want their belongings. The building '
      'contains materials typical of its era, the water has been in it for '
      'twelve hours, and the owner wants a decision tonight.',
      'The emergency is over and the hazard is not, which is exactly when '
      'the organisational attention leaves.',
      ['fire', 'em', 'social'],
      ['fire.contamination-discipline', 'fire.post-incident-analysis',
       'fire.building-construction-literacy', 'em.damage-assessment',
       'em.recovery-transition', 'social.resource-navigation',
       'social.trauma-informed-practice'],
      ['asbestos', 'lead-abatement', 'mold-remediation', 'industrial-clean',
       'insulators', 'waterproofers', 'firestop'],
      ['Who was authorised to permit re-entry, and did the crews on scene '
       'know that?',
       'What was told to residents about the hazard, in what language, and '
       'in writing?',
       'How were the responders\' own exposures recorded?',
       'Who picked up the residents\' housing problem, and on what day?',
       'Which remediation trades had to be involved, and did anybody have '
       'their number?'],
      'osha-and-state-plans',
      'an asbestos, lead or mould assessment and abatement procedure. Each '
      'is a licensed activity governed by regulation.'),

    S('resp.s.crane-collapse',
      'A crane failure in a city centre',
      'a downtown construction site with adjacent occupied buildings',
      'A tower crane has failed, with debris across a street and into an '
      'adjacent building. The site was active. The failure mechanism is '
      'unknown and the remaining structure is still loaded.',
      'A rescue problem, a stability problem and a criminal-investigation '
      'problem occupying the same square metres from the first minute.',
      ['fire', 'ems', 'law', 'em', 'social'],
      ['fire.size-up', 'fire.command-establishment',
       'fire.building-construction-literacy', 'fire.risk-benefit-framing',
       'ems.mci-role-clarity', 'law.interagency-role-clarity',
       'law.report-and-evidence-integrity', 'em.ics-role-discipline',
       'em.damage-assessment', 'social.psychological-first-aid'],
      ['crane-ops', 'riggers', 'operating-eng', 'heavy-equip',
       'ironworkers', 'steel-erectors', 'site-safety', 'demolition'],
      ['How was the tension between rescue access and evidence preservation '
       'handled, and who arbitrated it?',
       'Who assessed the stability of the remaining structure, and how long '
       'did that take?',
       'How were site workers accounted for, given the site\'s own records?',
       'When did the regulator and the investigating agency arrive, and what '
       'did they need that was already gone?',
       'How was the wider construction workforce - who will all hear about '
       'this - supported?'],
      'osha-and-state-plans',
      'a lifting equipment investigation or heavy rigging procedure. '
      'Failure analysis belongs to the regulator and to engineers.'),

    S('resp.s.ammonia-release',
      'A refrigerant release at a cold storage facility',
      'a cold storage warehouse with an industrial refrigeration plant',
      'A refrigerant release has been reported in a plant room. Workers have '
      'self-evacuated, one is symptomatic, and the plant continues to run '
      'because stopping it has consequences for the stored product.',
      'A commercial cost to the correct action, a symptomatic worker, and a '
      'plant that only three people in the building understand.',
      ['fire', 'ems'],
      ['fire.size-up', 'fire.risk-benefit-framing',
       'fire.command-establishment', 'ems.scene-assessment',
       'ems.scope-literacy', 'ems.exposure-control',
       'ems.documentation-handover'],
      ['hvacr', 'pipefitters', 'instrumentation', 'confined-space',
       'industrial-clean', 'insulators'],
      ['Who could actually describe the plant, and how were they found?',
       'How was the pressure to keep the plant running handled, and by '
       'whom?',
       'How were potentially exposed workers identified and accounted for, '
       'including those who had already gone home?',
       'What information went to the receiving hospital, and when?',
       'What does the facility\'s own emergency plan say, and had the fire '
       'service seen it?'],
      'osha-and-state-plans',
      'a refrigerant emergency procedure or an exposure treatment guide. '
      'The first belongs to the process safety regulation, the second to '
      'the medical director.'),

    S('resp.s.hot-work-fire',
      'A fire started by hot work on an occupied site',
      'a partially occupied building undergoing fit-out',
      'A fire has started in a concealed space during welding work on an '
      'occupied floor of a building under fit-out. The hot work permit '
      'system exists. The fire watch had ended.',
      'A preventable incident where the prevention system existed and did '
      'not run, and where the people who could say why are the people who '
      'will be blamed.',
      ['fire', 'law'],
      ['fire.size-up', 'fire.building-construction-literacy',
       'fire.command-establishment', 'fire.post-incident-analysis',
       'law.report-and-evidence-integrity', 'law.authority-literacy'],
      ['welders', 'firestop', 'insulators', 'site-safety', 'drywall',
       'sheetmetal', 'acoustic'],
      ['What did the permit system require, and what actually happened?',
       'How did the fire get into the concealed space, and what does that '
       'say about the firestopping?',
       'How was the investigation separated from the blame, in the first '
       'hour?',
       'Who on the site knew the fire watch had ended, and who could have '
       'stopped the work?',
       'Is this a finding for the crews, the contractor or the permit '
       'system?'],
      'nfpa',
      'a hot work permit procedure or a fire investigation methodology. '
      'Both have their own standards and their own qualified people.'),

    S('resp.s.line-of-duty-aftermath',
      'The days after a line-of-duty death',
      'an agency, its families and its community',
      'A responder has been killed on duty. The agency has to continue '
      'responding, support a family, cooperate with an investigation, '
      'manage a public funeral and hold together a workforce that has just '
      'learned the job can do this.',
      'Every organisational system is loaded at once, the people who would '
      'normally manage it are the people affected by it, and every decision '
      'is permanent in the family\'s memory.',
      ['fire', 'law', 'ems', 'em', 'social'],
      ['fire.post-incident-analysis', 'fire.command-establishment',
       'law.wellness-peer-support', 'law.field-supervision',
       'ems.fatigue-and-critical-incident',
       'em.continuity', 'social.vicarious-trauma-supervision',
       'social.ethics-and-boundaries', 'social.crisis-engagement',
       'social.disaster-behavioral-health-integration'],
      [],
      ['Who was the family\'s single point of contact, and how quickly was '
       'that named?',
       'How was the workforce kept in service without pretending nothing '
       'had happened?',
       'How were the investigation\'s needs and the agency\'s grief kept '
       'from colliding?',
       'Who supported the supervisors, who were supporting everybody else?',
       'What was in place before the day, and what had to be invented?'],
      'employer-agency',
      'a critical incident stress intervention, a line-of-duty death '
      'protocol or a benefits guide. The first is clinical, the second is '
      'the agency\'s and the association\'s, the third is statutory.'),

    S('resp.s.offsite-notification',
      'An offsite notification from a major energy facility',
      'a jurisdiction inside a facility\'s emergency planning zone',
      'A facility has made a notification that escalates its emergency '
      'classification. The jurisdiction\'s role is protective action for the '
      'public, and its information comes entirely from the facility.',
      'The jurisdiction must make a public protective action decision using '
      'technical information it cannot independently verify, from an '
      'operator with its own interests, on a timeline set by the facility.',
      ['em', 'law', 'fire', 'social'],
      ['em.public-information-warning', 'em.eoc-coordination',
       'em.ics-role-discipline', 'em.access-functional-needs',
       'em.exercise-and-after-action', 'law.community-legitimacy',
       'law.interagency-role-clarity', 'fire.risk-benefit-framing',
       'social.cultural-humility-language-access'],
      ['nuclear', 'instrumentation', 'substation', 'transmission',
       'hydro', 'district-energy'],
      ['What did the jurisdiction independently know, and what did it take '
       'entirely on trust?',
       'How was the protective action decision made and who signed it?',
       'How was the message delivered to people who do not speak English '
       'and people without power?',
       'When was this last exercised, and did the exercise allow failure?',
       'What would the jurisdiction have done if the facility\'s '
       'information had been wrong?'],
      'fema-nims',
      'a radiological emergency plan or a protective action guide. Both are '
      'federally governed and neither is stated here.'),
]


# ---------------------------------------------------------------------------
# VALIDATION. Everything below fails the build rather than emitting a
# registry with a hole in it.

# Two fields every authority record carries, set here from the fact of the
# build rather than typed once per record: this build opened nothing,
# because this build has no network, and no record carries a URL.
for _aid, _a in AUTHORITIES.items():
    for _f in ('name', 'kind', 'owns', 'this_pack_reproduces'):
        need(_a, _f, 'AUTHORITIES.' + _aid)
    _a['document_read_by_this_build'] = False
    _a['url'] = None

SERVICE_KEYS = sorted(SERVICES)
TIER_IDS = {sk: [t[0] for t in need(SERVICES[sk], 'tiers', 'SERVICES.' + sk)]
            for sk in SERVICE_KEYS}

for sk in SERVICE_KEYS:
    svc = SERVICES[sk]
    for aid in need(svc, 'standards_bodies', 'SERVICES.' + sk):
        need_in(AUTHORITIES, aid, 'SERVICES.%s.standards_bodies' % sk)
    rep = need(svc, 'representation', 'SERVICES.' + sk)
    for f in ('kinds', 'real_acronyms', 'what_they_do_here'):
        need(rep, f, 'SERVICES.%s.representation' % sk)
    if len(TIER_IDS[sk]) != len(set(TIER_IDS[sk])):
        raise ValueError('respond: %s: duplicate role tier id' % sk)
    if len(TIER_IDS[sk]) < 4:
        raise ValueError('respond: %s: a service with fewer than four role '
                         'tiers is not a career, it is a job title' % sk)

COMP_BY_ID = {}
for c in COMPETENCIES:
    cid = need(c, 'id', 'a competency record')
    if cid in COMP_BY_ID:
        raise ValueError('respond: duplicate competency id %r' % cid)
    sk = need_in(SERVICES, need(c, 'service', cid), '%s.service' % cid)
    need_in(TIER_IDS[sk], need(c, 'tier_floor', cid), '%s.tier_floor' % cid)
    need_in(AUTHORITIES, need(c, 'authority', cid), '%s.authority' % cid)
    look = need(c, 'look_for', cid)
    if len(look) < 3:
        raise ValueError('respond: %s: a competency with fewer than three '
                         'observable behaviours cannot be debriefed' % cid)
    for f in ('title', 'what_it_is', 'why_it_matters'):
        if len(need(c, f, cid)) < 24:
            raise ValueError('respond: %s: %s is too thin to be useful'
                             % (cid, f))
    COMP_BY_ID[cid] = c

SCEN_BY_ID = {}
for s in SCENARIOS:
    sid = need(s, 'id', 'a scenario record')
    if sid in SCEN_BY_ID:
        raise ValueError('respond: duplicate scenario id %r' % sid)
    for sk in need(s, 'services', sid):
        need_in(SERVICES, sk, '%s.services' % sid)
    for cid in need(s, 'competencies', sid):
        need_in(COMP_BY_ID, cid, '%s.competencies' % sid)
    # The cross-link rule the brief is emphatic about: a hall slug that does
    # not resolve against the bundle's own roster stops the build. This pack
    # does not get to invent a trade.
    for slug in need(s, 'halls', sid):
        need_in(HALL_NAME, slug, '%s.halls' % sid)
        need_in(HALL_CAMPUS, slug, '%s.halls (campus roster)' % sid)
    if len(need(s, 'debrief_questions', sid)) < 4:
        raise ValueError('respond: %s: a frame with fewer than four debrief '
                         'questions is a prompt, not a frame' % sid)
    if len(set(need(s, 'competencies', sid))) < 4:
        raise ValueError('respond: %s: a frame that exercises fewer than '
                         'four competencies is not creating pressure' % sid)
    need_in(AUTHORITIES, need(s, 'authority', sid), '%s.authority' % sid)
    need(s, 'this_frame_is_not', sid)
    SCEN_BY_ID[sid] = s


# ---------------------------------------------------------------------------
# THE TRAINING ITEMS. Every role tier, every competency and every scenario
# frame becomes an item carrying the three fields that matter: who owns the
# real standard, who has signed this off, and whether it still needs a
# practitioner to read it. The last two are the same for all of them today
# and the count at the bottom is what says so.

ITEMS = []


def item(kind, iid, label, service, authority):
    need_in(AUTHORITIES, authority, 'item %s.authority' % iid)
    rec = {'kind': kind, 'id': iid, 'label': label, 'service': service,
           'authority': authority, 'signed_off_by': None,
           'needs_practitioner_review': True}
    ITEMS.append(rec)
    return rec


for sk in SERVICE_KEYS:
    svc = SERVICES[sk]
    bodies = need(svc, 'standards_bodies', 'SERVICES.' + sk)
    for tid, tname, tdesc in need(svc, 'tiers', 'SERVICES.' + sk):
        item('role_tier', '%s.tier.%s' % (sk, tid), tname, sk, bodies[0])
for c in COMPETENCIES:
    item('competency', c['id'], c['title'], c['service'], c['authority'])
for s in SCENARIOS:
    item('scenario_frame', s['id'], s['title'], '+'.join(sorted(s['services'])),
         s['authority'])

if any(need(i, 'signed_off_by', i['id']) is not None for i in ITEMS):
    raise ValueError('respond: an item claims a sign-off. Nothing here has '
                     'been signed off by anybody and the mechanism must not '
                     'be able to claim otherwise from inside this file.')
if not all(need(i, 'needs_practitioner_review', i['id']) is True
           for i in ITEMS):
    raise ValueError('respond: every item needs practitioner review, '
                     'without exception')


# ---------------------------------------------------------------------------
# CROSS-LINKS INTO THE 111 TRADE HALLS.

HALL_LINKS = {}
for s in SCENARIOS:
    for slug in s['halls']:
        HALL_LINKS.setdefault(slug, []).append(s['id'])

CROSS_LINKS = {}
for slug in sorted(HALL_LINKS):
    fin = need(FIN_HALLS, slug, FINISHES_PATH + '#halls')
    conds = need(fin, 'conditions', '%s#halls.%s' % (FINISHES_PATH, slug))
    ppe = sorted({p for room, rec in conds.items()
                  for p in need(rec, 'ppe',
                                '%s#halls.%s.conditions.%s'
                                % (FINISHES_PATH, slug, room))})
    CROSS_LINKS[slug] = {
        'hall_name': need(HALL_NAME, slug, HALLS_PATH),
        'campus': need(HALL_CAMPUS, slug, CAMPUSES_PATH),
        'frames': sorted(HALL_LINKS[slug]),
        'trade_ppe_in_that_hall': ppe,
    }

UNTOUCHED_HALLS = [h for h in HALL_SLUGS if h not in CROSS_LINKS]
FRAMES_WITHOUT_HALLS = sorted(s['id'] for s in SCENARIOS if not s['halls'])
EXERCISED = {cid for s in SCENARIOS for cid in s['competencies']}
UNEXERCISED = sorted(set(COMP_BY_ID) - EXERCISED)
USED_AUTHORITIES = ({i['authority'] for i in ITEMS}
                    | {a for sk in SERVICE_KEYS
                       for a in SERVICES[sk]['standards_bodies']})
UNUSED_AUTHORITIES = sorted(set(AUTHORITIES) - USED_AUTHORITIES)
MULTI_AGENCY = [s for s in SCENARIOS if len(s['services']) >= 3]


# ---------------------------------------------------------------------------
# THE GAPS. Numerator and denominator are computed above every call. A gap
# that closes stays listed - that is the rule the bundle runs on.

GAPS = []


def gap(gid, question, have, of, unit, how, note):
    if not isinstance(have, int) or not isinstance(of, int):
        raise TypeError('respond: %s: a gap counts things, in whole numbers'
                        % gid)
    if of <= 0:
        raise ValueError('respond: %s: nothing to count against' % gid)
    if have > of:
        raise ValueError('respond: %s: %d of %d is not a share'
                         % (gid, have, of))
    if len(how) < 40 or len(note) < 40:
        raise ValueError('respond: %s: say how it was computed and what it '
                         'means' % gid)
    GAPS.append({'id': gid, 'question': question, 'have': have, 'of': of,
                 'unit': unit, 'missing': of - have,
                 'share': round(float(have) / float(of), 4),
                 'how': how, 'note': note})


N_TIERS = sum(1 for i in ITEMS if i['kind'] == 'role_tier')
N_COMPS = sum(1 for i in ITEMS if i['kind'] == 'competency')
N_FRAMES = sum(1 for i in ITEMS if i['kind'] == 'scenario_frame')
N_ITEMS = len(ITEMS)
SIGNED = sum(1 for i in ITEMS if i['signed_off_by'] is not None)
SIGNED_COMPS = sum(1 for i in ITEMS
                   if i['kind'] == 'competency' and i['signed_off_by'] is not None)
SIGNED_FRAMES = sum(1 for i in ITEMS
                    if i['kind'] == 'scenario_frame' and i['signed_off_by'] is not None)
SIGNED_TIERS = sum(1 for i in ITEMS
                   if i['kind'] == 'role_tier' and i['signed_off_by'] is not None)
REVIEWED_SERVICES = sum(
    1 for sk in SERVICE_KEYS
    if all(i['signed_off_by'] is not None for i in ITEMS
           if i['service'] == sk))
# The representation records as they will be published: endorsement is a
# field with a value of None, not an absent field, so that the count below
# is a count of records rather than a count of nothing.
PUBLISHED_REPS = {sk: dict(SERVICES[sk]['representation'],
                           endorsement=None,
                           endorsement_note='no organization named here has '
                           'reviewed, approved or endorsed any part of this '
                           'pack, and none has been contacted')
                  for sk in SERVICE_KEYS}
ENDORSED = sum(1 for sk in SERVICE_KEYS
               if need(PUBLISHED_REPS[sk], 'endorsement',
                       'representation of ' + sk) is not None)
AUTHORITIES_OPENED = sum(
    1 for aid, a in AUTHORITIES.items()
    if need(a, 'document_read_by_this_build', 'AUTHORITIES.' + aid) is True)

gap('respond.signed_off_items',
    'how many first-responder training items carry a named practitioner '
    'sign-off',
    SIGNED, N_ITEMS, 'items',
    'every role tier, competency domain and scenario frame this build '
    'produced, counted here, against the ones whose signed_off_by is not '
    'null - which is none of them',
    'this is the same shape of number as pack.signed_off_halls at 0 of 111, '
    'and for the same reason: the field exists, refuses an unnamed reviewer '
    'by being null, and nobody who does this work has filled one in')
gap('respond.signed_off_competencies',
    'how many competency domains have been reviewed by a serving '
    'practitioner of that service',
    SIGNED_COMPS, N_COMPS, 'competencies',
    'competency items whose signed_off_by is not null, over every competency '
    'domain in this registry, both counted from the item list',
    'a competency domain that no firefighter, officer, paramedic, emergency '
    'manager or licensed social worker has read is a proposal about their '
    'job written by somebody who does not do it')
gap('respond.signed_off_scenario_frames',
    'how many scenario frames have been reviewed by a serving practitioner',
    SIGNED_FRAMES, N_FRAMES, 'frames',
    'scenario frame items whose signed_off_by is not null, over every frame '
    'in this registry, both counted from the item list',
    'the frames are the part most likely to be mistaken for training '
    'material, so the number that says nobody has checked them matters most '
    'here')
gap('respond.signed_off_role_tiers',
    'how many role tier descriptions have been confirmed by somebody who '
    'holds that role',
    SIGNED_TIERS, N_TIERS, 'tiers',
    'role tier items whose signed_off_by is not null, over every tier across '
    'the five services, both counted from the item list',
    'rank and role names differ between agencies in the same county; these '
    'descriptions are written to be corrected and nobody has corrected them')
gap('respond.practitioner_reviewed_services',
    'how many of the services have had all of their content reviewed',
    REVIEWED_SERVICES, len(SERVICE_KEYS), 'services',
    'a service counts only when every item attributed to it is signed off; '
    'computed over the item list, not asserted',
    'no service is partially done here - all five are at zero, and a '
    'partial figure would be the more dangerous one to publish because it '
    'would imply the rest had been looked at')
gap('respond.authority_documents_opened',
    'how many of the named standards documents this build actually read',
    AUTHORITIES_OPENED, len(AUTHORITIES), 'authorities',
    'authority records whose document_read_by_this_build is true, over every '
    'authority named in this pack; the field is set from the build, and this '
    'build has no network at all',
    'this is why the tier is AUTHORED. Every standards host is unreachable '
    'from here, nothing was fetched, and a citation nobody opened would be a '
    'citation costume rather than a source')
gap('respond.organization_endorsements',
    'how many of the representing organizations have endorsed any of this',
    ENDORSED, len(SERVICE_KEYS), 'services',
    'a service counts when its representation record carries a non-null '
    'endorsement; the field is absent-and-therefore-null on all five and the '
    'count is taken from the records',
    'IAFF, FOP, NAGE, AFSCME, SEIU, NASW and the rest are real bodies with '
    'real members. None of them has seen this, none has been contacted, and '
    'no local, lodge, chapter or council of any of them is named anywhere in '
    'this pack')
gap('respond.halls_touched_by_a_frame',
    'how many of the bundle\'s trade halls a responder scenario actually '
    'touches',
    len(CROSS_LINKS), N_HALLS, 'halls',
    'the distinct hall slugs named across every scenario frame, each one '
    'resolved against pack/registry/halls.json at build time, over the full '
    'roster in that file',
    'this one is not zero, and it is the number that says how much of the '
    'bundle a responder curriculum would reach. The halls it does not reach '
    'are listed so the omission is inspectable rather than implied')
gap('respond.competencies_exercised_by_a_frame',
    'how many competency domains at least one scenario frame exercises',
    len(EXERCISED), N_COMPS, 'competencies',
    'the distinct competency ids named across every frame, over every '
    'competency in the registry, both counted from the source lists',
    'a competency no frame exercises is a competency with nowhere to be '
    'observed, and the unexercised ones are listed by name rather than '
    'averaged away')
gap('respond.multi_agency_frames',
    'how many frames put three or more services on the same incident',
    len(MULTI_AGENCY), N_FRAMES, 'frames',
    'frames whose services list holds three or more of the five, counted '
    'here from the frame records',
    'multi-agency coordination is the thing every after-action report in '
    'this domain finds broken, so the share of frames that actually force '
    'it is worth publishing rather than assuming')


# ---------------------------------------------------------------------------
# THE SAFETY SCAN. This pack refuses to carry anything a reader could
# mistake for an authoritative protocol, and refuses to name a local or a
# person. The scan runs over the finished payload text and fails the build.

FORBIDDEN = [
    ('a dose, rate or engineering figure with a unit attached',
     r'\b\d+(\.\d+)?\s*'
     r'(mg|mcg|ug|ml|cc|mL|gram|grams|units?|joules?|J\b|gpm|lpm|psi|bar|kPa|'
     r'mmHg|bpm|L/min|mg/kg|mcg/kg)\b'),
    ('a named local, lodge, chapter, council or apparatus number',
     r'\b(local|lodge|chapter|council|branch|post|unit|station|engine|truck|'
     r'medic|squad|battalion|district|company)\s+(no\.?\s*)?\d+\b'),
    # A rank followed by a capitalised word is how a person gets named. The
    # allow-list holds the words that legitimately follow a rank in a BODY's
    # name - "Peace Officer Standards and Training commission" is a
    # commission, not a man called Standards - and nothing else may.
    ('a person named behind a rank or honorific',
     r'\b(Chief|Captain|Lieutenant|Sergeant|Officer|Firefighter|Paramedic|'
     r'Deputy|Sheriff|Commissioner|Dr\.|Prof\.)\s+'
     r'(?!(?:Standards|Officer|Officers|Training|Safety|Support)\b)'
     r'[A-Z][a-z]{2,}'),
    ('a reserved provenance word that belongs to orbis/',
     r'AI-SYNTHESIZED'),
    ('a clinical agent or intervention named as if it were guidance',
     r'\b(epinephrine|naloxone|adrenaline|midazolam|ketamine|fentanyl|'
     r'tourniquet|defibrillat|intubat|cricothyro|needle decompress|'
     r'chest seal)\w*'),
    ('a triage category or scoring threshold presented as a cut-off',
     r'\b(START triage|SALT triage|triage tag|immediate/delayed|'
     r'Glasgow Coma|GCS \d|RPM score)\b'),
    ('a tactical entry, restraint or control instruction',
     r'\b(breach the|stack on|dynamic entry|prone restraint|chokehold|'
     r'carotid|pressure point|joint lock|forced entry technique)\b'),
    ('a run-time fetch',
     r'https?://'),
]


# ---------------------------------------------------------------------------

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

HONESTY = {
    'status': 'AUTHORED: every word of this pack was written here. No '
              'standards document was opened, no page was fetched and no '
              'model produced any of it. This environment has no network - '
              'NFPA, NREMT, FEMA, the state POST commissions and the social '
              'work boards are all unreachable from it - so all %d authority '
              'records carry document_read_by_this_build false and none '
              'carries a URL. A citation nobody opened is a costume.'
              % len(AUTHORITIES),
    'nobody_qualified_has_read_this': 'Nothing in this pack has been '
                                      'reviewed by a serving firefighter, a '
                                      'police officer, a paramedic, an '
                                      'emergency manager or a licensed '
                                      'social worker. Not one of the %d '
                                      'training items carries a sign-off - '
                                      'the number is %d of %d - and it must '
                                      'not be used as the basis of any real '
                                      'certification, qualification, hiring '
                                      'decision or operational procedure.'
                                      % (N_ITEMS, SIGNED, N_ITEMS),
    'scaffold_not_protocol': 'This is a scaffold: role taxonomy, competency '
                             'domains, scenario frames and debrief '
                             'structures. It is not a protocol and contains '
                             'no procedure, no drug, no dose, no triage '
                             'cut-off, no vital-sign threshold, no tactical '
                             'technique and no flow, pressure or air figure. '
                             '%d patterns for exactly those things are '
                             'scanned over the finished registry and the '
                             'build fails on any of them. Where a reader '
                             'wants the real requirement, every one of the '
                             '%d items names the body that owns it.',
    'the_authority_is_elsewhere': 'Each of the %d authority records names a '
                                  'real body and states that this pack '
                                  'reproduces none of its content. NFPA owns '
                                  'the fire service qualification standards; '
                                  'the state POST commission owns law '
                                  'enforcement certification; NREMT and the '
                                  'state EMS office own the certification '
                                  'levels and the agency medical director '
                                  'owns every clinical decision under them; '
                                  'FEMA and the national incident management '
                                  'system own the command structure; the '
                                  'NASW code of ethics and the state '
                                  'licensing board own social work practice. '
                                  'This pack points; it does not restate.'
                                  % len(AUTHORITIES),
    'unions_and_associations': 'IAFF, FOP, NAGE, AFSCME, SEIU, NASW and the '
                               'other bodies named across the %d services '
                               'are real organizations. They are named here '
                               'as TYPES of organization and by the role '
                               'they play in a workforce. No local, lodge, '
                               'chapter, council or bargaining unit number '
                               'appears anywhere in this pack, no officer or '
                               'member is named, and none of these '
                               'organizations has reviewed, approved or '
                               'endorsed any part of this - the endorsement '
                               'count is %d of %d services.'
                               % (len(SERVICE_KEYS), ENDORSED,
                                  len(SERVICE_KEYS)),
    'the_cross_links_are_real': 'The %d trade halls a scenario frame touches '
                                'are resolved against '
                                'pack/registry/halls.json at build time and '
                                'an unresolvable slug stops the build, so no '
                                'link here is invented. %d of the %d halls '
                                'are touched by no frame at all and are '
                                'listed by name. %d frames touch no trade '
                                'hall - a crisis call in a flat and the days '
                                'after a line-of-duty death are not building '
                                'problems, and pretending otherwise to '
                                'improve a coverage number would be the '
                                'dishonest option.'
                                % (len(CROSS_LINKS), len(UNTOUCHED_HALLS),
                                   N_HALLS, len(FRAMES_WITHOUT_HALLS)),
    'ppe_is_not_transferable': 'Each cross-linked hall publishes the PPE its '
                               'own practice rooms require, read from '
                               'surfaces/registry/finishes.json. That is the '
                               'TRADE\'s protective equipment for a teaching '
                               'space. It is not responder PPE, it is not an '
                               'entry decision and it does not transfer. It '
                               'is carried so that a frame about a collapse '
                               'can show what the people who built the thing '
                               'already wear, not so anybody can dress for '
                               'an incident from it.',
    'what_a_frame_is': 'A scenario frame records a situation, the decision '
                       'pressure it creates, the competencies it exercises '
                       'and the questions a debrief would ask. It records no '
                       'correct answer, and that is deliberate: the correct '
                       'answer belongs to the governing authority and the '
                       'local agency, and this pack holds neither. All %d '
                       'frames also state, in their own words, what they are '
                       'NOT.' % N_FRAMES,
    'the_debrief_structure_is_ours': 'The %d-stage debrief structure below '
                                     'is this pack\'s own scaffold. It is '
                                     'not the federal exercise and '
                                     'evaluation doctrine, and it is not a '
                                     'critical incident stress intervention '
                                     '- the first belongs to FEMA, the '
                                     'second is a clinical activity '
                                     'belonging to licensed people, and '
                                     'confusing either with this would be a '
                                     'real harm.' % len(DEBRIEF),
    'coverage_is_published_as_a_number': 'Nothing here is described as '
                                         'comprehensive. %d competency '
                                         'domains across %d services, %d '
                                         'scenario frames, %d of %d '
                                         'competencies exercised by at least '
                                         'one frame, %d halls touched of '
                                         '%d. The gaps block carries %d '
                                         'numbers and the closed ones stay '
                                         'listed.'
                                         % (N_COMPS, len(SERVICE_KEYS),
                                            N_FRAMES, len(EXERCISED),
                                            N_COMPS, len(CROSS_LINKS),
                                            N_HALLS, len(GAPS)),
}
HONESTY['scaffold_not_protocol'] = (HONESTY['scaffold_not_protocol']
                                    % (len(FORBIDDEN), N_ITEMS))

payload = {
    'pack': 'respond',
    'product': 'a first-responder and disaster-relief training scaffold: '
               'role taxonomy, competency domains, scenario frames and '
               'debrief structures across five services, every item naming '
               'the body that owns the real standard and none of them '
               'signed off by anybody',
    'pack_version': PACK_VERSION,
    'source_stamp': stamp,
    'provenance': 'AUTHORED',
    'honesty': HONESTY,
    'counts': {
        'services': len(SERVICE_KEYS),
        'role_tiers': N_TIERS,
        'competencies': N_COMPS,
        'scenario_frames': N_FRAMES,
        'training_items': N_ITEMS,
        'authorities': len(AUTHORITIES),
        'authorities_unused': len(UNUSED_AUTHORITIES),
        'debrief_stages': len(DEBRIEF),
        'observable_behaviours': sum(len(c['look_for']) for c in COMPETENCIES),
        'debrief_questions': sum(len(s['debrief_questions'])
                                 for s in SCENARIOS),
        'hall_cross_links': sum(len(v['frames']) for v in CROSS_LINKS.values()),
        'halls_touched': len(CROSS_LINKS),
        'halls_untouched': len(UNTOUCHED_HALLS),
        'halls_total': N_HALLS,
        'frames_without_hall_contact': len(FRAMES_WITHOUT_HALLS),
        'multi_agency_frames': len(MULTI_AGENCY),
        'competencies_exercised': len(EXERCISED),
        'competencies_unexercised': len(UNEXERCISED),
        'signed_off_items': SIGNED,
        'organization_endorsements': ENDORSED,
        'authority_documents_opened': AUTHORITIES_OPENED,
        'forbidden_patterns_scanned': len(FORBIDDEN),
        'by_service': {sk: {
            'role_tiers': len(TIER_IDS[sk]),
            'competencies': sum(1 for c in COMPETENCIES if c['service'] == sk),
            'frames': sum(1 for s in SCENARIOS if sk in s['services']),
            'standards_bodies': len(SERVICES[sk]['standards_bodies']),
        } for sk in SERVICE_KEYS},
    },
    'gaps': GAPS,
    'authorities': AUTHORITIES,
    'services': {sk: {
        'name': SERVICES[sk]['name'],
        'scope': SERVICES[sk]['scope'],
        'standards_bodies': SERVICES[sk]['standards_bodies'],
        'representation': PUBLISHED_REPS[sk],
        'tiers': [{'id': t[0], 'name': t[1], 'what_the_role_is': t[2],
                   'authority': SERVICES[sk]['standards_bodies'][0],
                   'signed_off_by': None,
                   'needs_practitioner_review': True}
                  for t in SERVICES[sk]['tiers']],
    } for sk in SERVICE_KEYS},
    'competencies': [dict(c, signed_off_by=None,
                          needs_practitioner_review=True)
                     for c in COMPETENCIES],
    'scenario_frames': [dict(s, signed_off_by=None,
                             needs_practitioner_review=True)
                        for s in SCENARIOS],
    'debrief_structure': [{'n': i + 1, 'stage': d[0], 'question': d[1],
                           'purpose': d[2]}
                          for i, d in enumerate(DEBRIEF)],
    'hall_cross_links': CROSS_LINKS,
    'halls_untouched': UNTOUCHED_HALLS,
    'frames_without_hall_contact': FRAMES_WITHOUT_HALLS,
    'competencies_unexercised': UNEXERCISED,
    'authorities_unused': UNUSED_AUTHORITIES,
    'reads': sorted([HALLS_PATH, CAMPUSES_PATH, FINISHES_PATH,
                     MANIFEST_PATH]),
}

blob = json.dumps(payload, indent=1, sort_keys=True) + '\n'
for label, pat in FORBIDDEN:
    m = re.search(pat, blob)
    if m:
        raise SystemExit('respond: the safety scan found %s: %r at offset '
                         '%d. This pack does not carry that, whatever the '
                         'sentence around it was trying to do.'
                         % (label, m.group(0), m.start()))

for rec in payload['competencies'] + payload['scenario_frames']:
    need(rec, 'authority', 'a published item')
    if need(rec, 'signed_off_by', rec['id']) is not None \
            or need(rec, 'needs_practitioner_review', rec['id']) is not True:
        raise SystemExit('respond: %s escaped the sign-off contract'
                         % rec['id'])

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(blob)

print('respond: %d services, %d role tiers, %d competency domains '
      '(%d observable behaviours), %d scenario frames (%d debrief questions, '
      '%d multi-agency); %d training items, %d signed off; %d authorities, '
      '%d documents opened; %d hall cross-links over %d of %d halls '
      '(%d frames touch none); %d gaps published; %d bytes'
      % (len(SERVICE_KEYS), N_TIERS, N_COMPS,
         payload['counts']['observable_behaviours'], N_FRAMES,
         payload['counts']['debrief_questions'], len(MULTI_AGENCY),
         N_ITEMS, SIGNED, len(AUTHORITIES), AUTHORITIES_OPENED,
         payload['counts']['hall_cross_links'], len(CROSS_LINKS), N_HALLS,
         len(FRAMES_WITHOUT_HALLS), len(GAPS), OUT.stat().st_size))
