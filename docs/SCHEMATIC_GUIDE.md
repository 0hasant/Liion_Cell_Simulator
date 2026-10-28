# Cell test bench: schematic guide (v0.3)

**Author:** Claude, for Hasan Turan · **Date:** 2026-10-29 · **Schematic:** `hardware/kicad/` (8 sheets, about 130 parts)

This guide explains the schematic block by block, so you can check it against your own understanding and the public references. Every number here is computed from the actual part values in the KiCad files. The checklist that goes with it is `docs/SCHEMATIC_REVIEW.md`: every item there has an ID (for example **L-03**) that this guide refers to.

> **Where the design came from.** I generated the schematic with `hardware/tools/design.py`; it was not copied from a single reference design. Each block uses a standard, textbook topology. For every block, section "Cross-check with" names the closest public reference that uses the same circuit, so you can compare the two side by side. Treat this design as unverified until you have checked it.

---

## 0. How to read the KiCad schematic

The KiCad sheets are hard to read, and that's a property of how they were drawn:

- **Parts are placed in a grid and joined by net labels, not by wires.** Two pins are connected when they carry the same label text (for example `ISNS_G`). Labels that start with `/Sheet/` are local to one sheet; the others (`GND`, `+3V3`, `FAULT`, `I_MON` …) are global.
- **Reference numbers tell you the sheet:** 1xx Power, 2xx Cell/Relays, 3xx Load, 4xx Charger, 5xx Measurement, 6xx Protection, 7xx Thermal, 8xx MCU. So R307 is resistor 7 on the Load sheet.
- **Modules are drawn as connectors.** The Blue Pill, ADS1115, MCP4725 and BTS7960 are bought modules that plug into pin sockets. Their symbols are connectors whose pin names list the module pins (for example "VCC GND SCL SDA A0 OUT").
- **Each sheet has short notes at the bottom.** v0.3 adds a "How it works / Check" note to every sheet that points back to this guide.

The figures in this guide redraw each block as a normal circuit diagram. They show the same connections as the KiCad files, only arranged so you can follow the signal.

![System block diagram](schematic_guide/00_system.svg)

**The whole bench in one paragraph.** A 30 V bench supply feeds two buck modules (12 V and 5 V) and the XL4016 charger module. The cell sits in the thermal pocket and is connected through a 15 A fuse to a common node (`CELL_P`). Two power relays decide what the cell sees: K1 connects the charger, K2 connects the electronic load. All cell current, in either direction, returns through one 10 mΩ shunt (R201). Its voltage is read three ways: by the load's op-amp (to regulate discharge current), by an ADS1115 (precise reading), and by a fast monitor for the MCU and the protection comparators. A Blue Pill (STM32F103) sets the load current and charger voltage through two I2C DACs, reads everything through two ADS1115s, switches the relays, and drives the Peltiers through a BTS7960 H-bridge. A set of comparators trips a hardware `FAULT` that turns everything off, even if the firmware hangs.

---

## 1. Power (sheet `power.kicad_sch`, parts 1xx)

![Power](schematic_guide/01_power.svg)

**What it does.** It takes the 30 V / 10 A bench supply in through J101 and makes the rails:

| Rail | Made by | Feeds |
|---|---|---|
| `VIN` (30 V) | J101 → F101 10 A fuse | J102 (12 V buck), J401 (charger) |
| `+12V` | XL4016 buck module on J102 | U301 op-amp, fans, J103 |
| `+12V_SW` | `+12V` through the KSD9700 60 °C thermostat (J104) | relay coils K1/K2, BTS7960 B+ |
| `+5V` | MP1584 buck module on J103 | comparators U601/U602, TL431 bias, BTS7960 logic, pocket fan, Blue Pill (through D801) |
| `+3V3` | the Blue Pill's own regulator | ADS1115 ×2, MCP4725 ×2, NTC dividers, pull-ups |

**How it works.** These are ordinary buck converters, the same kind as in a car USB charger, just bigger. The **thermostat** is a bimetal disc switch, like the one in a kettle. It sits on the load heatsink and opens at 60 °C, which removes power from both relay coils and the Peltier driver without asking the firmware. Relays open when their coils lose power, so the cell is disconnected.

**D101 (P6KE33A TVS)** clamps spikes on `VIN`. It also gives reverse-polarity protection: if the PSU is connected backwards, D101 conducts and F101 blows.

