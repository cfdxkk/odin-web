"""Actual Nuxt runtime poses against original fixed hoods and guide rails."""
import bpy,json,numpy as np,math
from pathlib import Path
from mathutils import Quaternion,Vector
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted();cache={}
basis=Quaternion((1,0,0),-math.pi/2)

def children(name):return[o for o in bpy.data.objects[name].children_recursive if o.type=='MESH']

def tree(objects):
 vs=[];fs=[]
 for o in objects:
  if o.name not in cache:
   o.data.calc_loop_triangles();cache[o.name]=(np.array([v.co for v in o.data.vertices]),np.array([t.vertices[:]for t in o.data.loop_triangles],dtype=np.int32))
  ps,ts=cache[o.name];M=np.array(inv@o.matrix_world);p=ps@M[:3,:3].T+M[:3,3];start=len(vs);vs.extend(p.tolist());fs.extend((ts+start).tolist())
 cloud=np.array(vs);tris=cloud[np.array(fs,dtype=np.int32)]
 return {'vertices':vs,'faces':fs,'tris':tris,'bounds':(cloud.min(0),cloud.max(0)),'bvh':None}

def hits(a,b):
 if np.any(np.minimum(a['bounds'][1],b['bounds'][1])-np.maximum(a['bounds'][0],b['bounds'][0])<-.00001):return 0
 for shape in[a,b]:
  if shape['bvh']is None:shape['bvh']=BVHTree.FromPolygons(shape['vertices'],shape['faces'],all_triangles=True,epsilon=0)
 pairs=a['bvh'].overlap(b['bvh'])
 if not pairs:return 0
 ia,ib=np.array(pairs,dtype=np.int32).T;ta=a['tris'][ia];tb=b['tris'][ib];ea=np.roll(ta,-1,axis=1)-ta;eb=np.roll(tb,-1,axis=1)-tb;na=np.cross(ea[:,0],ea[:,1]);nb=np.cross(eb[:,0],eb[:,1])
 axes=np.concatenate([na[:,None],nb[:,None],np.cross(ea[:,:,None],eb[:,None,:]).reshape(-1,9,3),np.cross(na[:,None],ea),np.cross(nb[:,None],eb)],axis=1)
 size=np.linalg.norm(axes,axis=2);pa=np.einsum('nac,nvc->nav',axes,ta);pb=np.einsum('nac,nvc->nav',axes,tb);overlap=np.minimum(pa.max(2),pb.max(2))-np.maximum(pa.min(2),pb.min(2))
 return int(np.sum(~((size>1e-8)&(overlap<-size*1e-5)).any(1)))

def apply(row):
 for j in row['joints']:
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);x,y,z,w=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((w,x,y,z))@basis
 bpy.context.view_layer.update()

hoods={i:tree([bpy.data.objects[f'Defense_{i:02}_FixedHood']])for i in range(1,5)}
rows=json.loads((root/'work/v01138-review/runtime-poses.json').read_text());report={i:{'poses':0,'hoodContacts':[],'railContacts':[],'upperRailContacts':[]}for i in range(1,5)}
for step,row in enumerate(rows):
 apply(row);rails={s:tree(children(f'DefenseRail_Forward_{s}'))for s in['Port','Starboard']}
 for i,out in report.items():
  gun=tree(children(f'Defense_{i:02}_Carriage'));out['poses']+=1
  for key,shape in [('hoodContacts',hoods[i]),('railContacts',rails['Port'if i<=2 else'Starboard'])]:
   n=hits(gun,shape)
   if n:out[key].append({'progress':row['progress'],'time':row['time'],'triangleContacts':n})
  upper=tree([o for o in children(f'Defense_{i:02}_Carriage')if not o.name.endswith('_LowerCradle')])
  n=hits(upper,rails['Port'if i<=2 else'Starboard'])
  if n:out['upperRailContacts'].append({'progress':row['progress'],'triangleContacts':n})
 if step%100==0:print('FORWARD_TWIN_SWEEP',step,len(rows),flush=True)
for i,out in report.items():
 out['zeroDropControlContacts']=[]
 for row in rows[:401]:
  if not .24<=row['progress']<=.52:continue
  apply(row);bpy.data.objects[f'Defense_{i:02}_Carriage'].location.z+=4.6;bpy.context.view_layer.update()
  n=hits(tree(children(f'Defense_{i:02}_Carriage')),hoods[i])
  if n:out['zeroDropControlContacts'].append({'progress':row['progress'],'triangleContacts':n})
(root/'docs/review/v0.11.38/mesh-clearance.json').write_text(json.dumps(report,indent=2)+'\n')
print('FORWARD_TWIN_CLEARANCE',[(i,len(r['hoodContacts']),len(r['railContacts']),len(r['zeroDropControlContacts']))for i,r in report.items()],flush=True)
assert all(not r['hoodContacts']and not r['upperRailContacts']for r in report.values())
