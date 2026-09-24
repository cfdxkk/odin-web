"""Fit the four main-battery aft leaves to real outboard hull hinge edges.

Designed for exec() near the end of revise_main_battery_v08.py, after the
existing aft strips and interior materials have been created. It can also run
on a v0.8 Blend for verification. The upper free edges stay at their measured
shroud positions. Only the other edge of each existing leaf is rebuilt along
the fixed exterior hull, and the empty is rebased onto that new edge. The
original holo.001 / holo.013 meshes are never edited. No .blend or GLB is saved.

This helper validates every whole degree of the 130-degree outward/downward
travel against the fixed hull and writes work/v08-review/aft-fit.json.
"""
import bpy
import json
import math
from pathlib import Path

from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree


def fit_aft_hinges_v08():
    root_path = Path(__file__).resolve().parents[1]
    source = json.loads((root_path / 'tools/main_armor_v07_boundaries.json').read_text(encoding='utf8'))
    asset_obj = bpy.data.objects['Odin_Asset']
    asset_inverse = asset_obj.matrix_world.inverted()
    # These measured X coordinates follow the outer source-hull shoulder.
    # The hinge is the rebuilt leaf's own lower/outboard edge, not a remote
    # pivot placed inside the bay. Its Y and Z slope is taken from the hull.
    # Measured fixed-hull shoulder samples are nearly collinear in X/Y:
    # Dorsal |X| 14.45@Y81, 13.90@90, 13.30@100, 12.55@112.6;
    # Ventral |X| 15.40@Y40, 15.10@45, 14.55@55, 14.05@63.5.
    exterior_x = {'Dorsal': (14.45, 12.55), 'Ventral': (15.40, 14.05)}
    clearance_cm = .35
    thickness_cm = .12

    def surface_height(hull, x, y, direction):
        transform = asset_inverse @ hull.matrix_world
        inverse = transform.inverted()
        start = inverse @ Vector((x, y, direction * 100))
        ray = inverse.to_3x3() @ Vector((0, 0, -direction))
        hit, point, _, _ = hull.ray_cast(start, ray)
        if not hit:
            raise RuntimeError(f'Fixed hull has no exterior surface at ({x:.3f}, {y:.3f})')
        return (transform @ point).z

    def hull_bvh(hull):
        hull.data.calc_loop_triangles()
        transform = asset_inverse @ hull.matrix_world
        vertices = [transform @ vert.co for vert in hull.data.vertices]
        triangles = [tuple(face.vertices) for face in hull.data.loop_triangles]
        return BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=.00001)

    def sample_leaf(mesh, hinge_start, hinge_end, angle_degrees, fixed_tree):
        mesh.data.calc_loop_triangles()
        transform = asset_inverse @ mesh.matrix_world
        vertices = [transform @ vert.co for vert in mesh.data.vertices]
        triangles = [tuple(face.vertices) for face in mesh.data.loop_triangles]
        axis = (hinge_end - hinge_start).normalized()
        collisions = []
        opened_vertices = None
        for degrees in range(131):
            turn = Quaternion(axis, math.radians(angle_degrees * degrees / 130))
            moved = [hinge_start + turn @ (point - hinge_start) for point in vertices]
            tree = BVHTree.FromPolygons(moved, triangles, all_triangles=True, epsilon=.00001)
            overlaps = tree.overlap(fixed_tree)
            if overlaps:
                collisions.append({'degrees': degrees, 'trianglePairs': len(overlaps)})
            if degrees == 130:
                opened_vertices = moved
        rows = len(vertices) // 4
        closed_free = sum(abs(vertices[2 * i].x) for i in range(rows)) / rows
        opened_free = sum(abs(opened_vertices[2 * i].x) for i in range(rows)) / rows
        return collisions, round(closed_free, 4), round(opened_free, 4), vertices, opened_vertices

    report = {'angleDegrees': 130, 'sampleDegrees': list(range(131)),
              'fixedHullTopologyEdited': False, 'leaves': {}}
    for bank, details in source.items():
        direction = int(details['direction'])
        hull = bpy.data.objects[details['hull']]
        before_topology = (len(hull.data.vertices), len(hull.data.polygons))
        fixed_tree = hull_bvh(hull)
        for side, side_sign in (('Port', -1), ('Starboard', 1)):
            joint = bpy.data.objects[f'Hatch_{bank}_Aft_{side}']
            mesh = bpy.data.objects[f'Hatch_{bank}_Aft_{side}_GapFiller']
            if mesh.parent != joint:
                raise RuntimeError(f'Expected existing aft leaf below {joint.name}')
            mesh.data.calc_loop_triangles()
            vertex_count = len(mesh.data.vertices)
            if vertex_count % 4:
                raise RuntimeError(f'Unexpected aft-leaf topology: {mesh.name}')
            half = vertex_count // 2
            rows = half // 2
            if rows < 10:
                raise RuntimeError(f'Aft leaf lacks the measured source strip: {mesh.name}')
            old_transform = asset_inverse @ mesh.matrix_world
            old_vertices = [old_transform @ vert.co for vert in mesh.data.vertices]
            y_first = old_vertices[0].y
            y_last = old_vertices[2 * (rows - 1)].y
            if y_last <= y_first:
                raise RuntimeError(f'Unexpected aft-leaf row order: {mesh.name}')

            x_first, x_last = (side_sign * n for n in exterior_x[bank])
            heights = []
            for i in range(rows):
                fraction = i / (rows - 1)
                x = x_first + (x_last - x_first) * fraction
                y = y_first + (y_last - y_first) * fraction
                heights.append(surface_height(hull, x, y, direction))
            start_z, end_z = heights[0], heights[-1]
            straight = [start_z + (end_z - start_z) * i / (rows - 1) for i in range(rows)]
            rise = max(0.0, max(direction * (height - line) for height, line in zip(heights, straight)))
            rise += clearance_cm
            start = Vector((x_first, y_first, start_z + direction * rise))
            end = Vector((x_last, y_last, end_z + direction * rise))
            shoulder_gaps = [direction * ((start.z + (end.z - start.z) * i / (rows - 1)) - height)
                             for i, height in enumerate(heights)]

            # The original 81-row leaf is a two-edge, two-sided manifold.
            # Preserve its upper/shroud edge, ribs/materials/UVs and face layout.
            # Move the lower edge onto the new hull-supported hinge line; its
            # underside follows at the original 0.12 cm thickness.
            local_inverse = old_transform.inverted()
            for row in range(rows):
                fraction = row / (rows - 1)
                hinge_point = start.lerp(end, fraction)
                mesh.data.vertices[2 * row + 1].co = local_inverse @ hinge_point
                mesh.data.vertices[2 * row + 1 + half].co = local_inverse @ (
                    hinge_point + Vector((0, 0, -direction * thickness_cm)))
            mesh.data.update()
            bpy.context.view_layer.update()

            children = [(child, child.matrix_world.copy()) for child in joint.children]
            joint.location = (start + end) * .5
            bpy.context.view_layer.update()
            for child, world in children:
                child.matrix_world = world
            bpy.context.view_layer.update()
            axis = (end - start).normalized()
            joint['hingeAxis'] = list(axis)
            joint['hingeEdge'] = [list(start), list(end)]
            joint['openingAngleDegrees'] = side_sign * direction * 130
            joint['construction'] = 'fitted-outboard-hull-hinge-with-original-upper-free-edge'
            joint['sourceReference'] = 'Measured upper shroud seam; actual holo exterior shoulder sampled along the angled hinge'
            joint['hullClearanceCm'] = clearance_cm
            joint['minHingeHullGapCm'] = min(shoulder_gaps)
            joint['maxHingeHullGapCm'] = max(shoulder_gaps)
            joint['fixedHullFacesRemoved'] = 0
            for obsolete in ('guideExit', 'guidePocket', 'slideVector'):
                if obsolete in joint:
                    del joint[obsolete]

            collisions, closed_free, opened_free, closed_v, open_v = sample_leaf(
                mesh, start, end, int(joint['openingAngleDegrees']), fixed_tree)
            if opened_free <= closed_free + .5:
                raise RuntimeError(f'{joint.name} free edge failed to open outboard: '
                                   f'{closed_free:.2f} -> {opened_free:.2f} cm')
            if collisions:
                raise RuntimeError(f'{joint.name} intersects {hull.name}: {collisions[:10]}')
            report['leaves'][joint.name] = {
                'fixedHull': hull.name,
                'hingeEdge': [list(start), list(end)],
                'hingeAxis': list(axis),
                'openingAngleDegrees': int(joint['openingAngleDegrees']),
                'minHingeHullGapCm': round(min(shoulder_gaps), 4),
                'maxHingeHullGapCm': round(max(shoulder_gaps), 4),
                'closedFreeEdgeMeanAbsX': closed_free,
                'openFreeEdgeMeanAbsX': opened_free,
                'hullCollisionAngles': [],
                'closedBounds': [
                    [round(min(v[k] for v in closed_v), 3) for k in range(3)],
                    [round(max(v[k] for v in closed_v), 3) for k in range(3)],
                ],
                'openBounds': [
                    [round(min(v[k] for v in open_v), 3) for k in range(3)],
                    [round(max(v[k] for v in open_v), 3) for k in range(3)],
                ],
            }
            print('FITTED_AFT', joint.name, 'free absX', closed_free, '->', opened_free,
                  '130-degree hull hits', len(collisions), flush=True)
        assert before_topology == (len(hull.data.vertices), len(hull.data.polygons))
    out = root_path / 'work/v08-review/aft-fit.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding='utf8')
    print('AFT_FIT_REPORT', out, flush=True)
    return report


fit_aft_hinges_v08()
