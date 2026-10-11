"""Straighten four vertical flank armor runs and close their lower nose seam.

The closed skins are edited in each mount's measured frame.  Deployed leaf
meshes are then rebaked around the newly measured contact edges, so a change
to the silhouette cannot introduce an orbital hinge.  The small triangular
infill is sampled from the *lower* source hull panel, not the upper fairing.
"""
import bpy, json, math, numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

R=Path(__file__).resolve().parents[1]
exec((R/'tools/revise_secondary_bridge_v090.py').read_text().split('def fit_channel_nose')[0])
out=R/'work/v0114-review';out.mkdir(exist_ok=True)
rows=json.loads((R/'docs/review/v0.11.0/side-batteries.json').read_text())
hull=bpy.data.objects['holo.001']
hp=np.array([inv@hull.matrix_world@v.co for v in hull.data.vertices])
report={}


def model_vertices(obj):
    M=inv@obj.matrix_world
    return np.array([M@v.co for v in obj.data.vertices])


def replace_vertices(obj, points):
    Mi=(inv@obj.matrix_world).inverted()
    assert len(obj.data.vertices)==len(points)
    for v,p in zip(obj.data.vertices,points):v.co=Mi@Vector(p)
    obj.data.update()


def frame_profile(points,C,Q,sign,count):
    q=(points[:count]-C)@Q
    outer=sorted((float(p[1]),float(abs(p[0]))) for p in q if sign*p[0]>2.0)
    assert len(outer)==count//3,(len(outer),count)
    return np.array(outer)


def warp_closed(points,C,Q,sign,flat,old_profile,target,plane,crown_profile,target_crown):
    q=(points-C)@Q
    ys=old_profile[:,0];xs=old_profile[:,1]
    old=np.interp(q[:,1],ys,xs)
    new=target(q[:,1])
    u=sign*q[:,0]
    fraction=np.maximum(0.,(u-flat)/np.maximum(.01,old-flat))
    shift=(new-old)*fraction
    q[:,0]+=sign*shift
    # Preserve the measured lower hull slope under the moved outside edge.
    # The inner ridge is adjusted to the front receiver height below.
    q[:,2]+=plane[0]*sign*shift
    # The accepted first plate's forward receiver is the actual hull crown.
    # Lower the high three aft crowns to it and remove the first plate's
    # longitudinal ramp.  The outer contact edge keeps its measured seat.
    old_crown=np.interp(q[:,1],crown_profile[:,0],crown_profile[:,1])
    q[:,2]+=(target_crown-old_crown)*np.clip(1.-fraction,0.,1.)
    return C+q@Q.T


