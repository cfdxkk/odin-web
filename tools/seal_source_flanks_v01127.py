"""Seal the fitted original flank armor; remove only the legacy fixed housing.

Run on v0.11.26. Source grate geometry, the nose leading edge, all joint
transforms, opening stops and barrel/carriage/cap timing stay unchanged.
"""
import bpy,bmesh,hashlib,json,math
import numpy as np
from pathlib import Path
from mathutils import Quaternion,Vector

root=Path(__file__).resolve().parents[1];scene=bpy.context.scene
asset=bpy.data.objects['Odin_Asset'];assert asset['version']=='0.11.26'
inv=asset.matrix_world.inverted();light=bpy.data.materials['Odin_Paint_Light'];red=bpy.data.materials['Odin_Turret_Interior_DeepRed']
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text(encoding='utf8'))
prior=json.loads((root/'docs/review/v0.11.26/source-fit.json').read_text(encoding='utf8'))
review=root/'docs/review/v0.11.27';review.mkdir(parents=True,exist_ok=True)
changed=set();source_path=root.parent/'Odin 建模/odin.blend'
with source_path.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
assert source_hash=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'

def plain(v):
 if hasattr(v,'to_dict'):return {k:plain(x)for k,x in v.to_dict().items()}
 if hasattr(v,'to_list'):return [plain(x)for x in v.to_list()]
 if isinstance(v,dict):return {k:plain(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [plain(x)for x in v]
 return v
def digest(o):
 h=hashlib.sha256();p=np.array([v.co for v in o.data.vertices],dtype=np.float32);h.update(p.tobytes())
 uv=o.data.uv_layers.active
 for f in o.data.polygons:
  h.update(np.array(f.vertices[:],dtype=np.int32).tobytes());h.update(o.data.materials[f.material_index].name.encode())
  if uv:h.update(np.array([uv.data[k].uv for k in f.loop_indices],dtype=np.float32).tobytes())
 return h.hexdigest()
before={o.name:digest(o)for o in scene.objects if o.type=='MESH'}
joints={o.name:(np.array(o.matrix_local).copy(),plain(dict(o.items())))for o in scene.objects if o.get('staticJoint')}
def points(o):return np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])
def crown(b):return 5.615-.007*b
def profile(x,b):return 6.326-1.58*max(.45,abs(x))-.007*b
report={'version':'0.11.27','sourceSha256':source_hash,'stations':{},'removedLegacyHousing':{}}

def apply_points(o,q,to_data):
 for v,p in zip(o.data.vertices,q):v.co=Vector(to_data(p))
 o.data.update();changed.add(o.name)

def lap(o,to_data,sign,b0,b1,lower=2.88):
 """A thin inner return that moves rigidly with this original cover."""
 bm=bmesh.new();bm.from_mesh(o.data)
 if light.name not in o.data.materials:o.data.materials.append(light)
 if red.name not in o.data.materials:o.data.materials.append(red)
 gray=o.data.materials.find(light.name);inner=o.data.materials.find(red.name)
 rows=[]
 for depth in(.001,.085):
  ring=[]
  for b in(b0,b1):
   ring.append([bm.verts.new(Vector(to_data(np.array([sign*x,b,profile(x,b)-depth]))))for x in(.02,.45,lower)])
  rows.append(ring)
 new=[]
 for k in range(2):
  f=bm.faces.new([rows[0][0][k],rows[0][1][k],rows[0][1][k+1],rows[0][0][k+1]]);f.material_index=gray;new.append(f)
  f=bm.faces.new([rows[1][0][k+1],rows[1][1][k+1],rows[1][1][k],rows[1][0][k]]);f.material_index=inner;new.append(f)
 for b in range(2):
  for k in range(2):
   f=bm.faces.new([rows[0][b][k],rows[0][b][k+1],rows[1][b][k+1],rows[1][b][k]]);f.material_index=gray;new.append(f)
 for k in(0,2):
  f=bm.faces.new([rows[0][0][k],rows[1][0][k],rows[1][1][k],rows[0][1][k]]);f.material_index=gray;new.append(f)
 uv=bm.loops.layers.uv.active
 if uv:
  for f in new:
   for loop in f.loops:loop[uv].uv=(loop.vert.co.x*.025,loop.vert.co.y*.025)
 bmesh.ops.recalc_face_normals(bm,faces=new);bm.to_mesh(o.data);bm.free();o.data.update()
 o['closedSeamReturn']=True;changed.add(o.name)

