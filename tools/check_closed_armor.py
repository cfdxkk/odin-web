"""Check the ten resting armor skins against the unchanged, fixed hull."""
import bpy,json,hashlib
from pathlib import Path
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1]
inverse=bpy.data.objects['Odin_Asset'].matrix_world.inverted()
def bvh(obj):
    matrix=inverse@obj.matrix_world;obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([matrix@v.co for v in obj.data.vertices],
        [tuple(t.vertices) for t in obj.data.loop_triangles],all_triangles=True,epsilon=.00001)
results=[]
for bank,name in [('Dorsal','holo.001'),('Ventral','holo.013')]:
    fixed=bvh(bpy.data.objects[name])
    for part in ['Port_FittedSkin','Starboard_FittedSkin','Nose_Wedge','Aft_Port_GapFiller','Aft_Starboard_GapFiller']:
        obj=bpy.data.objects[f'Hatch_{bank}_{part}']
        results.append(dict(armor=obj.name,hull=name,triangleIntersections=len(bvh(obj).overlap(fixed))))
report=dict(asset=Path(bpy.data.filepath).name,assetSha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),pairs=results)
(root/'docs/review/closed-armor-hull-clearance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
assert all(r['triangleIntersections']==0 for r in results),report
print('All ten closed armor skins clear the fixed hull.')
