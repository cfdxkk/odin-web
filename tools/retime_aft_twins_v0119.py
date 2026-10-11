"""Set a shallower inboard seat and gentle 40%-to-5% sink for aft twins.

Only static joint travel metadata changes. All animation stays in Nuxt/Three.
"""
import bpy
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert str(asset['version']) == '0.11.8'

inward = 2.3
drop = 7.5
names = []
for number in range(5, 9):
    joint = bpy.data.objects[f'Defense_{number:02}_Carriage']
    assert joint['station'] == 'aft'
    joint['finalStowInward'] = inward
    joint['finalStowDrop'] = drop
    joint['sinkStart'] = 0.40
    names.append(joint.name)
for side in ('Port', 'Starboard'):
    joint = bpy.data.objects[f'DefenseRail_Aft_{side}']
    joint['finalStowInward'] = inward
    joint['finalStowDrop'] = drop
    joint['sinkStart'] = 0.40
    names.append(joint.name)

asset['version'] = '0.11.9'
asset['aftDefenseRevision'] = 'no separate late lift; joint sink starts at 40 percent; shallower common inboard seat'
bpy.context.scene.name = 'ODIN v0.11.9 — aft twin sink'
for obj in bpy.context.scene.objects:
    obj.animation_data_clear()
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)

output = root / 'assets/blender/odin_articulated_v0.11.9.blend'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('AFT_TWIN_SINK', json.dumps({'joints': names, 'inboard': inward, 'drop': drop,
                                   'sinkStart': 0.40, 'editableAsset': str(output)}), flush=True)
