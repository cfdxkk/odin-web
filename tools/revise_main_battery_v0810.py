"""Fit main-bay junctions, real edge hinges and finite-thickness armor.

Read the immutable v0.8.8 geometry. All poses remain authored in JavaScript;
save a new v0.8.10 source, never the original odin.blend.
"""
import bpy,bmesh,json,math,hashlib
from pathlib import Path
from collections import Counter
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/blender/odin_articulated_v0.8.8.blend'
OUT=ROOT/'assets/blender/odin_articulated_v0.8.10.blend'
assert Path(bpy.data.filepath).resolve()==BASE.resolve()
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
paint=bpy.data.materials['Odin_Paint_Light'];red=bpy.data.materials['Odin_Turret_Interior_DeepRed']
THICKNESS=.12
report={'version':'0.8.10','baseline':BASE.name,'armorThickness':THICKNESS,'parts':{},'junctions':{},'interiors':{}}

def points(obj):return [(inv@obj.matrix_world)@v.co for v in obj.data.vertices]
def normal_matrix(obj):return (inv@obj.matrix_world).to_3x3().inverted().transposed()
def mesh_object(name,vertices,faces,parent,materials=(paint,red)):
 old=bpy.data.objects.get(name)
 if old:bpy.data.objects.remove(old,do_unlink=True)
 me=bpy.data.meshes.new(name);ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob);ob.parent=parent;bpy.context.view_layer.update()
 mi=(inv@ob.matrix_world).inverted();me.from_pydata([mi@v for v in vertices],[],faces);me.update()
 for material in materials:me.materials.append(material)
 return ob

def shell(obj,vertices,faces,thickness=THICKNESS,bevel=.19,depths=None,bevels=None):
 """Preserve the outer skin; build a bounded inner offset and beveled rim.

 Area-weighted normals avoid Solidify's unbounded miters on the source's
 extremely narrow seam triangles. Thickness is specified in asset units.
 """
 faces=[tuple(f) for f in faces if len(f)>=3]
 if obj.name.endswith(('_FittedSkin','_Wedge')):
  direction=1 if 'Dorsal' in obj.name else -1
  faces=[tuple(reversed(f)) if (vertices[f[1]]-vertices[f[0]]).cross(vertices[f[2]]-vertices[f[0]]).z*direction<0 else f for f in faces]
 normals=[Vector() for _ in vertices];perimeter={};valid=[]
 for f in faces:
  cross=sum(((vertices[f[i]]-vertices[f[0]]).cross(vertices[f[i+1]]-vertices[f[0]]) for i in range(1,len(f)-1)),Vector())
  if cross.length<1e-8:continue
  valid.append(f)
  for i in f:normals[i]+=cross
  for a,b in zip(f,f[1:]+f[:1]):perimeter.setdefault(tuple(sorted((a,b))),[]).append((a,b,cross.normalized()))
 inward={};boundary=[]
 for entries in perimeter.values():
  if len(entries)!=1:continue
  a,b,normal=entries[0];boundary.append((a,b));edge=(vertices[b]-vertices[a]).normalized();n=normal.cross(edge).normalized()
  inward.setdefault(a,[]).append(n);inward.setdefault(b,[]).append(n)
 inner=[]
 for i,p in enumerate(vertices):
  n=normals[i].normalized();q=p-n*(depths[i] if depths else thickness);rim=bevels[i] if bevels else bevel
  if i in inward:
   ns=inward[i];v=sum(ns,Vector()).normalized();v-=n*v.dot(n)
   if v.length>1e-6:
    v.normalize();q+=v*min(rim/max(min(v.dot(k) for k in ns),.25),rim*2)
  if obj.name.startswith('Hatch_Dorsal_') and obj.name.endswith('_FittedSkin') and p.y<117 and abs(p.x)<9.3:
   q+=Vector((0,.40,-.027))
  inner.append(q)
 count=len(vertices);allfaces=valid+[tuple(i+count for i in reversed(f))for f in valid]+[(b,a,a+count,b+count)for a,b in boundary]
 mi=(inv@obj.matrix_world).inverted();me=bpy.data.meshes.new(obj.name+'_SolidArmor');me.from_pydata([mi@v for v in vertices+inner],[],allfaces);me.materials.append(paint);me.materials.append(red);me.update();obj.data=me
 for f in me.polygons:f.material_index=1 if len(valid)<=f.index<2*len(valid) else 0;f.use_smooth=False
 obj['armorThickness']=thickness

