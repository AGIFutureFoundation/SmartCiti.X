// City-life ledger core (PLAY COINS only - not money). Pure: storage and registry are injected.
// The block between the markers is carried byte-for-byte into pages by web/econkit.py.
/* ECON_CORE:BEGIN */
const ECON_KEY = 'tc-econ-v1';
function econFresh(R) { return { v: 1, coins: R.rules.start_balance, day: 0, lots: {}, skills: {}, flags: {}, log: [] }; }
function econValid(s) {
  return !!s && s.v === 1 && Number.isInteger(s.coins) && s.coins >= 0 && Number.isInteger(s.day) &&
    typeof s.lots === 'object' && typeof s.skills === 'object' && typeof s.flags === 'object' && Array.isArray(s.log);
}
function econLoad(storage, R) {
  try {
    if (!storage) return { s: econFresh(R), saved: false };
    const raw = storage.getItem(ECON_KEY);
    if (!raw) return { s: econFresh(R), saved: true };
    const s = JSON.parse(raw);
    return { s: econValid(s) ? s : econFresh(R), saved: true };
  } catch (e) { return { s: econFresh(R), saved: false }; }
}
function econSave(storage, s) {
  try { if (!storage) return false; storage.setItem(ECON_KEY, JSON.stringify(s)); return true; } catch (e) { return false; }
}
function econClear(storage) { try { if (storage) storage.removeItem(ECON_KEY); return true; } catch (e) { return false; } }
function econNote(s, text) { s.log.push({ day: s.day, text: text }); if (s.log.length > 40) s.log.splice(0, s.log.length - 40); }
function econCharge(s, amt, why) {
  if (!Number.isInteger(amt) || amt < 0) throw new Error('econ: bad amount ' + amt);
  if (s.coins < amt) return { ok: false, reason: 'insufficient', need: amt, have: s.coins, why: why };
  s.coins -= amt; econNote(s, '-' + amt + ' ' + why); return { ok: true };
}
function econCredit(s, amt, why) {
  if (!Number.isInteger(amt) || amt < 0) throw new Error('econ: bad amount ' + amt);
  s.coins += amt; econNote(s, '+' + amt + ' ' + why); return { ok: true };
}
function econLot(R, id) { const l = R.lots[id]; if (!l) throw new Error('econ: unknown lot ' + id); return l; }
function econRefuse(r) { return { ok: false, events: [['refused', { reason: r.reason || r, need: r.need, have: r.have }]] }; }
function econRentFirst(s, lotId, lot, ev) {
  ev.push(['rent-paid', { lotId: lotId, day: s.day, coins: lot.rent_coins_per_day }]);
  if (!s.flags.firstRent) { s.flags.firstRent = s.day + 1; ev.push(['first-rent-paid', { lotId: lotId, day: s.day }]); }
}
function econRent(s, R, lotId) {
  const lot = econLot(R, lotId);
  if (s.lots[lotId]) return econRefuse('taken');
  const c = econCharge(s, lot.rent_coins_per_day, 'rent ' + lotId);
  if (!c.ok) return econRefuse(c);
  s.lots[lotId] = { mode: 'rent', since: s.day, business: null, staff: 0, unpaid: 0 };
  const ev = [['lot-rented', { lotId: lotId, parish: lot.parish }]];
  econRentFirst(s, lotId, lot, ev);
  return { ok: true, events: ev };
}
function econBuy(s, R, lotId) {
  const lot = econLot(R, lotId);
  const cur = s.lots[lotId];
  if (cur && cur.mode === 'own') return econRefuse('owned');
  const c = econCharge(s, lot.buy_coins, 'buy ' + lotId);
  if (!c.ok) return econRefuse(c);
  s.lots[lotId] = cur ? Object.assign(cur, { mode: 'own', unpaid: 0 }) : { mode: 'own', since: s.day, business: null, staff: 0, unpaid: 0 };
  return { ok: true, events: [['lot-bought', { lotId: lotId, parish: lot.parish }]] };
}
function econOpen(s, R, lotId, typeId) {
  const lot = econLot(R, lotId); const L = s.lots[lotId]; const bt = R.btypes[typeId];
  if (!bt) throw new Error('econ: unknown business ' + typeId);
  if (!L) return econRefuse('not-yours');
  if (L.business) return econRefuse('has-business');
  if (lot.allowed.indexOf('shop') < 0 || bt.zone !== lot.zone) return econRefuse('wrong-zone');
  const c = econCharge(s, bt.setup_coins, 'open ' + typeId);
  if (!c.ok) return econRefuse(c);
  L.business = typeId;
  const ev = [['shop-opened', { lotId: lotId, businessType: typeId, tradeId: bt.trade_id }]];
  if (!s.flags.firstShop) { s.flags.firstShop = s.day + 1; ev.push(['first-shop-opened', { lotId: lotId, businessType: typeId }]); }
  return { ok: true, events: ev };
}
function econHire(s, R, lotId) {
  const L = s.lots[lotId];
  if (!L || !L.business) return econRefuse('no-business');
  const bt = R.btypes[L.business];
  if (L.staff >= bt.max_staff) return econRefuse('full');
  L.staff += 1; econNote(s, 'hired staff ' + lotId);
  return { ok: true, events: [['staff-hired', { lotId: lotId, count: L.staff }]] };
}
function econTick(s, R, n) {
  const ev = [];
  for (let k = 0; k < (n || 1); k++) {
    for (const id of Object.keys(s.lots).sort()) {
      const L = s.lots[id]; const lot = econLot(R, id);
      if (L.business) {
        const bt = R.btypes[L.business];
        const skilled = bt.trade_id === null || !!s.skills[bt.trade_id];
        econCredit(s, (skilled ? bt.income_coins_per_day_skilled : bt.income_coins_per_day_unskilled) + L.staff * bt.staff_bonus_coins_per_day, 'income ' + id);
        if (L.staff > 0 && !econCharge(s, L.staff * bt.staff_wage_coins_per_day, 'wages ' + id).ok) {
          ev.push(['staff-left', { lotId: id, count: L.staff }]); L.staff = 0;
        }
      }
      if (L.mode === 'rent') {
        if (econCharge(s, lot.rent_coins_per_day, 'rent ' + id).ok) { L.unpaid = 0; econRentFirst(s, id, lot, ev); }
        else {
          L.unpaid += 1; ev.push(['rent-missed', { lotId: id, unpaid: L.unpaid }]);
          if (L.unpaid >= R.rules.eviction_after_unpaid_days) { delete s.lots[id]; econNote(s, 'released ' + id); ev.push(['lot-released', { lotId: id }]); }
        }
      }
    }
    s.day += 1; ev.push(['day', { day: s.day, coins: s.coins }]);
  }
  return { ok: true, events: ev };
}
function econPractice(s, R, tradeId) {
  if (!R.trades[tradeId]) throw new Error('econ: unknown trade ' + tradeId);
  const t = econTick(s, R, R.rules.practice_days);
  const fresh = !s.skills[tradeId];
  s.skills[tradeId] = true;
  if (fresh) t.events.push(['skill-unlocked', { tradeId: tradeId }]);
  return t;
}
function econNear(R, parish, x, z, radius) {
  const out = [];
  for (const id of R.byParish[parish] || []) {
    const l = R.lots[id]; const d = Math.hypot(l.x - x, l.z - z);
    if (d <= radius) out.push({ id: id, d: Math.round(d) });
  }
  return out.sort(function (a, b) { return a.d - b.d || (a.id < b.id ? -1 : 1); });
}
function econIndex(reg) {
  const R = { rules: reg.coin_rules, lots: {}, byParish: {}, btypes: {}, trades: {} };
  for (const f of Object.keys(reg.parishes)) {
    R.byParish[f] = [];
    for (const l of reg.parishes[f].lots) { R.lots[l.id] = l; R.byParish[f].push(l.id); }
  }
  for (const b of reg.business_types) { R.btypes[b.id] = b; if (b.trade_id) R.trades[b.trade_id] = b.label; }
  return R;
}
/* ECON_CORE:END */
export { ECON_KEY, econFresh, econValid, econLoad, econSave, econClear, econCharge, econCredit, econRent, econBuy, econOpen, econHire, econTick, econPractice, econNear, econIndex };
