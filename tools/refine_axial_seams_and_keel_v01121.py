"""Clean axial seams and fit a stationary keel bay with the accepted stern armor.

Run on v0.11.20. Source .blend files and the bow/stern gun joints are untouched.
The keel mount bakes the exact old 14% carriage position, not a new offset.
"""
import bpy
import bmesh
import hashlib
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.20'
inv = asset.matrix_world.inverted()
frames = json.loads((root / 'docs/review/v0.10.0/source-covers.json').read_text())
review = root / 'docs/review/v0.11.21'
review.mkdir(parents=True, exist_ok=True)
report = {}


def model_points(obj):
    return np.array([(inv @ obj.matrix_world) @ vertex.co for vertex in obj.data.vertices])


def fingerprint(obj):
    digest = hashlib.sha256()
    coords = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', coords)
    digest.update(coords.tobytes())
    for face in obj.data.polygons:
        digest.update(np.asarray(tuple(face.vertices), dtype=np.int32).tobytes())
        digest.update(obj.data.materials[face.material_index].name.encode())
    return digest.hexdigest()


before = {obj.name: fingerprint(obj) for obj in bpy.context.scene.objects if obj.type == 'MESH'}
joint_before = {obj.name: np.array(obj.matrix_local).copy() for obj in bpy.context.scene.objects
                if obj.get('staticJoint')}

# The six original outboard skirts were left floating after the receiver moved.
# Delete only those disconnected 166-vertex islands; retain the floor and all
# fifteen bore supports, including the fitted forward receiver seam.
receiver = bpy.data.objects['Axial_Bow_SourceReceiver_Skin']
bow_origin = np.array(frames['Axial_Bow']['frameOrigin']) + np.array(
    bpy.data.objects['Axial_Bow_SourceReceiver']['receiverShiftModel'])
bow_axes = np.array(frames['Axial_Bow']['frameAxes'])
coords = (model_points(receiver) - bow_origin) @ bow_axes
parents = list(range(len(coords)))


def find(index):
    while parents[index] != index:
        parents[index] = parents[parents[index]]
        index = parents[index]
    return index


for edge in receiver.data.edges:
    a, b = edge.vertices
    parents[find(a)] = find(b)
groups = {}
for vertex in receiver.data.vertices:
    groups.setdefault(find(vertex.index), []).append(vertex.index)
remove = []
removed_bounds = []
for ids in groups.values():
    low, high = coords[ids].min(0), coords[ids].max(0)
    if (len(ids) == 166 and min(abs(low[0]), abs(high[0])) > 4.7 and
            max(abs(low[0]), abs(high[0])) < 5.5 and low[1] > -15.1 and high[1] < 10.4):
        remove.extend(ids)
        removed_bounds.append([low.tolist(), high.tolist()])
assert len(removed_bounds) == 6 and len(remove) == 996
mesh = bmesh.new()
mesh.from_mesh(receiver.data)
mesh.verts.ensure_lookup_table()
bmesh.ops.delete(mesh, geom=[mesh.verts[index] for index in remove], context='VERTS')
mesh.to_mesh(receiver.data)
mesh.free()
receiver.data.update()
report['bowRemovedSkirts'] = {'count': 6, 'vertices': 996, 'localBounds': removed_bounds}

# Slightly narrow only the stern cap's central return. Its outer edges, length,
# thickness, source topology and both travel vectors remain unchanged.
stern_origin = np.array(frames['Axial_Stern']['frameOrigin'])
stern_axes = np.array(frames['Axial_Stern']['frameAxes'])
cap_mesh = bpy.data.objects['Axial_Stern_FrontCap_Skin']
cap_matrix = inv @ cap_mesh.matrix_world
cap_inverse = cap_matrix.inverted()
cap_points = model_points(cap_mesh)
cap_local = (cap_points - stern_origin) @ stern_axes
original_gap = 2 * float(np.min(np.abs(cap_local[:, 0])))
for vertex, point in zip(cap_mesh.data.vertices, cap_local):
    target = point.copy()
    target[0] -= np.sign(point[0]) * .055 * np.clip(1 - abs(point[0]) / 2.80, 0, 1)
    vertex.co = cap_inverse @ Vector(stern_origin + stern_axes @ target)
cap_mesh.data.update()
report['sternNoseCenterGap'] = {'before': original_gap,
    'after': 2 * float(np.min(np.abs(((model_points(cap_mesh) - stern_origin) @ stern_axes)[:, 0])))}


