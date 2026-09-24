"""Audit the actual runtime main-bore poses, including clearance to their covers.

Usage after review_rig_poses.mjs:
  blender -b assets/blender/odin_articulated_v0.8.2.blend --python-exit-code 1 \
    --python tools/check_bore_clearance.py -- 0.8.2 \
    --baseline-report docs/review/v0.8.2/baseline/v0.8.1-bore-clearance.json \
    --baseline-poses docs/review/v0.8.2/baseline/v0.8.1-clearance-poses.json

The entire telescoping tube is checked. Original rear breech attachment faces
behind source Y=107 (dorsal) / 57 (ventral) are recorded separately, because
those source attachments intentionally intersect the housing. Front collar
faces, including any face crossing that boundary, remain in the audit. Their
contacts behind the unchanged housing mouth are explicitly reported as nested
mount interfaces. Fixed hull and new top-cover contacts remain strict failures.
No mesh or source file is modified. This is a triangle-intersection check;
positive clearance measurements are sampled vertex-to-triangle distances.
"""
import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('version')
parser.add_argument('--poses', type=Path, default=ROOT / 'work/rig-review/clearance-poses.json')
parser.add_argument('--output', type=Path, help='Optional diagnostic report location')
parser.add_argument('--baseline-report', type=Path, help='Earlier version report for explicit attachment/contact comparisons')
parser.add_argument('--baseline-poses', type=Path, help='Earlier actual JS poses; required to establish unchanged guide contacts')
parser.add_argument('--diagnostic', action='store_true', help='Allow a temporary candidate and keep reports even on collisions')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
VERSION = args.version
BLEND = Path(bpy.data.filepath).resolve()
OUT = ROOT / 'work' / f'v{VERSION.replace(".", "")}-review' / 'bore-clearance.json'
if args.output:
    OUT = args.output.resolve()
POSES = args.poses.resolve()
GLB = ROOT / 'public/models/odin.glb'
RIG = ROOT / 'app/lib/odin-rig.ts'
if not args.diagnostic:
    expected = (ROOT / f'assets/blender/odin_articulated_v{VERSION}.blend').resolve()
    if BLEND != expected:
        raise RuntimeError(f'Open {expected} before the final audit')
    manifest = json.loads((ROOT / 'public/models/asset-manifest.json').read_text(encoding='utf8'))
    if manifest['version'] != VERSION:
        raise RuntimeError('Export the matching version before the audit')
    if POSES.stat().st_mtime_ns < max(GLB.stat().st_mtime_ns, RIG.stat().st_mtime_ns):
        raise RuntimeError('Regenerate actual JS poses after the latest GLB/rig change')
poses = json.loads(POSES.read_text(encoding='utf8'))
if len(poses) != 101 or any(abs(p['deployment'] - i / 100) > 1e-7 for i, p in enumerate(poses)):
    raise RuntimeError('Expected 101 poses at deployment 0.00 through 1.00')
asset = bpy.data.objects['Odin_Asset']
inverse = asset.matrix_world.inverted()
basis = Quaternion((1, 0, 0), -math.pi / 2)
banks = {'Dorsal': {'source': 'odin.004', 'housing': 'odin.005', 'shrouds': ['odin.006', 'odin.007', 'odin.008'], 'hull': 'holo.001', 'rear': 107},
         'Ventral': {'source': 'odin.012', 'housing': 'odin.013', 'shrouds': ['odin.014', 'odin.015', 'odin.016'], 'hull': 'holo.013', 'rear': 57}}
roles = ('Port', 'Center', 'Starboard')


def descendants(obj, name):
    p = obj.parent
    while p:
        if p.name == name:
            return True
        p = p.parent
    return False


def data(obj, selector=None):
    obj.data.calc_loop_triangles()
    vertices = [v.co.copy() for v in obj.data.vertices]
    rest = [inverse @ obj.matrix_world @ v for v in vertices]
    faces = [tuple(t.vertices) for t in obj.data.loop_triangles]
    if selector:
        faces = [face for face in faces if selector([rest[i] for i in face])]
    return {'object': obj, 'vertices': vertices, 'faces': faces}


def tree(meshes):
    vertices, faces, names = [], [], []
    for mesh in meshes:
        obj = mesh['object']
        matrix = inverse @ obj.matrix_world
        start = len(vertices)
        vertices.extend(matrix @ v for v in mesh['vertices'])
        faces.extend(tuple(i + start for i in f) for f in mesh['faces'])
        names.extend([obj.name] * len(mesh['faces']))
    return (BVHTree.FromPolygons(vertices, faces, all_triangles=True, epsilon=.00001), vertices, faces, names)


