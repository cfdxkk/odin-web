"""Report geometric contacts for actual JS poses, without changing the asset."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1];out=R/'work/v090-review';A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted();basis=Quaternion((1,0,0),-math.pi/2)
poses=json.loads((out/'candidate-poses.json').read_text(encoding='utf8'));cache={}
def data(o):
 if o.name not in cache:
  o.data.calc_loop_triangles();cache[o.name]=([v.co.copy()for v in o.data.vertices],[tuple(t.vertices)for t in o.data.loop_triangles])
 return cache[o.name]
def tree(objects):
 vertices=[];faces=[];names=[]
 for o in objects:
  ps,fs=data(o);m=inv@o.matrix_world;start=len(vertices);vertices.extend(m@p for p in ps);faces.extend(tuple(start+i for i in f)for f in fs);names.extend([o.name]*len(fs))
 return BVHTree.FromPolygons(vertices,faces,all_triangles=True,epsilon=.000001),vertices,faces,names
def hits(a,b):
 pairs=a[0].overlap(b[0]);groups={}
 for i,j in pairs:
  key=a[3][i]+' / '+b[3][j];g=groups.setdefault(key,[]);g.extend(a[1][k]for k in a[2][i])
 return {key:{'triangles':len(ps)//3,'bounds':np.round([np.min(ps,0),np.max(ps,0)],3).tolist()}for key,ps in groups.items()}
def children(j):return [o for o in j.children_recursive if o.type=='MESH']
single=[o for o in bpy.context.scene.objects if o.get('singleBattery')];bridge=[o for o in bpy.context.scene.objects if o.get('staticJoint')and o.name.startswith('BridgeArmor_')]
fixed=[bpy.data.objects['holo.001'],bpy.data.objects['BridgeWindow_SourceFrame'],bpy.data.objects['BridgeWindow_RearFrame']]
ft=tree(fixed);reports=[]
for pose in poses[::5]:
 for j in pose['joints']:
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
 bpy.context.view_layer.update();row={'deployment':pose['deployment'],'singles':{},'bridge':{}}
 for j in single:
  barrel=tree(children(j));covers=[o for o in bpy.context.scene.objects if o.get('barrelJoint')==j.name];ct=tree([c for o in covers for c in children(o)])
  contacts=hits(barrel,ct);h=hits(barrel,ft)
  if contacts or h:row['singles'][j.name]={'covers':contacts,'fixedHull':h}
 row['bridge']=hits(tree([c for j in bridge for c in children(j)]),ft)
 reports.append(row);print('POSE',pose['deployment'],'SINGLES',len(row['singles']),'BRIDGE',len(row['bridge']),flush=True)
(out/'secondary-contacts.json').write_text(json.dumps(reports,indent=2),encoding='utf8')
