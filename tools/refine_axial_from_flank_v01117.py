"""Refit seven flank-derived covers at each axial bay without touching guns.

The accepted v0.11.16 barrel, receiver, hull and source actions are unchanged.
Only the duplicated flank armor meshes and their static joints are replaced.
"""

import bpy
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Quaternion, Vector

root = Path(__file__).resolve().parents[1]
frames = json.loads((root / 'docs/review/v0.10.0/source-covers.json').read_text())
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.16'
inverse_asset = asset.matrix_world.inverted()
template_name = 'SideBattery_1_Starboard'
template_frame = frames[template_name]
template_origin = np.array(template_frame['frameOrigin'])
template_axes = np.array(template_frame['frameAxes'])
template_carriage = bpy.data.objects[template_name + '_Carriage']
template_carriage_closed = np.array(template_carriage['liftVector']) + np.array(template_carriage['slideVector'])


def mesh_points_model(obj):
    model_matrix = inverse_asset @ obj.matrix_world
    return np.array([model_matrix @ vertex.co for vertex in obj.data.vertices])


def create_joint(name, origin, **data):
    joint = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(joint)
    joint.parent = asset
    joint.location = origin.tolist()
    for key, value in data.items():
        joint[key] = value
    return joint


def clone_mesh(source, name, joint, opened):
    mesh = source.data.copy()  # Retain the accepted flank topology, UVs and materials.
    mesh.name = name
    child = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(child)
    child.parent = joint
    child.location = (0, 0, 0)
    child.rotation_euler = (0, 0, 0)
    child.scale = (1, 1, 1)
    for vertex, point in zip(mesh.vertices, opened):
        vertex.co = point - np.array(joint.location)
    mesh.update()
    return child


def source_leaf(index):
    joint = bpy.data.objects[f'{template_name}_Shutter_Port_{index:02d}']
    hinge = np.array(joint['sourceHingeLine'])
    rotation = np.array(Quaternion(Vector(joint['hingeAxisModel']),
                                   math.radians(joint['closedAngleDegrees'])).to_matrix())
    shift = template_carriage_closed if joint.parent == template_carriage else np.zeros(3)
    parts = {}
    for child in joint.children:
        if child.type != 'MESH':
            continue
        opened = mesh_points_model(child)
        closed = hinge + (opened - hinge) @ rotation.T + shift
        parts[child.name.rsplit('_', 1)[-1]] = (child, (closed - template_origin) @ template_axes)
    assert set(parts) == {'Skin', 'FittedBacking'}, (joint.name, list(parts))
    # The first six backing vertices are the accepted exterior roof.  Its
    # outer and inner corners provide a per-panel surface against which all
    # of the retained flank grate detail is remapped.
    backing = parts['FittedBacking'][1]
    roof = backing[:6]
    u_outer = float(np.mean(-roof[[0, 3], 0]))
    u_inner = float(np.mean(-roof[[2, 5], 0]))
    all_points = np.concatenate([part[1] for part in parts.values()])
    return parts, roof, u_inner, u_outer, float(all_points[:, 1].min()), float(all_points[:, 1].max())


leaves = [source_leaf(index) for index in range(3)]
slider = bpy.data.objects[template_name + '_Slider_Port']
slider_mesh = next(child for child in slider.children if child.type == 'MESH')
slider_points = (mesh_points_model(slider_mesh) - template_origin) @ template_axes
slider_top = slider_points[:9]
slider_u_inner = float(np.mean(-slider_top[[2, 5, 8], 0]))
slider_u_outer = float(np.mean(-slider_top[[0, 3, 6], 0]))
slider_y_min, slider_y_max = float(slider_points[:, 1].min()), float(slider_points[:, 1].max())


def roof_level(point, roof, u_inner, u_outer, y_min, y_max):
    u = -point[0]
    across = np.clip((u - u_inner) / (u_outer - u_inner), 0, 1)
    rear = roof[2, 1] * (1 - across) + roof[0, 1] * across
    front = roof[5, 1] * (1 - across) + roof[3, 1] * across
    along = np.clip((point[1] - rear) / (front - rear), 0, 1)
    outside = roof[0, 2] * (1 - along) + roof[3, 2] * along
    inside = roof[2, 2] * (1 - along) + roof[5, 2] * along
    return outside * across + inside * (1 - across)


def crown_uplift(station, y):
    along = np.clip((y + 16.25) / (10.53 + 16.25), 0, 1)
    return (.15 + .50 * along) if station == 'Bow' else .20 * along