def witnesses(a, b, pairs):
    points = []
    for ai, bi in pairs:
        av = [a[1][i] for i in a[2][ai]]
        bv = [b[1][i] for i in b[2][bi]]
        for edges, target in ((av, bv), (bv, av)):
            for p, q in zip(edges, edges[1:] + edges[:1]):
                direction = q - p
                if direction.length < 1e-8:
                    continue
                for triangle in (target, target[::-1]):
                    hit = intersect_ray_tri(*triangle, direction.normalized(), p, True)
                    if hit is not None and (hit - p).length <= direction.length + 1e-6:
                        points.append(hit)
                        break
    if not points:
        points = [a[1][i] for ai, _ in pairs for i in a[2][ai]]
        method = 'overlapping triangle envelope (coplanar or tangent contact)'
    else:
        method = 'triangle-edge intersection'
    return [[round(min(p[k] for p in points), 5) for k in range(3)],
            [round(max(p[k] for p in points), 5) for k in range(3)]], method


def contacts(a, b):
    grouped = defaultdict(list)
    for i, j in a[0].overlap(b[0]):
        grouped[(a[3][i], b[3][j])].append((i, j))
    result = []
    for (moving, target), pairs in sorted(grouped.items()):
        bounds, method = witnesses(a, b, pairs)
        result.append({'moving': moving, 'target': target, 'trianglePairs': len(pairs),
                       'intersectionBounds': bounds, 'boundsMethod': method})
    return result


def apply(pose):
    for joint in pose['joints']:
        obj = bpy.data.objects.get(joint['name'])
        if obj is None:
            raise RuntimeError(f'Missing static joint {joint["name"]}')
        x, y, z = joint['position']
        obj.location = (x, -z, y)
        q = joint['quaternion']
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = basis.inverted() @ Quaternion((q[3], q[0], q[1], q[2])) @ basis
    bpy.context.view_layer.update()


def minimum_gap(a, b):
    # Both directions cover vertices from the curved gun and planar cover.
    best = (float('inf'), None, None)
    for origin, destination, reverse in ((a, b, False), (b, a, True)):
        used = {i for f in origin[2] for i in f}
        for i in used:
            p = origin[1][i]
            q, _, _, distance = destination[0].find_nearest(p)
            if q is not None and distance < best[0]:
                best = (distance, q if reverse else p, p if reverse else q)
    return {'sampledSurfaceGap': round(best[0], 6), 'borePoint': list(best[1]), 'coverPoint': list(best[2]),
            'method': 'Bidirectional vertex-to-triangle nearest distance; upper bound on exact minimum'}


meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
groups, attachments, fixed, targets = {}, {}, {}, {}
selection = {}
for bank, config in banks.items():
    fixed[bank] = tree([data(bpy.data.objects[config['hull']])])
    targets[bank] = [data(bpy.data.objects[name]) for name in [config['housing']] + config['shrouds']]
    for role in roles:
        carrier_name = f'Main_{bank}_Carrier_{role}'
        members = [o for o in meshes if descendants(o, carrier_name)]
        if not members:
            # Baseline v0.8.1 has one residual object containing all three bores.
            members = [bpy.data.objects[f'Main_{bank}_TubeMesh_{role}']]
            source = bpy.data.objects[config['source']]
            def own(points, role=role):
                x = sum(p.x for p in points) / len(points)
                return (x < -3 if role == 'Port' else x > 3 if role == 'Starboard' else -3 <= x <= 3)
            residual = data(source, own)
        else:
            residual = None
        exposed, rear = [], []
        for obj in members:
            if 'TubeMesh_' in obj.name:
                exposed.append(data(obj))
            else:
                exposed.append(data(obj, lambda p, limit=config['rear']: max(v.y for v in p) >= limit))
                rear.append(data(obj, lambda p, limit=config['rear']: max(v.y for v in p) < limit))
        if residual:
            rest = [inverse @ residual['object'].matrix_world @ v for v in residual['vertices']]
            exposed.append({**residual, 'faces': [f for f in residual['faces'] if max(rest[i].y for i in f) >= config['rear']]})
            rear.append({**residual, 'faces': [f for f in residual['faces'] if max(rest[i].y for i in f) < config['rear']]})
        groups[(bank, role)] = exposed
        attachments[(bank, role)] = rear
        selection[f'{bank}/{role}'] = {'exposedTriangles': sum(len(m['faces']) for m in exposed),
                                      'enclosedAttachmentTriangles': sum(len(m['faces']) for m in rear),
                                      'rearAttachmentBoundarySourceY': config['rear']}

