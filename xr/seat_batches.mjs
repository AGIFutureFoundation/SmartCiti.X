/* How the landing browser round splits the sim seats into mocked-session runs,
   and what each seat is expected to reach. MOCKED session in headless Chromium;
   no physical headset. A batch is one browser run: boot, Enter VR once, then
   the seats in turn, inside the 90 s budget at the load the run was measured
   at. The table is data: xr/test_session.mjs checks it against sims/registry
   (every seat once, no unknown seat) and the browser half reads it. */
/* A is measured (two seats completed by the controllers in one run, 80 s at load 2.7);
   B onward are sized from the headless reference-run seconds (crane-lift 33, pressure-washer 33,
   airless-sprayer 30, forklift-run 60, excavator-trench 108) and are NOT yet run to completion. */
export const SEAT_BATCHES = {
  A: ['load-chart', 'scaffold-bay'],
  B: ['crane-lift'],
  C: ['overhead-crane', 'weld-bead'],
  D: ['pressure-washer'],
  E: ['airless-sprayer'],
  F: ['boom-lift'],
  G: ['forklift-run'],
  H: ['excavator-trench'],
};
/* what a seat is expected to reach in a batch: 'completion' (the controllers drive
   it to its result panel with a pass) or 'key-state' (verbs and gauges only).
   A seat not listed is expected to complete. */
export const SEAT_EXPECT = { 'excavator-trench': 'key-state' };   // its reference run is 108 simulated seconds, past a 90 s browser run
export const SEAT_COACH_SECS = 22;
