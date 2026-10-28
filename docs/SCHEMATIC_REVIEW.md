# Schematic review checklist (v0.3)

Go through this with `docs/SCHEMATIC_GUIDE.md` open. For every line:

1. Put **OK**, **CHANGE** or **?** in the *Status* column.
2. Write what you found, or what you want changed, in *Your comment*.
3. Commit the file. I'll read your comments and make the changes in the next version.

The IDs (P-01, L-03 …) match the guide. **Bold** items are the ones I think matter most.

## Part A: circuit checks

### Power (1xx)

| ID | What to check | How / reference | Status | Your comment |
|---|---|---|---|---|
| **P-01** | D101 P6KE33A: stand-off voltage V_RWM = 28.2 V is **below** the 30 V supply. It may conduct and heat at 30 V. Swap to P6KE36A (V_RWM 30.8 V)? | P6KE datasheet table: V_RWM vs your PSU's real maximum | | |
| P-02 | F101 10 A: enough for the whole input current (charger ~1 A at 30 V, 12 V rail ~4 A × 12/30, 5 V rail)? | Add up rail currents ÷ efficiency | | |
| P-03 | 12 V buck (XL4016 on J102) load: Peltiers ~3 A + relay coils 2 × 117 mA + 2 fans + op-amp | Module rating; is a heatsink needed? | | |
| P-04 | 5 V buck (MP1584 on J103) load: Blue Pill, comparators, TL431 bias, BTS7960 logic, pocket fan | MP1584 module rating (~2-3 A) | | |
| P-05 | Thermostat J104 cuts only `+12V_SW` (relays + BTS7960). The load stops because K2 opens. Is that enough for you? | Guide §1 | | |

### Cell path and relays (2xx)

| ID | What to check | How / reference | Status | Your comment |
|---|---|---|---|---|
| R-01 | K1/K2 ALFG2PF121 pinout (A1/A2 coil, 11/14 contacts) and footprint match the Panasonic datasheet | LF-G datasheet drawing vs footprint `Relay_SPST_Panasonic_ALFG_FormA` | | |
| **R-02** | Q201/Q202 BS170 driven from a 3.3 V GPIO must switch the 117 mA coil. Is R_DS(on) at V_GS = 3.3 V low enough on a worst-case part (V_GS(th) up to 3 V)? | BS170 datasheet: transfer curve. If not, use a MOSFET with R_DS(on) specified at V_GS ≤ 2.5 V | | |
| R-03 | Interlock: Q203 (gate K2_EN) and Q204 (gate K1_EN) make "both relays on" impossible. Do you agree with the logic? | Guide §2 relay figure | | |
| **R-04** | R201 LVK25 pin numbering: pins 1/4 = current, 2/3 = sense? Check against the Ohmite drawing. A swap here makes the Kelvin connection useless. | Ohmite LVK datasheet pad drawing vs footprint `R_Shunt_Ohmite_LVK25` | | |
| R-05 | F202 15 A mini-blade in a Keystone 3568 holder (30 A): fuse type and holder rating OK for 11 A continuous? | Keystone 3568 datasheet | | |
| R-06 | J205 (cell power) Phoenix MKDS 3 terminal current rating ≥ 11 A with 1.5 mm² wire | Phoenix datasheet | | |
| R-07 | Kelvin wires (J206) go to the cell tabs separately from the power plates (mechanical P75 probe) | `mechanical/README.md` | | |

### Electronic load (3xx)

