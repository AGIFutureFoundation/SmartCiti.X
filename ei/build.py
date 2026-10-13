#!/usr/bin/env python3
"""ei/ - the emotional-intelligence layer for this bundle's agents.

WHAT WAS MISSING. Every advisor in agents/registry/advisors.json answers a
technical question about the room it stands in. The guide answers six
questions about the place a learner is in. The mentor contract in fabric/
clamps a hint rung. Not one of them has a written answer to a learner who
is frustrated, ashamed of an error, frightened of a machine, worn out,
being frozen out by a crew, or carrying something from a bad call. The
absence was not neutral: an agent with nothing written for that case
improvises, and an improvising agent in this domain is the failure mode
this pack exists to prevent.

WHAT THIS PACK IS. Structure, not speech. There is no dialogue in this
file. Every record says what an agent NOTICES, what it is TRYING to do,
what it does NOT do, how far it may go, the observable point at which it
must STOP, and which rung of a human ladder it hands to. A page or an
agent turns that into words; this registry never does, and the suite
asserts that no field in it reads like a line of scripted speech.

THE HARD LIMIT, WHICH IS THE WHOLE POINT. A guide in a training app is
not a therapist, not a counsellor and not a crisis line. Three structures
make that hard to forget rather than merely stated:

  1. Every response carries `scope` and `stop_condition`. A response
     without either is refused by this build, so there is no way to add a
     new one and quietly leave the stopping point out.
  2. Every response carries a `handoff` naming a rung of a five-rung
     ladder of HUMANS. The ladder names the TYPE of resource and never a
     number, an organisation or a person - a wrong number in a crisis is
     worse than no number, and this build has no network with which to
     check one.
  3. Every response carries `max_turns`, bounded by the same ceiling the
     spec already sets for a Socratic exchange, read out of the spec
     rather than typed here. An agent that cannot count its turns can
     talk its way past its own stop condition.

WHY THE FRAMEWORKS ARE NAMED AND NOT REPRODUCED. This is AUTHORED work
with no network access and no clinician behind it. Naming psychological
first aid, motivational interviewing, Critical Incident Stress Management
and restorative practice says where the SHAPE of these moves comes from.
It does not reproduce any of their protocols, and each framework record
states in its own field what this pack is not reproducing. A pack that
implied it had implemented a clinical protocol would be the exact harm it
is trying to avoid.

WHY THIS CANNOT BE A LICENCE TO OVER-HELP. fabric/ already found that an
over-helping mentor passes the knowledge, scope and persona gates cleanly
and is caught only by cohort outcome. An emotionally attuned agent is the
most likely thing in this bundle to over-help, because comfort feels
generous and reads as care. So the invariant runs the other way: NO
response here may raise the served hint rung. Warmth changes the framing
and the pacing; it never does more of the work. The thresholds and the
measured lift are read out of fabric/ rather than restated here, and the
suite re-reads them.

FAIL CLOSED. Every cross-file read goes through need() or one(); a
missing key or a pattern that matches zero times or twice stops the build
with the path named. There is no default anywhere in this file, because
every default here would be a policy decision about somebody's bad day.
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'ei.json'

MANIFEST = 'pack/manifest.json'
ADVISORS = 'agents/registry/advisors.json'
HALLS = 'pack/registry/halls.json'
SPEC = 'SmartCitiX_TradeCraft_Academy_Spec.md'
EVALS = 'fabric/evals.mjs'
FABRIC_README = 'fabric/README.md'
BUS = 'bus/bus.mjs'


def need(d, key, what):
    """Read a key that must be there. A default in this pack would be a
    policy decision about how an agent treats a distressed person."""
    if not isinstance(d, dict):
        raise TypeError('ei: %s: expected a record, got %s'
                        % (what, type(d).__name__))
    if key not in d:
        raise KeyError('ei: %s: no key %r (it holds %r)'
                       % (what, key, sorted(d)[:16]))
    return d[key]


def text(rel):
    return (ROOT / rel).read_text()


def reg(rel):
    return json.loads(text(rel))


def one(rel, pattern, what, flags=0):
    """Exactly one match, or the build stops. A pattern that has started
    matching twice is a pattern that has stopped meaning what it meant."""
    hits = re.findall(pattern, text(rel), flags)
    if len(hits) != 1:
        raise SystemExit('ei: %s: %r matched %d times in %s, wanted exactly '
                         'one - the file it reads has moved underneath this '
                         'pack' % (what, pattern, len(hits), rel))
    return hits[0]


def many(rel, pattern, what, least, flags=0):
    hits = re.findall(pattern, text(rel), flags)
    if len(hits) < least:
        raise SystemExit('ei: %s: %r matched %d times in %s, wanted at least '
                         '%d' % (what, pattern, len(hits), rel, least))
    return hits


# ---------------------------------------------------------------------------
# facts read out of the rest of the bundle, never typed here

PACK_VERSION = need(reg(MANIFEST), 'pack_version', MANIFEST)

_adv = reg(ADVISORS)
ADVISOR_IDS = sorted(need(_adv, 'advisors', ADVISORS))
ADVISOR_NAMES = {k: need(v, 'name', '%s#advisors.%s' % (ADVISORS, k))
                 for k, v in need(_adv, 'advisors', ADVISORS).items()}
ADVISOR_ROLES = {k: need(v, 'role', '%s#advisors.%s' % (ADVISORS, k))
                 for k, v in need(_adv, 'advisors', ADVISORS).items()}

# ACP-07's four affect labels, taken from the spec's own table rather than
# retyped, so a state here cannot claim a classifier label the classifier
# does not emit.
_acp07_section = text(SPEC).split('## 7. ACP-07')[1].split('## 8.')[0]
AFFECT_LABELS = sorted(set(re.findall(r'\| `([A-Z]+)` \|', _acp07_section)))
if len(AFFECT_LABELS) != 4:
    raise SystemExit('ei: the ACP-07 table in %s no longer lists four affect '
                     'labels (found %r) - the states in this pack map onto '
                     'that table and the mapping has to be re-read by a '
                     'person, not re-rendered' % (SPEC, AFFECT_LABELS))

# The bus topics an agent could actually be listening to. A signal that
# names a topic the bus does not own is refused.
BUS_TOPICS = sorted(set(many(BUS, r"'([a-z_]+\.[a-z_]+)':\s+'", 'bus topics',
                             8)))

# The spec already bounds a Socratic exchange. This pack does not get to
# invent a second, looser ceiling for a harder conversation.
TURN_CEILING = int(one(SPEC, r'bounded dialogue \(. (\d+) turns\)',
                       'the bounded-dialogue turn ceiling'))
REENTRY_DAYS = int(one(SPEC, r'after . (\d+) days away',
                       'the re-entry ramp threshold'))
NO_DIAGNOSIS = one(SPEC, r'(No diagnostic inference from telemetry, ever\.)',
                   "ACP-08's own sentence forbidding diagnostic inference")
ANXIETY_RESPONSE = one(
    SPEC, r'\| `ANXIETY` \|[^|]*\|([^|]*)\|',
    "ACP-07's declared consumer response for ANXIETY").strip()

# fabric/ found the over-help failure and set the thresholds. Read, not
# restated - if fabric re-runs and the lift moves, this pack's honesty
# block moves with it.
OVER_HELP_MAX = float(one(EVALS, r'rungDisciplineMax:\s*([\d.]+)',
                          'the over-help ceiling'))
NON_INFERIORITY = float(one(EVALS, r'outcomeNonInferiority:\s*(-?[\d.]+)',
                            'the gate-5 non-inferiority threshold'))
_lift = one(FABRIC_README, r'lift .(0\.\d+) against a .(0\.\d+) threshold',
            "the over-helper's measured cohort lift")
OBSERVED_LIFT = -float(_lift[0])
if abs(-float(_lift[1]) - NON_INFERIORITY) > 1e-9:
    raise SystemExit('ei: fabric/README.md quotes a gate-5 threshold of %s '
                     'and fabric/evals.mjs sets %s - this pack will not pick '
                     'one of them' % (_lift[1], NON_INFERIORITY))

HALL_ROSTER = need(reg(HALLS), 'halls', HALLS)
HALL_SLUGS = {need(h, 'slug', '%s#halls' % HALLS): h for h in HALL_ROSTER}


# ---------------------------------------------------------------------------
# frameworks - named as the authority for the SHAPE of a move, and each one
# says in its own field what this pack is not reproducing

FRAMEWORKS = [
    {
        'id': 'psychological-first-aid',
        'name': 'psychological first aid',
        'shape_taken': 'the stance that the first useful act after a bad '
                       'moment is practical, unintrusive and oriented to '
                       'linking a person with their own people and their own '
                       'resources, rather than to eliciting an account of '
                       'how they feel.',
        'used_for': 'the overall posture of every response here: notice, '
                    'stay practical, offer the next concrete thing, link '
                    'outward.',
        'not_reproduced': 'no assessment, no protocol step, no screening '
                          'question and no session of any kind. This pack '
                          'reproduces none of the published guidance and '
                          'implements no part of it; it borrowed a posture '
                          'and says so.',
        'why_named': 'so a reader can check where the shape came from '
                     'instead of taking this pack on trust.',
    },
    {
        'id': 'motivational-interviewing',
        'name': 'motivational interviewing',
        'shape_taken': 'ask before advising; reflect the learner\'s own '
                       'stated reason for being here rather than supplying '
                       'one; resist the urge to correct a feeling.',
        'used_for': 'the disengagement, burnout and shame responses, where '
                    'the wrong move is an argument for carrying on.',
        'not_reproduced': 'MI is a clinical conversational method practised '
                          'by trained people with supervision. Nothing here '
                          'is MI, no agent is trained in it, and no agent '
                          'may present itself as practising it.',
        'why_named': 'because the alternative - an agent that talks a tired '
                     'person back into a machine - is the failure this '
                     'borrowing is meant to avoid.',
    },
    {
        'id': 'critical-incident-stress-management',
        'name': 'Critical Incident Stress Management',
        'shape_taken': 'the principle that a structured debrief after a '
                       'critical incident is run by trained people, in '
                       'person, on a timeline that is not the app\'s to '
                       'choose.',
        'used_for': 'the post-incident state, which is the one state in '
                    'this pack where the response is to stop and hand off '
                    'rather than to respond at all.',
        'not_reproduced': 'no defusing, no debriefing, no session, no '
                          'sequence and no phase of any published model. '
                          'This pack takes from it exactly one conclusion: '
                          'that this is not an app\'s job.',
        'why_named': 'the responder series is the reason this state exists, '
                     'and the reason it is the emptiest record here.',
    },
    {
        'id': 'restorative-practice',
        'name': 'restorative practice',
        'shape_taken': 'separate the person from the act; harm between '
                       'people is addressed by people, with the affected '
                       'person having a say in what happens next.',
        'used_for': 'the shame-after-error debrief moves and the '
                    'exclusion-or-hazing response.',
        'not_reproduced': 'no conference, no circle, no facilitation and no '
                          'mediation. An agent that tried to facilitate '
                          'between a learner and a crew would be taking a '
                          'role it cannot hold and cannot be accountable '
                          'for.',
        'why_named': 'hazing is a relationship between people in a hall, '
                     'and naming the frame makes clear why the agent\'s '
                     'only real move is to hand it to one.',
    },
]

# ---------------------------------------------------------------------------
# the handoff ladder - five rungs of HUMANS. Resource TYPES only. No number,
# no organisation, no person, anywhere, ever.

LADDER = [
    {
        'id': 'peer',
        'rank': 1,
        'resource_type': 'another apprentice in the same hall cohort',
        'reached_how': 'through whatever the hall already uses to put '
                       'apprentices in touch with each other; this pack '
                       'holds no roster and introduces nobody.',
        'agent_does': 'names that other people in this hall have stood '
                      'where the learner is standing, and that asking one '
                      'of them is an ordinary thing to do.',
        'agent_must_not': 'name a person, nominate a person, or pass on '
                          'anything the learner said.',
        'latency': 'whenever the learner chooses',
        'why_no_contact_detail': 'a peer is somebody the learner already '
                                 'has; the agent adds nothing by inventing '
                                 'one.',
    },
    {
        'id': 'journey-mentor',
        'rank': 2,
        'resource_type': 'the journey-level mentor or instructor responsible '
                         'for this learner\'s hall',
        'reached_how': 'through the hall\'s own instructor channel. Who that '
                       'is belongs to the hall, not to this bundle.',
        'agent_does': 'says plainly that this is a thing to raise with the '
                      'person who runs the hall, and offers to stop here so '
                      'the learner can.',
        'agent_must_not': 'escalate on the learner\'s behalf without saying '
                          'so, or imply the mentor has already been told.',
        'latency': 'same training day, in the ordinary course',
        'why_no_contact_detail': 'every hall\'s instructor is different and '
                                 'this pack knows none of them.',
    },
    {
        'id': 'member-assistance',
        'rank': 3,
        'resource_type': 'a member-assistance programme or employer '
                         'assistance programme of the kind attached to union '
                         'membership or employment',
        'reached_how': 'through the learner\'s own membership or employment '
                       'paperwork, which states what they have and how to '
                       'use it.',
        'agent_does': 'names that this category of support usually exists '
                      'and is usually confidential from the employer, and '
                      'points the learner at their own paperwork to find '
                      'out what theirs is.',
        'agent_must_not': 'state that the learner has such a programme, '
                          'describe what it covers, or promise how '
                          'confidential it is. Those are facts about a '
                          'specific plan and this pack holds none of them.',
        'latency': 'usually days, sometimes immediate',
        'why_no_contact_detail': 'these are per-local and per-employer. A '
                                 'number published here would be wrong for '
                                 'almost every learner who read it.',
    },
    {
        'id': 'licensed-professional',
        'rank': 4,
        'resource_type': 'a licensed mental-health or medical professional',
        'reached_how': 'through the learner\'s own health cover, their own '
                       'physician, or the programme at rung 3.',
        'agent_does': 'says that what the learner has described is outside '
                      'anything this app can help with and belongs with '
                      'somebody qualified, and stops.',
        'agent_must_not': 'suggest a type of treatment, a diagnosis, a '
                          'medication, a urgency rating, or a specialty. '
                          'Naming the rung is the whole of the move.',
        'latency': 'days to weeks, and the agent does not pretend otherwise',
        'why_no_contact_detail': 'licensing is jurisdictional and this '
                                 'bundle serves halls it cannot enumerate.',
    },
    {
        'id': 'emergency-services',
        'rank': 5,
        'resource_type': 'the emergency service for wherever the learner '
                         'physically is',
        'reached_how': 'by the learner, or by somebody with them, using the '
                       'emergency number of the country they are in.',
        'agent_does': 'stops the session, states that this is a situation '
                      'for emergency help now, and says that the number is '
                      'the local emergency number for where they are.',
        'agent_must_not': 'dial, contact anyone, delay, keep talking, ask a '
                          'follow-up question, or print a number. The app '
                          'cannot know which country a learner is in and a '
                          'wrong emergency number costs the minutes that '
                          'matter.',
        'latency': 'immediate',
        'why_no_contact_detail': 'this is the rung where a wrong number does '
                                 'the most harm, so it is the rung that most '
                                 'firmly has none.',
    },
]
LADDER_IDS = {r['id'] for r in LADDER}

# ---------------------------------------------------------------------------
# signals - things the app can observe. A signal is not a diagnosis, and
# every record carries its own confound so a reader cannot forget that.

def sig(sid, observable, window, may_mean, confound, topic, observable_today,
        reads_body=False):
    return {
        'id': sid,
        'observable': observable,
        'window': window,
        'may_mean': may_mean,
        'confound': confound,
        'bus_topic': topic,
        'observable_today': observable_today,
        'reads_body': reads_body,
        'threshold': {
            'value': None,
            'why': 'no threshold is set here. Every one of these needs a '
                   'per-cohort baseline this bundle has never collected, '
                   'and a number typed in now would be a guess wearing a '
                   'calibration\'s clothes.',
        },
        'not_a_diagnosis': 'this is an observation about actions in an app. '
                           'It is not a statement about a person, a mood, a '
                           'condition or a capacity, and no agent may treat '
                           'it as one.',
    }


SIGNALS = [
    sig('repeat-fail-same-step',
        'the same step of the same task fails repeatedly inside one session, '
        'with the attempts getting shorter rather than longer',
        'within one session',
        ['frustration', 'shame-after-error'],
        'the step may simply be badly written, or its prerequisite may never '
        'have been taught - the content is the first suspect, not the '
        'learner',
        'telemetry.event', True),
    sig('abandon-mid-run',
        'a simulator run is left before its end state, with no completion '
        'and no retry in the same session',
        'within one session',
        ['frustration', 'fear-of-machine', 'overwhelm'],
        'someone walked into the room, the shift started, or the device '
        'died. Most abandonment is logistics.',
        'telemetry.event', True),
    sig('long-idle-after-error',
        'a long pause with the session still open, beginning immediately '
        'after a failed step rather than at a natural break',
        'within one session',
        ['shame-after-error', 'overwhelm'],
        'a person can stop to think, to read, or to answer somebody. Idle '
        'after an error is only interesting because of where it starts.',
        'telemetry.event', True),
    sig('rushing-safety-steps',
        'checklist or walkaround items acknowledged faster than the text '
        'could be read, while the rest of the task runs at normal pace',
        'within one run',
        ['disengagement', 'burnout', 'overwhelm'],
        'a learner on their twentieth walkaround genuinely knows it. Speed '
        'on a familiar list is competence as often as it is avoidance.',
        'telemetry.event', True),
    sig('unsocial-hour-return',
        'sessions starting in the small hours when this learner\'s other '
        'sessions do not',
        'across sessions',
        ['burnout', 'overwhelm'],
        'shift work. This platform serves trades that work nights, and for '
        'a large share of learners the small hours are simply the evening.',
        'telemetry.event', True),
    sig('session-truncation-trend',
        'sessions getting shorter across a run of them, ending before the '
        'quest arc closes',
        'across sessions',
        ['disengagement', 'burnout'],
        'life got busier. A shortening session is a fact about a calendar '
        'at least as often as a fact about a learner.',
        'telemetry.event', True),
    sig('help-refused-then-failure',
        'available hint rungs declined, followed by a failed attempt and an '
        'immediate exit',
        'within one session',
        ['shame-after-error', 'exclusion-or-hazing'],
        'plenty of people would rather work it out alone and come back. '
        'Refusing help is a preference before it is anything else.',
        'hint.served', True),
    sig('hint-dependence-climb',
        'the requested rung climbing across attempts, with success rate flat',
        'across sessions',
        ['overwhelm', 'frustration'],
        'the task may have got harder, or the dial may have stepped up. The '
        'ladder moving is not by itself a person struggling.',
        'hint.served', True),
    sig('long-absence-return',
        'a first session after an absence longer than the re-entry threshold '
        'the spec already sets',
        'across sessions',
        ['disengagement', 'shame-after-error'],
        'holidays, illness, overtime and family. Most returns after a gap '
        'are nothing but a gap.',
        'profile.updated', True),
    sig('one-seat-avoidance',
        'other tasks attempted normally while one specific machine seat is '
        'repeatedly deferred or swapped away from',
        'across sessions',
        ['fear-of-machine'],
        'scheduling, or a preference for the work they are about to be '
        'tested on. Avoidance and prioritisation look identical from here.',
        'telemetry.event', True),
    sig('crew-role-unanswered',
        'in a multi-role crew exercise, calls made from this learner\'s role '
        'go unanswered while the rest of the run proceeds',
        'within one crew run',
        ['exclusion-or-hazing'],
        'a crew exercise with a missing seat, a dropped connection, or a '
        'learner who called at the wrong point in the sequence.',
        'telemetry.event', False),
    sig('gate-fail-then-instant-retry',
        'an assessment gate failed and re-entered within seconds, repeatedly, '
        'with no review step in between',
        'within one session',
        ['frustration', 'shame-after-error'],
        'a learner checking whether a fault was theirs or the simulator\'s. '
        'A fast retry is often a diagnosis of the app, not of the self.',
        'gate.decision', True),
]
SIGNAL_IDS = {s['id'] for s in SIGNALS}

# ---------------------------------------------------------------------------
# states

def st(sid, name, looks_like, not_this, acp07, urgency, agent_may,
       signals, first_suspect):
    return {
        'id': sid,
        'name': name,
        'looks_like': looks_like,
        'is_not': not_this,
        'acp07_nearest': acp07,
        'urgency': urgency,
        'agent_may': agent_may,
        'typical_signals': signals,
        'first_suspect': first_suspect,
    }


STATES = [
    st('frustration', 'Frustration',
       'effort continuing but narrowing - the same approach repeated harder '
       'and faster rather than differently.',
       'not anger at the agent, not a lack of interest, and not a sign that '
       'the task is too hard. Frustration is usually the sound of someone '
       'still trying.',
       'ANXIETY', 'routine', 'respond',
       ['repeat-fail-same-step', 'hint-dependence-climb',
        'gate-fail-then-instant-retry'],
       'the task. A step that frustrates many learners is a content defect '
       'before it is a learner state, and the response says so out loud.'),
    st('shame-after-error', 'Shame after an error',
       'a failed step followed by withdrawal rather than retry - a long '
       'idle, a refused hint, an exit, a return that avoids the same task.',
       'not guilt about an outcome and not a moral matter. Nothing in a '
       'simulator was damaged and nobody was hurt, and the response\'s '
       'first job is to make that concrete.',
       'ANXIETY', 'routine', 'respond',
       ['long-idle-after-error', 'help-refused-then-failure',
        'long-absence-return'],
       'the debrief that did not happen. An error closed without a debrief '
       'is where this state is manufactured.'),
    st('fear-of-machine', 'Fear of a specific machine',
       'competent work everywhere else and repeated deferral of one seat; '
       'when the seat does run, an early abandon.',
       'not incompetence and not irrationality. These machines kill people '
       'in the real world, and a learner who is wary of one has understood '
       'something true.',
       'ANXIETY', 'elevated', 'respond',
       ['one-seat-avoidance', 'abandon-mid-run'],
       'proportion. The response treats the wariness as accurate and works '
       'on the size of the next step, never on the feeling.'),
    st('overwhelm', 'Overwhelm',
       'many things open at once, rising requested hint rungs, flat success, '
       'long pauses that are not thinking pauses.',
       'not a verdict about capacity. Overwhelm is a statement about how '
       'much is open at once, which is a property of the sequence as much '
       'as of the person.',
       'ANXIETY', 'routine', 'respond',
       ['hint-dependence-climb', 'long-idle-after-error', 'abandon-mid-run'],
       'the working set. Too many skills open at once is a sequencing fault '
       'the platform already knows it can make.'),
    st('disengagement', 'Disengagement',
       'shorter sessions, safety steps skimmed, quests left before the arc '
       'closes, longer gaps between returns.',
       'not laziness and not a character judgement. It is the most common '
       'state in any training platform and it usually means the work stopped '
       'being worth the trip.',
       'DISENGAGED', 'routine', 'respond',
       ['session-truncation-trend', 'rushing-safety-steps',
        'long-absence-return'],
       'relevance. A learner who cannot see this week\'s work in next '
       'month\'s job has made a reasonable decision.'),
    st('burnout', 'Burnout',
       'sustained long hours across sessions, unsocial-hour returns against '
       'this learner\'s own pattern, shortening sessions, skimmed safety '
       'steps.',
       'not a clinical diagnosis of any condition, and no agent may use the '
       'word to the learner as though it were one. Here it names a pattern '
       'of load in an app, nothing else.',
       'DISENGAGED', 'elevated', 'respond',
       ['unsocial-hour-return', 'session-truncation-trend',
        'rushing-safety-steps'],
       'load. Hours worked outside this app are invisible here and are '
       'almost always the larger part of the total.'),
    st('exclusion-or-hazing', 'Being excluded or hazed',
       'a learner\'s calls going unanswered in crew work, help refused after '
       'a failure, participation dropping in group exercises while solo work '
       'holds up.',
       'not a conflict the agent can adjudicate and not a misunderstanding '
       'to be smoothed over. If a learner says they are being targeted, that '
       'is a report, not a symptom.',
       None, 'elevated', 'respond-then-hand-off',
       ['crew-role-unanswered', 'help-refused-then-failure'],
       'the crew, not the learner. The response never asks what the learner '
       'did to attract it.'),
    st('post-incident-distress', 'Carrying something from a real call',
       'nothing reliable. In-app behaviour after a real-world critical '
       'incident does not have a signature this bundle can read, and the '
       'pack says so rather than inventing one.',
       'not a state this agent may work with. It is named here so that an '
       'agent has somewhere to put a disclosure other than improvising a '
       'response to it.',
       None, 'hand-off-only', 'hand-off-only',
       [],
       'nothing. There is no diagnosis to reach for and no inference to '
       'draw; there is a person saying something, and a ladder.'),
]
STATE_IDS = {s['id'] for s in STATES}

# ---------------------------------------------------------------------------
# responses

def resp(rid, state, moment, framework, intent, notices, does, does_not,
         scope, stop_condition, handoff, max_turns, dial_may_step_down,
         rung_why, universal=False):
    return {
        'id': rid,
        'state': state,
        'moment': moment,
        'framework': framework,
        'intent': intent,
        'notices': notices,
        'does': does,
        'does_not': does_not,
        'scope': scope,
        'stop_condition': stop_condition,
        'handoff': handoff,
        'max_turns': max_turns,
        'universal': universal,
        'rung_effect': {
            'raises_served_rung': False,
            'dial_may_step_down': dial_may_step_down,
            'why': rung_why,
        },
    }


_RUNG_WHY_PLAIN = (
    'the state changes the framing and the pacing of the help, never its '
    'amount. Doing more of the work for a learner who is having a hard time '
    'is the exact move fabric/ measured as harmful.')
_RUNG_WHY_DIAL = (
    'the dial may step the difficulty down, which is the dial\'s decision '
    'from its own signals and is not the same act as raising the hint rung. '
    'The agent asks for neither.')

RESPONSES = [
    resp('frustration.in-run', 'frustration', 'in_run',
         'motivational-interviewing',
         'interrupt the loop of repeating one approach harder, by making the '
         'next attempt smaller and different rather than easier.',
         ['repeat-fail-same-step', 'gate-fail-then-instant-retry'],
         ['names the specific step that is failing, in the task\'s own words',
          'offers a change of approach at the rung already being served',
          'offers the choice of stopping the run cleanly instead of '
          'continuing',
          'records that this step failed repeatedly, so the content is '
          'reviewed as a suspect'],
         ['does not raise the hint rung to end the discomfort',
          'does not tell the learner to calm down, relax or take a breath',
          'does not comment on how the learner seems to be feeling',
          'does not repeat encouragement it has already given'],
         'one failing step inside one run. Nothing about the learner, the '
         'week, or the job.',
         'stop at the first mention of anything outside this run - the '
         'shift, home, money, sleep, or the body. That sentence is not this '
         'response\'s to answer.',
         'peer', 3, True, _RUNG_WHY_DIAL),
    resp('frustration.at-failure', 'frustration', 'at_failure',
         'restorative-practice',
         'close a failed run in a way that leaves a specific next attempt '
         'rather than a verdict.',
         ['repeat-fail-same-step'],
         ['runs the debrief moves bound to this agent, in order',
          'names the one step to attempt next and at what rung',
          'hands the choice of when back to the learner'],
         ['does not summarise the run as good or bad',
          'does not compare this learner to others',
          'does not promise the next attempt will go better'],
         'the run that just ended.',
         'stop if the learner answers the debrief with a statement about '
         'themselves rather than about the work - "I am useless at this" is '
         'a different conversation and this response does not have it.',
         'peer', 2, False, _RUNG_WHY_PLAIN),
    resp('shame.at-failure', 'shame-after-error', 'at_failure',
         'restorative-practice',
         'separate the person from the mistake before the session ends, '
         'because the gap between the error and the debrief is where this '
         'state hardens.',
         ['long-idle-after-error', 'help-refused-then-failure'],
         ['states plainly what the error did and did not cost, in a '
          'simulator',
          'names the error as a property of the attempt, not of the learner',
          'names what held in the run as specifically as what failed',
          'leaves one concrete next attempt on the table'],
         ['does not reassure in general terms',
          'does not say the mistake was fine if a safety step was missed - '
          'it says what the step is for and that the run is where it is '
          'meant to be found',
          'does not ask how the learner feels about it',
          'does not raise the rung so the next attempt cannot fail'],
         'one error in one run, and what it did and did not cost.',
         'stop if the learner describes the same error happening on a real '
         'job, or describes harm to a real person. That is not a debrief and '
         'the agent has nothing useful to add to it.',
         'journey-mentor', 3, False, _RUNG_WHY_PLAIN),
    resp('shame.at-return', 'shame-after-error', 'at_return',
         'psychological-first-aid',
         'make a return after an avoided failure ordinary, by starting '
         'somewhere other than the thing that was failed.',
         ['long-absence-return', 'one-seat-avoidance'],
         ['opens on work the learner has already completed cleanly',
          'lets the avoided task stay unmentioned until the learner raises '
          'it',
          'notes the re-entry ramp the platform already runs after an '
          'absence, as a property of the system rather than a concession'],
         ['does not mark the absence',
          'does not ask where the learner has been',
          'does not lead with the failed task'],
         'the first task of a returning session.',
         'stop if the learner gives a reason for the absence that is a '
         'health, family or work crisis - the response has no follow-up '
         'question for that and must not invent one.',
         'peer', 2, True, _RUNG_WHY_DIAL),
    resp('fear.before-approach', 'fear-of-machine', 'in_run',
         'psychological-first-aid',
         'shrink the next step until it is one the learner will actually '
         'take, while treating the wariness itself as correct.',
         ['one-seat-avoidance', 'abandon-mid-run'],
         ['states what the machine can actually do to a person, as the '
          'safety record for that room already states it',
          'names the smallest next action that is not the full task - a '
          'walkaround, a cold seat, a controls check with nothing running',
          'names the stop control and who else can stop the machine',
          'confirms the learner may decline the seat today without it being '
          'logged as a failure'],
         ['does not minimise the danger',
          'does not describe the fear as irrational, and does not describe '
          'it at all',
          'does not push a learner into a seat they have declined',
          'does not promise that nothing can go wrong'],
         'the size of the next step on one machine, and the facts about that '
         'machine already recorded elsewhere in this bundle.',
         'stop the moment the learner connects this machine to an injury '
         'they saw or had. That is not fear of a machine; it is a memory, '
         'and it goes up the ladder rather than into a smaller step.',
         'journey-mentor', 4, True, _RUNG_WHY_DIAL),
    resp('fear.between-sessions', 'fear-of-machine', 'between_sessions',
         'motivational-interviewing',
         'keep an avoided seat from quietly becoming a permanent hole in a '
         'learner\'s record, without making the avoidance a subject.',
         ['one-seat-avoidance'],
         ['surfaces, once, that this seat is still open and what it gates',
          'offers the smaller preparatory work that stands in front of it',
          'says that a learner can ask for this seat to be run with their '
          'instructor present, which is a normal request'],
         ['does not raise it more than once in a session',
          'does not frame the avoided seat as a deadline or a risk to '
          'standing',
          'does not offer to remove the requirement'],
         'one open seat and the work that leads to it.',
         'stop if the learner asks to have the seat removed from their path '
         'or says they intend to leave the trade over it - that is a '
         'conversation with the person who runs their hall.',
         'journey-mentor', 2, False, _RUNG_WHY_PLAIN),
    resp('overwhelm.in-run', 'overwhelm', 'in_run',
         'psychological-first-aid',
         'reduce how much is open at once, and treat the sequence as the '
         'likelier fault before the learner.',
         ['hint-dependence-climb', 'long-idle-after-error'],
         ['names how many things are currently open and closes what can be '
          'closed',
          'reduces the run to one task with one success condition',
          'flags the working set for review, since this pattern is a '
          'sequencing fault the platform already knows it can make'],
         ['does not add a new explanation on top of the pile',
          'does not offer a longer worked example as relief',
          'does not describe the learner as overwhelmed'],
         'what is open in this session right now.',
         'stop if what is open is not in the app - if the learner is '
         'carrying work, study and a shift at once, the agent has no lever '
         'on that and should not act as if it does.',
         'journey-mentor', 3, True, _RUNG_WHY_DIAL),
    resp('disengagement.at-return', 'disengagement', 'at_return',
         'motivational-interviewing',
         'give a returning learner an early, real win and let them say what '
         'they came back for, rather than arguing them into staying.',
         ['long-absence-return', 'session-truncation-trend'],
         ['opens with the re-entry ramp the platform already specifies after '
          'a long absence',
          'asks, once, what the learner wants out of the next hour and '
          'sequences to that if it is available',
          'names what the next completed thing unlocks, concretely'],
         ['does not raise the absence as a lapse',
          'does not use streaks, guilt or progress-loss framing',
          'does not promise value it cannot point at in the registry'],
         'the shape of the next session.',
         'stop if the learner says they are leaving the programme or the '
         'trade. The agent does not argue with that; the hall does, if '
         'anyone does.',
         'journey-mentor', 3, True, _RUNG_WHY_DIAL),
    resp('disengagement.between-sessions', 'disengagement',
         'between_sessions', 'motivational-interviewing',
         'find out whether the work stopped being relevant before assuming '
         'the learner stopped caring.',
         ['session-truncation-trend', 'rushing-safety-steps'],
         ['names the skipped or skimmed material specifically',
          'offers the path that reaches the work the learner came for '
          'soonest, if the graph allows it',
          'records relevance as a content signal rather than a learner '
          'signal'],
         ['does not re-send the same material with more encouragement',
          'does not increase contact frequency',
          'does not treat skimming as dishonesty'],
         'the sequence and what it is for.',
         'stop if the answer is about money, hours, transport or childcare. '
         'Those are real reasons and none of them is the app\'s to solve.',
         'journey-mentor', 2, False, _RUNG_WHY_PLAIN),
    resp('burnout.across-sessions', 'burnout', 'between_sessions',
         'motivational-interviewing',
         'name a load pattern the learner may not have seen, and make '
         'stopping for the day an ordinary, unpenalised option.',
         ['unsocial-hour-return', 'session-truncation-trend',
          'rushing-safety-steps'],
         ['states the observed pattern as hours and sessions, not as a '
          'condition',
          'names the platform\'s existing easier-today option and that it '
          'costs nothing',
          'says that hours outside this app are invisible here, so the '
          'learner is the only one who can see the real total'],
         ['does not use the word burnout to the learner as a description of '
          'them',
          'does not advise on sleep, diet, exercise, alcohol or time off',
          'does not ask about the learner\'s job, home or health',
          'does not raise the rung to keep a tired learner progressing'],
         'the pattern of use of this app, which is the only thing this pack '
         'can see.',
         'stop at any mention of not coping, of drinking or using to get '
         'through, or of not wanting to be here. Every one of those goes '
         'straight up the ladder and the coaching ends.',
         'member-assistance', 2, True, _RUNG_WHY_DIAL),
    resp('exclusion.reported', 'exclusion-or-hazing', 'in_run',
         'restorative-practice',
         'treat what the learner describes as a report about a crew, record '
         'that it was made, and get it to a person who can act - without '
         'investigating it.',
         ['crew-role-unanswered', 'help-refused-then-failure'],
         ['says that what has been described is not a normal part of '
          'training here',
          'states that this belongs with the person who runs the hall and '
          'offers to end the session so the learner can raise it',
          'states what the agent will and will not record before recording '
          'anything'],
         ['does not ask what the learner did',
          'does not ask who was involved or gather detail',
          'does not offer to mediate, explain the others\' behaviour, or '
          'suggest the learner is misreading it',
          'does not tell the learner to give it time'],
         'acknowledging a report and naming the rung it goes to. Nothing '
         'about the facts of it.',
         'stop coaching entirely at any description of physical harm, '
         'threats, sexual content, or a protected characteristic being used '
         'against the learner - that is abuse, not exclusion, and it leaves '
         'this pack at rung 3 or above immediately.',
         'journey-mentor', 2, False, _RUNG_WHY_PLAIN),
    resp('post-incident.disclosed', 'post-incident-distress', 'any',
         'critical-incident-stress-management',
         'stop being a coach the moment a real call enters the conversation, '
         'and hand to people, without making the learner tell it again.',
         [],
         ['stops the training thread immediately',
          'states that this is outside anything the app is for',
          'names the rungs of the ladder as categories of people, in order',
          'leaves the session open to be closed by the learner rather than '
          'closing it on them'],
         ['does not ask what happened',
          'does not ask for any detail, sequence or outcome',
          'does not offer a technique, a breathing exercise, a grounding '
          'exercise or any other intervention',
          'does not normalise, reframe, or say that this is common',
          'does not schedule a follow-up or check back in'],
         'one action: stopping and naming the ladder. This response has no '
         'coaching content at all, by design.',
         'this response is itself the stop condition - it begins after '
         'coaching has already ended and it never resumes coaching.',
         'member-assistance', 1, False,
         'no rung is served at all: there is no hint, no task and no '
         'attempt. The ladder is the entire response.',
         universal=True),
]
RESPONSE_IDS = {r['id'] for r in RESPONSES}

# ---------------------------------------------------------------------------
# red lines - each carries the action that replaces the prohibited one

def rl(rid, never, why, required_action, handoff, no_handoff_because=''):
    return {
        'id': rid,
        'never': never,
        'why': why,
        'required_action': required_action,
        'handoff': handoff,
        'no_handoff_because': no_handoff_because,
    }


RED_LINES = [
    rl('no-diagnosis',
       'name, suggest, hint at or rule out any condition, disorder, '
       'difficulty or diagnosis, for the learner or for anybody they '
       'mention.',
       'the platform already forbids it in its own governance rules, and a '
       'training app reaching a conclusion about a person from their click '
       'stream is the thing those rules exist to stop.',
       'describe only the observed actions, in the app\'s own terms, and '
       'hand the person to somebody qualified to say more.',
       'licensed-professional'),
    rl('no-medication',
       'discuss, recommend, discourage, compare or comment on any medication, '
       'dose, substance or supplement, including in response to a direct '
       'question.',
       'there is no circumstance in which a training agent has standing to '
       'say anything at all about a drug.',
       'state that this is a question for a prescriber or a pharmacist and '
       'that the agent will not answer it, then stop that thread.',
       'licensed-professional'),
    rl('no-confidentiality-promise',
       'promise, imply or agree that what the learner says stays between '
       'them and the agent.',
       'it cannot be true here. Affect state is visible to the learner and '
       'their instructor by design, and every adaptation lands on an '
       'immutable override log. An agent that promised secrecy would be '
       'lying to someone at their least defended.',
       'state, before any disclosure goes further, what is recorded and who '
       'can see it, and let the learner decide what to say next.',
       None,
       'this is a duty owed inside the conversation. Nothing is handed on, '
       'which is the point of it.'),
    rl('no-coaching-through-self-harm',
       'continue coaching, ask a follow-up, or keep the training thread open '
       'after any disclosure of self-harm, suicidal thought or intent.',
       'this is the case where a confident, well-meaning, unqualified '
       'response does the most harm, and the agent is unqualified by '
       'construction.',
       'stop the training thread in the same turn, state plainly that this '
       'needs a person and not an app, and name the ladder from rung 4 - and '
       'rung 5 where there is any indication of immediate danger - as '
       'categories of help, never as a number.',
       'emergency-services'),
    rl('no-coaching-through-substance-dependence',
       'coach, advise, assess, quantify or express a view after a disclosure '
       'of dependence on alcohol or any other substance.',
       'this is a health matter with a professional route, and an app that '
       'responds to it with a training plan has mistaken what it was told.',
       'stop the training thread, state that member-assistance programmes of '
       'this kind commonly cover exactly this, and point the learner at '
       'their own membership paperwork to find out what theirs covers.',
       'member-assistance'),
    rl('no-coaching-through-domestic-violence',
       'advise, plan, assess risk or suggest any course of action after a '
       'disclosure of violence or abuse at home.',
       'safety planning is specialist work where a wrong suggestion can '
       'raise the danger, and the app cannot see the situation, the '
       'household or the country.',
       'stop the training thread, state that this needs specialist help and '
       'that such help exists as a category, and say nothing about what the '
       'learner should do.',
       'licensed-professional'),
    rl('no-coaching-through-workplace-abuse',
       'investigate, adjudicate, advise on, or attempt to resolve a report '
       'of harassment, bullying or abuse on a job or in a hall.',
       'these have formal routes with rights attached, and an agent that '
       'handles one informally can destroy a record the learner will need.',
       'acknowledge the report, state that it goes to the person who runs '
       'the hall and through whatever formal route the hall has, and record '
       'only that a report was made.',
       'journey-mentor'),
    rl('no-coaching-through-threat-to-others',
       'continue any thread after a statement of intent to harm another '
       'person.',
       'this is beyond the app entirely and the only safe act is to stop '
       'and escalate.',
       'stop in the same turn, escalate to the top of the ladder, and make '
       'no attempt to assess how serious it was.',
       'emergency-services'),
    rl('no-storing-a-disclosure',
       'store, transcribe, summarise or pass on the content of anything a '
       'learner discloses about their life, health or household.',
       'the platform stores affect labels and scores and explicitly not '
       'inferences about a person; a stored disclosure outlives the moment '
       'and the consent.',
       'record that a handoff rung was offered and nothing about what was '
       'said, and tell the learner that is what is being recorded.',
       None,
       'the duty is to write less, not to send it somewhere else.'),
    rl('no-affect-in-a-score',
       'let any state, signal or response in this pack change a score, a '
       'gate decision, an unlock or a record of standing.',
       'the Inspector already tells learners that nothing narrative can move '
       'a rubric. The moment an emotional state moved a score, every learner '
       'would be right to manage what they showed the agent.',
       'keep every one of these paths out of the grading route entirely, and '
       'let the suite assert it against the graders rather than trusting '
       'this sentence.',
       None,
       'there is nobody to hand to: this is a property of the wiring, not an '
       'event in a conversation.'),
    rl('no-claiming-a-role',
       'describe itself as a counsellor, therapist, coach for anything but '
       'the trade, friend, or as a person; or accept one of those roles when '
       'a learner offers it.',
       'the whole of this pack rests on the learner knowing what they are '
       'talking to. An agent that accepts the role gets trusted with things '
       'it will handle badly.',
       'state what it is - a scripted helper for the training work - in the '
       'same turn the role is offered, and carry on only with the training '
       'work.',
       None,
       'the correction is a statement about itself and goes nowhere else.'),
]
RED_LINE_IDS = {r['id'] for r in RED_LINES}

# ---------------------------------------------------------------------------
# debrief moves - how a failed run is closed so the learner comes back

def dbm(mid, name, when, intent, structure, separates, names_next,
        forbidden_variant, available_today, unavailable_because=''):
    return {
        'id': mid,
        'name': name,
        'when': when,
        'intent': intent,
        'structure': structure,
        'separates_person_from_mistake': separates,
        'names_next_attempt': names_next,
        'forbidden_variant': forbidden_variant,
        'available_today': available_today,
        'unavailable_because': unavailable_because,
    }


DEBRIEF_MOVES = [
    dbm('name-what-held', 'Name what held',
        'first, before anything about the failure',
        'start the debrief from measured fact rather than from the fault, so '
        'the learner hears an accurate account rather than a kind one.',
        'name one or two specific things the run depended on that the '
        'learner did correctly, taken from the rubric axes that scored, not '
        'from impression.',
        False, False,
        'general praise - "good effort", "nice work". Praise that names '
        'nothing is the flattery this bundle bans everywhere else, and it '
        'teaches a learner to discount the next true thing they are told.',
        True),
    dbm('normalise-with-a-rate', 'Normalise with a real rate',
        'immediately after the failure is named',
        'replace "everyone finds this hard" with the measured share of first '
        'attempts that fail this step.',
        'state the observed first-attempt failure rate for this step from '
        'cohort data, and nothing more.',
        True, False,
        'saying it is common without a number. That is a guess offered as '
        'comfort, and if it turns out to be false the learner has been '
        'handled rather than told.',
        False,
        'no cohort has run on this platform, so no step has a first-attempt '
        'failure rate. This move is written and switched off, and the '
        'registry publishes it as off rather than letting an agent '
        'improvise the number.'),
    dbm('separate-person-from-mistake', 'Separate the person from the '
        'mistake',
        'whenever the learner\'s own account turns to themselves',
        'return the subject of the sentence to the attempt.',
        'restate the failure as something the attempt did, name the '
        'condition under which it happened, and leave the learner out of the '
        'grammar entirely.',
        True, False,
        'contradicting the learner about themselves - "you are not bad at '
        'this". That argues about the person, which keeps the person as the '
        'subject.',
        True),
    dbm('name-the-cost-honestly', 'Name what the error did and did not cost',
        'for any failure involving a safety step',
        'stop a missed safety step from being either catastrophised or '
        'waved away.',
        'state what the step exists to prevent, state that in this run it '
        'cost nothing because it was a simulator, and state that the run is '
        'exactly where this is meant to be found.',
        True, False,
        'telling a learner a missed safety step does not matter. It does, '
        'and a learner who is told otherwise has been taught the wrong '
        'thing kindly.',
        True),
    dbm('name-the-next-attempt', 'Name one concrete next attempt',
        'last, before the session closes',
        'leave the learner with a specific action rather than an intention.',
        'name the single step to attempt next, the rung of help that will be '
        'available on it, and nothing beyond that one step.',
        False, True,
        'a plan with several steps, or an encouragement to try again '
        'generally. Both leave the learner to do the deciding at the moment '
        'they are least able to.',
        True),
    dbm('hand-the-choice-back', 'Hand the choice back',
        'after the next attempt is named',
        'make stopping a normal option rather than a failure, using a '
        'mechanism the platform already has.',
        'offer retry now, retry later, or the platform\'s existing '
        'easier-today option, and state that the last of these is logged '
        'without questions and costs nothing.',
        False, True,
        'asking whether the learner wants to try once more. A question with '
        'one socially acceptable answer is not a choice.',
        True),
    dbm('close-the-session-cleanly', 'Close the session cleanly',
        'when the debrief itself has reached a stop condition',
        'end without leaving a thread open that the agent is not allowed to '
        'pick up.',
        'state that the session is ending, state what has been recorded, '
        'name the handoff rung once, and stop - with no follow-up question '
        'and no scheduled check-in.',
        False, False,
        'a warm sign-off that invites the learner to come back and talk any '
        'time. The agent cannot keep that offer, and an offer it cannot keep '
        'is the confidentiality promise in another form.',
        True),
]
DEBRIEF_IDS = {d['id'] for d in DEBRIEF_MOVES}

# ---------------------------------------------------------------------------
# agent bindings - resolved against the real advisor registry

_UNIVERSAL_RESPONSES = sorted(r['id'] for r in RESPONSES if r['universal'])

_BINDING_SOURCE = {
    'guide': {
        'responses': ['disengagement.at-return', 'shame.at-return'],
        'debrief_moves': [],
        'scope_note': 'meets a learner at the door, so it carries the return '
                      'cases and nothing that belongs inside a run.',
        'out_of_scope': ['fear-of-machine', 'exclusion-or-hazing',
                         'burnout'],
    },
    'safety-steward': {
        'responses': ['fear.before-approach', 'overwhelm.in-run'],
        'debrief_moves': ['name-the-cost-honestly',
                          'separate-person-from-mistake'],
        'scope_note': 'holds a room to its condition record, so it is the '
                      'agent a frightened learner is standing in front of - '
                      'and the one that must never trade a safety step for '
                      'reassurance.',
        'out_of_scope': ['burnout', 'disengagement'],
    },
    'crib-keeper': {
        'responses': ['frustration.in-run'],
        'debrief_moves': ['hand-the-choice-back'],
        'scope_note': 'issues and takes back tools, which is a short '
                      'interaction; it carries the in-run frustration case '
                      'because that is where it sees people, and nothing '
                      'longer.',
        'out_of_scope': ['burnout', 'exclusion-or-hazing', 'overwhelm'],
    },
    'layout-hand': {
        'responses': ['frustration.in-run', 'frustration.at-failure'],
        'debrief_moves': ['name-what-held', 'name-the-next-attempt'],
        'scope_note': 'works where a small early error becomes a large late '
                      'one, which is the classic frustration shape.',
        'out_of_scope': ['burnout', 'post-incident-distress'],
    },
    'inspector': {
        'responses': ['shame.at-failure', 'frustration.at-failure'],
        'debrief_moves': ['name-what-held', 'separate-person-from-mistake',
                          'name-the-cost-honestly', 'name-the-next-attempt',
                          'normalise-with-a-rate'],
        'scope_note': 'is the agent that delivers the failure, so it owns '
                      'the debrief. It already tells learners nothing '
                      'narrative can move a score, which is what makes its '
                      'warmth safe.',
        'out_of_scope': ['fear-of-machine', 'exclusion-or-hazing'],
    },
    'foreman': {
        'responses': ['exclusion.reported', 'overwhelm.in-run',
                      'burnout.across-sessions'],
        'debrief_moves': ['close-the-session-cleanly',
                          'hand-the-choice-back'],
        'scope_note': 'runs the crew and the hand-offs, so a crew that is '
                      'freezing someone out is its business - and the rung '
                      'above it is a person the foreman can actually name in '
                      'a real hall.',
        'out_of_scope': ['fear-of-machine'],
    },
    'records-clerk': {
        'responses': [],
        'debrief_moves': ['close-the-session-cleanly'],
        'scope_note': 'keeps the records, so its one job here is the '
                      'opposite of a response: it is the agent that can say '
                      'what is written down and who sees it, which is what '
                      'the confidentiality red line requires somebody to be '
                      'able to answer.',
        'out_of_scope': ['frustration', 'shame-after-error',
                         'fear-of-machine', 'overwhelm', 'disengagement',
                         'burnout', 'exclusion-or-hazing'],
    },
    'operator': {
        'responses': ['fear.before-approach', 'fear.between-sessions',
                      'frustration.in-run', 'shame.at-failure'],
        'debrief_moves': ['name-what-held', 'name-the-cost-honestly',
                          'name-the-next-attempt', 'hand-the-choice-back'],
        'scope_note': 'stands at the machine, which is where fear of a '
                      'machine actually happens and where a learner who '
                      'declines a seat must be able to decline it.',
        'out_of_scope': ['exclusion-or-hazing'],
    },
    'dispatcher': {
        'responses': ['disengagement.at-return',
                      'disengagement.between-sessions'],
        'debrief_moves': [],
        'scope_note': 'sends learners to halls and campuses, so it sees the '
                      'gaps between sessions and the returns, and nothing '
                      'inside a run.',
        'out_of_scope': ['fear-of-machine', 'shame-after-error',
                         'exclusion-or-hazing'],
    },
}

AGENT_BINDINGS = []
for aid in sorted(_BINDING_SOURCE):
    if aid not in ADVISOR_IDS:
        raise SystemExit(
            'ei: agent binding names %r, which is not an advisor in %s. The '
            'registry holds %r. This pack binds to real agents or it does '
            'not build - an invented id would be a response set that never '
            'runs, published as though it did.'
            % (aid, ADVISORS, ADVISOR_IDS))
    b = _BINDING_SOURCE[aid]
    rs = sorted(set(b['responses']) | set(_UNIVERSAL_RESPONSES))
    AGENT_BINDINGS.append({
        'agent': aid,
        'agent_name': ADVISOR_NAMES[aid],
        'agent_role': ADVISOR_ROLES[aid],
        'responses': rs,
        'universal_responses': list(_UNIVERSAL_RESPONSES),
        'debrief_moves': sorted(b['debrief_moves']),
        'red_lines': sorted(RED_LINE_IDS),
        'scope_note': b['scope_note'],
        'states_out_of_scope': sorted(b['out_of_scope']),
    })

_bound_agents = {b['agent'] for b in AGENT_BINDINGS}
_unbound = sorted(set(ADVISOR_IDS) - _bound_agents)
if _unbound:
    raise SystemExit(
        'ei: %d advisor(s) in %s have no binding here (%s). Every advisor a '
        'learner can talk to needs at least the red lines and the universal '
        'response, or there is an agent in this bundle with nothing written '
        'for the hardest thing it can be told.'
        % (len(_unbound), ADVISORS, ', '.join(_unbound)))


# ---------------------------------------------------------------------------
# validation - fail closed, naming the record and the field

def require(records, fields, what):
    seen = set()
    for r in records:
        rid = need(r, 'id', what)
        if rid in seen:
            raise SystemExit('ei: %s: duplicate id %r' % (what, rid))
        seen.add(rid)
        for f in fields:
            v = need(r, f, '%s[%s]' % (what, rid))
            if v is None or v == '' or v == []:
                raise SystemExit(
                    'ei: %s[%s]: field %r is empty. In this pack an empty '
                    'field is a decision nobody made.' % (what, rid, f))
    return seen


require(FRAMEWORKS, ['name', 'shape_taken', 'used_for', 'not_reproduced',
                     'why_named'], 'frameworks')
require(LADDER, ['rank', 'resource_type', 'reached_how', 'agent_does',
                 'agent_must_not', 'latency', 'why_no_contact_detail'],
        'handoff ladder')
require(SIGNALS, ['observable', 'window', 'may_mean', 'confound', 'bus_topic',
                  'threshold', 'not_a_diagnosis'], 'signals')
require(STATES, ['name', 'looks_like', 'is_not', 'urgency', 'agent_may',
                 'first_suspect'], 'states')
require(RESPONSES, ['state', 'moment', 'framework', 'intent', 'does',
                    'does_not', 'scope', 'stop_condition', 'handoff',
                    'max_turns', 'rung_effect'], 'responses')
require(RED_LINES, ['never', 'why', 'required_action'], 'red lines')
require(DEBRIEF_MOVES, ['name', 'when', 'intent', 'structure',
                        'forbidden_variant'], 'debrief moves')

for s in SIGNALS:
    for m in s['may_mean']:
        if m not in STATE_IDS:
            raise SystemExit('ei: signal %s points at state %r, which does '
                             'not exist' % (s['id'], m))
    if s['bus_topic'] not in BUS_TOPICS:
        raise SystemExit('ei: signal %s names bus topic %r; %s owns %r'
                         % (s['id'], s['bus_topic'], BUS, BUS_TOPICS))
    if s['reads_body']:
        raise SystemExit('ei: signal %s claims to read the body. No signal in '
                         'this pack may - there is no camera, no microphone '
                         'and no wearable in this bundle\'s input contract, '
                         'and inferring affect from a person rather than '
                         'from their actions is the line the platform\'s own '
                         'governance draws.' % s['id'])

for s in STATES:
    if s['acp07_nearest'] is not None and s['acp07_nearest'] not in AFFECT_LABELS:
        raise SystemExit('ei: state %s claims affect label %r, which the '
                         'ACP-07 classifier does not emit (%r)'
                         % (s['id'], s['acp07_nearest'], AFFECT_LABELS))
    for sg in s['typical_signals']:
        if sg not in SIGNAL_IDS:
            raise SystemExit('ei: state %s names signal %r, which does not '
                             'exist' % (s['id'], sg))

_fw = {f['id'] for f in FRAMEWORKS}
for r in RESPONSES:
    if r['state'] not in STATE_IDS:
        raise SystemExit('ei: response %s is for state %r, which does not '
                         'exist' % (r['id'], r['state']))
    if r['framework'] not in _fw:
        raise SystemExit('ei: response %s names framework %r, which is not '
                         'declared' % (r['id'], r['framework']))
    if r['handoff'] not in LADDER_IDS:
        raise SystemExit('ei: response %s hands off to %r, which is not a '
                         'rung of the ladder' % (r['id'], r['handoff']))
    for n in r['notices']:
        if n not in SIGNAL_IDS:
            raise SystemExit('ei: response %s notices signal %r, which does '
                             'not exist' % (r['id'], n))
    if not (1 <= r['max_turns'] <= TURN_CEILING):
        raise SystemExit(
            'ei: response %s allows %d turns; the spec bounds an agent '
            'dialogue at %d and a harder conversation does not get a looser '
            'ceiling' % (r['id'], r['max_turns'], TURN_CEILING))
    if need(r['rung_effect'], 'raises_served_rung',
            'response %s rung_effect' % r['id']) is not False:
        raise SystemExit(
            'ei: response %s would raise the served hint rung. No response '
            'in this pack may: fabric/ measured an over-helping mentor at a '
            'cohort lift of %.3f against a %.2f threshold, and an agent that '
            'over-helps out of sympathy is the same failure with a better '
            'motive.' % (r['id'], OBSERVED_LIFT, NON_INFERIORITY))

_covered = {r['state'] for r in RESPONSES}
_uncovered = sorted(STATE_IDS - _covered)
if _uncovered:
    raise SystemExit('ei: %d state%s no response (%s). A state named and '
                     'not answered is worse than one never named.'
                     % (len(_uncovered),
                        ' has' if len(_uncovered) == 1 else 's have',
                        ', '.join(_uncovered)))

for r in RED_LINES:
    if r['handoff'] is None:
        if not r['no_handoff_because']:
            raise SystemExit('ei: red line %s hands off nowhere and does not '
                             'say why' % r['id'])
    elif r['handoff'] not in LADDER_IDS:
        raise SystemExit('ei: red line %s hands off to %r, which is not a '
                         'rung' % (r['id'], r['handoff']))

for d in DEBRIEF_MOVES:
    if not d['available_today'] and not d['unavailable_because']:
        raise SystemExit('ei: debrief move %s is switched off and does not '
                         'say why' % d['id'])

_ranks = [r['rank'] for r in LADDER]
if _ranks != list(range(1, len(LADDER) + 1)):
    raise SystemExit('ei: the ladder\'s ranks are %r, which is not a ladder'
                     % _ranks)

# ---------------------------------------------------------------------------
# the responder series, counted twice because the two counts disagree

RESPONDER_WORDS = ['fire', 'rescue', 'medic', 'ambulance', 'emergency',
                   'responder', 'hazmat', 'paramedic']
_pat = re.compile('|'.join(RESPONDER_WORDS), re.I)
_keyword_hits = sorted(
    h['slug'] for h in HALL_ROSTER
    if _pat.search('%s %s %s' % (need(h, 'slug', HALLS), need(h, 'name', HALLS),
                                 need(h, 'focus', HALLS))))
# Declared, and each one checked against the roster: halls whose subject IS
# rescue work, as opposed to halls that install fire-stopping or braze
# medical gas.
RESCUE_HALL_SLUGS = ['confined-space', 'high-angle']
for _s in RESCUE_HALL_SLUGS:
    if _s not in HALL_SLUGS:
        raise SystemExit('ei: declared rescue hall %r is not in %s'
                         % (_s, HALLS))
RESCUE_HALLS = [{'slug': _s,
                 'name': need(HALL_SLUGS[_s], 'name', HALLS),
                 'focus': need(HALL_SLUGS[_s], 'focus', HALLS)}
                for _s in RESCUE_HALL_SLUGS]
# And halls that are a first-responder SERVICE - a fire service, an
# ambulance service, a police service. There are none, and the empty list is
# the finding rather than an omission.
RESPONDER_SERVICE_SLUGS = []

# ---------------------------------------------------------------------------
# counts, computed

_records = (len(SIGNALS) + len(STATES) + len(RESPONSES) + len(RED_LINES)
            + len(DEBRIEF_MOVES) + len(AGENT_BINDINGS))

COUNTS = {
    'frameworks': len(FRAMEWORKS),
    'handoff_rungs': len(LADDER),
    'signals': len(SIGNALS),
    'signals_observable_today': sum(1 for s in SIGNALS
                                    if s['observable_today']),
    'signals_with_calibrated_threshold': sum(
        1 for s in SIGNALS if s['threshold']['value'] is not None),
    'states': len(STATES),
    'states_the_agent_may_respond_to': sum(1 for s in STATES
                                           if s['agent_may'] != 'hand-off-only'),
    'states_handoff_only': sum(1 for s in STATES
                               if s['agent_may'] == 'hand-off-only'),
    'responses': len(RESPONSES),
    'responses_that_raise_the_rung': sum(
        1 for r in RESPONSES if r['rung_effect']['raises_served_rung']),
    'universal_responses': len(_UNIVERSAL_RESPONSES),
    'red_lines': len(RED_LINES),
    'red_lines_ending_in_a_handoff': sum(1 for r in RED_LINES
                                         if r['handoff'] is not None),
    'debrief_moves': len(DEBRIEF_MOVES),
    'debrief_moves_available_today': sum(1 for d in DEBRIEF_MOVES
                                         if d['available_today']),
    'agent_bindings': len(AGENT_BINDINGS),
    'advisors_in_registry': len(ADVISOR_IDS),
    'records': _records,
    'clinician_reviewed_records': 0,
    'handoff_rungs_ever_exercised': 0,
    'max_turns_ceiling': TURN_CEILING,
    'halls_in_roster': len(HALL_ROSTER),
    'halls_matching_responder_words': len(_keyword_hits),
    'halls_that_are_rescue_disciplines': len(RESCUE_HALLS),
    'halls_that_are_a_responder_service': len(RESPONDER_SERVICE_SLUGS),
    'longest_response_turns': max(r['max_turns'] for r in RESPONSES),
}

# ---------------------------------------------------------------------------
# gaps, published as numbers rather than described as progress

def gap(gid, question, have, of, unit, how, standing):
    return {
        'id': gid,
        'question': question,
        'have': have,
        'of': of,
        'unit': unit,
        'share': round(have / float(of), 4) if of else None,
        'how_counted': how,
        'standing': standing,
    }


GAPS = [
    gap('ei.clinician_reviewed',
        'how many records here have been read by a clinician, counsellor, '
        'psychologist, social worker or member-assistance professional',
        COUNTS['clinician_reviewed_records'], COUNTS['records'], 'records',
        'the reviewable records in this registry - signals, states, '
        'responses, red lines, debrief moves and agent bindings - counted '
        'here, against a review count that is zero because no review has '
        'happened.',
        'nobody qualified in this subject has read a line of this pack. It '
        'is authored work by a builder with no standing in the field, '
        'informed by the published frameworks it names and reproducing none '
        'of them. Every structural safeguard in here exists because that is '
        'true, not in spite of it.'),
    gap('ei.calibrated_signals',
        'how many signals have a threshold fitted to an actual cohort',
        COUNTS['signals_with_calibrated_threshold'], COUNTS['signals'],
        'signals',
        'signal records whose own `threshold.value` is not null, counted '
        'here.',
        'every threshold is null on purpose. A number typed in now would be '
        'a guess in a calibration\'s clothes, and the platform\'s own dial '
        'is specified to run in shadow mode for weeks before it acts for '
        'exactly this reason.'),
    gap('ei.observable_signals',
        'how many signals this bundle could actually emit today',
        COUNTS['signals_observable_today'], COUNTS['signals'], 'signals',
        'signal records whose own `observable_today` flag is true, counted '
        'here; each names a bus topic that the message bus really owns or '
        'the build refuses it.',
        'the one that is not observable needs per-role timing inside a crew '
        'exercise, which no surface in this bundle records yet. It is '
        'published as unobservable rather than quietly dropped, because the '
        'state it serves - being frozen out by a crew - is the one this '
        'platform is least able to see and least able to afford to miss.'),
    gap('ei.ladder_exercised',
        'how many rungs of the handoff ladder have ever carried a real '
        'learner',
        COUNTS['handoff_rungs_ever_exercised'], COUNTS['handoff_rungs'],
        'rungs',
        'there is no record anywhere in this bundle of a handoff having '
        'happened, so the count is zero by inspection.',
        'the ladder is declared, not proved. No learner has used this app, '
        'so no rung has been tested, and the rung that matters most is the '
        'one nobody has ever had to climb.'),
    gap('ei.debrief_moves_live',
        'how many debrief moves can run today',
        COUNTS['debrief_moves_available_today'], COUNTS['debrief_moves'],
        'moves',
        'debrief move records whose own `available_today` flag is true, '
        'counted here.',
        'the one that is off needs a measured first-attempt failure rate per '
        'step and no cohort has ever run. It stays written and switched off '
        'rather than being softened into "this is common", which is the '
        'guess it exists to replace.'),
    gap('ei.responder_series',
        'how many halls in the roster are a first-responder service, for '
        'which the post-incident state was written',
        COUNTS['halls_that_are_a_responder_service'],
        COUNTS['halls_in_roster'], 'halls',
        'the roster in pack/registry/halls.json read three ways and all '
        'three published: %d halls match at least one responder word (%s), '
        '%d are rescue disciplines by name and focus, and none is an '
        'emergency service. The keyword count is the one a careless reader '
        'would take, so it is printed next to the one that is true.'
        % (COUNTS['halls_matching_responder_words'],
           ', '.join(RESPONDER_WORDS),
           COUNTS['halls_that_are_rescue_disciplines']),
        'the responder series is announced and unbuilt. The post-incident '
        'state is therefore written ahead of the curriculum it is for, and '
        'it is the only state here whose response is to stop rather than to '
        'help. Two existing halls do teach rescue work, which is why the '
        'state is not simply deferred.'),
]

# ---------------------------------------------------------------------------
# honesty - it quotes the numbers above rather than describing them

HONESTY = {
    'status': 'AUTHORED: every record in this pack was written for this '
              'bundle. Nothing was fetched, no network was reached, no '
              'model generated any of it, and no protocol from any published '
              'framework is reproduced here. The four frameworks named in '
              '`frameworks` are cited as the authority for the SHAPE of a '
              'move and for nothing else; each one states in its own record '
              'what this pack does not reproduce.',
    'not_reviewed': 'no clinician, counsellor, psychologist, social worker '
                    'or member-assistance professional has reviewed any part '
                    'of this: %d of %d records are signed off. That is the '
                    'first number in the pack because it is the one that '
                    'governs how the rest should be read.'
                    % (COUNTS['clinician_reviewed_records'],
                       COUNTS['records']),
    'not_a_therapist': 'an agent running this pack is not a therapist, not a '
                       'counsellor, not a crisis line and not a person. '
                       'Every one of the %d responses carries a scope and an '
                       'observable stop condition, every one names a rung of '
                       'a ladder of humans, and the longest exchange any of '
                       'them permits is %d turns against the spec\'s own '
                       'ceiling of %d.'
                       % (COUNTS['responses'], COUNTS['longest_response_turns'],
                          COUNTS['max_turns_ceiling']),
    'no_contact_details': 'there is not one telephone number, organisation, '
                          'service name, web address or person in this pack, '
                          'and the suite regexes the payload to keep it that '
                          'way. The ladder names %d TYPES of resource. A '
                          'wrong number in a crisis is worse than no number, '
                          'this build has no network with which to check '
                          'one, and a number that was right for one hall '
                          'would be wrong for the rest.'
                          % COUNTS['handoff_rungs'],
    'no_dialogue': 'this pack contains no speech. It says what an agent '
                   'notices, what it is trying to do, what it does not do, '
                   'how far it may go and where it stops. Writing the words '
                   'would have been writing therapy, and nobody here is '
                   'qualified to write therapy.',
    'signals_are_not_diagnoses': 'a signal is an observation about actions '
                                 'in an app. All %d carry their own '
                                 'innocent explanation in a `confound` '
                                 'field, none reads a body, and %d of %d '
                                 'have a threshold fitted to a real cohort. '
                                 'The platform\'s own governance says it '
                                 'plainly: "%s"'
                                 % (COUNTS['signals'],
                                    COUNTS['signals_with_calibrated_threshold'],
                                    COUNTS['signals'], NO_DIAGNOSIS),
    'no_comfort_over_help': 'an emotionally attuned agent is the most likely '
                            'thing in this bundle to over-help, because '
                            'comfort feels generous. fabric/ already '
                            'measured that failure: an over-helper passes '
                            'the knowledge, scope and persona gates cleanly '
                            'and is caught only by cohort outcome, at a lift '
                            'of %.3f against a %.2f threshold, with over-help '
                            'capped at %.0f%% of turns. So %d of the %d '
                            'responses here raise the served hint rung, and '
                            'the build refuses one that would. Warmth '
                            'changes the framing and the pacing; it never '
                            'does more of the work.'
                            % (OBSERVED_LIFT, NON_INFERIORITY,
                               OVER_HELP_MAX * 100,
                               COUNTS['responses_that_raise_the_rung'],
                               COUNTS['responses']),
    'the_dial_is_not_this_pack': 'where a learner is struggling, the '
                                 'difficulty dial may step down - ACP-07 '
                                 'already specifies it: "%s". That is the '
                                 'dial acting on its own signals, and it is '
                                 'a different act from an agent raising the '
                                 'hint rung. No agent here asks for either.'
                                 % ANXIETY_RESPONSE,
    'nothing_here_is_scored': 'no state, signal or response in this pack may '
                              'touch a score, a gate, an unlock or a record '
                              'of standing; it is a red line, and the '
                              'Inspector already tells learners that nothing '
                              'narrative moves a rubric. If an emotional '
                              'state could move a score, every learner would '
                              'be right to manage what they showed the '
                              'agent.',
    'nothing_is_stored': 'the pack forbids storing the content of a '
                         'disclosure. What may be recorded is that a rung '
                         'was offered. A learner is told what is being '
                         'written down before anything is.',
    'ladder_is_untested': 'no learner has ever used this app, so %d of the '
                          '%d rungs have carried anybody. Everything here is '
                          'a design, and the rung that matters most is the '
                          'one nobody has ever had to climb.'
                          % (COUNTS['handoff_rungs_ever_exercised'],
                             COUNTS['handoff_rungs']),
    'responder_series_is_unbuilt': 'the post-incident state is written for a '
                                   'first-responder series that does not '
                                   'exist in this bundle: %d of %d halls are '
                                   'an emergency service, though %d are '
                                   'rescue disciplines and %d match a '
                                   'responder keyword. It is the emptiest '
                                   'record in the pack and the only one '
                                   'whose entire response is to stop.'
                                   % (COUNTS['halls_that_are_a_responder_service'],
                                      COUNTS['halls_in_roster'],
                                      COUNTS['halls_that_are_rescue_disciplines'],
                                      COUNTS['halls_matching_responder_words']),
}

CONTRACT = (
    'a record in this pack is structure, never speech. A `signal` is '
    'something the app can observe and says in its own field why that '
    'observation is not a diagnosis; a `state` is a thing worth responding '
    'to; a `response` carries an intent, what it does, what it does NOT do, '
    'a scope, an observable stop_condition, a bounded turn count and one '
    'rung of a ladder of humans; a `red_line` carries the action that '
    'replaces the prohibited one; an `agent_binding` names an agent that '
    'exists in %s or this build stops. Nothing in here is a script, and no '
    'agent may generate one from it and present it as this pack\'s.' % ADVISORS)

payload = {
    'pack': 'ei',
    'product': 'the emotional-intelligence layer for this bundle\'s training '
               'agents and helper guides: what an agent notices, what it '
               'does, what it never does, and the point at which it stops '
               'and hands a person to a person',
    'pack_version': PACK_VERSION,
    'source_stamp': hashlib.sha256(
        pathlib.Path(__file__).read_bytes()).hexdigest()[:16],
    'contract': CONTRACT,
    'honesty': HONESTY,
    'counts': COUNTS,
    'gaps': GAPS,
    'frameworks': FRAMEWORKS,
    'handoff_ladder': LADDER,
    'signals': SIGNALS,
    'states': STATES,
    'responses': RESPONSES,
    'red_lines': RED_LINES,
    'debrief_moves': DEBRIEF_MOVES,
    'agent_bindings': AGENT_BINDINGS,
    'reads': {
        'advisor_registry': ADVISORS,
        'hall_roster': HALLS,
        'spec': SPEC,
        'over_help_thresholds': EVALS,
        'over_help_finding': FABRIC_README,
        'bus_topics': BUS,
        'manifest': MANIFEST,
    },
    'read_values': {
        'affect_labels': AFFECT_LABELS,
        'bus_topics': BUS_TOPICS,
        'turn_ceiling': TURN_CEILING,
        'reentry_days': REENTRY_DAYS,
        'over_help_rate_max': OVER_HELP_MAX,
        'outcome_non_inferiority': NON_INFERIORITY,
        'over_helper_observed_lift': OBSERVED_LIFT,
        'no_diagnostic_inference': NO_DIAGNOSIS,
        'acp07_anxiety_response': ANXIETY_RESPONSE,
        'responder_keyword_halls': _keyword_hits,
        'rescue_halls': RESCUE_HALLS,
    },
}

# ---------------------------------------------------------------------------
# the checks that would make this pack dangerous if they failed

_strings = []


def walk(node, path):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ('say', 'says', 'script', 'line', 'dialogue', 'utterance',
                     'speech'):
                raise SystemExit(
                    'ei: %s carries a %r field. This pack writes structure, '
                    'not speech - a scripted line here would be simulated '
                    'therapy with a registry\'s authority behind it.'
                    % (path, k))
            walk(v, '%s.%s' % (path, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, '%s[%d]' % (path, i))
    elif isinstance(node, str):
        _strings.append((path, node))


walk(payload, 'payload')

# 111 is this bundle's hall count and appears as one, so it is not in the
# emergency-number list; the four that are cannot be confused with a fact
# this bundle publishes.
BANNED = [
    (r'\+?\d[\d ().-]{6,}\d', 'something shaped like a telephone number'),
    (r'\b9-?1-?1\b|\b9-?9-?9\b|\b9-?8-?8\b|\b1-?1-?2\b',
     'an emergency or crisis line number'),
    (r'\b(?:call|dial|text|ring|phone)\s+(?:the\s+|a\s+)?\d', 'a dialling '
     'instruction with digits after it'),
    (r'https?://|www\.|\S+@\S+\.\w', 'a web address or an email address'),
    (r'\b(?:SAMHSA|Samaritans|Lifeline|Befrienders|Shout|Trevor|MIND|NHS|'
     r'OSHA|NIOSH|ICISF|Red Cross|Alcoholics Anonymous|Narcotics Anonymous|'
     r'Crisis Text Line|Suicide Prevention)\b', 'a named organisation or '
     'service'),
]
for path, s in _strings:
    for pat, what in BANNED:
        m = re.search(pat, s)
        if m:
            raise SystemExit(
                'ei: %s contains %s (%r). This pack names types of resource '
                'and never an instance of one: a wrong number in a crisis is '
                'worse than no number, and this build has no network with '
                'which to check one.' % (path, what, m.group(0)))

_dump = json.dumps(payload)
assert 'AI-SYNTHESIZED' not in _dump.upper(), 'ei: that word belongs to orbis/'
_tiers = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED')
assert HONESTY['status'].split(':')[0] in _tiers, \
    'ei: the honesty block must open with one of the declared tiers'
assert COUNTS['responses_that_raise_the_rung'] == 0
assert COUNTS['clinician_reviewed_records'] == 0
assert COUNTS['states_handoff_only'] >= 1, \
    'ei: at least one state must be handed off rather than answered, or the ' \
    'pack has quietly decided it can handle everything'

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + '\n')

print('ei: %d records - %d signals (%d emittable today, %d calibrated), '
      '%d states (%d answered, %d handed off), %d responses over %d '
      'frameworks (0 raise the hint rung; longest %d turns of a %d ceiling), '
      '%d red lines (%d end in a handoff), %d debrief moves (%d live), '
      '%d agent bindings against %d advisors; %d handoff rungs, %d numbers '
      'or organisations named; %d/%d records clinician-reviewed; %d bytes '
      '(source stamp %s)'
      % (COUNTS['records'], COUNTS['signals'],
         COUNTS['signals_observable_today'],
         COUNTS['signals_with_calibrated_threshold'], COUNTS['states'],
         COUNTS['states_the_agent_may_respond_to'],
         COUNTS['states_handoff_only'], COUNTS['responses'],
         COUNTS['frameworks'], COUNTS['longest_response_turns'],
         COUNTS['max_turns_ceiling'], COUNTS['red_lines'],
         COUNTS['red_lines_ending_in_a_handoff'], COUNTS['debrief_moves'],
         COUNTS['debrief_moves_available_today'], COUNTS['agent_bindings'],
         COUNTS['advisors_in_registry'], COUNTS['handoff_rungs'], 0,
         COUNTS['clinician_reviewed_records'], COUNTS['records'],
         OUT.stat().st_size, payload['source_stamp']))
