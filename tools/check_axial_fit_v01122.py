"""Check saved full cover edges, original support, and unchanged gun rigs."""
import bpy
import hashlib
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Quaternion, Vector

root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.22'
inv = asset.matrix_world.inverted()
frames = json.loads((root / 'docs/review/v0.10.0/source-covers.json').read_text())
fit = json.loads((root / 'docs/review/v0.11.22/geometry-fit.json').read_text())
report = {'stations': {}}


def points(obj):
    return np.array([(inv @ obj.matrix_world) @ v.co for v in obj.data.vertices])


def closed_points(obj):
    joint = obj.parent
    hinge = np.array((inv @ joint.matrix_world).translation)
    rotation = np.array(Quaternion(Vector(joint['hingeAxisModel']),
        math.radians(joint['closedAngleDegrees'])).to_matrix())
    return hinge + (points(obj) - hinge) @ rotation.T


def digest(obj):
    h = hashlib.sha256()
    co = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', co)
    h.update(co.tobytes())
    for face in obj.data.polygons:
        h.update(np.array(tuple(face.vertices), dtype=np.int32).tobytes())
        h.update(obj.data.materials[face.material_index].name.encode())
    return h.hexdigest()


def snapshot():
    bpy.context.view_layer.update()
    return {o.name: {'matrix': np.array(o.matrix_local).copy(),
                    'parent': o.parent.name if o.parent else None,
                    'mesh': digest(o) if o.type == 'MESH' else None,
                    'joint': bool(o.get('staticJoint'))}
            for o in bpy.context.scene.objects}


for station in ('Stern', 'Keel'):
    prefix = 'Axial_' + station
    origin = np.array(frames[prefix]['frameOrigin'])
    axes = np.array(frames[prefix]['frameAxes'])
    if station == 'Keel':
        origin += np.array(bpy.data.objects['Axial_Keel_Mount']['fixedAssemblyOffsetModel'])
    width = 2.46 if station == 'Stern' else 2.298
    center = .015 * width / 2.46
    flat = .45 * width / 2.46
    yshift = 0 if station == 'Stern' else .14
    zshift = 0 if station == 'Stern' else .54
    crown = lambda y: 5.22 + .20 * (y - yshift + 16.25) / 26.78 - zshift
    housing = bpy.data.objects['odin.027' if station == 'Stern' else 'odin.030']
    housing_end = float(((points(housing) - origin) @ axes)[:, 1].max()) + .02
    max_error = 0
    adjacent_error = 0
    leaves = {}
    for side, sign in (('Port', -1), ('Starboard', 1)):
        for index, (start, end) in enumerate(((-16.25, -6.525), (-6.525, 1.90), (1.90, 10.53))):
            start += yshift
            end += yshift
            name = f'{prefix}_Shutter_{side}_{index:02d}'
            joint = bpy.data.objects[name]
            assert joint['openingTravelDegrees'] == 95
            backing = bpy.data.objects[name + '_FittedBacking']
            local = (closed_points(backing) - origin) @ axes
            assert len(local) == 12 and len(backing.data.polygons) == 10
            expected = []
            for k in range(6):
                cross = k % 3
                x = (width, flat, center)[cross]
                u = (x - center) / (width - center)
                y = end if k >= 3 else start + ((housing_end - start) * (1 - u) if index == 0 else 0)
                expected.append((sign * x, y, 2.49 - zshift if cross == 0 else crown(y)))
            max_error = max(max_error, float(np.max(abs(local[:6] - np.array(expected)))))
            leaves[side, index] = local
            assert any(m.name in ('Odin_Turret_Interior_DeepRed', 'Odin_Bay_Primer') for m in backing.data.materials)
            skin = bpy.data.objects[name + '_Skin']
            assert any(m.name in ('Odin_Turret_Interior_DeepRed', 'Odin_Bay_Primer') for m in skin.data.materials)
            if index:
                adjacent_error = max(adjacent_error, float(np.max(abs(local[:3] - leaves[side, index - 1][3:6]))))
    assert max_error < .0001 and adjacent_error < .0001, (station, max_error, adjacent_error)
    cap = bpy.data.objects[prefix + '_FrontCap']
    cap_mesh = bpy.data.objects[prefix + '_FrontCap_Skin']
    assert len(cap_mesh.data.vertices) == 56 and len(cap_mesh.data.polygons) == 66
    assert cap['settleEnd'] < cap['slideStart'] < cap['slideEnd']
    offset = np.array(cap['slideVector']) + np.array(cap['settleVector'])
    cap_local = (points(cap_mesh) + offset - origin) @ axes
    edge_error = 0
    for sign, base in ((1, 0), (-1, 28)):
        for ids, profile_name in (([0, 8, 4], 'rearProfile'), ([3, 9, 5], 'foreProfile')):
            expected = np.array(fit['stations'][station][profile_name])
            expected[:, 0] *= sign
            edge_error = max(edge_error, float(np.max(abs(cap_local[np.array(ids) + base] - expected))))
    assert edge_error < .0001, (station, edge_error)
    actual_seam = float(2 * np.min(abs(cap_local[:, 0])))
    assert abs(actual_seam - 2 * center) < .0001
    fore = np.array(fit['stations'][station]['foreProfile'])
    if station == 'Stern':
        receiver = (points(bpy.data.objects['Axial_Stern_OriginalNoseSupport']) - origin) @ axes
        hull = bpy.data.objects['holo.001']
        strip = ((points(hull) - origin) @ axes)[list(hull.data.polygons[166349].vertices)]
    else:
        receiver = (points(bpy.data.objects['Axial_Keel_OriginalNoseSupport']) - origin) @ axes
        hull = bpy.data.objects['holo.022']
        strip = ((points(hull) - origin) @ axes)[list(hull.data.polygons[24539].vertices)]
    receiver_error = max(float(np.min(np.linalg.norm(receiver - (p + [0, .02, 0]), axis=1))) for p in fore[1:])
    strip_corner = strip[np.argmin(strip[:, 1])]
    receiver_error = max(receiver_error, abs(float(strip_corner[1] - fore[0, 1] - .02)), abs(float(strip_corner[2] - fore[0, 2])))
    assert receiver_error < .0001
    report['stations'][station] = {
        'roofMaximumError': max_error, 'adjacentLeafMaximumError': adjacent_error,
        'capFullEdgeMaximumError': edge_error, 'fixedReceiverMaximumError': receiver_error,
        'capCenterSeam': actual_seam, 'leafWidth': 2 * width,
        'capWidth': float(2 * np.max(abs(cap_local[:, 0]))),
        'receiverSeam': .02, 'gunRootCrownClearance': .02,
        'retainedNoseTopology': {'vertices': 56, 'faces': 66}}

