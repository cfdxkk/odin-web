import bpy,json,hashlib,math,numpy as np
from pathlib import Path
from mathutils import Quaternion,Vector
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1]
fit=json.loads((root/'docs/review/v0.11.28/source-fit.json').read_text())
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text())
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
def points(o):
 p=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',p);m=np.array(inv@o.matrix_world);return p.reshape(-1,3)@m[:3,:3].T+m[:3,3]
def tree(objects,C,Q):
 vertices=[];triangles=[];materials=[]
 for o in objects:
  ps=points(o);base=len(vertices);vertices.extend(Vector(p)for p in ps);o.data.calc_loop_triangles()
  for t in o.data.loop_triangles:
   triangles.append(tuple(base+k for k in t.vertices));materials.append(o.data.materials[o.data.polygons[t.polygon_index].material_index].name)
 return BVHTree.FromPolygons(vertices,triangles,all_triangles=True),materials
roof=[]
for name,row in fit['stations'].items():
 C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);car=bpy.data.objects[name+'_SourceCarriage'];cap=bpy.data.objects[name+'_FrontCap'];objects=[]
 car.location+=Vector(car['closedOffsetModel']);cap.location+=Vector(cap['slideVector'])
 for side in('Port','Starboard'):
  for i in range(3):
   j=bpy.data.objects[f'{name}_Shutter_{side}_{i:02}'];j.rotation_mode='QUATERNION';j.rotation_quaternion=Quaternion(Vector(j['hingeAxisModel']),math.radians(j['closedAngleDegrees']));objects.extend(c for c in j.children if c.type=='MESH')
 objects.extend(c for c in cap.children if c.type=='MESH');bpy.context.view_layer.update()
 bvh,materials=tree(objects,C,Q);miss=[];red=[];error=0.;rays=0;crown_error=0.;profile_error=0.
 intercept=row['crownIntercept'];slope=row['sideSlope'];half=row['flatCrownWidth']/2
 def height(x,b):return intercept-.007*b-slope*max(0,abs(x)-half)
 for b in np.linspace(-17.35,row['capLeadingB']-.05,241):
  for x in(-.25,-.05,0,.05,.25):
   n=height(x,b);origin=C+Q@np.array([x,b,n+1]);hit,normal,index,distance=bvh.ray_cast(Vector(origin),Vector(-Q[:,2]),2)
   rays+=1
   if hit is None:miss.append([x,float(b)])
   elif materials[index]!='Odin_Paint_Light':red.append([x,float(b),materials[index]])
   else:crown_error=max(crown_error,abs(float(distance)-1))
 for sign in(-1,1):
  for b0 in(-8.195,.325,9.42):
   for b in np.linspace(b0-.18,b0+.18,19):
    for x in(.10,.30,.60,.85,1.25,1.75,2.25,2.70,2.84):
     n=height(x,b);origin=C+Q@np.array([sign*x,b,n+1]);hit,normal,index,distance=bvh.ray_cast(Vector(origin),Vector(-Q[:,2]),2)
     rays+=1
     if hit is None:miss.append([sign*x,float(b)])
     elif materials[index]!='Odin_Paint_Light':red.append([sign*x,float(b),materials[index]])
     else:profile_error=max(profile_error,abs(float(distance)-1))
 # All gray source exterior vertices and newly built roof vertices use a
 # single profile. The ray test catches actual upper-face and center steps.
 roof.append({'station':name,'rays':rays,'misses':miss,'interiorFirstHits':red,'maxCrownLineError':crown_error,'maxSideSeamError':profile_error,'flatCrownWidth':row['flatCrownWidth'],'heightReduction':row['heightReduction']})
 print('ROOF',name,rays,len(miss),len(red),crown_error,profile_error,flush=True)
 car.location-=Vector(car['closedOffsetModel']);cap.location-=Vector(cap['slideVector'])
 for side in('Port','Starboard'):
  for i in range(3):bpy.data.objects[f'{name}_Shutter_{side}_{i:02}'].rotation_quaternion=Quaternion((1,0,0,0))
 bpy.context.view_layer.update()

