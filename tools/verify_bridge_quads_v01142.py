"""Bind the narrow packing change to unchanged v0.11.40 native geometry."""
import bpy, hashlib, json
import numpy as np
from pathlib import Path
root=Path(__file__).resolve().parents[1];review=root/'docs/review/v0.11.42'
helper=(root/'tools/verify_bridge_quads_v01141.py').read_text().split('bpy.ops.wm.open_mainfile')[0]
exec(compile(helper,str(root/'tools/verify_bridge_quads_v01141.py'),'exec'))
review=root/'docs/review/v0.11.42'
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.40.blend'));before=snapshot()
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.42.blend'));after=snapshot()
assert before.keys()==after.keys()
allowed={f'PDC_{s}_{r}_{i}'for s in ['Port','Starboard']for r in ['Cradle','CradleGuide']for i in range(4)}
changed=[];meshes=0;joints=0;unaffected=0
for name,old in before.items():
 now=after[name]
 assert np.array_equal(now['matrix'],old['matrix'])and np.array_equal(now['world'],old['world']),name
 assert now['parent']==old['parent'],name
 if old['mesh']is not None:assert now['mesh']==old['mesh'],name;meshes+=1
 if old['props'].get('staticJoint'):
  joints+=1
  if name in allowed:
   assert {k:v for k,v in now['props'].items()if k not in ['compactVector','compactReleaseRelief','compactReliefStart','compactReliefEnd']}=={k:v for k,v in old['props'].items()if k!='compactVector'},name
   changed.append(name)
  else:assert now['props']==old['props'],name;unaffected+=1
for side in ['Port','Starboard']:
 for i in range(4):
  r=bpy.data.objects[f'PDC_{side}_Cradle_{i}'];g=bpy.data.objects[f'PDC_{side}_CradleGuide_{i}']
  assert np.linalg.norm(r['compactVector'])<np.linalg.norm(before[r.name]['props']['compactVector'])
  for o in [r,g]:assert o['compactReleaseRelief']==.60 and o['compactReliefStart']==.12 and o['compactReliefEnd']==.15
  t=bpy.data.objects[f'PDC_{side}_Arm_{i}'];assert t['slideStart']==.03 and t['slideEnd']==.18
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
source=root.parent/'Odin 建模/odin.blend'
with source.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
assert source_hash=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
with(root/'assets/blender/odin_articulated_v0.11.42.blend').open('rb')as f:native_hash=hashlib.file_digest(f,'sha256').hexdigest()
report={'version':'0.11.42','baseline':'0.11.40','nativeSha256':native_hash,'sourceSha256':source_hash,
 'allMeshesUnchanged':meshes,'allStaticRestFramesUnchanged':joints,'unaffectedJointProperties':unaffected,
 'modifiedJointProperties':changed,'allArmorGeometryAndMetadataUnchanged':True,'axialMotionMetadataUnchanged':True,
 'originalSourceUnchanged':True,'animationClips':0}
(review/'source-geometry.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('PRESERVED_QUAD_GEOMETRY',meshes,joints,unaffected,len(changed),flush=True)
