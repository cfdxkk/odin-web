"""Save the accepted v42 geometry with a reproducible static tempo profile."""
import bpy, json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
profile = json.loads((root/'app/lib/turret-tempo-profile.json').read_text())
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.42'
assert profile['version'] == '0.11.43'
asset['version'] = profile['version']
asset['turretTempoProfile'] = json.dumps(profile, separators=(',', ':'))
asset['turretTempoRevision'] = 'Retimed complete bridge-quad and aft-twin pose paths; geometry, pivots, strokes and clearance order unchanged.'
assert not bpy.data.actions
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.43.blend'), compress=True)
print('TURRET_TEMPO_SAVED', profile, flush=True)
