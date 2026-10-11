"""Check all native meshes, UVs, materials and rest frames against v42."""
import bpy, hashlib, json
import numpy as np
from pathlib import Path

root = Path(__file__).resolve().parents[1]
helper = (root/'tools/verify_bridge_quads_v01141.py').read_text().split('bpy.ops.wm.open_mainfile')[0]
exec(compile(helper, str(root/'tools/verify_bridge_quads_v01141.py'), 'exec'))
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.42.blend'))
before = snapshot()
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.43.blend'))
after = snapshot()
assert before.keys() == after.keys()
meshes = joints = 0
for name, old in before.items():
    now = after[name]
    assert np.array_equal(now['matrix'], old['matrix']) and np.array_equal(now['world'], old['world']), name
    assert now['parent'] == old['parent'], name
    if old['mesh'] is not None:
        assert now['mesh'] == old['mesh'], name
        meshes += 1
    if name != 'Odin_Asset':
        assert now['props'] == old['props'], name
    else:
        omit = {'version', 'turretTempoProfile', 'turretTempoRevision'}
        assert {k:v for k,v in now['props'].items() if k not in omit} == {k:v for k,v in old['props'].items() if k not in omit}
    joints += bool(old['props'].get('staticJoint'))
profile = json.loads(bpy.data.objects['Odin_Asset']['turretTempoProfile'])
assert profile == json.loads((root/'app/lib/turret-tempo-profile.json').read_text())
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
source = root.parent/'Odin 建模/odin.blend'
with source.open('rb') as f: source_hash = hashlib.file_digest(f, 'sha256').hexdigest()
assert source_hash == '9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
with (root/'assets/blender/odin_articulated_v0.11.43.blend').open('rb') as f: native_hash = hashlib.file_digest(f, 'sha256').hexdigest()
report = {'version':'0.11.43', 'baseline':'0.11.42', 'nativeSha256':native_hash, 'sourceSha256':source_hash,
          'allMeshesUnchanged':meshes, 'allStaticRestFramesUnchanged':joints, 'allJointPropertiesUnchanged':True,
          'originalSourceUnchanged':True, 'animationClips':0, 'tempoProfile':profile}
(root/'docs/review/v0.11.43/source-geometry.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
print('PRESERVED_TURRET_GEOMETRY', meshes, joints, flush=True)
