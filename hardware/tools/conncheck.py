"""Independent connectivity check for the single-sided board.

For every net: union all B.Cu copper (pads, tracks, filled zone), find the copper islands,
then join the islands that a wire jumper (W footprint) links. The net is complete when all
its pads end up in one group. Also checks that no two different nets' copper touch.

Usage: python3 conncheck.py <board.kicad_pcb>   -> exit code 0 when every net is complete"""
import sys, re, collections
import pcbnew
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

TOMM = pcbnew.ToMM

def poly_of(ps):
    out = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        pts = [(TOMM(ol.CPoint(k).x), TOMM(ol.CPoint(k).y)) for k in range(ol.PointCount())]
        if len(pts) >= 3:
            holes = []
            for h in range(ps.HoleCount(i)):
                hl = ps.Hole(i, h)
                holes.append([(TOMM(hl.CPoint(k).x), TOMM(hl.CPoint(k).y)) for k in range(hl.PointCount())])
            out.append(Polygon(pts, holes).buffer(0))
    return out

def check(path, verbose=True):
    b = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    shapes = collections.defaultdict(list)       # net -> copper shapes
    pads = collections.defaultdict(list)         # net -> [(ref, pad, Point)]
    jumpers = []                                 # (net, [points])
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        jp = []
        for p in fp.Pads():
            net = p.GetNetname()
            if not net or not p.IsOnLayer(pcbnew.B_Cu):
                continue
            ps = pcbnew.SHAPE_POLY_SET()
            p.TransformShapeToPolygon(ps, pcbnew.B_Cu, 0, pcbnew.FromMM(0.01))
            shapes[net] += poly_of(ps)
            c = p.GetPosition()
            pt = Point(TOMM(c.x), TOMM(c.y))
            pads[net].append((ref, p.GetNumber(), pt))
            jp.append(pt)
        if re.fullmatch(r'W\d+', ref) and jp:
            jumpers.append((fp.Pads()[0].GetNetname(), jp))
    for t in b.GetTracks():
        if t.GetLayer() != pcbnew.B_Cu:
            continue
        a, c = t.GetStart(), t.GetEnd()
        line = LineString([(TOMM(a.x), TOMM(a.y)), (TOMM(c.x), TOMM(c.y))]) if a != c else Point(TOMM(a.x), TOMM(a.y))
        shapes[t.GetNetname()].append(line.buffer(TOMM(t.GetWidth()) / 2, 8))
    for z in b.Zones():
        if z.IsOnLayer(pcbnew.B_Cu) and not z.GetIsRuleArea():
            shapes[z.GetNetname()] += poly_of(z.GetFilledPolysList(pcbnew.B_Cu))
    bad, merged = {}, {}
    for net, lst in shapes.items():
        u = unary_union(lst)
        islands = list(u.geoms) if hasattr(u, 'geoms') else [u]
        merged[net] = u
        def island(pt):
            for i, g in enumerate(islands):
                if g.distance(pt) < 1e-3:
                    return i
            return None
        par = list(range(len(islands)))
        def f(i):
            while par[i] != i:
                par[i] = par[par[i]]; i = par[i]
            return i
        for jnet, pts in jumpers:
            if jnet != net:
                continue
            ids = [island(p) for p in pts]
            for i in ids[1:]:
                par[f(ids[0])] = f(i)
        groups = collections.defaultdict(list)
        for ref, num, pt in pads[net]:
            i = island(pt)
            groups[f(i) if i is not None else ('none', ref, num)].append('%s.%s' % (ref, num))
        if len(groups) > 1:
            bad[net] = sorted(groups.values(), key=len)[:-1]
    # shorts: copper of two different nets touching
    # the shunt's Kelvin taps touch their force pads on purpose (net tie inside R201)
    tie = set()
    for fp in b.GetFootprints():
        if fp.GetReference() == 'R201':
            pn = {p.GetNumber(): p.GetNetname() for p in fp.Pads()}
            tie = {frozenset((pn['1'], pn['2'])), frozenset((pn['3'], pn['4']))}
    shorts = []
    nets = list(merged)
    for i, a in enumerate(nets):
        for c in nets[i + 1:]:
            if frozenset((a, c)) in tie:
                continue
            if merged[a].intersects(merged[c]) and merged[a].intersection(merged[c]).area > 1e-4:
                shorts.append((a, c))
    if verbose:
        print('nets checked: %d, wire jumpers: %d' % (len(shapes), len(jumpers)))
        print('incomplete nets: %s' % (bad or 'none'))
        print('shorts between nets: %s' % (shorts or 'none'))
    return bad, shorts

if __name__ == '__main__':
    bad, shorts = check(sys.argv[1])
    sys.exit(1 if bad or shorts else 0)
