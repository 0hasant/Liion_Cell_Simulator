"""Rip up whole nets and route them again after the given nets.
Usage: python3 ripup.py <in> <out> <net to route first> [...] -- <net to rip up and reroute> [...]"""
import sys
import numpy as np
import pcbnew
import router as R

src, dst = sys.argv[1], sys.argv[2]
args = sys.argv[3:]
cut = args.index('--')
first, ripped = args[:cut], args[cut + 1:]
# strip the nets' segments and vias in the file text (removing them through the
# KiCad 7 Python API corrupts the SWIG wrappers)
import re, tempfile, os
txt = open(src).read()
codes_txt = dict((name, code) for code, name in re.findall(r'^\s*\(net (\d+) "([^"]*)"\)', txt, re.M))
kill = {codes_txt[n] for n in first + ripped}
lines = [ln for ln in txt.split('\n')
         if not (re.match(r'\s*\((segment|via) ', ln) and re.search(r'\(net (\d+)\)', ln)
                 and re.search(r'\(net (\d+)\)', ln).group(1) in kill)]
tmp = os.path.join(tempfile.mkdtemp(), 'b.kicad_pcb')
open(tmp, 'w').write('\n'.join(lines))
b = pcbnew.LoadBoard(tmp)
rt = R.Router(b)
names = {n.GetNetCode(): n.GetNetname() for n in b.GetNetsByNetcode().values() if n.GetNetCode() > 0}
codes = {v: k for k, v in names.items()}
rt.clr_of = np.full(max(names) + 1, 0.2)
for code, nm in names.items():
    rt.clr_of[code] = R.RULES[R.netclass(nm)][1]
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        rt.paint_via(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y), pcbnew.ToMM(t.GetWidth()), t.GetNetCode())
    else:
        L = 0 if t.GetLayer() == pcbnew.F_Cu else 1
        a, e = t.GetStart(), t.GetEnd()
        rt.paint_segment(L, (pcbnew.ToMM(a.x), pcbnew.ToMM(a.y)), (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)),
                         pcbnew.ToMM(t.GetWidth()), t.GetNetCode())
byNet = R.pads_by_net(b)
fails = 0
# optional: GND pads (REF.PAD) to connect to a distant GND via before rerouting
import os
from skimage.graph import MCP_Geometric
gnd = codes['GND']
offs = [(0, dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)] + [(1, 0, 0), (-1, 0, 0)]
for tok in os.environ.get('GNDPADS', '').split():
    ref, num = tok.split('.')
    key = [k for k in rt.padcells if k[0] == ref and k[1] == num][0]
    cells = rt.cells_of(key)
    w, c, vd, vdr = 0.4, 0.2, 0.8, 0.4
    cost = rt.cost_grid(gnd, w, c, vd)
    for (pl, r, cc) in cells:
        cost[pl, r, cc] = 1.0
    starts = []
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == gnd:
            vr, vc = rt.cell(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
            if np.hypot(vr - cells[0][1], vc - cells[0][2]) * R.G > 6:
                starts += [(0, vr, vc), (2, vr, vc)]
    for s_ in starts:
        cost[s_] = 1.0
    m = MCP_Geometric(cost, offsets=offs)
    costs, _ = m.find_costs(starts, cells, find_all_ends=False)
    reached = [e for e in cells if np.isfinite(costs[e])]
    if reached:
        rt.commit_path(gnd, m.traceback(min(reached, key=lambda e: costs[e])), w, vd, vdr)
        print('GND pad', tok, 'connected to a main via')
    else:
        print('GND pad', tok, 'FAILED'); fails += 1
for nm in first + ripped:
    w, c, vd, vdr = R.NET_RULES.get(nm, R.RULES[R.netclass(nm)])
    f = rt.route_net(codes[nm], nm, byNet[codes[nm]], w, c, vd, vdr)
    print(nm, 'ok' if not f else 'FAILED')
    fails += f
rt.write()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(dst)
sys.exit(1 if fails else 0)
