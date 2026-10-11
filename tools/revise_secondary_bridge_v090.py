"""Rebuild static secondary-battery and bridge joints from v0.8.11.

The original odin.blend and accepted main batteries are not changed. Geometry,
materials and measured joint data only; all motion lives in app/lib/odin-rig.ts.
"""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
R=Path(__file__).resolve().parents[1];out=R/'work/v090-review';out.mkdir(exist_ok=True)
s=bpy.context.scene;A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted()
light=bpy.data.materials['Odin_Paint_Light'];red=bpy.data.materials['Odin_Bay_Primer']
report={'singleBatteries':{},'quads':{},'twins':{},'bridge':{}}
def parts(o):
 m=o.data;p=list(range(len(m.vertices)));M=inv@o.matrix_world
 def find(i):
  while p[i]!=i:p[i]=p[p[i]];i=p[i]
  return i
 for e in m.edges:a,b=e.vertices;p[find(a)]=find(b)
 g={}
 for v in m.vertices:g.setdefault(find(v.index),[]).append(v.index)
 result=[]
 for ids in g.values():
  ps=np.array([list(M@m.vertices[i].co)for i in ids]);result.append(dict(ids=set(ids),n=len(ids),points=ps,lo=ps.min(0),hi=ps.max(0),center=ps.mean(0)))
 return result
def keep(o,parent):
 bpy.context.view_layer.update();mw=o.matrix_world.copy();o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_world=mw
def move_origin(o,point):
 children={c:c.matrix_world.copy()for c in o.children};o.matrix_world=A.matrix_world@Matrix.Translation(Vector(point));bpy.context.view_layer.update()
 for c,m in children.items():c.matrix_world=m
def joint(name,point,parent=A,system='secondary'):
 o=bpy.data.objects.new(name,None);s.collection.objects.link(o);o.parent=A;o.location=point;o['staticJoint']=True;o['system']=system
 if parent!=A:keep(o,parent)
 return o
def extract(o,name,ids):
 cp=o.copy();cp.data=o.data.copy();s.collection.objects.link(cp);cp.name=name
 bm=bmesh.new();bm.from_mesh(cp.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS');bm.to_mesh(cp.data);bm.free();cp.data.update();return cp
def remove(o,ids):
 bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index in ids],context='VERTS');bm.to_mesh(o.data);bm.free();o.data.update()
def bore(o,forward):
 candidates=[]
 for g in parts(o):
  if g['n']<100:continue
  w,u=np.linalg.eigh(np.cov(g['points'].T));axis=u[:,-1]
  if w[-1]/max(w[-2],1e-10)<100:continue
  if np.dot(axis,forward)<0:axis=-axis
  candidates.append((np.ptp(g['points']@axis),axis))
 if not candidates:raise RuntimeError('No measured bore '+o.name)
 return Vector(max(candidates,key=lambda t:t[0])[1]).normalized()
def palette(name,source,rgb,metal=.12,rough=.7):
 m=source.copy();m.name=name;m.diffuse_color=(*rgb,1);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 for link in list(p.inputs['Base Color'].links):
  if link.from_node.type=='TEX_IMAGE':
   old=link.from_node.image;size=old.size[:];pixels=np.array(old.pixels[:],dtype=np.float32).reshape(size[1],size[0],4);lum=pixels[:,:,:3].mean(2);variation=np.clip(lum/max(lum.mean(),1e-8),.9,1.1)
   image=bpy.data.images.new(name+'_Albedo',width=size[0],height=size[1],alpha=False);pixels[:,:,:3]=variation[:,:,None]*np.array(rgb);image.pixels.foreach_set(pixels.ravel());image.pack();link.from_node.image=image
 p.inputs['Base Color'].default_value=(*rgb,1)
 return m

def prism(name,points,thickness,parent,outer=light,inner=red):
 n=len(points);pts=[Vector(p)for p in points];normal=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized()
 verts=pts+[p-normal*thickness for p in pts];faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)]
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);s.collection.objects.link(o);o.parent=A;o.data.materials.append(outer);o.data.materials.append(inner)
 for f in me.polygons:f.material_index=1 if f.index==1 else 0
 keep(o,parent);return o

