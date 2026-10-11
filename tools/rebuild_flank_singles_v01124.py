"""Restore side singles 2/4 from the read-only source before rebuilding armor.

Run on v0.11.23. Recover fixed faces by source topology, never by the facing
direction of a polygon. Reuse the source front shells without re-profiling.
All original channel grates remain fixed; missing covers reuse the completed flank armor assets.
Only static joints are saved; the original barrel curves run in Nuxt.
"""
import bpy,bmesh,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

root=Path(__file__).resolve().parents[1]
asset=bpy.data.objects['Odin_Asset'];assert asset['version']=='0.11.23'
inv=asset.matrix_world.inverted();scene=bpy.context.scene
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text(encoding='utf8'))
review=root/'docs/review/v0.11.24';review.mkdir(parents=True,exist_ok=True)
source_path=root.parent/'Odin 建模/odin.blend'
with source_path.open('rb') as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
light=bpy.data.materials['Odin_Paint_Light'];red=bpy.data.materials['Odin_Turret_Interior_DeepRed']
changed=set();removed=set();joint_changes=set();report={'sourceSha256':source_hash,'stations':{}}

def points(o):return np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])
def face_key(p):return tuple(sorted(tuple(round(float(a),4)for a in v)for v in p))
def digest(o):
 h=hashlib.sha256();p=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',p);h.update(p.tobytes())
 for f in o.data.polygons:h.update(np.array(f.vertices[:],dtype=np.int32).tobytes());h.update(o.data.materials[f.material_index].name.encode())
 return h.hexdigest()
before={o.name:digest(o)for o in scene.objects if o.type=='MESH'}
joints={o.name:np.array(o.matrix_local).copy()for o in scene.objects if o.get('staticJoint')}

# The completed vertical flank's actual covers are the armor template. The
# source hull grates and their triangular supporting frames remain on the hull.
template='SideBattery_1_Starboard';TC=np.array(frames[template]['frameOrigin']);TQ=np.array(frames[template]['frameAxes'])
carriage=bpy.data.objects[template+'_Carriage'];carriage_closed=np.array(carriage['liftVector'])+np.array(carriage['slideVector'])
armor_templates=[]
for i in range(3):
 j=bpy.data.objects[f'{template}_Shutter_Port_{i:02}'];H=np.array(j['sourceHingeLine']);R=np.array(Quaternion(Vector(j['hingeAxisModel']),math.radians(j['closedAngleDegrees'])).to_matrix())
 offset=carriage_closed if j.parent==carriage else np.zeros(3)
 parts={c.name.rsplit('_',1)[-1]:(c,(H+(points(c)-H)@R.T+offset-TC)@TQ)for c in j.children if c.type=='MESH'}
 armor_templates.append(parts)

def template_point(p,roof,a,b,width,flat,center,zline,sign):
 aft=roof[[2,1,0]];fore=roof[[5,4,3]];x=abs(p[0]);t=.5
 for _ in range(12):
  xs=abs(aft[:,0])*(1-t)+abs(fore[:,0])*t;col=0 if x<=xs[1] else 1
  u=np.clip((x-xs[col])/(xs[col+1]-xs[col]),0,1)
  lo=aft[col]*(1-u)+aft[col+1]*u;hi=fore[col]*(1-u)+fore[col+1]*u
  t=np.clip((p[1]-lo[1])/(hi[1]-lo[1]),0,1)
 y=a*(1-t)+b*t;ridge=zline(y);tx=[center,flat,width][col]*(1-u)+[center,flat,width][col+1]*u
 tz=ridge-cross_slope*max(0,tx-flat)
 # Keep the relief just inside the backing; do not carry broad source-hull
 # braces into the moving cover or push the reinforcement toward the bore.
 depth=.6*(p[2]-(lo[2]*(1-t)+hi[2]*t))
 return np.array([sign*tx,y,tz+np.clip(depth-.10,-.30,-.18)])

