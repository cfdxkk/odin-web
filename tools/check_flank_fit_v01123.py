"""Check the saved six-bay fit and exact preservation of every other mesh/rig."""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Quaternion,Vector

root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset']
assert asset['version']=='0.11.23'
inv=asset.matrix_world.inverted()
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text())
fit=json.loads((root/'docs/review/v0.11.23/geometry-fit.json').read_text())
report={'stations':{}}
def points(o):return np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])
def closed(o):
 j=o.parent;H=np.array((inv@j.matrix_world).translation)
 R=np.array(Quaternion(Vector(j['hingeAxisModel']),math.radians(j['closedAngleDegrees'])).to_matrix())
 return H+(points(o)-H)@R.T

for name in list(fit['axial'])+list(fit['flank']):
 C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes'])
 if name=='Axial_Keel':C+=np.array(bpy.data.objects[name+'_Mount']['fixedAssemblyOffsetModel'])
 cap=bpy.data.objects[name+'_FrontCap'];skin=bpy.data.objects[name+'_FrontCap_Skin']
 profile=(points(skin)+np.array(cap['slideVector'])+np.array(cap['settleVector'])-C)@Q
 z0,n0,rake=cap['closedCrownLineLocal'];line=lambda y:n0+rake*(y-z0)
 adjacent=0.;crown=0.;seam=0.;topology=[]
 for side,sgn in [('Port',-1),('Starboard',1)]:
  previous=None
  for i in range(3):
   joint=bpy.data.objects[f'{name}_Shutter_{side}_{i:02d}']
   backing=bpy.data.objects[joint.name+'_FittedBacking'];grate=bpy.data.objects[joint.name+'_Skin']
   assert len(joint.children)==2 and len(backing.data.vertices)==12 and len(backing.data.polygons)==10
   q=(closed(backing)-C)@Q;topology.append([len(grate.data.vertices),len(grate.data.polygons)])
   assert joint['openingTravelDegrees']==95.
   for k in [1,2,4,5]:crown=max(crown,abs(float(q[k,2]-line(q[k,1]))))
   if previous is not None:adjacent=max(adjacent,float(np.max(abs(previous[3:6]-q[:3]))))
   previous=q
  if name.startswith('Axial_'):indices=[0,8,4] if sgn==1 else [28,36,32]
  else:indices=[31,20,19] if sgn==1 else [10,3,0]
  rear=profile[indices];seam=max(seam,float(np.max(abs(rear[[2,1,0]][:,0]-previous[3:6,0]))),abs(float(rear[0,1]-previous[5,1]-.02)),abs(float(rear[0,2]-line(rear[0,1]))))
 assert max(crown,adjacent,seam)<.0001,(name,crown,adjacent,seam)
 assert cap['settleEnd']<cap['slideStart'] and np.linalg.norm(np.array(cap['settleVector']))>.59
 assert any('Red' in m.name or 'Primer' in m.name or 'Reinforcement' in m.name for m in skin.data.materials)
 outer_ids={0,8,4,3,9,5,28,36,32,31,37,33} if name.startswith('Axial_') else {0,1,2,3,10,11,18,19,20,21,30,31}
 outer_faces=[f for f in skin.data.polygons if set(f.vertices)<=outer_ids]
 assert outer_faces and all('Reinforcement' not in skin.data.materials[f.material_index].name for f in outer_faces),('Exterior cap paint changed',name)
 assert any('Reinforcement' in skin.data.materials[f.material_index].name for f in skin.data.polygons),('No red inward cap faces',name)
 if name.startswith('SideBattery_'):
  lip=bpy.data.objects[name+'_FixedSlotLips'];assert lip.parent.name=='Odin_Asset' and lip['stationaryHullLip']
  assert lip['hingeClearanceModel']==.08
 report['stations'][name]={'crownLineMaximumError':crown,'adjacentFullWidthEdgeMaximumError':adjacent,'noseRearMaximumError':seam,'receiverSeam':.02,'shutterSweep':95,'noseSourceTopology':[len(skin.data.vertices),len(skin.data.polygons)],'leafSourceTopology':topology}

def digest(o):
 h=hashlib.sha256();co=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',co);h.update(co.tobytes())
 for f in o.data.polygons:
  h.update(np.array(tuple(f.vertices),dtype=np.int32).tobytes());h.update(o.data.materials[f.material_index].name.encode())
 return h.hexdigest()
def value(v):
 if hasattr(v,'to_dict'):return {k:value(v[k]) for k in v.keys()}
 if hasattr(v,'to_list'):return [value(a) for a in v.to_list()]
 if isinstance(v,(list,tuple)):return [value(a) for a in v]
 return v
def snapshot():
 return {o.name:{'matrix':np.array(o.matrix_local).copy(),'parent':o.parent.name if o.parent else None,'hash':digest(o) if o.type=='MESH' else None,'joint':bool(o.get('staticJoint')),'data':{k:value(v) for k,v in o.items()}} for o in bpy.context.scene.objects}

after=snapshot();bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.22.blend'));before=snapshot()
changed=set(fit['changedMeshes']);moved=set(fit['refittedContactJoints'])
count=0;unchanged_joints=0;unchanged_guns=0
for name,old in before.items():
 if name not in after:
  assert any(name.startswith(f'SideBattery_{i}_{s}_Shutter_') for i in [2,4] for s in ['Port','Starboard']),name
  continue
 new=after[name]
 if old['hash'] is not None and name not in changed:assert new['hash']==old['hash'],name;count+=1
 if old['joint'] and name not in moved:
  assert np.array_equal(old['matrix'],new['matrix']) and old['parent']==new['parent'],name
  unchanged_joints+=1
 if old['data'].get('singleBattery') or old['data'].get('system') in ['main','main-telescope','main-bore-carriage','defense','pdc','bridge-quad']:
  assert old['data']==new['data'] and np.array_equal(old['matrix'],new['matrix']),('Gun/action changed',name)
  unchanged_guns+=1
assert count==fit['unchangedMeshes'] and unchanged_joints==163
report.update(unchangedMeshMaterialHashes=count,unchangedJointMatrices=unchanged_joints,unchangedGunMetadata=unchanged_guns)
# The user saved the reference animation file again before this revision.
# Check its current read-only input hash, rather than v0.11.22's older hash.
source_files=[(root.parent/'Odin 建模/odin.blend','9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'),(Path('D:/Odin/blender_test/odin_with_anime.blend'),'6cccc632d7939e028722cfe858cb4946935fbe93db3a0f85d4f0be699b4b2e95')]
report['originalSourceHashes']={}
for path,expected in source_files:
 actual=hashlib.sha256(path.read_bytes()).hexdigest();assert actual==expected,str(path)
 report['originalSourceHashes'][path.name]=actual
(root/'docs/review/v0.11.23/geometry-check.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('SAVED_FIT_VERIFIED',json.dumps(report),flush=True)
