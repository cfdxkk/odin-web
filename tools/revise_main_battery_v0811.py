"""Fit the visible corner in side/top projection and give rims real thickness.

The accepted outer armor planes and bore rig are retained. Only a new editable
copy is saved; no animation is baked into it.
"""
import bpy, bmesh, json, math, hashlib
import numpy as np
from pathlib import Path
from collections import Counter
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/blender/odin_articulated_v0.8.10.blend'
OUT = ROOT / 'assets/blender/odin_articulated_v0.8.11.blend'
assert Path(bpy.data.filepath).resolve() == BASE.resolve()
asset = bpy.data.objects['Odin_Asset']
inv = asset.matrix_world.inverted()
paint = bpy.data.materials['Odin_Paint_Light']
red = bpy.data.materials['Odin_Turret_Interior_DeepRed']
THICKNESS = .18
report = {'version': '0.8.11', 'rimThickness': THICKNESS, 'parts': {}, 'junctions': {}}
PLANES = [(1.2385092997145244,-.06458586233633538,61.41979689177092),(-1.2393497078569466,-.06942219204372839,62.20786261030588),(0,-.0654535522251,59.1309201278)]

def outline(ps,fs):
    ec=Counter(tuple(sorted((a,b))) for f in fs for a,b in zip(f,f[1:]+f[:1]));adj={}
    for (a,b),n in ec.items():
        if n==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    assert all(len(v)==2 for v in adj.values())
    ids=[next(iter(adj))];prev=None
    while True:
        nxt=next(i for i in adj[ids[-1]] if i!=prev)
        if nxt==ids[0]:break
        prev=ids[-1];ids.append(nxt)
    return [ps[i].copy() for i in ids]

def inside(poly,x,y):
    return sum((a.y>y)!=(b.y>y) and x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x for a,b in zip(poly,poly[1:]+poly[:1]))%2==1

def clean_skin(ps,fs):
    poly=outline(ps,fs);verts=[Vector((p.x,p.y))for p in poly];edges=[(i,(i+1)%len(verts))for i in range(len(verts))]
    # Constrain both roof ridges before triangulating. Every triangle then
    # belongs to a single original flat plane, including the serrated rim.
    for a,b,c in PLANES[:2]:
        inds=[]
        for y in [min(p.y for p in poly)-1,max(p.y for p in poly)+1]:
            x=((PLANES[2][1]-b)*y+PLANES[2][2]-c)/a;inds.append(len(verts));verts.append(Vector((x,y)))
        edges.append(tuple(inds))
    vs,_,faces,*_=delaunay_2d_cdt(verts,edges,[],0,1e-5)
    faces=[list(f) for f in faces if inside(poly,sum(vs[i].x for i in f)/len(f),sum(vs[i].y for i in f)/len(f))]
    used=sorted({i for f in faces for i in f});mapping={i:k for k,i in enumerate(used)}
    top=[Vector((vs[i].x,vs[i].y,min(a*vs[i].x+b*vs[i].y+c for a,b,c in PLANES)))for i in used]
    return top,[[mapping[i]for i in f]for f in faces]

def points(obj):
    return [(inv @ obj.matrix_world) @ v.co for v in obj.data.vertices]

def outer(obj):
    ps = points(obj); count = len(ps) // 2
    faces = [list(f.vertices) for f in obj.data.polygons if max(f.vertices) < count]
    used = sorted({i for f in faces for i in f}); remap = {i: k for k, i in enumerate(used)}
    return [ps[i] for i in used], [[remap[i] for i in f] for f in faces]

