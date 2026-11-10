# Cell test bench: schematic guide (v0.4)

**Author:** Claude, for Hasan Turan · **Date:** 2026-11-10 · **Schematic:** `hardware/kicad/` (8 sheets)

This guide explains the schematic block by block. Every number is computed from the part values in `hardware/tools/design.py`, which generates the KiCad files. What changed since v0.3 and why is in `docs/CHANGES_v0.4.md`. How to test the built board is in `docs/BRINGUP.md`.

> The v0.3 figures were removed because they no longer match. Nothing here has been built or simulated yet: treat every number as a design value to confirm on the bench.

## 0. How to read the KiCad schematic

- Parts are placed in a grid and joined by **net labels**, not wires. Two pins are connected when they carry the same label.
- **Reference numbers tell you the sheet:** 1xx Power, 2xx Cell/Relays, 3xx Load, 4xx Charger, 5xx Measurement, 6xx Protection, 7xx Thermal, 8xx MCU.
- The Blue Pill and the ADS1115 are bought modules that plug into sockets. Their symbols are connectors whose value lists the module pins.
- There are **two grounds**. `PGND` carries the power return currents (PSU, buck modules, load MOSFET, Peltier). `GND` is the quiet reference for the op-amps, comparators and the MCU. They are joined at one point only: wire link **JP201**, next to the shunt.

**The bench in one paragraph.** A 30 V supply feeds a 12 V buck module and the XL4016 charger module. The cell connects through an inline 15 A fuse to node `CELL_P`. Relay K1 connects the charger, relay K2 connects the electronic load, never both. All cell current returns through one 10 mΩ shunt (R201). A Blue Pill sets the load current, the charger voltage and the charger current limit with three filtered PWM outputs, reads current and voltage through an ADS1115, and drives the Peltiers. Six comparators watch voltage, current and temperature. Any trip is latched and drops safety relay K4, which removes the 12 V that every other relay and the Peltier need.

## 1. Power (1xx)

| Rail | Made by | Feeds |
|---|---|---|
| `VIN` (30 V) | J101, through an inline 5 A fuse | 12 V buck (J102), charger module (J401) |
| `+12V` | XL4016 buck module on J102 | K4, fans, 7805, op-amp supply `+12VA` (through R319) |
| `+12V_SW` | `+12V` through the contact of K4 | coils of K1, K2, K3 and the Peltiers |
| `+5V` | U101 (L7805CV) | comparators, TL431, pull-ups for K4 driver and `LOAD_OFF` |
| `+3V3` | the Blue Pill's own regulator (from USB) | ADS1115, NTC dividers, `FAULT_N` pull-up |

- **D101 (P6KE39CA)** clamps spikes on `VIN`. **D102 (1N5408)** conducts if the PSU is connected backwards, and the inline fuse blows.
- **Safety switch K4** (SRD-12VDC-SL-C). Its coil is fed through the thermostat on J104 (60 °C, normally closed, on the load heatsink) and switched by Q101. Q101 conducts only while comparator U602D lets `SW_B` float high, which it does only while `FAULT_N` is high. So `+12V_SW` disappears on any fault, when the heatsink overheats, when the 5 V rail is missing, and when the Blue Pill has no USB power. It works like the door switch of a microwave oven: the dangerous parts get no power unless everything is in order.
- R101/R102/R103 make sure Q101 is fully off even when the comparator output is at its worst-case low level (0.4 V becomes 0.27 V at the base).

**Check:** thermostat type is normally closed; K4 pin 3 is the normally-open contact (measure with a multimeter before soldering: pins 1–4 conduct at rest, 1–3 do not).

## 2. Cell connection, shunt and relays (2xx)