| ID | What to check | How / reference | Status | Your comment |
|---|---|---|---|---|
| L-01 | Loop equation I = DAC × (1k/30.4k) / 10 mΩ → 10.86 A at 3.3 V. Agree with the summing node R303/R304 and integrator R306/C302? | Guide §3; TI SBOA327 | | |
| L-02 | U301 (OPA2188, 12 V supply) output swing high enough to drive the IRFP260N gate to the V_GS it needs for 11 A? | OPA2188 output swing; IRFP260N transfer curve | | |
| L-03 | Stability: R307 100 Ω, C302 1 nF, R306 10k. Needs a scope test with a current step. | EEVblog load threads; TI SBOA327 design notes | | |
| L-04 | Precision parts: R301/R302 and R303/R304 are 0.1 %; R306 is not (it only sets the integrator speed). OK? | Guide §3 | | |
| **L-05** | IRFP260N in linear mode: DC safe operating area at ~3-4 V V_DS and 10 A (~30-40 W). Planar HEXFET, but check the DC SOA line. Heatsink size? | IRFP260N datasheet SOA figure | | |
| L-06 | 0.1 Ω 50 W series resistor: at 10 A it takes 10 W; the minimum cell voltage for full current is ~1.2 V | Guide §3 | | |
| L-07 | U301B current monitor offset comes from +3V3 (R311/R312), but the OC trip reference is the TL431 2.50 V. A 3V3 error moves the trip point. Acceptable? | Guide §3, §6 | | |
| L-08 | MCP4725 power-on output = value stored in its EEPROM. Make sure it's 0 (load and charger both safe at power-up). | MCP4725 datasheet "power-on reset" | | |
| L-09 | During charging, ISNS_N is positive, so U301A drives the gate fully on (K2 is open, so no current flows). Firmware must keep LOAD_OFF high while charging. | Guide §3, §9 | | |

### Charger (4xx)

| ID | What to check | How / reference | Status | Your comment |
|---|---|---|---|---|
| **C-01** | No hardware charge-current limit (module CC bypassed, shared GND). Only the 6.4 A comparator stops a surge. Accept with the firmware sequence in Guide §9, or change the design? | Guide §4 | | |
| C-02 | Measure your XL4016 module's FB divider (R_bottom, R_top + pot) and check that DAC 0-3.3 V covers ~2.5-4.25 V | Multimeter on the module; Guide §4 formula | | |
| C-03 | CV pot preset to 4.25 V before the FB wire is connected = hardware ceiling. Agree with 4.25 V? | Cell datasheet max charge voltage | | |
| C-04 | D401 BAT85 leakage at high temperature adds a tiny injection (lowers voltage slightly). Negligible? | BAT85 datasheet | | |
| C-05 | PSU off with K1 closed: the cell could back-feed the module. K1's coil is on +12V_SW, so K1 opens when power drops. Confirm. | Guide §2 | | |
| C-06 | Closing K1 connects the module's output capacitors to the cell; a voltage mismatch gives a current spike | Firmware: match voltages first | | |

### Measurement (5xx)

| ID | What to check | How / reference | Status | Your comment |
|---|---|---|---|---|
| M-01 | ADS1115 inputs stay within GND − 0.3 V … VDD + 0.3 V (ISNS_N and SENSE_N go ~−0.11 V during discharge: OK) | ADS1115 datasheet abs. max | | |
| M-02 | R503/R504 must be 0.1 % (cell voltage accuracy) or calibrated against a DMM | Guide §5 | | |
| M-03 | NTC type: 10k B3950? Pull-ups R506-R509 10k 0.1 %. Matches the NTCs you'll buy? | NTC datasheet | | |
| **M-04** | Dividers on SENSE_P (R503/R504, R510/R511, R608/R609, R610/R611) drain ~0.9 mA from the cell all the time, and feed voltage into unpowered ICs when the bench is off | Guide §10. Fix options: remove the cell when off, or add a switch/relay on the sense line | | |
| M-05 | ADS1115 and MCP4725 module pin order differs between sellers. Check against the modules you buy. | Silkscreen of the actual module | | |
| M-06 | V_FAST is referenced to GND, not SENSE_N: firmware subtracts I × R_shunt | Guide §5 | | |

### Protection (6xx)

