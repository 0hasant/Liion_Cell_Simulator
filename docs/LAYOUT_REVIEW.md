# Layout review checklist (cell test bench PCB)

Use this to judge any layout of the cell test bench board: a Quilter candidate, a hand edit, or a revision. It is written for this circuit's own nets and reference designators, so a check can be done by opening the board in KiCad and looking at the named parts.

Last updated: 2026-10-28. Quilter's limits and job settings are in `docs/QUILTER_NOTES.md`.

## How to use it

1. **Gates first.** A candidate that fails any gate is rejected or sent back for revision, whatever its score.
2. **Then score sections A to G** (100 points). Note every failed item with the part references, so the revision request can name them.
3. **Pick the highest score.** On a tie, pick the one with fewer vias and fewer top-layer tracks (easier to mill).
4. Write the result in the table at the end of this file and commit.

## Gates (must pass)

| # | Gate | How to check |
|---|---|---|
| G1 | 100 % routed, 0 unrouted nets | Quilter result page; KiCad DRC "unconnected items" = 0 |
| G2 | 0 DRC errors with our CNC rules (0.5 mm track, 0.4 mm clearance, 1 mm from edge) | KiCad DRC after setting Board Setup > Constraints to these values |
| G3 | Locked parts did not move: all J*, H101-H104, Q301 | Compare positions with `hardware/quilter_input/cell_test_bench.kicad_pcb` |
| G4 | Kelvin sense nets do not carry load current: ISNS_G, ISNS_N, SENSE_P, SENSE_N connect only at their sense pins (R201 pins 2/3, J206) and are not joined to any pour | Highlight each net in KiCad |
| G5 | No high-current net narrower than its rated width outside pads (see A1) | KiCad net inspector / measure |

## A. High-current paths (25 points)

The cell current loop is: J205.1 → F202 → CELL_P → K2 → LOAD_P → J301 (off-board 0.1 ohm) → LOAD_D → Q301 drain → Q301 source → GND → R201 force pin → CELL_N → J205.2. Charging: J401.3 → CHG_OUT → K1 → CELL_P → cell → CELL_N → R201 → GND → J401.2. Supply: J101 → VIN_RAW → F101 → VIN → J401.1 / J102.1.

- **A1 Width (10 pts).** For 1 oz outer copper and a 20 degC rise, IPC-2152 tables give roughly 2.8 mm for 10 A and 1.1 mm for 5 A. The 2 oz order halves that, but the CNC blank is usually 1 oz (35 µm), so design for 1 oz.
  - Cell loop and VIN: ≥ 3 mm or a pour.
  - CHG_OUT: ≥ 1.6 mm.
  - +12V_SW, TEC_A/B: ≥ 1.4 mm.
  - Quilter's own widths come from IPC-2221 and are wider still.
- **A2 Short loop (5 pts).** J205, F202, K1, K2, R201, Q301, J301 and J401 sit together near the bottom edge. The loop doesn't wander across the board.
- **A3 Copper on both sides (5 pts).** On a 2-layer result, the 10 A path is on both layers with several 0.9 mm vias in parallel. One via carries only a few amps.
- **A4 Q301 thermal (5 pts).** Nothing blocks the heatsink beyond the bottom edge. No other part within about 10 mm of Q301's tab side. NTC J503 lead route is free.

## B. Grounding (15 points)

GND carries the 10 A return (Q301 source, R201 force pin, J401.2) and is also the analog reference for U301, U501/U502 (ADS1115), U302/U401 (MCP4725) and the comparators. Analog Devices and TI both recommend one ground plane with power and analog areas kept apart, rather than cut planes. The return current then follows the shortest path and doesn't pass under the analog parts.

- **B1 (6 pts).** The 10 A GND return runs only between Q301 source, R201 and J401.2 / J101.2. The pour neck between that power corner and the analog area is where they meet, close to R201.
- **B2 (5 pts).** No analog ground pin (U301 pin 4, U501/U502 GND, U601/U602/U603, C301/C302, R306/R309) gets its ground through the 10 A path.
- **B3 (4 pts).** The ground return of the PWM/switching parts (Q702 fan driver, J701/J702 BTS7960, relay drivers Q201/Q202) doesn't pass under U301, U501 or U502.

The proper fix is a separate PGND net in the schematic, tied to GND at R201. That's an open item for the next schematic revision.

## C. Current and voltage sensing (20 points)

Rules from TI, Stackpole and Analog Devices shunt layout notes: take the sense lines from the shunt's sense pins (never from the current path), run the pair together, keep it away from noisy and high-current traces, and put the amplifier close to the shunt.

- **C1 (6 pts).** ISNS_G and ISNS_N leave R201 pins 3/2 as a tight pair, routed side by side to the U301 loop (ISNS_G: R302, R306, R312, C301; ISNS_N: R304, R309) and to ADS1115 #1 (R501, R502). No pour or power track runs between or under them.
- **C2 (5 pts).** U301 and its input network (R302-R306, R309-R312, C301) are within about 30 mm of R201.
- **C3 (5 pts).** SENSE_P/SENSE_N from J206 run as a pair to R503/R505 (ADC), R608/R610 (OV/UV dividers) and R510 (V_FAST). They don't run alongside CELL_P, LOAD_P or TEC lines.
- **C4 (4 pts).** The ADC filter parts sit at the ADC module: R501-R505, C501, C502 next to U501; C504-C506 next to U502.

