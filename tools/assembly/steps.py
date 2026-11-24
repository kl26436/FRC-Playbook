"""The assembly steps for every mechanism and for the whole robot, written once here.

Running this file writes public/robot-viewer/assembly.json, which both the Assemble it pages and the 3D viewer read.

A step is: t (title), do (what to do, one action a line), hw (hardware it uses), check (how to know it is right),
warn (what goes wrong), parts (which model parts appear at this step), pose (optional: move the model for this step).
A part selector is a part mark ("E-101"), a /regular expression/ matched against the model's part label,
{"re": ..., "sub": n, "nth": n} to narrow a match, or {"from": [set, first, last]} to take whole steps from another set.
Source: the CAD session's build instructions (2026-11-23) and the drawing notes. Nothing here has been assembled.
"""
import json, os

FRAME = ["D-101", "D-102", "/^MK4i/", "D-103", "D-105", "/WCP-0374/", "CL-102", "/tube plug \\(CL-102\\)/", "D-201"]

SETS = {}

SETS["drivebase"] = dict(
    title="Drivebase", sheets="Drivebase drawings, Rev G", base=[],
    intro="The frame is a 28 × 28 in square of aluminium tube. Its corners are the four swerve modules. A thin belly pan is riveted underneath.",
    steps=[
        dict(t="Cut and drill the four rails", parts=["D-101", "D-102"],
             do=["Check the rail length and hole pattern against the SDS MK4i frame drawing before cutting the first rail.",
                 "Cut two side rails and two end rails from 2 × 1 in tube with a 1/8 in wall. Each is 20.00 in long.",
                 "Drill each rail from the hole table on the drawing. Measure from the end the drawing names.",
                 "Drill the holes the other mechanisms need as well. They are on the last sheet: climber tubes, funnel posts, bumper brackets, the breaker plate.",
                 "Leave the rivet holes for parts that go on later. Drill those through the part itself when it is in place."],
             check="The right rail has four holes the left does not. The front rail has three the back does not."),
        dict(t="Bolt the rails to the swerve modules", parts=["/^MK4i/"],
             do=["Stand a module at each corner.",
                 "Lay each rail end on a module's bottom plate. The rails stop 4 in short of each corner, and the module fills the gap.",
                 "Bolt down through the rail into the module. Six screws for each module."],
             hw=["24 × #10-32 × 2.50 in socket head screws"],
             check="The frame is 28 in across both ways, and both diagonals measure the same."),
        dict(t="Add the cross member and the spine", parts=["D-103", "D-105", "/WCP-0374/"],
             do=["Press a tube plug into each end of the cross member and into the front end of the spine.",
                 "Fix each plug with three screws through the tube wall: two in one wide face, one in the other.",
                 "Bolt the cross member between the side rails, through the rails into its plugs.",
                 "Bolt the spine to the middle of the front rail the same way."],
             hw=["3 × WCP-0374 tube plugs", "9 × #10-32 × 3/8 in button head screws, into the plug sides", "9 × #10-32 × 1.50 in socket head screws, through the rails"]),
        dict(t="Fit the two climber base tubes", parts=["CL-102", "/tube plug \\(CL-102\\)/"],
             do=["These belong to the climber. They go in now because the belly pan rivets to them.",
                 "Each runs from the back rail to the cross member, one each side of where the battery will sit.",
                 "Bolt into the plug in each end. The screw goes in through the 3/8 in access hole in the far wall of the rail."],
             hw=["4 × WCP-2069 tube plugs", "8 × #10-32 × 1/2 in screws"],
             check="The gap between the two tubes is 7.15 in. The battery is 7.10 in wide."),
        dict(t="Rivet on the belly pan", parts=["D-201"],
             do=["Rivet the pan up into the rails, the cross member, the spine and both base tubes.",
                 "Use the longer rivets where the pan meets a 1/8 in wall, and the shorter ones under the thin base tubes."],
             hw=["39 × 5/32 in rivets, grip 0.188 to 0.25 in (97517A035), into the frame", "8 × 5/32 in rivets, grip 0.126 to 0.187 in (97517A032), into the base tubes"]),
        dict(t="Set the rivnuts", parts=[],
             do=["In the rail tops: eight 1/4-20 rivnuts for the bumper brackets.",
                 "In the right rail: two #10-32 rivnuts for the breaker plate.",
                 "On top of the cross member: four #10-32 rivnuts for cable tie mounts.",
                 "In the belly pan: fourteen #10-32 rivnuts and two #8-32 rivnuts for the electronics."],
             warn="Check the drill size against the rivnuts you bought before drilling a rail.",
             check="A screw runs into every rivnut by hand."),
        dict(t="Mount the camera", parts=["CAM-101", "/^CAM Limelight/"],
             do=["Bolt the camera to the back plate of its printed tower with four screws and lock nuts. Snug only: the camera's case is plastic.",
                 "Bolt the tower down through the front rail with two long screws, 1.55 in either side of centre."],
             hw=["4 × #10-32 × 1.50 in socket head screws and lock nuts", "2 × #10-32 × 2.75 in socket head screws and lock nuts"]),
    ])

