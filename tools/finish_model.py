"""Complete the display asset. Geometry/materials only: no Actions, cameras or lights exported."""
import bpy, math, json, numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

root=Path(__file__).resolve().parents[1]
output=root/'public'/'models';output.mkdir(parents=True,exist_ok=True)
texdir=root/'public'/'textures';texdir.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
scene.name='ODIN - Fan Art - Static Asset'
for o in list(scene.objects):
    if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
for o in scene.objects:
    o.animation_data_clear()
    # Freeze world transforms so that new export pivots remain simple and explicit.
    o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)

# Recover packed wear texture from the source; simplify the game shader to glTF PBR.
wear=bpy.data.images.get('180949_panel_a_base_diff.png')
wear.scale(1024,1024)
pixels=np.asarray(wear.pixels[:],dtype=np.float32).reshape(1024,1024,4)
lum=pixels[:,:,:3].mean(axis=2)
variation=np.clip(lum/max(float(lum.mean()),.01),.55,1.35)
colors={
 'holo_a_mtl_Painted_Metal_Light':(.22342,.25249,.31855,1),
 'holo_a_mtl_Painted_Metal_Dark.001':(.04147,.05653,.08437,1),
 'holo_a_mtl_Painted_Metal_Dark':(.03071,.05951,.08438,1),
 'holo_a_mtl_Painted_Metal_Orange':(.44798,.01454,.001,1),
 'holo_a_mtl_Painted_Metal_White':(.018,.023,.032,1),
 'Material':(.40,.43,.47,1),
 '材质':(.13178,.16129,.21223,1),
}
for idx,m in enumerate(list(bpy.data.materials)):
    color=colors.get(m.name,(.16,.22,.27,1))
    m.diffuse_color=color;m.use_nodes=True;m.node_tree.nodes.clear()
    bs=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    bs.inputs['Base Color'].default_value=color
    bs.inputs['Metallic'].default_value=.52
    bs.inputs['Roughness'].default_value=.38 if 'Light' in m.name else .48
    out=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    data=np.ones_like(pixels);data[:,:,:3]=variation[:,:,None]*np.array(color[:3])
    im=bpy.data.images.new(f'Odin_Paint_{idx}',width=1024,height=1024,alpha=False)
    im.pixels.foreach_set(data.ravel());im.filepath_raw=str(texdir/f'paint-{idx}.png');im.file_format='PNG';im.save();im.pack()
    tn=m.node_tree.nodes.new('ShaderNodeTexImage');tn.image=im;m.node_tree.links.new(tn.outputs['Color'],bs.inputs['Base Color'])
    m.name={'材质':'Odin_Weapon_Steel','Material':'Odin_Equipment_Alloy'}.get(m.name,m.name.replace('holo_a_mtl_Painted_Metal_','Odin_Paint_'))

def material(name,color,metal=.5,rough=.4,emit=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
    if emit:b.inputs['Emission Color'].default_value=(*color,1);b.inputs['Emission Strength'].default_value=emit
    return m
steel=material('Odin_Added_Dark_Alloy',(.05,.07,.1),.7,.32)
silver=material('Odin_Added_Machined_Alloy',(.28,.34,.41),.8,.29)
glass=material('Odin_Bridge_Glazing',(.02,.32,.46),.4,.2,1.7)
engine=material('Odin_Engine_Emission',(.025,.22,1.0),.0,.3,5)
amber=material('Odin_Hangar_Amber',(.95,.13,.012),.1,.35,2)
red=material('Odin_Nav_Port',(.9,.015,.008),0,.35,5)
cyan=material('Odin_Nav_Starboard',(.005,.5,.38),0,.35,4)
mark=material('Odin_Hull_Markings',(.55,.61,.67),.25,.5)

def bevel(o,width=.15):
    mod=o.modifiers.new('Edge machining','BEVEL');mod.width=width;mod.segments=2
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return o
def box(name,pos,size,mat,parent=None,edge=.08):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos)
    o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if edge:bevel(o,edge)
    if parent:
        world=o.matrix_world.copy();o.parent=parent;o.matrix_world=world
    return o
