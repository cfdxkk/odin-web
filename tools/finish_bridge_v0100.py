"""Rectangular flush glazing, airflow-aligned antenna paint, fitted radar booms."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1]
helpers=(R/'tools/revise_secondary_bridge_v090.py').read_text(encoding='utf8');exec(helpers[:helpers.index('def fit_channel_nose')])
out=R/'work/v0100-review';tower=bpy.data.materials['Odin_Bridge_Armor'];trim=bpy.data.materials['Odin_Bridge_Trim'];glass=bpy.data.materials['Odin_Bridge_Glazing'];alloy=bpy.data.materials['Odin_Equipment_Alloy']
builder=(R/'tools/revise_mechanics_v0100.py').read_text(encoding='utf8');exec(builder[builder.index('def segment('):builder.index('def channel(')]);exec(builder[builder.index('def boom('):builder.index('# Two rear capsules')])

old=bpy.data.objects['BridgeWindow_LowerObservation'];normal=Vector(old['planeNormal']);distance=old['planeDistance'];bpy.data.objects.remove(old,do_unlink=True)
def point(x,z):return(x,(distance-normal.x*x-normal.z*z)/normal.y,z)
pane=prism('BridgeWindow_LowerObservation',[point(x,z)for x,z in [(-3.42,80.49),(-3.42,95.43),(3.42,95.43),(3.42,80.49)]],.12,A,glass,glass)
pane['coplanarDatum']='Original lower front tower plate';pane['planeNormal']=list(normal);pane['planeDistance']=distance;pane['rectangular']=True

# One continuous UV color band, including the narrow edges. No stripe mesh.
tex=bpy.data.images.get('Odin_Antenna_Wrap_Paint')or bpy.data.images.new('Odin_Antenna_Wrap_Paint',width=8,height=512,alpha=False)
pixels=np.empty((512,8,4),dtype=np.float32);pixels[:]=(.52,.55,.58,1)
for row in range(512):
 z=.30+(row+.5)/512*6.85
 if 1.10<z<1.57:pixels[row]=(.72,.13,.055,1)
tex.pixels.foreach_set(pixels.ravel());tex.update();tex.pack()
paint=bpy.data.materials.get('Odin_Antenna_Painted_Wrap')or bpy.data.materials.new('Odin_Antenna_Painted_Wrap');paint.use_nodes=True;paint.diffuse_color=(.52,.55,.58,1)
nodes=paint.node_tree.nodes;nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');bs.inputs['Metallic'].default_value=.32;bs.inputs['Roughness'].default_value=.54;im=nodes.new('ShaderNodeTexImage');im.image=tex;im.extension='EXTEND';im.interpolation='Linear';output=nodes.new('ShaderNodeOutputMaterial');paint.node_tree.links.new(im.outputs['Color'],bs.inputs['Base Color']);paint.node_tree.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
uvNode=nodes.new('ShaderNodeUVMap');uvNode.uv_map='ContinuousPaint';paint.node_tree.links.new(uvNode.outputs['UV'],im.inputs['Vector'])
for o in [o for o in s.objects if o.name.startswith('BridgeAntenna_')]:bpy.data.objects.remove(o,do_unlink=True)
for side,sign in [('Port',-1),('Starboard',1)]:
 for upper in [True,False]:
  name=f'BridgeAntenna_{side}_{"Upper"if upper else"Lower"}';center=Vector((sign*(14.0 if upper else 23.0),-36.8 if upper else-26.6,132.2 if upper else 125.1));axis=Vector((0,0,1))if upper else Vector((0,.22,-1)).normalized();across=Vector((0,1,0))if upper else Vector((0,1,.22)).normalized();depth=axis.cross(across).normalized()
  shape=[(-1.48,.30),(1.48,.30),(1.65,6.6),(1.37,7.15),(-1.37,7.15),(-1.65,6.6)]
  panel=prism(name,[center+across*x+axis*z+depth*.32 for x,z in shape],.64,A,paint,paint);bevel(panel,.09)
  uv=panel.data.uv_layers.new(name='ContinuousPaint');M=inv@panel.matrix_world
  for loop in panel.data.loops:
   v=M@panel.data.vertices[loop.vertex_index].co-center;uv.data[loop.index].uv=((v.dot(across)+1.7)/3.4,(v.dot(axis)-.30)/6.85)
  panel['airflowAxisModel']=[0,1,0];panel['paintBand']='Embedded continuous UV texture, all four faces'
  segment(name+'_Pedestal',center-axis*.28,center+axis*.65,1.35,tower,.9)
  if not upper:segment(name+'_Mount',Vector((sign*21.9,-30.2,127.7)),center,1.1,trim)

# Rear capsules swing toward the aft quarters in plan view, matching the
# drawn diagonal rather than keeping their support booms transverse.
for o in [o for o in s.objects if o.name.startswith(('RadarBoom_','RadarClamp_','RadarCollar_'))]:bpy.data.objects.remove(o,do_unlink=True)
capsule=bpy.data.objects['Cylinder'];M=inv@capsule.matrix_world;Mi=M.inverted();groups=parts(capsule)
hull=bpy.data.objects['holo.001'];hull.data.calc_loop_triangles();H=inv@hull.matrix_world;tree=BVHTree.FromPolygons([H@v.co for v in hull.data.vertices],[tuple(t.vertices)for t in hull.data.loop_triangles],all_triangles=True)
report={}
for side,sign in [('Port',-1),('Starboard',1)]:
 group=next(g for g in groups if np.sign(g['center'][0])==sign);old=(group['lo']+group['hi'])/2;target=Vector((sign*25.3,-85.3,float(old[2])))
 delta=target-Vector(old)
 for i in group['ids']:capsule.data.vertices[i].co=Mi@(M@capsule.data.vertices[i].co+delta)
 a=Vector((sign*19.5,-77.5,105.8));b=Vector((sign*24.4,-85.3,105.8));boom('RadarBoom_Rear_'+side,a,b)
 for z in [104.5,106.2]:segment('RadarClamp_Rear_'+side+str(z),(b.x,b.y,z),(target.x,target.y,z),.45)
 small=bpy.data.objects['RadarCapsule_Bridge_'+side];G=inv@small.matrix_world;Gi=G.inverted();vs=np.array([G@v.co for v in small.data.vertices]);oldSmall=Vector((vs.min(0)+vs.max(0))/2);smallTarget=Vector((sign*6.5,-52.0,122.5));delta=smallTarget-oldSmall
 for v in small.data.vertices:v.co=Gi@(G@v.co+delta)
 # Seat the inner end on the actual protruding upper bridge support face.
 hit=tree.ray_cast(Vector((sign*20,-52.0,123.1)),Vector((-sign,0,0)),20)[0]
 assert hit is not None,(side,'bridge radar mounting surface')
 mount=Vector((hit.x+sign*.035,-52.0,123.1));end=Vector((sign*6.1,-52.0,123.1));boom('RadarBoom_Bridge_'+side,mount,end,.16)
 segment('RadarClamp_Bridge_'+side,mount-Vector((0,0,.55)),mount+Vector((0,0,.55)),.5,trim,.7)
 for obj,c,r in [(capsule,target,2.05),(small,smallTarget,1.07)]:
  bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=.22);band=bpy.context.object;band.name='RadarCollar_'+obj.name+'_'+side;band.parent=A;band.location=c;band.data.materials.append(light)
 report[side]={'rearBoomAnchor':list(a),'rearCapsule':list(target),'bridgeBoomAnchor':list(mount),'bridgeCapsule':list(smallTarget)}
capsule.data.update();(out/'bridge-refinements.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.10.0.blend'),compress=True)
print('BRIDGE REFINED',json.dumps(report),flush=True)
