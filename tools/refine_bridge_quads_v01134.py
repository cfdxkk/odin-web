"""Seat the original quad petals on their adjoining roof faces; hold the opening.

Run on v0.11.33. Preserve each source petal's topology, UVs and X/Y footprint.
Fit its outer skin in Z to the actual adjoining fixed roof plane, retaining the
vertical thickness under that skin. Bake the passage clearance into the open
geometry so the runtime uses one monotonic translation without a return leg.
"""
import bpy, json
import numpy as np
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
review = root / 'docs/review/v0.11.34'
review.mkdir(parents=True, exist_ok=True)
fit = json.loads((root / 'docs/review/v0.11.33/source-restoration.json').read_text())
source_planes = {r['face']: r for r in json.loads((root / 'tests/fixtures/bridge-quad-roof-faces-v01134.json').read_text())['starboardRoofFaces']}
asset = bpy.data.objects['Odin_Asset']
inv = asset.matrix_world.inverted()
fixed = bpy.data.objects[fit['fixedSeamMesh']]
fixed_points = np.array([(inv @ fixed.matrix_world) @ v.co for v in fixed.data.vertices])
original_fixed = fixed_points.copy()
for r in fit['fixedSeamEdits']:
    original_fixed[r['vertex']] = r['before']
fit['version'] = '0.11.34'

def height(tri, xy):
    a, b, c = tri
    n = np.cross(b-a, c-a)
    return a[2] - np.dot(n[:2], xy-a[:2]) / n[2]

def outer_height(tris, xy):
    # The source skin has several facets. Use its nearest projected triangle
    # so both bevels and the original thickness receive the same Z correction.
    best = None
    for tri in tris:
        weights = np.linalg.solve(np.column_stack((tri[1,:2]-tri[0,:2], tri[2,:2]-tri[0,:2])), xy-tri[0,:2])
        bary = np.array([1-weights.sum(), *weights])
        penalty = np.linalg.norm(np.minimum(bary, 0))
        candidate = (penalty, height(tri, xy))
        if best is None or candidate[0] < best[0]:
            best = candidate
    return best[1]

for side, sign in [('Port', -1), ('Starboard', 1)]:
    for k, row in enumerate(fit['quads'][side]['petalSeats']):
        joint = bpy.data.objects[row['joint']]
        skin = joint.children[0]
        M = inv @ skin.matrix_world
        original = np.array([M @ v.co for v in skin.data.vertices])
        old_shift = np.array(joint['compactVector'])
        out = 1 if k % 2 else -1
        roof_face = [252991, 55518, 252980, 48397][k]
        anchors = []
        anchor_ids = []
        for p in source_planes[roof_face]['points']:
            p = np.array(p) * [sign, 1, 1]
            distance = np.linalg.norm(original_fixed-p, axis=1)
            i = int(distance.argmin())
            assert distance[i] < .00002, (side, roof_face, p, distance[i])
            anchors.append(fixed_points[i])
            anchor_ids.append(i)
        target = np.array(anchors)
        roof = next(f for f in fixed.data.polygons if set(f.vertices) == set(anchor_ids))
        roof_material = fixed.data.materials[roof.material_index]
        tris = [original[list(f.vertices)] for f in skin.data.polygons
                if len(f.vertices) == 3 and f.area > 2 and f.normal.z * out > .8]
        # Mesh-local and hull Z agree for these source-centered skin meshes.
        assert len(tris) == 3, (joint.name, len(tris))
        shaped = original.copy()
        for i, p in enumerate(original):
            shaped[i,2] += height(target, p[:2]) - old_shift[2] - outer_height(tris, p[:2]) + out*.25
            skin.data.vertices[i].co = M.inverted() @ Vector(shaped[i])
        skin.data.materials.clear()
        skin.data.materials.append(roof_material)
        for f in skin.data.polygons:
            f.material_index = 0
        skin.data.update()
        shift = old_shift.copy()
        shift[2] -= out*.25
        joint['compactVector'] = shift.tolist()
        joint['translationOnly'] = True
        joint['lockedHullAxis'] = 'X'
        joint['monotonicPetalStroke'] = True
        joint['openEndpointHoldStart'] = float(joint['compactEnd'])
        for key in ['translationClearanceZ', 'translationClearanceReleaseStart', 'translationClearanceReleaseEnd']:
            if key in joint:
                del joint[key]
            row.pop(key, None)
        row['compactVector'] = shift.tolist()
        row['monotonicPetalStroke'] = True
        row['openEndpointHoldStart'] = float(joint['compactEnd'])
        row['material'] = roof_material.name
        row['surfaceFit'] = {'adjoiningSourceRoofFace': roof_face, 'fixedRoofVertexIds': anchor_ids,
                             'roofPlanePoints': target.tolist(), 'bakedOpenClearance': out*.25,
                             'outerMeshVertexIds': sorted({v for f in skin.data.polygons
                                if len(f.vertices) == 3 and f.area > 2 and f.normal.z*out > .8 for v in f.vertices})}
        row['geometryEdits'] = [{'vertex': i, 'before': p.tolist(), 'after': shaped[i].tolist()}
                                for i,p in enumerate(original)]
        closed = shaped + shift
        row['closedBounds'] = [closed.min(0).tolist(), closed.max(0).tolist()]
        row['surfaceFit']['maxClosedOuterHeightError'] = max(abs(height(target, closed[i,:2])-closed[i,2])
                                                           for i in row['surfaceFit']['outerMeshVertexIds'])
        assert row['surfaceFit']['maxClosedOuterHeightError'] < .00002
        assert np.array_equal(shaped[:,:2], original[:,:2])
        skin['quadRoofSurfaceFit'] = True
        skin['sourceXYUnchanged'] = True

fit['petalMotion'] = 'The original petals use one monotonic Z translation between their fitted hull seat and a held open endpoint. No rotation, ship X displacement or later return stroke is applied.'
fit['seamFit'] = 'The complete outer skin of each source 26-vertex petal is fitted in Z to its actual adjoining stationary roof face. Original topology, UVs and X/Y footprints are retained; the previous 32 fixed lip edits remain unchanged.'
fit['packingClearance'] = 'Original bearing/tube groups pack 2.0 in Y and 0.30 in Z; fork guides retain a net 0.60 Y stroke. Petals use the squared center clock. The 0.25 passage allowance is baked into the held open endpoint, with no late descent.'
fit['petalMaterial'] = 'All eight petal skins share the actual Odin_Bridge_Armor material used by the adjoining roof.'
asset['version'] = '0.11.34'
assert not bpy.data.actions
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.34.blend'), compress=True)
(review/'source-restoration.json').write_text(json.dumps(fit, indent=2)+'\n', encoding='utf8')
print('QUAD_ROOF_HOLD_FIT', [(s, [r['surfaceFit']['maxClosedOuterHeightError'] for r in q['petalSeats']])
                           for s,q in fit['quads'].items()], flush=True)
