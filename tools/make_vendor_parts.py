"""Place the real vendor models on the robot, in place of the outline shapes the CAD mesh export used.

    python3 tools/make_vendor_parts.py <folder of tessellated .npz> <folder of vendor .step> <CAD source folder> <out.npz> [robotA_mesh.json]

Each vendor file is tessellated once by vendor_tessellate.py, in its own axes. This script moves each to where it sits:
- Swerve modules and their motors: the same transforms the CAD source uses (assembly/vendor_place.py, swerve()).
- Electronics: the same method as the CAD source (vendor_place.py, electronics()): turn the vendor model each way
  that fills the stand-in box, and keep the way that puts the vendor's mounting holes on the holes we drill.
- Camera: on the tower's back plate, pitched up, as vendor_place.py limelight().
The result lists, for each placed model, the stand-in parts it replaces (by a pattern on their labels).
make_viewer_data.py --vendor=<out.npz> then swaps them in.
Needs build123d and the CAD source's common/layout.py.
"""
import sys, os, json, math, itertools, base64
import numpy as np

NPZ, STEPS, CAD, OUT = sys.argv[1:5]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(CAD, 'common'))
import layout as LAY
from build123d import import_step, GeomType, Location, Plane, Pos

SRC = sys.argv[5] if len(sys.argv) > 5 else '/home/claude/gen/r33/robotA_mesh_rev3.3.json'
J = json.load(open(SRC)); raw = base64.b64decode(J['bin_b64'])
POS = np.frombuffer(raw, dtype=np.int16, count=J['pos_bytes'] // 2).reshape(-1, 3).astype(np.float64) * J['q']
IDX = np.frombuffer(raw, dtype=np.uint32, offset=J['idx_offset'])


def standin_box(prefix):
    """Bounding box and label of the stand-in part whose label starts with prefix."""
    for p in J['parts']:
        if p['label'].startswith(prefix):
            m = J['meshes'][p['mesh']]
            v = POS[IDX[m['i0'] + p['t0'] * 3: m['i0'] + (p['t0'] + p['nt']) * 3].astype(np.int64) + m['v0']]
            return v.min(axis=0), v.max(axis=0), p['label']
    raise KeyError(prefix)


def load(name):
    d = np.load(os.path.join(NPZ, name + '.npz'))
    return [(d[f'v{k[1:]}'].astype(np.float64), d[f't{k[1:]}'], tuple(d[f'c{k[1:]}'])) for k in d.files if k[0] == 'v']


def rot(axis, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg)); M = np.eye(4)
    i, j = {'x': (1, 2), 'y': (2, 0), 'z': (0, 1)}[axis]; M[i, i] = c; M[i, j] = -s; M[j, i] = s; M[j, j] = c
    return M


def move(x, y, z): M = np.eye(4); M[:3, 3] = (x, y, z); return M
def frame(origin, z, x):
    z = np.array(z, float); z /= np.linalg.norm(z); x = np.array(x, float); x /= np.linalg.norm(x); y = np.cross(z, x)
    M = np.eye(4); M[:3, 0] = x; M[:3, 1] = y; M[:3, 2] = z; M[:3, 3] = origin; return M
def loc_matrix(loc):
    t = loc.wrapped.Transformation(); return np.array([[t.Value(i, j) for j in (1, 2, 3, 4)] for i in (1, 2, 3)] + [[0, 0, 0, 1]])


placed = []          # (label, replaces pattern, subsystem, colour, vertices, triangles)
def place(name, M, label, replaces, sub, tint=None):
    for v, t, c in load(name):
        w = (np.c_[v, np.ones(len(v))] @ M.T)[:, :3]
        if np.linalg.det(M[:3, :3]) < 0: t = t[:, ::-1]
        placed.append((label, replaces, sub, tint or c, w, t))

# ---- swerve modules, each with a drive and a steer motor ----
HALF = 14.0
MOTORS = [((-6.25, 4.688, -2.22), (0, 0, -1), 'drive'), ((-2.22, 4.688, -6.25), (-1, 0, 0), 'steer')]
for tag, ang in (('FR', 0), ('FL', 90), ('RL', 180), ('RR', 270)):
    T = rot('z', ang) @ move(HALF, -HALF, 0) @ rot('x', 90)
    place('mk4i', T, f'MK4i swerve module, SDS (vendor model) [{tag}]', r'^MK4i .*\[%s\]$' % tag, 0)
    for face, bulge, what in MOTORS:
        z = np.array((0, 1, 0), float); y = -np.array(bulge, float); x = np.cross(y, z)
        place('WCP-0940', T @ frame(np.array(face) - z * 1.23, z, x), f'MK4i {what} motor, Kraken X60 (WCP-0940, vendor model) [{tag}]', None, 0, (0.15, 0.15, 0.17))

# ---- electronics: fill the stand-in box, then match the mounting holes ----
def rotations():
    dirs = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    for ex in dirs:
        for ey in dirs:
            if sum(a * b for a, b in zip(ex, ey)) != 0: continue
            yield ex, ey, (ex[1] * ey[2] - ex[2] * ey[1], ex[2] * ey[0] - ex[0] * ey[2], ex[0] * ey[1] - ex[1] * ey[0])
def apply(M, p): return tuple(M[0][i] * p[0] + M[1][i] * p[1] + M[2][i] * p[2] for i in range(3))

