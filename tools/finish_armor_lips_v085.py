"""Restore the exterior aperture lips accidentally included in v0.8.4's red mask.

This is a material correction on existing exterior faces, not a seam cover or
an inner-wall repaint. It neither creates geometry nor saves the Blender file.
The two long dorsal strips are original hull triangles 155029 and 185047;
their outward normal has z=0.948695. Closed-preview pixel rays hit triangle
185047 directly, proving that the red line was the lip itself, not the cavity
showing through a badly fitting hatch. Adjacent tiny exterior bevels and the
ventral equivalents regain their exact v0.8.3 material as well.
"""
import bpy
import hashlib
import json
from array import array
from pathlib import Path


EXTERIOR_LIP_FACES = {
    'holo.001': {
        'material': 'Odin_Paint_Light', 'direction': 1,
        'faces': [131099, 134930, 134966, 155018, 155029, 155972, 159265,
                  159815, 160037, 167009, 167010, 167024, 167026, 167042,
                  172558, 172561, 172586, 185047],
    },
    'holo.013': {
        'material': 'Odin_Paint_Dark.001', 'direction': -1,
        'faces': [593, 648, 1353, 1403, 1456, 2151, 2321, 2394, 2395,
                  2440, 2638, 2648, 3099, 3290, 3396, 3681, 3682,
                  3878, 3908, 4066, 4067, 4296, 4530],
    },
}


def finish_armor_lips_v085():
    root = Path(__file__).resolve().parents[1]
    inverse = bpy.data.objects['Odin_Asset'].matrix_world.inverted()
    red_name = 'Odin_Turret_Interior_DeepRed'
    report = {
        'revision': '0.8.5', 'baselineFinish': 'odin_articulated_v0.8.3.blend',
        'cause': 'v0.8.4 inward-X-only mask included outward-facing exterior rim triangles',
        'closedPreviewRayFace': {'object': 'holo.001', 'face': 185047,
                                'normal': [-.314699, .030679, .948695]},
        'fixedHullTopologyChanged': False, 'newSeamGeometry': False,
        'interiorFinishPreserved': True, 'meshes': {},
    }
    for name, spec in EXTERIOR_LIP_FACES.items():
        obj = bpy.data.objects[name]
        mesh = obj.data
        matrix = inverse @ obj.matrix_world
        normal_matrix = matrix.to_3x3().inverted().transposed()
        selected = set(spec['faces'])
        materials = list(mesh.materials)
        expected = bpy.data.materials[spec['material']]
        assert expected in materials, f'{name}: original exterior material is missing'
        restore_index = materials.index(expected)
        old = [face.material_index for face in mesh.polygons]
        before = array('f', [0]) * (len(mesh.vertices) * 3)
        mesh.vertices.foreach_get('co', before)
        rows = []
        for index in spec['faces']:
            face = mesh.polygons[index]
            normal = (normal_matrix @ face.normal).normalized()
            assert normal.z * spec['direction'] > .8, f'{name}/{index}: no longer an exterior lip'
            assert materials[face.material_index].name in (red_name, spec['material'])
            center = matrix @ face.center
            rows.append({'face': index, 'side': 'Port' if center.x < 0 else 'Starboard',
                         'outwardNormal': list(normal), 'center': list(center),
                         'restoredMaterial': spec['material']})
            face.material_index = restore_index
        assert all(face.material_index == old[face.index]
                   for face in mesh.polygons if face.index not in selected)
        after = array('f', [0]) * (len(mesh.vertices) * 3)
        mesh.vertices.foreach_get('co', after)
        assert before == after
        report['meshes'][name] = {
            'restoredExteriorFaces': len(rows), 'faces': rows,
            'retainedRedFaceCount': sum(materials[face.material_index].name == red_name
                                       for face in mesh.polygons),
            'nonTargetFacesUnchanged': True,
            'vertexSha256': hashlib.sha256(before.tobytes()).hexdigest(),
        }
    path = root / 'work/v085-review/exterior-lip-finish.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print('EXTERIOR_LIP_FINISH', {name: part['restoredExteriorFaces']
                                 for name, part in report['meshes'].items()}, flush=True)
    return report
