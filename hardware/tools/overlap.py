import sys, pcbnew
from pcbgen import courtyard, KEEPOUT, W, H
b = pcbnew.LoadBoard(sys.argv[1])
boxes = []
for fp in b.GetFootprints():
    p = fp.GetPosition(); x, y = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
    c = courtyard(fp)
    boxes.append((x + c[0], y + c[1], x + c[2], y + c[3], fp.GetReference()))
bad = 0
for i in range(len(boxes)):
    a = boxes[i]
    if a[0] < -0.5 or a[1] < -0.5 or a[2] > W + 0.5 or a[3] > H + 0.5:
        print('OUTSIDE', a[4], [round(v, 1) for v in a[:4]]); bad += 1
    for j in range(i + 1, len(boxes)):
        c = boxes[j]
        if a[2] > c[0] and c[2] > a[0] and a[3] > c[1] and c[3] > a[1]:
            print('OVERLAP', a[4], c[4]); bad += 1
    for n, k in KEEPOUT.items():
        if a[2] > k[0] and k[2] > a[0] and a[3] > k[1] and k[3] > a[1] and not a[4].startswith(('U302', 'U401', 'U501', 'U502', 'J801', 'J802')):
            print('KEEPOUT', a[4], n); bad += 1
print('problems', bad)
