/* datashare/node_shell.mjs - the node shell both CLIs share: the registry, node's sha256, the contrib
   verifier (contrib/verify.mjs, the same rules the page and the Worker run) and the core. No network. */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { datashareCore } from './core.mjs';
import { verify } from '../contrib/verify.mjs';

export const CFG = JSON.parse(readFileSync(new URL('./registry/datashare.json', import.meta.url), 'utf8'));
export const sha256hex = async (s) => createHash('sha256').update(Buffer.from(s, 'utf8')).digest('hex');
export const CORE = datashareCore(CFG, sha256hex);

/* the verdict the core takes: ok, or the first failing contrib rule and its first message */
export function verdictOf(record) {
  try {
    const r = verify(record);
    for (const [rule, t] of Object.entries(r.tally)) if (t.fails.length) return { ok: false, rule, detail: t.fails[0] };
    return { ok: true, rule: null, detail: '' };
  } catch (e) {
    return { ok: false, rule: 'record.fields', detail: String(e && e.message) };
  }
}
