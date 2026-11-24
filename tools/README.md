# Rebuilding the parts list

`src/data/parts.json` is generated from the CAD package, in three steps:

1. `parse_drawings.py` reads the part tables out of the drawing PDFs (after `pdftotext -layout`).
2. `build_parts.py` merges those with the flat patterns, the printed parts list and the 3D model's part names.
3. `make_site_data.py` sorts each part by how it is made, writes its proposed steps and draws its outline.

The paths at the top of each script point at where the package was unpacked when they were last run. Change them before running. Needs Python with `ezdxf`, and `pdftotext` from Poppler.

## Rebuilding the 3D model data

`make_viewer_data.py <robotA_mesh.json>` turns the CAD mesh export into `public/robot-viewer/robot.bin` and `robot.json`.
Run it after `parts.json` changes, because it reads the part numbers from there so a clicked part can link to its page.

## Rebuilding the code example pages

The three example pages under `src/content/docs/code/` (`one-button-to-score`, `vision`, `write-an-auto`) are written in
`tools/code-pages/`. A line like `@@CODE main/java/frc/robot/Foo.java 10 24 Foo.java@@` is replaced by those lines of the
robot code, copied exactly, so an excerpt can never drift from what was typed.

    python3 tools/code-pages/build.py <clone of ClaudeBot> tools/code-pages/*.mdx

Edit the templates, not the generated pages. When the robot code changes, check each line range still points at the same
method before rebuilding, and update the commit named in each page's note.
