# Layout review checklist (cell test bench PCB, v0.4)

Use this to judge any layout of the board: a router result, a hand edit, or a revision. It names this circuit's own nets and reference designators, so each check can be done by opening the board in KiCad and looking at the named parts.

Last updated: 2026-11-11. v0.4 is single-sided: all copper on `B.Cu`, wire jumpers (W1 …) on the component side.

## How to use it

1. **Gates first.** A layout that fails a gate is rejected or reworked, whatever its score.
2. **Then score sections A to F** (100 points). Note every failed item with the part references.
3. Pick the highest score. On a tie, fewer jumpers wins.
4. Write the result in the table at the end and commit.

## Gates (must pass)

| # | Gate | How to check |
|---|---|---|
| G1 | 0 unconnected items | `hardware/fab/drc.rpt` ("Found 0 unconnected") |
| G2 | 0 DRC errors with the CNC rules (0.5 mm track, 0.4 mm clearance, 1 mm from edge, 0.4 mm annular ring) | `drc.rpt` |
| G3 | Fixed parts at their positions: all J*, K*, H101–H104, Q301, U501, R201 | Compare with the FIXED table in `hardware/tools/pcbgen.py` |
| G4 | Kelvin nets carry no load current: `ISNS_G`, `ISNS_N` leave only from R201 pads 3/2; `SENSE_P`, `SENSE_N` only from J206 | Highlight each net |
| G5 | No wire jumper in `CELL_P`, `CELL_N`, `LOAD_P`, `LOAD_D`, `CHG_OUT` | `hardware/fab/jumpers.csv` |

## A. High-current paths (25 points)

Discharge loop: J205.1 (cell +) → `CELL_P` → K2 → `LOAD_P` → J301 (0.1 Ω off-board) → `LOAD_D` → Q301 drain → source → `PGND` → R201 pad 4 → shunt → pad 1 → `CELL_N` → J205.2. Charge: J401.3 → `CHG_OUT` → K1 → `CELL_P` → cell → `CELL_N` → R201 → `PGND` → J401.2/4.

- **A1 Width (10).** 1 oz copper, 20 °C rise: about 2.8 mm for 10 A and 1.1 mm for 5 A. Cell loop ≥ 3.4 mm, `CHG_OUT` ≥ 1.6 mm, `PGND` ≥ 2 mm (≥ 3 mm along the edges), 12 V / Peltier nets ≥ 1.6 mm. Milled copper is reinforced with wire anyway (`docs/CNC_MILLING.md`).
- **A2 Short loop (5).** J205, R201, K1, K2, J301, Q301 along the bottom edge.
- **A3 No jumpers in power nets (5).** Jumpers on `PGND`, `+12V`, `+12V_SW`, `TEC_*` are allowed but each must be 0.75 mm² wire and carry ≤ 3 A.
- **A4 Q301 thermal (5).** Nothing between Q301's tab and the board edge; the load cooler sits flush with the edge.

## B. Grounding (15 points)

`PGND` carries the power returns; `GND` is the signal reference. They meet only at JP201 next to R201.

- **B1 (6).** JP201 is the only GND–PGND connection (check the netlist and that no jumper joins them).
- **B2 (5).** The GND fill reaches every analog ground pin (U301 pin 4, U401 pin 4, U501 GND, U601/U602 pin 12, C601, R603, R605, R607) through copper, not through long thin necks.
- **B3 (4).** The Peltier PWM current (`TEC_SW` → Q703 → `PGND`) and the fan current do not share copper with `GND`.

## C. Current and voltage sensing (20 points)

- **C1 (6).** `ISNS_G` and `ISNS_N` leave R201 pads 3/2 side by side and reach R305/R306/R307/R314/R317 (load loop) and R501/R502 (ADS1115) without running beside `CELL_*`, `LOAD_*` or `TEC_*`.
- **C2 (5).** U301 and its input network (R303–R308, R314–R317, C303, C304) within about 40 mm of R201.
- **C3 (5).** `SENSE_P`/`SENSE_N` from J206 run as a pair to R503/R505 and R408.
- **C4 (4).** ADC filter parts (R501–R505, C501, C502) close to U501.