SETS["electronics"] = dict(
    title="Electronics boards", sheets="Electronics drawings, Rev D", base=FRAME,
    intro="Every box sits on the belly pan, except the breaker on the right rail and the radio on a funnel post. Mount them now, before the elevator covers them. Wire them last.",
    steps=[
        dict(t="Power hub and small power module", parts=["/^EL-PDH/", "/^EL-MPM/", "/EL-SP \\(EL-(PDH|MPM)\\)/"],
             do=["Set every device's CAN ID before it goes on the robot.",
                 "Stand each box on four printed spacers over its rivnuts.",
                 "Screw down through the box and the spacer into the pan."],
             hw=["8 × #10-32 × 1.00 in button head screws", "8 × printed spacers, 3/8 in across and 1/4 in tall"]),
        dict(t="CANivore, roboRIO and gyro", parts=["/^EL-CANV/", "/EL-SP \\(EL-CANV\\)/", "/^EL-RIO/", "/^EL-PIG/"],
             do=["CANivore: two screws down through it and a spacer each, into the two #8-32 rivnuts.",
                 "roboRIO: screw its plate to its underside with four flat head screws, then screw the plate to the pan.",
                 "Gyro: two screws down through it and the pan, lock nuts underneath. Arrow pointing forward."],
             hw=["2 × #8-32 × 1.25 in pan head screws (CANivore)", "4 × #4-40 × 3/8 in flat head screws and 2 × #10-32 × 1/2 in button head screws (roboRIO)", "2 × #4-40 × 3/4 in pan head screws and lock nuts (gyro)"],
             warn="Decide which way the roboRIO's connectors face before drilling its plate. The plate fits either way round.",
             check="The gyro sits flat and does not rock. It gives the heading for the whole robot."),
        dict(t="Main breaker", parts=["/^EL-BRK/"],
             do=["Press four threaded inserts into the printed breaker plate with a soldering iron.",
                 "Screw the breaker to the plate.",
                 "Screw the plate to the two rivnuts on top of the right rail."],
             hw=["4 × #6-32 heat-set inserts (93365A130)", "4 × #6-32 × 1/2 in button head screws", "2 × #10-32 × 5/8 in button head screws"],
             check="The breaker's button can be reached from the right side of the robot."),
        dict(t="Battery stop, strap and battery", parts=["B-101", "B-102", "/^B-103/", "B-104", "/^EL-BAT/", "/^Battery/"],
             do=["Rivet the stop angle to the pan in front of where the battery sits.",
                 "Fit a strap loop on top of each climber base tube.",
                 "Lower the battery in over the back rail. It sits across the back, between the base tubes.",
                 "Run the strap over the top, through both loops, and close the buckle."],
             hw=["4 × 5/32 in rivets, 1/8 in grip", "2 × strap loops (McMaster 8030T11) on #10-32 rivnuts", "1 in strap with a cam buckle"],
             check="The battery cannot slide forward, back or sideways, and cannot lift."),
        dict(t="Cable tie mounts", parts=["EL-TIE"],
             do=["Screw four printed tie mounts to the pan beside the side rails.", "Screw four more to the top of the cross member."],
             hw=["8 × #10-32 × 3/8 in button head screws"]),
        dict(t="Battery connector", parts=["/^EL-SB50/"],
             do=["Bolt the connector to its printed bracket with two screws and lock nuts."],
             hw=["2 × #10-32 × 1.00 in socket head screws and lock nuts"]),
        dict(t="Radio, once the funnel posts are on", parts=["/^EL-RAD/", "/radio plate stand-off/", "/^VHB/", "/^Zip tie/"], show=["F-103-L"],
             do=["Stick the radio to its aluminium plate with foam tape. This radio has no screw holes.",
                 "Add two zip ties round the radio, through the notches in its sides and behind the plate.",
                 "Bolt the plate to the outside of the left middle funnel post, on its two printed stand-offs."],
             hw=["About 3 in of VHB foam tape", "2 × 1/4 in zip ties", "2 × #10-32 × 1.75 in socket head screws and lock nuts"],
             check="The radio's lights face outward."),
    ])

