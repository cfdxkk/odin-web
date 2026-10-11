"""Use the actual six source leaves and nose; add the requested rear carriage.

Run on v0.11.24. Source islands are selected as whole assemblies, never cut by
polygon facing. The original fixed trough, cheek supports and mount bearing
remain intact. All original source meshes retain their topology and UVs.
"""
import bpy,bmesh,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

root=Path(__file__).resolve().parents[1];scene=bpy.context.scene
asset=bpy.data.objects['Odin_Asset'];assert asset['version']=='0.11.24'
inv=asset.matrix_world.inverted();frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text(encoding='utf8'))
source_path=root.parent/'Odin 建模/odin.blend'
with source_path.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
light=bpy.data.materials['Odin_Paint_Light'];red=bpy.data.materials['Odin_Turret_Interior_DeepRed']
review=root/'docs/review/v0.11.25';review.mkdir(parents=True,exist_ok=True)
changed=set();removed=set();joint_changes=set();remove_keys=set();fixture={}
def points(o):return np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])
def face_key(ps):return tuple(sorted(tuple(round(float(v),4)for v in p)for p in ps))
def digest(o):
 h=hashlib.sha256();p=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',p);h.update(p.tobytes())
 for f in o.data.polygons:h.update(np.array(f.vertices[:],dtype=np.int32).tobytes());h.update(o.data.materials[f.material_index].name.encode())
 return h.hexdigest()
before={o.name:digest(o)for o in scene.objects if o.type=='MESH'}
joints={o.name:np.array(o.matrix_local).copy()for o in scene.objects if o.get('staticJoint')}
def erase(o):
 for c in list(o.children):erase(c)
 removed.add(o.name);data=o.data if o.type=='MESH'else None;bpy.data.objects.remove(o,do_unlink=True)
 if data and not data.users:bpy.data.meshes.remove(data)

with bpy.data.libraries.load(str(source_path),link=False)as(src,dst):dst.objects=['holo.001','odin.023','odin.071','holo.023']
source,g2,g4,separate_turret=dst.objects
for o in dst.objects:scene.collection.objects.link(o)
for o in [g2,g4]:o.modifiers.clear()
scene.frame_set(1);bpy.context.view_layer.update()
sp=np.array([source.matrix_world@v.co for v in source.data.vertices]);parents=list(range(len(sp)))
def find(i):
 while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
 return i
for e in source.data.edges:a,b=e.vertices;parents[find(a)]=find(b)
groups={};group_faces={}
for v in source.data.vertices:groups.setdefault(find(v.index),[]).append(v.index)
for f in source.data.polygons:group_faces.setdefault(find(f.vertices[0]),[]).append(f.index)

def extract(name,ids,parent,owner=None,coords=None):
 owner=owner or source;coords=sp if coords is None else coords
 cp=owner.copy();cp.data=owner.data.copy();cp.animation_data_clear();cp.modifiers.clear();scene.collection.objects.link(cp);cp.name=name
 for v,p in zip(cp.data.vertices,coords):v.co=Vector(p)
 bm=bmesh.new();bm.from_mesh(cp.data);bm.faces.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in ids],context='FACES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(cp.data);bm.free()
 cp.parent=asset;cp.matrix_parent_inverse=Matrix.Identity(4);cp.matrix_local=Matrix.Identity(4);bpy.context.view_layer.update()
 world=cp.matrix_world.copy();cp.parent=parent;cp.matrix_world=world
 for i,m in enumerate(cp.data.materials):
  label=m.name.lower()if m else''
  cp.data.materials[i]=bpy.data.materials['Odin_Paint_Orange']if'orange'in label else bpy.data.materials['Odin_Paint_Dark.001']if'dark'in label else light
 cp['sourceObject']='holo.023'if owner==separate_turret else'holo.001';cp['originalSourceArmor']=True;cp['sourceFaceCount']=len(ids);changed.add(cp.name)
 return cp

def plane_of(gid,C,Q):
 f=max((source.data.polygons[i]for i in group_faces[gid]),key=lambda f:f.area)
 p=(sp[list(f.vertices)]-C)@Q
 a,b,c=np.linalg.lstsq(np.c_[p[:,:2],np.ones(len(p))],p[:,2],rcond=None)[0]
 return np.array([-a,-b,1.]),float(c)

