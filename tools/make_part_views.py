"""2D views of every made part that has no flat pattern: tube, angle, bar, lathe and printed parts.

A router part already gets its picture from its DXF. This draws the same kind of picture for the rest, from the part's
solid in the CAD package's STEP files: the outline as seen face-on, hidden edges dashed, and every hole lettered by size.

    python3 tools/make_part_views.py [folder of the package's STEP files]      -> src/data/part-views.json

For each part: find its solid by its mark, find the directions its flat faces point, and look at it along the direction
of its biggest face. If holes run in another direction too, add a view along that direction. A round part gets a side
view and an end view. A hole is a cylinder face that curves inwards and goes all the way round.
Needs build123d and numpy.
"""
import sys, os, re, json, glob, math, collections
import numpy as np
from build123d import *

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '/mnt/user-data/uploads/RobotA_final_2026-11-23/1_cad_package_rev3.3/step'
ONLY = [a[7:] for a in sys.argv[1:] if a.startswith('--only=')]
K = 1 / 25.4
parts = json.load(open(os.path.join(HERE, '..', 'src', 'data', 'parts.json')))
want = [p for p in parts if not p['outline'] and (not ONLY or p['mark'] in ONLY)]

# the same drill names the flat-pattern hole tables use (tools/make_site_data.py)
DRILL = {0.089: ('#43', '#4-40 tap'), 0.106: ('#36', '#6-32 tap'), 0.116: ('#32', '#4 clearance'), 0.125: ('1/8', 'small screw or pilot'), 0.128: ('#30', '#4 clearance'), 0.136: ('#29', '#8-32 tap'),
         0.144: ('#27', '#6 clearance'), 0.159: ('#21', '#10-32 tap'), 0.161: ('#20', '5/32 rivet'), 0.166: ('#19', '#8 clearance'), 0.177: ('#16', '#8 clearance'), 0.196: ('#9', '#10 clearance'),
         0.201: ('#7', '1/4-20 tap or #10 clearance'), 0.250: ('1/4', '1/4 pin or shoulder'), 0.257: ('F', '1/4 clearance'), 0.266: ('H', '1/4 clearance'), 0.281: ('9/32', '1/4 clearance, loose'),
         0.297: ('19/64', '#10-32 rivnut'), 0.391: ('25/64', '1/4-20 rivnut: check your rivnut')}
def hole_use(d):
    k = min(DRILL, key=lambda x: abs(x - d))
    if abs(k - d) <= 0.0025: return (DRILL[k][0] + ' drill', DRILL[k][1])
    if abs(d - 1.125) < 0.003: return ('bore', 'bearing bore: test the fit in scrap first')
    if d >= 0.375: return ('bore or end mill', 'bore or pilot')
    return ('drill to size', '')

def leaves(n, out):
    ch = getattr(n, 'children', None)
    if ch:
        for k in ch: leaves(k, out)
    else: out.append(n)
mangle = lambda s: re.sub(r'[ ().]', '_', s)
pool = []
for path in sorted(glob.glob(STEPS + '/robotA_*_rev?.step')):
    if 'assembly' in path: continue
    L = []; leaves(import_step(path), L); pool += [s for s in L if s.label]
    print(os.path.basename(path), len(L), 'solids', flush=True)
SIDES = {'L': 'left', 'R': 'right', 'F': 'front', 'B': 'back'}
def find(mark):
    """the part's solid, and which of a handed pair it is when the mark covers both"""
    m = mangle(mark)
    for s in pool:
        if re.match(re.escape(m) + r'(?![0-9A-Za-z])', s.label) and not re.match(re.escape(m) + r'-[A-Z0-9]', s.label): return s, ''
    for s in pool:
        k = re.match(re.escape(m) + r'-([LRFB])(?![0-9A-Za-z])', s.label)
        if k: return s, SIDES[k.group(1)]
    own = glob.glob(os.path.join(STEPS, '..', 'printed', mark + '_*.step'))       # small printed parts have a STEP of their own
    if own:
        c = import_step(own[0]); sol = c.solids()
        if sol: return max(sol, key=lambda x: x.volume), ''
    return None, ''

