"""Pull the made-parts tables out of the drawing PDFs' text (pdftotext -layout)."""
import re, json, sys, glob, os, collections
MARK = re.compile(r'^(?:[A-Z]{1,3}|CAM|EL)-(?:[A-Z]+-)?\d{3}(?:-[LR])?$|^EL-[A-Z]+(?:-P)?$|^SP-[A-Z]+-[0-9.]+$')
QTY = re.compile(r'^\d+(?:\+\d+)?$')
SUB = {'bumpers': 'Bumpers', 'climber': 'Climber', 'drivebase': 'Drivebase', 'electronics': 'Electronics',
       'elevator': 'Elevator', 'funnel': 'Funnel', 'wrist_claw': 'Wrist and claw', 'robot_layout_weight': 'Robot'}
rows = []
for path in sorted(glob.glob('/tmp/robotA_*_drawings.txt')):
    key = re.search(r'robotA_(.+?)(?:_rev[A-Z])?_drawings', os.path.basename(path)).group(1)
    sheet = 1
    pages = open(path).read().split('\f')
    for pno, page in enumerate(pages, 1):
        for line in page.split('\n'):
            cells = [c.strip() for c in re.split(r' {3,}', line.strip()) if c.strip()]
            for i, c in enumerate(cells):
                if not MARK.match(c): continue
                rest = cells[i + 1:]
                # MARK | name | stock | qty | size...   or   MARK | name | qty
                if len(rest) >= 3 and QTY.match(rest[2]):
                    rows.append(dict(mark=c, name=rest[0], stock=rest[1], qty=rest[2], size=rest[3] if len(rest) > 3 and not MARK.match(rest[3]) else '', sub=SUB[key], pdf=os.path.basename(path).replace('.txt', '.pdf'), page=pno))
                elif len(rest) >= 2 and QTY.match(rest[1]):
                    rows.append(dict(mark=c, name=rest[0], stock='', qty=rest[1], size='', sub=SUB[key], pdf=os.path.basename(path).replace('.txt', '.pdf'), page=pno))
json.dump(rows, open('/home/claude/gen/parts/drawing_rows.json', 'w'), indent=1)
by = collections.Counter(r['sub'] for r in rows)
print(len(rows), dict(by))
for r in rows: print(f"{r['sub'][:8]:8} p{r['page']} {r['mark']:10} | {r['name'][:58]:58} | {r['stock'][:24]:24} | {r['qty']:4} | {r['size'][:50]}")
