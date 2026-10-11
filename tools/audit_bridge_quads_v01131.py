"""Check all restored quad poses, original receiver seating and barrel clearance."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,Euler
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
fit=json.loads((root/'docs/review/v0.11.31/source-restoration.json').read_text())
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
   r=bpy.data.objects[f'PDC_{side}_Cradle_{i}'];t=bpy.data.objects[f'PDC_{side}_Arm_{i}'];p=bpy.data.objects[f'PDC_{side}_HullPetal_{i}'];amount=1-ease(r['compactStart'],r['compactEnd'],d)
   r.location=origins[r]+Vector(r['compactVector'])*amount;t.location=origins[t]+Vector(t['slideVector'])*(1-ease(t['slideStart'],t['slideEnd'],d));p.location=origins[p]+Vector(p['compactVector'])*amount+Vector(p['clearanceVector'])*(1-ease(p['clearanceStart'],p['clearanceEnd'],d))*(1-amount**3);p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion().slerp(Quaternion(p['compactRotationWXYZ']),amount)
 bpy.context.view_layer.update()
report={}
for side,sign in[('Port',-1),('Starboard',1)]:
 tubes=[bpy.data.objects[f'PDC_{side}_ArmMesh_{i}']for i in range(4)];petals=[bpy.data.objects[f'PDC_{side}_HullPetal_{i}_Skin']for i in range(4)];events=[];cradle_contacts=[]
 for d in[i/400 for i in range(401)]:
  pose(d);a=tree(tubes);hits=intersections(a,tree(petals))
  if hits:events.append({'progress':d,'triangleContacts':hits})
  for o,m in references.items():assert np.max(abs(np.array(o.matrix_local)-m))<.00005,('Nonrigid source mesh',o.name)
 pose(0);seats=[];ends=[]
 for row in fit['quads'][side]['petalSeats']:
  p=bpy.data.objects[row['joint']].children[0];ps=points(p);n=np.array(row['receiverNormal']);target=np.array(row['receiverPoints'][0]);errors=[]
  for f,i in zip(p.data.polygons,p['sourceFaceIds']):
   if i in row['sourceOuterFaces']:errors.extend(abs(float(np.dot(n,v-target)))for v in ps[list(f.vertices)])
  assert max(errors)<.215,(row['joint'],max(errors))
  seats.append({'joint':row['joint'],'maxSkinToOriginalReceiverPlane':max(errors),'closedForemostCoordinate':float((ps[:,0]*sign).max())})
 for i,o in enumerate(tubes):
  p=points(o);tip=float((p[:,0]*sign).max());seat=seats[i]['closedForemostCoordinate'];assert tip<seat-.20,(side,i,tip,seat)
  ends.append({'quadrant':i,'closedTubeTip':tip,'closedArmorForemost':seat,'hiddenBehindArmor':seat-tip})
 c=bpy.data.objects[f'PDC_{side}_Carriage'];C=(inv@c.matrix_world).translation;assert np.max(abs(np.array(C)-np.array(c['sourceClosedOrigin'])))<.00002
 report[side]={'poses':401,'barrelPetalContacts':events,'closedSourceCarriage':list(C),'originalReceiverSeats':seats,'hiddenBarrelTips':ends,'sourceMeshesRemainRigid':True}
(root/'docs/review/v0.11.31/mesh-clearance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('QUAD_FULL_SWEEP',[(s,len(r['barrelPetalContacts']),max(v['maxSkinToOriginalReceiverPlane']for v in r['originalReceiverSeats']))for s,r in report.items()],flush=True)
assert all(not r['barrelPetalContacts']for r in report.values()),'A restored barrel crosses an original closing hull petal'
