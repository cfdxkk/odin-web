"""Fit five separate armor leaves to the intact v0.5 hull and turret boundaries.

The measured reference curves use Odin_Asset coordinates with the closed web
pose applied. No hull faces are removed. Only static geometry/joints are saved;
the runtime in odin-rig.ts supplies all reversible motion.
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from mathutils.bvhtree import BVHTree

root=Path(__file__).resolve().parents[1]
scene=bpy.context.scene;asset=bpy.data.objects['Odin_Asset']
paint=bpy.data.materials['Odin_Paint_Light']
reference=json.loads((root/'tools/main_armor_v07_boundaries.json').read_text())
original_hull={n:(len(bpy.data.objects[n].data.vertices),len(bpy.data.objects[n].data.polygons)) for n in ['holo.001','holo.013']}

def mix_curve(points,value,axis=1):
    points=sorted(points,key=lambda p:p[axis])
    if value<=points[0][axis]:return Vector(points[0])
    if value>=points[-1][axis]:return Vector(points[-1])
    for a,b in zip(points,points[1:]):
        if a[axis]<=value<=b[axis]:return Vector(a).lerp(Vector(b),(value-a[axis])/(b[axis]-a[axis]))

def keep_world(obj,parent):
    bpy.context.view_layer.update();world=obj.matrix_world.copy();obj.parent=parent;obj.matrix_world=world

def joint(name,position,role):
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj);obj.parent=asset;obj.location=position
    obj['staticJoint']=True;obj['system']='main-hatch';obj['armorRole']=role
    return obj

def shell(name,points,faces,parent,direction,thickness=.20):
    n=len(points);verts=[tuple(p) for p in points]+[tuple(Vector(p)+Vector((0,0,-direction*thickness))) for p in points]
    edges={}
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):
            k=tuple(sorted((a,b)));edges[k]=edges.get(k,0)+1
    fs=list(faces)+[tuple(i+n for i in reversed(f)) for f in faces]
    fs += [(a,b,b+n,a+n) for (a,b),count in edges.items() if count==1]
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],fs);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.parent=asset;data.materials.append(paint)
    keep_world(obj,parent);return obj

def ray_surface(hull,x,y,direction):
    m=asset.matrix_world.inverted()@hull.matrix_world;mi=m.inverted()
    hit,p,n,f=hull.ray_cast(mi@Vector((x,y,direction*100)),mi.to_3x3()@Vector((0,0,-direction)))
    return (m@p).z if hit else None

def clear_fixed_lip(obj,hull,direction):
    """Finish the ventral flange against its stepped, non-planar source lip.

    Projecting only the outline can leave an interior triangle crossing a
    raised lip. Move only the intersecting flange vertices by small steps.
    This is a static fit operation; the fixed hull remains byte-for-byte intact.
    """
    inverse=asset.matrix_world.inverted();matrix=inverse@hull.matrix_world
    hull.data.calc_loop_triangles()
    fixed=BVHTree.FromPolygons([matrix@v.co for v in hull.data.vertices],
        [tuple(t.vertices) for t in hull.data.loop_triangles],all_triangles=True)
    obj.data.calc_loop_triangles();faces=[tuple(t.vertices) for t in obj.data.loop_triangles]
    displacement={}
    for iteration in range(40):
        matrix=inverse@obj.matrix_world
        moving=BVHTree.FromPolygons([matrix@v.co for v in obj.data.vertices],faces,all_triangles=True)
        overlap=moving.overlap(fixed)
        if not overlap:break
        vertices={v for i,_ in overlap for v in faces[i]}
        for i in vertices:
            obj.data.vertices[i].co.z+=direction*.04
            displacement[i]=displacement.get(i,0)+.04
    else:raise RuntimeError(f'Cannot fit fixed lip at {obj.name}')
    obj.data.update();obj['fixedLipFitMaxOffset']=max(displacement.values(),default=0)
    print('FITTED FIXED LIP',obj.name,len(displacement),obj['fixedLipFitMaxOffset'],flush=True)

def build_bank(bank,config):
    direction=config['direction'];center=config['center'];nose_start=config['noseStart'];nose_end=config['noseEnd']
    side_data={}
    for side in ['Port','Starboard']:
        sign=-1 if side=='Port' else 1
        # Work in positive, outboard distance to preserve each measured side.
        data=config[side]
        def canonical(points):return [[sign*(p[0]-center),p[1],p[2]] for p in points]
        rear=canonical(data['rear']);lip=canonical(data['lip']);upper=canonical(data['upper'])
        # Close the small front shroud -> hull-lip corner with the main leaf.
        rear=[[x,y+.32,z] for x,y,z in rear]
        rear[0][0]=.075
        edge_start=rear[-1][1]+.10
        outer_start=mix_curve(lip,edge_start);outer_start.y=edge_start
        outer=[list(outer_start)]+[p for p in lip if edge_start<p[1]<nose_start]+[list(mix_curve(lip,nose_start))]
        outer[-1][1]=nose_start
        outer=[[p[0]-(.10 if bank=='Dorsal' else .30),p[1],p[2]+direction*.10] for p in outer]
        rear += [[outer[0][0],outer[0][1],outer[0][2]]]
        rear=sorted(rear,key=lambda p:p[0])
        ridge0=mix_curve(rear,1.7,0)
        end_center_z=(48.98 if bank=='Dorsal' else -55.68)
        def z_at(x,y,outer=outer,rear=rear,ridge0=ridge0,end_center_z=end_center_z):
            edge=mix_curve(outer,y)
            t=max(0,min(1,(y-ridge0.y)/(nose_start-ridge0.y)))
            ridge_x=1.7+(1.4-1.7)*t
            ridge_z=ridge0.z+(end_center_z-ridge0.z)*t
            u=max(0,min(1,(x-ridge_x)/max(.01,edge.x-ridge_x)))
            z=ridge_z+(edge.z-ridge_z)*u
            back=mix_curve(rear,x,0)
            blend=max(0,min(1,(y-back.y)/4))
            return back.z*(1-blend)+z*blend
        perimeter=rear+outer[1:]+[[.075,nose_start,end_center_z]]
        if bank=='Ventral':
            dense=[]
            for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):
                count=max(1,math.ceil((Vector(b)-Vector(a)).length/.25))
                dense.extend([list(Vector(a).lerp(Vector(b),i/count)) for i in range(count)])
            perimeter=dense
        # Triangulate the measured perimeter, with a constrained ridge and a
        # small interior grid. The actual serrations remain boundary vertices.
        xy=[Vector((p[0],p[1])) for p in perimeter];boundary_count=len(xy)
        values={tuple(round(v,5) for v in p[:2]):p[2] for p in perimeter}
        for y in range(math.ceil(min(p[1] for p in rear)),math.floor(nose_start)+1):
            edge=mix_curve(outer,y)
            for i in range(1,19):
                x=edge.x*i/19
                if y>mix_curve(rear,x,0).y+.05:
                    xy.append(Vector((x,y)))
        verts,_,faces,_,_,_=delaunay_2d_cdt(xy,[],[list(range(boundary_count))],1,.00001)
        points=[]
        for v in verts:
            z=values.get(tuple(round(q,5) for q in v),z_at(v.x,v.y))
            if bank=='Ventral':
                hz=ray_surface(bpy.data.objects[config['hull']],center+sign*v.x,v.y,direction)
                if hz is not None:z=direction*max(direction*z,direction*hz+.26)
            points.append((center+sign*v.x,v.y,z))
        p=joint(f'Hatch_{bank}_{side}',(center+sign*8,(edge_start+nose_start)/2,direction*44),'side')
        p['guideExit']=[sign*(10.5 if bank=='Dorsal' else 10),0,-direction*6];p['guidePocket']=[0,0,-direction*(11.6 if bank=='Dorsal' else 10.1)]
        p['slideVector']=[a+b for a,b in zip(p['guideExit'],p['guidePocket'])]
        p['closedOutlineXY']=[[center+sign*x,y] for x,y,z in perimeter]
        p['construction']='fitted-serrated-leaf';p['sourceReference']='Measured original shroud front profile and fixed serrated hull lip'
        skin=shell(f'Hatch_{bank}_{side}_FittedSkin',points,[tuple(f) for f in faces],p,direction)
        if bank=='Ventral':clear_fixed_lip(skin,bpy.data.objects[config['hull']],direction)
        skin['continuousLeaf']=True
        # Relief follows the fitted surface, stopping inside the serrated seam.
        for i in range(14):
            ya=max(q[1] for q in rear)+.65+i*(nose_start-max(q[1] for q in rear)-1.4)/14
            yb=ya+(nose_start-max(q[1] for q in rear)-1.4)/14*.72
            pts=[]
            for y in [ya,yb]:
                edge=mix_curve(outer,y)
                for x in [1.95,max(2.0,edge.x-.24)]:pts.append((center+sign*x,y,z_at(x,y)+direction*.10))
            shell(f'Hatch_{bank}_{side}_Rib_{i:02}',pts,[(0,1,3,2)],p,direction,.12)
        side_data[side]=(outer,z_at)

        # Separate gap filler; this is added between the shroud toe and hull
        # inner lip. Never extract or delete any fixed-hull polygon.
        aft_lip=canonical(data['aftLip'])
        end=upper[-1][1]-.12
        start=max(upper[0][1],aft_lip[0][1],81.0 if bank=='Dorsal' else 40.0)
        ys=[start+i*(end-start)/80 for i in range(81)]
        points=[]
        for y in ys:
            u=mix_curve(upper,y);lo=mix_curve(aft_lip,y)
            points.extend([(center+sign*(u.x+.08),y,u.z-direction*.12),(center+sign*(lo.x-.08),y,lo.z+direction*.04)])
        faces=[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(ys)-1)]
        aft=joint(f'Hatch_{bank}_Aft_{side}',(center+sign*10,sum(ys)/len(ys),direction*43),'aft')
        aft['guideExit']=[sign*1.7,0,-direction*2.6];aft['guidePocket']=[0,0,-direction*4.4]
        aft['slideVector']=[a+b for a,b in zip(aft['guideExit'],aft['guidePocket'])]
        aft['construction']='gap-filler';aft['sourceObject']=config['hull'];aft['hullFacesRemoved']=0
        aft['closedOutlineXY']=[[v[0],v[1]] for v in points[::2]+list(reversed(points[1::2]))]
        aft['sourceReference']='Independent filler between rotating shroud lower edge and intact fixed hull inner lip'
        shell(f'Hatch_{bank}_Aft_{side}_GapFiller',points,faces,aft,direction,.12)

    # Short fore-end cap, meeting both front leaves. Original farther foredeck
    # stays fixed; it is not incorrectly repurposed as the cap.
    p=joint(f'Hatch_{bank}_Nose',(center,(nose_start+nose_end)/2,direction*48),'nose')
    p['liftVector']=[0,0,direction*.95];p['slideVector']=[0,14 if bank=='Dorsal' else 12.5,0]
    p['sourceObject']=config['source'];p['construction']='short-fore-end-cap'
    points=[]
    for y in [nose_start+.12,nose_end]:
        for side,sign in [('Port',-1),('Starboard',1)]:
            outer,z_at=side_data[side]
            width=outer[-1][0] if y<nose_end else 1.0
            for x in ([width,1.4,0] if sign<0 else [1.4,width]):
                if y==nose_end:x=min(x,1.0)
                z=z_at(x,nose_start) if y<nose_end else (48.25 if bank=='Dorsal' else -53.50)
                hull_z=ray_surface(bpy.data.objects[config['hull']],center+sign*x,y,direction)
                if bank=='Ventral' and hull_z is not None:z=direction*max(direction*z,direction*hull_z+.24)
                points.append((center+sign*x,y,z))
    p['closedOutlineXY']=[[v[0],v[1]] for v in points]
    shell(f'Hatch_{bank}_Nose_Wedge',points,[(i,i+1,i+6,i+5) for i in range(4)],p,direction,.20)

bay_material=bpy.data.objects['MainBay_Dorsal'].data.materials[0]
for obj in list(scene.objects):
    if obj.name.startswith(('Hatch_','MainBay_','MainRail_')):bpy.data.objects.remove(obj,do_unlink=True)
for bank,config in reference.items():
    build_bank(bank,config)
    for side in ['Port','Starboard']:
        tube=bpy.data.objects[f'Main_{bank}_Tube_{side}']
        tube['boreAxis']=[0,.9984075,-.0564137] if bank=='Dorsal' else [0,.9896915,.1432158]
        tube['deployedOffset']=[0,2,-config['direction']*.389];tube['stowTravel']=16.0
    # Preserve the existing recessed floor material without changing topology.
    hull=bpy.data.objects[config['hull']];M=asset.matrix_world.inverted()@hull.matrix_world
    materials=list(hull.data.materials)
    if bay_material not in materials:hull.data.materials.append(bay_material);materials.append(bay_material)
    for face in hull.data.polygons:
        co=M@face.center;n=M.to_3x3()@face.normal
        selected=(76<co.y<169 and 28<co.z<35 and abs(co.x)<max(0,13-(co.y-76)*.14) and n.z>.8) if bank=='Dorsal' else (28<co.y<115 and -51<co.z<-37 and abs(co.x)<max(0,13-(co.y-28)*.145) and n.z<-.8)
        if selected:face.material_index=materials.index(bay_material)
for name,counts in original_hull.items():
    o=bpy.data.objects[name];assert counts==(len(o.data.vertices),len(o.data.polygons)),f'{name} topology changed'
    o['armorRevisionHullFacesRemoved']=0
for obj in scene.objects:obj.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
asset['version']='0.7.0';scene.name='ODIN v0.7 — fitted armor seams and nested outer tubes'
bpy.data.orphans_purge(do_recursive=True)
dest=root/'assets/blender/odin_articulated_v0.7.0.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
print('SAVED',dest,flush=True)
