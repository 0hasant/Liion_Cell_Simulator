"""Move a few reference designators that sit on the board edge or on other silkscreen.
Usage: python3 silkfix.py <in> <out>"""
import sys, pcbnew
MOVE = {  # ref: (dx, dy) in mm, relative to the footprint position
    'H101': (0, 4.6), 'H102': (-4.6, 0), 'J704': (0, 4.6), 'J705': (0, 4.6), 'J706': (0, 4.6),
    'Q301': (5.5, -4.2), 'J802': (-3.5, 3.0), 'C102': (-7.0, 0), 'J703': (0, 7.5), 'Q702': (2.5, 3.2),
}
b = pcbnew.LoadBoard(sys.argv[1])
for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref in MOVE:
        p = fp.GetPosition()
        dx, dy = MOVE[ref]
        fp.Reference().SetPosition(pcbnew.VECTOR2I(p.x + pcbnew.FromMM(dx), p.y + pcbnew.FromMM(dy)))
        fp.Reference().SetTextAngleDegrees(0)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2])
