"""Simple 2-layer grid router for the cell test bench PCB (KiCad 7 pcbnew API).

Each connection is a minimum-cost path on a 3-plane grid (F.Cu / via plane / B.Cu)
solved with scikit-image's MCP. Clearances come from dilating foreign copper by
(track width / 2 + clearance). Nets are routed in priority order: high current,
supply, sense, signals. GND is left to the copper pours, then any GND pad the pours
miss gets a track, and stitching vias tie the two pours together.

Usage: python3 router.py <in.kicad_pcb> <out.kicad_pcb>"""
import sys, math, json, os, time
import numpy as np
import pcbnew
from matplotlib.path import Path
from scipy import ndimage
from skimage.graph import MCP_Geometric

G = 0.2                       # grid pitch, mm
EDGE_CLR = 0.6
VIA_COST = 12.0
B_COST = 3.0      # B.Cu is kept as clear as possible so its GND pour stays continuous
MM = pcbnew.FromMM

# net class rules: (track width, clearance, via diameter, via drill)
RULES = {
    'HighCurrent': (3.0, 0.5, 1.6, 1.0),
    'Supply': (1.0, 0.3, 1.2, 0.7),
    'Sense': (0.3, 0.25, 0.9, 0.5),
    'Default': (0.3, 0.2, 0.9, 0.5),
    'GND': (0.5, 0.2, 0.9, 0.5),
}
HC = ['/Power/VIN_RAW', 'VIN', '/Cell_Relays/CELL_P', '/Cell_Relays/CELL_P_RAW', '/Cell_Relays/CELL_N',
      'LOAD_P', '/Electronic_Load/LOAD_D', 'CHG_OUT', '/Thermal/TEC_A', '/Thermal/TEC_B']
SUPPLY = ['+12V', '+12V_SW', '+5V', '+3V3', '/MCU/BP_5V', '/Thermal/FAN_N']
SENSE = ['ISNS_N', 'ISNS_G', 'SENSE_P', 'SENSE_N']
# GND pads that carry the 10 A loop: routed first as a wide track (star at the shunt)
NET_RULES = {'/Cell_Relays/CELL_N': (1.6, 0.4, 1.6, 1.0)}   # neck down at the shunt pad
PRIORITY = ['/Electronic_Load/GATE']   # short, boxed in by the high-current pads of Q301
GND_HC = [('R201', '4', 0), ('Q301', '3', 0), ('J401', '4', 0), ('J401', '2', 0), ('J101', '2', 0)]


def netclass(name):
    if name in HC: return 'HighCurrent'
    if name in SUPPLY: return 'Supply'
    if name in SENSE or name.startswith('/Measurement/ADC_'): return 'Sense'
    if name == 'GND': return 'GND'
    return 'Default'


def disk(r):
    k = int(math.ceil(r))
    y, x = np.ogrid[-k:k + 1, -k:k + 1]
    return x * x + y * y <= r * r + 1e-9


