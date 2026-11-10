"""Cell test bench - schematic v0.4 (generated).

v0.4 is the "production" revision: every part can be bought in Turkiye, the board is
single-sided so it can be milled in-house, and the open schematic review items are closed
(see docs/SCHEMATIC_REVIEW.md and docs/CHANGES_v0.4.md).

Run: python3 design.py <outdir>"""
import sys, re
import kigen as K
import libs

REV = '0.4'
DATE = '2026-11-10'

R, C, CP = 'Device:R', 'Device:C', 'Device:C_Polarized'
NPN_S, NPN_P = 'Transistor_BJT:BC547', 'Transistor_BJT:BC337'
SCHOTTKY, DIODE = 'Device:D_Schottky', 'Device:D'
RELAY = 'Relay:Panasonic_ALFG1PF121'
CONN = lambda n: 'Connector_Generic:Conn_01x%02d' % n
SCREW2 = 'Connector:Screw_Terminal_01x02'

# ---------------------------------------------------------------- footprints
FP_R = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
FP_C = 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
FP_TO92 = 'Package_TO_SOT_THT:TO-92_Inline_Wide'
FP_TO220 = 'Package_TO_SOT_THT:TO-220-3_Vertical'
FP_TO247 = 'Package_TO_SOT_THT:TO-247-3_Vertical'
FP_DO41 = 'Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal'
FP_DO35 = 'Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal'
FP_DO15 = 'Diode_THT:D_DO-15_P12.70mm_Horizontal'
FP_DO201 = 'Diode_THT:D_DO-201AD_P15.24mm_Horizontal'
FP_SOIC8 = 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
FP_DIP8, FP_DIP14 = 'Package_DIP:DIP-8_W7.62mm', 'Package_DIP:DIP-14_W7.62mm'
FP_RELAY = 'Relay_THT:Relay_SPST_Panasonic_ALFG_FormA_CircularHoles'
FP_RELAY2 = 'Relay_THT:Relay_DPDT_Finder_40.52'
FP_RELAY_S = 'Relay_THT:Relay_SPDT_SANYOU_SRD_Series_Form_C'
FP_SHUNT = 'Custom:R_Shunt_2512_Kelvin'
FP_LINK = 'Custom:WireLink_P10.16mm'
FP_HOLE = 'MountingHole:MountingHole_3.2mm_M3'
TB = lambda n: 'TerminalBlock:TerminalBlock_bornier-%d_P5.08mm' % n
TB_HC = 'Connector_Phoenix_GMSTB:PhoenixContact_GMSTBVA_2,5_2-G-7,62_1x02_P7.62mm_Vertical'
XH = lambda n: 'Connector_JST:JST_XH_B%dB-XH-A_1x%02d_P2.50mm_Vertical' % (n, n)
SOCK = lambda n: 'Connector_PinSocket_2.54mm:PinSocket_1x%02d_P2.54mm_Vertical' % n
PINH = lambda n: 'Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Vertical' % n
CP_FP = {'100uF 50V': 'Capacitor_THT:CP_Radial_D10.0mm_P5.00mm',
         '220uF 25V': 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm',
         '10uF 25V': 'Capacitor_THT:CP_Radial_D5.0mm_P2.50mm'}

# ---------------------------------------------------------------- sourcing keys (details in sourcing.py)
SHEETS = {}

def sheet(key, name, file, title, notes):
    SHEETS[key] = dict(name=name, file=file, title=title, notes=notes, parts=[])
    return SHEETS[key]['parts']

def part(ref, lib, val, nets, fp='', src=None, **kw):
    return dict(ref=ref, lib=lib, val=val, nets=nets, fp=fp, src=src, **kw)

def res(ref, val, a, b):
    return part(ref, R, val, {'1': a, '2': b}, FP_R, 'R')

def cap(ref, val, a, b):
    if val in CP_FP:
        return part(ref, CP, val, {'1': a, '2': b}, CP_FP[val], 'CP ' + val)
    return part(ref, C, val, {'1': a, '2': b}, FP_C, 'C')

def bjt(ref, lib, c, b, e):
    val = lib.split(':')[1]
    return part(ref, lib, val, {'1': c, '2': b, '3': e}, FP_TO92, val)

def diode(ref, lib, val, k, a, fp, src=None):
    return part(ref, lib, val, {'1': k, '2': a}, fp, src or val)

def hdr(ref, val, nets_list, fp, src=None):
    return part(ref, CONN(len(nets_list)), val, {str(i + 1): n for i, n in enumerate(nets_list)}, fp, src)

