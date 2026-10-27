"""Cell test bench - schematic v0.2 (generated, footprints assigned).
Run: python3 design.py <outdir>"""
import sys, re
import kigen as K
import libs

R, C, CP = 'Device:R', 'Device:C', 'Device:C_Polarized'
BS170, IRLZ44N = 'Transistor_FET:BS170', 'Transistor_FET:IRLZ44N'
SCHOTTKY, DIODE = 'Device:D_Schottky', 'Device:D'
RELAY = 'Relay:Panasonic_ALFG1PF121'
CONN = lambda n: 'Connector_Generic:Conn_01x%02d' % n
SCREW2 = 'Connector:Screw_Terminal_01x02'

# ---------------------------------------------------------------- footprints
FP_R = 'Resistor_SMD:R_1206_3216Metric'
FP_C = 'Capacitor_SMD:C_1206_3216Metric'
FP_TO92 = 'Package_TO_SOT_THT:TO-92_Inline_Wide'
FP_TO220 = 'Package_TO_SOT_THT:TO-220-3_Vertical'
FP_TO247 = 'Package_TO_SOT_THT:TO-247-3_Vertical'
FP_DO41 = 'Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal'
FP_DO35 = 'Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal'
FP_DO15 = 'Diode_THT:D_DO-15_P10.16mm_Horizontal'
FP_SOIC8 = 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
FP_DIP8, FP_DIP14 = 'Package_DIP:DIP-8_W7.62mm', 'Package_DIP:DIP-14_W7.62mm'
FP_FUSE = 'Fuse:Fuseholder_Blade_Mini_Keystone_3568'
FP_RELAY = 'Relay_THT:Relay_SPST_Panasonic_ALFG_FormA'
FP_SHUNT = 'Resistor_SMD:R_Shunt_Ohmite_LVK25'
FP_HOLE = 'MountingHole:MountingHole_3.2mm_M3'
TB = lambda n, big=False: ('TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-%s-%d-5.08_1x%02d_P5.08mm_Horizontal'
                           % ('3' if big else '1,5', n, n))
XH = lambda n: 'Connector_JST:JST_XH_B%dB-XH-A_1x%02d_P2.50mm_Vertical' % (n, n)
SOCK = lambda n: 'Connector_PinSocket_2.54mm:PinSocket_1x%02d_P2.54mm_Vertical' % n
PINH = lambda n: 'Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Vertical' % n
CP_FP = {'100uF 50V': 'Capacitor_THT:CP_Radial_D10.0mm_P5.00mm',
         '220uF 25V': 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm',
         '100uF 16V': 'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm'}

# ---------------------------------------------------------------- sourcing (Ozdisan first)
OZ = 'https://www.ozdisan.com/en/p/'
SRC = {
    'OPA2188': ('OPA2188AID', OZ + 'amplifiers-242/texas-opa2188aid-1587851', 'Ozdisan (request price; alt OPA2187IDR)'),
    'IRFP260N': ('IRFP260NPBF', OZ + 'discrete-mosfets-435/infineon-irfp260npbf-3517', 'Ozdisan'),
    'BS170': ('BS170', OZ + 'discrete-mosfets-435/ons-fairchild-bs170-12618', 'Ozdisan'),
    'IRLZ44N': ('IRLZ44NPBF', '', 'Direnc.net / Robotistan'),
    'LM339N': ('LM339N', OZ + 'analog-comparators-243/stm-lm339n-11869', 'Ozdisan'),
    'LM393N': ('LM393N', OZ + 'analog-comparators-243/stm-lm393n-6186', 'Ozdisan'),
    'TL431': ('TL431ACLPR', OZ + 'voltage-reference-ics-287/texas-tl431aclpr-590085', 'Ozdisan'),
    '1N4007': ('1N4007-E3/54', OZ + 'rectifier-diodes-389/vishay-1n4007-e3-54-339764', 'Ozdisan'),
    'BAT85': ('BAT85,113', OZ + 'schottky-diodes-385/nxp-bat85-113-833131', 'Ozdisan'),
    '1N5819': ('1N5819', OZ + 'schottky-diodes-385/oem-1n5819-oem-1006', 'Ozdisan'),
    'P6KE33A': ('P6KE33A', OZ + 'tvs-diodes-386/vishay-p6ke33a-432173', 'Ozdisan'),
    'ALFG2PF121': ('ALFG2PF121', 'https://ozdisan.com/elektromekanik-komponentler/roleler-ve-role-soketleri/genel-tip-roleler/ALFG2PF121/462930', 'Ozdisan (33 A, 12 V coil)'),
    'LVK25': ('LVK25R010FER', 'https://www.digikey.com/en/products/detail/ohmite/LVK25R010FER/1632761', 'DigiKey (not found at Ozdisan)'),
    'FUSEHOLDER': ('Keystone 3568', 'https://www.digikey.com/en/products/detail/keystone-electronics/3568/2137306', 'DigiKey; mini blade fuse holder, 30 A'),
}

