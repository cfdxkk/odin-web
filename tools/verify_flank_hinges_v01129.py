"""Reload both immutable native assets and verify seam ownership and pivots."""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1]
fit=json.loads((root/'docs/review/v0.11.29/seam-fit.json').read_text())
counts=json.loads((root/'docs/review/v0.11.26/source-fit.json').read_text())
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text())
changed=set(fit['changedMeshes'])
def plain(v):
 if hasattr(v,'to_dict'):return{k:plain(x)for k,x in v.to_dict().items()}
 if hasattr(v,'to_list'):return[plain(x)for x in v.to_list()]
 if isinstance(v,dict):return{k:plain(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return[plain(x)for x in v]
 return v
def digest(o):
 h=hashlib.sha256();h.update(np.array([v.co for v in o.data.vertices],dtype=np.float32).tobytes())
 for f in o.data.polygons:
  h.update(np.array(f.vertices[:],dtype=np.int32).tobytes());h.update(o.data.materials[f.material_index].name.encode())
  if o.data.uv_layers.active:h.update(np.array([o.data.uv_layers.active.data[k].uv for k in f.loop_indices],dtype=np.float32).tobytes())
 return h.hexdigest()
def points(o):
 a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);m=np.array(inv@o.matrix_world);return a.reshape(-1,3)@m[:3,:3].T+m[:3,3]
def closed_points(j):
 name=j['barrelJoint'];C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);H=np.array((inv@j.matrix_world).translation);R=np.array(Quaternion(Vector(j['hingeAxisModel']),math.radians(j['closedAngleDegrees'])).to_matrix());move=np.array(bpy.data.objects[name+'_SourceCarriage']['closedOffsetModel'])if j['panelIndex']==0 else 0
 return (H+(points(j.children[0])-H)@R.T+move-C)@Q