DEVS = [('EL-PDH', 'REV-11-1850', 'Y', 0.197), ('EL-RIO NI', 'am-3000a_roboRIO2', 'Z', 0.124), ('EL-CANV', 'CTRE_CANivore', 'Z', 0.19),
        ('EL-PIG', 'CTRE_Pigeon2', 'Z', 0.128), ('EL-MPM', 'REV-11-1956', 'Y', 0.197), ('EL-BRK ', 'am-0282_breaker', 'Y', 0.14), ('EL-RAD ', 'VH-109', 'Z', 0.22)]
report = {}
for pre, name, upv, hd in DEVS:
    lo, hi, lab = standin_box(pre); size = hi - lo
    m = import_step(os.path.join(STEPS, name + '.step')).scale(1 / 25.4); b = m.bounding_box()
    corners = list(itertools.product((b.min.X, b.max.X), (b.min.Y, b.max.Y), (b.min.Z, b.max.Z)))
    up_r = (0, 1, 0) if pre == 'EL-RAD ' else (0, 0, 1)
    cands = []
    for ex, ey, ez in rotations():
        M = (ex, ey, ez)
        if M['XYZ'.index(upv)] != up_r: continue
        cs = [apply(M, c) for c in corners]; mn = [min(c[i] for c in cs) for i in range(3)]; mx = [max(c[i] for c in cs) for i in range(3)]
        err = max(abs((mx[i] - mn[i]) - size[i]) for i in range(3))
        if err < 0.06: cands.append((M, (lo[0] - mn[0], lo[1] - mn[1], lo[2] - mn[2]), err))
    key = pre.strip().split()[0]
    if key in LAY.DEV: ours = [(LAY.DEV[key]['o'][0] + dx, LAY.DEV[key]['o'][1] + dy) for dx, dy in LAY.DEV[key]['holes']]; plane = (0, 1)
    elif key == 'EL-BRK': ours = [(LAY.BRK['o'][0] + dx, LAY.BRK['o'][1] + dy) for dx, dy in LAY.BRK['holes']]; plane = (0, 1)
    else: ours = [(LAY.RAD['x'] + dx, LAY.RAD['zc'] + dz) for dz, dx in LAY.RAD['holes']]; plane = (0, 2)
    holes = []
    for f in m.faces():
        if f.geom_type == GeomType.CYLINDER and f.radius and abs(2 * f.radius - hd) < 0.012:
            a = f.axis_of_rotation; holes.append((a.position, a.direction))
    res = []
    for M, t, err in cands:
        loc = Location(Plane(origin=t, x_dir=M[0], z_dir=M[2])); hs = set()
        for p_, d_ in holes:
            d2 = apply(M, (d_.X, d_.Y, d_.Z))
            if abs(sum(a * b_ for a, b_ in zip(d2, up_r))) > 0.99:
                q = (loc * Pos(p_.X, p_.Y, p_.Z)).position; q = (q.X, q.Y, q.Z); hs.add((round(q[plane[0]], 3), round(q[plane[1]], 3)))
        miss = [min(math.dist(o_, h_) for h_ in hs) if hs else 9.0 for o_ in ours]
        res.append((max(miss), loc))
    assert res, ('no way round fits the box', pre, name, size)
    res.sort(key=lambda x: x[0])
    report[key] = dict(model=name, ways_that_fit_the_box=len(res), worst_hole_miss_in=round(res[0][0], 3), other_way_miss_in=[round(r[0], 3) for r in res[1:]])
    place(name, loc_matrix(res[0][1]), lab, '^' + pre.replace(' ', r'\s'), 5)

# ---- camera: back on the tower plate, pitched up ----
CAM_C, CAM_PITCH, LL4 = (13.0, 0.0, 9.45), 12.0, (1.284, 3.154, 1.894)
ll = import_step(os.path.join(STEPS, 'Limelight4.step')).scale(1 / 25.4); lb = ll.bounding_box()
faces = [(f.area, f.center().Y) for f in ll.faces() if f.geom_type == GeomType.PLANE and abs(abs(f.normal_at().Y) - 1) < 1e-3]
big = max(faces); back_y = lb.min.Y if abs(big[1] - lb.min.Y) < abs(big[1] - lb.max.Y) else lb.max.Y; lens = 1 if back_y == lb.min.Y else -1
cx, cz = (lb.min.X + lb.max.X) / 2, (lb.min.Z + lb.max.Z) / 2
Mll = ((0, 1, 0), (1, 0, 0)) if lens == 1 else ((0, -1, 0), (-1, 0, 0))
Mll = (Mll[0], Mll[1], tuple(np.cross(Mll[0], Mll[1])))
c0 = apply(Mll, (cx, back_y, cz)); t_ll = (-LL4[0] / 2 - c0[0], -c0[1], -c0[2])
cam = move(*CAM_C) @ rot('y', -CAM_PITCH) @ loc_matrix(Location(Plane(origin=t_ll, x_dir=Mll[0], z_dir=Mll[2])))
place('Limelight4', cam, standin_box('CAM Limelight')[2], r'^CAM Limelight', 5, (0.12, 0.13, 0.14))

data = {}; meta = []
for i, (label, replaces, sub, colour, v, t) in enumerate(placed):
    data[f'v{i}'] = v.astype(np.float32); data[f't{i}'] = t.astype(np.int32)
    meta.append(dict(label=label, replaces=replaces, sub=sub, colour=[round(float(c), 3) for c in colour]))
np.savez_compressed(OUT, meta=json.dumps(meta), **data)
print('placed', len(placed), 'meshes,', sum(len(p[5]) for p in placed), 'triangles')
for k, v in report.items(): print(' ', k, v)