def solid(obj, ps, fs, thickness=THICKNESS):
    """Parallel planar inner surfaces, bounded miters and full-thickness rims."""
    normals = [[] for _ in ps]; edges = {}; valid = []
    for face in fs:
        n = sum(((ps[face[i]]-ps[face[0]]).cross(ps[face[i+1]]-ps[face[0]]) for i in range(1,len(face)-1)), Vector())
        if n.length < 1e-8: continue
        n.normalize()
        if obj.name.endswith(('_FittedSkin','_Wedge')) and n.z * (-1 if 'Ventral' in obj.name else 1) < -.02:
            face=list(reversed(face));n=-n
        valid.append(face)
        for i in face:
            if not any(n.dot(other) > .9995 for other in normals[i]): normals[i].append(n)
        for a,b in zip(face,face[1:]+face[:1]): edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
    inside = []
    for vi,(p, ns) in enumerate(zip(ps,normals)):
        if not ns: inside.append(p.copy()); continue
        if obj.name.endswith(('_FittedSkin','_Wedge')):
            offset=Vector((0,0,-.25 if 'Dorsal' in obj.name else .25))
            if obj.name.endswith('_FittedSkin') and p.y<117 and abs(p.x)<9.3:
                offset=Vector((0,.40,-.081))
        else:offset = Vector(np.linalg.lstsq(np.array([list(n) for n in ns]), np.full(len(ns),-thickness), rcond=.25)[0])
        if obj.name.endswith('_GapFiller') and vi%2==0:
            n=Vector(obj.parent['planeNormal']);s=1 if 'Starboard' in obj.name else -1
            bevel=min(.34,abs(ps[vi+1].x-p.x)*.3)
            offset+=Vector((s*bevel,0,-s*bevel*n.x/n.z))
        assert offset.length < thickness * 4, (obj.name, p, offset)
        inside.append(p + offset)
    count = len(ps)
    boundary = [entries[0] for entries in edges.values() if len(entries)==1]
    faces = valid + [[i+count for i in reversed(f)] for f in valid] + [[b,a,a+count,b+count] for a,b in boundary]
    local = (inv @ obj.matrix_world).inverted()
    mesh = bpy.data.meshes.new(obj.name + '_FullThickness')
    mesh.from_pydata([local @ p for p in ps+inside],[],faces)
    mesh.materials.append(paint); mesh.materials.append(red); mesh.update()
    for f in mesh.polygons:
        f.material_index = 1 if len(valid) <= f.index < 2*len(valid) else 0
        f.use_smooth = False
    obj.data = mesh; obj['armorThickness'] = thickness
    obj['rimConstruction'] = 'Full thickness at the visible perimeter; no knife-edge taper'
    report['parts'][obj.name] = {'outerVertices': count, 'rimThickness': thickness, 'boundaryEdges': len(boundary)}

# Reconstruct the rear leaves about the ORIGINAL hull shoulder direction.
# The former line had been shortened to a plane intersection, changing its
# slope in both side and top views. Use the measured source crease instead.
pose_data=json.loads((ROOT/'docs/review/v0.8.11/baseline-closed-pose.json').read_text(encoding='utf8'))
basis=Quaternion((1,0,0),-math.pi/2);saved={}
for j in pose_data['poses'][0]['joints']:
    if j['name'].startswith('Hatch_'):continue
    o=bpy.data.objects[j['name']];saved[o.name]=(o.location.copy(),o.rotation_mode,o.rotation_quaternion.copy(),o.rotation_euler.copy())
    x,y,z=j['position'];o.location=(x,-z,y);q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
bpy.context.view_layer.update()
shrouds=[]
for name in ['odin.005','odin.006','odin.007','odin.008']:
    o=bpy.data.objects[name];o.data.calc_loop_triangles();shrouds.append(BVHTree.FromPolygons(points(o),[tuple(t.vertices)for t in o.data.loop_triangles],all_triangles=True))
