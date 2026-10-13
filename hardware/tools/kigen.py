"""Tiny KiCad 7-format schematic generator: places symbols, connects every pin
with a short wire stub ending in a net label / power symbol / no-connect flag."""
import uuid, math, json, os
from sexp import Q, dump
import libs

PROJECT = 'cell_test_bench'
POWER_NETS = {'GND': 'power:GND', '+12V': 'power:+12V', '+5V': 'power:+5V', '+3V3': 'power:+3V3'}
STUB = 2.54
U = lambda: str(uuid.uuid4())

def font(sz=1.27):
    return ['effects', ['font', ['size', sz, sz]]]

def snap(v):
    return round(v / 1.27) * 1.27

def xf(px, py, rot, x, y):
    """lib (x, y-up) -> sheet coords for a symbol at (px,py) rotated rot deg (CCW on screen)."""
    t = math.radians(rot)
    sx, sy = x, -y
    rx = sx * math.cos(t) + sy * math.sin(t)
    ry = -sx * math.sin(t) + sy * math.cos(t)
    return round(px + rx, 4), round(py + ry, 4)

def outward(angle, rot):
    # pin angle points from tip toward body (lib coords); outward is opposite
    a = math.radians(angle + 180)
    dx, dy = math.cos(a), math.sin(a)
    return xf(0, 0, rot, dx, dy)

class Sheet:
    def __init__(self, name, file, title):
        self.name, self.file, self.title = name, file, title
        self.uuid = U()
        self.items = []      # sexpr items
        self.used_libs = {}
        self.comps = []
        self.texts = []
        self.nets_here = set()

class Design:
    def __init__(self):
        self.root = Sheet('Root', PROJECT + '.kicad_sch', 'Cell test bench')
        self.sheets = []
        self.pwr_n = 0
        self.globals = set()

    def sheet(self, name, file, title):
        s = Sheet(name, file, title)
        s.sheet_sym_uuid = U()
        self.sheets.append(s)
        return s

    def path(self, s):
        if s is self.root:
            return '/' + self.root.uuid
        return '/' + self.root.uuid + '/' + s.sheet_sym_uuid

# ---------------------------------------------------------------- placement
def place_symbol(D, s, libid, ref, value, unit, x, y, rot=0, inbom=True, fields=None, vpos=None):
    sym = libs.get(libid)
    s.used_libs[libid] = sym
    props = []
    pdefs = {p[1]: p for p in sym if isinstance(p, list) and p[0] == 'property'}
    vals = {'Reference': ref, 'Value': value, 'Footprint': '', 'Datasheet': '~'}
    if fields:
        vals.update(fields)
    off = {'Reference': (2.0, -3.0), 'Value': (2.0, 3.5)}
    for k, v in vals.items():
        dx, dy = off.get(k, (0, 0))
        e = font()
        if k not in ('Reference', 'Value') or (not inbom and k == 'Reference'):
            e.append('hide')
        e2 = e + [['justify', 'left']] if k in ('Reference', 'Value') and inbom else e
        at = [round(x + 6 + dx, 2), round(y + dy - 2, 2)]
        if not inbom:
            at = list(vpos) if (vpos and k == 'Value') else [x, y]
        props.append(['property', Q(k), Q(v), ['at', at[0], at[1], 0], e2])
    pins = [p for p in libs.pins(sym) if p['unit'] in (0, unit)]
    item = ['symbol', ['lib_id', Q(libid)], ['at', x, y, rot], ['unit', unit],
            ['in_bom', 'yes' if inbom else 'no'], ['on_board', 'yes' if inbom else 'no'], ['dnp', 'no'],
            ['uuid', U()]] + props + \
           [['pin', Q(p['number']), ['uuid', U()]] for p in pins] + \
           [['instances', ['project', Q(PROJECT), ['path', Q(D.path(s)), ['reference', Q(ref)], ['unit', unit]]]]]
    s.items.append(item)
    return pins

def wire(s, a, b):
    s.items.append(['wire', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]],
                    ['stroke', ['width', 0], ['type', 'default']], ['uuid', U()]])

def label(D, s, net, pt, d):
    ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
    just = 'left' if ang in (0, 90) else 'right'
    if net in D.globals:
        s.items.append(['global_label', Q(net), ['shape', 'passive'], ['at', pt[0], pt[1], ang],
                        ['fields_autoplaced'], ['effects', ['font', ['size', 1.27, 1.27]], ['justify', just]],
                        ['uuid', U()],
                        ['property', Q('Intersheetrefs'), Q('${INTERSHEET_REFS}'), ['at', pt[0], pt[1], 0],
                         ['effects', ['font', ['size', 1.27, 1.27]], 'hide']]])
    else:
        s.items.append(['label', Q(net), ['at', pt[0], pt[1], ang],
                        ['fields_autoplaced'], ['effects', ['font', ['size', 1.27, 1.27]], ['justify', just, 'bottom']],
                        ['uuid', U()]])

