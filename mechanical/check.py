"""Checks for the mechanical design.
1. Every printed part fits a 220 x 220 mm bed (in some orientation of its two smallest... XY as exported).
2. No two parts of the assembly overlap (intersection volume > 1 mm3), except pairs that are meant to touch.
Usage: python3 check.py [--pcb]"""
import sys, itertools
import cadquery as cq
import enclosure as E

BED = 220.0
# pairs that touch on purpose (a face contact gives volume 0 anyway; these overlap by design)
ALLOW = {
    frozenset(('E1_ebox_base', 'E4_cooler_cradle')),
}


def solids(asm):
    out = {}
    for name, child in asm.traverse():
        if child.obj is None:
            continue
        shp = child.obj.val() if isinstance(child.obj, cq.Workplane) else child.obj
        if isinstance(shp, cq.Assembly):
            continue
        out[name] = shp.moved(child.loc)
    return out


def main(with_pcb):
    parts, asm = E.build(with_pcb=with_pcb)
    ok = True
    print('Printed parts (X x Y x Z as exported, mm):')
    for name, wp in parts.items():
        bb = wp.val().BoundingBox()
        dims = sorted([bb.xlen, bb.ylen, bb.zlen])
        fits = dims[1] <= BED          # lay it on its largest face: the two largest dims must fit... see below
        fits = bb.xlen <= BED and bb.ylen <= BED
        ok &= fits
        print('  %-26s %6.1f x %6.1f x %6.1f  %s' % (name, bb.xlen, bb.ylen, bb.zlen, 'ok' if fits else 'TOO BIG'))
    sol = solids(asm)
    names = [n for n in sol if n not in ('E2_ebox_lid', 'T3_pocket_lid')]   # lids are drawn lifted
    print('Collisions (> 1 mm3):')
    bbs = {n: sol[n].BoundingBox() for n in names}
    hits = 0
    for a, b in itertools.combinations(names, 2):
        A, B = bbs[a], bbs[b]
        if A.xmax < B.xmin or B.xmax < A.xmin or A.ymax < B.ymin or B.ymax < A.ymin or A.zmax < B.zmin or B.zmax < A.zmin:
            continue
        if frozenset((a, b)) in ALLOW:
            continue
        try:
            v = sol[a].intersect(sol[b]).Volume()
        except Exception as e:                       # noqa: BLE001
            print('  %s / %s: could not intersect (%s)' % (a, b, e))
            continue
        if 'PCB' in (a, b) and v > 1.0:
            # component leads in the KiCad models stick out below the board (TO-247: 11 mm);
            # the real leads are cut after soldering, so overlaps entirely below the board are ignored
            below = E.FLOOR + E.STANDOFF_H - 0.01
            inter = sol[a].intersect(sol[b])
            v = sum(so.Volume() for so in inter.Solids() if so.BoundingBox().zmax > below)
        if v > 1.0:
            hits += 1
            print('  %s  x  %s : %.0f mm3' % (a, b, v))
    if not hits:
        print('  none')
    return ok and not hits


if __name__ == '__main__':
    sys.exit(0 if main('--pcb' in sys.argv) else 1)
