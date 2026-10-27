"""Write the grouped BOM (CSV) from design.py."""
import csv, sys, design
rows = {}
for k, r, pt in design.all_parts():
    if r.startswith('#'): continue
    mpn, url, sup = design.SRC.get(pt.get('src'), ('', '', ''))
    if not pt.get('src'):
        sup = 'Generic (any supplier, e.g. Ozdisan)'
    key = (pt['val'], design.lib_fp(pt['fp']), mpn)
    e = rows.setdefault(key, dict(refs=[], sup=sup, url=url))
    if r not in e['refs']: e['refs'].append(r)
w = csv.writer(open(sys.argv[1], 'w', newline=''))
w.writerow(['Qty', 'References', 'Value', 'Footprint', 'MPN', 'Supplier', 'Link'])
for (val, fp, mpn), e in sorted(rows.items(), key=lambda x: x[1]['refs'][0]):
    w.writerow([len(e['refs']), ' '.join(e['refs']), val, fp, mpn, e['sup'], e['url']])
print(len(rows), 'BOM lines')
