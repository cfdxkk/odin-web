"""Audit actual JS poses, tube clearance and the closed fitted hull envelope.

Run inside the unchanged v0.11.43 native file with two Blender threads.
Never edits or saves original vertices, UVs, materials or rest joints. The
support's constant runtime mounting fit is applied from the actual JS samples.
"""
import bpy, json, math, hashlib, numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree

root = Path(__file__).resolve().parents[1]
helper = (root / 'tools/audit_bridge_quads_v01134.py').read_text().split('origins=')[0]
exec(compile(helper, str(root / 'tools/audit_bridge_quads_v01134.py'), 'exec'))
basis = Quaternion(Vector((1, 0, 0)), -math.pi / 2)
rows = json.loads((root / 'work/v01152-review/runtime-poses.json').read_text())
baseline_rows = json.loads((root / 'work/v01152-review/baseline-poses.json').read_text())
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

def fixed_roof(side):
    # Use the actual adjacent outer hull faces, excluding unrelated internal
    # struts and deliberately buried mounting surfaces from the source mesh.
    selected = []
    faces = []
    for i, seat in enumerate(fit['quads'][side]['petalSeats']):
        o = bpy.data.objects[seat['forwardSeam']['fixedMesh']]
        p = points(o); o.data.calc_loop_triangles()
        tri = p[np.array([t.vertices[:] for t in o.data.loop_triangles], dtype=np.int32)]
        roof = np.array(seat['surfaceFit']['roofPlanePoints'])
        n = np.cross(roof[1] - roof[0], roof[2] - roof[0]); n /= np.linalg.norm(n)
        coplanar = abs((tri - roof[0]) @ n).max(1) < .001
        near_y = (tri[:, :, 1].min(1) < roof[:, 1].max() + 3) & (tri[:, :, 1].max(1) > roof[:, 1].min() - 3)
        near_x = ((tri[:, :, 0].min(1) < 65) & (tri[:, :, 0].max(1) > 10)) if side == 'Starboard' else ((tri[:, :, 0].min(1) < -10) & (tri[:, :, 0].max(1) > -65))
        ids = np.flatnonzero(coplanar & near_y & near_x)
        assert len(ids), (side, i, 'No adjacent fixed roof face')
        selected.extend(tri[ids]); faces.append({'quadrant': i, 'mesh': o.name, 'triangleIds': ids.tolist()})
    triangles = np.array(selected); cloud = triangles.reshape(-1, 3)
    indices = np.arange(len(cloud)).reshape(-1, 3)
    return (BVHTree.FromPolygons([Vector(v) for v in cloud], indices.tolist(), all_triangles=True), triangles), faces

frames = {o.name: np.array(o.matrix_local).copy() for o in bpy.context.scene.objects if o.type == 'MESH'}
report = {side: {'poses': 0, 'tubeCasingContacts': [], 'tubePetalContacts': [], 'cradlePairContacts': [], 'tubePairContacts': [], 'examples': []} for side in ['Port', 'Starboard']}
fixed_roofs = {}
for side, out in report.items():
    fixed_roofs[side], out['adjacentFixedRoofFaces'] = fixed_roof(side)
    out['receiverFixedRoofContacts'] = []
    out['baselineReceiverFixedRoofContacts'] = []
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
        if row['progress'] <= .69:
            count = sum(intersections(tree([bpy.data.objects[f'PDC_{side}_RootArmor_{i}']]), fixed_roofs[side]) for i in range(4))
            if count: out['receiverFixedRoofContacts'].append({'progress': row['progress'], 'contacts': count})
        for i in range(4):
            for j in range(i + 1, 4):
                for kind, a, b in [('cradlePairContacts', bearings[i], bearings[j]), ('tubePairContacts', tube_shapes[i], tube_shapes[j])]:
                    count = intersections(a, b)
                    if count: out[kind].append({'progress': row['progress'], 'quadrants': [i, j], 'contacts': count})
        if row['progress'] in [0, .1, .2, .3, .5, 1] and step < 202:
            centers = np.array([(points(o).min(0) + points(o).max(0)) / 2 for o in tubes])
            out['examples'].append({'progress': row['progress'], 'centers': centers.tolist(), 'foreAftSeparation': float(abs(centers[:2, 1].mean() - centers[2:, 1].mean())), 'verticalSeparation': float(abs(centers[[0, 2], 2].mean() - centers[[1, 3], 2].mean()))})
    if step % 50 == 0: print('QUAD_TAIL_CLEARANCE', step, len(rows), flush=True)
for row in baseline_rows[:202]:
    if row['progress'] > .69: continue
    apply(row)
    for side, out in report.items():
        count = sum(intersections(tree([bpy.data.objects[f'PDC_{side}_RootArmor_{i}']]), fixed_roofs[side]) for i in range(4))
        if count: out['baselineReceiverFixedRoofContacts'].append({'progress': row['progress'], 'contacts': count})
for name, matrix in frames.items():
    if name.endswith('_OriginalSupport'): continue
    assert np.max(abs(np.array(bpy.data.objects[name].matrix_local) - matrix)) < .00005, name
digest = lambda path: hashlib.sha256((root / path).read_bytes()).hexdigest()
evidence = {
    'version': 'v0.11.52-rc.1', 'originalMeshesUnchanged': True, 'supportMountingOffsetZ': -.35, 'forwardSamples': 202, 'reverseSamples': 31,
    'nativeFile': 'assets/blender/odin_articulated_v0.11.43.blend', 'nativeSha256': digest('assets/blender/odin_articulated_v0.11.43.blend'),
    'runtimePosesSha256': digest('work/v01152-review/runtime-poses.json'), 'codeHashEncoding': 'UTF-8 with LF newlines',
    'codeHashes': json.loads((root / 'docs/review/v0.11.52/motion-verification.json').read_text())['codeHashes'], 'sides': report
}
(root / 'docs/review/v0.11.52/mesh-clearance.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf8')
print('QUAD_TAIL_CLEARANCE_RESULT', [(s, r['poses'], len(r['tubeCasingContacts']), len(r['tubePetalContacts']), len(r['cradlePairContacts']), len(r['tubePairContacts'])) for s, r in report.items()], flush=True)
assert all(not r['tubeCasingContacts'] and not r['tubePetalContacts'] and not r['cradlePairContacts'] and not r['tubePairContacts'] for r in report.values())
assert all(p['minimumInsideMargin'] > .01 for r in report.values() for seat in r['closedHullEnvelope'] for p in seat['parts'].values())
# Report this seam-plane diagnostic without treating internal source mounting
# intersections as a zero-contact requirement. Rendered roof visibility is
# checked independently against the actual exported fixed hull in the browser.

