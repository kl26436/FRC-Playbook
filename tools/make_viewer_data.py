"""Turn the CAD mesh export into the data the 3D robot viewer loads.

Input : robotA_mesh.json from the CAD package (one mesh per motion group and colour, one triangle range per part)
        src/data/parts.json (the made parts, so a clicked part can link to its page)
Output: public/robot-viewer/robot.bin  int16 positions (step q inches), then indices (uint16 where a mesh allows it)
        public/robot-viewer/robot.json meshes, parts, made-part lookup

Meshes are regrouped by subsystem as well as motion group and colour, so the viewer can hide or pull apart a subsystem.
Run: python3 tools/make_viewer_data.py <path to robotA_mesh.json>
"""
import sys, os, re, json, base64, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
SRC = ARGS[0] if ARGS else '/mnt/user-data/uploads/RobotA_final_2026-11-23/3_docs/kickoff_brief/robotA/robotA_mesh.json'
OUT = os.path.join(HERE, '..', 'public', 'robot-viewer')
SUBS = ['Drivebase', 'Elevator', 'Wrist and claw', 'Funnel', 'Climber', 'Electronics', 'Bumpers']

made = json.load(open(os.path.join(HERE, '..', 'src', 'data', 'parts.json')))
marks = {p['mark']: p for p in made}
J = json.load(open(SRC))
raw = base64.b64decode(J['bin_b64'])
POS = np.frombuffer(raw, dtype=np.int16, count=J['pos_bytes'] // 2).reshape(-1, 3)
IDX = np.frombuffer(raw, dtype=np.uint32, offset=J['idx_offset'])
Q = J['q']

SPACERS = [('Spacer 3/8 OD x 0.25', 'SP-RND-0.25'), ('Spacer 3/8 OD x 0.125', 'SP-RND-0.125'),
           ('Spacer 1/2 OD x 0.50', 'SP-RND-0.50'), ('Spacer 1/2 hex bore x 0.125', 'SP-HEX-0.125')]


def mark_of(label):
    """The made-part mark a model label belongs to, or None for a bought part."""
    if label.startswith('EL-SB50-P'): return 'EL-SB'
    m = re.match(r'^([A-Z]{1,4}(?:-[A-Z0-9.]+)+)', label)
    if m:
        s = m.group(1)
        if s not in marks and s.split('.')[0] in marks: return s.split('.')[0]  # W-104.60T: a vendor size after the mark
        while True:
            if s in marks: return s
            if s.count('-') < 2: break
            s = s.rsplit('-', 1)[0]
    for start, mk in SPACERS:
        if label.startswith(start): return mk
    return None


KEY = [  # checked in order against the label, for parts in the fixed (frame) group
    (3, r'funnel|latch|tubing anchor|\(gate\)|^Latex|^F-'),
    (4, r'climber|pawl|^Fork stop|^Deploy|^Dowel pin|^Stop pin|spool|tower plate|\(CL-|^Bronze flanged|^CL-|\(pivot axle\)'),
    (2, r'wrist|^REV MAXPlanetary 2-stage|^W-|^C-1'),
    (5, r'^EL-|EL-SP|^VHB|^Zip tie|^Battery|^B-1|^CAM'),
    (6, r'^BU-'),
    (0, r'^MK4i|^D-|\(D-10'),
]


def sub_of(label, group, mark):
    if group == 'tray': return 3
    if group == 'fork': return 4
    if group == 'wrist': return 2
    if group in ('stage_a', 'stage_b'): return 1
    for s, rx in KEY:
        if re.search(rx, label): return s
    if mark: return SUBS.index(marks[mark]['sub'])
    return 1  # what is left in the frame and carriage groups came from the elevator model


# ---- every part: its triangles, mark and subsystem ----
parts = []
tri0 = collections.defaultdict(int)
for p in J['parts']:
    m = J['meshes'][p['mesh']]
    tris = IDX[m['i0'] + p['t0'] * 3: m['i0'] + (p['t0'] + p['nt']) * 3].astype(np.int64)  # indices are local to the mesh
    mk = mark_of(p['label'])
    parts.append(dict(label=p['label'], group=m['group'], color=tuple(m['color']), tris=tris + m['v0'], mark=mk))

# servo horns carry no subsystem word: give each the subsystem of the nearest servo
def centre(q): return POS[np.unique(q['tris'])].mean(axis=0) * Q
for q in parts: q['sub'] = sub_of(q['label'], q['group'], q['mark'])
servos = [q for q in parts if q['label'].startswith('REV-41-1097')]
for q in parts:
    if q['label'].startswith('Servo horn') and servos:
        c = centre(q); q['sub'] = min(servos, key=lambda s: np.linalg.norm(centre(s) - c))['sub']

# ---- regroup into meshes by (subsystem, motion group, colour) ----
buckets = collections.OrderedDict()
for q in parts: buckets.setdefault((q['sub'], q['group'], q['color']), []).append(q)
pos_out, idx_out, meshes, plist = [], [], [], []
voff = 0; ibytes = 0
for (sub, group, color), lst in buckets.items():
    vp, ip, nv, tri = [], [], 0, 0
    mi = len(meshes)
    for q in lst:
        u, inv = np.unique(q['tris'], return_inverse=True)
        v = POS[u]
        vp.append(v); ip.append(inv + nv); nv += len(u)
        f = v.astype(np.float64) * Q
        lo, hi = f.min(axis=0), f.max(axis=0)
        plist.append(dict(l=q['label'], m=mi, t0=tri, nt=len(inv) // 3, k=q['mark'],
                          c=[round(float(x), 2) for x in (lo + hi) / 2], r=round(float(np.linalg.norm(hi - lo) / 2), 2)))
        tri += len(inv) // 3
    V = np.concatenate(vp); I = np.concatenate(ip)
    w = 2 if nv <= 65535 else 4
    b = I.astype(np.uint16 if w == 2 else np.uint32).tobytes()
    b += b'\0' * ((4 - len(b) % 4) % 4)
    meshes.append(dict(sub=sub, group=group, color=[round(c, 3) for c in color], v0=voff, nv=nv, i0=ibytes, ni=len(I), w=w))
    pos_out.append(V); idx_out.append(b); voff += nv; ibytes += len(b)
Pb = np.concatenate(pos_out).astype(np.int16).tobytes()
Pb += b'\0' * ((4 - len(Pb) % 4) % 4)
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'robot.bin'), 'wb') as f: f.write(Pb + b''.join(idx_out))

# how many of each made part the model shows, and what the viewer needs to describe it
count = collections.Counter(q['k'] for q in plist if q['k'])
lookup = {mk: dict(slug=p['slug'], name=p['name'], sub=p['sub'], machine=p['machine'], qty=p['qty'] or str(count[mk]))
          for mk, p in marks.items() if count[mk]}
json.dump(dict(units='in', q=Q, frame=J['frame'], idx_offset=len(Pb), subs=SUBS, meshes=meshes, parts=plist, made=lookup),
          open(os.path.join(OUT, 'robot.json'), 'w'), separators=(',', ':'))

print(f"{len(meshes)} meshes, {len(plist)} parts, {(len(Pb) + ibytes) / 1e6:.2f} MB")
print('by subsystem:', {SUBS[s]: sum(1 for q in parts if q['sub'] == s) for s in range(len(SUBS))})
print('made parts shown:', len(lookup), 'of', len(marks), '| not in the model:', sorted(set(marks) - set(lookup)))
if '--list' in sys.argv:
    for q in sorted(parts, key=lambda q: (q['sub'], q['label'])): print(SUBS[q['sub']][:5], q['group'][:6].ljust(6), (q['mark'] or '-').ljust(12), q['label'][:90])