# Compare the restored geometry to the six original fixed support faces.
support = bpy.data.objects['Axial_Keel_OriginalNoseSupport']
assert len(support.data.polygons) == 6 and support.parent.name == 'Axial_Keel_Mount'
restored_points = points(support)
restored_faces = [restored_points[list(f.vertices)] for f in support.data.polygons]
delta = np.array(bpy.data.objects['Axial_Keel_Mount']['fixedAssemblyOffsetModel'])
with bpy.data.libraries.load(str(root.parent / 'Odin 建模/odin.blend'), link=False) as (src, dst):
    dst.objects = ['holo.022']
source = dst.objects[0]
bpy.context.scene.collection.objects.link(source)
bpy.context.view_layer.update()
source_points = np.array([source.matrix_world @ v.co for v in source.data.vertices]) + delta
source_error = 0
for index in (1456, 2736, 2737, 3291, 3293, 3518):
    original_face = source_points[list(source.data.polygons[index].vertices)]
    errors = [max(float(np.min(np.linalg.norm(candidate - p, axis=1))) for p in original_face)
              for candidate in restored_faces if len(candidate) == len(original_face)]
    source_error = max(source_error, min(errors))
assert source_error < .0001, source_error
bpy.data.objects.remove(source, do_unlink=True)
report['restoredOriginalSupportMaximumError'] = source_error

current = snapshot()
bpy.ops.wm.open_mainfile(filepath=str(root / 'assets/blender/odin_articulated_v0.11.21.blend'))
previous = snapshot()
allowed = set(fit['changedMeshes'])
mesh_count = joint_count = 0
for name, old in previous.items():
    assert name in current, ('Removed original object', name)
    new = current[name]
    assert old['parent'] == new['parent'], ('Changed parent', name)
    assert np.max(abs(old['matrix'] - new['matrix'])) < .00002, ('Changed transform', name)
    if old['joint']:
        joint_count += 1
    if old['mesh'] and name not in allowed:
        assert old['mesh'] == new['mesh'], ('Changed unrelated geometry/material', name)
        mesh_count += 1
assert set(current) - set(previous) == {'Axial_Keel_OriginalNoseSupport'}
assert joint_count == 187
report['unchangedMeshCount'] = mesh_count
report['unchangedJointTransforms'] = joint_count
report['sourceFileSha256'] = {}
expected_hashes = {
    root.parent / 'Odin 建模/odin.blend': '9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e',
    Path('D:/Odin/blender_test/odin_with_anime.blend'): 'c606825700df099f93ee1d39670d04371ce8cf71f9db77353a676f8de3b6c35e'}
for filename, expected in expected_hashes.items():
    h = hashlib.sha256()
    with filename.open('rb') as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b''):
            h.update(chunk)
    assert h.hexdigest() == expected, ('Modified source file', str(filename))
    report['sourceFileSha256'][filename.name] = h.hexdigest()
(root / 'docs/review/v0.11.22/geometry-audit.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('SAVED_AXIAL_EDGES_VERIFIED', json.dumps(report), flush=True)
