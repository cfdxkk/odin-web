"""v0.10.0 static geometry from the v0.9.0 editable asset.

Source faces determine the single-channel seats and quad aperture petals.
No animations are baked; all strokes are authored by odin-rig.ts.
"""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
R=Path(__file__).resolve().parents[1]
# Reuse the existing mesh extraction/parenting primitives, without executing
# that revision's reconstruction, materials, or save operations.
helpers=(R/'tools/revise_secondary_bridge_v090.py').read_text(encoding='utf8')
exec(helpers[:helpers.index('def fit_channel_nose')])
out=R/'work/v0100-review';out.mkdir(exist_ok=True)
report={'singles':{},'bridge':{},'quads':{},'mainArmor':{},'twins':{}}
hull=bpy.data.objects['holo.001'];hp=parts(hull)
axial_axes={station:np.array(bpy.data.objects[f'Axial_{station}_Shutter_Port']['hingeAxisModel'])for station in ['Bow','Stern','Keel']}
tower=bpy.data.materials['Odin_Bridge_Armor'];trim=bpy.data.materials['Odin_Bridge_Trim'];glass=bpy.data.materials['Odin_Bridge_Glazing'];orange=bpy.data.materials['Odin_Paint_Orange'];alloy=bpy.data.materials['Odin_Equipment_Alloy']

def erase_tree(o):
 for c in list(o.children):erase_tree(c)
 bpy.data.objects.remove(o,do_unlink=True)

def world_mesh(o):
 M=inv@o.matrix_world;o.data.transform(M);o.parent=A;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_local=Matrix.Identity(4);o.data.update();return o

def segment(name,a,b,width,mat=trim,depth=None):
 a,b=Vector(a),Vector(b);z=b-a;mid=(a+b)/2
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.parent=A;o.location=mid;o.rotation_mode='QUATERNION';o.rotation_quaternion=z.to_track_quat('Z','Y');o.scale=(width,depth or width,z.length);o.data.materials.append(mat)
 return o

def bevel(o,width=.08):
 bpy.context.view_layer.objects.active=o;m=o.modifiers.new('Machined edges','BEVEL');m.width=width;m.segments=2;bpy.ops.object.modifier_apply(modifier=m.name)

