"""Cell test bench - schematic draft v0.1 (generated). Run: python3 design.py <outdir>"""
import sys, re
import kigen as K

R, C, CP = 'Device:R', 'Device:C', 'Device:C_Polarized'
N7002, AO3400 = 'Transistor_FET:2N7002', 'Transistor_FET:AO3400A'
SCHOTTKY, DIODE = 'Device:D_Schottky', 'Device:D'
CONN = lambda n: 'Connector_Generic:Conn_01x%02d' % n
SCREW2 = 'Connector:Screw_Terminal_01x02'
SHEETS = {}

def sheet(key, name, file, title, notes):
    SHEETS[key] = dict(name=name, file=file, title=title, notes=notes, parts=[])
    return SHEETS[key]['parts']

def two(ref, lib, val, a, b, **kw):          # 2-pin parts: pin1=a, pin2=b
    return dict(ref=ref, lib=lib, val=val, nets={'1': a, '2': b}, **kw)

def part(ref, lib, val, nets, **kw):
    return dict(ref=ref, lib=lib, val=val, nets=nets, **kw)

def fet(ref, lib, val, g, d, s):
    pins = {'Device:Q_NMOS_GDS': ('1', '2', '3')}.get(lib, ('1', '3', '2'))   # G, D, S
    return part(ref, lib, val, {pins[0]: g, pins[1]: d, pins[2]: s})

def diode(ref, lib, val, k, a):
    return part(ref, lib, val, {'1': k, '2': a})

def hdr(ref, val, nets_list):
    return part(ref, CONN(len(nets_list)), val, {str(i + 1): n for i, n in enumerate(nets_list)})

# ============================================================ POWER
p = sheet('power', 'Power', 'power.kicad_sch', 'Power input and rails', [
    'PSU: existing 30 V / 10 A bench supply, no CC/CV. F1 + D1 (TVS) protect against overvoltage and reverse polarity (D1 conducts, F1 blows).',
    'J2: 12 V buck module (XL4015 or LM2596HV) for Peltiers, relays and fans.   J3: 5 V buck module (MP1584) for Blue Pill, comparators and BTS7960 logic.',
    '+3V3 comes from the Blue Pill regulator (MCU sheet).',
    'J4: bimetal thermostat KSD9700, normally closed, 60 C, mounted on the load heatsink. It cuts +12V_SW (relay coils + Peltier driver) independently of firmware.',
])
p += [
    hdr('J1', 'PSU in 30V 10A (+, -)', ['VIN_RAW', 'GND']),
    two('F1', 'Device:Fuse', '10A', 'VIN_RAW', 'VIN'),
    diode('D1', DIODE, 'SMBJ33A (TVS)', 'VIN', 'GND'),
    two('C1', CP, '100uF 50V', 'VIN', 'GND'),
    hdr('J2', '12V buck module: IN+ IN- OUT+ OUT-', ['VIN', 'GND', '+12V', 'GND']),
    two('C2', CP, '220uF 25V', '+12V', 'GND'),
    hdr('J3', '5V buck module: IN+ IN- OUT+ OUT-', ['+12V', 'GND', '+5V', 'GND']),
    two('C3', CP, '100uF 16V', '+5V', 'GND'),
    hdr('J4', 'Thermostat KSD9700 60C NC', ['+12V', '+12V_SW']),
    two('C4', CP, '220uF 25V', '+12V_SW', 'GND'),
    part('#FLG01', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'GND'}, inbom=False),
    part('#FLG02', 'power:PWR_FLAG', 'PWR_FLAG', {'1': '+12V'}, inbom=False),
    part('#FLG03', 'power:PWR_FLAG', 'PWR_FLAG', {'1': '+5V'}, inbom=False),
    part('#FLG04', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'VIN'}, inbom=False),
    part('#FLG05', 'power:PWR_FLAG', 'PWR_FLAG', {'1': '+12V_SW'}, inbom=False),
]
for c in p[1:4]:
    pass
p[0]['lib'] = SCREW2

