# The guide

One control, visible in every view and over every panel - the guide is the only thing in this bundle that is reachable from everywhere, which is what makes it a guide rather than a sixth panel.

**11 places** — 6 in the world,
4 panels and 1 page — each with the same
**6 fixed questions**, which is **66 answers** and not a
word more. Nothing accepts free text, because there is nothing behind it that could answer free text.

## What it is

SCRIPTED: the guide is a hand-written, deterministic script - a fixed set of places, six fixed questions each, and one fixed answer to each. No model runs behind it, nothing is generated at view time, and the guide reaches no network of its own.

the guide cannot be asked an open question because it has no way to answer one. The topics below are all of them, and the suite counts them; asking by voice picks one of these same topics and never produces a new answer.

The guide answers six fixed questions about the place the learner is already in, and nothing else. Every answer is a sentence written in this registry with the repo file it is grounded in named in `cites`; the only thing read at view time is a control scheme, and the biggest one - a seat's own keys and its XR mapping - is read from the simulator registry rather than copied here. Nothing is generated, no model runs behind it, and the guide itself reaches no network.

## The 6 asks

The same 6 everywhere, in the same order, so somebody who has asked
them once already knows what is on offer in a place they have never stood in.
The last of them is the one most helpers leave out.

| Ask | What it answers |
|---|---|
| `what` | what this place is |
| `do` | what can be done here |
| `move` | how to move, with the control scheme named |
| `back` | how to get back out |
| `measures` | what, if anything, this place measures |
| `limits` | what this place does NOT claim |

## The 11 places

The page's own `view` maps to a place id, and a place id is the whole routing: region, campus, hall, sim, restoration and avatar are the six world places, and an open panel selects its own place instead.

| Place | Kind | Opened by | What it is | Topics |
|---|---|---|---|---|
| **The region board** | world | where the app starts, and the region button in the top bar from anywhere else | the map of ten campuses the whole bundle hangs off | 6 |
| **A campus** | world | clicking a campus plate on the region board | the green, the ring of halls, the training yard and the restoration pins | 6 |
| **A hall interior** | world | walking through a hall door on the campus green, or picking the hall from the campus | the rooms of one trade hall, with advisors, a crib and the stations | 6 |
| **A training seat** | world | taking a stand in the campus training yard, or starting the seat from inside its hall | one machine simulator, its dash, its rubric and its walkaround | 6 |
| **A restoration site** | world | the restoration button in the top bar, or a restoration pin on a campus | a walkable bay-restoration site and the training tracks bound to it | 6 |
| **The avatar locker** | world | the avatar button in the top bar | the turntable where a learner builds the figure they walk as | 6 |
| **The front door** | page | opening index.html - it is the first page of the bundle | nine surfaces built from the same registries, and what each of them does and does not claim | 6 |
| **The records panel** | panel | the records button in the top bar | every run, pass and best time this browser has kept | 6 |
| **The schools panel** | panel | the schools button in the top bar | the flipped-classroom programme, its stages, bands and proposed districts | 6 |
| **The chapters panel** | panel | the chapter hall on a campus green | which campus hosts the chapter of each hall that is not at home here | 6 |
| **The orbis panel** | panel | the orbis button in the top bar, while standing in a hall | the deterministic video prompt this bundle writes for a hall, and never runs | 6 |

## What is read, not repeated

Every answer names the repo file it is grounded in, and
15 files are cited between them:

- `README.md`
- `agents/registry/advisors.json`
- `avatars/registry/avatars.json`
- `geo/registry/campuses_geo.json`
- `orbis/registry/orbis.json`
- `restoration/registry/restoration.json`
- `schools/registry/schools.json`
- `sims/registry/sims.json`
- `tools/registry/toolcribs.json`
- `training/registry/training.json`
- `unions/registry/campuses.json`
- `unions/registry/chapters.json`
- `unions/registry/unions.json`
- `web/build_3d.py`
- `web/build_home.py`

11 of the 66 topics — the `move` ask of every place —
carry no control rows of their own:

The `move` topic names a scheme id - the page renders that scheme's rows under the answer, and the special id seat:running is resolved against D.sims.sims[curSimId] at view time, never copied.

| Scheme | Where it applies | Rows |
|---|---|---|
| **Walking** | a campus green, a hall interior or a restoration site, once the walk button is pressed | 6 |
| **Mouse and pointer** | the region board, a campus or hall you are not walking in, and the avatar locker | 4 |
| **Touch** | a touch device, where walking is third-person rather than first | 5 |
| **In a headset, outside a seat** | an immersive VR or AR session, while walking rather than driving a seat | 4 |
| **A panel** | any of the four panels, which overlay whichever view you were in | 2 |

Beside those 5 shared schemes sit 11
seat schemes, read from `sims/registry/sims.json` rather than copied here:
63 control rows in all — 21 shared and
42 at the seats — plus 11 XR stick
mappings that come from the same place.

