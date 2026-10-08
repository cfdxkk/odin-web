"""Restore both original bridge quads, static mesh provenance and source motion.

Run on v0.11.30. The original file is opened read-only for mesh/curve capture;
the revised editable file and all animation metadata remain separate.
"""
import bpy,json,hashlib,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

root=Path(__file__).resolve().parents[1];source_path=root.parent/'Odin 建模/odin.blend'
review=root/'docs/review/v0.11.31';review.mkdir(parents=True,exist_ok=True)
def plain(v):
 if hasattr(v,'to_dict'):return{k:plain(x)for k,x in v.to_dict().items()}
 if hasattr(v,'to_list'):return[plain(x)for x in v.to_list()]
 if isinstance(v,dict):return{k:plain(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return[plain(x)for x in v]
 return v
def digest(o):
 h=hashlib.sha256();h.update(np.array([v.co for v in o.data.vertices],dtype=np.float32).tobytes())
 for f in o.data.polygons:
  h.update(np.array(f.vertices[:],dtype=np.int32).tobytes());h.update(o.data.materials[f.material_index].name.encode())
  if o.data.uv_layers.active:h.update(np.array([o.data.uv_layers.active.data[k].uv for k in f.loop_indices],dtype=np.float32).tobytes())
 return h.hexdigest()
def curve(o,path,index):
 a=o.animation_data.action
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for c in bag.fcurves:
     if c.data_path==path and c.array_index==index:return c
 raise ValueError((o.name,path,index))
def records(o,world):
 ps=np.array([world@v.co for v in o.data.vertices]);uv=o.data.uv_layers.active
 reflected=world.to_3x3().determinant()<0
 return {'points':ps,'faces':[list(reversed(f.vertices))if reflected else list(f.vertices)for f in o.data.polygons],
         'materials':[o.data.materials[f.material_index].name for f in o.data.polygons],
         'smooth':[f.use_smooth for f in o.data.polygons],
         'uv':[[list(uv.data[k].uv)for k in (reversed(f.loop_indices)if reflected else f.loop_indices)]for f in o.data.polygons]if uv else None,
         'edges':[list(e.vertices)for e in o.data.edges]}
def islands(data):
 p=list(range(len(data['points'])))
 def find(i):
  while p[i]!=i:p[i]=p[p[i]];i=p[i]
  return i
 for a,b in data['edges']:p[find(a)]=find(b)
 groups={}
 for i in range(len(p)):groups.setdefault(find(i),[]).append(i)
 return [{'ids':ids,'faces':[i for i,f in enumerate(data['faces'])if find(f[0])==find(ids[0])],
          'n':len(ids),'center':data['points'][ids].mean(0)}for ids in groups.values()]
with source_path.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source_path));s=bpy.context.scene;s.frame_set(45);bpy.context.view_layer.update()
source_objects={};source_origins={}
for inst in bpy.context.evaluated_depsgraph_get().object_instances:
 if inst.is_instance and inst.parent.name in('bridge turret','bridge turret.001')and inst.object.type=='MESH':
  side='Starboard'if inst.parent.name=='bridge turret'else'Port';name=inst.object.original.name
  source_objects[side,name]=records(inst.object.original,inst.matrix_world);source_origins[side,name]=np.array(inst.matrix_world.translation)
carriage_source={side:bpy.data.objects[suffix]for side,suffix in [('Starboard','bridge turret'),('Port','bridge turret.001')]}
carriage_deployed={side:np.array(o.matrix_world.translation)for side,o in carriage_source.items()}
carriage_closed={};fixture={'sourceSha256':source_hash,'sourceGeometryFrame':45,'closedCarriageFrame':30,'samples':[]}
for frame in[30,32,35,38,40,43,45,53,60,70,80,86]:
 s.frame_set(frame);bpy.context.view_layer.update();row={'frame':frame,'carriages':{},'guns':{}}
 for side,o in carriage_source.items():
  row['carriages'][side]=[list(r)for r in o.matrix_world]
  if frame==30:carriage_closed[side]=np.array(o.matrix_world.translation)
 for inst in bpy.context.evaluated_depsgraph_get().object_instances:
  if inst.is_instance and inst.object.original.name=='holo.014'and inst.parent.name in('bridge turret','bridge turret.001'):
   row['guns']['Starboard'if inst.parent.name=='bridge turret'else'Port']=[list(r)for r in inst.matrix_world]
 fixture['samples'].append(row)
