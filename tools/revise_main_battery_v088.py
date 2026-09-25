"""Build the v0.8.8 review asset from the untouched v0.8.6 editable copy.

Main skins and independent nose share continuous side/roof planes constrained
by the closed turret shroud and forward hull. Fit the thin rear edge through
the full skin thickness; split and refit only the fixed aperture receiving
strip. Preserve the planar aft leaves and their complete hinge sweep.
All motion remains in Nuxt/Three.js; this source contains static joints only.
"""
import bpy,bmesh,json,hashlib,math
import numpy as np
from pathlib import Path
from collections import Counter
from mathutils import Vector,Quaternion
from mathutils.geometry import tessellate_polygon
ROOT=Path(__file__).resolve().parents[1]
(ROOT/'work/v088-review').mkdir(parents=True,exist_ok=True)
BASE=ROOT/'assets/blender/odin_articulated_v0.8.6.blend'
OUT=ROOT/'assets/blender/odin_articulated_v0.8.8.blend'
assert Path(bpy.data.filepath).resolve()==BASE.resolve()
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
# Actual closed web pose, sampled from the previous editable revision.
SIDE={};fitEvidence={}
# Three real closed contact samples define the uninterrupted side plane.
baseline=json.loads((ROOT/'docs/review/v0.8.8/baseline-v086-closed-pose.json').read_text(encoding='utf8'))
assert baseline['assetVersion']=='0.8.6' and hashlib.sha256(BASE.read_bytes()).hexdigest()==baseline['blendSha256']
pose=baseline['poses'][0]
basis=Quaternion((1,0,0),-math.pi/2);restore={}
for j in pose['joints']:
 o=bpy.data.objects[j['name']];restore[o.name]=(o.location.copy(),o.rotation_mode,o.rotation_quaternion.copy(),o.rotation_euler.copy())
 x,y,zp=j['position'];o.location=(x,-zp,y);q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
bpy.context.view_layer.update()
for side,sign in [('Port',-1),('Starboard',1)]:
 samples=[]
 for radius,y,nm in [(2.9065,114,'odin.007'),(8.0935,113,'odin.006' if side=='Port' else 'odin.008'),(2.9065,168,'holo.001')]:
  x=.0935+sign*radius;o=bpy.data.objects[nm];m=inv@o.matrix_world;mi=m.inverted();hit,p,n,face=o.ray_cast(mi@Vector((x,y,100)),mi.to_3x3()@Vector((0,0,-1)))
  assert hit;v=m@p;samples.append(v);fitEvidence.setdefault(side,[]).append({'object':nm,'face':face,'point':list(v)})
 coeff=np.linalg.solve(np.array([[v.x,v.y,1]for v in samples]),np.array([v.z for v in samples]));SIDE[side]=tuple(float(v)for v in coeff)
closed_shrouds=[(bpy.data.objects[nm],inv@bpy.data.objects[nm].matrix_world)for nm in ['odin.005','odin.006','odin.007','odin.008']]
for nm,(loc,mode,q,e) in restore.items():
 o=bpy.data.objects[nm];o.location=loc;o.rotation_mode=mode;o.rotation_quaternion=q;o.rotation_euler=e
bpy.context.view_layer.update()
ROOF=(0.,-.0654535522251,59.1309201278)
red=bpy.data.materials['Odin_Turret_Interior_DeepRed']
def z(plane,p):return plane[0]*p.x+plane[1]*p.y+plane[2]
def outline(obj):
 ps=[(inv@obj.matrix_world)@v.co for v in obj.data.vertices];ec=Counter()
 for f in obj.data.polygons:
  if f.normal.z>.1:
   ids=list(f.vertices)
   for a,b in zip(ids,ids[1:]+ids[:1]):ec[tuple(sorted((a,b)))]+=1
 adj={}
 for (a,b),count in ec.items():
  if count==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
 assert all(len(v)==2 for v in adj.values())
 loop=[next(iter(adj))];prev=None
 while True:
  nxt=next(i for i in adj[loop[-1]]if i!=prev)
  if nxt==loop[0]:break
  prev=loop[-1];loop.append(nxt)
 return [ps[i] for i in loop]
def clip(poly,fn):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  fa,fb=fn(a),fn(b)
  if fa>=-1e-8:out.append(a)
  if fa*fb<0:out.append(a.lerp(b,fa/(fa-fb)))
 return out