def folded_rotation(n,target):
 # Solve the longitudinal hinge rake and angle, keeping the axis parallel
 # to the source rail in plan. This changes only the rigid pivot transform.
 theta=-math.radians(175);rake=0.
 def error(t,r):
  R=np.array(Quaternion(Vector((0,1,r)).normalized(),t).to_matrix());v=R@n
  return np.array([-v[0]/v[2],-v[1]/v[2]])-target[:2],R,v
 for _ in range(12):
  e,R,v=error(theta,rake)
  if np.linalg.norm(e)<1e-9:break
  eps=1e-5;J=np.column_stack([(error(theta+eps,rake)[0]-e)/eps,(error(theta,rake+eps)[0]-e)/eps])
  step=np.linalg.solve(J,e);theta-=step[0];rake-=step[1]
 e,R,v=error(theta,rake);assert np.linalg.norm(e)<.00001
 return theta,rake,R,v

report={'version':'0.11.25','sourceSha256':source_hash,'stations':{}}
for number,original_gun in [(2,g2),(4,g4)]:
 scene.frame_set(1);bpy.context.view_layer.update();gm=original_gun.matrix_world.copy();gp=np.array([gm@v.co for v in original_gun.data.vertices]);old_origin=np.array(gm.translation)
 for side,mirror in [('Starboard',1),('Port',-1)]:
  name=f'SideBattery_{number}_{side}';C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);q=(sp-C)@Q
  leaves={(s,i):[]for s in [-1,1]for i in range(3)};caps=[];housing=[];fixed=[];rear_support=[]
  for gid,ids in groups.items():
   p=q[ids];lo=p.min(0);hi=p.max(0)
   if max(abs(p[:,0]))>6.3 or lo[1]<-43 or hi[1]>33 or lo[2]<-8 or hi[2]>8:continue
   if 200<=len(ids)<=300 and lo[1]<-38 and hi[1]<-8:housing.append(gid);continue
   if len(ids)==18 and lo[1]>17 and hi[1]>29:caps.append(gid);continue
   if len(ids)in(18,102):fixed.append(gid);continue
   if len(ids)==184:
    if hi[1]<-8.7:rear_support.append(gid)
    else:fixed.append(gid)
    continue
   if lo[0]*hi[0]<=0 or min(abs(lo[0]),abs(hi[0]))<2.1 or lo[1]<-18 or hi[1]>9.8 or hi[2]<-1.3 or lo[2]<-1.7:continue
   s=1 if p[:,0].mean()>0 else-1;y=p[:,1].mean();i=0 if y<-8.2 else 1 if y<.52 else 2
   leaves[s,i].append(gid)
  external_body_ids=set();external_points=None
  if name=='SideBattery_4_Port':
   external_points=np.array([separate_turret.matrix_world@v.co for v in separate_turret.data.vertices]);exq=(external_points-C)@Q
   for face in separate_turret.data.polygons:
    p=exq[list(face.vertices)]
    if p[:,2].max()>-.75:external_body_ids.add(face.index)
   # The separated object contains the housing and two lower bearing islands.
   # Select the entire connected housing, retaining both bearings on the hull.
   exparents=list(range(len(exq)))
   def exfind(i):
    while exparents[i]!=i:exparents[i]=exparents[exparents[i]];i=exparents[i]
    return i
   for e in separate_turret.data.edges:a0,b0=e.vertices;exparents[exfind(a0)]=exfind(b0)
   exgroups={}
   for vertex in separate_turret.data.vertices:exgroups.setdefault(exfind(vertex.index),[]).append(vertex.index)
   body_group=[gid for gid,vs in exgroups.items()if 200<=len(vs)<=300]
   assert len(body_group)==1
   external_body_ids={f.index for f in separate_turret.data.polygons if exfind(f.vertices[0])==body_group[0]}
   for fi in external_body_ids:remove_keys.add(face_key(external_points[list(separate_turret.data.polygons[fi].vertices)]))
  assert (len(housing)==1 or external_body_ids) and len(caps)==2,(name,housing,caps)
  assert all(leaves.values())
  for s in [-1,1]:
   assert sorted(len(groups[g])for g in leaves[s,0])[-1]>=33
   assert any(len(groups[g])==27 for g in leaves[s,1])
   assert any(len(groups[g])==24 for g in leaves[s,2])
  moving={fi for gid in housing+caps+rear_support+[g for gs in leaves.values()for g in gs]for fi in group_faces[gid]}
  for fi in moving:remove_keys.add(face_key(sp[list(source.data.polygons[fi].vertices)]))
  for old in [o for o in list(scene.objects)if o.name.startswith(name+'_')and o.parent==asset and ('_Shutter_'in o.name or '_FrontCap'in o.name)]:erase(old)
  carriage=bpy.data.objects.new(name+'_SourceCarriage',None);scene.collection.objects.link(carriage);carriage.parent=asset;carriage.location=C.tolist()
  carriage['staticJoint']=True;carriage['system']='single-source-carriage';carriage['barrel']=name
  closed_local=np.array([0,.4,-1.6]);offset=Q@closed_local
  carriage['closedOffsetModel']=offset.tolist();carriage['raiseStart']=.32;carriage['raiseEnd']=.42
  body=extract(name+'_OriginalTurretShell',external_body_ids,carriage,separate_turret,external_points)if external_body_ids else extract(name+'_OriginalTurretShell',set(group_faces[housing[0]]),carriage)
  braces=extract(name+'_OriginalRearChannelSupports',{fi for gid in rear_support for fi in group_faces[gid]},carriage)
  braces.data.materials.append(red)
  bp=(points(braces)-C)@Q
  for f in braces.data.polygons:
   p=bp[list(f.vertices)];normal=np.array(f.normal)@Q
   # Paint the channel floor and the faces pointing into the bore channel;
   # the downward and outward faces retain their original gray exterior.
   if (normal[2]>-.2 and abs(p[:,0].mean())<2.85) or normal[0]*p[:,0].mean()<-.2:
    f.material_index=len(braces.data.materials)-1
  if external_body_ids:
   # This separately exported object was bevelled during the old import.
   # Its evaluated fragments cannot be removed by raw source-face keys.
   # Restore the whole original fixed bearing pair and exclude the entire
   # source housing island; only its new carriage child owns that housing.
   fixed_body=bpy.data.objects['holo.023'];old_mesh=fixed_body.data
   fixed_body.data=separate_turret.data.copy()
   for vertex,p in zip(fixed_body.data.vertices,external_points):vertex.co=Vector(p)
   bm=bmesh.new();bm.from_mesh(fixed_body.data);bm.faces.ensure_lookup_table()
   bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index in external_body_ids],context='FACES')
   bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(fixed_body.data);bm.free()
   fixed_body.modifiers.clear();fixed_body.matrix_local=Matrix.Identity(4)
   for i,m in enumerate(fixed_body.data.materials):
    fixed_body.data.materials[i]=bpy.data.materials['Odin_Paint_Dark.001']if m and'dark'in m.name.lower()else light
   fixed_body['sourcePreservation']=True;fixed_body['sourceObject']='holo.023';fixed_body['sourceFixedBearingFaces']=len(fixed_body.data.polygons)
   if not old_mesh.users:bpy.data.meshes.remove(old_mesh)
   changed.add(fixed_body.name)
  gun=bpy.data.objects[name]
  for c in list(gun.children):erase(c)
  origin=old_origin*np.array([mirror,1,1]);adjust=Q@np.array([0,-1.6,.6]);new_origin=origin+adjust
  rest=Quaternion(Vector(Q[:,0]),math.radians(-2.0));rest_matrix=np.array(rest.to_matrix())
  gun.parent=carriage;gun.matrix_parent_inverse=Matrix.Identity(4);gun.matrix_local=Matrix.Translation(Vector(new_origin-C));joint_changes.add(name)
  gun['sourceRigRotationWXYZ']=list(rest);gun['userRequestedRestAdjustment']=True;gun['sourceOriginModel']=origin.tolist();gun['adjustedOriginModel']=new_origin.tolist()
  gun['hingeAxisModel']=Q[:,0].tolist();gun['restCorrectionDegrees']=-2.0;gun['rootAdjustmentLocal']=[0,-1.6,.6]
  child=original_gun.copy();child.data=original_gun.data.copy();child.modifiers.clear();child.animation_data_clear();scene.collection.objects.link(child);child.name=name+'_SourceBarrel';child.parent=gun;child.matrix_parent_inverse=Matrix.Identity(4);child.matrix_local=Matrix.Identity(4)
  mirrored=gp*np.array([mirror,1,1]);local=(mirrored-origin)@rest_matrix.T
  for v,p in zip(child.data.vertices,local):v.co=Vector(p)
  if mirror<0:
   bm=bmesh.new();bm.from_mesh(child.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(child.data);bm.free()
  for i,m in enumerate(child.data.materials):child.data.materials[i]=bpy.data.materials['Odin_Weapon_Steel']
  changed.add(child.name);child['originalSourceBarrel']=True
  cap=bpy.data.objects.new(name+'_FrontCap',None);scene.collection.objects.link(cap);cap.parent=asset;cap.location=C.tolist()
  cap['staticJoint']=True;cap['system']='single-front-cap';cap['barrel']=name;cap['sourceOpenPose']=True;cap['sourceRigidCap']=True;cap['originalSourceArmor']=True;cap['sourceCapStroke']=True
  capids={fi for gid in caps for fi in group_faces[gid]};skin=extract(name+'_OriginalFrontCap',capids,cap)
  cloud=np.concatenate([q[groups[g]]for g in caps]);fore=cloud[cloud[:,1]>cloud[:,1].max()-.04]
  target=np.mean([q[np.argmin(np.linalg.norm(q-np.array([s*.344,21.892,5.030]),axis=1))]for s in [-1,1]],axis=0)
  dy=float(target[1]-fore[:,1].mean());dz=float(target[2]-fore[:,2].max())
  cap_offset=Q@np.array([0,dy,dz]);lift=.6*Q[:,2]
  cap['slideVector']=cap_offset.tolist();cap['clearanceLiftVector']=lift.tolist();cap['advanceVector']=(-dy*Q[:,1]).tolist();cap['parkingSettleVector']=(-dz*Q[:,2]-lift).tolist()
  cap['releaseEnd']=.03;cap['slideStart']=.04;cap['slideEnd']=.10;cap['settleStart']=.105;cap['settleEnd']=.11
  cap['sourceClearanceOffsetModel']=[0.,0.,0.];cap['settleVector']=[0.,0.,0.]
  skin.data.materials.append(red)
  for f in skin.data.polygons:
   p=(points(skin)[list(f.vertices)]-C)@Q
   if p[:,2].mean()<np.max(cloud[:,2])-.4 and f.normal.dot(Vector(Q[:,2]))<-.2:f.material_index=len(skin.data.materials)-1
  # The broad inward source cap face defines the common closed inner roof.
  source_cap=caps[0];fs=[source.data.polygons[fi]for fi in group_faces[source_cap]]
  cap_face=sorted(fs,key=lambda f:f.area,reverse=True)[1]
  cp=q[list(cap_face.vertices)];a,b,c=np.linalg.lstsq(np.c_[abs(cp[:,0]),cp[:,1],np.ones(len(cp))],cp[:,2],rcond=None)[0]
  target_plane=np.array([a,b,c+dz-b*dy]);assert -1.8<a<-1.3,(name,target_plane)
  rows=[]
  for (s,i),islands in leaves.items():
   ids={fi for gid in islands for fi in group_faces[gid]}
   primary=max(islands,key=lambda gid:max(source.data.polygons[fi].area for fi in group_faces[gid]))
   n,d0=plane_of(primary,C,Q)
   normalized_n=n.copy();normalized_n[0]*=s
   theta,rake,R,v=folded_rotation(normalized_n,target_plane)
   theta*=s;axis_local=np.array([0,1,rake]);R=np.array(Quaternion(Vector(axis_local),theta).to_matrix());v=R@n
   Hx=s*2.65;hb=-17.8 if i==0 else -8.2 if i==1 else .35
   move=closed_local if i==0 else np.zeros(3)
   hz=(target_plane[2]*v[2]-d0-(v[0]-n[0])*Hx-(v[1]-n[1])*hb-v@move)/(v[2]-n[2])
   Hlocal=np.array([Hx,hb,hz]);H=C+Q@Hlocal;axis=Q@axis_local;axis/=np.linalg.norm(axis)
   j=bpy.data.objects.new(f'{name}_Shutter_{"Port"if s<0 else"Starboard"}_{i:02}',None);scene.collection.objects.link(j);j.parent=carriage if i==0 else asset;j.location=(H-C if i==0 else H).tolist()
   j['staticJoint']=True;j['system']='single-shutter';j['barrelJoint']=name;j['panelIndex']=i;j['physicalHinge']=True;j['originalSourceArmor']=True;j['sourceObject']='holo.001';j['sourceIslandIds']=islands
   j['hingeAxisModel']=axis.tolist();j['closedAngleDegrees']=math.degrees(theta);j['openingTravelDegrees']=abs(math.degrees(theta));j['sourceOpenPose']=True
   j['openStart']=.12+.02*(2-i);j['openEnd']=.24+.02*(2-i);j['followsSourceCarriage']=i==0
   armor=extract(j.name+'_OriginalArmor',ids,j);armor.data.materials.append(red)
   ap=(points(armor)-C)@Q
   for f in armor.data.polygons:
    p=ap[list(f.vertices)];distance=(p@n-d0)/np.linalg.norm(n)
    if distance.mean()>-.18:f.material_index=len(armor.data.materials)-1
   j['hingeEdgeModel']=[H.tolist(),(H+axis*9).tolist()]
   j['closedPlaneLocal']=target_plane.tolist();j['sourceArmorFaces']=len(ids)
   rows.append({'name':j.name,'islands':islands,'faces':len(ids),'vertices':len(armor.data.vertices),'carriageFollower':i==0,'hingeLocal':Hlocal.tolist(),'closedAngle':math.degrees(theta)})
  fixed_ids={fi for gid in fixed for fi in group_faces[gid]}
  expected_fixed={face_key(sp[list(source.data.polygons[fi].vertices)])for fi in fixed_ids}
  report['stations'][name]={'leaves':rows,'sourceNoseFaces':len(capids),'sourceTurretFaces':len(external_body_ids)if external_body_ids else len(group_faces[housing[0]]),'carriageOffsetLocal':closed_local.tolist(),'sourceFixedFaces':len(fixed_ids),'sourceMovingFaces':len(moving)+len(external_body_ids),'sourceMovingVertices':len({v for fi in moving for v in source.data.polygons[fi].vertices}),'sourceFixedKeys':len(expected_fixed),'targetInnerPlane':target_plane.tolist()}
  # Independent golden poses from the original action, transformed by only
  # the user-requested rigid rest placement and the new parent carriage.
  samples=[];initial_rotation=gm.to_quaternion();start_frame=float(gun['sourceFrameRange'][0]);end_frame=float(gun['sourceFrameRange'][1])
  for d,frame in [(0.,1.),(.37,1.),(start_frame/100,start_frame),((start_frame+end_frame)/200,(start_frame+end_frame)/2),(end_frame/100,end_frame)]:
   scene.frame_set(int(frame),subframe=frame-int(frame));m=original_gun.matrix_world.copy()
   p=np.array([m@original_gun.data.vertices[k].co for k in[0,100]])*np.array([mirror,1,1]);p=new_origin+(p-origin)@rest_matrix.T
   fraction=max(0,min(1,(d-.32)/.10));fraction=fraction*fraction*(3-2*fraction);parent_move=offset*(1-fraction)
   samples.append({'frame':frame,'deployment':d,'origin':(new_origin+parent_move).tolist(),'vertices':{str(k):(p[t]+parent_move).tolist()for t,k in enumerate([0,100])}})
  fixture[name]=samples
  scene.frame_set(1);bpy.context.view_layer.update()

# Only positively identified source armor and moving turret islands leave the
# fixed hull. The complete original trough and cheek supports stay static.
for o in [bpy.data.objects['holo.001'],bpy.data.objects['Flank24_OriginalFixedHull'],bpy.data.objects['holo.023']]:
 bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table()
 erase_faces=[f for f in bm.faces if face_key([(inv@o.matrix_world)@v.co for v in f.verts])in remove_keys]
 bmesh.ops.delete(bm,geom=erase_faces,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(o.data);bm.free();changed.add(o.name)

for name,h in before.items():
 if name not in changed and name not in removed:assert digest(bpy.data.objects[name])==h,('Unrelated mesh changed',name)
for name,m in joints.items():
 if name not in joint_changes and name not in removed:assert np.array_equal(np.array(bpy.data.objects[name].matrix_local),m),('Unrelated joint changed',name)
for o in list(dst.objects):bpy.data.objects.remove(o,do_unlink=True)
for o in scene.objects:o.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
with source_path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==source_hash
report.update(unchangedOtherMeshes=len(before)-len(removed&set(before))-len(changed&set(before)),unchangedOtherJoints=len(joints)-len(removed&set(joints))-len(joint_changes),animationClips=0)
(review/'source-armor.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(root/'tests/fixtures/flank-source-motion-v01125.json').write_text(json.dumps(fixture,indent=2),encoding='utf8')
asset['version']='0.11.25';bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.25.blend'),compress=True)
print('SOURCE_ARMOR',[(name,len(row['leaves']),row['sourceMovingFaces'])for name,row in report['stations'].items()],flush=True)
