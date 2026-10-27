# Mechanical design

Generated with CadQuery from `enclosure.py`. Every printed part fits a 220 × 220 mm bed.

```
pip install cadquery trimesh matplotlib
python3 enclosure.py          # writes stl/ and step/ (includes the KiCad board STEP)
python3 render.py --pcb       # writes renders/*.png
```

The board model comes from `hardware/kicad/cell_test_bench.step`. To regenerate it:
`kicad-cli pcb export step --subst-models --user-origin 0x0mm -o cell_test_bench.step cell_test_bench.kicad_pcb`.

## Layout

There are two units, connected by a cable harness through grommets.

| Unit | Outer size | Contents |
|---|---|---|
| Electronics box | 214 × 214 × 89 mm | Main PCB on 8 mm standoffs. IRFP260N load heatsink at the PCB front edge with a 60 mm fan in the front wall. 0.1 Ω 50 W resistor on the same heatsink. Two XL4016 modules stacked front-left. MP1584. 4 mm binding posts on the left wall (PSU in). Blue Pill USB through the back wall. |
| Thermal unit | 130 × 130 × ~142 mm | Bottom: 60 mm fan, hot-side heatsink, 2 × TEC1-12706, 100 × 50 × 6 mm aluminium cold plate. Top: insulated cell pocket. BTS7960 under the vented rear cover. |

### Cell pocket (18650 and 21700, one at a time)

- The cold plate is the pocket floor. The cell lies on a 1 mm thermal pad on the plate.
- Swap the printed saddle to change cell size: `T6_saddle_18650` or `T7_saddle_21700`. The saddle centres the cell; its open floor lets the cell touch the pad.
- Two contact blocks ride in grooves in the pocket walls. Each block holds:
  - a 22 × 22 × 1.5 mm copper plate for power (solder a 1.5 mm² wire to its back);
  - a P75 spring probe through the plate centre for Kelvin sense, so it touches the cell terminal directly.
- The right block is pushed by an M4 thumbscrew through the end wall, which takes up the 65 mm / 70 mm length difference and sets contact pressure.
- The contact-plate centre sits 12 mm above the cold plate. The 22 mm plate covers both cell centres (18650 ≈ 10.3 mm, 21700 ≈ 11.7 mm).
- The lid has a 30 mm 5 V mixing fan and a port for the pocket-air NTC. Tape the cell-surface NTC to the cell.

## Printed parts

| File | Qty | Material / notes |
|---|---|---|
| E1_ebox_base.stl | 1 | PETG, 3 walls, 20 % infill |
| E2_ebox_lid.stl | 1 | PETG, print upside down (label face down) |
| E3_module_plate.stl | 1 | PETG |
| E4_heatsink_clamp.stl | 2 | PETG |
| T1_thermal_base.stl | 1 | PETG |
| T2_pocket_body.stl | 1 | PETG, 3 walls, **10 % gyroid infill** (air pockets insulate) |
| T3_pocket_lid.stl | 1 | PETG, 10 % gyroid, print upside down |
| T4_contact_block_fixed.stl | 1 | PETG or ASA (warm near the cell) |
| T5_contact_block_slider.stl | 1 | PETG or ASA |
| T6_saddle_18650.stl | 1 | PETG |
| T7_saddle_21700.stl | 1 | PETG |

Use PETG or ASA rather than PLA: the pocket reaches 45 °C and the electronics box is warm near the load heatsink.

## Hardware to buy

- 2 × TEC1-12706 Peltier, 40 × 40 × 3.8 mm (e.g. Direnc.net)
- Aluminium flat bar 100 × 50 × 6 mm (cold plate). Drill 4 × Ø3.4 at the corners (3.5 mm and 6 mm from the edges).
- Hot-side heatsink about 100 × 60 × 25 mm with 60 mm fan, 12 V
- Load heatsink about 100 × 40 × 70 mm (extrusion or an old CPU cooler) with 60 mm fan, 12 V
- 30 mm 5 V fan (pocket mixing)
- Thermal pad 1 mm (80 × 30 mm) and thermal paste for the Peltiers and MOSFET
- 0.1 Ω 50 W aluminium-housed resistor (RH50)
- 2 × copper sheet 22 × 22 × 1.5 mm, 2 × P75 spring probes, M4 × 30 thumbscrew + M4 heat-set insert
- M3 heat-set inserts (about 30), M3 screws, 4 × M3 × 30 spacers for the XL4016 stack
- 2 × 4 mm binding posts, 3 × PG7 grommets (or Ø16 rubber grommets)
- XPS foam strips or closed-cell foam tape to seal the cold plate edge and the lid plug
- KSD9700 60 °C NC thermostat (on the load heatsink)

## Peltier sandwich

Heatsink → paste → 2 × TEC1-12706 (cold side up, wires in series) → paste → cold plate. Clamp the plate to the heatsink with 4 × M3 screws through nylon washers so the plate does not short the heat path. Tighten evenly.

## Known limits

- The KiCad 3D model of the TO-247 has long leads that show below the PCB; cut the real leads after soldering. The board sits on 8 mm standoffs.
- Module and heatsink shapes in the assembly are envelopes. Check the real parts you buy and adjust the parameters at the top of `enclosure.py`.
- The lowest reachable cell temperature depends on the hot-side heatsink. Measure it before relying on below-ambient tests.
