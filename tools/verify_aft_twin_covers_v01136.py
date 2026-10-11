"""Verify complete receiver contours and tapered sections against odin.blend."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
root=Path(__file__).resolve().parents[1];review=root/'docs/review/v0.11.36'
fixture=json.loads((root/'tests/fixtures/aft-twin-receiver-profiles-v01136.json').read_text())
names={f'Defense_{i:02}_NotchGate_Skin'for i in range(5,9)}

def plain(v):
 if hasattr(v,'to_dict'):return{k:plain(x)for k,x in v.to_dict().items()}
 if hasattr(v,'to_list'):return[plain(x)for x in v.to_list()]
 if isinstance(v,dict):return{k:plain(x)for k,x in v.items()}
 if isinstance(v,(tuple,list)):return[plain(x)for x in v]
 return v

def digest(o):
 h=hashlib.sha256();h.update(np.array([v.co for v in o.data.vertices],dtype=np.float32).tobytes())
 for f in o.data.polygons:
  h.update(np.array(f.vertices[:],dtype=np.int32).tobytes());h.update(o.data.materials[f.material_index].name.encode())
  if o.data.uv_layers.active:h.update(np.array([o.data.uv_layers.active.data[k].uv for k in f.loop_indices],dtype=np.float32).tobytes())
 return h.hexdigest()

def cloud(o):
 a=bpy.data.objects['Odin_Asset'];return np.array([(a.matrix_world.inverted()@o.matrix_world)@v.co for v in o.data.vertices])

def gaps(points,contour):
 a,b=contour[:-1],contour[1:];v=b-a
 result=[]
 for p in points:
  t=np.clip(np.einsum('ij,ij->i',p-a,v)/np.einsum('ij,ij->i',v,v),0,1)
  result.append(float(np.linalg.norm(p-a-v*t[:,None],axis=1).min()))
 return result

bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.35.blend'))
meshes={o.name:(digest(o),np.array(o.matrix_local))for o in bpy.context.scene.objects if o.type=='MESH'and o.name not in names}
joints={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}
old={i:cloud(bpy.data.objects[f'Defense_{i:02}_NotchGate_Skin'])for i in range(5,9)}
source=root.parent/'Odin 建模/odin.blend'
with source.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
assert source_hash==fixture['sourceSha256']
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.scene.frame_set(fixture['sourceGeometryFrame'])
h=bpy.data.objects[fixture['sourceObject']];sp=np.array([h.matrix_world@v.co for v in h.data.vertices]);source_ids=[]
for row in fixture['apertures']:
 for sign in[1,-1]:
  for p in row['points'].values():
   p=np.array(p)*[sign,1,1];dist=np.linalg.norm(sp-p,axis=1);i=int(dist.argmin())
   assert dist[i]<.000001,(row['station'],p,dist[i]);source_ids.append(i)
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.36.blend'))
for name,(value,M)in meshes.items():
 o=bpy.data.objects[name];assert digest(o)==value and np.array_equal(np.array(o.matrix_local),M),('Unrelated mesh changed',name)
for name,(M,data)in joints.items():
 o=bpy.data.objects[name];assert np.array_equal(np.array(o.matrix_local),M)and plain(dict(o.items()))==data,('Joint or motion changed',name)
rows=[]
for row in fixture['apertures']:
 points={int(i):np.array(p)for i,p in row['points'].items()}
 for station,sign in[(row['station'],1),(row['station']+2,-1)]:
  o=bpy.data.objects[f'Defense_{station:02}_NotchGate_Skin'];p=cloud(o)*[sign,1,1]
  edges={}
  for f in o.data.polygons:
   ids=list(f.vertices)
   for a,b in zip(ids,ids[1:]+ids[:1]):
    edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
  assert set(edges.values())=={2},('Gate shell must be watertight',station)
  nt,ns=o['receiverGridColumns'],o['receiverGridRows'];p=p.reshape(2,ns,nt,3)
  contours={'outerFore':p[0,:,0], 'outerAft':p[0,:,-1], 'outerBottom':p[0,-1],
    'innerFore':p[1,:,0], 'innerAft':p[1,:,-1], 'innerBottom':p[1,-1]}
  errors={key:max(gaps(np.array([points[i]for i in row[key]]),c))for key,c in contours.items()}
  assert max(errors.values())<.00803,(station,errors)
  expected=np.array([points[a]-points[b]for a,b in zip(row['outerBottom'],row['innerBottom'])])
  section_error=float(np.linalg.norm((p[0,-1]-p[1,-1])-expected,axis=1).max())
  assert section_error<.00003,(station,section_error)
  # Source lower returns run nearly horizontally inward, unlike the old
  # normal extrusion which put their inner edges below the fixed hull lip.
  assert np.min(p[0,-1,:,0]-p[1,-1,:,0])>.8
  if station in(6,8):assert np.min(p[1,-1,:,2]-p[0,-1,:,2])>.15
  for key in ['outerFore','outerAft','innerFore','innerAft']:
   shift=np.array([0,-.008 if 'Fore'in key else.008,0])
   assert max(gaps(np.array([points[i]+shift for i in row[key]]),contours[key]))<.00003
  q=old[station]*[sign,1,1]
  old_errors={key:max(gaps(np.array([points[i]for i in row[key]]),c))for key,c in
     {'outerFore':q[[0,3]],'outerAft':q[[1,2]],'innerFore':q[[4,7]],'innerAft':q[[5,6]],
      'outerBottom':q[[3,2]],'innerBottom':q[[7,6]]}.items()}
  # Port old vertex order is reversed; compare its whole perimeter instead.
  if sign<0:
   old_errors={key:max(gaps(np.array([points[i]for i in row[key]]),np.concatenate((q[:4]if key.startswith('outer')else q[4:],q[:1]if key.startswith('outer')else q[4:5]))))for key in contours}
  assert old_errors['innerBottom']>.25 and old_errors['outerBottom']>.1
  rows.append({'station':station,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),
    'receiverContourMaxErrors':errors,'lowerShellSectionVectorError':section_error,
    'watertightShell':True,'sourceFloorSections':nt,'maxEndContourErrorAfterClearance':max(
      max(gaps(np.array([points[i]+[0,-.008 if 'Fore'in k else.008,0]for i in row[k]]),contours[k]))for k in['outerFore','outerAft','innerFore','innerAft']),
    'oldCoverControlErrors':old_errors,'lowerReturnWidths':(p[0,-1,:,0]-p[1,-1,:,0]).tolist()})
for a,b in[(5,7),(6,8)]:
 pa=cloud(bpy.data.objects[f'Defense_{a:02}_NotchGate_Skin'])*[-1,1,1]
 pb=cloud(bpy.data.objects[f'Defense_{b:02}_NotchGate_Skin'])
 assert np.max(abs(pa-pb))<.00003
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
with(root/'assets/blender/odin_articulated_v0.11.36.blend').open('rb')as f:native_hash=hashlib.file_digest(f,'sha256').hexdigest()
report={'version':'0.11.36','nativeSha256':native_hash,'sourceSha256':source_hash,'sourceReceiverVerticesVerified':len(source_ids),
 'covers':rows,'unchangedOtherMeshes':len(meshes),'unchangedJointTransforms':len(joints),'unchangedJointMotionMetadata':len(joints),
 'fixedHullUnchanged':True,'originalSourceUnchanged':True,'animationClips':0}
(review/'source-geometry.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('AFT_RECEIVER_VERIFIED',len(source_ids),len(meshes),len(joints),[(r['station'],max(r['receiverContourMaxErrors'].values()),r['oldCoverControlErrors']['innerBottom'])for r in rows],flush=True)