SETS["elevator"] = dict(
    title="Elevator", sheets="Elevator drawings, Rev J", base=FRAME,
    intro="Four frames slide inside each other: the mast, two stages and the carriage. A chain lifts the first stage. Ropes over pulleys make the other two follow.",
    steps=[
        dict(t="Cut the tubes", parts=[],
             do=["All the elevator tube is 2 × 1 in with a 1/16 in wall.",
                 "Cut every tube square to within 0.010 in.",
                 "The two uprights of one stage must match each other within 0.005 in."],
             warn="A stage with uprights of different lengths will bind. Cut each pair together."),
        dict(t="Build the mast", parts=["E-101", "E-102", "/tube plug E-10[12]/", "/mast top/"],
             do=["The mast base tube plugs into the two side rails.",
                 "Stand an upright at each end of it, joined with tube plugs.",
                 "Bolt a bearing block to the top of each upright."],
             check="The mast's outer faces are 26.00 in apart, which is the inside width of the frame."),
        dict(t="Brace it", parts=["E-103", "E-104", "D-301", "D-302"],
             do=["There is a diagonal brace on each side. The two are a mirror pair, cut from the same length of tube.",
                 "Cut the foot of each brace 22.2° off square, so it stands flat on its side rail.",
                 "Rivet a gusset to each brace and to the inside wall of its rail.",
                 "Clamp the top of each brace against the outer wall of its upright. Drill its four top holes through into the upright.",
                 "Rivet from inside the brace, reaching through the access holes in its outer wall. A long nosepiece helps.",
                 "Rivet the two foot angles between the rail tops and the mast, and the two tie angles between the mast base and the spine."],
             hw=["8 × rivets, braces to uprights", "12 × rivets for the foot angles", "8 × rivets for the tie angles"],
             warn="Fit both braces. With only one, the mast twists when the robot turns hard, and the stages bind.",
             check="The mast stands square to the frame and does not rock."),
        dict(t="Rivet on the drive plates", parts=["E-502", "E-503", "E-506"],
             do=["Rivet a shaft bearing plate to the outside of each upright, low down.",
                 "Rivet an idler plate to the outside and one to the inside of each upright, near the top."]),
        dict(t="Build the gearbox", parts=["E-504", "/^Gear /", "E-505", "E-509", "E-510", "/Snap ring/", "/gearbox tie/", "/Kraken X60 lift/", "/bearing intermediate shaft/", "/cross shaft, gearbox plate/", "/Shim washer 1\\/8/"],
             do=["Build the gearbox between its two 1/4 in plates.",
                 "A 12-tooth gear on each motor drives the 48-tooth gear. On the same shaft, an 18-tooth gear drives the 54-tooth gear. Together that is 12:1.",
                 "Countersink the three motor holes that sit under the big gears, from the inside face, and use flat head screws there.",
                 "Bolt the gearbox feet through the spine with two long screws, lock nuts and four shim washers."],
             hw=["#10-32 × 1/2 in flat head screws (91253A003) under the gears", "2 × #10-32 × 2.25 in socket head screws and lock nuts", "4 × 1/8 in shim washers"],
             warn="The big gears run 0.097 in off the plate. A raised screw head under them will hit."),
        dict(t="Fit the cross shaft and the idlers", parts=["E-501", "/cross shaft, mast plate/", "/sprocket drive/", "/hub drive/", "E-508", "/collar, 1\\/2 in hex inboard/", "/Shim washer 0.035/", "/washer cross shaft/", "E-507", "/sprocket idler/", "/hub idler/", "E-511", "/bearing idler/", "/washer idler/"],
             do=["Slide the cross shaft through the gearbox and through the bearing in each mast plate.",
                 "Put a 22-tooth sprocket on each end, 11.34 in from the centre. That is far enough out for the chains to pass over the swerve modules.",
                 "Fit an idler sprocket on its short shaft between the two idler plates, at the top of each upright."],
             check="The shaft spins freely by hand and cannot slide sideways."),
        dict(t="Build the first stage", parts=["E-201", "E-202", "/tube plug E-20[12]/", "/stage A (bottom|top)/", "E-206"],
             do=["Join the bottom tube and the two uprights with tube plugs.",
                 "Bolt bearing blocks at the bottom, where the stage rolls on the mast, and at the top, where it guides the next stage.",
                 "Bolt a cap plate to the top of each upright, with a pulley block under it."],
             hw=["#10-32 × 3/8 in screws for the cap plates and pulley blocks"],
             warn="A 1/2 in screw in a cap plate would reach the pulley. Use 3/8 in."),
        dict(t="Build the second stage", parts=["E-301", "E-302", "/tube plug E-30[12]/", "/stage B (bottom|top)/", "E-306"],
             do=["Build it the same way as the first: bottom tube, two uprights, bearing blocks, cap plates and pulley blocks."],
             hw=["#10-32 × 3/8 in screws for the cap plates and pulley blocks"]),
        dict(t="Build the carriage", parts=["E-401", "E-402", "E-403", "/tube plug E-401/", "/carriage (upper|lower)/"],
             do=["Join the bottom tube and the two short uprights.",
                 "Bolt on the upper and lower bearing blocks.",
                 "Bolt a pivot plate to each upright. The wrist will hang from these."],
             hw=["8 bolts for each pivot plate"]),
        dict(t="Slide the stages in", parts=[], pose=dict(c=18),
             do=["Lower the first stage into the mast from the top.", "Lower the second stage into the first, then the carriage into the second."],
             check="Each one slides its full 22 in by hand without binding."),
        dict(t="Fit the lift chain", parts=["E-203", "E-205"],
             do=["Rivet a chain bracket to the outside of each first-stage upright.",
                 "Run a chain on each side round the drive sprocket and the idler.",
                 "Clamp both ends of each chain to its bracket.",
                 "Take up the slack with the turnbuckles."],
             hw=["6 × rivets for each bracket", "About 11 ft of #25H chain in all", "#10-32 × 7/8 in socket head screws for the chain clamps", "WCP-0247 turnbuckles"]),
        dict(t="Run the two ropes", parts=["/Eye bolt 1\\/4-20/", "E-307", "E-404"],
             do=["First rope: from an eye bolt in the mast base tube, up over the pulley on the first stage, down to the rope angle on the second stage.",
                 "Second rope: from an eye bolt in the first stage's bottom tube, up over the pulley on the second stage, down to the rope angle on the carriage.",
                 "Knot each rope under its angle with a washer.",
                 "Tighten each rope with the two nuts on its eye bolt."],
             hw=["1/8 in UHMWPE rope", "4 × 1/4-20 × 4 in eye bolts, two nuts each", "#10 washers under the knots"],
             check="Lift the first stage 1 in by hand. The second stage rises 2 in and the carriage rises 3 in."),
        dict(t="Stops, pads and the home switch", parts=["E-108", "E-110", "E-210", "E-310", "E-109", "/magnetic limit switch/", "/^Magnet/"],
             do=["Bolt the two up-stop blocks through the mast uprights.",
                 "Press a rubber rest pad into the tube under each stage, where it lands.",
                 "Bolt the home switch post through the mast base tube from the front, into the inserts in its foot. There is no room for a nut.",
                 "Fit the switch on the post and the magnet on the back of the carriage."],
             check="With everything down, the magnet sits 0.15 in from the switch."),
        dict(t="Cable chain", parts=["E-111", "E-406"],
             do=["Join two 3 ft pieces of cable chain and use about 43 in.",
                 "Rivet its lower bracket to the right mast upright.",
                 "Bolt its arm to the inside of the right carriage upright."],
             warn="Check the printed bracket against the real chain before printing it."),
        dict(t="Check it by hand", parts=[], pose=dict(c=60),
             do=["Before the motors drive it, lift the carriage by hand through its full 66 in and let it down."],
             check="Nothing binds. All three stages land on their rest pads at the same moment."),
    ])

