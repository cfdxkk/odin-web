"""Replace the four aft bay fillers with genuinely planar inclined armor.

Run in the v0.8.1 scene before saving the v0.8.2 editable copy.  Only the
moving aft leaves and their hinge metadata are edited; this helper does not
save a Blend or export any asset.
"""
import bpy
import bmesh
import hashlib
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree


def planar_aft_v082():
    root=Path(__file__).resolve().parents[1]
    asset=bpy.data.objects['Odin_Asset']; inverse=asset.matrix_world.inverted()
    reference=json.loads((root/'tools/main_armor_v081_boundaries.json').read_text(encoding='utf8'))
    basis=Quaternion((1,0,0),-math.pi/2)
    baseline_path=root/'docs/review/v0.8.2/baseline-v081-closed-pose.json'
    baseline=json.loads(baseline_path.read_text(encoding='utf8'))
    if baseline['assetVersion']!='0.8.1' or baseline['pose']['deployment']!=0:
        raise RuntimeError('Expected the explicit closed v0.8.1 baseline pose')
    pose0=baseline['pose']
    saved={o.name:(o.location.copy(),o.rotation_mode,o.rotation_quaternion.copy(),o.rotation_euler.copy())
           for o in bpy.data.objects if o.get('staticJoint')}
    for j in pose0['joints']:
        obj=bpy.data.objects.get(j['name'])
        if obj and not obj.name.startswith('Hatch_'):
            x,y,z=j['position'];obj.location=(x,-z,y);q=j['quaternion']
            obj.rotation_mode='QUATERNION';obj.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
    bpy.context.view_layer.update()

    def geometry(obj):
        obj.data.calc_loop_triangles();m=inverse@obj.matrix_world
        return [m@v.co for v in obj.data.vertices],[tuple(t.vertices) for t in obj.data.loop_triangles]
    def tree(obj):
        vs,ts=geometry(obj)
        return BVHTree.FromPolygons(vs,ts,all_triangles=True,epsilon=.000001)
    def surface(hull,x,y,direction):
        m=inverse@hull.matrix_world;mi=m.inverted()
        hit,p,_,_=hull.ray_cast(mi@Vector((x,y,direction*100)),mi.to_3x3()@Vector((0,0,-direction)))
        return (m@p).z if hit else None
    report={'revision':'0.8.2','fixedHullEdited':False,
            'baselinePose':'docs/review/v0.8.2/baseline-v081-closed-pose.json',
            'baselinePoseSha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),'leaves':{}}
    for bank,direction,hull_name,names in [
        ('Dorsal',1,'holo.001',['odin.005','odin.006','odin.007','odin.008']),
        ('Ventral',-1,'holo.013',['odin.013','odin.014','odin.015','odin.016'])]:
        hull=bpy.data.objects[hull_name];fixed=tree(hull);shrouds=[tree(bpy.data.objects[n]) for n in names]
        for side,sign in [('Port',-1),('Starboard',1)]:
            joint=bpy.data.objects[f'Hatch_{bank}_Aft_{side}'];obj=joint.children[0]
            old,_=geometry(obj);n=len(old)//2;rows=n//13
            upper=[old[r*13] for r in range(rows)];outer=[old[r*13+12] for r in range(rows)]
            lip=reference[bank][side]['lip'];y=upper[-1].y
            end_lip=None
            for first,last in zip(lip,lip[1:]):
                if first[1]<=y<=last[1]:
                    end_lip=Vector(first).lerp(Vector(last),(y-first[1])/(last[1]-first[1]));break
            if end_lip is None:raise RuntimeError(f'No main mating edge for {joint.name}')
            end_lip.x-=sign*.035;end_lip.z+=direction*.005
            anchors=np.array([list(upper[0]),list(upper[-1]),list(end_lip)])
            co=np.linalg.solve(np.c_[anchors[:,:2],np.ones(3)],anchors[:,2])
            a,b,c=[float(v) for v in co]
            normal=Vector((-a,-b,1)).normalized()*direction
            thickness=.025
            def point(x,y): return Vector((x,y,a*x+b*y+c))
            points=[];free=[];edge=[]
            for row_index,(hi,lo) in enumerate(zip(upper,outer)):
                y=hi.y;start=sign*hi.x;end=sign*lo.x
                def shroud_distance(radius):
                    return min(t.find_nearest(point(sign*radius,y))[3] for t in shrouds)
                if row_index not in (0,rows-1) and shroud_distance(start)>.0431:
                    for step in range(1,181):
                        contact=start-step*.005
                        if shroud_distance(contact)<.043:break
                    else:contact=None
                    if contact is not None:
                        clear=contact+.005
                        for _ in range(28):
                            mid=(contact+clear)*.5
                            if shroud_distance(mid)<.043:contact=mid
                            else:clear=mid
                        start=clear
                def clears(radius):
                    x=sign*radius;p=point(x,y);z=surface(hull,x,y,direction)
                    bottom=p-normal*thickness
                    gap=min(fixed.find_nearest(p)[3],fixed.find_nearest(bottom)[3])
                    return gap>.032 and (z is None or direction*(p.z-z)>thickness*abs(normal.z)+.012)
                # The former shell bent down onto the shoulder.  Trim the
                # rigid plane at its real shoulder intersection instead.
                good=start;bad=None
                for step in range(1,math.ceil((end-start)/.025)+1):
                    candidate=min(end,start+step*.025)
                    if not clears(candidate):bad=candidate;break
                    good=candidate
                if bad is not None:
                    for _ in range(30):
                        mid=(good+bad)*.5
                        if clears(mid):good=mid
                        else:bad=mid
                    end=good
                hi=point(sign*start,y);lo=point(sign*end,y)
                free.append(hi);edge.append(lo);points.extend([hi,lo])
            faces=[(r*2,r*2+1,(r+1)*2+1,(r+1)*2) for r in range(rows-1)]
            count=len(points);vertices=points+[p-normal*thickness for p in points]
            all_faces=faces+[tuple(i+count for i in reversed(f)) for f in faces]
            boundary=[r*2 for r in range(rows)]+[r*2+1 for r in reversed(range(rows))]
            all_faces.extend((i,j,j+count,i+count) for i,j in zip(boundary,boundary[1:]+boundary[:1]))
            old_name=obj.name;bpy.data.objects.remove(obj,do_unlink=True)
            mesh=bpy.data.meshes.new(old_name);mesh.from_pydata(vertices,[],all_faces);mesh.update()
            bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
            obj=bpy.data.objects.new(old_name,mesh);bpy.context.scene.collection.objects.link(obj);obj.parent=asset
            bpy.context.view_layer.update();world=obj.matrix_world.copy();obj.parent=joint;obj.matrix_world=world
            mesh.materials.append(bpy.data.materials['Odin_Paint_Light']);mesh.materials.append(bpy.data.materials['Odin_Turret_Interior_DeepRed'])
            for face in mesh.polygons:
                face.use_smooth=False
                if face.normal.dot(normal)<-.5:face.material_index=1
            bpy.context.view_layer.update()
            vs,ts=geometry(obj)
            axle=[Vector(p) for p in joint['hingeEdge']];axis=Vector(joint['hingeAxis']);angle=float(joint['openingAngleDegrees'])
            # A tight static seam needs a little relief only where the lower
            # shroud toe sweeps past it in the first few hinge degrees.  Keep
            # the same plane and both end points: retract the in-plane edge
            # locally, never raise vertices off the rigid armor face.
            target=[p.copy() for p in free]
            original=[point(p.x,p.y) for p in upper]
            weights=[1.0]*rows
            local_inverse=(inverse@obj.matrix_world).inverted()
            for fit_iteration in range(45):
                touched=set()
                for quarter in range(25):
                    degree=quarter*.25
                    rotation=Quaternion(axis,math.radians(angle*degree/130))
                    posed=[axle[0]+rotation@(v-axle[0]) for v in vs]
                    posed_tree=BVHTree.FromPolygons(posed,ts,all_triangles=True,epsilon=.000001)
                    for obstacle in shrouds:
                        for fi,_ in posed_tree.overlap(obstacle):
                            touched.update((vi%count)//2 for vi in ts[fi])
                if not touched:break
                affected={j for i in touched for j in range(max(1,i-2),min(rows-1,i+3))}
                for row in affected:weights[row]=max(0.,weights[row]-.04)
                weights=[min(weights[max(0,i-1):min(rows,i+2)]) if i not in (0,rows-1) else 1. for i in range(rows)]
                for row in range(1,rows-1):
                    radius=original[row].x+(target[row].x-original[row].x)*weights[row]
                    p=point(radius,original[row].y);free[row]=p
                    obj.data.vertices[row*2].co=local_inverse@p
                    obj.data.vertices[row*2+count].co=local_inverse@(p-normal*thickness)
                obj.data.update();vs,ts=geometry(obj)
            else:raise RuntimeError(f'Could not fit planar shroud sweep edge for {joint.name}')
            if bank=='Ventral' and side=='Starboard':
                # The exported runtime samples an additional 1.16-degree
                # hinge pose at d=.15. Give its tiny shroud-toe contact a
                # local in-plane allowance; leave the plane and end seams.
                for row in range(1,rows-1):
                    distance=abs(free[row].y-49.40)/.75
                    if distance>=1:continue
                    taper=(1-distance*distance)**2
                    p=point(free[row].x+.012*taper,free[row].y);free[row]=p
                    obj.data.vertices[row*2].co=local_inverse@p
                    obj.data.vertices[row*2+count].co=local_inverse@(p-normal*thickness)
                obj.data.update();vs,ts=geometry(obj)
            moving=BVHTree.FromPolygons(vs,ts,all_triangles=True,epsilon=.000001)
            sweep=[]
            for degree in range(131):
                rotation=Quaternion(axis,math.radians(angle*degree/130))
                posed=[axle[0]+rotation@(v-axle[0]) for v in vs]
                posed_tree=BVHTree.FromPolygons(posed,ts,all_triangles=True,epsilon=.000001)
                hits=posed_tree.overlap(fixed);shroud_hits=sum(len(posed_tree.overlap(t)) for t in shrouds)
                if hits or shroud_hits:sweep.append({'degree':degree,'hullPairs':len(hits),'shroudPairs':shroud_hits})
            distances_upper=[min(t.find_nearest(p)[3] for t in shrouds) for p in free]
            distances_outer=[fixed.find_nearest(p)[3] for p in edge]
            residual=max(abs(normal.dot(vs[i]-vs[0])) for i in range(count))
            part={'outerPlane':list(co),'planeAnchors':anchors.tolist(),'maximumPlanarityError':residual,'constantNormalThickness':thickness,
                'upperDistanceRange':[min(distances_upper),max(distances_upper)],'outerDistanceRange':[min(distances_outer),max(distances_outer)],
                'hullClosedPairs':len(moving.overlap(fixed)),'shroudClosedPairs':sum(len(moving.overlap(t)) for t in shrouds),
                'sweepAngles':131,'openingAngleDegrees':angle,'hingeUnchanged':True,
                'upperEdgeFitIterations':fit_iteration,'upperEdgeTargetGap':.043,
                'upperEdgeMotionReliefMax':max((free[i]-target[i]).length for i in range(rows)),
                'upperEdgeMaximumInPlaneChange':max((free[i]-original[i]).length for i in range(rows)),'sweep':sweep}
            report['leaves'][joint.name]=part
            joint['construction']='single-planar-inclined-aft-armor-slab'
            joint['planeNormal']=list(normal);joint['planarityTolerance']=.00003
            joint['sourceReference']='Single plane through source shroud and main-armor mating edge; trimmed at unchanged hull intersection'
            joint['closedOutlineXY']=[[p.x,p.y] for p in free+list(reversed(edge))]
            print('PLANAR_AFT',joint.name,json.dumps(part),flush=True)
    for name,(location,mode,quat,euler) in saved.items():
        if name.startswith('Hatch_'):continue
        obj=bpy.data.objects[name];obj.location=location;obj.rotation_mode=mode
        if mode=='QUATERNION':obj.rotation_quaternion=quat
        else:obj.rotation_euler=euler
    bpy.context.view_layer.update()
    out=root/'work/v082-review/planar-aft.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf8')
    assert all(p['maximumPlanarityError']<.00001 and not p['sweep'] for p in report['leaves'].values()),report
    return report


planar_aft_v082()