SHEETS = {}

def sheet(key, name, file, title, notes):
    SHEETS[key] = dict(name=name, file=file, title=title, notes=notes, parts=[])
    return SHEETS[key]['parts']

def part(ref, lib, val, nets, fp='', src=None, **kw):
    return dict(ref=ref, lib=lib, val=val, nets=nets, fp=fp, src=src, **kw)

def res(ref, val, a, b):
    return part(ref, R, val, {'1': a, '2': b}, FP_R)

def cap(ref, val, a, b):
    if val in CP_FP:
        return part(ref, CP, val, {'1': a, '2': b}, CP_FP[val])
    return part(ref, C, val, {'1': a, '2': b}, FP_C)

def fet(ref, lib, val, g, d, s, fp, src):
    by = {p['name']: p['number'] for p in libs.pins(libs.get(lib))}
    return part(ref, lib, val, {by['G']: g, by['D']: d, by['S']: s}, fp, src)

def diode(ref, lib, val, k, a, fp, src=None):
    return part(ref, lib, val, {'1': k, '2': a}, fp, src)

def hdr(ref, val, nets_list, fp):
    return part(ref, CONN(len(nets_list)), val, {str(i + 1): n for i, n in enumerate(nets_list)}, fp)

def flag(ref, net):
    return part(ref, 'power:PWR_FLAG', 'PWR_FLAG', {'1': net}, inbom=False)

def hole(ref):
    return part(ref, 'Mechanical:MountingHole', 'M3 mounting hole', {}, FP_HOLE)

# ============================================================ POWER
p = sheet('power', 'Power', 'power.kicad_sch', 'Power input and rails', [
    'PSU: existing 30 V / 10 A bench supply, no CC/CV. F1 + D1 (TVS) protect against overvoltage and reverse polarity (D1 conducts, F1 blows).',
    'J2: 12 V buck module XL4016 (8 A) for Peltiers (~3 A), relays and fans.   J3: 5 V buck module (MP1584) for Blue Pill, comparators and BTS7960 logic.',
    '+3V3 comes from the Blue Pill regulator (MCU sheet).',
    'J4: bimetal thermostat KSD9700, normally closed, 60 C, mounted on the load heatsink. It cuts +12V_SW (relay coils + Peltier driver) independently of firmware.',
    'Fuses: mini blade (ATM) fuses in Keystone 3568 PCB holders. H1-H4: M3 mounting holes.',
])
p += [
    part('J1', SCREW2, 'PSU in 30V 10A (+, -)', {'1': 'VIN_RAW', '2': 'GND'}, TB(2, True)),
    part('F1', 'Device:Fuse', '10A mini blade', {'1': 'VIN_RAW', '2': 'VIN'}, FP_FUSE, 'FUSEHOLDER'),
    diode('D1', DIODE, 'P6KE33A (TVS)', 'VIN', 'GND', FP_DO15, 'P6KE33A'),
    cap('C1', '100uF 50V', 'VIN', 'GND'),
    hdr('J2', '12V buck XL4016: IN+ IN- OUT+ OUT-', ['VIN', 'GND', '+12V', 'GND'], TB(4)),
    cap('C2', '220uF 25V', '+12V', 'GND'),
    hdr('J3', '5V buck MP1584: IN+ IN- OUT+ OUT-', ['+12V', 'GND', '+5V', 'GND'], TB(4)),
    cap('C3', '100uF 16V', '+5V', 'GND'),
    hdr('J4', 'Thermostat KSD9700 60C NC', ['+12V', '+12V_SW'], TB(2)),
    cap('C4', '220uF 25V', '+12V_SW', 'GND'),
    flag('#FLG01', 'GND'), flag('#FLG02', '+12V'), flag('#FLG03', '+5V'), flag('#FLG04', 'VIN'), flag('#FLG05', '+12V_SW'),
    hole('H1'), hole('H2'), hole('H3'), hole('H4'),
]

