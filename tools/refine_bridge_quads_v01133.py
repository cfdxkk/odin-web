"""Translation-only original petals, with fixed hull lips joined to their edges.

Run on v0.11.32. All original petal vertices, UVs and static orientations
remain intact; only the adjoining fixed hull lip is fitted to the closed edge.
The petal X coordinate is invariant for every vertex, not just its origin.
"""
import bpy,json,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parents[1]
review=root/'docs/review/v0.11.33';review.mkdir(parents=True,exist_ok=True)
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
fit=json.loads((root/'docs/review/v0.11.32/source-restoration.json').read_text())
planes=json.loads((root/'tests/fixtures/bridge-quad-hull-lips-v01133.json').read_text())['starboardLips']
planes={p['face']:p for p in planes}
fixed=bpy.data.objects['holo.001'];M=inv@fixed.matrix_world
fixed_points=np.array([M@v.co for v in fixed.data.vertices]);original_fixed=fixed_points.copy()
fit['version']='0.11.33';fit['fixedSeamEdits']=[];fit['fixedSeamMesh']=fixed.name
fit['unchangedOtherMeshes']-=1
for side,sign in [('Port',-1),('Starboard',1)]:
 for row in fit['quads'][side]['quadrants']:
  k=row['quadrant'];ys=1 if k<2 else-1;zs=1 if k%2==0 else-1
  cradle=bpy.data.objects[f'PDC_{side}_Cradle_{k}'];guide=bpy.data.objects[f'PDC_{side}_CradleGuide_{k}']
  cradle['compactVector']=[0.,2.*ys,.30*zs];guide['compactVector']=[0.,-1.4*ys,0.]
  row['compactVector']=list(cradle['compactVector']);row['guideCompensation']=list(guide['compactVector'])
 for k,row in enumerate(fit['quads'][side]['petalSeats']):
  joint=bpy.data.objects[row['joint']];skin=joint.children[0]
  source_points=np.array([(inv@skin.matrix_world)@v.co for v in skin.data.vertices])
  ids=list(skin['sourceVertexIds']);outer_ids={v for f,i in zip(skin.data.polygons,skin['sourceFaceIds'])if i in row['sourceOuterFaces']for v in f.vertices}
  tip=max(outer_ids,key=lambda v:sign*source_points[v,0])
  corner=max(outer_ids-{tip},key=lambda v:sign*source_points[v,0])
  A=source_points[corner];B=source_points[tip]
  # The visible forward hull lip adjoining this original petal.
  lip=planes[[252845,11134,252962,46735][k]]
  ps=np.array(lip['points'])*np.array([sign,1,1])
  # Exterior edge: upper skins use the highest two lip vertices, lower
  # skins the lowest two. The bevel underneath retains its original width.
  midpoint=(min(sign*ps[:,0])+max(sign*ps[:,0]))/2
  choose=max if k%2 else min
  u=choose((p for p in ps if sign*p[0]<midpoint),key=lambda p:p[2])
  w=choose((p for p in ps if sign*p[0]>midpoint),key=lambda p:p[2])
  direction=(B-A)/(B[0]-A[0])
  ray=lambda x:A+direction*(x-A[0])
  dz=float(np.mean([p[2]-ray(p[0])[2]for p in [u,w]]))
  shift=np.array([0.,0.,dz])
  assert (dz<0)==bool(k%2),(side,k,dz)
  U=B+shift;W=ray(w[0])+shift
  delta_u=U-u;delta_w=W-w
  edited=[]
  for p in ps:
   dist=np.linalg.norm(original_fixed-p,axis=1);v=int(dist.argmin())
   assert dist[v]<.00002,(side,k,p,dist[v])
   a=np.clip((p[0]-u[0])/(w[0]-u[0]),0.,1.)
   new=p+delta_u*(1-a)+delta_w*a
   fixed.data.vertices[v].co=M.inverted()@Vector(new)
   edited.append(v)
   fit['fixedSeamEdits'].append({'vertex':v,'before':p.tolist(),'after':new.tolist(),'side':side,'quadrant':k})
  joint['compactVector']=shift.tolist();joint['translationOnly']=True
  joint['lockedHullAxis']='X';joint['sourceCenteredPetal']=True
  # Straight vertical clearance while the full source tubes pass the hull.
  # The source-open endpoint is recovered once the carriage clears the lip.
  joint['translationClearanceZ']=.25 if k%2 else-.25
  joint['translationClearanceReleaseStart']=.35;joint['translationClearanceReleaseEnd']=.60
  joint['petalPackingExponent']=2.
  for prop in ['compactRotationWXYZ','alignStart','alignEnd','clearanceVector','clearanceStart','clearanceEnd']:
   if prop in joint:del joint[prop]
  row['compactVector']=shift.tolist();row['translationOnly']=True;row['lockedHullAxis']='X'
  row['translationClearanceZ']=joint['translationClearanceZ']
  row['translationClearanceReleaseStart']=.35;row['translationClearanceReleaseEnd']=.60
  row['petalPackingExponent']=2.
  row['clearanceStroke']=.25
  row['closedBounds']=[(source_points+shift).min(0).tolist(),(source_points+shift).max(0).tolist()]
  row['forwardSeam']={'originalHullFace':lip['face'],'fixedMesh':fixed.name,
                     'fixedLipVertices':edited,'armorCornerVertex':corner,'armorTipVertex':tip,
                     'sourceArmorVertexIds':[ids[corner],ids[tip]],
                     'closedArmorEdge':[list(A+shift),list(B+shift)],
                     'closedHullEdge':[list(U),list(W)],'targetEndpointGap':0.,'targetLineAngle':0.}
  for prop in ['compactRotationWXYZ','alignStart','alignEnd','guideSeatDegrees','radialFraction','closedPrimarySurfaceErrors','maxPrimarySurfaceError','sourceReceiverFace','receiverPoints','receiverNormal']:
   row.pop(prop,None)
fixed.data.update();fixed['quadTranslationSeamFit']=True;fixed['quadSeamEditedVertices']=[e['vertex']for e in fit['fixedSeamEdits']]
fit['petalMotion']='Original open petals translate vertically toward the quad center with no rotation and no X displacement. Their original forward edges join fitted stationary hull lips at NAV.'
fit['seamFit']='Only the four vertices of each adjoining fixed lip are adjusted; each original 26-vertex petal and its static orientation remain unchanged.'
fit['packingClearance']='The original bearing/tube groups pack 2.0 units in Y and 0.30 in Z; original fork guides retain the 0.60 Y stroke. Petals follow the squared center clock in the same final interval, closing after the tubes clear their edges. They use a 0.25 vertical passage allowance during carriage travel and recover the original open endpoint.'
assert len(fit['fixedSeamEdits'])==32 and len({r['vertex']for r in fit['fixedSeamEdits']})==32
assert not bpy.data.actions
asset['version']='0.11.33'
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.33.blend'),compress=True)
(review/'source-restoration.json').write_text(json.dumps(fit,indent=2),encoding='utf8')
print('TRANSLATION_ONLY_PETALS',[(s,[row['compactVector']for row in q['petalSeats']])for s,q in fit['quads'].items()],'fixedLipVertices',len(fit['fixedSeamEdits']),flush=True)
