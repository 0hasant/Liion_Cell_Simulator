"""Cell test bench - enclosure and thermal cell pocket (CadQuery).

Two printable units, both under 220 x 220 mm:
  * Electronics box (E): main PCB, load MOSFET heatsink + 60 mm fan, two XL4016
    modules (stacked), MP1584. 214 x 214 x 89 mm.
  * Thermal unit (T): hot-side heatsink + 60 mm fan, 2x TEC1-12706, aluminium cold
    plate, insulated cell pocket with swappable saddles for 18650 / 21700,
    sliding contact block, BTS7960 driver. 130 x 130 mm footprint.

Run:  python3 enclosure.py           -> stl/*.stl, step/*.step, renders/*.png
      python3 enclosure.py --no-pcb  -> skip the (slow) KiCad board STEP import
"""
import os, sys, math
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_STL = os.path.join(HERE, 'stl')
OUT_STEP = os.path.join(HERE, 'step')
BOARD_STEP = os.path.join(HERE, '..', 'hardware', 'kicad', 'cell_test_bench.step')

# ============================================================== parameters
WALL, FLOOR = 3.0, 3.0
# electronics box
E_OUT = (214.0, 214.0)              # outer X, Y
E_H = 86.0                          # base height (without lid)
E_IN = (E_OUT[0] - 2 * WALL, E_OUT[1] - 2 * WALL)
PCB_W, PCB_H, PCB_T = 180.0, 130.0, 1.6
PCB_X0, PCB_Y0 = 14.0, 70.0         # PCB top-left corner in inner coords (PCB y axis points to -Y)
STANDOFF_H = 8.0
PCB_HOLES = [(4, 4), (176, 68), (4, 126), (176, 126)]
INSERT_D = 4.2                      # M3 heat-set insert hole
M3 = 3.4
# load heatsink (aluminium extrusion) + fan
HS_E = dict(x0=82.0, y0=30.0, w=100.0, d=40.0, h=70.0)
FAN60 = 60.0
# modules
XL4016 = (65.0, 47.0, 25.0)
MP1584 = (22.0, 17.0, 5.0)
BTS7960 = (50.0, 50.0, 43.0)
# thermal unit
T_OUT = (130.0, 130.0)
T_BASE_H = 60.0
HS_T = (100.0, 60.0, 25.0)          # hot-side heatsink (fins down)
TEC = (40.0, 40.0, 3.8)
PLATE = (100.0, 50.0, 6.0)          # aluminium cold plate (flat bar)
PAD = 1.0                           # thermal pad under the cell
POCKET_WALL = 14.0
POCKET_H = 50.0                     # pocket body height above the cold plate top
LID_T = 18.0
CELLS = {'18650': (18.6, 65.2), '21700': (21.4, 70.3)}   # diameter, length
CONTACT_Z = PAD + 11.0              # contact plate centre above the cold plate top


def box(x, y, z, cx=0, cy=0, cz=0):
    """box with its minimum corner at (cx, cy, cz)."""
    return cq.Workplane('XY').box(x, y, z, centered=False).translate((cx, cy, cz))