def target_leaf(point, source, segment, side, frame, index):
    _, roof, u_inner, u_outer, y_min, y_max = source
    fraction = np.clip((-point[0] - u_inner) / (u_outer - u_inner), 0, 1)
    # The flank plates are raked: their crown begins and ends farther along
    # the bore than the outboard hinge edge.  Normalize each longitudinal
    # profile at its own width, so axial neighbors meet across the complete
    # tent surface instead of leaving a V-shaped slit at every crown seam.
    source_rear = roof[2, 1] * (1 - fraction) + roof[0, 1] * fraction
    source_front = roof[5, 1] * (1 - fraction) + roof[3, 1] * fraction
    progress = np.clip((point[1] - source_rear) / (source_front - source_rear), -.005, 1.005)
    y = segment[0] + (segment[1] - segment[0]) * progress
    if index == 0:
        # Shorten only the inboard rear corner where the bow breech housing
        # overlaps the first leaf. Its muzzle-side edge must still meet leaf 2.
        # The former 2.80-unit bow retreat opened a visible triangular hole.
        rear_trim = 1.35 if frame[2] == 'Bow' else .80
        y += rear_trim * (1 - fraction) * (1 - progress)
    x = side * (0.015 + (2.46 - 0.015) * fraction)
    residual = (point[2] - roof_level(point, roof, u_inner, u_outer, y_min, y_max)) * .80
    origin, axes, station = frame
    ridge = 5.22 + crown_uplift(station, y)
    z = ridge * (1 - fraction) + 2.49 * fraction + residual
    return origin + axes @ np.array((x, y, z))


def target_cap(point, side, frame):
    fraction = np.clip((-point[0] - slider_u_inner) / (slider_u_outer - slider_u_inner), 0, 1)
    source_rear = slider_top[2, 1] * (1 - fraction) + slider_top[0, 1] * fraction
    source_front = slider_top[8, 1] * (1 - fraction) + slider_top[6, 1] * fraction
    progress = np.clip((point[1] - source_rear) / (source_front - source_rear), -.005, 1.005)
    y = 10.55 + (20.50 - 10.55) * progress
    width = 2.46 + .60 * progress
    x = side * (0.015 + (width - 0.015) * fraction)
    outer_z = slider_top[0, 2] * (1 - progress) + slider_top[6, 2] * progress
    inner_z = slider_top[2, 2] * (1 - progress) + slider_top[8, 2] * progress
    source_roof = outer_z * fraction + inner_z * (1 - fraction)
    residual = (point[2] - source_roof) * .80
    target_outer = 2.49 + .20 * progress
    origin, axes, station = frame
    # Carry the leaves' crown tangent through the complete nose plate.  The
    # former downward taper broke the silhouette exactly at this seam.
    crown_slope = (.50 if station == 'Bow' else .20) / (10.53 + 16.25)
    target_inner = 5.22 + crown_uplift(station, 10.53) + crown_slope * (y - 10.53)
    z = target_inner * (1 - fraction) + target_outer * fraction + residual
    return origin + axes @ np.array((x, y, z))


