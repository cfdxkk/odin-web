"""Audit all four flank crowns and their actual contact-edge hinges.

Run once against v0.11.2 for the out-of-scope baseline, then against v0.11.3.
The hinge test uses the backing mesh vertices rather than only joint metadata.
"""
import bpy, hashlib, json, math, numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion

R=Path(__file__).resolve().parents[1]
exec((R/'tools/revise_secondary_bridge_v090.py').read_text().split('def fit_channel_nose')[0])
out=R/'work/v0113-review';out.mkdir(exist_ok=True)
rows=json.loads((R/'docs/review/v0.11.0/side-batteries.json').read_text())
prefixes=tuple(rows)

def in_scope(o):
    if o.name=='Odin_Asset':return True
    while o:
        if o.name.startswith(prefixes):return True
        o=o.parent
    return False

state={}
for o in s.objects:
    if in_scope(o):continue
    h=hashlib.sha256();h.update(np.array(o.matrix_local,dtype=np.float64).tobytes())
    if o.type=='MESH':
        h.update(np.array([v.co[:] for v in o.data.vertices],dtype=np.float32).tobytes())
        h.update(str([tuple(f.vertices) for f in o.data.polygons]).encode())
        h.update(str([f.material_index for f in o.data.polygons]).encode())
        h.update(str([m.name for m in o.data.materials]).encode())
    if o.get('staticJoint'):
        h.update(json.dumps(dict(o.items()),sort_keys=True,default=lambda v:list(v)).encode())
    state[o.name]=h.hexdigest()

if str(A['version'])=='0.11.2':
    (out/'scope-before.json').write_text(json.dumps(state))
    print('BASELINE',len(state));raise SystemExit

assert str(A['version'])=='0.11.3'
before=json.loads((out/'scope-before.json').read_text())
changed=[name for name in before if state.get(name)!=before[name]]
assert not changed,('non-flank scope changed',changed)
assert len(before)==len(state),(len(before),len(state))

def model_vertices(obj):
    M=inv@obj.matrix_world
    return np.array([M@v.co for v in obj.data.vertices])

def line_distance(p,center,axis):
    return np.linalg.norm(np.cross(p-center,axis))

