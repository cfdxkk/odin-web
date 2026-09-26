"""Extend the bridge's existing cement-gray paint over its hull superstructure.

The three connected shell pieces are the fore fairing, middle bridge apron,
and long aft dorsal spine. They are separate from the main hull and mounted
equipment, so recoloring whole pieces gives a clean physical paint boundary.
"""

import bpy
import json
from collections import Counter, defaultdict
from pathlib import Path


root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert str(asset['version']) == '0.11.10'
hull = bpy.data.objects['holo.001']
mesh = hull.data
armor = bpy.data.materials['Odin_Bridge_Armor']
trim = bpy.data.materials['Odin_Bridge_Trim']
material_names = [material.name for material in mesh.materials]
assert armor.name in material_names and trim.name in material_names
armor_index = material_names.index(armor.name)
trim_index = material_names.index(trim.name)

# The original connected shell islands have stable vertex roots in v0.11.10.
# Assert their face counts to fail visibly if the editable source changes.
target_islands = {
    22614: ('long aft spine and bridge center', 16340),
    56526: ('bridge-side apron', 4096),
    50804: ('fore upper fairing', 3867),
}
parents = list(range(len(mesh.vertices)))


def find(index):
    while parents[index] != index:
        parents[index] = parents[parents[index]]
        index = parents[index]
    return index


def union(first, second):
    first, second = find(first), find(second)
    if first != second:
        parents[second] = first


for face in mesh.polygons:
    for vertex in face.vertices[1:]:
        union(face.vertices[0], vertex)

islands = defaultdict(list)
for face in mesh.polygons:
    island = find(face.vertices[0])
    if island in target_islands:
        islands[island].append(face)

changes = {}
for island, (description, expected_faces) in target_islands.items():
    faces = islands[island]
    assert len(faces) == expected_faces, (description, len(faces))
    before = Counter(mesh.materials[face.material_index].name for face in faces)
    assert set(before) <= {
        'Odin_Bridge_Armor', 'Odin_Bridge_Trim',
        'Odin_Paint_Light', 'Odin_Paint_Dark.001',
    }, (description, before)
    painted = Counter()
    for face in faces:
        material = mesh.materials[face.material_index].name
        if material == 'Odin_Paint_Light':
            face.material_index = armor_index
            painted['armor'] += 1
        elif material == 'Odin_Paint_Dark.001':
            face.material_index = trim_index
            painted['trim'] += 1
    assert painted, description
    changes[description] = dict(painted)

assert sum(changes[key].get('armor', 0) for key in changes) == 7063
assert sum(changes[key].get('trim', 0) for key in changes) == 40

# The forward end of the marked shape meets a small upper deck that is part
# of the continuous main-hull island. Paint only its exposed, upward-facing
# central wedge, stopping at the existing outer-deck paint boundary.
model_from_hull = asset.matrix_world.inverted() @ hull.matrix_world
fore_outline = [(-15, 42), (30, 26), (70, 0)]


def fore_width(y):
    for (a, wa), (b, wb) in zip(fore_outline, fore_outline[1:]):
        if a <= y <= b:
            return wa + (wb - wa) * (y - a) / (b - a)
    return -1


fore_count = 0
for face in mesh.polygons:
    if find(face.vertices[0]) != 174524:
        continue
    center = model_from_hull @ face.center
    if center.y <= -15 or abs(center.x) >= fore_width(center.y) or center.z < 35 or face.normal.z < .05:
        continue
    material = mesh.materials[face.material_index].name
    if material == 'Odin_Paint_Light':
        face.material_index = armor_index
        fore_count += 1
    elif material == 'Odin_Paint_Dark.001':
        face.material_index = trim_index
        fore_count += 1
assert fore_count == 517, fore_count
changes['central fore upper deck'] = {'armor': fore_count}

assert not any(obj.name.startswith('Bridge_Pinstripe_') for obj in bpy.data.objects)

asset['version'] = '0.11.11'
asset['bridgePaintRevision'] = 'Existing cement-gray bridge finish extended across three connected superstructure shell islands and the central fore upper-deck wedge; equipment and surrounding hull excluded'
bpy.context.scene.name = 'ODIN v0.11.11 — complete bridge superstructure paint'
for obj in bpy.context.scene.objects:
    obj.animation_data_clear()
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)

output = root / 'assets/blender/odin_articulated_v0.11.11.blend'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('BRIDGE_PAINT_EXTENDED', json.dumps({
    'shellIslands': changes,
    'palette': {
        armor.name: list(armor.diffuse_color),
        trim.name: list(trim.diffuse_color),
    },
    'editableAsset': str(output),
}), flush=True)
