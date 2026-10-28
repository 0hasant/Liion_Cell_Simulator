# PROJECT_SYNC: shared context for all chats and sessions

Read this first in any new chat about the Li-ion cell test bench. It is where the hardware chat and the 3D/mechanical chat agree on what we are building and what the limits are.

- Repo: `0hasant/Liion_Cell_Simulator`.
- **Master copy: `docs/PROJECT_SYNC.md` in the repo.** The Claude Project "Li-ion cell characteristic tester" holds a mirror. Edit the repo file, commit, then update the Project copy with the same text.

Last updated: 2026-10-28 (repo state v0.2)

## 1. Goal

Build a single-cell Li-ion characterization bench so that, in the end, we can fit a **2RC equivalent-circuit model** of a cell (OCV, R0, R1/C1, R2/C2 versus SOC and temperature).

Order of work: (1) hardware and mechanics, (2) firmware + Python UI, (3) test procedures and model fitting.

This is part of the Solaris final-year project (see the DAB converter project).

- **Budget target:** below 1500 TL (see section 6: not verified yet).
- **Workshop:** hand soldering, FDM printing (PETG/ASA, 220 x 220 mm bed).

## 2. What the bench does (requirements)

- **Cells:** 18650 and 21700, one at a time (DMEGC INR45E, generic 3.5 Ah 18650).
- **Discharge:** 0 to 10 A linear constant-current load, down to 2.0 V.
- **Charge:** from a 30 V / 10 A bench PSU through an XL4016 CC/CV module. The voltage is set by a DAC, with a 4.25 V hardware ceiling.
  - Up to 5 A for the 21700 (INR45E).
  - The generic 3.5 Ah 18650 is limited to about 0.5C (≈1.75 A) until its datasheet is known.
- **Measurement:** bidirectional current on one 10 mOhm 4-terminal shunt, Kelvin cell voltage, four NTCs (ADS1115 x2).
- **Temperature control:** cell held at about 10 to 45 degC in an insulated pocket, 2 x TEC1-12706 Peltiers.
- **Control:** STM32F103 Blue Pill, USB CDC to a Python UI.
- **Safety:** hardware OV / UV / OC / OT protection that works without firmware.

## 3. Who owns what

| Area | Chat | Source of truth |
|---|---|---|
| Electronics (schematic, PCB, BOM, protection, parts choice) | Hardware chat | `hardware/` |
| Enclosure, thermal unit, cell pocket, printed parts | 3D / mechanical chat | `mechanical/` |
| Firmware, Python UI, test procedures, model fitting | Not started | `firmware/`, `ui/` |

Rule: a chat edits only its own area. If it needs something from the other area, it writes a request in section 7 (Open interface items) instead of changing the other side.

## 4. Interface contract (the numbers both sides must respect)

### Hardware gives mechanics

