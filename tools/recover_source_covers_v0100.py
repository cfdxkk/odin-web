"""Animate the original seven single-gun covers, preserving their source relief.

Run after revise_mechanics_v0100.py. Source odin.blend is a read-only library.
The source pose is deployed, including the front sliding cap.
"""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
R=Path(__file__).resolve().parents[1]
helpers=(R/'tools/revise_secondary_bridge_v090.py').read_text(encoding='utf8')
exec(helpers[:helpers.index('def fit_channel_nose')])
out=R/'work/v0100-review';out.mkdir(exist_ok=True)
currentHull=bpy.data.objects['holo.001'];currentKeel=bpy.data.objects['holo.022']
hp=parts(currentHull);kp=parts(currentKeel)
frames=[((-.082539,-.034344,-.995996),(-.305406,.952156,-.007524)),((.938923,.092712,-.331404),(-.14875,.97775,-.1479)),((-.087255,-.019410,-.995997),(-.135697,.99073,-.007419)),((.896527,-.391877,-.206570),(.34655,.91091,-.22403))]
stations=[]
for i in range(1,5):
 for side,sign in [('Port',-1),('Starboard',1)]:
  name=f'SideBattery_{i}_{side}';p=bpy.data.objects[name];mesh=next(c for c in p.children if c.type=='MESH');M=inv@mesh.matrix_world;center=np.mean([M@v.co for v in mesh.data.vertices],0)
  mirror=np.diag([sign,1,1]);X,B=map(np.array,frames[i-1]);X=mirror@X*sign;B=mirror@B;B/=np.linalg.norm(B);X-=B*(X@B);X/=np.linalg.norm(X);N=np.cross(X,B);Q=np.stack([X,B,N],1)
  links=sorted([g for g in hp if g['n']==184 and np.sign(g['center'][0])==sign],key=lambda g:np.linalg.norm(g['center']-center))[:16];lp=np.concatenate([g['points']for g in links]);C=lp.mean(0);q=(lp-C)@Q;C+=X*(q[:,0].max()+q[:,0].min())/2
  cuts=[-20.13,-10.58,-.35,9.10]if i in(1,3)else[-17.84,-8.19,.52,9.76]
  stations.append((name,p,currentHull,C,Q,cuts,A,0))
for st in ['Bow','Stern','Keel']:
 name='Axial_'+st;p=bpy.data.objects[name+'_Barrel'];B=np.array({'Bow':(0,.9806908059,-.1955646780),'Stern':(0,-.9445449234,-.3283822280),'Keel':(0,-.9445452393,.3283813194)}[st]);B/=np.linalg.norm(B);forward=np.array((0,1 if st=='Bow'else-1,0));normal=np.array((0,0,-1 if st=='Keel'else 1))
 if B@forward<0:B=-B
 X=np.array([1.,0,0]);N=np.cross(X,B)
 if N@normal<0:X=-X;N=-N
 Q=np.stack([X,B,N],1);low,high={'Bow':(245,277),'Stern':(-272,-240),'Keel':(-77,-45)}[st];groups=kp if st=='Keel'else hp
 links=[g for g in groups if (g['n']==184 if st!='Keel'else 900<g['n']<1250)and low<g['lo'][1]<high and max(abs(g['lo'][0]),abs(g['hi'][0]))<3];C=np.concatenate([g['points']for g in links]).mean(0)
 cuts=np.array([-16.25,-6.525,1.90,10.53])+( .14 if st=='Keel'else 0)
 stations.append((name,p,currentKeel if st=='Keel'else currentHull,C,Q,cuts,bpy.data.objects['Axial_Keel_Mount']if st=='Keel'else A,1 if st=='Keel'else 0))

with bpy.data.libraries.load(str(R.parent/'Odin 建模/odin.blend'),link=False)as(src,dst):dst.objects=['holo.001','holo.022']
sources=list(dst.objects)
for o in sources:s.collection.objects.link(o)
bpy.context.view_layer.update()
for o in sources:
 o.data.transform(o.matrix_world);o.parent=A;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_local=Matrix.Identity(4)
 # Use the existing converted materials, keeping original faces and UVs.
 for i,m in enumerate(o.data.materials):
  label=m.name.lower()if m else''
  o.data.materials[i]=bpy.data.materials['Odin_Paint_Orange']if'orange'in label else bpy.data.materials['Odin_Paint_Dark.001']if'dark'in label else light
bpy.context.view_layer.update();sourceParts=[parts(o)for o in sources]

def erase(o):
 for c in list(o.children):erase(c)
 bpy.data.objects.remove(o,do_unlink=True)
for o in [o for o in s.objects if o.get('staticJoint')and(o.get('barrelJoint')or o.get('system')=='single-front-cap')]:erase(o)