report={}
hinge_errors=[];rim_errors=[];grate_clearances=[];ridge_errors=[]
for name,row in rows.items():
    C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes'])
    ridge=float(np.mean([r['height'] for r in row['ridge'] if r['group']==2]))
    carriage=bpy.data.objects[name+'_Carriage']
    shift_model=np.array(carriage['slideVector'])+np.array(carriage['liftVector'])
    mount={}
    for label,sign in [('Port',-1),('Starboard',1)]:
        slider=bpy.data.objects[name+'_Slider_'+label]
        skin=bpy.data.objects[slider.name+'_TrapezoidSkin']
        skin_q=(model_vertices(skin)-C)@Q
        front=np.array(slider['frontReceiverEdgeModel'])
        front_q=(front-C)@Q
        # The first plate remains a smooth exterior; its long lower rail was
        # already fitted in v0.11.2 and is preserved by this revision.
        n=len(skin_q)//2
        assert all(skin.data.materials[f.material_index].name=='Odin_Paint_Light'
                   for f in list(skin.data.polygons)[:(n//3-1)*2])
        for p in front_q:
            error=float(np.min(np.linalg.norm(skin_q[:n]-p,axis=1)))
            assert error<.0002,(skin.name,'front rim',error)
            rim_errors.append(error)
        leaves=[]
        for leaf in row['leaves']:
            if (('_Shutter_Port_' in leaf['name'])!=(label=='Port')):continue
            joint=bpy.data.objects[leaf['name']]
            backing=bpy.data.objects[joint.name+'_FittedBacking']
            grate=bpy.data.objects[joint.name+'_Skin']
            H=np.array(joint['sourceHingeLine'])
            axis=np.array(joint['hingeAxisModel']);axis/=np.linalg.norm(axis)
            angle=math.radians(float(joint['closedAngleDegrees']))
            rotation=np.array(Quaternion(Vector(axis),angle).to_matrix())
            shift=shift_model if leaf['group']>=3 else np.zeros(3)
            bp=model_vertices(backing)
            closed=(bp-H)@rotation.T+H+shift
            q=(closed-C)@Q
            half=len(bp)//2
            edge=[closed[i] for i in range(half) if abs(q[i,0])>2]
            assert len(edge)==2,(joint.name,'outer contact vertices',len(edge))
            declared=np.array(joint['hingeContactEdgeClosedModel'])
            max_edge_error=max(min(np.linalg.norm(e-d) for d in declared) for e in edge)
            max_axis_error=max(line_distance(e,H+shift,axis) for e in edge)
            assert max_edge_error<.0001 and max_axis_error<.0001,(joint.name,'hinge floats off contact edge',max_edge_error,max_axis_error)
            hinge_errors.append(max_axis_error)
            crown=q[:half][np.abs(q[:half,0])<1]
            assert len(crown)==4,(joint.name,'flat crown',crown)
            ridge_error=float(np.max(abs(crown[:,2]-ridge)))
            assert ridge_error<.003,(joint.name,'crown height',ridge_error)
            ridge_errors.append(ridge_error)
            assert joint['physicalHinge']==True
            assert joint['hingeLocation']=='armor outer contact edge'
            assert abs(abs(joint['closedAngleDegrees'])-150)<1e-6
            assert all(grate.data.materials[f.material_index].name=='Odin_Bay_Primer'
                       for f in grate.data.polygons)
            gp=model_vertices(grate)
            gq=(((gp-H)@rotation.T+H+shift)-C)@Q
            plane=np.array(joint['fittedHullFacetPlane']);flat=float(joint['ridgeHalfWidth'])
            profile=np.array(sorted((v[1],abs(v[0])) for v in q[:half] if abs(v[0])>2))
            outer=np.interp(gq[:,1],profile[:,0],profile[:,1])
            portion=np.clip((outer-np.abs(gq[:,0]))/(outer-flat),0,1)
            old_crown=plane[0]*sign*flat+plane[1]*gq[:,1]+plane[2]
            roof=plane[0]*np.sign(gq[:,0])*np.maximum(np.abs(gq[:,0]),flat)+plane[1]*gq[:,1]+plane[2]+(ridge-old_crown)*portion
            clearance=float(np.min(roof-gq[:,2]))
            assert clearance>.18,(grate.name,'inner grate pierces exterior',clearance)
            grate_clearances.append(clearance)
            leaves.append({'name':joint.name,'group':leaf['group'],
                           'maxMeshEdgeToHingeAxis':float(max_axis_error),
                           'maxMeshEdgeToMetadata':float(max_edge_error),
                           'flatCrownHeightError':ridge_error,
                           'minimumRedGrateRoofClearance':clearance})
        mount[label]={'frontRimError':max(rim_errors[-3:]),'leaves':leaves}
    report[name]=mount

sha=hashlib.sha256((R.parent/'Odin 建模/odin.blend').read_bytes()).hexdigest()
assert sha=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
assert len(hinge_errors)==24
assert not bpy.data.actions[:],('asset contains animation actions',list(bpy.data.actions))
audit={'unchangedObjectsOutsideScope':len(before),'changedOutsideScope':changed,
       'hinges':len(hinge_errors),'maxActualContactEdgeToHingeAxis':max(hinge_errors),
       'maxFlatCrownHeightError':max(ridge_errors),
       'maxFirstPlateFrontRimError':max(rim_errors),
       'minimumInnerGrateRoofClearance':min(grate_clearances),
       'originalBlendSha256':sha,'mounts':report}
(out/'geometry-audit.json').write_text(json.dumps(audit,indent=2))
print('AUDIT',json.dumps({key:audit[key] for key in [
    'unchangedObjectsOutsideScope','hinges','maxActualContactEdgeToHingeAxis',
    'maxFlatCrownHeightError','maxFirstPlateFrontRimError',
    'minimumInnerGrateRoofClearance','originalBlendSha256']}))
