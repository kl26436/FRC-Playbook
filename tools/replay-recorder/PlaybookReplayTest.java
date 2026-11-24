package frc.robot.subsystems.vision;

import static org.junit.jupiter.api.Assertions.assertTrue;

import edu.wpi.first.math.geometry.Pose2d;
import edu.wpi.first.math.geometry.Rotation2d;
import edu.wpi.first.math.geometry.Transform2d;
import edu.wpi.first.math.geometry.Translation2d;
import edu.wpi.first.wpilibj.DriverStation.Alliance;
import edu.wpi.first.wpilibj2.command.Command;
import edu.wpi.first.wpilibj2.command.CommandScheduler;
import frc.robot.RobotContainer;
import frc.robot.commands.ScoreCommands;
import frc.robot.field.Reef;
import frc.robot.field.Station;
import frc.robot.sim.ScoreJudge.CoralScore;
import frc.robot.subsystems.Superstructure.Wanted;
import frc.robot.testutil.AutoReplay;
import frc.robot.testutil.RobotFixture;
import frc.robot.testutil.SimHarness;
import java.io.IOException;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * Recordings for the playbook site that the auto recorder does not make: a driver's one-button
 * cycle, the camera correcting a wrong position, the camera's fix being refused, and one elevator
 * move at every loop.
 *
 * <p>This file lives in the playbook repo (tools/replay-recorder). Copy it to
 * src/test/java/frc/robot/subsystems/vision/ in the robot code and run
 * {@code ./gradlew simTest --tests "*PlaybookReplayTest*" -PreplayDir=<folder>}.
 *
 * <p>It changes no robot code. It reads a few private values the robot already logs (goals, the
 * camera's inputs, the target face) by reflection, because a test cannot read the log.
 */
@Tag("sim")
class PlaybookReplayTest {
    private static final double STEP_S = 0.05;
    private static final Pose2d OPEN_FIELD = new Pose2d(2.5, 6.5, Rotation2d.kZero);

    @AfterEach
    void tearDown() {
        CommandScheduler.getInstance().cancelAll();
    }

    private static Object peek(Object owner, String field) {
        try {
            Field f = owner.getClass().getDeclaredField(field);
            f.setAccessible(true);
            return f.get(owner);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(owner.getClass().getSimpleName() + "." + field, e);
        }
    }

    private static double num(Object owner, String field) {
        try {
            Field f = owner.getClass().getField(field);
            return f.getDouble(owner);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(owner.getClass().getSimpleName() + "." + field, e);
        }
    }

    /** What the vision code did with this loop's sighting: the same checks, in the same order, as Vision.evaluate. */
    private record Sight(int tag, double txDeg, double heightPx, int status, double fixX, double fixY) {}

    private static final String[] STATUS = {
        "no target face", "no tag in view", "tag is not the target face", "fix applied", "fix too far from the estimate", "degenerate sighting"
    };

    @SuppressWarnings("unchecked")
    private static Sight sight(RobotContainer r) {
        Vision v = r.vision();
        Object in = peek(v, "inputs");
        Optional<Integer> face = (Optional<Integer>) peek(v, "targetFace");
        boolean has;
        int tag;
        try {
            has = in.getClass().getField("hasTarget").getBoolean(in);
            tag = in.getClass().getField("tagId").getInt(in);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(e);
        }
        double tx = num(in, "txDeg");
        double h = num(in, "heightPx");
        if (!has) {
            return new Sight(-1, 0, 0, face.isEmpty() ? 0 : 1, Double.NaN, Double.NaN);
        }
        if (face.isEmpty()) {
            return new Sight(tag, tx, h, 0, Double.NaN, Double.NaN);
        }
        if (tag != Reef.tagId(Alliance.Blue, face.get())) {
            return new Sight(tag, tx, h, 2, Double.NaN, Double.NaN);
        }
        if (h < Vision.MIN_HEIGHT_PX) {
            return new Sight(tag, tx, h, 5, Double.NaN, Double.NaN);
        }
        Pose2d est = r.drive().pose();
        Translation2d fix = SingleTagFix.robotPosition(
                new TagObservation(tag, tx, h), CameraModel.limelight4(), est.getRotation(), Reef.tagPose3d(Alliance.Blue, face.get()));
        // After an applied fix the estimate already equals the fix, so "too far" can only be a refused one.
        boolean far = fix.getDistance(est.getTranslation()) > Vision.MAX_JUMP_M;
        return new Sight(tag, tx, h, far ? 4 : 3, fix.getX(), fix.getY());
    }

    private static final String COLUMNS =
            "\"t_s\",\"x_m\",\"y_m\",\"heading_deg\",\"carriage_in\",\"wrist_deg\",\"coral\",\"algae\",\"phase\","
                    + "\"goal_carriage_in\",\"goal_wrist_deg\",\"target_x_m\",\"target_y_m\",\"est_x_m\",\"est_y_m\","
                    + "\"tag\",\"tx_deg\",\"tag_height_px\",\"vision\",\"fix_x_m\",\"fix_y_m\"";

    private static String n(double v, String fmt) {
        return Double.isFinite(v) ? String.format(Locale.ROOT, fmt, v) : "null";
    }

    private static String row(RobotContainer r, double tS, int phase) {
        Pose2d p = r.sim().truePose();
        Pose2d est = r.drive().pose();
        Pose2d target = (Pose2d) peek(r.drive(), "target");
        Sight s = sight(r);
        return String.format(
                Locale.ROOT,
                "[%.2f,%.3f,%.3f,%.1f,%.2f,%.1f,%d,%d,%d,%s,%s,%.3f,%.3f,%.3f,%.3f,%d,%.2f,%.1f,%d,%s,%s]",
                tS, p.getX(), p.getY(), p.getRotation().getDegrees(), r.sim().trueCarriageIn(), r.sim().trueWristDeg(),
                r.sim().coralAboard() ? 1 : 0, r.sim().algaeAboard() ? 1 : 0, phase,
                n((Double) peek(r.elevator(), "goalIn"), "%.2f"), n((Double) peek(r.wrist(), "goalDeg"), "%.1f"),
                target.getX(), target.getY(), est.getX(), est.getY(),
                s.tag(), s.txDeg(), s.heightPx(), s.status(), n(s.fixX(), "%.3f"), n(s.fixY(), "%.3f"));
    }

    /** 2 route, 3 raise, 4 release while the scoring command runs; 5 stow once it has ended. */
    private static int scorePhase(RobotContainer r, Command score) {
        if (!CommandScheduler.getInstance().isScheduled(score)) {
            return 5;
        }
        var s = r.superstructure();
        if (s.isReleasing()) {
            return 4;
        }
        return s.wanted() == Wanted.STOW ? 2 : 3;
    }

    private static void write(String file, String label, String note, List<String> rows, List<CoralScore> scored, double scoreT)
            throws IOException {
        Path folder = AutoReplay.folder();
        if (folder == null) {
            return;
        }
        List<String> events = new ArrayList<>();
        for (CoralScore c : scored) {
            events.add(String.format(Locale.ROOT, "{\"t\":%.2f,\"what\":\"coral\",\"branch\":\"%s\",\"level\":\"%s\"}", scoreT, c.branch(), c.level()));
        }
        List<String> tags = new ArrayList<>();
        for (int id : Reef.allTagIds()) {
            var p = Reef.anyTagPose3d(id);
            tags.add(String.format(Locale.ROOT, "\"%d\":[%.3f,%.3f]", id, p.getX(), p.getY()));
        }
        Files.createDirectories(folder);
        Files.writeString(
                folder.resolve(file),
                "{\n\"label\":\"" + label + "\",\n\"note\":\"" + note + "\",\n\"alliance\":\"blue\",\n" + AutoReplay.stamp()
                        + ",\n\"tags\":{" + String.join(",", tags) + "}"
                        + ",\n\"phases\":[\"idle\",\"pickup\",\"route\",\"raise\",\"release\",\"stow\"],\n\"vision_states\":[\""
                        + String.join("\",\"", STATUS) + "\"],\n\"columns\":[" + COLUMNS + "],\n\"events\":[" + String.join(",", events)
                        + "],\n\"samples\":[\n" + String.join(",\n", rows) + "\n]\n}\n");
    }

    /** Stand still for a moment before the button is held, so the starting state can be seen. */
    private static double wait(RobotContainer r, List<String> rows, double seconds) {
        double t = 0;
        rows.add(row(r, 0, 0));
        while (t < seconds - 1e-9) {
            SimHarness.run(STEP_S);
            t += STEP_S;
            rows.add(row(r, t, 0));
        }
        return t;
    }

    /** Run the scoring command to its end, sampling as it goes; returns when the first coral was judged scored. */
    private static double runScore(RobotContainer r, Command score, List<String> rows, double t0, double maxS) {
        double scoredAt = Double.NaN;
        CommandScheduler.getInstance().schedule(score);
        double t = t0;
        int after = 0;
        while (t - t0 < maxS && after < Math.round(1.6 / STEP_S)) {
            SimHarness.run(STEP_S);
            t += STEP_S;
            int phase = scorePhase(r, score);
            rows.add(row(r, t, phase));
            if (Double.isNaN(scoredAt) && !r.sim().coralScored().isEmpty()) {
                scoredAt = t;
            }
            if (phase == 5) {
                after++;
            }
        }
        return scoredAt;
    }

    @Test
    void driverCycle() throws IOException {
        SimHarness.takeStepStats();
        RobotContainer r = RobotFixture.reset(OPEN_FIELD, false);
        // As if it had just scored: half a metre back from branch C's spot, empty.
        RobotFixture.reset(Reef.scoringPose(Alliance.Blue, Reef.Branch.C).transformBy(new Transform2d(-0.5, 0, Rotation2d.kZero)), false);
        List<String> rows = new ArrayList<>();
        double t = wait(r, rows, 0.5);
        Command pickup = ScoreCommands.stationPickup(r, () -> Station.Side.RIGHT, 3.0, true);
        CommandScheduler.getInstance().schedule(pickup);
        while (t < 8 && CommandScheduler.getInstance().isScheduled(pickup)) {
            SimHarness.run(STEP_S);
            t += STEP_S;
            rows.add(row(r, t, 1));
        }
        assertTrue(r.superstructure().hasCoral(), "the pickup should end with a coral");
        Command score = ScoreCommands.alignAndScore(r, () -> Reef.Branch.D, () -> Wanted.L4, 3.0, true);
        double scoredAt = runScore(r, score, rows, t, 10);
        assertTrue(Double.isFinite(scoredAt), "the cycle should score");
        write("teleop_cycle.json", "Station to L4, one button each", "A driver cycle: one command picks up at the right station, one scores on branch D at L4.", rows, r.sim().coralScored(), scoredAt);
        System.out.println("REPLAY driverCycle: " + SimHarness.takeStepStats());
    }

    /** Start at the right station holding a coral, with the odometry told a wrong place. */
    private RobotContainer wrongStart(double dx, double dy) {
        RobotContainer r = RobotFixture.reset(OPEN_FIELD, false);
        Pose2d start = Station.pickupPose(Alliance.Blue, Station.Side.RIGHT);
        RobotFixture.reset(start, true);
        r.drive().resetPose(new Pose2d(start.getTranslation().plus(new Translation2d(dx, dy)), start.getRotation()));
        return r;
    }

    @Test
    void visionFix() throws IOException {
        SimHarness.takeStepStats();
        RobotContainer r = wrongStart(0.35, -0.25);
        List<String> rows = new ArrayList<>();
        double t0 = wait(r, rows, 1.0);
        Command score = ScoreCommands.alignAndScore(r, () -> Reef.Branch.C, () -> Wanted.L4, 3.0, true);
        double scoredAt = runScore(r, score, rows, t0, 12);
        write("vision_fix.json", "The camera corrects a wrong position", "The robot starts believing it is 0.43 m from where it really is, as after a hard bump.", rows, r.sim().coralScored(), scoredAt);
        System.out.println("REPLAY visionFix: " + SimHarness.takeStepStats());
    }

    @Test
    void visionRejected() throws IOException {
        SimHarness.takeStepStats();
        RobotContainer r = wrongStart(1.2, 0.4);
        List<String> rows = new ArrayList<>();
        double t0 = wait(r, rows, 1.0);
        Command score = ScoreCommands.alignAndScore(r, () -> Reef.Branch.C, () -> Wanted.L4, 3.0, true);
        double scoredAt = runScore(r, score, rows, t0, 8);
        write("vision_rejected.json", "A fix too far away is refused", "The robot starts believing it is 1.26 m from where it really is. A fix more than 1 m from the estimate is not trusted.", rows, r.sim().coralScored(), scoredAt);
        System.out.println("REPLAY visionRejected: " + SimHarness.takeStepStats());
    }

    @Test
    void elevatorMove() throws IOException {
        SimHarness.takeStepStats();
        Path folder = AutoReplay.folder();
        RobotContainer r = RobotFixture.reset(OPEN_FIELD, true);
        List<String> rows = new ArrayList<>();
        double t = 0;
        Wanted[] plan = {Wanted.STOW, Wanted.L4, Wanted.STOW};
        double[] holdS = {0.3, 2.6, 2.6};
        for (int k = 0; k < plan.length; k++) {
            r.superstructure().setWanted(plan[k]);
            for (int i = 0; i < Math.round(holdS[k] / SimHarness.DT); i++) {
                SimHarness.run(SimHarness.DT);
                t += SimHarness.DT;
                Object e = peek(r.elevator(), "inputs");
                Object w = peek(r.wrist(), "inputs");
                rows.add(String.format(
                        Locale.ROOT,
                        "[%.2f,%d,%s,%.2f,%.1f,%.2f,%.1f,%s,%.1f,%.2f,%.1f]",
                        t, k, n((Double) peek(r.elevator(), "goalIn"), "%.2f"), r.sim().trueCarriageIn(), num(e, "velocityInPerS"),
                        num(e, "appliedVolts"), num(e, "statorAmps"), n((Double) peek(r.wrist(), "goalDeg"), "%.1f"), r.sim().trueWristDeg(),
                        num(w, "appliedVolts"), num(w, "statorAmps")));
            }
        }
        if (folder == null) {
            return;
        }
        Files.createDirectories(folder);
        Files.writeString(
                folder.resolve("elevator_move.json"),
                "{\n\"label\":\"Stow to L4 and back\",\n\"note\":\"Every 20 ms loop, with a coral aboard. The goal is what the planner asked for on that loop.\",\n"
                        + AutoReplay.stamp() + ",\n\"wanted\":[\"STOW\",\"L4\",\"STOW\"],\n"
                        + "\"columns\":[\"t_s\",\"wanted\",\"goal_carriage_in\",\"carriage_in\",\"velocity_in_per_s\",\"volts\",\"stator_amps\",\"goal_wrist_deg\",\"wrist_deg\",\"wrist_volts\",\"wrist_stator_amps\"],\n"
                        + "\"samples\":[\n" + String.join(",\n", rows) + "\n]\n}\n");
        System.out.println("REPLAY elevatorMove: " + SimHarness.takeStepStats());
    }
}