# ============================================================ CELL PATH + RELAYS
p = sheet('relays', 'Cell_Relays', 'relays.kicad_sch', 'Cell connection, shunt and relays K1/K2', [
    'Single 10 mOhm 4-terminal shunt R1 sits in the cell negative lead, so it measures BOTH charge and discharge current. System GND = shunt ground side (star point).',
    'Kelvin sense: ISNS_N / ISNS_G from the shunt sense pins, SENSE_P / SENSE_N from separate wires at the cell tabs.',
    'K1 (charger) and K2 (load): 12 V automotive relays 30-40 A, normally open, in sockets (pins 85, 86, 30, 87).',
    'Interlock: Q3 holds K1 off while K2_EN is high, Q4 holds K2 off while K1_EN is high (both commanded = both off). Q5/Q6 drop both relays on FAULT.',
    'R4/R7 pull-downs keep both relays off while the MCU boots.',
])
p += [
    part('J5', SCREW2, 'Cell power to pocket (+, -)', {'1': 'CELL_P_RAW', '2': 'CELL_N'}),
    hdr('J6', 'Cell Kelvin sense (+, -)', ['SENSE_P', 'SENSE_N']),
    two('F2', 'Device:Fuse', '15A (cell)', 'CELL_P_RAW', 'CELL_P'),
    part('R1', 'Device:R_Shunt', '10mR 4-terminal 1% 3W', {'1': 'CELL_N', '2': 'ISNS_N', '3': 'ISNS_G', '4': 'GND'}),
    hdr('K1', 'K1 charge relay socket: 85 86 30 87', ['+12V_SW', 'K1_COIL', 'CHG_OUT', 'CELL_P']),
    hdr('K2', 'K2 load relay socket: 85 86 30 87', ['+12V_SW', 'K2_COIL', 'CELL_P', 'LOAD_P']),
    diode('D1', DIODE, '1N4007', '+12V_SW', 'K1_COIL'),
    diode('D2', DIODE, '1N4007', '+12V_SW', 'K2_COIL'),
    fet('Q1', AO3400, 'AO3400A', 'K1_G', 'K1_COIL', 'GND'),
    fet('Q2', AO3400, 'AO3400A', 'K2_G', 'K2_COIL', 'GND'),
    two('R2', R, '1k', 'K1_EN', 'K1_G'),
    two('R3', R, '100k', 'K1_G', 'GND'),
    two('R4', R, '100k', 'K1_EN', 'GND'),
    two('R5', R, '1k', 'K2_EN', 'K2_G'),
    two('R6', R, '100k', 'K2_G', 'GND'),
    two('R7', R, '100k', 'K2_EN', 'GND'),
    fet('Q3', N7002, '2N7002', 'K2_EN', 'K1_G', 'GND'),
    fet('Q4', N7002, '2N7002', 'K1_EN', 'K2_G', 'GND'),
    fet('Q5', N7002, '2N7002', 'FAULT', 'K1_G', 'GND'),
    fet('Q6', N7002, '2N7002', 'FAULT', 'K2_G', 'GND'),
]

