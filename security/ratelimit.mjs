/**
 * Rate limiting and abuse control.
 *
 * Three separate buckets because they protect different things:
 *   - auth attempts   — protects accounts (brute force), strictest
 *   - agent turns     — protects the budget (an LLM call costs money)
 *   - general API     — protects the service
 *
 * A shared bucket lets a cheap flood exhaust the allowance that an expensive
 * operation needed. They are kept apart on purpose.
 */

export const BUCKETS = Object.freeze({
  auth:   { capacity: 5,    refillPerSec: 5 / 300 },   // 5 per 5 minutes
  agent:  { capacity: 30,   refillPerSec: 30 / 3600 }, // 30 mentor turns/hour
  api:    { capacity: 120,  refillPerSec: 2 },         // 120 burst, 2/sec sustained
  export: { capacity: 3,    refillPerSec: 3 / 86400 }, // 3 bulk exports/day
});

export class RateLimiter {
  constructor({ audit = null, now = () => Date.now() } = {}) {
    this.audit = audit;
    this.now = now;
    this.state = new Map();          // `${bucket}:${key}` -> {tokens, ts}
    this.blocked = 0;
  }

  /**
   * @returns {{allow:boolean, retryAfterSec:number, remaining:number}}
   */
  take(bucket, key, cost = 1) {
    const cfg = BUCKETS[bucket];
    if (!cfg) throw new Error(`unknown rate-limit bucket "${bucket}"`);
    const id = `${bucket}:${key}`;
    const t = this.now();
    let s = this.state.get(id);
    if (!s) { s = { tokens: cfg.capacity, ts: t }; this.state.set(id, s); }

    // refill
    const elapsed = Math.max(0, (t - s.ts) / 1000);
    s.tokens = Math.min(cfg.capacity, s.tokens + elapsed * cfg.refillPerSec);
    s.ts = t;

    if (s.tokens < cost) {
      this.blocked++;
      const need = cost - s.tokens;
      const retryAfterSec = Math.ceil(need / cfg.refillPerSec);
      // Auth throttling is security-relevant and belongs on the record.
      if (bucket === 'auth') {
        this.audit?.append({ actor: String(key), action: 'ratelimit.auth_throttled',
          why: 'too many authentication attempts', after: { retryAfterSec } });
      }
      return { allow: false, retryAfterSec, remaining: 0 };
    }
    s.tokens -= cost;
    return { allow: true, retryAfterSec: 0, remaining: Math.floor(s.tokens) };
  }

  /** Drop idle buckets so memory does not grow with every key ever seen. */
  sweep(maxIdleSec = 3600) {
    const t = this.now();
    let dropped = 0;
    for (const [id, s] of this.state) {
      if ((t - s.ts) / 1000 > maxIdleSec) { this.state.delete(id); dropped++; }
    }
    return dropped;
  }
}
