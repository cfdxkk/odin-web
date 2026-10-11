"""Independent geometry/scope check for the four refitted vertical flank mounts."""
import bpy, hashlib, json, math, numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion

R=Path(__file__).resolve().parents[1]
exec((R/'tools/revise_secondary_bridge_v090.py').read_text().split('def fit_channel_nose')[0])
out=R/'work/v0112-review';out.mkdir(exist_ok=True)
rows=json.loads((R/'docs/review/v0.11.0/side-batteries.json').read_text())
prefixes=tuple(rows)

def in_scope(o):
    if o.name=='Odin_Asset': return True
    while o:
        if o.name.startswith(prefixes): return True
        o=o.parent
    return False

state={}
for o in s.objects:
    if in_scope(o): continue
    h=hashlib.sha256();h.update(np.array(o.matrix_local,dtype=np.float64).tobytes())
    if o.type=='MESH':
        h.update(np.array([v.co[:] for v in o.data.vertices],dtype=np.float32).tobytes())
        h.update(str([tuple(f.vertices)for f in o.data.polygons]).encode())
        h.update(str([f.material_index for f in o.data.polygons]).encode())
        h.update(str([m.name for m in o.data.materials]).encode())
    if o.get('staticJoint'):
        h.update(json.dumps(dict(o.items()),sort_keys=True,default=lambda v:list(v)).encode())
    state[o.name]=h.hexdigest()

if str(A['version'])=='0.11.1':
    (out/'scope-before.json').write_text(json.dumps(state))
    print('BASELINE',len(state));raise SystemExit
assert str(A['version'])=='0.11.2'
before=json.loads((out/'scope-before.json').read_text())
changed=[name for name in before if state.get(name)!=before[name]]
assert not changed,('non-flank scope changed',changed)

hull=bpy.data.objects['holo.001'];M=inv@hull.matrix_world
hp=np.array([M@v.co for v in hull.data.vertices])
result={}
for name,row in rows.items():
    C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes']);hq=(hp-C)@Q
    record={}
    for label,sign in [('Port',-1),('Starboard',1)]:
        slider=bpy.data.objects[name+'_Slider_'+label]
        skin=bpy.data.objects[slider.name+'_TrapezoidSkin']
        assert all('_InnerRimReturn_' not in child.name for child in slider.children)
        plane=np.array(slider['fittedHullFacetPlane']);front=np.array(slider['frontReceiverEdgeModel'])
        assert all(np.min(np.linalg.norm(hp-p,axis=1))<.0001 for p in front),(name,label,'source rim')
        flat=abs(((front[0]-C)@Q)[0])
        def roof_error(o,front_edge=False):
            wm=inv@o.matrix_world
            # Topological first half is the actual smooth exterior, not the
            # hidden red reverse or a separate cosmetic filler.
            n=len(o.data.vertices)//2
            q=(np.array([wm@v.co for v in list(o.data.vertices)[:n]])-C)@Q
            x=np.sign(q[:,0])*np.maximum(abs(q[:,0]),flat)
            residual=np.max(abs(q[:,2]-(plane[0]*x+plane[1]*q[:,1]+plane[2])))
            assert residual<.002,(o.name,'visible skin leaves source plane',residual)
            assert all(o.data.materials[f.material_index].name=='Odin_Paint_Light' for f in list(o.data.polygons)[:(n//3-1)*2])
            if front_edge:
                edge=q[-3:];targets=(front-C)@Q
                distances=[min(np.linalg.norm(edge-p,axis=1))for p in targets]
                assert max(distances)<.0001,(o.name,'actual front face does not seat on hull',distances)
                return float(residual),float(max(distances))
            return float(residual),None
        residual,rim_error=roof_error(skin,True)
        roof_errors=[residual]
        grates=[]
        for leaf in row['leaves']:
            if (('_Shutter_Port_' in leaf['name'])!=(label=='Port')):continue
            joint=bpy.data.objects[leaf['name']]
            backing=bpy.data.objects[joint.name+'_FittedBacking']
            # Inspect the closed space, which includes the calibrated rear
            # carriage shift for groups 3 and 4.
            H=np.array(leaf['hinge']);rot=np.array(Quaternion(Vector(leaf['axis']),math.radians(joint['closedAngleDegrees'])).to_matrix())
            carriage=bpy.data.objects[name+'_Carriage']
            shift=((np.array(carriage['slideVector'])+np.array(carriage['liftVector']))@Q if leaf['group']>=3 else np.zeros(3))
            wm=inv@backing.matrix_world
            p=np.array([wm@v.co for v in backing.data.vertices]);closed=(p-H)@rot.T+H
            # The world mesh is authored deployed; undo that motion for the
            # underlying roof plane check.
            q=(closed-C)@Q+shift
            n=len(q)//2;outer=q[:n]
            x=np.sign(outer[:,0])*np.maximum(abs(outer[:,0]),flat)
            error=float(np.max(abs(outer[:,2]-(plane[0]*x+plane[1]*outer[:,1]+plane[2]))))
            assert error<.001,(backing.name,'leaf roof leaves source plane',error)
            roof_errors.append(error)
            grate=bpy.data.objects[joint.name+'_Skin'];gw=inv@grate.matrix_world
            gp=np.array([gw@v.co for v in grate.data.vertices]);gq=((gp-H)@rot.T+H-C)@Q+shift
            gx=np.sign(gq[:,0])*np.maximum(abs(gq[:,0]),flat)
            clearance=plane[0]*gx+plane[1]*gq[:,1]+plane[2]-gq[:,2]
            assert np.min(clearance)>.18,(grate.name,'red grate protrudes outside shell',np.min(clearance))
            assert all(grate.data.materials[f.material_index].name=='Odin_Bay_Primer' for f in grate.data.polygons)
            grates.append({'name':grate.name,'vertices':len(gq),'minimumRoofClearance':float(np.min(clearance))})
        record[label]={'sourcePlane':plane.tolist(),'actualFrontRimError':rim_error,
                       'maximumRoofPlaneError':max(roof_errors),'redInnerGrates':grates}
    result[name]=record

sha=hashlib.sha256((R.parent/'Odin 建模/odin.blend').read_bytes()).hexdigest()
assert sha=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
audit={'unchangedObjects':len(before),'changedOutsideScope':changed,'mounts':result,'originalSha256':sha}
(out/'geometry-audit.json').write_text(json.dumps(audit,indent=2))
print('AUDIT',json.dumps({'unchangedObjects':len(before),'mounts':len(result),'maxActualFrontRimError':max(v['actualFrontRimError']for r in result.values()for v in r.values()),'originalSha256':sha}))
