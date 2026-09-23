"""Batch static geometry and export a second lightweight LOD. Does not modify the .blend."""
import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
asset=bpy.data.objects['Odin_Asset']
for o in list(bpy.context.scene.objects):
    if o.name.startswith('EngineCore_') or o.name=='Odin_Restored_Starboard_Housing':
        name=o.name;mw=o.matrix_world.copy();props=dict(o.items());o.name=name+'_Geometry'
        anchor=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(anchor)
        anchor.parent=asset;anchor.matrix_world=mw
        for k,v in props.items():anchor[k]=v
        anchor['geometryMergedInto']='Odin_StaticHull'

parents=[asset]+[o for o in list(bpy.context.scene.objects) if o.type=='EMPTY' and o.children and o!=asset]
for parent in parents:
    members=[o for o in parent.children if o.type=='MESH' and not o.name.startswith('Hatch_')]
    if len(members)<2:continue
    bpy.ops.object.select_all(action='DESELECT')
    sources=[o.name for o in members]
    for o in members:o.select_set(True)
    bpy.context.view_layer.objects.active=members[0];bpy.ops.object.join()
    joined=bpy.context.object;joined.name='Odin_StaticHull' if parent==asset else parent.name+'_Geometry'
    joined['sourceMeshNames']=sources

def export(name):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(root/'public/models'/name),export_format='GLB',use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_yup=True,export_materials='EXPORT',export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6)
    return sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in bpy.context.scene.objects if o.type=='MESH')

high=export('odin.glb')
for o in list(bpy.context.scene.objects):
    if o.type=='MESH' and len(o.data.polygons)>5000:
        bpy.context.view_layer.objects.active=o
        modifier=o.modifiers.new('Web lightweight LOD','DECIMATE');modifier.ratio=.34;modifier.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
low=export('odin-lite.glb')
manifest=root/'public/models/asset-manifest.json'
d=json.loads(manifest.read_text(encoding='utf8'));d['webOptimization']={'batchedMeshes':sum(o.type=='MESH' for o in bpy.context.scene.objects),'highTriangles':high,'liteTriangles':low,'highBytes':(root/'public/models/odin.glb').stat().st_size,'liteBytes':(root/'public/models/odin-lite.glb').stat().st_size}
manifest.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8')
print('OPTIMIZED',d['webOptimization'],flush=True)