class Router:
    def __init__(self, board):
        self.b = board
        xs, ys = [], []
        for d in board.GetDrawings():
            if d.GetLayer() == pcbnew.Edge_Cuts:
                bb = d.GetBoundingBox()
                xs += [bb.GetLeft(), bb.GetRight()]; ys += [bb.GetTop(), bb.GetBottom()]
        self.x0, self.y0 = pcbnew.ToMM(min(xs)), pcbnew.ToMM(min(ys))
        self.w, self.h = pcbnew.ToMM(max(xs)) - self.x0, pcbnew.ToMM(max(ys)) - self.y0
        self.nx, self.ny = int(round(self.w / G)) + 1, int(round(self.h / G)) + 1
        # owner[layer]: 0 free, -1 blocked for everything, >0 net code (copper present)
        self.owner = np.zeros((2, self.ny, self.nx), np.int32)
        self.noVia = np.zeros((self.ny, self.nx), bool)     # pads/holes: no vias here
        self.padcells = {}                                   # (ref, pad#) -> (layers, mask idx)
        gy, gx = np.mgrid[0:self.ny, 0:self.nx]
        self.gx = self.x0 + gx * G
        self.gy = self.y0 + gy * G
        e = int(math.ceil(EDGE_CLR / G))
        self.owner[:, :e, :] = -1; self.owner[:, -e:, :] = -1
        self.owner[:, :, :e] = -1; self.owner[:, :, -e:] = -1
        self.tracks = []    # (net, layer, [(x,y),...], width)
        self.vias = []      # (net, x, y, dia, drill)
        self._paint_pads()

    # ---------------------------------------------------------- rasterising
    def cell(self, x, y):
        return int(round((y - self.y0) / G)), int(round((x - self.x0) / G))

    def poly_mask(self, pts, grow=0.0):
        pts = np.array(pts)
        xmin, ymin = pts.min(0) - grow - G
        xmax, ymax = pts.max(0) + grow + G
        r0, c0 = self.cell(xmin, ymin); r1, c1 = self.cell(xmax, ymax)
        r0, c0 = max(r0, 0), max(c0, 0); r1, c1 = min(r1, self.ny - 1), min(c1, self.nx - 1)
        sub = np.c_[self.gx[r0:r1 + 1, c0:c1 + 1].ravel(), self.gy[r0:r1 + 1, c0:c1 + 1].ravel()]
        inside = Path(pts).contains_points(sub, radius=2 * grow).reshape(r1 - r0 + 1, c1 - c0 + 1)
        return r0, c0, inside

    def _paint_pads(self):
        for fp in self.b.GetFootprints():
            for pad in fp.Pads():
                net = pad.GetNetCode()
                layers = [i for i, L in enumerate((pcbnew.F_Cu, pcbnew.B_Cu)) if pad.IsOnLayer(L)]
                ps = pcbnew.SHAPE_POLY_SET()
                lay = pcbnew.F_Cu if 0 in layers else pcbnew.B_Cu
                pad.TransformShapeToPolygon(ps, lay, 0, MM(0.01))
                ol = ps.Outline(0)
                pts = [(pcbnew.ToMM(ol.CPoint(i).x), pcbnew.ToMM(ol.CPoint(i).y)) for i in range(ol.PointCount())]
                r0, c0, m = self.poly_mask(pts) if pts else (0, 0, np.zeros((0, 0), bool))
                if not m.any():   # tiny pad: mark the centre cell
                    p = pad.GetPosition(); r, c = self.cell(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))
                    r0, c0, m = r, c, np.ones((1, 1), bool)
                key = (fp.GetReference(), pad.GetNumber(), self._dup(fp.GetReference(), pad.GetNumber()))
                val = net if net > 0 else -1
                for L in layers:
                    sub = self.owner[L, r0:r0 + m.shape[0], c0:c0 + m.shape[1]]
                    sub[m] = val
                self.noVia[r0:r0 + m.shape[0], c0:c0 + m.shape[1]] |= m
                if pad.HasHole() and not layers:      # NPTH: block all layers
                    p = pad.GetPosition(); d = pcbnew.ToMM(pad.GetDrillSize().x)
                    r, c = self.cell(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))
                    k = disk((d / 2 + 0.3) / G); kk = k.shape[0] // 2
                    for L in (0, 1):
                        sl = self.owner[L, max(r - kk, 0):r + kk + 1, max(c - kk, 0):c + kk + 1]
                        sl[k[:sl.shape[0], :sl.shape[1]]] = -1
                    self.noVia[max(r - kk, 0):r + kk + 1, max(c - kk, 0):c + kk + 1] = True
                self.padcells[key] = (layers, r0, c0, m, net)

    def _dup(self, ref, num):
        self._seen = getattr(self, '_seen', {})
        k = (ref, num)
        self._seen[k] = self._seen.get(k, -1) + 1
        return self._seen[k]

    def paint_segment(self, L, a, b, width, net):
        (x1, y1), (x2, y2) = a, b
        hw = width / 2
        xmin, xmax = min(x1, x2) - hw - G, max(x1, x2) + hw + G
        ymin, ymax = min(y1, y2) - hw - G, max(y1, y2) + hw + G
        r0, c0 = self.cell(xmin, ymin); r1, c1 = self.cell(xmax, ymax)
        r0, c0 = max(r0, 0), max(c0, 0); r1, c1 = min(r1, self.ny - 1), min(c1, self.nx - 1)
        px = self.gx[r0:r1 + 1, c0:c1 + 1]; py = self.gy[r0:r1 + 1, c0:c1 + 1]
        dx, dy = x2 - x1, y2 - y1
        l2 = dx * dx + dy * dy
        t = np.clip(((px - x1) * dx + (py - y1) * dy) / l2, 0, 1) if l2 > 0 else 0
        d2 = (px - (x1 + t * dx)) ** 2 + (py - (y1 + t * dy)) ** 2
        m = d2 <= hw * hw
        sub = self.owner[L, r0:r1 + 1, c0:c1 + 1]
        sub[m & (sub == 0)] = net

    def paint_via(self, x, y, dia, net):
        r, c = self.cell(x, y)
        k = disk(dia / 2 / G); kk = k.shape[0] // 2
        for L in (0, 1):
            sl = self.owner[L, r - kk:r + kk + 1, c - kk:c + kk + 1]
            sl[k & (sl == 0)] = net
        self.noVia[r - kk:r + kk + 1, c - kk:c + kk + 1] |= k

    # ---------------------------------------------------------- routing
    def cost_grid(self, net, width, clr, via_d):
        # clearance to foreign copper = max(own class clearance, the other net's class clearance)
        cost = np.ones((3, self.ny, self.nx))
        vb = np.zeros((self.ny, self.nx), bool)
        oc = self.clr_of
        for L, plane in ((0, 0), (1, 2)):
            o = self.owner[L]
            foreign = (o != 0) & (o != net)
            fclr = np.where(o > 0, oc[np.clip(o, 0, None)], 0.5)
            for cv in np.unique(fclr[foreign]):
                m = foreign & (fclr == cv)
                c = max(clr, cv)
                cost[plane][ndimage.binary_dilation(m, disk((width / 2 + c) / G + 1.3))] = -1
                vb |= ndimage.binary_dilation(m, disk((via_d / 2 + c) / G + 1.2))
        vb |= ndimage.binary_dilation(self.noVia, disk(via_d / 2 / G + 0.5))
        cost[1] = VIA_COST
        cost[1][vb] = -1
        cost[2][cost[2] > 0] = B_COST
        return cost

    def cells_of(self, key):
        layers, r0, c0, m, net = self.padcells[key]
        rr, cc = np.nonzero(m)
        out = []
        for L in layers:
            plane = 0 if L == 0 else 2
            out += [(plane, r0 + r, c0 + c) for r, c in zip(rr, cc)]
        return out

    def route_net(self, net, name, pads, width, clr, via_d, via_drill):
        """pads: list of (ref, pad#). Connect them all; returns number of failures."""
        if len(pads) < 2:
            return 0
        offs = [(0, dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)] + [(1, 0, 0), (-1, 0, 0)]
        cost = self.cost_grid(net, width, clr, via_d)
        # pad cells of this net are always passable on their layers
        for k in pads:
            for (pl, r, c) in self.cells_of(k):
                cost[pl, r, c] = 1.0
        # start from the pad nearest the centroid
        cent = np.mean([[r for _, r, _ in self.cells_of(k)][:1] + [c for _, _, c in self.cells_of(k)][:1] for k in pads], axis=0)
        pads = sorted(pads, key=lambda k: (self.cells_of(k)[0][1] - cent[0]) ** 2 + (self.cells_of(k)[0][2] - cent[1]) ** 2)
        tree = list(self.cells_of(pads[0]))
        remaining = pads[1:]
        fails = 0
        while remaining:
            ends = {}
            for k in remaining:
                for cl in self.cells_of(k):
                    ends[cl] = k
            m = MCP_Geometric(cost, offsets=offs)
            costs, _ = m.find_costs(tree, list(ends.keys()), find_all_ends=False)
            reached = [e for e in ends if np.isfinite(costs[e])]
            if not reached:
                fails += len(remaining)
                print('   FAIL', name, remaining)
                break
            end = min(reached, key=lambda e: costs[e])
            path = m.traceback(end)
            self.commit_path(net, path, width, via_d, via_drill)
            k = ends[end]
            remaining.remove(k)
            tree += [(pl, r, c) for (pl, r, c) in path if pl != 1]
            tree += self.cells_of(k)
            # refresh: our own new copper must not block us, foreign blocking unchanged
        return fails

    def commit_path(self, net, path, width, via_d, via_drill):
        pts = [(pl, self.x0 + c * G, self.y0 + r * G) for (pl, r, c) in path]
        runs, cur = [], []
        for (pl, x, y) in pts:
            if pl == 1:
                if cur:
                    runs.append(cur); cur = []
                self.vias.append((net, x, y, via_d, via_drill))
                self.paint_via(x, y, via_d, net)
                continue
            if cur and cur[-1][0] != pl:
                runs.append(cur); cur = []
            cur.append((pl, x, y))
        if cur:
            runs.append(cur)
        for run in runs:
            L = 0 if run[0][0] == 0 else 1
            xy = [(x, y) for _, x, y in run]
            # compress collinear points
            simp = [xy[0]]
            for i in range(1, len(xy) - 1):
                ax, ay = simp[-1]; bx, by = xy[i]; cx, cy = xy[i + 1]
                if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-9:
                    simp.append(xy[i])
            if len(xy) > 1:
                simp.append(xy[-1])
            if len(simp) == 1:
                continue
            self.tracks.append((net, L, simp, width))
            for a, b in zip(simp, simp[1:]):
                self.paint_segment(L, a, b, width, net)

    # ---------------------------------------------------------- output
    def write(self):
        lay = (pcbnew.F_Cu, pcbnew.B_Cu)
        nets = self.b.GetNetsByNetcode()
        for net, L, pts, w in self.tracks:
            for a, b in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(self.b)
                t.SetStart(pcbnew.VECTOR2I(MM(float(a[0])), MM(float(a[1])))); t.SetEnd(pcbnew.VECTOR2I(MM(float(b[0])), MM(float(b[1]))))
                t.SetWidth(MM(w)); t.SetLayer(lay[L]); t.SetNet(nets[net])
                self.b.Add(t)
        for net, x, y, d, drill in self.vias:
            v = pcbnew.PCB_VIA(self.b)
            v.SetPosition(pcbnew.VECTOR2I(MM(float(x)), MM(float(y))))
            v.SetWidth(MM(d)); v.SetDrill(MM(drill)); v.SetNet(nets[net])
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            self.b.Add(v)


