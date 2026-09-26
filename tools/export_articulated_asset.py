"""Export static, independently articulated high/lite GLBs; no animation clips."""
import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset']
version=str(asset['version'])
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
 bpy.ops.export_scene.gltf(filepath=str(root/'public/models'/name),export_format='GLB',use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_yup=True,export_materials='EXPORT',export_image_format='WEBP',export_image_quality=95,export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=7,export_draco_position_quantization=18,export_draco_normal_quantization=12,export_draco_texcoord_quantization=14)
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
d.update(version=version,meshCount=sum(o.type=='MESH' for o in bpy.context.scene.objects),triangles=high,animationClips=0,articulatedSource=f'assets/blender/odin_articulated_v{version}.blend',bridgeArmorSlats=45,rigSystems=['main','main-hatch','main-bore-carriage','main-telescope','secondary','axial-shutter','defense','pdc','bridge-armor','stern-door'])
d['webOptimization']={'batchedMeshes':sum(o.type=='MESH' for o in bpy.context.scene.objects),'highTriangles':high,'liteTriangles':low,'highBytes':(root/'public/models/odin.glb').stat().st_size,'liteBytes':(root/'public/models/odin-lite.glb').stat().st_size,'highTextureResolution':2048,'highPositionQuantization':18}
d['completion']=['Five-piece main bay armor: two polygonal forward skins, two independent gap fillers hinging outward 130 degrees along the inclined hull lip; intact fixed hull and fitted serrated seams, and the serrated fore-end cap that lifts then slides forward; dark red inward-facing armor surfaces','Main guns wait until all five armor pieces clear their travel corridor','Synchronized three-bore main-barrel telescopic tubes, measured center-bore axes','Six original axial shutter half-banks','Parallel quad gun slides and short gunner-pod travel','Recovered front bridge armor separated from the hull','Original hidden aft door and frame restored','Original-style gray charcoal and orange albedo with 2K wear maps']
d['completion']=list(dict.fromkeys(d['completion']))
d['completion'] += ['Aft armor leaves are single inclined planes with constant thickness and fitted edges', 'Independent complete bore carriages retain a high center bore beneath its top cover while the outer bores stow lower and inward; original deployed geometry retained']
d['completion'] += ['Each complete main bore follows its physical shroud rigidly; side bores finish nesting only after the covers seat', 'Deep-red main turret bearing drums, housing cavity faces and all inward armor surfaces; existing gray exterior retained']
if version=='0.9.0':
 d['rigSystems'] += ['single-shutter','defense-gate']
 d['completion'] += ['Eleven elevation-only singles with forward trunnions and seventy fitted triangular shutter leaves', 'Eight twin gun elevations measured from their actual bores, four independent aft hull notch gates', 'Eight stationary quad root armor assemblies with shorter sliding tubes', 'Recovered rear bridge shield faces, separate glazing and roof tracks; warm charcoal bridge and tea-gold windows', 'Main bay stationary corner receivers follow the adjacent exterior hull plane']
if version in ['0.10.0','0.11.0']:
 d['bridgeArmorSlats']=0
 d['rigSystems']=[v for v in d['rigSystems']if v not in ['bridge-armor','axial-shutter']]+['single-shutter','single-front-cap','defense-gate','pdc-hull-petal']
 d['completion']=[v for v in d['completion']if 'bridge armor'not in v and 'axial shutter'not in v]
 d['completion'] += ['Eleven rear-trunnion single batteries with their original seven covers animated per mount; source front cap pose is the deployed endpoint', 'Fixed bridge with rectangular flush tea-gold glazing, airflow-aligned antennas with UV-painted bands, faceted radome and four truss-mounted capsule radars', 'Short upper capsule trusses attach to the original projecting bridge tab; rear capsule trusses extend diagonally aft', 'Eight independent quad aperture petals, narrowed support forks and deeper aft twin stow', 'All ten main battery armor plates reinforced inward while preserving accepted outer contours']
if version=='0.11.0':
 d['rigSystems']+=['side-front-slider','side-battery-leaf','side-battery-carriage']
 d['completion']=[v for v in d['completion']if not v.startswith('Eleven rear-trunnion')]
 d['completion']+=['Four vertical flank singles (port/starboard 1 and 3): eight armor halves in four groups; first pair lifts then slides forward; original vented leaves close around physical inner edges with a flat ridge', 'Complete rear flank cradle, barrel and groups 3/4 lift then advance together on closing; upper sloping and axial singles retain their prior mechanisms', 'Legacy flank tip wings removed; aft first-pair parking is allowed inside the hull as requested']
 d['completion']+=['Matching inclined seams between groups 2/3 and unequal-ended trapezoid first sliders', 'Original grate detail stays inside continuous smooth hull-painted skins; only the local triangular bay gaps receive mirrored infill']
manifest.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8');print('EXPORTED',d['webOptimization'],flush=True)
