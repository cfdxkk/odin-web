"""Keep source lower foundations fixed; make cradle alignment a fixed installation.

Run on the accepted v0.11.39 native file. Partition only the independent
140-vertex foundation island, preserving all source faces, materials and UVs.
Animations remain in the Nuxt rig, with no alignment turn during travel.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

root=Path(__file__).resolve().parents[1]
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
review=root/'docs/review/v0.11.40';review.mkdir(parents=True,exist_ok=True)
report={'version':'0.11.40','stations':[],'sourceGeometryDeformed':False}

def groups(o):
 links=[[]for _ in o.data.vertices]
 for e in o.data.edges:
  a,b=e.vertices;links[a].append(b);links[b].append(a)
 seen=set();out=[]
 for i in range(len(links)):
  if i in seen:continue
  ids={i};todo=[i];seen.add(i)
  while todo:
   for j in links[todo.pop()]:
    if j not in seen:seen.add(j);ids.add(j);todo.append(j)
  out.append(ids)
 return out

for i in range(1,5):
 prefix=f'Defense_{i:02}';carriage=bpy.data.objects[prefix+'_Carriage'];lower=bpy.data.objects[prefix+'_LowerCradle']
 parts=groups(lower);ids=parts[-1];assert len(parts)==7 and len(ids)==140
 sourceIsland=int(lower['sourceIslands'][-1]);assert sourceIsland in[70,71]
 install=float(carriage['closedAlignmentDegrees'])
 turn=Quaternion(Vector((0,0,1)),math.radians(install))
 center=(inv@carriage.matrix_world).translation
 deployment=Vector(carriage['deployedOffsetModel'])
 installed=Matrix.Translation(center+deployment)@turn.to_matrix().to_4x4()@Matrix.Translation(-center)
 sourceWorld=lower.matrix_world.copy()
 foundation=lower.copy();foundation.data=lower.data.copy();bpy.context.scene.collection.objects.link(foundation)
 foundation.name=prefix+'_FoundationGeometry'
 bm=bmesh.new();bm.from_mesh(foundation.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS');bm.to_mesh(foundation.data);bm.free();foundation.data.update()
 mount=bpy.data.objects.new(prefix+'_FixedFoundation',None);bpy.context.scene.collection.objects.link(mount)
 mount.parent=asset;mount.matrix_local=Matrix.Identity(4);mount['fixedHullSupport']=True
 mount['sourceObject']='holo.011';mount['sourceIsland']=sourceIsland
 foundation.parent=mount;foundation.matrix_parent_inverse=Matrix.Identity(4)
 foundation.matrix_local=installed@inv@sourceWorld
 bpy.context.view_layer.update()
 for key in ['completeTurretSupport','sourceIslands']:
  if key in foundation:del foundation[key]
 foundation['fixedHullSupport']=True;foundation['sourceIsland']=sourceIsland
 bm=bmesh.new();bm.from_mesh(lower.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[bm.verts[k]for k in ids],context='VERTS');bm.to_mesh(lower.data);bm.free();lower.data.update()
 lower['sourceIslands']=list(lower['sourceIslands'])[:-1]
 carriage['translationOnly']=True;carriage['fixedInstallationDegrees']=install
 carriage['fixedFoundation']=mount.name
 for key in ['closedAlignmentDegrees','alignStart','alignEnd','rampFaceIndices']:
  if key in carriage:del carriage[key]
 # The reference ramp now belongs to the stationary hull foundation.
 F=inv@foundation.matrix_world;N=F.to_3x3().inverted().transposed()
 rampFaces=[f for f in foundation.data.polygons if f.area>10 and (N@f.normal).normalized().z<-.7 and (N@f.normal).normalized().x*carriage['side']>.3]
 assert len(rampFaces)==2
 normal=sum(((N@f.normal).normalized()*f.area for f in rampFaces),Vector()).normalized()
 assert (normal-Vector(carriage['rampNormalModel'])).length<1e-6
 assert abs(normal.dot(Vector(carriage['stowVectorModel'])))<1e-5
 carriage['fixedRampFaceIndices']=[f.index for f in rampFaces]
 report['stations'].append({'station':i,'foundationSourceIsland':sourceIsland,'foundationVertices':len(foundation.data.vertices),'foundationFaces':len(foundation.data.polygons),'movingLowerVertices':len(lower.data.vertices),'fixedInstallationDegrees':install,'deployedOffsetModel':list(deployment),'stowVectorModel':list(carriage['stowVectorModel']),'rampNormalModel':list(normal),'fixedRampFaces':[f.index for f in rampFaces],'receiverCrossAxisModel':list(carriage['receiverCrossAxisModel']),'receiverCenterModel':list(carriage['receiverCenterModel']),'horizontalTravel':math.hypot(*carriage['stowVectorModel'][:2]),'drop':-carriage['stowVectorModel'][2],'foundationInstalledMatrixModel':[list(row)for row in F]})
 bpy.context.view_layer.update()

asset['version']='0.11.40';assert not bpy.data.actions
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.40.blend'),compress=True)
(review/'assembly-fit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('FIXED_TWIN_FOUNDATIONS',[(r['station'],r['foundationSourceIsland'],r['foundationVertices'],r['fixedInstallationDegrees'])for r in report['stations']],flush=True)