aim=bpy.data.objects['Empty.007'];euler_start=[curve(aim,'rotation_euler',i).evaluate(53)for i in range(3)];euler_end=[curve(aim,'rotation_euler',i).evaluate(86)for i in range(3)]
fixture['eulerStart']=euler_start;fixture['eulerEnd']=euler_end
fixture['carriageBezier']={side:[{'co':list(k.co),'left':list(k.handle_left),'right':list(k.handle_right)}for k in curve(o,'location',0).keyframe_points]for side,o in carriage_source.items()}
hull=bpy.data.objects['holo.001'];hdata=records(hull,hull.matrix_world)
petal_data=json.loads((root/'work/v01131-review/quad-parts.json').read_text())['petals']
face_centers=np.array([hdata['points'][ids].mean(0)for ids in hdata['faces']])
def petal_seat(row,sign):
 p=np.array(row['center']);ys=1 if p[1]<-61.7066 else-1;zs=1 if p[2]<105.98 else-1
 target_id=(252817 if ys==1 else 252806)if zs==1 else(48381 if ys==1 else 87560)
 if sign<0:
  target_id=int(np.argmin(np.linalg.norm(face_centers-face_centers[target_id]*np.array([-1,1,1]),axis=1)))
 tp=hdata['points'][hdata['faces'][target_id]];n=np.cross(tp[1]-tp[0],tp[2]-tp[0]);n/=np.linalg.norm(n)
 outer=[]
 for i in row['faces']:
  ps=hdata['points'][hdata['faces'][i]];cross=np.cross(ps[1]-ps[0],ps[2]-ps[0]);area=np.linalg.norm(cross)/2
  if area>6 and cross[2]*(-zs)>0:outer.append((ps,cross/np.linalg.norm(cross),area,i))
 assert len(outer)==2,(sign,p,[(a,i)for ps,v,a,i in outer])
 source_n=sum(v*a for ps,v,a,i in outer);source_n/=np.linalg.norm(source_n)
 q=Vector(source_n).rotation_difference(Vector(n));R=np.array(q.to_matrix())
 area=sum(a for ps,v,a,i in outer);center=sum((p+(ps-p)@R.T).mean(0)*a for ps,v,a,i in outer)/area
 dy,dz=ys*.6,zs*.25;dx=-(np.dot(n,center-tp[0])+n[1]*dy+n[2]*dz)/n[0]
 shift=np.array([dx,dy,dz]);closed=p+(hdata['points'][row['ids']]-p)@R.T+shift
 errors=[abs(float(np.dot(n,v-tp[0])))for ps,v,a,i in outer for v in p+(ps-p)@R.T+shift]
 assert -18<sign*dx<0 and max(errors)<.5,(sign,p,dx,errors)
 return shift,q,{'sourceOuterFaces':[i for ps,v,a,i in outer],'sourceReceiverFace':target_id,'receiverPoints':tp.tolist(),'receiverNormal':n.tolist(),'closedPrimarySurfaceErrors':errors,'maxPrimarySurfaceError':max(errors),'closedBounds':[closed.min(0).tolist(),closed.max(0).tolist()],'guideSeatDegrees':math.degrees(q.angle)}
belt_faces=[182071,221180,232976,247874,175461,223163,231072,251065]
belt_sources={i:{'points':hdata['points'][hdata['faces'][i]],'material':hdata['materials'][i]}for i in belt_faces}
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.30.blend'))
s=bpy.context.scene;asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
before={o.name:digest(o)for o in s.objects if o.type=='MESH'}
joint_before={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in s.objects if o.get('staticJoint')}
removed=set();changed=set();report={'version':'0.11.31','sourceSha256':source_hash,'quads':{},'beltColors':[]}
def erase(o):
 for c in list(o.children):erase(c)
 removed.add(o.name);data=o.data if o.type=='MESH'else None;bpy.data.objects.remove(o,do_unlink=True)
 if data and not data.users:bpy.data.meshes.remove(data)
def joint(name,p,parent,system,**props):
 o=bpy.data.objects.new(name,None);s.collection.objects.link(o);o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4)
 bpy.context.view_layer.update();o.matrix_world=asset.matrix_world@Matrix.Translation(Vector(p));o['staticJoint']=True;o['system']=system
 for k,v in props.items():o[k]=v
 return o
