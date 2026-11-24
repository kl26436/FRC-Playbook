# Design decisions and math log

The source the playbook pages are written from (chapters 2 to 4, 9 and 10). It is not published as a page itself. It covers the mechanical design, Nov 19 to 23, 2026, at CAD package 3.2. Code decisions live in the code repo's own docs and appear here only where the CAD forced them.

**How sure are we.** Nothing here has been built. Every number is one of three kinds:
- *calculated*: worked by hand or in a script from catalogue data;
- *modelled*: measured on the build123d model (weights, clearances, clash sweeps);
- *assumed*: a guess that still needs measuring.

None is *tested* yet.

**Who decided.** "Kevin" marks a call Kevin made. "Design" marks a call made during the CAD work that Kevin has not overruled.

Motor data used everywhere below: Kraken X60 (trapezoidal) 6,000 rpm free, 7.09 N·m stall, 366 A stall, 2 A free. Kraken X60 with FOC (Phoenix Pro) is 5,800 rpm, 9.37 N·m, 483 A. The CAD math uses the trapezoidal numbers, which is the conservative case for torque. Source: WCP Kraken X60 motor performance page.

---

## 1. Decisions, in date order

Each entry gives the decision, the options, the reason and the numbers.

### Nov 19: Architecture (Design, from the kickoff brief)
- **Decided:** a swerve base, a continuous three-stage elevator, a coral wrist that the coral passes straight through, an algae claw under the wrist, a station funnel at the back and a deep-cage climber.
- **Why:** the game rewards short station-to-reef cycles (about 11 ft each way) and L4 (12 branches, 5 points, 7 in auto, never blocked by algae). The deep cage is worth 12 points, and one deep climb plus two parks makes the Barge RP. One architecture covers every must and should on the priority list.
- **Options:** a floor-feeder robot, dropped because the stations feed reliably and the floor pickup adds weight; a separate algae arm, dropped because a claw under the wrist reuses the elevator.

### Nov 19: Frame 28 × 28 in (Design)
- **Why:** a reef face is 37.8 in wide and cages hang 42.9 in apart. A 34.5 in robot with bumpers fits beside a partner at both.
- **Rules:** 112 in perimeter (limit 120, R104); 39.7 in starting height in the concept (limit 42).

### Nov 19: Elevator on the WCP GreyT 3-stage pattern (Design)
- **Decided:** 2x1 x 1/16 tube, WCP bearing blocks, cascade rigging. Each stage moves 22 in relative to its parent, so the carriage travels 66 in and the wrist pivot runs 24.5 to 90.5 in.
- **Why:** with continuous rigging the light carriage moves first. The station, L2, the processor and the low algae all sit in the first 22 in of carriage travel.
- **Changed on day one:** the SDS MK4i front modules clashed with the mast, so the mast moved back to X = 4.5 in.

### Nov 19 to 21: Elevator drive (Design)
- **Decided:** two Kraken X60, a 12:1 two-stage gearbox (12T:48T then 18T:54T, 20 DP gears) and 22T #25 sprockets on a cross shaft.
- **Correction:** the kickoff page says 15T:45T for the second stage. The model and drawings use 18T:54T. Both are 3:1, so the ratio is the same.
- **No down-haul:** the carriage weight brings the stages down, which saves a rope run and a tensioner. The cost is that the elevator cannot be driven down faster than gravity. (Design)

### Nov 20: Pass-through wrist on stub axles (Design)
- **Decided:** the wrist pivots on two stub axles (W-102), not a through-shaft, so the bore stays open and coral enters from behind.
- **Coral rollers:** a Kraken X44 driving HTD 5 mm belts.
- **Wrist drive:** a Kraken X60, a MAXPlanetary 16:1 and 16T to 60T #25 chain, so 16 × 60/16 = 60:1 overall. A through-bore absolute encoder sits on the pivot.
- **Claw:** reworked so the rollers can throw algae over the net rim.

### Nov 21: One Limelight 4 in the nose instead of three cameras (Design)
- **Options:** two cameras on the mast plus one high at the rear (the kickoff plan), or one camera low at the front.
- **Why:** the reef AprilTags are only 12.1 in off the carpet, so one camera low in the nose sees them at scoring distance. That means fewer boxes, wires and pounds.
- **Numbers:** mounted on printed tower CAM-101, pitched up 12°. The body centre is at (13.0, 0, 9.45).

