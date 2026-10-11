"""Fit the original closed covers to their hull seating height.

Original vertices and deployed endpoints are preserved. Only closed joint
datums change, with extra clearance over the existing breech crown.
"""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
R=Path(__file__).resolve().parents[1]
helpers=(R/'tools/revise_secondary_bridge_v090.py').read_text(encoding='utf8');exec(helpers[:helpers.index('def fit_channel_nose')])
out=R/'work/v0100-review';report=json.loads((out/'source-covers.json').read_text());base=json.loads((out/'geometry-build.json').read_text())
for name,row in report.items():
 C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes']);X,B,N=Q.T
 cap=bpy.data.objects[name+'_FrontCap'];cp=next(c for c in cap.children if c.type=='MESH');M=inv@cp.matrix_world;t=np.array([(np.array(M@v.co)-C)@Q for v in cp.data.vertices])
 planes=[]
 for sign in [-1,1]:
  fs=[]
  for f in cp.data.polygons:
   q=t[list(f.vertices)];a=np.linalg.lstsq(np.c_[q[:,:2],np.ones(len(q))],q[:,2],rcond=None)[0]
   if f.area>8 and q[:,0].mean()*sign>0 and .9<abs(a[0])<2.2 and abs(a[1])<.15:fs.append((f.area,a))
  planes.append(max(fs,key=lambda f:f[0])[1])
 a,b=planes;front=t[:,1].min();closedFront=front+np.dot(cap['slideVector'],B)
 center=((b[1]-a[1])*front+b[2]-a[2])/(a[0]-b[0]);crest=a[0]*center+a[1]*front+a[2];crossSlope=np.mean([abs(a[0]),abs(b[0])]);slope=np.mean([a[1],b[1]])
 seat=base['singles'][name]['closedSeat'];seatCrest=seat['base']+seat['rise']+seat['slope']*(closedFront-seat['front'])
 lift=max(.15,seatCrest-crest);cap['settleVector']=list(N*lift);closedCrest=crest+lift
 gun=bpy.data.objects[cap['barrel']];ps=np.concatenate([np.array([inv@c.matrix_world@v.co for v in c.data.vertices]) for c in gun.children if c.type=='MESH']);q=(ps-C)@Q
 y0=min(r['originalBounds'][0][1]for r in row['covers']);mask=(q[:,1]>y0)&(q[:,1]<closedFront-1)&(abs(q[:,0]-center)<2.2)
 # Retain the front butt joint and let the rear cover rise over the crown.
 if np.any(mask):slope=min(slope,float(np.min((q[mask,2]+.48+crossSlope*abs(q[mask,0]-center)-closedCrest)/(q[mask,1]-closedFront))))
 slope=max(slope,-.22)
 for leaf in row['covers']:
  j=bpy.data.objects[leaf['name']];skin=next(c for c in j.children if c.type=='MESH');M=inv@skin.matrix_world;q=np.array([(np.array(M@v.co)-C)@Q for v in skin.data.vertices]);sign=-1 if '_Shutter_Port_'in j.name else 1
  # Preserve the crossbar-derived source rake. The largest face can be a
  # flange or an integrated hull return rather than the cover's plane.
  oldAngle=math.radians(j['closedAngleDegrees'])
  if not j.get('sourceHingeAxisModel'):j['sourceHingeAxisModel']=list(j['hingeAxisModel'])
  oldAxis=np.array(j['sourceHingeAxisModel']);sourceSlope=2*np.dot(oldAxis,N)/np.dot(oldAxis,B)-np.mean([a[1],b[1]])
  axis=Vector(B+N*(sourceSlope+slope)*.5).normalized();turn=Quaternion(axis,oldAngle);rot=np.array(turn.to_matrix())
  edge=q[q[:,0]*sign>(q[:,0]*sign).max()-.12].mean(0);e=C+Q@edge;target=C+B*edge[1]+X*(center+sign*.055)+N*(closedCrest+slope*(edge[1]-closedFront))
  h=np.linalg.pinv(np.eye(3)-rot)@(target-rot@e);av=np.array(axis);h+=av*(np.dot(e,av)-np.dot(h,av));move_origin(j,h);j['hingeAxisModel']=list(axis)
 row['closedSeat']={'front':float(closedFront),'ridge':float(closedCrest),'slope':float(slope),'capLift':float(lift)}
 print('SEAT',name,row['closedSeat'],flush=True)
# Mirrored hulls share an exact mechanical datum. Avoid selecting a different
# extremal vertex on a beveled edge because of source floating-point noise.
for i in range(1,5):
 for k in range(3):
  for left,right in [('Port','Starboard'),('Starboard','Port')]:
   p=bpy.data.objects[f'SideBattery_{i}_Port_Shutter_{left}_{k:02}'];j=bpy.data.objects[f'SideBattery_{i}_Starboard_Shutter_{right}_{k:02}'];h=(inv@p.matrix_world).translation;move_origin(j,(-h.x,h.y,h.z));x,y,z=p['hingeAxisModel'];j['hingeAxisModel']=[-x,y,z];j['closedAngleDegrees']=-p['closedAngleDegrees']
# The bow has a shorter original trough. Keep its rear crown/trunnion seat,
# and fit just the distal tube inside the original deployed cap's sweep.
gun=bpy.data.objects['Axial_Bow_Barrel']
if not gun.get('sourceCapTipFit'):
 row=report['Axial_Bow'];C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes']);B=Q[:,1];direction=np.array(gun['sourceBoreDirectionModel']);cp=next(c for c in gun.children if c.type=='MESH');M=inv@cp.matrix_world;Mi=M.inverted();ps=np.array([M@v.co for v in cp.data.vertices]);q=(ps-C)@Q;limit=row['frontOpen'][0][1]-1.5;amount=max(0,(q[:,1].max()-limit)/np.dot(direction,B));along=ps@direction;weight=np.clip((along-along.max()+9)/9,0,1)
 for v,point,w in zip(cp.data.vertices,ps,weight):v.co=Mi@Vector(point-direction*amount*w)
 cp.data.update();gun['sourceCapTipFit']=float(amount);print('BOW TIP FIT',amount,flush=True)
bpy.context.view_layer.update();basis=Matrix.Rotation(-math.pi/2,4,'X');nodes=[]
for o in [A]+[o for o in s.objects if o.get('staticJoint')]:
 mat=basis@o.matrix_local@basis.inverted();nodes.append({'name':o.name,'parent':o.parent.name if o.parent else None,'matrix':[mat[r][c]for c in range(4)for r in range(4)],'extras':dict(o.items())})
(out/'rig-nodes.json').write_text(json.dumps(nodes,default=lambda x:list(x)),encoding='utf8');(out/'source-covers.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.10.0.blend'),compress=True)
