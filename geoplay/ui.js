/* Training drops - the map and panel part. It runs inside the geomap page, after
   the map exists. It draws the registry's public stops, lists their drops, and
   hands the on-device locator (TrainingDrops, above) a few handlers. A stop's
   coordinate is public registry data; the learner's position never reaches this
   code, only ids, states and distances rounded to 10 m. Nothing here stores or
   sends anything: which drops are open lives in one object in memory and is
   gone when the page is reloaded. */
const TDG = D.geoplay;
const TD_BY_ID = Object.fromEntries(TDG.stops.map((s) => [s.id, s]));
const TD = { open: {}, via: {}, state: {}, dist: {}, status: 'off', announce: [] };
const TD_STATUS = {
  off: 'Location is off. Press the button to let this device compare where it is with the pins, or pick a place by hand.',
  asking: 'Waiting for your device to answer; your browser asks you first.',
  watching: 'Using your device’s position here on this device only. It is compared with the pins and forgotten; nothing is stored or sent.',
  denied: 'Your device did not share its position. That is fine: pick a place under “I am here”.',
  unavailable: 'Your device could not work out its position. Pick a place under “I am here”.',
  timeout: 'Your device took too long to answer. Try again, or pick a place under “I am here”.',
  unsupported: 'This browser has no location service. Pick a place under “I am here”.',
};
const tdEl = (id) => document.getElementById(id);
const tdSrc = {
  type: 'FeatureCollection',
  features: TDG.stops.map((s) => ({ type: 'Feature', properties: { id: s.id, n: s.drops.length, near: false },
    geometry: { type: 'Point', coordinates: [s.lng, s.lat] } })),
};
function tdSyncMap() {
  const src = map.getSource('drops');
  if (!src) return;
  for (const f of tdSrc.features) f.properties.near = TD.state[f.properties.id] === 'in-range' || !!TD.open[f.properties.id];
  src.setData(tdSrc);
}
function tdDistText(s) {
  const d = TD.dist[s.id];
  if (TD.state[s.id] === 'too-coarse') return 'your device’s fix is too wide to tell (limit ' + TDG.rules.accuracy_max_m + ' m)';
  if (typeof d !== 'number') return 'distance unknown';
  return (d >= 1000 ? (d / 1000).toFixed(1) + ' km' : d + ' m') + ' away (rounded)';
}
function tdDropLi(s, d) {
  const open = !!TD.open[s.id];
  if (!open)
    return `<li data-drop="${ESC(d.id)}" data-locked="true">🔒 ${ESC(d.title)} <span class="src">${ESC(d.kind_label)}; opens within ${s.radius_m} m of the pin, or by “I am here”</span></li>`;
  const ls = d.lessons.length
    ? '<br><span class="src">lessons it builds on: ' + d.lessons.map((l) => `<a href="trade_craft_lessons.html#lesson-${ESC(l.id)}">${ESC(l.title)}</a>`).join(', ') + '</span>' : '';
  return `<li data-drop="${ESC(d.id)}" data-locked="false"><a class="door" href="${ESC(d.href)}">${ESC(d.title)}</a> <span class="src">${ESC(d.kind_label)}; ${ESC(d.provenance)}</span>${ls}</li>`;
}
function tdCheckLine(s) { return s.shoreline ? TDG.shorelineNote : 'Not yet ' + s.site_check.replace(/^not /, '') + '.'; }
/* The list is drawn once, in the registry's fixed order, and redrawn only when a stop opens or closes.
   Every other fix patches the distance text in place, so a focused control keeps its focus; an
   unlock is announced through the polite live region, not by moving anything. */
