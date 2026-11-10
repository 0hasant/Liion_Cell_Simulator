"""Where to buy every part in Turkiye. Prices in TL including VAT, as seen on 2026-11-10.
Stock changes daily: 'stock' is what the shop showed on that day."""
TL_PER_USD = 47.0      # ASSUMPTION, only used for the three Ozdisan lines priced in USD (+20 % VAT)
D, RB, MR, OZ = 'Direnc.net', 'Robotistan', 'Motorobit', 'Ozdisan'
def usd(p):
    return round(p * 1.2 * TL_PER_USD, 2)

# key -> (what to buy, shop, unit price TL, stock on the check date, link, note)
SRC = {
    'R': ('1/4 W 1 % metal film resistor (E24 value)', D, 0.67, 'in stock (series)', 'https://www.direnc.net/14w-metal-film-direnc', 'check each value in the cart; all values used are E24'),
    'C': ('ceramic capacitor, radial, 5 mm pitch, 50 V', D, 0.98, 'in stock (100 nF checked)', 'https://www.direnc.net/100nf-63v-seramik', '1 nF / 10 nF / 1 uF: same series, price similar'),
    'CP 100uF 50V': ('electrolytic 100 uF 50 V, D10 P5', D, 4.0, 'generic, price estimated', '', ''),
    'CP 220uF 25V': ('electrolytic 220 uF 25 V, D8 P3.5', D, 3.0, 'generic, price estimated', '', ''),
    'CP 10uF 25V': ('electrolytic 10 uF 25 V (or 50 V), D5 P2.5', D, 1.5, 'generic, price estimated', '', ''),
    'BC337': ('BC337 NPN TO-92', D, 1.21, 'in stock', 'https://www.direnc.net/bc337-transistor-bjt-npn-to-92', ''),
    'BC547': ('BC547 NPN TO-92', D, 1.28, 'in stock', 'https://www.direnc.net/bc547-transistor-bjt-npn-to-92', ''),
    'TL431': ('TL431G-T92-B, TO-92', D, 3.51, 'in stock', 'https://www.direnc.net/tl431g-t92-b-to92-voltaj-referans-entegresi', ''),
    'LM339N': ('LM339N DIP-14', D, 6.05, 'in stock', 'https://www.direnc.net/lm339n-pdip-14-dip-komparator-entegresi', ''),
    'LM358P': ('LM358P DIP-8', D, 4.23, 'in stock', 'https://www.direnc.net/arama?q=LM358P', ''),
    'OPA2171': ('OPA2171AIDR SOIC-8', D, 93.76, 'in stock', 'https://www.direnc.net/opa2171aidr-smd-10396', 'replaces OPA2188 (no stock in Turkiye)'),
    'L7805CV': ('L7805CV TO-220', D, 8.72, 'in stock', 'https://www.direnc.net/l7805cv-5v-15a-lineer-voltaj-regulator-to220', ''),
    'BAT85': ('BAT85 Schottky DO-35', D, 2.03, 'in stock', 'https://www.direnc.net/bat85-schottky-diodes-rectifiers-schottky-30v-200ma', ''),
    '1N5819': ('1N5819 Schottky 1 A 40 V DO-41', D, 1.57, 'in stock', 'https://www.direnc.net/1n5819-1a-40v-schottky-rectifier-mic', '1N4007 was sold out, 1N5819 does the same job here'),
    '1N5408': ('1N5408 3 A DO-201', D, 2.72, 'in stock', 'https://www.direnc.net/1n5408-rectifiers-1000v-3a--mic', ''),
    '1N4148': ('1N4148 DO-35', RB, 0.79, 'in stock', 'https://www.robotistan.com/1n4148-100v-450ma-aksiyel-tipli-hizli-diyot', 'sold out at Direnc'),
    'P6KE39CA': ('P6KE39CA TVS 600 W DO-15', D, 12.79, 'in stock', 'https://www.direnc.net/p6ke39ca-do-15-371v-600w-tvs-diyot', ''),
    'SHUNT': ('Isabellenhuette CMS 10 mOhm 1 % 2.5 W, 2512', D, 39.63, 'in stock', 'https://www.direnc.net/10mr-2515-sont-direnc', 'listed as "10mR 2515"; datasheet says size 2512'),
    'WIRE': ('wire link (resistor leg or 0.8 mm copper wire)', '-', 0.0, '-', '', ''),
    'IRFP260N': ('IRFP260NPBF TO-247', OZ, usd(0.77), '4451 in stock', 'https://www.ozdisan.com/en/p/discrete-mosfets-435/infineon-irfp260npbf-3517', 'USD 0.77 + VAT; Direnc lists IRFP260M at 69.87 TL (sold out on the check date)'),
    'IRLZ44N': ('IRLZ44NPBF TO-220 (VBsemi)', RB, 24.46, 'in stock', 'https://www.robotistan.com/vbsemi-elec-irlz44npbf-vb', 'TO-220 was sold out at Direnc'),
    'ALFG2PF121': ('Panasonic ALFG2PF121, 12 V, 33 A', OZ, usd(2.64), '28609 in stock', 'https://ozdisan.com/elektromekanik-komponentler/roleler-ve-role-soketleri/genel-tip-roleler/ALFG2PF121/462930', 'USD 2.64 + VAT'),
    'HK14FD': ('Huike HK14FD-DC12V-SHG, DPDT 5 A, 12 V ("4052" type)', D, 72.59, 'in stock', 'https://www.direnc.net/12v-cift-kontak-huike-4052-12v-10a', 'alternative: Tianbo TRA3-L-12VDC-S-2Z (116 TL)'),
    'SRD-12VDC-SL-C': ('Songle SRD-12VDC-SL-C, 10 A', RB, 20.68, 'in stock', 'https://www.robotistan.com/12v-10a-tek-kontak-role-srd12vdcslc', ''),
    'TB2': ('2-pin 5.08 mm screw terminal ("1 No")', D, 4.84, 'in stock', 'https://www.direnc.net/1-numara-2li-klemens', ''),
    'TB2S': ('2-pin 5.08 mm screw terminal ("0 No")', D, 3.45, 'in stock', 'https://www.direnc.net/0-numara-2li-klemens-1', 'sensor, fan, thermostat and FB wires'),
    'TB4': ('4-pin 5.08 mm screw terminal (two 2-pin blocks slid together)', D, 9.68, 'in stock', 'https://www.direnc.net/1-numara-2li-klemens', ''),
    'TB762': ('2-pin 7.62 mm pluggable terminal, header 180 deg + plug', D, 13.21, 'in stock', 'https://www.direnc.net/2-pin-762mm-90-gecmeli-takim-klemens-12424', 'plug: https://www.direnc.net/2-pin-762mm-90-gecmeli-takim-klemens'),
    'SOCK': ('1x40 precision (machined) female header 2.54 mm, cut to 1x20', D, 21.17, 'in stock', 'https://www.direnc.net/1x40-precision-disi-header', 'the plain 1x40 female header (6.05 TL) was sold out; cutting a machined strip costs one pin'),
    'ADS1115': ('ADS1115 16-bit I2C module + socket strip', D, 145.18, 'in stock', 'https://www.direnc.net/ads1115-16-bit-i2c-4-kanal-modul', 'pin order must be VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3'),
    'PINH': ('1x40 male pin header 2.54 mm (cut)', D, 5.0, 'generic, price estimated', '', ''),
}
# things that are not on the PCB: (qty, what, shop, unit price, stock, link, note)
OFFBOARD = [
    (1, 'Blue Pill STM32F103C8T6 board (clone)', MR, 281.52, '100+ in stock', 'https://www.motorobit.com/stm32f103c8t6-arm-mini-gelistirme-karti', 'sold out at Direnc and Robotistan'),
    (2, 'XL4016 8 A step-down module (12 V rail and charger)', MR, 244.80, '10+ in stock', 'https://www.motorobit.com/xl4016-8a-dc-dc-step-down-voltaj-regulatoru', '60 x 37 mm board; sold out at Direnc and Robotistan'),
    (1, 'Single-sided FR4 copper clad 20 x 30 cm (board blank, enough for one retry)', RB, 144.90, 'in stock', 'https://www.robotistan.com/20x30-bakir-plaket-fr4-epoksi', ''),
    (2, 'TEC1-12706 Peltier 40 x 40 mm', RB, 313.41, 'in stock', 'https://www.robotistan.com/tec1-12706', 'Direnc: 174.35 TL but sold out'),
    (2, 'CPU cooler 80 x 80 x 54 mm with 12 V fan (load heatsink, Peltier hot side)', MR, 397.80, 'listed, add-to-cart shown', 'https://www.motorobit.com/80x80x54mm-sogutuculu-fan-islemci-fani', '331.50 TL + VAT'),
    (1, '0.1 Ohm 50 W aluminium-housed resistor', D, 114.33, 'in stock', 'https://www.direnc.net/010r-50w-aluminyum-direnc', ''),
    (1, 'KSD9700 thermostat 60 C, normally closed', MR, 27.54, 'in stock', 'https://www.motorobit.com/ksd9700-250v-5a-nc-60-c-metal-termostat', '22.95 TL + VAT'),
    (4, 'NTC 10k thermistor TTC05103 (solder to a thin 2-wire cable)', D, 8.38, 'in stock', 'https://www.direnc.net/ttc05103jsy-ntc-termistor-10k-5', 'B value is about 4050 K: set it in firmware'),
    (1, '30 x 30 x 10 mm 12 V fan (pocket mixing)', RB, 91.10, 'in stock', 'https://www.robotistan.com/sogutma-fan-12v-kablo-28cm', ''),
    (2, 'Inline mini blade fuse holder with leads (PSU + lead, cell + lead)', D, 32.18, 'in stock', 'https://www.direnc.net/sigota-yuvasi-kablolu-30cm', 'shorten the leads on the cell side'),
    (2, 'Mini blade fuses: 5 A (PSU) and 15 A (cell)', 'auto parts shop', 10.0, 'not checked', '', 'price estimated'),
    (2, '4 mm binding post (red, black) for the PSU input', D, 31.96, 'in stock (red), black was sold out in one type', 'https://www.direnc.net/4mm-kirmizi-gold-born-jak-16121', ''),
    (1, 'Spring test probes for the Kelvin contacts (P75 or 3 mm pogo pins, pack)', D, 120.98, 'in stock (3 mm pack of 10); P75 pack sold out', 'https://www.direnc.net/3mm-pogo-pim-100-adet', ''),
    (1, 'Aluminium flat bar 100 x 50 x 6 mm (cold plate)', 'metal / hardware shop', 100.0, 'not checked', '', 'price estimated'),
    (1, 'Copper sheet 1.5 mm, 2 pieces 22 x 22 mm (cell contacts)', 'metal / hardware shop', 60.0, 'not checked', '', 'price estimated'),
    (1, 'Thermal paste + 1 mm thermal pad 80 x 30 mm', 'computer shop', 120.0, 'not checked', '', 'price estimated'),
    (1, 'M3 heat-set inserts (about 30), M3 screws, M4 thumbscrew + insert, 4 standoffs', 'hardware shop / marketplace', 200.0, 'not checked', '', 'price estimated'),
    (1, 'Wire: 1.5 mm2 (cell loop, 2 m), 0.75 mm2 (power, 3 m), thin 2-core (sensors, 5 m), 0.6 mm solid (jumpers)', 'electrical shop', 150.0, 'not checked', '', 'price estimated'),
    (1, 'PETG filament 1.75 mm, 1 kg', RB, 724.10, 'in stock', 'https://www.robotistan.com/fibromast-3d-175-mm-petg-filament-sari', 'both boxes need about 0.9 kg'),
    (1, 'PCB milling bits: 30 deg V-bit 0.1 mm, drills 0.8 / 1.0 / 1.3 mm, 1 mm end mill', 'marketplace', 250.0, 'not checked', '', 'only if you do not have them; price estimated'),
]