def pads_by_net(board):
    out, seen = {}, {}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            k = (fp.GetReference(), p.GetNumber())
            seen[k] = seen.get(k, -1) + 1
            if p.GetNetCode() > 0:
                out.setdefault(p.GetNetCode(), []).append(k + (seen[k],))
    return out


def stitch_gnd(rt, gnd, pitch=6.0):
    """Stitching vias on a regular grid wherever there is room, so both GND pours tie together."""
    d, drill, clr = 0.9, 0.5, 0.35
    free = np.ones((rt.ny, rt.nx), bool)
    for L in (0, 1):
        o = rt.owner[L]
        f = (o != 0) & (o != gnd)
        fclr = np.where(o > 0, rt.clr_of[np.clip(o, 0, None)], 0.5)
        for cv in np.unique(fclr[f]):
            free &= ~ndimage.binary_dilation(f & (fclr == cv), disk((d / 2 + max(clr, cv)) / G + 1.2))
    free &= ~ndimage.binary_dilation(rt.noVia, disk(d / 2 / G + 1.5))
    n = 0
    for y in np.arange(rt.y0 + 4, rt.y0 + rt.h - 3, pitch):
        for x in np.arange(rt.x0 + 4, rt.x0 + rt.w - 3, pitch):
            # look for a free spot near the grid point
            r, c = rt.cell(x, y)
            win = free[max(r - 8, 0):r + 9, max(c - 8, 0):c + 9]
            ys, xs = np.nonzero(win)
            if len(ys):
                i = np.argmin((ys - 8) ** 2 + (xs - 8) ** 2)
                rr, cc = max(r - 8, 0) + ys[i], max(c - 8, 0) + xs[i]
                vx, vy = rt.x0 + cc * G, rt.y0 + rr * G
                rt.vias.append((gnd, vx, vy, d, drill)); rt.paint_via(vx, vy, d, gnd)
                free[max(rr - 12, 0):rr + 13, max(cc - 12, 0):cc + 13] = False
                n += 1
    return n


