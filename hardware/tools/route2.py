"""Single-sided router with negotiated congestion (PathFinder style) for the cell test bench PCB.

route1.py routes one net after another, so early nets wall in later ones and far too many wire
jumpers are needed. Here all signal nets are routed again and again; sharing space with another
net is allowed at first but costs more every round, so the nets sort themselves out and a wire
jumper is used only where two nets really have to cross.

Power nets and the hand-drawn 11 A loop are routed first (route1) and stay fixed.

Usage: python3 route2.py <in.kicad_pcb> <out.kicad_pcb> [iterations]"""
import sys, os, math, time, json
import numpy as np
import pcbnew
from scipy import ndimage
from skimage.graph import MCP_Geometric
import route1 as R
from route1 import G, CLR, JPAD, JDRILL, WIDTH, PRE, disk

FIXED_NETS = list(PRE) + ['VIN', 'CHG_OUT', 'TEC_SW', 'TEC_A', 'TEC_B', '+12V_SW', '+12V', 'PGND']
JC = 80.0 / G       # cost of one jumper end (grid cells)
AIRC = 0.15
MARGIN = int(18 / G)
OFFS = [(0, dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)] + [(1, 0, 0), (-1, 0, 0)]


class PF(R.Router):
    def prepare(self):
        self.pre = {}
        for nm, lst in PRE.items():
            net = self.codes[nm]
            self.pre[net] = [(w, [tuple(p) for p in pts]) for w, pts in lst]
            self.tracks[net] = list(self.pre[net])
        self.rebuild()
        for nm in FIXED_NETS:
            net = self.codes.get(nm)
            if net is None:
                continue
            f = self.route_net(net)
            if f:
                print('  FAIL (fixed net)', nm, self.failed.get(nm))
        self.fixed = {self.codes[n] for n in FIXED_NETS if n in self.codes}
        self.sig = [n for n in self.pads if n not in self.fixed and len(self.pads[n]) >= 2]
        occ0 = self.occ.copy()
        self.hard, self.jsite = {}, {}
        for n in self.sig:
            w = WIDTH.get(self.names[n], 0.5)
            other = (occ0 != 0) & (occ0 != n)
            if n in self.tie:
                tn, tm = self.tie[n]
                other &= ~((occ0 == tn) & tm)
            dist = ndimage.distance_transform_edt(~other)
            h = (dist < (w / 2 + CLR) / G + 0.01) | (self.edist < w / 2 + 1.05)
            for _, _, cells, _ in self.pads[n]:
                h[cells[:, 0], cells[:, 1]] = False
            self.hard[n] = h
            self.jsite[n] = (dist >= (JPAD / 2 + CLR) / G + 0.01) & ~self.nojump & ~self.holes & ~self.jholes & (self.edist >= JPAD / 2 + 1.05)
        self.cnt = np.zeros((self.ny, self.nx), np.int16)
        self.hist = np.zeros((self.ny, self.nx), np.float32)
        self.terr = {}                    # net -> flat indices of its territory
        self.line = {}                    # net -> flat indices of its centre line
        self.sol = {}                     # net -> (tracks, jumpers)

    # ------------------------------------------------------------------
    def territory(self, net, tracks, jumpers):
        w = WIDTH.get(self.names[net], 0.5)
        m = np.zeros((self.ny, self.nx), np.int32)
        for wd, pts in tracks:
            for a, b in zip(pts, pts[1:]):
                self.paint_segment(m, a, b, wd + 2 * CLR + 0.5, 1)
        for a, b in jumpers:
            for p in (a, b):
                self.paint_segment(m, p, p, JPAD + 2 * CLR + 0.5, 1)
        return np.flatnonzero(m)

    def centre(self, tracks, jumpers):
        cells = set()
        for wd, pts in tracks:
            for a, b in zip(pts, pts[1:]):
                n = max(int(math.hypot(b[0] - a[0], b[1] - a[1]) / (G * 0.7)), 1)
                for i in range(n + 1):
                    r, c = self.cell(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
                    cells.add(r * self.nx + c)
        for a, b in jumpers:
            for p in (a, b):
                r, c = self.cell(*p)
                cells.add(r * self.nx + c)
        return np.array(sorted(cells), dtype=np.int64)

    def route_soft(self, net, pres):
        name = self.names[net]
        pads = self.pads[net]
        w = WIDTH.get(name, 0.5)
        hard = self.hard[net]
        cu = (1.0 + self.hist) * (1.0 + pres * self.cnt)
        cu = cu.astype(np.float32)
        cu[hard] = -1
        cnt_j = ndimage.maximum_filter(self.cnt, size=int(2.0 / G) | 1)
        jp = np.where(self.jsite[net], JC * (1.0 + pres * cnt_j), -1).astype(np.float32)
        cx = np.mean([p[3][0] for p in pads]); cy = np.mean([p[3][1] for p in pads])
        remaining = list(range(len(pads)))
        s = min(remaining, key=lambda i: (pads[i][3][0] - cx) ** 2 + (pads[i][3][1] - cy) ** 2)
        remaining.remove(s)
        tree = set(map(tuple, pads[s][2]))
        tracks, jumpers, failed = [], [], []
        while remaining:
            ends = {}
            for i in remaining:
                for r, k in pads[i][2]:
                    ends[(int(r), int(k))] = i
            tr = np.array(list(tree)); en = np.array(list(ends.keys()))
            found = None
            for full in (False, True):
                if full:
                    r0, c0, r1, c1 = 0, 0, self.ny, self.nx
                else:
                    # window around the tree and the nearest remaining pad
                    d = [min(abs(pads[i][3][0] - self.gx[0, tr[:, 1]]) + abs(pads[i][3][1] - self.gy[tr[:, 0], 0])) for i in remaining]
                    i0 = remaining[int(np.argmin(d))]
                    pc = pads[i0][2]
                    j = int(np.argmin(abs(tr[:, 0] - pc[0, 0]) + abs(tr[:, 1] - pc[0, 1])))
                    r0 = max(min(tr[j, 0], pc[:, 0].min()) - MARGIN, 0); r1 = min(max(tr[j, 0], pc[:, 0].max()) + MARGIN, self.ny)
                    c0 = max(min(tr[j, 1], pc[:, 1].min()) - MARGIN, 0); c1 = min(max(tr[j, 1], pc[:, 1].max()) + MARGIN, self.nx)
                cost = np.empty((3, r1 - r0, c1 - c0), np.float32)
                cost[2] = cu[r0:r1, c0:c1]; cost[1] = jp[r0:r1, c0:c1]; cost[0] = AIRC
                st = [(2, r - r0, c - c0) for r, c in tree if r0 <= r < r1 and c0 <= c < c1]
                ee = {(2, r - r0, c - c0): i for (r, c), i in ends.items() if r0 <= r < r1 and c0 <= c < c1}
                if not st or not ee:
                    continue
                for (_, r, c) in st:
                    if cost[2, r, c] < 0:
                        cost[2, r, c] = 1.0
                m = MCP_Geometric(cost, offsets=OFFS)
                cum, _ = m.find_costs(st, list(ee.keys()), find_all_ends=False)
                reached = [e for e in ee if np.isfinite(cum[e])]
                if reached:
                    end = min(reached, key=lambda e: cum[e])
                    found = ([(pl, r + r0, c + c0) for pl, r, c in m.traceback(end)], ee[end])
                    break
            if not found:
                failed = [(pads[i][0], pads[i][1]) for i in remaining]
                break
            path, i = found
            new = self.path_to_copper(net, path, w, tracks, jumpers)
            tree |= set(new)
            tree |= set(map(tuple, pads[i][2]))
            remaining.remove(i)
        return tracks, jumpers, failed

    def path_to_copper(self, net, path, width, tracks, jumpers):
        runs, cur, seg, new = [], [], [], []
        def close(seg):
            vias = [(c, r) for (pl, r, c) in seg if pl == 1]
            if len(vias) >= 2 and any(pl == 0 for pl, _, _ in seg) and vias[0] != vias[-1]:
                a = (round(vias[0][0] * G, 3), round(vias[0][1] * G, 3))
                e = (round(vias[-1][0] * G, 3), round(vias[-1][1] * G, 3))
                jumpers.append((a, e))
                new.extend([self.cell(*a), self.cell(*e)])
        for (pl, r, c) in path:
            if pl == 2:
                if seg:
                    close(seg); seg = []
                cur.append((r, c)); new.append((r, c))
            else:
                if cur:
                    runs.append(cur); cur = []
                seg.append((pl, r, c))
        if cur:
            runs.append(cur)
        for run in runs:
            xy = [(round(c * G, 3), round(r * G, 3)) for r, c in run]
            for idx in (0, -1):
                r, c = run[idx]
                if not np.isnan(self.pcx[r, c]) and self.pad_occ[r, c] == net:
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
            if len(simp) >= 2:
                tracks.append((width, simp))
        return new

    def negotiate(self, iters, log=print):
        t0 = time.time()
        pres = 0.6
        order = sorted(self.sig, key=lambda n: len(self.pads[n]))
        for it in range(iters):
            nfail = 0
            for net in order:
                if net in self.terr:
                    np.subtract.at(self.cnt.ravel(), self.terr[net], 1)
                tr, ju, fl = self.route_soft(net, pres)
                self.sol[net] = (tr, ju, fl)
                nfail += bool(fl)
                self.terr[net] = self.territory(net, tr, ju)
                self.line[net] = self.centre(tr, ju)
                np.add.at(self.cnt.ravel(), self.terr[net], 1)
            flat = self.cnt.ravel(); hf = self.hist.ravel()
            nover = 0
            for net in order:
                bad = self.line[net][flat[self.line[net]] > 1]
                nover += len(bad)
                hf[bad] += 0.5
            nj = sum(len(v[1]) for v in self.sol.values())
            log('iter %d: pres %.1f, overused cells %d, jumpers %d, failed %d, %.0f s' % (it, pres, nover, nj, nfail, time.time() - t0))
            if nover == 0 and nfail == 0:
                break
            pres = min(pres * 1.35, 400.0)

    def legalise(self, log=print):
        """commit conflict-free nets; reroute the rest one by one with hard clearances."""
        bad = []
        flat = self.cnt.ravel()
        for net in self.sig:
            tr, ju, fl = self.sol[net]
            if fl or (flat[self.line[net]] > 1).any():
                bad.append(net)
        good = [n for n in self.sig if n not in bad]
        # among conflicting nets keep as many as possible: remove one, re-check
        bad.sort(key=lambda n: -int((flat[self.line[n]] > 1).sum()))
        keep = []
        for net in list(bad):
            if not self.sol[net][2] and not (flat[self.line[net]] > 1).any():
                keep.append(net); continue
            np.subtract.at(flat, self.terr[net], 1)
        bad = [n for n in bad if n not in keep]
        for net in good + keep:
            self.tracks[net] = list(self.sol[net][0]); self.jumpers[net] = list(self.sol[net][1])
        self.rebuild()
        log('legalise: %d nets clean, %d to reroute' % (len(good) + len(keep), len(bad)))
        for net in sorted(bad, key=lambda n: len(self.pads[n])):
            self.tracks[net] = []; self.jumpers[net] = []
            f = self.route_net(net)
            if f:
                log('  FAIL %s %s' % (self.names[net], self.failed.get(self.names[net])))


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    iters = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 25
    b = pcbnew.LoadBoard(src)
    for t in list(b.GetTracks()):
        b.Remove(t)
    for z in list(b.Zones()):
        b.Remove(z)
    rt = PF(b)
    sol = dst.replace('.kicad_pcb', '_solution.json')
    if '--resume' in sys.argv and os.path.exists(sol):
        # reuse a finished routing (net name -> tracks, jumpers) instead of routing again
        d = json.load(open(sol))
        rt.tracks = {rt.codes[k]: [(w, [tuple(p) for p in pts]) for w, pts in v] for k, v in d['tracks'].items()}
        rt.jumpers = {rt.codes[k]: [(tuple(a), tuple(c)) for a, c in v] for k, v in d['jumpers'].items()}
        rt.failed = d['failed']
        rt.rebuild()
        rr = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--reroute=')]
        for nm in (rr[0].split(',') if rr else []):
            n = rt.codes[nm]
            rt.tracks[n] = []; rt.jumpers[n] = []
            rt.rebuild()
            f = rt.route_net(n)
            print('rerouted %s: %s, jumpers %d' % (nm, 'FAILED %s' % rt.failed.get(nm) if f else 'ok', len(rt.jumpers.get(n, []))))
    else:
        rt.prepare()
        print('fixed nets routed: jumpers %d, failed %s' % (rt.njump(), rt.failed))
        rt.negotiate(iters)
        rt.legalise()
        flt = lambda p: [float(p[0]), float(p[1])]
        json.dump({'tracks': {rt.names[n]: [(float(w), [flt(p) for p in pts]) for w, pts in v] for n, v in rt.tracks.items()},
                   'jumpers': {rt.names[n]: [(flt(a), flt(c)) for a, c in v] for n, v in rt.jumpers.items()},
                   'failed': rt.failed}, open(sol, 'w'))
    table = rt.write()
    R.add_gnd_zone(b)
    b.Save(dst)
    json.dump({'jumpers': table, 'failed': rt.failed}, open(dst.replace('.kicad_pcb', '_route.json'), 'w'), indent=1)
    print('jumpers:', len(table), 'failed:', rt.failed)