def flag(ref, net):
    return part(ref, 'power:PWR_FLAG', 'PWR_FLAG', {'1': net}, inbom=False)

def hole(ref):
    return part(ref, 'Mechanical:MountingHole', 'M3 mounting hole', {}, FP_HOLE)

# ============================================================ POWER
p = sheet('power', 'Power', 'power.kicad_sch', 'Power input, rails and safety switch', [
    'PSU: 30 V bench supply. Put a 5 A blade fuse in an inline holder in the + lead (off-board). D1 (TVS) clamps spikes; D2 conducts on reverse polarity and blows that fuse.',
    'J2: 12 V buck module (XL4016, 8 A) for Peltiers (~3 A), relays and fans. U1 (7805) makes +5 V for the comparators. +3V3 comes from the Blue Pill (MCU sheet).',
    'Two grounds: PGND carries power return currents, GND is the quiet signal ground. They are joined at ONE point, link JP201 next to the shunt (Cell_Relays sheet).',
    'Safety switch K4: +12V_SW (relay coils K1-K3 and the Peltier) is live only while FAULT_N is high. The comparator output SW_B (Protection sheet) lets Q1 hold K4 on.',
    'J4: bimetal thermostat (60 C, normally closed) on the load heatsink, in series with the K4 coil. It drops +12V_SW without any firmware.',
    'How it works / what to check: docs/SCHEMATIC_GUIDE.md section 1.',
])
p += [
    hdr('J1', 'PSU in 30V (+, -) via inline 5A fuse', ['VIN', 'PGND'], TB(2), 'TB2'),
    part('D1', 'Device:D_TVS', 'P6KE39CA (TVS)', {'1': 'VIN', '2': 'PGND'}, FP_DO15, 'P6KE39CA'),
    diode('D2', DIODE, '1N5408', 'VIN', 'PGND', FP_DO201),
    cap('C1', '100uF 50V', 'VIN', 'PGND'),
    hdr('J2', '12V buck XL4016: IN+ IN- OUT+ OUT-', ['VIN', 'PGND', '+12V', 'PGND'], TB(4), 'TB4'),
    cap('C2', '220uF 25V', '+12V', 'PGND'),
    part('U1', 'Regulator_Linear:L7805', 'L7805CV', {'1': '+12V', '2': 'GND', '3': '+5V'}, FP_TO220, 'L7805CV'),
    cap('C3', '100nF', '+12V', 'GND'),
    cap('C4', '10uF 25V', '+5V', 'GND'),
    hdr('J4', 'Thermostat 60C NC (on load heatsink)', ['+12V', 'TSTAT'], TB(2), 'TB2S'),
    part('K4', 'Relay:SANYOU_SRD_Form_C', 'SRD-12VDC-SL-C (safety)',
         {'5': 'TSTAT', '2': 'K4_COIL', '1': '+12V', '3': '+12V_SW', '4': 'NC'}, FP_RELAY_S, 'SRD-12VDC-SL-C'),
    diode('D3', SCHOTTKY, '1N5819', 'TSTAT', 'K4_COIL', FP_DO41),
    bjt('Q1', NPN_P, 'K4_COIL', 'K4_B', 'PGND'),
    res('R1', '2.2k', '+5V', 'SW_B'),
    res('R2', '2.2k', 'SW_B', 'K4_B'),
    res('R3', '4.7k', 'K4_B', 'PGND'),
    flag('#FLG01', 'GND'), flag('#FLG02', '+12V'), flag('#FLG03', '+5V'), flag('#FLG04', 'VIN'),
    flag('#FLG05', '+12V_SW'), flag('#FLG07', 'PGND'),
    hole('H1'), hole('H2'), hole('H3'), hole('H4'),
]

