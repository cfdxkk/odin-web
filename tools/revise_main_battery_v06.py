"""Five-piece, polygonal main-battery armor. Run on the separate v0.5 asset.

The two side skins follow the turret shroud and the narrowing foredeck. The
third skin is the short wedge at the fore-end of those covers, identified by
the user's annotated close-up. Only static geometry and guide metadata are saved. Nuxt owns
the clearance sequence; the original odin.blend is never modified.
"""
import bpy, bmesh, math
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
scene = bpy.context.scene
asset = bpy.data.objects['Odin_Asset']
paint = bpy.data.materials['Odin_Paint_Light']
roof_cache={}

BANKS = {
    'Dorsal': dict(direction=1, center=.0999, hull='holo.001',
        originY=135.77142857142857,
        outline=[(0.08,116.25),(2.0,116.25),(11.6,114.55),(12.6,118.5),
                 (10.45,145.5),(6.0,154.6),(0.08,154.6)],
        noseStart=154.8,noseEnd=168.5,noseRearWidth=5.8,noseTipWidth=1.0,
        source='立方体',lift=.95,forward=14.0,
        apron=[(13.9,71.8),(14.55,72.8),(15.8,114.3),(12.8,114.3),(11.55,114.3),(12.5,90.0)],
        exit=(13.6,0,-10.0), pocket=(2.8,0,-13.2), ribs=14),
    'Ventral': dict(direction=-1, center=0.0, hull='holo.013',
        originY=82.14285714285714,
        outline=[(0.08,67.8),(2.0,67.8),(11.2,65.7),(12.7,69.2),
                 (10.0,91.0),(5.6,103.0),(0.08,103.0)],
        noseStart=103.2,noseEnd=116.9,noseRearWidth=5.4,noseTipWidth=1.0,
        source='立方体.002',lift=.85,forward=12.5,
        apron=[(14.1,22.0),(14.75,23.0),(16.0,64.5),(13.0,65.4),(11.75,64.5),(12.7,40.2)],
        exit=(13.8,0,10.0), pocket=(2.6,0,13.0), ribs=13),
}

def keep_world(obj,parent):
    bpy.context.view_layer.update()
    world=obj.matrix_world.copy();obj.parent=parent;obj.matrix_world=world

def joint(name,position,role):
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj)
    obj.parent=asset;obj.location=position
    obj['staticJoint']=True;obj['system']='main-hatch';obj['armorRole']=role
    return obj

def surface(bank,x,y,sign=1):
    if bank=='Dorsal':
        u=(y-76.7555)/101.4139
        ridge=2.2584-1.1087*u
        height=54.1070-6.6379*u
        slope=1.1074+.3924*u
        z=height-max(0,x-ridge)*slope
        # The dorsal leaf sits under the fixed serrated deck lip. Keep its
        # roof smooth instead of imprinting those stationary details onto it.
        return z
    else:
        u=(y-28.8009)/100.4494
        ridge=2.2582-1.1087*u
        height=67.2268-15.4514*u
        slope=1.10+.48*u
        z=-(height-max(0,x-ridge)*slope)
    # At the tapered lip, the source hull rises into the side skin. Follow its
    # actual surface rather than letting a guessed plane disappear through it.
    key=(bank,round(sign*x,5),round(y,5))
    if key not in roof_cache:
        config=BANKS[bank];direction=config['direction'];hull=bpy.data.objects[config['hull']]
        matrix=asset.matrix_world.inverted()@hull.matrix_world;inverse=matrix.inverted()
        hit,point,normal,face=hull.ray_cast(inverse@Vector((sign*x+config['center'],y,direction*100)),inverse.to_3x3()@Vector((0,0,-direction)))
        if hit:z=direction*max(direction*z,direction*(matrix@point).z+.16)
        roof_cache[key]=z
    return roof_cache[key]

def span(poly,y):
    hits=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if abs(b[1]-a[1])<1e-7:
            if abs(y-a[1])<1e-7: hits.extend((a[0],b[0]))
        elif min(a[1],b[1])-1e-7<=y<=max(a[1],b[1])+1e-7:
            hits.append(a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1]))
    return min(hits),max(hits)

def make_mesh(name,verts,faces,parent,bevel=.0):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    obj.parent=asset;data.materials.append(paint)
    if bevel:
        m=obj.modifiers.new('Armor edge finish','BEVEL');m.width=bevel;m.segments=2;m.limit_method='ANGLE'
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=m.name)
    keep_world(obj,parent)
    return obj

def closed_shell(name,points,faces,parent,direction,thickness=.34,bevel=.055):
    n=len(points);verts=points+[tuple(Vector(p)+Vector((0,0,-direction*thickness))) for p in points]
    result=list(faces)+[tuple(i+n for i in reversed(f)) for f in faces]
    edges={}
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):
            key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
    result += [(a,b,b+n,a+n) for (a,b),count in edges.items() if count==1]
    return make_mesh(name,verts,result,parent,bevel)