aft_planes={}
for bank,direction in [('Dorsal',1),('Ventral',-1)]:
 for side,sign in [('Port',-1),('Starboard',1)]:
  name=f'Hatch_{bank}_Aft_{side}';joint=bpy.data.objects[name];ob=bpy.data.objects[name+'_GapFiller']
  coords=list(joint['closedOutlineXY']);count=len(coords)//2;normal=Vector(joint['planeNormal']).normalized();anchor=points(ob)[0]
  def planar(x,y):return Vector((x,y,anchor.z-(normal.x*(x-anchor.x)+normal.y*(y-anchor.y))/normal.z))
  free=[planar(x,y) for x,y in coords[:count]];outside=[planar(x,y) for x,y in reversed(coords[count:])]
  line_start,line_end=outside[0],outside[-1]
  outside=[line_start.lerp(line_end,(p.y-line_start.y)/(line_end.y-line_start.y))for p in outside]
  if bank=='Dorsal':
   skin=bpy.data.objects[f'Hatch_{bank}_{side}_FittedSkin'];sp=points(skin)[:len(skin.data.vertices)//2]
   candidates=[p for p in sp if p.y<117 and sign*p.x>8.7];u=min(candidates,key=lambda p:p.y);toe=max(candidates,key=lambda p:sign*p.x)
   trimmed_free=[];trimmed_outer=[]
   for p,c in zip(free,outside):
    if p.y>112:
     x=u.x+(p.y+.01-u.y)*(toe.x-u.x)/(toe.y-u.y)
     if sign*x>sign*p.x:p=planar(x,p.y)
    if sign*p.x>=sign*c.x-.003:break
    trimmed_free.append(p);trimmed_outer.append(c)
   free,outside=trimmed_free,trimmed_outer
  else:
   free,outside=free[:-3],outside[:-3]
  count=len(free)
  start,end=outside[0],outside[-1];edge=[];top=[];depths=[];bevels=[]
  for a,b in zip(free,outside):
   t=(b.y-start.y)/(end.y-start.y);c=start.lerp(end,t);edge.append(c);width=(c-a).length;tip=min(1,max(0,(end.y-b.y)/1.2));body=.02+.10*tip;top.extend([a,a.lerp(c,.5),c]);depths.extend([.025,min(body,.025+width*.12),body]);bevels.extend([min(.22,width*.18),0,min(.06,width*.15)])
  fs=[]
  for r in range(count-1):
   for j in [0,1]:
    f=(3*r+j,3*r+j+1,3*r+j+4,3*r+j+3)
    if (top[f[1]]-top[f[0]]).cross(top[f[2]]-top[f[0]]).dot(normal)<0:f=tuple(reversed(f))
    fs.append(f)
  shell(ob,top,fs,bevel=.22,depths=depths,bevels=bevels)
  # The axle runs through the actual straight material attachment edge.
  a=start.copy();b=end.copy();axis=(b-a).normalized()
  old=joint.location.copy();world=ob.matrix_world.copy();joint.location=a;bpy.context.view_layer.update();ob.matrix_world=world;bpy.context.view_layer.update()
  joint['hingeEdge']=[list(a),list(b)];joint['hingeAxis']=list(axis);joint['planeNormal']=list(normal)
  joint['closedOutlineXY']=[[v.x,v.y]for v in free+list(reversed(edge))]
  joint['hingeSurfaceEdge']=[list(start),list(end)];joint['armorThickness']=THICKNESS
  joint['sourceReference']='Fixed axle through the physical straight lower edge of the planar armor, not a parallel offset pivot'
  report['parts'][name]={'oldPivot':list(old),'pivot':list(a),'hingeEdge':[list(a),list(b)],'planeNormal':list(normal),'thickness':THICKNESS,'maximumOuterBoundaryAdjustment':max((a-b).length for a,b in zip(edge,outside))}
  aft_planes[bank,side]=(normal,anchor,free,edge)

# Thicken the six translating skins without touching their outside planes,
# serrations, ribs or static guide metadata.
def thicken_matched_skin(ob,ps,exterior,direction):
 """Keep fitted mating rims, with thicker inset fields and a small bevel.

 Every original seam vertex stays exactly where it was. Added face-centre
 vertices give the plate real body without forcing its thickness through the
 already fitted neighboring armor or fixed serrated receiver.
 """
 count=len(ps)//2;ec=Counter()
 for f in exterior:
  for a,b in zip(f,f[1:]+f[:1]):ec[tuple(sorted((a,b)))]+=1
 boundary=[e for e,c in ec.items()if c==1]
 def dist(p,a,b):
  e=b-a;t=max(0,min(1,(p-a).dot(e)/max(e.length_squared,1e-12)));return (p-a-e*t).length
 top=[p.copy()for p in ps[:count]];inner=[p.copy()for p in ps[count:]];tris=[];depths=[]
 for f in exterior:
  c=sum((top[i]for i in f),Vector())/len(f);old=sum((inner[i]for i in f),Vector())/len(f)
  distance=min(dist(c,top[a],top[b])for a,b in boundary);weight=max(0,min(1,(distance-.30)/.65))
  depth=abs(c.z-old.z);new_depth=depth+max(0,.18-depth)*weight
  inner.append(old-Vector((0,0,direction*(new_depth-depth))));ci=len(top);top.append(c);depths.append(new_depth)
  for a,b in zip(f,f[1:]+f[:1]):tris.append((a,b,ci))
 n=len(top);faces=tris+[tuple(i+n for i in reversed(f))for f in tris]+[(b,a,a+n,b+n)for a,b in boundary]
 me=bpy.data.meshes.new(ob.name+'_MatchedThickSkin');mi=(inv@ob.matrix_world).inverted();me.from_pydata([mi@p for p in top+inner],[],faces);me.materials.append(paint);me.materials.append(red);me.update();ob.data=me
 for f in me.polygons:f.material_index=1 if len(tris)<=f.index<2*len(tris) else 0;f.use_smooth=False
 ob['armorThickness']=.18;ob['matingRim']='Retained fitted rim with inward bevel to the thicker field'
 return min(depths),max(depths)

for bank,direction in [('Dorsal',1),('Ventral',-1)]:
 for role,suffix in [('Port','FittedSkin'),('Starboard','FittedSkin'),('Nose','Wedge')]:
  ob=bpy.data.objects[f'Hatch_{bank}_{role}_{suffix}'];ps=points(ob);nm=normal_matrix(ob)
  # The source uses corresponding exterior/interior vertex layers. Selecting
  # by normal alone also takes sloping rim faces, producing folded shell ends.
  exterior=[tuple(f.vertices) for f in ob.data.polygons if max(f.vertices)<len(ps)//2]
  assert exterior
  used=sorted({i for f in exterior for i in f});mapping={i:k for k,i in enumerate(used)}
  depths=thicken_matched_skin(ob,ps,exterior,direction)
  report['parts'][ob.name]={'bodyThickness':depths,'outerVerticesPreserved':len(used),'matingRimPreserved':True}
  if bank=='Dorsal' and role!='Nose':bpy.data.objects[f'Hatch_{bank}_{role}']['clearanceLift']=[0,0,.30]

# The blue-marked wedge is a rear return of the translating skin. Its bottom
# follows the inclined aft armor; it cannot belong to the hinged aft flap.
for side,sign in [('Port',-1),('Starboard',1)]:
 main=bpy.data.objects[f'Hatch_Dorsal_{side}'];skin=bpy.data.objects[main.name+'_FittedSkin'];ps=points(skin)
 # Use the unchanged exterior rear corner, where the old plane left an open
 # triangular window above the earlier, lower aft filler.
 topids=range(len(ps)//2)
 candidates=[ps[i]for i in topids if ps[i].y<117 and sign*ps[i].x>8.7]
 upper=min(candidates,key=lambda p:p.y);toe=max(candidates,key=lambda p:sign*p.x)
 normal,anchor,free,edge=aft_planes['Dorsal',side]
 def z(x,y):return anchor.z-(normal.x*(x-anchor.x)+normal.y*(y-anchor.y))/normal.z
 lower1=Vector((toe.x,toe.y,z(toe.x,toe.y)+.055))
 da=upper.z-z(upper.x,upper.y)-.055;db=toe.z-lower1.z
 if da<0:upper=upper.lerp(toe,-da/(db-da))
 # The short return is planar; its rim closes the visible height difference.
 wall=[upper,toe,lower1]
 wall=[p+Vector((0,.10,-.0067))for p in wall]
 n=(toe-upper).cross(lower1-upper).normalized()
 if n.x*sign<0:wall.reverse()
 ob=mesh_object(main.name+'_RearReturn',wall,[tuple(range(3))],main);shell(ob,wall,[tuple(range(3))],.035,bevel=.02)
 ob['junctionRole']='blue-moving-rear-return'
 report['junctions'][side]={'movingReturn':[list(p)for p in wall]}

 # The red-marked wedge is an immobile extension of the existing receiving
 # hull lip. The top follows the accepted main-side plane, with a narrow seam
 # under its finite thickness; the outside meets the original hull surface.
 # No face of this receiver is parented to an animated joint.
 hull=bpy.data.objects['holo.001'];hm=inv@hull.matrix_world;hi=hm.inverted()
 outer_next=min((p for p in ps[:len(ps)//2] if p.y>130 and sign*p.x>10.9),key=lambda p:p.y)
 plane_face=max((f for f in skin.data.polygons if f.material_index==0 and (normal_matrix(skin)@f.normal).x*sign>.5 and (normal_matrix(skin)@f.normal).z>.3),key=lambda f:f.area)
 pn=(normal_matrix(skin)@plane_face.normal).normalized();pa=ps[plane_face.vertices[0]]
 def cover_z(x,y):return pa.z-(pn.x*(x-pa.x)+pn.y*(y-pa.y))/pn.z
 receiver=[];nrows=33
 for i in range(nrows):
  y=toe.y+.035+i*(121.8-toe.y-.035)/(nrows-1)
  x=toe.x+(outer_next.x-toe.x)*(y-toe.y)/(outer_next.y-toe.y)
  # A fixed underlapping return closes the red-marked region from the
  # side. It sits inboard of the moving blue return so that the latter can
  # slide forward and out without passing through a solid receiving wedge.
  xx=x-sign*.60;hit,p,_,_=hull.ray_cast(hi@Vector((xx,y,60)),hi.to_3x3()@Vector((0,0,-1)))
  assert hit
  bottom=hm@p;bottom.z-=.04
  top=Vector((xx,y,cover_z(x,y)-.075));receiver.extend([bottom,top])
 fs=[]
 for i in range(nrows-1):
  f=(2*i,2*i+1,2*i+3,2*i+2)
  if (receiver[f[1]]-receiver[f[0]]).cross(receiver[f[2]]-receiver[f[0]]).x*sign<0:f=tuple(reversed(f))
  fs.append(f)
 ob=mesh_object(f'MainBay_Dorsal_{side}_FixedReceiver',receiver,fs,asset);shell(ob,receiver,fs,.12)
 ob['junctionRole']='red-fixed-hull-receiver';ob['fixedHull']='holo.001'
 report['junctions'][side]['fixedReceiver']={'name':ob.name,'animated':False,'rearY':receiver[0].y,'frontY':receiver[-1].y,'vertices':len(receiver)}

# Machine only the narrow, fixed receiving shoulder beside each real hinge.
# The original sheets had no room for a physical edge; their offset pivots
# concealed that problem. The local recess follows one straight plane and
# keeps the hull continuous while the plate turns about its material edge.
for bank,direction,hull_name in [('Dorsal',1,'holo.001'),('Ventral',-1,'holo.013')]:
 hull=bpy.data.objects[hull_name];hm=inv@hull.matrix_world;hmi=hm.inverted();hinges=[]
 for side,sign in [('Port',-1),('Starboard',1)]:
  j=bpy.data.objects[f'Hatch_{bank}_Aft_{side}'];a,b=map(Vector,j['hingeEdge']);n=Vector(j['planeNormal']);q=Quaternion(Vector(j['hingeAxis']),math.radians(j['openingAngleDegrees']));on=q@n
  floor_point=a-Vector((0,0,direction*.10))
  hinges.append((side,sign,a,b,on,floor_point))
 ylo=min(h[2].y for h in hinges)-.8;yhi=max(h[3].y for h in hinges)+1.3
 def eligible(pts):
  return max(p.y for p in pts)>ylo and min(p.y for p in pts)<yhi and min(abs(p.x) for p in pts)<19 and max(abs(p.x) for p in pts)>8 and max(p.z*direction for p in pts)>(30 if bank=='Dorsal' else 44)
 bm=bmesh.new();bm.from_mesh(hull.data)
 for axis,coordinates in [(1,[ylo,yhi]+list(range(math.ceil(ylo),math.floor(yhi)+1))),(0,[s*x*.5 for s in [-1,1]for x in range(16,39)])]:
  for coordinate in coordinates:
   selected=[]
   for f in bm.faces:
    ps=[hm@v.co for v in f.verts]
    if eligible(ps) and min(p[axis]for p in ps)<coordinate<max(p[axis]for p in ps):selected.append(f)
   if not selected:continue
   geom=set(selected)
   for f in selected:geom.update(f.edges);geom.update(f.verts)
   p=Vector();p[axis]=coordinate;n=Vector();n[axis]=1
   bmesh.ops.bisect_plane(bm,geom=list(geom),dist=1e-6,plane_co=hmi@p,plane_no=hm.to_3x3().transposed()@n,clear_inner=False,clear_outer=False)
 bm.to_mesh(hull.data);bm.free();hull.data.update();changed=[]
 for v in hull.data.vertices:
  p=hm@v.co
  for side,sign,a,b,n,fp in hinges:
   if not a.y-.65<p.y<b.y+1.1:continue
   t=(p.y-a.y)/(b.y-a.y);axis=a.lerp(b,t);outboard=sign*(p.x-axis.x)
   if not -1.5<outboard<4.5:continue
   z=fp.z-(n.x*(p.x-fp.x)+n.y*(p.y-fp.y))/n.z;depth=(p.z-z)*direction
   if 0<depth<2.6:
    q=p.copy();q.z=z;v.co=hmi@q;changed.append({'before':list(p),'after':list(q)});break
 hull.data.update();report.setdefault('hingeReceivers',{})[bank]={'modifiedVertices':len(changed),'maxDepth':max((abs(c['after'][2]-c['before'][2])for c in changed),default=0)}

# Give the thicker fields a matching internal recess. The perimeter of the
# fixed hull remains fitted to the original rim; only material underneath the
# closed moving covers is relieved, inside the existing main-bay aperture.
hull=bpy.data.objects['holo.001'];hm=inv@hull.matrix_world;hmi=hm.inverted();covers=[]
for role,suffix in [('Port','FittedSkin'),('Starboard','FittedSkin'),('Nose','Wedge')]:
 o=bpy.data.objects[f'Hatch_Dorsal_{role}_{suffix}'];ps=points(o);n=len(ps)//2;ec=Counter()
 for f in o.data.polygons:
  if max(f.vertices)>=n:continue
  ids=list(f.vertices)
  for a,b in zip(ids,ids[1:]+ids[:1]):ec[tuple(sorted((a,b)))]+=1
 boundary=[(ps[a],ps[b])for(a,b),c in ec.items()if c==1];m=inv@o.matrix_world;covers.append((o,m,m.inverted(),boundary))
recessed=0
for v in hull.data.vertices:
 p=hm@v.co
 if not 112<p.y<169 or abs(p.x)>15 or p.z<32:continue
 for o,m,mi,edges in covers:
  inside=False;distance=1e9
  for a,b in edges:
   if (a.y>p.y)!=(b.y>p.y) and p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x:inside=not inside
   dx=b.x-a.x;dy=b.y-a.y;t=max(0,min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/max(dx*dx+dy*dy,1e-15)));distance=min(distance,math.hypot(p.x-a.x-dx*t,p.y-a.y-dy*t))
  if not inside or distance<.08:continue
  hit,q,_,_=o.ray_cast(mi@Vector((p.x,p.y,65)),mi.to_3x3()@Vector((0,0,-1)))
  if not hit:continue
  q=m@q;weight=max(0,min(1,(distance-.08)/.25));z=q.z-.10-.22*weight
  if z<p.z<q.z+.2:
   p.z=z;v.co=hmi@p;recessed+=1;break
hull.data.update();report['internalFieldReceiverVertices']=recessed

# Repaint the existing fore cavity wall from inside the bay. The outer lip
# and upper hull stay grey; these are inward, rear-facing wall polygons.
for bank,name,direction,y0,y1,z0,z1 in [('Dorsal','holo.001',1,150,174,30,49),('Ventral','holo.013',-1,99,123,-62,-38)]:
 ob=bpy.data.objects[name];me=ob.data;m=inv@ob.matrix_world;nm=normal_matrix(ob)
 if red not in list(me.materials):me.materials.append(red)
 ri=list(me.materials).index(red);selected=[]
 for f in me.polygons:
  c=m@f.center;n=(nm@f.normal).normalized()
  if y0<c.y<y1 and z0<c.z<z1 and abs(c.x)<12 and (n.y<-.18 or n.x*c.x<-2) and n.z*direction<.8:
   f.material_index=ri;selected.append(f.index)
 report['interiors'][name]={'foreWallFaces':selected}

assert not bpy.data.actions
asset['version']='0.8.10';bpy.context.scene.name='ODIN v0.8.10 - fitted physical armor joints'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
report['blendSha256']=hashlib.sha256(OUT.read_bytes()).hexdigest()
path=ROOT/'work/v0810-review/geometry-build.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf8')
print('SAVED',OUT,flush=True)