def fit_channel_nose(container,groups,C,Q):
 """Finish the source wedge's truncated centre ridge in its own face plane."""
 ps=np.concatenate([(g['points']-C)@Q for g in groups]);y=ps[:,1].min();edge=ps[ps[:,1]<y+.11]
 outer=np.array([edge[np.argmin(edge[:,0])],edge[np.argmax(edge[:,0])]])
 centre=(outer[:,0].min()+outer[:,0].max())/2;half=np.ptp(outer[:,0])/2;base=outer[:,2].mean();top=edge[:,2].max();high=edge[edge[:,2]>top-.02];crest=np.max(abs(high[:,0]-centre));slope=(top-base)/(half-crest);apex=base+half*slope
 assert 2<half<4,(container.name,half)
 M=inv@container.matrix_world;Mi=M.inverted();planes=[]
 for g in groups:
  faces=[f for f in container.data.polygons if all(i in g['ids']for i in f.vertices)]
  f=max(faces,key=lambda f:f.area);t=np.array([(np.array(M@container.data.vertices[i].co)-C)@Q for i in f.vertices]);plane=np.linalg.lstsq(np.c_[t[:,:2],np.ones(len(t))],t[:,2],rcond=None)[0];planes.append(plane)
 apex=float(np.mean([a*centre+b*y+c for a,b,c in planes]));long_slope=float(np.mean([p[1]for p in planes]));slope=float(np.mean([abs(p[0])for p in planes]));base=float(np.mean([a*outer[k,0]+b*y+c for k,(a,b,c)in enumerate(sorted(planes,key=lambda p:-p[0]))]))
 for g in groups:
  for i in g['ids']:
   point=container.data.vertices[i];t=(np.array(M@point.co)-C)@Q;x=t[0]-centre
   if abs(x)<crest+.05:
    t[0]=centre+x*.024;t[2]+=slope*abs(x)*.976
    point.co=Mi@Vector(C+Q@t)
 container.data.update()
 return {'y':float(y)-.012,'base':float(base),'ridge':float(apex),'center':float(centre),'half':float(half),'slope':long_slope}

