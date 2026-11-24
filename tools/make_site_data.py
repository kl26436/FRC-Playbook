"""Turn the merged parts list into the data the site renders: kind, machine, proposed route, outline, sheet."""
import json, re, math, os, glob, subprocess, collections, sys
PKG = '/mnt/user-data/uploads/RobotA_final_2026-11-23/1_cad_package_rev3.2'
SITE = '/home/claude/frc-playbook'
merged = [p for p in json.load(open('/home/claude/gen/parts/merged.json')) if p['mark'] and not p['mark'].startswith('REV-') and p['src'] and p['mark'] != 'B-103']

DRILL = {0.094: ('3/32', 'pin or small screw'), 0.116: ('#32', 'small screw'), 0.124: ('1/8', 'pin'), 0.125: ('1/8', 'small screw or pilot'),
         0.159: ('#21', 'tap drill for #10-32: check the drawing for which holes are tapped'), 0.161: ('#20', '5/32 rivet'),
         0.177: ('#16', 'servo screw'), 0.196: ('#9', 'clearance for a #10 screw'), 0.201: ('#7', 'tap drill for 1/4-20, or a free fit for a #10 screw: check the drawing'),
         0.257: ('F', 'clearance for a 1/4 screw'), 0.266: ('H', 'clearance for a 1/4 screw'), 0.297: ('19/64', '#10-32 rivnut'), 0.32: ('5/16', 'pivot'),
         0.391: ('25/64', '1/4-20 rivnut')}
def hole_use(d):
    if d in DRILL: return DRILL[d]
    if abs(d - 1.125) < 0.002: return ('1/4 end mill', 'bearing bore: test the fit in scrap first')
    if d >= 0.25: return ('1/4 end mill', 'bore or pilot')
    return ('drill to size', '')

def kind_of(p):
    name = (p['name'] + ' ' + ' '.join(p['labels'])).lower(); stock = p['stock'].lower()
    if p['dxf']:
        mat = (p['dxf'][0]['material'] or stock).lower()
        if 'steel' in mat or 'steel' in stock: return 'steel plate'
        if 'polycarbonate' in mat or 'polycarbonate' in stock: return 'router, polycarbonate'
        return 'router, aluminium'
    if p['printed'] or 'printed' in stock or 'printed' in name: return 'printed'
    if p['sub'] == 'Bumpers':
        if 'plywood' in stock: return 'plywood'
        if 'angle' in stock: return 'angle'
        return 'soft goods'
    if 'angle' in stock or re.search(r'\bangle\b', name): return 'angle'
    if re.search(r'^(2x1|1x1) x', stock) or ('tube' in stock and 'od' not in stock): return 'tube'
    if 'thunderhex' in stock or 'thunderhex' in name or re.search(r'\b(shaft|axle)\b', name): return 'shaft'
    if re.search(r'turned|lathe|spool|pivot hub|standoff|stop lug|stop post|tie rod|\brod\b|round', name + ' ' + stock): return 'turned'
    if re.search(r'spacer', name): return 'turned'
    if 'flat' in stock or ('plate' in stock and not p['dxf']): return 'flat bar'
    if 'polycarbonate' in stock: return 'hand-cut sheet'
    if re.search(r'chain clamp', name): return 'printed'
    return 'other'

MACHINE = {'router, aluminium': 'CNC router', 'router, polycarbonate': 'CNC router', 'steel plate': 'Send out, or mill and file', 'printed': '3D printer',
           'tube': 'Saw and mill', 'angle': 'Saw and drill press', 'shaft': 'Lathe', 'turned': 'Lathe', 'flat bar': 'Saw and drill press',
           'hand-cut sheet': 'Bandsaw and drill press', 'plywood': 'Saw and router', 'soft goods': 'Hand tools', 'other': 'Hand tools'}

def fnum(x): return ('%.3f' % x).rstrip('0').rstrip('.')
def qty_text(q): return 'one left and one right' if q == '1+1' else q

