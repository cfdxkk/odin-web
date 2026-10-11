"""Check all restored quad poses, original receiver seating and barrel clearance."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,Euler
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
fit=json.loads((root/'docs/review/v0.11.33/source-restoration.json').read_text())
def ease(a,b,d):t=max(0,min(1,(d-a)/(b-a)));return t*t*(3-2*t)
def points(o):return np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])
def tree(objects):
 vs=[];fs=[]
 for o in objects:
  p=points(o);offset=len(vs);vs.extend(Vector(v)for v in p);o.data.calc_loop_triangles();fs.extend(tuple(offset+i for i in t.vertices)for t in o.data.loop_triangles)
 cloud=np.array(vs);tris=cloud[np.array(fs,dtype=np.int32)]
 return BVHTree.FromPolygons(vs,fs,all_triangles=True,epsilon=0.),tris
def intersections(a,b):
 hits=a[0].overlap(b[0])
 if not hits:return 0
 ia,ib=np.array(hits,dtype=np.int32).T;ta=a[1][ia];tb=b[1][ib];ea=np.roll(ta,-1,axis=1)-ta;eb=np.roll(tb,-1,axis=1)-tb;na=np.cross(ea[:,0],ea[:,1]);nb=np.cross(eb[:,0],eb[:,1])
 axes=np.concatenate([na[:,None],nb[:,None],np.cross(ea[:,:,None],eb[:,None,:]).reshape(-1,9,3),np.cross(na[:,None],ea),np.cross(nb[:,None],eb)],axis=1)
 size=np.linalg.norm(axes,axis=2);pa=np.einsum('nac,nvc->nav',axes,ta);pb=np.einsum('nac,nvc->nav',axes,tb);overlap=np.minimum(pa.max(2),pb.max(2))-np.maximum(pa.min(2),pb.min(2));mask=~((size>1e-8)&(overlap<-size*1e-5)).any(1)
 return int(np.sum(mask))
origins={o:o.location.copy()for o in bpy.context.scene.objects if o.get('staticJoint')};references={o:np.array(o.matrix_local).copy()for o in bpy.context.scene.objects if o.type=='MESH'}
def pose(d):
 for side in['Port','Starboard']:
  c=bpy.data.objects[f'PDC_{side}_Carriage'];a=.5+.5*ease(c['sourceCarriageStart'],c['sourceCarriageEnd'],d);amount=2*(ease(0,1,a)-.5);c.location=origins[c]+Vector(np.array(c['sourceClosedOrigin'])-np.array(c['sourceDeployedOrigin']))*(1-amount)
  g=bpy.data.objects[f'PDC_{side}_Gimbal'];a=ease(g['sourceAimStart'],g['sourceAimEnd'],d);start=g['sourceEulerStart'];end=g['sourceEulerEnd'];q=Euler([v+(end[i]-v)*a for i,v in enumerate(start)],'XYZ').to_quaternion()@Euler(start,'XYZ').to_quaternion().inverted()
  if g['sourceMirror']>0:q.y=-q.y;q.z=-q.z
  g.rotation_mode='QUATERNION';g.rotation_quaternion=q
  for i in range(4):
   r=bpy.data.objects[f'PDC_{side}_Cradle_{i}'];t=bpy.data.objects[f'PDC_{side}_Arm_{i}'];p=bpy.data.objects[f'PDC_{side}_HullPetal_{i}'];amount=1-ease(r['compactStart'],r['compactEnd'],d);amount+=r.get('compactLead',0)*amount*(1-amount)**2
   guide=bpy.data.objects[f'PDC_{side}_CradleGuide_{i}'];guide.location=origins[guide]+Vector(guide['compactVector'])*amount
   r.location=origins[r]+Vector(r['compactVector'])*amount;t.location=origins[t]+Vector(t['slideVector'])*(1-ease(t['slideStart'],t['slideEnd'],d))
   petal_amount=amount**p['petalPackingExponent'];p.location=origins[p]+Vector(p['compactVector'])*petal_amount
   p.location.z+=p['translationClearanceZ']*(1-petal_amount)*(1-ease(p['translationClearanceReleaseStart'],p['translationClearanceReleaseEnd'],d))
   p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion()
 bpy.context.view_layer.update()
report={}
pose(.78);petal_sources={o.name:points(o)for o in bpy.context.scene.objects if o.type=='MESH'and 'HullPetal'in o.name}
for side,sign in[('Port',-1),('Starboard',1)]:
 tubes=[bpy.data.objects[f'PDC_{side}_ArmMesh_{i}']for i in range(4)];petals=[bpy.data.objects[f'PDC_{side}_HullPetal_{i}_Skin']for i in range(4)];events=[];cradle_contacts=[];max_x=0.;max_turn=0.
 cradles=[[bpy.data.objects[f'PDC_{side}_FixedFork_{i}'],bpy.data.objects[f'PDC_{side}_RootArmor_{i}']]for i in range(4)]
 for d in[i/400 for i in range(401)]:
  pose(d)
  for p in petals:
   max_x=max(max_x,float(np.max(abs(points(p)[:,0]-petal_sources[p.name][:,0]))))
   max_turn=max(max_turn,float(p.parent.rotation_quaternion.angle))
  a=tree(tubes);hits=intersections(a,tree(petals))
  if hits:events.append({'progress':d,'triangleContacts':hits})
  bearings=[tree(group)for group in cradles]
  for i in range(4):
   for j in range(i+1,4):
    hits=intersections(bearings[i],bearings[j])
    if hits:cradle_contacts.append({'progress':d,'quadrants':[i,j],'triangleContacts':hits})
  for o,m in references.items():assert np.max(abs(np.array(o.matrix_local)-m))<.00005,('Nonrigid source mesh',o.name)
 pose(0);seats=[];ends=[]
 for row in fit['quads'][side]['petalSeats']:
  p=bpy.data.objects[row['joint']].children[0];ps=points(p);seam=row['forwardSeam'];fixed=points(bpy.data.objects[seam['fixedMesh']])[seam['fixedLipVertices']]
  a=ps[seam['armorCornerVertex']];b=ps[seam['armorTipVertex']]
  u=fixed[np.argmin(np.linalg.norm(fixed-b,axis=1))];w=fixed[np.argmax(fixed[:,0]*sign)]
  gap=float(np.linalg.norm(b-u));v=b-a;h=w-u
  angle=math.degrees(math.asin(min(1.,np.linalg.norm(np.cross(v,h))/np.linalg.norm(v)/np.linalg.norm(h))))
  assert gap<.00003 and angle<.001,(row['joint'],gap,angle)
  seats.append({'joint':row['joint'],'closedEdgeEndpointGap':gap,'closedEdgeAngleDegrees':angle,'closedForemostCoordinate':float((ps[:,0]*sign).max())})
 for i,o in enumerate(tubes):
  p=points(o);tip=float((p[:,0]*sign).max());seat=seats[i]['closedForemostCoordinate'];assert tip<seat-.20,(side,i,tip,seat)
  pose(.78);source_tip=float((points(o)[:,0]*sign).max());reference_tip=source_tip-10-fit['tubeReference']['newTravel'];pose(0)
  assert abs(tip-reference_tip)<.00002,(side,i,tip,reference_tip)
  ends.append({'quadrant':i,'closedTubeTip':tip,'closedArmorForemost':seat,'hiddenBehindArmor':seat-tip,
               'previous11PercentTubeTip':reference_tip,'referenceTipError':abs(tip-reference_tip)})
 c=bpy.data.objects[f'PDC_{side}_Carriage'];C=(inv@c.matrix_world).translation;assert np.max(abs(np.array(C)-np.array(c['sourceClosedOrigin'])))<.00002
 report[side]={'poses':401,'barrelPetalContacts':events,'cradlePairContacts':cradle_contacts,'closedSourceCarriage':list(C),'closedForwardSeams':seats,'maxArmorVertexXChange':max_x,'maxArmorRotationRadians':max_turn,'hiddenBarrelTips':ends,'sourceMeshesRemainRigid':True}
(root/'docs/review/v0.11.33/mesh-clearance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('QUAD_FULL_SWEEP',[(s,len(r['barrelPetalContacts']),max(v['closedEdgeEndpointGap']for v in r['closedForwardSeams']))for s,r in report.items()],flush=True)
assert all(not r['barrelPetalContacts']for r in report.values()),'A restored barrel crosses an original closing hull petal'
assert all(not r['cradlePairContacts']for r in report.values()),'Original gray cradles cross each other'

assert all(r['maxArmorVertexXChange']==0 and r['maxArmorRotationRadians']==0 for r in report.values()),'A gray armor vertex moved in ship X or rotated'
