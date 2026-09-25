"""Check the five closed dorsal shells and their source-hull-aligned hinges."""
import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1];out=R/'docs/review/v0.8.11';out.mkdir(exist_ok=True)
source=R/'assets/blender/odin_articulated_v0.8.11.blend'
assert Path(bpy.data.filepath).resolve()==source.resolve()
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted();report={'version':'0.8.11','blendSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'parts':{},'hinges':{}}
for role,suffix in [('Port','FittedSkin'),('Starboard','FittedSkin'),('Nose','Wedge'),('Aft_Port','GapFiller'),('Aft_Starboard','GapFiller')]:
 o=bpy.data.objects[f'Hatch_Dorsal_{role}_{suffix}'];bm=bmesh.new();bm.from_mesh(o.data)
 assert all(e.is_manifold and e.is_contiguous for e in bm.edges),o.name
 assert all(f.calc_area()>1e-8 for f in bm.faces),o.name
 volume=bm.calc_volume(signed=True);assert volume>0,o.name;bm.free()
 o.data.calc_loop_triangles();ts=[tuple(t.vertices)for t in o.data.loop_triangles]
 tree=BVHTree.FromPolygons([v.co for v in o.data.vertices],ts,all_triangles=True)
 hits=[(a,b)for a,b in tree.overlap(tree) if a<b and not(set(ts[a])&set(ts[b]))]
 assert not hits,(o.name,hits[:4])
 ps=[inv@o.matrix_world@v.co for v in o.data.vertices];n=len(ps)//2
 distances=[(ps[i]-ps[i+n]).length for i in range(n)]
 report['parts'][o.name]={'watertight':True,'selfIntersections':0,'positiveVolume':volume,'minimumCorrespondingSkinDistance':min(distances),'maximumCorrespondingSkinDistance':max(distances)}
 if role.startswith('Aft_'):
  j=o.parent;normal=Vector(j['planeNormal']).normalized();a,b=map(Vector,j['hingeEdge']);axis=Vector(j['hingeAxis'])
  plane_error=max(abs(normal.dot(p-ps[0]))for p in ps[:n]);assert plane_error<2e-5
  endpoint_errors=[min((p-q).length for p in ps)for q in [a,b]];assert max(endpoint_errors)<2e-5
  s=1 if 'Starboard' in role else -1;original=Vector((-s*.3078,5.6408,-.298)).normalized();alignment=axis.cross(original).length;assert alignment<2e-5
  report['hinges'][j.name]={'singlePlaneError':plane_error,'hingeOnMaterialEdge':endpoint_errors,'parallelToOriginalHullCreaseError':alignment,'openingDegrees':j['openingAngleDegrees'],'parent':j.parent.name}
original=R.parent/'Odin 建模/odin.blend'
report['originalSourceSha256']=hashlib.sha256(original.read_bytes()).hexdigest()
assert report['originalSourceSha256']=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
assert not bpy.data.actions
report['animationActions']=0;report['passed']=True
(out/'physical-fit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('Five watertight shells; no self intersections; flat aft leaves; hull-aligned fixed hinges; original source unchanged')
