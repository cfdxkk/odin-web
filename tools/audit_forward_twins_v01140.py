"""Check actual travel against stationary foundations, fixed hoods and guides."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
# Use the same triangle SAT implementation as the independently checked v38 sweep.
helpers=(root/'tools/audit_forward_twins_v01138.py').read_text().split('hoods=')[0]
exec(compile(helpers,str(root/'tools/audit_forward_twins_v01138.py'),'exec'))
def apply(row):
 # Only these source joints affect the tested four receivers; leave all
 # unrelated mesh dependencies untouched during the high resolution sweep.
 for j in row['joints']:
  if not j['name'].startswith(tuple(f'Defense_{i:02}_'for i in range(1,5))):continue
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);x,y,z,w=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((w,x,y,z))@basis
 bpy.context.view_layer.update()
rows=json.loads((root/'work/v01140-review/runtime-poses.json').read_text())
hoods={i:tree([bpy.data.objects[f'Defense_{i:02}_FixedHood']])for i in range(1,5)}
foundations={i:tree(children(f'Defense_{i:02}_FixedFoundation'))for i in range(1,5)}
fixedMatrices={i:np.array(bpy.data.objects[f'Defense_{i:02}_FoundationGeometry'].matrix_world)for i in range(1,5)}
carriageTurns={}
report={i:{'poses':0,'hoodContacts':[],'upperGuideContacts':[],'upperFoundationContacts':[],'supportFoundationEngagements':[],'maxFoundationWorldChange':0,'maxCradleRotationRadians':0,'horizontalOnlyControlContacts':[]}for i in range(1,5)}
for step,row in enumerate(rows):
 apply(row)
 for i,out in report.items():
  prefix=f'Defense_{i:02}';objects=children(prefix+'_Carriage');out['poses']+=1
  n=hits(tree(objects),hoods[i])
  if n:out['hoodContacts'].append({'progress':row['progress'],'time':row['time'],'triangleContacts':n})
  out['maxFoundationWorldChange']=max(out['maxFoundationWorldChange'],float(np.max(np.abs(np.array(bpy.data.objects[prefix+'_FoundationGeometry'].matrix_world)-fixedMatrices[i]))))
  turn=bpy.data.objects[prefix+'_Carriage'].rotation_quaternion.copy()
  if i not in carriageTurns:carriageTurns[i]=turn
  out['maxCradleRotationRadians']=max(out['maxCradleRotationRadians'],turn.rotation_difference(carriageTurns[i]).angle)
  upper=[o for o in objects if not o.get('completeTurretSupport')and not o.get('originalForwardGuides')]
  # The original lower shoe and foundation intentionally overlap at their
  # sliding bearing. Record that engagement, and reject contacts with the
  # upper gun, barrels and separate guides rather than deleting source faces.
  n=hits(tree([bpy.data.objects[prefix+'_LowerCradle']]),foundations[i])
  out['supportFoundationEngagements'].append({'progress':row['progress'],'triangleContacts':n})
  n=hits(tree([o for o in objects if not o.get('completeTurretSupport')]),foundations[i])
  if n:out['upperFoundationContacts'].append({'progress':row['progress'],'time':row['time'],'triangleContacts':n})
  n=hits(tree(upper),tree(children(prefix+'_Guides')))
  if n:out['upperGuideContacts'].append({'progress':row['progress'],'triangleContacts':n})
 if step%100==0:print('INCLINED_TWIN_SWEEP',step,len(rows),flush=True)
for i,out in report.items():
 c=bpy.data.objects[f'Defense_{i:02}_Carriage'];drop=-c['stowVectorModel'][2]
 for row in rows[:401]:
  if not .24<=row['progress']<=.64:continue
  u=max(0,min(1,(row['progress']-.24)/(.64-.24)));seated=1-u*u*(3-2*u)
  apply(row);c.location.z+=drop*seated;bpy.context.view_layer.update()
  n=hits(tree(children(c.name)),hoods[i])
  if n:out['horizontalOnlyControlContacts'].append({'progress':row['progress'],'triangleContacts':n})
(root/'docs/review/v0.11.40/mesh-clearance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('FIXED_FOUNDATION_CLEARANCE',[(i,len(r['hoodContacts']),len(r['upperGuideContacts']),len(r['upperFoundationContacts']),r['maxFoundationWorldChange'],r['maxCradleRotationRadians'])for i,r in report.items()],flush=True)
assert all(not r['hoodContacts']and not r['upperGuideContacts']and not r['upperFoundationContacts']and r['maxFoundationWorldChange']==0 and r['maxCradleRotationRadians']<1e-6 for r in report.values())
