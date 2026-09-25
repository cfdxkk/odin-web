"""Read-only comparison of everything outside the v0.8.8 armor repair."""
import bpy
import hashlib
import json
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_JOINTS = {'Hatch_Dorsal_Port', 'Hatch_Dorsal_Starboard', 'Hatch_Dorsal_Nose'}


def signature(obj):
    h = hashlib.sha256()
    h.update(obj.type.encode())
    h.update((obj.parent.name if obj.parent else '').encode())
    for matrix in (obj.matrix_world, obj.matrix_basis, obj.matrix_parent_inverse):
        h.update(array('f', (v for row in matrix for v in row)).tobytes())
    props = obj.id_properties_ensure().to_dict()
    if obj.name == 'Odin_Asset':
        props.pop('version', None)
    h.update(json.dumps(props, sort_keys=True, default=str).encode())
    if obj.type == 'MESH':
        mesh = obj.data
        for sequence, field, count, kind in [
            (mesh.vertices, 'co', 3, 'f'), (mesh.edges, 'vertices', 2, 'i'),
            (mesh.loops, 'vertex_index', 1, 'i'), (mesh.polygons, 'loop_start', 1, 'i'),
            (mesh.polygons, 'loop_total', 1, 'i'), (mesh.polygons, 'material_index', 1, 'i'),
        ]:
            values = array(kind, [0]) * (len(sequence) * count)
            sequence.foreach_get(field, values)
            h.update(values.tobytes())
        h.update(json.dumps([m.name if m else None for m in mesh.materials]).encode())
        for uv in mesh.uv_layers:
            values = array('f', [0]) * (len(uv.data) * 2)
            uv.data.foreach_get('uv', values)
            h.update(uv.name.encode())
            h.update(values.tobytes())
    return h.hexdigest()


def read(version):
    path = ROOT / f'assets/blender/odin_articulated_v{version}.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bpy.context.view_layer.update()
    result = {}
    for obj in bpy.context.scene.objects:
        parent, allowed = obj, obj.name == 'holo.001'
        while parent:
            allowed |= parent.name in ALLOWED_JOINTS
            parent = parent.parent
        if not allowed:
            result[obj.name] = signature(obj)
    return result, hashlib.sha256(path.read_bytes()).hexdigest()


before, baseline_sha = read('0.8.6')
after, candidate_sha = read('0.8.8')
original = Path('D:/星际公民相关/Odin/Odin 建模/odin.blend')
original_sha = hashlib.sha256(original.read_bytes()).hexdigest()
expected = '9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
report = {
    'baseline': '0.8.6', 'candidate': '0.8.8',
    'baselineBlendSha256': baseline_sha, 'candidateBlendSha256': candidate_sha,
    'scope': 'Every object except three dorsal forward armor joints and descendants, and the revised holo.001 receiving strip. Includes aft flaps, all ventral armor, all bore/shroud geometry, secondary/PDC, bridge armor and stern mechanisms.',
    'objectsCompared': len(before),
    'changed': sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
    'added': sorted(after.keys() - before.keys()), 'removed': sorted(before.keys() - after.keys()),
    'originalSource': {'path': str(original), 'sha256': original_sha, 'unchanged': original_sha == expected},
    'passed': before == after and original_sha == expected,
}
output = ROOT / 'work/v088-review/preserved-parts.json'
output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps(report, indent=2), flush=True)
assert report['passed'], 'Unexpected changes outside the repair'
