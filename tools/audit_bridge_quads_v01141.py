"""Sweep actual Nuxt poses against source petals and adjacent complete cradles."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
# Reuse the established broad-phase BVH and triangle SAT mesh intersection test.
helper=(root/'tools/audit_bridge_quads_v01134.py').read_text().split('origins=')[0]
exec(compile(helper,str(root/'tools/audit_bridge_quads_v01134.py'),'exec'))
basis=Quaternion(Vector((1,0,0)),-math.pi/2)
rows=json.loads((root/'work/v01141-review/runtime-poses.json').read_text())
origins={o.name:o.location.copy()for o in bpy.context.scene.objects if o.get('staticJoint')}
mesh_frames={o.name:np.array(o.matrix_local).copy()for o in bpy.context.scene.objects if o.type=='MESH'}
def apply(row):
 for j in row['joints']:
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y)
  x,y,z,w=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((w,x,y,z))@basis
 bpy.context.view_layer.update()
report={s:{'poses':0,'barrelPetalContacts':[],'cradlePairContacts':[],
           'tubePairContacts':[],'maxTransverseDisplacementMismatch':0.,
           'maxTubeAdvanceBeforePetalsOpen':0.,'maxArmorVertexXChange':0.,
           'maxArmorRotationRadians':0.,'closedForwardSeams':[]}for s in ['Port','Starboard']}
apply(rows[0]);closed_tubes={o.name:o.location.copy()for o in bpy.context.scene.objects if o.name.startswith('PDC_')and o.get('sourceFullTube')}
petal_x={o.name:points(o)[:,0].copy()for o in bpy.context.scene.objects if o.type=='MESH'and 'HullPetal'in o.name}
for step,row in enumerate(rows):
 apply(row)
 for side,out in report.items():
  out['poses']+=1
  tubes=[bpy.data.objects[f'PDC_{side}_ArmMesh_{i}']for i in range(4)]
  petals=[bpy.data.objects[f'PDC_{side}_HullPetal_{i}_Skin']for i in range(4)]
  tube_trees=[tree([o])for o in tubes]
  n=intersections(tree(tubes),tree(petals))
  if n:out['barrelPetalContacts'].append({'progress':row['progress'],'triangleContacts':n})
  cradles=[tree([bpy.data.objects[f'PDC_{side}_FixedFork_{i}'],bpy.data.objects[f'PDC_{side}_RootArmor_{i}']])for i in range(4)]
  for i in range(4):
   p=petals[i];r=bpy.data.objects[f'PDC_{side}_Cradle_{i}'];t=bpy.data.objects[f'PDC_{side}_Arm_{i}']
   clock=(p.parent.location.z-origins[p.parent.name].z)/p.parent['compactVector'][2]
   mismatch=(r.location-origins[r.name])-Vector(r['compactVector'])*clock
   out['maxTransverseDisplacementMismatch']=max(out['maxTransverseDisplacementMismatch'],float(mismatch.length))
   out['maxArmorVertexXChange']=max(out['maxArmorVertexXChange'],float(np.max(abs(points(p)[:,0]-petal_x[p.name]))))
   out['maxArmorRotationRadians']=max(out['maxArmorRotationRadians'],float(p.parent.rotation_quaternion.angle))
   if row['progress']<=.18:out['maxTubeAdvanceBeforePetalsOpen']=max(out['maxTubeAdvanceBeforePetalsOpen'],float((t.location-closed_tubes[t.name]).length))
   for j in range(i+1,4):
    for kind,a,b in [('cradlePairContacts',cradles[i],cradles[j]),('tubePairContacts',tube_trees[i],tube_trees[j])]:
     n=intersections(a,b)
     if n:out[kind].append({'progress':row['progress'],'quadrants':[i,j],'triangleContacts':n})
 if step%100==0:print('SYNCHRONIZED_QUAD_SWEEP',step,len(rows),flush=True)
apply(rows[0])
for side,sign in [('Port',-1),('Starboard',1)]:
 out=report[side];tips=[]
 for i,row in enumerate(fit['quads'][side]['petalSeats']):
  p=bpy.data.objects[row['joint']].children[0];ps=points(p);seam=row['forwardSeam']
  fixed=points(bpy.data.objects[seam['fixedMesh']])[seam['fixedLipVertices']]
  a=ps[seam['armorCornerVertex']];b=ps[seam['armorTipVertex']];u=fixed[np.argmin(np.linalg.norm(fixed-b,axis=1))];w=fixed[np.argmax(fixed[:,0]*sign)]
  gap=float(np.linalg.norm(b-u));v=b-a;h=w-u
  angle=math.degrees(math.asin(min(1.,np.linalg.norm(np.cross(v,h))/np.linalg.norm(v)/np.linalg.norm(h))))
  roof=points(bpy.data.objects[seam['fixedMesh']])[row['surfaceFit']['fixedRoofVertexIds']];normal=np.cross(roof[1]-roof[0],roof[2]-roof[0]);normal/=np.linalg.norm(normal)
  surface=float(max(abs(np.dot(ps[j]-roof[0],normal))for j in row['surfaceFit']['outerMeshVertexIds']))
  assert gap<.00003 and angle<.001 and surface<.00003
  out['closedForwardSeams'].append({'quadrant':i,'endpointGap':gap,'edgeAngleDegrees':angle,'surfaceError':surface})
  tube=points(bpy.data.objects[f'PDC_{side}_ArmMesh_{i}']);tip=float((tube[:,0]*sign).max());armor_tip=float((ps[:,0]*sign).max())
  assert armor_tip-tip>.20
  tips.append({'quadrant':i,'hiddenBehindArmor':armor_tip-tip})
 out['hiddenBarrelTips']=tips
for name,matrix in mesh_frames.items():assert np.max(abs(np.array(bpy.data.objects[name].matrix_local)-matrix))<.00005,name
(root/'docs/review/v0.11.41/mesh-clearance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('QUAD_SYNCHRONIZED_CLEARANCE',[(s,len(r['barrelPetalContacts']),len(r['cradlePairContacts']),len(r['tubePairContacts']),r['maxTransverseDisplacementMismatch'])for s,r in report.items()],flush=True)
assert all(not r['barrelPetalContacts']and not r['cradlePairContacts']and not r['tubePairContacts']for r in report.values())
assert all(r['maxTransverseDisplacementMismatch']<.00003 and r['maxTubeAdvanceBeforePetalsOpen']==0 and r['maxArmorVertexXChange']==0 and r['maxArmorRotationRadians']==0 for r in report.values())
