"""Create the single-sided PCB (KiCad 7 format) from the exported netlist.

- Board outline, mounting holes and the big parts are placed by hand (FIXED).
- Small through-hole parts (resistors, diodes, small caps, TO-92) go into a grid of
  vertical "slots"; a simulated-annealing pass assigns parts to slots so that the
  total wire length is short.
- All copper is on B.Cu. Through-hole parts sit on the top, the two SMD parts
  (shunt R201, op-amp U301) are soldered on the copper side.
- Pads are enlarged so they survive milling and drilling without plating.

Usage: python3 pcbgen.py <netlist> <project dir> [seed]"""
import sys, os, json, re, math, random
import pcbnew
from sexp import parse, find

W, H = 180.0, 130.0
MM = pcbnew.FromMM
TOMM = pcbnew.ToMM

def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))

# ---------------------------------------------------------------- fixed placements: ref -> (x, y, rot)
FIXED = {
    'H101': (4, 4, 0), 'H102': (176, 68, 0), 'H103': (4, 126, 0), 'H104': (176, 126, 0),
    # left edge, wire entry facing left. Order chosen so VIN, +12V and CHG_OUT leave without crossing.
    'J102': (7, 27.24, 90), 'J101': (7, 35, 270), 'J401': (7, 48, 270),
    'C102': (16, 48, 90), 'C101': (16.6, 56.5, 270),
    'D102': (22, 38.24, 90), 'D101': (27, 36, 90),
    # top-left: thermostat, 5 V regulator, safety relay K4
    'J104': (14, 6, 0), 'U101': (20.5, 14, 0), 'K4': (32, 18.5, 0),
    # top edge: fans, Peltier relay and output (wire entry up)
    'J704': (57.08, 6, 180), 'J706': (68.08, 6, 180), 'J705': (79.08, 6, 180), 'J702': (92.08, 6, 180),
    'K3': (54, 17, 0), 'Q703': (60, 34, 0),
    # Blue Pill, USB end at the top edge (J801 = B12 row, pin 1 at the USB end)
    'J801': (158, 12, 0), 'J802': (173.24, 60.26, 180),
    'J803': (150, 22.16, 0), 'JP801': (150, 52.64, 0),
    # protection comparators
    'U601': (116, 14, 0), 'U602': (136, 14, 0),
    # measurement: ADS1115 socket (module body lies to the right), NTCs on the right edge, Kelvin sense
    'U501': (150, 70, 0),
    'J501': (173, 75.5, 270), 'J502': (173, 87, 270), 'J503': (173, 98.5, 270), 'J504': (173, 110, 270),
    'J206': (130, 124, 0),
    'U401': (126, 98, 0),
    # load control loop
    'U301': (101, 98, 0), 'R312': (124.5, 109.5, 270),
    # high-current loop along the bottom edge
    'K1': (17, 97, 0), 'K2': (53, 97, 0), 'J205': (40, 122, 0), 'R201': (57, 122, 0), 'JP201': (62, 116, 0),
    'J301': (84, 122, 0), 'Q301': (118.9, 127, 180),
    'J402': (20, 74, 90),
}
BOTTOM = {'R201', 'U301'}            # SMD parts, soldered on the copper side
LOCKED = lambda ref: ref[0] in 'JKH' or ref in ('Q301', 'U501')
# areas where module bodies overhang the board (top side): low parts only / keep free
OVERHANG = {
    'Blue Pill': (160.0, 8.0, 171.4, 62.0),
    'ADS1115': (151.8, 68.0, 169.0, 96.0),
}
# slot regions for the small parts: (x0, y0, x1, y1)
SLOT_W, SLOT_H = 4.5, 13.97
REGIONS = [
    (10, 25.4, 156, 96),     # everything above the relays, left of the Blue Pill
    (84, 98, 170, 128),      # around the load loop and the measurement block
    (150, 64, 170, 98),      # under the ADS1115 module
    (96, 2, 114, 24),        # top centre
]
# every small part may only use slots inside the rectangles of its functional cluster
CLUSTER_RECT = {
    'P': [(30, 27, 62, 53)],                              # K4 driver, 5 V regulator caps
    'CI': [(12, 53, 54, 66), (14, 67, 44, 96)],                             # charger FB injection (next to J402)
    'RD': [(14, 67, 84, 96)],                             # K1/K2 drivers and interlock
    'T': [(52, 39, 73, 66)],                              # Peltier relay / PWM
    'F': [(84, 25, 112, 38)],                             # fan driver
    'LA': [(73, 39, 126, 96), (86, 98, 124, 118), (44, 67, 84, 96)],        # load loop, current monitor, PWM filter
    'PR': [(84, 39, 156, 66), (96, 2, 114, 24)],          # protection
    'ME': [(112, 67, 172, 98), (150, 64, 172, 98), (136, 98, 172, 128)],   # measurement, charger amplifier
}
# hand-drawn copper of the 11 A loop (see route1.py PRE): no parts here
KEEPOUT = [(0, 8, 5.6, 130), (0, 123.8, 111, 130), (37.5, 106, 54, 125), (76, 106, 87, 125), (89, 117.6, 116.5, 130)]
def cluster_of(ref):
    n = ref.lstrip('RCQDUJP')
    sheet = n[0]
    if sheet == '1': return 'P'
    if sheet == '2': return 'RD'
    if sheet == '3': return 'LA'
    if sheet == '4':
        return 'CI' if ref in ('R401', 'R402', 'C401', 'C402', 'D401', 'D402', 'R405') else 'ME'
    if sheet == '5': return 'ME'
    if sheet == '7':
        return 'F' if ref in ('Q702', 'R705', 'R706', 'D703') else 'T'
    return 'PR'

