"""Single-sided router for the cell test bench PCB (KiCad 7 pcbnew API).

All copper is on B.Cu. Where a connection cannot be made in copper, the router adds a
wire jumper on the component side: two drilled pads joined by a piece of wire. Jumpers
are expensive in the cost function, so they are only used when the detour is long.

Method: minimum-cost paths on a 3-plane grid (wire plane / jumper-pad plane / copper)
with scikit-image's MCP. Clearance = distance transform of foreign copper.
The 11 A loop and the PGND backbone are drawn by hand (PRE) and everything else is routed.

Usage: python3 route1.py <in.kicad_pcb> <out.kicad_pcb> [passes]"""
import sys, math, time, json
import numpy as np
import pcbnew
from matplotlib.path import Path
from scipy import ndimage
from skimage.graph import MCP_Geometric

G = 0.1                    # grid pitch, mm
CLR = 0.5                  # routing clearance on the grid (real clearance >= 0.4 mm after rounding)
EDGE = 1.3                 # copper centre line to board edge
JPAD, JDRILL = 2.4, 1.0    # wire jumper pad
JCOST = 84.0 / G           # cost of one jumper end, in grid cells of track
AIR = 0.2                 # cost per cell of jumper wire
MM = pcbnew.FromMM
TOMM = pcbnew.ToMM

WIDTH = {'CELL_P': 4.0, 'CELL_N': 3.4, 'LOAD_P': 4.0, 'LOAD_D': 4.0, 'PGND': 2.0, 'CHG_OUT': 2.6,
         'VIN': 1.6, '+12V': 1.6, '+12V_SW': 1.6, 'TEC_A': 1.6, 'TEC_B': 1.6, 'TEC_SW': 1.6,
         'FAN_N': 0.8, '+5V': 0.8, '+3V3': 0.8, '+12VA': 0.8, 'GND': 0.8, 'K4_COIL': 0.8,
         'K1_COIL': 0.8, 'K2_COIL': 0.8, 'K3_COIL': 0.8, 'TSTAT': 0.8}
NOJUMP = {'CELL_P', 'CELL_N', 'LOAD_P', 'LOAD_D', 'CHG_OUT'}          # no wire jumpers in these nets
FIRST = ['VIN', 'CHG_OUT', 'TEC_SW', 'TEC_A', 'TEC_B', '+12V_SW', '+12V', 'PGND',
         'ISNS_N', 'ISNS_G', 'SENSE_P', 'SENSE_N', 'GATE', 'OA_OUT']
LAST = ['+12VA', '+5V', '+3V3', 'GND']
# hand-drawn copper: net -> list of (width, [(x, y), ...])
PRE = {
    'PGND': [(3.0, [(3, 13.5), (3, 117), (10, 124), (10, 126.8)]), (4.0, [(10, 126.8), (108, 126.8)]),
             (1.7, [(60, 122.5), (60, 126)])],
    'CELL_P': [(4.0, [(51.2, 109), (42.8, 109)]), (4.0, [(42.8, 109), (42.8, 112.5), (40, 116), (40, 122)])],
    'CELL_N': [(3.4, [(47.62, 122), (54, 122)])],
    'LOAD_P': [(4.0, [(78.8, 109), (78.8, 113), (84, 118.5), (84, 122)])],
    'LOAD_D': [(4.0, [(91.62, 122), (94.5, 120.2), (110.6, 120.2), (113.45, 123), (113.45, 127)])],
}


def short(name):
    return name.split('/')[-1]


def disk(r):
    k = int(math.ceil(r))
    y, x = np.ogrid[-k:k + 1, -k:k + 1]
    return x * x + y * y <= r * r + 1e-9


