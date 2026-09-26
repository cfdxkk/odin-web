"""Render actual JS poses for every secondary family and bridge armor."""
import bpy,json,math,sys,argparse
from pathlib import Path
from mathutils import Vector,Quaternion
R=Path(__file__).resolve().parents[1];s=bpy.context.scene;version=str(bpy.data.objects['Odin_Asset']['version']);out=R/f'work/v{version.replace(".", "")}-review'
p=argparse.ArgumentParser();p.add_argument('--label',default='candidate');p.add_argument('--poses',default='candidate-poses.json');p.add_argument('--steps',default='0,0.5,1');p.add_argument('--views',default='');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]if '--'in sys.argv else[])
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1000;s.render.resolution_y=750;s.render.resolution_percentage=100
s.display.shading.color_type='MATERIAL';s.display.shading.light='STUDIO';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.show_shadows=True;s.display.shading.background_type='WORLD';s.world.color=(.045,.055,.07)
cd=bpy.data.cameras.new('SecondaryReview');c=bpy.data.objects.new('SecondaryReview',cd);s.collection.objects.link(c);s.camera=c;cd.type='ORTHO';cd.clip_start=.01;cd.clip_end=100
views=[('bow',(0,258,40),(1,1,.6),.7),('stern',(0,-248,52),(1,-1,.6),.7),('keel',(0,-58,-64),(1,-1,-.7),.95),('single1',(74,86,4),(2,1,.7),.7),('single2',(55,16,30),(2,1,.7),.7),('single3',(61,0,-28),(2,1,-.7),.7),('single4',(68,-170,29),(2,1,.7),.7),('defense',(36,-49,57),(1,1,.7),.85),('aft-defense',(28,-197,45),(1,1,.7),1.0),('bridge',(0,-36,128),(1,1,.40),.78),('bridge-side',(0,-31,129),(2,0,.1),.3),('bridge-rear',(0,-43,128),(1,-2,.4),.78),('quad',(43,-62,106),(1,1,.6),.5)]
views += [('main-side',(9,116,42),(5,0,0),.32),('main-top',(7,117,44),(0,0,5),.36)]
views += [('radars',(0,-50,119),(1,-1,.55),1.05),('window',(0,-24,91),(1,3,.5),.4),('single2-top',(55,16,30),(.3103,.1882,.9318),.72),('single2-side',(55,16,30),(.9389,.0927,-.3314),.72)]
views += [(name+'-port',(-target[0],target[1],target[2]),(-offset[0],offset[1],offset[2]),scale)for name,target,offset,scale in views if name in ['single1','single2','single3','single4','defense','aft-defense','quad']]
basis=Quaternion((1,0,0),-math.pi/2);steps=[float(v)for v in a.steps.split(',')]
for pose in json.loads((out/a.poses).read_text(encoding='utf8')):
 if not any(abs(pose['deployment']-d)<1e-6 for d in steps):continue
 for j in pose['joints']:
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
 bpy.context.view_layer.update()
 for name,target,offset,scale in views:
  if a.views and name not in a.views.split(','):continue
  target=Vector(target)*.01;c.location=target+Vector(offset);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=scale;s.render.filepath=str(out/f'{a.label}-{name}-{pose["deployment"]:.2f}.png');bpy.ops.render.render(write_still=True)