def base_order(byNet, names):
    order = []
    for code, pads in byNet.items():
        nm = names[code]
        if nm == 'GND' or len(pads) < 2:
            continue
        rank = {'HighCurrent': 0, 'Supply': 1, 'Sense': 2, 'Default': 3}[netclass(nm)]
        order.append((rank, -len(pads) if rank < 2 else len(pads), nm))
    return [nm for _, _, nm in sorted(order)]


def route_all(src, order):
    b = pcbnew.LoadBoard(src)
    for t in list(b.GetTracks()):
        b.Remove(t)
    rt = Router(b)
    byNet = pads_by_net(b)
    names = {n.GetNetCode(): n.GetNetname() for n in b.GetNetsByNetcode().values() if n.GetNetCode() > 0}
    codes = {v: k for k, v in names.items()}
    gnd = codes['GND']
    rt.clr_of = np.full(max(names) + 1, 0.2)
    for code, nm in names.items():
        rt.clr_of[code] = RULES[netclass(nm)][1]
    if order is None:
        order = base_order(byNet, names)
    failed = []
    for nm in PRIORITY:
        w, c, vd, vdr = RULES[netclass(nm)]
        if rt.route_net(codes[nm], nm, byNet[codes[nm]], w, c, vd, vdr):
            failed.append(nm)
    order = [n for n in order if n not in PRIORITY]
    w, c, vd, vdr = RULES['HighCurrent']
    if rt.route_net(gnd, 'GND_HC', [k for k in GND_HC if k in byNet[gnd]], w, c, vd, vdr):
        failed.append('GND_HC')
    fanout_gnd(b, rt, gnd, byNet[gnd])
    for nm in order:
        w, c, vd, vdr = NET_RULES.get(nm, RULES[netclass(nm)])
        if rt.route_net(codes[nm], nm, byNet[codes[nm]], w, c, vd, vdr):
            failed.append(nm)
    stitch_gnd(rt, gnd)
    gfail = connect_gnd_to_pours(b, rt, gnd, byNet[gnd])
    return b, rt, gnd, failed, gfail, order


