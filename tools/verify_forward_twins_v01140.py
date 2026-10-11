"""Verify the source foundation partition without deleting or reshaping faces."""
import bpy,json,hashlib,numpy as np,math
from pathlib import Path
from collections import Counter
from mathutils import Matrix,Vector,Quaternion
root=Path(__file__).resolve().parents[1];review=root/'docs/review/v0.11.40'
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
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.39.blend'))
old={o.name:(faces(o),np.array(o.matrix_local),np.array(o.matrix_world))for o in bpy.context.scene.objects if o.type=='MESH'}
joints={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}
reference={}
A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted()
for i in range(1,5):
 p=f'Defense_{i:02}';c=bpy.data.objects[p+'_Carriage'];turn=Quaternion(Vector((0,0,1)),math.radians(c['closedAlignmentDegrees']));center=(inv@c.matrix_world).translation
 reference[i]=np.array(Matrix.Translation(center+Vector(c['deployedOffsetModel']))@turn.to_matrix().to_4x4()@Matrix.Translation(-center)@inv@bpy.data.objects[p+'_LowerCradle'].matrix_world)
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.40.blend'));A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted()
changed={f'Defense_{i:02}_LowerCradle'for i in range(1,5)};rows=[]
for name,(signature,local,world)in old.items():
 if name in changed:continue
 o=bpy.data.objects[name];assert faces(o)==signature,name
 assert np.max(np.abs(np.array(o.matrix_local)-local))<1e-6,name
 assert np.max(np.abs(np.array(o.matrix_world)-world))<1e-6,name
for i in range(1,5):
 p=f'Defense_{i:02}';c=bpy.data.objects[p+'_Carriage'];lower=bpy.data.objects[p+'_LowerCradle'];foundation=bpy.data.objects[p+'_FoundationGeometry'];mount=bpy.data.objects[p+'_FixedFoundation']
 assert faces(lower)+faces(foundation)==old[lower.name][0]
 assert len(foundation.data.vertices)==140 and len(foundation.data.polygons)==145
 assert mount.parent==A and not mount.get('staticJoint')and mount.get('fixedHullSupport')
 assert lower.parent==c and foundation.parent==mount
 assert np.max(np.abs(np.array(lower.matrix_local)-old[lower.name][1]))<1e-6
 poseError=float(np.max(np.abs(np.array(inv@foundation.matrix_world)-reference[i])))
 print('FOUNDATION_POSE_ERROR',i,poseError,flush=True)
 assert poseError<.00003
 assert c['translationOnly']and 'alignStart'not in c and 'alignEnd'not in c
 F=inv@foundation.matrix_world;N=F.to_3x3().inverted().transposed()
 normal=sum(((N@foundation.data.polygons[k].normal).normalized()*foundation.data.polygons[k].area for k in c['fixedRampFaceIndices']),Vector()).normalized()
 error=abs(normal.dot(Vector(c['stowVectorModel'])));assert error<1e-5
 rows.append({'station':i,'foundationSourceIsland':foundation['sourceIsland'],'foundationVertices':len(foundation.data.vertices),'foundationFaces':len(foundation.data.polygons),'movingLowerVertices':len(lower.data.vertices),'allLowerFacesAndUVsPreservedExactlyOnce':True,'fixedFoundationWorldPoseMaxError':float(np.max(np.abs(np.array(inv@foundation.matrix_world)-reference[i]))),'stationaryRampTangencyError':error,'cradleTranslationOnly':True,'fixedInstallationDegrees':c['fixedInstallationDegrees']})
for name,(matrix,props)in joints.items():
 o=bpy.data.objects[name];assert np.max(np.abs(np.array(o.matrix_local)-matrix))<1e-6,name
 if name not in{f'Defense_{i:02}_Carriage'for i in range(1,5)}:assert plain(dict(o.items()))==props,name
def digest(path):
 with path.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
sourceHash=digest(root.parent/'Odin 建模/odin.blend');assert sourceHash=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
report={'version':'0.11.40','sourceSha256':sourceHash,'nativeSha256':digest(root/'assets/blender/odin_articulated_v0.11.40.blend'),'originalSourceUnchanged':True,'allLowerFacesAndUVsPreservedExactlyOnce':True,'unchangedOtherMeshes':len(old)-4,'unchangedExistingJointTransforms':len(joints),'unchangedOtherJointProperties':len(joints)-4,'animationClips':len(bpy.data.actions),'stations':rows}
assert not bpy.data.actions;(review/'source-geometry.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('FIXED_FOUNDATION_SOURCE_PROOF',report,flush=True)