### Nov 21: CANrange sensors instead of beam breaks (Design)
- **Why:** the sensors are on CAN, so no DIO wires run up the elevator. CANrange 61 sees the coral seated in the wrist and CANrange 62 sees algae in the claw.

### Nov 21: Two CAN buses (Design)
- **Decided:** the CANivore (CAN FD) carries only the drivetrain and gyro. The roboRIO bus carries everything that moves above the frame. IDs are grouped by tens by location.
- **Why:** a broken wire in the elevator harness cannot take the drivetrain down.

### Nov 21: L4 pose (Design)
- **Decided:** the wrist at −53° with the pivot at 90.5 in, which uses all the travel. The kickoff concept had −50° at 87 in.
- **Why:** worked from the real pivot travel and the bumper-to-branch distance. The coral travels 6.7 in past the branch tip. This is the first pose to test on a real reef.

### Nov 21: Every hole drilled in the model, fasteners placed from the holes (Design)
- **Why:** a script finds every hole and places the screw, nut, rivet or rivnut it needs. It also flags any hole with nothing through it, and any part that needs a hole the model does not show. Fasteners are then counted, not guessed, for the weight.

### Nov 22: Climber moves to a rear cage bay (Kevin)
- **Options:** the kickoff concept, a fork on the left rail that strafes into the cage and rotates 108°; or a fork on one axle across the back of the robot.
- **Why:** checking the left-rail fork in CAD showed it could not do the deep climb. Kevin chose a rear cage bay with a hinged funnel.
- **Numbers:** the pivot is at X = −13.5, 16 in up. The fork swings from stowed (90°) to level, stopping at −2°, and winds back to 88°; the hard stop is at 97°.

### Nov 22: Funnel hinges out of the way (Design, forced by the climber)
- **Decided:** the tray, walls and cross tubes are one unit, hinged on the right posts. It swings 90° up and over to the right. A servo latch holds it closed, and two strands of latex tubing throw it open onto a stop.
- **Why:** this clears the rear cage bay for the climb and keeps the 30.5° slide into the wrist.
- **Rule for the code:** one shot per match. Nothing closes it again until the pit.

### Nov 22: Deploy springs redesigned (Kevin picked option B)
- **Problem:** no stock torsion spring with enough torque fits the 0.49 in space between the arm plate and the tower plate.
- **Options:**
  - A, extension springs in that space: rejected, because the lever arm is only about 0.8 in and the springs would run near their stretch limit.
  - **B, torsion springs inside the fork on a hex axle that does not turn: picked.**
  - C, widening the space: rejected, because it moves the gearboxes and motors outboard and ripples into the drivebase and funnel.
- **As built:** McMaster 9271K689 (RH) and 9271K624 (LH): 0.92 OD, 0.095 wire, 17.1 in·lb at 180°. The larger 1.038 OD springs stood 0.02 in behind the frame perimeter. The moving leg rests on a pin in the arm plate. Printed hub CL-208 sets the preload in 60° steps on the hex.

### Nov 22: Weight passes (Design)
- **Wrist and claw:** side plates and claw plates went from 3/16 to 1/8 in.
- **Elevator Rev G:** 3/16 cap plates, the E-403 pivot plates on 8 bolts a side, and inside corners at R 0.13 so a 1/4 in end mill can cut them.
- **Drivebase:** the real MK4i weight (4.15 lb a module) replaced the estimate.

### Nov 23: Mast brace E-103 riveted to the upright (Design, from Kevin's question)
- **Problem:** Kevin asked what the brace does. It was bolted at the foot and only touched the upright at the top, so it carried nothing.
- **Decided (Rev H):** four rivets through the brace's inner wall into the right upright, set through 0.40 in access holes in the opposite wall. The foot is cut 22.2° so it sits flat on the rail. The brace is 1x1 x 1/16, 29.91 in long.

### Nov 23: Funnel eye bolt cut to length (Design)
- The 2434K598 eye bolt thread is cut to 1.25 in after the nut is on. It now clears climber tower plate CL-101-R by 0.19 in; before, it touched.