| ID | What to check | How / reference | Status | Your comment |
|---|---|---|---|---|
| **X-01** | OV/UV dividers measure SENSE_P against GND, not SENSE_N. At 5 A charge the OV trip falls to ~4.24 V; at 10 A discharge UV becomes ~2.05 V. Acceptable, or use a difference amplifier? | Guide §6 | | |
| X-02 | Trip values: OV 4.29 V, UV 1.95 V, OC +11.25 A / −6.39 A, OT 61.5 °C. Right for your cells? | Guide §6 table; cell datasheets | | |
| X-03 | No hysteresis: comparators may chatter near the threshold. Firmware latches the fault. Add hysteresis resistors? | LM339 datasheet application | | |
| X-04 | UV trips with no cell inserted, and blocks charging a cell below 1.95 V | Guide §6 | | |
| X-05 | OC trips use I_MON (offset from +3V3) vs VREF (TL431). See L-07. | Guide §6 | | |
| X-06 | LM339/LM393 on 5 V: inputs must stay below V_CC − 1.5 V = 3.5 V (I_MON is clamped at 3.3 V: OK) | LM339 datasheet | | |
| X-07 | FAULT reaches all four kill points: Q303 (load), Q205/Q206 (relays), Q701 (BTS7960) | Netlist (Part B below) | | |

### Thermal (7xx)

| ID | What to check | How / reference | Status | Your comment |
|---|---|---|---|---|
| **T-01** | IBT-2 module input buffer (74HC244 powered from 5 V) may need > 3.5 V for "high". Test with 3.3 V, or add a 74HCT245 / power the buffer from 3.3 V. | Arduino forum thread on IBT-2; 74HC244 datasheet V_IH | | |
| T-02 | Q702 IRLZ44N at V_GS = 3.3 V for two fans (~0.2-0.4 A): R_DS(on) is specified at 4-5 V | IRLZ44N datasheet | | |
| T-03 | Two TEC1-12706 in series on 12 V: about 3 A, about 6 V each. Enough cooling power? | TEC1-12706 datasheet curves | | |
| T-04 | Fan PWM frequency (PA8) and D701 flyback diode OK for your fans? | Fan datasheet | | |

### MCU (8xx)

| ID | What to check | How / reference | Status | Your comment |
|---|---|---|---|---|
| **U-01** | D801: board +5V → Blue Pill 5 V pin, which is wired directly to USB VBUS. It stops the PC feeding the board, but lets the board feed ~4.7 V into the USB cable when the PC is off. The sheet note says the opposite. Decide: keep, reverse, or power the Blue Pill only from USB. | stm32-base.org Blue Pill power warning | | |
| U-02 | Blue Pill 3.3 V regulator supplies all the I2C modules, NTCs and pull-ups (~10-20 mA). OK? | Blue Pill LDO rating | | |
| U-03 | PA0/PA1 are not 5 V tolerant. I_MON is clamped by D301/D302; V_FAST is ≤ 2.1 V. OK. | STM32F103 datasheet | | |
| U-04 | I2C pull-ups: R801/R802 are DNP. Do your modules have pull-ups? | Module schematic | | |

### Layout-related (found during the Quilter run)

| ID | What to check | How / reference | Status | Your comment |
|---|---|---|---|---|
| F-01 | K1/K2 coil pads are 2.1 × 0.5 mm slots: not drillable on the CNC. Change to round holes for the real pin size. | ALFG datasheet pin size | | |
| F-02 | GND carries both the 10 A return and the analog reference. Split into PGND / GND joined at R201? | `docs/LAYOUT_REVIEW.md` §B | | |

## Part B: every part

Pin → net is taken from the netlist (v0.3, J703 removed). "—" = not connected. Check that each part's value, footprint and connections make sense, using the block checks above.


### Power (1xx)