X44 = lambda n: {"re": "Kraken X44", "nth": n}
SETS["wrist-and-claw"] = dict(
    title="Wrist and claw", sheets="Wrist and claw drawings, Rev E", base=FRAME + [{"from": ["elevator", 0, 99]}],
    intro="The wrist is a box open at both ends, so a coral passes straight through it. The claw's two plates bolt to the outside and carry the algae rollers underneath.",
    steps=[
        dict(t="Test the claw's grip first", parts=[],
             do=["Before building anything, put two shafts of the claw's flex wheels on a board, 13.00 in apart.", "Push a real algae into them."],
             warn="If the ball slips, change to softer or stickier wheels, or squeeze more. Finding that out now costs a board. Finding out later costs the claw."),
        dict(t="Build the box", parts=["W-201", "W-203", "W-202", "W-204", "W-205"],
             do=["Rivet a floor angle along the bottom of each side plate.",
                 "Screw the four tie rods between the side plates. They set the width.",
                 "Lay the clear floor on the floor angles, and fix the two coral guides on top of it."],
             hw=["8 × #10-32 × 3/8 in screws, one in each end of each tie rod"],
             check="The inside faces of the side plates are 9.21 in apart."),
        dict(t="Coral rollers", parts=["W-206", "/WCP-1297/", "W-207", "W-208", "W-211", "/bearing coral wheel shaft/", "/pulley (36T|24T).*wheel shaft/", "/belt 110T/", "/belt 70T x 15 mm motor/", X44(0), "/SplineXS bore motor$/", "/Kraken spacers.*the motor pulley/", "/bearing to pulley stack/", "/washer coral wheel shaft/"],
             do=["Slide two wheel shafts through the side plates, each with two green flex wheels, 1.25 in either side of centre.",
                 "Bolt the small motor inside the right plate with its shaft sticking out through it.",
                 "Outside the right plate: a belt from the motor's 12-tooth pulley to the 36-tooth pulley on the front shaft.",
                 "A second belt joins the two shafts so both turn together."],
             hw=["#10-32 × 3/8 in screws for the motor face. The holes are only 0.25 in deep", "70-tooth and 110-tooth belts, 5 mm pitch, 15 mm wide"],
             warn="Use button head screws on the motor face. The pulleys sit only 0.19 in off the plate."),
        dict(t="Claw plates and rods", parts=["C-101", "C-103"],
             do=["Bolt a claw plate to the outside of each side plate with seven screws and lock nuts. The lower three also clamp the floor angle.",
                 "Fit both rods between the claw plates now. They cannot go in once the rollers are on."],
             hw=["14 × #10-32 × 5/8 in button head screws and lock nuts"]),
        dict(t="Claw rollers and their motors", parts=["C-102", "/^Claw roller/", "C-104", "/bearing claw roller/", "/pulley 24T.*claw/", "/belt 90T/", "/belt 70T x 15 mm claw/", X44(1), X44(2), "/SplineXS bore claw/", "/Kraken spacers.*claw/", "/claw bearing to pulley/", "/washer claw roller/"],
             do=["Slide each roller shaft through the claw plates with its eight flex wheels.",
                 "Bolt two small motors inside the right claw plate, shafts out.",
                 "Belt each motor to its own roller."],
             hw=["90-tooth belt for the front roller, 70-tooth for the rear"],
             check="The rollers are 13.00 in apart. With both motors pulling in, the two rollers turn opposite ways."),
        dict(t="Big sprocket", parts=["W-104", "W-209"],
             do=["Screw six standoffs to the left side plate.", "Screw the 60-tooth sprocket to the standoffs."]),
        dict(t="Hang the wrist on the carriage", parts=["W-101", "W-102", "W-103", "/bearing wrist pivot/", "/collar right stub/", "/washer wrist stub/"],
             do=["Lift the carriage 1.25 in and prop it there.",
                 "Fit a pivot hub in each carriage pivot plate.",
                 "Hold the wrist between the hubs and slide a stub axle in from each side.",
                 "Left side, from the outside in: washer, hub bearings, spacer, side plate, washer.",
                 "Right side: two clamp collars hold the axle and the plate in place."],
             warn="Do not turn the wrist with the carriage right down. It hits the camera, its tower and the lift gearbox.",
             check="The wrist swings freely and has no side play."),
        dict(t="Wrist drive", parts=["/Kraken X60 wrist/", "/MAXPlanetary 2-stage/", "/^16T #25/", "W-105", "W-106"],
             do=["Bolt the motor and its 16:1 gearbox to the drive plate on the carriage.",
                 "Fit the 16-tooth sprocket on the gearbox.",
                 "Run chain from it to the 60-tooth sprocket. Tighten with the turnbuckle in the rear run."],
             hw=["#25 chain, 18.16 in between sprocket centres", "WCP-0247 turnbuckle"],
             check="16:1 in the gearbox and 60 to 16 in the chain make 60:1 overall."),
        dict(t="Encoder and end stops", parts=["W-302", "/through bore encoder/", "/Spacer 1\\/2 OD x 0.50/", "W-301", "W-210"],
             do=["Mount the encoder plate on its two spacers, on the right hub's screws, with the encoder on the right stub axle.",
                 "Screw the stop post into the right pivot plate, 2.15 in below the pivot.",
                 "Screw the two stop lugs to the right side plate."],
             check="Swing the wrist by hand to each end. A lug meets the post at both ends, before anything else touches."),
        dict(t="Sensors and cable posts", parts=["/CANrange/", "C-105", "W-213", "W-212", "W-304"],
             do=["Clamp the coral sensor's bracket on the tie rod, looking down into the wrist.",
                 "Clip the algae sensor's bracket on the backstop rod, looking along the claw's mouth.",
                 "Fit the cable anchor on top of the left carriage upright and the cable post on the left side plate."],
             warn="The sensor's screw size is not published. The brackets have small pilot holes: drill them to suit."),
    ])