### Nov 23: Stay about 0.7 lb over the weight limit (Kevin)
- **Numbers:** 115.68 lb modelled against the 115 lb limit (R103, battery and bumpers not counted). Kevin accepted 115.63; the six sprocket screws and the pawl shims added 0.05 lb. 12.4 lb of the total is estimated: wiring 4.0 lb and a fastener allowance.
- **Options not taken:** 2x1 frame rails from 1/8 to 1/16 wall (about −3.6 lb), lightening pockets in the tube walls, or one climber motor instead of two.
- **Note:** the robot cannot pass inspection at this weight. The playbook should show it as a known miss with the options above.

### Nov 23: Wrist keep-out table (Design)
- **Decided:** a six-zone table giving the lowest wrist angle the code may allow at each carriage height.

  | Carriage height (in) | Lowest wrist angle |
  | --- | --- |
  | below 1.25 | stowed (−90) only |
  | 1.25 to 7 | −75 |
  | 7 to 9 | −60 |
  | 9 to 15 | −45 |
  | 15 to 23 | −40 |
  | 23 to 66 | any |

- **How:** 3,256 exact clash tests (15 carriage heights × 12 wrist angles, each against every part) checked the wrist against the funnel, the fork, the camera, every elevator stage at its own height, the frame and the modules.
- **The unstow move:** every angle is clear at exactly 1.25 in. So hold the carriage at 1.25 while the wrist leaves or returns to stow.

### Nov 23: Every hole accounted for (Design, CAD package 3.2)
- **Before:** 26 holes had nothing through them.
- **After, 0.** Each of the 26 now has a fastener or a part through it, or is marked as a spare:
  - The W-104 60T sprocket's six bolt holes were drawn 30° away from its W-209 standoffs. They now line up, and their six screws are in the model. The real part does not change: 30° is exactly five teeth on a 60-tooth sprocket.
  - W-201 and C-101 are one part file for both sides, so each plate carries the other side's holes. The 15 holes like this are listed as spares.
  - The funnel open-stop screw is drawn in the funnel hardware file, not the detail fastener file.
  - The E-406 holes take the energy chain's end link, which is drawn only as an envelope.
  - The climber rope-anchor holes are spares.
- **Fasteners:** 617 placed, 0 running into another part, 5.06 lb counted.

### Nov 23: Climber pawl shims (Design)
- **Problem:** the pawl (3/16 thick) sits on a 1/4 long spacer, which leaves 0.0625 in of axial play.
- **Decided:** three 0.014 in shims (McMaster 99040A614, 5/16 ID × 1/2 OD) on the spacer under each pawl. The play drops to 0.25 − 0.1875 − 3 × 0.014 = 0.0205 in, and the pawl stays in line with the ratchet wheel.
- **Check on real parts:** the pawl must still swing free.

---

## 2. The math, worked with the robot's numbers

Each section is a candidate for a playbook calculator: the inputs in the first line, then the steps.

### 2.1 Drive speed
- **Inputs:** Kraken X60 6,000 rpm, SDS MK4i L2 ratio 6.75:1, wheel tread 3.947 in (as modelled; measure the real wheel).
- Wheel speed = 6,000 / 6.75 = 889 rpm.
- Speed = 889 × π × 3.947 in / 12 = 918 ft/min = **15.3 ft/s free** (calculated).

### 2.2 Elevator speed
- **Inputs:** 6,000 rpm motor, 12:1 gearbox, 22T #25 sprocket. #25 pitch is 0.25 in, so the chain moves 22 × 0.25 = 5.5 in per shaft turn.
- Shaft = 6,000 / 12 = 500 rpm = 8.33 rev/s.
- Stage A = 8.33 × 5.5 = 45.8 in/s. In a cascade the carriage moves 3 times as far as stage A, so the carriage free speed is 3 × 45.8 = **137.5 in/s** (calculated).
- **Design cruise:** 110 in/s (80% of free). Full travel is 66 / 110 = 0.6 s plus the speed-up and slow-down.
- **Code (miss):** held at 65 in/s, because at 110 the Phoenix Motion Magic profile in simulation did not slow down in time and hit the top stop. The untried fix is to keep Phoenix in rotor rotations and convert to inches in the IO class. Teaching point: a mechanism can be fast enough on paper and still be limited by the control setup.

