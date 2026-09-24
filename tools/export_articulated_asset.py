"""Export static, independently articulated high/lite GLBs; no animation clips."""
import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset']
for o in list(bpy.context.scene.objects):
 if o.name.startswith('EngineCore_'):
  name=o.name;mw=o.matrix_world.copy();props=dict(o.items());o.name=name+'_Geometry'
  a=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(a);a.parent=asset;a.matrix_world=mw
  for k,v in props.items():a[k]=v
for parent in [asset]+[o for o in bpy.context.scene.objects if o.type=='EMPTY' and o!=asset]:
 members=[o for o in parent.children if o.type=='MESH']
 if len(members)<2:continue
 bpy.ops.object.select_all(action='DESELECT')
 for o in members:o.select_set(True)
 bpy.context.view_layer.objects.active=members[0];bpy.ops.object.join();bpy.context.object.name=parent.name+'_Geometry'
def export(name):
 bpy.ops.object.select_all(action='SELECT')
 bpy.ops.export_scene.gltf(filepath=str(root/'public/models'/name),export_format='GLB',use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_yup=True,export_materials='EXPORT',export_image_format='WEBP',export_image_quality=95,export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=7,export_draco_position_quantization=16,export_draco_normal_quantization=12,export_draco_texcoord_quantization=14)
 return sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in bpy.context.scene.objects if o.type=='MESH')
high=export('odin.glb')
for im in bpy.data.images:
 if max(im.size)>1024:im.scale(1024,1024)
for o in list(bpy.context.scene.objects):
 if o.type=='MESH' and len(o.data.polygons)>3000:
  bpy.context.view_layer.objects.active=o;m=o.modifiers.new('Lightweight LOD','DECIMATE');m.ratio=.3;m.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=m.name)
  o.data.validate(clean_customdata=True);o.data.update()
low=export('odin-lite.glb')
manifest=root/'public/models/asset-manifest.json';d=json.loads(manifest.read_text(encoding='utf8'))
d.update(version='0.7.0',meshCount=sum(o.type=='MESH' for o in bpy.context.scene.objects),triangles=high,animationClips=0,articulatedSource='assets/blender/odin_articulated_v0.7.0.blend',bridgeArmorSlats=45,rigSystems=['main','main-hatch','main-telescope','secondary','axial-shutter','defense','pdc','bridge-armor','stern-door'])
d['webOptimization']={'batchedMeshes':sum(o.type=='MESH' for o in bpy.context.scene.objects),'highTriangles':high,'liteTriangles':low,'highBytes':(root/'public/models/odin.glb').stat().st_size,'liteBytes':(root/'public/models/odin-lite.glb').stat().st_size,'highTextureResolution':2048,'highPositionQuantization':16}
d['completion']=['Five-piece main bay armor: two polygonal forward skins, two independent gap fillers below the shrouds; intact fixed hull and fitted serrated seams, and the short fore-end wedge cap that lifts then slides forward','Main guns wait until all five armor pieces clear their travel corridor','Independent outer main-barrel telescopic tubes','Six original axial shutter half-banks','Parallel quad gun slides and short gunner-pod travel','Recovered front bridge armor separated from the hull','Original hidden aft door and frame restored','Original-style gray charcoal and orange albedo with 2K wear maps']
d['completion']=list(dict.fromkeys(d['completion']))
manifest.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8');print('EXPORTED',d['webOptimization'],flush=True)