# ---------------------------------------------------------------- helpers
def courtyard(fp):
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            b = g.GetBoundingBox()
            xs += [b.GetLeft(), b.GetRight()]; ys += [b.GetTop(), b.GetBottom()]
    if not xs:
        b = fp.GetBoundingBox(False, False)
        xs, ys = [b.GetLeft(), b.GetRight()], [b.GetTop(), b.GetBottom()]
    return [TOMM(v) for v in (min(xs), min(ys), max(xs), max(ys))]

def add_rect(board, layer, x0, y0, x1, y1, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(V(x0, y0)); s.SetEnd(V(x1, y1))
    s.SetLayer(layer); s.SetWidth(MM(width))
    board.Add(s)

def add_text(board, txt, x, y, size=1.2, layer=pcbnew.F_SilkS, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt); t.SetPosition(V(x, y)); t.SetLayer(layer)
    t.SetTextSize(V(size, size)); t.SetTextThickness(MM(size * 0.15))
    if mirror:
        t.SetMirrored(True)
    board.Add(t)

DRILLS = [0.8, 1.0, 1.3, 1.5, 1.8, 2.0, 3.2]

def fix_pads(fp):
    """Bottom-copper-only pads, large enough for a milled board without plated holes."""
    pads = list(fp.Pads())
    for pad in pads:
        if pad.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
            continue
        d = TOMM(pad.GetDrillSize().x)
        d2 = min([x for x in DRILLS if x >= d - 0.06] or [d])
        pad.SetDrillSize(V(d2, d2))
        p = pad.GetPosition()
        near, ang = 1e9, 0.0
        for q in pads:
            if q is pad or q.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                continue
            qp = q.GetPosition()
            dist = math.hypot(TOMM(qp.x - p.x), TOMM(qp.y - p.y))
            if dist < near:
                near, ang = dist, math.degrees(math.atan2(qp.y - p.y, qp.x - p.x))
        big = max(d2 + 1.2, 2.0)
        if d2 >= 1.5:
            big = d2 + 1.8
        pad.SetShape(pcbnew.PAD_SHAPE_OVAL)
        if near < big + 0.6:
            narrow = max(near - 0.7, d2 + 0.8)      # annular ring >= 0.4 mm
            # narrow along the direction to the neighbour, long across it
            rel = (ang - pad.GetOrientation().AsDegrees()) % 180
            along_x = min(rel, 180 - rel) < 45
            long_ = min(big + 0.6, 3.4)
            pad.SetSize(V(narrow, long_) if along_x else V(long_, narrow))
        else:
            pad.SetSize(V(big, big))
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.B_Cu); ls.AddLayer(pcbnew.B_Mask); ls.AddLayer(pcbnew.F_Mask)
        pad.SetLayerSet(ls)