V = lambda v: np.array([v.X, v.Y, v.Z])
def unit(v): return v / np.linalg.norm(v)
def cluster(items, tol=0.9995):
    """group (direction, weight, payload) by direction, either sign"""
    out = []
    for d, w, pay in items:
        for c in out:
            if abs(np.dot(c['d'], d)) > tol: c['w'] += w; c['items'].append(pay); break
        else: out.append(dict(d=d, w=w, items=[pay]))
    return sorted(out, key=lambda c: -c['w'])

def analyse(s, round_part):
    planar, cyl = [], []
    for f in s.faces():
        if f.geom_type == GeomType.PLANE: planar.append((unit(V(f.normal_at())), f.area * K * K, f))
        elif f.geom_type == GeomType.CYLINDER:
            ax = f.axis_of_rotation; d = unit(V(ax.direction)); p = V(f.position_at(0.5, 0.5)); n = V(f.normal_at(f.position_at(0.5, 0.5)))
            w = p - V(ax.position); radial = w - d * np.dot(w, d)
            zs = [np.dot(V(v), d) for v in f.vertices()]; h = (max(zs) - min(zs)) if zs else 0
            cover = f.area / (2 * math.pi * f.radius * h) if h > 1e-6 else 0
            cyl.append((d, f.area * K * K, dict(r=f.radius * K, pos=V(ax.position), d=d, hole=np.dot(n, radial) < 0, cover=cover, z0=min(zs) if zs else 0)))
    P, C = cluster(planar), cluster(cyl)
    pts = np.array([V(v) for v in s.vertices()])
    def spread(d): q = pts @ d; return q.max() - q.min()
    if round_part and C:
        a = C[0]['d']
        side = next((c['d'] for c in P if abs(np.dot(c['d'], a)) < 0.02), None)
        if side is None: side = unit(np.cross(a, [0, 0, 1] if abs(a[2]) < 0.9 else [1, 0, 0]))
        return [('side', side, a), ('end', a, unit(np.cross(side, a)))], C
    if not P: return [], C
    d1 = P[0]['d']
    d2 = next((c['d'] for c in P[1:] if abs(np.dot(c['d'], d1)) < 0.02), None)
    if d2 is None:
        q = pts - np.outer(pts @ d1, d1); q -= q.mean(axis=0); d2 = unit(np.linalg.svd(q, full_matrices=False)[2][0]); d2 = unit(d2 - d1 * np.dot(d2, d1))
    d3 = unit(np.cross(d1, d2))
    long_, short = (d2, d3) if spread(d2) >= spread(d3) else (d3, d2)
    views = [('face', d1, long_)]
    def has_holes(d): return any(abs(np.dot(c['d'], d)) > 0.9995 and any(h['hole'] and h['cover'] > 0.9 for h in c['items']) for c in C)
    if has_holes(short): views.append(('edge', short, long_))
    if has_holes(long_): views.append(('end', long_, short if spread(short) >= spread(d1) else d1))
    return views, C

