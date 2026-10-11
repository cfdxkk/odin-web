"""Check the saved bow fit and source-restored fixed stern support before export."""
import bpy
import json
import hashlib
import numpy as np
from pathlib import Path

root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.20'
scene_objects = {obj.name: obj for obj in bpy.context.scene.objects}
report_path = root / 'docs/review/v0.11.20/source-fit.json'
report = json.loads(report_path.read_text())
inverse_asset = asset.matrix_world.inverted()


def vertices(obj):
    result = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', result)
    return result.reshape(-1, 3)


def model_points(obj):
    matrix = inverse_asset @ obj.matrix_world
    return np.array([matrix @ vertex.co for vertex in obj.data.vertices])


def face_key(points):
    return tuple(sorted(tuple(round(float(value), 3) for value in point) for point in points))


support = scene_objects['Axial_Stern_OriginalNoseSupport']
assert support.parent == asset and len(support.data.polygons) == 8
support_points = model_points(support)
assert {face_key(support_points[list(face.vertices)]) for face in support.data.polygons} == {
    face_key(face) for face in report['sternSourceSupportModelFaces']
}, 'Fixed support must have exactly the reference faces at unchanged coordinates'

frames = json.loads((root / 'docs/review/v0.10.0/source-covers.json').read_text())
frame = frames['Axial_Bow']
origin = np.array(frame['frameOrigin']) + np.array(scene_objects['Axial_Bow_SourceReceiver']['receiverShiftModel'])
axes = np.array(frame['frameAxes'])
cap = scene_objects['Axial_Bow_FrontCap']
closed_offset = np.array(cap['slideVector']) + np.array(cap['settleVector'])
seam = np.array(report['bowReceiverForeSeamLocal'])
maximum_seam_error = 0
for child in cap.children:
    local = (model_points(child) + closed_offset - origin) @ axes
    for index, point in zip((6, 7, 8), seam):
        maximum_seam_error = max(maximum_seam_error,
                                 abs(local[index, 1] - point[1] + report['bowForeSeamGap']),
                                 abs(local[index, 2] - point[2]))
    assert local[:, 1].max() < 20.1, 'The cap still extends past the raised receiver lip'
assert maximum_seam_error < .0001, maximum_seam_error

previous = root / 'assets/blender/odin_articulated_v0.11.19.blend'


def normalize(value):
    if hasattr(value, 'to_list'):
        return normalize(value.to_list())
    if hasattr(value, 'to_dict'):
        return normalize(value.to_dict())
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def snapshot():
    bpy.context.view_layer.update()
    result = {}
    for obj in bpy.context.scene.objects:
        row = {'matrix': np.array(obj.matrix_world), 'props': {key: normalize(value) for key, value in obj.items()}}
        if obj.type == 'MESH':
            row['vertices'] = vertices(obj)
            row['faces'] = [tuple(face.vertices) for face in obj.data.polygons]
        result[obj.name] = row
    return result


current_objects = snapshot()
cap_name = cap.name
bpy.ops.wm.open_mainfile(filepath=str(previous))
old_objects = snapshot()
changed_meshes = {'Axial_Bow_FrontCap_Skin_Port', 'Axial_Bow_FrontCap_Skin_Starboard'}
unchanged_meshes, unchanged_joints = 0, 0
for name, old in old_objects.items():
    assert name in current_objects, f'Existing object removed: {name}'
    current = current_objects[name]
    assert np.allclose(current['matrix'], old['matrix'], atol=1e-7), name
    if current['props'].get('staticJoint'):
        for key, value in old['props'].items():
            if key in ('closedCrownLineModel', 'closedLengthLocal') and name == cap_name:
                continue
            assert current['props'][key] == value, f'Joint or animation metadata changed: {name}/{key}'
        unchanged_joints += 1
    if 'vertices' in current and name not in changed_meshes:
        assert np.array_equal(current['vertices'], old['vertices']), f'Unrequested mesh deformation: {name}'
        assert current['faces'] == old['faces'], name
        unchanged_meshes += 1
    elif name in changed_meshes:
        # The accepted rear seam is not part of this shortening operation.
        indices = [0, 1, 2, 9, 10, 11]
        assert np.array_equal(current['vertices'][indices], old['vertices'][indices]), name
assert unchanged_meshes > 200 and unchanged_joints > 100, (unchanged_meshes, unchanged_joints)

report['validation'] = {
    'unchangedOtherMeshes': unchanged_meshes,
    'unchangedStaticJoints': unchanged_joints,
    'fixedSupportExactSourceFaces': 8,
    'bowMaximumForeSeamErrorModelUnits': maximum_seam_error,
    'bowUnchangedRearVerticesPerHalf': 6,
    'referenceSha256': hashlib.sha256(Path(r'D:\Odin\blender_test\odin_with_anime.blend').read_bytes()).hexdigest(),
}
report_path.write_text(json.dumps(report, indent=2), encoding='utf8')
print('NOSE_SOURCE_FIT_VERIFIED', json.dumps(report['validation']), flush=True)
