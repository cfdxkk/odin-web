"""Check full hull thickness against independent original-source sections."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
root=Path(__file__).resolve().parents[1];review=root/'docs/review/v0.11.37'
fixture=json.loads((root/'tests/fixtures/aft-twin-full-shell-v01137.json').read_text())
names={f'Defense_{i:02}_NotchGate_Skin'for i in range(5,9)}
labels=['outer','middle','middle2','inner']

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

bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.36.blend'))
meshes={o.name:(digest(o),np.array(o.matrix_local))for o in bpy.context.scene.objects if o.type=='MESH'and o.name not in names}
joints={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}
old_top={}
for station in range(5,9):
 o=bpy.data.objects[f'Defense_{station:02}_NotchGate_Skin'];nt,ns=o['receiverGridColumns'],o['receiverGridRows']
 p=cloud(o).reshape(2,ns,nt,3);old_top[station]=p[0,0]-p[1,0]
source=root.parent/'Odin 建模/odin.blend'
with source.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
assert source_hash==fixture['sourceSha256']
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.scene.frame_set(fixture['sourceGeometryFrame'])
h=bpy.data.objects[fixture['sourceObject']];sp=np.array([h.matrix_world@v.co for v in h.data.vertices]);source_ids=[]
source_edges={tuple(sorted(e.vertices[:]))for e in h.data.edges};source_roof_edges=0
for row in fixture['apertures']:
 for sign in[1,-1]:
  original_ids={}
  for key,p in row['points'].items():
   if int(key)<0:continue
   p=np.array(p)*[sign,1,1];dist=np.linalg.norm(sp-p,axis=1);i=int(dist.argmin())
   assert dist[i]<.000001,(row['station'],p,dist[i]);source_ids.append(i);original_ids[int(key)]=i
  for key in['sourceRoofFore','sourceRoofAft']:
   path=row[key]
   for a,b in zip(path,path[1:]):
    assert tuple(sorted([original_ids[a],original_ids[b]]))in source_edges,('Source roof edge missing',row['station'],key,a,b)
    source_roof_edges+=1
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.37.blend'))
for name,(value,M)in meshes.items():
 o=bpy.data.objects[name];assert digest(o)==value and np.array_equal(np.array(o.matrix_local),M),('Unrelated mesh changed',name)
for name,(M,data)in joints.items():
 o=bpy.data.objects[name];assert np.array_equal(np.array(o.matrix_local),M)and plain(dict(o.items()))==data,('Joint or motion changed',name)
rows=[]
for row in fixture['apertures']:
 points={int(i):np.array(p)for i,p in row['points'].items()}
 ts=np.array([(points[row['outerBottom'][0]][1]-points[i][1])/
       (points[row['outerBottom'][0]][1]-points[row['outerBottom'][-1]][1])for i in row['outerBottom']])
 for station,sign in[(row['station'],1),(row['station']+2,-1)]:
  o=bpy.data.objects[f'Defense_{station:02}_NotchGate_Skin'];p=cloud(o)*[sign,1,1]
  edges={}
  for f in o.data.polygons:
   ids=list(f.vertices)
   for a,b in zip(ids,ids[1:]+ids[:1]):
    edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
  assert set(edges.values())=={2},('Gate shell must be watertight',station)
  nt,ns=o['receiverGridColumns'],o['receiverGridRows'];count=nt*ns;nb=2*nt+2*ns-4
  border=[*range(nt),*[j*nt+nt-1 for j in range(1,ns)],
          *range(count-2,count-nt-1,-1),*[j*nt for j in range(ns-2,0,-1)]]
  grids=p[:2*count].reshape(2,ns,nt,3)
  rings={'outer':grids[0].reshape(-1,3)[border],'inner':grids[1].reshape(-1,3)[border],
         'middle':p[2*count:2*count+nb],'middle2':p[2*count+nb:]}
  layer_contours={}
  for label,ring in rings.items():
   by_vertex={j:ring[k]for k,j in enumerate(border)}
   layer_contours[label+'Fore']=np.array([by_vertex[j*nt]for j in range(ns)])
   layer_contours[label+'Aft']=np.array([by_vertex[j*nt+nt-1]for j in range(ns)])
   layer_contours[label+'Bottom']=np.array([by_vertex[(ns-1)*nt+j]for j in range(nt)])
   layer_contours[label+'Top']=ring[:nt]
  errors={}
  for label in labels:
   for key in['Fore','Aft','Bottom']:
    name=label+key;c=layer_contours[name];expected=np.array([points[i]for i in row[name]])
    shift=np.array([0,-.008 if key=='Fore'else.008,0]) if key!='Bottom'else np.array([0,0,0])
    if key=='Bottom':expected[:,1]+=.008*(2*ts-1)
    else:expected+=shift
    errors[name]=max(gaps(expected,c))
  assert max(errors.values())<.00003,(station,errors)
  roof_errors={}
  for key in['Fore','Aft']:
   roof=np.array([points[i]for i in row['sourceRoof'+key]])
   roof[:,1]+=-.008 if key=='Fore'else.008
   # Bidirectional boundary check: both the entire generated roof edge
   # and dense samples of the true source edge must lie on each other.
   contour=np.array([layer_contours[label+'Top'][0 if key=='Fore'else-1]for label in labels])
   samples=np.concatenate([np.linspace(a,b,25)for a,b in zip(roof,roof[1:])])
   roof_errors[key]=max(max(gaps(contour,roof)),max(gaps(samples,contour)))
  assert max(roof_errors.values())<.00003,(station,roof_errors)
  # Compare complete upper cross-section vectors at every longitudinal
  # sample, including intermediate roof layers. A thin outer-shell-only
  # gate (v36) misses these vectors by over half a source unit.
  section_errors=[]
  for label in labels[1:]:
   f=points[row['outerFore'][0]]-points[row[label+'Fore'][0]]
   a=points[row['outerAft'][0]]-points[row[label+'Aft'][0]]
   expected=(1-ts[:,None])*f+ts[:,None]*a
   actual=layer_contours['outerTop']-layer_contours[label+'Top']
   section_errors.append(float(np.linalg.norm(actual-expected,axis=1).max()))
  full_top=layer_contours['outerTop']-layer_contours['innerTop']
  widths=np.linalg.norm(full_top,axis=1)
  assert min(widths)>1.0 and max(section_errors)<.00003,(station,widths,section_errors)
  expected_bottom=np.array([points[a]-points[b]for a,b in zip(row['outerBottom'],row['innerBottom'])])
  lower_error=float(np.linalg.norm(grids[0,-1]-grids[1,-1]-expected_bottom,axis=1).max())
  assert lower_error<.00003
  control_error=float(np.linalg.norm(old_top[station]*[sign,1,1]-full_top,axis=1).min())
  assert control_error>.50,(station,control_error)
  rows.append({'station':station,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),
    'sourceShellLayers':4,'sourceFloorSections':nt,'fullReceiverContourMaxErrors':errors,
    'upperShellSectionVectorError':max(section_errors),'lowerShellSectionVectorError':lower_error,
    'fullRoofBoundaryErrors':roof_errors,
    'upperRimSectionLengths':widths.tolist(),'oldFirstLayerControlMinThicknessError':control_error,
    'watertightShell':True})
for a,b in[(5,7),(6,8)]:
 pa=cloud(bpy.data.objects[f'Defense_{a:02}_NotchGate_Skin'])*[-1,1,1]
 pb=cloud(bpy.data.objects[f'Defense_{b:02}_NotchGate_Skin'])
 assert np.max(abs(pa-pb))<.00003
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
with(root/'assets/blender/odin_articulated_v0.11.37.blend').open('rb')as f:native_hash=hashlib.file_digest(f,'sha256').hexdigest()
report={'version':'0.11.37','nativeSha256':native_hash,'sourceSha256':source_hash,'sourceReceiverVerticesVerified':len(source_ids),
 'sourceRoofEdgesVerified':source_roof_edges,
 'covers':rows,'unchangedOtherMeshes':len(meshes),'unchangedJointTransforms':len(joints),'unchangedJointMotionMetadata':len(joints),
 'fixedHullUnchanged':True,'originalSourceUnchanged':True,'animationClips':0}
(review/'source-geometry.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('AFT_FULL_THICKNESS_VERIFIED',len(source_ids),len(meshes),len(joints),[(r['station'],r['upperShellSectionVectorError'],r['oldFirstLayerControlMinThicknessError'])for r in rows],flush=True)
