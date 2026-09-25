"""Close the four main-battery aft seams against the real closed web pose.

Execute in the v0.8 editable scene; no source file or exported asset is saved.
The fixed hull and rotating shrouds are reference surfaces and are never edited.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree


def fit_aft_seams_v081():
    root = Path(__file__).resolve().parents[1]
    reference = json.loads((root/'tools/main_armor_v07_boundaries.json').read_text(encoding='utf8'))
    poses = json.loads((root/'work/rig-review/poses.json').read_text(encoding='utf8'))
    pose0 = poses[0] if isinstance(poses, list) else poses['poses'][0]
    asset = bpy.data.objects['Odin_Asset']
    inverse = asset.matrix_world.inverted()
    basis = Quaternion((1, 0, 0), -math.pi/2)
    saved = {o.name:(o.location.copy(), o.rotation_mode, o.rotation_quaternion.copy(), o.rotation_euler.copy())
             for o in bpy.data.objects if o.get('staticJoint')}
    for joint in pose0['joints']:
        obj=bpy.data.objects.get(joint['name'])
        if obj and not obj.name.startswith('Hatch_'):
            x,y,z=joint['position']; obj.location=(x,-z,y)
            q=joint['quaternion']; obj.rotation_mode='QUATERNION'
            obj.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
    bpy.context.view_layer.update()
    light=bpy.data.materials['Odin_Paint_Light']
    red=bpy.data.materials['Odin_Turret_Interior_DeepRed']

    def curve(points,y):
        if y<=points[0][1]: return Vector(points[0])
        if y>=points[-1][1]: return Vector(points[-1])
        for a,b in zip(points,points[1:]):
            if a[1]<=y<=b[1]: return Vector(a).lerp(Vector(b),(y-a[1])/(b[1]-a[1]))

    def tree(obj):
        obj.data.calc_loop_triangles(); transform=inverse@obj.matrix_world
        return BVHTree.FromPolygons([transform@v.co for v in obj.data.vertices],
            [tuple(t.vertices) for t in obj.data.loop_triangles],all_triangles=True,epsilon=.000001)

    def surface(hull,x,y,direction):
        transform=inverse@hull.matrix_world; inv=transform.inverted()
        hit,p,_,_=hull.ray_cast(inv@Vector((x,y,direction*100)),inv.to_3x3()@Vector((0,0,-direction)))
        return (transform@p).z if hit else None

    def create_skin(name,points,thickness,faces,parent,direction):
        count=len(points); vertices=list(points)+[p+Vector((0,0,-direction*t)) for p,t in zip(points,thickness)]
        edges={}
        for face in faces:
            for a,b in zip(face,face[1:]+face[:1]):
                key=tuple(sorted((a,b))); edges[key]=edges.get(key,0)+1
        all_faces=faces+[tuple(i+count for i in reversed(f)) for f in faces]
        all_faces.extend((a,b,b+count,a+count) for (a,b),n in edges.items() if n==1)
        old=bpy.data.objects.get(name)
        if old: bpy.data.objects.remove(old,do_unlink=True)
        data=bpy.data.meshes.new(name); data.from_pydata(vertices,[],all_faces); data.update()
        bm=bmesh.new(); bm.from_mesh(data); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
        obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj);obj.parent=asset
        bpy.context.view_layer.update(); world=obj.matrix_world.copy();obj.parent=parent;obj.matrix_world=world
        data.materials.append(light);data.materials.append(red)
        for polygon in data.polygons:
            if polygon.normal.z*direction<-.12: polygon.material_index=1
        return obj

    report={'revision':'0.8.1','fixedHullEdited':False,'leaves':{}}
    exterior={'Dorsal':(81.0,112.6169,14.45,12.55),'Ventral':(40.0,63.5674,15.40,14.05)}
    for bank,config in reference.items():
        direction=config['direction'];hull=bpy.data.objects[config['hull']];fixed=tree(hull)
        shroud_names=['odin.005','odin.006','odin.007','odin.008'] if bank=='Dorsal' else ['odin.013','odin.014','odin.015','odin.016']
        shroud_trees=[tree(bpy.data.objects[n]) for n in shroud_names]
        y0,y1,x0,x1=exterior[bank]
        for side,sign in [('Port',-1),('Starboard',1)]:
            name=f'Hatch_{bank}_Aft_{side}';joint=bpy.data.objects[name]
            upper=config[side]['upper']
            start=upper[0][1]+.04;end=upper[-1][1]-.02
            rows=math.ceil((end-start)/.10)+1
            ys=[start+(end-start)*i/(rows-1) for i in range(rows)]
            outer=[]
            for y in ys:
                x=sign*(x0+(x1-x0)*(y-y0)/(y1-y0))
                z=surface(hull,x,y,direction)
                if z is None:raise RuntimeError(f'No hull surface for {name} at {x,y}')
                outer.append(Vector((x,y,z+direction*.045)))
            # The hinge follows the hull's inclined shoulder. Its axle sits
            # within the rounded edge; the visible lip is contoured to the
            # unchanged hull instead of hovering on a lifted straight line.
            a=outer[0].copy();b=outer[-1].copy()
            residual=[direction*(p.z-a.lerp(b,i/(rows-1)).z) for i,p in enumerate(outer)]
            offset=min(residual)-.025
            a.z+=direction*offset;b.z+=direction*offset
            a.x+=sign*.25;b.x+=sign*.25
            points=[];thickness=[];free=[]
            columns=[0,.10,.30,.55,.78,.93,1]
            width=13
            for y,lo in zip(ys,outer):
                guess=curve(upper,y)+Vector((sign*.025,0,-direction*.035))
                closest=min((t.find_nearest(guess) for t in shroud_trees),key=lambda result:result[3])[0]
                hi=closest+(guess-closest).normalized()*.043
                hi.y=y
                for _ in range(5):
                    closest=min((t.find_nearest(hi) for t in shroud_trees),key=lambda result:result[3])[0]
                    hi=closest+(hi-closest).normalized()*.043;hi.y=y
                free.append(hi)
                inner=curve(config[side]['aftLip'],y)
                inner.y=y;inner.x-=sign*.025;inner.z+=direction*.035
                # Behind the gap's widest end the housing toe already lies
                # outboard of the bay lip. Do not send a false folded strip
                # back underneath that solid rotating housing.
                gap=sign*(inner.x-hi.x)
                blend=max(0.,min(1.,gap/.75));blend=blend*blend*(3-2*blend)
                inner=hi.lerp(lo,.33).lerp(inner,blend)
                row=[]
                for t in columns:
                    row.append((hi.lerp(inner,t),.12*(1-t)+.014*t))
                for t in columns[1:]:
                    row.append((inner.lerp(lo,t),.014))
                for p,thick in row:
                    hz=surface(hull,p.x,p.y,direction)
                    if hz is not None:p.z=direction*max(direction*p.z,direction*hz+thick+.025)
                    points.append(p);thickness.append(thick)
            faces=[(r*width+c,r*width+c+1,(r+1)*width+c+1,(r+1)*width+c)
                   for r in range(rows-1) for c in range(width-1)]
            joint.location=(a+b)*.5;joint.rotation_mode='QUATERNION';joint.rotation_quaternion=Quaternion()
            bpy.context.view_layer.update()
            skin=create_skin(name+'_GapFiller',points,thickness,faces,joint,direction)
            # The fixed shoulder contains small raised facets between ray
            # samples. Correct only facets that actually intersect it; never
            # lift the entire perimeter to hide this local contact.
            skin.data.calc_loop_triangles()
            tris=[tuple(t.vertices) for t in skin.data.loop_triangles]
            vertex_correction={}
            for iteration in range(100):
                m=inverse@skin.matrix_world
                verts=[m@v.co for v in skin.data.vertices]
                moving=BVHTree.FromPolygons(verts,tris,all_triangles=True,epsilon=.000001)
                hits=moving.overlap(fixed)
                if not hits:break
                touched={v%len(points) for i,_ in hits for v in tris[i]}
                for index in touched:
                    for actual in [index,index+len(points)]:
                        skin.data.vertices[actual].co.z+=direction*.008
                    vertex_correction[index]=vertex_correction.get(index,0)+.008
            skin.data.update()
            axis=(b-a).normalized();angle=sign*direction*130
            joint['hingeAxis']=list(axis);joint['hingeEdge']=[list(a),list(b)];joint['openingAngleDegrees']=angle
            joint['slideVector']=[0,0,0]
            joint['construction']='closed-web-pose-fitted-aft-leaf-with-tapered-hull-lip'
            joint['sourceReference']='Full original shroud lower outline and sampled fixed exterior hull shoulder'
            joint['hullClearanceCm']=.025;joint['closedOutlineXY']=[[p.x,p.y] for p in free+list(reversed(outer))]
            bpy.context.view_layer.update();skin.data.calc_loop_triangles();m=inverse@skin.matrix_world
            vertices=[m@v.co for v in skin.data.vertices];triangles=[tuple(t.vertices) for t in skin.data.loop_triangles]
            upper_distances=[min(t.find_nearest(vertices[i*width])[3] for t in shroud_trees) for i in range(rows)]
            outer_distances=[fixed.find_nearest(vertices[i*width+width-1])[3] for i in range(rows)]
            closed_tree=BVHTree.FromPolygons(vertices,triangles,all_triangles=True,epsilon=.000001)
            shroud_intersections={n:len(closed_tree.overlap(t)) for n,t in zip(shroud_names,shroud_trees)}
            shroud_hit_y={n:[min(vertices[v].y for i,_ in closed_tree.overlap(t) for v in triangles[i]),max(vertices[v].y for i,_ in closed_tree.overlap(t) for v in triangles[i])]
                          for n,t in zip(shroud_names,shroud_trees) if closed_tree.overlap(t)}
            collisions=[];shroud_sweep=[]
            for degree in range(131):
                rot=Quaternion(axis,math.radians(angle*degree/130))
                moved=[a+rot@(p-a) for p in vertices]
                moving=BVHTree.FromPolygons(moved,triangles,all_triangles=True,epsilon=.000001)
                hits=moving.overlap(fixed)
                if hits:collisions.append({'degrees':degree,'pairs':len(hits),'sample':[list(moved[i]) for i in triangles[hits[0][0]]]})
                shroud_pairs=sum(len(moving.overlap(t)) for t in shroud_trees)
                if shroud_pairs:shroud_sweep.append({'degrees':degree,'pairs':shroud_pairs})
            report['leaves'][name]={'rows':rows,'hingeEdge':[list(a),list(b)],'angleDegrees':angle,
                'upperSeamNominal':math.sqrt(.025**2+.035**2),'hullLipNominal':.045,
                'upperStart':list(free[0]),'upperEnd':list(free[-1]),'hullCollisionAngles':collisions}
            report['leaves'][name]['maxLocalHullFitCorrection']=max(vertex_correction.values(),default=0)
            report['leaves'][name]['actualUpperSurfaceDistanceRange']=[min(upper_distances),max(upper_distances)]
            report['leaves'][name]['actualOuterSurfaceDistanceRange']=[min(outer_distances),max(outer_distances)]
            report['leaves'][name]['closedShroudIntersections']=shroud_intersections
            report['leaves'][name]['closedShroudHitY']=shroud_hit_y
            report['leaves'][name]['closedShroudSweepIntersections']=shroud_sweep
            if collisions or shroud_sweep:
                raise RuntimeError(f'{name} has articulation intersections: hull={collisions[:3]}, shroud={shroud_sweep[:3]}')
            print('AFT_SEAM',name,'collisions',collisions[:10],flush=True)
    for name,(location,mode,quat,euler) in saved.items():
        if name.startswith('Hatch_'):continue
        obj=bpy.data.objects[name];obj.location=location;obj.rotation_mode=mode
        if mode=='QUATERNION':obj.rotation_quaternion=quat
        else:obj.rotation_euler=euler
    bpy.context.view_layer.update()
    dest=root/'work/v081-review/aft-seams.json';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2),encoding='utf8')
    return report


fit_aft_seams_v081()
