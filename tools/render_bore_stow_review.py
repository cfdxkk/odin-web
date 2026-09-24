"""Front oblique views of stowed bores after the bay armor has cleared."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Quaternion, Vector

root = Path(__file__).resolve().parents[1]
version = sys.argv[sys.argv.index('--')+1]
expected = root/f'assets/blender/odin_articulated_v{version}.blend'
if Path(bpy.data.filepath).resolve() != expected.resolve():
    raise RuntimeError('Load the requested versioned model')
poses = json.loads((root/'work/rig-review/poses.json').read_text(encoding='utf8'))
output = root/f'docs/review/v{version}'
output.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1200; scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.light = 'STUDIO'
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.background_type = 'WORLD'
scene.world.color = (.045,.055,.07)
camera = bpy.data.objects.new('BoreStowReview',bpy.data.cameras.new('BoreStowReview'))
scene.collection.objects.link(camera); scene.camera = camera
camera.data.type = 'ORTHO'; camera.data.clip_end = 100
basis = Quaternion((1,0,0),-math.pi/2)
pose = min(poses,key=lambda p: abs(p['deployment']-.34))
for joint in pose['joints']:
    obj=bpy.data.objects[joint['name']]
    x,y,z=joint['position']; obj.location=(x,-z,y)
    q=joint['quaternion']; obj.rotation_mode='QUATERNION'
    obj.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
bpy.context.view_layer.update()
for bank, target, direction in [('dorsal',(0,133,45),(.35,1,.58)),('ventral',(0,87,-53),(.35,1,-.58))]:
    aim=Vector(target)*.01
    camera.location=aim+Vector(direction)*4
    camera.rotation_euler=(aim-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=1.3
    scene.render.filepath=str(output/f'{bank}-bore-stow.png')
    bpy.ops.render.render(write_still=True)
print('Rendered stow poses with cleared armor; editable source not saved',flush=True)
