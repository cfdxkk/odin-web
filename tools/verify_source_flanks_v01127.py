"""Prove source detail preservation, sealed seams and exact mechanical retention."""
import bpy,hashlib,json,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1]
def plain(v):
 if hasattr(v,'to_dict'):return{k:plain(x)for k,x in v.to_dict().items()}
 if hasattr(v,'to_list'):return[plain(x)for x in v.to_list()]
 if isinstance(v,dict):return{k:plain(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return[plain(x)for x in v]
 return v
def snapshot(o):
 uv=o.data.uv_layers.active
 return {'co':np.array([v.co for v in o.data.vertices],dtype=np.float32),'faces':[tuple(f.vertices)for f in o.data.polygons],
 'materials':[o.data.materials[f.material_index].name for f in o.data.polygons],
 'uv':[np.array([uv.data[k].uv for k in f.loop_indices],dtype=np.float32)if uv else np.array([])for f in o.data.polygons]}
def digest(r):
 h=hashlib.sha256(r['co'].tobytes())
 for f,m,u in zip(r['faces'],r['materials'],r['uv']):h.update(np.array(f,dtype=np.int32).tobytes());h.update(m.encode());h.update(u.tobytes())
 return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.26.blend'))
before={o.name:snapshot(o)for o in bpy.context.scene.objects if o.type=='MESH'}
joint_before={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}
old_bearing=bpy.data.objects['Odin_Restored_Starboard_Housing'];bearing_matrix=np.array(old_bearing.matrix_local).copy()
pb=before[old_bearing.name]['co'];bearings={}
for f in old_bearing.data.polygons:
 p=pb[list(f.vertices)]
 key=tuple(sorted(tuple(v)for v in p));u=before[old_bearing.name]['uv'][f.index]
 bearings[key]=(old_bearing.data.materials[f.material_index].name,{tuple(pb[v]):uv for v,uv in zip(f.vertices,u)})
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.27.blend'))
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted();fit=json.loads((root/'docs/review/v0.11.27/source-fit.json').read_text(encoding='utf8'))
rest={o.name:(o.location.copy(),o.rotation_mode,o.rotation_euler.copy(),o.rotation_quaternion.copy(),o.scale.copy())for o in bpy.context.scene.objects if o.get('staticJoint')}
changed={r['mesh']for station in fit['stations'].values()for r in station['leaves']}|{n+'_OriginalFrontCap'for n in fit['stations']}|{'Odin_Restored_Starboard_Housing','holo.001'}
unchanged=0;details=[]
for name,r in before.items():
 if name not in changed:assert digest(snapshot(bpy.data.objects[name]))==digest(r),(name,'Unrelated geometry changed');unchanged+=1
 elif name=='holo.001':
  new=snapshot(bpy.data.objects[name]);assert np.array_equal(new['co'][:len(r['co'])],r['co'])and new['faces'][:len(r['faces'])]==r['faces']
  different=[k for k,(a,b)in enumerate(zip(r['materials'],new['materials'][:len(r['faces'])]))if a!=b]
  assert different==[131174,163397]
  assert all(new['materials'][k]=='Odin_Paint_Light'for k in different)
  assert all(np.array_equal(a,b)for a,b in zip(r['uv'],new['uv'][:len(r['faces'])]))
  assert len(new['faces'])-len(r['faces'])==4
  assert all(m=='Odin_Paint_Light'for m in new['materials'][len(r['faces']):])
  assert all(new['materials'][k]=='Odin_Turret_Interior_DeepRed'for k in(194058,163402))
 elif name!='Odin_Restored_Starboard_Housing':
  new=snapshot(bpy.data.objects[name]);look={tuple(sorted(f)):k for k,f in enumerate(new['faces'])};err=0.
  for f,m,u in zip(r['faces'],r['materials'],r['uv']):
   k=look[tuple(sorted(f))];assert new['materials'][k]==m
   indices=[new['faces'][k].index(v)for v in f]
   if len(u):err=max(err,float(np.max(abs(u-new['uv'][k][indices]))))
  assert err<1e-6,(name,err)
  details.append({'mesh':name,'retainedPolygons':len(r['faces']),'maxUvError':err})
for name,(m,props)in joint_before.items():
 o=bpy.data.objects[name];assert np.array_equal(np.array(o.matrix_local),m);assert plain(dict(o.items()))==props
assert not bpy.data.objects.get('Odin_Restored_Starboard_Housing')
o=bpy.data.objects['Flank_4_Starboard_FixedBearingPair'];p=np.array([v.co for v in o.data.vertices],dtype=np.float32);count=0;uv=o.data.uv_layers.active
assert np.array_equal(np.array(o.matrix_local),bearing_matrix)
for f in o.data.polygons:
 key=tuple(sorted(tuple(v)for v in p[list(f.vertices)]));assert key in bearings,('Bearing changed',f.index)
 assert o.data.materials[f.material_index].name==bearings[key][0];count+=1
 for vi,li in zip(f.vertices,f.loop_indices):assert np.max(abs(np.array(uv.data[li].uv)-bearings[key][1][tuple(p[vi])]))<1e-6
assert count==1590
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text(encoding='utf8'));seams=[]
for name in fit['stations']:
 C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);objects=[]
 car=bpy.data.objects[name+'_SourceCarriage'];car.location+=Vector(car['closedOffsetModel'])
 cap=bpy.data.objects[name+'_FrontCap'];cap.location+=Vector(cap['slideVector'])
 for side in('Port','Starboard'):
  for i in range(3):
   j=bpy.data.objects[f'{name}_Shutter_{side}_{i:02}'];j.rotation_mode='QUATERNION';j.rotation_quaternion=Quaternion(Vector(j['hingeAxisModel']),np.deg2rad(j['closedAngleDegrees']));objects.extend(c for c in j.children if c.type=='MESH')
 objects.extend(c for c in cap.children if c.type=='MESH');bpy.context.view_layer.update()
 vertices=[];triangles=[];materials=[];owners=[]
 for o in objects:
  base=len(vertices);ps=np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices]);vertices.extend(Vector(v)for v in ps);o.data.calc_loop_triangles()
  for t in o.data.loop_triangles:triangles.append(tuple(base+k for k in t.vertices));materials.append(o.data.materials[o.data.polygons[t.polygon_index].material_index].name);owners.append((o.name,t.polygon_index))
 tree=BVHTree.FromPolygons(vertices,triangles,all_triangles=True);miss=[];red=[];rays=0;error=0.
 for sign in(-1,1):
  for b0 in(-8.195,.325,9.42):
   for b in np.linspace(b0-.18,b0+.18,19):
    for x in(.075,.30,.45,.60,.85,1.25,1.75,2.25,2.70,2.84):
     n=6.326-1.58*max(.45,x)-.007*b;p=C+Q@np.array([sign*x,b,n]);direction=Q@np.array([-1.58*sign,-.007,-1.]);direction/=np.linalg.norm(direction)
     hit,normal,index,distance=tree.ray_cast(Vector(p-direction),Vector(direction),2.)
     rays+=1
     if hit is None:miss.append([sign,x,b])
     elif materials[index]!='Odin_Paint_Light':red.append([sign,x,b,materials[index],owners[index],float(distance),((np.array(hit)-C)@Q).tolist()])
     else:error=max(error,abs(float(distance)-1.))
 center_miss=[];center_red=[];center_rays=0
 leading=min(row[1]for o in objects if 'OriginalFrontCap'in o.name for row in((np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])-C)@Q)if abs(row[0])<.05 and row[1]>15)
 for b in np.linspace(-17.4,leading-.05,160):
  n=5.615-.007*b if b<=9.425 else (5.615-.007*9.425)+(5.03-(5.615-.007*9.425))*(b-9.425)/(leading-9.425)
  for x in(-.012,0.,.012):
   start=C+Q@np.array([x,b,n+1]);hit,normal,index,distance=tree.ray_cast(Vector(start),Vector(-Q[:,2]),2.)
   center_rays+=1
   if hit is None:center_miss.append([x,b])
   elif materials[index]!='Odin_Paint_Light':center_red.append([x,b,owners[index]])
 seams.append({'station':name,'rays':rays,'misses':miss,'interiorFirstHits':red,'maxSurfaceDistanceError':error,'centerCrownRays':center_rays,'centerCrownMisses':center_miss,'centerCrownInteriorFirstHits':center_red})
 car.location-=Vector(car['closedOffsetModel']);cap.location-=Vector(cap['slideVector'])
 for side in('Port','Starboard'):
  for i in range(3):bpy.data.objects[f'{name}_Shutter_{side}_{i:02}'].rotation_quaternion=Quaternion((1,0,0,0))
 bpy.context.view_layer.update()
 print('SEAM_RAYS',name,rays,len(miss),len(red),error,'CENTER',center_rays,len(center_miss),len(center_red),flush=True)
