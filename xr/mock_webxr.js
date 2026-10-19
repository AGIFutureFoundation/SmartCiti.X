/* MOCKED WebXR runtime - injected BEFORE any page script by the session
   harness (xr/session_harness.mjs, via page.addInitScript).

   WHAT THIS IS. A fake `navigator.xr` that is just faithful enough for
   three.js r160's own WebXRManager to run on top of it in headless
   Chromium: isSessionSupported, requestSession, a session with
   requestReferenceSpace / requestAnimationFrame / updateRenderState /
   inputSources / end, an XRWebGLLayer shim backed by a real WebGL
   framebuffer (so the page's draws land somewhere that can be read back),
   an XRFrame with getViewerPose (two eyes) and getPose (two tracked-pointer
   controllers), and xr-standard gamepads the page polls.

   WHAT THIS IS NOT. No physical headset, no browser XR runtime, no compositor, no
   head or hand tracking, no lens or display, no real controller. Every
   frame, pose and button here is made up by this file. It can show that
   the page's XR code path RUNS and BEHAVES under the WebXR interfaces the
   page uses; it cannot show that it works on a headset. The status of the
   roadmap criterion stays "mocked half met, headset half not met".

   Everything the harness can break on purpose carries a `MUT:` tag so a
   mutation is one line. */
