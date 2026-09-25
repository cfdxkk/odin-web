"""Measure physical attachment, planar aft skins and finite armor thickness."""
import bpy, json, hashlib
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
inverse = asset.matrix_world.inverted()
assert asset['version'] == '0.8.10' and not bpy.data.actions
report = {'version': '0.8.10', 'aft': {}, 'skins': {}, 'junctions': {}}

for bank in ['Dorsal', 'Ventral']:
    for side in ['Port', 'Starboard']:
        joint = bpy.data.objects[f'Hatch_{bank}_Aft_{side}']
        mesh = bpy.data.objects[joint.name + '_GapFiller']
        transform = inverse @ mesh.matrix_world
        points = [transform @ v.co for v in mesh.data.vertices]
        count = len(points) // 2
        normal = Vector(joint['planeNormal']).normalized()
        offsets = [point.dot(normal) for point in points[:count]]
        deviation = max(offsets) - min(offsets)
        assert deviation < .00003, (joint.name, deviation)
        hinge_errors = [min((point - Vector(endpoint)).length for point in points[:count])
                        for endpoint in joint['hingeEdge']]
        assert max(hinge_errors) < .00003, (joint.name, hinge_errors)
        thickness = [(points[i] - points[i + count]).dot(normal) for i in range(count)]
        assert max(thickness) > .119 and min(thickness) > .019, joint.name
        report['aft'][joint.name] = {'planeError': deviation, 'hingeEndpointErrors': hinge_errors,
                                    'thickness': [min(thickness), max(thickness)]}
    for role, suffix in [('Port', 'FittedSkin'), ('Starboard', 'FittedSkin'), ('Nose', 'Wedge')]:
        mesh = bpy.data.objects[f'Hatch_{bank}_{role}_{suffix}']
        transform = inverse @ mesh.matrix_world
        points = [transform @ v.co for v in mesh.data.vertices]
        count = len(points) // 2
        thickness = [abs(points[i].z - points[i + count].z) for i in range(count)]
        assert max(thickness) >= .17 and min(thickness) > .009, mesh.name
        assert all(mesh.data.materials[f.material_index].name == 'Odin_Turret_Interior_DeepRed'
                   for f in mesh.data.polygons if min(f.vertices) >= count)
        report['skins'][mesh.name] = {'thickness': [min(thickness), max(thickness)]}

for side in ['Port', 'Starboard']:
    moving = bpy.data.objects[f'Hatch_Dorsal_{side}_RearReturn']
    fixed = bpy.data.objects[f'MainBay_Dorsal_{side}_FixedReceiver']
    assert moving.parent.name == f'Hatch_Dorsal_{side}'
    assert fixed.parent == asset and not fixed.get('staticJoint')
    report['junctions'][side] = {'blueParent': moving.parent.name, 'redParent': fixed.parent.name}

original = Path('D:/星际公民相关/Odin/Odin 建模/odin.blend')
report['originalSourceSha256'] = hashlib.sha256(original.read_bytes()).hexdigest()
assert report['originalSourceSha256'] == '9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
report['blendSha256'] = hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
path = ROOT / 'work/v0810-review/physical-fit.json'
path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps(report, indent=2))