**Cross-check with:**
- XL4016 datasheet: typical application, FB = 1.25 V.
- MP1584 module listing.
- Vishay P6KE series datasheet: check the stand-off voltage (V_RWM).

**Things to check:** P-01 to P-05. The most important is **P-01**: the P6KE33A's stand-off voltage is 28.2 V, which is below your 30 V supply.

---

## 2. Cell connection, shunt and relays (sheet `relays.kicad_sch`, parts 2xx)

![Cell path](schematic_guide/02_cellpath.svg)

**What it does.** It connects the cell to either the charger or the load, never both, and measures the current in both directions.

**How it works.**
- **The shunt R201 (10 mΩ, 4-terminal)** sits in the cell's negative lead. A shunt is a precise, very small resistor: 10 A through 10 mΩ gives 100 mV. It has **4 terminals**, two thick ones for the current (pins 1 and 4) and two thin ones for measuring (pins 2 and 3). Measuring on separate pins keeps the solder-joint and copper resistance out of the reading. That's the "Kelvin" or 4-wire method, the same idea a good multimeter uses for low-ohm measurements.
- Because the shunt is in the negative lead, it sees **both** charge and discharge. The sign tells you which: during discharge `ISNS_N` is below `ISNS_G` (negative), and during charge it is above.
- **GND is defined at R201 pin 4.** All the measurement circuits reference `ISNS_G` (pin 3) rather than "some GND", so the load current flowing in the ground copper doesn't add errors.
- **F202 (15 A)** protects against a short at the cell connector. The hardware over-current trip happens first, at about 11 A.
- **K1 and K2 (Panasonic ALFG2PF121, 33 A, 12 V coil)** are normally open, so with no power the cell is isolated.

![Relay driver](schematic_guide/02b_relaydriver.svg)

**Relay driver.** The MCU drives `K1_EN` high. R202 passes it to the gate of Q201 (BS170), which turns on and pulls the coil low, and the relay closes. D201 catches the coil's voltage spike at turn-off: a coil is an inductor and fights a sudden change of current. R203 and R204 (100k) keep the gate low while the MCU boots, so the relays stay open.

**Interlock and fault drop-out.** Q203 has its gate on `K2_EN`. When the MCU asks for the load relay, Q203 shorts K1's gate, so **K1 and K2 can never be on together**, even if the firmware has a bug. Q205 does the same on `FAULT`. K2's side is the mirror image (Q202, Q204, Q206).

**Cross-check with:**
- Panasonic LF-G (ALFG) datasheet: coil 12 V, 117 mA, 103 Ω, 1.4 W, contact 33 A.
- Altium's article on relay flyback diodes (layout).
- BS170 datasheet (onsemi): check that V_GS = 3.3 V turns it on hard enough for 117 mA (**R-02**).

**Things to check:** R-01 to R-07.

---

## 3. Electronic load (sheet `load.kicad_sch`, parts 3xx)

![Load control loop](schematic_guide/03_load.svg)

**What it does.** It draws a programmable constant current, 0 to 10.8 A, from the cell. It's a "dummy load": the energy becomes heat in the MOSFET Q301 and the 0.1 Ω 50 W resistor on the heatsink.

**How it works**, like a cruise control:
- The DAC (U302, MCP4725) sets the target. R301 and R302 shrink it to 0–108 mV, the same size as the shunt voltage at full current: `SETP = DAC × 1k / 30.4k`.
- R303 and R304 average `SETP` and the shunt voltage `ISNS_N`, giving `INP`. During discharge `ISNS_N` is negative, so `INP = (SETP − I·R_shunt)/2`.
- The op-amp U301A compares `INP` with `ISNS_G` (≈ 0 V). R306 and C302 make it an **integrator**: if `INP` is above zero it slowly raises the gate, more current flows, and `INP` falls. It settles exactly where `INP = 0`, i.e. **I = SETP / 10 mΩ**.
- **Numbers:** DAC 3.3 V → `SETP` 108.6 mV → **10.86 A**. One DAC step (12-bit) is about 2.65 mA.
- R307 (100 Ω) between the op-amp and the gate keeps the op-amp stable while driving the MOSFET's large gate capacitance. R308 holds the gate low if the op-amp is unpowered.
- **Kill switches:** Q302 (`LOAD_OFF`, held high by R305 so the load starts OFF) and Q303 (`FAULT`) short `INP` to ground, so the op-amp pulls the gate down and the current stops.

