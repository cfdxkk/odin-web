"""Lower and align the seven original side-2/4 covers in their closed pose.

Keep the original armor topology, vent detail and UVs. Replace only the
previous crown extensions. Joint transforms and mechanical timing stay intact.
The original odin.blend is a read-only reference.
"""
import bpy,bmesh,hashlib,json,math
import numpy as np
from pathlib import Path
from mathutils import Quaternion,Vector

root=Path(__file__).resolve().parents[1]
asset=bpy.data.objects['Odin_Asset'];assert asset['version']=='0.11.27'
inv=asset.matrix_world.inverted()
light=bpy.data.materials['Odin_Paint_Light'];red=bpy.data.materials['Odin_Turret_Interior_DeepRed']
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text())
source_fit=json.loads((root/'docs/review/v0.11.26/source-fit.json').read_text())
review=root/'docs/review/v0.11.28';review.mkdir(parents=True,exist_ok=True)
source_path=root.parent/'Odin 建模/odin.blend'
with source_path.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
assert source_hash=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
CROWN_HEIGHTS={2:4.65,4:4.87}
CROWN=4.65;HALF=.30;LOWER=2.88;BASE=6.326-1.58*LOWER
SLOPE=(CROWN-BASE)/(LOWER-HALF)
changed=set();report={'version':'0.11.28','sourceSha256':source_hash,'stations':{}}

def plain(v):
 if hasattr(v,'to_dict'):return{k:plain(x)for k,x in v.to_dict().items()}
 if hasattr(v,'to_list'):return[plain(x)for x in v.to_list()]
 if isinstance(v,dict):return{k:plain(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return[plain(x)for x in v]
 return v

def points(o):
 a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a)
 m=np.array(inv@o.matrix_world);return a.reshape(-1,3)@m[:3,:3].T+m[:3,3]

def digest(o):
 h=hashlib.sha256();h.update(np.array([v.co for v in o.data.vertices],dtype=np.float32).tobytes())
 uv=o.data.uv_layers.active
 for f in o.data.polygons:
  h.update(np.array(f.vertices[:],dtype=np.int32).tobytes());h.update(o.data.materials[f.material_index].name.encode())
  if uv:h.update(np.array([uv.data[k].uv for k in f.loop_indices],dtype=np.float32).tobytes())
 return h.hexdigest()

before={o.name:digest(o)for o in bpy.context.scene.objects if o.type=='MESH'}
joints={o.name:(np.array(o.matrix_local),plain(dict(o.items())))for o in bpy.context.scene.objects if o.get('staticJoint')}
geometry_properties={'crownHalfWidth','closedOuterPlaneLocal'}
def crown(b):return CROWN-.007*b
def base(b):return BASE-.007*b
def profile(x,b):return crown(b)-SLOPE*max(0.,abs(x)-HALF)
def width(x):
 return math.copysign(abs(x)*HALF/.45 if abs(x)<=.45 else HALF+(abs(x)-.45)*(LOWER-HALF)/(LOWER-.45),x)

def trim_extensions(o,count):
 bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=list(bm.verts)[count:],context='VERTS')
 bm.to_mesh(o.data);bm.free();o.data.update()
 assert len(o.data.vertices)==count,(o.name,count,len(o.data.vertices))

def edge(o,q,sign,min_length):
 candidates=[]
 for f in o.data.polygons:
  if o.data.materials[f.material_index]!=light:continue
  for a,b in zip(f.vertices,list(f.vertices[1:])+[f.vertices[0]]):
   if q[a,0]*sign>0 and q[b,0]*sign>0 and abs(q[a,1]-q[b,1])>min_length and max(abs(q[a,0]),abs(q[b,0]))<1.4:
    candidates.append((abs(q[a,0])+abs(q[b,0]),a,b))
 assert candidates,o.name
 _,a,b=min(candidates);return tuple(sorted((a,b),key=lambda k:q[k,1]))

def append_faces(o,to_data,surfaces):
 bm=bmesh.new();bm.from_mesh(o.data);uv=bm.loops.layers.uv.active;new=[]
 gray=o.data.materials.find(light.name);inner=o.data.materials.find(red.name)
 for ps,mat in surfaces:
  vs=[bm.verts.new(Vector(to_data(np.array(p))))for p in ps]
  f=bm.faces.new(vs);f.material_index=gray if mat=='gray'else inner;f.smooth=False;new.append(f)
  if uv:
   for loop in f.loops:loop[uv].uv=(loop.vert.co.x*.025,loop.vert.co.y*.025)
 bmesh.ops.recalc_face_normals(bm,faces=new);bm.to_mesh(o.data);bm.free();o.data.update()