(() => {
  if (window.__xrMock) return;
  const cfg = Object.assign({
    vr: true, ar: false,          // what isSessionSupported answers
    floor: true,                  // grant local-floor (false: only `local`)
    eyeW: 256, eyeH: 288,         // one eye's viewport, in framebuffer pixels
    head: [0, 1.6, 0],            // standing head position, local-floor
    blend: 'opaque',
    readEvery: 0,                 // read the framebuffer back every N frames (0: only when the harness asks - a read-back
                                  // waits for the whole GPU queue, so it must not sit inside a timing window)
  }, window.__xrMockCfg || {});

  const stats = {
    installedAtMs: performance.now(), readyStateAtInstall: document.readyState,
    supportCalls: [], requests: [], refSpaces: [], refSpaceRejected: [],
    framesDelivered: 0, firstFrameMs: null, lastFrameMs: null, gaps: [],
    viewerPoseCalls: 0, layersCreated: 0, renderStates: [], inputChanges: 0,
    selectStart: 0, select: 0, selectEnd: 0, squeeze: 0,
    sessionsStarted: 0, sessionsEnded: 0, endEvents: 0,
    reads: [], lastRead: null, requestedFrameCallbacks: 0,
    buttons: [], axes: [],
  };

  /* ---- matrices: column-major, as WebXR hands them to a page ---------- */
  const ident = () => new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  const trans = (x, y, z) => { const m = ident(); m[12] = x; m[13] = y; m[14] = z; return m; };
  function persp(fovY, aspect, near, far) {
    const f = 1 / Math.tan(fovY / 2), m = new Float32Array(16);
    m[0] = f / aspect; m[5] = f; m[10] = (far + near) / (near - far); m[11] = -1;
    m[14] = 2 * far * near / (near - far);
    return m;
  }

  /* ---- spaces, input sources, gamepads -------------------------------- */
  const mkSpace = (name, pos) => ({ name, pos, matrix() { return trans(...this.pos); } });
  const refSpace = (type) => ({ type, getOffsetReferenceSpace() { return this; }, onreset: null });
  function mkSource(hand, x) {
    const nBtn = 6;
    return {
      handedness: hand, targetRayMode: 'tracked-pointer',
      targetRaySpace: mkSpace(hand + '-ray', [x, 1.2, -0.4]),
      gripSpace: mkSpace(hand + '-grip', [x, 1.15, -0.35]),
      profiles: ['oculus-touch-v3', 'generic-trigger-squeeze-thumbstick'],
      hand: null,
      // xr-standard: [0,1] touchpad, [2,3] thumbstick; buttons trigger,
      // squeeze, touchpad, thumbstick, A/X, B/Y
      gamepad: { id: 'mock-xr-controller', index: -1, connected: true, mapping: 'xr-standard',
        axes: [0, 0, 0, 0],
        buttons: Array.from({ length: nBtn }, () => ({ pressed: false, touched: false, value: 0 })) },
    };
  }
  const left = mkSource('left', -0.25), right = mkSource('right', 0.25);
  const bySide = { left, right };

  /* ---- the framebuffer an XRWebGLLayer hands the page ------------------ */
  class MockXRWebGLLayer {
    constructor(session, gl, init = {}) {
      this.session = session; this.context = gl;
      stats.layersCreated++;
      this.antialias = !!init.antialias;
      this.fixedFoveation = 0;                       // r160 writes it on setFoveation
      this.framebufferWidth = cfg.eyeW * 2; this.framebufferHeight = cfg.eyeH;
      this.framebufferScale = init.framebufferScaleFactor || 1;
      const W = this.framebufferWidth, H = this.framebufferHeight;
      const prev = gl.getParameter(gl.FRAMEBUFFER_BINDING);
      const prevRb = gl.getParameter(gl.RENDERBUFFER_BINDING);
      this.framebuffer = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, this.framebuffer);
      // renderbuffers, not textures: three keeps a texture-binding cache this
      // file must never disturb
      const rc = gl.createRenderbuffer();
      gl.bindRenderbuffer(gl.RENDERBUFFER, rc);
      gl.renderbufferStorage(gl.RENDERBUFFER, gl.RGBA8, W, H);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.RENDERBUFFER, rc);
      const rd = gl.createRenderbuffer();
      gl.bindRenderbuffer(gl.RENDERBUFFER, rd);
      gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH24_STENCIL8, W, H);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_STENCIL_ATTACHMENT, gl.RENDERBUFFER, rd);
      this.status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
      gl.bindFramebuffer(gl.FRAMEBUFFER, prev);
      gl.bindRenderbuffer(gl.RENDERBUFFER, prevRb);
    }
    getViewport(view) {
      const w = cfg.eyeW, h = cfg.eyeH;
      return { x: view.eye === 'right' ? w : 0, y: 0, width: w, height: h };
    }
  }
  window.XRWebGLLayer = MockXRWebGLLayer;
  // makeXRCompatible would need a real XR device behind the GL context
  for (const C of [window.WebGL2RenderingContext, window.WebGLRenderingContext])
    if (C) C.prototype.makeXRCompatible = function () { return Promise.resolve(); };

  /* ---- the frame ------------------------------------------------------- */
  const makeFrame = (session) => ({
    session, time: 0,
    getViewerPose(space) {
      stats.viewerPoseCalls++;
      const t = performance.now() / 1000;
      // a slow standing sway, so successive frames are not identical
      const hx = cfg.head[0] + Math.sin(t * .7) * .02;
      const hy = (space.type === 'local-floor' ? cfg.head[1] : 0) + Math.sin(t * 1.1) * .005;
      const hz = cfg.head[2];
      const near = session.renderState.depthNear ?? .1, far = session.renderState.depthFar ?? 1000;
      const proj = persp(Math.PI / 2, cfg.eyeW / cfg.eyeH, near, far);
      const view = (eye, dx) => ({ eye, projectionMatrix: proj,
        transform: { matrix: trans(hx + dx, hy, hz), position: { x: hx + dx, y: hy, z: hz } } });
      return { transform: { matrix: trans(hx, hy, hz) },
        views: [view('left', -.032), view('right', .032)] };   // MUT: viewer-pose
    },
    getPose(space) {
      if (!space || !space.matrix) return null;
      return { transform: { matrix: space.matrix() }, emulatedPosition: false };
    },
    getJointPose() { return null; },
  });

  /* ---- the session ----------------------------------------------------- */
  class MockXRSession extends EventTarget {
    constructor(mode, init) {
      super();
      this.mode = mode; this.init = init;
      this.environmentBlendMode = cfg.blend; this.visibilityState = 'visible';
      this.renderState = { depthNear: .1, depthFar: 1000, baseLayer: null };   // no `layers`: baseLayer path
      this._inputs = []; this._pending = []; this._h = 0; this._ended = false;
      this.frame = makeFrame(this); this._raf = 0;
    }
    get inputSources() { return this._inputs; }
    requestReferenceSpace(type) {
      stats.refSpaces.push(type);
      if (type === 'local-floor' && !cfg.floor) { stats.refSpaceRejected.push(type); return Promise.reject(new Error('mock: local-floor not granted')); }
      return Promise.resolve(refSpace(type));
    }
    updateRenderState(s) { stats.renderStates.push(Object.keys(s)); Object.assign(this.renderState, s); }
    requestAnimationFrame(cb) {
      stats.requestedFrameCallbacks++;
      const h = ++this._h; this._pending.push([h, cb]);
      if (!this._raf && !this._ended) this._raf = requestAnimationFrame(this._pump);
      return h;
    }
    cancelAnimationFrame(h) { this._pending = this._pending.filter((p) => p[0] !== h); }
    _pump = (t) => {
      this._raf = 0;
      if (this._ended) return;
      const batch = this._pending; this._pending = [];
      if (!stats.firstFrameMs) {
        // the runtime reports its input sources as the session comes alive
        this._inputs = [left, right];
        stats.inputChanges++;
        const ev = new Event('inputsourceschange'); ev.session = this;
        ev.added = [left, right]; ev.removed = [];
        this.dispatchEvent(ev);
      }
      const now = performance.now();
      if (stats.lastFrameMs !== null && stats.gaps.length < 4000) stats.gaps.push(now - stats.lastFrameMs);
      if (stats.firstFrameMs === null) stats.firstFrameMs = now;
      stats.lastFrameMs = now;
      this.frame.time = t;
      for (const [, cb] of batch) {
        cb(t, this.frame);                           // MUT: deliver-frames
        stats.framesDelivered++;
      }
      if (this._pending.length && !this._raf) this._raf = requestAnimationFrame(this._pump);
      if (cfg.readEvery && stats.framesDelivered % cfg.readEvery === 1) readBack(this);
    };
    end() {
      if (this._ended) return Promise.resolve();
      this._ended = true; stats.sessionsEnded++;
      if (this._raf) cancelAnimationFrame(this._raf);
      this._pending = []; this._inputs = [];
      this.dispatchEvent(new Event('end'));          // MUT: end-event
      stats.endEvents++;
      return Promise.resolve();
    }
  }
  let live = null;

  /* ---- read the framebuffer back: did the page draw anything, in both eyes? */
  function readBack(session) {
    const layer = session.renderState.baseLayer; if (!layer) return;
    const gl = layer.context, W = layer.framebufferWidth, H = layer.framebufferHeight;
    const prev = gl.getParameter(gl.FRAMEBUFFER_BINDING);
    gl.bindFramebuffer(gl.FRAMEBUFFER, layer.framebuffer);
    const px = new Uint8Array(W * H * 4);
    gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, px);
    gl.bindFramebuffer(gl.FRAMEBUFFER, prev);
    const eye = (x0, x1) => {
      let sum = 0, n = 0, lit = 0; const seen = new Set();
      for (let y = 0; y < H; y += 7) for (let x = x0; x < x1; x += 7) {
        const i = (y * W + x) * 4, l = px[i] + px[i + 1] + px[i + 2];
        sum += l; n++; if (l > 12) lit++; seen.add((px[i] >> 4) << 8 | (px[i + 1] >> 4) << 4 | (px[i + 2] >> 4));
      }
      return { mean: sum / n / 3, lit: lit / n, colours: seen.size };
    };
    let diff = 0, dn = 0; const half = W / 2;
    for (let y = 0; y < H; y += 7) for (let x = 0; x < half; x += 7) {
      const a = (y * W + x) * 4, b = (y * W + x + half) * 4;
      diff += Math.abs(px[a] - px[b]) + Math.abs(px[a + 1] - px[b + 1]) + Math.abs(px[a + 2] - px[b + 2]); dn++;
    }
    const r = { frame: stats.framesDelivered, left: eye(0, half), right: eye(half, W),
      stereoDiff: diff / dn / 3, size: [W, H], status: layer.status === gl.FRAMEBUFFER_COMPLETE };
    stats.lastRead = r; if (stats.reads.length < 60) stats.reads.push(r);
  }

  /* ---- navigator.xr ---------------------------------------------------- */
  const xr = Object.assign(new EventTarget(), {
    isSessionSupported(mode) {
      stats.supportCalls.push(mode);
      return Promise.resolve(mode === 'immersive-vr' ? cfg.vr : mode === 'immersive-ar' ? cfg.ar : false);   // MUT: supported
    },
    requestSession(mode, init = {}) {
      stats.requests.push({ mode, required: init.requiredFeatures || [], optional: init.optionalFeatures || [] });
      if (live && !live._ended) return Promise.reject(new DOMException('mock: a session is already live', 'InvalidStateError'));
      if (mode === 'immersive-vr' && !cfg.vr || mode === 'immersive-ar' && !cfg.ar)
        return Promise.reject(new DOMException('mock: mode not supported', 'NotSupportedError'));
      live = new MockXRSession(mode, init); stats.sessionsStarted++;
      return Promise.resolve(live);
    },
  });
  Object.defineProperty(navigator, 'xr', { value: xr, configurable: true });

  /* ---- what the harness drives ----------------------------------------- */
  const evt = (type, src) => {
    const e = new Event(type); e.inputSource = src; e.frame = live && live.frame; return e;
  };
  window.__xrMock = {
    cfg, stats,
    live: () => live,
    // a thumbstick: x, y in [-1, 1] on the xr-standard thumbstick axes 2 and 3
    stick(side, x, y) { bySide[side].gamepad.axes[2] = x; bySide[side].gamepad.axes[3] = y; stats.axes.push([side, x, y]); },
    // a button by xr-standard index (0 trigger, 1 squeeze, 4 A/X, 5 B/Y); the
    // trigger and squeeze ALSO raise the session's select / squeeze events, as a runtime does
    button(side, i, down) {
      const src = bySide[side], b = src.gamepad.buttons[i];
      const was = b.pressed;
      b.pressed = b.touched = !!down; b.value = down ? 1 : 0;        // MUT: button-state
      stats.buttons.push([side, i, !!down]);
      if (!live || live._ended || was === !!down) return;
      if (i === 0) {
        if (down) { stats.selectStart++; live.dispatchEvent(evt('selectstart', src)); }
        else { stats.select++; stats.selectEnd++; live.dispatchEvent(evt('select', src)); live.dispatchEvent(evt('selectend', src)); }   // MUT: select-event
      } else if (i === 1 && down) { stats.squeeze++; live.dispatchEvent(evt('squeeze', src)); }
    },
    readNow() { if (live && !live._ended) readBack(live); return stats.lastRead; },
    snapshot() {
      const s = JSON.parse(JSON.stringify(stats));
      s.gaps = s.gaps.slice(); return s;
    },
  };
})();