let tdSig = null, tdRenders = 0;
const tdSignature = () => TDG.stops.map((s) => s.id + (TD.open[s.id] ? '1' : '0')).join('|');
function tdMeta(s) {
  const open = !!TD.open[s.id];
  return tdDistText(s) + '; unlock radius ' + s.radius_m + ' m' + (open ? '; open ' + (TD.via[s.id] === 'device' ? 'by this device’s position' : 'by your own pick') : '');
}
function tdRow(s) {
  const open = !!TD.open[s.id];
  return `<li data-stop="${ESC(s.id)}" data-open="${open}"><b>${ESC(s.name)}</b> <span class="pv">${ESC(s.class_label)}</span>`
    + `<span class="pv ${s.coordinate_provenance === 'RECORDED' ? 'rec' : 'auth'}">pin ${ESC(s.coordinate_provenance)}</span>`
    + `<br><span class="src" data-dist>${ESC(tdMeta(s))}</span>`
    + `<br><span class="src" data-site-check="${ESC(s.site_check)}">${ESC(tdCheckLine(s))}</span>`
    + `<ul class="tasklist" style="max-height:none">${s.drops.map((d) => tdDropLi(s, d)).join('')}</ul>`
    + `<button type="button" class="popbtn" data-drop-fly="${ESC(s.id)}">show on the map</button></li>`;
}
function tdFocusKey(el) {
  const row = el && el.closest ? el.closest('[data-stop]') : null;
  if (!row) return null;
  return row.dataset.stop + '|' + (el.hasAttribute('data-drop-fly') ? 'fly' : el.getAttribute('href') || '');
}
let tdNear = '';
function tdRender() {
  const list = tdEl('dropList');
  const sig = tdSignature();
  if (sig !== tdSig) {
    const kept = list.contains(document.activeElement) ? tdFocusKey(document.activeElement) : null;
    list.innerHTML = TDG.stops.map(tdRow).join('');
    tdSig = sig; tdRenders++;
    if (kept) {
      const again = [...list.querySelectorAll('a, button')].find((el) => tdFocusKey(el) === kept);
      if (again) again.focus();
    }
  }
  for (const s of TDG.stops) {
    const row = list.querySelector(`[data-stop="${s.id}"] [data-dist]`);
    const text = tdMeta(s);
    if (row && row.textContent !== text) row.textContent = text;
  }
  tdEl('dropCount').textContent = Object.keys(TD.open).length + ' of ' + TDG.stops.length + ' stops open';
  if (TD.announce.length) { tdEl('dropAnnounce').textContent = TD.announce.join(' '); TD.announce = []; }
  const near = TDG.stops.filter((s) => TD.state[s.id] === 'in-range' || TD.open[s.id]).map((s) => s.id).join();
  if (near !== tdNear) { tdNear = near; tdSyncMap(); }
}
function tdUnlock(id, via) {
  if (!TD_BY_ID[id]) return;
  if (!TD.open[id]) {
    TD.via[id] = via;
    TD.announce.push('Opened ' + TD_BY_ID[id].name + ': ' + TD_BY_ID[id].drops.length + ' training drops.');
  }
  TD.open[id] = true;
}
function tdStatus(word) {
  TD.status = word;
  tdEl('dropStatus').textContent = TD_STATUS[word];
  const on = word === 'watching' || word === 'asking';
  const b = tdEl('dropLocate');
  b.setAttribute('aria-pressed', String(on));
  b.textContent = on ? 'Stop using my location' : 'Use my location (stays on this device)';
  if (!on) { TD.state = {}; TD.dist = {}; }
  tdRender();
}
function tdSurvey(list) {
  TD.state = {}; TD.dist = {};
  for (const r of list) {
    TD.state[r.id] = r.state; TD.dist[r.id] = r.distance_m;
    if (r.state === 'in-range') tdUnlock(r.id, 'device');
  }
  tdRender();
}
const tdLocator = TrainingDrops.createLocator(navigator, TDG.rules, TDG.stops, { onSurvey: tdSurvey, onStatus: tdStatus });
tdEl('dropLocate').addEventListener('click', () => { if (tdLocator.active()) tdLocator.stop(); else tdLocator.start(); });
tdEl('dropHere').innerHTML = '<option value="">choose a public place</option>'
  + TDG.stops.map((s) => `<option value="${ESC(s.id)}">${ESC(s.name)}</option>`).join('');