def area(ps):return sum(np.linalg.norm(np.cross(ps[k]-ps[0],ps[k+1]-ps[0]))/2 for k in range(1,len(ps)-1))
def uv_error(p,u,triangles):
 candidates=[]
 for t,uv in triangles:
  for corner,old_uv in zip(t,uv):
   if np.linalg.norm(p-corner)<.0001:candidates.append(np.max(abs(u-old_uv)))
  # Intersections are on the original render triangle edges. Recompute
  # exact cut points rather than an ill-conditioned barycentric solve on
  # the source's very thin rolled-rail triangles.
  for a,b in ((0,1),(1,2),(2,0)):
   for bound in(-8.195,.325):
    if abs(t[b,1]-t[a,1])<1e-10:continue
    fraction=(bound-t[a,1])/(t[b,1]-t[a,1])
    if not 0<=fraction<=1:continue
    point=t[a]+fraction*(t[b]-t[a]);old_uv=uv[a]+fraction*(uv[b]-uv[a])
    if np.linalg.norm(p-point)<.0001:candidates.append(np.max(abs(u-old_uv)))
 assert candidates,('Source point left its original triangle',p)
 return min(candidates)
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.28.blend'))
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
before={o.name:digest(o)for o in bpy.context.scene.objects if o.type=='MESH'and o.name not in changed}
joints={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')and not(o.get('barrelJoint')in fit['stations'])}
sources={}
for name,s in counts['stations'].items():
 for row in s['leaves']:
  j=bpy.data.objects[row['name']];o=j.children[0];q=closed_points(j);o.data.calc_loop_triangles();uv=o.data.uv_layers.active
  bank=int(j['panelIndex']);physical='Port'if'_Shutter_Port_'in j.name else'Starboard'
  for f in o.data.polygons:
   if max(f.vertices)>=row['originalVertices']:continue
   ts=[t for t in o.data.loop_triangles if t.polygon_index==f.index]
   triangles=[(q[list(t.vertices)],np.array([uv.data[k].uv for k in t.loops]))for t in ts]
   sources[name,physical,bank,f.index]={'area':sum(area(p)for p,u in triangles),'triangles':triangles,'mat':o.data.materials[f.material_index].name}
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.29.blend'))
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
for name,h in before.items():assert digest(bpy.data.objects[name])==h,('Unrelated mesh changed',name)
for name,(m,data)in joints.items():
 o=bpy.data.objects[name];now=plain(dict(o.items()));now.pop('holdRaisedAfterAdvance',None)
 matrix_error=float(np.max(abs(np.array(o.matrix_local)-m)))
 assert matrix_error<.00002 and data==now,('Unrelated mechanism changed',name,matrix_error,[k for k in data if data[k]!=now.get(k)])
areas={key:0. for key in sources};max_uv=0.;rail=[];bounds=[]
for name,s in fit['stations'].items():
 C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);offset=np.array(bpy.data.objects[name+'_SourceCarriage']['closedOffsetModel'])
 for row in s['leaves']:
  j=bpy.data.objects[row['joint']];o=j.children[0];q=closed_points(j);H=np.array((inv@j.matrix_world).translation)+(offset if j['panelIndex']==0 else 0);h=(H-C)@Q;axis=np.array(j['hingeAxisModel'])@Q
  assert abs(abs(h[0])-2.88)<.0001 and abs(h[2]-(1.7756-.007*h[1]))<.0001
  assert np.linalg.norm(np.cross(axis,np.array([0,1,-.007])))<.00001
  rail.append({'joint':j.name,'positionError':abs(h[2]-(1.7756-.007*h[1])),'axisError':float(np.linalg.norm(np.cross(axis,np.array([0,1,-.007]))))})
  physical='Port'if'_Shutter_Port_'in j.name else'Starboard';uv=o.data.uv_layers.active;lining=[];o.data.calc_loop_triangles()
  for f in o.data.polygons:
   fi=o.data.attributes['originalSourceFace'].data[f.index].value-1
   if fi<0:continue
   bank=o.data.attributes['originalSourceBank'].data[f.index].value;key=(name,physical,bank,fi);source=sources[key]
   assert o.data.materials[f.material_index].name==source['mat']
   areas[key]+=sum(area(q[list(t.vertices)])for t in o.data.loop_triangles if t.polygon_index==f.index)
   for k,li in zip(f.vertices,f.loop_indices):max_uv=max(max_uv,float(uv_error(q[k],np.array(uv.data[li].uv),source['triangles'])))
   if source['mat']=='Odin_Turret_Interior_DeepRed':lining.extend(q[list(f.vertices),1].tolist())
  lo,hi=[(None,-8.195),(-8.195,.325),(.325,None)][j['panelIndex']]
  if lo is not None:assert min(lining)>=lo-.0001
  if hi is not None:assert max(lining)<=hi+.0001
  bounds.append({'joint':j.name,'liningRange':[min(lining),max(lining)],'boundaryLimits':[lo,hi]})
errors=[abs(areas[k]-s['area'])for k,s in sources.items()]
assert max(errors)<.002,('Source surface area changed',max(errors));assert max_uv<.0006,('Source UVs changed',max_uv)
noncollapsed=[k for k,s in sources.items()if s['area']>1e-8]
assert all(areas[k]>0 for k in noncollapsed),('Lost an original source surface',[k for k in noncollapsed if areas[k]<=0])
assert hashlib.sha256((root.parent/'Odin 建模/odin.blend').read_bytes()).hexdigest()==fit['sourceSha256']
report={'version':'0.11.29','unchangedOtherMeshes':len(before),'unchangedOtherJoints':len(joints),'originalSourcePolygons':len(noncollapsed),'retainedSourcePolygons':int(sum(areas[k]>0 for k in noncollapsed)),'collapsedOriginalPolygons':len(sources)-len(noncollapsed),'maxSourceAreaError':float(max(errors)),'maxSourceUvError':max_uv,'hingeRails':rail,'liningBanks':bounds,'originalSourceUnchanged':True,'animationClips':0}
(root/'docs/review/v0.11.29/source-geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('SEAM_SOURCE_PROOF',len(before),len(joints),len(sources),max(errors),max_uv,flush=True)
