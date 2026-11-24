"""Read the setpoints, gains and limits out of the robot code and write src/data/control.json.

    python3 tools/code-pages/make_control_data.py <clone of kl26436/ClaudeBot>

The Setpoints and control page draws its table, its chart and its gain tables from that file, so the numbers on
the page are the ones in the code at the commit named in the file.
"""
import json, pathlib, re, subprocess, sys

REPO = pathlib.Path(sys.argv[1])
SRC = REPO / 'src/main/java/frc/robot'
OUT = pathlib.Path(__file__).resolve().parents[2] / 'src/data/control.json'


def consts(path, names=None, block=None):
    """Every `static final double NAME = expression;` in a file (or in one named inner class)."""
    text = (SRC / path).read_text()
    if block:
        start = text.index(f'class {block} ')
        text = text[start:text.index('\n    }\n', start)]
    found = {}
    for name, expr, note in re.findall(r'static final double (\w+) =\s*([^;]+);[ \t]*(?://[ \t]*(.*))?', text):
        if names and name not in names:
            continue
        if not re.fullmatch(r'[\d.\s*/+()-]+', expr):
            continue  # built from other constants: worked out below where it is needed
        found[name] = {'value': round(eval(expr), 4), 'placeholder': 'PLACEHOLDER' in note}
    return found


def val(d, k):
    return d[k]['value']


setpoints = []
text = (SRC / 'config/Setpoints.java').read_text()
for name, c, w, note in re.findall(r'^\s+([A-Z0-9_]+)\(([-\d.]+), ([-\d.]+)\)[,;][ \t]*(?://[ \t]*(.*))?$', text, re.M):
    setpoints.append({'name': name, 'carriageIn': float(c), 'wristDeg': float(w), 'placeholder': 'PLACEHOLDER' in note})
assert len(setpoints) == 12, setpoints

tol = consts('config/Setpoints.java')
ek = consts('config/RobotConstants.java', block='ElevatorK')
wk = consts('config/RobotConstants.java', block='WristK')
eg = consts('subsystems/elevator/ElevatorIOTalonFX.java', {'KG', 'KS', 'KV', 'KA', 'KP', 'KD'})
wg = consts('subsystems/wrist/WristIOTalonFX.java', {'KG', 'KS', 'KV', 'KA', 'KP', 'KD'})
dp = consts('subsystems/drive/DriveToPoint.java')
sw = consts('subsystems/drive/SwerveSubsystem.java', {'AT_TARGET_M', 'AT_TARGET_DEG'})
assert len(eg) == 6 and len(wg) == 6, (eg, wg)

in_per_rot = val(ek, 'SPROCKET_TEETH') * val(ek, 'CHAIN_PITCH_IN') * val(ek, 'STAGES') / val(ek, 'GEAR_RATIO')
commit = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()

data = {
    'commit': commit,
    'setpoints': setpoints,
    'carriageTolIn': val(tol, 'CARRIAGE_TOL_IN'),
    'wristTolDeg': val(tol, 'WRIST_TOL_DEG'),
    'elevator': {
        'gains': {k: eg[k]['value'] for k in ('KG', 'KS', 'KV', 'KA', 'KP', 'KD')},
        'inPerMotorRot': round(in_per_rot, 4),
        'cruiseInPerS': val(ek, 'CRUISE_IN_PER_S'),
        'accelInPerS2': val(ek, 'ACCEL_IN_PER_S2'),
        'softMaxIn': val(ek, 'SOFT_MAX_IN'),
        'travelIn': val(ek, 'TRAVEL_IN'),
        'statorLimitA': val(ek, 'STATOR_LIMIT_A'),
    },
    'wrist': {
        'gains': {k: wg[k]['value'] for k in ('KG', 'KS', 'KV', 'KA', 'KP', 'KD')},
        'cruiseDegPerS': val(wk, 'CRUISE_DEG_PER_S'),
        'accelDegPerS2': val(wk, 'ACCEL_DEG_PER_S2'),
        'minDeg': val(wk, 'MIN_DEG'),
        'maxDeg': val(wk, 'MAX_DEG'),
        'statorLimitA': val(wk, 'STATOR_LIMIT_A'),
        'gearRatio': val(wk, 'GEAR_RATIO'),
    },
    'drive': {
        'kpAuto': val(dp, 'KP_AUTO'),
        'kpTeleop': val(dp, 'KP_TELEOP'),
        'kd': val(dp, 'KD'),
        'atTargetM': val(sw, 'AT_TARGET_M'),
        'atTargetDeg': val(sw, 'AT_TARGET_DEG'),
    },
}
OUT.write_text(json.dumps(data, indent=2) + '\n')
print('wrote', OUT, 'from commit', commit)
print(json.dumps({k: v for k, v in data.items() if k != 'setpoints'}))
