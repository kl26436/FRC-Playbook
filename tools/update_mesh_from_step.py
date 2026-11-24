"""Rev 3.3 mesh for the viewer: the rev 3.2 mesh export with the changed packages re-read from the rev 3.3 STEP files.

The CAD session did not re-export robotA_mesh.json for 3.3, and its source cannot be run here (generated inputs are not
in the package). So: keep every unchanged part from the 3.2 export; re-tessellate, with the export script's own settings,
  - the elevator's fixed parts from 2_onshape_imports/E1_mast.step (second brace, second gusset),
  - the whole climber from step/robotA_climber_revD.step (bought ratchet, moved gearboxes and servo, new printed parts),
  - the left side rail from step/robotA_drivebase_revG.step (four new gusset holes).
"""
import sys, os, re, json, base64, collections
import numpy as np
from build123d import *
U = '/mnt/user-data/uploads/RobotA_final_2026-11-23'
OLD = U + '/3_docs/kickoff_brief/robotA/robotA_mesh.json'
sys.path.insert(0, '/home/claude/gen/r33')
Q = 0.004
HW = re.compile(r'^(\d{4,5}[A-Z]\d{2,4}|McMaster|REF joint|#|Rivnut|rivnut|nylock|Nylock|washer|Washer)')

J = json.load(open(OLD)); raw = base64.b64decode(J['bin_b64'])
POS = np.frombuffer(raw, dtype=np.int16, count=J['pos_bytes'] // 2).reshape(-1, 3).astype(np.float64) * J['q']
IDX = np.frombuffer(raw, dtype=np.uint32, offset=J['idx_offset'])
old = []
for p in J['parts']:
    m = J['meshes'][p['mesh']]
    t = IDX[m['i0'] + p['t0'] * 3: m['i0'] + (p['t0'] + p['nt']) * 3].astype(np.int64) + m['v0']
    u, inv = np.unique(t, return_inverse=True)
    old.append(dict(label=p['label'], group=m['group'], color=tuple(m['color']), V=POS[u], T=inv.reshape(-1, 3)))

# which subsystem an old part belongs to: the same rules as tools/make_viewer_data.py
marks = {p['mark'] for p in json.load(open('/home/claude/frc-playbook/src/data/parts.json'))}
KEY = [(3, r'funnel|latch|tubing anchor|\(gate\)|^Latex|^F-'),
       (4, r'climber|pawl|^Fork stop|^Deploy|^Dowel pin|^Stop pin|spool|tower plate|\(CL-|^Bronze flanged|^CL-|\(pivot axle\)'),
       (2, r'wrist|^REV MAXPlanetary 2-stage|^W-|^C-1'), (5, r'^EL-|EL-SP|^VHB|^Zip tie|^Battery|^B-1|^CAM'), (6, r'^BU-'), (0, r'^MK4i|^D-|\(D-10')]
def sub_of(label, group):
    if group == 'tray': return 3
    if group == 'fork': return 4
    if group == 'wrist': return 2
    if group in ('stage_a', 'stage_b'): return 1
    for s, rx in KEY:
        if re.search(rx, label): return s
    m = re.match(r'^([A-Z]{1,4})-', label)
    if m and m.group(1) in ('F',): return 3
    if m and m.group(1) == 'CL': return 4
    return 1
for q in old: q['sub'] = sub_of(q['label'], q['group'])
# two kinds of part the label rules cannot place: the gearbox foot shims are drivebase parts, and each servo horn belongs with the nearest servo
servos = [q for q in old if q['label'].startswith('REV-41-1097')]
for q in old:
    if 'gearbox foot to spine' in q['label']: q['sub'] = 0
    if q['label'].startswith('Servo horn'):
        c = q['V'].mean(axis=0); q['sub'] = min(servos, key=lambda s_: np.linalg.norm(s_['V'].mean(axis=0) - c))['sub']

def leaves(n, out, loc=None):
    ch = getattr(n, 'children', None)
    if ch:
        here = n.location if loc is None else loc * n.location
        for c in ch: leaves(c, out, here)
    else:
        if loc is not None and loc.position.length + abs(loc.orientation.length) > 1e-9:
            s = loc * n; s.label = n.label; s.color = getattr(n, 'color', None); n = s
        out.append(n)

def tess(s, lab, k):
    """exactly the export script's settings"""
    vend = 'vendor model' in lab or lab.startswith(('WCP-0940', 'WCP-0941', 'REV MAX', 'REV-11-1271'))
    tol, ang = (0.12 if vend else 0.03) / k, (1.2 if vend else 0.6)
    vs, ts = [], []
    if not vend:
        try: vs, ts = s.tessellate(tol, ang)
        except Exception: vs, ts = [], []
    if vend or not ts:
        amin = (0.1 if vend else 0.0) / (k * k); vs, ts = [], []
        for f_ in s.faces():
            try:
                if amin and f_.area < amin: continue
                v_, t_ = f_.tessellate(tol, ang)
            except Exception: continue
            ts += [(a_ + len(vs), b_ + len(vs), c_ + len(vs)) for a_, b_, c_ in t_]; vs += list(v_)
    if not ts: return None
    return np.array([(v.X, v.Y, v.Z) for v in vs], dtype=np.float64) * k, np.array(ts, dtype=np.int64)
def colour(s):
    c = tuple(round(float(x), 3) for x in tuple(s.color)) if getattr(s, 'color', None) is not None else (0.6, 0.62, 0.65, 1.0)
    return c if len(c) == 4 else c + (1.0,)
def box(V): return np.r_[V.min(axis=0), V.max(axis=0)]

new = [q for q in old]
report = {}

# ---- 1. elevator, fixed parts ----
L = []; leaves(import_step(U + '/2_onshape_imports/E1_mast.step'), L)
e1 = []
for s in L:
    if s.label and s.label.startswith('REF'): continue
    lab = re.sub(r' +', ' ', re.sub(r'(\d)_(\d)', r'\1.\2', s.label).replace('_', ' ')).strip() if s.label else ''
    if HW.match(lab): continue
    if lab.strip() in ('', 'SOLID'): lab = 'REV MAXPlanetary 2-stage gearbox (vendor model)'
    r = tess(s, lab, 1 / 25.4)
    if r is None: print('no triangles', lab[:60]); continue
    e1.append(dict(label=lab, group='frame', color=colour(s), V=r[0], T=r[1], sub=1))
gone = [q for q in new if q['group'] == 'frame' and q['sub'] == 1]
a, b = collections.Counter(q['label'] for q in gone), collections.Counter(q['label'] for q in e1)
report['elevator'] = dict(before=len(gone), after=len(e1), removed=sorted((a - b).elements()), added=sorted((b - a).elements()))
new = [q for q in new if not (q['group'] == 'frame' and q['sub'] == 1)] + e1

# ---- 2. climber ----
mangle = lambda s: re.sub(r'[ ().]', '_', s)
def unmangle(s):
    s = re.sub(r'(\d)_(\d)', r'\1.\2', s); s = s.replace('__', ' ('); s = re.sub(r'_([,:;])', r')\1', s); s = re.sub(r'_$', ')', s)
    return re.sub(r' +', ' ', s.replace('_', ' ')).strip()
# two labels the STEP's name mangling cannot be undone for: taken from climber/climber.py
FIX = {'CL-311 pawl link, printed Onyx 0.22 thick, holes 0.257 and 0.128.2 10 apart: on the pawl tail shoulder screw, a #4-40 screw into the servo horn':
       'CL-311 pawl link, printed Onyx 0.22 thick, holes 0.257 and 0.128 2.10 apart: on the pawl tail shoulder screw, a #4-40 screw into the servo horn',
       'Shoulder screw 1/4 x 5/16 shoulder, #10-32 thread, 18-8.94035A532 (pawl tail: link CL-311 turns on the shoulder, thread into the pawl)':
       'Shoulder screw 1/4 x 5/16 shoulder, #10-32 thread, 18-8 94035A532 (pawl tail: link CL-311 turns on the shoulder, thread into the pawl)'}
oldc = [q for q in new if q['sub'] == 4]
by = collections.defaultdict(list)
for q in oldc: by[mangle(q['label'])].append(q)
L = []; leaves(import_step(U + '/1_cad_package_rev3.3/step/robotA_climber_revD.step'), L)
cl = []; guessed = []
for s in L:
    m = s.label or ''
    if m in by: lab, grp = by[m][0]['label'], by[m][0]['group']
    else: lab, grp = FIX.get(unmangle(m), unmangle(m)), 'frame'; guessed.append(lab)
    if lab.startswith('REF') or HW.match(lab): continue
    r = tess(s, lab, 1 / 25.4)
    if r is None: print('no triangles', lab[:60]); continue
    cl.append(dict(label=lab, group=grp, color=colour(s), V=r[0], T=r[1], sub=4))
a, b = collections.Counter(q['label'] for q in oldc), collections.Counter(q['label'] for q in cl)
report['climber'] = dict(before=len(oldc), after=len(cl), removed=sorted((a - b).elements()), added=sorted((b - a).elements()), labels_rebuilt=sorted(set(guessed)))
new = [q for q in new if q['sub'] != 4] + cl

# ---- 3. left side rail ----
L = []; leaves(import_step(U + '/1_cad_package_rev3.3/step/robotA_drivebase_revG.step'), L)
rail = [s for s in L if (s.label or '').startswith('D-101-L')]; assert len(rail) == 1
i = [k for k, q in enumerate(new) if q['label'].startswith('D-101-L')]; assert len(i) == 1
r = tess(rail[0], new[i[0]]['label'], 1 / 25.4)
report['rail'] = dict(label=new[i[0]]['label'], triangles_before=len(new[i[0]]['T']), triangles_after=len(r[1]), box_moved=float(np.abs(box(new[i[0]]['V']) - box(r[0])).max()))
new[i[0]] = dict(new[i[0]], V=r[0], T=r[1])

# ---- write, in the export's format ----
order = ['frame', 'stage_a', 'stage_b', 'carriage', 'wrist', 'fork', 'tray']
buckets = collections.OrderedDict()
for g in order:
    for q in new:
        if q['group'] == g: buckets.setdefault((g, tuple(round(float(c), 3) for c in q['color'])), []).append(q)
P, I, meshes, parts = [], [], [], []; voff = ioff = 0
for (g, col), lst in buckets.items():
    pos, idx, nv = [], [], 0; mi = len(meshes); tri = 0
    for q in lst:
        pos.append(q['V']); idx.append(q['T'] + nv); nv += len(q['V'])
        parts.append(dict(label=q['label'], mesh=mi, t0=tri, nt=int(len(q['T'])))); tri += len(q['T'])
    A = np.concatenate(pos); T = np.concatenate(idx)
    qz = np.round(A / Q).astype(np.int64); assert np.abs(qz).max() < 32767
    P.append(qz.astype(np.int16)); I.append(T.astype(np.uint32))
    meshes.append(dict(group=g, color=list(col), v0=voff, nv=len(A), i0=ioff, ni=len(T) * 3)); voff += len(A); ioff += len(T) * 3
Pb = np.concatenate(P).tobytes(); Ib = np.concatenate(I).tobytes(); pad = (4 - len(Pb) % 4) % 4
out = dict(units='in', q=Q, frame=J['frame'], rev='3.3', pos_bytes=len(Pb), idx_offset=len(Pb) + pad, meshes=meshes, parts=parts,
           bin_b64=base64.b64encode(Pb + b'\0' * pad + Ib).decode())
json.dump(out, open('/home/claude/gen/r33/robotA_mesh_rev3.3.json', 'w'), separators=(',', ':'))
json.dump(report, open('/home/claude/gen/r33/mesh_report.json', 'w'), indent=1)
print(len(old), 'parts before,', len(parts), 'after;', ioff // 3, 'triangles')
print(json.dumps(report, indent=1)[:6000])