original_outlines={}
report={'revision':'0.8.8','study':'continuous armor surfaces fitted to the closed shroud and forward hull','sidePlanes':SIDE,'fitEvidence':fitEvidence,'roof':ROOF,'baselineClosedPose':'docs/review/v0.8.8/baseline-v086-closed-pose.json','ribs':False,'receivingHullLipCorrected':False,'parts':{}}
for name in ['Hatch_Dorsal_Port_FittedSkin','Hatch_Dorsal_Starboard_FittedSkin','Hatch_Dorsal_Nose_Wedge']:
 obj=bpy.data.objects[name];parent=obj.parent;poly=outline(obj)
 if '_Nose_' not in name:
  side='Port' if '_Port_' in name else 'Starboard';plane=SIDE[side];fixes=[]
  for p in poly:
   if p.y>=115.81 or abs(p.x-.0935)>8.90 or z(plane,p)>=z(ROOF,p)-.04:continue
   start=Vector((p.x,p.y+2,0));start.z=min(z(plane,start),z(ROOF,start));direction=Vector((0,-1,-plane[1])).normalized();hits=[]
   for dx in [-.07,0,.07]:
    for dz in [0,-.015,-.035,-.055]:
     origin=start+Vector((dx,0,plane[0]*dx+dz))
     for target,tm in closed_shrouds:
      ti=tm.inverted();hit,q,n,fi=target.ray_cast(ti@origin,ti.to_3x3()@direction)
      if hit:
       q=tm@q;dist=(q-origin).length
       if dist<4:hits.append((q.y,q,target.name,fi))
   if hits:
    _,q,nm,fi=max(hits,key=lambda h:h[0]);old=p.copy();p.y=q.y+.06
    fixes.append({'before':list(old),'afterXY':[p.x,p.y],'receivingObject':nm,'face':fi})
  report.setdefault('rearInterfaceUpdates',{})[side]=fixes
 original_outlines[name]=[p.copy() for p in poly]
 if sum(a.x*b.y-b.x*a.y for a,b in zip(poly,poly[1:]+poly[:1]))<0:poly.reverse()
 regions=[]
 for side,plane in SIDE.items():
  p=clip(poly,lambda q:z(ROOF,q)-z(plane,q))
  other=SIDE['Starboard' if side=='Port' else 'Port']
  p=clip(p,lambda q:z(other,q)-z(plane,q))
  if len(p)>2:regions.append((p,plane))
 p=poly
 for plane in SIDE.values():p=clip(p,lambda q:z(plane,q)-z(ROOF,q))
 if len(p)>2:regions.append((p,ROOF))
 top=[];tris=[];index={}
 def vertex(p):
  key=tuple(round(v,6)for v in p)
  if key not in index:index[key]=len(top);top.append(p)
  return index[key]
 for p,plane in regions:
  pp=[Vector((q.x,q.y,z(plane,q)))for q in p];ids=[vertex(q)for q in pp]
  for tri in tessellate_polygon([pp]):
   fi=[ids[t] if isinstance(t,int) else ids[min(range(len(pp)),key=lambda i:(pp[i]-t).length_squared)]for t in tri]
   if (top[fi[1]]-top[fi[0]]).cross(top[fi[2]]-top[fi[0]]).z<0:fi.reverse()
   tris.append(tuple(fi))
 n=len(top);faces=list(tris)+[tuple(i+n for i in reversed(t))for t in tris];ec=Counter()
 for f in tris:
  for a,b in zip(f,f[1:]+f[:1]):ec[tuple(sorted((a,b)))]+=1
 faces +=[(a,b,b+n,a+n)for(a,b),count in ec.items()if count==1]
 mi=(inv@obj.matrix_world).inverted();verts=top+[p-Vector((0,0,.055))for p in top];mesh=bpy.data.meshes.new(name+'_NativeContinuous');mesh.from_pydata([mi@p for p in verts],[],faces);mesh.update()
 mesh.materials.append(obj.data.materials[0]);mesh.materials.append(red)
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 for f in mesh.polygons:f.material_index=1 if len(tris)<=f.index<2*len(tris) else 0;f.use_smooth=False
 obj.data=mesh
 removed=[]
 for child in list(parent.children):
  if child.type=='MESH' and child!=obj:removed.append(child.name);bpy.data.objects.remove(child,do_unlink=True)
 report['parts'][name]={'surfacePlanes':len(regions),'topVertices':n,'triangles':len(tris),'removedRibObjects':removed}