# ============================================================ CELL PATH + RELAYS
p = sheet('relays', 'Cell_Relays', 'relays.kicad_sch', 'Cell connection, shunt and relays K1/K2', [
    'Cell + lead: put a 15 A blade fuse in an inline holder close to the cell (off-board).',
    'R1: 10 mOhm 2512 shunt (Isabellenhuette CMS, 2.5 W) in the cell negative lead, so it measures BOTH charge and discharge. Pads 2/3 are Kelvin taps at the inner pad edges.',
    'JP1 is the single GND-PGND link (a wire link next to the shunt). Do not add another ground connection between the two nets.',
    'K1 (charger) and K2 (load): Panasonic ALFG2PF121, 12 V coil, 33 A, normally open. Coils run from +12V_SW, so any fault opens both.',
    'Interlock: Q3 holds K1 off while K2_EN is high and Q4 holds K2 off while K1_EN is high (both commanded = both off).',
    'Coil drivers Q1/Q2 are BC337 (bipolar) so a 3.3 V GPIO switches them fully. R3/R6 keep the relays off while the MCU boots.',
    'How it works / what to check: docs/SCHEMATIC_GUIDE.md section 2.',
])
p += [
    hdr('J5', 'Cell power to pocket (+, -) via inline 15A fuse', ['CELL_P', 'CELL_N'], TB_HC, 'TB762'),
    hdr('J6', 'Cell Kelvin sense (+, -)', ['SENSE_P', 'SENSE_N'], TB(2), 'TB2S'),
    part('R1', 'Device:R_Shunt', '10mR 1% 2.5W 2512', {'1': 'CELL_N', '2': 'ISNS_N', '3': 'ISNS_G', '4': 'PGND'}, FP_SHUNT, 'SHUNT'),
    part('JP1', 'Jumper:Jumper_2_Bridged', 'GND-PGND link (wire)', {'1': 'PGND', '2': 'GND'}, FP_LINK, 'WIRE'),
    part('K1', RELAY, 'ALFG2PF121 (charge)', {'A1': '+12V_SW', 'A2': 'K1_COIL', '11': 'CHG_OUT', '14': 'CELL_P'}, FP_RELAY, 'ALFG2PF121'),
    part('K2', RELAY, 'ALFG2PF121 (load)', {'A1': '+12V_SW', 'A2': 'K2_COIL', '11': 'CELL_P', '14': 'LOAD_P'}, FP_RELAY, 'ALFG2PF121'),
    diode('D1', SCHOTTKY, '1N5819', '+12V_SW', 'K1_COIL', FP_DO41),
    diode('D2', SCHOTTKY, '1N5819', '+12V_SW', 'K2_COIL', FP_DO41),
    bjt('Q1', NPN_P, 'K1_COIL', 'K1_B', 'GND'),
    bjt('Q2', NPN_P, 'K2_COIL', 'K2_B', 'GND'),
    res('R2', '1k', 'K1_EN', 'K1_B'),
    res('R3', '10k', 'K1_EN', 'GND'),
    res('R4', '10k', 'K2_EN', 'K1_IB'),
    bjt('Q3', NPN_S, 'K1_B', 'K1_IB', 'GND'),
    res('R5', '1k', 'K2_EN', 'K2_B'),
    res('R6', '10k', 'K2_EN', 'GND'),
    res('R7', '10k', 'K1_EN', 'K2_IB'),
    bjt('Q4', NPN_S, 'K2_B', 'K2_IB', 'GND'),
]

