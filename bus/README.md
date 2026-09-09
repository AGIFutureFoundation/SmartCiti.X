# SmartCiti.X : Trade Craft Academy — Message Bus & Telemetry

ACP-01, ACP-08 and ACP-09 as running code: the event envelope, the bus that
binds the agents, and the audit log the "Why this?" surface reads from.

```
bus.mjs         ACP-09  topics, single-writer enforcement, dedupe, dispatch
telemetry.mjs   ACP-01  envelope, signal extraction, quality guards, xAPI egress
audit.mjs       ACP-08  append-only decision and override log
safeguards.mjs  ACP-08  parity monitor, stop conditions, override manager
session.mjs             the whole loop assembled over the bus
test.mjs                12 contract checks
test_safeguards.mjs     15 safeguard checks
```

```bash
node test.mjs
node test_safeguards.mjs
```

## Why this exists

Until this pack, every component called every other component's methods
directly. That meant the spec's two load-bearing rules — **single writer per
aggregate** and **every adaptation on the audit log** — were documented but not
enforced. A mentor could not write dial state only because nobody had written
the line of code that would.

Now the bus refuses. Each topic has exactly one permitted publisher, components
are handed a publisher bound to their own role, and a mentor attempting
`dial.setpoint` is rejected whether it asks politely or its model simply decides
to. The console has a button that makes a mentor genuinely try, so you can watch
the refusal rather than take it on trust.

## The guards that earn their keep

**At-least-once means dedupe.** The transport the spec assumes redelivers, so
the bus dedupes on `event_id` and *counts* duplicates rather than hiding them.

**A skewed client clock must not reorder history.** Past two minutes of skew the
server's receipt time is the one trusted, and the envelope records which was
used (`ts_source`).

**Silence is not evidence.** A window with fewer than three usable events
produces no profile update at all — it returns the reason instead.

**A failing subscriber must not take down its siblings.** Handler exceptions are
contained, counted, and audited; the other subscribers still receive the message.

**Rejected telemetry is visible.** A malformed event that the profile guard
refuses lands on the audit log, so a broken client shows up in the record rather
than quietly doing nothing.

## The audit log is one log

The learner's "Why this?" and the compliance record read the same rows, so an
explanation shown to a person and a record shown to a regulator cannot disagree.
Entries are frozen and `entries()` hands out a copy — history cannot be rewritten
by a caller that happens to hold a reference.

## xAPI egress

`toXapi()` maps an envelope to an xAPI 1.0.3 statement. It is an adapter on the
end of the same pipeline, not a second pipeline — and it deliberately carries no
affect data, per ACP-08's rule that affect labels never reach an export.

## What is not here

No network transport, persistence or retry policy: this is the in-process
contract layer, and a real deployment puts a broker underneath it. The topic
list and single-writer table are the part that must survive that move unchanged.

## Safeguards (ACP-08)

Everything in `safeguards.mjs` refuses rather than warns — a safeguard that only
logs is a log.

**Parity.** A relative cohort disparity above 10% opens a ticket and blocks
promotions. Cohorts under n=20 are noise, so the alarm stays worth listening to.
The monitor also fingerprints the dial parameters each cohort is served, and
flags `parity.masking_suspected` when a disparity is open *while cohorts sit on
different settings* — without that record, "we fixed the metric" and "we hid the
metric" look identical afterwards.

**Stop conditions.** Calibration drift across many items, a cohort stuck in
`SUPPORT`, or a parity job that failed to run — any of these halts adaptation and
serves fixed difficulty. The last one means the system will not keep adapting
unwatched.

**Overrides.** Instructors pin; learners get "easier today" twice a week, granted
without question and declined kindly when spent. Pinned episodes weigh 0.3,
because overridden evidence is biased. Precedence is tested: a pin beats the
dial, a stop condition beats the pin.
