/* Training drops - the on-device part. Pure geometry plus a locator that wraps
   the browser's own geolocation. It is given the stops as data and a
   navigator-like object; it has no network call, no storage, no cookie and no
   global state beyond what it returns. A position is read inside onFix, turned
   into a distance rounded to 10 m per stop, handed on as that and nothing
   else, and not kept anywhere. */
const TrainingDrops = (() => {
  const EARTH_M = 6371008.8;
  const ROUND_M = 10;
  const rad = (d) => (d * Math.PI) / 180;

  /* great-circle distance in metres between two WGS84 points */
  function distanceM(aLat, aLng, bLat, bLng) {
    const dLat = rad(bLat - aLat), dLng = rad(bLng - aLng);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(aLat)) * Math.cos(rad(bLat)) * Math.sin(dLng / 2) ** 2;
    return 2 * EARTH_M * Math.asin(Math.min(1, Math.sqrt(h)));
  }

  /* one stop against one fix: 'in-range', 'out-of-range' or 'too-coarse'.
     A fix that is not finite, or whose accuracy circle is wider than the
     limit, never unlocks anything. */
  function unlockCheck(stop, fix, limits) {
    const ok = fix && Number.isFinite(fix.lat) && Number.isFinite(fix.lng)
      && Math.abs(fix.lat) <= 90 && Math.abs(fix.lng) <= 180;
    if (!ok) return { state: 'no-fix', distance_m: null };
    const d = distanceM(fix.lat, fix.lng, stop.lat, stop.lng);
    const shown = Math.round(d / ROUND_M) * ROUND_M;
    if (!(Number.isFinite(fix.accuracy) && fix.accuracy <= limits.accuracy_max_m))
      return { state: 'too-coarse', distance_m: shown };
    return { state: d <= stop.radius_m ? 'in-range' : 'out-of-range', distance_m: shown };
  }

  /* every stop against one fix, nearest first; only ids, states and rounded
     distances come back - never the fix */
  function survey(stops, fix, limits) {
    return stops.map((s) => ({ id: s.id, ...unlockCheck(s, fix, limits) }))
      .sort((a, b) => (a.distance_m === null) - (b.distance_m === null) || a.distance_m - b.distance_m);
  }

  /* the locator. start() asks the device (the browser shows its own permission
     prompt); handlers.onSurvey(list) gets the survey for each fix;
     handlers.onStatus(word) gets 'asking' | 'watching' | 'denied' |
     'unavailable' | 'timeout' | 'unsupported' | 'off'. */
  function createLocator(nav, limits, stops, handlers) {
    let watchId = null, refused = false;
    const geo = nav && nav.geolocation ? nav.geolocation : null;
    function onFix(pos) {
      const c = pos && pos.coords;
      if (!c) return;
      handlers.onSurvey(survey(stops, { lat: c.latitude, lng: c.longitude, accuracy: c.accuracy }, limits));
      handlers.onStatus('watching');
    }
    function onErr(err) {
      const code = err && err.code;
      const word = code === 1 ? 'denied' : code === 3 ? 'timeout' : 'unavailable';
      if (code === 1) { refused = true; stop(word); } else handlers.onStatus(word);
    }
    function start() {
      if (!geo) { handlers.onStatus('unsupported'); return false; }
      if (watchId !== null) return true;
      refused = false;
      handlers.onStatus('asking');
      const id = geo.watchPosition(onFix, onErr, { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 });
      if (refused) geo.clearWatch(id); else watchId = id;
      return !refused;
    }
    function stop(word) {
      if (watchId !== null && geo) geo.clearWatch(watchId);
      watchId = null;
      handlers.onStatus(word || 'off');
    }
    return { start, stop, active: () => watchId !== null };
  }

  return { distanceM, unlockCheck, survey, createLocator, ROUND_M };
})();