### 2.3 Elevator holding current and kG
- **Inputs (modelled):** mass that moves with each stage. Stage A 5.71 lb, stage B 4.68 lb, and the carriage with the whole wrist and claw 19.83 lb. Fasteners and game pieces are not included.
- **Virtual work:** in a cascade, stage B moves 2× and the carriage 3× as far as stage A. The load felt at the stage A drive is 5.71 × 1 + 4.68 × 2 + 19.83 × 3 = **74.6 lbf**.
- **Shaft torque:** the effective sprocket radius is 5.5 / 2π = 0.875 in, so the torque is 74.6 × 0.875 = 65.3 lb·in = 7.38 N·m.
- **Per motor:** 7.38 / 12 / 2 = 0.31 N·m. At 85% gearbox efficiency that is 0.36 N·m.
- **Current to hold:** 0.36 / (7.09 / 366 N·m per A) = **about 19 A per motor** (calculated).
- **Voltage to hold (kG):** winding resistance is 12 V / 366 A = 0.033 Ω, so 19 A × 0.033 Ω = **about 0.6 V**. The real kG comes from tuning, but this says where to start.
- **Margin:** the starting stator limit is 60 A, about 3 times the holding current. The rest is available for acceleration.

### 2.4 Wrist holding torque and current
- **Inputs:** 60:1 overall, 85% efficiency.
- **Torque constant at the wrist:** 7.09 / 366 × 60 × 8.851 × 0.85 = **8.74 lb·in per amp** (8.851 converts N·m to lb·in).
- **Worst holding torque (modelled, from the wrist's mass and centre of gravity):**

  | Holding | Worst torque | Current |
  | --- | --- | --- |
  | Empty | 110 lb·in at +20° | 12.6 A |
  | With a coral | 124 lb·in | 14.2 A |
  | With an algae | 137 lb·in | 15.6 A |

- **Starting stator limit:** 40 A.

### 2.5 Climb: torque, rope, ratio, current, speed
- **Inputs (modelled, climber study):** the robot as it hangs, 146.4 lb, plus 21 lb for the cage's share, 167.4 lb in all. The lever from the fork pivot to the centre of gravity is 14.6 in. The study ran before the last weight changes; rerun it if the weight moves much.
- **Torque on the fork:** about **2,140 lb·in**.
- **Rope:** two ropes, each on a 3.5 in radius track, so each carries 2,140 / 2 / 3.5 = **305 lb**.
- **Spool:** a 1.00 in core plus the rope gives an effective radius of about 0.563 in. The spool torque is 305 × 0.563 = 172 lb·in = 19.4 N·m.
- **Ratio:** track to spool is 3.5 / 0.563 = 6.22:1, times the MAXPlanetary 25:1, which is **about 156:1 overall**.
- **Motor:** 19.4 / 25 = 0.78 N·m, or 0.91 N·m with losses. That is 0.91 / 0.0194 = **about 47 A per motor**, under the 60 A starting limit and on a 40 A breaker for a few seconds.
- **Speed:** 6,000 rpm / 156 = 38.5 rpm = **231°/s with no load**. The 88° climb takes well under 1 s at free speed, and longer under load.
- **Check against the kickoff brief:** it estimated about 2,000 lb·in and about 150:1. The model gives 2,140 lb·in and 156:1.

### 2.6 Pawl: how far the fork can settle
- **Inputs:** a 16-tooth ratchet wheel, so 360 / 16 = 22.5° of wheel per tooth.
- The wheel is on the spool shaft. The fork turns 6.22 times slower than the spool, so one tooth lets the fork settle at most 22.5 / 6.22 = **3.6°** before a pawl bites.

### 2.7 Deploy springs against gravity
- **Inputs:** fork 3.64 lb, centre of gravity 2.54 in in front of the pivot when stowed.
- **Gravity holds it up:** 11.7 lb·in at 97°, 9.3 at 90°, 0 at 66°. Below 66° gravity deploys it and the rope controls the speed.
- **Spring rate:** 17.1 lb·in / 180° = 0.095 lb·in per degree. Wound 140° at stow, that is 13.3 lb·in per spring, **26.6 lb·in for the pair**.
- **Net at stow (90°):** 26.6 − 9.3 = **17.3 lb·in pushing it out**. The springs never wind past 180°.

### 2.8 How fast the robot can speed up before it tips
- **Rule:** the robot tips when acceleration × centre-of-gravity height exceeds g × the horizontal distance from the centre of gravity to the wheel contact line. So the largest safe acceleration, in g, is tan(tip angle).

  | Pose (on the field, battery and bumpers on) | Centre of gravity height | Tip angle, worst side | Largest safe acceleration |
  | --- | --- | --- | --- |
  | Stowed | 9.6 in | 46.9° | 1.07 g |
  | Carriage halfway (33 in), wrist level | 15.7 in | 35.3° | 0.71 g |
  | Carriage at the top (66 in), wrist level | 21.5 in | 27.5° | **0.52 g** (16.7 ft/s²) |

- **For the code:** limit drive acceleration whenever the carriage is high.

### 2.9 Funnel slope and friction
- The tray is at 30.5°. A coral slides on its own if the static friction coefficient between PVC and polycarbonate is under tan(30.5°) = **0.59**.
- That coefficient is *assumed*. Measure it with a tilt test: lay a coral on a sheet of the tray polycarbonate and raise one end until the coral starts to slide. tan(angle) is the coefficient. This makes a good first student exercise.

### 2.10 Bolt circles and teeth
- A bolt circle on a sprocket can be turned by any multiple of 360 / teeth without changing the part. On the W-104 60T sprocket, 360 / 60 = 6°, so 30° is 5 teeth and the part is identical.

### 2.11 Weight budget, modelled vs estimated

| Package | lb |
| --- | --- |
| Drivebase | 37.7 |
| Elevator | 31.3 |
| Wrist and claw | 12.9 |
| Climber | 12.9 |
| Funnel | 6.9 |
| Electronics | 4.0 |
| Wiring (estimate) | 4.0 |
| Fasteners (counted plus allowance) | 6.1 |
| **Robot (R103)** | **115.7** |
| Battery | 12.9 |
| Bumpers | 14.3 |

The kickoff estimate was 106 lb. The difference is fasteners that were counted rather than guessed, real vendor weights, and parts the concept never had (stops, brackets, mounts, springs).

### 2.12 Reef geometry used for the poses (from the field drawings)
- **Branch heights:** L1 18 in, L2 31.9 in, L3 47.6 in, L4 72 in.
- **Algae on the reef:** a ball on the L2 branches has its centre 35.6 in up and blocks L2 and L3. A ball on the L3 branches sits at 51.5 in and blocks only L3.
- **Scoring poses:** 17.25 in off the face along its normal, and 6.47 in left or right for the branch.

---

## 3. Misses and open items (chapter 10 material)
- **Weight:** about 0.7 lb over (Kevin chose to leave it for now). See the options above.
- **Elevator cruise speed** in code: 65 in/s against the 110 design (2.2).
- **Wrist keep-out table:** read literally, it gave no way to leave stow. Found in the clash grid, fixed with the 1.25 in unstow band.
- **Climber concept:** the left-rail fork could not do the deep climb. It was found in CAD before anything was cut.
- **Deploy spring:** the first design needed a spring that does not exist.
- **Things only real parts can prove:** the climber on a real cage (it holds by friction on the sleeves and gates), the claw grip on a real ball, the coral turning end-on in the funnel, the net rim height (88.9 in read from the drawing), the processor pose (marked marginal) and the MAXPlanetary rating at the climber.

## Sources
- The build123d model and its checks: `mass_summary.json`, `climber/study_summary.json`, `wrist_summary.json`, `assembly/fasteners.json` and the CAD package 3.2 README.
- The REEFSCAPE kickoff brief (Part 1 analysis, Part 2 design changes), the software handoff, and the climber deploy-spring design note (Nov 22).
- The 2025 Game Manual and Field Drawings in this project.
- WCP Kraken X60 motor performance: https://docs.wcproducts.com/kraken-x60/kraken-x60-motor/overview-and-features/motor-performance
