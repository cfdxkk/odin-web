"""Fit complete forward-twin travel to the source cradle slope and fixed receiver.

Run from the v0.11.38 native file. Original faces and UVs are partitioned,
with their source surfaces retained. Runtime performs one diagonal carriage stroke, then a
horizontal barrel-only withdrawal; original rear brackets stay in place.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

root=Path(__file__).resolve().parents[1];asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
review=root/'docs/review/v0.11.39';review.mkdir(parents=True,exist_ok=True)
report={'version':'0.11.39','stations':[],'movingGeometryDeformed':False}

def groups(o):
 links=[[]for _ in o.data.vertices]
 for e in o.data.edges:a,b=e.vertices;links[a].append(b);links[b].append(a)
 seen=set();out=[]
 for i in range(len(links)):
  if i in seen:continue
  ids={i};todo=[i];seen.add(i)
  while todo:
   for j in links[todo.pop()]:
    if j not in seen:seen.add(j);ids.add(j);todo.append(j)
  out.append(ids)
 return out

def extract(o,name,ids,parent):
 bpy.context.view_layer.update();world=o.matrix_world.copy();copy=o.copy();copy.data=o.data.copy();bpy.context.scene.collection.objects.link(copy);copy.name=name
 bm=bmesh.new();bm.from_mesh(copy.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS');bm.to_mesh(copy.data);bm.free();copy.data.update()
 copy.parent=parent;copy.matrix_parent_inverse=Matrix.Identity(4);copy.matrix_world=world
 return copy

def mount(name,parent,static=False):
 o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.parent=parent;o.matrix_local=Matrix.Identity(4)
 if static:o['staticJoint']=True;o['system']='defense-tube-slide'
 return o

for side,stations in [('Port',[1,2]),('Starboard',[3,4])]:
 rail=bpy.data.objects[f'holo.011_{side}'];M=inv@rail.matrix_world;parts=groups(rail)
 for station in stations:
  carriage=bpy.data.objects[f'Defense_{station:02}_Carriage'];guideMount=mount(f'Defense_{station:02}_Guides',carriage,True)
  guideMount['system']='defense-guide';guideMount['preserveReceiverHeading']=True
  ids=set().union(*(g for g in parts if (sum((M@rail.data.vertices[j].co).y for j in g)/len(g)>-50)==(station in[1,3])))
  guides=extract(rail,f'Defense_{station:02}_GuideGeometry',ids,guideMount);guides['originalForwardGuides']=True
 bpy.data.objects.remove(rail,do_unlink=True)
 bpy.data.objects[f'DefenseRail_Forward_{side}']['guidesFollowCompleteCarriage']=True

for station in range(1,5):
 prefix=f'Defense_{station:02}';carriage=bpy.data.objects[prefix+'_Carriage'];sign=carriage['side'];hood=bpy.data.objects[prefix+'_FixedHood'];lower=bpy.data.objects[prefix+'_LowerCradle'];elevation=bpy.data.objects[prefix+'_Elevation']
 suffix='turret 1'+(f'.{station-1:03}'if station>1 else'');gun=bpy.data.objects['odin.072__'+suffix]
 H=inv@hood.matrix_world;normalMatrix=H.to_3x3().inverted().transposed()
 sideFaces=[f for f in hood.data.polygons if f.area>2 and abs((normalMatrix@f.normal).normalized().z)<.02 and abs((normalMatrix@f.normal).normalized().y)>.9]
 transverse=sum(((normalMatrix@f.normal).normalized()*f.area*(1 if (normalMatrix@f.normal).y>0 else-1)for f in sideFaces),Vector());transverse.z=0;transverse.normalize()
 outward=Vector((sign*transverse.y,-sign*transverse.x,0))
 # The largest underside roof quad defines the actual hood centerline.
 roof=max((f for f in hood.data.polygons if len(f.vertices)==4 and (normalMatrix@f.normal).normalized().z<-.7),key=lambda f:f.area)
 roofCenter=H@roof.center
 deployed=Vector((sign*9.781,2.079,0));centerCorrection=transverse*(roofCenter-(inv@carriage.matrix_world).translation-deployed).dot(transverse)
 bore=Vector(elevation['sourceBoreDirectionModel']);bore.z=0;bore.normalize()
 alignment=math.atan2(outward.y,outward.x)-math.atan2(bore.y,bore.x)
 alignment=math.atan2(math.sin(alignment),math.cos(alignment));turn=Quaternion(Vector((0,0,1)),alignment)
 # The original lower cradle's two inclined underside faces are the ramp.
 foot=groups(lower)[-1];L=inv@lower.matrix_world;N=L.to_3x3().inverted().transposed()
 slopeFaces=[f for f in lower.data.polygons if all(j in foot for j in f.vertices)and f.area>10 and (N@f.normal).normalized().z<-.7 and (N@f.normal).normalized().x*sign>.3]
 print('SOURCE_RAMP_FACES',station,len(foot),[(f.index,f.area,list((N@f.normal).normalized()))for f in slopeFaces],flush=True)
 assert len(slopeFaces)==2
 sourceNormal=sum(((N@f.normal).normalized()*f.area for f in slopeFaces),Vector()).normalized();rampNormal=turn@sourceNormal
 inward=-outward;horizontalTravel=3.3;slide=inward*horizontalTravel;slide.z=-(rampNormal.x*slide.x+rampNormal.y*slide.y)/rampNormal.z
 assert slide.z<0 and abs(slide.dot(rampNormal))<1e-6
 for key in ['stowDrop','raiseStart','raiseEnd','translationEnd']:del carriage[key]
 carriage['inclinedStow']=True;carriage['deployedOffsetModel']=list(deployed+centerCorrection);carriage['stowVectorModel']=list(slide)
 carriage['rampNormalModel']=list(rampNormal);carriage['sourceRampNormalModel']=list(sourceNormal);carriage['rampFaceIndices']=[f.index for f in slopeFaces]
 carriage['receiverCrossAxisModel']=list(transverse);carriage['receiverCenterModel']=list(roofCenter);carriage['centerCorrectionModel']=list(centerCorrection)
 carriage['closedAlignmentDegrees']=math.degrees(alignment);carriage['travelStart']=.24;carriage['travelEnd']=.64;carriage['alignStart']=.65;carriage['alignEnd']=.85;carriage['aimStart']=.69
 parts=groups(gun);assert len(parts)==72 and len(parts[6])==1847 and len(parts[7])==1851
 tubeIds=set().union(*(p for i,p in enumerate(parts)if i not in[6,7]));tube=mount(prefix+'_Tubes',elevation,True)
 tube['horizontalBoreAxisModel']=list(bore);tube['stowTravel']=5.0;tube['extendStart']=.04;tube['extendEnd']=.22;tube['originalBarrels']=True;tube['retainedRearBracketIslands']=[6,7]
 moving=extract(gun,prefix+'_TubeGeometry',tubeIds,tube);moving['originalTubeFaces']=True
 bm=bmesh.new();bm.from_mesh(gun.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[j]for j in tubeIds],context='VERTS');bm.to_mesh(gun.data);bm.free();gun.data.update();gun['retainedRearBrackets']=True
 report['stations'].append({'station':station,'stowVectorModel':list(slide),'sourceRampFaces':[{'index':f.index,'vertices':[list(L@lower.data.vertices[j].co)for j in f.vertices],'normal':list((N@f.normal).normalized())}for f in slopeFaces],'sourceRampNormalModel':list(sourceNormal),'rampNormalModel':list(rampNormal),'horizontalTravel':horizontalTravel,'drop':-slide.z,'slopeDegrees':math.degrees(math.atan2(-slide.z,horizontalTravel)),'closedAlignmentDegrees':math.degrees(alignment),'receiverCrossAxisModel':list(transverse),'receiverCenterModel':list(roofCenter),'centerCorrectionModel':list(centerCorrection),'deployedOffsetModel':list(deployed+centerCorrection),'tubeVertices':len(moving.data.vertices),'retainedRearBracketVertices':len(gun.data.vertices),'tubeStowTravel':5.0})

asset['version']='0.11.39';bpy.context.view_layer.update();assert not bpy.data.actions
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.39.blend'),compress=True)
(review/'assembly-fit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('INCLINED_FORWARD_TWINS',[(r['station'],r['stowVectorModel'],r['closedAlignmentDegrees'],r['centerCorrectionModel'])for r in report['stations']],flush=True)
