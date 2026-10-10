"""Verify source surfaces, exact measured ramp tangency and fixed receiver centering."""
import bpy,json,numpy as np,hashlib,math
from pathlib import Path
from collections import Counter
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1];review=root/'docs/review/v0.11.39'
def plain(v):
 if hasattr(v,'to_dict'):return{k:plain(x)for k,x in v.to_dict().items()}
 if hasattr(v,'to_list'):return[plain(x)for x in v.to_list()]
 if isinstance(v,dict):return{k:plain(x)for k,x in v.items()}
 if isinstance(v,(tuple,list)):return[plain(x)for x in v]
 return v
def faces(o,coordinates=True):
 result=Counter()
 for f in o.data.polygons:
  h=hashlib.sha256()
  if coordinates:h.update(np.array([o.data.vertices[i].co for i in f.vertices],dtype=np.float32).tobytes())
  else:h.update(np.array(f.vertices[:],dtype=np.int32).tobytes())
  h.update(o.data.materials[f.material_index].name.encode());h.update(bytes([f.use_smooth]))
  for layer in o.data.uv_layers:h.update(np.array([layer.data[k].uv for k in f.loop_indices],dtype=np.float32).tobytes())
  result[h.hexdigest()]+=1
 return result
def changed(name):return name.endswith('_FixedHood')and name.startswith('Defense_0')or name.startswith('holo.011_')or name.startswith('odin.072__turret 1')and name.split('__')[-1]in['turret 1','turret 1.001','turret 1.002','turret 1.003']
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.38.blend'))
old={o.name:(faces(o),np.array(o.matrix_local),np.array(o.matrix_world))for o in bpy.context.scene.objects if o.type=='MESH'}
joints={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}
receiverReference={}
for i in range(1,5):
 h=bpy.data.objects[f'Defense_{i:02}_FixedHood'];H=bpy.data.objects['Odin_Asset'].matrix_world.inverted()@h.matrix_world;N=H.to_3x3().inverted().transposed();roof=max((f for f in h.data.polygons if len(f.vertices)==4 and(N@f.normal).normalized().z<-.7),key=lambda f:f.area);p=[H@h.data.vertices[k].co for k in roof.vertices];samples=[]
 for u in[.05,.2,.35,.5,.65,.8,.95]:
  for v in[.05,.2,.35,.5,.65,.8,.95]:samples.append(p[0]*(1-u)*(1-v)+p[1]*u*(1-v)+p[2]*u*v+p[3]*(1-u)*v)
 h.data.calc_loop_triangles();originalSurface=BVHTree.FromPolygons([H@v.co for v in h.data.vertices],[t.vertices[:]for t in h.data.loop_triangles],all_triangles=True)
 # The source quad is slightly non-planar. Probe its true triangulated
 # surface, rather than a bilinear interpolation that is off the source.
 receiverReference[i]={'roof':[originalSurface.find_nearest(p)[0]for p in samples],'maxHeight':max((H@v.co).z for v in h.data.vertices),'materials':set(m.name for m in h.data.materials),'usedMaterials':set(h.data.materials[f.material_index].name for f in h.data.polygons),'uvLayers':[layer.name for layer in h.data.uv_layers]}
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.39.blend'));asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
for name,(signature,local,world)in old.items():
 if changed(name):continue
 o=bpy.data.objects[name];assert faces(o)==signature,name;assert np.max(np.abs(np.array(o.matrix_local)-local))<1e-6,name;assert np.max(np.abs(np.array(o.matrix_world)-world))<1e-6,name
for side,stations in [('Port',[1,2]),('Starboard',[3,4])]:
 original=old[f'holo.011_{side}'];parts=[bpy.data.objects[f'Defense_{i:02}_GuideGeometry']for i in stations]
 assert sum((faces(o)for o in parts),Counter())==original[0]
 assert all(np.max(np.abs(np.array(o.matrix_world)-original[2]))<1e-6 for o in parts)
