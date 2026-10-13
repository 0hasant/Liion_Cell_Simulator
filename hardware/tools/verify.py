import sys, design
from sexp import parse, find
D = design.build('out')
# intended
want = {}
for k in design.ORDER:
    for pt in design.SHEETS[k]['parts']:
        ref = pt['ref']
        if ref.startswith('#'): continue
        r = ref[0] + str(design.PREFIX[k]) + '%02d' % int(''.join(c for c in ref if c.isdigit()))
        if ref[0] == 'K': r = ref
        for pin, n in pt['nets'].items():
            want[(r, pin)] = n
net = parse(open('chk/net.net').read())[0]
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
    if n == 'NC':
        continue
    groups.setdefault(n, set()).add(got[key])
for n, g in groups.items():
    if len(g) != 1:
        print('SPLIT', n, g); bad += 1
inv = {}
for n, g in groups.items():
    for kn in g: inv.setdefault(kn, set()).add(n)
for kn, ns in inv.items():
    if len(ns) > 1: print('MERGED', kn, ns); bad += 1
extra = [k for k in got if k not in want]
print('pins checked', len(want), 'nets', len(groups), 'problems', bad, 'extra nodes', extra[:5])
