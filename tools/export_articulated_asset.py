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
 staging=root/'work/asset-export';staging.mkdir(parents=True,exist_ok=True)
 temporary=staging/name
 bpy.ops.object.select_all(action='SELECT')
 bpy.ops.export_scene.gltf(filepath=str(temporary),export_format='GLB',use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_yup=True,export_materials='EXPORT',export_image_format='WEBP',export_image_quality=95,export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=7,export_draco_position_quantization=18,export_draco_normal_quantization=12,export_draco_texcoord_quantization=14)
 temporary.replace(root/'public/models'/name)
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
if version in ['0.10.0','0.11.0','0.11.1','0.11.2','0.11.3','0.11.4','0.11.5','0.11.6','0.11.7','0.11.8','0.11.9','0.11.10','0.11.11','0.11.12','0.11.13','0.11.14','0.11.15','0.11.16','0.11.17','0.11.18']:
 d['bridgeArmorSlats']=0
 d['rigSystems']=[v for v in d['rigSystems']if v not in ['bridge-armor','axial-shutter']]+['single-shutter','single-front-cap','defense-gate','pdc-hull-petal']
 d['completion']=[v for v in d['completion']if 'bridge armor'not in v and 'axial shutter'not in v]
 d['completion'] += ['Eleven rear-trunnion single batteries with their original seven covers animated per mount; source front cap pose is the deployed endpoint', 'Fixed bridge with rectangular flush tea-gold glazing, airflow-aligned antennas with UV-painted bands, faceted radome and four truss-mounted capsule radars', 'Short upper capsule trusses attach to the original projecting bridge tab; rear capsule trusses extend diagonally aft', 'Eight independent quad aperture petals, narrowed support forks and deeper aft twin stow', 'All ten main battery armor plates reinforced inward while preserving accepted outer contours']
if version in ['0.11.0','0.11.1','0.11.2','0.11.3','0.11.4','0.11.5','0.11.6','0.11.7','0.11.8','0.11.9','0.11.10','0.11.11','0.11.12','0.11.13','0.11.14','0.11.15','0.11.16','0.11.17','0.11.18']:
 d['rigSystems']+=['side-front-slider','side-battery-leaf','side-battery-carriage']
 d['completion']=[v for v in d['completion']if not v.startswith('Eleven rear-trunnion')]
 d['completion']+=['Four vertical flank singles (port/starboard 1 and 3): eight armor halves in four groups; first pair lifts then slides forward; original vented leaves close around physical inner edges with a flat ridge', 'Complete rear flank cradle, barrel and groups 3/4 lift then advance together on closing; upper sloping and axial singles retain their prior mechanisms', 'Legacy flank tip wings removed; aft first-pair parking is allowed inside the hull as requested']
 d['completion']+=['Matching inclined seams between groups 2/3 and unequal-ended trapezoid first sliders', 'Original grate detail stays inside continuous smooth hull-painted skins; only the local triangular bay gaps receive mirrored infill']
if version in ['0.11.1','0.11.2','0.11.3','0.11.4','0.11.5','0.11.6','0.11.7','0.11.8','0.11.9','0.11.10','0.11.11','0.11.12','0.11.13','0.11.14','0.11.15','0.11.16','0.11.17','0.11.18']:
 d['completion']+=['Fixed bay floors and transitions remain on the hull; only the rear pedestal, gun, bearings and groups 3/4 translate', 'Four centered single bores stow parallel to their channels with calibrated rear pivots; local transition and nose openings closed; interior stiffeners painted red']
 d['completion']+=['Fixed nose infill continues the original lower inner-slot nose plane without the former triangular depression']
 d['completion']+=['Aft first armor pair returns inward/down onto the original lower slot rim; leading contours remain clear of the larger outer hull surround']
if version in ['0.11.2','0.11.3','0.11.4','0.11.5','0.11.6','0.11.7','0.11.8','0.11.9','0.11.10','0.11.11','0.11.12','0.11.13','0.11.14','0.11.15','0.11.16','0.11.17','0.11.18']:
 d['completion']=[v for v in d['completion'] if not v.startswith('Aft first armor pair returns')]
 d['completion']+=['All four vertical flank mounts have smooth armor lower edges seated on the original inner rail; the first pair meets the original front lip without an outboard folded return']
