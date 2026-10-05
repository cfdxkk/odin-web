"""Check restored side singles and their real meshes through the web poses."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text(encoding='utf8'))
def points(o):return np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])
def ease(a,b,d):t=max(0,min(1,(d-a)/(b-a)));return t*t*(3-2*t)
report={}
for name in [f'SideBattery_{i}_{s}'for i in[2,4]for s in['Starboard','Port']]:
 C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes'])
 gun=bpy.data.objects[name];cap=bpy.data.objects[name+'_FrontCap'];leaves=[bpy.data.objects[f'{name}_Shutter_{s}_{i:02}' ]for s in['Port','Starboard']for i in range(3)]
 # Rebuild the sealing return's original outer faces with consistent winding.
 seal=bpy.data.objects[name+'_FrontCap_SealingReturns'];old=seal.data
 coords=[v.co.copy()for v in old.vertices[:32]];fs=[]
 for f in old.polygons[:8]:
  face=tuple(f.vertices);model=np.array([inv@seal.matrix_world@coords[i]for i in face]);local=(model-C)@Q
  normal=np.cross(local[1]-local[0],local[2]-local[0])
  if local[:,0].mean()<0 and (normal[0]>1e-5 or normal[2]<-1e-5):face=tuple(reversed(face))
  fs.append(face)
 me=bpy.data.meshes.new(old.name+'_Consistent');me.from_pydata(coords,[],fs);me.materials.append(bpy.data.materials['Odin_Paint_Light']);me.materials.append(bpy.data.materials['Odin_Turret_Interior_DeepRed']);seal.data=me
 mod=seal.modifiers.new('Sealing gauge','SOLIDIFY');mod.thickness=.10;mod.offset=-1;mod.material_offset=1;bpy.context.view_layer.objects.active=seal;bpy.ops.object.modifier_apply(modifier=mod.name)
 # Each bank keeps its original lower contact edge. The covers never scale.
 origins={j:j.location.copy()for j in[gun,cap]+leaves}
 meshes=[c for j in[gun,cap]+leaves for c in j.children if c.type=='MESH']
 references={o:np.array(o.matrix_local).copy()for o in meshes}
 def pose(d):
  for j in leaves:
   angle=float(j['closedAngleDegrees'])-np.sign(j['closedAngleDegrees'])*float(j['openingTravelDegrees'])*ease(j['openStart'],j['openEnd'],d)
   j.rotation_mode='QUATERNION';j.rotation_quaternion=Quaternion(Vector(j['hingeAxisModel']),math.radians(angle))
  amount=ease(gun['sourceMotionStart'],gun['sourceMotionEnd'],d);parent=Quaternion(gun['sourceParentRotationWXYZ']);start=parent@Euler(gun['sourceEulerStart'],'XYZ').to_quaternion()
  current=parent@Euler([a+(b-a)*amount for a,b in zip(gun['sourceEulerStart'],gun['sourceEulerEnd'])],'XYZ').to_quaternion();turn=current@start.inverted()
  if gun['sourceMirror']<0:turn.y=-turn.y;turn.z=-turn.z
  gun.rotation_mode='QUATERNION';gun.rotation_quaternion=turn
  move=np.array(cap['slideVector'])+np.array(cap['clearanceLiftVector'])*ease(0,.08,d)+np.array(cap['advanceVector'])*ease(.10,.23,d)+np.array(cap['parkingSettleVector'])*ease(.24,.26,d)
  cap.location=origins[cap]+Vector(move);bpy.context.view_layer.update()
 def tree(objects):
  vs=[];fs=[]
  for o in objects:
   p=points(o);base=len(vs);vs.extend(Vector(v)for v in p);fs.extend(tuple(base+i for i in f.vertices)for f in o.data.polygons)
   o.data.calc_loop_triangles()
   # Replace the polygon list with explicit triangles so the BVH indices
   # also identify the triangles used in the geometric intersection check.
   del fs[-len(o.data.polygons):]
   fs.extend(tuple(base+i for i in t.vertices)for t in o.data.loop_triangles)
  cloud=np.array(vs);triangles=cloud[np.array(fs,dtype=np.int32)]
  return BVHTree.FromPolygons(vs,fs,all_triangles=True,epsilon=0.),triangles
 def intersections(a,b):
  hits=a[0].overlap(b[0])
  if not hits:return 0
  ia,ib=np.array(hits,dtype=np.int32).T;ta=a[1][ia];tb=b[1][ib]
  ea=np.roll(ta,-1,axis=1)-ta;eb=np.roll(tb,-1,axis=1)-tb
  na=np.cross(ea[:,0],ea[:,1]);nb=np.cross(eb[:,0],eb[:,1])
  axes=np.concatenate([na[:,None],nb[:,None],np.cross(ea[:,:,None],eb[:,None,:]).reshape(-1,9,3),np.cross(na[:,None],ea),np.cross(nb[:,None],eb)],axis=1)
  size=np.linalg.norm(axes,axis=2);pa=np.einsum('nac,nvc->nav',axes,ta);pb=np.einsum('nac,nvc->nav',axes,tb)
  # BVH.overlap is a broad-phase query: oblique triangles' bounding boxes
  # overlap even when their surfaces are separate. Test the actual triangles
  # on all separating axes, including in-plane axes for coplanar triangles.
  overlap=np.minimum(pa.max(2),pb.max(2))-np.maximum(pa.min(2),pb.min(2))
  separated=(size>1e-8)&(overlap<-size*1e-5)
  return int(np.sum(~separated.any(1)))
 collisions=[]
 for d in [i/100 for i in range(101)]:
  pose(d);barrel=tree([gun.children[0]])
  touching=[]
  for j in[cap]+leaves:
   hits=intersections(barrel,tree([o for o in j.children if o.type=='MESH']))
   if hits:touching.append([j.name,hits])
  if touching:collisions.append({'progress':d,'contacts':touching})
  for o in meshes:assert np.max(abs(references[o]-np.array(o.matrix_local)))<.0002,('Non-rigid armor geometry',o.name)
 pose(0)
 minimum=[];gp=(points(gun.children[0])-C)@Q
 for j in leaves:
  shell=bpy.data.objects[j.name+'_OuterSkin'];p=(points(shell)-C)@Q;roof=p[:6];side=1 if p[:,0].mean()>0 else-1
  cloud=gp[(gp[:,0]*side>0)&(gp[:,1]>roof[:,1].min())&(gp[:,1]<roof[:,1].max())]
  tri=roof[[0,1,3,4]];plane=np.linalg.lstsq(np.c_[tri[:,:2],np.ones(4)],tri[:,2],rcond=None)[0]
  minimum.append(float(np.min(np.c_[cloud[:,:2],np.ones(len(cloud))]@plane-cloud[:,2])))
 report[name]={'poses':101,'barrelArmorContacts':collisions,'closedRoofVerticalGaps':minimum,'rigidChildren':len(meshes)}
 for j in[gun]+leaves:j.rotation_quaternion=Quaternion((1,0,0,0))
 cap.location=origins[cap];bpy.context.view_layer.update()
(root/'docs/review/v0.11.24/mesh-clearance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.24.blend'),compress=True)
print('BARREL_ARMOR_CONTACTS',[(n,len(r['barrelArmorContacts']),min(r['closedRoofVerticalGaps']))for n,r in report.items()],flush=True)
