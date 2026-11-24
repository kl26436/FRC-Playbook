"""Turn the CAD package's fastener model into data the 3D viewer can draw, and work out which parts each fastener joins.

Input : step/robotA_detail_fasteners.step (every rivet, screw, nut and rivnut as a simple solid in robot position, mm)
        public/robot-viewer/robot.json + robot.bin (the part meshes)
Output: public/robot-viewer/fasteners.json
        kinds: the distinct fasteners; items: [kind, x, y, z, dx, dy, dz, length, head radius, [part indices it passes through]]

The names inside the STEP are shared between identical shapes and are not reliable, so each fastener is measured:
its thread size from the shank radius, its length from its extent along its axis.
A fastener joins a part when the part has hole-edge points round the fastener's axis (a clearance hole), or when
a point on the fastener's axis is inside the part's solid (a tapped rod end, a tube plug, a motor face drawn as a block).
A lock nut takes the parts of the screw it sits on.
Needs build123d, numpy, scipy.   Run: python3 tools/make_fastener_data.py <path to the STEP> [--vendor=<placed.npz>] [--mesh=<robotA_mesh.json>]

With --vendor (when the viewer data was built with the real vendor models), the joins are still worked out on the
CAD's own plain shapes, whose holes are exact, and then pointed at the vendor model that took each shape's place.
"""
import sys, os, re, json, collections, subprocess, tempfile
import numpy as np
from scipy.spatial import cKDTree
from build123d import import_step, GeomType

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'public', 'robot-viewer')
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
STEP = ARGS[0] if ARGS else '/mnt/user-data/uploads/RobotA_final_2026-11-23/1_cad_package_rev3.2/step/robotA_detail_fasteners.step'

RIVETS = [(0.187, '97517A032'), (0.25, '97517A035'), (0.375, '97517A040'), (0.5, '97517A041')]


def frac(x):
    """0.625 -> '5/8', 1.5 -> '1.50' """
    if x < 1:
        n = round(x * 16); d = 16
        while n % 2 == 0 and d > 1: n //= 2; d //= 2
        return f'{n}/{d}'
    return f'{x:.2f}'


def classify(length, radii):
    rmin, rmax = radii[0], radii[-1]
    def near(a, b): return abs(a - b) < 0.006
    if near(rmin, 0.078) and any(near(r, 0.11) for r in radii):
        grip = round(length - 0.20, 2); pn = next(p for g, p in RIVETS if grip <= g + 0.005)
        return f'5/32 in rivet, {pn}'
    if any(near(r, 0.149) for r in radii): return '#10-32 rivnut'
    if rmax >= 0.26 and length < 0.7: return '1/4-20 rivnut'
    if near(rmin, 0.095):
        if length <= 0.3 and rmax > 0.2: return '#10-32 lock nut'
        if near(rmax, 0.193): return f'#10-32 × {frac(length)} in flat head screw'
        return f'#10-32 × {frac(round(length - 0.19, 3))} in screw'
    if near(rmin, 0.082): return f'#8-32 × {frac(round(length - 0.164, 3))} in screw'
    if near(rmin, 0.056):
        if length <= 0.2: return '#4-40 lock nut'
        return f'#4-40 × {frac(round(length - 0.112, 3))} in screw'
    if rmin > 0.11:
        if any(r > 0.25 for r in radii) and length < 0.75 and len(radii) > 2: return '1/4-20 rivnut'
        return f'1/4-20 × {frac(round(length - 0.25, 3))} in screw'
    return f'unknown r{rmin:.3f} l{length:.2f}'


