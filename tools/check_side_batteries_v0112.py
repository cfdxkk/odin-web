"""v0.11.2 actual-Three.js-pose contact sweep for all four flank mounts.

The first slider deliberately seats against the source hull rim at NAV zero;
its full gauge clears during the first one percent of the lift interval.
"""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
code=(R/'tools/check_side_batteries_v0110.py').read_text()
code=code.replace('work/v0110-review','work/v0112-review')
code=code.replace("assert not any(v for k,v in summary.items()if k!='samples'),summary",'''
assert all(summary[k]==0 for k in ['gunArmorEvents','group23Events','group12Events','armorFairingEvents']),summary
seating=[]
for row in results:
    for mount,contacts in row['mounts'].items():
        for pair in contacts['firstPairHull']:
            assert row['deployment']<=.01,(row['deployment'],mount,pair)
            assert pair.endswith('/ holo.001') or '_Skin_FixedTroughReturn' in pair,(row['deployment'],mount,pair)
            seating.append((row['deployment'],mount,pair))
summary['sourceRimSeatingContacts']=len(seating)
(out/'side-contact-summary.json').write_text(json.dumps(summary,indent=2))
''')
exec(compile(code,str(__file__),'exec'))
