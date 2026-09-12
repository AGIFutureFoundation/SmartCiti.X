# The advisors

A hall is a building until somebody in it will answer a question.
**9 advisors** stand in the rooms and on the campus green,
each one of the Academy's own rigged avatars — breathing, turning its head
toward you — and each able to answer exactly **34 questions**
between them.

## What an advisor is

an advisor is a scripted guide, not an instructor and not an AI: no model runs behind one, nothing is generated at view time, no network is reached, and every line an advisor can say is written in this registry or read from another registry in this bundle.

an advisor cannot be asked an open question because it has no way to answer one. The topics below are all of them, and the suite counts them.

## Quote, never copy

a topic is either a `say` - a sentence written in this registry about this bundle's own policy, with the record it comes from named in `cites` - or a `read` - a binding naming the page-data path the answer must be read from at view time. No `read` answer is copied into this registry, so the record it quotes stays the one truth for that fact.

That is why 20 of the 34 topics carry no words
at all. Ask the safety steward what to wear and the answer is the hall's
own condition record; walk into a different hall and the same question
gives a different answer, because the record changed and the advisor did
not. The other 14 are written down, and each one names the
file it was written in.

| Binding | What the page must read |
|---|---|
| `conditions.ppe` | the PPE list on this room's condition record |
| `conditions.hazards` | the hazards this room's condition record carries |
| `conditions.env` | the lux, air changes and noise this room is held to |
| `surface.finish` | the floor finish this room is given, and why |
| `crib.tools` | the tools this district's crib issues |
| `crib.drill` | how the crib check is scored |
| `sim.walkaround` | the pre-shift walkaround points for this hall's seat |
| `sim.rubric` | what the seat at this hall actually measures |
| `seat.task` | the goal of the seat currently running, read live rather than from the hall it happens to have been entered from |
| `seat.controls` | the control scheme of the seat currently running |
| `seat.dash` | the gauges the seat currently running puts on the dash |
| `seat.rubric` | what the seat currently running actually measures |
| `seat.walkaround` | the pre-shift walkaround points for the seat currently running |
| `seat.trade` | every hall that actually trains on the seat currently running, not just the one the learner is standing in |
| `hall.rooms` | the rooms this hall is laid out with |
| `hall.focus` | what this hall is for |
| `campus.districts` | the districts this campus holds |
| `campus.network` | the other campuses and the distance to them |
| `city.anchors` | the recorded places around this campus |
| `city.walk` | which recorded places fall inside a ten- and fifteen-minute walk of this campus |

## Who is standing where

| Advisor | Stands in | Role | Can be asked |
|---|---|---|---|
| 🧭 **Orientation guide** | the hall door | meets you at the door and says what the place is | What is this hall? *(reads hall.focus)*<br>What is laid out in here? *(reads hall.rooms)*<br>Where should I start? *(written here)*<br>How much of this is real? *(written here)* |
| 🦺 **Safety steward** | the safety room | holds the room to its own condition record | What do I need on in here? *(reads conditions.ppe)*<br>What is the hazard here? *(reads conditions.hazards)*<br>Light, air and noise? *(reads conditions.env)*<br>Can I refuse the work? *(written here)* |
| 🧰 **Crib keeper** | the tools room | issues, calibrates and takes back the tools | What is issued out of this crib? *(reads crib.tools)*<br>How is the crib check scored? *(reads crib.drill)*<br>Whose tools are these? *(written here)* |
| 📐 **Layout hand** | the layout room | sets out the work and defends the control points | Why this floor? *(reads surface.finish)*<br>What is a control point? *(written here)*<br>How do I know the line is true? *(written here)* |
| 🔍 **Inspector** | the inspection room | holds the work to the acceptance criteria | What does the seat here measure? *(reads sim.rubric)*<br>Can I talk my way to a pass? *(written here)*<br>Does a pass here certify me? *(written here)* |
| 📋 **Foreman** | the coordination room | runs the shift brief and the hand-offs | What gets walked before a start? *(reads sim.walkaround)*<br>Is the walkaround a gate? *(written here)*<br>What makes a hand-off good? *(written here)* |
| 🗂️ **Records clerk** | the documentation room | keeps the permits, the certificates and the as-builts | Where does my progress go? *(written here)*<br>What does the Academy certify? *(written here)*<br>Who are the school partners? *(written here)* |
| 👷 **Operator** | the running seat's own yard | stands at the machine and walks you through the seat | What am I trying to do here? *(reads seat.task)*<br>What do the controls do? *(reads seat.controls)*<br>What are the gauges telling me? *(reads seat.dash)*<br>What does this seat actually measure? *(reads seat.rubric)*<br>What should I walk before I start? *(reads seat.walkaround)*<br>Who actually trains on this machine? *(reads seat.trade)* |
| 📡 **Dispatcher** | the campus green | sends you to the right campus and the right hall | What does this campus hold? *(reads campus.districts)*<br>Where are the other campuses? *(reads campus.network)*<br>What is around us? *(reads city.anchors)*<br>What can I reach on foot? *(reads city.walk)*<br>Is the campus really here? *(written here)* |

## What an advisor is not

- **Not advice.** nothing an advisor says is a certification, a permit, a code ruling or a substitute for the qualified person on site; where an advisor states a duty it states it as this Academy teaches it, not as any jurisdiction's law.
- **Not scored.** talking to an advisor changes no score and unlocks nothing: no grader reads advisor state, and the suite asserts it by reading the graders.
- **Not a person.** an advisor represents no real worker, steward, instructor or union officer, and no real union local is named: the figures are the Academy's own schematic avatars wearing the Academy's own crew marks.

## On foot

The dispatcher answers *"what can I reach on foot?"* against bands that
were not invented here: **800 m** for ten
minutes and **1200 m** for fifteen,
recorded - locator.x src/walk.js, apache-2.0, cross-checked against that checkout on
every build. The six destination classes a walkable measure has to count
travel with them: Shops & everyday errands, Eating & drinking, Workplaces, Health & care, Learning, Lodging & mixed use.

The caveats travel with them too, because without them the number lies:

- this is not Walk Score(R) and no relationship with it is claimed or implied.
- distance here is straight-line between coordinates, not a street-network walk: a freeway, a rail cut, a canal or a gated block makes the real walk longer, sometimes impossibly longer. Walk the block before you believe the number.
- the Academy draws the bands around a campus and reports which RECORDED anchors fall inside them. It counts no shops, because this bundle holds no shop records - the classes above are carried so the map can say what a walkable measure would have to count.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
