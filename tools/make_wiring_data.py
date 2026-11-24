"""Turn the CAD package's CAN map into the data the Wire it chapter draws from.

Input : lists/robotA_can_map.csv (four tables one after another: devices, other power, roboRIO ports, bus order)
Output: src/data/wiring.json
Run   : python3 tools/make_wiring_data.py [path to robotA_can_map.csv]

The robot code holds the same numbers in src/main/java/frc/robot/config/Ports.java, and its PortsTest compares the two.
"""
import sys, os, csv, json

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads/RobotA_final_2026-11-23/1_cad_package_rev3.2/lists/robotA_can_map.csv'
tables, cur = [], None
for row in csv.reader(open(SRC, newline='')):
    if not any(c.strip() for c in row): cur = None; continue
    if cur is None: cur = dict(head=[c.strip() for c in row], rows=[]); tables.append(cur)
    else: cur['rows'].append([c.strip() for c in row])
by = {t['head'][0]: t for t in tables}
devices = [dict(id=int(r[0]), bus=r[1], device=r[2], does=r[3], channel=r[4], protection=r[5]) for r in by['can_id']['rows']]
other = [dict(channel=r[0], load=r[1], protection=r[2]) for r in by['other power']['rows']]
ports = [dict(port=r[0], use=r[1]) for r in by['roboRIO port']['rows']]
buses = [dict(bus=r[0], order=[s.strip() for s in r[1].split('>')], note=r[2]) for r in by['bus']['rows']]
json.dump(dict(devices=devices, other=other, ports=ports, buses=buses), open(os.path.join(HERE, '..', 'src', 'data', 'wiring.json'), 'w'), indent=1)
print(len(devices), 'CAN devices,', len(other), 'other power rows,', len(ports), 'roboRIO ports,', [len(b['order']) for b in buses], 'stops on the two buses')
