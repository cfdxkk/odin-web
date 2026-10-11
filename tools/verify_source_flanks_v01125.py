"""Read-only source polygon/UV and fixed-hull ownership check for v0.11.25.

Run with the saved v0.11.25 .blend. Face centres find candidates; actual
corner positions and per-corner UVs determine equality, within float error.
"""
import bpy, json, hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree

root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
inv = asset.matrix_world.inverted()
source_path = root.parent / 'Odin 建模/odin.blend'
with source_path.open('rb') as f:
    source_hash = hashlib.file_digest(f, 'sha256').hexdigest()
with bpy.data.libraries.load(str(source_path), link=False) as (src, dst):
    dst.objects = ['holo.001', 'holo.023']
owners = dict(zip(['holo.001', 'holo.023'], dst.objects))
for o in dst.objects:
    bpy.context.scene.collection.objects.link(o)
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()

catalog = {}
for name, o in owners.items():
    points = np.array([o.matrix_world @ v.co for v in o.data.vertices])
    kd = KDTree(len(o.data.polygons))
    faces = []
    uv = o.data.uv_layers.active
    for f in o.data.polygons:
        ps = points[list(f.vertices)]
        faces.append((ps, np.array([uv.data[i].uv for i in f.loop_indices]) if uv else None))
        kd.insert(Vector(ps.mean(0)), f.index)
    kd.balance()
    catalog[name] = (kd, faces)

def candidates(name, points):
    kd, faces = catalog[name]
    for _, i, _ in kd.find_range(Vector(points.mean(0)), .00012):
        ref, uv = faces[i]
        if len(ref) != len(points):
            continue
        distances = np.linalg.norm(points[:, None, :] - ref[None, :, :], axis=2)
        corners = distances.argmin(1)
        if len(set(corners)) == len(points) and distances[np.arange(len(points)), corners].max() < .00012:
            yield i, ref, uv, corners

moving_ids = {name: set() for name in catalog}
rows = []
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH'
          and o.name.startswith(('SideBattery_2_', 'SideBattery_4_'))
          and o.get('originalSourceArmor')]
assert len(meshes) == 36, len(meshes)
for o in meshes:
    owner = o['sourceObject']
    points = np.array([(inv @ o.matrix_world) @ v.co for v in o.data.vertices])
    uv = o.data.uv_layers.active
    max_error = max_uv_error = 0.
    matched = []
    for f in o.data.polygons:
        ps = points[list(f.vertices)]
        matches = list(candidates(owner, ps))
        assert matches, ('Changed source polygon', o.name, f.index)
        chosen = None
        for i, ref, ref_uv, corners in matches:
            current_uv = np.array([uv.data[k].uv for k in f.loop_indices]) if uv else None
            err = 0. if current_uv is None and ref_uv is None else float(np.max(abs(current_uv-ref_uv[corners])))
            if err < .000001:
                chosen = (i, ref, corners, err)
                break
        assert chosen, ('Changed source UV', o.name, f.index)
        i, ref, corners, err = chosen
        matched.append(i)
        max_error = max(max_error, float(np.max(np.linalg.norm(ps-ref[corners], axis=1))))
        max_uv_error = max(max_uv_error, err)
    assert not (moving_ids[owner] & set(matched)), ('Duplicate moving source faces', o.name)
    moving_ids[owner].update(matched)
    rows.append({'mesh': o.name, 'sourceObject': owner, 'polygons': len(matched),
                 'maxCornerError': max_error, 'maxUvError': max_uv_error})

duplicates = []
fixed_counts = {}
fixed_ids = {name: set() for name in catalog}
for name in ['holo.001', 'Flank24_OriginalFixedHull', 'holo.023']:
    o = bpy.data.objects[name]
    points = np.array([(inv @ o.matrix_world) @ v.co for v in o.data.vertices])
    count = 0
    for f in o.data.polygons:
        ps = points[list(f.vertices)]
        for owner in catalog:
            for i, *_ in candidates(owner, ps):
                fixed_ids[owner].add(i)
                if i in moving_ids[owner]:
                    duplicates.append({'fixedMesh': name, 'polygon': f.index, 'sourceObject': owner, 'sourcePolygon': i})
                    count += 1
    fixed_counts[name] = count
assert not duplicates, ('Moving source faces left on fixed hull', duplicates[:12], len(duplicates))

# Check whole source islands in the four local mount regions, including the
# trough, cheek braces and front transverse supports that must remain fixed.
source = owners['holo.001']
points = np.array([source.matrix_world @ v.co for v in source.data.vertices])
parents = list(range(len(points)))
def find(i):
    while parents[i] != i:
        parents[i] = parents[parents[i]]
        i = parents[i]
    return i
for edge in source.data.edges:
    a, b = edge.vertices
    parents[find(a)] = find(b)
groups = {}
for v in source.data.vertices:
    groups.setdefault(find(v.index), []).append(v.index)
faces = {}
for f in source.data.polygons:
    faces.setdefault(find(f.vertices[0]), []).append(f.index)
frames = json.loads((root / 'docs/review/v0.10.0/source-covers.json').read_text(encoding='utf8'))
fixed_regions = {}
for name in [f'SideBattery_{number}_{side}' for number in [2, 4] for side in ['Starboard', 'Port']]:
    frame = frames[name]
    local = (points-np.array(frame['frameOrigin'])) @ np.array(frame['frameAxes'])
    expected = set()
    for gid, indices in groups.items():
        ps = local[indices]
        lo, hi = ps.min(0), ps.max(0)
        if max(abs(ps[:, 0])) <= 6.3 and lo[1] >= -43 and hi[1] <= 33 and lo[2] >= -8 and hi[2] <= 8:
            expected.update(faces.get(gid, []))
    expected -= moving_ids['holo.001']
    missing = expected - fixed_ids['holo.001']
    assert not missing, ('Missing fixed source structure', name, sorted(missing)[:12], len(missing))
    fixed_regions[name] = len(expected)
external_fixed = set(range(len(owners['holo.023'].data.polygons))) - moving_ids['holo.023']
missing_external = external_fixed - fixed_ids['holo.023']
if missing_external:
    missing_points = np.concatenate([catalog['holo.023'][1][i][0] for i in missing_external])
    print('MISSING_BEARING', len(missing_external), missing_points.min(0), missing_points.max(0), sorted(missing_external)[:16], flush=True)
assert external_fixed <= fixed_ids['holo.023'], 'Left 4 lower bearing changed'
with source_path.open('rb') as f:
    assert hashlib.file_digest(f, 'sha256').hexdigest() == source_hash
report = {'version': '0.11.25', 'sourceSha256': source_hash,
          'meshes': rows, 'originalMovingPolygons': sum(r['polygons'] for r in rows),
          'duplicateMovingFacesOnFixedHull': fixed_counts, 'fixedSourcePolygonsByMount': fixed_regions,
          'left4FixedBearingPolygons': len(external_fixed), 'originalUnchanged': True}
(root / 'docs/review/v0.11.25/source-geometry.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('SOURCE_GEOMETRY', len(rows), report['originalMovingPolygons'], fixed_counts, flush=True)