def draw(s, look, right, C, sizes):
    """one view: (svg body, width, height, holes seen [(dia, u, v)])"""
    b = s.bounding_box(); pl = Plane(origin=b.center(), x_dir=tuple(right), z_dir=tuple(look))
    loc = pl.to_local_coords(s)
    vis, hid = loc.project_to_viewport((0, 0, 1e5), (0, 1, 0), (0, 0, 0))
    def pts(e):
        """a line as its two ends, a circle or arc as an SVG arc, anything else as a short run of points"""
        if e.geom_type == GeomType.CIRCLE:
            c = e.arc_center; r = e.radius * K; a, b_, mid = e.position_at(0), e.position_at(1), e.position_at(0.5)
            cx, cy = c.X * K, c.Y * K
            if (a - b_).length < 1e-6: return ('arc', f'M{cx + r:.2f},{-cy:.2f}A{r:.3f},{r:.3f} 0 1 0 {cx - r:.2f},{-cy:.2f}A{r:.3f},{r:.3f} 0 1 0 {cx + r:.2f},{-cy:.2f}', [(cx - r, cy - r), (cx + r, cy + r)])
            a0, am, a1 = (math.atan2(q.Y - c.Y, q.X - c.X) for q in (a, mid, b_)); two = 2 * math.pi
            ccw = ((am - a0) % two) < ((a1 - a0) % two); span = (a1 - a0) % two if ccw else (a0 - a1) % two
            return ('arc', f'M{a.X * K:.2f},{-a.Y * K:.2f}A{r:.3f},{r:.3f} 0 {1 if span > math.pi else 0} {0 if ccw else 1} {b_.X * K:.2f},{-b_.Y * K:.2f}', [(a.X * K, a.Y * K), (b_.X * K, b_.Y * K), (mid.X * K, mid.Y * K)])
        n = 2 if e.geom_type == GeomType.LINE else 13
        P = [(p.X * K, p.Y * K) for p in (e.position_at(t) for t in np.linspace(0, 1, n))]
        return ('line', 'M' + ' L'.join(f'{x:.2f},{-y:.2f}' for x, y in P), P)
    VP, HP = [pts(e) for e in vis], [pts(e) for e in hid]
    allp = np.array([q for e in VP for q in e[2]]) if VP else np.zeros((1, 2))
    x0, y0 = allp.min(axis=0); x1, y1 = allp.max(axis=0)
    up = np.cross(look, right)
    holes = {}
    for c in C:
        if abs(np.dot(c['d'], look)) < 0.9995: continue
        by = collections.defaultdict(float)
        for h in c['items']:
            if not h['hole'] or not 0.06 <= 2 * h['r'] <= 2.6: continue
            w = (h['pos'] - V(b.center())) * K; key = (round(float(np.dot(w, right)), 2), round(float(np.dot(w, up)), 2), round(2 * h['r'], 3))
            by[(key, round(h['z0'], 1))] += h['cover']
        for (key, _z), cov in by.items():
            if cov > 0.9: holes[key] = True
    # the projection may come out mirrored left to right: pick the way the drawn circles agree with
    circ = [(e.arc_center.X * K, e.arc_center.Y * K) for e in list(vis) + list(hid) if e.geom_type == GeomType.CIRCLE]
    def score(sx): return sum(1 for (u, v, d) in holes if any(abs(sx * u - cx) < 0.02 and abs(v - cy) < 0.02 for cx, cy in circ))
    sx = 1 if score(1) >= score(-1) else -1
    H = [(d, sx * u, v) for (u, v, d) in holes]
    return VP, HP, (x0, y0, x1, y1), H

def svg_of(VP, HP, box, H, sizes):
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0; big = max(w, h); strip = w / max(h, 1e-6) > 6
    sw = big / (520 if strip else 260); fs = min(big / 26, max(h, 0.2) * 0.55) if strip else big / 26
    m = big * 0.03 + 0.05; top = fs * 1.5 if strip else 0
    def path(P): return ''.join(e[1] for e in P)
    el = [f'<path d="{path(HP)}" stroke-width="{sw * 0.6:.4f}" stroke-dasharray="{sw * 5:.3f} {sw * 4:.3f}" opacity="0.45"/>' if HP else '', f'<path d="{path(VP)}"/>']
    seen = set(); lab = []; placed = []
    for d, u, v in sorted(H, key=lambda t: (t[1], -t[2])):
        i = sizes.index(d); r = d / 2
        el.append(f'<circle cx="{u:.3f}" cy="{-v:.3f}" r="{r:.3f}" class="h{i}"/>')
        if i not in seen:
            seen.add(i)
            if strip: lab.append((u, i))
            else:
                x, y = u + r + fs * 0.2, -v - r - fs * 0.1
                while any(abs(x - px) < fs * 0.8 and abs(y - py) < fs * 0.9 for px, py in placed): x += fs * 0.85      # two sizes on one centre: letters side by side
                placed.append((x, y)); el.append(f'<text x="{x:.3f}" y="{y:.3f}" class="h{i}" font-size="{fs:.3f}">{chr(65 + i)}</text>')
    lx = -1e9
    for u, i in lab:                                           # a long thin part: letters go in a row above it, kept apart
        x = max(u - fs * 0.3, lx + fs * 0.9); lx = x
        el.append(f'<text x="{x:.3f}" y="{-y1 - fs * 0.35:.3f}" class="h{i}" font-size="{fs:.3f}">{chr(65 + i)}</text>')
    vb = f'{x0 - m:.3f} {-y1 - m - top:.3f} {w + 2 * m:.3f} {h + 2 * m + top:.3f}'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" fill="none" stroke="currentColor" stroke-width="{sw:.4f}" stroke-linecap="round" stroke-linejoin="round">'
            + ''.join(el) + '</svg>'), strip

