"""Restore the aft twins' original four-unit sink without changing their travel."""

import bpy
import json
from pathlib import Path


root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert str(asset['version']) == '0.11.9'

changed = []
for number in range(5, 9):
    joint = bpy.data.objects[f'Defense_{number:02}_Carriage']
    assert joint['station'] == 'aft'
    assert abs(float(joint['finalStowInward']) - 2.3) < 1e-6
    joint['finalStowDrop'] = 4.0
    changed.append(joint.name)
for side in ('Port', 'Starboard'):
    joint = bpy.data.objects[f'DefenseRail_Aft_{side}']
    assert abs(float(joint['finalStowInward']) - 2.3) < 1e-6
    joint['finalStowDrop'] = 4.0
    changed.append(joint.name)

asset['version'] = '0.11.10'
asset['aftDefenseRevision'] = 'original four-unit sink restored; outward endpoint and forty-percent onset retained'
bpy.context.scene.name = 'ODIN v0.11.10 — aft twin original sink depth'
for obj in bpy.context.scene.objects:
    obj.animation_data_clear()
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)

output = root / 'assets/blender/odin_articulated_v0.11.10.blend'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('AFT_TWIN_DROP_RESTORED', json.dumps({
    'joints': changed, 'inboard': 2.3, 'drop': 4.0,
    'editableAsset': str(output),
}), flush=True)