- **R201, 10 mΩ, 2512.** It sits in the cell's negative lead, so it sees charge and discharge. 10 A gives 100 mV. Pads 1 and 4 carry the current. Pads 2 and 3 are two short copper stubs that leave the inner corners of those pads: the **Kelvin taps** `ISNS_N` and `ISNS_G`. Measuring there keeps the solder joints and the copper out of the reading, the same idea as the four-wire ohm range of a bench multimeter.
- During discharge `ISNS_N` is below `ISNS_G` (negative). During charge it is above.
- **K1 and K2** (Panasonic ALFG2PF121, 33 A) are normally open. Their coils hang on `+12V_SW`.
- **Drivers.** `K1_EN` → R202 (1 kΩ) → base of Q201 (BC337), which pulls the coil low. R203 keeps the relay off while the MCU boots. D201 catches the coil's turn-off spike.
- **Interlock.** Q203 has its base on `K2_EN` and shorts Q201's base, so K1 cannot close while K2 is commanded. Q204 does the mirror image. Both commanded means both off.

**Check:** Kelvin wires on J206 go to the cell tabs separately from the power contacts.

## 3. Electronic load (3xx)

It draws a programmable constant current from the cell. The energy becomes heat in Q301 (IRFP260N) and in the external 0.1 Ω 50 W resistor, both on the load heatsink.

Think of a cruise control:

1. **Target.** PWM from PA6 is smoothed by R301/C301 and R302/C302 and divided by R303/R304: `SETP = duty × 3.3 V / 27.8`, 0 to 119 mV.
2. **Compare.** R305 and R306 average `SETP` and the shunt voltage: `INP = (SETP − I × 10 mΩ) / 2`.
3. **Correct.** U301A (with R307, C304) is an integrator. While `INP` is above `INN` it raises the gate, the current rises and `INP` falls. It settles at `INP = INN`.
4. **Result.** `I = (SETP − 2 × INN) / 10 mΩ`. R308 biases `INN` to +2.5 mV, so the first 4 % of PWM gives no current. That dead band guarantees zero current at PWM = 0 whatever the op-amp offset is. Full scale is about 11.3 A. The firmware trims the PWM until the ADS1115 reads the wanted current.

- R312 (100 Ω) isolates the op-amp from the MOSFET gate capacitance. R313 holds the gate low when the op-amp has no supply.
- **Load off.** `LOAD_OFF` is pulled to +5 V by R310. Through R309 and D301 it lifts `INN` to about 0.4 V, far above any `INP`, so the op-amp output sits at 0 V. The MCU pulls PB14 low (open drain) to enable the load. No MCU means load off.
- **Fault.** When K4 drops, the low side of its coil (`K4_COIL`) rises to 12 V and lifts `INN` through R311/D302. The load current stops within microseconds, before K2 opens.
- **Loop speed.** The loop gain crosses unity near 1.6 kHz at 10 A, so a current step settles in well under 1 ms. For a pulse test, preset the PWM and switch with `LOAD_OFF`.

**Current monitor (U301B).** `I_MON = 1.71 V + 0.12 V/A`, discharge positive. The offset comes from VREF (R316/R317), the gain from R314/R315 (12×). R318 with D303/D304 clamps the signal to the MCU's 0–3.3 V range. It feeds PA0, the two over-current comparators and the charger current limit.

**Check:** heatsink size for 40 W in Q301; a scope on the shunt during a current step (no ringing).

## 4. Charger (4xx)

The XL4016 module regulates its output so that its FB pin sits at 1.25 V. The board pushes extra current into FB, which makes the module lower its output. Two sources push:

- **Voltage (CV).** PWM from PA7 → R401/C401 → R402/C402 → D401 → FB. PWM = 0 means no push, and the output equals the trimmer setting. **Set the trimmer to 4.25 V before connecting the FB wire.** That is the hardware ceiling: nothing on the board can raise it.
- **Current (CC).** U401A compares `I_MON` with `ILIM`. If the charge current is above the limit, its output rises and pushes into FB through R405/D402 until the current is back at the limit. R404/C403 make it a slow integrator (about 50 Hz) so it does not fight the module's own loop.
- **ILIM** is PWM from PB0 through R406, with R407 to +3.3 V. Pin high-Z (reset) gives 3.3 V, which means "no current allowed". PWM 0 % allows 5.6 A, 30 % allows 0 A.

