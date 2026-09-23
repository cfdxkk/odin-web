"""Static visual QA of poses calculated by the website, never saved as animation."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Quaternion
root=Path(__file__).resolve().parents[1];out=root/'work/rig-review';s=bpy.context.scene
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100
s.display.shading.color_type='MATERIAL';s.display.shading.light='STUDIO';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.show_shadows=True;s.display.shading.background_type='WORLD';s.world.color=(.045,.055,.07)
c=bpy.data.objects.new('ReviewCamera',bpy.data.cameras.new('ReviewCamera'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.clip_end=100
basis=Quaternion((1,0,0),-math.pi/2)
views=[('main',(0,123,50),(1,1,.9),1.65),('bridge',(0,-33,128),(1,1,.45),.70),('quad',(43,-61.7,106),(1,1,.5),.70),('bridge-rear',(0,-43,127),(1,-2,.7),.8),('ventral',(0,74,-55),(1,1,-.8),1.85),('defense',(35,-48,56),(1,.35,.8),1.2),('side',(0,-5,40),(1,.1,.18),6.6),('stern',(0,-174,-20),(.5,-1,-.65),2.1),('single',(0,240,44),(1,1,.6),.85)]
for pose in json.loads((out/'poses.json').read_text(encoding='utf8')):
 for j in pose['joints']:
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y)
  q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
 bpy.context.view_layer.update()
 for name,aim,direction,extent in views:
  center=Vector(aim)*.01;c.data.ortho_scale=extent;c.location=center+Vector(direction)*4
  c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler()
  s.render.filepath=str(out/f'{name}-{pose["deployment"]:.2f}.png');bpy.ops.render.render(write_still=True)
print('Static pose review complete',flush=True)