def fanout_gnd(b, rt, gnd, pads):
    """Give every SMD GND pad a short stub and a via to the bottom pour before the
    signals are routed, so no SMD GND pad gets boxed in later."""
    w, clr, vd, vdr = RULES['GND']
    offs = [(0, dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)] + [(1, 0, 0), (-1, 0, 0)]
    smd = {(fp.GetReference(), p.GetNumber()) for fp in b.GetFootprints() for p in fp.Pads()
           if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD}
    n = 0
    for k in pads:
        if (k[0], k[1]) not in smd:
            continue
        cells = rt.cells_of(k)
        rc = int(np.mean([c[1] for c in cells])); cc = int(np.mean([c[2] for c in cells]))
        R = int(3.0 / G)
        r0, r1 = max(rc - R, 0), min(rc + R, rt.ny - 1)
        c0, c1 = max(cc - R, 0), min(cc + R, rt.nx - 1)
        cost = rt.cost_grid(gnd, w, clr, vd)[:, r0:r1 + 1, c0:c1 + 1].copy()
        cost[2] = -1                                   # stay on top, end in a via
        loc = [(pl, r - r0, c - c0) for (pl, r, c) in cells if pl == 0]
        for (pl, r, c) in loc:
            cost[0, r, c] = 1.0
        vr, vc = np.nonzero(cost[1] > 0)
        ends = [(1, r, c) for r, c in zip(vr, vc)]
        if not ends:
            continue
        m = MCP_Geometric(cost, offsets=offs)
        costs, _ = m.find_costs(loc, ends, find_all_ends=False)
        reached = [e for e in ends if np.isfinite(costs[e])]
        if not reached:
            continue
        path = [(pl, r + r0, c + c0) for (pl, r, c) in m.traceback(min(reached, key=lambda e: costs[e]))]
        rt.commit_path(gnd, path, w, vd, vdr)
        n += 1
    return n


def main_pour_masks(b, rt, gnd):
    """Fill the pours with the current routing and rasterise the largest GND fill
    polygon of each layer (the 'main' pour)."""
    import shapely
    from shapely.geometry import Polygon
    rt.write()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    masks = []
    for L in (pcbnew.F_Cu, pcbnew.B_Cu):
        best, area = None, 0
        for z in b.Zones():
            if z.GetNetCode() != gnd or z.GetIsRuleArea() or z.GetLayer() != L:
                continue
            ps = z.GetFilledPolysList(L)
            for i in range(ps.OutlineCount()):
                ol = ps.Outline(i)
                outer = [(pcbnew.ToMM(ol.CPoint(k).x), pcbnew.ToMM(ol.CPoint(k).y)) for k in range(ol.PointCount())]
                holes = []
                for h in range(ps.HoleCount(i)):
                    hl = ps.Hole(i, h)
                    holes.append([(pcbnew.ToMM(hl.CPoint(k).x), pcbnew.ToMM(hl.CPoint(k).y)) for k in range(hl.PointCount())])
                poly = Polygon(outer, holes)
                if poly.area > area:
                    best, area = poly, poly.area
        m = shapely.contains_xy(best, rt.gx, rt.gy) if best is not None else np.zeros_like(rt.gx, bool)
        masks.append(m)
    for t in list(b.GetTracks()):
        b.Remove(t)
    return masks


