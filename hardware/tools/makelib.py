"""Build the project-local footprint library (lib/cell_bench.pretty) and 3D models
(lib/cell_bench.3dshapes) from the KiCad standard libraries.
Usage: python3 makelib.py <kicad project dir>"""
import os, re, sys, subprocess
import design

SYS_FP = '/usr/share/kicad/footprints'
RAW3D = 'https://raw.githubusercontent.com/KiCad/kicad-packages3D/master'
LIB = 'cell_bench'

def _fp(name, descr, attr, body):
    return ('(footprint "%s" (version 20221018) (generator pcbnew)\n  (layer "F.Cu")\n  (descr "%s")\n  (attr %s)\n'
            '  (fp_text reference "REF**" (at 0 -3.2) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
            '  (fp_text value "%s" (at 0 3.2) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))\n'
            '%s)\n' % (name, descr, attr, name, body))

def _rect(layer, x0, y0, x1, y1, w=0.12):
    return '  (fp_rect (start %g %g) (end %g %g) (stroke (width %g) (type solid)) (fill none) (layer "%s"))\n' % (x0, y0, x1, y1, w, layer)

CUSTOM = {
    # 2-terminal 2512 metal-strip shunt (Isabellenhuette CMS: 6.35 x 3.05 mm) with Kelvin taps.
    # Pads 1/4 carry the current. Pads 2/3 are small taps at the inner corner of each pad, both on
    # the same side, so the sense pair leaves together and does not run under the resistor body.
    'R_Shunt_2512_Kelvin': _fp('R_Shunt_2512_Kelvin',
        '10 mOhm 2512 current shunt, 2 terminals, Kelvin taps (pads 2, 3) leave the inner pad corners as two short stubs', 'smd',
        '  (pad "1" smd rect (at -3.0 0) (size 1.7 3.6) (layers "F.Cu" "F.Paste" "F.Mask"))\n'
        '  (pad "4" smd rect (at 3.0 0) (size 1.7 3.6) (layers "F.Cu" "F.Paste" "F.Mask"))\n'
        '  (pad "2" smd rect (at -2.2 2.7) (size 0.9 2.0) (layers "F.Cu"))\n'
        '  (pad "3" smd rect (at 2.2 2.7) (size 0.9 2.0) (layers "F.Cu"))\n'
        '  (net_tie_pad_groups "1, 2" "3, 4")\n'
        + _rect('F.Fab', -3.175, -1.525, 3.175, 1.525, 0.1) + _rect('F.CrtYd', -4.1, -2.05, 4.1, 3.95, 0.05)
        + _rect('F.SilkS', -1.9, -1.6, 1.9, 1.6)),
    # wire link: bare or insulated wire on the component side
    'WireLink_P10.16mm': _fp('WireLink_P10.16mm', 'Wire link, 10.16 mm', 'through_hole',
        '  (pad "1" thru_hole circle (at 0 0) (size 2.2 2.2) (drill 1.0) (layers "*.Cu" "*.Mask"))\n'
        '  (pad "2" thru_hole circle (at 10.16 0) (size 2.2 2.2) (drill 1.0) (layers "*.Cu" "*.Mask"))\n'
        '  (fp_line (start 1.1 0) (end 9.06 0) (stroke (width 0.15) (type solid)) (layer "F.SilkS"))\n'
        + _rect('F.CrtYd', -1.3, -1.3, 11.46, 1.3, 0.05)),
}

def main(proj):
    pretty = os.path.join(proj, 'lib', LIB + '.pretty')
    shapes = os.path.join(proj, 'lib', LIB + '.3dshapes')
    os.makedirs(pretty, exist_ok=True)
    os.makedirs(shapes, exist_ok=True)
    fps = sorted({pt['fp'] for _, _, pt in design.all_parts() if pt['fp']})
    missing3d = []
    for f in fps:
        lib, name = f.split(':')
        if lib == 'Custom':
            open(os.path.join(pretty, name + '.kicad_mod'), 'w').write(CUSTOM[name])
            continue
        src = open(os.path.join(SYS_FP, lib + '.pretty', name + '.kicad_mod')).read()
        m = re.search(r'\(model "?\$\{KICAD\d_3DMODEL_DIR\}/([^" )]+)\.wrl"?', src)
        step_name = None
        if m:
            rel = m.group(1)
            step_name = os.path.basename(rel) + '.step'
            dst = os.path.join(shapes, step_name)
            if not os.path.exists(dst):
                r = subprocess.run(['curl', '-sS', '-m', '120', '-f', '-o', dst, RAW3D + '/' + rel + '.step'])
                if r.returncode != 0:
                    missing3d.append(step_name)
                    if os.path.exists(dst):
                        os.remove(dst)
            src = re.sub(r'\(model "?\$\{KICAD\d_3DMODEL_DIR\}/[^" )]+\.wrl"?',
                         '(model "${KIPRJMOD}/lib/%s.3dshapes/%s"' % (LIB, step_name), src)
        src = re.sub(r'^\(footprint "[^"]*"', '(footprint "%s"' % name, src)
        open(os.path.join(pretty, name + '.kicad_mod'), 'w').write(src)
    open(os.path.join(proj, 'fp-lib-table'), 'w').write(
        '(fp_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/lib/%s.pretty")'
        '(options "")(descr "Project footprints for the cell test bench"))\n)\n' % (LIB, LIB))
    # drop footprints and models that the design no longer uses
    keep_fp = {f.split(':')[1] + '.kicad_mod' for f in fps}
    used3d = set()
    for f in os.listdir(pretty):
        if f not in keep_fp:
            os.remove(os.path.join(pretty, f)); continue
        used3d |= set(re.findall(r'3dshapes/([^" )]+\.step)', open(os.path.join(pretty, f)).read()))
    for f in os.listdir(shapes):
        if f not in used3d:
            os.remove(os.path.join(shapes, f))
    print('footprints:', len(fps), 'missing 3D:', missing3d)
    return missing3d

if __name__ == '__main__':
    main(sys.argv[1])