def paint(label):
 return bpy.data.materials['Odin_Paint_Dark.001']if'dark'in label.lower()else bpy.data.materials['Odin_Paint_Light']
def mesh(name,data,ids,parent,source_name):
 ids=sorted(ids);used=sorted({v for i in ids for v in data['faces'][i]});index={v:i for i,v in enumerate(used)}
 faces=[[index[v]for v in data['faces'][i]]for i in ids];me=bpy.data.meshes.new(name);me.from_pydata(data['points'][used].tolist(),[],faces);me.update()
 o=bpy.data.objects.new(name,me);s.collection.objects.link(o);o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4)
 bpy.context.view_layer.update();me.transform((inv@parent.matrix_world).inverted());o.matrix_local=Matrix.Identity(4)
 materials=[]
 for i,f in zip(ids,me.polygons):
  mat=paint(data['materials'][i])
  if mat not in materials:materials.append(mat);me.materials.append(mat)
  f.material_index=materials.index(mat);f.use_smooth=data['smooth'][i]
 if data['uv']:
  uv=me.uv_layers.new(name='UVMap')
  for i,f in zip(ids,me.polygons):
   for loop,p in zip(f.loop_indices,data['uv'][i]):uv.data[loop].uv=p
 o['sourceObject']=source_name;o['restoredOriginalGeometry']=True;o['sourceFaceIds']=ids;o['sourceVertexIds']=used;o['sourceFrame']=45
 changed.add(name);return o
for side,sign in[('Port',-1),('Starboard',1)]:
 for old_name in [o.name for o in s.objects]:
  o=bpy.data.objects.get(old_name)
  if o is None:continue
  if o.name==f'PDC_{side}_Carriage' or o.name.startswith(f'PDC_{side}_HullPetal_') or o.name.startswith(f'PDC_{side}_FixedGuide_'):
   if o.name in bpy.data.objects:erase(o)
 C=carriage_deployed[side];G=source_origins[side,'holo.014'];data=source_objects[side,'holo.014'];support=source_objects[side,'holo.016'];groups=islands(data)
 carriage=joint(f'PDC_{side}_Carriage',C,asset,'pdc',side=sign,sourceQuadCarriage=True,sourceClosedFrame=30,sourceDeployedFrame=45,sourceClosedOrigin=carriage_closed[side].tolist(),sourceDeployedOrigin=C.tolist(),sourceCarriageStart=.20,sourceCarriageEnd=.56)
 gimbal=joint(f'PDC_{side}_Gimbal',G,carriage,'pdc',sourceQuadAim=True,sourceMirror=sign,sourceEulerStart=euler_start,sourceEulerEnd=euler_end,sourceAimStart=.80,sourceAimEnd=1.,fixedRootArmorPieces=4)
 rail=mesh(f'PDC_{side}_OriginalSupport',support,set(range(len(support['faces']))),carriage,'holo.016')
 center=[];quadrants={i:[]for i in range(4)}
 for g in groups:
  if g['n']in(76,116,450,104,205)or(g['n']==24 and abs(g['center'][1]+61.7066)>2):
   k=int(g['center'][1]>-61.7066)*2+int(g['center'][2]>105.98);quadrants[k].append(g)
  else:center.append(g)
 casing=mesh(f'PDC_{side}_Casing',data,{f for g in center for f in g['faces']},gimbal,'holo.014')
 leaves=[]
 for k,groups_k in quadrants.items():
  assert sorted(g['n']for g in groups_k)==[24,76,104,116,205,450],(side,k,[(g['n'],g['center'])for g in groups_k])
  ys=-1 if k>=2 else 1;zs=-1 if k%2 else 1
  compact=[0,ys*.6,zs*.25]
  carrier=joint(f'PDC_{side}_Cradle_{k}',G,gimbal,'quad-cradle',quadCompact=True,compactVector=compact,compactStart=.03,compactEnd=.18,quadrant=k)
  arm=joint(f'PDC_{side}_Arm_{k}',G,carrier,'pdc',sourceFullTube=True,stowTravel=32.,slideVector=[-sign*32.,0,0],slideStart=.03,slideEnd=.18,quadrant=k)
  tube=mesh(f'PDC_{side}_ArmMesh_{k}',data,{f for g in groups_k if g['n']in(24,76,104)for f in g['faces']},arm,'holo.014')
  fork=mesh(f'PDC_{side}_FixedFork_{k}',data,{f for g in groups_k if g['n']==116 for f in g['faces']},carrier,'holo.014')
  root_armor=mesh(f'PDC_{side}_RootArmor_{k}',data,{f for g in groups_k if g['n']in(205,450)for f in g['faces']},carrier,'holo.014')
  leaves.append({'quadrant':k,'tubeVertices':len(tube.data.vertices),'rearCradleVertices':len(fork.data.vertices)+len(root_armor.data.vertices),'compactVector':compact,'tubeSlide':list(arm['slideVector'])})
 seats=[]
 for k,row in enumerate(sorted((r for r in petal_data if r['center'][0]*sign>0),key=lambda r:(r['center'][1],r['center'][2]))):
  p=np.array(row['center']);ys=1 if p[1]<-61.7066 else-1;zs=1 if p[2]<105.98 else-1
  shift,turn,seat=petal_seat(row,sign)
  petal=joint(f'PDC_{side}_HullPetal_{k}',p,asset,'pdc-hull-petal',sourceQuadPetal=True,compactVector=shift.tolist(),compactRotationWXYZ=list(turn),clearanceVector=(np.array(seat['receiverNormal'])*.85).tolist(),clearanceStart=.56,clearanceEnd=.78,compactStart=.03,compactEnd=.18)
  seats.append({'joint':petal.name,**seat,'compactVector':shift.tolist(),'compactRotationWXYZ':list(turn)})
  skin=mesh(f'PDC_{side}_HullPetal_{k}_Skin',hdata,set(row['faces']),petal,'holo.001');assert len(skin.data.vertices)==26
 report['quads'][side]={'sourceCarriageClosed':carriage_closed[side].tolist(),'sourceCarriageDeployed':C.tolist(),'sourceGunOrigin':G.tolist(),'completeGunVertices':sum(len(o.data.vertices)for o in s.objects if o.type=='MESH'and o.get('sourceObject')=='holo.014'and o.name.startswith(f'PDC_{side}_')),'sourceGunVertices':len(data['points']),'supportVertices':len(rail.data.vertices),'sourceSupportVertices':len(support['points']),'quadrants':leaves,'sourcePetals':4,'petalSeats':seats}
