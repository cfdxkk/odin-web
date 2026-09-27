"""Fit diagonal butt seams and the unequal ends of the first sliding pair.

Run after revise_side_batteries_v0110.py. Work in each mount's closed frame,
then return each detailed original leaf to its deployed pose for export.
"""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
R=Path(__file__).resolve().parents[1];s=bpy.context.scene;A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted();out=R/'work/v0110-review'
report=json.loads((out/'side-batteries.json').read_text())
light=bpy.data.materials['Odin_Paint_Light'];red=bpy.data.materials['Odin_Bay_Primer']

def mesh(name,rows,parent,to_model,ends,half,flat,sign):
 n=len(rows[0]);pts=[p for row in rows for p in row]
 faces=[(k,k+1,k+1+n,k+n)for k in range(n-1)]
 data=bpy.data.meshes.new(name);data.from_pydata(pts,[],faces);data.update()
 o=bpy.data.objects.new(name,data);s.collection.objects.link(o);o.parent=A;o.data.materials.append(light);o.data.materials.append(red)
 bpy.context.view_layer.objects.active=o;m=o.modifiers.new('Source armor gauge','SOLIDIFY');m.thickness=.23;m.offset=-1;m.material_offset=1;bpy.ops.object.modifier_apply(modifier=m.name)
 bm=bmesh.new();bm.from_mesh(o.data)
 # Seat both thickness edges on the same miter. Across the flat crown the
 # transverse seam is straight; it must not form a V at the center split.
 for v in bm.verts:
  ys=[y+r*(half-max(sign*v.co.x,flat))for y,r,_ in ends]
  v.co.y=min(ys,key=lambda y:abs(y-v.co.y))
 for v in bm.verts:v.co=Vector(to_model(np.array(v.co)))
 bm.to_mesh(o.data);bm.free();o.data.update()
 bpy.context.view_layer.update();world=o.matrix_world.copy();o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_world=world
 return o

