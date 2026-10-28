"""Create the PCB (KiCad 7 format) from the exported netlist: board outline, footprints,
nets, initial placement, net classes, GND pours and module keep-outs.
Usage: python3 pcbgen.py <netlist> <project dir>"""
import sys, os, json, re
import pcbnew
from sexp import parse, find

W, H = 180.0, 130.0
MM = pcbnew.FromMM

def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))

# ---------------------------------------------------------------- fixed placements: ref -> (x, y, rot)
FIXED = {
    'H101': (4, 4, 0), 'H102': (176, 68, 0), 'H103': (4, 126, 0), 'H104': (176, 126, 0),
    # left edge: terminal blocks rotated 270 so the wire entry faces the left edge
    'J101': (6.5, 14, 270), 'J102': (6, 30, 270), 'J103': (6, 54, 270), 'J401': (6, 78, 270),
    'J104': (6, 102, 270), 'J402': (19, 90, 90),
    'F101': (18, 9, 0),
    # bottom edge: high-current path, wire entry down (rot 0)
    'J205': (46, 123.5, 0), 'J206': (58, 126, 0), 'J301': (92, 123.5, 0),
    'Q301': (118, 127, 180),          # TO-247 back faces the board edge: heatsink outside the board
    'K1': (24, 100, 0), 'K2': (66, 100, 0),
    'F202': (28, 118, 0),
    'R201': (57, 113, 0),
    # top edge: thermal connectors, wire entry up (rot 180)
    'J702': (55, 6, 180), 'J703': (68, 6, 180), 'J701': (74, 4, 90),
    'J704': (99, 4, 0), 'J706': (108, 4, 0), 'J705': (117, 4, 0),
    # NTC connectors on the bottom-right edge
    'J501': (137, 126, 0), 'J502': (146, 126, 0), 'J503': (155, 126, 0), 'J504': (164, 126, 0),
    # Blue Pill, USB end at the top edge (J801 = B12 row, pin 1 at the USB end)
    'J801': (158, 12, 0), 'J802': (173.24, 60.26, 180), 'J803': (162, 66, 270),
    # plug-in modules (module bodies overhang to the right of each socket)
    'U302': (98, 70, 0), 'U401': (44, 70, 0), 'U501': (128, 72, 0), 'U502': (128, 100, 0),
}
# keep-out rectangles where plug-in modules overhang the board (no footprints)
KEEPOUT = {
    'Blue Pill': (160.2, 9.0, 171.2, 62.0),
    'ADS1115 #1': (129.8, 69.0, 148.0, 97.0),
    'ADS1115 #2': (129.8, 97.5, 148.0, 122.0),
    'MCP4725 load': (99.8, 67.0, 114.0, 86.0),
    'MCP4725 chg': (45.8, 67.0, 60.0, 86.0),
}
# packing regions for everything else: sheet -> list of rectangles
REGIONS = {
    'Power': [(17, 17, 52, 64)],
    'Charger': [(17, 66, 43, 92)],
    'Cell_Relays': [(55, 62, 98, 96), (55, 42, 98, 60)],
    'Electronic_Load': [(95, 86, 127, 122), (75, 114, 95, 122)],
    'Measurement': [(149, 71, 175, 121)],
    'Protection': [(118, 12, 153, 66)],
    'Thermal': [(36, 14, 116, 40)],
    'MCU': [(100, 44, 117, 66), (55, 42, 98, 60)],
}
POWER_NETS = ['GND', 'VIN', '/Power/VIN_RAW', '/Cell_Relays/CELL_P', '/Cell_Relays/CELL_P_RAW',
              '/Cell_Relays/CELL_N', 'LOAD_P', '/Electronic_Load/LOAD_D', 'CHG_OUT',
              '/Thermal/TEC_A', '/Thermal/TEC_B', '+12V', '+12V_SW']

def courtyard(fp):
    """courtyard bbox in mm relative to the footprint position (current orientation)."""
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            b = g.GetBoundingBox()
            xs += [b.GetLeft(), b.GetRight()]
            ys += [b.GetTop(), b.GetBottom()]
    p = fp.GetPosition()
    if not xs:
        b = fp.GetBoundingBox(False, False)
        xs, ys = [b.GetLeft(), b.GetRight()], [b.GetTop(), b.GetBottom()]
    return [pcbnew.ToMM(v) for v in (min(xs) - p.x, min(ys) - p.y, max(xs) - p.x, max(ys) - p.y)]