def channel_covers(name,C,Q,links,parent=A,nose=None):
 """Fit thin triangular leaves to the actual source bearing line.

 The side channels consist of four short banks with different inclinations.
 Each keeps its own straight hinge, avoiding the old floating back sections.
 """
 X,B,N=[Q[:,i]for i in range(3)];gs=sorted(links,key=lambda g:(g['center']-C)@B);cs=np.array([[(g['center']-C)@B,((g['points']-C)@Q)[:,2].max()]for g in gs])
 lo=min(((g['points']-C)@Q)[:,1].min()for g in gs)-1.9;hi=max(((g['points']-C)@Q)[:,1].max()for g in gs)+1.0
 if name=='Axial_Bow':lo=max(lo,-10.65)
 banks=4 if name.startswith('Side')else 1;nodes=[]
 # A continuous seat follows the local hull's original bearing heights. The
 # leaf faces stay planar within each bank, with a narrow mechanical seam.
 if nose is not None:
  hi=float(nose['y']);front=nose['base'];rear=front+nose['slope']*(lo-hi)
  centre=float(nose['center']);half=float(nose['half']);rise=float(nose['ridge'])-front
 else:
  centre=0.;half=2.70;front=float(cs[-1,1])-.1;rear=float(cs[0,1])-.1;rise=3.28
 cuts=np.linspace(lo,hi,banks+1);hn=np.linspace(rear,front,banks+1)
 for k in range(banks):
  y0,y1=cuts[k],cuts[k+1];n0,n1=hn[k],hn[k+1];slope=(n1-n0)/(y1-y0);axis=Vector(B+N*slope).normalized()
  for leaf,ls in [('Port',-1),('Starboard',1)]:
   h=Vector(C+X*(centre+ls*half)+B*y0+N*n0);suffix=''if banks==1 else f'_{k:02}';j=joint(name+'_Shutter_'+leaf+suffix,h,parent,system='single-shutter')
   j['hingeAxisModel']=list(axis);j['closedAngleDegrees']=-ls*180.;j['barrelJoint']=name if name.startswith('Side')else name+'_Barrel'
   # The exterior closes at the centre ridge; a 0.025-unit seam is small
   # enough to read as a joint rather than a hole into the bay.
   gap=.012;points=[]
   for y,n in [(y0+gap,n0+slope*gap),(y1-gap,n1-slope*gap)]:
    points.extend([C+X*(centre+ls*x)+B*y+N*(n+z)for x,z in [(half,0),(.026,rise-.02),(.012,rise)]])
   faces=[(0,1,4,3),(1,2,5,4)]
   if ls>0:faces=[tuple(reversed(f))for f in faces]
   me=bpy.data.meshes.new(name+'_ShutterSkin_'+leaf+suffix);me.from_pydata(points,[],faces);me.materials.append(light);me.materials.append(red);me.update();skin=bpy.data.objects.new(me.name,me);s.collection.objects.link(skin);skin.parent=A;keep(skin,j)
   mod=skin.modifiers.new('Constant gauge armor','SOLIDIFY');mod.thickness=.10;mod.offset=-1;mod.material_offset=1;bpy.context.view_layer.objects.active=skin;bpy.ops.object.modifier_apply(modifier=mod.name)
   # Fine transverse relief retains the source vented, sectional treatment.
   for ri,y in enumerate(np.arange(y0+.45,y1-.2,.83)):
    n=n0+(y-y0)*slope;w=.035
    # Seat the relief on this fitted plane, not the old guessed ridge height;
    # coincident strip faces caused the dotted shimmer on the closed armor.
    def rib_z(x):return (half-x)*(rise-.02)/(half-.026)+.035
    strip=[C+X*(centre+ls*x)+B*yy+N*(n+slope*(yy-y)+rib_z(x))for x,yy in [(half-.1,y),(.12,y),(.12,y+w),(half-.1,y+w)]]
    if ls>0:strip.reverse()
    prism(name+'_ShutterRib_'+leaf+suffix+f'_{ri:02}',strip,.025,j,light,light)
   # Store the static asset in the deployed pose. JS closes the leaf.
   turn=Matrix.Translation(h)@Matrix.Rotation(math.pi,4,axis)@Matrix.Translation(-h)
   bpy.context.view_layer.update()
   for child in j.children:child.matrix_world=A.matrix_world@turn@inv@child.matrix_world
   nodes.append(j.name)
 return nodes

