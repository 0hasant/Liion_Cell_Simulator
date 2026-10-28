"""Run KiCad DRC (pcbnew API) and summarise. Usage: python3 drc.py <board> <report.rpt>"""
import sys, re, collections
import pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
b.GetDesignSettings().m_MinResolvedSpokes = 1   # same as the project rule
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
ok = pcbnew.WriteDRCReport(b, sys.argv[2], pcbnew.EDA_UNITS_MILLIMETRES, True)
txt = open(sys.argv[2]).read()
kinds = collections.Counter(re.findall(r'^\[([a-z_]+)\]', txt, re.M))
print('report written:', ok)
for line in txt.splitlines():
    if line.startswith('**') or 'unconnected' in line.lower() and 'Found' in line:
        print(line)
print(dict(kinds))
