"""Render the four flank mounts from side, above, below and astern at JS poses."""
import bpy,json,math,sys,argparse
from pathlib import Path
from mathutils import Vector,Quaternion

R=Path(__file__).resolve().parents[1]
out=R/'work/v0114-review/multiview';out.mkdir(parents=True,exist_ok=True)
rows=json.loads((R/'docs/review/v0.11.0/side-batteries.json').read_text())
poses=json.loads((R/'work/v0114-review/candidate-poses.json').read_text())
p=argparse.ArgumentParser();p.add_argument('--mounts',default=','.join(rows));p.add_argument('--poses',default='0,0.48,1');p.add_argument('--views',default='side,upper,lower,rear')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]if '--'in sys.argv else[])
mounts=a.mounts.split(',');selected_poses=[float(x)for x in a.poses.split(',')];views=a.views.split(',')
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1100;s.render.resolution_y=700;s.render.resolution_percentage=100
s.display.shading.color_type='MATERIAL';s.display.shading.light='STUDIO';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.show_shadows=True;s.display.shading.background_type='WORLD';s.world.color=(.045,.055,.07)
cd=bpy.data.cameras.new('FlankMultiview');camera=bpy.data.objects.new('FlankMultiview',cd);s.collection.objects.link(camera);s.camera=camera;cd.type='ORTHO';cd.clip_start=.01;cd.clip_end=100;cd.ortho_scale=.52
A=bpy.data.objects['Odin_Asset'];root=A.matrix_world;normal=root.to_3x3()
basis=Quaternion((1,0,0),-math.pi/2)
for requested in selected_poses:
    pose=min(poses,key=lambda p:abs(p['deployment']-requested))
    assert abs(pose['deployment']-requested)<.001
    for joint in pose['joints']:
        o=bpy.data.objects[joint['name']];x,y,z=joint['position'];o.location=(x,-z,y)
        q=joint['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
    bpy.context.view_layer.update()
    for name in mounts:
        row=rows[name];C=Vector(row['frameOrigin']);Q=row['frameAxes']
        X=Vector((Q[0][0],Q[1][0],Q[2][0]));B=Vector((Q[0][1],Q[1][1],Q[2][1]));N=Vector((Q[0][2],Q[1][2],Q[2][2]))
        target=root@(C+B*2)
        X=(normal@X).normalized();B=(normal@B).normalized();N=(normal@N).normalized()
        offsets={'side':N*.65-B*.05-X*.08,'upper':N*.60-X*.52,'lower':N*.60+X*.52,'rear':N*.50-B*.65-X*.07}
        for view in views:
            camera.location=target+offsets[view]
            camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
            s.render.filepath=str(out/f'{name}-{pose["deployment"]:.2f}-{view}.png')
            bpy.ops.render.render(write_still=True)
            print('RENDERED',name,pose['deployment'],view,flush=True)