def side_skin(bank,side,config):
    sign=-1 if side=='Port' else 1;direction=config['direction'];poly=config['outline']
    p=joint(f'Hatch_{bank}_{side}',(sign*11+config['center'],config['originY'],direction*42),'side')
    p['guideExit']=[sign*config['exit'][0],0,config['exit'][2]]
    p['guidePocket']=[sign*config['pocket'][0],0,config['pocket'][2]]
    p['slideVector']=[a+b for a,b in zip(p['guideExit'],p['guidePocket'])]
    p['closedOutlineXY']=[[sign*x+config['center'],y] for x,y in poly]
    p['sourceReference']='RSI main-battery clip; polygonal shroud notch and foredeck chamfer'
    y0=min(y for x,y in poly);y1=max(y for x,y in poly)
    rows=sorted(set([y for x,y in poly]+[y0+(y1-y0)*i/40 for i in range(41)]))
    verts=[];faces=[]
    for y in rows:
        low,high=span(poly,y)
        ridge=(2.2584-1.1087*(y-76.7555)/101.4139 if bank=='Dorsal' else 2.2582-1.1087*(y-28.8009)/100.4494)
        for x in (low,max(low,min(high,ridge)),high):
            verts.append((sign*x+config['center'],y,surface(bank,x,y,sign)))
    for i in range(len(rows)-1):
        for k in range(2): faces.append((i*3+k,i*3+k+1,(i+1)*3+k+1,(i+1)*3+k))
    skin=closed_shell(f'Hatch_{bank}_{side}_PolygonSkin',verts,faces,p,direction)
    skin['continuousLeaf']=True;skin['polygonSides']=len(poly)
    # Shallow transverse stiffeners are clipped to the same polygonal skin.
    # A continuous backplate remains visible between them.
    for i in range(config['ribs']):
        rib_end=config['noseStart']-.5
        ya=y0+.7+(rib_end-y0-1.2)*i/config['ribs'];yb=ya+(rib_end-y0-1.2)/config['ribs']*.73
        pts=[]
        for y in (ya,yb):
            low,high=span(poly,y);low=max(low+.25,2.0);high-=.25
            if high-low<.45:break
            for x in (low,high):pts.append((sign*x+config['center'],y,surface(bank,x,y,sign)+direction*.12))
        if len(pts)==4:
            closed_shell(f'Hatch_{bank}_{side}_Rib_{i:02}',pts,[(0,1,3,2)],p,direction,.16,.025)
    return p

def separate_nose(bank,config):
    # This is the short triangular cap in the user's green outline, immediately
    # ahead of the long side skins. The farther foredeck stays intact.
    center=config['center'];direction=config['direction']
    rear=config['noseStart'];front=config['noseEnd'];width=config['noseRearWidth'];tip=config['noseTipWidth']
    ridge=1.4
    xy=[(-width,rear),(-ridge,rear),(ridge,rear),(width,rear),(-tip,front),(tip,front)]
    points=[(x+center,y,surface(bank,abs(x),y,-1 if x<0 else 1)) for x,y in xy]
    p=joint(f'Hatch_{bank}_Nose',(center,(rear+front)/2,direction*48),'nose')
    p['liftVector']=[0,0,direction*config['lift']]
    p['slideVector']=[0,config['forward'],0]
    p['sourceObject']=config['source']
    p['sourceReference']='User annotated short fore-end wedge, confirmed against RSI deployment clip'
    p['closedOutlineXY']=[[x+center,y] for x,y in [xy[0],xy[1],xy[2],xy[3],xy[5],xy[4]]]
    cap=closed_shell(f'Hatch_{bank}_Nose_Wedge',points,[(0,1,4),(1,2,5,4),(2,3,5)],p,direction,.30,.045)
    cap['continuousLeaf']=True
    print('SHORT FORE-END CAP',bank,rear,front,flush=True)

