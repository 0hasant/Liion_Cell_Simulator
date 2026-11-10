"""Manufacturing outputs for in-house CNC milling of the single-sided board.

Writes to <outdir>:
  gerber/   B_Cu, Edge_Cuts, F_Silkscreen (component-side marks) + one Excellon drill file
            -> for FlatCAM / pcb2gcode / Snapmaker Luban
  svg/      B_Cu mirrored (as seen when the copper side faces up on the CNC bed),
            Edge_Cuts mirrored, F_Silkscreen (laser-mark the component side), all 1:1 in mm
  print/    1:1 PDFs: copper seen from the component side (lay parts on it to check pin pitch)
  jumpers.csv  wire jumpers W1..Wn: net, both ends (mm), length
  drill_summary.csv  hole sizes and counts (which drill bits you need)
  drc.rpt   KiCad DRC report with the CNC rules

Usage: python3 fab.py <board.kicad_pcb> <outdir>"""
import sys, os, json, csv, subprocess, collections, re
import pcbnew

def run(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr)
        raise SystemExit('failed: ' + ' '.join(args))
    return r.stdout

def main(board, out):
    for d in ('gerber', 'svg', 'print'):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    b = pcbnew.LoadBoard(board)
    # ---- drill summary
    holes = collections.Counter()
    for fp in b.GetFootprints():
        for p in fp.Pads():
            d = p.GetDrillSize().x
            if d > 0:
                holes[round(pcbnew.ToMM(d), 2)] += 1
    with open(os.path.join(out, 'drill_summary.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Hole mm', 'Count', 'Use'])
        use = {0.8: 'IC, header, small diode, transistor', 1.0: 'resistors, caps, wire jumpers', 1.3: 'terminals, TO-220/247, relays',
               1.5: 'relay power pins, TO-247', 1.8: 'terminal blocks', 2.0: 'large pins', 3.2: 'M3 mounting holes'}
        for d in sorted(holes):
            w.writerow([d, holes[d], use.get(d, '')])
    # ---- jumpers (wire list written by cleanup.py)
    wj = board.replace('.kicad_pcb', '_jumpers.json')
    wires = json.load(open(wj)) if os.path.exists(wj) else []
    power = {'PGND', 'VIN', '+12V', '+12V_SW', 'TEC_A', 'TEC_B', 'TEC_SW', 'CHG_OUT'}
    with open(os.path.join(out, 'jumpers.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Wire', 'Footprint', 'Net', 'From pad', 'x1 mm', 'y1 mm', 'To pad', 'x2 mm', 'y2 mm', 'Length mm', 'Wire type'])
        for r in wires:
            w.writerow([r['wire'], r['ref'], r['net'], r['pads'][0], round(r['a'][0], 2), round(r['a'][1], 2), r['pads'][1],
                        round(r['b'][0], 2), round(r['b'][1], 2), r['length'],
                        '0.75 mm2 stranded (power)' if r['net'] in power else '0.6 mm solid, insulated'])
    rows = wires
    # ---- gerbers + drill
    g = os.path.join(out, 'gerber') + '/'
    run('kicad-cli', 'pcb', 'export', 'gerbers', '--layers', 'B.Cu,Edge.Cuts,F.Silkscreen,B.Mask',
        '--no-protel-ext', '--subtract-soldermask', '-o', g, board)
    run('kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th', '--excellon-units', 'mm',
        '--generate-map', '--map-format', 'pdf', '-o', g, board)
    # ---- SVG for Luban (mirrored copper and outline: copper side up on the bed)
    s = os.path.join(out, 'svg')
    for layer, mir, name in (('B.Cu', True, 'B_Cu_mirrored'), ('Edge.Cuts', True, 'Edge_Cuts_mirrored'),
                             ('F.Silkscreen,Edge.Cuts', False, 'F_Silkscreen')):
        run('kicad-cli', 'pcb', 'export', 'svg', '--layers', layer, '--black-and-white', '--page-size-mode', '2',
            '--exclude-drawing-sheet', *(['--mirror'] if mir else []), '-o', os.path.join(s, name + '.svg'), board)
    # ---- 1:1 print, copper seen from the component side, with outline and part outlines
    p = os.path.join(out, 'print')
    run('kicad-cli', 'pcb', 'export', 'pdf', '--layers', 'B.Cu,Edge.Cuts,F.Fab', '--black-and-white',
        '--include-border-title', '-o', os.path.join(p, 'copper_from_component_side_1to1.pdf'), board)
    run('kicad-cli', 'pcb', 'export', 'pdf', '--layers', 'F.Silkscreen,Edge.Cuts', '--black-and-white',
        '--include-border-title', '-o', os.path.join(p, 'assembly_component_side_1to1.pdf'), board)
    # ---- DRC
    rpt = os.path.join(out, 'drc.rpt')
    b2 = pcbnew.LoadBoard(board)          # rules come from the .kicad_pro next to the board
    pcbnew.ZONE_FILLER(b2).Fill(b2.Zones())
    pcbnew.WriteDRCReport(b2, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = open(rpt).read()
    kinds = collections.Counter(re.findall(r'^\[([a-z_]+)\]', txt, re.M))
    # KiCad cannot see the wire jumpers, so it lists one "unconnected" pair per wire.
    # Connectivity is checked independently by conncheck.py (copper islands + jumpers).
    import conncheck
    bad, shorts = conncheck.check(board, verbose=False)
    errors = {k: v for k, v in kinds.items() if k != 'unconnected_items'}
    unc = kinds.get('unconnected_items', 0)
    open(os.path.join(out, 'drc_summary.txt'), 'w').write(
        'DRC with CNC rules (%s)\n' % os.path.basename(board) +
        'DRC errors (excluding unconnected items): %s\n' % (errors or 'none') +
        'KiCad unconnected items: %d (one per wire jumper: %d wires)\n' % (unc, len(rows)) +
        'conncheck.py, nets incomplete after counting the wire jumpers: %s\n' % (bad or 'none') +
        'conncheck.py, copper shorts between nets: %s\n' % (shorts or 'none'))
    if bad or shorts:
        errors['connectivity'] = {'incomplete': bad, 'shorts': shorts}
    print('holes:', dict(sorted(holes.items())), 'wires:', len(rows))
    print('DRC errors:', errors or 'none', '| KiCad unconnected (jumper wires):', unc)
    return errors, rows

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