def center_return(o,to_data,b0,b1,n0,n1):
 """Hide the narrow center gap beneath the two existing flat roof halves."""
 bm=bmesh.new();bm.from_mesh(o.data)
 gray=o.data.materials.find(light.name);inner=o.data.materials.find(red.name)
 vertices=[]
 for depth in(.001,.085):
  for b,n in[(b0,n0),(b1,n1)]:
   for x in(-.055,.055):vertices.append(bm.verts.new(Vector(to_data(np.array([x,b,n-depth])))))
 new=[]
 for ids,mat in[((0,1,3,2),gray),((4,6,7,5),inner),((0,4,5,1),gray),((2,3,7,6),gray),((0,2,6,4),gray),((1,5,7,3),gray)]:
  f=bm.faces.new([vertices[k]for k in ids]);f.material_index=mat;new.append(f)
 uv=bm.loops.layers.uv.active
 if uv:
  for f in new:
   for loop in f.loops:loop[uv].uv=(loop.vert.co.x*.025,loop.vert.co.y*.025)
 bmesh.ops.recalc_face_normals(bm,faces=new);bm.to_mesh(o.data);bm.free();o.data.update()
 o['closedCenterReturn']=True;changed.add(o.name)

for number in(2,4):
 for side in('Starboard','Port'):
  name=f'SideBattery_{number}_{side}';C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes'])
  offset=np.array(bpy.data.objects[name+'_SourceCarriage']['closedOffsetModel']);rows=[]
  for physical_side,sign in [('Port',-1),('Starboard',1)]:
   for i in range(3):
    j=bpy.data.objects[f'{name}_Shutter_{physical_side}_{i:02}'];o=j.children[0]
    H=np.array((inv@j.matrix_world).translation);R=np.array(Quaternion(Vector(j['hingeAxisModel']),math.radians(j['closedAngleDegrees'])).to_matrix())
    move=offset if i==0 else np.zeros(3);q=(H+(points(o)-H)@R.T+move-C)@Q;old=q.copy()
    original_count=next(r['originalVertices']for r in prior['stations'][name]['leaves']if r['name']==j.name)
    lower,upper=[(-17.4,-8.205),(-8.185,.315),(.335,9.415)][i]
    gray=set(v for f in o.data.polygons if o.data.materials[f.material_index]==light for v in f.vertices if v<original_count)
    # Include the small original exterior end triangles and rolled edge.
    # The earlier area cutoff missed them, leaving a raked upper end and
    # exposing the red rail through the middle/front bank boundary.
    for k in gray:
     if q[k,1]<lower+2.15:q[k,1]=lower
     elif q[k,1]>upper-2.15:q[k,1]=upper
     if abs(q[k,0])>2.:q[k,0]=sign*2.88
     q[k,2]=profile(q[k,0],q[k,1])
    for k in range(original_count,len(q)):
     b=old[k,1]
     if b<lower+2.15:q[k,1]=lower
     elif b>upper-2.15:q[k,1]=upper
     # The first crown return follows the actual original exterior edge.
     candidates=[v for v in gray if np.linalg.norm(old[k]-old[v]-np.array([0,0,-.16]))<.00015]
     if candidates:q[k]=q[candidates[0]]-np.array([0,0,.16])
     else:q[k,2]=crown(q[k,1])-(.16 if old[k,2]<crown(b)-.08 else 0.)
    mi=np.array((inv@o.matrix_world).inverted())
    def to_data(p):return(mi@np.r_[H+(C+Q@p-H-move)@R,1])[:3]
    apply_points(o,q,to_data)
    if i>0:lap(o,to_data,sign,lower-.075,lower+.025)
    if i==2:lap(o,to_data,sign,upper-.025,upper+.35)
    if sign<0:center_return(o,to_data,lower-.03,upper+.03,crown(lower-.03),crown(upper+.03))
    # Original inward grate faces have their own vertices; retain every
    # vertex not connected to an exterior source skin.
    retained=[k for k in range(original_count)if k not in gray]
    assert np.max(abs(old[retained]-q[retained]))==0
    rows.append({'mesh':o.name,'originalVertices':original_count,'fittedSourceExteriorVertices':len(gray),'unchangedGrateVertices':len(retained),'closedBankRange':[lower,upper],'seamLapWidth':.10 if i>0 else 0})
  cap=bpy.data.objects[name+'_FrontCap'];o=cap.children[0];slide=np.array(cap['slideVector']);q=(points(o)+slide-C)@Q;old=q.copy()
  count=prior['stations'][name]['originalCapVertices'];gray=set(v for f in o.data.polygons if o.data.materials[f.material_index]==light for v in f.vertices if v<count)
  for k in gray:
   if q[k,1]<15:
    q[k,1]=9.425
    if abs(q[k,0])>2.70:q[k,0]=math.copysign(2.88,q[k,0])
    q[k,2]=profile(q[k,0],q[k,1])
  for k in range(count,len(q)):
   if old[k,1]>=15:continue
   q[k,1]=9.425
   candidates=[v for v in gray if np.linalg.norm(old[k]-old[v]-np.array([0,0,-.16]))<.00015]
   if candidates:q[k]=q[candidates[0]]-np.array([0,0,.16])
   else:q[k,2]=crown(q[k,1])-(.16 if old[k,2]<crown(old[k,1])-.08 else 0.)
  mi=np.array((inv@o.matrix_world).inverted())
  def cap_to_data(p):return(mi@np.r_[C+Q@p-slide,1])[:3]
  apply_points(o,q,cap_to_data)
  assert np.max(abs(q[old[:,1]>=15]-old[old[:,1]>=15]))==0
  leading=float(np.min(q[(np.abs(q[:,0])<.05)&(q[:,1]>15),1]));front_height=float(np.min(q[(np.abs(q[:,0])<.05)&(q[:,1]>15),2]))+.16
  center_return(o,cap_to_data,9.395,leading,crown(9.395),front_height)
  report['stations'][name]={'leaves':rows,'capRearProfileB':9.425,'capLeadingEdgeUnchanged':True,'flatCrownHalfWidth':.45,'barrelAndJointMetadataUnchanged':True}

