"""Separate the fixed source hood from the complete forward twin lifting cradle.

All faces, UVs and materials are preserved. The native rest position is the
requested raised endpoint; runtime movement starts from a lower stowed seat.
"""
import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Matrix

root=Path(__file__).resolve().parents[1]
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
review=root/'docs/review/v0.11.38';review.mkdir(parents=True,exist_ok=True)
report={'version':'0.11.38','stations':[],'sourceFacesReassigned':[]}

def parts(o):
 links=[[]for _ in o.data.vertices]
 for e in o.data.edges:a,b=e.vertices;links[a].append(b);links[b].append(a)
 seen=set();groups=[]
 for i in range(len(links)):
  if i in seen:continue
  ids={i};todo=[i];seen.add(i)
  while todo:
   for j in links[todo.pop()]:
    if j not in seen:seen.add(j);ids.add(j);todo.append(j)
  groups.append(ids)
 return groups

def subset(o,name,ids,parent):
 bpy.context.view_layer.update()
 copy=o.copy();copy.data=o.data.copy();bpy.context.scene.collection.objects.link(copy);copy.name=name
 bm=bmesh.new();bm.from_mesh(copy.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS')
 bm.to_mesh(copy.data);bm.free();copy.data.update()
 world=o.matrix_world.copy();copy.parent=parent;copy.matrix_parent_inverse=Matrix.Identity(4);copy.matrix_world=world
 return copy

for side,indices in [('Port',[1,2]),('Starboard',[3,4])]:
 rail=bpy.data.objects[f'DefenseRail_Forward_{side}'];o=bpy.data.objects[f'holo.011_{side}'];groups=parts(o)
 assert len(groups)==72
 assert [len(groups[i])for i in[0,1,2,3,4,5,6,9,12,13,70,71]]==[330,264,2682,330,264,2682,5356,5345 if side=='Port'else 5342,718,718,140,140]
 used=set()
 for station,hood,lower in zip(indices,[12,13],[[0,1,2,9,14,15,71],[3,4,5,6,16,17,70]]):
  prefix=f'Defense_{station:02}';carriage=bpy.data.objects[prefix+'_Carriage']
  mount=bpy.data.objects.new(prefix+'_FixedArmor',None);bpy.context.scene.collection.objects.link(mount);mount.parent=asset;mount.matrix_local=Matrix.Identity(4)
  mount['fixedHullArmor']=True;mount['sourceObject']='holo.011';mount['sourceIsland']=hood
  fixed=subset(o,prefix+'_FixedHood',groups[hood],mount)
  # Pin the hood at the screenshot/source frame-30 OUTBOARD rail endpoint.
  # Its old frame-15 pose would bury the roof in the deck and expose the bay.
  fixed.location.x+=(1 if side=='Starboard'else-1)*9.781475067138672;fixed.location.y+=2.0791168212890625
  fixed['sourceFixedReferenceFrame']=30
  fixed['sourceObject']='holo.011';fixed['sourceIsland']=hood;fixed['fixedHullArmor']=True
  ids=set().union(*(groups[i]for i in lower));support=subset(o,prefix+'_LowerCradle',ids,carriage)
  support['sourceObject']='holo.011';support['sourceIslands']=lower;support['completeTurretSupport']=True
  carriage['completeForwardTwin']=True;carriage['stowDrop']=4.6;carriage['raiseStart']=.52;carriage['raiseEnd']=.68
  carriage['translationEnd']=.52;carriage['aimStart']=.69;carriage['raisedEndpointIsSourceRest']=True
  carriage['fixedHood']=fixed.name;carriage['lowerCradle']=support.name
  used.update(ids);used.update(groups[hood])
  report['stations'].append({'station':station,'fixedHood':fixed.name,'hoodSourceIsland':hood,'hoodVertices':len(fixed.data.vertices),'fixedHoodSourceFrame':30,'lowerCradle':support.name,'supportSourceIslands':lower,'supportVertices':len(support.data.vertices),'raisedOrigin':list((inv@carriage.matrix_world).translation),'stowDrop':4.6,'raiseInterval':[.52,.68],'aimStart':.69})
 bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i]for i in used],context='VERTS');bm.to_mesh(o.data);bm.free();o.data.update()
 rail['fixedHoodsRemoved']=True;rail['completeTurretSupportsRemoved']=True
 rail['stowDrop']=4.6;rail['raiseStart']=.52;rail['raiseEnd']=.68;rail['completeForwardTwinGuide']=True
 report['sourceFacesReassigned'].append({'side':side,'originalVertices':sum(len(g)for g in groups),'retainedRailVertices':len(o.data.vertices),'reassignedVertices':len(used),'geometryDeformed':False})

asset['version']='0.11.38'
bpy.context.view_layer.update()
assert not bpy.data.actions
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.38.blend'),compress=True)
(review/'assembly-partition.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('FORWARD_TWIN_ASSEMBLIES',[(r['station'],r['hoodVertices'],r['supportVertices'],r['stowDrop'])for r in report['stations']],flush=True)