def route(p, kind):
    q = qty_text(p['qty'] or (str(p['printed']['qty']) if p['printed'] else str(p.get('model_qty') or 1)))
    name = p['name']; steps = []; checks = []
    if kind.startswith('router') or kind == 'steel plate':
        d = p['dxf'][0]; small = [(dia, n) for dia, n in d['holes'] if dia < 0.25]; big = [(dia, n) for dia, n in d['holes'] if dia >= 0.25]
        mat = {'router, aluminium': '6061 aluminium', 'router, polycarbonate': 'polycarbonate', 'steel plate': 'steel'}[kind]
        if '5052' in p['stock']: mat = '5052 aluminium'
        files = ' and '.join(f"`{x['file']}`" for x in p['dxf'])
        if kind == 'steel plate':
            steps = [f"Stock: {fnum(d['thick'])} in steel plate, at least {fnum(d['w'] + 0.5)} × {fnum(d['h'] + 0.5)} in for each part. Make {q}.",
                     f"This part is steel{' and has sharp inside corners' if d['sharp'] else ''}, so it is not a job for the router. Send the flat pattern {files} out for laser or waterjet cutting.",
                     "If it has to be made in the shop: rough it out on the bandsaw, mill the straight edges, and file the corners to the drawing.",
                     "Deburr every edge."]
            if small: steps.append("Drill the small holes on the drill press: " + ', '.join(f"{n} × {fnum(dia)} in ({hole_use(dia)[0]} drill)" for dia, n in small) + ".")
            checks = [f"Overall size {fnum(d['w'])} × {fnum(d['h'])} in.", "It fits its mating part and moves freely: see the drawing."]
        else:
            steps = [f"Stock: {fnum(d['thick'])} in {mat} sheet, at least {fnum(d['w'] + 1)} × {fnum(d['h'] + 1)} in for each part. Make {q}.",
                     f"Fix the sheet flat to the spoilboard. Load the flat pattern {files} in the router software. It is drawn in inches at full size."]
            if d['thick'] <= 0.07: steps.append("This sheet is thin and will lift. Hold it down across its whole area, not only at the edges.")
            if kind == 'router, polycarbonate': steps.append("Polycarbonate melts if the cutter rubs. Use a sharp single-flute cutter and keep the feed up.")
            if small:
                steps.append("Cut the small holes first. They are smaller than the 1/4 in cutter, so use a 1/8 in end mill, or spot them on the router and drill them on the drill press: "
                             + ', '.join(f"{n} × {fnum(dia)} in ({hole_use(dia)[0]})" for dia, n in small) + ".")
            if d['min_arc'] is not None and d['min_arc'] < 0.125:
                steps.append(f"The smallest inside radius on this part is {fnum(d['min_arc'])} in, which a 1/4 in cutter cannot reach. Cut those features with the 1/8 in end mill too.")
            if big:
                steps.append("Cut the larger holes with the 1/4 in end mill: " + ', '.join(f"{n} × {fnum(dia)} in" for dia, n in big) + "."
                             + (" For the 1.125 in bearing bores, cut one in scrap first and try a real bearing in it." if any(abs(dia - 1.125) < 0.002 for dia, _ in big) else ""))
            steps += ["Cut the outline last, with the 1/4 in end mill, leaving tabs so the part cannot move.", "Break the tabs and deburr every edge and hole."]
            if len(p['dxf']) > 1: steps.append("The left and right parts are different files. Mark each one L or R as it comes off the router.")
            checks = [f"Overall size {fnum(d['w'])} × {fnum(d['h'])} in.", f"Hole count: {sum(n for _, n in d['holes'])}."]
            if any(abs(dia - 1.125) < 0.002 for dia, _ in d['holes']): checks.append("A bearing presses into each 1.125 in bore without rocking.")
            if kind == 'router, polycarbonate': checks.append("No thread-locker on screws that touch this part. It cracks polycarbonate.")
    elif kind == 'tube':
        length = re.search(r'[\d.]+', p['size']); L = length.group(0) if length else 'the length on the drawing'
        steps = [f"Stock: {p['stock']}, 6061-T6. Make {q}, each {L} in long.",
                 "Saw each piece about 1/16 in over length.",
                 "Square both ends on the mill and bring the piece to length." + (" The elevator drawing asks for ±0.010 in, and the two uprights of one stage must match each other." if p['sub'] == 'Elevator' else ""),
                 "Drill the holes on the mill from the hole table on the drawing. Measure from the end the drawing names. Use a #9 drill (0.196 in) for #10 screws and a #20 drill (0.161 in) for 5/32 rivets.",
                 "Watch which walls each hole goes through. Rivet holes usually go through one wall only.",
                 "Deburr the ends and every hole, inside the tube as well."]
        checks = [f"Length {L} in.", "Hole positions against the part it bolts to.", "No burrs inside: a bearing block or plug must slide in."]
    elif kind == 'angle':
        steps = [f"Stock: {p['stock'] or 'aluminium angle, see the drawing'}. Make {q}." + (f" {p['size']}." if p['size'] else ""),
                 "Saw to length and file or sand the ends square.", "Mark the holes from the drawing, centre punch, and drill on the drill press.", "Deburr."]
        checks = ["Length and hole spacing against the mating part."]
    elif kind == 'shaft':
        text = (p['name'] + ' ' + p['size'] + ' ' + p['stock']).lower()
        steps = [f"Stock: {p['stock'] or '1/2 in ThunderHex'}. Make {q}." + (f" {p['size']}." if p['size'] else ""),
                 "Saw about 1/16 in over length.", "In the lathe, face both ends and bring the shaft to length."]
        if '1/4-20' in text: steps.append("Centre drill, drill with a #7 drill (0.201 in) and tap 1/4-20 in each end. Tap in the lathe so the thread runs true.")
        if '#10-32' in text: steps.append("Centre drill, drill with a #21 drill (0.159 in) and tap #10-32 in each end.")
        if 'snap ring' in text: steps.append("Cut the two snap ring grooves at the positions on the drawing.")
        if 'journal' in text: steps.append("Turn the round journals for the bearings to the size on the drawing. Sneak up on the size and test with a bearing.")
        steps.append("Break the sharp edges with a file.")
        checks = ["Length.", "A bearing slides on by hand.", "A screw runs into each tapped end by hand."] if 'tap' in text else ["Length.", "A bearing slides on by hand."]
    elif kind == 'turned':
        text = (p['name'] + ' ' + p['size'] + ' ' + p['stock'] + ' ' + ' '.join(p['labels'])).lower()
        steps = [f"Stock: {p['stock'] or 'round bar, see the drawing'}. Make {q}." + (f" {p['size']}." if p['size'] else ""),
                 "In the lathe, face the end, turn the outside to size and drill or bore the hole.", "Part it off a little long, turn it round and face it to length."]
        if '#10-32' in text and 'tap' in text or 'both ends' in text or 'one end' in text: steps.append("Drill and tap the ends as the drawing shows, in the lathe.")
        if 'hex' in text and 'mill' in text: steps.append("Mill the hex on the mill, holding the part in a collet block or a dividing head.")
        steps.append("Break the sharp edges.")
        checks = ["Length and diameters with calipers.", "It fits the shaft or screw it goes on."]
    elif kind == 'printed':
        pr = p['printed']; mat = pr['material'] if pr else 'see the printed parts list'
        steps = [f"Print {q} in {mat}.", "Use the STL file from the package. STL files are in millimetres, with the part sitting flat on the bed."]
        what = (pr['what'] if pr else p['name']).lower()
        if 'heat-set' in what: steps.append("Press in the heat-set inserts with a soldering iron after printing.")
        steps.append("Print one and try it against the real part it fits before printing the full set.")
        checks = ["It fits the purchased part or shaft it was drawn around.", "Holes are clear of stringing."]
    elif kind == 'flat bar':
        steps = [f"Stock: {p['stock']}. Make {q}. {p['size']}.".replace('..', '.'), "Saw to length and round the ends with a file.", "Mark, centre punch and drill the holes on the drill press.", "Deburr."]
        checks = ["Hole spacing: it sets how far a latch or pawl moves."]
    elif kind == 'hand-cut sheet':
        steps = [f"Stock: {p['stock']}. Make {q}. {p['size']}.".replace('..', '.'), "Cut on the bandsaw and sand the edges smooth.", "Drill the holes at assembly, through the part it mounts to.", "No thread-locker on its screws. It cracks polycarbonate."]
        checks = ["It sits flat and clear of moving parts."]
    elif kind == 'plywood':
        steps = [f"Stock: {p['stock']}. Make {q}. {p['size']}.", "Cut to size on the saw.", "Cut the pockets with the router or a Forstner bit, as the drawing shows.", "Sand the edges."]
        checks = ["Length against the frame.", "Pocket positions against the mounting brackets."]
    else:
        steps = [f"{p['stock'] or name}. Make {q}." + (f" {p['size']}." if p['size'] else ""), "Cut to size by hand and fit it at assembly."]
        checks = ["It fits where the drawing shows."]
    return steps, checks