def channel(name,p,container,C,Q,links,noses,parent):
 X,B,N=[Q[:,i]for i in range(3)]
 # Recover the existing nose, now a complete sliding cap instead of hull.
 if len(noses)!=2:
  M=inv@container.matrix_world;candidates=[]
  for f in container.data.polygons:
   if f.area<12:continue
   world=np.array([list(M@container.data.vertices[i].co)for i in f.vertices]);q=(world-C)@Q
   if 17<q[:,1].min()<23 and 27<q[:,1].max()<35 and max(abs(q[:,0]))<4 and 3<q[:,2].mean()<9:
    candidates.append((f.area,{'ids':set(f.vertices),'points':world,'virtual':True}))
  noses=[g for area,g in sorted(candidates,key=lambda p:-p[0])[:2]]
 assert len(noses)==2,(name,'front cap halves',len(noses))
 ps=np.concatenate([(g['points']-C)@Q for g in noses]);front=float(ps[:,1].min());edge=ps[ps[:,1]<front+.12]
 centre=(edge[:,0].min()+edge[:,0].max())/2;half=np.ptp(edge[:,0])/2
 crest=edge[:,2].max();left=edge[np.argmin(edge[:,0])];right=edge[np.argmax(edge[:,0])];base=(left[2]+right[2])/2
 # Source nose outer faces supply both longitudinal slopes and butt seams.
 planes=[];M=inv@container.matrix_world
 for g in noses:
  face=max([f for f in container.data.polygons if all(i in g['ids']for i in f.vertices)],key=lambda f:f.area)
  t=np.array([(np.array(M@container.data.vertices[i].co)-C)@Q for i in face.vertices]);planes.append(np.linalg.lstsq(np.c_[t[:,:2],np.ones(len(t))],t[:,2],rcond=None)[0])
 slope=float(np.mean([plane[1]for plane in planes]))
 if noses[0].get('virtual'):
  a,b=planes;centre=float(((b[1]-a[1])*front+b[2]-a[2])/(a[0]-b[0]));half=max(abs(edge[:,0]-centre));crest=float(a[0]*centre+a[1]*front+a[2]);base=float(np.mean([min(plane[0]*(centre-half)+plane[1]*front+plane[2],plane[0]*(centre+half)+plane[1]*front+plane[2])for plane in planes]))
 rise=crest-base
 lo=min(((g['points']-C)@Q)[:,1].min()for g in links)-1.9
 if name=='Axial_Bow':lo=max(lo,-10.65)
 end=front-.025;cuts=lo+(end-lo)*np.array([0,.26,.63,1.])
 cap=joint(name+'_FrontCap',C+B*front,parent,system='single-front-cap')
 cap['slideVector']=list(-B*3.);cap['settleVector']=list(-N*.75);cap['barrel']=p.name
 ids=set().union(*(g['ids']for g in noses));cp=extract(container,name+'_FrontCap_Skin',ids);keep(cp,cap)
 # Preserve the measured outside while adding an inward return to the cap.
 cp['fittedSourceSeat']=True
 # The source side walls determine the gauge shared by all seven covers.
 gauges=[]
 for g,plane in zip(noses,planes):
  t=(g['points']-C)@Q;distance=abs(t[:,2]-t[:,0]*plane[0]-t[:,1]*plane[1]-plane[2])/math.sqrt(1+plane[0]**2+plane[1]**2)
  gauges.extend(distance[distance>.03].tolist())
 gauge=float(np.clip(np.median(gauges)if gauges else .24,.22,.38))
 cp['armorThickness']=gauge;cap['armorThickness']=gauge
 cm=(inv@cp.matrix_world).to_3x3();bm=bmesh.new();bm.from_mesh(cp.data)
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if (cm@f.normal).dot(Vector(N))<.12 or f.calc_area()<.08],context='FACES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(cp.data);bm.free();cp.data.update()
 m=cp.modifiers.new('Front cap return','SOLIDIFY');m.thickness=gauge;m.offset=-1;bpy.context.view_layer.objects.active=cp;bpy.ops.object.modifier_apply(modifier=m.name)
 leaves=[]
 for k in range(3):
  y0,y1=cuts[k],cuts[k+1];n0=base+slope*(y0-front);axis=Vector(B+N*slope).normalized()
  for label,sign in [('Port',-1),('Starboard',1)]:
   j=joint(f'{name}_Shutter_{label}_{k:02}',C+X*(centre+sign*half)+B*y0+N*n0,parent,system='single-shutter')
   opening=180-math.degrees(math.atan2(rise,half))+1.5
   j['hingeAxisModel']=list(axis);j['closedAngleDegrees']=-sign*opening;j['barrelJoint']=p.name;j['panelIndex']=k;j['panelLength']=float(y1-y0);j['armorThickness']=gauge;j['openStart']=.015+k*.03;j['openEnd']=.225+k*.05
   pts=[C+X*(centre+sign*x)+B*y+N*(base+slope*(y-front)+z)for x,y,z in [(half,y0+.016,0),(.018,y0+.016,rise),( .018,y1-.016,rise),(half,y1-.016,0)]]
   if sign>0:pts.reverse()
   skin=prism(j.name+'_Skin',pts,gauge,j);skin['seatHalfWidth']=float(half)
   # Very shallow transverse lines only. The six leaves stay planar.
   for ri,y in enumerate(np.arange(y0+.5,y1-.25,1.25)):
    def point(x,yy):return C+X*(centre+sign*x)+B*yy+N*(base+slope*(yy-front)+(half-x)*rise/(half-.018)+.028)
    pts=[point(x,yy)for x,yy in [(half-.1,y),(.12,y),(.12,y+.025),(half-.1,y+.025)]]
    if sign>0:pts.reverse()
    prism(j.name+f'_Rib_{ri:02}',pts,.02,j,light,light)
   # Rest GLB pose is open; the closed shape above is the seating datum.
   turn=Matrix.Translation(Vector(C+X*(centre+sign*half)+B*y0+N*n0))@Matrix.Rotation(math.radians(sign*opening),4,axis)@Matrix.Translation(-Vector(C+X*(centre+sign*half)+B*y0+N*n0))
   bpy.context.view_layer.update()
   for c in j.children:c.matrix_world=A.matrix_world@turn@inv@c.matrix_world
   leaves.append(j.name)
 # Put the axis through the rear end of the existing breech, as marked red.
 old=(inv@p.matrix_world).translation.copy();direction=Vector(p['sourceBoreDirectionModel']);rear=old-direction*float(p.get('trunnionAdvance',7.5));move_origin(p,rear)
 p['trunnionAdvance']=0.;p['trunnionReference']='rear breech, user red datum';p['stowSink']=0.
 # Seat the moving breech crown against the fixed rear shell, not the floor
 # of the bay. A small fixed rest pitch fits the tube inside the closed roof.
 gun=next(c for c in p.children if c.type=='MESH');G=inv@gun.matrix_world;Gi=G.inverted();world=np.array([G@v.co for v in gun.data.vertices]);t=(world-C)@Q
 shroud=min([g for g in parts(gun)if g['n']>1000],key=lambda g:((g['points']-C)@Q)[:,1].min())
 sq=(shroud['points']-C)@Q;endq=sq[sq[:,1]<sq[:,1].min()+.15];crown=endq[endq[:,2]>endq[:,2].max()-.025].mean(0)
 H=inv@container.matrix_world;hp=np.array([H@v.co for v in container.data.vertices]);hq=(hp-C)@Q
 mask=(abs(hq[:,0]-centre)<half*.7)&(hq[:,1]>crown[1]-6)&(hq[:,1]<crown[1]-.5)&(hq[:,2]>crown[2]-.3)&(hq[:,2]<crown[2]+3)
 if np.any(mask):
  lip=hq[mask];lip=lip[lip[:,2]>lip[:,2].max()-.04];target=lip.mean(0);target[0]=centre;target[1]+=.04;target[2]-=.025
 else:target=crown+np.array([0,-2.5,.5])
 axis=Vector(p['hingeAxisModel']);anchor=Vector(C+Q@crown);destination=Vector(C+Q@target)
 edgeIds=np.array([e.vertices[:]for e in gun.data.edges])
 for pitch in np.linspace(0,-12,121):
  turn=Quaternion(axis,math.radians(pitch));rot=turn.to_matrix();shift=destination-(rear+rot@(anchor-rear));placed=np.array([rear+rot@(Vector(v)-rear)+shift for v in world]);q=(placed-C)@Q
  samples=[q];qa,qb=q[edgeIds[:,0]],q[edgeIds[:,1]]
  for cut in [lo,front]:
   cross=(qa[:,1]-cut)*(qb[:,1]-cut)<0;a,b=qa[cross],qb[cross];samples.append(a+(b-a)*((cut-a[:,1])/(b[:,1]-a[:,1]))[:,None])
  check=np.concatenate(samples);mask=(check[:,1]>lo-.0001)&(check[:,1]<front+.0001)&(abs(check[:,0]-centre)<half)
  roof=base+slope*(check[:,1]-front)+rise*(1-abs(check[:,0]-centre)/half)-gauge/math.cos(math.atan2(rise,half))
  if not np.any(mask)or float(np.max(check[mask,2]-roof[mask]))<-.14:break
 # The bow's original bore is longer than its distinct front seat. Shorten
 # only the distal tube, preserving the fitted breech, axis and rear cowl.
 if name=='Axial_Bow' and q[:,1].max()>front-.95:
  newDirection=np.array(turn@direction);along=placed@newDirection;tip=along.max();amount=(q[:,1].max()-front+.95)/(newDirection@B);weight=np.clip((along-(tip-12))/12,0,1)
  placed-=weight[:,None]*amount*newDirection;q=(placed-C)@Q
 for v,point in zip(gun.data.vertices,placed):v.co=Gi@Vector(point)
 move_origin(p,rear+shift);p['sourceBoreDirectionModel']=list(turn@direction);p['restPitchDegrees']=float(pitch);p['crownSeatModel']=list(destination);p['restSeatTranslation']=list(shift)
 cap['slideVector']=list(-B*float(np.clip(front-q[:,1].max()-.4,.6,3.)));cap['settleVector']=list(-N*1.0)
 report['singles'][name]={'frontCap':cap.name,'leaves':leaves,'armorThickness':gauge,'openAngle':opening,'cuts':cuts.tolist(),'closedSeat':{'center':float(centre),'halfWidth':float(half),'front':front,'base':float(base),'rise':float(rise),'slope':slope},'rearTrunnion':list(rear+shift),'restPitchDegrees':float(pitch),'crownSeatError':float((rear+rot@(anchor-rear)+shift-destination).length),'removedForwardOffset':list(old-rear)}
 if noses[0].get('virtual'):
  bm=bmesh.new();bm.from_mesh(container.data);bm.verts.ensure_lookup_table();bm.verts.index_update();bmesh.ops.delete(bm,geom=[f for f in bm.faces if all(v.index in ids for v in f.verts)],context='FACES_ONLY');bm.to_mesh(container.data);bm.free();container.data.update();return set()
 return ids

