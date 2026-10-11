"""Continue axial crowns and fit accepted flank covers to side singles 2/4.

Input: v0.11.22. Original guns, fixed hulls and source actions stay intact.
The new side leaves retain the accepted SideBattery_1 mesh topology/UVs;
their nose covers retain each mount's original separated source shell.
"""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Quaternion,Vector,Matrix

root=Path(__file__).resolve().parents[1]
asset=bpy.data.objects['Odin_Asset'];assert asset['version']=='0.11.22'
inv=asset.matrix_world.inverted()
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text())
review=root/'docs/review/v0.11.23';review.mkdir(parents=True,exist_ok=True)
report={'axial':{},'flank':{}};changed=set();removed=set();moved_joints=set()
red=bpy.data.materials['Odin_Armor_Reinforcement']

def points(obj):return np.array([(inv@obj.matrix_world)@v.co for v in obj.data.vertices])
def digest(obj):
 h=hashlib.sha256();co=np.empty(len(obj.data.vertices)*3,dtype=np.float32)
 obj.data.vertices.foreach_get('co',co);h.update(co.tobytes())
 for f in obj.data.polygons:
  h.update(np.array(tuple(f.vertices),dtype=np.int32).tobytes())
  h.update(obj.data.materials[f.material_index].name.encode())
 return h.hexdigest()
before={o.name:digest(o) for o in bpy.context.scene.objects if o.type=='MESH'}
joints={o.name:np.array(o.matrix_local).copy() for o in bpy.context.scene.objects if o.get('staticJoint')}

def frame(name):
 f=frames[name];C=np.array(f['frameOrigin']);Q=np.array(f['frameAxes'])
 if name=='Axial_Keel':C+=np.array(bpy.data.objects[name+'_Mount']['fixedAssemblyOffsetModel'])
 return C,Q

def rotation(j):return np.array(Quaternion(Vector(j['hingeAxisModel']),math.radians(j['closedAngleDegrees'])).to_matrix())
def set_points(obj,model):
 inverse=(inv@obj.matrix_world).inverted()
 for v,p in zip(obj.data.vertices,model):v.co=inverse@Vector(p)
 obj.data.update();changed.add(obj.name)

def red_inside(obj,fitted,rear,fore):
 if red.name not in obj.data.materials:obj.data.materials.append(red)
 red_index=obj.data.materials.find(red.name)
 def gap(p):
  x=abs(p[0]);t=.5
  for _ in range(12):
   xs=rear[:,0]*(1-t)+fore[:,0]*t;k=0 if x<=xs[1] else 1
   u=(x-xs[k])/(xs[k+1]-xs[k])
   lo=rear[k]*(1-u)+rear[k+1]*u;hi=fore[k]*(1-u)+fore[k+1]*u
   t=np.clip((p[1]-lo[1])/(hi[1]-lo[1]),-.01,1.01)
  return p[2]-(lo[2]*(1-t)+hi[2]*t)
 gaps=np.array([gap(p) for p in fitted])
 for f in obj.data.polygons:
  # Source shells contain inconsistent winding and double-sided paint.
  # The inward skin is identified by its offset below the exterior roof,
  # so an inverted source normal cannot recolor the visible outer face.
  g=gaps[list(f.vertices)]
  if np.mean(g)<-.06 and np.max(g)<-.005:f.material_index=red_index
 obj.data.update()

def reprofile_half_shell(local,half_specs,rear,fore):
 """Retain the original folded returns relative to its two end profiles."""
 result=local.copy()
 for sign,rear_ids,front_ids,rear_anchors,front_anchors in half_specs:
  for ids,anchors,target in [(rear_ids,rear_anchors,rear),(front_ids,front_anchors,fore)]:
   source=local[anchors].copy();source[:,0]=abs(source[:,0])
   for i in ids:
    p=local[i].copy();x=abs(p[0]);k=0 if x<=source[1,0] else 1
    t=(x-source[k,0])/(source[k+1,0]-source[k,0])
    old_surface=source[k]+t*(source[k+1]-source[k])
    new_surface=target[k]+t*(target[k+1]-target[k])
    residual=p-old_surface;residual[0]=0
    result[i]=new_surface+residual;result[i,0]*=sign
 return result

