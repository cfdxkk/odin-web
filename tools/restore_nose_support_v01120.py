"""Restore the stern's fixed nose support and fit the bow cap to its receiver.

Both source Blender files are read-only libraries. Source gun meshes and
keyframe-derived joints remain unchanged; only the fixed stern faces and the
bow cap's forward end are edited in the versioned output.
"""

import bpy
import bmesh
import json
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.19'
inverse_asset = asset.matrix_world.inverted()
frames = json.loads((root / 'docs/review/v0.10.0/source-covers.json').read_text())
reference_path = Path(r'D:\Odin\blender_test\odin_with_anime.blend')
assert reference_path.exists()
report = {}


def model_points(obj):
    matrix = inverse_asset @ obj.matrix_world
    return np.array([matrix @ vertex.co for vertex in obj.data.vertices])


def face_key(points):
    return tuple(sorted(tuple(round(float(value), 3) for value in point) for point in points))


with bpy.data.libraries.load(str(reference_path), link=False) as (source, destination):
    destination.objects = ['holo.001', 'single_behind_1st_armor']
reference_hull, reference_cap = destination.objects
assert len(reference_cap.data.polygons) == 66
reference_cap_points = np.array([reference_cap.matrix_world @ vertex.co
                                 for vertex in reference_cap.data.vertices])
cap = bpy.data.objects['Axial_Stern_FrontCap_Skin']
assert {face_key(model_points(cap)[list(face.vertices)]) for face in cap.data.polygons} == {
    face_key(reference_cap_points[list(face.vertices)]) for face in reference_cap.data.polygons
}, 'The moving stern plate must remain the exact named source shell'

# The separated source armor makes the fixed hull underneath unambiguous.
# Compare against every original fixed nose face already present, so recovery
# restores just the eight omitted support faces and cannot duplicate the roof.
stern_frame = frames['Axial_Stern']
stern_origin = np.array(stern_frame['frameOrigin'])
stern_axes = np.array(stern_frame['frameAxes'])
existing = set()
for name in ('holo.001', 'Axial_Stern_OriginalNoseRoof'):
    obj = bpy.data.objects[name]
    points = model_points(obj)
    local = (points - stern_origin) @ stern_axes
    for face in obj.data.polygons:
        coords = local[list(face.vertices)]
        if (np.max(np.abs(coords[:, 0])) < 6 and
                coords[:, 1].min() > 9 and coords[:, 1].max() < 38):
            existing.add(face_key(points[list(face.vertices)]))

reference_matrix = reference_hull.matrix_world.copy()
reference_points = np.array([reference_matrix @ vertex.co
                             for vertex in reference_hull.data.vertices])
reference_local = (reference_points - stern_origin) @ stern_axes
restore_faces = set()
for face in reference_hull.data.polygons:
    coords = reference_local[list(face.vertices)]
    low, high = coords.min(0), coords.max(0)
    if not (np.max(np.abs(coords[:, 0])) < 3.4 and
            low[1] > 15.3 and high[1] < 33.2 and
            low[2] > -3 and high[2] < 7.2):
        continue
    if face_key(reference_points[list(face.vertices)]) not in existing:
        restore_faces.add(face.index)
assert len(restore_faces) == 8, len(restore_faces)

support = reference_hull.copy()
support.data = reference_hull.data.copy()
support.animation_data_clear()
bpy.context.scene.collection.objects.link(support)
support.name = 'Axial_Stern_OriginalNoseSupport'
support.data.name = support.name
support.data.transform(reference_matrix)
support.parent = asset
support.matrix_parent_inverse = Matrix.Identity(4)
support.matrix_local = Matrix.Identity(4)
mesh = bmesh.new()
mesh.from_mesh(support.data)
mesh.faces.ensure_lookup_table()
bmesh.ops.delete(mesh, geom=[face for face in mesh.faces if face.index not in restore_faces], context='FACES')
bmesh.ops.delete(mesh, geom=[vertex for vertex in mesh.verts if not vertex.link_faces], context='VERTS')
mesh.to_mesh(support.data)
mesh.free()
support.data.update()
for index, material in enumerate(support.data.materials):
    label = material.name.lower() if material else ''
    name = ('Odin_Paint_Orange' if 'orange' in label else
            'Odin_Paint_Dark.001' if 'dark' in label else 'Odin_Paint_Light')
    support.data.materials[index] = bpy.data.materials[name]
support['restoredFrom'] = 'odin_with_anime.blend/holo.001 below single_behind_1st_armor'
support['sourceFaceCount'] = len(restore_faces)
support['stationarySourceSupport'] = True
support['sourceGeometry'] = True
report['sternRestoredFixedSupportFaces'] = len(restore_faces)
report['sternReferenceFaceIndices'] = sorted(restore_faces)
report['sternSourceSupportModelFaces'] = [reference_points[list(reference_hull.data.polygons[index].vertices)].tolist()
                                          for index in sorted(restore_faces)]

