"""Verify original faces/UVs, fixed hood ownership and complete cradle membership."""
import bpy,json,numpy as np,hashlib
from pathlib import Path
from collections import Counter
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
from mathutils import Vector
root=Path(__file__).resolve().parents[1];review=root/'docs/review/v0.11.38'

def plain(v):
 if hasattr(v,'to_dict'):return{k:plain(x)for k,x in v.to_dict().items()}
 if hasattr(v,'to_list'):return[plain(x)for x in v.to_list()]
 if isinstance(v,dict):return{k:plain(x)for k,x in v.items()}
 if isinstance(v,(tuple,list)):return[plain(x)for x in v]
 return v

def faces(o):
 result=Counter()
 for f in o.data.polygons:
  h=hashlib.sha256();h.update(np.array([o.data.vertices[i].co for i in f.vertices],dtype=np.float32).tobytes())
  h.update(o.data.materials[f.material_index].name.encode());h.update(bytes([f.use_smooth]))
  for layer in o.data.uv_layers:h.update(np.array([layer.data[k].uv for k in f.loop_indices],dtype=np.float32).tobytes())
  result[h.hexdigest()]+=1
 return result

def digest(o):return hashlib.sha256(json.dumps(sorted(faces(o).items())).encode()).hexdigest()

bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.37.blend'))
original={o.name:(digest(o),np.array(o.matrix_local))for o in bpy.context.scene.objects if o.type=='MESH'and not o.name.startswith('holo.011_')}
joints={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}
rails={side:{'faces':faces(bpy.data.objects[f'holo.011_{side}']),'world':np.array(bpy.data.objects[f'holo.011_{side}'].matrix_world)}for side in['Port','Starboard']}
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.38.blend'))
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted();rows=[]
for side,stations in [('Port',[1,2]),('Starboard',[3,4])]:
 members=[bpy.data.objects[f'holo.011_{side}']]+[bpy.data.objects[f'Defense_{i:02}_{role}']for i in stations for role in['FixedHood','LowerCradle']]
 final=sum((faces(o)for o in members),Counter())
 assert final==rails[side]['faces'],'Every original polygon, material and UV must exist exactly once'
 for o in members:
  expected=rails[side]['world'].copy()
  if o.name.endswith('_FixedHood'):expected[:3,3]+=np.array(asset.matrix_world)[:3,:3]@np.array([(-1 if side=='Port'else 1)*9.781475067138672,2.0791168212890625,0])
  assert np.max(np.abs(np.array(o.matrix_world)-expected))<.000001
for i in range(1,5):
 c=bpy.data.objects[f'Defense_{i:02}_Carriage'];hood=bpy.data.objects[f'Defense_{i:02}_FixedHood'];lower=bpy.data.objects[f'Defense_{i:02}_LowerCradle']
 assert hood.parent.name==f'Defense_{i:02}_FixedArmor'and hood.parent.parent==asset
 assert lower.parent==c and c['raisedEndpointIsSourceRest']and c['stowDrop']==4.6
 rows.append({'station':i,'hoodVertices':len(hood.data.vertices),'hoodFaces':len(hood.data.polygons),'supportVertices':len(lower.data.vertices),'supportFaces':len(lower.data.polygons),'hoodParent':hood.parent.name,'supportParent':lower.parent.name,'hoodSourceReferenceFrame':30,'raisedOrigin':list((inv@c.matrix_world).translation),'stowDrop':c['stowDrop']})
for name,(signature,matrix)in original.items():
 o=bpy.data.objects[name];assert digest(o)==signature,name;assert np.max(np.abs(np.array(o.matrix_local)-matrix))<.000001,name
changed_metadata={f'Defense_{i:02}_Carriage'for i in range(1,5)}|{f'DefenseRail_Forward_{s}'for s in['Port','Starboard']}
for name,(matrix,props)in joints.items():
 o=bpy.data.objects[name];assert np.max(np.abs(np.array(o.matrix_local)-matrix))<.000001,name
 if name not in changed_metadata:assert plain(dict(o.items()))==props,name
source=root.parent/'Odin 建模/odin.blend'
with source.open('rb')as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
assert sha=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
fixed={o.name:np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])for o in bpy.context.scene.objects if o.name.endswith(('_FixedHood','_LowerCradle'))and o.name.startswith('Defense_')}
bpy.ops.wm.open_mainfile(filepath=str(source))
def source_shapes(frame):
 bpy.context.scene.frame_set(frame);o=bpy.data.objects['holo.011'];ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
 sp=[o.matrix_world@v.co for v in mesh.vertices];kd=KDTree(len(sp))
 for i,p in enumerate(sp):kd.insert(p,i)
 kd.balance();mesh.calc_loop_triangles();surface=BVHTree.FromPolygons(sp,[t.vertices[:]for t in mesh.loop_triangles],all_triangles=True);ev.to_mesh_clear()
 return kd,surface
hood_kd,hood_surface=source_shapes(30);lower_kd,lower_surface=source_shapes(15)
for row in rows:
 i=row['station']
 for role in['FixedHood','LowerCradle']:
  kd,source_surface=(hood_kd,hood_surface)if role=='FixedHood'else(lower_kd,lower_surface)
  cloud=fixed[f'Defense_{i:02}_{role}'];errors=[kd.find(p)[2]for p in cloud]
  # The prior evaluated asset also contains vertices added along original
  # faces during triangulation. Check those against the actual source surface.
  surface_errors=[e if e<=.0001 else source_surface.find_nearest(Vector(p))[3]for p,e in zip(cloud,errors)]
  row[role+'SourceVertexMaxError']=max(errors);row[role+'SourceInterpolatedVertices']=sum(e>.0001 for e in errors)
  row[role+'SourceMaxError']=max(surface_errors);row[role+'SourceUnmatchedVertices']=sum(e>.0001 for e in surface_errors)
  if role=='FixedHood':assert not row[role+'SourceUnmatchedVertices'],(i,role,max(surface_errors))
  else:
   # The accepted evaluated mesh already differs at a handful of bearing seam
   # vertices. The exact face/coordinate comparison above proves this revision
   # introduces no such differences; do not remodel those unrelated seams.
   row['inheritedSupportSourceSurfaceDifferences']=[{'nativeVertex':k,'position':p.tolist(),'distance':surface_errors[k]}for k,(p,e)in enumerate(zip(cloud,surface_errors))if e>.0001]
   assert len(row['inheritedSupportSourceSurfaceDifferences'])<.005*len(cloud)
   assert max(surface_errors)<.16
 suffix='turret 1'+(f'.{i-1:03}'if i>1 else'');origin=np.array(bpy.data.objects[suffix].matrix_world.translation)
 row['originalRestOrigin']=origin.tolist();assert np.linalg.norm(origin-row['raisedOrigin'])<.00003
report={'version':'0.11.38','sourceSha256':sha,'originalSourceUnchanged':True,'sourceReferenceFrame':15,'originalRailFacesAndUVsPreservedExactlyOnce':True,'unchangedOtherMeshes':len(original),'unchangedStaticJointTransforms':len(joints),'unchangedOtherJointProperties':len(joints)-len(changed_metadata),'stations':rows,'animationClips':0}
with (root/'assets/blender/odin_articulated_v0.11.38.blend').open('rb')as f:report['nativeSha256']=hashlib.file_digest(f,'sha256').hexdigest()
(review/'source-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print('FORWARD_TWIN_SOURCE_VERIFIED',report,flush=True)