| Ref | Value | Footprint | Pins → nets | Status | Your comment |
|---|---|---|---|---|---|
| C101 | 100uF 50V | CP_Radial_D10.0mm_P5.00mm | 1: VIN, 2: GND | | |
| C102 | 220uF 25V | CP_Radial_D8.0mm_P3.50mm | 1: +12V, 2: GND | | |
| C103 | 100uF 16V | CP_Radial_D6.3mm_P2.50mm | 1: +5V, 2: GND | | |
| C104 | 220uF 25V | CP_Radial_D8.0mm_P3.50mm | 1: +12V_SW, 2: GND | | |
| D101 | P6KE33A (TVS) | D_DO-15_P10.16mm_Horizontal | 1: VIN, 2: GND | | |
| F101 | 10A mini blade | Fuseholder_Blade_Mini_Keystone_3568 | 1: VIN_RAW, 2: VIN | | |
| J101 | PSU in 30V 10A (+, -) | TerminalBlock_Phoenix_MKDS-3-2-5.08_1x02_P5.08mm_Horizontal | 1: VIN_RAW, 2: GND | | |
| J102 | 12V buck XL4016: IN+ IN- OUT+ OUT- | TerminalBlock_Phoenix_MKDS-1,5-4-5.08_1x04_P5.08mm_Horizontal | 1: VIN, 2: GND, 3: +12V, 4: GND | | |
| J103 | 5V buck MP1584: IN+ IN- OUT+ OUT- | TerminalBlock_Phoenix_MKDS-1,5-4-5.08_1x04_P5.08mm_Horizontal | 1: +12V, 2: GND, 3: +5V, 4: GND | | |
| J104 | Thermostat KSD9700 60C NC | TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal | 1: +12V, 2: +12V_SW | | |
| H101 | M3 mounting hole | MountingHole_3.2mm_M3 | (mechanical) | | |
| H102 | M3 mounting hole | MountingHole_3.2mm_M3 | (mechanical) | | |
| H103 | M3 mounting hole | MountingHole_3.2mm_M3 | (mechanical) | | |
| H104 | M3 mounting hole | MountingHole_3.2mm_M3 | (mechanical) | | |

### Cell path and relays (2xx)

| Ref | Value | Footprint | Pins → nets | Status | Your comment |
|---|---|---|---|---|---|
| D201 | 1N4007 | D_DO-41_SOD81_P10.16mm_Horizontal | 1: +12V_SW, 2: K1_COIL | | |
| D202 | 1N4007 | D_DO-41_SOD81_P10.16mm_Horizontal | 1: +12V_SW, 2: K2_COIL | | |
| F202 | 15A mini blade (cell) | Fuseholder_Blade_Mini_Keystone_3568 | 1: CELL_P_RAW, 2: CELL_P | | |
| J205 | Cell power to pocket (+, -) | TerminalBlock_Phoenix_MKDS-3-2-5.08_1x02_P5.08mm_Horizontal | 1: CELL_P_RAW, 2: CELL_N | | |
| J206 | Cell Kelvin sense (+, -) | JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical | 1: SENSE_P, 2: SENSE_N | | |
| K1 | ALFG2PF121 (charge) | Relay_SPST_Panasonic_ALFG_FormA | 11: CHG_OUT, 14: CELL_P, A1: +12V_SW, A2: K1_COIL | | |
| K2 | ALFG2PF121 (load) | Relay_SPST_Panasonic_ALFG_FormA | 11: CELL_P, 14: LOAD_P, A1: +12V_SW, A2: K2_COIL | | |
| Q201 | BS170 | TO-92_Inline_Wide | 1: K1_COIL, 2: K1_G, 3: GND | | |
| Q202 | BS170 | TO-92_Inline_Wide | 1: K2_COIL, 2: K2_G, 3: GND | | |
| Q203 | BS170 | TO-92_Inline_Wide | 1: K1_G, 2: K2_EN, 3: GND | | |
| Q204 | BS170 | TO-92_Inline_Wide | 1: K2_G, 2: K1_EN, 3: GND | | |
| Q205 | BS170 | TO-92_Inline_Wide | 1: K1_G, 2: FAULT, 3: GND | | |
| Q206 | BS170 | TO-92_Inline_Wide | 1: K2_G, 2: FAULT, 3: GND | | |
| R201 | 10mR 1% 2W LVK25 | R_Shunt_Ohmite_LVK25 | 1: CELL_N, 2: ISNS_N, 3: ISNS_G, 4: GND | | |
| R202 | 1k | R_1206_3216Metric | 1: K1_EN, 2: K1_G | | |
| R203 | 100k | R_1206_3216Metric | 1: K1_G, 2: GND | | |
| R204 | 100k | R_1206_3216Metric | 1: K1_EN, 2: GND | | |
| R205 | 1k | R_1206_3216Metric | 1: K2_EN, 2: K2_G | | |
| R206 | 100k | R_1206_3216Metric | 1: K2_G, 2: GND | | |
| R207 | 100k | R_1206_3216Metric | 1: K2_EN, 2: GND | | |

