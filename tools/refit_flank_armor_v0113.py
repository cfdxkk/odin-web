"""Lift the four flank armor crowns back to their original hull silhouette.

v0.11.2 seated each lower armor edge on the correct original inner rail, but
projected the *entire* roof onto the lower nose facet. That pulled the flat
ridge about 0.8 model units too far into the bay. Keep the fitted lower edges
and front rim, and join them to the accepted v0.11.1 crown line. Refit the red
inner grates and static seam metadata to the same surface.
"""
import bpy, json, math, numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

R = Path(__file__).resolve().parents[1]
exec((R/'tools/revise_secondary_bridge_v090.py').read_text().split('def fit_channel_nose')[0])
out = R/'work/v0113-review'; out.mkdir(exist_ok=True)
rows = json.loads((R/'docs/review/v0.11.0/side-batteries.json').read_text())
report = {}


def source_profile(mesh, frame, H, rotation, shift, C, Q):
    """Read the fitted long outer edge from the actual v0.11.2 armor mesh."""
    M = inv @ mesh.matrix_world
    p = np.array([M @ v.co for v in list(mesh.data.vertices)[:len(mesh.data.vertices)//2]])
    if H is not None: p = (p-H)@rotation.T+H
    q = (p-C)@Q+shift
    profile = sorted((float(v[1]),float(abs(v[0]))) for v in q if abs(v[0])>2.0)
    assert len(profile)==frame,(mesh.name,profile)
    return np.array(profile)


def retune_point(model, H, rotation, shift, C, Q, sign, plane, flat,
                 profile, ridge, taper):
    p = np.array(model,dtype=float)
    if H is not None: p = (p-H)@rotation.T+H
    q = (p-C)@Q+shift
    old_plane_crown = plane[0]*sign*flat+plane[1]*q[1]+plane[2]
    outer = np.interp(q[1],profile[:,0],profile[:,1])
    portion = np.clip((outer-abs(q[0]))/(outer-flat),0,1)
    advance = np.clip(taper(q[1]),0,1)
    q[2] += (ridge-old_plane_crown)*portion*advance
    closed = C+Q@(q-shift)
    return H+rotation.T@(closed-H) if H is not None else closed


def retune_mesh(mesh, warp):
    M = inv @ mesh.matrix_world; Mi = M.inverted()
    for vertex in mesh.data.vertices:
        vertex.co = Mi @ Vector(warp(M @ vertex.co))
    mesh.data.update()


def shorten_inner_grate(grate, H, rotation, shift, C, Q):
    """Keep a red stiffener inside its leaf's forward butt seam."""
    M=inv@grate.matrix_world;Mi=M.inverted()
    ps=np.array([M@v.co for v in grate.data.vertices])
    qs=((ps-H)@rotation.T+H-C)@Q+shift
    front=float(qs[:,1].max())
    qs[:,1]-=.16*np.clip((qs[:,1]-(front-1.5))/1.5,0,1)
    for vertex,q in zip(grate.data.vertices,qs):
        vertex.co=Mi@Vector(H+rotation.T@(C+Q@(q-shift)-H))
    grate.data.update()


def retune_joint_metadata(joint, warp, C, Q, closed_warp):
    M = inv @ joint.matrix_world; Mi = M.inverted()
    if 'crownSeamsLocal' in joint:
        joint['crownSeamsLocal'] = [
            [list(Mi@Vector(warp(M@Vector(p)))) for p in edge]
            for edge in joint['crownSeamsLocal']]
    if 'seamEdgeLocal' in joint:
        joint['seamEdgeLocal'] = [list(Mi@Vector(warp(M@Vector(p))))
                                  for p in joint['seamEdgeLocal']]
    if 'closedSeamEdgeModel' in joint:
        joint['closedSeamEdgeModel'] = [list(closed_warp(np.array(p)))
                                        for p in joint['closedSeamEdgeModel']]


def reanchor_leaf(joint, backing, H, old_axis, shift_model, C, Q):
    """Put the pivot on the closed armor's outer contact edge.

    Re-bake the authored open mesh from its unchanged closed geometry. The
    continuous edge then remains on the joint axis throughout the fold.
    """
    old_axis=np.array(old_axis,dtype=float);old_axis/=np.linalg.norm(old_axis)
    old_angle=math.radians(joint['closedAngleDegrees'])
    sign=-1 if '_Shutter_Port_' in joint.name else 1
    # A 150-degree mechanical travel opens all three leaves fully while
    # keeping their contact-edge pivots clear of the fixed triangular cheeks.
    new_degrees=-sign*150.
    old_rot=np.array(Quaternion(Vector(old_axis),old_angle).to_matrix())
    bm=inv@backing.matrix_world
    outer=[]
    for vertex in list(backing.data.vertices)[:len(backing.data.vertices)//2]:
        model=np.array(bm@vertex.co)
        closed=H+old_rot@(model-H)+shift_model
        q=(closed-C)@Q
        if abs(q[0])>2.0:outer.append(closed)
    assert len(outer)==2,(joint.name,'contact edge',outer)
    outer.sort(key=lambda p:((p-C)@Q)[1])
    axis=np.array(outer[1]-outer[0]);axis/=np.linalg.norm(axis)
    closed_pivot=np.mean(outer,axis=0)
    deployed_pivot=closed_pivot-shift_model
    new_rot=np.array(Quaternion(Vector(axis),math.radians(new_degrees)).to_matrix())
    child_data={}
    for child in joint.children:
        if child.type!='MESH':continue
        M=inv@child.matrix_world
        ps=np.array([M@v.co for v in child.data.vertices])
        child_data[child]=(ps-H)@old_rot.T+H+shift_model
    old_joint=inv@joint.matrix_world
    metadata={key:[[np.array(old_joint@Vector(p)) for p in edge] for edge in joint[key]]
              if key=='crownSeamsLocal' else [np.array(old_joint@Vector(p)) for p in joint[key]]
              for key in ['crownSeamsLocal','seamEdgeLocal'] if key in joint}
    move_origin(joint,deployed_pivot)
    for child,closed in child_data.items():
        M=inv@child.matrix_world;Mi=M.inverted()
        deployed=np.array([deployed_pivot+new_rot.T@(p-shift_model-deployed_pivot)
                           for p in closed])
        for vertex,p in zip(child.data.vertices,deployed):vertex.co=Mi@Vector(p)
        child.data.update()
    jointM=(inv@joint.matrix_world).inverted()
    def local_from_closed(p):
        deployed=deployed_pivot+new_rot.T@(p-shift_model-deployed_pivot)
        return list(jointM@Vector(deployed))
    if 'crownSeamsLocal' in metadata:
        old=metadata['crownSeamsLocal']
        closed=[[H+old_rot@(p-H)+shift_model for p in edge] for edge in old]
        joint['crownSeamsLocal']=[[local_from_closed(p) for p in edge] for edge in closed]
    if 'seamEdgeLocal' in metadata:
        closed=[H+old_rot@(p-H)+shift_model for p in metadata['seamEdgeLocal']]
        joint['seamEdgeLocal']=[local_from_closed(p) for p in closed]
    joint['legacySourceHingeLine']=list(H)
    joint['sourceHingeLine']=list(deployed_pivot)
    joint['hingeAxisModel']=list(axis)
    joint['closedAngleDegrees']=new_degrees
    joint['hingeContactEdgeClosedModel']=[list(p) for p in outer]
    joint['physicalHinge']=True
    joint['hingeLocation']='armor outer contact edge'
    return float(np.linalg.norm(closed_pivot-H)),[list(p) for p in outer]


for name,row in rows.items():
    C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes'])
    ridge=float(np.mean([r['height'] for r in row['ridge'] if r['group']==2]))
    carriage=bpy.data.objects[name+'_Carriage']
    shift=(np.array(carriage['slideVector'])+np.array(carriage['liftVector']))@Q
    result={}
    for label,sign in [('Port',-1),('Starboard',1)]:
        fitted=[]
        for leaf in row['leaves']:
            if (('_Shutter_Port_' in leaf['name'])!=(label=='Port')):continue
            joint=bpy.data.objects[leaf['name']]
            backing=bpy.data.objects[joint.name+'_FittedBacking']
            grate=bpy.data.objects[joint.name+'_Skin']
            H=np.array(leaf['hinge'])
            rot=np.array(Quaternion(Vector(leaf['axis']),math.radians(joint['closedAngleDegrees'])).to_matrix())
            d=shift if leaf['group']>=3 else np.zeros(3)
            plane=np.array(joint['fittedHullFacetPlane']);flat=float(joint['ridgeHalfWidth'])
            profile=source_profile(backing,2,H,rot,d,C,Q)
            def taper(_y):return 1.
            def warp(p):return retune_point(p,H,rot,d,C,Q,sign,plane,flat,profile,ridge,taper)
            def closed_warp(p):
                return retune_point(p,None,None,np.zeros(3),C,Q,sign,plane,flat,profile,ridge,taper)
            retune_joint_metadata(joint,warp,C,Q,closed_warp)
            retune_mesh(backing,warp)
            retune_mesh(grate,warp)
            if leaf['group']==3:shorten_inner_grate(grate,H,rot,d,C,Q)
            joint['fittedUpperCrownHeight']=ridge
            hinge_shift=Q@d
            moved,edge=reanchor_leaf(joint,backing,H,leaf['axis'],hinge_shift,C,Q)
            fitted.append({'group':leaf['group'],'lowerEdgeProfile':profile.tolist(),
                           'upperCrownHeight':ridge,'hingeMove':moved,
                           'hingeContactEdgeClosedModel':edge})

        slider=bpy.data.objects[name+'_Slider_'+label]
        skin=bpy.data.objects[slider.name+'_TrapezoidSkin']
        plane=np.array(slider['fittedHullFacetPlane'])
        flat=float(bpy.data.objects[next(l['name'] for l in row['leaves']
                       if l['group']==2 and (('_Shutter_Port_' in l['name'])==(label=='Port')))]['ridgeHalfWidth'])
        profile=source_profile(skin,3,None,None,np.zeros(3),C,Q)
        rear=float(((np.array(slider['closedOutlineModel'][0])-C)@Q)[1])
        front=float(((np.array(slider['frontReceiverEdgeModel'][0])-C)@Q)[1])
        assert front>rear+5,(name,label,rear,front)
        def taper(y):return (front-y)/(front-rear)
        def warp(p):return retune_point(p,None,None,np.zeros(3),C,Q,sign,plane,flat,profile,ridge,taper)
        slider['closedOutlineModel']=[list(warp(p)) for p in slider['closedOutlineModel']]
        retune_mesh(skin,warp)
        slider['fittedUpperCrownHeight']=ridge
        slider['frontFit']='smooth first plate slopes from original crown to original lower rim'
        result[label]={'ridge':ridge,'sliderRearY':rear,'sliderFrontY':front,
                       'sliderLowerEdgeProfile':profile.tolist(),'leaves':fitted}
        print('CROWN',name,label,'lower rail preserved; upper ridge',round(ridge,4),flush=True)
    report[name]=result

A['version']='0.11.3'
A['sideBatteryRevision']='upper crowns follow accepted hull silhouette; lower armor edges remain on original inner rail'
bpy.context.view_layer.update()
basis=Matrix.Rotation(-math.pi/2,4,'X');nodes=[]
for o in [A]+[o for o in s.objects if o.get('staticJoint')]:
    m=basis@o.matrix_local@basis.inverted()
    nodes.append({'name':o.name,'parent':o.parent.name if o.parent else None,
                  'matrix':[m[r][c]for c in range(4)for r in range(4)],'extras':dict(o.items())})
(out/'rig-nodes.json').write_text(json.dumps(nodes,default=lambda v:list(v)))
(out/'crown-fit.json').write_text(json.dumps(report,indent=2))
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.11.3.blend'),compress=True)
