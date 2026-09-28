"""Verify saved axial geometry against v0.11.20 before publishing."""
import bpy
import hashlib
import json
import numpy as np
from pathlib import Path
from mathutils import Quaternion, Vector
import math

root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.21'
frames = json.loads((root / 'docs/review/v0.10.0/source-covers.json').read_text())
report_path = root / 'docs/review/v0.11.21/geometry-audit.json'
report = json.loads(report_path.read_text())
inv = asset.matrix_world.inverted()
origin = np.array(frames['Axial_Keel']['frameOrigin']) + np.array(report['keelLockedOffsetModel'])
axes = np.array(frames['Axial_Keel']['frameAxes'])
stern_origin = np.array(frames['Axial_Stern']['frameOrigin'])
stern_axes = np.array(frames['Axial_Stern']['frameAxes'])


def model_points(obj):
    return np.array([(inv @ obj.matrix_world) @ vertex.co for vertex in obj.data.vertices])


def closed_points(obj):
    parent = obj.parent
    hinge = np.array((inv @ parent.matrix_world).translation)
    rotation = np.array(Quaternion(Vector(parent['hingeAxisModel']),
        math.radians(parent['closedAngleDegrees'])).to_matrix())
    return hinge + (model_points(obj) - hinge) @ rotation.T


fit_error = 0
for side in ('Port', 'Starboard'):
    for index in range(3):
        name = f'Shutter_{side}_{index:02d}'
        joint = bpy.data.objects['Axial_Keel_' + name]
        assert joint.parent.name == 'Axial_Keel_Mount'
        assert joint['openingTravelDegrees'] == 95
        assert joint['openEnd'] == bpy.data.objects['Axial_Stern_' + name]['openEnd']
        assert len(joint.children) == 2
        for suffix in ('Skin', 'FittedBacking'):
            keel = bpy.data.objects[f'Axial_Keel_{name}_{suffix}']
            stern = bpy.data.objects[f'Axial_Stern_{name}_{suffix}']
            assert [tuple(p.vertices) for p in keel.data.polygons] == [tuple(p.vertices) for p in stern.data.polygons]
            actual = (closed_points(keel) - origin) @ axes
            expected = (closed_points(stern) - stern_origin) @ stern_axes
            expected[:, 0] *= 2.298 / 2.46
            expected[:, 1] += .14
            expected[:, 2] -= .54
            fit_error = max(fit_error, float(np.max(np.abs(actual - expected))))
            assert any(m.name in ('Odin_Turret_Interior_DeepRed', 'Odin_Bay_Primer')
                       for m in keel.data.materials)
assert fit_error < .0001, fit_error
report['keelClosedTemplateMaximumError'] = fit_error
cap = bpy.data.objects['Axial_Keel_FrontCap']
assert cap['settleEnd'] < cap['slideStart'] < cap['slideEnd']
assert len(cap.children) == 1
cap_mesh = cap.children[0]
assert len(cap_mesh.data.polygons) == 66
assert any(cap_mesh.data.materials[p.material_index].name == 'Odin_Turret_Interior_DeepRed'
           for p in cap_mesh.data.polygons), 'Keel foremost armor has no red inside'
closed_offset = np.array(cap['slideVector']) + np.array(cap['settleVector'])
cap_local = (model_points(cap_mesh) + closed_offset - origin) @ axes
crown = cap_local[(np.abs(cap_local[:,0]) < .16) & (cap_local[:,1] > 18)]
seam = np.array(report['keelReceiverForeCrownLocal'])
assert len(crown) >= 2
leading = crown[np.argmax(crown[:,2])]
assert abs(leading[2]-seam[2]) < .0001 and abs(leading[1]-seam[1]+.02) < .0001
report['keelForeCrownMaximumError'] = max(abs(leading[2]-seam[2]), abs(leading[1]-seam[1]+.02))


def mesh_digest(obj):
    digest = hashlib.sha256()
    coords = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', coords)
    digest.update(coords.tobytes())
    for face in obj.data.polygons:
        digest.update(np.asarray(tuple(face.vertices), dtype=np.int32).tobytes())
        digest.update(obj.data.materials[face.material_index].name.encode())
    return digest.hexdigest()


def snapshot():
    bpy.context.view_layer.update()
    return {obj.name: {'matrix': np.array(obj.matrix_local),
                      'mesh': mesh_digest(obj) if obj.type == 'MESH' else None,
                      'parent': obj.parent.name if obj.parent else None}
            for obj in bpy.context.scene.objects}


current = snapshot()
keel_hull_coords = np.array([v.co[:] for v in bpy.data.objects['holo.022'].data.vertices])
bpy.ops.wm.open_mainfile(filepath=str(root / 'assets/blender/odin_articulated_v0.11.20.blend'))
previous = snapshot()
assert np.array_equal(keel_hull_coords, np.array([v.co[:] for v in bpy.data.objects['holo.022'].data.vertices])), \
    'Keel fixed hull geometry was changed rather than only its interior color'
allowed_meshes = {'Axial_Bow_SourceReceiver_Skin', 'Axial_Stern_FrontCap_Skin', 'holo.022'}
count = 0
for name, old in previous.items():
    if name.startswith(('Axial_Keel_Shutter_', 'Axial_Keel_FrontCap')):
        continue
    assert name in current
    new = current[name]
    assert old['parent'] == new['parent'], name
    if name != 'Axial_Keel_Mount':
        error = float(np.max(np.abs(old['matrix'] - new['matrix'])))
        assert error < .00002, ('Changed transform', name, error)
    if old['mesh'] and name not in allowed_meshes:
        assert old['mesh'] == new['mesh'], ('Changed mesh', name)
        count += 1
report['savedUnchangedMeshCount'] = count
report['keelHullVerticesUnchanged'] = True
report['sourceFileSha256'] = {}
for filename in (root.parent / 'Odin 建模/odin.blend', Path('D:/Odin/blender_test/odin_with_anime.blend')):
    digest = hashlib.sha256()
    with filename.open('rb') as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b''):
            digest.update(chunk)
    report['sourceFileSha256'][filename.name] = digest.hexdigest()
report_path.write_text(json.dumps(report, indent=2), encoding='utf8')
print('SAVED_GEOMETRY_VERIFIED', count, fit_error, flush=True)
