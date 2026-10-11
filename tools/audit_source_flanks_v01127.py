"""Read-only triangle and rigid articulation audit for the fitted source armor and limited sweeps."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,Euler
from mathutils.bvhtree import BVHTree

root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
def points(o):return np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])
def ease(a,b,d):t=max(0,min(1,(d-a)/(b-a)));return t*t*(3-2*t)
def tree(objects,region=None):
 vs=[];fs=[]
 for o in objects:
  p=points(o);base=len(vs);vs.extend(Vector(v)for v in p);o.data.calc_loop_triangles()
  for t in o.data.loop_triangles:
   if region:
    C,Q=region;local=(p[list(t.vertices)]-C)@Q;lo,hi=local.min(0),local.max(0)
    if hi[0]<-8 or lo[0]>8 or hi[1]<-44 or lo[1]>33 or hi[2]<-8 or lo[2]>10:continue
   fs.append(tuple(base+i for i in t.vertices))
 cloud=np.array(vs);triangles=cloud[np.array(fs,dtype=np.int32)]
 return BVHTree.FromPolygons(vs,fs,all_triangles=True,epsilon=0.),triangles
def intersections(a,b,detail=False):
 hits=a[0].overlap(b[0])
 if not hits:return 0
 ia,ib=np.array(hits,dtype=np.int32).T;ta=a[1][ia];tb=b[1][ib]
 ea=np.roll(ta,-1,axis=1)-ta;eb=np.roll(tb,-1,axis=1)-tb;na=np.cross(ea[:,0],ea[:,1]);nb=np.cross(eb[:,0],eb[:,1])
 axes=np.concatenate([na[:,None],nb[:,None],np.cross(ea[:,:,None],eb[:,None,:]).reshape(-1,9,3),np.cross(na[:,None],ea),np.cross(nb[:,None],eb)],axis=1)
 size=np.linalg.norm(axes,axis=2);pa=np.einsum('nac,nvc->nav',axes,ta);pb=np.einsum('nac,nvc->nav',axes,tb)
 overlap=np.minimum(pa.max(2),pb.max(2))-np.maximum(pa.min(2),pb.min(2))
 mask=~((size>1e-8)&(overlap<-size*1e-5)).any(1)
 return (ta[mask],tb[mask])if detail else int(np.sum(mask))

report={}
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text(encoding='utf8'))
for name in [f'SideBattery_{i}_{s}'for i in[2,4]for s in['Starboard','Port']]:
 gun=bpy.data.objects[name];cap=bpy.data.objects[name+'_FrontCap'];carriage=bpy.data.objects[name+'_SourceCarriage']
 leaves=[bpy.data.objects[f'{name}_Shutter_{s}_{i:02}']for s in['Port','Starboard']for i in range(3)]
 body=bpy.data.objects[name+'_OriginalTurretShell'];rear=bpy.data.objects[name+'_OriginalRearChannelSupports']
 origins={j:j.location.copy()for j in[gun,cap,carriage]+leaves}
 meshes=[c for j in[gun,cap]+leaves for c in j.children if c.type=='MESH']+[body,rear]
 references={o:np.array(o.matrix_local).copy()for o in meshes};source_open={j:points(j.children[0])for j in leaves}
 C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes'])
 fixed=tree([bpy.data.objects[n]for n in['holo.001','Flank24_OriginalFixedHull','holo.023','Flank_4_Starboard_FixedBearingPair']+[o.name for o in bpy.context.scene.objects if o.get('fixedOuterHull')]],(C,Q))
 original_fixed_contacts=[]
 for j in[cap]+leaves:
  hits=intersections(tree([c for c in j.children if c.type=='MESH']),fixed)
  if hits:original_fixed_contacts.append({'object':j.name,'triangleContacts':hits})
 def pose(d):
  for j in leaves:
   angle=j['closedAngleDegrees']-math.copysign(j['openingTravelDegrees'],j['closedAngleDegrees'])*ease(j['openStart'],j['openEnd'],d)
   j.rotation_mode='QUATERNION';j.rotation_quaternion=Quaternion(Vector(j['hingeAxisModel']),math.radians(angle))
  amount=ease(gun['sourceMotionStart'],gun['sourceMotionEnd'],d);parent=Quaternion(gun['sourceParentRotationWXYZ']);start=parent@Euler(gun['sourceEulerStart'],'XYZ').to_quaternion()
  current=parent@Euler([a+(b-a)*amount for a,b in zip(gun['sourceEulerStart'],gun['sourceEulerEnd'])],'XYZ').to_quaternion();turn=current@start.inverted()
  if gun['sourceMirror']<0:turn.y=-turn.y;turn.z=-turn.z
  rest=Quaternion(gun['sourceRigRotationWXYZ']);gun.rotation_mode='QUATERNION';gun.rotation_quaternion=rest@turn@rest.inverted()
  carriage.location=origins[carriage]+Vector(carriage['closedOffsetModel'])*(1-ease(carriage['raiseStart'],carriage['raiseEnd'],d))
  move=np.array(cap['slideVector'])+np.array(cap['clearanceLiftVector'])*ease(0,cap['releaseEnd'],d)+np.array(cap['advanceVector'])*ease(cap['slideStart'],cap['slideEnd'],d)+np.array(cap['parkingSettleVector'])*ease(cap['settleStart'],cap['settleEnd'],d)
  cap.location=origins[cap]+Vector(move);bpy.context.view_layer.update()
 collisions=[];shell_contacts=[];source_shell_contacts=[];fixed_armor_contacts=[]
 # The source barrel and socket are a connected mechanical mount. Keep a
 # separate original-pose contact baseline, instead of treating all breech
 # contact with its housing as a new collision or omitting those contacts.
 source_origin=np.array(gun['sourceOriginModel']);adjusted_origin=np.array(gun['adjustedOriginModel'])
 rest=Quaternion(gun['sourceRigRotationWXYZ']);rest_matrix=np.array(rest.to_matrix())
 gun_mesh=gun.children[0];gun_mesh.data.calc_loop_triangles()
 source_points=source_origin+(points(gun_mesh)-adjusted_origin)@rest_matrix
 source_faces=np.array([t.vertices[:]for t in gun_mesh.data.loop_triangles],dtype=np.int32)
 source_body=tree([body])
 for d in[i/100 for i in range(101)]:
  pose(d);barrel=tree([c for c in gun.children if c.type=='MESH']);touching=[]
  for j in[cap]+leaves:
   hits=intersections(barrel,tree([c for c in j.children if c.type=='MESH']))
   if hits:touching.append([j.name,hits])
  if touching:collisions.append({'progress':d,'contacts':touching})
  if d<=.30 or d==1:
   contacts=[]
   for j in[cap]+leaves:
    pair=intersections(tree([c for c in j.children if c.type=='MESH']),fixed,True)
    if isinstance(pair,tuple)and len(pair[0]):
     p=(pair[0].reshape(-1,3)-C)@Q
     contacts.append({'object':j.name,'triangleContacts':len(pair[0]),'armorBoundsLocal':[p.min(0).tolist(),p.max(0).tolist()]})
   if contacts:fixed_armor_contacts.append({'progress':d,'contacts':contacts})
  hits=intersections(barrel,tree([body]))
  if hits:shell_contacts.append({'progress':d,'triangleContacts':hits})
  source_turn=np.array((rest.inverted()@gun.rotation_quaternion@rest).to_matrix())
  original_points=source_origin+(source_points-source_origin)@source_turn.T
  original_barrel=(BVHTree.FromPolygons([Vector(v)for v in original_points],source_faces.tolist(),all_triangles=True,epsilon=0.),original_points[source_faces])
  hits=intersections(original_barrel,source_body)
  if hits:source_shell_contacts.append({'progress':d,'triangleContacts':hits})
  for o in meshes:assert np.max(abs(references[o]-np.array(o.matrix_local)))<.0002,('Non-rigid geometry',o.name)
 pose(1)
 expected={}
 for j in leaves:
  H=np.array((inv@j.matrix_world).translation);R=np.array(Quaternion(Vector(j['hingeAxisModel']),math.radians(j['limitedOpenAngleDegrees'])).to_matrix())
  expected[j]=H+(source_open[j]-H)@R.T
 original_error=max(float(np.max(abs(points(j.children[0])-expected[j])))for j in leaves)
 assert original_error<.0001,(name,original_error)
 report[name]={'poses':101,'barrelArmorContacts':collisions,'barrelHousingContacts':shell_contacts,'originalBarrelHousingContacts':source_shell_contacts,'armorFixedHullContacts':fixed_armor_contacts,'originalOpenArmorFixedHullContacts':original_fixed_contacts,'limitedOpenCoordinateError':original_error,'rigidMeshes':len(meshes)}
 C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);details=[]
 for d in[0.,1.]:
  pose(d);barrel=tree([gun.children[0]])
  for other in[body]+[j.children[0]for j in leaves]:
   pair=intersections(barrel,tree([other]),True)
   if isinstance(pair,tuple) and len(pair[0]):
    p=(pair[0].reshape(-1,3)-C)@Q
    details.append({'progress':d,'object':other.name,'barrelBoundsLocal':[p.min(0).tolist(),p.max(0).tolist()]})
 report[name]['contactRegions']=details
 for j in[gun]+leaves:j.rotation_quaternion=Quaternion((1,0,0,0))
 for j in[cap,carriage]:j.location=origins[j]
 bpy.context.view_layer.update()
(root/'docs/review/v0.11.27/mesh-clearance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('SOURCE_CLEARANCE',[(n,len(r['barrelArmorContacts']),len(r['barrelHousingContacts']))for n,r in report.items()],flush=True)