# A single crown line crosses both the shutters and nose shell. The fixed
# receiver's original diagonal and the accepted breech height are its datums.
rear_ids={0,1,4,7,8,11,12,14,16,20,21,23,24,26}
front_ids=set(range(28))-rear_ids
for name in ['Axial_Stern','Axial_Keel']:
 C,Q=frame(name);cap=bpy.data.objects[name+'_FrontCap'];skin=bpy.data.objects[name+'_FrontCap_Skin']
 shift=np.array(cap['slideVector'])+np.array(cap['settleVector'])
 local=(points(skin)+shift-C)@Q
 fore=np.array(cap['receiverForeSeamLocal']);start=-16.25+(0 if name.endswith('Stern') else .14)
 rear_z=5.22-(0 if name.endswith('Stern') else .54)
 rake=(fore[0,2]-rear_z)/(fore[0,1]-start)
 old_rake=.20/26.78
 for side in ['Port','Starboard']:
  for i in range(3):
   j=bpy.data.objects[f'{name}_Shutter_{side}_{i:02d}'];H=np.array((inv@j.matrix_world).translation);R=rotation(j)
   backing=bpy.data.objects[j.name+'_FittedBacking']
   roof=(H+(points(backing)-H)@R.T-C)@Q
   old=roof.copy()
   for k in [1,2,4,5]:
    dz=rear_z+rake*(roof[k,1]-start)-roof[k,2]
    roof[k,2]+=dz;roof[k+6,2]+=dz
   set_points(backing,H+(C+roof@Q.T-H)@R)
   j['closedEndEdgesModel']=[[(C+Q@roof[k]).tolist() for k in pair] for pair in [(0,2),(3,5)]]
   j['closedCrownLineLocal']=[start,rear_z,rake]
   grate=bpy.data.objects[j.name+'_Skin'];g=(H+(points(grate)-H)@R.T-C)@Q
   # Carry the retained interior relief with the roof while its contact edge
   # remains on the original fixed hull lip.
   width=max(abs(old[[0,3],0]));flat=max(abs(old[[1,4],0]));t=np.clip((width-abs(g[:,0]))/(width-flat),0,1)
   g[:,2]+=(rake-old_rake)*(g[:,1]-start)*t
   set_points(grate,H+(C+g@Q.T-H)@R)
 rear=np.array([(np.array(p)-C)@Q for p in cap['closedRearProfileModel']])
 old_rear=rear.copy();rear[:2,2]=rear_z+rake*(rear[:2,1]-start)
 specs=[(s,[k+b for k in rear_ids],[k+b for k in front_ids],[b,b+8,b+4],[b+3,b+9,b+5]) for s,b in [(1,0),(-1,28)]]
 fitted=reprofile_half_shell(local,specs,rear,fore)
 set_points(skin,C+fitted@Q.T-shift)
 red_inside(skin,fitted,rear,fore)
 cap['closedRearProfileModel']=[(C+Q@p).tolist() for p in rear]
 cap['closedCrownLineLocal']=[start,rear_z,rake]
 cap['originalClosedBounds']=[fitted.min(0).tolist(),fitted.max(0).tolist()]
 cap['originalOpenBounds']=[(fitted-shift@Q).min(0).tolist(),(fitted-shift@Q).max(0).tolist()]
 report['axial'][name]={'crownDatum':[start,rear_z],'crownRakeBefore':old_rake,'crownRakeAfter':float(rake),'capRearBefore':old_rear.tolist(),'capRearAfter':rear.tolist(),'fixedReceiverProfile':fore.tolist()}