SETS["funnel"] = dict(
    title="Funnel", sheets="Funnel drawings, Rev F", base=FRAME,
    intro="Four posts carry one hinged piece: the tray, its walls and two cross tubes. It hinges on the right-hand posts. A hook on the left holds it shut.",
    steps=[
        dict(t="Mock it up first", parts=[],
             do=["Build the tray and walls in cardboard or scrap plastic, at the right slope.", "Drop real coral into it, straight and crooked."],
             warn="How well a crooked coral straightens, and whether it crosses the gap over the bumper, are the open questions. Answer them before cutting polycarbonate."),
        dict(t="Stand the four posts", parts=["F-101", "F-103-L", "F-103-R", "F-105"],
             do=["Two rear posts on the back rail, 5.70 in either side of centre.",
                 "Two middle posts on the cross member, 7.10 in either side of centre.",
                 "Rivet a foot gusset to each post and to the tube it stands on. The middle posts get one on each face."],
             hw=["6 × foot gussets", "48 × 5/32 in rivets"]),
        dict(t="Hinge plates on the right posts", parts=["F-110", "F-111", "F-114"],
             do=["Rivet a pivot plate to each face of the right middle post.",
                 "Rivet the rear pivot plate, with its shim behind it, to the front of the right rear post.",
                 "Fit the open-stop screw and nut in the rear pivot plate."],
             hw=["8 × rivets for the two middle plates", "8 × rivets for the rear plate and shim", "1 × #10-32 × 3/4 in socket head screw and nut"]),
        dict(t="Tray and walls", parts=["F-201", "F-202", "F-203"],
             do=["Cut the tray and two walls from 1/8 in polycarbonate. Cut one wall as drawn and one flipped over.",
                 "Smooth side of the tray up. Break its front and rear edges.",
                 "Rivet an angle along each side: its flat leg under the tray, its upright leg outside the wall."],
             hw=["42 × 5/32 in rivets"]),
        dict(t="Cross tubes and saddles", parts=["F-102", "F-104", "F-107", "F-108"],
             do=["Press two threaded inserts into each printed saddle.",
                 "Screw the saddles down onto the two cross tubes from underneath.",
                 "Bolt the tray to the saddles, square to the tray."],
             hw=["8 × #10-32 heat-set inserts (93365A154)", "4 × #10-32 × 1.25 in button head screws, up through the tubes", "4 × #10-32 × 3/8 in button head screws, tray to saddles"]),
        dict(t="Hang it on the hinge", parts=["F-112"],
             do=["Rivet the drop link to the front of the rear cross tube.",
                 "Put one bolt through the two middle pivot plates and the middle cross tube.",
                 "Put the other through the drop link and the rear pivot plate, with a washer between them."],
             hw=["3 × rivets", "1 × #10-32 × 2.00 in socket head screw, lock nut, 2 washers", "1 × #10-32 × 1.00 in socket head screw, lock nut, 3 washers"],
             warn="Leave both bolts free to turn. They are the hinge.",
             check="The tray swings up and over to the right, and stops on the stop screw at 90°."),
        dict(t="Latch", parts=["F-113", {"re": "Smart Robot Servo \\(funnel", "sub": 3}, {"re": "Servo horn", "sub": 3}, "F-115", "F-116", "/latch link/", "/holds the latch hook/"],
             do=["Bolt the hook to the left middle post so it turns. Its finger sits over the end of the middle cross tube.",
                 "Hook a spring from the hook to a post screw 1.35 in below.",
                 "Bolt the servo to the post on its two printed blocks, shaft toward the post.",
                 "Join the servo's horn to the hook with the link. Tap the horn's hole and use thread locker."],
             hw=["1 × #10-32 × 1.50 in socket head screw, lock nut, 2 washers (hook pivot)", "3 × #8-32 × 2.25 in socket head screws and lock nuts (servo)", "#4-40 screws at each end of the link"],
             check="The finger covers the tube. It may need filing to fit."),
        dict(t="Tubing", parts=["/Eye bolt #10-32/"],
             do=["Put the eye bolt through both walls of the right rear post, 14.0 in up, nut on the inside.",
                 "Then cut its thread to 1.25 in.",
                 "Stretch two strands of latex tubing from the eye bolt to the right end of the rear cross tube."],
             hw=["Eye bolt 2434K598", "About 2 ft of 3/8 in latex tubing"],
             warn="Uncut, the eye bolt touches a climber plate. Cut, it clears by 0.19 in. Check that gap on the robot.",
             check="With the robot tilted 10°, the tubing still throws the tray fully open."),
        dict(t="Close it and test the latch", parts=[], pose=dict(tray=90),
             do=["To close: hold the hook forward, push the tray down onto the posts, and let the hook spring back.",
                 "Fire the servo. The tray should swing fully open and stay there."],
             check="Drive it over a bump with the tray shut. It must not pop open. A tray that opens in a match is a broken intake."),
    ])

