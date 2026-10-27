"""Build the project-local footprint library (lib/cell_bench.pretty) and 3D models
(lib/cell_bench.3dshapes) from the KiCad standard libraries.
Usage: python3 makelib.py <kicad project dir>"""
import os, re, sys, subprocess
import design

SYS_FP = '/usr/share/kicad/footprints'
RAW3D = 'https://raw.githubusercontent.com/KiCad/kicad-packages3D/master'
LIB = 'cell_bench'

def main(proj):
    pretty = os.path.join(proj, 'lib', LIB + '.pretty')
    shapes = os.path.join(proj, 'lib', LIB + '.3dshapes')
    os.makedirs(pretty, exist_ok=True)
    os.makedirs(shapes, exist_ok=True)
    fps = sorted({pt['fp'] for _, _, pt in design.all_parts() if pt['fp']})
    missing3d = []
    for f in fps:
        lib, name = f.split(':')
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
    print('footprints:', len(fps), 'missing 3D:', missing3d)
    return missing3d

if __name__ == '__main__':
    main(sys.argv[1])