# The old whole port-housing mirror contains the duplicate shell and two
# legitimate fixed bearing islands. Delete the shell island only.
o=bpy.data.objects['Odin_Restored_Starboard_Housing'];p=points(o);parents=list(range(len(p)))
def find(i):
 while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
 return i
for e in o.data.edges:a,b=e.vertices;parents[find(a)]=find(b)
groups={};faces={}
for v in o.data.vertices:groups.setdefault(find(v.index),[]).append(v.index)
for f in o.data.polygons:faces.setdefault(find(f.vertices[0]),[]).append(f.index)
housing=[g for g,ids in groups.items()if p[ids,1].max()-p[ids,1].min()>25]
assert len(groups)==3 and len(housing)==1
remove=set(faces[housing[0]]);preserved=[f for f in o.data.polygons if f.index not in remove]
assert len(remove)==359 and len(preserved)==1590
bearing_keys=[sorted(tuple(float(x)for x in p[v])for v in f.vertices)for f in preserved]
bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index in remove],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(o.data);bm.free();o.data.update()
now=points(o);assert bearing_keys==[sorted(tuple(float(x)for x in now[v])for v in f.vertices)for f in o.data.polygons]
old_name=o.name;changed.add(old_name);o.name='Flank_4_Starboard_FixedBearingPair';o['fixedBearingPair']=True;o['removedLegacyHousingPolygons']=len(remove);o['completion']='Original fixed bearing pair; duplicate housing removed'
report['removedLegacyHousing']={'oldMesh':old_name,'remainingMesh':o.name,'removedPolygons':len(remove),'retainedBearingPolygons':len(o.data.polygons),'retainedBearingIslands':2,'bearingCoordinatesUnchanged':True}
# These two receiver end faces are part of the exterior hull, bounded only
# by gray hull faces. An earlier interior-color region also painted them,
# leaving the tiny red triangle below the front lip seen in the report.
o=bpy.data.objects['holo.001'];gray=o.data.materials.find(light.name)
for fi in(131174,163397):
 f=o.data.polygons[fi];assert o.data.materials[f.material_index]==red
 f.material_index=gray
