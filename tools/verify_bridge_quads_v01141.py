"""Verify metadata-only revision preserves all source meshes and static frames."""
import bpy, hashlib, json
import numpy as np
from pathlib import Path
root=Path(__file__).resolve().parents[1];review=root/'docs/review/v0.11.41'
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
def snapshot():
 return {o.name:{'matrix':np.array(o.matrix_local),'parent':o.parent.name if o.parent else None,
                 'props':plain(dict(o.items())),'mesh':digest(o)if o.type=='MESH'else None,
                 'world':np.array(o.matrix_world)}for o in bpy.context.scene.objects}
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.40.blend'));before=snapshot()
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.41.blend'));after=snapshot()
assert before.keys()==after.keys()
allowed={f'PDC_{s}_{r}_{i}'for s in ['Port','Starboard']for r in ['Cradle','CradleGuide','Arm']for i in range(4)}
changed=[];meshes=0;joints=0;unaffected=0
for name,old in before.items():
 now=after[name];assert np.array_equal(now['matrix'],old['matrix'])and np.array_equal(now['world'],old['world']),name
 assert now['parent']==old['parent'],name
 if old['mesh']is not None:assert now['mesh']==old['mesh'],name;meshes+=1
 if old['props'].get('staticJoint'):
  joints+=1
  if name in allowed:changed.append(name)
  else:assert now['props']==old['props'],name;unaffected+=1
for side in ['Port','Starboard']:
 for i in range(4):
  r=bpy.data.objects[f'PDC_{side}_Cradle_{i}'];p=bpy.data.objects[r['synchronizedPetal']]
  assert list(r['compactVector'])==[0.,1.95*(1 if i<2 else-1),.33*(1 if i%2==0 else-1)]
  assert np.linalg.norm(r['compactVector'])<np.linalg.norm(before[r.name]['props']['compactVector'])
  t=bpy.data.objects[f'PDC_{side}_Arm_{i}'];assert t['slideStart']>p['compactEnd']
  assert list(bpy.data.objects[f'PDC_{side}_CradleGuide_{i}']['compactVector'])==[0.,-1.35*(1 if i<2 else-1),0.]
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
source=root.parent/'Odin 建模/odin.blend'
with source.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
assert source_hash=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
with(root/'assets/blender/odin_articulated_v0.11.41.blend').open('rb')as f:native_hash=hashlib.file_digest(f,'sha256').hexdigest()
report={'version':'0.11.41','nativeSha256':native_hash,'sourceSha256':source_hash,'allMeshesUnchanged':meshes,
        'allStaticRestFramesUnchanged':joints,'unaffectedJointProperties':unaffected,'modifiedJointProperties':changed,
        'originalSourceUnchanged':True,'animationClips':0}
(review/'source-geometry.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('PRESERVED_QUAD_GEOMETRY',meshes,joints,unaffected,len(changed),flush=True)