# Recover all eight side-single cover banks from the hull. Their material
# frames are measured from matching 184-vertex source bearing brackets (ICP
# residual <0.005 model units), not guessed global Euler rotations.
frames=[
 ((-.082539,-.034344,-.995996),(-.305406,.952156,-.007524),(.94864,.30356,-.08908)),
 ((.938923,.092712,-.331404),(-.14875,.97775,-.1479),(.31032,.18817,.93186)),
 ((-.087255,-.019410,-.995997),(-.135697,.99073,-.007419),(.98689,.13451,-.089075)),
 ((.896527,-.391877,-.206570),(.34655,.91091,-.22403),(.27595,.12925,.95245)),
]
hull=bpy.data.objects['holo.001'];hp=parts(hull);remove_hull=set()
for index in range(1,5):
 for side,sign in [('Port',-1),('Starboard',1)]:
  name=f'SideBattery_{index}_{side}';p=bpy.data.objects[name];mesh=next(c for c in p.children if c.type=='MESH');M=inv@mesh.matrix_world;gunpts=np.array([list(M@v.co)for v in mesh.data.vertices]);center=gunpts.mean(0)
  mirror=np.diag([sign,1,1]);X=np.array(frames[index-1][0]);B=np.array(frames[index-1][1]);N=np.array(frames[index-1][2]);X=mirror@X*sign;B=mirror@B;B/=np.linalg.norm(B);X-=B*(X@B);X/=np.linalg.norm(X);N=np.cross(X,B);Q=np.stack([X,B,N],1)
  links=sorted([g for g in hp if g['n']==184 and np.sign(g['center'][0])==sign],key=lambda g:np.linalg.norm(g['center']-center))[:16]
  # Symmetric channel centre is the midpoint of its transverse bracket limits.
  lp=np.concatenate([g['points']for g in links]);C=lp.mean(0);q=(lp-C)@Q;C+=X*(q[:,0].max()+q[:,0].min())/2
  q=(lp-C)@Q;selected=[]
  for g in hp:
   if g['n']>=184 or np.linalg.norm(g['center']-C)>40:continue
   t=(g['points']-C)@Q;lo=t.min(0);hi=t.max(0)
   if lo[1]<q[:,1].min()-2.5 or hi[1]>q[:,1].max()+2.5:continue
   if lo[0]*hi[0]<=0 or min(abs(lo[0]),abs(hi[0]))<2.14 or max(abs(lo[0]),abs(hi[0]))>5.7:continue
   if lo[2]<q[:,2].min()-3 or hi[2]>q[:,2].max()+3:continue
   selected.append(g)
  remove_hull|=set().union(*(g['ids']for g in selected))
  noses=[]
  for g in hp:
   if g['n']!=18:continue
   t=(g['points']-C)@Q
   if t[:,1].min()>10 and t[:,1].min()<25 and abs(t[:,0].mean())<4 and abs(t[:,2].mean())<10:noses.append(g)
  nose=None
  if len(noses)==2:
   nose=fit_channel_nose(hull,noses,C,Q)
  shutters=channel_covers(name,C,Q,links,nose=nose)
  direction=bore(mesh,Vector(B));axis=direction.cross(Vector(N)).normalized();old=(inv@p.matrix_world).translation.copy();new=old+direction*7.5;move_origin(p,new)
  p['singleBattery']=True;p['hingeAxisModel']=list(axis);p['pitchDegrees']=23.;p['sourceBoreDirectionModel']=list(direction);p['outwardNormal']=N.tolist();p['trunnionAdvance']=7.5;p['stowSink']={1:0.,2:.45,3:.15,4:.15}[index]
  if 'deployQuaternion'in p:del p['deployQuaternion']
  report['singleBatteries'][name]={'trunnion':list(new),'axis':list(axis),'covers':shutters,'sourceCoverVertices':sum(len(g['ids'])for g in selected)}
remove(hull,remove_hull)

# Continue the real exterior hull plane through the small main-bay receiver.
# The underlap is hidden under the armor rim; the exposed surface is coplanar
# with the adjacent hull instead of the former rectangular vertical plug.
from mathutils.bvhtree import BVHTree
hull.data.calc_loop_triangles();hm=inv@hull.matrix_world;hi=hm.inverted();ht=BVHTree.FromPolygons([hm@v.co for v in hull.data.vertices],[tuple(t.vertices)for t in hull.data.loop_triangles],all_triangles=True)
bm=bmesh.new();bm.from_mesh(hull.data)
for ycut in [116.745,116.770]:
 selected=[]
 for face in bm.faces:
  ps=[hm@v.co for v in face.verts]
  if min(p.y for p in ps)<ycut<max(p.y for p in ps) and 10<min(abs(p.x)for p in ps)<15 and max(p.z for p in ps)>35:selected.append(face)
 geom=set(selected)
 for face in selected:geom.update(face.edges);geom.update(face.verts)
 bmesh.ops.bisect_plane(bm,geom=list(geom),dist=1e-6,plane_co=hi@Vector((0,ycut,0)),plane_no=hm.to_3x3().transposed()@Vector((0,1,0)),clear_inner=False,clear_outer=False)
bm.to_mesh(hull.data);bm.free();hull.data.update()
report['mainHullCorners']={}
for side,sign in [('Port',-1),('Starboard',1)]:
 samples=[]
 for x,y in [(14,116),(15,116),(14,118)]:
  hit,_,_,_=ht.ray_cast(Vector((sign*x,y,45)),Vector((0,0,-1)));assert hit is not None;samples.append(hit)
 a,b,c=np.linalg.solve(np.array([[p.x,p.y,1]for p in samples]),np.array([p.z for p in samples]));count=0
 for vert in hull.data.vertices:
  p=hm@vert.co
  if not(116.768<=p.y<=123 and 10.95<=sign*p.x<=14.1 and 35<p.z<42):continue
  plane=a*p.x+b*p.y+c
  if p.z<plane-3:continue
  rim=(-1.2393497078569466*11.123249053955078-.06942219204372839*p.y+62.20786261030588)if sign>0 else (1.2385092997145244*-11.123249053955078-.06458586233633538*p.y+61.41979689177092)
  p.z=min(plane,rim-.30);vert.co=hi@p;count+=1
 old=bpy.data.objects.get(f'MainBay_Dorsal_{side}_FixedReceiver')
 if old:bpy.data.objects.remove(old,do_unlink=True)
 report['mainHullCorners'][side]={'exteriorPlane':[float(a),float(b),float(c)],'vertices':count}
