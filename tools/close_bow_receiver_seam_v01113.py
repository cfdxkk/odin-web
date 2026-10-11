"""Close the bow receiver's diagonal shoulder without deforming source meshes.

The source bow housing is narrower than its receiver. Moving the whole
receiver far enough to hide the resulting diagonal opening would uncover the
stowed barrel. These two small stationary shoulder skins join their actual
mesh edges instead; the original receiver and gun meshes stay byte-for-byte
unchanged and the web-authored joints are left alone.
"""

import bpy
from pathlib import Path
from mathutils import Matrix


ROOT = Path(__file__).resolve().parents[1]
ASSET = bpy.data.objects['Odin_Asset']
assert str(ASSET['version']) == '0.11.12'
housing = bpy.data.objects['odin.003']
receiver = bpy.data.objects['Axial_Bow_SourceReceiver_Skin']
receiver_joint = bpy.data.objects['Axial_Bow_SourceReceiver']
assert all(abs(a - b) < 1e-5 for a, b in zip(receiver_joint.location, (0, 3.45, 0.55)))


def asset_point(obj, vertex_index):
    return ASSET.matrix_world.inverted() @ obj.matrix_world @ obj.data.vertices[vertex_index].co


# Ordered along the *outer* housing silhouette and the receiver's exposed
# shoulder. The prior inset housing edge left a visible triangular opening at
# the top of the seam in a close side view. Neither source mesh is edited.
HOUSING_EDGE = (1102, 779, 1101, 1458)
RECEIVER_EDGE = (4127, 4189, 4176, 4178)
PORT_HOUSING_EDGE = (1372, 1027, 1261, 1459)
PORT_RECEIVER_EDGE = (3870, 3932, 3919, 3921)
FACE_INDICES = (
    (0, 4, 5), (0, 5, 1),
    (1, 5, 6), (1, 6, 2),
    (2, 6, 7), (2, 7, 3),
)

fairing_joint = bpy.data.objects.new('Axial_Bow_SeamFairing', None)
bpy.context.scene.collection.objects.link(fairing_joint)
fairing_joint.parent = ASSET
fairing_joint.matrix_parent_inverse = Matrix.Identity(4)
fairing_joint.matrix_local = Matrix.Identity(4)
fairing_joint['staticJoint'] = True
fairing_joint['system'] = 'bow-receiver-seam'
fairing_joint['sourceMeshesPreserved'] = True

for side in ('Starboard', 'Port'):
    if side == 'Starboard':
        housing_ids = HOUSING_EDGE
        receiver_ids = RECEIVER_EDGE
    else:
        housing_ids = PORT_HOUSING_EDGE
        receiver_ids = PORT_RECEIVER_EDGE
    vertices = [asset_point(housing, i) for i in housing_ids] + [asset_point(receiver, i) for i in receiver_ids]
    faces = FACE_INDICES if side == 'Starboard' else tuple(tuple(reversed(face)) for face in FACE_INDICES)
    mesh = bpy.data.meshes.new('Axial_Bow_SeamFairing_' + side + '_Mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(bpy.data.materials['Odin_Paint_Light'])
    obj = bpy.data.objects.new('Axial_Bow_SeamFairing_' + side, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = fairing_joint
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_local = Matrix.Identity(4)
    obj['side'] = side
    obj['edgeSource'] = 'odin.003 + Axial_Bow_SourceReceiver_Skin'
    print('BOW_SEAM', side, 'VERTICES', len(mesh.vertices), 'FACES', len(mesh.polygons), flush=True)

ASSET['version'] = '0.11.13'
ASSET['bowRevision'] = 'source bow turret and rigid receiver preserved; stationary shoulder skins close both diagonal gaps'
assert not any(obj.animation_data and obj.animation_data.action for obj in bpy.context.scene.objects)
destination = ROOT / 'assets/blender/odin_articulated_v0.11.13.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
print('BOW_SEAM_SAVED', destination, flush=True)
