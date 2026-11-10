"""Draw the board (bottom copper seen from the component side) to a PNG for review.
Usage: python3 view.py <board> <out.png> [x0 y0 x1 y1]"""
import sys, math
import pcbnew
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle
from matplotlib.collections import PatchCollection, LineCollection
MMf = pcbnew.ToMM

def poly_of(pad, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    pad.TransformShapeToPolygon(ps, layer, 0, pcbnew.FromMM(0.02))
    if ps.OutlineCount() == 0:
        return None
    ol = ps.Outline(0)
    return [(MMf(ol.CPoint(i).x), MMf(ol.CPoint(i).y)) for i in range(ol.PointCount())]

def draw(board_path, out, win=None, labels=True, nets=False):
    b = pcbnew.LoadBoard(board_path)
    x0, y0, x1, y1 = win or (0, 0, 180, 130)
    scale = 0.11 if not win else min(0.5, 22.0 / max(x1 - x0, y1 - y0))
    fig, ax = plt.subplots(figsize=((x1 - x0) * scale, (y1 - y0) * scale), dpi=100)
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect('equal')
    ax.add_patch(Rectangle((0, 0), 180, 130, fill=False, ec='k', lw=1))
    # zones (filled)
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        col = '#cfe8cf' if z.GetNetname() == 'GND' else '#f3d9b0'
        for L in (pcbnew.B_Cu,):
            if not z.IsOnLayer(L):
                continue
            ps = z.GetFilledPolysList(L)
            for i in range(ps.OutlineCount()):
                ol = ps.Outline(i)
                pts = [(MMf(ol.CPoint(k).x), MMf(ol.CPoint(k).y)) for k in range(ol.PointCount())]
                if len(pts) > 2:
                    ax.add_patch(Polygon(pts, closed=True, fc=col, ec='none', zorder=1))
    segs, lws, cols = [], [], []
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            ax.add_patch(Circle((MMf(p.x), MMf(p.y)), MMf(t.GetWidth()) / 2, fc='#d040d0', ec='none', zorder=4))
            continue
        a, c = t.GetStart(), t.GetEnd()
        w = MMf(t.GetWidth())
        top = t.GetLayer() == pcbnew.F_Cu
        ax.plot([MMf(a.x), MMf(c.x)], [MMf(a.y), MMf(c.y)], color='#d040d0' if top else '#2060c0',
                lw=(0.8 if top else w * scale * 72 / 1.0 * 0.0393701 * 25.4 / 25.4), solid_capstyle='round',
                ls='--' if top else '-', zorder=5 if top else 3, alpha=0.9)
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        bottom = fp.GetLayer() == pcbnew.B_Cu
        for g in fp.GraphicalItems():
            if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                bb = g.GetBoundingBox()
                ax.add_patch(Rectangle((MMf(bb.GetLeft()), MMf(bb.GetTop())), MMf(bb.GetWidth()), MMf(bb.GetHeight()),
                                       fill=False, ec='#c05050' if bottom else '#888888', lw=0.5, ls=':' if bottom else '-', zorder=2))
        for pad in fp.Pads():
            pts = poly_of(pad, pcbnew.B_Cu)
            if pts:
                nm = pad.GetNetname()
                fc = '#e09020' if nm in ('PGND',) else '#30a030' if nm == 'GND' else '#c03030' if nm else '#aaaaaa'
                ax.add_patch(Polygon(pts, closed=True, fc=fc, ec='none', zorder=6, alpha=0.9))
            if pad.GetDrillSize().x > 0:
                p = pad.GetPosition()
                ax.add_patch(Circle((MMf(p.x), MMf(p.y)), MMf(pad.GetDrillSize().x) / 2, fc='w', ec='none', zorder=7))
            if nets and pad.GetNetname():
                p = pad.GetPosition()
                ax.text(MMf(p.x), MMf(p.y), pad.GetNetname().split('/')[-1], fontsize=3.2, ha='center', va='center', zorder=9, color='k')
        if labels:
            bb = fp.GetBoundingBox(False, False)
            c = bb.GetCenter()
            ax.text(MMf(c.x), MMf(c.y), ref, fontsize=5 if not win else 7, ha='center', va='center', color='#000080', zorder=8)
    ax.set_xticks(range(int(x0), int(x1) + 1, 10)); ax.set_yticks(range(int(y0), int(y1) + 1, 10))
    ax.tick_params(labelsize=6); ax.grid(True, lw=0.2, color='#cccccc')
    fig.tight_layout(pad=0.2)
    fig.savefig(out)
    plt.close(fig)

if __name__ == '__main__':
    win = tuple(float(v) for v in sys.argv[3:7]) if len(sys.argv) >= 7 else None
    draw(sys.argv[1], sys.argv[2], win, nets='--nets' in sys.argv)
