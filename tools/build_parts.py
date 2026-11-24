"""Merge the CAD package's lists into one parts file for the site."""
import json, re, glob, os, collections, sys
PKG = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/gen/r33/pkg/1_cad_package_rev3.3'        # the unpacked CAD package
MESH = sys.argv[2] if len(sys.argv) > 2 else '/home/claude/gen/r33/robotA_mesh_rev3.3.json'       # the mesh export, for part names and counts
rows = json.load(open('/home/claude/gen/parts/drawing_rows.json'))
BASE = lambda m: re.sub(r'-[LR]$', '', m)
parts = collections.OrderedDict()
def get(mark):
    return parts.setdefault(mark, dict(mark=mark, name='', sub='', qty='', stock='', size='', src=[], dxf=[], stl='', pdf='', page=0, printed=None, labels=[]))
PREFIX_SUB = {'B': 'Electronics', 'BU': 'Bumpers', 'C': 'Wrist and claw', 'CAM': 'Electronics', 'CL': 'Climber', 'D': 'Drivebase', 'E': 'Elevator', 'EL': 'Electronics', 'F': 'Funnel', 'W': 'Wrist and claw', 'SP': 'Electronics'}
# 1. drawing tables (first complete row wins; later sheets may add size)
for r in rows:
    if r['mark'].startswith('BU-401'): continue          # a purchased rivnut, listed with the bumpers
    p = get(BASE(r['mark']))
    if r['mark'] != BASE(r['mark']):                      # F-103-L / F-103-R are two different lengths
        p = get(r['mark'])
    if not p['name'] or (not p['stock'] and r['stock']):
        p.update(name=r['name'], stock=r['stock'] or p['stock'], qty=r['qty'], size=r['size'] or p['size'], pdf=r['pdf'], page=r['page'])
    if not p['sub']: p['sub'] = r['sub']
    p['src'].append('drawing')
# 2. router flat patterns
import ezdxf
from ezdxf import bbox
for f in sorted(glob.glob(PKG + '/dxf/*/*.dxf')):
    fn = os.path.basename(f)
    m = re.match(r'^((?:[A-Z]+-)+(?:\d{3}|[A-Z]+-P)(?:-[LR])?)_(.+?)_(\d\.\d{3})(?:_(.+))?\.dxf$', fn)
    mark, nm, thick, mat = m.group(1), m.group(2).replace('_', ' '), float(m.group(3)), (m.group(4) or '').replace('_', ' ')
    p = get(BASE(mark))
    msp = ezdxf.readfile(f).modelspace()
    bb = bbox.extents(msp)
    holes = collections.Counter(round(e.dxf.radius * 2, 3) for e in msp if e.dxftype() == 'CIRCLE')
    arcs = [round(e.dxf.radius, 3) for e in msp if e.dxftype() == 'ARC']
    p['dxf'].append(dict(file=fn, folder=os.path.basename(os.path.dirname(f)), thick=thick, material=mat,
                         w=round(bb.extmax.x - bb.extmin.x, 2), h=round(bb.extmax.y - bb.extmin.y, 2),
                         holes=sorted(holes.items()), min_arc=min(arcs) if arcs else None,
                         sharp=not arcs and any(e.dxftype() == 'LINE' for e in msp)))
    if not p['name']: p['name'] = nm
    if not p['sub']: p['sub'] = PREFIX_SUB.get(mark.split('-')[0], '')
    p['src'].append('dxf')
# 3. printed parts list
for line in open(PKG + '/printed/PRINTED_PARTS_LIST.txt'):
    m = re.match(r'^(\S+)\s+(\d+)\s+([\d.]+ x [\d.]+ x [\d.]+)\s{2,}(.+?)\s{2,}(.+)$', line.rstrip())
    if not m or m.group(1) == 'MARK': continue
    mark = m.group(1)
    what = m.group(5); stl = re.search(r'\[([^\]]+)\]?$', what)
    p = get(mark)
    p['printed'] = dict(qty=int(m.group(2)), size=m.group(3), material=m.group(4).strip(), what=re.sub(r'\s*\[[^\]]*\]?$', '', what).strip())
    if not p['name']: p['name'] = re.sub(r'^' + re.escape(mark) + r'\s*', '', p['printed']['what']).split(',')[0]
    if not p['sub']: p['sub'] = PREFIX_SUB.get(mark.split('-')[0], '')
    p['src'].append('printed')
stls = {re.match(r'^((?:[A-Z]+-)+[A-Z0-9.]+?)_', os.path.basename(x)) and re.match(r'^((?:[A-Z]+-)*[A-Z0-9.]+)_', os.path.basename(x)).group(1): os.path.basename(x) for x in []}
# 4. every marked part in the 3D model, for names and counts the tables do not give
model = json.load(open(MESH))
cnt = collections.Counter(); lab = {}
for q in model['parts']:
    m = re.match(r'^((?:[A-Z]{1,4}-)(?:[A-Z]+-)?\d{2,3}[A-Z]?(?:-[LR])?)\b[ ,:]*(.*)$', q['label'])
    if not m: continue
    cnt[BASE(m.group(1))] += 1; lab.setdefault(BASE(m.group(1)), m.group(2))
for mark, n in cnt.items():
    if mark in parts or any(k.startswith(mark + '-') for k in parts):
        for k in parts:
            if k == mark or k.startswith(mark + '-'): parts[k]['model_qty'] = n; parts[k]['labels'].append(lab[mark])
        continue
    p = get(mark); p.update(name=lab[mark], qty=str(n), sub=PREFIX_SUB.get(mark.split('-')[0], '')); p['model_qty'] = n; p['src'].append('model')
json.dump(list(parts.values()), open('/home/claude/gen/parts/merged.json', 'w'), indent=1)
print(len(parts), 'marks;', collections.Counter(','.join(sorted(set(p['src']))) for p in parts.values()))
print('--- from the model only:')
for p in parts.values():
    if p['src'] == ['model']: print(' ', p['mark'].ljust(9), p['qty'].rjust(2), '|', p['name'][:120])
print('--- printed but qty differs from drawing:')
for p in parts.values():
    if p['printed'] and p['qty'] and str(p['printed']['qty']) != p['qty']: print(' ', p['mark'], p['qty'], p['printed']['qty'])