class Router:
    def __init__(self, board):
        self.b = board
        self.W, self.H = 180.0, 130.0
        self.nx, self.ny = int(round(self.W / G)) + 1, int(round(self.H / G)) + 1
        gy, gx = np.mgrid[0:self.ny, 0:self.nx]
        self.gx, self.gy = gx * G, gy * G
        self.names = {n.GetNetCode(): short(n.GetNetname()) for n in board.GetNetsByNetcode().values() if n.GetNetCode() > 0}
        self.codes = {v: k for k, v in self.names.items()}
        self.pad_occ = np.zeros((self.ny, self.nx), np.int32)      # pads only
        self.holes = np.zeros((self.ny, self.nx), bool)            # drilled holes (centres, dilated later)
        self.nojump = np.zeros((self.ny, self.nx), bool)           # component bodies etc.
        self.pcx = np.full((self.ny, self.nx), np.nan, np.float32)  # pad centre for pad cells
        self.pcy = np.full((self.ny, self.nx), np.nan, np.float32)
        self.pads = {}                                              # net code -> list of (ref, pad, cells array)
        # distance of every grid point to the board edge (mm); copper must stay >= 1.0 mm away
        self.edist = np.minimum(np.minimum(self.gx, self.W - self.gx), np.minimum(self.gy, self.H - self.gy))
        self.edge = self.edist < EDGE
        self.tracks = {}      # net code -> list of (width, [(x, y), ...])
        self.jumpers = {}     # net code -> list of ((x1, y1), (x2, y2))
        self.failed = {}
        self.tie = {}          # net code -> (other net code, mask): copper that may touch (shunt Kelvin taps)
        self._paint_pads()
        for fp in self.b.GetFootprints():
            if fp.GetReference() == 'R201':
                # a Kelvin tap overlaps the corner of its force pad. Only those force-pad cells
                # (within 1.6 mm of the tap centre) may be ignored by the tap's net; the rest of
                # the force pad and all force-net tracks keep their full clearance.
                pn = {p.GetNumber(): p for p in fp.Pads()}
                for tap, force in (('2', '1'), ('3', '4')):
                    tp = pn[tap].GetPosition()
                    tx, ty = TOMM(tp.x), TOMM(tp.y)
                    near = (self.gx - tx) ** 2 + (self.gy - ty) ** 2 <= 1.6 ** 2
                    m = near & (self.pad_occ == pn[force].GetNetCode())
                    self.tie[pn[tap].GetNetCode()] = (pn[force].GetNetCode(), m)
        self.rebuild()

    # ---------------------------------------------------------- rasterising
    def cell(self, x, y):
        return int(round(y / G)), int(round(x / G))

    def poly_mask(self, pts):
        pts = np.array(pts)
        xmin, ymin = pts.min(0) - G
        xmax, ymax = pts.max(0) + G
        r0, c0 = self.cell(xmin, ymin); r1, c1 = self.cell(xmax, ymax)
        r0, c0 = max(r0, 0), max(c0, 0); r1, c1 = min(r1, self.ny - 1), min(c1, self.nx - 1)
        sub = np.c_[self.gx[r0:r1 + 1, c0:c1 + 1].ravel(), self.gy[r0:r1 + 1, c0:c1 + 1].ravel()]
        inside = Path(pts).contains_points(sub, radius=1e-6).reshape(r1 - r0 + 1, c1 - c0 + 1)
        return r0, c0, inside

    def _paint_pads(self):
        for fp in self.b.GetFootprints():
            top = fp.GetLayer() == pcbnew.F_Cu
            ref = fp.GetReference()
            # body: no jumper ends under components
            for g in fp.GraphicalItems():
                if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                    bb = g.GetBoundingBox()
                    r0, c0 = self.cell(TOMM(bb.GetLeft()) - 0.3, TOMM(bb.GetTop()) - 0.3)
                    r1, c1 = self.cell(TOMM(bb.GetRight()) + 0.3, TOMM(bb.GetBottom()) + 0.3)
                    self.nojump[max(r0, 0):r1 + 1, max(c0, 0):c1 + 1] = True
            for pad in fp.Pads():
                net = pad.GetNetCode()
                p = pad.GetPosition()
                px, py = TOMM(p.x), TOMM(p.y)
                r, c = self.cell(px, py)
                if pad.GetDrillSize().x > 0:
                    k = disk((TOMM(pad.GetDrillSize().x) / 2 + JDRILL / 2 + 0.7) / G); kk = k.shape[0] // 2
                    sl = self.holes[max(r - kk, 0):r + kk + 1, max(c - kk, 0):c + kk + 1]
                    sl |= k[:sl.shape[0], :sl.shape[1]]
                if not pad.IsOnLayer(pcbnew.B_Cu):
                    if pad.GetDrillSize().x > 0:        # mounting hole: keep copper away
                        k = disk(3.4 / G); kk = k.shape[0] // 2
                        sl = self.pad_occ[max(r - kk, 0):r + kk + 1, max(c - kk, 0):c + kk + 1]
                        sl[k[:sl.shape[0], :sl.shape[1]]] = -1
                    continue
                ps = pcbnew.SHAPE_POLY_SET()
                pad.TransformShapeToPolygon(ps, pcbnew.B_Cu, 0, MM(0.01))
                ol = ps.Outline(0)
                pts = [(TOMM(ol.CPoint(i).x), TOMM(ol.CPoint(i).y)) for i in range(ol.PointCount())]
                r0, c0, m = self.poly_mask(pts)
                if not m.any():
                    r0, c0, m = r, c, np.ones((1, 1), bool)
                val = net if net > 0 else -1
                sub = self.pad_occ[r0:r0 + m.shape[0], c0:c0 + m.shape[1]]
                # net-tie pads (shunt taps) overlap their force pad: the tap wins
                small = ref == 'R201' and pad.GetNumber() in ('2', '3')
                sub[m & ((sub == 0) | small)] = val
                rr, cc = np.nonzero(m)
                cells = np.c_[rr + r0, cc + c0]
                if small:
                    cells = np.array([[r, c]])
                self.pcx[cells[:, 0], cells[:, 1]] = px
                self.pcy[cells[:, 0], cells[:, 1]] = py
                if net > 0:
                    self.pads.setdefault(net, []).append((ref, pad.GetNumber(), cells, (px, py)))

    def paint_segment(self, occ, a, b, width, net):
        (x1, y1), (x2, y2) = a, b
        hw = width / 2
        r0, c0 = self.cell(min(x1, x2) - hw - G, min(y1, y2) - hw - G)
        r1, c1 = self.cell(max(x1, x2) + hw + G, max(y1, y2) + hw + G)
        r0, c0 = max(r0, 0), max(c0, 0); r1, c1 = min(r1, self.ny - 1), min(c1, self.nx - 1)
        px = self.gx[r0:r1 + 1, c0:c1 + 1]; py = self.gy[r0:r1 + 1, c0:c1 + 1]
        dx, dy = x2 - x1, y2 - y1
        l2 = dx * dx + dy * dy
        t = np.clip(((px - x1) * dx + (py - y1) * dy) / l2, 0, 1) if l2 > 0 else 0
        d2 = (px - (x1 + t * dx)) ** 2 + (py - (y1 + t * dy)) ** 2
        sub = occ[r0:r1 + 1, c0:c1 + 1]
        sub[(d2 <= hw * hw) & (sub == 0)] = net

    def rebuild(self):
        """occupancy grid from pads + all committed tracks and jumper pads."""
        self.occ = self.pad_occ.copy()
        self.jholes = np.zeros((self.ny, self.nx), bool)
        for net, lst in self.tracks.items():
            for w, pts in lst:
                for a, b in zip(pts, pts[1:]):
                    self.paint_segment(self.occ, a, b, w, net)
        for net, lst in self.jumpers.items():
            for a, b in lst:
                for (x, y) in (a, b):
                    self.paint_jpad(x, y, net)

    def paint_jpad(self, x, y, net):
        self.paint_segment(self.occ, (x, y), (x, y), JPAD, net)
        r, c = self.cell(x, y)
        k = disk((JDRILL + 0.7) / G); kk = k.shape[0] // 2
        sl = self.jholes[max(r - kk, 0):r + kk + 1, max(c - kk, 0):c + kk + 1]
        sl |= k[:sl.shape[0], :sl.shape[1]]

    # ---------------------------------------------------------- routing
    def cost_grid(self, net, width, allow_jump):
        other = (self.occ != 0) & (self.occ != net)
        if net in self.tie:
            tn, tm = self.tie[net]
            other &= ~((self.occ == tn) & tm)
        dist = ndimage.distance_transform_edt(~other)
        cost = np.empty((3, self.ny, self.nx), np.float32)
        cu = np.ones((self.ny, self.nx), np.float32)
        # gentle preference for keeping some distance to foreign copper (keeps channels tidy)
        cu[dist < (width / 2 + CLR + 0.6) / G] = 1.6
        cu[dist < (width / 2 + CLR) / G + 0.01] = -1
        cu[self.edist < width / 2 + 1.05] = -1
        cost[2] = cu
        if allow_jump:
            ok = (dist >= (JPAD / 2 + CLR) / G + 0.01) & ~self.nojump & ~self.holes & ~self.jholes & (self.edist >= JPAD / 2 + 1.05)
            cost[1] = np.where(ok, JCOST, -1)
            cost[0] = AIR
        else:
            cost[1] = -1
            cost[0] = -1
        return cost

    def tree_cells(self, net):
        """centre-line cells of this net's committed copper (plane 2)."""
        cells = []
        for w, pts in self.tracks.get(net, []):
            for a, b in zip(pts, pts[1:]):
                n = max(int(math.hypot(b[0] - a[0], b[1] - a[1]) / (G * 0.7)), 1)
                for i in range(n + 1):
                    x = a[0] + (b[0] - a[0]) * i / n; y = a[1] + (b[1] - a[1]) * i / n
                    cells.append(self.cell(x, y))
        for a, b in self.jumpers.get(net, []):
            cells += [self.cell(*a), self.cell(*b)]
        return cells

    def route_net(self, net, verbose=False):
        name = self.names[net]
        pads = self.pads.get(net, [])
        if len(pads) < 2 and not self.tracks.get(net):
            return 0
        width = WIDTH.get(name, 0.5)
        allow = name not in NOJUMP
        offs = [(0, dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)] + [(1, 0, 0), (-1, 0, 0)]
        widths = [width] + [w for w in (1.6, 1.0, 0.5) if w < width]
        costs = {}
        def cg(w):
            if w not in costs:
                c = self.cost_grid(net, w, allow)
                for _, _, cells, _ in pads:
                    c[2][cells[:, 0], cells[:, 1]] = 1.0
                for (r, k) in list(self.tree_cells(net)) + list(tree):
                    c[2][r, k] = 1.0
                costs[w] = c
            return costs[w]
        # connected components: start with pre-drawn copper if any, else the first pad
        groups = []          # list of sets of cells; group 0 is the growing tree
        pre = self.tree_cells(net)
        remaining = list(range(len(pads)))
        tree = set(map(tuple, pre))
        if not tree:
            # start at the pad closest to the centroid of the net
            cx = np.mean([p[3][0] for p in pads]); cy = np.mean([p[3][1] for p in pads])
            s = min(remaining, key=lambda i: (pads[i][3][0] - cx) ** 2 + (pads[i][3][1] - cy) ** 2)
            remaining.remove(s)
            tree = set(map(tuple, pads[s][2]))
        else:
            # pads already touched by pre-drawn copper
            for i in list(remaining):
                if any((int(r), int(c)) in tree for r, c in pads[i][2]):
                    remaining.remove(i)
                    tree |= set(map(tuple, pads[i][2]))
        fails = 0
        while remaining:
            done = False
            for w in widths:
                c = cg(w)
                ends = {}
                for i in remaining:
                    for r, k in pads[i][2]:
                        ends[(2, int(r), int(k))] = i
                starts = [(2, r, k) for (r, k) in tree]
                m = MCP_Geometric(c, offsets=offs)
                cum, _ = m.find_costs(starts, list(ends.keys()), find_all_ends=False)
                reached = [e for e in ends if np.isfinite(cum[e])]
                if not reached:
                    continue
                end = min(reached, key=lambda e: cum[e])
                path = m.traceback(end)
                new = self.commit(net, path, w)
                if self.made_jumper:
                    costs.clear()
                    tree |= set(new)
                for cst in costs.values():
                    for (r, k) in new:
                        cst[2][r, k] = 1.0
                i = ends[end]
                remaining.remove(i)
                tree |= set(new)
                tree |= set(map(tuple, pads[i][2]))
                if w != width and verbose:
                    print('   %s: narrowed to %.1f mm near %s.%s' % (name, w, pads[i][0], pads[i][1]))
                done = True
                break
            if not done:
                fails += len(remaining)
                self.failed[name] = [(pads[i][0], pads[i][1]) for i in remaining]
                break
        if not fails:
            self.failed.pop(name, None)
        return fails

    def commit(self, net, path, width):
        """turn a grid path into tracks (plane 2) and jumpers; returns new centre-line cells."""
        runs, cur, seg = [], [], []
        new = []
        made_jumper = False
        def close(seg):
            vias = [(c, r) for (pl, r, c) in seg if pl == 1]
            if len(vias) >= 2 and any(pl == 0 for pl, _, _ in seg) and vias[0] != vias[-1]:
                a = (round(vias[0][0] * G, 3), round(vias[0][1] * G, 3))
                e = (round(vias[-1][0] * G, 3), round(vias[-1][1] * G, 3))
                self.jumpers.setdefault(net, []).append((a, e))
                for (x, y) in (a, e):
                    self.paint_jpad(x, y, net)
                    new.append(self.cell(x, y))
                return True
            return False
        for (pl, r, c) in path:
            if pl == 2:
                if seg:
                    made_jumper |= close(seg); seg = []
                cur.append((r, c)); new.append((r, c))
            else:
                if cur:
                    runs.append(cur); cur = []
                seg.append((pl, r, c))
        if cur:
            runs.append(cur)
        self.made_jumper = made_jumper
        for run in runs:
            xy = [(round(c * G, 3), round(r * G, 3)) for r, c in run]
            # snap run ends to the pad centre when they sit in a pad
            for idx in (0, -1):
                r, c = run[idx]
                if not np.isnan(self.pcx[r, c]) and self.occ[r, c] == net:
                    ctr = (float(self.pcx[r, c]), float(self.pcy[r, c]))
                    if ctr != xy[idx]:
                        xy = ([ctr] + xy) if idx == 0 else (xy + [ctr])
            simp = [xy[0]]
            for i in range(1, len(xy) - 1):
                ax, ay = simp[-1]; bx, by = xy[i]; cx, cy = xy[i + 1]
                if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-9:
                    simp.append(xy[i])
            if len(xy) > 1:
                simp.append(xy[-1])
            if len(simp) < 2:
                continue
            self.tracks.setdefault(net, []).append((width, simp))
            for a, b in zip(simp, simp[1:]):
                self.paint_segment(self.occ, a, b, width, net)
        return new

    def rip(self, net):
        pre = [t for t in self.tracks.get(net, []) if t in self.pre.get(net, [])]
        self.tracks[net] = pre
        self.jumpers[net] = []
        self.rebuild()

    # ---------------------------------------------------------- driver
    def run(self, passes=2, log=print):
        self.pre = {}
        for nm, lst in PRE.items():
            net = self.codes[nm]
            self.pre[net] = [(w, [tuple(p) for p in pts]) for w, pts in lst]
            self.tracks[net] = list(self.pre[net])
        self.rebuild()
        def hp(net):
            pts = [p[3] for p in self.pads.get(net, [])]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            return (max(xs) - min(xs)) + (max(ys) - min(ys)) if pts else 0
        nets = [n for n in self.pads if len(self.pads[n]) >= 2 or self.names[n] in PRE]
        mid = sorted([n for n in nets if self.names[n] not in FIRST + LAST + list(PRE)], key=hp)
        order = [self.codes[n] for n in PRE if self.codes[n] in nets and n not in FIRST] + \
                [self.codes[n] for n in FIRST if n in self.codes and self.codes[n] in nets] + mid + \
                [self.codes[n] for n in LAST if n in self.codes and self.codes[n] in nets]
        t0 = time.time()
        for net in order:
            f = self.route_net(net, verbose=True)
            if f:
                log('  FAIL %s: %s' % (self.names[net], self.failed[self.names[net]]))
        log('run 0: jumpers %d, failed nets %d, %.0f s' % (self.njump(), len(self.failed), time.time() - t0))
        best = (self.score(), dict(self.tracks), dict(self.jumpers), dict(self.failed))
        for p in range(passes):
            # start again, routing the nets that needed jumpers (or failed) first
            trouble = sorted([n for n in order if self.names[n] not in NOJUMP and
                              (self.jumpers.get(n) or self.names[n] in self.failed)],
                             key=lambda n: -(len(self.jumpers.get(n, [])) + 5 * (self.names[n] in self.failed)))
            head = [n for n in order if self.names[n] in PRE or self.names[n] in FIRST[:8]]
            order = head + [n for n in trouble if n not in head] + [n for n in order if n not in head and n not in trouble]
            self.tracks = {net: list(v) for net, v in self.pre.items()}
            self.jumpers = {}
            self.failed = {}
            self.rebuild()
            for net in order:
                self.route_net(net)
            log('run %d: jumpers %d, failed nets %d, %.0f s' % (p + 1, self.njump(), len(self.failed), time.time() - t0))
            if self.score() < best[0]:
                best = (self.score(), dict(self.tracks), dict(self.jumpers), dict(self.failed))
        _, self.tracks, self.jumpers, self.failed = best
        self.rebuild()

    def score(self):
        return self.njump() + 20 * sum(len(v) for v in self.failed.values())

    def njump(self):
        return sum(len(v) for v in self.jumpers.values())

    # ---------------------------------------------------------- output
    def write(self):
        b = self.b
        nets = b.GetNetsByNetcode()
        for net, lst in self.tracks.items():
            for w, pts in lst:
                for a, c in zip(pts, pts[1:]):
                    if a == c:
                        continue
                    t = pcbnew.PCB_TRACK(b)
                    t.SetStart(pcbnew.VECTOR2I(MM(float(a[0])), MM(float(a[1]))))
                    t.SetEnd(pcbnew.VECTOR2I(MM(float(c[0])), MM(float(c[1]))))
                    t.SetWidth(MM(w)); t.SetLayer(pcbnew.B_Cu); t.SetNet(nets[net])
                    b.Add(t)
        n = 0
        table = []
        for net in sorted(self.jumpers, key=lambda k: self.names[k]):
            for a, c in self.jumpers[net]:
                a, c = (float(a[0]), float(a[1])), (float(c[0]), float(c[1]))
                n += 1
                ref = 'W%d' % n
                fp = pcbnew.FOOTPRINT(b)
                fp.SetReference(ref); fp.SetValue('wire ' + self.names[net])
                fp.SetFPIDAsString('cell_bench:WireJumper')
                fp.SetPosition(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
                fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_THROUGH_HOLE)
                for i, (x, y) in enumerate((a, c)):
                    pad = pcbnew.PAD(fp)
                    pad.SetNumber(str(i + 1))
                    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
                    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
                    pad.SetSize(pcbnew.VECTOR2I(MM(JPAD), MM(JPAD)))
                    pad.SetDrillSize(pcbnew.VECTOR2I(MM(JDRILL), MM(JDRILL)))
                    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.B_Cu); ls.AddLayer(pcbnew.B_Mask); ls.AddLayer(pcbnew.F_Mask)
                    pad.SetLayerSet(ls)
                    pad.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
                    pad.SetPos0(pcbnew.VECTOR2I(MM(x - a[0]), MM(y - a[1])))
                    pad.SetNet(nets[net])
                    fp.Add(pad)
                ln = pcbnew.FP_SHAPE(fp)
                ln.SetShape(pcbnew.SHAPE_T_SEGMENT)
                ln.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); ln.SetEnd(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
                ln.SetLayer(pcbnew.F_SilkS); ln.SetWidth(MM(0.3))
                fp.Add(ln)
                fp.Reference().SetPosition(pcbnew.VECTOR2I(MM((a[0] + c[0]) / 2), MM((a[1] + c[1]) / 2 - 1.2)))
                fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.9), MM(0.9)))
                fp.Reference().SetTextThickness(MM(0.13))
                fp.Value().SetVisible(False)
                b.Add(fp)
                table.append((ref, self.names[net], a, c, round(math.hypot(c[0] - a[0], c[1] - a[1]), 1)))
        return table


