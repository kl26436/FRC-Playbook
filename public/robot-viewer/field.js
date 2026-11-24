/* The blue half of the REEFSCAPE field for the replay view, built from simple shapes.
   Units are inches in field coordinates: X from the blue alliance wall toward red, Y to the left of a blue
   driver, Z up, origin at the blue corner on the scoring-table side (the same axes the robot code uses).
   Plan positions are the ones in src/assets/field-map.svg; the reef, station, net and cage sections are the
   ones tools/render/render_final.py uses for the ray-traced pictures. It is not the official field CAD.
   window.buildField(THREE, carpetMaterial) returns { group, tags, held, makeCoral, makeAlgae, ... }. */
(function () {
  'use strict';
  window.buildField = function (T, carpetMat) {
    var W = 317, LEN = 400;                       // field width, and how much of its length is drawn
    var REEF = [176.75, 158.5], APOTHEM = 32.75;  // reef centre, centre to a face
    var BRANCH_Y = 6.47;                          // a branch is this far to each side of its face's tag
    var REEF_TAGS = [18, 17, 22, 21, 20, 19];     // blue reef tag on face 0 (toward the blue wall), then round
    var g = new T.Group();
    var Z = new T.Vector3(0, 0, 1), Y = new T.Vector3(0, 1, 0);

    function mat(color, opt) {
      var o = { color: color, roughness: 0.75, metalness: 0 };
      for (var k in (opt || {})) o[k] = opt[k];
      var m = new T.MeshStandardMaterial(o); m.color.convertSRGBToLinear(); return m;
    }
    var M = {
      black: mat(0x202327, { roughness: 0.6 }), violet: mat(0x6a2f95, { roughness: 0.4 }), white: mat(0xf2f2ee, { roughness: 0.5 }),
      algae: mat(0x1fa390, { roughness: 0.55 }), alu: mat(0x9aa3ab, { roughness: 0.45, metalness: 0.6 }),
      plate: mat(0x7d858c, { roughness: 0.5, metalness: 0.5 }), blue: mat(0x1a48b8, { roughness: 0.45 }), red: mat(0xc23b33, { roughness: 0.45 }),
      tapeBlue: mat(0x2f62d8), tapeRed: mat(0xc23b33), tapeBlack: mat(0x101214), tapeWhite: mat(0xe8e8e4),
      clear: mat(0xcfe3ee, { transparent: true, opacity: 0.22, roughness: 0.2, depthWrite: false, side: T.DoubleSide }),
      net: mat(0xf4f4f0, { transparent: true, opacity: 0.4, depthWrite: false, side: T.DoubleSide }),
      tagOn: mat(0xffffff),
    };

    // ---- shapes, each added to a parent in that parent's own coordinates ----
    function box(parent, m, size, centre, rot) {
      var o = new T.Mesh(new T.BoxGeometry(size[0], size[1], size[2]), m);
      o.position.set(centre[0], centre[1], centre[2]); if (rot) o.rotation.set(rot[0], rot[1], rot[2]); parent.add(o); return o;
    }
    function tube(parent, m, a, b, r, seg) {
      var va = new T.Vector3(a[0], a[1], a[2]), vb = new T.Vector3(b[0], b[1], b[2]), d = vb.clone().sub(va);
      var o = new T.Mesh(new T.CylinderGeometry(r, r, d.length(), seg || 10), m);
      o.position.copy(va).add(vb).multiplyScalar(0.5); o.quaternion.setFromUnitVectors(Y, d.normalize()); parent.add(o); return o;
    }
    function ball(parent, m, centre, r) {
      var o = new T.Mesh(new T.SphereGeometry(r, 20, 14), m); o.position.set(centre[0], centre[1], centre[2]); parent.add(o); return o;
    }
    // A coral: 4.5 in pipe, 11.875 in long, standing along local Z.
    function makeCoral() {
      var o = new T.Mesh(new T.CylinderGeometry(2.25, 2.25, 11.875, 20, 1, true), M.coral || (M.coral = mat(0xf4f4f0, { roughness: 0.45, side: T.DoubleSide })));
      o.geometry.rotateX(Math.PI / 2); return o;
    }
    function makeAlgae() { return new T.Mesh(new T.SphereGeometry(8.125, 24, 16), M.algae); }
    // A frame standing at a point on the carpet and turned about Z: x is "forward", y is "left".
    function frame(x, y, angle) { var f = new T.Group(); f.position.set(x, y, 0); f.rotation.z = angle; g.add(f); return f; }
    function tape(a, b, m, wide) {
      var dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy);
      box(g, m, [len, wide || 2, 0.06], [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.04], [0, 0, Math.atan2(dy, dx)]);
    }
    function tagPanel(parent, x, z, facing) {       // a tag on a wall in the frame's YZ plane, facing along x
      box(parent, M.white, [0.25, 10.5, 10.5], [x, 0, z]);
      return box(parent, M.tapeBlack, [0.08, 8.125, 8.125], [x + facing * 0.16, 0, z]);
    }

    // ---- carpet and tape ----
    var carpet = new T.Mesh(new T.PlaneGeometry(LEN, W), carpetMat); carpet.position.set(LEN / 2, W / 2, 0); g.add(carpet);
    tape([297.5, 0], [297.5, W], M.tapeBlack);                           // starting line
    for (var k = 0; k < 6; k++) {                                        // the reef zone
      var a0 = (30 + 60 * k) * Math.PI / 180, a1 = (90 + 60 * k) * Math.PI / 180;
      tape([REEF[0] + 54 * Math.cos(a0), REEF[1] + 54 * Math.sin(a0)], [REEF[0] + 54 * Math.cos(a1), REEF[1] + 54 * Math.sin(a1)], M.tapeBlue);
    }
    [[158.5, 305, M.tapeBlue], [12, 158.5, M.tapeRed]].forEach(function (zn) {   // barge zones
      tape([322.44, zn[0]], [368.44, zn[0]], zn[2]); tape([322.44, zn[1]], [368.44, zn[1]], zn[2]);
      tape([322.44, zn[0]], [322.44, zn[1]], zn[2]); tape([368.44, zn[0]], [368.44, zn[1]], zn[2]);
    });

    // ---- the reef: six identical faces round a core ----
    var core = new T.Mesh(new T.CylinderGeometry(18.7, 18.7, 22.9, 6), M.black); core.geometry.rotateX(Math.PI / 2);
    core.position.set(REEF[0], REEF[1], 11.45); core.rotation.z = Math.PI / 6; g.add(core);
    var faces = [], tags = {}, reefAlgae = [];
    for (var f = 0; f < 6; f++) {
      var out = Math.PI + f * Math.PI / 3;                               // which way this face looks
      // the face's frame: x runs into the reef from the face, y to the left of a robot facing it
      var F = frame(REEF[0] + APOTHEM * Math.cos(out), REEF[1] + APOTHEM * Math.sin(out), out + Math.PI);
      faces.push(F);
      [[[0.5, 37.8, 17.88], [0.25, 0, 8.94]], [[16, 37.8, 0.5], [8.5, 0, 0.6]], [[0.25, 37.8, 10], [9.6, 0, 17.9]],
        [[7, 37.8, 0.25], [13.1, 0, 22.8]], [[9.2, 37.8, 11.6], [5.1, 0, 6.4]], [[7, 37.8, 21.9], [13.1, 0, 11.55]]]
        .forEach(function (b) { box(F, M.black, b[0], b[1]); });
      box(F, M.black, [9.6, 37.8, 0.25], [5.0, 0, 14.6], [0, 0.34, 0]);   // the sloped floor of the L1 trough
      tags[REEF_TAGS[f]] = { mesh: tagPanel(F, -0.14, 12.13, -1), frame: F, z: 12.13 };
      [BRANCH_Y, -BRANCH_Y].forEach(function (y) {
        tube(F, M.violet, [12.84, y, 0.63], [12.84, y, 53.8], 0.83);
        tube(F, M.violet, [12.84, y, 23.7], [1.61, y, 31.72], 0.83);
        tube(F, M.violet, [12.84, y, 39.55], [1.61, y, 47.59], 0.83);
        tube(F, M.violet, [12.84, y, 53.8], [1.18, y, 61.96], 0.83);
        tube(F, M.violet, [1.18, y, 61.96], [1.18, y, 71.87], 0.83);
        ball(F, M.violet, [12.84, y, 53.8], 0.83); ball(F, M.violet, [1.18, y, 61.96], 0.83);
      });
      // one algae a face to start with, high and low in turn
      reefAlgae.push(ball(F, M.algae, [6.65, 0, f % 2 === 0 ? 50.9 : 35.0], 8.125));
    }

    // ---- coral stations: a wall across each blue corner ----
    function station(mx, my, inward) {
      var S = frame(mx, my, inward);                                     // x points into the field
      box(S, M.plate, [0.5, 76, 37.5], [0, 0, 18.75]);
      box(S, M.clear, [0.3, 76, 31], [0, 0, 60]);
      box(S, M.black, [16.5, 76, 0.5], [-4.73, 0, 44.26], [0, 55 * Math.PI / 180, 0]);
      tagPanel(S, 0.35, 58.5, 1);
      [38, -38].forEach(function (y) { box(S, M.alu, [2, 2, 75.5], [-1, y, 37.75]); });
    }
    station(33.5, 25.8, Math.atan2(64.6, 47));                           // right station (low Y)
    station(33.5, 291.2, Math.atan2(-64.6, 47));                         // left station

    // ---- walls ----
    function wall(a, b, height, top) {
      var dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy), ang = Math.atan2(dy, dx), c = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
      box(g, M.clear, [len, 0.4, height], [c[0], c[1], height / 2], [0, 0, ang]);
      box(g, top, [len, 1.5, 1.5], [c[0], c[1], height], [0, 0, ang]);
    }
    wall([0, 49.3], [0, 267.7], 78, M.blue);                             // blue alliance wall
    wall([65.8, W], [LEN, W], 20, M.alu);                                // guardrails
    wall([65.8, 0], [221.7, 0], 20, M.alu); wall([249.7, 0], [LEN, 0], 20, M.alu);

    // ---- processor, in the gap in the scoring-table rail ----
    var P = frame(235.7, 0, Math.PI / 2);                                // x points into the field
    box(P, M.black, [15, 28, 7], [-7.5, 0, 3.5]); box(P, M.black, [15, 28, 6], [-7.5, 0, 27]);
    [13, -13].forEach(function (y) { box(P, M.black, [15, 2, 30], [-7.5, y, 15]); });
    box(P, M.black, [0.5, 28, 30], [-14.75, 0, 15]);
    tagPanel(P, 0.2, 38, 1); box(P, M.black, [1, 14, 14], [-0.5, 0, 37]);

    // ---- barge: a truss across the field, the cages hanging from it and a net each side ----
    var BX = 345.44;
    box(g, M.alu, [12, W + 24, 12], [BX, W / 2, 68]);
    [-6, W + 6].forEach(function (y) { box(g, M.alu, [12, 12, 74], [BX, y, 37]); });
    function cage(y, m) {
      var C = frame(BX, y, 0);
      [[1, 1], [1, -1], [-1, 1], [-1, -1]].forEach(function (s) { tube(C, m, [s[0] * 3.03, s[1] * 3.03, 3.5], [s[0] * 3.03, s[1] * 3.03, 27.5], 0.66, 8); });
      box(C, m, [6.75, 6.75, 0.2], [0, 0, 3.6]); box(C, m, [6.75, 6.75, 0.2], [0, 0, 27.4]);
      tube(C, M.alu, [0, 0, 27.5], [0, 0, 62], 0.25, 6);
    }
    [200.0, 242.9, 285.9].forEach(function (y) { cage(y, M.blue); });
    [117.0, 74.1, 31.1].forEach(function (y) { cage(y, M.red); });
    function net(y0, y1, rim) {
      var len = y1 - y0, geo = new T.PlaneGeometry(48, len, 12, 1), p = geo.attributes.position;
      for (var i = 0; i < p.count; i++) { var u = p.getX(i) / 24; p.setZ(i, -12.5 * (1 - u * u)); }
      geo.computeVertexNormals();
      var n = new T.Mesh(geo, M.net); n.position.set(BX, (y0 + y1) / 2, 88.5); g.add(n);
      [-24, 24].forEach(function (dx) {
        tube(g, rim, [BX + dx, y0, 88.5], [BX + dx, y1, 88.5], 0.7, 8);
        [y0, y1].forEach(function (y) { tube(g, M.alu, [BX + dx * 0.25, y, 74], [BX + dx, y, 88.5], 0.5, 6); });
      });
    }
    net(164.5, 311, M.blue); net(6, 152.5, M.red);

    // ---- the three coral standing on their marks, each with an algae on top ----
    [86.5, 158.5, 230.5].forEach(function (y) {
      var c = makeCoral(); c.position.set(48, y, 5.94); g.add(c);
      ball(g, M.algae, [48, y, 19.7], 8.125);
    });

    // ---- where a scored coral sits, in its face's frame ----
    function scoredAt(branch, level) {
      var i = 'ABCDEFGHIJKL'.indexOf(branch); if (i < 0) return null;
      var c = makeCoral(), y = i % 2 === 0 ? BRANCH_Y : -BRANCH_Y, tilt = -Math.atan2(8.02, 11.23);
      if (level === 'L4') c.position.set(1.18, y, 66.4);
      else if (level === 'L3') { c.position.set(5.7, y, 44.7); c.rotation.y = -Math.PI / 2 - tilt; }
      else if (level === 'L2') { c.position.set(5.7, y, 28.8); c.rotation.y = -Math.PI / 2 - tilt; }
      else { c.position.set(5, y, 17.6); c.rotation.x = Math.PI / 2; }
      faces[Math.floor(i / 2)].add(c); return c;
    }
    // The face nearest a point on the carpet: used to say which reef algae a robot just took.
    function nearestFace(x, y) {
      var best = 0, d = 1e9;
      for (var f = 0; f < 6; f++) {
        var out = Math.PI + f * Math.PI / 3, e = Math.hypot(x - REEF[0] - APOTHEM * Math.cos(out), y - REEF[1] - APOTHEM * Math.sin(out));
        if (e < d) { d = e; best = f; }
      }
      return best;
    }
    return { group: g, tags: tags, reefAlgae: reefAlgae, scoredAt: scoredAt, nearestFace: nearestFace, makeCoral: makeCoral, makeAlgae: makeAlgae,
      mat: mat, M: M, netX: BX, netZ: 80, Z: Z };
  };
})();