def face_key(points):return tuple(sorted(tuple(round(float(x),3)for x in p)for p in points))
removeKeys={currentHull:set(),currentKeel:set()}
def source_faces(source,name,faceids,parent,cut=None):
 cp=source.copy();cp.data=source.data.copy();s.collection.objects.link(cp);cp.name=name
 bm=bmesh.new();bm.from_mesh(cp.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in faceids],context='FACES')
 if cut:
  C,B,lo,hi=cut
  for value,outer in [(lo,False),(hi,True)]:
   bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=Vector(C+B*value),plane_no=Vector(B),clear_inner=not outer,clear_outer=outer)
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(cp.data);bm.free();cp.data.update();keep(cp,parent)
 return cp

report={}
for name,p,container,C,Q,cuts,parent,srcIndex in stations:
 X,B,N=[Q[:,i]for i in range(3)];source=sources[srcIndex];gs=sourceParts[srcIndex];S=inv@source.matrix_world;verts=np.array([S@v.co for v in source.data.vertices]);q=(verts-C)@Q
 fixedBracketIds=set().union(*(g['ids']for g in gs if g['n']==184))
 # Recover the two existing halves of the original front cap. Its original
 # location is the OPEN endpoint; NAV moves it back to meet the six leaves.
 candidates=[]
 for f in source.data.polygons:
  t=q[list(f.vertices)];lo=t.min(0);hi=t.max(0)
  if f.area>8 and 12<lo[1]<23 and 23<hi[1]<36 and max(abs(t[:,0]))<4 and 0<t[:,2].mean()<10:
   plane=np.linalg.lstsq(np.c_[t[:,:2],np.ones(len(t))],t[:,2],rcond=None)[0]
   if .9<abs(plane[0])<2.2 and abs(plane[1])<.15:candidates.append(f)
 largest=[max([f for f in candidates if np.mean(q[list(f.vertices),0])*sign>0],key=lambda f:f.area)for sign in[-1,1]]
 assert len(largest)==2,(name,'front source faces')
 capFaceIds=set();capGroupIds=set()
 for f in largest:
  g=next(g for g in gs if f.vertices[0]in g['ids'])
  if g['n']<200:capGroupIds|=g['ids']
  else:
   # Some side mounts share the cap with the fixed trough. Keep only its
   # actual two broad source faces and their existing return edges.
   chosen=set(f.vertices)
   for ff in source.data.polygons:
    if len(chosen.intersection(ff.vertices))>=2 and ff.area<3:capFaceIds.add(ff.index)
   capFaceIds.add(f.index)
 capFaceIds|={f.index for f in source.data.polygons if all(i in capGroupIds for i in f.vertices)}
 capPs=q[list(set(i for fi in capFaceIds for i in source.data.polygons[fi].vertices))];front=float(capPs[:,1].min());capCrest=float(capPs[capPs[:,1]<front+.16,2].max())
 capPlanes=[]
 for f in largest:
  t=q[list(f.vertices)];capPlanes.append(np.linalg.lstsq(np.c_[t[:,:2],np.ones(len(t))],t[:,2],rcond=None)[0])
 slope=float(np.mean([a[1]for a in capPlanes]));crossSlope=float(np.mean([abs(a[0])for a in capPlanes]));left,right=capPlanes
 center=float(((right[1]-left[1])*front+right[2]-left[2])/(left[0]-right[0]))
 capCrest=float(np.mean([a[0]*center+a[1]*front+a[2]for a in capPlanes]))
 closedFront=float(cuts[-1])-.035;closedCrest=capCrest+.15
 cap=joint(name+'_FrontCap',C+B*front,parent,system='single-front-cap');cap['barrel']=p.name;cap['sourceOpenPose']=True;cap['slideVector']=list(B*(closedFront-front));cap['settleVector']=list(N*.15);cap['sourceObject']='holo.022'if srcIndex else'holo.001';cap['armorThickness']=.25
 cp=source_faces(source,name+'_FrontCap_Skin',capFaceIds,cap);cp['sourceGeometry']=True;cp['armorThickness']=.25
 cap['originalOpenBounds']=np.array([capPs.min(0),capPs.max(0)]).tolist()
 rows=[]
 for k in range(3):
  y0,y1=float(cuts[k]),float(cuts[k+1]);ym=(y0+y1)/2
  for label,sign in [('Port',-1),('Starboard',1)]:
   slats=[]
   for g in gs:
    t=(g['points']-C)@Q;lo=t.min(0);hi=t.max(0);signed=t[:,0]*sign
    if signed.min()>2.0 and signed.max()<6.1 and y0<t[:,1].mean()<y1 and .3<hi[1]-lo[1]<3.0 and hi[0]-lo[0]>1.8 and hi[2]-lo[2]>1.8:slats.append(g)
   assert len(slats)>0,(name,label,k,'source crossbars',len(slats))
   cloud=np.concatenate([(g['points']-C)@Q for g in slats]);origin=cloud.mean(0);_,axes=np.linalg.eigh(np.cov(cloud.T));normal=axes[:,0]
   if normal[2]<0:normal=-normal
   ids=set()
   for f in source.data.polygons:
    if f.vertices[0]in fixedBracketIds:continue
    t=q[list(f.vertices)];signed=t[:,0]*sign
    if signed.min()<2.05 or signed.max()>5.95 or t[:,1].max()<y0-.08 or t[:,1].min()>y1+.08:continue
    if max(abs((t-origin)@normal))>.72:continue
    ids.add(f.index)
   # Shared faces are split at the existing segment boundary. No new cover
   # surfaces, replacement prisms, relief, or colored proxy panels are made.
   j=joint(f'{name}_Shutter_{label}_{k:02}',C+B*ym,parent,system='single-shutter')
   skin=source_faces(source,j.name+'_Skin',ids,j,(C,B,y0+.015,y1-.015));skin['sourceGeometry']=True
   M=inv@skin.matrix_world;ps=np.array([M@v.co for v in skin.data.vertices]);t=(ps-C)@Q
   assert len(ps)>30,(j.name,len(ps))
   # The crossbar plane measures the actual existing cover angle. Fold it
   # over its inner longitudinal attachment, staying above the source pose.
   dx=sign*normal[2];dz=-sign*normal[0];d0=np.array([dx,dz]);d0/=np.linalg.norm(d0);d1=np.array([-sign,crossSlope]);d1/=np.linalg.norm(d1)
   a0=math.atan2(d0[1],d0[0]);a1=math.atan2(d1[1],d1[0]);angle=-(a1-a0)
   if sign>0:
    while angle>0:angle-=2*math.pi
   else:
    while angle<0:angle+=2*math.pi
   # Hinge rake follows the mean of source and closed longitudinal slopes.
   sourceSlope=-normal[1]/normal[2];axis=Vector(B+N*(sourceSlope+slope)*.5).normalized();turn=Quaternion(axis,angle);rot=np.array(turn.to_matrix())
   edge=t[t[:,0]*sign>(t[:,0]*sign).max()-.12].mean(0);e=C+Q@edge
   target=C+B*edge[1]+X*(center+sign*.055)+N*(closedCrest+slope*(edge[1]-closedFront))
   h=np.linalg.pinv(np.eye(3)-rot)@(target-rot@e);a=np.array(axis);h+=a*(np.dot(e,a)-np.dot(h,a));move_origin(j,h)
   j['hingeAxisModel']=list(axis);j['closedAngleDegrees']=math.degrees(angle);j['barrelJoint']=p.name;j['panelIndex']=k;j['openStart']=.015+k*.03;j['openEnd']=.225+k*.05;j['armorThickness']=.25;j['sourceGeometry']=True;j['sourceObject']=cap['sourceObject']
   for fi in ids:removeKeys[container].add(face_key(verts[list(source.data.polygons[fi].vertices)]))
   rows.append({'name':j.name,'vertices':len(ps),'angle':math.degrees(angle),'originalBounds':[t.min(0).tolist(),t.max(0).tolist()],'sourceFaces':len(ids)})
 for fi in capFaceIds:removeKeys[container].add(face_key(verts[list(source.data.polygons[fi].vertices)]))
 report[name]={'covers':rows,'frameOrigin':C.tolist(),'frameAxes':Q.tolist(),'frontOpen':np.array(cap['originalOpenBounds']).tolist(),'frontClosedSlide':list(cap['slideVector']),'frontClosedLift':list(cap['settleVector'])}
 print('RECOVERED',name,[r['vertices']for r in rows],flush=True)

# Remove source faces that survived the earlier procedural covers. Matching
# original coordinates avoids changing any unrelated hull region.
for container,keys in removeKeys.items():
 M=inv@container.matrix_world;bm=bmesh.new();bm.from_mesh(container.data);removeFaces=[f for f in bm.faces if face_key([M@v.co for v in f.verts])in keys]
 bmesh.ops.delete(bm,geom=removeFaces,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(container.data);bm.free();container.data.update()
for o in sources:bpy.data.objects.remove(o,do_unlink=True)

(out/'source-covers.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.context.view_layer.update();basis=Matrix.Rotation(-math.pi/2,4,'X');nodes=[]
for o in [A]+[o for o in s.objects if o.get('staticJoint')]:
 mat=basis@o.matrix_local@basis.inverted();nodes.append({'name':o.name,'parent':o.parent.name if o.parent else None,'matrix':[mat[r][c]for c in range(4)for r in range(4)],'extras':dict(o.items())})
(out/'rig-nodes.json').write_text(json.dumps(nodes,default=lambda x:list(x)),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.10.0.blend'),compress=True)
