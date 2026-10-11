"""Run on v0.11.40: retain its quad motion and relieve tube center packing.

Preserve every mesh, rest frame, fitted petal and original axial interval.
Tube bearings stay attached; the long guide retains its net 0.60 stroke.
"""
import bpy, json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
review=root/'docs/review/v0.11.42';review.mkdir(parents=True,exist_ok=True)
rows=[]
for side in ['Port','Starboard']:
 for i in range(4):
  r=bpy.data.objects[f'PDC_{side}_Cradle_{i}']
  g=bpy.data.objects[f'PDC_{side}_CradleGuide_{i}']
  t=bpy.data.objects[f'PDC_{side}_Arm_{i}']
  ys=1 if i<2 else -1;zs=1 if i%2==0 else -1
  before=list(r['compactVector'])
  r['compactVector']=[0.,ys*1.98,zs*.30]
  g['compactVector']=[0.,-ys*1.38,0.]
  for joint in [r,g]:
   joint['compactReleaseRelief']=.60
   joint['compactReliefStart']=.12
   joint['compactReliefEnd']=.15
  assert t['slideStart']==.03 and t['slideEnd']==.18
  rows.append({'side':side,'quadrant':i,'previousCompactVector':before,
    'compactVector':list(r['compactVector']),'guideVector':list(g['compactVector']),
    'compactReleaseRelief':.60,'compactReliefInterval':[.12,.15],
    'packingInterval':[.03,.18],'tubeExtensionInterval':[.03,.18],
    'tubeAxialTravel':float(t['stowTravel'])})
asset=bpy.data.objects['Odin_Asset'];asset['version']='0.11.42'
asset['bridgeQuadStrokeRevision']='Restore v0.11.40 quad motion. Only relieve transverse tube packing after the fitted petals clear; original axial travel and armor motion are unchanged.'
assert not bpy.data.actions
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.42.blend'),compress=True)
(review/'assembly-fit.json').write_text(json.dumps({'version':'0.11.42','baseline':'0.11.40','quadrants':rows},indent=2)+'\n',encoding='utf8')
print('SHORTER_QUAD_PACKING',len(rows),flush=True)
