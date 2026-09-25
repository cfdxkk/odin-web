"""Rebuild static mechanical joints. Run on odin_web_completed.blend, never the source.

No animation curves or clips are exported. Nuxt authors the complete motion sequence.
Measurements come from source geometry; the official exterior clips define the mechanism.
"""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1];scene=bpy.context.scene
source=json.loads((root/'work/source-articulation.json').read_text(encoding='utf8'))
islands=json.loads((root/'work/mesh-islands.json').read_text(encoding='utf8'))
instances=json.loads((root/'work/instances.json').read_text(encoding='utf8'))
asset=bpy.data.objects['Odin_Asset'];inverse=asset.matrix_world.inverted()
worlds={o:inverse@o.matrix_world for o in scene.objects if o.type=='MESH'}
for o,m in worlds.items():
 o.data.transform(m);o.parent=asset;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_local=Matrix.Identity(4)
for o in list(scene.objects):
 if o.type!='MESH' and o!=asset:bpy.data.objects.remove(o,do_unlink=True)
scene.name='ODIN v0.2 — articulated static asset'

def pivot(name,position,parent=asset,system=''):
 o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.parent=parent
 o.matrix_local=Matrix.Translation(Vector(position));o.empty_display_size=1
 o['system']=system;o['staticJoint']=True
 return o
def bind(o,p):
 # Geometry is in original model coordinates. Preserve it in the new joint's space.
 bpy.context.view_layer.update();raw=inverse@o.matrix_world
 target=inverse@p.matrix_world
 o.data.transform(target.inverted()@raw);o.parent=p;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_local=Matrix.Identity(4)
def origin(name):return Vector([r[3] for r in source[name]['poses']['-52']['world'][:3]])
def extract(o,name,ids):
 copy=o.copy();copy.data=o.data.copy();scene.collection.objects.link(copy);copy.name=name
 bm=bmesh.new();bm.from_mesh(copy.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS');bm.to_mesh(copy.data);bm.free();copy.data.update()
 return copy
def remove_vertices(o,ids):
 bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index in ids],context='VERTS');bm.to_mesh(o.data);bm.free();o.data.update()
def split_sides(o):
 parts=[]
 for sign,side in [(-1,'Port'),(1,'Starboard')]:
  ids={v.index for v in o.data.vertices if v.co.x*sign>=-.001}
  parts.append((sign,side,extract(o,o.name+'_'+side,ids)))
 bpy.data.objects.remove(o,do_unlink=True);return parts
