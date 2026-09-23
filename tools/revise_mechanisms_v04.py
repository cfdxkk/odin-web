"""Repair the static joints using original Odin geometry and CIG exterior references.

Run on assets/blender/odin_articulated_v0.3.0.blend. The original odin.blend
is opened as a read-only library, never saved. All motion remains in Nuxt.
"""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion,Euler
root=Path(__file__).resolve().parents[1];s=bpy.context.scene
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
light=bpy.data.materials['Odin_Paint_Light'];steel=bpy.data.materials['Odin_Added_Machined_Alloy']

def pivot(name,pos,parent=asset,system=''):
 o=bpy.data.objects.new(name,None);s.collection.objects.link(o);o.parent=parent;o.location=pos;o['staticJoint']=True;o['system']=system;return o
def keep(o,p):
 bpy.context.view_layer.update();m=o.matrix_world.copy();o.parent=p;o.matrix_world=m
def islands(o):
 m=o.data;p=list(range(len(m.vertices)));M=inv@o.matrix_world
 def find(i):
  while p[i]!=i:p[i]=p[p[i]];i=p[i]
  return i
 for e in m.edges:a,b=e.vertices;p[find(a)]=find(b)
 groups={}
 for v in m.vertices:groups.setdefault(find(v.index),[]).append(v.index)
 result=[]
 for ids in groups.values():
  pts=[M@m.vertices[i].co for i in ids]
  result.append(dict(ids=set(ids),n=len(ids),lo=Vector([min(v[k] for v in pts) for k in range(3)]),hi=Vector([max(v[k] for v in pts) for k in range(3)])))
 return result
def extract(o,name,ids):
 cp=o.copy();cp.data=o.data.copy();s.collection.objects.link(cp);cp.name=name
 bm=bmesh.new();bm.from_mesh(cp.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS');bm.to_mesh(cp.data);bm.free();cp.data.update();return cp
def remove(o,ids):
 bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index in ids],context='VERTS');bm.to_mesh(o.data);bm.free();o.data.update()
def clip_x(o,low,high):
 # Clip real source faces at their panel seams, retaining their UV coordinates.
 M=inv@o.matrix_world;o.data.transform(M);o.parent=asset;o.matrix_local=Matrix.Identity(4)
 bm=bmesh.new();bm.from_mesh(o.data)
 for x,positive in [(low,False),(high,True)]:
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(x,0,0),plane_no=(1,0,0),clear_inner=not positive,clear_outer=positive)
 bm.to_mesh(o.data);bm.free();o.data.update()
def solid(name,pts,parent,thickness,mat=light):
 n=len(pts);verts=pts+[tuple(Vector(p)+Vector(thickness)) for p in pts]
 faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);s.collection.objects.link(o);o.parent=asset;o.data.materials.append(mat)
 mod=o.modifiers.new('Edge finish','BEVEL');mod.width=.07;mod.segments=2;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name);keep(o,parent);return o

# Remove the misplaced broad replacement covers and protruding bay decorations.
for o in list(s.objects):
 if o.name.startswith(('Hatch_','SternDoor','SternHangarDoor','MainBayRib_','MainBayLamp_')) or '_FixedGuide_' in o.name:
  bpy.data.objects.remove(o,do_unlink=True)
# The forward hatch starts in front of the gun housing, not over its shrouds.
# Two continuous leaf banks with overlapping ribs hinge outwards along the deck.
for bank,y0,z0,direction in [('Dorsal',114.5,48.0,1),('Ventral',65.0,-62.0,-1)]:
 length=52.;slope=-direction*.174
 for side,sign in [('Port',-1),('Starboard',1)]:
  p=pivot(f'Hatch_{bank}_{side}',(sign*12.55,y0+length/2,z0+slope*length/2),system='main-hatch')
  axis=Vector((0,1,slope)).normalized();p['hingeAxis']=[axis.x,axis.z,-axis.y];p['openingSign']=-sign*direction
  for i in range(10):
   a=y0+i*length/10;b=a+length/10-.12
   pts=[(sign*.04,a,z0+slope*(a-y0)),(sign*12.55,a,z0+slope*(a-y0)),(sign*12.55,b,z0+slope*(b-y0)),(sign*.04,b,z0+slope*(b-y0))]
   solid(f'Hatch_{bank}_{side}_Rib_{i:02}',pts,p,(0,0,-direction*1.1))