# ---------------------------------------------------------------- build
def build(netfile, proj, seed=1):
    net = parse(open(netfile).read())[0]
    lib = os.path.join(proj, 'lib', 'cell_bench.pretty')
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    netmap, padnet = {}, {}
    for n in find(find(net, 'nets')[0], 'net'):
        name = str(find(n, 'name')[0][1])
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni
        for nd in find(n, 'node'):
            padnet[(str(find(nd, 'ref')[0][1]), str(find(nd, 'pin')[0][1]))] = ni
    fps = {}
    for c in find(find(net, 'components')[0], 'comp'):
        ref = str(find(c, 'ref')[0][1])
        fpname = str(find(c, 'footprint')[0][1]).split(':')[1]
        fp = pcbnew.FootprintLoad(lib, fpname)
        fp.SetFPIDAsString('cell_bench:' + fpname)
        fp.SetReference(ref)
        fp.SetValue(str(find(c, 'value')[0][1]))
        sp = str(find(find(c, 'sheetpath')[0], 'tstamps')[0][1])
        fp.SetPath(pcbnew.KIID_PATH(sp + str(find(c, 'tstamps')[0][1])))
        for pad in fp.Pads():
            ni = padnet.get((ref, pad.GetNumber()))
            if ni is not None:
                pad.SetNet(ni)
        fix_pads(fp)
        board.Add(fp)
        fps[ref] = fp
    # ------------------------------------------------ fixed parts
    occupied = []          # (x0, y0, x1, y1, ref)
    for ref, (x, y, rot) in FIXED.items():
        fp = fps[ref]
        fp.SetPosition(V(x, y))
        fp.SetOrientationDegrees(rot)
        if ref in BOTTOM:
            fp.Flip(V(x, y), False)
        occupied.append(tuple(courtyard(fp)) + (ref,))
        if LOCKED(ref):
            fp.SetLocked(True)
    for i, k in enumerate(KEEPOUT):
        occupied.append(tuple(k) + ('X%d' % i,))
    # ------------------------------------------------ slots
    def blocked(r):
        if r[0] < 1.5 or r[1] < 1.5 or r[2] > W - 1.5 or r[3] > H - 1.5:
            return True
        for o in occupied:
            m = 1.6 if o[4][0] in 'UJ' else 0.3      # leave an escape channel around ICs, sockets, relays
            if not (r[2] <= o[0] - m or r[0] >= o[2] + m or r[3] <= o[1] - m or r[1] >= o[3] + m):
                return True
        ox = OVERHANG['Blue Pill']
        return not (r[2] <= ox[0] or r[0] >= ox[2] or r[3] <= ox[1] or r[1] >= ox[3])
    slots = []
    for (x0, y0, x1, y1) in REGIONS:
        y = y0 + 1.3
        while y + 10.16 + 1.3 <= y1 + 1e-6:
            x = x0 + 2.2
            while x + 2.2 <= x1 + 1e-6:
                r = (x - 2.3, y - 1.4, x + 2.3, y + 10.16 + 1.4)
                if not blocked(r) and all(abs(x - s[0]) >= SLOT_W - 0.01 or abs(y - s[1]) >= SLOT_H - 0.01 for s in slots):
                    slots.append((round(x, 2), round(y, 2)))
                x += SLOT_W
            y += SLOT_H
    movable = [r for r in fps if r not in FIXED]
    if len(movable) > len(slots):
        raise SystemExit('not enough slots: %d parts, %d slots' % (len(movable), len(slots)))
    # pad geometry of every movable part: pads lie on a line, length p
    geo = {}
    for ref in movable:
        fp = fps[ref]
        fp.SetPosition(V(0, 0)); fp.SetOrientationDegrees(0)
        pads = [(pd.GetNumber(), TOMM(pd.GetPosition().x), TOMM(pd.GetPosition().y), pd.GetNetname()) for pd in fp.Pads()]
        assert all(abs(py) < 1e-6 for _, _, py, _ in pads), ref
        p = max(px for _, px, _, _ in pads)
        geo[ref] = (p, pads)

    def pad_xy(ref, slot, flip):
        """absolute pad positions for a part in a slot. flip=False: pad 1 on top."""
        p, pads = geo[ref]
        sx, sy = slot
        off = (10.16 - p) / 2
        return [(nm, sx, (sy + off + px) if not flip else (sy + off + p - px)) for _, px, _, nm in pads]

    # ---- cost: wire length (MST) + crossings between straight MST edges of different nets.
    # A crossing is roughly one wire jumper on a single-sided board, so it is weighted heavily.
    import numpy as np
    SKIP = {'GND', 'PGND', ''}
    LAMBDA = 12.0
    fixed_pts = {}
    for ref in FIXED:
        for pd in fps[ref].Pads():
            nm = pd.GetNetname()
            if nm in SKIP:
                continue
            fixed_pts.setdefault(nm, []).append((TOMM(pd.GetPosition().x), TOMM(pd.GetPosition().y)))
    WEIGHT = {'ISNS_N': 3, 'ISNS_G': 3, 'SENSE_P': 2, 'SENSE_N': 2}
    rnd = random.Random(seed)
    allowed = {}
    for ref in movable:
        rects = CLUSTER_RECT[cluster_of(ref)]
        cx0, cy0, cx1, cy1 = courtyard(fps[ref])
        wide = min(cx1 - cx0, cy1 - cy0) > SLOT_W - 0.2      # TO-92, 5 mm electrolytics: never side by side
        allowed[ref] = [i for i, (sx, sy) in enumerate(slots)
                        if any(x0 <= sx <= x1 and y0 <= sy and sy + 10.16 <= y1 for (x0, y0, x1, y1) in rects)
                        and (not wide or int(round(sx / SLOT_W)) % 2 == 0)]
    import collections
    need = collections.Counter(cluster_of(r) for r in movable)
    cap = {k: len([1 for (sx, sy) in slots if any(x0 <= sx <= x1 and y0 <= sy and sy + 10.16 <= y1 for (x0, y0, x1, y1) in v)]) for k, v in CLUSTER_RECT.items()}
    print('cluster need/capacity:', {k: (need[k], cap[k]) for k in CLUSTER_RECT})
    # initial assignment: bipartite matching (parts -> allowed slots), randomised
    match = {}                      # slot -> ref
    def try_place(ref, seen):
        opts = list(allowed[ref]); rnd.shuffle(opts)
        for i in opts:
            if i in seen:
                continue
            seen.add(i)
            if i not in match or try_place(match[i], seen):
                match[i] = ref
                return True
        return False
    sys.setrecursionlimit(10000)
    for ref in sorted(movable, key=lambda r: len(allowed[r])):
        if not try_place(ref, set()):
            raise SystemExit('no free slot for %s (cluster %s)' % (ref, cluster_of(ref)))
    assign = {ref: (i, False) for i, ref in match.items()}
    owner = {assign[r][0]: r for r in movable}
    nets_of = {r: sorted({nm for _, _, _, nm in geo[r][1] if nm not in SKIP}) for r in movable}
    members = {}
    for r in movable:
        for nm in nets_of[r]:
            members.setdefault(nm, []).append(r)
    allnets = sorted(set(members) | set(fixed_pts))
    nid = {nm: i for i, nm in enumerate(allnets)}

    def mst(nm):
        pts = list(fixed_pts.get(nm, []))
        for r in members.get(nm, []):
            si, fl = assign[r]
            pts += [(x, y) for n2, x, y in pad_xy(r, slots[si], fl) if n2 == nm]
        n = len(pts)
        if n < 2:
            return np.zeros((0, 4)), 0.0
        if n == 2:
            (x1, y1), (x2, y2) = pts
            return np.array([[x1, y1, x2, y2]]), math.hypot(x2 - x1, y2 - y1)
        intree = [False] * n
        dist = [1e18] * n; par = [0] * n
        dist[0] = 0.0
        ed = []; tot = 0.0
        for _ in range(n):
            j = min((i for i in range(n) if not intree[i]), key=lambda i: dist[i])
            intree[j] = True
            if j:
                ed.append((pts[par[j]][0], pts[par[j]][1], pts[j][0], pts[j][1])); tot += dist[j]
            xj, yj = pts[j]
            for i in range(n):
                if not intree[i]:
                    dd = math.hypot(pts[i][0] - xj, pts[i][1] - yj)
                    if dd < dist[i]:
                        dist[i] = dd; par[i] = j
        return np.array(ed), tot

    def ncross(A, B):
        if len(A) == 0 or len(B) == 0:
            return 0
        ax1, ay1, ax2, ay2 = [A[:, i][:, None] for i in range(4)]
        bx1, by1, bx2, by2 = [B[:, i][None, :] for i in range(4)]
        d1 = (bx2 - bx1) * (ay1 - by1) - (by2 - by1) * (ax1 - bx1)
        d2 = (bx2 - bx1) * (ay2 - by1) - (by2 - by1) * (ax2 - bx1)
        d3 = (ax2 - ax1) * (by1 - ay1) - (ay2 - ay1) * (bx1 - ax1)
        d4 = (ax2 - ax1) * (by2 - ay1) - (ay2 - ay1) * (bx2 - ax1)
        return int(np.count_nonzero((d1 * d2 < 0) & (d3 * d4 < 0)))

    edges, length = {}, {}
    for nm in allnets:
        edges[nm], length[nm] = mst(nm)
    state = {}
    def rebuild_all():
        state['E'] = np.concatenate([edges[nm] for nm in allnets if len(edges[nm])])
        state['N'] = np.concatenate([np.full(len(edges[nm]), nid[nm]) for nm in allnets if len(edges[nm])])
    rebuild_all()

    def part_cost(S, E_s):
        """wire length of nets S plus crossings that involve them (E_s: their edges)."""
        ids = [nid[nm] for nm in S]
        oth = state['E'][~np.isin(state['N'], ids)]
        c = 0
        for nm in S:
            c += ncross(E_s[nm], oth)
        for i in range(len(S)):
            for j in range(i + 1, len(S)):
                c += ncross(E_s[S[i]], E_s[S[j]])
        return c

    def total_cross():
        c = 0
        for i, a in enumerate(allnets):
            for bnm in allnets[i + 1:]:
                c += ncross(edges[a], edges[bnm])
        return c

    steps = 120000
    T0, T1 = 25.0, 0.3
    for it in range(steps):
        T = T0 * (T1 / T0) ** (it / steps)
        a = rnd.choice(movable)
        sa, fa = assign[a]
        if rnd.random() < 0.15:
            b_ = None; new_a = (sa, not fa); new_b = None
        else:
            sb = rnd.choice(allowed[a])
            if sb == sa:
                continue
            b_ = owner.get(sb)
            if b_ and sa not in allowed[b_]:
                continue
            new_a = (sb, fa); new_b = (sa, assign[b_][1]) if b_ else None
        S = sorted(set(nets_of[a]) | (set(nets_of[b_]) if b_ else set()))
        if not S:
            continue
        old_e = {nm: edges[nm] for nm in S}
        before = sum(WEIGHT.get(nm, 1) * length[nm] for nm in S) + LAMBDA * part_cost(S, old_e)
        old_a, old_b = assign[a], (assign[b_] if b_ else None)
        assign[a] = new_a
        if b_:
            assign[b_] = new_b
        new_e, new_l = {}, {}
        for nm in S:
            new_e[nm], new_l[nm] = mst(nm)
        after = sum(WEIGHT.get(nm, 1) * new_l[nm] for nm in S) + LAMBDA * part_cost(S, new_e)
        if after <= before or rnd.random() < math.exp((before - after) / T):
            for nm in S:
                edges[nm] = new_e[nm]; length[nm] = new_l[nm]
            rebuild_all()
            if b_ is None and new_a[0] != sa:
                owner.pop(sa, None)
            if new_a[0] != sa:
                owner[new_a[0]] = a
                if b_:
                    owner[sa] = b_
        else:
            assign[a] = old_a
            if b_:
                assign[b_] = old_b
    total = (round(sum(length.values())), total_cross())
    for ref in movable:
        si, fl = assign[ref]
        p, pads = geo[ref]
        sx, sy = slots[si]
        off = (10.16 - p) / 2
        fp = fps[ref]
        if not fl:
            fp.SetOrientationDegrees(270); fp.SetPosition(V(sx, sy + off))
        else:
            fp.SetOrientationDegrees(90); fp.SetPosition(V(sx, sy + off + p))
    # ------------------------------------------------ outline, texts
    add_rect(board, pcbnew.Edge_Cuts, 0, 0, W, H, 0.1)
    for name, (x0, y0, x1, y1) in OVERHANG.items():
        add_rect(board, pcbnew.Dwgs_User, x0, y0, x1, y1, 0.1)
        add_text(board, name + ' (module body)', (x0 + x1) / 2, (y0 + y1) / 2, 1.0, pcbnew.Dwgs_User)
    add_text(board, 'USB', 165.6, 4.0, 1.5)
    add_text(board, 'B12', 154.2, 9.0, 1.0)
    add_text(board, 'GND', 176.2, 9.0, 1.0)
    path = os.path.join(proj, 'cell_test_bench.kicad_pcb')
    board.Save(path)
    return len(movable), len(slots), total

