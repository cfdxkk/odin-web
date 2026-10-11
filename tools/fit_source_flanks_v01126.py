"""Fit the existing source flank armor and restore the original outer rail belt.

Run on v0.11.25. The six original grate assemblies, cap strokes, carriage and
source barrel curves are retained. Only their closed exterior contours and
maximum leaf sweeps change; the original Blender source is read-only.
"""
import bpy, bmesh, hashlib, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector, Euler
from mathutils.kdtree import KDTree

root = Path(__file__).resolve().parents[1]
scene = bpy.context.scene
asset = bpy.data.objects['Odin_Asset']
assert asset['version'] == '0.11.25'
inv = asset.matrix_world.inverted()
frames = json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text(encoding='utf8'))
review = root/'docs/review/v0.11.26'
review.mkdir(parents=True, exist_ok=True)
source_path = root.parent/'Odin 建模/odin.blend'
with source_path.open('rb') as f:
    source_hash = hashlib.file_digest(f, 'sha256').hexdigest()
light = bpy.data.materials['Odin_Paint_Light']
red = bpy.data.materials['Odin_Turret_Interior_DeepRed']
changed = set()

def points(o):
    return np.array([(inv @ o.matrix_world) @ v.co for v in o.data.vertices])

def digest(o):
    h = hashlib.sha256()
    co = np.empty(len(o.data.vertices)*3, dtype=np.float32)
    o.data.vertices.foreach_get('co', co)
    h.update(co.tobytes())
    for f in o.data.polygons:
        h.update(np.asarray(f.vertices[:], dtype=np.int32).tobytes())
        h.update(o.data.materials[f.material_index].name.encode())
    return h.hexdigest()