## 2 voice switches, both off

Both voice features are off by default and opt-in, and each carries its own banner stating exactly what leaves the device when it is on. Asking by voice sends captured audio to a speech service run by the browser's vendor, which this bundle neither operates nor can see.

| Switch | Browser API | State | Storage key |
|---|---|---|---|
| **Read the answer aloud** | `window.speechSynthesis with SpeechSynthesisUtterance` | off by default | `tc-guide-voice-out` |
| **Ask the guide by voice** | `SpeechRecognition, or webkitSpeechRecognition where that is the only name offered` | off by default | `tc-guide-voice-in` |

**Asking by voice sends audio off this device.**
Switching it on sends your recorded voice off this device. Chrome and Edge do not recognise speech inside the page - they stream the captured audio to a speech service run by the browser's own vendor, and Safari sends it to its vendor's service in the same way. This bundle neither operates that service, pays for it, nor can see what it receives, keeps or does with it; all that comes back into this page is a line of text, and what happened to the audio is between you and your browser's vendor.

This bundle stores no audio anywhere: nothing is written to this browser's storage, nothing is uploaded by us, and the recognised words are used once to pick a topic and then dropped. Chrome 139 and later can be asked to recognise on the device instead - availableOnDevice() and processLocally - and the guide asks for that wherever it is offered; if the language pack is missing the request fails with language-not-supported, and the guide stops there and says so rather than quietly retrying through the vendor's service.
Where the browser offers neither constructor - Firefox, which ships it disabled, and anything older - the control is absent rather than degraded: nothing here substitutes another service for the one your browser declined to provide.

**Reading an answer aloud is usually local, and not always.**
It is usually local and not always: most speechSynthesis voices are installed on the machine, but some platforms offer network voices, where the text of the answer is sent to the voice vendor to be spoken. Where the voice is a network one, this bundle neither operates nor can see the service that speaks it; SpeechSynthesisVoice.localService is the only thing that says which kind you have, and the guide shows it rather than claiming local.

Nothing is recorded: reading aloud captures no microphone input, stores no audio, and hands the browser only the text of an answer that is already written in this registry. Where the browser exposes no speechSynthesis, or exposes it with no voice for your language, the control is absent rather than degraded, and the answer stays on screen exactly as written.

The guide keeps two things in this browser and nothing else: whether each of the two voice switches is on. No question you ask it, by hand or by voice, is recorded anywhere.

## Hands in a headset: declared, not proved

UNVERIFIED-ON-HARDWARE: no headset has been available to this build, so not one of these gestures has been made by a real hand in a real session. They are declared to be implemented and tested against a MOCKED WebXR session only.

a mocked session reports whatever joint poses the test hands it, which proves the arithmetic - the distances, the hysteresis, the hold timers - and proves nothing whatever about tracking quality, occlusion, latency, or whether a person can comfortably hold the shape.

this table is a contract for the page to implement, not a description of what the page does today: its own XR note lists hand tracking among the things that do not exist in it yet, and this registry does not claim otherwise.

| Gesture | What it does | Joints | Fires at | Releases at | Held for |
|---|---|---|---|---|---|
| **Pinch to select** | select whatever the hand is aimed at - the same pick the left controller trigger already does: a door, an advisor, a station, a crib, a campus plate | 2 | 0.02 m | 0.035 m | 0 ms |
| **Point to move** | walk the rig in the direction the index finger points, at the same speed the left thumb stick is capped at, for as long as the point is held | 8 | 0.09 m | 0.075 m | 120 ms |
| **Open palm to stop** | stop: zero the walk command and let go of every key the hand is holding - the hand's version of taking your hand off the stick, and the one gesture that needs no aim | 6 | 0.09 m | 0.075 m | 250 ms |
| **Palm up to open the guide** | open this guide, on the place you are standing in, without having to find a button - which is the whole point of a helper that is meant to be reachable from anywhere | 8 | 0.09 m | 0.075 m | 500 ms |

The recogniser reads 25 joints of the WebXR hand skeleton and
asks the session for the `hand-tracking` feature.
every distance and angle here is AUTHORED - typed from general practice, not measured against a hand on hardware - and is expected to move once a headset is available to check it against.

no gesture scores anything, unlocks anything or is recorded: the recogniser runs only inside a session that was granted hand tracking, and off entirely otherwise.

## What the guide is not

- **Not advice.** nothing the guide says is a certification, a permit, a code ruling or a substitute for the qualified person on site; where it states a duty it states it as this Academy teaches it, not as any jurisdiction's law.
- **Not scored.** opening the guide changes no score and unlocks nothing: no grader reads guide state, and there is no guide state for one to read.
- **No episode.** nothing is recorded. The guide writes no episode, and the only thing it ever puts in storage is the state of its two voice switches.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
