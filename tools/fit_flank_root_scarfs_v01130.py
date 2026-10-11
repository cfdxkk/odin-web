"""Restore sloped rear cover ends using the original turret-root bevels.

Run on v0.11.29. Only the eight original rear armor meshes are trimmed.
The two measured source bevel planes define their scarf; every mechanical
transform, bore mesh, source action, cap stroke and fixed hull stays intact.
"""
import bpy,bmesh,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Quaternion,Vector
root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset']
assert asset['version']=='0.11.29';inv=asset.matrix_world.inverted()
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text())
review=root/'docs/review/v0.11.30';review.mkdir(parents=True,exist_ok=True)
source_path=root.parent/'Odin 建模/odin.blend'
with source_path.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
assert source_hash=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
CLEARANCE=.055;changed=set();report={'version':'0.11.30','sourceSha256':source_hash,'clearance':CLEARANCE,'stations':{}}
def plain(v):
 if hasattr(v,'to_dict'):return{k:plain(x)for k,x in v.to_dict().items()}
 if hasattr(v,'to_list'):return[plain(x)for x in v.to_list()]
 if isinstance(v,dict):return{k:plain(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return[plain(x)for x in v]
 return v
def points(o):
 a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);m=np.array(inv@o.matrix_world);return a.reshape(-1,3)@m[:3,:3].T+m[:3,3]
def digest(o):
 h=hashlib.sha256();h.update(np.array([v.co for v in o.data.vertices],dtype=np.float32).tobytes())
 for f in o.data.polygons:
  h.update(np.array(f.vertices[:],dtype=np.int32).tobytes());h.update(o.data.materials[f.material_index].name.encode())
  if o.data.uv_layers.active:h.update(np.array([o.data.uv_layers.active.data[k].uv for k in f.loop_indices],dtype=np.float32).tobytes())
 return h.hexdigest()
before={o.name:digest(o)for o in bpy.context.scene.objects if o.type=='MESH'}
joints={o.name:(np.array(o.matrix_local).copy(),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}
for number in(2,4):
 for side in('Starboard','Port'):
  name=f'SideBattery_{number}_{side}';C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);offset=np.array(bpy.data.objects[name+'_SourceCarriage']['closedOffsetModel']);body=bpy.data.objects[name+'_OriginalTurretShell'];body_q=(points(body)+offset-C)@Q;rows=[]
  for physical,sign in(('Port',-1),('Starboard',1)):
   candidates=[]
   for f in body.data.polygons:
    ps=body_q[list(f.vertices)];normal=np.cross(ps[1]-ps[0],ps[2]-ps[0]);length=np.linalg.norm(normal)
    if length<1e-8 or not(-18<ps[:,1].mean()<-16)or sign*ps[:,0].mean()<1.5 or ps[:,2].max()<2.4:continue
    normal/=length
    if normal[1]<.65 or abs(normal[2])<.25:continue
    coeff=np.linalg.lstsq(np.c_[ps[:,[0,2]],np.ones(len(ps))],ps[:,1],rcond=None)[0]
    if not(-1.2<coeff[1]<-.65 or .3<coeff[1]<.65):continue
    error=float(np.max(abs(np.c_[ps[:,[0,2]],np.ones(len(ps))]@coeff-ps[:,1])))
    candidates.append((f.area,coeff,f.index,ps,error))
   lower=max((r for r in candidates if r[1][1]<0),key=lambda r:r[0]);upper=max((r for r in candidates if r[1][1]>0),key=lambda r:r[0]);planes=[]
   for area,coeff,face,ps,error in(lower,upper):
    assert error<CLEARANCE*.6,(name,physical,face,error)
    adjusted=coeff.copy();adjusted[2]+=CLEARANCE
    planes.append({'sourceFace':face,'sourcePlaneB':coeff.tolist(),'coverPlaneB':adjusted.tolist(),'sourcePoints':ps.tolist(),'maxSourceFitError':error})
   j=bpy.data.objects[f'{name}_Shutter_{physical}_00'];o=j.children[0];H=np.array((inv@j.matrix_world).translation);R=np.array(Quaternion(Vector(j['hingeAxisModel']),math.radians(j['closedAngleDegrees'])).to_matrix());q=(H+(points(o)-H)@R.T+offset-C)@Q;mi=np.array((inv@o.matrix_world).inverted());old_vertices=len(q);old_faces=len(o.data.polygons)
   bm=bmesh.new();bm.from_mesh(o.data)
   for v,p in zip(bm.verts,q):v.co=Vector(p)
   bm.faces.layers.int.new('rootSourceFace');bm.faces.layers.int.new('rootScarfEndCap')
   marker=bm.faces.layers.int.get('rootScarfEndCap');original_layer=bm.faces.layers.int.get('rootSourceFace');source_layer=bm.faces.layers.int.get('originalSourceFace');caps=[]
   for i,f in enumerate(bm.faces):f[original_layer]=i+1
   for plane in planes:
    a,b,c=plane['coverPlaneB'];cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=Vector((0,c,0)),plane_no=Vector((-a,1,-b)),clear_inner=True,clear_outer=False)
    edges=[e for e in cut['geom_cut']if isinstance(e,bmesh.types.BMEdge)and e.is_valid and len(e.link_faces)==1]
    if edges:
     # Close only newly cut loops. Exterior skin ends stay gray; inward
     # grate and rib ends retain the red primer rather than exposing voids.
     filled=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
     for f in filled:
      boundary_materials={other.material_index for e in f.edges for other in e.link_faces if other!=f}
      gray=o.data.materials.find('Odin_Paint_Light');red=o.data.materials.find('Odin_Turret_Interior_DeepRed');f.material_index=gray if gray in boundary_materials else red;f[marker]=1
      if source_layer:f[source_layer]=0
      f[original_layer]=0
      uv=bm.loops.layers.uv.active
      if uv:
       for loop in f.loops:loop[uv].uv=(loop.vert.co.x*.025,loop.vert.co.z*.025)
      caps.append(f)
   bm.verts.ensure_lookup_table();fitted=np.array([v.co for v in bm.verts]);assert len(fitted)>100 and fitted[:,1].max()>-8.3
   for plane in planes:
    a,b,c=plane['coverPlaneB'];assert np.min(fitted[:,1]-a*fitted[:,0]-b*fitted[:,2]-c)>-.0001
   cap_count=sum(f[marker]>0 for f in bm.faces)
   for v in bm.verts:v.co=Vector((mi@np.r_[H+(C+Q@np.array(v.co)-H-offset)@R,1])[:3])
   bm.to_mesh(o.data);bm.free();o.data.update();o['sourceRootScarf']=True;changed.add(o.name)
   j['rearScarfPlanesLocal']=[p['coverPlaneB']for p in planes];j['rearScarfClearance']=CLEARANCE
   rows.append({'joint':j.name,'mesh':o.name,'planes':planes,'beforeVertices':old_vertices,'beforeFaces':old_faces,'afterVertices':len(o.data.vertices),'afterFaces':len(o.data.polygons),'newEndCaps':cap_count,'rearClosedRange':[float(fitted[:,1].min()),float(fitted[:,1].max())]})
  report['stations'][name]={'rearCovers':rows,'unchangedSourceHousing':body.name}
for name,h in before.items():
 if name not in changed:assert digest(bpy.data.objects[name])==h,('Unrelated mesh changed',name)
for name,(matrix,props)in joints.items():
 o=bpy.data.objects[name];assert np.array_equal(np.array(o.matrix_local),matrix),('Mechanical transform changed',name)
 now=plain(dict(o.items()));now.pop('rearScarfPlanesLocal',None);now.pop('rearScarfClearance',None);assert props==now,('Mechanical metadata changed',name)
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
with source_path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==source_hash
report.update(changedMeshes=sorted(changed),unchangedOtherMeshes=len(before)-len(changed),unchangedJointTransforms=len(joints),unchangedMechanicalMetadata=len(joints),animationClips=0)
(review/'root-fit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
asset['version']='0.11.30';bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.30.blend'),compress=True)
print('SOURCE_ROOT_SCARFS',len(changed),len(before)-len(changed),len(joints),flush=True)
