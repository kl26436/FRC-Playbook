// Every calculator in the playbook is defined once, here.
// Pages show one with <Calc id="..." />, and the Math reference page lists them all.
// Default values are the robot's own numbers.

export type Values = Record<string, number>;

export interface CalcInput {
  key: string;
  label: string;
  unit: string;
  value: number;
  step?: number;
}

export interface CalcOutput {
  label: string;
  unit: string;
  digits?: number;
  compute: (v: Values) => number;
}

export interface CalcDef {
  title: string;
  group: 'Game' | 'Mechanical' | 'Software';
  page: string; // slug of the page that explains it
  inputs: CalcInput[];
  outputs: CalcOutput[];
  steps: string[];
  note?: string;
}

const N_M_TO_LB_IN = 8.851;
const G_FT_S2 = 32.17;

// Shared pieces, so each formula is written once.
const chainPerTurn = (v: Values) => v.teeth * v.pitch; // inches of chain per shaft turn
const elevatorFree = (v: Values) => (v.rpm / v.ratio / 60) * chainPerTurn(v) * v.stages;
const elevatorLoad = (v: Values) => v.a + 2 * v.b + 3 * v.c;
const elevatorShaftTorque = (v: Values) => (elevatorLoad(v) * chainPerTurn(v)) / (2 * Math.PI); // lb·in
const elevatorMotorTorque = (v: Values) =>
  elevatorShaftTorque(v) / N_M_TO_LB_IN / v.ratio / v.motors / (v.eff / 100); // N·m
const elevatorHoldAmps = (v: Values) => elevatorMotorTorque(v) / (v.stallTorque / v.stallAmps);
const wristTorquePerAmp = (v: Values) => (v.stallTorque / v.stallAmps) * v.ratio * N_M_TO_LB_IN * (v.eff / 100);
const climbRope = (v: Values) => (v.weight * v.lever) / v.ropes / v.track;
const climbRatio = (v: Values) => (v.track / v.spool) * v.gearbox;
const cycleSeconds = (v: Values) => (2 * v.dist) / v.speed + v.intake + v.score;
const weightTotal = (v: Values) =>
  v.drive + v.elev + v.wrist + v.climb + v.funnel + v.elec + v.wiring + v.fasteners;

// Wrist angles the code allows at each carriage height (the keep-out table, from the code's KeepOut.java).
export const keepOutZones = [
  { from: 0, to: 0.75, min: -90, max: -90 },
  { from: 0.75, to: 2, min: -90, max: 75 },
  { from: 2, to: 7, min: -75, max: 75 },
  { from: 7, to: 9, min: -60, max: 75 },
  { from: 9, to: 15, min: -45, max: 75 },
  { from: 15, to: 23, min: -40, max: 75 },
  { from: 23, to: 65.25, min: -90, max: 75 },
];
const zoneAt = (h: number) => keepOutZones.find((z) => h < z.to) ?? keepOutZones[keepOutZones.length - 1];
const profileAccelDist = (v: Values) => (v.cruise * v.cruise) / (2 * v.accel);
const profilePeak = (v: Values) => (2 * profileAccelDist(v) > v.travel ? Math.sqrt(v.accel * v.travel) : v.cruise);
const profileTime = (v: Values) => {
  const peak = profilePeak(v);
  const ramps = (peak * peak) / v.accel; // distance covered speeding up plus slowing down
  return (2 * peak) / v.accel + Math.max(0, v.travel - ramps) / peak;
};

// One reef tag seen by the nose camera: the same formula as SingleTagFix.distanceM in the robot code.
const TAG_IN = 6.5; // the black square of a field AprilTag
const TAG_CENTRE_IN = 12.13; // a reef tag's centre above the carpet
const LENS_IN = 9.58; // the camera lens above the carpet
const V_FOV_DEG = 56.2;
const V_PIXELS = 800;
const tagDistanceIn = (px: number) => {
  const tan = Math.tan((((px * V_FOV_DEG) / V_PIXELS) * Math.PI) / 180);
  const h = TAG_CENTRE_IN - TAG_IN / 2 - LENS_IN; // tag bottom above the lens (negative: the lens is a little higher)
  const disc = Math.max(0, TAG_IN * TAG_IN - 4 * tan * tan * h * (h + TAG_IN));
  return (TAG_IN + Math.sqrt(disc)) / (2 * tan);
};