hull.data.update()

# Preserve the accepted receiving relief beneath the aft hinge. Extending the
# exposed hull plane must not fill the swept pocket under that moving leaf.
for side,sign in [('Port',-1),('Starboard',1)]:
 j=bpy.data.objects[f'Hatch_Dorsal_Aft_{side}'];a,b=map(Vector,j['hingeEdge']);n=Vector(j['planeNormal']);axis=Vector(j['hingeAxis'])
 opened=Quaternion(axis,math.radians(j['openingAngleDegrees']))@n
 for v in hull.data.vertices:
  p=hm@v.co
  if not a.y-1.2<p.y<min(b.y+1.2,116.746) or not 8<sign*p.x<18 or not 35<p.z<45:continue
  line=a+(p.y-a.y)/axis.y*axis;radius=sign*(p.x-line.x)
  if not -1.7<radius<2:continue
  closedz=a.z-(n.x*(p.x-a.x)+n.y*(p.y-a.y)+.235)/n.z
  openz=a.z-(opened.x*(p.x-a.x)+opened.y*(p.y-a.y))/opened.z-.07
  height=min(closedz,openz) if radius<.02 else openz
  weight=min(1,max(0,(2-radius)/.5),max(0,(radius+1.7)/.5))
  if height<p.z<height+3:p.z+=(height-p.z)*weight;v.co=hi@p
hull.data.update()

# Three axial singles use the same triangular, inward-closing cross section.
# Re-seat their upper bearings; the old 90-degree pose folded the leaves below
# the channel. No extra sinking or yaw is added to their barrel motion.
for station,gunname,forward,normal in [('Bow','odin.002',(0,1,0),(0,0,1)),('Stern','odin.026',(0,-1,0),(0,0,1)),('Keel','odin.029',(0,-1,0),(0,0,-1))]:
 p=bpy.data.objects[f'Axial_{station}_Barrel'];mesh=bpy.data.objects[gunname];direction=bore(mesh,Vector(forward));axis=direction.cross(Vector(normal)).normalized();old=(inv@p.matrix_world).translation.copy();new=old+direction*7.5;move_origin(p,new)
 p['singleBattery']=True;p['hingeAxisModel']=list(axis);p['pitchDegrees']=21.;p['sourceBoreDirectionModel']=list(direction);p['outwardNormal']=list(normal);p['trunnionAdvance']=7.5
 old=bpy.data.objects[f'Axial_{station}_Shutter_Port'];a=np.array(old['hingeAxis']);B=np.array([a[0],-a[2],a[1]]);B/=np.linalg.norm(B);X=np.array([1,0,0]);N=np.cross(X,B)
 if N@normal<0:X=-X;N=-N
 if B@forward<0:B=-B;X=-X
 Q=np.stack([X,B,N],1);container=bpy.data.objects['holo.022']if station=='Keel'else hull
 low,high={'Bow':(245,277),'Stern':(-272,-240),'Keel':(-77,-45)}[station]
 links=[g for g in parts(container)if (g['n']==184 if station!='Keel'else 900<g['n']<1250)and low<g['lo'][1]<high and max(abs(g['lo'][0]),abs(g['hi'][0]))<3.0]
 assert len(links)==15,(station,len(links));C=np.concatenate([g['points']for g in links]).mean(0)
 for leaf in ['Port','Starboard']:
  bpy.data.objects.remove(bpy.data.objects[f'Axial_{station}_ShutterMesh_{leaf}'],do_unlink=True);bpy.data.objects.remove(bpy.data.objects[f'Axial_{station}_Shutter_{leaf}'],do_unlink=True)
 noses=[]
 for g in parts(container):
  if g['n']!=28:continue
  t=(g['points']-C)@Q
  if 16<t[:,1].min()<21 and abs(t[:,0].mean())<4:noses.append(g)
 nose=fit_channel_nose(container,noses,C,Q)if len(noses)==2 else None
 channel_covers('Axial_'+station,C,Q,links,bpy.data.objects['Axial_Keel_Mount']if station=='Keel'else A,nose=nose)
 p['stowSink']=.35 if station=='Keel'else 0.
 report['singleBatteries'][p.name]={'trunnion':list(new),'axis':list(axis),'covers':[f'Axial_{station}_Shutter_{x}'for x in ['Port','Starboard']]}