SETS["climber"] = dict(
    title="Climber", sheets="Climber drawings, Rev D", base=FRAME,
    intro="A tower plate stands each side of the battery. The fork turns on an axle between them. Each side has its own winch: a motor, a gearbox, a ratchet and a spool.",
    steps=[
        dict(t="Tower plates", parts=["CL-101", "CL-103"],
             do=["The two base tubes are already in. They went on with the frame.",
                 "Rivet a tower plate to the outside of each base tube.",
                 "Rivet a small clip between each tower plate and the top of the back rail."],
             hw=["5 × rivets into each base tube", "2 × rivets into each rail clip"]),
        dict(t="Build the fork's arms", parts=["CL-201", "/Bronze flanged/", "CL-204"],
             do=["Press a bronze bearing into the big hole in each arm plate, flange facing outward.",
                 "Rivet a printed rope track to the outside of each arm plate.",
                 "Smooth the small rope hole, and round the top end of the track where the rope turns in."],
             hw=["2 × bronze flanged bearings (6338K417)", "4 × rivets for each track"]),
        dict(t="Join the arms", parts=["CL-202", "CL-207", "CL-206", "/^Stop pin/"],
             do=["Screw the three tie rods between the arm plates.",
                 "Two of the rods carry rubber sleeves. The cage rests on those.",
                 "Fit the two clear entry guides. Drill their holes with the guides held in place.",
                 "Put a stop pin on each front tie rod screw."]),
        dict(t="Gates", parts=["CL-203", "CL-205", "/Torsion spring, light/"],
             do=["Make one gate first and try it. Then make the second.",
                 "Screw each printed gate block to the inside of its arm plate, into four threaded inserts.",
                 "Hang the gate finger on its upright screw in the block, with the light spring under it."],
             hw=["4 × heat-set inserts in each block", "1 × #10-32 × 1.50 in socket head screw and lock nut for each finger"],
             check="A 1.315 in pipe pushed in folds the finger back. The finger springs shut behind it and will not open outward."),
        dict(t="Slide the axle through", parts=["CL-104", "CL-208", "CL-209", "CL-210", "/Dowel pin 3\\/16/", "/Deploy torsion spring/", "/\\(pivot axle\\)/"],
             do=["Hold the fork between the towers.",
                 "Slide the hex axle in from one side. As it goes, thread on each part in order: a spacer, an arm plate, a spring, a spring hub, the long spacer tube, then the same in reverse.",
                 "The right-hand-wound spring goes on the left and the left-hand-wound one on the right.",
                 "Screw a washer and screw into each end of the axle."],
             hw=["Springs 9271K689 (left side) and 9271K624 (right side)", "2 × 1/4-20 × 1/2 in button head screws and washers"],
             warn="The axle's hole in each tower has a flat, so the axle cannot turn. The fork turns on the axle."),
        dict(t="Hook up the springs", parts=["/Deploy spring pin/"],
             do=["Cut each spring's legs: 2.0 in for the moving leg, 1.5 in for the fixed leg.",
                 "The fixed leg rests on the pin in its printed hub.",
                 "The moving leg rests on a pin screwed into the arm plate."],
             hw=["2 × #10-32 × 3/4 in button head screws, spacers (92415A662) and lock nuts"],
             warn="Never wind a spring past 180°.",
             check="Let go of the stowed fork with no rope on it. It swings out by itself."),
        dict(t="End stops", parts=["/^Fork stop/", "CL-308"],
             do=["Fit two bolts in each tower plate, heads inward, each with a small turned spacer.", "One stops the fork at 97°. The other catches it just past level."],
             hw=["4 × 1/4-20 × 1.00 in socket head screws and lock nuts"],
             check="Swing the fork by hand. A stop pin meets a bolt at each end."),
        dict(t="Winches", parts=["CL-302", "/spool shaft, in the tower/", "CL-301", "CL-310", "/^WCP-0405 ratchet wheel/", "CL-306", "CL-309", "/^WCP-0405 pawl/", "/MAXPlanetary 25:1/", "/Kraken X60 \\(climber\\)/"],
             do=["The ratchet is bought: one WCP-0405 ratchet and pawl kit for each side. There is nothing to machine.",
                 "Each side: a short hex shaft runs from the gearbox, through the ratchet wheel and the spool, into a bearing in the tower plate. A thin printed spacer goes between the bearing and the wheel.",
                 "The pawl goes on now. Slip a printed thrust washer, then the pawl, onto the rear gearbox spacer. The pawl turns on that spacer.",
                 "Bolt the motor to its 25:1 gearbox. Bolt the gearbox to the tower through the two spacers. The face of the gearbox keeps the pawl on."],
             hw=["2 × WCP-0405 ratchet and pawl kits", "4 × #10-32 × 1.00 in socket head screws (91251A347), heads inboard"],
             warn="The spool must be metal. It carries the whole climb.",
             check="Each pawl swings freely on its spacer."),
        dict(t="Pawl springs, links and servos", parts=["/^Shoulder screw 1\\/4/", "CL-311", "/^Extension spring 9654K972/", "/climber pawl release/", {"re": "Servo horn", "sub": 4}, "CL-305"],
             do=["Put a printed link on a shoulder screw. Screw it into the tapped hole in the pawl's tail, with thread locker.",
                 "Fit a spring post below each pawl: a long screw through the tower plate, head inboard, with a nut against the plate.",
                 "Hook the spring from the post up to the shoulder screw, outside the link. It pulls the pawl onto the wheel.",
                 "Tap the hole in the servo horn nearest 0.50 in from its centre, #4-40.",
                 "Bolt each servo to the tower on two printed blocks. Screw the top of the link to the horn from the tower side, with thread locker."],
             hw=["2 × shoulder screws, 1/4 in shoulder × 5/16, #10-32 thread (94035A532)", "2 × #10-32 × 1.25 in socket head screws, each with a hex nut and a lock nut, for the spring posts",
                 "2 × extension springs (9654K972)", "8 × #8-32 × 1.75 in screws and lock nuts for the servos", "2 × #4-40 × 3/8 in screws and washers for the links"],
             warn="Check both sides before fitting the rope. Each wheel must lock against paying out. The right wheel is the left one flipped over.",
             check="Each pawl clicks over the teeth when the spool is wound in. With the servo horn at 141° the pawl is clear of the teeth, and at 165° it is down."),
        dict(t="Ropes", parts=["/WCP-0166 rope/"], pose=dict(psi=0, tray=90, c=1.25, th=0),
             do=["Thread each rope through the small hole just past the top of its track. Tie a stopper knot with a washer on the inside.",
                 "Lead it over the track and down to the spool."],
             hw=["1/8 in rope"],
             check="With the fork level, two turns of rope are still on each spool."),
        dict(t="Stow it", parts=[],
             do=["Wind the fork straight up, under the funnel."],
             check="The closest thing to it is a claw roller, 0.60 in away."),
    ])

