"""v0.8.5: revised main/aft armor meeting line; retain the separate nose leaf.

Load v0.8.4. Only the four main side leaves and four rigid planar aft leaves
change. The main/aft shared edge gets a distinct upper shoulder and a short
inclined lower segment, keeping the forward lift-and-slide plate independent.
"""
import bpy, bmesh, hashlib, json, math
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/blender/odin_articulated_v0.8.4.blend'
OUT=ROOT/'assets/blender/odin_articulated_v0.8.5.blend'
assert Path(bpy.data.filepath).resolve()==BASE.resolve()
asset=bpy.data.objects['Odin_Asset']; inv=asset.matrix_world.inverted()
ref=json.loads((ROOT/'tools/main_armor_v081_boundaries.json').read_text(encoding='utf8'))
paint=bpy.data.materials['Odin_Paint_Light']; red=bpy.data.materials['Odin_Turret_Interior_DeepRed']
GAP=.035; EXTENSION=4.0
report={'revision':'0.8.5','baseline':BASE.name,'noseUnchanged':True,'parts':{}}

def pts(obj):
 m=inv@obj.matrix_world
 return [m@v.co for v in obj.data.vertices]

def curve(points,y):
 if y<=points[0][1]:return Vector(points[0])
 if y>=points[-1][1]:return Vector(points[-1])
 for a,b in zip(points,points[1:]):
  if a[1]<=y<=b[1]:return Vector(a).lerp(Vector(b),(y-a[1])/(b[1]-a[1]))

def signature(obj):
 return hashlib.sha256(json.dumps({'points':[list(v.co) for v in obj.data.vertices],'faces':[list(f.vertices) for f in obj.data.polygons], 'materials':[f.material_index for f in obj.data.polygons], 'matrix':[list(r) for r in obj.matrix_world], 'parent':obj.parent.name if obj.parent else ''}).encode()).hexdigest()