def outline_svg(p):
    import ezdxf
    out = []
    for d in p['dxf'][:1]:
        msp = ezdxf.readfile(f"{PKG}/dxf/{d['folder']}/{d['file']}").modelspace()
        xs, ys, el = [], [], []
        for e in msp:
            t = e.dxftype()
            if t == 'LINE':
                a, b = e.dxf.start, e.dxf.end; xs += [a.x, b.x]; ys += [a.y, b.y]
                el.append(f'<line x1="{a.x:.3f}" y1="{-a.y:.3f}" x2="{b.x:.3f}" y2="{-b.y:.3f}"/>')
            elif t == 'CIRCLE':
                c, r = e.dxf.center, e.dxf.radius; xs += [c.x - r, c.x + r]; ys += [c.y - r, c.y + r]
                cls = ' class="small"' if r * 2 < 0.25 else ''
                el.append(f'<circle cx="{c.x:.3f}" cy="{-c.y:.3f}" r="{r:.3f}"{cls}/>')
            elif t == 'ARC':
                c, r = e.dxf.center, e.dxf.radius; a0, a1 = math.radians(e.dxf.start_angle), math.radians(e.dxf.end_angle)
                sweep = (e.dxf.end_angle - e.dxf.start_angle) % 360
                x0, y0, x1, y1 = c.x + r * math.cos(a0), c.y + r * math.sin(a0), c.x + r * math.cos(a1), c.y + r * math.sin(a1)
                xs += [x0, x1, c.x - r, c.x + r] if sweep > 180 else [x0, x1]; ys += [y0, y1, c.y - r, c.y + r] if sweep > 180 else [y0, y1]
                el.append(f'<path d="M{x0:.3f},{-y0:.3f} A{r:.3f},{r:.3f} 0 {1 if sweep > 180 else 0} 0 {x1:.3f},{-y1:.3f}"/>')
        m = max(max(xs) - min(xs), max(ys) - min(ys)) * 0.04 + 0.05
        vb = f"{min(xs) - m:.3f} {-max(ys) - m:.3f} {max(xs) - min(xs) + 2 * m:.3f} {max(ys) - min(ys) + 2 * m:.3f}"
        sw = max(max(xs) - min(xs), max(ys) - min(ys)) / 260
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" fill="none" stroke="currentColor" stroke-width="{sw:.4f}" stroke-linecap="round">' + ''.join(el) + '</svg>'
    return ''