def add_crown(o,q,ids,sign,to_data):
 # Connect the source upper edge to a narrow flat top. All endpoint heights
 # come from the same plane; the lower return has explicit .16 thickness.
 bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();gray=o.data.materials.find(light.name);inner=o.data.materials.find(red.name)
 a,b=ids;top=[bm.verts[a],bm.verts[b]];coordinates=[q[a],q[b]]
 shoulder=[np.array([sign*HALF,q[k,1],crown(q[k,1])])for k in ids]
 seam=[np.array([sign*.02,p[1],p[2]])for p in shoulder]
 # When the original cap already extends inside the shoulder, its source
 # roof supplies the shoulder; extend its actual edge straight to the seam.
 if max(abs(q[a,0]),abs(q[b,0]))<HALF:
  shoulder=[q[a].copy(),q[b].copy()]
 coordinates+=shoulder+seam
 for p in coordinates[2:]:top.append(bm.verts.new(Vector(to_data(p))))
 underside=[bm.verts.new(Vector(to_data(p-np.array([0,0,.16]))))for p in coordinates]
 new=[]
 def face(vs,material):
  if len({tuple(v.co)for v in vs})<3:return
  f=bm.faces.new(vs);f.material_index=material;f.smooth=False;new.append(f)
 for ids in[(0,1,3,2),(2,3,5,4)]:
  face([top[k]for k in ids],gray);face([underside[k]for k in reversed(ids)],inner)
 for ids in[(0,2,4),(1,5,3)]:
  for i,j in zip(ids,ids[1:]):face([top[i],top[j],underside[j],underside[i]],gray)
 face([top[4],top[5],underside[5],underside[4]],gray)
 face([top[1],top[0],underside[0],underside[1]],inner)
 uv=bm.loops.layers.uv.active
 if uv:
  for f in new:
   for loop in f.loops:loop[uv].uv=(loop.vert.co.x*.025,loop.vert.co.y*.025)
 bmesh.ops.recalc_face_normals(bm,faces=new);bm.to_mesh(o.data);bm.free();o.data.update()

def seam_return(o,to_data,sign,b0,b1):
 # The original rolled end rail shares vertices with its gray skin. Its
 # inward red end face can be coplanar at the .02 bank seam, so the small
 # gray overlap sits .006 above that edge rather than showing its primer.
 top=[np.array([sign*x,b,profile(x,b)+.006])for b in(b0,b1)for x in(.02,HALF,LOWER)]
 low=[p-np.array([0,0,.08])for p in top];faces=[]
 for i in range(2):
  ids=[i,i+3,i+4,i+1];faces.append(([top[k]for k in ids],'gray'));faces.append(([low[k]for k in reversed(ids)],'red'))
 for i,j in[(0,1),(1,2),(3,4),(4,5),(0,3),(2,5)]:faces.append(([top[i],top[j],low[j],low[i]],'gray'))
 append_faces(o,to_data,faces)

def center_return(o,to_data,b0,b1):
 ps=[np.array([x,b,crown(b)-depth])for depth in(.003,.083)for b in(b0,b1)for x in(-.055,.055)]
 surfaces=[]
 for ids,mat in[((0,1,3,2),'gray'),((4,6,7,5),'red'),((0,4,5,1),'gray'),((2,3,7,6),'gray'),((0,2,6,4),'gray'),((1,5,7,3),'gray')]:surfaces.append(([ps[k]for k in ids],mat))
 append_faces(o,to_data,surfaces)