### Electronic load (3xx)

| Ref | Value | Footprint | Pins → nets | Status | Your comment |
|---|---|---|---|---|---|
| C301 | 10nF | C_1206_3216Metric | 1: SETP, 2: ISNS_G | | |
| C302 | 1nF | C_1206_3216Metric | 1: INN, 2: OA_OUT | | |
| C303 | 10nF | C_1206_3216Metric | 1: I_MON, 2: GND | | |
| C304 | 100nF | C_1206_3216Metric | 1: +12V, 2: GND | | |
| C305 | 10uF | C_1206_3216Metric | 1: +12V, 2: GND | | |
| D301 | BAT85 | D_DO-35_SOD27_P7.62mm_Horizontal | 1: +3V3, 2: I_MON | | |
| D302 | BAT85 | D_DO-35_SOD27_P7.62mm_Horizontal | 1: I_MON, 2: GND | | |
| J301 | Series R 0.1R 50W alu (off-board) | TerminalBlock_Phoenix_MKDS-3-2-5.08_1x02_P5.08mm_Horizontal | 1: LOAD_P, 2: LOAD_D | | |
| Q301 | IRFP260N | TO-247-3_Vertical | 1: GATE, 2: LOAD_D, 3: GND | | |
| Q302 | BS170 | TO-92_Inline_Wide | 1: INP, 2: LOAD_OFF, 3: GND | | |
| Q303 | BS170 | TO-92_Inline_Wide | 1: INP, 2: FAULT, 3: GND | | |
| R301 | 29.4k 0.1% | R_1206_3216Metric | 1: DAC_L, 2: SETP | | |
| R302 | 1k 0.1% | R_1206_3216Metric | 1: SETP, 2: ISNS_G | | |
| R303 | 10k 0.1% | R_1206_3216Metric | 1: SETP, 2: INP | | |
| R304 | 10k 0.1% | R_1206_3216Metric | 1: ISNS_N, 2: INP | | |
| R305 | 10k | R_1206_3216Metric | 1: +3V3, 2: LOAD_OFF | | |
| R306 | 10k | R_1206_3216Metric | 1: INN, 2: ISNS_G | | |
| R307 | 100R | R_1206_3216Metric | 1: OA_OUT, 2: GATE | | |
| R308 | 10k | R_1206_3216Metric | 1: GATE, 2: GND | | |
| R309 | 1k 0.1% | R_1206_3216Metric | 1: ISNS_N, 2: MN | | |
| R310 | 12k 0.1% | R_1206_3216Metric | 1: MN, 2: MON_RAW | | |
| R311 | 24.9k | R_1206_3216Metric | 1: +3V3, 2: MB | | |
| R312 | 1k | R_1206_3216Metric | 1: MB, 2: ISNS_G | | |
| R313 | 1k | R_1206_3216Metric | 1: MON_RAW, 2: I_MON | | |
| U301 | OPA2188AID | SOIC-8_3.9x4.9mm_P1.27mm | 1: OA_OUT, 2: INN, 3: INP, 4: GND, 5: MB, 6: MN, 7: MON_RAW, 8: +12V | | |
| U302 | MCP4725 module #1 (A0=GND, 0x60): VCC GND SCL SDA A0 OUT | PinSocket_1x06_P2.54mm_Vertical | 1: +3V3, 2: GND, 3: SCL, 4: SDA, 5: GND, 6: DAC_L | | |

### Charger (4xx)