def add_rect(board, layer, x0, y0, x1, y1, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(V(x0, y0)); s.SetEnd(V(x1, y1))
    s.SetLayer(layer); s.SetWidth(MM(width))
    board.Add(s)

def add_text(board, txt, x, y, size=1.2, layer=pcbnew.F_SilkS):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt); t.SetPosition(V(x, y)); t.SetLayer(layer)
    t.SetTextSize(V(size, size)); t.SetTextThickness(MM(size * 0.15))
    board.Add(t)

def build(netfile, proj):
    net = parse(open(netfile).read())[0]
    lib = os.path.join(proj, 'lib', 'cell_bench.pretty')
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    # nets
    netmap = {}
    padnet = {}
    for n in find(find(net, 'nets')[0], 'net'):
        name = str(find(n, 'name')[0][1])
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni
        for nd in find(n, 'node'):
            padnet[(str(find(nd, 'ref')[0][1]), str(find(nd, 'pin')[0][1]))] = ni
    # footprints
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
        sheet = str(find(find(c, 'sheetpath')[0], 'names')[0][1]).strip('/')
        for pad in fp.Pads():
            ni = padnet.get((ref, pad.GetNumber()))
            if ni is not None:
                pad.SetNet(ni)
                if ni.GetNetname() == 'GND' and pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                    pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        board.Add(fp)
        fps[ref] = (fp, sheet)
    # fixed placement
    occupied = []
    for ref, (x, y, rot) in FIXED.items():
        fp = fps[ref][0]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(V(x, y))
        cx0, cy0, cx1, cy1 = courtyard(fp)
        occupied.append((x + cx0, y + cy0, x + cx1, y + cy1, ref))
        if ref.startswith(('J', 'K', 'Q3', 'H', 'U', 'F')):
            fp.SetLocked(True)
    for name, r in KEEPOUT.items():
        occupied.append(r + (name,))
    # shelf packing of the rest, per sheet region
    def free(r):
        return all(r[2] <= o[0] or r[0] >= o[2] or r[3] <= o[1] or r[1] >= o[3] for o in occupied)
    gap = 2.6
    unplaced = []
    by_sheet = {}
    for ref, (fp, sheet) in fps.items():
        if ref in FIXED:
            continue
        by_sheet.setdefault(sheet, []).append(ref)
    order = lambda r: (r[0] != 'U', r[0] != 'Q', r[0] != 'D', int(re.sub(r'\D', '', r) or 0))
    for sheet, refs in by_sheet.items():
        refs.sort(key=order)
        for ref in refs:
            fp = fps[ref][0]
            # resistors/caps vertical saves width in rows
            cx0, cy0, cx1, cy1 = courtyard(fp)
            w, h = cx1 - cx0, cy1 - cy0
            gap = 3.4 if sheet == 'Electronic_Load' else 2.6
            placed = False
            for (rx0, ry0, rx1, ry1) in REGIONS[sheet]:
                y = ry0
                while y + h <= ry1 and not placed:
                    x = rx0
                    while x + w <= rx1:
                        cand = (x, y, x + w, y + h)
                        if free((cand[0] - gap / 2, cand[1] - gap / 2, cand[2] + gap / 2, cand[3] + gap / 2)):
                            fp.SetPosition(V(x - cx0, y - cy0))
                            occupied.append(cand + (ref,))
                            placed = True
                            break
                        x += 0.5
                    y += 0.5
                if placed:
                    break
            if not placed:
                unplaced.append((ref, sheet, round(w, 1), round(h, 1)))
    # outline
    add_rect(board, pcbnew.Edge_Cuts, 0, 0, W, H, 0.1)
    # keep-out rule areas (no footprints) for module overhangs
    for name, (x0, y0, x1, y1) in KEEPOUT.items():
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowFootprints(True)
        z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowCopperPour(False)
        ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu)
        z.SetLayerSet(ls)
        z.SetZoneName('Module overhang: ' + name)
        ol = z.Outline(); ol.NewOutline()
        for (px, py) in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            ol.Append(MM(px), MM(py))
        board.Add(z)
        add_text(board, name, (x0 + x1) / 2, (y0 + y1) / 2, 1.0, pcbnew.F_Fab)
    # GND pours on both layers
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer); z.SetNet(netmap['GND'])
        z.SetMinThickness(MM(0.25)); z.SetLocalClearance(MM(0.4))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.5)); z.SetThermalReliefSpokeWidth(MM(0.8))
        z.SetAssignedPriority(0)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline(); ol.NewOutline()
        for (px, py) in [(0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)]:
            ol.Append(MM(px), MM(py))
        board.Add(z)
    # silkscreen notes
    add_text(board, 'Cell test bench v0.2  2026-10', 30, 128.2, 1.2, pcbnew.B_SilkS)
    add_text(board, 'USB', 166, 2.5, 1.5)
    add_text(board, 'B12', 154.5, 12, 1.0)
    add_text(board, 'VB', 177.5, 60, 1.0)
    path = os.path.join(proj, 'cell_test_bench.kicad_pcb')
    board.Save(path)
    return unplaced

