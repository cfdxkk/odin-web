"""Fit the original stern nose armor and extend the bow bore clearance.

Read odin.blend only as a source library. Keep both source barrel meshes and
their Nuxt animation untouched. The saved output contains geometry and joints.
"""

import bpy
import bmesh
import json
import numpy as np
from collections import defaultdict, deque
from pathlib import Path
from mathutils import Matrix, Vector

root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.18'
inverse_asset = asset.matrix_world.inverted()
frames = json.loads((root / 'docs/review/v0.10.0/source-covers.json').read_text())
paint = bpy.data.materials['Odin_Turret_Interior_DeepRed']
light = bpy.data.materials['Odin_Paint_Light']
report = {}


def points_model(obj):
    model_matrix = inverse_asset @ obj.matrix_world
    return np.array([model_matrix @ vertex.co for vertex in obj.data.vertices])


def keep_source_faces(source, name, face_ids, source_matrix):
    clone = source.copy()
    clone.data = source.data.copy()
    bpy.context.scene.collection.objects.link(clone)
    clone.name = name
    clone.data.name = name
    clone.data.transform(source_matrix)
    clone.parent = asset
    clone.matrix_parent_inverse = Matrix.Identity(4)
    clone.matrix_local = Matrix.Identity(4)
    mesh = bmesh.new()
    mesh.from_mesh(clone.data)
    mesh.faces.ensure_lookup_table()
    bmesh.ops.delete(mesh, geom=[face for face in mesh.faces if face.index not in face_ids], context='FACES')
    bmesh.ops.delete(mesh, geom=[vertex for vertex in mesh.verts if not vertex.link_faces], context='VERTS')
    mesh.to_mesh(clone.data)
    mesh.free()
    clone.data.update()
    for index, material in enumerate(clone.data.materials):
        label = material.name.lower() if material else ''
        target = ('Odin_Paint_Orange' if 'orange' in label else
                  'Odin_Paint_Dark.001' if 'dark' in label else 'Odin_Paint_Light')
        clone.data.materials[index] = bpy.data.materials[target]
    clone['restoredFrom'] = 'odin.blend/holo.001'
    clone['sourceFaceCount'] = len(face_ids)
    return clone


def face_key(points):
    return tuple(sorted(tuple(round(float(value), 3) for value in point) for point in points))


# The v0.11.18 moving piece was a static roof at y=26..33. Put that roof
# back into the fixed hull at its untouched source vertices, while replacing
# the moving skin with the genuine deployed plate at y=15.614..25.541.
source_path = root.parent / 'Odin 建模' / 'odin.blend'
with bpy.data.libraries.load(str(source_path), link=False) as (source, destination):
    destination.objects = ['holo.001']
original = destination.objects[0]
source_matrix = original.matrix_world.copy()
original_points = np.array([source_matrix @ vertex.co for vertex in original.data.vertices])
stern_frame = frames['Axial_Stern']
stern_origin = np.array(stern_frame['frameOrigin'])
stern_axes = np.array(stern_frame['frameAxes'])
stern_local = (original_points - stern_origin) @ stern_axes

roof_candidates = []
for face in original.data.polygons:
    pts = stern_local[list(face.vertices)]
    low, high = pts.min(0), pts.max(0)
    if (face.area > 18 and 25.8 < low[1] < 26.2 and
            32.5 < high[1] < 33.0 and np.max(np.abs(pts[:, 0])) < 3):
        roof_candidates.append(face)
roof_major = [max((face for face in roof_candidates
                   if stern_local[list(face.vertices), 0].mean() * sign > 0),
                  key=lambda face: face.area) for sign in (-1, 1)]
roof_faces = set()
for major in roof_major:
    corners = set(major.vertices)
    for face in original.data.polygons:
        if len(corners.intersection(face.vertices)) < 2:
            continue
        pts = stern_local[list(face.vertices)]
        low, high = pts.min(0), pts.max(0)
        if (low[1] >= 25.2 and high[1] <= 33.2 and
                np.max(np.abs(pts[:, 0])) <= 3.2 and low[2] >= 2.0 and high[2] <= 7.2):
            roof_faces.add(face.index)
assert len(roof_faces) == 8, len(roof_faces)
roof = keep_source_faces(original, 'Axial_Stern_OriginalNoseRoof', roof_faces, source_matrix)