# Preserve the original barrels; isolate just the telescopic outer tubes from
# their breeches. The center tube does not telescope.
for bank,name,direction in [('Dorsal','odin.004',1),('Ventral','odin.012',-1)]:
 o=bpy.data.objects[name];parts=islands(o);selected=set()
 for side,sign in [('Port',-1),('Starboard',1)]:
  ids=set()
  for g in parts:
   if (g['lo'].x>4 if sign>0 else g['hi'].x<-4) and g['hi'].y>(120 if bank=='Dorsal' else 70) and g['lo'].y>(107 if bank=='Dorsal' else 57):ids|=g['ids']
  assert ids,(bank,side)
  tube=extract(o,f'Main_{bank}_TubeMesh_{side}',ids)
  p=pivot(f'Main_{bank}_Tube_{side}',(0,0,0),bpy.data.objects[f'Main_{bank}_Barrels'],'main-telescope');keep(tube,p);selected|=ids
 remove(o,selected)

# The axial shutters' skins and fifteen bearing/link groups are merged into the
# hull/cradle. Separate the skins and derive their hinges from the fixed links.
hull=bpy.data.objects['holo.001'];hull_parts=islands(hull);to_remove=set()
for station,obj in [('Bow',hull),('Stern',hull),('Keel',bpy.data.objects['holo.022'])]:
 parts=hull_parts if obj==hull else islands(obj);chosen=[]
 for g in parts:
  lo,hi=g['lo'],g['hi']
  if max(abs(lo.x),abs(hi.x))>3.0 or hi.x-lo.x<5:continue
  if station=='Bow' and g['n']==184 and 245<lo.y<277:chosen.append(g)
  if station=='Stern' and g['n']==184 and -272<lo.y<-240:chosen.append(g)
  if station=='Keel' and 900<g['n']<1250 and -77<lo.y<-45:chosen.append(g)
 assert len(chosen)==15,(station,len(chosen))
 ids=set();centers=sorted([(g['lo']+g['hi'])/2 for g in chosen],key=lambda v:v.y)
 slope=(centers[-1].z-centers[0].z)/(centers[-1].y-centers[0].y);mid=(centers[-1]+centers[0])/2
 # Keep the original links/bearings in the channel. Only the vented outer armor
 # skins fold over them; rotating the links with the skins produces protruding teeth.
 for g in parts:
  lo,hi=g['lo'],g['hi'];outer=max(abs(lo.x),abs(hi.x));inner=min(abs(lo.x),abs(hi.x))
  if not (lo.x*hi.x>0 and inner>2.28 and outer<5.30):continue
  if station=='Bow' and 245<lo.y and hi.y<272 and g['n']<150:ids|=g['ids']
  if station=='Stern' and -272<lo.y and hi.y<-240 and g['n']<150:ids|=g['ids']
  if station=='Keel' and -77<lo.y and hi.y<-45 and g['n']<700:ids|=g['ids']
 parent=bpy.data.objects['Axial_Keel_Mount'] if station=='Keel' else asset
 for side,sign in [('Port',-1),('Starboard',1)]:
  assert ids,station
  leaf=extract(obj,f'Axial_{station}_ShutterMesh_{side}',ids);clip_x(leaf,0 if sign>0 else -100,100 if sign>0 else 0)
  # Outer source edge, centered on the sloping shutter's bearing line.
  width=max(g['hi'].x for g in chosen)
  # Source rib's upper inner attachment is the fixed bearing; its outside skin
  # hangs down beside the channel when open. It folds inward to close over it.
  inner_height=(max(g['hi'].z-slope*((g['lo'].y+g['hi'].y)/2-mid.y) for g in chosen) if station!='Keel' else min(g['lo'].z-slope*((g['lo'].y+g['hi'].y)/2-mid.y) for g in chosen))
  hinge=Vector((sign*width,mid.y,inner_height))
  p=pivot(f'Axial_{station}_Shutter_{side}',hinge,system='axial-shutter');keep(p,parent);keep(leaf,p)
  axis=Vector((0,1,slope)).normalized();p['hingeAxis']=[axis.x,axis.z,-axis.y];p['openingSign']=sign*(-1 if station=='Keel' else 1)
 if obj==hull:to_remove|=ids
 else:remove(obj,ids)

# The large front shield itself was still fused into the hull. Moving only its
# roof runners left that stationary shield covering the glazing in every mode.
front=next(g for g in hull_parts if g['n']==2283 and g['lo'].z>125)
for o in list(s.objects):
 if o.name.startswith('BridgeArmor_Front_'):bpy.data.objects.remove(o,do_unlink=True)
