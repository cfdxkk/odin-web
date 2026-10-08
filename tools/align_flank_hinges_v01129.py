"""Align the original flank cover hinges and partition their inward lining.

Run on the immutable v0.11.28 editable asset. Work in the accepted closed
frame, then bake it back into static meshes about the corrected seam pivots.
All source lining surfaces are retained, with UV interpolation only where a
surface crosses a bank boundary. Barrel and carriage mechanics are untouched.
"""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector

root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset']
assert asset['version']=='0.11.28'
inv=asset.matrix_world.inverted()
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text())
original=json.loads((root/'docs/review/v0.11.26/source-fit.json').read_text())
review=root/'docs/review/v0.11.29';review.mkdir(parents=True,exist_ok=True)
source_path=root.parent/'Odin 建模/odin.blend'
source_hash=hashlib.sha256(source_path.read_bytes()).hexdigest()
assert source_hash=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
LIGHT='Odin_Paint_Light';RED='Odin_Turret_Interior_DeepRed'
BASE=1.7756;RAKE=-.007;WIDTH=2.88;BOUNDARIES=(-8.195,.325)
changed=set();report={'version':'0.11.29','sourceSha256':source_hash,'stations':{}}

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
def points(o):
 a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);m=np.array(inv@o.matrix_world)
 return a.reshape(-1,3)@m[:3,:3].T+m[:3,3]
def area(ps):
 return sum(np.linalg.norm(np.cross(ps[k]-ps[0],ps[k+1]-ps[0]))/2 for k in range(1,len(ps)-1))
def clip(vertices,bound,above):
 out=[]
 for a,b in zip(vertices,vertices[1:]+vertices[:1]):
  da=a[0][1]-bound;db=b[0][1]-bound;inside=da>=-1e-9 if above else da<=1e-9
  if inside:out.append(a)
  if (da<0<db)or(db<0<da):
   t=da/(da-db);p=a[0]+t*(b[0]-a[0]);p[1]=bound;out.append((p,a[1]+t*(b[1]-a[1])))
 return out
