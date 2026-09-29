// node economy/test.mjs - deterministic checks of the city-life economy (play coins only - not money).
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import * as E from './core.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const rd = (p) => readFileSync(path.join(ROOT, p), 'utf8');
let fails = 0, n = 0;
function check(name, cond, info) { n++; if (cond) console.log('  ok ' + name); else { fails++; console.log('FAIL ' + name + (info ? ' :: ' + info : '')); } }

const regRaw = rd('economy/registry/economy.json');
const reg = JSON.parse(regRaw);
const P = JSON.parse(rd('parishes/registry/parishes.json'));
const U = JSON.parse(rd('unions/registry/unions.json'));
const LOCS = ['en', 'es', 'fr', 'de', 'pt', 'zh', 'hi', 'ar'];

// ---------- registry rules
check('registry.stamp', reg.pack === 'economy' && /^[0-9a-f]{16}$/.test(reg.source_stamp) && reg.source_stamp_sha256.startsWith(reg.source_stamp));
const CUR = /[$€£¥₹₩₽¢]|\b(USD|EUR|GBP|dollars?|cents?|euros?)\b/i;
check('registry.no_currency', !CUR.test(regRaw), (regRaw.match(CUR) || [''])[0]);
check('registry.coin_rules', reg.coin_rules.unit === 'coins' && reg.coin_rules.note === 'play coins - not money' && reg.coin_rules.overdraft === false && reg.coin_rules.provenance === 'AUTHORED' && Number.isInteger(reg.coin_rules.start_balance) && reg.coin_rules.start_balance > 0);
const sel = P.selection.selected;
check('registry.parishes_match', JSON.stringify(Object.keys(reg.parishes).sort()) === JSON.stringify([...sel].sort()));
const lots = Object.values(reg.parishes).flatMap((p) => p.lots);
check('registry.lot_ids_unique', new Set(lots.map((l) => l.id)).size === lots.length && lots.length > 0);
const badZone = lots.filter((l) => !(l.zone === 'commercial' || l.zone === 'residential') || l.landuse_provenance !== 'DERIVED' ||
  JSON.stringify(l.allowed) !== JSON.stringify([l.zone === 'commercial' ? 'shop' : 'home']));
check('registry.lots_on_commercial_or_residential', badZone.length === 0, badZone.map((l) => l.id).join(','));
check('registry.lots_authored_labelled', lots.every((l) => l.provenance === 'AUTHORED' && /not a real property/.test(l.label)));
check('registry.lot_scene_coords', lots.every((l) => l.x === l.local_m[0] && l.z === -l.local_m[1]));
function pip(rings, e, nn) { let ins = false; for (const r of rings) for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
  const [x1, y1] = r[j], [x2, y2] = r[i]; if ((y1 > nn) !== (y2 > nn) && e < (x2 - x1) * (nn - y1) / (y2 - y1) + x1) ins = !ins; } return ins; }
const outside = lots.filter((l) => !pip(P.parishes[l.parish].outline_local_m.flat(), l.local_m[0], l.local_m[1]));
check('registry.lots_inside_outline', outside.length === 0, outside.map((l) => l.id).join(','));
const kr = reg.placement.water_keepout.radius_m;
const wet = lots.filter((l) => { const o = P.parishes[l.parish].frame.origin_in_world_m;
  return P.water.labels.some((w) => Math.hypot(l.local_m[0] + o[0] - w.world_m[0], l.local_m[1] + o[1] - w.world_m[1]) < kr); });
check('registry.lots_outside_water_keepout', wet.length === 0 && P.water.labels.length > 0, wet.map((l) => l.id).join(','));
const gap = lots.filter((a) => lots.some((b) => a !== b && a.parish === b.parish && Math.hypot(a.x - b.x, a.z - b.z) < 200));
check('registry.lots_spaced', gap.length === 0);
check('registry.rent_matches_rentals', lots.every((l) => { const r = reg.rentals[l.allowed[0]]; return r.zone === l.zone && r.rent_coins_per_day === l.rent_coins_per_day && r.buy_coins === l.buy_coins; }));
const slugs = new Set(U.unions.map((u) => u.slug));
const badTrade = reg.business_types.filter((b) => (b.trade_id === null) !== (b.generic === true) || (b.trade_id !== null && !slugs.has(b.trade_id)));
check('registry.business_trade_ids_exist', badTrade.length === 0 && reg.business_types.some((b) => b.trade_id), badTrade.map((b) => b.id).join(','));
check('registry.business_ids_unique', new Set(reg.business_types.map((b) => b.id)).size === reg.business_types.length);
const cnt = reg.counts;
check('registry.counts_match', cnt.lots === lots.length && cnt.commercial === lots.filter((l) => l.zone === 'commercial').length &&
  cnt.business_types === reg.business_types.length && Object.values(reg.parishes).every((p) => p.counts.lots === p.lots.length));

