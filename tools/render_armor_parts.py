"""A static color key matching the user's five-piece annotation; never saved."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Quaternion
root=Path(__file__).resolve().parents[1];s=bpy.context.scene
basis=Quaternion((1,0,0),-math.pi/2)
for joint in json.loads((root/'work/rig-review/poses.json').read_text())[0]['joints']:
    obj=bpy.data.objects[joint['name']];x,y,z=joint['position'];obj.location=(x,-z,y)
    q=joint['quaternion'];obj.rotation_mode='QUATERNION'
    obj.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
bpy.context.view_layer.update()
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1500;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.display.shading.color_type='MATERIAL';s.display.shading.light='STUDIO';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.background_type='WORLD';s.world.color=(.045,.055,.07)
for role,color in [('Port',(1,.42,.7,1)),('Starboard',(.85,.055,.045,1)),('Nose',(.07,.72,.22,1)),('Aft_Port',(.025,.025,.03,1)),('Aft_Starboard',(1,.78,.015,1))]:
    material=bpy.data.materials.new('Review '+role);material.diffuse_color=color
    parent=bpy.data.objects[f'Hatch_Dorsal_{role}']
    for obj in parent.children:
        if obj.type=='MESH':
            obj.data.materials.clear();obj.data.materials.append(material)
c=bpy.data.objects.new('PartsReviewCamera',bpy.data.cameras.new('PartsReviewCamera'));s.collection.objects.link(c);s.camera=c
c.data.type='ORTHO';c.data.ortho_scale=1.75;c.data.clip_end=100
center=Vector((0,123,50))*.01;c.location=center+Vector((1,1,1.2))*4;c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(root/'docs/review/main-armor-parts.png');bpy.ops.render.render(write_still=True)
c.location=center+Vector((.12,.12,1.8))*4;c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(root/'docs/review/main-armor-parts-top.png');bpy.ops.render.render(write_still=True)