# Add the straight pressed ribs directly on the accepted side planes.
def crossings(poly,y):
 return sorted(a.x+(b.x-a.x)*(y-a.y)/(b.y-a.y) for a,b in zip(poly,poly[1:]+poly[:1]) if (a.y>y)!=(b.y>y))
for side,sign in [('Port',-1),('Starboard',1)]:
 parent=bpy.data.objects[f'Hatch_Dorsal_{side}'];poly=original_outlines[parent.name+'_FittedSkin'];plane=SIDE[side];step=(154.95-115.7975-1)/14
 for i in range(14):
  ya=116.2975+i*step;yb=ya+step*.68
  def inner(y):return (ROOF[1]*y+ROOF[2]-plane[1]*y-plane[2])/plane[0]+sign*.13
  ra,rb=sign*inner(ya),sign*inner(yb);ri=max(ra,rb)
  ca,cbb=crossings(poly,ya),crossings(poly,yb)
  oa=max(sign*x for x in ca)-.15;ob=max(sign*x for x in cbb)-.15
  xa=sign*ri
  ps=[Vector((x,y,z(plane,Vector((x,y,0)))+.08))for x,y in [(xa,ya),(sign*oa,ya),(sign*ob,yb),(xa,yb)]]
  if sign<0:ps.reverse()
  bot=[q-Vector((0,0,.082))for q in ps];verts=ps+bot;fs=[(0,1,2),(0,2,3),(6,5,4),(7,6,4)]+[(j,(j+1)%4,(j+1)%4+4,j+4)for j in range(4)]
  nm=f'Hatch_Dorsal_{side}_Rib_{i:02}';mesh=bpy.data.meshes.new(nm);obj=bpy.data.objects.new(nm,mesh);bpy.context.scene.collection.objects.link(obj);obj.parent=parent;bpy.context.view_layer.update();mi=(inv@obj.matrix_world).inverted();mesh.from_pydata([mi@q for q in verts],[],fs);mesh.materials.append(bpy.data.materials['Odin_Paint_Light']);mesh.update()
  for f in mesh.polygons:f.use_smooth=False
report['ribs']=True
for side in ['Port','Starboard']:
 joint=bpy.data.objects[f'Hatch_Dorsal_{side}']
 release=list(joint.get('seamReleaseVector',[0,0,0]));release[1]+=.22;joint['seamReleaseVector']=release
 joint['clearanceLift']=[0,0,.15]
 joint['earlySeamReleaseFraction']=.4
# The source hull is a coarse unfinished model. Only its aperture receiving
# strip adapts to the approved cover plane; hull outside this strip is untouched.
hull=bpy.data.objects['holo.001'];hm=inv@hull.matrix_world;hmi=hm.inverted();samples=[];indices=[]
# Split long coarse hull facets at the receiving strip before moving vertices.
# Without these cuts one front-lip vertex drags a facet extending behind the
# rear flap, even though that flap and its hinge were left untouched.
bm=bmesh.new();bm.from_mesh(hull.data)
for axis,coords in [(1,[114.5]+list(range(116,175,2))),(0,list(range(-16,17)))]:
 for coordinate in coords:
  fs=[]
  for f in bm.faces:
   pts=[hm@v.co for v in f.verts]
   if max(p.z for p in pts)<32 or max(p.y for p in pts)<114.49 or min(p.y for p in pts)>174.01:continue
   if min(p.x for p in pts)>16.01 or max(p.x for p in pts)<-16.01:continue
   if min(p[axis]for p in pts)<coordinate<max(p[axis]for p in pts):fs.append(f)
  if not fs:continue
  geom=set(fs)
  for f in fs:geom.update(f.edges);geom.update(f.verts)
  p=Vector((0,0,0));p[axis]=coordinate;n=Vector((0,0,0));n[axis]=1
  bmesh.ops.bisect_plane(bm,geom=list(geom),dist=1e-6,plane_co=hmi@p,plane_no=hm.to_3x3().transposed()@n,clear_inner=False,clear_outer=False)
bm.to_mesh(hull.data);bm.free();hull.data.update()
original_hull_points=[v.co.copy()for v in hull.data.vertices]
for v in hull.data.vertices:
 p=hm@v.co
 if 114.5<p.y<174 and abs(p.x)<15.5 and p.z>34:indices.append(v.index);samples.append(p)
