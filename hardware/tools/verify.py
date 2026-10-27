"""Compare KiCad's exported netlist (chk/net.net) with the intended connections in design.py."""
import sys, design
from sexp import parse, find
want = {}
fps = {}
for k, r, pt in design.all_parts():
    if r.startswith('#'): continue
    fps[r] = design.lib_fp(pt['fp'])
    for pin, n in pt['nets'].items():
        want[(r, pin)] = n
net = parse(open(sys.argv[1] if len(sys.argv) > 1 else 'chk/net.net').read())[0]
got = {}
for n in find(find(net, 'nets')[0], 'net'):
    name = find(n, 'name')[0][1]
    for nd in find(n, 'node'):
        got[(find(nd, 'ref')[0][1], find(nd, 'pin')[0][1])] = name
bad = 0
groups = {}
for key, n in want.items():
    if key not in got:
        print('missing in netlist', key, n); bad += 1; continue
    if n == 'NC': continue
    groups.setdefault(n, set()).add(got[key])
for n, g in groups.items():
    if len(g) != 1: print('SPLIT', n, g); bad += 1
inv = {}
for n, g in groups.items():
    for kn in g: inv.setdefault(kn, set()).add(n)
for kn, ns in inv.items():
    if len(ns) > 1: print('MERGED', kn, ns); bad += 1
comps = {find(c, 'ref')[0][1]: (find(c, 'footprint')[0][1] if find(c, 'footprint') else '') for c in find(find(net, 'components')[0], 'comp')}
for r, f in fps.items():
    if comps.get(r) != f: print('FOOTPRINT', r, comps.get(r), f); bad += 1
print('pins checked', len(want), 'nets', len(groups), 'parts', len(comps), 'problems', bad)
sys.exit(1 if bad else 0)