# The true source armor is its own disconnected, double-sided shell (33 faces
# per side). The eight large triangular faces selected previously belong to a
# 682-face connected hull component and must never be animated as a cover.
edge_faces = defaultdict(list)
for face in original.data.polygons:
    for edge in face.edge_keys:
        edge_faces[edge].append(face.index)


def connected_faces(seed):
    seen = {seed}
    queue = deque([seed])
    while queue:
        face = original.data.polygons[queue.popleft()]
        for edge in face.edge_keys:
            for neighbor in edge_faces[edge]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
    return seen


wrong_static_faces = {12573, 110325, 158457, 196534, 196535,
                      197467, 230983, 232895}
cap_faces = connected_faces(165461) | connected_faces(199635)
assert len(cap_faces) == 66 and not cap_faces.intersection(wrong_static_faces)
cap_vertices = {vertex for face_index in cap_faces
                for vertex in original.data.polygons[face_index].vertices}
assert len(cap_vertices) == 56
cap_bounds = np.array([stern_local[list(cap_vertices)].min(0),
                       stern_local[list(cap_vertices)].max(0)])
assert 18.4 < cap_bounds[0, 1] < 18.6 and 26.8 < cap_bounds[1, 1] < 27.0

# The old forward-hull recovery also contains this disconnected shell. Strip
# it there, otherwise the original deployed plate remains as a second static
# copy while the correct one moves into the closed position.
source_cap_keys = {
    face_key(original_points[list(original.data.polygons[index].vertices)])
    for index in cap_faces
}
forward_hull = bpy.data.objects['Axial_Stern_OriginalForwardHull']
forward_matrix = inverse_asset @ forward_hull.matrix_world
mesh = bmesh.new()
mesh.from_mesh(forward_hull.data)
remove = [face for face in mesh.faces if face_key(
    [forward_matrix @ vertex.co for vertex in face.verts]) in source_cap_keys]
assert len(remove) == len(cap_faces), (len(remove), len(cap_faces))
bmesh.ops.delete(mesh, geom=remove, context='FACES')
bmesh.ops.delete(mesh, geom=[vertex for vertex in mesh.verts if not vertex.link_faces], context='VERTS')
mesh.to_mesh(forward_hull.data)
mesh.free()
forward_hull.data.update()
assert len(forward_hull.data.polygons) == 26
# Each of those 26 faces is already in the fixed source hull. Keeping this
# recovered object would z-fight against the unchanged hull at the new seam.
bpy.data.objects.remove(forward_hull, do_unlink=True)

# The two vented source leaves inserted as a static shoulder in v0.11.18
# duplicate the new six-leaf armor and are the two unwanted white panels.
shoulder = bpy.data.objects['Axial_Stern_OriginalShoulder']
assert shoulder['sourceFaceCount'] == 818
bpy.data.objects.remove(shoulder, do_unlink=True)

cap = bpy.data.objects['Axial_Stern_FrontCap']
for child in list(cap.children):
    if child.type == 'MESH':
        bpy.data.objects.remove(child, do_unlink=True)
skin = keep_source_faces(original, 'Axial_Stern_FrontCap_Skin', cap_faces, source_matrix)
skin.parent = cap
skin.matrix_parent_inverse = Matrix.Identity(4)
bpy.context.view_layer.update()
skin.matrix_world = asset.matrix_world.copy()
skin['sourceGeometry'] = True
cap['sourceObject'] = 'holo.001'
cap['armorTemplate'] = 'odin.blend/holo.001 disconnected 66-face armor shell'
cap['sourceGeometry'] = True
cap['sourceOpenPose'] = True
cap['onePieceNoseAssembly'] = True
cap['slideVector'] = list(-Vector(stern_axes[:, 1]) * 8.00)
cap['settleVector'] = list(-Vector(stern_axes[:, 2]) * .60)
cap['originalOpenBounds'] = cap_bounds.tolist()
cap['originalClosedBounds'] = (cap_bounds + [0, -8.00, -.60]).tolist()

# The leaves keep their fitted closed geometry and hinge axes. Limit just the
# deployed endpoint so the opening sweep stops at 95 degrees, clear of the
# aft hull while still leaving a wide path for azimuth traverse.
for obj in bpy.data.objects:
    if obj.get('barrelJoint') == 'Axial_Stern_Barrel':
        assert abs(abs(float(obj['closedAngleDegrees'])) - 150) < .001
        obj['openingTravelDegrees'] = 95.0