for number in(2,4):
 CROWN=CROWN_HEIGHTS[number];SLOPE=(CROWN-BASE)/(LOWER-HALF)
 for side in('Starboard','Port'):
  name=f'SideBattery_{number}_{side}';C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);offset=np.array(bpy.data.objects[name+'_SourceCarriage']['closedOffsetModel']);rows=[]
  for physical_side,sign in[('Port',-1),('Starboard',1)]:
   for i in range(3):
    j=bpy.data.objects[f'{name}_Shutter_{physical_side}_{i:02}'];o=j.children[0]
    count=next(r['originalVertices']for r in source_fit['stations'][name]['leaves']if r['name']==j.name)
    trim_extensions(o,count)
    H=np.array((inv@j.matrix_world).translation);R=np.array(Quaternion(Vector(j['hingeAxisModel']),math.radians(j['closedAngleDegrees'])).to_matrix());move=offset if i==0 else np.zeros(3)
    q=(H+(points(o)-H)@R.T+move-C)@Q;gray={v for f in o.data.polygons if o.data.materials[f.material_index]==light for v in f.vertices}
    factor=(CROWN-BASE)/(5.615-BASE)
    for k in gray:
     q[k,0]=width(q[k,0])
     if abs(q[k,0])<HALF:q[k,0]=math.copysign(HALF,q[k,0])
     q[k,2]=profile(q[k,0],q[k,1])
    for k in range(len(q)):
     # Preserve the original inward ribs and their clear bore cavity. Only
     # shorten tips above the new skin; do not squeeze the complete grates
     # inward or downward into the unchanged barrel's armored breech.
     if k not in gray:q[k,2]=min(q[k,2],profile(q[k,0],q[k,1])-.06)
    rib_feet=[]
    if number==2 and i==0:
     # The source breech is offset toward one cheek. Let the complete
     # diagonal rear rib clear it by widening its lower foot inside the
     # unchanged hinge edge, rather than raising the whole armor roof.
     for k,p in enumerate(q):
      if k not in gray and -17.6<p[1]<-16.8 and p[2]<2.2 and 2.1<abs(p[0])<2.8:
       p[0]=math.copysign(min(2.82,abs(p[0])+.23),p[0]);rib_feet.append(k)
    ids=edge(o,q,sign,6);mi=np.array((inv@o.matrix_world).inverted())
    def to_data(p):return(mi@np.r_[H+(C+Q@p-H-move)@R,1])[:3]
    for v,p in zip(o.data.vertices,q):v.co=Vector(to_data(p))
    o.data.update();add_crown(o,q,ids,sign,to_data)
    b0,b1=j['closedBankRange']
    if i>0:seam_return(o,to_data,sign,b0-.075,b0+.025)
    if i==2:seam_return(o,to_data,sign,b1-.025,b1+.35)
    if sign<0:center_return(o,to_data,b0-.03,b1+.03)
    j['crownHalfWidth']=HALF;j['closedOuterPlaneLocal']=[-SLOPE,-.007,CROWN+SLOPE*HALF]
    o['alignedLowCrown']=True;o['fittedFlatCrown']=True;o['crownThickness']=.16;changed.add(o.name)
    rows.append({'mesh':o.name,'originalVertices':count,'originalPolygons':int(o['sourceFaceCount']),'exteriorHeightRatio':factor,'oldCrownAtB0':5.615,'newCrownAtB0':CROWN,'crownHalfWidth':HALF,'closedBankRange':[b0,b1],'upperSourceEdge':q[list(ids)].tolist(),'fittedInnerRibFeet':rib_feet})
  cap=bpy.data.objects[name+'_FrontCap'];o=cap.children[0];count=source_fit['stations'][name]['originalCapVertices'];trim_extensions(o,count)
  slide=np.array(cap['slideVector']);q=(points(o)+slide-C)@Q;gray={v for f in o.data.polygons if o.data.materials[f.material_index]==light for v in f.vertices}
  leading=float(np.median(q[(np.abs(q[:,0])<.4)&(q[:,1]>15),1]))
  for k in gray:
   q[k,0]=width(q[k,0])
   if abs(q[k,0])<HALF:q[k,0]=math.copysign(HALF,q[k,0])
   q[k,2]=profile(q[k,0],q[k,1])
  for k in range(len(q)):
   if k not in gray:q[k,2]=min(q[k,2],profile(q[k,0],q[k,1])-.06)
  ids=[edge(o,q,s,10)for s in(-1,1)];mi=np.array((inv@o.matrix_world).inverted())
  def to_data(p):return(mi@np.r_[C+Q@p-slide,1])[:3]
  for v,p in zip(o.data.vertices,q):v.co=Vector(to_data(p))
  o.data.update()
  for sign,edgeids in zip((-1,1),ids):add_crown(o,q,edgeids,sign,to_data)
  center_return(o,to_data,9.395,leading)
  o['alignedLowCrown']=True;changed.add(o.name)
  # Remove a small high cheek lip over the new closed roof. The barrel,
  # bearing, floor and fixed pivot coordinates are not moved.
  shell=bpy.data.objects[name+'_OriginalTurretShell'];p=points(shell);sq=(p+offset-C)@Q;edited=[];mi=np.array((inv@shell.matrix_world).inverted())
  for k,v in enumerate(shell.data.vertices):
   x,b,n=sq[k]
   if 1.45<abs(x)<3.1 and -18<b<-7.8 and n>profile(x,b)-.06:
    sq[k,2]=profile(x,b)-.06;v.co=Vector((mi@np.r_[C+Q@sq[k]-offset,1])[:3]);edited.append(k)
  if edited:shell.data.update();changed.add(shell.name)
  report['stations'][name]={'leaves':rows,'capMesh':o.name,'originalCapVertices':count,'originalCapPolygons':int(o['sourceFaceCount']),'capLeadingB':leading,'crownIntercept':CROWN,'crownLongitudinalSlope':-.007,'flatCrownWidth':2*HALF,'sideSlope':SLOPE,'heightReduction':5.615-CROWN,'trimmedTurretCheekVertices':edited}

