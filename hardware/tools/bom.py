"""Write the priced BOM (CSV) from design.py + sourcing.py.
Usage: python3 bom.py <bom.csv> <bom_offboard.csv>"""
import csv, sys, design, sourcing
rows = {}
for k, r, pt in design.all_parts():
    if r.startswith('#') or r.startswith('H'):
        continue
    key = (pt['val'] if pt['src'] in ('R', 'C') else '', pt['src'], design.lib_fp(pt['fp']))
    e = rows.setdefault(key, dict(refs=[], val=pt['val']))
    if r not in e['refs']:
        e['refs'].append(r)
total = 0.0
w = csv.writer(open(sys.argv[1], 'w', newline=''))
w.writerow(['Qty', 'References', 'Value', 'Footprint', 'Buy', 'Shop', 'Unit TL (VAT incl.)', 'Line TL', 'Stock 2026-11-10', 'Link', 'Note'])
for (val, src, fp), e in sorted(rows.items(), key=lambda x: x[1]['refs'][0]):
    what, shop, price, stock, url, note = sourcing.SRC[src]
    n = len(e['refs'])
    total += n * price
    w.writerow([n, ' '.join(e['refs']), e['val'], fp.split(':')[1], what, shop, '%.2f' % price, '%.2f' % (n * price), stock, url, note])
w.writerow([]); w.writerow(['', '', '', '', 'PCB parts total', '', '', '%.2f' % total])
off = 0.0
w2 = csv.writer(open(sys.argv[2], 'w', newline=''))
w2.writerow(['Qty', 'Item', 'Shop', 'Unit TL (VAT incl.)', 'Line TL', 'Stock 2026-11-10', 'Link', 'Note'])
for q, what, shop, price, stock, url, note in sourcing.OFFBOARD:
    off += q * price
    w2.writerow([q, what, shop, '%.2f' % price, '%.2f' % (q * price), stock, url, note])
w2.writerow([]); w2.writerow(['', 'Modules, mechanics and consumables total', '', '', '%.2f' % off])
w2.writerow(['', 'PCB parts total', '', '', '%.2f' % total]); w2.writerow(['', 'GRAND TOTAL', '', '', '%.2f' % (total + off)])
print('%d BOM lines, PCB parts %.0f TL, off-board %.0f TL, total %.0f TL' % (len(rows), total, off, total + off))
