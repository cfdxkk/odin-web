"""Restore source stern geometry and clear the bow bore without editing odin.blend.

The web copy of odin.026 was baked 2.197 m aft and 1.293 m high relative
to the original closed pose.  Its mesh is shifted rigidly back into the source
world position; neither the mesh shape nor the source action is changed.
"""

import bpy
import bmesh
import json
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.17'
inverse_asset = asset.matrix_world.inverted()


def translate_model_geometry(obj, displacement):
    model_matrix = inverse_asset @ obj.matrix_world
    local_displacement = model_matrix.to_3x3().inverted() @ Vector(displacement)
    obj.data.transform(Matrix.Translation(local_displacement))
    obj.data.update()


stern_barrel = bpy.data.objects['odin.026']
stern_alignment = Vector((0, -2.197144031524658, -1.2932260036468506))
translate_model_geometry(stern_barrel, stern_alignment)
stern_barrel['restoredSourceClosedOffsetModel'] = list(stern_alignment)

# Extend the forward slot by parking the bow's original seven-piece nose cap
# farther down the same deck incline. Its *closed* geometry remains identical.
frame = json.loads((root / 'docs/review/v0.10.0/source-covers.json').read_text())['Axial_Bow']
forward_axis = Vector(np.array(frame['frameAxes'])[:, 1])
extra_open = 3.05 * forward_axis
cap = bpy.data.objects['Axial_Bow_FrontCap']
old_slide = Vector(cap['slideVector'])
cap['slideVector'] = list(old_slide - extra_open)
cap['additionalOpenTravelModel'] = list(extra_open)
for obj in cap.children:
    if obj.type == 'MESH':
        translate_model_geometry(obj, extra_open)

# The source hull has a real flared shoulder beneath the stern muzzle-side
# leaf. A prior cover extraction removed its faces with the old armor. Bring
# back just that shoulder, retaining its original topology, UVs and paint.
source_path = root.parent / 'Odin 建模' / 'odin.blend'
with bpy.data.libraries.load(str(source_path), link=False) as (source, destination):
    destination.objects = ['holo.001']
original = destination.objects[0]
stern_frame = json.loads((root / 'docs/review/v0.10.0/source-covers.json').read_text())['Axial_Stern']
origin = np.array(stern_frame['frameOrigin'])
axes = np.array(stern_frame['frameAxes'])
source_matrix = original.matrix_world.copy()
source_points = np.array([source_matrix @ vertex.co for vertex in original.data.vertices])
local = (source_points - origin) @ axes
current_hull = bpy.data.objects['holo.001']
current_matrix = inverse_asset @ current_hull.matrix_world
current_points = np.array([current_matrix @ vertex.co for vertex in current_hull.data.vertices])


def face_key(points):
    return tuple(sorted(tuple(round(float(x), 3) for x in point) for point in points))


current_face_keys = set()
for polygon in current_hull.data.polygons:
    points = current_points[list(polygon.vertices)]
    if (abs(points[:, 0]).min() < 10 and -280 < points[:, 1].min() < -230):
        current_face_keys.add(face_key(points))

restore_faces = set()
for polygon in original.data.polygons:
    points = local[list(polygon.vertices)]
    if (np.min(np.abs(points[:, 0])) < 2.10 or
            np.max(np.abs(points[:, 0])) > 5.55 or
            points[:, 1].min() < 1.70 or points[:, 1].max() > 10.70 or
            points[:, 2].min() < -.45 or points[:, 2].max() > 3.20):
        continue
    if face_key(source_points[list(polygon.vertices)]) not in current_face_keys:
        restore_faces.add(polygon.index)
assert len(restore_faces) >= 100, len(restore_faces)

shoulder = original.copy()
shoulder.data = original.data.copy()
bpy.context.scene.collection.objects.link(shoulder)
shoulder.name = 'Axial_Stern_OriginalShoulder'
shoulder.data.name = shoulder.name
shoulder.data.transform(source_matrix)
shoulder.parent = asset
shoulder.matrix_parent_inverse = Matrix.Identity(4)
shoulder.matrix_local = Matrix.Identity(4)
mesh = bmesh.new()
mesh.from_mesh(shoulder.data)
mesh.faces.ensure_lookup_table()
bmesh.ops.delete(mesh, geom=[face for face in mesh.faces if face.index not in restore_faces], context='FACES')
bmesh.ops.delete(mesh, geom=[vertex for vertex in mesh.verts if not vertex.link_faces], context='VERTS')
mesh.to_mesh(shoulder.data)
mesh.free()
shoulder.data.update()
for index, material in enumerate(shoulder.data.materials):
    label = material.name.lower() if material else ''
    paint = ('Odin_Paint_Orange' if 'orange' in label else
             'Odin_Paint_Dark.001' if 'dark' in label else 'Odin_Paint_Light')
    shoulder.data.materials[index] = bpy.data.materials[paint]