o=bpy.data.objects['holo.001'];cloud=points(o);centers=np.empty(len(o.data.polygons)*3,dtype=np.float32);o.data.polygons.foreach_get('center',centers);m=np.array(inv@o.matrix_world);centers=centers.reshape(-1,3)@m[:3,:3].T+m[:3,3]
for row in roof:
 name=row['station'];C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);t=(centers-C)@Q
 vertices=[];triangles=[];materials=[]
 candidates=np.where((abs(t[:,0])<2)&(t[:,1]>20)&(t[:,1]<33)&(t[:,2]>2)&(t[:,2]<6))[0]
 for fi in candidates:
  f=o.data.polygons[int(fi)];ps=cloud[list(f.vertices)];start=len(vertices);vertices.extend(Vector(p)for p in ps)
  for k in range(1,len(ps)-1):triangles.append((start,start+k,start+k+1));materials.append(o.data.materials[f.material_index].name)
 fixed_tree=BVHTree.FromPolygons(vertices,triangles,all_triangles=True);miss=[];primer=[];error=0.;rays=0
 for b in np.linspace(21.95,29.60,52):
  for x in(-.20,0.,.20):
   n=fit['stations'][name]['crownIntercept']-.007*b;origin=C+Q@np.array([x,b,n+1]);hit,normal,index,distance=fixed_tree.ray_cast(Vector(origin),Vector(-Q[:,2]),2)
   rays+=1
   if hit is None:miss.append([x,float(b)])
   elif materials[index]!='Odin_Paint_Light':primer.append([x,float(b),materials[index]])
   else:error=max(error,abs(float(distance)-1))
 row.update(fixedReceiverRays=rays,fixedReceiverMisses=miss,fixedReceiverInteriorFirstHits=primer,maxFixedReceiverCrownError=error)
 print('FIXED_RECEIVER_ROOF',name,rays,len(miss),len(primer),error,flush=True)
 assert not miss and not primer and error<.015,('Fixed receiver does not match armor crown',name)
assert all(np.linalg.norm(centers-np.mean(item['pointsModel'],axis=0),axis=1).min()>.01 for item in fit['removedFloatingTriangles'])
# Probe the actual fixed exterior just under the common hinge rail. This
# catches a remaining short cheek, step or through-hole rather than merely
# accepting matching pivot metadata.
fixed_lips=[]
for name in fit['stations']:
 C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);vertices=[];triangles=[];mats=[];refs=[]
 for mesh in('holo.001','Flank24_OriginalFixedHull'):
  o=bpy.data.objects[mesh];p=points(o);q=(p-C)@Q;o.data.calc_loop_triangles()
  for t in o.data.loop_triangles:
   ps=q[list(t.vertices)]
   # Only the bay's original cheek components and their fitted contour
   # extensions. Adjacent long hull bulkheads cross this local frame but
   # are not part of the rail-to-cover seam under inspection.
   if max(abs(ps[:,0]))>6 or ps[:,1].min()<-18.5 or ps[:,1].max()>10 or ps[:,2].max()<1.4 or ps[:,2].min()>2.6:continue
   base=len(vertices);vertices.extend(Vector(v)for v in p[list(t.vertices)]);triangles.append((base,base+1,base+2));mats.append(o.data.materials[t.material_index].name);refs.append((mesh,t.polygon_index,ps.tolist()))
 bvh=BVHTree.FromPolygons(vertices,triangles,all_triangles=True);missing=[];red=[];error=0.
 for sign in(-1,1):
  for b in np.linspace(-17.35,9.4,241):
   n=1.7756-.007*b-.03;hit,normal,index,distance=bvh.ray_cast(Vector(C+Q@np.array([sign*2.96,b,n])),Vector(-sign*Q[:,0]),.25)
   if hit is None:missing.append([sign,float(b)])
   elif mats[index]!='Odin_Paint_Light':
    red.append([sign,float(b)])
    if len(red)<3:print('LIP_PRIMER_HIT',name,((np.array(hit)-C)@Q).tolist(),refs[index],flush=True)
   else:error=max(error,abs(abs(((np.array(hit)-C)@Q)[0])-2.88))
 fixed_lips.append({'station':name,'rays':482,'missing':missing,'redFirstHits':red,'maxOuterRailError':error})
 print('FIXED_HINGE_LIP',name,len(missing),len(red),error,flush=True)
 assert not missing and not red and error<.045,('Fixed lip has a step or opening',name,missing[:5],red[:5],error)
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
with(root.parent/'Odin 建模/odin.blend').open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==fit['sourceSha256']
with(root/'assets/blender/odin_articulated_v0.11.29.blend').open('rb')as f:native_hash=hashlib.file_digest(f,'sha256').hexdigest()
report={'version':'0.11.29','nativeSha256':native_hash,'closedRoofs':roof,'fixedHingeLips':fixed_lips,'removedFloatingTriangles':2,'originalSourceUnchanged':True,'animationClips':0}
(root/'docs/review/v0.11.29/roof-geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8')
assert all(not r['misses']and not r['interiorFirstHits']and r['maxCrownLineError']<.015 and r['maxSideSeamError']<.025 for r in roof),'Unsealed or uneven closed armor roof'
print('CLOSED_ROOF_PROOF',len(roof),flush=True)
