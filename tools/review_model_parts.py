import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1];out=root/'work/parts-review';out.mkdir(exist_ok=True)
s=bpy.context.scene
names=['odin.004','odin.005','odin.006','odin.021','odin.023','odin.070','odin.071','holo.014__bridge turret','holo.016__bridge turret','holo.010','holo.011']
meshes=[o for o in s.objects if o.type=='MESH']
for o in meshes:o.hide_render=True
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=900;s.render.resolution_y=650;s.render.resolution_percentage=100
s.display.shading.color_type='MATERIAL';s.display.shading.light='STUDIO';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.background_type='WORLD';s.world.color=(.025,.03,.04)
c=bpy.data.objects.new('ReviewCamera',bpy.data.cameras.new('ReviewCamera'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.clip_end=100
data={}
for name in names:
 o=bpy.data.objects.get(name)
 if not o:continue
 o.hide_render=False;bpy.context.view_layer.update()
 pts=[o.matrix_world@v.co for v in o.data.vertices]
 low=Vector([min(p[i] for p in pts) for i in range(3)]);high=Vector([max(p[i] for p in pts) for i in range(3)])
 center=(low+high)*.5;extent=max(high-low);c.data.ortho_scale=extent*1.3
 c.location=center+Vector((1.05,1.6,1.25))*extent;c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(out/(name.replace(' ','_')+'.png'));bpy.ops.render.render(write_still=True);o.hide_render=True
 data[name]={'bounds':[list(low/.01),list(high/.01)],'verts':len(pts)}
(out/'parts.json').write_text(json.dumps(data,indent=2),encoding='utf8')
