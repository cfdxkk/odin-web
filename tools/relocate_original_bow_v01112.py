"""Restore the source bow single turret, then relocate its original receiver.

Only the bow is touched. The untouched odin.blend supplies the gun, housing,
receiver shell, and internal brackets. No Blender animation is carried over:
the existing web-authored barrel motion and every other battery stay intact.
"""

import bpy
import bmesh
import os
from collections import defaultdict
from pathlib import Path
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'Odin 建模' / 'odin.blend'
ASSET = bpy.data.objects['Odin_Asset']
assert str(ASSET['version']) == '0.11.11'

# The original source receiver remains rigid. Its sole adjustment is the
# translation that brings its rear channel edge to the fixed turret edge.
SHIFT = Vector((0.0, float(os.environ.get('ODIN_BOW_FORWARD', '3.45')), float(os.environ.get('ODIN_BOW_VERTICAL', '0.55'))))


def islands(obj):
    mesh = obj.data
    parent = list(range(len(mesh.vertices)))

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for edge in mesh.edges:
        a, b = edge.vertices
        parent[root(a)] = root(b)
    groups = defaultdict(list)
    for vertex in mesh.vertices:
        groups[root(vertex.index)].append(vertex.index)
    matrix = ASSET.matrix_world.inverted() @ obj.matrix_world if obj.parent == ASSET else obj.matrix_world
    for ids in groups.values():
        points = [matrix @ mesh.vertices[index].co for index in ids]
        low = tuple(min(point[axis] for point in points) for axis in range(3))
        high = tuple(max(point[axis] for point in points) for axis in range(3))
        yield ids, low, high


def receiver_ids(obj, original):
    floor_size = 516 if original else 454
    floor = []
    braces = []
    skirts = []
    for ids, low, high in islands(obj):
        if max(abs(low[0]), abs(high[0])) > 6.5:
            continue
        if len(ids) == floor_size and 217 < low[1] < 219 and 287 < high[1] < 290:
            floor.append(ids)
        elif len(ids) == 184 and 245 < low[1] < 277 and 246 < high[1] < 278:
            braces.append(ids)
        elif len(ids) == 166 and 245 < low[1] < 272 and 246 < high[1] < 273:
            skirts.append(ids)
    assert len(floor) == 1, ('floor', original, len(floor))
    assert len(braces) == 15, ('braces', original, len(braces))
    assert len(skirts) == (6 if original else 0), ('skirts', original, len(skirts))
    return set().union(*floor, *braces, *skirts), (len(floor), len(braces), len(skirts))


def erase_tree(obj):
    for child in list(obj.children):
        erase_tree(child)
    bpy.data.objects.remove(obj, do_unlink=True)


with bpy.data.libraries.load(str(SOURCE), link=False) as (source, loaded):
    loaded.objects = ['odin.002', 'odin.003', 'holo.001']
source_gun, source_housing, source_hull = loaded.objects
for obj in loaded.objects:
    bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.update()

for source_obj, target_name, target_material in (
    (source_gun, 'odin.002', 'Odin_Weapon_Steel'),
    (source_housing, 'odin.003', 'Odin_Paint_Light'),
):
    target = bpy.data.objects[target_name]
    evaluated = source_obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    restored = bpy.data.meshes.new_from_object(
        evaluated, preserve_all_data_layers=True, depsgraph=bpy.context.evaluated_depsgraph_get()
    )
    placement = target.matrix_world.inverted() @ ASSET.matrix_world @ source_obj.matrix_world
    restored.transform(placement)
    restored.materials.clear()
    restored.materials.append(bpy.data.materials[target_material])
    for modifier in list(target.modifiers):
        target.modifiers.remove(modifier)
    old = target.data
    target.data = restored
    if old.users == 0:
        bpy.data.meshes.remove(old)
    assert target.parent.name == ('Axial_Bow_Barrel' if target_name == 'odin.002' else 'Axial_Bow_Mount')

# The previous experimental armor is deliberately discarded. The requested
# first step is the source receiver's location, not another armor redesign.
for name in [obj.name for obj in bpy.data.objects]:
    obj = bpy.data.objects.get(name)
    if obj is None:
        continue
    if obj.name.startswith(('Axial_Bow_Shutter_', 'Axial_Bow_FrontCap')) and obj.parent is not None:
        if obj.parent.name.startswith(('Axial_Bow_Shutter_', 'Axial_Bow_FrontCap')):
            continue
        erase_tree(obj)

target_hull = bpy.data.objects['holo.001']
discard, current_counts = receiver_ids(target_hull, original=False)
source_ids, source_counts = receiver_ids(source_hull, original=True)

receiver_mesh = source_hull.data.copy()
bm = bmesh.new()
bm.from_mesh(receiver_mesh)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in source_ids], context='VERTS')
bm.to_mesh(receiver_mesh)
bm.free()
receiver_mesh.update()
source_positions = sorted(tuple(round(axis, 5) for axis in source_hull.data.vertices[index].co) for index in source_ids)
receiver_positions = sorted(tuple(round(axis, 5) for axis in vertex.co) for vertex in receiver_mesh.vertices)
assert receiver_positions == source_positions, 'Receiver vertices must remain identical to odin.blend'
receiver_mesh.materials.clear()
for material in list(target_hull.data.materials)[:6]:
    receiver_mesh.materials.append(material)

receiver_joint = bpy.data.objects.new('Axial_Bow_SourceReceiver', None)
bpy.context.scene.collection.objects.link(receiver_joint)
receiver_joint.parent = ASSET
receiver_joint.matrix_parent_inverse = Matrix.Identity(4)
receiver_joint.matrix_local = Matrix.Translation(SHIFT)
receiver_joint['staticJoint'] = True
receiver_joint['system'] = 'bow-receiver'
receiver_joint['sourceFile'] = 'odin.blend'
receiver_joint['receiverShiftModel'] = list(SHIFT)
receiver = bpy.data.objects.new('Axial_Bow_SourceReceiver_Skin', receiver_mesh)
bpy.context.scene.collection.objects.link(receiver)
receiver.parent = receiver_joint
receiver.matrix_parent_inverse = Matrix.Identity(4)
receiver.matrix_local = Matrix.Identity(4)

bm = bmesh.new()
bm.from_mesh(target_hull.data)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index in discard], context='VERTS')
bm.to_mesh(target_hull.data)
bm.free()
target_hull.data.update()

for obj in loaded.objects:
    bpy.data.objects.remove(obj, do_unlink=True)
for action in list(bpy.data.actions):
    if action.users == 0:
        bpy.data.actions.remove(action)

ASSET['version'] = '0.11.12'
ASSET['bowRevision'] = 'original source turret and receiver, receiver moved forward/down only'
assert not any(obj.animation_data and obj.animation_data.action for obj in bpy.context.scene.objects)
destination = Path(os.environ.get('ODIN_BOW_OUTPUT', str(ROOT / 'assets/blender/odin_articulated_v0.11.12.blend')))
bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
print('BOW_SOURCE_RESTORED', current_counts, source_counts, 'RIGID_SHIFT', tuple(SHIFT), destination, flush=True)