# Read the accepted grates and opaque roofs before changing any target bays.
template='SideBattery_1_Starboard';TC,TQ=frame(template)
carriage=bpy.data.objects[template+'_Carriage'];carriage_closed=np.array(carriage['liftVector'])+np.array(carriage['slideVector'])
sources=[]
for i in range(3):
 j=bpy.data.objects[f'{template}_Shutter_Port_{i:02d}'];H=np.array(j['sourceHingeLine']);R=rotation(j)
 offset=carriage_closed if j.parent==carriage else np.zeros(3)
 parts={c.name.rsplit('_',1)[-1]:(c,(H+(points(c)-H)@R.T+offset-TC)@TQ) for c in j.children if c.type=='MESH'}
 assert set(parts)=={'Skin','FittedBacking'}
 sources.append(parts)

def leaf_remap(p,roof,a,b,flat,center,zline):
 # Resolve the source raked roof at this transverse location, so the
 # original relief and shell thickness stay inside the fitted exterior.
 aft=roof[[2,1,0]];fore=roof[[5,4,3]];x=abs(p[0]);t=.5
 # Source flank trapezoids have different transverse coordinates at their
 # two ends. Resolve that bilinear surface rather than using its aft width
 # for both ends (which would create a seam step after remapping).
 for _ in range(12):
  xs=abs(aft[:,0])*(1-t)+abs(fore[:,0])*t;col=0 if x<=xs[1] else 1
  u=np.clip((x-xs[col])/(xs[col+1]-xs[col]),-.01,1.01)
  lo=aft[col]*(1-u)+aft[col+1]*u;hi=fore[col]*(1-u)+fore[col+1]*u
  t=np.clip((p[1]-lo[1])/(hi[1]-lo[1]),-.005,1.005)
 edge=a*(1-t)+b*t;y=edge[1];ridge=zline[1]+zline[2]*(y-zline[0])
 target_x=[center,flat,abs(edge[0])]
 target_z=[ridge,ridge,edge[2]]
 tx=target_x[col]*(1-u)+target_x[col+1]*u
 tz=target_z[col]*(1-u)+target_z[col+1]*u
 return np.array([tx,y,tz+.8*(p[2]-(lo[2]*(1-t)+hi[2]*t))])

def clone_mesh(source,name,parent,opened):
 mesh=source.data.copy();mesh.name=name
 obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
 obj.parent=parent;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_local=Matrix.Identity(4)
 bpy.context.view_layer.update();set_points(obj,opened)
 obj['sourceGeometry']=True;obj['armorTemplate']=source.name
 return obj

def erase_mesh(obj):
 removed.add(obj.name);data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
 if data.users==0:bpy.data.meshes.remove(data)