# ============================================================ ELECTRONIC LOAD
p = sheet('load', 'Electronic_Load', 'load.kicad_sch', 'Electronic load 0-10 A (linear, CC)', [
    'Setpoint: PWM from PA6 (TIM3_CH1), filtered by R1/C1 and R2/C2, divided by R3/R4: SETP = PWM x 3.3 V / 27.8 = 0-119 mV.',
    'CC loop: INP = (SETP - I x 10 mOhm)/2. U1A integrates (R7, C4) until INP equals INN, so I = (SETP - 2 x INN)/10 mOhm. R8 biases INN by +2.5 mV, so PWM = 0 always means zero current.',
    'Full scale about 11.3 A (firmware limits to 10 A). Q1 IRFP260N works in linear mode on the heatsink; the external 0.1 Ohm 50 W resistor (J1) shares the heat.',
    'Load off: LOAD_OFF is pulled up to +5 V (R10) and lifts INN to 0.4 V through D1/R9, so the op-amp output goes to 0 V. The MCU pulls PB14 low (open drain) to enable the load.',
    'Hardware fault: K4_COIL rises to 12 V when the safety switch drops, and lifts INN through D2/R11. K2 opens a few ms later.',
    'U1B: current monitor I_MON = 1.707 V + 0.12 V/A (discharge positive), for the MCU ADC (PA0), the OC comparators and the charger current limit.',
    'U1 = OPA2171 (SOIC-8, soldered on the copper side). R19/C6/C7 filter the op-amp supply +12VA (also feeds U401). How it works / what to check: docs/SCHEMATIC_GUIDE.md section 3.',
])
p += [
    hdr('J1', 'Series R 0.1R 50W alu (off-board)', ['LOAD_P', 'LOAD_D'], TB_HC, 'TB762'),
    part('Q1', 'Device:Q_NMOS_GDS', 'IRFP260N', {'1': 'GATE', '2': 'LOAD_D', '3': 'PGND'}, FP_TO247, 'IRFP260N'),
    res('R1', '10k', 'PWM_L', 'DL1'),
    cap('C1', '1uF', 'DL1', 'GND'),
    res('R2', '10k', 'DL1', 'DAC_L'),
    cap('C2', '1uF', 'DAC_L', 'GND'),
    res('R3', '6.8k', 'DAC_L', 'SETP'),
    res('R4', '1k', 'SETP', 'ISNS_G'),
    cap('C3', '100nF', 'SETP', 'ISNS_G'),
    res('R5', '10k', 'SETP', 'INP'),
    res('R6', '10k', 'ISNS_N', 'INP'),
    part('U1', 'Device:Opamp_Dual', 'OPA2171AIDR', {'3': 'INP', '2': 'INN', '1': 'OA_OUT'}, FP_SOIC8, 'OPA2171', unit=1),
    res('R7', '10k', 'INN', 'ISNS_G'),
    cap('C4', '1nF', 'INN', 'OA_OUT'),
    res('R8', '10M', 'VREF', 'INN'),
    res('R9', '100k', 'LOAD_OFF', 'LOFF_K'),
    diode('D1', DIODE, '1N4148', 'INN', 'LOFF_K', FP_DO35),
    res('R10', '10k', '+5V', 'LOAD_OFF'),
    res('R11', '150k', 'K4_COIL', 'FLT_K'),
    diode('D2', DIODE, '1N4148', 'INN', 'FLT_K', FP_DO35),
    res('R12', '100R', 'OA_OUT', 'GATE'),
    res('R13', '10k', 'GATE', 'GND'),
    part('U1', 'Device:Opamp_Dual', 'OPA2171AIDR', {'5': 'MB', '6': 'MN', '7': 'MON_RAW'}, FP_SOIC8, 'OPA2171', unit=2),
    res('R14', '1k', 'ISNS_N', 'MN'),
    res('R15', '12k', 'MN', 'MON_RAW'),
    res('R16', '18k', 'VREF', 'MB'),
    res('R17', '1k', 'MB', 'ISNS_G'),
    res('R18', '1k', 'MON_RAW', 'I_MON'),
    diode('D3', SCHOTTKY, 'BAT85', '+3V3', 'I_MON', FP_DO35),
    diode('D4', SCHOTTKY, 'BAT85', 'I_MON', 'GND', FP_DO35),
    cap('C5', '10nF', 'I_MON', 'GND'),
    part('U1', 'Device:Opamp_Dual', 'OPA2171AIDR', {'8': '+12VA', '4': 'GND'}, FP_SOIC8, 'OPA2171', unit=3),
    res('R19', '100R', '+12V', '+12VA'),
    cap('C6', '100nF', '+12VA', 'GND'),
    cap('C7', '10uF 25V', '+12VA', 'GND'),
]

# ============================================================ CHARGER
p = sheet('charger', 'Charger', 'charger.kicad_sch', 'Charger: XL4016 CC/CV module, voltage and current set by the MCU', [
    'Set the module CV pot to 4.25 V with no load BEFORE wiring the FB tap, and turn its CC pot fully up. 4.25 V is the hardware ceiling: both loops below can only LOWER the output.',
    'Voltage (CV): PWM from PA7, filtered by R1/C1, R2/C2, injects current into the XL4016 FB pin (1.25 V) through D1. PWM = 0 gives the ceiling; more PWM gives less voltage.',
    'Current (CC): U1A compares I_MON with ILIM and, when the charge current is above the limit, injects into FB through R5/D2. This is a hardware current limit (review item C-01).',
    'ILIM: PWM from PB0 through R6, with R7 to +3V3. PB0 high-Z (reset) = 3.3 V = zero current allowed. PWM 0 % = 5.6 A, 30 % = 0 A.',
    'U1B buffers SENSE_P (V_CELL), so the protection dividers and V_FAST do not load the cell (review item M-04). R9 makes "no cell" read 0 V.',
    'Firmware still matches the module voltage to the cell before closing K1, then raises voltage and current targets. How it works: docs/SCHEMATIC_GUIDE.md section 4.',
])
p += [
    hdr('J1', 'XL4016 CC/CV module: IN+ IN- OUT+ OUT-', ['VIN', 'PGND', 'CHG_OUT', 'PGND'], TB(4), 'TB4'),
    hdr('J2', 'XL4016 FB tap (pin 1 to the FB pin; pin 2 spare GND)', ['XL_FB', 'GND'], TB(2), 'TB2S'),
    res('R1', '560R', 'PWM_C', 'DC1'),
    cap('C1', '10uF 25V', 'DC1', 'GND'),
    res('R2', '560R', 'DC1', 'DAC_C'),
    cap('C2', '10uF 25V', 'DAC_C', 'GND'),
    diode('D1', SCHOTTKY, 'BAT85', 'XL_FB', 'DAC_C', FP_DO35),
    part('U1', 'Device:Opamp_Dual', 'LM358P', {'3': 'ILIM', '2': 'CCN', '1': 'CC_OUT'}, FP_DIP8, 'LM358P', unit=1),
    res('R4', '15k', 'I_MON', 'CCN'),
    cap('C3', '100nF', 'CCN', 'CC_OUT'),
    res('R5', '3.3k', 'CC_OUT', 'CC_INJ'),
    diode('D2', SCHOTTKY, 'BAT85', 'XL_FB', 'CC_INJ', FP_DO35),
    res('R6', '10k', 'PWM_I', 'ILIM'),
    res('R7', '22k', '+3V3', 'ILIM'),
    cap('C4', '10uF 25V', 'ILIM', 'GND'),
    part('U1', 'Device:Opamp_Dual', 'LM358P', {'5': 'SBUF', '6': 'V_CELL', '7': 'V_CELL'}, FP_DIP8, 'LM358P', unit=2),
    res('R8', '10k', 'SENSE_P', 'SBUF'),
    res('R9', '1M', 'SBUF', 'GND'),
    cap('C5', '10nF', 'SBUF', 'GND'),
    part('U1', 'Device:Opamp_Dual', 'LM358P', {'8': '+12VA', '4': 'GND'}, FP_DIP8, 'LM358P', unit=3),
    cap('C6', '100nF', '+12VA', 'GND'),
]