# ============================================================== electronics box
def ebox_base():
    ox, oy = E_OUT
    b = box(ox, oy, E_H).edges('|Z').fillet(4)
    cav = box(E_IN[0], E_IN[1], E_H, WALL, WALL, FLOOR).edges('|Z').fillet(2)
    b = b.cut(cav)
    def inner(x, y):
        return (WALL + x, WALL + y)
    # PCB standoffs with heat-set insert holes
    for hx, hy in PCB_HOLES:
        x, y = inner(PCB_X0 + hx, PCB_Y0 + (PCB_H - hy))
        s = cq.Workplane('XY').circle(4.0).extrude(STANDOFF_H).translate((x, y, FLOOR))
        b = b.union(s)
        b = b.cut(cq.Workplane('XY').circle(INSERT_D / 2).extrude(STANDOFF_H).translate((x, y, FLOOR + 1)))
    # corner bosses for the lid screws
    for cx, cy in [(8, 8), (ox - 8, 8), (8, oy - 8), (ox - 8, oy - 8)]:
        boss = cq.Workplane('XY').rect(10, 10).extrude(E_H - FLOOR).translate((cx, cy, FLOOR))
        b = b.union(boss)
        b = b.cut(cq.Workplane('XY').circle(INSERT_D / 2).extrude(12).translate((cx, cy, E_H - 12)))
    # front wall: 60 mm fan grille in front of the load heatsink
    fx = WALL + HS_E['x0'] + HS_E['w'] / 2
    fz = FLOOR + 6 + FAN60 / 2
    grille = cq.Workplane('XZ').workplane(offset=0).center(fx, fz)
    for i in range(-2, 3):
        for j in range(-2, 3):
            if i * i + j * j <= 5:
                b = b.cut(cq.Workplane('XZ').center(fx + i * 10, fz + j * 10).rect(7, 7).extrude(-WALL - 1).translate((0, -0.5, 0)))
    for sx in (-25, 25):
        for sz in (-25, 25):
            b = b.cut(cq.Workplane('XZ').center(fx + sx, fz + sz).circle(M3 / 2).extrude(-WALL - 1).translate((0, -0.5, 0)))
    # left wall: two 4 mm binding posts (PSU in) next to J101
    py = WALL + PCB_Y0 + (PCB_H - 14)
    for dy in (-9.5, 9.5):
        b = b.cut(cq.Workplane('YZ').center(py + dy, FLOOR + 40).circle(4.2).extrude(WALL + 1).translate((-0.5, 0, 0)))
    # back wall: USB opening for the Blue Pill (PCB x = 166)
    ux = WALL + PCB_X0 + 166
    usb_z = FLOOR + STANDOFF_H + PCB_T + 11.0
    b = b.cut(box(13, WALL + 2, 9, ux - 6.5, oy - WALL - 1, usb_z - 4.5))
    # right wall: two cable grommets to the thermal unit (cell power + sense, Peltier/fans/NTC)
    for gy in (WALL + 45, WALL + 175):
        b = b.cut(cq.Workplane('YZ').center(gy, FLOOR + 30).circle(8).extrude(WALL + 2).translate((ox - WALL - 1, 0, 0)))
    # exhaust slots on both side walls above the heatsink zone
    for k in range(8):
        y = WALL + HS_E['y0'] - 20 + k * 8
        for x0 in (-0.5, ox - WALL - 0.5):
            b = b.cut(box(WALL + 1, 4, 30, x0, y, E_H - 40))
    # floor locating ribs for the load heatsink
    for x in (HS_E['x0'] - 3, HS_E['x0'] + HS_E['w']):
        b = b.union(box(3, HS_E['d'], 6, WALL + x, WALL + HS_E['y0'], FLOOR))
    # insert holes for the module plate (XL4016 stack) and MP1584
    for (x, y) in [(8, 8), (68, 8), (8, 50), (68, 50)]:
        b = b.union(cq.Workplane('XY').circle(4).extrude(4).translate((WALL + x, WALL + y, FLOOR)))
        b = b.cut(cq.Workplane('XY').circle(INSERT_D / 2).extrude(5).translate((WALL + x, WALL + y, FLOOR + 0.5)))
    # rubber feet recesses
    for cx, cy in [(15, 15), (ox - 15, 15), (15, oy - 15), (ox - 15, oy - 15)]:
        b = b.cut(cq.Workplane('XY').circle(6).extrude(1.0).translate((cx, cy, 0)))
    return b


def ebox_lid():
    ox, oy = E_OUT
    t = 3.0
    lid = box(ox, oy, t).edges('|Z').fillet(4)
    lip = box(E_IN[0] - 1, E_IN[1] - 1, 4, WALL + 0.5, WALL + 0.5, -4).edges('|Z').fillet(2)
    lip = lip.cut(box(E_IN[0] - 5, E_IN[1] - 5, 4, WALL + 2.5, WALL + 2.5, -4))
    lid = lid.union(lip)
    # cut the lip around the corner bosses
    for cx, cy in [(8, 8), (ox - 8, 8), (8, oy - 8), (ox - 8, oy - 8)]:
        lid = lid.cut(box(13, 13, 4, cx - 6.5, cy - 6.5, -4))
        lid = lid.cut(cq.Workplane('XY').circle(M3 / 2).extrude(t).translate((cx, cy, 0)))
        lid = lid.cut(cq.Workplane('XY').circle(3.2).extrude(1.8).translate((cx, cy, t - 1.8)))
    # vents above the load heatsink
    for k in range(9):
        x = WALL + HS_E['x0'] + 6 + k * 10
        lid = lid.cut(box(5, HS_E['d'] - 6, t + 1, x, WALL + HS_E['y0'] + 3, -0.5))
    # label
    lid = lid.cut(cq.Workplane('XY').workplane(offset=t - 0.6).center(ox / 2, oy / 2 + 30)
                  .text('Li-ion Cell Test Bench', 9, 0.6, kind='bold', halign='center', valign='center'))
    return lid


