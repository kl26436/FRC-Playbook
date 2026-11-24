# Replay recorder

`PlaybookReplayTest.java` records the runs the playbook plays back on its code pages:

| File | Shown on | What it is |
| --- | --- | --- |
| `teleop_cycle.json` | One button to score | Station pickup, then branch D at L4, one command each |
| `vision_fix.json` | How the camera finds the robot | Position wrong by 0.43 m; the camera's reading is used |
| `vision_rejected.json` | How the camera finds the robot | Position wrong by 1.26 m; every reading is refused |
| `elevator_move.json` | Not shown yet | Stow to L4 and back, every 20 ms, with volts and amps |

It is a test for the robot code repo (ClaudeBot). It changes no robot code. It reads a few private values
(the mechanism goals, the drive target, what the camera reported) by reflection.

## To record

1. Copy `PlaybookReplayTest.java` into the robot code at `src/test/java/frc/robot/subsystems/vision/`.
2. In the robot code folder run:

   ```
   ./gradlew simTest --tests "*PlaybookReplayTest*" -PreplayDir=docs/playbook/replays
   ```

3. Commit the four JSON files in the robot code repo. The playbook's build fetches the first three from there
   (`scripts/fetch-replays.mjs`) and they replace the copies in `public/replays/`.

## The copies in this repo were made in a cloud sandbox

In that sandbox the Phoenix simulator does not ramp the elevator down at the end of a Motion Magic move: the
controller's own reference stays at cruise speed until the target and then drops to zero. The carriage runs into
the end of its travel at about 110 in/s. The robot code's own tests `ElevatorSimTest.neverPassesTheSoftLimit` and
two in `SuperstructureSimTest` fail there for the same reason. It is the symptom the robot code's design log
records on Nov 23 ("the simulated profile stopped slowing down and the carriage hit the top"). The fix made then
holds on the team PC: the autos recorded there follow the profile to within 0.15 in. It does not hold in the
sandbox, and the cause was not found.

So the three files carry a `caveat` line, which the player shows under the replay, and `elevator_move.json` is
not published. Recordings made on the team PC have no `caveat` and need none.
