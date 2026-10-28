# Cell Test Bench

Single-cell characterization bench for 18650 and 21700 Li-ion cells (DMEGC INR45E, generic 3.5 Ah 18650).
Part of the Solaris final-year project.

- 0–10 A linear electronic load (constant current), down to 2.0 V
- Charging up to 5 A from a 30 V / 10 A bench PSU through an XL4016 CC/CV module, voltage set by a DAC
- Bidirectional current measurement on one 10 mΩ 4-terminal shunt (Ohmite LVK25)
- Cell held at about 10–45 °C in an insulated pocket cooled/heated by two TEC1-12706 Peltiers
- STM32F103 Blue Pill, USB CDC to a Python UI
- Hardware protection (OV, UV, OC, OT) that works without the firmware

## Repository layout

| Path | Contents |
|---|---|
| `hardware/kicad/` | KiCad project: open `cell_test_bench.kicad_pro` |
| `hardware/kicad/lib/` | Project footprint library (`cell_bench.pretty`) and 3D models (`cell_bench.3dshapes`) |
| `hardware/bom.csv` | BOM with Özdisan links where available |
| `hardware/tools/` | Python scripts that generated the schematic, placement and routing |
| `mechanical/` | Enclosure + thermal cell pocket (CadQuery): STL parts, STEP assembly, renders |
| `docs/` | Schematic PDF, PCB renders, DRC report |
| `firmware/`, `ui/` | Not started yet |

## Status (v0.2)

| Item | State |
|---|---|
| Schematic | 8 sheets, every part has a footprint, netlist checked against KiCad's export |
| Parts | Hand-solder friendly: THT where sensible, 1206 passives, SOIC-8 op-amp |
| PCB | 180 × 130 mm, 2 layers (order 2 oz copper), placed and routed, GND pours on both layers |
| DRC | See `docs/drc_report.txt` and the notes below |
| 3D | Board STEP + enclosure assembly in `mechanical/step/` |

### Opening in KiCad 10

The files are saved in KiCad 7 format. KiCad 10 opens them and upgrades on save. The project's own `fp-lib-table` points to `lib/cell_bench.pretty`, so the footprints and 3D models travel with the repository.

After opening, run these once in KiCad 10:

1. **Schematic → Inspect → ERC.** Expect pin-type warnings on the module headers, which are drawn as connectors.
2. **PCB → Edit → Fill All Zones** (B), then **Inspect → DRC**.
3. **Tools → Update PCB from Schematic** should report no changes.

### Layout notes

- Every connector sits on a board edge, with wire entry facing outward.
  - **Left edge:** PSU input, buck modules, XL4016 charger, thermostat.
  - **Bottom edge:** cell, series resistor, IRFP260N, NTCs. The MOSFET's back faces outward so the heatsink bolts on beyond the edge.
  - **Top edge:** Peltier driver, fans, Blue Pill USB.
- **High-current path:** 3 mm tracks on both layers, plus pours. The 10 mΩ shunt pad necks down to 1.6 mm because the pad itself is only 1.4 mm wide.
- **Ground:** the bottom layer is kept as clear as possible so its GND pour stays continuous. Each SMD GND pad has its own via to it, and stitching vias tie the two pours together.
- **Plug-in modules** (Blue Pill, 2× ADS1115, 2× MCP4725) have keep-out areas where the module body overhangs the board.
- The layout was autorouted by `hardware/tools/router.py`. It is electrically complete, but a hand pass in KiCad (or a run through Quilter) will make it tidier.

## Sheets