changed.add(o.name);report['restoredGrayOuterEndFaces']={'mesh':o.name,'faces':[131174,163397],'geometryAndUvsUnchanged':True}
# The source floor quads span the bore channel and the surrounding outer
# lip. Keep the complete original floor red; finish only their outboard
# bands in gray. No source floor, wall or support polygon is removed.
bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table();uv=bm.loops.layers.uv.active
floor_rows=[];world=inv@o.matrix_world;mi=world.inverted()
floor_faces={fi:bm.faces[fi]for fi in(194058,163402)}
for side,fi in [('Starboard',194058),('Port',163402)]:
 name=f'SideBattery_2_{side}';C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);f=floor_faces[fi]
 assert o.data.materials[f.material_index]==red
 model=np.array([world@loop.vert.co for loop in f.loops]);local=(model-C)@Q;tex=np.array([loop[uv].uv for loop in f.loops]);normal=np.cross(model[1]-model[0],model[2]-model[0]);normal/=np.linalg.norm(normal)
 if normal[2]<0:normal=-normal
 for sign in(-1,1):
  clipped=[]
  for i in range(len(local)):
   a,b=local[i],local[(i+1)%len(local)];ua,ub=tex[i],tex[(i+1)%len(local)];inside_a=sign*a[0]>=2.88;inside_b=sign*b[0]>=2.88
   if inside_a:clipped.append((a.copy(),ua.copy()))
   if inside_a!=inside_b:
    t=(sign*2.88-a[0])/(b[0]-a[0]);clipped.append((a+t*(b-a),ua+t*(ub-ua)))
  assert len(clipped)>=3
  vertices=[bm.verts.new(mi@Vector(C+Q@p+normal*.015))for p,_ in clipped]
  patch=bm.faces.new(vertices);patch.material_index=gray;patch.smooth=False
  for loop,(_,t)in zip(patch.loops,clipped):loop[uv].uv=t
  floor_rows.append({'station':name,'sourceFloorFace':fi,'outerSide':sign,'innerRedHalfWidth':2.88,'paintStandOff':.015,'vertices':len(clipped)})
bm.to_mesh(o.data);bm.free();o.data.update();report['grayOuterFloorBands']=floor_rows
for n,h in before.items():
 if n not in changed:assert digest(bpy.data.objects[n])==h,('Unrelated mesh changed',n)
for n,(m,props)in joints.items():
 assert np.array_equal(np.array(bpy.data.objects[n].matrix_local),m),('Joint changed',n)
 assert plain(dict(bpy.data.objects[n].items()))==props,('Motion metadata changed',n)
assert all(o.animation_data is None for o in scene.objects)and not bpy.data.actions
with source_path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==source_hash
report.update(unchangedOtherMeshes=len(before)-len(changed),unchangedJointTransforms=len(joints),unchangedJointMetadata=len(joints),animationClips=0)
(review/'source-fit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
asset['version']='0.11.27';bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.27.blend'),compress=True)
print('SEALED_SOURCE_FLANKS',len(report['stations']),len(remove),report['unchangedOtherMeshes'],flush=True)