def module_plate():
    """Printed carrier for the XL4016 modules: slotted holes fit any hole pattern,
    four M3 x 30 spacers carry the second module above the first."""
    p = box(75, 57, 3).edges('|Z').fillet(3)
    for (x, y) in [(5, 5), (65, 5), (5, 47), (65, 47)]:
        p = p.cut(cq.Workplane('XY').circle(M3 / 2).extrude(3).translate((x + 0.0, y + 0.0, 0)))
    for y in (12, 45):
        p = p.cut(cq.Workplane('XY').slot2D(50, M3, 0).extrude(3).translate((37.5, y, 0)))
    return p


def heatsink_clamp():
    c = box(16, 40, 30).cut(box(16, 34, 27, 0, 3, 3))
    c = c.union(box(26, 40, 3, -5, 0, 0))
    for y in (8, 32):
        c = c.cut(cq.Workplane('XY').circle(M3 / 2).extrude(3).translate((-1, y, 0)))
    return c


# ============================================================== thermal unit
def t_base():
    ox, oy = T_OUT
    b = box(ox, oy, T_BASE_H).edges('|Z').fillet(4)
    b = b.cut(box(ox - 2 * WALL, oy - 2 * WALL, T_BASE_H, WALL, WALL, FLOOR))
    # heatsink zone: centred in X, at the front in Y
    hx0 = (ox - HS_T[0]) / 2
    hy0 = 12.0
    ledge_z = T_BASE_H - 0.0 - HS_T[2] - TEC[2]   # heatsink top + TECs end at the base top
    # ledges the heatsink rests on (left / right ends)
    for x in (hx0 - 4, hx0 + HS_T[0] - 6):
        b = b.union(box(10, HS_T[1], ledge_z - FLOOR, x, hy0, FLOOR))
    # floor intake grille under the 60 mm fan
    fx, fy = ox / 2, hy0 + HS_T[1] / 2
    for i in range(-2, 3):
        for j in range(-2, 3):
            if i * i + j * j <= 5:
                b = b.cut(box(7, 7, FLOOR + 1, fx + i * 10 - 3.5, fy + j * 10 - 3.5, -0.5))
    for sx in (-25, 25):
        for sy in (-25, 25):
            b = b.cut(cq.Workplane('XY').circle(M3 / 2).extrude(FLOOR + 1).translate((fx + sx, fy + sy, -0.5)))
    # feet so the fan can breathe
    for cx, cy in [(10, 10), (ox - 10, 10), (10, oy - 10), (ox - 10, oy - 10)]:
        b = b.union(cq.Workplane('XY').circle(6).extrude(8).translate((cx, cy, -8)))
    # side exhaust slots at fin height
    for k in range(10):
        x = hx0 + 5 + k * 9.5
        b = b.cut(box(4, WALL + 1, 18, x, -0.5, ledge_z - 2))
    # BTS7960 standoffs behind the heatsink
    for (x, y) in [(40, 78), (80, 78), (40, 118), (80, 118)]:
        b = b.union(cq.Workplane('XY').circle(4).extrude(5).translate((x, y, FLOOR)))
        b = b.cut(cq.Workplane('XY').circle(INSERT_D / 2).extrude(5).translate((x, y, FLOOR + 1)))
    # cable grommet (to the electronics box)
    b = b.cut(cq.Workplane('YZ').center(oy - 30, 30).circle(8).extrude(WALL + 2).translate((-1, 0, 0)))
    # insert holes for the pocket body on the top rim
    for cx, cy in [(8, 8), (ox - 8, 8), (8, oy - 8), (ox - 8, oy - 8)]:
        b = b.union(box(12, 12, T_BASE_H - FLOOR, cx - 6, cy - 6, FLOOR).edges('|Z').fillet(2))
        b = b.cut(cq.Workplane('XY').circle(INSERT_D / 2).extrude(10).translate((cx, cy, T_BASE_H - 10)))
    return b, (hx0, hy0, ledge_z)


