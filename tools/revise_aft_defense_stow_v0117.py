"""Keep the four aft twin turrets and their shared rails in one final sink.

Geometry is preserved. Only static joint travel metadata changes; the motion
curve is authored in app/lib/odin-rig.ts and the GLB has no animation clips.
"""

import bpy
import json
from pathlib import Path


root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert str(asset['version']) == '0.11.6'

inward = 5.0
drop = 4.0
carriages = []
for number in range(5, 9):
    joint = bpy.data.objects[f'Defense_{number:02}_Carriage']
    assert joint['station'] == 'aft'
    joint['finalStowInward'] = inward
    joint['finalStowDrop'] = drop
    carriages.append(joint.name)

rails = []
for side in ('Port', 'Starboard'):
    joint = bpy.data.objects[f'DefenseRail_Aft_{side}']
    joint['finalStowDrop'] = drop
    rails.append(joint.name)

asset['version'] = '0.11.7'
asset['aftDefenseRevision'] = 'last 20 percent retracts and sinks together; shared support rails sink with twins'
bpy.context.scene.name = 'ODIN v0.11.7 — aft twin stow'
for obj in bpy.context.scene.objects:
    obj.animation_data_clear()
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)

output = root / 'assets/blender/odin_articulated_v0.11.7.blend'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('AFT TWIN STOW', json.dumps({
    'carriages': carriages, 'supportRails': rails,
    'extraInward': inward, 'totalDrop': drop,
    'editableAsset': str(output),
}), flush=True)