# ============================================================ CELL PATH + RELAYS
p = sheet('relays', 'Cell_Relays', 'relays.kicad_sch', 'Cell connection, shunt and relays K1/K2', [
    'Single 10 mOhm 4-terminal shunt R1 (Ohmite LVK25, 2 W) sits in the cell negative lead, so it measures BOTH charge and discharge current. System GND = shunt ground side (star point).',
    'Kelvin sense: ISNS_N / ISNS_G from the shunt sense pads, SENSE_P / SENSE_N from separate wires at the cell tabs (J6).',
    'K1 (charger) and K2 (load): Panasonic ALFG2PF121 PCB power relays, 12 V coil, 33 A, normally open.',
    'Interlock: Q3 holds K1 off while K2_EN is high, Q4 holds K2 off while K1_EN is high (both commanded = both off). Q5/Q6 drop both relays on FAULT.',
    'R4/R7 pull-downs keep both relays off while the MCU boots. Q1/Q2: BS170 (TO-92) coil drivers, coil ~150 mA.',
])
p += [
    part('J5', SCREW2, 'Cell power to pocket (+, -)', {'1': 'CELL_P_RAW', '2': 'CELL_N'}, TB(2, True)),
    hdr('J6', 'Cell Kelvin sense (+, -)', ['SENSE_P', 'SENSE_N'], XH(2)),
    part('F2', 'Device:Fuse', '15A mini blade (cell)', {'1': 'CELL_P_RAW', '2': 'CELL_P'}, FP_FUSE, 'FUSEHOLDER'),
    part('R1', 'Device:R_Shunt', '10mR 1% 2W LVK25', {'1': 'CELL_N', '2': 'ISNS_N', '3': 'ISNS_G', '4': 'GND'}, FP_SHUNT, 'LVK25'),
    part('K1', RELAY, 'ALFG2PF121 (charge)', {'A1': '+12V_SW', 'A2': 'K1_COIL', '11': 'CHG_OUT', '14': 'CELL_P'}, FP_RELAY, 'ALFG2PF121'),
    part('K2', RELAY, 'ALFG2PF121 (load)', {'A1': '+12V_SW', 'A2': 'K2_COIL', '11': 'CELL_P', '14': 'LOAD_P'}, FP_RELAY, 'ALFG2PF121'),
    diode('D1', DIODE, '1N4007', '+12V_SW', 'K1_COIL', FP_DO41, '1N4007'),
    diode('D2', DIODE, '1N4007', '+12V_SW', 'K2_COIL', FP_DO41, '1N4007'),
    fet('Q1', BS170, 'BS170', 'K1_G', 'K1_COIL', 'GND', FP_TO92, 'BS170'),
    fet('Q2', BS170, 'BS170', 'K2_G', 'K2_COIL', 'GND', FP_TO92, 'BS170'),
    res('R2', '1k', 'K1_EN', 'K1_G'),
    res('R3', '100k', 'K1_G', 'GND'),
    res('R4', '100k', 'K1_EN', 'GND'),
    res('R5', '1k', 'K2_EN', 'K2_G'),
    res('R6', '100k', 'K2_G', 'GND'),
    res('R7', '100k', 'K2_EN', 'GND'),
    fet('Q3', BS170, 'BS170', 'K2_EN', 'K1_G', 'GND', FP_TO92, 'BS170'),
    fet('Q4', BS170, 'BS170', 'K1_EN', 'K2_G', 'GND', FP_TO92, 'BS170'),
    fet('Q5', BS170, 'BS170', 'FAULT', 'K1_G', 'GND', FP_TO92, 'BS170'),
    fet('Q6', BS170, 'BS170', 'FAULT', 'K2_G', 'GND', FP_TO92, 'BS170'),
]

