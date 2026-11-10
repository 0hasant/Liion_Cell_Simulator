"""Post-route cleanup.
1. Put the wire-jumper pads where the router meant them (from <board>_route.json).
2. Remove dangling track stubs (repeat until none are left).
3. Merge collinear touching segments of the same net and width.
4. Refill the GND zone.
Usage: python3 cleanup.py <in.kicad_pcb> <out.kicad_pcb>"""
import sys, os, json, re, math
import pcbnew

MM, TOMM = pcbnew.FromMM, pcbnew.ToMM

JPAD, JDRILL = 2.4, 1.0
_KEEP = []          # removed board items must stay referenced, or SWIG frees them and corrupts the board
SNAP = 0.8          # jumper ends of the same net closer than this share one hole

def fix_jumpers(b, route_json, wires_json):
    """Rebuild the wire jumpers from the router's list. Jumpers of one net that meet at a
    point are merged into one footprint (one hole per point, several wires), so no hole is
    drilled twice. Writes the wire list to wires_json."""
    if not os.path.exists(route_json):
        return 0
    rows = json.load(open(route_json))['jumpers']
    nets = {}
    for code, n in b.GetNetsByNetcode().items():
        nets[n.GetNetname().split('/')[-1]] = n
    for fp in list(b.GetFootprints()):
        if re.fullmatch(r'W\d+', fp.GetReference()):
            b.Remove(fp); _KEEP.append(fp)
    bynet = {}
    for ref, net, a, c, ln in rows:
        bynet.setdefault(net, []).append((tuple(a), tuple(c)))
    wires, k = [], 0
    for net in sorted(bynet):
        pts = []                                   # distinct points of this net
        def pid(p):
            for i, q in enumerate(pts):
                if math.hypot(p[0] - q[0], p[1] - q[1]) < SNAP:
                    return i
            pts.append(p)
            return len(pts) - 1
        segs = [(pid(a), pid(c)) for a, c in bynet[net]]
        segs = [s for s in segs if s[0] != s[1]]
        # connected groups of segments
        parent = list(range(len(pts)))
        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]; i = parent[i]
            return i
        for i, j in segs:
            parent[find(i)] = find(j)
        groups = {}
        for s_ in segs:
            groups.setdefault(find(s_[0]), []).append(s_)
        for g in sorted(groups.values(), key=lambda g: pts[g[0][0]]):
            k += 1
            ref = 'W%d' % k
            ids = sorted({i for s_ in g for i in s_})
            num = {i: str(n + 1) for n, i in enumerate(ids)}
            x0, y0 = pts[ids[0]]
            fp = pcbnew.FOOTPRINT(b)
            fp.SetReference(ref); fp.SetValue('wire ' + net)
            fp.SetFPIDAsString('cell_bench:WireJumper')
            fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_THROUGH_HOLE)
            fp.SetPosition(pcbnew.VECTOR2I(MM(x0), MM(y0)))
            for i in ids:
                x, y = pts[i]
                pad = pcbnew.PAD(fp)
                pad.SetNumber(num[i]); pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE); pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
                pad.SetSize(pcbnew.VECTOR2I(MM(JPAD), MM(JPAD))); pad.SetDrillSize(pcbnew.VECTOR2I(MM(JDRILL), MM(JDRILL)))
                ls = pcbnew.LSET(); ls.AddLayer(pcbnew.B_Cu); ls.AddLayer(pcbnew.B_Mask)
                pad.SetLayerSet(ls)
                pad.SetPos0(pcbnew.VECTOR2I(MM(x - x0), MM(y - y0)))
                pad.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
                pad.SetNet(nets[net])
                fp.Add(pad)
            for n, (i, j) in enumerate(g):
                (xa, ya), (xb, yb) = pts[i], pts[j]
                ln_ = pcbnew.FP_SHAPE(fp)
                ln_.SetShape(pcbnew.SHAPE_T_SEGMENT)
                ln_.SetStart(pcbnew.VECTOR2I(MM(xa), MM(ya))); ln_.SetEnd(pcbnew.VECTOR2I(MM(xb), MM(yb)))
                ln_.SetLayer(pcbnew.F_SilkS); ln_.SetWidth(MM(0.3))
                fp.Add(ln_)
                wid = ref if len(g) == 1 else ref + 'abcdefghij'[n]
                wires.append(dict(ref=ref, wire=wid, net=net, pads=[num[i], num[j]], a=[xa, ya], b=[xb, yb],
                                  length=round(math.hypot(xb - xa, yb - ya), 1)))
            (xa, ya), (xb, yb) = pts[g[0][0]], pts[g[0][1]]
            fp.Reference().SetPosition(pcbnew.VECTOR2I(MM((xa + xb) / 2), MM((ya + yb) / 2 - 1.2)))
            fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.9), MM(0.9))); fp.Reference().SetTextThickness(MM(0.13))
            fp.Value().SetVisible(False)
            b.Add(fp)
    json.dump(wires, open(wires_json, 'w'), indent=1)
    return len(wires)

def drop_dangling(b):
    removed = 0
    while True:
        b.BuildConnectivity()
        conn = b.GetConnectivity()
        dead = []
        for t in b.GetTracks():
            if t.GetClass() != 'PCB_TRACK':
                continue
            if conn.TestTrackEndpointDangling(t, False):
                dead.append(t)
        if not dead:
            return removed
        for t in dead:
            b.Remove(t); _KEEP.append(t)
        removed += len(dead)

def tidy_text(b, W=180.0, H=130.0):
    """Hide footprint value labels (long module descriptions) and keep reference texts on the
    board, so exports sized to the board area are exactly 180 x 130 mm."""
    n = 0
    for fp in b.GetFootprints():
        fp.Value().SetVisible(False)
        for t in [fp.Reference()] + [g for g in fp.GraphicalItems() if g.GetClass() == 'FP_TEXT']:
            bb = t.GetBoundingBox()
            x0, y0, x1, y1 = (TOMM(bb.GetLeft()), TOMM(bb.GetTop()), TOMM(bb.GetRight()), TOMM(bb.GetBottom()))
            dx = (0.5 - x0) if x0 < 0.5 else ((W - 0.5) - x1 if x1 > W - 0.5 else 0)
            dy = (0.5 - y0) if y0 < 0.5 else ((H - 0.5) - y1 if y1 > H - 0.5 else 0)
            if dx or dy:
                p = t.GetPosition()
                t.SetPosition(pcbnew.VECTOR2I(p.x + MM(dx), p.y + MM(dy)))
                n += 1
    return n

def zero_length(b):
    n = 0
    for t in list(b.GetTracks()):
        if t.GetClass() == 'PCB_TRACK' and t.GetStart() == t.GetEnd():
            b.Remove(t); _KEEP.append(t); n += 1
    return n

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(src)
    nj = fix_jumpers(b, src.replace('.kicad_pcb', '_route.json'), dst.replace('.kicad_pcb', '_jumpers.json'))
    nz = zero_length(b)
    nt = tidy_text(b)
    nd = drop_dangling(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(dst)
    njf = len([f for f in b.GetFootprints() if re.fullmatch(r'W\d+', f.GetReference())])
    print('wires %d in %d jumper footprints, zero-length removed %d, dangling removed %d' % (nj, njf, nz, nd))