# ============================================================ ELECTRONIC LOAD
p = sheet('load', 'Electronic_Load', 'load.kicad_sch', 'Electronic load 0-10 A (linear, CC)', [
    'CC loop: U1A compares the DAC setpoint with the shunt voltage. Summing node INP = (SETP - I*Rshunt)/2, so the loop settles at I = SETP / 10 mOhm.',
    'Setpoint: MCP4725 #1 (0x60) 0-3.3 V, divided by R1/R2 to 0-108 mV -> 0-10.8 A full scale (~2.6 mA per LSB).',
    'Q1 IRFP260N in linear mode on the CPU-cooler heatsink, with the external 0.1 Ohm 50 W aluminium resistor (J1) in series to share the heat.',
    'Kill: Q2 (LOAD_OFF from MCU, pulled up = off at boot) and Q3 (hardware FAULT) short INP to ground -> gate goes low.',
    'Sequence: close K2 with LOAD_OFF high, release LOAD_OFF with DAC = 0, then ramp the DAC.',
    'U1B: bidirectional current monitor for the fast internal ADC and the OC comparators: I_MON = 1.65 V + 0.12 V/A (approx -13 A ... +13 A).',
    'U1 = OPA2188 (zero-drift, 36 V, input range includes V-). Check pinout of the DAC module you buy (order varies).',
])
p += [
    part('J1', SCREW2, 'Series R 0.1R 50W alu (off-board)', {'1': 'LOAD_P', '2': 'LOAD_D'}),
    part('Q1', 'Device:Q_NMOS_GDS', 'IRFP260N', {'1': 'GATE', '2': 'LOAD_D', '3': 'GND'}),
    hdr('U2', 'MCP4725 module #1 (A0=GND, 0x60): VCC GND SCL SDA A0 OUT', ['+3V3', 'GND', 'SCL', 'SDA', 'GND', 'DAC_L']),
    two('R1', R, '29.4k 0.1%', 'DAC_L', 'SETP'),
    two('R2', R, '1k 0.1%', 'SETP', 'ISNS_G'),
    two('C1', C, '10nF', 'SETP', 'ISNS_G'),
    two('R3', R, '10k 0.1%', 'SETP', 'INP'),
    two('R4', R, '10k 0.1%', 'ISNS_N', 'INP'),
    fet('Q2', N7002, '2N7002', 'LOAD_OFF', 'INP', 'GND'),
    fet('Q3', N7002, '2N7002', 'FAULT', 'INP', 'GND'),
    two('R5', R, '10k', '+3V3', 'LOAD_OFF'),
    part('U1', 'Device:Opamp_Dual', 'OPA2188', {'3': 'INP', '2': 'INN', '1': 'OA_OUT'}, unit=1),
    two('R6', R, '10k', 'INN', 'ISNS_G'),
    two('C2', C, '1nF', 'INN', 'OA_OUT'),
    two('R7', R, '100R', 'OA_OUT', 'GATE'),
    two('R8', R, '10k', 'GATE', 'GND'),
    part('U1', 'Device:Opamp_Dual', 'OPA2188', {'5': 'MB', '6': 'MN', '7': 'MON_RAW'}, unit=2),
    two('R9', R, '1k 0.1%', 'ISNS_N', 'MN'),
    two('R10', R, '12k 0.1%', 'MN', 'MON_RAW'),
    two('R11', R, '24.9k', '+3V3', 'MB'),
    two('R12', R, '1k', 'MB', 'ISNS_G'),
    two('R13', R, '1k', 'MON_RAW', 'I_MON'),
    diode('D1', SCHOTTKY, 'BAT54', '+3V3', 'I_MON'),
    diode('D2', SCHOTTKY, 'BAT54', 'I_MON', 'GND'),
    two('C3', C, '10nF', 'I_MON', 'GND'),
    part('U1', 'Device:Opamp_Dual', 'OPA2188', {'8': '+12V', '4': 'GND'}, unit=3),
    two('C4', C, '100nF', '+12V', 'GND'),
    two('C5', C, '10uF', '+12V', 'GND'),
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
    hdr('J1', 'XL4016 CC/CV module: IN+ IN- OUT+ OUT-', ['VIN', 'GND', 'CHG_OUT', 'GND']),
    hdr('J2', 'XL4016 FB tap (wire to FB pin, GND)', ['XL_FB', 'GND']),
    hdr('U1', 'MCP4725 module #2 (A0=VCC, 0x61): VCC GND SCL SDA A0 OUT', ['+3V3', 'GND', 'SCL', 'SDA', '+3V3', 'DAC_C']),
    two('R2', R, '100R', 'DAC_C', 'DAC_CF'),
    two('C1', C, '1uF', 'DAC_CF', 'GND'),
    two('R1', R, '1.2k', 'DAC_CF', 'CHG_INJ'),
    diode('D1', SCHOTTKY, 'BAT54', 'XL_FB', 'CHG_INJ'),
]