def pocket_body(plate_xy):
    """Insulated cell pocket: sits on the base rim, the cold plate is its floor.
    The rear part is a vented cover over the BTS7960 driver."""
    ox, oy = T_OUT
    px0, py0 = plate_xy
    cav_x0, cav_y0 = px0 - 1, py0 - 1
    cav_w, cav_d = PLATE[0] + 2, PLATE[1] + 2
    by0, body_d = 0.0, oy
    h = PLATE[2] + POCKET_H
    b = box(ox, body_d, h, 0, by0, 0).edges('|Z').fillet(4)
    b = b.cut(box(cav_w, cav_d, h, cav_x0, cav_y0, 0))
    # rear chamber over the BTS7960 (open bottom, 3 mm roof with vents)
    rear_y0 = cav_y0 + cav_d + POCKET_WALL
    b = b.cut(box(ox - 2 * WALL, oy - WALL - rear_y0, h - 3, WALL, rear_y0, 0))
    for k in range(9):
        b = b.cut(box(4, oy - WALL - rear_y0 - 10, 4, 20 + k * 10, rear_y0 + 5, h - 3.5))
    # side grooves that guide the two contact blocks (3 x 3 mm, along X)
    gz = PLATE[2] + 2
    for y in (cav_y0 - 3, cav_y0 + cav_d):
        b = b.cut(box(cav_w - 4, 3, 3, cav_x0 + 2, y, gz))
    # thumbscrew through the right end wall (M4 heat-set insert from outside)
    sz = PLATE[2] + CONTACT_Z
    b = b.cut(cq.Workplane('YZ').center(cav_y0 + cav_d / 2, sz).circle(2.9).extrude(ox).translate((cav_x0 + cav_w - 1, 0, 0)))
    # wire channel for the cell power + sense wires and the NTC (left end, down to the base)
    b = b.cut(box(cav_x0 + 1, 12, 8, -0.5, cav_y0 + cav_d / 2 - 6, PLATE[2] + 10))
    # screw holes into the base rim inserts
    for cx, cy in [(8, 8), (ox - 8, 8), (8, oy - 8), (ox - 8, oy - 8)]:
        b = b.cut(cq.Workplane('XY').circle(M3 / 2).extrude(h).translate((cx, cy, 0)))
        b = b.cut(cq.Workplane('XY').circle(3.2).extrude(4).translate((cx, cy, h - 4)))
    # lid insert holes around the pocket opening
    for cx in (cav_x0 - 7, cav_x0 + cav_w + 7):
        for cy in (cav_y0 + 8, cav_y0 + cav_d - 8):
            b = b.cut(cq.Workplane('XY').circle(INSERT_D / 2).extrude(8).translate((cx, cy, h - 8)))
    return b, (by0, body_d, h, cav_x0, cav_y0, cav_w, cav_d)