# ---- the part meshes: every vertex with the part it belongs to ----
OPT = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
GEO = OUT; REMAP = None
if OPT.get('vendor'):
    GEO = tempfile.mkdtemp()
    subprocess.run([sys.executable, os.path.join(HERE, 'make_viewer_data.py')] + ([OPT['mesh']] if OPT.get('mesh') else []) + ['--out=' + GEO], check=True, stdout=subprocess.DEVNULL)
    new = json.load(open(os.path.join(OUT, 'robot.json')))['parts']
    swaps = [(re.compile(m['replaces']), m['label']) for m in json.loads(str(np.load(OPT['vendor'])['meta'])) if m['replaces']]
    where = collections.defaultdict(list)
    for i, p in enumerate(new): where[p['l']].append(i)
    REMAP = []
    for p in json.load(open(os.path.join(GEO, 'robot.json')))['parts']:
        to = next((lab for rx, lab in swaps if rx.search(p['l'])), None)
        if to: REMAP.append(where[to][0])                 # a swapped shape: the first piece of the vendor model
        else:                                             # an unchanged part: same label, same place
            hit = [i for i in where[p['l']] if new[i]['c'] == p['c'] and new[i]['nt'] == p['nt']]
            assert len(hit) >= 1, p['l']; REMAP.append(hit[0])
