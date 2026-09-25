"""v0.8.3: explicit inner armor finish and static bore-to-guide identity.

Load the versioned v0.8.2 copy. This changes face materials and metadata only;
all vertices, topology, UVs, rest transforms and source exterior faces remain.
Animation is supplied exclusively by the Nuxt rig, never this Blender file.
"""
import bpy
import hashlib
import json
import sys
from array import array
from collections import Counter, defaultdict
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'assets/blender/odin_articulated_v0.8.2.blend'
if Path(bpy.data.filepath).resolve() != BASELINE.resolve():
    raise RuntimeError('Load the saved v0.8.2 baseline; never modify original odin.blend')
asset = bpy.data.objects['Odin_Asset']
inverse = asset.matrix_world.inverted()
red = bpy.data.materials['Odin_Turret_Interior_DeepRed']
report = {'revision': '0.8.3', 'baseline': BASELINE.name,
          'geometryUVRestTransformsUnchanged': False, 'meshes': {}, 'carrierGuides': {}}


def signature(obj):
    digest = hashlib.sha256()
    digest.update(obj.type.encode())
    digest.update((obj.parent.name if obj.parent else '').encode())
    digest.update(array('f', (v for row in obj.matrix_world for v in row)).tobytes())
    if obj.type == 'MESH':
        mesh = obj.data
        for seq, prop, multiplier, code in [(mesh.vertices, 'co', 3, 'f'),
                                           (mesh.edges, 'vertices', 2, 'i'),
                                           (mesh.loops, 'vertex_index', 1, 'i'),
                                           (mesh.polygons, 'loop_start', 1, 'i'),
                                           (mesh.polygons, 'loop_total', 1, 'i')]:
            values = array(code, [0]) * (len(seq) * multiplier)
            seq.foreach_get(prop, values)
            digest.update(values.tobytes())
        for layer in mesh.uv_layers:
            values = array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(layer.name.encode()); digest.update(values.tobytes())
    return digest.hexdigest()


before = {o.name: signature(o) for o in bpy.context.scene.objects}