def netclasses(proj):
    """Write net classes into the project file (KiCad 7 format)."""
    pro_path = os.path.join(proj, 'cell_test_bench.kicad_pro')
    pro = json.load(open(pro_path))
    base = {"bus_width": 12, "clearance": 0.25, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
            "track_width": 0.4, "via_diameter": 0.9, "via_drill": 0.5, "wire_width": 6}
    classes = [dict(base, name="Default", clearance=0.2, track_width=0.3)]
    classes.append(dict(base, name='HighCurrent', clearance=0.5, track_width=3.0, via_diameter=1.6, via_drill=1.0))
    classes.append(dict(base, name='Supply', clearance=0.3, track_width=1.0, via_diameter=1.2, via_drill=0.7))
    classes.append(dict(base, name='Sense', clearance=0.3, track_width=0.3))
    pats = [{"netclass": "HighCurrent", "pattern": p} for p in
            ['/Power/VIN_RAW', 'VIN', '/Cell_Relays/CELL_P', '/Cell_Relays/CELL_P_RAW', '/Cell_Relays/CELL_N',
             'LOAD_P', '/Electronic_Load/LOAD_D', 'CHG_OUT', '/Thermal/TEC_A', '/Thermal/TEC_B']]
    pats += [{"netclass": "Supply", "pattern": p} for p in ['+12V', '+12V_SW', '+5V', '+3V3', '/MCU/BP_5V', '/Thermal/FAN_N']]
    pats += [{"netclass": "Sense", "pattern": p} for p in ['ISNS_N', 'ISNS_G', 'SENSE_P', 'SENSE_N',
                                                          '/Measurement/ADC_*']]
    pro['net_settings'] = {"classes": classes, "meta": {"version": 3}, "net_colors": None,
                           "netclass_assignments": None, "netclass_patterns": pats}
    pro.setdefault('board', {})
    pro['board']['design_settings'] = {
        "rules": {"min_clearance": 0.2, "min_track_width": 0.25, "min_via_diameter": 0.6,
                  "min_through_hole_diameter": 0.3, "min_copper_edge_clearance": 0.5,
                  "min_hole_clearance": 0.25, "min_hole_to_hole": 0.25, "min_silk_clearance": 0.0,
                  "min_resolved_spokes": 1},
        "track_widths": [0.0, 0.3, 0.4, 0.6, 1.0, 1.5, 2.0, 3.0, 4.0],
        "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.9, "drill": 0.5},
                           {"diameter": 1.2, "drill": 0.7}, {"diameter": 1.6, "drill": 1.0}],
        "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                     "copper_text_size_v": 1.5, "copper_text_thickness": 0.3, "silk_line_width": 0.15,
                     "silk_text_size_h": 1.0, "silk_text_size_v": 1.0, "silk_text_thickness": 0.15},
    }
    pro['boards'] = []
    json.dump(pro, open(pro_path, 'w'), indent=2)

if __name__ == '__main__':
    un = build(sys.argv[1], sys.argv[2])
    netclasses(sys.argv[2])
    print('unplaced:', un)
