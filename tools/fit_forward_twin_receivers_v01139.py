"""Clip original fixed receiver side surfaces against separate source sweeps.

Surface clipping does not require the imported hood to be a manifold solid.
It preserves the source triangles, painted UVs and loop normals outside the
small local clearance cuts. Original moving meshes and every rest frame stay
unchanged; the central source canopy is never widened, moved or lifted.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Quaternion,Vector
root=Path(__file__).resolve().parents[1];A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted();basis=Quaternion((1,0,0),-math.pi/2)
rows=json.loads((root/'work/v01139-review/runtime-poses.json').read_text())
rest={o.name:(o.location.copy(),o.rotation_mode,o.rotation_euler.copy(),o.rotation_quaternion.copy(),o.rotation_axis_angle[:],o.scale.copy())for o in bpy.context.scene.objects if o.get('staticJoint')and o.name.startswith(tuple(f'Defense_{i:02}_'for i in range(1,5)))}
def restore():
 for name,(location,mode,euler,quaternion,axisAngle,scale)in rest.items():
  o=bpy.data.objects[name];o.location=location;o.rotation_mode=mode;o.rotation_euler=euler;o.rotation_quaternion=quaternion;o.rotation_axis_angle=axisAngle;o.scale=scale
 bpy.context.view_layer.update()
def groups(o):
 links=[[]for v in o.data.vertices]
 for edge in o.data.edges:
  a,b=edge.vertices;links[a].append(b);links[b].append(a)
 seen=set();parts=[]
 for i in range(len(links)):
  if i in seen:continue
  todo=[i];part={i};seen.add(i)
  while todo:
   for j in links[todo.pop()]:
    if j not in seen:seen.add(j);part.add(j);todo.append(j)
  parts.append(part)
 return parts
def apply(row,station):
 for j in row['joints']:
  if not j['name'].startswith(tuple(f'Defense_{i:02}_'for i in range(1,5))):continue
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);x,y,z,w=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((w,x,y,z))@basis
 bpy.context.view_layer.update()
def planeClip(poly,normal,distance,inside):
 output=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da=normal.dot(a[0])-distance;db=normal.dot(b[0])-distance;ka=da<=0 if inside else da>=0;kb=db<=0 if inside else db>=0
  if ka:output.append(a)
  if ka!=kb:
   t=da/(da-db);output.append((a[0].lerp(b[0],t),[u.lerp(v,t)for u,v in zip(a[1],b[1])],a[2].lerp(b[2],t).normalized()))
 return output
def subtract(poly,planes):
 if any(min(n.dot(v[0])-d for v in poly)>.000001 for n,d in planes):return[poly]
 outside=[];remaining=poly
 for normal,distance in planes:
  part=planeClip(remaining,normal,distance,False)
  if len(part)>=3:outside.append(part)
  remaining=planeClip(remaining,normal,distance,True)
  if len(remaining)<3:break
 return outside
report=[]
for station in range(1,5):
 prefix=f'Defense_{station:02}';suffix='turret 1'+(f'.{station-1:03}'if station>1 else'');rear=bpy.data.objects['odin.072__'+suffix];tube=bpy.data.objects[prefix+'_TubeGeometry'];guide=bpy.data.objects[prefix+'_GuideGeometry'];hood=bpy.data.objects[prefix+'_FixedHood']
 parts=[(rear,g)for g in groups(rear)]+[(guide,g)for g in groups(guide)];tubeGroups=groups(tube);parts.extend((tube,set().union(*tubeGroups[k:k+3]))for k in[0,3]);clouds=[[]for p in parts]
 selected=[r for r in rows if r['progress']<=.85 and round(r['progress']*1000)%20==0]+[rows[400]]+rows[-4:]
 for row in selected:
  apply(row,station)
  for cloud,(obj,ids)in zip(clouds,parts):
   M=inv@obj.matrix_world;cloud.extend(M@obj.data.vertices[k].co for k in ids)
 restore();H=inv@hood.matrix_world;Hi=H.inverted();original=hood.data;oldCount=len(original.vertices);oldVerts=[H@v.co for v in original.vertices];hBounds=[(min(p[k]for p in oldVerts),max(p[k]for p in oldVerts))for k in range(3)];sweeps=[]
 for cloud in clouds:
  bounds=[(min(p[k]for p in cloud),max(p[k]for p in cloud))for k in range(3)]
  if any(bounds[k][1]<hBounds[k][0]-.04 or bounds[k][0]>hBounds[k][1]+.04 for k in range(3)):continue
  sub=bmesh.new();vs=[sub.verts.new(p)for p in cloud];result=bmesh.ops.convex_hull(sub,input=vs,use_existing_faces=False);sub.normal_update();center=sum(cloud,Vector())/len(cloud);planes={}
  for face in sub.faces:
   n=face.normal.normalized();d=n.dot(face.verts[0].co)
   if n.dot(center)>d:n=-n;d=-d
   # Enclose every sampled source point, including nearly coplanar facets
   # where imported coordinate precision makes a face plane unreliable.
   d=max(n.dot(p)for p in cloud)+.04;key=tuple(round(x,6)for x in n)+(round(d,5),);planes[key]=(n.copy(),d)
  sub.free();sweeps.append(list(planes.values()))
 original.calc_loop_triangles();layers=list(original.uv_layers);fragments=[]
 for tri in original.loop_triangles:
  face=original.polygons[tri.polygon_index];poly=[(H@original.vertices[k].co,[layer.data[loop].uv.copy()for layer in layers],original.corner_normals[loop].vector.copy())for k,loop in zip(tri.vertices,tri.loops)];current=[poly]
  for planes in sweeps:current=[piece for p in current for piece in subtract(p,planes)]
  for p in current:
   for k in range(1,len(p)-1):
    triangle=[p[0],p[k],p[k+1]]
    if(triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).length>.00000001:fragments.append((triangle,face.material_index,face.use_smooth))
 verts=[];faces=[];normals=[];uvs=[]
 for triangle,material,smooth in fragments:
  start=len(verts);verts.extend(Hi@v[0]for v in triangle);faces.append((start,start+1,start+2));normals.extend(v[2]for v in triangle);uvs.extend(v[1]for v in triangle)
 mesh=bpy.data.meshes.new(prefix+'_FittedReceiver');mesh.from_pydata(verts,[],faces)
 for material in original.materials:mesh.materials.append(material)
 for layerIndex,layer in enumerate(layers):
  new=mesh.uv_layers.new(name=layer.name)
  for k,item in enumerate(uvs):new.data[k].uv=item[layerIndex]
 for face,(_,material,smooth)in zip(mesh.polygons,fragments):face.material_index=material;face.use_smooth=smooth
 mesh.normals_split_custom_set(normals);mesh.update();hood.data=mesh;hood['receiverSweepRelief']=True;hood['sweepClearanceModel']=.04
 report.append({'station':station,'sourceVertices':oldCount,'fittedVertices':len(mesh.vertices),'sourceFaces':len(original.polygons),'fittedTriangles':len(mesh.polygons),'sweepPoses':len(selected),'separateSourceComponentSweeps':len(parts),'appliedConvexSweeps':len(sweeps),'clearanceMarginModel':.04,'originalTransformsPreserved':True,'originalUVsAndNormalsInterpolatedAtCuts':True});print('SOURCE_RECEIVER_SWEEP_FIT',report[-1],flush=True)
restore();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.39.blend'),compress=True)
(root/'docs/review/v0.11.39/receiver-fit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