# The quad's bearing, rail and four breech armor pieces stay on the gimbal.
# Only the source tube + inner sleeve telescope through them.
for side,sign in [('Port',-1),('Starboard',1)]:
 bpy.data.objects[f'PDC_{side}_Gimbal']['fixedRootArmorPieces']=4
 for i in range(4):
  mesh=bpy.data.objects[f'PDC_{side}_ArmMesh_{i}'];groups=parts(mesh);fixed=set().union(*(g['ids']for g in groups if g['n']in(450,104,205)))
  assert len(fixed)==759,(side,i,len(fixed))
  root=extract(mesh,f'PDC_{side}_RootArmor_{i}',fixed);keep(root,bpy.data.objects[f'PDC_{side}_Gimbal']);remove(mesh,fixed)
  p=bpy.data.objects[f'PDC_{side}_Arm_{i}'];p['stowTravel']=13.5
  report['quads'][p.name]={'staticRootVertices':len(fixed),'slidingVertices':len(mesh.data.vertices),'stowTravel':13.5}

# The eight true twin turrets use measured bore axes, including mirrored mounts.
# Positive elevation must point away from the deck on both sides.
for i in range(8):
 suffix='turret 1'+(f'.{i:03}'if i else '');mesh=bpy.data.objects['odin.072__'+suffix];prefix=f'Defense_{i+1:02}';p=bpy.data.objects[prefix+'_Elevation'];sign=bpy.data.objects[prefix+'_Carriage']['side'];direction=bore(mesh,Vector((sign,0,0)));axis=direction.cross(Vector((0,0,1))).normalized()
 p['hingeAxisModel']=list(axis);p['sourceBoreDirectionModel']=list(direction);p['pitchDegrees']=6.-math.degrees(math.asin(direction.z));p['targetElevationDegrees']=6.
 report['twins'][prefix]={'bore':list(direction),'axis':list(axis),'pitchDegrees':float(p['pitchDegrees'])}

# Four aft notch gates follow the original cut lip. Their moving face covers
# only the existing aperture, and slides below it before the carriage moves.
from mathutils.kdtree import KDTree
M=inv@hull.matrix_world;kd=KDTree(len(hull.data.vertices))
for vertex in hull.data.vertices:kd.insert(M@vertex.co,vertex.index)
kd.balance()
mouth=[(33.51,-175.07,45.70),(32.05,-185.91,45.80),(35.16,-186.35,42.61),(36.58,-175.79,42.38)]
for index,sign,aft in [(5,1,False),(6,1,True),(7,-1,False),(8,-1,True)]:
 pts=[]
 for x,y,z in mouth:
  seed=Vector((sign*(x-(6.384 if aft else 0)),y-(41.944 if aft else 0),z));co,_,distance=kd.find(seed);pts.append(co if distance<1.0 else seed)
 centre=sum(pts,Vector())/4;pts=[centre+(p-centre)*.992 for p in pts]
 # Keep the outward surface facing away from the ship.
 if (pts[1]-pts[0]).cross(pts[2]-pts[0]).x*sign<0:pts.reverse()
 j=joint(f'Defense_{index:02}_NotchGate',centre,system='defense-gate');j['slideVector']=[sign*3.9,-.55,-4.4];j['releaseVector']=[-sign*.15,0,-.14];j['carriage']=f'Defense_{index:02}_Carriage'
 prism(j.name+'_Skin',pts,.18,j)
 report['twins'][f'Defense_{index:02}']['gate']=j.name

