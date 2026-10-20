/* How the landing browser round splits the sim seats into mocked-session runs,
   and what each seat is expected to reach. MOCKED session in headless Chromium;
   no physical headset. A batch is one browser run: boot, Enter VR once, then
   the seats in turn, inside the 90 s budget at the load the run was measured
   at. The table is data: xr/test_session.mjs checks it against sims/registry
   (every seat once, no unknown seat) and the browser half reads it. */
/* A is measured (two seats completed by the controllers in one run). The other batches are sized from the
   headless reference-run seconds (crane-lift 33, pressure-washer 33, airless-sprayer 30, forklift-run 60,
   excavator-trench 108), so two slow seats cannot share a 90 s run: each batch declares its own budget
   in BATCH_BUDGET_S, and the measured table lives in the lead's State cell, not here. */
export const SEAT_BATCHES = {
  A: ['load-chart', 'scaffold-bay'],
  B: ['crane-lift', 'overhead-crane'],           // one hall (crane operators)
  C: ['pressure-washer', 'airless-sprayer'],     // one hall (painters)
  D: ['weld-bead', 'boom-lift'],
  E: ['forklift-run', 'excavator-trench'],       // one hall (operating engineers)
};
/* the wall-clock budget each batch declares, in seconds (the run's own hard cap; a batch that overruns fails
   by name rather than hanging). A is the default 88 s; a batch that holds a seat whose reference run is 30 s or
   more of simulated time at about 16 to 30 session frames per second declares more. */
export const BATCH_BUDGET_S = { A: 88, B: 150, C: 150, D: 150, E: 190 };
/* what a seat is expected to reach in a batch: 'completion' (the controllers drive
   it to its result panel with a pass) or 'key-state' (verbs and gauges only).
   A seat not listed is expected to complete. */
export const SEAT_EXPECT = { 'excavator-trench': 'key-state' };   // its reference run is 108 simulated seconds, past any budget declared here
export const SEAT_COACH_SECS = 22;
/* the ceiling on the coach's time at one seat; the coach stops at the seat's own result panel, so the cap is
   only ever spent on a seat that does not finish. A seat not listed gets SEAT_COACH_SECS. */
export const SEAT_COACH_CAP_S = { 'crane-lift': 60, 'overhead-crane': 45, 'weld-bead': 40, 'pressure-washer': 55, 'airless-sprayer': 50, 'boom-lift': 50, 'forklift-run': 100, 'excavator-trench': 12 };