def add_gnd_zone(b):
    gnd = [n for n in b.GetNetsByNetcode().values() if n.GetNetname() == 'GND'][0]
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.B_Cu); z.SetNet(gnd)
    z.SetMinThickness(MM(0.6)); z.SetLocalClearance(MM(0.6))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetAssignedPriority(0)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetZoneName('GND fill')
    ol = z.Outline(); ol.NewOutline()
    for (px, py) in [(1.0, 1.0), (179.0, 1.0), (179.0, 129.0), (1.0, 129.0)]:
        ol.Append(MM(px), MM(py))
    b.Add(z)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    passes = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    b = pcbnew.LoadBoard(src)
    for t in list(b.GetTracks()):
        b.Remove(t)
    for z in list(b.Zones()):
        b.Remove(z)
    for fp in list(b.GetFootprints()):
        if fp.GetReference().startswith('W') and fp.GetReference()[1:].isdigit():
            b.Remove(fp)
    rt = Router(b)
    rt.run(passes)
    table = rt.write()
    add_gnd_zone(b)
    b.Save(dst)
    json.dump({'jumpers': table, 'failed': rt.failed}, open(dst.replace('.kicad_pcb', '_route.json'), 'w'), indent=1)
    print('jumpers:', len(table), 'failed:', rt.failed)
    for row in table:
        print('  ', row)