# The rear armor face was still fused into the hull; only its roof/bottom
# guides had been animated. Recover the actual face and retain the guides as
# fixed hardware. Each upper/lower half follows the real window contour.
rear=next(g for g in parts(hull)if g['n']==875 and g['lo'][2]>125 and g['hi'][1]<-40)
rear_window=extract(hull,'BridgeWindow_RearFrame',rear['ids']);keep(rear_window,A)
for i,m in enumerate(list(rear_window.data.materials)):
 if m and 'Dark'in m.name:rear_window.data.materials[i]=bpy.data.materials['Odin_Bridge_Glazing']
rear_window.location.y+=.18
for bank in ['RearUpper','RearLower']:
 joints=sorted([o for o in s.objects if o.get('staticJoint')and o.get('bank')==bank],key=lambda o:(inv@o.matrix_world).translation.x)
 for i,j in enumerate(joints):
  old=next(c for c in j.children if c.type=='MESH');name=old.name;old.name='BridgeFixedGuide_'+name;keep(old,A)
  mesh=extract(hull,name,rear['ids']);M=inv@mesh.matrix_world;mesh.data.transform(M);mesh.parent=A;mesh.matrix_parent_inverse=Matrix.Identity(4);mesh.matrix_local=Matrix.Identity(4)
  bm=bmesh.new();bm.from_mesh(mesh.data)
  bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.normal.y>-.70 or f.normal.z>-.20 or f.calc_area()<.1],context='FACES')
  x0=-18.563+i*(37.126/15)+.014;x1=-18.563+(i+1)*(37.126/15)-.014
  x0=max(x0,-18.32);x1=min(x1,18.32)
  for co,no,inside in [((x0,0,0),(1,0,0),True),((x1,0,0),(1,0,0),False),((0,0,128.15),(0,0,1),bank=='RearUpper')]:
   bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=co,plane_no=no,clear_inner=inside,clear_outer=not inside)
  bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(mesh.data);bm.free();mesh.data.update()
  ps=[v.co for v in mesh.data.vertices];upper=bank=='RearUpper';z=max(p.z for p in ps)if upper else min(p.z for p in ps);edge=[p for p in ps if abs(p.z-z)<.12];y=min(p.y for p in edge)if upper else max(p.y for p in edge)
  move_origin(j,((x0+x1)/2,y-.60,z));keep(mesh,j);mesh.location.y-=.60
  mod=mesh.modifiers.new('Rear shield thickness','SOLIDIFY');mod.thickness=.08;mod.offset=-1;bpy.context.view_layer.objects.active=mesh;bpy.ops.object.modifier_apply(modifier=mod.name)
  j['closedGeometry']=True;j['parkPitch']=60.
remove(hull,rear['ids'])

# A common crosshead carries the front louvers on two roof tracks. It keeps
# the lifted hinge row visibly connected to the bridge through the stroke.
front=bpy.data.objects['BridgeArmor_Front_07'];origin=(inv@front.matrix_world).translation
for sign in [-1,1]:
 x=sign*18.7;path=[(origin.y,origin.z),(origin.y+.9,origin.z+1.4),(origin.y+.9-8.2,origin.z+1.4)]
 for k,((y0,z0),(y1,z1))in enumerate(zip(path,path[1:])):
  direction=Vector((0,y1-y0,z1-z0)).normalized();across=Vector((0,-direction.z,direction.y))*.065
  a=Vector((x,y0,z0));b=Vector((x,y1,z1));prism(f'BridgeFixedGuide_FrontTrack_{sign}_{k}',[a-across,b-across,b+across,a+across],.10,A,light,light)
cross=[Vector((x,origin.y+y+.4,origin.z+.03))for x,y in [(-18.8,-.09),(18.8,-.09),(18.8,.09),(-18.8,.09)]]
prism('BridgeArmor_Front_Crosshead',cross,.14,front,light,light)

