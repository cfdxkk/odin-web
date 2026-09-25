"""Fixed side and inside views from the same exported JS poses as the film."""
import bpy, json, math, hashlib
from pathlib import Path
from mathutils import Vector, Quaternion

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'work/preview-v0.8.10/poses.json').read_text(encoding='utf8'))
assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()==data['blendSha256']
out=ROOT/'docs/review/v0.8.10';out.mkdir(parents=True,exist_ok=True)
basis=Quaternion((1,0,0),-math.pi/2)
def pose(d):
 for j in data['poses'][round(d*100)]['joints']:
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
 bpy.context.view_layer.update()
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1600;s.render.resolution_y=900;s.render.resolution_percentage=100
s.display.shading.color_type='MATERIAL';s.display.shading.light='STUDIO';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.show_shadows=True;s.display.shading.background_type='WORLD';s.world.color=(.045,.055,.07)
cd=bpy.data.cameras.new('ArmorDetail');c=bpy.data.objects.new('ArmorDetail',cd);s.collection.objects.link(c);s.camera=c;cd.type='ORTHO';cd.clip_start=.01;cd.clip_end=100
for name,d,center,offset,scale in [('side-closed',0,(0,124,45),(5,0,.14),1.05),('junction-closeup',0,(9,115,44),(5,0,.3),.38),('interior-open',1,(0,138,45),(3,-3,2.1),1.5),('hinge-midstroke',.23,(0,109,46),(3,-1.7,1.8),1.1)]:
 pose(d);target=Vector(center)*.01;c.location=target+Vector(offset);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=scale;s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