arr=np.array(samples);x=arr[:,0];y=arr[:,1];distance=np.full(len(samples),1e9);inside=np.zeros(len(samples),dtype=bool)
for poly in original_outlines.values():
 ip=np.zeros(len(samples),dtype=bool);dp=np.full(len(samples),1e9)
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if abs(a.y-b.y)>1e-10:ip ^= ((a.y>y)!=(b.y>y)) & (x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x)
  dx,dy=b.x-a.x,b.y-a.y;t=np.clip(((x-a.x)*dx+(y-a.y)*dy)/max(dx*dx+dy*dy,1e-20),0,1);dp=np.minimum(dp,np.hypot(x-a.x-dx*t,y-a.y-dy*t))
 distance=np.minimum(distance,dp);inside|=ip
plane=np.minimum.reduce([a*x+b*y+c for a,b,c in list(SIDE.values())+[ROOF]])
receiving=plane-.10;weight=np.where(inside,1,np.clip(1-distance/2.,0,1));eligible=(weight>0)&(((inside)&(arr[:,2]>receiving))|((distance<2.)&(arr[:,2]>receiving-3.0)))
# Never reinterpret tall unrelated neighboring details as aperture trim.
eligible &= arr[:,2]<receiving+2.5
changes=[]
for k in np.flatnonzero(eligible):
 old=samples[k];q=old.copy();q.z+=float((receiving[k]-q.z)*weight[k]);delta=q.z-old.z
 if abs(delta)<1e-6:continue
 hull.data.vertices[indices[k]].co=hmi@q;changes.append({'vertex':indices[k],'before':list(old),'after':list(q)})
hull.data.update()
# Preserve the already-fitted rear-flap sweep. The front shoulder approaches
# that joint at a corner, so its receiving-strip edit must stop at the actual
# swept volume rather than a rectangular Y cutoff.
from mathutils.bvhtree import BVHTree
aft_sweeps=[]
for side in ['Port','Starboard']:
 joint=bpy.data.objects[f'Hatch_Dorsal_Aft_{side}'];o=bpy.data.objects[joint.name+'_GapFiller'];m=inv@o.matrix_world
 o.data.calc_loop_triangles();ps=[m@v.co for v in o.data.vertices];fs=[tuple(t.vertices)for t in o.data.loop_triangles]
 axle=Vector(joint['hingeEdge'][0]);axis=Vector(joint['hingeAxis']);angle=float(joint['openingAngleDegrees'])
 for degree in range(131):
  q=Quaternion(axis,math.radians(angle*degree/130));aft_sweeps.append(BVHTree.FromPolygons([axle+q@(p-axle)for p in ps],fs,all_triangles=True,epsilon=.00001))
hull.data.calc_loop_triangles();hfs=[tuple(t.vertices)for t in hull.data.loop_triangles];restored=set()
for iteration in range(8):
 hv=[hm@v.co for v in hull.data.vertices];ht=BVHTree.FromPolygons(hv,hfs,all_triangles=True,epsilon=.00001);touch=set()
 for at in aft_sweeps:
  for hi,_ in ht.overlap(at):touch.update(hfs[hi])
 changed=False
 for vi in touch:
  if (hull.data.vertices[vi].co-original_hull_points[vi]).length>1e-7:
   hull.data.vertices[vi].co=original_hull_points[vi];restored.add(vi);changed=True
 hull.data.update()
 if not changed:break
changes=[]
for k,oldlocal in enumerate(original_hull_points):
 newlocal=hull.data.vertices[k].co
 if (newlocal-oldlocal).length>1e-6:changes.append({'vertex':k,'before':list(hm@oldlocal),'after':list(hm@newlocal)})
report['fixedHullReceivingLip']={'object':hull.name,'changedVertices':len(changes),'outsideTransitionWidth':2.,'aftSweepRestoredVertices':len(restored),'maximumDisplacement':max((abs(q['after'][2]-q['before'][2])for q in changes),default=0),'changes':changes}
report['receivingHullLipCorrected']=True
asset['version']='0.8.8'
OUT.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True);report['sha256']=hashlib.sha256(OUT.read_bytes()).hexdigest();(ROOT/'work/v088-review/geometry-build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('SAVED',str(OUT),report['sha256'],flush=True)