def pocket_lid(geom):
    by0, body_d, h, cav_x0, cav_y0, cav_w, cav_d = geom
    lx0, ly0 = cav_x0 - 13, cav_y0 - 12
    lw, ld = cav_w + 26, cav_d + 24
    lid = box(lw, ld, LID_T, lx0, ly0, 0).edges('|Z').fillet(4)
    plug = box(cav_w - 1, cav_d - 1, 8, cav_x0 + 0.5, cav_y0 + 0.5, -8)
    lid = lid.union(plug)
    # 30 mm mixing fan recess (blows down into the pocket) + wire hole
    fx, fy = cav_x0 + 22, cav_y0 + cav_d / 2
    lid = lid.cut(box(31, 31, 11, fx - 15.5, fy - 15.5, -8.5))
    lid = lid.cut(cq.Workplane('XY').circle(13).extrude(LID_T).translate((fx, fy, -8)))
    lid = lid.cut(cq.Workplane('XY').circle(2).extrude(LID_T + 8).translate((fx + 18, fy + 12, -8)))
    # NTC (pocket air) port
    lid = lid.cut(cq.Workplane('XY').circle(2.2).extrude(LID_T + 8).translate((cav_x0 + cav_w - 20, fy, -8)))
    for cx in (cav_x0 - 7, cav_x0 + cav_w + 7):
        for cy in (cav_y0 + 8, cav_y0 + cav_d - 8):
            lid = lid.cut(cq.Workplane('XY').circle(M3 / 2).extrude(LID_T).translate((cx, cy, 0)))
    lid = lid.cut(cq.Workplane('XY').workplane(offset=LID_T - 0.6).center(cav_x0 + cav_w / 2 + 15, fy)
                  .text('18650 / 21700', 6, 0.6, kind='bold', halign='center', valign='center'))
    return lid


def contact_block(slider=False):
    """Holds a 22 x 22 x 1.5 mm copper contact plate (power) with a P75 spring
    probe through its centre (Kelvin sense). Rides in the pocket side grooves."""
    w = PLATE[1] + 2 - 0.6                # fits the cavity depth
    blk = box(10, w, 30, 0, 0, 0)
    for y in (-2.7, w):                   # rails into the grooves
        blk = blk.union(box(10, 2.7, 2.6, 0, y, 2.2))
    cz = CONTACT_Z
    # copper plate recess on the cell side (+X face)
    blk = blk.cut(box(1.6, 22.4, 22.4, 10 - 1.6, w / 2 - 11.2, cz - 11.2))
    # power wire hole and sense probe hole
    blk = blk.cut(cq.Workplane('YZ').center(w / 2 + 6, cz - 6).circle(1.6).extrude(12).translate((-1, 0, 0)))
    blk = blk.cut(cq.Workplane('YZ').center(w / 2, cz).circle(0.85).extrude(12).translate((-1, 0, 0)))
    blk = blk.cut(cq.Workplane('YZ').center(w / 2, cz).circle(1.6).extrude(6).translate((-1, 0, 0)))
    if slider:
        # pocket for the M4 thumbscrew tip (pushes the block towards the cell)
        blk = blk.cut(cq.Workplane('YZ').center(w / 2, cz).circle(2.2).extrude(4).translate((-0.1, 0, 0)))
    return blk.translate((0, 0.3, 0))


def saddle(cell):
    """Cradle that centres one cell on the cold plate; the cell rests directly on the
    thermal pad through the open floor."""
    d, _ = CELLS[cell]
    w = PLATE[1] + 2 - 0.6
    s = box(36, w, d * 0.75)
    cyl = cq.Workplane('YZ').center(w / 2, PAD + d / 2).circle(d / 2 + 0.3).extrude(36)
    s = s.cut(cyl)
    s = s.cut(box(36, d * 0.6, PAD + 2, 0, w / 2 - d * 0.3, 0))          # open floor under the cell
    s = s.cut(box(12, w, d, 12, 0, PAD + d * 0.45))                      # finger gap (top only)
    s = s.cut(cq.Workplane('XY').workplane(offset=d * 0.75 - 0.6).center(6, 5)
              .text(cell, 4, 0.6, halign='center', valign='center'))
    return s.translate((0, 0.3, 0))


def cold_plate():
    p = box(*PLATE)
    for x in (3.5, PLATE[0] - 3.5):
        for y in (6, PLATE[1] - 6):
            p = p.cut(cq.Workplane('XY').circle(M3 / 2).extrude(PLATE[2]).translate((x, y, 0)))
    return p


# ============================================================== purchased-part placeholders
def heatsink(w, d, h, fins_axis='Z', n=10):
    base_t = 6
    if fins_axis == 'Z':        # base on top, fins pointing down
        hs = box(w, d, base_t, 0, 0, h - base_t)
        for i in range(n):
            hs = hs.union(box(1.6, d, h - base_t, i * (w - 1.6) / (n - 1), 0, 0))
    else:                       # base at +Y, fins pointing to -Y
        hs = box(w, base_t, h, 0, d - base_t, 0)
        for i in range(n):
            hs = hs.union(box(1.6, d - base_t, h, i * (w - 1.6) / (n - 1), 0, 0))
    return hs


