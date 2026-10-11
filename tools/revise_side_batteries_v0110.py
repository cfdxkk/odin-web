"""Four vertical flank mounts: physical hinges, paired sliders, rigid carriage.

Run against v0.10.0. Upper sloping mounts, axial singles and all other systems
are left untouched. The source pose of the six vented leaves is deployed.
"""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
R=Path(__file__).resolve().parents[1]
helpers=(R/'tools/revise_secondary_bridge_v090.py').read_text(encoding='utf8')
exec(helpers[:helpers.index('def fit_channel_nose')])
out=R/'work/v0110-review';out.mkdir(exist_ok=True)
source=json.loads((R/'docs/review/v0.10.0/source-covers.json').read_text())
hull=bpy.data.objects['holo.001'];report={}

def erase(o):
 for c in list(o.children):erase(c)
 bpy.data.objects.remove(o,do_unlink=True)

def model_points(o):
 M=inv@o.matrix_world
 return np.array([M@v.co for v in o.data.vertices])

def inner_rail(skin,C,Q,sign):
 candidates=[]
 for g in parts(skin):
  t=(g['points']-C)@Q;span=np.ptp(t,axis=0)
  if span[1]>7.5 and span[0]<.75 and span[2]<1.2:
   candidates.append((float(np.mean(t[:,0])*sign),g))
 g=min(candidates,key=lambda p:p[0])[1]
 ps=g['points'];axis=np.linalg.eigh(np.cov(ps.T))[1][:,-1]
 if axis@Q[:,1]<0:axis=-axis
 return ps.mean(0),axis

def solid_strip(name,rows,parent,depth=.23):
 # Profile rows are rear/front arrays from the inner seam to the outer edge.
 vertices=rows[0]+rows[1];n=len(rows[0]);faces=[]
 for k in range(n-1):faces.append((k,k+1,k+1+n,k+n))
 me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update()
 o=bpy.data.objects.new(name,me);s.collection.objects.link(o);o.parent=A
 o.data.materials.append(light);o.data.materials.append(red)
 bpy.context.view_layer.objects.active=o
 mod=o.modifiers.new('Armor gauge','SOLIDIFY');mod.thickness=depth;mod.offset=-1;mod.material_offset=1
 bpy.ops.object.modifier_apply(modifier=mod.name);keep(o,parent);return o

