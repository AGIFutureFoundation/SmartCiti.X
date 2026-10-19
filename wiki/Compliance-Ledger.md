# The compliance ledger

The compliance ledger (`compliance/registry/compliance.json`) sets what the
bundle's own registries require of a hall and its rooms beside what a
`tc-completion/1` record can evidence of them. This ledger is not a code reference and cites no jurisdiction: it lists what the bundle's own rules require of a hall and its rooms, and what a tc-completion/1 record can evidence of them. Every number is computed from the stamped inputs; none is typed.

**The loop.** [Completion-Record](Completion-Record.md) (export your progress) -> [Verify-A-Record](Verify-A-Record.md) (a rep checks it) -> [Contribute](Contribute.md) (share the episodes behind it, if you choose). [Work-Sites](Work-Sites.md) -> [Verify-A-Record](Verify-A-Record.md) for a crew. [Sessions](Sessions.md) and [Compliance-Ledger](Compliance-Ledger.md) read the same files.

## The process, for a union rep

1. **Take the learner's completion record** ([Completion-Record](Completion-Record.md)).
2. **Run `node compliance/verify.mjs <record.json>`.** The record is verified by the completion
   verifier first; one that fails stops there.
3. **Read each hall the record touches**: its hazards, every room's required
   protective equipment and placard, the record's lessons step by step, the
   seats, and the hall's sign-off status.
4. **Read the class on every line** - `episode-backed`, `device-mark`, `self-reported`. A walk or placard step is the
   learner's word and is reported as such.
5. **Read the totals line and the last line.** The ledger names no
   jurisdiction; a real deployment brings its own.

## The ledger at this build

111 halls, 63 with hazards;
110 of 110 hazard rooms carry a
placard; 0 halls signed off by a practitioner;
5 halls have a lesson
that walks every hazard room.

## Check it offline

On the completion pack's own fixture record:

```text
$ node compliance/verify.mjs completion/fixture/good.json
compliance report: 3 halls touched by this record (of 111); ledger built 2026-09-26, stamp 8a4ceed33db622e1

hall riggers (Riggers & Signalpersons) — lesson riggers-first-card, seat rigging-signals passed, seat load-chart passed
  hazards: suspended-load; hazard rooms: materials
  room safety [no hazard] PPE: hi-vis, safety boots — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room procedure [no hazard] PPE: gloves, hard hat, hi-vis, safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room machines [no hazard] PPE: gloves, hard hat, hearing protection, hi-vis, safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room tools [no hazard] PPE: safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room materials [hazard suspended-load] PPE: gloves, hard hat, hi-vis, safety boots — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room layout [no hazard] PPE: safety boots — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room inspection [no hazard] PPE: safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room troubleshooting [no hazard] PPE: safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  lesson riggers-first-card: complete in the record; placard step in every hazard room: no; hazard rooms not walked: materials
    step 1 walk @coordination: self-reported (done is the learner's word)
    step 2 advisor @coordination: evidenced
    step 3 walkaround @yard: evidenced
    step 4 sim @yard: evidenced
  lesson riggers-carry-under-control: in progress in the record; placard step in every hazard room: no; hazard rooms not walked: materials
    step 1 walk @machines: not done
    step 2 walkaround @yard: not done
    step 3 crew @yard: not done
    step 4 sim @yard: not done
    step 5 advisor @yard: not done
  lesson f-timber-frame-site-walk: in progress in the record; placard step in every hazard room: no; hazard rooms not walked: materials
    step 1 walk @safety: not done
    step 2 placard @safety: not done
    step 3 advisor @safety: not done
    step 4 advisor @safety: not done
  seat crane-lift: not passed in this record
  seat rigging-signals (Rigging Signal Call): passed — evidenced by record.sims and a sim step episode; decided by the seat's rule: calls == all, wrong == 0, time informational — the axes are the seat's rule in sims.json, not the record's evidence; the record carries passed only
  seat load-chart (Load Chart Judgment): passed — evidenced by record.sims and a sim step episode; decided by the seat's rule: judgments == all, overloads == 0, time informational — the axes are the seat's rule in sims.json, not the record's evidence; the record carries passed only
  seat overhead-crane: not passed in this record
  sign-off: UNSIGNED — this hall's content is unverified general practice (content_status absent: inherits the global caveat) (0 of 111 halls signed off today, read through pack/hall_signoff.mjs) — not-evidenced (a hall's fact, not the record's)

hall crane-ops (Crane Operators) — lesson crane-ops-read-the-chart, seat rigging-signals passed, seat load-chart passed
  hazards: suspended-load; hazard rooms: materials
  room safety [no hazard] PPE: hi-vis, safety boots — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room procedure [no hazard] PPE: gloves, hard hat, hi-vis, safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room machines [no hazard] PPE: gloves, hard hat, hearing protection, hi-vis, safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room tools [no hazard] PPE: safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room materials [hazard suspended-load] PPE: gloves, hard hat, hi-vis, safety boots — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room layout [no hazard] PPE: safety boots — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room inspection [no hazard] PPE: safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room troubleshooting [no hazard] PPE: safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  lesson crane-ops-read-the-chart: complete in the record; placard step in every hazard room: no; hazard rooms not walked: materials
    step 1 walk @machines: self-reported (done is the learner's word)
    step 2 walkaround @yard: evidenced
    step 3 sim @yard: evidenced
    step 4 advisor @yard: evidenced
  lesson d-wind-staging-site-walk: in progress in the record; placard step in every hazard room: no; hazard rooms not walked: materials
    step 1 walk @safety: not done
    step 2 placard @safety: not done
    step 3 advisor @safety: not done
    step 4 advisor @safety: not done
  seat crane-lift: not passed in this record
  seat rigging-signals (Rigging Signal Call): passed — evidenced by record.sims and a sim step episode; decided by the seat's rule: calls == all, wrong == 0, time informational — the axes are the seat's rule in sims.json, not the record's evidence; the record carries passed only
  seat load-chart (Load Chart Judgment): passed — evidenced by record.sims and a sim step episode; decided by the seat's rule: judgments == all, overloads == 0, time informational — the axes are the seat's rule in sims.json, not the record's evidence; the record carries passed only
  seat overhead-crane: not passed in this record
  sign-off: UNSIGNED — this hall's content is unverified general practice (content_status absent: inherits the global caveat) (0 of 111 halls signed off today, read through pack/hall_signoff.mjs) — not-evidenced (a hall's fact, not the record's)

hall scaffold (Scaffold Erectors) — lesson scaffold-read-the-tag
  hazards: work-at-height, timber-trade; hazard rooms: safety, procedure
  room safety [hazard work-at-height] PPE: chinstrap helmet, full-body harness, hi-vis, safety boots — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room procedure [hazard timber-trade+work-at-height] PPE: chinstrap helmet, dust mask, full-body harness, gloves, hard hat, hearing protection, hi-vis, safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room machines [no hazard] PPE: gloves, hard hat, hearing protection, hi-vis, safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room tools [no hazard] PPE: safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room materials [no hazard] PPE: gloves, hard hat, hi-vis, safety boots — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room layout [no hazard] PPE: safety boots — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room inspection [no hazard] PPE: safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  room troubleshooting [no hazard] PPE: safety boots, safety glasses — placard hung — not-evidenced (a room requirement is the bundle's fact; no record field carries it)
  lesson scaffold-read-the-tag: in progress in the record; placard step in every hazard room: no; hazard rooms not walked: procedure
    step 1 walk @safety: self-reported (done is the learner's word)
    step 2 placard @safety: self-reported (done is the learner's word)
    step 3 station @safety: not done
    step 4 walkaround @yard: not done
    step 5 advisor @safety: not done
  lesson scaffold-build-in-order: in progress in the record; placard step in every hazard room: no; hazard rooms not walked: safety, procedure
    step 1 walk @materials: not done
    step 2 placard @materials: not done
    step 3 crew @yard: not done
    step 4 walkaround @yard: not done
    step 5 sim @yard: not done
  seat scaffold-bay: not passed in this record
  sign-off: UNSIGNED — this hall's content is unverified general practice (content_status absent: inherits the global caveat) (0 of 111 halls signed off today, read through pack/hall_signoff.mjs) — not-evidenced (a hall's fact, not the record's)

totals: 10 evidenced, 4 self-reported, 27 not-evidenced items across the halls touched
signature: unsigned: this device only
this report is against the bundle's own rules, not any jurisdiction's; a signed record attests a key, not a person; nothing here is a certification or an inspection
```

Exit status **0**, captured when this page was built.

## The honest limits

Quoted from the registry at build time, never retyped:

`compliance/registry/compliance.json#honesty.is`:

> the bundle's internal compliance ledger: what its own registries require and what its own record format can evidence

`compliance/registry/compliance.json#honesty.is_not`:

> - a code reference
> - a jurisdiction overlay
> - a certification
> - an inspection
> - an accreditation

`compliance/registry/compliance.json#honesty.signoff`:

> no hall's content is signed off by a practitioner today (read through pack/hall_signoff.mjs); every hall inherits the global caveat

`compliance/registry/compliance.json#honesty.signature`:

> a signed record attests a key, not a person (completion.json#signature)

`compliance/registry/compliance.json#honesty.self_reported`:

> a walk or placard step is the learner's word: it cannot be evidenced by any record

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