# ============================================================ MEASUREMENT
p = sheet('meas', 'Measurement', 'measurement.kicad_sch', 'Measurement: 2 x ADS1115, NTCs, fast voltage', [
    'ADS1115 #1 (0x48): A0-A1 differential = shunt (current, +-256 mV range), A2-A3 differential = cell voltage / 2 (Kelvin, +-2.048 V range).',
    'ADS1115 #2 (0x49): four NTC channels (10k B3950, 10k pull-up): cell surface, pocket air, load heatsink, Peltier hot side.',
    'V_FAST: cell voltage / 2 for the Blue Pill internal ADC (pulse capture at ~1 kHz). It is ground-referenced, so subtract I x shunt in software.',
    'Divider resistors R3/R4 should be 0.1 % 25 ppm, or calibrate against a DMM.',
])
p += [
    hdr('U1', 'ADS1115 module #1 (ADDR=GND): VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3',
        ['+3V3', 'GND', 'SCL', 'SDA', 'GND', 'NC', 'ADC_IG', 'ADC_IN', 'ADC_VP', 'ADC_VN']),
    two('R1', R, '100R', 'ISNS_G', 'ADC_IG'),
    two('R2', R, '100R', 'ISNS_N', 'ADC_IN'),
    two('C1', C, '100nF', 'ADC_IG', 'ADC_IN'),
    two('R3', R, '10k 0.1%', 'SENSE_P', 'ADC_VP'),
    two('R4', R, '10k 0.1%', 'ADC_VP', 'ADC_VN'),
    two('R5', R, '100R', 'SENSE_N', 'ADC_VN'),
    two('C2', C, '100nF', 'ADC_VP', 'ADC_VN'),
    hdr('U2', 'ADS1115 module #2 (ADDR=VDD): VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3',
        ['+3V3', 'GND', 'SCL', 'SDA', '+3V3', 'NC', 'NTC_CELL', 'NTC_AIR', 'NTC_HS', 'NTC_TEC']),
]
for i, n in enumerate(['NTC_CELL', 'NTC_AIR', 'NTC_HS', 'NTC_TEC']):
    p += [two('R%d' % (6 + i), R, '10k 0.1%', '+3V3', n),
          two('C%d' % (3 + i), C, '100nF', n, 'GND'),
          hdr('J%d' % (1 + i), 'NTC 10k ' + n.split('_')[1].lower(), [n, 'GND'])]
p += [
    two('R10', R, '10k', 'SENSE_P', 'V_FAST'),
    two('R11', R, '10k', 'V_FAST', 'GND'),
    two('C7', C, '10nF', 'V_FAST', 'GND'),
]

# ============================================================ PROTECTION
p = sheet('prot', 'Protection', 'protection.kicad_sch', 'Hardware protection (independent of firmware)', [
    'VREF = 2.5 V from TL431 (U3). Comparators run from +5 V, open-collector outputs wired-OR onto FAULT_N (pull-up to 3V3).',
    'Trips: OV cell > ~4.29 V | UV cell < ~1.95 V | OC discharge > ~11 A | OC charge > ~6.4 A | heatsink or cell NTC > ~62 C.',
    'Q1 inverts FAULT_N -> FAULT (active high), which kills the load setpoint, both relay gates and the Peltier driver enable.',
    'The MCU reads FAULT_N on PB15 and can also pull it low (open-drain) to force a safe stop and latch the fault in firmware.',
    'UV also trips with no cell inserted (shows as "no cell"). Add ~10 mV hysteresis resistors later if the comparators chatter.',
])
p += [
    two('R1', R, '1k', '+5V', 'VREF'),
    part('U3', 'Reference_Voltage:TL431DBZ', 'TL431', {'1': 'VREF', '2': 'VREF', '3': 'GND'}),
    two('C1', C, '100nF', 'VREF', 'GND'),
    two('R2', R, '10k', 'VREF', 'VREF_H'),
    two('R3', R, '10k', 'VREF_H', 'GND'),
    two('R4', R, '15k', 'VREF', 'VREF_C'),
    two('R5', R, '8.2k', 'VREF_C', 'GND'),
    two('R6', R, '27k', 'VREF', 'VREF_T'),
    two('R7', R, '9.1k', 'VREF_T', 'GND'),
    two('R8', R, '7.15k', 'SENSE_P', 'OV_DIV'),
    two('R9', R, '10k', 'OV_DIV', 'GND'),
    part('U1', 'Comparator:LM339', 'LM339', {'5': 'VREF', '4': 'OV_DIV', '2': 'FAULT_N'}, unit=1),
    two('R10', R, '5.6k', 'SENSE_P', 'UV_DIV'),
    two('R11', R, '10k', 'UV_DIV', 'GND'),
    part('U1', 'Comparator:LM339', 'LM339', {'7': 'UV_DIV', '6': 'VREF_H', '1': 'FAULT_N'}, unit=2),
    two('R12', R, '20k', 'I_MON', 'ID_DIV'),
    two('R13', R, '100k', 'ID_DIV', 'GND'),
    part('U1', 'Comparator:LM339', 'LM339', {'11': 'VREF', '10': 'ID_DIV', '13': 'FAULT_N'}, unit=3),
    part('U1', 'Comparator:LM339', 'LM339', {'9': 'I_MON', '8': 'VREF_C', '14': 'FAULT_N'}, unit=4),
    part('U1', 'Comparator:LM339', 'LM339', {'3': '+5V', '12': 'GND'}, unit=5),
    part('U2', 'Comparator:LM2903', 'LM393', {'3': 'NTC_HS', '2': 'VREF_T', '1': 'FAULT_N'}, unit=1),
    part('U2', 'Comparator:LM2903', 'LM393', {'5': 'NTC_CELL', '6': 'VREF_T', '7': 'FAULT_N'}, unit=2),
    part('U2', 'Comparator:LM2903', 'LM393', {'8': '+5V', '4': 'GND'}, unit=3),
    two('C2', C, '100nF', '+5V', 'GND'),
    two('C3', C, '100nF', '+5V', 'GND'),
    two('R14', R, '10k', '+3V3', 'FAULT_N'),
    fet('Q1', N7002, '2N7002', 'FAULT_N', 'FAULT', 'GND'),
    two('R15', R, '10k', '+3V3', 'FAULT'),
]