function tdFly(id) {
  const s = TD_BY_ID[id];
  if (REDUCED) map.jumpTo({ center: [s.lng, s.lat], zoom: 14 });
  else map.flyTo({ center: [s.lng, s.lat], zoom: 14, duration: 1200 });
}
tdEl('dropHere').addEventListener('change', (e) => {
  const id = e.target.value;
  if (!id) return;
  tdUnlock(id, 'manual'); tdRender(); tdFly(id);
  tdEl('dropStatus').textContent = 'Opened by your own pick: “' + TD_BY_ID[id].name + '”. Nothing was measured and nothing is kept.';
});
tdEl('dropList').addEventListener('click', (e) => {
  const b = e.target.closest('[data-drop-fly]');
  if (b) tdFly(b.dataset.dropFly);
});
tdEl('dropForget').addEventListener('click', () => { TD.open = {}; TD.via = {}; tdEl('dropHere').value = ''; TD.announce.push('All drops closed again.'); tdRender(); });
function tdPopup(id) {
  const s = TD_BY_ID[id];
  showPopup([s.lng, s.lat],
    `<b>${ESC(s.name)}</b><br><span class="pv">${ESC(s.class_label)}</span><span class="pv ${s.coordinate_provenance === 'RECORDED' ? 'rec' : 'auth'}">pin ${ESC(s.coordinate_provenance)}</span>`
    + `<br>${s.drops.length} training drops here, play only; unlock radius ${s.radius_m} m.`
    + `<br><span class="src">${ESC(s.source_ref)}: ${ESC(s.source_text)}</span>`
    + `<br><span class="src">${ESC(tdCheckLine(s))}</span>`
    + `<br><b class="td-safety">${ESC(TDG.safetyLine)}</b>`
    + `<br><button type="button" class="popbtn" data-drops-panel="1">open the drops list</button>`);
}
document.addEventListener('click', (e) => {
  if (!e.target.closest('[data-drops-panel]')) return;
  if (currentPopup) currentPopup.remove();
  if (openPanel !== 'drops') document.querySelector('[data-panel="drops"]').click();
});
function tdAddLayers() {
  if (map.getSource('drops')) return;
  map.addSource('drops', { type: 'geojson', data: tdSrc });
  tdNear = '*'; setTimeout(tdRender, 0);   // the next render sends the current near/open flags to the new source
  map.addLayer({ id: 'env-drops-near', type: 'circle', source: 'drops', filter: ['==', ['get', 'near'], true],
    paint: { 'circle-radius': 15, 'circle-color': '#E8743B', 'circle-opacity': 0.25, 'circle-stroke-color': '#E8743B', 'circle-stroke-width': 2, 'circle-translate': [18, -14] } });
  map.addLayer({ id: 'env-drops', type: 'circle', source: 'drops',
    paint: { 'circle-radius': 8, 'circle-color': '#E8743B', 'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 2, 'circle-translate': [18, -14] } });
  map.on('click', 'env-drops', (e) => { e.preventDefault(); tdPopup(e.features[0].properties.id); });
  map.on('mouseenter', 'env-drops', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'env-drops', () => { map.getCanvas().style.cursor = ''; });
  const t = document.querySelector('[data-layer="drops"]');
  if (t && !t.checked) for (const id of ['env-drops', 'env-drops-near']) map.setLayoutProperty(id, 'visibility', 'none');
}
document.getElementById('layerToggles').addEventListener('change', (e) => {
  if (e.target.dataset.layer !== 'drops') return;
  for (const id of ['env-drops', 'env-drops-near'])
    if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', e.target.checked ? 'visible' : 'none');
});
if (map.isStyleLoaded()) tdAddLayers(); else map.once('load', tdAddLayers);
tdEl('dropStatus').textContent = TD_STATUS.off;
tdRender();
/* test hook: ids and words only - never a position */
window.__geoplay = () => ({
  stops: TDG.stops.map((s) => s.id), open: Object.keys(TD.open), via: { ...TD.via }, states: { ...TD.state },
  status: TD.status, active: tdLocator.active(), renders: tdRenders, layer: !!map.getLayer('env-drops'),
  safetyShown: !!tdEl('dropSafety') && tdEl('dropSafety').textContent.trim() === TDG.safetyLine,
  locks: [...document.querySelectorAll('#dropList [data-locked="true"]')].length,
  unlocks: [...document.querySelectorAll('#dropList [data-locked="false"] a.door')].map((a) => a.getAttribute('href')),
});