for side,sign in [('Port',-1),('Starboard',1)]:
    joint=bpy.data.objects[f'Hatch_Dorsal_Aft_{side}'];obj=bpy.data.objects[joint.name+'_GapFiller']
    old_points=points(obj);old_free=old_points[:len(old_points)//2:3]
    main=bpy.data.objects[f'Hatch_Dorsal_{side}_FittedSkin'];mp,_=outer(main)
    candidates=[p for p in mp if p.y<117 and sign*p.x>8.7];u=min(candidates,key=lambda p:p.y);toe=max(candidates,key=lambda p:sign*p.x)
    original_a=Vector((sign*14.6731,76.1789,41.1194));original_b=Vector((sign*14.3653,81.8197,40.8214));direction=original_b-original_a;direction/=direction.y
    y0=75.735927;y1=toe.y-.035
    # The user-marked red leaf owns the whole diagonal U--T, including the
    # former triangular return. Its single plane also contains the hull axis.
    normal=(toe-u).cross(direction).normalized()
    if normal.z<0:normal=-normal
    shoulder=Vector((-sign*.224,.039,.974)).normalized()
    shoulder-=direction.normalized()*shoulder.dot(direction.normalized());shoulder.normalize()
    matrix=np.array([[normal.x,normal.z],[shoulder.x,shoulder.z]])
    rhs=np.array([normal.dot(u)-normal.y*y0,shoulder.dot(original_a)+.025-shoulder.y*y0])
    x,z=np.linalg.solve(matrix,rhs);a=Vector((x,y0,z));b=a+direction*(y1-y0)
    def on_plane(x,y):return Vector((x,y,a.z-(normal.x*(x-a.x)+normal.y*(y-a.y))/normal.z))
    vertices=[];free=[];edge=[];rows=241
    for row in range(rows):
        y=y0+(y1-y0)*row/(rows-1);hinge=a+direction*(y-y0)
        z=float(np.interp(y,[p.y for p in old_free],[p.z for p in old_free]))
        x=(normal.dot(u)-normal.y*y-normal.z*z)/normal.x
        p=on_plane(x,y)
        if y<u.y:
            along=Vector((sign,0,-sign*normal.x/normal.z)).normalized();origin=p+along*.7;hits=[]
            for shroud in shrouds:
                hit,_,_,distance=shroud.ray_cast(origin,-along,1.1)
                if hit is not None:hits.append((hit-p).dot(along))
            if hits and max(hits)>-.08:p+=along*(max(hits)+.08)
        if y>=u.y:
            x=u.x+(toe.x-u.x)*(y-u.y)/(toe.y-u.y)+sign*.075
            p=on_plane(x,y)
        if sign*p.x>sign*hinge.x-.005:p=on_plane(hinge.x-sign*.005,y)
        free.append(p);edge.append(hinge);vertices.extend([p,hinge])
    fs=[]
    for i in range(rows-1):
        f=[2*i,2*i+1,2*i+3,2*i+2]
        if (vertices[f[1]]-vertices[f[0]]).cross(vertices[f[2]]-vertices[f[0]]).dot(normal)<0:f.reverse()
        fs.append(f)
    axle_a=a;axle_b=b
    world=obj.matrix_world.copy();joint.location=axle_a;bpy.context.view_layer.update();obj.matrix_world=world;bpy.context.view_layer.update()
    joint['hingeAxis']=list(direction.normalized());joint['hingeEdge']=[list(axle_a),list(axle_b)];joint['hingeSurfaceEdge']=[list(axle_a),list(axle_b)];joint['planeNormal']=list(normal)
    joint['closedOutlineXY']=[[p.x,p.y]for p in free+list(reversed(edge))]
    joint['sourceReference']='Straight source-hull crease: measured vertices 128056/128058 and 144152/144154, not a trimmed cover slope'
    solid(obj,vertices,fs)
    report.setdefault('hullAlignedHinges',{})[side]={'sourceLine':[list(original_a),list(original_b)],'hinge':[list(axle_a),list(axle_b)],'planeNormal':list(normal),'parallelError':direction.normalized().cross((original_b-original_a).normalized()).length}
for name,(loc,mode,q,e) in saved.items():
    o=bpy.data.objects[name];o.location=loc;o.rotation_mode=mode;o.rotation_quaternion=q;o.rotation_euler=e
bpy.context.view_layer.update()

for bank in ['Dorsal']:
    for role,suffix in [('Port','FittedSkin'),('Starboard','FittedSkin'),('Nose','Wedge'),('Aft_Port','GapFiller'),('Aft_Starboard','GapFiller')]:
        obj = bpy.data.objects[f'Hatch_{bank}_{role}_{suffix}']; ps,fs = outer(obj)
        if suffix in ['FittedSkin','Wedge']:ps,fs=clean_skin(ps,fs)
        if bank=='Dorsal' and role in ['Port','Starboard']:
            sign = -1 if role=='Port' else 1
            candidates = [i for i,p in enumerate(ps) if p.y<117 and sign*p.x>8.7]
            ui = min(candidates,key=lambda i:ps[i].y); ti = max(candidates,key=lambda i:sign*ps[i].x)
            u,t = ps[ui],ps[ti]
            old=bpy.data.objects.get(obj.parent.name+'_RearReturn')
            if old:bpy.data.objects.remove(old,do_unlink=True)
            obj.parent['clearanceLift']=[0,0,.42]
            obj.parent['closedOutlineXY']=[[p.x,p.y]for p in outline(ps,fs)]
            report['junctions'][role]={'mainRearDiagonal':[list(u),list(t)],'triangularRegionParent':f'Hatch_Dorsal_Aft_{role}'}
        solid(obj,ps,fs)

# Refit the actual fixed hull, rather than overlaying another sheet on it.
hull=bpy.data.objects['holo.001'];hm=inv@hull.matrix_world;hi=hm.inverted()
with bpy.data.libraries.load(str(ROOT/'assets/blender/odin_articulated_v0.8.6.blend'),link=False) as (src,dst):
    assert hull.data.name in src.meshes,hull.data.name
    dst.meshes=[hull.data.name]
reference_mesh=dst.meshes[0];reference_mesh.calc_loop_triangles()
original_hull=BVHTree.FromPolygons([hm@v.co for v in reference_mesh.vertices],[tuple(t.vertices)for t in reference_mesh.loop_triangles],all_triangles=True)
def hull_z(x,y):
    hit,p,_,_=hull.ray_cast(hi@Vector((x,y,65)),hi.to_3x3()@Vector((0,0,-1)))
    assert hit,(x,y)
    return (hm@p).z
for side,sign in [('Port',-1),('Starboard',1)]:
    skin=bpy.data.objects[f'Hatch_Dorsal_{side}_FittedSkin'];sp=points(skin);n=len(sp)//2
    toe=Vector(report['junctions'][side]['mainRearDiagonal'][1])
    nextpoint=min((p for p in sp[:n] if p.y>130 and sign*p.x>10.9),key=lambda p:p.y)
    faces=[f for f in skin.data.polygons if max(f.vertices)<n]
    sf=max((f for f in faces if f.normal.z>.1 and f.normal.x*sign>.3),key=lambda f:f.area)
    transform=inv@skin.matrix_world;normal=(transform.to_3x3().inverted().transposed()@sf.normal).normalized();anchor=sp[sf.vertices[0]]
    def cover_z(x,y):return anchor.z-(normal.x*(x-anchor.x)+normal.y*(y-anchor.y))/normal.z
    axis_a,axis_b=map(Vector,report['hullAlignedHinges'][side]['hinge']);changed=[]
    for v in hull.data.vertices:
        p=hm@v.co
        if not(74<p.y<124 and 10<sign*p.x<16 and 34<p.z<44):continue
        old=p.copy();original,_,_,_=original_hull.ray_cast(Vector((p.x,p.y,65)),Vector((0,0,-1)))
        if original is None:continue
        axis=axis_a.lerp(axis_b,(p.y-axis_a.y)/(axis_b.y-axis_a.y));radius=sign*(p.x-axis.x)
        if p.y<toe.y-.04 and -.25<radius<1.5 and 0<original.z-p.z<3:
            p.z=original.z
        if toe.y+.035<p.y<123:
            x=toe.x+(nextpoint.x-toe.x)*(p.y-toe.y)/(nextpoint.y-toe.y);radius=sign*(p.x-x)
            if -.13<radius<1.5:
                target=cover_z(p.x,p.y)-.285;weight=max(0,min(1,1-max(0,radius)/1.5))
                target=original.z+max(0,target-original.z)*weight
                if 0<target-p.z<3:p.z=target
        if (p-old).length>1e-6:v.co=hi@p;changed.append((p-old).length)
    obj=bpy.data.objects.get(f'MainBay_Dorsal_{side}_FixedReceiver')
    if obj:bpy.data.objects.remove(obj,do_unlink=True)
    report['junctions'][side]['fixedReceiver']={'object':hull.name,'verticesRefitted':len(changed),'maxAdjustment':max(changed,default=0)}
hull.data.update();bpy.data.meshes.remove(reference_mesh)

# A continuous, locally recessed hull receiver follows the underside all the
# way to the real rim. The former inset-only relief stopped short of the rim.
polys=[]
for role,suffix in [('Port','FittedSkin'),('Starboard','FittedSkin'),('Nose','Wedge')]:
    ps,fs=outer(bpy.data.objects[f'Hatch_Dorsal_{role}_{suffix}']);polys.append(outline(ps,fs))
ids=[];samples=[]
for v in hull.data.vertices:
    p=hm@v.co
    if 112<p.y<172 and abs(p.x)<15.5 and 32<p.z<53:ids.append(v.index);samples.append(p)
arr=np.array(samples);x=arr[:,0];y=arr[:,1];dist=np.full(len(arr),1e9);isin=np.zeros(len(arr),dtype=bool)
for poly in polys:
    ip=np.zeros(len(arr),dtype=bool)
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if abs(a.y-b.y)>1e-9:ip^=((a.y>y)!=(b.y>y))&(x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x)
        dx,dy=b.x-a.x,b.y-a.y;t=np.clip(((x-a.x)*dx+(y-a.y)*dy)/max(dx*dx+dy*dy,1e-20),0,1)
        dist=np.minimum(dist,np.hypot(x-a.x-dx*t,y-a.y-dy*t))
    isin|=ip
height=np.minimum.reduce([a*x+b*y+c for a,b,c in PLANES])-.42
weight=np.where(isin,1,np.clip(1-dist/.65,0,1));count=0
for k in np.flatnonzero((weight>0)&(arr[:,2]>height)&(arr[:,2]<height+2.8)):
    p=Vector(arr[k]);p.z+=(height[k]-p.z)*weight[k];hull.data.vertices[ids[k]].co=hi@p;count+=1
report['fullRimReceiverVertices']=count
hull.data.update()

for side,sign in [('Port',-1),('Starboard',1)]:
    j=bpy.data.objects[f'Hatch_Dorsal_Aft_{side}'];a,b=map(Vector,j['hingeEdge']);n=Vector(j['planeNormal']);axis=Vector(j['hingeAxis'])
    opened=Quaternion(axis,math.radians(j['openingAngleDegrees']))@n
    bm=bmesh.new();bm.from_mesh(hull.data)
    for offset in [-.30,0,.03]:
        p=a+Vector((sign*offset,0,0));cutnormal=Vector((1,-axis.x/axis.y,0));selected=[]
        for f in bm.faces:
            vs=[hm@v.co for v in f.verts]
            if max(v.z for v in vs)<35 or min(v.y for v in vs)>b.y+1.2 or max(v.y for v in vs)<a.y-1.2:continue
            if max(sign*v.x for v in vs)<8 or min(sign*v.x for v in vs)>18:continue
            ds=[cutnormal.dot(v-p)for v in vs]
            if min(ds)<0<max(ds):selected.append(f)
        geom=set(selected)
        for f in selected:geom.update(f.edges);geom.update(f.verts)
        bmesh.ops.bisect_plane(bm,geom=list(geom),dist=1e-6,plane_co=hi@p,plane_no=hm.to_3x3().transposed()@cutnormal,clear_inner=False,clear_outer=False)
    bm.to_mesh(hull.data);bm.free();hull.data.update()
    changed=0
    for v in hull.data.vertices:
        p=hm@v.co
        if not a.y-1.2<p.y<b.y+1.2 or not 8<sign*p.x<18 or not 35<p.z<45:continue
        line=a+(p.y-a.y)/axis.y*axis;radius=sign*(p.x-line.x)
        if not -1.7<radius<2:continue
        closedz=a.z-(n.x*(p.x-a.x)+n.y*(p.y-a.y)+THICKNESS+.055)/n.z
        openz=a.z-(opened.x*(p.x-a.x)+opened.y*(p.y-a.y))/opened.z-.07
        height=min(closedz,openz) if radius<.02 else openz
        weight=min(1,max(0,(2-radius)/.5),max(0,(radius+1.7)/.5))
        if height<p.z<height+3:
            p.z+=(height-p.z)*weight;v.co=hi@p;changed+=1
    report['hullAlignedHinges'][side]['receiverVertices']=changed
hull.data.update()

# The stationary receiving lip closes the small fore-corner window from both
# side and top. It underlaps the main plate by only 0.045, not the former 0.60.
for side,sign in [('Port',-1),('Starboard',1)]:
    skin=bpy.data.objects[f'Hatch_Dorsal_{side}_FittedSkin'];sp,fs=outer(skin)
    toe=Vector(report['junctions'][side]['mainRearDiagonal'][1])
    nextpoint=min((p for p in sp if p.y>130 and sign*p.x>10.9),key=lambda p:p.y)
    ps=[];faces=[]
    for row in range(25):
        y=toe.y+.055+(122-toe.y-.055)*row/24
        x=toe.x+(nextpoint.x-toe.x)*(y-toe.y)/(nextpoint.y-toe.y)-sign*.045
        z=min(a*x+b*y+c for a,b,c in PLANES)-.295
        bottom=min(hull_z(x,y)-.05,z-.06)
        ps.extend([Vector((x,y,bottom)),Vector((x,y,z))])
    for i in range(24):
        f=[2*i,2*i+2,2*i+3,2*i+1]
        if (ps[f[1]]-ps[f[0]]).cross(ps[f[2]]-ps[f[0]]).x*sign<0:f.reverse()
        faces.append(f)
    name=f'MainBay_Dorsal_{side}_FixedReceiver';o=bpy.data.objects.new(name,bpy.data.meshes.new(name));bpy.context.scene.collection.objects.link(o);o.parent=asset;bpy.context.view_layer.update()
    solid(o,ps,faces,.06);o['fixedHull']='holo.001';o['junctionRole']='fixed-underlapping-corner-seal'

# Cut real receiving rebates below the mating rims. The outer armor remains
# full thickness; it is no longer tapered into a nearly invisible knife edge.
for j in pose_data['poses'][0]['joints']:
    if j['name'].startswith('Hatch_'):continue
    o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
bpy.context.view_layer.update()
def tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(t.vertices)for t in obj.data.loop_triangles],all_triangles=True)
for role,suffix in [('Port','FittedSkin'),('Starboard','FittedSkin'),('Nose','Wedge'),('Aft_Port','GapFiller'),('Aft_Starboard','GapFiller')]:
    if not role.startswith('Aft_'):continue
    plate=bpy.data.objects[f'Hatch_Dorsal_{role}_{suffix}'];cutter=plate.copy();cutter.data=plate.data.copy();bpy.context.scene.collection.objects.link(cutter)
    cutter.name='TemporaryReceivingRebate'
    bm=bmesh.new();j=plate.parent;axle=Vector(j['hingeEdge'][0]);axis=Vector(j['hingeAxis']);local=(inv@cutter.matrix_world).inverted();sign=1 if j['openingAngleDegrees']>0 else -1
    for degree in [0,10,20,30,40]:
        turn=Quaternion(axis,math.radians(sign*degree))
        for p in points(plate):bm.verts.new(local@(axle+turn@(p-axle)))
    bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
    for vertex in list(bm.verts):
        if not vertex.link_faces:bm.verts.remove(vertex)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    for v in bm.verts:v.co+=v.normal*.10
    bm.to_mesh(cutter.data);bm.free();cutter.data.update();bpy.context.view_layer.update();ct=tree(cutter)
    for name in ['odin.005','odin.006','odin.008']:
        target=bpy.data.objects[name]
        if not tree(target).overlap(ct):continue
        before=len(target.data.polygons);bpy.context.view_layer.objects.active=target
        mod=target.modifiers.new('Fitted armor receiving rebate','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;mod.material_mode='TRANSFER';mod.use_hole_tolerant=True
        bpy.ops.object.modifier_apply(modifier=mod.name);target.data.update()
        report.setdefault('receivingRebates',[]).append({'armor':plate.name,'receiver':name,'facesBefore':before,'facesAfter':len(target.data.polygons)})
        print('REBATE',plate.name,name,before,len(target.data.polygons),flush=True)
    bpy.data.objects.remove(cutter,do_unlink=True)
for name,(loc,mode,q,e) in saved.items():
    o=bpy.data.objects[name];o.location=loc;o.rotation_mode=mode;o.rotation_quaternion=q;o.rotation_euler=e
bpy.context.view_layer.update()

asset['version']='0.8.11';bpy.context.scene.name='ODIN v0.8.11 - visible sealed armor edges'
assert not bpy.data.actions
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
report['blendSha256']=hashlib.sha256(OUT.read_bytes()).hexdigest()
path=ROOT/'work/v0811-review/geometry-build.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf8')
print('SAVED',OUT,flush=True)