def netclasses(proj):
    """Net classes and design rules for a milled, single-sided board (KiCad 7 project format)."""
    pro_path = os.path.join(proj, 'cell_test_bench.kicad_pro')
    pro = json.load(open(pro_path))
    base = {"bus_width": 12, "clearance": 0.4, "diff_pair_gap": 0.4, "diff_pair_via_gap": 0.4,
            "diff_pair_width": 0.6, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
            "track_width": 0.6, "via_diameter": 2.4, "via_drill": 1.0, "wire_width": 6}
    classes = [dict(base, name="Default")]
    classes.append(dict(base, name='Loop11A', track_width=4.0))
    classes.append(dict(base, name='Power', track_width=1.6))
    classes.append(dict(base, name='Charge6A', track_width=2.6))
    pats = [{"netclass": "Loop11A", "pattern": p} for p in ['CELL_P', 'CELL_N', 'LOAD_P', 'LOAD_D', '/Cell_Relays/CELL_N', '/Electronic_Load/LOAD_D']]
    pats += [{"netclass": "Charge6A", "pattern": p} for p in ['CHG_OUT']]
    pats += [{"netclass": "Power", "pattern": p} for p in ['PGND', 'VIN', '+12V', '+12V_SW', '/Thermal/TEC_*', 'TEC_*']]
    pro['net_settings'] = {"classes": classes, "meta": {"version": 3}, "net_colors": None,
                           "netclass_assignments": None, "netclass_patterns": pats}
    pro.setdefault('board', {})
    pro['board']['design_settings'] = {
        "rules": {"min_clearance": 0.4, "min_track_width": 0.5, "min_via_diameter": 1.8,
                  "min_via_annular_width": 0.4, "min_through_hole_diameter": 0.8,
                  "min_copper_edge_clearance": 1.0, "min_hole_clearance": 0.4, "min_hole_to_hole": 0.5,
                  "min_silk_clearance": 0.0, "min_resolved_spokes": 1},
        "rule_severities": {"lib_footprint_issues": "ignore", "lib_footprint_mismatch": "ignore",
                            "silk_overlap": "ignore", "silk_over_copper": "ignore", "silk_edge_clearance": "ignore",
                            "text_height": "ignore", "text_thickness": "ignore"},
        "track_widths": [0.0, 0.5, 0.6, 0.8, 1.0, 1.6, 2.6, 4.0],
        "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 2.4, "drill": 1.0}],
        "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                     "copper_text_size_v": 1.5, "copper_text_thickness": 0.3, "silk_line_width": 0.15,
                     "silk_text_size_h": 1.0, "silk_text_size_v": 1.0, "silk_text_thickness": 0.15},
    }
    pro['boards'] = []
    json.dump(pro, open(pro_path, 'w'), indent=2)

if __name__ == '__main__':
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    print('parts in slots, slots, (wire length mm, crossings):', build(sys.argv[1], sys.argv[2], seed))
    netclasses(sys.argv[2])
