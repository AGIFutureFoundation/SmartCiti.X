# Work sites

A work site is a declared job where a crew drawn from at least two unions
works with hand-offs, and its completion is checked offline from each
member's own exported records - 8 sites, 28 roles,
44 hand-offs, 16 unions.

**The loop.** [Completion-Record](Completion-Record.md) (export your progress) -> [Verify-A-Record](Verify-A-Record.md) (a rep checks it) -> [Contribute](Contribute.md) (share the episodes behind it, if you choose). [Work-Sites](Work-Sites.md) -> [Verify-A-Record](Verify-A-Record.md) for a crew. [Sessions](Sessions.md) and [Compliance-Ledger](Compliance-Ledger.md) read the same files.

## The process, for a crew and its rep

1. **Open [`web/trade_craft_worksites.html`](../web/trade_craft_worksites.html)** and pick a site. Each names its job, its
   place, its roles and the hand-offs in order, with the evidence at each end.
2. **Each member takes one role** and works it alone, on their own device:
   the seat, walkaround, crew question or station that role's evidence names.
3. **Each member exports their own file** -
   [Completion-Record](Completion-Record.md) and/or
   [Contribute](Contribute.md) - and gives it to the rep.
4. **The rep runs the site verifier** with the site id and every member's
   file (below; see also [Verify-A-Record](Verify-A-Record.md)). Each file
   must first verify under its own pack's verifier.
5. **Read the tallies**: roles covered, hand-offs in order (by the episodes'
   own timestamps), and identities attested - an unsigned file is a label,
   and the verifier says so on every line.

![The work sites page, `web/trade_craft_worksites.html`](img/process-worksites.png)

*The work sites page, `web/trade_craft_worksites.html`.*

## The 8 sites

| Site | id | Place | Roles | Hand-offs | Unions |
|---|---|---|---|---|---|
| **Shoreline drainage cut, Heron's Head** | `herons-head-shoreline-cut` | restoration-site | 4 | 6 | Laborers, Operating Engineers |
| **Tank seam entry, New Orleans** | `nola-tank-entry` | campus | 3 | 5 | Boilermakers, Tank Erectors, Welding Trades |
| **Blind pick between the container stacks, Oakland** | `oak-terminal-blind-pick` | campus | 4 | 6 | Port Crane Technicians, Riggers & Signalpersons, Steel Erectors |
| **Levee toe trench, South Bay salt ponds** | `salt-ponds-levee-trench` | restoration-site | 4 | 6 | Construction Surveyors, Laborers, Operating Engineers, Shoring & Underpinning |
| **Curtainwall run under the line, Treasure Island** | `ti-curtainwall-boom-run` | campus | 3 | 5 | Electrical Workers, Glaziers |
| **One bay up and tagged, scaffold court** | `ti-scaffold-court-bay` | space | 3 | 5 | Laborers, Scaffold Erectors |
| **Tower steel pick, crane simulator bay** | `ti-tower-steel-pick` | space | 4 | 6 | Crane Operators, Ironworkers, Riggers & Signalpersons |
| **Deck seam under permit, welding bay** | `ti-welding-bay-hot-work` | space | 3 | 5 | Boilermakers, Structural Fabricators, Welding Trades |

### The fixture's site: Tower steel pick, crane simulator bay

| Role | Name | Union | Job |
|---|---|---|---|
| `lift-director` | Lift director | Ironworkers | owns the lift plan and is the only voice that changes it |
| `crane-operator` | Crane operator | Crane Operators | runs the machine and takes moves from one set of hands only |
| `signalperson` | Signalperson | Riggers & Signalpersons | gives the crane its moves and owns the path the load travels |
| `rigger` | Rigger | Riggers & Signalpersons | chooses and makes the hitch, and knows what the load weighs |

## Check it offline

On the pack's own fixture crew (*fixture crew A..D - not learners; four labels because four records, not four people*):

