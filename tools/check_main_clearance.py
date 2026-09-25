"""Sample actual JS poses and test armor against guns and adjacent armor.

Run against the editable asset after tools/review_rig_poses.mjs. This catches
intersections along the whole reversible travel, not just the end poses.
"""
import bpy,json,math,hashlib
from itertools import combinations
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

root=Path(__file__).resolve().parents[1]
scene=bpy.context.scene;asset=bpy.data.objects['Odin_Asset']
inverse=asset.matrix_world.inverted();basis=Quaternion((1,0,0),-math.pi/2)
poses=json.loads((root/'work/rig-review/clearance-poses.json').read_text())
geometries={}
for obj in scene.objects:
    if obj.type!='MESH':continue
    parents=[];p=obj.parent
    while p is not None:parents.append(p.name);p=p.parent
    if any(name.startswith(('Hatch_','Main_')) for name in parents):
        obj.data.calc_loop_triangles()
        geometries[obj.name]=(obj,[v.co.copy() for v in obj.data.vertices],[tuple(t.vertices) for t in obj.data.loop_triangles],parents)

def merge_bvh(items):
    vertices=[];triangles=[];names=[]
    for obj,points,faces,parents in items:
        m=inverse@obj.matrix_world;offset=len(vertices)
        vertices.extend([m@p for p in points]);triangles.extend([tuple(i+offset for i in f) for f in faces]);names.extend([obj.name]*len(faces))
    return BVHTree.FromPolygons(vertices,triangles,all_triangles=True,epsilon=.00001),names,vertices,triangles

def witnesses(av,at,gv,gt,pairs):
    points=[]
    for ai,gi in pairs:
        a=[av[i] for i in at[ai]];g=[gv[i] for i in gt[gi]]
        for edges,tri in ((a,g),(g,a)):
            for p,q in zip(edges,edges[1:]+edges[:1]):
                ray=q-p
                if ray.length<1e-7:continue
                hit=intersect_ray_tri(*tri,ray.normalized(),p,True)
                if hit is not None and (hit-p).length<=ray.length+1e-6:points.append(hit)
    if not points:return None
    return [[round(min(p[k] for p in points),3) for k in range(3)],[round(max(p[k] for p in points),3) for k in range(3)]]

collisions=[];counts={}
for pose in poses:
    for j in pose['joints']:
        obj=bpy.data.objects[j['name']];x,y,z=j['position'];obj.location=(x,-z,y)
        q=j['quaternion'];obj.rotation_mode='QUATERNION';obj.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
    bpy.context.view_layer.update()
    for bank in ('Dorsal','Ventral'):
        gun,names,gv,gt=merge_bvh([v for v in geometries.values() if any(p.startswith(f'Main_{bank}_') for p in v[3])])
        armor_banks={}
        for role in ('Port','Starboard','Nose','Aft_Port','Aft_Starboard'):
            armor,anames,av,at=merge_bvh([v for v in geometries.values() if f'Hatch_{bank}_{role}' in v[3]])
            armor_banks[role]=(armor,anames,av,at)
            overlap=armor.overlap(gun)
            if overlap:
                pairs=sorted(set((anames[a],names[b]) for a,b in overlap))
                collisions.append({'deployment':pose['deployment'],'bank':bank,'role':role,'trianglePairs':len(overlap),'objects':pairs,'intersectionBounds':witnesses(av,at,gv,gt,overlap)})
                for a,b in pairs:counts[f'{bank}/{role}: {a} × {b}']=counts.get(f'{bank}/{role}: {a} × {b}',0)+1
        for left,right in combinations(armor_banks,2):
            a,an,av,at=armor_banks[left];b,bn,bv,bt=armor_banks[right];overlap=a.overlap(b)
            if overlap:
                pairs=sorted(set((an[i],bn[j]) for i,j in overlap))
                collisions.append({'deployment':pose['deployment'],'bank':bank,'role':f'{left}/{right}','trianglePairs':len(overlap),'objects':pairs,'intersectionBounds':witnesses(av,at,bv,bt,overlap)})
                for x,y in pairs:counts[f'{bank}/{left}/{right}: {x} × {y}']=counts.get(f'{bank}/{left}/{right}: {x} × {y}',0)+1
    if round(pose['deployment']*100)%20==0:print('CHECKED',pose['deployment'],flush=True)
report={'asset':Path(bpy.data.filepath).name,'assetSha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'rigSha256':hashlib.sha256((root/'app/lib/odin-rig.ts').read_bytes()).hexdigest(),'samples':len(poses),'testedPairsPerPose':30,'collisionPoses':len(set(c['deployment'] for c in collisions)),'pairs':counts,'collisions':collisions}
(root/'work/rig-review/main-clearance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='collisions'},indent=2),flush=True)
if collisions:raise RuntimeError('Main armor collision; inspect main-clearance.json')