**Why the 0.1 Ω resistor is in series.** At 10 A it drops 1 V and takes 10 W of the heat, so the MOSFET dissipates less. The cost is that the load can't hold 10 A when the cell is below about 1.2 V. Your cutoff is 2.0 V, so that's fine.

![Current monitor](schematic_guide/04_imon.svg)

**Fast current monitor (U301B).** The second half of the op-amp turns the small shunt voltage into a 0–3.3 V signal for the MCU's fast ADC (PA0) and the over-current comparators. R311 and R312 make an offset of 0.127 V, and the amplifier gain is 13 / −12, so **`I_MON` = 1.65 V + 0.12 V per amp**. 1.65 V means zero current. It goes up for discharge and down for charge, covering about ±13.7 A. D301 and D302 clamp it so it can never exceed the MCU's 0–3.3 V.

**Cross-check with:**
- TI *Voltage-to-current (V-I) converter circuit with MOSFET* (SBOA327 / CIRCUIT060014): the same low-side op-amp + MOSFET + shunt idea, including the gate resistor and compensation capacitor. Ours differs in two ways: the feedback goes to the + input through the R303/R304 summing pair, and the op-amp is wired as an integrator.
- TI *Low-side bidirectional current-sensing circuit* (SBOA223 / TIPD175): the same idea as U301B, i.e. an offset reference plus a gain stage to read ± current on a single supply.
- EEVblog "Dynamic Electronic Load" project: the public DIY electronic load and its discussion of MOSFET linear-mode stability.
- IRFP260N datasheet (Infineon): check the DC safe operating area for about 30 W at 3–4 V drain-source (**L-05**).
- OPA2188 datasheet (TI): input range down to V− − 0.1 V and rail-to-rail output. Check that the output can drive the gate high enough from a 12 V supply (**L-02**).

**Things to check:** L-01 to L-09.

---

## 4. Charger (sheet `charger.kicad_sch`, parts 4xx)

![Charger](schematic_guide/05_charger.svg)

**What it does.** It charges the cell from the XL4016 CC/CV buck module, with the output voltage set by the MCU.