def add_lips(name,C,Q,profile,start,end,width,height):
 verts=[];faces=[];materials=[]
 ys=[start]+[float(p[1]) for p in profile if start<p[1]<end]+[end]
 for sign in [-1,1]:
  for a,b in zip(ys,ys[1:]):
   def low(y):return np.array([sign*np.interp(y,profile[:,1],profile[:,0]),y,np.interp(y,profile[:,1],profile[:,2])])
   outer=[low(a),low(b),np.array([sign*(width+.045),b,height-.08]),np.array([sign*(width+.045),a,height-.08])]
   inner=[p+np.array([-sign*.10,0,-.045]) for p in outer];base=len(verts)
   verts += [C+Q@p for p in outer+inner]
   fs=[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
   if sign<0:fs=[tuple(reversed(f)) for f in fs]
   faces += [tuple(base+i for i in f) for f in fs];materials += [0,1,0,0,0,0]
 mesh=bpy.data.meshes.new(name+'_FixedSlotLips');mesh.from_pydata(verts,[],faces)
 mesh.materials.append(bpy.data.materials['Odin_Paint_Light']);mesh.materials.append(bpy.data.materials['Odin_Turret_Interior_DeepRed'])
 obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.scene.collection.objects.link(obj);obj.parent=asset;obj.matrix_local=Matrix.Identity(4)
 for face,mat in zip(mesh.polygons,materials):face.material_index=mat
 mesh.update();obj['stationaryHullLip']=True;obj['hingeClearanceModel']=.08;changed.add(obj.name)

hull=bpy.data.objects['holo.001'];hull_points=points(hull)
for number in [2,4]:
 for hull_side in ['Port','Starboard']:
  name=f'SideBattery_{number}_{hull_side}';C,Q=frame(name);p=(hull_points-C)@Q
  cap=bpy.data.objects[name+'_FrontCap'];cap_skin=bpy.data.objects[name+'_FrontCap_Skin']
  offset=np.array(cap['slideVector'])+np.array(cap['settleVector']);old_cap=(points(cap_skin)+offset-C)@Q
  assert len(old_cap)==36
  # The unmodified hull center strip and its triangular shoulder are the
  # actual front receiver, rather than the older raised proxy cap datum.
  def nearest(target,side):
   candidates=p[p[:,0]*side>0].copy();candidates[:,0]=abs(candidates[:,0])
   return candidates[np.argmin(np.linalg.norm(candidates-target,axis=1))]
  crest=np.mean([nearest(np.array([.344,21.892,5.03]),s) for s in [-1,1]],axis=0)
  outer=np.mean([nearest(np.array([1.235,20.596,3.77]),s) for s in [-1,1]],axis=0)
  center=.015;flat=.45
  fore=np.array([[center,crest[1]-.02,crest[2]],[crest[0],crest[1]-.02,crest[2]],[outer[0],outer[1]-.02,outer[2]]])
  # One rail per side interpolates the accepted aft contact to the fixed
  # front wall. All six new roofs therefore have continuous full-width seams.
  rail=[];rear_height=[]
  for side,sgn in [('Port',-1),('Starboard',1)]:
   first=bpy.data.objects[f'{name}_Shutter_{side}_00'];last=bpy.data.objects[f'{name}_Shutter_{side}_02']
   a=(np.array(first['hingeEdgeModel'][0])-C)@Q
   b=(np.array(last['hingeEdgeModel'][1])-C)@Q
   rail.append((a,b))
   crown=bpy.data.objects[first.name+'_Crown'];H=np.array((inv@first.matrix_world).translation);R=rotation(first)
   q=(H+(points(crown)-H)@R.T-C)@Q;rear_height.append(float(np.mean(q[[2,3],2])))
  start=float(np.mean([a[1] for a,b in rail]));end=float(np.mean([b[1] for a,b in rail]))
  height=float(np.mean(rear_height));rake=(fore[0,2]-height)/(fore[0,1]-start)
  zline=[start,height,float(rake)];segments=[start,-8.244, .520,end]
  # The fixed front wall has a near-identical lip on both hull sides.
  front_wall_z=3.60;front_width=2.55
  common_a=np.array([front_width,start,front_wall_z]);common_b=np.array([front_width,end,front_wall_z])
  targets=[[2.55,-17.084,3.386],[2.503,-8.556,3.497],[2.500,-8.282,1.832],[2.454,.293,1.944],[2.500,.32,1.943],[2.500,9.45,1.984]]
  wall_profile=np.array([np.mean([nearest(np.array(t),s) for s in [-1,1]],axis=0) for t in targets])
  wall_profile=wall_profile[np.argsort(wall_profile[:,1])]
  add_lips(name,C,Q,wall_profile,start,end,front_width,front_wall_z)
  def edge(y):
   t=(y-start)/(end-start);return common_a*(1-t)+common_b*t
  row={'template':template,'crownLine':zline,'segments':segments,'foreProfile':fore.tolist(),'fixedLipLowerProfile':wall_profile.tolist(),'fixedLipHingeClearance':.08,'leaves':[]}
  for side,sgn in [('Port',-1),('Starboard',1)]:
   for i in range(3):
    j=bpy.data.objects[f'{name}_Shutter_{side}_{i:02d}'];a=edge(segments[i]);b=edge(segments[i+1]);a[0]*=sgn;b[0]*=sgn
    H=C+Q@a;axis=Q@(b-a);axis/=np.linalg.norm(axis)
    for child in list(j.children):
     assert child.type=='MESH';erase_mesh(child)
    j.location=(j.parent.matrix_world.inverted()@asset.matrix_world@Vector(H)).to_tuple()
    j['hingeAxisModel']=axis.tolist();j['sourceHingeLine']=H.tolist();j['closedAngleDegrees']=-sgn*150.
    j['openingTravelDegrees']=95.;j['hingeEdgeModel']=[(C+Q@a).tolist(),(C+Q@b).tolist()]
    j['openStart']=.26+.035*i;j['openEnd']=.53+.055*i
    j['armorTemplate']=f'{template}_Shutter_Port_{i:02d}';j['armorAnimationTemplate']=f'Axial_Stern_Shutter_{side}_{i:02d}'
    j['fittedCrownWidthModel']=2*flat;j['closedCrownLineLocal']=zline
    moved_joints.add(j.name);bpy.context.view_layer.update();R=rotation(j)
    parts=sources[i];roof=parts['FittedBacking'][1][:6]
    for suffix,(source,source_points) in parts.items():
     target=np.array([leaf_remap(q,roof,a,b,flat,center,zline) for q in source_points]);target[:,0]*=sgn
     opened=H+(C+target@Q.T-H)@R
     obj=clone_mesh(source,j.name+'_'+suffix,j,opened)
     if suffix=='FittedBacking':
      j['closedEndEdgesModel']=[[(C+Q@target[k]).tolist() for k in pair] for pair in [(0,2),(3,5)]]
      row['leaves'].append({'name':j.name,'rearProfile':target[:3].tolist(),'foreProfile':target[3:6].tolist(),'vertices':len(obj.data.vertices)})
  rear=np.array([[center,end+.02,height+rake*(end+.02-start)],[flat,end+.02,height+rake*(end+.02-start)],[front_width,end+.02,front_wall_z]])
  specs=[(-1,[0,3,5,6,10,13,14,16,17],[1,2,4,7,8,9,11,12,15],[10,3,0],[11,2,1]),(1,[19,20,24,25,28,31,32,34,35],[18,21,22,23,26,27,29,30,33],[31,20,19],[30,21,18])]
  fitted=reprofile_half_shell(old_cap,specs,rear,fore)
  cap['settleVector']=(-.6*Q[:,2]).tolist();cap['slideStart']=.10;cap['slideEnd']=.25;cap['settleStart']=0.;cap['settleEnd']=.08
  cap['armorAnimationTemplate']='Axial_Stern_FrontCap';cap['closedCrownLineLocal']=zline
  cap['closedRearProfileModel']=[(C+Q@v).tolist() for v in rear];cap['closedForeProfileModel']=[(C+Q@v).tolist() for v in fore]
  cap['receiverForeSeamLocal']=fore.tolist();cap['receiverForeSeamGap']=.02;cap['fullReceiverEdgeFit']=True
  new_offset=np.array(cap['slideVector'])+np.array(cap['settleVector'])
  set_points(cap_skin,C+fitted@Q.T-new_offset)
  red_inside(cap_skin,fitted,rear,fore)
  cap['originalClosedBounds']=[fitted.min(0).tolist(),fitted.max(0).tolist()]
  cap['originalOpenBounds']=[(fitted-new_offset@Q).min(0).tolist(),(fitted-new_offset@Q).max(0).tolist()]
  row['rearProfile']=rear.tolist();row['capSourceVertices']=36;row['capSourceFaces']=len(cap_skin.data.polygons)
  report['flank'][name]=row

bpy.context.view_layer.update()
for name,h in before.items():
 if name not in changed and name not in removed:assert digest(bpy.data.objects[name])==h,('Unintended mesh change',name)
for name,m in joints.items():
 if name not in moved_joints:assert np.array_equal(np.array(bpy.data.objects[name].matrix_local),m),('Unintended joint transform',name)
report.update(changedMeshes=sorted(changed),removedLegacyMeshes=len(removed),unchangedMeshes=len(before)-len(changed&set(before))-len(removed),unchangedJointTransforms=len(joints)-len(moved_joints),refittedContactJoints=sorted(moved_joints))
asset['version']='0.11.23'
(review/'geometry-fit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
output=root/'assets/blender/odin_articulated_v0.11.23.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
print('FITTED_FLANK_2_4',json.dumps({k:v for k,v in report.items() if k not in ['axial','flank','changedMeshes','refittedContactJoints']}),flush=True)