## D. Load control loop stability (15 points)

The op-amp-plus-MOSFET current sink tends to oscillate. Forum builders and app notes agree: keep the gate drive short, put the gate resistor right at the gate (within about 6 mm), and keep the compensation parts at the op-amp.

- **D1 (6 pts).** GATE net: R307 within about 6 mm of Q301 pin 1; R308 (the other part on the GATE net) at the gate as well. OA_OUT from U301 pin 1 to R307 is short.
- **D2 (4 pts).** C302 (compensation) and R306 sit at U301 pins 1/2. The INN loop area is small.
- **D3 (3 pts).** Kill transistors Q302/Q303 and LOAD_OFF/FAULT lines are close to U301 pin 3 (INP).
- **D4 (2 pts).** Decoupling C304 (100 nF) at U301 pin 8, C305 (10 µF) close by.

## E. Protection, relays, MCU and thermal (10 points)

- **E1 (3 pts).** Flyback diodes D201/D202 directly across the K1/K2 coil pins. Relay coil traces (K1_COIL, K2_COIL, +12V_SW) don't run alongside the sense pairs.
- **E2 (3 pts).** The comparators U601/U602 and the TL431 U603 sit together, with C601-C603 at their supply pins. VREF stays short.
- **E3 (2 pts).** I2C (SCL/SDA) runs as a pair from J801 to U302, U401, U501, U502, with pull-ups R801/R802 near J801.
- **E4 (2 pts).** Fan PWM (FAN_PWM → R703 → Q702) and TEC_RPWM/LPWM stay near the top edge, away from the analog block.

## F. CNC manufacturability (15 points)

Fab-lab tests with V-bits and 1/64" mills put the reliable limits at about 0.4 mm track and clearance (0.5-0.6 mm safer), pads at least 0.5 mm larger than the hole, and copper at least 1 mm from the edge. Fewer layers and fewer vias make milling far easier.

- **F1 (5 pts).** Vias: fewer is better. Each via is a hand-soldered wire. Score 5 at ≤ 20, 3 at ≤ 40, 1 at ≤ 80, 0 above.
- **F2 (5 pts).** Top-layer copper: the fewer and shorter the top tracks, the easier a single-sided conversion. Score 5 if top copper is only short hops (≤ 15 tracks), 3 at ≤ 40, 0 above.
- **F3 (3 pts).** No track passes between pins of DIP-14/DIP-8 (U601, U602), pin headers or the relay pads. With 0.5/0.4 mm rules it shouldn't fit, but check.
- **F4 (2 pts).** Pours have no slivers narrower than 0.5 mm and no isolated copper islands (they lift off when milled).

## G. Cleanup needed afterwards (not scored, list it)

- Silkscreen overlaps (Quilter doesn't place silkscreen).
- Module keep-outs: Blue Pill, ADS1115 and MCP4725 bodies over other parts.
- Test points: SENSE, ISNS, VREF, GATE, I_MON, FAULT_N reachable with a probe.

## Results

| Date | Job / candidate | Gates | A | B | C | D | E | F | Total | Vias | Top tracks | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-28 | v0.3 job, 1.1 | fail G1 (92.3 %), G2 | – | – | – | – | – | – | – | 111 | – | **keep for hand finishing** (all parts on top, fewest vias of the top-only candidates) |
| 2026-10-28 | v0.3 job, 6.1 | fail G1 (93.7 %), G2 | – | – | – | – | – | – | – | 133 | – | runner-up: best routing but parts on both sides |
| 2026-10-28 | v0.3 job, 2.1 / 3.1 / 4.1 / 5.1 | fail G1 (89.9-92.0 %) | – | – | – | – | – | – | – | 104-161 | – | rejected |

## Sources

- TI LMP8640 datasheet, layout section (Kelvin connection away from the high-current path): https://www.ti.com/document-viewer/LMP8640/datasheet/layout
- Stackpole, shunt resistor PCB layout note: https://stackpole-europe-website.pages.dev/guide-shunt-layout
- Analog Devices, improving pad layout of low-value shunt resistors: https://www.analog.com/en/resources/analog-dialogue/articles/optimize-high-current-sensing-accuracy.html
- Analog Devices, mixed-signal PCB grounding: https://www.analog.com/en/resources/technical-articles/successful-pcb-grounding-with-mixedsignal-chips--follow-the-path-of-least-impedance.html
- TI SLYT512, grounding in mixed-signal systems: https://ti.com/lit/pdf/SLYT512
- AtlasPCB, IPC-2152 trace width table: https://atlaspcb.com/blog/pcb-trace-width-current-capacity
- Altium, relay flyback diode placement: https://resources.altium.com/p/why-you-should-use-a-flyback-diode-in-a-relay-to-prevent-electrical-noise-in-your-circuits
- Maker Pro forum, electronic load gate resistor placement: https://makerv2.webteractive.co/forums/goto/post?id=1790330
- Fab Academy, in-house PCB milling design rules: https://fabacademy.org/2026/labs/winam/group_assignment/week8/ and https://fabacademy.org/2025/labs/nellai/assets/assignments/electronicd_production.html
- EEVblog Dynamic Electronic Load project (public KiCad electronic-load design): https://eevblog.com/forum/projects/dynamic-electronic-load-project/125
- Quilter documentation: https://docs.quilter.ai
