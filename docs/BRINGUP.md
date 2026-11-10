# Bring-up: testing the v0.4 board step by step

Nothing in v0.4 has been built yet. Do these steps in order and stop at the first one that fails. Use a current-limited supply for the first power-up if you can borrow one.

You need: a multimeter, the 30 V supply, a second small supply or a spare cell, and later a scope.

## 0. Before soldering

| # | Check | Expected |
|---|---|---|
| 0.1 | Lay each relay, the TO-247, the terminals and the Blue Pill sockets on a 1:1 print of the bottom copper (`hardware/fab/…-B_Cu.pdf`) | Every pin lands on its pad |
| 0.2 | K4 (SRD) with a multimeter: which pin pairs conduct at rest | Pad 1–4 conducts, 1–3 open |
| 0.3 | K3 (HK14FD): coil pins and the two changeover sets match the "4052" pinout on the footprint | A1/A2 coil, 11/21 common, 12/22 closed at rest |
| 0.4 | ADS1115 module header order | VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3 |
| 0.5 | After milling: continuity of every wide track, and no short between `PGND`, `GND`, `VIN`, `+12V`, `+5V`, `+3V3` | Open circuit between rails (GND–PGND too, until JP201 is fitted) |

## 1. Assembly order

1. The two SMD parts on the copper side: R201 (shunt) and U301 (OPA2171, pin 1 mark!).
2. Wire jumpers W1 … Wn (`hardware/fab/jumpers.csv`). Use insulated 0.6 mm solid wire. For the jumpers marked "power" use 0.75 mm² wire.
3. Resistors and diodes, then capacitors, transistors, IC sockets, terminals, relays.
4. Q301 last, with its heatsink already in place so the leads are not stressed.
5. Tin the wide tracks of the cell loop (`CELL_P`, `CELL_N`, `LOAD_P`, `LOAD_D`, the `PGND` strip along the bottom edge) and lay a 1.5 mm² copper wire in the solder. Milled 35 µm copper alone is not enough for 10 A.
6. Do **not** plug in the Blue Pill, the ADS1115 or the ICs yet.

## 2. Power rails (no ICs, no modules except the 12 V buck)

| # | Do | Expected |
|---|---|---|
| 2.1 | Set the 12 V buck module to 12.0 V on the bench first, then wire it to J102 | |
| 2.2 | Apply 30 V to J101 through the 5 A fuse | Supply current below 50 mA |
| 2.3 | Measure `+12V`, `+5V` | 12.0 V, 4.9–5.1 V |
| 2.4 | Measure `+12V_SW` | 0 V (K4 is off) |
| 2.5 | Measure VREF at U603 | 2.47–2.52 V |

## 3. Protection (ICs in, Blue Pill out)

Fit U601, U602, U401. Feed +3.3 V from a bench supply into the `+3V3` pin of the Blue Pill socket.

| # | Do | Expected |
|---|---|---|
| 3.1 | Measure `FAULT_N` | Low (tripped: no cell, NTCs open is fine) |
| 3.2 | Connect 10 kΩ resistors in place of the four NTCs and a 3.7 V source to J206 (+ to `SENSE_P`, − to `SENSE_N`) and also from J206 − to `GND` | |
| 3.3 | Touch `ARM` to +3.3 V for a moment | `FAULT_N` goes high, K4 clicks, `+12V_SW` = 12 V |
| 3.4 | Raise the J206 voltage slowly | Trips between 4.25 and 4.41 V and stays tripped when you go back down |
| 3.5 | Re-arm, lower the voltage | Trips near 1.96 V |
| 3.6 | Re-arm, replace the heatsink NTC resistor by 2.2 kΩ | Trips |
| 3.7 | Re-arm, pull the thermostat wire off J104 | K4 drops (no latch: it returns when reconnected) |

## 4. Load (U301 in)

| # | Do | Expected |
|---|---|---|
| 4.1 | `LOAD_OFF` open (pulled up) | Gate of Q301 = 0 V |
| 4.2 | Measure `I_MON` with no current | 1.68–1.74 V |
| 4.3 | Cell or a 4 V / 3 A supply on J205, arm, close K2 by tying `K2_EN` to +3.3 V, tie `LOAD_OFF` to GND | Still 0 A (PWM_L is 0 V) |
| 4.4 | Feed 0.3 V into `PWM_L` from a bench supply, raise slowly | Current starts near 0.14 V and rises about 0.36 A per 0.1 V |
| 4.5 | Scope on `I_MON` and on Q301's gate, toggle `LOAD_OFF` at 1 A and at 8 A | Clean edge, no ringing. If it rings: move R312 onto Q301's gate leg (the gate track is about 18 mm long on this layout), then raise C304 to 2.2 nF |
| 4.6 | Hold 5 A for 5 minutes | Heatsink warm, fans running when `FAN_PWM` is high, no trip |

## 5. Charger

| # | Do | Expected |
|---|---|---|
| 5.1 | Module alone on the bench: set its trimmer to **4.25 V** | |
| 5.2 | Measure the resistance from the module's FB pin to its ground | Note it; typical 300–400 Ω |
| 5.3 | Wire the module to J401 and the FB pin to J402 pin 1 | Output still 4.25 V with `PWM_C` at 0 V |
| 5.4 | Feed 0–3.3 V into `PWM_C` | Output falls smoothly to about 3 V. If the range is too small, lower R401 and R402 |
| 5.5 | With `PWM_I` open | U401 pin 1 is high and the module output is at its minimum |
| 5.6 | Cell at about 3.6 V, arm, set the output to the cell voltage, close K1, tie `PWM_I` to GND, raise the output | Current rises and stops near 5.6 A |

## 6. With the Blue Pill

1. Plug in the Blue Pill and the ADS1115. JP801 stays open. Connect USB.
2. Check I2C address 0x48 answers.
3. Calibrate: cell voltage against a DMM at two voltages; current against a DMM in series at 1 A and 5 A; `I_MON` zero.
4. Check each NTC reads room temperature.
5. Peltier: PWM 30 %, K3 relaxed. The cold plate must get colder. If it gets warmer, swap the two wires on J702.

## Limits to respect

- Cell loop: 10 A discharge, 5 A charge.
- Wire jumpers: no more than 3 A in any jumper (the layout keeps the cell loop free of them).
- Do not leave a cell in the holder for weeks with the bench off: the ADS1115 divider draws 0.2 mA.