| Ref | Value | Footprint | Pins → nets | Status | Your comment |
|---|---|---|---|---|---|
| C401 | 1uF | C_1206_3216Metric | 1: DAC_CF, 2: GND | | |
| D401 | BAT85 | D_DO-35_SOD27_P7.62mm_Horizontal | 1: XL_FB, 2: CHG_INJ | | |
| J401 | XL4016 CC/CV module: IN+ IN- OUT+ OUT- | TerminalBlock_Phoenix_MKDS-1,5-4-5.08_1x04_P5.08mm_Horizontal | 1: VIN, 2: GND, 3: CHG_OUT, 4: GND | | |
| J402 | XL4016 FB tap (wire to FB pin, GND) | JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical | 1: XL_FB, 2: GND | | |
| R401 | 1.2k | R_1206_3216Metric | 1: DAC_CF, 2: CHG_INJ | | |
| R402 | 100R | R_1206_3216Metric | 1: DAC_C, 2: DAC_CF | | |
| U401 | MCP4725 module #2 (A0=VCC, 0x61): VCC GND SCL SDA A0 OUT | PinSocket_1x06_P2.54mm_Vertical | 1: +3V3, 2: GND, 3: SCL, 4: SDA, 5: +3V3, 6: DAC_C | | |

### Measurement (5xx)

| Ref | Value | Footprint | Pins → nets | Status | Your comment |
|---|---|---|---|---|---|
| C501 | 100nF | C_1206_3216Metric | 1: ADC_IG, 2: ADC_IN | | |
| C502 | 100nF | C_1206_3216Metric | 1: ADC_VP, 2: ADC_VN | | |
| C503 | 100nF | C_1206_3216Metric | 1: NTC_CELL, 2: GND | | |
| C504 | 100nF | C_1206_3216Metric | 1: NTC_AIR, 2: GND | | |
| C505 | 100nF | C_1206_3216Metric | 1: NTC_HS, 2: GND | | |
| C506 | 100nF | C_1206_3216Metric | 1: NTC_TEC, 2: GND | | |
| C507 | 10nF | C_1206_3216Metric | 1: V_FAST, 2: GND | | |
| J501 | NTC 10k cell | JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical | 1: NTC_CELL, 2: GND | | |
| J502 | NTC 10k air | JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical | 1: NTC_AIR, 2: GND | | |
| J503 | NTC 10k hs | JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical | 1: NTC_HS, 2: GND | | |
| J504 | NTC 10k tec | JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical | 1: NTC_TEC, 2: GND | | |
| R501 | 100R | R_1206_3216Metric | 1: ISNS_G, 2: ADC_IG | | |
| R502 | 100R | R_1206_3216Metric | 1: ISNS_N, 2: ADC_IN | | |
| R503 | 10k 0.1% | R_1206_3216Metric | 1: SENSE_P, 2: ADC_VP | | |
| R504 | 10k 0.1% | R_1206_3216Metric | 1: ADC_VP, 2: ADC_VN | | |
| R505 | 100R | R_1206_3216Metric | 1: SENSE_N, 2: ADC_VN | | |
| R506 | 10k 0.1% | R_1206_3216Metric | 1: +3V3, 2: NTC_CELL | | |
| R507 | 10k 0.1% | R_1206_3216Metric | 1: +3V3, 2: NTC_AIR | | |
| R508 | 10k 0.1% | R_1206_3216Metric | 1: +3V3, 2: NTC_HS | | |
| R509 | 10k 0.1% | R_1206_3216Metric | 1: +3V3, 2: NTC_TEC | | |
| R510 | 10k | R_1206_3216Metric | 1: SENSE_P, 2: V_FAST | | |
| R511 | 10k | R_1206_3216Metric | 1: V_FAST, 2: GND | | |
| U501 | ADS1115 module #1 (ADDR=GND): VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3 | PinSocket_1x10_P2.54mm_Vertical | 1: +3V3, 2: GND, 3: SCL, 4: SDA, 5: GND, 6: unconnected-(U501-Pin_6-Pad6), 7: ADC_IG, 8: ADC_IN, 9: ADC_VP, 10: ADC_VN | | |
| U502 | ADS1115 module #2 (ADDR=VDD): VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3 | PinSocket_1x10_P2.54mm_Vertical | 1: +3V3, 2: GND, 3: SCL, 4: SDA, 5: +3V3, 6: unconnected-(U502-Pin_6-Pad6), 7: NTC_CELL, 8: NTC_AIR, 9: NTC_HS, 10: NTC_TEC | | |