nose_before={obj.name:signature(obj) for obj in bpy.context.scene.objects if obj.type=='MESH' and obj.parent and '_Nose' in obj.parent.name}
for bank,cfg in ref.items():
 direction=cfg['direction']; center=cfg['center']
 for side,sign in [('Port',-1),('Starboard',1)]:
  main=bpy.data.objects[f'Hatch_{bank}_{side}']; aft=bpy.data.objects[f'Hatch_{bank}_Aft_{side}']; ao=aft.children[0]
  old=pts(ao); n=len(old)//2; rows=n//2
  free=old[:n:2]; edge=old[1:n:2]
  tip=free[-1].copy(); old_corner=edge[-1].copy()
  lip=cfg[side]['lip']; main_y=float(cfg[side]['upper'][-1][1])+.0175
  # The outline below the shroud shoulder moves forward, without changing
  # the long upper shroud contact or the independently animated nose seam.
  def lip_point(y):
   p=curve(lip,y);p.x-=sign*GAP;p.z+=direction*.005;p.y=y
   return p
  corner=lip_point(old_corner.y+EXTENSION)
  # A single plane through the preserved upper edge and the new outer end.
  normal=(tip-free[0]).cross(corner-free[0]).normalized()
  if normal.z*direction<0:normal.negate()
  def plane_z(x,y):return free[0].z-(normal.x*(x-free[0].x)+normal.y*(y-free[0].y))/normal.z
  threshold=abs(cfg[side]['upper'][-1][0]-center)
  old_rear_corner=lip_point(main_y)
  fade_end=main_y+16
  change={}
  for obj in list(main.children):
   if obj.type!='MESH':continue
   m=inv@obj.matrix_world;mi=m.inverted();count=0;maximum=0.
   for vertex in obj.data.vertices:
    p=m@vertex.co;radius=sign*(p.x-center)
    if p.y>fade_end or radius<threshold-.0001:continue
    lo=lip_point(p.y);outer=sign*(lo.x-center)
    if outer<=threshold+.001:continue
    u=max(0,min(1,(radius-threshold)/(outer-threshold)))
    fade=max(0,min(1,(fade_end-p.y)/(fade_end-main_y)))
    new_y=p.y+EXTENSION*u*fade
    hi=lip_point(new_y);new_radius=threshold+(radius-threshold)*(sign*(hi.x-center)-threshold)/(outer-threshold)
    x=center+sign*new_radius
    rear_r=threshold+(sign*(old_rear_corner.x-center)-threshold)*u
    rear_y=main_y+EXTENSION*u
    rear_new_radius=threshold+(rear_r-threshold)*(sign*(lip_point(rear_y).x-center)-threshold)/(sign*(old_rear_corner.x-center)-threshold)
    rx=center+sign*rear_new_radius
    old_rear_z=cfg[side]['upper'][-1][2]*(1-u)+old_rear_corner.z*u
    dz=(plane_z(rx,rear_y)-old_rear_z)*fade
    # Keep the upper interface exact and avoid moving its seam offset.
    dz*=u
    q=Vector((x,new_y,p.z+dz));vertex.co=mi@q
    count+=1;maximum=max(maximum,(q-p).length)
   obj.data.update();obj.data.set_sharp_from_angle(angle=math.radians(30))
   change[obj.name]={'movedVertices':count,'maximumDisplacement':maximum}
  # The planar aft triangle inherits its original long mating boundaries;
  # only its forward wedge extends to the new shared corner.
  front=[];outside=[]
  for a,b in zip(free,edge):
   front.append(Vector((a.x,a.y,plane_z(a.x,a.y))))
   outside.append(Vector((b.x,b.y,plane_z(b.x,b.y))))
  for i in range(1,41):
   t=i/40;y=tip.y+EXTENSION*t
   a=tip.lerp(corner,t);a.z=plane_z(a.x,y)
   b=lip_point(y);b.z=plane_z(b.x,y)
   front.append(a);outside.append(b)
  top=[]
  for a,b in zip(front,outside):top.extend([a,b])
  top_count=len(top);thickness=.025
  bottom=[p-normal*thickness for p in top]
  # Bevel the new diagonal seam inward: a normal extrusion otherwise pokes
  # through its neighboring leaf despite the correctly fitted outer faces.
  slope=(corner.y-tip.y)/(corner.x-tip.x)
  for i,p in enumerate(bottom):
   limit=tip.y+(p.x-tip.x)*slope-.012
   if p.y>limit and p.y>tip.y-.1:
    dy=limit-p.y;p.y+=dy;p.z-=normal.y/normal.z*dy
  vertices=top+bottom
  faces=[(r*2,r*2+1,(r+1)*2+1,(r+1)*2) for r in range(len(front)-1)]
  fs=faces+[tuple(i+top_count for i in reversed(f)) for f in faces]
  boundary=[2*r for r in range(len(front))]+[2*r+1 for r in reversed(range(len(front)))]
  fs += [(i,j,j+top_count,i+top_count) for i,j in zip(boundary,boundary[1:]+boundary[:1])]
  mesh=bpy.data.meshes.new(ao.name+'_v085');mesh.from_pydata(vertices,[],fs);mesh.update()
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
  # New vertices were built in asset space, preserve the original child rest transform.
  transform=(inv@ao.matrix_world).inverted()
  for vertex in mesh.vertices:vertex.co=transform@vertex.co
  ao.data=mesh;mesh.materials.append(paint);mesh.materials.append(red);mesh.update()
  nm=(inv@ao.matrix_world).to_3x3().inverted().transposed()
  for face in mesh.polygons:
   face.use_smooth=False
   if (nm@face.normal).normalized().dot(normal)<-.5:face.material_index=1
  aft['planeNormal']=list(normal)
  aft['closedOutlineXY']=[[p.x,p.y] for p in front+list(reversed(outside))]
  aft['sourceReference']='Planar aft armor with forward lower shoulder; shared kinked main-leaf boundary, independent nose'
  main['rearSeamReference']='Upper shroud contour plus shared forward lower shoulder; nose remains independent'
  outline=[]
  for ox,oy in main['closedOutlineXY']:
   radius=sign*(ox-center);outer=sign*(lip_point(oy).x-center)
   if oy<=fade_end and radius>=threshold and outer>threshold+.001:
    u=max(0,min(1,(radius-threshold)/(outer-threshold)));fade=max(0,min(1,(fade_end-oy)/(fade_end-main_y)))
    ny=oy+EXTENSION*u*fade
    nr=threshold+(radius-threshold)*(sign*(lip_point(ny).x-center)-threshold)/(outer-threshold)
    outline.append([center+sign*nr,ny])
   else:outline.append([ox,oy])
  main['closedOutlineXY']=outline
  # The extended toe must clear the translating skin after its outward turn.
  # Rebase the parallel axle very slightly, leaving every closed vertex fixed.
  adjustment={('Dorsal','Port'):(.40,0,.05),('Dorsal','Starboard'):(-.25,0,.05),
              ('Ventral','Port'):(1.30,0,-.20),('Ventral','Starboard'):(-1.30,0,-.10)}[bank,side]
  delta=Vector(adjustment);closed_before=pts(ao);pivot_before=aft.location.copy();world=ao.matrix_world.copy()
  aft.location+=delta;bpy.context.view_layer.update();ao.matrix_world=world;bpy.context.view_layer.update()
  aft['hingeEdge']=[list(Vector(p)+delta) for p in aft['hingeEdge']]
  aft['boundaryRevisionHingeRebase']=list(delta)
  aft['boundaryRevisionHingeParallel']=True
  residual=max((a-b).length for a,b in zip(closed_before,pts(ao)))
  assert residual<.00005
  assert abs(float(aft['openingAngleDegrees']))==130
  planar_error=max(abs(normal.dot(p-free[0])) for p in top)
  assert planar_error<.00005

  report['parts'][main.name]={'upperShoulder':list(tip),'previousOuterEnd':list(old_corner),'newOuterEnd':list(corner),'extension':EXTENSION,'aftPlaneNormal':list(normal),'meshes':change,'innerSeamBevel':.012,'maximumPlanarityError':planar_error,'hinge':{'before':list(pivot_before),'after':list(aft.location),'parallelAxis':list(aft['hingeAxis']),'angleDegrees':float(aft['openingAngleDegrees']),'closedVertexResidual':residual}}
  print('SHARED_BOUNDARY',main.name,report['parts'][main.name],flush=True)
for name,digest in nose_before.items():assert signature(bpy.data.objects[name])==digest
helper=ROOT/'tools/finish_armor_lips_v085.py'
exec(compile(helper.read_text(encoding='utf8'),str(helper),'exec'))
report['exteriorLipFinish']=finish_armor_lips_v085()
assert not bpy.data.actions
asset['version']='0.8.5';bpy.context.scene.name='ODIN v0.8.5 - five independent armor leaves with matched aft shoulders'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
report['blendSha256']=hashlib.sha256(OUT.read_bytes()).hexdigest()
path=ROOT/'work/v085-review/armor-boundaries.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf8')
print('SAVED',OUT,flush=True)