| Item | Value | Source |
|---|---|---|
| PCB size | 180 x 130 mm, 2 layers (order 2 oz copper) | `hardware/kicad/cell_test_bench.kicad_pcb` |
| Board model for fitting | `hardware/kicad/cell_test_bench.step` | Regenerate with kicad-cli (see `mechanical/README.md`) |
| Mounting holes | 4 x M3 at (4, 4), (176, 68), (4, 126), (176, 126) mm from the PCB top-left corner. PCB on 8 mm standoffs in the box. | `hardware/tools/pcbgen.py`, `mechanical/enclosure.py` |
| Connector placement | All connectors on board edges, wire entry facing outward. **Left:** PSU input, buck modules, XL4016 charger, thermostat. **Bottom:** cell, series resistor, IRFP260N, NTCs. **Top:** Peltier driver, fans, Blue Pill USB. | `README.md` layout notes |
| Load MOSFET | IRFP260N (TO-247) at the bottom edge, back facing outward so the heatsink bolts on beyond the edge | `README.md` |
| Plug-in modules with keep-outs | Blue Pill, 2 x ADS1115, 2 x MCP4725 | `README.md` |
| Heat sources | IRFP260N + 0.1 Ohm 50 W resistor on the load heatsink (up to ~10 A x cell voltage in the load), XL4016 modules, BTS7960 | `README.md` |
| Thermostat | KSD9700 60 degC NC, must be mounted on the load heatsink (wired to J104) | `hardware/` Power sheet |
| Fans | Two 12 V fans switched together on one PWM (PA8, IRLZ44N): load heatsink 60 mm and Peltier hot side 60 mm. One 5 V 30 mm pocket mixing fan, always on. | `mechanical/README.md` |
| NTCs (4, on ADS1115 #2) | Cell surface (thermal unit, taped to the cell), pocket air (thermal unit, lid port), load heatsink (electronics box), Peltier hot side (thermal unit) | `hardware/` Measurement sheet |

### Mechanics gives hardware

| Item | Value |
|---|---|
| Electronics box | 214 x 214 x 89 mm outer (86 mm base + 3 mm lid) |
| Thermal unit | 130 x 130 x ~142 mm outer |
| BTS7960 (Peltier driver) | Mounted in the thermal unit, under the vented rear cover (see section 7) |
| Cell pocket | 100 x 50 x 6 mm aluminium cold plate is the pocket floor. Saddles T6 (18650) / T7 (21700). Contact plates 22 x 22 x 1.5 mm copper with a P75 Kelvin probe. |
| Cable links between units | Through grommets: cell power (2 x 1.5 mm2, short) + Kelvin sense (2 thin wires), BTS7960 supply (+12V_SW, GND) + logic (RPWM, LPWM, EN, 5 V, GND), NTCs (3 pairs), Peltier hot-side fan. Cell and sense wires must be short; power wires thick. |
| Hardware to buy | See `mechanical/README.md` |

## 5. Hard constraints (do not break without agreeing)

1. One cell at a time, 18650 or 21700, swapped by changing the printed saddle.
2. Pocket temperature range about 10 to 45 degC. Printed parts near the cell and the load heatsink must be PETG or ASA, not PLA.
3. Every printed part fits a 220 x 220 mm bed.
4. Max currents:
   - Discharge: 10 A (trip about 11 A).
   - Charge: 5 A (trip about 6.4 A); generic 18650 about 1.75 A.
   - Wiring, contacts and the shunt path must carry this.
5. Cell voltage limits enforced in hardware: OV about 4.29 V, UV about 1.95 V. OT trip about 62 degC on the heatsink or cell NTC.
6. Cell terminals need four-wire (Kelvin) contact. The power plate and the sense probe touch the cell separately.
7. Hand-solderable parts only:
   - THT where sensible.
   - 1206 passives.
   - SOIC-8 (OPA2188) and the wide-2512 LVK25 shunt are the smallest allowed.
8. The KiCad files are the source of truth once edited in KiCad. Do not re-run the `hardware/tools/` generators after that.
9. Budget: target below roughly 1500 TL total (not yet checked against a priced BOM).

## 6. Known limits and risks (carry these forward)

- **Charger current limit:** the XL4016's own limit is bypassed (shared ground). Charge current is firmware-regulated and limited by the OC comparator.
- **UV protection:** also trips with no cell inserted, and blocks charging a cell below about 1.95 V.
- **Comparators:** no hysteresis; firmware must latch faults.
- **Check before soldering:**
  - BTS7960 module accepts 3.3 V logic.
  - Module pin orders (MCP4725, ADS1115, BTS7960) vary by seller.
  - Relay footprint vs the Panasonic ALFG2PF121 datasheet.
- **TO-247 3D model:** the KiCad model has long leads showing below the PCB; cut the real leads after soldering.
- **3D envelopes:** heatsink and module shapes in the 3D assembly are envelopes. Re-measure the real purchased parts and update the parameters at the top of `mechanical/enclosure.py`.
- **Lowest cell temperature:** depends on the hot-side heatsink; measure before relying on below-ambient tests.
- **PCB layout:** autorouted, electrically complete (DRC clean) but not yet hand-tidied. The layout may still change, so mechanics should re-export the board STEP before finalizing.
- **Budget:** not verified. `hardware/bom.csv` has no prices yet. Peltiers, heatsinks, aluminium plate, relays, OPA2188, LVK25, modules and filament together may exceed 1500 TL. Price the BOM before ordering.
- **Supply:** OPA2188 showed 0 stock at Özdisan (request price). Alternative OPA2187.

## 7. Open interface items (requests between chats)

Add one line per item: `date | from -> to | request | status`.

- 2026-10-28 | sync review -> hardware + mechanics | **Peltier driver location mismatch.**
  - The PCB routes the BTS7960 motor outputs back to the board (J702 M+/M- -> J703 -> Peltiers), but mechanics mounts the BTS7960 in the thermal unit. That sends the ~3 A Peltier current out, back and out again.
  - Decide one: (a) Peltiers wire directly to the BTS7960 in the thermal unit and J703 is not used (no PCB change needed, J702 M+/M- left open); or (b) move the BTS7960 into the electronics box.
  - Recommended: (a).
  - Status: open.

## 8. Change protocol

1. Before changing any number in section 4 or 5, edit this file in the same commit and add a line to the changelog.
2. If hardware moves a connector, heatsink position, or mounting hole, the PCB STEP must be regenerated and the mechanical chat told via section 7.
3. If mechanics changes box size, standoff height, or cable path, the hardware chat is told via section 7.
4. Start of every chat: read this file, then `README.md` (and `mechanical/README.md` for 3D work). Keep summaries of decisions in this file, not only in chat.
5. After editing this file in the repo, copy the same text to the Claude Project (`claude/PROJECT_SYNC.md`).

## 9. Changelog

- 2026-10-28: file created from repo state v0.2 when hardware and 3D design were split into separate chats.
- 2026-10-28: review fixes:
  - File committed to the repo as master.
  - Added: BTS7960 location mismatch (section 7), per-cell charge limit, thermostat mount, NTC locations, mounting-hole coordinates, cable list, SOIC-8/LVK25 in the hand-solder rule.
  - Budget marked as not verified.