if version=='0.11.3':
 d['completion']+=['Armor crowns return to their accepted flat top line while the lower edges retain their measured source-rail fit; all twenty-four hinged leaves rotate around their actual armor-to-slot contact edges']
if version=='0.11.4':
 d['completion']+=['All four vertical flank armor crowns sit at their source front-receiver height, removing the first plate ramp and aligning the closed top-view line', 'All eight vertical flank armor outer edges follow one straight plan-view rail per side, with their contact hinges rebaked on that rail', 'The eight front triangular seams are closed on the original lower nose panel rather than the upper fairing']
if version in ['0.11.5','0.11.6','0.11.7','0.11.8','0.11.9','0.11.10','0.11.11','0.11.12','0.11.13','0.11.14','0.11.15','0.11.16','0.11.17','0.11.18']:
 d['completion']+=['Side batteries 2 and 4 and all axial singles have smooth exterior armor, red inner reinforcements and physical contact-edge hinges; side 2 and 4 do not translate fore or aft', 'The keel single retains its separate final diagonal inboard stroke after all armor is stowed', 'Bridge hull armor has a neutral cement-gray finish']
 if version in ['0.11.5','0.11.6']:
  d['completion']+=['Aft defense twins 5–8 retain their former lateral travel and lower the complete carriage during final stow']
if version=='0.11.5':
 d['completion']+=['Thin red pinstripes run along the sloping bridge-base sidewalls']
if version in ['0.11.6','0.11.7','0.11.8','0.11.9','0.11.10','0.11.11','0.11.12','0.11.13','0.11.14','0.11.15','0.11.16','0.11.17','0.11.18']:
 d['completion']+=['The added bridge-base pinstripes are removed without changing the cement-gray paint area or palette']
if version in ['0.11.7','0.11.8']:
 d['completion']+=['Aft defense twins 5–8 keep retracting during the final 20% while the gun carriage and shared support rail sink together; the deeper inboard parked position clears the closed hull gates']
if version in ['0.11.8','0.11.9','0.11.10','0.11.11','0.11.12','0.11.13','0.11.14','0.11.15','0.11.16','0.11.17','0.11.18']:
 d['completion']+=['Long aft twin guides and lower support brackets reach the same inboard seat as the gun bodies with a small bounded lag, avoiding protrusion through the turret glazing; their vertical sink remains synchronized']
if version=='0.11.9':
 d['completion']+=['Aft twin gun carriages and shared rails begin one slow descent at 40% instead of a late turret lift, and park 2.7 source units farther outboard at a deeper closed-gate-safe level']
if version=='0.11.10':
 d['completion']+=['Aft twin carriages and shared rails retain their 40% descent onset and 2.7-unit outward correction, with the original four-unit sink restored']
if version in ['0.11.11','0.11.12','0.11.13','0.11.14','0.11.15','0.11.16','0.11.17','0.11.18']:
 d['completion']+=['The existing cement-gray bridge material now covers the aft dorsal spine, bridge-side apron, fore upper fairing and central fore-deck wedge while keeping equipment and the surrounding outer hull separate', 'Aft twin carriages and shared rails retain their 40% descent onset and 2.7-unit outward correction, with the original four-unit sink restored']
if version in ['0.11.12','0.11.13','0.11.14','0.11.15','0.11.16','0.11.17','0.11.18']:
 d['rigSystems']+=['bow-receiver']
 d['completion']=[item for item in d['completion'] if 'all axial singles' not in item and 'Eleven rear-trunnion single batteries' not in item]
 d['completion']+=['Only the bow single turret is restored from untouched odin.blend geometry; its source receiver, six side skirts and fifteen brackets move rigidly toward the turret seam without deformation, while the existing bow gun pivot, web rotation timing and stern remain unchanged']
if version in ['0.11.14','0.11.15','0.11.16','0.11.17','0.11.18']:
 d['completion']=[item for item in d['completion'] if 'Only the bow single turret is restored' not in item]
 d['completion']+=['Unrequested bow shoulder skins removed; the bow turret and receiver retain source geometry and the accepted rigid receiver position', 'The original odin.blend bow gun location and Euler keyframes (frames 30–56) are reproduced in Nuxt']
