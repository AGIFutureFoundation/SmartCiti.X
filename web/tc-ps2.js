// tc-ps2.js: SmartCiti PS2-era pass for the trade_craft worlds (SMARTCITI-STYLE.md, in
// WorldForge-Browser). These worlds are authored flat-color Lambert already, so the pass is
// renderer-side: era internal resolution with chunky pixel upscale, composite-video grading,
// CRT scanline overlay, and nearest-filtered texture pages capped at 512px. ?modern=1 opts
// out. Idempotent; re-run via window.__tcPS2() after async textures (e.g. the atlas) land.
import * as THREE from './vendor/three.module.min.js';

const PAGE = 512;

function eraMaps(scene, stats) {
  const seen = new Set();
  scene.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      const map = m?.map; if (!map || seen.has(map.uuid)) continue;
      seen.add(map.uuid); stats.maps++;
      const img = map.image, w = img?.width || 0, h = img?.height || 0;
      if (w > PAGE || h > PAGE) {                       // era texture page ceiling
        const s = PAGE / Math.max(w, h), dw = Math.max(2, Math.round(w * s)), dh = Math.max(2, Math.round(h * s));
        const c = document.createElement('canvas'); c.width = dw; c.height = dh;
        c.getContext('2d').drawImage(img, 0, 0, dw, dh);
        map.image = c; map.needsUpdate = true; stats.downscaled++;
      }
      map.magFilter = THREE.NearestFilter;              // chunky texels
      map.anisotropy = 1;                               // PS2s had no anisotropic filtering
    }
  });
}

export function tcPS2(renderer, canvas, scene) {
  if (new URLSearchParams(location.search).get('modern') === '1') return { on: false };
  const stats = { on: true, maps: 0, downscaled: 0 };
  renderer.setPixelRatio(Math.max(0.35, Math.min(devicePixelRatio || 1, 2) * 0.42));  // ~PS2-class framebuffer
  canvas.style.imageRendering = 'pixelated';
  canvas.style.filter = 'saturate(1.14) contrast(1.07) sepia(0.05)';                    // composite-video push
  eraMaps(scene, stats);
  if (!document.getElementById('tc-crt')) {
    const ov = document.createElement('div');
    ov.id = 'tc-crt'; ov.setAttribute('aria-hidden', 'true');
    ov.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:3;'
      + 'background:repeating-linear-gradient(0deg,rgba(6,10,26,.08) 0 1px,transparent 1px 3px),'
      + 'radial-gradient(ellipse at center,transparent 60%,rgba(10,6,24,.32) 100%);';
    document.body.appendChild(ov);
  }
  window.__tcPS2 = () => eraMaps(scene, stats);
  return stats;
}
