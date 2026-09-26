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
if version in ['0.10.0','0.11.0','0.11.1','0.11.2','0.11.3','0.11.4','0.11.5','0.11.6','0.11.7','0.11.8','0.11.9','0.11.10']:
 d['bridgeArmorSlats']=0
 d['rigSystems']=[v for v in d['rigSystems']if v not in ['bridge-armor','axial-shutter']]+['single-shutter','single-front-cap','defense-gate','pdc-hull-petal']
 d['completion']=[v for v in d['completion']if 'bridge armor'not in v and 'axial shutter'not in v]
 d['completion'] += ['Eleven rear-trunnion single batteries with their original seven covers animated per mount; source front cap pose is the deployed endpoint', 'Fixed bridge with rectangular flush tea-gold glazing, airflow-aligned antennas with UV-painted bands, faceted radome and four truss-mounted capsule radars', 'Short upper capsule trusses attach to the original projecting bridge tab; rear capsule trusses extend diagonally aft', 'Eight independent quad aperture petals, narrowed support forks and deeper aft twin stow', 'All ten main battery armor plates reinforced inward while preserving accepted outer contours']
if version in ['0.11.0','0.11.1','0.11.2','0.11.3','0.11.4','0.11.5','0.11.6','0.11.7','0.11.8','0.11.9','0.11.10']:
 d['rigSystems']+=['side-front-slider','side-battery-leaf','side-battery-carriage']
 d['completion']=[v for v in d['completion']if not v.startswith('Eleven rear-trunnion')]
 d['completion']+=['Four vertical flank singles (port/starboard 1 and 3): eight armor halves in four groups; first pair lifts then slides forward; original vented leaves close around physical inner edges with a flat ridge', 'Complete rear flank cradle, barrel and groups 3/4 lift then advance together on closing; upper sloping and axial singles retain their prior mechanisms', 'Legacy flank tip wings removed; aft first-pair parking is allowed inside the hull as requested']
 d['completion']+=['Matching inclined seams between groups 2/3 and unequal-ended trapezoid first sliders', 'Original grate detail stays inside continuous smooth hull-painted skins; only the local triangular bay gaps receive mirrored infill']
if version in ['0.11.1','0.11.2','0.11.3','0.11.4','0.11.5','0.11.6','0.11.7','0.11.8','0.11.9','0.11.10']:
 d['completion']+=['Fixed bay floors and transitions remain on the hull; only the rear pedestal, gun, bearings and groups 3/4 translate', 'Four centered single bores stow parallel to their channels with calibrated rear pivots; local transition and nose openings closed; interior stiffeners painted red']
 d['completion']+=['Fixed nose infill continues the original lower inner-slot nose plane without the former triangular depression']
 d['completion']+=['Aft first armor pair returns inward/down onto the original lower slot rim; leading contours remain clear of the larger outer hull surround']
if version in ['0.11.2','0.11.3','0.11.4','0.11.5','0.11.6','0.11.7','0.11.8','0.11.9','0.11.10']:
 d['completion']=[v for v in d['completion'] if not v.startswith('Aft first armor pair returns')]
 d['completion']+=['All four vertical flank mounts have smooth armor lower edges seated on the original inner rail; the first pair meets the original front lip without an outboard folded return']
if version=='0.11.3':
 d['completion']+=['Armor crowns return to their accepted flat top line while the lower edges retain their measured source-rail fit; all twenty-four hinged leaves rotate around their actual armor-to-slot contact edges']
if version=='0.11.4':
 d['completion']+=['All four vertical flank armor crowns sit at their source front-receiver height, removing the first plate ramp and aligning the closed top-view line', 'All eight vertical flank armor outer edges follow one straight plan-view rail per side, with their contact hinges rebaked on that rail', 'The eight front triangular seams are closed on the original lower nose panel rather than the upper fairing']
if version in ['0.11.5','0.11.6','0.11.7','0.11.8','0.11.9','0.11.10']:
 d['completion']+=['Side batteries 2 and 4 and all axial singles have smooth exterior armor, red inner reinforcements and physical contact-edge hinges; side 2 and 4 do not translate fore or aft', 'The keel single retains its separate final diagonal inboard stroke after all armor is stowed', 'Bridge hull armor has a neutral cement-gray finish']
 if version in ['0.11.5','0.11.6']:
  d['completion']+=['Aft defense twins 5–8 retain their former lateral travel and lower the complete carriage during final stow']
if version=='0.11.5':
 d['completion']+=['Thin red pinstripes run along the sloping bridge-base sidewalls']
if version in ['0.11.6','0.11.7','0.11.8','0.11.9','0.11.10']:
 d['completion']+=['The added bridge-base pinstripes are removed without changing the cement-gray paint area or palette']
if version in ['0.11.7','0.11.8']:
 d['completion']+=['Aft defense twins 5–8 keep retracting during the final 20% while the gun carriage and shared support rail sink together; the deeper inboard parked position clears the closed hull gates']
if version in ['0.11.8','0.11.9','0.11.10']:
 d['completion']+=['Long aft twin guides and lower support brackets reach the same inboard seat as the gun bodies with a small bounded lag, avoiding protrusion through the turret glazing; their vertical sink remains synchronized']
if version=='0.11.9':
 d['completion']+=['Aft twin gun carriages and shared rails begin one slow descent at 40% instead of a late turret lift, and park 2.7 source units farther outboard at a deeper closed-gate-safe level']
if version=='0.11.10':
 d['completion']+=['Aft twin carriages and shared rails retain their 40% descent onset and 2.7-unit outward correction, with the original four-unit sink restored']
d['completion']=list(dict.fromkeys(d['completion']))
manifest.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8');print('EXPORTED',d['webOptimization'],flush=True)