def erase(o):
 for c in list(o.children):erase(c)
 removed.add(o.name);data=o.data if o.type=='MESH'else None;bpy.data.objects.remove(o,do_unlink=True)
 if data and data.users==0:bpy.data.meshes.remove(data)

def set_points(o,p):
 inverse=(inv@o.matrix_world).inverted()
 for v,q in zip(o.data.vertices,p):v.co=inverse@Vector(q)
 o.data.update();changed.add(o.name)

def source_faces(source,name,ids,parent,coords):
 cp=source.copy();cp.data=source.data.copy();cp.animation_data_clear();cp.modifiers.clear();scene.collection.objects.link(cp);cp.name=name
 cp.parent=asset;cp.matrix_parent_inverse=Matrix.Identity(4);cp.matrix_local=Matrix.Identity(4)
 # Transform before extraction so source face indices and UV loops are retained.
 for v,p in zip(cp.data.vertices,coords):v.co=Vector(p)
 bm=bmesh.new();bm.from_mesh(cp.data);bm.faces.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in ids],context='FACES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(cp.data);bm.free()
 for i,m in enumerate(cp.data.materials):
  label=m.name.lower()if m else''
  cp.data.materials[i]=bpy.data.materials['Odin_Paint_Orange']if'orange'in label else bpy.data.materials['Odin_Paint_Dark.001']if'dark'in label else light
 bpy.context.view_layer.update();world=cp.matrix_world.copy();cp.parent=parent;cp.matrix_world=world
 cp['sourceObject']='holo.001';cp['sourceGeometry']=True;changed.add(cp.name);return cp

with bpy.data.libraries.load(str(source_path),link=False)as(src,dst):dst.objects=['holo.001','odin.023','odin.071']
source,g2,g4=dst.objects
for o in dst.objects:scene.collection.objects.link(o)
scene.frame_set(1);bpy.context.view_layer.update()
sp=np.array([source.matrix_world@v.co for v in source.data.vertices])
parents=list(range(len(sp)))
def find(i):
 while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
 return i
for e in source.data.edges:a,b=e.vertices;parents[find(a)]=find(b)
groups={};group_faces={}
for v in source.data.vertices:groups.setdefault(find(v.index),[]).append(v.index)
for f in source.data.polygons:group_faces.setdefault(find(f.vertices[0]),[]).append(f.index)

static_keys=set()
for o in scene.objects:
 if o.type!='MESH'or o in dst.objects:continue
 if o.parent and (o.parent.get('barrelJoint')or o.parent.get('system')=='single-front-cap'):continue
 p=points(o)
 for f in o.data.polygons:static_keys.add(face_key(p[list(f.vertices)]))
remove_keys=set();restore_ids=set();expected_fixed=set();source_moving=set();fixtures={}

