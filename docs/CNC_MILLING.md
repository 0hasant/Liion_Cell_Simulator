# Milling the board on the Snapmaker

The v0.4 board is single-sided: all copper is on the bottom (`B.Cu`). Components go on the plain FR4 side, their leads come through and are soldered on the copper side. Where one copper layer cannot make a connection, a wire jumper (W1, W2 …) on the component side does it.

Files are in `hardware/fab/` (made by `hardware/tools/fab.py`):

| File | Use |
|---|---|
| `gerber/cell_test_bench-B_Cu.gbr` | Copper, for FlatCAM or pcb2gcode (board seen from the component side) |
| `gerber/cell_test_bench-Edge_Cuts.gbr` | Outline |
| `gerber/cell_test_bench-PTH.drl`, `-NPTH.drl` | Excellon drill files (mm) |
| `svg/B_Cu_mirrored.svg` | Copper as seen with the copper side facing up on the bed, 1:1, for Snapmaker Luban |
| `svg/Edge_Cuts_mirrored.svg` | Outline, same orientation |
| `svg/F_Silkscreen.svg` | Part outlines and references, for the laser on the component side (optional) |
| `print/copper_from_component_side_1to1.pdf` | Print at 100 % and lay the real parts on it before milling |
| `drill_summary.csv` | Which drill sizes and how many holes |
| `jumpers.csv` | Every wire jumper: net, both ends, length, wire type |

## Board size and material

- 180 × 130 mm, single-sided FR4, 1.6 mm, 35 µm copper. A 200 × 300 mm blank leaves room for one retry.
- Design rules: 0.5 mm minimum track, 0.4 mm minimum clearance, copper at least 1 mm from the edge.

## Option A: FlatCAM (recommended: it handles the mirroring and the drill file)

1. Open the B_Cu Gerber, Edge_Cuts Gerber and both drill files.
2. **Mirror all of them** about the X axis (Tool → 2-Sided PCB, axis Y, point = board centre 90, 65). The copper side faces up on the bed, so the image has to be mirrored.
3. Isolation routing on B_Cu: 30° V-bit 0.1 mm tip, depth 0.08–0.1 mm, 2 passes, 50 % overlap. Check that the isolation does not leave copper between pads that should be separate (between DIP pins it is 0.7 mm; with a 0.2 mm effective cut width this works).
4. Drill job from the Excellon file. Group by size; the summary file lists them (0.8, 1.0, 1.3, 1.5, 1.8, 2.0 and 3.2 mm).
5. Cut-out: 1 mm or 2 mm end mill around Edge_Cuts, 4 tabs.
6. Export G-code and run it in Luban as "CNC G-code".

## Option B: Snapmaker Luban only

1. CNC → import `B_Cu_mirrored.svg`. Set the size to 180 × 130 mm exactly (check after import: Luban sometimes rescales SVGs).
2. Carving mode "On the path" with a V-bit for isolation. Luban cuts along SVG outlines; the copper areas in the SVG are filled shapes, so it cuts around them.
3. Drill holes with the drill file through FlatCAM, or by hand on a drill press using the 1:1 print.
4. Cut the outline with `Edge_Cuts_mirrored.svg`.

## Order of work on the machine

1. Fix the blank flat (double-sided tape over the whole area, copper side up). Flatness matters more than anything else for 0.1 mm isolation.
2. Probe Z at several points, or mill a 0.05 mm facing pass first if the bed is not flat.
3. Isolation → drilling → outline.
4. Clean with fine steel wool, check with a multimeter (`docs/BRINGUP.md` step 0.5), then tin the copper.

## Wire jumpers

- Each jumper is two holes 1.0 mm with a 2.4 mm pad. Fit them before the other parts.
- Insulated 0.6 mm solid wire for signals. The jumpers on power nets (`jumpers.csv` says which) use 0.75 mm² stranded wire.
- No jumper is in the 10 A cell loop: `CELL_P`, `CELL_N`, `LOAD_P`, `LOAD_D` and `CHG_OUT` are copper only.

## High-current copper

Milled 35 µm copper is not enough for 10 A on its own. After soldering, tin the wide tracks of the cell loop (`CELL_P`, `CELL_N`, `LOAD_P`, `LOAD_D`) and the wide `PGND` strip along the left and bottom edges, and solder a 1.5 mm² bare copper wire along them.

## SMD parts on the copper side

R201 (2512 shunt) and U301 (OPA2171, SOIC-8) are soldered on the copper side. Their pads are in the copper Gerber; nothing needs drilling. U301 sits on the copper side, so when you look at the copper side you see its top: the pinout matches the datasheet top view there. On the component-side print it appears mirrored. Check the pin-1 mark before soldering.