```text
$ node worksites/verify.mjs ti-tower-steel-pick worksites/fixture/good/*.json
site ti-tower-steel-pick: Tower steel pick, crane simulator bay - Crane lift crew at space crane-sim-bay
ok record member-a-lift-director.json: tc-contribution/1 verifies; unsigned, identity not attested
ok record member-b-rigger-completion.json: tc-completion/1 verifies; unsigned, identity not attested
ok record member-b-rigger.json: tc-contribution/1 verifies; unsigned, identity not attested
ok record member-c-signalperson.json: tc-contribution/1 verifies; unsigned, identity not attested
ok record member-d-crane-operator.json: tc-contribution/1 verifies; unsigned, identity not attested
ok role lift-director (Lift director, ironworkers): held by fixture crew A - not a learner - identity not attested; evidence: crew crane-lift-crew:lift-director asked "plan"; crew crane-lift-crew:lift-director asked "change"
ok role crane-operator (Crane operator, crane-ops): held by fixture crew D - not a learner - identity not attested; evidence: sim crane-lift/bay-steel passed
ok role signalperson (Signalperson, riggers): held by fixture crew C - not a learner - identity not attested; evidence: walkaround rigging-signals#sightline; sim rigging-signals/bay-first-card passed; walkaround rigging-signals#path
ok role rigger (Rigger, riggers): held by fixture crew B - not a learner - identity not attested; evidence: sim load-chart/bay-pick-list passed; crew crane-lift-crew:rigger asked "weight"
ok handoff 1 lift-director->rigger: crew crane-lift-crew:lift-director asked "plan" at 2026-09-26T03:00:00.000Z (fixture crew A - not a learner) -> sim load-chart/bay-pick-list passed at 2026-09-26T03:00:01.000Z (fixture crew B - not a learner)
ok handoff 2 rigger->signalperson: sim load-chart/bay-pick-list passed at 2026-09-26T03:00:01.000Z (fixture crew B - not a learner) -> walkaround rigging-signals#sightline at 2026-09-26T03:00:02.000Z (fixture crew C - not a learner)
ok handoff 3 signalperson->crane-operator: sim rigging-signals/bay-first-card passed at 2026-09-26T03:00:03.000Z (fixture crew C - not a learner) -> sim crane-lift/bay-steel passed at 2026-09-26T03:00:04.000Z (fixture crew D - not a learner)
ok handoff 4 crane-operator->signalperson: sim crane-lift/bay-steel passed at 2026-09-26T03:00:04.000Z (fixture crew D - not a learner) -> walkaround rigging-signals#path at 2026-09-26T03:00:05.000Z (fixture crew C - not a learner)
ok handoff 5 signalperson->rigger: walkaround rigging-signals#path at 2026-09-26T03:00:05.000Z (fixture crew C - not a learner) -> crew crane-lift-crew:rigger asked "weight" at 2026-09-26T03:00:07.000Z (fixture crew B - not a learner)
ok handoff 6 rigger->lift-director: crew crane-lift-crew:rigger asked "weight" at 2026-09-26T03:00:07.000Z (fixture crew B - not a learner) -> crew crane-lift-crew:lift-director asked "change" at 2026-09-26T03:00:09.000Z (fixture crew A - not a learner)
roles covered 4 of 4
handoffs in order 6 of 6
identities attested 0 of 4
records read 5 under 4 identities
crew completion: complete
a crew completion proves that N records, each internally consistent, together cover the roles and the order; not that these people stood on one site at one time; nothing here is a certification
```

Exit status **0**, captured when this page was built.

## The honest limits

Quoted from the registry at build time, never retyped:

`worksites/registry/worksites.json#honesty.authored`:

> these are AUTHORED scenarios, hand-written and validated against the registries; none is a record of a job anyone ran

`worksites/registry/worksites.json#honesty.no_multi_user`:

> no two learners have ever been on a site together here: this bundle has no multi-user session, no shared world state and no server. A crew completion is N separate records, each made alone on its own device, read side by side

`worksites/registry/worksites.json#honesty.not_a_certification`:

> a crew completion proves that N records, each internally consistent, together cover the roles and the order; not that these people stood on one site at one time; nothing here is a certification

`worksites/registry/worksites.json#honesty.unverified`:

> the roles, the hand-offs and the stop conditions written here are unverified general practice, pending authoring by journey-level practitioners of each trade. Where a role is marked commonly-required that is a statement about widespread practice as this Academy understands it, not a reading of any jurisdiction's rule, and every distance, period and threshold a role mentions is deliberately left to the reader's own jurisdiction rather than given a number here.

`worksites/registry/worksites.json#honesty.not_a_permit`:

> nothing a crew role says is a permit, an entry authorisation, a tag, a certificate or a code ruling. The permits, tags and authorisations named here are the names of real artefacts, and this bundle issues none of them and stands in for none of them.

`worksites/registry/worksites.json#honesty.not_stated`:

> no duration and no price is stated anywhere in this registry

`worksites/registry/worksites.json#honesty.ppe`:

> never typed: derived from surfaces/ for a custom space's finishes; a campus or a restoration site has no finishes here and the registry says so

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