Charging sequence for the firmware: load off → set CV so the module output equals the measured cell voltage → set ILIM → close K1 → raise CV to 4.20 V. The current limit holds the CC phase by itself. Stop at C/20 and open K1.

**U401B** buffers `SENSE_P` into `V_CELL`. The protection dividers and `V_FAST` hang on the buffer, not on the cell. R409 makes an empty holder read 0 V.

**Check:** measure the module's FB divider and confirm that PWM 0–100 % moves the output from 4.25 V down to about 3 V. If not, change R401/R402.

## 5. Measurement (5xx)

- **ADS1115 (0x48).** A0−A1: shunt, ±256 mV range, about 0.8 mA per bit. A2−A3: cell voltage between the Kelvin wires, halved by R503/R504 to fit ±2.048 V. With 1 % resistors, calibrate once against a DMM.
- **NTCs.** Four 10 kΩ NTCs with 10 kΩ pull-ups to +3.3 V go to PA2–PA5: cell surface, pocket air, load heatsink, Peltier hot side. `T = 1 / (1/298.15 + ln(R/10k)/B)` with `R = 10k × V / (3.3 − V)`. The TTC05103 parts have B ≈ 4050 K.
- **V_FAST** is `V_CELL / 2` on PA1 for the fast voltage step at a current edge, which gives R0 of the 2RC model. It is measured against ground, so subtract `I × 10 mΩ`.

Why two voltage paths: R0 comes from the jump in the first milliseconds (fast MCU ADC), R1/C1 and R2/C2 from the slow relaxation over seconds to minutes (precise ADS1115).

## 6. Protection (6xx)

U603 (TL431) makes **VREF = 2.495 V**. Its capacitor C601 must be 10 µF: a TL431 can oscillate with values between about 10 nF and 3 µF.

| Trip | Signal | Trips when | Value |
|---|---|---|---|
| Over-voltage (U601A) | `V_CELL × 15k/26k` | above VREF | cell > **4.33 V** |
| Under-voltage (U601B) | `V_CELL × 16k/25.1k` | below VREF/2 | cell < **1.96 V** |
| Discharge over-current (U601C) | `I_MON × 100k/124k` | above VREF | I > about **11.6 A** |
| Charge over-current (U601D) | `I_MON` | below 0.96 V | I > about **6.2 A** charging |
| Heatsink over-temperature (U602A) | `NTC_HS` | below 0.63 V | about **61 °C** |
| Cell over-temperature (U602B) | `NTC_CELL` | below 0.63 V | about **61 °C** |

All outputs are open-collector on one line, `FAULT_N` (pulled up to +3.3 V by R616). Any comparator can pull it low.

- **Latch (U602C).** Its input `LATCH_IN` follows `FAULT_N` through R614, delayed by C604 (1 ms). Once `LATCH_IN` falls below 1.25 V the comparator holds `FAULT_N` low itself. To re-arm, the MCU drives `ARM` (PB10) high for a few milliseconds, then returns it to high-Z. Driving `ARM` low forces a trip.
- **Power-up state is tripped**, because `LATCH_IN` starts at 0 V. The firmware has to arm the bench on purpose.
- **U602D** turns `FAULT_N` into `SW_B` for the K4 driver.
- Voltage trips are measured against ground, not against `SENSE_N`. At 5 A charge the shunt lifts the cell by 50 mV, so OV acts at about 4.28 V. At 10 A discharge UV acts at about 2.06 V.
- With 1 % parts the OV point can sit between about 4.25 V and 4.41 V. The charger's 4.25 V ceiling is the first line of defence.
- No cell in the holder reads 0 V and trips UV, so the bench cannot be armed without a cell.

## 7. Thermal (7xx)

