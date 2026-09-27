"""Keep aft twin guides just behind their gun bodies during inward retraction.

The rail mesh contains both long guides and lower supporting pieces. This
version updates only static joint travel metadata; the rig animates it in JS.
"""

import bpy
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert str(asset['version']) == '0.11.7'

rails = []
for side in ('Port', 'Starboard'):
    joint = bpy.data.objects[f'DefenseRail_Aft_{side}']
    assert any(child.name.startswith('holo.010_') for child in joint.children)
    joint['finalStowInward'] = 5.0
    joint['retractLag'] = 0.025
    rails.append(joint.name)

asset['version'] = '0.11.8'
asset['aftRailRevision'] = 'long guides and lower brackets slide inboard just behind gun body without crossing glazing'
bpy.context.scene.name = 'ODIN v0.11.8 — aft twin rail fit'
for obj in bpy.context.scene.objects:
    obj.animation_data_clear()
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)

output = root / 'assets/blender/odin_articulated_v0.11.8.blend'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('AFT_RAIL_FIT', json.dumps({'rails': rails, 'extraInward': 5.0, 'retractLag': 0.025, 'editableAsset': str(output)}), flush=True)