# ============================================================ ELECTRONIC LOAD
p = sheet('load', 'Electronic_Load', 'load.kicad_sch', 'Electronic load 0-10 A (linear, CC)', [
    'CC loop: U1A compares the DAC setpoint with the shunt voltage. Summing node INP = (SETP - I*Rshunt)/2, so the loop settles at I = SETP / 10 mOhm.',
    'Setpoint: MCP4725 #1 (0x60) 0-3.3 V, divided by R1/R2 to 0-108 mV -> 0-10.8 A full scale (~2.6 mA per LSB).',
    'Q1 IRFP260N (TO-247) in linear mode at the board edge, bolted to the CPU-cooler heatsink, with the external 0.1 Ohm 50 W aluminium resistor (J1) in series to share the heat.',
    'Kill: Q2 (LOAD_OFF from MCU, pulled up = off at boot) and Q3 (hardware FAULT) short INP to ground -> gate goes low.',
    'Sequence: close K2 with LOAD_OFF high, release LOAD_OFF with DAC = 0, then ramp the DAC.',
    'U1B: bidirectional current monitor for the fast internal ADC and the OC comparators: I_MON = 1.65 V + 0.12 V/A (approx -13 A ... +13 A).',
    'U1 = OPA2188AID (SOIC-8, zero-drift, 36 V). MCP4725 module pin order differs between sellers: check U2 before soldering the socket.',
])
p += [
    part('J1', SCREW2, 'Series R 0.1R 50W alu (off-board)', {'1': 'LOAD_P', '2': 'LOAD_D'}, TB(2, True)),
    part('Q1', 'Device:Q_NMOS_GDS', 'IRFP260N', {'1': 'GATE', '2': 'LOAD_D', '3': 'GND'}, FP_TO247, 'IRFP260N'),
    hdr('U2', 'MCP4725 module #1 (A0=GND, 0x60): VCC GND SCL SDA A0 OUT', ['+3V3', 'GND', 'SCL', 'SDA', 'GND', 'DAC_L'], SOCK(6)),
    res('R1', '29.4k 0.1%', 'DAC_L', 'SETP'),
    res('R2', '1k 0.1%', 'SETP', 'ISNS_G'),
    cap('C1', '10nF', 'SETP', 'ISNS_G'),
    res('R3', '10k 0.1%', 'SETP', 'INP'),
    res('R4', '10k 0.1%', 'ISNS_N', 'INP'),
    fet('Q2', BS170, 'BS170', 'LOAD_OFF', 'INP', 'GND', FP_TO92, 'BS170'),
    fet('Q3', BS170, 'BS170', 'FAULT', 'INP', 'GND', FP_TO92, 'BS170'),
    res('R5', '10k', '+3V3', 'LOAD_OFF'),
    part('U1', 'Device:Opamp_Dual', 'OPA2188AID', {'3': 'INP', '2': 'INN', '1': 'OA_OUT'}, FP_SOIC8, 'OPA2188', unit=1),
    res('R6', '10k', 'INN', 'ISNS_G'),
    cap('C2', '1nF', 'INN', 'OA_OUT'),
    res('R7', '100R', 'OA_OUT', 'GATE'),
    res('R8', '10k', 'GATE', 'GND'),
    part('U1', 'Device:Opamp_Dual', 'OPA2188AID', {'5': 'MB', '6': 'MN', '7': 'MON_RAW'}, FP_SOIC8, 'OPA2188', unit=2),
    res('R9', '1k 0.1%', 'ISNS_N', 'MN'),
    res('R10', '12k 0.1%', 'MN', 'MON_RAW'),
    res('R11', '24.9k', '+3V3', 'MB'),
    res('R12', '1k', 'MB', 'ISNS_G'),
    res('R13', '1k', 'MON_RAW', 'I_MON'),
    diode('D1', SCHOTTKY, 'BAT85', '+3V3', 'I_MON', FP_DO35, 'BAT85'),
    diode('D2', SCHOTTKY, 'BAT85', 'I_MON', 'GND', FP_DO35, 'BAT85'),
    cap('C3', '10nF', 'I_MON', 'GND'),
    part('U1', 'Device:Opamp_Dual', 'OPA2188AID', {'8': '+12V', '4': 'GND'}, FP_SOIC8, 'OPA2188', unit=3),
    cap('C4', '100nF', '+12V', 'GND'),
    cap('C5', '10uF', '+12V', 'GND'),
]