# Warm charcoal tower armor, with original orange/white markings retained.
tower=palette('Odin_Bridge_Armor',light,(.34,.327,.307),.16,.69)
trim=palette('Odin_Bridge_Trim',bpy.data.materials['Odin_Paint_Dark.001'],(.245,.242,.232),.22,.62)
for obj in s.objects:
 if obj.type!='MESH' or obj.name.startswith(('Main_','Hatch_','MainBay','odin.00','odin.01','odin.02','odin.07','PDC_')):continue
 if obj.name.startswith(('BridgeArmor_','BridgeFixedGuide_')) or obj.name in ['Cube','Cube.001','Cylinder','Cylinder.001']:
  for i,m in enumerate(list(obj.data.materials)):
   if m and m.name.startswith('Odin_Paint_') and 'Orange'not in m.name and 'White'not in m.name:obj.data.materials[i]=trim if 'Dark'in m.name else tower
 elif obj==hull:
  M=inv@obj.matrix_world;ti=len(obj.data.materials);obj.data.materials.append(tower);di=len(obj.data.materials);obj.data.materials.append(trim)
  for f in obj.data.polygons:
   ps=[M@obj.data.vertices[i].co for i in f.vertices];c=sum(ps,Vector())/len(ps);m=obj.data.materials[f.material_index]
   if m and m.name.startswith('Odin_Paint_') and 'Orange'not in m.name and 'White'not in m.name and min(p.z for p in ps)>54 and -168<c.y<-18 and abs(c.x)<(61 if c.z>102 else 38):f.material_index=di if 'Dark'in m.name else ti
glass=bpy.data.materials['Odin_Bridge_Glazing'];glass.diffuse_color=(.26,.17,.068,1);p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.26,.17,.068,1);p.inputs['Roughness'].default_value=.16;p.inputs['Metallic'].default_value=.65;p.inputs['Emission Strength'].default_value=0;p.inputs['Coat Weight'].default_value=.7;p.inputs['Coat Roughness'].default_value=.12
# Glass belongs only to window faces, not the copied roof and lower skirt.
for name,sign in [('BridgeWindow_SourceFrame',1),('BridgeWindow_RearFrame',-1)]:
 obj=bpy.data.objects[name];gi=len(obj.data.materials);obj.data.materials.append(tower)
 for f in obj.data.polygons:
  if f.normal.y*sign<.5 or f.normal.z>-.20:f.material_index=gi
# The old front leaf incorrectly included the fixed horizontal sill. Extract
# only its angled shield face, then give it its own constant-gauge return.
for obj in list(s.objects):
 if obj.type=='MESH'and obj.name.startswith('BridgeArmor_Front_Mesh_'):
  bm=bmesh.new();bm.from_mesh(obj.data);normal=max(bm.faces,key=lambda f:f.calc_area()).normal.copy()
  if normal.y<.65:normal=Vector((0,.794,-.608))
  bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.normal.dot(normal)<.992 or f.calc_area()<.15],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(obj.data);bm.free();obj.data.update()
  mod=obj.modifiers.new('Shield thickness','SOLIDIFY');mod.thickness=.10;mod.offset=-1;bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)
  obj.location.y+=.16
# Retraction first lifts clear of the roof, folds outside the glazing, then
# parks on the roof guides. These are metadata for the JS runtime.
for obj in s.objects:
 if not obj.get('staticJoint') or not obj.name.startswith('BridgeArmor_'):continue
 if obj.get('bank')=='Front':obj['parkLift']=1.4;obj['parkSlide']=8.2;obj['parkPitch']=127.
 else:obj['outboardRelease']=.22
report['bridge']={'frontShields':15,'rearShields':30,'frontParkLift':1.4,'frontParkPitch':127,'glass':'warm gold / tea tint','towerPalette':[.34,.327,.307]}
for obj in s.objects:obj.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
A['version']='0.9.0';s.name='ODIN v0.9.0 — single batteries, twin mechanisms and bridge'
(out/'geometry-build.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.context.view_layer.update()
basis=Matrix.Rotation(-math.pi/2,4,'X');nodes=[]
for obj in [A]+[o for o in s.objects if o.get('staticJoint')]:
 props={k:obj[k]for k in obj.keys()};mat=basis@obj.matrix_local@basis.inverted()
 nodes.append({'name':obj.name,'parent':obj.parent.name if obj.parent else None,'matrix':[mat[r][c]for c in range(4)for r in range(4)],'extras':props})
(out/'rig-nodes.json').write_text(json.dumps(nodes,default=lambda x:list(x)),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.9.0.blend'),compress=True)
print('SAVED v0.9.0 STATIC GEOMETRY',flush=True)