def fan(size, t):
    f = box(size, size, t).cut(cq.Workplane('XY').circle(size / 2 - 2).extrude(t).translate((size / 2, size / 2, 0)))
    f = f.union(cq.Workplane('XY').circle(size / 5).extrude(t).translate((size / 2, size / 2, 0)))
    return f


def cell_model(cell):
    d, l = CELLS[cell]
    return cq.Workplane('YZ').circle(d / 2).extrude(l)


# ============================================================== build
def build(with_pcb=True):
    os.makedirs(OUT_STL, exist_ok=True)
    os.makedirs(OUT_STEP, exist_ok=True)
    parts = {}
    parts['E1_ebox_base'] = ebox_base()
    parts['E2_ebox_lid'] = ebox_lid()
    parts['E3_module_plate'] = module_plate()
    parts['E4_heatsink_clamp'] = heatsink_clamp()
    tb, (hx0, hy0, ledge_z) = t_base()
    parts['T1_thermal_base'] = tb
    plate_xy = (hx0, hy0 + (HS_T[1] - PLATE[1]) / 2)
    pb, geom = pocket_body(plate_xy)
    parts['T2_pocket_body'] = pb
    parts['T3_pocket_lid'] = pocket_lid(geom)
    parts['T4_contact_block_fixed'] = contact_block(False)
    parts['T5_contact_block_slider'] = contact_block(True)
    parts['T6_saddle_18650'] = saddle('18650')
    parts['T7_saddle_21700'] = saddle('21700')
    for name, wp in parts.items():
        cq.exporters.export(wp, os.path.join(OUT_STL, name + '.stl'), tolerance=0.05, angularTolerance=0.2)

    # ---------------- assembly
    asm = cq.Assembly(name='cell_test_bench')
    grey, dark, alu, cu = cq.Color(0.85, 0.85, 0.88), cq.Color(0.25, 0.25, 0.28), cq.Color(0.75, 0.77, 0.8), cq.Color(0.85, 0.5, 0.2)
    green, blue, red = cq.Color(0.1, 0.45, 0.2), cq.Color(0.15, 0.3, 0.7), cq.Color(0.7, 0.1, 0.1)
    L = lambda x, y, z: cq.Location(cq.Vector(x, y, z))
    asm.add(parts['E1_ebox_base'], name='E1_ebox_base', color=grey)
    asm.add(parts['E2_ebox_lid'], name='E2_ebox_lid', color=cq.Color(0.85, 0.85, 0.88, 0.35), loc=L(0, 0, E_H + 40))
    # PCB: KiCad board origin is its top-left corner, Y points to -Y here
    pcb_z = FLOOR + STANDOFF_H
    if with_pcb and os.path.exists(BOARD_STEP):
        # exported with --user-origin 0x0mm: STEP (x, y) = KiCad (x, -y), board bottom at z = 0
        board = cq.importers.importStep(BOARD_STEP)
        asm.add(board, name='PCB', loc=L(WALL + PCB_X0, WALL + PCB_Y0 + PCB_H, pcb_z))
    else:
        asm.add(box(PCB_W, PCB_H, PCB_T), name='PCB', color=green, loc=L(WALL + PCB_X0, WALL + PCB_Y0, pcb_z))
    asm.add(heatsink(HS_E['w'], HS_E['d'], HS_E['h'], 'Y', 14), name='load_heatsink', color=alu,
            loc=L(WALL + HS_E['x0'], WALL + HS_E['y0'], FLOOR))
    asm.add(fan(FAN60, 15).rotate((0, 0, 0), (1, 0, 0), 90), name='load_fan_60mm', color=dark,
            loc=L(WALL + HS_E['x0'] + HS_E['w'] / 2 - FAN60 / 2, WALL + 15, FLOOR + 6))
    # 0.1 R 50 W aluminium resistor bolted to the heatsink face above Q301 (standing, 50 x 28 x 15)
    asm.add(box(50, 15, 28), name='series_R_0R1_50W', color=cq.Color(0.8, 0.7, 0.2),
            loc=L(WALL + HS_E['x0'] + 25, WALL + HS_E['y0'] + HS_E['d'], FLOOR + 38))
    asm.add(parts['E3_module_plate'], name='E3_module_plate', color=grey, loc=L(WALL + 1, WALL + 1, FLOOR + 4))
    asm.add(box(*XL4016), name='XL4016_charger', color=blue, loc=L(WALL + 6, WALL + 6, FLOOR + 12))
    asm.add(box(*XL4016), name='XL4016_12V', color=blue, loc=L(WALL + 6, WALL + 6, FLOOR + 42))
    asm.add(box(*MP1584), name='MP1584_5V', color=blue, loc=L(E_OUT[0] - WALL - 26, WALL + 4, FLOOR))
    # thermal unit to the right of the electronics box
    tx = E_OUT[0] + 15
    asm.add(parts['T1_thermal_base'], name='T1_thermal_base', color=grey, loc=L(tx, 0, 8))
    tz = 8
    asm.add(fan(FAN60, 15), name='hot_side_fan_60mm', color=dark,
            loc=L(tx + T_OUT[0] / 2 - 30, hy0 + HS_T[1] / 2 - 30, tz + FLOOR))
    asm.add(heatsink(*HS_T, 'Z', 12), name='hot_side_heatsink', color=alu, loc=L(tx + hx0, hy0, tz + ledge_z))
    for i in range(2):
        asm.add(box(*TEC), name='TEC1_12706_%d' % (i + 1), color=cq.Color(0.95, 0.95, 0.95),
                loc=L(tx + hx0 + 8 + i * 44, hy0 + (HS_T[1] - TEC[1]) / 2, tz + ledge_z + HS_T[2]))
    plate_z = tz + T_BASE_H
    asm.add(cold_plate(), name='cold_plate_alu', color=alu, loc=L(tx + plate_xy[0], plate_xy[1], plate_z))
    asm.add(box(*BTS7960), name='BTS7960', color=red, loc=L(tx + 35, 73, tz + FLOOR + 5))
    asm.add(parts['T2_pocket_body'], name='T2_pocket_body', color=cq.Color(0.9, 0.9, 0.9, 0.6), loc=L(tx, 0, plate_z))
    by0, body_d, h, cav_x0, cav_y0, cav_w, cav_d = geom
    asm.add(parts['T3_pocket_lid'], name='T3_pocket_lid', color=cq.Color(0.9, 0.9, 0.9, 0.5), loc=L(tx, 0, plate_z + h + 45))
    top = plate_z + PLATE[2]
    asm.add(box(80, 30, PAD), name='thermal_pad', color=cq.Color(0.5, 0.6, 0.9), loc=L(tx + cav_x0 + 11, cav_y0 + cav_d / 2 - 15, top))
    # 21700 shown in place; the 18650 saddle is exported but not placed
    d, l = CELLS['21700']
    x_cell = tx + cav_x0 + 1 + 10 + 1.5
    asm.add(parts['T4_contact_block_fixed'], name='T4_contact_block_fixed', color=dark, loc=L(tx + cav_x0 + 1, cav_y0 + 0.3, top))
    asm.add(parts['T5_contact_block_slider'].rotate((5, 0, 0), (5, 0, 1), 180).translate((0, PLATE[1] + 2 - 0.6 + 0.6, 0)),
            name='T5_contact_block_slider', color=dark, loc=L(x_cell + l + 1.5, cav_y0 - 0.3, top))
    asm.add(parts['T7_saddle_21700'], name='T7_saddle_21700', color=cq.Color(0.95, 0.6, 0.1), loc=L(x_cell + l / 2 - 18, cav_y0 + 0.3, top))
    asm.add(cell_model('21700'), name='cell_21700', color=cq.Color(0.2, 0.5, 0.25),
            loc=L(x_cell, cav_y0 + cav_d / 2, top + PAD + d / 2))
    asm.save(os.path.join(OUT_STEP, 'cell_test_bench_assembly.step'))
    return parts, asm


if __name__ == '__main__':
    build(with_pcb='--no-pcb' not in sys.argv)
    print('done')