# ============================================================ CHARGER
p = sheet('charger', 'Charger', 'charger.kicad_sch', 'Charger: XL4016 CC/CV module with DAC-set voltage', [
    'Set the module CV pot to 4.25 V with no load BEFORE wiring the FB tap. That pot value is the hardware voltage ceiling.',
    'DAC #2 (0x61) injects current into the XL4016 FB pin (1.25 V) through D1 + R1. Injection can only LOWER the output, so DAC = 0 / MCU dead = 4.25 V ceiling, never higher.',
    'With the module bottom FB resistor ~360 Ohm and top ~860 Ohm: DAC 0 V -> 4.25 V, DAC 3.3 V -> ~3.0 V. Measure your module and adjust R1.',
    'The module own CC shunt is bypassed because IN- and OUT- share system GND. Turn its CC pot to max; current is regulated by firmware (ADS1115 + shunt) and limited by the OC comparator.',
    'Firmware CC/CV: lower/raise the DAC until measured current = target, then hold 4.2 V and stop at C/20 by opening K1.',
])
p += [
    hdr('J1', 'XL4016 CC/CV module: IN+ IN- OUT+ OUT-', ['VIN', 'GND', 'CHG_OUT', 'GND'], TB(4)),
    hdr('J2', 'XL4016 FB tap (wire to FB pin, GND)', ['XL_FB', 'GND'], XH(2)),
    hdr('U1', 'MCP4725 module #2 (A0=VCC, 0x61): VCC GND SCL SDA A0 OUT', ['+3V3', 'GND', 'SCL', 'SDA', '+3V3', 'DAC_C'], SOCK(6)),
    res('R2', '100R', 'DAC_C', 'DAC_CF'),
    cap('C1', '1uF', 'DAC_CF', 'GND'),
    res('R1', '1.2k', 'DAC_CF', 'CHG_INJ'),
    diode('D1', SCHOTTKY, 'BAT85', 'XL_FB', 'CHG_INJ', FP_DO35, 'BAT85'),
]

# ============================================================ MEASUREMENT
p = sheet('meas', 'Measurement', 'measurement.kicad_sch', 'Measurement: 2 x ADS1115, NTCs, fast voltage', [
    'ADS1115 #1 (0x48): A0-A1 differential = shunt (current, +-256 mV range), A2-A3 differential = cell voltage / 2 (Kelvin, +-2.048 V range).',
    'ADS1115 #2 (0x49): four NTC channels (10k B3950, 10k pull-up): cell surface, pocket air, load heatsink, Peltier hot side.',
    'V_FAST: cell voltage / 2 for the Blue Pill internal ADC (pulse capture at ~1 kHz). It is ground-referenced, so subtract I x shunt in software.',
    'Divider resistors R3/R4 should be 0.1 % 25 ppm, or calibrate against a DMM. ADS1115 modules plug into 1x10 female headers.',
])
p += [
    hdr('U1', 'ADS1115 module #1 (ADDR=GND): VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3',
        ['+3V3', 'GND', 'SCL', 'SDA', 'GND', 'NC', 'ADC_IG', 'ADC_IN', 'ADC_VP', 'ADC_VN'], SOCK(10)),
    res('R1', '100R', 'ISNS_G', 'ADC_IG'),
    res('R2', '100R', 'ISNS_N', 'ADC_IN'),
    cap('C1', '100nF', 'ADC_IG', 'ADC_IN'),
    res('R3', '10k 0.1%', 'SENSE_P', 'ADC_VP'),
    res('R4', '10k 0.1%', 'ADC_VP', 'ADC_VN'),
    res('R5', '100R', 'SENSE_N', 'ADC_VN'),
    cap('C2', '100nF', 'ADC_VP', 'ADC_VN'),
    hdr('U2', 'ADS1115 module #2 (ADDR=VDD): VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3',
        ['+3V3', 'GND', 'SCL', 'SDA', '+3V3', 'NC', 'NTC_CELL', 'NTC_AIR', 'NTC_HS', 'NTC_TEC'], SOCK(10)),
]
for i, n in enumerate(['NTC_CELL', 'NTC_AIR', 'NTC_HS', 'NTC_TEC']):
    p += [res('R%d' % (6 + i), '10k 0.1%', '+3V3', n),
          cap('C%d' % (3 + i), '100nF', n, 'GND'),
          hdr('J%d' % (1 + i), 'NTC 10k ' + n.split('_')[1].lower(), [n, 'GND'], XH(2))]