for number,original_gun in [(2,g2),(4,g4)]:
 curves=[]
 for layer in original_gun.animation_data.action.layers:
  for strip in layer.strips:
   bag=strip.channelbag(original_gun.animation_data.action_slot)
   if bag:curves+=list(bag.fcurves)
 euler_curves=sorted([c for c in curves if c.data_path=='rotation_euler'],key=lambda c:c.array_index)
 start=[float(c.keyframe_points[0].co[1])for c in euler_curves];end=[float(c.keyframe_points[-1].co[1])for c in euler_curves]
 start_frame=float(euler_curves[0].keyframe_points[0].co[0]);end_frame=float(euler_curves[0].keyframe_points[-1].co[0])
 for c in euler_curves:
  assert len(c.keyframe_points)==2
  a,b=c.keyframe_points
  assert abs(a.handle_right.y-a.co.y)<1e-6 and abs(b.handle_left.y-b.co.y)<1e-6
  assert abs(a.handle_right.x-(2*a.co.x+b.co.x)/3)<1e-5 and abs(b.handle_left.x-(a.co.x+2*b.co.x)/3)<1e-5
 scene.frame_set(1);bpy.context.view_layer.update()
 gm=original_gun.matrix_world.copy();gp=np.array([gm@v.co for v in original_gun.data.vertices]);gun_origin=np.array(gm.translation)
 local_rotation=original_gun.rotation_euler.to_quaternion()
 parent_rotation=gm.to_quaternion()@local_rotation.inverted()
 for hull_side,mirror in [('Starboard',1),('Port',-1)]:
  name=f'SideBattery_{number}_{hull_side}';fr=frames[name];C=np.array(fr['frameOrigin']);Q=np.array(fr['frameAxes']);q=(sp-C)@Q
  selected=[];nose=[]
  for gid,ids in groups.items():
   p=q[ids];lo=p.min(0);hi=p.max(0)
   if max(abs(p[:,0]))>6 or lo[1]<-18 or hi[1]>33 or lo[2]<-6 or hi[2]>8:continue
   if len(ids)==18 and lo[1]>17 and hi[1]>29:nose.append(gid);continue
   # Inventory disconnected source grates for the preservation audit. The 102-vertex trough,
   # 18-vertex support cheeks and 184-vertex transverse bearings stay fixed.
   if len(ids)in(18,102,184):continue
   # The raised bank is also retained as original structure; animation uses
   # the completed flank cover assets instead of dismantling source grates.
   if lo[0]*hi[0]<=0 or min(abs(lo[0]),abs(hi[0]))<2.4 or hi[1]>-8.15 or lo[2]<.4:continue
   selected.append(gid)
  assert len(nose)==2,(name,nose)
  moving_ids={fi for gid in nose for fi in group_faces[gid]}
  source_moving |= moving_ids
  for fi in moving_ids:remove_keys.add(face_key(sp[list(source.data.polygons[fi].vertices)]))
  # Restore all original local fixed faces, including faces on large hull
  # components. Exclude only the positively identified moving islands.
  fixed_ids=set()
  for f in source.data.polygons:
   p=q[list(f.vertices)];lo=p.min(0);hi=p.max(0)
   if max(abs(p[:,0]))<10 and lo[1]>-33 and hi[1]<36 and lo[2]>-10 and hi[2]<17 and f.index not in moving_ids:
    fixed_ids.add(f.index);k=face_key(sp[list(f.vertices)]);expected_fixed.add(k)
    if k not in static_keys:restore_ids.add(f.index);static_keys.add(k)
  obsolete=[o.name for o in scene.objects if o.name.startswith(name+'_')and ('_Shutter_'in o.name or '_FrontCap'in o.name or '_FixedSlotLips'in o.name)and o.parent==asset]
  for old_name in obsolete:erase(bpy.data.objects[old_name])
  gun=bpy.data.objects[name]
  for child in list(gun.children):erase(child)
  for key in list(gun.keys()):
   if key not in ['system','staticJoint']:del gun[key]
  origin=gun_origin*np.array([mirror,1,1]);gun.matrix_local=Matrix.Translation(Vector(origin));joint_changes.add(gun.name)
  gun['singleBattery']=True;gun['sourceEulerMotion']=True;gun['sourceObject']=f'odin.{23 if number==2 else 71:03d}'
  gun['sourceEulerStart']=start;gun['sourceEulerEnd']=end;gun['sourceParentRotationWXYZ']=list(parent_rotation)
  gun['sourceMirror']=mirror;gun['sourceFrameRange']=[start_frame,end_frame];gun['sourceMotionStart']=start_frame/100;gun['sourceMotionEnd']=end_frame/100
  gun['hingeAxisModel']=Q[:,0].tolist();gun['outwardNormal']=Q[:,2].tolist();gun['trunnionAdvance']=0.
  gun['sourceBoreDirectionModel']=Q[:,1].tolist();gun['stowSink']=0.
  child=original_gun.copy();child.data=original_gun.data.copy();child.modifiers.clear();child.animation_data_clear();scene.collection.objects.link(child);child.name=name+'_SourceBarrel'
  child.parent=gun;child.matrix_parent_inverse=Matrix.Identity(4);child.matrix_local=Matrix.Identity(4)
  for v,p in zip(child.data.vertices,gp):v.co=Vector(p*np.array([mirror,1,1])-origin)
  if mirror<0:
   bm=bmesh.new();bm.from_mesh(child.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(child.data);bm.free()
  for i,m in enumerate(child.data.materials):child.data.materials[i]=bpy.data.materials['Odin_Weapon_Steel']
  child['sourceGeometry']=True;child['sourceObject']=gun['sourceObject'];changed.add(child.name)
  bpy.context.view_layer.update()
  assert np.max(abs(points(child)-gp*np.array([mirror,1,1])))<.00004
  cap=bpy.data.objects.new(name+'_FrontCap',None);scene.collection.objects.link(cap);cap.parent=asset;cap.location=C.tolist()
  cap['staticJoint']=True;cap['system']='single-front-cap';cap['barrel']=name;cap['sourceOpenPose']=True;cap['sourceRigidCap']=True
  cap['sourceObject']='holo.001';cap['sourceCapStroke']=True;cap['armorThickness']=.25
  clearance_height=1.35;parking_advance=3.0
  clearance=Q[:,2]*clearance_height+Q[:,1]*parking_advance
  cap['sourceClearanceOffsetModel']=clearance.tolist()
  capids={fi for gid in nose for fi in group_faces[gid]};skin=source_faces(source,name+'_FrontCap_Skin',capids,cap,sp+clearance)
  capq=(points(skin)-C)@Q
  # Seat the source shell's fore lip on the unchanged raised source receiver.
  cap_fore=capq[capq[:,1]>capq[:,1].max()-.04]
  target=np.mean([q[np.argmin(np.linalg.norm(q-np.array([s*.344,21.892,5.030]),axis=1))]for s in [-1,1]],axis=0)
  dy=float(target[1]-cap_fore[:,1].mean());dz=float(target[2]+clearance_height-cap_fore[:,2].max())
  offset=Q@np.array([0,dy,dz]);lift=.60*Q[:,2];advance=-dy*Q[:,1];settle=-dz*Q[:,2]-lift
  cap['slideVector']=offset.tolist();cap['settleVector']=[0.,0.,0.];cap['clearanceLiftVector']=lift.tolist();cap['advanceVector']=advance.tolist();cap['parkingSettleVector']=settle.tolist()
  cap['slideStart']=.10;cap['slideEnd']=.23;cap['settleStart']=.24;cap['settleEnd']=.26
  cap['originalOpenBounds']=[capq.min(0).tolist(),capq.max(0).tolist()]
  skin['sourceRigidCap']=True
  cap.data=None
  # The original folded interior uses red; original outside coordinates/UVs
  # are kept. Inconsistent source face winding cannot recolor the outer roof.
  skin.data.materials.append(red);ri=len(skin.data.materials)-1
  cap_local=(points(skin)-clearance-C)@Q
  for f in skin.data.polygons:
   p=cap_local[list(f.vertices)];side=1 if p[:,0].mean()>0 else-1
   source_half=[g for g in nose if np.mean(q[groups[g]],axis=0)[0]*side>0][0]
   broad=max((source.data.polygons[i]for i in group_faces[source_half]),key=lambda f:f.area)
   coords=q[list(broad.vertices)];plane=np.linalg.lstsq(np.c_[coords[:,:2],np.ones(len(coords))],coords[:,2],rcond=None)[0]
   gaps=p[:,2]-(np.c_[p[:,:2],np.ones(len(p))]@plane)
   if gaps.mean()<-.06 and gaps.max()<-.005:f.material_index=ri
  # A newly made lower sealing return joins the unchanged source shell to
  # the original receiver; no source cap vertex is stretched or re-profiled.
  seal_points=[];seal_faces=[];seal_materials=[]
  for gid in nose:
   ids=groups[gid];half=q[ids];sgn=1 if half[:,0].mean()>0 else-1
   rear=half[half[:,1]<half[:,1].min()+.12];fore=half[half[:,1]>half[:,1].max()-.04]
   outer_rear=rear[np.argmax(abs(rear[:,0]))]
   fore_outer=half[np.argmin(np.linalg.norm(half-np.array([sgn*1.49,28.82,4.05]),axis=1))]
   fore_flat=fore[np.argmax(abs(fore[:,0]))];fore_center=fore[np.argmin(abs(fore[:,0]))]
   rear_center=rear[np.argmin(abs(rear[:,0]))]
   border=[outer_rear,fore_outer,fore_flat,fore_center]
   for a,b in zip(border,border[1:]):
    base=len(seal_points);seal_points += [C+Q@(p+np.array([0,parking_advance,0]))for p in[a,b,b+np.array([0,0,clearance_height]),a+np.array([0,0,clearance_height])]]
    seal_faces.append(tuple(base+i for i in (range(4) if sgn>0 else reversed(range(4)))));seal_materials.append(0)
   # Complete the absent ridge strip, leaving a small mechanical centre seam.
   base=len(seal_points);a=rear_center+np.array([0,0,clearance_height]);b=fore_center+np.array([0,0,clearance_height]);c=b.copy();d=a.copy();c[0]=d[0]=sgn*.015
   seal_points += [C+Q@(p+np.array([0,parking_advance,0]))for p in[a,b,c,d]];seal_faces.append(tuple(base+i for i in (range(4) if sgn>0 else reversed(range(4)))));seal_materials.append(0)
  me=bpy.data.meshes.new(name+'_FrontCap_SealingReturns');me.from_pydata(seal_points,[],seal_faces);me.materials.append(light);me.materials.append(red)
  seal=bpy.data.objects.new(me.name,me);scene.collection.objects.link(seal);seal.parent=cap;seal.matrix_local=Matrix.Translation(Vector(-C))
  mod=seal.modifiers.new('Missing cap sealing gauge','SOLIDIFY');mod.thickness=.10;mod.offset=-1;mod.material_offset=1
  bpy.context.view_layer.objects.active=seal;bpy.ops.object.modifier_apply(modifier=mod.name);changed.add(seal.name)
  closed=cap_local+np.array([0,dy+parking_advance,dz+clearance_height]);rear_b=float(closed[:,1].min());rear_pts=closed[closed[:,1]<rear_b+.12]
  center=float(np.min(abs(rear_pts[:,0])));flat=float(np.min(abs(rear_pts[rear_pts[:,2]>rear_pts[:,2].max()-.04,0][abs(rear_pts[rear_pts[:,2]>rear_pts[:,2].max()-.04,0])>.4])))
  width=float(np.max(abs(rear_pts[:,0])));z_front=float(rear_pts[:,2].max())
  outer=float(np.mean(rear_pts[abs(rear_pts[:,0])>width-.04,2]));cross_slope=(z_front-outer)/(width-flat)
  start_b=-17.63;end_b=rear_b-.025;segments=[start_b,-8.19,.52,end_b]
  # The continuous missing outer skin follows the original rear bearing
  # height and the intact source front shell, without reshaping the hull.
  back_brackets=[q[ids]for gid,ids in groups.items()if len(ids)==184 and max(abs(q[ids,0]))<3 and -16<q[ids,1].mean()<-15]
  back_outer=float(np.max(np.concatenate(back_brackets)[:,2]))-.10
  z_rear=back_outer+cross_slope*(width-flat);rake=(z_front-z_rear)/(end_b-start_b)
  def z(y):return z_rear+rake*(y-start_b)
  row={'fixedSourceFaces':len(fixed_ids),'sourceCapVertices':len(skin.data.vertices),'sourceCapFaces':len(skin.data.polygons),'capRigidOffsetLocal':[0,dy,dz],'capClearanceOffsetLocal':[0,parking_advance,clearance_height],'sourceCapCoordinateError':float(np.max(abs(points(skin)-clearance-sp[sorted({i for fi in capids for i in source.data.polygons[fi].vertices})]))),'retainedFixedGrateIslands':len(selected),'leaves':[]}
  for leaf,sign in [('Port',-1),('Starboard',1)]:
   for i,(a,b)in enumerate(zip(segments,segments[1:])):
    contact_z=[(3.42,3.52),(1.84,1.95),(1.95,1.985)][i]
    contact=np.array([[sign*2.50,a,contact_z[0]],[sign*2.50,b,contact_z[1]]])
    H=C+Q@contact[0];axis=Q@(contact[1]-contact[0]);axis/=np.linalg.norm(axis)
    j=bpy.data.objects.new(f'{name}_Shutter_{leaf}_{i:02d}',None);scene.collection.objects.link(j);j.parent=asset;j.location=H.tolist()
    j['staticJoint']=True;j['system']='single-shutter';j['barrelJoint']=name;j['panelIndex']=i;j['physicalHinge']=True
    j['hingeAxisModel']=axis.tolist();j['closedAngleDegrees']=-sign*150.;j['openingTravelDegrees']=95.;j['openStart']=.27+.02*i;j['openEnd']=.37+.022*i
    j['armorTemplate']=f'{template}_Shutter_Port_{i:02}';j['sourceObject']='accepted-flank-armor';j['sourceFlankTemplate']=True
    j['sourceGeometry']=True;j['armorThickness']=.25;j['coverRole']='missing-exterior-armor';j['fixedHullFacesRemoved']=0
    roof=np.array([[sign*x,y,z(y)-cross_slope*max(0,x-flat)]for y in[a,b]for x in[width,flat,center]])
    # A constant-gauge exterior shell over the original inward grate detail.
    n=np.array([sign*cross_slope,-rake,1]);n/=np.linalg.norm(n);back=roof-.25*n
    lower=contact.copy();lower[:,2]-=.025;lower_back=lower-.14*np.array([sign,0,0])
    model=C+np.concatenate([roof,back,lower,lower_back])@Q.T
    fs=[(0,1,4,3),(1,2,5,4),(9,10,7,6),(10,11,8,7),(0,6,7,1),(1,7,8,2),(3,4,10,9),(4,5,11,10),(0,3,9,6),(2,8,11,5)]
    fs += [(0,3,13,12),(6,14,15,9),(12,13,15,14),(0,12,14,6),(3,9,15,13)]
    if sign>0:fs=[tuple(reversed(f))for f in fs]
    mesh=bpy.data.meshes.new(j.name+'_OuterSkin');mesh.from_pydata(model,[],fs);mesh.materials.append(light);mesh.materials.append(red)
    shell=bpy.data.objects.new(j.name+'_OuterSkin',mesh);scene.collection.objects.link(shell);shell.parent=j;shell.matrix_local=Matrix.Identity(4)
    for f in mesh.polygons:f.material_index=1 if f.index in[2,3]else 0
    source_skin,source_points=armor_templates[i]['Skin'];source_roof=armor_templates[i]['FittedBacking'][1][:6]
    fitted=np.array([template_point(p,source_roof,a,b,width,flat,center,z,sign)for p in source_points]);fitted_model=C+fitted@Q.T
    grate=bpy.data.objects.new(j.name+'_FlankReinforcement',source_skin.data.copy());scene.collection.objects.link(grate);grate.parent=j;grate.matrix_local=Matrix.Identity(4)
    bpy.context.view_layer.update();set_points(grate,fitted_model)
    grate['armorTemplate']=source_skin.name;grate.data.materials.clear();grate.data.materials.append(red)
    for f in grate.data.polygons:f.material_index=0
    turn=np.array(Quaternion(Vector(axis),math.radians(-float(j['closedAngleDegrees']))).to_matrix())
    for o in[shell,grate]:
     closed_points=model if o==shell else fitted_model
     set_points(o,H+(closed_points-H)@turn.T)
    j['hingeEdgeModel']=[H.tolist(),(C+Q@contact[1]).tolist()];j['closedEndEdgesModel']=[[(C+Q@roof[k]).tolist()for k in pair]for pair in[(0,2),(3,5)]]
    row['leaves'].append({'name':j.name,'armorTemplate':source_skin.name,'vertices':len(grate.data.vertices),'fixedSourceFacesRemoved':0})
  report['stations'][name]=row
  samples=[]
  for f in[start_frame,start_frame+7,(start_frame+end_frame)/2,end_frame-6,end_frame]:
   scene.frame_set(int(f),subframe=f-int(f));m=original_gun.matrix_world.copy()
   samples.append({'frame':f,'deployment':f/100,'origin':(np.array(m.translation)*np.array([mirror,1,1])).tolist(),'vertices':{str(i):(np.array(m@original_gun.data.vertices[i].co)*np.array([mirror,1,1])).tolist()for i in[0,100]}})
  fixtures[name]=samples

scene.frame_set(1);bpy.context.view_layer.update()
hull=bpy.data.objects['holo.001'];p=points(hull)
bm=bmesh.new();bm.from_mesh(hull.data);bm.faces.ensure_lookup_table()
erase_faces=[];legacy_fragments=0
region_frames=[(np.array(frames[name]['frameOrigin']),np.array(frames[name]['frameAxes']))for name in report['stations']]
for f in bm.faces:
 coords=np.array([inv@hull.matrix_world@v.co for v in f.verts]);k=face_key(coords)
 if k in remove_keys:erase_faces.append(f);continue
 if k in expected_fixed:continue
 for C,Q in region_frames:
  local=(coords-C)@Q;lo=local.min(0);hi=local.max(0)
  if max(abs(local[:,0]))<10 and lo[1]>-33 and hi[1]<36 and lo[2]>-10 and hi[2]<17:
   erase_faces.append(f);legacy_fragments+=1;break
bmesh.ops.delete(bm,geom=erase_faces,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(hull.data);bm.free();changed.add(hull.name)
support=source_faces(source,'Flank24_OriginalFixedHull',restore_ids,asset,sp);support['fixedSourceFaces']=len(restore_ids);support['sourcePreservation']=True
support.data.materials.append(red)
supp=points(support)
for f in support.data.polygons:
 centroid=supp[list(f.vertices)].mean(0)
 for name in report['stations']:
  C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);l=(centroid-C)@Q;n=np.array(f.normal)@Q
  if abs(l[0])<2.85 and -20<l[1]<23 and (n[2]>.5 or n[0]*l[0]<-.5):f.material_index=len(support.data.materials)-1
for o in list(dst.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.context.view_layer.update()
actual_fixed=set()
for o in scene.objects:
 if o.type!='MESH'or(o.parent and (o.parent.get('barrelJoint')or o.parent.get('system')=='single-front-cap')):continue
 p=points(o)
 for f in o.data.polygons:actual_fixed.add(face_key(p[list(f.vertices)]))
assert expected_fixed<=actual_fixed,('Missing source fixed faces',len(expected_fixed-actual_fixed))
assert not source_moving.intersection(restore_ids)
for name,h in before.items():
 if name not in changed and name not in removed:assert digest(bpy.data.objects[name])==h,('Unexpected mesh change',name)
for name,m in joints.items():
 if name not in joint_changes and name not in removed:assert np.array_equal(np.array(bpy.data.objects[name].matrix_local),m),('Unexpected joint',name)
report.update(restoredFixedFaces=len(restore_ids),removedLegacyStaticFragments=legacy_fragments,verifiedOriginalFixedFaces=len(expected_fixed),fixedFacesOnMovingJoints=0,unchangedMeshes=len(before)-len(removed&set(before))-len(changed&set(before)),unchangedOtherJoints=len(joints)-len(removed&set(joints))-len(joint_changes),animationClips=0)
with source_path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==source_hash
for o in scene.objects:o.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
asset['version']='0.11.24'
(review/'source-restoration.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(root/'tests/fixtures/flank-source-motion-v01124.json').write_text(json.dumps(fixtures,indent=2),encoding='utf8')
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.24.blend'),compress=True)
print('SOURCE_RESTORATION',json.dumps({k:v for k,v in report.items()if k!='stations'}),flush=True)