# Shift the existing bow receiver's forward slot section two units along the
# deck incline. The aft 15.6 units are identical, including the gun root and
# its seal; only the muzzle-end roof, inner trench and end armor are extended.
bow_frame = frames['Axial_Bow']
bow_axes = np.array(bow_frame['frameAxes'])
bow_origin = np.array(bow_frame['frameOrigin']) + np.array(
    bpy.data.objects['Axial_Bow_SourceReceiver']['receiverShiftModel'])
receiver = bpy.data.objects['Axial_Bow_SourceReceiver_Skin']
receiver_matrix = inverse_asset @ receiver.matrix_world
receiver_inverse = receiver_matrix.inverted()
receiver_points = points_model(receiver)
receiver_local = (receiver_points - bow_origin) @ bow_axes
changed = 0
for vertex, coordinate, model in zip(receiver.data.vertices, receiver_local, receiver_points):
    progress = np.clip((coordinate[1] - 15.6) / 4.8, 0, 1)
    if progress <= 0:
        continue
    adjusted = model + bow_axes[:, 1] * (2.0 * progress)
    vertex.co = receiver_inverse @ Vector(adjusted)
    changed += 1
receiver.data.update()
receiver['forwardChannelExtensionModel'] = list(bow_axes[:, 1] * 2.0)
receiver['forwardChannelStartLocalY'] = 15.6
receiver['forwardChannelEndLocalY'] = 22.4

# Extend the same fore-end of the existing seventh armor plate to meet the
# longer slot, keeping its rear edge exactly on the final hinged pair.
bow_cap = bpy.data.objects['Axial_Bow_FrontCap']
old_travel = Vector(bow_cap['additionalOpenTravelModel'])
closed_slide = Vector(bow_cap['slideVector'])
park_extension = Vector(bow_axes[:, 1]) * .95
for child in bow_cap.children:
    if child.type != 'MESH':
        continue
    model_matrix = inverse_asset @ child.matrix_world
    inverse = model_matrix.inverted()
    model_points = points_model(child)
    # The original plate already had a full 8.25-unit travel before the
    # v0.11.18 additional 3.05. Undo the COMPLETE open translation when
    # locating its closed rear edge, or that edge will pull away from leaf 3.
    coords = (model_points - bow_origin + closed_slide) @ bow_axes
    for vertex, point, local in zip(child.data.vertices, model_points, coords):
        progress = np.clip((local[1] - 10.55) / 9.95, 0, 1)
        extended_y = local[1] + 2.0 * progress
        # The source plate's outermost end is a square cut. Its last row now
        # follows an inclined line: the lower outer corner ends aft of the
        # upper crown, matching the ship's diagonal nose seam.
        nose_trim = 0.0
        if extended_y > 22.0:
            target_y = 22.55 - 1.30 * min(abs(local[0]) / 3.06, 1.0)
            nose_trim = target_y - extended_y
        # The two crown vertices formerly stood about 0.13 model units above
        # the fixed receiver's deck slope at this seam. Seat both surfaces of
        # the plate together to preserve its thickness and lose the lip.
        crown_seat = -0.13 if abs(local[0]) < .20 and extended_y > 20.8 else 0.0
        displacement = (bow_axes[:, 1] * (2.0 * progress + nose_trim) +
                        bow_axes[:, 2] * crown_seat + park_extension)
        vertex.co = inverse @ Vector(point + displacement)
    child.data.update()
bow_cap['slideVector'] = list(Vector(bow_cap['slideVector']) - park_extension)
bow_cap['additionalOpenTravelModel'] = list(old_travel + park_extension)
bow_cap['closedForeEndExtensionModel'] = list(bow_axes[:, 1] * 2.0)


