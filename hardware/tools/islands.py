"""Find GND pour islands with no via or through-hole GND pad (so not tied to the other
layer) and drop a stitching via inside each, where the other layer's pour is.
Usage: python3 islands.py <in> <out>"""
import sys
import pcbnew
from shapely.geometry import Polygon, Point

MM = pcbnew.FromMM
b = pcbnew.LoadBoard(sys.argv[1])
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
gnd = b.GetNetcodeFromNetname('GND')


def polys(layer):
    out = []
    for z in b.Zones():
        if z.GetNetCode() != gnd or z.GetIsRuleArea() or z.GetLayer() != layer:
            continue
        ps = z.GetFilledPolysList(layer)
        for i in range(ps.OutlineCount()):
            ol = ps.Outline(i)
            outer = [(pcbnew.ToMM(ol.CPoint(k).x), pcbnew.ToMM(ol.CPoint(k).y)) for k in range(ol.PointCount())]
            holes = []
            for h in range(ps.HoleCount(i)):
                hl = ps.Hole(i, h)
                holes.append([(pcbnew.ToMM(hl.CPoint(k).x), pcbnew.ToMM(hl.CPoint(k).y)) for k in range(hl.PointCount())])
            out.append(Polygon(outer, holes).buffer(0))
    return out


from shapely.geometry import LineString
F, B = polys(pcbnew.F_Cu), polys(pcbnew.B_Cu)
nodes = [('F', p) for p in F] + [('B', p) for p in B]
parent = list(range(len(nodes)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
def union(i, j):
    parent[find(i)] = find(j)
def touching(geom, layers):
    return [i for i, (L, p) in enumerate(nodes) if L in layers and p.intersects(geom)]
# extra nodes: tracks, vias, pads
items = []
for t in b.GetTracks():
    if t.GetNetCode() != gnd:
        continue
    if t.GetClass() == 'PCB_VIA':
        pt = Point(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
        items.append((pt.buffer(pcbnew.ToMM(t.GetWidth()) / 2), 'FB'))
    else:
        a_, e_ = t.GetStart(), t.GetEnd()
        ln = LineString([(pcbnew.ToMM(a_.x), pcbnew.ToMM(a_.y)), (pcbnew.ToMM(e_.x), pcbnew.ToMM(e_.y))])
        items.append((ln.buffer(pcbnew.ToMM(t.GetWidth()) / 2), 'F' if t.GetLayer() == pcbnew.F_Cu else 'B'))
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetCode() != gnd:
            continue
        pt = Point(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
        r = pcbnew.ToMM(max(p.GetSize().x, p.GetSize().y)) / 2 + 0.9     # pad + thermal spoke reach
        items.append((pt.buffer(r), 'FB' if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else 'F'))
base = len(nodes)
for k, (g, lay) in enumerate(items):
    nodes.append(('item', g)); parent.append(base + k)
    for i in touching(g, lay):
        union(base + k, i)
# items touching each other on a shared layer (tracks end on pads/vias)
for k1 in range(len(items)):
    for k2 in range(k1 + 1, len(items)):
        g1, l1 = items[k1]; g2, l2 = items[k2]
        if set(l1) & set(l2) and g1.intersects(g2):
            union(base + k1, base + k2)
comps = {}
for i in range(len(nodes)):
    comps.setdefault(find(i), []).append(i)
main = max(comps.values(), key=lambda c: sum(nodes[i][1].area for i in c if nodes[i][0] in 'FB'))
added = 0
for c in comps.values():
    if c is main:
        continue
    isl = [i for i in c if nodes[i][0] in ('F', 'B')]
    for i in isl:
        L, poly = nodes[i]
        others = [p for j, (L2, p) in enumerate(nodes[:base]) if L2 != L and j in main]
        core = poly.buffer(-0.9)
        done = False
        for op in others:
            spot = core.intersection(op.buffer(-0.9))
            if not spot.is_empty:
                pt = spot.representative_point()
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(MM(float(pt.x)), MM(float(pt.y))))
                v.SetWidth(MM(0.8)); v.SetDrill(MM(0.4)); v.SetNet(b.GetNetsByNetcode()[gnd])
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                b.Add(v); added += 1; done = True
                print('island via', L, round(pt.x, 2), round(pt.y, 2), 'island area', round(poly.area, 1))
                break
        if not done:
            print('isolated island, no via spot:', L, round(poly.area, 1), poly.representative_point())
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2])
print('added', added)
