# Contributing training data

A contribution is a `tc-contribution/1` package a learner builds from the
episodes their own device recorded, under a consent statement and a licence
they read first, and keeps as a file: this bundle sends it nowhere.

**The loop.** [Completion-Record](Completion-Record.md) (export your progress) -> [Verify-A-Record](Verify-A-Record.md) (a rep checks it) -> [Contribute](Contribute.md) (share the episodes behind it, if you choose). [Work-Sites](Work-Sites.md) -> [Verify-A-Record](Verify-A-Record.md) for a crew. [Sessions](Sessions.md) and [Compliance-Ledger](Compliance-Ledger.md) read the same files.

## The process, for a learner

1. **Train.** Seat runs, advisor exchanges, crew questions and walkarounds are
   recorded to `tc-training`, localStorage of the built 3D page.
2. **Open [`web/trade_craft_contribute.html`](../web/trade_craft_contribute.html)** and read *Consent*. The statement, verbatim:

   > I share the training episodes in this package, recorded by this device, for the scopes named in consent.scope under the licence named in consent.license. I can withdraw by not sharing the file again; copies already given away are governed by that licence. Nothing in this package names me: it carries scenario ids, control schemes and measured outcomes, and the label or wallet address I chose to attach.

3. **Choose the scopes** you share for - 2 of them:

   - `agent-training` - the episodes may be used to train, evaluate or benchmark a software agent (for example the ml-agents conversion the training pack describes); this bundle has trained none
   - `robot-training` - the episodes may be used to train, evaluate or benchmark a controller for a physical robot; training/ says these are schematic single-machine simulators and no such controller should be trained on them for real equipment, and this bundle has trained none

4. **Accept the licence**: Creative Commons Attribution 4.0 International (`CC-BY-4.0`),
   one licence for every package.
5. **Under *Build the package*, press *Export contribution package*.** The file lands in your downloads.
   With a connected wallet, *Sign this package with the connected wallet* signs its digest and consent scope.
6. **Look at *Where this could go*.** It lists the destinations
   [Protocols](Protocols.md) names - each marked not integrated. Giving the
   file to anyone is your act, not the bundle's.
7. **Anyone can check it offline**: [Verify-A-Record](Verify-A-Record.md).

![The contribute page, `web/trade_craft_contribute.html`](img/process-contribute.png)

*The contribute page, `web/trade_craft_contribute.html`. The learner data in this capture is synthetic, injected by the smoke harness - not a learner's record.*

## Check it offline

On the pack's own fixture package (labelled *fixture - not a learner*):

```text
$ node contrib/verify.mjs contrib/fixture/good.json
ok record.fields: checked 9, failing 0
ok digest: checked 2, failing 0
ok contributor.signature: checked 1, failing 0
ok consent.statement: checked 1, failing 0
ok consent.scope: checked 4, failing 0
ok consent.license: checked 1, failing 0
ok consent.granted_at: checked 1, failing 0
ok episode.kind: checked 6, failing 0
ok episode.fields: checked 107, failing 0
ok episode.t: checked 6, failing 0
ok trace: checked 5, failing 0
ok ids.sim: checked 4, failing 0
ok ids.scenario: checked 3, failing 0
ok ids.hall: checked 6, failing 0
ok ids.campus: checked 6, failing 0
ok dataset.counts: checked 3, failing 0
ok origin.classroom: checked 0, failing 0
ok privacy: checked 0, failing 0
ok ids.env: checked 0, failing 0
ok world.samples: checked 0, failing 0
ok world.outcome: checked 0, failing 0
note trace: training.json enumerates no gauge field names (gauges() is described, not listed), so each trace is held to its sample count and sample keys only; nothing inside gauges is checked
signature: unsigned: this device only
summary: 6 episodes (advisor 1, crew 1, sim 3, walkaround 1), 1 trace(s) attached holding 4 samples, 2 sim(s) covered (airless-sprayer, boom-lift)
a contribution proves what a device recorded and, if signed, which key vouched for it - not who, and not that any agent or robot learned from it; nothing is sent anywhere by this bundle
```

Exit status **0**, captured when this page was built.

## The honest limits

Quoted from the registry at build time, never retyped:

`contrib/registry/contrib.json#honesty.does_not_prove`:

> - who the contributor is: contributor.claimed is a label this device stored, attested by this device only, and nothing checks it - unless a wallet signed, in which case it is the identity of a key, not of a person; a stolen key signs just as well
> - that any agent or robot learned from this package: exporting this file trains nothing by itself: no agent exists in this bundle and none is claimed to, until one is actually trained against this data outside it
> - that the package reached anyone: nothing in this bundle sends it anywhere; the learner keeps the file and hands it over, or does not
> - anything on any blockchain: a wallet signature is computed in the browser and carried in the file; nothing is written to any chain, nothing is anchored, and no one can look it up
> - that the device was honest: a package can be written by hand and will verify if it is internally consistent
> - that the gauges inside a trace sample mean anything: training/ describes them as display-shaped scalars and short labels and enumerates none, so the verifier holds a trace to its count and sample keys only
> - that an advisor, crew role, topic or walkaround point an episode names exists: only seats, scenarios, halls and campuses are resolved
> - that the episodes came from real equipment: every episode comes from SCHEMATIC physics and deterministic rubrics, not a real robot or a real machine: useful for exercising a training pipeline's plumbing and export format, not for training a controller that will run on real equipment.

`contrib/registry/contrib.json#honesty.nothing_sent`:

> nothing is sent anywhere by this bundle: no platform is integrated, no destination is validated, no upload exists. The contribute page writes a file to the learner's own downloads and stops.

`contrib/registry/contrib.json#honesty.no_agent_trained`:

> exporting this file trains nothing by itself: no agent exists in this bundle and none is claimed to, until one is actually trained against this data outside it

`contrib/registry/contrib.json#honesty.anonymous`:

> no name, no email, no biometric or device-identifying data is ever recorded - an episode carries only a scenario id, the control scheme the registry already declares, and the measured outcome.

`contrib/registry/contrib.json#honesty.digest`:

> a digest proves integrity since export, not identity

`contrib/registry/contrib.json#honesty.signature`:

> null unless a wallet signed: this bundle has no key of its own and no server, so an unsigned package is attested by this device only. A signed package carries an EIP-191 personal_sign signature by the connected wallet over this package's digest and consent scope; it proves that the holder of that key signed this digest at export - the identity of a key, not of a person. A signature that does not recover to the address it claims, or that signs any other message, is refused as a forgery. Nothing is written to any chain and nothing is anchored.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