// ---------- i18n
const loc = Object.fromEntries(LOCS.map((l) => [l, JSON.parse(rd('i18n/locales/' + l + '.json')).strings]));
const ek = Object.keys(loc.en).filter((k) => k.startsWith('econ.'));
check('i18n.econ_keys_all_locales', ek.length >= 20 && LOCS.every((l) => ek.every((k) => typeof loc[l][k] === 'string' && loc[l][k].length > 0)));
check('i18n.not_money_8_locales', LOCS.every((l) => loc[l]['econ.not_money'] && (l === 'en' ? /not money/.test(loc[l]['econ.not_money']) : loc[l]['econ.not_money'] !== loc.en['econ.not_money'])));
check('i18n.real_translations', LOCS.filter((l) => l !== 'en').every((l) => ek.every((k) => loc[l][k] !== loc.en[k])));
check('i18n.no_currency', LOCS.every((l) => ek.every((k) => !CUR.test(loc[l][k]))));

// ---------- page kit
let js = '', kitErr = '';
try { js = execFileSync('python3', ['-c', 'import sys;sys.path.insert(0,"web");from econkit import econ_js;sys.stdout.write(econ_js())'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); } catch (e) { kitErr = String(e.stderr || e).split('\n').filter(Boolean).pop(); }
check('kit.builds', js.length > 0, kitErr);
const core = rd('economy/core.mjs');
const coreBlock = core.slice(core.indexOf('/* ECON_CORE:BEGIN */'), core.indexOf('/* ECON_CORE:END */') + '/* ECON_CORE:END */'.length);
check('kit.core_byte_for_byte', coreBlock.length > 1000 && js.includes(coreBlock));
check('kit.no_network', !/\bfetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon|EventSource|importScripts/.test(js));
check('kit.no_payments', !/stripe|payments\/|checkout/i.test(js + rd('web/econkit.py').replace(/never linked to payments\/? ?(or Stripe)?/gi, '')));
check('kit.no_completion_write', !/TCQuests|\.complete\s*\(|\.find\s*\(\s*['"]/.test(js) && (js.match(/setItem\(/g) || []).length === 1 && js.includes('storage.setItem(ECON_KEY'));
check('kit.no_currency', !CUR.test(js), (js.match(CUR) || [''])[0]);

// ---------- ledger
const R = E.econIndex(reg);
const start = reg.coin_rules.start_balance;
const shop = lots.find((l) => l.zone === 'commercial'), home = lots.find((l) => l.zone === 'residential');
const trade = reg.business_types.find((b) => b.trade_id), gen = reg.business_types.find((b) => !b.trade_id);
const names = (r) => r.events.map((e) => e[0]);
let s = E.econFresh(R);
check('ledger.fresh', s.coins === start && s.day === 0 && E.econValid(s));
let r = E.econRent(s, R, shop.id);
check('ledger.rent_charges_first_day', r.ok && s.coins === start - shop.rent_coins_per_day && names(r).join() === 'lot-rented,rent-paid,first-rent-paid');
r = E.econRent(s, R, shop.id);
check('ledger.rent_taken_refused', !r.ok && names(r)[0] === 'refused');
r = E.econOpen(s, R, shop.id, trade.id);
const shop2 = lots.find((l) => l.zone === 'commercial' && l.id !== shop.id);
const s2 = JSON.parse(JSON.stringify(s)); E.econRent(s2, R, shop2.id);
check('ledger.shop_opened_once', r.ok && names(r).join() === 'shop-opened,first-shop-opened' && r.events[0][1].tradeId === trade.trade_id && names(E.econOpen(s2, R, shop2.id, gen.id)).join() === 'shop-opened');
let before = s.coins; r = E.econTick(s, R, 1);
check('ledger.tick_rent_and_income', s.day === 1 && s.coins === before + trade.income_coins_per_day_unskilled - shop.rent_coins_per_day && !names(r).includes('first-rent-paid'));
before = s.coins; r = E.econPractice(s, R, trade.trade_id);
check('ledger.practice_unlocks_skill', s.skills[trade.trade_id] === true && names(r).includes('skill-unlocked') && s.day === 1 + reg.coin_rules.practice_days &&
  s.coins === before + trade.income_coins_per_day_unskilled - shop.rent_coins_per_day);
before = s.coins; E.econTick(s, R, 1);
check('ledger.skilled_income', s.coins === before + trade.income_coins_per_day_skilled - shop.rent_coins_per_day);
r = E.econOpen(s, R, home.id, gen.id);
check('ledger.open_needs_lot', !r.ok);
s.lots[home.id] = { mode: 'rent', since: s.day, business: null, staff: 0, unpaid: 0 };
r = E.econOpen(s, R, home.id, gen.id);
check('ledger.open_wrong_zone_refused', !r.ok && r.events[0][1].reason === 'wrong-zone');
// cannot go negative silently
let t = E.econFresh(R); t.coins = shop.buy_coins - 1;
r = E.econBuy(t, R, shop.id);
check('ledger.no_silent_negative_buy', !r.ok && t.coins === shop.buy_coins - 1 && r.events[0][0] === 'refused' && r.events[0][1].reason === 'insufficient');
t = E.econFresh(R); E.econRent(t, R, home.id); t.coins = 0;
const seen = [];
for (let d = 0; d < reg.coin_rules.eviction_after_unpaid_days; d++) { seen.push(...names(E.econTick(t, R, 1))); check('ledger.never_negative_day' + d, t.coins >= 0); }
check('ledger.unpaid_rent_releases', seen.filter((x) => x === 'rent-missed').length === reg.coin_rules.eviction_after_unpaid_days && seen.includes('lot-released') && !t.lots[home.id]);
t = E.econFresh(R); E.econRent(t, R, shop.id); E.econOpen(t, R, shop.id, trade.id); E.econHire(t, R, shop.id); E.econHire(t, R, shop.id); t.coins = 0;
t.skills = {};
r = E.econTick(t, R, 1);
const inc2 = trade.income_coins_per_day_unskilled + 2 * trade.staff_bonus_coins_per_day, wage2 = 2 * trade.staff_wage_coins_per_day;
check('ledger.wages_paid_or_staff_leave', t.coins >= 0 && (inc2 >= wage2 ? t.lots[shop.id].staff === 2 && t.coins === inc2 - wage2 - shop.rent_coins_per_day : names(r).includes('staff-left')));
for (let k = 0; k < trade.max_staff; k++) E.econHire(t, R, shop.id);
check('ledger.hire_capped', t.lots[shop.id].staff === trade.max_staff && !E.econHire(t, R, shop.id).ok);
check('ledger.bad_amount_throws', (() => { try { E.econCharge(t, -1, 'x'); return false; } catch (e) { return true; } })());
// storage
function mem() { const m = {}; return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, removeItem: (k) => { delete m[k]; }, m }; }
const st = mem();
t = E.econFresh(R); E.econRent(t, R, home.id);
check('storage.save_load_roundtrip', E.econSave(st, t) && JSON.stringify(E.econLoad(st, R).s) === JSON.stringify(t) && E.econLoad(st, R).saved && Object.keys(st.m).join() === 'tc-econ-v1');
check('storage.reset', E.econClear(st) && E.econLoad(st, R).s.coins === start && !('tc-econ-v1' in st.m));
const boom = { getItem() { throw new Error('denied'); }, setItem() { throw new Error('denied'); }, removeItem() { throw new Error('denied'); } };
const lb = E.econLoad(boom, R);
check('storage.throws_path', lb.saved === false && lb.s.coins === start && E.econSave(boom, lb.s) === false && E.econClear(boom) === false && E.econLoad(null, R).saved === false);
st.setItem('tc-econ-v1', JSON.stringify({ v: 1, coins: -5, day: 0, lots: {}, skills: {}, flags: {}, log: [] }));
check('storage.rejects_negative_or_corrupt', E.econLoad(st, R).s.coins === start && (st.setItem('tc-econ-v1', '{bad'), E.econLoad(st, R).s.coins === start) &&
  (st.setItem('tc-econ-v1', JSON.stringify({ v: 2, coins: 9 })), E.econLoad(st, R).s.coins === start));
// nearby + determinism
const nr = E.econNear(R, shop.parish, shop.x, shop.z, 250);
check('near.sorted_radius', nr.length >= 1 && nr[0].id === shop.id && nr.every((x, i) => x.d <= 250 && (i === 0 || nr[i - 1].d <= x.d)) && E.econNear(R, 'nope', 0, 0, 250).length === 0);
function run() { const q = E.econFresh(R); E.econRent(q, R, shop.id); E.econOpen(q, R, shop.id, trade.id); E.econHire(q, R, shop.id); E.econTick(q, R, 5); E.econPractice(q, R, trade.trade_id); E.econTick(q, R, 3); return JSON.stringify(q); }
check('ledger.deterministic', run() === run());

console.log(fails ? `FAIL economy: ${fails} of ${n} checks failed` : `economy: all ${n} checks ok (${lots.length} lots, ${reg.business_types.length} business types)`);
process.exit(fails ? 1 : 0);