# Keep the fixed receiver continuous with the new front-cap plane. Re-angle
# only the local upper nose/fairing and its inward return, retaining topology.
fixed_rows=[]
for mesh in('holo.001','Flank24_OriginalFixedHull'):
 o=bpy.data.objects[mesh];p=points(o);mi=np.array((inv@o.matrix_world).inverted());changes={}
 for name in report['stations']:
  CROWN=report['stations'][name]['crownIntercept'];SLOPE=report['stations'][name]['sideSlope']
  C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);q=(p-C)@Q
  selected=np.where((abs(q[:,0])<1.6)&(q[:,1]>19.5)&(q[:,1]<33)&(q[:,2]>2.30)&(q[:,2]<6))[0]
  roof=set()
  for f in o.data.polygons:
   ps=q[list(f.vertices)]
   if o.data.materials[f.material_index]==light and max(abs(ps[:,0]))<1.6 and ps[:,1].min()>20 and ps[:,1].max()<33 and ps[:,2].min()>3.5:roof.update(f.vertices)
  for k in selected:
   x,b,n=q[k];oldcrest=5.03+.007*(b-21.89);factor=(crown(b)-base(b))/(oldcrest-base(b));q[k,2]=base(b)+(n-base(b))*factor
   if k in roof:
    if abs(x)<.4:q[k,0]=math.copysign(HALF,x)
    q[k,2]=profile(q[k,0],b)
   changes[int(k)]=C+Q@q[k]
  if len(selected):fixed_rows.append({'mesh':mesh,'station':name,'upperReceiverVertices':list(map(int,selected)),'roofVertices':sorted(roof)})
 for k,p in changes.items():o.data.vertices[k].co=Vector((mi@np.r_[p,1])[:3])
 if changes:o.data.update();changed.add(o.name)
report['fixedReceiverFit']=fixed_rows

# Exactly two isolated one-face scraps, one beside each side-4 housing.
o=bpy.data.objects['holo.001'];removed=[];bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table()
for index in(44592,46198):
 f=bm.faces[index];assert len(f.verts)==3 and all(len(v.link_faces)==1 for v in f.verts)
 removed.append({'mesh':o.name,'face':index,'pointsModel':[list((inv@o.matrix_world)@v.co)for v in f.verts]})
bmesh.ops.delete(bm,geom=[bm.faces[i]for i in(44592,46198)],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(o.data);bm.free();o.data.update();changed.add(o.name)
report['removedFloatingTriangles']=removed
for name,h in before.items():
 if name not in changed:assert digest(bpy.data.objects[name])==h,('Unrelated mesh changed',name)
for name,(m,props)in joints.items():
 o=bpy.data.objects[name];assert np.array_equal(np.array(o.matrix_local),m),('Joint transform changed',name)
 now=plain(dict(o.items()));assert{k:v for k,v in props.items()if k not in geometry_properties}=={k:v for k,v in now.items()if k not in geometry_properties},('Motion metadata changed',name)
assert not bpy.data.actions and all(o.animation_data is None for o in bpy.context.scene.objects)
with source_path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==source_hash
report.update(unchangedOtherMeshes=len(before)-len(changed),unchangedJointTransforms=len(joints),unchangedMechanicalMetadata=len(joints),animationClips=0,changedMeshes=sorted(changed))
(review/'source-fit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
asset['version']='0.11.28';bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.28.blend'),compress=True)
print('LOWERED_FLANK_CROWNS',CROWN,HALF,len(changed),len(removed),flush=True)