before={o.name:digest(o)for o in bpy.context.scene.objects if o.type=='MESH'}
mechanics={o.name:(np.array(o.matrix_local).copy(),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}

for number in(2,4):
 for side in('Starboard','Port'):
  name=f'SideBattery_{number}_{side}';C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes'])
  offset=np.array(bpy.data.objects[name+'_SourceCarriage']['closedOffsetModel']);rows=[]
  for physical,sign in(('Port',-1),('Starboard',1)):
   leaves=[bpy.data.objects[f'{name}_Shutter_{physical}_{i:02}']for i in range(3)]
   bucket=[[]for _ in leaves];incoming=[0]*3;source_count=0;source_area=0.;output_area=0.;crossing=0;ownership=[]
   for i,j in enumerate(leaves):
    o=j.children[0];H=np.array((inv@j.matrix_world).translation);R=np.array(Quaternion(Vector(j['hingeAxisModel']),math.radians(j['closedAngleDegrees'])).to_matrix());move=offset if i==0 else 0
    q=(H+(points(o)-H)@R.T+move-C)@Q
    count=next(r['originalVertices']for r in original['stations'][name]['leaves']if r['name']==j.name)
    uv=o.data.uv_layers.active;o.data.calc_loop_triangles();triangles={}
    for t in o.data.loop_triangles:triangles.setdefault(t.polygon_index,[]).append(t)
    for f in o.data.polygons:
     mat=o.data.materials[f.material_index].name;ps=[(q[k].copy(),np.array(uv.data[li].uv)if uv else np.zeros(2))for k,li in zip(f.vertices,f.loop_indices)]
     is_source=max(f.vertices)<count;is_lining=is_source and mat==RED
     if is_source:
      source_count+=1
      source_area+=sum(area(q[list(t.vertices)])for t in triangles[f.index])
     if not is_lining:
      # The fitted source skins contain collapsed contour vertices. Retain
      # their actual existing triangulation, rather than re-tessellating an
      # n-gon after welding and inadvertently opening a triangular hole.
      for t in triangles[f.index]:
       triangle=[(q[k].copy(),np.array(uv.data[li].uv)if uv else np.zeros(2))for k,li in zip(t.vertices,t.loops)]
       bucket[i].append((triangle,mat,is_source,i,f.index))
       if is_source:output_area+=area(q[list(t.vertices)])
      continue
     destinations=[]
     # Partition the source's actual render triangles. A few rolled rails
     # have non-planar quads, whose surfaces must not change upon splitting.
     for t in triangles[f.index]:
      triangle=[(q[k].copy(),np.array(uv.data[li].uv)if uv else np.zeros(2))for k,li in zip(t.vertices,t.loops)]
      for target,(lo,hi)in enumerate(((None,BOUNDARIES[0]),(BOUNDARIES[0],BOUNDARIES[1]),(BOUNDARIES[1],None))):
       piece=triangle
       if lo is not None:piece=clip(piece,lo,True)
       if hi is not None:piece=clip(piece,hi,False)
       if len(piece)<3 or area(np.array([p for p,u in piece]))<1e-8:continue
       bucket[target].append((piece,mat,True,i,f.index));output_area+=area(np.array([p for p,u in piece]));destinations.append(target)
       if target!=i:incoming[target]+=1
     destinations=sorted(set(destinations))
     if len(destinations)>1:crossing+=1
     if destinations!=[i]:ownership.append({'sourceLeaf':j.name,'sourceFace':f.index,'ownerBanks':destinations})
   assert abs(output_area-source_area)<.0005,(name,physical,source_area,output_area)
   for i,j in enumerate(leaves):
    o=j.children[0];move=offset if i==0 else np.zeros(3);b=sum(j['closedBankRange'])/2
    closed_hinge=np.array([sign*WIDTH,b,BASE+RAKE*b]);H=C+Q@closed_hinge-move;axis=Q@np.array([0,1,RAKE]);axis/=np.linalg.norm(axis)
    # Rear origin is local to the carriage; forward origins remain on hull.
    j.matrix_local=Matrix.Translation(Vector(H-C if i==0 else H));j['hingeAxisModel']=axis.tolist()
    j['hingeSeamLocal']=[sign*WIDTH,BASE,RAKE];j['alignedSeamHinge']=True
    j['hingeEdgeModel']=[(C+Q@np.array([sign*WIDTH,end,BASE+RAKE*end])-move).tolist()for end in j['closedBankRange']]
    bpy.context.view_layer.update();R=np.array(Quaternion(Vector(axis),math.radians(j['closedAngleDegrees'])).to_matrix())
    verts=[];faces=[];uvs=[];labels=[];provenance=[];lookup={}
    for ps,mat,src,old_bank,old_face in bucket[i]:
     ids=[];face_uv=[]
     for p,u in ps:
      key=tuple(np.round(p,7));idx=lookup.get(key)
      if idx is None:idx=len(verts);lookup[key]=idx;verts.append((C+Q@p-H-move)@R)
      ids.append(idx);face_uv.append(u)
     if len(set(ids))<3:continue
     faces.append(ids);uvs.append(face_uv);labels.append(mat);provenance.append((int(src),old_bank,old_face))
    mesh=bpy.data.meshes.new(o.data.name+'_SeamFit');mesh.from_pydata(verts,[],faces);mesh.update()
    for mat in o.data.materials:mesh.materials.append(mat)
    layer=mesh.uv_layers.new(name=uv.name if uv else'UVMap')
    source_layer=mesh.attributes.new('originalSourceFace','INT','FACE');bank_layer=mesh.attributes.new('originalSourceBank','INT','FACE')
    for f,us,mat,(src,bank,face)in zip(mesh.polygons,uvs,labels,provenance):
     f.material_index=mesh.materials.find(mat)
     for li,u in zip(f.loop_indices,us):layer.data[li].uv=u
     source_layer.data[f.index].value=face+1 if src else 0;bank_layer.data[f.index].value=bank
    old=o.data;o.data=mesh;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_local=Matrix.Identity(4)
    if not old.users:bpy.data.meshes.remove(old)
    o['liningPartitionedAtSeams']=True;o['sourceGratesRetained']=True;changed.add(o.name)
    rows.append({'joint':j.name,'mesh':o.name,'closedHingeLocal':closed_hinge.tolist(),'hingeAxisLocal':(axis@Q).tolist(),'bankRange':list(j['closedBankRange']),'reassignedLiningPieces':incoming[i],'sourceFaces':sum(p[0]for p in provenance)})
   report.setdefault('liningPartitions',[]).append({'station':name,'physicalSide':physical,'originalPolygons':source_count,'crossingPolygons':crossing,'sourceArea':source_area,'retainedArea':output_area,'ownershipChanges':ownership})
  cap=bpy.data.objects[name+'_FrontCap'];cap['holdRaisedAfterAdvance']=True
  report['stations'][name]={'leaves':rows,'cap':cap.name,'capHoldRaised':True,'hingeRailLocal':[WIDTH,BASE,RAKE]}

# Align the original fixed outer cheek upper contour and its thin returns
# with the common closed hinge rail. Only the local external lip is changed;
# the original floor, bearings, inward struts and adjoining belt stay intact.
fixed=[]
for mesh_name in('holo.001','Flank24_OriginalFixedHull'):
 o=bpy.data.objects[mesh_name];p=points(o);mi=np.array((inv@o.matrix_world).inverted());edits={}
 inner_vertices={k for f in o.data.polygons if o.data.materials[f.material_index].name==RED for k in f.vertices}
 for name in report['stations']:
  C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);q=(p-C)@Q
  for k in np.where((abs(q[:,0])>=2.45)&(abs(q[:,0])<=2.9001)&(q[:,1]>-17.44)&(q[:,1]<9.48)&(q[:,2]>1.4)&(q[:,2]<2.5))[0]:
   x,b,n=q[k];target=BASE+RAKE*b-.012
   if n<target-.025:continue
   # Outer and inward-return rows preserve their existing .08 thickness.
   x=math.copysign(WIDTH-.08 if k in inner_vertices else WIDTH,x)
   new=np.array([x,b,target]);edits[int(k)]=C+Q@new
  fixed.append({'mesh':mesh_name,'station':name,'editedVertices':sum(1 for k in edits if -17.44<q[k,1]<9.48 and abs(q[k,0])<2.901)})
 for k,p in edits.items():o.data.vertices[k].co=Vector((mi@np.r_[p,1])[:3])
 if edits:o.data.update();changed.add(o.name)
report['fixedLipFit']=fixed
bpy.context.view_layer.update()
for name,h in before.items():
 if name not in changed:assert digest(bpy.data.objects[name])==h,('Unrelated mesh changed',name)
for name,(m,data)in mechanics.items():
 if '_Shutter_'in name and name.startswith(('SideBattery_2_','SideBattery_4_')):continue
 assert np.array_equal(np.array(bpy.data.objects[name].matrix_local),m),('Unrelated joint moved',name)
 now=plain(dict(bpy.data.objects[name].items()));now.pop('holdRaisedAfterAdvance',None)
 assert data==now,('Unrelated mechanics changed',name)
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
assert hashlib.sha256(source_path.read_bytes()).hexdigest()==source_hash
report.update(changedMeshes=sorted(changed),unchangedOtherMeshes=len(before)-len(changed),unchangedBarrelsAndCarriages=True,animationClips=0)
(review/'seam-fit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
asset['version']='0.11.29';bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.29.blend'),compress=True)
print('ALIGNED_SEAM_HINGES',len(rows)*4,len(changed),[r['crossingPolygons']for r in report['liningPartitions']],flush=True)
