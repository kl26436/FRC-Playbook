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
const motorKv = (v: Values) => 12 / (v.rpm / 60); // volts per motor turn per second
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

// Mast sway: each upright is a beam standing up from the mast base (a cantilever).
// Everything is per upright, so the weights are halved. E is for aluminium.
const E_ALU = 10.0e6; // psi
const G_IN_S2 = 386.1;
const mastI = (v: Values) => (v.width * v.depth ** 3 - (v.width - 2 * v.wall) * (v.depth - 2 * v.wall) ** 3) / 12; // in^4
const mastS = (v: Values) => mastI(v) / (v.depth / 2); // in^3
const mastV = (v: Values) => (v.g * (v.wC + v.wB + v.wA)) / 2; // lb, sideways at the mast top
const mastM = (v: Values) => (v.g * (v.wC * (v.hC - v.L) + v.wB * (v.hB - v.L) + v.wA * (v.hA - v.L))) / 2; // lb·in at the mast top
const swayFree = (v: Values) => {
  const EI = E_ALU * mastI(v), V = mastV(v), M = mastM(v), L = v.L;
  const top = (V * L ** 3) / (3 * EI) + (M * L ** 2) / (2 * EI);
  const tilt = (V * L ** 2) / (2 * EI) + (M * L) / EI;
  return top + tilt * (v.hC - L); // the stages above the top lean with it
};
const braceMoment = (v: Values) => mastV(v) * (v.L - v.b) + mastM(v); // lb·in in the upright at the brace
const swayBraced = (v: Values) => {
  const EI = E_ALU * mastI(v), V = mastV(v), M = mastM(v), c = v.L - v.b;
  const tiltB = (braceMoment(v) * v.b) / (4 * EI); // upright held at the base, pinned at the brace
  const top = tiltB * c + (V * c ** 3) / (3 * EI) + (M * c ** 2) / (2 * EI);
  const tilt = tiltB + (V * c ** 2) / (2 * EI) + (M * c) / EI;
  return top + tilt * (v.hC - v.L);
};
const wobbleHz = (sway: number, g: number) => Math.sqrt(G_IN_S2 / (sway / g)) / (2 * Math.PI);
const braceForce = (v: Values) => {
  const push = mastV(v) + (3 * braceMoment(v)) / (2 * v.b); // sideways push the brace has to take
  const len = Math.hypot(v.x, v.b - v.yf);
  return push * (len / v.x);
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
      { key: 'drive', label: 'Drivebase', unit: 'lb', value: 37.69, step: 0.05 },
      { key: 'elev', label: 'Elevator', unit: 'lb', value: 32.15, step: 0.05 },
      { key: 'wrist', label: 'Wrist and claw', unit: 'lb', value: 12.93, step: 0.05 },
      { key: 'climb', label: 'Climber', unit: 'lb', value: 12.88, step: 0.05 },
      { key: 'funnel', label: 'Funnel', unit: 'lb', value: 6.85, step: 0.05 },
      { key: 'elec', label: 'Electronics', unit: 'lb', value: 3.95, step: 0.05 },
      { key: 'wiring', label: 'Wiring (estimate)', unit: 'lb', value: 4.0, step: 0.1 },
      { key: 'fasteners', label: 'Fasteners', unit: 'lb', value: 6.08, step: 0.05 },
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
    note: 'Modelled, except wiring, which is an estimate. Fasteners are counted from the model, plus an allowance. Battery and bumpers do not count toward the limit.',
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

  'motor-voltage': {
    title: 'Voltage to hold and to move a mechanism',
    group: 'Software',
    page: 'code/setpoints-and-control',
    inputs: [
      { key: 'rpm', label: 'Motor free speed', unit: 'rpm', value: 5800, step: 100 },
      { key: 'stallAmps', label: 'Motor stall current', unit: 'A', value: 483, step: 1 },
      { key: 'holdAmps', label: 'Current to hold still, each motor', unit: 'A', value: 15.8, step: 0.1 },
      { key: 'perTurn', label: 'Travel per motor turn', unit: 'in', value: 1.375, step: 0.005 },
      { key: 'speed', label: 'Speed', unit: 'in/s', value: 110, step: 5 },
    ],
    outputs: [
      { label: 'Voltage to hold (kG)', unit: 'V', digits: 2, compute: (v) => (v.holdAmps * 12) / v.stallAmps },
      { label: 'Voltage per motor turn a second (kV)', unit: 'V', digits: 3, compute: motorKv },
      { label: 'Voltage to hold and cruise', unit: 'V', digits: 1, compute: (v) => (v.holdAmps * 12) / v.stallAmps + (v.speed / v.perTurn) * motorKv(v) },
    ],
    steps: [
      'Winding resistance = 12 V ÷ stall current.',
      'kG = holding current × resistance.',
      'kV = 12 V ÷ free speed in turns per second.',
      'Motor speed = mechanism speed ÷ travel per turn. Cruise voltage = kG + motor speed × kV.',
    ],
    note: 'Calculated, for a Kraken X60 with FOC and no losses in the gearbox. If the answer is close to 12 V there is nothing left to speed up with.',
  },

  'steady-error': {
    title: 'How far off does it settle?',
    group: 'Software',
    page: 'code/setpoints-and-control',
    inputs: [
      { key: 'volts', label: 'Voltage it is short by (friction, or a wrong kG)', unit: 'V', value: 0.13, step: 0.01 },
      { key: 'kp', label: 'kP', unit: 'V per motor turn', value: 0.7, step: 0.1 },
      { key: 'perTurn', label: 'Travel per motor turn', unit: 'in', value: 1.375, step: 0.005 },
    ],
    outputs: [{ label: 'Settles off by', unit: 'in', digits: 2, compute: (v) => (v.volts / v.kp) * v.perTurn }],
    steps: [
      'With no integral term, the loop stops pushing when kP × error equals the voltage it is short by.',
      'Error in motor turns = voltage ÷ kP. Multiply by travel per turn.',
    ],
    note: 'Calculated. The 0.13 V is an example, not a measurement. Anything that waits for this mechanism needs a window wider than the answer.',
  },

  'stopping-distance': {
    title: 'How far does it go before it stops?',
    group: 'Software',
    page: 'code/superstructure',
    inputs: [
      { key: 'speed', label: 'Speed', unit: 'in/s', value: 110, step: 5 },
      { key: 'accel', label: 'Slowing-down rate', unit: 'in/s²', value: 212.3, step: 1 },
      { key: 'loop', label: 'Time before the new command arrives', unit: 's', value: 0.02, step: 0.005 },
    ],
    outputs: [
      { label: 'Before it starts to slow', unit: 'in', compute: (v) => v.speed * v.loop },
      { label: 'While slowing', unit: 'in', compute: (v) => (v.speed * v.speed) / (2 * v.accel) },
      { label: 'In all', unit: 'in', compute: (v) => v.speed * v.loop + (v.speed * v.speed) / (2 * v.accel) },
    ],
    steps: ['Distance before slowing = speed × loop time.', 'Distance while slowing = speed² ÷ (2 × slowing-down rate).'],
    note: 'Calculated. For the wrist, read the inches as degrees: 400 °/s and 1,600 °/s² is 58°.',
  },

  'ratchet-load': {
    title: 'How hard does the ratchet tooth get pushed?',
    group: 'Mechanical',
    page: 'subsystems/climber',
    inputs: [
      { key: 'weight', label: 'Robot as it hangs (battery and bumpers on)', unit: 'lb', value: 146.4, step: 0.5 },
      { key: 'lever', label: 'Fork pivot to centre of gravity, sideways', unit: 'in', value: 14.6, step: 0.1 },
      { key: 'ropes', label: 'Number of ropes (one per side)', unit: '', value: 2, step: 1 },
      { key: 'track', label: 'Rope track radius on the fork', unit: 'in', value: 3.5, step: 0.25 },
      { key: 'spool', label: 'Spool radius, core plus rope', unit: 'in', value: 0.563, step: 0.01 },
      { key: 'tooth', label: 'Radius where the pawl touches the tooth', unit: 'in', value: 0.43, step: 0.01 },
      { key: 'thick', label: 'Ratchet thickness', unit: 'in', value: 0.354, step: 0.01 },
      { key: 'teeth', label: 'Teeth on the ratchet wheel', unit: '', value: 18, step: 1 },
      { key: 'yield', label: 'Yield strength of the steel (assumed)', unit: 'psi', value: 60000, step: 5000 },
    ],
    outputs: [
      { label: 'Torque on the fork', unit: 'lb·in', digits: 0, compute: (v) => v.weight * v.lever },
      { label: 'Pull in each rope', unit: 'lb', digits: 0, compute: (v) => (v.weight * v.lever) / v.ropes / v.track },
      { label: 'Torque on each spool', unit: 'lb·in', digits: 0, compute: (v) => ((v.weight * v.lever) / v.ropes / v.track) * v.spool },
      { label: 'Push on one tooth', unit: 'lb', digits: 0, compute: (v) => (((v.weight * v.lever) / v.ropes / v.track) * v.spool) / v.tooth },
      { label: 'Flat the pawl tip wears to', unit: 'in', digits: 3, compute: (v) => (((v.weight * v.lever) / v.ropes / v.track) * v.spool) / v.tooth / (v.thick * v.yield) },
      { label: 'Fork can settle before a pawl catches', unit: '°', digits: 1, compute: (v) => 360 / v.teeth / (v.track / v.spool) },
    ],
    steps: [
      'Torque on the fork = robot weight × the distance from the fork pivot to the robot\'s centre of gravity (worst when that line is level).',
      'Pull in each rope = fork torque ÷ number of ropes ÷ track radius.',
      'Torque on each spool = rope pull × spool radius. This is what each ratchet has to hold.',
      'Push on one tooth = spool torque ÷ the radius where the pawl touches.',
      'The pawl touches along one edge, so the steel squashes a little until the flat is wide enough: width = push ÷ (thickness × yield strength).',
      'Fork settling = degrees per tooth ÷ (track radius ÷ spool radius), the ratio between the fork and the spool.',
    ],
    note: 'The weight and lever are modelled. WCP does not publish the ratchet steel, so the yield strength is a guess: ask, or test one. A flat a few thousandths wide is fine; one near the tooth depth (0.11 in) is not.',
  },

  'mast-brace': {
    title: 'Does the mast need a brace?',
    group: 'Mechanical',
    page: 'subsystems/elevator',
    inputs: [
      { key: 'g', label: 'Sideways acceleration (a hard stop or a hit)', unit: 'g', value: 1, step: 0.5 },
      { key: 'wC', label: 'Carriage and wrist weight', unit: 'lb', value: 19.8, step: 0.1 },
      { key: 'hC', label: 'Its height above the mast base', unit: 'in', value: 85.4, step: 0.5 },
      { key: 'wB', label: 'Stage B weight', unit: 'lb', value: 4.7, step: 0.1 },
      { key: 'hB', label: 'Its height above the mast base', unit: 'in', value: 62.6, step: 0.5 },
      { key: 'wA', label: 'Stage A weight', unit: 'lb', value: 5.7, step: 0.1 },
      { key: 'hA', label: 'Its height above the mast base', unit: 'in', value: 39.75, step: 0.5 },
      { key: 'L', label: 'Mast height (base to top)', unit: 'in', value: 35, step: 0.5 },
      { key: 'depth', label: 'Upright tube depth, in the sway direction', unit: 'in', value: 2, step: 0.5 },
      { key: 'width', label: 'Upright tube width', unit: 'in', value: 1, step: 0.5 },
      { key: 'wall', label: 'Upright tube wall', unit: 'in', value: 0.0625, step: 0.0625 },
      { key: 'b', label: 'Brace joins the upright at', unit: 'in', value: 27.25, step: 0.25 },
      { key: 'x', label: 'Brace foot, distance from the upright', unit: 'in', value: 10.5, step: 0.5 },
      { key: 'yf', label: 'Brace foot, height above the mast base', unit: 'in', value: 1.3, step: 0.1 },
      { key: 'gap', label: 'Distance between the two uprights', unit: 'in', value: 25, step: 0.5 },
    ],
    outputs: [
      { label: 'Carriage sway, no brace', unit: 'in', digits: 2, compute: swayFree },
      { label: 'Carriage sway, braced', unit: 'in', digits: 2, compute: swayBraced },
      { label: 'Peak stress in the upright, no brace', unit: 'psi', digits: 0, compute: (v) => (mastV(v) * v.L + mastM(v)) / mastS(v) },
      { label: 'Peak stress in the upright, braced', unit: 'psi', digits: 0, compute: (v) => braceMoment(v) / mastS(v) },
      { label: 'Wobble, no brace', unit: 'Hz', digits: 1, compute: (v) => wobbleHz(swayFree(v), v.g) },
      { label: 'Wobble, braced', unit: 'Hz', digits: 1, compute: (v) => wobbleHz(swayBraced(v), v.g) },
      { label: 'Push in each brace', unit: 'lb', digits: 0, compute: braceForce },
      { label: 'Twist if only one side is braced', unit: '°', digits: 1, compute: (v) => (((swayFree(v) - swayBraced(v)) / v.gap) * 180) / Math.PI },
    ],
    steps: [
      'Work on one upright, so halve the weights. Multiply each by the acceleration in g to get the sideways force.',
      'At the mast top: force V = the sum of the forces. Moment M = the sum of each force × (its height − mast height): the stages stick up above the top.',
      'Tube stiffness I = (width × depth³ − (width − 2 × wall) × (depth − 2 × wall)³) ÷ 12. E = 10,000,000 psi for aluminium.',
      'No brace (a cantilever): top moves V × L³ ÷ (3EI) + M × L² ÷ (2EI), and tilts V × L² ÷ (2EI) + M × L ÷ EI. The carriage moves the top movement + tilt × (carriage height − mast height).',
      'Braced (held at the base, pinned at the brace, height b): moment at the brace Mb = V × (L − b) + M. The upright turns Mb × b ÷ (4EI) there. Add the bit above the brace as a short cantilever, then lean the carriage as before.',
      'Stress = the biggest moment ÷ (I ÷ half the depth). Aluminium 6061 starts to bend for good at about 35,000 psi.',
      'Wobble = √(386 ÷ sway at 1 g) ÷ 2π. Below about 4 Hz, the driver can feel it and the camera sees it.',
      'Push in the brace = (V + 1.5 × Mb ÷ b) × brace length ÷ foot distance.',
      'Twist with one brace = (sway unbraced − sway braced) ÷ distance between the uprights, in radians. Times 57.3 for degrees.',
    ],
    note: 'The braced number treats the brace as solid. A computer model that lets the brace stretch a little gives 0.33 in instead of 0.29 and 5.5 Hz instead of 5.8, so the hand sums are close enough to decide with. The robot\'s numbers are with the carriage at the top.',
  },
};
