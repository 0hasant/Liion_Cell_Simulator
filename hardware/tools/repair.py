"""Connect GND pads that DRC still reports as unconnected: route a thin GND track
from each pad to the nearest other GND copper (pad, track or via).
Usage: python3 repair.py <board> <drc.rpt> <out board> [REF.PAD ...]"""
import sys, re
import numpy as np
import pcbnew
from skimage.graph import MCP_Geometric
import router as R

b = pcbnew.LoadBoard(sys.argv[1])
rpt = open(sys.argv[2]).read()
targets = sorted(set(re.findall(r'Pad (\S+) \[GND\] of (\S+)', rpt)))
targets += [tuple(t.split('.')[::-1]) for t in sys.argv[4:]]     # extra pads given as REF.PAD
print('targets', targets)
rt = R.Router(b)
names = {n.GetNetCode(): n.GetNetname() for n in b.GetNetsByNetcode().values() if n.GetNetCode() > 0}
rt.clr_of = np.full(max(names) + 1, 0.2)
for code, nm in names.items():
    rt.clr_of[code] = R.RULES[R.netclass(nm)][1]
gnd = b.GetNetcodeFromNetname('GND')
before = rt.owner.copy()
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        rt.paint_via(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y), pcbnew.ToMM(t.GetWidth()), t.GetNetCode())
    else:
        L = 0 if t.GetLayer() == pcbnew.F_Cu else 1
        a, e = t.GetStart(), t.GetEnd()
        rt.paint_segment(L, (pcbnew.ToMM(a.x), pcbnew.ToMM(a.y)), (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)),
                         pcbnew.ToMM(t.GetWidth()), t.GetNetCode())
# GND copper that comes from tracks and vias (not pads): these belong to the main network
trackgnd = (rt.owner == gnd) & (before != gnd)
offs = [(0, dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)] + [(1, 0, 0), (-1, 0, 0)]
w, clr, vd, vdr = 0.25, 0.2, 0.8, 0.4
nfix = 0
FAR = float(__import__('os').environ.get('FAR', '0'))
for num, ref in targets:
    key = [k for k in rt.padcells if k[0] == ref and k[1] == num][0]
    net = rt.padcells[key][4]
    cells = rt.cells_of(key)
    cost = rt.cost_grid(net, w, clr, vd)
    own = set(cells)
    src = trackgnd if net == gnd else (rt.owner == net)
    if net == gnd and FAR:
        # only GND vias further than FAR mm away: they sit in the main pours
        src = np.zeros_like(rt.owner, bool)
        pr, pc = cells[0][1], cells[0][2]
        for t in b.GetTracks():
            if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == gnd:
                vr, vc = rt.cell(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
                if np.hypot(vr - pr, vc - pc) * R.G > FAR:
                    src[:, vr, vc] = True
    starts = []
    for L, plane in ((0, 0), (1, 2)):
        rr, cc = np.nonzero(src[L])
        starts += [(plane, r, c) for r, c in zip(rr, cc) if (plane, r, c) not in own]
    for (pl, r, c) in cells:
        cost[pl, r, c] = 1.0
    for (pl, r, c) in starts:
        cost[pl, r, c] = 1.0
    m = MCP_Geometric(cost, offsets=offs)
    costs, _ = m.find_costs(starts, cells, find_all_ends=False)
    reached = [e for e in cells if np.isfinite(costs[e])]
    if not reached:
        print('  could not connect', ref, num); continue
    rt.commit_path(net, m.traceback(min(reached, key=lambda e: costs[e])), w, vd, vdr)
    nfix += 1
rt.write()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[3])
print('fixed', nfix, 'of', len(targets))
