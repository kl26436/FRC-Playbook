/* The robot in 3D, from the final CAD. Data: robot.json + robot.bin, written by tools/make_viewer_data.py.
   CAD units are inches: X forward, Y left, Z up, origin on the carpet at the robot's centre.
   One page, five uses, chosen by ?mode= : explore (click a part), part (one part, alone or in place),
   keepout (the wrist keep-out table as a picture), replay (posed by the page that embeds it),
   assemble (build a mechanism step by step, with its fasteners: steps come from assembly.json). */
(function () {
  'use strict';
  var T = window.THREE, D2R = Math.PI / 180;
  var qs = new URLSearchParams(location.search);
  var MODE = qs.get('mode') || 'explore', PART = qs.get('part');
  document.body.className = 'mode-' + MODE;
  function $(id) { return document.getElementById(id); }
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // Joint pivots, from the CAD (the same numbers the robot code uses).
  var PIV_W = [4.5, 0, 24.5], PIV_F = [-13.5, 0, 16.0], PIV_T = [0, -7.1, 27.5];
  var GROUPS = ['frame', 'stage_a', 'stage_b', 'carriage', 'wrist', 'fork', 'tray'];
  var SUB_COL = ['#5b6b78', '#2f7fd1', '#e07b1f', '#18a08f', '#b04fc2', '#d8b21f', '#2a4fd1'];
  // Where each subsystem goes when the robot is pulled apart, inches in CAD axes.
  var APART = [[0, 0, 0], [0, 0, 30], [30, 0, 30], [-26, 0, 40], [-34, 0, 2], [0, 40, 0], [0, 0, -14]];

  // The wrist keep-out table the code uses: at a carriage height from..to, the wrist may be between min and max degrees.
  // Keep in step with keepOutZones in src/calcs.ts.
  var ZONES = [[0, 0.75, -90, -90], [0.75, 2, -90, 75], [2, 7, -75, 75], [7, 9, -60, 75], [9, 15, -45, 75], [15, 23, -40, 75], [23, 66, -90, 75]];
  // The swept clash check on the CAD (wrist drawing, sheet 3): 1 = clear at that carriage height and wrist angle.
  var GH = [0, 1.25, 3, 6, 7, 9, 12, 15, 17.5, 20, 22, 23, 27, 45, 66], GT = [-90, -75, -60, -45, -40, -38, -35, -30, 0, 41, 60, 75];
  var GRID = [[1,1,0,0,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1,1,1],[0,1,1,1,1,1,1,1,1,1,1,1],[0,1,1,1,1,1,1,1,1,1,1,1],[0,1,1,1,1,1,1,1,1,1,1,1],
    [0,0,1,1,1,1,1,1,1,1,1,1],[0,0,0,1,1,1,1,1,1,1,1,1],[0,0,0,1,1,1,1,1,1,1,1,1],[1,0,0,0,1,1,1,1,1,1,1,1],[1,1,0,0,1,1,1,1,1,1,1,1],[1,1,0,0,1,1,1,1,1,1,1,1],
    [1,1,1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1,1,1]];
  function zoneAt(h) { for (var i = 0; i < ZONES.length; i++) if (h < ZONES[i][1]) return ZONES[i]; return ZONES[ZONES.length - 1]; }
  function allowed(h, th) { var z = zoneAt(h); return th >= z[2] - 0.5 && th <= z[3] + 0.5; }

  var canvas = $('view'), hint = $('hint');
  var renderer;
  try {
    if (!T) throw new Error('no three');
    renderer = new T.WebGLRenderer({ canvas: canvas, antialias: true, preserveDrawingBuffer: true });
  } catch (err) {
    canvas.parentNode.innerHTML = '<p class="fallback">The 3D model needs WebGL, which is not available in this browser.</p>';
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputEncoding = T.sRGBEncoding;
  renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  var scene = new T.Scene(), camera = new T.PerspectiveCamera(32, 1, 1, 4000);
  scene.add(new T.HemisphereLight(0xffffff, 0x6f757c, 0.85));
  var sun = new T.DirectionalLight(0xffffff, 1.1); sun.position.set(80, 160, 120); scene.add(sun);
  var fill = new T.DirectionalLight(0xffffff, 0.35); fill.position.set(-120, 60, -90); scene.add(fill);
  var floorMat = new T.MeshStandardMaterial({ roughness: 1 });
  var floor = new T.Mesh(new T.CircleGeometry(140, 64), floorMat); floor.rotation.x = -Math.PI / 2; floor.position.y = -0.02; scene.add(floor);
  var grid = new T.GridHelper(240, 20, 0x888888, 0x777777); grid.material.opacity = 0.18; grid.material.transparent = true; scene.add(grid);
  scene.background = new T.Color();
  function retheme() { scene.background.set(css('--viewer-bg')); floorMat.color.set(css('--viewer-floor')).convertSRGBToLinear(); dirty = true; }

  // CAD (X forward, Y left, Z up) to three.js (X forward, Y up, Z right)
  var root = new T.Group(); root.matrixAutoUpdate = false;
  root.matrix.set(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1); scene.add(root);
  function toThree(c) { return new T.Vector3(c[0], c[2], -c[1]); }
  var S = [], GG = [];              // S[sub]: a group per subsystem; GG[sub][motion group]
  var state = { c: 0, th: -90, psi: 90, tray: 0 }, apart = 0;
  var meshes = [], parts = [], made = {}, subs = [], byMark = {}, byG = {}, samples = {}, M = {};
  var dirty = true;
  GROUPS.forEach(function (g) { M[g] = new T.Matrix4(); });

  function m4() { return new T.Matrix4(); }
  function about(p, rot) { return m4().makeTranslation(p[0], p[1], p[2]).multiply(rot).multiply(m4().makeTranslation(-p[0], -p[1], -p[2])); }
  function apply() {
    var c = state.c;
    M.stage_a.makeTranslation(0, 0, c / 3); M.stage_b.makeTranslation(0, 0, 2 * c / 3); M.carriage.makeTranslation(0, 0, c);
    M.wrist.copy(m4().makeTranslation(0, 0, c).multiply(about(PIV_W, m4().makeRotationY((-state.th - 90) * D2R))));
    M.fork.copy(about(PIV_F, m4().makeRotationY((state.psi - 90) * D2R)));
    M.tray.copy(about(PIV_T, m4().makeRotationX(state.tray * D2R)));
    GG.forEach(function (G) { GROUPS.forEach(function (g) { G[g].matrix.copy(M[g]); G[g].matrixWorldNeedsUpdate = true; }); });
    S.forEach(function (s, i) { s.position.set(APART[i][0] * apart, APART[i][1] * apart, APART[i][2] * apart); });
    if (MODE === 'keepout' && !anim) { tgt.y = 22 + state.c * 0.5; dist = 125 + state.c * 1.5; placeCam(); }
    onChange(); dirty = true;
  }
  function measure() {
    var top = 0, reach = 0, v = new T.Vector3();
    GROUPS.forEach(function (g) {
      var s = samples[g]; if (!s) return;
      for (var i = 0; i < s.length; i += 3) {
        v.set(s[i], s[i + 1], s[i + 2]).applyMatrix4(M[g]);
        if (v.z > top) top = v.z;
        var r = Math.max(Math.abs(v.x) - 14, Math.abs(v.y) - 14); if (r > reach) reach = r;
      }
    });
    return { pivot: PIV_W[2] + state.c, top: top, reach: Math.max(0, reach) };
  }

  // ---- camera: orbit a target ----
  var tgt = new T.Vector3(0, 22, 0), az = 38 * D2R, el = 18 * D2R, dist = 125, anim = null;
  var lim = { dmin: 40, dmax: 420, emin: -0.05, ymin: 0, ymax: 110 };
  function placeCam() {
    camera.position.set(tgt.x + dist * Math.cos(el) * Math.cos(az), tgt.y + dist * Math.sin(el), tgt.z + dist * Math.cos(el) * Math.sin(az));
    camera.lookAt(tgt); dirty = true;
  }
  function setView(a, e, d, to, ms) {
    var a0 = az, e0 = el, d0 = dist, p0 = tgt.clone(), t0 = performance.now();
    var a1 = a * D2R, e1 = e * D2R, d1 = d || dist, p1 = to || tgt.clone();
    while (a1 - a0 > Math.PI) a1 -= 2 * Math.PI; while (a0 - a1 > Math.PI) a1 += 2 * Math.PI;
    anim = function (now) { var k = Math.min(1, (now - t0) / (ms || 450)); k = k * k * (3 - 2 * k);
      az = a0 + (a1 - a0) * k; el = e0 + (e1 - e0) * k; dist = d0 + (d1 - d0) * k; tgt.lerpVectors(p0, p1, k); placeCam(); if (k >= 1) anim = null; };
  }
  var drag = null, pinch = null, moved = 0;
  canvas.addEventListener('pointerdown', function (e) { drag = { x: e.clientX, y: e.clientY, pan: e.button === 2 || e.shiftKey }; moved = 0; try { canvas.setPointerCapture(e.pointerId); } catch (x) {} });
  canvas.addEventListener('pointermove', function (e) {
    if (!drag || pinch) return; var dx = e.clientX - drag.x, dy = e.clientY - drag.y; moved += Math.abs(dx) + Math.abs(dy);
    drag.x = e.clientX; drag.y = e.clientY;
    if (drag.pan) tgt.y = Math.max(lim.ymin, Math.min(lim.ymax, tgt.y + dy * dist / 600));
    else { az += dx * 0.008; el = Math.max(lim.emin, Math.min(1.45, el + dy * 0.006)); }
    anim = null; placeCam();
  });
  canvas.addEventListener('pointerup', function (e) { if (drag && moved < 6) pick(e); drag = null; });
  canvas.addEventListener('pointercancel', function () { drag = null; });
  canvas.addEventListener('contextmenu', function (e) { e.preventDefault(); });
  function zoom(f) { dist = Math.max(lim.dmin, Math.min(lim.dmax, dist * f)); anim = null; placeCam(); }
  canvas.addEventListener('wheel', function (e) { e.preventDefault(); zoom(Math.exp(e.deltaY * 0.001)); }, { passive: false });
  function gap(e) { return Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY); }
  canvas.addEventListener('touchstart', function (e) { if (e.touches.length === 2) pinch = gap(e); }, { passive: true });
  canvas.addEventListener('touchmove', function (e) { if (e.touches.length === 2 && pinch) { var d = gap(e); zoom(pinch / d); pinch = d; } }, { passive: true });
  canvas.addEventListener('touchend', function () { pinch = null; }, { passive: true });

  // ---- highlighting ----
  var marked = [], ghosted = false, solo = null, chosen = null;
  var hlSoft = new T.MeshBasicMaterial({ color: 0xff7a1a, transparent: true, opacity: 0.6, depthTest: false });
  var hlSolid = new T.MeshStandardMaterial({ color: new T.Color('#ff7a1a').convertSRGBToLinear(), roughness: 0.6, metalness: 0.1 });
  function subGeom(p) {
    var src = meshes[p.m].geom, ix = meshes[p.m].idxAll.subarray(p.t0 * 3, (p.t0 + p.nt) * 3), g = new T.BufferGeometry();
    g.setAttribute('position', src.getAttribute('position')); g.setAttribute('normal', src.getAttribute('normal'));
    g.setIndex(new T.BufferAttribute(new Uint32Array(ix), 1)); return g;
  }
  function clearMarks() { marked.forEach(function (h) { h.parent.remove(h); h.geometry.dispose(); }); marked = []; dirty = true; }
  function mark(list, solid) {
    clearMarks();
    list.forEach(function (p) {
      var me = meshes[p.m], h = new T.Mesh(subGeom(p), solid ? hlSolid : hlSoft); h.renderOrder = 10;
      GG[me.sub][me.group].add(h); marked.push(h);
    });
  }
  function ghost(on) {
    ghosted = on;
    meshes.forEach(function (m) {
      m.mat.transparent = on || m.alpha < 0.99; m.mat.opacity = on ? 0.1 : (m.alpha < 0.99 ? Math.max(0.35, m.alpha) : 1);
      m.mat.depthWrite = !on && m.alpha >= 0.99; m.mat.needsUpdate = true;
    });
    dirty = true;
  }
  function same(p) { return p.k ? byMark[p.k] : p.g !== undefined ? byG[p.g] : [p]; }   // a vendor model in several colours is several pieces with one g

  // ---- picking ----
  var ray = new T.Raycaster(), ndc = new T.Vector2();
  function pick(e) {
    if (MODE !== 'explore') return;
    var r = canvas.getBoundingClientRect(); ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    var hits = ray.intersectObjects(meshes.filter(function (m) { return S[m.sub].visible; }).map(function (m) { return m.mesh; }), false);
    if (!hits.length) return choose(null);
    var me = meshes[hits[0].object.userData.mi], f = hits[0].faceIndex, P = me.parts, lo = 0, hi = P.length - 1;
    while (lo < hi) { var mid = (lo + hi + 1) >> 1; if (P[mid].t0 <= f) lo = mid; else hi = mid - 1; }
    choose(P[lo]);
  }
  function choose(p) {
    chosen = p;
    if (p) mark(same(p), false); else clearMarks();
    var box = $('picked'); if (!box) return;
    if (!p) { box.innerHTML = '<p class="muted">Click or tap any part to see what it is. Made parts link to the page that shows how to make them.</p>'; return; }
    var sub = subs[meshes[p.m].sub], h = '<span class="tag" style="--c:' + SUB_COL[meshes[p.m].sub] + '">' + esc(sub) + '</span>';
    if (p.k && made[p.k]) {
      var d = made[p.k];
      h += '<h3>' + esc(p.k) + ' ' + esc(d.name) + '</h3><p>' + esc(p.l) + '</p>' +
        '<p class="facts">Made on: <b>' + esc(d.machine) + '</b>' + (d.qty ? ' · Make <b>' + esc(d.qty) + '</b>' : '') + '</p>' +
        '<p><a class="go" target="_top" href="../parts/' + encodeURIComponent(d.slug) + '/">How to make ' + esc(p.k) + '</a></p>';
    } else h += '<h3>Bought part</h3><p>' + esc(p.l) + '</p>';
    box.innerHTML = h;
    var sel = $('find'); if (sel) sel.value = p.k && made[p.k] ? p.k : '';
  }

  // ---- one part: alone, or in place on the robot ----
  function showAlone(k) {
    var p = byMark[k][0], me = meshes[p.m];
    S.forEach(function (s) { s.visible = false; }); floor.visible = grid.visible = false; clearMarks(); ghost(false);
    if (solo) { root.remove(solo); }
    var g = subGeom(p), col = me.base.clone();
    if (col.r + col.g + col.b < 0.25) col.setRGB(0.25, 0.27, 0.3);   // near-black parts would vanish on the dark theme
    solo = new T.Group();
    solo.add(new T.Mesh(g, new T.MeshStandardMaterial({ color: col, roughness: 0.6, metalness: 0.15, side: T.DoubleSide })));
    var edges = new T.LineSegments(new T.EdgesGeometry(g, 28), new T.LineBasicMaterial({ color: 0x0f2029, transparent: true, opacity: 0.55 }));
    solo.add(edges); root.add(solo);
    lim.dmin = Math.max(1.5, p.r * 1.6); lim.dmax = Math.max(40, p.r * 12); lim.emin = -1.45; lim.ymin = -200; lim.ymax = 200;
    camera.near = Math.max(0.05, p.r / 20); camera.updateProjectionMatrix();
    setView(38, 22, Math.max(3, p.r * 3.7), toThree(p.c), 350);
  }
  function showInPlace(k) {
    var list = byMark[k], p = list[0];
    if (solo) { root.remove(solo); solo = null; }
    S.forEach(function (s) { s.visible = true; }); floor.visible = grid.visible = true; ghost(true); mark(list, true);
    lim.dmin = 25; lim.dmax = 420; lim.emin = -0.05; lim.ymin = 0; lim.ymax = 110; camera.near = 1; camera.updateProjectionMatrix();
    var c = [0, 0, 0]; list.forEach(function (q) { c[0] += q.c[0] / list.length; c[1] += q.c[1] / list.length; c[2] += q.c[2] / list.length; });
    var side = c[1] < -1 ? -38 : 38;   // look from the side the part is on
    setView(c[0] < -4 ? 180 - side : side, 20, 140, new T.Vector3(0, 20, 0), 500);
  }

  // ---- load ----
  function load() {
    return Promise.all([fetch('robot.json').then(function (r) { return r.json(); }), fetch('robot.bin').then(function (r) { return r.arrayBuffer(); })]).then(function (res) {
      var J = res[0], buf = res[1], q = J.q;
      subs = J.subs; made = J.made;
      subs.forEach(function (name, i) {
        var s = new T.Group(); S.push(s); root.add(s); var G = {}; GG.push(G);
        GROUPS.forEach(function (g) { var o = new T.Group(); o.matrixAutoUpdate = false; G[g] = o; s.add(o); });
      });
      var P = new Int16Array(buf, 0, J.idx_offset / 2);
      J.meshes.forEach(function (m, mi) {
        var pos = new Float32Array(m.nv * 3); for (var k = 0; k < m.nv * 3; k++) pos[k] = P[m.v0 * 3 + k] * q;
        var idx = m.w === 2 ? new Uint16Array(buf, J.idx_offset + m.i0, m.ni) : new Uint32Array(buf, J.idx_offset + m.i0, m.ni);
        var g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(pos, 3));
        g.setIndex(new T.BufferAttribute(idx, 1)); g.computeVertexNormals();
        var col = new T.Color(m.color[0], m.color[1], m.color[2]).convertSRGBToLinear(), a = m.color[3];
        var mat = new T.MeshStandardMaterial({ color: col, metalness: 0.15, roughness: 0.62, transparent: a < 0.99, opacity: a < 0.99 ? Math.max(0.35, a) : 1, side: a < 0.99 ? T.DoubleSide : T.FrontSide, depthWrite: a >= 0.99 });
        var mesh = new T.Mesh(g, mat); mesh.userData.mi = mi; GG[m.sub][m.group].add(mesh);
        meshes.push({ sub: m.sub, group: m.group, geom: g, mesh: mesh, mat: mat, base: col.clone(), alpha: a, parts: [], idxAll: idx });
        var s = samples[m.group] || (samples[m.group] = []); for (var k2 = 0; k2 < m.nv; k2 += 7) s.push(pos[k2 * 3], pos[k2 * 3 + 1], pos[k2 * 3 + 2]);
      });
      J.parts.forEach(function (p, i) { p.i = i; parts.push(p); meshes[p.m].parts.push(p); if (p.k) (byMark[p.k] || (byMark[p.k] = [])).push(p); if (p.g !== undefined) (byG[p.g] || (byG[p.g] = [])).push(p); });
      apply();
      return J;
    });
  }

  function resize() {
    var w = canvas.clientWidth, h = canvas.clientHeight; if (!w || !h) return;
    var pr = renderer.getPixelRatio();
    if (canvas.width !== Math.round(w * pr) || canvas.height !== Math.round(h * pr)) { renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); dirty = true; }
  }
  function frame(now) { requestAnimationFrame(frame); resize(); if (anim) anim(now); if (dirty) { renderer.render(scene, camera); dirty = false; } }
  if ('IntersectionObserver' in window) new IntersectionObserver(function () { dirty = true; }).observe(canvas);
  if (window.MutationObserver) new MutationObserver(retheme).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  if (window.matchMedia) { var mq = window.matchMedia('(prefers-color-scheme: dark)'); if (mq.addEventListener) mq.addEventListener('change', retheme); }

  function pose(p, ms) {
    var s0 = { c: state.c, th: state.th, psi: state.psi, tray: state.tray }, t0 = performance.now(), dur = ms || 900;
    function step(now) { var k = Math.min(1, (now - t0) / dur); k = k * k * (3 - 2 * k);
      ['c', 'th', 'psi', 'tray'].forEach(function (key) { if (p[key] !== undefined) state[key] = s0[key] + (p[key] - s0[key]) * k; });
      apply(); if (k < 1) requestAnimationFrame(step); }
    requestAnimationFrame(step);
  }

  // ---- what each mode shows around the model ----
  var readout = $('readout');
  function fmtDeg(x) { return (x < -0.05 ? '−' : '') + Math.abs(x).toFixed(0) + '°'; }
  function onChange() {
    if (!meshes.length) return;
    var m = measure();
    if (readout) readout.innerHTML = '<span>Wrist pivot <b>' + m.pivot.toFixed(1) + ' in</b></span><span>Tallest point <b>' + m.top.toFixed(1) + ' in</b></span><span>Past the frame <b>' + m.reach.toFixed(1) + ' in</b></span>';
    if (MODE === 'keepout') paintKeep();
  }

  var POSES = {
    stow: { c: 0, th: -90, psi: 90, tray: 0, t: 'Stowed', d: 'How the robot starts a match: carriage down, wrist hanging between the rails, fork up, funnel closed. Everything is inside the frame.' },
    intake: { c: 1.25, th: -35, psi: 90, tray: 0, t: 'Station', d: 'Carriage up 1.25 in, wrist at −35° under the funnel. Coral slides down the tray between the rails into the coral rollers.' },
    l2: { c: 17.5, th: -35, psi: 90, tray: 0, t: 'L2', d: 'Wrist pivot at 42.0 in, wrist at −35° to match the branch, bumper on the reef.' },
    l3: { c: 33.3, th: -35, psi: 90, tray: 0, t: 'L3', d: 'Wrist pivot at 57.8 in, same angle. All three stages are moving now.' },
    l4: { c: 66, th: -52.8, psi: 90, tray: 0, t: 'L4', d: 'All the travel: pivot at 90.5 in, wrist about 53° below level onto the vertical branch tip.' },
    lowalgae: { c: 8.8, th: 46, psi: 90, tray: 0, t: 'Low algae', d: 'Wrist at +46°, pivot at 33.3 in: the claw reaches the ball on the lower reef level.' },
    algae: { c: 24.6, th: 46, psi: 90, tray: 0, t: 'High algae', d: 'Wrist at +46°, pivot at 49.1 in: the claw reaches the ball on the upper reef level.' },
    net: { c: 66, th: 75, psi: 90, tray: 0, t: 'Net', d: 'Full height, wrist at +75°. Reverse both claw rollers to throw the ball into the net.' },
    climb0: { c: 1.25, th: 0, psi: -2, tray: 90, t: 'Climb ready', d: 'Funnel tray swung open, pawls lifted and the fork let down level behind the robot. Back onto the cage.' },
    climb1: { c: 1.25, th: 0, psi: 88, tray: 90, t: 'Climbed', d: 'Both climber motors wind the ropes until the fork is back up with the cage across the robot. The pawls hold it after the robot is disabled.' }
  };

  function setupExplore(J) {
    var pb = $('poses'), pt = $('posetext');
    pb.innerHTML = Object.keys(POSES).map(function (k) { return '<button type="button" data-pose="' + k + '" aria-pressed="' + (k === 'stow') + '">' + esc(POSES[k].t) + '</button>'; }).join('');
    pt.textContent = POSES.stow.d;
    pb.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return; var p = POSES[b.getAttribute('data-pose')];
      Array.prototype.forEach.call(pb.children, function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      pt.textContent = p.d; pose(p);
      setView(p.tray > 45 ? 145 : 38, 16, (p.c > 40 ? 200 : 125) + 90 * apart, new T.Vector3(0, Math.min(62, 22 + p.c * 0.55), 0));
    });
    var sb = $('subs');
    sb.innerHTML = subs.map(function (s, i) { return '<label><input type="checkbox" checked data-sub="' + i + '"><i style="background:' + SUB_COL[i] + '"></i>' + esc(s) + '</label>'; }).join('');
    sb.addEventListener('change', function (e) { var i = +e.target.getAttribute('data-sub'); S[i].visible = e.target.checked; if (chosen && meshes[chosen.m].sub === i && !e.target.checked) choose(null); dirty = true; });
    $('apart').addEventListener('input', function (e) { apart = +e.target.value; apply(); dist = Math.max(dist, 125 + 110 * apart); placeCam(); });
    $('bysub').addEventListener('change', function (e) {
      meshes.forEach(function (m) { if (e.target.checked) m.mat.color.set(SUB_COL[m.sub]).convertSRGBToLinear(); else m.mat.color.copy(m.base); });
      document.body.classList.toggle('bysub', e.target.checked); dirty = true;
    });
    var sel = $('find'), h = '<option value="">Find a made part…</option>';
    subs.forEach(function (s) {
      var ks = Object.keys(made).filter(function (k) { return made[k].sub === s; }).sort();
      if (ks.length) h += '<optgroup label="' + esc(s) + '">' + ks.map(function (k) { return '<option value="' + esc(k) + '">' + esc(k + ' ' + made[k].name).slice(0, 60) + '</option>'; }).join('') + '</optgroup>';
    });
    sel.innerHTML = h;
    sel.addEventListener('change', function () {
      if (!sel.value) return choose(null);
      var p = byMark[sel.value][0]; S[meshes[p.m].sub].visible = true;
      var cb = sb.querySelector('[data-sub="' + meshes[p.m].sub + '"]'); if (cb) cb.checked = true;
      choose(p);
    });
    choose(null);
    hint.textContent = J.parts.length + ' parts. Drag to turn, pinch or scroll to zoom, tap a part to name it.';
    // ?pose=key opens in that pose; ?sub=N opens on one subsystem with the rest hidden
    var open = POSES[qs.get('pose')];
    if (open) { var ob = pb.querySelector('[data-pose="' + qs.get('pose') + '"]'); if (ob) ob.click(); }
    var only = qs.get('sub');
    if (only !== null && subs[+only]) {
      only = +only; var lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9], n = 0;
      subs.forEach(function (_, i) { S[i].visible = i === only; sb.querySelector('[data-sub="' + i + '"]').checked = i === only; });
      J.parts.forEach(function (q) { if (meshes[q.m].sub !== only) return; n++; for (var k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], q.c[k] - q.r); hi[k] = Math.max(hi[k], q.c[k] + q.r); } });
      var c = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2], r = Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) / 2;
      anim = null; tgt.copy(toThree(c)); dist = Math.max(lim.dmin, Math.min(170, r * 2.9)); az = (c[0] < -4 ? 142 : 38) * D2R; el = 18 * D2R; placeCam();
      hint.textContent = 'Showing only: ' + subs[only] + ' (' + n + ' parts). Tick the other subsystems below to bring them back.';
    }
  }

  function setupPart(J) {
    if (!PART || !byMark[PART]) { hint.textContent = 'This part is not in the 3D model.'; return; }
    var n = byMark[PART].length, btns = document.querySelectorAll('[data-show]');
    function show(which) {
      Array.prototype.forEach.call(btns, function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-show') === which ? 'true' : 'false'); });
      if (which === 'alone') { showAlone(PART); hint.textContent = 'The part on its own. Drag to turn it, pinch or scroll to zoom.'; }
      else { showInPlace(PART); hint.textContent = n > 1 ? 'All ' + n + ' of them, in orange, where they sit on the robot.' : 'In orange, where it sits on the robot.'; }
    }
    Array.prototype.forEach.call(btns, function (b) { b.addEventListener('click', function () { show(b.getAttribute('data-show')); }); });
    show(qs.get('show') === 'place' ? 'place' : 'alone');
  }

  // ---- keep-out: the table as a picture ----
  var chart = $('chart'), cx2 = chart && chart.getContext('2d'), HMAX = 30, CH = { l: 46, r: 12, t: 12, b: 38 };
  function chartXY(th, h) { var w = chart.clientWidth - CH.l - CH.r, hh = chart.clientHeight - CH.t - CH.b; return [CH.l + (th + 90) / 165 * w, CH.t + (1 - Math.min(h, HMAX) / HMAX) * hh]; }
  function paintKeep() {
    if (!cx2) return;
    var pr = Math.min(window.devicePixelRatio || 1, 2), W = chart.clientWidth, H = chart.clientHeight;
    if (chart.width !== Math.round(W * pr)) { chart.width = Math.round(W * pr); chart.height = Math.round(H * pr); }
    cx2.setTransform(pr, 0, 0, pr, 0, 0); cx2.clearRect(0, 0, W, H);
    var ink = css('--ink'), muted = css('--muted'), line = css('--line'), bad = css('--bad'), good = css('--good');
    var o = chartXY(-90, 0), e = chartXY(75, HMAX);
    cx2.fillStyle = css('--surface'); cx2.fillRect(o[0], e[1], e[0] - o[0], o[1] - e[1]);
    // the code's rule: shade what it will not allow
    cx2.fillStyle = bad; cx2.globalAlpha = 0.22;
    ZONES.forEach(function (z) {
      if (z[0] >= HMAX) return; var a = chartXY(-90, Math.min(z[1], HMAX)), b = chartXY(z[2], z[0]);
      if (z[2] > -90) cx2.fillRect(a[0], a[1], b[0] - a[0], b[1] - a[1]);
      if (z[3] < 75) { var c = chartXY(z[3], Math.min(z[1], HMAX)), d = chartXY(75, z[0]); cx2.fillRect(c[0] + 3, c[1], d[0] - c[0] - 3, d[1] - c[1]); }
    });
    cx2.globalAlpha = 1;
    // axes
    cx2.strokeStyle = line; cx2.lineWidth = 1; cx2.font = '12px ' + css('--font-body'); cx2.fillStyle = muted; cx2.textAlign = 'center'; cx2.textBaseline = 'top';
    [-90, -60, -30, 0, 30, 60].forEach(function (a) { var p = chartXY(a, 0); cx2.beginPath(); cx2.moveTo(p[0], o[1]); cx2.lineTo(p[0], e[1]); cx2.stroke(); cx2.fillText((a < 0 ? '−' : '') + Math.abs(a) + '°', p[0], o[1] + 5); });
    cx2.fillText('Wrist angle (−90° hangs straight down, 0° is level)', (o[0] + e[0]) / 2, o[1] + 21);
    cx2.textAlign = 'right'; cx2.textBaseline = 'middle';
    [0, 5, 10, 15, 20, 25, 30].forEach(function (h) { var p = chartXY(-90, h); cx2.beginPath(); cx2.moveTo(o[0], p[1]); cx2.lineTo(e[0], p[1]); cx2.stroke(); cx2.fillText(h, o[0] - 6, p[1]); });
    cx2.save(); cx2.translate(12, (o[1] + e[1]) / 2); cx2.rotate(-Math.PI / 2); cx2.textAlign = 'center'; cx2.fillText('Carriage height, in', 0, 0); cx2.restore();
    // every pose the CAD clash check tested, inside the chart
    GH.forEach(function (h, i) { if (h > HMAX) return; GT.forEach(function (th, j) {
      var p = chartXY(th, h); cx2.beginPath(); cx2.arc(p[0], p[1], 3.2, 0, 7); cx2.fillStyle = GRID[i][j] ? good : bad; cx2.fill();
      if (!GRID[i][j]) { cx2.strokeStyle = bad; cx2.lineWidth = 1.5; cx2.beginPath(); cx2.moveTo(p[0] - 5, p[1] - 5); cx2.lineTo(p[0] + 5, p[1] + 5); cx2.moveTo(p[0] + 5, p[1] - 5); cx2.lineTo(p[0] - 5, p[1] + 5); cx2.stroke(); }
    }); });
    // where the robot is now
    var ok = allowed(state.c, state.th), m = chartXY(state.th, state.c);
    cx2.beginPath(); cx2.arc(m[0], m[1], 8, 0, 7); cx2.fillStyle = css('--surface'); cx2.fill(); cx2.lineWidth = 3; cx2.strokeStyle = ink; cx2.stroke();
    cx2.beginPath(); cx2.arc(m[0], m[1], 3, 0, 7); cx2.fillStyle = ink; cx2.fill();
    if (state.c > HMAX) { cx2.fillStyle = muted; cx2.textAlign = 'left'; cx2.textBaseline = 'bottom'; cx2.fillText('↑ ' + state.c.toFixed(0) + ' in: above this chart, all clear', Math.min(m[0] + 12, e[0] - 190), m[1] + 18); }
    var z = zoneAt(state.c), st = $('keepstate');
    st.className = 'keep ' + (ok ? 'ok' : 'bad');
    st.innerHTML = (ok ? '<b>The code allows this.</b> ' : '<b>The code blocks this.</b> Look at the model: the wrist is inside the elevator, the frame or the funnel. ') +
      'With the carriage at ' + state.c.toFixed(1) + ' in, the table row is ' + z[0] + ' to ' + z[1] + ' in: ' +
      (z[2] === z[3] ? 'the wrist must be stowed at ' + fmtDeg(z[2]) + '.' : z[2] === -90 ? 'any wrist angle.' : 'wrist at ' + fmtDeg(z[2]) + ' or higher.');
    $('v-c').textContent = state.c.toFixed(1) + ' in'; $('v-th').textContent = fmtDeg(state.th);
  }
  function setupKeep() {
    var sc = $('s-c'), sth = $('s-th');
    function set(c, th) { state.c = Math.max(0, Math.min(66, c)); state.th = Math.max(-90, Math.min(75, th)); sc.value = state.c; sth.value = state.th; apply(); }
    sc.addEventListener('input', function () { set(+sc.value, state.th); }); sth.addEventListener('input', function () { set(state.c, +sth.value); });
    function fromChart(e) {
      var r = chart.getBoundingClientRect(), w = r.width - CH.l - CH.r, hh = r.height - CH.t - CH.b;
      set(Math.round((1 - (e.clientY - r.top - CH.t) / hh) * HMAX * 4) / 4, Math.round(-90 + (e.clientX - r.left - CH.l) / w * 165));
    }
    var down = false;
    chart.addEventListener('pointerdown', function (e) { down = true; try { chart.setPointerCapture(e.pointerId); } catch (x) {} fromChart(e); });
    chart.addEventListener('pointermove', function (e) { if (down) fromChart(e); });
    chart.addEventListener('pointerup', function () { down = false; }); chart.addEventListener('pointercancel', function () { down = false; });
    Array.prototype.forEach.call(document.querySelectorAll('[data-try]'), function (b) { b.addEventListener('click', function () { var v = b.getAttribute('data-try').split(','); pose({ c: +v[0], th: +v[1] }, 700); setTimeout(function () { sc.value = +v[0]; sth.value = +v[1]; }, 750); }); });
    window.addEventListener('resize', paintKeep);
    az = 90 * D2R; el = 6 * D2R; dist = 125; tgt.set(2, 22, 0); placeCam();
    set(8, -30);
    hint.textContent = 'Side view. Drag the dot on the chart, or use the sliders.';
  }

  // ---- assemble: one mechanism built up step by step ----
  var FAST_NEW = new T.MeshBasicMaterial({ color: 0xe6007e, depthTest: false, transparent: true, opacity: 0.95 });
  var FAST_OLD = new T.MeshStandardMaterial({ color: new T.Color('#2b2f36').convertSRGBToLinear(), roughness: 0.5, metalness: 0.4 });
  function setupAssemble(J) {
    var name = qs.get('set') || 'robot';
    Promise.all([fetch('assembly.json').then(function (r) { return r.json(); }), fetch('fasteners.json').then(function (r) { return r.json(); })]).then(function (res) {
      var A = res[0][name], F = res[1]; if (!A) { hint.textContent = 'No steps found for this mechanism.'; return; }
      var steps = A.steps, cur = -1, title = $('as-title'), count = $('as-count'), what = $('as-what');
      // which step first shows each part and each fastener (-1: there from the start, undefined: never)
      var partStep = {}, fastStep = {};
      A.base.forEach(function (i) { partStep[i] = -1; }); A.basef.forEach(function (i) { fastStep[i] = -1; });
      steps.forEach(function (st, n) { st.p.forEach(function (i) { partStep[i] = n; }); st.f.forEach(function (i) { fastStep[i] = n; }); });
      // a small cylinder for every fastener, riding with the first part it joins
      var unit = new T.CylinderGeometry(1, 1, 1, 10), up = new T.Vector3(0, 1, 0), fmesh = {};
      Object.keys(fastStep).forEach(function (k) {
        var it = F.items[k], host = meshes[parts[it[9][0]].m], len = it[7], r = Math.max(0.07, it[8] * 0.7);
        var m = new T.Mesh(unit, FAST_OLD), d = new T.Vector3(it[4], it[5], it[6]);
        m.position.set(it[1] + it[4] * len / 2, it[2] + it[5] * len / 2, it[3] + it[6] * len / 2);
        m.quaternion.setFromUnitVectors(up, d); m.userData = { r: r, len: len }; m.scale.set(r, len, r); m.visible = false;
        GG[host.sub][host.group].add(m); fmesh[k] = m;
      });
      function centreOf(list, flist) {
        var lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9], v = new T.Vector3();
        function grow(x, y, z, r, g) { v.set(x, y, z).applyMatrix4(M[g]); [v.x, v.y, v.z].forEach(function (c, k) { lo[k] = Math.min(lo[k], c - r); hi[k] = Math.max(hi[k], c + r); }); }
        list.forEach(function (i) { var q = parts[i]; grow(q.c[0], q.c[1], q.c[2], q.r, meshes[q.m].group); });
        flist.forEach(function (k) { var it = F.items[k]; grow(it[1], it[2], it[3], 0.4, meshes[parts[it[9][0]].m].group); });
        if (lo[0] > hi[0]) return null;
        return { c: [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2], r: Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) / 2 };
      }
      function plural(n, w) { return n + ' ' + w + (n === 1 ? '' : 's'); }
      function show(n, quiet) {
        n = Math.max(0, Math.min(steps.length - 1, n)); if (n === cur) return; cur = n; var st = steps[n];
        var p = st.pose || {}; state.c = p.c || 0; state.th = p.th === undefined ? -90 : p.th; state.psi = p.psi === undefined ? 90 : p.psi; state.tray = p.tray || 0; apply();
        meshes.forEach(function (m) {
          var cnt = 0; m.parts.forEach(function (q) { if (partStep[q.i] !== undefined && partStep[q.i] <= n) cnt += q.nt * 3; });
          if (!cnt) { m.mesh.visible = false; return; }
          var arr = new m.idxAll.constructor(cnt), o = 0;
          m.parts.forEach(function (q) { if (partStep[q.i] !== undefined && partStep[q.i] <= n) { arr.set(m.idxAll.subarray(q.t0 * 3, (q.t0 + q.nt) * 3), o); o += q.nt * 3; } });
          m.geom.setIndex(new T.BufferAttribute(arr, 1)); m.mesh.visible = true;
        });
        mark(st.p.map(function (i) { return parts[i]; }), true);
        Object.keys(fmesh).forEach(function (k) {
          var m = fmesh[k], s = fastStep[k], on = s <= n, now = s === n, r = m.userData.r * (now ? 1.7 : 1);
          m.visible = on; m.material = now ? FAST_NEW : FAST_OLD; m.renderOrder = now ? 20 : 0; m.scale.set(r, m.userData.len + (now ? 0.12 : 0), r);
        });
        var box = centreOf(st.p, st.f) || centreOf(A.base.concat.apply(A.base, steps.slice(0, n + 1).map(function (x) { return x.p; })), []);
        if (box) {
          var side = box.c[1] > 2 ? -1 : 1, back = box.c[0] < -5;
          setView(side * (back ? 142 : 38), 24, Math.max(22, Math.min(170, box.r * 3.4)), toThree(box.c), 500);
        }
        title.textContent = 'Step ' + (n + 1) + ' of ' + steps.length + ': ' + st.t;
        var seen = {}, np = 0; st.p.forEach(function (i) { var g = parts[i].g; if (g === undefined) np++; else if (!seen[g]) { seen[g] = 1; np++; } });
        var bits = []; if (np) bits.push(plural(np, 'part') + ' in orange');
        var nf = 0; Object.keys(st.fam || {}).forEach(function (k) { nf += st.fam[k]; });
        if (nf) bits.push(plural(nf, 'fastener') + ' in pink');
        what.textContent = bits.length ? 'New at this step: ' + bits.join(', ') + '.' : 'Nothing new to fit at this step.';
        count.textContent = (n + 1) + ' / ' + steps.length;
        $('as-prev').disabled = n === 0; $('as-next').disabled = n === steps.length - 1;
        if (!quiet && window.parent !== window) window.parent.postMessage({ type: 'assembly-step', set: name, i: n }, '*');
      }
      $('as-prev').addEventListener('click', function () { show(cur - 1); });
      $('as-next').addEventListener('click', function () { show(cur + 1); });
      window.addEventListener('message', function (e) { var d = e.data; if (d && d.type === 'assembly-show' && d.set === name) show(+d.i, true); });
      lim.dmin = 6; lim.emin = -0.6; camera.near = 0.5; camera.updateProjectionMatrix();
      hint.textContent = 'Drag to turn, pinch or scroll to zoom.';
      show(+qs.get('step') || 0, true);
      if (window.parent !== window) window.parent.postMessage({ type: 'assembly-ready', set: name }, '*');
    }).catch(function () { hint.textContent = 'The assembly steps did not load.'; });
  }

  // ---- replay: the page that embeds this one sends each pose ----
  function setupReplay() {
    window.addEventListener('message', function (e) {
      var d = e.data; if (!d || d.type !== 'pose') return;
      state.c = +d.c || 0; state.th = d.th === undefined ? -90 : +d.th; state.psi = d.psi === undefined ? 90 : +d.psi; state.tray = +d.tray || 0; apply();
      if (d.view === 'climb' && setupReplay.v !== 'climb') { setupReplay.v = 'climb'; setView(150, 14, 135, new T.Vector3(-4, 20, 0), 600); }
      if (d.view === 'auto' && setupReplay.v !== 'auto') { setupReplay.v = 'auto'; setView(52, 12, 215, new T.Vector3(0, 48, 0), 600); }
    });
    az = 52 * D2R; el = 12 * D2R; dist = 215; tgt.set(0, 48, 0); placeCam();
    hint.textContent = 'The robot at this moment in the run. Drag to turn it.';
    if (window.parent !== window) window.parent.postMessage({ type: 'robot-viewer-ready' }, '*');
  }

  retheme(); placeCam(); requestAnimationFrame(frame);
  load().then(function (J) {
    document.body.classList.add('loaded');
    if (MODE === 'part') setupPart(J); else if (MODE === 'keepout') setupKeep(); else if (MODE === 'replay') setupReplay(); else if (MODE === 'assemble') setupAssemble(J); else setupExplore(J);
  }).catch(function () { hint.textContent = 'The model files did not load.'; });
})();
