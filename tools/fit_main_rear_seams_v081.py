"""Fit only the long main armor's rear seam to the actual closed JS shrouds.

Run after the main/aft geometry builders. The nose and outer hull seam remain
unchanged. No Blend or GLB is saved and all reference joint poses are restored.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree


def fit_main_rear_seams_v081():
    root=Path(__file__).resolve().parents[1]
    ref=json.loads((root/'tools/main_armor_v081_boundaries.json').read_text(encoding='utf8'))
    all_poses=json.loads((root/'work/rig-review/poses.json').read_text(encoding='utf8'))
    pose0=all_poses[0] if isinstance(all_poses,list) else all_poses['poses'][0]
    asset=bpy.data.objects['Odin_Asset'];inverse=asset.matrix_world.inverted()
    basis=Quaternion((1,0,0),-math.pi/2)
    saved={}
    for j in pose0['joints']:
        obj=bpy.data.objects.get(j['name'])
        if not obj or obj.name.startswith('Hatch_'):continue
        saved[obj.name]=(obj.location.copy(),obj.rotation_mode,obj.rotation_quaternion.copy(),obj.rotation_euler.copy())
        x,y,z=j['position'];obj.location=(x,-z,y);q=j['quaternion']
        obj.rotation_mode='QUATERNION';obj.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
    bpy.context.view_layer.update()

    def curve(ps,x):
        ps=sorted(ps,key=lambda p:p[0])
        if x<=ps[0][0]:return Vector(ps[0])
        if x>=ps[-1][0]:return Vector(ps[-1])
        for a,b in zip(ps,ps[1:]):
            if a[0]<=x<=b[0]:return Vector(a).lerp(Vector(b),(x-a[0])/(b[0]-a[0]))

    def geometry(obj):
        obj.data.calc_loop_triangles();m=inverse@obj.matrix_world
        return [m@v.co for v in obj.data.vertices],[tuple(t.vertices) for t in obj.data.loop_triangles]

    def tree(obj):
        vs,ts=geometry(obj)
        return BVHTree.FromPolygons(vs,ts,all_triangles=True,epsilon=.000001)

    report={'revision':'0.8.1','scope':'four long-armor rear edges only','parts':{}}
    for bank,config in ref.items():
        shroud_names=['odin.005','odin.006','odin.007','odin.008'] if bank=='Dorsal' else ['odin.013','odin.014','odin.015','odin.016']
        shrouds=[tree(bpy.data.objects[n]) for n in shroud_names]
        for side,sign in [('Port',-1),('Starboard',1)]:
            parent=bpy.data.objects[f'Hatch_{bank}_{side}'];obj=bpy.data.objects[parent.name+'_FittedSkin']
            vertices,triangles=geometry(obj);m=inverse@obj.matrix_world;mi=m.inverted()
            rear=config[side]['rear'];end_radius=abs(config[side]['upper'][-1][0]-config['center'])
            # Correct only triangles that touch the closed source shroud.
            # The thin edge's upper/lower vertices fit independently, keeping
            # the mating bevel close instead of moving the whole seam away.
            initial=tree(obj)
            touching={index for shroud in shrouds for ai,_ in initial.overlap(shroud) for index in triangles[ai]}
            groups={i:[i] for i in range(len(vertices))}
            deltas={};edge_distances=[]
            for indices in groups.values():
                if not any(i in touching for i in indices):continue
                point=vertices[indices[0]]
                if abs(point.x-config['center'])>=end_radius-.06:continue
                back=curve(rear,point.x);distance=point.y-back.y
                if distance<-.15 or distance>1.5:continue
                hits=[]
                for index in indices:
                    p=vertices[index]
                    hit,normal,_,_=min((shroud.find_nearest(p) for shroud in shrouds),key=lambda result:result[3])
                    hits.append(hit.y+.042/max(.85,abs(normal.y)))
                if not hits:continue
                target=max(hits)
                if abs(target-point.y)>1.:continue
                # Move only forward out of the actual contact. Unaffected rear
                # samples and every nose/outer-lip vertex keep their position.
                delta=target-point.y
                delta=max(0.,delta)
                if abs(delta)<.000001:continue
                for index in indices:
                    p=vertices[index].copy();p.y+=delta;obj.data.vertices[index].co=mi@p
                    deltas[index]=delta
            obj.data.update();bpy.context.view_layer.update()
            obj.data.set_sharp_from_angle(angle=math.radians(30))
            after=tree(obj);intersections={name:len(after.overlap(shroud)) for name,shroud in zip(shroud_names,shrouds)}
            new_vertices,_=geometry(obj)
            for index in deltas:
                p=new_vertices[index];back=curve(rear,p.x)
                if vertices[index].y-back.y<=.06:
                    edge_distances.append(min(t.find_nearest(p)[3] for t in shrouds))
            report['parts'][obj.name]={'verticesMoved':len(deltas),'maxForwardChange':max(deltas.values(),default=0),
                'maxRearwardChange':min(deltas.values(),default=0),'closedShroudIntersections':intersections,
                'movedRearEdgeSurfaceDistanceRange':[min(edge_distances,default=0),max(edge_distances,default=0)]}
            report['parts'][obj.name]['changedPoints']=[{'before':list(vertices[i]),'after':list(new_vertices[i]),'distance':min(t.find_nearest(new_vertices[i])[3] for t in shrouds)} for i in deltas]
            parent['rearSeamReference']='Actual closed web-pose shroud forward surfaces; 0.042 clearance'
            print('MAIN_REAR_FIT',obj.name,{k:v for k,v in report['parts'][obj.name].items() if k!='changedPoints'},flush=True)
    for name,(location,mode,quat,euler) in saved.items():
        obj=bpy.data.objects[name];obj.location=location;obj.rotation_mode=mode
        if mode=='QUATERNION':obj.rotation_quaternion=quat
        else:obj.rotation_euler=euler
    bpy.context.view_layer.update()
    out=root/'work/v081-review/main-rear-seams.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf8')
    assert all(not any(part['closedShroudIntersections'].values()) for part in report['parts'].values()),report
    return report


fit_main_rear_seams_v081()