# ============================================================ THERMAL
p = sheet('thermal', 'Thermal', 'thermal.kicad_sch', 'Peltier driver and fans', [
    'BTS7960 (IBT-2) H-bridge module drives two Peltiers in series from +12V_SW (about 6 V each, better efficiency). RPWM = heat/cool one way, LPWM = the other.',
    'TEC_EN goes to R_EN and L_EN; Q1 pulls it low on FAULT. The thermostat on the Power sheet also removes +12V_SW.',
    'Check that the IBT-2 logic accepts 3.3 V inputs when powered from 5 V; if not, add a 74HCT245 level shifter.',
    'Q2 switches both 12 V fans (load heatsink, Peltier hot side) with PWM from PA8. J5 is an always-on 5 V mixing fan inside the pocket.',
])
p += [
    hdr('J1', 'BTS7960 IBT-2 logic: RPWM LPWM R_EN L_EN R_IS L_IS VCC GND',
        ['TEC_RPWM', 'TEC_LPWM', 'TEC_EN_G', 'TEC_EN_G', 'NC', 'NC', '+5V', 'GND']),
    hdr('J2', 'BTS7960 power: B+ B- M+ M-', ['+12V_SW', 'GND', 'TEC_A', 'TEC_B']),
    part('J3', SCREW2, 'Peltier x2 in series', {'1': 'TEC_A', '2': 'TEC_B'}),
    two('R1', R, '1k', 'TEC_EN', 'TEC_EN_G'),
    two('R2', R, '100k', 'TEC_EN_G', 'GND'),
    fet('Q1', N7002, '2N7002', 'FAULT', 'TEC_EN_G', 'GND'),
    fet('Q2', AO3400, 'AO3400A', 'FAN_G', 'FAN_N', 'GND'),
    two('R3', R, '100R', 'FAN_PWM', 'FAN_G'),
    two('R4', R, '100k', 'FAN_G', 'GND'),
    diode('D1', SCHOTTKY, 'SS14', '+12V', 'FAN_N'),
    hdr('J4', 'Fans 12V: heatsink (+,-)', ['+12V', 'FAN_N']),
    hdr('J6', 'Fans 12V: Peltier hot side (+,-)', ['+12V', 'FAN_N']),
    hdr('J5', 'Pocket mixing fan 5V', ['+5V', 'GND']),
]

