"""Shared closed seams for the five-piece bay; load the immutable v0.8 copy.

The main leaves and nose share a ridged cross-section. Their outside perimeter
comes from the actual hull hole, not a raised decoration. No fixed hull edits.
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

root=Path(__file__).resolve().parents[1]
asset=bpy.data.objects['Odin_Asset']; scene=bpy.context.scene
paint=bpy.data.materials['Odin_Paint_Light']; red=bpy.data.materials['Odin_Turret_Interior_DeepRed']
ref=json.loads((root/'tools/main_armor_v081_boundaries.json').read_text(encoding='utf8'))
GAP=.035; HALF_GAP=.0175; THICKNESS=.055

def curve(points,y,axis=1):
    ps=sorted(points,key=lambda p:p[axis])
    if y<=ps[0][axis]: return Vector(ps[0])
    if y>=ps[-1][axis]: return Vector(ps[-1])
    for a,b in zip(ps,ps[1:]):
        if a[axis]<=y<=b[axis]: return Vector(a).lerp(Vector(b),(y-a[axis])/(b[axis]-a[axis]))

def surface(hull,x,y,direction):
    m=asset.matrix_world.inverted()@hull.matrix_world;inv=m.inverted()
    hit,p,_,_=hull.ray_cast(inv@Vector((x,y,direction*100)),inv.to_3x3()@Vector((0,0,-direction)))
    return (m@p).z if hit else None

def clear_children(parent):
    for child in list(parent.children): bpy.data.objects.remove(child,do_unlink=True)

def shell(name,points,faces,parent,direction,thickness=THICKNESS):
    n=len(points)
    verts=[tuple(v) for v in points]+[tuple(Vector(v)+Vector((0,0,-direction*thickness))) for v in points]
    edges={}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
    fs=list(faces)+[tuple(i+n for i in reversed(f)) for f in faces]
    fs.extend((a,b,b+n,a+n) for (a,b),count in edges.items() if count==1)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],fs);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.parent=asset
    bpy.context.view_layer.update();world=obj.matrix_world.copy();obj.parent=parent;obj.matrix_world=world
    mesh.materials.append(paint);mesh.materials.append(red)
    for face in mesh.polygons:
        if direction*face.normal.z<-.1:face.material_index=1
    return obj

audit={}
for bank,c in ref.items():
    direction=c['direction'];center=c['center'];end=c['noseStart'];hull=bpy.data.objects[c['hull']]
    top_end=48.98 if bank=='Dorsal' else -55.68
    side_sections={}
    for side,sign in [('Port',-1),('Starboard',1)]:
        data=c[side]
        def canon(ps):return [[sign*(p[0]-center),p[1],p[2]] for p in ps]
        lip=canon(data['lip']);rear=canon(data['rear']);u=canon([data['upper'][-1]])[0]
        rear=[[x,y+HALF_GAP,z] for x,y,z in rear if x<u[0]-.025]
        rear[0][0]=HALF_GAP
        rear.append([u[0],u[1]+HALF_GAP,u[2]])
        edge_y=u[1]+HALF_GAP
        lo=curve(lip,edge_y);lo.y=edge_y
        outside=[list(lo)]+[p for p in lip if edge_y<p[1]<end]+[list(curve(lip,end))]
        outside[-1][1]=end
        outside=[[x-GAP,y,z+direction*.005] for x,y,z in outside]
        rear.append(outside[0]);rear=sorted(rear,key=lambda p:p[0])
        ridge_start=curve(rear,1.7,0)
        def height(x,y,rear=rear,outside=outside,ridge_start=ridge_start,end=end,top_end=top_end):
            edge=curve(outside,y)
            u=max(0,min(1,x/edge.x));rx=u*rear[-1][0]
            for _ in range(5):rx=u*curve(outside,curve(rear,rx,0).y).x
            back=curve(rear,rx,0)
            t=max(0,min(1,(y-back.y)/(end-back.y)))
            finish=outside[-1];front_x=u*finish[0]
            front=top_end+(finish[2]-top_end)*max(0,min(1,(front_x-1.4)/(finish[0]-1.4)))
            edge_t=max(0,min(1,(y-outside[0][1])/(end-outside[0][1])))
            linear_edge=outside[0][2]*(1-edge_t)+finish[2]*edge_t
            correction=(edge.z-linear_edge)*u*t/max(edge_t,.00001)
            return back.z*(1-t)+front*t+correction
        # Include the ridge on the front boundary. A single sloping edge here
        # previously disagreed with the nose's flat crest by more than a unit.
        boundary=rear+outside[1:]+[[1.4,end,top_end],[HALF_GAP,end,top_end]]
        xy=[Vector(p[:2]) for p in boundary]
        boundary_count=len(xy)
        heights={tuple(round(v,6) for v in p[:2]):p[2] for p in boundary}
        ridge_ids=[]
        for i in range(41):
            t=i/40;y=ridge_start.y+(end-ridge_start.y)*t;x=1.7+(1.4-1.7)*t
            ridge_ids.append(len(xy));xy.append(Vector((x,y)))
        constraints=list(zip(ridge_ids,ridge_ids[1:]))
        for y in range(math.ceil(min(p[1] for p in rear)),math.floor(end)+1):
            edge=curve(outside,y)
            for i in range(1,22):
                x=edge.x*i/22
                if y>curve(rear,x,0).y+.01:xy.append(Vector((x,y)))
        vs,_,faces,_,_,_=delaunay_2d_cdt(xy,constraints,[list(range(boundary_count))],1,.000001)
        points=[]
        for v in vs:
            z=heights.get(tuple(round(q,6) for q in v),height(v.x,v.y))
            points.append((center+sign*v.x,v.y,z))
        parent=bpy.data.objects[f'Hatch_{bank}_{side}'];clear_children(parent)
        obj=shell(f'Hatch_{bank}_{side}_FittedSkin',points,[tuple(f) for f in faces],parent,direction)
        obj.data.set_sharp_from_angle(angle=math.radians(30))
        for polygon in obj.data.polygons: polygon.use_smooth=True
        bpy.context.view_layer.update()
        parent['closedOutlineXY']=[[center+sign*x,y] for x,y,z in boundary]
        parent['closedSeamGap']=GAP;parent['sharedNoseRidgeHalfWidth']=1.4
        parent['seamReleaseVector']=[0,.85,0]
        parent['clearanceLift']=[0,0,.8 if bank=='Dorsal' else -2.2]
        parent['sourceReference']='Exact fixed hull hole edge; shared ridged nose section; matched shroud perimeter'
        # Small surface ribs follow the same analytic surface, stopping before
        # every mating edge rather than forming a second lifted border.
        max_back=max(p[1] for p in rear)
        for i in range(14):
            ya=max_back+.5+i*(end-max_back-1)/14;yb=ya+(end-max_back-1)/14*.68
            ps=[];columns=33;row_count=5
            for row in range(row_count):
                y=ya+(yb-ya)*row/(row_count-1)
                edge=curve(outside,y)
                for k in range(columns):
                    x=1.95+(max(2,edge.x-.22)-1.95)*k/(columns-1)
                    actual=surface(obj,center+sign*x,y,direction)
                    if actual is None:raise RuntimeError('Rib outside main armor skin')
                    ps.append((center+sign*x,y,actual+direction*.10))
            rib=shell(f'Hatch_{bank}_{side}_Rib_{i:02}',ps,[(r*columns+k,r*columns+k+1,(r+1)*columns+k+1,(r+1)*columns+k) for r in range(row_count-1) for k in range(columns-1)],parent,direction,.04)
            rib.data.set_sharp_from_angle(angle=math.radians(30))
            for polygon in rib.data.polygons:polygon.use_smooth=True
            for face in rib.data.polygons:face.material_index=0
        side_sections[side]=(outside,height)
        audit[f'{bank}/{side}']={'lipGap':GAP,'lipHeightOffset':.005,'frontRidge':[center+sign*1.4,end,top_end],'aftMeetingPoint':[center+sign*u[0],u[1]+HALF_GAP,u[2]]}

    parent=bpy.data.objects[f'Hatch_{bank}_Nose'];clear_children(parent)
    start=end+GAP;finish=c['noseEnd']
    fore_fit_start=finish-2.0
    ys=sorted({start,finish,fore_fit_start}|{p[1] for side in ['Port','Starboard'] for p in c[side]['lip'] if start<p[1]<finish})
    rows=[]
    for a,b in zip(ys,ys[1:]):
        count=max(1,math.ceil((b-a)/(.055 if a>=fore_fit_start else .3)));rows.extend(a+(b-a)*i/count for i in range(count))
    rows.append(finish)
    # At the forward seam use the real foredeck, rather than a taller assumed
    # wedge. The central ray reaches the empty bay floor, so sample the lips.
    probes=[surface(hull,center+sign*1.4,finish,direction) for sign in [-1,1]]
    end_top=sum(v for v in probes if v is not None)/len([v for v in probes if v is not None])
    points=[]
    # Preserve the five-point ridged section at the aft seam, but tessellate
    # across its width as well as along it. The fixed foredeck has raised teeth
    # between the two former crest probes, so five columns missed its contour.
    sections=[(0,1,16),(1,2,8),(2,3,8),(3,4,16)]
    column_count=49
    for y in rows:
        t=(y-start)/(finish-start);crest=top_end+(end_top-top_end)*t
        edges={}
        for side,sign in [('Port',-1),('Starboard',1)]:
            edge=curve(c[side]['lip'],y)
            edges[side]=(edge.x-sign*GAP,edge.z+direction*.005)
        width=min(abs(edges['Port'][0]-center),abs(edges['Starboard'][0]-center))
        ridge=min(1.4*(1-t)+1.1*t,width*.80)
        section=[(edges['Port'][0],edges['Port'][1]),(center-ridge,crest),(center,crest),(center+ridge,crest),(edges['Starboard'][0],edges['Starboard'][1])]
        row=[]
        for first,last,count in sections:
            xa,za=section[first];xb,zb=section[last]
            row.extend((xa+(xb-xa)*i/count,za+(zb-za)*i/count) for i in range(count))
        row.append(section[-1])
        for x,z in row:
            if y>=fore_fit_start:
                hz=surface(hull,x,y,direction)
                if hz is not None:
                    # Only the short forward overlap follows the fixed deck.
                    # The rear shared main/nose section remains unchanged.
                    z=direction*max(direction*z,direction*hz+THICKNESS+.012)
            points.append((x,y,z))
    faces=[(r*column_count+i,r*column_count+i+1,(r+1)*column_count+i+1,(r+1)*column_count+i) for r in range(len(rows)-1) for i in range(column_count-1)]
    nose_outline=points[::column_count]+list(reversed(points[column_count-1::column_count]))
    if bank=='Dorsal':
        # The actual forward mating edge is also serrated across the ship.
        # These are original holo.001 edge vertices, mirrored about its X=0
        # seam. A straight cut at y=168.5 ran through these fixed teeth.
        tooth_half=[(0.,168.707184,47.748001),(.388976,167.906281,47.780052),
            (.710311,168.649979,47.744797),(1.051940,167.791855,47.780056),
            (1.369892,168.535553,47.744797),(1.711522,167.677429,47.780052),
            (2.029474,168.421143,47.744797),(2.374486,168.283844,47.231949)]
        fore=[[-x,y-GAP,z+.005] for x,y,z in reversed(tooth_half[1:])]+[[x,y-GAP,z+.005] for x,y,z in tooth_half]
        fore[0][0]+=GAP;fore[-1][0]-=GAP
        rear_row=points[:column_count]
        edge_chains={}
        for side,sign in [('Port',-1),('Starboard',1)]:
            stop=fore[0 if sign<0 else -1][1]
            edge_chains[side]=[[p[0]-sign*GAP,p[1],p[2]+.005]
                for p in c[side]['lip'] if start<p[1]<stop]
        boundary=list(rear_row)+edge_chains['Starboard']+list(reversed(fore))+list(reversed(edge_chains['Port']))
        xy=[Vector(p[:2]) for p in boundary];count=len(xy)
        for yi in range(math.ceil(start*10),math.ceil(max(p[1] for p in fore)*10)):
            y=yi/10
            left=curve(c['Port']['lip'],y).x+GAP;right=curve(c['Starboard']['lip'],y).x-GAP
            for xi in range(math.ceil(left*16),math.floor(right*16)+1):
                x=xi/16
                if y<curve(fore,x,0).y-.0001:xy.append(Vector((x,y)))
        vs,_,polys,_,_,_=delaunay_2d_cdt(xy,[],[list(range(count))],1,.000001)
        from mathutils.kdtree import KDTree
        boundary_tree=KDTree(len(boundary))
        for i,p in enumerate(boundary):boundary_tree.insert(Vector((p[0],p[1],0)),i)
        boundary_tree.balance()
        fitted=[]
        for v in vs:
            _,bi,error=boundary_tree.find(Vector((v.x,v.y,0)))
            if error<.0001:z=boundary[bi][2]
            else:
                t=(v.y-start)/(finish-start);crest=top_end+(end_top-top_end)*t
                side='Starboard' if v.x>=center else 'Port';sign=1 if side=='Starboard' else -1
                e=curve(c[side]['lip'],v.y);edge_x=e.x-sign*GAP;edge_z=e.z+.005
                radius=abs(v.x-center);ridge=1.4*(1-t)+1.1*t
                z=crest+(edge_z-crest)*max(0,min(1,(radius-ridge)/(abs(edge_x-center)-ridge)))
                front=curve(fore,v.x,0);u=max(0,min(1,(v.y-(front.y-2))/2));u=u*u*(3-2*u)
                z=z*(1-u)+front.z*u
            fitted.append((v.x,v.y,z))
        points=fitted;faces=[tuple(f) for f in polys];nose_outline=boundary
    nose_skin=shell(f'Hatch_{bank}_Nose_Wedge',points,faces,parent,direction,.025 if bank=='Dorsal' else THICKNESS)
    if bank=='Dorsal':
        from mathutils.bvhtree import BVHTree
        inverse=asset.matrix_world.inverted();hull.data.calc_loop_triangles()
        hm=inverse@hull.matrix_world
        fixed=BVHTree.FromPolygons([hm@v.co for v in hull.data.vertices],
            [tuple(t.vertices) for t in hull.data.loop_triangles],all_triangles=True,epsilon=.000001)
        nose_skin.data.calc_loop_triangles();triangles=[tuple(t.vertices) for t in nose_skin.data.loop_triangles]
        count=len(points);corrections={}
        assert len(nose_skin.data.vertices)==count*2
        for iteration in range(160):
            nm=inverse@nose_skin.matrix_world;closed=[nm@v.co for v in nose_skin.data.vertices]
            touched=set()
            for lift in [.95*(i/50)**2*(3-2*i/50) for i in range(51)]:
                posed=[p+Vector((0,0,lift)) for p in closed]
                moving=BVHTree.FromPolygons(posed,triangles,all_triangles=True,epsilon=.000001)
                touched.update(v%count for i,_ in moving.overlap(fixed) for v in triangles[i])
            if not touched:break
            for index in touched:
                p=closed[index]
                delta=Vector((0,0,.006)) if p.y>finish-2.4 else Vector((-.004 if p.x>center else .004,0,0))
                for actual in [index,index+count]:nose_skin.data.vertices[actual].co+=delta
                corrections[index]=corrections.get(index,Vector())+delta
        else:raise RuntimeError('Nose fitted edge still contacts fixed hull during lift')
        nose_skin.data.update()
        nose_skin['forwardEdgeLocalFitMax']=max((v.length for v in corrections.values()),default=0)
        nose_skin['forwardEdgeSource']='Original holo.001 transverse serrated seam'
        print('NOSE_LOCAL_FIT',len(corrections),nose_skin['forwardEdgeLocalFitMax'],flush=True)
    if bank=='Ventral':parent['liftVector']=[0,0,-2.3]
    parent['closedSeamGap']=GAP;parent['sharedMainRidgeHalfWidth']=1.4
    parent['closedOutlineXY']=[[p[0],p[1]] for p in nose_outline]
    audit[f'{bank}/Nose']={'aftSeamGap':GAP,'aftCrest':top_end,'forwardCrest':end_top,'fixedForedeckProbes':probes}

for filename in ['fit_aft_seams_v081.py','fit_main_rear_seams_v081.py']:
    helper=root/'tools'/filename
    exec(compile(helper.read_text(encoding='utf8'),str(helper),'exec'))
for obj in scene.objects:obj.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
asset['version']='0.8.1';scene.name='ODIN v0.8.1 - shared armor seams'
bpy.data.orphans_purge(do_recursive=True)
(root/'work/v081-main-fit.json').write_text(json.dumps(audit,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.8.1.blend'),compress=True)
print('SAVED v0.8.1 main seam candidate',flush=True)