# which drawing sheet shows each part best: the sheet of its own subsystem's drawing that names it most often
# (ties go to the later sheet, since detail sheets follow the assembly sheet)
counts = {}
for path in sorted(glob.glob('/tmp/robotA_*_drawings.txt')):
    pdf = os.path.basename(path).replace('.txt', '.pdf')
    for n, page in enumerate(open(path).read().split('\f'), 1):
        for m in re.finditer(r'(?<![A-Z0-9-])((?:[A-Z]{1,3}|EL)-(?:[A-Z]+-)?\d{3})(?![0-9])', page):
            counts.setdefault(m.group(1), collections.Counter())[(pdf, n)] += 1
pages = {}
SUBPDF = {'Bumpers': 'robotA_bumpers_revC_drawings.pdf', 'Climber': 'robotA_climber_revC_drawings.pdf', 'Drivebase': 'robotA_drivebase_revF_drawings.pdf',
          'Electronics': 'robotA_electronics_revD_drawings.pdf', 'Elevator': 'robotA_elevator_revH_drawings.pdf', 'Funnel': 'robotA_funnel_revF_drawings.pdf', 'Wrist and claw': 'robotA_wrist_claw_revE_drawings.pdf'}

site = []
for p in merged:
    kind = kind_of(p); steps, checks = route(p, kind)
    qty = p['qty'] or (str(p['printed']['qty']) if p['printed'] else str(p.get('model_qty', '')))
    base = re.sub(r'-[LR]$', '', p['mark'])
    home = p['pdf'] or SUBPDF.get(p['sub'], '')
    own = {k: v for k, v in counts.get(base, {}).items() if k[0] == home} or counts.get(base, {})
    pdf, page = max(own.items(), key=lambda kv: (kv[1], kv[0][1]))[0] if own else (home, p['page'] or 1)
    name = p['name']; name = re.sub(r'\s*\(DXF\)', '', name).strip(); name = name[0].upper() + name[1:] if name else p['mark']
    d = p['dxf'][0] if p['dxf'] else None
    site.append(dict(
        mark=p['mark'], slug=p['mark'].lower(), name=name, sub=p['sub'] or 'Robot', qty=qty_text(qty), kind=kind, machine=MACHINE[kind],
        stock=(p['stock'] or (f"{fnum(d['thick'])} in {'polycarbonate' if 'polycarbonate' in kind else 'steel' if kind == 'steel plate' else '6061 aluminium'} sheet" if d else '') or (p['printed']['material'] if p['printed'] else '')),
        size=p['size'] or (f"{fnum(d['w'])} × {fnum(d['h'])} in" if d else '') or (p['printed']['size'] + ' in' if p['printed'] else ''),
        detail=(p['printed']['what'] if p['printed'] else (p['labels'][0] if p['labels'] else '')),
        thick=d['thick'] if d else None, w=d['w'] if d else None, h=d['h'] if d else None,
        holes=[dict(dia=dia, n=n, drill=hole_use(dia)[0], use=hole_use(dia)[1]) for dia, n in d['holes']] if d else [],
        dxf=[f"{x['folder']}/{x['file']}" for x in p['dxf']], pdf=pdf, page=page, steps=steps, checks=checks, outline=outline_svg(p)))
order = ['Drivebase', 'Elevator', 'Wrist and claw', 'Funnel', 'Climber', 'Electronics', 'Bumpers', 'Robot']
site.sort(key=lambda s: (order.index(s['sub']), s['mark']))
os.makedirs(SITE + '/src/data', exist_ok=True)
json.dump(site, open(SITE + '/src/data/parts.json', 'w'), indent=1)
print(len(site), 'parts'); print(collections.Counter(s['kind'] for s in site)); print(collections.Counter(s['sub'] for s in site)); print(collections.Counter(s['machine'] for s in site))
for s in site:
    if s['kind'] in ('other', 'turned', 'hand-cut sheet', 'flat bar', 'soft goods', 'steel plate'): print(' ', s['kind'][:10].ljust(10), s['mark'].ljust(9), s['qty'].rjust(3), '|', s['name'][:50].ljust(50), '|', s['stock'][:28].ljust(28), '|', s['pdf'][7:20], s['page'])
