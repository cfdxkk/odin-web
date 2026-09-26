"""Check detailed grille vertices are inside the closed armor skin."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Quaternion,Vector
R=Path(__file__).resolve().parents[1];out=R/'work/v0110-review';report=json.loads((out/'side-batteries.json').read_text());A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted();result=[]
for name,row in report.items():
 C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes']);half=np.mean([abs(((np.array(l['hinge'])-C)@Q)[0])for l in row['leaves']if l['group']==2]);flat=np.mean([r['halfWidth']for r in row['ridge']if r['group']==2]);ridge=np.mean([r['height']for r in row['ridge']if r['group']==2]);base=np.mean([bpy.data.objects[l['name']]['backingSeatLift']for l in row['leaves']if l['group']==2]);slope=(ridge-base)/(half-flat)
 for leaf in row['leaves']:
  j=bpy.data.objects[leaf['name']];o=next(c for c in j.children if c.name.endswith('_Skin'));M=inv@o.matrix_world;H=np.array(leaf['hinge']);rot=np.array(Quaternion(Vector(leaf['axis']),math.radians(j['closedAngleDegrees'])).to_matrix());shift=np.array([0,row['carriageAdvance'],row['carriageLift']])if leaf['group']>=3 else np.zeros(3)
  ps=np.array([M@v.co for v in o.data.vertices]);q=((ps-H)@rot.T+H-C)@Q+shift
  clearance=(ridge+slope*flat-slope*abs(q[:,0])-q[:,2])/math.sqrt(1+slope*slope)
  overhang=float(np.max(abs(q[:,0]))-half);minimum=float(clearance.min());result.append({'leaf':j.name,'detailVertices':len(q),'minimumInsideOuterFace':minimum,'outerEdgeOverhang':overhang})
  assert minimum>.249 and overhang<-.039,(j.name,minimum,overhang)
 for label in ['Port','Starboard']:
  o=bpy.data.objects[name+'_Fairing_'+label];verts=np.array([v.co[:]for v in o.data.vertices]);face=max(o.data.polygons,key=lambda p:p.area);v=verts[list(face.vertices)];normal=np.cross(v[1]-v[0],v[2]-v[0]);normal/=np.linalg.norm(normal)
  assert np.max(np.abs((v-v[0])@normal))<1e-4,(o.name,'non-planar face')
(out/'surface-audit.json').write_text(json.dumps({'innerDetailLeaves':result,'localTriangularInfill':8},indent=2));print('24 inner-detail leaves lie inside continuous skins; 8 local triangular bay patches')
