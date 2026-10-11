"""Check corrected geometry, fixed/mobile membership and original scope."""
import bpy,json,hashlib,math,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
R=Path(__file__).resolve().parents[1]
exec((R/'tools/revise_secondary_bridge_v090.py').read_text().split('def fit_channel_nose')[0])
out=R/'work/v0111-review';rows=json.loads((R/'docs/review/v0.11.0/side-batteries.json').read_text());result={}
prefixes=tuple(rows)
def in_scope(o):
 if o.name=='Odin_Asset':return True
 while o:
  if o.name.startswith(prefixes):return True
  o=o.parent
 return False
state={}
for o in s.objects:
 if in_scope(o):continue
 h=hashlib.sha256();h.update(np.array(o.matrix_local,dtype=np.float64).tobytes())
 if o.type=='MESH':
  h.update(np.array([v.co[:]for v in o.data.vertices],dtype=np.float32).tobytes())
  h.update(str([tuple(f.vertices)for f in o.data.polygons]).encode());h.update(str([f.material_index for f in o.data.polygons]).encode());h.update(str([m.name for m in o.data.materials]).encode())
 if o.get('staticJoint'):h.update(json.dumps(dict(o.items()),sort_keys=True,default=lambda v:list(v)).encode())
 state[o.name]=h.hexdigest()
if str(A['version'])=='0.11.0':
 (out/'scope-before.json').write_text(json.dumps(state));print('BASELINE',len(state));raise SystemExit
before=json.loads((out/'scope-before.json').read_text());changed=[n for n in before if before[n]!=state.get(n)]
assert not changed,changed
hull=bpy.data.objects['holo.001'];M=inv@hull.matrix_world;hullpoints=np.array([M@v.co for v in hull.data.vertices])
for name,row in rows.items():
 C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes']);X,B,N=Q.T;gun=bpy.data.objects[name];carriage=bpy.data.objects[name+'_Carriage'];mesh=next(c for c in gun.children if c.type=='MESH')
 measured=np.array(bore(mesh,B));angle=math.degrees(math.atan2(np.linalg.norm(np.cross(measured,B)),float(measured@B)))
 assert angle<.01,(name,'actual rest bore not parallel',angle)
 tubes=[p for p in parts(mesh)if p['n']>100 and np.ptp(p['points']@B)>35]
 tube=max(tubes,key=lambda p:(p['points']@B).max());along=tube['points']@B
 ring=tube['points'][along>along.max()-.025];uv=(ring-C)@np.stack([X,N],axis=1)
 center=np.linalg.lstsq(np.c_[2*uv,np.ones(len(uv))],np.sum(uv*uv,axis=1),rcond=None)[0][:2]
 expected=(np.array(gun['boreCenterModel'])-C)@np.stack([X,N],axis=1)
 assert abs(center[0])<.002 and np.max(abs(center-expected))<.002,(name,'actual barrel is displaced from its calibrated centerline',center,expected)
 noseErrors=[]
 for label in ['Port','Starboard']:
  for suffix in ['_FixedTransitionPatch_','_FixedNosePatch_','_FixedNoseReturn_']:
   p=bpy.data.objects[name+suffix+label];assert p.parent==A
  p=bpy.data.objects[name+'_FixedNosePatch_'+label];M=inv@p.matrix_world
  face=p.data.polygons[0];pq=np.array([(np.array(M@p.data.vertices[i].co)-C)@Q for i in face.vertices])
  plane=np.array(p['sourceFacetPlane']);residual=float(np.max(abs(pq[:,2]-np.c_[pq[:,:2],np.ones(len(pq))]@plane)))
  assert residual<.0001,(name,label,'nose patch is not coplanar with source hull',residual)
  noseErrors.append(residual)
 fixed=[bpy.data.objects[n]for n in carriage['fixedBayStructures']]
 assert len(fixed)==3 and all(o.parent==A for o in fixed)
 for leaf in row['leaves']:
  skin=bpy.data.objects[leaf['name']+'_Skin'];assert all(skin.data.materials[f.material_index].name=='Odin_Bay_Primer'for f in skin.data.polygons)
  backing=bpy.data.objects[leaf['name']+'_FittedBacking'];assert any(backing.data.materials[f.material_index].name=='Odin_Paint_Light'for f in backing.data.polygons)
 receiverFits={}
 if '_3_'in name:
  for label,sign in [('Port',-1),('Starboard',1)]:
   slider=bpy.data.objects[name+'_Slider_'+label]
   returned=bpy.data.objects[slider.name+'_InnerRimReturn_Slope'];M=inv@returned.matrix_world
   points=np.array([M@v.co for v in returned.data.vertices]);rim=np.array(slider['frontReceiverEdgeModel'])
   source_error=max(float(np.min(np.linalg.norm(hullpoints-p,axis=1)))for p in rim)
   edge_error=max(float(np.min(np.linalg.norm(points-p,axis=1)))for p in rim)
   assert source_error<.0001 and edge_error<.0001,(name,label,'first armor must close on actual lower rim',source_error,edge_error)
   local_rim=(rim-C)@Q
   assert local_rim[:,1].max()<23 and local_rim[:,2].max()<2.7,(name,label,'wrong hull layer selected')
   for suffix in ['_TrapezoidSkin','_InnerRimReturn_Slope','_InnerRimReturn_Crown']:
    o=bpy.data.objects[slider.name+suffix];M=inv@o.matrix_world
    # Inspect the visible roof/return planes, excluding pre-existing gauge
    # miters around the solidified crown's thickness.
    for f in list(o.data.polygons)[:2 if suffix=='_TrapezoidSkin' else 1]:
     p=np.array([M@o.data.vertices[i].co for i in f.vertices]);u=p[1]-p[0];v=p[2]-p[0];normal=np.cross(u,v);normal/=np.linalg.norm(normal)
     assert np.max(abs((p-p[0])@normal))<.0001,(o.name,'non-planar face')
   receiverFits[label]={'receiverLayer':'lower inner slot rim','originalRimVertexError':source_error,'actualReturnEdgeError':edge_error,'planarRoofAndReturn':True}
 result[name]={'actualBoreRestAngleDegrees':angle,'actualBoreCenterError':float(np.max(abs(center-expected))),'fixedStructures':len(fixed),'localClosureHalves':6,'nosePlaneMaximumError':max(noseErrors),'redInnerGrates':6,'aftFirstPlateReceiverFit':receiverFits}
poses=json.loads((out/'candidate-poses.json').read_text());basis=Quaternion((1,0,0),-math.pi/2)
fixed=[o for o in s.objects if o.get('fixedBayStructure')];matrices={o.name:np.array(o.matrix_world)for o in fixed};error=0.
for pose in poses:
 for j in pose['joints']:
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
 bpy.context.view_layer.update()
 for o in fixed:error=max(error,float(np.max(np.abs(np.array(o.matrix_world)-matrices[o.name]))))
assert error<1e-7,error
sha=hashlib.sha256((R.parent/'Odin 建模/odin.blend').read_bytes()).hexdigest();assert sha=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
audit={'unchangedObjects':len(before),'changedOutsideScope':changed,'maximumFixedStructureMotion':error,'poseSamples':len(poses),'mounts':result,'originalSha256':sha}
(out/'geometry-audit.json').write_text(json.dumps(audit,indent=2));print(audit,flush=True)