for idx in [1,3]:
 for side in ['Starboard','Port']:
  name=f'SideBattery_{idx}_{side}';row=source[name];C0=np.array(row['frameOrigin']);Q0=np.array(row['frameAxes'])
  gun=bpy.data.objects[name];leaves={}
  # Separate fixed trough returns accidentally included with the old leaves.
  for k in range(3):
   for label,sign in [('Port',-1),('Starboard',1)]:
    j=bpy.data.objects[f'{name}_Shutter_{label}_{k:02}'];skin=next(c for c in j.children if c.type=='MESH')
    restored=set()
    for g in parts(skin):
     t=(g['points']-C0)@Q0
     span=np.ptp(t,axis=0)
     if (k==1 and span[1]<2.5 and span[2]>3.8 and t[:,1].mean()>-2.5) or (k==2 and g['n'] in [4,7,11,13]):restored|=g['ids']
    if restored:
     cp=extract(skin,skin.name+'_FixedTroughReturn',restored);keep(cp,A);remove(skin,restored)
    leaves[(k,sign)]=(j,skin)
  # Survey the two actual inner longitudinal rail centerlines. These physical
  # attachment edges, rather than a virtual inverse-solved pivot, define Q.
  hl,bl=inner_rail(leaves[(2,-1)][1],C0,Q0,-1);hr,br=inner_rail(leaves[(2,1)][1],C0,Q0,1)
  B=(bl+br);B/=np.linalg.norm(B);X=hr-hl;X-=B*(X@B);X/=np.linalg.norm(X);N=np.cross(X,B)
  Q=np.stack([X,B,N],axis=1);C=(hl+hr)/2;C-=B*((C-C0)@B)
  # Existing legacy tip wings are intentionally discarded. The new first
  # group occupies the bay in CLOSED pose, ahead of the six hinged leaves.
  erase(bpy.data.objects[name+'_FrontCap'])
  carriage=joint(name+'_Carriage',C,A,system='side-battery-carriage')
  carriage['battery']=name;carriage['sideBatteryMechanism']=True
  keep(gun,carriage);gun['sideBatteryMechanism']=True
  # The connected original outer pedestal is part of the same rear carriage,
  # including its sloped cheeks and root casing, not just the internal trough.
  housing=bpy.data.objects['holo.024'];housing_ids=set()
  for g in parts(housing):
   q=(g['points']-C)@Q;lo=q.min(0);hi=q.max(0)
   if max(abs(q[:,0]))<6 and -60<lo[1] and -4<hi[1]<0 and -20<lo[2] and hi[2]<5:housing_ids|=g['ids']
  assert len(housing_ids)>2000,(name,'missing original outer pedestal')
  shell=extract(housing,name+'_Carriage_OuterPedestal',housing_ids);keep(shell,carriage);remove(housing,housing_ids)
  carriage['originalOuterPedestalVertices']=len(housing_ids)
  for label in ['Port','Starboard']:
   fixed_return=bpy.data.objects.get(f'{name}_Shutter_{label}_01_Skin_FixedTroughReturn')
   if fixed_return:keep(fixed_return,carriage)
  leafReport=[];closed={};hinges={}
  for (k,sign),(j,skin) in leaves.items():
   H,axis=inner_rail(skin,C0,Q0,sign)
   move_origin(j,H);j['hingeAxisModel']=list(axis);j['closedAngleDegrees']=-sign*180.
   j['system']='side-battery-leaf';j['armorGroup']=4-k;j['physicalHinge']=True
   j['sourceHingeLine']=list(H);j['sideBatteryMechanism']=True
   # Root leaves clear first; all leaves remain at their original open pose.
   j['openStart']=.25+k*.035;j['openEnd']=.54+k*.055
   if k<2:keep(j,carriage)
   ps=model_points(skin);rot=np.array(Quaternion(Vector(axis),math.radians(-sign*180)).to_matrix())
   t=((ps-H)@rot.T+H-C)@Q;closed[(k,sign)]=t;hinges[(k,sign)]=(H,axis,rot)
   leafReport.append({'name':j.name,'group':4-k,'hinge':H.tolist(),'axis':axis.tolist(),'sourceVertices':len(ps),'closedBounds':[t.min(0).tolist(),t.max(0).tolist()]})
  # The actual front edge of the moving pair seats against the fixed pair.
  # The common outboard lift aligns both original inner bearing rails.
  frontH=np.mean([hinges[(2,z)][0]for z in [-1,1]],axis=0)
  rearH=np.mean([hinges[(1,z)][0]for z in [-1,1]],axis=0)
  rise=float((frontH-rearH)@N)
  fixedRear=max(np.min(closed[(2,z)][:,1])for z in [-1,1])
  movingFront=max(np.max(closed[(1,z)][:,1])for z in [-1,1])
  advance=max(.05,fixedRear-movingFront-.025)
  carriage['liftVector']=list(N*rise);carriage['slideVector']=list(B*advance)
  carriage['closingLiftStart']=.76;carriage['closingLiftEnd']=.86
  carriage['closingSlideStart']=.87;carriage['closingSlideEnd']=1.
  # Attach the original rear trough and its eight transverse supports to the
  # same carriage as the gun, preserving every vertex in deployed pose.
  hp=parts(hull);ids=set()
  for g in hp:
   t=(g['points']-C0)@Q0
   if g['n']==184 and max(abs(t[:,0]))<3.3 and -23<t[:,1].mean()<-2:ids|=g['ids']
  bracket=extract(hull,name+'_Carriage_Bearings',ids);keep(bracket,carriage);remove(hull,ids)
  # The main trough is a connected source shell; split at its existing break.
  M=inv@hull.matrix_world;ps=np.array([M@v.co for v in hull.data.vertices]);t=(ps-C0)@Q0;faceids=set()
  for f in hull.data.polygons:
   q=t[list(f.vertices)]
   if max(abs(q[:,0]))<5.85 and q[:,1].min()>-27 and q[:,1].max()<-1.05 and q[:,2].min()>-13 and q[:,2].max()<3.4:faceids.add(f.index)
  cp=hull.copy();cp.data=hull.data.copy();s.collection.objects.link(cp);cp.name=name+'_Carriage_Trough'
  bm=bmesh.new();bm.from_mesh(cp.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in faceids],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(cp.data);bm.free();keep(cp,carriage)
  bm=bmesh.new();bm.from_mesh(hull.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index in faceids],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(hull.data);bm.free()
  # Flat ridge returns are part of each existing leaf. Their closed width is
  # measured from the source outer edge; the two halves meet on a narrow seam.
  ridgeRows=[]
  for (k,sign),(j,skin) in leaves.items():
   H,axis,rot=hinges[(k,sign)];t=closed[(k,sign)];y0,y1=np.min(t[:,1]),np.max(t[:,1])
   # Longitudinal rakes are retained. Small return lips close the center gap.
   inner=t[np.argsort(sign*t[:,0])[:max(8,len(t)//15)]]
   zSlope=float(axis@N/(axis@B));height=float(np.percentile(inner[:,2]-zSlope*inner[:,1],75))
   width=float(max(.12,np.percentile(sign*inner[:,0],60)))
   hq=(H-C)@Q;backLift=0.
   if k==2:
    cross=(height-(hq[2]-zSlope*hq[1]))/(abs(hq[0])-width)
    normal=np.array([sign*cross,-zSlope,1.]);normal/=np.linalg.norm(normal)
    plane=np.dot(np.array([sign*width,0,height]),normal)
    backLift=float((np.max(t@normal)-plane+.25)/normal[2])
    height+=backLift;j['backingSeatLift']=backLift
   rows=[]
   for y in [y0+.012,y1-.012]:
    rows.append([list(H+rot.T@(C+Q@np.array([sign*x,y,height+zSlope*y])-H))for x in [.025,width+.10]])
   if sign<0:rows=[list(reversed(r))for r in rows]
   solid_strip(j.name+'_FlatRidgeReturn',rows,j,.22)
   if k==2:
    # The source front grille has no back skin. Close its actual rectangular
    # frame with the same gauge as the other two existing armored leaves.
    back=[]
    for y in [y0+.03,y1-.03]:
     back.append([list(H+rot.T@(C+Q@np.array([x,y,z])-H))for x,z in [(sign*width,height+zSlope*y),(hq[0],hq[2]+zSlope*(y-hq[1])+backLift)]])
    if sign<0:back=[list(reversed(r))for r in back]
    solid_strip(j.name+'_FrameBacking',back,j,.22)
   j['ridgeHalfWidth']=width;j['ridgeIntercept']=height;j['ridgeSlope']=zSlope
   ridgeRows.append({'group':4-k,'side':sign,'halfWidth':width,'height':height,'slope':zSlope})
  # First group follows the second group's CLOSED roof planes and flat ridge.
  rear=max(np.max(closed[(2,z)][:,1])for z in [-1,1])+.025
  front=18.40 if idx==1 else 18.65
  # A common profile on both sides gives a flat, finite-width crown.
  half=(np.linalg.norm(hr-hl))/2;ridge=np.mean([r['height']for r in ridgeRows if r['group']==2]);flat=.44
  slope=np.mean([r['slope']for r in ridgeRows if r['group']==2]);zBase=np.mean([leaves[(2,z)][0]['backingSeatLift']for z in [-1,1]])
  # Align the roof seams themselves, including the source return edges.
  rearRidge=np.mean([r['height']+r['slope']*movingFront for r in ridgeRows if r['group']==3])
  rise=float(ridge+slope*fixedRear-rearRidge);carriage['liftVector']=list(N*rise)
  # The preceding revision placed these bores above the actual hinge roof.
  # Re-seat each complete barrel and move its rear trunnion by the same vector.
  gunMesh=next(c for c in gun.children if c.type=='MESH');G=inv@gunMesh.matrix_world;Gi=G.inverted();gps=model_points(gunMesh);gq=(gps-C)@Q+np.array([0,advance,rise])
  samples=[gq];edges=np.array([e.vertices[:]for e in gunMesh.data.edges]);qa,qb=gq[edges[:,0]],gq[edges[:,1]]
  for y in [-19.,-10.,fixedRear,rear,front]:
   mask=(qa[:,1]-y)*(qb[:,1]-y)<0;a,b=qa[mask],qb[mask];samples.append(a+(b-a)*((y-a[:,1])/(b[:,1]-a[:,1]))[:,None])
  check=np.concatenate(samples);mask=(check[:,1]>-19.01)&(check[:,1]<front)&(abs(check[:,0])<half-.1)
  roof=ridge*np.minimum(1,(half-abs(check[:,0]))/(half-flat))
  sink=max(0,float(np.max(check[mask,2]-roof[mask]))+.38)
  shift=-N*sink
  for v,point in zip(gunMesh.data.vertices,gps):v.co=Gi@Vector(point+shift)
  move_origin(gun,np.array((inv@gun.matrix_world).translation)+shift);gun['roofSeatOffset']=list(shift);gun['trunnionReference']='rear breech, translated with complete bore for physical flank roof'
  for label,sign in [('Port',-1),('Starboard',1)]:
   j=joint(f'{name}_Slider_{label}',C,A,system='side-front-slider')
   j['battery']=name;j['armorGroup']=1;j['authoredClosed']=True;j['sideBatteryMechanism']=True
   j['liftVector']=list(N*.65);j['slideVector']=list(B*(front-rear+.6));j['armorThickness']=.23
   j['allowHullParkingIntersection']=idx==3
   rows=[]
   for y in [rear,front]:
    rows.append([list(C+Q@np.array([sign*x,y,z+slope*y]))for x,z in [(.025,ridge),(flat,ridge),(half,zBase)]])
   if sign<0:rows=[list(reversed(r))for r in rows]
   solid_strip(j.name+'_Skin',rows,j,.23)
  report[name]={'frameOrigin':C.tolist(),'frameAxes':Q.tolist(),'leaves':leafReport,'ridge':ridgeRows,'carriageLift':rise,'carriageAdvance':advance,'barrelSeat':sink,'sliderClosedRange':[rear,front],'sliderStroke':front-rear+.6,'troughFaces':len(faceids),'bearingVertices':len(ids),'deletedLegacyCap':True}
  print('SIDE',name,'rise',rise,'advance',advance,'ridge',ridge,'first',rear,front,flush=True)

A['version']='0.11.0';A['sideBatteryRevision']='four groups, physical edge hinges and closing carriage'
bpy.context.view_layer.update();basis=Matrix.Rotation(-math.pi/2,4,'X');nodes=[]
for o in [A]+[o for o in s.objects if o.get('staticJoint')]:
 mat=basis@o.matrix_local@basis.inverted();nodes.append({'name':o.name,'parent':o.parent.name if o.parent else None,'matrix':[mat[r][c]for c in range(4)for r in range(4)],'extras':dict(o.items())})
(out/'rig-nodes.json').write_text(json.dumps(nodes,default=lambda v:list(v)),encoding='utf8')
(out/'side-batteries.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.11.0.blend'),compress=True)