**How it works.** The XL4016 chip adjusts its output so that its FB pin sits at 1.25 V. Normally a resistor divider (with the module's pot) sets that. Here we **push a small extra current into FB** from the second DAC (U401) through R401 and D401. The chip sees FB too high and lowers its output. So:
- **DAC = 0 V:** D401 blocks, nothing is injected, and the output equals the pot setting. Set the pot to **4.25 V** before connecting the FB wire. That is the hardware ceiling: the DAC can only make the voltage lower, never higher. If the MCU dies, the worst case is 4.25 V.
- **DAC higher:** more current is injected and the output goes lower. With a typical module divider (R_bottom ≈ 360 Ω, R_top ≈ 860 Ω), DAC 3.3 V gives about 3.0 V. **The module's resistor values are a guess: measure yours (C-02).**
- R402 and C401 filter the DAC.

**Important limitation (C-01).** The module's own current limit is bypassed, because its IN− and OUT− are both tied to our GND. **Nothing in hardware limits the charge current except the 6.4 A over-current trip.** If K1 closes while the module output is at 4.25 V and the cell is at 3.0 V, a large current will flow until the comparator trips. The firmware therefore has to:
1. Set the DAC so the module output equals the measured cell voltage.
2. Close K1.
3. Slowly lower the DAC to raise the current to the target (CC phase).
4. Hold 4.20 V (CV phase).
5. Stop at C/20.

This works, but it is the weakest part of the design. You should decide whether you accept it.

**Cross-check with:**
- TI SLVA861 *How to Dynamically Adjust Power Module Output Voltage* and TI SNVAA33 ("feedback current injection network"): the same FB current-injection method used here.
- Maxim/ADI app notes 4498 / 4149 (DS4402/4404 margining a DC-DC converter through FB): the same idea with a current DAC.
- XL4016 datasheet: FB = 1.25 V, FB absolute max.
- A mikrocontroller.net thread on driving the XL4016 FB from a DAC, with the same 360 Ω bottom resistor on common modules.
- Battery University BU-409, *Charging Lithium-ion*: the CC/CV profile and the C/20 end condition the firmware must follow.

**Things to check:** C-01 to C-06.

---

## 5. Measurement (sheet `measurement.kicad_sch`, parts 5xx)

![Measurement](schematic_guide/06_measure.svg)

**What it does.** It makes the precise measurements used for the 2RC model fit.

**U501, ADS1115 #1 (address 0x48):**
- **A0−A1, shunt current.** Differential input through R501/R502 (100 Ω) with C501 (100 nF) as a small RC filter. On the ±256 mV range one bit is about 7.8 µV, i.e. **≈ 0.8 mA per bit**.
- **A2−A3, cell voltage.** Read directly between the Kelvin sense wires `SENSE_P`/`SENSE_N`, so cable and contact drops are excluded. R503/R504 halve it (4.2 V → 2.09 V) to fit the ±2.048 V range. These two resistors set the voltage accuracy: they must be **0.1 %**, or you calibrate against a good DMM (M-02).

**U502, ADS1115 #2 (address 0x49):** four NTCs (cell surface, pocket air, load heatsink, Peltier hot side). Each is a 10k pull-up to 3V3 with the 10k B3950 NTC to ground and a 100 nF filter. The voltage falls as temperature rises. R_NTC = 10k × V / (3.3 − V), then T from the B-equation.

**V_FAST** (R510/R511, C507) is the cell voltage ÷ 2 into the Blue Pill's internal ADC on PA1. It is fast (µs-scale), so it captures the instant voltage step when a current pulse starts, which gives R0 in the 2RC model. It is referenced to GND, not `SENSE_N`, so the firmware subtracts I × R_shunt.

**Why this matters for the 2RC model.** R0 comes from the instant voltage jump; R1/C1 and R2/C2 come from the slow relaxation over seconds to minutes. The ADS1115 (≤ 860 samples/s) gives the precision for the slow part, and V_FAST plus I_MON give the speed for the fast part.

**Cross-check with:**
- TI ADS1115 datasheet: input range GND − 0.3 V to VDD + 0.3 V, PGA ranges, data rates, and input filter recommendations.
- Any NTC B-parameter / Steinhart–Hart note, plus your NTC's datasheet for B3950.
- Stackpole / TI shunt layout notes (already in `docs/LAYOUT_REVIEW.md`).

**Things to check:** M-01 to M-06.

---

## 6. Protection (sheet `protection.kicad_sch`, parts 6xx)

![Protection](schematic_guide/07_protection.svg)

**What it does.** It trips a hardware fault that doesn't depend on the firmware.

**How it works.** U603 (TL431) makes an accurate **2.50 V reference**. Six comparators each compare a scaled signal with it (or with a divided copy of it). Their open-collector outputs are all tied to `FAULT_N` (a "wired-OR"): any one of them can pull it low. Q601 inverts `FAULT_N` into `FAULT` (active high), which kills the load (Q303), drops both relays (Q205/Q206) and disables the Peltier driver (Q701). The MCU reads `FAULT_N` on PB15 and can also pull it low itself to force a safe stop.

| Trip | Signal | Threshold | Computed trip point |
|---|---|---|---|
| Over-voltage (U601, pins 4/5) | `OV_DIV` = SENSE_P × 10k/17.15k | > 2.50 V | cell > **4.29 V** |
| Under-voltage (U601, pins 6/7) | `UV_DIV` = SENSE_P × 10k/15.6k | < 1.25 V (`VREF_H`) | cell < **1.95 V** |
| Discharge over-current (U601, pins 10/11) | `ID_DIV` = I_MON × 100k/120k | > 2.50 V | I > **+11.25 A** |
| Charge over-current (U601, pins 8/9) | `I_MON` | < 0.884 V (`VREF_C`) | I < **−6.39 A** |
| Heatsink over-temperature (U602, pins 2/3) | `NTC_HS` | < 0.630 V (`VREF_T`) | NTC < 2.36 kΩ ≈ **61.5 °C** |
| Cell over-temperature (U602, pins 5/6) | `NTC_CELL` | < 0.630 V | ≈ **61.5 °C** |

**Cross-check with:**
- TI TL431 datasheet ("shunt regulator" use with REF tied to cathode = 2.495 V).
- TI LM339 / LM393 datasheets: open-collector outputs that can be wired together, input common-mode range up to V_CC − 1.5 V.

**Things to check:** X-01 to X-07. In particular, **X-01**: the voltage trips measure `SENSE_P` against GND, not against `SENSE_N`. During charging the shunt lifts the cell's negative terminal by up to 50 mV, so the OV trip moves down to about 4.24 V, close to the 4.20 V charge voltage.

---

## 7. Thermal (sheet `thermal.kicad_sch`, parts 7xx)

**What it does.** It drives the Peltiers and the fans.

**How it works.**
- **Peltier driver:** the BTS7960 (IBT-2) module is an H-bridge, the same circuit that drives a DC motor forwards and backwards. For a Peltier, "forwards" cools the pocket and "backwards" heats it. `TEC_RPWM`/`TEC_LPWM` (PB0/PB1) choose the direction and power by PWM. `TEC_EN` (PB10) enables both halves through R701; R702 keeps it off at boot, and Q701 forces it off on `FAULT`. The two TEC1-12706 in series run from `+12V_SW`, about 6 V and roughly 3 A each.
- **Option (a), decided 2026-10-28:** the BTS7960 is mounted in the thermal unit and the Peltiers wire straight to it. The board only sends `+12V_SW`/GND (J702 pins 1–2) and the logic header (J701). J703 has been removed.
- **Fans:** Q702 (IRLZ44N logic-level MOSFET) switches both 12 V fans (J704, J706) together with PWM from PA8. R703 is the gate resistor, R704 the pull-down, and D701 the flyback diode for the fan motors. J705 is the always-on 5 V pocket mixing fan.

**Cross-check with:**
- The IBT-2 / BTS7960 module documentation (pinout RPWM, LPWM, R_EN, L_EN, VCC, GND).
- Infineon BTS7960 datasheet: logic input high ≥ 2.15 V, but the module adds a 74HC244 buffer powered from 5 V (**T-01**).
- IRLZ44N datasheet (R_DS(on) at V_GS = 4 V; you drive it with 3.3 V, **T-02**).

**Things to check:** T-01 to T-04.

---

## 8. MCU (sheet `mcu.kicad_sch`, parts 8xx)

**What it does.** The Blue Pill (STM32F103C8) plugs into two 1×20 sockets J801/J802. USB goes to the PC (CDC serial to the Python UI).

| Pin | Net | Use |
|---|---|---|
| PA0 | I_MON | ADC: fast current |
| PA1 | V_FAST | ADC: fast cell voltage ÷ 2 |
| PA8 | FAN_PWM | TIM1_CH1: both 12 V fans |
| PA9 / PA10 | DBG_TX / DBG_RX | debug UART (J803) |
| PA11 / PA12 | USB | on the Blue Pill |
| PB0 / PB1 | TEC_RPWM / TEC_LPWM | TIM3_CH3 / CH4: Peltier direction + power |
| PB10 | TEC_EN | BTS7960 enable |
| PB6 / PB7 | SCL / SDA | I2C1: ADS1115 0x48, 0x49; MCP4725 0x60 (load), 0x61 (charger) |
| PB12 / PB13 | K1_EN / K2_EN | charger relay / load relay |
| PB14 | LOAD_OFF | high = load off (pulled up by R305) |
| PB15 | FAULT_N | read the hardware fault; open-drain output to force a stop |

- **D801** connects the board's `+5V` to the Blue Pill's 5 V pin. On the Blue Pill that pin is wired **directly** to the USB VBUS line, with no protection. The sheet note says D801 stops the board back-feeding the PC; it actually does the opposite: it stops the **PC** from feeding the board's 5 V rail, and lets the board feed about 4.7 V into the USB cable when the PC is off (**U-01**).
- R801/R802 are 4.7k I2C pull-ups, marked DNP: most ADS1115/MCP4725 modules already have them.

**Cross-check with:**
- stm32-base.org Blue Pill page and schematic (power warning about the 5 V pin).
- STM32F103C8 datasheet DS5319 (which pins are 5 V tolerant; PA0/PA1 are ADC pins and are not).

**Things to check:** U-01 to U-04.

---

## 9. How the firmware is expected to use the hardware

These sequences come from the design, so check that you agree with them:

1. **Boot:** relays open (R203/R206 pull-downs), load off (R305 holds `LOAD_OFF` high), BTS7960 off (R702), DACs at power-on value (MCP4725 default: check, **L-08**).
2. **Discharge pulse:** K1 open → close K2 with `LOAD_OFF` high → set DAC_L = 0 → release `LOAD_OFF` → ramp DAC_L to the target → log V (ADS1115 + V_FAST) and I → set DAC_L = 0 → `LOAD_OFF` high → open K2.
3. **Charge:** K2 open, `LOAD_OFF` high → set the charger DAC so the module output = cell voltage → close K1 → lower the DAC step by step until I = target (CC) → hold 4.20 V (CV) → open K1 at C/20.
4. **Fault:** any comparator trips → hardware drops everything → firmware sees `FAULT_N` low, logs it, and latches (the comparators have no hysteresis, **X-03**).

---

## 10. Summary of the issues found while writing this guide

The full list, with how to check each one, is in `docs/SCHEMATIC_REVIEW.md`. The ones I'd look at first:

| ID | Issue | Why it matters |
|---|---|---|
| **P-01** | P6KE33A stand-off (28.2 V) is below the 30 V supply | The TVS can start conducting and heating at 30 V. P6KE36A (30.8 V stand-off) is the usual choice. |
| **C-01** | Charger has no hardware current limit (module CC bypassed) | Closing K1 at the wrong moment trips OC or stresses the cell. Firmware must follow the sequence above. |
| **U-01** | D801 direction / Blue Pill 5 V pin tied to USB VBUS | The board can back-feed the PC's USB port, and the sheet note is wrong. |
| **X-01** | OV/UV trips measured against GND, not SENSE_N | The OV trip drops to about 4.24 V while charging at 5 A, close to the 4.20 V target. |
| **R-02** | BS170 driven with 3.3 V for a 117 mA relay coil | Check R_DS(on) at V_GS = 3.3 V. |
| **T-01** | BTS7960 module buffer (74HC244 at 5 V) vs 3.3 V logic | It may not see 3.3 V as "high". Sellers say it works, but test it. |
| **M-04** | Divider currents drain the cell (≈ 0.9 mA) and back-power unpowered chips | Matters if a cell is left in the pocket with the bench off. |
| **F-01** | Relay coil pads are 2.1 × 0.5 mm slots | They can't be drilled on the CNC (layout, not schematic). |

---

## 11. References (for cross-checking)

- TI, *Voltage-to-current (V-I) converter circuit with MOSFET*, SBOA327: https://www.ti.com/lit/pdf/sboa327
- TI, *Low-side, bidirectional current sensing circuit*, SBOA223: https://www.ti.com/lit/pdf/SBOA223 · TIPD175: https://www.ti.com/tool/TIPD175
- TI, *How to Dynamically Adjust Power Module Output Voltage*, SLVA861: https://www.ti.com/lit/pdf/slva861
- TI, SNVAA33 (feedback current injection network): https://www.ti.com/document-viewer/lit/html/SNVAA33
- Maxim/ADI, App note 4498, *Add Margining Capability to a DC/DC Converter*: https://www.analog.com/media/en/technical-documentation/design-notes/add-margining-capability-to-a-dcdc-converter.pdf
- XLSemi, XL4016 datasheet: https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/XL4016E1_C55881.pdf (FB = 1.25 V)
- mikrocontroller.net, XL4016 FB driven by a DAC: https://www.mikrocontroller.net/topic/340508
- Panasonic, LF-G (ALFG) relay datasheet: https://industrial.panasonic.com/ac/e/ (ALFG2PF121: 12 V, 117 mA, 1.4 W, 33 A)
- TI datasheets: ADS1115 https://www.ti.com/lit/ds/symlink/ads1115.pdf · OPA2188 https://www.ti.com/lit/ds/symlink/opa2188.pdf · TL431 https://www.ti.com/lit/ds/symlink/tl431.pdf · LM339 https://www.ti.com/lit/ds/symlink/lm339.pdf · LM393 https://www.ti.com/lit/ds/symlink/lm393.pdf
- Microchip, MCP4725 datasheet: https://ww1.microchip.com/downloads/en/devicedoc/22039d.pdf
- Infineon, IRFP260N and BTS7960 datasheets (infineon.com)
- onsemi, BS170 datasheet (onsemi.com)
- stm32-base.org, Blue Pill: https://stm32-base.org/boards/STM32F103C8T6-Blue-Pill
- Arduino forum, IBT-2 74HC244 logic level: https://forum.arduino.cc/t/bts7960-btn7960n-ibt-2-motor-drive-module/1142926
- EEVblog forum, Dynamic Electronic Load project: https://eevblog.com/forum/projects/dynamic-electronic-load-project/125
- Battery University, BU-409 *Charging Lithium-ion*: https://batteryuniversity.com/article/bu-409-charging-lithium-ion