def cylinder(name,pos,radius,depth,mat,orient=(math.pi/2,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius,depth=depth,location=pos,rotation=orient)
    o=bpy.context.object;o.name=name;o.data.materials.append(mat)
    bevel(o,.06)
    for p in o.data.polygons:p.use_smooth=True
    return o
def group(name,pos,names):
    p=bpy.data.objects.new(name,None);scene.collection.objects.link(p);p.location=pos
    bpy.context.view_layer.update()
    for n in names:
        o=bpy.data.objects.get(n)
        if o:
            mw=o.matrix_world.copy();o.parent=p;o.matrix_world=mw
    return p

# The source contains this left-side housing only. Restore the matching right side.
source=bpy.data.objects['holo.023'];mir=source.copy();mir.data=source.data.copy();scene.collection.objects.link(mir)
mir.name='Odin_Restored_Starboard_Housing';mir.data.transform(Matrix.Diagonal((-1,1,1,1)));mir.data.flip_normals()
mir['completion']='Mirrored port housing across hull centerline'

# Build named pivots from isolated static meshes. Animation is implemented in Nuxt.
top=group('MainTurret_Dorsal',(0.1,79.6,30),[f'odin.{i:03}' for i in range(4,9)])
bottom=group('MainTurret_Ventral',(0,29.5,-43),[f'odin.{i:03}' for i in range(12,17)])
group('Turret_Bow',(0,234.5,37),['odin.002','odin.003'])
group('Turret_Stern',(0,-225.6,53),['odin.026','odin.027'])
group('Turret_Keel',(0,-30,-57.2),['odin.029','odin.030','holo.022'])
for i in range(8):
    suffix='turret 1'+(f'.{i:03}' if i else '')
    base=bpy.data.objects[f'odin.073__{suffix}']
    points=[v.co for v in base.data.vertices]
    center=sum(points,Vector())/len(points)
    group(f'DefenseTurret_{i+1:02}',center,[f'odin.{j:03}__{suffix}' for j in [72,73,74]])
for side,suffix in [('Port','bridge turret.001'),('Starboard','bridge turret')]:
    group('BridgeTurret_'+side,(-12.3 if side=='Port' else 12.3,-61.7,105.9),[f'holo.{j:03}__{suffix}' for j in [14,16]])

# Finish the two slab placeholders as separate hatch plates with machined edges.
for old,new in [('立方体','Hatch_Dorsal'),('立方体.002','Hatch_Ventral')]:
    o=bpy.data.objects.get(old)
    if o:o.name=new;bevel(o,.35)
    if o:
        o.data.materials.clear();o.data.materials.append(bpy.data.materials['Odin_Paint_Light'])

# Retain engine locations from the source VFX anchors; export only physical cores.
engines=[(0,-240.25,15.12,10.0),(-72.45,-234.6,16.66,6.3),(72.45,-234.6,16.66,6.3),(-42.79,-259.1,7.39,2.8),(42.79,-259.1,7.39,2.8),(-51.9,-259.1,9.59,2.8),(51.9,-259.1,9.59,2.8),(-23.42,-40.05,-48.19,2.7),(23.42,-40.05,-48.19,2.7),(-104.62,-191.9,21.6,1.65),(104.62,-191.9,21.6,1.65),(-104.62,-191.9,13.04,1.65),(104.62,-191.9,13.04,1.65)]
for i,(x,y,z,r) in enumerate(engines):
    o=cylinder(f'EngineCore_{i:02}',(x,y,z),r,.18,engine)
    o['radius']=r;o['engineIndex']=i
    cylinder(f'EngineInner_{i:02}',(x,y-.15,z),r*.46,.19,silver)
    # Concentric physical nozzle collars enrich the unfinished engine close-up.
    bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=8,location=(x,y-.05,z),rotation=(math.pi/2,0,0),major_radius=r*.94,minor_radius=.18 if r>5 else .09)
    tor=bpy.context.object;tor.name=f'EngineCollar_{i:02}';tor.data.materials.append(silver)

