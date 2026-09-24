"""Create v0.8.2 static parts; all articulation remains in Nuxt/Three.js.

Run with the saved v0.8.1 editable asset. The original odin.blend is never opened
or overwritten. Each helper owns a separate set of mechanical parts.
"""
import bpy
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
baseline = root / 'assets/blender/odin_articulated_v0.8.1.blend'
if Path(bpy.data.filepath).resolve() != baseline.resolve():
    raise RuntimeError('Load the v0.8.1 editable baseline before this revision')

for filename in ['planar_aft_v082.py', 'differential_main_bores_v082.py']:
    helper = root / 'tools' / filename
    namespace = {'__file__': str(helper), '__name__': '__main__'}
    exec(compile(helper.read_text(encoding='utf8'), str(helper), 'exec'), namespace)
    if 'differential_main_bores_v082_audit' in namespace:
        report = root / 'work/v082-review/bore-source-preservation.json'
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(namespace['differential_main_bores_v082_audit'], indent=2), encoding='utf8')

for obj in bpy.context.scene.objects:
    obj.animation_data_clear()
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)
bpy.data.objects['Odin_Asset']['version'] = '0.8.2'
bpy.context.scene.name = 'ODIN v0.8.2 - planar aft armor and differentiated bore stow'
bpy.data.orphans_purge(do_recursive=True)
output = root / 'assets/blender/odin_articulated_v0.8.2.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print('SAVED', output.name, flush=True)