# Remove only the superseded secondary skins. The accepted main bay is kept.
for o in [o for o in s.objects if o.get('barrelJoint') and o.get('staticJoint')]:erase_tree(o)
frames=[((-.082539,-.034344,-.995996),(-.305406,.952156,-.007524)),((.938923,.092712,-.331404),(-.14875,.97775,-.1479)),((-.087255,-.019410,-.995997),(-.135697,.99073,-.007419)),((.896527,-.391877,-.206570),(.34655,.91091,-.22403))]
delete_hull=set()
for i in range(1,5):
 for side,sign in [('Port',-1),('Starboard',1)]:
  name=f'SideBattery_{i}_{side}';p=bpy.data.objects[name];mesh=next(c for c in p.children if c.type=='MESH');M=inv@mesh.matrix_world;center=np.mean([M@v.co for v in mesh.data.vertices],0)
  mirror=np.diag([sign,1,1]);X,B=map(np.array,frames[i-1]);X=mirror@X*sign;B=mirror@B;B/=np.linalg.norm(B);X-=B*(X@B);X/=np.linalg.norm(X);N=np.cross(X,B);Q=np.stack([X,B,N],1)
  links=sorted([g for g in hp if g['n']==184 and np.sign(g['center'][0])==sign],key=lambda g:np.linalg.norm(g['center']-center))[:16]
  lp=np.concatenate([g['points']for g in links]);C=lp.mean(0);t=(lp-C)@Q;C+=X*(t[:,0].max()+t[:,0].min())/2
  noses=[g for g in hp if g['n']==18 and 10<((g['points']-C)@Q)[:,1].min()<25 and abs(((g['points']-C)@Q)[:,0].mean())<4 and abs(((g['points']-C)@Q)[:,2].mean())<10]
  delete_hull|=channel(name,p,hull,C,Q,links,noses,A)
