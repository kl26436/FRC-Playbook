# Rebuilding the parts list

`src/data/parts.json` is generated from the CAD package, in three steps:

1. `parse_drawings.py` reads the part tables out of the drawing PDFs (after `pdftotext -layout`).
2. `build_parts.py` merges those with the flat patterns, the printed parts list and the 3D model's part names.
3. `make_site_data.py` sorts each part by how it is made, writes its proposed steps and draws its outline.

The paths at the top of each script point at where the package was unpacked when they were last run. Change them before running. Needs Python with `ezdxf`, and `pdftotext` from Poppler.

## Rebuilding the 3D model data

`make_viewer_data.py <robotA_mesh.json>` turns the CAD mesh export into `public/robot-viewer/robot.bin` and `robot.json`.
Run it after `parts.json` changes, because it reads the part numbers from there so a clicked part can link to its page.
