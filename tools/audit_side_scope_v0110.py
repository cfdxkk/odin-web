"""Compare unaffected geometry and static joints with the preceding asset."""
import bpy,json,hashlib,sys,numpy as np
from pathlib import Path
from mathutils.kdtree import KDTree
R=Path(__file__).resolve().parents[1];out=R/'work/v0110-review';out.mkdir(exist_ok=True)
prefixes=tuple(f'SideBattery_{i}_{side}'for i in [1,3]for side in ['Port','Starboard'])
def in_scope(o):
 if o.name in ['holo.001','holo.024','Odin_Asset']:return True
 while o:
  if o.name.startswith(prefixes):return True
  o=o.parent
 return False
state={}
for o in bpy.context.scene.objects:
 if in_scope(o):continue
 digest=hashlib.sha256()
 digest.update(np.array(o.matrix_local,dtype=np.float64).tobytes())
 if o.type=='MESH':
  digest.update(np.array([v.co[:]for v in o.data.vertices],dtype=np.float32).tobytes())
  digest.update(str([tuple(f.vertices)for f in o.data.polygons]).encode())
  digest.update(str([f.material_index for f in o.data.polygons]).encode())
  digest.update(str([m.name for m in o.data.materials]).encode())
 if o.get('staticJoint'):digest.update(json.dumps(dict(o.items()),sort_keys=True,default=lambda v:list(v)).encode())
 state[o.name]=digest.hexdigest()
A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted()
def source_mesh(objects):
 vertices=[];faces=0
 for o in objects:
  M=inv@o.matrix_world;vertices.extend([list(M@v.co)for v in o.data.vertices]);faces+=len(o.data.polygons)
 return {'vertices':vertices,'faces':faces}
if '--snapshot'in sys.argv:
 (out/'scope-before.json').write_text(json.dumps(state));print('SNAPSHOT',len(state))
 for source in ['holo.001','holo.024']:
  (out/(source+'-before.json')).write_text(json.dumps(source_mesh([bpy.data.objects[source]])))
else:
 before=json.loads((out/'scope-before.json').read_text());changed=[n for n in before if before[n]!=state.get(n)]
 transfers={}
 for source,suffixes in [('holo.001',('_Carriage_Trough','_Carriage_Bearings')),('holo.024',('_Carriage_OuterPedestal',))]:
  prior=json.loads((out/(source+'-before.json')).read_text());objects=[bpy.data.objects[source]]+[o for o in bpy.context.scene.objects if o.name.startswith(prefixes)and o.name.endswith(suffixes)]
  after=source_mesh(objects);kd=KDTree(len(prior['vertices']))
  for i,p in enumerate(prior['vertices']):kd.insert(p,i)
  kd.balance();errors=[kd.find(p)[2]for p in after['vertices']]
  transfers[source]={'sourceFaces':prior['faces'],'retainedFaces':after['faces'],'maximumRestVertexError':max(errors)}
  assert after['faces']==prior['faces'] and max(errors)<.001,transfers[source]
 result={'unaffectedObjects':len(before),'changedOutsideScope':changed,'originalGeometryTransfers':transfers,'originalSha256':hashlib.sha256((R.parent/'Odin 建模/odin.blend').read_bytes()).hexdigest()}
 (out/'scope-audit.json').write_text(json.dumps(result,indent=2));print(result)
 assert not changed,result
 assert result['originalSha256']=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
