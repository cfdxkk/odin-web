"""Reload and verify actual source-based scarf geometry, UVs and crown closure."""
import bpy,json,hashlib,math,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1]
fit=json.loads((root/'docs/review/v0.11.30/root-fit.json').read_text())
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
def closed(j):
 name=j['barrelJoint'];C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);H=np.array((inv@j.matrix_world).translation);R=np.array(Quaternion(Vector(j['hingeAxisModel']),math.radians(j['closedAngleDegrees'])).to_matrix());offset=np.array(bpy.data.objects[name+'_SourceCarriage']['closedOffsetModel'])
 return(H+(points(j.children[0])-H)@R.T+offset-C)@Q
def area(ps):return sum(np.linalg.norm(np.cross(ps[k]-ps[0],ps[k+1]-ps[0]))/2 for k in range(1,len(ps)-1))
def clip(ps,plane):
 a,b,c=plane;out=[]
 for p,q in zip(ps,ps[1:]+ps[:1]):
  d=p[0][1]-a*p[0][0]-b*p[0][2]-c;e=q[0][1]-a*q[0][0]-b*q[0][2]-c
  if d>=-1e-9:out.append(p)
  if d*e<0:
   t=d/(d-e);out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
 return out
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.29.blend'))
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
others={o.name:digest(o)for o in bpy.context.scene.objects if o.type=='MESH'and o.name not in changed}
joints={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}
expected={}
for station in fit['stations'].values():
 for row in station['rearCovers']:
  j=bpy.data.objects[row['joint']];o=j.children[0];q=closed(j);uv=o.data.uv_layers.active;o.data.calc_loop_triangles();records={}
  for f in o.data.polygons:
   polygons=[]
   for t in [t for t in o.data.loop_triangles if t.polygon_index==f.index]:
    ps=[(q[k].copy(),np.array(uv.data[li].uv))for k,li in zip(t.vertices,t.loops)]
    for plane in row['planes']:ps=clip(ps,plane['coverPlaneB'])
    if len(ps)>=3:polygons.append(ps)
   records[f.index]={'area':sum(area(np.array([p for p,u in ps]))for ps in polygons),'points':[p for ps in polygons for p,u in ps],'uv':[u for ps in polygons for p,u in ps],'material':o.data.materials[f.material_index].name}
  expected[o.name]=records
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.30.blend'))
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
for name,h in others.items():assert digest(bpy.data.objects[name])==h,('Unrelated model changed',name)
for name,(matrix,data)in joints.items():
 o=bpy.data.objects[name];now=plain(dict(o.items()));now.pop('rearScarfPlanesLocal',None);now.pop('rearScarfClearance',None)
 assert np.max(abs(np.array(o.matrix_local)-matrix))<.00002 and data==now,('Mechanical transform or timing changed',name)
rows=[]
for name,station in fit['stations'].items():
 for row in station['rearCovers']:
  j=bpy.data.objects[row['joint']];o=j.children[0];q=closed(j);uv=o.data.uv_layers.active;observed={i:0. for i in expected[o.name]};error=0.;uv_error=0.;caps=0;planes=row['planes'];o.data.calc_loop_triangles()
  for f in o.data.polygons:
   original=o.data.attributes['rootSourceFace'].data[f.index].value-1
   if original<0:caps+=1;continue
   source=expected[o.name][original];observed[original]+=sum(area(q[list(t.vertices)])for t in o.data.loop_triangles if t.polygon_index==f.index)
   assert o.data.materials[f.material_index].name==source['material']
   ps=np.array(source['points']);us=np.array(source['uv'])
   for k,li in zip(f.vertices,f.loop_indices):
    distances=np.linalg.norm(ps-q[k],axis=1);indices=np.where(distances<.0002)[0]
    assert len(indices),('Cut point left its source surface',o.name,original,q[k],distances.min())
    error=max(error,float(distances.min()));uv_error=max(uv_error,float(min(np.max(abs(np.array(uv.data[li].uv)-us[i]))for i in indices)))
  area_error=max(abs(observed[i]-s['area'])for i,s in expected[o.name].items());assert area_error<.001 and uv_error<.00001
  margins=[]
  for plane in planes:
   a,b,c=plane['coverPlaneB'];margins.append(float(np.min(q[:,1]-a*q[:,0]-b*q[:,2]-c)))
  assert min(margins)>-.0001
  vertices=[Vector(p)for p in q];tris=[t.vertices[:]for t in o.data.loop_triangles];materials=[o.data.materials[t.material_index].name for t in o.data.loop_triangles];bvh=BVHTree.FromPolygons(vertices,tris,all_triangles=True);miss=[];red=[];roof_error=0.;rays=0
  intercept=4.65 if '_2_' in name else 4.87;slope=(intercept-1.7756)/(2.88-.3);sign=-1 if '_Shutter_Port_' in j.name else 1
  for x in(.025,.10,.25,.30,.50,.80,1.10,1.50,1.90,2.30,2.60,2.84):
   for step in(.02,.06,.12):
    b=max((a['coverPlaneB'][0]*sign*x+a['coverPlaneB'][1]*(intercept-slope*max(0,x-.3))+a['coverPlaneB'][2])/(1+.007*a['coverPlaneB'][1])for a in planes)+step;n=intercept-.007*b-slope*max(0,x-.3);hit,normal,index,distance=bvh.ray_cast(Vector((sign*x,b,n+1)),Vector((0,0,-1)),2);rays+=1
    if hit is None:miss.append([sign*x,b])
    elif materials[index]!='Odin_Paint_Light':red.append([sign*x,b])
    else:roof_error=max(roof_error,abs(float(distance)-1))
  assert not miss and not red and roof_error<.015,('Scarf roof has an opening',j.name,miss,red,roof_error)
  rows.append({'mesh':o.name,'planes':planes,'retainedSourceUvError':uv_error,'maxSourcePointError':error,'maxTrimmedAreaError':area_error,'minimumPlaneMargins':margins,'closedScarfRays':rays,'missingRoof':miss,'redFirstHits':red,'maxRoofError':roof_error,'sealedEndFaces':caps})
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
with(root.parent/'Odin 建模/odin.blend').open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==fit['sourceSha256']
with(root/'assets/blender/odin_articulated_v0.11.30.blend').open('rb')as f:native_hash=hashlib.file_digest(f,'sha256').hexdigest()
report={'version':'0.11.30','nativeSha256':native_hash,'unchangedOtherMeshes':len(others),'unchangedJointTransforms':len(joints),'unchangedMechanicalMetadata':len(joints),'rearCovers':rows,'originalSourceUnchanged':True,'animationClips':0}
(root/'docs/review/v0.11.30/root-geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('ROOT_SCARF_PROOF',len(rows),len(others),len(joints),max(r['retainedSourceUvError']for r in rows),flush=True)