# ============================================================ MEASUREMENT
p = sheet('meas', 'Measurement', 'measurement.kicad_sch', 'Measurement: ADS1115, NTCs, fast voltage', [
    'ADS1115 module (0x48): A0-A1 differential = shunt (current, +-256 mV range, 0.8 mA per bit), A2-A3 differential = cell voltage / 2 (Kelvin, +-2.048 V range).',
    'R3/R4 set the voltage accuracy. With 1 % parts, calibrate once against a DMM (two points) and store the gain in firmware.',
    'Four NTCs (10k, 10k pull-up to +3V3) go to the MCU ADC (PA2-PA5): cell surface, pocket air, load heatsink, Peltier hot side. NTC_HS and NTC_CELL also feed the OT comparators.',
    'V_FAST: buffered cell voltage / 2 for the MCU ADC (PA1), for the fast voltage step at a current edge (R0). It is ground-referenced: subtract I x 10 mOhm in firmware.',
    'How it works / what to check: docs/SCHEMATIC_GUIDE.md section 5.',
])
p += [
    hdr('U1', 'ADS1115 module (ADDR=GND): VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3',
        ['+3V3', 'GND', 'SCL', 'SDA', 'GND', 'NC', 'ADC_IG', 'ADC_IN', 'ADC_VP', 'ADC_VN'], SOCK(10), 'ADS1115'),
    res('R1', '100R', 'ISNS_G', 'ADC_IG'),
    res('R2', '100R', 'ISNS_N', 'ADC_IN'),
    cap('C1', '100nF', 'ADC_IG', 'ADC_IN'),
    res('R3', '10k', 'SENSE_P', 'ADC_VP'),
    res('R4', '10k', 'ADC_VP', 'ADC_VN'),
    res('R5', '100R', 'SENSE_N', 'ADC_VN'),
    cap('C2', '100nF', 'ADC_VP', 'ADC_VN'),
]
for i, n in enumerate(['NTC_CELL', 'NTC_AIR', 'NTC_HS', 'NTC_TEC']):
    p += [res('R%d' % (6 + i), '10k', '+3V3', n),
          cap('C%d' % (3 + i), '100nF', n, 'GND'),
          hdr('J%d' % (1 + i), 'NTC 10k ' + n.split('_')[1].lower(), [n, 'GND'], TB(2), 'TB2S')]
p += [
    res('R10', '10k', 'V_CELL', 'V_FAST'),
    res('R11', '10k', 'V_FAST', 'GND'),
    cap('C7', '10nF', 'V_FAST', 'GND'),
]