SETS["bumpers"] = dict(
    title="Bumpers", sheets="Bumper drawings, Rev C", base=FRAME,
    intro="Two U-shaped halves, front and rear, meet at the middle of each side. Eight bolts hold them on.",
    steps=[
        dict(t="Cut the boards", parts=["BU-101", "BU-102"],
             do=["Cut two end boards and four side boards from 3/4 in plywood, all 5.00 in tall.",
                 "Each end board runs the full width. The side boards butt into it.",
                 "Drill shallow pockets in the inside faces, over the heads of the frame's bolts."],
             check="Hold each board against the frame. It sits flat, with every bolt head inside a pocket."),
        dict(t="Corner braces", parts=["BU-104"],
             do=["Screw an aluminium angle inside each corner, above the frame."],
             hw=["4 × #10 × 3/4 in wood screws in each leg"]),
        dict(t="Mounting brackets", parts=["BU-103"],
             do=["Screw eight small angle brackets to the inside of the boards, at the positions on the drawing.",
                 "The upright leg goes against the board. The flat leg sits on the rail top, over a rivnut."],
             hw=["2 × #10 × 3/4 in wood screws in each bracket"]),
        dict(t="Padding and cover", parts=["BU-201", "BU-202"],
             do=["Stack two pool noodles along every board. Fill the corners with cut pieces.",
                 "Wrap the fabric cover over them and staple it to the back of the plywood, every inch."]),
        dict(t="Bolt them on", parts=[],
             do=["Drop each half on from above.", "Bolt down through each bracket into its rivnut. No washer."],
             hw=["8 × 1/4-20 × 1/2 in button head screws (91255A537)"],
             warn="A washer leaves too little thread in the rivnut.",
             check="The robot is 34.5 in across the bumpers. Hard parts are 0.75 in from the frame."),
    ])

ALL = lambda name: {"from": [name, 0, 99]}
SETS["robot"] = dict(
    title="The whole robot", sheets="", base=[],
    intro="The order matters. Some parts are riveted to parts of another mechanism, and some get covered by what comes next.",
    steps=[
        dict(t="Frame and swerve modules", link="drivebase", parts=["D-101", "D-102", "/^MK4i/", "D-103", "D-105", "/WCP-0374/"],
             do=["Everything else bolts to this, so it comes first."]),
        dict(t="Climber base tubes", link="drivebase", parts=["CL-102", "/tube plug \\(CL-102\\)/"],
             do=["They are climber parts, but the belly pan rivets up into them. They must be in before the pan."]),
        dict(t="Belly pan, rivnuts and camera", link="drivebase", parts=["D-201", "CAM-101", "/^CAM Limelight/"],
             do=["Set every rivnut now, while the frame is open and easy to reach."]),
        dict(t="Electronics boards and the battery stop", link="electronics", parts=[{"from": ["electronics", 0, 5]}],
             do=["Mount them before the elevator goes in, because the mast and gearbox sit over them.", "Mount only. Wiring comes last."]),
        dict(t="Mast, gearbox and cross shaft", link="elevator", parts=[{"from": ["elevator", 0, 5]}],
             do=["The mast braces rivet to the frame, and the gearbox bolts through the spine."]),
        dict(t="Stages, carriage, chain and ropes", link="elevator", parts=[{"from": ["elevator", 6, 99]}],
             do=["The stages slide in from the top, so nothing may sit above the mast yet.", "Check the whole elevator by hand before going on."]),
        dict(t="Wrist and claw", link="wrist-and-claw", parts=[ALL("wrist-and-claw")], pose=dict(c=1.25),
             do=["Build it on the bench, then hang it on the carriage with the carriage propped 1.25 in up."]),
        dict(t="Funnel", link="funnel", parts=[ALL("funnel"), {"from": ["electronics", 6, 6]}],
             do=["The posts stand on the back rail and the cross member.", "The radio goes on a funnel post, so it is fitted now."]),
        dict(t="Climber", link="climber", parts=[ALL("climber")],
             do=["It goes in after the funnel because the stowed fork sits under the tray, and the funnel's eye bolt has to be checked against a tower plate."]),
        dict(t="Bumpers", link="bumpers", parts=[ALL("bumpers")],
             do=["They can be built at any time. They go on last so the frame stays easy to reach."]),
        dict(t="Wiring", link="/wire-it/", linkText="The wiring chapter", parts=[],
             do=["Now run every wire. The boxes were mounted back in step 4."]),
        dict(t="First power and checks", link="/wire-it/#before-the-first-power-up", linkText="The checks, in order", parts=[],
             do=["Power up with the robot on blocks. Check each mechanism by itself, slowly, before running anything together."]),
    ])

