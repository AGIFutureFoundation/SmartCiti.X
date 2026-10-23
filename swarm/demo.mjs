/* swarm/demo.mjs - route a handful of example commands and print the audit log as JSON lines (node swarm/demo.mjs).
 * Every command is a dry run; the real-hardware example is refused. Reads registries, writes only to stdout. */
import { createRouter } from './router.mjs';

const OAK = [[37.77, -122.30], [37.77, -122.24], [37.83, -122.24], [37.83, -122.30]];
const base = (id, capability, region, extra = {}) => ({ schema: 'swarm-command/1', id, capability, region, ...extra });
const commands = [
  base('demo-1', 'robot.litter-pickup', { polygon: OAK }, { params: { level: 1, seed: 3 } }),
  base('demo-2', 'robot.gate-drive', { polygon: OAK }),
  base('demo-3', 'software.advise-visitor', { cells: ['9q9', 'dr5'] }),
  base('demo-4', 'robot.rov-survey', { polygon: OAK }, { mode: 'live' }),
  base('demo-5', 'robot.litter-sort', { polygon: [[30, -60], [30, -50], [35, -50], [35, -60]] }),
];
const router = createRouter();
for (const c of commands) router.route(c);
process.stdout.write(router.audit.toJSONL());