# ============================================================ PROTECTION
p = sheet('prot', 'Protection', 'protection.kicad_sch', 'Hardware protection (independent of firmware), latched', [
    'VREF = 2.495 V from TL431 (U3). C1 must be 10 uF: a TL431 can oscillate with 10 nF - 3 uF on its output.',
    'Six trips pull FAULT_N low (open-collector, wired-OR): OV cell > 4.33 V | UV cell < 1.96 V | discharge > 11.6 A | charge > 6.2 A | heatsink or cell NTC > about 62 C.',
    'Latch (U2C): once FAULT_N has been low for about 1 ms it is held low. The MCU re-arms by driving ARM (PB10) high for a moment, and can force a trip by driving ARM low. Normally ARM is high-Z.',
    'Power-up state is "tripped": FAULT_N low, K4 off, +12V_SW dead, load off. Nothing moves until the firmware arms the bench. No USB (no +3V3) also means tripped.',
    'U2D turns FAULT_N into SW_B, which drives the safety switch K4 (Power sheet). UV also trips with no cell inserted.',
    'How it works / what to check: docs/SCHEMATIC_GUIDE.md section 6.',
])
p += [
    res('R1', '1k', '+5V', 'VREF'),
    part('U3', 'Reference_Voltage:TL431LP', 'TL431 (TO-92)', {'1': 'VREF', '2': 'GND', '3': 'VREF'}, FP_TO92, 'TL431'),
    cap('C1', '10uF 25V', 'VREF', 'GND'),
    res('R2', '10k', 'VREF', 'VREF_H'),
    res('R3', '10k', 'VREF_H', 'GND'),
    res('R4', '16k', 'VREF', 'VREF_C'),
    res('R5', '10k', 'VREF_C', 'GND'),
    res('R6', '27k', 'VREF', 'VREF_T'),
    res('R7', '9.1k', 'VREF_T', 'GND'),
    res('R8', '11k', 'V_CELL', 'OV_DIV'),
    res('R9', '15k', 'OV_DIV', 'GND'),
    part('U1', 'Comparator:LM339', 'LM339N', {'5': 'VREF', '4': 'OV_DIV', '2': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=1),
    res('R10', '9.1k', 'V_CELL', 'UV_DIV'),
    res('R11', '16k', 'UV_DIV', 'GND'),
    part('U1', 'Comparator:LM339', 'LM339N', {'7': 'UV_DIV', '6': 'VREF_H', '1': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=2),
    res('R12', '24k', 'I_MON', 'ID_DIV'),
    res('R13', '100k', 'ID_DIV', 'GND'),
    part('U1', 'Comparator:LM339', 'LM339N', {'11': 'VREF', '10': 'ID_DIV', '13': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=3),
    part('U1', 'Comparator:LM339', 'LM339N', {'9': 'I_MON', '8': 'VREF_C', '14': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=4),
    part('U1', 'Comparator:LM339', 'LM339N', {'3': '+5V', '12': 'GND'}, FP_DIP14, 'LM339N', unit=5),
    cap('C2', '100nF', '+5V', 'GND'),
    part('U2', 'Comparator:LM339', 'LM339N', {'5': 'NTC_HS', '4': 'VREF_T', '2': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=1),
    part('U2', 'Comparator:LM339', 'LM339N', {'7': 'NTC_CELL', '6': 'VREF_T', '1': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=2),
    part('U2', 'Comparator:LM339', 'LM339N', {'11': 'LATCH_IN', '10': 'VREF_H', '13': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=3),
    part('U2', 'Comparator:LM339', 'LM339N', {'9': 'FAULT_N', '8': 'VREF_H', '14': 'SW_B'}, FP_DIP14, 'LM339N', unit=4),
    part('U2', 'Comparator:LM339', 'LM339N', {'3': '+5V', '12': 'GND'}, FP_DIP14, 'LM339N', unit=5),
    cap('C3', '100nF', '+5V', 'GND'),
    res('R14', '100k', 'FAULT_N', 'LATCH_IN'),
    res('R15', '10k', 'ARM', 'LATCH_IN'),
    cap('C4', '10nF', 'LATCH_IN', 'GND'),
    res('R16', '10k', '+3V3', 'FAULT_N'),
]

# ============================================================ THERMAL
p = sheet('thermal', 'Thermal', 'thermal.kicad_sch', 'Peltier driver and fans', [
    'Two TEC1-12706 Peltiers in series on J2 (about 6 V / 3 A each). Q3 (IRLZ44N, logic level) switches them with PWM from PB8 (TIM4_CH3).',
    'K3 swaps the polarity: relaxed = cool the pocket, energised (TEC_DIR, PB9) = heat. Firmware sets PWM to 0 before it toggles K3.',
    'Peltier and K3 run from +12V_SW, so any fault (or the thermostat) switches the Peltiers off. This replaces the BTS7960 module (cheaper, and no 3.3 V logic problem).',
    'Q2 (BC337) switches both 12 V heatsink fans with PWM from PA8. J5 is the always-on 12 V pocket mixing fan.',
    'How it works / what to check: docs/SCHEMATIC_GUIDE.md section 7.',
])
p += [
    hdr('J2', 'Peltier 2x TEC1-12706 in series (A, B)', ['TEC_A', 'TEC_B'], TB(2), 'TB2'),
    part('K3', 'Relay:FINDER-40.52', 'HK14FD-DC12V-SHG (DPDT, polarity)',
         {'A1': '+12V_SW', 'A2': 'K3_COIL', '11': 'TEC_A', '12': '+12V_SW', '14': 'TEC_SW',
          '21': 'TEC_B', '22': 'TEC_SW', '24': '+12V_SW'}, FP_RELAY2, 'HK14FD'),
    diode('D1', SCHOTTKY, '1N5819', '+12V_SW', 'K3_COIL', FP_DO41),
    bjt('Q1', NPN_P, 'K3_COIL', 'K3_B', 'PGND'),
    res('R1', '1k', 'TEC_DIR', 'K3_B'),
    res('R2', '10k', 'TEC_DIR', 'GND'),
    part('Q3', 'Transistor_FET:IRLZ44N', 'IRLZ44N', {'1': 'TEC_G', '2': 'TEC_SW', '3': 'PGND'}, FP_TO220, 'IRLZ44N'),
    res('R3', '100R', 'TEC_PWM', 'TEC_G'),
    res('R4', '10k', 'TEC_G', 'PGND'),
    diode('D2', SCHOTTKY, '1N5819', '+12V_SW', 'TEC_SW', FP_DO41),
    bjt('Q2', NPN_P, 'FAN_N', 'FAN_B', 'PGND'),
    res('R5', '470R', 'FAN_PWM', 'FAN_B'),
    res('R6', '10k', 'FAN_PWM', 'GND'),
    diode('D3', SCHOTTKY, '1N5819', '+12V', 'FAN_N', FP_DO41),
    hdr('J4', 'Fan 12V load heatsink (+,-)', ['+12V', 'FAN_N'], TB(2), 'TB2S'),
    hdr('J6', 'Fan 12V Peltier hot side (+,-)', ['+12V', 'FAN_N'], TB(2), 'TB2S'),
    hdr('J5', 'Pocket mixing fan 12V (+,-)', ['+12V', 'PGND'], TB(2), 'TB2S'),
]

# ============================================================ MCU
p = sheet('mcu', 'MCU', 'mcu.kicad_sch', 'Blue Pill (STM32F103C8) and interfaces', [
    'Blue Pill plugs into two 1x20 female headers, 15.24 mm (0.6 in) apart. USB goes to the PC (USB CDC for the Python UI) and also powers the Blue Pill.',
    'JP1 is normally OPEN: the Blue Pill 5V pin is wired straight to USB VBUS, so the board must not feed it while a PC is connected (review item U-01). Close JP1 only to run without USB.',
    'ADC: PA0 I_MON, PA1 V_FAST, PA2-PA5 NTCs. PWM "DACs": PA6 load setpoint, PA7 charger voltage, PB0 charger current limit (TIM3). PA8 fans (TIM1). PB8 Peltier PWM (TIM4), PB9 Peltier direction.',
    'PB6/PB7 I2C1 (ADS1115 0x48). PB12 K1_EN, PB13 K2_EN. PB14 LOAD_OFF (open drain, 5 V pull-up, low = load on). PB15 FAULT_N (input). PB10 ARM (high-Z; pulse high = arm, low = trip).',
    'How it works / what to check: docs/SCHEMATIC_GUIDE.md section 8.',
])
p += [
    hdr('J1', 'Blue Pill header A: B12 B13 B14 B15 A8 A9 A10 A11 A12 A15 B3 B4 B5 B6 B7 B8 B9 5V GND 3V3',
        ['K1_EN', 'K2_EN', 'LOAD_OFF', 'FAULT_N', 'FAN_PWM', 'DBG_TX', 'DBG_RX', 'NC', 'NC', 'NC',
         'NC', 'NC', 'NC', 'SCL', 'SDA', 'TEC_PWM', 'TEC_DIR', 'BP_5V', 'GND', '+3V3'], SOCK(20), 'SOCK'),
    hdr('J2', 'Blue Pill header B: VB C13 C14 C15 A0 A1 A2 A3 A4 A5 A6 A7 B0 B1 B10 B11 RST 3V3 GND GND',
        ['NC', 'NC', 'NC', 'NC', 'I_MON', 'V_FAST', 'NTC_CELL', 'NTC_AIR', 'NTC_HS', 'NTC_TEC', 'PWM_L', 'PWM_C',
         'PWM_I', 'NC', 'ARM', 'NC', 'NC', '+3V3', 'GND', 'GND'], SOCK(20), 'SOCK'),
    hdr('JP1', 'Board 5V to Blue Pill (normally open)', ['+5V', 'BP_J'], PINH(2), 'PINH'),
    diode('D1', SCHOTTKY, '1N5819', 'BP_5V', 'BP_J', FP_DO41),
    hdr('J3', 'Debug UART: TX RX GND', ['DBG_TX', 'DBG_RX', 'GND'], PINH(3), 'PINH'),
    cap('C1', '10uF 25V', '+3V3', 'GND'),
    flag('#FLG06', '+3V3'),
]

# ============================================================ BUILD
ORDER = ['power', 'relays', 'load', 'charger', 'meas', 'prot', 'thermal', 'mcu']
PREFIX = {'power': 1, 'relays': 2, 'load': 3, 'charger': 4, 'meas': 5, 'prot': 6, 'thermal': 7, 'mcu': 8}
# nets that are power nets in the PCB sense (wide tracks), with their design current in A
CURRENT = {'CELL_P': 11, 'CELL_N': 11, 'LOAD_P': 11, 'LOAD_D': 11, 'PGND': 11, 'CHG_OUT': 6,
           'VIN': 3, '+12V': 4, '+12V_SW': 3.5, 'TEC_A': 3, 'TEC_B': 3, 'TEC_SW': 3, '+5V': 0.3, '+3V3': 0.1,
           'FAN_N': 0.4}

def refname(k, ref):
    if ref.startswith('#') or ref[0] == 'K':
        return ref
    m = re.match(r'([A-Z]+)(\d+)', ref)
    return m.group(1) + str(PREFIX[k]) + '%02d' % int(m.group(2))

def lib_fp(fp):
    return 'cell_bench:' + fp.split(':')[1] if fp else ''

def all_parts():
    for k in ORDER:
        for pt in SHEETS[k]['parts']:
            yield k, refname(k, pt['ref']), pt

def build(outdir):
    D = K.Design()
    seen, count = {}, {}
    for k, ref, pt in all_parts():
        for n in pt['nets'].values():
            seen.setdefault(n, set()).add(k)
            count[n] = count.get(n, 0) + 1
    D.globals = {n for n, ks in seen.items() if len(ks) > 1 and n not in K.POWER_NETS and n != 'NC'}
    lonely = [n for n, c in count.items() if c < 2 and n != 'NC']
    if lonely:
        raise SystemExit('single-connection nets: %s' % lonely)
    for k, ref, pt in all_parts():
        if not ref.startswith('#') and not pt['fp']:
            raise SystemExit('no footprint: ' + ref)
    for k in ORDER:
        S = SHEETS[k]
        s = D.sheet(S['name'], S['file'], S['title'])
        cols = 6
        for i, pt in enumerate(S['parts']):
            ref = refname(k, pt['ref'])
            fields = {'Footprint': lib_fp(pt['fp'])}
            col, row = i % cols, i // cols
            x, y = 35 + col * 62, 40 + row * 34
            K.comp(D, s, pt['lib'], ref, pt['val'], x, y, pt['nets'], unit=pt.get('unit', 1), fields=fields)
        rows = (len(S['parts']) + cols - 1) // cols
        ny = 40 + rows * 34 + 2
        for j, line in enumerate(S['notes']):
            line = re.sub(r'\b(JP|[RCQDUJFH])(\d{1,2})(?=[A-D]?\b)',
                          lambda m: m.group(1) + str(PREFIX[k]) + '%02d' % int(m.group(2)), line)
            K.text(s, line, 25, ny + j * 4.5, 1.27)
    K.text(D.root, 'Cell test bench - schematic v%s. One 18650/21700 cell at a time; 0-10 A load, <=5 A charge, Peltier-controlled cell pocket.' % REV, 30, 30, 2)
    K.text(D.root, 'Inter-sheet connections use global labels. Power nets: GND (signal), PGND (power return), +12V, +5V, +3V3 (Blue Pill), VIN (30 V), +12V_SW (after safety switch K4).', 30, 38, 1.5)
    K.text(D.root, 'Single-sided board for in-house CNC milling. Explanation of every block: docs/SCHEMATIC_GUIDE.md.', 30, 44, 1.5)
    K.write_all(D, outdir)
    return D

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'out')
