"""Audit actual JS poses, including receiver tails against the closed hull roof.

Run inside the unchanged v0.11.43 native file with two Blender threads.
Never edits or saves original vertices, UVs, materials or rest joints.
"""
import bpy, json, math, hashlib, numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion

root = Path(__file__).resolve().parents[1]
helper = (root / 'tools/audit_bridge_quads_v01134.py').read_text().split('origins=')[0]
exec(compile(helper, str(root / 'tools/audit_bridge_quads_v01134.py'), 'exec'))
basis = Quaternion(Vector((1, 0, 0)), -math.pi / 2)
rows = json.loads((root / 'work/v01150-review/runtime-poses.json').read_text())
baseline_rows = json.loads((root / 'work/v01150-review/baseline-poses.json').read_text())
fit = json.loads((root / 'docs/review/v0.11.34/source-restoration.json').read_text())

def apply(row):
    for joint in row['joints']:
        o = bpy.data.objects[joint['name']]
        x, y, z = joint['position']; o.location = (x, -z, y)
        x, y, z, w = joint['quaternion']; o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = basis.inverted() @ Quaternion((w, x, y, z)) @ basis
    bpy.context.view_layer.update()

def roof_envelope(side):
    seats = []
    for i, seat in enumerate(fit['quads'][side]['petalSeats']):
        roof = np.array(seat['surfaceFit']['roofPlanePoints'])
        normal = np.cross(roof[1] - roof[0], roof[2] - roof[0]); normal /= np.linalg.norm(normal)
        outward = 1 if i % 2 else -1
        parts = {}
        for part in ['ArmMesh', 'RootArmor', 'FixedFork']:
            p = points(bpy.data.objects[f'PDC_{side}_{part}_{i}'])
            roof_z = roof[0, 2] - (p[:, :2] - roof[0, :2]) @ normal[:2] / normal[2]
            excess = float((outward * (p[:, 2] - roof_z)).max())
            parts[part] = {'maximumOutsideHeight': excess, 'minimumInsideMargin': -excess}
        seats.append({'quadrant': i, 'roofPlanePoints': roof.tolist(), 'parts': parts})
    return seats

frames = {o.name: np.array(o.matrix_local).copy() for o in bpy.context.scene.objects if o.type == 'MESH'}
report = {side: {'poses': 0, 'tubeCasingContacts': [], 'tubePetalContacts': [], 'cradlePairContacts': [], 'tubePairContacts': [], 'examples': []} for side in ['Port', 'Starboard']}
apply(rows[0])
for side, out in report.items(): out['closedHullEnvelope'] = roof_envelope(side)
apply(baseline_rows[0])
for side, out in report.items(): out['baselineClosedHullEnvelope'] = roof_envelope(side)
for step, row in enumerate(rows):
    apply(row)
    for side, out in report.items():
        out['poses'] += 1
        tubes = [bpy.data.objects[f'PDC_{side}_ArmMesh_{i}'] for i in range(4)]
        petals = [bpy.data.objects[f'PDC_{side}_HullPetal_{i}_Skin'] for i in range(4)]
        tube_shapes = [tree([o]) for o in tubes]
        casing = tree([bpy.data.objects[f'PDC_{side}_Casing']])
        count = sum(intersections(shape, casing) for shape in tube_shapes)
        if count: out['tubeCasingContacts'].append({'progress': row['progress'], 'contacts': count})
        count = intersections(tree(tubes), tree(petals))
        if count: out['tubePetalContacts'].append({'progress': row['progress'], 'contacts': count})
        bearings = [tree([bpy.data.objects[f'PDC_{side}_FixedFork_{i}'], bpy.data.objects[f'PDC_{side}_RootArmor_{i}']]) for i in range(4)]
        for i in range(4):
            for j in range(i + 1, 4):
                for kind, a, b in [('cradlePairContacts', bearings[i], bearings[j]), ('tubePairContacts', tube_shapes[i], tube_shapes[j])]:
                    count = intersections(a, b)
                    if count: out[kind].append({'progress': row['progress'], 'quadrants': [i, j], 'contacts': count})
        if row['progress'] in [0, .1, .2, .3, .5, 1] and step < 202:
            centers = np.array([(points(o).min(0) + points(o).max(0)) / 2 for o in tubes])
            out['examples'].append({'progress': row['progress'], 'centers': centers.tolist(), 'foreAftSeparation': float(abs(centers[:2, 1].mean() - centers[2:, 1].mean())), 'verticalSeparation': float(abs(centers[[0, 2], 2].mean() - centers[[1, 3], 2].mean()))})
    if step % 50 == 0: print('QUAD_TAIL_CLEARANCE', step, len(rows), flush=True)
for name, matrix in frames.items(): assert np.max(abs(np.array(bpy.data.objects[name].matrix_local) - matrix)) < .00005, name
digest = lambda path: hashlib.sha256((root / path).read_bytes()).hexdigest()
evidence = {
    'version': 'v0.11.50-rc.1', 'originalMeshesUnchanged': True, 'forwardSamples': 202, 'reverseSamples': 31,
    'nativeFile': 'assets/blender/odin_articulated_v0.11.43.blend', 'nativeSha256': digest('assets/blender/odin_articulated_v0.11.43.blend'),
    'runtimePosesSha256': digest('work/v01150-review/runtime-poses.json'), 'codeHashEncoding': 'UTF-8 with LF newlines',
    'codeHashes': json.loads((root / 'docs/review/v0.11.50/motion-verification.json').read_text())['codeHashes'], 'sides': report
}
(root / 'docs/review/v0.11.50/mesh-clearance.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf8')
print('QUAD_TAIL_CLEARANCE_RESULT', [(s, r['poses'], len(r['tubeCasingContacts']), len(r['tubePetalContacts']), len(r['cradlePairContacts']), len(r['tubePairContacts'])) for s, r in report.items()], flush=True)
assert all(not r['tubeCasingContacts'] and not r['tubePetalContacts'] and not r['cradlePairContacts'] and not r['tubePairContacts'] for r in report.values())
assert all(p['minimumInsideMargin'] > .01 for r in report.values() for seat in r['closedHullEnvelope'] for p in seat['parts'].values())
assert all(any(seat['parts']['RootArmor']['maximumOutsideHeight'] > .10 for seat in r['baselineClosedHullEnvelope']) for r in report.values()), 'Roof envelope must detect the prior rear-shell penetration'