shoulder['restoredFrom'] = 'odin.blend/holo.001'
shoulder['sourceFaceCount'] = len(restore_faces)
shoulder['station'] = 'Axial_Stern'

# The actual foremost plate is farther down the muzzle channel than the old
# substitute (the source roof at station 26..33, not the roof at 16..26).
# Extract precisely that existing source plate so it can lift and slide.
green_candidates = []
for polygon in original.data.polygons:
    points = local[list(polygon.vertices)]
    lower, upper = points.min(0), points.max(0)
    if (polygon.area > 18 and 25.8 < lower[1] < 26.2 and
            32.5 < upper[1] < 33.0 and np.max(np.abs(points[:, 0])) < 3):
        green_candidates.append(polygon)
major_faces = [max((polygon for polygon in green_candidates
                    if local[list(polygon.vertices), 0].mean() * sign > 0),
                   key=lambda polygon: polygon.area)
               for sign in (-1, 1)]
cap_faces = set()
for major in major_faces:
    corners = set(major.vertices)
    for polygon in original.data.polygons:
        if len(corners.intersection(polygon.vertices)) < 2:
            continue
        points = local[list(polygon.vertices)]
        lower, upper = points.min(0), points.max(0)
        if (lower[1] >= 25.2 and upper[1] <= 33.2 and
                np.max(np.abs(points[:, 0])) <= 3.2 and
                lower[2] >= 2.0 and upper[2] <= 7.2):
            cap_faces.add(polygon.index)
cap_vertex_ids = {vertex for face_index in cap_faces
                  for vertex in original.data.polygons[face_index].vertices}
assert len(cap_faces) == 8 and len(cap_vertex_ids) == 16, (len(cap_faces), len(cap_vertex_ids))

# Those eight faces currently live in the fixed hull. Removing the matching
# source faces prevents a stationary duplicate when the plate opens.
source_cap_keys = {face_key(source_points[list(original.data.polygons[index].vertices)])
                   for index in cap_faces}
mesh = bmesh.new()
mesh.from_mesh(current_hull.data)
remove_faces = [face for face in mesh.faces
                if face_key([current_matrix @ vertex.co for vertex in face.verts]) in source_cap_keys]
assert len(remove_faces) == len(cap_faces), (len(remove_faces), len(cap_faces))
bmesh.ops.delete(mesh, geom=remove_faces, context='FACES')
bmesh.ops.delete(mesh, geom=[vertex for vertex in mesh.verts if not vertex.link_faces], context='VERTS')
mesh.to_mesh(current_hull.data)
mesh.free()
current_hull.data.update()

stern_cap = bpy.data.objects['Axial_Stern_FrontCap']
for old_skin in list(stern_cap.children):
    if old_skin.type == 'MESH':
        bpy.data.objects.remove(old_skin, do_unlink=True)
skin = original.copy()
skin.data = original.data.copy()
bpy.context.scene.collection.objects.link(skin)
skin.name = 'Axial_Stern_FrontCap_Skin'
skin.data.name = skin.name
skin.data.transform(source_matrix)
mesh = bmesh.new()
mesh.from_mesh(skin.data)
mesh.faces.ensure_lookup_table()
bmesh.ops.delete(mesh, geom=[face for face in mesh.faces if face.index not in cap_faces], context='FACES')
bmesh.ops.delete(mesh, geom=[vertex for vertex in mesh.verts if not vertex.link_faces], context='VERTS')
mesh.to_mesh(skin.data)
mesh.free()
skin.data.update()
# The original plate is the closed endpoint at the green-marked position.
# Author its open endpoint farther forward and above its source deck line;
# the existing JS lift-first, slide-second timing brings it back exactly.
open_shift = Vector(axes[:, 1]) * 5.1 + Vector(axes[:, 2]) * .7
skin.data.transform(Matrix.Translation(open_shift))
skin.parent = stern_cap
skin.matrix_parent_inverse = Matrix.Identity(4)
bpy.context.view_layer.update()
skin.matrix_world = asset.matrix_world.copy()
for index, material in enumerate(skin.data.materials):
    label = material.name.lower() if material else ''
    paint = ('Odin_Paint_Orange' if 'orange' in label else
             'Odin_Paint_Dark.001' if 'dark' in label else 'Odin_Paint_Light')
    skin.data.materials[index] = bpy.data.materials[paint]
