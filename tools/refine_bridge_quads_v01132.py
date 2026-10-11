"""Keep source quad geometry; shorten tubes to prior 11% and seat petals radially."""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix

root=Path(__file__).resolve().parents[1]
review=root/'docs/review/v0.11.32';review.mkdir(parents=True,exist_ok=True)
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
fit=json.loads((root/'docs/review/v0.11.31/source-restoration.json').read_text())
fit['version']='0.11.32'
def ease(a,b,d):
 t=max(0,min(1,(d-a)/(b-a)));return t*t*(3-2*t)
reference=.11
reference_compact=1-ease(.03,.18,reference)
travel=32*reference_compact
fit['tubeReference']={'version':'0.11.31','progress':reference,'previousTravel':32.,'previousCompactAmount':reference_compact,'newTravel':travel}
for side,sign in [('Port',-1),('Starboard',1)]:
 quad=fit['quads'][side]
 center=np.array(quad['sourceGunOrigin']);center[1]=quad['sourceCarriageClosed'][1]
 for row in quad['quadrants']:
  arm=bpy.data.objects[f"PDC_{side}_Arm_{row['quadrant']}"]
  arm['stowTravel']=travel;arm['slideVector']=[-sign*travel,0.,0.]
  arm['stowReferenceVersion']='0.11.31';arm['stowReferenceProgress']=reference
  row['tubeSlide']=list(arm['slideVector'])
  k=row['quadrant'];cradle=bpy.data.objects[f'PDC_{side}_Cradle_{k}']
  ys=1 if k<2 else-1;zs=1 if k%2==0 else-1
  cradle['compactVector']=[0.,1.35*ys,.30*zs];cradle['compactLead']=2.5
  guide=bpy.data.objects.new(f'PDC_{side}_CradleGuide_{k}',None);bpy.context.scene.collection.objects.link(guide)
  guide.parent=cradle;guide.matrix_parent_inverse=Matrix.Identity(4);guide.matrix_basis=Matrix.Identity(4)
  guide['staticJoint']=True;guide['system']='quad-cradle-guide';guide['compactVector']=[0.,-.75*ys,0.]
  guide['compactStart']=.03;guide['compactEnd']=.18;guide['compactLead']=2.5
  fork=bpy.data.objects[f'PDC_{side}_FixedFork_{k}'];local=fork.matrix_basis.copy()
  fork.parent=guide;fork.matrix_parent_inverse=Matrix.Identity(4);fork.matrix_basis=local
  row['compactVector']=list(cradle['compactVector']);row['guideCompensation']=list(guide['compactVector'])
 for row in quad['petalSeats']:
  joint=bpy.data.objects[row['joint']];skin=joint.children[0]
  p=np.array((inv@joint.matrix_world).translation)
  source_points=np.array([(inv@skin.matrix_world)@v.co for v in skin.data.vertices])
  q=Quaternion(row['compactRotationWXYZ']);R=np.array(q.to_matrix())
  n=np.array(row['receiverNormal']);target=np.array(row['receiverPoints'][0])
  outer=[]
  for f,i in zip(skin.data.polygons,skin['sourceFaceIds']):
   if i not in row['sourceOuterFaces']:continue
   points=source_points[list(f.vertices)]
   area=np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0]))/2
   outer.append((points,area))
  centroid=sum((p+(points-p)@R.T).mean(0)*area for points,area in outer)/sum(a for ps,a in outer)
  radial=center-p;radial[0]=0
  amount=-np.dot(n,centroid-target)/np.dot(n,radial)
  assert 0<amount<.5,(joint.name,amount)
  shift=radial*amount;assert shift[0]==0
  closed=p+(source_points-p)@R.T+shift
  errors=[abs(float(np.dot(n,v-target)))for points,area in outer for v in p+(points-p)@R.T+shift]
  joint['compactVector']=shift.tolist();joint['sourceCenteredPetal']=True;joint['quadCenter']=center.tolist()
  joint['alignStart']=.20;joint['alignEnd']=.40;joint['compactLead']=2.5
  for prop in ['clearanceVector','clearanceStart','clearanceEnd']:
   if prop in joint:del joint[prop]
  row.update(compactVector=shift.tolist(),quadCenter=center.tolist(),radialFraction=amount,
             closedPrimarySurfaceErrors=errors,maxPrimarySurfaceError=max(errors),
             closedBounds=[closed.min(0).tolist(),closed.max(0).tolist()],axialTravel=0.,clearanceStroke=0.,
             alignStart=.20,alignEnd=.40)
fit['petalMotion']='Original open skins align with adjacent hull normals during carriage seating, then contract directly toward the cross-section center after the frame-30 stop. No axial slide or clearance detour.'
fit['centerTiming']={'start':.03,'end':.18,'lead':2.5,'progress':'c + lead*c*(1-c)**2','tubeAxialProgress':'c','monotonic':True}
assert not bpy.data.actions
asset['version']='0.11.32'
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.32.blend'),compress=True)
(review/'source-restoration.json').write_text(json.dumps(fit,indent=2),encoding='utf8')
print('CENTERED_QUAD_STOW',travel,[(s,[r['compactVector']for r in q['petalSeats']])for s,q in fit['quads'].items()],flush=True)