def paint_interior(obj, station, origin, axes):
    matrix = inverse_asset @ obj.matrix_world
    points = points_model(obj)
    local = (points - origin) @ axes
    if paint.name not in obj.data.materials:
        obj.data.materials.append(paint)
    red_index = obj.data.materials.find(paint.name)
    count = 0
    selected = []
    normal_matrix = np.array(matrix.to_3x3().inverted().transposed())
    for face in obj.data.polygons:
        coords = local[list(face.vertices)]
        center = coords.mean(0)
        if not (-22 < center[1] < 29 and abs(center[0]) < 3.2):
            continue
        normal = (normal_matrix @ np.array(face.normal)) @ axes
        if obj.name.endswith('_FixedBayFloor'):
            # The four earlier flank floor pans used the dark gray material.
            # They are still inside the bore trench, so paint their upward
            # inner faces too while preserving the outer skirt and underside.
            if (obj.data.materials[face.material_index].name in
                    ('Odin_Paint_Light', 'Odin_Paint_Dark.001') and
                    center[1] < 18 and -6 < center[2] < 1 and
                    normal[2] > .6):
                face.material_index = red_index
                count += 1
                selected.append(face.index)
            continue
        material = obj.data.materials[face.material_index]
        # Stations 1 and 3 retain dark-painted inner walls and floor in the
        # original combined hull. Their complete face bounds sit wholly in
        # the narrow bore trench; broad dark exterior/deck faces do not.
        if material.name == 'Odin_Paint_Dark.001' and obj.name == 'holo.001':
            low, high = coords.min(0), coords.max(0)
            bounded = (np.max(np.abs(coords[:, 0])) < 2.72 and
                       low[1] > -2.25 and high[1] < 19.0 and
                       low[2] > -2.0 and high[2] < 3.6)
            inward = ((center[0] * normal[0] < -.35 and abs(center[0]) > 1.0) or
                      (normal[2] > .6 and abs(center[0]) < 1.75))
            if bounded and inward:
                face.material_index = red_index
                count += 1
                selected.append(face.index)
            continue
        if material != light or abs(center[0]) >= 2.4:
            continue
        inside_wall = (.35 < abs(center[0]) < 2.35 and
                       center[0] * normal[0] < -.40 and -1.8 < center[2] < 5.7)
        floor = (abs(center[0]) < 1.75 and center[2] < 1.0 and normal[2] > .65)
        end_wall = (abs(center[0]) < 2.1 and center[2] < 3.6 and
                    abs(normal[1]) > .72)
        if inside_wall or floor or end_wall:
            face.material_index = red_index
            count += 1
            selected.append(face.index)
    if count:
        obj.data.update()
    report.setdefault('redInteriorFaces', {})[station + '/' + obj.name] = count
    return count


# Repaint only fixed trough faces. The side shutter exteriors, deck paint,
# barrel steel and dark equipment keep their accepted materials.
paint_interior(receiver, 'Axial_Bow', bow_origin, bow_axes)
for index in range(1, 5):
    for side in ('Port', 'Starboard'):
        station = f'SideBattery_{index}_{side}'
        frame = frames[station]
        origin = np.array(frame['frameOrigin'])
        axes = np.array(frame['frameAxes'])
        hull = bpy.data.objects['holo.001']
        paint_interior(hull, station, origin, axes)
        for obj in bpy.data.objects:
            if obj.name.startswith(station + '_Fixed') and obj.type == 'MESH':
                paint_interior(obj, station, origin, axes)

bpy.data.objects.remove(original, do_unlink=True)
asset['version'] = '0.11.19'
asset['sternOriginalFrontPlateFaces'] = len(cap_faces)
asset['sternOriginalForwardHullFaces'] = 0
asset['sternRestoredFixedNoseRoofFaces'] = len(roof_faces)
asset['sternRemovedWrongTriangularCapFaces'] = len(wrong_static_faces)
asset['sternRemovedDuplicateShoulderFaces'] = 818
asset['sternSourceShoulderFaces'] = 0
asset['bowFrontChannelExtensionModel'] = list(bow_axes[:, 1] * 2.0)
asset['bowAdditionalFrontCapTravelModel'] = list(old_travel + park_extension)
report['sternOriginalPlateLocalBounds'] = cap_bounds.tolist()
report['sternRestoredFixedRoofFaces'] = len(roof_faces)
report['sternRemovedWrongTriangularCapFaces'] = len(wrong_static_faces)
report['sternRemovedDuplicateForwardArmorFaces'] = len(remove)
report['bowExtendedReceiverVertices'] = changed
report['bowForeEndExtensionModel'] = list(bow_axes[:, 1] * 2.0)
report['sternOpeningTravelDegrees'] = 95
review_dir = root / 'docs/review/v0.11.19'
review_dir.mkdir(parents=True, exist_ok=True)
(review_dir / 'geometry-changes.json').write_text(json.dumps(report, indent=2), encoding='utf8')
output = root / 'assets/blender/odin_articulated_v0.11.19.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('FITTED_ORIGINAL_STERN_AND_CHANNELS', output, json.dumps(report), flush=True)
