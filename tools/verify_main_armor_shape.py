"""Independently measure the actual dorsal armor ribs; never edit the asset.

Run in Blender, for example:
  blender -b --python-exit-code 1 --python verify_main_armor_shape.py -- \
    --blend assets/blender/odin_articulated_v0.8.7.blend --output report.json

Distances are in Odin_Asset coordinates (source model units). Exterior cap
faces are selected geometrically by positive asset-space normal Z, not by
vertex row numbers or a generator's report. The current ribs have un-beveled
caps; if this construction changes, review the surface-selection contract.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blend', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--max-plane-deviation', type=float, default=1e-4)
    p.add_argument('--max-edge-deviation', type=float, default=1e-4)
    p.add_argument('--max-normal-angle', type=float, default=.02)
    p.add_argument('--report-only', action='store_true', help='Write a failure report without raising, for negative controls.')
    return p


def plane(points):
    center = points.mean(axis=0)
    _, _, basis = np.linalg.svd(points-center, full_matrices=False)
    normal = basis[-1]
    if normal[2] < 0:
        normal = -normal
    residual = (points-center) @ normal
    return center, normal, basis[0], residual


def ordered_boundary(faces):
    counts = Counter()
    for indices in faces:
        for a, b in zip(indices, indices[1:]+indices[:1]):
            counts[tuple(sorted((a, b)))] += 1
    edges = [edge for edge, count in counts.items() if count == 1]
    graph = defaultdict(list)
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)
    if not graph or any(len(adjacent) != 2 for adjacent in graph.values()):
        raise ValueError('Exterior cap must have one simple boundary loop.')
    start = min(graph)
    loop = [start]
    previous = None
    current = start
    while True:
        nxt = next(n for n in graph[current] if n != previous)
        if nxt == start:
            break
        if nxt in loop:
            raise ValueError('Invalid exterior cap boundary.')
        loop.append(nxt)
        previous, current = current, nxt
    if len(loop) != len(edges):
        raise ValueError('Multiple exterior cap boundary loops.')
    return loop


def long_edges(points, loop, dominant_axis):
    # Split the real perimeter at transverse end edges. This also handles the
    # old tessellated/bent cap without assuming its vertex ordering or row count.
    count = len(loop)
    aligned = []
    for i, a in enumerate(loop):
        delta = points[loop[(i+1) % count]]-points[a]
        length = np.linalg.norm(delta)
        aligned.append(length > 1e-10 and abs(delta @ dominant_axis)/length > .65)
    if all(aligned) or not any(aligned):
        raise ValueError('Cannot distinguish long sides from transverse rib ends.')
    start = next(i for i, value in enumerate(aligned) if not value)
    runs = []
    run = []
    for step in range(1, count+1):
        i = (start+step) % count
        if aligned[i]:
            if not run:
                run = [loop[i]]
            run.append(loop[(i+1) % count])
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    if len(runs) != 2:
        raise ValueError(f'Expected two long boundary chains, found {len(runs)}.')
    result = []
    for ids in runs:
        ps = points[ids]
        delta = ps[-1]-ps[0]
        length = float(np.linalg.norm(delta))
        axis = delta/length
        # Endpoint chord measures a real straight edge, not merely an abstract
        # best-fit line that could hide bends at its ends.
        residual = np.linalg.norm(np.cross(ps-ps[0], axis), axis=1)
        result.append({'vertexIds': ids, 'chordLength': length,
                       'maxChordDeviation': float(residual.max()),
                       'rmsChordDeviation': float(np.sqrt(np.mean(residual**2)))})
    return result


def measure(obj, asset_inverse, args):
    matrix = asset_inverse @ obj.matrix_world
    points = np.asarray([tuple(matrix @ vertex.co) for vertex in obj.data.vertices], dtype=float)
    obj.data.calc_loop_triangles()
    triangles = []
    normals = []
    polygon_area_vectors = defaultdict(lambda: np.zeros(3))
    for triangle in obj.data.loop_triangles:
        ids = tuple(triangle.vertices)
        ps = points[list(ids)]
        vector = np.cross(ps[1]-ps[0], ps[2]-ps[0])
        length = np.linalg.norm(vector)
        if length <= 1e-12:
            continue
        triangles.append((triangle.polygon_index, ids))
        normals.append(vector/length)
        polygon_area_vectors[triangle.polygon_index] += vector
    top_ids = {index for index, vector in polygon_area_vectors.items()
               if vector[2]/np.linalg.norm(vector) > .1}
    if not top_ids:
        raise ValueError(f'{obj.name}: no outward-facing cap')
    faces = [list(obj.data.polygons[index].vertices) for index in sorted(top_ids)]
    vertices = sorted({v for face in faces for v in face})
    center, normal, axis, residual = plane(points[vertices])
    cap_normals = np.asarray([n for (triangle, n) in zip(triangles, normals)
                              if triangle[0] in top_ids])
    angles = np.degrees(np.arccos(np.clip(cap_normals @ normal, -1, 1)))
    perimeter = ordered_boundary(faces)
    edges = long_edges(points, perimeter, axis)
    plane_max = float(np.max(np.abs(residual)))
    edge_max = max(edge['maxChordDeviation'] for edge in edges)
    angle_max = float(angles.max())
    checks = {'plane': plane_max <= args.max_plane_deviation,
              'longEdges': edge_max <= args.max_edge_deviation,
              'triangleNormals': angle_max <= args.max_normal_angle}
    return {'name': obj.name, 'meshVertices': len(points), 'meshPolygons': len(obj.data.polygons),
            'capPolygonIds': sorted(top_ids), 'capVertexCount': len(vertices),
            'fittedPlanePoint': center.tolist(), 'fittedPlaneNormal': normal.tolist(),
            'maxPlaneDeviation': plane_max,
            'rmsPlaneDeviation': float(np.sqrt(np.mean(residual**2))),
            'maxTriangleNormalAngleDegrees': angle_max,
            'longEdges': edges, 'checks': checks, 'passed': all(checks.values())}


def main():
    args = parser().parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    source = args.blend.resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.view_layer.update()
    asset_inverse = bpy.data.objects['Odin_Asset'].matrix_world.inverted()
    expected = [f'Hatch_Dorsal_{side}_Rib_{i:02d}' for side in ('Port', 'Starboard') for i in range(14)]
    missing = [name for name in expected if name not in bpy.data.objects]
    results = []
    errors = []
    for name in expected:
        if name not in bpy.data.objects:
            continue
        try:
            results.append(measure(bpy.data.objects[name], asset_inverse, args))
        except Exception as error:
            errors.append({'name': name, 'error': str(error)})
    report = {'schema': 1, 'source': source.name, 'sourceSha256': digest,
              'measurementSpace': 'Odin_Asset source coordinates',
              'readOnly': True, 'expectedRibs': 28, 'measuredRibs': len(results),
              'method': 'Actual mesh SVD cap plane, actual triangulated face normals, and two true perimeter long-edge endpoint chords; no generator metadata.',
              'selection': 'Un-beveled outward cap polygons with normalized source-space normal Z > 0.1; one boundary loop and two long perimeter chains required.',
              'thresholds': {'maxPlaneDeviation': args.max_plane_deviation,
                             'maxEdgeDeviation': args.max_edge_deviation,
                             'maxTriangleNormalAngleDegrees': args.max_normal_angle},
              'missingObjects': missing, 'errors': errors, 'ribs': results}
    report['summary'] = {'maxPlaneDeviation': max((r['maxPlaneDeviation'] for r in results), default=None),
                         'maxLongEdgeDeviation': max((e['maxChordDeviation'] for r in results for e in r['longEdges']), default=None),
                         'maxTriangleNormalAngleDegrees': max((r['maxTriangleNormalAngleDegrees'] for r in results), default=None),
                         'failedRibs': [r['name'] for r in results if not r['passed']]}
    report['passed'] = not missing and not errors and len(results) == 28 and all(r['passed'] for r in results)
    report['sourceUnchanged'] = hashlib.sha256(source.read_bytes()).hexdigest() == digest
    report['passed'] = report['passed'] and report['sourceUnchanged']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'summary': report['summary'], 'output': str(args.output)}))
    if not report['passed'] and not args.report_only:
        raise RuntimeError('Main armor rib shape verification failed; see report.')


if __name__ == '__main__':
    main()
