"""Restore the unchanged bow meshes and rigid receiver from v0.11.12.

The v0.11.13 shoulder fairing was new geometry that the user did not ask for.
This revision changes no vertex, object transform, or animation data in the
editable asset. The original bow gun keyframes are reproduced in Nuxt.
"""

import bpy
from pathlib import Path


root = Path(__file__).resolve().parents[1]
asset = bpy.data.objects['Odin_Asset']
assert str(asset['version']) == '0.11.12'
assert 'Axial_Bow_SeamFairing' not in bpy.data.objects
receiver = bpy.data.objects['Axial_Bow_SourceReceiver']
assert all(abs(a - b) < 1e-5 for a, b in zip(receiver.location, (0, 3.45, 0.55)))
assert not any(obj.animation_data and obj.animation_data.action for obj in bpy.context.scene.objects)

asset['version'] = '0.11.14'
asset['bowRevision'] = 'unchanged source meshes and rigid receiver; original bow gun keyframes reproduced in Nuxt'
destination = root / 'assets/blender/odin_articulated_v0.11.14.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
print('BOW_SOURCE_MOTION_SAVED', destination, flush=True)