def resolve():
    """Turn every selector into model part numbers, and give each fastener to the step that places the last part it joins."""
    import re, collections
    here = os.path.dirname(os.path.abspath(__file__)); data = os.path.join(here, '..', '..', 'public', 'robot-viewer')
    J = json.load(open(os.path.join(data, 'robot.json'))); F = json.load(open(os.path.join(data, 'fasteners.json')))
    P = J['parts']; made = J['made']
    subs = [J['meshes'][p['m']]['sub'] for p in P]

    def pick(sel, done):
        if isinstance(sel, dict) and 'from' in sel:
            name, a, b = sel['from']; out = []
            for st in SETS[name]['steps'][a:b + 1]:
                for x in st['parts']: out += pick(x, done)
            return out
        if isinstance(sel, dict):
            hit = [i for i, p in enumerate(P) if re.search(sel['re'], p['l']) and ('sub' not in sel or subs[i] == sel['sub'])]
            return [hit[sel['nth']]] if 'nth' in sel else hit
        if sel.startswith('/'):
            rx = re.compile(sel[1:-1]); return [i for i, p in enumerate(P) if rx.search(p['l'])]
        hit = [i for i, p in enumerate(P) if p['k'] == sel]
        assert hit, 'no part with mark ' + sel
        return hit

    def family(kind):
        return 'rivet' if 'rivet' in kind else 'rivnut' if 'rivnut' in kind else 'lock nut' if 'lock nut' in kind else 'screw'

    out = {}
    for name, S in SETS.items():
        step_of = {}
        for i in sum((pick(x, None) for x in S['base']), []): step_of.setdefault(i, -1)
        for a, x in enumerate(S['base']):
            assert pick(x, None), (name, 'base', x)
        steps = []
        for n, st in enumerate(S['steps']):
            new = []
            for x in st['parts']:
                got = pick(x, None); assert got, (name, st['t'], x)
                for i in got:
                    if i not in step_of: step_of[i] = n; new.append(i)
            for i in sum((pick(x, None) for x in st.get('show', [])), []): step_of.setdefault(i, -1)
            steps.append(new)
        fast = [[] for _ in S['steps']]; base_f = []
        for fi, it in enumerate(F['items']):
            joined = it[9]
            if not all(j in step_of for j in joined): continue
            n = max(step_of[j] for j in joined)
            (fast[n] if n >= 0 else base_f).append(fi)
        rs = []
        for n, st in enumerate(S['steps']):
            listed = collections.OrderedDict()
            groups_seen = set()
            for i in steps[n]:
                p = P[i]
                if 'g' in p:                       # a vendor model in several colours counts once
                    if p['g'] in groups_seen: continue
                    groups_seen.add(p['g'])
                if p['k'] and p['k'] in made: key = ('made', p['k'])
                else: key = ('bought', re.sub(r'\s*\[vendor model\]|\s*\(vendor model\)', '', re.split(r'[,:(]| x \d', p['l'])[0]).strip()[:48])
                listed[key] = listed.get(key, 0) + 1
            pl = [dict(k=k[1], n=c, name=made[k[1]]['name'], slug=made[k[1]]['slug']) if k[0] == 'made' else dict(name=k[1], n=c) for k, c in listed.items()]
            kinds = collections.Counter(F['kinds'][F['items'][fi][0]] for fi in fast[n])
            fam = collections.Counter(); [fam.update({family(k): c}) for k, c in kinds.items()]
            r = {k: v for k, v in st.items() if k not in ('parts', 'show')}
            r.update(p=steps[n], f=fast[n], pl=pl, fk=sorted(([k, c] for k, c in kinds.items()), key=lambda x: x[0]), fam=dict(fam))
            rs.append(r)
        out[name] = dict(title=S['title'], sheets=S['sheets'], intro=S['intro'], base=sorted(i for i, v in step_of.items() if v == -1), basef=base_f, steps=rs)
    return out, P, subs, J


if __name__ == '__main__':
    out, P, subs, J = resolve()
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'public', 'robot-viewer', 'assembly.json')
    json.dump(out, open(dest, 'w'), separators=(',', ':'), ensure_ascii=False)
    print('wrote', len(out), 'sets,', sum(len(s['steps']) for s in out.values()), 'steps')
    # coverage: which modelled parts of a mechanism does its own set never place?
    scope = {'drivebase': [0], 'electronics': [5], 'elevator': [1], 'wrist-and-claw': [2], 'funnel': [3], 'climber': [4], 'bumpers': [6]}
    for name, ss in scope.items():
        placed = set(out[name]['base']) | set(i for st in out[name]['steps'] for i in st['p'])
        miss = sorted(set(P[i]['l'][:58] for i in range(len(P)) if subs[i] in ss and i not in placed))
        nf = sum(len(st['f']) for st in out[name]['steps'])
        print(f"{name}: {sum(len(st['p']) for st in out[name]['steps'])} parts and {nf} fasteners in steps; not placed: {miss}")
    used = set(fi for st in out['robot']['steps'] for fi in st['f']) | set(out['robot']['basef'])
    print('whole robot:', len(set(i for st in out['robot']['steps'] for i in st['p'])), 'of', len(P), 'parts;', len(used), 'of', sum(1 for _ in json.load(open(os.path.join(os.path.dirname(dest), 'fasteners.json')))['items']), 'fastener solids')
    if '--steps' in __import__('sys').argv:
        for name, S in out.items():
            for n, st in enumerate(S['steps']): print(name, n + 1, st['t'], '|', len(st['p']), 'parts |', st['fk'])