if version in ['0.11.15','0.11.16','0.11.17','0.11.18']:
 d['completion']=[item for item in d['completion'] if 'upper sloping and axial singles retain their prior mechanisms' not in item]
 d['completion']+=['Bow and stern singles each have six flank-derived contact-edge hinged armor shutters and one translating front cap; the muzzle-end shutters close first after the gun lowers, and neither turret mount translates after closure']
if version in ['0.11.17','0.11.18']:
 d['completion']+=['The original odin.blend stern gun location and Euler keyframes (frames 11–37) are reproduced in Nuxt; source barrel actions remain unchanged', 'Bow and stern armor crowns and breech trapezoids meet their existing turret housings; the nose cap lifts before translating forward']
if version=='0.11.18':
 d['completion']=[item for item in d['completion'] if not item.startswith('Bow and stern singles each have six flank-derived')]
 d['completion']+=['The redundant rear substitute is removed; the stern moving nose cover uses the eight original odin.blend roof faces at the farther-forward source position', 'Stern bore static geometry is aligned point-for-point to the original odin.blend closed pose without changing its action', 'The original stern trough shoulder and fixed forward hull are restored without reshaping their source faces', 'Bow front cap parks farther forward and lower along its existing incline, clearing the untouched source bore action']
if version in ('0.11.19','0.11.20','0.11.21','0.11.22','0.11.23','0.11.24','0.11.25','0.11.26','0.11.27','0.11.28','0.11.29','0.11.30','0.11.31','0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['bridgeArmorSlats']=0
 d['rigSystems']=[item for item in d['rigSystems'] if item not in ('bridge-armor','axial-shutter')]+['single-shutter','single-front-cap','side-front-slider','side-battery-leaf','side-battery-carriage','defense-gate','pdc-hull-petal','bow-receiver']
 d['completion']=[item for item in d['completion'] if 'axial shutter' not in item and 'bridge armor' not in item]
 d['completion']+=['Original bow and stern barrel keyframes remain authored in Nuxt, with no GLB animation clips', 'The stern moving nose plate uses the original disconnected 66-face armor shell from odin.blend; the misplaced triangle and duplicate vented leaves are removed', 'Six stern shutters retain their fitted closed seams and stop after a 95-degree opening sweep', 'The bow muzzle channel extends two units down the deck incline and its foremost plate has an inclined end seam aligned with the fixed deck', 'The inward surfaces of the bow and all eight flank bore channels use deep-red paint without recoloring their exterior armor', 'Main, secondary, defense, PDC and bridge mechanisms retain their established motions']
if version in ('0.11.20','0.11.21','0.11.22','0.11.23','0.11.24','0.11.25','0.11.26','0.11.27','0.11.28','0.11.29','0.11.30','0.11.31','0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['completion']=[item for item in d['completion'] if 'disconnected 66-face' not in item or 'misplaced triangle' not in item]
 d['completion']+=['The stern nose plate is the exact single_behind_1st_armor shell; the eight fixed support faces beneath it are restored at their original source coordinates', 'The bow foremost plate is shortened along the existing receiver diagonal and meets its raised lip and crown while its fitted rear seam remains unchanged']
if version in ('0.11.21','0.11.22','0.11.23','0.11.24','0.11.25','0.11.26','0.11.27','0.11.28','0.11.29','0.11.30','0.11.31','0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['completion']=[item for item in d['completion'] if 'exact single_behind_1st_armor' not in item or 'eight fixed support' not in item]
 d['completion']+=['The stern source nose shell has a slightly narrowed central seam; its eight fixed source support faces remain unchanged', 'Six floating bow receiver skirts are removed while its fitted channel and bore supports remain', 'Extended stationary stern slot lips close the gap to the six hinged leaves', 'The keel bay stays at the former 14% whole-assembly position at every deployment progress; it uses six fitted flank-derived leaves and one source nose cover with the stern opening sequence', 'Keel inward armor surfaces, supports and bore channel use deep-red paint']
if version in ('0.11.22','0.11.23','0.11.24','0.11.25','0.11.26','0.11.27','0.11.28','0.11.29','0.11.30','0.11.31','0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['completion']=[item for item in d['completion'] if not item.startswith('The stern source nose shell has a slightly narrowed')]
 d['completion']+=['Stern and keel source nose shells retain their topology and curled edges while their full rear profiles match the adjacent shutters and their full leading diagonals match the original fixed receivers', 'All stern and keel shutter crowns share continuous widths, crown planes and narrow center seams; the rear edges meet their unchanged gun-root housings', 'Six missing original keel fixed nose support faces are restored from odin.blend; the former 14-percent seat and original barrel actions remain unchanged']
if version=='0.11.23':
 d['completion']+=['Stern and keel crown lines continue across all six shutters and the original nose cover to the unchanged fixed receiver', 'Port and starboard side singles 2 and 4 use six accepted flank-derived vented leaves with red inner skins and their own original fitted nose cap; the cap lifts before advancing, shutters sweep 95 degrees before the unchanged barrel action starts', 'Only the 24 side single cover contact hinges are re-fitted; all other 163 joint transforms and every gun and fixed hull mesh remain unchanged']
if version=='0.11.24':
 d['completion'] += ['Side singles 2 and 4 recover their original fixed trough and turret support faces from odin.blend; no fixed source faces are assigned to armor joints', 'Their original double-shell front caps retain their shape and UVs with a rigid outward clearance offset; added lower sealing returns meet the unchanged receiver, then the caps lift and advance', 'All original source channel walls, raised grates and triangular braces remain fixed; six missing outer covers reuse the completed flank armor assets with red inward reinforcement and contact-edge hinges', 'All four side 2/4 barrels retain their exact source geometry, fixed locations and three-channel Euler curves in Nuxt; handmade sinks and pitch offsets are removed', 'The accepted stern and keel continuous crown lines and all other weapon geometry and joints remain unchanged']
if version in ('0.11.25','0.11.26','0.11.27','0.11.28','0.11.29','0.11.30','0.11.31','0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['rigSystems'] += ['single-source-carriage']
 d['completion'] += ['Side singles 2 and 4 use their six original vented armor assemblies and original nose shells from odin.blend, with source topology and UVs retained and red inward faces', 'The source rear turret shell, bore and final armor pair rise together; closing retracts the bore, seats the shell forward and down, then folds the armor', 'The bore roots and their physical pivots share the requested upward and rearward rigid offset; a small rest-angle correction lowers the muzzle, while the source three-channel Euler action remains intact', 'The original stationary trough, cheek supports and lower mount bearings remain fixed; no substitute armor skins or copied side-1 leaves remain on side 2/4']
if version in ('0.11.26','0.11.27','0.11.28','0.11.29','0.11.30','0.11.31','0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['completion']=[item for item in d['completion'] if 'source topology and UVs retained' not in item]
 d['completion'] += ['The existing six source flank leaves and nose shells gain continuous gray exterior shoulders and a flat crown, with deep-red inward returns and narrow closed seams', 'Original outer rail belt panels are restored on both ship sides as fixed hull geometry; outward cheek faces are aligned to the closed armor plane', 'Side 2 and 4 leaf sweeps stop at their previous front-leaf 20-percent and 18-percent orientations respectively; original bore curves, corrected pivots, carriage stroke and motion order remain unchanged', 'Both original side-4 elevation linkages follow their barrel curves from the correct closed pose; their source polygons and UVs are retained']
if version=='0.11.27':
 d['completion'] += ['The small source exterior end triangles and rolled rails of side 2/4 covers share aligned closed profiles; gray inner seam returns prevent views through bank and nose joints', 'The front nose rear profile meets the adjacent original leaf; its original leading receiver edge is unchanged', 'The obsolete fixed mirrored starboard side-4 housing is removed while its two fixed bearing islands retain their original geometry, UVs and coordinates', 'All 191 joint transforms and motion metadata remain unchanged from v0.11.26, including the limited opening stops and original barrel/carriage/cap phases']
if version in ('0.11.28','0.11.29','0.11.30','0.11.31','0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['completion']=[item for item in d['completion'] if 'original leading receiver edge is unchanged' not in item and not item.startswith('All 191 joint transforms and motion metadata remain unchanged')]
 d['completion'] += ['Side 2/4 source covers use one lower straight crown profile across all six leaves, the nose and the fitted fixed receiver; the flat crown is 0.60 source units wide', 'Only the two isolated side-4 floating triangles are removed; original grate topology and UVs are retained, and barrel pivots, source Euler curves, carriage timing and opening stops are unchanged']
if version in ('0.11.29','0.11.30','0.11.31','0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['completion']=[item.replace('original grate topology and UVs are retained','original grate surfaces and their texture coordinates are retained') for item in d['completion']]
 d['completion'] += ['All side 2/4 original hinged covers share one lower hull-seam rail; source inward lining is partitioned at the same bank boundaries with preserved surfaces and interpolated UVs', 'The original fixed outer cheek lips continue the common hinge line without a step; front caps lift and advance without settling downward']
if version in ('0.11.30','0.11.31','0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['completion'] += ['The eight original side 2/4 rear armor ends follow the two measured source turret-root bevels, with closed cut ends and red inward lining; all joints, source housings, bore actions and front-cap motions are unchanged']
if version in ('0.11.31','0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['completion']=[item for item in d['completion'] if not any(label in item for label in ['Parallel quad gun slides and short gunner-pod travel', 'Eight stationary quad root armor', 'Eight independent quad aperture petals'])]
 d['completion'] += ['Both complete bridge quads recover all 5001 original gun vertices and 1602 original support vertices, with intact source topology and UVs; carriage motion stops at source frame 30 in NAV and original aiming channels are restored', 'The original tubes retract farther independently of their gray rear cradles; after carriage stow, four cradles and four unpainted original hull petals compact toward each quad center together', 'Side-2 original outer rail belt panels recover their source light top and dark side materials']
if version in ('0.11.32','0.11.33','0.11.34','0.11.35','0.11.36'):
 d['completion'] += ['Bridge quad extra tube travel ends at the former v0.11.31 11-percent tube position, shortening the stroke by 55 percent', 'The four original gray petals align to their source hull receiver normals, then contract directly toward the quad center without axial retreat or a clearance detour; gray cradles compact with the tubes after frame-30 carriage seating']
if version=='0.11.33':
 d['completion']=[item for item in d['completion']if 'align to their source hull receiver normals' not in item]
 d['completion'] += ['All eight original gray bridge quad petals keep their source orientation and every vertex X coordinate throughout translation-only closure; their original forward edges join fitted stationary hull lips in NAV', 'Only 32 fixed hull lip vertices are adjusted at the eight original petal junctions; original petal surfaces, UVs, full tube reach, gray guide packing and frame-30 carriage stop are retained']
if version in ('0.11.34','0.11.35','0.11.36'):
 d['completion']=[item for item in d['completion']if 'align to their source hull receiver normals' not in item]
 d['completion'] += ['The eight original bridge quad petals make one monotonic vertical stroke and hold the open endpoint from 18 percent; no late descent, rotation or ship X displacement remains', 'Each complete outer petal skin is fitted in Z to its actual adjoining roof face, retaining all original 26 vertices, source topology, UVs and X/Y footprint; the prior 32 fixed lip edits are unchanged', 'All eight quad armor skins share the adjoining Odin_Bridge_Armor material; complete original tubes, support, gray guide packing and the frame-30 carriage stop are retained']
if version=='0.11.35':
 d['completion'] += ['Aft twin covers 5–8 follow their actual source aperture rims with planar exterior skins and local source-shell thickness; mirrored covers 6/8 use the exterior rim corners rather than the recessed inner lip', 'All four gate translation vectors, carriage/rail timing, gun geometry and other static joints remain unchanged']
if version=='0.11.36':
 d['completion'] += ['Aft twin gates 5–8 match the original full fore/aft cut profiles and all 56 lower return sections per receiver; independently lofted inner skins reproduce the adjoining tapered shell cross-section', 'Only four gate meshes change; the immutable source hull, all other weapon geometry and all 207 static joint frames and motion properties remain unchanged']
if version=='0.11.13':
 d['rigSystems']+=['bow-receiver-seam']
 d['completion']+=['Mirrored stationary bow shoulder skins join the untouched turret housing and rigid source receiver along the full diagonal seam without changing the original barrel motion']
d['completion']=list(dict.fromkeys(d['completion']))
manifest.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8');print('EXPORTED',d['webOptimization'],flush=True)