for i in range(15):
 x=(i-7)*2.49;leaf=extract(hull,f'BridgeArmor_Front_Mesh_{i:02}',front['ids']);clip_x(leaf,x-1.235,x+1.235)
 # Separate the skirt at the roof knuckle. The fixed upper ledge is not part
 # of a rotating shield: including it makes an L-shaped wall stand on the roof.
 bm=bmesh.new();bm.from_mesh(leaf.data)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,0,129.80),plane_no=(0,0,1),clear_outer=True)
 bm.to_mesh(leaf.data);bm.free();leaf.data.update()
 pts=[v.co for v in leaf.data.vertices];top=max(v.z for v in pts);edge=max(v.y for v in pts)
 p=pivot(f'BridgeArmor_Front_{i:02}',(x,edge,top),system='bridge-armor');p['bank']='Front';keep(leaf,p)
# The original surface supplies the matching window frame behind the shutters.
glazing=extract(hull,'BridgeWindow_SourceFrame',front['ids'])
for i,m in enumerate(list(glazing.data.materials)):
 if m and 'Dark' in m.name:glazing.data.materials[i]=bpy.data.materials['Odin_Bridge_Glazing']
for vertex in glazing.data.vertices:vertex.co.y-=.30
for o in list(s.objects):
 if o.name.startswith('BridgeWindow_') and o!=glazing:bpy.data.objects.remove(o,do_unlink=True)
to_remove|=front['ids'];remove(hull,to_remove)

# Keep the quad gun axes parallel throughout extension. The pod remains visible
# under its canopy in NAV; only eight source units of pod travel are necessary.
for side in ['Port','Starboard']:
 bpy.data.objects[f'PDC_{side}_Carriage']['podTravel']=8.

# Use the actual inverse of each source rest orientation. Negating Euler angles
# in the same order had tipped the bridge-side twin mounts below the horizon.
source=json.loads((root/'work/source-articulation.json').read_text(encoding='utf8'))
basis=Quaternion((1,0,0),-math.pi/2)
for i,name in enumerate(['odin.021','odin.023','odin.070','odin.071']):
 R=Matrix(source[name]['poses']['-52']['world']).to_3x3()
 for side,sign in [('Port',-1),('Starboard',1)]:
  mirror=Matrix.Diagonal((sign,1,1));neutral=(mirror@R@mirror).inverted().to_quaternion()
  p=bpy.data.objects[f'SideBattery_{i+1}_{side}']
  # The mesh also has a baked bore inclination, beyond its object rotation.
  # Measure the longest slender barrel island, so the final six-degree aim is
  # relative to the hull horizon rather than just the source object's axes.
  mesh=next(o for o in p.children if o.type=='MESH');M=inv@mesh.matrix_world;candidates=[]
  for g in islands(mesh):
   if g['n']<1000:continue
   pts=np.array([list(M@mesh.data.vertices[k].co) for k in g['ids']]);w,u=np.linalg.eigh(np.cov(pts.T));axis=u[:,-1]
   if w[-1]/max(w[-2],1e-12)<12:continue
   if axis[1]<0:axis=-axis
   candidates.append((np.ptp(pts@axis),Vector(axis)))
  assert candidates,(name,side)
  bore=max(candidates,key=lambda item:item[0])[1]
  neutral=(neutral@bore).rotation_difference(Vector((0,1,0)))@neutral
  aim=Euler((math.radians(6),0,math.radians(-sign*[18,28,38,52][i])),'XYZ').to_quaternion()
  q=basis@(aim@neutral)@basis.inverted();p['deployQuaternion']=[q.x,q.y,q.z,q.w]
  measured=basis@bore;p['sourceBoreDirection']=list(measured)

# Restore the hidden original lower aft door and its rim. Keep the original
# material assignment and all vertices, instead of placing a new plane over it.
door=pivot('SternHangarDoor',(0,0,0),system='stern-door');door['closedInAllModes']=True
original=root.parent/'Odin 建模'/'odin.blend'
with bpy.data.libraries.load(str(original),link=False) as (a,b):b.objects=['holo.025','holo.026']
for o in b.objects:
 s.collection.objects.link(o);o.name='SternDoor_Original_'+o.name;o.hide_render=False;o.hide_set(False)
 M=o.matrix_world.copy();o.parent=door;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_local=M
 o.animation_data_clear()
 for idx,m in enumerate(list(o.data.materials)):
  if not m:continue
  suffix=m.name.replace('holo_a_mtl_Painted_Metal_','').split('.')[0]
  o.data.materials[idx]=bpy.data.materials.get('Odin_Paint_'+suffix,light)
 o['sourceObject']='holo.025' if '025' in o.name else 'holo.026'
for o in s.objects:o.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
asset['version']='0.4.0';s.name='ODIN v0.4 — recovered shields, telescopic tubes and parallel quad slides'
bpy.data.orphans_purge(do_recursive=True)
dest=root/'assets/blender/odin_articulated_v0.4.0.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
print('SAVED',dest,flush=True)
