"""Independent source topology/UV restoration and rigid closure check."""
import bpy,json,hashlib,math,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix,Euler
root=Path(__file__).resolve().parents[1];review=root/'docs/review/v0.11.31'
def digest(o):
 h=hashlib.sha256();h.update(np.array([v.co for v in o.data.vertices],dtype=np.float32).tobytes())
 for f in o.data.polygons:
  h.update(np.array(f.vertices[:],dtype=np.int32).tobytes());h.update(o.data.materials[f.material_index].name.encode())
  if o.data.uv_layers.active:h.update(np.array([o.data.uv_layers.active.data[k].uv for k in f.loop_indices],dtype=np.float32).tobytes())
 return h.hexdigest()
def plain(v):
 if hasattr(v,'to_dict'):return{k:plain(x)for k,x in v.to_dict().items()}
 if hasattr(v,'to_list'):return[plain(x)for x in v.to_list()]
 if isinstance(v,dict):return{k:plain(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return[plain(x)for x in v]
 return v
fit=json.loads((review/'source-restoration.json').read_text());removed=set(fit['removedObjects'])
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.30.blend'))
unrelated={o.name:digest(o)for o in bpy.context.scene.objects if o.type=='MESH'and o.name not in removed and not o.get('fixedOuterHull')}
joints={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')and o.name not in removed}
belts={side:np.array([(bpy.data.objects['Odin_Asset'].matrix_world.inverted()@bpy.data.objects[f'Flank_2_{side}_OriginalOuterRailBelt'].matrix_world)@v.co for v in bpy.data.objects[f'Flank_2_{side}_OriginalOuterRailBelt'].data.vertices])for side in['Port','Starboard']}
source=root.parent/'Odin 建模/odin.blend'
with source.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
assert source_hash==fit['sourceSha256']
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.scene.frame_set(45);bpy.context.view_layer.update();expected={}
def store(o,M):
 p=np.array([M@v.co for v in o.data.vertices]);uv=o.data.uv_layers.active
 return {'points':p,'faces':[{v:(np.array(uv.data[li].uv)if uv else None)for v,li in zip(f.vertices,f.loop_indices)}for f in o.data.polygons],'materials':[o.data.materials[f.material_index].name for f in o.data.polygons]}
for inst in bpy.context.evaluated_depsgraph_get().object_instances:
 if inst.is_instance and inst.parent.name in('bridge turret','bridge turret.001')and inst.object.original.name in('holo.014','holo.016'):
  expected['Starboard'if inst.parent.name=='bridge turret'else'Port',inst.object.original.name]=store(inst.object.original,inst.matrix_world)
h=bpy.data.objects['holo.001'];hull=store(h,h.matrix_world)
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.31.blend'))
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
for name,value in unrelated.items():assert digest(bpy.data.objects[name])==value,('Unrelated source surface changed',name)
for name,(matrix,props)in joints.items():
 o=bpy.data.objects[name];assert np.array_equal(np.array(o.matrix_local),matrix)and plain(dict(o.items()))==props
rows=[];seen={};max_point=0.;max_uv=0.
for o in bpy.context.scene.objects:
 if o.type!='MESH'or not o.name.startswith('PDC_'):continue
 source_name=o.get('sourceObject');assert source_name in('holo.014','holo.016','holo.001'),o.name
 side='Port'if o.name.startswith('PDC_Port_')else'Starboard';data=hull if source_name=='holo.001'else expected[side,source_name]
 ids=list(o['sourceVertexIds']);faces=list(o['sourceFaceIds']);p=np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices]);err=float(np.max(abs(p-data['points'][ids])));max_point=max(max_point,err);uv_error=0.
 assert len(o.data.polygons)==len(faces)and err<.00005
 for i,f in zip(faces,o.data.polygons):
  assert {ids[v]for v in f.vertices}==set(data['faces'][i]),(o.name,i,'Topology changed')
  for v,li in zip(f.vertices,f.loop_indices):
   uv_error=max(uv_error,float(np.max(abs(np.array(o.data.uv_layers.active.data[li].uv)-data['faces'][i][ids[v]]))))
  material='Odin_Paint_Dark.001'if'dark'in data['materials'][i].lower()else'Odin_Paint_Light'
  assert o.data.materials[f.material_index].name==material
  if source_name!='holo.001':
   key=(side,source_name,i);assert key not in seen,('Duplicated source face',key);seen[key]=o.name
 max_uv=max(max_uv,uv_error);assert uv_error<.000001
 rows.append({'mesh':o.name,'sourceObject':source_name,'vertices':len(ids),'faces':len(faces),'pointError':err,'uvError':uv_error})
for key,data in expected.items():assert sum(k[:2]==key for k in seen)==len(data['faces']),('Original parts missing',key)
for side,p in belts.items():
 o=bpy.data.objects[f'Flank_2_{side}_OriginalOuterRailBelt'];now=np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices]);assert np.array_equal(now,p)
 assert sum(o.data.materials[f.material_index].name=='Odin_Paint_Dark.001'for f in o.data.polygons)==3
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
with(root/'assets/blender/odin_articulated_v0.11.31.blend').open('rb')as f:native_hash=hashlib.file_digest(f,'sha256').hexdigest()
report={'version':'0.11.31','nativeSha256':native_hash,'sourceSha256':source_hash,'sourceMeshParts':rows,'maxPointError':max_point,'maxUvError':max_uv,'unchangedOtherMeshes':len(unrelated),'unchangedOtherJoints':len(joints),'beltGeometryUnchanged':True,'completeSourceFaces':{side:{n:sum(k[:2]==(side,n)for k in seen)for n in['holo.014','holo.016']}for side in['Port','Starboard']},'originalSourceUnchanged':True,'animationClips':0}
(review/'source-geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('ORIGINAL_QUAD_GEOMETRY',len(rows),len(unrelated),len(joints),max_point,max_uv,flush=True)
