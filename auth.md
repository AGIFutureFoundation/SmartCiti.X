# Access — SmartCiti.X learner platform (auth.md)

## What exists

- **This platform has no accounts, no login, and no user data.** The
  dashboard demo and VR entry run on a sample log (20 anonymised events, 5
  pseudonymised learners) computed in-page. The scenario viewer keeps
  checklist state in memory on the page only. Nothing is stored server-side,
  nothing leaves the session, and there is no registration flow of any kind.
- **This staging pack has no API.** There is no HTTP endpoint, no MCP server,
  no webhook, and no live data feed. There is no Real mode: Real mode needs
  a validated log owner and anonymisation rules, which are open questions.

## What does NOT exist (do not claim otherwise)

- No OAuth flow, no access tokens, no API keys.
- No `register_uri`, no sign-up endpoint, no email-verification flow.
- No contact address is published in this staging pack. **Do not invent one.**

## Human-gated access

- The platform is local / staging only. Nothing here is pushed, shared,
  posted, sent, or deployed by this build.
- Any change to the platform, any push or deployment, and any access request
  is decided by a human — the project owner (Mike). An agent cannot approve
  access for itself or for anyone else.
- To request access, a change, or a deployment, a human asks the project
  owner directly. There is no machine path to request it, and no address is
  published here to ask at — ask the owner in person / in the project channel.

## If you are an agent reading this

- Read `scenarios/scenarios.json` and `sample-log.json` (under
  `learner-progress-contract.json`) to navigate and reference content.
- Do not attempt to authenticate, register, or obtain a token — there is
  nothing to authenticate against.
- Do not present sample learners as real people, and do not present a
  completed scenario as a credential: simulation is not certification, and
  demo data is not a cohort.