def add_lips(prefix, origin, axes, parent, width, crown_z, y_start, y_end, profile):
    """Extend the fixed outboard slot wall up to the leaf's contact edge."""
    vertices, faces, materials = [], [], []
    light = bpy.data.materials['Odin_Paint_Light']
    red = bpy.data.materials['Odin_Turret_Interior_DeepRed']
    for sign in (-1, 1):
        # Lower edge lies on the original fixed support line. The upper edge
        # stops below the leaf's backing, leaving room for the hinge sweep.
        stations = [y_start] + [p[1] for p in profile if y_start < p[1] < y_end] + [y_end]
        for a, b in zip(stations, stations[1:]):
            def lower(y):
                return [sign * float(np.interp(y, profile[:,1], profile[:,0])), y,
                        float(np.interp(y, profile[:,1], profile[:,2]))]
            points = [lower(a), lower(b), [sign * (width + .045), b, crown_z - .10],
                      [sign * (width + .045), a, crown_z - .10]]
            inner = [np.array(point) + np.array([-sign * .10, 0, -.045]) for point in points]
            base = len(vertices)
            vertices += [(parent.matrix_world.inverted() @ asset.matrix_world) @ Vector(origin + axes @ np.array(p))
                         for p in points + inner]
            side_faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2),
                          (2, 6, 7, 3), (3, 7, 4, 0)]
            if sign < 0:
                side_faces = [tuple(reversed(face)) for face in side_faces]
            faces += [tuple(base + index for index in face) for face in side_faces]
            materials += [0, 1, 0, 0, 0, 0]
    data = bpy.data.meshes.new(prefix + '_FixedSlotLips')
    data.from_pydata(vertices, [], faces)
    data.materials.append(light)
    data.materials.append(red)
    obj = bpy.data.objects.new(data.name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.matrix_local = Matrix.Identity(4)
    for face, material_index in zip(data.polygons, materials):
        face.material_index = material_index
    obj['stationaryHullLip'] = True
    obj['hingeClearanceModel'] = .10
    data.update()
    return obj


stern_hull = bpy.data.objects['holo.001']
stern_hull_local = (model_points(stern_hull) - stern_origin) @ stern_axes
profile = []
for index in (156176, 156172, 156170):
    for p in stern_hull_local[list(stern_hull.data.polygons[index].vertices)]:
        if 2.5 < p[0] < 3.3 and p[2] > 1.1:
            profile.append(p)
profile = np.array(sorted(profile, key=lambda p:p[1]))
assert len(profile) == 6
add_lips('Axial_Stern', stern_origin, stern_axes, asset, 2.46, 2.49, -16.25, 10.53, profile)
report['sternFixedSlotLip'] = {'length': 26.78, 'hingeClearance': .10, 'innerMaterial': 'Odin_Turret_Interior_DeepRed'}
report['sternFixedSlotWallLowerProfile'] = profile.tolist()

# Bake the old carriage at exactly fourteen percent. Every keel part remains
# below this mount; its whole-assembly translation is removed from the JS rig.
mount = bpy.data.objects['Axial_Keel_Mount']
delta = np.array([0, 14.270 * (20 / 27), -6.135 * (20 / 27)])
mount.location += Vector(delta)
mount['fixedAtPriorDeployment'] = .14
mount['fixedAssemblyOffsetModel'] = delta.tolist()
bpy.context.view_layer.update()
keel_origin = np.array(frames['Axial_Keel']['frameOrigin']) + delta
keel_axes = np.array(frames['Axial_Keel']['frameAxes'])
target_matrix = inv @ mount.matrix_world
target_inverse = target_matrix.inverted()
report['keelLockedMountModel'] = list(mount.location)
report['keelLockedOffsetModel'] = delta.tolist()

for obj in sorted([obj for obj in bpy.data.objects if obj.name.startswith(
        ('Axial_Keel_Shutter_', 'Axial_Keel_FrontCap'))], key=lambda obj: len(obj.name), reverse=True):
    bpy.data.objects.remove(obj, do_unlink=True)


def relocate(point):
    local = (point - stern_origin) @ stern_axes
    local[0] *= (2.298 / 2.46)
    local[1] += .14
    local[2] -= .54
    return keel_origin + keel_axes @ local


def copy_props(source, target):
    for key, value in source.items():
        if hasattr(value, 'to_list'):
            value = value.to_list()
        target[key] = value


for side in ('Port', 'Starboard'):
    for index in range(3):
        source = bpy.data.objects[f'Axial_Stern_Shutter_{side}_{index:02d}']
        hinge = np.array((inv @ source.matrix_world).translation)
        target_hinge = relocate(hinge)
        joint = bpy.data.objects.new(f'Axial_Keel_Shutter_{side}_{index:02d}', None)
        bpy.context.scene.collection.objects.link(joint)
        joint.parent = mount
        joint.location = target_inverse @ Vector(target_hinge)
        copy_props(source, joint)
        joint['barrelJoint'] = 'Axial_Keel_Barrel'
        joint['hingeAxisModel'] = keel_axes[:, 1].tolist()
        joint['hingeEdgeModel'] = [relocate(np.array(p)).tolist() for p in source['hingeEdgeModel']]
        joint['closedEndEdgesModel'] = [[relocate(np.array(p)).tolist() for p in edge]
                                      for edge in source['closedEndEdgesModel']]
        joint['receiverDatumShiftModel'] = delta.tolist()
        joint['armorAnimationTemplate'] = source.name
        joint['armorThickness'] = .23
        R_source = np.array(Quaternion(Vector(source['hingeAxisModel']),
                         math.radians(source['closedAngleDegrees'])).to_matrix())
        R_target = np.array(Quaternion(Vector(joint['hingeAxisModel']),
                         math.radians(joint['closedAngleDegrees'])).to_matrix())
        for child in source.children:
            if child.type != 'MESH':
                continue
            points = model_points(child)
            closed = hinge + (points - hinge) @ R_source.T
            target_closed = np.array([relocate(p) for p in closed])
            opened = target_hinge + (target_closed - target_hinge) @ R_target
            data = child.data.copy()
            name = child.name.replace('Axial_Stern', 'Axial_Keel')
            data.name = name
            obj = bpy.data.objects.new(name, data)
            bpy.context.scene.collection.objects.link(obj)
            obj.parent = joint
            for vertex, point in zip(data.vertices, opened):
                vertex.co = point - target_hinge
            data.update()

# Use the same original-source shell as the stern's accepted foremost plate.
# It is an independent seventh cover, lifting before sliding down the bore.
source_cap = bpy.data.objects['Axial_Stern_FrontCap']
source_offset = np.array(source_cap['slideVector']) + np.array(source_cap['settleVector'])
cap = bpy.data.objects.new('Axial_Keel_FrontCap', None)
bpy.context.scene.collection.objects.link(cap)
cap.parent = mount
copy_props(source_cap, cap)
cap['barrel'] = 'Axial_Keel_Barrel'
cap['armorAnimationTemplate'] = source_cap.name
cap['slideVector'] = (keel_axes[:, 1] * -8).tolist()
cap['settleVector'] = (keel_axes[:, 2] * -.60).tolist()
cap['receiverDatumShiftModel'] = delta.tolist()
offset = np.array(cap['slideVector']) + np.array(cap['settleVector'])
cap.location = target_inverse @ Vector(relocate(np.array((inv @ source_cap.matrix_world).translation) + source_offset) - offset)
bpy.context.view_layer.update()
cap_inverse = (inv @ cap.matrix_world).inverted()
red = bpy.data.materials['Odin_Turret_Interior_DeepRed']
for child in source_cap.children:
    if child.type != 'MESH':
        continue
    closed = model_points(child) + source_offset
    mapped_closed = np.array([relocate(p) for p in closed])
    # The keel's existing forward crown is a little taller than the stern
    # template. Keep the fitted rear seam, and seat the front crown on that
    # measured original receiver edge rather than leaving a stepped opening.
    fixed_hull = bpy.data.objects['holo.022']
    fixed_local = (model_points(fixed_hull) - keel_origin) @ keel_axes
    fixed_roof = fixed_local[list(fixed_hull.data.polygons[24539].vertices)]
    receiver_crown = fixed_roof[np.argmin(fixed_roof[:,1])]
    cap_local = (mapped_closed - keel_origin) @ keel_axes
    crown_index = int(np.argmax(cap_local[:,2]))
    fore_delta = np.array([0, receiver_crown[1] - .02 - cap_local[crown_index,1],
                          receiver_crown[2] - cap_local[crown_index,2]])
    for index, p in enumerate(cap_local):
        across = np.clip((abs(p[0]) - .16) / (2.64 - .16), 0, 1)
        front_y = 19.0805 * (1-across) + 15.9069 * across
        along = np.clip((p[1] - 10.70) / (front_y - 10.70), 0, 1)
        mapped_closed[index] += keel_axes @ (fore_delta * along * (1-across))
    report['keelReceiverForeCrownLocal'] = receiver_crown.tolist()
    report['keelForeCrownGapModel'] = .02
    opened = mapped_closed - offset
    data = child.data.copy()
    data.name = child.name.replace('Axial_Stern', 'Axial_Keel')
    obj = bpy.data.objects.new(data.name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = cap
    for vertex, point in zip(data.vertices, opened):
        vertex.co = cap_inverse @ Vector(point)
    data.update()
    bpy.context.view_layer.update()
    if red.name not in data.materials:
        data.materials.append(red)
    for face in data.polygons:
        normal = np.array((inv @ obj.matrix_world).to_3x3().inverted().transposed() @ face.normal) @ keel_axes
        if normal[2] < -.25:
            face.material_index = data.materials.find(red.name)
    cap['originalOpenBounds'] = [((opened-keel_origin)@keel_axes).min(0).tolist(),
                                 ((opened-keel_origin)@keel_axes).max(0).tolist()]
    cap['originalClosedBounds'] = [((mapped_closed-keel_origin)@keel_axes).min(0).tolist(),
                                   ((mapped_closed-keel_origin)@keel_axes).max(0).tolist()]

fixed_local = (model_points(bpy.data.objects['holo.022']) - keel_origin) @ keel_axes
keel_profile = []
for p in profile:
    expected = p + np.array([-.1657,.14,-.53635])
    keel_profile.append(fixed_local[np.argmin(np.linalg.norm(fixed_local-expected, axis=1))])
keel_profile = np.array(keel_profile)
add_lips('Axial_Keel', keel_origin, keel_axes, mount, 2.298, 1.95, -16.11, 10.67, keel_profile)

# The original channel is part of the stationary keel hull. Recolor only its
# inward walls, floor and rib faces, retaining the gray painted outer shell.
hull = bpy.data.objects['holo.022']
points = model_points(hull)
local = (points - keel_origin) @ keel_axes
if red.name not in hull.data.materials:
    hull.data.materials.append(red)
red_index = hull.data.materials.find(red.name)
normal_matrix = np.array((inv @ hull.matrix_world).to_3x3().inverted().transposed())
red_faces = []
for face in hull.data.polygons:
    coords = local[list(face.vertices)]
    center = coords.mean(0)
    if not (-19 < center[1] < 27 and np.max(np.abs(coords[:, 0])) < 3.1 and -4 < center[2] < 5.4):
        continue
    normal = (normal_matrix @ np.array(face.normal)) @ keel_axes
    inward_wall = abs(center[0]) > .35 and center[0] * normal[0] < -.35
    floor = abs(center[0]) < 1.85 and center[2] < 1.0 and normal[2] > .6
    rib = abs(center[0]) < 2.3 and center[2] < 2.0 and abs(normal[1]) > .75
    if (inward_wall or floor or rib) and hull.data.materials[face.material_index].name in (
            'Odin_Paint_Light', 'Odin_Paint_Dark.001'):
        face.material_index = red_index
        red_faces.append(face.index)
hull.data.update()
report['keelRedChannelFaces'] = len(red_faces)
assert len(red_faces) > 100
asset['version'] = '0.11.21'
bpy.context.view_layer.update()

# Catch unintended edits before writing the new version. Mesh-local geometry
# and local joint transforms for all other systems must remain byte-identical.
allowed = {'Axial_Bow_SourceReceiver_Skin', 'Axial_Stern_FrontCap_Skin', 'holo.022'}
unchanged_meshes = 0
for name, digest in before.items():
    if name.startswith(('Axial_Keel_Shutter_', 'Axial_Keel_FrontCap')) or name in allowed:
        continue
    assert fingerprint(bpy.data.objects[name]) == digest, ('Unintended mesh change', name)
    unchanged_meshes += 1
unchanged_joints = 0
for name, matrix in joint_before.items():
    if name.startswith(('Axial_Keel_Shutter_', 'Axial_Keel_FrontCap')) or name == 'Axial_Keel_Mount':
        continue
    assert np.array_equal(np.array(bpy.data.objects[name].matrix_local), matrix), ('Joint changed', name)
    unchanged_joints += 1
report['unchangedMeshCount'] = unchanged_meshes
report['unchangedJointCount'] = unchanged_joints
report['keelArmorTemplate'] = 'Axial_Stern: six flank-derived leaves and original source nose shell'
(review / 'geometry-audit.json').write_text(json.dumps(report, indent=2), encoding='utf8')
output = root / 'assets/blender/odin_articulated_v0.11.21.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('REFINED_AXIAL_AND_KEEL', output, json.dumps(report), flush=True)