### Protection (6xx)

| Ref | Value | Footprint | Pins → nets | Status | Your comment |
|---|---|---|---|---|---|
| C601 | 100nF | C_1206_3216Metric | 1: VREF, 2: GND | | |
| C602 | 100nF | C_1206_3216Metric | 1: +5V, 2: GND | | |
| C603 | 100nF | C_1206_3216Metric | 1: +5V, 2: GND | | |
| Q601 | BS170 | TO-92_Inline_Wide | 1: FAULT, 2: FAULT_N, 3: GND | | |
| R601 | 1k | R_1206_3216Metric | 1: +5V, 2: VREF | | |
| R602 | 10k | R_1206_3216Metric | 1: VREF, 2: VREF_H | | |
| R603 | 10k | R_1206_3216Metric | 1: VREF_H, 2: GND | | |
| R604 | 15k | R_1206_3216Metric | 1: VREF, 2: VREF_C | | |
| R605 | 8.2k | R_1206_3216Metric | 1: VREF_C, 2: GND | | |
| R606 | 27k | R_1206_3216Metric | 1: VREF, 2: VREF_T | | |
| R607 | 9.1k | R_1206_3216Metric | 1: VREF_T, 2: GND | | |
| R608 | 7.15k | R_1206_3216Metric | 1: SENSE_P, 2: OV_DIV | | |
| R609 | 10k | R_1206_3216Metric | 1: OV_DIV, 2: GND | | |
| R610 | 5.6k | R_1206_3216Metric | 1: SENSE_P, 2: UV_DIV | | |
| R611 | 10k | R_1206_3216Metric | 1: UV_DIV, 2: GND | | |
| R612 | 20k | R_1206_3216Metric | 1: I_MON, 2: ID_DIV | | |
| R613 | 100k | R_1206_3216Metric | 1: ID_DIV, 2: GND | | |
| R614 | 10k | R_1206_3216Metric | 1: +3V3, 2: FAULT_N | | |
| R615 | 10k | R_1206_3216Metric | 1: +3V3, 2: FAULT | | |
| U601 | LM339N | DIP-14_W7.62mm | 1: FAULT_N, 2: FAULT_N, 3: +5V, 4: OV_DIV, 5: VREF, 6: VREF_H, 7: UV_DIV, 8: VREF_C, 9: I_MON, 10: ID_DIV, 11: VREF, 12: GND, 13: FAULT_N, 14: FAULT_N | | |
| U602 | LM393N | DIP-8_W7.62mm | 1: FAULT_N, 2: VREF_T, 3: NTC_HS, 4: GND, 5: NTC_CELL, 6: VREF_T, 7: FAULT_N, 8: +5V | | |
| U603 | TL431ACLPR | TO-92_Inline_Wide | 1: VREF, 2: GND, 3: VREF | | |

### Thermal (7xx)