for side in['Port','Starboard']:
 o=bpy.data.objects[f'Flank_2_{side}_OriginalOuterRailBelt'];M=inv@o.matrix_world
 for f in o.data.polygons:
  ps=np.array([M@o.data.vertices[i].co for i in f.vertices]);source_id=min(o['sourceFaceIds'],key=lambda i:np.linalg.norm(ps.mean(0)-belt_sources[i]['points'].mean(0)))
  label=belt_sources[source_id]['material'];mat=paint(label)
  if mat.name not in [m.name for m in o.data.materials]:o.data.materials.append(mat)
  f.material_index=o.data.materials.find(mat.name);report['beltColors'].append({'mesh':o.name,'sourceFace':source_id,'material':mat.name})
 o['sourceMaterialRestored']=True;changed.add(o.name)
for name,h in before.items():
 if name not in removed and name not in changed:assert digest(bpy.data.objects[name])==h,('Unrelated geometry changed',name)
unchanged_joints=0
for name,(matrix,props)in joint_before.items():
 if name in removed:continue
 o=bpy.data.objects[name];assert np.array_equal(np.array(o.matrix_local),matrix)and plain(dict(o.items()))==props,('Unrelated articulation changed',name);unchanged_joints+=1
assert all(r['completeGunVertices']==r['sourceGunVertices']==5001 and r['supportVertices']==r['sourceSupportVertices']==1602 for r in report['quads'].values())
for o in s.objects:o.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
with source_path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==source_hash
report.update(unchangedOtherMeshes=sum(n not in removed and n not in changed for n in before),unchangedOtherJoints=unchanged_joints,removedObjects=sorted(removed),sourceEulerStart=euler_start,sourceEulerEnd=euler_end,animationClips=0)
(review/'source-restoration.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(root/'tests/fixtures/bridge-quad-source-v01131.json').write_text(json.dumps(fixture,indent=2),encoding='utf8')
asset['version']='0.11.31';bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.31.blend'),compress=True)
print('SOURCE_QUADS_RESTORED',[(side,r['completeGunVertices'],r['supportVertices'])for side,r in report['quads'].items()],report['beltColors'],flush=True)