for station,forward,normal in [('Bow',(0,1,0),(0,0,1)),('Stern',(0,-1,0),(0,0,1)),('Keel',(0,-1,0),(0,0,-1))]:
 name='Axial_'+station;p=bpy.data.objects[name+'_Barrel'];container=bpy.data.objects['holo.022']if station=='Keel'else hull
 # Source transverse brackets determine the channel's slight deck rake.
 B=axial_axes[station];B/=np.linalg.norm(B)
 if B@forward<0:B=-B
 X=np.array([1.,0.,0.]);N=np.cross(X,B)
 if N@normal<0:X=-X;N=-N
 Q=np.stack([X,B,N],1);low,high={'Bow':(245,277),'Stern':(-272,-240),'Keel':(-77,-45)}[station]
 groups=parts(container)if station=='Keel'else hp
 links=[g for g in groups if (g['n']==184 if station!='Keel'else 900<g['n']<1250)and low<g['lo'][1]<high and max(abs(g['lo'][0]),abs(g['hi'][0]))<3]
 assert len(links)==15,(station,len(links));C=np.concatenate([g['points']for g in links]).mean(0)
 noses=[g for g in groups if g['n']==(176 if station=='Keel'else 28) and 14<((g['points']-C)@Q)[:,1].min()<24 and abs(((g['points']-C)@Q)[:,0].mean())<4 and abs(((g['points']-C)@Q)[:,2].mean())<12]
 if len(noses)!=2:
  print('AXIAL NOSES',station,[{'lo':((g['points']-C)@Q).min(0).tolist(),'hi':((g['points']-C)@Q).max(0).tolist()}for g in groups if g['n']==28],flush=True)
 ids=channel(name,p,container,C,Q,links,noses,bpy.data.objects['Axial_Keel_Mount']if station=='Keel'else A)
 if station=='Keel':remove(container,ids)
 else:delete_hull|=ids
