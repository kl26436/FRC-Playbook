"""The real motor, gearbox and servo models on the climber towers, as the CAD source places them (assembly/climber_hw.py).
They are in 2_onshape_imports/climber_hw_tower.step; the package's climber STEP draws them as a plain cylinder and boxes.
Writes an .npz in the same form as make_vendor_parts.py, to be merged into its output."""
import sys, re, json, time, collections
import numpy as np
from build123d import *
SRC, OUT = sys.argv[1], sys.argv[2]
K = 1 / 25.4; TOL, ANG, MINF = 0.12, 1.2, 0.1
t0 = time.time(); c = import_step(SRC); print('imported', round(time.time() - t0), 's', flush=True)
WANT = [(r'REV-21-2100_MAXPlanetary.*climber_(left|right)', r'^REV MAXPlanetary 25:1', 'REV MAXPlanetary 25:1 gearbox, REV-21-2100 (climber) [%s]', (0.2, 0.2, 0.22)),
        (r'WCP-0940_Kraken_X60.*climber_(left|right)', r'^WCP-0940 Kraken X60 \(climber\)', 'WCP-0940 Kraken X60 (climber) [%s]', (0.15, 0.15, 0.17)),
        (r'REV-41-1097.*climber_(left|right)', r'^REV-41-1097 .*climber pawl release', 'REV-41-1097 Smart Robot Servo (climber pawl release) [%s]', (0.12, 0.12, 0.13))]
def mat(loc):
    t = loc.wrapped.Transformation(); return np.array([[t.Value(i, j) for j in (1, 2, 3, 4)] for i in (1, 2, 3)])
def leaves(n, out, loc=None):
    """(leaf, placement of everything above it): the vertices are moved by numbers, so no shape is copied"""
    ch = getattr(n, 'children', None)
    if ch:
        here = n.location if loc is None else loc * n.location
        for k in ch: leaves(k, out, here)
    else: out.append((n, loc))
data, meta = {}, []
for k in c.children:
    lab = k.label or ''
    hit = next(((m, rp, name, tint) for rx, rp, name, tint in WANT for m in [re.search(rx, lab)] if m), None)
    if not hit: continue
    m, rp, name, tint = hit; L = []; leaves(k, L, None)
    groups = collections.defaultdict(lambda: dict(v=[], t=[], n=0))
    for s, loc in L:
        col = getattr(s, 'color', None) or getattr(k, 'color', None)
        rgb = tuple(round(float(x), 2) for x in tuple(col)[:3]) if col is not None else tint      # these files carry no colours
        M = mat(loc) if loc is not None else None
        for f in s.faces():
            try:
                if f.area < MINF / (K * K): continue
                vs, ts = f.tessellate(TOL / K, ANG)
            except Exception: continue
            if not ts: continue
            V = np.array([(v.X, v.Y, v.Z) for v in vs])
            if M is not None: V = V @ M[:, :3].T + M[:, 3]
            g = groups[rgb]; g['v'].append(V * K); g['t'].append(np.array(ts) + g['n']); g['n'] += len(vs)
    side = 'left' if np.concatenate([np.concatenate(g['v']) for g in groups.values()])[:, 1].mean() > 0 else 'right'
    if side != m.group(1): print('   label says', m.group(1), 'but the model sits on the', side)
    tris = 0
    for rgb, g in groups.items():
        i = len(meta); data[f'v{i}'] = np.concatenate(g['v']).astype(np.float32); data[f't{i}'] = np.concatenate(g['t']).astype(np.int32); tris += len(data[f't{i}'])
        meta.append(dict(label=name % side, replaces=rp, sub=4, colour=list(rgb)))
    allv = np.concatenate([data[f'v{i}'] for i in range(len(meta)) if meta[i]['label'] == name % side])
    print(name % side, '|', len(L), 'solids', tris, 'triangles', len(groups), 'colours | box', allv.min(axis=0).round(2), allv.max(axis=0).round(2), flush=True)
np.savez_compressed(OUT, meta=json.dumps(meta), **data)