skin['sourceGeometry'] = True
skin['restoredFrom'] = 'odin.blend/holo.001'
skin['sourceFaceCount'] = len(cap_faces)
stern_cap['sourceObject'] = 'holo.001'
stern_cap['armorTemplate'] = 'odin.blend/holo.001 foremost source roof'
stern_cap['sourceGeometry'] = True
stern_cap['slideVector'] = list(-Vector(axes[:, 1]) * 5.1)
stern_cap['settleVector'] = list(-Vector(axes[:, 2]) * .7)
stern_cap['originalClosedBounds'] = [local[list(cap_vertex_ids)].min(0).tolist(),
                                    local[list(cap_vertex_ids)].max(0).tolist()]
stern_cap['originalOpenBounds'] = [(local[list(cap_vertex_ids)].min(0) + [0, 5.1, .7]).tolist(),
                                  (local[list(cap_vertex_ids)].max(0) + [0, 5.1, .7]).tolist()]
if 'closedCrownLineModel' in stern_cap:
    del stern_cap['closedCrownLineModel']

# The source hull also has a fixed forward roof below that moving plate. Those
# faces were lost during the older replacement. Restore them exactly as drawn
# in odin.blend: no remeshing, offset, or substitute armor surface.
forward_faces = set()
for polygon in original.data.polygons:
    points = local[list(polygon.vertices)]
    if (points[:, 1].min() < 18.40 or points[:, 1].max() > 27.00 or
            np.max(np.abs(points[:, 0])) > 3.20 or
            points[:, 2].min() < 2.70 or points[:, 2].max() > 6.25):
        continue
    if (polygon.index not in cap_faces and
            face_key(source_points[list(polygon.vertices)]) not in current_face_keys):
        forward_faces.add(polygon.index)
assert len(forward_faces) >= 30, len(forward_faces)
forward_hull = original.copy()
forward_hull.data = original.data.copy()
bpy.context.scene.collection.objects.link(forward_hull)
forward_hull.name = 'Axial_Stern_OriginalForwardHull'
forward_hull.data.name = forward_hull.name
forward_hull.data.transform(source_matrix)
forward_hull.parent = asset
forward_hull.matrix_parent_inverse = Matrix.Identity(4)
forward_hull.matrix_local = Matrix.Identity(4)
mesh = bmesh.new()
mesh.from_mesh(forward_hull.data)
mesh.faces.ensure_lookup_table()
bmesh.ops.delete(mesh, geom=[face for face in mesh.faces if face.index not in forward_faces], context='FACES')
bmesh.ops.delete(mesh, geom=[vertex for vertex in mesh.verts if not vertex.link_faces], context='VERTS')
mesh.to_mesh(forward_hull.data)
mesh.free()
forward_hull.data.update()
for index, material in enumerate(forward_hull.data.materials):
    label = material.name.lower() if material else ''
    paint = ('Odin_Paint_Orange' if 'orange' in label else
             'Odin_Paint_Dark.001' if 'dark' in label else 'Odin_Paint_Light')
    forward_hull.data.materials[index] = bpy.data.materials[paint]
forward_hull['restoredFrom'] = 'odin.blend/holo.001'
forward_hull['sourceFaceCount'] = len(forward_faces)
bpy.data.objects.remove(original, do_unlink=True)

asset['version'] = '0.11.18'
asset['sternBarrelSourceAlignmentModel'] = list(stern_alignment)
asset['sternSourceShoulderFaces'] = len(restore_faces)
asset['sternOriginalFrontPlateFaces'] = len(cap_faces)
asset['sternOriginalForwardHullFaces'] = len(forward_faces)
asset['bowAdditionalFrontCapTravelModel'] = list(extra_open)
output = root / 'assets/blender/odin_articulated_v0.11.18.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('RESTORED_STERN_AND_BOW', output, len(restore_faces), len(cap_faces), len(forward_faces), list(extra_open), flush=True)