NAMES = {'face': 'Looking at the widest face', 'edge': 'Turned a quarter turn', 'end': 'Looking at the end', 'side': 'From the side'}
out = {}; missing = []
for p in want:
    s, side = find(p['mark'])
    if s is None: missing.append(p['mark']); continue
    round_part = p['kind'] in ('turned', 'shaft') or bool(re.search(r'spacer|washer|bushing|roller', p['name'], re.I))
    try:
        views, C = analyse(s, round_part)
        drawn = [(kind,) + draw(s, look, right, C, None) for kind, look, right in views]
    except Exception as e:
        print('  could not draw', p['mark'], type(e).__name__, str(e)[:80]); missing.append(p['mark']); continue
    # a face-on view with no holes adds nothing when a holed view shows the same outline (a square tube)
    if len(drawn) > 1 and not drawn[0][4]:
        w0, h0 = drawn[0][3][2] - drawn[0][3][0], drawn[0][3][3] - drawn[0][3][1]
        if any(v[4] and abs((v[3][2] - v[3][0]) - w0) < 0.02 * w0 + 0.02 and abs((v[3][3] - v[3][1]) - h0) < 0.02 * h0 + 0.02 for v in drawn[1:]): drawn = drawn[1:]
    drawn.sort(key=lambda v: (v[0] == 'end', 0))                 # end views last
    if round_part and len(drawn) == 2 and drawn[0][3][2] - drawn[0][3][0] < drawn[0][3][3] - drawn[0][3][1]: drawn.reverse()      # a disc: its round face first
    sizes = sorted({d for v in drawn for d, _, _ in v[4]})
    if len(sizes) > 8:                                           # too many sizes to letter: keep the eight most used
        cnt = collections.Counter(d for v in drawn for d, _, _ in v[4]); sizes = sorted(d for d, _ in cnt.most_common(8))
    vs = []
    for kind, VP, HP, box, H in drawn:
        H = [h for h in H if h[0] in sizes]
        svg, strip = svg_of(VP, HP, box, H, sizes)
        vs.append(dict(kind=kind, title=NAMES[kind], w=round(float(box[2] - box[0]), 2), h=round(float(box[3] - box[1]), 2), strip=bool(strip), svg=svg))
    cnt = collections.Counter(d for v in drawn for d, _, _ in v[4])
    out[p['mark']] = dict(views=vs, side=side, holes=[dict(dia=float(d), n=int(cnt[d]), drill=hole_use(d)[0], use=hole_use(d)[1]) for d in sizes])
json.dump(out, open(os.path.join(HERE, '..', 'src', 'data', 'part-views.json'), 'w'), separators=(',', ':'))
print(len(out), 'parts drawn of', len(want), '| no solid found or not drawable:', missing)
print('views per part:', dict(collections.Counter(len(v['views']) for v in out.values())), '| size', os.path.getsize(os.path.join(HERE, '..', 'src', 'data', 'part-views.json')) // 1024, 'KB')
