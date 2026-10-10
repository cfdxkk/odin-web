"""Sweep the actual aft twin guns and rails past the fitted gate solids."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
rest={o:(o.location.copy(),o.rotation_quaternion.copy())for o in bpy.context.scene.objects if o.get('staticJoint')}
cache={}
def ease(a,b,d):t=max(0,min(1,(d-a)/(b-a)));return t*t*(3-2*t)
def move(name,delta,turn=None):
 o=bpy.data.objects[name];o.location=rest[o][0]+Vector(delta)
 if turn is not None:o.rotation_mode='QUATERNION';o.rotation_quaternion=turn@rest[o][1]
def pose(d,scan=0,unsunk=False):
 final=ease(.05,.20,d);travel=.2*final+.8*ease(.20,.52,d);sink=1-ease(.05,.40,d);gun=ease(.65,.94,d);aim=ease(.95,1,d)
 for side,sign in [('Port',-1),('Starboard',1)]:
  rail=bpy.data.objects[f'DefenseRail_Aft_{side}'];lag=travel+float(rail['retractLag'])*math.sin(math.pi*travel);extra=float(rail['finalStowInward'])
  move(rail.name,[sign*((9.903+extra)*lag-extra),-1.392*lag,0 if unsunk else-float(rail['finalStowDrop'])*sink])
 for i in range(5,9):
  prefix=f'Defense_{i:02}';gate=bpy.data.objects[prefix+'_NotchGate'];c=bpy.data.objects[prefix+'_Carriage'];sign=c['side'];extra=c['finalStowInward']
  move(gate.name,np.array(gate['slideVector'])*ease(0,.05,d)+np.array(gate['releaseVector'])*ease(0,.04,d))
  move(c.name,[sign*((9.903+extra)*travel-extra),-1.392*travel,0 if unsunk else-c['finalStowDrop']*sink])
  heading=22 if i in(5,7)else-16
  yaw=sign*heading*gun+scan*aim
  move(prefix+'_Yaw',[0,0,0],Quaternion((0,0,1),math.radians(yaw)))
  elev=bpy.data.objects[prefix+'_Elevation']
  move(elev.name,[0,0,0],Quaternion(Vector(elev['hingeAxisModel']).normalized(),math.radians(elev['pitchDegrees'])*gun))
 bpy.context.view_layer.update()
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
def children(name):return[o for o in bpy.data.objects[name].children_recursive if o.type=='MESH']
report={i:{'poses':0,'gunCoverContacts':[],'railCoverContacts':[]}for i in range(5,9)}
for step in range(401):
 d=step/400;pose(d)
 rails={side:tree(children(f'DefenseRail_Aft_{side}'))for side in['Starboard','Port']}
 for i,row in report.items():
  gate=tree(children(f'Defense_{i:02}_NotchGate'));gun=tree(children(f'Defense_{i:02}_Carriage'));side='Starboard'if i<7 else'Port';rail=rails[side]
  row['poses']+=1
  for key,shape in [('gunCoverContacts',gun),('railCoverContacts',rail)]:
   n=hits(shape,gate)
   if n:row[key].append({'progress':d,'triangleContacts':n})
 if step%100==0:print('AFT_SWEEP_PROGRESS',step,'/400',flush=True)
for i,row in report.items():
 row['scanEndpointContacts']=[]
 for scan in[-3,3]:
  pose(1,scan);gate=tree(children(f'Defense_{i:02}_NotchGate'));n=hits(tree(children(f'Defense_{i:02}_Carriage')),gate)
  if n:row['scanEndpointContacts'].append({'scanDegrees':scan,'triangleContacts':n})
 pose(0,unsunk=True)
 row['unsunkControlContacts']=hits(tree(children(f'Defense_{i:02}_Carriage')),tree(children(f'Defense_{i:02}_NotchGate')))
# The closed exterior must also remain in front of the fixed source rim. The
# tiny serrated rim ridges otherwise protrude through a least-squares plane.
pose(0)
hull=bpy.data.objects['holo.001'];hull.data.calc_loop_triangles()
M=np.array(inv@hull.matrix_world);points=np.array([v.co for v in hull.data.vertices])@M[:3,:3].T+M[:3,3]
hull_tris=points[np.array([t.vertices[:]for t in hull.data.loop_triangles])]
for i,row in report.items():
 skin=bpy.data.objects[f'Defense_{i:02}_NotchGate_Skin'];skin.data.calc_loop_triangles();M=np.array(inv@skin.matrix_world)
 vertices=np.array([v.co for v in skin.data.vertices])@M[:3,:3].T+M[:3,3]
 faces=[list(t.vertices)for t in skin.data.loop_triangles if t.polygon_index==0]
 outer=vertices[np.array(faces)]
 lo,hi=outer.min((0,1))-.1,outer.max((0,1))+.1
 nearby=hull_tris[((hull_tris.max(1)>=lo)&(hull_tris.min(1)<=hi)).all(1)]
 def shape(tris):
  vs=tris.reshape(-1,3);return {'vertices':vs.tolist(),'faces':np.arange(len(vs)).reshape(-1,3).tolist(),'tris':tris,'bounds':(vs.min(0),vs.max(0)),'bvh':None}
 row['closedExteriorHullContacts']=hits(shape(outer),shape(nearby))
 control=outer-np.array(skin['hullFitNormalModel'])*skin['hullFitNormalClearance']
 row['unseatedExteriorControlContacts']=hits(shape(control),shape(nearby))
(root/'docs/review/v0.11.35/mesh-clearance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('AFT_COVER_SWEEP',[(i,len(r['gunCoverContacts']),len(r['railCoverContacts']),r['unsunkControlContacts'])for i,r in report.items()],flush=True)
assert all(not r['gunCoverContacts']and not r['railCoverContacts']and not r['scanEndpointContacts']for r in report.values())
assert all(r['unsunkControlContacts']>0 for r in report.values()),'The omitted-sink control must cross each closed cover'
assert all(r['closedExteriorHullContacts']==0 for r in report.values()),'The fixed source rim must not protrude through a closed exterior skin'
assert all(r['unseatedExteriorControlContacts']>0 for r in report.values()),'The rim-seating check must detect a skin below the source rim envelope'