| Ref | Value | Footprint | Pins → nets | Status | Your comment |
|---|---|---|---|---|---|
| D701 | 1N5819 | D_DO-41_SOD81_P10.16mm_Horizontal | 1: +12V, 2: FAN_N | | |
| J701 | BTS7960 IBT-2 logic: RPWM LPWM R_EN L_EN R_IS L_IS VCC GND | PinHeader_1x08_P2.54mm_Vertical | 1: TEC_RPWM, 2: TEC_LPWM, 3: TEC_EN_G, 4: TEC_EN_G, 5: unconnected-(J701-Pin_5-Pad5), 6: unconnected-(J701-Pin_6-Pad6), 7: +5V, 8: GND | | |
| J702 | BTS7960 power: B+ B- M+ M- | TerminalBlock_Phoenix_MKDS-1,5-4-5.08_1x04_P5.08mm_Horizontal | 1: +12V_SW, 2: GND, 3: —, 4: — | | |
| J704 | Fan 12V heatsink (+,-) | JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical | 1: +12V, 2: FAN_N | | |
| J705 | Pocket mixing fan 5V | JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical | 1: +5V, 2: GND | | |
| J706 | Fan 12V Peltier hot side (+,-) | JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical | 1: +12V, 2: FAN_N | | |
| Q701 | BS170 | TO-92_Inline_Wide | 1: TEC_EN_G, 2: FAULT, 3: GND | | |
| Q702 | IRLZ44N | TO-220-3_Vertical | 1: FAN_G, 2: FAN_N, 3: GND | | |
| R701 | 1k | R_1206_3216Metric | 1: TEC_EN, 2: TEC_EN_G | | |
| R702 | 100k | R_1206_3216Metric | 1: TEC_EN_G, 2: GND | | |
| R703 | 100R | R_1206_3216Metric | 1: FAN_PWM, 2: FAN_G | | |
| R704 | 100k | R_1206_3216Metric | 1: FAN_G, 2: GND | | |

### MCU (8xx)

| Ref | Value | Footprint | Pins → nets | Status | Your comment |
|---|---|---|---|---|---|
| C801 | 10uF | C_1206_3216Metric | 1: +3V3, 2: GND | | |
| D801 | 1N5819 | D_DO-41_SOD81_P10.16mm_Horizontal | 1: BP_5V, 2: +5V | | |
| J801 | Blue Pill header A: B12 B13 B14 B15 A8 A9 A10 A11 A12 A15 B3 B4 B5 B6 B7 B8 B9 5V GND 3V3 | PinSocket_1x20_P2.54mm_Vertical | 1: K1_EN, 2: K2_EN, 3: LOAD_OFF, 4: FAULT_N, 5: FAN_PWM, 6: DBG_TX, 7: DBG_RX, 8: unconnected-(J801-Pin_8-Pad8), 9: unconnected-(J801-Pin_9-Pad9), 10: unconnected-(J801-Pin_10-Pad10), 11: unconnected-(J801-Pin_11-Pad11), 12: unconnected-(J801-Pin_12-Pad12), 13: unconnected-(J801-Pin_13-Pad13), 14: SCL, 15: SDA, 16: unconnected-(J801-Pin_16-Pad16), 17: unconnected-(J801-Pin_17-Pad17), 18: BP_5V, 19: GND, 20: +3V3 | | |
| J802 | Blue Pill header B: VB C13 C14 C15 A0 A1 A2 A3 A4 A5 A6 A7 B0 B1 B10 B11 RST 3V3 GND GND | PinSocket_1x20_P2.54mm_Vertical | 1: unconnected-(J802-Pin_1-Pad1), 2: unconnected-(J802-Pin_2-Pad2), 3: unconnected-(J802-Pin_3-Pad3), 4: unconnected-(J802-Pin_4-Pad4), 5: I_MON, 6: V_FAST, 7: unconnected-(J802-Pin_7-Pad7), 8: unconnected-(J802-Pin_8-Pad8), 9: unconnected-(J802-Pin_9-Pad9), 10: unconnected-(J802-Pin_10-Pad10), 11: unconnected-(J802-Pin_11-Pad11), 12: unconnected-(J802-Pin_12-Pad12), 13: TEC_RPWM, 14: TEC_LPWM, 15: TEC_EN, 16: unconnected-(J802-Pin_16-Pad16), 17: unconnected-(J802-Pin_17-Pad17), 18: +3V3, 19: GND, 20: GND | | |
| J803 | Debug UART: TX RX GND | PinHeader_1x03_P2.54mm_Vertical | 1: DBG_TX, 2: DBG_RX, 3: GND | | |
| R801 | 4.7k DNP | R_1206_3216Metric | 1: +3V3, 2: SCL | | |
| R802 | 4.7k DNP | R_1206_3216Metric | 1: +3V3, 2: SDA | | |
