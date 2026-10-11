"""Remove only the v0.11.5 bridge-base pinstripes.

The cement-gray bridge materials and their expanded hull-face assignment are
preserved exactly. The bow single-gun geometry and animation are untouched.
"""

import bpy
import json
from pathlib import Path


root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert str(asset['version']) == '0.11.5'

hull = bpy.data.objects['holo.001']
palette = {
    name: tuple(bpy.data.materials[name].diffuse_color)
    for name in ('Odin_Bridge_Armor', 'Odin_Bridge_Trim')
}
painted_faces = {
    name: sum(1 for face in hull.data.polygons if hull.data.materials[face.material_index].name == name)
    for name in palette
}

pinstripes = [obj for obj in bpy.data.objects if obj.name.startswith('Bridge_Pinstripe_')]
assert pinstripes, 'Expected the v0.11.5 bridge-base pinstripes'
removed_names = [obj.name for obj in pinstripes]
for obj in pinstripes:
    bpy.data.objects.remove(obj, do_unlink=True)
for mesh in list(bpy.data.meshes):
    if mesh.name.startswith('Bridge_Pinstripe_Paint') and mesh.users == 0:
        bpy.data.meshes.remove(mesh)
stripe_material = bpy.data.materials.get('Odin_Bridge_Pinstripe')
if stripe_material and stripe_material.users == 0:
    bpy.data.materials.remove(stripe_material)

assert not any(obj.name.startswith('Bridge_Pinstripe_') for obj in bpy.data.objects)
assert palette == {
    name: tuple(bpy.data.materials[name].diffuse_color) for name in palette
}
assert painted_faces == {
    name: sum(1 for face in hull.data.polygons if hull.data.materials[face.material_index].name == name)
    for name in palette
}

asset['version'] = '0.11.6'
asset['bridgePaintRevision'] = 'Cement-gray area and palette retained; added base pinstripes removed'
bpy.context.scene.name = 'ODIN v0.11.6 — gray bridge without added pinstripes'
for obj in bpy.context.scene.objects:
    obj.animation_data_clear()
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)

output = root / 'assets/blender/odin_articulated_v0.11.6.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('BRIDGE PINSTRIPES REMOVED', json.dumps({
    'removedObjects': removed_names,
    'grayBridgeFaces': painted_faces,
    'grayBridgePalette': palette,
    'editableAsset': str(output),
}), flush=True)
