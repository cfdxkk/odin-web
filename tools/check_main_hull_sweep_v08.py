"""Audit all ten moving main-bay leaves against the unmodified fixed hull.

Usage, after regenerating the 101 runtime poses with review_rig_poses.mjs:
  blender -b assets/blender/odin_articulated_v0.8.0.blend \
    --python tools/check_main_hull_sweep_v08.py -- 0.8.0

For v0.8.1, open that version's Blend and append ``-- 0.8.1`` instead.
The versioned report is then work/v081-review/hull-sweep.json.

The report is work/v08-review/hull-sweep.json. This script never edits meshes,
keyframes, the source .blend, or the website. Coordinates are centimeters in
Odin_Asset local space (X starboard, Y bow, Z up).
"""
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri


ROOT = Path(__file__).resolve().parents[1]
arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
VERSION = arguments[0] if arguments else '0.8.0'
if len(arguments) > 1 or not re.fullmatch(r'\d+\.\d+\.\d+', VERSION):
    raise RuntimeError('Usage: blender -b <versioned.blend> --python tools/check_main_hull_sweep_v08.py -- 0.8.1')
REVIEW_DIR = 'v08-review' if VERSION == '0.8.0' else f'v{VERSION.replace(".", "")}-review'
BLEND = (ROOT / f'assets/blender/odin_articulated_v{VERSION}.blend').resolve()
POSES_PATH = ROOT / 'work/rig-review/clearance-poses.json'
OUT_PATH = ROOT / 'work' / REVIEW_DIR / 'hull-sweep.json'
GLB_PATH = ROOT / 'public/models/odin.glb'
RIG_PATH = ROOT / 'app/lib/odin-rig.ts'
MANIFEST_PATH = ROOT / 'public/models/asset-manifest.json'
HULLS = {'Dorsal': 'holo.001', 'Ventral': 'holo.013'}
ROLES = ('Port', 'Starboard', 'Nose', 'Aft_Port', 'Aft_Starboard')

if Path(bpy.data.filepath).resolve() != BLEND:
    raise RuntimeError(f'Open the v{VERSION} editable source first: {BLEND}')
if not POSES_PATH.is_file():
    raise RuntimeError(f'Generate 101 current runtime poses first: {POSES_PATH}')
manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf8'))
if manifest.get('version') != VERSION:
    raise RuntimeError(f'Expected exported v{VERSION} asset, found {manifest.get("version")}')
if POSES_PATH.stat().st_mtime_ns < max(GLB_PATH.stat().st_mtime_ns, RIG_PATH.stat().st_mtime_ns):
    raise RuntimeError('The 101 runtime poses predate the current GLB or rig; rerun node tools/review_rig_poses.mjs')
poses = json.loads(POSES_PATH.read_text(encoding='utf8'))
if len(poses) != 101 or any(abs(p['deployment'] - i / 100) > 1e-7 for i, p in enumerate(poses)):
    raise RuntimeError('Expected the 101 deployment samples d=0.00 through 1.00 at 0.01 steps')
asset = bpy.data.objects['Odin_Asset']
asset_inverse = asset.matrix_world.inverted()
basis = Quaternion((1, 0, 0), -math.pi / 2)


def ancestry_contains(obj, parent_name):
    parent = obj.parent
    while parent:
        if parent.name == parent_name:
            return True
        parent = parent.parent
    return False


def mesh_data(obj):
    obj.data.calc_loop_triangles()
    return {
        'object': obj,
        'vertices': [v.co.copy() for v in obj.data.vertices],
        'triangles': [tuple(t.vertices) for t in obj.data.loop_triangles],
    }


def build_bvh(meshes):
    vertices, triangles, face_names = [], [], []
    for mesh in meshes:
        obj = mesh['object']
        transform = asset_inverse @ obj.matrix_world
        offset = len(vertices)
        vertices.extend(transform @ point for point in mesh['vertices'])
        triangles.extend(tuple(index + offset for index in face) for face in mesh['triangles'])
        face_names.extend([obj.name] * len(mesh['triangles']))
    if not triangles:
        raise RuntimeError('Cannot build a BVH from an empty mesh group')
    tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=.00001)
    return tree, face_names, vertices, triangles


def intersection_bounds(moving_vertices, moving_faces, hull_vertices, hull_faces, pairs):
    """Return actual triangle-edge witnesses, with an explicit conservative fallback."""
    contact_points = []
    for moving_i, hull_i in pairs:
        moving = [moving_vertices[i] for i in moving_faces[moving_i]]
        hull = [hull_vertices[i] for i in hull_faces[hull_i]]
        for edge_tri, target_tri in ((moving, hull), (hull, moving)):
            for start, end in zip(edge_tri, edge_tri[1:] + edge_tri[:1]):
                direction = end - start
                length = direction.length
                if length < 1e-8:
                    continue
                # Test both windings: a contact may be seen from either side.
                for tri in (target_tri, target_tri[::-1]):
                    point = intersect_ray_tri(*tri, direction / length, start, True)
                    if point is not None and (point - start).length <= length + 1e-6:
                        contact_points.append(point)
                        break
    method = 'triangle-edge intersection'
    if not contact_points:
        # Coplanar/tangent BVH contacts can have no ray witness. Keep a bounded,
        # clearly identified envelope instead of reporting an invented point.
        indices_m = {i for a, _ in pairs for i in moving_faces[a]}
        indices_h = {i for _, b in pairs for i in hull_faces[b]}
        contact_points = [moving_vertices[i] for i in indices_m] + [hull_vertices[i] for i in indices_h]
        method = 'overlapping-triangle envelope'
    bounds = [
        [round(min(point[axis] for point in contact_points), 4) for axis in range(3)],
        [round(max(point[axis] for point in contact_points), 4) for axis in range(3)],
    ]
    return bounds, method