remove(hull,delete_hull)

# Remove all reconstructed bridge shields and their guide hardware. Windows
# and the original fixed roof/frame remain the structure of the bridge.
for name in [o.name for o in s.objects if o.name.startswith(('BridgeArmor_','BridgeFixedGuide_'))]:
 o=bpy.data.objects.get(name)
 if o:erase_tree(o)
report['bridge']['animatedArmor']=0

# Four real tapered antenna panels replace the unpainted floating cubes.
for name in ['Cube','Cube.001']:erase_tree(bpy.data.objects[name])
for side,sign in [('Port',-1),('Starboard',1)]:
 for upper in [True,False]:
  name=f'BridgeAntenna_{side}_{"Upper"if upper else "Lower"}'
  center=Vector((sign*(14.0 if upper else 23.0),-36.8 if upper else -26.6,132.2 if upper else 125.1))
  axis=Vector((0,0,1))if upper else Vector((sign*.22,.04,-1)).normalized();across=Vector((1,0,sign*.22 if not upper else 0)).normalized();depth=axis.cross(across).normalized()
  shape=[(-1.48,.30),(1.48,.30),(1.65,6.6),(1.37,7.15),(-1.37,7.15),(-1.65,6.6)]
  pts=[center+across*x+axis*z+depth*.32 for x,z in shape]
  panel=prism(name,pts,.64,A,alloy,alloy);bevel(panel,.09)
  for face in [-1,1]:
   pts=[center+across*x+axis*z+depth*(face*.335)for x,z in [(-1.54,1.1),(1.54,1.1),(1.56,1.57),(-1.56,1.57)]]
   prism(name+f'_Stripe_{face}',pts,.02,A,orange,orange)
  segment(name+'_Pedestal',center-axis*.28,center+axis*.65,1.35,tower,.9)
  if not upper:segment(name+'_Mount',Vector((sign*21.9,-30.2,127.7)),center,1.1,trim)

# Move the low roof domes clear of the windows and toward both roof ends.
o=world_mesh(bpy.data.objects['Cylinder.001'])
for v in o.data.vertices:
 sign=1 if v.co.x>0 else-1;v.co.x+=sign*6.;v.co.z=132.0+(v.co.z-130.0)*.72
o.data.update()
# A flat-shaded geodesic shell preserves the source triangular topology.
o=bpy.data.objects['Icosphere']
for f in o.data.polygons:f.use_smooth=False
o.data.materials.clear();o.data.materials.append(alloy)
report['bridge']['radomeTriangles']=len(o.data.polygons)

def boom(name,a,b,width=.24):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();Y=Vector((0,1,0));Z=axis.cross(Y).normalized();spread=.58
 for yy in [-1,1]:
  for zz in [-1,1]:segment(name+f'_Chord{yy}{zz}',a+Y*yy*spread+Z*zz*spread,b+Y*yy*spread+Z*zz*spread,width)
 for k in range(4):
  p=a.lerp(b,k/3)
  segment(name+f'_Tie{k}',p-Y*spread-Z*spread,p+Y*spread+Z*spread,width*.75)
  if k<3:
   q=a.lerp(b,(k+1)/3)
   for yy in [-1,1]:segment(name+f'_Brace{k}{yy}',p+Y*yy*spread-Z*spread,q+Y*yy*spread+Z*spread,width*.7)

