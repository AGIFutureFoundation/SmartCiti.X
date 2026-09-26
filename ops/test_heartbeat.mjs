/** ACP-13 §21.4 — heartbeats: silence becomes a signal, and a silent safety-critical component halts. */
import { HeartbeatMonitor, HeartbeatError, KINDS, monitorScheduler, DEFAULT_GRACE_MS } from './heartbeat.mjs';
import { Scheduler, JOBS, CADENCE } from './jobs.mjs';
import { AuditLog } from '../bus/audit.mjs';

let n = 0;
const ok = (label, cond) => { if (!cond) { console.error('FAIL', label); process.exit(1); } n++; console.log('  ok ', label); };
const throws = (fn, re) => { try { fn(); return false; } catch (e) { return re.test(String(e.message)); } };

/* ------------------------------------------------------------ registration */
{
  const m = new HeartbeatMonitor();
  ok('a component registers with a kind and the interval it promises to beat on',
    m.register('mentor:joyce@1.2.0', { kind: 'mentor', intervalMs: 10_000 }) === 'never');
  ok('registering is not a beat: a component that has never reported is "never", not "alive"',
    m.status('mentor:joyce@1.2.0') === 'never');
  ok('an unknown kind is refused', throws(() => m.register('x', { kind: 'thing', intervalMs: 1 }), /unknown kind/));
  ok('a non-positive interval is refused', throws(() => m.register('x', { kind: 'crew', intervalMs: 0 }), /positive/));
  ok('registering the same id twice is refused rather than silently resetting its history',
    throws(() => m.register('mentor:joyce@1.2.0', { kind: 'mentor', intervalMs: 1 }), /already monitored/));
  ok('a beat from a component nobody registered is refused: an unknown "alive" is not evidence',
    throws(() => m.beat('ghost'), /not monitored/));
  ok('every kind the spec names is monitorable', ['job', 'mentor', 'crew', 'station', 'service'].every((k) => KINDS.includes(k)));
}

/* ------------------------------------------------------- alive and stale --- */
{
  const audit = new AuditLog();
  const m = new HeartbeatMonitor({ audit, grace: 1_000 });
  m.register('station:oakland-weld-bay', { kind: 'station', intervalMs: 10_000 });
  m.beat('station:oakland-weld-bay');
  ok('a beat makes a component alive', m.status('station:oakland-weld-bay') === 'alive');
  ok('within its window nothing is stale', m.sweep(10_500).length === 0 && m.status('station:oakland-weld-bay') === 'alive');
  const stale = m.sweep(1_000);
  ok('one ms past interval + grace the component is stale, and the sweep returns exactly what changed',
    stale.length === 1 && stale[0].id === 'station:oakland-weld-bay' && m.status('station:oakland-weld-bay') === 'stale');
  ok('the lapse says how long the silence has been and what was promised',
    /last beat 11500 ms ago, interval 10000 ms/.test(stale[0].why));
  ok('a second sweep does not re-report the same lapse: one outage is one record',
    m.sweep(60_000).length === 0 && audit.entries({ action: 'heartbeat.stale' }).length === 1);
  m.beat('station:oakland-weld-bay');
  ok('a beat closes the lapse and is audited as a recovery with the silence measured',
    m.status('station:oakland-weld-bay') === 'alive'
    && /beating again after 71500 ms/.test(audit.entries({ action: 'heartbeat.recovered' })[0].why));
  ok('the record counts beats and lapses for the board', m.board()[0].beats === 2 && m.board()[0].lapses === 1);
  ok('a beat from the past cannot rewind the record',
    m.beat('station:oakland-weld-bay', 5).ok === false && m.board()[0].lastBeat === m.clock);
}

/* --------------------------------------------- never reported goes stale --- */
{
  const audit = new AuditLog();
  const m = new HeartbeatMonitor({ audit });
  m.register('crew:oakland-a', { kind: 'crew', intervalMs: 5_000 });
  m.sweep(5_000 + DEFAULT_GRACE_MS + 1);
  ok('a component that registered and never reported goes stale too, and the record says so',
    m.status('crew:oakland-a') === 'stale' && /registered and never reported/.test(m.lapses[0].why));
}