def rebake_leaf(joint,backing,carriage_shift,C,Q,sign,flat,target,plane,target_crown):
    old_H=np.array(joint['sourceHingeLine'])
    old_axis=np.array(joint['hingeAxisModel']);old_angle=math.radians(joint['closedAngleDegrees'])
    old_R=np.array(Quaternion(Vector(old_axis),old_angle).to_matrix())
    old_joint=inv@joint.matrix_world
    child_data={c:model_vertices(c) for c in joint.children if c.type=='MESH'}
    def close(p):return (p-old_H)@old_R.T+old_H+carriage_shift
    old_profile=frame_profile(close(child_data[backing]),C,Q,sign,len(backing.data.vertices)//2)
    old_ridge=float(joint['fittedUpperCrownHeight'])
    crown_profile=np.array([[old_profile[0,0],old_ridge],[old_profile[-1,0],old_ridge]])
    def transform(p):return warp_closed(close(p),C,Q,sign,flat,old_profile,target,plane,crown_profile,target_crown)
    closed_data={child:transform(p) for child,p in child_data.items()}
    outer=(closed_data[backing][:len(backing.data.vertices)//2]-C)@Q
    outer=np.array([closed_data[backing][i] for i,p in enumerate(outer) if sign*p[0]>2.0])
    assert len(outer)==2,(joint.name,len(outer))
    outer=sorted(outer,key=lambda p:((p-C)@Q)[1])
    axis=(outer[1]-outer[0]);axis/=np.linalg.norm(axis)
    assert np.dot(axis,old_axis)>.99,(joint.name,'axis reversed')
    H=np.mean(outer,axis=0)-carriage_shift
    new_R=np.array(Quaternion(Vector(axis),old_angle).to_matrix())
    metadata={k:[[np.array(old_joint@Vector(v)) for v in edge] for edge in joint[k]]
              if k=='crownSeamsLocal' else [np.array(old_joint@Vector(v)) for v in joint[k]]
              for k in ['crownSeamsLocal','seamEdgeLocal'] if k in joint}
    def deploy(p):return (p-carriage_shift-H)@new_R+H
    move_origin(joint,H)
    for child,closed in closed_data.items():replace_vertices(child,deploy(closed))
    Mi=(inv@joint.matrix_world).inverted()
    def local(p):return list(Mi@Vector(deploy(transform(np.array([p]))[0])))
    if 'crownSeamsLocal'in metadata:
        joint['crownSeamsLocal']=[[local(p) for p in edge] for edge in metadata['crownSeamsLocal']]
    if 'seamEdgeLocal'in metadata:
        joint['seamEdgeLocal']=[local(p) for p in metadata['seamEdgeLocal']]
    if 'closedSeamEdgeModel'in joint:
        joint['closedSeamEdgeModel']=[list(p) for p in warp_closed(np.array(joint['closedSeamEdgeModel']),C,Q,sign,flat,old_profile,target,plane,crown_profile,target_crown)]
    joint['sourceHingeLine']=list(H)
    joint['hingeAxisModel']=list(axis)
    joint['hingeContactEdgeClosedModel']=[list(p) for p in outer]
    joint['contactLineFit']='straight shared plan-view rail'
    joint['fittedUpperCrownHeight']=float(target_crown)
    return {'before':old_profile.tolist(),'after':[((p-C)@Q).tolist() for p in outer],
            'contactEdgeError':float(max(np.linalg.norm((H+new_R@(deploy(p)-H)+carriage_shift)-p) for p in outer))}


def lower_nose_infill(name,label,C,Q,sign,source_end):
    """Fill only the slit between the source lower nose and first armor tip."""
    patch=bpy.data.objects[name+'_FixedNosePatch_'+label]
    pq=(model_vertices(patch)[:len(patch.data.vertices)//2]-C)@Q
    # The old upper patch already has the two longitudinal stations.  Its
    # root lies just above the lower hull, whose actual source vertices are
    # used below to construct the new, independent lower-panel face.
    root=pq[np.argmin(pq[:,1])]
    crown=pq[np.argmax(pq[:,1])]
    hq=(hp-C)@Q
    def source_near(target,tol):
        distances=np.linalg.norm(hq-target,axis=1)
        i=int(np.argmin(distances))
        assert distances[i]<tol,(name,label,'source boundary',target,hq[i],distances[i])
        return i
    # Source end is the inner rim at y≈18.25/19.55.  Its continuing boundary
    # vertex at +0.16 is the third vertex of the triangular *lower* slit.
    inner=source_near(source_end+np.array([0,.167,0]),.08)
    # Choose source vertices below the old overlay, then validate the
    # adjacent panel's x-slope against the original lower hull.
    outer=source_near(root+np.array([0,0,-.08]),.13)
    apex=source_near(crown,.08)
    ids=[inner,outer,apex]
    q=hq[ids]
    # This third boundary belongs to the broad lower nose facet: the new
    # triangle spans the *dark slit* between it and the previous upper patch.
    assert sign*q[2,0]<.6 and q[2,1]-q[0,1]>10,(name,label,'lower nose crown',q)
    pts=[Vector(p) for p in hp[ids]]
    if (pts[1]-pts[0]).cross(pts[2]-pts[0]).dot(Vector(Q[:,2]))<0:pts.reverse()
    fill=prism(name+'_FixedLowerNoseInfill_'+label,pts,.06,A,light,light)
    fill['sideBatteryMechanism']=True
    fill['fixedBayStructure']=True
    fill['sourceHullVertexIds']=ids
    fill['receiverLayer']='original lower inner-slot nose panel'
    fill['surface']='flush lower-panel triangle; upper fairing untouched'
    return {'sourceIds':ids,'vertices':q.tolist()}


for name,row in rows.items():
    C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes'])
    carriage=bpy.data.objects[name+'_Carriage']
    shift=np.array(carriage['slideVector'])+np.array(carriage['liftVector'])
    result={}
    for label,sign in [('Port',-1),('Starboard',1)]:
        leafs=[l for l in row['leaves'] if (('_Shutter_Port_'in l['name'])==(label=='Port'))]
        rear_joint=bpy.data.objects[next(l['name'] for l in leafs if l['group']==4)]
        rear_edge=np.array(rear_joint['hingeContactEdgeClosedModel'])
        rear_q=(rear_edge-C)@Q
        rear=rear_q[np.argmin(rear_q[:,1])]
        slider=bpy.data.objects[name+'_Slider_'+label]
        receiver=(np.array(slider['frontReceiverEdgeModel'])-C)@Q
        front=receiver[np.argmax(sign*receiver[:,0])]
        crown=receiver[np.argmin(sign*receiver[:,0])]
        target_crown=float(crown[2])
        assert 2.4<target_crown<3.1,(name,label,'source hull crown',target_crown)
        y0=float(rear[1]);x0=float(sign*rear[0]);y1=float(front[1]);x1=float(sign*front[0])
        assert y1>y0+30 and .02<abs(x1-x0)<.08,(name,label,y0,x0,y1,x1)
        def target(y):return x0+(x1-x0)*(np.asarray(y)-y0)/(y1-y0)
        sides=[]
        for leaf in leafs:
            joint=bpy.data.objects[leaf['name']]
            backing=bpy.data.objects[joint.name+'_FittedBacking']
            plane=np.array(joint['fittedHullFacetPlane']);flat=float(joint['ridgeHalfWidth'])
            d=shift if leaf['group']>=3 else np.zeros(3)
            value=rebake_leaf(joint,backing,d,C,Q,sign,flat,target,plane,target_crown)
            value['group']=leaf['group'];sides.append(value)
        skin=bpy.data.objects[slider.name+'_TrapezoidSkin']
        skin_data=model_vertices(skin)
        profile=frame_profile(skin_data,C,Q,sign,len(skin.data.vertices)//2)
        top_q=(skin_data[:len(skin.data.vertices)//2]-C)@Q
        inner=top_q[np.abs(top_q[:,0])<.1]
        crown_profile=inner[np.argsort(inner[:,1])][:,[1,2]]
        assert len(crown_profile)==3,(name,label,'first plate crown profile',crown_profile)
        flat=float(bpy.data.objects[next(l['name'] for l in leafs if l['group']==2)]['ridgeHalfWidth'])
        plane=np.array(slider['fittedHullFacetPlane'])
        replace_vertices(skin,warp_closed(skin_data,C,Q,sign,flat,profile,target,plane,crown_profile,target_crown))
        slider['closedOutlineModel']=[list(p) for p in warp_closed(np.array(slider['closedOutlineModel']),C,Q,sign,flat,profile,target,plane,crown_profile,target_crown)]
        slider['straightOuterRail']='shared original rear-to-front hull contacts'
        slider['fittedUpperCrownHeight']=target_crown
        result[label]={'line':{'rearY':y0,'rearX':x0,'frontY':y1,'frontX':x1},
                       'sourceHullCrownHeight':target_crown,
                       'leaves':sides,'sliderBefore':profile.tolist(),
                       'lowerNoseInfill':lower_nose_infill(name,label,C,Q,sign,front)}
        print('STRAIGHT',name,label,'rail',x0,y0,'to',x1,y1,'and lower seam filled',flush=True)
    report[name]=result

A['version']='0.11.4'
A['sideBatteryRevision']='straight source-height crowns and outer rails; lower nose triangular seams closed'
bpy.context.view_layer.update();basis=Matrix.Rotation(-math.pi/2,4,'X');nodes=[]
for o in [A]+[o for o in s.objects if o.get('staticJoint')]:
    m=basis@o.matrix_local@basis.inverted()
    nodes.append({'name':o.name,'parent':o.parent.name if o.parent else None,
                  'matrix':[m[r][c]for c in range(4)for r in range(4)],'extras':dict(o.items())})
(out/'rig-nodes.json').write_text(json.dumps(nodes,default=lambda v:list(v)))
(out/'contour-fit.json').write_text(json.dumps(report,indent=2))
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.11.4.blend'),compress=True)
