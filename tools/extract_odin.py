import bpy, math, json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]
work=root/'work'
src=bpy.context.scene
dg=bpy.context.evaluated_depsgraph_get()
print('EXTRACT START',flush=True)
copies=[]
for inst in dg.object_instances:
    orig=inst.object.original
    if orig.type!='MESH' or orig.hide_render:continue
    if any(c.name in ['perseus','Collection','Collection 3','Collection 4','Collection 9','VFX'] for c in orig.users_collection):continue
    if not inst.is_instance and not orig.visible_get():continue
    if not inst.is_instance and not any(c.name in ['Collection 2','side gun','集合 10'] for c in orig.users_collection):continue
    mesh=bpy.data.meshes.new_from_object(inst.object,preserve_all_data_layers=True,depsgraph=dg)
    obj=bpy.data.objects.new(orig.name+('__'+inst.parent.original.name if inst.is_instance else ''),mesh)
    obj.matrix_world=inst.matrix_world.copy()
    obj['source_object']=orig.name
    obj['source_instance']=inst.parent.original.name if inst.is_instance else ''
    copies.append(obj)
print('MESH COPIES',len(copies),flush=True)
scene=bpy.data.scenes.new('Odin_Static_Asset')
bpy.context.window.scene=scene
for obj in copies:scene.collection.objects.link(obj)
for s in list(bpy.data.scenes):
    if s!=scene:bpy.data.scenes.remove(s)
# Remove original objects and dependencies only from this in-memory copy.
keep=set(copies)
bpy.data.batch_remove(ids=[o for o in bpy.data.objects if o not in keep])
for o in copies:o.name=o['source_object']+('__'+o['source_instance'] if o['source_instance'] else '')
print('SCENE ISOLATED',flush=True)
bpy.data.orphans_purge(do_recursive=True)
print('PURGED',flush=True)
palette={'Light':(0.25,0.30,0.32,1),'Dark':(0.06,0.075,0.085,1),'Orange':(0.6,0.055,0.013,1),'White':(0.46,0.50,0.52,1)}
for m in bpy.data.materials:
    key=next((k for k in palette if k in m.name),None)
    color=palette.get(key,(0.18,0.22,0.25,1))
    m.diffuse_color=color
    m.use_nodes=True
    m.node_tree.nodes.clear()
    bs=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled'); bs.inputs['Base Color'].default_value=color
    bs.inputs['Metallic'].default_value=0.52;bs.inputs['Roughness'].default_value=0.43
    output=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1500;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Inspection world')
scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=0.4
scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.world.color=(0.025,0.03,0.04)
scene.display.shading.show_specular_highlight=True
cam_data=bpy.data.cameras.new('InspectionCamera');cam=bpy.data.objects.new('InspectionCamera',cam_data);scene.collection.objects.link(cam);scene.camera=cam
cam_data.type='ORTHO';cam_data.ortho_scale=880;cam_data.clip_end=5000
target=Vector((0,20,20))
for name,pos in [('front',(650,1050,590)),('rear',(-650,-1050,420)),('side',(1200,0,120)),('top',(0,0,1600))]:
    print('RENDER',name,flush=True)
    cam.location=pos;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(work/f'odin-before-{name}.png');bpy.ops.render.render(write_still=True)
scene.render.filepath=''
bpy.ops.wm.save_as_mainfile(filepath=str(work/'odin-isolated.blend'),compress=True)
stats=[dict(name=o.name,vertices=len(o.data.vertices),triangles=sum(max(0,len(p.vertices)-2) for p in o.data.polygons),bounds=[[min((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)],[max((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)]]) for o in copies]
(work/'isolated-geometry.json').write_text(json.dumps(stats,indent=2),encoding='utf8')
print('EXTRACTED',len(copies),'meshes',sum(x['triangles'] for x in stats),'triangles')