# ============================================================ MCU
p = sheet('mcu', 'MCU', 'mcu.kicad_sch', 'Blue Pill (STM32F103C8) and interfaces', [
    'Blue Pill plugs into two 1x20 female headers. USB (micro-USB on the Blue Pill) goes to the PC: USB CDC for the Python UI.',
    'D1 stops the 5 V rail from back-feeding the PC USB port (the Blue Pill 5V pin is tied to VBUS).',
    'Pins: PA0 I_MON, PA1 V_FAST (ADC) | PB6/PB7 I2C1 | PB12 K1_EN, PB13 K2_EN | PB14 LOAD_OFF | PB15 FAULT_N (open-drain, read + force) |',
    'PB0/PB1 TIM3 TEC_RPWM/LPWM, PB10 TEC_EN | PA8 TIM1 FAN_PWM | PA9/PA10 debug UART | PA11/PA12 USB (on board).',
    'R1/R2: I2C pull-ups. Fit only if the modules do not already have them.',
])
p += [
    hdr('J1', 'Blue Pill header A: B12 B13 B14 B15 A8 A9 A10 A11 A12 A15 B3 B4 B5 B6 B7 B8 B9 5V GND 3V3',
        ['K1_EN', 'K2_EN', 'LOAD_OFF', 'FAULT_N', 'FAN_PWM', 'DBG_TX', 'DBG_RX', 'NC', 'NC', 'NC',
         'NC', 'NC', 'NC', 'SCL', 'SDA', 'NC', 'NC', 'BP_5V', 'GND', '+3V3']),
    hdr('J2', 'Blue Pill header B: VB C13 C14 C15 A0 A1 A2 A3 A4 A5 A6 A7 B0 B1 B10 B11 RST 3V3 GND GND',
        ['NC', 'NC', 'NC', 'NC', 'I_MON', 'V_FAST', 'NC', 'NC', 'NC', 'NC', 'NC', 'NC',
         'TEC_RPWM', 'TEC_LPWM', 'TEC_EN', 'NC', 'NC', '+3V3', 'GND', 'GND']),
    diode('D1', SCHOTTKY, 'SS14', 'BP_5V', '+5V'),
    hdr('J3', 'Debug UART: TX RX GND', ['DBG_TX', 'DBG_RX', 'GND']),
    two('R1', R, '4.7k DNP', '+3V3', 'SCL'),
    two('R2', R, '4.7k DNP', '+3V3', 'SDA'),
    two('C1', C, '10uF', '+3V3', 'GND'),
    part('#FLG06', 'power:PWR_FLAG', 'PWR_FLAG', {'1': '+3V3'}, inbom=False),
]

# ============================================================ BUILD
ORDER = ['power', 'relays', 'load', 'charger', 'meas', 'prot', 'thermal', 'mcu']
PREFIX = {'power': 1, 'relays': 2, 'load': 3, 'charger': 4, 'meas': 5, 'prot': 6, 'thermal': 7, 'mcu': 8}

def build(outdir):
    D = K.Design()
    # nets used on more than one sheet become global labels
    seen = {}
    for k in ORDER:
        for pt in SHEETS[k]['parts']:
            for n in pt['nets'].values():
                seen.setdefault(n, set()).add(k)
    D.globals = {n for n, ks in seen.items() if len(ks) > 1 and n not in K.POWER_NETS and n != 'NC'}
    # every net needs >=2 connections
    count = {}
    for k in ORDER:
        for pt in SHEETS[k]['parts']:
            for n in pt['nets'].values():
                count[n] = count.get(n, 0) + 1
    lonely = [n for n, c in count.items() if c < 2 and n != 'NC']
    if lonely:
        raise SystemExit('single-connection nets: %s' % lonely)
    for k in ORDER:
        S = SHEETS[k]
        s = D.sheet(S['name'], S['file'], S['title'])
        cols = 6
        for i, pt in enumerate(S['parts']):
            ref = pt['ref']
            if not ref.startswith('#'):
                ref = ref[0] + str(PREFIX[k]) + '%02d' % int(''.join(c for c in ref if c.isdigit()))
                if pt['ref'][0] == 'K':
                    ref = pt['ref']
            col, row = i % cols, i // cols
            x, y = 35 + col * 62, 40 + row * 34
            K.comp(D, s, pt['lib'], ref, pt['val'], x, y, pt['nets'], unit=pt.get('unit', 1))
        rows = (len(S['parts']) + cols - 1) // cols
        ny = 40 + rows * 34 + 2
        for j, line in enumerate(S['notes']):
            line = re.sub(r'\b([RCQDUJF])(\d{1,2})(?=[A-D]?\b)',
                          lambda m: m.group(1) + str(PREFIX[k]) + '%02d' % int(m.group(2)), line)
            K.text(s, line, 25, ny + j * 4.5, 1.27)
    K.text(D.root, 'Cell test bench - schematic draft v0.1 (generated). One 18650/21700 cell at a time; 0-10 A load, <=5 A charge, Peltier-controlled cell pocket.', 30, 30, 2)
    K.text(D.root, 'Inter-sheet connections use global labels. Power nets: GND, +12V, +5V, +3V3 (Blue Pill), VIN (30 V), +12V_SW (after thermostat).', 30, 38, 1.5)
    K.write_all(D, outdir)
    return D

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'out')
