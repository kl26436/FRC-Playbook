# Rendering the final robot

`render_final.py` ray-traces the robot in one game pose. It reads the same mesh the site's 3D viewer uses
(`public/robot-viewer/robot.json` and `robot.bin`), so a new CAD export only needs `tools/make_viewer_data.py` run first.

    python3.11 tools/render/render_final.py <pose> <out.jpg> <width> <height> <samples>

Poses: `start`, `station`, `l4`, `algae`, `net`, `climb`. The images on the site are 1400 x 875 at 64 samples,
about three minutes each on two CPU cores.

## What it needs

Blender's Python module, `bpy` 5.x, which is built for Python 3.11. Where the default Python is newer:

    pip download bpy --no-deps --only-binary=:all: --python-version 3.11 --platform manylinux_2_28_x86_64 -d wheel
    unzip wheel/bpy-*.whl -d site
    PYTHONPATH=site python3.11 tools/render/render_final.py start start.jpg 1400 875 64

It prints a NumPy import error on start-up if NumPy is missing. The script does not use NumPy, so that is harmless.

## What is real and what is a stand-in

- **The robot is the CAD**, posed with the same joint numbers as the viewer and the robot code. Parts the CAD colours for
  clarity (the elevator stages, printed parts) are given their real finish: aluminium, and black for printed Onyx.
- **Fasteners, wires, chain and rope are not in the mesh**, so they are not in the pictures.
- **The swerve modules, motors and electronics are the makers' own models**, made coarser (see `tools/README.md`).
  Their finishes are set from the model's colours: black plates, blue tread, a red power hub.
- **The field parts are stand-ins** built from boxes and tubes at the sizes and positions the kickoff brief's model used:
  one reef face with a branch pair, a coral station wall and chute, a deep cage on a chain. They are not the field CAD.
- **Game pieces are placed by geometry, not by simulation.**
  - A held coral lies on the wrist floor, along the wrist.
  - A held algae sits against both claw rollers and the backstop rod: 14.15 in along the wrist and 12.30 in below it.
    With the wrist in the high-algae pose that puts the ball 50.7 in up, against 50.9 in for a ball on the reef.
  - The climbed cage is placed by turning it about the fork pivot from where it hangs with the fork level
    (7.5 in behind the pivot, 3.1 in off the carpet). That puts its eye bolt over the robot's centre, 24.0 in up;
    the climber drawing says 1.3 in behind centre and 23.9 in up. The robot is lifted 3.9 in and tipped 2.5 degrees nose up,
    which is the drawing's estimate.
- **The team number** is in Blender's built-in font, slanted. It is not the team's bumper font.
