"""Move only the bow armor joints onto the already relocated source receiver.

The v0.11.15 flank-derived leaves and nose cap were fitted against a v0.10
slot frame.  The untouched bow receiver was later translated rigidly in
v0.11.12, so those seven armor joints sat aft and below their contact lip.
Their meshes, hinge axes, articulation distances and gun motion stay intact.
"""

import bpy
from pathlib import Path
from mathutils import Vector


root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.15'
receiver = bpy.data.objects['Axial_Bow_SourceReceiver']
shift = Vector(receiver['receiverShiftModel'])
assert all(abs(actual - expected) < 1e-5 for actual, expected in zip(shift, (0, 3.45, .55)))

names = [f'Axial_Bow_Shutter_{side}_{index:02d}'
         for side in ('Port', 'Starboard') for index in range(3)]
names.append('Axial_Bow_FrontCap')


def translated(points):
    return [(Vector(point) + shift)[:] for point in points]


for name in names:
    joint = bpy.data.objects[name]
    assert joint.parent == asset and joint.get('staticJoint')
    original_children = [(child.name, tuple(tuple(vertex.co) for vertex in child.data.vertices))
                         for child in joint.children if child.type == 'MESH']
    joint.location += shift
    if name != 'Axial_Bow_FrontCap':
        joint['hingeEdgeModel'] = translated(joint['hingeEdgeModel'])
        joint['closedEndEdgesModel'] = [translated(edge) for edge in joint['closedEndEdgesModel']]
    joint['receiverDatumShiftModel'] = shift[:]
    assert original_children == [
        (child.name, tuple(tuple(vertex.co) for vertex in child.data.vertices))
        for child in joint.children if child.type == 'MESH'
    ], f'{name} mesh changed while aligning the joint'

asset['version'] = '0.11.16'
asset['bowArmorRevision'] = 'seven unchanged armor meshes translated with the restored source receiver'
output = root / 'assets/blender/odin_articulated_v0.11.16.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('BOW ARMOR ALIGNED TO RECEIVER', tuple(shift), output, flush=True)
