"""Correct the four vertical flank cradles from the immutable v0.11.0 asset.

Keep fixed bay transitions on the hull; align each full gun to its measured
channel; close only the missing triangular faces and paint inner stiffeners.
Static geometry and joint metadata only. Three.js continues to own animation.
"""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
R=Path(__file__).resolve().parents[1]
exec((R/'tools/revise_secondary_bridge_v090.py').read_text().split('def fit_channel_nose')[0])
out=R/'work/v0111-review';out.mkdir(exist_ok=True)
rows=json.loads((R/'docs/review/v0.11.0/side-batteries.json').read_text())
report={};hull=bpy.data.objects['holo.001'];hp=np.array([inv@hull.matrix_world@v.co for v in hull.data.vertices])

def flat_patch(name,points,parent,normal):
    pts=[Vector(p)for p in points]
    if (pts[1]-pts[0]).cross(pts[2]-pts[0]).dot(Vector(normal))<0:pts.reverse()
    o=prism(name,pts,.12,parent,light,light)
    o['surface']='measured local hull boundary closure';o['sideBatteryMechanism']=True
    return o

def saved_world(o):
    local=o.matrix_parent_inverse@o.matrix_basis
    return saved_world(o.parent)@local if o.parent else o.matrix_basis.copy()

for name,row in rows.items():
    C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes']);X,B,N=Q.T
    carriage=bpy.data.objects[name+'_Carriage'];gun=bpy.data.objects[name]
    fixed=[]
    # The source pedestal already includes the rear trough and its rails.
    # These separately extracted faces are the deep bay floor and the fixed
    # transition outside the red outline, not part of that moving pedestal.
    for o in list(carriage.children):
        if o.name.endswith('_Carriage_Trough')or '_FixedTroughReturn'in o.name:
            keep(o,A);o.name=o.name.replace('_Carriage_Trough','_FixedBayFloor')
            o['fixedBayStructure']=True;fixed.append(o.name)
    carriage['movingScope']='rear pedestal, gun, bearings and armor groups 3/4 only'
    carriage['fixedBayStructures']=fixed
    # Both triangular transition cuts use the existing rim, never a broad
    # overlay across the surrounding bay cheek.
    hq=(hp-C)@Q
    inner_receivers={}
    for label,sign in [('Port',-1),('Starboard',1)]:
        targets=[(sign*2.797,-.50,-.646),(sign*2.799,1.807,-.642),(sign*5.411,-2.25,-5.01)]
        ids=[int(np.argmin(np.linalg.norm(hq-np.array(t),axis=1)))for t in targets]
        assert len(set(ids))==3,(name,label,'transition rim')
        flat_patch(name+'_FixedTransitionPatch_'+label,hp[ids],A,N)
    # Removing the legacy raised tip wings also removed the fixed surface
    # below them. Recover those exact boundary vertices, omitting their old
    # raised lip. The closure stays on the hull and has no animation joint.
    with bpy.data.libraries.load(str(R/'assets/blender/odin_articulated_v0.10.0.blend'),link=False)as(fr,to):
        to.objects=[name+'_FrontCap_Skin']
    source=to.objects[0];M=inv@saved_world(source)
    ps=np.array([M@v.co for v in source.data.vertices]);q=(ps-C)@Q
    assert 18<q[:,1].min()<20 and 29<q[:,1].max()<31,(name,'source cap transform',q.min(0),q.max(0))
    for label,sign in [('Port',-1),('Starboard',1)]:
        signed=q[:,0]*sign;side=np.flatnonzero(signed>.1)
        root=side[np.argmax(signed[side])]
        crown=side[np.argmax(q[side,1])]
        front=side[np.argmin(np.abs(q[side,1]-(q[crown,1]-.90)))]
        low=side[np.argmin(np.abs(q[side,1]-(q[crown,1]-1.21)))]
        assert len({int(root),int(crown),int(front),int(low)})==4
        # Continue the LOWER slot's original nose face, not the larger outer
        # hull surround. Its rear diagonal is the user's marked receiver.
        candidates=[]
        for f in hull.data.polygons:
            if f.area<10:continue
            face=hq[list(f.vertices)];sx=face[:,0]*sign
            if len(face)==3 and sx.min()>.2 and sx.max()<2.6 and face[:,1].min()>16 and 27<face[:,1].max()<31 and np.ptp(face[:,1])>7 and face[:,2].min()>-2 and face[:,2].max()<4:
                plane=np.linalg.lstsq(np.c_[face[:,:2],np.ones(len(face))],face[:,2],rcond=None)[0]
                if 1.4<abs(plane[0])<1.5 and abs(plane[1])<.02:candidates.append((f.area,plane,face))
        assert len(candidates)==1,(name,label,'neighboring nose plane',len(candidates))
        plane=candidates[0][1];nose=q[[root,crown,front]].copy()
        receiver_face=candidates[0][2]
        receiver_root=receiver_face[np.argmin(receiver_face[:,1])]
        receiver_crown=receiver_face[np.argsort(receiver_face[:,1])[1]]
        # The small original rim has an exposed rear edge 0.16 units behind
        # the broad nose facet. Use that actual vertex, including its height.
        target=receiver_root+np.array([0,-.16,0])
        rim_root=hq[int(np.argmin(np.linalg.norm(hq-target,axis=1)))]
        assert np.linalg.norm(rim_root-target)<.02,(name,label,'inner rim edge')
        inner_receivers[label]=(receiver_crown.copy(),rim_root.copy())
        nose[:,2]=np.c_[nose[:,:2],np.ones(len(nose))]@plane
        nose_model=nose@Q.T+C
        patch=flat_patch(name+'_FixedNosePatch_'+label,nose_model,A,N)
        patch['sourceFacetPlane']=list(plane);patch['sourceFrameOrigin']=list(C);patch['sourceFrameAxes']=Q.tolist()
        patch['receiverLayer']='lower inner slot nose'
        flat_patch(name+'_FixedNoseReturn_'+label,[nose_model[2],nose_model[1],ps[low]],A,N)
    bpy.data.objects.remove(source,do_unlink=True)
    # Original source grates are entirely inside the fitted smooth skin.
    # Paint every stiffener and its return red, not merely the backing face.
    for leaf in row['leaves']:
        skin=bpy.data.objects[leaf['name']+'_Skin'];skin.data.materials.clear();skin.data.materials.append(red)
        for f in skin.data.polygons:f.material_index=0
        skin['interiorPrimer']=True
    mesh=next(c for c in gun.children if c.type=='MESH');M=inv@mesh.matrix_world;Mi=M.inverted()
    ps=np.array([M@v.co for v in mesh.data.vertices]);direction=np.array(bore(mesh,B));direction/=np.linalg.norm(direction)
    turn=Vector(direction).rotation_difference(Vector(B));rot=np.array(turn.to_matrix())
    pivot=np.array((inv@gun.matrix_world).translation)
    # Use the distal tube's circular muzzle ring, not the asymmetric shroud
    # bounding box, to locate the bore centerline.
    long=[]
    for p in parts(mesh):
        along=p['points']@direction
        if p['n']>100 and np.ptp(along)>35:long.append(p)
    tube=max(long,key=lambda p:(p['points']@direction).max())
    along=tube['points']@direction;ring=tube['points'][along>along.max()-.025]
    U=np.array(Vector(direction).orthogonal().normalized());V=np.cross(direction,U)
    uv=ring@np.stack([U,V],axis=1)
    a=np.c_[2*uv,np.ones(len(uv))];b=np.sum(uv*uv,axis=1);fit=np.linalg.lstsq(a,b,rcond=None)[0]
    line=U*fit[0]+V*fit[1]+direction*along.max()
    placed=(ps-pivot)@rot.T+pivot;line=rot@(line-pivot)+pivot
    correction=-X*((line-C)@X);placed+=correction;line+=correction
    half=np.mean([abs(((np.array(l['hinge'])-C)@Q)[0])for l in row['leaves']if l['group']==2])
    ridge=np.mean([r['height']for r in row['ridge']if r['group']==2]);flat=np.mean([r['halfWidth']for r in row['ridge']if r['group']==2]);base=np.mean([bpy.data.objects[l['name']]['backingSeatLift']for l in row['leaves']if l['group']==2])
    slider_fit={}
    if '_3_'in name:
        # Finish the first plate on the lower inner slot's diagonal lip.
        # Its smooth roof stays in the accepted plane; a short folded end
        # returns inward/down to the lip instead of extending to outer hull.
        for label,sign in [('Port',-1),('Starboard',1)]:
            joint=bpy.data.objects[name+'_Slider_'+label]
            skin=bpy.data.objects[joint.name+'_TrapezoidSkin']
            crown,outer=inner_receivers[label]
            end_rake=float((crown[1]-outer[1])/(sign*(outer[0]-crown[0])))
            assert 1.4<end_rake<1.6,(name,label,end_rake)
            end_y=float(outer[1])-end_rake*(half-sign*outer[0])
            skin_matrix=inv@skin.matrix_world;skin_inverse=skin_matrix.inverted();points=np.array([skin_matrix@v.co for v in skin.data.vertices]);qskin=(points-C)@Q
            old_front=np.array([row['sliderClosedRange'][1]+2.*(half-max(sign*p[0],flat))for p in qskin])
            front_vertices=np.flatnonzero(abs(qskin[:,1]-old_front)<.001)
            assert len(front_vertices)==6,(name,label,'slider front vertices',len(front_vertices))
            for index in front_vertices:
                qskin[index,1]=end_y+end_rake*(half-max(sign*qskin[index,0],flat))
                skin.data.vertices[int(index)].co=skin_inverse@Vector(C+Q@qskin[index])
            skin.data.update()
            top_crown=np.array([sign*flat,end_y+end_rake*(half-flat),ridge])
            top_outer=np.array([sign*half,end_y,base])
            top_center=np.array([sign*.025,top_crown[1],ridge])
            bottom_center=crown.copy();bottom_center[0]=sign*.025
            for suffix,outline in [('Slope',[top_crown,top_outer,outer,crown]),('Crown',[top_center,top_crown,crown,bottom_center])]:
                points=[Vector(C+Q@p)for p in outline]
                if (points[1]-points[0]).cross(points[2]-points[0]).dot(Vector(B))<0:points.reverse()
                returned=prism(joint.name+'_InnerRimReturn_'+suffix,points,.12,joint,light,red)
                returned['sideBatteryMechanism']=True;returned['receiverLayer']='lower inner slot rim'
            joint['frontEdgeRake']=end_rake
            joint['frontReceiverEdgeModel']=[list(C+Q@p)for p in [crown,outer]]
            joint['closedOutlineModel']=[list(C+Q@p)for p in np.concatenate([qskin[:3],qskin[3:6][::-1]])]
            joint['frontFit']='roof ends above inner slot lip; folded edge seats on original lower rim'
            slider_fit[label]={'frontEdgeRake':end_rake,'outerEnd':end_y,'receiverCrown':crown.tolist(),'receiverOuter':outer.tolist(),'receiverLayer':'lower inner slot rim','endReturnGauge':.12}
    seat=np.array(carriage['slideVector'])+np.array(carriage['liftVector']);q=(placed+seat-C)@Q
    edges=np.array([e.vertices[:]for e in mesh.data.edges]);qa,qb=q[edges[:,0]],q[edges[:,1]];samples=[q]
    for y in [-17.35,-8.65,.1,8.8,18.4]:
        mask=(qa[:,1]-y)*(qb[:,1]-y)<0;a,b=qa[mask],qb[mask]
        samples.append(a+(b-a)*((y-a[:,1])/(b[:,1]-a[:,1]))[:,None])
    check=np.concatenate(samples);roof=base+(ridge-base)*np.minimum(1,(half-abs(check[:,0]))/(half-flat))
    mask=(check[:,1]>-17.35)&(check[:,1]<18.4)&(abs(check[:,0])<half-.04)
    # Reserve the full source grate/rail depth below the exterior shell.
    lift=float(np.min(roof[mask]-check[mask,2]))-1.25
    placed+=N*lift;line+=N*lift
    for v,p in zip(mesh.data.vertices,placed):v.co=Mi@Vector(p)
    # Put the new pitch pivot on the same axis at the existing rear-trunnion
    # longitudinal station. No yaw or inward rest pitch remains.
    newpivot=line+B*((pivot-line)@B);move_origin(gun,newpivot)
    gun['sourceBoreDirectionModel']=list(B);gun['hingeAxisModel']=list(X);gun['outwardNormal']=list(N)
    gun['restPitchDegrees']=0.;gun['stowSink']=0.;gun['slotAxisModel']=list(B);gun['slotOriginModel']=list(C)
    gun['boreCenterModel']=list(line);gun['barrelCenterlineOffset']=float((line-C)@X)
    gun['trunnionReference']='rear station, on corrected channel-parallel bore centerline'
    bpy.context.view_layer.update();local=gun.matrix_world.inverted()@A.matrix_world
    actual_matrix=inv@mesh.matrix_world
    actual=np.array([actual_matrix@v.co for v in mesh.data.vertices])
    assert np.max(abs(actual-placed))<.0001,(name,'gun mesh placement differs from calibrated bore')
    gun['boreAxisPointsLocal']=[list(local@Vector(line+B*d))for d in[-15.,0.]]
    report[name]={'fixedObjects':fixed,'boreCorrectionDegrees':math.degrees(turn.angle),'boreTransverseOffset':float((line-C)@X),'boreRestAxis':list(B),'rearTrunnion':newpivot.tolist(),'normalSeatCorrection':lift,'muzzleRingSamples':len(ring),'restParallelToSlot':True,'aftSliderReceiverFit':slider_fit}
    print('CORRECTED',name,report[name],flush=True)

A['version']='0.11.1';A['sideBatteryRevision']='bounded rear cradle, centered parallel bores, restored local faces, red inner stiffeners'
bpy.context.view_layer.update();basis=Matrix.Rotation(-math.pi/2,4,'X');nodes=[]
for o in [A]+[o for o in s.objects if o.get('staticJoint')]:
    mat=basis@o.matrix_local@basis.inverted();nodes.append({'name':o.name,'parent':o.parent.name if o.parent else None,'matrix':[mat[r][c]for c in range(4)for r in range(4)],'extras':dict(o.items())})
(out/'rig-nodes.json').write_text(json.dumps(nodes,default=lambda v:list(v)))
(out/'corrections.json').write_text(json.dumps(report,indent=2))
# The source-cap library was only a measurement reference. Drop its unlinked
# ancestor/data copies so the editable deliverable contains the live asset.
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.11.1.blend'),compress=True)