| Sheet | What it does |
|---|---|
| Power | PSU input, 10 A mini-blade fuse, TVS, 12 V (XL4016) and 5 V (MP1584) buck modules, thermostat cutting `+12V_SW` |
| Cell_Relays | Cell power and Kelvin-sense connectors, 15 A cell fuse, 10 mΩ shunt, relays K1 (charger) and K2 (load), Panasonic ALFG2PF121, with interlock and fault drop-out |
| Electronic_Load | IRFP260N linear CC loop (OPA2188), MCP4725 setpoint, series 0.1 Ω 50 W resistor, kill transistors, bidirectional current monitor `I_MON` |
| Charger | XL4016 CC/CV module, second MCP4725 injecting current into FB to lower the output from a 4.25 V hardware ceiling |
| Measurement | ADS1115 #1 (shunt, cell voltage), ADS1115 #2 (four NTCs), `V_FAST` divider for the internal ADC |
| Protection | TL431 2.5 V reference, LM339N + LM393N comparators, `FAULT_N` wired-OR, `FAULT` inverter |
| Thermal | BTS7960 H-bridge for 2× TEC1-12706, fan PWM (IRLZ44N), pocket mixing fan |
| MCU | Blue Pill headers, USB back-feed diode, debug UART, I2C pull-ups |

## Blue Pill pin map

| Pin | Signal | Function |
|---|---|---|
| PA0 | I_MON | Fast current (internal ADC), 1.65 V + 0.12 V/A |
| PA1 | V_FAST | Fast cell voltage / 2 (internal ADC) |
| PA8 | FAN_PWM | TIM1_CH1, both 12 V fans |
| PA9 / PA10 | DBG_TX / DBG_RX | Debug UART |
| PA11 / PA12 | USB | USB CDC to the PC (on the Blue Pill) |
| PB0 / PB1 | TEC_RPWM / TEC_LPWM | TIM3_CH3 / CH4, Peltier heat/cool |
| PB10 | TEC_EN | BTS7960 enable |
| PB6 / PB7 | SCL / SDA | I2C1: ADS1115 0x48, 0x49; MCP4725 0x60 (load), 0x61 (charger) |
| PB12 / PB13 | K1_EN / K2_EN | Charger relay / load relay |
| PB14 | LOAD_OFF | High = load off (pulled up, off at boot) |
| PB15 | FAULT_N | Read hardware fault; open-drain output to force a stop |

The Blue Pill plugs in with its USB end at the top board edge. The silkscreen marks the B12 and VB corners: check the orientation before soldering the headers.

## Key design numbers

- Load setpoint: DAC 0–3.3 V → divider 29.4 k / 1 k → 0–108 mV → 0–10.8 A.
- Current monitor: `I_MON = 1.65 V + 0.12 V/A`.
- Protection trips: OV > ~4.29 V, UV < ~1.95 V, discharge > ~11 A, charge > ~6.4 A, heatsink or cell NTC > ~62 °C.
- Charger: set the XL4016 CV pot to 4.25 V before connecting the FB tap. The DAC can only lower the voltage from there.

## Known limits

- The XL4016 module's own current limit is bypassed, because its IN− and OUT− share system ground. Charge current is regulated by firmware and limited by the OC comparator.
- UV protection also trips when no cell is inserted, and prevents charging a cell that is below ~1.95 V.
- The comparators have no hysteresis yet. The firmware is expected to latch faults.
- Check that the BTS7960 module accepts 3.3 V logic inputs.
- Module pin orders (MCP4725, ADS1115, BTS7960) vary between sellers. Check them against the silkscreen before soldering the sockets.
- Check the relay footprint against the Panasonic ALFG2PF121 datasheet. KiCad's footprint is drawn for the ALFG series.

## Regenerating

The schematic, placement and routing are reproducible from `hardware/tools/`:

```
python3 design.py ../kicad                 # schematic (overwrites edits!)
python3 makelib.py ../kicad                # project footprint library + 3D models
kicad-cli sch export netlist --format kicadsexpr -o net.net ../kicad/cell_test_bench.kicad_sch
python3 pcbgen.py net.net ../kicad         # board outline + placement (overwrites the PCB!)
python3 router.py in.kicad_pcb out.kicad_pcb
```

Once you start editing in KiCad, those edits are the source of truth. Don't re-run the generators after that.
