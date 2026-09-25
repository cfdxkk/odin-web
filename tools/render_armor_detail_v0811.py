import bpy,json,math
from pathlib import Path
from mathutils import Vector,Quaternion
R=Path(__file__).resolve().parents[1];out=R/'docs/review/v0.8.11';out.mkdir(exist_ok=True)
data=json.loads((R/'docs/review/v0.8.11/baseline-closed-pose.json').read_text(encoding='utf8'));prefix='after' if 'v0.8.11' in bpy.data.filepath else 'before'
basis=Quaternion((1,0,0),-math.pi/2)
for j in data['poses'][0]['joints']:
 if j['name'].startswith('Hatch_'):continue
 o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
bpy.context.view_layer.update()
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1400;s.render.resolution_y=900;s.render.resolution_percentage=100
s.display.shading.color_type='MATERIAL';s.display.shading.light='STUDIO';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.show_shadows=True;s.display.shading.background_type='WORLD';s.world.color=(.045,.055,.07)
cd=bpy.data.cameras.new('OrthoCheck');c=bpy.data.objects.new('OrthoCheck',cd);s.collection.objects.link(c);s.camera=c;cd.type='ORTHO';cd.clip_start=.01;cd.clip_end=100
for name,target,offset,scale in [('side',(9,116,42),(5,0,0),.32),('top',(7,117,44),(0,0,5),.36),('top-full',(0,108,43),(0,0,5),1.55),('side-full',(0,118,43),(5,0,0),1.35),('rear-oblique',(7,104,43),(1.2,-5,1.6),.8)]:
 target=Vector(target)*.01;c.location=target+Vector(offset);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=scale;s.render.filepath=str(out/(prefix+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