/* ----------------------------------------- safety-critical lapse halts ---- */
{
  const audit = new AuditLog();
  const halts = [];
  const m = new HeartbeatMonitor({ audit, grace: 0, onStale: (l) => halts.push(l.id) });
  m.register('service:dial', { kind: 'service', intervalMs: 1_000, safetyCritical: true });
  m.register('mentor:sam@1.0.0', { kind: 'mentor', intervalMs: 1_000 });
  m.beat('service:dial'); m.beat('mentor:sam@1.0.0');
  m.sweep(1_001);
  ok('a silent safety-critical component reaches the halt hook; a silent mentor does not',
    halts.length === 1 && halts[0] === 'service:dial' && m.anyCriticalStale());
  ok('the audit row carries the safety flag so a reader can tell the two lapses apart',
    audit.entries({ action: 'heartbeat.stale' }).map((e) => e.after.safetyCritical).join() === 'true,false');
  m.beat('service:dial');
  ok('once the critical component beats, the board is no longer critically stale', !m.anyCriticalStale());
}

{
  const audit = new AuditLog();
  const m = new HeartbeatMonitor({ audit, grace: 0, onStale: () => { throw new Error('hook broke'); } });
  m.register('service:dial', { kind: 'service', intervalMs: 1, safetyCritical: true });
  m.register('service:lpa', { kind: 'service', intervalMs: 1, safetyCritical: true });
  const stale = m.sweep(2);
  ok('a throwing halt hook is contained and audited, and the sweep still finds the next silent component',
    stale.length === 2 && audit.entries({ action: 'heartbeat.hook_failed' }).length === 2);
}

/* ------------------------------------------------ the scheduler beats ----- */
{
  const audit = new AuditLog();
  const halts = [];
  const m = new HeartbeatMonitor({ audit, grace: 0, onStale: (l) => halts.push(l.id) });
  const s = monitorScheduler(new Scheduler({ audit }), m, { jobs: JOBS, cadence: CADENCE });
  ok('every ACP-13 job is on the board, and only the parity job is safety-critical',
    m.byKind('job').length === JOBS.length
    && m.byKind('job').filter((r) => r.safetyCritical).map((r) => r.id).join() === 'job:parity_job');
  for (const j of JOBS) s.on(j.name, () => 'ran');
  s.tick(0);
  ok('a job that ran beats: the first tick leaves every job alive',
    m.byKind('job').every((r) => r.status === 'alive'));
  s.tick(CADENCE.weekly);
  ok('a scheduler that keeps running its jobs keeps every job alive a week later',
    m.byKind('job').every((r) => r.status === 'alive') && halts.length === 0);

  const audit2 = new AuditLog();
  const halts2 = [];
  const m2 = new HeartbeatMonitor({ audit: audit2, grace: 0, onStale: (l) => halts2.push(l.id) });
  const s2 = monitorScheduler(new Scheduler({ audit: audit2 }), m2, { jobs: JOBS, cadence: CADENCE });
  for (const j of JOBS) if (j.name !== 'parity_job') s2.on(j.name, () => 'ran');
  s2.tick(0);
  s2.tick(CADENCE.weekly + 1);
  ok('a scheduler that never runs the parity job turns it stale and halts, on top of the "no handler" audit the loop already writes',
    m2.status('job:parity_job') === 'stale' && halts2.join() === 'job:parity_job'
    && audit2.entries({ action: 'job.missing' }).length >= 1);
  const s3audit = new AuditLog();
  const m3 = new HeartbeatMonitor({ audit: s3audit, grace: 0 });
  const s3 = monitorScheduler(new Scheduler({ audit: s3audit }), m3, { jobs: JOBS, cadence: CADENCE });
  for (const j of JOBS) s3.on(j.name, j.name === 'parity_job' ? () => { throw new Error('cohorts unavailable'); } : () => 'ran');
  s3.tick(0);
  s3.tick(CADENCE.weekly + 1);
  ok('a job that runs but throws does not beat: failing is not the same as alive',
    m3.status('job:parity_job') === 'stale');
}

console.log(`${n} checks passed`);
