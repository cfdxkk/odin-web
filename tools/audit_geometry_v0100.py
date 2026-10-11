"""Check fitted seats, unchanged main exteriors and the requested glass plane."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted()
out=R/'work/v0100-review';report={}
panels=[o for o in bpy.context.scene.objects if o.get('barrelJoint')]
caps=[o for o in bpy.context.scene.objects if o.get('system')=='single-front-cap']
assert len(panels)==66 and len(caps)==11
for cap in caps:
 leaves=[o for o in panels if o['barrelJoint']==cap['barrel']]
 assert len(leaves)==6 and cap.get('sourceOpenPose') and all(o.get('sourceGeometry') for o in leaves)
 assert all(c.get('sourceGeometry') for c in cap.children if c.type=='MESH')
report['singleCovers']={'mounts':len(caps),'sideLeaves':len(panels),'frontCaps':len(caps),'geometry':'Original source panels, native relief and thickness retained','sourcePose':'Deployed'}
pane=bpy.data.objects['BridgeWindow_LowerObservation'];M=inv@pane.matrix_world;normal=Vector(pane['planeNormal']);distance=pane['planeDistance'];points=[M@v.co for v in pane.data.vertices[:len(pane.data.vertices)//2]]
error=max(abs(normal.dot(p)-distance)for p in points)
assert error<1e-5 and len(points)==4 and pane.get('rectangular') and min(p.z for p in points)>80.4 and max(p.z for p in points)<95.5
report['lowerGlass']={'planeError':error,'planeNormal':list(normal),'planeDistance':distance,'bounds':[np.min(points,0).tolist(),np.max(points,0).tolist()]}
assert not any(o.name.startswith(('BridgeArmor_','BridgeFixedGuide_'))for o in bpy.context.scene.objects)
radome=bpy.data.objects['Icosphere'];assert all(len(f.vertices)==3 and not f.use_smooth for f in radome.data.polygons)
report['bridge']={'armorJoints':0,'radomeTriangles':len(radome.data.polygons),'capsules':4,'mountedPanelAntennas':4}
antennas=[o for o in bpy.context.scene.objects if o.get('paintBand')]
assert len(antennas)==4 and not any('Stripe' in o.name for o in bpy.context.scene.objects if o.name.startswith('BridgeAntenna_'))
assert all(list(o.get('airflowAxisModel'))==[0,1,0] and len(o.data.uv_layers)>0 for o in antennas)
report['bridge']['antennaStripe']='Continuous embedded UV texture; no stripe geometry'
report['bridge']['radarMounts']=json.loads((out/'bridge-refinements.json').read_text())
for mount in report['bridge']['radarMounts'].values():
 assert abs(mount['bridgeBoomAnchor'][1]+52)<1e-4 and abs(mount['bridgeBoomAnchor'][0])<.5
 assert np.linalg.norm(np.array(mount['bridgeBoomAnchor'])-mount['bridgeCapsule'])<6.2
names=[o.name for o in bpy.context.scene.objects if o.type=='MESH'and o.name.startswith('Hatch_')and o.name.endswith(('FittedSkin','Wedge','GapFiller'))]
current={n:bpy.data.objects[n]for n in names}
with bpy.data.libraries.load(str(R/'assets/blender/odin_articulated_v0.9.0.blend'),link=False)as(src,dst):dst.objects=names.copy()
report['mainArmor']={}
for name,old in zip(names,dst.objects):
 new=current[name];n=len(old.data.vertices)//2;outer=max((new.data.vertices[i].co-old.data.vertices[i].co).length for i in range(n))
 before=np.array([(old.data.vertices[i+n].co-old.data.vertices[i].co).length for i in range(n)]);after=np.array([(new.data.vertices[i+n].co-new.data.vertices[i].co).length for i in range(n)])
 assert outer<1e-5 and abs(float(np.median(after/before))-2.1)<1e-4
 report['mainArmor'][name]={'outerVertexError':outer,'thicknessBefore':float(np.median(before)),'thicknessAfter':float(np.median(after))}
assert len(names)==10
(out/'geometry-audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({'glassPlaneError':error,'mainExteriorsUnchanged':len(names),'singleCovers':77,'bridgeArmor':0}))