def connect_gnd_to_pours(b, rt, gnd, pads):
    """Route a short GND track from every GND pad that does not touch a main pour
    to the nearest main pour (on either layer)."""
    w, clr, vd, vdr = RULES['GND']
    masks = main_pour_masks(b, rt, gnd)
    reach = [ndimage.binary_dilation(m, disk(1.0 / G)) for m in masks]   # spoke reach
    offs = [(0, dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)] + [(1, 0, 0), (-1, 0, 0)]
    fails = 0
    todo = []
    for k in pads:
        layers, r0, c0, m, net = rt.padcells[k]
        ok = 0
        for L in layers:
            sub = reach[L][r0:r0 + m.shape[0], c0:c0 + m.shape[1]]
            if (sub & m).sum() >= 2:
                ok += 1
        if not ok:
            todo.append(k)
    for k in todo:
        cost = rt.cost_grid(gnd, w, clr, vd)
        cells = rt.cells_of(k)
        for (pl, r, c) in cells:
            cost[pl, r, c] = 1.0
        starts = []
        for L, plane in ((0, 0), (1, 2)):
            core = ndimage.binary_erosion(masks[L], disk((w / 2 + 0.3) / G))
            rr, cc = np.nonzero(core & (cost[plane] > 0))
            starts += [(plane, r, c) for r, c in zip(rr, cc)]
        if not starts:
            fails += 1; continue
        mcp = MCP_Geometric(cost, offsets=offs)
        costs, _ = mcp.find_costs(starts, cells, find_all_ends=False)
        reached = [e for e in cells if np.isfinite(costs[e])]
        if not reached:
            # last resort: a via in the pad straight down to the bottom pour
            layers, r0, c0, m, net = rt.padcells[k]
            rr, cc = np.nonzero(m)
            rc, ccn = r0 + int(rr.mean()), c0 + int(cc.mean())
            x, y = rt.x0 + ccn * G, rt.y0 + rc * G
            k2 = disk((vd / 2 + 0.3) / G + 1.2); kk = k2.shape[0] // 2
            win = rt.owner[1, rc - kk:rc + kk + 1, ccn - kk:ccn + kk + 1]
            if win.shape == k2.shape and not ((win != 0) & (win != gnd) & k2).any() and masks[1][rc, ccn]:
                rt.vias.append((gnd, x, y, vd, vdr)); rt.paint_via(x, y, vd, gnd)
                print('   GND via-in-pad', k)
                continue
            fails += 1; print('   GND pad not connected', k); continue
        end = min(reached, key=lambda e: costs[e])
        rt.commit_path(gnd, mcp.traceback(end), w, vd, vdr)
    return fails


def prune_vias(b, gnd):
    """Drop GND vias that are not inside a filled GND pour on both layers and touch no track."""
    zones = [z for z in b.Zones() if z.GetNetCode() == gnd and not z.GetIsRuleArea()]
    tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == gnd]
    n = 0
    for v in [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == gnd]:
        p = v.GetPosition()
        hit = set()
        for z in zones:
            L = z.GetLayer()
            if z.GetFilledPolysList(L).Contains(p):
                hit.add(L)
        if len(hit) < 2 and not any(t.HitTest(p) for t in tracks):
            b.Remove(v); n += 1
    return n


def main(src, dst, passes=8):
    t0 = time.time()
    order, best = None, None
    for p in range(passes):
        b, rt, gnd, failed, gfail, order = route_all(src, order)
        score = (len(failed), gfail)
        print('pass %d: failed %s, GND pads unrouted %d' % (p + 1, failed, gfail), flush=True)
        if best is None or score < best[0]:
            best = (score, b, rt, gnd, failed, gfail)
        if not failed and not gfail:
            break
        # move the failed nets to the front (after the high-current class), keep the rest in order
        hc = [n for n in order if netclass(n) == 'HighCurrent']
        rest = [n for n in order if n not in failed and n not in hc]
        order = hc + [n for n in failed if n in order and n not in hc] + rest
    score, b, rt, gnd, failed, gfail = best
    rt.write()
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    removed = prune_vias(b, gnd)
    filler.Fill(b.Zones())
    print('removed dangling stitching vias', removed)
    b.Save(dst)
    print('failed nets', failed, 'GND unrouted', gfail, 'tracks', len(rt.tracks), 'vias', len(rt.vias), 'time %.0fs' % (time.time() - t0))
    return len(failed)


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1], sys.argv[2]) else 0)