rows=[]
for i in range(1,5):
 suffix='turret 1'+(f'.{i-1:03}'if i>1 else'');name='odin.072__'+suffix;c=bpy.data.objects[f'Defense_{i:02}_Carriage'];tube=bpy.data.objects[f'Defense_{i:02}_TubeGeometry'];rear=bpy.data.objects[name]
 assert faces(tube)+faces(rear)==old[name][0]
 assert np.max(np.abs(np.array(tube.matrix_world)-old[name][2]))<1e-6
 assert len(rear.data.vertices)==3698 and rear.parent.name==f'Defense_{i:02}_Elevation'
 assert bpy.data.objects[f'Defense_{i:02}_Guides'].parent==c
 assert bpy.data.objects[f'Defense_{i:02}_Guides'].get('staticJoint')and bpy.data.objects[f'Defense_{i:02}_Guides'].get('preserveReceiverHeading')
 hood=bpy.data.objects[f'Defense_{i:02}_FixedHood'];H=inv@hood.matrix_world;points=[H@v.co for v in hood.data.vertices];reference=receiverReference[i];surface=BVHTree.FromPolygons(points,[f.vertices[:]for f in hood.data.polygons])
 roofError=max(surface.find_nearest(p)[3]for p in reference['roof']);roofHeightError=abs(max(p.z for p in points)-reference['maxHeight']);print('RECEIVER_ROOF_SOURCE_ERROR',i,roofError,roofHeightError,flush=True);assert roofError<1e-5 and roofHeightError<1e-5
 # Blender's Boolean consolidates the duplicate unused white slot. Verify
 # material identities and actual painted faces, rather than unused slots.
 assert set(m.name for m in hood.data.materials)==reference['materials']
 assert set(hood.data.materials[f.material_index].name for f in hood.data.polygons)==reference['usedMaterials']
 assert[layer.name for layer in hood.data.uv_layers]==reference['uvLayers']
 assert np.max(np.abs(np.array(hood.matrix_local)-old[hood.name][1]))<1e-6
 lower=bpy.data.objects[f'Defense_{i:02}_LowerCradle'];M=inv@lower.matrix_world;N=M.to_3x3().inverted().transposed()
 normal=sum(((N@lower.data.polygons[k].normal).normalized()*lower.data.polygons[k].area for k in c['rampFaceIndices']),Vector()).normalized();turn=Quaternion(Vector((0,0,1)),math.radians(c['closedAlignmentDegrees']));aligned=turn@normal;slide=Vector(c['stowVectorModel'])
 assert (normal-Vector(c['sourceRampNormalModel'])).length<1e-6
 assert (aligned-Vector(c['rampNormalModel'])).length<1e-6 and abs(slide.dot(aligned))<1e-5
 transverse=Vector(c['receiverCrossAxisModel']);endpoint=(inv@c.matrix_world).translation+Vector(c['deployedOffsetModel'])+slide
 assert abs((endpoint-Vector(c['receiverCenterModel'])).dot(transverse))<1e-5
 elevation=bpy.data.objects[f'Defense_{i:02}_Elevation'];bore=Vector(elevation['sourceBoreDirectionModel']);bore.z=0;bore.normalize();assert abs((turn@bore).dot(transverse))<1e-5
 rows.append({'station':i,'tubeVertices':len(tube.data.vertices),'retainedRearBracketVertices':len(rear.data.vertices),'rampTangencyError':abs(slide.dot(aligned)),'receiverCenterlineError':abs((endpoint-Vector(c['receiverCenterModel'])).dot(transverse)),'closedBoreAlignmentError':abs((turn@bore).dot(transverse)),'drop':-slide.z,'horizontalTravel':Vector((slide.x,slide.y,0)).length,'sourceRampFaces':plain(c['rampFaceIndices']),'receiverMaterialsAndUVLayersPreserved':True,'receiverRoofHeightMaxError':roofHeightError,'receiverRoofSurfaceMaxError':roofError,'receiverRoofSurfaceSamples':len(reference['roof']),'receiverSweepClearanceModel':hood['sweepClearanceModel']})
changes={f'Defense_{i:02}_Carriage'for i in range(1,5)}|{f'DefenseRail_Forward_{s}'for s in['Port','Starboard']}
for name,(matrix,props)in joints.items():
 o=bpy.data.objects[name];assert np.max(np.abs(np.array(o.matrix_local)-matrix))<1e-6,name
 if name not in changes:assert plain(dict(o.items()))==props,name
with (root.parent/'Odin 建模/odin.blend').open('rb')as f:sourceHash=hashlib.file_digest(f,'sha256').hexdigest()
assert sourceHash=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
with (root/'assets/blender/odin_articulated_v0.11.39.blend').open('rb')as f:nativeHash=hashlib.file_digest(f,'sha256').hexdigest()
report={'version':'0.11.39','originalSourceUnchanged':True,'sourceSha256':sourceHash,'nativeSha256':nativeHash,'allPartitionedFacesAndUVsPreservedExactlyOnce':True,'fixedReceiverSideLipsAdjusted':True,'unchangedOtherMeshes':sum(not changed(name)for name in old),'unchangedExistingJointTransforms':len(joints),'unchangedOtherJointProperties':len(joints)-len(changes),'newHorizontalTubeJoints':4,'newReceiverGuideJoints':4,'animationClips':len(bpy.data.actions),'stations':rows}
assert not bpy.data.actions;(review/'source-geometry.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print('INCLINED_TWIN_SOURCE_PROOF',report,flush=True)