- **Peltiers.** Two TEC1-12706 in series on J702 (about 6 V and 3 A each). Q703 (IRLZ44N) switches them to `PGND` with PWM from PB8. D702 catches wiring inductance.
- **K3** swaps the polarity. Relaxed: current flows from A to B (wire it so this cools the pocket). Energised by `TEC_DIR` (PB9): reversed, the pocket is heated. Set the PWM to 0 before toggling K3.
- Peltier and K3 are fed from `+12V_SW`, so every fault switches them off.
- **Fans.** Q702 (BC337) switches the two cooler fans (J704, J706) with PWM from PA8. J705 is the 12 V pocket mixing fan, always on.

## 8. MCU (8xx)

| Pin | Net | Use |
|---|---|---|
| PA0 / PA1 | I_MON / V_FAST | ADC: fast current, fast cell voltage ÷ 2 |
| PA2–PA5 | NTC_CELL, NTC_AIR, NTC_HS, NTC_TEC | ADC |
| PA6 / PA7 / PB0 | PWM_L / PWM_C / PWM_I | TIM3 CH1–CH3: load setpoint, charger voltage, charger current limit |
| PA8 | FAN_PWM | TIM1 CH1 |
| PA9 / PA10 | DBG_TX / DBG_RX | debug UART (J803) |
| PB6 / PB7 | SCL / SDA | I2C1, ADS1115 at 0x48 |
| PB8 / PB9 | TEC_PWM / TEC_DIR | TIM4 CH3, GPIO |
| PB10 | ARM | high-Z normally; high = re-arm, low = force trip |
| PB12 / PB13 | K1_EN / K2_EN | charger relay / load relay |
| PB14 | LOAD_OFF | open drain with 5 V pull-up; low = load on |
| PB15 | FAULT_N | input: low = tripped |

- **JP801** is normally open. The Blue Pill's 5 V pin is wired straight to USB VBUS, so the board must not feed it while a PC is plugged in. Close JP801 only to run the Blue Pill without USB.
- A PWM "DAC" needs a steady 3.3 V. Use 14 bits at 4.4 kHz on TIM3: the ripple after the filters is below 1 mA of load current.

## 9. What the hardware does on its own

1. **Power on:** tripped. K4 off, all relays open, load off, Peltier off, charger limited to 0 A.
2. **Firmware arms** (ARM high for 5 ms) only when a cell is present and all readings are sane.
3. **Any trip:** `FAULT_N` low → load current to zero at once → K4 opens in about 10 ms → K1, K2, K3 and the Peltier lose power. It stays that way until re-armed.
4. **USB unplugged or firmware frozen with ARM high-Z:** a frozen firmware cannot clear a trip, and without +3.3 V the bench is tripped.

## 10. References

- TI, *Voltage-to-current (V-I) converter circuit with MOSFET*, SBOA327: https://www.ti.com/lit/pdf/sboa327
- TI, *Low-side, bidirectional current sensing circuit*, SBOA223: https://www.ti.com/lit/pdf/SBOA223
- TI, *How to Dynamically Adjust Power Module Output Voltage*, SLVA861: https://www.ti.com/lit/pdf/slva861
- XLSemi XL4016 datasheet (FB = 1.25 V): https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/XL4016E1_C55881.pdf
- TI datasheets: ADS1115 https://www.ti.com/lit/ds/symlink/ads1115.pdf · OPA2171 https://www.ti.com/lit/ds/symlink/opa2171.pdf · TL431 https://www.ti.com/lit/ds/symlink/tl431.pdf · LM339 https://www.ti.com/lit/ds/symlink/lm339.pdf · LM358 https://www.ti.com/lit/ds/symlink/lm358.pdf
- Isabellenhütte CMS shunt datasheet (Direnc copy): https://pdf.direnc.net/upload/10mr-2515-sont-direnc-cms-datasheet.pdf
- stm32-base.org, Blue Pill: https://stm32-base.org/boards/STM32F103C8T6-Blue-Pill
- Battery University, BU-409 *Charging Lithium-ion*: https://batteryuniversity.com/article/bu-409-charging-lithium-ion