# Two rear capsules on standoff booms, plus the two smaller bridge repeaters.
capsule=world_mesh(bpy.data.objects['Cylinder']);original=parts(capsule)
for side,sign in [('Port',-1),('Starboard',1)]:
 group=next(g for g in original if np.sign(g['center'][0])==sign)
 for vi in group['ids']:capsule.data.vertices[vi].co.x+=sign*10.
 boom('RadarBoom_Rear_'+side,(sign*18.8,-81.72,105.8),(sign*31.3,-81.72,105.8))
 for z in [104.5,106.2]:segment('RadarClamp_Rear_'+side+str(z),(sign*30.3,-81.72,z),(sign*32.1,-81.72,z),.45)
 small=extract(capsule,'RadarCapsule_Bridge_'+side,group['ids']);world_mesh(small)
 old=Vector((sign*32.2796,-81.7215,104.8067));target=Vector((sign*17.7,-47.4,119.2))
 for v in small.data.vertices:v.co=target+(v.co-old)*.52
 boom('RadarBoom_Bridge_'+side,(sign*8.0,-47.4,119.8),(sign*17.3,-47.4,119.8),.16)
 # The pale narrow collar makes the capsule a mounted radome, not a rod.
 for obj,c,r in [(capsule,Vector((sign*32.2796,-81.7215,104.8067)),2.05),(small,target,1.07)]:
  bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=.22,location=(0,0,0));band=bpy.context.object;band.name='RadarCollar_'+obj.name+'_'+side;band.parent=A;band.location=c;band.data.materials.append(light)
capsule.data.update()
# Existing dark observation aperture becomes a matching tea-gold window.
window=bpy.data.objects['holo.015'];window.data.materials.clear();window.data.materials.append(bpy.data.materials['材质.004'])
for f in window.data.polygons:f.material_index=0
M=inv@hull.matrix_world
datum=max([f for f in hull.data.polygons if len(f.vertices)==5 and all(abs((M@hull.data.vertices[i].co).x)<4.1 and 68<(M@hull.data.vertices[i].co).z<81 for i in f.vertices)],key=lambda f:f.area)
datumPoints=[M@hull.data.vertices[i].co for i in datum.vertices];normal=(datumPoints[1]-datumPoints[0]).cross(datumPoints[2]-datumPoints[0]).normalized();distance=normal.dot(datumPoints[0])
def glazing_point(x,z):return(x,(distance-normal.x*x-normal.z*z)/normal.y,z)
opening=[(-3.42,80.49),(-3.42,95.43),(3.42,95.43),(3.42,80.49)]
pane=prism('BridgeWindow_LowerObservation',[glazing_point(x,z)for x,z in opening],.12,A,glass,glass)
pane['coplanarDatum']='Original lower front tower plate';pane['planeNormal']=list(normal);pane['planeDistance']=distance
report['bridge']['glassAperture']='vertical front-tower recess below quad deck, z80.50..95.43';report['bridge']['capsules']=4;report['bridge']['mountedPanelAntennas']=4