for name,(location,mode,euler,quaternion,scale)in rest.items():
 o=bpy.data.objects[name];o.location=location;o.rotation_mode=mode;o.rotation_euler=euler;o.rotation_quaternion=quaternion;o.scale=scale
bpy.context.view_layer.update()
for name,(m,_)in joint_before.items():assert np.array_equal(np.array(bpy.data.objects[name].matrix_local),m)
with(root.parent/'Odin 建模/odin.blend').open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==fit['sourceSha256']
with(root/'assets/blender/odin_articulated_v0.11.27.blend').open('rb')as f:native_sha=hashlib.file_digest(f,'sha256').hexdigest()
report={'version':'0.11.27','nativeSha256':native_sha,'unchangedOtherMeshes':unchanged,'unchangedJointTransforms':len(joint_before),'unchangedJointMetadata':len(joint_before),'sourceArmorPolygonsAndUvs':details,'fixedBearingPolygons':count,'legacyFixedHousingPolygons':0,'closedSeams':seams,'restoredGrayOuterEndFaces':[131174,163397],'fixedHullCoordinatesAndUvsUnchanged':True,'retainedOriginalFixedHullPolygons':len(before['holo.001']['faces']),'grayOuterFloorBands':4,'originalFloorFacesStillRed':[194058,163402],'originalSourceUnchanged':True}
(root/'docs/review/v0.11.27/source-geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8')
assert all(not row['misses']and not row['interiorFirstHits']and not row['centerCrownMisses']and not row['centerCrownInteriorFirstHits']for row in seams),('Unsealed source seams',[(r['station'],len(r['misses']),len(r['interiorFirstHits']),len(r['centerCrownMisses']),len(r['centerCrownInteriorFirstHits']))for r in seams])
print('SOURCE_SEAM_PROOF',unchanged,len(joint_before),count,flush=True)