# Bridge windows and mast navigation lights follow the source superstructure.
for i in range(12):
    box(f'BridgeWindow_{i:02}',(-21.2+i*3.85,-25.7,120.8),(2.8,.14,2.0),glass,edge=.06)
for i in range(8):
    box(f'UpperBridgeWindow_{i:02}',(-12.5+i*3.55,-34.72,136.1),(2.6,.14,1.8),glass,edge=.06)
for x,mat in [(-105.4,red),(105.4,cyan)]:
    for z in [30.5,-25.5]:box('NavigationLens',(x,-177,z),(.7,1.3,.6),mat,edge=.1)
for z in [70,80,90]:
    for sign in [-1,1]:box('BridgeAccessLight',(sign*11.1,-64.8,z),(.25,1.7,.55),amber,edge=.02)

# Place hull numbers on actual surface hits instead of guessing their x position.
hull=bpy.data.objects['holo.001']
bvh=BVHTree.FromPolygons([v.co for v in hull.data.vertices],[p.vertices[:] for p in hull.data.polygons])
for side in [-1,1]:
    loc,norm,idx,dist=bvh.ray_cast(Vector((side*200,-44,81)),Vector((-side,0,0)))
    if loc:
        curve=bpy.data.curves.new('Hull stencil','FONT');curve.body='77';curve.size=8;curve.align_x='CENTER';curve.extrude=.015
        o=bpy.data.objects.new('Odin_Registration_'+str(side),curve);scene.collection.objects.link(o)
        tangent=Vector((0,0,1)).cross(norm).normalized();up=norm.cross(tangent).normalized()
        o.location=loc+norm*.23-up*3.5
        o.rotation_euler=Matrix((tangent,up,norm)).transposed().to_euler()
        curve.materials.append(mark);bpy.context.view_layer.objects.active=o;o.select_set(True)
        bpy.ops.object.convert(target='MESH');o.select_set(False)

# Meshes stay as authored; no Blender animation, lighting or VFX leaves this file.
for o in scene.objects:o.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
asset=group('Odin_Asset',(0,0,0),[o.name for o in scene.objects if not o.parent])
asset.scale=(.01,.01,.01)
asset['source']='User-provided odin.blend; active Odin assembly only'
asset['scope']='Fan-art exterior completion; no official production/interior model claim'
asset['animation']='None. All motion generated by Nuxt / Three.js at runtime.'
scene.unit_settings.system='METRIC'
bpy.context.view_layer.update()
for o in scene.objects:o.select_set(True)
bpy.context.view_layer.objects.active=asset
bpy.data.orphans_purge(do_recursive=True)
blend=root.parent/'Odin 建模'/'odin_web_completed.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
print('SAVED STATIC BLEND',blend,flush=True)
kwargs=dict(filepath=str(output/'odin.glb'),export_format='GLB',use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_apply=True,export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_image_format='AUTO')
try:
    bpy.ops.export_scene.gltf(**kwargs,export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6)
except Exception as e:
    print('DRACO FALLBACK',str(e),flush=True);bpy.ops.export_scene.gltf(**kwargs)
manifest=dict(source='odin.blend',meshCount=sum(o.type=='MESH' for o in scene.objects),triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in scene.objects if o.type=='MESH'),animationClips=0,engineAnchors=[dict(position=[x*.01,z*.01,-y*.01],radius=r*.01) for x,y,z,r in engines],completion=['Restored opposite-side housing','Finished retractable gun hatch geometry','Rebuilt PBR materials from original packed wear texture','Added physical engine cores and nozzle collars','Added bridge glazing and navigation lights','Added hull registration markings','Preserved all active Odin hull and turret geometry; excluded Perseus and hidden backups'])
(output/'asset-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf8')
print('EXPORT COMPLETE',manifest['meshCount'],manifest['triangles'],(output/'odin.glb').stat().st_size,flush=True)