def material(name,color,metal=.5,rough=.4,emission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
 b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
 if emission:b.inputs['Emission Color'].default_value=(*color,1);b.inputs['Emission Strength'].default_value=emission
 return m
dark=bpy.data.materials.get('Odin_Added_Dark_Alloy') or material('Odin_Added_Dark_Alloy',(.035,.05,.07));light=bpy.data.materials['Odin_Paint_Light']
steel=bpy.data.materials['Odin_Added_Machined_Alloy'];bay=material('Odin_Bay_Primer',(.20,.016,.012),.35,.42)
warning=material('Odin_Bay_Service_Light',(1,.09,.015),.0,.4,2)
def bevel(o,width=.08,segments=3):
 mod=o.modifiers.new('Machined edge bevel','BEVEL');mod.width=width;mod.segments=segments;mod.limit_method='ANGLE';mod.angle_limit=.52
 mod.affect='EDGES';bpy.context.view_layer.objects.active=o
 bpy.ops.object.modifier_apply(modifier=mod.name)
def mesh_box(name,pos,size,mat,parent=asset):
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.transform(Matrix.Translation(Vector(pos)))
 o.parent=asset;o.matrix_local=Matrix.Identity(4);o.data.materials.append(mat);bevel(o)
 if parent!=asset:bind(o,parent)
 return o

# Two main triple batteries: barrel cradle, housing and three sliding shrouds remain separate.
for side,ids,mount_name in [('Dorsal',range(4,9),'Empty.001'),('Ventral',range(12,17),'Empty.003')]:
 mount=pivot('Main_'+side+'_Mount',origin(mount_name),system='main')
 for i,role in zip(ids,['Barrels','Housing','Shroud_Port','Shroud_Center','Shroud_Starboard']):
  old=f'odin.{i:03}';pos=origin(old);p=pivot('Main_'+side+'_'+role,pos-origin(mount_name),mount,'main')
  bind(bpy.data.objects[old],p)

# The old covers were solid blocks and animated by scaling. Replace them with nested
# rigid panels which slide under the forward deck. Every panel retains its dimensions.
for side,old,base_y,base_z,direction in [('Dorsal','Hatch_Dorsal',79.57,54.0,1),('Ventral','Hatch_Ventral',29.50,-68.0,-1)]:
 bpy.data.objects.remove(bpy.data.objects[old],do_unlink=True)
 for i in range(5):
  length=19.9;y0=base_y+i*19.8;y1=y0+length
  z0=base_z-direction*i*3.45;z1=z0-direction*3.47;thick=.60
  verts=[(x,y,z-direction*thick*k) for k in range(2) for x,y,z in [(-13.35,y0,z0),(13.35,y0,z0),(13.35,y1,z1),(-13.35,y1,z1)]]
  mesh=bpy.data.meshes.new('Rigid cover panel');mesh.from_pydata(verts,[],[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]);mesh.update()
  o=bpy.data.objects.new(f'Hatch_{side}_Panel_{i:02}',mesh);scene.collection.objects.link(o);o.parent=asset;o.data.materials.append(light);bevel(o,.1)
  p=pivot(f'Hatch_{side}_{i:02}',(0,y0,z0),system='main-hatch');p['panelIndex']=i;bind(o,p)
 # A recessed service tray, twin rails, crossmembers and warm maintenance lamps.
 z=base_z-direction*18
 mesh_box('MainBay_'+side,(0,base_y+44,z),(26,106,1.1),bay)
 for x in [-12.8,12.8]:
  mesh_box('MainRail_'+side,(x,base_y+44,z+direction*1.1),(.38,103,.55),steel)
  for i in range(9):
   mesh_box('MainBayRib_'+side,(x,base_y+i*11,z+direction*3),(.4,.5,5.6),bay)
   if i%2==0:mesh_box('MainBayLamp_'+side,(x*.96,base_y+i*11,z+direction*4.7),(.26,1.1,.32),warning)

# Three axial single batteries, including the belly battery's separate cradle travel.
for side,gun,housing,mount in [('Bow','odin.002','odin.003','Empty'),('Stern','odin.026','odin.027','Empty.004'),('Keel','odin.029','odin.030','Empty.005')]:
 assembly=pivot('Axial_'+side+'_Mount',origin(mount),system='secondary')
 p=pivot('Axial_'+side+'_Barrel',origin(gun)-origin(mount),assembly,'secondary');bind(bpy.data.objects[gun],p);bind(bpy.data.objects[housing],assembly)
 if side=='Keel':bind(bpy.data.objects['holo.022'],assembly)

# Mirror-generated gun pairs must rotate about opposite physical hinges, never the
# same pivot. Split the evaluated mirror into individual port/starboard assemblies.
for index,name in enumerate(['odin.021','odin.023','odin.070','odin.071']):
 for sign,side,o in split_sides(bpy.data.objects[name]):
  pos=origin(name);pos.x=abs(pos.x)*sign
  p=pivot(f'SideBattery_{index+1}_{side}',pos,system='secondary');bind(o,p)
for station,name in [('Aft','holo.010'),('Forward','holo.011')]:
 for sign,side,o in split_sides(bpy.data.objects[name]):
  pos=origin(name);pos.x=abs(pos.x)*sign;p=pivot(f'DefenseRail_{station}_{side}',pos,system='defense');bind(o,p)

# Eight local defense mounts: rail translation -> raised ring -> yaw -> gun elevation.
for i in range(8):
 suffix='turret 1'+(f'.{i:03}' if i else '')
 pos=origin(suffix);p=pivot(f'Defense_{i+1:02}_Carriage',pos,system='pdc')
 p['side']=-1 if pos.x<0 else 1;p['station']='forward' if i<4 else 'aft'
 yaw=pivot(f'Defense_{i+1:02}_Yaw',(0,0,0),p,'pdc')
 for j in [73,74]:bind(bpy.data.objects[f'odin.{j:03}__{suffix}'],yaw)
 entry=next(x for x in instances if x['name']=='odin.072' and x['parent']==suffix)
 m=Matrix(entry['matrix']);hinge=m.translation
 gun=pivot(f'Defense_{i+1:02}_Elevation',hinge-pos,yaw,'pdc')
 axis=(m.to_3x3()@Vector((1,0,0))).normalized();gun['hingeAxis']=[axis.x,axis.z,-axis.y]
 bind(bpy.data.objects[f'odin.072__{suffix}'],gun)

# Quad PDCs beside the tower. The source merged all four folding gun arms into one
# object. Separate its disconnected islands by quadrant, preserving original UVs.
prototype=islands['holo.014__bridge turret']
for sign,side,suffix in [(-1,'Port','bridge turret.001'),(1,'Starboard','bridge turret')]:
 pos=origin(suffix);carriage=pivot('PDC_'+side+'_Carriage',pos,system='pdc')
 gun=bpy.data.objects['holo.014__'+suffix]
 groups={k:set() for k in range(4)};center_ids=set()
 for c in prototype:
  if c['n']==997 or (c['n']==24 and c['lo'][0]>32):center_ids.update(c['ids']);continue
  front=(c['lo'][1]+c['hi'][1])*.5>-61.8;upper=(c['lo'][2]+c['hi'][2])*.5>105.98
  groups[int(front)*2+int(upper)].update(c['ids'])
 for k,ids in groups.items():
  arm=extract(gun,f'PDC_{side}_ArmMesh_{k}',ids)
  hinge=Vector((sign*23.02,-58.68 if k>=2 else -64.94,107.30 if k%2 else 104.65))
  p=pivot(f'PDC_{side}_Arm_{k}',hinge-pos,carriage,'pdc');p['side']=sign;p['quadrant']=k
  bind(arm,p)
 body=extract(gun,f'PDC_{side}_Casing',center_ids);bind(body,carriage)
 bpy.data.objects.remove(gun,do_unlink=True)
 fork=bpy.data.objects['holo.016__'+suffix];bind(fork,carriage)
 for offset in [-3.1,3.1]:
  mesh_box(f'PDC_{side}_FixedGuide_{offset}',(sign*22.5,-61.7+offset,105.9),(22,.65,.75),steel)

# Recover the existing detailed bridge armor slats from the hull. They were baked
# into the hull in the old export. Front, upper rear and lower rear banks get hinges.
hull=bpy.data.objects['holo.001'];remove=set();armor_count=0
for c in islands['holo.001']:
 lo,hi=c['lo'],c['hi']
 if not (200<c['n']<400 and lo[2]>125 and hi[0]-lo[0]<2.6):continue
 if lo[1]>-35 and lo[2]>130:bank='Front';hinge=((lo[0]+hi[0])/2,hi[1],hi[2])
 elif lo[2]>130:bank='RearUpper';hinge=((lo[0]+hi[0])/2,lo[1],hi[2])
 elif lo[2]<127:bank='RearLower';hinge=((lo[0]+hi[0])/2,lo[1],lo[2])
 else:continue
 slat=extract(hull,f'BridgeArmor_{bank}_Mesh_{armor_count:02}',set(c['ids']))
 p=pivot(f'BridgeArmor_{bank}_{armor_count:02}',hinge,system='bridge-armor');p['bank']=bank;bind(slat,p)
 if bank=='Front':
  # Complete the short source panels so the sloped shield covers the full glazing.
  for vertex in slat.data.vertices:vertex.co.y*=1.30
 remove.update(c['ids']);armor_count+=1
remove_vertices(hull,remove)

# The previous provisional glazing was placed above/in front of the bridge.
# Build each pane directly on four raycast hits on the actual angled window face.
for o in list(scene.objects):
 if o.name.startswith(('BridgeWindow_','UpperBridgeWindow_')):bpy.data.objects.remove(o,do_unlink=True)
glass=bpy.data.materials['Odin_Bridge_Glazing'];glass.diffuse_color=(.018,.07,.09,1)
g=glass.node_tree.nodes.get('Principled BSDF');g.inputs['Base Color'].default_value=(.018,.07,.09,1)
g.inputs['Emission Color'].default_value=(.014,.065,.085,1);g.inputs['Emission Strength'].default_value=.25
surface=BVHTree.FromPolygons([v.co for v in hull.data.vertices],[p.vertices[:] for p in hull.data.polygons])
for i in range(15):
 x=(i-7)*2.48;vertices=[]
 for xx,z in [(x-1.05,126.1),(x+1.05,126.1),(x+1.05,129.7),(x-1.05,129.7)]:
  hit,normal,_,_=surface.ray_cast(Vector((xx,0,z)),Vector((0,-1,0)))
  if hit is not None:vertices.append(hit+normal*.035)
 if len(vertices)!=4:continue
 mesh=bpy.data.meshes.new('Surface fitted bridge pane');mesh.from_pydata(vertices,[],[(0,1,2,3)]);mesh.update()
 o=bpy.data.objects.new(f'BridgeWindow_{i:02}',mesh);scene.collection.objects.link(o);o.parent=asset;o.data.materials.append(glass)

# Restore 2K source wear and tangent normals instead of the old downsampled 1K maps.
texdir=root/'work/textures';wear=bpy.data.images.load(str(texdir/'180949_panel_a_base_diff.png'),check_existing=True)
size=2048;wear.scale(size,size);pixels=np.asarray(wear.pixels[:],dtype=np.float32).reshape(size,size,4)
lum=pixels[:,:,:3].mean(2);variation=np.clip(lum/max(float(lum.mean()),.01),.67,1.27)
packed_normal=bpy.data.images.load(str(texdir/'0e955e_ship_painted_tileable_a_ddna.png'),check_existing=True);packed_normal.colorspace_settings.name='Non-Color'
# The game texture stores XY normals, not glTF's normalized RGB tangent normal.
# Reconstruct Z instead of interpreting its gray packed channel as a zero normal.
packed_normal.scale(size,size);n=np.asarray(packed_normal.pixels[:],dtype=np.float32).reshape(size,size,4)
xy=np.clip(n[:,:,:2]*2-1,-1,1)
n[:,:,2]=(np.sqrt(np.clip(1-(xy*xy).sum(2),0,1))+1)*.5;n[:,:,3]=1
normal=bpy.data.images.new('Odin_Tangent_Normal_2K',width=size,height=size,alpha=False);normal.colorspace_settings.name='Non-Color';normal.pixels.foreach_set(n.ravel());normal.pack()
gloss=bpy.data.images.load(str(texdir/'0e955e_ship_painted_tileable_a_ddna.glossmap.png'),check_existing=True);gloss.colorspace_settings.name='Non-Color'
rough=bpy.data.images.new('Odin_Roughness_2K',width=size,height=size,alpha=False)
g=np.asarray(gloss.pixels[:],dtype=np.float32).reshape(gloss.size[1],gloss.size[0],4)
if tuple(gloss.size)!=(size,size):gloss.scale(size,size);g=np.asarray(gloss.pixels[:],dtype=np.float32).reshape(size,size,4)
r=np.ones((size,size,4),dtype=np.float32);r[:,:,:3]=np.clip(.29+.24*(1-g[:,:,:3]),.29,.58)
rough.pixels.foreach_set(r.ravel());rough.colorspace_settings.name='Non-Color';rough.pack()
for m in list(bpy.data.materials):
 if not (m.name.startswith('Odin_Paint_') or m.name in ['Odin_Weapon_Steel','Odin_Equipment_Alloy']):continue
 b=m.node_tree.nodes.get('Principled BSDF')
 if not b:continue
 if m.name=='Odin_Paint_Light':m.diffuse_color=(.42,.46,.51,1)
 if m.name.startswith('Odin_Paint_Dark'):m.diffuse_color=(.055,.067,.083,1)
 col=np.array(m.diffuse_color[:3]);data=np.ones_like(pixels);data[:,:,:3]=variation[:,:,None]*col
 paint=bpy.data.images.new(m.name+'_Albedo_2K',width=size,height=size,alpha=False);paint.pixels.foreach_set(data.ravel());paint.pack()
 for n in m.node_tree.nodes:
  if n.type=='TEX_IMAGE':n.image=paint
 n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=normal
 convert=m.node_tree.nodes.new('ShaderNodeNormalMap');convert.inputs['Strength'].default_value=.24
 m.node_tree.links.new(n.outputs['Color'],convert.inputs['Color']);m.node_tree.links.new(convert.outputs['Normal'],b.inputs['Normal'])
 n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=rough;m.node_tree.links.new(n.outputs['Color'],b.inputs['Roughness'])

# Add true bevel geometry to sharp exterior parts, preserving planar hull surfaces.
for o in list(scene.objects):
 if o.type!='MESH':continue
 if o.name.startswith(('odin.','holo.','Hatch_')) and len(o.data.polygons)<35000:bevel(o,.055,3)
 o.data.validate(clean_customdata=False)
 o.animation_data_clear()
for o in list(scene.objects):
 if o.name.startswith('EngineCore_'):
  o['radius']=o.get('radius',3)
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
asset['version']='0.2.0';asset['animation']='Static joints only. Procedural motion is authored in app/lib/odin-rig.ts.'
asset['bridgeArmorSlats']=armor_count
for o in scene.objects:o.select_set(True)
bpy.context.view_layer.objects.active=asset
bpy.data.orphans_purge(do_recursive=True)
destination=root/'assets/blender/odin_articulated_v0.2.0.blend';destination.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)
print('STATIC ARTICULATED SOURCE',destination,'armor slats',armor_count,flush=True)