def power(D, s, net, pt, d):
    libid = POWER_NETS[net]
    D.pwr_n += 1
    # choose rotation so the symbol body points along d (GND body points down by default, others up)
    default = (0, 1) if net == 'GND' else (0, -1)
    rots = {0: default}
    for r in (0, 90, 180, 270):
        v = xf(0, 0, r, default[0], -default[1])
        rots[r] = (round(v[0]), round(v[1]))
    rot = next(r for r in (0, 90, 180, 270) if rots[r] == d)
    vp = (round(pt[0] + d[0] * 4.5, 2), round(pt[1] + d[1] * 4.5, 2))
    place_symbol(D, s, libid, '#PWR%03d' % D.pwr_n, net, 1, pt[0], pt[1], rot, inbom=False, vpos=vp)

def comp(D, s, libid, ref, value, x, y, nets, unit=1, rot=0, fields=None):
    """nets: {pin_number: netname | 'NC'}"""
    x, y = snap(x), snap(y)
    pins = place_symbol(D, s, libid, ref, value, unit, x, y, rot, inbom=not ref.startswith('#'), fields=fields)
    s.comps.append((ref, unit, libid))
    for p in pins:
        net = nets.get(p['number'])
        if net is None:
            raise ValueError('%s pin %s (%s) unassigned' % (ref, p['number'], p['name']))
        tip = xf(x, y, rot, p['x'], p['y'])
        if net == 'NC':
            s.items.append(['no_connect', ['at', tip[0], tip[1]], ['uuid', U()]])
            continue
        d = outward(p['angle'], rot)
        d = (round(d[0]), round(d[1]))
        end = (round(tip[0] + d[0] * STUB, 4), round(tip[1] + d[1] * STUB, 4))
        wire(s, tip, end)
        s.nets_here.add(net)
        if net in POWER_NETS:
            power(D, s, net, end, d)
        else:
            label(D, s, net, end, d)
    extra = set(nets) - {p['number'] for p in pins}
    if extra:
        raise ValueError('%s: unknown pins %s' % (ref, extra))

def text(s, txt, x, y, size=1.5):
    s.items.append(['text', Q(txt), ['at', x, y, 0],
                    ['effects', ['font', ['size', size, size]], ['justify', 'left', 'top']], ['uuid', U()]])

# ---------------------------------------------------------------- output
def sheet_file(D, s, paper='A3'):
    out = ['kicad_sch', ['version', 20230121], ['generator', 'eeschema'], ['uuid', s.uuid], ['paper', Q(paper)],
           ['title_block', ['title', Q(s.title)], ['date', Q('2026-10-13')], ['rev', Q('0.1 draft')],
            ['company', Q('Solaris - cell test bench')]],
           ['lib_symbols'] + list(s.used_libs.values())]
    out += s.items
    if s is D.root:
        out.append(['sheet_instances', ['path', Q('/'), ['page', Q('1')]]])
    return dump(out) + '\n'

def add_sheet_symbols(D):
    x0, y0, w, h = 40, 60, 60, 25
    for i, s in enumerate(D.sheets):
        col, row = i % 4, i // 4
        x, y = x0 + col * 90, y0 + row * 50
        D.root.items.append(
            ['sheet', ['at', x, y], ['size', w, h], ['fields_autoplaced'],
             ['stroke', ['width', 0.1524], ['type', 'solid']], ['fill', ['color', 0, 0, 0, 0.0]],
             ['uuid', s.sheet_sym_uuid],
             ['property', Q('Sheetname'), Q(s.name), ['at', x, y - 0.7, 0],
              ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'bottom']]],
             ['property', Q('Sheetfile'), Q(s.file), ['at', x, y + h + 0.6, 0],
              ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'top']]],
             ['instances', ['project', Q(PROJECT), ['path', Q('/' + D.root.uuid), ['page', Q(str(i + 2))]]]]])
        text(D.root, s.title, x + 2, y + 4, 1.27)

def write_all(D, outdir):
    os.makedirs(outdir, exist_ok=True)
    add_sheet_symbols(D)
    for s in [D.root] + D.sheets:
        open(os.path.join(outdir, s.file), 'w').write(sheet_file(D, s))
    pro = {
        "meta": {"filename": PROJECT + ".kicad_pro", "version": 1},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[D.root.uuid, "Root"]] + [[s.sheet_sym_uuid, s.name] for s in D.sheets],
        "boards": [], "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "text_variables": {}
    }
    open(os.path.join(outdir, PROJECT + '.kicad_pro'), 'w').write(json.dumps(pro, indent=2) + '\n')