for name,row in report.items():
 C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes']);X,B,N=Q.T
 carriage=bpy.data.objects[name+'_Carriage'];advance=2.08
 frontH=np.mean([l['hinge']for l in row['leaves']if l['group']==2],axis=0);rearH=np.mean([l['hinge']for l in row['leaves']if l['group']==3],axis=0)
 rise=float((frontH-rearH)@N);delta=np.array([0,advance,rise]);carriage['slideVector']=list(B*advance);carriage['liftVector']=list(N*rise)
 half=np.mean([abs(((np.array(l['hinge'])-C)@Q)[0])for l in row['leaves']if l['group']==2])
 ridge=np.mean([r['height']for r in row['ridge']if r['group']==2]);flat=np.mean([r['halfWidth']for r in row['ridge']if r['group']==2]);base=np.mean([bpy.data.objects[l['name']]['backingSeatLift']for l in row['leaves']if l['group']==2])
 rake=.42;fore=8.80;panelLength=8.70;seamGap=.026
 seam23=fore-panelLength;seam34=seam23-seamGap-panelLength;rear=seam34-seamGap-panelLength
 ranges={2:(seam23,fore),3:(seam34,seam23-seamGap),4:(rear,seam34-seamGap)}
 def height(x):return ridge if x<=flat else base+(ridge-base)*(half-x)/(half-flat)
 seams={}
 for leaf in row['leaves']:
  j=bpy.data.objects[leaf['name']];group=leaf['group'];sign=-1 if '_Shutter_Port_'in j.name else 1
  H=np.array(leaf['hinge']);rot=np.array(Quaternion(Vector(leaf['axis']),math.radians(j['closedAngleDegrees'])).to_matrix());shift=delta if group>=3 else np.zeros(3)
  def to_model(q):return list(H+rot.T@(C+Q@(q-shift)-H))
  lo,hi=ranges[group]
  # Keep the original grate and perimeter relief. Its rear/front corners are
  # trimmed on inclined planes; no rectangular cut is left at the butt seam.
  for o in list(j.children):
   if o.type!='MESH':continue
   if not o.name.endswith('_Skin'):
    bpy.data.objects.remove(o,do_unlink=True);continue
   M=inv@o.matrix_world;Mi=M.inverted();bm=bmesh.new();bm.from_mesh(o.data)
   for v in bm.verts:
    world=np.array(M@v.co);v.co=Vector(((world-H)@rot.T+H-C)@Q+shift)
   for y,clear_outer in [(lo,False),(hi,True)]:
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,y+rake*half,0),plane_no=(rake*sign,1,0),clear_inner=not clear_outer,clear_outer=clear_outer)
   # The backing is re-cut to the common measured roof plane. Remove the old
   # two broad backing faces; preserve the existing grid, bars and relief.
   bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_area()>12],context='FACES')
   bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
   # Grates and stiffeners belong exclusively to the inner face. Trim old
   # frame returns that would protrude through the smooth shell or its edge.
   slope=(ridge-base)/(half-flat)
   inner_plane=ridge+slope*flat-.25*math.sqrt(1+slope*slope)
   for point,normal in [((sign*(half-.04),0,0),(sign,0,0)),((0,0,inner_plane),(sign*slope,0,1))]:
    cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=point,plane_no=normal,clear_outer=True)
    edges=[e for e in cut['geom_cut']if isinstance(e,bmesh.types.BMEdge)and e.is_boundary]
    if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
   for v in bm.verts:v.co=Mi@Vector(to_model(np.array(v.co)))
   bm.to_mesh(o.data);bm.free();o.data.update()
  rows=[]
  for y in [lo,hi]:rows.append([[sign*x,y+rake*(half-max(x,flat)),height(x)]for x in [.025,flat,half]])
  if sign<0:rows=[list(reversed(r))for r in rows]
  mesh(j.name+'_FittedBacking',rows,j,to_model,[(lo,rake,False),(hi,rake,True)],half,flat,sign)
  j['diagonalSeamRake']=rake;j['closedLongitudinalRange']=[lo,hi];j['carriageSeatModel']=list(Q@shift)
  j['grateFace']='interior';j['exteriorFinish']='continuous hull paint'
  local=j.matrix_world.inverted()@A.matrix_world
  j['crownSeamsLocal']=[[list(local@Vector(to_model(np.array([sign*x,y+rake*(half-flat),ridge]))))for x in [.025,flat]]for y in [lo,hi]]
  if group in [2,3]:
   y=lo if group==2 else hi;edge=[[sign*x,y+rake*(half-x),height(x)]for x in [flat,half]]
   j['closedSeamEdgeModel']=[list(C+Q@np.array(p))for p in edge];seams[j.name]=edge
   local=j.matrix_world.inverted()@A.matrix_world
   j['seamEdgeLocal']=[list(local@Vector(to_model(np.array(p))))for p in edge]
 # First pair: rear edge matches group 2, front edge follows the forward
 # hull shoulder. The unequal rake makes a trapezoid in the leaf's own plane.
 for label,sign in [('Port',-1),('Starboard',1)]:
  j=bpy.data.objects[f'{name}_Slider_{label}']
  for o in list(j.children):bpy.data.objects.remove(o,do_unlink=True)
  y0=fore+.080;y1=row['sliderClosedRange'][1];frontRake=2.0
  rows=[[[sign*x,y+r*(half-max(x,flat)),height(x)]for x in [.025,flat,half]]for y,r in [(y0,rake),(y1,frontRake)]]
  if sign<0:rows=[list(reversed(r))for r in rows]
  mesh(j.name+'_TrapezoidSkin',rows,j,lambda p:list(C+Q@p),[(y0,rake,False),(y1,frontRake,True)],half,flat,sign)
  j['rearEdgeRake']=rake;j['frontEdgeRake']=frontRake;j['planform']='unequal-edge trapezoid';j['slideVector']=list(B*10.2);j['liftVector']=list(N*1.55)
  j['closedOutlineModel']=[list(C+Q@np.array(p))for p in rows[0]+list(reversed(rows[1]))]
 # Fill only the triangular break identified by the user. Retain the rest of
 # the native bay cheeks and their outline; do not blanket the full recess.
 for label,sign in [('Port',-1),('Starboard',1)]:
  outline=[(2.799,1.807,-.642),(5.411,-2.256,-5.011),(5.645,14.249,-5.316)]
  points=[list(C+Q@np.array([sign*x,y,z]))for x,y,z in outline]
  if sign<0:points.reverse()
  data=bpy.data.meshes.new(name+'_Fairing_'+label);data.from_pydata(points,[],[(0,1,2)]);data.update()
  o=bpy.data.objects.new(data.name,data);s.collection.objects.link(o);o.parent=A;o.data.materials.append(light)
  bpy.context.view_layer.objects.active=o;m=o.modifiers.new('Fairing gauge','SOLIDIFY');m.thickness=.15;m.offset=-1;bpy.ops.object.modifier_apply(modifier=m.name)
  o['sideBatteryMechanism']=True;o['surface']='local triangular bay gap only'
 if '_3_'in name:
  # Close the tiny triangular recess in each aft pedestal cheek only. Use
  # its actual three rim vertices so the patch moves with the whole cradle.
  shell=bpy.data.objects[name+'_Carriage_OuterPedestal'];M=inv@shell.matrix_world
  ps=np.array([M@v.co for v in shell.data.vertices]);qs=(ps-C)@Q
  for label,sign in [('Port',-1),('Starboard',1)]:
   targets=[(sign*3.801,-9.417,-3.273),(sign*3.797,-14.238,-3.212),(sign*4.634,-13.784,-4.651)]
   indices=[int(np.argmin(np.linalg.norm(qs-np.array(t),axis=1)))for t in targets]
   assert len(set(indices))==3,(name,label,'recess rim')
   points=[ps[i].tolist()for i in indices]
   if sign<0:points.reverse()
   data=bpy.data.meshes.new(name+'_Carriage_RecessPatch_'+label);data.from_pydata(points,[],[(0,1,2)]);data.update()
   o=bpy.data.objects.new(data.name,data);s.collection.objects.link(o);o.parent=A;o.data.materials.append(light)
   bpy.context.view_layer.update();world=o.matrix_world.copy();o.parent=carriage;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_world=world
   o['surface']='original triangular recess rim cap'
 row['carriageAdvance']=advance;row['carriageLift']=rise;row['diagonalSeamRake']=rake;row['closedSeamEdges']=seams;row['seamGap']=.026;row['sliderRearRake']=rake;row['sliderFrontRake']=frontRake;row['sliderStroke']=10.2;row['sliderLift']=1.55
 print('FITTED EDGES',name,'paired sloped seam',rake,'trapezoid',rake,frontRake,flush=True)
bpy.context.view_layer.update();basis=Matrix.Rotation(-math.pi/2,4,'X');nodes=[]
for o in [A]+[o for o in s.objects if o.get('staticJoint')]:
 m=basis@o.matrix_local@basis.inverted();nodes.append({'name':o.name,'parent':o.parent.name if o.parent else None,'matrix':[m[r][c]for c in range(4)for r in range(4)],'extras':dict(o.items())})
(out/'rig-nodes.json').write_text(json.dumps(nodes,default=lambda v:list(v)));(out/'side-batteries.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.11.0.blend'),compress=True)