## D. Load loop stability (15 points)

- **D1 (6).** `GATE` short: R312 near Q301 pin 1, R313 at the gate. `OA_OUT` from U301 pin 1 to R312 short.
- **D2 (4).** C304 and R307 at U301 pins 1/2: small `INN` loop.
- **D3 (3).** D301/D302 (load-off and fault injection) close to `INN`.
- **D4 (2).** C306/C307 decoupling at U301 pin 8.

## E. Protection, relays, MCU, thermal (10 points)

- **E1 (3).** Flyback diodes D201/D202/D701/D103 close to their relay coils.
- **E2 (3).** U601, U602, U603 together; C601 (10 µF) at U603; `VREF` short.
- **E3 (2).** I2C from J801 to U501 short.
- **E4 (2).** `TEC_PWM`, `FAN_PWM` away from the analog block.

## F. CNC manufacturability (15 points)

- **F1 (8).** Wire jumpers: ≤ 30 → 8, ≤ 50 → 6, ≤ 70 → 4, ≤ 90 → 2, more → 0.
- **F2 (4).** No track between pins of DIP-14 (U601, U602) or pin headers (it can't fit with the rules, but check).
- **F3 (3).** No copper slivers under 0.5 mm, no isolated islands (island removal is on in the GND fill).

## Not scored, list it

- Silkscreen overlaps (only matters if you laser-mark the component side).
- Module keep-outs: Blue Pill and ADS1115 bodies over other parts (both modules sit high on sockets; only parts taller than 8 mm matter).
- Test points: `SENSE_P`, `ISNS_N`, `VREF`, `GATE`, `I_MON`, `FAULT_N` reachable with a probe from the copper side.

## Results

| Date | Layout | Gates | A | B | C | D | E | F | Total | Jumpers | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-28 | v0.3 Quilter 1.1 | fail G1, G2 | – | – | – | – | – | – | – | 111 vias | kept for hand finishing (superseded by v0.4) |
| 2026-10-28 | v0.3 Quilter 2.1–6.1 | fail G1 | – | – | – | – | – | – | – | 104–161 vias | rejected |
| 2026-11-11 | **v0.4 single-sided, route2 run "p1"** (placement seed 1, 26 negotiation rounds) | **pass** G1–G5 | 23 | 13 | 13 | 6 | 7 | 9 | **71** | 82 wires in 69 jumper footprints | **kept** as the v0.4 board |
| 2026-11-11 | v0.4 run "p2" (placement seed 2) | fail G1 (one GND pad) | – | – | – | – | – | – | – | 88 | rejected |

### Notes on the v0.4 board (p1)

- Gates: `hardware/fab/drc_summary.txt` (0 DRC errors with the CNC rules; `conncheck.py`: every net complete after counting the wire jumpers, no shorts). KiCad lists 82 unconnected items, one per wire jumper, because it cannot see the wires.
- Widths: cell loop 3.4–4 mm, `PGND` 2–4 mm, `CHG_OUT` 1.6 mm, `VIN`/`+12V`/`+12V_SW`/Peltier 1.6 mm.
- Jumpers on power nets: `+12V` ×5, `+12V_SW` ×3, `TEC_A`, `TEC_B`, `VIN` ×1 each (0.75 mm² wire, ≤ 3 A). None in the cell loop or `PGND`. Five `GND` jumpers tie fill islands together (A3 −2, B2 −2).
- **Weakest area, D (load loop compactness):** U301 is about 50 mm from R201, R312 (gate resistor) about 18 mm from Q301's gate, D301/D302 about 25 mm from `INN`. The loop is slow (about 1.6 kHz), so long traces matter less than in a fast design, but the gate trace can pick up MOSFET ringing. Bring-up step 4.5 checks it with a scope; if it rings, move R312 to Q301's gate leg (cut the track, solder R312 directly on the leg) and/or raise C304 to 2.2 nF.
- C1: the shunt sense pair does not run side by side for its whole length (`ISNS_G` 71 mm with 1 jumper, `ISNS_N` 26 mm with 2 jumpers). The ADS1115 reading is differential and filtered (R501/R502/C501), so the effect should be small; calibrate the current at bring-up.