p += [
    res('R10', '10k', 'SENSE_P', 'V_FAST'),
    res('R11', '10k', 'V_FAST', 'GND'),
    cap('C7', '10nF', 'V_FAST', 'GND'),
]

# ============================================================ PROTECTION
p = sheet('prot', 'Protection', 'protection.kicad_sch', 'Hardware protection (independent of firmware)', [
    'VREF = 2.5 V from TL431 (U3, TO-92). Comparators (LM339N DIP-14, LM393N DIP-8) run from +5 V, open-collector outputs wired-OR onto FAULT_N (pull-up to 3V3).',
    'Trips: OV cell > ~4.29 V | UV cell < ~1.95 V | OC discharge > ~11 A | OC charge > ~6.4 A | heatsink or cell NTC > ~62 C.',
    'Q1 inverts FAULT_N -> FAULT (active high), which kills the load setpoint, both relay gates and the Peltier driver enable.',
    'The MCU reads FAULT_N on PB15 and can also pull it low (open-drain) to force a safe stop and latch the fault in firmware.',
    'UV also trips with no cell inserted (shows as "no cell"). Add ~10 mV hysteresis resistors later if the comparators chatter.',
])
p += [
    res('R1', '1k', '+5V', 'VREF'),
    part('U3', 'Reference_Voltage:TL431LP', 'TL431ACLPR', {'1': 'VREF', '2': 'GND', '3': 'VREF'}, FP_TO92, 'TL431'),
    cap('C1', '100nF', 'VREF', 'GND'),
    res('R2', '10k', 'VREF', 'VREF_H'),
    res('R3', '10k', 'VREF_H', 'GND'),
    res('R4', '15k', 'VREF', 'VREF_C'),
    res('R5', '8.2k', 'VREF_C', 'GND'),
    res('R6', '27k', 'VREF', 'VREF_T'),
    res('R7', '9.1k', 'VREF_T', 'GND'),
    res('R8', '7.15k', 'SENSE_P', 'OV_DIV'),
    res('R9', '10k', 'OV_DIV', 'GND'),
    part('U1', 'Comparator:LM339', 'LM339N', {'5': 'VREF', '4': 'OV_DIV', '2': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=1),
    res('R10', '5.6k', 'SENSE_P', 'UV_DIV'),
    res('R11', '10k', 'UV_DIV', 'GND'),
    part('U1', 'Comparator:LM339', 'LM339N', {'7': 'UV_DIV', '6': 'VREF_H', '1': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=2),
    res('R12', '20k', 'I_MON', 'ID_DIV'),
    res('R13', '100k', 'ID_DIV', 'GND'),
    part('U1', 'Comparator:LM339', 'LM339N', {'11': 'VREF', '10': 'ID_DIV', '13': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=3),
    part('U1', 'Comparator:LM339', 'LM339N', {'9': 'I_MON', '8': 'VREF_C', '14': 'FAULT_N'}, FP_DIP14, 'LM339N', unit=4),
    part('U1', 'Comparator:LM339', 'LM339N', {'3': '+5V', '12': 'GND'}, FP_DIP14, 'LM339N', unit=5),
    part('U2', 'Comparator:LM2903', 'LM393N', {'3': 'NTC_HS', '2': 'VREF_T', '1': 'FAULT_N'}, FP_DIP8, 'LM393N', unit=1),
    part('U2', 'Comparator:LM2903', 'LM393N', {'5': 'NTC_CELL', '6': 'VREF_T', '7': 'FAULT_N'}, FP_DIP8, 'LM393N', unit=2),
    part('U2', 'Comparator:LM2903', 'LM393N', {'8': '+5V', '4': 'GND'}, FP_DIP8, 'LM393N', unit=3),
    cap('C2', '100nF', '+5V', 'GND'),
    cap('C3', '100nF', '+5V', 'GND'),
    res('R14', '10k', '+3V3', 'FAULT_N'),
    fet('Q1', BS170, 'BS170', 'FAULT_N', 'FAULT', 'GND', FP_TO92, 'BS170'),
    res('R15', '10k', '+3V3', 'FAULT'),
]

# ============================================================ THERMAL
p = sheet('thermal', 'Thermal', 'thermal.kicad_sch', 'Peltier driver and fans', [
    'BTS7960 (IBT-2) H-bridge module drives two TEC1-12706 Peltiers (40x40 mm) in series from +12V_SW (about 6 V / 3 A each, better efficiency). RPWM = heat/cool one way, LPWM = the other.',
    'TEC_EN goes to R_EN and L_EN; Q1 pulls it low on FAULT. The thermostat on the Power sheet also removes +12V_SW.',
    'Check that the IBT-2 logic accepts 3.3 V inputs when powered from 5 V; if not, add a 74HCT245 level shifter.',
    'Q2 (IRLZ44N, TO-220) switches both 12 V fans (load heatsink, Peltier hot side) with PWM from PA8. J5 is an always-on 5 V mixing fan inside the pocket.',
])
p += [
    hdr('J1', 'BTS7960 IBT-2 logic: RPWM LPWM R_EN L_EN R_IS L_IS VCC GND',
        ['TEC_RPWM', 'TEC_LPWM', 'TEC_EN_G', 'TEC_EN_G', 'NC', 'NC', '+5V', 'GND'], PINH(8)),
    hdr('J2', 'BTS7960 power: B+ B- M+ M-', ['+12V_SW', 'GND', 'TEC_A', 'TEC_B'], TB(4)),
    part('J3', SCREW2, 'Peltier 2x TEC1-12706 in series', {'1': 'TEC_A', '2': 'TEC_B'}, TB(2)),
    res('R1', '1k', 'TEC_EN', 'TEC_EN_G'),
    res('R2', '100k', 'TEC_EN_G', 'GND'),
    fet('Q1', BS170, 'BS170', 'FAULT', 'TEC_EN_G', 'GND', FP_TO92, 'BS170'),
    fet('Q2', IRLZ44N, 'IRLZ44N', 'FAN_G', 'FAN_N', 'GND', FP_TO220, 'IRLZ44N'),
    res('R3', '100R', 'FAN_PWM', 'FAN_G'),
    res('R4', '100k', 'FAN_G', 'GND'),
    diode('D1', SCHOTTKY, '1N5819', '+12V', 'FAN_N', FP_DO41, '1N5819'),
    hdr('J4', 'Fan 12V heatsink (+,-)', ['+12V', 'FAN_N'], XH(2)),
    hdr('J6', 'Fan 12V Peltier hot side (+,-)', ['+12V', 'FAN_N'], XH(2)),
    hdr('J5', 'Pocket mixing fan 5V', ['+5V', 'GND'], XH(2)),
]

# ============================================================ MCU
p = sheet('mcu', 'MCU', 'mcu.kicad_sch', 'Blue Pill (STM32F103C8) and interfaces', [
    'Blue Pill plugs into two 1x20 female headers, 15.24 mm (0.6 in) apart. USB (micro-USB on the Blue Pill) goes to the PC: USB CDC for the Python UI.',
    'D1 stops the 5 V rail from back-feeding the PC USB port (the Blue Pill 5V pin is tied to VBUS).',
    'Pins: PA0 I_MON, PA1 V_FAST (ADC) | PB6/PB7 I2C1 | PB12 K1_EN, PB13 K2_EN | PB14 LOAD_OFF | PB15 FAULT_N (open-drain, read + force) |',
    'PB0/PB1 TIM3 TEC_RPWM/LPWM, PB10 TEC_EN | PA8 TIM1 FAN_PWM | PA9/PA10 debug UART | PA11/PA12 USB (on board).',
    'R1/R2: I2C pull-ups. Fit only if the modules do not already have them.',
])
p += [
    hdr('J1', 'Blue Pill header A: B12 B13 B14 B15 A8 A9 A10 A11 A12 A15 B3 B4 B5 B6 B7 B8 B9 5V GND 3V3',
        ['K1_EN', 'K2_EN', 'LOAD_OFF', 'FAULT_N', 'FAN_PWM', 'DBG_TX', 'DBG_RX', 'NC', 'NC', 'NC',
         'NC', 'NC', 'NC', 'SCL', 'SDA', 'NC', 'NC', 'BP_5V', 'GND', '+3V3'], SOCK(20)),
    hdr('J2', 'Blue Pill header B: VB C13 C14 C15 A0 A1 A2 A3 A4 A5 A6 A7 B0 B1 B10 B11 RST 3V3 GND GND',
        ['NC', 'NC', 'NC', 'NC', 'I_MON', 'V_FAST', 'NC', 'NC', 'NC', 'NC', 'NC', 'NC',
         'TEC_RPWM', 'TEC_LPWM', 'TEC_EN', 'NC', 'NC', '+3V3', 'GND', 'GND'], SOCK(20)),
    diode('D1', SCHOTTKY, '1N5819', 'BP_5V', '+5V', FP_DO41, '1N5819'),
    hdr('J3', 'Debug UART: TX RX GND', ['DBG_TX', 'DBG_RX', 'GND'], PINH(3)),
    res('R1', '4.7k DNP', '+3V3', 'SCL'),
    res('R2', '4.7k DNP', '+3V3', 'SDA'),
    cap('C1', '10uF', '+3V3', 'GND'),
    flag('#FLG06', '+3V3'),
]

# ============================================================ BUILD
ORDER = ['power', 'relays', 'load', 'charger', 'meas', 'prot', 'thermal', 'mcu']
PREFIX = {'power': 1, 'relays': 2, 'load': 3, 'charger': 4, 'meas': 5, 'prot': 6, 'thermal': 7, 'mcu': 8}

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
            if pt.get('src'):
                mpn, url, sup = SRC[pt['src']]
                fields.update({'MPN': mpn, 'Supplier': sup, 'Supplier link': url})
            col, row = i % cols, i // cols
            x, y = 35 + col * 62, 40 + row * 34
            K.comp(D, s, pt['lib'], ref, pt['val'], x, y, pt['nets'], unit=pt.get('unit', 1), fields=fields)
        rows = (len(S['parts']) + cols - 1) // cols
        ny = 40 + rows * 34 + 2
        for j, line in enumerate(S['notes']):
            line = re.sub(r'\b([RCQDUJFH])(\d{1,2})(?=[A-D]?\b)',
                          lambda m: m.group(1) + str(PREFIX[k]) + '%02d' % int(m.group(2)), line)
            K.text(s, line, 25, ny + j * 4.5, 1.27)
    K.text(D.root, 'Cell test bench - schematic v0.2 (generated, footprints assigned). One 18650/21700 cell at a time; 0-10 A load, <=5 A charge, Peltier-controlled cell pocket.', 30, 30, 2)
    K.text(D.root, 'Inter-sheet connections use global labels. Power nets: GND, +12V, +5V, +3V3 (Blue Pill), VIN (30 V), +12V_SW (after thermostat).', 30, 38, 1.5)
    K.write_all(D, outdir)
    return D

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'out')