fixed = {}
moving = {}
for bank, hull_name in HULLS.items():
    hull = bpy.data.objects[hull_name]
    if hull.type != 'MESH':
        raise RuntimeError(f'Fixed hull {hull_name} is not a mesh')
    fixed[bank] = build_bvh([mesh_data(hull)])
    for role in ROLES:
        joint_name = f'Hatch_{bank}_{role}'
        if joint_name not in bpy.data.objects:
            raise RuntimeError(f'Missing hatch joint: {joint_name}')
        members = [mesh_data(obj) for obj in bpy.context.scene.objects
                   if obj.type == 'MESH' and ancestry_contains(obj, joint_name)]
        if not members:
            raise RuntimeError(f'No mesh descendants for {joint_name}')
        moving[(bank, role)] = members

hits = []
summary = {f'{bank}/{role}': {
    'movingJoint': f'Hatch_{bank}_{role}',
    'fixedHull': HULLS[bank],
    'hitSamples': 0,
    'firstDeployment': None,
    'lastDeployment': None,
    'peakTrianglePairs': 0,
} for bank, role in moving}
for sample_index, pose in enumerate(poses):
    for joint in pose['joints']:
        obj = bpy.data.objects.get(joint['name'])
        if obj is None:
            raise RuntimeError(f'Blender source is missing runtime joint {joint["name"]}')
        x, y, z = joint['position']
        obj.location = (x, -z, y)
        q = joint['quaternion']
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = basis.inverted() @ Quaternion((q[3], q[0], q[1], q[2])) @ basis
    bpy.context.view_layer.update()
    for (bank, role), members in moving.items():
        moving_tree, names, mv, mf = build_bvh(members)
        hull_tree, _, hv, hf = fixed[bank]
        pairs = moving_tree.overlap(hull_tree)
        if not pairs:
            continue
        by_object = defaultdict(list)
        for moving_face, hull_face in pairs:
            by_object[names[moving_face]].append((moving_face, hull_face))
        part_hits = []
        for object_name, object_pairs in sorted(by_object.items()):
            bounds, method = intersection_bounds(mv, mf, hv, hf, object_pairs)
            part_hits.append({
                'movingObject': object_name,
                'trianglePairs': len(object_pairs),
                'intersectionBounds': bounds,
                'boundsMethod': method,
            })
        key = f'{bank}/{role}'
        entry = summary[key]
        if entry['firstDeployment'] is None:
            entry['firstDeployment'] = pose['deployment']
        entry['hitSamples'] += 1
        entry['lastDeployment'] = pose['deployment']
        entry['peakTrianglePairs'] = max(entry['peakTrianglePairs'], len(pairs))
        lower = [min(part['intersectionBounds'][0][axis] for part in part_hits) for axis in range(3)]
        upper = [max(part['intersectionBounds'][1][axis] for part in part_hits) for axis in range(3)]
        hits.append({
            'sample': sample_index,
            'deployment': pose['deployment'],
            'movingJoint': f'Hatch_{bank}_{role}',
            'fixedHull': HULLS[bank],
            'trianglePairs': len(pairs),
            'intersectionBounds': [lower, upper],
            'parts': part_hits,
        })
    if sample_index % 20 == 0:
        print(f'HULL_SWEEP {sample_index:03d}/100', flush=True)

report = {
    'assetVersion': VERSION,
    'sourceBlend': BLEND.name,
    'sourceBlendSha256': hashlib.sha256(BLEND.read_bytes()).hexdigest(),
    'rigSha256': hashlib.sha256(RIG_PATH.read_bytes()).hexdigest(),
    'glbSha256': hashlib.sha256(GLB_PATH.read_bytes()).hexdigest(),
    'posesSha256': hashlib.sha256(POSES_PATH.read_bytes()).hexdigest(),
    'coordinateSpace': 'Odin_Asset source-model coordinates; X starboard, Y bow, Z up',
    'samples': len(poses),
    'testedLeavesPerSample': len(moving),
    'fixedHulls': HULLS,
    'hitSamples': len({entry['sample'] for entry in hits}),
    'hitEvents': len(hits),
    'intermediateHitEvents': sum(0 < entry['deployment'] < 1 for entry in hits),
    'summary': summary,
    'hits': hits,
}
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
print(json.dumps({key: report[key] for key in ('samples', 'testedLeavesPerSample', 'hitSamples', 'hitEvents', 'intermediateHitEvents', 'summary')}, indent=2), flush=True)
print(f'Hull sweep report: {OUT_PATH}', flush=True)
if hits:
    raise RuntimeError('Moving armor intersects the fixed hull; inspect hull-sweep.json')