# Separate the actual four aperture petals on each quad (26 vertices each).
hp=parts(hull);ids=set()
for side,sign in [('Port',-1),('Starboard',1)]:
 petals=[g for g in hp if g['n']==26 and 27<sign*g['center'][0]<40 and -69<g['center'][1]<-54 and 102<g['center'][2]<111]
 assert len(petals)==4,(side,len(petals))
 for k,g in enumerate(sorted(petals,key=lambda g:(g['center'][1],g['center'][2]))):
  j=joint(f'PDC_{side}_HullPetal_{k}',g['center'],system='pdc-hull-petal');j['stowVector']=[-sign*.75,0,-.30]
  mesh=extract(hull,j.name+'_Skin',g['ids']);keep(mesh,j);ids|=g['ids']
 # Narrow and lower the rear fork rails to the central aperture corridor.
 rail=bpy.data.objects['holo.016__bridge turret'+('.001'if side=='Port'else '')];M=inv@rail.matrix_world;Mi=M.inverted()
 count=0
 for v in rail.data.vertices:
  p=M@v.co
  if sign*p.x<25:
   p.y=-61.7066+(p.y+61.7066)*.32;p.z=105.9+(p.z-105.9)*.35;v.co=Mi@p;count+=1
 rail.data.update();report['quads'][side]={'petals':4,'forkVerticesRecessed':count}
 # End the carriage fork at the aperture instead of sending its broad rear
 # shoe through the original sloping hull wall.
 bm=bmesh.new();bm.from_mesh(rail.data)
 res=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=Mi@Vector((sign*21.8,0,0)),plane_no=M.to_3x3().transposed()@Vector((sign,0,0)),clear_inner=True)
 border=[e for e in res['geom_cut']if isinstance(e,bmesh.types.BMEdge)and e.is_boundary]
 if border:bmesh.ops.holes_fill(bm,edges=border,sides=0)
 bm.to_mesh(rail.data);bm.free();rail.data.update()
 for k in range(4):
  fork=bpy.data.objects[f'PDC_{side}_FixedFork_{k}'];M=inv@fork.matrix_world;Mi=M.inverted()
  for v in fork.data.vertices:
   p=M@v.co;p.y=-61.7066+(p.y+61.7066)*.68;p.z=105.9+(p.z-105.9)*.50;v.co=Mi@p
  mesh=bpy.data.objects[f'PDC_{side}_ArmMesh_{k}'];M=inv@mesh.matrix_world;Mi=M.inverted();bm=bmesh.new();bm.from_mesh(mesh.data)
  res=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=Mi@Vector((sign*34.7,0,0)),plane_no=M.to_3x3().transposed()@Vector((sign,0,0)),clear_inner=True)
  border=[e for e in res['geom_cut']if isinstance(e,bmesh.types.BMEdge)and e.is_boundary]
  if border:bmesh.ops.holes_fill(bm,edges=border,sides=0)
  bm.to_mesh(mesh.data);bm.free();mesh.data.update()
  for part in [mesh,fork,bpy.data.objects[f'PDC_{side}_RootArmor_{k}']]:
   M=inv@part.matrix_world;Mi=M.inverted();delta=Vector((0,.30 if k<2 else -.30,1.20 if k%2==0 else -.22))
   for v in part.data.vertices:v.co=Mi@(M@v.co+delta)
   part.data.update()
remove(hull,ids)

# Aft twins gain extra closed travel inside their own hull pockets.
for i in range(5,9):
 j=bpy.data.objects[f'Defense_{i:02}_Carriage'];sign=j['side'];j['extraStowVector']=[-sign*4.3,.60,-.30]
 report['twins'][j.name]={'extraStow':list(j['extraStowVector'])}

# Increase each accepted solid's inward wall. Outer vertices and outline are
# byte-for-byte unchanged; no extra ridge or outward swelling is introduced.
for bank in ['Dorsal','Ventral']:
 for role,suffix in [('Port','FittedSkin'),('Starboard','FittedSkin'),('Nose','Wedge'),('Aft_Port','GapFiller'),('Aft_Starboard','GapFiller')]:
  o=bpy.data.objects[f'Hatch_{bank}_{role}_{suffix}'];M=inv@o.matrix_world;Mi=M.inverted();n=len(o.data.vertices)//2;before=[];after=[]
  for i in range(n):
   outer=M@o.data.vertices[i].co;inside=M@o.data.vertices[i+n].co;delta=inside-outer
   before.append(delta.length);delta*=2.1;o.data.vertices[i+n].co=Mi@(outer+delta);after.append(delta.length)
  o.data.update();o['armorThickness']=float(np.median(after));o.parent['armorThickness']=float(np.median(after));o['revision']='v0.10.0 inward reinforcement; accepted outer faces retained'
  report['mainArmor'][o.name]={'outerVerticesUnchanged':n,'beforeMedian':float(np.median(before)),'afterMedian':float(np.median(after))}
for side in ['Port','Starboard']:
 j=bpy.data.objects['Hatch_Dorsal_'+side];j['clearanceLift']=[0.,0.,.75];j['clearancePhaseEnd']=.09