baseline_report = json.loads(args.baseline_report.read_text(encoding='utf8')) if args.baseline_report else None
baseline_poses = json.loads(args.baseline_poses.read_text(encoding='utf8')) if args.baseline_poses else None
if bool(baseline_report) != bool(baseline_poses):
    raise RuntimeError('Supply both --baseline-report and --baseline-poses to compare earlier contacts')
baseline_events = {}
if baseline_report:
    for event in baseline_report['hits']:
        for contact in event['contacts']:
            baseline_events[(event['sample'], event['bank'], event['role'], contact['target'])] = contact


def unchanged_center_guide(index, bank, contact):
    """Only forgive the exact old center-guide contact at an unchanged pose."""
    if not baseline_report or 'CarrierMesh_Center' not in contact['moving']:
        return False
    if contact['target'] != banks[bank]['shrouds'][1]:
        return False
    old = baseline_events.get((index, bank, 'Center', contact['target']))
    if not old or any(abs(a - b) > .002 for row_a, row_b in zip(old['intersectionBounds'], contact['intersectionBounds']) for a, b in zip(row_a, row_b)):
        return False
    old_joints = {joint['name']: joint for joint in baseline_poses[index]['joints']}
    current = {joint['name']: joint for joint in poses[index]['joints']}
    carrier = bpy.data.objects[f'Main_{bank}_Carrier_Center']
    # Preserve-world reparenting leaves float32 residuals around 2e-6 source
    # units; this tolerance is 1000 times smaller than the visible seal gap.
    if carrier.location.length > 1e-5 or carrier.rotation_quaternion.angle > 1e-5:
        return False
    for suffix in ('Mount', 'Barrels', 'Tube_Center', 'Shroud_Center'):
        name = f'Main_{bank}_{suffix}'
        if name not in old_joints or name not in current:
            return False
        for field in ('position', 'quaternion'):
            if max(abs(a - b) for a, b in zip(old_joints[name][field], current[name][field])) > 1e-5:
                return False
    return True


hits, enclosed_hits, external_hits, mount_contacts, old_guide_contacts, measures, summaries = [], [], [], [], [], {}, Counter()
for index, pose in enumerate(poses):
    apply(pose)
    for bank, config in banks.items():
        cover = tree(targets[bank])
        moving = {role: tree(groups[(bank, role)]) for role in roles}
        for role, bore in moving.items():
            found = contacts(bore, cover) + contacts(bore, fixed[bank])
            if found:
                hits.append({'sample': index, 'deployment': pose['deployment'], 'bank': bank, 'role': role, 'contacts': found})
                for hit in found:
                    summaries[f'{bank}/{role}: {hit["moving"]} x {hit["target"]}'] += 1
                    entry = {'sample': index, 'deployment': pose['deployment'], 'bank': bank, 'role': role, **hit}
                    if hit['target'] == config['housing']:
                        # The original model has no boolean sockets around its
                        # breeches. These intersections are behind the armored
                        # housing mouth, and were present in the source poses.
                        # Keep their complete bounds and timing differences in
                        # the report instead of claiming all geometry is clear.
                        front = max(v.y for mesh in targets[bank][:1] for v in
                                    (inverse @ mesh['object'].matrix_world @ p for p in mesh['vertices']))
                        if hit['intersectionBounds'][1][1] <= front + .001:
                            entry['housingFrontY'] = front
                            entry['baselineAtSamePose'] = bool(baseline_events.get((index, bank, role, hit['target'])))
                            entry['classification'] = 'Nested rear tube or original collar inside the unchanged housing mouth'
                            mount_contacts.append(entry)
                            continue
                    if unchanged_center_guide(index, bank, hit):
                        entry['classification'] = 'Original center guide contact; identical ancestor poses and intersection bounds'
                        old_guide_contacts.append(entry)
                    else:
                        external_hits.append(entry)
            # Keep actual original breech contact evidence at endpoint poses.
            if index in (0, 100) and any(m['faces'] for m in attachments[(bank, role)]):
                rear = tree(attachments[(bank, role)])
                old = contacts(rear, cover) + contacts(rear, fixed[bank])
                if old:
                    enclosed_hits.append({'deployment': pose['deployment'], 'bank': bank, 'role': role, 'contacts': old})
        for first, second in combinations(roles, 2):
            found = contacts(moving[first], moving[second])
            if found:
                hits.append({'sample': index, 'deployment': pose['deployment'], 'bank': bank, 'role': f'{first}/{second}', 'contacts': found})
                for hit in found:
                    summaries[f'{bank}/{first}/{second}: {hit["moving"]} x {hit["target"]}'] += 1
                    external_hits.append({'sample': index, 'deployment': pose['deployment'], 'bank': bank, 'role': f'{first}/{second}', **hit})
        if index in (0, 100):
            key = f'{bank}/' + ('stowed' if index == 0 else 'deployed')
            cap = tree([data(bpy.data.objects[config['shrouds'][1]])])
            measures[key] = {'centerCoverClearance': minimum_gap(moving['Center'], cap), 'carriages': {}}
            for role in roles:
                obj = bpy.data.objects.get(f'Main_{bank}_Carrier_{role}')
                tube = bpy.data.objects[f'Main_{bank}_TubeMesh_{role}']
                points = [inverse @ tube.matrix_world @ vertex.co for vertex in tube.data.vertices]
                measures[key]['carriages'][role] = {
                    'localOffset': list(obj.location) if obj else [0, 0, 0],
                    'tubeCentroid': list(sum(points, Vector()) / len(points)),
                    'tubeBounds': [[min(p[k] for p in points) for k in range(3)],
                                   [max(p[k] for p in points) for k in range(3)]],
                }
    if index % 20 == 0:
        print(f'BORE_CLEARANCE {index:03}/100', flush=True)