J = json.load(open(os.path.join(GEO, 'robot.json'))); raw = open(os.path.join(GEO, 'robot.bin'), 'rb').read()
POS = np.frombuffer(raw, dtype=np.int16, count=J['idx_offset'] // 2).reshape(-1, 3).astype(np.float64) * J['q']
owner = np.full(len(POS), -1, dtype=np.int32)
for pi, p in enumerate(J['parts']):
    m = J['meshes'][p['m']]; dt = np.uint16 if m['w'] == 2 else np.uint32
    idx = np.frombuffer(raw, dtype=dt, count=m['ni'], offset=J['idx_offset'] + m['i0'])[p['t0'] * 3:(p['t0'] + p['nt']) * 3]
    owner[np.unique(idx).astype(np.int64) + m['v0']] = pi
tree = cKDTree(POS)
TRIS, BOX = [], []
for pi, p in enumerate(J['parts']):
    m = J['meshes'][p['m']]; dt = np.uint16 if m['w'] == 2 else np.uint32
    idx = np.frombuffer(raw, dtype=dt, count=m['ni'], offset=J['idx_offset'] + m['i0'])[p['t0'] * 3:(p['t0'] + p['nt']) * 3].astype(np.int64) + m['v0']
    T = POS[idx].reshape(-1, 3, 3); TRIS.append(T); BOX.append((T.reshape(-1, 3).min(axis=0), T.reshape(-1, 3).max(axis=0)))
BLO = np.array([b[0] for b in BOX]); BHI = np.array([b[1] for b in BOX])
RAY = np.array([0.5377, 0.2671, 0.7997]); RAY /= np.linalg.norm(RAY)      # an odd direction, to miss edges


def inside(pt, pi):
    """Is the point inside part pi? Count the triangles a ray from the point crosses: odd means inside."""
    T = TRIS[pi]; e1 = T[:, 1] - T[:, 0]; e2 = T[:, 2] - T[:, 0]
    h = np.cross(RAY, e2); a = np.einsum('ij,ij->i', e1, h); ok = np.abs(a) > 1e-12
    f = np.where(ok, 1.0 / np.where(ok, a, 1), 0); sv = pt - T[:, 0]; u = f * np.einsum('ij,ij->i', sv, h)
    qv = np.cross(sv, e1); v = f * (qv @ RAY); t = f * np.einsum('ij,ij->i', e2, qv)
    return int(np.sum(ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (t > 1e-9))) % 2 == 1

# ---- the fasteners ----
leaves = []
def collect(n):
    ch = getattr(n, 'children', None) or []
    if not ch: leaves.append(n)
    for k in ch: collect(k)
collect(import_step(STEP))

kinds, items = [], []
for n in leaves:
    cyl = [f for f in n.faces() if f.geom_type == GeomType.CYLINDER]
    ax = max(cyl, key=lambda f: f.area).axis_of_rotation
    o = np.array(tuple(ax.position)) / 25.4; d = np.array(tuple(ax.direction)); d /= np.linalg.norm(d)
    V = np.array([tuple(v) for v in n.vertices()]) / 25.4
    t = (V - o) @ d; rad = np.linalg.norm((V - o) - np.outer(t, d), axis=1)
    radii = sorted(set(round(float(x), 3) for x in rad if x > 0.01)); t0, t1 = float(t.min()), float(t.max())
    kind = classify(t1 - t0, radii)
    # point the axis from the head (the wide end) toward the tip, so the viewer can put a head on the right end
    head_at_t1 = np.mean(t[rad > rad.max() - 0.01]) > (t0 + t1) / 2
    if head_at_t1: d = -d; t0, t1 = -t1, -t0
    a, b = o + d * t0, o + d * t1                         # head end, tip end
    # parts with hole-edge points round the axis
    mid, half = (a + b) / 2, (t1 - t0) / 2
    near = tree.query_ball_point(mid, half + 0.35)
    P = POS[near]; tt = (P - a) @ d; rr = np.linalg.norm((P - a) - np.outer(tt, d), axis=1)
    reach = max(radii[0] + 0.05, 0.13)
    ok = (tt > -0.06) & (tt < (t1 - t0) + 0.06) & (rr < reach)
    count = collections.Counter(int(owner[near[i]]) for i in np.nonzero(ok)[0] if owner[near[i]] >= 0)
    joined = set(pi for pi, c in count.items() if c >= 3)
    for frac_along in (0.2, 0.5, 0.8, 0.97):
        pt = a + d * (t1 - t0) * frac_along
        for pi in np.nonzero(np.all((BLO <= pt) & (BHI >= pt), axis=1))[0]:
            if int(pi) not in joined and inside(pt, int(pi)): joined.add(int(pi))
    if not joined:                                        # nothing found: take the part nearest the head
        joined = {int(owner[tree.query(a)[1]])}
    joined = sorted(joined)
    if kind not in kinds: kinds.append(kind)
    items.append([kinds.index(kind)] + [round(float(x), 3) for x in a] + [round(float(x), 3) for x in d] + [round(t1 - t0, 3), round(radii[-1], 3), joined])

# a lock nut takes the parts of the screw it is on
for it in items:
    if 'lock nut' not in kinds[it[0]]: continue
    c = np.array(it[1:4]) + np.array(it[4:7]) * it[7] / 2; best = None
    for sc in items:
        if 'screw' not in kinds[sc[0]]: continue
        a = np.array(sc[1:4]); d = np.array(sc[4:7]); t = (c - a) @ d; r = np.linalg.norm((c - a) - t * d)
        if r < 0.04 and -0.15 < t < sc[7] + 0.35 and (best is None or r < best[0]): best = (r, sc)
    if best: it[-1] = sorted(set(it[-1]) | set(best[1][-1])); it.append(items.index(best[1]))
    else: it.append(-1)

if REMAP:
    for it in items: it[9] = sorted(set(REMAP[i] for i in it[9]))
    J = json.load(open(os.path.join(OUT, 'robot.json')))
json.dump(dict(kinds=kinds, items=items), open(os.path.join(OUT, 'fasteners.json'), 'w'), separators=(',', ':'))
by = collections.Counter(kinds[i[0]] for i in items)
print(len(items), 'solids,', sum(v for k, v in by.items() if 'nut' not in k or 'rivnut' in k), 'fasteners plus', sum(v for k, v in by.items() if 'lock nut' in k), 'lock nuts')
for k, v in sorted(by.items()): print(f'  {v:4d}  {k}')
nj = collections.Counter(len(i[9]) for i in items); print('parts joined per fastener:', dict(sorted(nj.items())))
if '--list' in sys.argv:
    for i in items:
        parts = i[9]
        if len(parts) < 2: print(kinds[i[0]], i[1:4], [J['parts'][p]['l'][:40] for p in parts])