def islands(mesh):
    parents = list(range(len(mesh.vertices)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]; i = parents[i]
        return i
    for edge in mesh.edges:
        a, b = edge.vertices; parents[find(a)] = find(b)
    groups = defaultdict(list)
    for face in mesh.polygons:
        groups[find(face.vertices[0])].append(face.index)
    return sorted(groups.values(), key=len, reverse=True)


def finish_inside(obj, bank, is_housing=False):
    mesh = obj.data
    if red not in list(mesh.materials): mesh.materials.append(red)
    red_index = list(mesh.materials).index(red)
    old = [p.material_index for p in mesh.polygons]
    matrix = inverse @ obj.matrix_world
    normal_matrix = matrix.to_3x3().inverted().transposed()
    points = [matrix @ v.co for v in mesh.vertices]
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    tree = BVHTree.FromPolygons(points, polygons, all_triangles=False)
    direction = 1 if bank == 'Dorsal' else -1
    groups = islands(mesh)
    shell_ids = set(groups[0]) if is_housing else set(range(len(polygons)))
    shell_vertices = {i for f in shell_ids for i in polygons[f]}
    shell_points = [points[i] for i in shell_vertices]
    center_x = (min(p.x for p in shell_points)+max(p.x for p in shell_points))*.5
    rear, front = min(p.y for p in shell_points), max(p.y for p in shell_points)
    inside_z = direction * (min(direction*p.z for p in shell_points) - 1.0)
    if is_housing:
        # The armored housing is an open-bottom shell above the circular race.
        # Probe its cavity, rather than colouring the visible outward shell.
        inside_z = direction * (min(direction*p.z for p in shell_points) + .3)
    reasons = Counter()
    changed = []
    for face in mesh.polygons:
        if face.material_index == red_index or face.index not in shell_ids: continue
        normal = (normal_matrix @ face.normal).normalized()
        # Roof and upward-facing exterior bevels retain their existing finish.
        if direction * normal.z > .18: continue
        center = matrix @ face.center
        y = min(front-.5, max(rear+.5, center.y))
        anchors = [Vector((center_x, y, inside_z))]
        if is_housing:
            anchors += [Vector((center_x+x, y+offset, inside_z))
                        for x in (-5, 0, 5) for offset in (-4, 4)]
        else:
            anchors += [Vector((center_x+x, y+offset, inside_z))
                        for x in (-1, 1) for offset in (-2, 2)]
        for anchor in anchors:
            vector = center-anchor
            if vector.length < 1e-6 or normal.dot(-vector.normalized()) < .08: continue
            location, hit_normal, index, distance = tree.ray_cast(anchor, vector.normalized(), vector.length+.02)
            if index == face.index and location is not None and abs(distance-vector.length)<.015:
                face.material_index = red_index
                reasons['visible_inward_cavity_face'] += 1
                changed.append(face.index)
                break
    if is_housing:
        # The second-largest connected source island is the recessed circular
        # bearing drum, not the exterior armored housing. Its full cylindrical
        # wall must be red; a Z-normal-only selector leaves it patchwork grey.
        drum = groups[1]
        vertices = {i for f in drum for i in polygons[f]}
        extent = [max(points[i][a] for i in vertices)-min(points[i][a] for i in vertices) for a in range(3)]
        assert len(drum) == 5158 and 18 < extent[0] < 21 and 18 < extent[1] < 21
        for index in drum:
            face = mesh.polygons[index]
            if face.material_index != red_index:
                face.material_index = red_index; changed.append(index)
                reasons['recessed_circular_bearing_drum'] += 1
    changed_set = set(changed)
    preserved = [i for i, mat in enumerate(old) if i not in changed_set]
    assert all(mesh.polygons[i].material_index == old[i] for i in preserved)
    assert all(direction*(normal_matrix @ mesh.polygons[i].normal).normalized().z <= .18+1e-6
               for i in changed if i in shell_ids)
    report['meshes'][obj.name] = {
        'parent': obj.parent.name, 'addedRedFaces': len(changed), 'reasons': dict(reasons),
        'changedFaceIndices': sorted(changed), 'unchangedFaceCount': len(preserved),
        'before': dict(Counter(mesh.materials[i].name for i in old)),
        'after': dict(Counter(mesh.materials[p.material_index].name for p in mesh.polygons)),
        'exteriorRoofAndBevelsUnchanged': True,
    }


for bank, names in [('Dorsal', ['odin.005','odin.006','odin.007','odin.008']),
                    ('Ventral', ['odin.013','odin.014','odin.015','odin.016'])]:
    for index, name in enumerate(names): finish_inside(bpy.data.objects[name], bank, index == 0)
    for role in ('Port', 'Center', 'Starboard'):
        guide_role = role if bank == 'Dorsal' or role == 'Center' else ('Starboard' if role == 'Port' else 'Port')
        carrier = bpy.data.objects[f'Main_{bank}_Carrier_{role}']
        guide = f'Main_{bank}_Shroud_{guide_role}'
        carrier['followShroud'] = guide
        carrier['motionBasis'] = 'Rigid relative to physical shroud; extra outer-pair final nesting; independent common axial telescope'
        report['carrierGuides'][carrier.name] = guide
        # The coupled cover stroke carries the ventral tips closer to the
        # fixed lip. All six bores share the measured safe axial stow length.
        bpy.data.objects[f'Main_{bank}_Tube_{role}']['stowTravel'] = 20.0

report['commonAxialStowTravel'] = 20.0

# Interior faces are real, oriented polygons. Do not tint the outer armor with
# a double-sided overlay, duplicate faces, or emissive light.
red.use_backface_culling = True
report['interiorMaterial'] = {'name': red.name, 'baseColorLinear': list(red.diffuse_color),
                              'singleSided': True, 'newGeometry': False}
report['approvedExternalArmorPreserved'] = {
    o.name: dict(Counter(o.data.materials[p.material_index].name for p in o.data.polygons))
    for o in bpy.context.scene.objects
    if o.type == 'MESH' and o.name.startswith('Hatch_') and '_Rib_' not in o.name
}
after = {o.name: signature(o) for o in bpy.context.scene.objects}
assert before == after, 'Material-only revision changed geometry, UVs, parenting, or rest transforms'
report['geometryUVRestTransformsUnchanged'] = True
report['objectCount'] = len(before)
report['geometryAuditSha256'] = hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()
for obj in bpy.context.scene.objects: obj.animation_data_clear()
for action in list(bpy.data.actions): bpy.data.actions.remove(action)
asset['version'] = '0.8.3'
bpy.context.scene.name = 'ODIN v0.8.3 - synchronized gun guides and deep-red armor interiors'
candidate = '--candidate' in sys.argv
output = ROOT / ('work/v083-review/material-candidate.blend' if candidate else 'assets/blender/odin_articulated_v0.8.3.blend')
output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
report['output'] = str(output.relative_to(ROOT))
report['blendSha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
report_path = ROOT / 'work/v083-review/interior-materials.json'
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
print(json.dumps({name: {k: v for k, v in data.items() if k not in ('changedFaceIndices', 'before', 'after')}
                  for name, data in report['meshes'].items()}, indent=2), flush=True)
print('SAVED', output, flush=True)