for bank in banks:
    stowed = measures[f'{bank}/stowed']['carriages']
    deployed = measures[f'{bank}/deployed']['carriages']
    measures[f'{bank}/stowDisplacements'] = {
        role: [round(a - b, 6) for a, b in zip(stowed[role]['tubeCentroid'], deployed[role]['tubeCentroid'])]
        for role in roles
    }
report = {'assetVersion': VERSION, 'sourceBlend': BLEND.name, 'sourceBlendSha256': hashlib.sha256(BLEND.read_bytes()).hexdigest(),
          'rigSha256': hashlib.sha256(RIG.read_bytes()).hexdigest(), 'glbSha256': hashlib.sha256(GLB.read_bytes()).hexdigest(),
          'posesSha256': hashlib.sha256(POSES.read_bytes()).hexdigest(), 'diagnostic': args.diagnostic,
          'coordinateSpace': 'Odin_Asset source coordinates: X starboard, Y bow, Z up',
          'samples': len(poses), 'selection': selection, 'measurements': measures,
          'hitSamples': len({hit['sample'] for hit in hits}), 'hitEvents': len(hits), 'summary': dict(summaries), 'hits': hits,
          'externalHitSamples': len({hit['sample'] for hit in external_hits}), 'externalHitEvents': len(external_hits), 'externalHits': external_hits,
          'mountInterfaceContactEvents': len(mount_contacts), 'mountInterfaceContacts': mount_contacts,
          'unchangedBaselineGuideContactEvents': len(old_guide_contacts), 'unchangedBaselineGuideContacts': old_guide_contacts,
          'baselineComparison': ({'sourceBlend': baseline_report['sourceBlend'], 'sourceBlendSha256': baseline_report['sourceBlendSha256'],
                                  'reportSha256': hashlib.sha256(args.baseline_report.read_bytes()).hexdigest(),
                                  'posesSha256': hashlib.sha256(args.baseline_poses.read_bytes()).hexdigest(),
                                  'sourceHitSamples': baseline_report['hitSamples'],
                                  'mountContactEventsAtSameBaselinePose': sum(c['baselineAtSamePose'] for c in mount_contacts),
                                  'mountContactEventsWithChangedTiming': sum(not c['baselineAtSamePose'] for c in mount_contacts)} if baseline_report else None),
          'enclosedAttachmentEndpointContacts': enclosed_hits,
          'limitations': ['Rear attachment faces are reported separately, not counted as exposed-bore clearance.',
                          'Nested rear tubes/collars behind the housing mouth retain the original model\'s overlapping mount surfaces; their bounds and changed timing are explicit and are not a global zero-intersection claim.',
                          'Fixed-hull, neighboring-bore and new shroud contacts fail the final audit. Original guide contacts require equal baseline poses and intersection bounds.',
                          'BVH triangle intersection does not measure fully contained closed solids or prove exact minimum distance.']}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
print(json.dumps({'samples': len(poses), 'externalHitEvents': len(external_hits), 'mountInterfaceContactEvents': len(mount_contacts), 'unchangedBaselineGuideContactEvents': len(old_guide_contacts), 'summary': dict(summaries), 'measurements': measures}, indent=2), flush=True)
print(f'Bore audit: {OUT}', flush=True)
if external_hits and not args.diagnostic:
    raise RuntimeError('Exposed main bore intersects a cover, hull, or neighboring bore; inspect bore-clearance.json')