def separate_apron(bank,side,config):
    """Separate the actual hull skin below each moving gun shroud.

    Cutting the existing surface retains its slope, panel details and UVs.
    It is independent of both the long forward cover and the rising shroud.
    """
    sign=-1 if side=='Port' else 1;direction=config['direction']
    hull=bpy.data.objects[config['hull']];M=asset.matrix_world.inverted()@hull.matrix_world;inverse=M.inverted()
    poly=[Vector((x,y,0)) for x,y in config['apron']]
    center=sum(poly,Vector())/len(poly)
    planes=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        normal=Vector((-(b-a).y,(b-a).x,0)).normalized()
        if normal.dot(center-a)<0:normal.negate()
        planes.append((a,normal))
    def projected(co):
        p=M@co;return Vector((sign*(p.x-config['center']),p.y,0)),direction*p.z
    def inside(co):
        p,h=projected(co)
        return h>(33 if bank=='Dorsal' else 43) and all(n.dot(p-a)>-.0001 for a,n in planes)
    bm=bmesh.new();bm.from_mesh(hull.data)
    # Only local roof faces need cuts; keep other hull topology untouched.
    for a,n in planes:
        faces=[]
        for f in bm.faces:
            points=[projected(v.co) for v in f.verts]
            if max(h for p,h in points)<(33 if bank=='Dorsal' else 43):continue
            if max(p.y for p,h in points)<min(p.y for p in poly) or min(p.y for p,h in points)>max(p.y for p in poly):continue
            if max(p.x for p,h in points)<11 or min(p.x for p,h in points)>17:continue
            if direction*(M.to_3x3()@f.normal).z<.35:continue
            faces.append(f)
        geom=set(faces)
        for f in faces:geom.update(f.edges);geom.update(f.verts)
        point=inverse@Vector((sign*a.x+config['center'],a.y,0))
        normal=M.to_3x3().transposed()@Vector((sign*n.x,n.y,0))
        bmesh.ops.bisect_plane(bm,geom=list(geom),dist=.00001,plane_co=point,plane_no=normal,use_snap_center=False,clear_outer=False,clear_inner=False)
    selected=[f for f in bm.faces if inside(f.calc_center_median()) and direction*(M.to_3x3()@f.normal).z>.35]
    assert selected,(bank,side,'Missing original aft armor skin')
    data=bpy.data.meshes.new(f'Hatch_{bank}_Aft_{side}_OriginalSkin')
    vertices=[];faces=[];materials=[];uvs=[];uv=bm.loops.layers.uv.active
    for f in selected:
        offset=len(vertices);vertices.extend([tuple(M@v.co) for v in f.verts]);faces.append(tuple(range(offset,len(vertices))));materials.append(f.material_index)
        uvs.extend([tuple(loop[uv].uv) for loop in f.loops] if uv else [(0,0)]*len(f.verts))
    data.from_pydata(vertices,[],faces);data.update()
    for material in hull.data.materials:data.materials.append(material)
    layer=data.uv_layers.new(name='UVMap')
    for loop,tex in zip(layer.data,uvs):loop.uv=tex
    for f,index in zip(data.polygons,materials):f.material_index=index
    obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);obj.parent=asset
    p=joint(f'Hatch_{bank}_Aft_{side}',(sign*13+config['center'],center.y,direction*40),'aft')
    p['guideExit']=[sign*3.0,0,-direction*3.8];p['guidePocket']=[sign*.8,0,-direction*6.0]
    p['slideVector']=[a+b for a,b in zip(p['guideExit'],p['guidePocket'])]
    p['closedOutlineXY']=[[sign*x+config['center'],y] for x,y in config['apron']]
    p['sourceObject']=hull.name;p['sourceReference']='RSI lower shroud skirts; black and yellow regions in user annotation'
    keep_world(obj,p)
    mod=obj.modifiers.new('Armor skin thickness','SOLIDIFY');mod.thickness=.20;mod.offset=-1
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)
    bmesh.ops.delete(bm,geom=selected,context='FACES');bm.to_mesh(hull.data);bm.free();hull.data.update()
    print('SEPARATED AFT SKIN',bank,side,len(faces),flush=True)
bay_material=bpy.data.objects['MainBay_Dorsal'].data.materials[0]
for obj in list(scene.objects):
    if obj.name.startswith(('Hatch_','MainBay_','MainRail_')):bpy.data.objects.remove(obj,do_unlink=True)
# Color the original recessed floor instead of using the old rectangular floor
# and rails that projected through the narrowing bow/keel exterior.
for bank,config in BANKS.items():
    hull=bpy.data.objects[config['hull']];M=asset.matrix_world.inverted()@hull.matrix_world
    materials=list(hull.data.materials)
    if bay_material not in materials:hull.data.materials.append(bay_material);materials.append(bay_material)
    mi=materials.index(bay_material)
    for face in hull.data.polygons:
        point=M@face.center;normal=M.to_3x3()@face.normal
        if bank=='Dorsal':selected=76<point.y<169 and 28<point.z<35 and abs(point.x)<max(0,13-(point.y-76)*.14) and normal.z>.8
        else:selected=28<point.y<115 and -51<point.z<-37 and abs(point.x)<max(0,13-(point.y-28)*.145) and normal.z<-.8
        if selected:face.material_index=mi
for bank,config in BANKS.items():
    for side in ('Port','Starboard'):side_skin(bank,side,config)
    separate_nose(bank,config)
    for side in ('Port','Starboard'):separate_apron(bank,side,config)
for obj in scene.objects:obj.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
asset['version']='0.6.0';scene.name='ODIN v0.6 — five-piece main-battery armor'
bpy.data.orphans_purge(do_recursive=True)
dest=root/'assets/blender/odin_articulated_v0.6.0.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
print('SAVED',dest,flush=True)
