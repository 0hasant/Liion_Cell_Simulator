# Mechanical design (v0.4)

Generated with CadQuery from `enclosure.py`. Every printed part fits a 220 × 220 mm bed.

```
pip install cadquery trimesh matplotlib
python3 enclosure.py          # writes stl/ and step/ (includes the KiCad board STEP)
python3 check.py --pcb        # bed size + collision check of the whole assembly
python3 render.py --pcb       # writes renders/*.png
```

The board model is `hardware/kicad/cell_test_bench.step`. To regenerate it:
`kicad-cli pcb export step --subst-models --user-origin 0x0mm -o cell_test_bench.step cell_test_bench.kicad_pcb`.

## Layout

There are two units, connected by cables through grommets.

| Unit | Outer size | Contents |
|---|---|---|
| Electronics box | 214 × 214 × 89 mm | Main PCB on 8 mm standoffs. Load cooler (80 × 80 × 54 mm CPU cooler) standing on its side in a printed cradle, flat base against the PCB front edge: IRFP260N, the 0.1 Ω 50 W resistor and the KSD9700 thermostat bolt to it. Its fan faces an 80 mm grille in the front wall. Two XL4016 modules stacked front-left on a printed plate. 4 mm binding posts on the left wall (PSU in). Blue Pill USB through the back wall. |
| Thermal unit | 130 × 130 × about 155 mm | Bottom: 80 × 80 × 54 mm CPU cooler with its fan pointing down at a floor grille, standing on four posts. On its base: 2 × TEC1-12706 side by side, then the 100 × 50 × 6 mm aluminium cold plate. Top: insulated cell pocket. Back: wiring chamber for the Peltier series link and NTC splices. |

### What changed from v0.3

- No BTS7960 in the thermal unit: the Peltiers are driven from the main board (J702).
- No MP1584 module: 5 V comes from a 7805 on the board.
- Both heatsinks are now the same 80 × 80 × 54 mm CPU cooler with a 12 V fan (in stock at Motorobit). The thermal base grew to 72.8 mm to hold it.
- The cold plate is clamped by four countersunk M3 screws into bosses in the thermal base, which pulls the plate onto the TECs and the cooler onto its posts.
- The load cooler sits in a printed cradle (`E4_cooler_cradle`), and two ribs under the lid stop it lifting.
- Grommets moved: cell power + Kelvin through the right wall behind the cooler; Peltier, fans and NTCs further back, next to their connectors.
- The pocket mixing fan is now 12 V (same 30 mm size).

## Cell pocket (18650 and 21700, one at a time)

- The cold plate is the pocket floor. The cell lies on a 60 × 10 × 1 mm thermal pad on the plate.
- Swap the printed saddle to change cell size: `T6_saddle_18650` or `T7_saddle_21700`. The saddle centres the cell; its open floor lets the cell touch the pad.
- Two contact blocks ride in grooves in the pocket walls. Each block holds:
  - a 22 × 22 × 1.5 mm copper plate for power (solder a 1.5 mm² wire to its back);
  - a spring probe through the plate centre for Kelvin sense, so it touches the cell terminal directly.
- The right block is pushed by an M4 thumbscrew through the end wall, which takes up the 65 / 70 mm length difference and sets contact pressure.
- The lid has the 30 mm mixing fan and a port for the pocket-air NTC. Tape the cell-surface NTC to the cell.

## Printed parts

| File | Qty | Material / notes |
|---|---|---|
| E1_ebox_base.stl | 1 | PETG, 3 walls, 20 % infill |
| E2_ebox_lid.stl | 1 | PETG, print upside down (label face down), supports under the two ribs not needed |
| E3_module_plate.stl | 1 | PETG |
| E4_cooler_cradle.stl | 1 | PETG |
| T1_thermal_base.stl | 1 | PETG |
| T2_pocket_body.stl | 1 | PETG, 3 walls, **10 % gyroid infill** (air pockets insulate) |
| T3_pocket_lid.stl | 1 | PETG, 10 % gyroid, print upside down |
| T4_contact_block_fixed.stl | 1 | PETG or ASA (warm near the cell) |
| T5_contact_block_slider.stl | 1 | PETG or ASA |
| T6_saddle_18650.stl | 1 | PETG |
| T7_saddle_21700.stl | 1 | PETG |

Use PETG or ASA, not PLA: the pocket reaches 45 °C and the load cooler gets warm. About 0.9 kg of filament in total.

## Hardware to buy

The priced list with Turkish shops is `hardware/bom_offboard.csv`. Mechanical items:

- 2 × CPU cooler 80 × 80 × 54 mm with 12 V fan
- 2 × TEC1-12706 Peltier, 40 × 40 × 3.8 mm
- Aluminium flat bar 100 × 50 × 6 mm (cold plate). Drill 4 × Ø3.4 with a 90° countersink at (3.5, 6), (96.5, 6), (3.5, 44), (96.5, 44) mm
- 0.1 Ω 50 W aluminium-housed resistor, KSD9700 60 °C NC thermostat
- 30 × 30 × 10 mm 12 V fan (pocket)
- Thermal paste, 1 mm thermal pad, TO-247 insulating pad + bushing (the IRFP260N tab is the drain)
- 2 × copper sheet 22 × 22 × 1.5 mm, 2 × spring probes, M4 × 30 thumbscrew + M4 heat-set insert
- About 30 M3 heat-set inserts, M3 screws (4 of them countersunk M3 × 12 for the cold plate), 4 × M3 × 30 spacers for the XL4016 stack, 4 × 8 mm standoffs for the PCB
- 2 × 4 mm binding posts, 3 × Ø16 rubber grommets
- XPS foam strips or closed-cell foam tape to seal the cold plate edge and the lid plug

## Assembly notes

- **Load cooler:** drill the cooler base for Q301 (M3, tab hole about 30 mm above the box floor, centred on Q301), the resistor flanges and the thermostat. Check the cooler base is flat over the area under Q301; if not, add a 3 mm aluminium spreader plate and shorten the cradle by 3 mm (`HS_E` in `enclosure.py`).
- **Peltier sandwich:** cooler base → paste → 2 × TEC1-12706 (cold side up, wired in series) → paste → cold plate. Tighten the four countersunk screws evenly, a quarter turn at a time. Re-tighten after the first warm run (PETG settles).
- **Peltier polarity:** with K3 relaxed the board drives J702 A positive. Wire it so that this cools the plate; `docs/BRINGUP.md` step 6 tells you how to check.

## Known limits

- Module and cooler shapes are envelopes. Measure the parts you receive and adjust the parameters at the top of `enclosure.py` (`COOLER`, `XL4016`, `RH50`).
- The KiCad 3D model of the TO-247 has long leads that show below the PCB; cut the real leads after soldering.
- The lowest reachable cell temperature depends on the hot-side cooler. Measure it before relying on below-ambient tests.
