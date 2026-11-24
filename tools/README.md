# Rebuilding the parts list

`src/data/parts.json` is generated from the CAD package, in three steps:

1. `parse_drawings.py` reads the part tables out of the drawing PDFs (after `pdftotext -layout`).
2. `build_parts.py` merges those with the flat patterns, the printed parts list and the 3D model's part names.
3. `make_site_data.py` sorts each part by how it is made, writes its proposed steps and draws its outline.

`build_parts.py` and `make_site_data.py` take the unpacked package folder as their first argument (`build_parts.py` takes the
mesh export as its second). The other paths at the top of each script point at where things were when they were last run.
Needs Python with `ezdxf`, and `pdftotext` and `pdftoppm` from Poppler.

After a new CAD package, also replace what the site hosts under `public/files/`: the drawing PDFs, one JPEG per sheet
(`pdftoppm -r 100 -jpeg`, named `<pdf name>-<page>.jpg`), the DXF folders and the four list CSVs. Then update the revision
letters on the Downloads page.

## The 2D views on the part pages

A router part's picture is its DXF. Every other made part gets views drawn from its solid by `make_part_views.py [folder
of the package's STEP files]`, which writes `src/data/part-views.json`. Run it after `make_site_data.py`, because it reads
`parts.json` to see which parts have no flat pattern. It looks for each part by its mark in the package's subsystem STEP
files, and in `printed/` for the few small printed parts that are not in those.

- It looks at the part along the direction of its biggest flat face, and adds a view along any other direction holes run
  in. A round part gets a side view and an end view.
- A hole is a cylinder face that curves inwards and goes all the way round. Slots and fillets are left out of the table.
- Hole names (drill size, what it is usually for) come from the same list the flat patterns use, plus the two rivnut sizes.
- Check that every job sheet still prints on one page after running it.

## When a CAD package arrives without a new mesh export

`update_mesh_from_step.py` was written for package 3.3, which changed the elevator's fixed parts, the climber and one side
rail but came with the 3.2 mesh export. It keeps every unchanged part from the old export and re-reads the changed
packages from their STEP files, using the mesh export script's own settings. It prints what it removed and added, so the
swap can be checked against the package's change list. Edit the three sections at the top of it for the next change.

## Rebuilding the 3D model data

Four steps, in this order. Each prints a short check when it finishes.

    # 1. Each vendor STEP file, once: a coarse mesh in the vendor's own axes
    python3 tools/vendor_tessellate.py <file.step> <cache>/<name>.npz [tolerance] [smallest face] [names to leave out or recolour]
    # 2. Put every vendor model where it sits on the robot
    python3 tools/make_vendor_parts.py <cache> <folder of vendor STEP files> <CAD source folder> <cache>/placed.npz [robotA_mesh.json]
    # 2b. The climber's motors, gearboxes and servos, already placed in the tower hardware file
    python3 tools/make_climber_vendor_parts.py <2_onshape_imports/climber_hw_tower.step> <cache>/climber_placed.npz
    # 3. The robot: public/robot-viewer/robot.bin and robot.json
    python3 tools/make_viewer_data.py [robotA_mesh.json] --vendor=<cache>/placed.npz,<cache>/climber_placed.npz
    # 4. The fasteners, then the assembly steps
    python3 tools/make_fastener_data.py [robotA_detail_fasteners.step] --vendor=<cache>/placed.npz,<cache>/climber_placed.npz
    python3 tools/assembly/steps.py

- The CAD mesh export draws the swerve modules, their motors, the electronics and the camera as outline shapes. Steps 1 and 2
  swap in the makers' own models: SDS MK4i, WCP Kraken X60, REV power hub and Mini Power Module, NI roboRIO, CTRE CANivore
  and Pigeon, the AndyMark breaker, the Vivid-Hosting radio and the Limelight 4. Leave `--vendor` off to build without them.
- The package's climber STEP draws each climber motor as a plain cylinder and each gearbox and servo as a box. The real
  models (Kraken X60, REV MAXPlanetary 25:1, REV Smart Robot Servo) are in `climber_hw_tower.step`, already in place, so
  step 2b lifts them out of there. In that file both sides are named "climber right"; the script names each side from
  where the model actually sits.
- `make_vendor_parts.py` uses the same placements as the CAD source (`assembly/vendor_place.py`). It prints how far each
  electronics model's mounting holes land from the holes we drill. All were within 0.002 in. The roboRIO and the breaker
  fit either way round, so the model cannot say which way their connectors face.
- The swerve module was tessellated at tolerance 0.2 and smallest face 0.1, leaving out the Falcon motors (we use Krakens),
  the screws and the two gear sets we do not use. Its plates were recoloured black, because the file's colours are placeholders.
- Run step 3 after `parts.json` changes, because it reads the part numbers from there so a clicked part can link to its page.
- Run step 4 after step 3 every time. Fasteners and steps refer to parts by their number in `robot.json`, and that number changes.
- The assembly steps are written by hand in `tools/assembly/steps.py`. The script checks that every part and every fastener
  in the model is placed by some step, and stops if a step names a part that is not there.

## Rebuilding the wiring data

`make_wiring_data.py [robotA_can_map.csv]` turns the CAD package's CAN map into `src/data/wiring.json`. The Wire it
chapter's diagrams and its ID table are drawn from that file, so they cannot disagree with each other. The build stops
if a device in the map is missing from the bus diagram.

## Rebuilding the code example pages

The three example pages under `src/content/docs/code/` (`one-button-to-score`, `vision`, `write-an-auto`) are written in
`tools/code-pages/`. A line like `@@CODE main/java/frc/robot/Foo.java 10 24 Foo.java@@` is replaced by those lines of the
robot code, copied exactly, so an excerpt can never drift from what was typed.

    python3 tools/code-pages/build.py <clone of ClaudeBot> tools/code-pages/*.mdx

Edit the templates, not the generated pages. When the robot code changes, check each line range still points at the same
method before rebuilding, and update the commit named in each page's note.

## Code pages

- `code-pages/build.py <ClaudeBot clone> code-pages/<page>.mdx` fills each `@@CODE path first last title@@` line with those
  lines of the robot code and writes the page to `src/content/docs/code/`. Edit the page here, not there.
- `code-pages/make_control_data.py <ClaudeBot clone>` reads the setpoints, gains and limits out of the code and writes
  `src/data/control.json`. The Setpoints and control page draws its chart, its gain tables and its model from that file.
- `replay-recorder/` holds the test that records the runs played back on One button to score and How the camera finds
  the robot. Its README says how to record, and why the copies in this repo carry a caveat.

## The field in the replays

`public/robot-viewer/field.js` builds the blue half of the field from boxes, tubes and balls: the reef, both coral
stations, the processor, the barge with its cages and nets, the walls and the tape. Plan positions are the ones in
`src/assets/field-map.svg`; the reef, station, net and cage sections are the ones `tools/render/render_final.py` uses.
In replay mode the viewer keeps the robot at the origin and moves the field under it. The page (`AutoReplay.astro`)
posts the robot's place, what it holds, what it has scored or dropped, and for the camera recordings the tag in view.
