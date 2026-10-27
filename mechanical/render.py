"""Render PNG previews of the assembly (matplotlib, no GPU needed).
Usage: python3 render.py [--pcb]"""
import os, sys, tempfile
import numpy as np
import cadquery as cq
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import enclosure as E

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'renders')


def meshes(asm, tol=0.4):
    out = []
    tmp = tempfile.mkdtemp()
    for name, child in asm.traverse():
        if child.obj is None:
            continue
        shape = child.obj.val() if isinstance(child.obj, cq.Workplane) else child.obj
        shape = shape.moved(child.loc)
        path = os.path.join(tmp, name.replace('/', '_') + '.stl')
        cq.exporters.export(cq.Workplane().add(shape), path, tolerance=tol, angularTolerance=0.5)
        m = trimesh.load(path)
        c = child.color.toTuple() if child.color else (0.6, 0.6, 0.6, 1.0)
        out.append((name, m, c))
    return out


def draw(items, path, elev, azim, title, skip=(), only=None, size=(1400, 950)):
    """Software z-buffer renderer (flat shading, orthographic)."""
    W, H = size
    e, a = np.radians(elev), np.radians(azim)
    # camera basis: d points from the target towards the camera
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])  # points from target to camera
    right = np.cross([0, 0, 1], d); right /= np.linalg.norm(right)
    up = np.cross(d, right)
    light = 0.6 * d + 0.5 * up + 0.3 * right; light /= np.linalg.norm(light)
    sel = [(n, m, c) for n, m, c in items
           if not any(s in n for s in skip) and (not only or any(o in n for o in only))]
    allv = np.vstack([m.vertices for _, m, _ in sel])
    P = np.c_[allv @ right, allv @ up]
    mn, mx = P.min(0), P.max(0)
    scale = 0.9 * min(W / (mx[0] - mn[0]), H / (mx[1] - mn[1]))
    off = np.array([W, H]) / 2 - scale * (mn + mx) / 2
    zbuf = np.full((H, W), -np.inf)
    img = np.ones((H, W, 3))
    for name, m, c in sel:
        v = m.vertices
        sx = v @ right * scale + off[0]
        sy = H - (v @ up * scale + off[1])
        sz = v @ d
        n = m.face_normals
        inten = 0.35 + 0.65 * np.abs(n @ light)
        col = np.array(c[:3])
        for f, it in zip(m.faces, inten):
            x, y, z = sx[f], sy[f], sz[f]
            x0, x1 = int(max(np.floor(x.min()), 0)), int(min(np.ceil(x.max()), W - 1))
            y0, y1 = int(max(np.floor(y.min()), 0)), int(min(np.ceil(y.max()), H - 1))
            if x1 < x0 or y1 < y0:
                continue
            den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(den) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            l0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
            l1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
            l2 = 1 - l0 - l1
            inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            if not inside.any():
                continue
            zz = l0 * z[0] + l1 * z[1] + l2 * z[2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            upd = inside & (zz > sub)
            sub[upd] = zz[upd]
            img[y0:y1 + 1, x0:x1 + 1][upd] = np.clip(col * it, 0, 1)
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(img); ax.set_axis_off()
    ax.text(20, 40, title, fontsize=14)
    fig.savefig(path)
    plt.close(fig)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    parts, asm = E.build(with_pcb='--pcb' in sys.argv)
    items = meshes(asm)
    draw(items, os.path.join(OUT, 'assembly_exploded.png'), 28, -60, 'Cell test bench: electronics box + thermal unit (lids lifted)')
    draw(items, os.path.join(OUT, 'electronics_box.png'), 55, -70, 'Electronics box (lid removed)',
         only=('E1_', 'PCB', 'load_', 'series_R', 'XL4016', 'MP1584', 'E3_'))
    draw(items, os.path.join(OUT, 'thermal_unit.png'), 30, -50, 'Thermal unit: cell pocket (21700 shown), Peltiers, heatsink',
         only=('T1_', 'T2_', 'T4_', 'T5_', 'T7_', 'cell_', 'cold_plate', 'TEC1', 'hot_side', 'BTS7960', 'thermal_pad'))
    draw(items, os.path.join(OUT, 'thermal_pocket_detail.png'), 50, -35, 'Pocket interior: contact blocks, saddle, 21700 cell',
         only=('T4_', 'T5_', 'T7_', 'cell_', 'cold_plate', 'thermal_pad', 'TEC1'))
    print('renders done')