for station in ('Bow', 'Stern'):
    prefix = f'Axial_{station}'
    frame_data = frames[prefix]
    origin = np.array(frame_data['frameOrigin'])
    receiver_shift = np.zeros(3)
    if station == 'Bow':
        receiver_shift = np.array(bpy.data.objects['Axial_Bow_SourceReceiver']['receiverShiftModel'])
        origin += receiver_shift
    axes = np.array(frame_data['frameAxes'])
    frame = origin, axes, station
    axis = axes[:, 1]
    # Replace only the old axial armor, leaving both source turret assemblies
    # and the bow receiver absolutely unchanged.
    old_covers = [obj for obj in list(bpy.data.objects)
                  if obj.name.startswith((prefix + '_Shutter_', prefix + '_FrontCap'))]
    for obj in sorted(old_covers, key=lambda item: len(item.name), reverse=True):
        bpy.data.objects.remove(obj, do_unlink=True)
    segments = [(-16.25, -6.525), (-6.525, 1.90), (1.90, 10.53)]
    seam_edges = {}
    for side_name, side in (('Port', -1), ('Starboard', 1)):
        for index, segment in enumerate(segments):
            source = leaves[index]
            roof = source[1]
            closed_edges = [
                [target_leaf(roof[which], source, segment, side, frame, index).tolist()
                 for which in pair]
                for pair in ((0, 2), (3, 5))
            ]
            seam_edges[side_name, index] = closed_edges
            hinge = origin + axes @ np.array((side * 2.46, segment[0], 2.49))
            angle = -side * 150.0
            rotation = np.array(Quaternion(Vector(axis), math.radians(angle)).to_matrix())
            if station == 'Bow':
                open_start, open_end = (0.07, 0.10, 0.13)[index], (0.22, 0.26, 0.29)[index]
            else:
                open_start, open_end = .26 + index * .035, .53 + index * .055
            name = f'{prefix}_Shutter_{side_name}_{index:02d}'
            joint = create_joint(name, hinge, staticJoint=True, system='single-shutter',
                                 barrelJoint=prefix + '_Barrel', physicalHinge=True,
                                 hingeAxisModel=axis.tolist(), closedAngleDegrees=angle,
                                 panelIndex=index, armorGroup=4-index,
                                 openStart=open_start, openEnd=open_end,
                                 armorThickness=.23, sourceGeometry=True,
                                 sourceObject=template_name,
                                 armorTemplate=f'{template_name}_Shutter_Port_{index:02d}',
                                 hingeEdgeModel=[hinge.tolist(),
                                                 (hinge + axis * (segment[1]-segment[0])).tolist()],
                                 closedEndEdgesModel=closed_edges,
                                 shorterBreechTrapezoid=(index == 0),
                                 receiverDatumShiftModel=receiver_shift.tolist())
            for suffix, (mesh, points) in source[0].items():
                closed = np.array([target_leaf(point, source, segment, side, frame, index) for point in points])
                opened = hinge + (closed - hinge) @ rotation
                clone_mesh(mesh, name + '_' + suffix, joint, opened)
    # The single nose assembly uses both mirrored side-slider skins as one
    # moving plate.  They share one joint, one travel vector and one seal.
    travel = axes[:, 1] * -5.02
    # The opened cap is above its seal. It lifts before translating forward.
    settle = axes[:, 2] * -.42
    cap_origin = origin + axes @ np.array((0, 10.55, 5.22 + crown_uplift(station, 10.53))) - travel - settle
    cap = create_joint(prefix + '_FrontCap', cap_origin, staticJoint=True,
                       system='single-front-cap', barrel=prefix + '_Barrel',
                       sourceOpenPose=True, slideVector=travel.tolist(),
                       settleVector=settle.tolist(), armorThickness=.23,
                       armorGroup=1, sourceObject=template_name,
                       armorTemplate=template_name + '_Slider_Port',
                       onePieceNoseAssembly=True,
                       slideStart=(.075 if station == 'Bow' else .10),
                       slideEnd=(.23 if station == 'Bow' else .25),
                       settleStart=0.0,
                       settleEnd=(.06 if station == 'Bow' else .08),
                       receiverDatumShiftModel=receiver_shift.tolist())
    cap['closedCrownLineModel'] = [
        target_cap(slider_top[which], -1, frame).tolist() for which in (2, 5, 8)
    ]
    for side_name, side in (('Port', -1), ('Starboard', 1)):
        closed = np.array([target_cap(point, side, frame) for point in slider_points])
        opened = closed - travel - settle
        clone_mesh(slider_mesh, cap.name + '_Skin_' + side_name, cap, opened)
        cap_rear = [target_cap(slider_top[which], side, frame) for which in (0, 2)]
        for index in range(3):
            before = seam_edges[side_name, index][1]
            after = (seam_edges[side_name, index+1][0] if index < 2
                     else [point.tolist() for point in cap_rear])
            errors = [np.linalg.norm(np.array(a)-np.array(b)) for a,b in zip(before,after)]
            assert max(errors) < .07, (station, side_name, index, errors)
    assert len([obj for obj in bpy.data.objects if obj.get('barrelJoint') == prefix + '_Barrel']) == 6
    assert len([obj for obj in bpy.data.objects if obj.get('system') == 'single-front-cap'
                and obj.get('barrel') == prefix + '_Barrel']) == 1

asset['version'] = '0.11.17'
asset['axialArmorSource'] = 'refitted SideBattery_1_Starboard flank plates; original guns untouched'
output = root / 'assets/blender/odin_articulated_v0.11.17.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('REFITTED BOW AND STERN SEVEN-PIECE FLANK ARMOR', output, flush=True)