# Deepen only the receiving surface hidden underneath the reinforced upper
# armor. Its exterior edge, all plate outside faces and hinge axes stay put.
from mathutils.bvhtree import BVHTree
inners=[];faces=[];cuts={}
for o in [o for o in s.objects if o.type=='MESH'and o.name.startswith('Hatch_Dorsal_')and o.name.endswith(('FittedSkin','Wedge','GapFiller'))]:
 M=inv@o.matrix_world;n=len(o.data.vertices)//2;start=len(inners);inners.extend(M@v.co for v in o.data.vertices);o.data.calc_loop_triangles()
 faces.extend(tuple(start+i for i in t.vertices)for t in o.data.loop_triangles)
 edges={}
 for f in o.data.polygons:
  if not(all(i<n for i in f.vertices)or all(i>=n for i in f.vertices)):continue
  ids=list(f.vertices)
  for a,b in zip(ids,ids[1:]+ids[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
 for edge,entries in edges.items():
  if len(entries)!=1:continue
  a,b=[M@o.data.vertices[i].co for i in edge];delta=b-a;normal=Vector((-delta.y,delta.x,0))
  if normal.length<.01:continue
  normal.normalize()
  if normal.x<0:normal=-normal
  key=tuple(round(v,4)for v in normal[:2])+(round(normal.dot(a),3),)
  lo=Vector((min(a.x,b.x)-.2,min(a.y,b.y)-.2,35));hi=Vector((max(a.x,b.x)+.2,max(a.y,b.y)+.2,54))
  if key in cuts:
   old=cuts[key];lo=Vector([min(lo[k],old[2][k])for k in range(3)]);hi=Vector([max(hi[k],old[3][k])for k in range(3)])
  cuts[key]=(a,normal,lo,hi)
M=inv@hull.matrix_world;Mi=M.inverted();bm=bmesh.new();bm.from_mesh(hull.data)
for v in bm.verts:v.co=M@v.co
def bounds(f):return np.min([v.co[:]for v in f.verts],0),np.max([v.co[:]for v in f.verts],0)
candidate={}
for f in bm.faces:
 low,high=bounds(f)
 if np.all(high>=(-16,74,34))and np.all(low<=(16,171,54)):candidate[f]=(low,high)
for a,normal,lo,hi in cuts.values():
 selected=[f for f,(low,high)in candidate.items()if f.is_valid and np.all(high>=lo)and np.all(low<=hi)]
 geom=set(selected)
 for f in selected:geom.update(f.edges);geom.update(f.verts)
 result=bmesh.ops.bisect_plane(bm,geom=list(geom),dist=1e-6,plane_co=a,plane_no=normal)
 for f in selected:candidate.pop(f,None)
 for f in result['geom']:
  if isinstance(f,bmesh.types.BMFace)and f.is_valid:candidate[f]=bounds(f)
for v in bm.verts:v.co=Mi@v.co
bm.to_mesh(hull.data);bm.free();hull.data.update()
innerTree=BVHTree.FromPolygons(inners,faces,all_triangles=True);M=inv@hull.matrix_world;Mi=M.inverted();count=0
for v in hull.data.vertices:
 p=M@v.co
 if not(75<p.y<170 and abs(p.x)<15.3 and 35<p.z<53):continue
 samples=[innerTree.ray_cast(Vector((p.x+x,p.y+y,30)),Vector((0,0,1)),25)[0]for x,y in [(0,0),(.06,0),(-.06,0),(0,.06),(0,-.06)]]
 hit=min([h for h in samples if h],key=lambda h:h.z,default=None)
 if hit and hit.z-.10<p.z<hit.z+6.:
  p.z=hit.z-.10;v.co=Mi@p;count+=1
hull.data.update();report['mainArmor']['hiddenReceiverVertices']=count

for o in s.objects:o.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
A['version']='0.10.0';s.name='ODIN v0.10.0 — measured seats, rear trunnions, fixed bridge and mounted radars'
bpy.context.view_layer.update();basis=Matrix.Rotation(-math.pi/2,4,'X');nodes=[]
for o in [A]+[o for o in s.objects if o.get('staticJoint')]:
 mat=basis@o.matrix_local@basis.inverted();nodes.append({'name':o.name,'parent':o.parent.name if o.parent else None,'matrix':[mat[r][c]for c in range(4)for r in range(4)],'extras':dict(o.items())})
(out/'rig-nodes.json').write_text(json.dumps(nodes,default=lambda x:list(x)),encoding='utf8')
(out/'geometry-build.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.10.0.blend'),compress=True)
print('SAVED v0.10.0',flush=True)
