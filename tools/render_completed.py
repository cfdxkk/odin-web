import bpy,math
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1];s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('ReviewWorld');s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.21,.3,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.45
def area(name,pos,power,color,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(2,4,7),2200,(.82,.88,1),7)
area('Rim',(-4,-2,4),2600,(.32,.56,1),5)
area('Fill',(5,-3,1),1400,(1,.46,.21),5)
d=bpy.data.cameras.new('ReviewCamera');o=bpy.data.objects.new('ReviewCamera',d);s.collection.objects.link(o);s.camera=o
d.type='ORTHO';d.ortho_scale=8.9
# Pose inspection only, not saved and not exported.
for n,dy,dz in [('Hatch_Dorsal',90,-9),('Hatch_Ventral',90,14)]:
    obj=bpy.data.objects.get(n);obj.location.y+=dy;obj.location.z+=dz
bpy.data.objects['MainTurret_Dorsal'].location.z+=12
bpy.data.objects['MainTurret_Ventral'].location.z-=12
for name,pos in [('hero',(8,9,5)),('engines',(-7,-10,4))]:
    o.location=pos;o.rotation_euler=(Vector((0,.2,.2))-o.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(root/'work'/f'completed-{name}.png');bpy.ops.render.render(write_still=True)
