"""Verify the four source-rim fits and preserve all unrelated source geometry."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
root=Path(__file__).resolve().parents[1];review=root/'docs/review/v0.11.35'
fixture=json.loads((root/'tests/fixtures/aft-twin-hull-rims-v01135.json').read_text())
fit=json.loads((review/'cover-fit.json').read_text());names={r['mesh']for r in fit['covers']}
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
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.34.blend'))
meshes={o.name:digest(o)for o in bpy.context.scene.objects if o.type=='MESH'and o.name not in names}
joints={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}
topology={n:([list(f.vertices)for f in bpy.data.objects[n].data.polygons],[bpy.data.objects[n].data.materials[f.material_index].name for f in bpy.data.objects[n].data.polygons])for n in names}
source=root.parent/'Odin 建模/odin.blend'
with source.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
assert source_hash==fixture['sourceSha256']
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.scene.frame_set(fixture['sourceGeometryFrame']);h=bpy.data.objects[fixture['sourceObject']]
sp=np.array([h.matrix_world@v.co for v in h.data.vertices]);source_ids=[]
for row in fixture['starboardApertures']:
 for sign in[1,-1]:
  for p in row['outerCorners']+[p for pair in row['shellThicknessPairs']for p in pair]:
   p=np.array(p)*[sign,1,1];dist=np.linalg.norm(sp-p,axis=1);i=int(dist.argmin())
   assert dist[i]<.000001,(row['station'],p,dist[i]);source_ids.append(i)
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.35.blend'))
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
for name,value in meshes.items():assert digest(bpy.data.objects[name])==value,('Unrelated mesh changed',name)
for name,(M,data)in joints.items():
 o=bpy.data.objects[name];assert np.array_equal(np.array(o.matrix_local),M)and plain(dict(o.items()))==data,('Joint frame or animation metadata changed',name)
h=bpy.data.objects['holo.001'];hp=np.array([(inv@h.matrix_world)@v.co for v in h.data.vertices]);rows=[]
for row in fit['covers']:
 o=bpy.data.objects[row['mesh']];p=np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices]);normal=np.cross(p[1]-p[0],p[2]-p[0]);normal/=np.linalg.norm(normal)
 assert ([list(f.vertices)for f in o.data.polygons],[o.data.materials[f.material_index].name for f in o.data.polygons])==topology[o.name]
 source_corners=hp[row['hullOuterCornerVertices']]
 assert np.array_equal(source_corners,np.array(row['originalHullCorners']))
 measurements=[float((hp[a]-hp[b])@normal)for a,b in row['hullThicknessPairVertices']]
 thickness=float(np.mean(measurements));cover_thickness=abs((p[4:]-p[:4])@normal)
 plane_error=float(abs((p[:4]-p[0])@normal).max());thickness_error=float(abs(cover_thickness-thickness).max())
 assert plane_error<.00003 and thickness_error<.00003
 assert np.max(abs((p[4:]-p[:4])+normal*thickness))<.00003
 assert np.max(abs(p[:4]-np.array(row['closedOuterCorners'])))<.00003
 assert max(np.linalg.norm(p[:4]-source_corners,axis=1))<.065
 assert np.min((p[:4]-source_corners)@normal)>.009
 rows.append({'station':row['station'],'mesh':o.name,'coverThickness':float(cover_thickness.mean()),'hullThickness':thickness,'maxThicknessError':thickness_error,'outerPlanarityError':plane_error,'normal':normal.tolist(),'sourceCornerGap':np.linalg.norm(p[:4]-source_corners,axis=1).tolist(),'vertices':len(p),'faces':len(o.data.polygons)})
for a,b in[(5,7),(6,8)]:
 pa=bpy.data.objects[f'Defense_{a:02}_NotchGate_Skin'];pb=bpy.data.objects[f'Defense_{b:02}_NotchGate_Skin'];cloud=lambda o:np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])
 mirrored=cloud(pa)*[-1,1,1];assert all(np.min(np.linalg.norm(cloud(pb)-p,axis=1))<.00003 for p in mirrored)
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
with(root/'assets/blender/odin_articulated_v0.11.35.blend').open('rb')as f:native_hash=hashlib.file_digest(f,'sha256').hexdigest()
report={'version':'0.11.35','nativeSha256':native_hash,'sourceSha256':source_hash,'sourceRimVerticesVerified':len(source_ids),'covers':rows,'unchangedOtherMeshes':len(meshes),'unchangedJointTransforms':len(joints),'unchangedJointMotionMetadata':len(joints),'fixedHullUnchanged':True,'originalSourceUnchanged':True,'animationClips':0}
(review/'source-geometry.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('AFT_COVER_SOURCE_FIT',len(meshes),len(joints),[(r['station'],r['maxThicknessError'],r['outerPlanarityError'])for r in rows],flush=True)
