"""v0.8.4: finish the original main-battery aperture's recessed sidewalls.

The grey strip beside the stowed muzzles belongs to the fixed hull, not the
moving hatch. Select only cavity-facing source polygons seen from inside the
bay. Keep the source topology, exterior faces, joints and animation unchanged.
Run with the immutable, versioned v0.8.3 Blender copy loaded.
"""
import bpy
import hashlib
import json
from array import array
from collections import Counter
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'assets/blender/odin_articulated_v0.8.3.blend'
OUTPUT = ROOT / 'assets/blender/odin_articulated_v0.8.4.blend'
if Path(bpy.data.filepath).resolve() != BASELINE.resolve():
    raise RuntimeError('Load the versioned v0.8.3 baseline; original odin.blend is never modified')
asset = bpy.data.objects['Odin_Asset']
inverse = asset.matrix_world.inverted()
red = bpy.data.materials['Odin_Turret_Interior_DeepRed']


def signature(obj):
    digest = hashlib.sha256()
    digest.update(obj.type.encode())
    digest.update((obj.parent.name if obj.parent else '').encode())
    for matrix in (obj.matrix_world, obj.matrix_basis, obj.matrix_parent_inverse):
        digest.update(array('f', (value for row in matrix for value in row)).tobytes())
    metadata = obj.id_properties_ensure().to_dict()
    if obj == asset:
        metadata.pop('version', None)
    digest.update(json.dumps(metadata, sort_keys=True, default=str).encode())
    if obj.type == 'MESH':
        mesh = obj.data
        for seq, prop, multiplier, code in [(mesh.vertices, 'co', 3, 'f'),
                                           (mesh.edges, 'vertices', 2, 'i'),
                                           (mesh.loops, 'vertex_index', 1, 'i'),
                                           (mesh.polygons, 'loop_start', 1, 'i'),
                                           (mesh.polygons, 'loop_total', 1, 'i')]:
            values = array(code, [0]) * (len(seq) * multiplier)
            seq.foreach_get(prop, values)
            digest.update(values.tobytes())
        for layer in mesh.uv_layers:
            values = array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(layer.name.encode())
            digest.update(values.tobytes())
    return digest.hexdigest()


def face_materials(obj):
    return [obj.data.materials[face.material_index].name if obj.data.materials else None
            for face in obj.data.polygons]


before = {obj.name: signature(obj) for obj in bpy.context.scene.objects}
before_materials = {
    obj.name: face_materials(obj)
    for obj in bpy.context.scene.objects if obj.type == 'MESH'
}
report = {'revision': '0.8.4', 'baseline': BASELINE.name, 'output': OUTPUT.name,
          'scope': 'Existing fixed main-battery cavity sidewalls, dorsal and ventral',
          'interiorMaterial': red.name, 'meshes': {}}

for bank, name, ymin, ymax, zmin, zmax, expected_count in [
    ('Dorsal', 'holo.001', 76, 169, 28, 53, 74),
    ('Ventral', 'holo.013', 28, 122, -62, -37, 114),
]:
    obj = bpy.data.objects[name]
    mesh = obj.data
    matrix = inverse @ obj.matrix_world
    normal_matrix = matrix.to_3x3().inverted().transposed()
    points = [matrix @ vertex.co for vertex in mesh.vertices]
    tree = BVHTree.FromPolygons(points, [tuple(face.vertices) for face in mesh.polygons])
    selected = []
    for face in mesh.polygons:
        center = matrix @ face.center
        normal = (normal_matrix @ face.normal).normalized()
        # The measured main aperture alone. Outward-facing exterior slope,
        # the serrated lip's upper faces and all moving plates are excluded.
        if not (ymin < center.y < ymax and zmin < center.z < zmax
                and 1 < abs(center.x) < 15
                and normal.x * center.x < -.25 * abs(center.x)):
            continue
        if any(point.y < ymin - 1 or point.y > ymax + 1
               or point.z < zmin - 1 or point.z > zmax + 1
               for point in (points[index] for index in face.vertices)):
            continue
        anchor = Vector((0, center.y, center.z))
        vector = center - anchor
        location, _, hit_index, distance = tree.ray_cast(
            anchor, vector.normalized(), vector.length + .02)
        if (location is not None and hit_index == face.index
                and abs(distance - vector.length) < .015):
            selected.append(face.index)
    assert len(selected) == expected_count, f'{bank} cavity selection changed; inspect before proceeding'
    if red not in list(mesh.materials):
        mesh.materials.append(red)
    red_index = list(mesh.materials).index(red)
    changed = [index for index in selected if mesh.polygons[index].material_index != red_index]
    for index in changed:
        mesh.polygons[index].material_index = red_index
    selected_set = set(selected)
    assert all(mesh.materials[face.material_index].name == before_materials[name][face.index]
               for face in mesh.polygons if face.index not in selected_set)
    report['meshes'][name] = {
        'bank': bank, 'selectedCavityFaces': len(selected), 'addedRedFaces': len(changed),
        'changedFaceIndices': changed,
        'selection': 'Aperture bounds + center-facing normal + unobstructed cavity ray',
        'sourceBoundsYZ': [ymin, ymax, zmin, zmax],
        'exteriorAndNonSelectedFacesUnchanged': True,
        'before': dict(Counter(before_materials[name])),
        'after': dict(Counter(mesh.materials[face.material_index].name for face in mesh.polygons)),
    }

after = {obj.name: signature(obj) for obj in bpy.context.scene.objects}
assert before == after, 'Geometry, UVs, transforms, hierarchy or joint metadata changed'
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH' and obj.name not in report['meshes']:
        assert before_materials[obj.name] == face_materials(obj)
assert not bpy.data.actions, 'Static asset unexpectedly contains animation actions'
report.update({'geometryUVRestTransformsAndJointMetadataUnchanged': True,
               'nonTargetObjectMaterialsUnchanged': True,
               'materialDefinitionUnchanged': True,
               'animationActionCount': len(bpy.data.actions),
               'objectCount': len(before),
               'geometryAuditSha256': hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()})
asset['version'] = '0.8.4'
bpy.context.scene.name = 'ODIN v0.8.4 - deep-red fixed main-battery inner walls'
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
report['blendSha256'] = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
report_path = ROOT / 'work/v084-review/interior-materials.json'
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print('SAVED', OUTPUT, flush=True)
print(json.dumps({name: data['addedRedFaces'] for name, data in report['meshes'].items()}), flush=True)
