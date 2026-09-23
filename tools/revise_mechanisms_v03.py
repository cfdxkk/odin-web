"""Run on the v0.2.1 copy. Static model revision; never edits odin.blend.

Observable exterior references: RSI Odin main-battery / tower-quad clips and
Star Citizen Live CFoQp6wRjPo (51:24–52:16 for the aft enclosure).
No Blender keyframes are created. The runtime owns every moving joint.
"""
import bpy,bmesh,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
root=Path(__file__).resolve().parents[1];s=bpy.context.scene
asset=bpy.data.objects['Odin_Asset'];inverse=asset.matrix_world.inverted()
def pivot(name,pos,parent=asset,system=''):
 o=bpy.data.objects.new(name,None);s.collection.objects.link(o);o.parent=parent;o.matrix_local=Matrix.Translation(Vector(pos));o['staticJoint']=True;o['system']=system;return o
def parent_keep(o,p):
 bpy.context.view_layer.update();m=o.matrix_world.copy();o.parent=p;o.matrix_world=m
def bevel(o,width=.09):
 bpy.context.view_layer.objects.active=o;m=o.modifiers.new('Machined edge','BEVEL');m.width=width;m.segments=3;bpy.ops.object.modifier_apply(modifier=m.name)
def solid(name,points,mat,parent=asset,thickness=(0,0,-.65)):
 n=len(points);verts=points+[tuple(Vector(p)+Vector(thickness)) for p in points]
 faces=[tuple(range(n)),tuple(reversed(range(n,n*2)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 o=bpy.data.objects.new(name,mesh);s.collection.objects.link(o);o.parent=asset;o.matrix_local=Matrix.Identity(4);o.data.materials.append(mat);bevel(o)
 parent_keep(o,parent);return o
light=bpy.data.materials['Odin_Paint_Light'];dark=bpy.data.materials['Odin_Paint_Dark.001'];steel=bpy.data.materials['Odin_Added_Machined_Alloy'];orange=bpy.data.materials['Odin_Paint_Orange']

# Each longitudinal cover bank splits at the centreline and hinges outward.
# Five paired rigid leaves follow the sloping deck; no forward translation.
for o in list(s.objects):
 if o.name.startswith('Hatch_'):bpy.data.objects.remove(o,do_unlink=True)
for bank,base_y,base_z,direction in [('Dorsal',79.57,54.,1),('Ventral',29.50,-68.,-1)]:
 for i in range(5):
  y0=base_y+i*19.8;y1=y0+19.55;z0=base_z-direction*i*3.45;z1=z0-direction*3.407
  axis=Vector((0,1,-direction*3.407/19.55)).normalized()
  for side,sign in [('Port',-1),('Starboard',1)]:
   hinge=(sign*13.35,(y0+y1)/2,(z0+z1)/2)
   p=pivot(f'Hatch_{bank}_{side}_{i:02}',hinge,system='main-hatch')
   p['hingeAxis']=[axis.x,axis.z,-axis.y];p['openingSign']=sign*direction;p['panelIndex']=i
   points=[(sign*.07,y0,z0),(sign*13.35,y0,z0),(sign*13.35,y1,z1),(sign*.07,y1,z1)]
   solid(p.name+'_Leaf',points,light,p,(0,0,-direction*.6))

# The 116-vertex islands are the stationary mounting forks, not folding arms.
# Extract them before putting the four arms and cockpit on an aiming gimbal.
for side,sign in [('Port',-1),('Starboard',1)]:
 carriage=bpy.data.objects[f'PDC_{side}_Carriage'];bpy.context.view_layer.update()
 gimbal=pivot(f'PDC_{side}_Gimbal',(0,0,0),carriage,'pdc')
 gimbal.matrix_world=asset.matrix_world@Matrix.Translation(Vector((sign*23.02,-61.7066,105.98)))
 for k in range(4):
  arm=bpy.data.objects[f'PDC_{side}_ArmMesh_{k}'];mesh=arm.data
  adj=[[] for _ in mesh.vertices]
  for e in mesh.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
  remaining=set(range(len(adj)));fixed=set()
  while remaining:
   start=remaining.pop();part={start};stack=[start]
   while stack:
    for nxt in adj[stack.pop()]:
     if nxt in remaining:remaining.remove(nxt);part.add(nxt);stack.append(nxt)
   if len(part)==116:fixed.update(part)
  assert len(fixed)==116,(arm.name,len(fixed))
  support=arm.copy();support.data=mesh.copy();support.name=f'PDC_{side}_FixedFork_{k}';s.collection.objects.link(support)
  for obj,keep in [(support,True),(arm,False)]:
   bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table()
   bmesh.ops.delete(bm,geom=[v for v in bm.verts if (v.index not in fixed if keep else v.index in fixed)],context='VERTS');bm.to_mesh(obj.data);bm.free()
  parent_keep(support,gimbal);parent_keep(bpy.data.objects[f'PDC_{side}_Arm_{k}'],gimbal)
 parent_keep(bpy.data.objects[f'PDC_{side}_Casing'],gimbal)

# Close the lower aft hangar aperture under the main engine. This tapered ramp
# follows the existing rim rather than sealing the engine or inventing a tail box.
door=pivot('SternHangarDoor',(0,0,0),system='stern-door');door['closedInAllModes']=True
def panel(name,x0,x1,y0,y1,z0,z1,mat=light):
 return solid(name,[(x0,y0,z0),(x1,y0,z0),(x1,y1,z1),(x0,y1,z1)],mat,door,(0,.55,.65))
for sign,side in [(-1,'Port'),(1,'Starboard')]:
 for row in range(2):
  u0=row*.5;u1=(row+1)*.5
  y0=-212+108*u0;y1=-212+108*u1-.2;z0=-10.5-23*u0;z1=-10.5-23*u1
  solid(f'SternDoor_{side}_{row}',[(sign*.10,y0,z0),(sign*(33-3*u0),y0,z0),(sign*(33-3*u1),y1,z1),(sign*.10,y1,z1)],light,door,(0,.7,.8))
 # Side seals and service rails are outside the panel surface.
 solid(f'SternDoor_{side}_Frame',[(sign*33,-213,-10.7),(sign*34.2,-213,-10.7),(sign*31.2,-103,-34),(sign*30,-103,-34)],steel,door,(0,.5,.5))
panel('SternDoor_Header',-33.5,33.5,-214,-209,-10.1,-11.2,dark)
panel('SternDoor_CenterSeam',-.18,.18,-211,-105,-11.2,-33.8,dark)
panel('SternDoor_Threshold',-30.5,30.5,-107,-102.5,-33.7,-34.5,steel)
for i in range(18):
 x=-30+i*3.4
 solid(f'SternDoor_Warning_{i:02}',[(x,-207,-11.65),(x+1.5,-207,-11.65),(x+3.1,-201,-12.95),(x+1.6,-201,-12.95)],orange,door,(0,.04,.04))

# glTF stores sRGB albedo bytes. Use a restrained original-style gray/charcoal
# and warm orange palette; retain UVs, wear and the reconstructed tangent normals.
palette={'Odin_Paint_Light':(.55,.585,.62),'Odin_Paint_Dark.001':(.27,.30,.335),'Odin_Paint_Dark':(.27,.30,.335),'Odin_Paint_Orange':(.65,.235,.075),'Odin_Paint_White':(.69,.72,.74),'Odin_Weapon_Steel':(.32,.35,.38),'Odin_Equipment_Alloy':(.40,.43,.46)}
wear=bpy.data.images['Odin_Paint_Light_Albedo_2K'];size=wear.size[0]
px=np.array(wear.pixels[:],dtype=np.float32).reshape(size,size,4);lum=px[:,:,:3].mean(2);variation=np.clip(lum/max(float(lum.mean()),.01),.82,1.15)
for name,col in palette.items():
 m=bpy.data.materials.get(name)
 if not m:continue
 b=m.node_tree.nodes.get('Principled BSDF');m.diffuse_color=(*col,1);b.inputs['Metallic'].default_value=.12;b.inputs['Roughness'].default_value=.66
 image=bpy.data.images.new(name+'_Livery_v03',width=size,height=size,alpha=False);data=np.ones_like(px);data[:,:,:3]=variation[:,:,None]*np.array(col);image.pixels.foreach_set(data.ravel());image.pack()
 for link in list(b.inputs['Base Color'].links):
  if link.from_node.type=='TEX_IMAGE':link.from_node.image=image
 for n in m.node_tree.nodes:
  if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.16
rough=bpy.data.images.get('Odin_Roughness_2K')
if rough:
 p=np.ones((size,size,4),np.float32);p[:,:,:3]=(.64+.08*(1-variation[:,:,None]));rough.pixels.foreach_set(p.ravel());rough.pack()
for name in ['Odin_Added_Machined_Alloy','Odin_Added_Dark_Alloy']:
 m=bpy.data.materials.get(name)
 if m:
  b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Roughness'].default_value=.62;b.inputs['Metallic'].default_value=.5
for o in s.objects:o.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
asset['version']='0.3.0';s.name='ODIN v0.3 — hinged covers, quad forks, aft door'
bpy.data.orphans_purge(do_recursive=True)
dest=root/'assets/blender/odin_articulated_v0.3.0.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
print('SAVED STATIC REVISION',dest,flush=True)