before = {o.name:digest(o) for o in scene.objects if o.type == 'MESH'}
joint_before = {o.name:np.array(o.matrix_local).copy() for o in scene.objects if o.get('staticJoint')}
def plain(value):
    if hasattr(value, 'to_dict'):return {k:plain(v) for k,v in value.to_dict().items()}
    if hasattr(value, 'to_list'):return [plain(v) for v in value.to_list()]
    if isinstance(value, dict):return {k:plain(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):return [plain(v) for v in value]
    return value
barrel_before = {o.name:plain(dict(o.items())) for o in scene.objects if o.name in frames and o.name.startswith('SideBattery_')}
report = {'version':'0.11.26', 'sourceSha256':source_hash, 'stations':{}, 'restoredHull':[], 'sourceElevationRails':[]}

def ease(a, b, d):
    t = max(0., min(1., (d-a)/(b-a)))
    return t*t*(3-2*t)

def material_slot(o, mat):
    if mat.name not in o.data.materials:
        o.data.materials.append(mat)
    return o.data.materials.find(mat.name)

def extend_top(o, q, edge, shoulder, seam, to_data):
    """Extend a source exterior edge into a solid flat crown, in the same mesh."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    gray = material_slot(o, light)
    inner = material_slot(o, red)
    for v, p in zip(bm.verts, q):
        v.co = Vector(to_data(p))
    a, b = edge
    old = [bm.verts[a], bm.verts[b]]
    vertices = old.copy()
    for p in list(shoulder)+list(seam):
        vertices.append(bm.verts.new(Vector(to_data(p))))
    # Rows: original edge (0/1), sloping shoulder (2/3), flat seam (4/5).
    roofs = [(0,1,3,2), (2,3,5,4)]
    for indices in roofs:
        f = bm.faces.new([vertices[i] for i in indices])
        f.material_index = gray
        f.smooth = False
    underside = []
    for p in [q[a], q[b], *shoulder, *seam]:
        p = np.array(p).copy()
        p[2] -= .16
        underside.append(bm.verts.new(Vector(to_data(p))))
    for indices in roofs:
        f = bm.faces.new([underside[i] for i in reversed(indices)])
        f.material_index = inner
    for indices in [(0,2,4), (1,5,3)]:
        for i,j in zip(indices,indices[1:]):
            f = bm.faces.new([vertices[i], vertices[j], underside[j], underside[i]])
            f.material_index = gray
    f = bm.faces.new([vertices[4], vertices[5], underside[5], underside[4]])
    f.material_index = gray
    # The original edge remains connected to the new roof; its inner return
    # is below the existing rolled rail and cannot become a floating exterior.
    f = bm.faces.new([old[1], old[0], underside[0], underside[1]])
    f.material_index = inner
    uv = bm.loops.layers.uv.active
    if uv:
        for f in bm.faces:
            if any(v.index >= len(q) or v in vertices[2:]+underside for v in f.verts):
                for loop in f.loops:
                    p = np.array(loop.vert.co)
                    loop[uv].uv = (float(p[0])*.025, float(p[1])*.025)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    o['fittedFlatCrown'] = True
    o['crownThickness'] = .16
    o['sourceGratesRetained'] = True
    changed.add(o.name)

def top_edge(o, q, side):
    outer = [f for f in o.data.polygons if o.data.materials[f.material_index] == light]
    candidates = []
    for f in sorted(outer, key=lambda f:f.area, reverse=True)[:8]:
        for a,b in zip(f.vertices, list(f.vertices[1:])+[f.vertices[0]]):
            if abs(q[a,1]-q[b,1]) > 6 and max(abs(q[a,0]),abs(q[b,0])) < 1.6:
                candidates.append((abs(q[a,0])+abs(q[b,0]),a,b))
    assert candidates, o.name
    _, a,b = min(candidates)
    return tuple(sorted([a,b], key=lambda i:q[i,1]))

for number in (2,4):
    for side in ('Starboard','Port'):
        name = f'SideBattery_{number}_{side}'
        C = np.array(frames[name]['frameOrigin'])
        Q = np.array(frames[name]['frameAxes'])
        carriage = bpy.data.objects[name+'_SourceCarriage']
        offset = np.array(carriage['closedOffsetModel'])
        rows = []
        reference = .20 if number == 2 else .18
        for physical_side, sign in [('Port',-1),('Starboard',1)]:
            front = bpy.data.objects[f'{name}_Shutter_{physical_side}_02']
            travel = abs(float(front['closedAngleDegrees'])) * ease(float(front['openStart']),float(front['openEnd']),reference)
            for i in range(3):
                j = bpy.data.objects[f'{name}_Shutter_{physical_side}_{i:02}']
                o = j.children[0]
                H = np.array((inv @ j.matrix_world).translation)
                R = np.array(Quaternion(Vector(j['hingeAxisModel']), math.radians(j['closedAngleDegrees'])).to_matrix())
                move = offset if i == 0 else np.zeros(3)
                q = (H+(points(o)-H)@R.T+move-C)@Q
                old_count = len(q)
                edge = top_edge(o,q,sign)
                target_range = [(-17.4,-8.205),(-8.185,.315),(.335,9.415)][i]
                gray_vertices = set()
                for f in o.data.polygons:
                    p = q[list(f.vertices)]
                    n = np.cross(p[1]-p[0],p[2]-p[0])
                    if o.data.materials[f.material_index] == light and f.area>6 and abs(n[2])>.2*np.linalg.norm(n):
                        gray_vertices.update(f.vertices)
                # Source exterior ends are raked differently in each bank.
                # Fit both complete exterior end edges, not the bounds of
                # the disconnected grate bars and rolled edge details.
                lower=[]
                for f in o.data.polygons:
                    if o.data.materials[f.material_index]!=light or f.area<6:continue
                    for a,b in zip(f.vertices,list(f.vertices[1:])+[f.vertices[0]]):
                        if abs(q[a,1]-q[b,1])>5 and min(abs(q[a,0]),abs(q[b,0]))>2.:
                            lower.append((abs(q[a,1]-q[b,1]),a,b))
                assert lower,o.name
                _,a,b=max(lower)
                bottom=tuple(sorted([a,b],key=lambda k:q[k,1]))
                end_lines=[]
                for upper,lower_vertex in zip(edge,bottom):
                    a,b=np.linalg.solve(np.array([[abs(q[upper,0]),1],[abs(q[lower_vertex,0]),1]]),q[[upper,lower_vertex],1])
                    end_lines.append((a,b))
                starts=end_lines[0][0]*abs(q[:,0])+end_lines[0][1]
                ends=end_lines[1][0]*abs(q[:,0])+end_lines[1][1]
                fitted_b=target_range[0]+(q[:,1]-starts)/(ends-starts)*(target_range[1]-target_range[0])
                for v in gray_vertices:
                    q[v,1]=fitted_b[v]
                    if abs(q[v,0])>2.:q[v,0]=sign*2.88
                    q[v,2] = 6.326-1.58*abs(q[v,0])-.007*q[v,1]
                shoulder = [np.array([sign*.45,q[k,1],5.615-.007*q[k,1]]) for k in edge]
                seam = [np.array([sign*.02,p[1],p[2]]) for p in shoulder]
                local_inverse = np.array((inv @ o.matrix_world).inverted())
                def to_data(p):
                    closed_model = C+Q@p
                    authored = H+(closed_model-H-move)@R
                    return (local_inverse @ np.r_[authored,1])[:3]
                extend_top(o,q,edge,shoulder,seam,to_data)
                j['openingTravelDegrees'] = travel
                j['limitedSourceOpening'] = True
                j['openingLimitReferenceProgress'] = reference
                j['openingLimitReferenceJoint'] = front.name
                j['limitedOpenAngleDegrees'] = float(j['closedAngleDegrees'])-math.copysign(travel,float(j['closedAngleDegrees']))
                j['closedOuterPlaneLocal'] = [-1.58,-.007,6.326]
                j['crownHalfWidth'] = .45
                j['centerSeamHalfWidth'] = .02
                j['lowerEdgeHalfWidth'] = 2.88
                j['closedBankRange'] = list(target_range)
                rows.append({'name':j.name,'originalVertices':old_count,'vertices':len(o.data.vertices),'sourceArmorFaces':int(j['sourceArmorFaces']), 'faces':len(o.data.polygons),'referenceProgress':reference,'openingTravelDegrees':travel,'openAngleDegrees':float(j['limitedOpenAngleDegrees']),'closedRange':list(target_range),'crownEdgeClosed': [p.tolist() for p in seam]})
        cap = bpy.data.objects[name+'_FrontCap']
        o = cap.children[0]
        cap_offset = np.array(cap['slideVector'])
        cq = (points(o)+cap_offset-C)@Q
        edges = [top_edge(o,cq,s) for s in (-1,1)]
        # top_edge chooses the closest gray upper edge; filter by side here.
        edges = []
        for sign in (-1,1):
            candidates=[]
            for f in o.data.polygons:
                if o.data.materials[f.material_index]!=light:continue
                for a,b in zip(f.vertices,list(f.vertices[1:])+[f.vertices[0]]):
                    if cq[a,0]*sign>0 and cq[b,0]*sign>0 and abs(cq[a,1]-cq[b,1])>10 and max(abs(cq[a,0]),abs(cq[b,0]))<1.3:
                        candidates.append((abs(cq[a,0])+abs(cq[b,0]),a,b))
            _,a,b=min(candidates)
            edges.append(tuple(sorted([a,b],key=lambda k:cq[k,1])))
        old_cap_vertices=len(cq)
        cap_inverse=np.array((inv @ o.matrix_world).inverted())
        def cap_to_data(p):
            return (cap_inverse @ np.r_[C+Q@p-cap_offset,1])[:3]
        cap_crowns=[]
        for sign,edge in zip((-1,1),edges):
            if len(o.data.vertices)!=len(cq):
                cq=(points(o)+cap_offset-C)@Q
            shoulder=[]
            for k in edge:
                p=cq[k].copy()
                if p[1]<15:
                    p[0]=sign*.45;p[2]=5.615-.007*p[1]
                else:
                    p[0]=sign*.344;p[2]=5.030
                shoulder.append(p)
            seam=[np.array([sign*.02,p[1],p[2]])for p in shoulder]
            extend_top(o,cq,edge,shoulder,seam,cap_to_data)
            cap_crowns.append([p.tolist()for p in seam])
        cap['fittedFlatCrown']=True;cap['centerSeamHalfWidth']=.02
        report['stations'][name]={'leaves':rows,'originalCapVertices':old_cap_vertices,'capVertices':len(o.data.vertices),'capCrownClosed':cap_crowns,'openingLimitReferenceProgress':reference,'barrelAndCarriageUnchanged':True}

# The outer belt directly below the side rail is four source faces per side.
# These stay on Odin_Asset; the moving covers never own them.
with bpy.data.libraries.load(str(source_path), link=False) as (src,dst):
    dst.objects=['holo.001']
source=dst.objects[0]
scene.collection.objects.link(source)
bpy.context.view_layer.update()
sp=np.array([source.matrix_world@v.co for v in source.data.vertices])
for side, ids in [('Starboard',[182071,221180,232976,247874]),('Port',[175461,223163,231072,251065])]:
    cp=source.copy();cp.data=source.data.copy();cp.animation_data_clear();cp.modifiers.clear()
    scene.collection.objects.link(cp);cp.name=f'Flank_2_{side}_OriginalOuterRailBelt'
    for v,p in zip(cp.data.vertices,sp):v.co=Vector(p)
    bm=bmesh.new();bm.from_mesh(cp.data);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in ids],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bm.to_mesh(cp.data);bm.free()
    cp.parent=asset;cp.matrix_parent_inverse=Matrix.Identity(4);cp.matrix_local=Matrix.Identity(4)
    for i in range(len(cp.data.materials)):cp.data.materials[i]=light
    cp['restoredFrom']='odin.blend/holo.001';cp['sourceFaceIds']=ids;cp['fixedOuterHull']=True
    changed.add(cp.name)
    report['restoredHull'].append({'name':cp.name,'sourceFaceIds':ids,'faces':len(cp.data.polygons),'vertices':len(cp.data.vertices),'static':True})

# Planarize only the outward shell vertices of the source cheek islands.
# Their inner walls, floor, bearing mounts and red reinforcements remain fixed.
parents=list(range(len(sp)))
def find(i):
    while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
    return i
for e in source.data.edges:a,b=e.vertices;parents[find(a)]=find(b)
groups={};group_faces={}
for v in source.data.vertices:groups.setdefault(find(v.index),[]).append(v.index)
for f in source.data.polygons:group_faces.setdefault(find(f.vertices[0]),[]).append(f.index)
rail_keys=set()
def face_key(p):return tuple(sorted(tuple(np.round(v,4))for v in p))
for side,gid in [('Starboard',46052),('Port',44418)]:
    name=f'SideBattery_4_{side}';gun=bpy.data.objects[name]
    ids=group_faces[gid];assert len(groups[gid])==36 and len(ids)==24
    origin=np.array(gun['sourceOriginModel']);adjusted=np.array(gun['adjustedOriginModel'])
    parent=Quaternion(gun['sourceParentRotationWXYZ'])
    start=parent@Euler(gun['sourceEulerStart'],'XYZ').to_quaternion()
    end=parent@Euler(gun['sourceEulerEnd'],'XYZ').to_quaternion()
    turn=end@start.inverted()
    if gun['sourceMirror']<0:turn.y=-turn.y;turn.z=-turn.z
    rest=Quaternion(gun['sourceRigRotationWXYZ']);end_turn=rest@turn@rest.inverted()
    R=np.array(end_turn.to_matrix());rest_matrix=np.array(rest.to_matrix())
    authored=adjusted+(sp-origin)@rest_matrix.T@R
    cp=source.copy();cp.data=source.data.copy();cp.animation_data_clear();cp.modifiers.clear();scene.collection.objects.link(cp);cp.name=name+'_SourceElevationRail'
    for v,p in zip(cp.data.vertices,authored):v.co=Vector(p)
    bm=bmesh.new();bm.from_mesh(cp.data);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in ids],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(cp.data);bm.free()
    cp.parent=asset;cp.matrix_parent_inverse=Matrix.Identity(4);cp.matrix_local=Matrix.Identity(4);bpy.context.view_layer.update();world=cp.matrix_world.copy();cp.parent=gun;cp.matrix_world=world
    for i in range(len(cp.data.materials)):cp.data.materials[i]=light
    cp['sourceObject']='holo.001';cp['sourceIsland']=gid;cp['sourceFaceIds']=ids;cp['originalSourceLinkage']=True;cp['sourceEndRigTurnWXYZ']=list(end_turn)
    changed.add(cp.name);rail_keys.update(face_key(sp[list(source.data.polygons[fi].vertices)])for fi in ids)
    report['sourceElevationRails'].append({'mesh':cp.name,'sourceIsland':gid,'sourceFaceIds':ids,'sourcePolygons':len(ids),'followsBarrel':name})
for o in [bpy.data.objects['holo.001'],bpy.data.objects['Flank24_OriginalFixedHull']]:
    bm=bmesh.new();bm.from_mesh(o.data);m=inv@o.matrix_world
    removed=[f for f in bm.faces if face_key([m@v.co for v in f.verts])in rail_keys]
    if removed:
        bmesh.ops.delete(bm,geom=removed,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(o.data);changed.add(o.name)
    bm.free()
updates={};cheeks=[]
for name in report['stations']:
    C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes']);q=(sp-C)@Q
    for gid,ids in groups.items():
        p=q[ids]
        if len(ids)!=18 or p[:,1].min()<-18.5 or p[:,1].max()>10 or p[:,2].min()<-3 or p[:,2].max()>3.5 or p[:,0].min()*p[:,0].max()<=0:continue
        sign=np.sign(p[:,0].mean());outer=set()
        for fi in group_faces[gid]:
            f=source.data.polygons[fi];p=q[list(f.vertices)];n=np.cross(p[1]-p[0],p[2]-p[0]);n/=np.linalg.norm(n)
            if n[0]*sign>.65 and f.area>6:outer.update(f.vertices)
        if not outer:continue
        for vi in outer:
            p=q[vi].copy();p[0]=sign*(6.306-.007*p[1]-p[2])/1.58
            assert np.linalg.norm(p-q[vi])<1.,(name,gid,p,q[vi])
            updates[tuple(np.round(sp[vi],4))]=C+Q@p
        cheeks.append({'station':name,'sourceIsland':gid,'outerVertices':len(outer),'sourceOuterVertices':sorted(outer)})
counts={}
update_items=list(updates.items());update_tree=KDTree(len(update_items))
for i,(p,_)in enumerate(update_items):update_tree.insert(Vector(p),i)
update_tree.balance()
for o in [bpy.data.objects['holo.001'],bpy.data.objects['Flank24_OriginalFixedHull']]:
    m=inv@o.matrix_world;mi=m.inverted();n=0
    for v in o.data.vertices:
        _,index,distance=update_tree.find(m@v.co)
        if distance<.0002:v.co=mi@Vector(update_items[index][1]);n+=1
    if n:
        o.data.update();changed.add(o.name)
    counts[o.name]=n
# Close the gaps above and beside the original short cheek walls by extending
# their exterior contour in-place. No bearing or inward trough face is cut.
for row in cheeks:
    name=row['station'];C=np.array(frames[name]['frameOrigin']);Q=np.array(frames[name]['frameAxes'])
    source_vertices=row['sourceOuterVertices']
    desired=[updates[tuple(np.round(sp[k],4))]for k in source_vertices]
    match=None
    for o in [bpy.data.objects['holo.001'],bpy.data.objects['Flank24_OriginalFixedHull']]:
        p=points(o);distances=np.linalg.norm(p[:,None,:]-np.array(desired)[None,:,:],axis=2)
        indices=distances.argmin(0)
        if max(distances[indices,np.arange(len(desired))])<.0002:match=(o,indices.tolist());break
    assert match,name
    o,indices=match;p=points(o);q=(p-C)@Q;sign=np.sign(q[indices,0].mean())
    upper=sorted(indices,key=lambda k:q[k,2],reverse=True)[:2]
    lower=[k for k in indices if k not in upper]
    upper.sort(key=lambda k:q[k,1]);lower.sort(key=lambda k:q[k,1])
    bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table()
    inverse=(inv@o.matrix_world).inverted()
    def vertex(x,b,n=None):
        n=6.306-1.58*abs(x)-.007*b if n is None else n
        v=bm.verts.new(inverse@Vector(C+Q@np.array([x,b,n])))
        return v
    gray=material_slot(o,light);inner=material_slot(o,red)
    ur,uf=[bm.verts[k]for k in upper];lr,lf=[bm.verts[k]for k in lower]
    # Keep the middle-bank skirt below its physical hinge sweep. The rear
    # bank lifts with the turret, while the forward bank has a higher hinge.
    tr=vertex(sign*2.88,q[upper[0],1]);tf=vertex(sign*2.88,q[upper[1],1])
    rear_top=vertex(sign*2.60,-17.42);rear_low=vertex(sign*abs(q[lower[0],0]),-17.42)
    fore_top=vertex(sign*2.88,9.46);fore_low=vertex(sign*abs(q[lower[1],0]),9.46)
    patches=[(ur,uf,tf,tr),(lr,ur,tr,rear_top,rear_low),(uf,lf,fore_low,fore_top,tf)]
    new_faces=[]
    for vertices in patches:
        f=bm.faces.new(vertices);f.material_index=gray;f.smooth=False;new_faces.append(f)
        uv=bm.loops.layers.uv.active
        if uv:
            for loop in f.loops:loop[uv].uv=(loop.vert.co.x*.025,loop.vert.co.y*.025)
        # A thin red inside return closes the exterior without exposing gray
        # paint in the bore channel when its grates open.
        inner_vertices=[]
        for v in vertices:
            model=np.array((inv@o.matrix_world)@v.co);local=(model-C)@Q;local[0]-=sign*.08
            inner_vertices.append(bm.verts.new(inverse@Vector(C+Q@local)))
        f=bm.faces.new(list(reversed(inner_vertices)));f.material_index=inner;new_faces.append(f)
        for i in range(len(vertices)):
            j=(i+1)%len(vertices);f=bm.faces.new([vertices[i],vertices[j],inner_vertices[j],inner_vertices[i]]);f.material_index=gray;new_faces.append(f)
    bmesh.ops.recalc_face_normals(bm,faces=new_faces);bm.to_mesh(o.data);bm.free();o.data.update();changed.add(o.name)
    row['fixedContourExtensions']=3
report['fixedCheekFit']={'islands':cheeks,'editedVertices':counts,'innerFacesRetained':True}
bpy.data.objects.remove(source,do_unlink=True)
for name,h in before.items():
    if name not in changed:assert digest(bpy.data.objects[name])==h,('Unrelated geometry changed',name)
for name,m in joint_before.items():
    assert np.array_equal(np.array(bpy.data.objects[name].matrix_local),m),('Joint rest changed',name)
for name,props in barrel_before.items():
    assert plain(dict(bpy.data.objects[name].items()))==props,('Barrel metadata changed',name)
for o in scene.objects:assert o.animation_data is None,o.name
assert not bpy.data.actions
with source_path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==source_hash
report.update(unchangedOtherMeshes=len(before)-len(set(before)&changed),unchangedJointTransforms=len(joint_before),animationClips=0)
(review/'source-fit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
asset['version']='0.11.26'
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.26.blend'),compress=True)
print('FITTED_SOURCE_FLANKS',len(report['stations']),len(cheeks),counts,flush=True)
