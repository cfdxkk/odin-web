"""Run on v0.11.40: synchronize complete quad tubes/cradles to fitted petals.

Preserve all accepted source meshes, materials, UVs and static rest frames.
Only joint metadata changes; animation is authored in the Nuxt rig.
"""
import bpy, json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
review = root / 'docs/review/v0.11.41'
review.mkdir(parents=True, exist_ok=True)
rows = []
for side in ['Port', 'Starboard']:
    for i in range(4):
        prefix = f'PDC_{side}'
        petal = bpy.data.objects[f'{prefix}_HullPetal_{i}']
        cradle = bpy.data.objects[f'{prefix}_Cradle_{i}']
        guide = bpy.data.objects[f'{prefix}_CradleGuide_{i}']
        tube = bpy.data.objects[f'{prefix}_Arm_{i}']
        before = list(cradle['compactVector'])
        # Preserve four-way source articulation, shortening the total stroke.
        # The common squared petal clock also removes the old early squeeze:
        # the tubes previously reached much farther inward at every half-open
        # pose than their nearby armor. Endpoints retain source-skin clearance.
        ys = 1 if i < 2 else -1
        zs = 1 if i % 2 == 0 else -1
        cradle['compactVector'] = [0., ys*1.95, zs*.33]
        cradle['synchronizedPetal'] = petal.name
        cradle['petalPackingExponent'] = petal['petalPackingExponent']
        for key in ['compactStart', 'compactEnd', 'compactLead']:
            cradle[key] = petal[key]
        # The long source fork keeps its accepted net 0.60 guide stroke while
        # its short bearing shares the tube stroke; both use the petal clock.
        guide['compactVector'] = [0., -ys*1.35, 0.]
        guide['synchronizedPetal'] = petal.name
        tube['slideStart'] = .20
        tube['slideEnd'] = .56
        tube['extendsAfterPetal'] = petal.name
        rows.append({'side': side, 'quadrant': i, 'petal': petal.name,
                     'previousCompactVector': before,
                     'compactVector': list(cradle['compactVector']),
                     'guideVector': list(guide['compactVector']),
                     'packingInterval': [float(petal['compactStart']), float(petal['compactEnd'])],
                     'tubeExtensionInterval': [float(tube['slideStart']), float(tube['slideEnd'])],
                     'tubeAxialTravel': float(tube['stowTravel'])})
asset = bpy.data.objects['Odin_Asset']
asset['version'] = '0.11.41'
asset['bridgeQuadStrokeRevision'] = 'All four tubes and their source cradles use shorter total center strokes (1.95 Y / 0.33 Z) on their fitted armor petal clock. No early squeeze; axial extension follows petal release.'
assert not bpy.data.actions
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'assets/blender/odin_articulated_v0.11.41.blend'), compress=True)
(review / 'assembly-fit.json').write_text(json.dumps({'version': '0.11.41', 'quadrants': rows}, indent=2)+'\n', encoding='utf8')
print('SYNCHRONIZED_QUAD_STROKES', [(r['side'], r['quadrant'], r['compactVector']) for r in rows], flush=True)
