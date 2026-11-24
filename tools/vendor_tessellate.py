"""Tessellate one vendor STEP file coarsely and cache it, in the vendor's own axes, in inches.

    python3 tools/vendor_tessellate.py <file.step> <out.npz> [tolerance in] [smallest face, sq in] [name to leave out | name=r,g,b] ...

A name is matched anywhere in a part's name inside the file, so give enough of it to be exact ("Motor,_Falcon500",
not "Falcon", which also matches the module's own plates). name=r,g,b recolours matching parts (a vendor file's
colours are often placeholders).

Solids are merged by colour, so a module comes out as a handful of meshes. Small faces are dropped: these models
are for looking at on a phone, not for measuring. Needs build123d.
"""
import sys, time, collections
import numpy as np
from build123d import import_step

src, out = sys.argv[1], sys.argv[2]
K = 1 / 25.4; ANG = 0.9
TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05      # inches
MIN_FACE = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02  # square inches
LEAVE_OUT = [a for a in sys.argv[5:] if '=' not in a]
RECOLOUR = [(a.split('=')[0], tuple(float(x) for x in a.split('=')[1].split(','))) for a in sys.argv[5:] if '=' in a]
t0 = time.time()
shape = import_step(src)
print('imported', round(time.time() - t0, 1), 's', flush=True)

# Colour and name come from the file's tree. Position comes from the whole model's own list of solids,
# because a solid reached through the tree does not always carry the placement of the sub-assemblies above it.
def sig(s): return (round(s.volume, 1), round(s.area, 1), len(s.faces()))
look = {}
def walk(n, col=None, name=''):
    c = getattr(n, 'color', None); col = c if c is not None else col
    name = n.label or name
    ch = getattr(n, 'children', None) or []
    if ch:
        for k in ch: walk(k, col, name)
    else:
        for s in (n.solids() or [n]): look.setdefault(sig(s), (col, name))
walk(shape)
solids = shape.solids() or [shape]          # a file drawn as surfaces has no solids: take it whole
print(len(solids), 'solids,', len(look), 'distinct', flush=True)

groups = collections.defaultdict(lambda: dict(v=[], t=[], n=0, names=collections.Counter()))
skipped = 0; unknown = 0
for s in solids:
    col, name = look.get(sig(s), (None, '')); unknown += sig(s) not in look
    if any(x.lower() in name.lower() for x in LEAVE_OUT): continue
    rgb = tuple(round(float(x), 2) for x in tuple(col)[:3]) if col is not None else (0.6, 0.62, 0.65)
    rgb = next((c for k, c in RECOLOUR if k.lower() in name.lower()), rgb)
    g = groups[rgb]; g['names'][name] += 1
    for f in s.faces():
        try:
            if f.area * K * K < MIN_FACE: skipped += 1; continue
            vs, ts = f.tessellate(TOL / K, ANG)
        except Exception: continue
        if not ts: continue
        g['v'].append(np.array([(v.X, v.Y, v.Z) for v in vs]) * K); g['t'].append(np.array(ts) + g['n']); g['n'] += len(vs)
if unknown: print(unknown, 'solids not matched to a name (drawn in the default colour)')
data = {}
for i, (rgb, g) in enumerate(groups.items()):
    if not g['v']: continue
    data[f'v{i}'] = np.concatenate(g['v']).astype(np.float32); data[f't{i}'] = np.concatenate(g['t']).astype(np.int32); data[f'c{i}'] = np.array(rgb)
    print('  colour', rgb, len(data[f'v{i}']), 'verts', len(data[f't{i}']), 'tris', g['names'].most_common(3), flush=True)
np.savez_compressed(out, **data)
allv = np.concatenate([data[k] for k in data if k[0] == 'v'])
print('done', round(time.time() - t0, 1), 's; box', allv.min(axis=0).round(2), allv.max(axis=0).round(2), '; faces skipped', skipped, '; tris', sum(len(data[k]) for k in data if k[0] == 't'))