export const calcs: Record<string, CalcDef> = {
  'cycle-value': {
    title: 'What a scoring cycle is worth',
    group: 'Game',
    page: 'read-the-game',
    inputs: [
      { key: 'cycle', label: 'Time for one cycle', unit: 's', value: 8, step: 0.5 },
      { key: 'time', label: 'Time spent cycling', unit: 's', value: 115, step: 5 },
      { key: 'points', label: 'Points per piece', unit: 'pts', value: 5, step: 1 },
    ],
    outputs: [
      { label: 'Pieces scored', unit: '', digits: 0, compute: (v) => Math.floor(v.time / v.cycle) },
      { label: 'Points scored', unit: 'pts', digits: 0, compute: (v) => Math.floor(v.time / v.cycle) * v.points },
      { label: 'Points per second', unit: 'pts/s', digits: 2, compute: (v) => v.points / v.cycle },
    ],
    steps: [
      'Pieces = time spent cycling ÷ time for one cycle, rounded down.',
      'Points = pieces × points per piece.',
      'Points per second = points per piece ÷ time for one cycle.',
    ],
    note: 'Assumed: an 8 s cycle and 115 s of cycling (teleop is 135 s; this leaves 20 s for the climb).',
  },

  'cycle-time': {
    title: 'Cycle time budget',
    group: 'Game',
    page: 'choose-what-to-be-good-at',
    inputs: [
      { key: 'dist', label: 'Distance, one way', unit: 'ft', value: 11.5, step: 0.5 },
      { key: 'speed', label: 'Average driving speed', unit: 'ft/s', value: 6, step: 0.5 },
      { key: 'intake', label: 'Time to pick up', unit: 's', value: 1.5, step: 0.1 },
      { key: 'score', label: 'Time to line up and score', unit: 's', value: 2.5, step: 0.1 },
    ],
    outputs: [
      { label: 'Driving, both ways', unit: 's', compute: (v) => (2 * v.dist) / v.speed },
      { label: 'Whole cycle', unit: 's', compute: cycleSeconds },
      { label: 'Share of the cycle spent driving', unit: '%', digits: 0, compute: (v) => ((2 * v.dist) / v.speed / cycleSeconds(v)) * 100 },
    ],
    steps: [
      'Driving time = 2 × distance ÷ average speed.',
      'Cycle time = driving time + pick-up time + scoring time.',
    ],
    note: 'Assumed: the speed and the two handling times. Average speed is far below top speed, because the robot starts and stops every trip.',
  },

  'frame-fit': {
    title: 'Frame size check',
    group: 'Mechanical',
    page: 'concept',
    inputs: [
      { key: 'len', label: 'Frame length', unit: 'in', value: 28, step: 0.5 },
      { key: 'wid', label: 'Frame width', unit: 'in', value: 28, step: 0.5 },
      { key: 'bumper', label: 'Bumper thickness, each side', unit: 'in', value: 3.25, step: 0.25 },
      { key: 'limit', label: 'Perimeter limit', unit: 'in', value: 120, step: 1 },
    ],
    outputs: [
      { label: 'Frame perimeter', unit: 'in', compute: (v) => 2 * (v.len + v.wid) },
      { label: 'Room left under the limit', unit: 'in', compute: (v) => v.limit - 2 * (v.len + v.wid) },
      { label: 'Width with bumpers on', unit: 'in', compute: (v) => v.wid + 2 * v.bumper },
    ],
    steps: [
      'Perimeter = 2 × (length + width).',
      'Width with bumpers = frame width + 2 × bumper thickness.',
    ],
  },

  'weight-budget': {
    title: 'Weight budget',
    group: 'Mechanical',
    page: 'subsystems/from-concept-to-design',
    inputs: [
      { key: 'drive', label: 'Drivebase', unit: 'lb', value: 37.7, step: 0.1 },
      { key: 'elev', label: 'Elevator', unit: 'lb', value: 31.3, step: 0.1 },
      { key: 'wrist', label: 'Wrist and claw', unit: 'lb', value: 12.9, step: 0.1 },
      { key: 'climb', label: 'Climber', unit: 'lb', value: 12.9, step: 0.1 },
      { key: 'funnel', label: 'Funnel', unit: 'lb', value: 6.9, step: 0.1 },
      { key: 'elec', label: 'Electronics', unit: 'lb', value: 4.0, step: 0.1 },
      { key: 'wiring', label: 'Wiring (estimate)', unit: 'lb', value: 4.0, step: 0.1 },
      { key: 'fasteners', label: 'Fasteners', unit: 'lb', value: 6.1, step: 0.1 },
      { key: 'limit', label: 'Weight limit', unit: 'lb', value: 115, step: 1 },
    ],
    outputs: [
      { label: 'Robot weight', unit: 'lb', compute: weightTotal },
      { label: 'Room left under the limit', unit: 'lb', compute: (v) => v.limit - weightTotal(v) },
    ],
    steps: [
      'Robot weight = the sum of every subsystem, plus wiring and fasteners.',
      'Room left = weight limit − robot weight. A negative number means the robot is over.',
    ],
    note: 'Modelled, except wiring, which is an estimate. The rows are rounded, so they add to 115.8 lb; the model total is 115.68 lb. Battery and bumpers do not count toward the limit.',
  },

  'drive-speed': {
    title: 'Top driving speed',
    group: 'Mechanical',
    page: 'subsystems/drivebase',
    inputs: [
      { key: 'rpm', label: 'Motor free speed', unit: 'rpm', value: 6000, step: 100 },
      { key: 'ratio', label: 'Gear ratio (motor turns per wheel turn)', unit: ': 1', value: 6.75, step: 0.01 },
      { key: 'wheel', label: 'Wheel diameter', unit: 'in', value: 3.947, step: 0.001 },
    ],
    outputs: [
      { label: 'Wheel speed', unit: 'rpm', digits: 0, compute: (v) => v.rpm / v.ratio },
      { label: 'Top speed, no load', unit: 'ft/s', compute: (v) => ((v.rpm / v.ratio) * Math.PI * v.wheel) / 12 / 60 },
    ],
    steps: [
      'Wheel speed = motor speed ÷ gear ratio.',
      'Distance per wheel turn = π × wheel diameter.',
      'Speed = wheel speed × distance per turn, changed from inches per minute to feet per second (÷ 12, ÷ 60).',
    ],
    note: 'Calculated. The wheel diameter is from the model; measure the real wheel.',
  },

  'elevator-speed': {
    title: 'Elevator speed',
    group: 'Mechanical',
    page: 'subsystems/elevator',
    inputs: [
      { key: 'rpm', label: 'Motor free speed', unit: 'rpm', value: 6000, step: 100 },
      { key: 'ratio', label: 'Gearbox ratio', unit: ': 1', value: 12, step: 0.5 },
      { key: 'teeth', label: 'Sprocket teeth', unit: 'teeth', value: 22, step: 1 },
      { key: 'pitch', label: 'Chain pitch', unit: 'in', value: 0.25, step: 0.125 },
      { key: 'stages', label: 'Carriage travel per inch of first stage', unit: '×', value: 3, step: 1 },
      { key: 'cruise', label: 'Cruise speed, share of free speed', unit: '%', value: 80, step: 5 },
      { key: 'travel', label: 'Carriage travel', unit: 'in', value: 66, step: 1 },
    ],
    outputs: [
      { label: 'Chain moved per shaft turn', unit: 'in', compute: chainPerTurn },
      { label: 'Carriage free speed', unit: 'in/s', compute: elevatorFree },
      { label: 'Cruise speed', unit: 'in/s', digits: 0, compute: (v) => (elevatorFree(v) * v.cruise) / 100 },
      { label: 'Full travel at cruise speed alone', unit: 's', digits: 2, compute: (v) => v.travel / ((elevatorFree(v) * v.cruise) / 100) },
    ],
    steps: [
      'Shaft speed = motor speed ÷ gearbox ratio, then ÷ 60 for turns per second.',
      'Chain per shaft turn = sprocket teeth × chain pitch.',
      'First-stage speed = shaft speed × chain per turn.',
      'Carriage speed = first-stage speed × 3, because each stage rides on the one below it.',
      'Cruise speed = free speed × the share you choose.',
      'Travel ÷ cruise speed is the time at cruise speed alone. A real move also has to speed up and slow down: the motion profile calculator in Code it gives the whole move, 1.11 s for this elevator.',
    ],
    note: 'Calculated.',
  },

  'elevator-hold': {
    title: 'Current and voltage to hold the elevator still',
    group: 'Mechanical',
    page: 'subsystems/elevator',
    inputs: [
      { key: 'a', label: 'Weight moving with stage A', unit: 'lb', value: 5.71, step: 0.01 },
      { key: 'b', label: 'Weight moving with stage B', unit: 'lb', value: 4.68, step: 0.01 },
      { key: 'c', label: 'Carriage, wrist and claw', unit: 'lb', value: 19.83, step: 0.01 },
      { key: 'teeth', label: 'Sprocket teeth', unit: 'teeth', value: 22, step: 1 },
      { key: 'pitch', label: 'Chain pitch', unit: 'in', value: 0.25, step: 0.125 },
      { key: 'ratio', label: 'Gearbox ratio', unit: ': 1', value: 12, step: 0.5 },
      { key: 'motors', label: 'Motors', unit: '', value: 2, step: 1 },
      { key: 'eff', label: 'Gearbox efficiency', unit: '%', value: 85, step: 1 },
      { key: 'stallTorque', label: 'Motor stall torque', unit: 'N·m', value: 7.09, step: 0.01 },
      { key: 'stallAmps', label: 'Motor stall current', unit: 'A', value: 366, step: 1 },
    ],
    outputs: [
      { label: 'Load felt at the drive', unit: 'lbf', compute: elevatorLoad },
      { label: 'Torque on the drive shaft', unit: 'lb·in', compute: elevatorShaftTorque },
      { label: 'Torque from each motor', unit: 'N·m', digits: 2, compute: elevatorMotorTorque },
      { label: 'Current in each motor', unit: 'A', digits: 0, compute: elevatorHoldAmps },
      { label: 'Voltage to hold (a starting kG)', unit: 'V', digits: 2, compute: (v) => elevatorHoldAmps(v) * (12 / v.stallAmps) },
    ],
    steps: [
      'Load at the drive = stage A weight × 1 + stage B weight × 2 + carriage weight × 3. A stage that moves twice as far for the same chain travel pulls back twice as hard.',
      'Shaft torque = load × sprocket radius. The radius is chain per turn ÷ 2π.',
      'Torque per motor = shaft torque ÷ gearbox ratio ÷ number of motors ÷ efficiency. (1 N·m = 8.851 lb·in.)',
      'Current = torque per motor ÷ the motor\'s torque per amp, which is stall torque ÷ stall current.',
      'Voltage = current × winding resistance, which is 12 V ÷ stall current.',
    ],
    note: 'Calculated from modelled weights. Fasteners and game pieces are not included. The real kG comes from tuning; this says where to start.',
  },

  'slide-friction': {
    title: 'Will it slide on its own?',
    group: 'Mechanical',
    page: 'subsystems/funnel',
    inputs: [{ key: 'angle', label: 'Slope of the tray', unit: '°', value: 30.5, step: 0.5 }],
    outputs: [
      { label: 'Highest friction coefficient that still slides', unit: '', digits: 2, compute: (v) => Math.tan((v.angle * Math.PI) / 180) },
    ],
    steps: ['A piece slides on its own when the friction coefficient is less than tan(slope).'],
    note: 'The friction between a coral and the tray is assumed. Measure it with a tilt test: raise one end of the tray material until the coral starts to slide, then take tan of that angle.',
  },

  'tip-accel': {
    title: 'How hard can it accelerate before it tips?',
    group: 'Mechanical',
    page: 'subsystems/elevator',
    inputs: [{ key: 'angle', label: 'Tip angle, worst side', unit: '°', value: 27.5, step: 0.5 }],
    outputs: [
      { label: 'Largest safe acceleration', unit: 'g', digits: 2, compute: (v) => Math.tan((v.angle * Math.PI) / 180) },
      { label: 'The same, in feet per second squared', unit: 'ft/s²', compute: (v) => Math.tan((v.angle * Math.PI) / 180) * G_FT_S2 },
    ],
    steps: [
      'Tip angle is the angle between straight down and the line from the centre of gravity to the wheel contact line.',
      'Largest safe acceleration, in g = tan(tip angle).',
      'Multiply by 32.17 for feet per second squared.',
    ],
    note: 'Modelled, with battery and bumpers on. The default is the worst case: carriage at the top, wrist level.',
  },

  'wrist-hold': {
    title: 'Current to hold the wrist still',
    group: 'Mechanical',
    page: 'subsystems/wrist-and-claw',
    inputs: [
      { key: 'torque', label: 'Worst holding torque at the pivot', unit: 'lb·in', value: 137, step: 1 },
      { key: 'ratio', label: 'Overall ratio, motor to wrist', unit: ': 1', value: 60, step: 1 },
      { key: 'eff', label: 'Efficiency', unit: '%', value: 85, step: 1 },
      { key: 'stallTorque', label: 'Motor stall torque', unit: 'N·m', value: 7.09, step: 0.01 },
      { key: 'stallAmps', label: 'Motor stall current', unit: 'A', value: 366, step: 1 },
    ],
    outputs: [
      { label: 'Torque at the wrist for each amp', unit: 'lb·in per A', digits: 2, compute: wristTorquePerAmp },
      { label: 'Current to hold', unit: 'A', compute: (v) => v.torque / wristTorquePerAmp(v) },
    ],
    steps: [
      'Motor torque per amp = stall torque ÷ stall current.',
      'At the wrist, that is multiplied by the ratio and the efficiency. (1 N·m = 8.851 lb·in.)',
      'Current to hold = holding torque ÷ torque per amp.',
      'The default is the worst case: holding an algae. Try 110 lb·in for an empty wrist and 124 with a coral.',
    ],
    note: 'Modelled torque, calculated current. The wrist motor starts with a 40 A limit, so holding uses under half of it.',
  },

  climb: {
    title: 'What it takes to lift the robot',
    group: 'Mechanical',
    page: 'subsystems/climber',
    inputs: [
      { key: 'weight', label: 'Robot weight, with battery and bumpers', unit: 'lb', value: 146.4, step: 0.1 },
      { key: 'lever', label: 'Fork pivot to the centre of gravity', unit: 'in', value: 14.6, step: 0.1 },
      { key: 'ropes', label: 'Ropes', unit: '', value: 2, step: 1 },
      { key: 'track', label: 'Rope track radius on the fork', unit: 'in', value: 3.5, step: 0.1 },
      { key: 'spool', label: 'Spool radius, to the rope centre', unit: 'in', value: 0.5625, step: 0.01 },
      { key: 'gearbox', label: 'Gearbox ratio', unit: ': 1', value: 25, step: 1 },
      { key: 'eff', label: 'Gearbox efficiency', unit: '%', value: 85, step: 1 },
      { key: 'rpm', label: 'Motor free speed', unit: 'rpm', value: 6000, step: 100 },
      { key: 'stallTorque', label: 'Motor stall torque', unit: 'N·m', value: 7.09, step: 0.01 },
      { key: 'stallAmps', label: 'Motor stall current', unit: 'A', value: 366, step: 1 },
    ],
    outputs: [
      { label: 'Torque to turn the fork', unit: 'lb·in', digits: 0, compute: (v) => v.weight * v.lever },
      { label: 'Pull in each rope', unit: 'lb', digits: 0, compute: climbRope },
      { label: 'Overall ratio, motor to fork', unit: ': 1', digits: 0, compute: climbRatio },
      { label: 'Current in each motor', unit: 'A', digits: 0, compute: (v) => (climbRope(v) * v.spool) / N_M_TO_LB_IN / v.gearbox / (v.eff / 100) / (v.stallTorque / v.stallAmps) },
      { label: 'Fork speed with no load', unit: '°/s', digits: 0, compute: (v) => (v.rpm / climbRatio(v)) * 6 },
    ],
    steps: [
      'Fork torque = robot weight × the distance from the pivot to the centre of gravity.',
      'Pull in each rope = fork torque ÷ number of ropes ÷ track radius.',
      'Overall ratio = (track radius ÷ spool radius) × gearbox ratio. A small spool is a big reduction for free.',
      'Motor torque = rope pull × spool radius ÷ gearbox ratio ÷ efficiency. Current = motor torque ÷ torque per amp.',
    ],
    note: 'Modelled weight and lever, calculated loads. The weight is an estimate until a real robot is on a scale. Each motor is on a 40 A breaker with a 60 A limit to start.',
  },

  'tag-distance': {
    title: 'How far away is the tag?',
    group: 'Software',
    page: 'code/vision',
    inputs: [{ key: 'px', label: 'Height of the tag in the picture', unit: 'px', value: 134, step: 1 }],
    outputs: [
      { label: 'Angle the tag fills, top to bottom', unit: '°', digits: 2, compute: (v) => (v.px * V_FOV_DEG) / V_PIXELS },
      { label: 'Distance from camera to tag', unit: 'in', compute: (v) => tagDistanceIn(v.px) },
      { label: 'The same, in metres', unit: 'm', digits: 2, compute: (v) => tagDistanceIn(v.px) * 0.0254 },
      { label: 'Change in distance if the height is one pixel off', unit: 'in', digits: 2, compute: (v) => Math.abs(tagDistanceIn(v.px) - tagDistanceIn(v.px + 1)) },
    ],
    steps: [
      'Angle = height in pixels × 56.2° ÷ 800. The camera sees 56.2° from top to bottom, spread over 800 pixels.',
      'The tag is 6.5 in tall. From far away, distance ≈ 6.5 in ÷ tan(angle).',
      'The exact formula also allows for the lens sitting 9.58 in up and the tag centre 12.13 in up. For this robot that changes the answer by about 1% at half a metre, and less from further away.',
      'Try 34 px, the tag from 4 m away, and 134 px, the tag from 1 m away.',
    ],
    note: 'Calculated. No real camera has been tested yet. Far away, one pixel is several inches, which is why the code only trusts the tag it is driving toward and gets more exact as it closes in.',
  },

  'keep-out': {
    title: 'What wrist angles are allowed at this height?',
    group: 'Software',
    page: 'code/superstructure',
    inputs: [{ key: 'h', label: 'Carriage height', unit: 'in', value: 17.5, step: 0.25 }],
    outputs: [
      { label: 'Lowest wrist angle allowed', unit: '°', digits: 0, compute: (v) => zoneAt(v.h).min },
      { label: 'Highest wrist angle allowed', unit: '°', digits: 0, compute: (v) => zoneAt(v.h).max },
    ],
    steps: [
      'Find the band of the keep-out table that the carriage height falls in.',
      'Read off the lowest and highest wrist angle for that band. −90° is stowed, 0° is level, +75° is tipped all the way up.',
    ],
    note: 'Modelled: the bands come from clash checks on the CAD. The band from 0.75 to 2 in still has to be checked by hand on the real robot.',
  },

  'motion-profile': {
    title: 'How long does a profiled move take?',
    group: 'Software',
    page: 'code/superstructure',
    inputs: [
      { key: 'travel', label: 'Distance to move', unit: 'in', value: 65.25, step: 0.25 },
      { key: 'cruise', label: 'Cruise speed', unit: 'in/s', value: 110, step: 5 },
      { key: 'accel', label: 'Acceleration', unit: 'in/s²', value: 212.3, step: 1 },
    ],
    outputs: [
      { label: 'Top speed reached', unit: 'in/s', digits: 0, compute: profilePeak },
      { label: 'Time spent speeding up', unit: 's', digits: 2, compute: (v) => profilePeak(v) / v.accel },
      { label: 'Distance covered speeding up', unit: 'in', compute: (v) => (profilePeak(v) * profilePeak(v)) / (2 * v.accel) },
      { label: 'Whole move', unit: 's', digits: 2, compute: profileTime },
    ],
    steps: [
      'Time to reach cruise speed = cruise speed ÷ acceleration.',
      'Distance covered while speeding up = cruise speed² ÷ (2 × acceleration). Slowing down takes the same distance again.',
      'If those two distances add up to more than the move, the mechanism never reaches cruise speed. Its top speed is then the square root of (acceleration × distance).',
      'Whole move = time speeding up + time at cruise + time slowing down.',
    ],
    note: 'Calculated. The acceleration is 0.55 g (g is 386.09 in/s²), just under the 0.6 g cap the code sets for the elevator.',
  },
};