# The raised receiver starts on a diagonal, not a vertical end line. Take its
# outer seam and crown directly from the unchanged receiver; the cap's rear
# six vertices stay untouched. Refit only its two forward rings to that seam.
bow_frame = frames['Axial_Bow']
bow_origin = np.array(bow_frame['frameOrigin']) + np.array(
    bpy.data.objects['Axial_Bow_SourceReceiver']['receiverShiftModel'])
bow_axes = np.array(bow_frame['frameAxes'])
receiver = bpy.data.objects['Axial_Bow_SourceReceiver_Skin']
receiver_local = (model_points(receiver) - bow_origin) @ bow_axes
receiver_side = receiver_local[list(receiver.data.polygons[4939].vertices)]
lower = receiver_side[np.argmin(receiver_side[:, 1])]
upper = receiver_side[np.argmin(receiver_side[:, 0])]
ridge_points = receiver_local[list(receiver.data.polygons[4982].vertices)]
ridge = ridge_points[np.argmin(ridge_points[:, 1])]
assert 15.6 < lower[1] < 15.8 and 19.8 < upper[1] < 20.1 and 20.0 < ridge[1] < 20.1
gap = .02
bow_cap = bpy.data.objects['Axial_Bow_FrontCap']
closed_offset = np.array(bow_cap['slideVector']) + np.array(bow_cap['settleVector'])
before, after = {}, {}
for child in bow_cap.children:
    if child.type != 'MESH':
        continue
    matrix = inverse_asset @ child.matrix_world
    inverse = matrix.inverted()
    points = model_points(child)
    local = (points + closed_offset - bow_origin) @ bow_axes
    assert len(local) == 18 and len(child.data.polygons) == 16
    sign = -1 if '_Port' in child.name else 1
    rear_indices = (0, 1, 2, 9, 10, 11)
    rear = local[list(rear_indices)].copy()
    target = local.copy()
    target[6] = (sign * lower[0], lower[1] - gap, lower[2])
    target[7] = (sign * upper[0], upper[1] - gap, upper[2])
    target[8] = (local[8, 0], ridge[1] - gap, ridge[2])
    for outer, inner in ((6, 15), (7, 16), (8, 17)):
        target[inner] = target[outer] + (local[inner] - local[outer])
    for leading, shoulder in ((6, 3), (7, 4), (8, 5), (15, 12), (16, 13), (17, 14)):
        target[shoulder] = target[leading] + (local[shoulder] - local[leading])
        target[shoulder, 1] = target[leading, 1] - .24
    assert np.array_equal(target[list(rear_indices)], rear)
    before[child.name] = [local.min(0).tolist(), local.max(0).tolist()]
    after[child.name] = [target.min(0).tolist(), target.max(0).tolist()]
    for index, (vertex, point) in enumerate(zip(child.data.vertices, target)):
        if index in rear_indices:
            continue
        model = bow_origin + bow_axes @ point - closed_offset
        vertex.co = inverse @ Vector(model)
    child.data.update()
    child['forwardSeamFitsReceiver'] = True
    child['unchangedRearVertexCount'] = len(rear_indices)
    if sign == -1:
        bow_cap['closedCrownLineModel'] = [(bow_origin + bow_axes @ target[index]).tolist()
                                           for index in (2, 5, 8)]
bow_cap['receiverForeSeamLocal'] = [lower.tolist(), upper.tolist(), ridge.tolist()]
bow_cap['receiverForeSeamGap'] = gap
bow_cap['closedLengthLocal'] = max(value[1][1] for value in after.values()) - min(value[0][1] for value in after.values())
report['bowCapBoundsBefore'] = before
report['bowCapBoundsAfter'] = after
report['bowReceiverForeSeamLocal'] = [lower.tolist(), upper.tolist(), ridge.tolist()]
report['bowForeSeamGap'] = gap

for obj in (reference_hull, reference_cap):
    bpy.data.objects.remove(obj, do_unlink=True)
asset['version'] = '0.11.20'
asset['sternRestoredFixedNoseSupportFaces'] = 8
asset['sternSupportReference'] = 'odin_with_anime.blend/single_behind_1st_armor'
asset['bowCapClosedLengthLocal'] = bow_cap['closedLengthLocal']
review_dir = root / 'docs/review/v0.11.20'
review_dir.mkdir(parents=True, exist_ok=True)
(review_dir / 'source-fit.json').write_text(json.dumps(report, indent=2), encoding='utf8')
output = root / 'assets/blender/odin_articulated_v0.11.20.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('RESTORED_NOSE_SUPPORT_AND_FIT', output, len(restore_faces), bow_cap['closedLengthLocal'], flush=True)
